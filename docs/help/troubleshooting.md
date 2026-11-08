# Troubleshooting

## No audio devices or COM ports

Connect the interface and choose Refresh audio and serial devices. If running from source, install requirements.txt into the same Python environment used to launch the app. Use a uniquely named output if duplicate device names are reported.

## Connected but no spots

Check the cluster hostname, port and callsign. The supplied example is a TCP/Telnet connection, not a web URL. The cluster may be awaiting a different login response or may be quiet. Read the Source console and use the visible command input if the login procedure requires another command. For a password, use the dedicated password field and reconnect. Its eye button reveals the value for checking. Known secrets and command echoes are redacted from the console.

For HTTPS, confirm the feed uses the documented array format and has current timezone aware timestamps. HTML pages and other JSON schemas are not accepted. Redirected URLs must be replaced with the final direct feed URL.

## Cannot enable RF

Choose a radio audio device, configure serial PTT if used and fill the ID fields required by your policy. Save and apply before enabling. A connected source and a supervision checkbox are not required. RF uses saved settings, so pending edits do not change the selected device until applied. Wait for Idle if output is stopping or a preview is still playing.

A local preview must finish before enabling. Wait for Idle after stopping output. The sample spot loader only supports local preview and does not make a live source ready.

## Voice synthesis fails

For Windows, check that speech support and the selected voice are installed. For Piper, check the executable, model and matching configuration paths and see Listening and accessibility. Choose a blank voice to use the default. Speech is rendered before keying. A synthesis failure disables RF and leaves PTT unasserted.

## WAV fails

Use uncompressed PCM16 WAV audio with a supported rate and channel count. Both ID policy requires mono 22050 Hz. The app does not resample a recording for the selected audio device. Convert the recording or choose a compatible device and format.

## Audio reaches the wrong place

Check Local preview output and Radio audio output separately. The app never intentionally changes to a default device when the selected one is unavailable. If a device name changed, refresh and select it again.

## No PTT

VOX does not drive a PTT line. Configure radio or interface VOX separately or use supported serial wiring with RTS or DTR. Check COM port and polarity. CM108 HID and CAT require future support.

## Output does not stop

Use STOP ALL OUTPUT. If the hardware remains keyed, stop transmission using the station's physical controls. The app attempts serial release but cannot override failed hardware or a forced process termination. Verify release behavior on your actual interface before normal use.

## Settings do not apply

Stop output and wait for Idle, then save and apply. Passwords and tokens are session only. Settings are at %LOCALAPPDATA%\DXTalker\settings.json. If the file is unreadable or from an unsupported schema, move it aside to start with defaults. Keep a copy for investigation.

## Report a problem

Include the version shown in Help and Info, Windows version, interface model, audio device name, PTT mode, source type and the application activity messages. Do not include passwords, tokens or private source URLs. Source and packaged smoke reports describe automated checks only, not physical radio compatibility.


## Intermittent cluster sign in

Read the source state and session console. Connected means the socket is open. Signed in with no spots may mean a quiet or filtered cluster; a valid received spot is still needed before enabling automatic output. The client handles prompts across read boundaries and processes prompts followed by banners in the same read. Network or login failures stop output and retain the bounded retry policy. A duplicate session can mean another program is using the same callsign on that node.

## Update check reports a connection error

An internet connection does not establish that the GitHub update request succeeded. The application now distinguishes public API rate limits, HTTP responses, DNS, TLS verification and timeouts. Check the reported category and try Release page for a manual download. The Pilot channel includes preview releases. Stable may have no applicable release during pilot testing.


## Audio playback stopped or RuntimeError

Older builds can show only RuntimeError for several unrelated output failures. Export a diagnostic report from History / Updates and include the approximate time and whether the failure occurred during local listening, a preview or RF output. The short warning alone does not establish a device or speech provider cause.

Version 0.2.0a10 fixes a confirmed completion race: the stream could finish after the app’s completion wait timed out but before it queried native stream state. The app now accepts that normal completion notification. After all samples have been queued, a missing notification receives at most 250 ms of grace, with cancellation and maximum duration still enforced. An early stop remains a failure, and the app never assumes that queued samples were played merely because they were submitted.

Known playback failures show readable messages. Their exported cause codes are audio_stream_stopped for an inactive stream before all frames were queued, audio_finish_unconfirmed for missing completion confirmation, audio_stream_fault for a reported audio stream fault and audio_incomplete for completion with missing frames. Reports include numeric frame counts, sample rate, channels and local/radio route. Queued frames measure submission to the audio API, not confirmed physical sound output. Reports do not include audio samples or device names.

For a genuine device failure, check the selected output, USB connection and Windows sound settings. Refresh devices, select the intended local or radio output again and save and apply while output is stopped. Try a local preview before resuming. No automatic retry, default device switch or RF reenable occurs. Actual device faults still stop output and attempt PTT release.

## Quiet input reported as faulty

A receive level below the threshold means the measured samples were quiet. It does not mean the input stream is healthy. No current measurement, no samples, inactive device and stale samples are separate states. Use Test receive input to inspect the input health explanation. Check the exact selected device, permissions and other audio apps, then reopen the test. See [Radio audio and PTT](radio.md). Do not lower the threshold to repair a device fault.

## Output errors and delays

Runtime output faults now appear in a dismissible in app notice and Activity, preserving the UI event loop instead of blocking it behind an error dialog. Output still stops and must be deliberately restarted. Export the local diagnostic ZIP from History / Updates if a fault recurs. It includes fixed receive input fault codes and speech preparation/audio duration measurements without synthesis text, provider credentials or spot comments. There is no automatic upload.

An older report from 0.2.0a8 contained audio stop errors along the completion path addressed in the subsequent playback timing correction. Its stall traces were inside modal error dialogs. That does not establish the cause of a new version's fault. Include the current version and a fresh export when reporting a recurrence.


## Slow desktop navigation after a14

A14 introduced extra rendering work for rounded controls and panels. A15 reduces the image tiling work and skips unchanged state button updates. The rounded appearance is retained. This correction does not require resetting settings or changing speech providers.

If navigation remains slow after updating, export a fresh diagnostic ZIP from History / Updates. Include the app version, Windows version, approximate time, whether a cluster was connected and whether local listening or RF output was running. Mention whether the delay occurs immediately after launch or develops over time. Existing diagnostics capture long event loop stalls but may not record every shorter navigation delay. No diagnostics are uploaded automatically.


Build verification now checks startup, tab switching, scrolling and idle CPU use before publication. These checks do not run continuously on your PC and do not replace the diagnostic export if a slowdown recurs. The Node.js runtime used by GitHub Actions is part of build automation; the Windows application runs Python and Tk and does not require Node.js.
