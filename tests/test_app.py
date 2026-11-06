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


    def test_ids_hide_inactive_source_and_preserve_text_and_file(self):
        self.assertEqual(self.app.voice_id_speech_fields.winfo_manager(), 'grid')
        self.assertEqual(self.app.voice_id_wav_fields.winfo_manager(), '')
        self.app.variables['voice_text'].set('Test station')
        self.app.variables['voice_wav'].set('example.wav')
        self.app.variables['voice_mode'].set('WAV')
        self.assertEqual(self.app.voice_id_speech_fields.winfo_manager(), '')
        self.assertEqual(self.app.voice_id_wav_fields.winfo_manager(), 'grid')
        self.app.variables['voice_mode'].set('Speech')
        self.assertEqual(self.app.variables['voice_text'].get(), 'Test station')
        self.assertEqual(self.app.variables['voice_wav'].get(), 'example.wav')
        self.assertLess(int(self.app.field_widgets['cw_wpm'].cget('width')), 15)
        self.assertLess(int(self.app.field_widgets['cw_text'].cget('width')), 45)

    def test_rf_toggle_without_source_or_ack_never_applies_or_reconnects(self):
        from unittest.mock import Mock
        from dxtalker.appearance import PALETTES
        engine = self.app.engine
        # Prevent the actual worker from rendering or opening hardware in this UI check.
        with engine.lock:
            engine.configure(replace(self.app.settings, radio_device='local', preview_device='local', cw_text='E'))
            self.app.variables['host'].set('pending.example')
            self.assertFalse(self.app.channel_ack.get())
            with patch.object(self.app, '_apply', side_effect=AssertionError('Applied pending settings')), \
                 patch.object(self.app, '_connect', side_effect=AssertionError('Reconnected')), \
                 patch.object(self.app, '_disconnect', side_effect=AssertionError('Disconnected')), \
                 patch('dxtalker.app.messagebox.askyesno', side_effect=AssertionError('Unexpected prerequisite')):
                self.app._enable()
                self.assertTrue(engine.enabled)
                button = self.app.rf_controls[0]
                self.assertEqual(button['button'].cget('text'), 'RF enabled')
                # Legacy acknowledgement edits no longer control RF.
                self.app.channel_ack.set(True)
                self.app.channel_ack.set(False)
                self.assertTrue(engine.enabled)
                for theme in PALETTES:
                    self.app.theme.set(theme)
                    button['focus'] = False
                    self.app._render_connections()
                    self.assertEqual(button['shell'].cget('background'), PALETTES[theme]['accent'])
                    button['focus'] = True
                    self.app._render_connections()
                    self.assertEqual(button['button'].cget('text'), 'Disable RF')
                    self.assertEqual(button['shell'].cget('background'), '#d63852')
                # Disabling RF leaves an existing cluster and live rows intact.
                source = Mock()
                self.app.source = source
                generation = self.app.source_generation
                self.app._add_spot(self.spot())
                self.app._enable()
                self.assertFalse(engine.enabled)
                self.assertIs(self.app.source, source)
                self.assertEqual(self.app.source_generation, generation)
                self.assertEqual(len(self.app.spots), 1)
                source.stop.assert_not_called()
                self.assertEqual(button['button'].cget('text'), 'Enable RF')
                self.app.source = None
            self.assertEqual(self.app.variables['host'].get(), 'pending.example')

    def test_rf_button_resets_after_stop_and_output_fault(self):
        engine = self.app.engine
        with engine.lock:
            engine.configure(replace(self.app.settings, radio_device='radio', cw_text='E'))
            self.app._enable()
            self.app._stop()
            self.assertEqual(self.app.rf_controls[0]['button'].cget('text'), 'Enable RF')
            self.app._enable()
            engine.stop('Output fault. RF disabled.')
            self.app._poll()
            self.assertEqual(self.app.rf_controls[0]['button'].cget('text'), 'Enable RF')


    def test_rf_stopping_state_and_source_loss_never_auto_rearm(self):
        class Source:
            def __init__(self, settings, emit, secret):
                self.emit = emit
                self.ready = threading.Event()
                self.connected = threading.Event()
            def start(self): pass
            def stop(self): pass
        with patch('dxtalker.app.SourceClient', Source):
            self.app._connect()
        engine = self.app.engine
        with engine.lock:
            engine.configure(replace(self.app.settings, radio_device='radio', cw_text='E'))
            self.app._enable()
            engine.busy = True
            self.app._enable()
            self.assertEqual(self.app.rf_controls[0]['button'].cget('text'), 'Stopping...')
            self.assertEqual(str(self.app.rf_controls[0]['button'].cget('state')), 'disabled')
            engine.busy = False
            self.app._enable()
            self.app.source.emit('source_lost', 'Test connection lost')
            self.assertFalse(engine.enabled)
            self.app.source.ready.set()
            self.app.source.connected.set()
            self.app.source.emit('source_ready', 'Ready again')
            self.app._poll()
            self.assertFalse(engine.enabled)
            self.assertEqual(self.app.rf_controls[0]['button'].cget('text'), 'Enable RF')


    def test_format_presets_reorder_include_and_persist(self):
        self.assertEqual(self.app.format_preset.get(), 'Frequency first')
        self.app.format_preset.set('Callsign first')
        self.app._format_preset_selected()
        self.assertEqual(self.app.variables['announcement_intro'].get(), 'New DX')
        self.assertIn('New DX. WB4IUY/P. 14025.5 kHz.', self.app.format_example.get())
        self.app._move_format('intro', 1)
        self.assertEqual(self.app.variables['announcement_order'].get(), 'callsign,intro,frequency')
        self.assertEqual(int(self.app.format_rows['intro']['row'].grid_info()['row']), 1)
        self.assertEqual(str(self.app.format_rows['callsign']['up'].cget('state')), 'disabled')
        self.app.variables['include_intro'].set(False)
        self.app.variables['speak_units'].set(False)
        self.app.variables['frequency_unit'].set('MHz')
        self.assertEqual(self.app.format_example.get(), 'Example: WB4IUY/P. 14.0255.')
        self.assertEqual(self.app.format_preset.get(), 'Custom')
        self.app._apply()
        saved = load_settings()
        self.assertEqual(saved.announcement_order, 'callsign,intro,frequency')
        self.assertFalse(saved.include_intro)
        self.assertFalse(saved.speak_units)
        self.app.variables['include_frequency'].set(False)
        self.assertEqual(str(self.app.format_rows['frequency']['content'].cget('state')), 'disabled')
        self.app.variables['include_frequency'].set(True)
        self.assertFalse(self.app.variables['speak_units'].get())

    def test_format_preview_does_not_save_pending_source_edits(self):
        self.app.settings = replace(self.app.settings, preview_device='local')
        self.app.variables['host'].set('pending.example')
        self.app.variables['announcement_intro'].set('My station DX')
        with patch.object(self.app, '_apply', side_effect=AssertionError('Applied pending settings')), \
             patch.object(self.app.engine, 'preview') as preview:
            self.app._preview_format()
        settings = preview.call_args.kwargs['settings']
        self.assertEqual(settings.announcement_intro, 'My station DX')
        self.assertNotEqual(settings.host, 'pending.example')
        self.assertEqual(self.app.variables['host'].get(), 'pending.example')
        self.assertEqual(self.app.settings.announcement_intro, 'New DX on')
        for part in ('intro', 'callsign', 'frequency'):
            self.app.variables['include_' + part].set(False)
        self.assertIn('at least one', self.app.format_example.get())
        with self.assertRaises(ValueError):
            self.app._preview_format()

    def test_format_edits_stop_active_output_without_reconnecting(self):
        from unittest.mock import Mock
        source = Mock()
        self.app.source = source
        self.app.engine.local_enabled = True
        self.app.variables['announcement_intro'].set('My DX')
        self.assertFalse(self.app.engine.local_enabled)
        self.assertTrue(self.app.engine.cancel.is_set())
        source.stop.assert_not_called()
        self.app.source = None


    def test_profile_edit_rename_delete_and_create_do_not_overwrite_other_profiles(self):
        self.app.profile_name.set('First')
        self.app.variables['host'].set('first.example')
        self.app._save_profile()
        first_id = self.app.selected_profile_id
        self.assertEqual(self.app.save_profile_button.cget('text'), 'Save changes')
        self.app._new_profile()
        self.assertEqual(self.app.save_profile_button.cget('text'), 'Save new profile')
        self.assertEqual(str(self.app.delete_profile_button.cget('state')), 'disabled')
        self.app.profile_name.set('Second')
        self.app.variables['host'].set('second.example')
        self.app._save_profile()
        self.app.profile_choice.set('First')
        # An incomplete radio edit must not block source profile management.
        self.app.variables['lead_ms'].set('unfinished')
        self.app._select_profile()
        self.app.profile_name.set('First renamed')
        self.app.variables['host'].set('edited.example')
        self.app._save_profile()
        self.assertEqual(self.app.selected_profile_id, first_id)
        self.assertEqual(len(self.app.profile_store.profiles), 2)
        self.assertEqual(set(self.app.live_profile_picker.cget('values')), {'First renamed', 'Second'})
        self.assertEqual(self.app.variables['lead_ms'].get(), 'unfinished')
        with patch('dxtalker.app.messagebox.askyesno', return_value=False):
            self.app._delete_profile()
        self.assertEqual(len(self.app.profile_store.profiles), 2)
        with patch('dxtalker.app.messagebox.askyesno', return_value=True):
            self.app._delete_profile()
        self.assertEqual([p['name'] for p in self.app.profile_store.profiles], ['Second'])
        self.assertEqual(tuple(self.app.live_profile_picker.cget('values')), ('Second',))
        self.assertIsNone(self.app.selected_profile_id)
        self.assertEqual(self.app.profile_choice.get(), '')
        self.assertEqual(self.app.secret.get(), '')
        self.assertFalse(self.app.engine.enabled)

    def test_source_and_ptt_show_only_relevant_groups_without_losing_values(self):
        self.assertEqual(self.app.tcp_source_fields.winfo_manager(), 'grid')
        self.assertEqual(self.app.https_source_fields.winfo_manager(), '')
        self.app.variables['host'].set('keep.example')
        self.app.variables['source_type'].set('HTTPS JSON')
        self.app._source_type_changed(clear_secret=True)
        self.assertEqual(self.app.tcp_source_fields.winfo_manager(), '')
        self.assertEqual(self.app.https_source_fields.winfo_manager(), 'grid')
        self.assertEqual(self.app.variables['host'].get(), 'keep.example')
        self.assertEqual(self.app.serial_ptt_fields.winfo_manager(), '')
        self.app.variables['serial_port'].set('COM9')
        self.app.variables['ptt_method'].set('RTS')
        self.assertEqual(self.app.serial_ptt_fields.winfo_manager(), 'grid')
        self.app.variables['ptt_method'].set('VOX')
        self.assertEqual(self.app.serial_ptt_fields.winfo_manager(), '')
        self.assertEqual(self.app.variables['serial_port'].get(), 'COM9')
        self.assertLess(int(self.app.field_widgets['lead_ms'].cget('width')), 15)
        self.assertLess(int(self.app.field_widgets['host'].cget('width')), 45)

    def test_new_profile_stops_feed_and_clears_previous_display_and_credentials(self):
        from unittest.mock import Mock
        source = Mock()
        self.app.source = source
        self.app._add_spot(self.spot())
        self.app._append_raw('previous session')
        self.app.secret.set('synthetic secret')
        self.app.command.set('show/dx')
        self.app._new_profile()
        source.stop.assert_called_once()
        self.assertIsNone(self.app.source)
        self.assertFalse(self.app.spots)
        self.assertFalse(self.app.raw_lines)
        self.assertEqual(self.app.command.get(), '')
        self.assertEqual(self.app.secret.get(), '')
        self.assertFalse(self.app.remember_secret.get())


    def test_failed_secret_unlock_still_allows_profile_editing_and_deletion(self):
        self.app.profile_name.set('Working')
        self.app._save_profile()
        def protector(value, decrypt=False):
            if decrypt:
                raise ValueError('Synthetic credential unlock failure')
            return 'encrypted-fixture'
        self.app.profile_store.protector = protector
        locked = self.app.profile_store.save('Locked', replace(self.app.settings, host='locked.example'), secret='synthetic', remember=True)
        self.app._refresh_profiles()
        self.app.profile_choice.set('Locked')
        with patch('dxtalker.app.messagebox.showwarning') as warning:
            self.app._select_profile()
        warning.assert_called_once()
        self.assertEqual(self.app.profile_choice.get(), 'Locked')
        self.assertEqual(self.app.profile_name.get(), 'Locked')
        self.assertEqual(self.app.selected_profile_id, locked['id'])
        self.assertEqual(self.app.variables['host'].get(), 'locked.example')
        self.assertEqual(self.app.secret.get(), '')
        self.assertFalse(self.app.remember_secret.get())
        # Loading alone must not erase the stored credential.
        self.assertEqual(next(p for p in self.app.profile_store.profiles if p['id'] == locked['id'])['secret'], 'encrypted-fixture')
        with patch('dxtalker.app.messagebox.askyesno', return_value=True) as ask:
            self.app._delete_profile()
        self.assertIn("'Locked'", ask.call_args.args[1])
        self.assertEqual([p['name'] for p in self.app.profile_store.profiles], ['Working'])


    def test_listening_is_armed_before_the_first_connection_packet(self):
        app=self.app
        class Source:
            def __init__(self, settings, emit, secret):
                self.emit=emit;self.ready=threading.Event();self.connected=threading.Event()
            def start(self):
                assert app.engine.local_enabled
                self.emit('spot',app_test_spot)
            def stop(self):pass
        app_test_spot=self.spot()
        app.variables['preview_device'].set('local')
        app._apply()
        app._listen()
        self.assertTrue(app.engine.local_enabled)
        with patch('dxtalker.app.SourceClient',Source),patch.object(app.engine,'offer') as offer:
            app._connect();app._poll()
        offer.assert_called_once_with(app_test_spot)
        self.assertTrue(app.engine.local_enabled)
        self.assertFalse(app.engine.enabled)


    def test_collection_qr_starts_with_all_profiles_and_paginates(self):
        from tkinter import ttk
        import tkinter as tk
        self.app.profile_store.save('Home',Settings(),'secret',False)
        self.app.profile_store.save('Travel',Settings(),'secret',False)
        self.app._profile_qr()
        dialog=next(w for w in self.root.winfo_children() if isinstance(w,tk.Toplevel))
        def descendants(widget):
            for child in widget.winfo_children():
                yield child
                yield from descendants(child)
        picker=next(w for w in descendants(dialog) if isinstance(w,tk.Listbox))
        self.assertEqual(picker.curselection(),(0,1))
        generate=next(w for w in descendants(dialog) if isinstance(w,ttk.Button) and w.cget('text')=='Generate QR codes')
        with patch("dxtalker.app.messagebox.showerror", side_effect=AssertionError("QR generation failed")):
            generate.invoke()
        self.root.update()
        self.assertTrue(any(isinstance(w,ttk.Label) and str(w.cget('textvariable')) for w in descendants(dialog)))
        dialog.destroy()

    def test_elevenlabs_window_requires_no_key_and_does_not_generate_on_open(self):
        from dxtalker.elevenlabs_ui import ElevenLabsDialog
        with patch('dxtalker.elevenlabs_ui.SharedSpeech') as client:
            dialog=ElevenLabsDialog(self.app);self.root.update()
            client.assert_not_called()
            self.assertNotIn('API key',self.app.variables)
            self.assertNotIn('API key',dialog.values)
            dialog.close()


    def test_shared_speech_provider_has_voice_choices_and_no_tester_keys(self):
        self.app.variables['speech_provider'].set('ElevenLabs')
        self.app._speech_provider_changed()
        self.assertTrue(self.app.eleven_speech_fields.grid_info())
        self.assertEqual(str(self.app.field_widgets['speech_rate'].cget('state')),'disabled')
        self.assertEqual(self.app._read_settings().speech_provider,'ElevenLabs')
        self.assertNotIn('api_key',self.app.variables)
        with patch('dxtalker.cloud_speech.SharedSpeech') as client:
            client.return_value.voices.return_value={'Pilot voice (voiceA)':'voiceA'}
            self.app._load_shared_voices()
            import time
            deadline=time.monotonic()+2
            while self.app.shared_voices_loading and time.monotonic()<deadline:
                self.app._poll();time.sleep(.01)
        self.assertEqual(self.app.eleven_voices,{'Pilot voice (voiceA)':'voiceA'})
