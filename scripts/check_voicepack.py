"""Assemble a downloadable example without opening an audio device or PTT."""
import sys,threading,wave,json
from pathlib import Path
from datetime import datetime
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from dxtalker.models import Settings,UTC,parse_line
from dxtalker.voicepacks import VoicePack
from dxtalker.speech import spot_plan

def check(folder):
    root=Path(folder);pack=VoicePack(root)
    for key in pack.data['clips']:pack.clip(key)
    now=datetime.now(UTC);spot=parse_line(f'DX de N0CALL: 14025.5 WB4IUY/P {now:%H%M}Z','synthetic',now)
    settings=Settings(speech_provider='Recorded')
    clip=pack.render(spot_plan(spot,settings),settings,threading.Event())
    with wave.open(str(root/'example.wav'),'wb') as output:
        output.setparams((1,2,clip.rate,0,'NONE','not compressed'));output.writeframes(clip.pcm)
    print(json.dumps(dict(clips=len(pack.data['clips']),example_seconds=round(clip.duration,2),radio_opened=False)))
if __name__=='__main__':check(sys.argv[1])
