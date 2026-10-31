from array import array
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
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
