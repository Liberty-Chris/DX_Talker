import base64
import hashlib
import json
from pathlib import Path
import unittest
import zlib
from dxtalker import transfer
from dxtalker.models import Settings

class CollectionQrTests(unittest.TestCase):
    def test_listening_qr_exports_active_filters_and_presets_without_cluster_data(self):
        settings = Settings(host='private.example', login='KF4DBX', special_keywords='US-',
                            special_calls='W1AW', filter_bands='20m',
                            listening_presets='{"CW":{"filter_modes":"CW","special_keywords":"US-"}}')
        data = transfer.listening_document(settings)
        pages = transfer.qr_sequence(data)
        self.assertEqual(len(pages), 1)
        self.assertEqual(transfer.decode(pages[0]), data)
        self.assertEqual(data['version'], 4)
        self.assertEqual(set(data), {'schema', 'version', 'filters'})
        raw = transfer.encode(data)
        self.assertNotIn(b'private.example', raw)
        self.assertNotIn(b'KF4DBX', raw)
        self.assertEqual(data['filters']['special_calls'], 'W1AW')
        self.assertEqual(data['filters']['filter_bands'], '20m')
        self.assertEqual(json.loads(data['filters']['listening_presets'])['CW']['special_keywords'], 'US-')
        with self.assertRaises(ValueError):
            transfer.validate(dict(data, profiles=[]))

    def test_desktop_fixture_contains_every_selected_profile_and_filters(self):
        fixture=json.loads((Path(__file__).resolve().parents[1]/'android/app/src/test/resources/desktop_collection.json').read_text())
        data,pages=fixture['data'],fixture['pages']
        self.assertEqual(transfer.qr_sequence(data),pages)
        parts={}
        for page in reversed(pages):
            self.assertLessEqual(len(page),1800)
            prefix,identity,index,total,encoded=page.split(':')
            self.assertEqual(prefix,'DXT2');self.assertEqual(int(total),len(pages))
            parts[int(index)]=base64.urlsafe_b64decode(encoded+'='*((-len(encoded))%4))
        compressed=b''.join(parts[i] for i in sorted(parts))
        self.assertEqual(hashlib.sha256(compressed).hexdigest(),identity)
        self.assertEqual(transfer.decode(zlib.decompress(compressed)),data)
        self.assertEqual(len(data['profiles']),55)
        small={**data,'profiles':data['profiles'][:2]}
        single=transfer.qr_sequence(small)
        self.assertEqual(len(single),1);self.assertEqual(transfer.decode(single[0]),small)

    def test_transfer_limit_is_checked_before_page_generation(self):
        fixture=json.loads((Path(__file__).resolve().parents[1]/'android/app/src/test/resources/desktop_collection.json').read_text())
        data=fixture['data'];data['profiles']*=100
        with self.assertRaisesRegex(ValueError,'64 KiB'):transfer.qr_sequence(data)
