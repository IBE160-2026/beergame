# Story 6.12: visual check of confirming the Order and the kept draft on the play screen (`/spill/{id}`)

Demo Student, faked `/api/me/games/{id}`, `/play`, `/weeks/*/view` and `/weeks/11/order` answers (as `e2e/order-confirm.spec.ts`); Grossist of a Classic game in Uke 11 (`play-week-11.json`), the next Uke is `play-week-14.json`. The sending shots hold the POST open. Chromium, `nb-NO`, `Europe/Oslo`, full page. Every shot: no page-level sideways scroll, no text under 13 px, at most one primary button. Fix: the read-only value box while sending now has the `future-tint` fill and the value in `ink-muted` (DESIGN.md → Ordrefelt); it was `paper` / `ink`.

- `spill-skrevet24-320.png`: 24 typed before sending; ink border, Din ordre at nå 24, Levering Uke 15 boxed, «På vei 16 + 24», primary «Bekreft ordre på 24».
- `spill-skrevet24-390.png`: same at 390.
- `spill-skrevet24-768.png`: same at 768.
- `spill-skrevet24-1280.png`: same, laptop.
- `spill-sender-320.png`: Submitting; button «Sender ordre på 24 …» in the Disabled look (future-tint, axis border, ink-muted), focused, busy; field read-only on future-tint, − and + disabled.
- `spill-sender-390.png`: same at 390.
- `spill-sender-768.png`: same at 768.
- `spill-sender-1280.png`: same, laptop.
- `spill-sendt-320.png`: Confirmed; «Ordren på 24 er sendt.» bold and focused, «Skjermen går videre …» in caption; no field, no button; table and Kjedebånd keep 24 (mockup `06` C).
- `spill-sendt-390.png`: same at 390.
- `spill-sendt-768.png`: same at 768.
- `spill-sendt-1280.png`: same, laptop; message tops the right column.
- `spill-nesteuke-320.png`: the send completed the Uke; Uke 14 heading focused, empty field, «Bekreft ordre» disabled, no typed box.
- `spill-nesteuke-390.png`: same at 390.
- `spill-nesteuke-768.png`: same at 768.
- `spill-nesteuke-1280.png`: same, laptop.
- `spill-gjenopprettet-320.png`: 24 typed, then reload; the draft is back with its preview and «Bekreft ordre på 24», nothing sent.
- `spill-gjenopprettet-390.png`: same at 390.
- `spill-gjenopprettet-768.png`: same at 768.
- `spill-gjenopprettet-1280.png`: same, laptop.
- `spill-sender-tekst200-390.png`: Submitting at 200 % text; fits, but «…» wraps alone onto a second line of the button.
- `spill-sendt-tekst200-390.png`: Confirmed at 200 % text; both lines wrap and fit.
