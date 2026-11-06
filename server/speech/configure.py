"""Owner setup for DreamHost. Prompts privately; never places the ElevenLabs key in web files."""
import argparse
import getpass
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import sys
from urllib.parse import urlsplit


def private_json(path,data):
    path=Path(path)
    fd=os.open(str(path)+'.tmp',os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    with os.fdopen(fd,'w') as stream:json.dump(data,stream,indent=2)
    os.chmod(str(path)+'.tmp',0o600)
    os.replace(str(path)+'.tmp',path)


def install(web_root,url,private,key,voices,model='eleven_multilingual_v2',daily_characters=10000,rotate=False):
    web_root=Path(web_root).resolve();private=Path(private).resolve()
    parsed=urlsplit(url)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or not parsed.path.endswith('/speech.php'):
        raise ValueError('Use the full HTTPS URL ending in /speech.php without a query or credentials')
    if private==web_root or web_root in private.parents or private in web_root.parents:
        raise ValueError('Choose a private folder outside the website and a separate public service folder')
    if not key or len(key)>1024 or any(ord(c)<33 or ord(c)>126 for c in key):raise ValueError('Enter a valid API key')
    if not 1<=len(voices)<=100 or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',model):raise ValueError('Configure 1 to 100 voices and a valid model ID')
    for voice in voices:
        if set(voice)!={'id','name'} or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',voice['id']) or not 1<=len(voice['name'])<=100 or any(ord(c)<32 for c in voice['name']):raise ValueError('Invalid voice name or ID')
    if not 1<=daily_characters<=1000000:raise ValueError('Choose a daily character limit from 1 to 1000000')
    if web_root.exists() and (web_root/'speech.php').exists() and 'DX Talker speech gateway' not in (web_root/'speech.php').read_text():
        raise ValueError('The public speech.php already exists and does not belong to this installer')
    private.mkdir(parents=True,exist_ok=True);os.chmod(private,0o700)
    existing={}
    config_path=private/'config.json'
    if config_path.exists():existing=json.loads(config_path.read_text())
    token='dxp_'+secrets.token_urlsafe(32) if rotate or not existing.get('pilot_token','').startswith('dxp_') else existing['pilot_token']
    config=dict(enabled=True,api_key=key,pilot_token=token,voices=voices,model_id=model,
                daily_characters=daily_characters,daily_requests=existing.get('daily_requests',2000),hourly_requests_per_ip=existing.get('hourly_requests_per_ip',300),
                cache_bytes=existing.get('cache_bytes',20*1024*1024),storage=str(private/'state'))
    private_json(config_path,config)
    source=Path(__file__).with_name('gateway.php')
    if source.resolve()!=(private/'gateway.php').resolve():shutil.copyfile(source,private/'gateway.php')
    os.chmod(private/'gateway.php',0o600)
    web_root.mkdir(parents=True,exist_ok=True)
    def quote(value):return "'"+str(value).replace('\\','\\\\').replace("'","\\'")+"'"
    public="<?php\n// DX Talker speech gateway. Provider credentials remain outside the website.\nini_set('display_errors','0');\nrequire "+quote(private/'gateway.php')+";\ndx_http_entry("+quote(config_path)+");\n"
    (web_root/'speech.php').write_text(public)
    private_json(private/'client.json',dict(schema='dxtalker-speech-service',version=1,url=url,pilot_token=token))
    return config_path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--web-root',required=True,help='The public folder where speech.php will be installed')
    parser.add_argument('--url',required=True,help='Full public HTTPS speech.php URL')
    parser.add_argument('--private',default=str(Path.home()/'dxtalker-private/speech'))
    parser.add_argument('--daily-characters',type=int)
    parser.add_argument('--rotate-pilot-token',action='store_true')
    args=parser.parse_args()
    if not sys.stdin.isatty():raise SystemExit("Run setup interactively in your SSH terminal so the API key can be entered privately.")
    existing_path=Path(args.private)/'config.json'
    existing=json.loads(existing_path.read_text()) if existing_path.exists() else {}
    key=getpass.getpass('ElevenLabs API key (hidden; blank keeps existing): ') or existing.get('api_key','')
    previous=existing.get('voices',[{}])[0]
    voice=input('Allowed voice ID'+(' ['+previous.get('id','')+']' if previous.get('id') else '')+': ').strip() or previous.get('id','')
    label=input('Voice name ['+previous.get('name','ElevenLabs pilot voice')+']: ').strip() or previous.get('name','ElevenLabs pilot voice')
    model=input('Model ID ['+existing.get('model_id','eleven_multilingual_v2')+']: ').strip() or existing.get('model_id','eleven_multilingual_v2')
    voices=[dict(id=voice,name=label)]+existing.get('voices',[])[1:]
    path=install(args.web_root,args.url,args.private,key,voices,model,args.daily_characters or existing.get('daily_characters',10000),args.rotate_pilot_token)
    print('Private API configuration:',path)
    print('Build configuration without the ElevenLabs key:',path.parent/'client.json')
    print('Copy the client.json contents into the GitHub Actions secret DXTALKER_SPEECH_CONFIG, then build the app.')
    print('Do not upload config.json or the private folder to the website or repository.')

if __name__=='__main__':main()
