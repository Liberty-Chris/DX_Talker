"""Idle repaint and cleanup regressions use synthetic devices only."""
from dataclasses import replace
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from test_app import AppTests as _Fixtures


@unittest.skipUnless(sys.platform=='win32' or os.environ.get('DISPLAY'),'Requires desktop display')
class IdleUITests(unittest.TestCase):
    setUp=_Fixtures.setUp
    tearDown=_Fixtures.tearDown
    spot=_Fixtures.spot

    def test_idle_polls_do_not_rewrite_labels_buttons_or_meter(self):
        from contextlib import ExitStack
        app=self.app
        app._poll();self.root.update()
        targets=[(app.empty_spots,'set'),(app.routing_hint,'set'),(app.receive_threshold,'set'),
                 (app.receive_status,'set'),(app.queue_summary,'set'),(app.filter_summary,'set'),
                 (app.receive_level,'coords'),(app.empty_label,'place'),(app.empty_label,'place_forget'),
                 (app.catch_up_button,'configure'),(app.receive_test_button,'configure')]
        targets.extend((button,'configure') for button,_ in app.capability_buttons)
        with ExitStack() as stack:
            writes=[stack.enter_context(patch.object(widget,method,wraps=getattr(widget,method))) for widget,method in targets]
            for _ in range(20):app._poll()
            self.assertTrue(all(write.call_count==0 for write in writes),[write.call_count for write in writes])

    def test_changed_selection_spots_queue_and_route_update_without_delay(self):
        app=self.app
        app._poll()
        app._add_spot(replace(self.spot(),comment='FT8',mode='FT8'));row=next(iter(app.spots));app.tree.selection_set(row)
        app._poll()
        self.assertEqual(app.empty_label.winfo_manager(),'')
        preview=next(button for button,action in app.capability_buttons if action=='preview')
        self.assertEqual(str(preview.cget('state')),'normal')
        with patch.object(app.engine,'queue_status',return_value=(2,8,0)):
            app._poll()
        self.assertIn('2 waiting',app.queue_summary.get())
        self.assertEqual(str(app.catch_up_button.cget('state')),'normal')
        app._clear_spots();app._poll()
        self.assertEqual(app.empty_label.winfo_manager(),'place')
        self.assertEqual(str(preview.cget('state')),'disabled')
        app.settings=replace(app.settings,preview_device='same',radio_device='same')
        app._poll()
        self.assertIn('may key VOX',app.routing_hint.get())

    def test_hidden_receive_meter_updates_when_measurement_changes(self):
        app=self.app
        with patch.object(app.engine.monitor,'snapshot',return_value=('busy',-30.0,0)):
            app._poll()
        self.assertIn('-30 dBFS',app.receive_threshold.get())
        self.assertEqual(app.receive_level.coords(app.receive_fill),[0.0,0.0,150.0,24.0])
        app.settings=replace(app.settings,receive_threshold_db=-25)
        with patch.object(app.engine.monitor,'snapshot',return_value=('clear',-45.0,0)):
            app._poll()
        self.assertIn('Threshold: -25',app.receive_threshold.get())
        self.assertEqual(app.receive_level.coords(app.receive_mark),[175.0,0.0,175.0,24.0])

    def test_smoke_assertion_failure_releases_logs_before_temporary_cleanup(self):
        from dxtalker.selftest import close_smoke_app
        path=self.app.diagnostics.directory/'diagnostics.jsonl'
        try:
            try:
                raise AssertionError('Synthetic performance failure')
            finally:
                close_smoke_app(self.app)
        except AssertionError as exc:
            self.assertEqual(str(exc),'Synthetic performance failure')
        self.assertTrue(self.app.diagnostics.closed.is_set())
        path.rename(path.with_suffix('.closed'))


del _Fixtures
