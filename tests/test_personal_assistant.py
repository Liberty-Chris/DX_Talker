from dataclasses import replace
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from array import array
import json
import queue
import tempfile
import threading
import time
import unittest
import wave

from dxtalker.models import Settings, UTC, parse_line, parse_json_feed
from dxtalker.filtering import matches,rejection
from dxtalker.privileges import eligibility
from dxtalker.receiver import ReceiveMonitor
from dxtalker.speech import SpeechService, voice_plan
from dxtalker.audio import WindowsSpeech, Cancelled, Clip
from dxtalker.spotting import command
from dxtalker import transfer
from test_engine import EngineTests as _EngineTests,wait_for


class PrivilegeTests(unittest.TestCase):
    def test_cross_platform_reviewed_cases(self):
        cases=json.loads((Path(__file__).parent/'fixtures/us_privileges.json').read_text())
        self.assertEqual((Path(__file__).parents[1]/'android/app/src/test/resources/us_privileges.json').read_bytes(),(Path(__file__).parent/'fixtures/us_privileges.json').read_bytes())
        for cls,mode,f,region,expected in cases:
            with self.subTest(cls=cls,mode=mode,f=f,region=region):self.assertEqual(eligibility(f,mode,cls,region),expected)

    def test_reviewed_fcc_boundaries_and_mode_restrictions(self):
        cases=[
            ('General','SSB','14225','eligible'),('General','SSB','14224.9999','outside'),
            ('Advanced','SSB','14175','eligible'),('Advanced','SSB','14174.9999','outside'),
            ('Extra','SSB','14150','eligible'),('Extra','SSB','14149.9999','outside'),
            ('General','SSB','3800','eligible'),('Advanced','SSB','3700','eligible'),('Extra','SSB','3600','eligible'),
            ('General','CW','14200','outside'),('Extra','CW','14200','eligible'),
            ('General','FT8','14074','eligible'),('General','FT8','14225','outside'),
            ('General','SSB','10130','outside'),('General','CW','10130','eligible'),
            ('Technician','CW','7025','eligible'),('Technician','CW','7024.9999','outside'),
            ('Technician','FT8','7074','outside'),('Novice','SSB','7120','outside'),
            ('Technician','FT8','28074','eligible'),('Technician','SSB','28300','eligible'),
            ('Technician','AM','28300','outside'),('Novice','CW','28500','outside'),
            ('Technician','FM','146520','eligible'),('Novice','FM','146520','outside'),
            ('Technician','SSB','50050','outside'),('Technician','CW','50050','eligible'),
            ('Novice','FM','223500','eligible'),('General','FT8','221000','outside'),
            ('Novice','FM','1271000','eligible'),('Novice','FM','1295000','outside'),
            ('General','SSB','5330.5','eligible'),('General','CW','5330.5','outside'),
            ('General','CW','5332','eligible'),('General','SSB','5332','outside'),
            ('General','FT8','5357','eligible'),('General','SSB','5366.5','outside'),
            ('Technician','CW','5357','outside'),('General','Unknown','14225','unknown'),
        ]
        for cls,mode,f,expected in cases:
            with self.subTest(cls=cls,mode=mode,f=f):self.assertEqual(eligibility(f,mode,cls),expected)

    def test_itu_regions_are_fcc_locations_not_foreign_license_rules(self):
        self.assertEqual(eligibility('1900','CW','General','US Region 1'),'outside')
        self.assertEqual(eligibility('1900','CW','General','US Region 3'),'eligible')
        self.assertEqual(eligibility('3950','SSB','General','US Region 3'),'outside')
        self.assertEqual(eligibility('145500','FM','General','US Region 1'),'eligible')
        self.assertEqual(eligibility('223500','FM','General','US Region 3'),'outside')

    def test_license_unknown_does_not_override_known_outside(self):
        now=datetime.now(UTC)
        spot=parse_line(f'DX de WB4IUY: 14225 KF4DBX POTA {now:%H%M}Z','test',now)
        settings=Settings(license_class='General',filter_bands='20m',filter_activities='POTA',filter_modes='SSB,Unknown')
        self.assertFalse(matches(spot,settings))
        self.assertTrue(matches(spot,replace(settings,license_unknown=True)))
        self.assertFalse(matches(replace(spot,frequency_khz=Decimal('14190')),replace(settings,license_unknown=True)))
        self.assertTrue(matches(replace(spot,mode='SSB'),settings))

    def test_feed_location_and_known_station_filters_are_separate(self):
        now=datetime.now(UTC)
        raw=[dict(dx_call='JA1ABC',spotter='WB4IUY',frequency_khz='14225',time=now.isoformat(),mode='SSB',comment='POTA',dx_country='JP',dx_continent='AS',spotter_country='US',spotter_continent='NA',spotter_region='NC')]
        spot=parse_json_feed(json.dumps(raw).encode(),'test',now)[0]
        s=Settings(filter_spotter_countries='US',filter_dx_countries='JP',filter_spotter_regions='NC,SC',filter_activities='POTA',filter_modes='SSB',filter_bands='20m,40m')
        self.assertTrue(matches(spot,s))
        self.assertFalse(matches(spot,replace(s,filter_dx_countries='US')))
        self.assertFalse(matches(spot,replace(s,filter_spotter_countries='CA',geography_unknown=True)))
        missing=replace(spot,spotter_country='',spotter_continent='',spotter_region='')
        self.assertEqual(rejection(missing,s),'Location unknown')
        self.assertTrue(matches(missing,replace(s,location_overrides='WB4IUY=US,NA,NC')))
        self.assertTrue(matches(missing,replace(s,geography_unknown=True)))
        self.assertFalse(matches(missing,s)) # A US-looking callsign is not a location.

    def test_transfer_presets_and_legacy_defaults(self):
        s=Settings(license_class='General',filter_bands='20m',spacing_seconds=0,location_overrides='WB4IUY=US,NA,NC',listening_presets='{"POTA 20":{"filter_bands":"20m","filter_activities":"POTA"}}')
        profiles=[dict(name='Home',connection={key:getattr(s,key) for key in transfer.SOURCE_FIELDS})]
        data=transfer.document(profiles,s)
        self.assertEqual(transfer.decode(transfer.encode(data)),data)
        old=dict(data,version=1,filters={})
        self.assertEqual(transfer.decode(transfer.encode(old))['filters'],{})
        for values in ({'listening_presets':'{"bad":{"serial_port":"COM8"}}'},{'license_class':'Invented'},{'filter_spotter_continents':'XX'},{'location_overrides':'WB4IUY=US,NA,NC,EXTRA'}):
            with self.assertRaises(ValueError):replace(s,**values).validate()


