"""Optional real neural voice smoke test. Produces PCM without opening audio/PTT."""
import argparse
from dataclasses import replace
from datetime import datetime
import json
from pathlib import Path
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dxtalker.models import Settings, UTC, parse_line
from dxtalker.speech import SpeechService

parser = argparse.ArgumentParser()
parser.add_argument('--executable', required=True)
parser.add_argument('--model', required=True)
parser.add_argument('--report', default='piper-smoke.json')
args = parser.parse_args()
report = {'ok': False, 'audio_played': False, 'ptt_opened': False}
start = time.monotonic()
try:
    settings = replace(Settings(), speech_provider='Piper', piper_executable=args.executable,
                       piper_model=args.model, character_pause_ms=0, group_pause_ms=450)
    now = datetime.now(UTC)
    spot = parse_line(f'DX de N0CALL: 14025.5 WB4IUY/P {now:%H%M}Z', 'test', now)
    clip = SpeechService().render_spot(spot, settings, threading.Event())
    assert clip.rate == 22050 and clip.channels == 1 and 1 < clip.duration < 120
    report.update(ok=True, speech_seconds=clip.duration, elapsed_seconds=round(time.monotonic() - start, 2),
                  provider='Piper', model=Path(args.model).name, platform=sys.platform)
except Exception as error:
    report['error'] = type(error).__name__ + ': ' + str(error)
Path(args.report).write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
raise SystemExit(0 if report['ok'] else 1)
