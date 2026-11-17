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
- Utsatt til slutt: Story 3.15 og delene av Epic 15 som må kjøres mot produksjon (15.10, 15.14, og punktene grunnleggeren fyller inn i 15.9 og 15.11). Story 3.14 bygges på plass i Epic 3 (bestemt av brukeren); Story 13.7 og 15.9 bygger på den.
- Issue #35 er opprettet med hele sjekklista.
- Programmene er gjort klare etter at brukeren ba om det: uv er oppdatert fra 0.5.21 til 0.13.7, Node.js 24.22.3 er lastet ned fra nodejs.org (sjekksum kontrollert), pakket ut i nvm-mappa og gjort aktiv, og Docker Desktop er startet. Autostart sto alt på. `nvm install` ga ingen utdata i dette skallet, derfor ble Node installert for hånd. Byttet av aktiv versjon krevde en elevert kommando.
- Kontroll etterpå: `node -v` gir v24.22.3, `uv --version` gir 0.13.7, og `docker run postgres:17` starter. Portene 8080, 5432, 3000 og 8000 er fortsatt ledige, selv om Docker startet 24 containere fra før.
- De 24 containerne fra før er stoppet etter at brukeren ba om det. De er ikke slettet, og volumene er urørt. De har omstartsregelen `unless-stopped`, så de starter ikke igjen av seg selv.
- Brukeren har lagt inn LLM-nøkkelen i `.env`. Dvale og dvalemodus er slått av på strøm med `powercfg` (begge `0`, kontrollert). Windows Update er tatt ut av lista etter at brukeren bestemte å ikke gjøre noe med den nå.
- Økten kjører i bypass permissions. Brukeren ba om sperrer, så 62 `deny`-regler er lagt i `.claude/settings.local.json` (git-ignorert): alle Neon- og Railway-verktøy og `railway`, force-push, sletting av grener og repo med `git`/`gh`, `docker prune/rm/rmi/volume rm`, `rm -rf` og `Remove-Item` mot absolutte stier og `..`, lesing av `.env`, og endring av `.env` og settings-filene. Kontrollert: `docker rm` blir avvist. Sperrene er prefiksregler, ikke en sandkasse.
- Avgjørelsene i Issue #35 er tatt:
  - Omfang: alt som kan bygges lokalt.
  - Git: én gren per epic, én commit per story og push etter hver, og merge til `main` når CI er grønn. Brukeren har gitt stående tillatelse til commit, push og merge for kjøringen.
  - Blokkerte stories: agenten løser problemet selv og fører et issue med beslutningene den tok.
  - Stories som trenger grunnleggeren: settes til `review` med et issue.
  - Antakelsene i `open-assumptions.md` bygges som de står.
  - Sesjonsloggen føres med én seksjon per story.
- Story 5.13 og FR-20: før startdatoen gir sen registrering uten ledig sete et nytt klassespill. `prd.md` (FR-20) og `open-assumptions.md` er rettet, ikke committet. Issue #35 er oppdatert, og Issue #31 har fått en kommentar.
- Arbeidskopien er ren: `.working/` under epics er lagt i `.gitignore`, og FR-20, `open-assumptions.md` og `.gitignore` er committet som `cb7ba05`.
- Kjøreboka `.docs/implementation-artifacts/autobuild-runbook.md` er committet som `ba20359`. Den sier hvordan hver story bygges med en underagent som kjører `bmad-build-auto`, hvordan sprint-status, commit, push, issue og logg håndteres, hvordan epics merges, og hvilke regler som gjelder. Målteksten til `/goal` (1 238 tegn) peker til kjøreboka. Den ligger i scratchpad og ble gitt til brukeren i chatten.
- Brukeren ba om commit og push: `main` er pushet til `origin/main` (`e24dfed..67f543b`).
- Brukeren spurte om agentene tester appen med Playwright CLI. Svar: `bmad-build-auto` sier ingenting om Playwright. 116 stories har Playwright-tester i kriteriene, men det er automatiske tester i CI, ikke en visuell kontroll. Brukeren ba om en visuell kontroll, og den er lagt inn i kjøreboka som steg 5 (`f2498f7`). For hver story som endrer en skjerm tar en underagent skjermbilder på 390 og 1280 px med Playwright. Bildene legges i `.docs/implementation-artifacts/screenshots/<N.M>/` og sammenlignes med mockupene, `DESIGN.md` og `EXPERIENCE.md`. Klare avvik rettes, og resten føres i et issue.
- Målteksten ligger i `GOAL.md` i rotmappa, skrevet av brukeren. Den er committet (`daa4e18`) etter brukerens ønske, så arbeidskopien er ren.
- Ikke gjort: dvale og Windows Update er ikke endret, `.claude/settings.json` er ikke laget, og målteksten til `/goal` er ikke skrevet.

### Åpne punkter
- Issue #35: sjekklista før autonom bygging (programmer, Claude Code, avgjørelser, LLM-nøkkelen, klargjøring).
- Issue #31, #32 og #21 står som før.
