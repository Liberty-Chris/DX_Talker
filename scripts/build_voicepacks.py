"""Generate reusable voice packs from local Piper models, loading each speaker once."""
import argparse, hashlib, json, os, sys, wave
from pathlib import Path
os.environ['ORT_DISABLE_TELEMETRY']='1'
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from dxtalker.models import PHONETIC, DIGITS
from dxtalker.audio import wav_clip, Clip
from array import array
from dxtalker.speech import normalize_clip
from dxtalker.voicepacks import LETTERS

def trim(clip):
    values=array('h');values.frombytes(clip.pcm)
    if sys.byteorder!='little':values.byteswap()
    audible=[i for i,value in enumerate(values) if abs(value)>100]
    if not audible:raise ValueError('A generated clip was silent')
    padding=round(22050*.025)
    values=values[max(0,audible[0]-padding):min(len(values),audible[-1]+padding+1)]
    fade=min(110,len(values)//2)
    for i in range(fade):
        values[i]=round(values[i]*i/fade);values[-1-i]=round(values[-1-i]*i/fade)
    if sys.byteorder!='little':values.byteswap()
    return Clip(values.tobytes())

def build(model,destination,label,license_path,extra='',speaker=None):
    from piper import PiperVoice, SynthesisConfig
    if not Path(license_path).is_file(): raise ValueError('Supply the model license/model card for this voice')
    voice=PiperVoice.load(str(model))
    vocabulary={v.lower():v for v in PHONETIC.values()}
    vocabulary.update({v:v for v in DIGITS.values()})
    vocabulary.update({v:v for v in 'new on at frequency callsign this is stroke dash point kilohertz megahertz'.split()})
    vocabulary['dx']='D X'
    vocabulary.update({'letter:'+k:v for k,v in LETTERS.items()})
    for phrase in ['New DX','New DX on',extra]:
        if phrase.strip():vocabulary['phrase:'+phrase.strip().lower()]=phrase.strip()
    destination=Path(destination)
    if (destination/'voice.json').exists():raise ValueError('Choose a new pack folder; an installed pack is never overwritten')
    destination.mkdir(parents=True,exist_ok=True)
    clips={}
    for key,text in vocabulary.items():
        name=hashlib.sha256(key.encode()).hexdigest()[:24]+'.wav'
        path=destination/name
        with wave.open(str(path),'wb') as output:voice.synthesize_wav(text,output,syn_config=SynthesisConfig(speaker_id=speaker))
        clip=trim(normalize_clip(wav_clip(path)))
        with wave.open(str(path),'wb') as output:
            output.setparams((1,2,22050,0,'NONE','not compressed'));output.writeframes(clip.pcm)
        clips[key]=dict(file=name,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    (destination/'LICENSE.txt').write_text(Path(license_path).read_text())
    manifest=dict(schema='dxtalker-voice',version=1,label=label,model=Path(model).name,model_sha256=hashlib.sha256(Path(model).read_bytes()).hexdigest(),speaker=speaker,clips=clips)
    (destination/'voice.json').write_text(json.dumps(manifest,indent=2))
    return len(clips)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--model');group.add_argument('--models-dir',help='Build every local model/speaker with a matching .MODEL_CARD file')
    parser.add_argument('--output',required=True)
    parser.add_argument('--license',help='Reviewed model card/license for one model')
    parser.add_argument('--label');parser.add_argument('--intro',default='');parser.add_argument('--speaker',type=int)
    args=parser.parse_args()
    if args.model:
        if not args.license or not args.label:parser.error('--model requires --license and --label')
        print('Generated clips:',build(args.model,args.output,args.label,args.license,args.intro,args.speaker))
    else:
        models=sorted(Path(args.models_dir).glob('*.onnx'))
        if not models:parser.error('No local ONNX models found')
        for model in models:
            license_path=model.with_suffix('.MODEL_CARD')
            if not license_path.is_file():raise ValueError('Review and provide '+str(license_path)+' before batch generation')
            config=json.loads(Path(str(model)+'.json').read_text())
            speakers=config.get('speaker_id_map') or {model.stem:None}
            for label,speaker in speakers.items():
                identity=model.stem+('-'+str(speaker) if speaker is not None else '')
                print(identity,build(model,Path(args.output)/identity,str(label),license_path,args.intro,speaker))
if __name__=='__main__':main()
