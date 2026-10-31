# Proposed architecture

Status: initial implementation. The Windows pilot uses Python, Tkinter, sounddevice, pyserial and Windows System.Speech. See the decision record for rationale and the status page for verification limits.

## Components and responsibilities

| Component | Responsibility | Boundary |
| :--- | :--- | :--- |
| Desktop interface | Settings, spot list, status, local preview, enable and stop | Does not key hardware directly |
| Source adapters | Connect, authenticate, frame incoming records and reconnect | TCP/Telnet and HTTP adapters have separate contracts |
| Spot parser | Classify records and normalize valid DX spots | Rejects banners, chat, prompts and malformed records |
| Policy and queue | Filtering, deduplication, expiry and rate limits | Bounded memory and explicit drop reasons |
| Speech and Morse | Produce audio from validated content and ID settings | Produces audio without controlling PTT |
| ID scheduler | Track due identification using a monotonic schedule | Coordinates deadlines with the transmission coordinator |
| Transmission coordinator | Serialize ID, spot and test requests | Sole owner of radio audio and PTT lifecycle |
| Hardware adapters | Selected audio endpoint and supported PTT method | No fallback to an unrelated audio endpoint |
| Settings and diagnostics | Versioned preferences and redacted events | Sensitive values use appropriate Windows protected storage |
| Help provider | Package and render docs/help pages | Stable topic IDs from the manifest |

## Connection model

A source moves through disconnected, connecting, awaiting login, authenticating, streaming and retry states. Failed login is distinguishable from an unreachable server. Reconnect uses bounded backoff and cannot itself enable RF transmission.

TCP packet boundaries are not line boundaries. Preserve partial lines across reads and cap buffer and line lengths. Handle service negotiation separately from spot parsing. HTTP sources require provider specific pagination, cursor or streaming behavior once their contract is known.

## Spot model

The initial Spot record stores source, spotter, DX callsign, decimal frequency in kHz, normalized UTC timestamp and receipt time. Comments are excluded. A UI row identifier is separate from the callsign and frequency duplicate key. Raw prompts and source traffic are not retained in diagnostics. Preserve raw source text only in bounded redacted diagnostics when useful.

The archive's time fields often contain only HHMMZ and sometimes are wrapped or incomplete. Do not invent a historical date. Live date inference and midnight rollover require explicit tests and a documented rule. Freshness checks must distinguish receipt time from source time.

## Transmission model

A single coordinator arbitrates due IDs and ordinary announcements. A completed transmission includes playback completion and attempted PTT release. Failed playback, device removal or cancellation transitions to a fault with transmission disabled.

PTT deassertion belongs in all exit paths, but software cleanup cannot guarantee release after process termination, a USB failure or a hardware latch. Select interfaces with a documented idle state and timeout behavior, then bench test failure cases before unattended use.

Audio Morse, generated voice and WAV playback share the same output pipeline. Speech should be prepared before keying so synthesis latency cannot hold an idle carrier. Bound audio duration and queue residence time. Do not replay old backlog following reconnect.

## Testing approach

Use offline captures and synthetic fixtures for login prompts, Telnet negotiation, split reads, multiple lines in a read, malformed spots and midnight rollover. Use a fake clock for ID deadlines, expiry and reconnect. Use fake audio and PTT adapters for cancellation and serialization.

Physical verification must cover the named interface, operating system, audio routing, PTT polarity, startup state, stop, device unplug, application termination and maximum transmit duration. Simulation is not a substitute for this evidence.

## Technology decision

The selected stack and pinned direct dependency versions are recorded in [decisions](decisions.md), requirements.txt and requirements-build.txt. The portable Windows build packages the application runtime and canonical help pages. Native APIs remain behind AudioOutput, WindowsSpeech and serial PTT adapters.
