# Spot mode classification

Updated November 8, 2026.

The same classification and filter decision selects live rows and announcements. Explicit structured mode metadata wins. Otherwise one recognized comment mode wins. USB and LSB normalize to SSB and PSK31, PSK63 and PSK125 normalize to PSK. Conflicting tags and recognized unsupported modes stay Unknown. Only reports with no mode evidence use frequency inference.

The baseline below uses conservative common CW portions of the published IARU regional HF plans linked from the regional band plan pages. It deliberately leaves regional differences, mixed modes, beacon allocations and unreviewed bands Unknown. A preferred calling frequency is not an exclusive mode segment. The 30m subset excludes the Region 3 phone exception. No automatic callsign location inference is performed. These are operating practice classifications, not guarantees about actual transmissions or legal permissions. National usage can differ; explicit spot metadata always wins.

| Band | Lower kHz, included | Upper kHz, excluded | Inferred mode |
| :--- | ---: | ---: | :--- |
| 160m | 1810 | 1830 | CW |
| 80m | 3500 | 3535 | CW |
| 40m | 7000 | 7030 | CW |
| 30m | 10110 | 10115 | CW |
| 20m | 14000 | 14070 | CW |
| 17m | 18068 | 18095 | CW |
| 15m | 21000 | 21070 | CW |
| 12m | 24890 | 24915 | CW |
| 10m | 28000 | 28070 | CW |

SSB, FT8, FT4, RTTY, PSK, FM and AM use the same evidence rule. No uniquely identifying frequency segment for them is asserted by this baseline. An untagged spot at 14074, 14080, 14225 or 29600 kHz remains Unknown. Reports tagged with these modes still match normally, even inside a nominal CW segment. Additional reviewed exclusive segments can be added without changing the filter policy.

Sources checked November 8, 2026: [IARU regional plan index](https://www.iaru-r2.org/en/on-the-air/band-plans/), [Region 1 HF plan](https://www.iaru-r1.org/wp-content/uploads/2021/06/hf_r1_bandplan.pdf), [Region 2 plan](https://www.iaru-r2.org/wp-content/uploads/2020/02/IARU-Region-2-Band-plan.pdf) and [Region 3 plan](https://www.iaru-r2.org/wp-content/uploads/2020/02/IARU-Region-3-Band-plan.pdf). The linked editions are dated October 2020, September 2020 and September 2019 respectively. This is a conservative reviewed subset rather than a claim to implement every national plan.

The interval tables use exact decimal comparisons. Shared desktop and Android fixtures check both sides of every boundary, all supported comment modes, conflicting tags, mixed segments, explicit Unknown inclusion and band/activity intersections. The desktop table and announcement queue and Android display/speech decisions are exercised against the same fixture file.

An empty stored mode selection now means all known modes. Unknown must appear explicitly in the selection. The stored value None means no choices; it never silently broadens to all. Existing explicit selections and presets retain their choices. Older clients that do not support None must be updated before importing those presets.
