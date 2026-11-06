import base64
import hashlib
import json
from pathlib import Path
import unittest
import zlib
from dxtalker import transfer

class CollectionQrTests(unittest.TestCase):
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
