# DXt band selection authority

band_table.csv is the exact supplied WB4IUY update received November 15, 2026. Preserve its bytes and original source/version columns. The SHA256 is embedded in both generated platform tables.

Run `python scripts/sync_band_table.py` after a reviewed source update. `--check` verifies the committed Python and Kotlin data. The current source compiles to 1075 distinct class/mode selection rules and eleven unchanged CW inference segments. Band selector treatment of 2200m and 630m remains Other, as the source conditions specify.

The kHz columns are canonical. The supplied MHz display references include inconsistent endpoints and comma decimal separators. They are retained as received and never used in comparisons. Header quoting is also retained. Empty rows are ignored. Duplicate rule rows are deduplicated during compilation without changing their selection result. Point frequencies remain exact; ranges include their lower endpoint and exclude their upper endpoint.

The table is application selection policy. Existing license authorization and FCC region logic remain separate. Its US Region 2 class/mode rows further restrict matching when a license class is selected. DIGITAL is a reported unspecified digital category, not an alias for every digital mode or Unknown. Unknown retains its separate admission and eligibility controls. Explicit mode evidence still takes priority over the unchanged CW inference ranges.

Boundary tests read the original CSV independently of the generated tables. Shared spot fixtures exercise desktop and Android display/speech admission. No actual station mode, regulatory compliance or RF reception is established by these tests.
