# Story 6.7: visual check of Graf over tabell on the play screen (`/spill/{id}`)

Taken after the visual fix (net-graph gridlines and zero line stop at nå). Demo Student, stand-in game and play envelope: Uke 11 from `frontend/src/modules/games/fixtures/play-week-11.json`; Uke 2 cut down from `play-week-3.json`; Uke 32 extended from `play-week-30.json` with made-up deep backlog in Uke 31–32 (−64, −98), so the cost axis grows to 120 kr in nå. Chromium, `nb-NO`, `Europe/Oslo`, full page. Every shot: marks ≤ 1 px from their column, now-line on the nå column's right edge, no label overlap, no text < 13 px, no clipped cell, no page-level sideways scroll; non-nå Week numbers `ink-muted` (#5E6F82), nå bold `ink`.

- `spill-uke2-360.png`: Uke 2 at 360 px; one point per line plus nå, «Lager 12», «Posisjon 24», 40 kr axis; captions wider than the past cover the now-line and tint.
- `spill-uke2-390.png`: Uke 2 at 390 px; same.
- `spill-uke2-768.png`: Uke 2 at 768 px (phone layout).
- `spill-uke2-1280.png`: Uke 2 at 1280 px (laptop layout).
- `spill-uke11-grossist-360.png`: Uke 11 at 360 px; lines Uke 4–11, Netto lager below zero in red, «Restordre 20», «Posisjon −4», ticks −20…40, cost bars blue then red.
- `spill-uke11-grossist-390.png`: Uke 11 at 390 px; same, compare with mockup 05 (phone).
- `spill-uke11-grossist-768.png`: Uke 11 at 768 px.
- `spill-uke11-grossist-1280.png`: Uke 11 at 1280 px; lines Uke 1–11, compare with mockup 05 (laptop).
- `spill-uke32-360.png`: Uke 32 at 360 px; y-axis −80…40 in 40-steps, «Aksen går nå til 120 kr.», tick «120 kr», no bar cut.
- `spill-uke32-390.png`: Uke 32 at 390 px; same.
- `spill-uke32-768.png`: Uke 32 at 768 px.
- `spill-uke32-1280.png`: Uke 32 at 1280 px; region scrolled to nå, ticks −60/0/60.
- `spill-uke11-detaljist-390.png`: Uke 11 as Detaljist at 390 px.
- `spill-uke11-distributor-390.png`: Uke 11 as Distributør at 390 px.
- `spill-uke11-fabrikk-390.png`: Uke 11 as Fabrikk at 390 px.
- `spill-uke11-tekst200-360.png`: Uke 11 at 360 px with 200 % text; nå and nå + 4 in view, captions wrap and break the now-line.
- `spill-uke11-tekst200-390.png`: Uke 11 at 390 px with 200 % text; same.
- `spill-uke32-tekst200-360.png`: Uke 32 at 360 px with 200 % text.
- `spill-uke32-tekst200-390.png`: Uke 32 at 390 px with 200 % text.
- `print-graf-over-tabell-1280.png`: internal print page (HTML fetched from the frontend container, `/print/*` is 404 at the proxy) in Chromium at 1280 px; the laptop rows show but the now-line and caption tint follow the phone variant (A4-only page; the WeasyPrint check passes).
