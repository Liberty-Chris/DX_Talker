# Share a DX spot

Spot myself fills the callsign from the current cluster session. Spot a station accepts a station you worked or simply heard. Android opens the same form through Spot and offers Use my callsign. Enter the station callsign, frequency, kHz or MHz and an optional comment. Time and submitting identity are supplied through the cluster session rather than separate form fields.

Choose Send spot to validate the entered fields and submit directly. Desktop updates the normalized command beneath the fields as you type; there is no separate review button. DX Talker submits only to the TCP/Telnet cluster currently being monitored. It never sends the same spot to several nodes. Interconnected clusters may propagate it according to their routing and policies; delivery everywhere is not guaranteed. Respect the node, event and contest rules, including any restrictions on self spotting.

This form uses the common `DX frequency callsign comment` command with frequency normalized to kHz. It requires evidence of sign in or a received valid spot. A live socket alone is insufficient. HTTPS JSON feeds are read only. Some nodes have different commands or shorter comment limits; use that node's help and review its reply. The app accepts up to 100 printable comment characters and limits submissions to one per ten seconds. Callsigns, frequencies and comments cannot inject extra command lines.

Queued means the command awaits socket delivery. Sent means it was written to the current cluster connection. Neither means the cluster accepted or propagated the spot. Desktop Source activity shows redacted node replies; Android reports acceptance as unconfirmed. There is no automatic retry or universal acceptance parser. Do not resubmit just because a spot is absent from a filtered view. Check the node's response and your filters first.

Switching or losing the cluster invalidates pending submissions; they are never replayed onto the next connection. Reopen the form after switching. Spotting does not key a radio, start listening or alter filters. No live public spot is submitted by automated verification.
