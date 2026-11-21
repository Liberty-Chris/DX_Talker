from array import array
from dataclasses import replace
import threading
import time
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from dxtalker.receiver import ReceiveMonitor
from dxtalker.models import Settings
from test_engine import EngineTests as _EngineTests, FakeAudio, wait_for
from dxtalker.audio import Cancelled


class DetectorTests(unittest.TestCase):
    def test_own_transmit_and_switching_audio_do_not_create_a_traffic_hold(self):
        from dxtalker.receiver import ReceiveCancel
        tick=[10.0];monitor=ReceiveMonitor(clock=lambda:tick[0])
        monitor.stream=SimpleNamespace(active=True);monitor._started_at=0
        quiet=array('h',[0]*1024).tobytes();loud=array('h',[6000]*1024).tobytes()
        monitor.feed(quiet);self.assertTrue(monitor.ready())
        cancel=ReceiveCancel(threading.Event(),monitor);cancel.ignore_busy=True
        monitor.transmit_started();monitor.feed(loud)
        self.assertEqual(monitor.snapshot()[0],'transmitting');self.assertFalse(cancel.is_set())
        monitor.transmit_ended()
        for instant in (10.2,10.9):
            tick[0]=instant;monitor.feed(loud,discontinuity=True)
            self.assertEqual(monitor.snapshot()[0],'settling');self.assertFalse(monitor.ready())
            self.assertFalse(monitor.traffic_pending)
        tick[0]=11.0
        self.assertEqual(monitor.snapshot()[0],'settling')  # A fresh receive frame is required.
        monitor.feed(quiet)
        self.assertEqual(monitor.snapshot(),('clear',monitor.level,0));self.assertTrue(monitor.ready())
        monitor.transmit_started();monitor.feed(b'\0\0',fault=True)
        self.assertTrue(cancel.is_set());self.assertIsNotNone(cancel.fault)

    def test_startup_is_clear_on_first_quiet_frame_and_real_traffic_requires_five_seconds(self):
        tick=[0.0];monitor=ReceiveMonitor(clock=lambda:tick[0])
        monitor.stream=SimpleNamespace(active=True);monitor._started_at=0
        def feed(level):monitor.feed(array('h',[level]*1024).tobytes())
        self.assertFalse(monitor.ready());self.assertEqual(monitor.snapshot()[0],'starting')
        feed(0);self.assertTrue(monitor.ready())
        tick[0]=1;feed(6000);self.assertEqual(monitor.snapshot()[0],'busy')
        tick[0]=2;feed(0);self.assertEqual(monitor.snapshot()[2],5)
        for instant in range(3, 7):
            tick[0] = instant
            feed(0)
        tick[0]=6.9;feed(0);self.assertFalse(monitor.ready())
        tick[0]=7;feed(0);self.assertTrue(monitor.ready())
        tick[0]=8;feed(6000);self.assertFalse(monitor.ready())
        tick[0]=9;feed(0)
        for instant in range(10, 14):
            tick[0] = instant
            feed(0)
        tick[0]=13.9;feed(0);self.assertFalse(monitor.ready())
        tick[0]=14;feed(0);self.assertTrue(monitor.ready())
        tick[0]=24
        with self.assertRaisesRegex(ValueError,'monitoring failed'):monitor.ready()
        feed(0);monitor.feed(b'\0\0',fault=True)
        with self.assertRaises(ValueError):monitor.ready()
        monitor.fault=False;monitor.stream.active=False
        with self.assertRaises(ValueError):monitor.ready()

    def test_real_audio_after_settling_starts_hold_and_new_traffic_restarts_it(self):
        tick=[10.0];monitor=ReceiveMonitor(clock=lambda:tick[0])
        monitor.stream=SimpleNamespace(active=True);monitor._started_at=0
        def feed(level):monitor.feed(array('h',[level]*1024).tobytes())
        feed(0);monitor.transmit_started();feed(6000);monitor.transmit_ended()
        tick[0]=11;feed(6000);self.assertEqual(monitor.snapshot()[0],'busy')
        tick[0]=12;feed(0);self.assertEqual(monitor.snapshot()[2],5)
        tick[0]=15;feed(6000);self.assertEqual(monitor.snapshot()[0],'busy')
        tick[0]=16;feed(0)
        for instant in range(17, 21):
            tick[0] = instant
            feed(0)
        tick[0]=20.9;feed(0);self.assertFalse(monitor.ready())
        tick[0]=21;feed(0);self.assertTrue(monitor.ready())

    def test_brief_gap_recovers_into_quiet_and_counts_once(self):
        tick = [0.0]
        events = []
        monitor = ReceiveMonitor(lambda: tick[0], lambda kind, data: events.append(data))
        monitor.stream = SimpleNamespace(active=True)
        monitor.feed(b'\0\0')
        tick[0] = 2.0
        self.assertEqual(monitor.snapshot(), ('recovering', None, 0))
        self.assertFalse(monitor.ready())
        tick[0] = 4.0
        monitor.feed(b'\0\0')
        self.assertTrue(monitor.ready())
        self.assertEqual(monitor.recoveries, 1)
        self.assertEqual([event['code'] for event in events], ['started', 'recovered'])
        self.assertEqual(events[1]['gap_ms'], 4000)
        self.assertEqual(events[0]['gap_id'], events[1]['gap_id'])

    def test_recovery_does_not_count_missing_audio_toward_traffic_hold(self):
        tick = [0.0]
        monitor = ReceiveMonitor(lambda: tick[0])
        monitor.stream = SimpleNamespace(active=True)
        monitor.feed(array('h', [6000]).tobytes())
        tick[0] = 0.5
        monitor.feed(b'\0\0')
        tick[0] = 6.0
        monitor.feed(b'\0\0')
        self.assertEqual(monitor.snapshot()[2], 5)
        self.assertEqual(monitor.recoveries, 1)

    def test_late_callback_cannot_clear_an_expired_or_inactive_stream(self):
        for inactive in (False, True):
            with self.subTest(inactive=inactive):
                tick = [0.0]
                events = []
                monitor = ReceiveMonitor(lambda: tick[0], lambda kind, data: events.append(data))
                monitor.stream = SimpleNamespace(active=True)
                monitor.feed(b'\0\0')
                tick[0] = 2.0
                self.assertFalse(monitor.ready())
                if inactive:
                    monitor.stream.active = False
                    self.assertEqual(monitor.snapshot()[0], 'fault')
                    monitor.stream.active = True
                else:
                    tick[0] = 10.0
                monitor.feed(b'\0\0')
                with self.assertRaises(ValueError):
                    monitor.ready()
                self.assertEqual(monitor.recoveries, 0)
                self.assertEqual([event['code'] for event in events], ['started', 'failed'])

    def test_existing_seven_second_setting_migrates_to_five(self):
        import tempfile
        from pathlib import Path
        from dxtalker.models import load_settings,save_settings
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'settings.json'
            save_settings(Settings(receive_quiet_seconds=7),path)
            loaded=load_settings(path)
            self.assertEqual(loaded.receive_quiet_seconds,5)
            self.assertEqual(Settings().receive_quiet_seconds,5)

    def test_missing_callbacks_and_invalid_settings(self):
        tick=[0];monitor=ReceiveMonitor(clock=lambda:tick[0]);monitor.stream=SimpleNamespace(active=True);monitor._started_at=0
        tick[0]=2
        with self.assertRaisesRegex(ValueError,'no audio'):monitor.ready()
        for kwargs in ({'receive_quiet_seconds':4},{'receive_quiet_seconds':11},{'receive_threshold_db':-61}):
            with self.assertRaises(ValueError):replace(Settings(),**kwargs).validate()
        with self.assertRaisesRegex(ValueError,'receive audio input'):
            replace(Settings(),receive_guard=True).validate_rf()


