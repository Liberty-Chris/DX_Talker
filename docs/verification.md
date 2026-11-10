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


## 0.2.0a8. Pilot operations and transfer

Implemented in source: listening arms before source readiness and preserves that intent before explicit Connect starts its worker; RF remains source-independent. Added private rotating diagnostics, safe exception stacks, UI delay sampling, supported native crash dumps and manual ZIP export. No automatic upload exists. Stable local diagnostics default off and installer creation is gated by owner-approved terms/privacy hashes.

Transfer version 1 supports selected-profile QR and full collection files with filters, excluding credentials and query-bearing feed URLs. Android validates before reviewed import, preserves existing entries, protects credentials with Keystore, applies spot/age/duplicate/frequency/spacing policy and phonetic decimal speech, queues before TTS readiness and bounds backlog. Network worker generations isolate stopped sessions. A curated directory contract and empty bundled list await Dad's entries; retired entries cannot be added and profiles are not auto-deleted.

Windows CI is expanded to x64/x86 installers and portable artifacts with matching updater selection and isolated install identities. The experimental Python 3.4/SAPI XP source kit is listening-only and has no current XP runtime acceptance; a full modern XP port remains unimplemented. Radio setup recipes are included in Help.

The recorded voice provider uses checksummed mono PCM assets with no model inference during playback. A local real LJ Speech high model generated 77 assets, about 1.77 MB before silence trimming. A sample announcement assembled in about 2 ms. This measures preparation, not audio endpoint latency or subjective voice quality. Batch generation supports local models/speakers with corresponding model cards. The generated artifact is included in CI rather than committing binaries.

Local verification so far: 112 tests pass under a Linux dummy X display with no skips. Tests cover first-packet listening, safe diagnostics and stalled-UI evidence, profile transfer round trips/field rejection/zip-bomb limits and recorded clip checksums. XP kit parser and Python 3.4 syntax checks pass on modern Python, which does not establish XP execution. Native Android tests/build and Windows x86/x64 smoke/install checks are pending the branch workflow. Physical phone camera/background behavior, actual 32 bit Windows, XP machines and radio acceptance remain open.


## November 7, 2026. Personal DX assistant

Local Linux verification passes 176 Python tests under a dummy X display with no skips. Checks include separate CW/voice deadlines, pause parsing and escaping, Windows process reuse through a synthetic child, PTT pulse/stop release without audio or cluster prerequisites, input overflow quiet restart, missing-frame explanations, retained hidden row bounds, local filter edits preserving the source and old/new transfer validation. The desktop live/filter/ID layouts were rendered and inspected locally.

Android testDebugUnitTest passes 20 tests and assembleDebug/assembleDebugAndroidTest succeed using SDK 35, Gradle 8.9 and JDK 21 locally. Tests include shared reviewed license boundaries, activity/band/mode/geography intersections, unknown policy, v3 presets, unsafe import rejection, spotting validation and retired directory entries. Kotlin tables are checked with python scripts/sync_privileges.py --check. Actual Windows reuse/SSML/packaged checks and emulator layout/navigation run in CI; physical radio, Windows audio drivers, phone accessibility/camera and live cluster acceptance remain distinct operator tests. No paid speech generation or live cluster spot was performed.


