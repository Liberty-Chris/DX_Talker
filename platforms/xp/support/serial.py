"""Exclusive Win32 serial line PTT. No CAT commands and no audio ownership."""
import ctypes as C
import re

DWORD = C.c_uint32
WORD = C.c_uint16
BYTE = C.c_ubyte
HANDLE = C.c_void_p

class DCB(C.Structure):
    _fields_ = [('DCBlength', DWORD), ('BaudRate', DWORD), ('flags', DWORD),
                ('wReserved', WORD), ('XonLim', WORD), ('XoffLim', WORD),
                ('ByteSize', BYTE), ('Parity', BYTE), ('StopBits', BYTE),
                ('XonChar', C.c_char), ('XoffChar', C.c_char), ('ErrorChar', C.c_char),
                ('EofChar', C.c_char), ('EvtChar', C.c_char), ('wReserved1', WORD)]


def api():
    kernel = C.WinDLL('kernel32', use_last_error=True)
    kernel.CreateFileW.argtypes = [C.c_wchar_p, DWORD, DWORD, C.c_void_p, DWORD, DWORD, HANDLE]
    kernel.CreateFileW.restype = HANDLE
    for name in ('GetCommState', 'SetCommState'):
        fn = getattr(kernel, name); fn.argtypes = [HANDLE, C.POINTER(DCB)]; fn.restype = C.c_int
    kernel.EscapeCommFunction.argtypes = [HANDLE, DWORD]; kernel.EscapeCommFunction.restype = C.c_int
    kernel.CloseHandle.argtypes = [HANDLE]; kernel.CloseHandle.restype = C.c_int
    return kernel


def serial_ports():
    import winreg
    ports = set()
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'HARDWARE\DEVICEMAP\SERIALCOMM') as key:
            index = 0
            while True:
                try: value = winreg.EnumValue(key, index)[1]
                except OSError: break
                if isinstance(value, str) and re.fullmatch(r'COM[1-9][0-9]{0,4}', value.upper()): ports.add(value.upper())
                index += 1
    except OSError: pass
    return sorted(ports, key=lambda port: int(port[3:]))


class SerialPTT:
    def __init__(self, port, method, active_high=True, backend=None):
        self.port, self.method, self.active_high = port, method, active_high
        self.backend, self.handle = backend, None

    def open(self):
        if not re.fullmatch(r'COM[1-9][0-9]{0,4}', self.port.upper()): raise ValueError('Choose a valid COM port')
        if self.method not in ('RTS', 'DTR', 'RTS+DTR'): raise ValueError('Choose a supported serial PTT method')
        if self.handle is not None: raise ValueError('PTT port is already open')
        self.backend = self.backend or api()
        handle = self.backend.CreateFileW('\\\\.\\' + self.port, 0xC0000000, 0, None, 3, 0, None)
        if handle in (None, C.c_void_p(-1).value): raise ValueError('Cannot open the selected PTT port. Check the cable and other applications.')
        self.handle = handle
        try:
            state = DCB(); state.DCBlength = C.sizeof(DCB)
            if not self.backend.GetCommState(handle, C.byref(state)): raise OSError('Cannot read the serial configuration')
            state.BaudRate, state.ByteSize, state.Parity, state.StopBits = 9600, 8, 0, 0
            # Clear hardware handshakes and apply the requested idle line
            # levels in the first DCB update. Drivers can still pulse
            # during initial open; physical interface acceptance remains needed.
            state.flags = 1
            if not self.active_high:
                if 'DTR' in self.method: state.flags |= 1 << 4
                if 'RTS' in self.method: state.flags |= 1 << 12
            if not self.backend.SetCommState(handle, C.byref(state)): raise OSError('Cannot configure the serial port')
            for line in ('RTS', 'DTR'):
                self._line(line, not self.active_high if line in self.method else False)
        except BaseException:
            self.close(); raise

    def _line(self, line, level):
        command = (3 if level else 4) if line == 'RTS' else (5 if level else 6)
        if not self.backend.EscapeCommFunction(self.handle, command): raise OSError('PTT line control failed')

    def set(self, keyed):
        if self.handle is None: raise ValueError('PTT port is not open')
        level = self.active_high if keyed else not self.active_high
        for line in ('RTS', 'DTR'):
            if line in self.method: self._line(line, level)

    def close(self):
        if self.handle is None: return
        failure = None
        try:
            for line in ('RTS', 'DTR'):
                if line in self.method:
                    try: self._line(line, not self.active_high)
                    except Exception as error: failure = error
        finally:
            handle, self.handle = self.handle, None
            if not self.backend.CloseHandle(handle): failure = OSError('PTT port close failed')
        if failure: raise failure
