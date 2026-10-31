"""One owner for queued announcements, ID scheduling, audio and PTT."""
from __future__ import annotations

from collections import deque
from datetime import datetime
import threading
import time

from .audio import AudioOutput, Cancelled, WindowsSpeech, join_clips, morse_clip, wav_clip
from .models import UTC
from .ptt import create_ptt


class Engine:
    def __init__(self, settings, emit, audio=None, speech=None, ptt_factory=create_ptt,
                 clock=time.monotonic):
        self.settings, self.emit = settings, emit
        self.rf_allowed = lambda: True
        self.audio, self.speech = audio or AudioOutput(), speech or WindowsSpeech()
        self.ptt_factory, self.clock = ptt_factory, clock
        self.lock = threading.RLock()
        self.wake, self.cancel, self.quit = threading.Event(), threading.Event(), threading.Event()
        self.items = deque(maxlen=100)
        self.seen = {}
        self.enabled = self.busy = False
        self.next_id, self.next_spot, self.alternate = 0, 0, 0
        self.worker = threading.Thread(target=self._run, daemon=True, name="DX transmission")
        self.worker.start()

    def configure(self, settings):
        with self.lock:
            if self.enabled or self.busy:
                raise ValueError("Stop output and wait for Idle before applying settings")
            self.settings = settings
            self.items.clear()
            self.seen.clear()

    def enable(self):
        with self.lock:
            if self.busy:
                raise ValueError("Wait for the current preview to finish")
            self.settings.validate_rf()
            if not self.rf_allowed():
                raise ValueError("A working source connection is required before enabling RF")
            self.cancel.clear()
            self.items.clear()
            self.seen.clear()
            self.enabled, self.next_id, self.next_spot, self.alternate = True, self.clock(), 0, 0
        self.emit("output", "RF enabled. Identification due before announcements.")
        self.wake.set()

    def stop(self, message="RF disabled. Output stopped."):
        with self.lock:
            self.enabled = False
            self.cancel.set()
            self.items.clear()
        self.wake.set()
        self.emit("output", message)

    def shutdown(self):
        self.stop()
        self.quit.set()
        self.wake.set()

    def offer(self, spot):
        now = self.clock()
        with self.lock:
            s = self.settings
            if not self.enabled:
                return False
            if not s.min_khz <= spot.frequency_khz <= s.max_khz:
                return False
            age = (datetime.now(UTC) - spot.timestamp).total_seconds()
            if age > s.max_age_seconds or age < -120:
                return False
            self.seen = {k: t for k, t in self.seen.items() if now - t < s.repeat_seconds}
            if spot.key in self.seen or any(kind == "spot" and value.key == spot.key for kind, value in self.items):
                return False
            if len(self.items) >= self.items.maxlen:
                return False
            self.items.append(("spot", spot))
        self.wake.set()
        return True

    def preview(self, kind, text=None):
        if kind not in ("voice", "cw", "spot"):
            raise ValueError("Unknown preview")
        with self.lock:
            if self.enabled or self.busy or self.items:
                raise ValueError("Stop RF output and wait for Idle before previewing")
            if not self.settings.preview_device:
                raise ValueError("Choose a local preview audio device")
            self.cancel.clear()
            self.items.append(("preview_" + kind, text))
        self.wake.set()

    def identify(self):
        with self.lock:
            if not self.enabled:
                raise ValueError("Enable RF first or use a local ID preview")
            self.next_id = self.clock()
        self.wake.set()

    def _select(self):
        with self.lock:
            now = self.clock()
            if self.enabled and now >= self.next_id:
                self.busy = True
                return "id", None, self.settings
            if self.items:
                kind, value = self.items[0]
                if kind == "spot" and (not self.enabled or now < self.next_spot):
                    if not self.enabled:
                        self.items.popleft()
                    return None
                self.items.popleft()
                self.busy = True
                return kind, value, self.settings
        return None

    def _voice(self, s):
        return wav_clip(s.voice_wav) if s.voice_mode == "WAV" else self.speech.render(s.voice_text, s.voice, s.speech_rate, self.cancel)

    def _id(self, s):
        mode = s.id_mode
        if mode == "Alternate":
            mode = "CW" if self.alternate % 2 == 0 else "Voice"
        if mode == "CW":
            return morse_clip(s.cw_text, s.cw_wpm, s.cw_hz)
        if mode == "Voice":
            return self._voice(s)
        return join_clips([morse_clip(s.cw_text, s.cw_wpm, s.cw_hz), self._voice(s)])

    def _wait(self, seconds):
        if self.cancel.wait(seconds):
            raise Cancelled()

    def _transmit(self, clip, s):
        if clip.duration + (s.lead_ms + s.tail_ms) / 1000 > s.max_tx_seconds:
            raise ValueError("Audio exceeds the configured maximum transmit duration. Shorten it or change the limit.")
        if self.cancel.is_set() or not self.rf_allowed():
            raise Cancelled()
        # Resolve the exact audio device before keying, then resolve again at playback.
        self.audio.resolve(s.radio_device, clip.channels)
        ptt = self.ptt_factory(s)
        timeout = threading.Event()
        watchdog = None
        try:
            ptt.open()
            if self.cancel.is_set():
                raise Cancelled()
            deadline = self.clock() + s.max_tx_seconds

            def release_on_timeout():
                timeout.set()
                self.cancel.set()
                # A second release attempt must not depend on a blocked audio API.
                try:
                    ptt.set(False)
                except Exception:
                    pass

            watchdog = threading.Timer(s.max_tx_seconds, release_on_timeout)
            watchdog.daemon = True
            watchdog.start()
            ptt.set(True)
            self.emit("activity", "Transmitting")
            self._wait(s.lead_ms / 1000)
            self.audio.play(clip, s.radio_device, s.volume_percent, self.cancel, deadline)
            self._wait(s.tail_ms / 1000)
        finally:
            try:
                ptt.close()
            finally:
                if watchdog:
                    watchdog.cancel()
        if timeout.is_set():
            raise TimeoutError("Transmit watchdog stopped output")

    def _run(self):
        while not self.quit.is_set():
            self.wake.wait(0.1)
            self.wake.clear()
            task = self._select()
            if task is None:
                continue
            kind, value, s = task
            try:
                self.emit("activity", "Preparing audio")
                if kind == "spot":
                    if (datetime.now(UTC) - value.timestamp).total_seconds() > s.max_age_seconds:
                        continue
                    clip = self.speech.render(value.speech, s.voice, s.speech_rate, self.cancel)
                elif kind == "preview_spot":
                    clip = self.speech.render(value, s.voice, s.speech_rate, self.cancel)
                elif kind == "preview_voice":
                    clip = self._voice(s)
                elif kind == "preview_cw":
                    clip = morse_clip(s.cw_text, s.cw_wpm, s.cw_hz)
                else:
                    clip = self._id(s)
                if self.cancel.is_set():
                    raise Cancelled()
                if kind.startswith("preview_"):
                    self.emit("activity", "Local preview. No PTT.")
                    self.audio.play(clip, s.preview_device, s.volume_percent, self.cancel, self.clock() + 120)
                else:
                    with self.lock:
                        if not self.enabled:
                            raise Cancelled()
                        # Recheck expiry after synthesis and do not overrun the next ID.
                        if kind == "spot":
                            if (datetime.now(UTC) - value.timestamp).total_seconds() > s.max_age_seconds:
                                continue
                            if clip.duration + (s.lead_ms + s.tail_ms) / 1000 >= s.id_minutes * 60:
                                raise ValueError("Announcement is longer than the ID interval")
                            if self.clock() + clip.duration + (s.lead_ms + s.tail_ms) / 1000 >= self.next_id:
                                self.items.appendleft((kind, value))
                                self.next_id = self.clock()
                                continue
                    self._transmit(clip, s)
                    with self.lock:
                        if kind == "id":
                            self.next_id = self.clock() + s.id_minutes * 60
                            self.alternate += 1
                        else:
                            self.seen[value.key] = self.clock()
                            self.next_spot = self.clock() + s.spacing_seconds
            except Cancelled:
                self.stop("Output cancelled. RF disabled.")
            except Exception as exc:
                # Transport errors can contain identifiers; only expected local
                # validation messages are shown verbatim.
                detail = str(exc) if isinstance(exc, (ValueError, TimeoutError)) else type(exc).__name__
                self.stop("Output fault. RF disabled.")
                self.emit("error", detail)
            finally:
                with self.lock:
                    self.busy = False
                self.emit("activity", "Idle")
