# UX-konsept 07 Pikselfabrikken

## 2026-11-05 kl. 16:45 — Bård Pettersen

### Oppgave
Lage konsept 07 av 10 parallelle SVG-designkonsepter for undervisningsappen, etter felles brief. Konseptet er et originalt håndholdt pikselspill med arbeidsnavnet Pikselkjeden, der lager, restordre og det som er på vei vises som kasser, hyller og pakker. Faglærer skal vurdere alle konseptene samlet.

### Plan
- Felles brief: `.docs/planning-artifacts/ux-designs/ux-beergame-2026-11-05/.working/concepts/_shared/BRIEF.md`.
- Bygge alt med `build.py`, med tall fra `_shared/fixture.json`, egne sprites og et 4 px-rutenett på telefonene.
- Rendre med `_shared/render.py`, se på PNG-ene og rette i samlede runder.

### Resultat
- Laget i `.docs/planning-artifacts/ux-designs/ux-beergame-2026-11-05/.working/concepts/07-pikselfabrikken/`: `build.py`, `concept.md`, 9 SVG-filer og `_png/`. Mappa er ikke committet.
- Grepet er at ett bånd-felt er én ankomstuke. De 16 på vei er 16 tellbare kasser (4, 4 og 8), og 24 tastet vises som hule kasser oppå dem før Sara bestiller.
- Alle 9 SVG-er validerer som XML. Skriptsjekk: bare klasser med `c07-`, ingen id-er, ingen `script`, ingen emoji eller piltegn i tekst, minste tekst 13 px, og «Demodata» på alle sider. «Beer» finnes bare i `07-debrief.svg`.
- Typografien ble byttet etter at jeg så renderen. Pixelify gjorde «fil» til «Al» og hadde utydelige versaler, Silkscreen Bold gjorde «4» til en klatt, Press Start hadde et 8-tall som ligner S, og Atkinson har null med skråstrek, som kan leses som Ø. Nå brukes Jersey 25 til titler og tall, og Rubik til tekst.
- Innholdsfeil rettet underveis: quizen røpet riktig svar, restordre i overgangsrammen stemte ikke med tallraden, og uken for lagertoppen hentes nå fra dataene (Lager 30 i uke 29).
- Sett i render: 05 og 06 i tre runder, 01, 02, 03, 04, 07, 08 og 09 i to runder.
- Ikke sett etter siste rettelser: 01 (bokser rundt Rolle-tallene), 07 (ny flyt i «Ditt øyeblikk») og 08 (etiketten Filtrering). Det samme gjelder 06, der teksten i KI-vinduet i ramme E er forkortet. Grensen for synsrunder var nådd.

### Åpne punkter
Ingen nye issues. Konseptet er ikke valgt ennå, så svakhetene står under «Ærlig risiko» i `concept.md`: pall for over 24 i ett felt er ikke tegnet, og feltene viser forventet ankomst, ikke sikker. Det må bli egne issues hvis konseptet velges.
