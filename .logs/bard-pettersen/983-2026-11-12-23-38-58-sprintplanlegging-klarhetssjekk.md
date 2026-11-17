# Sprintplanlegging: klarhetssjekk for ØL-spillet

## 2026-11-12 kl. 23:38 — Bård Pettersen

### Oppgave
Kjøre `bmad-sprint-planning` for ØL-spillet v1: først kontrollere at planleggingen er god nok til å bygge fra, deretter lage `sprint-status.yaml` fra epics. Forrige økt ([epics og stories](984-2026-11-12-15-11-37-epics-og-stories.md)) pekte på denne som neste steg.

### Plan
- Kartlegge planleggingsdokumentene: brief, PRD med addendum, arkitektur, UX-dokumentene, `epics.md` og `open-assumptions.md`.
- Mekaniske kontroller med skript: at hvert krav er dekket av en story, henvisninger til senere stories, og siterte norske strenger mot UX-dokumentene.
- Tre subagenter leste hvert UX-krav (26 hver) mot stories som dekker det. Dette var kontrollen Issue #33 ba om.
- Egen kontroll av arkitekturen mot stories, de åpne issuene som mater tidlige epics, og de tre viktigste funnene fra leserne.
- Prøvekjøring av `sprint_plan.py generate --dry-run`.

### Resultat
- Dom: **CONCERNS**. Brukeren valgte «Fix first», så `sprint-status.yaml` er **ikke** laget.
- Funnene er skrevet til `.docs/planning-artifacts/implementation-readiness.md` (ny fil, ikke committet).
- Det som holder: alle 89 FR, 10 NFR, 26 AD-regler og 78 UX-krav står i en `Covers:`-linje. De 28 henvisningene til senere stories er overleveringer, ikke avhengigheter. 435 av 452 siterte norske strenger stemmer nøyaktig med `EXPERIENCE.md` eller `DESIGN.md`. Prøvekjøringen leser alle 15 epics og 199 stories; de to advarslene gjelder dokumenttittelen og overskriften «Epic List».
- UX-kontrollen: 48 av 78 UX-krav er dekket uten funn. 29 funn: 4 konflikter, 13 mangler og 12 mindre. Ingen berører Epic 1 eller 2. De tre konfliktene leserne meldte er kontrollert i teksten:
  - Matriseveggen: radene kan få fokus (7.2, 7.7, 7.11), men veggen er `aria-hidden` (7.3).
  - Pause: pauselinja og «Ta pause» er plassert ved Setestatus (8.6), som en Student først ser etter å ha bestilt (6.14).
  - Revisjonsloggen ruller i egen region ved 320 px (3.12), mot `DESIGN.md`.
- Eget funn: Story 4.5 og 6.1 siterer invitasjonslinja som avgjørelsen om startdato har gjort feil.
- Bekreftet at arkitekturen ikke er oppdatert med kommandoene og tabellene stories legger til (Issue #32), og at `EXPERIENCE.md` fortsatt har de to utdaterte punktene (Issue #31).
- Ikke kontrollert: mockup-bildene er ikke åpnet, UX-DR75 og UX-DR76 er stikkprøvd, og tokenverdiene i `DESIGN.md` er ikke sammenlignet med stories. For innholdet i hvert FR bygger sjekken på valideringen fra forrige økt; her ble bare id-ene kontrollert.
- Issue #33 er lukket (kontrollen er gjort). Issue #34 er åpnet med funnene. Issue #31 har fått en kommentar om Story 4.5 og 6.1.

### Åpne punkter
- Issue #34: rette de 29 UX-funnene i `epics.md`, `EXPERIENCE.md` og `DESIGN.md`, og deretter kjøre `bmad-sprint-planning` på nytt. Seks av funnene trenger en UX-avgjørelse først (Matriseveggen, pauseplasseringen, «Du får beskjed når Uke 12 åpner.», primærknappen på Klasseøkt, kostnadsaksen over 40 kr, tidsbegrenset test).
- Issue #31: antakelsene i `open-assumptions.md` er fortsatt ubekreftet, og sen registrering uten ledig sete (FR-20, Story 5.13) trenger avgjørelse.
- Issue #32: arkitekturen mangler de nye kommandoene. Den første er `games.commands.advance` i Story 2.1.
- Issue #21: datoplan for 199 stories mot kursdatoen mangler.

## 2026-11-17 kl. 12:29 — Bård Pettersen

### Oppgave
Kjøre `bmad-sprint-planning` på nytt etter at funnene fra klarhetssjekken er rettet ([UX-avgjørelser etter klarhetssjekken](982-2026-11-14-17-41-55-ux-avgjorelser-etter-klarhetssjekk.md)), og lage `sprint-status.yaml`.

### Plan
- Kjøre de mekaniske kontrollene på nytt på den committede planen (`ff3eb3b`).
- Lage sporingsfila med `sprint_plan.py generate` og validere den med `validate`.
- Føre status inn i `implementation-readiness.md`.

### Resultat
- Kontrollene ga samme resultat som 2026-11-14: 199 stories, alle FR, NFR, AD-regler og UX-krav i en `Covers:`-linje, 450 av 468 siterte norske strenger stemmer nøyaktig med UX-dokumentene, og henvisningene til senere stories er overleveringer. Planfilene er uendret siden commiten.
- Klarhetssjekken er ikke lest på nytt av uavhengige lesere. Vurderingen bygger på sjekken 2026-11-12 og rettingene 2026-11-14.
- Ny fil `.docs/implementation-artifacts/sprint-status.yaml`: 15 epics, 199 stories og 15 retrospektiver. Alle epics og stories står som `backlog`, retrospektivene som `optional`. `validate` gir ingen feil, og ingen nøkler er like.
- Skriptet ga to advarsler, som ved prøvekjøringen: dokumenttittelen og overskriften «Epic List» er ikke epics.
- Nøklene er kuttet ved 60 tegn, og fem nøkler har æ, ø eller å (4.1, 6.9, 7.11, 13.2, 13.4).
- `implementation-readiness.md` har fått en statuslinje for 2026-11-17.
- Committet som `8a7b5c2` etter at brukeren ba om det: `sprint-status.yaml` og endringen i `implementation-readiness.md`. Pushet til `origin/main` sammen med de tidligere commitene fra klarhetssjekken. Mappa `.working/` under epics er holdt utenfor.

### Åpne punkter
- Issue #31: bekrefte utkastene til tekst og valgene i `open-assumptions.md`, og avgjøre sen registrering uten ledig sete (Story 5.13, FR-20).
- Issue #32: hendelsesemner per kommando og de andre tilleggene mangler fortsatt i arkitekturen.
- Issue #21: datoplan mot kursdatoen mangler.
