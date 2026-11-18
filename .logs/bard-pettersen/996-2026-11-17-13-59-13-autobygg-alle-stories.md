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

## Story 1.9: Ordrer, beslutningslogg og ny uke (2026-11-17)

### Oppgave
Bygge Story 1.9 på `epic-1`.

### Plan
`bmad-build-auto` i én underagent, med implementering i egen kontekst og gjennomgang i underagenter.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-1-9-place-orders-decision-log-advance-week.md`. Commit `e364bf2`.
- `games.commands.place_order` i én transaksjon, med én rad i beslutningsloggen (`seat_weeks`) som databasen nekter å endre, og ny uke eller `finish` i samme transaksjon. Nye kommandoer: `sim play` og `sim log`.
- 989 tester grønne, full grenddekning av motoren, ruff ren. En ekte kjøring ga 144 loggrader, og alle kostnader stemte med `sim trace --orders rule_based`.
- Gjennomgang: 23 funn. `sim play` kunne gå i evig løkke og er rettet, og det er lagt til en test for en halvspilt uke.
- Status: `done`.

### Åpne punkter
- Issue #45: beslutninger om ordrer, feilkoder og uforanderlige rader.
- Issue #44: spillet stopper i uke 1 når den veiledede ordren er høyere enn største ordre.

## Story 1.10: Verifisere hvert ferdig spill ved avspilling (2026-11-17)

### Oppgave
Bygge Story 1.10 på `epic-1`.

### Plan
`bmad-build-auto` i én underagent, med implementering i egen kontekst og gjennomgang i underagenter.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-1-10-verify-finished-game-by-replaying.md`. Commit `2e6bed8`.
- Regelversjoner som pakker (`engine/rules/v1/`), `engine.replay`, `games.service.verify_finished` med en uforanderlig rad i `game_checks` (Alembic `0005`), og `sim check <id>`. `sim play` sjekker etter siste uke.
- 1041 tester grønne, full grenddekning av motoren, ruff ren. Et klassisk spill med frø 7 er spilt og sjekket to ganger: `check ok`.
- Gjennomgang: 29 funn, 5 lave rettet, 24 avvist.
- Status: `done`.

### Åpne punkter
- Issue #46: beslutninger om regelversjoner og sjekkraden.

## Story 1.11: Batcher av rene AI-spill med skriptede spillere (2026-11-17)

### Oppgave
Bygge Story 1.11 på `epic-1`.

### Plan
`bmad-build-auto` i én underagent, med implementering i egen kontekst og gjennomgang i underagenter.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-1-11-run-batches-of-all-ai-games.md`. Commit `863cabb`.
- `python -m app.sim run <batch.json> [--export DIR]` oppretter, starter, spiller og sjekker hvert spill gjennom `games.commands`, og skriver sammendrag per spill og batch. Ny `games.service.game_summary`, ny policy `order-incoming`, CSV-eksport av beslutningsloggen, og en røyktest-batch i CI.
- 1082 tester grønne, full grenddekning av motoren, ruff ren. Røyktesten ga 3/3 sjekker ok.
- Gjennomgang: 34 funn, ingen høye eller middels, 10 lave rettet.
- Underagenten fant at `sim check --all` fra Story 1.10 manglet. Det bygges som egen retting.
- Status: `done`.

### Åpne punkter
- Issue #47: beslutninger om batchformat, frø, utkoder og eksport.

## Retting: `sim check --all` fra Story 1.10 (2026-11-17)

### Oppgave
Akseptansekravet `python -m app.sim check --all` fra Story 1.10 manglet i koden.

### Plan
Én underagent bygger det med gjenbruk av `verify_finished`.

### Resultat
- Commit `711eac8`. `check --all` sjekker alle ferdige spill (eldste først), lister bare feilede, og avslutter med `checked N ok=X failed=Y`. Utkoder 0, 1 og 2. Spill uten regelpakke teller som feilet.
- 1088 tester grønne, ruff ren. Merknad lagt til i specen for 1.10.

### Åpne punkter
- Issue #47 nevner funnet.

## Story 1.12: Fraktkapasitet per plass (2026-11-17)

### Oppgave
Bygge Story 1.12 på `epic-1`, den siste i Epic 1. Underveis valgte brukeren OpenRouter med modellen `deepseek/deepseek-v4.1-flash-1017`.

### Plan
`bmad-build-auto` i én underagent. Modellvalget føres i Issue #9, i spinen og i kjøreboka etter at storyen er committet.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-1-12-cap-what-a-seat-can-ship-per-week.md`. Commit `8f2f18d`.
- Valgfri `capacity` per rolle i `GameSettings`, regler v1 sender det minste av lager, skyld og kapasitet, bevaringssjekken tar med kapasiteten, `validate` avviser kapasitet når `FEATURE_CAPACITY` er av, og ny advarsel `capacity_below_peak_demand`.
- 1132 tester grønne, full grenddekning av motoren, ruff ren, røyktesten 3/3. Golden-sporet `capped-retailer-6` er sjekket uavhengig med 0 avvik.
- Modellvalget står i Issue #9, i spinen (åpent valg om LLM-leverandør) og i kjøreboka.
- Status: `done`.

