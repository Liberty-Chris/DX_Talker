# DX Talker

DX Talker brings spoken DX cluster announcements to amateur radio. This project is modernizing the application created by Kevin Leggett (KT4BN) and Dave Hockaday (WB4IUY) in the early 1990s.

According to the project history supplied by Chris Hockaday, the original was associated with QST, monitored a DX cluster through a TNC packet node and retransmitted information over RF. It periodically identified the station using voice and CW. The exact QST article citation remains to be located.

## Project status

Modernization planning and documentation are underway. This repository currently preserves the original software archive and defines the intended Windows application. There is no modern application, installer or supported build procedure yet. Features described below are planned unless explicitly marked implemented in the [status record](docs/STATUS.md).

## The modern application

The first release will be a Windows desktop application that connects to an internet DX source, reads useful spots aloud and sends audio to a radio through a USB audio interface. PTT means push to talk and will be controlled through a compatible interface. A USB audio device alone does not necessarily provide PTT.

Operators will configure separate text fields for CW identification and voice identification. Text to speech is the default voice method. An optional WAV recording will provide an alternative voice ID. CW will be generated as audio Morse code through the selected radio audio device.

The application will provide feed connection status, a spot display, announcement controls, local previews and an explicit control to enable RF transmission. Exact radio hardware, PTT methods and operating system support will be selected and tested during development.

## Internet source example

The supplied example is host `w4mr.ddns.net` on port `7373`, using a TCP/Telnet cluster connection. It is an address and port rather than an HTTP web feed. The application must handle the service's sign in exchange before it can consume spots.

The current prompt sequence, credentials required, availability and feed permissions have not been verified. The project has not connected to this service or signed in. A callsign may be sufficient on some clusters, but this endpoint's requirements must be confirmed.

Supporting this example requires a TCP/Telnet adapter. A separate web URL adapter is planned once an actual HTTP or HTTPS feed, authentication method and payload format are identified. Entering an arbitrary web page URL will not automatically create a DX feed.

## Documentation

Start with the [documentation index](docs/README.md). The [roadmap](ROADMAP.md) describes milestones and their completion criteria. [Product requirements](docs/requirements.md) define intended behavior. [Architecture](docs/architecture.md) records the proposed boundaries without locking in a technology stack.

The [operator help](docs/help/index.md) is the future application's help source. Its pages distinguish planned workflows from available behavior. The [agent instructions](AGENTS.md) explain how code, status, decisions and help must stay synchronized.

The [original archive description](Original_Files/Description.md) and [legacy findings](docs/legacy.md) distinguish directly observed evidence from historical recollections. [Open questions](docs/questions.md) tracks the few details that need operator or author input.

## Attribution and permissions

Credit for the original DX Talker belongs to Kevin Leggett (KT4BN) and Dave Hockaday (WB4IUY). The archive is preserved for historical reference. No repository license has been selected and this documentation does not grant new rights to the original software, recordings or bundled runtime components. Distribution terms for a modern release remain an open project decision.
