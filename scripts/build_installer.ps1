param([ValidateSet('x64','x86')][string]$Architecture = 'x64')
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path dist/DXTalker/DXTalker.exe)) { throw 'Build the portable application first' }
$compiler = Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'
if (-not (Test-Path $compiler)) { throw 'Install Inno Setup 6 before building the installer' }
$version = python -c "from dxtalker import __version__; print(__version__)"
$stableFlags = @()
if ($version -notmatch '(a|b|rc)\d+$') {
    python scripts/check_stable_release.py
    if ($LASTEXITCODE -ne 0) { throw 'Stable terms/privacy approval is required' }
    $stableFlags += '/DStableRelease=1'
}
& $compiler "/DAppArch=$Architecture" @stableFlags scripts/installer.iss
if ($LASTEXITCODE -ne 0) { throw 'Installer compilation failed' }
