from dataclasses import replace
import hashlib
from io import BytesIO
from pathlib import Path
import tempfile
import threading
import unittest

from dxtalker import updates


def release(version="v0.2.0a4", prerelease=True, content=b"test installer"):
    base = f"https://github.com/{updates.REPOSITORY}/releases/download/{version}/"
    return {"tag_name": version, "prerelease": prerelease, "draft": False, "body": "Changes",
            "assets": [{"name": updates.INSTALLER, "size": len(content), "browser_download_url": base + updates.INSTALLER},
                       {"name": updates.CHECKSUMS, "browser_download_url": base + updates.CHECKSUMS}]}


class UpdateTests(unittest.TestCase):
    def test_channel_version_order_and_missing_assets(self):
        candidates = [release("v0.2.0a10"), release("v0.2.0a2"), release("v0.1.0", False),
                      release("v0.3.0rc1"), release("garbage")]
        self.assertEqual(updates.select_release(candidates, "0.1.0a2").version, "v0.3.0rc1")
        self.assertEqual(updates.select_release(candidates, "0.1.0a2", "Stable").version, "v0.1.0")
        self.assertIsNone(updates.select_release([release("v0.1.0a1")], "0.1.0a2"))
        bad = release()
        bad["assets"] = []
        self.assertIsNone(updates.select_release([bad]))
        self.assertGreater(updates.version_key("0.2.0"), updates.version_key("0.2.0rc9"))

    def test_foreign_download_url_and_oversized_release_rejected(self):
        for url in ("http://github.com/Liberty-Chris/DX_Talker/releases/download/v1/a.exe",
                    "https://github.com.evil.example/Liberty-Chris/DX_Talker/releases/download/v1/a.exe",
                    "https://github.com/other/repository/releases/download/v1/a.exe"):
            candidate = release()
            candidate["assets"][0]["browser_download_url"] = url
            self.assertIsNone(updates.select_release([candidate]))
        candidate = release()
        candidate["assets"][0]["size"] = updates.MAX_INSTALLER + 1
        self.assertIsNone(updates.select_release([candidate]))

    def test_verified_download_is_atomic_and_detects_later_tampering(self):
        payload = b"test installer"
        expected = hashlib.sha256(payload).hexdigest()
        candidate = updates.select_release([release(content=payload)], current="0.1.0a2")
        def opener(url):
            return BytesIO((expected + "  " + updates.INSTALLER + "\n").encode() if url.endswith(".txt") else payload)
        with tempfile.TemporaryDirectory() as folder:
            path, digest = updates.download(candidate, folder, opener=opener)
            self.assertEqual(path.read_bytes(), payload)
            self.assertTrue(updates.verify_download(path, digest))
            self.assertFalse(path.with_suffix(".partial").exists())
            path.write_bytes(b"changed")
            self.assertFalse(updates.verify_download(path, digest))

    def test_corrupt_truncated_and_cancelled_download_never_replace_installer(self):
        candidate = updates.select_release([release()], current="0.1.0a2")
        expected = hashlib.sha256(b"test installer").hexdigest()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / updates.INSTALLER
            path.write_bytes(b"previous verified file")
            for data in (b"wrong installer", b"short"):
                def opener(url):
                    return BytesIO((expected + "  " + updates.INSTALLER).encode() if url.endswith(".txt") else data)
                with self.assertRaises(ValueError):
                    updates.download(candidate, folder, opener=opener)
                self.assertEqual(path.read_bytes(), b"previous verified file")
                self.assertFalse(path.with_suffix(".partial").exists())
            cancel = threading.Event()
            cancel.set()
            with self.assertRaises(InterruptedError):
                updates.download(candidate, folder, cancel, opener=opener)

    def test_bad_checksum_and_bounded_api_response(self):
        with self.assertRaises(ValueError):
            updates.check(opener=lambda url: BytesIO(b"x" * (1024 * 1024 + 1)))
        with self.assertRaises(ValueError):
            updates.checksum_for(b"bad checksum")

    def test_published_preview_is_offered_to_a1_and_explained_on_stable_channel(self):
        import json
        data = json.dumps([release('v0.2.0a2')]).encode()
        opener = lambda url: BytesIO(data)
        result = updates.check_report('Pilot', current='0.2.0a1', opener=opener)
        self.assertEqual(result.release.version, 'v0.2.0a2')
        stable = updates.check_report('Stable', current='0.2.0a1', opener=opener)
        self.assertIsNone(stable.release)
        self.assertIn('Choose Pilot', stable.status)
        self.assertIn('0.2.0a2', stable.status)
        current = updates.check_report('Pilot', current='0.2.0a2', opener=opener)
        self.assertIsNone(current.release)
        self.assertIn('Installed 0.2.0a2', current.status)
        self.assertIn('No newer', current.status)

    def test_network_errors_are_distinct_and_do_not_expose_exception_text(self):
        from urllib.error import HTTPError, URLError
        import socket, ssl
        limit = HTTPError('https://example.org/private', 403, 'private error', {'X-RateLimit-Remaining': '0'}, None)
        self.assertIn('limit', updates.describe_error(limit))
        certificate = URLError(ssl.SSLCertVerificationError('private certificate details'))
        self.assertIn('verified', updates.describe_error(certificate))
        self.assertNotIn('private', updates.describe_error(certificate))
        dns = URLError(socket.gaierror('private hostname'))
        self.assertIn('resolved', updates.describe_error(dns))
        self.assertIn('timed out', updates.describe_error(TimeoutError('private timeout')))


    def test_update_context_requires_certificate_and_hostname_verification(self):
        import ssl
        context = updates.update_ssl_context()
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)

    def test_windows_updates_use_native_trust_context(self):
        from types import SimpleNamespace
        from unittest.mock import Mock, patch
        import ssl
        factory = Mock()
        with patch.object(updates.sys, 'platform', 'win32'), patch.dict(
                'sys.modules', {'truststore': SimpleNamespace(SSLContext=factory)}):
            self.assertIs(updates.update_ssl_context(), factory.return_value)
        factory.assert_called_once_with(ssl.PROTOCOL_TLS_CLIENT)

    def test_url_opener_uses_verified_context_and_https_redirect_guard(self):
        from unittest.mock import Mock, patch
        from urllib.error import URLError
        import ssl
        context = ssl.create_default_context()
        opener = Mock()
        opener.open.side_effect = URLError(ssl.SSLCertVerificationError('untrusted'))
        with patch.object(updates, 'update_ssl_context', return_value=context), patch.object(
                updates.request, 'build_opener', return_value=opener) as build:
            with self.assertRaises(URLError):
                updates.open_url(updates.API)
        redirect, https = build.call_args.args
        self.assertIsInstance(redirect, updates.HTTPSRedirect)
        self.assertIs(https._context, context)
        self.assertEqual(opener.open.call_count, 1)
        with self.assertRaises(ValueError):
            redirect.redirect_request(None, None, 302, '', {}, 'http://example.org/')
