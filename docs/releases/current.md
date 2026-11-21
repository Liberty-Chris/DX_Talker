DX Talker 1.0.0b8 improves recovery when receive audio briefly stops.

After one second without fresh samples, DX Talker pauses RF and releases PTT if keyed. When valid samples return before 60 seconds have elapsed since the last good sample, the radio session can resume. If the gap reaches 60 seconds or the device reports a capture fault, RF disables and must be reenabled manually.

The Audio Output heading shows how many times receive audio has recovered in the current session. Exported diagnostics describe the length and outcome of each interruption.

The five second quiet period still applies after detected traffic. Android remains a listener and uses version code 27.
