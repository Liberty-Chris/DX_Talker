"""Keep release tag, application, installer, EXE metadata and bundled manual aligned."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from dxtalker import __version__
from dxtalker.updates import version_key

version_key(__version__)
if len(sys.argv) > 1 and sys.argv[1] != "v" + __version__:
    raise SystemExit("Release tag must match dxtalker.__version__")
installer = (ROOT / "scripts/installer.iss").read_text()
metadata = (ROOT / "scripts/windows_version.txt").read_text()
manual = json.loads((ROOT / "docs/help/manifest.json").read_text())
assert f'#define AppVersion "{__version__}"' in installer
assert f"StringStruct('FileVersion', '{__version__}')" in metadata
assert f"StringStruct('ProductVersion', '{__version__}')" in metadata
assert manual["version"] == __version__
android=(ROOT / "android/app/build.gradle.kts").read_text()
assert f'versionName = "{__version__}"' in android
notes = (ROOT / "docs/releases/current.md").read_text().strip()
assert notes.startswith(f"DX Talker {__version__} "), "Release notes must describe the application version"
print("Release version aligned:", __version__)
