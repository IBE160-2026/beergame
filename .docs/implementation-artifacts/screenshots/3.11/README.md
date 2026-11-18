# Story 3.11 — visual check

Taken after the fix in «Story 3.11: visuelle rettinger». Every state except `-ekte`, `admin-omraade-lenke` and `ingen-tilgang` uses a faked list of four Norwegian institutions (Playwright routing that also answers create, rename and 409). Compared with DESIGN.md, EXPERIENCE.md, nb.ts and mockup 09-alle-sider. No sideways scroll at any width; the only primary button is «Opprett Institusjon».

- `admin-omraade-lenke-390.png` — Admin-område with the two Lenker «Brukere og roller» and «Institusjoner». Matches.
- `admin-omraade-lenke-1280.png` — the same at 1280. Matches.
- `institusjoner-tom-390.png` — empty list (faked): the form, then «Ingen Institusjoner ennå. Opprett den første over.». Matches.
- `institusjoner-tom-1280.png` — the same at 1280. Matches.
- `institusjoner-feil-tomt-390.png` — empty name: invalid Tekstfelt, «Skriv navnet på Institusjonen.» under it. Matches.
- `institusjoner-feil-tomt-1280.png` — the same at 1280. Matches.
- `institusjoner-feil-krollalfa-390.png` — «post@usn.no»: «Navnet kan ikke inneholde @ eller kontrolltegn.» updated as typed. Matches.
- `institusjoner-feil-krollalfa-1280.png` — the same at 1280. Matches.
- `institusjoner-duplikat-390.png` — «høgskolen i molde» refused (409): «Det finnes allerede en Institusjon med dette navnet.», list unchanged. Matches.
- `institusjoner-duplikat-1280.png` — the same at 1280. Matches.
- `institusjoner-opprettet-390.png` — after a create: field empty, result line «Universitetet i Agder er opprettet.», new row on top. Matches.
- `institusjoner-opprettet-1280.png` — the same at 1280. Matches.
- `institusjoner-liste-390.png` — four rows as labelled blocks with full-width «Gi … nytt navn». Matches.
- `institusjoner-liste-1280.png` — table Navn / Opprettet / Endre. Matches (after the fix: fixed-width Opprettet column).
- `institusjoner-endre-390.png` — inline rename: «Nytt navn på Høgskolen i Molde» prefilled and selected, «Lagre navnet», «Avbryt». Matches.
- `institusjoner-endre-1280.png` — the same in the table row. Matches.
- `institusjoner-endre-feil-390.png` — rename to «nord universitet» refused: reason under the rename field, form stays open. Matches.
- `institusjoner-endre-feil-1280.png` — the same at 1280. Matches.
- `institusjoner-endret-390.png` — after a rename to a long name: row line «Høgskolen i Molde heter nå …», name and button wrap. Matches.
- `institusjoner-endret-1280.png` — the same at 1280; the date column no longer shifts with name length. Matches (after the fix).
- `institusjoner-ekte-390.png` — the real page on the dev database: 50 e2e test rows and «Vis flere Institusjoner». Matches; the test data makes it long.
- `institusjoner-ekte-1280.png` — the same at 1280. Matches.
- `institusjoner-ingen-tilgang-390.png` — Lecturer: «Du har ikke tilgang til denne siden.» and «Til Lærerhjem», no form. Matches.
- `institusjoner-ingen-tilgang-1280.png` — the same at 1280. Matches.

Judgement left: the «Gi … nytt navn» buttons have ragged widths that follow the name length (as on the User list); the create result line stays while a row is being renamed.
