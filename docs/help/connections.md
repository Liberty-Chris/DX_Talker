# Source connections

## TCP/Telnet clusters

Choose TCP/Telnet and enter a hostname and port separately. The supplied example is w4mr.ddns.net on port 7373. Enter your login callsign and a password only if the service requires one. Choose Connect.

The adapter recognizes common login, callsign, username and password prompts, including prompts received in several fragments or without a newline. It also handles basic Telnet option negotiation. The connection control shows Connected when the network socket is open. A recognized session prompt can show Signed in while a quiet cluster waits for its first spot. Receiving DX spots still requires a validated spot.

If the cluster needs a different response, use Manual response or cluster command. Commands are always visible, send one line and clear after sending. Enter sends the command too. The field is also available on Live spots. Commands and authentication responses are not written to history. The Source console shows the latest 15 incoming lines with known secrets and command echoes redacted. It remains session only and is never announced.

A network connection alone does not prove sign in succeeded. Waiting for a valid spot can also mean the cluster is quiet. W4MR's current prompts and access requirements have not been tested live in this project.

Plain TCP/Telnet does not encrypt the connection. Source login does not create a DX Talker account.

## HTTPS JSON

Choose HTTPS JSON and enter an HTTPS feed URL. An optional bearer token goes in the session password or token field. Polling is configurable with a minimum of 15 seconds. The app rejects redirects and embedded URL credentials.

The response must be a JSON array of at most 2000 spot records within 1 MiB. Each record needs dx_call, spotter, frequency_khz and time. Frequency is in kilohertz and time is an ISO timestamp including a timezone.

```json
[{"dx_call":"WB4IUY","spotter":"KT4BN","frequency_khz":"14025.5","time":"2026-10-31T12:34:00Z"}]
```

The timestamp must represent the actual spot time. The example above illustrates format only and will expire. Ordinary web pages and arbitrary provider JSON schemas are not supported.

## Disconnects

Connection failures disable RF and clear queued output. The source retries with increasing delays up to 60 seconds. Reconnect does not enable RF. Verify the connection and deliberately enable output when ready.

Changing source settings requires a new connection. Passwords and tokens remain in memory for the session and are not written to saved settings or the activity journal.


## Saved cluster profiles

Save profile stores a named connection with source type, hostname, port, callsign or SSID, feed URL and polling interval. The saved profile selector is available on Source and Live spots. Selecting a profile disconnects the previous source, stops output and clears the live view and console. Connect explicitly when ready. New profile starts a separate profile with default connection details and keeps your login callsign. Enter a name and details, then Save new profile. To edit or rename a profile, select it, change its name or connection details and choose Save changes. Delete profile removes the selected profile after confirmation; cancelling keeps it. There is no fixed profile count limit. Both selectors update after save, rename or deletion. Unfinished edits in other tabs do not block profile management.

Remember password or token on this PC is optional. It does not create a secret key; it remembers the cluster password or HTTPS token you entered. It protects a profile password or token with Windows DPAPI for the current user account. It is stored encrypted in profiles.json, separately from ordinary settings. Copying this file to another account or computer may prevent decryption; enter the secret again there. Clear Remember password or token and save the profile to remove its saved secret. Without this option, the secret is session only.

A session secret remains available when reconnecting the same connection. Selecting a different saved profile loads only that profile's secret. Manual commands do not carry into the next profile. Keep credentials out of profile names and feed URLs.

Use Source Connect and Disconnect to change connections without restarting the application. RF and local listening must be explicitly enabled again after connecting. The Help topic Cluster customization has a reserved place for the forthcoming geographic filter guide.

## Source controls and password visibility

Source groups saved profiles, connection details, manual commands and the session console. TCP/Telnet shows hostname, port and login callsign. HTTPS JSON shows the feed URL and polling interval. Hidden fields retain their values and are not used by the selected connection type. Cluster command controls are inactive for HTTPS feeds.

The password or token field has an eye button with Show and Hide text. Show reveals the current value for typo checking. Hide conceals it again. Revealing a value does not save it or change how it is protected. Visibility resets when choosing another profile, creating a profile, switching source type or restarting the app. Switching source type clears the session secret so a cluster password cannot accidentally become a feed token.

Connect and Disconnect are together in the saved profile panel. They use the currently entered connection details. The manual command fields on Source and Live spots have no masking option. If a cluster asks for a password, use the dedicated password field and reconnect or knowingly send a visible manual response.


