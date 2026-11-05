# Speech and listening access

Choose Speech to adjust delivery. Windows speech remains the default provider. Select an installed voice or leave it blank and choose Any, Male or Female as a voice preference. A named voice overrides the preference. Availability depends on installed System.Speech voices; a preference cannot install a missing voice.

Speech speed runs from minus 10 to 10. Zero is normal. Use the spin controls or type a value. Pause between letters and digits accepts 0 to 1000 milliseconds. Zero retains natural word spacing. Pause between announcement groups accepts 0 to 3000 milliseconds. The included sections and their order come from Announcement format in Announcements. Units, when enabled, stay attached to frequency. These pauses affect spot announcements, not freeform voice ID text or recorded WAV audio.

Choose Preview sample speech to hear a portable callsign and decimal frequency with the current settings. Save and apply changes before listening. Speech is generated before radio keying; excessive duration is rejected by the configured transmission limit.

## Optional neural voices

Piper is an optional local neural speech provider. Windows speech remains available without installing it. DX Talker does not bundle a neural runtime or voice model and does not send text to a cloud service.

Install a Piper CLI separately from the [Piper project](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/CLI.md). For example, in a separate Python environment install piper-tts and use its voice downloader to obtain an English voice. Select the resulting piper.exe and a local .onnx model using Browse. Keep the matching .onnx.json file beside that model. Review the runtime and voice licenses when selecting a model; they are separate from the DX Talker license.

Select Piper as Speech provider and preview a sample. The model determines the speaker and voice character. Windows voice and gender controls apply only to the Windows provider. Piper speed uses the same control, with positive values faster. Speech plans insert the requested PCM silence between groups and characters. Character spacing may require many CLI invocations and can substantially increase preparation time. Zero character spacing is the best starting point. Synthesis has a two minute bound and remains cancellable. No automatic fallback substitutes a different provider after failure.

Piper output must be mono PCM16 WAV. DX Talker normalizes its sample rate to 22050 Hz for the shared output path. The adapter has synthetic fixture coverage and a real model render check. Actual voice quality and speed still need a listening test on the operator's computer. DX Talker disables ONNX Runtime telemetry in the Piper subprocess before it starts.

## Live local listening

Choose your speakers or headphones as Local preview output in Audio / PTT. Connect a source, receive valid spots and choose Listen locally or press F8. The control changes to Listening with the appearance accent. Hovering or keyboard focusing it offers Stop listening in red. Click it again or press F8 again to stop local audio while the cluster remains connected and the live view continues receiving spots. Future eligible spots are announced locally using the same age, frequency, duplicate and spacing policies as radio announcements. Existing rows are not replayed. Local listening never constructs a serial PTT adapter or schedules station identification.

Local listening and RF transmission are mutually exclusive. Disconnect, source failure, settings edits and Escape stop output. Neither mode resumes automatically after restart or reconnect. An output device shared with a VOX radio can still reach and key that radio; the app asks before using a shared device.

## Navigation and visibility

F6 previews the selected spot while output is stopped. F8 toggles local listening. Escape stops all output. Alt+C focuses the Live spots command input. Ctrl+Tab and Ctrl+Shift+Tab move between pages. Tab and Shift+Tab move through controls. Enter sends a command from its input field.

Choose High contrast in Appearance for white text on a dark background. Speech also contains Interface text size, from 10 to 18 points. Save to apply. Settings pages scroll vertically. At small window heights the Live spots activity panel is hidden to preserve table space. Enlarge the window to see it. Larger text can require a wider window.

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

Announcements groups Frequency range, Timing and repeats and RF supervision into compact sections. Frequency limits always use kHz. Timing fields are in seconds, with supported ranges beside them. The busy channel limitation appears as guidance; an acknowledgement checkbox no longer gates RF. Editing, validation and Save and apply behavior are unchanged.


## Announcement format

Open Announcements to choose which sections are spoken and in what order. Frequency first preserves the original “New DX on. Frequency with units. Callsign.” format. Callsign first uses “New DX. Callsign. Frequency with units.” Callsign + frequency omits the intro. Choose a preset as a starting point; further edits show Custom.

Each section has an include checkbox and Up and Down buttons. Use them with the mouse or Tab and Enter/Space. Unchecking a section preserves its text and position for later use. Intro offers New DX and New DX on, or type your own single line of up to 80 characters. At least one section must be included; an included intro cannot be blank. Invalid choices show guidance in the example and cannot be saved or played.

Speak units belongs to Frequency and moves with it. Uncheck it to omit kilohertz or megahertz without changing the number. Frequency units in Speech or Live spots still controls decimal placement. Excluding Frequency also excludes its units; the units choice is retained when the section is restored. Source records, history and filter limits remain in kHz.

The sentence example updates immediately with a portable callsign and a decimal frequency. Actual callsigns are spoken phonetically. Listen to example uses the pending format with your saved voice, pauses and local preview output. It does not save other edits, reconnect a source or assert serial PTT. Stop active output and wait for Idle before previewing. A shared local/radio audio device can still key a VOX radio, so the usual shared device confirmation applies.

Save and apply makes the format active for RF, live local listening and spot previews. Editing the format stops active output; it never resumes automatically. These controls do not change CW IDs, freeform voice ID text or recorded voice IDs.
