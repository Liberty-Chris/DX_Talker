"""Simulated paired outputs, with one RF owner and independent local mute."""
from dataclasses import replace
import threading
import unittest

from dxtalker.audio import Cancelled
import test_engine as fixtures
from test_engine import FakeAudio, wait_for


class ControlledAudio(FakeAudio):
    def __init__(self):
        super().__init__()
        self.release = threading.Event()
        self.finished = threading.Event()

    def play(self, clip, device, volume, cancel, deadline):
        self.cancel=cancel
        super().play(clip, device, volume, cancel, deadline)
        try:
            while not self.release.wait(.005):
                if cancel.is_set(): raise Cancelled()
        finally:
            self.finished.set()


class DualOutputTests(unittest.TestCase):
    setUp = fixtures.EngineTests.setUp
    tearDown = fixtures.EngineTests.tearDown
    spot = fixtures.EngineTests.spot

    def arm(self, local=True):
        self.local = FakeAudio()
        self.engine.local_audio = self.local
        with self.engine.lock:
            self.engine.enable(local=local)
            self.engine.next_id = self.engine.next_voice_id = self.engine.clock()+3600

    def test_spots_and_ids_share_one_render_and_ptt_with_two_destinations(self):
        self.arm()
        self.engine.settings=replace(self.settings,local_volume_percent=23,volume_percent=47,spacing_seconds=0)
        self.assertTrue(self.engine.offer(self.spot()))
        wait_for(lambda:len(self.audio.played)==1 and not self.engine.busy)
        self.engine.identify()
        wait_for(lambda:len(self.audio.played)==2 and not self.engine.busy)
        self.assertEqual(len(self.local.played),2)
        self.assertEqual([c.pcm for c,_ in self.local.played],[c.pcm for c,_ in self.audio.played])
        self.assertEqual([d for _,d in self.local.played],['local','local'])
        self.assertEqual([d for _,d in self.audio.played],['radio','radio'])
        self.assertEqual(self.local.volumes,[23,23])
        self.assertEqual(self.audio.volumes,[47,100])
        self.assertEqual(len(self.speech.texts),1)
        self.assertEqual(len(self.ptts),2)
        for ptt in self.ptts:self.assertEqual(ptt.calls,['open',True,False,'close'])
        self.engine.update_preferences(replace(self.engine.settings,local_volume_percent=61),('local_volume_percent',))
        self.assertEqual(self.local.volume_reader(),61)
        self.assertIsNone(self.audio.volume_reader)

    def test_local_mute_during_rf_does_not_cancel_radio_or_clear_queue(self):
        self.arm()
        radio,local=ControlledAudio(),ControlledAudio()
        self.engine.audio,self.engine.local_audio=radio,local
        self.assertTrue(self.engine.offer(self.spot()))
        self.assertTrue(radio.entered.wait(2));self.assertTrue(local.entered.wait(2))
        self.assertTrue(self.engine.offer(self.spot('K1AAA')))
        self.engine.set_local_muted(True)
        self.assertTrue(local.finished.wait(1))
        self.assertFalse(self.engine.cancel.is_set())
        self.assertTrue(self.engine.enabled);self.assertTrue(self.engine.busy)
        self.assertEqual(len(self.engine.items),1)
        radio.release.set()
        wait_for(lambda:len(radio.played)==2 and not self.engine.busy)
        self.assertEqual(len(local.played),1)
        self.engine.set_local_muted(False)
        local.release.set()
        self.engine.settings=replace(self.engine.settings,spacing_seconds=0)
        self.engine.next_spot=0
        self.assertTrue(self.engine.offer(self.spot('K2BBB')))
        wait_for(lambda:len(radio.played)==3 and not self.engine.busy)
        self.assertEqual(len(local.played),2)

    def test_stop_cancels_both_streams_and_releases_ptt(self):
        self.arm()
        radio,local=ControlledAudio(),ControlledAudio()
        self.engine.audio,self.engine.local_audio=radio,local
        self.assertTrue(self.engine.offer(self.spot()))
        self.assertTrue(radio.entered.wait(2));self.assertTrue(local.entered.wait(2))
        self.engine.stop()
        wait_for(lambda:not self.engine.busy)
        self.assertTrue(radio.finished.is_set());self.assertTrue(local.finished.is_set())
        self.assertEqual(self.ptts[0].calls[-2:],[False,'close'])
        self.assertFalse(self.engine.enabled);self.assertFalse(self.engine.local_enabled)

    def test_local_device_failure_mutes_monitor_without_losing_rf(self):
        self.arm()
        self.local.fail=True
        self.assertTrue(self.engine.offer(self.spot()))
        wait_for(lambda:self.engine.local_muted and not self.engine.busy)
        self.assertTrue(self.engine.enabled)
        self.assertFalse(self.engine.cancel.is_set())
        self.assertTrue(self.engine.offer(self.spot('K1AAA')))
        wait_for(lambda:len(self.audio.played)==2 and not self.engine.busy)

    def test_starting_local_monitor_preserves_armed_rf_and_receive_monitor(self):
        self.arm(local=False)
        from unittest.mock import patch
        with patch.object(self.engine.monitor,'close',side_effect=AssertionError('Receive guard closed')):
            self.engine.listen_locally()
        self.assertTrue(self.engine.enabled);self.assertTrue(self.engine.local_enabled)
        self.assertFalse(self.engine.cancel.is_set())

    def test_same_destination_requires_separate_speakers_before_rf_is_armed(self):
        self.engine.settings=replace(self.settings,preview_device='radio')
        with self.assertRaisesRegex(ValueError,'different local listening speakers'):
            self.engine.enable(local=True)
        self.assertFalse(self.engine.enabled)

    def test_receive_activity_cancels_both_streams_and_defers_rf_retry(self):
        from test_receiver import FakeMonitor
        self.engine.monitor=monitor=FakeMonitor()
        monitor.clear=True
        self.engine.settings=replace(self.settings,receive_guard=True,receive_device='receiver')
        self.arm()
        radio,local=ControlledAudio(),ControlledAudio()
        self.engine.audio,self.engine.local_audio=radio,local
        self.assertTrue(self.engine.offer(self.spot()))
        self.assertTrue(radio.entered.wait(2));self.assertTrue(local.entered.wait(2))
        monitor.clear=False
        wait_for(lambda:not self.engine.busy)
        self.assertTrue(radio.finished.is_set());self.assertTrue(local.finished.is_set())
        self.assertTrue(self.engine.enabled);self.assertTrue(self.engine.local_enabled)
        self.assertEqual(len(self.engine.items),1)
        self.assertEqual(self.ptts[0].calls[-2:],[False,'close'])
        radio.release.set();local.release.set();monitor.clear=True;self.engine.wake.set()
        wait_for(lambda:len(radio.played)==2 and not self.engine.busy)

    def test_radio_fault_disarms_both_routes(self):
        self.arm()
        self.engine.local_audio=local=ControlledAudio()
        owner=self
        class CheckingPTT(fixtures.FakePTT):
            def close(this):
                owner.assertTrue(local.cancel.is_set(),'Radio failure must cancel the monitor before PTT cleanup')
                super().close()
        def create(settings):
            ptt=CheckingPTT();self.ptts.append(ptt);return ptt
        self.engine.ptt_factory=create
        class FailingRadio(FakeAudio):
            def play(this,clip,device,volume,cancel,deadline):
                self.assertTrue(local.entered.wait(2))
                raise RuntimeError('Radio disconnected')
        self.engine.audio=FailingRadio()
        self.assertTrue(self.engine.offer(self.spot()))
        self.assertTrue(local.entered.wait(2))
        self.assertTrue(local.finished.wait(2))
        wait_for(lambda:not self.engine.enabled and not self.engine.busy)
        self.assertFalse(self.engine.local_enabled)
        self.assertEqual(self.ptts[0].calls[-2:],[False,'close'])

    def test_ptt_release_does_not_wait_for_local_speaker_completion(self):
        self.arm()
        self.engine.local_audio=local=ControlledAudio()
        self.assertTrue(self.engine.offer(self.spot()))
        self.assertTrue(local.entered.wait(2))
        wait_for(lambda:'close' in self.ptts[0].calls)
        self.assertFalse(local.finished.is_set())
        local.release.set()
        wait_for(lambda:not self.engine.busy)

    def test_receive_hold_defers_local_monitor_until_actual_transmission(self):
        from test_receiver import FakeMonitor
        self.engine.monitor=monitor=FakeMonitor()
        self.engine.settings=replace(self.settings,receive_guard=True,receive_device='receiver')
        self.arm()
        self.assertTrue(self.engine.offer(self.spot()))
        threading.Event().wait(.15)
        self.assertFalse(self.audio.played);self.assertFalse(self.local.played);self.assertFalse(self.ptts)
        monitor.clear=True;self.engine.wake.set()
        wait_for(lambda:len(self.audio.played)==1 and not self.engine.busy)
        self.assertEqual(len(self.local.played),1)
