$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path dist/DXTalker/DXTalker.exe)) { throw 'Build the portable application first' }
$compiler = Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'
if (-not (Test-Path $compiler)) { throw 'Install Inno Setup 6 before building the installer' }
& $compiler scripts/installer.iss
if ($LASTEXITCODE -ne 0) { throw 'Installer compilation failed' }
