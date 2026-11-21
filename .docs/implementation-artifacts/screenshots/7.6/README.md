# Story 7.6: visual check of the Oversikt right rail

Compared with `08-laerer-oversikt.png` (right rail), DESIGN.md and EXPERIENCE.md. Screenshots are full page, nb-NO, taken after the visual fix (rail and game rows now use container queries in rem). «200pct» is `html { font-size: 200% }` at 1280 px. «rik» is a stubbed overview answer (15 finished, 3 waiting) for a populated rail; the others come from a real local game.

- `oversikt-venter-{390,1024,1280,1280-200pct}.png`: one game waiting; «Venter ellers» lists the Student by Role and time, AI line, «Klassens kostnad» says none finished, Trakt. At 390 the wall note reads «Venter, under 1 min» inside the wall and the rail stands under it. Matches (the mockup's «Send Melding» links are outside this story).
- `oversikt-ferdig-{390,1024,1280,1280-200pct}.png`: one finished game; cost chart with median label, summary line, «Vis som tabell», bars per Role split lager/restordre, key, Trakt. Matches the mockup's rail (a single game gives a flat box, as expected; the mockup's «Kjedekost per uke» graph is a later story).
- `oversikt-tabell-{390,1024,1280,1280-200pct}.png`: «Vis som tabell» open in «Klassens kostnad»: two-column Spill/Kjedekost table, link now «Vis som graf». Matches.
- `oversikt-for-start-{390,1024,1280,1280-200pct}.png`: before the Start date: allocation only, no cost block, «Venter ellers» and Trakt. Matches.
- `oversikt-rik-{390,1024,1280,1280-200pct}.png`: populated rail (stub): three waiting names, a dense cost chart with median and midterste halvdel, role bars with restordre in red, funnel bars scaled to Registrert. Matches the mockup; one long name wraps its «min» to a second line at 1280.

Fixed: at 200 % text the rail sat beside the wall (media query ignores the enlarged root size) and squeezed the game rows to one letter per line; at 1024 px the game rows were cramped. Now the rail is beside the wall when its container is at least 48 rem wide, and the game rows use the four-column grid only from 42 rem; otherwise stacked. No page scroll sideways in any shot.
