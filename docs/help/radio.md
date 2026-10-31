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

Audio level percent scales generated audio and WAV playback. Set the radio's input gain using the interface and radio instructions. This app does not measure deviation.

## Stop and faults

STOP ALL OUTPUT cancels pending work and attempts release. Source loss, output errors and settings changes disable RF. Wait for Idle before applying changes and explicitly enable output after recovery.

Some serial drivers can pulse control lines when a port opens. Test that behavior before connecting PTT for normal use. Software cannot guarantee release after forced process termination, USB failure or a hardware latch. Verify your station's physical stop method and any interface timeout.

The pilot does not detect a busy channel. Enable RF only under the supervised channel policy acknowledged in Announcements.
