# Original DX Talker files

This directory preserves the historical DX Talker archive supplied for the modernization project. Kevin Leggett and Dave Hockaday created the original application in the early 1990s, according to the project history supplied by Chris Hockaday.

The original monitored a DX cluster through a TNC packet node and retransmitted the information over RF, with periodic voice and CW identification. The QST publication reference and exact release chronology remain unverified.

## Archive contents

The preserved file is [DX Talker archive](DX-TALKER-20261014T212211Z-1-001.zip). It contains 107 file entries under `DX-TALKER/`. The three principal directories are `DXTALK/`, `dxtalk1/` and `dxtalker/`.

The archive includes seven EXE files, 82 WAV files, compressed installer and runtime components, an IOPORT.VBX control, four transfer logs, a setup list, a text notice and a captured cluster session. File counts include repeated copies.

The EXE headers inspected are Windows NE executables. Embedded references to VBRUN300, MSCOMM.VBX, CMDIALOG.VBX and IOPORT.VBX are consistent with a Visual Basic 3 era Windows application. No standalone editable Visual Basic project, form or module source files were found. Form names embedded in an executable are not recovered source files.

The WAV collection contains letters, digits and phrases such as `dxspot.wav`, `khz.wav`, `point.wav` and `stroke.wav`. The inspected executables reference `ID.wav`, but no file with that name is present.

The capture at `DX-TALKER/dxtalker/wav/hyperlog.cap` contains DX spot lines alongside cluster messages and a command prompt. This is useful evidence for parser design. The archive also contains a notice dated April 2001, so its packaging should not be treated as an untouched early 1990s release.

## Preservation

The ZIP was inspected statically on October 14, 2026. No archived executable was run. Its SHA256 is:

```text
e9ac3463fae15baeff4279ad452a9471ab09bb420e7742e26e876a3da3420485
```

Keep the original ZIP unchanged. Place extracted working material outside this directory and record any derived findings in [legacy findings](../docs/legacy.md). Do not treat bundled runtime files or audio as automatically licensed for redistribution with the modern application.

See the [main README](../README.md), [roadmap](../ROADMAP.md) and [questions](../docs/questions.md) for the modernization effort.
