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


## November 6, 2026. Diagnostics, transfer and pilot targets

Permit local listening to arm independently of source readiness and restore already armed listening before an explicitly requested connection starts its worker. Do not preserve RF or auto-resume after source failure. Diagnostics use bounded private files, fixed error categories and safe stack locations, with manual report export and no upload transport. Stable builds default logging off and require owner approval of exact legal/privacy texts.

Use a versioned credential-free QR/file schema rather than accounts. Keep canonical filters in kHz, reject unknown fields and query-bearing feed URLs in transfers, review before mobile import and never connect automatically. Dad's curated directory starts empty with explicit active/retired states and review dates; no automatic deletion of operator profiles occurs.

Separate x86 packaging and installer identity from x64; choose updater assets by runtime bitness. XP is incompatible with the modern runtime. Keep a separately labelled Python 3.4/SAPI source test kit while a full XP port and actual XP acceptance remain open.

Recorded voices are deterministic local PCM assets with checksummed manifests and bounds, generated from separately reviewed Piper models. The reference LJ Speech card identifies a public domain training dataset. Do not bulk redistribute every voice under one assumed license. Multi-model/speaker generation is opt-in local work with a matching card per model.


## November 6, 2026. Collection QR, receiver hold and ElevenLabs

Keep the existing transfer document and single QR format compatible. Add DXT2 as a transport for bounded numbered compressed chunks with a whole collection digest. Default desktop selection to all saved profiles and commit nothing on Android until the entire collection validates and is reviewed. Preserve partial scans through activity recreation, allow explicit reset and reject mixed collections.

Measure optional local input RMS rather than claiming hardware carrier detection. Hold initial/due IDs and spots until a full operator selected 5 to 10 second quiet interval, cancel an interrupted transmission and retry eligible work. A stalled or failed input disables RF. Keep startup disabled and do not let local previews or listening depend on the receiver gate. Receiver audio is never recorded or uploaded.

Use ElevenLabs to generate the existing offline Recorded format rather than adding a cloud dependency to every announcement. Generation is explicit and uses the operator’s own session only key and account credits. Retain verified completed clips for resuming but do not automatically retry billed requests. Preserve voice/model provenance without asserting redistribution rights. Piper remains an optional provider and generator.


## November 6, 2026. One shared ElevenLabs pilot account

Replace individual tester key entry with a private PHP gateway on existing DreamHost hosting, initially at www.jcara.club/dxtalker-speech/speech.php. The owner enters the account key through a hidden shell prompt and stores it outside the public website. The app receives only the endpoint and a revocable pilot admission value, with no owner key field. Both online speech and optional Recorded pack generation use this shared service. Keep direct owner generation as a developer script rather than the tester UI.

The admission value is distributed in the app and is therefore not a durable app secret. Bound the pilot with atomic daily text/request limits, per observed IP hourly requests, two concurrent upstream jobs, fixed provider URL, disabled redirects, certificate checks and configured voice/model choices. Cache PCM privately with an age and size bound. Prepare the full clip before PTT. Do not automatically retry billed requests or silently switch speech providers.

Only trusted Windows builds inject the client configuration from DXTALKER_SPEECH_CONFIG. Reject accidentally supplied owner configuration. Builds without deployment configuration remain explicit about service availability. The service and app are implemented and tested with synthetic providers; hosting installation and actual account usage require owner setup.


## November 6, 2026. Bounded playback completion confirmation

Use the completion notification as the output API completion signal and recheck it when observing an inactive stream. A final buffer may complete between the polling wait and stream state read. Allow a bounded 250 ms interval only when all frames have already been queued, with cancellation and deadline checks continuing every polling interval. Never treat queued PCM alone as successful playback or suppress real faults.

Use an owned AudioPlaybackError type for fixed operator messages and numeric evidence. Export only allowlisted cause codes and frame/rate/channel counts plus local/radio route. Do not log arbitrary backend exception messages, device names or audio. A generic historical RuntimeError alone cannot prove the failure mechanism.

## November 6, 2026. Mobile navigation and received spot filters

Keep Android listening focused on Listen, Clusters and Settings with persistent audio controls. Detail pages maintain a Back history and Bundle saved form drafts; navigation never owns the foreground listener. Applying local filters cancels pending speech rather than reconnecting. Saving profiles is distinct from selecting them. Announcement sections are controlled visually rather than requiring template syntax.

Preserve at most 160 printable comment characters and optional explicit mode only in memory. Classify exact supported mode/activity tokens and treat missing/conflicting mode as Unknown rather than infer from a regional band plan. Match selected groups with AND and values within each group with OR. Blank groups accept all. Keep metadata out of speech and disk logs. Use shared cross-platform fixtures. Transfer document version 2 carries selection strings, while existing version 1 transfers remain readable. Old readers reject the expanded transfer rather than silently losing filtering intent.

Enable OS TCP keepalive without injecting characters into an unconfirmed login or changing the user's saved server filters. Desktop tuning requests short transport probes and Android retains native timing. Quiet incoming data alone does not establish connection failure. Automatic server filtering and application heartbeats await tested server adapters; no universal command is assumed. DXSpider and AR Cluster use different filtering grammars. References: https://www.dxcluster.org/usermanual_en-12.html and https://www.arcluster.org/user-guide/ . Physical Android background, speech and camera tests remain separate acceptance gates.


## November 7, 2026. Personal listening and field use

Keep regulatory rules in a versioned exact decimal dataset, separate from voluntary band plans. Generate Kotlin frequency tables from the reviewed Python data and test shared explicit boundary examples. An unknown mode is not proof of eligibility. FCC geography, split operation, occupied bandwidth and station conditions remain explicit limits in Help, with sources linked there rather than crowding controls.

