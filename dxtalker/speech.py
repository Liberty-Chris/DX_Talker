"""Provider independent speech plans. Providers produce PCM before output."""
from array import array
from html import escape
from pathlib import Path
import os
import re
import subprocess
import sys
import tempfile
import time

from .audio import Cancelled, Clip, WindowsSpeech, wav_clip
from .linux_speech import EspeakSpeech


def spot_plan(spot, settings):
    groups = spot.announcement_groups(settings)
    plan = []
    for index, (kind, group) in enumerate(groups):
        final = settings.group_pause_ms if index < len(groups) - 1 else 0
        if settings.character_pause_ms and kind != "intro":
            words = group.split()
            # Keep optional units naturally attached to the last frequency digit.
            if kind == "frequency" and settings.speak_units:
                words[-2:] = [" ".join(words[-2:])]
            plan.extend((word, settings.character_pause_ms if i < len(words) - 1 else final)
                        for i, word in enumerate(words))
        else:
            plan.append((group, final))
    return plan


def plan_ssml(plan):
    content = "".join(escape(text) + (f'<break time="{pause}ms"/>' if pause else " ") for text, pause in plan)
    return '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">' + content + '</speak>'


def normalize_clip(clip):
    """Normalize optional neural output to the coordinator's mono 22050 PCM format."""
    if clip.channels != 1:
        raise ValueError("Neural speech must produce mono PCM16 WAV")
    if clip.rate == 22050:
        return clip
    samples = array("h")
    samples.frombytes(clip.pcm)
    if sys.byteorder != "little":
        samples.byteswap()
    if not samples:
        raise ValueError("Neural voice produced no audio")
    count = round(len(samples) * 22050 / clip.rate)
    result = array("h")
    for i in range(count):
        pos = i * clip.rate / 22050
        lo = min(int(pos), len(samples) - 1)
        hi = min(lo + 1, len(samples) - 1)
        result.append(round(samples[lo] + (samples[hi] - samples[lo]) * (pos - lo)))
    if sys.byteorder != "little":
        result.byteswap()
    return Clip(result.tobytes())


def voice_plan(text):
    """Operator-only pause markers. No SSML or executable markup is accepted."""
    pattern=re.compile(r'\[pause(?:\s+(\d{1,5})(ms|s)?)?\]',re.I)
    plan=[];start=0
    for match in pattern.finditer(text):
        pause=int(match[1] or 1000)*(1000 if (match[2] or '').lower()=='s' else 1)
        if not 0<=pause<=10000:raise ValueError('Each voice pause must be between zero and ten seconds')
        phrase=text[start:match.start()].strip()
        if phrase:plan.append((phrase,pause))
        elif plan:plan[-1]=(plan[-1][0],plan[-1][1]+pause)
        else:plan.append(('',pause))
        start=match.end()
    tail=text[start:].strip()
    if tail:plan.append((tail,0))
    if not any(phrase for phrase,_ in plan):raise ValueError('Enter spoken words for the voice ID')
    if sum(pause for _,pause in plan)>120000:raise ValueError('Voice pauses exceed two minutes')
    return plan


class SpeechService:
    def __init__(self):
        self.windows = None
        self.packs = {}
        self.resolved_voice = ''

    def close(self):
        if self.windows:self.windows.close()
        self.packs.clear()

    def render_configured(self, text, settings, cancel):
        plan=voice_plan(text)
        return self._render(plan, settings, cancel, structured=len(plan)>1 or any(pause for _,pause in plan))

    def render_spot(self, spot, settings, cancel):
        return self._render(spot_plan(spot, settings), settings, cancel)

    def _render(self, plan, settings, cancel, structured=True):
        self.resolved_voice=''
        if settings.speech_provider == "ElevenLabs":
            from .cloud_speech import SharedSpeech
            client=SharedSpeech()
            # Older deployed gateways accept pauses through 3000 ms and require
            # text in every part. Longer/leading pauses are assembled locally.
            if any(pause>3000 or not text for text,pause in plan):
                chunks=[];size=0
                for text,pause in plan:
                    if cancel.is_set():raise Cancelled()
                    pcm=client.render_plan([(text,0)],settings.eleven_voice,cancel).pcm if text else b''
                    silence=b'\0\0'*round(22050*pause/1000);size+=len(pcm)+len(silence)
                    if size>22050*2*120:raise ValueError('Speech exceeds two minutes')
                    chunks.extend([pcm,silence])
                return Clip(b''.join(chunks))
            return client.render_plan(plan, settings.eleven_voice, cancel)
        if settings.speech_provider == "Recorded":
            from .voicepacks import VoicePack
            if not settings.voice_pack or Path(settings.voice_pack).name != settings.voice_pack:
                raise ValueError('Choose an installed recorded voice pack')
            key=(settings.voice_pack_root,settings.voice_pack)
            if key not in self.packs:
                if len(self.packs)>=4:self.packs.pop(next(iter(self.packs)))
                self.packs[key]=VoicePack(Path(settings.voice_pack_root)/settings.voice_pack)
            return self.packs[key].render(plan,settings,cancel)
        if settings.speech_provider in ("Windows", "eSpeak NG"):
            if self.windows is None:self.windows=EspeakSpeech() if settings.speech_provider == "eSpeak NG" else WindowsSpeech()
            clip=self.windows.render(plan_ssml(plan) if structured else plan[0][0],settings.voice,settings.speech_rate,cancel,settings.voice_gender,ssml=structured)
            self.resolved_voice=getattr(self.windows,'last_voice','')
            return clip
        if not Path(settings.piper_executable).is_file() or not Path(settings.piper_model).is_file():
            raise ValueError("Choose an installed Piper executable and an ONNX voice model in Speech and access")
        if not Path(settings.piper_model + ".json").is_file():
            raise ValueError("The Piper voice needs its matching .onnx.json configuration file")
        chunks = []
        deadline = time.monotonic() + 120
        with tempfile.TemporaryDirectory(prefix="DXTalker_neural_") as folder:
            output = Path(folder) / "voice.wav"
            for text, pause in plan:
                if not text:
                    chunks.append(b'\0\0'*round(22050*pause/1000));continue
                if cancel.is_set():
                    raise Cancelled()
                # No shell, no network and no provider access to PTT/audio devices.
                command = [settings.piper_executable, "--model", settings.piper_model,
                           "--output_file", str(output), "--length_scale", str(2 ** (-settings.speech_rate / 10))]
                flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                with subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                      stderr=subprocess.DEVNULL, creationflags=flags,
                                      env={**os.environ, "ORT_DISABLE_TELEMETRY": "1"}) as proc:
                    pending = (text + "\n").encode("utf-8")
                    while True:
                        if cancel.is_set() or time.monotonic() > deadline:
                            proc.kill()
                            proc.communicate()
                            if cancel.is_set():
                                raise Cancelled()
                            raise TimeoutError("Neural speech synthesis timed out")
                        try:
                            proc.communicate(input=pending, timeout=0.05)
                            break
                        except subprocess.TimeoutExpired:
                            pending = None
                    if proc.returncode:
                        raise ValueError("Piper failed. Check the executable, voice model and matching configuration.")
                clip = normalize_clip(wav_clip(output))
                chunks.extend([clip.pcm, b"\0\0" * round(22050 * pause / 1000)])
                if sum(map(len, chunks)) > 22050 * 2 * 120:
                    raise ValueError("Speech exceeds two minutes. Reduce pauses or shorten the announcement.")
        return Clip(b"".join(chunks))
