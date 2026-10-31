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
        self.entered = threading.Event()
        self.block = False
        self.fail = False

    def resolve(self, key, channels):
        return 0

    def play(self, clip, device, volume, cancel, deadline):
        self.played.append((clip, device))
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

    def tearDown(self):
        self.engine.shutdown()
        self.engine.worker.join(3)
        self.assertFalse(self.engine.worker.is_alive())

    def spot(self, dx="KT4BN", minute_offset=0):
        now = datetime.now(UTC)
        stamp = now + timedelta(minutes=minute_offset)
        return parse_line(f"DX de N0CALL: 7074 {dx} CQ {stamp:%H%M}Z", "test", now)

    def enable_and_id(self):
        self.engine.enable()
        wait_for(lambda: len(self.audio.played) >= 1 and not self.engine.busy)

    def test_startup_is_disabled_and_does_not_queue_spots(self):
        self.assertFalse(self.engine.enabled)
        self.assertFalse(self.engine.offer(self.spot()))
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

    def test_source_gate_prevents_enable_and_transmit(self):
        self.engine.rf_allowed = lambda: False
        with self.assertRaises(ValueError):
            self.engine.enable()
        with self.assertRaises(Cancelled):
            self.engine._transmit(Clip(b"\0\0" * 100), self.settings)
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
