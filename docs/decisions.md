# Decision record

Updated October 17, 2026.

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

## D007 Rights reserved separately for modern and historical material

State: accepted project owner decision from Chris Hockaday on October 17, 2026.

Reserve all rights for the modern project for now, with no public use, modification or redistribution license. Preserve historical rights separately in Original_Files/LICENSE and expressly exclude the archive from the modern notice. Existing valid permissions, applicable law, GitHub's applicable terms and third party terms remain unaffected. Keep the original ZIP unchanged.

Chris may revisit the modern policy later, subject to authorization from applicable copyright holders. This decision does not establish current historical ownership or claim ownership of bundled components. Confirm ownership and historical publishing agreements before historical reuse or licensing.

## D008 Standalone hardware and direct repeater integration

State: accepted future project direction from Chris Hockaday (KF4DBX) on October 17, 2026.

Keep Windows as the first application target. Plan a standalone radio connected device using WiFi for internet access and a direct repeater integration option for systems using ASL3, Allmon and Asterisk. These are separate future deployment paths, with hardware, integration methods, supported versions and timing still open. This records direction rather than claiming working compatibility.
