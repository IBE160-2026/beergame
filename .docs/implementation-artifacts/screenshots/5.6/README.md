# Story 5.6 – visual check (Add Lab hours)

Taken as the demo Faglærer on fresh Classes made through the api, 390 and 1280 px, full page, `nb-NO`, after commit "Story 5.6: visuelle rettinger" (Lab hour label at the line's edge now lines up with its square's edge). Compared with mockup `03-laerer-spill.png`, DESIGN.md and EXPERIENCE.md. Native date/time fields show `MM/DD/YYYY` and `AM/PM` because headless Chromium uses its own language, not the context locale; this is not an app deviation (same in 5.2).

- `klasseokt-ingen-labtimer-390.png`: dates set, no Lab hours, «Legg til Labtime» and «Ingen Labtimer ennå.». Matches.
- `klasseokt-ingen-labtimer-1280.png`: as above, two columns as in mockup 03. Matches.
- `klasseokt-ny-labtime-skjema-390.png`: in-place form «Ny Labtime», fields in one column, consequence line, one primary «Lagre Labtime», «Lagre Klasseøkt» secondary. Matches.
- `klasseokt-ny-labtime-skjema-1280.png`: as above, Dato/Start/Slutt on one row. Matches.
- `klasseokt-feil-halvskrevet-dato-390.png`: half-typed date gets «Datoen er ikke fylt ut helt.» under «Dato». Matches.
- `klasseokt-feil-halvskrevet-dato-1280.png`: as above. Matches.
- `klasseokt-feil-for-lang-390.png`: 13 h gets «En Labtime kan vare høyst 12 timer.» under «Slutt», plus the form's refusal line. Matches.
- `klasseokt-feil-for-lang-1280.png`: as above; the two-line error under «Slutt» pushes «Sted» down. Matches.
- `klasseokt-feil-slutt-passert-390.png`: end in the past gets «Labtimen er allerede over. Velg et senere tidspunkt.». Matches.
- `klasseokt-feil-slutt-passert-1280.png`: as above. Matches.
- `klasseokt-feil-slutt-for-start-uten-sted-390.png`: «Slutt må være etter start.» and «Skriv hvor Labtimen er.» each under its field. Matches.
- `klasseokt-feil-slutt-for-start-uten-sted-1280.png`: as above. Matches.
- `klasseokt-labtime-lagt-til-390.png`: one saved Lab hour: square, legend, list line, «Labtimen er lagt til.». Matches.
- `klasseokt-labtime-lagt-til-1280.png`: as above. Matches.
- `klasseokt-flere-labtimer-390.png`: five Lab hours, two places in the legend («Datalab A2 og Rom 101»); Datolinje scrolls in its own region (520 px minimum, by design), no page scroll. Matches.
- `klasseokt-flere-labtimer-1280.png`: squares under the axis, day/time labels centred on their squares, lifted a tier where they would overlap; date labels centred on ticks, start/end-aligned at the edges. Matches mockup 03 (more tiers than the mockup because the Lab hours are denser).
- `klasseokt-endre-labtime-skjema-390.png`: change form under its list line, «Lagre endringen» primary, «Fjern Labtimen» secondary, «Avbryt». Matches.
- `klasseokt-endre-labtime-skjema-1280.png`: as above. Matches.
- `klasseokt-labtime-ferdig-390.png`: ended Lab hour «(ferdig)» in secondary ink, no «Endre». Matches.
- `klasseokt-labtime-ferdig-1280.png`: as above; edge label now lines up with its square. Matches.

No digest mail screenshot: the check ran at 02:00, inside the digest's quiet hours (22–07), so no Lab hour mail was sent.
