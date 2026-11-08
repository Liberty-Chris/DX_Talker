"""Persistent SAPI 5 worker. Render PCM before the shared coordinator may key."""
import os
import queue
import subprocess
import tempfile
import threading
import time
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape


def sapi_xml(ssml):
    root = ET.fromstring(ssml)
    if root.tag.split('}')[-1] != 'speak': raise ValueError('Invalid speech plan')
    result = [escape(root.text or '')]
    for item in root:
        if item.tag.split('}')[-1] != 'break' or list(item): raise ValueError('Unsupported speech plan')
        value = item.get('time', '')
        if not value.endswith('ms') or not value[:-2].isdigit(): raise ValueError('Invalid speech pause')
        pause = int(value[:-2])
        if pause > 120000: raise ValueError('Speech pause exceeds the limit')
        result.append('<silence msec="' + str(pause) + '"/>')
        result.append(escape(item.tail or ''))
    return ''.join(result)


class WindowsSpeech:
    def __init__(self):
        self.process, self.responses = None, None
        self.last_voice = ''
    def __enter__(self): return self
    def __exit__(self, *args): self.close()
    def __del__(self):
        try: self.close()
        except Exception: pass

    def close(self):
        process, self.process = self.process, None
        if process is None: return
        if process.poll() is None:
            process.terminate()
            try: process.wait(timeout=2)
            except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=2)
        for stream in (process.stdin, process.stdout):
            if stream: stream.close()

    def _reply(self, cancel, timeout=30):
        from dxtalker.audio import Cancelled
        deadline = time.monotonic() + timeout
        while True:
            if cancel.is_set(): raise Cancelled()
            if time.monotonic() >= deadline: raise TimeoutError('Windows speech synthesis timed out')
            try: line = self.responses.get(timeout=0.05)
            except queue.Empty: continue
            if line is None or len(line) > 131072: raise ValueError('Windows speech worker stopped. Check the installed voice.')
            reply = ET.fromstring(line)
            if reply.tag == 'error': raise ValueError('Windows speech failed. Check the selected voice and installed speech support.')
            return reply

    def _start(self, cancel):
        if self.process is not None and self.process.poll() is None: return
        self.close()
        system = os.environ['SystemRoot']
        candidates = [os.path.join(system, 'System32', 'cscript.exe')]
        fallback = os.path.join(system, 'SysWOW64', 'cscript.exe')
        if os.path.isfile(fallback): candidates.append(fallback)
        failure = None
        for executable in candidates:
            try:
                self.responses = queue.Queue()
                worker = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sapi_worker.vbs')
                self.process = subprocess.Popen([executable, '//nologo', worker], stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000))
                process, responses = self.process, self.responses
                def read(process=process, responses=responses):
                    try:
                        for line in process.stdout:
                            responses.put(line)
                    except (OSError, ValueError): pass
                    finally: responses.put(None)
                threading.Thread(target=read, daemon=True, name='XP speech responses').start()
                if self._reply(cancel, 10).tag != 'ready': raise ValueError('Windows speech worker could not start')
                return
            except Exception as error:
                failure = error
                self.close()
                if cancel.is_set(): raise
        raise failure or ValueError('No Windows speech engine is available')

    def _request(self, request, cancel):
        self._start(cancel)
        data = ET.tostring(request, encoding='us-ascii') + b'\n'
        if len(data) > 131072: raise ValueError('Speech request exceeds the limit')
        process, responses = self.process, self.responses
        def write():
            try: process.stdin.write(data); process.stdin.flush()
            except (OSError, ValueError): responses.put(None)
        threading.Thread(target=write, daemon=True, name='XP speech request').start()
        return self._reply(cancel)

    def voices(self, cancel):
        try:
            reply = self._request(ET.Element('request', mode='voices'), cancel)
            if reply.tag != 'voices': raise ValueError('Windows speech returned an invalid voice list')
            return [item.text or '' for item in reply.findall('voice')]
        except BaseException:
            self.close(); raise

    def render(self, text, voice, rate, cancel, gender='Any', ssml=False):
        from dxtalker.audio import Cancelled, wav_clip
        if cancel.is_set(): raise Cancelled()
        if not text.strip() or len(text) > (12000 if ssml else 1000) or not -10 <= rate <= 10:
            raise ValueError('Speech text or speed is outside the supported range')
        with tempfile.TemporaryDirectory(prefix='DXTalker_') as folder:
            output = os.path.join(folder, 'speech.wav')
            request = ET.Element('request', mode='render', voice=voice, gender=gender, rate=str(rate), output=output, xml='1' if ssml else '0')
            ET.SubElement(request, 'speech').text = sapi_xml(text) if ssml else text
            try:
                reply = self._request(request, cancel)
                if reply.tag != 'ok': raise ValueError('Windows speech returned an invalid response')
                self.last_voice = reply.get('voice', 'System default')
                return wav_clip(output)
            except BaseException:
                self.close(); raise
