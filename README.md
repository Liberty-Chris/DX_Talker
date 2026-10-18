# DX Talker

DX Talker brings spoken DX cluster announcements to amateur radio. My dad, Dave Hockaday (WB4IUY), and Kevin Leggett (KT4BN) created the original application in the early 1990s. I'm Chris Hockaday (KF4DBX), and I'm bringing it into the modern era.

The original DX Talker monitored a DX cluster through a TNC packet node, announced spots over RF and periodically identified the station using voice and CW.

## Project status

I'm starting with a modern Windows application, with a standalone hardware device and direct repeater integration planned to follow. This repository holds the original software archive and the plans for the new versions.

Development is still in the planning stage. There isn't a modern application or installer available yet. The features below describe where the project is headed. The [status record](docs/STATUS.md) tracks what's actually been built and tested.

## The modern application

The Windows application will connect to an internet DX source, read spots aloud and send audio to a radio through a USB interface. A compatible interface will also handle push to talk (PTT), so the application can key the radio for announcements.

You'll have separate text fields for CW and voice identification. Voice IDs will use text to speech by default, with the option to use your own WAV recording. CW IDs will be generated as audio Morse code through the radio's audio connection.

The application will show connection status and incoming spots, provide announcement controls and let you preview audio before transmitting. You'll explicitly enable RF transmission when you're ready. Supported Windows versions, radio interfaces and PTT methods will be confirmed during development.

## Standalone hardware

I'm also planning a standalone DX Talker device that connects to a radio and gets its internet connection over WiFi. The goal is to handle DX announcements and station identification without needing a Windows computer running alongside it.

This is a planned follow on to the Windows application. Hardware, radio connections and availability will be announced as development progresses.

## Direct repeater integration

I'm planning a direct integration option for repeater systems using ASL3, Allmon and Asterisk. The goal is to bring DX Talker announcements into the existing repeater system without needing a separate radio just to feed it audio.

The integration method, configuration and supported versions still need to be worked out and tested. This is a future option, and it isn't available yet.

## Internet source example

One source I'm working toward supporting is `w4mr.ddns.net` on port `7373`. This is a TCP/Telnet DX cluster connection that requires a sign in before spots can be received.

I still need to confirm its current login prompts, access requirements and feed permissions. It hasn't been connected to or tested as part of this project yet.

I also plan to support web feeds once a provider, feed format and authentication method are selected. A cluster host and port and an HTTP or HTTPS feed need different connection methods. An ordinary web page URL won't work as a DX feed on its own.

## Documentation

The [documentation index](docs/README.md) is the starting point for the project documents. The [roadmap](ROADMAP.md) lays out the development milestones, [requirements](docs/requirements.md) describe the intended features and [architecture](docs/architecture.md) outlines how the pieces will fit together.

The [operator help](docs/help/index.md) is being written alongside the project so it can become the application's Help and Info content. The [agent instructions](AGENTS.md) keep development, documentation and status updates in sync.

For the historical material, see the [original archive description](Original_Files/Description.md) and [legacy findings](docs/legacy.md). The [open questions](docs/questions.md) track details we still need to settle.

## Attribution and permissions

The original DX Talker was created by Dave Hockaday (WB4IUY) and Kevin Leggett (KT4BN). I'm preserving their work here as part of bringing DX Talker forward.

All rights are reserved for now. The [modern project notice](LICENSE) and [original files notice](Original_Files/LICENSE) cover the two separately. Public availability doesn't grant new permission to reuse or redistribute them. Existing valid permissions, applicable law, GitHub's applicable terms and third party rights still apply.

I may change the modern project's license later. That won't automatically change the rights or permissions for the original files.
