"""Install only runtime facilities absent from Python 3.4."""
import os
# Must precede imports which can load hashlib/OpenSSL. The launcher supplies
# the same process-only setting before the interpreter starts.
os.environ['OPENSSL_ia32cap'] = ':~0x20000000'
import builtins
import threading
from types import SimpleNamespace
import traceback

if not hasattr(builtins, 'ModuleNotFoundError'):
    builtins.ModuleNotFoundError = ImportError

if not hasattr(threading, 'excepthook'):
    def default_hook(args):
        if args.exc_type is not SystemExit:
            traceback.print_exception(args.exc_type, args.exc_value, args.exc_traceback)
    threading.excepthook = default_hook
    original_run = threading.Thread.run
    def monitored_run(self):
        try: original_run(self)
        except BaseException as error:
            threading.excepthook(SimpleNamespace(exc_type=type(error), exc_value=error,
                                                exc_traceback=error.__traceback__, thread=self))
    threading.Thread.run = monitored_run


import os
import sys
if sys.platform == 'win32' and not os.environ.get('LOCALAPPDATA'):
    import ctypes
    folder = ctypes.create_unicode_buffer(260)
    if ctypes.windll.shell32.SHGetFolderPathW(None, 28, None, 0, folder) != 0:
        raise OSError('Windows could not locate the local application data folder')
    os.environ['LOCALAPPDATA'] = folder.value

# Tcl 8.6 supports variable traces; Python 3.4 lacks the later wrapper name.
import tkinter
if not hasattr(tkinter.Variable, 'trace_add'):
    def trace_add(self, mode, callback):
        modes = (mode,) if isinstance(mode, str) else tuple(mode)
        names = {'read': 'r', 'write': 'w', 'unset': 'u'}
        short = ''.join(names[item] for item in modes)
        full = {'r': 'read', 'w': 'write', 'u': 'unset'}
        def changed(name, index, operation):
            return callback(name, index, full[operation])
        return self.trace_variable(short, changed)
    tkinter.Variable.trace_add = trace_add

import tkinter.ttk as ttk
if not hasattr(ttk, 'Spinbox'):
    class Spinbox(ttk.Entry):
        def __init__(self, master=None, **options):
            ttk.Entry.__init__(self, master, 'ttk::spinbox', **options)
        def set(self, value):
            self.tk.call(self._w, 'set', value)
    ttk.Spinbox = Spinbox
