# Decision record

Updated October 14, 2026.

## D001 Windows first

State: accepted project direction from Chris Hockaday.

The first modern application targets Windows and connects radio audio and PTT through compatible USB interfaces. Other platforms remain future possibilities. Exact supported Windows versions and hardware are unresolved.

## D002 Independent CW and voice settings

State: accepted project direction from Chris Hockaday.

Provide separate text fields for CW and voice identification. Generated speech is the default voice method and a WAV file is an optional alternative. The initial CW design uses audio Morse through the radio audio device. Confirm scheduling policy separately.

## D003 Preserved archive and traceable help

State: accepted documentation baseline.

Keep the original archive unchanged. Use docs/help as the canonical operator manual with stable topic IDs. Behavior changes update help and implementation status in the same change. Planned behavior must remain distinguishable from shipped behavior.

## D004 Separate source adapters

State: proposed technical approach.

Use a TCP/Telnet adapter for the supplied endpoint and a separate provider specific adapter for a confirmed HTTP or HTTPS feed. This preserves the user's internet feed goal without pretending a cluster host and port is a web API.

## D005 Central transmission ownership

State: proposed technical approach.

Route all audio and PTT through one coordinator to prevent overlapping announcements and IDs. Require deliberate RF enable after startup or fault recovery. Validate behavior on actual hardware before unattended operation.

## D006 Technology stack

State: open.

No language, framework, speech library, audio library, PTT library or installer technology has been chosen. Record alternatives, current dependency evidence, rationale and verification here when selecting them.
