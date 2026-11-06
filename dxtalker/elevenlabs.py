"""Explicit, resumable ElevenLabs generation. Playback always uses local Recorded packs."""
import hashlib
import json
import re
import threading
import time
from pathlib import Path
from urllib import request, error, parse
import wave

from .audio import Clip, Cancelled, wav_clip
from .updates import update_ssl_context
from .voicepacks import vocabulary, trim_clip


class CancelEither:
    """Generation stops on its own Cancel or application shutdown, even if Tk is gone."""
    def __init__(self, local, shutdown):
        self.local, self.shutdown = local, shutdown

    def is_set(self):
        return self.local.is_set() or self.shutdown.is_set()


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('ElevenLabs redirected the request. No API key was forwarded.')


class ElevenLabs:
    def __init__(self, api_key, opener=None):
        if not isinstance(api_key, str) or not api_key.strip() or len(api_key)>1024 or any(ord(c)<33 or ord(c)>126 for c in api_key):
            raise ValueError('Enter your ElevenLabs API key')
        self._key = api_key
        self._opener = opener

    def _request(self, path, cancel, data=None, limit=441000):
        if cancel.is_set(): raise Cancelled()
        body = json.dumps(data).encode() if data is not None else None
        req = request.Request('https://api.elevenlabs.io'+path, data=body,
                              headers={'xi-api-key': self._key, 'Content-Type':'application/json',
                                       'Accept':'audio/pcm' if data else 'application/json'})
        try:
            opener = self._opener or request.build_opener(NoRedirect(), request.HTTPSHandler(context=update_ssl_context())).open
            with opener(req, timeout=10) as response:
                if data is not None and hasattr(response, 'headers'):
                    content_type = response.headers.get('Content-Type', '').split(';')[0].lower()
                    if content_type not in ('audio/pcm', 'audio/raw', 'application/octet-stream'):
                        raise ValueError('ElevenLabs returned an unsupported audio response')
                result = bytearray()
                deadline = time.monotonic()+30
                while True:
                    if cancel.is_set(): raise Cancelled()
                    if time.monotonic()>deadline: raise TimeoutError()
                    chunk = response.read(16384)
                    if not chunk: break
                    result.extend(chunk)
                    if len(result)>limit: raise ValueError('ElevenLabs response exceeded the audio or voice list limit')
                if cancel.is_set(): raise Cancelled()
                return bytes(result)
        except error.HTTPError as exc:
            messages = {401:'ElevenLabs rejected the request. Check the API key, account credits and voice access.', 403:'ElevenLabs denied access. Check key permissions, the voice and your plan.',
                        402:'ElevenLabs credits or plan access are insufficient.', 429:'ElevenLabs rate or credit limit reached. Wait or check your account, then resume.'}
            raise ValueError(messages.get(exc.code, f'ElevenLabs returned HTTP {exc.code}. Check your account and resume later.')) from None
        except (error.URLError, OSError, TimeoutError):
            raise ValueError('ElevenLabs could not be reached securely or timed out. Check your connection, clock and HTTPS filtering, then resume.') from None

    @staticmethod
    def identifiers(voice_id, model_id):
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', voice_id) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', model_id):
            raise ValueError('Enter a valid ElevenLabs voice ID and model ID')

    def voices(self, cancel):
        # A bounded page; entering any voice ID is also supported for larger libraries.
        raw = self._request('/v2/voices?page_size=100', cancel, limit=2*1024*1024)
        try:
            items = json.loads(raw)['voices']
            # Page zero can include extra default voices beyond page_size.
            if not isinstance(items, list) or len(items)>1000: raise ValueError()
            return {str(item['name'])[:100]+' ('+item['voice_id']+')':item['voice_id'] for item in items[:100]
                    if re.fullmatch(r'[A-Za-z0-9_-]{1,128}', item['voice_id'])}
        except (KeyError, TypeError, ValueError):
            raise ValueError('ElevenLabs returned an invalid voice list') from None

    def render(self, text, voice_id, model_id, cancel):
        self.identifiers(voice_id, model_id)
        raw = self._request('/v1/text-to-speech/'+voice_id+'?output_format=pcm_22050', cancel,
                            {'text':text, 'model_id':model_id, 'seed':42})
        if not raw or len(raw)%2: raise ValueError('ElevenLabs returned invalid PCM audio')
        return trim_clip(Clip(raw))


