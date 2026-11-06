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


## 0.2.0a3 speech and operation controls

Announcements now speak intro, frequency with units and phonetic callsign. A saved kHz/MHz choice is shared by Speech and Live spots. Decimal conversion affects display and speech only. Canonical received data, history and filters remain in kHz. Speech controls use compact groups with only the chosen provider visible.

Connection controls now share one action per page: Connect, Connecting or Reconnecting, Connected and a Disconnect action on hover or keyboard focus. Transport connectivity is separate from login status and validated spots. Local listening has a matching toggle. Starting and stopping listening uses applied settings and does not reconnect the source or apply pending edits.

A test reproduced a missed login prompt when a banner followed it in the same socket read. The adapter now processes lines and partial prompts after removing terminal formatting and NUL padding. Socket cleanup occurs before retry backoff and handles cancellation while connecting. This finding does not establish the cause of Dad's reported server trouble.

The published 0.2.0a2 release has a valid installer and checksum asset. The same public GitHub request succeeds from this environment. Dad's generic update error is not enough to determine his machine's failure category. The new status distinguishes DNS, TLS verification, timeout, HTTP and public API rate limits and explains Pilot versus Stable selection.

Verification: 84 tests pass under the local virtual display, including ten desktop integration tests. Documentation, help manifest and version alignment checks pass. Visual review covers the compact live page and speech groups. Windows package, native speech and installer verification will run on the feature branch. Physical radio acceptance and Dad's final installed upgrade remain open.


## 0.2.0a4 Announcements layout

The Announcements page groups frequency limits, timing and repeats, and RF supervision. Numeric fields use compact widths with units and range hints. Filter values remain in kHz. Settings, validation and announcement behavior are unchanged.

All 84 existing tests pass under the local virtual display without skips. Documentation links, version alignment and diff whitespace checks pass. Visual review covers 1160 by 830 and 900 by 600; the smaller window scrolls while the save action remains available. Windows workflow verification is pending for the PR.


## Windows update certificate and desktop shortcut followup

The reported screenshot establishes a certificate verification failure, not its underlying cause. Update HTTPS requests now use truststore 0.10.5 on Windows with an explicit native SSL context. Certificate and hostname checks remain enabled; HTTPS redirects and installer checksum verification remain enforced. Source and packaged smoke checks construct the context to detect missing runtime dependencies. Unit coverage checks context requirements, Windows selection and propagation of verification failures without an insecure retry.

The installer detects desktop shortcuts by their target path in the user and shared desktop folders. An existing shortcut suppresses both the optional task and new icon creation, including a renamed shortcut. It does not delete existing duplicates or unrelated links. Windows installer verification renames the initial shortcut, forces the desktop task during reinstall and checks that no duplicate is created. Native Windows and installer execution remain CI checks; Dad's successful installed update remains an acceptance check.

Verification: all 87 tests passed locally under the virtual display without skips. Documentation, version alignment and diff whitespace checks passed. Native Windows packaging and installer checks are pending CI.


## 0.2.0a5. Compact IDs and RF output toggle

IDs now groups CW, voice and schedule settings into compact sections with short numeric inputs and adjacent previews. Inactive speech or recorded voice fields are hidden without clearing them. RF uses the shared state control with an accent enabled state and a red Disable RF action on hover or keyboard focus. Disabling stops queued and active RF without touching the connected feed or live rows.

Enable uses applied settings and no longer requires source readiness, supervision acknowledgement or shared device confirmation. Radio and ID configuration validation, serialization, startup disabled state, source loss shutdown, cancellation, faults and watchdog limits remain. Initial, scheduled and requested IDs can operate without a source. The legacy acknowledgement value remains loadable but is no longer an operational control.

All 92 tests pass locally under a virtual display without skips. Coverage includes offline RF identification with fake audio and PTT, cancellation and invalid configuration rejection, inactive voice fields, toggle preservation of pending settings and cluster state, theme and keyboard focus states, stop/fault state reset, stopping feedback and no automatic reenable after source loss and reconnect. Visual review covers speech and WAV IDs at 1160 by 830 and the compact layout at 900 by 600. Documentation links, version alignment and whitespace checks pass. Windows packaging, speech and installer checks await the feature branch workflow. Physical radio acceptance remains open.


## 0.2.0a6. Announcement format editor

