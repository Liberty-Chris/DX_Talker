"""Offline eSpeak NG renders WAV only. The coordinator owns playback and PTT."""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET

class EspeakSpeech:
    def __init__(self, executable=None):
        self.executable = executable or shutil.which('espeak-ng')
        self.last_voice = ''
    def close(self): pass
    def _run(self, arguments, text, cancel, timeout=30):
        from .audio import Cancelled
        if cancel.is_set(): raise Cancelled()
        if not self.executable: raise ValueError('Install eSpeak NG to use the Ubuntu system voice.')
        with subprocess.Popen([self.executable] + arguments, stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as process:
            deadline = time.monotonic() + timeout
            pending = text.encode('utf-8')
            while True:
                if cancel.is_set() or time.monotonic() >= deadline:
                    process.kill(); process.communicate()
                    if cancel.is_set(): raise Cancelled()
                    raise TimeoutError('System speech synthesis timed out')
                try:
                    output, unused = process.communicate(pending, timeout=.05)
                    break
                except subprocess.TimeoutExpired: pending = None
            if process.returncode: raise ValueError('System speech failed. Check eSpeak NG and the selected voice.')
            if len(output) > 1024 * 1024: raise ValueError('System voice response exceeds its limit')
            return output.decode('utf-8', errors='replace')
    def voices(self, cancel):
        output = self._run(['--voices'], '', cancel)
        result = []
        for line in output.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 5 and re.fullmatch(r'[A-Za-z0-9_/-]{1,100}', parts[4]):
                result.append(parts[4])
        return sorted(set(result))
    def render(self, text, voice, rate, cancel, gender='Any', ssml=False):
        from .audio import wav_clip
        if not text.strip() or len(text) > (12000 if ssml else 1000) or not -10 <= rate <= 10:
            raise ValueError('Speech text or speed is outside the supported range')
        if voice and voice not in self.voices(cancel): raise ValueError('Choose an installed system voice')
        selected = voice or 'en-us'
        if gender == 'Female': selected += '+f3'
        elif gender == 'Male': selected += '+m3'
        if ssml:
            root = ET.fromstring(text)
            if root.tag.split('}')[-1] != 'speak': raise ValueError('Invalid speech plan')
            for node in root:
                if node.tag.split('}')[-1] != 'break' or list(node) or not re.fullmatch(r'\d{1,6}ms', node.get('time', '')):
                    raise ValueError('Unsupported speech plan')
                if int(node.get('time')[:-2]) > 120000: raise ValueError('Speech pause exceeds its limit')
                node.tag = 'break'
            root.tag = 'speak'
            text = ET.tostring(root, encoding='unicode')
        with tempfile.TemporaryDirectory(prefix='DXTalker_speech_') as folder:
            output = Path(folder) / 'speech.wav'
            arguments = ['--stdin', '-w', str(output), '-v', selected, '-s', str(round(175 * 2 ** (rate / 20)))]
            if ssml: arguments.append('-m')
            self._run(arguments, text, cancel)
            self.last_voice = selected
            return wav_clip(output)
