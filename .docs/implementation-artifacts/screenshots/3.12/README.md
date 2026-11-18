# Story 3.12 — visual check

Taken after the fix in «Story 3.12: visuelle rettinger». Browser locale `nb-NO` (Chromium started with `--lang=nb-NO`, so the date fields read `dd.mm.yyyy`), time zone Europe/Oslo. Every state except `admin-omraade-lenke`, `-ekte` and `-ingen-tilgang` uses a faked log of 12 rows covering all eleven actions (Playwright routing that applies the real actor, action and date filters and pages by cursor). Compared with DESIGN.md, EXPERIENCE.md, nb.ts and mockup 09-alle-sider. No sideways scroll at any width; no primary button on the page («Vis flere hendelser» and «Prøv igjen» are secondary, as on the other Admin lists).

- `admin-omraade-lenke-390.png` — Admin-område with three Lenker; «Revisjonslogg» third. Matches.
- `admin-omraade-lenke-1280.png` — the same at 1280. Matches.
- `revisjonslogg-liste-390.png` — filters stacked, then every row as a labelled block (Tidspunkt / Utført av / Handling / Gjelder / Endring). Matches.
- `revisjonslogg-liste-1280.png` — four filters in one row, table Tidspunkt / Utført av / Handling / Gjelder / Endring; «Systemet» in secondary ink, «–» for an empty change. Matches (after the fix: names and actions on one line, fixed short columns).
- `revisjonslogg-filter-utfort-av-390.png` — «Utført av: Systemet»: the two bootstrap rows. Matches.
- `revisjonslogg-filter-utfort-av-1280.png` — the same at 1280; columns keep their widths. Matches (after the fix).
- `revisjonslogg-filter-handling-390.png` — «Handling: Invitasjon akseptert»: two rows (new and existing account). Matches.
- `revisjonslogg-filter-handling-1280.png` — the same at 1280. Matches.
- `revisjonslogg-filter-dato-390.png` — 16.11.2026–17.11.2026: four rows in Norwegian date format. Matches.
- `revisjonslogg-filter-dato-1280.png` — the same at 1280. Matches.
- `revisjonslogg-dato-omvendt-390.png` — 18.11 to 14.11: «Til og med» invalid with «Til og med-datoen kan ikke være før fra og med-datoen.», the list keeps the last valid rows. Matches.
- `revisjonslogg-dato-omvendt-1280.png` — the same at 1280. Matches.
- `revisjonslogg-ingen-treff-390.png` — Ola Hansen + Institusjon opprettet: «Ingen treff.». Matches.
- `revisjonslogg-ingen-treff-1280.png` — the same at 1280. Matches.
- `revisjonslogg-tom-390.png` — empty log: «Ingen hendelser ennå.». Matches.
- `revisjonslogg-tom-1280.png` — the same at 1280. Matches.
- `revisjonslogg-vis-flere-390.png` — first page of five rows and secondary «Vis flere hendelser». Matches.
- `revisjonslogg-vis-flere-1280.png` — the same at 1280. Matches.
- `revisjonslogg-vis-flere-feil-390.png` — next page fails: rows stay, «Flere hendelser kunne ikke lastes. Prøv igjen.» above the button. Matches.
- `revisjonslogg-vis-flere-feil-1280.png` — the same at 1280. Matches.
- `revisjonslogg-feil-390.png` — load error: filters, «Siden kunne ikke lastes.» and «Prøv igjen». Matches.
- `revisjonslogg-feil-1280.png` — the same at 1280. Matches.
- `revisjonslogg-ekte-390.png` — the real page on the dev database: 50 e2e test rows and «Vis flere hendelser». Matches; the test data makes it long.
- `revisjonslogg-ekte-1280.png` — the same at 1280; long test names wrap inside «Utført av». Matches.
- `revisjonslogg-ingen-tilgang-390.png` — Lecturer: «Du har ikke tilgang til denne siden.» and «Til Lærerhjem», no filters or rows. Matches.
- `revisjonslogg-ingen-tilgang-1280.png` — the same at 1280. Matches.

Judgement left: with the default Chromium language (not `--lang=nb-NO`) the date fields show `mm/dd/yyyy` even with locale `nb-NO`; the format follows the browser's language, not the page. Two targets in «Gjelder» (Invitation · User) wrap to two lines at 1280.