class VoiceTests(unittest.TestCase):
    def test_pause_markers_are_silence_not_words_or_ssml(self):
        self.assertEqual(voice_plan('QST from WB4IUY [pause 2s] Visit JCARA.club'),[('QST from WB4IUY',2000),('Visit JCARA.club',0)])
        self.assertEqual(voice_plan('[pause] Hello [pause 500ms] again'),[('',1000),('Hello',500),('again',0)])
        with self.assertRaises(ValueError):voice_plan('Hello [pause 20s] again')
        with self.assertRaises(ValueError):voice_plan('[pause]')
        with patch('dxtalker.speech.WindowsSpeech') as provider:
            SpeechService().render_configured('Hello <test> [pause] again',Settings(speech_provider='Windows'),threading.Event())
            ssml=provider.return_value.render.call_args[0][0]
            self.assertIn('&lt;test&gt;',ssml);self.assertIn('1000ms',ssml);self.assertNotIn('[pause]',ssml)

    def test_long_online_pause_is_local_and_compatible_with_existing_gateway(self):
        with patch('dxtalker.cloud_speech.SharedSpeech') as cls:
            cls.return_value.render_plan.return_value=Clip(b'\0\0'*2205)
            clip=SpeechService().render_configured('[pause] Hello [pause 5s] again',Settings(speech_provider='ElevenLabs'),threading.Event())
            self.assertAlmostEqual(clip.duration,6.2)
            self.assertEqual([c.args[0] for c in cls.return_value.render_plan.call_args_list],[[('Hello',0)],[('again',0)]])

    def test_one_windows_process_handles_multiple_requests_and_closes(self):
        processes=[]
        class Process:
            def __init__(this,*args,**kwargs):
                this.requests=[];this.lines=queue.Queue();this.done=False
                this.stdin=SimpleNamespace(write=this.write,flush=lambda:None,close=lambda:None)
                this.stdout=this;processes.append(this)
            def write(this,line):
                value=json.loads(line);this.requests.append(value)
                with wave.open(value['output'],'wb') as wav:
                    wav.setparams((1,2,22050,0,'NONE','not compressed'));wav.writeframes(b'\0\0'*100)
                this.lines.put(json.dumps(dict(ok=True,voice=value['voice'] or 'Resolved default'))+'\n')
            def __iter__(this):return this
            def __next__(this):
                value=this.lines.get()
                if value is None:raise StopIteration
                return value
            def close(this):pass
            def poll(this):return 0 if this.done else None
            def terminate(this):this.done=True;this.lines.put(None)
            def wait(this,timeout):return 0
        with patch('dxtalker.audio.sys.platform','win32'),patch.dict('os.environ',SystemRoot='C:/Windows'),patch('dxtalker.audio.subprocess.CREATE_NO_WINDOW',0,create=True),patch('dxtalker.audio.subprocess.Popen',Process):
            voice=WindowsSpeech()
            voice.render('First','Specific',0,threading.Event())
            voice.render('Second','',1,threading.Event(),gender='Female')
            self.assertEqual(len(processes),1)
            self.assertEqual(voice.last_voice,'Resolved default')
            self.assertEqual(processes[0].requests[1]['voice'],'')
            voice.close();self.assertTrue(processes[0].done)


