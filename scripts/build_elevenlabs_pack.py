"""Generate an offline voice pack using your own ElevenLabs account credits."""
import argparse
import getpass
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from dxtalker.elevenlabs import ElevenLabs, build_pack

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--voice-id',required=True)
    parser.add_argument('--model-id',default='eleven_multilingual_v2')
    parser.add_argument('--label',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--intro',default='')
    args=parser.parse_args()
    # Never accept credentials in command line arguments or write them into packs.
    key=os.environ.get('ELEVENLABS_API_KEY') or getpass.getpass('ElevenLabs API key: ')
    try:
        path=build_pack(ElevenLabs(key),args.output,args.label,args.voice_id,args.model_id,args.intro,
                        progress=lambda done,total:print(f'{done}/{total} clips complete'))
        print('Recorded voice ready:',path)
    except KeyboardInterrupt:
        raise SystemExit('Stopped. Completed clips are retained for resuming with the same settings.')
