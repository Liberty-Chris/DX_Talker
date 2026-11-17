"""User workflows: isolated actions, durable drafts and explicit output ownership."""
from dataclasses import replace
import os
import sys
import threading
import unittest
from unittest.mock import Mock, patch

from test_app import AppTests as _Fixtures
from dxtalker.models import load_settings, Settings


@unittest.skipUnless(sys.platform=='win32' or os.environ.get('DISPLAY'),'Requires desktop display')
class UsabilityTests(unittest.TestCase):
    def test_failover_connect_snapshots_saved_nodes_without_cross_using_credentials(self):
        app=self.app
        app.profile_store.protector=lambda text,decrypt=False: text[7:] if decrypt else 'locked:'+text
        app.profile_store.save('Backup',replace(app.settings,host='backup.invalid',login='K2BBB'),'backup-password',True)
        app.variables['cluster_failover'].set(True)
        app.secret.set('primary-password')
        source=Mock();source.connected=threading.Event()
        with patch('dxtalker.app.SourceClient',return_value=source) as constructor:app._connect()
        self.assertTrue(constructor.call_args.args[0].cluster_failover)
        self.assertEqual(constructor.call_args.args[2],'primary-password')
        name,settings,secret=constructor.call_args.kwargs['alternates'][0]
        self.assertEqual((name,settings.host,settings.login,secret),('Backup','backup.invalid','K2BBB','backup-password'))
        self.assertFalse(app.engine.enabled)

    def test_late_packets_are_bound_to_source_session(self):
        from types import SimpleNamespace
        app=self.app
        app.source=SimpleNamespace(session_epoch=2,stop=lambda:None,connected=threading.Event(),ready=threading.Event(),signed_in=threading.Event(),settings=app.settings)
        generation=app.source_generation
        app.emit('source_event',(generation,'spot_session',(1,self.spot())))
        app._poll()
        self.assertFalse(app.spots)

    def test_session_packet_events_stay_bounded_and_do_not_hide_control_events(self):
        app=self.app;generation=app.source_generation
        app.emit('source_event',(generation,'spot_session',(1,self.spot())))
        app.emit('source_event',(generation,'raw_session',(1,'synthetic')))
        self.assertEqual(app.events.get_nowait()[1][1],'spot_session')
        self.assertEqual(app.raw_events.get_nowait()[1][1],'raw_session')

    setUp=_Fixtures.setUp
    tearDown=_Fixtures.tearDown
    spot=_Fixtures.spot

    def test_words_and_attention_sound_autosave_without_applying_rf_option(self):
        app = self.app
        app.variables['rf_auto_reconnect'].set(True)
        self.assertFalse(app.settings.rf_auto_reconnect)
        panel = app.filter_editor
        panel.variables['special_keywords'].set('Cobia,county hunter')
        panel.variables['special_keywords_only'].set(True)
        panel.variables['special_alert'].set('Double ding')
        saved = load_settings()
        self.assertEqual(saved.special_keywords, 'Cobia,county hunter')
        self.assertTrue(saved.special_keywords_only)
        self.assertEqual(saved.special_alert, 'Double ding')
        self.assertFalse(saved.rf_auto_reconnect)
        self.assertFalse(app.engine.enabled)
        app._apply()
        self.assertTrue(load_settings().rf_auto_reconnect)
        self.assertFalse(app.engine.enabled)

    def test_source_readiness_is_ordered_before_loss_without_waiting_for_ui_poll(self):
        app = self.app
        class Source:
            def __init__(self, settings, emit, secret, **kwargs): self.emit=emit; self.connected=threading.Event()
            def start(self): pass
            def stop(self): pass
        with patch('dxtalker.app.SourceClient', Source): app._connect()
        with app.engine.lock:
            app.engine.settings=replace(app.settings, rf_auto_reconnect=True)
            app.engine.enabled=True
            app.source.emit('source_lost','Source lost')
            app.source.emit('source_ready','Receiving DX spots')
            self.assertTrue(app.engine.reconnect_ready)
            app.source.emit('source_lost','Source lost again')
            self.assertFalse(app.engine.reconnect_ready)
            # Processing the old ready event must not rearm recovery.
            app._poll()
            self.assertFalse(app.engine.reconnect_ready)

    def test_radio_apply_preserves_rf_and_monitor_after_validated_cleanup(self):
        app = self.app
        with app.engine.lock, patch.object(app.engine, 'enable') as enable:
            app.engine.enabled = True
            app.engine.local_enabled = True
            app.engine.local_muted = True
            app.variables['radio_device'].set('radio')
            app.variables['preview_device'].set('local')
            app.variables['cw_text'].set('E')
            app._apply()
            enable.assert_called_once_with(local=True, muted=True)
            self.assertEqual(app.save_status.get(), 'Radio changes applied.')
            self.assertEqual(str(app.save_button.cget('state')), 'disabled')
            self.assertEqual(app.save_button.cget('text'), 'Radio settings saved')
        self.assertEqual(load_settings().cw_text, 'E')

    def test_invalid_radio_apply_leaves_running_output_alone(self):
        app = self.app
        with app.engine.lock:
            app.engine.enabled = True
            app.variables['radio_device'].set('')
            app.variables['cw_text'].set('E')
            with self.assertRaises(ValueError): app._apply()
            self.assertTrue(app.engine.enabled)
            self.assertFalse(app.engine.cancel.is_set())

    def test_fault_during_pending_apply_prevents_rf_resumption(self):
        app = self.app
        with app.engine.lock, patch.object(app.engine, 'enable') as enable:
            app.engine.enabled = True
            app.engine.busy = True
            app.variables['radio_device'].set('radio')
            app.variables['cw_text'].set('E')
            app._apply()
            app.engine.fault_generation += 1
            app.engine.busy = False
            self.root.after(100, self.root.quit); self.root.mainloop()
            enable.assert_not_called()
            self.assertFalse(app.engine.enabled)

    def test_source_loss_during_apply_validation_cannot_restore_rf(self):
        app = self.app
        with app.engine.lock, patch.object(app.engine, 'enable') as enable:
            app.engine.enabled = True
            app.variables['radio_device'].set('radio')
            app.variables['cw_text'].set('E')
            with patch.object(Settings, 'validate_rf', side_effect=lambda: app.engine.stop('Source lost', defer_cleanup=True)):
                app._apply()
            enable.assert_not_called()
            self.assertFalse(app.engine.enabled)

    def test_scheduled_id_dialog_add_edit_remove_and_preview_are_radio_drafts(self):
        from dxtalker.id_schedule import new_entry
        import json
        import tkinter as tk
        app = self.app
        panel = next(w for w in app.tabs['Identification'].winfo_children() if w.winfo_class() == 'TLabelframe' and w.cget('text') == 'Scheduled voice IDs')
        controls = next(w for w in panel.winfo_children() if w.winfo_class() == 'TFrame')
        buttons = {w.cget('text'): w for w in controls.winfo_children()}
        buttons['+ Add voice ID'].invoke(); self.root.update()
        dialog = next(w for w in self.root.winfo_children() if isinstance(w, tk.Toplevel))
        inputs = {int(w.grid_info()['row']): w for w in dialog.winfo_children() if w.winfo_class() == 'TEntry' and 'row' in w.grid_info()}
        inputs[0].delete(0, 'end'); inputs[0].insert(0, 'Meeting reminder')
        inputs[2].insert(0, 'Club meeting tonight')
        actions = next(w for w in dialog.winfo_children() if w.winfo_class() == 'TFrame' and int(w.grid_info().get('row', -1)) == 17)
        next(w for w in actions.winfo_children() if w.cget('text') == 'Save voice ID').invoke()
        ids = json.loads(app.variables['voice_ids'].get())
        self.assertEqual(len(ids), 1); self.assertEqual(ids[0]['name'], 'Meeting reminder')
        self.assertEqual(load_settings().voice_ids, '[]')
        self.assertEqual(str(app.save_button.cget('state')), 'normal')
        tree = next(w for w in panel.winfo_children() if w.winfo_class() == 'Treeview')
        tree.selection_set(ids[0]['id'])
        with patch.object(app, '_start_preview') as preview:
            buttons['Preview locally'].invoke()
            self.assertEqual(preview.call_args.kwargs['settings'].voice_text, 'Club meeting tonight')
        buttons['Remove'].invoke()
        self.assertEqual(app.variables['voice_ids'].get(), '[]')

    def test_rf_and_local_controls_work_independently_and_spot_actions_are_visible(self):
        app=self.app
        with app.engine.lock:
            app.engine.configure(replace(app.settings,radio_device='radio',preview_device='local',cw_text='E'))
            app.variables['preview_device'].set('local')
            app._enable()
            app._listen()
            self.assertTrue(app.engine.enabled);self.assertTrue(app.engine.local_enabled)
            self.assertEqual(app.listening_controls[0]['button'].cget('text'),'Monitoring RF')
            app._listen()
            self.assertTrue(app.engine.enabled);self.assertTrue(app.engine.local_muted)
            app._listen()
            self.assertTrue(app.engine.enabled);self.assertFalse(app.engine.local_muted)
            app._enable()
            self.assertFalse(app.engine.enabled);self.assertTrue(app.engine.local_enabled)
            app._enable()
            self.assertTrue(app.engine.enabled);self.assertTrue(app.engine.local_enabled)
            app._stop()
            self.assertFalse(app.engine.enabled);self.assertFalse(app.engine.local_enabled)
        self.assertEqual(app.spot_station_button.winfo_manager(),'pack')
        self.assertEqual(app.spot_myself_button.winfo_manager(),'pack')
        with patch.object(app,'_spot_dialog') as open_dialog:
            app.spot_station_button.invoke();open_dialog.assert_called_with(False)
            app.spot_myself_button.invoke();open_dialog.assert_called_with(True)
        self.root.deiconify();self.root.geometry('900x600');self.root.update()
        for button in (app.spot_station_button,app.spot_myself_button):
            self.assertTrue(button.winfo_viewable())
            self.assertLessEqual(button.winfo_rootx()+button.winfo_width(),self.root.winfo_rootx()+self.root.winfo_width())

    def test_connect_ignores_incomplete_radio_and_speech_edits(self):
        app=self.app
        app.variables['host'].set('test.invalid')
        app.variables['lead_ms'].set('unfinished')
        app.variables['speech_rate'].set('unfinished')
        source=Mock();source.connected=threading.Event()
        with patch('dxtalker.app.SourceClient',return_value=source) as constructor:
            app._connect()
        source.start.assert_called_once()
        self.assertEqual(constructor.call_args.args[0].host,'test.invalid')
        self.assertEqual(constructor.call_args.args[0].lead_ms,Settings().lead_ms)
        self.assertEqual(load_settings().speech_rate,0)
        self.assertFalse(app.engine.enabled)

    def test_cw_preview_uses_its_fields_without_saving_source_or_radio(self):
        app=self.app
        app.variables['port'].set('unfinished')
        app.variables['lead_ms'].set('unfinished')
        app.variables['speech_rate'].set('unfinished')
        app.variables['preview_device'].set('local')
        app.variables['cw_text'].set('E')
        with patch.object(app.engine,'preview') as preview:
            app._preview('cw')
        snapshot=preview.call_args.kwargs['settings']
        self.assertEqual(snapshot.cw_text,'E')
        self.assertEqual(snapshot.preview_device,'local')
        self.assertEqual(load_settings().cw_text,'')
        self.assertEqual(load_settings().port,7373)
        self.assertEqual(app.variables['lead_ms'].get(),'unfinished')

    def test_autosave_keeps_rf_and_connection_and_reports_bad_field(self):
        app=self.app
        source=Mock();app.source=source
        with app.engine.lock:
            app.engine.enabled=True
            app.variables['speech_rate'].set('unfinished')
            app.variables['frequency_unit'].set('MHz')
            app._flush_preferences()
            self.assertTrue(app.engine.enabled)
            self.assertFalse(app.engine.cancel.is_set())
            self.assertEqual(load_settings().frequency_unit,'MHz')
            self.assertEqual(load_settings().speech_rate,0)
            self.assertIn('speech rate',next(iter(app.preference_errors.values())))
            self.assertEqual(app.variables['speech_rate'].get(),'unfinished')
            source.stop.assert_not_called()
        app.source=None

    def test_stop_cancels_a_pending_output_transition(self):
        app=self.app
        action=Mock()
        with app.engine.lock:
            app.engine.busy=True
            app._when_idle(action,stop=True)
            app._stop()
            app.engine.busy=False
            self.root.after(100,self.root.quit);self.root.mainloop()
            action.assert_not_called()
            self.assertFalse(app.engine.enabled)
            self.assertFalse(app.engine.local_enabled)

    def test_radio_draft_survives_without_becoming_active(self):
        from dxtalker.preferences import load_radio_draft
        app=self.app
        app.variables['lead_ms'].set('unfinished')
        app.variables['radio_device'].set('draft radio')
        app._save_radio_draft()
        draft=load_radio_draft()
        self.assertEqual(draft['lead_ms'],'unfinished')
        self.assertEqual(draft['radio_device'],'draft radio')
        self.assertNotIn('password',draft)
        self.assertNotIn('enabled',draft)
        self.assertEqual(load_settings().radio_device,'')
        self.assertFalse(app.engine.enabled)

    def test_default_radio_draft_is_empty_and_delete_undo_keeps_secret(self):
        from dxtalker.preferences import load_radio_draft
        app=self.app;app._save_radio_draft()
        self.assertEqual(load_radio_draft(),{})
        item=app.profile_store.save('Private',app.settings)
        app.selected_profile_id=item['id']
        with patch.object(app.profile_store,'_forget') as forget:
            app._delete_profile()
            forget.assert_not_called()
            app._undo()
            self.assertEqual(app.profile_store.profiles,[item])
            forget.assert_not_called()

    def test_unmute_focus_is_green_in_every_theme(self):
        from dxtalker.appearance import PALETTES
        app=self.app
        with app.engine.lock:
            app.engine.local_enabled=True;app.engine.local_muted=True
            item=app.listening_controls[0];item['focus']=True
            for name,palette in PALETTES.items():
                app.theme.set(name);app._render_connections()
                style=item['button'].cget('style')
                fill=self.root.tk.call('ttk::style','lookup',style,'-bordercolor')
                self.assertEqual(fill,palette['positive'])
                self.assertEqual(item['button'].cget('text'),'Unmute')

    def test_source_loss_invalidates_pending_rf_enable(self):
        app=self.app
        class Source:
            def __init__(self,settings,emit,secret,**kwargs):self.emit=emit;self.connected=threading.Event()
            def start(self):pass
            def stop(self):pass
        with patch('dxtalker.app.SourceClient',Source):app._connect()
        action=Mock()
        with app.engine.lock:
            app.engine.busy=True;app._when_idle(action)
            app.source.emit('source_lost','Fixture disconnected')
            app.engine.busy=False
            self.root.after(100,self.root.quit);self.root.mainloop()
            action.assert_not_called()
            self.assertFalse(app.engine.enabled)

    def test_compact_view_keeps_filter_context_and_all_pages_reachable(self):
        app=self.app
        self.root.deiconify();self.root.geometry('900x600');self.root.update()
        app._responsive_layout();self.root.update()
        self.assertTrue(app.live_hint.winfo_ismapped())
        app.variables['text_size'].set('18');app._flush_preferences();self.root.update()
        self.assertTrue(app.nav_frame.winfo_ismapped())
        self.assertEqual(set(app.nav_picker.cget('values')),set(app.tabs))
        app._select_page('Listening filters');self.root.update()
        self.assertTrue(app.filter_editor.frame.winfo_ismapped())

    def test_profile_drafts_exclude_passwords_and_recover_unfinished_port(self):
        import json
        from dxtalker.models import settings_path
        app=self.app
        app.variables['port'].set('unfinished');app.secret.set('synthetic-secret')
        app.profile_name.set('In progress');app._persist_profile_drafts()
        raw=settings_path().with_name('profile-drafts.json').read_text()
        self.assertNotIn('synthetic-secret',raw)
        self.assertEqual(json.loads(raw)['new']['connection']['port'],'unfinished')
        app.profile_drafts.clear();app._load_profile_drafts()
        self.assertEqual(app.variables['port'].get(),'unfinished')
        self.assertEqual(app.profile_name.get(),'In progress')

    def test_switch_cluster_uses_one_action_without_applying_radio_draft(self):
        app=self.app
        class Source:
            def __init__(self,settings,emit,secret,**kwargs):self.settings=settings;self.connected=threading.Event();self.connected.set();self.stop=Mock()
            def start(self):pass
        with patch('dxtalker.app.SourceClient',Source):
            app._connect()
            previous=app.source
            app.variables['host'].set('other.invalid');app.variables['lead_ms'].set('unfinished')
            app._render_connections()
            self.assertEqual(app.connection_controls[0]['button'].cget('text'),'Switch cluster')
            app._connection_action()
        previous.stop.assert_called_once()
        self.assertEqual(app.source.settings.host,'other.invalid')
        self.assertEqual(app.settings.lead_ms,Settings().lead_ms)
        self.assertEqual(app.variables['lead_ms'].get(),'unfinished')
        self.assertFalse(app.engine.enabled)

del _Fixtures
