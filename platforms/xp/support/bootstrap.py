"""Install only runtime facilities absent from Python 3.4."""
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
