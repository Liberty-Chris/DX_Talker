"""Run shared behavioral fixtures with the bundled interpreter. No public/RF I/O."""
import os
import sys
import unittest
import unittest.mock as mock
import xp_support.bootstrap

# Compatibility for test assertions, not changes to application behavior.
if not isinstance(getattr(mock._Call, 'args', None), property):
    mock._Call.args = property(lambda call: call[0] if len(call) == 2 else call[1])
    mock._Call.kwargs = property(lambda call: call[1] if len(call) == 2 else call[2])
for name, count in (('assert_not_called', 0), ('assert_called_once', 1)):
    if not hasattr(mock.Mock, name):
        def check(self, expected=count):
            if self.call_count != expected: raise AssertionError('Unexpected mock call count')
        setattr(mock.Mock, name, check)
if not hasattr(mock.Mock, 'assert_called'):
    def called(self):
        if not self.call_count: raise AssertionError('Mock was not called')
    mock.Mock.assert_called = called


def run(root):
    os.chdir(root)
    sys.path.insert(0, root)
    sys.path.insert(0, os.path.join(root, 'tests'))
    os.environ['PYTHONPATH'] = root
    names = ['test_models', 'test_protocol', 'test_spot_filters', 'test_engine',
             'test_source', 'test_profiles_history', 'test_diagnostics_transfer_packs',
             'test_collection_qr', 'test_appearance', 'test_app', 'test_receiver', 'test_xp_native']
    suite = unittest.defaultTestLoader.loadTestsFromNames(names)
    return unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful()


if __name__ == '__main__':
    raise SystemExit(0 if run(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) else 1)
