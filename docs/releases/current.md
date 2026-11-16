DX Talker 1.0.0b3 is the final feature beta before stable v1 acceptance.

IDs adds up to 20 named scheduled voice messages using generated speech or PCM WAV recordings. Choose interval, daily, weekly, monthly weekday, monthly date or one time schedules, multiple daily times, date limits and a daily window. First Tuesday reminders at two times are supported. Existing CW and primary voice ID settings are preserved. Due station identification stays ahead of scheduled messages and all audio uses the existing transmission coordinator, receive hold, maximum duration and Stop control. Missed disabled times are skipped and busy messages expire after a bounded grace period.

Cluster retries create fresh sockets and log attempt numbers and bounded delays. Successful sign in or feed reception resets backoff. Receiver cleanup is separated from the source retry worker. Quiet source status clears when data resumes. Source loss and output faults still disable RF; reconnect never rearms it.

Explicitly applying valid radio settings preserves previously enabled RF and local monitoring after cleanup, with required identification first. Invalid drafts leave the running configuration alone. Stop, source loss and output faults prevent resumption. The footer now shows a neutral saved confirmation and disables Radio settings saved when no edits are pending. Enabled accent buttons have visible hover feedback.

WB4IUY's supplied table is preserved and compiled for desktop and Android. All twenty named modes are supported with DIGITAL and Unknown kept distinct. The eleven CW inference ranges are unchanged and license authorizations remain separate from the table's listening ranges. IOTA, JOTA, LLOTA and special calls filters work on both platforms, including portable variants and Only these calls. The same decision governs display and speech.

A compact getting started guide opens in desktop Help and remains available offline with connection and troubleshooting topics. Additional guides link to https://wb4iuy.net/dxtalker/. Android's Open Help action uses the same destination.

Features are frozen after this batch. Stable v1 preparation follows regression testing and operator acceptance on actual computers, phones and radio interfaces. This beta does not establish physical RF or Windows 10 overnight acceptance.
