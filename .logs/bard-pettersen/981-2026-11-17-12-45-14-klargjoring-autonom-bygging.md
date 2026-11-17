# Klargjøring før autonom bygging

## 2026-11-17 kl. 12:45 — Bård Pettersen

### Oppgave
Brukeren vil bruke `/goal` til å bygge alle epics og stories uten at noen følger med, med én underagent per story. Først skulle det kartlegges hva brukeren må gjøre på forhånd: API-nøkler, CLI-programmer og annet. Underveis sa brukeren at nøklene skal legges inn før `/goal` kjøres.

### Plan
- Lese `SETUP-GUIDE.md`, `technology.md` og versjonstabellen i `ARCHITECTURE-SPINE.md` for kontoer, nøkler og låste versjoner.
- Søke i `epics.md` etter stories som trenger ekte nøkler, produksjon eller grunnleggeren.
- Sjekke hvilke programmer som finnes på maskinen, og innstillingene i git og GitHub-repoet.
- Lese `bmad-build-auto` for hva en kjøring uten tilsyn krever.
- La en underagent slå opp `/goal` i dokumentasjonen til Claude Code.

### Resultat
- Ingen nøkler trengs for selve byggingen: alle integrasjoner kjører som mock lokalt og i CI (AD-17).
- Maskinen: Docker Desktop er installert, men kjørte ikke. Node er 23.11 (arkitekturen låser 24), og uv er 0.5.21 (låst til 0.13.7). Python 3.14, git, `gh`, Railway CLI og Claude Code 2.1.326 er i orden. Portene 8080, 5432, 3000 og 8000 er ledige.
- Repoet: offentlig, Actions er på, `main` er ikke beskyttet. Mappa `.working/` under epics er usporet, og `bmad-build-auto` krever en ren arbeidskopi.
- Stories som ikke kan fullføres uten grunnleggeren: 1.2, 2.7, 3.15, 15.10, 15.11, 15.13 og 15.14.
- `/goal` (fra dokumentasjonen): vilkåret vurderes av en liten modell etter hver tur, det finnes ingen innebygd grense for turer eller tokens, auto-modus anbefales, kjøringen pauser ved bruksgrensen, og målet hentes tilbake med `claude --continue`. Underagenter kan starte egne underagenter i tre lag.
- Brukeren bestemte to ting underveis: byggingen kjøres bare lokalt (Postgres i Docker, fillagring i `./.local-storage/`, e-post som mock), og klargjøring til produksjon tas helt til slutt, når nettsiden er godkjent. AWS Bedrock er valgt bort.
- Ny fil `.env` i prosjektroten. Den er git-ignorert og committes ikke. Den har bare `OPENROUTER_API_KEY` og `OPENROUTER_BASE_URL`, og brukeren fyller inn nøkkelen selv. LLM-nøkkelen er den eneste nøkkelen lokal kjøring kan bruke, og den er valgfri (Story 2.7 og 2.11).
- Utsatt til slutt: Story 3.15 og delene av Epic 15 som må kjøres mot produksjon (15.10, 15.14, og punktene grunnleggeren fyller inn i 15.9 og 15.11). Story 3.14 er ikke avgjort; Story 13.7 og 15.9 bygger på den.
- Issue #35 er opprettet med hele sjekklista.
- Ikke gjort: ingen programmer er installert eller oppdatert, `.claude/settings.json` er ikke laget, og målteksten til `/goal` er ikke skrevet.

### Åpne punkter
- Issue #35: sjekklista før autonom bygging (programmer, Claude Code, avgjørelser, LLM-nøkkelen, klargjøring), og avgjørelsen om Story 3.14 skal bygges på plass eller utsettes.
- Issue #31, #32 og #21 står som før.
