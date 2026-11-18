DX Talker 1.0.0b7 removes unnecessary receive countdowns.

Receive hold now starts only after audio is detected above the configured threshold during normal receiving. It lasts five seconds after that audio ends and restarts if more receive audio arrives. Startup needs fresh receiver samples, but silence no longer starts a countdown.

In default half duplex mode, our own transmitted audio and one second of relay settling are ignored. Once settling ends and fresh quiet receiver audio arrives, the next transmission is eligible without another five or seven second hold. Real audio after settling triggers the five second hold. Input faults still stop RF. Existing saved quiet delay settings migrate to five seconds.

The receive labels and operator help describe these states. Announcement spacing, PTT lead and tail settings and required identification remain separate. Beta 6 filtering fixes remain included. Android version code is 26; Android remains a listener with no radio PTT.
