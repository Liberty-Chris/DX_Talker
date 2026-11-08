"""Syntax helpers preserve evaluation order and duplicate-keyword rejection."""

from collections import OrderedDict
ordered = OrderedDict

def merge(*pieces):
    result = OrderedDict()
    for piece in pieces:
        result.update(piece)
    return result


def unpack(*pieces):
    result = []
    for piece in pieces:
        result.extend(piece)
    return result


def keywords(*pieces):
    result = {}
    for piece in pieces:
        for key in piece:
            if not isinstance(key, str) or key in result:
                raise TypeError('Duplicate or invalid keyword argument')
            result[key] = piece[key]
    return result


def isascii(value):
    if not isinstance(value, (str, bytes, bytearray)): raise TypeError('Expected text or bytes')
    return all((ord(item) if isinstance(item, str) else item) < 128 for item in value)
