# Radio audio and PTT

## Choose outputs

Local preview output is the device used by preview controls. Radio audio output is the device used while RF is enabled. Choose exact device names and prefer Windows WASAPI where available. Save and apply settings.

A preview can still reach the radio if both roles use the same device. This is particularly relevant for VOX, which can key from any incoming audio. Separate local and radio outputs for listening tests.

The app resolves the selected device before playback. Missing or ambiguous names stop output instead of falling back to another device. Refresh audio and serial devices after connecting an interface. Refreshing disables RF.

## PTT methods

VOX sends audio without controlling a PTT line. Your radio or interface must already be configured to key from that audio.

RTS, DTR and RTS+DTR control compatible serial PTT wiring. Select the COM port and PTT active high setting. Unchecking active high reverses the selected line's polarity. Unused lines stay low. Serial flow control is not used.

A USB audio device does not necessarily supply PTT. CM108 HID interfaces, including RIM devices, are not controlled by these serial modes. CAT and vendor specific interfaces are also not included yet. Exact hardware compatibility needs a bench test.

## Traditional PC serial ports and DB9 wiring

DX Talker can use a built in PC COM port or a compatible USB serial adapter for PTT. USB is not required for the control connection. Select its COM number in Audio / PTT and use an adapter that actually exposes the required control lines.

For a standard PC RS232 DB9 serial connector, choosing RTS in the app uses pin 7 for transmit control. Choosing DTR uses pin 4. Pin 5 is the PC serial signal ground and is the reference on the computer side of a suitable interface. RTS+DTR operates both control outputs independently; do not join pins 4 and 7 together.

Pin 3, marked TXD, carries outgoing serial data. It is not transmit audio. There is no analog audio output on a standard PC RS232 DB9 connector. DX Talker uses the selected control lines for serial PTT rather than sending CAT commands on TXD.

These assignments are for the computer's standard serial connector, not a radio's accessory connector. A radio or interface can use a DB9 shell for a completely different arrangement, including audio and PTT. Use the manufacturer's pinout for that device. Check the connector's moulded pin numbers: looking at the mating face and looking at the solder side reverses the apparent layout. A null modem cable can also reroute signals; verify end to end continuity rather than assuming a cable is wired straight through.

## Converting serial control into radio PTT

RTS and DTR are RS232 electrical signals, not ordinary radio PTT contacts or a guaranteed 3.3 V or 5 V logic output. Many radio PTT inputs expect a switch closure to their designated PTT return. Use a compatible interface that translates the control signal into the electrical action required by the radio. Do not connect raw RTS/DTR directly to an ordinary ground to transmit PTT input unless the radio or interface manual explicitly permits that connection.

An optocoupler interface can provide an isolated switching output; a correctly designed transistor interface can also switch a suitable radio PTT input. The driver, reverse voltage protection, current rating and radio PTT voltage must be matched to the actual hardware. This guide does not establish one universal component circuit for every radio. On an isolated interface, PC pin 5 belongs to its computer side; do not bypass the isolation by automatically joining it to radio ground.

The app's Active high option selects the logical asserted state of RTS/DTR. It does not convert RS232 to TTL voltage or make an unsafe wiring arrangement compatible. Verify the interface's idle and transmit behavior, polarity and release with the radio disconnected before normal operation. Some ports can pulse control lines when opening or during startup.

## The separate audio connection

Choose the sound device carrying the radio audio in Audio / PTT. It can be the computer's built in sound output, a USB sound adapter or the radio's own USB audio device. This audio path is separate from the serial PTT path.

Connect that output through the attenuation and audio isolation appropriate to the radio's microphone, data or accessory transmit audio input. A sound output is not automatically at the correct level for a microphone input. Start low and verify the transmitted audio using the exact radio/interface instructions. If using a stereo output for a mono radio input, use an appropriate channel or mixing network rather than directly shorting the left and right outputs together.

The complete arrangement therefore has two paths: the PC's RTS or DTR control through a PTT interface to the radio's PTT input, and the selected sound output through the audio interface to the radio's transmit audio input. A combined commercial interface may package both paths in one box or cable, but they remain separate functions.

## Choosing a radio specific cable

Record the exact radio model, interface model, radio connector, intended mode and the manufacturer's pin numbering view. Then identify transmit audio input, its return, PTT input, PTT return, required levels and keying polarity from that model's documentation. A connector that fits physically is not enough to establish compatibility. Only add a model specific wiring recipe after those details and the stop/release behavior are verified.

