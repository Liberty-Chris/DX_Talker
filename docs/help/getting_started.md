# Getting started

## Launch

The setup program targets Windows 10 22H2 and Windows 11 on x64 PCs. Run DXTalker-Setup-Windows-x64.exe to install for your Windows account. Python is included. Setup creates a Start menu entry and a desktop shortcut by default, using the DXt icon. You can clear the desktop shortcut option during setup. Close DX Talker before installing an update. Run the new setup program to update the existing installation. Remove DX Talker through Windows Settings. Settings and appearance preferences under %LOCALAPPDATA%\DXTalker are retained during updates and removal. The installer is unsigned, so Windows may show a publisher or SmartScreen warning. Actual Windows 10 and Windows 11 acceptance tests remain open.

For the portable option, extract the portable Windows package and keep its internal files alongside DXTalker.exe. Launch the EXE. To run from source, follow the repository's Windows setup document.

## Appearance

Choose Light or Dark from Appearance in the header. The DXt logo and interface colors change together. This choice is remembered immediately and does not apply pending radio settings or change RF state. New installations start in Dark mode.

## Try it without a cluster or radio

In Audio and PTT, choose your speakers or headphones as Local preview output. Save and apply settings. In Live spots, choose Load sample spots, select a row and choose Preview selected. Sample spots never enter the radio queue.

In Identification, enter the CW and voice text you want to use. Try Preview CW locally and Preview voice locally. These controls do not assert serial PTT. Use headphones or speakers separate from the radio audio path, especially if your radio uses VOX.

## Receive spots

In Source, enter the cluster hostname, port and login callsign. Enter a session password only if required and choose Connect using these settings. Common prompts are handled automatically. A visible manual field lets you send cluster commands. Use the dedicated password field for a secret. Its eye button shows or hides the value for checking. Named profiles retain each source configuration.

The source becomes ready when valid spots arrive. The initial example is w4mr.ddns.net, port 7373. Its live behavior still needs operator verification. You can also use an HTTPS JSON feed matching the supported contract described in Source connections.

## Set up radio output

Choose the radio audio device and PTT method in Audio and PTT. In Identification, configure the required ID text and schedule. In Announcements, choose the announcement format, frequency filters and timing. Supervise operation on a clear or coordinated channel; no acknowledgement checkbox is required.

Save and apply settings. Enable RF uses those saved settings and starts with identification, even without a connected source. The button reads RF enabled while active, and Disable RF on hover or keyboard focus. Click again to stop RF without disconnecting the cluster. New live spots are then eligible for announcement. Previously displayed spots are not replayed. Send ID now requests the configured ID immediately.

## Stop and recover

STOP ALL OUTPUT cancels current and queued output and requests PTT release. Wait for Idle before applying changes or previewing. Source loss or an output fault disables RF. Reconnect does not automatically enable it again.

Settings are saved locally. RF and local listening enable state are never saved. Passwords and tokens remain session only unless you explicitly remember one in a Windows protected cluster profile.

For speech, keyboard and local listening tools, see Listening and accessibility. History and updates covers retention, log folders and the application update process.
