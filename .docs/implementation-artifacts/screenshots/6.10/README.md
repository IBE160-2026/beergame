# Story 6.10: visual check of the Veiledet uke on the play screen (`/spill/{id}`)

Taken after the visual fix «Story 6.10: visuelle rettinger» (the Din ordre cell at nå with a placed Order is an `ink` block with a `paper` number, DESIGN.md → Graf over tabell, as in `05-spill.png` and `01-landing.png`). Demo Student, faked `/api/me/games/{id}`, `/play` and `/weeks/*/view` answers; Grossist of a Classic game, `guided_weeks: 4`. Uke 1 is `play-week-1.json`; Uke 4 and Uke 5 are `play-week-3.json` moved on in steady state (scratch stand-ins, Uke 5 with `turn.guided: false`). Chromium, `nb-NO`, `Europe/Oslo`, full page. Every shot: no page-level sideways scroll, no text under 13 px, no button in `main`.

- `spill-veiledet-uke1-320.png`: Uke 1; «Din ordre for Uke 1», 4 read-only on `future-tint` in `ink-muted`, help line, Din ordre cell 4 as ink block.
- `spill-veiledet-uke1-390.png`: same at 390; field fills the width under the table.
- `spill-veiledet-uke1-768.png`: same, phone layout, field at max 28 rem.
- `spill-veiledet-uke1-1280.png`: same, laptop; the field tops the right column.
- `spill-veiledet-uke4-320.png`: Uke 4, the last Veiledet uke; history 4/4/4, nå 4 as ink block.
- `spill-veiledet-uke4-390.png`: same at 390; compare with `05-spill.png` left.
- `spill-veiledet-uke4-768.png`: same, phone layout.
- `spill-veiledet-uke4-1280.png`: same, laptop.
- `spill-ordinaer-uke5-320.png`: Uke 5, first ordinary Uke: no Ordrefelt yet (Story 6.11), Din ordre at nå the empty dashed cell.
- `spill-ordinaer-uke5-390.png`: same at 390.
- `spill-ordinaer-uke5-768.png`: same, phone layout.
- `spill-ordinaer-uke5-1280.png`: same, laptop.
- `spill-tekst200-veiledet-uke1-390.png`: 200 % text, Uke 1; the value at 64 px, the help line wraps to two lines, nothing cut.
- `spill-tekst200-veiledet-uke4-390.png`: 200 % text, Uke 4; the table scrolls in its own region, the field and help line wrap inside the page.
