# Windows XP application port

The target is the full desktop application's core behavior on Windows XP x86 SP3 and Windows XP x64 SP2: saved cluster collections, local filters and license rules, announcement customization, local listening, explicit radio audio, serial PTT, receive audio supervision, voice/CW identification, history, diagnostics, profile transfer and verified update discovery.

The small client under legacy/xp remains a limited source test kit. It is not the application port and must not be presented as equivalent by giving it an installer.

The port reuses the maintained desktop UI, settings, parsers, filters and transmission coordinator. A checked build transformation targets the Python 3.4 syntax supported by the official XP compatible runtime. Compatibility modules supply newer standard library interfaces. Windows XP adapters supply system speech, selected audio I/O and serial control through APIs available on XP. Native adapters remain behind the existing coordinator, including cancellation, maximum duration, receiver quiet delay and failure release behavior.

Installers must bundle a private runtime. They must not require an operator to install Python, change PATH or replace another Python installation. XP x86 and x64 packages are built and checked separately. Contemporary Windows installers retain their existing updater filenames; descriptive release labels identify OS, bitness and installer versus portable packages.

Build verification must execute the transformed code using the actual bundled interpreter, verify native binary architecture and required runtime libraries, exercise shared policy fixtures, test adapters with simulated hardware and verify install, shortcuts, launch, reinstall and removal. No automated test may key a radio or submit a public spot. Hosted modern Windows checks do not establish XP acceptance. Each XP architecture still requires a named physical machine or VM test before its runtime and hardware behavior can be claimed verified.

Both private runtime installers are built for XP acceptance testing. Shared core behavior and hosted installation checks pass; feature acceptance on actual XP systems remains open.

The private x86 and x64 interpreters now stage successfully in hosted Windows checks. The first actual interpreter run exposed a Windows path normalization conflict in the compatibility layer. A regression fixture covers both internal string normalization and atomic settings replacement. Installer compilation and shared interpreter checks remain mandatory before any installer artifact is offered.

The hosted x64 runtime intermittently exited with access violation 0xc0000005 in `_ssl.pyd`. The bundled OpenSSL 1.0.2d falls within the SHA instruction dispatch versions described in [Intel's upstream advisory](https://www.intel.com/content/www/us/en/developer/articles/troubleshooting/openssl-sha-crash-bug-requires-application-update.html). The XP launcher sets `OPENSSL_ia32cap=:~0x20000000` in its own process before starting private Python. Build checks use the same setting and verify known SHA1/SHA256 results plus public update HTTPS. This selects an alternative implementation of the same algorithms; it does not disable certificate or hostname checks and does not alter global Windows environment settings. The legacy runtime remains an acceptance-test dependency, not a claim of a currently maintained cryptographic stack.

## Build and verification

Use the Windows pilot workflow. Its reusable XP jobs fetch and verify the pinned dependencies, stage each private runtime, compile the native launcher and Inno Setup 5.6.1 installer, run 148 shared checks with each actual interpreter and test source and installed application behavior. Full source verification passes 218 local tests. The installed checks include the same startup, navigation, scrolling and idle CPU budgets as the modern desktop build. The runtime directories and private CRT binaries are checked for matching PE architecture. Official Python MSI metadata is adjusted only in a disposable extraction copy to include its private CRT; executable payloads remain unchanged.

The [verified XP run](https://github.com/Liberty-Chris/DX_Talker/actions/runs/42464870470) includes the two installer artifacts and per architecture JSON reports. A failed XP job blocks release publication. After merging and publishing, the same two installers appear under their explicit XP download labels. The old listener kit is retained as a developer artifact rather than included in the application downloads.

| Acceptance target | Remaining evidence |
| :--- | :--- |
| Windows XP x86 SP3 | Named VM or physical install, UI/speech/QR/HTTPS, repeated restart and long session |
| Windows XP x64 SP2 | Named VM or physical install, installed SAPI availability and the same operation checks |
| Radio integration on each XP target | Selected endpoint routing, RTS/DTR polarity, receive hold, cancellation, timeout, unplug and process failure |

Do not infer XP acceptance from a modern Windows host running the older interpreter. The bundle includes an older runtime and OpenSSL, so it is a pilot compatibility target rather than a supported current security stack. External Piper binaries are not bundled or declared XP compatible. Recorded PCM packs are shared with the modern desktop application.
