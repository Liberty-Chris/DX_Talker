from dataclasses import replace
from datetime import datetime
import queue
import socket
import threading
import time
import unittest
from unittest.mock import patch

from dxtalker.models import UTC, Settings
from dxtalker.source import NoRedirect, SourceClient


class SourceTests(unittest.TestCase):
    def test_real_local_socket_partial_prompts_negotiation_and_spots(self):
        events = queue.Queue()
        received = []
        failures = []
        server = socket.socket()
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        server.settimeout(3)
        port = server.getsockname()[1]
        finished = threading.Event()

        def serve():
            try:
                conn, _ = server.accept()
                with conn:
                    conn.settimeout(3)
                    conn.sendall(b"\xff\xfb\x01log")
                    time.sleep(0.02)
                    conn.sendall(b"in:")
                    pending = b""
                    while b"\r\n" not in pending:
                        pending += conn.recv(4096)
                    received.append(pending)
                    conn.sendall(b"Pass")
                    time.sleep(0.02)
                    conn.sendall(b"word:")
                    pending = b""
                    while b"\r\n" not in pending:
                        pending += conn.recv(4096)
                    received.append(pending)
                    conn.sendall(f"\r\nWelcome\r\nTo ALL: not a spot\r\nDX de N0CALL: 7074 KT4BN CQ {datetime.now(UTC):%H%M}Z\r\n".encode())
                    finished.wait(3)
            except Exception as exc:
                failures.append(exc)
            finally:
                server.close()

        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        client = SourceClient(replace(Settings(), host="127.0.0.1", port=port, login="KF4DBX"),
                              lambda kind, value: events.put((kind, value)), "sessionSecret")
        client.start()
        observed = []
        try:
            deadline = time.monotonic() + 4
            while time.monotonic() < deadline:
                event = events.get(timeout=4)
                observed.append(event)
                if event[0] == "spot":
                    break
            self.assertEqual([v.dx_call for k, v in observed if k == "spot"], ["KT4BN"])
            self.assertIn(b"KF4DBX\r\n", received[0])
            self.assertIn(b"\xff\xfe\x01", received[0])
            self.assertEqual(received[1], b"sessionSecret\r\n")
            self.assertNotIn("sessionSecret", str(observed))
            self.assertTrue(any(k == "source_ready" for k, _ in observed))
        finally:
            client.stop()
            finished.set()
            client.thread.join(4)
            thread.join(4)
        self.assertFalse(failures)
        self.assertFalse(client.thread.is_alive())

    def test_manual_commands_are_bounded_single_lines(self):
        client = SourceClient(Settings(), lambda *args: None)
        client.sock = object()
        for text in ("", "login\r\ncommand", "x" * 201, "日本語"):
            with self.assertRaises(ValueError):
                client.send(text)
        client.send("KF4DBX")
        self.assertEqual(client.commands.get_nowait(), "KF4DBX")

    def test_https_reads_contract_and_does_not_log_token(self):
        import json

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def read(self, limit):
                return json.dumps([{"dx_call": "WB4IUY", "spotter": "N0CALL", "frequency_khz": 14025,
                                    "time": datetime.now(UTC).isoformat()}]).encode()

        class Opener:
            def open(self, req, timeout):
                self.request = req
                return Response()

        observed = []
        client = SourceClient(replace(Settings(), source_type="HTTPS JSON", feed_url="https://example.org/feed"),
                              lambda kind, value: observed.append((kind, value)), "privateToken")
        opener = Opener()
        old_emit = client.emit

        def emit(kind, value):
            old_emit(kind, value)
            if kind == "spot":
                client.cancel.set()

        client.emit = emit
        with patch("dxtalker.source.request.build_opener", return_value=opener):
            client._https()
        self.assertEqual(opener.request.get_header("Authorization"), "Bearer privateToken")
        self.assertNotIn("privateToken", str(observed))
        self.assertTrue(any(k == "spot" for k, _ in observed))

    def test_redirects_are_not_followed(self):
        self.assertIsNone(NoRedirect().redirect_request(None, None, 302, "Found", {}, "https://other.org/"))

    def test_connection_failure_disables_and_redacts_exception_content(self):
        observed = []

        def connector(*args, **kwargs):
            raise OSError("never log this password")

        client = SourceClient(Settings(), lambda kind, value: observed.append((kind, value)), connector=connector)
        def emit(kind, value):
            observed.append((kind, value))
            if kind == "source_lost":
                client.cancel.set()
        client.emit = emit
        client._run()
        self.assertTrue(any(k == "source_lost" for k, _ in observed))
        self.assertNotIn("password", str(observed))


    def test_raw_console_redacts_secrets_commands_and_controls(self):
        observed = []
        client = SourceClient(Settings(), lambda *event: observed.append(event), "privateSecret")
        client.sock = object()
        client.send("manualSecret")
        client._raw("echo privateSecret manualSecret token=unknownValue\x07")
        self.assertNotIn("privateSecret", str(observed))
        self.assertNotIn("manualSecret", str(observed))
        self.assertNotIn("unknownValue", str(observed))
        self.assertNotIn("\x07", str(observed))
        self.assertEqual(observed[0][0], "raw")

    def test_login_prompt_not_lost_when_banner_shares_same_network_chunk(self):
        class Socket:
            def __init__(self):
                self.packets = [b'login:\r\nWelcome to the test cluster\r\n']
                self.sent = []
            def settimeout(self, value): pass
            def sendall(self, value): self.sent.append(value)
            def recv(self, size):
                if self.packets: return self.packets.pop(0)
                client.cancel.set()
                raise socket.timeout()
        sock = Socket()
        client = SourceClient(Settings(login='WB4IUY'), lambda *event: None,
                              connector=lambda *a, **kw: sock)
        client._cluster()
        self.assertEqual(sock.sent, [b'WB4IUY\r\n'])

    def test_ansi_and_nul_login_password_prompts_work_at_every_split(self):
        packets = b'\x1b[32mlogin:\x1b[0m\x00\r\nWelcome\r\nPassword:\x00'
        for split in range(len(packets) + 1):
            class Socket:
                def __init__(self):
                    self.packets = [p for p in (packets[:split], packets[split:]) if p]
                    self.sent = []
                def settimeout(self, value): pass
                def sendall(self, value): self.sent.append(value)
                def recv(self, size):
                    if self.packets: return self.packets.pop(0)
                    client.cancel.set()
                    raise socket.timeout()
            sock = Socket()
            client = SourceClient(Settings(login='WB4IUY'), lambda *event: None, 'fixtureSecret',
                                  connector=lambda *a, **kw: sock)
            client._cluster()
            with self.subTest(split=split):
                self.assertEqual(sock.sent, [b'WB4IUY\r\n', b'fixtureSecret\r\n'])

    def test_quiet_cluster_session_prompt_is_visible_without_claiming_valid_spots(self):
        observed = []
        class Socket:
            def __init__(self):
                self.packets = [b'login:', b'WB4IUY de N0CALL 05-Nov-2026 1200Z dxspider >']
            def settimeout(self, value): pass
            def sendall(self, value): pass
            def recv(self, size):
                if self.packets: return self.packets.pop(0)
                client.cancel.set()
                raise socket.timeout()
        client = SourceClient(Settings(login='WB4IUY'), lambda *event: observed.append(event),
                              connector=lambda *a, **kw: Socket())
        client._cluster()
        self.assertTrue(any(k == 'raw' and v == 'login:' for k, v in observed))
        self.assertTrue(any(k == 'source_state' and v.startswith('Signed in') for k, v in observed))
        self.assertFalse(client.ready.is_set())
        self.assertFalse(any(k == 'spot' for k, _ in observed))

    def test_failed_socket_is_closed_before_retry_notification(self):
        class Socket:
            closed = False
            def settimeout(self, value): pass
            def recv(self, size): raise ConnectionError('private remote text')
            def shutdown(self, how): pass
            def close(self): self.closed = True
        sock = Socket()
        observed = []
        def emit(kind, value):
            observed.append((kind, value))
            if kind == 'source_lost':
                self.assertTrue(sock.closed)
                self.assertIsNone(client.sock)
                client.cancel.set()
        client = SourceClient(Settings(), emit, connector=lambda *a, **kw: sock)
        client._run()
        self.assertNotIn('private remote text', str(observed))
        self.assertFalse(client.ready.is_set())

    def test_stop_during_connect_closes_new_socket_without_login(self):
        class Socket:
            closed = False
            def close(self): self.closed = True
        sock = Socket()
        def connector(*args, **kwargs):
            client.cancel.set()
            return sock
        client = SourceClient(Settings(login='WB4IUY'), lambda *event: None, connector=connector)
        client._cluster()
        self.assertTrue(sock.closed)
        self.assertIsNone(client.sock)
