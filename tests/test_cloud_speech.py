from dataclasses import replace
from io import BytesIO
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from dxtalker import __version__
from dxtalker.audio import Cancelled, Clip
from dxtalker.cloud_speech import SharedSpeech, configuration, NoRedirect
from dxtalker.models import Settings
from dxtalker.speech import SpeechService

CONFIG=dict(schema='dxtalker-speech-service',version=1,url='https://speech.example.org/speech.php',pilot_token='dxp_'+'a'*40)
ROOT=Path(__file__).resolve().parents[1]

class SharedSpeechTests(unittest.TestCase):
    def test_build_configuration_rejects_owner_keys_and_unsafe_urls(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'speech.json';path.write_text(json.dumps(CONFIG));self.assertEqual(configuration(path),CONFIG)
            for change in [dict(api_key='PRIVATE'),dict(url='http://example.org/'),dict(url='https://user:password@example.org/'),dict(url='https://example.org/?token=secret'),dict(pilot_token=''),dict(pilot_token='sk_'+'a'*40)]:
                path.write_text(json.dumps({**CONFIG,**change}))
                with self.assertRaises(ValueError):configuration(path)

    def test_shared_requests_do_not_contain_provider_keys_and_preserve_plan(self):
        requests=[]
        def opener(req,timeout):requests.append(req);return BytesIO(b'\x00\x10'*100)
        clip=SharedSpeech(CONFIG,opener).render_plan([('New DX on',450),('Alpha',0)],'voiceA',threading.Event())
        self.assertGreater(clip.duration,0)
        self.assertEqual(json.loads(requests[0].data)['plan'],[['New DX on',450],['Alpha',0]])
        self.assertEqual(requests[0].get_header('User-agent'),'DXTalker/'+__version__)
        self.assertIsNone(requests[0].get_header('Xi-api-key'))
        self.assertEqual(requests[0].get_header('X-dxtalker-pilot'),'dxp_'+'a'*40)
        with self.assertRaises(ValueError):NoRedirect().redirect_request(None)
        cancel=threading.Event();cancel.set()
        with self.assertRaises(Cancelled):SharedSpeech(CONFIG,opener).render_plan([('Alpha',0)],'',cancel)
        self.assertEqual(len(requests),1)

    def test_catalog_errors_and_limits_are_safe(self):
        catalog=dict(schema='dxtalker-speech-catalog',version=1,model_id='eleven_multilingual_v2',voices=[dict(id='voiceA',name='Pilot voice')])
        client=SharedSpeech(CONFIG,lambda *a,**k:BytesIO(json.dumps(catalog).encode()))
        self.assertEqual(client.voices(threading.Event()),{'Pilot voice (voiceA)':'voiceA'})
        for code in [401,403,429,503,500]:
            def fail(*a,**k):raise HTTPError(CONFIG['url'],code,'PRIVATE_RESPONSE',{},None)
            with self.assertRaises(ValueError) as exc:SharedSpeech(CONFIG,fail).render_plan([('Alpha',0)],'',threading.Event())
            self.assertNotIn('PRIVATE_RESPONSE',str(exc.exception))
        with self.assertRaisesRegex(ValueError,'size limit'):
            SharedSpeech(CONFIG,lambda *a,**k:BytesIO(b'x'*(22050*2*120+1))).render_plan([('Alpha',0)],'',threading.Event())

    def test_catalog_identifies_itself_and_cloudflare_403_does_not_blame_voice(self):
        seen=[]
        def blocked(req,timeout):
            seen.append(req)
            raise HTTPError(req.full_url,403,'Forbidden',{},BytesIO(b'error code: 1010'))
        with self.assertRaisesRegex(ValueError,'website blocked access'):
            SharedSpeech(CONFIG,blocked).catalog(threading.Event())
        self.assertEqual(seen[0].get_header('User-agent'),'DXTalker/'+__version__)
        self.assertIsNone(seen[0].data)

    def test_only_explicit_service_denials_are_described_as_voice_or_model_errors(self):
        for body,expected in [(b'{"error":"voice_unavailable","private":"DO_NOT_ECHO"}','voice or model'),
                              (b'{"error":"model_changed"}','voice or model'),
                              (b'<html>DO_NOT_ECHO</html>','website blocked access'),
                              (b'{"error":"unrecognized"}','website blocked access')]:
            def blocked(req,timeout):raise HTTPError(req.full_url,403,'Forbidden',{},BytesIO(body))
            with self.assertRaisesRegex(ValueError,expected) as exc:
                SharedSpeech(CONFIG,blocked).render_plan([('Alpha',0)],'',threading.Event())
            self.assertNotIn('DO_NOT_ECHO',str(exc.exception))

    def test_provider_routes_through_coordinator_pcm_boundary(self):
        s=replace(Settings(),speech_provider='ElevenLabs',eleven_voice='voiceA')
        with patch('dxtalker.cloud_speech.SharedSpeech') as client:
            client.return_value.render_plan.return_value=Clip(b'\x00\x10'*100)
            clip=SpeechService().render_configured('Test ID',s,threading.Event())
            self.assertEqual(clip.channels,1)
            self.assertEqual(client.return_value.render_plan.call_args.args[:2],([('Test ID',0)],'voiceA'))

    def test_dreamhost_install_keeps_key_private_and_preserves_pilot_token(self):
        spec=importlib.util.spec_from_file_location('speech_configure',ROOT/'server/speech/configure.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as folder:
            private=Path(folder)/'private';web=Path(folder)/'web/speech'
            args=(web,'https://speech.example.org/speech/speech.php',private,'OWNER_KEY',[dict(id='voiceA',name='Pilot voice')])
            path=module.install(*args)
            self.assertNotIn('OWNER_KEY',(web/'speech.php').read_text())
            client=json.loads((private/'client.json').read_text());self.assertNotIn('api_key',client)
            self.assertEqual(json.loads(path.read_text())['api_key'],'OWNER_KEY')
            if os.name != "nt":self.assertEqual(path.stat().st_mode & 0o777,0o600)
            token=client['pilot_token'];module.install(*args)
            self.assertEqual(json.loads((private/'client.json').read_text())['pilot_token'],token)
            with self.assertRaises(ValueError):module.install(web,args[1],web/'private','OWNER_KEY',args[-1])


    def test_build_rejects_private_account_configuration_and_removes_it_before_packaging(self):
        import subprocess
        import sys
        path=ROOT/'assets/services/speech.json';original=path.read_bytes()
        try:
            owner={**CONFIG,'api_key':'PRIVATE_UPSTREAM_KEY'}
            result=subprocess.run([sys.executable,str(ROOT/'scripts/configure_speech_build.py')],env={**os.environ,'DXTALKER_SPEECH_CONFIG':json.dumps(owner)},capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertNotIn('PRIVATE_UPSTREAM_KEY',result.stdout+result.stderr)
            self.assertNotIn(b'PRIVATE_UPSTREAM_KEY',path.read_bytes())
        finally:path.write_bytes(original)
