# Original DX Talker files

This is the original DX Talker archive. My dad, Dave Hockaday (WB4IUY), and Kevin Leggett (KT4BN) created the application in the early 1990s. I'm keeping these files together as part of bringing DX Talker forward.

The original monitored a DX cluster through a TNC packet node and retransmitted the information over RF, with periodic voice and CW identification. I'm still looking for the exact QST reference and release dates.

## Archive contents

The preserved file is [DX Talker archive](DX-TALKER-20261014T212211Z-1-001.zip). It contains 107 file entries under `DX-TALKER/`. The three principal directories are `DXTALK/`, `dxtalk1/` and `dxtalker/`.

The archive includes seven EXE files, 82 WAV files, compressed installer and runtime components, an IOPORT.VBX control, four transfer logs, a setup list, a text notice and a captured cluster session. File counts include repeated copies.

The EXE headers inspected are Windows NE executables. Embedded references to VBRUN300, MSCOMM.VBX, CMDIALOG.VBX and IOPORT.VBX are consistent with a Visual Basic 3 era Windows application. No standalone editable Visual Basic project, form or module source files were found. Form names embedded in an executable are not recovered source files.

The WAV collection contains letters, digits and phrases such as `dxspot.wav`, `khz.wav`, `point.wav` and `stroke.wav`. The inspected executables reference `ID.wav`, but no file with that name is present.

The capture at `DX-TALKER/dxtalker/wav/hyperlog.cap` contains DX spot lines alongside cluster messages and a command prompt. This is useful evidence for parser design. The archive also contains a notice dated April 2001, so its packaging should not be treated as an untouched early 1990s release.

## Preservation

The archive review on October 14, 2026 examined the files without running the old programs. Its SHA256 is:

```text
e9ac3463fae15baeff4279ad452a9471ab09bb420e7742e26e876a3da3420485
```

Keep the original ZIP unchanged. Place extracted working material outside this directory and record what you learn in [legacy findings](../docs/legacy.md). Do not treat bundled runtime files or audio as automatically licensed for redistribution with the modern application.

See the [main README](../README.md), [roadmap](../ROADMAP.md) and [questions](../docs/questions.md) for the modernization effort.

## Rights and permissions

See [the original files notice](LICENSE). All rights are reserved by the applicable copyright holders, subject to existing valid permissions, applicable law and GitHub's applicable terms. The modern project's license does not apply to this archive. Bundled components retain their own applicable rights and terms.
