# Windows pilot verification

Updated October 31, 2026.

## Local automated checks

The implementation was checked with Python 3.12.14 on Linux using python -m unittest discover -s tests -v, python -m compileall -q dxtalker run_dxtalker.py and python scripts/check_docs.py.

All 45 core tests pass locally, including appearance persistence and damaged preference recovery. Tests use a local socket server for the cluster sign in and inject fake hardware for RF coordination. They cover split prompts and Telnet negotiation, secret redaction, HTTPS parsing and redirect policy, settings validation and persistence, midnight timestamps, malformed input, Morse timing, WAV formats, explicit device resolution, serial polarity, queue capacity, ID priority, cancellation and release after output faults.

The suite does not connect to W4MR or perform any RF operation. Windows APIs cannot be verified by those portable tests alone.

## Windows workflow

The workflow tests core behavior on Linux and Windows. On its hosted Windows runner it installs the pinned direct dependencies, generates speech with System.Speech, creates the actual UI, verifies all settings are represented, loads sample spots and saves a temporary profile. It then packages a portable Windows application and repeats the same check against the EXE. The initial Windows build passed both source and packaged smoke checks, including actual Windows speech generation. Updated commits repeat those checks. Reports and synthetic UI screenshots are published as Windows-verification artifacts.

A successful workflow is evidence for that commit and runner only. It is not a Windows 11 physical radio test. The workflow does not play audio, open serial ports, connect to a cluster or assert PTT.

## Operator acceptance still open

Listen to sample callsigns and frequencies and both IDs on Windows 11. Test live cluster sign in and reconnect. Verify the selected radio output, audio format, gain and serial or VOX behavior. Confirm PTT polarity and lead and tail timing using the actual interface.

Verify stop, timeout, device removal, source loss and application exit. Record radio model, interface, driver, Windows version, observed behavior and any hardware timeout. Busy channel detection, CM108 HID and CAT support are outside this pilot.

## Preservation

The original archive blob remains unchanged. Documentation is checked for local link targets, stable unique help IDs and packaged topic targets. Historical executable files are not run or included in the modern portable package.


## DXt branding pass

Local checks cover both themes, all six tabs and visible stop, appearance and save controls at 1160 by 830 and 900 by 600 using Tk on a Linux virtual display. Device discovery and voice enumeration are stubbed for this visual check. Sample spots are synthetic. Appearance persistence is checked separately from the radio profile and theme switching is checked without calls to engine stop, configure or enable.

The Windows source and packaged smoke checks now exercise both themes and publish an additional light theme screenshot. A successful run is still required for the updated commit; local checks do not establish Windows shell icon behavior or physical radio compatibility.

## November 4, 2026 operator batch

Local virtual display run: `python -m unittest discover -s tests -q` passed 70 tests without skips. New coverage includes profile persistence and renaming, legacy settings defaults, bounded JSONL rotation, exact SSML break placement, provider routing, a synthetic neural CLI fixture, live local listening without PTT, independent gains, console redaction, source generation isolation, view clearing and update channel ordering, checksum, truncation, cancellation and tampering.

Visual QA inspected the eight desktop tabs at 1160 by 830 and the live page at 900 by 600. The compact view retains the spot table by hiding the activity panel. The docs checker and version alignment checker pass. Windows native speech, DPAPI and packaged install tests still await the branch workflow. A real two release update and actual neural voice listening remain acceptance checks.


## November 5, 2026 source control followup

All 72 tests pass under the virtual display, including permanent command visibility, temporary password reveal and remasking on profile load, source relevant control states and session secret clearing on source type changes. Documentation and version alignment checks pass. Visual review covers the source page and compact live page.

A real Piper 1.8.0 render using en_US-lessac-medium on Linux produced 8.12 seconds of PCM in 5.01 seconds, with no audio endpoint or PTT opened. ORT_DISABLE_TELEMETRY=1 was applied before the subprocess started. Windows real model rendering is added to the workflow and remains pending for this commit.


## November 5, 2026 speech order and state controls

All 84 tests pass with the virtual display, including ten desktop integration tests. Coverage includes exact kHz/MHz conversion with fractional zeros, intro/frequency/callsign ordering, shared unit display, inactive provider sections, actual connection state and red disconnect hover, and a local listening toggle that never applies pending settings or replaces its source. The same source continues delivering rows after local audio stops.

A prompt plus banner in one network read failed before the connection patch and passes after it. ANSI and NUL padded login/password prompts are exercised at every single split point. Tests check socket release before retry and cancellation during connect. Update checks cover preview selection for an installed 0.2.0a1, Stable channel guidance, and redacted DNS, TLS, HTTP and rate limit explanations. The current GitHub API request returned HTTP 200 from this environment. That does not diagnose the separate Windows user's generic failure.

UI review covers Speech at 1160 by 830 and Live spots at 900 by 600. Documentation links and version alignment pass. Windows workflow results must be recorded separately after publication of the branch.


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
