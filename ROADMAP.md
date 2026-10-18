# DX Talker modernization roadmap

Updated October 17, 2026.

The initial documentation is in place. Next comes choosing the hardware and development tools, then building the Windows application. [Project status](docs/STATUS.md) tracks progress.

## Milestones

| Milestone | State | Scope | Completion evidence |
| :--- | :--- | :--- | :--- |
| M0 Documentation foundation | Complete | Archive review, requirements, help structure and project workflow | Static archive findings recorded and documentation links checked |
| M1 Discovery and decisions | Planned | Confirm cluster sign in, choose initial interface and supported Windows target, decide stack and ID policy | Sanitized cluster transcript, interface specification and accepted decision records |
| M2 Local Windows prototype | Planned | Desktop shell, settings, spot model, offline replay, speech and Morse previews | Valid and malformed fixture tests, pronunciation examples and local audio verification with RF disabled |
| M3 Live source connection | Planned | TCP/Telnet adapter for supplied example, explicit login states, reconnect and parsing | Authorized connection test plus deterministic login, framing, disconnect and duplicate tests |
| M4 Radio integration | Planned | Selected USB audio device, selected PTT method and transmission coordinator | Bench evidence for correct routing, lead and tail timing, stop, timeout, unplug and shutdown behavior |
| M5 Identification and announcements | Planned | Separate CW and voice fields, default speech, WAV option, scheduling and spot filtering | ID deadlines, queue limits, stale spot expiry, WAV failure and no overlapping transmissions verified |
| M6 Windows pilot | Planned | Installer, settings migration, diagnostics, accessible UI and packaged Help and Info | Clean machine install, upgrade, removal and operator acceptance with named hardware and Windows versions |
| M7 First release | Planned | Resolve pilot defects and publish supported scope | Release checklist complete, accurate help and known limitations published |

Work through the connection and local audio stages before enabling radio transmission. Test radio control before adding unattended scheduling. Web feed support needs a selected provider and format, so its place in the first release depends on that choice.

## Immediate next task

Confirm the desired initial USB radio interface and obtain a sanitized description of the W4MR sign in prompts through an authorized operator. The project can meanwhile turn the archived cluster capture into reviewed parser examples without running the old program or transmitting.

Record the framework choice only after comparing Windows audio device selection, speech availability, serial or vendor PTT support, packaging and testability. No language or framework is selected yet.

## First release acceptance

An operator can configure a source, sign in as required, see valid spots and preview speech locally. They can select the radio audio device and supported PTT method, configure CW and voice IDs and choose generated speech or a WAV voice ID.

Enabling transmission is explicit. Parsed spots enter a bounded queue, stale spots expire and scheduled identification receives priority. Stop cancels queued transmission and releases PTT. Reconnection or application restart never silently resumes RF operation.

The pilot must demonstrate ordinary operation and failure recovery using actual supported hardware. Application Help and Info are generated from the maintained documentation and accurately describe the released version.

## Beyond the first release

Planned follow ons are a standalone device that connects to a radio and uses WiFi for internet access, plus direct repeater integration for systems using ASL3, Allmon and Asterisk. Neither is implemented or included in the initial Windows release. Hardware selection, integration methods, supported versions and release timing remain open. Both paths require their own implementation and bench verification before release.

Candidates include additional web feed providers, additional PTT adapters, radio control integration, richer spot filters, pronunciation profiles and additional platforms. These are possibilities for later versions.

## Updating this roadmap

Move a milestone to In progress only when work begins. Mark it Complete only when its completion evidence exists. Update status, decisions, operator help and changelog in the same change. Record newly discovered dependencies and retain explicit unknowns.