def build_pack(client, destination, label, voice_id, model_id, intro='', cancel=None, progress=lambda done,total:None):
    """Keep verified completed clips on cancellation so resuming avoids regenerating them."""
    cancel = cancel or threading.Event()
    ElevenLabs.identifiers(voice_id, model_id)
    if not label.strip() or len(label)>100 or any(ord(c)<32 for c in label): raise ValueError('Enter a voice label of 1 to 100 characters')
    if len(intro)>80 or any(ord(c)<32 for c in intro): raise ValueError('Use an intro of up to 80 characters')
    words = vocabulary(intro)
    destination = Path(destination)
    partial = destination.with_name(destination.name+'.partial')
    if destination.exists(): raise ValueError('Choose a new pack name. Completed packs are never overwritten.')
    if partial.is_symlink(): raise ValueError('Choose a local pack folder rather than a linked partial folder')
    identity = dict(provider='ElevenLabs', voice_id=voice_id, model_id=model_id, label=label, vocabulary=words)
    partial.mkdir(parents=True, exist_ok=True)
    journal = partial/'generation.json'
    if journal.exists():
        saved = json.loads(journal.read_text())
        if saved.get('identity')!=identity: raise ValueError('This partial pack uses different voice settings. Restore them to resume or choose a new name.')
        clips = saved['clips']
    else:
        clips = {}
    def save():
        temp = journal.with_suffix('.tmp')
        temp.write_text(json.dumps(dict(identity=identity,clips=clips),indent=2))
        temp.replace(journal)
    save()
    progress(0,len(words))
    for done,(key,text) in enumerate(words.items(),1):
        if cancel.is_set(): raise Cancelled()
        name = hashlib.sha256(key.encode()).hexdigest()[:24]+'.wav'
        path = partial/name
        existing = clips.get(key)
        valid = False
        if existing and existing.get('file')==name and path.is_file() and not path.is_symlink() and path.stat().st_size<=441044:
            valid = hashlib.sha256(path.read_bytes()).hexdigest()==existing.get('sha256')
            if valid:
                clip = wav_clip(path)
                valid = clip.rate==22050 and clip.channels==1 and clip.duration<=10
        if not valid:
            if path.is_symlink(): raise ValueError('A partial clip is linked. Choose a fresh pack folder.')
            clip = client.render(text, voice_id, model_id, cancel)
            if cancel.is_set(): raise Cancelled()
            if clip.rate!=22050 or clip.channels!=1 or not 0<clip.duration<=10: raise ValueError('Generated clip has an unsupported format or duration')
            with wave.open(str(path),'wb') as output:
                output.setparams((1,2,22050,0,'NONE','not compressed'));output.writeframes(clip.pcm)
            clips[key] = dict(file=name,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            save()
        progress(done,len(words))
    if cancel.is_set(): raise Cancelled()
    manifest = dict(schema='dxtalker-voice',version=1,label=label,provider='ElevenLabs',voice_id=voice_id,model_id=model_id,clips=clips)
    (partial/'voice.json').write_text(json.dumps(manifest,indent=2))
    (partial/'PROVENANCE.txt').write_text('Generated using ElevenLabs. Voice ID: '+voice_id+'\nModel: '+model_id+'\nUse and redistribution depend on your ElevenLabs plan, voice permissions and applicable terms. This file grants no additional rights.\n')
    partial.rename(destination)
    return destination
