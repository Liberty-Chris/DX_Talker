# Changelog

## 0.2.0a2. November 5, 2026

Removed command masking. Added a temporary Show and Hide eye control to the dedicated source password field. Only source relevant controls are active, and duplicate connection buttons are removed. Changing source type clears the session secret; profile changes conceal it again.

Piper starts with ONNX telemetry disabled. Added concrete Windows neural voice setup instructions, a real model render verification job and an explicit Actions option to publish a verified release from main for updater testing.

## 0.2.0a1. November 4, 2026

Saved cluster profiles with optional Windows protected secrets, shared visible command entry, a bounded redacted source console and automatic live view clearing on source changes.

Configurable speech rate, voice gender preference, character pauses and group pauses with the “New DX on” introduction. Optional external Piper neural voice adapter. Independent spot, CW, voice ID and local listening levels.

Live local listening, keyboard shortcuts, larger interface text, high contrast appearance and saved supervised operation acknowledgement. Configurable rotating history and display retention. A reserved cluster customization help topic.

GitHub release notifications, Pilot and Stable channels, verified downloads and interactive update installation. Tested tag builds publish setup, portable files and checksums. Initial installation is required to enable future notifications. Mobile and older system contracts and acceptance gates are documented.


## November 2, 2026. Windows installer

Added an Inno Setup installer targeting Windows 10 22H2 and Windows 11 x64. Setup creates DXt desktop and Start menu shortcuts, installs the bundled runtime and provides removal through Windows Settings. Updates and removal retain local preferences. Added workflow checks for installation, shortcuts, the installed application self test, reinstallation and removal. Actual Windows 10 and Windows 11 acceptance remains open.

## October 31, 2026. Windows pilot 0.1.0a2

Added the DXt identity to the application header and Windows icon, plus EXE product and version information. Added light and dark themes with a separate saved appearance preference. Updated status panels, spot table colors and action spacing. Appearance changes leave radio settings and RF state alone.

Included the branding assets in the portable package and extended Windows smoke checks to exercise both themes.

## October 31, 2026. Windows pilot 0.1.0a1

Added the first Windows application source, including a live spot view, TCP/Telnet sign in, manual cluster responses, generic HTTPS JSON feeds, local sample spots and saved settings. Passwords and tokens remain in memory.

Added explicit preview and radio output selection, Windows speech, audio Morse, optional WAV IDs and serial RTS, DTR or VOX output configuration. One coordinator controls playback, ID priority, queue expiry, cancellation and PTT release attempts.

Added automated core tests, Windows source and packaged smoke checks and a portable Windows build workflow. Updated the canonical help to match the pilot. Physical radio testing, W4MR testing and release installation work remain open.

## October 17, 2026

Reworked the project documentation to read more naturally and removed repeated reporting language. Simplified the status page so it explains where the project stands and what's next.

Added plans for a standalone WiFi device and direct repeater integration for systems using ASL3, Allmon and Asterisk.

Added callsigns to the original authors' names: Kevin Leggett (KT4BN) and Dave Hockaday (WB4IUY). Introduced the modernization in the README from my perspective as Chris Hockaday (KF4DBX).

Added separate rights notices for the modern project and original files. All rights are reserved for now. The original ZIP is unchanged.

## October 14, 2026

Added the project overview, roadmap, requirements, proposed architecture, decisions and open questions.

Started the Help and Info pages and added instructions for keeping them current during development.

Reviewed the original archive without running its programs. Recorded the files found and the details useful for building the new application.
