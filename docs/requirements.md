# Product requirements

Status: planned. Updated October 14, 2026.

## Purpose and scope

The first product is a Windows desktop application that turns selected internet DX spots into spoken announcements over a radio with station identification. It modernizes the original workflow while preserving attribution to Kevin Leggett (KT4BN) and Dave Hockaday (WB4IUY).

## Required behavior

| ID | Requirement | Acceptance criterion |
| :--- | :--- | :--- |
| R01 | Windows desktop operation | Named Windows targets, architecture and installer are tested before being advertised |
| R02 | Configurable internet source | Operator can choose source type and enter host and port or a supported feed URL |
| R03 | Source sign in | Connection remains in an explicit login state until the configured service exchange succeeds; errors are visible and secrets are redacted |
| R04 | TCP/Telnet example support | An adapter handles the confirmed W4MR service exchange, fragmented lines and Telnet negotiation where present |
| R05 | Supported web feed | A provider, payload and authentication contract are confirmed before implementation is claimed |
| R06 | Spot ingestion | Validated spot records retain callsign, frequency, spotter, source and time information without treating chat as a spot |
| R07 | Spoken announcements | Callsigns and decimal frequencies are spoken unambiguously; local preview is available |
| R08 | USB radio audio | Operator selects a specific supported Windows output device; loss of that device stops RF audio rather than switching to default speakers |
| R09 | USB associated PTT | Supported interface and control method are explicit; audio and PTT are configured independently when needed |
| R10 | CW ID | A dedicated text field, audio Morse generator, speed, tone and local preview are provided |
| R11 | Voice ID | A dedicated text field uses text to speech by default with voice, rate and preview controls |
| R12 | Recorded voice ID | Operator may select a WAV file, validate it and preview it; missing or invalid audio has a visible recovery path |
| R13 | ID scheduling | Configurable intervals and policy govern voice and CW IDs with verified priority over ordinary spots |
| R14 | RF control | Application starts with transmission disabled; enable, stop and a visible transmit state are available |
| R15 | Queue discipline | Queue length, age, deduplication and announcement rate are bounded and configurable where useful |
| R16 | Failure handling | Disconnect, audio loss, PTT failure, cancellation and shutdown stop affected output and attempt PTT release |
| R17 | Settings and diagnostics | Settings survive restart without automatically enabling RF; diagnostics redact credentials |
| R18 | Help and Info | Released application packages the maintained help pages and reports its version and supported scope |

## Feed interpretation

The supplied endpoint is `w4mr.ddns.net:7373`. It implies a TCP connection using a Telnet style cluster interface, not a confirmed HTTP feed. Login fields and prompts must come from service evidence rather than assumptions. Source login is distinct from an application account; no DX Talker account or cloud synchronization is currently required.

For web feeds, authentication may use a provider specific token or other mechanism. Do not invent an API contract. Plain TCP/Telnet may expose submitted credentials in transit; describe the chosen service's transport accurately in help.

## Announcement policy

Initial proposed spoken content is the DX callsign and frequency. Band filters, duplicate suppression, spot age and whether to include spotter, time or comments require an operator decision. Free text comments are excluded from RF speech by default pending that decision.

Preserve the frequency value and explicit units. Use a documented callsign pronunciation policy that handles digits and portable suffixes. Test speech with the installed Windows voice rather than assuming ordinary word pronunciation is sufficient.

## Identification policy

CW and voice text are separate settings. Whether to alternate them or schedule both, interval limits, end of transmission behavior and overdue handling require a confirmed operating policy. The scheduler must not starve identification behind a busy spot queue. A failed required ID must visibly pause further automatic announcements until the configured policy can be satisfied.

In this scope, CW means audio Morse sent through the radio audio path. Direct hardware keying of an HF CW input is a separate possible feature.

## Transmission sequencing

Only one coordinator may key the radio. It acquires the configured device, asserts PTT, waits a configurable lead time, plays one item, waits a configurable tail time and releases PTT. The maximum transmit duration must also cover a stalled playback. Long announcements cannot bypass identification deadlines.

Preview uses an explicitly selected local device with no PTT. Startup, device change, reconnect and recovery leave RF disabled until the operator deliberately enables it. Emergency stop cancels queued RF work.

Busy channel detection is unresolved because audio and PTT alone do not establish a reliable receive activity signal. Automatic operation on a shared channel must await a documented channel access policy and compatible hardware.

## Release limits

Initial hardware support is limited to interfaces actually tested. No universal USB compatibility, recovered legacy source, exact original behavior, specific Windows version or live provider availability is claimed.
