# Story 7.7 visual check (Spillinnsikt)

Fresh Class game, 2 Students and 2 Rule-based players, 4 Weeks opened. The «marks» shots stub the insight answer (takeover, guard switch, fallbacks, reclaim); all others are the live api. Chromium `--lang=nb-NO`.

- `spillinnsikt-running-390.png` Running game at 390 px: crumb, «Spill 1» with «Pågår», four Seats stacked Fabrikk first with the link-slot text, one table per Role; only the tables scroll sideways (right fade), page does not. Matches DESIGN.md/EXPERIENCE.md, no primary button.
- `spillinnsikt-running-1280.png` Same at 1280 px: Seats in four columns, tables full width with every column and Merknad. Matches.
- `spillinnsikt-running-1280-200.png` Same at 200 % text: no page-level sideways scroll, tables scroll in their regions, Seats in four columns (cramped but readable; the 200 % is simulated by font-size, so rem breakpoints do not move). Matches.
- `spillinnsikt-marks-390.png` Marks stubbed, 390 px: Merknad is off-screen right, rows with a mark wrap taller (12 em minimum); nothing cut off. Matches, minor uneven row height.
- `spillinnsikt-marks-1280.png` Marks stubbed, 1280 px: «KI tok over etter ventetiden», «Reserveordre: KI svarte ikke i tide», «Byttet til regelbasert KI (spillvakt)», «Reserveordre: KI ga ugyldig svar. Studenten tok setet tilbake» in Merknad; open Week's Order empty. Matches.
- `spillinnsikt-marks-1280-200.png` Marks stubbed, 200 % text: as above, Merknad scrolls inside the region. Matches.
- `oversikt-back-focus-1280.png` Oversikt after Back from Spill 1: focus ring on the game's first wall cell («Spill 1, Uke 1: Netto lager 12.»), URL back to bare `/oversikt`. Matches.
- `oversikt-back-focus-390.png` Same at 390 px, focus on the same cell. Matches.
- `spillinnsikt-refused-student-390.png` A Student of the game opening the address: «Du har ikke tilgang til denne siden.» and «Til Hjem»; no game data. Matches.
- `spillinnsikt-refused-student-1280.png`, `-1280-200.png` Same at the other widths. Matches.

Deviation left for judgement: the mockup (`09-alle-sider.png`, «Spillinnsikt (uke for uke)») draws a Rolle × Uke matrix with a chain graph; Story 7.7 builds Weeks-as-rows tables per Role by spec decision, the matrix and charts are Story 7.8.
