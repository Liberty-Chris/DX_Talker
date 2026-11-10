# Speech and listening access

Choose Speech to adjust delivery. Windows speech remains the default provider. Select an installed voice or leave it blank and choose Any, Male or Female as a voice preference. A named voice overrides the preference. Availability depends on installed System.Speech voices; a preference cannot install a missing voice.

Speech speed runs from minus 10 to 10. Zero is normal. Use the spin controls or type a value. Pause between letters and digits accepts 0 to 1000 milliseconds. Zero retains natural word spacing. Pause between announcement groups accepts 0 to 3000 milliseconds. The included sections and their order come from Announcement format in Announcements. Units, when enabled, stay attached to frequency. These pauses affect spot announcements, not freeform voice ID text or recorded WAV audio.

Choose Preview sample speech to hear a portable callsign and decimal frequency with the current settings. Save and apply changes before listening. Speech is generated before radio keying; excessive duration is rejected by the configured transmission limit.

## Optional neural voices

Piper is an optional local neural speech provider. Windows speech remains available without installing it. DX Talker does not bundle a Piper runtime or voice model. Piper synthesis runs locally; ElevenLabs is the separate online option described below.

Install a Piper CLI separately from the [Piper project](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/CLI.md). For example, in a separate Python environment install piper-tts and use its voice downloader to obtain an English voice. Select the resulting piper.exe and a local .onnx model using Browse. Keep the matching .onnx.json file beside that model. Review the runtime and voice licenses when selecting a model; they are separate from the DX Talker license.

Select Piper as Speech provider and preview a sample. The model determines the speaker and voice character. Windows voice and gender controls apply only to the Windows provider. Piper speed uses the same control, with positive values faster. Speech plans insert the requested PCM silence between groups and characters. Character spacing may require many CLI invocations and can substantially increase preparation time. Zero character spacing is the best starting point. Synthesis has a two minute bound and remains cancellable. No automatic fallback substitutes a different provider after failure.

Piper output must be mono PCM16 WAV. DX Talker normalizes its sample rate to 22050 Hz for the shared output path. The adapter has synthetic fixture coverage and a real model render check. Actual voice quality and speed still need a listening test on the operator's computer. DX Talker disables ONNX Runtime telemetry in the Piper subprocess before it starts.

## Live local listening

Choose your speakers or headphones as Local preview output in Audio / PTT. Connect a source and choose Listen locally or press F8, including before the first spot arrives. The active control reads Listening and offers Mute when hovered or focused. Clicking it or pressing F8 mutes local audio immediately while the source remains connected and filtered live spots keep populating. It then reads Unmute. Current and queued local announcements are cancelled and muted arrivals are displayed without generating speech. A gray M beside the callsign identifies these intentional muted rows; open their announcement details for the reason. Unmute announces only new matching spots and never replays a muted backlog. Existing age, repeat and listening filters still apply. Local listening never constructs a serial PTT adapter or schedules station identification. Escape or Stop all output remains a full output stop.

Local listening and RF can run together through separate audio destinations. With RF enabled, local speakers monitor the same spots and identification as the radio. Local mute or volume zero silences speakers without stopping RF or discarding its queue. Monitoring resumes on the next transmission after Unmute. Disabling RF leaves local listening active. Stop all output, Escape and source loss stop both routes. Restart and automatic reconnect never enable RF. Select different local speakers and radio audio devices for simultaneous use. An output shared with a VOX radio can still key that radio during local listening.

## Navigation and visibility

F6 previews the selected spot while output is stopped. F8 starts local listening or toggles its mute state. Escape stops all output. Alt+C focuses a visible command input. At compact window heights, Cluster commands or Alt+C opens Source and scrolls to its command field. Ctrl+Tab and Ctrl+Shift+Tab move between pages. Tab and Shift+Tab move through controls. Enter sends a command from its input field.

Choose High contrast in Appearance for white text on a dark background. Speech also contains Interface text size, from 10 to 18 points. Save to apply. Settings pages scroll vertically. At small window heights the header shrinks and the Live spots activity panel, filter summary and duplicate command bar are hidden to preserve table space. Cluster commands remains available above the table controls. Enlarge the window to see it. Larger text can require a wider window.

These controls improve keyboard and listening access. Tkinter screen reader support varies. NVDA, Windows Narrator, keyboard focus order and enlarged text need acceptance testing with visually impaired operators before claiming complete assistive technology support.


## Windows Piper setup example

Install Python 3.12 x64 if it is not already available. This is separate from the Python bundled inside DX Talker. In PowerShell, run:

