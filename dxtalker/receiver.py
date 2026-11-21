"""Optional receive audio gate. Audio levels only; no recording or speech recognition."""
from array import array
from datetime import datetime, timezone
import math
import sys
import threading
import time

STALE_AFTER = 1.0
STOP_AFTER = 60.0
CAPTURE_APIS = frozenset(('Windows WASAPI', 'MME', 'Windows MME', 'Windows DirectSound',
                          'Windows WDM-KS', 'ALSA', 'OSS', 'JACK', 'Core Audio'))


class ChannelBusy(Exception):
    pass


class ReceiveMonitor:
    def __init__(self, clock=time.monotonic, emit=None):
        self.clock = clock
        self.emit = emit
        self.lock = threading.RLock()
        self.stream = None
        self.level = None
        self.last_frame = None
        self.quiet_since = None
        self.fault = False
        self.fault_code = None
        self.gap_pending = False
        self.gap_generation = 0
        self.recoveries = 0
        self.capture_details = {}
        self.threshold = -40
        self.delay = 5
        self.traffic_pending = False
        self.transmitting = False
        self.settle_until = 0

    def transmit_started(self):
        with self.lock:
            self.transmitting = True
            self.traffic_pending = False
            self.quiet_since = None

    def transmit_ended(self):
        with self.lock:
            self.transmitting = False
            self.settle_until = self.clock() + 1.0
            self.traffic_pending = False
            self.quiet_since = None

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
        index, device = matches[0]
        host = apis[device['hostapi']]['name']
        with self.lock:
            self._started_at = self.clock()
            self.threshold, self.delay = settings.receive_threshold_db, 5
            self.traffic_pending = False
            self.level, self.last_frame, self.quiet_since, self.fault = None, None, None, False
            self.fault_code = None
            self.capture_details = dict(host_api=host if host in CAPTURE_APIS else 'Other',
                                        sample_rate_hz=device['default_samplerate'], block_frames=1024)
        try:
            self.stream = sd.RawInputStream(device=index, samplerate=device['default_samplerate'], channels=1,
                                            dtype='int16', blocksize=1024, callback=self._callback)
            self.stream.start()
        except Exception:
            self.close()
            raise ValueError('Cannot open the receive input. Check its selection, Windows microphone permissions and other apps.') from None

    def _callback(self, data, frames, timing, status):
        # An input overflow means missed samples, not a dead device. Restart the
        # active traffic quiet interval; a gap alone does not invent traffic.
        # Persistent/unrecognized status remains a fault.
        overflow=bool(getattr(status, 'input_overflow', False))
        other=bool(status) and (not overflow or any(bool(getattr(status,k,False)) for k in ('input_underflow','output_underflow','output_overflow','priming_output')))
        self.feed(bytes(data), fault=other, discontinuity=overflow)

    def feed(self, pcm, fault=False, discontinuity=False):
        """Deterministic detector core also used by tests with synthetic PCM."""
        samples = array('h')
        samples.frombytes(pcm[:len(pcm)//2*2])
        if sys.byteorder != 'little': samples.byteswap()
        level = 20 * math.log10(max(1, math.sqrt(sum(n*n for n in samples) / max(1, len(samples)))) / 32768)
        with self.lock:
            now = self.clock()
            if self.stream is None or self.fault:
                return
            self._check_gap(now)
            if self.fault:
                return
            if fault or not samples or len(pcm) % 2:
                self._fail('callback_fault' if fault else 'invalid_samples', now)
                return
            if self.gap_pending:
                self.recoveries += 1
                self._gap_event('recovered', now, input_overflow=discontinuity)
                self.gap_pending = False
            if self.last_frame is None:
                self.fault_code = None
            self.level, self.last_frame = level, now
            if discontinuity:
                self.quiet_since = None
            # Blanked audio updates device health and the meter only. It must
            # not create a traffic hold or accumulate quiet credit.
            if self.transmitting or now < self.settle_until:
                return
            if level >= self.threshold:
                self.traffic_pending = True
                self.quiet_since = None
            elif self.traffic_pending:
                if self.quiet_since is None:
                    self.quiet_since = now
                elif now - self.quiet_since >= self.delay:
                    self.traffic_pending = False

    def _gap_event(self, code, now, **details):
        if self.emit is not None:
            self.emit('receive_gap', dict(
                code=code, gap_id=self.gap_generation, recovery_count=self.recoveries,
                gap_ms=round((now - self.last_frame) * 1000),
                observed_at_utc=datetime.now(timezone.utc).isoformat(),
                receive_blanked=self.transmitting or now < self.settle_until,
                traffic_hold_active=self.traffic_pending, **self.capture_details, **details))

    def _fail(self, code, now):
        self.fault = True
        self.fault_code = code
        if self.gap_pending:
            self._gap_event('failed', now, receive_code=code)
            self.gap_pending = False

    def _check_gap(self, now, stream_active=None):
        if self.last_frame is None or now - self.last_frame <= STALE_AFTER:
            return
        if not self.gap_pending:
            self.gap_pending = True
            self.gap_generation += 1
            self.quiet_since = None
            self._gap_event('started', now, stream_active=stream_active)
        if now - self.last_frame >= STOP_AFTER:
            self._fail('stale_samples', now)

    def snapshot(self, check_stream=True):
        with self.lock:
            if self.stream is None:
                return 'off', self.level, 0
            try:
                active = self.stream.active if check_stream else True
            except Exception:
                active = False
            now = self.clock()
            if not self.fault:
                if not active:
                    self._fail('device_inactive', now)
                else:
                    self._check_gap(now, stream_active=True if check_stream else None)
            if self.fault:
                return 'fault', self.level, 0
            if self.gap_pending:
                return 'recovering', None, 0
            if self.last_frame is None:
                # The test meter and RF gate share the same startup timeout.
                if now - self.started_at > STALE_AFTER:
                    self.fault_code = 'no_samples'
                    return 'fault', None, 0
                return 'starting', self.level, self.delay
            if self.transmitting:
                return 'transmitting', self.level, self.delay
            if now < self.settle_until or self.last_frame < self.settle_until:
                return 'settling', self.level, 0
            if not self.traffic_pending:
                return 'clear', self.level, 0
            remaining = self.delay if self.quiet_since is None else max(0, self.delay-(now-self.quiet_since))
            return ('busy' if self.level >= self.threshold else 'waiting' if remaining else 'clear'), self.level, remaining

    def ready(self, check_stream=True):
        state, _, _ = self.snapshot(check_stream=check_stream)
        if state in ('off', 'fault'):
            raise ValueError('Receive audio monitoring failed. RF stopped. ' + self.fault_message())
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
            if self.gap_pending:
                self._gap_event('closed', self.clock())
                self.gap_pending = False
            self.transmitting = False
            self.settle_until = 0
            self.traffic_pending = False
            self.quiet_since = None
        if stream is not None:
            try: stream.abort()
            finally: stream.close()


class ReceiveCancel:
    """Cancellation facade checks the input between output callbacks and lead/tail waits."""
    def __init__(self, cancel, monitor):
        self.cancel, self.monitor = cancel, monitor
        self.interrupted = False
        self.fault = None
        self.ignore_busy = False
        self.gap_generation = getattr(monitor, 'gap_generation', 0)

    def is_set(self):
        if self.cancel.is_set(): return True
        try:
            ready = self.monitor.ready(check_stream=False)
            if (getattr(self.monitor, 'gap_generation', 0) != self.gap_generation
                    or (not ready and not self.ignore_busy)):
                self.interrupted = True
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
