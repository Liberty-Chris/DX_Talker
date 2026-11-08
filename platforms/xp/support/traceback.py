from traceback import *
import traceback as _native
from collections import namedtuple
FrameSummary = namedtuple('FrameSummary', 'filename lineno name line')
def extract_tb(tb, limit=None):
    return [FrameSummary(*frame) for frame in _native.extract_tb(tb, limit)]
def extract_stack(frame=None, limit=None):
    return [FrameSummary(*item) for item in _native.extract_stack(frame, limit)]
