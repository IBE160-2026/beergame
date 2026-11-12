# Figur: epics, stories og sprintplan

## 2026-11-12 kl. 13:53 — Bård Pettersen

### Oppgave
Kjøre `bmad-help` for å se hvor prosjektet står, og deretter lage en SVG-figur som viser hvordan epics og stories henger sammen, med sprintplanlegging, og forklare hvorfor steget gjøres. Figuren skulle bruke ØL-spillet som eksempel.

### Plan
- `bmad-help`: lese katalog, konfig, artefakter, forrige logg og åpne issues. Konklusjon: brief, research, PRD, UX og arkitektur er ferdige; epics og stories er neste påkrevde steg, men brukeren har sagt at det venter til han sier ifra.
- Hente eksempler fra PRD (FR-23 til FR-29) og arkitekturen (AD-1, AD-2, AD-3, AD-20), og statusverdiene fra `bmad-sprint-planning`.
- Tegne figuren med fargene og skriften fra `DESIGN.md`, og kontrollere den med en PNG-gjengivelse i Edge headless.

### Resultat
- Ny fil: `.docs/figures/epics-stories-sprintplan.svg` (ikke committet). Fem trinn: grunnlag (PRD, UX, arkitektur), seks eksempel-epics, fem stories under «Spilling uke for uke», story 4.2 «Legge inn ordre» åpnet med akseptansekriterier fra FR-24, og sprintplan med klarhetssjekk (PASS, CONCERNS, FAIL), `sprint-status.yaml` og bygging. Nederst tre grunner til steget: riktig størrelse, sporbarhet, rekkefølge og status.
- Figuren sier selv at inndelingen i epics og stories er en illustrasjon. Den endelige lages av `bmad-create-epics-and-stories`.
- Kontrollert: gyldig XML, og gjengivelsen viser ingen tekst som overlapper eller går ut av boksene.
- Ingen issues ble åpnet eller lukket.
- Senere samme økt: figuren er committet som `13ddfd1` og pushet til `origin/main` på brukerens forespørsel. Punktet over om «ikke committet» gjelder derfor ikke lenger.

### Åpne punkter
Ingen.
