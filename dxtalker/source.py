"""Internet adapters. Events cross into the UI through a bounded queue."""
from __future__ import annotations

from datetime import datetime
import queue
import re
import socket
import threading
from urllib import request, error
import ssl

from .models import UTC, Settings, parse_json_feed, parse_line
from .protocol import LineFramer, TelnetDecoder, TerminalText


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # A token must never follow a redirect to another service.
        return None


class ClusterLoginError(PermissionError):
    """Only local fixed messages are allowed here, never server text."""


class SourceClient:
    def __init__(self, settings: Settings, emit, session_secret="", connector=socket.create_connection):
        settings.validate_connection()
        self.settings, self.secret = settings, session_secret
        self.ready = threading.Event()
        self.connected = threading.Event()

        def notify(kind, value):
            if kind in ("source_connected", "source_ready") and not self.cancel.is_set():
                self.connected.set()
            if kind == "source_ready" and not self.cancel.is_set():
                self.ready.set()
            elif kind == "source_lost" or (kind == "source_state" and value == "Disconnected"):
                self.ready.clear()
                self.connected.clear()
            emit(kind, value)

        self.emit = notify
        self.connector = connector
        self.cancel = threading.Event()
        self.commands = queue.Queue(maxsize=8)
        self.redaction_lock = threading.Lock()
        self.redactions = [session_secret] if session_secret else []
        self.sock = None
        self.socket_lock = threading.Lock()
        self.thread = threading.Thread(target=self._run, daemon=True, name="DX source")

    def start(self):
        self.thread.start()

    def stop(self):
        self.ready.clear()
        self.cancel.set()
        self._close_socket()

    def _close_socket(self):
        self.connected.clear()
        with self.socket_lock:
            sock, self.sock = self.sock, None
        if sock:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            finally:
                sock.close()

    def send(self, text):
        if self.cancel.is_set() or self.settings.source_type != "TCP/Telnet" or not self.sock:
            raise ValueError("Connect to a cluster before sending a login response or command")
        if not text or len(text) > 200 or any(ord(c) < 32 or ord(c) > 126 for c in text):
            raise ValueError("Use one line of at most 200 printable ASCII characters")
        with self.redaction_lock:
            self.redactions = list(dict.fromkeys(self.redactions + [text]))[-128:]
        try:
            self.commands.put_nowait(text)
        except queue.Full:
            raise ValueError("Wait for the previous cluster command") from None

    def _raw(self, line):
        # Console is session only. Scrub known credentials and all manual echoes.
        with self.redaction_lock:
            for value in sorted(self.redactions, key=len, reverse=True):
                line = line.replace(value, "[redacted]")
        line = re.sub(r"(?i)(password|token|secret)\s*[:=]\s*\S+", r"\1: [redacted]", line)
        line = "".join(c for c in line if c.isprintable())[:1024]
        self.emit("raw", line)

    def _run(self):
        delay = 2
        while not self.cancel.is_set():
            failure = None
            try:
                if self.settings.source_type == "TCP/Telnet":
                    self._cluster()
                else:
                    self._https()
                delay = 2
            except Exception as exc:
                failure = exc
            finally:
                # Release the prior session before backoff or a replacement login.
                self._close_socket()
                while not self.commands.empty():
                    self.commands.get_nowait()
            if self.cancel.is_set():
                break
            if failure is not None:
                if isinstance(failure, ClusterLoginError):
                    detail = str(failure)
                elif isinstance(failure, error.HTTPError):
                    detail = {401: "Feed authentication required. Check the token", 403: "Feed denied access. Check permission or rate limits",
                              404: "Feed URL was not found", 429: "Feed rate limit reached. Increase the polling interval"}.get(failure.code, f"Feed returned HTTP {failure.code}")
                elif isinstance(failure, error.URLError):
                    reason = failure.reason
                    detail = ("Feed certificate could not be verified. Check the clock and HTTPS filtering" if isinstance(reason, ssl.SSLCertVerificationError)
                              else "Feed hostname could not be resolved" if isinstance(reason, socket.gaierror)
                              else "Feed request timed out" if isinstance(reason, TimeoutError) else "Feed network request failed")
                elif isinstance(failure, ConnectionResetError):
                    detail = "Cluster closed the connection. Check access rules or duplicate sessions"
                elif isinstance(failure, socket.gaierror):
                    detail = "Cluster hostname could not be resolved"
                elif isinstance(failure, ConnectionRefusedError):
                    detail = "Source refused the connection"
                elif isinstance(failure, TimeoutError):
                    detail = "Source connection timed out"
                elif isinstance(failure, PermissionError):
                    detail = "Source sign in was rejected"
                else:
                    detail = f"Source unavailable ({type(failure).__name__})"
                self.emit("source_lost", f"{detail}. Retrying in {delay}s. RF is disabled.")
                if self.cancel.wait(delay):
                    break
                delay = min(delay * 2, 60)
        self.secret = ""
        self.connected.clear()
        self.emit("source_state", "Disconnected")

    def _cluster(self):
        s = self.settings
        self.emit("source_state", "Connecting")
        sock = self.connector((s.host, s.port), timeout=5)
        with self.socket_lock:
            cancelled = self.cancel.is_set()
            if not cancelled:
                self.sock = sock
        if cancelled:
            sock.close()
            return
        sock.settimeout(0.5)
        self.emit("source_connected", "Connected. Waiting for sign in or the first valid spot.")
        decoder, framer, terminal = TelnetDecoder(), LineFramer(), TerminalText()
        sent_login = sent_password = receiving = False
        while not self.cancel.is_set():
            try:
                while True:
                    sock.sendall((self.commands.get_nowait() + "\r\n").encode("ascii"))
            except queue.Empty:
                pass
            try:
                raw = sock.recv(4096)
            except socket.timeout:
                continue
            if not raw:
                raise ConnectionError("Cluster disconnected")
            clean, reply = decoder.feed(raw)
            if reply:
                sock.sendall(reply)
            lines = framer.feed(terminal.feed(clean))
            partial = framer.partial
            # A socket read may contain a prompt followed by a banner. Process
            # each framed line and the partial prompt, not only the packet tail.
            candidates = [(line, True) for line in lines] + ([(partial, False)] if partial else [])
            for line, complete in candidates:
                if complete:
                    self._raw(line)
                if re.search(r"(?:already (?:connected|logged\s*in)|duplicate (?:login|connection))", line, re.I):
                    raise ClusterLoginError("Callsign is already connected. Close the other session or use a cluster supported SSID")
                if re.search(r"(?:invalid password|login failed|access denied|authentication failed)", line, re.I):
                    raise ClusterLoginError("Cluster rejected sign in. Check the callsign and required password")
                prompt = re.search(r"(?:login|call\s*sign|callsign|call|user\s*name)\s*[:>]\s*$", line, re.I)
                password = re.search(r"password\s*[:>]\s*$", line, re.I)
                if prompt and not sent_login:
                    if not complete:
                        self._raw(line)
                    if s.login:
                        sock.sendall((s.login + "\r\n").encode("ascii"))
                        sent_login = True
                        if not complete:
                            framer.buffer.clear()
                        self.emit("source_state", "Callsign sent. Waiting for sign in confirmation or a valid spot.")
                    else:
                        self.emit("source_state", "Sign in requested. Enter a callsign or use the manual response field.")
                elif password and not sent_password:
                    if not complete:
                        self._raw(line)
                    if self.secret:
                        sock.sendall((self.secret + "\r\n").encode("ascii"))
                        sent_password = True
                        if not complete:
                            framer.buffer.clear()
                        self.emit("source_state", "Password sent. Waiting for sign in confirmation or a valid spot.")
                    else:
                        self.emit("source_state", "Password requested. Enter it in the password field and reconnect, or send a visible manual response.")
                spot = parse_line(line, "cluster") if complete else None
                if spot:
                    if not receiving:
                        self.emit("source_ready", "Receiving DX spots")
                        receiving = True
                    self.emit("spot", spot)
                elif not receiving and s.login and re.fullmatch(
                        r"\(?" + re.escape(s.login) + r"\)?\s+de\s+[A-Z0-9/\-]+\s+.*>\s*", line, re.I):
                    if not complete:
                        self._raw(line)
                    self.emit("source_state", "Signed in to cluster. Waiting for the first valid DX spot.")
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
