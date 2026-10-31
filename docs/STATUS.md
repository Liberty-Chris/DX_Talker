# Project status

Updated October 31, 2026.

## Where things stand

The first Windows pilot is implemented in source. It has live spots, configurable cluster and HTTPS connections, local previews, speech, CW and voice IDs, saved settings and configurable radio output. The portable Windows build is produced by the Windows pilot workflow after its checks pass. See [Windows setup](../README_WINDOWS.md).

The original archive remains preserved. Its editable Visual Basic source is still unavailable.

## Implemented in the pilot

TCP/Telnet connections support incremental lines, option negotiation, common callsign and password prompts, manual responses and reconnect. HTTPS polling accepts the documented JSON contract with an optional session token. The W4MR example itself has not yet been tested live.

Audio output is selected explicitly for preview and radio use. Windows System.Speech renders audio before PTT is asserted. CW is audio Morse. Voice IDs use generated speech or validated PCM16 WAV audio. ID policy can be CW, Voice, Alternate or Both.

PTT adapters support serial RTS, DTR, both lines and an explicit VOX mode. CM108 HID, CAT and vendor specific controls remain open. Compatibility with physical interfaces is not yet claimed.

One coordinator prioritizes IDs, serializes audio, limits the queue, expires spots and attempts PTT release on completion, cancellation and errors. Source loss disables RF. Startup, settings changes and recovery require deliberate RF enable. Passwords and tokens are not saved or journaled.

The desktop now includes the DXt header, light and dark appearance, a matching Windows icon and EXE version information. Appearance is saved independently of radio settings.

## Verification

The core test suite runs locally without Windows hardware. It covers parsing, incremental framing, a local TCP sign in, HTTPS contract handling, settings, Morse timing, serial line policies and simulated transmission failures. [Verification notes](verification.md) record the commands and scope.

The Windows workflow adds source and packaged UI checks and real Windows speech generation to a temporary WAV. It publishes reports with each successful build. These checks do not play sound, open a serial port or transmit.

Windows 11 listening tests, a live W4MR session and physical radio interface tests remain necessary. The pilot is not a completed production release.

## What's next

Download a successful workflow build and test sample spot and ID previews on Windows 11. Then connect a live cluster. Choose the first physical interface once Dad is ready and verify audio, PTT, stop, disconnect and exit behavior with that hardware.

The standalone WiFi device and ASL3, Allmon and Asterisk integration follow the Windows work. Rights remain reserved under the existing project and archive notices.