The [NI RS232 connector reference](https://www.ni.com/en/support/documentation/supplemental/18/converting-an-rj50-serial-connector-to-db9-or-db25.html) documents the PC DB9 signal assignments. The [Sound Card Packet serial PTT guide](https://www.soundcardpacket.org/7cableptt.aspx) illustrates the separate serial control and isolated radio PTT switching approach. Its example circuit is a reference, not a substitute for checking a particular radio's electrical requirements.

## Timing and level

PTT lead time delays playback after keying. Tail time delays release after audio ends. Maximum transmit seconds includes lead, playback and tail. Audio that cannot fit within this limit is rejected before keying. A watchdog makes a separate release attempt if output stalls.

Spot radio level, CW ID level and Voice ID level have independent percentage controls from zero to 100. Zero mutes that category. CW and voice levels are applied independently even in a combined ID. Local listening level additionally scales local previews and live local announcements. Set the radio's input gain using the interface and radio instructions. This app does not measure deviation.

## Stop and faults

STOP ALL OUTPUT cancels pending work and attempts release. Source loss, output errors and settings changes disable RF. Wait for Idle before applying changes and explicitly enable output after recovery.

Some serial drivers can pulse control lines when a port opens. Test that behavior before connecting PTT for normal use. Software cannot guarantee release after forced process termination, USB failure or a hardware latch. Verify your station's physical stop method and any interface timeout.

## RF toggle

Enable RF uses saved radio and ID settings without applying pending edits or changing the cluster connection. A connected source, a valid received spot, a supervision acknowledgement and a shared device confirmation are not prerequisites. The radio output and the ID settings still must be valid, and any current output must finish before enabling. Save and apply configuration changes first.

While enabled, the button has an accent border and reads RF enabled. Hover or keyboard focus turns it red and changes the text to Disable RF. Clicking stops current and queued RF output without disconnecting the source or clearing the live view. It shows Stopping while cancellation finishes. Stop All Output, faults, source loss and settings changes also return it to the disabled state. Startup and reconnect never enable RF automatically.

Without a source, RF can still send initial, periodic and manually requested IDs. Only new validated live spots are eligible for RF announcements; sample rows and displayed history are not queued. Optional receive audio monitoring can hold RF when audio is detected; it is not a carrier detector. Supervise operation on a clear or coordinated channel. Shared local and radio devices may send previews to a VOX radio; use separate outputs for listening tests.


## Compact Audio / PTT controls

Audio outputs, Push to talk, Transmit timing and Audio levels are separate compact groups. Device selectors have bounded widths and numeric fields show their units and ranges. Refresh devices updates both audio and serial choices and stops output as before. VOX hides serial port and polarity fields; choosing a serial PTT method shows them again with their saved values. Changing the visible method does not change the configured hardware until settings are saved and applied. CM108 HID and CAT remain outside this pilot.

## Radio setup recipes

Start with RF disabled and a monitored test path. Choose the exact radio audio output and a separate local speaker/headphone output. Avoid device defaults that can change after a USB reconnect. Turn off Windows audio enhancements and spatial processing for the radio output, then start the application's spot and ID gains low and increase while monitoring the transmitted audio. Device selection and a working USB cable do not establish a safe level or compatible PTT wiring.

For an HF transceiver with built in USB audio, select its USB audio device and select the radio's USB/data audio input using that model's manual. Set an appropriate operating mode and data input gain. Use the radio's VOX/data VOX if supported, or a separate compatible serial PTT interface. Selecting a CAT COM port is insufficient: this pilot does not send CAT commands.

For an FM mobile such as a Kenwood TM-V71A or TM-281, use an interface matched to that radio's audio input, ground and PTT connections. Some data connectors provide different receive audio pins and levels; transmission needs the transmit audio path and optional receive monitoring needs a separate receive audio path. Do not infer a pinout or level from another Kenwood model. Use the exact radio and interface manuals before making a cable. Select VOX only if the radio/interface actually keys from the provided audio. Otherwise use a compatible RTS/DTR interface with verified polarity.

For a RIM/CM108 interface, Windows may expose usable audio but the app does not drive its HID PTT. Use a separately supported PTT path or an already configured VOX interface. A repeater controller's COS/COR, CTCSS and flat/deemphasized audio paths need a controller-specific integration; choosing an audio device does not implement those functions.

Preview CW and voice locally first. With the test radio path ready, enable RF to send the initial ID and verify keying, lead/tail timing, volume and release. Stop RF while an item is playing and verify unkeying. Test device unplug and source failure before normal operation. Check FM deviation with appropriate equipment; this app has no deviation measurement or hardware carrier detector. Audio Morse IDs are transmitted audio, not direct hardware CW keying.

For exact model menus and pinouts, record the radio model, interface model, connector used and whether the intended path is FM, SSB or repeater-controller audio. Those details are required before a model-specific wiring guide can be verified.


## Receive audio transmit hold

In Audio / PTT, enable Monitor radio receive audio and choose the exact Receive input name. Connect the radio’s receive audio through a suitable sound input interface. A PC DB9 serial port cannot carry this audio. Use the exact radio manual for connector assignments and acceptable levels. Use line level or an appropriately attenuated and isolated output rather than wiring a speaker output directly into a microphone input.

Use Test receive input while output is stopped. The level display reports RMS dBFS, where zero is full scale and negative values are quieter. Set Audio threshold above idle noise but below normal received speech. Lower numbers detect quieter signals. The supported threshold is minus 60 to minus 5 dBFS and the default is minus 40. Testing reads the input without transmitting, saving audio or sending it to any service. Stop receive test closes the input. Save and apply to use the chosen settings for RF.

Quiet delay ranges from 5 to 10 seconds and defaults to 7. Enabling RF with monitoring selected opens the input and waits for a complete quiet interval before the initial ID. Detected audio resets that interval. Both queued spots and due IDs wait while receiving or counting down; due IDs take priority when the input clears. Spots that expire while waiting are discarded and the queue remains bounded. Local listening and local previews are unaffected.

If audio arrives during transmission, playback is cancelled, PTT is released and that announcement or ID is retried after the quiet delay if still eligible. The transmit watchdog remains active. Stop, source failure and settings edits still disable output. A missing, failed or stalled input stops RF and requires explicit enable again after correction. There is no automatic fallback to unmonitored transmission.

Use a squelched receive output that goes quiet when the channel clears. Continuous unsquelched noise can hold RF indefinitely. Disable microphone enhancements and automatic gain that obscure the threshold. Do not select a desktop microphone, Stereo Mix or a radio monitor path carrying DX Talker’s own transmit audio. Self audio or radio sidetone can cause repeated cancellations. Check input monitoring behavior while transmitting with your particular interface. Audio detection can miss silent carriers and quiet speech; it cannot guarantee collision avoidance. Hardware carrier or COR input is future work. Receiver wiring, duplex endpoint behavior, threshold and PTT release need acceptance on the actual radio before unattended use.
