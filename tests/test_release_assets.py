from pathlib import Path
import importlib.util
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('release_assets', ROOT/'scripts/release_assets.py')
assets = importlib.util.module_from_spec(spec); spec.loader.exec_module(assets)
sys.modules['release_assets'] = assets
spec = importlib.util.spec_from_file_location('label_release_assets', ROOT/'scripts/label_release_assets.py')
labels = importlib.util.module_from_spec(spec); spec.loader.exec_module(labels)

class ReleaseAssetTests(unittest.TestCase):
    def release(self):
        name = 'DXTalker-Setup-Windows-x86.exe'
        return dict(id=1, tag_name='v0.2.0a15', draft=False, body='Manually written release notes.\n',
                    assets=[dict(id=2, name=name, label=None, browser_download_url='https://github.com/Liberty-Chris/DX_Talker/releases/download/v0.2.0a15/'+name)])

    def test_labels_distinguish_installer_portable_xp_and_source(self):
        self.assertIn('Not for XP', assets.label('DXTalker-Setup-Windows-x86.exe'))
        self.assertIn('64 bit application installer', assets.label('DXTalker-Setup-Windows-XP-64bit.exe'))
        self.assertIn('portable ZIP', assets.label('DXTalker-Windows-x64.zip'))
        self.assertIn('Not an installer or full application', assets.label('DXTalker-XP-source-test-kit.zip'))
        self.assertIn('Android phones and tablets', assets.label('DXTalker-Android.apk'))
        self.assertIn('manual installation', assets.label('DXTalker-Android.apk'))
        self.assertIsNone(assets.label('unknown.exe'))

    def test_reconciliation_only_changes_labels_and_managed_body(self):
        release = self.release(); call = Mock()
        changes = labels.reconcile(release, True, call)
        self.assertEqual(len(changes), 2)
        calls = call.call_args_list
        self.assertEqual(calls[0].args[0:2], ('PATCH', '/releases/assets/2'))
        self.assertEqual(set(calls[0].args[2]), {'label'})
        self.assertEqual(set(calls[1].args[2]), {'body'})
        body = calls[1].args[2]['body']
        self.assertTrue(body.startswith(release['body']))
        self.assertIn(release['assets'][0]['browser_download_url'], body)
        updated = dict(release, body=body, assets=[dict(release['assets'][0], label=changes[0]['label'])])
        again = Mock(); self.assertEqual(labels.reconcile(updated, True, again), [])
        again.assert_not_called()
        dry = Mock(); labels.reconcile(release, False, dry); dry.assert_not_called()

    def test_invalid_links_and_incomplete_markers_do_not_mutate(self):
        release = self.release(); call = Mock()
        release['assets'][0]['browser_download_url'] = 'https://example.org/installer.exe'
        with self.assertRaises(ValueError): labels.reconcile(release, True, call)
        call.assert_not_called()
        release = self.release(); release['body'] += assets.START
        with self.assertRaises(ValueError): labels.reconcile(release, True, call)
        call.assert_not_called()

    def test_publication_keeps_exact_updater_filenames(self):
        with tempfile.TemporaryDirectory() as folder:
            name = 'DXTalker-Setup-Windows-x86.exe'
            (Path(folder)/name).write_text('synthetic')
            args = assets.arguments(folder)
            self.assertEqual(args[0].split('#')[0], str(Path(folder)/name))
            self.assertIn('32 bit installer', args[0])
            (Path(folder)/'mystery.zip').write_text('synthetic')
            with self.assertRaises(ValueError): assets.arguments(folder)

    def test_publication_notes_include_only_prepared_downloads(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)/'release'; directory.mkdir()
            name = 'DXTalker-Setup-Windows-XP-32bit.exe'
            (directory/name).write_text('synthetic')
            (directory/'DXTalker-Android.apk').write_bytes(b'synthetic APK')
            notes = Path(folder)/'notes.md'; notes.write_text('Original release prose.\n')
            output = Path(folder)/'prepared.md'
            command = [sys.executable, str(ROOT/'scripts/release_assets.py'), str(directory), '--notes', str(notes), '--tag', 'v0.2.0a17', '--output', str(output)]
            subprocess.run(command, check=True, capture_output=True)
            prepared = output.read_text()
            self.assertTrue(prepared.startswith('Original release prose.\n'))
            self.assertIn('/v0.2.0a17/'+name, prepared)
            self.assertNotIn('source-test-kit', prepared)
            self.assertIn('/v0.2.0a17/DXTalker-Android.apk', prepared)
            self.assertIn('Android phones and tablets', prepared)
            (directory/'unlabelled.exe').write_text('synthetic')
            failed = subprocess.run(command, capture_output=True)
            self.assertNotEqual(failed.returncode, 0)
            self.assertEqual(output.read_text(), prepared)
