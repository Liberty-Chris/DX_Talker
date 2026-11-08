"""Apply reviewed archived release prose without changing tags or downloads."""
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
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
    body = release.get('body', '')
    start, end = '<!-- dxtalker-downloads:start -->', '<!-- dxtalker-downloads:end -->'
    if body.count(start) != body.count(end) or body.count(start) > 1:
        raise ValueError('Incomplete managed download section. Existing release text was preserved.')
    if start in body:
        first, last = body.index(start), body.index(end) + len(end)
        if last < first: raise ValueError('Invalid managed download section')
        notes = notes.rstrip() + '\n\n' + body[first:last]
    if body.strip() == notes:
        return False
    # Preserve the managed table without writing generated content into the
    # canonical archive. Other release properties and asset labels stay intact.
    with tempfile.TemporaryDirectory(prefix='dxtalker-release-notes-') as folder:
        prepared = path
        if start in body:
            prepared = Path(folder)/'notes.md'
            prepared.write_text(notes + '\n', encoding='utf-8')
        response = run(['gh', 'release', 'edit', tag, '--repo', repository,
                        '--notes-file', str(prepared)], capture_output=True, text=True, check=False)
    if response.returncode:
        raise ValueError('Release notes edit failed. Check the release before retrying.')
    return True


if __name__ == '__main__':
    try:
        if sys.argv[1:] not in ([], ['--check']):
            raise ValueError('Expected no arguments or --check')
        repository = os.environ.get('GITHUB_REPOSITORY', '')
        published = None
        if not sys.argv[1:]:
            response = subprocess.run(['gh', 'release', 'list', '--repo', repository, '--limit', '1000', '--json', 'tagName'], capture_output=True, text=True, check=True)
            entries = json.loads(response.stdout)
            if not isinstance(entries, list) or any(not isinstance(item, dict) or not isinstance(item.get('tagName'), str) for item in entries):
                raise ValueError('Could not verify published release versions')
            published = {item['tagName'] for item in entries}
        for path in sorted((ROOT / 'docs/releases').glob('v*.md')):
            if sys.argv[1:] == ['--check']:
                read_notes(path.stem)
                print(path.stem + ': archived version checked')
                continue
            if path.stem not in published:
                print(path.stem + ': archived source version is not published')
                continue
            changed = sync_notes(path.stem, repository)
            print(path.stem + (': release text corrected' if changed else ': release text already aligned'))
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
