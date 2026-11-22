# Radio audio and PTT

## Choose outputs

Local preview output is the device used by preview controls. Radio audio output is the device used while RF is enabled. Choose exact device names and prefer Windows WASAPI where available. Save and apply settings.

A preview can still reach the radio if both roles use the same device. This is particularly relevant for VOX, which can key from any incoming audio. Separate local and radio outputs for listening tests.

The app resolves the selected device before playback. Missing or ambiguous names stop output instead of falling back to another device. Refresh audio and serial devices after connecting an interface. Refreshing disables RF.

## Monitoring RF locally

Select separate local speakers and radio audio outputs, then enable both RF and Listen locally from Live spots. The local control reads Monitoring RF. Spots and IDs are synthesized once and played through both destinations during the same transmission. Local mute and volume affect speakers only. Receive hold delays both streams until the channel is clear. In full duplex mode, returning receive activity interrupts both. PTT is released independently of local speaker cleanup. A local speaker fault mutes monitoring and reports the problem while RF continues. Radio or receive input faults stop both outputs.

Half duplex: ignore audio during own transmit is enabled by default under Receive audio transmit hold. Apply radio changes to activate edits. Use it for an HT or an interface that returns transmitted audio to the receive input. DXt ignores busy audio from immediately before keying until release. Input faults, Stop and the transmit watchdog remain active. After PTT release, the detector ignores receive activity for one second while relay switching and remaining transmitted audio settle. It then requires a fresh receiver frame. Quiet audio allows the next transmission without a quiet countdown. Only audio detected above the threshold during normal receiving creates a traffic hold. The meter labels own transmit and settling states while continuing to show measured levels. Turning receive volume down is unnecessary and would prevent detection of real received signals.

Disable half duplex only with an independent receive path that can hear other stations during transmission and does not contain DXt audio. That restores immediate busy audio interruption. A simplex HT cannot reliably detect another caller while it is transmitting. This option cannot distinguish voices or remove a wiring loop. Keep Windows microphone feedback and Listen to this device disabled on the Digirig unless deliberately routing receiver audio to separate speakers for a test.

Disable RF retains local listening. Stop all output and Escape stop both. Local monitoring does not play received radio audio. It plays DX Talker announcements. Separate devices can have different output latency.

## PTT methods

VOX sends audio without controlling a PTT line. Your radio or interface must already be configured to key from that audio.

RTS, DTR and RTS+DTR control compatible serial PTT wiring. Select the COM port and PTT active high setting. Unchecking active high reverses the selected line's polarity. Unused lines stay low. Serial flow control is not used.

On modern Windows, CM108 HID controls the DigiRig Lite's USB PTT on GPIO3. Select its USB PTT device separately from its audio input and output. CAT and vendor specific interfaces still need separate adapters.

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

While enabled, the button has an accent border and reads RF enabled. Hover or keyboard focus turns it red and changes the text to Disable RF. Clicking stops current and queued RF output without disconnecting the source or clearing the live view. It shows Stopping while cancellation finishes. Stop All Output, faults, source loss and settings changes also return it to the disabled state. Startup never enables RF automatically. Reconnect leaves it off unless the applied Resume RF after source reconnect option is enabled for a previously active session.

Without a source, RF can still send initial, periodic and manually requested IDs. Only new validated live spots are eligible for RF announcements; sample rows and displayed history are not queued. Optional receive audio monitoring can hold RF when audio is detected; it is not a carrier detector. Supervise operation on a clear or coordinated channel. Shared local and radio devices may send previews to a VOX radio; use separate outputs for listening tests.


## Compact Audio / PTT controls

Audio outputs, Push to talk, Transmit timing and Audio levels are separate compact groups. Device selectors have bounded widths and numeric fields show their units and ranges. Refresh devices updates audio, serial and USB PTT choices. Each PTT method shows only its relevant fields and retains the other methods’ saved selections. Use Apply radio changes to activate edits for normal output.

## Radio setup recipes

Start with RF disabled and a monitored test path. Choose the exact radio audio output and a separate local speaker/headphone output. Avoid device defaults that can change after a USB reconnect. Turn off Windows audio enhancements and spatial processing for the radio output, then start the application's spot and ID gains low and increase while monitoring the transmitted audio. Device selection and a working USB cable do not establish a safe level or compatible PTT wiring.

For an HF transceiver with built in USB audio, select its USB audio device and select the radio's USB/data audio input using that model's manual. Set an appropriate operating mode and data input gain. Use the radio's VOX/data VOX if supported, or a separate compatible serial PTT interface. Selecting a CAT COM port is insufficient: this pilot does not send CAT commands.

