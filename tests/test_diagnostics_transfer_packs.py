from dataclasses import replace
from datetime import datetime
import hashlib,json,tempfile,threading,unittest,wave,zipfile,zlib,base64
from pathlib import Path
from dxtalker.models import Settings,UTC,parse_line
from dxtalker.profiles import ProfileStore
from dxtalker.diagnostics import Diagnostics
from dxtalker import transfer
from dxtalker.voicepacks import VoicePack
from dxtalker.speech import spot_plan

class DiagnosticsTests(unittest.TestCase):
    def test_safe_traceback_stall_and_manual_export(self):
        with tempfile.TemporaryDirectory() as folder:
            tick=[0];d=Diagnostics(folder,clock=lambda:tick[0])
            try:raise RuntimeError('SECRET password and token URL should never be logged')
            except RuntimeError as exc:d.exception('test_exception',type(exc),exc.__traceback__)
            tick[0]=10;d.sample_stall();d.sample_stall();d.heartbeat();d.close()
            text=(Path(folder)/'diagnostics.jsonl').read_text()
            self.assertNotIn('SECRET',text);self.assertNotIn('password',text)
            records=[json.loads(x) for x in text.splitlines()]
            self.assertEqual(sum(x['event']=='ui_stall' for x in records),1)
            self.assertTrue(any(x['event']=='ui_responsive_again' for x in records))
            self.assertFalse(list(Path(folder).glob('*.pending')))
            d.export(Path(folder)/'report.zip')
            with zipfile.ZipFile(Path(folder)/'report.zip') as archive:
                self.assertEqual(set(archive.namelist()),{'diagnostics.jsonl','README.txt'})
    def test_unclean_marker_and_opt_out(self):
        with tempfile.TemporaryDirectory() as folder:
            d=Diagnostics(folder);d.close(clean=False);d.marker.write_text("2147483647")
            again=Diagnostics(folder);again.close()
            self.assertIn('"previous_incomplete": 1',(Path(folder)/'diagnostics.jsonl').read_text())
            private=Path(folder)/'disabled';d=Diagnostics(private,enabled=False);d.close();self.assertFalse(private.exists())

class TransferTests(unittest.TestCase):
    def data(self):
        return dict(schema='dxtalker-transfer',version=1,profiles=[dict(name='Test',connection={k:getattr(Settings(),k) for k in transfer.SOURCE_FIELDS})],filters={'frequency_unit':'MHz'})
    def test_qr_and_file_roundtrip_are_credential_free(self):
        with tempfile.TemporaryDirectory() as folder:
            store=ProfileStore(Path(folder)/'p.json',protector=lambda *a,**k:'ENCRYPTED_SECRET')
            store.save('Home',Settings(),'ACTUAL_PASSWORD',True)
            data=transfer.document(store.profiles,Settings())
            for qr in (True,False):
                raw=transfer.encode(data,qr=qr);self.assertEqual(transfer.decode(raw),data)
                self.assertNotIn('SECRET',str(raw));self.assertNotIn('ACTUAL_PASSWORD',str(raw))
    def test_rejects_secrets_unknown_versions_urls_and_zip_bombs(self):
        for field,value in [('password','secret'),('id','unknown')]:
            data=self.data();data['profiles'][0][field]=value
            with self.assertRaises(ValueError):transfer.encode(data)
        data=self.data();data['profiles'][0]['connection'].update(source_type='HTTPS JSON',feed_url='https://example.org/?token=secret')
        with self.assertRaises(ValueError):transfer.encode(data)
        bomb='DXT1:'+base64.urlsafe_b64encode(zlib.compress(b' '*100000)).decode().rstrip('=')
        with self.assertRaises(ValueError):transfer.decode(bomb)
        with self.assertRaises(ValueError):transfer.decode('DXT1:!!')
    def test_directory_status_and_schema(self):
        entry=dict(id='test',name='Test',connection=self.data()['profiles'][0]['connection'],status='retired',checked='',description='Test fixture')
        self.assertEqual(transfer.catalog(dict(schema='dxtalker-directory',version=1,entries=[entry]))[0]['status'],'retired')
        with self.assertRaises(ValueError):transfer.catalog(dict(schema='dxtalker-directory',version=1,entries=[entry,entry]))

class VoicePackTests(unittest.TestCase):
    def test_recorded_playback_has_pauses_checksums_and_no_inference(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);clips={}
            for key in ('phrase:new dx on','seven','zero','four','kilohertz','Kilo'.lower(),'Tango'.lower(),'Bravo'.lower(),'November'.lower()):
                name=hashlib.sha256(key.encode()).hexdigest()[:24]+'.wav';path=root/name
                with wave.open(str(path),'wb') as output:output.setparams((1,2,22050,0,'NONE','not compressed'));output.writeframes(b'\0\0'*2205)
                clips[key]=dict(file=name,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            (root/'voice.json').write_text(json.dumps(dict(schema='dxtalker-voice',version=1,label='Fixture',clips=clips)))
            s=Settings(speech_provider='Recorded');now=datetime.now(UTC)
            spot=parse_line(f'DX de N0CALL: 7074 KT4BN {now:%H%M}Z','test',now)
            pack=VoicePack(root);clip=pack.render(spot_plan(spot,s),s,threading.Event())
            self.assertGreater(clip.duration,1)
            with self.assertRaises(ValueError):pack.render([('Unknown custom words',0)],s,threading.Event())
            first=next(iter(clips.values()));(root/first['file']).write_bytes(b'bad')
            with self.assertRaises(ValueError):VoicePack(root).clip('phrase:new dx on')
