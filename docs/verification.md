# Windows pilot verification

Updated October 31, 2026.

## Local automated checks

The implementation was checked with Python 3.12.14 on Linux using python -m unittest discover -s tests -v, python -m compileall -q dxtalker run_dxtalker.py and python scripts/check_docs.py.

All 43 core tests pass locally. Tests use a local socket server for the cluster sign in and inject fake hardware for RF coordination. They cover split prompts and Telnet negotiation, secret redaction, HTTPS parsing and redirect policy, settings validation and persistence, midnight timestamps, malformed input, Morse timing, WAV formats, explicit device resolution, serial polarity, queue capacity, ID priority, cancellation and release after output faults.

The suite does not connect to W4MR or perform any RF operation. Windows APIs cannot be verified by those portable tests alone.

## Windows workflow

The workflow tests core behavior on Linux and Windows. On its hosted Windows runner it installs the pinned direct dependencies, generates speech with System.Speech, creates the actual UI, verifies all settings are represented, loads sample spots and saves a temporary profile. It then packages a portable Windows application and repeats the same check against the EXE. The initial Windows build passed both source and packaged smoke checks, including actual Windows speech generation. Updated commits repeat those checks. Reports and synthetic UI screenshots are published as Windows-verification artifacts.

A successful workflow is evidence for that commit and runner only. It is not a Windows 11 physical radio test. The workflow does not play audio, open serial ports, connect to a cluster or assert PTT.

## Operator acceptance still open

Listen to sample callsigns and frequencies and both IDs on Windows 11. Test live cluster sign in and reconnect. Verify the selected radio output, audio format, gain and serial or VOX behavior. Confirm PTT polarity and lead and tail timing using the actual interface.

Verify stop, timeout, device removal, source loss and application exit. Record radio model, interface, driver, Windows version, observed behavior and any hardware timeout. Busy channel detection, CM108 HID and CAT support are outside this pilot.

## Preservation

The original archive blob remains unchanged. Documentation is checked for local link targets, stable unique help IDs and packaged topic targets. Historical executable files are not run or included in the modern portable package.
