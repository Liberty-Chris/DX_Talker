# History and updates

## Live view and history

Live view maximum spots controls the in memory display, from 50 to 5000 rows. Oldest rows are removed first. Clear view removes displayed rows without deleting history files. Changing a source connection or selecting another saved profile clears the view automatically. Stale events from the previous connection are discarded. Clearing the view does not replay or transmit old spots.

Keep spot and connection history enables structured JSONL files. Each validated received spot records source type, profile name, callsigns, frequency and timestamps. Connection and disconnect events are also recorded. The application activity panel is separate, remains in memory and holds 200 lines. The console holds the latest 15 lines and is never written to history. Manual commands and authentication data are excluded from disk history.

Choose a history folder or leave it blank to use the logs folder under the DXTalker settings directory. Save to apply. Open history folder opens the currently applied location. Changing folders starts writing there; previous files remain in their old folder.

History file size is configurable from 1 to 100 MiB and backup count from 1 to 30. The active file is history.jsonl. Rotated files use numeric suffixes. The default is one 5 MiB active file and four backups, approximately 25 MiB total. Rotation occurs before the next record would exceed the file size. Reducing the backup count removes surplus numbered backups in the selected folder. Decreasing the file size takes effect on the next record; existing larger backups age out through rotation.

A full disk or unwritable folder stops history writing and produces an activity message. Receiving and output continue. Choose a writable folder and save again to retry. Turning logging off closes the file and leaves existing history intact. These are local operational records, not an amateur radio contact log or ADIF export.

## Updates

The installed version is shown here and in Help. Check for updates automatically checks public GitHub Releases at startup and once per day while running. Check now performs a manual check. Pilot includes prereleases and final releases. Stable includes final releases only. Releases must have a recognized newer version, a Windows x64 installer and SHA256SUMS.txt to be offered.

A new release appears in the status and footer banner. Read the release notes or open Release page. Download update runs in the background and verifies the installer against the release SHA256 checksum before enabling installation. A failed or interrupted download never replaces the current installation. Close the app to cancel a pending download.

Install update asks before stopping output. It waits for Idle, disconnects the source, opens the verified setup program and closes DX Talker. If output does not stop within 30 seconds, installation is paused. Settings, appearance and named profiles remain in their account data folder. Restarted output stays disabled. Setup remains interactive; updates never install silently or restart RF.

The updater installs only from the packaged Windows app. Source checkouts use Git. Portable users may install the account based setup version through this flow. Release assets are public and no GitHub sign in is needed. Checks contact GitHub and can be turned off. No cluster login or profile details are submitted.

Checksums detect damaged downloads and changes after download. They are published with the release; this is not independent publisher signing. The installer remains unsigned.

Existing versions without an updater need one manual installation of this updater enabled build. They cannot receive an update notification retroactively. After that, the next published compatible release can exercise the full notification and installation flow.


## When update checking fails

The status includes the installed version and selected channel after a successful check. Stable does not offer preview releases. If a newer compatible preview exists, the status explains that Pilot is needed instead of reporting only that nothing was found.

A failed check is not evidence that no release exists. DNS errors, TLS certificate verification, timeouts, GitHub HTTP responses and public API rate limits receive distinct messages. GitHub can rate limit a shared public address even when ordinary internet access works. Use Release page for a manual installer download if needed. Do not disable HTTPS verification to work around a certificate error.

## Local diagnostics and support reports

History is the optional spot/connection record. Diagnostics are separate bounded local application records under %LOCALAPPDATA%\DXTalker\diagnostics. Pilot logging defaults on and can be disabled through Keep local diagnostic logs; restart applies that choice. Stable builds default off. No diagnostic or crash report is automatically sent anywhere.

Records include version, session ID, fixed connection failure categories, output activity times and exception types with source file/function/line locations. Exceptions do not include message values, locals, passwords, tokens, full profile/settings files or raw cluster text. A UI watchdog samples code locations after a long delay and records recovery. A file dialog or slow system operation can also delay the UI; a stall record is evidence, not a root cause by itself. Native fault dumps are enabled after desktop startup and paths are reduced to basenames in exported reports. Not every native failure, power loss or forced termination can produce a crash trace; incomplete session markers are recorded on the next launch without guessing why.

Export diagnostic report creates a local ZIP of bounded diagnostic logs only. Review and share it manually when investigating a problem. No report is uploaded. Logs cannot recover activity before diagnostics were enabled, and failure to create the log folder is reported in the app. Future public telemetry requires separate explicit consent and approved privacy/usage terms; it is not implemented by this local export feature.


Selecting the optional ElevenLabs provider sends announcement or speech ID text through the shared pilot speech service to ElevenLabs. This is independent of diagnostic logging or report export. Offline Windows, Piper and Recorded choices remain available. The service may retain bounded generated audio in its private cache; its setup guide documents retention and limits.
