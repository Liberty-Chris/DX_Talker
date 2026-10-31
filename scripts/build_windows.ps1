$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
python -m PyInstaller --noconfirm --clean --onedir --windowed --name DXTalker --icon assets/brand/dxt.ico --version-file scripts/windows_version.txt --add-data 'assets/brand;assets/brand' --add-data 'docs/help;docs/help' --add-data 'LICENSE;.' --collect-all sounddevice --collect-all _sounddevice_data --hidden-import _cffi_backend run_dxtalker.py
if ($LASTEXITCODE -ne 0) { throw 'Windows packaging failed' }
Copy-Item README_WINDOWS.md dist/DXTalker/README_WINDOWS.md
Copy-Item LICENSE dist/DXTalker/LICENSE
Compress-Archive -Path dist/DXTalker -DestinationPath dist/DXTalker-Windows-x64.zip -Force
