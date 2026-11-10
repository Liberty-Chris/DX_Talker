from dataclasses import replace
from datetime import datetime, timedelta
import threading
import time
import unittest

from dxtalker.audio import Cancelled, Clip
from dxtalker.engine import Engine
from dxtalker.models import UTC, Settings, parse_line


def wait_for(predicate, timeout=3):
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() > deadline:
            raise AssertionError("Timed out waiting for worker")
        threading.Event().wait(0.005)


class FakeAudio:
    def __init__(self):
        self.played = []
        self.volumes = []
        self.entered = threading.Event()
        self.block = False
        self.fail = False

    def resolve(self, key, channels):
        return 0

    def play(self, clip, device, volume, cancel, deadline):
        self.played.append((clip, device))
        self.volumes.append(volume)
        self.entered.set()
        if self.fail:
            raise RuntimeError("Device lost")
        if self.block:
            cancel.wait(2)
            if cancel.is_set():
                raise Cancelled()


class FakeSpeech:
    def __init__(self):
        self.texts = []

    def render(self, text, voice, rate, cancel):
        self.texts.append(text)
        return Clip(b"\0\0" * 2205)


class FakePTT:
    def __init__(self):
        self.calls = []

    def open(self):
        self.calls.append("open")

    def set(self, keyed):
        self.calls.append(keyed)

    def close(self):
        self.calls.extend([False, "close"])


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.audio, self.speech = FakeAudio(), FakeSpeech()
        self.ptts, self.events = [], []
        self.settings = replace(Settings(), radio_device="radio", preview_device="local", cw_text="E",
                                voice_text="KF4DBX", lead_ms=0, tail_ms=0, spacing_seconds=1)

        def create(settings):
            ptt = FakePTT()
            self.ptts.append(ptt)
            return ptt

        self.engine = Engine(self.settings, lambda *event: self.events.append(event), self.audio, self.speech, create)

    def test_inferred_cw_and_opted_in_unknown_are_actually_announced(self):
        self.engine.settings=replace(self.settings,filter_modes='CW',filter_bands='20m',spacing_seconds=0)
        self.engine.listen_locally()
        now=datetime.now(UTC)
        cw=parse_line(f'DX de N0CALL: 14025 K1AAA 599 {now:%H%M}Z','fixture',now)
        unknown=parse_line(f'DX de N0CALL: 14225 K2BBB {now:%H%M}Z','fixture',now)
        digital=parse_line(f'DX de N0CALL: 14074 K3CCC FT8 {now:%H%M}Z','fixture',now)
        self.assertTrue(self.engine.offer(cw))
        self.assertFalse(self.engine.offer(unknown));self.assertFalse(self.engine.offer(digital))
        wait_for(lambda:len(self.audio.played)==1 and not self.engine.busy)
        self.engine.update_listening(replace(self.engine.settings,filter_modes='CW,Unknown'))
        self.assertTrue(self.engine.offer(unknown))
        self.assertFalse(self.engine.offer(replace(unknown,frequency_khz=__import__('decimal').Decimal('7225'))))
        self.assertFalse(self.engine.offer(digital))
        wait_for(lambda:len(self.audio.played)==2 and not self.engine.busy)
        self.assertEqual(len(self.speech.texts),2)
        self.assertFalse(self.ptts)

    def test_mode_and_activity_filter_rejects_before_audio_or_ptt(self):
        self.engine.settings = replace(self.settings, filter_modes='CW', filter_activities='POTA')
        self.engine.local_enabled = True
        now = datetime.now(UTC)
        digital = parse_line(f'DX de N0CALL: 14074 WB4IUY FT8 POTA {now:%H%M}Z', 'fixture', now)
        unknown = parse_line(f'DX de N0CALL: 14025 WB4IUY CQ {now:%H%M}Z', 'fixture', now)
        self.assertFalse(self.engine.offer(digital))
        self.assertFalse(self.engine.offer(unknown))
        self.assertEqual(len(self.engine.items), 0)
        self.assertFalse(self.ptts)
        self.assertFalse(self.speech.texts)

    def test_muted_local_session_admits_display_receipts_without_audio_or_backlog(self):
        self.engine.settings=replace(self.settings,filter_bands='20m',filter_modes='CW',spacing_seconds=0)
        self.engine.listen_locally();self.engine.set_local_muted(True)
        now=datetime.now(UTC)
        first=parse_line(f'DX de N0CALL: 14025 K1AAA CW {now:%H%M}Z','fixture',now)
        self.assertTrue(self.engine.offer(first,'muted-row'))
        receipts=[event[1] for event in self.events if event[0]=='spot_status']
        self.assertEqual(receipts[-1]['state'],'muted')
        self.assertFalse(self.engine.items);self.assertFalse(self.speech.texts);self.assertFalse(self.audio.played)
        self.assertTrue(self.engine.local_enabled);self.assertFalse(self.engine.enabled)
        self.assertIn('Mode',self.engine.admit(replace(first,dx_call='K2BBB',comment='SSB')))
        self.engine.set_local_muted(False)
        self.assertFalse(self.engine.offer(first))
        self.assertTrue(self.engine.offer(replace(first,dx_call='K3CCC'),'heard-row'))
        wait_for(lambda:len(self.audio.played)==1 and not self.engine.busy)
        self.assertFalse(self.ptts)
        self.assertEqual([r[1]['state'] for r in self.events if r[0]=='spot_status' and r[1]['token']=='heard-row'],['announcing','announced'])

    def test_mute_cancels_current_and_pending_local_audio_without_stopping_session(self):
        release=threading.Event()
        original=self.audio.play
        def play(clip,device,volume,cancel,deadline):
            self.audio.block=True
            self.audio.entered.set();release.wait(2)
            return original(clip,device,volume,cancel,deadline)
        self.audio.play=play
        self.engine.listen_locally();now=datetime.now(UTC)
        first=parse_line(f'DX de N0CALL: 14025 K1AAA CW {now:%H%M}Z','fixture',now)
        try:
            self.assertTrue(self.engine.offer(first,'current'));self.assertTrue(self.audio.entered.wait(1))
            self.assertTrue(self.engine.offer(replace(first,dx_call='K2BBB'),'pending'))
            self.engine.set_local_muted(True)
            with self.assertRaises(ValueError):self.engine.set_local_muted(False)
        finally:release.set()
        wait_for(lambda:not self.engine.busy)
        self.assertTrue(self.engine.local_enabled);self.assertTrue(self.engine.local_muted)
        self.assertFalse(self.engine.items);self.assertFalse(self.ptts)
        states={r[1]['token']:r[1]['state'] for r in self.events if r[0]=='spot_status'}
        self.assertEqual(states,{'current':'muted','pending':'muted'})
        self.assertFalse(any(r[0]=='error' for r in self.events))
        self.audio.block=False;self.engine.set_local_muted(False)
        self.assertTrue(self.engine.offer(replace(first,dx_call='K3CCC')))
        wait_for(lambda:len(self.audio.played)==2 and not self.engine.busy)

    def test_mute_during_speech_preparation_preserves_session_and_skips_future_generation(self):
        entered=threading.Event()
        class Speech(FakeSpeech):
            def render(self,text,voice,rate,cancel):
                self.texts.append(text);entered.set()
                if cancel.wait(2):raise Cancelled()
                return Clip(b'\0\0'*2205)
        self.engine.speech=Speech();self.engine.listen_locally();now=datetime.now(UTC)
        spot=parse_line(f'DX de N0CALL: 14025 K1AAA CW {now:%H%M}Z','fixture',now)
        self.assertTrue(self.engine.offer(spot,'preparing'));self.assertTrue(entered.wait(1))
        self.engine.set_local_muted(True);wait_for(lambda:not self.engine.busy)
        self.assertTrue(self.engine.local_enabled)
        self.assertTrue(self.engine.offer(replace(spot,dx_call='K2BBB'),'muted-arrival'))
        self.assertEqual(len(self.engine.speech.texts),1);self.assertFalse(self.audio.played)
        self.assertEqual({r[1]['state'] for r in self.events if r[0]=='spot_status' and r[1]['state']!='announcing'},{'muted'})

    def test_local_mute_does_not_touch_rf_and_zero_local_volume_keeps_display_receipts(self):
        self.engine.settings=replace(self.settings,local_volume_percent=0)
        self.engine.listen_locally();now=datetime.now(UTC)
        spot=parse_line(f'DX de N0CALL: 14025 K1AAA CW {now:%H%M}Z','fixture',now)
        self.assertTrue(self.engine.offer(spot,'zero-volume'))
        self.assertFalse(self.engine.items);self.assertFalse(self.speech.texts)
        self.assertEqual([r[1]['state'] for r in self.events if r[0]=='spot_status'],['muted'])
        self.engine.stop();self.engine.enabled=True
        with self.assertRaises(ValueError):self.engine.set_local_muted(True)
        self.assertTrue(self.engine.enabled);self.assertFalse(self.engine.local_muted)

    def tearDown(self):
        self.engine.shutdown()
        self.engine.worker.join(3)
        self.assertFalse(self.engine.worker.is_alive())

    def spot(self, dx="KT4BN", minute_offset=0):
        now = datetime.now(UTC)
        stamp = now + timedelta(minutes=minute_offset)
        return parse_line(f"DX de N0CALL: 7074 {dx} FT8 {stamp:%H%M}Z", "test", now)

    def enable_and_id(self):
        self.engine.enable()
        wait_for(lambda: len(self.audio.played) >= 1 and not self.engine.busy)

    def test_audio_off_display_still_obeys_filters_and_zero_rf_volume_does_not_hide_rows(self):
        self.engine.settings=replace(self.settings,filter_bands='20m')
        self.assertEqual(self.engine.admit(self.spot(),'excluded'),'Band')
        self.engine.settings=replace(self.settings,volume_percent=0)
        # Reserve RF state without opening a device or scheduling a real ID.
        with self.engine.lock:
            self.engine.enabled=True;self.engine.next_id=time.monotonic()+3600
            self.assertEqual(self.engine.admit(self.spot(),'rf-zero'),'')
            self.assertFalse(self.engine.items)
        self.assertEqual([v['state'] for k,v in self.events if k=='spot_status'],['display_only'])
        self.assertFalse(self.audio.played);self.assertFalse(self.speech.texts);self.assertFalse(self.ptts)

    def test_startup_is_disabled_and_does_not_queue_spots(self):
        self.assertFalse(self.engine.enabled)
        self.assertTrue(self.engine.offer(self.spot(),'audio-off'))
        self.assertEqual([v['state'] for k,v in self.events if k=='spot_status'],['display_only'])
        self.assertEqual(len(self.engine.items), 0)
        self.assertEqual(self.ptts, [])

    def test_initial_id_then_spot_with_ptt_release(self):
        self.enable_and_id()
        self.assertTrue(self.engine.offer(self.spot()))
        wait_for(lambda: len(self.audio.played) == 2 and not self.engine.busy)
        self.assertIn("Kilo Tango four Bravo November", self.speech.texts[-1])
        for ptt in self.ptts:
            self.assertEqual(ptt.calls, ["open", True, False, "close"])

    def test_local_preview_never_constructs_ptt(self):
        self.engine.preview("voice")
        wait_for(lambda: len(self.audio.played) == 1 and not self.engine.busy)
        self.assertEqual(self.audio.played[0][1], "local")
        self.assertEqual(self.ptts, [])

    def test_stop_interrupts_and_releases_ptt(self):
        self.audio.block = True
        self.engine.enable()
        self.assertTrue(self.audio.entered.wait(2))
        self.engine.offer(self.spot())
        self.engine.stop()
        wait_for(lambda: not self.engine.busy)
        self.assertFalse(self.engine.enabled)
        self.assertEqual(len(self.engine.items), 0)
        self.assertEqual(self.ptts[0].calls[-2:], [False, "close"])

    def test_audio_fault_disarms_and_releases(self):
        self.audio.fail = True
        self.engine.enable()
        wait_for(lambda: bool(self.ptts) and not self.engine.enabled and not self.engine.busy)
        self.assertEqual(self.ptts[0].calls[-2:], [False, "close"])
        self.assertTrue(any(kind == "error" for kind, _ in self.events))

    def test_duplicate_stale_and_filtered_spots_do_not_queue(self):
        self.enable_and_id()
        self.assertFalse(self.engine.offer(self.spot(minute_offset=-20)))
        spot = self.spot()
        self.assertTrue(self.engine.offer(spot))
        self.assertFalse(self.engine.offer(spot))
        wait_for(lambda: len(self.audio.played) == 2 and not self.engine.busy)
        self.assertFalse(self.engine.offer(spot))

    def test_queue_has_a_hard_capacity(self):
        # Hold the lock so the worker cannot drain while exercising admission.
        self.enable_and_id()
        with self.engine.lock:
            self.engine.next_spot = time.monotonic() + 60
            accepted = [self.engine.offer(self.spot(f"K{i}ABC")) for i in range(150)]
            self.assertEqual(sum(accepted), 100)
            self.assertEqual(len(self.engine.items), 100)

    def test_id_priority_over_pending_spots(self):
        self.enable_and_id()
        with self.engine.lock:
            self.engine.offer(self.spot())
            self.engine.next_id = 0
        wait_for(lambda: len(self.audio.played) >= 3 and not self.engine.busy)
        self.assertGreater(self.audio.played[1][0].duration, 0)
        self.assertEqual(len(self.speech.texts), 1)
        self.assertEqual(self.engine.alternate, 2)

    def test_reconfiguration_or_preview_while_armed_is_rejected(self):
        self.enable_and_id()
        with self.assertRaises(ValueError):
            self.engine.configure(self.settings)
        with self.assertRaises(ValueError):
            self.engine.preview("cw")

    def test_oversized_transmission_never_opens_ptt(self):
        with self.assertRaises(ValueError):
            self.engine._transmit(Clip(b"\0\0" * 22050 * 121), self.settings)
        self.assertEqual(self.ptts, [])

    def test_rf_can_identify_without_a_source_but_cancellation_still_blocks_ptt(self):
        self.engine.source_available = lambda: False
        self.enable_and_id()
        self.assertTrue(self.engine.enabled)
        self.assertEqual(len(self.ptts), 1)
        self.engine.stop()
        count = len(self.ptts)
        with self.assertRaises(Cancelled):
            self.engine._transmit(Clip(b"\0\0" * 100), self.settings)
        self.assertEqual(len(self.ptts), count)

    def test_incomplete_radio_setup_never_enables_or_keys(self):
        self.engine.configure(replace(self.settings, radio_device=""))
        with self.assertRaisesRegex(ValueError, "radio audio device"):
            self.engine.enable()
        self.assertFalse(self.engine.enabled)
        self.assertEqual(self.ptts, [])

    def test_watchdog_releases_independently_of_a_stalled_audio_call(self):
        released = threading.Event()

        class StalledAudio(FakeAudio):
            def play(self, *args):
                # Ignore cancellation, as a stuck native call might do.
                self.entered.set()
                released.wait(7)

        class WatchPTT(FakePTT):
            def set(self, keyed):
                super().set(keyed)
                if not keyed:
                    released.set()

        self.engine.audio = StalledAudio()
        self.engine.ptt_factory = lambda s: WatchPTT()
        self.engine.configure(replace(self.settings, max_tx_seconds=5))
        self.engine.enable()
        self.assertTrue(released.wait(6))
        wait_for(lambda: not self.engine.busy)
        self.assertFalse(self.engine.enabled)

    def test_resume_does_not_replay_disabled_backlog(self):
        self.engine.offer(self.spot())
        self.enable_and_id()
        self.engine.stop()
        self.engine.offer(self.spot())
        self.enable_and_id()
        self.assertEqual(self.speech.texts, [])


    def test_live_local_listening_uses_preview_only_and_never_identifies_or_keys(self):
        self.engine.listen_locally()
        self.assertTrue(self.engine.local_enabled)
        self.assertFalse(self.engine.enabled)
        self.assertTrue(self.engine.offer(self.spot()))
        wait_for(lambda: len(self.audio.played) == 1 and not self.engine.busy)
        self.assertEqual(self.audio.played[0][1], "local")
        self.assertEqual(self.ptts, [])
        self.assertFalse(self.engine.offer(self.spot()))
        self.engine.stop()
        self.assertFalse(self.engine.local_enabled)
        self.assertTrue(self.engine.offer(self.spot("WB4IUY")))
        self.assertFalse(self.engine.items)

    def test_local_listening_can_arm_before_source_and_still_requires_device(self):
        self.engine.source_available = lambda: False
        self.engine.listen_locally()
        self.assertTrue(self.engine.local_enabled)
        self.assertTrue(self.engine.offer(self.spot()))
        wait_for(lambda: len(self.audio.played)==1 and not self.engine.busy)
        self.assertEqual(self.ptts, [])
        self.engine.stop()
        self.engine.configure(replace(self.settings, preview_device=""))
        with self.assertRaises(ValueError):
            self.engine.listen_locally()
        self.engine.configure(self.settings)
        self.audio.fail = True
        self.engine.listen_locally()
        self.engine.offer(self.spot())
        wait_for(lambda: not self.engine.local_enabled)
        self.assertEqual(self.ptts, [])

    def test_cw_and_voice_id_levels_do_not_use_spot_gain(self):
        self.engine.configure(replace(self.settings, volume_percent=7, cw_volume_percent=20))
        self.enable_and_id()
        self.assertEqual(self.audio.volumes[0], 100)
        self.engine.offer(self.spot())
        wait_for(lambda: len(self.audio.played) == 2 and not self.engine.busy)
        self.assertEqual(self.audio.volumes[1], 7)

    def test_local_volume_is_independent(self):
        self.engine.configure(replace(self.settings, volume_percent=12, local_volume_percent=34))
        self.engine.listen_locally()
        self.engine.offer(self.spot())
        wait_for(lambda: len(self.audio.played) == 1 and not self.engine.busy)
        self.assertEqual(self.audio.volumes, [34])


    def test_preview_uses_format_snapshot_without_applying_settings_or_keying(self):
        custom = replace(self.settings, announcement_order='intro,callsign,frequency',
                         announcement_intro='New DX', speak_units=False, frequency_unit='MHz')
        self.engine.preview('spot', self.spot(), settings=custom)
        wait_for(lambda: len(self.audio.played) == 1 and not self.engine.busy)
        self.assertEqual(self.speech.texts[0], 'New DX. Kilo Tango four Bravo November. seven point zero seven four.')
        self.assertIs(self.engine.settings, self.settings)
        self.assertEqual(self.ptts, [])
        self.assertFalse(self.engine.enabled)

    def test_known_playback_fault_logs_fixed_code_and_frames_and_shows_readable_message(self):
        from dxtalker.audio import AudioPlaybackError
        class FaultAudio(FakeAudio):
            def play(self,*args):
                raise AudioPlaybackError('audio_stream_stopped',frames_queued=1024,frames_expected=2048,sample_rate=22050,channels=1)
        self.engine.audio=FaultAudio()
        self.engine.preview('voice')
        wait_for(lambda:any(kind=='diagnostic' for kind,value in self.events) and not self.engine.busy)
        evidence=next(value for kind,value in self.events if kind=='diagnostic')
        self.assertEqual(evidence['code'],'audio_stream_stopped')
        self.assertEqual(evidence['route'],'local')
        self.assertEqual(evidence['playback']['frames_queued'],1024)
        self.assertTrue(any(kind=='error' and 'Audio output stopped' in value for kind,value in self.events))
        self.assertEqual(self.ptts,[])

    def test_known_radio_playback_fault_still_disarms_and_releases_ptt(self):
        from dxtalker.audio import AudioPlaybackError
        class FaultAudio(FakeAudio):
            def play(self,*args):
                raise AudioPlaybackError('audio_stream_fault',frames_queued=0,frames_expected=1000,sample_rate=22050,channels=1)
        self.engine.audio=FaultAudio()
        self.engine.enable()
        wait_for(lambda:bool(self.ptts) and not self.engine.enabled and not self.engine.busy)
        self.assertEqual(self.ptts[0].calls[-2:],[False,'close'])
        evidence=next(value for kind,value in self.events if kind=='diagnostic')
        self.assertEqual(evidence['route'],'radio')
        self.assertEqual(evidence['code'],'audio_stream_fault')

    def test_recovered_spot_underrun_keeps_rf_enabled_and_releases_ptt(self):
        self.enable_and_id()
        class RecoveryAudio(FakeAudio):
            def play(self,*args):
                super().play(*args)
                return dict(output_underflows=1,status_flags=['output_underflow'])
        self.engine.audio=RecoveryAudio()
        self.assertTrue(self.engine.offer(self.spot()))
        wait_for(lambda:any(kind=='audio_recovery' for kind,value in self.events) and not self.engine.busy)
        self.assertTrue(self.engine.enabled)
        self.assertEqual(self.ptts[-1].calls[-2:],[False,'close'])
        self.assertFalse(any(kind=='diagnostic' for kind,value in self.events))
        event=next(value for kind,value in self.events if kind=='audio_recovery')
        self.assertEqual(event['route'],'radio')
        self.assertEqual(event['operation'],'spot')

    def test_recovery_does_not_mark_an_interrupted_required_id_complete(self):
        class RecoveryAudio(FakeAudio):
            def play(self,*args):
                super().play(*args)
                return dict(output_underflows=1,status_flags=['output_underflow'])
        self.engine.audio=RecoveryAudio()
        self.engine.enable()
        wait_for(lambda:bool(self.ptts) and not self.engine.enabled and not self.engine.busy)
        self.assertEqual(self.ptts[-1].calls[-2:],[False,'close'])
        event=next(value for kind,value in self.events if kind=='diagnostic')
        self.assertEqual(event['code'],'audio_id_interrupted')
        self.assertEqual(self.engine.alternate,0)

    def test_power_request_is_released_when_output_worker_exits(self):
        from unittest.mock import patch
        from dxtalker.power import OutputPower, CONTINUOUS, SYSTEM
        from types import SimpleNamespace
        self.engine.shutdown();self.engine.worker.join(2)
        calls=[]
        api=SimpleNamespace(request=lambda flags:calls.append((threading.get_ident(),flags)) or True)
        with patch('dxtalker.engine.OutputPower', side_effect=lambda emit:OutputPower(emit,api)):
            self.engine=Engine(replace(self.settings,keep_awake='Computer'), lambda *event:self.events.append(event), self.audio,self.speech,lambda settings:FakePTT())
            self.engine.listen_locally()
            wait_for(lambda:bool(calls))
            self.engine.stop()
            wait_for(lambda:len(calls)>=2)
            self.engine.listen_locally()
            wait_for(lambda:len(calls)>=3)
            self.engine.shutdown();self.engine.worker.join(2)
        self.assertEqual([flags for thread,flags in calls],[CONTINUOUS|SYSTEM,CONTINUOUS,CONTINUOUS|SYSTEM,CONTINUOUS])
        self.assertEqual(len({thread for thread,flags in calls}),1)

    def test_live_receipt_turns_green_only_after_completed_audio_and_cleanup(self):
        self.enable_and_id()
        self.audio.block=True
        spot=self.spot()
        self.assertEqual(self.engine.admit(spot,'receipt-one'),'')
        wait_for(lambda:self.audio.entered.is_set() and self.engine.current_spot is spot)
        self.assertFalse(any(k=='spot_status' and v['state']=='announced' for k,v in self.events))
        self.engine.stop('Stopped by operator')
        wait_for(lambda:not self.engine.busy)
        receipts=[v for k,v in self.events if k=='spot_status' and v['token']=='receipt-one']
        self.assertEqual(receipts[-1]['state'],'rejected')
        self.assertEqual(receipts[-1]['reason'],'Stopped by operator')
        self.assertFalse(self.engine.spot_tokens)
        self.assertEqual(self.ptts[-1].calls[-2:],[False,'close'])

    def test_completed_receipt_and_duplicate_share_one_final_admission(self):
        self.enable_and_id()
        spot=self.spot()
        self.assertEqual(self.engine.admit(spot,'completed'),'')
        wait_for(lambda:any(k=='spot_status' and v['state']=='announced' for k,v in self.events))
        self.assertIn('Duplicate',self.engine.admit(spot,'duplicate'))
        self.assertFalse(self.engine.spot_tokens)
        self.assertEqual(sum(k=='spot_status' and v['state']=='announced' for k,v in self.events),1)
        self.assertEqual(self.ptts[-1].calls[-2:],[False,'close'])

    def test_every_discarded_pending_receipt_gets_a_reason(self):
        self.enable_and_id()
        for operation in ('catch_up','update_listening','stop'):
            spot=replace(self.spot(),dx_call='K1'+operation[:2].upper())
            with self.engine.lock:
                self.engine.next_spot=time.monotonic()+60
                self.assertEqual(self.engine.admit(spot,operation),'')
                if operation=='update_listening':self.engine.update_listening(self.settings)
                else:getattr(self.engine,operation)()
            receipt=next(v for k,v in self.events if k=='spot_status' and v['token']==operation)
            self.assertEqual(receipt['state'],'rejected');self.assertTrue(receipt['reason'])
        self.assertFalse(self.engine.spot_tokens)

    def test_active_spot_reserves_its_retry_slot_and_expiry_has_a_receipt(self):
        self.enable_and_id()
        with self.engine.lock:
            self.engine.next_spot=time.monotonic()+60
            self.engine.current_spot=self.spot('K1ACT')
            for i in range(99):
                self.assertEqual(self.engine.admit(self.spot('K'+str(i)+'ABC'),str(i)),'')
            self.assertEqual(self.engine.admit(self.spot('K1FULL'),'full'),'Announcement queue is full')
            self.engine.current_spot=None
            self.engine.items[0]=('spot',replace(self.engine.items[0][1],timestamp=datetime.now(UTC)-timedelta(seconds=601)))
            # Retain the same receipt identity for the synthetic aged object.
            expired=self.engine.items[0][1]
            original_id=next(key for key,token in self.engine.spot_tokens.items() if token=='0')
            self.engine.spot_tokens[id(expired)]=self.engine.spot_tokens.pop(original_id)
            self.engine._select()
        receipt=next(v for k,v in self.events if k=='spot_status' and v['token']=='0')
        self.assertEqual(receipt['state'],'rejected')
        self.assertIn('Expired',receipt['reason'])
