# Story 5.4 — skjermbilder (390 og 1280 px)

Fersk Klasse og Klasseøkt per bredde gjennom api-et, innlogget som faglaerer@example.com, `locale: 'nb-NO'`. Sammenlignet med mockup 03, DESIGN.md og EXPERIENCE.md. Ingen siderulling sideveis i noe bilde.

- `klasseokt-klassisk-390.png` / `-1280.png`: lesevisning, Klassisk; «Etterspørsel 4, så 8 fra Uke 5» i lista, «Kundene» med «4, så 8» (lager, halvfet) og «fra Uke 5» under, som mockup 03 (Issue #98). Stemmer. På 390 px ligger «Kundene» i diagrammets egen rulleflate (se `kjede-klassisk-rullet-390.png`).
- `klasseokt-serietabell-390.png` / `-1280.png`: «Skjul etterspørselen uke for uke» åpen, tabell Uke | Etterspørsel, tall høyrejustert, uke 5 går til 8, avgrenset rulleflate med fast topprad. Stemmer.
- `endre-trinn-390.png` / `-1280.png`: åpen blokk, «Etterspørsel» under de elleve feltene, «Mønster» = Trinn med Startnivå, Nytt nivå, Endres fra uke; én primærknapp. Stemmer. (Valgt tekst i nedtrekket ser ut til å tegnes i systemfonten selv om beregnet font er Source Sans 3; felles komponent, se åpne punkter.)
- `endre-fast-serie-390.png` / `-1280.png`: «Fast serie», tomt felt «Etterspørsel per uke» over full bredde med hint. Stemmer.
- `endre-feil-lengde-390.png` / `-1280.png`: seks verdier mot 36 uker; rød kant og «Skriv ett helt tall per uke, 36 tall i alt.» under hintet. Stemmer.
- `endre-tilfeldig-390.png` / `-1280.png`: «Tilfeldig», Snitt 4 overført fra Startnivå, tom Spredning, «Frø» forhåndsutfylt med serverens frø og hint. Stemmer.
- `endre-trinn-variasjon-feil-390.png` / `-1280.png`: «Trinn med tilfeldig variasjon», Spredning 30 med «Må være fra 0 til 20.» under feltet, Frø synlig. Stemmer.
- `endre-trinn-variasjon-390.png` / `-1280.png`: samme mønster med gyldige verdier, ingen feil. Stemmer.
- `klasseokt-tilfeldig-fro-390.png` / `-1280.png`: lagret Tilfeldig 8 ± 2 med frø 42; raden «Frø 42», advarselen om I hvert ledd under sin rad, «Kundene» «8 ± 2» / «tilfeldig», kalibreringslinja. Stemmer.
- `endre-fast-serie-lang-390.png` / `-1280.png`: 52 uker og en fast serie på 52 tall. Stemmer i oppsett, men serien står i et enlinjes felt der bare de første 10–15 tallene vises (avvik til vurdering).
- `klasseokt-fast-serie-lang-390.png` / `-1280.png`: lagret, «Fast serie over 52 uker», tabell med 52 rader i rulleflaten, «Kundene» «Fast serie» / «52 uker», advarsel om Største ordre. Stemmer.
- `kjede-klassisk-rullet-390.png`: kjeden rullet til høyre ende på 390 px; «Kundene», «4, så 8», «fra Uke 5» helt synlige, falming på venstre side. Stemmer.
- `kjede-lang-linje-rullet-390.png`: Trinn med variasjon 100, så 100 ± 20 fra Uke 20; den lange linja får plass i diagrammet. Stemmer.

## Til vurdering (ikke rettet)

- En fast serie på 36–52 tall i ett enlinjes Tekstfelt: det meste av serien er skjult i feltet, så faglæreren ser ikke hele serien mens hen redigerer (et `textarea` som brytes ville vist alt; endrer komponent og Enter-oppførsel).
- Nedtrekket «Mønster» viser valgt tekst i det som ser ut som systemfonten (Windows/Chromium); felles `SelectField`, også brukt i tidligere skjermer.
- Datofeltene viser `mm/dd/yyyy` i headless Chromium; følger nettleserens språk, ikke denne historien.
