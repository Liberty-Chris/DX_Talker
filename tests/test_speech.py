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
        self.assertIn(("five kilohertz", 650), plan)
        self.assertEqual(plan[-1], ("Papa", 0))
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
        settings = Settings(speech_provider="Windows", voice_gender="Female", speech_rate=-3)
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


    def test_frequency_precedes_callsign_and_unit_conversion_keeps_precision(self):
        from decimal import Decimal
        now = datetime.now(UTC)
        spot = parse_line(f"DX de N0CALL: 14025.5 WB4IUY/P {now:%H%M}Z", "cluster", now)
        self.assertEqual(spot.frequency_text("kHz"), "14025.5")
        self.assertEqual(spot.frequency_text("MHz"), "14.0255")
        self.assertEqual(spot.frequency_khz, Decimal("14025.5"))
        plan = spot_plan(spot, Settings(frequency_unit="MHz"))
        self.assertEqual(plan[1][0], "one four point zero two five five megahertz")
        self.assertEqual(plan[2][0], "Whiskey Bravo four India Uniform Yankee stroke Papa")
        self.assertTrue(spot.speech.startswith("New DX on. one four zero two five"))
        for freq, expected in (("7074", "7.074"), ("50125", "50.125"), ("1807", "1.807"), ("1000", "1"), ("1.0001", "0.0010001")):
            value = parse_line(f"DX de N0CALL: {freq} WB4IUY {now:%H%M}Z", "cluster", now)
            self.assertEqual(value.frequency_text("MHz"), expected)


    def test_every_order_and_inclusion_with_optional_units_and_pauses(self):
        import itertools
        now = datetime.now(UTC)
        spot = parse_line(f"DX de N0CALL: 14025.5 WB4IUY/P untrusted comment {now:%H%M}Z", "cluster", now)
        for order in itertools.permutations(('intro', 'callsign', 'frequency')):
            for flags in itertools.product((False, True), repeat=3):
                if not any(flags):
                    continue
                included = dict(zip(('intro', 'callsign', 'frequency'), flags))
                for unit, units in (('kHz', 'kilohertz'), ('MHz', 'megahertz')):
                    for speak_units in (False, True):
                        for pause in (0, 125):
                            settings = Settings(announcement_order=','.join(order), announcement_intro='New DX',
                                                include_intro=flags[0], include_callsign=flags[1], include_frequency=flags[2],
                                                frequency_unit=unit, speak_units=speak_units, character_pause_ms=pause,
                                                group_pause_ms=650)
                            frequency = ('one four zero two five point five' if unit == 'kHz' else
                                         'one four point zero two five five') + (' ' + units if speak_units else '')
                            text = {'intro': 'New DX', 'callsign': 'Whiskey Bravo four India Uniform Yankee stroke Papa',
                                    'frequency': frequency}
                            expected = [text[name] for name in order if included[name]]
                            plan = spot_plan(spot, settings)
                            self.assertEqual(' '.join(t for t, _ in plan), ' '.join(expected))
                            self.assertEqual(plan[-1][1], 0)
                            self.assertEqual(sum(ms == 650 for _, ms in plan), len(expected) - 1)
                            self.assertNotIn('untrusted', plan_ssml(plan))
        self.assertEqual(str(spot.frequency_khz), '14025.5')

    def test_custom_intro_is_escaped_and_both_providers_share_the_format(self):
        now = datetime.now(UTC)
        spot = parse_line(f"DX de N0CALL: 7074 KT4BN {now:%H%M}Z", 'cluster', now)
        for provider in ('Windows', 'Piper'):
            settings = Settings(speech_provider=provider, announcement_intro='DX <notice> & news',
                                announcement_order='callsign,intro,frequency', speak_units=False)
            with patch.object(SpeechService, '_render', return_value=Clip(b'\0\0' * 100)) as render:
                SpeechService().render_spot(spot, settings, threading.Event())
            plan = render.call_args.args[0]
            self.assertEqual(plan[0][0], 'Kilo Tango four Bravo November')
            self.assertEqual(plan[-1][0], 'seven zero seven four')
            root = ET.fromstring(plan_ssml(plan))
            self.assertNotIn('<notice>', plan_ssml(plan))
            self.assertIn('DX <notice> & news', ''.join(root.itertext()))
