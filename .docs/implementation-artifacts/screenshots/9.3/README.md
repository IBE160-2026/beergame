# Story 9.3: skjermbilder (Debrief steg 1, Forklaringen før avsløringen)

Student `student@example.com`, Debrief-endepunktene besvart med de samme stand-in-svarene som `frontend/e2e/debrief-explanation.spec.ts`; innlogging og sider fra lane-stakken (`http://127.0.0.1:8081`). Bredder: 390 og 1280 px, og 390 px med 200 % tekst (`-390-200`). Sammenlignet med `07-debrief.png` (kolonne 1), DESIGN.md og EXPERIENCE.md. Ingen sidescroll i noen av dem (scrollWidth = clientWidth).

- `steg1-tomt-390.png`, `steg1-tomt-1280.png`: tom Forklaring; netto lager-grafen (null-linje, lager blått, restordre rødt, akser -40 til 20, Uke 1/12/24/36), «Vis som tabell», Tekstfelt, hint, grunn «Skriv Forklaringen før du sender.» og inaktiv «Send Forklaring». Samsvarer, bortsett fra mockupens Uke-stripe under grafen (se under).
- `steg1-tomt-390-200.png`: som over med 200 % tekst; alt brytes om, ingenting kuttes, ingen sidescroll. Samsvarer (overskriften deles med bindestrek «Forklarin-gen», det samme som øvrige overskrifter).
- `steg1-skrevet-390.png`, `steg1-skrevet-1280.png`: tekst skrevet, én primærknapp «Send Forklaring» aktiv og mørk, som i mockupen. Samsvarer.
- `steg1-tabell-390.png`, `steg1-tabell-1280.png`: «Vis som tabell» viser Uke og Netto lager for alle 36 uker i stedet for grafen, «Vis som graf» tilbake. Samsvarer med kravet; bare de 36 radene gjør siden lang, så Tekstfeltet havner langt nede (til vurdering).
- `steg1-sendt-390.png`, `steg1-sendt-1280.png`: sendt tilstand: «Din Forklaring» skrivebeskyttet med forklaringen og «Forklaringen er sendt og lagret slik du skrev den.»; feltet og knappen er borte, grafen står igjen. Samsvarer (mockupen tegner ikke denne tilstanden; kopi merket [ASSUMPTION]).
- `steg1-lastefeil-390.png`, `steg1-lastefeil-1280.png`: netto lager-lesingen svarer 500: «Dette steget kunne ikke hentes.» med «Prøv igjen», og Tekstfeltet kan fortsatt brukes. Samsvarer.

## Til vurdering (ikke endret)

1. Mockupen har en Uke-stripe (blå/rød celler per uke) under grafen; implementasjonen har ikke den. Spesifikasjonen ber bare om graf med fyll, akser og Uke-etiketter.
2. Tabellvisningen er ikke høydebegrenset, så 36 rader skyver Tekstfeltet langt ned på telefon.
