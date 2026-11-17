import csv
from dataclasses import replace
from datetime import datetime
from decimal import Decimal
import hashlib
from pathlib import Path
import unittest

from dxtalker.band_table import policy_eligibility
from dxtalker.band_table_data import SOURCE_SHA256, INFERENCE
from dxtalker.filtering import mode_of, MODES, matches, activities_of, rejection
from dxtalker.models import Settings, UTC, make_spot
from dxtalker import transfer

ROOT = Path(__file__).parents[1]


class BandTableTests(unittest.TestCase):
    def test_original_csv_hash_and_every_policy_boundary(self):
        source = ROOT / 'docs/reference/band_table.csv'
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), SOURCE_SHA256)
        with source.open(encoding='utf-8-sig', newline='') as stream:
            rows = [r for r in csv.reader(stream) if r][1:]
        indexed = {}
        for row in rows:
            if row[0] != 'License filter': continue
            for mode in row[7].split(';'):
                indexed.setdefault((row[8], mode.strip()), []).append(row)
        for (cls, mode), rules in indexed.items():
            probes = {Decimal(r[i]) + delta for r in rules for i in (2, 3) for delta in (Decimal('0'), Decimal('-.0001'), Decimal('.0001'))}
            for f in probes:
                found = {r[9] for r in rules if (f == Decimal(r[2]) if r[6] == 'Discrete reported frequency' else Decimal(r[2]) <= f < Decimal(r[3]))}
                expected = 'eligible' if 'Eligible' in found else 'unknown' if 'Unverified' in found else 'outside'
                with self.subTest(cls=cls, mode=mode, f=f):
                    self.assertEqual(policy_eligibility(f, mode, cls), expected)

    def test_inference_and_unknown_semantics_are_preserved(self):
        self.assertEqual(len(INFERENCE), 11)
        self.assertEqual(mode_of('', frequency_khz=3540), 'CW')
        self.assertEqual(mode_of('', frequency_khz=7035), 'CW')
        self.assertEqual(mode_of('', frequency_khz=14074), 'Unknown')
        self.assertEqual(mode_of('DIGITAL', frequency_khz=3540), 'DIGITAL')
        self.assertEqual(mode_of('CW DIGITAL', frequency_khz=3540), 'Unknown')
        self.assertEqual(mode_of('JT65', frequency_khz=3540), 'Unknown')
        for mode in set(MODES) - {'Unknown'}:
            self.assertEqual(mode_of(mode, frequency_khz=3540), mode)
            self.assertEqual(mode_of('', mode.lower(), 3540), mode)
        self.assertEqual(mode_of('MFSK16'), 'MFSK')
        self.assertEqual(mode_of('PSK31'), 'PSK')

    def test_activity_tags_special_calls_and_remaining_filters(self):
        now = datetime.now(UTC)
        spot = make_spot('W1AW/3', '14225', 'KF4DBX', now, 'test', now, 'SSB IOTA')
        for tag in ('POTA', 'SOTA', 'FOTA', 'IOTA', 'JOTA', 'LLOTA'):
            tagged = replace(spot, comment='SSB ' + tag)
            self.assertTrue(matches(tagged, Settings(filter_activities=tag)))
            self.assertEqual(activities_of('NOT' + tag), {'General'})
        s = Settings(filter_activities='POTA', special_calls='TZ4AM,W1AW', special_calls_only=True)
        self.assertTrue(matches(spot, s))
        self.assertFalse(matches(spot, replace(s, special_calls_portable=False)))
        self.assertFalse(matches(replace(spot, dx_call='W1AWX'), s))
        self.assertFalse(matches(spot, replace(s, filter_modes='CW')))
        self.assertTrue(matches(spot, replace(s, filter_bands='40m')))
        self.assertFalse(matches(spot, replace(s, filter_dx_countries='JP')))
        self.assertTrue(matches(spot, replace(s, special_calls_only=False)))
        self.assertFalse(matches(replace(spot, dx_call='K1ABC'), replace(s, special_calls_only=False)))

    def test_filters_transfer_and_old_settings_defaults(self):
        s = Settings(filter_modes='WSPR,DIGITAL,Unknown', filter_activities='IOTA,LLOTA', special_calls='W1AW,TZ4AM', special_calls_only=True)
        profiles = [dict(name='Test', connection={key: getattr(s, key) for key in transfer.SOURCE_FIELDS})]
        data = transfer.decode(transfer.encode(transfer.document(profiles, s)))
        self.assertEqual(data['filters']['special_calls'], 'W1AW,TZ4AM')
        self.assertEqual(Settings().special_calls, '')
        with self.assertRaises(ValueError): Settings(special_calls_only=True).validate()
        with self.assertRaises(ValueError): Settings(special_calls='W1AW,w1aw').validate()

    def test_authoritative_selection_ranges_do_not_rewrite_license_authorizations(self):
        from dxtalker.privileges import eligibility
        self.assertEqual(eligibility('3540', 'RTTY', 'General'), 'eligible')
        self.assertEqual(policy_eligibility('3540', 'RTTY', 'General'), 'outside')
        now = datetime.now(UTC)
        spot = make_spot('WB4IUY', '3540', 'KF4DBX', now, 'test', now, 'RTTY')
        self.assertEqual(rejection(spot, Settings(license_class='General')), 'Outside selected band table')
        self.assertTrue(matches(spot, Settings()))
