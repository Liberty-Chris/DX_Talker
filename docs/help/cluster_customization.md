# Cluster customization

This section is reserved for Dave Hockaday's (WB4IUY) cluster configuration guide. His geographic filter examples and tested commands will be added when available.

For now, connect your cluster and open Source. Use the session console to read cluster replies and the command field to send one command at a time. Commands are always visible and available on Live spots too. Cluster command syntax varies by server implementation. Consult your cluster's own help before changing filters.

Geographic filters generally select who reports a spot, rather than guaranteeing which DX stations you can hear. The application's frequency, age, duplicate and spacing controls are separate from server filters.

## Choose spots without cluster commands

Announcements now has Bands, Modes and Activities selectors. Empty selections accept all. A choice within a group accepts any selected item; selected groups must all match. For example, 20m and 40m with CW and POTA announces CW spots tagged POTA on either band. Minimum and maximum frequency limits still apply. Band ranges describe filters rather than transmitting permissions in your country.

Modes include CW, SSB, FT8, FT4, RTTY, PSK, FM, AM and Unknown. Explicit feed mode metadata takes priority. Otherwise a single recognized mode in the comment is used. USB and LSB count as SSB; PSK31, PSK63 and PSK125 count as PSK. Conflicting or absent mode information is Unknown. The app does not guess a mode just from frequency. Activities recognize POTA, SOTA and FOTA tags as whole words in comments. General means no recognized activity tag; it does not guarantee that a station is not activating something. Untagged activations cannot reliably be classified from a normal cluster feed.

Comments are bounded metadata used for matching. They are not spoken or written to history or diagnostic exports. Desktop Live spots retains received records while these filters select announcements. Android Recent spots shows matching records. Filters work on received data; they cannot recover spots already removed by server filters. Reconnect does not reset your cluster account's filters. Automatic changes to server filters remain future work because DXSpider, AR Cluster and other servers have different commands and may retain settings for other clients using your callsign.

Android has the same controls under Listen, Filters or Settings, Bands, modes and activities. Save filters applies them to the active listener without reconnecting and clears pending speech and visible results. Desktop settings retain their existing Save and apply behavior, which stops output before applying changes.