Announcements now has presets, include switches and Up/Down controls for Intro, Callsign and Frequency, with optional units attached to frequency. Intro accepts short custom text. A live sentence example follows edits; Listen to example uses an immutable settings snapshot through the existing output coordinator without applying pending source edits. Settings persistence preserves the former format for existing installations. IDs remain outside this format.

All 99 tests pass locally under a virtual display without skips. The format matrix covers all six section permutations, all seven nonempty inclusion combinations, both unit systems, spoken units on/off and character pauses on/off. Other checks cover custom intro SSML escaping, shared provider plans, legacy settings defaults, persistence, invalid/empty formats, UI reorder and inclusion behavior, output stop on edits and preview settings isolation without PTT. Visual review covers the normal and compact window sizes and a callsign first MHz example without spoken units. Documentation, version alignment and whitespace checks pass. Windows workflow verification is pending. No physical RF was used for these checks.


## 0.2.0a7. Profiles and compact Source/Audio controls

Profile management now distinguishes Save new profile, Save changes and confirmed Delete profile. Both selectors and the saved count update together. Profile save/load ignores unrelated pending radio edits. New and deletion clear the previous session display and credential. The fixed count cap is removed from saving and loading while stable IDs, case insensitive unique names, atomic writes and optional Windows protected credentials remain. The credential label and explanation describe a password or token rather than a secret key.

Source groups profiles, connection details, manual commands and console into compact sections and hides inactive TCP/HTTPS controls. Audio / PTT groups outputs, PTT, timing and levels and hides serial controls in VOX mode while retaining their values. Routing and transmission behavior are unchanged.

All 104 tests pass locally under a virtual display without skips. A 205 profile regression covers saving, reopening, editing, deleting and rejecting an update to a removed ID. Desktop checks cover independent creation, rename, deletion cancellation, selector synchronization, unfinished radio edits, source/PTT field visibility and session clearing. Visual checks cover TCP/HTTPS and VOX/serial layouts at 1160 by 830 and both tabs at 900 by 600. Documentation links, version alignment and whitespace checks pass. Native Windows package and installer verification remain pending CI. Physical radio acceptance remains open.

A failed saved credential unlock still loads the connection details for editing or deletion, clears the session secret and explains reentry. Loading alone does not erase the saved credential. Deletion confirmation names the saved record explicitly. The regression covers these behaviors.


## 0.2.0a8. Pilot operations and transfer

Implemented in source: listening arms before source readiness and preserves that intent before explicit Connect starts its worker; RF remains source-independent. Added private rotating diagnostics, safe exception stacks, UI delay sampling, supported native crash dumps and manual ZIP export. No automatic upload exists. Stable local diagnostics default off and installer creation is gated by owner-approved terms/privacy hashes.

Transfer version 1 supports selected-profile QR and full collection files with filters, excluding credentials and query-bearing feed URLs. Android validates before reviewed import, preserves existing entries, protects credentials with Keystore, applies spot/age/duplicate/frequency/spacing policy and phonetic decimal speech, queues before TTS readiness and bounds backlog. Network worker generations isolate stopped sessions. A curated directory contract and empty bundled list await Dad's entries; retired entries cannot be added and profiles are not auto-deleted.

Windows CI is expanded to x64/x86 installers and portable artifacts with matching updater selection and isolated install identities. The experimental Python 3.4/SAPI XP source kit is listening-only and has no current XP runtime acceptance; a full modern XP port remains unimplemented. Radio setup recipes are included in Help.

The recorded voice provider uses checksummed mono PCM assets with no model inference during playback. A local real LJ Speech high model generated 77 assets, about 1.77 MB before silence trimming. A sample announcement assembled in about 2 ms. This measures preparation, not audio endpoint latency or subjective voice quality. Batch generation supports local models/speakers with corresponding model cards. The generated artifact is included in CI rather than committing binaries.

Local verification so far: 112 tests pass under a Linux dummy X display with no skips. Tests cover first-packet listening, safe diagnostics and stalled-UI evidence, profile transfer round trips/field rejection/zip-bomb limits and recorded clip checksums. XP kit parser and Python 3.4 syntax checks pass on modern Python, which does not establish XP execution. Native Android tests/build and Windows x86/x64 smoke/install checks are pending the branch workflow. Physical phone camera/background behavior, actual 32 bit Windows, XP machines and radio acceptance remain open.
