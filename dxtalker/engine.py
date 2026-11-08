"""One owner for queued announcements, ID scheduling, audio and PTT."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime
import threading
import time

from .diagnostics import Diagnostics
from .audio import AudioOutput, AudioPlaybackError, Cancelled, scale_clip, join_clips, morse_clip, wav_clip
from .models import UTC
from .speech import SpeechService
from .ptt import create_ptt
from .receiver import ReceiveMonitor, ReceiveCancel, ChannelBusy


@dataclass(frozen=True)
class PreviewRequest:
    value: object
    settings: object


class Engine:
    def __init__(self, settings, emit, audio=None, speech=None, ptt_factory=create_ptt,
                 clock=time.monotonic, monitor=None):
        self.settings, self.emit = settings, emit
        self.source_available = lambda: True
        self.audio, self.speech = audio or AudioOutput(), speech or SpeechService()
        self.ptt_factory, self.clock = ptt_factory, clock
        self.monitor = monitor or ReceiveMonitor(clock)
        self.gate_state = None
        self.lock = threading.RLock()
        self.wake, self.cancel, self.quit = threading.Event(), threading.Event(), threading.Event()
        self.items = deque(maxlen=100)
        self.seen = {}
        self.enabled = self.busy = False
        self.local_enabled = False
        self.next_id, self.next_spot, self.alternate = 0, 0, 0
        self.next_voice_id = 0
        self.pending_voice_clip = None
        self.expired_spots = 0
        self.preparation_seconds = 0
        self.worker = threading.Thread(target=self._run, daemon=True, name="DX transmission")
        self.worker.start()

    def configure(self, settings):
        with self.lock:
            if self.enabled or self.local_enabled or self.busy:
                raise ValueError("Stop output and wait for Idle before applying settings")
            self.settings = settings
            self.pending_voice_clip = None
            self.items.clear()
            self.seen.clear()

    def enable(self):
        with self.lock:
            if self.busy:
                raise ValueError("Wait for the current preview to finish")
            self.settings.validate_rf()
            self.monitor.close()
            if self.settings.receive_guard:
                self.monitor.start(self.settings)
            self.gate_state = None
            self.local_enabled = False
            self.cancel.clear()
            self.items.clear()
            self.seen.clear()
            self.enabled, self.next_id, self.next_spot, self.alternate = True, self.clock(), 0, 0
            self.next_voice_id = self.clock()
            self.pending_voice_clip = None
        self.emit("output", "RF enabled. Identification due before announcements.")
        self.wake.set()

    def stop(self, message="RF disabled. Output stopped."):
        with self.lock:
            self.enabled = self.local_enabled = False
            self.pending_voice_clip = None
            self.cancel.set()
            self.items.clear()
        if not self.busy:
            self.monitor.close()
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
            if not (self.enabled or self.local_enabled):
                return False
            from .filtering import matches
            if not s.min_khz <= spot.frequency_khz <= s.max_khz or not matches(spot, s):
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

    def preview(self, kind, text=None, settings=None):
        if kind not in ("voice", "cw", "spot"):
            raise ValueError("Unknown preview")
        with self.lock:
            if self.enabled or self.local_enabled or self.busy or self.items:
                raise ValueError("Stop RF output and wait for Idle before previewing")
            preview_settings = settings or self.settings
            preview_settings.validate()
            if not preview_settings.preview_device:
                raise ValueError("Choose a local preview audio device")
            self.cancel.clear()
            self.items.append(("preview_" + kind, PreviewRequest(text, preview_settings)))
        self.wake.set()

    def identify(self):
        with self.lock:
            if not self.enabled:
                raise ValueError("Enable RF first or use a local ID preview")
            self.next_id = self.clock()
            self.next_voice_id = self.clock()
        self.wake.set()

    def _select(self):
        with self.lock:
            now = self.clock()
            fresh=deque((kind,value) for kind,value in self.items if kind!='spot' or (datetime.now(UTC)-value.timestamp).total_seconds()<=self.settings.max_age_seconds)
            self.expired_spots += len(self.items)-len(fresh)
            self.items.clear(); self.items.extend(fresh)
            if self.enabled and self.settings.receive_guard:
                ready = self.monitor.ready()
                if ready != self.gate_state:
                    self.gate_state = ready
                    self.emit('activity', 'Idle' if ready else 'RF waiting for receive audio to clear')
                if not ready:
                    return None
            if self.enabled and now >= self.next_id:
                self.busy = True
                return ("id_cw" if self.settings.id_mode=="Independent" else "id"), None, self.settings
            if self.enabled and self.settings.id_mode=="Independent" and now>=self.next_voice_id:
                self.busy = True
                return "id_voice", None, self.settings
            if self.items:
                kind, value = self.items[0]
                if kind == "spot" and (not (self.enabled or self.local_enabled) or now < self.next_spot):
                    if not (self.enabled or self.local_enabled):
                        self.items.popleft()
                    return None
                self.items.popleft()
                self.busy = True
                if (kind.startswith("preview_") or kind=="ptt_test") and isinstance(value, PreviewRequest):
                    return kind, value.value, value.settings
                return kind, value, self.settings
        return None

    def listen_locally(self):
        with self.lock:
            if self.enabled or self.busy:
                raise ValueError("Stop output and wait for Idle before starting local listening")
            if not self.settings.preview_device:
                raise ValueError("Choose a local preview audio device")
            self.monitor.close()
            self.cancel.clear()
            self.items.clear()
            self.seen.clear()
            self.next_spot = 0
            self.local_enabled = True
        self.emit("output", "Listening locally. Serial PTT disabled.")
        self.wake.set()

    def _speak(self, text, s):
        if hasattr(self.speech, "render_configured"):
            return self.speech.render_configured(text, s, self.cancel)
        return self.speech.render(text, s.voice, s.speech_rate, self.cancel)

    def _spot_audio(self, spot, s):
        if hasattr(self.speech, "render_spot"):
            return self.speech.render_spot(spot, s, self.cancel)
        return self._speak(". ".join(text for _, text in spot.announcement_groups(s)) + ".", s)

    def _voice(self, s):
        clip = wav_clip(s.voice_wav) if s.voice_mode == "WAV" else self._speak(s.voice_text, s)
        return scale_clip(clip, s.voice_id_volume_percent)

    def _id(self, s):
        mode = s.id_mode
        if mode == "Alternate":
            mode = "CW" if self.alternate % 2 == 0 else "Voice"
        if mode == "CW":
            return scale_clip(morse_clip(s.cw_text, s.cw_wpm, s.cw_hz), s.cw_volume_percent)
        if mode == "Voice":
            return self._voice(s)
        return join_clips([scale_clip(morse_clip(s.cw_text, s.cw_wpm, s.cw_hz), s.cw_volume_percent), self._voice(s)])

    def _wait(self, seconds):
        if self.cancel.wait(seconds):
            raise Cancelled()

    def _transmit(self, clip, s, volume=None):
        duration = clip.duration if clip is not None else 2
        if duration + (s.lead_ms + s.tail_ms) / 1000 > s.max_tx_seconds:
            raise ValueError("Audio exceeds the configured maximum transmit duration. Shorten it or change the limit.")
        if self.cancel.is_set():
            raise Cancelled()
        # Resolve the exact audio device before keying, then resolve again at playback.
        if clip is not None:
            self.audio.resolve(s.radio_device, clip.channels)
        if s.receive_guard and not self.monitor.ready():
            raise ChannelBusy()
        receive_cancel = ReceiveCancel(self.cancel, self.monitor) if s.receive_guard else None
        playback_cancel = receive_cancel or self.cancel
        if playback_cancel.is_set():
            if self.cancel.is_set(): raise Cancelled()
            if receive_cancel.fault: raise receive_cancel.fault
            raise ChannelBusy()
        ptt = self.ptt_factory(s)
        timeout = threading.Event()
        watchdog = None
        try:
            ptt.open()
            if s.receive_guard and not self.monitor.ready():
                raise ChannelBusy()
            if playback_cancel.is_set():
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
            if playback_cancel.wait(s.lead_ms / 1000): raise Cancelled()
            if clip is None:
                if playback_cancel.wait(2): raise Cancelled()
            else:
                self.audio.play(clip, s.radio_device, s.volume_percent if volume is None else volume, playback_cancel, deadline)
            if playback_cancel.wait(s.tail_ms / 1000): raise Cancelled()
        except Cancelled:
            if receive_cancel and not self.cancel.is_set():
                if receive_cancel.fault: raise receive_cancel.fault
                if receive_cancel.interrupted: raise ChannelBusy()
            raise
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
            kind, value = None, None
            s = self.settings
            try:
                task = self._select()
                if task is None:
                    continue
                kind, value, s = task
                if kind=="ptt_test":
                    self.emit('activity','PTT test. Waiting for channel clear' if s.receive_guard else 'PTT test')
                    while s.receive_guard and not self.monitor.ready():
                        if self.cancel.wait(.05):raise Cancelled()
                    self._transmit(None,s)
                    self.emit('journal','PTT test finished. RF remains disabled.')
                    continue
                preparation_started=time.monotonic()
                self.emit("activity", "Preparing audio")
                if kind == "spot":
                    if (datetime.now(UTC) - value.timestamp).total_seconds() > s.max_age_seconds:
                        continue
                    clip = self._spot_audio(value, s)
                elif kind == "preview_spot":
                    clip = self._spot_audio(value, s) if hasattr(value, "dx_call") else self._speak(value, s)
                elif kind == "preview_voice":
                    clip = self._voice(s)
                elif kind == "preview_cw":
                    clip = scale_clip(morse_clip(s.cw_text, s.cw_wpm, s.cw_hz), s.cw_volume_percent)
                elif kind=='id_cw':
                    clip = scale_clip(morse_clip(s.cw_text,s.cw_wpm,s.cw_hz),s.cw_volume_percent)
                elif kind=='id_voice':
                    clip = self.pending_voice_clip or self._voice(s)
                else:
                    clip = self._id(s)
                self.preparation_seconds=round(time.monotonic()-preparation_started,3)
                if isinstance(getattr(self.speech,'resolved_voice',None),str) and self.speech.resolved_voice:
                    self.emit('speech_voice',self.speech.resolved_voice)
                self.emit('performance',dict(operation=kind,preparation_seconds=self.preparation_seconds,audio_seconds=round(clip.duration,3),provider=s.speech_provider))
                if self.cancel.is_set():
                    raise Cancelled()
                if kind=='spot':
                    from .filtering import matches
                    if not matches(value,self.settings):continue
                if kind=='id_voice' and clip.duration+(s.lead_ms+s.tail_ms)/1000>=s.id_minutes*60:
                    raise ValueError('Voice ID is longer than the CW interval. Shorten the message or increase the interval.')
                if kind == "spot" and self.local_enabled:
                    if (datetime.now(UTC) - value.timestamp).total_seconds() > s.max_age_seconds:
                        continue
                    self.audio.play(clip, s.preview_device, s.local_volume_percent, self.cancel, self.clock() + 120)
                    self.emit("announcement", {"dx_call": value.dx_call, "frequency_khz": str(value.frequency_khz), "route": "local"})
                    with self.lock:
                        self.seen[value.key] = self.clock()
                        self.next_spot = self.clock() + s.spacing_seconds
                elif kind.startswith("preview_"):
                    self.emit("activity", "Local preview. No PTT.")
                    self.audio.play(clip, s.preview_device, s.local_volume_percent, self.cancel, self.clock() + 120)
                else:
                    with self.lock:
                        if not self.enabled:
                            raise Cancelled()
                        # Preserve prepared voice audio if a CW deadline needs priority.
                        if kind=='id_voice' and self.clock()+clip.duration+(s.lead_ms+s.tail_ms)/1000>=self.next_id:
                            self.pending_voice_clip=clip
                            self.next_id=self.clock()
                            continue
                        # Recheck expiry after synthesis and do not overrun the next ID.
                        if kind == "spot":
                            if (datetime.now(UTC) - value.timestamp).total_seconds() > s.max_age_seconds:
                                continue
                            if clip.duration + (s.lead_ms + s.tail_ms) / 1000 >= s.id_minutes * 60:
                                raise ValueError("Announcement is longer than the ID interval")
                            deadline=min(self.next_id,self.next_voice_id) if s.id_mode=="Independent" else self.next_id
                            if self.clock() + clip.duration + (s.lead_ms + s.tail_ms) / 1000 >= deadline:
                                self.items.appendleft((kind, value))
                                if s.id_mode=="Independent" and self.next_voice_id<self.next_id:
                                    self.next_voice_id = self.clock()
                                else:self.next_id = self.clock()
                                continue
                    self._transmit(clip, s, volume=100 if kind.startswith("id") else s.volume_percent)
                    if kind == "spot":
                        self.emit("announcement", {"dx_call": value.dx_call, "frequency_khz": str(value.frequency_khz), "route": "radio"})
                    with self.lock:
                        if kind == "id_voice":
                            self.pending_voice_clip=None
                            self.next_voice_id = self.clock() + s.voice_id_minutes * 60
                        elif kind in ("id", "id_cw"):
                            self.next_id = self.clock() + s.id_minutes * 60
                            self.alternate += 1
                        else:
                            self.seen[value.key] = self.clock()
                            self.next_spot = self.clock() + s.spacing_seconds
            except ChannelBusy:
                if kind=="ptt_test":
                    self.emit("journal","PTT test interrupted by receive audio. PTT released; run the test again when clear.")
                with self.lock:
                    if self.enabled and kind=='id_voice':self.pending_voice_clip=clip
                    if self.enabled and kind == 'spot':
                        self.items.appendleft((kind, value))
                self.emit('activity', 'RF waiting for receive audio to clear')
            except Cancelled:
                self.stop("Output cancelled. RF disabled.")
            except Exception as exc:
                evidence = dict(error_type=type(exc).__name__, frames=Diagnostics.frames(exc.__traceback__))
                if isinstance(exc, ValueError) and s.receive_guard:
                    evidence['receive_code']=getattr(self.monitor,'fault_code',None)
                if isinstance(exc, AudioPlaybackError):
                    evidence.update(code=exc.code, playback=exc.context, operation=kind,
                                    route='local' if kind.startswith('preview_') or self.local_enabled else 'radio')
                self.emit('diagnostic', evidence)
                # Transport errors can contain identifiers; only expected local
                # validation messages are shown verbatim.
                detail = str(exc) if isinstance(exc, (ValueError, TimeoutError, AudioPlaybackError)) else type(exc).__name__
                self.stop("Output fault. RF disabled.")
                self.emit("error", detail)
            finally:
                with self.lock:
                    self.busy = False
                    if kind is not None and not self.enabled:
                        self.monitor.close()
                if kind is not None:
                    self.emit("activity", "Idle")

        if hasattr(self.speech,'close'):
            self.speech.close()

    def test_ptt(self, settings=None):
        import re
        from dataclasses import replace
        s=replace(settings or self.settings,lead_ms=0,tail_ms=0)
        s.validate()
        if s.ptt_method=='VOX':raise ValueError('VOX needs an audio test. Use a monitored radio ID test after setup.')
        if not re.fullmatch(r'COM[1-9]\d{0,2}',s.serial_port,re.I):raise ValueError('Choose the serial COM port to test')
        with self.lock:
            if self.enabled or self.local_enabled or self.busy or self.items:raise ValueError('Stop output and wait for Idle before testing PTT')
            self.monitor.close()
            if s.receive_guard:self.monitor.start(s)
            self.cancel.clear()
            self.items.append(('ptt_test',PreviewRequest(None,s)))
        self.wake.set()

    def queue_status(self):
        with self.lock:
            spots=[v for k,v in self.items if k=='spot']
            age=max(((datetime.now(UTC)-v.timestamp).total_seconds() for v in spots),default=0)
            return len(spots),max(0,round(age)),self.expired_spots

    def catch_up(self):
        with self.lock:
            retained=[(k,v) for k,v in self.items if k!='spot']
            self.items.clear();self.items.extend(retained)
        self.emit('journal','Pending spots cleared. Listening for new spots; current audio and IDs are preserved.')

    def update_listening(self, settings):
        from dataclasses import replace
        from .listening import FIELDS
        with self.lock:
            self.settings=replace(self.settings,**{k:getattr(settings,k) for k in (*FIELDS,'listening_presets')})
            retained=[(k,v) for k,v in self.items if k!='spot']
            self.items.clear();self.items.extend(retained);self.seen.clear()
        self.wake.set()