For an FM mobile such as a Kenwood TM-V71A or TM-281, use an interface matched to that radio's audio input, ground and PTT connections. Some data connectors provide different receive audio pins and levels; transmission needs the transmit audio path and optional receive monitoring needs a separate receive audio path. Do not infer a pinout or level from another Kenwood model. Use the exact radio and interface manuals before making a cable. Select VOX only if the radio/interface actually keys from the provided audio. Otherwise use a compatible RTS/DTR interface with verified polarity.

For a DigiRig Lite on modern Windows, connect the Lite and click Refresh devices. Choose CM108 HID and select the Lite under USB PTT device. Its descriptor may read USB Audio Device with a reference in brackets. If multiple entries have the same name, refresh with the Lite disconnected and again with it connected to identify the matching reference. Moving the Lite to a different USB port may require selecting it again. Set Radio output and, when receive monitoring is enabled, Receive input to the Lite’s Windows sound devices. With output stopped, use Test PTT for 2 seconds and confirm the radio keys and returns to receive. Apply radio changes for IDs and announcements. Physical acceptance of other CM108 interfaces is still pending. Repeater controller integration also needs its own audio and receive signaling support.

Preview CW and voice locally first. With the test radio path ready, enable RF to send the initial ID and verify keying, lead/tail timing, volume and release. Stop RF while an item is playing and verify unkeying. Test device unplug and source failure before normal operation. Check FM deviation with appropriate equipment; this app has no deviation measurement or hardware carrier detector. Audio Morse IDs are transmitted audio, not direct hardware CW keying.

For exact model menus and pinouts, record the radio model, interface model, connector used and whether the intended path is FM, SSB or repeater-controller audio. Those details are required before a model-specific wiring guide can be verified.


## Receive audio transmit hold

In Audio / PTT, enable Monitor radio receive audio and choose the exact Receive input name. Connect the radio’s receive audio through a suitable sound input interface. A PC DB9 serial port cannot carry this audio. Use the exact radio manual for connector assignments and acceptable levels. Use line level or an appropriately attenuated and isolated output rather than wiring a speaker output directly into a microphone input.

Use Test receive input while output is stopped. The level display reports RMS dBFS, where zero is full scale and negative values are quieter. Set Audio threshold above idle noise but below normal received speech. Lower numbers detect quieter signals. The supported threshold is minus 60 to minus 5 dBFS and the default is minus 40. Testing reads the input without transmitting, saving audio or sending it to any service. Stop receive test closes the input. Save and apply to use the chosen settings for RF.

The received traffic hold is fixed at five seconds. Existing saved settings migrate from the previous delay to five seconds. Enabling RF with monitoring selected opens the input and requires fresh samples before the initial ID. Quiet input is immediately clear; startup alone does not create a countdown. Detected audio above the configured threshold blocks RF until five continuous seconds after it ends. More detected audio restarts the hold. Both queued spots and due IDs wait while receiving or counting down; due IDs take priority when the input clears. Spots that expire while waiting are discarded and the queue remains bounded. Local listening and local previews are unaffected.

With half duplex disabled, audio arriving during transmission cancels playback, releases PTT and allows that announcement or ID to retry after the quiet delay if still eligible. With half duplex enabled, busy audio during own transmit and the one second settling period is ignored. Once fresh receiver audio is quiet after settling, the next item can transmit without another traffic hold. The transmit watchdog remains active. Stop, source failure and settings edits still disable output. A missing, failed or stalled input stops RF and requires explicit enable again after correction. There is no automatic fallback to unmonitored transmission.

Use a squelched receive output that goes quiet when the channel clears. Continuous unsquelched noise can hold RF indefinitely. Disable microphone enhancements and automatic gain that obscure the threshold. Do not select a desktop microphone or Stereo Mix. If the interface returns transmit audio or radio sidetone, use half duplex mode to prevent repeated self cancellations. Check input monitoring behavior while transmitting with your particular interface. Audio detection can miss silent carriers and quiet speech; it cannot guarantee collision avoidance. Hardware carrier or COR input is future work. Receiver wiring, duplex endpoint behavior, threshold and PTT release need acceptance on the actual radio before unattended use.

## Test PTT

With output stopped, choose the serial method, port and polarity or choose CM108 HID and its USB device. Click Test PTT for 2 seconds. The test uses the visible settings without applying unrelated source or ID edits. It needs no cluster, spoken ID or audio output. It asserts the selected PTT for two seconds and releases it through the same coordinator, cancellation path and watchdog used by normal radio output. Stop All Output or Escape cancels it immediately. RF remains disabled afterward. No separate test path bypasses serialization.

