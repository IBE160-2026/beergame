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
- Ny fil `.env` i prosjektroten med bare variabelnavn. Den er git-ignorert og committes ikke. Brukeren fyller inn nøklene selv.
- Issue #35 er opprettet med hele sjekklista.
- Ikke gjort: ingen programmer er installert eller oppdatert, `.claude/settings.json` er ikke laget, og målteksten til `/goal` er ikke skrevet.

### Åpne punkter
- Issue #35: sjekklista før autonom bygging (programmer, Claude Code, avgjørelser, nøkler, klargjøring).
- Issue #31, #32 og #21 står som før.
