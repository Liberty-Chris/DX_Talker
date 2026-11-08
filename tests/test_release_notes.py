from pathlib import Path
import importlib.util
import json
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock

spec = importlib.util.spec_from_file_location('release_notes', Path(__file__).parents[1] / 'scripts/sync_release_notes.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ReleaseNotesTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.path = self.root / 'docs/releases/v0.2.0a12.md'
        self.path.parent.mkdir(parents=True)
        self.path.write_text('DX Talker 0.2.0a12 adds filters.\n', encoding='utf-8')
        self.release = dict(tagName='v0.2.0a12', isDraft=False, body='DX Talker 0.2.0a11 old text')

    def invoke(self, release=None, code=0):
        run = Mock(side_effect=[SimpleNamespace(returncode=code, stdout=json.dumps(release or self.release)),
                                SimpleNamespace(returncode=0, stdout='')])
        result = module.sync_notes('v0.2.0a12', 'Liberty-Chris/DX_Talker', self.root, run)
        return result, run

    def test_correction_only_edits_release_prose(self):
        changed, run = self.invoke()
        self.assertTrue(changed)
        self.assertEqual(run.call_args_list[1].args[0], ['gh', 'release', 'edit', 'v0.2.0a12', '--repo',
                         'Liberty-Chris/DX_Talker', '--notes-file', str(self.path)])

    def test_matching_prose_does_not_edit(self):
        changed, run = self.invoke(dict(self.release, body=self.path.read_text()))
        self.assertFalse(changed)
        self.assertEqual(run.call_count, 1)

    def test_mismatched_archive_cannot_be_uploaded(self):
        self.path.write_text('DX Talker 0.2.0a11 wrong release')
        run = Mock()
        with self.assertRaisesRegex(ValueError, 'own release version'):
            module.sync_notes('v0.2.0a12', 'Liberty-Chris/DX_Talker', self.root, run)
        run.assert_not_called()

    def test_failed_lookup_draft_or_wrong_tag_stops(self):
        for code, patch in [(1, {}), (0, dict(isDraft=True)), (0, dict(tagName='v0.2.0a11'))]:
            with self.subTest(code=code, patch=patch), self.assertRaises(ValueError):
                self.invoke(dict(self.release, **patch), code)
