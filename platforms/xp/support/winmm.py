"""Selected WinMM PCM devices for XP. Output is owned by the shared coordinator.

No default-device substitution, global mixer changes or hardware PTT calls.
Native buffers survive until reset/unprepare/close have completed successfully.
"""
from array import array
import ctypes as C
import threading
import time

DWORD = C.c_uint32
WORD = C.c_uint16
HANDLE = C.c_void_p
UINT_PTR = C.c_size_t
_quarantined = []

class Format(C.Structure):
    _pack_ = 1
    _fields_ = [('tag', WORD), ('channels', WORD), ('rate', DWORD), ('average', DWORD),
                ('alignment', WORD), ('bits', WORD), ('extra', WORD)]

class Header(C.Structure):
    _fields_ = [('data', C.c_void_p), ('length', DWORD), ('recorded', DWORD),
                ('user', UINT_PTR), ('flags', DWORD), ('loops', DWORD),
                ('next', C.c_void_p), ('reserved', UINT_PTR)]

class OutCaps(C.Structure):
    _fields_ = [('manufacturer', WORD), ('product', WORD), ('version', DWORD),
                ('name', WORD * 32), ('formats', DWORD), ('channels', WORD),
                ('reserved', WORD), ('support', DWORD)]

class InCaps(C.Structure):
    _fields_ = OutCaps._fields_[:-1]


def api():
    library = C.WinDLL('winmm')
    for prefix, caps in (('waveOut', OutCaps), ('waveIn', InCaps)):
        fn = getattr(library, prefix + 'GetNumDevs'); fn.argtypes = []; fn.restype = DWORD
        fn = getattr(library, prefix + 'GetDevCapsW'); fn.argtypes = [UINT_PTR, C.POINTER(caps), DWORD]; fn.restype = DWORD
        fn = getattr(library, prefix + 'Open'); fn.argtypes = [C.POINTER(HANDLE), DWORD, C.POINTER(Format), UINT_PTR, UINT_PTR, DWORD]; fn.restype = DWORD
        for suffix in ('PrepareHeader', 'UnprepareHeader'):
            fn = getattr(library, prefix + suffix); fn.argtypes = [HANDLE, C.POINTER(Header), DWORD]; fn.restype = DWORD
        for suffix in ('Reset', 'Close'):
            fn = getattr(library, prefix + suffix); fn.argtypes = [HANDLE]; fn.restype = DWORD
    library.waveOutWrite.argtypes = [HANDLE, C.POINTER(Header), DWORD]; library.waveOutWrite.restype = DWORD
    library.waveInAddBuffer.argtypes = [HANDLE, C.POINTER(Header), DWORD]; library.waveInAddBuffer.restype = DWORD
    library.waveInStart.argtypes = [HANDLE]; library.waveInStart.restype = DWORD
    return library


def _check(result, message):
    if result: raise ValueError(message)


def _available():
    if _quarantined: raise ValueError('Audio driver cleanup failed. Restart DX Talker before opening audio again.')


def _name(caps):
    return C.string_at(C.addressof(caps) + type(caps).name.offset, 64).decode('utf-16-le').split('\0', 1)[0]


def query_hostapis(): return [{'name': 'Windows MME'}]


def query_devices(backend=None):
    backend = backend or api()
    devices = []
    for prefix, caps_type, direction in (('waveOut', OutCaps, 'output'), ('waveIn', InCaps, 'input')):
        for index in range(int(getattr(backend, prefix + 'GetNumDevs')())):
            caps = caps_type()
            _check(getattr(backend, prefix + 'GetDevCapsW')(index, C.byref(caps), C.sizeof(caps)), 'Cannot inspect the selected audio devices. Refresh devices.')
            rate = 22050 if caps.formats & 0x40 else 44100 if caps.formats & 0x400 else 11025
            devices.append(dict(name=_name(caps), hostapi=0, native_id=index, direction=direction,
                                max_output_channels=int(caps.channels) if direction == 'output' else 0,
                                max_input_channels=int(caps.channels) if direction == 'input' else 0,
                                default_samplerate=rate))
    return devices


