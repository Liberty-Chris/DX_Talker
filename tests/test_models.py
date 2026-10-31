from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest

from dxtalker.models import UTC, Settings, load_settings, parse_json_feed, parse_line, save_settings


class SpotTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 31, 0, 1, tzinfo=UTC)

    def test_midnight_portable_calls_and_fractional_frequency(self):
        spot = parse_line("DX de W4MR: 14025.5 WB4IUY/P CQ 2359Z", "test", self.now)
        self.assertEqual(spot.timestamp.day, 30)
        self.assertEqual(spot.frequency_khz, Decimal("14025.5"))
        self.assertIn("stroke Papa", spot.speech)
        self.assertIn("one four zero two five point five kilohertz", spot.speech)

    def test_does_not_speak_chat_or_unvalidated_content(self):
        for line in ("To ALL de W4MR: hello", "login:", "DX de W4MR: nan WB4IUY 0001Z",
                     "DX de W4MR: 14025 WB4IUY no time", "DX de W4MR: 14025 HELLO 0001Z",
                     "DX de W4MR: 0 WB4IUY 0001Z", "DX de W4MR: 14025 WB4IUY 9999Z"):
            with self.subTest(line=line):
                self.assertIsNone(parse_line(line, "test", self.now))

    def test_near_future_is_tolerated_but_far_future_is_rejected(self):
        self.assertIsNotNone(parse_line("DX de N0CALL: 7074 KT4BN 0002Z", "test", self.now))
        self.assertIsNone(parse_line("DX de N0CALL: 7074 KT4BN 0010Z", "test", self.now))

    def test_json_requires_valid_timezone_calls_and_finite_frequency(self):
        base = {"dx_call": "KT4BN", "spotter": "N0CALL", "frequency_khz": "7074", "time": "2026-10-31T00:01:00Z"}
        values = [base, {**base, "frequency_khz": "NaN"}, {**base, "time": "2026-10-31T00:01:00"},
                  {**base, "dx_call": "hello world"}, "not a spot"]
        spots = parse_json_feed(json.dumps(values).encode(), "test", self.now)
        self.assertEqual(len(spots), 1)
        self.assertEqual(spots[0].dx_call, "KT4BN")

    def test_json_top_level_and_capacity(self):
        for payload in (b"{}", json.dumps([{}] * 2001).encode()):
            with self.assertRaises(ValueError):
                parse_json_feed(payload, "test", self.now)

    def test_comments_are_not_in_speech(self):
        spot = parse_line("DX de W4MR: 14025 WB4IUY malicious comment 0001Z", "test", self.now)
        self.assertNotIn("malicious", spot.speech)


class SettingsTests(unittest.TestCase):
    def test_defaults_and_roundtrip_without_secrets_or_armed_state(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "settings.json"
            self.assertEqual(load_settings(path), Settings())
            s = replace(Settings(), login="KF4DBX", cw_text="KF4DBX", min_khz=7000.0)
            save_settings(s, path)
            self.assertEqual(load_settings(path), s)
            data = json.loads(path.read_text())
            self.assertNotIn("password", data)
            self.assertNotIn("enabled", data)
            self.assertFalse(path.with_suffix(".tmp").exists())

    def test_unknown_schema_does_not_overwrite_settings(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "settings.json"
            original = '{"schema_version": 20}'
            path.write_text(original)
            with self.assertRaises(ValueError):
                load_settings(path)
            self.assertEqual(path.read_text(), original)

    def test_reject_bad_numbers_types_and_newlines(self):
        for changes in ({"port": 0}, {"cw_wpm": 0}, {"id_minutes": 0}, {"max_tx_seconds": 500},
                        {"min_khz": float("nan")}, {"max_khz": float("inf")}, {"host": "x\npassword"},
                        {"lead_ms": True}, {"ptt_method": "magic"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(Settings(), **changes).validate()

    def test_url_validation(self):
        for url in ("http://example.org/spots", "https://user:secret@example.org/spots", "file:///spots", "https://example.org/#token"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                replace(Settings(), source_type="HTTPS JSON", feed_url=url).validate_connection()
        replace(Settings(), source_type="HTTPS JSON", feed_url="https://example.org/spots").validate_connection()

    def test_rf_requires_device_ptt_and_id(self):
        with self.assertRaises(ValueError):
            Settings().validate_rf()
        s = replace(Settings(), radio_device="chosen", cw_text="KF4DBX")
        s.validate_rf()
        with self.assertRaises(ValueError):
            replace(s, ptt_method="RTS").validate_rf()
        replace(s, ptt_method="RTS", serial_port="COM10").validate_rf()
        with self.assertRaises(ValueError):
            replace(s, id_mode="Voice").validate_rf()
