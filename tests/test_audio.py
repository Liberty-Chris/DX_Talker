from array import array
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import time
import wave

from dxtalker.audio import AudioOutput, Clip, join_clips, morse_clip, validate_morse, wav_clip


class AudioTests(unittest.TestCase):
    def test_paris_timing_and_word_spacing(self):
        # PARIS has 43 units before its trailing word gap. At 20 WPM one unit is 60 ms.
        clip = morse_clip("PARIS", 20)
        self.assertAlmostEqual(clip.duration, 43 * 0.06, places=2)
        self.assertAlmostEqual(morse_clip("E E", 20).duration, 9 * 0.06, places=2)

    def test_tone_has_silenced_edges_and_bounded_amplitude(self):
        clip = morse_clip("E", 20)
        samples = array("h")
        samples.frombytes(clip.pcm)
        self.assertEqual(samples[0], 0)
        self.assertEqual(samples[-1], 0)
        self.assertLessEqual(max(abs(v) for v in samples), 13000)

    def test_unsupported_or_excessively_long_morse_fails(self):
        for text in ("", "KF4DBX!", "E" * 121):
            with self.assertRaises(ValueError):
                validate_morse(text)
        with self.assertRaises(ValueError):
            morse_clip("0" * 120, 5)

    def test_wav_contract_and_combined_ids(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "id.wav"
            with wave.open(str(path), "wb") as out:
                out.setparams((1, 2, 22050, 0, "NONE", ""))
                out.writeframes(b"\0\0" * 22050)
            clip = wav_clip(path)
            self.assertEqual(clip.duration, 1)
            self.assertEqual(join_clips([clip, clip]).duration, 2.5)
            with self.assertRaises(ValueError):
                join_clips([Clip(b"\0\0" * 100, 44100), clip])
            with wave.open(str(path), "wb") as out:
                out.setparams((1, 1, 22050, 0, "NONE", ""))
                out.writeframes(b"\0" * 100)
            with self.assertRaises(ValueError):
                wav_clip(path)

    def test_exact_audio_selection_rejects_missing_and_duplicate_devices(self):
        class FakeSD:
            @staticmethod
            def query_hostapis():
                return [{"name": "Windows WASAPI"}]

            @staticmethod
            def query_devices():
                return [{"name": "USB", "hostapi": 0, "max_output_channels": 2}] * 2

        with patch.dict("sys.modules", {"sounddevice": FakeSD}):
            for key in ("Windows WASAPI :: USB", "Windows WASAPI :: Missing"):
                with self.assertRaises(ValueError):
                    AudioOutput.resolve(key, 1)

    def test_playback_volume_completion_and_underflow(self):
        class Stop(Exception):
            pass

        class Abort(Exception):
            pass

        for underflow in (False, True):
            captured = []

            class Stream:
                def __init__(self, **kwargs):
                    self.kwargs = kwargs
                    self.active = True

                def __enter__(self):
                    output = bytearray(8)
                    try:
                        self.kwargs["callback"](output, 4, None, underflow)
                    except (Stop, Abort):
                        pass
                    captured.append(output)
                    self.kwargs["finished_callback"]()
                    return self

                def __exit__(self, *args):
                    pass

            fake = SimpleNamespace(RawOutputStream=Stream, CallbackStop=Stop, CallbackAbort=Abort)
            audio = AudioOutput()
            samples = array("h", [1000, -1000])
            with patch.dict("sys.modules", {"sounddevice": fake}), patch.object(audio, "resolve", return_value=4):
                if underflow:
                    with self.assertRaises(RuntimeError):
                        audio.play(Clip(samples.tobytes()), "chosen", 50, threading.Event(), time.monotonic() + 1)
                else:
                    audio.play(Clip(samples.tobytes()), "chosen", 50, threading.Event(), time.monotonic() + 1)
                    decoded = array("h")
                    decoded.frombytes(captured[0])
                    self.assertEqual(list(decoded), [500, -500, 0, 0])

    def test_local_volume_reader_changes_between_buffers_without_restart(self):
        class Stop(Exception):pass
        class Abort(Exception):pass
        captured=[];level=[50]
        class Stream:
            active=True
            def __init__(self,**kwargs):self.kwargs=kwargs
            def __enter__(self):
                for percent in (50,0,100):
                    level[0]=percent;out=bytearray(4)
                    try:self.kwargs['callback'](out,2,None,False)
                    except Stop:pass
                    samples=array('h');samples.frombytes(out);captured.append(list(samples))
                self.kwargs['finished_callback']();return self
            def __exit__(self,*args):pass
        audio=AudioOutput();audio.volume_reader=lambda:level[0]
        fake=SimpleNamespace(RawOutputStream=Stream,CallbackStop=Stop,CallbackAbort=Abort)
        with patch.dict('sys.modules',{'sounddevice':fake}),patch.object(audio,'resolve',return_value=0):
            audio.play(Clip(array('h',[1000,-1000]*3).tobytes()),'local',70,threading.Event(),time.monotonic()+2)
        self.assertEqual(captured,[[500,-500],[0,0],[1000,-1000]])

    def test_normal_finish_between_wait_and_stream_state_check_is_not_a_fault(self):
        class Stop(Exception):pass
        class Abort(Exception):pass
        class Stream:
            def __init__(self,**kwargs):self.kwargs=kwargs
            def __enter__(self):
                try:self.kwargs['callback'](bytearray(4),2,None,False)
                except Stop:pass
                return self
            @property
            def active(self):
                # The 20 ms wait has timed out; native completion is observed
                # just before the main thread reads the inactive stream state.
                self.kwargs['finished_callback']()
                return False
            def __exit__(self,*args):pass
        fake=SimpleNamespace(RawOutputStream=Stream,CallbackStop=Stop,CallbackAbort=Abort)
        audio=AudioOutput()
        with patch.dict('sys.modules',{'sounddevice':fake}),patch.object(audio,'resolve',return_value=0):
            audio.play(Clip(b'\0\0'*2),'chosen',100,threading.Event(),time.monotonic()+1)

    def test_finish_notification_can_arrive_after_inactive_is_first_observed(self):
        class Stop(Exception):pass
        class Abort(Exception):pass
        class Stream:
            def __init__(self,**kwargs):self.kwargs=kwargs;self.queries=0
            def __enter__(self):
                try:self.kwargs['callback'](bytearray(4),2,None,False)
                except Stop:pass
                return self
            @property
            def active(self):
                self.queries+=1
                if self.queries==2:self.kwargs['finished_callback']()
                return False
            def __exit__(self,*args):pass
        fake=SimpleNamespace(RawOutputStream=Stream,CallbackStop=Stop,CallbackAbort=Abort)
        audio=AudioOutput()
        with patch.dict('sys.modules',{'sounddevice':fake}),patch.object(audio,'resolve',return_value=0):
            audio.play(Clip(b'\0\0'*2),'chosen',100,threading.Event(),time.monotonic()+2)

    def test_genuine_early_stream_stop_has_numeric_evidence_and_stays_a_fault(self):
        from dxtalker.audio import AudioPlaybackError
        closed=[]
        class Stream:
            active=False
            def __init__(self,**kwargs):self.kwargs=kwargs
            def __enter__(self):self.kwargs['callback'](bytearray(2),1,None,False);return self
            def __exit__(self,*args):closed.append(True)
        fake=SimpleNamespace(RawOutputStream=Stream)
        audio=AudioOutput()
        with patch.dict('sys.modules',{'sounddevice':fake}),patch.object(audio,'resolve',return_value=0):
            with self.assertRaises(AudioPlaybackError) as error:
                audio.play(Clip(b'\0\0'*4),'chosen',100,threading.Event(),time.monotonic()+1)
        self.assertEqual(error.exception.code,'audio_stream_stopped')
        self.assertEqual({key:error.exception.context[key] for key in ('frames_queued','frames_expected','sample_rate','channels')},dict(frames_queued=1,frames_expected=4,sample_rate=22050,channels=1))
        self.assertEqual(error.exception.context['status_flags'], [])
        self.assertEqual(closed,[True])

    def test_missing_finish_signal_is_bounded_and_cancellation_during_grace_still_stops(self):
        from dxtalker.audio import AudioPlaybackError,Cancelled
        class Stop(Exception):pass
        class Abort(Exception):pass
        for cancelled in (False,True):
            cancel=threading.Event();aborted=[]
            class Stream:
                def __init__(self,**kwargs):self.kwargs=kwargs
                def __enter__(self):
                    try:self.kwargs['callback'](bytearray(4),2,None,False)
                    except Stop:pass
                    return self
                @property
                def active(self):
                    if cancelled:cancel.set()
                    return False
                def abort(self):aborted.append(True)
                def __exit__(self,*args):pass
            fake=SimpleNamespace(RawOutputStream=Stream,CallbackStop=Stop,CallbackAbort=Abort)
            tick=[0]
            def clock():tick[0]+=.05;return tick[0]
            audio=AudioOutput()
            with patch.dict('sys.modules',{'sounddevice':fake}),patch.object(audio,'resolve',return_value=0),patch('dxtalker.audio.time.monotonic',side_effect=clock):
                with self.assertRaises(Cancelled if cancelled else AudioPlaybackError) as error:
                    audio.play(Clip(b'\0\0'*2),'chosen',100,cancel,100)
            if cancelled:self.assertEqual(aborted,[True])
            else:self.assertEqual(error.exception.code,'audio_finish_unconfirmed')

    def playback_scenario(self, flags, *, tick=.1, cancel=None, deadline=1000):
        from dxtalker.audio import AudioPlaybackError
        class Stop(Exception): pass
        class Abort(Exception): pass
        class Status:
            def __init__(self, names):
                for name in names: setattr(self, name, True)
            def __bool__(self): return bool(vars(self))
        captured=[]; settings=[]
        class Stream:
            active = False
            latency = .2
            def __init__(self, **kwargs): self.options=kwargs; settings.append(kwargs)
            def __enter__(self):
                for names in flags:
                    output=bytearray(4)
                    try: self.options['callback'](output,2,None,Status(names))
                    except (Stop,Abort): break
                    captured.append(bytes(output))
                self.options['finished_callback']()
                return self
            def __exit__(self,*args): pass
        fake=SimpleNamespace(RawOutputStream=Stream,CallbackStop=Stop,CallbackAbort=Abort)
        audio=AudioOutput(); clock=[0]
        def now():
            clock[0]+=tick
            return clock[0]
        with patch.dict('sys.modules',{'sounddevice':fake}),patch.object(audio,'resolve',return_value=0),patch('dxtalker.audio.time.monotonic',side_effect=now):
            report=audio.play(Clip(b'\x01\x00'*len(flags)*2),'Windows WASAPI :: PRIVATE DEVICE',100,cancel or threading.Event(),deadline)
        return report,settings,captured

    def test_screensaver_scheduling_glitch_recovers_with_adaptive_buffering(self):
        report,settings,captured=self.playback_scenario([[],['output_underflow'],[],[]])
        self.assertEqual(report['output_underflows'],1)
        self.assertEqual(report['status_flags'],['output_underflow'])
        self.assertEqual(report['latency_seconds'],.2)
        self.assertEqual(report['max_callback_gap_ms'],100)
        self.assertEqual(settings[0]['blocksize'],0)
        self.assertEqual(settings[0]['latency'],'high')
        self.assertNotIn('PRIVATE',str(report))
        self.assertEqual(len(captured),3)

    def test_priming_is_informational_and_does_not_disable_audio(self):
        report,unused,unused=self.playback_scenario([['priming_output'],[]])
        self.assertIsNone(report)

    def test_persistent_or_repeated_underruns_still_stop(self):
        from dxtalker.audio import AudioPlaybackError
        for count,tick in [(4,.1),(9,3)]:
            with self.assertRaises(AudioPlaybackError) as failure:
                self.playback_scenario([['output_underflow']]*count,tick=tick)
            self.assertEqual(failure.exception.code,'audio_underflow_persistent')
            self.assertEqual(failure.exception.context['output_underflows'],count)
            self.assertLess(failure.exception.context['frames_queued'],failure.exception.context['frames_expected'])

    def test_other_audio_flags_are_not_misclassified_as_recoverable(self):
        from dxtalker.audio import AudioPlaybackError
        for flags in [['output_overflow'],['input_overflow','output_underflow']]:
            with self.assertRaises(AudioPlaybackError) as failure:
                self.playback_scenario([flags,[]])
            self.assertEqual(failure.exception.code,'audio_stream_fault')
            self.assertEqual(failure.exception.context['status_flags'],sorted(flags))

    def test_underrun_recovery_never_overrides_cancel_or_deadline(self):
        from dxtalker.audio import Cancelled
        cancelled=threading.Event(); cancelled.set()
        with self.assertRaises(Cancelled):self.playback_scenario([['output_underflow']],cancel=cancelled)
        with self.assertRaises(TimeoutError):self.playback_scenario([['output_underflow']],deadline=0)
