"""Internet adapters. Events cross into the UI through a bounded queue."""
from __future__ import annotations

from datetime import datetime
import queue
import re
import socket
import threading
from urllib import request

from .models import UTC, Settings, parse_json_feed, parse_line
from .protocol import LineFramer, TelnetDecoder


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # A token must never follow a redirect to another service.
        return None


class SourceClient:
    def __init__(self, settings: Settings, emit, session_secret="", connector=socket.create_connection):
        settings.validate_connection()
        self.settings, self.secret = settings, session_secret
        self.ready = threading.Event()

        def notify(kind, value):
            if kind == "source_ready" and not self.cancel.is_set():
                self.ready.set()
            elif kind == "source_lost" or (kind == "source_state" and value == "Disconnected"):
                self.ready.clear()
            emit(kind, value)

        self.emit = notify
        self.connector = connector
        self.cancel = threading.Event()
        self.commands = queue.Queue(maxsize=8)
        self.sock = None
        self.thread = threading.Thread(target=self._run, daemon=True, name="DX source")

    def start(self):
        self.thread.start()

    def stop(self):
        self.ready.clear()
        self.cancel.set()
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

    def send(self, text):
        if self.settings.source_type != "TCP/Telnet" or not self.sock:
            raise ValueError("Connect to a cluster before sending a login response or command")
        if not text or len(text) > 200 or any(ord(c) < 32 or ord(c) > 126 for c in text):
            raise ValueError("Use one line of at most 200 printable ASCII characters")
        try:
            self.commands.put_nowait(text)
        except queue.Full:
            raise ValueError("Wait for the previous cluster command") from None

    def _run(self):
        delay = 2
        while not self.cancel.is_set():
            try:
                if self.settings.source_type == "TCP/Telnet":
                    self._cluster()
                else:
                    self._https()
                delay = 2
            except Exception as exc:
                # Do not log exception text: URLs, prompts and authentication values
                # can appear in transport exceptions.
                self.emit("source_lost", f"Source unavailable ({type(exc).__name__}). Retrying in {delay}s. RF is disabled.")
                if self.cancel.wait(delay):
                    break
                delay = min(delay * 2, 60)
            finally:
                if self.sock:
                    self.sock.close()
                    self.sock = None
                while not self.commands.empty():
                    self.commands.get_nowait()
        self.secret = ""
        self.emit("source_state", "Disconnected")

    def _cluster(self):
        s = self.settings
        self.emit("source_state", "Connecting")
        self.sock = self.connector((s.host, s.port), timeout=5)
        self.sock.settimeout(0.5)
        self.emit("source_state", "Connected. Waiting for sign in or the first valid spot.")
        decoder, framer = TelnetDecoder(), LineFramer()
        sent_login = sent_password = receiving = False
        prompt_tail = ""
        while not self.cancel.is_set():
            try:
                while True:
                    self.sock.sendall((self.commands.get_nowait() + "\r\n").encode("ascii"))
            except queue.Empty:
                pass
            try:
                raw = self.sock.recv(4096)
            except socket.timeout:
                continue
            if not raw:
                raise ConnectionError("Cluster disconnected")
            clean, reply = decoder.feed(raw)
            if reply:
                self.sock.sendall(reply)
            lines = framer.feed(clean)
            # Prompts frequently have no newline and can span socket reads.
            prompt_tail = (prompt_tail + clean.decode("ascii", errors="ignore"))[-512:]
            if not sent_login and re.search(r"(?:login|call\s*sign|callsign|call|user\s*name)\s*[:>]\s*$", prompt_tail, re.I):
                if s.login:
                    self.sock.sendall((s.login + "\r\n").encode("ascii"))
                    sent_login = True
                    prompt_tail = ""
                    self.emit("source_state", "Callsign sent. Waiting for sign in confirmation or a valid spot.")
                else:
                    self.emit("source_state", "Sign in requested. Enter a callsign or use the manual response field.")
            if not sent_password and re.search(r"password\s*[:>]\s*$", prompt_tail, re.I):
                if self.secret:
                    self.sock.sendall((self.secret + "\r\n").encode("ascii"))
                    sent_password = True
                    prompt_tail = ""
                    self.emit("source_state", "Password sent. Waiting for sign in confirmation or a valid spot.")
                else:
                    self.emit("source_state", "Password requested. Use the masked manual response field.")
            for line in lines:
                if re.search(r"(?:invalid password|login failed|access denied|authentication failed)", line, re.I):
                    raise PermissionError("Sign in rejected")
                spot = parse_line(line, "cluster")
                if spot:
                    if not receiving:
                        self.emit("source_ready", "Receiving DX spots")
                        receiving = True
                    self.emit("spot", spot)
                elif not receiving and re.search(r"\bde\b.*>\s*$", line):
                    self.emit("source_state", "Cluster prompt received. Waiting for valid DX spots.")
        # Do not carry manual responses across connection boundaries.
        while not self.commands.empty():
            self.commands.get_nowait()

    def _https(self):
        self.emit("source_state", "Connecting to HTTPS feed")
        opener = request.build_opener(NoRedirect())
        while not self.cancel.is_set():
            headers = {"Accept": "application/json", "User-Agent": "DXTalker/0.1"}
            if self.secret:
                headers["Authorization"] = "Bearer " + self.secret
            req = request.Request(self.settings.feed_url, headers=headers)
            with opener.open(req, timeout=5) as response:
                data = response.read(1048577)
                if len(data) > 1048576:
                    raise ValueError("Feed exceeds size limit")
            spots = parse_json_feed(data, "https")
            self.emit("source_ready", f"HTTPS feed received. {len(spots)} valid spots.")
            for spot in spots:
                self.emit("spot", spot)
            if self.cancel.wait(self.settings.poll_seconds):
                return
