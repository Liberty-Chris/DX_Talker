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
    def test_own_transmit_audio_is_blanked_but_faults_and_new_quiet_delay_remain(self):
        from dxtalker.receiver import ReceiveCancel
        tick=[10.0];monitor=ReceiveMonitor(clock=lambda:tick[0])
        monitor.stream=SimpleNamespace(active=True);monitor._started_at=0
        monitor.feed(array('h',[0]*1024).tobytes());monitor.quiet_since=0
        self.assertTrue(monitor.ready())
        cancel=ReceiveCancel(threading.Event(),monitor);cancel.ignore_busy=True
        monitor.transmit_started();monitor.feed(array('h',[6000]*1024).tobytes())
        self.assertEqual(monitor.snapshot()[0],'transmitting');self.assertFalse(cancel.is_set())
        monitor.transmit_ended();tick[0]=10.2;monitor.feed(array('h',[0]*1024).tobytes())
        self.assertEqual(monitor.snapshot()[0],'settling');self.assertFalse(monitor.ready())
        tick[0]=10.4;monitor.feed(array('h',[0]*1024).tobytes())
        tick[0]=17.3;monitor.feed(array('h',[0]*1024).tobytes());self.assertFalse(monitor.ready())
        tick[0]=17.5;monitor.feed(array('h',[0]*1024).tobytes());self.assertTrue(monitor.ready())
        monitor.transmit_started();monitor.feed(b'\0\0',fault=True)
        self.assertTrue(cancel.is_set());self.assertIsNotNone(cancel.fault)

    def test_quiet_delay_resets_and_faults_close_the_gate(self):
        tick=[0]
        monitor=ReceiveMonitor(clock=lambda:tick[0])
        monitor.stream=SimpleNamespace(active=True)
        monitor._started_at=0
        monitor.delay=7
        def feed(level):monitor.feed(array('h',[level]*1024).tobytes())
        self.assertFalse(monitor.ready())
        feed(0)
        tick[0]=6.9;feed(0);self.assertFalse(monitor.ready())
        tick[0]=7;feed(0);self.assertTrue(monitor.ready())
        tick[0]=8;feed(6000);self.assertFalse(monitor.ready())
        tick[0]=9;feed(0)
        tick[0]=15;feed(0);self.assertFalse(monitor.ready())
        tick[0]=16;feed(0);self.assertTrue(monitor.ready())
        tick[0]=18
        with self.assertRaisesRegex(ValueError,'monitoring failed'):monitor.ready()
        feed(0);monitor.feed(b'\0\0',fault=True)
        with self.assertRaises(ValueError):monitor.ready()
        monitor.fault=False;monitor.stream.active=False
        with self.assertRaises(ValueError):monitor.ready()

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

del _EngineTests
