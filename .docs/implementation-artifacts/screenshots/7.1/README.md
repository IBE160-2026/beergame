# Story 7.1 Oversikt: visual check

Taken as the Lecturer on the local stack (Chromium, `--lang=nb-NO`), fresh data, full page. Mockup `08-laerer-oversikt` shows the finished Oversikt of later stories (heatmap rows, filters, side panels); Story 7.1 covers only its headline, groups and rows, which match its typography, tokens and tone. `DESIGN.md` and `EXPERIENCE.md` agree with what is built.

- `oversikt-for-start-tom-390.png`, `-1280.png`: before the Start date, nothing allocated: Start date line, «Fordeling 0», «Ingen spill er fordelt ennå.». Matches. Judgement: «Fordeling 0» above the empty line is redundant.
- `oversikt-for-start-fordelt-1280.png`, `-390.png`: before the Start date, three games allocated: allocation rows only (Spill n and Seats, free Seats «Ledig»), no counts, no cost. Matches.
- `oversikt-blandet-1280.png`, `-390.png`: after the lock, one game each of Venter (three waited-for Students by name and Role, «under 1 min»), Pågår and Ferdig (lowest cost first, no Uke, FR-14). Headline «1 ferdig · 1 pågår · 1 venter», «Oppdatert hh:mm:ss». Matches; rows are a ruled list at 1280 and stacked with «Kjedekost» label at 390, no sideways scroll.
- `oversikt-ikke-startet-1280.png`, `-390.png`: locked, no game started: headline «· 2 ikke startet», group «Ikke startet 2», Seats only. Matches. At 1280 the Seat text starts at the Uke column's offset, leaving an empty gap; harmless.
- `oversikt-student-avvist-1280.png`, `-390.png`: a Student gets «Du har ikke tilgang til denne siden.» with «Til Hjem», as for a page that does not exist. Matches EXPERIENCE.md.

Exactly one primary button: none on the page (only the shell's secondary «Logg ut»). Nothing cut off at 390 px; scrollWidth equals clientWidth in every shot.
