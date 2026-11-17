from array import array
from dataclasses import replace
from datetime import datetime
from decimal import Decimal
import io
import json
import threading
import unittest
import wave

from dxtalker.attention import alert_clip
from dxtalker.engine import Engine
from dxtalker.filtering import keyword_selection, keyword_matches, special_match, matches
from dxtalker.models import Settings, UTC, make_spot
from dxtalker import transfer
from test_engine import FakeAudio, FakeSpeech, FakePTT, wait_for


def spot(call='W1AW/3', comment='SSB USS Cobia', frequency='14225', reporter='N0CALL'):
    now = datetime.now(UTC)
    return make_spot(call, frequency, reporter, now, 'fixture', now, comment)


class KeywordTests(unittest.TestCase):
    def test_short_special_calls_bypass_band_selection_but_not_other_limits(self):
        from dxtalker.models import parse_line, valid_call
        from dxtalker.filtering import calls_selection, rejection
        for call in ('C8K','K1A','W1A'):
            self.assertTrue(valid_call(call))
            self.assertEqual(calls_selection(call.lower()),{call})
            now=datetime.now(UTC)
            parsed=parse_line(f'DX de W3LPL: 14025 {call} CW {now:%H%M}Z','fixture',now)
            self.assertEqual(parsed.dx_call,call)
            s=Settings(special_calls=call.lower(),filter_bands='40m')
            self.assertTrue(matches(parsed,s))
            self.assertEqual(rejection(parsed,replace(s,filter_modes='SSB')),'Mode')
            self.assertEqual(rejection(parsed,replace(s,min_khz=7000,max_khz=7300)),'Frequency range')

    def test_literal_words_phrases_boundaries_and_case(self):
        words = keyword_selection('Cobia, county hunter, USS   Test')
        for text in ('USS COBIA submarine', 'county   hunter calling', 'uss test today'):
            self.assertTrue(keyword_matches(text, words))
        for text in ('scobias', 'county hunters', 'USStest'):
            self.assertFalse(keyword_matches(text, words))
        with self.assertRaises(ValueError): keyword_selection('.*')
        self.assertTrue(keyword_matches('CQ event (A+B)', keyword_selection('A+B')))
        for value in ('Cobia,cOBIA', ','.join('word'+str(i) for i in range(51)), 'x'*81):
            with self.assertRaises(ValueError): keyword_selection(value)

    def test_word_call_or_activity_selection_preserves_other_filters(self):
        s = Settings(special_keywords='Cobia', special_keywords_only=True, filter_activities='POTA')
        self.assertTrue(matches(spot(), s))
        self.assertFalse(matches(spot(comment='SSB Rover'), s))
        self.assertFalse(matches(spot(), replace(s, filter_bands='40m')))
        self.assertFalse(matches(spot(), replace(s, filter_modes='CW')))
        self.assertFalse(matches(spot(), replace(s, filter_dx_countries='JP')))
        both = replace(s, special_calls='TZ4AM', special_calls_only=True)
        self.assertTrue(matches(spot(call='TZ4AM', comment='SSB DX'), both))
        self.assertTrue(matches(spot(), both))
        self.assertFalse(matches(spot(call='K1ABC', comment='SSB DX'), both))
        supplemental = replace(s, special_keywords_only=False)
        self.assertTrue(matches(spot(comment='SSB POTA'), supplemental))
        self.assertTrue(matches(spot(), supplemental))

    def test_spotted_call_is_independent_of_reporting_call(self):
        s = Settings(special_calls='W1AW', special_calls_only=True)
        self.assertTrue(matches(spot(), s))
        self.assertFalse(matches(spot(call='K1ABC', reporter='W1AW'), s))
        self.assertFalse(matches(spot(), replace(s, special_calls_portable=False)))

    def test_unknown_modes_still_require_opt_in(self):
        s = Settings(special_keywords='Cobia', special_keywords_only=True)
        untagged = spot(comment='USS Cobia')
        self.assertFalse(matches(untagged, s))
        self.assertTrue(matches(untagged, replace(s, filter_modes='Unknown')))

    def test_presets_transfer_types_and_old_defaults(self):
        s = Settings(special_keywords='Cobia,county hunter', special_keywords_only=True, special_alert='Double ding')
        profiles = [dict(name='Test', connection={k:getattr(s,k) for k in transfer.SOURCE_FIELDS})]
        document = transfer.decode(transfer.encode(transfer.document(profiles,s)))
        self.assertEqual(document['filters']['special_keywords'], s.special_keywords)
        self.assertEqual(document['filters']['special_alert'], 'Double ding')
        self.assertFalse(Settings().rf_auto_reconnect)
        self.assertEqual(Settings().special_alert, 'Off')
        with self.assertRaises(ValueError): Settings(special_keywords_only=True).validate()
        with self.assertRaises(ValueError): Settings(special_alert='invented').validate()
        with self.assertRaises(ValueError): Settings(rf_auto_reconnect='true').validate()


