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

    def test_command_fields_always_visible(self):
        self.assertEqual(len(self.app.command_entries), 2)
        self.app.command.set("show/dx")
        for entry in self.app.command_entries:
            self.assertEqual(entry.cget("show"), "")
            self.assertEqual(entry.get(), "show/dx")
        self.assertFalse(hasattr(self.app, "command_secret"))

    def test_password_visibility_is_temporary_and_resets_on_profile_load(self):
        self.app.secret.set("synthetic secret")
        self.assertEqual(self.app.secret_entry.cget("show"), "*")
        self.app._toggle_secret()
        self.assertEqual(self.app.secret_entry.cget("show"), "")
        self.assertEqual(self.app.secret_toggle.cget("text"), "Hide")
        self.app._toggle_secret()
        self.assertEqual(self.app.secret.get(), "synthetic secret")
        self.assertEqual(self.app.secret_entry.cget("show"), "*")
        self.app.profile_name.set("Home")
        self.app._save_profile()
        self.app._toggle_secret()
        self.app._select_profile()
        self.assertEqual(self.app.secret_entry.cget("show"), "*")
        self.assertFalse(self.app.secret_visible)
        self.assertFalse(hasattr(self.app.settings, "secret_visible"))

    def test_source_type_enables_relevant_controls_and_preserves_details(self):
        self.assertEqual(str(self.app.field_widgets["feed_url"].cget("state")), "disabled")
        self.assertEqual(str(self.app.field_widgets["host"].cget("state")), "normal")
        self.app.secret.set("synthetic secret")
        self.app.variables["source_type"].set("HTTPS JSON")
        self.app._source_type_changed(clear_secret=True)
        self.assertEqual(self.app.secret.get(), "")
        self.assertEqual(str(self.app.field_widgets["feed_url"].cget("state")), "normal")
        self.assertEqual(str(self.app.field_widgets["host"].cget("state")), "disabled")
        self.assertEqual(self.app.secret_label.cget("text"), "HTTPS bearer token (optional)")
        self.assertEqual(self.app.variables["host"].get(), "w4mr.ddns.net")
        for entry in self.app.command_entries:
            self.assertEqual(str(entry.cget("state")), "disabled")
        self.app.variables["source_type"].set("TCP/Telnet")
        self.app._source_type_changed()
        self.assertEqual(str(self.app.field_widgets["host"].cget("state")), "normal")
        for entry in self.app.command_entries:
            self.assertEqual(str(entry.cget("state")), "normal")


    def test_units_change_live_rows_without_changing_the_source_record(self):
        spot = self.spot()
        self.app._add_spot(spot)
        item = next(iter(self.app.spots))
        self.app.variables['frequency_unit'].set('MHz')
        self.app._apply()
        self.assertEqual(self.app.tree.item(item, 'values')[2], '7.074')
        self.assertEqual(self.app.tree.heading('frequency')['text'], 'Frequency MHz')
        self.assertEqual(str(spot.frequency_khz), '7074')
        self.app.variables['frequency_unit'].set('kHz')
        self.app._apply()
        self.assertEqual(self.app.tree.item(item, 'values')[2], '7074')

    def test_connection_control_tracks_actual_socket_and_hover_action(self):
        class Source:
            def __init__(self): self.connected = threading.Event()
            def stop(self): self.connected.clear()
        self.app._render_connections()
        self.assertTrue(all(i['button'].cget('text') == 'Connect' for i in self.app.connection_controls))
        self.app.source = Source()
        self.app._render_connections()
        self.assertTrue(all(i['button'].cget('text') == 'Connecting...' for i in self.app.connection_controls))
        self.app.source.connected.set()
        self.app._render_connections()
        self.assertTrue(all(i['button'].cget('text') == 'Connected' for i in self.app.connection_controls))
        self.app.connection_controls[0]['hover'] = True
        self.app._render_connections()
        self.assertEqual(self.app.connection_controls[0]['button'].cget('text'), 'Disconnect')
        self.assertEqual(self.app.connection_controls[0]['shell'].cget('background'), '#d63852')
        self.app._connection_action()
        self.assertIsNone(self.app.source)
        self.assertTrue(all(i['button'].cget('text') == 'Connect' for i in self.app.connection_controls))

    def test_speech_settings_hide_the_inactive_provider_controls(self):
        self.assertEqual(self.app.piper_speech_fields.winfo_manager(), '')
        self.assertEqual(self.app.windows_speech_fields.winfo_manager(), 'grid')
        self.app.variables['speech_provider'].set('Piper')
        self.app._speech_provider_changed()
        self.assertEqual(self.app.windows_speech_fields.winfo_manager(), '')
        self.assertEqual(self.app.piper_speech_fields.winfo_manager(), 'grid')


    def test_listening_toggle_never_applies_settings_or_reconnects_source(self):
        from unittest.mock import Mock
        self.app.engine.configure(replace(self.app.settings, preview_device='local'))
        source = Mock()
        source.ready = threading.Event()
        source.ready.set()
        source.connected = threading.Event()
        source.connected.set()
        self.app.source = source
        generation = self.app.source_generation
        # Pending source edits must not be applied by either direction of the toggle.
        self.app.variables['host'].set('pending.example')
        with patch.object(self.app, '_apply', side_effect=AssertionError('Settings applied')), \
             patch.object(self.app, '_connect', side_effect=AssertionError('Source reconnected')), \
             patch.object(self.app, '_disconnect', side_effect=AssertionError('Source disconnected')):
            self.app._listen()
            self.assertTrue(self.app.engine.local_enabled)
            self.assertEqual(self.app.listening_controls[0]['button'].cget('text'), 'Listening')
            self.app.listening_controls[0]['hover'] = True
            self.app._render_connections()
            self.assertEqual(self.app.listening_controls[0]['button'].cget('text'), 'Stop listening')
            self.app._listen()
            self.assertFalse(self.app.engine.local_enabled)
            self.assertIs(self.app.source, source)
            self.assertTrue(source.ready.is_set())
            self.assertEqual(self.app.source_generation, generation)
            source.stop.assert_not_called()
            # Incoming source data still reaches the live view while listening is off.
            self.app.emit('source_event', (generation, 'spot', self.spot()))
            self.app._poll()
            self.assertEqual(len(self.app.spots), 1)
        self.assertEqual(self.app.variables['host'].get(), 'pending.example')
        self.app.source = None
