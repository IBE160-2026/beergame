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

## Story 1.3: Innstillinger mot grenser og advarsler (2026-11-17)

### Oppgave
Bygge Story 1.3 på `epic-1`.

### Plan
`bmad-build-auto` i én underagent. Implementeringsagenten stoppet etter kode og referansespor. En uavhengig agent regnet ut sporene for hånd, og byggeagenten fullførte verifisering og gjennomgang selv.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-1-3-settings-ranges-and-warnings.md`. Commit `89f2943`.
- `starting_backlog`, `RANGES`, `validate` og `warnings` med stabile koder, og `python -m app.sim settings check <fil>` med utkodene 0, 1 og 2.
- To nye referansespor (forsinkelser 1/1/1 og 3/3/3). Den uavhengige håndutregningen ga 0 avvik.
- 185 tester grønne, full grenddekning av motoren, ruff ren. Gjennomgang: 26 funn, 8 rettet, 18 avvist.
- Status: `done`.

### Åpne punkter
- Issue #38: plassholdergrenser, faktoren ×10 og startverdier per rolle.

## Story 1.4: Etterspørselsserie fra mønster og frø (2026-11-17)

### Oppgave
Bygge Story 1.4 på `epic-1`.

### Plan
`bmad-build-auto` i én underagent, som nå implementerer selv og bare bruker underagenter til gjennomgang og uavhengige sjekker.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-1-4-demand-series-from-pattern-and-seed.md`. Commit `953d76a`.
- `backend/app/engine/demand.py` med fire mønstre (fast, steg, tilfeldig, steg+støy), `series(pattern, weeks, seed)`, `new_seed`, `demand_seed` i `GameSettings`, og `python -m app.sim demand`.
- 662 tester grønne, full grenddekning av motoren, ruff ren. Golden-seriene er sjekket av en uavhengig agent med egen kode.
- Gjennomgang: 30 funn, ett middels rettet (`--weeks 0` krasjet), flere lave rettet, resten avvist.
- Status: `done`.

### Åpne punkter
- Issue #39: beslutninger om frø, trekning og plassholdergrenser.

## Story 1.5: Riktig bokføring ved konstruksjon (2026-11-17)

### Oppgave
Bygge Story 1.5 på `epic-1`.

### Plan
`bmad-build-auto` i én underagent, med implementering i egen kontekst og gjennomgang i underagenter.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-1-5-bookkeeping-correct-by-construction.md`. Commit `7b988ef`.
- Ren sjekk `backend/app/engine/check.py`: `conservation(settings, states, orders)` gir en liste brudd med regel, uke og rolle. Den regner ut forventede verdier selv i stedet for å kalle motoren.
- 736 tester grønne (300 tilfeldige spill med fast frø), full grenddekning, ruff ren.
- Gjennomgang i to runder. Første runde fant at en plass kunne sende mer enn den hadde. Ny forsendelsesregel ble lagt til. Andre runde: fem små rettinger.
- Status: `done`.

### Åpne punkter
- Issue #40: beslutninger om egenskapstester, enheter underveis og forsendelsesregelen.

## Story 1.6: Bestille med den regelbaserte spilleren (2026-11-17)

### Oppgave
Bygge Story 1.6 på `epic-1`.

### Plan
`bmad-build-auto` i én underagent, med implementering i egen kontekst og gjennomgang i underagenter.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-1-6-order-with-rule-based-player.md`. Commit `144f568`.
- `SeatView` med bare tall, `engine.rule_based.order` (Sterman-forankring), `engine.guided_order`, parametersettet `placeholder-unverified` som JSON, `rule_based.md`, `sim trace --orders rule_based` med advarsel, og et golden-spor.
- 817 tester grønne, full grenddekning av motoren, ruff ren.
- Gjennomgang: første runde fant at forsyningslinjen manglet oppstrøms startrestordre (12 i stedet for 32). Det ble rettet, og andre runde fant bare små ting.
- Status: `done`.

### Åpne punkter
- Issue #41: plassholderparametere og tolkninger i regelspilleren.

## Story 1.7: Simuleringsspill med AI-spiller på hver plass (2026-11-17)

### Oppgave
Bygge Story 1.7 på `epic-1`.

### Plan
`bmad-build-auto` i én underagent, med implementering i egen kontekst og gjennomgang i underagenter.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-1-7-create-simulation-game-ai-seats.md`. Commit `47d58ef`.
- Alembic `0002` med `games`, `seats` og `seat_occupancy` (trigger nekter endring), `games.commands.create` og `assign_seat`, `games.policy`, `platform/events`, `engine.scripted.REGISTRY` og `python -m app.sim create`.
- 899 tester grønne, full grenddekning av motoren, ruff ren. `sim create --settings classic --seats rule_based` virker.
- Gjennomgang: 38 funn (5 middels), de middels rettet, resten avvist med begrunnelse.
- Status: `done`.

### Åpne punkter
- Issue #42: beslutninger om spillopprettelse, policy og hendelser, og anbefalt oppfølgende gjennomgang.

## Story 1.8: Starte spillet og lese hva hver plass ser (2026-11-17)

### Oppgave
Bygge Story 1.8 på `epic-1`.

### Plan
`bmad-build-auto` i én underagent, med implementering i egen kontekst og gjennomgang i underagenter.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-1-8-start-game-read-seat-state.md`. Commit `a7e2adb`.
- `games.commands.start`, `SeatState` for hver plass i den åpne uka, og `python -m app.sim start` og `show <id> --seat retailer`.
- 949 tester grønne, full grenddekning av motoren, ruff ren. Create, start og show er kjørt mot den lokale databasen.
- Gjennomgang: 34 funn, ett middels (manglende test av referanseordre per plass) og 8 lave rettet, resten avvist.
- Status: `done`.

### Åpne punkter
- Issue #43: felt i `SeatState`, forhåndsvisning og at `game_weeks` ikke er beskyttet mot endring ennå.
