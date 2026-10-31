# Getting started

## Launch

Extract the portable Windows package and keep its internal files alongside DXTalker.exe. Launch the EXE. To run from source, follow the repository's Windows setup document.

## Try it without a cluster or radio

In Audio and PTT, choose your speakers or headphones as Local preview output. Save and apply settings. In Live spots, choose Load sample spots, select a row and choose Preview selected. Sample spots never enter the radio queue.

In Identification, enter the CW and voice text you want to use. Try Preview CW locally and Preview voice locally. These controls do not assert serial PTT. Use headphones or speakers separate from the radio audio path, especially if your radio uses VOX.

## Receive spots

In Source, enter the cluster hostname, port and login callsign. Enter a session password only if required and choose Connect using these settings. Common prompts are handled automatically. A masked manual field lets you send an unusual login response or cluster command.

The source becomes ready when valid spots arrive. The initial example is w4mr.ddns.net, port 7373. Its live behavior still needs operator verification. You can also use an HTTPS JSON feed matching the supported contract described in Source connections.

## Set up radio output

Choose the radio audio device and PTT method in Audio and PTT. In Identification, configure the required ID text and schedule. In Announcements, set filters and acknowledge supervised operation on a clear or coordinated channel.

Save and apply settings. When a source is ready, Enable RF starts with identification. New live spots are then eligible for announcement. Previously displayed spots are not replayed. Send ID now requests the configured ID immediately.

## Stop and recover

STOP ALL OUTPUT cancels current and queued output and requests PTT release. Wait for Idle before applying changes or previewing. Source loss or an output fault disables RF. Reconnect does not automatically enable it again.

Settings are saved locally. Passwords, tokens, RF enable state and the supervised channel acknowledgement are not saved.
