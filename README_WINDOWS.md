# DX Talker Windows pilot

Version 0.1.0a2. Initial target: Windows 11 x64.

## Portable application

The Windows pilot workflow builds DXTalker-Windows-x64.zip after core tests and Windows smoke checks pass. Open the successful run under the repository's Actions tab and download the DXTalker-Windows-x64 artifact. Extract the downloaded ZIP. Keep DXTalker.exe alongside its _internal folder and launch the EXE. Python is bundled in that package.

The package is unsigned and is a pilot build. It is not yet a published installer or a hardware certified release. The Windows verification reports in the same run identify which automated checks actually passed.

## Appearance

The DXt mark appears in the header and Windows application icon. Choose Light or Dark from Appearance in the header. The choice takes effect immediately and is remembered separately from radio settings. Changing appearance does not apply pending radio edits or change RF state. New installations start in Dark mode.

## Run from source

Install Python 3.12 x64 from python.org with Tcl/Tk support. From a checkout of the working branch, run these commands in PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run_dxtalker.py
```

## First listening test

Open Audio and PTT and choose your speakers or headphones for Local preview output. Open Live spots, load sample spots, select one and choose Preview selected. Samples never enter the RF queue.

In Identification, enter your CW ID and voice ID, choose a Windows voice if desired and try both local previews. Voice IDs can also use a WAV recording. Use uncompressed PCM16 audio, mono or stereo, with a sample rate from 8 to 96 kHz. The Both ID policy requires a mono 22050 Hz WAV when using a recording.

## Receive a live cluster

Open Source. Choose TCP/Telnet, enter the hostname, port and login callsign and enter a session password only if the service requires one. W4MR's example address is w4mr.ddns.net with port 7373. Choose Connect using these settings.

Common callsign and password prompts are handled automatically. If your cluster needs another response or command, use the masked manual response field. Its content is never written to the activity journal. The connection becomes ready after the first valid DX spot arrives. W4MR's actual prompts still need testing.

For a compatible HTTPS feed, choose HTTPS JSON and enter a URL that follows the contract in docs/feed_contract.md. A bearer token is optional and is kept only for the current session.

## Prepare radio output

Choose the radio's exact audio device. Select VOX only for an interface or radio configured to key from audio. Otherwise choose serial RTS, DTR or RTS+DTR and the correct COM port and polarity. These methods require compatible wiring. CM108 HID interfaces such as RIM devices need a future HID adapter and are not controlled by the current serial PTT implementation.

Set lead time, tail time and the maximum transmit duration. Save and apply. Configure CW and voice text and the ID policy. In Announcements, acknowledge supervised operation on a clear or coordinated channel. Busy channel detection is not implemented.

Once a source is ready, Enable RF starts with an ID. New live spots are then eligible for announcement. Spots received before enabling are not replayed. Send ID now requests the configured ID policy immediately. STOP ALL OUTPUT cancels pending work and requests PTT release.

Use a local preview device separate from the radio path. With VOX, a preview routed to the radio can itself cause transmission even though the app never asserts PTT for preview.

## Settings and recovery

Settings live at %LOCALAPPDATA%\DXTalker\settings.json. Passwords, tokens, the channel acknowledgement and RF enable state are not saved. Restarting starts with RF disabled.

Changing a setting while RF is enabled disarms output. Save and apply the change before enabling again. If output is busy, stop it and wait for Idle before applying settings. Source loss, output faults and device refresh also disable RF. Reconnection does not reenable it.

The app refuses missing or ambiguous audio device names instead of switching devices. The first pilot does not provide automatic audio format conversion. Select a device supporting the recording's format or convert the recording.

## Developer checks and build

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/check_docs.py
.\.venv\Scripts\python.exe run_dxtalker.py --self-test source-smoke.json
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\Activate.ps1
.\scripts\build_windows.ps1
```

The self test generates speech to a temporary WAV and creates the UI, checks its settings and help and closes it. It does not play audio, open PTT or connect to a source. Windows workflow tests run on a hosted Windows runner, which is distinct from testing on Windows 11 with an actual radio interface.

## Still to verify

The remaining operator checks are a live W4MR sign in, speech pronunciation and playback on Windows 11, radio audio levels and PTT behavior on the chosen interface. Test stop, unplug and application exit with that interface before regular operation. An open serial port can briefly pulse on some USB drivers and software cannot guarantee release after process termination or hardware failure.