def _format(rate, channels):
    if rate != int(rate) or not 8000 <= rate <= 96000 or channels not in (1, 2):
        raise ValueError('Audio requires PCM16 mono or stereo at a supported sample rate')
    return Format(1, channels, int(rate), int(rate) * channels * 2, channels * 2, 16, 0)


class AudioOutput:
    @staticmethod
    def devices():
        return sorted({'Windows MME :: ' + item['name'] for item in query_devices() if item['max_output_channels'] > 0})

    @staticmethod
    def resolve(key, channels, backend=None):
        matches = [index for index, item in enumerate(query_devices(backend))
                   if item['max_output_channels'] >= channels and 'Windows MME :: ' + item['name'] == key]
        if len(matches) != 1: raise ValueError('Audio device is missing or ambiguous. Refresh devices and select a uniquely named output.')
        return matches[0]

    def __init__(self, backend=None): self.backend = backend

    def play(self, clip, device, volume, cancel, deadline):
        from dxtalker.audio import Cancelled, AudioPlaybackError
        _available()
        if cancel.is_set(): raise Cancelled()
        if time.monotonic() > deadline: raise TimeoutError('Maximum playback duration reached')
        if clip.channels not in (1, 2) or not 0 <= volume <= 100 or not clip.pcm or len(clip.pcm) % (clip.channels * 2):
            raise ValueError('Audio data or volume is invalid')
        backend = self.backend or api()
        matches = [item for item in query_devices(backend) if item['max_output_channels'] >= clip.channels and 'Windows MME :: ' + item['name'] == device]
        if len(matches) != 1: raise ValueError('Audio device is missing or ambiguous. Refresh devices and select it again.')
        selected = matches[0]
        fmt = _format(clip.rate, clip.channels)
        samples = array('h'); samples.frombytes(clip.pcm)
        import sys
        if sys.byteorder != 'little': samples.byteswap()
        if volume != 100:
            for index in range(len(samples)):
                if index % 4096 == 0:
                    if cancel.is_set(): raise Cancelled()
                    if time.monotonic() > deadline: raise TimeoutError('Maximum playback duration reached')
                samples[index] = round(samples[index] * volume / 100)
        if sys.byteorder != 'little': samples.byteswap()
        buffer = (C.c_char * (len(samples) * 2)).from_buffer(samples)
        header = Header(data=C.cast(buffer, C.c_void_p), length=len(samples) * 2)
        handle = HANDLE(); opened = prepared = False
        try:
            _check(backend.waveOutOpen(C.byref(handle), selected['native_id'], C.byref(fmt), 0, 0, 0), 'Cannot open the selected audio output. Check its format and other applications.')
            opened = True
            caps = OutCaps()
            _check(backend.waveOutGetDevCapsW(handle.value, C.byref(caps), C.sizeof(caps)), 'Cannot confirm the opened audio device')
            if _name(caps) != selected['name']: raise ValueError('Audio device changed while opening. Refresh and select it again.')
            if cancel.is_set(): raise Cancelled()
            _check(backend.waveOutPrepareHeader(handle, C.byref(header), C.sizeof(header)), 'Cannot prepare audio output')
            prepared = True
            _check(backend.waveOutWrite(handle, C.byref(header), C.sizeof(header)), 'The selected audio output rejected playback')
            while not header.flags & 1:
                if cancel.is_set(): raise Cancelled()
                if time.monotonic() > deadline: raise TimeoutError('Maximum playback duration reached')
                time.sleep(0.01)
            if cancel.is_set(): raise Cancelled()
            if time.monotonic() > deadline: raise TimeoutError('Maximum playback duration reached')
        finally:
            errors = []
            if opened:
                if backend.waveOutReset(handle): errors.append('reset')
                if prepared and backend.waveOutUnprepareHeader(handle, C.byref(header), C.sizeof(header)): errors.append('unprepare')
                if backend.waveOutClose(handle): errors.append('close')
            if errors:
                _quarantined.append((backend, handle, header, buffer, samples))
                raise ValueError('Audio driver cleanup failed. Output stopped. Restart DX Talker before opening audio again.')


class InputStatus:
    def __init__(self, overflow=False, fault=False):
        self.input_overflow, self.input_underflow = overflow, fault
    def __bool__(self): return self.input_overflow or self.input_underflow