```powershell
$piperHome = Join-Path $env:LOCALAPPDATA 'DXTalker\Piper'
py -3.12 -m venv "$piperHome\venv"
& "$piperHome\venv\Scripts\python.exe" -m pip install 'piper-tts==1.8.0'
$env:ORT_DISABLE_TELEMETRY = '1'
& "$piperHome\venv\Scripts\python.exe" -m piper.download_voices --download-dir "$piperHome\voices" en_US-lessac-medium
```

In Speech select Piper. Browse to %LOCALAPPDATA%\DXTalker\Piper\venv\Scripts\piper.exe as the executable and %LOCALAPPDATA%\DXTalker\Piper\voices\en_US-lessac-medium.onnx as the voice model. Keep its .onnx.json configuration beside it. Use Speech speed 0, character pause 0 and group pause 450 for the first comparison. Choose your computer speakers as Local preview output, stop output and choose Preview sample speech.

Version 0.2.0a2 sets the telemetry environment switch for every Piper launch. When trying the older 0.2.0a1 build, launch DX Talker from the same PowerShell session after setting the switch so it inherits that setting:

```powershell
& "$env:LOCALAPPDATA\Programs\DXTalker\DXTalker.exe"
```

Downloading a different voice and selecting its ONNX file changes voice character. The [Piper voice samples](https://rhasspy.github.io/piper-samples/) help compare options. Runtime and voice downloads need internet access; rendering uses the installed local files. No cloud speech account is required.


## Frequency first announcements

A spot is spoken as “New DX on”, then frequency and units, then the phonetic callsign. For example, 14025.5 kHz becomes “New DX on. One four zero two five point five kilohertz. Whiskey Bravo four India Uniform Yankee.”

Frequency units can be kHz or MHz. The selection is shared by Speech and the unit toggle in Live spots. Save and apply it like other settings. In MHz, that same spot is 14.0255 MHz and is spoken as “one four point zero two five five megahertz.” Decimal conversion preserves the received value, including leading fractional zeros. Trailing fractional zeros are omitted.

Existing live rows are reformatted when settings are applied. Received data, history files, duplicate matching and frequency filter limits remain in kHz. Selecting MHz does not retune a radio or change those limits.

The Speech page groups common delivery settings separately from the selected provider and interface options. Only the selected provider's controls are shown. Preview sample speech and Speech setup and shortcuts remain at the top of the page. Fields have bounded widths rather than expanding across the window.

The listening toggle uses already applied settings. It does not save pending edits or reconnect the source. Save and apply audio or speech changes before starting. When stopping an in progress clip, the control briefly reads Stopping until playback cleanup finishes.

## Announcement policy controls

Announcements groups Announcement format, Timing and repeats and RF supervision into compact sections. Frequency limits are on Source in the listening editor under Location and advanced filters and always use kHz. Timing fields are in seconds, with supported ranges beside them. Optional receive audio transmit hold is configured in Audio / PTT; an acknowledgement checkbox no longer gates RF. Editing, validation and Save and apply behavior are unchanged.


## Announcement format

Open Announcements to choose which sections are spoken and in what order. Frequency first preserves the original “New DX on. Frequency with units. Callsign.” format. Callsign first uses “New DX. Callsign. Frequency with units.” Callsign + frequency omits the intro. Choose a preset as a starting point; further edits show Custom.

Each section has an include checkbox and Up and Down buttons. Use them with the mouse or Tab and Enter/Space. Unchecking a section preserves its text and position for later use. Intro offers New DX and New DX on, or type your own single line of up to 80 characters. At least one section must be included; an included intro cannot be blank. Invalid choices show guidance in the example and cannot be saved or played.

Speak units belongs to Frequency and moves with it. Uncheck it to omit kilohertz or megahertz without changing the number. Frequency units in Speech or Live spots still controls decimal placement. Excluding Frequency also excludes its units; the units choice is retained when the section is restored. Source records, history and filter limits remain in kHz.

The sentence example updates immediately with a portable callsign and a decimal frequency. Actual callsigns are spoken phonetically. Listen to example uses the pending format with your saved voice, pauses and local preview output. It does not save other edits, reconnect a source or assert serial PTT. Stop active output and wait for Idle before previewing. A shared local/radio audio device can still key a VOX radio, so the usual shared device confirmation applies.

Save and apply makes the format active for RF, live local listening and spot previews. Editing the format stops active output; it never resumes automatically. These controls do not change CW IDs, freeform voice ID text or recorded voice IDs.

## Listen before the first spot

Listen locally can be armed before connecting or before a cluster emits its first spot. Select and save a local audio output, then enable listening. Only newly received validated spots are spoken; the first one is eligible immediately. If listening is already armed when you explicitly press Connect, it is restored before the source worker starts, so the first valid packet is not lost to a connection/listening race. Connecting still applies the edited settings. RF is never preserved this way. Source loss still stops listening and automatic reconnection does not silently resume it.

## Recorded voices

Recorded uses pre-generated local WAV assets instead of system speech or live model inference. Select a parent voice pack folder and a named voice. Existing providers remain available. Recorded rate is fixed at generation time; character and group pauses remain configurable. Unknown custom intro/ID words produce an error asking for added assets or another provider. See the repository's recorded voice pack guide for generation, installation and per-model licensing.


## Shared ElevenLabs pilot speech

Choose ElevenLabs in the Provider menu to use the shared DX Talker pilot account. No API key is required in the app. Refresh voices to load the enabled choices or leave Voice blank for the service default. Save and apply and use Preview sample speech with local speakers before enabling RF. The model and allowance are managed by the pilot administrator. Speed is fixed by the service while character and group pauses remain configurable.

This online provider sends announcement and speech ID text to the DX Talker speech service and ElevenLabs. Synthesis completes before PTT is keyed. A network, quota or service failure stops output with a message. There is no automatic provider fallback or billed retry. Choose Windows, Piper or Recorded if the service is unavailable. Builds made before the service address is configured show setup guidance instead of asking testers for a key.

## Generate an ElevenLabs recorded voice

Choose Generate ElevenLabs recorded voice in Speech to create offline assets through the same shared pilot service. No key or model field is shown. Refresh voices to choose an enabled voice, or leave blank for the service default. Choose a readable label, parent voice pack folder and a new pack name. The current custom announcement intro is included as a phrase.

Generate voice pack uses the shared testing allowance. The screen shows the clip count and approximate text size first. The standard vocabulary contains 77 clips; a custom intro may add one. No request is sent merely by opening the window. Completed clips are kept in a partial folder on cancellation. Retry with the same folder, name, voice, label and intro to reuse verified clips. A request already in progress can still use allowance. Completed packs are never overwritten.

When finished, choose Use this voice, then Preview sample speech. The provider becomes Recorded. Playback uses local WAVs without an internet connection or further API requests. Windows speech and Piper remain available. Generated packs retain voice and model provenance; sharing rights depend on the account plan and voice permissions. Arbitrary ID text may require a separate WAV or additional assets.

The owner enters the ElevenLabs account key on the hosting server once, outside the public website folder. It is not included in app settings, QR transfers, logs or installers. The repository’s shared speech service guide covers DreamHost setup and build configuration.


If Refresh voices or the service check reports website access blocked with HTTP 403, contact the pilot administrator about website security filtering. That failure does not establish that a voice or model is invalid. The app identifies itself as DXTalker rather than using Python’s default client identifier. An explicit service voice/model denial during synthesis instead asks for refreshed voice choices.

## Android listening interface

Android uses permanent Listen, Clusters and Settings navigation. The audio controls stay visible on every page. Listen arms speech before the first spot; Stop listening closes the mobile session. Mute cancels current and queued speech and discards muted arrivals. Pause holds current and new speech until Resume, within queue and age limits. Both keep the feed connected. Changing pages or applying filters does not reconnect the cluster. Selecting another saved cluster switches an active session to that profile and clears old results.

Android Back returns through detail pages and then to Listen. Form drafts and the current page survive activity recreation and remain in memory until the activity is discarded. Save profile stores a profile without selecting or connecting it; Use this cluster selects it. Remove offers Undo. Existing QR collection and file imports are under Clusters, with reviewed complete collection import and credential exclusion preserved.

Settings includes System, Light, Dark and High contrast appearance, local diagnostics and a visual announcement builder. Choose intro, callsign and frequency sections, move them up or down and optionally speak units. Announcement changes save automatically for future speech without reconnecting or interrupting current playback. Test announcement uses Android system speech. Android engine and voice installation choices are available through Open speech settings. This mobile batch does not add paid online speech or radio transmission.

## Preparation time and installed packs

Windows speech now reuses one System.Speech process for consecutive announcements, removing repeated PowerShell and synthesizer startup. The first render can still take longer. Cancellation, failure and application shutdown close the process. The actual resolved Windows voice name appears after preview or playback, even when the Voice field is blank. A Male/Female preference is a selection hint, not a voice name or guarantee of identical voices on two computers.

Recorded playback retains a bounded cache of verified WAV assets. It avoids both system synthesis and online requests at playback time. DX Talker discovers installed packs in its own voices folder, a selected custom folder and the bundled assets/voices folder. Advanced storage options reveal paths when needed. No new voice packs are bundled in this update; selected packs can be included in a later verified build.

Generate ElevenLabs recorded voice chooses an application managed destination automatically. Refresh/choose an allowed voice, review the label and intro, then Generate. The status reports progress and Use this voice selects the finished pack. The selection saves automatically; preview when ready. Advanced storage options are optional. Interrupted generation can resume using the same settings; completed packs are not overwritten. Generating a pack uses the shared service allowance. No key is requested from testers.

Local Windows generation and recorded playback are useful for busy feeds. Online ElevenLabs includes service/network/provider latency and cannot guarantee contest rate throughput. See [Keeping up](listening_filters.md) for queue age, preparation timing, zero additional gap and catch up controls. Filtering reduces the number of announcements; no speech engine can speak an unlimited incoming feed in real time.

Voice ID pause controls and independent CW/voice schedules are described under [Station identification](identification.md).

Desktop buttons and settings panels have rounded surfaces in every appearance mode. Keyboard focus, Enter and Space activation, disabled states and the connection/listening/RF state colors remain available. Outer window borders follow the operating system. Announcements aligns its format, timing and RF supervision panels. The listening filter editor has its own Filters page.


On Android Listen, use the kHz/MHz control beside Recent spots. It updates retained row frequencies and future speech without reconnecting the cluster. Pending/current speech is stopped when units change, and displayed history is not replayed. Frequencies and band/license rules stay in canonical kHz internally. Applying a listening preset can also change units; its value is retained when other filter controls are edited.

On the XP pilot, Windows speech uses installed SAPI 5 voices through a persistent local worker rather than requiring PowerShell. Voice selection, speed and pauses remain available. Speech is rendered to PCM before radio keying. Installing an external Piper build requires one that is compatible with XP; the current modern Piper download is not an XP compatibility claim. Recorded packs use the same portable PCM assets.

## Ubuntu system speech

On Ubuntu, eSpeak NG replaces the Windows provider. It renders offline WAV audio through the same coordinator, including character/group pauses and speed controls. A named voice overrides the gender preference. Piper requires its Linux executable and local model. Recorded packs and configured ElevenLabs speech remain available. See [Ubuntu desktop](ubuntu.md).

## Desktop live row checks

Connecting to a cluster admits matching live rows regardless of local listening or RF state. The admission still applies listening filters, timestamp and repeat rules. Gray D marks display only rows received with audio off or zero RF spot volume. Audio must be enabled before new arrivals are queued for speech. Green checks confirm completed playback. Red checks open a reason for an admitted row that did not complete; queued rows have a neutral marker. Gray M means intentional local mute with no queued speech. Select a row and press Enter for text details. Rejected spots is a separate review of incoming rejections. Manual samples use Sample preview instead of filling the live list. See [Listening filters and receipts](listening_filters.md).

## POTA, FOTA and SOTA announcement wording

In Filters on desktop or Android, turn on Use POTA / FOTA / SOTA wording during mixed listening to announce an accepted tagged spot as activity, mode, frequency and callsign. For example: POTA. SSB. One four point two five megahertz. Whiskey Bravo four India Uniform Yankee. The switch starts off. When the activity selection contains only POTA, FOTA or SOTA, the same wording is used automatically even with the mixed listening switch off. An empty activity selection or one including General is mixed listening. Selecting None admits no spots.

This changes wording only. Band, mode, activity, frequency limits, license and location filters remain in force. Stop, mute, age, repeat, queue and radio controls also remain unchanged. Ordinary spots retain the configured DX format. Tagged spots use the fixed activity order instead of custom introduction, section visibility and section ordering. Existing kHz/MHz and spoken unit choices remain respected.

Only recognized activity tags are spoken, not arbitrary comments. If several tags are present, announce POTA, FOTA and SOTA in that order, omitting absent tags. Use the identified mode and omit it when Unknown. The existing US inference and explicit mode evidence rules determine that mode. Voice synthesis uses “poughta” for POTA, “phota” for FOTA and “sota” for SOTA. Displayed labels and spot details keep the normal activity acronyms. Newly generated recorded packs include these spoken phrases. Existing recorded packs continue spelling the acronyms with their letter assets; generate a new pack to use the revised pronunciation. Mode acronyms still use the existing delivery.

The switch saves immediately with listening choices and is included in presets and profile/QR transfers. Update both receiving and sending apps to a24 or later before transferring this new preference. Older files without the field remain supported and default it to off.

Local mute is session state and is not saved across app restarts. Explicit Connect preserves an already armed local session's mute state before the source starts. Source loss and Stop all output still stop the session; restarting output remains explicit. Muting does not alter radio volume or RF controls. With RF off, the local volume slider at zero also keeps matching display rows as muted. With RF on, local mute and zero volume leave radio announcements active. A selected local spot preview is still available while muted after current audio has finished stopping. Muted idle listening does not request Windows keep awake on its own.

The beta uses scoped previews, automatic speech preference saving and preserved radio drafts. See [Operation and saving](usability.md) for exact transitions and recovery.
