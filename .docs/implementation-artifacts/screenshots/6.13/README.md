# Story 6.13: visual check of the Ordrefelt's failure, checking and offline lines (`/spill/{id}`)

No visual fix was needed. Demo Student, faked `/api/me/games/{id}`, `/play` and order answers (`frontend/e2e/support/play.ts`), Playwright route, clock and offline controls. Chromium, `nb-NO`, `Europe/Oslo`, full page. Every shot: no page-level sideways scroll, no text under 13 px in the order area, the message above the button and not cut off, exactly one primary button, copy as in `nb.ts`. Mockup 06 does not draw these states; checked against EXPERIENCE.md → State Patterns → Spill and DESIGN.md → Ordrefelt.

- `spill-feilet-320.png`: Submit failed; «Ordren ble ikke sendt. Ingenting er bestilt ennå.» bold `ink` above «Prøv å sende 24 igjen»; 24 kept, editable.
- `spill-feilet-390.png`: same at 390.
- `spill-feilet-768.png`: same, phone layout.
- `spill-feilet-1280.png`: same, laptop right column (message 15 px).
- `spill-feilet-tekst200-390.png`: Submit failed with root text at 200 %; message and button wrap, nothing clipped.
- `spill-uke-over-320.png`: `week_not_open`; the screen moves to Uke 14 with «Uke 11 er over. Ordren på 24 ble ikke sendt.» above an empty field's «Bekreft ordre».
- `spill-uke-over-390.png`: same at 390.
- `spill-uke-over-768.png`: same, phone layout.
- `spill-uke-over-1280.png`: same, laptop.
- `spill-sete-tapt-320.png`: `seat_not_yours`; «Du har ikke dette setet lenger. Ordren på 24 ble ikke sendt.», 24 kept, «Bekreft ordre på 24».
- `spill-sete-tapt-390.png`: same at 390.
- `spill-sete-tapt-768.png`: same, phone layout.
- `spill-sete-tapt-1280.png`: same, laptop.
- `spill-sjekker-320.png`: Timed out; «Vi vet ikke om ordren kom fram. Sjekker …» regular `ink`, field read-only on `future-tint`, busy «Sender ordre på 24 …».
- `spill-sjekker-390.png`: same at 390.
- `spill-sjekker-768.png`: same, phone layout.
- `spill-sjekker-1280.png`: same, laptop.
- `spill-sjekker-tekst200-390.png`: Timed out at 200 % text; wraps, nothing clipped.
- `spill-frakoblet-320.png`: offline with 24 typed; Tilkoblingslinje at the top and «Ordren på 24 er ikke sendt.» above «Bekreft ordre på 24».
- `spill-frakoblet-390.png`: same at 390.
- `spill-frakoblet-768.png`: same, phone layout.
- `spill-frakoblet-1280.png`: same, laptop.
- `spill-tilkoblet-igjen-320.png`: back online; «Tilkoblet igjen. Ordren er ikke sendt ennå.», normal button, nothing sent.
- `spill-tilkoblet-igjen-390.png`: same at 390.
- `spill-tilkoblet-igjen-768.png`: same, phone layout.
- `spill-tilkoblet-igjen-1280.png`: same, laptop.
