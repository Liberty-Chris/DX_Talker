# Legacy inspection findings

Inspected October 14, 2026. Method: ZIP inventory, selected executable headers, printable strings and text capture review. No executable was run and no behavioral equivalence is claimed.

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

## Historical account

Chris Hockaday identifies Kevin Leggett and Dave Hockaday as the original authors and describes early 1990s QST association, TNC packet cluster monitoring, RF announcements and periodic voice and CW IDs. These are project supplied history rather than behavior verified by executing the archive.

## Reuse boundaries

Preserve the ZIP and its checksum in [the archive description](../Original_Files/Description.md). Derive small reviewed parser fixtures in a future implementation change, with provenance and unrelated correspondence removed. Do not publish transfer log content as documentation or assume bundled recordings and dependencies may be shipped in a new installer.

## Remaining questions

The QST citation, original release versions, PTT hardware wiring and exact ID behavior cannot be established from this inspection. Seek author clarification for those details if they affect modernization choices. Full source recovery is not a prerequisite for a new implementation.
