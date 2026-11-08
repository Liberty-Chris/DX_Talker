"""Build transformations preserve values and evaluation order before XP staging."""
import ast
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
        source = 'api.OpenProcess(4096, False, 3)'
        self.assertIn('4096', transform(source, '/repo/other.py'))
        self.assertIn('1024', transform(source, '/repo/dxtalker/diagnostics.py'))

    def test_unsupported_parameter_syntax_stops_the_build(self):
        with self.assertRaisesRegex(ValueError, 'explicit XP adapter'):
            transform('def future(value, /): return value')
