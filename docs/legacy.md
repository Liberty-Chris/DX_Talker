# Notes on the original software

Reviewed October 14, 2026. The review covered the ZIP's file list, information embedded in the programs and the captured cluster session. The programs were not run, so these notes describe what the files tell us rather than how the application behaved in use.

## Evidence

| Observation | Archive location | Interpretation and limit |
| :--- | :--- | :--- |
| 107 file entries and 82 WAV entries | Entire archive | Counts include duplicate assets |
| MZ and NE headers with VBRUN300 references | dxtalk1/DXTALKER.EXE and dxtalk1/dxtest2.exe | Consistent with a Windows Visual Basic 3 era program |
| MSCOMM.VBX and serial settings text | Inspected executables | Serial communications UI existed; exact TNC setup is unconfirmed |
| IOPORT.VBX references and bundled control | Executables and dxtalk1/IOPORT.VBX | Port access dependency exists; exact PTT wiring is unconfirmed |
| DX de, dxspot.wav, STROKE and POINT strings | Inspected executables | Consistent with recognizing spots and composing audio; execution order was not recovered |
| ID.wav reference with no matching archive file | Inspected executables and archive inventory | Recording based identification is suggested; timing and fallback remain unknown |
| DXTALKER.FRM, CANSEND.FRM and TERMSET.FRM strings | Inspected executables | Embedded names exist but editable form source is absent |
| Mixed DX spots, messages and prompt | dxtalker/wav/hyperlog.cap | Parser must distinguish spot records from other cluster traffic |
| Wrapped or incomplete spot timestamps | dxtalker/wav/hyperlog.cap | Useful malformed input and framing examples |
| April 2001 event notice | dxtalk1/ve.txt | Archive includes material later than the reported original development period |

All locations above are relative to `DX-TALKER/` inside the ZIP. No standalone .vbp, .mak, .frm or .bas source files were found.

## Background

My dad, Dave Hockaday (WB4IUY), and Kevin Leggett (KT4BN) created DX Talker in the early 1990s. It monitored DX clusters through a TNC packet node, announced spots over RF and identified with voice and CW. The archive gives us useful details about the original implementation, although it doesn't answer every question.

## Working with the files

Preserve the ZIP and its checksum in [the archive description](../Original_Files/Description.md). Derive small reviewed parser fixtures in a future implementation change, with provenance and unrelated correspondence removed. Do not publish transfer log content as documentation or assume bundled recordings and dependencies may be shipped in a new installer.

## Remaining questions

I still need to confirm the QST reference, original release versions, PTT wiring and exact ID behavior. Those are questions for Dad and Kevin as we work through the design. We can start the modern implementation without recovering every original detail.
