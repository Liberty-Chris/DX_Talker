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

Independent policy enables both schedules without mixing their audio. CW / policy interval controls CW; Voice interval controls the spoken ID or recorded voice message from one to 120 minutes. Both are initially due when RF is enabled. CW is selected first when both are due. Each schedule advances only after its own transmission succeeds. Spots remain behind due IDs. A voice message that cannot fit within the CW interval is rejected before keying. All normal radio, receive hold, watchdog and stop behavior applies. Choose intervals appropriate to the station's identification requirements; this setting does not establish regulatory compliance.

In generated voice ID text, place the cursor between phrases, choose Pause (seconds) and Insert pause. The button inserts a marker such as `[pause 2s]`. That marker creates silence rather than speaking the word pause. `[pause]` means one second and `[pause 500ms]` means half a second. Individual markers accept zero to ten seconds and total speech remains bounded. Ordinary spaces and underscores are not pause controls. Other text is treated as text, not executable SSML.

Windows speech, Piper and Recorded packs honor the plan. A recorded pack must contain every spoken word or a matching recorded phrase; use a WAV ID for a custom message not covered by the pack. Online ElevenLabs retains the pauses. Long or leading pauses can be assembled locally using separate service requests for the spoken phrases, so these requests can consume additional shared testing allowance. No automatic billed retries are added. A selected WAV already contains its timing and ignores text markers.

ID edits are radio drafts until Apply radio changes. Local ID previews use only their relevant displayed fields and never apply source edits. WAV selection reports its format before a preview. See [Operation and saving](usability.md).

## Scheduled voice IDs

Scheduled voice IDs adds up to 20 named messages alongside the existing station ID policy. Use + Add voice ID, give the message a name and assign Speech text or a WAV recording. Edit changes the selected message, Remove deletes it from the draft and Preview locally uses the selected message without PTT. Apply radio changes activates the collection. Existing station ID text and intervals are preserved when upgrading.

Speech uses the provider and voice chosen in Speech. Choose an installed system voice or Piper for arbitrary offline messages. Recorded packs require the message words or a matching recorded phrase; a WAV recording can hold a custom message. Text supports the same pause markers as the primary voice ID. Recordings use the same PCM16, sample rate and duration requirements as other voice IDs. Enabled WAV messages are checked before RF can start. A generated message is checked before keying and must fit both the maximum transmission duration and the required ID interval.

Interval schedules repeat every 1 to 10080 minutes, starting one interval after RF is enabled. Daily schedules use one or more times each day. Weekly schedules use selected weekdays. Monthly weekday schedules choose the first, second, third, fourth, fifth or last occurrence of one weekday. Monthly date schedules choose a day number. Once schedules choose one date. Calendar schedules accept up to 24 distinct times in 24 hour HH:MM format. Optional starting and ending dates limit the schedule. A daily window limits permitted times and interval dispatch to the selected same day window.

For a club meeting reminder twice on the first Tuesday of each month, choose Monthly weekday, select Tuesday, set occurrence to 1 and enter times such as 12:00, 17:00. The next planned time appears beside the message. Interval previews show the planned delay from enabling rather than a running countdown. All times use the computer's local clock and timezone. Set its timezone and clock correctly before enabling RF. A nonexistent time during the spring daylight saving change is skipped. A repeated fall clock time plays once per running application session.

Due station IDs take priority, followed by scheduled voice IDs and then spots. Every transmission uses the same receiver quiet gate, audio routing, PTT owner, maximum duration and Stop control. Scheduled voice messages wait their turn; they cannot interrupt another transmission. If the channel stays busy beyond the message's configured grace period of 1 to 60 minutes, that occurrence is skipped and recorded in Activity and diagnostics. Messages that coincide are considered in collection order. A fifth weekday or day 31 is skipped in a month without that occurrence.

RF must be enabled. Enabling after a scheduled time does not replay missed messages. Restarting the application never enables RF or catches up on missed IDs. Stopping, source loss or an output fault disables RF under the existing policy. An opted in source reconnect can restore a previously enabled RF session with a required ID first, but it does not catch up on calendar messages missed during the outage. A failed scheduled ID also stops RF with an error. Correct the problem and enable RF deliberately. Do not rely on this application as the sole identification system until timing, receiver behavior, audio and failure recovery have been checked on the actual repeater and computer.
