DX Talker 0.2.0a17 adds separate Windows XP application installers and clearer download choices.

XP packages reuse the maintained desktop application, including cluster profiles, listening filters, announcement formats, local listening, radio output, serial PTT, receiver audio hold, CW and voice IDs, history, diagnostics and collection QR transfer. They bundle their own runtime and use XP compatible system speech and audio adapters. No separate Python installation is required.

Choose the XP 32 bit installer for Windows XP SP3 or the XP 64 bit installer for Windows XP x64 SP2. These are pilot packages for XP acceptance testing. Hosted Windows build checks are separate from testing on actual XP systems and radios. Optional external speech executables need their own XP compatible versions. System speech uses installed SAPI voices; recorded voice packs remain available.

Windows 10 and 11 installers and portable downloads retain their existing filenames for updater compatibility. Release download labels and a download table distinguish system, architecture and package purpose. The older limited XP listener source kit remains a developer artifact rather than the XP application download.

The a16 automatic desktop performance checks and the a15 rendering correction are retained. Android behavior is unchanged in this batch.

This release also includes the mode filtering corrections merged from main: the spot list and speech use the same selection, missing modes are inferred as CW only in reviewed single mode segments and Include unknown explicitly controls uncertain reports. Filter selections save automatically on desktop and Android without reconnecting the cluster.
