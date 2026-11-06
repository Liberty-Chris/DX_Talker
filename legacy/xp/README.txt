DX Talker experimental XP listening source test kit

This is a separate minimal TCP/SAPI test client, not the modern Windows app.
It requires a separately installed, genuine Windows XP compatible Python 3.4
runtime with Tkinter and Windows SAPI 5 / cscript. No original DX Talker binaries
are used. Double-click start.bat after installing that runtime.

Scope: one TCP cluster, visible status, local default-device speech, a bounded
spot/speech view and local rotating failure categories. Stop listening terminates
the client speech process. It does not provide RF, PTT, HTTPS, profiles, QR import,
modern updater, current announcement customization or complete Telnet parity.
Passwords are session-only. TCP sends login data without encryption.

No claim of XP runtime or radio acceptance is made until a named XP machine or
VM has been tested. Source syntax and parser checks in modern CI do not establish
that acceptance. Test first with a local fixture and audio disconnected from RF.
Windows XP x86 SP3 and XP x64 SP2 need separate recorded acceptance.

Modern Windows x86 installers are for Windows 10 22H2, not XP. A complete XP port
remains a separate implementation and verification task.
