"""Desktop integration checks use synthetic sources and never play audio or key PTT."""
from dataclasses import replace
from datetime import datetime
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from dxtalker.models import Settings, UTC, load_settings, parse_line, save_settings


@unittest.skipUnless(sys.platform == "win32" or os.environ.get("DISPLAY"), "Requires a desktop display")
class AppTests(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        from dxtalker.app import Application
        self.folder = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, LOCALAPPDATA=self.folder.name)
        self.env.start()
        save_settings(Settings(check_updates=False))
        self.root = tk.Tk()
        self.root.withdraw()
        with patch.object(Application, "_refresh_devices"), patch.object(Application, "_load_voices"):
            self.app = Application(self.root)
        self.root.update()

    def tearDown(self):
        self.app.close()
        self.app.engine.worker.join(3)
        for callback in self.root.tk.call("after", "info"):
            self.root.after_cancel(callback)
        try:
            self.root.destroy()
        except Exception:
            pass
        self.env.stop()
        self.folder.cleanup()

    def spot(self):
        now = datetime.now(UTC)
        return parse_line(f"DX de N0CALL: 7074 WB4IUY CQ {now:%H%M}Z", "cluster", now)

    def test_settings_fields_acknowledgment_profiles_and_clear(self):
        from dataclasses import fields
        self.assertEqual(set(self.app.variables), {f.name for f in fields(Settings)})
        self.app.variables["supervised_ack"].set(True)
        self.app._apply()
        self.assertTrue(load_settings().supervised_ack)
        self.assertFalse(self.app.engine.enabled)
        self.app.profile_name.set("Home")
        self.app._save_profile()
        self.app._add_spot(self.spot())
        self.app.command.set("old command")
        self.app._select_profile()
        self.assertEqual(len(self.app.spots), 0)
        self.assertEqual(self.app.command.get(), "")
        self.assertFalse(self.app.engine.enabled)
        self.assertEqual(self.app.variables["supervised_ack"].get(), True)

    def test_new_source_clears_old_spots_and_discards_late_events(self):
        class FakeSource:
            def __init__(self, settings, emit, secret):
                self.emit = emit
                self.ready = threading.Event()
            def start(self): pass
            def stop(self): pass
        with patch("dxtalker.app.SourceClient", FakeSource):
            self.app._connect()
            previous = self.app.source
            self.app._add_spot(self.spot())
            generation = self.app.source_generation
            self.app.variables["host"].set("new.example")
            self.app._connect()
            self.assertFalse(self.app.spots)
            previous.emit("spot", self.spot())
            self.app.emit("source_event", (generation, "spot", self.spot()))
            self.app._poll()
            self.assertFalse(self.app.spots)
            self.assertFalse(self.app.engine.enabled)

    def test_display_and_raw_console_are_bounded_history_survives_clear(self):
        self.app.variables["display_limit"].set(50)
        self.app._apply()
        for _ in range(70):
            self.app._add_spot(self.spot())
        self.assertEqual(len(self.app.spots), 50)
        for i in range(30):
            self.app._append_raw(str(i))
        self.assertEqual(self.app.raw_lines, [str(i) for i in range(15, 30)])
        self.app._history_spot(self.spot())
        self.app._clear_spots()
        path = Path(self.folder.name) / "DXTalker/logs/history.jsonl"
        self.assertIn("WB4IUY", path.read_text())
        self.assertFalse(self.app.spots)

    def test_command_fields_visible_by_default_and_password_mask_is_shared(self):
        self.assertEqual(len(self.app.command_entries), 2)
        for entry in self.app.command_entries:
            self.assertEqual(entry.cget("show"), "")
        self.app.command_secret.set(True)
        self.app._mask_commands()
        for entry in self.app.command_entries:
            self.assertEqual(entry.cget("show"), "*")
