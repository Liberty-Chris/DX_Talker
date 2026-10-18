# Project decisions

Updated October 17, 2026.

## D001 Windows first

Decided.

I'm starting with a Windows application using a compatible USB interface for radio audio and PTT. The first supported Windows versions and radio interfaces still need to be chosen.

## D002 Separate CW and voice settings

Decided.

CW and voice identification will have separate text fields. Voice will use text to speech by default, with an optional WAV recording. CW will be generated as audio Morse through the radio connection. The timing and whether the two IDs alternate still need to be settled.

## D003 Original archive and help pages

Decided.

Keep the original ZIP unchanged. The pages in docs/help will become the application's operator manual. Keep their topic IDs stable and update the relevant help page whenever a feature changes.

## D004 Separate cluster and web feed connections

Proposed.

Use one connection method for TCP/Telnet clusters and another for supported HTTP or HTTPS feeds. The W4MR host and port are the initial cluster example. A web feed provider still needs to be selected.

## D005 One place to manage transmission

Proposed.

One part of the application should manage all radio audio and PTT so announcements and IDs cannot overlap. Transmission should stay disabled after startup or a fault until the operator enables it. This needs testing with the supported hardware before unattended use.

## D006 Development tools

Still open.

The language, framework, audio and speech libraries, PTT libraries and installer tools haven't been chosen. Record the choices and why they fit the project here as they're made.

## D007 Separate rights for new and original work

Decided October 17, 2026.

I'm reserving all rights for now. The [modern project notice](../LICENSE) excludes the historical archive, which has its [own notice](../Original_Files/LICENSE).

I may change the modern license later with any necessary permissions. That won't automatically change the original files' terms. Existing permissions and bundled components' terms still apply. Ownership and any publishing agreements need to be checked before licensing or reusing historical material.

## D008 Standalone hardware and repeater integration

Planned October 17, 2026.

After the Windows application, I'm planning a standalone device that connects to a radio and uses WiFi for internet access. I'm also planning direct integration for repeater systems using ASL3, Allmon and Asterisk.

The hardware, integration method, supported versions and release timing still need to be worked out.
