# Radio audio and PTT

Status: planned. No interface compatibility is claimed yet.

## Two separate functions

Audio carries the generated speech, recorded ID and audio Morse to the radio. PTT tells the radio when to transmit. A USB audio adapter may provide only audio. Some radio interfaces also expose a serial port or a vendor specific control for PTT.

The first supported interface and method will be named after bench testing. Do not assume a generic USB cable or every USB sound device provides both functions.

## Intended controls

Select the radio's Windows audio output explicitly. Set PTT device and control method according to the tested interface instructions. Lead time allows the transmitter to settle before audio and tail time holds it briefly after playback.

Preview uses an explicitly selected local listening device without asserting PTT. If the radio audio device disappears, RF output should stop and the application should report the fault.

## Stopping transmission

The planned stop control cancels pending RF output and attempts immediate PTT release. A maximum transmit duration bounds normal software operation. The application will document any hardware timeout or idle behavior supported by the selected interface.

Behavior after cable removal or process termination requires actual hardware testing. Recovery should require the operator to reenable RF deliberately.

## Shared channels

Channel availability detection is not yet designed. USB audio and PTT alone may not tell the application whether another station is using the frequency. Supported automatic operation will depend on a confirmed station and channel access policy.
