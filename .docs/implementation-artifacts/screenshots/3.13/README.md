# Story 3.13: visual check

Taken after the fixes in «Story 3.13: visuelle rettinger», against `mockups/01-landing.png`, `DESIGN.md` and `EXPERIENCE.md`. None of the pages scrolls sideways at 390 px. The access-request list and the 429/202 answers are faked; the Users and Invitations lists are cut to four rows.

- `landing-anonym-390.png`: Landing, anonymous, phone. Headline, lead (`body-lead`), buttons, Seat table in one column. Matches.
- `landing-anonym-1280.png`: Landing, anonymous, laptop, full page. Hairline under the header, headline breaks between the sentences, Netto lager in `net-pos-2`. Matches the scope of the story. The mockup's graph, cost panel and «Alle spillene» are left to later stories.
- `landing-forste-skjerm-1280x800.png`: Landing, first viewport. The name, headline, lead, both buttons and the whole Seat table are above the fold. Matches.
- `laerertilgang-tom-390.png` / `-1280.png`: empty request form. Same shell as «Logg inn», one primary button. Matches.
- `laerertilgang-valideringsfeil-390.png` / `-1280.png`: all three reasons in `restordre` under the fields, focus on Navn. Matches.
- `laerertilgang-for-mange-390.png` / `-1280.png`: faked 429. «For mange forespørsler. Prøv igjen om en time.» above the button, and what was typed is kept. Matches.
- `laerertilgang-sendt-390.png` / `-1280.png`: the confirmation line between rules, and «Til forsiden». Matches.
- `brukere-foresporsler-390.png` / `-1280.png`: «Forespørsler om lærertilgang» between «Inviter» and «Brukere». Three rows on laptop, labelled blocks on phone. Matches the other Admin lists.
- `brukere-inviter-utfylt-390.png` / `-1280.png`: after «Inviter Per Hansen som Faglærer». The address and Faglærer are filled in, «Fyller inn fra forespørselen til Per Hansen.» shows, and the field has focus. Matches.
- `brukere-avvist-390.png` / `-1280.png`: after «Avvis». The row is gone, and the status line «Forespørselen fra Ingrid Bakke-Solheim er avvist.» shows. Matches.
