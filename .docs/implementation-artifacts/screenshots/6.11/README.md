# Story 6.11: visual check of the editable Ordrefelt and its preview on the play screen (`/spill/{id}`)

Demo Student, faked `/api/me/games/{id}`, `/play` and `/weeks/*/view` answers (as `e2e/order-field.spec.ts`); Grossist of a Classic game. Uke 11 is `play-week-11.json` (På vei 16, arrival Uke 15, max 999); the long-delay shots are the same envelope with 3/3/3 rules and `preview.order_arrival_week` 17 (scratch stand-in); the Guided Week is `play-week-3.json`. Chromium, `nb-NO`, `Europe/Oslo`, full page. Every shot: no page-level sideways scroll, no text under 13 px, every field control at least 44 px, at most one primary button. No visual fix was needed.

- `spill-tom-320.png`: empty; «Antall enheter», help line, «Sist Uke bestilte du 8.», − and «Bekreft ordre» disabled, Din ordre at nå a dashed cell, band «På vei 16».
- `spill-tom-390.png`: same at 390.
- `spill-tom-768.png`: same, phone layout, field at max 28 rem.
- `spill-tom-1280.png`: same, laptop; field tops the right column.
- `spill-skrevet24-320.png`: 24 typed; Din ordre at nå ink block 24, Levering Uke 15 boxed 24 joined by a thin line, band «Din ordre 24», «På vei 16 + 24» with the ink-bordered box, «Kommer fram om lag Uke 15. …», primary «Bekreft ordre på 24».
- `spill-skrevet24-390.png`: same at 390; compare with `05-spill.png` left.
- `spill-skrevet24-768.png`: same at 768.
- `spill-skrevet24-1280.png`: same, laptop; compare with `05-spill.png` right.
- `spill-null-320.png`: 0 typed; valid, «Bekreft ordre på 0», band «På vei 16 + 0» with no box, − disabled.
- `spill-null-390.png`: same at 390.
- `spill-null-768.png`: same at 768.
- `spill-null-1280.png`: same, laptop.
- `spill-forstor-320.png`: 1000 typed and left; restordre border, «1 000 er mer enn 999. Skriv et helt tall fra 0 til 999.» under the help line, + disabled, no preview.
- `spill-forstor-390.png`: same at 390.
- `spill-forstor-768.png`: same at 768.
- `spill-forstor-1280.png`: same, laptop.
- `spill-ikketall-320.png`: «2a» typed and left; restordre border, «Skriv et helt tall fra 0 til 999.», both segments disabled, no preview.
- `spill-ikketall-390.png`: same at 390.
- `spill-ikketall-768.png`: same at 768.
- `spill-ikketall-1280.png`: same, laptop.
- `spill-langforsinkelse-320.png`: 3/3/3 game, arrival Uke 17 beyond nå + 4; nå shows 24, no Levering cell and no line, the arrival line names Uke 17, band «På vei 16 + 24».
- `spill-langforsinkelse-390.png`: same at 390.
- `spill-langforsinkelse-768.png`: same at 768.
- `spill-langforsinkelse-1280.png`: same, laptop.
- `spill-veiledet-uke3-320.png`: Guided Uke 3; read-only 4 on `future-tint`, no segments, no button (cursor `default`, caret transparent; not visible in a still).
- `spill-veiledet-uke3-390.png`: same at 390.
- `spill-veiledet-uke3-768.png`: same at 768.
- `spill-veiledet-uke3-1280.png`: same, laptop.
- `spill-skrevet24-tekst200-390.png`: 24 typed at 200 % text; field, arrival line and button wrap and fit; table scrolls inside its own box.
- `spill-forstor-tekst200-390.png`: 1000 at 200 % text; the reason wraps under the help line, nothing cut off.
