# Source connections

## TCP/Telnet clusters

Choose TCP/Telnet and enter a hostname and port separately. The supplied example is w4mr.ddns.net on port 7373. Enter your login callsign and a password only if the service requires one. Choose Connect using these settings.

The adapter recognizes common login, callsign, username and password prompts, including prompts received in several fragments or without a newline. It also handles basic Telnet option negotiation. After the first valid spot, the status changes to Receiving DX spots.

If the cluster needs a different response, use Manual response or cluster command. This field is masked, sends one line and clears after sending. Responses are not journaled. Raw source traffic is not shown in this pilot.

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