class RawInputStream:
    def __init__(self, device, samplerate, channels, dtype, blocksize, callback, backend=None):
        if channels != 1 or dtype != 'int16' or not 128 <= blocksize <= 8192: raise ValueError('Invalid receive audio format')
        self.backend = backend or api()
        devices = query_devices(self.backend)
        if isinstance(device, dict):
            matches = [item for item in devices if item['max_input_channels'] > 0 and item['name'] == device.get('name') and device.get('direction') == 'input']
            if len(matches) != 1: raise ValueError('The selected receive input is missing or ambiguous')
            selected = matches[0]
        else:
            if not isinstance(device, int) or not 0 <= device < len(devices) or not devices[device]['max_input_channels']:
                raise ValueError('The selected receive input is unavailable')
            selected = devices[device]
        self.device, self.fmt = selected, _format(samplerate, channels)
        self.blocksize, self.callback = blocksize, callback
        self.handle = HANDLE(); self.headers = []; self.buffers = []
        self.active = False; self.opened = False
        self.stop = threading.Event(); self.thread = None

    def start(self):
        _available()
        if self.opened: raise ValueError('Receive input is already open')
        try:
            _check(self.backend.waveInOpen(C.byref(self.handle), self.device['native_id'], C.byref(self.fmt), 0, 0, 0), 'Cannot open the selected receive input')
            self.opened = True
            caps = InCaps()
            _check(self.backend.waveInGetDevCapsW(self.handle.value, C.byref(caps), C.sizeof(caps)), 'Cannot confirm the receive input')
            if _name(caps) != self.device['name']: raise ValueError('Receive device changed while opening. Refresh devices.')
            for unused in range(4):
                buffer = C.create_string_buffer(self.blocksize * 2)
                header = Header(data=C.cast(buffer, C.c_void_p), length=self.blocksize * 2)
                _check(self.backend.waveInPrepareHeader(self.handle, C.byref(header), C.sizeof(header)), 'Cannot prepare receive input')
                self.buffers.append(buffer); self.headers.append(header)
                _check(self.backend.waveInAddBuffer(self.handle, C.byref(header), C.sizeof(header)), 'Cannot queue receive input')
            _check(self.backend.waveInStart(self.handle), 'Cannot start receive input')
            self.stop.clear(); self.active = True
            self.thread = threading.Thread(target=self._read, daemon=True, name='XP receive audio')
            self.thread.start()
            return self
        except BaseException:
            self.close(); raise

    def _read(self):
        last = time.monotonic()
        try:
            while not self.stop.wait(0.01):
                for header in self.headers:
                    if not header.flags & 1: continue
                    now = time.monotonic()
                    overflow = now - last > 4 * self.blocksize / self.fmt.rate + 0.1
                    last = now
                    length = int(header.recorded)
                    if length > header.length or length % 2: raise ValueError('Invalid receive buffer')
                    self.callback(C.string_at(header.data, length), length // 2, None, InputStatus(overflow))
                    if self.stop.is_set(): return
                    header.recorded = 0
                    _check(self.backend.waveInAddBuffer(self.handle, C.byref(header), C.sizeof(header)), 'Receive input queue failed')
        except Exception:
            try: self.callback(b'', 0, None, InputStatus(fault=True))
            except Exception: pass
        finally:
            self.active = False

    def abort(self):
        self.stop.set()
        if self.opened:
            _check(self.backend.waveInReset(self.handle), 'Cannot stop receive audio')
        if self.thread is not None and self.thread is not threading.current_thread():
            self.thread.join(2)
            if self.thread.is_alive(): raise TimeoutError('Receive audio is still stopping')
        self.active = False

    def close(self):
        if not self.opened: return
        errors = []
        try: self.abort()
        except Exception:
            # Keep native storage alive if the driver or callback has not returned.
            _quarantined.append(self)
            raise
        for header in self.headers:
            if self.backend.waveInUnprepareHeader(self.handle, C.byref(header), C.sizeof(header)): errors.append('unprepare')
        if self.backend.waveInClose(self.handle): errors.append('close')
        if errors:
            _quarantined.append(self)
            raise ValueError('Receive driver cleanup failed. Restart DX Talker before opening audio again.')
        self.opened = False; self.headers = []; self.buffers = []; self.handle = HANDLE()
