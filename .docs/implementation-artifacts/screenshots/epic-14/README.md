# Epic 14: Klasserapport og statistikk (close-out visual check)

Taken once for the epic on the local stack (2026-11-23), at 390 px and 1280 px, full page, from the
epic's own e2e specs (their mocked api answers, except `klasserapport-live` and `eksport`, which
read real data: one Class game played out, a locked Class session). Checked by an independent
review sub-agent against DESIGN.md, EXPERIENCE.md and the mockups.

Screenshot | what it shows | matches the design?

- `klasserapport-spill-{390,1280}.png` | Klasserapport, the games part (14.1): Trakt, Kjedekost, cost per Role, Forsterkning, Mønstre, KI-spillere, Troverdighet, 60 games | matches; fixed in the close-out: at 200 % text on a wide screen the label and value columns took the whole row and the bars vanished (label column now at most 40 %, bar at least 4 rem)
- `klasserapport-laering-{390,1280}.png` | the learning part (14.2): Starting task beside the test items, each question, the AI scores | matches
- `klasserapport-live-{390,1280}.png` | the live report after one real Class game was played out | matches
- `alle-spill-{390,1280}.png` | «Alle spill side om side» (14.5), the Student's own game drawn thick | matches; at 390 the charts scroll in their own region, as designed
- `plenum-{390,1280}.png` | the plenary wall (14.6) | matches
- `tverrklasse-{390,1280}.png` | Tverrklasse-statistikk (14.3) | matches
- `tverrklasse-ulikt-oppsett-{390,1280}.png` | the filters and a Class session labelled «Ulikt oppsett: …», scores not comparable (14.4) | matches
- `tverrinstitusjonell-{390,1280}.png` | Tverrinstitusjonell statistikk, flag on (14.7) | matches (same bar fix as the Klasserapport)
- `eksport-{390,1280}.png` | Klasseøkt «Eksport» with ZIP, fullføringsliste and the game-data CSV (14.8) | fixed in the close-out: «Last ned spilldata (CSV)» was a plain link beside two buttons; now styled as the same secondary action

Low notes left as they are: the Kjedekost axis ticks sit close at 390 px in the live report; the
plenary's Rolle tabs and legend use caption size; earlier and current Klasseøkt share one bar tone
in Tverrklasse-statistikk.