class SoundTests(unittest.TestCase):
    def test_alert_duration_counts_toward_rf_watchdog_before_ptt(self):
        from dxtalker.audio import Clip
        audio, speech, ptts, events = FakeAudio(), FakeSpeech(), [], []
        speech.render=lambda *args:Clip(b'\0\0'*round(22050*4.8))
        settings=Settings(preview_device='local',radio_device='radio',cw_text='E',lead_ms=0,tail_ms=0,max_tx_seconds=5,
                          special_keywords='Cobia',special_alert='Double ding')
        def create(s):
            ptt=FakePTT();ptts.append(ptt);return ptt
        engine=Engine(settings,lambda *event:events.append(event),audio,speech,create)
        try:
            engine.enable();wait_for(lambda:len(audio.played)==1 and not engine.busy)
            engine.offer(spot())
            wait_for(lambda:engine.fault_generation>0 and not engine.busy)
            self.assertFalse(engine.enabled)
            self.assertEqual(len(ptts),1)  # Only the initial required ID keyed.
            self.assertTrue(any(k=='error' and 'maximum transmit' in v for k,v in events))
        finally:
            engine.shutdown();engine.worker.join(3)
            self.assertFalse(engine.worker.is_alive())

    def test_sounds_are_short_bounded_pcm_with_no_network_or_speech(self):
        for kind in ('Double ding', 'Chime', 'Beep'):
            clip = alert_clip(kind)
            self.assertLess(clip.duration, 1)
            samples = array('h'); samples.frombytes(clip.pcm)
            self.assertGreater(max(samples), 100)
            self.assertLess(max(abs(v) for v in samples), 10000)
            self.assertEqual(samples[-1], 0)
        with self.assertRaises(ValueError): alert_clip('Off')

    def test_sound_prefix_is_in_the_coordinator_clip_only_for_matches(self):
        audio, speech, ptts = FakeAudio(), FakeSpeech(), []
        settings = Settings(preview_device='local', radio_device='radio', cw_text='E', lead_ms=0, tail_ms=0,
                            spacing_seconds=0, special_keywords='Cobia', special_alert='Double ding')
        def create(s):
            ptt = FakePTT(); ptts.append(ptt); return ptt
        engine = Engine(settings, lambda *event:None, audio, speech, create)
        try:
            engine.listen_locally()
            engine.offer(spot())
            wait_for(lambda:len(audio.played)==1 and not engine.busy)
            self.assertGreater(audio.played[0][0].duration, .5)
            self.assertFalse(ptts)
            engine.offer(spot(call='K1ABC', comment='SSB ordinary'))
            wait_for(lambda:len(audio.played)==2 and not engine.busy)
            self.assertAlmostEqual(audio.played[1][0].duration, .1)
            engine.set_local_muted(True)
            engine.offer(spot(call='K2ABC'))
            self.assertFalse(engine.items)
            self.assertEqual(len(audio.played), 2)
        finally:
            engine.shutdown(); engine.worker.join(3)
            self.assertFalse(engine.worker.is_alive())


class RFRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.audio, self.speech, self.ptts, self.events = FakeAudio(), FakeSpeech(), [], []
        self.settings = Settings(radio_device='radio', preview_device='local', cw_text='E', lead_ms=0, tail_ms=0)
        def create(s):
            ptt = FakePTT(); self.ptts.append(ptt); return ptt
        self.engine = Engine(self.settings, lambda *event:self.events.append(event), self.audio, self.speech, create)
        self.connected = True
        self.engine.source_available = lambda:self.connected

    def tearDown(self):
        self.engine.shutdown(); self.engine.worker.join(3)
        self.assertFalse(self.engine.worker.is_alive())

    def arm(self, automatic=True, local=False, muted=False):
        self.engine.configure(replace(self.settings, rf_auto_reconnect=automatic))
        self.engine.enable(local=local, muted=muted)
        wait_for(lambda:len(self.audio.played)==1 and not self.engine.busy)

    def lose(self):
        self.connected = False
        self.engine.stop('Source lost. RF disabled.', defer_cleanup=True)
        wait_for(lambda:not self.engine.busy and not self.engine.monitor_cleanup.is_set())
        self.assertFalse(self.engine.enabled)

    def test_opted_in_recovery_requires_ready_source_and_starts_with_id(self):
        self.arm(local=True, muted=True)
        self.lose()
        self.connected = True
        self.engine._recover_source()
        self.assertFalse(self.engine.enabled)  # An open socket alone is not sign in.
        self.engine.source_restored()
        wait_for(lambda:len(self.audio.played)==2 and not self.engine.busy)
        self.assertTrue(self.engine.enabled)
        self.assertTrue(self.engine.local_enabled); self.assertTrue(self.engine.local_muted)
        self.assertFalse(self.speech.texts)  # CW ID precedes any spot speech.
        self.assertTrue(all(p.calls==['open', True, False, 'close'] for p in self.ptts))

    def test_default_stop_and_never_armed_sessions_cannot_auto_enable(self):
        self.arm(automatic=False); self.lose(); self.connected=True
        self.engine.source_restored(); self.engine._recover_source()
        self.assertFalse(self.engine.enabled)
        self.engine.configure(replace(self.settings, rf_auto_reconnect=True))
        self.lose(); self.connected=True; self.engine.source_restored(); self.engine._recover_source()
        self.assertFalse(self.engine.enabled)

    def test_manual_stop_cancels_pending_recovery(self):
        self.arm(); self.lose(); self.engine.stop()
        self.connected=True; self.engine.source_restored(); self.engine._recover_source()
        self.assertFalse(self.engine.enabled); self.assertIsNone(self.engine.reconnect_rf)

    def test_recovery_keeps_duplicate_suppression_for_completed_spots(self):
        self.arm()
        report=spot()
        self.assertTrue(self.engine.offer(report))
        wait_for(lambda:len(self.audio.played)==2 and not self.engine.busy)
        self.lose();self.connected=True;self.engine.source_restored()
        wait_for(lambda:len(self.audio.played)==3 and not self.engine.busy)
        self.assertFalse(self.engine.offer(report))
        self.assertFalse(self.engine.items)

    def test_repeated_loss_invalidates_prior_readiness(self):
        self.arm(); self.lose()
        with self.engine.lock:
            self.engine.source_restored()
            self.engine.stop('Source lost again', defer_cleanup=True)
            self.assertFalse(self.engine.reconnect_ready)
        wait_for(lambda:not self.engine.busy and not self.engine.monitor_cleanup.is_set())
        self.connected=True; self.engine._recover_source()
        self.assertFalse(self.engine.enabled)
        self.engine.source_restored()
        wait_for(lambda:len(self.audio.played)==2 and not self.engine.busy)

    def test_audio_failure_during_recovery_is_not_retried(self):
        self.arm(); self.lose(); self.audio.fail=True; self.connected=True
        self.engine.source_restored()
        wait_for(lambda:self.engine.fault_generation>0 and not self.engine.busy)
        self.assertFalse(self.engine.enabled); self.assertIsNone(self.engine.reconnect_rf)
        self.engine.source_restored(); self.engine._recover_source()
        self.assertFalse(self.engine.enabled)

    def test_receive_cleanup_fault_cancels_recovery_with_visible_reason(self):
        from unittest.mock import patch
        self.arm()
        with patch.object(self.engine.monitor,'close',side_effect=OSError('synthetic driver failure')):
            self.lose()
            wait_for(lambda:self.engine.fault_generation>0)
        self.connected=True;self.engine.source_restored();self.engine._recover_source()
        self.assertFalse(self.engine.enabled)
        self.assertTrue(any(k=='output' and 'recovery cancelled' in v for k,v in self.events))

    def test_recovery_restarts_receive_monitor_and_waits_for_quiet(self):
        class Monitor:
            def __init__(self): self.clear=False; self.starts=0; self.stream=None
            def start(self, settings): self.starts+=1;self.clear=False;self.stream=object()
            def close(self): self.stream=None
            def ready(self, check_stream=True): return self.stream is not None and self.clear
        monitor=Monitor();self.engine.monitor=monitor
        self.engine.configure(replace(self.settings,rf_auto_reconnect=True,receive_guard=True,receive_half_duplex=False,receive_device='input'))
        self.engine.enable();monitor.clear=True;self.engine.wake.set()
        wait_for(lambda:len(self.audio.played)==1 and not self.engine.busy)
        self.lose();self.connected=True;self.engine.source_restored()
        wait_for(lambda:monitor.starts==2 and self.engine.enabled)
        self.assertEqual(len(self.audio.played),1)
        monitor.clear=True;self.engine.wake.set()
        wait_for(lambda:len(self.audio.played)==2 and not self.engine.busy)

    def test_loss_during_playback_releases_ptt_and_does_not_replay_backlog(self):
        self.arm(); self.audio.block=True; self.audio.entered.clear()
        self.engine.offer(spot())
        self.assertTrue(self.audio.entered.wait(1))
        self.engine.offer(spot(call='K2ABC'))
        self.lose()
        self.assertFalse(self.engine.items)
        self.assertEqual(self.ptts[-1].calls[-2:], [False,'close'])
        self.audio.block=False; self.connected=True; self.engine.source_restored()
        wait_for(lambda:len(self.audio.played)==3 and not self.engine.busy)
        self.assertEqual(len(self.speech.texts),1)
