# Spot mode classification

Updated November 9, 2026. US operating practice is the default on desktop and Android.

The earlier intersection of IARU regional plans is superseded. Other countries' operating restrictions do not narrow this inference table. FCC license eligibility is a separate check based on the operator's selected class and FCC operating region.

Explicit structured mode metadata wins. Otherwise one recognized comment mode wins. USB and LSB normalize to SSB and PSK31, PSK63 and PSK125 normalize to PSK. Conflicting tags and recognized unsupported modes stay Unknown. Only reports with no mode evidence use frequency inference.

## US CW inference

The HF ranges below are an application inference from ARRL's published US operating guidance, with documented digital overlaps excluded. They are not an official FCC table of CW exclusive HF frequencies. FCC section 97.305 permits data alongside CW throughout many HF segments. A Novice or Technician chart marked CW only describes that license class's permissions; it does not prove that a spotted General or Extra station is using CW.

| Band | Lower kHz, included | Upper kHz, excluded | Basis |
| :--- | ---: | ---: | :--- |
| 160m | 1810 | 1836 | Above ARRL's lower digital portion; stop before its published FT4 and FT8 activity |
| 80m | 3500 | 3570 | Lower US CW operating portion; RTTY/data starts at 3570 in ARRL guidance |
| 40m | 7000 | 7040 | Lower US CW operating portion; stop at ARRL's RTTY/data DX frequency |
| 30m | 10100 | 10130 | Lower US operating portion before ARRL's RTTY/data range |
| 20m | 14000 | 14070 | Lower US operating portion before ARRL's RTTY/data range |
| 17m | 18068 | 18095 | Exclude digital overlap beginning at 18095 in the operating guide hosted by ARRL |
| 15m | 21000 | 21070 | Lower US operating portion before ARRL's RTTY/data range |
| 12m | 24890 | 24915 | Exclude digital overlap beginning at 24915 in the operating guide hosted by ARRL |
| 10m | 28000 | 28070 | ARRL's lower preferred CW range |
| 6m | 50000 | 50100 | FCC CW exclusive segment |
| 2m | 144000 | 144100 | FCC CW exclusive segment |

An untagged 3540, 7035, 10105 or 1832 kHz report now qualifies as inferred CW. Untagged 1836, 1840, 3570, 7040, 10130, 18095, 24915 and 28070 kHz reports remain Unknown. Calling frequencies inside the selected ranges do not create holes in those ranges. Explicit FT8, RTTY or another recognized mode still wins inside a CW inference range.

No frequency inference is applied on 60m or other unlisted bands. Shared phone/digital portions remain Unknown. ARRL's general band plan and its older Considerate Operator guide differ on 28150 to 28190 kHz: one shows CW and the other shows automatically controlled data within that portion. Leave this disputed overlap Unknown rather than advertise it as exclusive CW. This is a documented source conflict, not a restriction imported from another region.

Frequency inference cannot confirm the actual transmission mode. A DX spot may concern a station anywhere. This US default does not establish the remote station's jurisdiction or guarantee its mode. Operator selected license filters remain independent of mode inference and actual transmit permission.

## Sources

Reviewed November 9, 2026. Links remain in Help instead of crowding the filter controls.

[ARRL US band plan](https://www.arrl.org/band-plan) supplies preferred operating portions and distinguishes voluntary planning from rules.

[ARRL Considerate Operator's Guide](https://www.arrl.org/files/file/conop.pdf), November 2013, supplies additional US CW and data operating references. It remains linked from ARRL's current operator guidance. Its conflicting upper 10m segment is not used for inference.

[ARRL International Digital Contest guidance](https://www.arrl.org/arrl-digital-contest) lists FT4 at 1836 to 1840 kHz and FT8 beginning at 1840 kHz. Those portions must not be guessed as CW.

[Operating procedures hosted by ARRL](https://arrl.org/files/file/DXCC/Eth-operating-EN-ARRL-CORR-JAN-2011.pdf), edition June 2010 with January 2011 corrections, identifies the 17m and 12m digital overlaps. This is used as evidence of mixed activity, not as another region's license restrictions or a new US regulation.

[FCC 47 CFR 97.305, authorized emission types](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-D/part-97/subpart-D/section-97.305) distinguishes general CW permission and shared HF emissions from the CW exclusive lower 6m and 2m segments. [ARRL US license allocations](https://www.arrl.org/frequency-allocations) explains class specific permissions.

## Shared selection behavior

SSB, FT8, FT4, RTTY, PSK, FM and AM require mode evidence; their calling frequencies alone do not prove the mode. An untagged report at 14074, 14080, 14225 or 29600 kHz remains Unknown. Reports explicitly tagged CW match on any otherwise eligible frequency, not just inside the inference ranges.

The interval tables use exact decimal comparisons. Shared desktop and Android fixtures exercise both sides of every US boundary, the expanded former regional cutoffs, explicit mode overrides, digital overlaps, conflicting evidence and the license/mode distinction. Android fixtures also assert identical display and speech decisions. The desktop receive path shares final admission with the speech queue.

An empty stored mode selection means all known modes. Unknown must appear explicitly in the selection. The stored value None means no choices; it never silently broadens to all. Saved choices and presets retain their selections. Desktop All modes, including unknown removes only the mode restriction. Band, activity, location and license checks still apply.
