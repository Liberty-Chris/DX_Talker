DX Talker 1.0.0b4 improves receive gating and cluster recovery during beta testing.

Source raw cluster traffic is 25 text rows tall with a separate scrollbar and the latest 500 redacted session lines. Reviewing older lines no longer forces scrolling back to the newest traffic.

Half duplex receive gating is enabled by default. Receive activity still holds transmission before keying, but the app ignores busy audio during its own transmission so interface loopback does not cancel an ID. Input faults, Stop and the transmit watchdog remain active. After release, allow 300 ms for the receiver to settle and require a fresh quiet interval. Disable half duplex only with an independent receiver to retain interruption by incoming audio during transmission.

Optional Cycle saved clusters after two retries applies on Connect. After two failed reconnect attempts, try the next saved TCP/Telnet profile using its own callsign and stored credentials. Each alternate gets an initial attempt and two retries. The saved list cycles with bounded backoff, skipping duplicate endpoints and profiles that cannot be unlocked. A quiet but open connection is not treated as failed. Old commands, spot forms and queued packets cannot cross sessions. RF recovery remains a separate explicit option and required identification stays first.

Desktop, Windows XP compatibility and Android release versions stay aligned. These new radio and Source controls are desktop features. Physical Digirig/Baofeng verification and overnight operator acceptance remain necessary before stable v1.