class ReceiveHealthTests(unittest.TestCase):
    def test_no_measurement_is_distinct_from_quiet_and_overflow_resets_delay(self):
        tick=[0];m=ReceiveMonitor(clock=lambda:tick[0]);m.stream=SimpleNamespace(active=True);m._started_at=0
        self.assertIsNone(m.snapshot()[1]);tick[0]=2
        self.assertEqual(m.snapshot()[0],'fault');self.assertEqual(m.fault_code,'no_samples')
        m.fault_code=None;m.feed(array('h',[0]*100).tobytes());tick[0]=9;m.feed(array('h',[0]*100).tobytes());self.assertTrue(m.ready())
        status=SimpleNamespace(input_overflow=True)
        m._callback(array('h',[0]*100).tobytes(),100,None,status)
        self.assertFalse(m.ready());self.assertFalse(m.fault)
        tick[0]=16;m.feed(array('h',[0]*100).tobytes());self.assertTrue(m.ready())


class AssistantEngineTests(unittest.TestCase):
    setUp=_EngineTests.setUp
    tearDown=_EngineTests.tearDown
    spot=_EngineTests.spot
    def test_ptt_test_uses_coordinator_and_stop_releases_without_speech_or_audio(self):
        self.engine.test_ptt(replace(self.settings,ptt_method='RTS',serial_port='COM8',cw_text=''))
        wait_for(lambda:bool(self.ptts) and True in self.ptts[0].calls)
        self.engine.stop();wait_for(lambda:not self.engine.busy)
        self.assertEqual(self.ptts[0].calls,["open",True,False,"close"])
        self.assertFalse(self.engine.enabled);self.assertFalse(self.audio.played);self.assertFalse(self.speech.texts)

    def test_ptt_pulse_releases_automatically_without_resolving_audio(self):
        from unittest.mock import Mock
        self.audio.resolve=Mock(side_effect=AssertionError('PTT test must not open audio'))
        self.engine.test_ptt(replace(self.settings,ptt_method='DTR',serial_port='COM8',radio_device='',cw_text=''))
        wait_for(lambda:bool(self.ptts) and self.ptts[0].calls[-1]=='close',timeout=4)
        self.assertEqual(self.ptts[0].calls,['open',True,False,'close'])
        self.assertFalse(self.engine.enabled)
        self.audio.resolve.assert_not_called()

    def test_independent_ids_keep_separate_deadlines_and_never_overlap(self):
        tick=[100.0];self.engine.clock=lambda:tick[0]
        self.engine.configure(replace(self.settings,id_mode='Independent',id_minutes=10,voice_id_minutes=30))
        self.engine.enable();wait_for(lambda:len(self.audio.played)==2 and not self.engine.busy)
        self.assertEqual(self.engine.next_id,700);self.assertEqual(self.engine.next_voice_id,1900)
        tick[0]=700;self.engine.wake.set();wait_for(lambda:len(self.audio.played)==3 and not self.engine.busy)
        self.assertEqual(len(self.speech.texts),1);self.assertEqual(self.engine.next_voice_id,1900)
        self.assertTrue(all(p.calls==['open',True,False,'close'] for p in self.ptts))

    def test_voice_preparation_does_not_overrun_cw_or_generate_twice(self):
        from unittest.mock import Mock
        tick=[100.0];self.engine.clock=lambda:tick[0]
        self.engine.configure(replace(self.settings,id_mode='Independent',id_minutes=1))
        self.engine._voice=Mock(return_value=Clip(b'\0\0'*22050*10))
        with self.engine.lock:
            self.engine.enable();self.engine.next_id=105
        wait_for(lambda:len(self.audio.played)==2 and not self.engine.busy)
        self.engine._voice.assert_called_once()
        self.assertLess(self.audio.played[0][0].duration,1)
        self.assertEqual(self.audio.played[1][0].duration,10)
        self.assertIsNone(self.engine.pending_voice_clip)

    def test_live_policy_edit_and_catchup_preserve_output_and_source(self):
        self.engine.listen_locally()
        with self.engine.lock:
            self.engine.next_spot=time.monotonic()+60
            self.assertTrue(self.engine.offer(self.spot()))
            self.engine.update_listening(replace(self.settings,filter_bands='20m'))
            self.assertEqual(len(self.engine.items),0);self.assertTrue(self.engine.local_enabled)
            self.assertFalse(self.engine.offer(self.spot()))
        self.engine.catch_up();self.assertTrue(self.engine.local_enabled);self.assertFalse(self.ptts)


class SubmissionTests(unittest.TestCase):
    def test_frequency_conversion_and_command_injection_rejection(self):
        self.assertEqual(command('wb4iuy','14.225','MHz','POTA US-0001'),'DX 14225 WB4IUY POTA US-0001')
        for args in [('WB4IUY','nan','kHz',''),('WB4IUY','14000','kHz','hello\nBYE'),('WB4IUY','14000','kHz','hi; BYE'),('BAD','14000','kHz','')]:
            with self.assertRaises(ValueError):command(*args)

    def test_submission_requires_current_authenticated_session_and_rate_limit(self):
        from dxtalker.source import SourceClient
        client=SourceClient(Settings(login='WB4IUY'),lambda *e:None)
        text=command('WB4IUY','14225')
        with self.assertRaises(ValueError):client.submit_spot(text)
        client.signed_in.set();client.connected.set();client.submit_spot(text)
        self.assertEqual(client.commands.get_nowait().command,text)
        with self.assertRaises(ValueError):client.submit_spot(text)
        client.stop()
        with self.assertRaises(ValueError):client.submit_spot(text)

del _EngineTests
