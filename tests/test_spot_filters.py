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
                self.assertEqual(filtering.mode_of(spot.comment,spot.mode,spot.frequency_khz), case['mode'])
                self.assertEqual(sorted(filtering.activities_of(spot.comment)), case['activities'])
                self.assertEqual(filtering.matches(spot, replace(Settings(), **case['filters'])), case['match'])
                self.assertNotIn('POTA', spot.speech)

    def test_android_and_desktop_use_identical_segments_and_fixtures(self):
        import re
        root=Path(__file__).resolve().parent.parent
        android=(root/'android/app/src/main/java/club/dxtalker/android/SpotFilters.kt').read_text()
        spans=[(int(lo),int(hi),mode) for lo,hi,mode in re.findall(r'Triple\((\d+),(\d+),"([A-Z0-9]+)"\)',android)]
        self.assertEqual(spans,list(filtering.MODE_SEGMENTS))
        self.assertEqual((root/'tests/fixtures/spot_filters.json').read_bytes(),(root/'android/app/src/test/resources/spot_filters.json').read_bytes())

    def test_none_survives_settings_and_transfer_roundtrip(self):
        settings=Settings(filter_bands='None',filter_modes='None',filter_activities='None').validate()
        profiles=[dict(name='Test',connection={key:getattr(settings,key) for key in transfer.SOURCE_FIELDS})]
        data=transfer.decode(transfer.encode(transfer.document(profiles,settings)))
        for key in ('filter_bands','filter_modes','filter_activities'):
            self.assertEqual(data['filters'][key],'None')
            with self.assertRaises(ValueError):replace(Settings(),**{key:'None,CW'}).validate()

    def test_activity_wording_preference_survives_presets_and_transfer_without_bypassing_filters(self):
        from dxtalker.listening import snapshot,validate_presets
        settings=replace(Settings(),activity_announcements=True,filter_bands='40m',filter_modes='CW',filter_activities='POTA',license_class='General')
        preset=json.dumps({'Activity':snapshot(settings)})
        self.assertTrue(validate_presets(preset)['Activity']['activity_announcements'])
        profiles=[dict(name='Test',connection={key:getattr(settings,key) for key in transfer.SOURCE_FIELDS})]
        self.assertTrue(transfer.decode(transfer.encode(transfer.document(profiles,settings)))['filters']['activity_announcements'])
        for value in ('true',1,None):
            with self.assertRaises(ValueError):replace(settings,activity_announcements=value).validate()
        now=datetime.now(UTC)
        spot=parse_line(f'DX de N0CALL: 14250 WB4IUY POTA SSB {now:%H%M}Z','test',now)
        self.assertEqual(filtering.rejection(spot,settings),'Band')
        self.assertEqual(filtering.rejection(spot,replace(settings,filter_bands='20m')),'Mode')
        self.assertEqual(filtering.rejection(spot,replace(settings,filter_bands='20m',filter_modes='SSB',license_class='Novice')),'Outside selected license segments')
        self.assertEqual(filtering.rejection(spot,replace(settings,filter_bands='20m',filter_modes='SSB',filter_dx_countries='CA')),'Location unknown')
        self.assertEqual(filtering.activity_tags('POTATO FOTAX SOTAX'),())
        self.assertFalse(filtering.activity_style(replace(settings,activity_announcements=False,filter_activities='POTA,General')))
        self.assertFalse(filtering.activity_style(replace(settings,activity_announcements=False,filter_activities='None')))

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
        self.assertEqual(data['version'],3)
        self.assertEqual(transfer.decode(transfer.encode(data,qr=True)),data)
        spot=parse_line('DX de N0CALL: 14074 WB4IUY FT8 POTA private-comment 1234Z','test',datetime(2026,11,6,12,34,tzinfo=UTC))
        with tempfile.TemporaryDirectory() as folder:
            history=History(replace(settings,log_directory=folder))
            history.spot(spot);history.close()
            text=(Path(folder)/'history.jsonl').read_text()
            self.assertNotIn('private-comment',text)
            self.assertNotIn('POTA',text)