## One connection control

Source and Live spots use the same connection action. With no source connection it reads Connect in the normal neutral style. When the network is connected it reads Connected with the appearance accent border. Hovering over it or focusing it with the keyboard changes it to Disconnect with a red border; clicking closes the connection and stops output. While connecting or retrying it remains neutral and can be clicked to cancel. A Connected indicator confirms the transport, not that login succeeded or that valid spots have arrived.

Prompts are processed by logical line and partial prompt, including when banners share a network read. ANSI presentation sequences and NUL padding are removed before matching. The session console can show recognized prompts without waiting for a newline. Failed sockets are closed before retry backoff; stopping during connection establishment closes the returned socket before login. Duplicate session and rejected login messages are distinguished from DNS, refused connection and timeout errors.

Some clusters limit simultaneous sessions under one callsign. Close another client using that login or consult the cluster's SSID policy. Server outages, access rules and custom prompts can still require operator investigation.


New profile and deleting the selected profile stop the previous connection, clear its live rows and console and remove its session credential from the editor. Other saved profiles and their remembered credentials are retained. Saving a profile saves connection details only; it does not apply pending radio settings or connect automatically. Connect still applies the current settings, including any pending edits elsewhere, before starting the source.


If Windows cannot unlock a remembered password or token, the profile's connection details still load so it can be edited or deleted. A message asks you to enter the credential again. The stored credential is preserved until you save or delete the profile. Saving with Remember unchecked removes it; checking Remember and saving stores the newly entered value for this account.

## Transfer to Android and curated clusters

QR to phone opens a collection selector with every saved profile selected. Keep the entire collection or choose a subset, then Generate QR codes. Previous and Next move through numbered pages when needed. Update Android to 0.2.0a9 or later, choose Scan desktop QR and collect all pages in any order. Duplicate scans do not duplicate profiles and nothing is saved until the complete collection is reviewed and imported. Continue later preserves scan progress across activity recreation; Reset QR collection starts over. The QR collection includes current filters. Export profiles saves all profiles and filters to a file. Passwords/tokens are excluded; private feed URL query parameters must be removed before sharing. Review the QR/file's visible destination information before importing it on Android through Manage cluster profiles. Imported names do not overwrite existing profiles and no connection starts automatically. See the repository profile transfer guide for the versioned format.

Cluster directory includes W1NR, DX Spots, N2WQ, WB3FFV, W3LPL and W4MYA from the supplied validated operator list. Choose an entry and Add selected cluster on desktop, or Browse recommended clusters and Add to my clusters on Android. Hostname and port are filled for you. Your existing callsign is reused when available; otherwise enter your own. No other operator's callsign or credentials are bundled. Nothing connects automatically. You can also load a directory JSON file; retired entries cannot be added. Review dates record the supplied list, not a live availability guarantee. Existing saved profiles are removed only through the confirmed Delete profile action.

Connection errors distinguish DNS, refused or timed out connections, rejected or duplicate logins, HTTP authentication/permission/rate-limit errors and certificate verification failures. Status explains retry timing. Raw server text and credential-bearing URLs are excluded from diagnostic reports.

## Keeping a quiet cluster connected

TCP keepalive is enabled on desktop and Android. Desktop requests a 60 second idle interval and 10 second probes where the operating system supports tuning; Android uses its operating system's keepalive timing. These are transport probes rather than cluster commands, passwords or DX spots. They help detect dead TCP connections but do not override a cluster's own idle logout policy or Android background restrictions.

After 90 seconds without incoming cluster bytes, status explains that the feed may be quiet. A quiet feed alone does not cause a reconnect. Actual closed or failed connections still use bounded retry. No periodic command, blank line or backspace is injected into login or password prompts. Cluster specific application heartbeats require a documented compatible server command and remain future work.

Automatic sign in ignores DX spot lines, including a packet split after a spotter callsign ending in CALL and comments mentioning passwords. These are spot metadata rather than authentication prompts. Android checks partial prompts at command delimiters or an idle read instead of scanning the growing line for every character.

On Android, Scan desktop QR collection requests camera access when needed. Denial keeps the app and collected pages open and offers Android app settings. Import file remains available without a camera. Camera initialization or preview failure shows guidance inside the scanner with Close scanner; it does not clear the collection. Export diagnostics if the scanner still fails on your device. Camera use stops when you leave the scanner.