class FakeMonitor:
    def __init__(self): self.clear=False;self.failed=False;self.started=False
    def start(self,s):self.started=True
    def close(self):self.started=False
    def ready(self, **kwargs):
        if self.failed:raise ValueError('Receive audio monitoring failed')
        return self.clear
    def transmit_started(self):self.blanked=True
    def transmit_ended(self):self.blanked=False;self.clear=False


class ReceiverEngineTests(unittest.TestCase):
    setUp = _EngineTests.setUp
    tearDown = _EngineTests.tearDown
    spot = _EngineTests.spot
    def guarded(self):
        self.monitor=FakeMonitor();self.engine.monitor=self.monitor
        self.engine.configure(replace(self.settings,receive_guard=True,receive_half_duplex=False,receive_device='receiver'))

    def test_busy_defers_initial_id_and_spots_without_losing_queue(self):
        self.guarded();self.engine.enable();self.engine.offer(self.spot())
        time.sleep(.15)
        self.assertEqual(self.ptts,[]);self.assertEqual(len(self.engine.items),1)
        self.monitor.clear=True;self.engine.wake.set()
        wait_for(lambda:len(self.audio.played)==2 and not self.engine.busy)
        self.assertEqual(self.engine.alternate,1)
        self.assertTrue(self.engine.enabled)

    def test_receive_during_transmit_cancels_releases_and_retries_after_clear(self):
        self.guarded();self.monitor.clear=True
        entered=threading.Event()
        class Incoming(FakeAudio):
            def play(this,clip,device,volume,cancel,deadline):
                super().play(clip,device,volume,cancel,deadline)
                if len(this.played)==1:
                    entered.set()
                    if cancel.wait(2):raise Cancelled()
        self.engine.audio=Incoming()
        self.engine.enable();self.assertTrue(entered.wait(2))
        self.monitor.clear=False
        wait_for(lambda:not self.engine.busy)
        self.assertEqual(self.ptts[0].calls[-2:],[False,'close'])
        self.assertTrue(self.engine.enabled);self.assertFalse(self.engine.cancel.is_set())
        self.assertEqual(self.engine.alternate,0)
        self.monitor.clear=True;self.engine.wake.set()
        wait_for(lambda:len(self.engine.audio.played)==2 and not self.engine.busy)
        self.assertEqual(self.engine.alternate,1)

    def test_expired_spot_is_not_sent_after_receive_hold(self):
        from datetime import datetime, timedelta
        from dxtalker.models import UTC
        self.guarded();self.engine.enable()
        spot=self.spot()
        with self.engine.lock:
            self.engine.offer(spot)
            self.engine.items[0]=('spot',replace(spot,timestamp=datetime.now(UTC)-timedelta(seconds=601)))
        self.monitor.clear=True;self.engine.wake.set()
        wait_for(lambda:len(self.audio.played)==1 and not self.engine.items and not self.engine.busy)
        self.assertEqual(self.speech.texts,[])

    def test_inactive_input_is_checked_again_before_keying_even_with_a_recent_callback(self):
        from dxtalker.audio import Clip
        self.guarded()
        monitor=ReceiveMonitor()
        now=time.monotonic()
        monitor.stream=SimpleNamespace(active=False,abort=lambda:None,close=lambda:None)
        monitor._started_at=now-10;monitor.last_frame=now;monitor.quiet_since=now-10
        self.engine.monitor=monitor
        with self.assertRaisesRegex(ValueError,'monitoring failed'):
            self.engine._transmit(Clip(b'\0\0'*100),self.engine.settings)
        self.assertEqual(self.ptts,[])

    def test_input_loss_disarms_instead_of_transmitting(self):
        self.guarded();self.engine.enable();self.monitor.failed=True
        wait_for(lambda:not self.engine.enabled)
        self.assertEqual(self.ptts,[]);self.assertFalse(self.monitor.started)

    def test_local_listening_and_preview_ignore_radio_gate(self):
        self.guarded();self.engine.listen_locally();self.engine.offer(self.spot())
        wait_for(lambda:len(self.audio.played)==1 and not self.engine.busy)
        self.assertFalse(self.monitor.started);self.assertEqual(self.ptts,[])

    def test_half_duplex_own_audio_does_not_cancel_id_and_next_item_waits(self):
        self.guarded();self.monitor.clear=True
        self.engine.configure(replace(self.engine.settings,receive_half_duplex=True))
        monitor=self.monitor
        class Loopback(FakeAudio):
            def play(this,clip,device,volume,cancel,deadline):
                this.assert_blanked=getattr(monitor,'blanked',False)
                monitor.clear=False
                self.assertFalse(cancel.wait(.02))
                super().play(clip,device,volume,cancel,deadline)
        self.engine.audio=Loopback()
        with self.engine.lock:
            self.engine.enable();self.engine.offer(self.spot())
        wait_for(lambda:len(self.engine.audio.played)==1 and not self.engine.busy)
        self.assertTrue(self.engine.audio.assert_blanked)
        self.assertFalse(monitor.blanked);self.assertTrue(self.engine.enabled)
        self.assertEqual(self.engine.alternate,1)
        self.assertEqual(len(self.engine.items),1)
        time.sleep(.1);self.assertEqual(len(self.ptts),1)
        self.assertEqual(self.ptts[0].calls[-2:],[False,'close'])

    def test_half_duplex_next_spot_needs_only_settling_when_receiver_is_quiet(self):
        tick=[10.0]
        monitor=ReceiveMonitor(clock=lambda:tick[0])
        quiet=array('h',[0]*1024).tobytes();loud=array('h',[6000]*1024).tobytes()
        def start(settings):
            monitor._started_at=tick[0]
            monitor.stream=SimpleNamespace(active=True,abort=lambda:None,close=lambda:None)
            monitor.feed(quiet)
        with patch.object(monitor,'start',side_effect=start):
            self.engine.monitor=monitor
            self.engine.configure(replace(self.settings,receive_guard=True,receive_half_duplex=True,receive_device='receiver'))
            class Loopback(FakeAudio):
                def play(this,clip,device,volume,cancel,deadline):
                    monitor.feed(loud)
                    self.assertFalse(cancel.is_set())
                    super().play(clip,device,volume,cancel,deadline)
            self.engine.audio=Loopback()
            with self.engine.lock:
                self.engine.enable();self.engine.offer(self.spot())
            wait_for(lambda:len(self.engine.audio.played)==1 and not self.engine.busy)
            self.assertEqual(len(self.ptts),1);self.assertEqual(len(self.engine.items),1)
            tick[0]=10.9;monitor.feed(loud);self.assertFalse(monitor.ready())
            tick[0]=11;monitor.feed(quiet);self.assertTrue(monitor.ready())
            self.engine.wake.set()
            wait_for(lambda:len(self.engine.audio.played)==2 and not self.engine.busy)
            self.assertEqual(len(self.ptts),2);self.assertFalse(self.engine.items)

    def test_half_duplex_input_fault_still_releases_ptt_and_disarms(self):
        self.guarded();self.monitor.clear=True
        self.engine.configure(replace(self.engine.settings,receive_half_duplex=True,ptt_method='RTS',serial_port='COM99'))
        monitor=self.monitor
        class InputFailure(FakeAudio):
            def play(this,clip,device,volume,cancel,deadline):
                monitor.failed=True
                self.assertTrue(cancel.is_set())
                raise Cancelled()
        self.engine.audio=InputFailure();self.engine.enable()
        wait_for(lambda:bool(self.ptts) and not self.engine.enabled and not self.engine.busy)
        self.assertFalse(monitor.blanked)
        self.assertEqual(self.ptts[0].calls[-2:],[False,'close'])

    def test_receive_gap_releases_half_duplex_ptt_and_retries_id_after_recovery(self):
        tick = [0.0]
        entered = threading.Event()
        self.guarded()
        self.engine.configure(replace(self.engine.settings, receive_half_duplex=True,
                                      ptt_method='RTS', serial_port='COM99'))
        monitor = ReceiveMonitor(clock=lambda: tick[0])

        def start(settings):
            monitor.stream = SimpleNamespace(active=True, abort=lambda: None, close=lambda: None)
            monitor.feed(b'\0\0')

        class GapDuringPlayback(FakeAudio):
            def play(this, clip, device, volume, cancel, deadline):
                super().play(clip, device, volume, cancel, deadline)
                if len(this.played) == 1:
                    entered.set()
                    if cancel.wait(2):
                        raise Cancelled()

        self.engine.monitor = monitor
        self.engine.audio = GapDuringPlayback()
        with patch.object(monitor, 'start', side_effect=start):
            self.engine.enable()
            self.assertTrue(entered.wait(2))
            tick[0] = 2.0
            wait_for(lambda: not self.engine.busy)
            self.assertEqual(self.ptts[0].calls[-2:], [False, 'close'])
            self.assertTrue(self.engine.enabled)
            self.assertEqual(self.engine.alternate, 0)
            self.assertEqual(monitor.snapshot()[0], 'recovering')
            tick[0] = 4.0
            monitor.feed(b'\0\0')
            self.engine.wake.set()
            wait_for(lambda: self.engine.alternate == 1 and not self.engine.busy)
            self.assertEqual(monitor.recoveries, 1)

del _EngineTests
