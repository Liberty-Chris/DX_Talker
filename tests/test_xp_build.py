"""Build transformations preserve values and evaluation order before XP staging."""
import ast
import hashlib
import io
import tempfile
from pathlib import Path
from urllib.error import URLError
import sys
import types
import unittest
from unittest.mock import patch
from platforms.xp.build_app import transform
from platforms.xp.support import runtime

class XPBuildTests(unittest.TestCase):
    def execute(self, source, filename='<fixture>'):
        package = types.ModuleType('xp_support')
        package.__path__ = []
        with patch.dict(sys.modules, {'xp_support': package, 'xp_support.runtime': runtime}):
            namespace = {}
            generated = transform(source, filename)
            ast.parse(generated, feature_version=(3, 4))
            exec(compile(generated, filename, 'exec'), namespace)
        return namespace

    def test_order_unpacking_formatting_and_duplicate_keywords(self):
        result = self.execute('''
events = []
def mark(value):
    events.append(value)
    return value
first = {'one': mark(1), 'two': mark(2)}
combined = {**first, 'three': mark(3), 'one': mark(4)}
sequence = [mark(5), *[6, 7], mark(8)]
formatted = f"{3.125:.2f} {sequence!r}"
def collect(**values): return values
keywords = collect(one=1, **{'two': 2}, three=3)
try:
    collect(one=1, **{'one': 2})
except TypeError:
    rejected = True
''')
        self.assertEqual(list(result['combined']), ['one', 'two', 'three'])
        self.assertEqual(list(result['combined'].values()), [4, 2, 3])
        self.assertEqual(result['events'], [1, 2, 3, 4, 5, 8])
        self.assertEqual(result['formatted'], '3.12 [5, 6, 7, 8]')
        self.assertEqual(result['keywords'], {'one': 1, 'two': 2, 'three': 3})
        self.assertTrue(result['rejected'])

    def test_platform_rewrites_are_scoped_to_the_application_module(self):
        source = 'def update_ssl_context():\n return 42\n'
        self.assertEqual(self.execute(source)['update_ssl_context'](), 42)
        generated = transform(source, '/repo/dxtalker/updates.py')
        self.assertIn('return ssl.create_default_context()', generated)
        source = 'request.build_opener(NoRedirect())'
        self.assertNotIn('HTTPSHandler', transform(source, '/repo/other.py'))
        self.assertIn('HTTPSHandler(context=ssl.create_default_context())', transform(source, '/repo/dxtalker/source.py'))
        source = 'api.OpenProcess(4096, False, 3)'
        self.assertIn('4096', transform(source, '/repo/other.py'))
        self.assertIn('1024', transform(source, '/repo/dxtalker/diagnostics.py'))

    def test_unsupported_parameter_syntax_stops_the_build(self):
        with self.assertRaisesRegex(ValueError, 'explicit XP adapter'):
            transform('def future(value, /): return value')

    def test_dependency_timeout_retries_but_never_bypasses_pinned_hash(self):
        from platforms.xp import prepare
        content = b'synthetic runtime'
        with tempfile.TemporaryDirectory() as folder, patch.dict(prepare.DOWNLOADS, {'fixture': {'url': 'https://example.org/runtime.exe', 'sha256': hashlib.sha256(content).hexdigest()}}):
            with patch.object(prepare.urllib.request, 'urlopen', side_effect=[URLError(TimeoutError()), io.BytesIO(content)]) as opened, patch.object(prepare.time, 'sleep'):
                result = prepare.fetch('fixture', Path(folder))
                self.assertEqual(opened.call_count, 2)
                self.assertEqual(result.read_bytes(), content)
            result.unlink()
            with patch.object(prepare.urllib.request, 'urlopen', return_value=io.BytesIO(b'corrupt')) as opened:
                with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                    prepare.fetch('fixture', Path(folder))
                self.assertEqual(opened.call_count, 1)
                self.assertFalse(result.exists())
                self.assertFalse(list(Path(folder).glob('*.partial')))

    def test_dependency_certificate_failure_is_not_retried(self):
        from platforms.xp import prepare
        with tempfile.TemporaryDirectory() as folder, patch.dict(prepare.DOWNLOADS, {'fixture': {'url': 'https://example.org/runtime.exe', 'sha256': '0'*64}}):
            failure = URLError(prepare.ssl.SSLCertVerificationError('synthetic certificate failure'))
            with patch.object(prepare.urllib.request, 'urlopen', side_effect=failure) as opened, patch.object(prepare.time, 'sleep') as sleep:
                with self.assertRaises(URLError): prepare.fetch('fixture', Path(folder))
                self.assertEqual(opened.call_count, 1)
                sleep.assert_not_called()
