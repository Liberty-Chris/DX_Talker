"""Inject only service URL and revocable pilot access into a trusted build, never a provider key."""
import json
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from dxtalker.cloud_speech import configuration

if __name__=='__main__':
    value=os.environ.get('DXTALKER_SPEECH_CONFIG','').strip()
    path=Path(__file__).resolve().parent.parent/'assets/services/speech.json'
    if value:
        try:
            # Schema rejects an accidentally pasted owner config containing api_key.
            json.loads(value)
            path.write_text(value,encoding='utf-8')
            configuration(path)
        except Exception:
            path.write_text('{"schema":"dxtalker-speech-service","version":1,"url":"","pilot_token":""}\n')
            raise SystemExit('Invalid shared speech build configuration. Supply client.json, never the private API configuration.') from None
        print('Shared pilot speech endpoint configured. No ElevenLabs account key is bundled.')
    else:
        print('No shared speech build configuration supplied. Online ElevenLabs will show setup guidance.')
