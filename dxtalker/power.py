"""Thread scoped Windows idle requests and read only screensaver observation."""
import sys
import time

CONTINUOUS = 0x80000000
SYSTEM = 0x00000001
DISPLAY = 0x00000002


class WindowsPowerAPI:
    def __init__(self):
        import ctypes
        from ctypes import wintypes
        self.ctypes = ctypes
        self.execute = ctypes.windll.kernel32.SetThreadExecutionState
        self.execute.argtypes = [wintypes.DWORD]
        self.execute.restype = wintypes.DWORD
        self.parameters = ctypes.windll.user32.SystemParametersInfoW
        self.parameters.argtypes = [wintypes.UINT, wintypes.UINT, wintypes.LPVOID, wintypes.UINT]
        self.parameters.restype = wintypes.BOOL

    def request(self, flags):
        return bool(self.execute(flags))

    def screensaver(self):
        value = self.ctypes.c_int()
        if not self.parameters(0x0072, 0, self.ctypes.byref(value), 0):
            return None
        return bool(value.value)


class OutputPower:
    """All requests and release run on the same output worker thread."""
    def __init__(self, emit, api=None):
        self.emit = emit
        self.api = api
        self.mode = 'Off'
        self.attempted = None
        if api is None and sys.platform == 'win32':
            try: self.api = WindowsPowerAPI()
            except (AttributeError, OSError): pass

    def __enter__(self): return self

    def set_active(self, active, mode):
        desired = mode if active else 'Off'
        if not self.api or desired == self.attempted:
            return
        self.attempted = desired
        if desired == 'Off' and self.mode == 'Off':
            return
        flags = CONTINUOUS
        if desired != 'Off': flags |= SYSTEM
        if desired == 'Computer and display': flags |= DISPLAY
        try: success = self.api.request(flags)
        except (OSError, AttributeError): success = False
        self.emit('power_event', dict(code='idle_request' if success else 'idle_request_failed', mode=desired))
        if success:
            self.mode = desired
        else:
            self.emit('journal', 'Windows could not change the keep awake request. Check power settings before unattended use.')

    def __exit__(self, *args):
        # Even a failed mode change may leave the previous request active.
        self.attempted = None
        self.set_active(False, 'Off')


class DesktopPowerObserver:
    """Poll on the existing diagnostics watchdog, never on the audio callback."""
    def __init__(self, record, api=None, clock=time.monotonic):
        self.record, self.clock = record, clock
        self.api = api
        self.last = None
        self.previous = None
        if api is None and sys.platform == 'win32':
            try: self.api = WindowsPowerAPI()
            except (AttributeError, OSError): pass

    def sample(self):
        if not self.api: return
        now = self.clock()
        if self.last is not None and now - self.last > 10:
            self.record('desktop_power', code='observation_gap', seconds=round(now-self.last, 1))
        self.last = now
        try: active = self.api.screensaver()
        except (OSError, AttributeError): active = None
        if active is not None and active != self.previous:
            self.record('desktop_power', code='screensaver_state', active=active)
            self.previous = active
