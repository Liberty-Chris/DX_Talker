"""Apply reviewed archived release prose without changing tags or downloads."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent


def read_notes(tag, root=ROOT):
    if not re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+(?:(?:a|b|rc)[0-9]+)?', tag):
        raise ValueError('Invalid release tag')
    path = root / 'docs/releases' / (tag + '.md')
    notes = path.read_text(encoding='utf-8').strip()
    if not notes.startswith(f'DX Talker {tag[1:]} '):
        raise ValueError('Archived notes must describe their own release version')
    return path, notes


def sync_notes(tag, repository, root=ROOT, run=subprocess.run):
    if not re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+(?:(?:a|b|rc)[0-9]+)?', tag):
        raise ValueError('Invalid release tag')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
        raise ValueError('Invalid release repository')
    path, notes = read_notes(tag, root)
    response = run(['gh', 'release', 'view', tag, '--repo', repository,
                    '--json', 'tagName,isDraft,body'], capture_output=True, text=True, check=False)
    if response.returncode:
        raise ValueError('Could not read the published release. No notes were changed.')
    try:
        release = json.loads(response.stdout)
    except (ValueError, TypeError):
        raise ValueError('Invalid release response. No notes were changed.') from None
    if not isinstance(release, dict) or release.get('tagName') != tag or release.get('isDraft') is not False:
        raise ValueError('Expected a published release with a matching tag')
    if release.get('body', '').strip() == notes:
        return False
    response = run(['gh', 'release', 'edit', tag, '--repo', repository,
                    '--notes-file', str(path)], capture_output=True, text=True, check=False)
    if response.returncode:
        raise ValueError('Release notes edit failed. Check the release before retrying.')
    return True


if __name__ == '__main__':
    try:
        if sys.argv[1:] not in ([], ['--check']):
            raise ValueError('Expected no arguments or --check')
        repository = os.environ.get('GITHUB_REPOSITORY', '')
        for path in sorted((ROOT / 'docs/releases').glob('v*.md')):
            if sys.argv[1:] == ['--check']:
                read_notes(path.stem)
                print(path.stem + ': archived version checked')
                continue
            changed = sync_notes(path.stem, repository)
            print(path.stem + (': release text corrected' if changed else ': release text already aligned'))
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
