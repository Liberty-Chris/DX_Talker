# Troubleshooting

This is a draft of the troubleshooting guide. We'll add the application's actual messages and controls as they're built.

## Cannot connect to the source

Check source type, hostname and port or supported feed URL. The W4MR example is a TCP/Telnet host and port rather than an HTTP URL. Check whether the application reports a network failure or an incomplete sign in.

If the service's prompts have changed, retain a sanitized diagnostic excerpt for investigation. Never include passwords or access tokens in a report.

## Connected but no spots appear

A connection may still be awaiting login. The source may be quiet or incoming records may be rejected as chat, banners or malformed lines. The intended diagnostics should distinguish these cases.

## Preview sounds wrong

Confirm the local listening device and voice selection. Listen to callsign digits, portable suffixes and decimal frequencies. Report the sample text and chosen voice when pronunciation is ambiguous.

## Radio has no audio or does not key

Verify the selected radio audio endpoint and the independently configured PTT method. USB audio alone may not include PTT. Interface specific connection and level guidance will be supplied after hardware validation.

## An audio device disappears

The intended behavior is to stop RF output, release PTT where possible and report the missing device. Reconnect and select the correct device, then deliberately enable RF after checking configuration.

## Transmission does not stop

Use the application's stop control. If hardware remains keyed, use the station's physical means of stopping transmission. Preserve redacted diagnostics after control is restored. The supported interface's recovery procedure must be documented following bench tests.

## A WAV ID cannot play

Check that the recording exists and can be decoded in preview. Replace or reselect it, or explicitly choose generated speech. Do not assume the app silently substitutes another ID.

## Reporting a problem

Include the released application version, Windows version, radio interface model, PTT method, source type, observed behavior and redacted diagnostics. The future Info section should make version information easy to copy.
