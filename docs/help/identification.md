# Station identification

## CW ID

Enter the complete identification in CW ID text. Supported characters are letters, digits, spaces, slash, period, dash, question mark and equals. Text can contain up to 120 characters and generated audio must fit the transmit duration limit.

Set CW speed from 5 to 50 words per minute and tone from 300 to 1500 Hz. Preview CW locally plays audio Morse through the local preview device without asserting serial PTT. This feature does not directly key a radio's CW input.

## Voice ID

Enter Voice ID text and select Speech or WAV as the source. Speech uses the provider selected in Speech. Windows System.Speech is the built in default, with optional Piper support. Voice and delivery controls are in Speech.

For WAV, browse to an uncompressed 16 bit PCM recording, mono or stereo, with a sample rate from 8 to 96 kHz and duration no longer than 120 seconds. It must also fit your maximum transmit time. Missing or invalid WAV audio stops output with an error; the app does not silently substitute another ID.

Use Preview voice locally and listen to the complete result. Voice ID text is spoken as written. Live spot callsigns are spelled using phonetics and frequency digits.

## ID policy

CW sends only the CW ID. Voice sends only the selected voice ID. Alternate starts with CW and alternates CW and voice on subsequent IDs. Both sends CW followed by voice in one transmission with a short gap. Both requires a mono 22050 Hz PCM16 WAV when using a recording.

The interval can be set from 1 to 30 minutes. The default is CW every ten minutes while RF is enabled. Configure an interval and text appropriate to your station's operating policy.

Enable RF begins with an ID, including when no cluster is connected. Due IDs take priority over queued spots. Send ID now requests an ID immediately. Timing for the next scheduled ID starts after the previous one completes. No automatic IDs transmit while RF is disabled.

An ID failure disables automatic RF output. Correct the problem, preview the ID and enable RF deliberately when ready. The pilot does not add a separate final ID when output is stopped.


## Compact controls

IDs groups CW identification, Voice identification and ID schedule into compact sections. Text fields have room for a station ID, with short numeric inputs for speed, tone and interval. Each voice source shows only its relevant text or WAV path; switching sources preserves the entered values. The WAV path scrolls horizontally and has a Browse button. Each ID section includes its local preview action.

## Independent schedules and voice pauses

Independent policy enables both schedules without mixing their audio. Interval controls CW; Voice interval controls the spoken ID or recorded voice message from one to 120 minutes. Both are initially due when RF is enabled. CW is selected first when both are due. Each schedule advances only after its own transmission succeeds. Spots remain behind due IDs. A voice message that cannot fit within the CW interval is rejected before keying. All normal radio, receive hold, watchdog and stop behavior applies. Choose intervals appropriate to the station's identification requirements; this setting does not establish regulatory compliance.

In generated voice ID text, place the cursor between phrases, choose Pause (seconds) and Insert pause. The button inserts a marker such as `[pause 2s]`. That marker creates silence rather than speaking the word pause. `[pause]` means one second and `[pause 500ms]` means half a second. Individual markers accept zero to ten seconds and total speech remains bounded. Ordinary spaces and underscores are not pause controls. Other text is treated as text, not executable SSML.

Windows speech, Piper and Recorded packs honor the plan. A recorded pack must contain every spoken word or a matching recorded phrase; use a WAV ID for a custom message not covered by the pack. Online ElevenLabs retains the pauses. Long or leading pauses can be assembled locally using separate service requests for the spoken phrases, so these requests can consume additional shared testing allowance. No automatic billed retries are added. A selected WAV already contains its timing and ignores text markers.
