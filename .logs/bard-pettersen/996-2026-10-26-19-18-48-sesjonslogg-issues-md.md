# Sesjonslogg-skillen: commit og issues.md

## 2026-10-26 kl. 19:18 — Bård Pettersen

### Oppgave
Forklare hvordan sesjonsloggingen fungerer, og endre brukerskillen `sesjonslogg` på tre punkter: (1) den skal alltid committe loggfila, så loggene ikke kommer ut av sync, (2) `book issues`-delen er spesifikk for website-prosjektet og skal ut av den generelle skillen, som igjen skal bruke `issues.md`, og (3) website-prosjektet skal selv si at det bruker book CLI.

### Plan
- Plan godkjent i plan-modus: `C:\Users\pape\.claude\plans\pasted-content-id-95a7-issues-robust-catmull.md`.
- Commit-krav først, så issues.md-omleggingen. Siden `issues.md` da endres hver økt, ble commit-regelen utvidet til loggfil + `issues.md` (valgt av brukeren).
- `book`-regelen legges i website-prosjektets `AGENTS.md`, siden `CLAUDE.md` der bare er `@AGENTS.md` og `AGENTS.md` har et tak på 100 linjer.
- Rette beergames `CLAUDE.md`, som fortsatt nevnte `book issues`.

### Resultat
- `C:\Users\pape\.claude\skills\sesjonslogg\SKILL.md`:
  - ny seksjon «Commit loggfila (alltid)». Path-begrenset commit (`git add -- …` + `git commit -m "Logg: <tittel>" -- …`) av loggfila og `issues.md`, ingenting annet. Kontroll med `git show --stat HEAD`, ingen push, ingen `--no-verify`, og prosjektets egen commit-konvensjon vinner hvis den finnes.
  - seksjonen «Issues gjennom book-CLI-en» erstattet av `issues.md` (per bruker, `- [ ]`/`- [x] … (løst dato)`, aldri slette linjer). Unntak: prosjektets `CLAUDE.md`/`AGENTS.md` kan si at punkter føres et annet sted. Ingen `book`-treff igjen i skillen.
  - øvrige referanser rettet (beskrivelse, formål, mal, forankring-sitat, oppstart av fortsettelse).
- `D:\pytagoras\projects\websites\_migration-port1-final-20260821\AGENTS.md`, regel 2: åpne punkter føres «alltid» som `Agent`-merkede Issues via `book issues`, aldri i `issues.md`. Fortsatt 100 linjer. Ikke committet, og fila hadde andre ukommitterte endringer fra før som ikke er mine.
- `CLAUDE.md` i beergame: «oppretter/lukker … via `book issues`» byttet til «fører åpne punkter i `.logs/<bruker>/issues.md`». Ikke committet (bare logg + `issues.md` committes av skillen).
- Åpnet SKILL.md og Cursor i prosjektmappen på forespørsel.
- Overgang til GitHub Issues i beergame (senere i økten): `CLAUDE.md` sier nå at åpne punkter føres med `gh issue` (etikett `agent`), aldri i `issues.md`. Etiketten `agent` er opprettet i `IBE160-2026/beergame` (offentlig repo, issues aktivert, `gh` innlogget). Konkurrentpunktet er opprettet som Issue #1 (https://github.com/IBE160-2026/beergame/issues/1). Punktet om loggrot i website-prosjektet ble bevisst ikke ført til det offentlige repoet og står igjen i `issues.md`. `CLAUDE.md` er endret, men ikke committet. Brukerskillen er ikke endret: den sier at prosjektets `CLAUDE.md` overstyrer `issues.md`, så den følger denne instruksen.
- Ikke testet i en ekte økt utover denne loggføringen. Beergame har ikke hatt `issues.md` før nå; åpne punkter fra `999-…-product-brief.md` er ikke overført.

### Åpne punkter
- Issue #1 — konkurrentverifisering står igjen: `.docs/planning-artifacts/research/competition.md` (commit `062cfb5`) inneholder bare spørsmålet «What competition exists?». Først ført inn i `issues.md` etter at jeg feilaktig hadde antatt at researchen var gjort ut fra commit-meldingen; flyttet til GitHub senere i økten. Opprinnelig punkt fra `999-2026-09-07-16-11-51-product-brief.md`.
- Skillen skriver til `.logs/<bruker-slug>/`, mens website-prosjektets `AGENTS.md` og `docs/70-logg/README.md` sier at logger skal ligge i `docs/70-logg/<bruker>/` (markørfila `.pytagoras-docs`, RYDDELISTE sak 3). Skillen må kunne peke på riktig loggrot i website-prosjektet før `.logs/` fjernes fra kodrepoene.
