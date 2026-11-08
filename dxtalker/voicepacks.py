"""Offline PCM voice packs. No model inference, network, fallback or executable code."""
import hashlib
from collections import OrderedDict
import json
from pathlib import Path
import re
import threading
from .audio import Clip, Cancelled, wav_clip

LETTERS = dict(zip('abcdefghijklmnopqrstuvwxyz', ['ay','bee','see','dee','ee','ef','gee','aitch','eye','jay','kay','el','em','en','oh','pee','cue','ar','ess','tee','you','vee','double you','ex','why','zee']))

def vocabulary(extra=''):
    from .models import PHONETIC, DIGITS
    words = {v.lower(): v for v in PHONETIC.values()}
    words.update({v: v for v in DIGITS.values()})
    words.update({v: v for v in 'new on at frequency callsign this is stroke dash point kilohertz megahertz'.split()})
    words['dx'] = 'D X'
    words.update({'letter:'+key: value for key, value in LETTERS.items()})
    for phrase in ['New DX', 'New DX on', extra]:
        if phrase.strip(): words['phrase:'+phrase.strip().lower()] = phrase.strip()
    return words


def trim_clip(clip):
    from array import array
    import sys
    values = array('h'); values.frombytes(clip.pcm)
    if sys.byteorder != 'little': values.byteswap()
    audible = [i for i, value in enumerate(values) if abs(value)>100]
    if not audible: raise ValueError('A generated clip was silent')
    padding = round(22050*.025)
    values = values[max(0,audible[0]-padding):min(len(values),audible[-1]+padding+1)]
    fade = min(110,len(values)//2)
    for i in range(fade):
        values[i] = round(values[i]*i/fade); values[-1-i] = round(values[-1-i]*i/fade)
    if sys.byteorder != 'little': values.byteswap()
    return Clip(values.tobytes())


def keys_for(text):
    words = re.findall(r"[A-Za-z0-9/\-]+", text)
    result=[]
    for word in words:
        if any(c.isdigit() for c in word) or word.isupper() and len(word)>1 and word!='DX':
            for char in word.lower():
                result.append('letter:'+char if char.isalpha() else {'/':'stroke','-':'dash'}.get(char, {'0':'zero','1':'one','2':'two','3':'three','4':'four','5':'five','6':'six','7':'seven','8':'eight','9':'nine'}.get(char,char)))
        elif len(word)==1 and word.isalpha() and word.isupper(): result.append('letter:'+word.lower())
        else: result.append(word.lower())
    return result

class VoicePack:
    def __init__(self, directory):
        self.directory=Path(directory)
        path=self.directory/'voice.json'
        if path.stat().st_size>131072: raise ValueError('Voice pack manifest is too large')
        self.data=json.loads(path.read_text())
        if self.data.get('schema')!='dxtalker-voice' or self.data.get('version')!=1 or not isinstance(self.data.get('clips'),dict):
            raise ValueError('Invalid recorded voice pack')
        self.label=str(self.data.get('label','Recorded voice'))[:100]
        self.cache=OrderedDict();self.cache_bytes=0

    def clip(self,key):
        if key in self.cache:
            self.cache.move_to_end(key);return self.cache[key]
        item=self.data['clips'].get(key)
        if not isinstance(item,dict): raise ValueError('Recorded voice lacks a required word. Regenerate the pack with your custom intro or use system speech.')
        name=item.get('file','')
        if not re.fullmatch(r'[a-f0-9]{24}\.wav',name):raise ValueError('Unsafe recorded clip filename')
        path=self.directory/name
        if path.is_symlink() or path.stat().st_size>22050*2*10+44:raise ValueError('Recorded clip is too large or linked')
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=item.get('sha256'):raise ValueError('Recorded clip checksum mismatch')
        clip=wav_clip(path)
        if clip.rate!=22050 or clip.channels!=1:raise ValueError('Recorded clips must be mono 22050 Hz PCM16')
        while self.cache and self.cache_bytes+len(clip.pcm)>16*1024*1024:
            _,old=self.cache.popitem(last=False);self.cache_bytes-=len(old.pcm)
        self.cache[key]=clip;self.cache_bytes+=len(clip.pcm)
        return clip

    def render(self,plan,settings,cancel):
        chunks=[];size=0
        for text,pause in plan:
            if not text.strip():
                silence=b'\0\0'*round(22050*pause/1000);chunks.append(silence);size+=len(silence)
                if size>22050*2*120:raise ValueError('Recorded speech exceeds two minutes')
                continue
            phrase='phrase:'+text.strip().lower()
            keys=[phrase] if phrase in self.data['clips'] else keys_for(text)
            if not keys: raise ValueError('Recorded voice text contains no supported words')
            for index,key in enumerate(keys):
                if cancel.is_set():raise Cancelled()
                pcm=self.clip(key).pcm
                gap=pause if index==len(keys)-1 else 35
                silence=b'\0\0'*round(22050*gap/1000)
                size+=len(pcm)+len(silence)
                if size>22050*2*120:raise ValueError('Recorded speech exceeds two minutes')
                chunks.extend([pcm,silence])
        return Clip(b''.join(chunks))

def installed(root):
    if not root or not Path(root).is_dir():return {}
    result={}
    for path in sorted(Path(root).glob('*/voice.json')):
        try:
            pack=VoicePack(path.parent)
            result[path.parent.name]=pack.label
        except (OSError,ValueError,KeyError):pass
    return result
