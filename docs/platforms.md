# Platform groundwork and compatibility

## Current implementation

The distribution target remains Windows 10 22H2 x64 and Windows 11 x64. Portable core tests also run on Linux. This does not establish a packaged Linux or macOS product. The Windows installer, System.Speech and DPAPI secret storage are Windows adapters.

SpeechService consumes a validated Spot and immutable Settings and produces a Clip. A Clip is little endian signed PCM16 with explicit sample rate and channel count. Windows SSML and optional Piper both implement that boundary. The coordinator owns all output, playback cancellation, radio timing and PTT. Local listening uses the same coordinator with no serial adapter or ID schedule. New platform shells must not bypass it for RF.

SourceClient emits source_state, source_ready, source_lost, spot and raw events. Raw text is bounded, redacted, session only and excluded from speech. A source generation identifies the active connection; stale generation events are discarded. ProfileStore retains only source connection fields, separate from audio and radio settings. Protected credentials require a platform specific vault adapter.

History JSONL schema version 1 consists of a UTC time and kind, with a spot's normalized callsigns, decimal frequency string, UTC source and receipt timestamps, source identifier and profile name. Connection events contain profile and source type; disconnect contains profile. Raw text, commands, credentials and feed URLs are excluded. Mobile or companion implementations can consume these records without a Tk dependency.

## iOS and Android

The initial mobile scope is local spoken cluster listening. Build native source transport, lifecycle handling, audio output, platform speech and secure credential storage around the same validated spot and speech plan concepts. iOS Keychain and Android Keystore backed storage replace DPAPI. Store releases and their platform update mechanisms replace the Windows installer updater.

Validate background network and audio behavior, interruption handling, Bluetooth routing, accessibility focus, VoiceOver and TalkBack before making mobile support claims. RF and external radio control are separate milestones. Do not promise continuous background cluster connections until platform lifecycle tests pass.

The current Python core is a behavioral reference and test fixture source, not a claim that an iOS binary can be compiled directly from this Windows desktop app. Keep parsers and announcement policies isolated so a mobile implementation can reuse their contracts and test cases without copying the desktop UI.

## Older desktops

Use a capability matrix rather than a blanket old OS promise. Test the oldest supported interpreter, package runtime, TLS stack, audio library, speech API, architecture and installer on each actual OS. Older macOS and Linux releases may need separate runtime pins and package formats. Windows x86 requires its own build and dependency checks. A 32 bit binary alone does not establish older Windows compatibility.

The current Python 3.12 and Windows 10 installer floor are unchanged. Do not advertise Windows 7, Vista, old macOS or old mobile OS support based on source portability. Record pass/fail evidence before selecting a lower support floor. Preserve offline OS speech as an option so a future neural voice requirement cannot exclude older hardware.

## Next acceptance gates

| Target | Next concrete gate | Current evidence |
| :--- | :--- | :--- |
| Windows x64 | Two successive release update and operator listening tests | CI core, packaging and installer checks |
| Linux desktop | Native source launch with selected audio and Piper fixture, then real audio test | Portable core tests |
| macOS desktop | Package, native speech adapter and secure vault | Design only |
| iOS | VoiceOver accessible local cluster listening prototype | Contract and lifecycle plan |
| Android | TalkBack accessible local cluster listening prototype | Contract and lifecycle plan |
| Older OS and x86 | Runtime and dependency matrix on named versions | Not yet tested |

## November 2026 pilot targets

The build matrix now produces x64 and x86 installers and portable packages. The x86 target is for Windows 10 22H2; Windows 11 is an x64 target here. x86 has its own installer identity, directory and shortcuts, while account settings remain shared. Do not run both architectures against the same live station at once. Each runtime's updater selects its own architecture. x86 packaging tests on a current x64 Windows runner do not establish operation on a physical 32 bit Windows machine.

Windows XP uses a separate build of the maintained desktop core with a private Python 3.4.4 runtime and XP adapters for SAPI speech, WinMM audio/input and serial RTS/DTR. Profiles, filters, announcements, coordinated radio output and IDs, history, diagnostics, collection transfer and verified update selection remain shared. Separate 32 bit SP3 and 64 bit SP2 pilot installers are prepared for acceptance testing. See the [XP port and verification record](xp_port.md). Hosted Windows checks do not establish actual XP or hardware acceptance. Optional external speech programs require their own XP compatible versions.

The older `legacy/xp` source test kit remains a limited developer listener requiring a separately installed runtime. It is not the full application and is not the XP installer.
