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

## 2026-11-14 kl. 17:55 — Bård Pettersen

### Oppgave
Rette `epics.md` etter de seks UX-avgjørelsene og de øvrige funnene fra klarhetssjekken, og gjøre alt klart til `bmad-sprint-planning`.

### Plan
- Lese hver berørt story og rette kriteriene med et skript som krever at hver tekst som byttes finnes nøyaktig én gang.
- Føre avgjørelsene, utkastene til tekst og valgene som ble tatt under rettingen inn i `open-assumptions.md`.
- Føre de nye kommandoene inn i AD-2 i arkitekturen (Issue #32).
- Kjøre de mekaniske kontrollene og prøvekjøringen av sprintskriptet på nytt.

### Resultat
- `epics.md`: 51 endringer i 36 stories lukker alle 29 funn. Ingen stories er lagt til, fjernet eller omnummerert. Berørte stories: 3.1, 3.12, 4.5, 5.1, 5.8, 5.9, 6.1, 6.2, 6.3, 6.6, 6.7, 6.9, 6.11, 6.12, 6.14, 6.15, 6.16, 6.17, 7.1, 7.2, 7.3, 7.6, 7.7, 7.8, 7.9, 8.6, 8.7, 8.11, 8.12, 9.5, 9.15, 11.2, 11.12, 13.3, 13.4 og 13.8.
- `open-assumptions.md`: ny del med de seks avgjørelsene, fire utkast til tekst som må bekreftes, åtte tekster som fortsatt må skrives, og elleve valg tatt under rettingen.
- `ARCHITECTURE-SPINE.md`: AD-2 lister nå `advance`, `set_snapshot`, `propose_time`, `accept_time`, `recompute_turn_times`, `end_in_room` og `close`, aktøren på `place_order` og `start`, og erstatt-argumentet på `assign_seat`.
- `implementation-readiness.md`: ny del «Status after the fixes (2026-11-14)».
- Kontroller kjørt på nytt, alle består: 199 stories, 1 252 kriterier (3 til 8 per story), alle FR, NFR, AD-regler og UX-krav i en `Covers:`-linje, 450 av 468 siterte norske strenger stemmer nøyaktig med UX-dokumentene (resten er eksempelverdier og overskrifter). Tre nye henvisninger til senere stories er overleveringer (6.9 og 7.8 til 9.5, 6.15 til 6.16). Prøvekjøringen av `sprint_plan.py` leser 15 epics og 199 stories.
- Begrensning: rettingene er ikke lest av en annen leser, og mockup 03, 04, 05, 06 og 08 er ikke tegnet på nytt.
- Issue #34 er lukket. Issue #31 og #32 har fått kommentarer.
- Committet som `ff3eb3b` etter at brukeren ba om det: `epics.md`, `open-assumptions.md`, `ARCHITECTURE-SPINE.md`, `EXPERIENCE.md`, `DESIGN.md`, de to `.memlog.md`-filene, figurmappa og `implementation-readiness.md`. Ikke pushet. Mappa `.working/` under epics er holdt utenfor. `sprint-status.yaml` er ikke laget; det gjør `bmad-sprint-planning`.

### Åpne punkter
- Issue #31: bekrefte utkastene til tekst og valgene i den nye delen av `open-assumptions.md`, og avgjøre sen registrering uten ledig sete (Story 5.13, FR-20).
- Issue #32: hendelsesemner per kommando og de andre tilleggene mangler fortsatt i arkitekturen.
- Issue #21: datoplan mot kursdatoen mangler.
