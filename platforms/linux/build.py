"""Build a private-runtime Ubuntu amd64 deb. Run on Ubuntu 22.04."""
import argparse
from importlib import metadata
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]

def build():
    sys.path.insert(0, str(ROOT))
    from dxtalker import __version__
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:a|b|rc)\d+', __version__):
        raise ValueError('Ubuntu packaging currently targets pilot builds only')
    if sys.platform != 'linux' or os.uname().machine != 'x86_64': raise ValueError('Build on Ubuntu amd64')
    (ROOT/'assets/voices').mkdir(exist_ok=True)
    command = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir', '--name', 'DXTalker', '--collect-all', 'sounddevice', '--hidden-import', '_cffi_backend']
    for item in ['assets/brand', 'assets/catalog', 'assets/services', 'assets/voices', 'docs/help']:
        command += ['--add-data', item + ':' + item]
    command += ['--add-data', 'LICENSE:.', 'run_dxtalker.py']
    subprocess.run(command, cwd=ROOT, check=True)
    package = ROOT/'build/ubuntu-package'
    if package.exists(): shutil.rmtree(package)
    program = package/'opt/dxtalker'
    shutil.copytree(ROOT/'dist/DXTalker', program)
    notices = program/'licenses'; notices.mkdir()
    for name in ['sounddevice', 'pyserial', 'qrcode', 'pypng', 'cffi', 'pycparser']:
        distribution = metadata.distribution(name)
        for item in distribution.files or []:
            if 'licen' in item.name.lower() or item.name.lower() == 'copying':
                target = notices/name/item.name; target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(distribution.locate_file(item), target)
    # The runtime license must be supplied by the build's official CPython tree.
    python_license = ROOT/'platforms/linux/PYTHON-LICENSE.txt'
    if not python_license.is_file(): raise ValueError('Provide the official runtime license at build/PYTHON-LICENSE.txt')
    shutil.copy2(python_license, notices/'PYTHON-LICENSE.txt')
    control = package/'DEBIAN'; control.mkdir()
    (control/'control').write_text('Package: dxtalker\nVersion: '+__version__+'\nArchitecture: amd64\nMaintainer: DX Talker\nSection: hamradio\nPriority: optional\nDepends: libc6 (>= 2.35), libportaudio2, ca-certificates, espeak-ng, libsecret-tools, policykit-1, xdg-utils\nDescription: Spoken DX cluster assistant\n Profiles, local filters, speech, coordinated radio output and identification.\n')
    desktop = package/'usr/share/applications'; desktop.mkdir(parents=True)
    (desktop/'dxtalker.desktop').write_text('[Desktop Entry]\nType=Application\nName=DX Talker\nComment=Spoken DX cluster assistant\nExec=/opt/dxtalker/DXTalker\nIcon=dxtalker\nTerminal=false\nCategories=Network;HamRadio;\nStartupWMClass=DXTalker\n')
    icon = package/'usr/share/icons/hicolor/256x256/apps'; icon.mkdir(parents=True)
    shutil.copy2(ROOT/'assets/brand/icon.png', icon/'dxtalker.png')
    binary = package/'usr/bin'; binary.mkdir(parents=True)
    (binary/'dxtalker').symlink_to('/opt/dxtalker/DXTalker')
    output = ROOT/'dist/DXTalker-Ubuntu-amd64.deb'
    subprocess.run(['dpkg-deb', '--root-owner-group', '--build', str(package), str(output)], check=True)
    return output

if __name__ == '__main__': print(build())
