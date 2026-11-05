from array import array
from dataclasses import replace
from datetime import datetime
import threading
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from dxtalker.audio import Clip, scale_clip
from dxtalker.models import Settings, UTC, parse_line
from dxtalker.speech import SpeechService, normalize_clip, plan_ssml, spot_plan


class SpeechTests(unittest.TestCase):
    def test_phonetics_and_precise_character_group_pauses(self):
        now = datetime.now(UTC)
        spot = parse_line(f"DX de N0CALL: 14025.5 WB4IUY/P CQ {now:%H%M}Z", "cluster", now)
        settings = replace(Settings(), character_pause_ms=125, group_pause_ms=650)
        plan = spot_plan(spot, settings)
        self.assertEqual(plan[0], ("New DX on", 650))
        self.assertIn(("four", 125), plan)
        self.assertIn(("Papa", 650), plan)
        self.assertEqual(plan[-1], ("five kilohertz", 0))
        root = ET.fromstring(plan_ssml(plan))
        breaks = root.findall("{http://www.w3.org/2001/10/synthesis}break")
        self.assertEqual([x.attrib["time"] for x in breaks].count("650ms"), 2)
        self.assertNotIn("CQ", ET.tostring(root).decode())

    def test_ssml_escapes_operator_text(self):
        root = ET.fromstring(plan_ssml([('hello <voice> & text', 0)]))
        self.assertEqual(root.text, 'hello <voice> & text ')

    def test_windows_provider_receives_voice_gender_speed_and_ssml(self):
        now = datetime.now(UTC)
        spot = parse_line(f"DX de N0CALL: 7074 KT4BN {now:%H%M}Z", "cluster", now)
        settings = Settings(voice_gender="Female", speech_rate=-3)
        with patch("dxtalker.speech.WindowsSpeech") as provider:
            SpeechService().render_spot(spot, settings, threading.Event())
            args, kwargs = provider.return_value.render.call_args
            self.assertEqual(args[2], -3)
            self.assertEqual(args[4], "Female")
            self.assertTrue(kwargs["ssml"])

    def test_neural_missing_model_fails_before_output(self):
        with self.assertRaises(ValueError):
            SpeechService().render_configured("test", Settings(speech_provider="Piper"), threading.Event())

    def test_independent_pcm_gain_and_neural_rate_normalization(self):
        clip = Clip(array("h", [10000, -10000] * 8000).tobytes(), rate=16000)
        quieter = scale_clip(clip, 25)
        self.assertEqual(array("h", quieter.pcm)[0], 2500)
        normalized = normalize_clip(clip)
        self.assertEqual(normalized.rate, 22050)
        self.assertAlmostEqual(normalized.duration, 1, places=3)

    def test_neural_cli_fixture_receives_model_and_speed_and_pcm_pauses(self):
        import tempfile
        import wave
        with tempfile.TemporaryDirectory() as folder:
            folder = __import__('pathlib').Path(folder)
            exe, model = folder / "piper.exe", folder / "voice.onnx"
            exe.touch()
            model.touch()
            model.with_suffix(".onnx.json").write_text("{}")
            commands = []
            environments = []
            class Process:
                returncode = 0
                def __init__(self, command, **kwargs):
                    commands.append(command)
                    environments.append(kwargs["env"])
                    path = command[command.index("--output_file") + 1]
                    with wave.open(path, 'wb') as output:
                        output.setparams((1, 2, 22050, 0, 'NONE', 'not compressed'))
                        output.writeframes(b'\0\0' * 2205)
                def __enter__(self): return self
                def __exit__(self, *args): pass
                def communicate(self, input=None, timeout=None): return None, None
            settings = Settings(speech_provider="Piper", piper_executable=str(exe), piper_model=str(model), speech_rate=5)
            now = datetime.now(UTC)
            spot = parse_line(f"DX de N0CALL: 7074 KT4BN {now:%H%M}Z", "test", now)
            with patch("dxtalker.speech.subprocess.Popen", Process):
                clip = SpeechService().render_spot(spot, settings, threading.Event())
            self.assertEqual(len(commands), 3)
            self.assertTrue(all(env["ORT_DISABLE_TELEMETRY"] == "1" for env in environments))
            self.assertEqual(commands[0][commands[0].index('--model') + 1], str(model))
            self.assertAlmostEqual(clip.duration, .3 + .9, places=3)