Use feed supplied or operator known station locations instead of presenting callsign areas as actual current QTH. Keep reporter and DX location choices separate. Local filters never clear server side account filters. Apply listening changes without reconnecting; preserve current playback but clear pending spots. Share noncredential presets through transfer version 3 and retain legacy imports.

Spotting requires reviewed explicit submission to the current signed in TCP node. Socket delivery is not cluster acceptance. Do not duplicate submissions across nodes or retry after reconnect. A bounded manual serial PTT test remains inside the sole transmission coordinator and respects the optional receive gate. Independent CW/voice deadlines serialize audio; operator pause markers produce PCM/SSML silence and are not passed through as spoken words.

Reuse Windows synthesis initialization and verified recorded PCM assets instead of trading freshness for an unbounded backlog. Retain bounded queue/age limits and expose preparation time and queue age. Runtime faults stop output and use a nonblocking notice so a user reading an error does not look like a frozen event loop. Bundled voice assets and reviewed directory entries are separate supplied content, not fabricated during implementation.


## Release version ownership and prose corrections. November 7, 2026

Keep published installers tied to their original version and tested commit. Workflow changes that need a newly distributed package receive a new application version; rerunning a workflow does not increment it. Check conflicts before packaging and again at publication. Store corrections to published descriptions in version named archive files and synchronize only the release body through a separate workflow. This resolves copied descriptions without replacing installed users' downloads or moving tags.


## Embedded Source listening editor. November 8, 2026

Place the full listening editor alongside connection settings on wide desktop windows and below them on narrower windows. Use the existing Source scrollbar and route the Live spots shortcut to this section. Keep filter changes staged and preserve the independent Apply listening filters action, which must not apply pending connection or radio edits. The main settings save merges pending filter fields too, so visible edits are not silently omitted. This replaces a detached window while preserving independent connection and output controls.


## Spot metadata and mobile filter application. November 8, 2026

Use a separate desktop Mode column and label the operator's selected license filter above the list. Do not present an untagged activity fallback as General, which can be mistaken for a license class. Omit missing activity/mode metadata from live row details. Keep one canonical mobile draft key per filter and an anchored Apply action. Route display and announcement preparation through one filter decision so rejected reports cannot enter either path. Retain canonical received frequencies for display conversion; unit changes do not reconnect or replay history.


## Desktop rounded rendering cost. November 8, 2026

Keep rounded desktop controls but use larger solid strips in image elements, explicit 32 pixel widget minima and shared Tk image instances. Tk tiles these images instead of stretching them. The original 32 pixel surface left a 12 pixel center, causing excessive draw calls on large cards. Cache the geometry separately from colors to avoid recomputing every antialiased corner for a newly visited state. Skip unchanged state control writes during the 75 ms event poll, while still rendering source, output, hover, focus and theme changes. Do not slow safety event polling to mask rendering cost.

A comparison of the a12 and a14 tags reproduced slower tab switching under the same Linux dummy display with no public cluster, speech or RF activity. This establishes a rendering regression, not a confirmed diagnosis of the reporting PC. Windows packaged verification and operator testing remain distinct evidence.


## Build-time desktop performance gate. November 8, 2026

Use explicit synthetic self test measurements to block builds that exceed reviewed startup, navigation, scrolling or idle CPU budgets. Publish the measured evidence beside existing Windows verification reports, including failed checks. Pair wall clock budgets with deterministic drawing work checks instead of relying solely on fast hosted hardware. Keep profiling out of ordinary operation and leave the safety event poll unchanged. Node.js 24 belongs to GitHub action execution, not the Python/Tk desktop runtime. Track the wider older hardware resource audit as the next maintenance batch.

## November 8, 2026. Shared XP desktop core

Build the maintained desktop code for the official private Python 3.4.4 runtime instead of packaging the limited legacy listener as a full application. Explicit compatibility modules cover language and standard library differences. Native SAPI, WinMM and serial adapters remain behind the shared coordinator. Official runtime installers, pure QR dependencies, CA data and the XP compatible setup compiler are hash pinned. The native launcher imports only kernel32 and user32 and declares an XP subsystem minimum. Installation is account local and architecture specific.

Keep existing modern installer filenames for updater compatibility and add descriptive release asset labels plus a managed download table. XP update selection uses separate XP filenames. The older source kit remains available as a developer artifact. Hosted interpreter and installation checks do not replace named XP VM or physical acceptance, especially for audio drivers, USB interfaces and process or cable failures. Stable XP packaging remains blocked pending approved legal text and the corresponding installer presentation review.

## November 8, 2026. Immediate filters and conservative mode inference

Use one selection policy for the spot list and speech. Remove the desktop All received bypass. Infer a missing mode only from reviewed single mode frequency segments and leave mixed or conflicting reports Unknown. Require explicit Include unknown even when no particular mode is selected. Use the common regional CW subset documented in mode_inference.md and do not label shared phone or digital segments as a particular mode.

Filter checkboxes and selectors save immediately without reconnecting the source or applying unrelated connection/radio edits. Valid text edits save after a short pause. Loading a preset activates it atomically. Unchecking the last choice saves None rather than accepting everything. This supersedes the staged filter editor decision. Existing output start/stop, queue, age, repeat and RF controls remain separate.

## November 8, 2026. Ubuntu desktop package

Reuse the maintained desktop core rather than a separate Linux shell. Build the first amd64 Debian package on Ubuntu 22.04 with a private Python 3.12 runtime and verify installation on 22.04 and 24.04. System dependencies stay package managed. eSpeak NG supplies offline WAV rendering; Secret Service protects remembered credentials. Preserve shared filtering, output coordination and startup RF behavior. Linux serial paths and native CA certificates replace Windows platform choices. Package updates request administrator authentication after shared download verification. ARM, other distributions and actual radio acceptance remain separate work.
