# Story 4.6 — visual check (2026-11-19)

Class page, «Invitasjoner» section, at 390 and 1280 px, full page. Compared with `mockups/02-laerer-klasse.png` (its «Status etter utsending» bar is Story 4.7's registration status, so only the section's place under the Roster and the hairline/caption grammar apply), DESIGN.md and EXPERIENCE.md. No horizontal scroll at 390 px in any shot; no primary button in the section.

- `klasse-invitasjoner-ingen-avvisninger-390.png` / `-1280.png` — fresh Class, 3 sent, no bounces: four counts, no list. Matches (caption over `figure-total`, hairline row, 2×2 on the phone).
- `klasse-invitasjoner-live-for-390.png` / `-1280.png` — open page before the bounces: «Sendt 3», «Kom ikke fram 0». Matches.
- `klasse-invitasjoner-live-etter-390.png` / `-1280.png` — same page, not reloaded, after one hard and one soft bounce and the 15 s refresh: «Kom ikke fram 2» and both rows. Matches.
- `klasse-invitasjoner-avvist-390.png` / `-1280.png` — reload with one hard, one soft bounce: counts 3/2/0/0, list with «Kom ikke fram, permanent feil» / «… midlertidig feil»; long addresses wrap on the phone. Matches.
- `klasse-invitasjoner-akseptert-utlopt-390.png` / `-1280.png` — faked api answer 246/2/238/6: three-digit figures line up in tabular figures. Matches.
- `klasse-invitasjoner-feil-390.png` / `-1280.png` — summary request answers 500: «Tallene for Invitasjonene kunne ikke hentes.» in `restordre` under the heading. Matches.
- `klasse-ikke-eier-390.png` / `-1280.png` — the demo Lecturer opens another Lecturer's Class: permission-denied page, no counts. Matches.
- `klasse-demo-uten-invitasjoner-390.png` / `-1280.png` — the demo Class «class-of-1994» as its owner sees it (Invitations sent by earlier test runs in this database). Matches.

Judgement left: «Kom ikke fram» is read as count label, list heading and row status (rejected in review as intended); the section sits under the upload box rather than beside it as in the mockup's right column (the Class page is one column).
