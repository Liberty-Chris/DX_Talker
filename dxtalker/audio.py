"""PCM generation, bounded speech synthesis and explicitly selected audio output."""
from __future__ import annotations

from array import array
from collections import deque
from dataclasses import dataclass
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import wave

MORSE = dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/.-?=",
                 ".- -... -.-. -.. . ..-. --. .... .. .--- -.- .-.. -- -. --- .--. --.- .-. ... - ..- ...- .-- -..- -.-- --.. ----- .---- ..--- ...-- ....- ..... -.... --... ---.. ----. -..-. .-.-.- -....- ..--.. -...-".split()))


class Cancelled(Exception):
    pass


class AudioPlaybackError(RuntimeError):
    """Fixed local messages and numeric evidence, safe for diagnostics and the UI."""
    MESSAGES = {
        'audio_stream_stopped': 'Audio output stopped before playback completed. Check the selected audio device, its connection and system sound settings.',
        'audio_finish_unconfirmed': 'Audio output stopped without confirming completion. Check the selected audio device and try a local preview again.',
        'audio_stream_fault': 'The audio device reported a playback fault. Check its connection and system sound settings before restarting output.',
        'audio_incomplete': 'Audio output ended before all samples were delivered. Check the selected audio device before restarting output.',
        'audio_underflow_persistent': 'Audio delivery repeatedly fell behind. Output stopped. Check audio drivers, power settings and other running applications before restarting output.',
        'audio_id_interrupted': 'Identification audio was interrupted. RF stopped. Check the audio device and restart RF when ready to send a complete ID.',
    }

    def __init__(self, code, *, frames_queued, frames_expected, sample_rate, channels, details=None):
        super().__init__(self.MESSAGES[code])
        self.code = code
        self.context = dict(frames_queued=frames_queued, frames_expected=frames_expected,
                            sample_rate=sample_rate, channels=channels)
        if details:
            self.context.update(details)


@dataclass(frozen=True)
class Clip:
    pcm: bytes
    rate: int = 22050
    channels: int = 1

    @property
    def duration(self):
        return len(self.pcm) / (self.rate * self.channels * 2)


def validate_morse(text):
    if not text.strip() or len(text) > 120:
        raise ValueError("Enter a CW ID of 1 to 120 characters")
    bad = sorted(set(text.upper()) - set(MORSE) - {" "})
    if bad:
        raise ValueError("Unsupported CW characters: " + " ".join(bad))


def morse_clip(text, wpm=20, hz=700, rate=22050):
    validate_morse(text)
    if not 5 <= wpm <= 50 or not 300 <= hz <= 1500:
        raise ValueError("CW speed or tone is outside its supported range")
    unit = 1.2 / wpm
    samples = array("h")

    def append(units, tone=False):
        count = round(units * unit * rate)
        if len(samples) + count > rate * 120:
            raise ValueError("CW recording exceeds two minutes. Shorten the ID or increase the speed.")
        ramp = max(1, int(rate * 0.004))
        for i in range(count):
            envelope = min(1.0, i / ramp, (count - 1 - i) / ramp)
            samples.append(round(13000 * envelope * math.sin(2 * math.pi * hz * i / rate)) if tone else 0)

    for wi, word in enumerate(text.upper().split()):
        if wi:
            append(7)
        for ci, char in enumerate(word):
            if ci:
                append(3)
            for si, symbol in enumerate(MORSE[char]):
                if si:
                    append(1)
                append(1 if symbol == "." else 3, True)
    if sys.byteorder != "little":
        samples.byteswap()
    return Clip(samples.tobytes(), rate)


def wav_clip(path):
    with wave.open(str(path), "rb") as wav:
        rate, channels, width, count = wav.getframerate(), wav.getnchannels(), wav.getsampwidth(), wav.getnframes()
        if width != 2 or channels not in (1, 2) or wav.getcomptype() != "NONE" or not 8000 <= rate <= 96000:
            raise ValueError("Use an uncompressed 16 bit PCM WAV, mono or stereo, 8 to 96 kHz")
        if not 0 < count / rate <= 120:
            raise ValueError("WAV duration must be greater than zero and no longer than 120 seconds")
        data = wav.readframes(count)
        if len(data) != count * channels * width:
            raise ValueError("WAV file is incomplete")
        return Clip(data, rate, channels)


