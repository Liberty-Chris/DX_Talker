# Project status

Updated November 4, 2026.

## Where things stand

The first Windows pilot is implemented in source. It has live spots, configurable cluster and HTTPS connections, local previews, speech, CW and voice IDs, saved settings and configurable radio output. The portable Windows build is produced by the Windows pilot workflow after its checks pass. See [Windows setup](../README_WINDOWS.md).

The original archive remains preserved. Its editable Visual Basic source is still unavailable.

## Implemented in the pilot

TCP/Telnet connections support incremental lines, option negotiation, common callsign and password prompts, manual responses and reconnect. HTTPS polling accepts the documented JSON contract with an optional session token. The W4MR example itself has not yet been tested live.

Audio output is selected explicitly for preview and radio use. Windows System.Speech renders audio before PTT is asserted. CW is audio Morse. Voice IDs use generated speech or validated PCM16 WAV audio. ID policy can be CW, Voice, Alternate or Both.

PTT adapters support serial RTS, DTR, both lines and an explicit VOX mode. CM108 HID, CAT and vendor specific controls remain open. Compatibility with physical interfaces is not yet claimed.

One coordinator prioritizes IDs, serializes audio, limits the queue, expires spots and attempts PTT release on completion, cancellation and errors. Source loss disables RF. Startup, settings changes and recovery require deliberate RF enable. Passwords and tokens are never journaled. A source profile can optionally remember its secret using Windows account DPAPI protection. Ordinary settings exclude credentials.

The desktop now includes the DXt header, light and dark appearance, a matching Windows icon and EXE version information. Appearance is saved independently of radio settings.

The installer source adds account based installation, the DXt desktop shortcut, a Start menu entry and Windows removal support. Its minimum target is Windows 10 22H2 x64, also targeting Windows 11 x64. The workflow compiles setup and checks install, shortcuts, installed UI and speech, reinstall and removal on its hosted Windows runner. The [Windows verification run](https://github.com/Liberty-Chris/DX_Talker/actions/runs/41570491770) passed core tests and documentation checks on Windows and Linux, source and packaged UI and speech checks, installer compilation, installation, shortcut targets, installed launch, reinstallation and removal. The setup artifact is available in that run. Separate acceptance tests on Windows 10 and Windows 11 remain open.

Local application testing is reported to be working well. The exact Windows build and hardware coverage were not supplied with that report.

## Verification

The core test suite runs locally without Windows hardware. It covers parsing, incremental framing, a local TCP sign in, HTTPS contract handling, settings, Morse timing, serial line policies and simulated transmission failures. [Verification notes](verification.md) record the commands and scope.

The Windows workflow adds source and packaged UI checks and real Windows speech generation to a temporary WAV. It publishes reports with each successful build. These checks do not play sound, open a serial port or transmit.

Windows 11 listening tests, a live W4MR session and physical radio interface tests remain necessary. The pilot is not a completed production release.

## What's next

Download a successful workflow build and test sample spot and ID previews on Windows 11. Then connect a live cluster. Choose the first physical interface once Dad is ready and verify audio, PTT, stop, disconnect and exit behavior with that hardware.

The standalone WiFi device and ASL3, Allmon and Asterisk integration follow the Windows work. Rights remain reserved under the existing project and archive notices.

## 0.2.0a1 operator update batch

Implemented in source: named connection profiles, visible command controls on both source and live pages, a redacted session console, automatic source change clearing, configurable display retention and rotating structured history. History includes validated received spots, completed announcement routes and connection lifecycle, excluding raw text and credentials.

Speech has explicit character and group pauses, rate, installed voice selection and gender preference. Windows remains the default. An optional external Piper CLI produces neural speech before playback. Independent spot, CW ID, voice ID and local levels are applied by the shared coordinator. Live local listening never constructs serial PTT or schedules IDs. High contrast, larger text, shortcuts and saved supervision acknowledgement are implemented.

The updater discovers compatible public GitHub Releases by channel, shows notes, verifies downloads and opens setup only after output stops. Tagged release publication is gated by the Windows workflow. Source and packaged Windows smoke checks include SSML generation and DPAPI roundtrip with synthetic data. The first full two release operator upgrade test remains open. An existing installation without an updater needs one manual setup installation.

The cluster customization help topic is reserved for Dad’s guide. Mobile and older system work currently consists of portable core boundaries and documented platform contracts and acceptance gates. There are no new mobile, macOS, Linux or older Windows installers in this batch. Full screen reader acceptance, actual Piper model listening and physical radio checks remain open.

### Local verification for this batch

The portable suite passes 70 tests, including four desktop integration tests under a Linux virtual X display. Documentation links, ten help manifest topics and release version alignment pass. Visual review covered all eight pages at 1160 by 830 and Live spots at 900 by 600; the compact layout hides the in memory activity panel to preserve table space. The historical archive is unchanged.

Windows System.Speech SSML, DPAPI and packaged installer checks are defined in the workflow but have not run for this branch. No new Windows executable has been produced locally. The feature branch is authorized for publication and Windows workflow verification is pending.


## 0.2.0a2 connection controls and first update test

Commands remain visible on both pages. The dedicated source password field has a temporary eye control with Show and Hide text. Source type changes activate relevant controls and clear the session secret; profile changes conceal the field again. The duplicate lower Source connection buttons are removed.

The Windows workflow now includes real Piper rendering with a downloaded test model. An optional workflow input publishes the verified main version with its installer and checksums. It cannot publish from an ordinary PR run. Windows help includes a complete optional runtime and voice setup example.

Piper child processes set ORT_DISABLE_TELEMETRY=1 before startup. Model files are not included in the application package. The local real model render passed using en_US-lessac-medium, producing 8.12 seconds of PCM in 5.01 seconds on Linux without opening audio or PTT. All 72 tests pass with the virtual display, including six desktop integration tests. Windows verification for this followup is pending.

The first installed Windows update from 0.2.0a1 to 0.2.0a2 is an operator acceptance test after release publication. It has not been claimed as completed.
