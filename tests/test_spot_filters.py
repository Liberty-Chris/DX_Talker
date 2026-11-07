from dataclasses import replace
from datetime import datetime
import json
from pathlib import Path
import tempfile
import unittest
from dxtalker import filtering, transfer
from dxtalker.models import Settings, UTC, parse_line, parse_json_feed
from dxtalker.history import History


class SpotFilterTests(unittest.TestCase):
    def test_shared_cases(self):
        for case in json.loads((Path(__file__).parent/'fixtures/spot_filters.json').read_text()):
            with self.subTest(case=case):
                spot = parse_line(case['line'], 'fixture', datetime(2026,11,6,12,34,tzinfo=UTC))
                self.assertIsNotNone(spot)
                self.assertEqual(filtering.mode_of(spot.comment), case['mode'])
                self.assertEqual(sorted(filtering.activities_of(spot.comment)), case['activities'])
                self.assertEqual(filtering.matches(spot, replace(Settings(), **case['filters'])), case['match'])
                self.assertNotIn('POTA', spot.speech)

    def test_explicit_mode_wins_and_bad_metadata_is_bounded(self):
        now=datetime.now(UTC)
        payload=[dict(dx_call='WB4IUY',spotter='N0CALL',frequency_khz='14074',time=now.isoformat(),comment='FT8 POTA'+chr(0)+'x'*300,mode='USB')]
        spot=parse_json_feed(json.dumps(payload).encode(),'test',now)[0]
        self.assertEqual(filtering.mode_of(spot.comment,spot.mode),'SSB')
        self.assertEqual(len(spot.comment),160)
        self.assertNotIn(chr(0),spot.comment)
        self.assertEqual(filtering.mode_of('FT8 CW'),'Unknown')
        self.assertEqual(filtering.mode_of('FT8','nonsense'),'Unknown')
        self.assertEqual(filtering.activities_of('SPOTATO FOTAX'),{'General'})

    def test_unknowns_are_not_guessed_from_frequency_and_invalid_settings_rejected(self):
        spot=parse_line('DX de N0CALL: 14074 WB4IUY CQ 1234Z','test',datetime(2026,11,6,12,34,tzinfo=UTC))
        self.assertFalse(filtering.matches(spot,replace(Settings(),filter_modes='FT8')))
        self.assertTrue(filtering.matches(spot,replace(Settings(),filter_modes='Unknown')))
        for key,value in [('filter_modes','FT9'),('filter_activities','POTA,POTA'),('filter_bands','20m,invalid')]:
            with self.assertRaises(ValueError):replace(Settings(),**{key:value}).validate()

    def test_transfer_v2_roundtrip_and_comment_not_written_to_history(self):
        settings=replace(Settings(),filter_modes='FT8,Unknown',filter_activities='POTA,SOTA',filter_bands='20m,40m')
        profiles=[dict(name='Test',connection={key:getattr(settings,key) for key in transfer.SOURCE_FIELDS})]
        data=transfer.document(profiles,settings)
        self.assertEqual(data['version'],2)
        self.assertEqual(transfer.decode(transfer.encode(data,qr=True)),data)
        spot=parse_line('DX de N0CALL: 14074 WB4IUY FT8 POTA private-comment 1234Z','test',datetime(2026,11,6,12,34,tzinfo=UTC))
        with tempfile.TemporaryDirectory() as folder:
            history=History(replace(settings,log_directory=folder))
            history.spot(spot);history.close()
            text=(Path(folder)/'history.jsonl').read_text()
            self.assertNotIn('private-comment',text)
            self.assertNotIn('POTA',text)
