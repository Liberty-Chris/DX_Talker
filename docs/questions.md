# Open questions

Updated October 17, 2026. Record answers here with the date, evidence and any resulting decision.

## Needed before implementation commitments

| ID | Question | Why it matters | Source of answer |
| :--- | :--- | :--- | :--- |
| Q01 | Which radio and USB interface should be supported first? | Determines audio connection and PTT control method | Chris and interface documentation |
| Q02 | What exact prompts and login fields does W4MR require? | Defines source authentication without guessing | Authorized operator transcript and service operator |
| Q03 | Is the initial source the supplied TCP/Telnet service, a web feed or both? If a web feed, which URL and format? | Sets first release scope | Chris and source provider |
| Q04 | Which Windows versions and processor architectures are required? | Controls stack, packaging and test targets | Chris and pilot users |
| Q05 | Should voice and CW IDs alternate or both run, at what intervals and after which transmissions? | Defines scheduler behavior | Chris and station operating policy |
| Q06 | How will channel availability be established for automatic announcements? | Audio plus PTT does not necessarily supply a busy signal | Station operator and selected hardware |
| Q07 | Which spot fields, filters and repeat limits should be spoken? | Controls usefulness and channel occupancy | Chris and pilot operators |

## Useful questions for Dave Hockaday (WB4IUY)

| ID | Question | Evidence so far |
| :--- | :--- | :--- |
| H01 | What QST issue, article title and author credits describe DX Talker? | History supplied by Chris; citation not in reviewed files |
| H02 | What PTT interface and port wiring did the original use? | IOPORT.VBX appears in archive |
| H03 | How were CW and voice IDs scheduled and configured? | ID.wav is referenced but absent; CW behavior supplied by Chris |
| H04 | Are the original Visual Basic source and missing ID recording still available? | Archive contains compiled programs and audio assets |
| H05 | Which original behaviors should the modern application preserve? | Spot capture and speech fragment filenames offer partial clues |

Ask about gaps that affect a concrete decision. Work on known requirements can proceed without recovering every historical detail.

## Release decisions

The current policy reserves all rights in the modern project and separately preserves the rights of the historical archive's applicable holders. See [the modern project notice](../LICENSE) and [the original files notice](../Original_Files/LICENSE). Confirm current historical ownership, any original publishing agreements and permissions before reusing or distributing historical assets. Any later public license requires appropriate authorization and an explicit scope. Decide application name and versioning, distribution channel, update strategy and supported hardware list before releasing an installer.

## Resolved clarifications

On October 14, 2026, inspection established that the supplied address is a host and port example for TCP/Telnet rather than an identified HTTP feed. This does not resolve Q03 or verify the service itself.

On October 14, 2026, static archive inspection found no editable Visual Basic source files. Modern development can proceed from documented requirements without assuming those files exist.
