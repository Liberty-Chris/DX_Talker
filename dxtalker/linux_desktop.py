"""Ubuntu desktop integration. No shell commands, audio or radio ownership."""
from pathlib import Path
import re
import shutil
import subprocess
import uuid

PREFIX = 'secret-service:'

def _secret(arguments, value=None):
    executable = shutil.which('secret-tool')
    if not executable: raise ValueError('Install libsecret-tools and unlock your desktop keyring, or leave Remember unchecked.')
    try:
        result = subprocess.run([executable] + arguments, input=value, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        raise ValueError('The desktop keyring did not respond. Unlock it or leave Remember unchecked.') from None
    if result.returncode: raise ValueError('The desktop keyring is unavailable or locked. Unlock it or leave Remember unchecked.')
    return result.stdout.rstrip('\n')

def protect_secret(value, decrypt=False):
    if decrypt:
        if not re.fullmatch(r'secret-service:[0-9a-f]{32}', value):
            raise ValueError('This saved secret belongs to another platform. Reenter it for this desktop keyring.')
        result = _secret(['lookup', 'application', 'dxtalker', 'id', value[len(PREFIX):]])
        if not result: raise ValueError('The saved secret was not found in the desktop keyring. Reenter it.')
        return result
    identifier = uuid.uuid4().hex
    _secret(['store', '--label=DX Talker cluster credential', 'application', 'dxtalker', 'id', identifier], value)
    return PREFIX + identifier

def forget_secret(reference):
    if re.fullmatch(r'secret-service:[0-9a-f]{32}', reference or ''):
        try: _secret(['clear', 'application', 'dxtalker', 'id', reference[len(PREFIX):]])
        except ValueError: pass

def install_update(path):
    path = Path(path).resolve()
    if path.suffix != '.deb' or not path.is_file(): raise ValueError('Download a verified Ubuntu package first.')
    if not Path('/usr/bin/pkexec').is_file() or not Path('/usr/bin/apt-get').is_file():
        raise ValueError('Use Ubuntu Software or apt to install the downloaded package.')
    from .models import settings_path
    with (settings_path().parent/'update-install.log').open('ab') as log:
        return subprocess.Popen(['/usr/bin/pkexec', '/usr/bin/apt-get', '-y', 'install', str(path)],
                                stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
