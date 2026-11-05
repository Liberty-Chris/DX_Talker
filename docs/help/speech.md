# Speech and listening access

Choose Speech to adjust delivery. Windows speech remains the default provider. Select an installed voice or leave it blank and choose Any, Male or Female as a voice preference. A named voice overrides the preference. Availability depends on installed System.Speech voices; a preference cannot install a missing voice.

Speech speed runs from minus 10 to 10. Zero is normal. Use the spin controls or type a value. Pause between letters and digits accepts 0 to 1000 milliseconds. Zero retains natural word spacing. Pause between announcement groups accepts 0 to 3000 milliseconds. The groups are “New DX on”, the phonetic callsign and the frequency including kilohertz. These pauses affect spot announcements, not freeform voice ID text or recorded WAV audio.

Choose Preview sample speech to hear a portable callsign and decimal frequency with the current settings. Save and apply changes before listening. Speech is generated before radio keying; excessive duration is rejected by the configured transmission limit.

## Optional neural voices

Piper is an optional local neural speech provider. Windows speech remains available without installing it. DX Talker does not bundle a neural runtime or voice model and does not send text to a cloud service.

Install a Piper CLI separately from the [Piper project](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/CLI.md). For example, in a separate Python environment install piper-tts and use its voice downloader to obtain an English voice. Select the resulting piper.exe and a local .onnx model using Browse. Keep the matching .onnx.json file beside that model. Review the runtime and voice licenses when selecting a model; they are separate from the DX Talker license.

Select Piper as Speech provider and preview a sample. The model determines the speaker and voice character. Windows voice and gender controls apply only to the Windows provider. Piper speed uses the same control, with positive values faster. Speech plans insert the requested PCM silence between groups and characters. Character spacing may require many CLI invocations and can substantially increase preparation time. Zero character spacing is the best starting point. Synthesis has a two minute bound and remains cancellable. No automatic fallback substitutes a different provider after failure.

Piper output must be mono PCM16 WAV. DX Talker normalizes its sample rate to 22050 Hz for the shared output path. This adapter is covered with a synthetic CLI fixture; actual model quality and speed still need a listening test on the operator's computer.

## Live local listening

Choose your speakers or headphones as Local preview output in Audio / PTT. Connect a source, receive valid spots and choose Listen locally or press F8. Future eligible spots are announced locally using the same age, frequency, duplicate and spacing policies as radio announcements. Existing rows are not replayed. Local listening never constructs a serial PTT adapter or schedules station identification.

Local listening and RF transmission are mutually exclusive. Disconnect, source failure, settings edits and Escape stop output. Neither mode resumes automatically after restart or reconnect. An output device shared with a VOX radio can still reach and key that radio; the app asks before using a shared device.

## Navigation and visibility

F6 previews the selected spot while output is stopped. F8 starts local listening. Escape stops all output. Alt+C focuses the Live spots command input. Ctrl+Tab and Ctrl+Shift+Tab move between pages. Tab and Shift+Tab move through controls. Enter sends a command from its input field.

Choose High contrast in Appearance for white text on a dark background. Speech also contains Interface text size, from 10 to 18 points. Save to apply. Settings pages scroll vertically. At small window heights the Live spots activity panel is hidden to preserve table space. Enlarge the window to see it. Larger text can require a wider window.

These controls improve keyboard and listening access. Tkinter screen reader support varies. NVDA, Windows Narrator, keyboard focus order and enlarged text need acceptance testing with visually impaired operators before claiming complete assistive technology support.
