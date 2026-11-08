import sys
import threading
import unittest
from types import SimpleNamespace
from dxtalker.power import OutputPower, DesktopPowerObserver, WindowsPowerAPI, CONTINUOUS, SYSTEM, DISPLAY
from dxtalker.models import Settings
from dataclasses import replace


class PowerTests(unittest.TestCase):
    def test_requests_only_active_output_and_restores_on_the_same_thread(self):
        calls=[]; events=[]
        api=SimpleNamespace(request=lambda flags:calls.append((threading.get_ident(),flags)) or True)
        with OutputPower(lambda *event:events.append(event),api) as power:
            power.set_active(False,'Computer')
            power.set_active(True,'Off')
            self.assertFalse(calls)
            power.set_active(True,'Computer')
            power.set_active(True,'Computer')
            power.set_active(True,'Computer and display')
            power.set_active(False,'Computer and display')
        self.assertEqual([value for thread,value in calls],[CONTINUOUS|SYSTEM,CONTINUOUS|SYSTEM|DISPLAY,CONTINUOUS])
        self.assertEqual({thread for thread,value in calls},{threading.get_ident()})
        self.assertTrue(all(name=='power_event' for name,value in events))

    def test_exception_and_failed_mode_change_release_previous_request(self):
        calls=[]
        def request(flags):
            calls.append(flags)
            return flags != CONTINUOUS|SYSTEM|DISPLAY
        with self.assertRaises(RuntimeError):
            with OutputPower(lambda *event:None,SimpleNamespace(request=request)) as power:
                power.set_active(True,'Computer')
                power.set_active(True,'Computer and display')
                raise RuntimeError('synthetic')
        self.assertEqual(calls[-1],CONTINUOUS)

    def test_screensaver_state_changes_and_gaps_have_no_keyboard_or_device_data(self):
        state=[False];tick=[0];records=[]
        api=SimpleNamespace(screensaver=lambda:state[0])
        observer=DesktopPowerObserver(lambda event,**data:records.append((event,data)),api,lambda:tick[0])
        observer.sample();observer.sample()
        state[0]=True;tick[0]=2;observer.sample()
        state[0]=False;tick[0]=25;observer.sample()
        self.assertEqual([data['active'] for event,data in records if data['code']=='screensaver_state'],[False,True,False])
        self.assertEqual([data['seconds'] for event,data in records if data['code']=='observation_gap'],[23])
        self.assertTrue(all(set(data)<= {'code','active','seconds'} for event,data in records))

    def test_keep_awake_default_off_and_invalid_values_rejected(self):
        self.assertEqual(Settings().keep_awake,'Off')
        with self.assertRaises(ValueError):replace(Settings(),keep_awake='simulate keys').validate()

    @unittest.skipUnless(sys.platform=='win32','Native Windows API only')
    def test_native_request_and_release_bindings(self):
        api=WindowsPowerAPI()
        try:self.assertTrue(api.request(CONTINUOUS|SYSTEM))
        finally:self.assertTrue(api.request(CONTINUOUS))
        self.assertIn(api.screensaver(),(True,False,None))
