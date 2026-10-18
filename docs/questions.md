# Open questions

Updated October 17, 2026.

These are the details I still need to work out as development gets started. Record answers here so the plans and help pages stay current.

## Windows application

| ID | Question | Why it matters |
| :--- | :--- | :--- |
| Q01 | Which radio and USB interface should we support first? | Determines the audio and PTT connections |
| Q02 | What does the W4MR login process ask for? | Lets us build and test the connection properly |
| Q03 | Should the first release support the TCP/Telnet cluster, a web feed or both? Which web provider and format? | Sets the connection work for the first release |
| Q04 | Which Windows versions and processor architectures should we support? | Helps choose development tools and test machines |
| Q05 | Should voice and CW IDs alternate or both run? At what intervals and after which transmissions? | Defines the ID schedule |
| Q06 | How will the application know whether the channel is busy? | Audio and PTT connections alone may not provide that information |
| Q07 | Which spot details, filters and repeat limits do we want? | Determines what gets announced and how often |

## Standalone hardware and repeater integration

For the standalone device, choose the hardware, power supply, radio connections, WiFi setup and local controls.

For direct repeater integration, choose the target ASL3, Allmon and Asterisk versions and work out how to connect audio and control. Announcements need to fit around repeater traffic and existing station identification.

## Questions for Dad, Dave Hockaday (WB4IUY)

| ID | Question | What we have so far |
| :--- | :--- | :--- |
| H01 | Which QST issue and article covered DX Talker? | The exact reference hasn't been located |
| H02 | What PTT interface and wiring did the original use? | IOPORT.VBX is in the archive |
| H03 | How were voice and CW IDs configured and scheduled? | The program references ID.wav, but that recording isn't in the archive |
| H04 | Are the Visual Basic source and missing ID recording still around? | The archive contains compiled programs and audio files |
| H05 | Which original behaviors should we carry forward? | The captured spots and speech clips give us a starting point |

## Before release

Choose the version numbering, distribution channel, update method and supported hardware list. Review permissions before using original recordings or bundled components in a new release.

Rights are reserved for now under the [modern project notice](../LICENSE) and [original files notice](../Original_Files/LICENSE). Any later license change needs to be clear about which material it covers and have the necessary permissions.

## What we've already checked

The W4MR example is a TCP/Telnet host and port. We still need to test its login process and choose a web feed provider if web feed support is included.

The archive review on October 14, 2026 found compiled programs but no editable Visual Basic source. We can build the modern application from the requirements while looking for the original source.
