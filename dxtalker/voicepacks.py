"""Offline PCM voice packs. No model inference, network, fallback or executable code."""
import hashlib
import json
from pathlib import Path
import re
import threading
from .audio import Clip, Cancelled, wav_clip

LETTERS = dict(zip('abcdefghijklmnopqrstuvwxyz', ['ay','bee','see','dee','ee','ef','gee','aitch','eye','jay','kay','el','em','en','oh','pee','cue','ar','ess','tee','you','vee','double you','ex','why','zee']))

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
        self.cache={}

    def clip(self,key):
        if key in self.cache:return self.cache[key]
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
        self.cache[key]=clip
        return clip

    def render(self,plan,settings,cancel):
        chunks=[];size=0
        for text,pause in plan:
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