### Åpne punkter
- Issue #48: beslutninger om kapasitet og funksjonsflagget.
- Issue #9: modellen må verifiseres mot OpenRouter og EU-ruting i Story 2.7.

## Story 2.1: Én ordrekilde for alle plasser som ikke er studenter (2026-11-18)

### Oppgave
Bygge Story 2.1 på `epic-2`, etter at Epic 1 er merget (PR #49). Underveis ba brukeren om at testene må være raske.

### Plan
`bmad-build-auto` i én underagent. Regelen om raske tester ble sendt til agenten underveis, lagt i minnet og i malen for senere stories.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-2-1-one-order-source-for-non-student-seats.md`. Commit `5a63c8d`.
- `players.ensure_order` legger alle veiledede, regelbaserte og skriptede ordrer i samme transaksjon som åpner uka. Nye kommandoer `advance` og `switch_to_rule_based`. `sim` har ikke lenger egen ordreløkke.
- Hele pakken: 1153 grønne, én feilet test ble rettet og kjørt på nytt for seg (22 grønne). Røyktesten 3/3. Golden-batchene gir samme ordrer og kostnader som før.
- Trege tester: hele spill tar 6–7 s hver, batchtestene i `test_sim.py` 13–39 s.
- Gjennomgang: 34 funn, 6 rettet, 1 utsatt (historikken leses på nytt per plass).
- Status: `done`.

### Åpne punkter
- Issue #50: beslutninger om ordrekilden og det utsatte ytelsesfunnet.

## Raskere testpakke (2026-11-18)

### Oppgave
Brukeren ba om raske tester. Backend-pakken tok 618 s lokalt og 4–5 min i CI.

### Plan
Én underagent måler med `--durations` og retter årsakene uten å svekke det testene beviser.

### Resultat
- Commit `825b071` (egen logg i `75fdf7d`). Hele pakken: 42 s lokalt (1154 grønne), full grenddekning av motoren beholdt.
- Produksjonsretting: ordrekilden gjenbruker historikken i stedet for å lese den per plass, og turer settes inn med én INSERT. Et spill på 36 uker gikk fra 6,4 til 3,2 s.
- Testoppsett: migrering én gang per sesjon, `pytest-xdist==3.8.0` med én database per arbeider, delte ferdigspilte spill, raskere `drain()`.
- Regelen står i minnet, i kjøreboka og i malen for byggeagentene.

### Åpne punkter
- Issue #50: neste steg er færre lesinger per plass i `place_order(within=…)`.

## Story 2.2: Modellkonfig og evalueringsbudsjett fra kommandolinja (2026-11-18)

### Oppgave
Bygge Story 2.2 på `epic-2`.

### Plan
`bmad-build-auto` i én underagent, med regelen om raske tester.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-2-2-register-model-config-and-evaluation-budget.md`. Commit `6693c8e`.
- Migrering `0006` med `ai_model_configs` og `ai_budgets`, modulene `ai.config` og `ai.budget`, `python -m app.ai.cli` (`config add|edit|list|show`, `budget set`) og to eksempelkonfiger i `backend/ai-configs/`.
- Hele pakken: 1223 grønne på 46 s, full grenddekning av motoren, ruff ren. Én ny test tar 1,3 s fordi den starter en egen prosess.
- Gjennomgang: 43 funn (3 middels). Hovedrettingen avviser hemmeligheter skrevet inn i endepunkt-URL-en. Ett middels funn er utsatt.
- Status: `done`.

### Åpne punkter
- Issue #51: beslutninger om konfigformat, hemmeligheter, plassholderpriser og budsjett, og det utsatte funnet om validering av gamle rader.

## Story 2.3: Validert LLM-kall gjennom gatewayen (2026-11-18)

### Oppgave
Bygge Story 2.3 på `epic-2`. Før storyen: rette CI, som feilet etter fartsjobben.

### Plan
- CI-feilen: xdist-arbeiderne arvet en omskrevet `DATABASE_URL` og koblet til en testdatabase som ikke finnes i en tom CI-database. Original-URL-en holdes nå i `OLSPILLET_BASE_DATABASE_URL`, og databaser opprettes fra `postgres`. Prøvd lokalt mot en ikke-eksisterende basedatabase.
- `bmad-build-auto` i én underagent.

### Resultat
- CI-rettingen: commit på `epic-2`. CI grønn igjen, 1 min 18 s per kjøring (mot rundt 5 min før).
- Spec: `.docs/implementation-artifacts/spec-2-3-validated-llm-call-through-gateway.md`. Commit `529c0b6`.
- `app.ai.gateway.run(...)`, tabellen `llm_call` (migrering 0007), vasking av personopplysninger med tilbakeoversetting, deterministisk mock-leverandør, hash-lås på promptfiler (`prompts check|lock`) og en importsjekk som holder leverandør-SDK-er inne i `app/ai`.
- Hele pakken: 1251 grønne på 63 s, full grenddekning av motoren, ruff ren.
- Gjennomgang: 51 funn, 17 rettet, 1 utsatt.
- Migrering 0007 ble endret etter at de delte testdatabasene var migrert, så jeg slettet `olspillet_test*` etterpå, og de bygges på nytt.
- Status: `done`.

### Åpne punkter
- Issue #52: beslutninger om gatewayen, det utsatte funnet om avbrutte kall og anbefalt oppfølgende gjennomgang.

## Story 2.4: LLM-spiller som bestiller fra plassens tilstand (2026-11-18)

### Oppgave
Bygge Story 2.4 på `epic-2`.

### Plan
`bmad-build-auto` i én underagent, med regelen om raske tester.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-2-4-ask-llm-player-for-order-from-seat-state.md`. Commit `74f2201`.
- `backend/app/modules/players/llm.py` bygger promptverdier bare fra `SeatState`, med streng ordreskjema. Promptene `player_order/v1.md` og `recognition_probe/v1.md` er låst. `gateway.preview` viser nøyaktig forespørsel uten modellkall. Nye kommandoer `sim prompt` og `sim probe`.
- Hele pakken: 1271 grønne på 49 s, full grenddekning av motoren. Fire nye prøvetester tar 1,5–2,2 s hver.
- Gjennomgang: 40 funn. Rettet blant annet krasj i `sim prompt` ved store bokstaver, tapte svar i prøven og to ulike svarformater.
- Oppfølgende gjennomgang anbefalt (også for 1.7 og 2.3). Den samles ved slutten av Epic 2.
- Status: `done`.

### Åpne punkter
- Issue #53: beslutninger om prompten og gjenkjenningsprøven.

## Story 2.5: LLM-ordrer som jobber med regelbasert fallback (2026-11-18)

### Oppgave
Bygge Story 2.5 på `epic-2`.

### Plan
`bmad-build-auto` i én underagent, med regelen om raske tester og at jobbtester ikke venter på klokka.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-2-5-place-llm-orders-as-jobs-rule-based-fallback.md`. Commit `e73998b`.
- LLM-spillere får ordrene sine fra `ai-orders`-jobber (procrastinate 3.11.0, skjema i Alembic 0008). Feiler modellen, legger jobben inn den regelbaserte referanseordren, merket med feiltype og kall-id-er. Compose har nå `worker-ai` og `worker-batch`.
- Hele pakken: 1307 grønne på 55 s, full grenddekning av motoren, golden-resultater uendret. `worker-ai` spilte et mock-LLM-spill på 36 uker i compose, og sjekken bestod.
- Gjennomgang: 38 funn, de middels rettet (en jobb kunne stoppe et spill, feiltyper uten test, skjemaavvik). Ett utsatt.
- Status: `done`.

### Åpne punkter
- Issue #54: beslutninger om jobbene og fallback, det utsatte funnet om databasefeil og anbefalt oppfølgende gjennomgang.

## Story 2.6: Hver LLM-ordre innenfor tidsbudsjettet (2026-11-18)

### Oppgave
Bygge Story 2.6 på `epic-2`, og løse de utsatte funnene i Issue #52 og #54.

### Plan
`bmad-build-auto` i én underagent, med injisert klokke i stedet for ekte ventetid i testene.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-2-6-keep-llm-orders-inside-time-budget.md`. Commit `a6f8247`.
- Hver `llm`-tur lagrer `ai_deadline_at` (ren funksjon `games.rules.turn_times`). Jobben stopper modellkallet ved fristen. `worker-ai` kjører en redningsløkke hvert 5. s som legger inn `timeout`-fallback og åpner neste uke.
- Issue #52: avbrutt forsøk logges som `cancelled`. Issue #54: databasefeil prøves på nytt to ganger, så tar løkka over.
- Hele pakken: 1335 grønne på rundt 50 s, full grenddekning av motoren. Håndsjekk i Docker: løkka la inn 4 fallbacks etter fristen. Åtte tester i `test_rescue.py` tar 1–2,5 s.
- Gjennomgang: 36 funn, 9 rettet. Alvorligst: Postgres-klokka gikk 96 s foran verten, så fristene regnes nå på databaseklokka.
- Status: `done`.

### Åpne punkter
- Issue #55: beslutninger om frister, nye forsøk og redningsløkka.

## Story 2.7: Ekte EU-endepunkt innenfor ratebegrensningen (2026-11-18)

### Oppgave
Bygge Story 2.7 på `epic-2` mot OpenRouter med `deepseek/deepseek-v4.1-flash-1017`, og kjøre en prøve mot det ekte endepunktet.

### Plan
- Første forsøk ga agenten lov til å bruke nøkkelen i `.env`. Det automatiske sikkerhetsfilteret stoppet det (`Unauthorized Access`), og det ble ikke prøvd å omgå det.
- Andre forsøk: bygge og teste alt mot mocken og en falsk HTTP-transport, lese OpenRouters offentlige modelliste uten nøkkel, og lage en prøvekommando grunnleggeren kan kjøre.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-2-7-call-real-eu-endpoint-within-rate-limit.md`. Commit `539afb2`.
- OpenAI-kompatibel adapter med OpenRouter-ruting (ingen fallback, ZDR, nektet datainnsamling) i modellkonfigen, ratebegrenser, 429-ventetid, og `python -m app.sim endpoint --config <ID>`.
- Modellen finnes (50 endepunkter, 43 ZDR). Region per endepunkt er ikke offentlig. Konfigen låser til Nebius.
- Hele pakken: 1371 grønne på rundt 55 s, full grenddekning av motoren.
- Gjennomgang: 43 funn, 18 rettet, 2 utsatt.
- Status: `review`. Prøven med ekte kall venter på grunnleggeren.

### Åpne punkter
- Issue #56: kjør prøven med nøkkelen, bekreft at Nebius kjører modellen i EU, og to utsatte funn.

## Story 2.8: Budsjettreservasjon per kall og bytte ved kostnadsgrensen (2026-11-18)

### Oppgave
Bygge Story 2.8 på `epic-2`.

### Plan
`bmad-build-auto` i én underagent, uten ekte nøkler.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-2-8-reserve-budget-per-call-switch-at-cost-limit.md`. Commit `7ed4021`.
- Gatewayen reserverer verste kostnad før hvert forsøk med én betinget `UPDATE`, og gjør opp i samme transaksjon som `llm_call`-raden. LLM-spillere kan bruke budsjettet opp til `limit − reserve`. Ved grensen legger jobben inn regelbasert ordre (`budget_exhausted`), og alle LLM-plasser på budsjettet byttes til regelbaserte (`cost_limit`). Migrering 0011 og `python -m app.ai.cli cost --scope`.
- Hele pakken: 1387 grønne på 57 s, full grenddekning, golden-resultater uendret. To eldre tidstester feilet én gang og bestod så fem ganger.
- Gjennomgang: 34 funn, 3 middels og 4 lave rettet, 1 utsatt.
- Status: `done`.

### Åpne punkter
- Issue #57: beslutninger om reservasjon og kostnadsgrense, og mulig ustabile tidstester.

## Story 2.9: Nær-optimal referanseordre for hver plass og uke (2026-11-18)

### Oppgave
Bygge Story 2.9 på `epic-2`.

### Plan
`bmad-build-auto` i én underagent. Golden-verdiene sjekkes av en uavhengig agent i stedet for grunnleggeren.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-2-9-store-near-optimal-reference-order.md`. Commit `3660e00`.
- Ren funksjon `engine.near_optimal.order(...)` (`placeholder-0`). Referansen regnes én gang per plass når uka åpner og lagres på turen. `place_order` kopierer den til beslutningsloggen. Migrering 0012 med trigger mot endring.
- Hele pakken: 1415 grønne på 60 s, full grenddekning, golden-resultater uendret. To nye tester over 1 s (3,6 s og 1,0 s).
- Uavhengig sjekk: alle 36 uker stemte.
- Gjennomgang: 26 funn, 2 middels og flere lave rettet, ingenting utsatt.
- Status: `done`.

### Åpne punkter
- Issue #58: plassholderalgoritmen må erstattes, og hvordan verdiene lagres.

## Story 2.10: Spillvakten bytter en LLM-plass som driver ut (2026-11-18)

### Oppgave
Bygge Story 2.10 på `epic-2`.

### Plan
`bmad-build-auto` i én underagent, med navngitte plassholdere for de åpne valgene i Issue #20. Agenten brukte lang tid på å lese inn bakgrunnen og fikk en statusforespørsel underveis. Den sto ikke fast.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-2-10-play-guard-switch-drifting-llm-seat.md`. Commit `b6f1fbd`.
- `place_order` kjører spillvakten (`backend/app/analysis/play_guard.py`) på hver LLM-ordre. Går plassen ut av båndet, legges det til en rad (`rule_based`, `guard_switch`) fra neste uke, og plassen er regelbasert resten av spillet. Ingen migrering.
- Hele pakken: 1449 grønne på 60 s, full dekning av motor og analyse, golden-resultater uendret. Seks nye tester tar 1,3–2,7 s.
- Gjennomgang: 26 funn, 1 middels og 4 lave rettet.
- Status: `done`.

### Åpne punkter
- Issue #59: plassholdere for spillvakten, og at vakten kan bytte ut en spiller som spiller nær optimalt.
- Issue #20: kalibrering av spillvakten.

## Story 2.11: Måle modell og effort-nivå på simulerte batcher (2026-11-18)

### Oppgave
Bygge Story 2.11 på `epic-2`. Storyen skal måle den valgte modellen på ekte kall.

### Plan
`bmad-build-auto` i én underagent, uten nøkkel: alt bygges og testes mot mocken, og kommandoer og kostnadsanslag for den ekte målingen skrives ned.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-2-11-measure-model-effort-level-on-sim-batches.md`. Commit `ac74190`.
- `sim run` lagrer hver batch (migrering 0013: `simulation_batches`, `games.batch_id`, `seat_weeks.effort_level`), og `sim report <id>` skriver alle tallene storyen ber om. Ny CI-sjekk `backend/scripts/sim-llm-smoke.sh` med ekte `worker-ai` og mock.
- Hele pakken: 1484 grønne på 61 s, full grenddekning, golden-resultater uendret. Fire nye tester tar 1,2–5,2 s i full kjøring.
- Gjennomgang: 31 funn, 11 rettet.
- Status: `review`. Den ekte målingen venter på grunnleggeren.

### Åpne punkter
- Issue #60: kjør målingen med nøkkelen, kostnadsanslag og beslutninger.

## Story 2.12: Bare målte effort-nivåer, og låst modell (2026-11-18)

### Oppgave
Bygge Story 2.12 på `epic-2`, uten at noen ekte måling er kjørt (Issue #56 og #60).

### Plan
`bmad-build-auto` i én underagent. Mock-batcher skal aldri telle som ekte måling i produksjon.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-2-12-offer-measured-effort-levels-pin-model.md`. Commit `72bbba4`.
- `python -m app.sim approve <batch> --level <navn>` lagrer en måling bare for en ekte batch som besto alle tre grensene. `ai.config.offered_effort_levels` lister bare målte nivåer. `ai.cli pin` setter standardkonfig. Migrering 0014.
- I produksjon tilbys ingen nivåer før en ekte måling er godkjent. Lokalt og i CI tilbyr en seedet mock-konfig `standard`.
- Hele pakken: 1523 grønne på 65 s, full grenddekning, golden-resultater uendret.
- Gjennomgang: 31 funn, 12 rettet, 1 utsatt (mock-flagget per batch).
- Status: `done`.

### Åpne punkter
- Issue #61: beslutninger om godkjenning, låsing og seeding, og det utsatte funnet om mock-flagget.

## Story 2.13: Beskrive hver AI-spillertype på enkelt norsk (2026-11-18)

### Oppgave
Bygge Story 2.13 på `epic-2`, den siste i Epic 2.

### Plan
`bmad-build-auto` i én underagent. Norsken sjekkes av uavhengige språkagenter i stedet for grunnleggeren. Agenten sto lenge på steg 1 (ventet på en mappeliste) og fikk en statusforespørsel.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-2-13-describe-ai-player-types-plain-norwegian.md`. Commit `cd9cc1a`.
- To norske tekster (regelbasert og LLM), `players.service.describe(kind, version=None)` og `python -m app.sim describe`. 24 nye tester binder tekstene til koden.
- Gjennomgang: fire kodegjennomgåere og to språkgjennomgåere, 53 funn, 36 rettet.
- Hele pakken: 1538 grønne på 59 s før rettingene. Etter rettingene feilet 2 tester i hver av tre fulle kjøringer, fra tre tidsavhengige tester i `test_llm_jobs.py`, `test_sim_llm.py` og `test_rescue.py`, under last fra andre prosesser. De rettes før PR-en for Epic 2.
- Status: `done`.

### Åpne punkter
- Issue #62: beslutninger om tekstene og versjonering.

## Deterministiske tidstester (2026-11-18)

### Oppgave
Seks tidsavhengige tester feilet av og til under last (sett i Story 2.8 og 2.13).

### Plan
Én underagent finner årsakene og gjør testene deterministiske uten å svekke påstandene.

### Resultat
- Commit `ccd2f5b`, bare tester. Stoppede klokker i stedet for ekte frister, hendelser i stedet for faste `sleep`, og et sjenerøst standard tidsbudsjett der fristen ikke er det som testes.
- Verifisert: fire filer 20 ganger med `-n 16`, fire av dem med full CPU-last, og hele pakken tre ganger (1547 grønne).
- Årsak: klokka i den lokale Docker-Postgres er ustabil.

### Åpne punkter
- Issue #63: ustabil klokke i lokal Docker-Postgres.

## Oppfølgende gjennomgang av Epic 1–2 (2026-11-18)

### Oppgave
Lese rettingene som kom etter gjennomgangen i Story 1.2, 1.7, 2.3–2.8 og 2.11–2.13.

### Plan
Én uavhengig agent fikk specene og koden, ikke konklusjonene.

### Resultat
- Commit `74205cc`. To feil rettet: fallback når budsjettomfanget ikke kan leses (2.5), og lesetiden for fristen (2.6). Ny test for Story 2.5 der `place_order` avviser en modellordre.
- Hele pakken: 1550 grønne på 61 s, ruff ren.

### Åpne punkter
- Issue #64: tre tvilsomme funn.

## Story 3.1: «Logg inn» i produktets design (2026-11-18)

### Oppgave
Bygge Story 3.1 på `epic-3`, den første storyen med en skjerm, og kontrollere den visuelt.

### Plan
- `bmad-build-auto` i én underagent.
- Visuell kontroll i en egen underagent: compose, Playwright, skjermbilder i 390 og 1280 px, sammenlignet med mockup, DESIGN.md og EXPERIENCE.md.
- Rette en ustabil tidstest (Issue #63).

### Resultat
- Spec: `.docs/implementation-artifacts/spec-3-1-see-logg-inn-in-product-design.md`. Commit `11423a7`.
- Tokens fra DESIGN.md, selvhostet Source Sans 3, felles knapp, lenke og tekstfelt, all tekst i `nb.ts`, tekst- og fargesjekk i bygget. `/logg-inn` sjekker feltene i nettleseren. Vitest og Playwright med axe, og ny e2e-jobb i CI.
- Frontend: typecheck, Vitest (181), tekstsjekk, bygg og Playwright (7) grønne.
- Tidstesten `test_the_turns_read_time_is_when_the_read_ended` tåler nå treg Docker-klokke (commit `90072cd`).
- Visuell kontroll: 11 skjermbilder i `.docs/implementation-artifacts/screenshots/3.1/`, ingen klare avvik, fire punkter til vurdering. Passordet havner ikke i URL-en.
- Status: `done`.

### Åpne punkter
- Issue #67: beslutninger og utsatte funn.
- Issue #66: visuelle avvik til vurdering.

## Story 3.2: Logge inn og ut med e-post og passord (2026-11-18)

### Oppgave
Bygge Story 3.2 på `epic-3` og kontrollere den visuelt.

### Plan
`bmad-build-auto` i én underagent, med testbrukere per rolle til senere tester. Deretter visuell kontroll i en egen underagent.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-3-2-log-in-and-log-out-email-password.md`. Commit `1d6ad4a`. Migrering 0015.
- Backend: 1599 grønne på 67 s. Frontend: typecheck, Vitest (197), tekstsjekk og bygg grønne. Playwright: 15 grønne.
- Gjennomgang: 41 funn, 13 rettet (blant annet et kappløp som slapp parallelle gjetninger forbi grensen), 2 utsatt til Story 3.14.
- Visuell kontroll: 10 skjermbilder i `.docs/implementation-artifacts/screenshots/3.2/`, alle stemmer, ingen rettinger.
- Status: `done`.

### Åpne punkter
- Issue #69: beslutninger om økt, grenser, tekst og testinnlogging.
- Issue #68: produktnavnet flytter seg mellom sidene.

## Story 3.3: Egen hjemside og rollestyring (2026-11-18)

### Oppgave
Bygge Story 3.3 på `epic-3` og kontrollere den visuelt. Løse Issue #68 (produktnavnet flytter seg).

### Plan
`bmad-build-auto` i én underagent, og visuell kontroll i en egen underagent.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-3-3-land-on-own-home-held-to-role.md`. Commit `76f7c76`.
- `platform/authz` med `can(user, action, resource)`, en policy på hver API-rute, roller lest fra databasen ved hver forespørsel, og 403 `forbidden` uansett om tingen finnes. Hjemsidene `/admin`, `/laererhjem` og `/hjem` har felles toppfelt. Det finnes også en side for manglende tilgang, en side for ukjent adresse og en brødsmulesti.
- Retting fra 3.2: deadlock ved parallelle innlogginger.
- Backend: 1629 grønne på 69 s. Frontend: typecheck, Vitest (206), tekstsjekk og bygg grønne. Playwright: 35 grønne.
- Visuell kontroll: 20 skjermbilder i `.docs/implementation-artifacts/screenshots/3.3/`, alle stemmer. Issue #68 er løst.
- Status: `done`.

### Åpne punkter
- Issue #70: beslutninger, og stilen på toppfeltet til vurdering.

## Story 3.4: Lasting, feil og frakoblet (2026-11-18)

### Oppgave
Bygge Story 3.4 på `epic-3` og kontrollere den visuelt.

### Plan
`bmad-build-auto` i én underagent, og så visuell kontroll i en egen underagent. Byggeagenten brukte over en time på steg 1 og fikk en statusforespørsel. Malen for byggeagenter sier nå at steg 1 skal ta rundt 10 minutter.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-3-4-see-loading-failure-offline-states.md`. Commit `c563eb4`, visuell retting `8a99c63`.
- Plassholder ved lasting («Laster …» etter 1 s, feil etter 10 s), tilkoblingslinje (frakoblet, feil, «Tilkoblet igjen.»), felles hjelper for handlinger (aldri sendt på nytt av seg selv), utløpt økt med retur til samme side, og redusert bevegelse.
- Backend: 1629 grønne på 61 s. Frontend: typecheck, Vitest (239), tekstsjekk og bygg grønne. Playwright: 53 grønne.
- Gjennomgang: 33 funn, 2 middels og 9 lave rettet.
- Visuell kontroll: 18 skjermbilder, én retting (feillinja for «Logg ut» brøt toppfeltet på 390 px), to punkter til vurdering.
- Status: `done`.

### Åpne punkter
- Issue #71: beslutninger, visuelle avvik og anbefalt oppfølgende gjennomgang.

## Story 3.5: All e-post gjennom én kanal (2026-11-18)

### Oppgave
Bygge Story 3.5 på `epic-3`.

### Plan
`bmad-build-auto` i én underagent. Bare mock-e-post, og leverandøren bak en adapter (Issue #29). Ingen endring under `frontend/`, så ingen visuell kontroll.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-3-5-send-every-mail-through-one-pipeline.md`. Commit `d0294bb`. Migrering 0016.
- `platform/notify` (tabellen `notices`, `enqueue`), `platform/email` (Jinja2-maler, `Sender`-adapter, Resend eller `[email:mock]`), `modules/messaging` (leveranser, kø, nye forsøk, regler for samlemeldinger, `send-test`) og `modules/ops` (`ops.sweep` i `worker-batch --sweeper`).
- Backend: 1688 grønne på 63 s, ingen ny test over 1 s. I compose kom en umiddelbar e-post som én `[email:mock]`-linje på rundt 1 s, og en samlemelding ved neste sveip.
- Gjennomgang: 34 funn, 3 reelle feil rettet.
- Status: `done`.

### Åpne punkter
- Issue #72: beslutninger om e-postkanalen, og at Story 3.6 trenger malvariabler.

## Story 3.6: Tilbakestille glemt passord på e-post (2026-11-18)

### Oppgave
Bygge Story 3.6 på `epic-3` og kontrollere den visuelt. Rette en kjent feil på `/logg-inn`: knappen flytter seg når en feilmelding forsvinner.

### Plan
`bmad-build-auto` i én underagent, deretter visuell kontroll i en egen underagent som også retter feilen på `/logg-inn`.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-3-6-reset-forgotten-password-by-email.md`. Commit `a5ef6de`, visuelle rettinger `7b9a5d3`. Migrering 0017.
- Tre offentlige endepunkter for tilbakestilling, malvariabler i e-post til brukere, sidene `/glemt-passord` og `/nytt-passord`, og et lokalt testendepunkt for postkassen.
- Backend: 1706 grønne på 72 s. Frontend: typecheck, Vitest (250), tekstsjekk og bygg grønne. Playwright: 59 grønne. Tre nye flyttester tar 4–10 s hver, fordi de sender ekte mock-e-post gjennom arbeideren.
- Gjennomgang: 49 funn. Rettet blant annet at bcrypt kjørte før token-sjekken, og at to lenker for samme bruker kunne bekreftes samtidig.
- Visuell kontroll: 18 skjermbilder, to rettinger, tre punkter til vurdering.
- Status: `done`.

### Åpne punkter
- Issue #73: beslutninger, sikkerhetsrisikoen (andre økter logges ikke ut) og visuelle avvik.

## Story 3.7: Invitere faglærer eller Admin på e-post (2026-11-18)

### Oppgave
Bygge Story 3.7 på `epic-3` og kontrollere den visuelt.

### Plan
`bmad-build-auto` i én underagent, og visuell kontroll i en egen underagent. Byggeagenten skulle ha én ende-til-ende-test for e-post og teste resten på API-nivå.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-3-7-invite-lecturer-or-admin-by-email.md`. Commit `89f19e5`, visuell retting `d0dc5ce`. Migrering 0018.
- Tabellen `invitations` (bare hashen lagres), `POST /api/admin/invitations` for Admin, ny `platform/audit` med `audit_events`, e-posten «Invitasjon til ØL-spillet» og siden `/admin/brukere`.
- Backend: 1734 grønne på 72 s. Frontend: Vitest 255, typecheck, tekstsjekk, fargesjekk og bygg grønne. Playwright: 67 grønne. Bare én ny test venter på ekte e-post.
- Gjennomgang: 38 funn, ingen høye eller middels, 5 lave rettet.
- Visuell kontroll: 14 skjermbilder og e-postteksten. Én retting. Den utdaterte resultatlinja rettes i Story 3.8.
- Status: `done`.

### Åpne punkter
- Issue #74: beslutninger og visuelle avvik.
