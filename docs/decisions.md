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

Selected October 31, 2026 for the first Windows pilot.

Use Python 3.12 with Tkinter for the desktop interface, sounddevice for explicit audio output selection and pyserial for RTS and DTR control. Use Windows System.Speech through a bounded PowerShell child process to generate WAV audio before keying. Package with PyInstaller on a Windows GitHub Actions runner.

This keeps the parsing, connection and transmission policies testable on other systems while keeping the actual product focused on Windows. Native .NET was considered but is not required for this first implementation. The Windows package and hardware behavior still need pilot verification. Target Windows 11 x64 first. Other Windows versions and architectures are not claimed.

Audio selection uses an exact host API and device name and rejects ambiguous matches. Device indexes are resolved again before playback. Serial PTT supports RTS, DTR or both, with explicit active polarity. VOX is an operator selected alternative. CM108 HID, CAT and vendor specific PTT remain future adapters.

## D007 Separate rights for new and original work

Decided October 17, 2026.

I'm reserving all rights for now. The [modern project notice](../LICENSE) excludes the historical archive, which has its [own notice](../Original_Files/LICENSE).

I may change the modern license later with any necessary permissions. That won't automatically change the original files' terms. Existing permissions and bundled components' terms still apply. Ownership and any publishing agreements need to be checked before licensing or reusing historical material.

## D008 Standalone hardware and repeater integration

Planned October 17, 2026.

After the Windows application, I'm planning a standalone device that connects to a radio and uses WiFi for internet access. I'm also planning direct integration for repeater systems using ASL3, Allmon and Asterisk.

The hardware, integration method, supported versions and release timing still need to be worked out.


## D009 Initial configurable operating policy

Selected October 31, 2026 for the pilot.

Keep hardware selection configurable. Start with a TCP/Telnet source and a documented generic HTTPS JSON feed contract. Provide offline sample spots and local audio preview. Store settings locally but keep source passwords and tokens in memory for the session.

Schedule voice, CW, alternating IDs or both according to an explicit operator setting. The initial default is CW every ten minutes while RF is enabled, including an ID before the first automatic spot. The operator must supply ID text before enabling RF. This is a configurable product default and does not establish a station's legal identification policy.

Automatic shared channel access detection is deferred. The pilot requires the operator to acknowledge supervised use on a clear or coordinated channel. Startup, source loss, settings changes and faults disable RF and clear queued work. Reconnect never rearms transmission.