def join_clips(clips):
    # Generated voice and Morse use this common format.
    if any(c.rate != 22050 or c.channels != 1 for c in clips):
        raise ValueError("Combined IDs require mono 22050 Hz audio. Convert the WAV or use alternating IDs.")
    return Clip((b"\0\0" * 11025).join(c.pcm for c in clips))


SPEECH_SCRIPT = r'''
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
  if ($env:DX_MODE -eq 'voices') {
    $names = @($synth.GetInstalledVoices() | Where-Object { $_.Enabled } | ForEach-Object { $_.VoiceInfo.Name })
    ConvertTo-Json -InputObject $names -Compress
  } else {
    $config = Get-Content -LiteralPath $env:DX_CONFIG -Raw -Encoding UTF8 | ConvertFrom-Json
    $synth.Rate = [int]$config.rate
    if ($config.voice) { $synth.SelectVoice([string]$config.voice) }
    elseif ($config.gender -and $config.gender -ne 'Any') {
      $synth.SelectVoiceByHints([System.Speech.Synthesis.VoiceGender]([string]$config.gender))
    }
    $format = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo -ArgumentList 22050, ([System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen), ([System.Speech.AudioFormat.AudioChannel]::Mono)
    $synth.SetOutputToWaveFile($env:DX_WAV, $format)
    if ($config.ssml) { $synth.SpeakSsml([string]$config.text) }
    else { $synth.Speak([string]$config.text) }
  }
} finally { $synth.Dispose() }
'''


PERSISTENT_SPEECH_SCRIPT = r'''
$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$defaultVoice = $synth.Voice.Name
try {
  while (($line = [Console]::ReadLine()) -ne $null) {
    try {
      $config = $line | ConvertFrom-Json
      $synth.SelectVoice($defaultVoice)
      $synth.Rate = [int]$config.rate
      if ($config.voice) { $synth.SelectVoice([string]$config.voice) }
      elseif ($config.gender -and $config.gender -ne 'Any') {
        $synth.SelectVoiceByHints([System.Speech.Synthesis.VoiceGender]([string]$config.gender))
      }
      $format = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo -ArgumentList 22050, ([System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen), ([System.Speech.AudioFormat.AudioChannel]::Mono)
      $synth.SetOutputToWaveFile([string]$config.output, $format)
      if ($config.ssml) { $synth.SpeakSsml([string]$config.text) }
      else { $synth.Speak([string]$config.text) }
      $synth.SetOutputToNull()
      [Console]::WriteLine((@{ok=$true;voice=$synth.Voice.Name} | ConvertTo-Json -Compress))
    } catch {
      $synth.SetOutputToNull()
      [Console]::WriteLine('{"ok":false}')
    }
  }
} finally { $synth.Dispose() }
'''