CI on ece8d7c336d160e2fb993d702e30bba56cf3cdbf passes the [Windows workflow](https://github.com/Liberty-Chris/DX_Talker/actions/runs/42439736674) including source, packaged and installed synthesis reuse on x86 and x64, installer/reinstall/removal checks and real local Piper rendering. Source/package/installed x64 reports identify Microsoft David Desktop and confirm the same speech process handled consecutive renders. The [Android workflow](https://github.com/Liberty-Chris/DX_Talker/actions/runs/42439736680) passes the app build and emulator navigation/layout tests. Its dark/light screenshots were reviewed; system navigation has reserved space and the spot list remains usable.

The compact desktop followup responds to Windows screenshot evidence that a 900 by 600 view could clip the manual command field. It shrinks the header, retains a visible Cluster commands shortcut to Source and verifies the command button inside the scrolled canvas bounds. The expanded local suite passes 176 tests without skips. CI for that followup remains pending until its branch checks finish.


## Desktop performance guard. November 8, 2026

The explicit Windows self test measures UI creation, repeated tab switches, scrolling on the six settings pages and idle process CPU. It runs before source packaging and again inside the portable and installed applications. A budget failure makes the self test fail, so the workflow cannot publish that build. Existing Windows verification JSON artifacts retain the measurements, limits and failure names even if verification fails.

The initial hosted runner budgets are 2,000 ms for UI creation, 100 ms median and 500 ms 95th percentile for tab switches and scrolling and 0.10 CPU seconds per idle wall second. Each navigation pass warms every tab before three measured rounds. Scroll checks move each settings canvas through the middle, bottom and top. Idle sampling runs the real event loop for two seconds. CPU ratio measures process CPU divided by elapsed wall time, not Task Manager's percentage normalized across all cores. Budgets are regression gates on the build runner, not guaranteed response times on every PC. Startup here measures Tk/application creation, not installer launch, EXE extraction or Windows security scanning.

Tests also check the underlying drawing work: identical corner artwork, much larger repeatable image centers, shared geometry and no unchanged state control writes. Those deterministic checks complement timing budgets when a hosted runner is unusually fast or busy. The benchmark is imported only by explicit self test execution. It does not add continuous profiling to the normally running app, connect a cluster, play audio or open PTT. Operator performance testing on slower physical machines remains necessary.

## November 8, 2026. XP shared core pilot

All 218 local source tests pass under a Linux dummy display. Each staged official Python 3.4.4 interpreter passes 148 shared checks on hosted modern Windows. The [XP verification reports](https://github.com/Liberty-Chris/DX_Talker/actions/runs/42464870470) show complete UI and all 78 settings fields, real SAPI rendering without playback, DPAPI roundtrip, valid PNG QR output, digest vectors and public update HTTPS with certificate/hostname checking. Source and installed performance budgets pass on x86 and x64. Both installers pass install, native launch, reinstall, renamed shortcut preservation, settings preservation and removal. The original archive SHA256 remains `e9ac3463fae15baeff4279ad452a9471ab09bb420e7742e26e876a3da3420485`.

The native audio and serial tests use simulated APIs. There is no physical XP, audio endpoint, serial PTT or public cluster submission acceptance in this record. The hosted target is Windows build 26100. An unrelated modern x86 setup step encountered GitHub HTTP 504 while downloading Python; it is separate from the passing XP jobs. Final branch checks must pass before the PR is marked ready.

## Ubuntu package verification

The reusable Ubuntu workflow builds on 22.04 and installs that package on 22.04 and 24.04. It checks the desktop entry and executable, synthetic native keyring round trip, eSpeak NG WAV rendering with measured pauses, verified public GitHub HTTPS, shared UI pages and retained performance budgets. It reinstalls and removes the package while preserving a user settings marker. Reports are uploaded as Ubuntu verification artifacts. No playback, serial access, public spotting or RF occurs. Physical Ubuntu and radio acceptance remains required.

## Idle transition audio checks

Fake PortAudio callbacks inject isolated and repeated output underruns, priming status, other flags, cancellation and deadlines. Coordinator tests verify that recovered spot audio preserves RF, PTT is released and interrupted required IDs disarm without advancing their schedule. Power tests verify thread scoped request/release, failed mode changes, worker exit and screensaver observation gaps. Windows runs additionally bind and briefly exercise the native idle request and release API. No simulated screen event establishes physical driver acceptance. Retest the original Windows 10 screensaver and audio endpoint combination.


## 1.0.0b1 usability verification

The graphical Linux suite ran `python -m unittest discover -s tests -v`: 276 tests, no failures and one native Windows API test skipped. New workflows cover independent preference saving during RF, unfinished field isolation, scoped previews/connect, durable credential free drafts, profile Undo, one action cluster switching, themed Unmute and cancellation of deferred output on Stop/source loss. Existing filtering, transmission coordination, receive hold and compatibility checks remain enabled. Audio callback tests verify volume changes between buffers without restarting playback.

Gradle 8.9 with Android 35 ran `testDebugUnitTest assembleDebug assembleDebugAndroidTest`: all 23 unit tests pass and both APKs compile/package. Instrumentation compilation is not emulator execution. No emulator or physical phone interaction acceptance ran locally. Android versionCode is 20 and versionName is 1.0.0b1.

`check_docs.py`, `check_versions.py`, `sync_privileges.py --check` and whitespace checks pass. Release version ordering from 0.2.0a25 through beta, release candidate and final was checked. The original archive has no diff. Native desktop inspection covered Live spots, green Unmute, Filters, grouped maintenance and a 900 by 600 compact preview with large text selection and page navigation. Windows/XP native package, installer and hardware checks remain required through the hosted workflow and operator beta acceptance.

## Beta idle CPU correction

The merged 1.0.0b1 source failed modern Windows x86 idle CPU twice, most recently 0.12455 against a 0.10 limit. Its second startup measurement passed at 1808 ms. XP x86 passed the rerun after the earlier public GitHub rate limit failure.

Idle polling was repeatedly writing Tk variables and widget options, repositioning the empty list label and changing hidden meter coordinates. The correction caches rendered values, spot visibility and navigation geometry. It retains 75 ms control polling, unchanged receive detection and every existing performance limit. Deterministic regressions check that repeated idle polls issue no writes to those surfaces and that selection, spots, queue, routing and receive changes still render immediately.

A same environment graphical Linux comparison with synthetic devices and four second idle samples measured process CPU ratio 0.04291 before and 0.01087 after. This is a local source comparison, not Windows x86 acceptance. The Windows smoke test now closes its application before temporary folder cleanup after failed assertions, preserving the original performance failure instead of masking it with a locked diagnostic file error. Hosted Windows package checks must confirm the correction on both architectures.
