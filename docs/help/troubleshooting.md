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
