"""Local bounded diagnostics: code locations and fixed events, never exception values."""
from datetime import datetime, timezone
import json
from logging.handlers import RotatingFileHandler
import logging
from pathlib import Path
import sys
import threading
import time
import traceback
import uuid
import zipfile
import re
import faulthandler
import os

from . import __version__
from .models import settings_path

def process_alive(pid):
    if pid <= 0: return False
    if sys.platform == 'win32':
        # os.kill(pid, 0) terminates processes on Windows; never use it as a probe.
        import ctypes
        from ctypes import wintypes
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
        kernel.OpenProcess.restype=wintypes.HANDLE
        kernel.GetExitCodeProcess.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)]
        kernel.GetExitCodeProcess.restype=wintypes.BOOL
        kernel.CloseHandle.argtypes=[wintypes.HANDLE]
        handle=kernel.OpenProcess(0x1000,False,pid)
        if not handle:return ctypes.get_last_error()==5
        try:
            code=wintypes.DWORD()
            return not kernel.GetExitCodeProcess(handle,ctypes.byref(code)) or code.value==259
        finally:kernel.CloseHandle(handle)
    try:os.kill(pid,0);return True
    except PermissionError:return True
    except ProcessLookupError:return False

class Diagnostics:
    def __init__(self, directory=None, enabled=True, clock=time.monotonic):
        self.directory = Path(directory) if directory else settings_path().parent / 'diagnostics'
        self.enabled, self.clock = enabled, clock
        self.lock = threading.RLock()
        self.last_heartbeat = clock()
        self.hung = False
        self.closed = threading.Event()
        self.session = uuid.uuid4().hex
        self.handler = None
        self.marker = None
        self.native_file = None
        if enabled:
            self.directory.mkdir(parents=True, exist_ok=True)
            self.handler = RotatingFileHandler(self.directory / 'diagnostics.jsonl', maxBytes=1024*1024,
                                               backupCount=4, encoding='utf-8')
            # Markers provide evidence of incomplete shutdown, not a guessed cause.
            incomplete=0
            for old in self.directory.glob('session-*.pending'):
                try:
                    pid=int(old.read_text())
                    if not process_alive(pid):raise ProcessLookupError()
                except PermissionError:
                    continue
                except (OSError,ValueError):
                    incomplete+=1;old.unlink(missing_ok=True)
            self.record('startup', previous_incomplete=incomplete)
            self.marker = self.directory / ('session-' + self.session + '.pending')
            self.marker.write_text(str(os.getpid()))
            self.watcher = threading.Thread(target=self._watch, daemon=True, name='DX diagnostics watchdog')
            self.watcher.start()

    def record(self, event, **values):
        if not self.handler:
            return
        # Only caller-owned fixed codes, numbers and pre-sanitized stack frames enter here.
        line = json.dumps(dict(time=datetime.now(timezone.utc).isoformat(), version=__version__, session=self.session, event=event, **values))
        with self.lock:
            record = logging.LogRecord('diagnostics', logging.INFO, '', 0, line, (), None)
            try:
                if self.handler.shouldRollover(record): self.handler.doRollover()
                self.handler.stream.write(line + '\n')
                self.handler.flush()
            except OSError:
                self.enabled = False

    @staticmethod
    def frames(tb):
        return [dict(file=Path(f.filename).name, line=f.lineno, function=f.name) for f in traceback.extract_tb(tb)]

    def exception(self, kind, exc_type, tb):
        self.record(kind, error_type=exc_type.__name__, frames=self.frames(tb))

    def heartbeat(self):
        self.last_heartbeat = self.clock()
        if self.hung:
            self.record('ui_responsive_again')
            self.hung = False

    def sample_stall(self):
        delay = self.clock() - self.last_heartbeat
        if delay < 8 or self.hung:
            return
        self.hung = True
        stacks = []
        for frame in sys._current_frames().values():
            stacks.append([dict(file=Path(f.filename).name, line=f.lineno, function=f.name)
                           for f in traceback.extract_stack(frame)[-20:]])
        dialog=any(frame['file'] in ('commondialog.py','messagebox.py') for stack in stacks for frame in stack)
        self.record('ui_dialog_wait' if dialog else 'ui_stall', seconds=round(delay), threads=stacks)

    def _watch(self):
        from .power import DesktopPowerObserver
        power = DesktopPowerObserver(self.record, clock=self.clock)
        while not self.closed.wait(2):
            self.sample_stall()
            power.sample()

    def enable_native_faults(self):
        if not self.handler: return
        path=self.directory/'native-fault.log'
        if path.exists() and path.stat().st_size>512*1024:
            path.replace(self.directory/'native-fault.log.1')
        self.native_file=path.open('a')
        faulthandler.enable(file=self.native_file,all_threads=True)

    def export(self, destination):
        # Re-encode validated event records, never bundle settings, profiles or raw text.
        with self.lock, zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(self.directory.glob('diagnostics.jsonl*')):
                if path.is_file() and path.stat().st_size <= 2*1024*1024:
                    archive.writestr(path.name, path.read_bytes())
            for path in self.directory.glob('native-fault.log*'):
                if path.is_file() and path.stat().st_size<=2*1024*1024:
                    value=path.read_text(errors='replace')
                    value=re.sub(r'File "([^"\n]+)"',lambda match:'File "'+Path(match[1].replace('\\','/')).name+'"',value)
                    archive.writestr(path.name,value)
            archive.writestr('README.txt' , 'DX Talker local diagnostic events. No automatic upload.\n'
                             'Exception messages/locals, credentials, profiles and raw cluster data are excluded.\n'
                             'Incomplete shutdown can also mean a power failure or forced process termination.\n')

    def close(self, clean=True):
        self.closed.set()
        self.record('clean_shutdown' if clean else 'abnormal_shutdown')
        with self.lock:
            if self.native_file:
                faulthandler.disable(); self.native_file.close(); self.native_file=None
            if self.handler: self.handler.close(); self.handler = None
            if self.marker and clean: self.marker.unlink(missing_ok=True)
