"""Ubuntu adapter tests use fake subprocesses. No audio, PTT or real keyring."""
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import wave
from dxtalker.audio import Cancelled
from dxtalker.linux_speech import EspeakSpeech
from dxtalker import linux_desktop, models, updates

class LinuxTests(unittest.TestCase):
    def test_wav_render_keeps_text_off_command_line_and_preserves_pause(self):
        seen = []
        class Process:
            returncode = 0
            def __init__(self, command, **options): self.command = command; seen.append((command, options))
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def communicate(self, value, timeout):
                self.input = value
                if '--voices' in self.command: return b'Pty Language Age/Gender VoiceName File\n 5 en-us --/M English gmw/en-US\n', b''
                seen.append(value)
                with wave.open(self.command[self.command.index('-w')+1], 'wb') as output:
                    output.setnchannels(1); output.setsampwidth(2); output.setframerate(22050); output.writeframes(b'\0\0'*2205)
                return b'', b''
        with patch('dxtalker.linux_speech.subprocess.Popen', Process):
            clip = EspeakSpeech('/usr/bin/espeak-ng').render('<speak>secret &amp; text<break time="500ms"/>again</speak>', '', 2, threading.Event(), ssml=True)
        self.assertEqual(clip.duration, .1)
        self.assertIn('-w', seen[0][0]); self.assertIn('--stdin', seen[0][0]); self.assertIn('-m', seen[0][0])
        self.assertNotIn('secret', ' '.join(seen[0][0]))
        self.assertIn(b'500ms', seen[1])
        with self.assertRaises(ValueError): EspeakSpeech('/fake').render('<speak><audio src="file:///tmp/x"/></speak>', '', 0, threading.Event(), ssml=True)

    def test_cancelled_speech_never_launches_a_process(self):
        cancel=threading.Event(); cancel.set()
        with patch('dxtalker.linux_speech.subprocess.Popen') as launched:
            with self.assertRaises(Cancelled): EspeakSpeech('/fake').render('test','',0,cancel)
            launched.assert_not_called()

    def test_secret_service_uses_stdin_and_stores_an_opaque_reference(self):
        with patch('dxtalker.linux_desktop.shutil.which', return_value='/usr/bin/secret-tool'), patch('dxtalker.linux_desktop.subprocess.run', return_value=SimpleNamespace(returncode=0,stdout='')) as run:
            reference=linux_desktop.protect_secret('synthetic-secret')
            args, kwargs=run.call_args
            self.assertNotIn('synthetic-secret',' '.join(args[0]))
            self.assertEqual(kwargs['input'],'synthetic-secret')
            self.assertRegex(reference,r'^secret-service:[0-9a-f]{32}$')
        with patch('dxtalker.linux_desktop._secret',return_value='synthetic-secret'):
            self.assertEqual(linux_desktop.protect_secret(reference,True),'synthetic-secret')
        with self.assertRaises(ValueError): linux_desktop.protect_secret('foreign-windows-blob',True)

    def test_keyring_failure_never_falls_back_to_plaintext(self):
        with patch('dxtalker.linux_desktop.shutil.which',return_value=None):
            with self.assertRaises(ValueError): linux_desktop.protect_secret('synthetic-secret')

    def test_xdg_settings_and_serial_validation(self):
        with patch('dxtalker.models.sys.platform','linux'), patch.dict('os.environ', {'XDG_CONFIG_HOME':'/tmp/synthetic-config','LOCALAPPDATA':''}):
            self.assertEqual(models.settings_path(),Path('/tmp/synthetic-config/dxtalker/settings.json'))
            settings=models.Settings(radio_device='fake',ptt_method='RTS',serial_port='/dev/serial/by-id/usb-test-if00',cw_text='TEST')
            settings.validate_rf()
            for value in ['/etc/passwd','/dev/null','/dev/serial/by-id/../null']:
                with self.assertRaises(ValueError):replace(settings,serial_port=value).validate_rf()

    def test_ubuntu_updater_does_not_select_a_windows_installer(self):
        base='https://github.com/Liberty-Chris/DX_Talker/releases/download/v9.0.0/'
        with patch.object(updates,'INSTALLER','DXTalker-Ubuntu-amd64.deb'):
            assets=[dict(name=name,browser_download_url=base+name,size=100) for name in ['DXTalker-Setup-Windows-x64.exe','SHA256SUMS.txt']]
            release=dict(tag_name='v9.0.0',assets=assets)
            self.assertIsNone(updates.select_release([release]))
            assets.append(dict(name=updates.INSTALLER,browser_download_url=base+updates.INSTALLER,size=100))
            self.assertTrue(updates.select_release([release]).installer_url.endswith('.deb'))
