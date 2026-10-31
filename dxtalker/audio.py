"""PCM generation, bounded speech synthesis and explicitly selected audio output."""
from __future__ import annotations

from array import array
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
    $format = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo -ArgumentList 22050, ([System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen), ([System.Speech.AudioFormat.AudioChannel]::Mono)
    $synth.SetOutputToWaveFile($env:DX_WAV, $format)
    $synth.Speak([string]$config.text)
  }
} finally { $synth.Dispose() }
'''


class WindowsSpeech:
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

    def render(self, text, voice, rate, cancel):
        if not text.strip() or len(text) > 1000:
            raise ValueError("Speech text must contain 1 to 1000 characters")
        with tempfile.TemporaryDirectory(prefix="DXTalker_") as folder:
            config, output = Path(folder) / "speech.json", Path(folder) / "speech.wav"
            config.write_text(json.dumps({"text": text, "voice": voice, "rate": rate}), encoding="utf-8")
            self._run({"DX_MODE": "speech", "DX_CONFIG": str(config), "DX_WAV": str(output)}, cancel)
            return wav_clip(output)


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
        gain = volume / 100
        data = array("h", (round(n * gain) for n in data))
        if sys.byteorder != "little":
            data.byteswap()
        pcm, offset, total = data.tobytes(), 0, len(data) * 2
        finished = __import__("threading").Event()
        audio_fault = []

        def callback(out, frames, timing, status):
            nonlocal offset
            if cancel.is_set() or time.monotonic() > deadline:
                raise sd.CallbackAbort
            if status:
                audio_fault.append(True)
                raise sd.CallbackAbort
            size = frames * clip.channels * 2
            count = min(size, total - offset)
            out[:count] = pcm[offset:offset + count]
            if count < size:
                out[count:] = b"\0" * (size - count)
            offset += count
            if offset == total:
                raise sd.CallbackStop

        with sd.RawOutputStream(device=index, samplerate=clip.rate, channels=clip.channels,
                                dtype="int16", callback=callback, finished_callback=finished.set,
                                blocksize=1024) as stream:
            while not finished.wait(0.02):
                if cancel.is_set() or time.monotonic() > deadline:
                    stream.abort()
                    break
                if not stream.active:
                    raise RuntimeError("Audio output stopped unexpectedly")
        if cancel.is_set():
            raise Cancelled()
        if time.monotonic() > deadline:
            raise TimeoutError("Maximum playback duration reached")
        if audio_fault:
            raise RuntimeError("Audio stream reported a playback fault")
        if offset < total:
            raise RuntimeError("Audio output did not complete")
