# Autobygg av alle stories

Kjøring etter `GOAL.md` og kjøreboka `.docs/implementation-artifacts/autobuild-runbook.md`. Én seksjon per story. Siste seksjon lister stories i `review` og `blocked` med issuene.

## Story 1.1: Stillas som starter lokalt uten nøkler (2026-11-17)

### Oppgave
Bygge Story 1.1 på grenen `epic-1`. Underveis ba brukeren om mappene `frontend/` og `backend/` i stedet for `web/` og `api/`.

### Plan
- `bmad-build-auto` i én underagent: spec, implementering, gjennomgang, commit.
- Etterpå: døpe om mappene og compose-tjenestene, rette stiene i epics, spine, oppsettsguide og kjørebok, og kjøre alle kontroller og stacken på nytt.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-1-1-scaffold-repo-zero-keys.md`. Commit `ccde93e` (stillaset), `94c1c5b` (omdøping), `286ae24` (status).
- Backend: 25 tester, ruff og format grønne. Frontend: `npm ci`, typecheck og build grønne. `docker compose up` gir fire friske tjenester (`postgres`, `backend`, `frontend`, `proxy`), og `/api/health` svarer 200 gjennom :8080.
- Gjennomgang: 35 funn, 17 rettet, 14 avvist med begrunnelse i specen, ett middels funn utsatt (CI bygger ikke compose-stacken).
- Omdøpingen: `api/` → `backend/`, `web/` → `frontend/`, også compose-tjenester, CI-jobber og Caddy-oppstrømmer. URL-stier som `/api/*` er uendret. Navnevalget står i spinen under «Source tree». Den flyttede `.venv` måtte lages på nytt.
- På denne maskinen holder en WSL-relé `::1:8080`, så lokale sjekker bruker `127.0.0.1:8080`.
- Status: `done`.

### Åpne punkter
- Issue #36: CI bygger ikke compose-stacken og Caddy.

## Story 1.2: Klassisk kjede uke for uke mot referansesporet (2026-11-17)

### Oppgave
Bygge Story 1.2 på `epic-1`. Brukeren sa underveis at det ikke skal være noen human in the loop: sjekker som kjøreboka la på grunnleggeren, tas av andre agenter og Playwright CLI.

### Plan
- `bmad-build-auto` i én underagent. Implementeringsagenten stoppet halvveis, og byggeagenten fullførte selv.
- Grunnleggerens sjekk av de ti første ukene erstattes av en uavhengig agent som regner dem ut uten å se byggerens tabell.
- Kjøreboka oppdateres: ingen stories settes til `review` for å vente på grunnleggeren.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-1-2-classic-chain-reference-trace.md`. Commit `1b1e27a` (story), pluss kjørebok og status.
- Ren motor i `backend/app/engine/` (`GameSettings`, `initial_state`, `advance`), `python -m app.sim trace`, to golden-spor (konstant 4 over 36 uker, steg til 8 over 10 uker), CI-krav om 100 % grenddekning av motoren.
- 86 tester grønne, ruff ren. Den uavhengige utregningen av uke 1–10 ga 0 avvik.
- Gjennomgang: 37 funn (0 høye, 3 middels), 7 grupper rettet, 30 avvist med begrunnelse.
- Kjøreboka sier nå at sjekker tas av agenter og Playwright CLI (`@playwright/cli@0.1.24`). Valget ligger også i minnet.
- Status: `done`.

### Åpne punkter
- Issue #37: fabrikkpipeline, uavhengig sjekk og anbefalt oppfølgende gjennomgang.

