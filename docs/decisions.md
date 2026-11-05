# Project decisions

Updated October 17, 2026.

## D001 Windows first

Decided.

I'm starting with a Windows application using a compatible USB interface for radio audio and PTT. The first supported Windows versions and radio interfaces still need to be chosen.

## D002 Separate CW and voice settings

Decided.

CW and voice identification will have separate text fields. Voice will use text to speech by default, with an optional WAV recording. CW will be generated as audio Morse through the radio connection. The timing and whether the two IDs alternate still need to be settled.

## D003 Original archive and help pages

Decided.

Keep the original ZIP unchanged. The pages in docs/help will become the application's operator manual. Keep their topic IDs stable and update the relevant help page whenever a feature changes.

## D004 Separate cluster and web feed connections

Proposed.

Use one connection method for TCP/Telnet clusters and another for supported HTTP or HTTPS feeds. The W4MR host and port are the initial cluster example. A web feed provider still needs to be selected.

## D005 One place to manage transmission

Proposed.

One part of the application should manage all radio audio and PTT so announcements and IDs cannot overlap. Transmission should stay disabled after startup or a fault until the operator enables it. This needs testing with the supported hardware before unattended use.

## D006 Development tools

Selected October 31, 2026 for the first Windows pilot.

Use Python 3.12 with Tkinter for the desktop interface, sounddevice for explicit audio output selection and pyserial for RTS and DTR control. Use Windows System.Speech through a bounded PowerShell child process to generate WAV audio before keying. Package with PyInstaller on a Windows GitHub Actions runner.

This keeps the parsing, connection and transmission policies testable on other systems while keeping the actual product focused on Windows. Native .NET was considered but is not required for this first implementation. The Windows package and hardware behavior still need pilot verification. Target Windows 11 x64 first. Other Windows versions and architectures are not claimed.

Audio selection uses an exact host API and device name and rejects ambiguous matches. Device indexes are resolved again before playback. Serial PTT supports RTS, DTR or both, with explicit active polarity. VOX is an operator selected alternative. CM108 HID, CAT and vendor specific PTT remain future adapters.

## D007 Separate rights for new and original work

Decided October 17, 2026.

I'm reserving all rights for now. The [modern project notice](../LICENSE) excludes the historical archive, which has its [own notice](../Original_Files/LICENSE).

I may change the modern license later with any necessary permissions. That won't automatically change the original files' terms. Existing permissions and bundled components' terms still apply. Ownership and any publishing agreements need to be checked before licensing or reusing historical material.

## D008 Standalone hardware and repeater integration

Planned October 17, 2026.

After the Windows application, I'm planning a standalone device that connects to a radio and uses WiFi for internet access. I'm also planning direct integration for repeater systems using ASL3, Allmon and Asterisk.

The hardware, integration method, supported versions and release timing still need to be worked out.


## D009 Initial configurable operating policy

Selected October 31, 2026 for the pilot.

Keep hardware selection configurable. Start with a TCP/Telnet source and a documented generic HTTPS JSON feed contract. Provide offline sample spots and local audio preview. Store settings locally but keep source passwords and tokens in memory for the session.

Schedule voice, CW, alternating IDs or both according to an explicit operator setting. The initial default is CW every ten minutes while RF is enabled, including an ID before the first automatic spot. The operator must supply ID text before enabling RF. This is a configurable product default and does not establish a station's legal identification policy.

Automatic shared channel access detection is deferred. The pilot requires the operator to acknowledge supervised use on a clear or coordinated channel. Startup, source loss, settings changes and faults disable RF and clear queued work. Reconnect never rearms transmission.


## D010 DXt identity and appearance

Selected October 31, 2026.

Use the approved minimalist DXt lettering with a cyan lowercase t. The D and X use graphite on light surfaces and white on dark surfaces. A vector master supplies clean transparent header assets and a multiresolution Windows icon. Use a stable charcoal tile for the shell icon so it remains visible against either Windows theme.

Store appearance in appearance.json beside settings.json. Switching themes is cosmetic and must not apply pending settings, stop output or enable RF. Default to Dark and provide an explicit Light option. Ship generated PNG and ICO assets so the Windows build and runtime need no vector rendering dependency.

## D011 Windows installer

Selected November 2, 2026.

Use Inno Setup 6 around the existing portable package. One x64 setup targets Windows 10 22H2 and Windows 11. Keep the installer AppId stable for updates. Install for the current account without requiring administrator access. Include Start menu and desktop shortcuts with the DXt icon, with the desktop option selected initially. Keep user settings outside the installation directory and retain them on removal. Keep the portable download available. Verify installation lifecycle on the hosted runner and record actual Windows 10 and Windows 11 acceptance separately before claiming tested compatibility.

## November 4, 2026: Operator controls and release updates

Named source profiles retain connection details separately from radio settings. Optional secrets use Windows account DPAPI protection, with no plaintext password in ordinary settings, examples or diagnostics. Selecting a profile stops output and clears the current view. Connection generations discard stale callbacks. The user explicitly requested saved cluster data and remembered supervision acknowledgement. Startup and recovery still leave output disabled.

Use Windows System.Speech SSML for explicit spot group and character pauses. The standard introduction becomes “New DX on”. An optional external Piper CLI adapter offers local neural voices without a service account or cloud text submission. Do not bundle a model or promise a voice license, performance or quality without selection and listening tests. Provider output stays behind the existing coordinator and is prepared before PTT.

