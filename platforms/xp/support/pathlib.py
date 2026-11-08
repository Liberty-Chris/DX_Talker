"""The application's path operations, with str paths accepted by Python 3.4 I/O."""
import glob
import os
from urllib.request import pathname2url

class Path(str):
    def __new__(cls, *parts):
        return str.__new__(cls, os.path.normpath(os.path.join(*(str(p) for p in parts))) if parts else '.')
    def __truediv__(self, other): return type(self)(self, other)
    def __rtruediv__(self, other): return type(self)(other, self)
    def __fspath__(self): return str(self)
    @property
    def name(self): return os.path.basename(self)
    @property
    def parent(self): return type(self)(os.path.dirname(self) or '.')
    @property
    def parents(self):
        result = []; current = self
        while current.parent != current:
            current = current.parent; result.append(current)
        return tuple(result)
    @property
    def suffix(self): return os.path.splitext(self.name)[1]
    @property
    def stem(self): return os.path.splitext(self.name)[0]
    @property
    def parts(self):
        drive, tail = os.path.splitdrive(self)
        pieces = [v for v in tail.split(os.sep) if v]
        if tail.startswith(os.sep): pieces.insert(0, drive + os.sep)
        elif drive: pieces.insert(0, drive)
        return tuple(pieces)
    def with_name(self, name):
        if not name or os.path.basename(name) != name: raise ValueError('Invalid filename')
        return self.parent / name
    def with_suffix(self, suffix):
        if suffix and (not suffix.startswith('.') or os.sep in suffix): raise ValueError('Invalid suffix')
        return self.with_name(self.stem + suffix)
    def exists(self): return os.path.exists(self)
    def is_file(self): return os.path.isfile(self)
    def is_dir(self): return os.path.isdir(self)
    def is_symlink(self): return os.path.islink(self)
    def is_absolute(self): return os.path.isabs(self)
    def absolute(self): return type(self)(os.path.abspath(self))
    def resolve(self, strict=False):
        if strict and not self.exists(): raise FileNotFoundError(str(self))
        return type(self)(os.path.realpath(self))
    def relative_to(self, other):
        base = type(self)(other).absolute()
        target = self.absolute()
        relative = os.path.relpath(target, base)
        if relative == '..' or relative.startswith('..' + os.sep): raise ValueError('Path is outside the directory')
        return type(self)(relative)
    def as_uri(self):
        if not self.is_absolute(): raise ValueError('URI requires an absolute path')
        return 'file:' + pathname2url(self)
    def stat(self): return os.stat(self)
    def open(self, mode='r', buffering=-1, encoding=None, errors=None, newline=None):
        return open(self, mode, buffering, encoding=encoding, errors=errors, newline=newline)
    def read_text(self, encoding=None, errors=None):
        with self.open(encoding=encoding, errors=errors) as stream: return stream.read()
    def write_text(self, text, encoding=None, errors=None):
        with self.open('w', encoding=encoding, errors=errors) as stream: return stream.write(text)
    def read_bytes(self):
        with open(self, 'rb') as stream: return stream.read()
    def write_bytes(self, data):
        with open(self, 'wb') as stream: return stream.write(data)
    def mkdir(self, mode=0o777, parents=False, exist_ok=False):
        if parents: return os.makedirs(self, mode=mode, exist_ok=exist_ok)
        try: os.mkdir(self, mode)
        except FileExistsError:
            if not exist_ok or not self.is_dir(): raise
    def unlink(self, missing_ok=False):
        try: os.unlink(self)
        except FileNotFoundError:
            if not missing_ok: raise
    def replace(self, other): os.replace(self, str(other)); return type(self)(other)
    def rename(self, other): os.rename(self, str(other)); return type(self)(other)
    def iterdir(self): return (self / name for name in os.listdir(self))
    def glob(self, pattern): return (type(self)(name) for name in glob.glob(os.path.join(glob.escape(str(self)),pattern)))
    @classmethod
    def home(cls): return cls(os.path.expanduser('~'))
    @classmethod
    def cwd(cls): return cls(os.getcwd())
