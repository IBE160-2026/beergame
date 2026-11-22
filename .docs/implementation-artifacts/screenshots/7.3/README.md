# Story 7.3 «Vis som tabell»: visuell kontroll

Oversikt (`/klasseokter/{id}/oversikt`) som Faglærer, to spill (Spill 2 venter, Spill 1 pågår). Bredder 1280, 390 og 1280 med 200 % tekst (`200pct`). Ingen sidevis horisontal rulling i noen tilstand (målt, 0 px).

- `oversikt-vegg-default-{1280,390,200pct}.png`: Visning-bryter med «Vegg» valgt, forklaring og vegg; samsvarer med 7.2-veggen og mockup 08 (bryteren er større og står over veggen, ikke til høyre for grafen: kjent avvik, se under).
- `oversikt-tabell-standard-{1280,390,200pct}.png`: tabellen etter Status stigende (veggens rekkefølge, Status understreket med ↑); samsvarer. På 390 ligger Uke-kolonnene bak rulling inne i tabellområdet, siden ruller ikke.
- `oversikt-tabell-kjedekost-{1280,390,200pct}.png`: sortert etter «Kjedekost, kr» stigende, ↑ i hodet; samsvarer.
- `oversikt-tabell-venter-{1280,390,200pct}.png`: sortert etter «Venter på», lengst ventetid først, ↓; samsvarer.
- `oversikt-tabell-fokus-{1280,390,200pct}.png`: tastaturfokus på radhodet (2 px ink-ramme, 1 px paper innvendig); samsvarer etter retting (ringen manglet før, se commit «Story 7.3: visuelle rettinger»).
- `oversikt-vegg-tilbake-{1280,390,200pct}.png`: veggen etter å ha byttet tilbake; samsvarer.
