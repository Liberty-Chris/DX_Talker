"""Optional receive audio gate. Audio levels only; no recording or speech recognition."""
from array import array
import math
import sys
import threading
import time


class ChannelBusy(Exception):
    pass


class ReceiveMonitor:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.lock = threading.RLock()
        self.stream = None
        self.level = None
        self.last_frame = None
        self.quiet_since = None
        self.fault = False
        self.fault_code = None
        self.threshold = -40
        self.delay = 7

    @staticmethod
    def devices():
        import sounddevice as sd
        apis = sd.query_hostapis()
        return sorted({f"{apis[d['hostapi']]['name']} :: {d['name']}" for d in sd.query_devices() if d['max_input_channels'] > 0})

    def start(self, settings):
        import sounddevice as sd
        self.close()
        apis = sd.query_hostapis()
        matches = [(i, d) for i, d in enumerate(sd.query_devices()) if d['max_input_channels'] > 0
                   and f"{apis[d['hostapi']]['name']} :: {d['name']}" == settings.receive_device]
        if len(matches) != 1:
            raise ValueError('Receive input is missing or ambiguous. Refresh devices and choose a unique input.')
        with self.lock:
            self._started_at = self.clock()
            self.threshold, self.delay = settings.receive_threshold_db, settings.receive_quiet_seconds
            self.level, self.last_frame, self.quiet_since, self.fault = None, None, None, False
            self.fault_code = None
        index, device = matches[0]
        try:
            self.stream = sd.RawInputStream(device=index, samplerate=device['default_samplerate'], channels=1,
                                            dtype='int16', blocksize=1024, callback=self._callback)
            self.stream.start()
        except Exception:
            self.close()
            raise ValueError('Cannot open the receive input. Check its selection, Windows microphone permissions and other apps.') from None

    def _callback(self, data, frames, timing, status):
        # An input overflow means missed samples, not a dead device. Restart the
        # complete quiet interval; persistent/unrecognized status remains a fault.
        overflow=bool(getattr(status, 'input_overflow', False))
        other=bool(status) and (not overflow or any(bool(getattr(status,k,False)) for k in ('input_underflow','output_underflow','output_overflow','priming_output')))
        self.feed(bytes(data), fault=other, discontinuity=overflow)

    def feed(self, pcm, fault=False, discontinuity=False):
        """Deterministic detector core also used by tests with synthetic PCM."""
        samples = array('h')
        samples.frombytes(pcm[:len(pcm)//2*2])
        if sys.byteorder != 'little': samples.byteswap()
        level = 20 * math.log10(max(1, math.sqrt(sum(n*n for n in samples) / max(1, len(samples)))) / 32768)
        now = self.clock()
        with self.lock:
            self.level, self.last_frame = level, now
            self.fault = self.fault or fault or not samples or len(pcm)%2 != 0
            if self.fault and not self.fault_code:
                self.fault_code = 'callback_fault' if fault else 'invalid_samples'
            if discontinuity:
                self.quiet_since = None
            if not samples:
                self.level = None
            if level >= self.threshold:
                self.quiet_since = None
            elif self.quiet_since is None:
                self.quiet_since = now

    def snapshot(self, check_stream=True):
        with self.lock:
            if self.stream is None:
                return 'off', self.level, 0
            try:
                active = self.stream.active if check_stream else True
            except Exception:
                active = False
            if self.fault or not active or (self.last_frame is not None and self.clock()-self.last_frame > 1):
                self.fault_code = self.fault_code or ('device_inactive' if not active else 'stale_samples')
                return 'fault', self.level, 0
            if self.last_frame is None:
                # The test meter and RF gate share the same startup timeout.
                if self.clock()-self.started_at > 1:
                    self.fault_code = 'no_samples'
                    return 'fault', None, 0
                return 'starting', self.level, self.delay
            remaining = self.delay if self.quiet_since is None else max(0, self.delay-(self.clock()-self.quiet_since))
            return ('busy' if self.level >= self.threshold else 'waiting' if remaining else 'clear'), self.level, remaining

    def ready(self, check_stream=True):
        state, _, _ = self.snapshot(check_stream=check_stream)
        if state in ('off', 'fault'):
            raise ValueError('Receive audio monitoring failed. RF stopped. ' + self.fault_message())
        if state == 'starting' and self.clock()-self.started_at > 1:
            raise ValueError('Receive input delivered no audio. RF stopped. Check the input device before enabling RF again.')
        return state == 'clear'

    def fault_message(self):
        return {
            'device_inactive': 'The selected input stopped. Check the device connection and Windows microphone permissions.',
            'no_samples': 'The input delivered no audio samples. Check the selected input and Windows microphone permissions.',
            'stale_samples': 'Fresh input samples stopped arriving. Check the input device and other audio apps.',
            'callback_fault': 'The input driver reported an audio fault. Stop the test and reopen the selected input.',
            'invalid_samples': 'The input returned invalid or empty samples. Stop the test and check the device.'
        }.get(self.fault_code, 'Check the input device before enabling RF again.')

    @property
    def started_at(self):
        return self._started_at

    def close(self):
        with self.lock:
            stream, self.stream = self.stream, None
        if stream is not None:
            try: stream.abort()
            finally: stream.close()


class ReceiveCancel:
    """Cancellation facade checks the input between output callbacks and lead/tail waits."""
    def __init__(self, cancel, monitor):
        self.cancel, self.monitor = cancel, monitor
        self.interrupted = False
        self.fault = None

    def is_set(self):
        if self.cancel.is_set(): return True
        try:
            if not self.monitor.ready(check_stream=False): self.interrupted = True
        except ValueError as exc:
            self.fault = exc
            self.interrupted = True
        return self.interrupted

    def wait(self, seconds):
        end = time.monotonic()+seconds
        while not self.is_set():
            remaining = end-time.monotonic()
            if remaining <= 0: return False
            self.cancel.wait(min(.02, remaining))
        return True
