"""Friendly download roles without renaming files required by installed updaters."""
import argparse
from pathlib import Path
from urllib.parse import urlsplit

REPOSITORY = 'Liberty-Chris/DX_Talker'
ROLES = {
    'DXTalker-Setup-Windows-x64.exe': (0, 'Windows 10 and 11', '64 bit installer. Recommended for most PCs'),
    'DXTalker-Setup-Windows-x86.exe': (1, 'Windows 10 and 11', '32 bit installer. Not for XP'),
    'DXTalker-Windows-x64.zip': (4, 'Windows 10 and 11', '64 bit portable ZIP. No installer'),
    'DXTalker-Windows-x86.zip': (5, 'Windows 10 and 11', '32 bit portable ZIP. Not for XP'),
    'DXTalker-Setup-Windows-XP-32bit.exe': (2, 'Windows XP SP3', '32 bit application installer. XP acceptance testing'),
    'DXTalker-Setup-Windows-XP-64bit.exe': (3, 'Windows XP x64 SP2', '64 bit application installer. XP acceptance testing'),
    'DXTalker-XP-source-test-kit.zip': (8, 'Developers only', 'Limited XP listener source. Not an installer or full application'),
    'DXTalker-VoicePack-LJ-high.zip': (6, 'Optional voice pack', 'Recorded English LJ voice. ZIP'),
    'SHA256SUMS.txt': (9, 'Download verification', 'SHA256 checksums'),
}
# Original modern releases were x64 only. Preserve their existing filenames.
ROLES['DXTalker-Setup-Windows.exe'] = ROLES['DXTalker-Setup-Windows-x64.exe']
ROLES['DXTalker-Windows.zip'] = ROLES['DXTalker-Windows-x64.zip']
START = '<!-- dxtalker-downloads:start -->'
END = '<!-- dxtalker-downloads:end -->'


def label(name):
    role = ROLES.get(name)
    return role[1] + '. ' + role[2] if role else None


def downloads(body, assets):
    if body.count(START) != body.count(END) or body.count(START) > 1:
        raise ValueError('Incomplete managed download section. Existing release text was preserved.')
    rows = []
    for asset in assets:
        role = ROLES.get(asset['name'])
        if role is None: continue
        url = asset['browser_download_url']
        parsed = urlsplit(url)
        if parsed.scheme != 'https' or parsed.netloc != 'github.com' or not parsed.path.startswith('/' + REPOSITORY + '/releases/download/') or parsed.query or parsed.fragment:
            raise ValueError('Unexpected release download address')
        rows.append((role[0], '| ' + role[1] + ' | [' + role[2] + '](' + url + ') |'))
    if not rows: return body
    block = START + '\n### Choose your download\n\n| System or purpose | Download |\n| :--- | :--- |\n' + '\n'.join(row for _, row in sorted(rows)) + '\n' + END
    if START in body:
        start, end = body.index(START), body.index(END) + len(END)
        if end < start: raise ValueError('Invalid managed download section')
        return body[:start] + block + body[end:]
    return body.rstrip() + '\n\n' + block + '\n'


def arguments(directory):
    result = []
    for path in sorted(Path(directory).iterdir()):
        if not path.is_file(): continue
        friendly = label(path.name)
        if friendly is None: raise ValueError('Add a clear download role before publishing: ' + path.name)
        result.append(str(path) + '#' + friendly)
    if not result: raise ValueError('No prepared release downloads')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('directory')
    options = parser.parse_args()
    print('\n'.join(arguments(options.directory)))