class WindowsSpeech:
    def __init__(self):
        self.process = None
        self.last_voice = ''

    def __enter__(self):return self

    def __exit__(self,*args):self.close()

    def __del__(self):
        try:self.close()
        except Exception:pass

    def close(self):
        proc,self.process=self.process,None
        if proc is not None:
            if proc.poll() is None:
                proc.terminate()
                try:proc.wait(timeout=2)
                except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=2)
            for stream in (proc.stdin,proc.stdout):
                if stream:stream.close()

    def _start(self):
        import os,queue,threading
        if sys.platform!='win32':raise RuntimeError('Windows speech synthesis requires Windows')
        if self.process is not None and self.process.poll() is None:return
        self.close()
        shell=str(Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe')
        self.responses=queue.Queue()
        self.process=subprocess.Popen([shell,'-NoLogo','-NoProfile','-NonInteractive','-Command',PERSISTENT_SPEECH_SCRIPT],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding='utf-8',creationflags=subprocess.CREATE_NO_WINDOW,bufsize=1)
        proc,responses=self.process,self.responses
        def read():
            try:
                for line in proc.stdout:responses.put(line)
            except (OSError,ValueError):pass
            finally:responses.put(None)
        threading.Thread(target=read,daemon=True,name='Windows speech responses').start()

    def _run(self, env, cancel, timeout=30):
        import os
        if sys.platform != "win32":
            raise RuntimeError("Windows speech synthesis requires Windows")
        shell = str(Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe")
        with subprocess.Popen([shell, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", SPEECH_SCRIPT],
                              env={**os.environ, **env}, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                              creationflags=subprocess.CREATE_NO_WINDOW) as proc:
            deadline = time.monotonic() + timeout
            while True:
                if cancel.is_set() or time.monotonic() > deadline:
                    proc.kill()
                    proc.communicate()
                    if cancel.is_set():
                        raise Cancelled()
                    raise TimeoutError("Speech synthesis timed out")
                try:
                    output, _ = proc.communicate(timeout=0.05)
                    break
                except subprocess.TimeoutExpired:
                    continue
            if proc.returncode:
                raise RuntimeError("Windows speech failed. Check the selected voice and installed Windows speech support.")
            return output.decode("utf-8-sig", errors="replace")

    def voices(self, cancel):
        result = json.loads(self._run({"DX_MODE": "voices"}, cancel))
        return result if isinstance(result, list) else [result]

    def render(self, text, voice, rate, cancel, gender="Any", ssml=False):
        import queue
        if not text.strip() or len(text)>(12000 if ssml else 1000):raise ValueError('Speech text must contain 1 to 1000 characters')
        if cancel.is_set():raise Cancelled()
        with tempfile.TemporaryDirectory(prefix='DXTalker_') as folder:
            output=Path(folder)/'speech.wav'
            try:
                self._start()
                import threading
                payload=json.dumps(dict(text=text,voice=voice,rate=rate,gender=gender,ssml=ssml,output=str(output)))+'\n'
                proc,responses=self.process,self.responses
                def write():
                    try:proc.stdin.write(payload);proc.stdin.flush()
                    except (OSError,ValueError):responses.put(None)
                deadline=time.monotonic()+30
                threading.Thread(target=write,daemon=True,name='Windows speech request').start()
                while True:
                    if cancel.is_set():raise Cancelled()
                    if time.monotonic()>deadline:raise TimeoutError('Speech synthesis timed out')
                    try:line=self.responses.get(timeout=.05)
                    except queue.Empty:continue
                    if line is None:raise ValueError('Windows speech process stopped. Check the installed voice and try again.')
                    reply=json.loads(line.lstrip('\ufeff'))
                    if not reply.get('ok'):raise ValueError('Windows speech failed. Check the selected voice and installed speech support.')
                    self.last_voice=reply.get('voice','System default')
                    return wav_clip(output)
            except BaseException:
                self.close()
                raise


class AudioOutput:
    @staticmethod
    def devices():
        import sounddevice as sd
        apis = sd.query_hostapis()
        return sorted({f"{apis[d['hostapi']]['name']} :: {d['name']}" for d in sd.query_devices() if d["max_output_channels"] > 0})

    @staticmethod
    def resolve(key, channels):
        import sounddevice as sd
        apis = sd.query_hostapis()
        matches = [i for i, d in enumerate(sd.query_devices())
                   if d["max_output_channels"] >= channels and f"{apis[d['hostapi']]['name']} :: {d['name']}" == key]
        if len(matches) != 1:
            raise ValueError("Audio device is missing or ambiguous. Refresh devices and select a uniquely named output.")
        return matches[0]

    def play(self, clip, device, volume, cancel, deadline):
        import sounddevice as sd
        index = self.resolve(device, clip.channels)
        # Callback output stays cancellable even if an audio endpoint stalls.
        data = array("h")
        data.frombytes(clip.pcm)
        if sys.byteorder != "little":
            data.byteswap()
        volume_reader=getattr(self,'volume_reader',None)
        gain = volume / 100
        if volume_reader is None:
            data = array("h", (round(n * gain) for n in data))
        if sys.byteorder != "little":
            data.byteswap()
        pcm, offset, total = data.tobytes(), 0, len(data) * 2
        finished = __import__("threading").Event()
        audio_fault = []
        inactive_since = None
        underruns = deque(maxlen=4)
        underrun_count = 0
        status_flags = set()
        last_callback = None
        max_callback_gap = 0
        actual_latency = None

        def report():
            host = device.split(' :: ', 1)[0]
            if host not in ('Windows WASAPI', 'MME', 'Windows DirectSound', 'Windows WDM-KS', 'ALSA', 'OSS', 'JACK', 'Core Audio'):
                host = 'Other'
            result = dict(status_flags=sorted(status_flags), output_underflows=underrun_count,
                          max_callback_gap_ms=round(max_callback_gap * 1000, 1),
                          host_api=host, requested_latency='high', requested_blocksize=0)
            if actual_latency is not None:
                result['latency_seconds'] = actual_latency
            return result

        def failure(code):
            return AudioPlaybackError(code, frames_queued=offset//(clip.channels*2),
                                      frames_expected=total//(clip.channels*2),
                                      sample_rate=clip.rate, channels=clip.channels, details=report())

        def callback(out, frames, timing, status):
            nonlocal offset, underrun_count, last_callback, max_callback_gap
            now = time.monotonic()
            if last_callback is not None:
                max_callback_gap = max(max_callback_gap, now - last_callback)
            last_callback = now
            if cancel.is_set() or now > deadline:
                raise sd.CallbackAbort
            if status:
                flags = {name for name in ('input_underflow', 'input_overflow', 'output_underflow', 'output_overflow', 'priming_output')
                         if getattr(status, name, False)}
                status_flags.update(flags or {'unknown_status'})
                if not flags or flags - {'output_underflow', 'priming_output'}:
                    audio_fault.append('audio_stream_fault')
                    raise sd.CallbackAbort
                if 'output_underflow' in flags:
                    underrun_count += 1
                    while underruns and now - underruns[0] > 2:
                        underruns.popleft()
                    underruns.append(now)
                    # A brief scheduling interruption may recover on this very
                    # callback. Repeated breakup must not hold a silent carrier.
                    if len(underruns) > 3 or underrun_count > 8:
                        audio_fault.append('audio_underflow_persistent')
                        raise sd.CallbackAbort
            size = frames * clip.channels * 2
            count = min(size, total - offset)
            block=pcm[offset:offset+count]
            if volume_reader is not None:
                samples=array('h');samples.frombytes(block)
                if sys.byteorder!='little':samples.byteswap()
                gain=max(0,min(100,volume_reader()))/100
                samples=array('h',(round(sample*gain) for sample in samples))
                if sys.byteorder!='little':samples.byteswap()
                block=samples.tobytes()
            out[:count] = block
            if count < size:
                out[count:] = b"\0" * (size - count)
            offset += count
            if offset == total:
                raise sd.CallbackStop

        with sd.RawOutputStream(device=index, samplerate=clip.rate, channels=clip.channels,
                                dtype="int16", callback=callback, finished_callback=finished.set,
                                blocksize=0, latency='high') as stream:
            latency = getattr(stream, 'latency', None)
            if isinstance(latency, (int, float)) and math.isfinite(latency) and 0 <= latency <= 120:
                actual_latency = round(latency, 4)
            while not finished.wait(0.02):
                if cancel.is_set() or time.monotonic() > deadline:
                    stream.abort()
                    break
                if not stream.active:
                    # Native completion may occur between Event.wait() and this
                    # state query. Wait for its Python notification rather than
                    # misreporting a normal final buffer as a device failure.
                    if finished.is_set():
                        continue
                    if audio_fault:
                        raise failure(audio_fault[0])
                    if offset < total:
                        raise failure('audio_stream_stopped')
                    now = time.monotonic()
                    if inactive_since is None:
                        inactive_since = now
                    if now-inactive_since >= .25:
                        raise failure('audio_finish_unconfirmed')
                else:
                    inactive_since = None
        if cancel.is_set():
            raise Cancelled()
        if time.monotonic() > deadline:
            raise TimeoutError("Maximum playback duration reached")
        if audio_fault:
            raise failure(audio_fault[0])
        if offset < total:
            raise failure('audio_incomplete')
        return report() if underrun_count else None


def scale_clip(clip, percent):
    """Scale a PCM segment before combining IDs with independent levels."""
    data = array("h")
    data.frombytes(clip.pcm)
    if sys.byteorder != "little":
        data.byteswap()
    data = array("h", (round(n * percent / 100) for n in data))
    if sys.byteorder != "little":
        data.byteswap()
    return Clip(data.tobytes(), clip.rate, clip.channels)
