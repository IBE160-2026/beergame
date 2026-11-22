# Story 7.2 screenshots (visual check)

Fresh Class with 10 Students (3 games: Spill 1 finished, Spill 2 waiting, Spill 3 running), rule-based AI; Lecturer view. Landing = bundled demo data. Compared with mockup 08-laerer-oversikt, DESIGN.md and EXPERIENCE.md.

- `oversikt-flere-spill-1280.png`: Oversikt with Matrisevegg above «Spill og seter», legend, groups Venter/Pågår/Ferdig, kjedekost column. Matches (fixed-size 15 px cells as in the mockup; the mockup's filters, median graph, right rail and Melding links belong to 7.3-7.9).
- `oversikt-flere-spill-390.png`: same at 390 px. Matches; wall scrolls inside its own region (status text runs on to the right), no page scroll (scrollWidth = clientWidth).
- `oversikt-flere-spill-200pst.png`: same at 1280 px with 200 % text. Matches; legend wraps, wall scrolls in its region, no page scroll.
- `oversikt-fokus-celle-1280.png`: Spill 2, Uke 3 focused; inset focus ring (ink frame) visible. Matches.
- `oversikt-fokus-celle-390.png`: same at 390 px. Matches.
- `oversikt-for-start-390.png`, `oversikt-for-start-1280.png`: before the Start date, no wall, allocation only. Matches.
- `landing-matrisevegg-1280.png`: Landing section «Alle spillene på én skjerm» with «Demodata», legend, 8 demo games, Venter 2 / Pågår 6, game numbers only. Matches.
- `landing-matrisevegg-390.png`: same at 390 px; cells shrink to fit, red cells print «−», Uke header thinned to 1, 5, 10, 15. Matches.
- `landing-fokus-celle-390.png`, `landing-fokus-celle-1280.png`: a cell focused with the inset ring. Matches.
- `landing-matrisevegg-200pst.png`: Landing at 200 % text; wall fits and is readable. Matches. Note (not 7.2): the Landing headline wraps one word per line at this size.

No deviations found; no frontend changes made. Exactly one primary button on the Landing («Be om lærertilgang»); none on the Oversikt.
