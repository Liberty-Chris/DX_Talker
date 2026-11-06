"""Owner endpoint check. Catalog is not a paid generation; --preview explicitly requests audio."""
import argparse
from pathlib import Path
import sys
import threading
import wave
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from dxtalker.cloud_speech import SharedSpeech, configuration

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--client-config',required=True)
    parser.add_argument('--preview',help='Write a short generated PCM WAV here; consumes account allowance')
    args=parser.parse_args()
    try:
        service=SharedSpeech(configuration(args.client_config));cancel=threading.Event()
        catalog=service.catalog(cancel)
        print('Shared speech catalog is reachable over HTTPS. Voices:',len(catalog['voices']))
        if args.preview:
            clip=service.render_plan([('New DX on',450),('one four zero two five kilohertz',450),('Whiskey Bravo four India Uniform Yankee',0)],catalog['voices'][0]['id'],cancel)
            with wave.open(args.preview,'wb') as output:
                output.setparams((1,2,22050,0,'NONE','not compressed'));output.writeframes(clip.pcm)
            print('Preview WAV saved. No playback or PTT was opened. Seconds:',round(clip.duration,2))
    except Exception as exc:
        raise SystemExit(str(exc) if isinstance(exc,ValueError) else 'Service check failed. Review private server setup and logs.') from None
