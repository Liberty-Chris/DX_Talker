"""Shared pilot speech gateway. The ElevenLabs account key never reaches the app."""
import json
from pathlib import Path
import sys
import threading
import time
from urllib import request, error
from urllib.parse import urlsplit

from . import __version__
from .audio import Cancelled, Clip
from .updates import update_ssl_context

MAX_AUDIO = 22050*2*120


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('The shared speech service redirected a request. Contact the pilot administrator.')


def configuration(path=None):
    root=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent.parent))
    path=Path(path) if path else root/'assets/services/speech.json'
    if not path.is_file() or path.stat().st_size>8192:
        raise ValueError('Shared ElevenLabs speech is not configured in this build. Contact the pilot administrator.')
    try:
        data=json.loads(path.read_text(encoding='utf-8-sig'))
        if set(data)!={'schema','version','url','pilot_token'} or data['schema']!='dxtalker-speech-service' or type(data['version']) is not int or data['version']!=1:raise ValueError()
        url=urlsplit(data['url'])
        token=data['pilot_token']
        if url.scheme!='https' or not url.hostname or url.username or url.password or url.query or url.fragment:raise ValueError()
        if not isinstance(token,str) or not token.startswith('dxp_') or not 36<=len(token)<=256 or any(not(c.isascii() and (c.isalnum() or c in '-_')) for c in token):raise ValueError()
        return data
    except (TypeError,KeyError,ValueError):
        raise ValueError('Shared ElevenLabs speech is not configured in this build. Contact the pilot administrator.') from None


class SharedSpeech:
    def __init__(self, config=None, opener=None):
        self.config=config or configuration()
        # Revalidate injected configuration through the same field rules without persisting it.
        url=urlsplit(self.config.get('url',''))
        if url.scheme!='https' or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError('The shared speech address must use HTTPS without credentials or a query')
        self.opener=opener

    def _request(self, cancel, payload=None):
        if cancel.is_set():raise Cancelled()
        req=request.Request(self.config['url'],data=json.dumps(payload).encode() if payload is not None else None,
                            headers={'User-Agent':'DXTalker/'+__version__,'X-DXTalker-Pilot':self.config['pilot_token'],'Content-Type':'application/json',
                                     'Accept':'application/octet-stream' if payload is not None else 'application/json'})
        limit=MAX_AUDIO if payload is not None else 65536
        try:
            opener=self.opener or request.build_opener(NoRedirect(),request.HTTPSHandler(context=update_ssl_context())).open
            with opener(req,timeout=10) as response:
                if payload is not None and hasattr(response,'headers') and response.headers.get_content_type()!='application/octet-stream':
                    raise ValueError('The shared speech service returned an unsupported audio response')
                result=bytearray();deadline=time.monotonic()+30
                while True:
                    if cancel.is_set():raise Cancelled()
                    if time.monotonic()>deadline:raise TimeoutError()
                    chunk=response.read(16384)
                    if not chunk:break
                    result.extend(chunk)
                    if len(result)>limit:raise ValueError('The shared speech response exceeded its size limit')
                if cancel.is_set():raise Cancelled()
                return bytes(result)
        except error.HTTPError as exc:
            voice_denied=False
            if exc.code==403 and payload is not None:
                try:
                    detail=json.loads(exc.read(1024))
                    voice_denied=isinstance(detail,dict) and detail.get('error') in ('voice_unavailable','model_changed')
                except (ValueError,TypeError,AttributeError,OSError):
                    pass
            messages={401:'Shared speech access has expired. Contact the pilot administrator for an updated build.',
                      403:('This ElevenLabs voice or model is no longer enabled for the pilot. Refresh the voice list.' if voice_denied else
                           'The speech website blocked access (HTTP 403). Contact the pilot administrator to check website security filtering.'),
                      429:'Shared speech is busy or has reached its testing limit. Try later or choose system or Recorded speech.',
                      503:'Shared speech has not been configured or is temporarily unavailable. Contact the pilot administrator.'}
            raise ValueError(messages.get(exc.code,'The shared speech service could not generate audio. Try later or choose system or Recorded speech.')) from None
        except (error.URLError,OSError,TimeoutError):
            raise ValueError('Shared speech could not be reached securely or timed out. Check your connection or choose system or Recorded speech.') from None

    def catalog(self,cancel):
        raw=self._request(cancel)
        try:
            data=json.loads(raw)
            if set(data)!={'schema','version','model_id','voices'} or data['schema']!='dxtalker-speech-catalog' or type(data['version']) is not int or data['version']!=1:raise ValueError()
            from .elevenlabs import ElevenLabs
            if not isinstance(data['voices'],list) or not 1<=len(data['voices'])<=100:raise ValueError()
            for item in data['voices']:
                if set(item)!={'id','name'} or not isinstance(item['name'],str) or not 1<=len(item['name'])<=100 or any(ord(c)<32 for c in item['name']):raise ValueError()
                ElevenLabs.identifiers(item['id'],data['model_id'])
            return data
        except (TypeError,KeyError,ValueError):
            # Preserve useful fixed transport errors; JSON/schema faults reveal no response values.
            raise ValueError('The shared voice list is unavailable. Check service setup or contact the pilot administrator.') from None

    def voices(self,cancel):
        data=self.catalog(cancel)
        return {item['name']+' ('+item['id']+')':item['id'] for item in data['voices']}

    def render_plan(self,plan,voice_id,cancel,expected_model=""):
        raw=self._request(cancel,{'schema':'dxtalker-speech-request','version':1,'voice_id':voice_id,'model_id':expected_model,
                                  'plan':[[text,pause] for text,pause in plan]})
        if not raw or len(raw)%2:raise ValueError('The shared speech service returned invalid PCM audio')
        return Clip(raw)

    def render(self,text,voice_id,model_id,cancel):
        # The server owns model selection. model_id is retained by the pack builder for provenance.
        return self.render_plan([(text,0)],voice_id,cancel,expected_model=model_id)
