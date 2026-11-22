# Story 8.5 visual check (commit 5fe60c5), Lecturer, nb-NO. Widths 390, 1280, 200 % text (200pct). No horizontal overflow in any shot (scrollWidth == clientWidth, logged).

- spillinnsikt-before-{390,1280,200pct}.png: Spillstyring under the Seats, one row per Student Seat, consequence caption above a secondary button; full width at 390. Matches (title is headline, spec says label).
- oversikt-band-before-{390,1280,200pct}.png: Varselbånd with consequence caption under band text, «Send Melding» primary, «Sett inn KI-spiller for …» secondary; stacked full width at 390, side by side at 1280. Matches.
- spillinnsikt-failed-press-390.png: mocked 409 order_exists; inline red refusal under the button, button stays. Matches.
- spillinnsikt-pressed-{390,1280,200pct}.png: result line «KI-spiller satt inn for X.» replaces the button; Seat above shows «KI satt inn av {name}». Matches.
- spillinnsikt-marked-{390,1280,200pct}.png: reload after presses; Seats marked, pressed rows no longer offered. Matches.
- oversikt-marked-{390,1280,200pct}.png: «Fabrikk: KI-spiller (KI satt inn av {name})» in Spill og seter. Matches.
- oversikt-band-pressed-{390,1280,200pct}.png: result line below the band, on paper; at 390 the band moves to the next waiting Seat and the line still names the earlier Student. At 1280/200 % the game left the band. Matches behaviour; placement is judgement.
- spillinnsikt-lostrace-{390,1280,200pct}.png: stale page, 409 takeover_exists; line «{name} har allerede satt inn en KI-spiller.» in place of button. Matches.
- spillinnsikt-lastweek-{390,1280}.png: game in last Uke (weeks 2), Spiller0 has ordered it: no row, no button for that Seat; the other Seat still offered. Matches.
