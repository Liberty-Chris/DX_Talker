from dataclasses import replace
from datetime import datetime
import json
from pathlib import Path
import tempfile
import unittest

from dxtalker.history import History
from dxtalker.models import Settings, UTC, load_settings, parse_line
from dxtalker.profiles import ProfileStore


class ProfileTests(unittest.TestCase):
    def test_profiles_switch_connection_only_and_keep_secrets_out_of_plaintext(self):
        def protector(text, decrypt=False):
            return "test-password" if decrypt else "encrypted-fixture"
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "profiles.json"
            store = ProfileStore(path, protector)
            first = store.save("Home", Settings(login="KF4DBX"), "test-password", True)
            second = store.save("Alternate", Settings(host="cluster.example", port=9000))
            self.assertNotIn("test-password", path.read_text())
            self.assertEqual(ProfileStore(path, protector).profiles, store.profiles)
            loaded, secret = store.load(first["id"], Settings(volume_percent=37))
            self.assertEqual(loaded.login, "KF4DBX")
            self.assertEqual(loaded.volume_percent, 37)
            self.assertEqual(secret, "test-password")
            loaded, secret = store.load(second["id"], loaded)
            self.assertEqual((loaded.host, loaded.port, secret), ("cluster.example", 9000, ""))
            renamed = store.save("New name", loaded, profile_id=first["id"])
            self.assertEqual(renamed["id"], first["id"])
            self.assertEqual(renamed["secret"], "")
            store.delete(first["id"])
            self.assertEqual(len(store.profiles), 1)

    def test_duplicate_names_and_bad_profile_do_not_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "profiles.json"
            store = ProfileStore(path)
            store.save("Home", Settings())
            original = path.read_bytes()
            for name, settings in (("home", Settings()), ("bad\nname", Settings()), ("Other", Settings(host="bad/host"))):
                with self.assertRaises(ValueError):
                    store.save(name, settings)
                self.assertEqual(path.read_bytes(), original)
            path.write_text('{"schema_version": 99}')
            with self.assertRaises(ValueError):
                ProfileStore(path)
            self.assertEqual(path.read_text(), '{"schema_version": 99}')

    def test_old_settings_migrate_with_preferences_and_no_output_state(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            path.write_text(json.dumps({"schema_version": 1, "voice": "Existing voice", "volume_percent": 33}))
            value = load_settings(path)
            self.assertEqual((value.voice, value.volume_percent, value.group_pause_ms), ("Existing voice", 33, 450))
            self.assertFalse(value.supervised_ack)
            self.assertFalse(hasattr(value, "enabled"))


class HistoryTests(unittest.TestCase):
    def test_structured_spots_and_bounded_rotation(self):
        with tempfile.TemporaryDirectory() as folder:
            history = History(Settings(log_directory=folder, log_max_mb=1, log_backups=2))
            history.handler.maxBytes = 500
            now = datetime.now(UTC)
            spot = parse_line(f"DX de N0CALL: 7074 WB4IUY CQ {now:%H%M}Z", "cluster", now)
            for _ in range(30):
                history.spot(spot, "Home")
            history.close()
            files = list(Path(folder).glob("history.jsonl*"))
            self.assertEqual(len(files), 3)
            for file in files:
                for line in file.read_text().splitlines():
                    row = json.loads(line)
                    self.assertEqual((row["kind"], row["dx_call"], row["profile"]), ("spot", "WB4IUY", "Home"))
                    self.assertNotIn("raw", row)
                    self.assertNotIn("password", row)

    def test_disabled_logging_does_not_create_folder(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder) / "unused"
            history = History(Settings(log_directory=str(directory), logging_enabled=False))
            history.record("connection", profile="Home")
            history.close()
            self.assertFalse(directory.exists())
