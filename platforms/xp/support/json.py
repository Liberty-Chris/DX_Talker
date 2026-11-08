from json import *
import json as _native
from collections import OrderedDict
JSONDecodeError = getattr(_native, 'JSONDecodeError', ValueError)
def loads(value, *args, **kwargs):
    if isinstance(value, (bytes, bytearray)): value = bytes(value).decode('utf-8-sig')
    if 'object_pairs_hook' not in kwargs and 'object_hook' not in kwargs: kwargs['object_pairs_hook'] = OrderedDict
    return _native.loads(value, *args, **kwargs)
