# UX-avgjørelser etter klarhetssjekken

## 2026-11-14 kl. 17:41 — Bård Pettersen

### Oppgave
Kjøre `bmad-ux` i oppdateringsmodus for å ta de seks UX-avgjørelsene fra klarhetssjekken ([sprintplanlegging, klarhetssjekk](983-2026-11-12-23-38-58-sprintplanlegging-klarhetssjekk.md)) og føre dem inn i `EXPERIENCE.md` og `DESIGN.md`. Brukeren ville ha alternativene tegnet som SVG-figurer i stedet for en spørsmålsdialog i tekst.

### Plan
- Lese de berørte delene av UX-dokumentene, PRD og stories, og sette opp tre alternativer per avgjørelse.
- Tegne én figur per avgjørelse med alternativene side om side, bygget med byggeklossene fra mockupene (`vlib.py`), og kontrollere hver figur som PNG.
- Føre brukerens valg inn i UX-dokumentene, sammen med de to punktene som var bekreftet 2026-11-12 (Issue #31).
- Logge valgene i UX-loggen (`.memlog.md`) og oppdatere issuene.

### Resultat
- Seks figurer i `.docs/planning-artifacts/ux-designs/ux-beergame-2026-11-05/.working/valg-2026-11-13/` (`v1-matrisevegg`, `v2-pause`, `v3-ukebeskjed`, `v4-primaerknapp`, `v5-kostakse`, `v6-tidsbegrenset-test`), med `build.py` og PNG-er i `_png/`.
- Brukerens valg 2026-11-14:
  1. Matriseveggen: hele veggen kan leses celle for celle (C).
  2. Pause: Setestatus står på spillskjermen hele Uka, også før ordren (A).
  3. «Du får beskjed når Uke 12 åpner.» byttes med en linje som sier det som faktisk skjer (B).
  4. Klasseøkt: forhåndsvisningen av fordelingen er et panel på stedet, med «Bekreft fordeling» som primærknapp mens det er åpent (B).
  5. Kost per uke: aksen har ikke noe maksimum og vokser med 40 kr om gangen (B, endret av brukeren fra dobling).
  6. Tidsbegrenset test blir i v1 og viser tid igjen øverst (A).
- `EXPERIENCE.md` (22 endringer) og `DESIGN.md` (3 endringer) er oppdatert, `updated: 2026-11-14`, status fortsatt `final`. De to bekreftede punktene fra 2026-11-12 er også inne: Rolle og spill vises fra startdato, og «Ikke kontrollert med en Kontrolltest.» gjelder også standard sensorveiledning.
- Ny tekst er skrevet som utkast og merket `[ASSUMPTION: copy]`. Fire antakelser om oppførsel er merket på samme måte: linja «Venter på: …» tegnes ikke lenger under knappen, tastene i veggen, at «Tid igjen» teller hele minutter, og at etiketten «Mer tid før KI tar over» står uendret.
- Mockup 03, 04, 05, 06 og 08 er ikke tegnet på nytt. UX-dokumentene sier at de gjelder foran mockupene.
- Validering (bmad-ux sin gjennomgang) og språkgjennomgangen er ikke kjørt.
- Ikke committet: endringene i `EXPERIENCE.md`, `DESIGN.md` og `.memlog.md`, figurmappa og `implementation-readiness.md`.
- Issue #34 og #31 har fått kommentarer med avgjørelsene.

### Åpne punkter
- Issue #34: stories i `epics.md` må følge de seks avgjørelsene (6.7, 6.12, 6.14, 5.1, 5.8, 5.9, 7.2, 7.3, 7.7, 7.11, 8.6, 8.7, 8.9, 11.12, 4.5, 6.1, 11.2), og de øvrige funnene fra klarhetssjekken er ikke rettet. Deretter kjøres `bmad-sprint-planning` på nytt.
- Issue #34: brukeren må bekrefte utkastene til ny tekst og de fire antakelsene om oppførsel.
- Issue #31, #32 og #21 står som før.
