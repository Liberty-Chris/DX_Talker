# Radio audio and PTT

## Choose outputs

Local preview output is the device used by preview controls. Radio audio output is the device used while RF is enabled. Choose exact device names and prefer Windows WASAPI where available. Save and apply settings.

A preview can still reach the radio if both roles use the same device. This is particularly relevant for VOX, which can key from any incoming audio. Separate local and radio outputs for listening tests.

The app resolves the selected device before playback. Missing or ambiguous names stop output instead of falling back to another device. Refresh audio and serial devices after connecting an interface. Refreshing disables RF.

## PTT methods

VOX sends audio without controlling a PTT line. Your radio or interface must already be configured to key from that audio.

RTS, DTR and RTS+DTR control compatible serial PTT wiring. Select the COM port and PTT active high setting. Unchecking active high reverses the selected line's polarity. Unused lines stay low. Serial flow control is not used.

A USB audio device does not necessarily supply PTT. CM108 HID interfaces, including RIM devices, are not controlled by these serial modes. CAT and vendor specific interfaces are also not included yet. Exact hardware compatibility needs a bench test.

## Timing and level

PTT lead time delays playback after keying. Tail time delays release after audio ends. Maximum transmit seconds includes lead, playback and tail. Audio that cannot fit within this limit is rejected before keying. A watchdog makes a separate release attempt if output stalls.

Spot radio level, CW ID level and Voice ID level have independent percentage controls from zero to 100. Zero mutes that category. CW and voice levels are applied independently even in a combined ID. Local listening level additionally scales local previews and live local announcements. Set the radio's input gain using the interface and radio instructions. This app does not measure deviation.

## Stop and faults

STOP ALL OUTPUT cancels pending work and attempts release. Source loss, output errors and settings changes disable RF. Wait for Idle before applying changes and explicitly enable output after recovery.

Some serial drivers can pulse control lines when a port opens. Test that behavior before connecting PTT for normal use. Software cannot guarantee release after forced process termination, USB failure or a hardware latch. Verify your station's physical stop method and any interface timeout.

## RF toggle

Enable RF uses saved radio and ID settings without applying pending edits or changing the cluster connection. A connected source, a valid received spot, a supervision acknowledgement and a shared device confirmation are not prerequisites. The radio output and the ID settings still must be valid, and any current output must finish before enabling. Save and apply configuration changes first.

While enabled, the button has an accent border and reads RF enabled. Hover or keyboard focus turns it red and changes the text to Disable RF. Clicking stops current and queued RF output without disconnecting the source or clearing the live view. It shows Stopping while cancellation finishes. Stop All Output, faults, source loss and settings changes also return it to the disabled state. Startup and reconnect never enable RF automatically.

Without a source, RF can still send initial, periodic and manually requested IDs. Only new validated live spots are eligible for RF announcements; sample rows and displayed history are not queued. The pilot does not detect a busy channel. Supervise operation on a clear or coordinated channel. Shared local and radio devices may send previews to a VOX radio; use separate outputs for listening tests.


## Compact Audio / PTT controls

Audio outputs, Push to talk, Transmit timing and Audio levels are separate compact groups. Device selectors have bounded widths and numeric fields show their units and ranges. Refresh devices updates both audio and serial choices and stops output as before. VOX hides serial port and polarity fields; choosing a serial PTT method shows them again with their saved values. Changing the visible method does not change the configured hardware until settings are saved and applied. CM108 HID and CAT remain outside this pilot.

## Radio setup recipes

Start with RF disabled and a monitored test path. Choose the exact radio audio output and a separate local speaker/headphone output. Avoid device defaults that can change after a USB reconnect. Turn off Windows audio enhancements and spatial processing for the radio output, then start the application's spot and ID gains low and increase while monitoring the transmitted audio. Device selection and a working USB cable do not establish a safe level or compatible PTT wiring.

For an HF transceiver with built in USB audio, select its USB audio device and select the radio's USB/data audio input using that model's manual. Set an appropriate operating mode and data input gain. Use the radio's VOX/data VOX if supported, or a separate compatible serial PTT interface. Selecting a CAT COM port is insufficient: this pilot does not send CAT commands.

For an FM mobile such as a Kenwood TM-V71A or TM-281, use an interface matched to that radio's audio input, ground and PTT connections. Some data connectors provide different receive audio pins and levels; this app needs the transmit audio path. Do not infer a pinout or level from another Kenwood model. Use the exact radio and interface manuals before making a cable. Select VOX only if the radio/interface actually keys from the provided audio. Otherwise use a compatible RTS/DTR interface with verified polarity.

For a RIM/CM108 interface, Windows may expose usable audio but the app does not drive its HID PTT. Use a separately supported PTT path or an already configured VOX interface. A repeater controller's COS/COR, CTCSS and flat/deemphasized audio paths need a controller-specific integration; choosing an audio device does not implement those functions.

Preview CW and voice locally first. With the test radio path ready, enable RF to send the initial ID and verify keying, lead/tail timing, volume and release. Stop RF while an item is playing and verify unkeying. Test device unplug and source failure before normal operation. Check FM deviation with appropriate equipment; this app has no deviation measurement or busy channel detector. Audio Morse IDs are transmitted audio, not direct hardware CW keying.

For exact model menus and pinouts, record the radio model, interface model, connector used and whether the intended path is FM, SSB or repeater-controller audio. Those details are required before a model-specific wiring guide can be verified.
