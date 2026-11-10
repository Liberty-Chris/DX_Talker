from io import BytesIO
from pathlib import Path
import json
import tempfile
import threading
import unittest
from urllib.error import HTTPError, URLError
from dxtalker.audio import Clip, Cancelled
from dxtalker.elevenlabs import ElevenLabs, build_pack, NoRedirect, CancelEither
from dxtalker.voicepacks import VoicePack, vocabulary


class ElevenLabsTests(unittest.TestCase):
    def test_pcm_api_uses_fixed_host_and_no_secrets_in_pack(self):
        requests=[]
        def open_request(req,timeout):
            requests.append(req)
            return BytesIO(b'\x00\x10'*1000)
        client=ElevenLabs('test_secret',opener=open_request)
        clip=client.render('Alpha','testVoice','eleven_multilingual_v2',threading.Event())
        self.assertGreater(clip.duration,0)
        req=requests[0]
        self.assertEqual(req.full_url,'https://api.elevenlabs.io/v1/text-to-speech/testVoice?output_format=pcm_22050')
        self.assertEqual(json.loads(req.data)['text'],'Alpha')
        self.assertEqual(req.get_header('Xi-api-key'),'test_secret')
        with self.assertRaises(ValueError):client.render('Alpha','../evil','model',threading.Event())
        with self.assertRaises(ValueError):NoRedirect().redirect_request(None,None,None,None,None,None)
        cancel=threading.Event();cancel.set()
        with self.assertRaises(Cancelled):client.render('Alpha','voice','model',cancel)
        self.assertEqual(len(requests),1)

    def test_voice_page_accepts_extra_defaults_but_only_displays_one_hundred(self):
        body=json.dumps({'voices':[{'voice_id':f'voice{i}','name':f'Voice {i}'} for i in range(120)]}).encode()
        client=ElevenLabs('key',opener=lambda *a,**k:BytesIO(body))
        voices=client.voices(threading.Event())
        self.assertEqual(len(voices),100)
        self.assertEqual(voices['Voice 0 (voice0)'],'voice0')

    def test_api_errors_are_actionable_and_never_echo_credentials_or_bodies(self):
        for code in [401,402,403,429,500]:
            def fail(req,timeout):raise HTTPError(req.full_url,code,'SECRET server body',{},None)
            with self.assertRaises(ValueError) as error:
                ElevenLabs('private_key',opener=fail).render('Alpha','voice','model',threading.Event())
            self.assertNotIn('SECRET',str(error.exception));self.assertNotIn('private_key',str(error.exception))
        def fail(req,timeout):raise URLError('SECRET')
        with self.assertRaisesRegex(ValueError,'securely'):
            ElevenLabs('private_key',opener=fail).render('Alpha','voice','model',threading.Event())
        with self.assertRaisesRegex(ValueError,'invalid PCM'):
            ElevenLabs('private_key',opener=lambda *a,**k:BytesIO(b'x')).render('Alpha','voice','model',threading.Event())

    def test_interrupted_generation_resumes_verified_clips_without_more_api_calls(self):
        cancel=threading.Event();calls=[]
        class Client:
            def render(self,text,*args):
                calls.append(text)
                return Clip(b'\x00\x10'*500)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'voice'
            def progress(done,total):
                if done==3:cancel.set()
            with self.assertRaises(Cancelled):build_pack(Client(),path,'Fixture','voice','model',cancel=cancel,progress=progress)
            self.assertFalse(path.exists());self.assertEqual(len(calls),3)
            with self.assertRaisesRegex(ValueError,'different voice settings'):
                build_pack(Client(),path,'Fixture','otherVoice','model')
            cancel.clear();build_pack(Client(),path,'Fixture','voice','model',cancel=cancel)
            self.assertEqual(len(calls),len(vocabulary()))
            pack=VoicePack(path);self.assertEqual(len(pack.data['clips']),len(vocabulary()))
            self.assertGreater(pack.render([('New DX on',0)],None,cancel).duration,0)
            for pronunciation in ('poughta','phota','sota'):
                self.assertIn(pronunciation,calls)
                natural=pack.render([(pronunciation,0)],None,cancel)
                del pack.data['clips']['phrase:'+pronunciation]
                compatible=pack.render([(pronunciation,0)],None,cancel)
                self.assertGreater(compatible.duration,natural.duration)
            self.assertNotIn('api_key',(path/'voice.json').read_text())
            with self.assertRaisesRegex(ValueError,'never overwritten'):build_pack(Client(),path,'Fixture','voice','model')

    def test_application_shutdown_prevents_further_paid_requests_without_tk_callbacks(self):
        local,shutdown=threading.Event(),threading.Event();calls=[]
        class Client:
            def render(self,text,*args):
                calls.append(text);shutdown.set();return Clip(b'\x00\x10'*500)
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(Cancelled):
                build_pack(Client(),Path(folder)/'voice','Fixture','voice','model',cancel=CancelEither(local,shutdown))
            self.assertEqual(len(calls),1)
            self.assertFalse((Path(folder)/'voice').exists())

    def test_corrupt_partial_clip_is_regenerated_and_response_size_is_bounded(self):
        calls=[];cancel=threading.Event()
        class Client:
            def render(self,text,*args):calls.append(text);return Clip(b'\x00\x10'*500)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'voice'
            with self.assertRaises(Cancelled):
                build_pack(Client(),path,'Fixture','voice','model',cancel=cancel,progress=lambda done,total:cancel.set() if done==1 else None)
            partial=path.with_name('voice.partial');next(partial.glob('*.wav')).write_bytes(b'broken')
            cancel.clear();build_pack(Client(),path,'Fixture','voice','model',cancel=cancel)
            self.assertEqual(len(calls),len(vocabulary())+1)
        with self.assertRaisesRegex(ValueError,'exceeded'):
            ElevenLabs('key',opener=lambda *a,**k:BytesIO(b'x'*441002)).render('Alpha','voice','model',cancel)