History uses bounded rotating JSONL with a selectable folder, file size and backup count. Keep received spots, completed announcement routes and source lifecycle events. The live window is bounded independently and clears on source changes. Raw incoming text is a redacted 15 line session console, not a disk log or speech input. Commands remain visible, with explicit masking for a password response.

Use tested GitHub Release assets as the update channel. Offer Pilot and Stable discovery, background checks, release notes, SHA256 verified download and an operator initiated interactive installer. Publishing is gated on core, packaged Windows speech/UI and installer checks. The same AppId retains installation identity and account data. No automatic installation or restored RF state is permitted. Existing builds need one initial manual updater installation. The first two release upgrade test remains an acceptance gate.

Accessibility additions include live local listening, independent audio levels, keyboard shortcuts, a high contrast theme and configurable text size. Full screen reader support requires operator acceptance; Tkinter portability alone is not evidence. Mobile and older desktop work begins with documented contracts and a capability matrix, not unverified package support claims. See platforms.md and release_process.md.


## November 5, 2026: Clear source controls and preview publication

Keep cluster commands visible at all times. Confine visibility toggling to the dedicated password or token field, with an eye icon plus Show and Hide text. Visibility is temporary and resets at profile or source boundaries. Clear a session secret when manually changing source type to avoid sending a cluster password to an HTTPS service. Preserve inactive connection fields while disabling them.

Add an explicit workflow dispatch option for publishing from main after verification. This provides a release path without requiring local Git credentials, while ordinary branch and PR builds cannot publish. Preview tags remain visible to the Pilot channel. Require real neural rendering alongside existing tests before publication. Set ORT_DISABLE_TELEMETRY=1 before every Piper process so local speech does not initialize the runtime telemetry uploader.


## November 5, 2026: Announcement order and connection clarity

Use intro, frequency with units and phonetic callsign for all spot speech providers. Convert kHz to MHz with Decimal only at the display and speech boundary. Keep incoming data, filtering and logs in canonical kHz. Use one saved unit selection across the live view and speech page.

Compact speech settings into delivery, active provider and interface groups. Use one connection action per page with a neutral disconnected state, an appearance accent on connected transport and a red disconnect action on hover or keyboard focus. Connecting and retrying remain distinct and cancellable. An open socket must not imply authenticated login or valid DX data.

A deterministic regression test reproduced a missed login prompt when a banner followed it in the same TCP read. Match framed lines and partial prompts after removing terminal presentation sequences. Close sockets before retry backoff and discard connections that finish after cancellation. Do not attribute the reported server trouble to this bug without operator evidence.

Update failures must describe DNS, TLS, HTTP, timeout and rate limit categories without showing remote exception text. Report installed version and channel after successful checks and explain preview availability to Stable users. Do not weaken HTTPS verification.

Local listening is a true output toggle, using applied settings. Stopping it cancels audio and queued announcements while preserving the source generation, socket and incoming live view. This prevents a button intended to stop listening from implicitly applying source edits or restarting a session. Its visual state follows the engine, with a brief disabled Stopping state while playback cleanup finishes.

## November 5, 2026: Compact announcement policy

Apply the established compact field helper to Announcements. Group frequency range, timing and repeats and RF supervision in bounded width sections. Keep units and timing bounds adjacent to controls. Retain existing variables, validation, acknowledgement persistence and output stop behavior.


## November 5, 2026. RF toggle and compact IDs

Use the same state control for connection, local listening and RF. The RF action reads applied settings and never saves pending edits or reconnects a source. Remove source readiness, the supervision checkbox and shared device confirmation as RF prerequisites so a configured station can identify offline. This supersedes the earlier source and acknowledgement gates. Keep output and ID validation, one transmission coordinator, cancellation, source loss shutdown and bounded transmission. Retain the legacy supervised_ack setting only for compatible settings loading.

Group IDs into bounded CW, voice and schedule sections. Show only text or a recorded file for the selected voice source without discarding the inactive value.


## November 5, 2026. Operator controlled announcement format

Keep a validated permutation of Intro, Callsign and Frequency plus independent include flags. Attach optional units to frequency so moving the number cannot strand its units elsewhere. Preserve legacy frequency first delivery as the default. Support a short operator authored intro while keeping remote comments excluded. At least one section must remain included.

Use presets, checkboxes and Up/Down controls rather than requiring drag gestures. Show a live readable example and send Listen to example through the existing coordinator with an immutable preview settings snapshot. This previews pending format edits without saving unrelated settings or modifying the cluster. Existing local output routing, serial PTT exclusion, cancellation and shared VOX device confirmation remain. IDs are outside the format editor.


## November 5, 2026. Profiles and connection/audio layout

Remove the fixed 100 profile cap on both save and load. Preserve stable IDs during edits and renames and reject updates to missing IDs. Use explicit Save new profile, Save changes and Delete profile actions, update both selectors and keep deletion confirmation. Profile save/load uses connection data plus applied settings as a base, so unrelated unfinished edits cannot block it or be applied accidentally.

Use compact grouped Source and Audio / PTT controls with only the selected connection type and PTT fields visible. Clarify that remembered credentials are the existing cluster password or token encrypted for the current Windows account, not a newly created secret key. New/delete clears the old session display and credential while preserving other saved profiles.