When receive monitoring is selected, the test first opens that input and requires fresh receiver samples. Quiet input is immediately clear; detected receive audio requires five seconds of silence afterward. In full duplex mode, incoming audio interrupts keying and releases PTT. In half duplex mode, busy audio is ignored while keyed and during one second of settling after release. A fresh quiet sample after settling permits the next item; only actual detected receive activity creates the five second hold. Input failure stops the test in either mode. VOX cannot be tested by toggling a serial line; use an appropriately monitored audio/ID test after setting up the radio path. VOX lead time remains receive guarded because audio has not yet keyed the radio.

RTS/DTR line control does not send CAT bytes, so it does not need a user selectable baud rate. A radio's CAT baud setting does not establish compatibility with serial line PTT. CAT remains a separate future adapter.

The receive meter separates input health from sound level. Before the first frame it says there is no measurement. Missing initial frames, an inactive device, stale samples and invalid callback data have distinct explanations and diagnostic codes. A displayed quiet level does not establish that a failed input is healthy. A transient input overflow restarts the entire quiet countdown; unrecognized driver faults remain latched until the input is reopened. Channel clear describes measured channel audio, not RF being armed. Correct the input and deliberately enable RF after a fault.

Once the input has delivered valid samples, a gap longer than one second pauses transmission and releases PTT if keyed. If valid samples return before 60 seconds have elapsed since the last good block, the current RF session continues and any eligible interrupted item can start again. When receive traffic was detected before the gap, the five seconds of quiet must come from fresh audio. A quiet channel without detected traffic can clear as soon as fresh samples return, subject to relay settling. A gap of 60 seconds, inactive stream, invalid audio or driver fault disables RF and requires manual reenable. A stream that never starts delivering samples still uses the one second startup timeout.

The Audio Output heading shows RX recoveries for the current app session, including Test receive input. Successful recoveries also appear in the session log and in exported diagnostics.

The XP pilot exposes audio through Windows MME and serial RTS/DTR through Windows communication APIs. Audio names differ from modern Windows backend names, so select and test the intended endpoints again after importing settings. Missing or ambiguous devices stop output rather than selecting default speakers. An audio driver cleanup failure requires restarting the application before reopening audio. Physical XP driver and radio behavior still require bench testing.

## Ubuntu audio and serial devices

Ubuntu uses the same audio/PTT coordinator with Linux device names. Audio still requires a separate sound interface; serial RTS/DTR controls do not carry audio. See [Ubuntu desktop](ubuntu.md) for serial permissions, stable paths and physical acceptance checks.

## Screensaver transitions and keep awake

Windows Audio / PTT includes optional Keep awake controls under Power management. Off is the default. Computer prevents automatic system idle sleep during active output; Computer and display also requests that the display stay awake. Save and apply before starting output. Requests end when output stops. They do not alter Num Lock, screensaver or lock settings. Modern buffering tolerates isolated spot underruns, while interrupted IDs and persistent audio faults still stop RF. See [Screensaver transitions and keep awake](troubleshooting.md#screensaver-transitions-and-keep-awake) for recovery limits, diagnostics and the physical retest.

## Beta radio configuration

Radio edits are preserved as drafts. Apply radio changes applies radio, PTT, receive and ID settings together after output cleanup. RF remains disabled until Enable RF. Ordinary listening preferences save independently. The receive meter marks the configured threshold. Local preview routing is indicated inline rather than requiring repeated approval. [Operation and saving](usability.md) describes the full workflow.

## Resume RF after source reconnect

In Audio / PTT under Transmit timing, Resume RF after source reconnect is off by default and is a radio draft until Apply radio changes. When enabled, a source loss still stops audio, clears queued spots and releases PTT. If RF had been enabled, the current session remembers that intent and shows that automatic RF recovery is waiting for the source. A connection socket alone is insufficient. Recovery waits for recognized sign in confirmation or valid feed data and for receiver cleanup. It then revalidates the radio configuration, restarts receive monitoring and sends the required ID before new spot announcements. Receive quiet time, transmit duration and normal fault handling still apply.

Stop all output, Disable RF, manual Disconnect or source switching, a new manual output/preview session, application restart and an output fault cancel pending recovery. A failed recovery or failed ID stays stopped rather than repeatedly retrying a failed audio device. The saved option never enables RF at startup. Previously queued spots and missed calendar messages are not replayed. Local monitoring and mute state from the previously enabled RF session are restored. This option only covers source outages; it does not recover unplugged radios, failed drivers or invalid IDs.
