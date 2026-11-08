param([ValidateSet('x64','x86')][string]$Architecture = 'x64')
$ErrorActionPreference = 'Stop'
Set-Location (Resolve-Path (Join-Path $PSScriptRoot '../..'))
$bits = if ($Architecture -eq 'x86') { '32' } else { '64' }
$folder = "DXTalkerXP-${bits}bit"
$installDir = Join-Path $env:LOCALAPPDATA "Programs\$folder"
$settingsDir = Join-Path $env:LOCALAPPDATA 'DXTalker'
$desktop = Join-Path ([Environment]::GetFolderPath('Desktop')) "DX Talker XP ($bits bit).lnk"
$startMenu = Join-Path ([Environment]::GetFolderPath('Programs')) "DX Talker XP ($bits bit)\DX Talker XP ($bits bit).lnk"
# Refuse to touch an existing operator installation.
if ((Test-Path $installDir) -or (Test-Path $settingsDir) -or (Test-Path $desktop) -or (Test-Path (Split-Path $startMenu))) {
    throw 'Installer checks require a clean disposable Windows account'
}
function Run-Checked($file, $arguments) {
    $process = Start-Process -FilePath $file -ArgumentList $arguments -PassThru
    if (-not $process.WaitForExit(120000)) { $process.Kill(); throw "Timed out: $file" }
    if ($process.ExitCode -ne 0) { throw "Failed with exit code $($process.ExitCode): $file" }
}
$setup = Join-Path $PWD "dist\DXTalker-Setup-Windows-XP-${bits}bit.exe"
$reportPath = Join-Path $PWD "xp-$Architecture-installer-smoke.json"
$report = [ordered]@{ ok = $false; windows = [Environment]::OSVersion.VersionString }
try {
    Run-Checked $setup @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-', '/TASKS=desktopicon')
    foreach ($path in @("$installDir\DXTalkerXP.exe", "$installDir\runtime\python34.dll", "$installDir\runtime\msvcr100.dll", "$installDir\dxtalker\app.py", $desktop, $startMenu)) {
        if (-not (Test-Path $path)) { throw "Missing installation item: $path" }
    }
    $shell = New-Object -ComObject WScript.Shell
    foreach ($path in @($desktop, $startMenu)) {
        if ($shell.CreateShortcut($path).TargetPath -ne "$installDir\DXTalkerXP.exe") { throw "Wrong shortcut target: $path" }
    }
    foreach ($unwanted in @('tests', 'scripts', 'launcher.obj', 'launcher.rc', 'installer.iss')) {
        if (Test-Path (Join-Path $installDir $unwanted)) { throw "Installer included build/test content: $unwanted" }
    }
    $report.install = $true
    $appReport = Join-Path $PWD "xp-$Architecture-installed-smoke.json"
    Run-Checked "$installDir\DXTalkerXP.exe" @('--self-test', ('"' + $appReport + '"'))
    if (-not (Get-Content $appReport -Raw | ConvertFrom-Json).ok) { throw 'Installed application check failed' }
    $report.launch = $true
    $marker = Join-Path $settingsDir 'installer-check.txt'
    New-Item -ItemType Directory -Path $settingsDir -Force | Out-Null
    Set-Content $marker 'preserve'
    # A user renamed shortcut must suppress creation even if the task is forced.
    $renamedDesktop = Join-Path (Split-Path $desktop) "My DX Talker XP $bits.lnk"
    Move-Item $desktop $renamedDesktop
    Run-Checked $setup @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-', '/TASKS=desktopicon')
    if ((Get-Content $marker -Raw).Trim() -ne 'preserve') { throw 'Upgrade changed user data' }
    if (Test-Path $desktop) { throw 'Upgrade created a duplicate desktop shortcut' }
    if (-not (Test-Path $renamedDesktop)) { throw 'Upgrade removed the existing shortcut' }
    if ($shell.CreateShortcut($renamedDesktop).TargetPath -ne "$installDir\DXTalkerXP.exe") { throw 'Upgrade changed the shortcut target' }
    Move-Item $renamedDesktop $desktop
    $report.shortcut_preserved = $true
    $report.reinstall = $true
    Run-Checked "$installDir\DXTalkerXP.exe" @('--self-test', ('"' + $appReport + '"'))
    if (-not (Get-Content $appReport -Raw | ConvertFrom-Json).ok) { throw 'Upgraded application check failed' }
    Run-Checked "$installDir\unins000.exe" @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART')
    for ($attempt = 0; $attempt -lt 50 -and (Test-Path "$installDir\unins000.exe"); $attempt++) {
        Start-Sleep -Milliseconds 200
    }
    foreach ($path in @("$installDir\DXTalkerXP.exe", $desktop, $startMenu)) {
        if (Test-Path $path) { throw "Uninstall left installed item: $path" }
    }
    if ((Get-Content $marker -Raw).Trim() -ne 'preserve') { throw 'Uninstall changed user data' }
    $report.uninstall = $true
    $report.ok = $true
} finally {
    $report | ConvertTo-Json | Set-Content $reportPath
}
