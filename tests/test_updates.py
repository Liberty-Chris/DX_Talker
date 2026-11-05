from dataclasses import replace
import hashlib
from io import BytesIO
from pathlib import Path
import tempfile
import threading
import unittest

from dxtalker import updates


def release(version="v0.2.0a2", prerelease=True, content=b"test installer"):
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
