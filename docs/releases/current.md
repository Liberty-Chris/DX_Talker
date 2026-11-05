DX Talker 0.2.0a3 announces frequency before callsign: “New DX on. Frequency. Callsign.” A shared kHz/MHz selection converts both spoken frequency and live rows without changing the received data.

Speech controls are grouped into compact sections. Only the selected voice provider's settings are shown, and preview controls are at the top. Connect and Disconnect become one control: neutral Connect, accented Connected and red Disconnect on hover or keyboard focus. Clicking an active connection stops it; a pending connection can be cancelled. Local listening has a matching Listening and Stop listening toggle. Stopping local audio preserves the cluster feed and live rows.

Cluster login handling now recognizes prompts followed by banners in the same network read, fragmented ANSI sequences and padded prompts. The connection status distinguishes an open socket, a recognized login and valid incoming spots. Failed sockets close before retrying.

Update checks distinguish DNS, TLS verification, timeouts, HTTP errors and GitHub rate limiting. Successful checks show the installed version and channel and explain when a preview requires Pilot. Network access alone does not prove that an update request succeeded.

Profiles and settings are retained. Existing frequency filters and history remain in kHz. Automatic output remains disabled on startup and recovery.
