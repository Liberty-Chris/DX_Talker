# Changelog

## 0.2.0a15. Unreleased

Bundle six recommended nodes from the supplied validated operator list: W1NR, DX Spots, N2WQ, WB3FFV, W3LPL and W4MYA. Show preconfigured addresses in the choosers and reuse the operator's entered callsign when saving a node. Preserve existing profiles and explicit connection. Embed the listening filter editor directly on Source in responsive columns; keep independent filter application and include pending filter edits in the main save action. Move frequency limits into its advanced controls. Record physical phone confirmation that a14 QR scanning and import work.

Add a desktop Mode column and explicit license filter heading. Omit untagged activity and unknown mode placeholders from mobile rows. Put kHz/MHz on Listen and keep Apply filters visible below the form. Use canonical filter draft keys, preserve preset units and clear stale displayed rows when applying while stopped. Share display/speech acceptance and add synthetic live-feed UI coverage for bands, modes, license classes and unit/preset changes.

Correct the desktop rendering regression introduced in a14. Enlarge the solid areas of rounded image tiles while preserving their corner artwork and small control sizes, share identical Tk surfaces and reuse corner geometry across colors. Update state controls only when their visible state changes instead of rewriting them every 75 ms. Rounded styling, keyboard behavior and output controls remain available.

## 0.2.0a14. November 8, 2026

Remove the separate spot review action on desktop and Android while preserving validation, session binding and rate limits. Move the listening shortcut out of Frequency range and align Announcements panels. Add rounded ttk buttons and panel surfaces, keeping native window frames. Give Android an explicit camera permission flow and an owned QR scanner with camera lifecycle/error handling and diagnostic events. Add camera permission/return instrumentation coverage and an ordered release download index.

## 0.2.0a13. November 7, 2026

Move GitHub Actions to releases declaring the Node.js 24 runtime. Serialize release publication and recognize an already published complete release on an exact commit retry without replacing assets. Stop on incomplete releases or inspection errors. Preserve the existing protection against tags pointing at another commit. Correct the a12 release notes and require their version to match application metadata before building.

Add an early publication tag check before Windows packaging, with an explicit version bump message. Align application, Windows numeric metadata, installer, help and Android version to a13. Archive the corrected a12 notes and synchronize reviewed archived text through a separate metadata only workflow after merge. Keep release assets and tags intact.

## 0.2.0a12. November 7, 2026

Add a single listening filter editor with saved presets, FCC license/emission eligibility, separate reporting/DX geography, explicit unknown handling and version 3 QR transfer. Make the Android spot list the main scrolling area above system navigation and move setup/spotting to separate pages. Add reviewed spotting to the current cluster only and curated directory browsing on Android.

Add a bounded serial PTT test, independent CW/voice schedules and voice pause controls. Clarify receive input health versus quiet level, recover transient input overflow through a new quiet interval and use nonblocking runtime notices. Reuse the Windows speech process and verified recorded clips, expose queue/preparation timing, allow zero additional gap and add catch up controls. Simplify recorded voice generation and discover bundled/user packs without requiring path setup. No new recorded packs or reviewed cluster entries are supplied in this update.

## 0.2.0a11

Android gains persistent navigation and audio controls, predictable Back behavior, draft restoration, appearance choices and a visual announcement builder. Shared band, mode and activity filters transfer through version 2 QR/files. TCP keepalive and quiet-feed messaging improve connection diagnosis without sending arbitrary cluster commands.

## 0.2.0a10. November 6, 2026

Fix a playback completion race that could report a normal final buffer as an unexpected audio stream stop. Allow a bounded completion notification interval after all samples are queued while preserving cancellation, deadlines and device fault handling. Show fixed readable playback messages and export cause codes, numeric sample progress and local/radio routes for diagnosis.

## 0.2.0a9. November 6, 2026

Identify shared speech requests as DXTalker to pass website client filtering. Distinguish website HTTP 403 responses from explicit service voice/model denials.

Choose all or selected cluster profiles for QR transfer. Large selections use numbered pages collected and validated on Android before reviewed import. Add optional receive audio transmit hold with a level display, adjustable threshold, 5 to 10 second quiet delay, input fault shutdown and interrupted transmission retry. Add shared ElevenLabs online speech and reusable Recorded voice generation with no tester key entry. Keep the account key in private DreamHost configuration, enforce server allowances and preserve verified clip resume. Windows speech and Piper remain available.

## 0.2.0a8. November 6, 2026

Correct the publish job’s x64 portable artifact name so release assembly can complete after both Windows builds pass.

Arm local listening before the first spot and preserve that intent during explicit Connect. Add bounded private diagnostics and manual export, clearer feed errors, QR/file profile/filter transfer, an initially empty curated directory, recorded WAV voice packs and a local model/speaker batch generator. Improve Android import, parsing, pronunciation, filtering, queuing, connection lifecycle and credential storage. Add Windows x86 artifacts with matching updates and a separate limited XP source test kit. Gate stable legal/privacy acceptance on owner approved text and expand radio setup guidance.

## 0.2.0a7. November 5, 2026

Clarify profile creation, editing, renaming and confirmed deletion. Remove the fixed profile count cap and isolate profile operations from unrelated pending settings. Explain optional Windows protected password/token storage. Compact Source and Audio / PTT, hide inactive connection and serial controls and retain their values.

## 0.2.0a6. November 5, 2026

Add announcement presets, section inclusion and order controls, editable intro text, optional spoken frequency units and a live sentence example. Preserve frequency conversion when units are muted. Preview the pending format through the output coordinator without applying unrelated edits. Existing settings keep the prior default; IDs and source data are unchanged.

## 0.2.0a5. November 5, 2026

Compact the IDs tab into CW, voice and schedule sections. Hide inactive voice source fields while preserving values. Give RF a stateful enable and disable control with accent and red stop states. Use saved settings without applying pending edits or changing the source. Remove source readiness, supervision acknowledgement and shared device confirmation gates from RF enable. Retain valid radio and ID configuration, output serialization, cancellation, fault shutdown and transmit limits.

## 0.2.0a4. November 5, 2026

Compact the Announcements page into Frequency range, Timing and repeats and RF supervision. Use short numeric fields, explicit units and nearby range guidance. Clarify that filter limits remain in kHz while speech and display can use MHz. Settings and output behavior are unchanged.

Use Windows native certificate verification for update checks and downloads. Preserve existing desktop shortcuts, including renamed ones, without offering to create a duplicate. Add packaged certificate context and installer shortcut regression checks.

## 0.2.0a3. November 5, 2026

Announce intro, frequency and callsign in that order. Add exact kHz/MHz selection shared by speech and live display. Keep source data, filters and logs in kHz.

Compact the speech page, hide inactive provider settings and put previews at the top. Replace separate connection actions with one control that reflects actual transport state, highlights a connected state and offers red Disconnect on hover or keyboard focus.

Make local listening a true output toggle that does not apply settings or reconnect the cluster.

Fix a reproduced login prompt framing failure, fragmented terminal formatting and socket cleanup before retry. Improve update status with installed version, channel and distinct network error categories.

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
