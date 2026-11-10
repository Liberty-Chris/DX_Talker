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
    setUp=_Fixtures.setUp
    tearDown=_Fixtures.tearDown

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
            def __init__(self,settings,emit,secret):self.emit=emit;self.connected=threading.Event()
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
            def __init__(self,settings,emit,secret):self.settings=settings;self.connected=threading.Event();self.connected.set();self.stop=Mock()
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
