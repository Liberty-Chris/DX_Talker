# Station identification

Status: planned. Final scheduling and operating policy are not yet selected.

## CW identification

Enter identification text in the dedicated CW field. The proposed application turns this into audio Morse through the selected radio audio device, with configurable speed and tone and a local preview.

This design does not directly key a radio's CW key input. Any such hardware support would be documented as a separate feature.

## Voice identification

Enter voice identification text in its own field. Generated speech is the default. The intended controls allow selecting an available voice and speech rate and previewing the result locally.

Callsign pronunciation must be checked by listening to the preview. Voice availability depends on the eventual speech implementation and installed Windows voices.

## Recorded WAV identification

Choose a WAV recording as an alternative to generated speech for the voice ID. The application must verify that it can decode the file, check its duration and provide a local preview before it can be selected for RF use.

If the selected recording becomes unavailable, the application should show an actionable error. Any fallback to generated speech must be explicit and documented rather than silently changing the station's identification.

## Timing

Separate text fields do not determine whether voice and CW alternate or both transmit. That policy and its intervals are still open. Identification must receive priority over a busy queue of spots.

The completed help will describe exact intervals, overdue behavior and any end of transmission identification supported by the released scheduler.
