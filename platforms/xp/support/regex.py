"""Expose group indexing without changing the shared parsers."""
from re import *
import re as _native

class Match:
    def __init__(self, value): self._value = value
    def __getattr__(self, name): return getattr(self._value, name)
    def __getitem__(self, key): return self._value.group(key)

class Pattern:
    def __init__(self, value): self._value = value
    def __getattr__(self, name): return getattr(self._value, name)
    def match(self, *args): return _wrap(self._value.match(*args))
    def search(self, *args): return _wrap(self._value.search(*args))
    def fullmatch(self, *args): return _wrap(self._value.fullmatch(*args))
    def finditer(self, *args): return (Match(item) for item in self._value.finditer(*args))
    def sub(self, replacement, *args): return self._value.sub(_replacement(replacement), *args)
    def subn(self, replacement, *args): return self._value.subn(_replacement(replacement), *args)

def _wrap(value): return Match(value) if value is not None else None
def _replacement(value): return (lambda match: value(Match(match))) if callable(value) else value
def compile(pattern, flags=0): return pattern if isinstance(pattern, Pattern) else Pattern(_native.compile(pattern, flags))
def match(pattern, string, flags=0): return compile(pattern, flags).match(string)
def search(pattern, string, flags=0): return compile(pattern, flags).search(string)
def fullmatch(pattern, string, flags=0): return compile(pattern, flags).fullmatch(string)
def finditer(pattern, string, flags=0): return compile(pattern, flags).finditer(string)
def sub(pattern, replacement, string, count=0, flags=0): return compile(pattern, flags).sub(replacement, string, count)
def subn(pattern, replacement, string, count=0, flags=0): return compile(pattern, flags).subn(replacement, string, count)
