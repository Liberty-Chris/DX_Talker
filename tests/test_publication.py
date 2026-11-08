from pathlib import Path
import importlib.util
import json
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock

spec=importlib.util.spec_from_file_location('publication',Path(__file__).parents[1]/'scripts/check_published_release.py')
publication=importlib.util.module_from_spec(spec);spec.loader.exec_module(publication)


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.path=Path(self.folder.name)
        for name in ('DXTalker-Setup-Windows-x64.exe','SHA256SUMS.txt'):(self.path/name).write_bytes(b'synthetic')
        self.release=dict(tag_name='v0.2.0a12',draft=False,assets=[dict(name=p.name,state='uploaded',size=9) for p in self.path.iterdir()])

    def run_check(self,code,data):
        run=Mock(return_value=SimpleNamespace(returncode=code,stdout=json.dumps(data)))
        result=publication.inspect_release('v0.2.0a12',self.path,'Liberty-Chris/DX_Talker',run)
        self.assertEqual(run.call_count,1)
        self.assertEqual(run.call_args.args[0][0:2],['gh','api'])
        return result

    def test_complete_release_is_read_only_success(self):
        self.assertEqual(self.run_check(0,self.release),'https://github.com/Liberty-Chris/DX_Talker/releases/tag/v0.2.0a12')

    def test_only_explicit_404_allows_creation(self):
        self.assertIsNone(self.run_check(1,dict(status='404',message='Not Found')))
        for data in (dict(status='403'),dict(status='503'),dict(message='Unknown')):
            with self.assertRaises(publication.PublicationError):self.run_check(1,data)

    def test_incomplete_or_empty_assets_stop_without_replacement(self):
        for assets in ([],[dict(name='SHA256SUMS.txt',state='uploaded',size=9)],[dict(name=a['name'],state='uploaded',size=0) for a in self.release['assets']]):
            with self.subTest(assets=assets),self.assertRaisesRegex(publication.PublicationError,'incomplete'):
                self.run_check(0,dict(self.release,assets=assets))

    def test_draft_or_different_tag_requires_review(self):
        for patch in (dict(draft=True),dict(tag_name='v0.2.0a11')):
            with self.assertRaises(publication.PublicationError):self.run_check(0,dict(self.release,**patch))

    def test_non_json_failure_is_not_treated_as_missing_release(self):
        with self.assertRaises(publication.PublicationError):
            publication.inspect_release('v0.2.0a12',self.path,'Liberty-Chris/DX_Talker',Mock(return_value=SimpleNamespace(returncode=1,stdout='')))
