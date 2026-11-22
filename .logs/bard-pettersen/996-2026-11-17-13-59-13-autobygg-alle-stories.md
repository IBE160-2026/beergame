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

## Story 3.8: Opprette konto fra en invitasjon (2026-11-18)

### Oppgave
Bygge Story 3.8 på `epic-3`, rette Issue #74 og kontrollere siden visuelt. Brukeren ba om å stoppe etter Epic 4, for å kjøre compact.

### Plan
`bmad-build-auto` i én underagent. Agenten ble avbrutt før gjennomgangen var ferdig, og fullførte etter å ha blitt sendt tilbake. Deretter visuell kontroll i en egen underagent.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-3-8-create-account-from-invitation.md`. Commit `405e8d0` (story), `9b9b247` (rettinger fra gjennomgangen) og `5a411c6` (visuell retting). Migrering 0019.
- Fire offentlige ruter for invitasjoner (sjekk, aksept, aksept med innlogging, fornyelse), grenser for forespørsler, første Admin fra `BOOTSTRAP_ADMIN_EMAILS` i produksjon, og siden `/invitasjon` med tre tilstander.
- Backend: 1763 grønne på 63–68 s. Frontend: typecheck, Vitest (261), tekstsjekk, fargesjekk og bygg grønne. Playwright: 74 grønne.
- Gjennomgang: 42 lave funn, de reelle rettet. En ustabil test for parallell aksept er rettet.
- Visuell kontroll: 24 skjermbilder, én retting, og to punkter til vurdering.
- Status: `done`.

### Åpne punkter
- Issue #75: beslutninger, passordlengde og lange adresser.
- Issue #74 er løst.

## Story 3.9: Finne brukere og gi eller fjerne roller (2026-11-18)

### Oppgave
Bygge Story 3.9 på `epic-3`, heve de lokale invitasjonsgrensene og kontrollere siden visuelt.

### Plan
`bmad-build-auto` i én underagent. Agenten måtte gi fra seg kontrollen før gjennomgangen var ferdig, og fullførte etter at den ble sendt tilbake. Deretter visuell kontroll i en egen underagent.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-3-9-find-users-grant-revoke-roles.md`. Commit `ad3624b` (lokale grenser), `efafe22` (story) og `5e09d6f` (visuelle rettinger).
- `GET /api/admin/users` med søk og peker, og tildeling og tilbaketrekking av roller med revisjonsrad og hendelse. `409 last_admin` under lås og et register for blokkeringer (`409 role_revoke_blocked`). Søk og brukertabell på `/admin/brukere`, med blokker med etiketter under rundt 60em.
- Backend: 1794 grønne på 69 s. Frontend: typecheck, Vitest (267), tekstsjekk, fargesjekk og bygg grønne. Playwright: 83 grønne.
- Gjennomgang: 44 funn (4 middels), alle de middels rettet.
- Visuell kontroll: 30 skjermbilder, to rettinger, to punkter til vurdering.
- Status: `done`.

### Åpne punkter
- Issue #76: beslutninger, låsen Story 3.10 må bruke, og visuelle avvik.

## Story 3.10: Deaktivere og reaktivere brukere og sende invitasjoner på nytt (2026-11-18)

### Oppgave
Bygge Story 3.10 på `epic-3`: dekke regelen om siste Admin ved deaktivering, vurdere Issue #73, og kontrollere sidene visuelt.

### Plan
`bmad-build-auto` i én underagent, med låsen og Issue #73 i oppdraget. Etterpå en visuell kontroll i en egen underagent.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-3-10-deactivate-reactivate-users-resend-invitations.md`. Commit `7ecc156`, visuelle rettinger `c329108`. Migrering 0020.
- Deaktivering og reaktivering, invitasjonsliste med status og «Send på nytt». Låsen for siste Admin, og øktversjon per bruker.
- Issue #73 er løst: en tilbakestilling avslutter alle andre økter.
- Backend: 1815 grønne på 68 s. Frontend: typecheck, Vitest (277), tekstsjekk og bygg grønne. Playwright: 89/89 før rettingene etter gjennomgangen. Etterpå feilet én av to `system-states`-tester av og til.
- Gjennomgang: 28 funn (4 middels), 3 middels og 9 lave rettet, 1 utsatt.
- Visuell kontroll: 26 skjermbilder og to rettinger. Fire punkter går til den samlede gjennomgangen.
- Status: `done`.

### Åpne punkter
- Issue #77: beslutninger, visuelle avvik og ustabile e2e-tester.
- Issue #73 er lukket.

## Story 3.11: Opprette institusjoner (2026-11-18)

### Oppgave
Bygge Story 3.11 på `epic-3` og kontrollere den visuelt.

### Plan
`bmad-build-auto` i én underagent, og så visuell kontroll i en egen underagent med en forfalsket, realistisk liste.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-3-11-create-institutions.md`. Commit `8b7650e`, visuell retting `75733f7`. Migrering 0021.
- Tabellen `institutions` og tre Admin-ruter (liste, opprett, gi nytt navn) med revisjonsrad. `service.list_institutions()` og `get_institution(id)`. Siden `/admin/institusjoner`.
- Backend: 1837 grønne på 71 s. Frontend: typecheck, Vitest (288), sjekkene og bygget er grønne. Playwright: 95 av 96. Ustabile tester: offline-testen i `system-states.spec.ts` og `test_rescue.py`.
- Gjennomgang: 33 funn. Ett middels rettet («İzmir» ga 500).
- Visuell kontroll: 24 skjermbilder, én retting, to punkter til vurdering.
- Status: `done`.

### Åpne punkter
- Issue #78: beslutninger om institusjoner og visuelle avvik.

## Story 3.12: Lese revisjonsloggen (2026-11-18)

### Oppgave
Bygge Story 3.12 på `epic-3` og kontrollere den visuelt.

### Plan
`bmad-build-auto` i én underagent. Deretter visuell kontroll i en egen underagent, med en forfalsket logg som dekker alle handlingene.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-3-12-read-audit-log.md`. Commit `85dc7f0`, visuell retting `69f85b4`.
- Filtrert lesing i `platform/audit`, ny `modules/admin` med `GET /api/admin/audit` og `/actors` (bare Admin), og siden `/admin/revisjonslogg` med fire filtre.
- En API-test sjekker at hver Admin-handling i Epic 3 gir nøyaktig én rad.
- Backend: 1859 grønne på 71 s. Frontend: typecheck, Vitest (295), sjekker og bygg grønne. Playwright: 102 av 104. De to feilene var den kjente ustabile `system-states`-testen.
- Gjennomgang: 33 lave funn, 6 rettet.
- Visuell kontroll: 26 skjermbilder, én retting og to punkter til vurdering.
- Status: `done`.

### Åpne punkter
- Issue #79: beslutninger om revisjonsloggen, datoformat og visuelle avvik.

## Story 3.13: Forsiden og forespørsel om faglærertilgang (2026-11-18)

### Oppgave
Bygge Story 3.13 på `epic-3` og kontrollere forsiden visuelt mot mockupen.

### Plan
`bmad-build-auto` i én underagent, med beskjed om at designet skal være datasentrisk og uten metaforer. Deretter en visuell kontroll i en egen underagent.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-3-13-read-landing-ask-lecturer-access.md`. Commit `7bca194`, visuelle rettinger `aa5e8fa`. Migrering 0022.
- `/` er forsiden, med én plass med demodata som uketabell. Skjemaet `/laerertilgang` lagrer i `access_requests`. «Brukere og roller» lister åpne forespørsler med «Inviter» og «Avvis».
- Backend: 1881 grønne på 71 s. Frontend: typecheck, Vitest (319), sjekker og bygg grønne. Playwright: 116 av 118 (den kjente ustabile `system-states`-testen).
- Gjennomgang: 45 funn, én middels rettet, én utsatt (oppbevaring av forespørsler).
- Visuell kontroll: 23 skjermbilder, fire rettinger på forsiden, fire punkter til vurdering.
- Status: `done`.

### Åpne punkter
- Issue #80: beslutninger, oppbevaring og nå-linja i uketabellen.

## Story 3.14: Streng produksjonskonfigurasjon i repoet (2026-11-18)

### Oppgave
Bygge Story 3.14 på `epic-3` uten skykonto, og ta med det som ble utsatt fra Story 3.2 (`JWT_SECRET` og klient-IP).

### Plan
`bmad-build-auto` i én underagent, som bare lager filer i repoet. Ingen skjermendring, så ingen visuell kontroll.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-3-14-strict-production-configuration.md`. Commit `4de78da`.
- Produksjonsvakter for hemmeligheter, flagg og grenser, klient-IP gjennom Caddy med `TRUSTED_PROXY_CIDRS`, `railway.toml` per tjeneste, bygg fra rotmappa, tilkoblingsbudsjett og `scripts/smoke`.
- Backend: 1962 grønne på 65 s. `scripts/smoke` og Playwright `logg-inn` og `landing` (19/19) er grønne mot den gjenoppbygde stacken.
- Status: `done`. Det som krever konto, står under «For Story 3.15» i specen.

### Åpne punkter
- Issue #81: beslutninger, og punktene til Story 3.15 (blant annet at `railway.toml` er merket utgått fra 2026-12-01).

## Avslutning av Epic 3 (2026-11-18)

### Oppgave
Gjøre klar for PR fra `epic-3`: rette CI, gjøre en samlet oppfølgende gjennomgang, rette UX-avvikene som ble utsatt, og gjøre de ustabile testene stabile. Story 3.15 står i `backlog`, som kjøreboka sier.

### Plan
- Rette CI selv. Fargeparet `ink` på `net-zero` manglet i tabellen etter den visuelle rettingen i Story 3.13.
- Én underagent for oppfølgende gjennomgang (3.1, 3.4, 3.5, 3.9, 3.10) og fem UX-rettinger.
- Én underagent for ustabile tester (`system-states.spec.ts` og `test_rescue.py`).
- Den visuelle kontrollen kjører nå hele Vitest-pakken (under 2 s).

### Resultat
- CI-retting: `ink` på `net-zero` er tillatt (DESIGN.md, matrisetrinn).
- Commit `6ea5c17`: e-post sendt på nytt for alltid når en resolver feilet, og kappløp ved deaktivering samtidig med invitasjon. Begge er rettet med tester. UX-rettinger i invitasjonslista, på «Institusjoner» og i invitasjonsskjemaet. Ny test for «Vis flere».
- Commit `ab504fd`: tilbakestillingstestene brukte demobrukerne og logget ut andre arbeidere. Demoinnlogginger ble stoppet av grensen. Tidtakerne startet først etter hydrering. `online`-hendelsen kom for tidlig. Den lokale postkassen valgte etter `sent_at` mens klokka hoppet. `test_rescue` hadde en fast frist på 2 s. Playwright 122/122 to ganger, system-states 180/180 to ganger, og `test_rescue` 40/40 under last.
- Backend: 1967 grønne.

### Åpne punkter
- Issue #82: tre tvilsomme funn (blant annet motsatt låserekkefølge som kan gi 500).

## Story 4.1: Lage klasse fra Lærerhjemmet (2026-11-18)

### Oppgave
Bygge Story 4.1 på `epic-4` (første story i Epic 4) og kontrollere den visuelt. Epic 3 er merget (PR #83). Brukeren vil at kjøringen stopper etter Epic 4, så compact kan kjøres.

### Plan
`bmad-build-auto` i én underagent, med sperren fra Story 3.9 koblet på. Deretter visuell kontroll i en egen underagent.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-4-1-create-class-from-laererhjem.md`. Commit `e3d48f7`. Migrering 0023.
- Modulen `classes` (`classes`, `class_staff`), `/api/classes`, policyer og `classes_visible_to(user)`. Sperren mot å fjerne faglærerrollen er koblet på (409 med riktig antall). Lærerhjemmet viser tom og fylt tilstand, og «Lag Klasse», klassesiden og en demoklasse er på plass.
- Backend: 1992 grønne. Frontend: typecheck, Vitest (335), sjekker og bygg grønne. Playwright: 130 grønne.
- Gjennomgang: 37 funn, 3 middels grupper og 4 lave rettet.
- Visuell kontroll: 14 skjermbilder, alle stemmer, to punkter til vurdering.
- Status: `done`.

### Åpne punkter
- Issue #84: beslutninger, restrisiko og visuelle punkter.

## Story 4.2: Laste opp klasseliste og velge e-postkolonne (2026-11-19)

### Oppgave
Bygge Story 4.2 på `epic-4` og kontrollere den visuelt.

### Plan
`bmad-build-auto` i én underagent. Personopplysninger skal ikke i loggen. Deretter visuell kontroll i en egen underagent.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-4-2-upload-roster-file-pick-email-column.md`. Commit `e20518f`, visuelle rettinger `68f0eb9`. Migrering 0024.
- Opplasting av .xlsx og .csv på klassesiden, lest i minnet. Bare cellene lagres, og de utløper. Forhåndsvisning, valg av e-postkolonne med grunn, og ny kontroll når kolonnen endres. Ny avhengighet: `openpyxl==3.1.5`.
- Backend: 2042 grønne på rundt 70 s (`test_rescue.py` feilet én gang under en Docker-ombygging). Frontend: typecheck, Vitest (341), sjekker og bygg er grønne. Playwright: 135 grønne.
- Gjennomgang: 37 funn, 6 middels og 13 lave rettet.
- Visuell kontroll: 22 skjermbilder og to rettinger. To klare avvik rettes i Story 4.3.
- Status: `done`.

### Åpne punkter
- Issue #85: beslutninger, sjekk mot ekte Canvas-eksporter, og visuelle avvik.

## Story 4.3: Ugyldige rader og innliming av adresser (2026-11-19)

### Oppgave
Bygge Story 4.3 på `epic-4`, rette to visuelle avvik fra 4.2 (Issue #85) og kontrollere visuelt.

### Plan
`bmad-build-auto` i én underagent. Den ble avbrutt i gjennomgangen og fullførte etter at den ble sendt tilbake. Deretter visuell kontroll i en egen underagent.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-4-3-see-invalid-rows-paste-addresses.md`. Commit `6d0f9aa`, visuelle rettinger `073da09`. Migrering 0025.
- `address_problem` gir hver rad en grunn. `POST /api/classes/{id}/roster-paste` er ny. Siden har «Ugyldige rader: N av M» og innliming med «Fortsett». Issue #85 punkt 1 og 2 er rettet.
- Backend: 2077 grønne. Frontend: typecheck, Vitest (344), sjekker og bygg grønne. Playwright: 139 grønne, og en ny test for grensen på 100.
- Gjennomgang: 32 funn, alle 7 middels og 13 lave rettet.
- Visuell kontroll: 16 skjermbilder og to rettinger. Tre tekstavvik rettes i Story 4.4.
- Status: `done`.

### Åpne punkter
- Issue #86: beslutninger og visuelle avvik.

## Story 4.4: Sende invitasjoner til klasselista med gyldighet (2026-11-19)

### Oppgave
Bygge Story 4.4 på `epic-4`, rette tre tekstavvik fra 4.3 (Issue #86) og kontrollere siden visuelt. Før storyen ble e2e-jobben i CI gjort raskere.

### Plan
- CI: Playwright-nettleseren caches, og apt-pakkene installeres bare når cachen ikke treffer. Installasjonen hadde tatt 7 av rundt 10 minutter.
- `bmad-build-auto` i én underagent, og så visuell kontroll i en egen underagent som også skulle legge til den utsatte testen.

### Resultat
- CI: første kjøring med cache tok 3,5 min, mot nesten 10 før.
- Spec: `.docs/implementation-artifacts/spec-4-4-send-invitations-roster-validity-period.md`. Commit `1330577`, visuelle rettinger `4d2a319`. Migrering 0026.
- Invitasjoner til studenter med gyldighet, merking av adresser som allerede står på lista, avvisning med 404 og 422, og antallet på klasselista på Lærerhjemmet og klassesiden. Issue #86 er rettet.
- Backend: 2101 grønne på 72 s. Frontend: typecheck, Vitest (348), sjekker og bygg grønne. Playwright: 142 grønne, pluss ny test for avvist sending.
- Visuell kontroll: 18 skjermbilder og to rettinger. Det utsatte funnet om test for avvist sending er lukket.
- Status: `done`.

### Åpne punkter
- Issue #87: beslutninger og visuelle avvik.
- Issue #86 lukkes.

## Story 4.5: Registrere seg som student gjennom invitasjonen (2026-11-19)

### Oppgave
Bygge Story 4.5 på `epic-4` og kontrollere den visuelt.

### Plan
`bmad-build-auto` i én underagent, som utvider invitasjonsflyten fra Story 3.8. Deretter visuell kontroll i en egen underagent. En `docker compose`-prosess så ut til å henge, så jeg stoppet den. Agentens egen bygging var da allerede ferdig.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-4-5-register-student-through-invitation.md`. Commit `9ba94af`, visuelle rettinger `d9c098d`. Migrering 0027.
- Studentlenker virker på «Du er invitert», med ny konto eller eksisterende konto og passord. Aksepten skjer i én transaksjon. Studenten ser bare sine egne klasser, og Hjem viser dem med startdato. Demoklassen har 8 studenter.
- Backend: 2113 grønne på 73 s. Frontend: typecheck, Vitest (351), sjekker og bygg grønne. Playwright: 146 grønne, pluss ny test for at Hjem oppdateres.
- Gjennomgang: 36 funn, 13 rettet (5 middels).
- Visuell kontroll: 22 skjermbilder og én etikett rettet.
- Status: `done`.

### Åpne punkter
- Issue #88: beslutninger, restrisiko (arkiverte klasser, ansatte som er studenter) og visuelle punkter.

## Story 4.6: Invitasjoner som kom i retur, og tallene (2026-11-19)

### Oppgave
Bygge Story 4.6 på `epic-4` og kontrollere den visuelt.

### Plan
`bmad-build-auto` i én underagent, med en lokal simulering av returer som ikke finnes i produksjon. Deretter visuell kontroll i en egen underagent.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-4-6-see-bounced-invitations-and-counts.md`. Commit `2983c90`, test fra den visuelle kontrollen `b7a66c7`. Migrering 0028.
- Webhook for Resend med signatursjekk, tall og returer på `GET /api/classes/{id}/invitations`, seksjonen «Invitasjoner» på klassesiden, og en lokal dev-rute for returer.
- Backend: 2171 grønne. Frontend: typecheck, Vitest (354), sjekker og bygg grønne. Playwright: 149 grønne, pluss ny test for oppdatering på åpen side.
- Gjennomgang: 30 funn, 3 middels og 8 lave rettet, 1 utsatt til 4.7.
- Visuell kontroll: 14 skjermbilder, alle stemmer.
- Status: `done`.

### Åpne punkter
- Issue #89: beslutninger om returer og tall, og visuelle punkter.

## Story 4.7: Følge registreringsstatus og sende påminnelser (2026-11-19)

### Oppgave
Bygge Story 4.7 på `epic-4`, ta med to utsatte punkter fra 4.5 og 4.6, og kontrollere visuelt.

### Plan
`bmad-build-auto` i én underagent, og så visuell kontroll i en egen underagent med vekt på den stablede stolpen.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-4-7-follow-registration-status-send-reminders.md`. Commit `99f6aa4`, visuell retting `ce41622`. Migrering 0029.
- `GET /api/classes/{id}/registrations` (status beregnes ved lesing), `POST /api/classes/{id}/reminders` (til alle eller én), `registered_students()`, og seksjonen «Status etter utsending» med stablet stolpe, summer, filter, søk og bekreftelse på stedet.
- Backend: 2194 grønne. Frontend: typecheck, Vitest (358), sjekker og bygg grønne. Playwright: 153 grønne.
- Gjennomgang: 35 funn, 1 middels og 7 lave rettet.
- Visuell kontroll: 36 skjermbilder, én retting, to punkter til vurdering (blant annet kontrasten i segmentet «Uregistrert»).
- Status: `done`.

### Åpne punkter
- Issue #90: beslutninger og visuelle punkter.

## Story 4.8: Registrere student manuelt og endre enkeltadresser (2026-11-19)

### Oppgave
Bygge Story 4.8 på `epic-4` og kontrollere den visuelt. Rette at to skjemaer kunne være åpne samtidig.

### Plan
`bmad-build-auto` i én underagent, med en eksplisitt beslutning om adresser til registrerte studenter. Deretter visuell kontroll i en egen underagent.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-4-8-register-student-manually-change-single-addresses.md`. Commit `8177a33`, visuelle rettinger `5595813`. Migrering 0030.
- Manuell registrering, ny enkeltadresse og «Fjern», med konsekvensen vist over knappen. Rad-handlinger i statuslista. Engangslenke for første passord.
- Backend: 2227 grønne. Frontend: typecheck, Vitest (362), sjekker og bygg grønne. Playwright: 155 grønne.
- Gjennomgang: 36 funn, ett middels rettet og 12 lave rettet.
- Visuell kontroll: 28 skjermbilder og to rettinger. Bare ett skjema kan nå være åpent om gangen.
- Status: `done`.

### Åpne punkter
- Issue #91: beslutninger, telling av «Send N» og tekstpunkter. Disse tas i den samlede gjennomgangen.

## Story 4.9: Dele klasse med medeiere og assistenter (2026-11-19)

### Oppgave
Bygge Story 4.9 på `epic-4`, sjekke alle klasseruter fra 4.2–4.8 mot rollene, og kontrollere visuelt.

### Plan
`bmad-build-auto` i én underagent, med en matrise av rolle × rute. Etterpå visuell kontroll i en egen underagent.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-4-9-share-class-co-owners-assistant-lecturers.md`. Commit `8488f0e`, visuell retting `8b56c85`. Migrering 0031.
- Siden «Faglærere og assistenter» på `/klasser/{id}/faglaerere`, med «Legg til Faglærer», «Inviter Assistent», fjerning, avvisning av siste eier, invitasjonstypen `assistant` og et register for aksept. Assistentrollen regnes ut fra `class_staff`, og assistenten har bare lesetilgang.
- Backend: 2250 grønne. Frontend: typecheck, Vitest (367), sjekker og bygg grønne. Playwright: 160/160 før gjennomgangen. Etterpå feilet to tester utenfor storyen like etter en omstart.
- Gjennomgang: 38 funn, 10 rettet.
- Visuell kontroll: 28 skjermbilder, én retting, fem tekstpunkter til den samlede gjennomgangen.
- Status: `done`.

### Åpne punkter
- Issue #92: beslutninger, visuelle punkter og ustabile e2e-tester.

## Story 4.10: Arkivere en klasse (2026-11-19)

### Oppgave
Bygge Story 4.10 på `epic-4`, den siste storyen i Epic 4. Avgjøre hva en arkivert klasse tillater på alle ruter fra 4.1–4.9, og kontrollere visuelt.

### Plan
`bmad-build-auto` i én underagent, med en matrise av rolle × rute × arkivert. Deretter visuell kontroll i en egen underagent på en ny klasse, aldri på demoklassen.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-4-10-archive-class.md`. Commit `e0ed1bd`, visuell retting `d634de7`.
- Arkivering i én transaksjon, med beskjed til de ansatte. 409 `class_archived` for eiere, ellers 403. Invitasjoner ugyldiggjøres og opplastinger slettes. Studentene mister klassen. Det er ingen angring.
- Backend: 2270 grønne på 101 s. Frontend: typecheck, Vitest (369), sjekker og bygg grønne. Playwright: 167/167.
- Gjennomgang: 36 funn. 3 middels og 6 lave er rettet, blant annet en kappløpstest for alle ni rutene som endrer noe.
- Visuell kontroll: 24 skjermbilder, én retting og fem punkter til den samlede gjennomgangen.
- Status: `done`.

### Åpne punkter
- Issue #93: beslutninger, vranglås ved aksept samtidig med arkivering, og visuelle punkter.

## Avslutning av Epic 4 (2026-11-19)

### Oppgave
Gjøre `epic-4` klar for PR: samlet gjennomgang, rette vranglåser og UX-punkter som var samlet opp, og få e2e-testene stabile også på gamle lokale data. Underveis ble CI gjort raskere med cache for Playwright.

### Plan
- Én underagent for den samlede gjennomgangen: to vranglåser, B-punktene fra Issue #91–#93, og oppfølging av specene for 4.3–4.6.
- Én underagent for e2e-testene: de skal ikke avhenge av gamle data, og ustabile tester skal rettes.

### Resultat
- Commit `7e67cc4`: fast låserekkefølge (klasse → bruker → invitasjon → oppføring på klasselista), med én test per kappløp (Issue #82 punkt 2 og #93). «Send N» teller ikke gjenopprettede studenter. Tekst- og UX-rettinger i 4.8–4.10. Specene for 4.3–4.6 er ok.
- Commit `bb73550`: `homes.spec.ts` sjekker bare egne data. Testene venter på hydrering, innloggingssvar og fonter før de måler. Den lokale grensen for innlogging per IP er hevet i compose. To trege filer har fått `test.slow()`.
- Backend: 2278 grønne. Playwright: fire fulle kjøringer, 168/168 hver gang.
- Issue #82 er lukket.

### Åpne punkter
- Issue #94: ett tvilsomt funn (et kolonnevalg som er underveis når en ny fil lastes opp).
- Issue #95: to trege e2e-filer (opptil 28 s).

## Stopp etter Epic 4: status for kjøringen (2026-11-19)

### Oppgave
Brukeren ba om stopp når Epic 4 var ferdig, for å kjøre compact og fortsette i et nytt kontekstvindu.

### Plan
Merge Epic 4 når CI er grønn, lage `epic-5` fra den nye `main` med statusen «epic-4: done», og stoppe før Story 5.1.

### Resultat
- Epic 1–4 er merget til `main` (PR #49, #65, #83, #96) med grønn CI. `epic-1` til `epic-4` står som `done`.
- `epic-5` er laget fra `main`. Story 5.1 står fortsatt i `backlog`. Neste økt starter der, etter kjøreboka.
- Story 3.15 står i `backlog` etter kjøreboka, fordi den krever produksjonskontoer.

**Stories i `review`:**
- Story 2.7: prøve mot OpenRouter med nøkkelen i `.env`. Sikkerhetsfilteret stoppet agentenes bruk av nøkkelen. Issue #56.
- Story 2.11: ekte måling av modell og effort-nivå. Samme årsak. Issue #60.

**Stories i `blocked`:** ingen.

**For neste økt:**
- Malene for byggeagenter ligger i scratchpad og kan forsvinne. Det viktige står i kjøreboka: ingen human in the loop, raske tester, mappene `backend/` og `frontend/`, OpenRouter med `deepseek/deepseek-v4.1-flash-1017`, og visuell kontroll per skjermstory.
- Erfaringer: byggeagenten implementerer selv. Gjennomgangsagenter blir noen ganger avbrutt, og da må byggeagenten sendes tilbake for å lese resultatene fra transkriptene. Compose-bygg kjøres med `timeout 900 … --wait`. Den visuelle kontrollen kjører hele Vitest-pakken. Tester må ikke avhenge av gamle lokale data.
- Testbrukere (passord `olspillet-demo`): `admin@`, `faglaerer@`, `admin-faglaerer@`, `assistent@`, `student@` og `student2`…`student8@example.com`. Demoklassen er «class-of-1994».

### Åpne punkter
- Issue #56 og #60: prøve og måling mot OpenRouter (grunnleggeren).
- Issue #95: to trege e2e-filer, bør tas før Epic 5.
- Issue #94: ett tvilsomt funn i 4.3.
- Issue #31: tekstgjennomgang av alle [ASSUMPTION]-tekster.

## Story 5.1: Lage klasseøkt med Classic-standardene (2026-11-19)

### Oppgave
Bygge Story 5.1 etter kjøreboka. Faglæreren lager en klasseøkt fra klassesiden, og økta fylles med Classic-standardene.

### Plan
Før storyen: gjøre testpakkene raskere og løse Issue #95. Deretter bygge med `bmad-build-auto`, gjøre en visuell kontroll med Playwright og avslutte.

### Resultat
- **Testfart:** backend-pakken gikk fra 98,6 s til 56,8 s, og hele Playwright-pakken fra 86 s til 77 s. Commits 072297b og 10090f6. Issue #95 er lukket.
- **Spec:** `.docs/implementation-artifacts/spec-5-1-create-class-session-classic-defaults.md`.
- **Commits:**
  - 19c85f0: ny modul `sessions`, migrasjon 0032 `class_sessions`, skjermen `/klasseokter/{id}` og lista på klassesiden;
  - 3623044: visuelle rettinger (merkelapper på 13 px, likt radbrudd på mobil).
- **Tester:** 2296 backend-tester (56 s), 372 Vitest-tester, 182 Playwright-tester, typecheck, copy-sjekk, fargelint og bygg.
- **Gjennomgang:** fire gjennomgangsagenter fant 40 punkter. 12 ble rettet, og resten ble avvist med begrunnelse i specen.
- **Skjermbilder:** `screenshots/5.1/`, 14 bilder.
- **Status:** done.

### Åpne punkter
- Issue 99: beslutninger i Story 5.1.
- Issue #98: visuelle avvik (rulling i kjeden på mobil, etterspørselen under «Kundene», like merkelapper). Rettes i 5.2.
- Issue #97: ingen bekreftelse når siste adresse fjernes (Epic 4). Tas i avslutningen av Epic 5.

## Story 5.2: Sette de fire datoene på datolinja (2026-11-19)

### Oppgave
Bygge Story 5.2 etter kjøreboka, og rette avvik (a) og (b) fra Issue #98 på samme skjerm.

### Plan
Bygge med `bmad-build-auto`, gjøre en visuell kontroll med Playwright og avslutte.

### Resultat
- **Spec:** `.docs/implementation-artifacts/spec-5-2-set-four-dates-on-datolinje.md`.
- **Commit e0c80d8:**
  - migrasjon 0033 med de fire datoene, og reglene for rekkefølge og passerte datoer i API-et;
  - datolinja og `GET /api/me/class-sessions`;
  - «Venter» og «Neste frist» på Lærerhjemmet;
  - kanter som toner ut når innholdet ruller, og løpenummer i merkelappene.
- **Tester:** 2315 backend-tester (57 s), Vitest, typecheck, bygg og 193 Playwright-tester.
- **Gjennomgang:** 31 punkter, 4 middels. De middels er rettet.
- **Visuell kontroll:** 19 skjermbilder i `screenshots/5.2/`. Ingen klare avvik.
- **Status:** done.

### Åpne punkter
- Issue 100: beslutninger og visuelle vurderinger i 5.2. Et halvveis utfylt datofelt tømmer datoen; det tas i avslutningen av Epic 5.
- Issue #98: etterspørselen under «Kundene» står igjen, og tas i 5.4.

## Story 5.3: Endre spillinnstillinger med feil og advarsler for verdiområder (2026-11-19)

### Oppgave
Bygge Story 5.3 etter kjøreboka.

### Plan
Bygge med `bmad-build-auto`, gjøre en visuell kontroll med Playwright og avslutte.

### Resultat
- **Spec:** `.docs/implementation-artifacts/spec-5-3-change-game-settings-range-errors-warnings.md`.
- **Commit 0cc0bcc:** lagring av spillinnstillinger med motorens validering, ruten `settings-check`, redigering av de elleve innstillingene med feil og advarsler, kalibreringslinje og felles tallformat.
- **Avbrudd:** byggeagenten stoppet midt i gjennomgangen og ble sendt tilbake for å fullføre.
- **Tester:**
  - backend: 2347 tester (60 s);
  - frontend: Vitest 391, typecheck, bygg og Playwright 200/200.
- **Gjennomgang:** 33 funn, 6 middels. De middels er rettet.
- **Visuell kontroll:** 14 skjermbilder i `screenshots/5.3/`. Ingen klare avvik; to punkter er samlet til avslutningen av epicet.
- **Status:** done.

### Åpne punkter
- Issue 101: beslutninger i Story 5.3.

## Story 5.4: Velge etterspørselsmønster og frø (2026-11-20)

### Oppgave
Bygge Story 5.4 etter kjøreboka, og vise etterspørselen under «Kundene» (siste punkt i Issue #98).

### Plan
Bygge med `bmad-build-auto`, gjøre en visuell kontroll med Playwright og avslutte.

### Resultat
- **Spec:** `.docs/implementation-artifacts/spec-5-4-choose-demand-pattern-and-seed.md`.
- **Commit 4a1875c:** `demand` og `demand_seed` i lagring og sjekk, ruten `demand-series`, delen «Etterspørsel» med fire mønstre og frø, tabell uke for uke, og etterspørselen i kjeden.
- **Tester:**
  - backend: 2376 tester (58 s);
  - frontend: Vitest 398, typecheck, bygg og Playwright 207.
- **Gjennomgang:** 36 funn, 4 middels. De middels er rettet.
- **Visuell kontroll:** 24 skjermbilder i `screenshots/5.4/`. Ingen klare avvik; to punkter er samlet til avslutningen av epicet.
- **Status:** done.

### Åpne punkter
- Issue 102: beslutninger i Story 5.4.
- Issue #98 lukkes; alle tre punktene er løst.

## Story 5.5: Velge KI-modus, effort-nivå og debrief-modus (2026-11-20)

### Oppgave
Bygge Story 5.5 etter kjøreboka.

### Plan
Bygge med `bmad-build-auto`, gjøre en visuell kontroll med Playwright og avslutte.

### Resultat
- **Spec:** `.docs/implementation-artifacts/spec-5-5-choose-ai-mode-effort-level-debrief-mode.md`.
- **Commit 4550567:** migrasjon 0034 `effort_level`, valg av KI-modus, effort-nivå og debrief-modus med effektlinjer, beskrivelser av KI-spillerne og Visningsbryter.
- **Avbrudd:** byggeagenten leverte før gjennomgangen var ferdig og ble sendt tilbake.
- **Tester:**
  - backend: 2393 tester (63 s);
  - frontend: Vitest 406, typecheck, bygg og Playwright 216.
- **Gjennomgang:** 33 funn, 2 middels. Begge er rettet.
- **Visuell kontroll:** 16 skjermbilder i `screenshots/5.5/`. Ett avvik er rettet (3a56c65). Den låste visningen tas i 5.11.
- **Status:** done.

### Åpne punkter
- Issue 103: beslutninger i Story 5.5.

## Story 5.6: Legge til labtimer (2026-11-20)

### Oppgave
Bygge Story 5.6 etter kjøreboka.

### Plan
Bygge med `bmad-build-auto`, gjøre en visuell kontroll med Playwright og avslutte.

### Resultat
- **Spec:** `.docs/implementation-artifacts/spec-5-6-add-lab-hours.md`.
- **Commit 3e79579:** migrasjon 0035 `lab_hours`, ruter for å legge til, endre og fjerne, melding i den daglige oppsummeringsmailen, labtimer på datolinja med forklaring og liste.
- **Tester:**
  - backend: 2412 tester;
  - frontend: Vitest 414, typecheck, bygg og Playwright 224.
- **Gjennomgang:** 38 punkter. Det middels punktet (fokus etter «Avbryt») er rettet.
- **Visuell kontroll:** 20 skjermbilder i `screenshots/5.6/`. Ett avvik er rettet (795a5a9).
- **Status:** done.

### Åpne punkter
- Issue 104: beslutninger i Story 5.6.

## Story 5.7: Merke klasseøkta som obligatorisk og sette inaktivitetsgrensen (2026-11-20)

### Oppgave
Bygge Story 5.7 etter kjøreboka.

### Plan
Bygge med `bmad-build-auto`, gjøre en visuell kontroll med Playwright og avslutte.

### Resultat
- **Spec:** `.docs/implementation-artifacts/spec-5-7-mark-obligatory-set-inactivity-limit.md`.
- **Commit 2b26dc8:**
  - bryteren «Obligatorisk» og andelen uker som kreves (migrasjon 0036);
  - feltet «Ventetid før KI tar over»;
  - melding i den daglige oppsummeringsmailen.
- **Tester:**
  - backend: 2435 tester (63 s);
  - frontend: Vitest 422, typecheck, bygg og Playwright 234;
  - migrasjonstesten tar 1,7 s, på linje med de andre migrasjonstestene.
- **Gjennomgang:** 35 funn, 1 middels. Det middels er rettet.
- **Visuell kontroll:** 18 skjermbilder i `screenshots/5.7/`. Ingen avvik.
- **Status:** done.

### Åpne punkter
- Issue 105: beslutninger i Story 5.7.

## Story 5.8: Forhåndsvise en tilfeldig fordeling og kjøre den på nytt (2026-11-20)

### Oppgave
Bygge Story 5.8 etter kjøreboka.

### Plan
Bygge med `bmad-build-auto`, gjøre en visuell kontroll med Playwright og avslutte.

### Resultat
- **Spec:** `.docs/implementation-artifacts/spec-5-8-preview-random-allocation-run-again.md`.
- **Commit c3d31a0:**
  - fordelingsfunksjonen og migrasjon 0037 `allocation_drafts`;
  - ruter for å lese, åpne og trekke på nytt;
  - blokken «Fordeling» med SVG-diagram og listevisning.
- **Tester:**
  - backend: 2462 tester (62 s);
  - frontend: Vitest 425, typecheck, bygg og Playwright 242.
- **Gjennomgang:** 28 funn, 3 middels. Alle er rettet.
- **Visuell kontroll:** 26 skjermbilder i `screenshots/5.8/`. Ett avvik er rettet (94678f6), to små punkter går til 5.9.
- **Status:** done.

### Åpne punkter
- Issue 106: beslutninger i Story 5.8.

## Story 5.9: Bekrefte fordelingen jeg ser på (2026-11-20)

### Oppgave
Bygge Story 5.9 etter kjøreboka, og rette de to punktene fra Issue #106 i fordelingspanelet.

### Plan
Bygge med `bmad-build-auto`, gjøre en visuell kontroll med Playwright og avslutte.

### Resultat
- **Spec:** `.docs/implementation-artifacts/spec-5-9-confirm-allocation-i-am-looking-at.md`.
- **Commit ebd5057:**
  - «Bekreft fordeling» med kontroll av revisjon;
  - klassespill og plasser (migrasjon 0038) og mail;
  - fordelinger som mangler, på Lærerhjemmet;
  - stiplet celle for fjernede studenter og ramme på 1 px.
- **Avbrudd:** byggeagenten ble sendt tilbake én gang, fordi gjennomgangsagentene stoppet.
- **Tester:**
  - backend: 2482 tester;
  - frontend: Vitest 428, typecheck, bygg og Playwright 245.
- **Gjennomgang:** 31 funn, 2 middels. Begge er rettet.
- **Visuell kontroll:** 22 skjermbilder i `screenshots/5.9/`. To avvik er rettet (f73ecd8).
- **Status:** done.

### Åpne punkter
- Issue 107: beslutninger i Story 5.9.

## Story 5.10: Flytte eller bytte studenter i fordelingen (2026-11-20)

### Oppgave
Bygge Story 5.10 etter kjøreboka, og la en bekreftet fordeling vise at den er bekreftet (Issue #107).

### Plan
Bygge med `bmad-build-auto`, gjøre en visuell kontroll med Playwright og avslutte.

### Resultat
- **Spec:** `.docs/implementation-artifacts/spec-5-10-move-or-swap-students-in-allocation.md`.
- **Commit 5f4bf07:**
  - flytte og bytte, før og etter bekreftelse, med `move_seat` og migrasjon 0039;
  - plasslister i panelet;
  - bekreftelseslinja.
- **Tester:**
  - backend: 2501 tester;
  - frontend: Vitest 430, typecheck, bygg og Playwright 252.
- **Gjennomgang:** 30 funn, 2 middels. Begge er rettet.
- **Visuell kontroll:** 22 skjermbilder i `screenshots/5.10/`. Ett avvik er rettet (9b68c2c).
- **Status:** done.

### Åpne punkter
- Issue 108: beslutninger i Story 5.10.

## Story 5.11: Låse klasseøkta på startdatoen (2026-11-20)

### Oppgave
Bygge Story 5.11 etter kjøreboka, og rette den låste visningen fra Issue #103.

### Plan
Bygge med `bmad-build-auto`, gjøre en visuell kontroll med Playwright og avslutte.

### Resultat
- **Spec:** `.docs/implementation-artifacts/spec-5-11-lock-class-session-at-start-date.md`.
- **Commit 1dd6b0f:**
  - låsing i sveipet, med et frosset øyeblikksbilde (migrasjon 0040);
  - avvisning og melding når nøkkelen mangler;
  - låst visning som tekst.
- **Avbrudd:** steg 1 tok rundt én time før byggeagenten fikk en statusforespørsel.
- **Tester:**
  - backend: 2510 tester;
  - frontend: Vitest, typecheck og bygg;
  - Playwright: 256 passerte og 1 feilet under last; den passerer når den kjøres alene.
- **Gjennomgang:** 50 funn. 11 ble rettet og 3 er utsatt. Byggeagenten anbefaler en oppfølgende gjennomgang.
- **Visuell kontroll:** 12 skjermbilder i `screenshots/5.11/`. Ingen klare avvik.
- **Status:** done.

### Åpne punkter
- Issue 109: beslutninger og utsatte punkter i Story 5.11.

## Story 5.12: Åpne klassespillene på det frosne øyeblikksbildet (2026-11-20)

### Oppgave
Bygge Story 5.12 etter kjøreboka.

### Plan
Bygge med `bmad-build-auto`, gjøre en kort visuell kontroll med Playwright og avslutte.

### Resultat
- **Spec:** `.docs/implementation-artifacts/spec-5-12-open-class-games-on-frozen-snapshot.md`.
- **Commit 7e011a7:**
  - `set_snapshot`, og KI-spillere på ledige plasser;
  - automatisk fordeling ved låsing;
  - fullføring av åpninger i sveipet;
  - lista over åpnede spill i «Fordeling».
- **Tester:**
  - backend: 2518 tester;
  - frontend: Vitest 432, typecheck, bygg og Playwright 262.
- **Gjennomgang:** 46 funn, 13 rettet og 2 utsatt. Byggeagenten anbefaler en oppfølgende gjennomgang.
- **Visuell kontroll:** 8 skjermbilder i `screenshots/5.12/`. Ett avvik er rettet (0d21d83).
- **Status:** done.

### Åpne punkter
- Issue 110: beslutninger og utsatte punkter i Story 5.12.

## Story 5.13: Gi plass til studenter som registrerer seg etter fordelingen (2026-11-20)

### Oppgave
Bygge Story 5.13 etter kjøreboka.

### Plan
Bygge med `bmad-build-auto`, gjøre en kort visuell kontroll med Playwright og avslutte.

### Resultat
- **Spec:** `.docs/implementation-artifacts/spec-5-13-seat-students-who-register-after-allocation.md`.
- **Commit a558089:** to nye handlinger i sveipet (plass til nye studenter og erstatning for fjernede studenter), `students_without_seat` og linja i «Fordeling».
- **Tester:**
  - backend: 2538 tester;
  - frontend: Vitest 433, typecheck, bygg og Playwright 263.
- **Gjennomgang:** 34 lave funn. 9 ble rettet.
- **Visuell kontroll:** 8 skjermbilder i `screenshots/5.13/`. Ett avvik er rettet (accb50d).
- **Status:** done.

### Åpne punkter
- Issue 111: beslutninger i Story 5.13.

## Story 5.14: Minne studentene på hver frist 24 timer før (2026-11-20)

### Oppgave
Bygge Story 5.14 etter kjøreboka.

### Plan
Bygge med `bmad-build-auto`. Ingen visuell kontroll, fordi `frontend/` ikke endres.

### Resultat
- **Spec:** `.docs/implementation-artifacts/spec-5-14-remind-students-24-hours-before-each-deadline.md`.
- **Commit 8c3e9d7:** `sessions.send_deadline_reminder` i sveipet, migrasjon 0041 `deadline_reminders` og mailmalen for påminnelsen.
- **Tester:** 2551 backend-tester (rundt 71 s), ruff og copy-sjekken.
- **Gjennomgang:** 21 lave funn. 4 ble rettet.
- **Status:** done.

### Åpne punkter
- Issue 112: beslutninger i Story 5.14.
- Backend-pakken har vokst til rundt 71 s. Den måles igjen i avslutningen av Epic 5.

## Story 5.15: Sette transportkapasitet (kuttliste, `FEATURE_CAPACITY`) (2026-11-20)

### Oppgave
Bygge Story 5.15 etter kjøreboka.

### Plan
Bygge med `bmad-build-auto`, gjøre en visuell kontroll med Playwright og avslutte.

### Resultat
- **Spec:** `.docs/implementation-artifacts/spec-5-15-set-shipping-capacity.md`.
- **Commit afe6439:** kapasitet som spillinnstilling bak flagget, `capacity_enabled` i API-et, bryteren «Kapasitet» og «Maks N» i kjeden.
- **Avbrudd:**
  - steg 1 tok rundt 30 minutter før byggeagenten fikk en statusforespørsel;
  - byggeagenten leverte under gjennomgangen og ble sendt tilbake.
- **Tester:**
  - backend: 2562 tester;
  - frontend: Vitest 441, typecheck, bygg og Playwright 265/265.
- **Gjennomgang:** 30 funn, 7 middels. Fire problemer ble rettet.
- **Visuell kontroll:** 12 skjermbilder i `screenshots/5.15/`. Ett avvik er rettet (1dc73ce).
- **Status:** done.

### Åpne punkter
- Issue 113: beslutninger i Story 5.15.

## Story 5.16: Sette informasjonssynlighet (kuttliste, `FEATURE_INFO_VISIBILITY`) (2026-11-20)

### Oppgave
Bygge Story 5.16 etter kjøreboka.

### Plan
Bygge med `bmad-build-auto` etter samme mønster som 5.15, gjøre en visuell kontroll og avslutte.

### Resultat
- **Spec:** `.docs/implementation-artifacts/spec-5-16-set-information-visibility.md`.
- **Commit 79ad488:** `info_visibility` i innstillingene (`schema_version` 2) og «Synlige naboer» med to brytere bak flagget.
- **Tester:**
  - backend: 2591 tester, og dekningen av motoren er 100 %;
  - frontend: Vitest 445, typecheck og bygg;
  - Playwright: 267/267 i én kjøring. I neste kjøring fikk 12 tester tidsavbrudd rett etter bygget, og de passerte ved ny kjøring.
- **Gjennomgang:** 28 funn. Det middels funnet er rettet.
- **Visuell kontroll:** 10 skjermbilder i `screenshots/5.16/`. Ett avvik er rettet (d065411).
- **Status:** done.

### Åpne punkter
- Issue 114: beslutninger i Story 5.16.

## Story 5.17: La studentene velge klassespill og plass (kuttliste, `FEATURE_STUDENT_CHOICE`) (2026-11-20)

### Oppgave
Bygge Story 5.17 etter kjøreboka.

### Plan
Bygge med `bmad-build-auto`, gjøre en visuell kontroll med Playwright og avslutte.

### Resultat
- **Spec:** `.docs/implementation-artifacts/spec-5-17-let-students-choose-class-game-and-seat.md`.
- **Commit 441ffb8:**
  - «Fordelingsmåte» for faglæreren, med migrasjon 0042;
  - siden «Velg spill og sete» for studentene og lenken på Hjem;
  - et nytt steg i sveipet for studenter som registrerer seg sent.
- **Tester:**
  - backend: 2606 tester;
  - frontend: Vitest 452, typecheck og bygg;
  - Playwright: den nye filen passerer 6/6. 7 andre tester feilet under last og passerte ved ny kjøring.
- **Gjennomgang:** 48 funn, 16 grupper rettet og 1 utsatt. Byggeagenten anbefaler en oppfølgende gjennomgang.
- **Visuell kontroll:** 20 skjermbilder i `screenshots/5.17/`. To avvik er rettet (a42b1d3).
- **Status:** done.

### Åpne punkter
- Issue 115: beslutninger i Story 5.17.

## Story 5.18: Lage en klasseøkt fra en tidligere økt (kuttliste, `FEATURE_RERUN`) (2026-11-20)

### Oppgave
Bygge Story 5.18, den siste storyen i Epic 5, etter kjøreboka.

### Plan
Bygge med `bmad-build-auto`, gjøre en visuell kontroll med Playwright og avslutte.

### Resultat
- **Spec:** `.docs/implementation-artifacts/spec-5-18-create-class-session-from-earlier-one.md`.
- **Commit 5f35b1c:** to nye ruter bak flagget, migrasjon 0043, et panel for å velge kilde på klassesiden, og en merknad på den nye Klasseøkta.
- **Tester:**
  - backend: 2621 tester (81 s);
  - frontend: Vitest 456, typecheck og bygg;
  - Playwright: 271 passerte. 7 feilet under last og passerte ved ny kjøring.
- **Gjennomgang:** 40 funn, 1 middels. 14 ble rettet.
- **Visuell kontroll:** 14 skjermbilder i `screenshots/5.18/`. Ingen klare avvik.
- **Status:** done.

### Åpne punkter
- Issue 116: beslutninger i Story 5.18.

## Avslutning av Epic 5 (2026-11-20)

### Oppgave
Avslutte Epic 5 etter kjøreboka: én oppfølgende gjennomgang, én stabilisering av e2e, og deretter PR og merge.

### Plan
1. Gjennomgå 5.11, 5.12 og 5.17 på tvers av storyene, siden specene deres anbefalte det, og rette de samlede UX-punktene.
2. Stabilisere e2e under last og gjøre backend-pakken raskere.
3. Lage en PR mot `main`.

### Resultat
- **Oppfølgende gjennomgang:** commits 6e91bd5, ce5a46e, 3e6ba26 og 841a79a.
  - Låsen sjekker startdatoen på nytt etter at raden er låst.
  - Låsen kan bruke plassen til en student som valgte og så ble fjernet.
  - En avvist lås lagres og vises til faglæreren (migrasjon 0044). Arkiverte økter prøves ikke lenger hvert minutt.
  - UX-punktene fra Issue #97, #100–#102, #109 og #114–#116 er rettet, og issuene er lukket.
- **Stabilisering:** commits 354a1ff og 5c00c0c.
  - Sveipet blokkerte mailkøen i 10–20 s hvert minutt. Oppslagene leser nå samlet, og tiden gikk fra 6,3 s til 0,17 s.
  - Restretting av Issue #97, og fokus flyttes etter at elementet finnes.
  - Den lange filterlista i admin-audit er kortet ned i testene.
  - Funnet en produksjonsfeil: upsert av tilgangsforespørsler feilet med en generisk plan. Rettet, med en regresjonstest.
  - Backend-pakken gikk fra rundt 80 s til 60 s.
  - E2e med CI-kommandoen passerte 280/280 to ganger på rad rett etter bygget.

### Åpne punkter
- Issue #117: to punkter som er avgjort til senere (spill som aldri åpnes, og spill med bare KI-spillere når studentene velger).
- Issue #56 og #60: Story 2.7 og 2.11 står i `review`.
- Issue #31: tekstgjennomgang av alle [ASSUMPTION]-tekster.

## Story 6.1: Se klassespill, rolle og plasser på Hjem (2026-11-20)

### Oppgave
Bygge Story 6.1, den første storyen i Epic 6, etter kjøreboka.

### Plan
Bygge med `bmad-build-auto`, gjøre en visuell kontroll med Playwright og avslutte.

### Resultat
- **Spec:** `.docs/implementation-artifacts/spec-6-1-see-class-game-role-seats-on-hjem.md`. I tillegg er `epic-6-context.md` laget.
- **Commit 1e17fda:**
  - `game` og `steps` i `/api/me/class-sessions`, og modulen `progress` (migrasjon 0045);
  - `own_seat` og `GET /api/me/games/{id}`;
  - ny Hjem for studenten.
- **Tester:**
  - backend: 2610 tester (64 s);
  - frontend: Vitest 467, typecheck og bygg;
  - Playwright: 288 tester med 2 arbeidere.
- **Gjennomgang:** 47 funn, 4 middels. 3 ble rettet.
- **Visuell kontroll:** 18 skjermbilder i `screenshots/6.1/`. Tre avvik er rettet (bd3cb91).
- **Status:** done.

### Åpne punkter
- Issue 119: beslutninger i Story 6.1.

## Story 6.2: Lese reglene før første ordre (2026-11-20)

### Oppgave
Bygge Story 6.2 etter kjøreboka.

### Plan
Bygge med `bmad-build-auto`, gjøre en visuell kontroll med Playwright og avslutte.

### Resultat
- **Spec:** `.docs/implementation-artifacts/spec-6-2-read-rules-before-first-order.md`.
- **Commit 7aaf91b:** regelsiden `/spill/{id}/regler`, `briefing_first` og `rules` i spillkortet, og «Les reglene» på Hjem.
- **Tester:**
  - backend: 2613 tester;
  - frontend: Vitest 473 og bygg;
  - Playwright: 297 tester med 2 arbeidere.
- **Gjennomgang:** to runder. Grafstripa er utsatt til 6.6 og 6.7.
- **Visuell kontroll:** 9 skjermbilder i `screenshots/6.2/`. To avvik er rettet (6ca3ac6).
- **Status:** done.

### Åpne punkter
- Issue 120: beslutninger i Story 6.2.

## Story 6.3: Gjøre startoppgaven (2026-11-20)

### Oppgave
Bygge Story 6.3 etter kjøreboka.

### Plan
Bygge med `bmad-build-auto`, gjøre en visuell kontroll med Playwright og avslutte.

### Resultat
- **Spec:** `.docs/implementation-artifacts/spec-6-3-do-the-starting-task.md`.
- **Commit 4a5c3a7:**
  - modulene `content` og `tests`, migrasjon 0046 og `score_sum`;
  - tre ruter for startoppgaven og siden `/spill/{id}/startoppgave`;
  - komponenten `column-item`.
- **Tester:**
  - backend: 2628 tester;
  - frontend: Vitest 480 og bygg;
  - Playwright: 305 tester med 2 arbeidere;
  - én ny test tar 1,1 s.
- **Gjennomgang:** 55 funn. 2 middels grupper ble rettet.
- **Visuell kontroll:** 19 skjermbilder i `screenshots/6.3/`. Ingen klare avvik; tre punkter er samlet til avslutningen av epicet.
- **Status:** done.

### Åpne punkter
- Issue 121: beslutninger i Story 6.3.

## Story 6.4: Se endringer uten å laste siden på nytt (2026-11-20)

### Oppgave
Bygge Story 6.4 etter kjøreboka.

### Plan
Bygge med `bmad-build-auto`. Ingen egen visuell kontroll, fordi den eneste synlige endringen er linja om tilkoblingen.

### Resultat
- **Spec:** `.docs/implementation-artifacts/spec-6-4-see-changes-without-reloading.md`.
- **Commit 851bf88:** SSE på `GET /api/events` med `LISTEN` i Postgres, ny henting etter `topics.ts` i webappen, og linja som viser at siden er utdatert.
- **Tester:**
  - backend: 2651 tester;
  - frontend: Vitest 493 og bygg;
  - Playwright: 309 tester med 2 arbeidere, uten faste pauser.
- **Gjennomgang:** 46 funn, 5 middels. 2 ble rettet, og 1 er utsatt. Byggeagenten anbefaler en oppfølgende gjennomgang.
- **Status:** done.

### Åpne punkter
- Issue 122: beslutninger i Story 6.4.

## Story 6.5: Starte klassespillet (2026-11-20)

### Oppgave
Bygge Story 6.5 etter kjøreboka.

### Plan
Bygge med `bmad-build-auto`, gjøre en visuell kontroll med Playwright og avslutte.

### Resultat
- **Spec:** `.docs/implementation-artifacts/spec-6-5-start-the-class-game.md`.
- **Commit 81538f1:**
  - `POST /api/me/games/{id}/start`, og `status` og `week` på spillet;
  - neste steg på Hjem, på ferdigskjermen og på den nye spillsiden `/spill/{id}`.
- **Tester:**
  - backend: 2659 tester;
  - frontend: Vitest 495 og bygg;
  - Playwright: 319 tester med 2 arbeidere.
- **Gjennomgang:** 37 funn, 4 middels. Alle er rettet. Byggeagenten anbefaler en oppfølgende gjennomgang.
- **Visuell kontroll:** 29 skjermbilder i `screenshots/6.5/`. Ingen klare avvik.
- **Status:** done.

### Åpne punkter
- Issue 123: beslutninger i Story 6.5, og en merknad om hvordan et helt spill kan kjøres i de siste reisene.

## Story 6.6: Se uka til plassen min i uketabellen (2026-11-20)

### Oppgave
Bygge Story 6.6 etter kjøreboka.

### Plan
Bygge med `bmad-build-auto`, gjøre en visuell kontroll med Playwright og avslutte.

### Resultat
- **Spec:** `.docs/implementation-artifacts/spec-6-6-see-my-seat-week-in-week-table.md`.
- **Commit 1243a70:**
  - `GET /api/me/games/{id}/play`, og Netto lager i motoren (`SeatState` v2);
  - Topplinja og uketabellen på `/spill/{id}`, med oppsett for telefon, nettbrett og laptop.
- **Tester:**
  - backend: 2674 tester (65 s), og dekningen av motoren er 100 %;
  - frontend: Vitest 504 og bygg;
  - Playwright: 330 tester med 2 arbeidere.
- **Gjennomgang:** 33 lave funn. 11 ble rettet.
- **Visuell kontroll:** 24 skjermbilder i `screenshots/6.6/`. Tre avvik er rettet (94d50db).
- **Status:** done.

### Åpne punkter
- Issue 124: beslutninger i Story 6.6.

## Story 6.7: Se Netto lager, Posisjon og kostnad som graf over tabellen (2026-11-20)

### Oppgave
Bygge Story 6.7 etter kjøreboka, og gjøre ukenumrene grå unntatt inneværende uke (Issue #124).

### Plan
Bygge med `bmad-build-auto`, gjøre en visuell kontroll med Playwright og avslutte.

### Resultat
- **Spec:** `.docs/implementation-artifacts/spec-6-7-graph-over-table.md`.
- **Commit 548c08f:**
  - graf over tabellen i SVG laget for hånd, med «Nå»-linje og fremtid i tonet bakgrunn;
  - kostnadsdelingen i motoren (`SeatState` v3);
  - PDF-sjekk med WeasyPrint i CI.
- **Tester:**
  - backend: 2693 tester, og dekningen av motoren er 100 %;
  - frontend: Vitest 523 og bygg;
  - Playwright: 349 tester med 2 arbeidere;
  - PDF-sjekken passerer.
- **Gjennomgang:** 31 lave funn. 6 ble rettet.
- **Visuell kontroll:** 20 skjermbilder i `screenshots/6.7/`. Ett avvik er rettet (e960af9).
- **Status:** done.

### Åpne punkter
- Issue 125: beslutninger i Story 6.7.

## Story 6.8: Se plassen med Demodata på forsiden som graf over tabellen (2026-11-20)

### Oppgave
Bygge Story 6.8 etter kjøreboka.

### Plan
Bygge med `bmad-build-auto`, gjøre en visuell kontroll med Playwright og avslutte.

### Resultat
- **Spec:** `.docs/implementation-artifacts/spec-6-8-landing-demodata-graph-over-table.md`.
- **Commit 2e950e5:** `seat-figure.tsx` med samme `WeekTable` som spillskjermen, data fra motoren i `demo-seat.json`, og felles sjekker for justering i `e2e/support/graph.ts`.
- **Tester:**
  - backend: 2694 tester;
  - frontend: Vitest 525 og bygg;
  - Playwright: 348 av 349 passerte. 1 mailtest feilet under last og passerte alene.
- **Gjennomgang:** 32 funn. 15 lave ble rettet.
- **Visuell kontroll:** 6 skjermbilder i `screenshots/6.8/`. To avvik er rettet (d1c33b4).
- **Status:** done.

### Åpne punkter
- Issue 126: beslutninger i Story 6.8.

## Story 6.9: Se mitt ledd i kjeden i Kjedebåndet (2026-11-20)

### Oppgave
Bygge Story 6.9 etter kjøreboka.

### Plan
Bygge med `bmad-build-auto`, gjøre en visuell kontroll med Playwright og avslutte.

### Resultat
- **Spec:** `.docs/implementation-artifacts/spec-6-9-kjedeband-own-link.md`.
- **Commit dd227c6:** Kjedebåndet i SVG med en egen utregning av oppsettet, plassert mellom Topplinja og grafen. Ingen endringer i backend.
- **Tester:**
  - backend: 2695 tester;
  - frontend: Vitest 544 og bygg;
  - Playwright: 357 tester med 2 arbeidere.
- **Gjennomgang:** 36 lave funn. 6 ble rettet.
- **Visuell kontroll:** 40 skjermbilder i `screenshots/6.9/`. Ett avvik er rettet (c7287ef).
- **Status:** done.

### Åpne punkter
- Issue 127: beslutninger i Story 6.9.

## Story 6.10: Spille de veiledede ukene (2026-11-20)

### Oppgave
Bygge Story 6.10 etter kjøreboka.

### Plan
Bygge med `bmad-build-auto`, gjøre en visuell kontroll med Playwright og avslutte.

### Resultat
- **Spec:** `.docs/implementation-artifacts/spec-6-10-play-the-guided-weeks.md`.
- **Commit e0db96f:** fast ordre for alle plasser i veiledede uker, visning som ordre (migrasjon 0047), og felt som bare kan leses på spillskjermen.
- **Tester:**
  - backend: 2704 tester (76 s), og resultatene fra golden batch er uendret;
  - frontend: Vitest 547 og bygg;
  - Playwright: 364 tester før rettingene, og 55 tester for spillskjermen etter dem.
- **Gjennomgang:** 30 funn, 1 middels. 4 ble rettet.
- **Visuell kontroll:** 14 skjermbilder i `screenshots/6.10/`. Ett avvik er rettet (e1ddf85).
- **Status:** done.

### Åpne punkter
- Issue 128: beslutninger i Story 6.10.

## Story 6.11: Skrive en ordre og se hvor den kommer fram (2026-11-20)

### Oppgave
Bygge Story 6.11 etter kjøreboka, og fjerne tekstmarkøren i ordrefeltet når det bare kan leses (Issue #128).

### Plan
Bygge med `bmad-build-auto`, gjøre en visuell kontroll med Playwright og avslutte.

### Resultat
- **Spec:** `.docs/implementation-artifacts/spec-6-11-type-an-order-and-see-where-it-lands.md`.
- **Commit f31ace1:** ordrefelt med − og + og validering, forhåndsvisning i tabellen med en tynn linje, og en boks i Kjedebåndet.
- **Tester:**
  - backend: 2705 tester (75 s);
  - frontend: Vitest 631 og bygg;
  - Playwright: 370 tester.
- **Gjennomgang:** 33 lave funn. 7 ble rettet, og 1 er utsatt til 6.12.
- **Visuell kontroll:** 30 skjermbilder i `screenshots/6.11/`. Ingen klare avvik.
- **Status:** done.

### Åpne punkter
- Issue 129: beslutninger i Story 6.11.

## Story 6.12: Bekrefte ordren og beholde det som er skrevet (2026-11-20)

### Oppgave
Bygge Story 6.12 etter kjøreboka, med testen som ble utsatt fra 6.11.

### Plan
Bygge med `bmad-build-auto`, gjøre en visuell kontroll med Playwright og avslutte.

### Resultat
- **Spec:** `.docs/implementation-artifacts/spec-6-12-confirm-the-order-and-keep-what-i-typed.md`.
- **Commit 77f6111:** ordreruten med `actor` i `place_order`, tilstandene «sender» og «bekreftet» i ordrefeltet, og utkast som tåler ny lasting (`drafts.ts`).
- **Tester:**
  - backend: 2712 tester;
  - frontend: Vitest 638 og bygg;
  - Playwright: 382 tester.
- **Gjennomgang:** 31 lave funn. 6 ble rettet.
- **Visuell kontroll:** 22 skjermbilder i `screenshots/6.12/`. Ett avvik er rettet (7c2e91c).
- **Status:** done.

### Åpne punkter
- Issue 130: beslutninger i Story 6.12.

## Story 6.13: Aldri miste eller doble en ordre ved dårlig forbindelse (2026-11-21)

### Oppgave
Bygge Story 6.13 etter kjøreboka, og rette bruddet før «…» fra Issue #130.

### Plan
Bygge med `bmad-build-auto`, gjøre en visuell kontroll med Playwright og avslutte.

### Resultat
- **Spec:** `.docs/implementation-artifacts/spec-6-13-never-lose-or-double-an-order-on-a-bad-connection.md`.
- **Commit 8821dcd:** sjekk av lagret ordre etter feil, tidsavbrudd etter 10 s med sjekk, tilstand uten nett, og en API-test for kappløp. Ingen endringer i backend-koden.
- **Tester:**
  - backend: 2713 tester;
  - frontend: Vitest 644 og bygg;
  - Playwright: 390 passerte og 1 feilet på en lokator, som er rettet.
- **Gjennomgang:** 37 funn, 5 middels. Byggeagenten anbefaler en oppfølgende gjennomgang.
- **Visuell kontroll:** 26 skjermbilder i `screenshots/6.13/`. Ingen avvik. Hele Playwright-pakken passerte 395/395.
- **Status:** done.

### Åpne punkter
- Issue 131: beslutninger i Story 6.13.

## Story 6.14: Se hvilke plasser som har bestilt, og hvem spillet venter på (2026-11-21)

### Oppgave
Bygge Story 6.14 etter kjøreboka.

### Plan
Bygge med `bmad-build-auto`, og kjøre bare e2e-filene for de berørte skjermene (ny regel). Gjøre en visuell kontroll med full backend-kjøring og avslutte.

### Resultat
- **Spec:** `.docs/implementation-artifacts/spec-6-14-see-which-seats-have-ordered-and-whom-the-game-waits-for.md`.
- **Commit 1230594:** migrasjon 0048 `wait_started_at`, `next_change_at` fra fristene til KI-spillerne, og Setestatus på spillskjermen og Hjem.
- **Tester:**
  - backend: hele pakken passerte i den visuelle kontrollen;
  - frontend: Vitest 653 og bygg;
  - Playwright: 145 målrettede tester.
- **Gjennomgang:** 36 funn, 1 middels. Det middels er rettet.
- **Visuell kontroll:** 23 skjermbilder i `screenshots/6.14/`. Ingen klare avvik; to punkter er samlet til avslutningen av epicet.
- **Status:** done.

### Åpne punkter
- Issue 132: beslutninger i Story 6.14.

## Story 6.15: Se den nye uka innen to sekunder, på alle enheter (2026-11-21)

### Oppgave
Bygge Story 6.15 etter kjøreboka.

### Plan
Måle først, så rette. Gjøre en visuell kontroll og avslutte. To gjennomgangsagenter i stedet for fire.

### Resultat
- **Spec:** `.docs/implementation-artifacts/spec-6-15-see-new-week-within-two-seconds-on-any-device.md`.
- **Commit a95c4cb:**
  - rettingen i `live.ts`; ny uke vises nå etter 385–820 ms, mot 590–706 ms før;
  - oppsummering av ukeovergangen og nå-linja som glir;
  - ruten for lokal lås (`/api/dev/…/lock`).
- **Tester:**
  - backend: 2731 tester (96 s, over grensen);
  - frontend: Vitest 658 og bygg;
  - Playwright: 406 tester i full kjøring.
- **Gjennomgang:** 31 funn, 1 middels. 8 ble rettet.
- **Visuell kontroll:** 29 skjermbilder i `screenshots/6.15/`. Ett avvik er rettet (b1e1c18).
- **Status:** done.

### Åpne punkter
- Issue 133: beslutninger i Story 6.15.
- Backend-pakken er gjort raskere: fra 78,7 s til 59,8 s (commit 17af926).

## Story 6.16: Se hva plassen har kostet så langt (2026-11-21)

### Oppgave
Bygge Story 6.16 etter kjøreboka.

### Plan
Bygge med `bmad-build-auto` og to gjennomgangsagenter, gjøre en visuell kontroll og avslutte.

### Resultat
- **Spec:** `.docs/implementation-artifacts/spec-6-16-see-what-my-seat-has-cost-so-far.md`.
- **Commit 4f3b9cc:**
  - løpende kostnad i motoren (`SeatState` v4);
  - «Kostnad så langt» med graf og tabell, og Alle rader på telefon;
  - panelet på forsiden, og kostnadsaksen i steg på 20 kr.
- **Tester:**
  - backend: 2742 tester (63–69 s);
  - frontend: Vitest 669 og bygg;
  - Playwright: 155 målrettede tester.
- **Gjennomgang:** 23 funn, 1 middels. 5 ble rettet.
- **Visuell kontroll:** 11 skjermbilder i `screenshots/6.16/`. Ett avvik er rettet (ce44a40).
- **CI:** e2e var rød på `student-choice` og `worker-ai`, og er rettet i 07345fa.
- **Status:** done.

### Åpne punkter
- Issue 134: beslutninger i Story 6.16.

## Story 6.17: Se på Hjem om spillet venter på meg (2026-11-21)

### Oppgave
Bygge Story 6.17 etter kjøreboka.

### Plan
Bygge med `bmad-build-auto` og to gjennomgangsagenter, gjøre en visuell kontroll og avslutte.

### Resultat
- **Spec:** `.docs/implementation-artifacts/spec-6-17-see-on-hjem-whether-the-game-waits-for-me.md`.
- **Commit 6885186:** felles spillkort med liten graf og tre rader, tallene for egen plass i Hjem-dataene, og «Spillet venter på deg».
- **Tester:**
  - backend: hele pakken (68 s);
  - frontend: Vitest og bygg;
  - Playwright: de berørte filene.
- **Gjennomgang:** 17 lave funn. 6 ble rettet.
- **Visuell kontroll:** 21 skjermbilder i `screenshots/6.17/`. Ingen klare avvik.
- **CI:** grønn igjen etter rettingen i 07345fa.
- **Status:** done.

### Åpne punkter
- Issue 135: beslutninger i Story 6.17.

## Story 6.18: Se kjedens totalkostnad når spillet er ferdig (2026-11-21)

### Oppgave
Bygge Story 6.18 etter kjøreboka.

### Plan
Bygge med `bmad-build-auto` og to gjennomgangsagenter, gjøre en visuell kontroll og avslutte.

### Resultat
- **Spec:** `.docs/implementation-artifacts/spec-6-18-see-the-chains-total-cost-when-the-game-ends.md`.
- **Commit 36d86e2:**
  - slutten av spillet og steget «klassespill»;
  - resultatruten;
  - sluttskjermen med Kjedens regning og kostnad over tid;
  - linja på Hjem.
- **Tester:**
  - backend: 2746 tester (65 s);
  - frontend: Vitest 687 og bygg;
  - Playwright: de berørte filene.
- **Gjennomgang:** 25 funn, 2 middels. Begge er rettet.
- **Visuell kontroll:** 21 skjermbilder i `screenshots/6.18/`. Ett avvik er rettet (696697e).
- **Status:** done.

### Åpne punkter
- Issue 136: beslutninger i Story 6.18.

## Story 6.19: Foreslå og godta et tidspunkt å spille (2026-11-21)

### Oppgave
Bygge Story 6.19 etter kjøreboka.

### Plan
Bygge med `bmad-build-auto` og to gjennomgangsagenter, gjøre en visuell kontroll og avslutte.

### Resultat
- **Spec:** `.docs/implementation-artifacts/spec-6-19-propose-and-accept-a-time-to-play.md`.
- **Commit 744510f:** migrasjon 0049, `propose_time` og `accept_time`, mail i den daglige oppsummeringen, og forslaget på Hjem og spillsiden.
- **Tester:**
  - backend: 2744 tester (63 s);
  - frontend: Vitest 692 og bygg;
  - Playwright: 57 målrettede tester.
- **Gjennomgang:** 24 funn, 1 middels. Det er rettet.
- **Visuell kontroll:** 29 skjermbilder i `screenshots/6.19/`. Ingen klare avvik.
- **Status:** done.

### Åpne punkter
- Issue 137: beslutninger i Story 6.19.

## Story 6.20: Spille et privat testspill som faglærer (kuttliste, `FEATURE_LECTURER_TEST_GAME`) (2026-11-21)

### Oppgave
Bygge Story 6.20 etter kjøreboka.

### Plan
Bygge med `bmad-build-auto` og to gjennomgangsagenter, gjøre en visuell kontroll og avslutte.

### Resultat
- **Spec:** `.docs/implementation-artifacts/spec-6-20-play-a-private-test-game-as-a-lecturer.md`.
- **Commit 88d136b:** blokken «Testspill» på Klasseøkta, testspill med KI-spillere på spillskjermen til studentene, utelatelse fra lister og sveip (migrasjon 0050), og flagg.
- **Tester:**
  - backend: 2754 tester (70,8 s);
  - frontend: Vitest 692 og bygg;
  - Playwright: 66 målrettede tester.
- **Gjennomgang:** 28 funn. Ett problem ble rettet.
- **Visuell kontroll:** 40 skjermbilder i `screenshots/6.20/`. Ett avvik er rettet (8723631).
- **Status:** done.

### Åpne punkter
- Issue 138: beslutninger i Story 6.20.

## Story 6.21: Se nabotallene som faglæreren har slått på (kuttliste, `FEATURE_INFO_VISIBILITY`) (2026-11-21)

### Oppgave
Bygge Story 6.21 etter kjøreboka.

### Plan
Bygge med `bmad-build-auto` og to gjennomgangsagenter, gjøre en kort visuell kontroll og avslutte.

### Resultat
- **Spec:** `.docs/implementation-artifacts/spec-6-21-see-the-neighbour-numbers-the-lecturer-switched-on.md`.
- **Commit 5596450:** nabotall i `seat_state`, filtrert på serveren, promptversjonen `player_order/v2`, og blokker med nabotall i Kjedebåndet.
- **Tester:**
  - backend: 2770 tester (66 s);
  - frontend: Vitest 699 og bygg;
  - Playwright: 119 målrettede tester.
- **Gjennomgang:** 22 lave funn. 6 ble rettet.
- **Visuell kontroll:** 21 skjermbilder i `screenshots/6.21/`. Ett avvik er rettet (887a1e4).
- **Status:** done.

### Åpne punkter
- Issue 139: beslutninger i Story 6.21. LLM-spillere ser ikke nabotallene før konfigurasjonen flyttes til v2 (sammen med Issue #60).

## Story 6.22: Se kapasiteten i reglene og på en plass med kapasitet (kuttliste, `FEATURE_CAPACITY`) (2026-11-21)

### Oppgave
Bygge Story 6.22, den siste storyen i Epic 6, etter kjøreboka.

### Plan
Bygge med `bmad-build-auto` og to gjennomgangsagenter, gjøre en kort visuell kontroll og avslutte.

### Resultat
- **Spec:** `.docs/implementation-artifacts/spec-6-22-see-the-capacity-in-the-briefing-and-on-a-capped-seat.md`.
- **Commit da35783:** `rules.capacity` i API-et, seksjonen «Kapasitet» i reglene, og radene Lager og Restordre for plassen med kapasitet.
- **Tester:**
  - backend: 2774 tester (66,8 s);
  - frontend: Vitest 713 og bygg;
  - Playwright: 138 målrettede tester.
- **Gjennomgang:** 18 lave funn. 3 ble rettet.
- **Visuell kontroll:** 14 skjermbilder i `screenshots/6.22/`. Ingen avvik.
- **Status:** done.

### Åpne punkter
- Issue 140: beslutninger i Story 6.22.

## Avslutning av Epic 6 (2026-11-21)

### Oppgave
Avslutte Epic 6 etter kjøreboka: oppfølgende gjennomgang, de samlede UX-punktene, testfart og stabil e2e, og deretter PR og merge.

### Plan
1. Gjennomgå logikken i 6.1, 6.4, 6.5 og 6.13 og fem logikkpunkter, og rette de 17 UX-punktene. Disse to delene gikk i parallell.
2. Gjøre e2e raskere og stabil.
3. Lage en PR mot `main`.

### Resultat
- **Oppfølgende gjennomgang:** commits 59824a4–8ab777b.
  - SSE dekket ikke lenger spill studenten har forlatt.
  - API-et viste ikke lenger en plass en annen student hadde overtatt.
  - `order_exists` svarer før `week_not_open`.
  - En medeier ser nye økter uten å koble til på nytt.
  - Sjekken av ferdige spill venter lenger og lenger mellom forsøk når den feiler.
  - Fristen leses under lås.
  - `test_rescue` avhenger ikke lenger av klokka.
- **UX-rettinger:** commits fbd4728, 2950cee, 1c458af og 4603cb7.
  - 16 av 17 punkter er rettet, blant dem norsk datoformat (`--lang=nb-NO`) og feilen der et ferdig spill viste plassene som «venter».
  - Grafstripa i reglene og totalaksen med steget 2,5 er på plass.
  - Skjermbildene ligger i `screenshots/epic-6-avslutning/`.
- **Stabilisering:** commits efc9cb3, 7d86933 og 2ace2cb.
  - En ekte feil i backend: rutene for studenter holdt to tilkoblinger til databasen samtidig, og poolen låste seg når mange sider leste på nytt. Rettet, med en test.
  - Nettleserkontekster som ble liggende åpne etter testene, lukkes nå.
  - En ustabil test for opplasting av klasseliste er rettet.
  - Hele Playwright-pakken gikk fra 7,6 til 4,3 minutter (444 tester), og passerte to ganger på rad rett etter bygget. Backend-pakken tar 66,7 s.
- **Issues:** #119–#140 er lukket.

### Åpne punkter
- Issue #141: tre punkter som er avgjort til senere. Det viktigste er en mulig fastlåsing av LLM-turer, og den hører til Epic 8.
- Issue #139: LLM-spillere bruker `player_order/v2` først etter målingen mot OpenRouter (Issue #60).
- Issue #56 og #60: Story 2.7 og 2.11 står i `review`.
- Issue #31: tekstgjennomgang av alle [ASSUMPTION]-tekster.

## Stopp etter Epic 6: status for kjøringen (2026-11-21)

### Oppgave
Brukeren ba om stopp etter Epic 6 for å kjøre compact før Epic 7.

### Plan
Merge Epic 6 når CI er grønn, lage `epic-7` fra den nye `main`, og stoppe før Story 7.1.

### Resultat
- Epic 1–6 er merget til `main` med grønn CI: PR #49, #65, #83, #96, #118 og #142. `epic-1` til `epic-6` står som `done`.
- Den første CI-kjøringen for PR #142 feilet på én e2e-test (`Response has been disposed`). Årsaken var en route-handler som fortsatt kjørte da testens sider ble lukket. Feilen er rettet i 1e12ffa, og hele pakken passerte 444 av 444.
- `epic-7` er laget fra `main`. Story 7.1 («See the status of every Class game on the Oversikt») står fortsatt i `backlog`.
- 107 stories gjenstår i Epic 7–15. Det er ikke medregnet 3.15, 15.10 og 15.14.

**Stories i `review`:**
- Story 2.7, Issue #56.
- Story 2.11, Issue #60.

**Stories i `blocked`:** ingen.

**Slik fortsetter neste økt:**
- Les kjøreboka med «Lessons from Epics 5–6». Hjelpeskriptene og malene ligger i scratchpad og kan forsvinne. Da må de lages på nytt: `setstatus.ps1`, `finish.ps1`, malene for byggeagenten og den visuelle kontrollen, og lista med punkter til avslutningen av en epic.
- **Byggeagenten** får standardprompten, med disse tilleggene:
  - to gjennomgangsagenter (blind og edge case), eller fire når endringen er risikabel;
  - bare målrettede Playwright-filer; hele pakken kjører i CI;
  - compose startes med `proxy worker-batch worker-ai`;
  - delte fikstrer i `backend/tests/games/helpers.py`;
  - aldri la en live-oppdatering kappløpe med et klikk;
  - ikke levere mens gjennomgangsagentene kjører.
- **Visuell kontroll** gjøres for hver skjermstory, med `--lang=nb-NO`.
- **Underveis** samles punkter til avslutningen av epicen.
- **Avslutning av en epic:**
  1. oppfølgende gjennomgang og UX-punkter, i parallell;
  2. stabilisering med to rene kjøringer av hele pakken;
  3. PR og merge.
- **Hele spillet i Playwright** (GOAL punkt 4): bruk ruten `POST /api/dev/class-sessions/{id}/lock`, som bare finnes lokalt. Den kom i Story 6.15.

### Åpne punkter
- Issue #56 og #60: Story 2.7 og 2.11 står i `review`.
- Issue #141: punkter som står igjen fra Epic 6 og hører til Epic 8.
- Issue #139: LLM-spillere bruker `player_order/v2` først etter målingen i Issue #60.
- Issue #117: punkter som står igjen fra Epic 5.
- Issue #31: tekstgjennomgang av alle [ASSUMPTION]-tekster.

## Story 7.1: Se status for alle klassespill på Oversikt (spor 1)

### Oppgave
Bygge Story 7.1 på `epic-7`, i spor 1 (hovedmappa). Første story med to spor i parallell: spor 2 bygger Epic 9 i `.claude/worktrees/lane-2` med egen stack (8081/5433).

### Plan
Byggeagent med `bmad-build-auto`, to gjennomgangsagenter på Sonnet (blind og edge case), deretter visuell kontroll på Sonnet.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-7-1-see-the-status-of-every-class-game-on-the-oversikt.md`, pluss `epic-7-context.md`.
- Commits: bfd8f8b (storyen og første runde etter gjennomgang), 7483a5d (andre runde).
- Én statusregel (`games.rules.game_status`), lesemodellen `game_summaries` (migrasjon 0051 med utfylling av eksisterende spill), `GET /api/class-sessions/{id}/overview` bak den nye tillatelsen `class_sessions.overview`, og siden `/klasseokter/{id}/oversikt`.
- Tester: backend 2793 på 70 s, Vitest 718, typecheck, `lint:colours`, bygg, Playwright for oversikten og berørte skjermer (47).
- Gjennomgang: 24 funn. Rettet blant annet: ferdige spill viser ikke siste uke (FR-14), ETag godtar `W/` og `*`, sterkere test for faste spørringer, tidsuavhengig e2e. Resten avvist eller utsatt med begrunnelse i specen.
- Gjennomgangsagentene klarte ikke å levere tilbake til byggeagenten. Jeg sendte funnene videre med SendMessage.
- Visuell kontroll (Sonnet): 14 skjermbilder i `screenshots/7.1/`, ingen klare avvik, to små punkter til avslutningen av epicen.
- Status: done.

### Åpne punkter
- Issue #143: beslutninger og utsatte funn (oppfrisking på hver kommando uten budsjett, ingen gjenoppbygging av `game_summaries`, sletting i Epic 15, «pause» i Epic 8).

## Story 9.1: Regn ut fakta om et ferdig spill (spor 2)

### Oppgave
Bygge Story 9.1 på `epic-9` i spor 2 (`.claude/worktrees/lane-2`, egen stack på 8081/5433), samtidig med Epic 7 i spor 1.

### Plan
Byggeagent med `bmad-build-auto` og to gjennomgangsagenter på Sonnet. Ingen skjerm endret, så ingen visuell kontroll.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-9-1-compute-the-facts-of-a-finished-game.md`, pluss `epic-9-context.md` (på `epic-9`).
- Commit: b494185 på `epic-9`.
- Faktasett per spill og sete, tre oppdagede mønstre som én innholdspost med versjon, tre øyeblikk, migrasjon 0101, og `python -m app.sim facts` for simulerte spill.
- Tester: backend 2856, ruff, migrasjon fram og tilbake, Vitest 713, bygg, Playwright 42.
- Gjennomgang: 22 funn, 12 rettet, 8 avvist og 2 utsatt.
- Status: done.

### Åpne punkter
- Issue #144: beslutninger (terskler for mønstrene, øyeblikk, lagring én gang) og leser for gamle faktasett ved ny analyseversjon.

## Story 7.2: Les alle klassespill uke for uke på Matriseveggen (spor 1)

### Oppgave
Bygge Story 7.2 på `epic-7` i spor 1.

### Plan
Byggeagent med `bmad-build-auto`, to gjennomgangsagenter på Sonnet som også skriver funnene til fil, deretter visuell kontroll på Sonnet.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-7-2-read-all-class-games-week-by-week-on-the-matrisevegg.md`.
- Commit: 2a12c33.
- `GET /api/games/{id}/weeks` for stab, med ETag. Matriseveggen som SVG laget for hånd, med `role="grid"` og lesing celle for celle fra tastaturet, på Oversikt og på Landing med demodata.
- Tester: backend 2797, Vitest 736, typecheck, `lint:colours`, `check:copy`, bygg, Playwright 72 med axe på 1440 px, 320 px og 200 % tekst.
- Gjennomgang: 23 funn, 8 rettet (blant dem at rader ble tomme hver gang spillets versjon endret seg), 12 avvist med begrunnelse.
- Visuell kontroll (Sonnet): 11 skjermbilder i `screenshots/7.2/`, ingen avvik. Overskriften på Landing brytes ett ord per linje ved 200 % tekst; den er tatt med i lista til slutten av epicen (gammelt punkt fra Epic 6).
- Status: done.

### Åpne punkter
- Issue #145: beslutninger og risiko (tom rad ved feilet henting til Story 7.5, skjermleser bare sjekket i Chromium).

## Story 9.2: Åpne Debrief når klassespillet er slutt (spor 2)

### Oppgave
Bygge Story 9.2 på `epic-9` i spor 2.

### Plan
Byggeagent med `bmad-build-auto`, to gjennomgangsagenter på Sonnet, deretter visuell kontroll på Sonnet i spor 2 (port 8081).

### Resultat
- Spec: `.docs/implementation-artifacts/spec-9-2-open-the-debrief-when-the-class-game-has-ended.md` (på `epic-9`).
- Commit: 1d9bad6.
- Modulen `debrief` med én regel for når Debrief er åpen, valget «Når Debriefen åpner» på Klasseøkt, frigjøring i sweepen med samlet e-post, og lenker fra «Spillet er ferdig», Stegene og Hjem. Migrasjon 0102.
- Tester: backend 2864 på 69 s, Vitest 719, typecheck, `check:copy`, `lint:colours`, bygg, Playwright 78 på port 8081 med axe i tre bredder.
- Gjennomgang: 19 funn, 4 rettet (blant dem at Debrief-id-er ikke lekker), 1 utsatt, resten avvist med begrunnelse.
- Visuell kontroll (Sonnet, spor 2): 22 skjermbilder i `screenshots/9.2/` (commit e8ae6b9 på `epic-9`), ingen avvik. Valgknappene for «Når Debriefen åpner» står uten mellomrom når de stables; tatt med i lista til slutten av epicen.
- Status: done.

### Åpne punkter
- Issue #146: beslutninger, og at en tilbakeholdt Debrief blir stående hvis et klassespill aldri blir ferdig (Epic 8).

## Story 7.3: Bytt veggen til «Vis som tabell» (spor 1)

### Oppgave
Bygge Story 7.3 på `epic-7` i spor 1.

### Plan
Byggeagent med `bmad-build-auto`, to gjennomgangsagenter på Sonnet, deretter visuell kontroll på Sonnet.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-7-3-switch-the-wall-to-vis-som-tabell.md`.
- Commit: b131971.
- Bare frontend: valget «Visning», tabellen `components/charts/matrix-table.tsx` med sortering og `aria-sort`, og felles posisjon med veggen slik at fokus følger samme spill.
- Tester: backend 2797 på 79 s, Vitest 750, typecheck, `lint:colours`, `check:copy`, bygg, Playwright 54 med axe i tre bredder.
- Gjennomgang: 21 funn, 5 rettet (blant dem at sorteringen forsvant ved bytte av visning), 14 avvist.
- Visuell kontroll (Sonnet): 18 skjermbilder i `screenshots/7.3/`. Rettet fokusringen på radoverskriftene, som ikke tegnet noe (9e1a4fc). Tre avvik går til Story 7.4 på samme side: «Visning» står som en blokk på 450 px over veggen i stedet for et lite valg ved siden av, tabellen er bare 590 px bred ved 1280 px, og «Venter på» brytes over 3–4 linjer.
- Status: done.

### Åpne punkter
- Issue #147: beslutninger og risiko (tastaturnavigasjon med flere spill bare testet i Vitest).

## Story 9.3: Skriv Forklaringen før avsløringen (spor 2)

### Oppgave
Bygge Story 9.3 på `epic-9` i spor 2.

### Plan
Byggeagent med `bmad-build-auto`, to gjennomgangsagenter på Sonnet, deretter visuell kontroll på Sonnet i spor 2.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-9-3-write-the-explanation-before-the-reveal.md` (på `epic-9`).
- Commit: 18c2974.
- Migrasjon 0103 med én Forklaring per student og klasseøkt, lagret én gang og låst. Senere steg krever Forklaringen. Steg 1 viser studentens netto lager over hele spillet med «Vis som tabell», skrivefeltet og «Send Forklaring».
- Tester: backend 2861 på 72 s, Vitest 725, typecheck, `check:copy`, `lint:colours`, bygg, Playwright 66 med axe.
- Gjennomgang: 21 funn, 3 rettet (feilmelding og «Prøv igjen» når lesing feiler, test for 409, ødelagte norske tegn i en testfil), 18 avvist.
- Visuell kontroll (Sonnet, spor 2): 15 skjermbilder i `screenshots/9.3/` (e6c6c85), ingen klare avvik. Ukestripen fra mockupen er utelatt med vilje (beslutning 7). Tabellvisningen har ingen høydegrense og skyver skrivefeltet langt ned på mobil; det går til Story 9.4 på samme side.
- Status: done.

### Åpne punkter
- Issue #148: beslutninger (låst Forklaring, maks 5000 tegn, endepunkter for steg 2–5).

## Story 9.4: Se avsløringen av kundeetterspørselen (spor 2)

### Oppgave
Bygge Story 9.4 på `epic-9` i spor 2, og rette tabellhøyden på steg 1 fra den visuelle kontrollen av 9.3.

### Plan
Byggeagent med `bmad-build-auto`, to gjennomgangsagenter på Sonnet, deretter visuell kontroll på Sonnet i spor 2.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-9-4-see-the-reveal-of-customer-demand.md` (på `epic-9`).
- Commits: 2ce357c (storyen), 066fd73 (byggeagentens skjermbilder).
- Steg 2 med avsløringen: overskrift laget av kode fra etterspørselsrekken med setningsmaler (ny innholdstype `sentence_templates`, migrasjon 0104), Etterspørselsbåndet over tabellen med Kundene, Ordre inn og Din ordre, og «Øvelsen heter Beer Game.». Tabellen på steg 1 har nå høydegrense.
- Tester: backend 2884 på 69 s, Vitest 732, typecheck, `lint:colours`, `check:copy`, bygg, Playwright 117 med axe.
- Gjennomgang: 27 funn, 7 rettet (blant dem at plassholderne i malene må være rene navn).
- `week-advance` feilet én gang på tidskravet mens begge sporene kjørte, og passerte alene.
- Visuell kontroll (Sonnet, spor 2): ti skjermbilder i `screenshots/9.4/` (b331cfc). Rettet at ukene 34–36 lå bak sidelengs rulling ved 1280 px (5b94e3a). Nøkkel over båndet og alle ukenummer som kolonneoverskrifter avviker fra mockupen, men følger specen.
- Status: done.

### Åpne punkter
- Issue #149: beslutninger (setningsmaler, valg av overskrift, plassering av steg 2).

## Story 7.4: Filtrer veggen og sammenlign med medianen for klassen (spor 1)

### Oppgave
Bygge Story 7.4 på `epic-7` i spor 1, og rette tre layoutfeil fra den visuelle kontrollen av 7.3 på samme side.

### Plan
Byggeagent med `bmad-build-auto`, to gjennomgangsagenter på Sonnet, deretter visuell kontroll på Sonnet.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-7-4-filter-the-wall-and-compare-with-the-class-median.md`.
- Commit: 9cfb9d6.
- Filtre for Rolle, Celler og Status, fargeskala for flyt, `GET /api/class-sessions/{id}/overview/aggregates` med median, midterste halvdel og snitt, og mediangraf over ukekolonnene. De tre layoutfeilene fra 7.3 er rettet.
- Tester: backend 2809 (74 s og 94 s, trolig mens spor 2 kjørte samtidig), Vitest 762, typecheck, bygg, Playwright for oversikt, landing og ordre med axe.
- Gjennomgang: 20 funn, 6 rettet, resten avvist.
- Én uforklart feil i en backend-kjøring og én ustabil `homes`-test ved 360 px; begge passerte ved ny kjøring.
- Visuell kontroll (Sonnet): 18 skjermbilder i `screenshots/7.4/` med tre spill, ingen klare avvik. De tre layoutfeilene fra 7.3 er bekreftet rettet. «Venter på …» kuttes ved høyre kant av veggen ved 390 px; det står på lista til slutten av epicen.
- Status: done.

### Åpne punkter
- Issue #150: beslutninger, tid på backend-pakken med to spor, og to ustabile tester til stabiliseringen.

## Story 7.5: Følg spillene live med «Oppdater automatisk» (spor 1)

### Oppgave
Bygge Story 7.5 på `epic-7` i spor 1, og lukke de utsatte punktene fra 7.1 og 7.2 om feilet henting og om Startdatoen.

### Plan
Byggeagent med `bmad-build-auto`, to gjennomgangsagenter på Sonnet, deretter visuell kontroll på Sonnet.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-7-5-follow-the-games-live-with-oppdater-automatisk.md`.
- Commit: c4d928b.
- Ny lesing med ETag, bryteren «Oppdater automatisk», «N endringer siden hh:mm» når den er av, rader som står stille mens fokus er i veggen, høflig opplesing av tallene, egne tilkoblingslinjer, nye forsøk hvert 10. sekund og ny lesing ved Startdatoen (`next_change_at`).
- Tester: backend 2809 på 97,5 s (mens spor 2 kjørte samtidig), Vitest 776, typecheck, `lint:colours`, `check:copy`, bygg, Playwright 47 uten ustabile tester.
- Gjennomgang: 20 funn, 4 rettet (1 middels), 14 avvist.
- Visuell kontroll (Sonnet): 13 skjermbilder i `screenshots/7.5/`, ingen avvik. Tilkoblingslinjene følger reglene i EXPERIENCE.md.
- Status: done.

### Åpne punkter
- Issue #151: beslutninger, og tiden på backend-pakken når to spor kjører samtidig.

## Story 9.5: Skrubb gjennom hele kjeden og se forsterkningen (spor 2)

### Oppgave
Bygge Story 9.5 på `epic-9` i spor 2.

### Plan
Byggeagent med `bmad-build-auto`, to gjennomgangsagenter på Sonnet, deretter visuell kontroll på Sonnet i spor 2.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-9-5-scrub-the-whole-chain-and-see-the-amplification.md` (på `epic-9`).
- Commit: b54b964.
- Steg 3 i Debrief: Ukeskrubberen, Kjedebåndet med alle fire roller, Ordrestolper over tallene per rolle og uke, og Forsterkning. Ordrestolpene og tabellen er felles komponenter som Story 7.8 skal gjenbruke.
- Tester: backend 2880, Vitest 747, typecheck, `lint:colours`, `check:copy`, bygg, Playwright 123.
- Gjennomgang: 24 funn, 13 rettet, 6 falske, ingenting utsatt.
- `test_ai/test_effort` og `week-advance` feilet én gang hver og passerte ved ny kjøring.
- Visuell kontroll (Sonnet, spor 2): ti skjermbilder i `screenshots/9.5/` (4b20820). Rettet at Forsterkning-kolonnen lå utenfor synsfeltet ved 1280 px, og at fokusringen på skrubberen dekket ukeetikettene (f9cc374). Kjedebåndet er begrenset til 56 rem ved 1280 px; går til Story 9.6 på samme side.
- Status: done.

### Åpne punkter
- Issue #152: beslutninger, felles komponenter for Story 7.8, og to ustabile tester.

## Story 9.6: Svar på refleksjonsspørsmålene (spor 2)

### Oppgave
Bygge Story 9.6 på `epic-9` i spor 2, og la Kjedebåndet på steg 3 få full bredde (fra den visuelle kontrollen av 9.5).

### Plan
Byggeagent med `bmad-build-auto`, to gjennomgangsagenter på Sonnet, deretter visuell kontroll på Sonnet i spor 2.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-9-6-answer-the-reflection-questions.md` (på `epic-9`).
- Commit: 0688d38.
- Tre refleksjonsspørsmål som innhold med versjon (migrasjon 0105), ett om gangen, med utkast som blir tatt vare på. Svar kan ikke endres. Kjedebåndet på steg 3 har nå full bredde.
- Tester: backend 2886 på 70 s, Vitest 750, typecheck, `lint:colours`, `check:copy`, bygg, Playwright 129, ingen ustabile tester.
- Gjennomgang: 28 funn, ingen høye eller middels, 4 rettet.
- Visuell kontroll (Sonnet, spor 2): 13 skjermbilder i `screenshots/9.6/` (1ef3c11), ingen avvik. Kjedebåndet har bekreftet full bredde. Refleksjonsdelen står i en smal kolonne som steg 1; skrivefelt i lesebredde er et rimelig valg.
- Status: done.

### Åpne punkter
- Issue #153: beslutninger (midlertidige spørsmål til Issue #16, svar som ikke kan endres, ingen skjerm for lærerne ennå).

## Story 7.6: Se hvem som venter, klassens kostnad og trakten i høyre kolonne (spor 1)

### Oppgave
Bygge Story 7.6 på `epic-7` i spor 1, og rette at «Venter på …» kuttes ved 390 px.

### Plan
Byggeagent med `bmad-build-auto`, to gjennomgangsagenter på Sonnet, deretter visuell kontroll på Sonnet.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-7-6-see-who-waits-the-class-cost-and-the-funnel-in-the-right-rail.md`.
- Commit: 59f10fe.
- Høyre kolonne med «Venter ellers», «Klassens kostnad» (Kostnadsfordeling som SVG, tabell, stolper per rolle) og «Trakt». Ny ren funksjon `analysis.class_cost` og `progress.service.funnel` med hurtigbuffer. Kort merknad i veggen ved 390 px. Ingen migrasjon.
- Tester: backend 2815 på 71 s, Vitest 785, typecheck, `lint:colours`, `check:copy`, bygg, Playwright 48.
- Gjennomgang: 27 funn, 2 middels (samme uendelige løkke i aksen, funnet av begge, rettet), 6 lave rettet, 1 utsatt.
- `week-advance` feilet én gang på grensen på 2 s mens gjennomgangsagentene kjørte; tredje gang denne testen er ustabil.
- Visuell kontroll (Sonnet): 20 skjermbilder i `screenshots/7.6/`. Rettet at høyre kolonne klemte spillradene til én bokstav per linje ved 200 % tekst og at radene var trange ved 1024 px (49153fc). «min» i «Venter ellers» brytes med lange navn; tatt med i lista til slutten av epicen.
- Orkestratoren satte grensen i `week-advance` til 3 s lokalt og 2 s i CI (d9201b9).
- Status: done.

### Åpne punkter
- Issue #154: beslutninger og den ustabile `week-advance`-testen.

## Story 9.7: Se egne øyeblikk, laget fra faktasettet (spor 2)

### Oppgave
Bygge Story 9.7 på `epic-9` i spor 2.

### Plan
Byggeagent med `bmad-build-auto`, to gjennomgangsagenter på Sonnet, deretter visuell kontroll på Sonnet i spor 2.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-9-7-see-my-own-moments-rendered-from-the-facts.md` (på `epic-9`).
- Commit: 26d2e33. I tillegg 07e2db3 (grensen i `week-advance` fra spor 1, plukket inn).
- Steg 4: tre egne øyeblikk, ett om gangen, med setninger fylt inn av kode fra faktasettet, grafen over tabellen i den uken, mønsteret, hva de andre så, og studentens egen Forklaring ved siden av. Ny innholdstype `moment_templates` (migrasjon 0106) og tabellen `debrief_fact_sets`.
- Tester: backend 2908 på 81 s (kjørt av orkestratoren etter byggeagentens siste retting), Vitest 752, typecheck, bygg, Playwright 134.
- Gjennomgang: 23 funn, ingen høye eller middels, 4 rettet.
- Ti e2e-tester feilet i én kjøring mens gjennomgangsagentene kjørte, og passerte ved ny kjøring.
- Visuell kontroll (Sonnet, spor 2): ti skjermbilder i `screenshots/9.7/` (a36cd06). Rettet at tabellen «Dette så de andre i Uke N» rullet hele siden sidelengs ved 200 % tekst (e2a559d). Tabell i stedet for linjer som i mockupen er beholdt.
- Status: done.

### Åpne punkter
- Issue #155: beslutninger og ustabile e2e-tester under last.

## Story 7.7: Åpne ett spill uke for uke i Spillinnsikt (spor 1)

### Oppgave
Bygge Story 7.7 på `epic-7` i spor 1, og bruke felles komponenter fra `epic-9` der de trengs.

### Plan
Byggeagent med `bmad-build-auto`, to gjennomgangsagenter på Sonnet, deretter visuell kontroll på Sonnet.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-7-7-open-one-game-week-by-week-in-spillinnsikt.md`.
- Commit: 569ffab.
- `GET /api/games/{id}/insight` bare for stab, med ETag; merker for alle årsaker til at et sete skifter; siden `/klasseokter/{id}/oversikt/spill/{gameId}` med tabeller per rolle og fokus tilbake til samme spill. `scroll-region.tsx` hentet uendret fra `epic-9`.
- Tester: backend 2835 (første kjøring hadde 1175 tidsavbrudd mot databasen mens begge sporene kjørte; ny kjøring passerte), Vitest 794, typecheck, `lint:colours`, `check:copy`, bygg, Playwright 50.
- Gjennomgang: 26 funn, 1 middels og 8 lave rettet.
- Åtte e2e-tester feilet én gang på tidsavbrudd for e-post og passerte ved ny kjøring.
- Visuell kontroll (Sonnet): elleve skjermbilder i `screenshots/7.7/`, ingen avvik. Matrisen og grafene fra mockupen kommer i Story 7.8. En overview-test var ustabil i en samlet kjøring under last.
- Status: done.

### Åpne punkter
- Issue #156: beslutninger og last fra to spor på samme maskin.

## Story 7.8: Se ordre, lager og restordre for alle fire roller som grafer i Spillinnsikt (spor 1)

### Oppgave
Bygge Story 7.8 på `epic-7` i spor 1, med de felles komponentene fra `epic-9` (Story 9.5).

### Plan
Byggeagent med `bmad-build-auto`, to gjennomgangsagenter på Sonnet, deretter visuell kontroll på Sonnet.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-7-8-see-all-four-roles-orders-inventory-and-backlog-as-charts-in-spillinnsikt.md`.
- Commit: 72a9cbf.
- «Kjeden i grafer» i Spillinnsikt: Ordrestolper over tallene per rolle og uke med «Kundene» nederst, og en ny felles graf for lager og restordre med ett bånd per rolle. Begge har «Vis som tabell». `first_large_order_week` per rolle fra endepunktet.
- Felles komponenter: `order-bars.tsx` hentet uendret fra `epic-9`; `order-bars-table.tsx` med én liten tilføyelse (Forsterkning valgfri). Notert til merge.
- Tester: backend 2835, Vitest 806, typecheck, `lint:colours`, `check:copy`, bygg, Playwright 50, ingen ustabile tester.
- Gjennomgang: 14 funn, ingen høye eller middels, 3 rettet.
- Visuell kontroll (Sonnet): ni skjermbilder i `screenshots/7.8/` med et spill på 22 uker. Rettet ujevne ukekolonner i tabellene (b88ae24). Tre punkter til avslutningen av epicen: «Lager og restordre» mangler verdietiketter, `ScrollRegion` toner kantene selv om DESIGN.md sier nei til fading, og røde ukemerker i Ordrestolpene står tett ved 390 px.
- Status: done.

### Åpne punkter
- Issue #157: beslutninger og punkter til merge av `epic-7` og `epic-9`.

## Story 9.8: Se kjedens regning og fullfør Debrief (spor 2)

### Oppgave
Bygge Story 9.8 på `epic-9` i spor 2.

### Plan
Byggeagent med `bmad-build-auto`, to gjennomgangsagenter på Sonnet, deretter visuell kontroll på Sonnet i spor 2. Byggeagenten spurte om å merge `epic-7` for lenkepunktet fra Story 7.7; jeg sa nei og godkjente en registrering som bare skjer når lenkepunktet finnes, og som gjøres ubetinget ved merge.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-9-8-see-the-chains-bill-and-finish-the-debrief.md` (på `epic-9`).
- Commit: b3e9488.
- «Kjedens regning» med simulerte rader fra en ren simulering i faktasettet (analyseversjon 2), «Fullfør Debriefen» med `debrief_summaries` (migrasjon 0107), og en side der stab leser Forklaring og oppsummering.
- Tester: backend 2912, Vitest 757, Playwright 144 med axe, ingen ustabile tester, ingen nye over 1 s.
- Commit 719b43e: sjekken for lenkepunktet fra Story 7.7 samlet på ett sted, med TODO til merge.
- Visuell kontroll (Sonnet, spor 2): 16 skjermbilder i `screenshots/9.8/` (9a25f4e), ingen avvik. Ved 200 % tekst og 390 px ruller regningstabellen i sin egen beholder, slik «Spillet er ferdig» gjør.
- Status: done.

### Åpne punkter
- Issue #158: beslutninger, simulerte kostnader med plassholderparametre, og lenkene i Spillinnsikt etter merge.

## Story 7.9: Send en Melding til en student, et klassespill eller hele klasseøkta (spor 1)

### Oppgave
Bygge Story 7.9 på `epic-7` i spor 1.

### Plan
Byggeagent med `bmad-build-auto`, to gjennomgangsagenter på Sonnet, deretter visuell kontroll på Sonnet.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-7-9-send-a-message-to-a-student-a-class-game-or-the-whole-class-session.md`.
- Commit: f553c6b. Migrasjon 0052_messages.
- Meldingsskjemaet på `/klasseokter/{id}/melding`, åpnet fra Oversikt, Spillinnsikt og hvert sete. Én transaksjon lagrer meldingen, mottakerne og varslene, og hver student får e-post. En nøkkel fra klienten hindrer dobbel sending.
- Tester: backend 2842, Vitest 812, typecheck, `lint:colours`, `check:copy`, bygg, Playwright 52 med `--workers=4`, ingen ustabile tester.
- Gjennomgang: 29 funn, 2 middels (en importløkke som krasjet, rettet), 6 lave rettet.
- Visuell kontroll (Sonnet): 33 skjermbilder i `screenshots/7.9/`, ingen avvik. Felles sidehode brytes over to linjer ved 390 px (ikke denne storyen); tatt med i lista til slutten av epicen.
- Status: done.

### Åpne punkter
- Issue #159: beslutninger (mottakere, 403 for utenforstående, nøkkel mot dobbel sending).

## Story 9.9: Bestå Debrief-quizen (spor 2)

### Oppgave
Bygge Story 9.9 på `epic-9` i spor 2.

### Plan
Byggeagent med `bmad-build-auto`, to gjennomgangsagenter på Sonnet, deretter visuell kontroll på Sonnet i spor 2.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-9-9-pass-the-debrief-quiz.md` (på `epic-9`).
- Commit: 93444ab.
- Steg 5 «Debrief-quiz» med ny innholdstype `debrief_quiz` (midlertidige spørsmål), poeng regnet bare på serveren, forsøk som ikke kan endres (`quiz_attempts`, migrasjon 0108), og `quiz_passed` i samme transaksjon. Komponenten Quizvalg i `components/quiz-choice.tsx`.
- Tester: backend 2932, Vitest 763, typecheck, `lint:colours`, `check:copy`, bygg, Playwright 149 med `--workers=4`, ingen ustabile tester.
- Gjennomgang: 23 funn, ingen høye eller middels, 5 rettet.
- Visuell kontroll (Sonnet, spor 2): 24 skjermbilder i `screenshots/9.9/` (9dfae1f). Rettet at «Ditt svar, ikke riktig» ble kuttet og at «−13» ble delt ved 200 % tekst (1230385).
- Status: done.

### Åpne punkter
- Issue #160: beslutninger (midlertidige spørsmål til Issue #16, stokking ved nye forsøk, ingen nye forsøk etter bestått).

## Story 7.10: Les Meldinger i appen (spor 1)

### Oppgave
Bygge Story 7.10 på `epic-7` i spor 1, og legge til en test for importrekkefølgen i `messaging.messages` (fra 7.9).

### Plan
Byggeagent med `bmad-build-auto`, to gjennomgangsagenter på Sonnet, deretter visuell kontroll på Sonnet.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-7-10-read-messages-in-the-product.md`.
- Commit: 2a4652b. Ingen migrasjon.
- Studenter: «Meldinger» på Hjem etter klassene, nyeste først, oppdatert live. Stab: siden `/klasseokter/{id}/meldinger`. Nytt hjelpemiddel for tilgang, `authz.messages_addressed_to`.
- Tester: backend 2849, Vitest 817, typecheck, `lint:colours`, `check:copy`, bygg, Playwright 66 etter ny bygging av stacken, ingen ustabile tester. Ny importtest i en fersk tolk (2,8 s).
- Gjennomgang: 23 funn, ingen høye eller middels, 7 rettet (blant dem at arkiverte klasser holdes utenfor for studenter).
- Visuell kontroll (Sonnet): 15 skjermbilder i `screenshots/7.10/`, ingen avvik. Klassenavnet for en student med to klasser er verken fotografert eller dekket av en test; tatt med i lista til slutten av epicen.
- Status: done.

### Åpne punkter
- Issue #161: beslutninger (ingen lest-status, tak på 100 og 200 meldinger uten sider, tilgang for fjernede studenter).

## Story 9.10: Utelat et quizspørsmål og se quizforsøk (spor 2)

### Oppgave
Bygge Story 9.10 på `epic-9` i spor 2, og avgjøre om stabssiden for Debrief fra 9.8 skal vise navnet på studenten.

### Plan
Byggeagent med `bmad-build-auto`, to gjennomgangsagenter på Sonnet, deretter visuell kontroll på Sonnet i spor 2. Byggeagenten ble stoppet én gang av en feil med abonnementet og startet igjen.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-9-10-exclude-a-quiz-question-and-see-quiz-attempts.md` (på `epic-9`).
- Commit: 2001f84.
- Eiere kan utelate quizspørsmål på Klasseøkt med «Lagre quizvalg» (`quiz_exclusions`, migrasjon 0109, revisjonslogg). Studentene får bare de gjenværende spørsmålene, og de som berøres får e-post og en linje på Hjem. Stabssiden viser nå navnet på studenten og alle quizforsøk.
- Tester: backend 2940, Vitest 767, typecheck, `lint:colours`, `check:copy`, bygg, Playwright 259 etter ny bygging av stacken, ingen ustabile tester.
- Gjennomgang: 32 funn, ingen høye eller middels, 7 rettet.
- Visuell kontroll (Sonnet, spor 2): 27 skjermbilder i `screenshots/9.10/` (463a8ac), ingen avvik. Kolonnene for spørsmålene på Klasseøkt flukter ikke helt ved 1280 px; tatt med i lista til slutten av epicen.
- Status: done.

### Åpne punkter
- Issue #162: beslutninger (navn på stabssiden etter FR-47, egen lagreknapp, hvem som varsles).

## Story 7.11: Handle på spillet som har ventet lengst, fra Varselbåndet (spor 1)

### Oppgave
Bygge Story 7.11 på `epic-7` i spor 1, den siste storyen i Epic 7.

### Plan
Byggeagent med `bmad-build-auto` og to gjennomgangsagenter på Sonnet. Den visuelle kontrollen gjøres av agenten som avslutter Epic 7, etter den nye flyten i kjøreboka («Faster flow»).

### Resultat
- Spec: `.docs/implementation-artifacts/spec-7-11-act-on-the-longest-waiting-game-from-the-varselband.md`.
- Commit: 114331e. Ingen migrasjon.
- Overview-svaret velger spillet som har ventet lengst (`alert`). Varselbåndet viser «Spill 2 venter på Noah (Grossist) i 23 t.» med «Send Melding» til den studenten, leses høflig opp maks én gang i minuttet og står stille når «Oppdater automatisk» er av. Raden er markert i vegg, tabell og spilliste, og hver rad har «Melding» til sitt klassespill.
- Tester: backend 2857, Vitest 829, typecheck, `lint:colours`, `check:copy`, bygg, Playwright 69 i ti spesifikasjoner, ingen ustabile tester.
- Gjennomgang: 20 funn, ingen høye eller middels, 3 rettet.
- Visuell kontroll: gjøres i avslutningen av Epic 7.
- Status: done.

### Åpne punkter
- Issue #163: beslutninger (hvem båndet nevner, likhet mellom spill, plassering av «Melding»).

## Story 8.1: Registrer når hver uke åpnet og når hvert sete bestilte (spor 1)

### Oppgave
Bygge Story 8.1 på `epic-8` i spor 1. `epic-8` er laget fra den ferdige `epic-7`, mens avslutningen av Epic 7 kjører i et eget worktree.

### Plan
Byggeagent med `bmad-build-auto` og fire gjennomgangsagenter på Sonnet (datamodell). Neste byggeagent ble startet med en gang storyen var committet, etter den nye flyten.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-8-1-record-when-week-opened-and-seat-ordered.md`.
- Commit: 8b940a2. Migrasjon 0053 med utfylling for spill som allerede venter.
- Spillet har sin egen klokke for FR-36: frister for overtakelse og innsetting per tur, nærmeste frist i `game_summaries`, `next_change_at` fra lesemodellen, og tre nye kolonner i Spillinnsikt.
- Tester: backend 2880, Vitest 830, typecheck, `lint:colours`, `check:copy`, bygg, Playwright 73 med `--workers=4`, ingen ustabile tester.
- Gjennomgang: 42 funn, 3 middels (utfyllingen for spill i gang, rettet), 5 lave rettet, 1 utsatt til 8.9.
- Visuell kontroll: tas sammen med neste visuelle kontroll av Spillinnsikt, for å unngå fire stacker samtidig.
- Status: done.

### Åpne punkter
- Issue #164: beslutninger og utsatte punkter.

## Avslutning av Epic 7

### Oppgave
Avslutte Epic 7 (7.1–7.11) med visuell kontroll av 7.11, oppfølgende rettinger, stabilisering, PR og CI, i et eget worktree mens spor 1 startet Epic 8 og spor 2 bygde Epic 9.

### Plan
Én agent i `.claude/worktrees/epic7` med egen stack (8090/5434), etter «Faster flow» i kjøreboka. Orkestratoren merget etter grønn CI.

### Resultat
- Visuell kontroll av 7.11 i `screenshots/7.11/`, og bilder etter rettingene i `screenshots/epic-7-avslutning/`.
- Rettinger (6c31495, 06486a0): «Fordeling 0» og avstand i «Ikke startet», overskriften på Landing ved 200 % tekst, harde mellomrom i ventetider, verdietiketter i «Lager og restordre», `ScrollRegion` uten fading (1 px linje og synlig rullefelt), sidehodet på én linje ved 390 px, e2e for en student i to klasser, og `nextMail` som venter på bestemt tekst.
- Hele Playwright-pakken passerte to ganger på rad, 464 av 464. Vitest 830, typecheck, `lint:colours`, `check:copy` og bygg passerte.
- Backend-pakken ble ikke raskere: 121–162 s mens to andre agenter brukte maskinen. Summen av testtidene er 755 s, så 8 prosesser kan ikke komme mye under 94 s. Det trengs felles, ferdigspilte spill som fikstur.
- PR #165 med grønn CI, merget til `main`. `epic-7` satt til done.

### Åpne punkter
- Issue #166: utsatte punkter fra Epic 7 (gjenoppbygging av `game_summaries`, hendelse ved endring i klasselista, gruppe for «pause» i Epic 8, fart på backend-pakken, mindre UX-punkter, én test i `test_place_order.py` som feilet én gang under last).

## Story 9.11: Gå gjennom Debrief sammen som gruppe (spor 2)

### Oppgave
Bygge Story 9.11 på `epic-9` i spor 2.

### Plan
Byggeagent med `bmad-build-auto` og to gjennomgangsagenter på Sonnet. Etter den nye flyten startet byggeagenten for 9.12 med en gang, og den visuelle kontrollen gikk samtidig i et eget worktree med egen stack, bare med rapport.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-9-11-go-through-the-debrief-together-as-a-group.md` (på `epic-9`).
- Commit: d23993b. Migrasjon 0110.
- Felles Debrief når minst to studenter er aktive: felles steg 1–3, «Ferdig med steget», åpneren kan flytte alle videre etter en ventetid, låste steg i api-et (403 `step_locked`), og `debrief:<id>` videresendt til nettleseren.
- Tester: backend 2939, Vitest 773, typecheck, `lint:colours`, `check:copy`, bygg, Playwright 118 med `--workers=4`, ingen ustabile tester. Én backend-kjøring hang mens Docker bygde ved siden av; ny kjøring alene passerte.
- Gjennomgang: 28 funn, 5 lave rettet, 1 middels sendt videre til 9.12 (gruppe uten åpner kan ikke gå videre).
- Visuell kontroll (Sonnet, bare rapport, eget worktree og egen stack): 42 skjermbilder i `screenshots/9.11/`, ingen klare feil i 9.11. Tre punkter sendt til 9.12 på samme side: ingen fylt primærknapp i gruppelinja, samme klokkeslett vist to ganger, og en kuttet etikett i grafen på steg 2 i korte spill.
- Status: done.

### Åpne punkter
- Issue #167: beslutninger (felles steg 1–3, ventetid på 5 min som plassholder, varsling).

## Story 8.2: En KI-spiller tar over etter Inaktivitetsgrensen (spor 1)

### Oppgave
Bygge Story 8.2 på `epic-8` i spor 1.

### Plan
Byggeagent med `bmad-build-auto` og fire gjennomgangsagenter på Sonnet (samtidighet). Etter storyen merget orkestratoren `main` (avslutningen av Epic 7) inn i `epic-8`, løste én konflikt i `nb.ts` og kjørte typecheck, Vitest og `check:copy` (d52d84c). Neste byggeagent startet før den visuelle kontrollen.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-8-2-ai-player-takes-over-after-inactivity-limit.md`.
- Commit: 159838f. Migrasjon 0054.
- Sweepen gir et sete til en KI-spiller etter Inaktivitetsgrensen, ett sete per transaksjon; KI-spilleren bestiller med en gang og alle studentene får e-post. «KI-spiller bestiller for Jonas» på Spill og Hjem, og «KI-spiller har bestilt for deg.» i stedet for Ordrefeltet.
- Tester: backend 2907, Vitest 838, typecheck, `check:copy`, `lint:colours`, bygg, Playwright 94 med `--workers=4`, ingen ustabile tester.
- Gjennomgang: 38 funn, 5 middels, alle rettet. Punkt 2 i Issue #141 er løst.
- Visuell kontroll av 8.1 og 8.2 (Sonnet, bare rapport, eget worktree og egen stack): 21 skjermbilder i `screenshots/8.2/`, ingen klare feil. Til Story 8.4 på samme skjerm: lenken «Alle rader og kostnad» forsvinner ved 1280 px når setet er tatt over, og «Din ordre 9» viser KI-spillerens ordre som om den var studentens.
- Status: done.

### Åpne punkter
- Issue #168: beslutninger, og oppfølgende gjennomgang anbefalt til slutten av Epic 8.

## Story 9.12: Fortsett alene når gruppen ikke er der (spor 2)

### Oppgave
Bygge Story 9.12 på `epic-9` i spor 2, med det utsatte punktet fra 9.11 (gruppe uten åpner) og tre visuelle rettinger fra kontrollen av 9.11.

### Plan
Byggeagent med `bmad-build-auto` og fire gjennomgangsagenter i to runder. Den blinde gjennomgangen klarte ikke å levere tilbake; orkestratoren pekte byggeagenten til filen. Visuell kontroll som bare rapporterer, i eget worktree.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-9-12-continue-alone-when-the-group-is-not-there.md` (på `epic-9`).
- Commit: f93c388. Migrasjon 0111.
- En student i gruppedebrief går videre alene ved å forlate gruppen, ved frafall etter 2 min uten hjerteslag, ved tilbakefall etter 48 timer, eller når gruppen allerede har passert steg 3. Den som ble med først kan flytte gruppen videre når åpneren er borte.
- Tester: backend 2946, Vitest 776, typecheck, `check:copy`, `lint:colours`, bygg, Playwright 136 av 137 (`order-confirm` feilet én gang og passerte ved ny kjøring).
- Gjennomgang: 18 rettet (2 middels), 1 lavt utsatt.
- Visuelle rettinger fra kontrollen av 9.11 (1b33fb5): én fylt primærknapp i gruppelinja, klokkeslettet vises én gang, og grafen på steg 2 klemmes ikke i korte spill. Playwright 137 av 137 etterpå.
- Visuell kontroll (Sonnet, bare rapport, eget worktree): skjermbilder i `screenshots/9.12/`, tatt av f93c388, altså før 1b33fb5; de tre funnene den rapporterte er rettet der. Nytt punkt: i bekreftelsen av «Forlat gruppen» har de to knappene samme stil; tatt med i lista til slutten av epicen.
- Status: done.

### Åpne punkter
- Issue #169: beslutninger, og at 48 timer regnes fra spillets slutt (en tilbakeholdt Debrief kan falle tilbake med én gang).

## Story 8.3: Se på Oversikt hvilket klassespill som er nærmest overtakelse (spor 1)

### Oppgave
Bygge Story 8.3 på `epic-8` i spor 1. Første story etter at `main` (avslutningen av Epic 7) ble merget inn i `epic-8`.

### Plan
Byggeagent med `bmad-build-auto` og to gjennomgangsagenter på Sonnet. Neste byggeagent (8.4) startet med en gang; den visuelle kontrollen venter til den forrige kontrollens stack er ledig.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-8-3-see-on-the-oversikt-which-class-game-is-closest-to-takeover.md`.
- Commit: 007e8e9. Ingen migrasjon.
- Varselbåndet viser spillet med tidligste frist for overtakelse og teller ned («KI overtar om 1 t.», «KI overtar nå.»). Seter med KI-spiller får merke i tekst på Oversikt og i Spillinnsikt.
- Tester: backend 2916, Vitest 842, typecheck, `lint:colours`, `check:copy`, bygg, Playwright 138 av 139 (`homes` ved 320 px feilet én gang og passerte ved ny kjøring). Rettet et regex med hardt mellomrom som merge med `main` hadde ødelagt.
- Gjennomgang: 25 funn, ingen høye eller middels, 3 lave rettet.
- Byggeagenten endret ved en feil linjeslutt i 15 skjermbilder fra 8.2 og satte dem tilbake til innholdet i HEAD; git ser dem som uendret.
- Visuell kontroll (Sonnet, bare rapport, eget worktree): 15 skjermbilder i `screenshots/8.3/`, ingen klare feil. «Pause spillet» og «Sett inn KI-spiller» i båndet kommer med 8.5 og 8.6. Fargen på raden i spillista går 8 px forbi venstre marg; tatt med i lista til slutten av epicen.
- Status: done.

### Åpne punkter
- Issue #170: beslutninger (regel for båndet, merker for KI-spillere, ingen migrasjon).

## Story 9.13: Vis gruppedebriefen på en delt skjerm (spor 2)

### Oppgave
Bygge Story 9.13 på `epic-9` i spor 2.

### Plan
Byggeagent med `bmad-build-auto` og to gjennomgangsagenter på Sonnet. Byggeagenten for 9.12 gjorde ferdig visuelle rettinger i samme worktree mens denne startet; orkestratoren fikk dem committet først (1b33fb5) og varslet om at stacken var stoppet.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-9-13-show-the-group-debrief-on-a-shared-screen.md` (på `epic-9`).
- Commit: e7499d0.
- Lenken «Delt skjerm: hele kjeden» og siden `/delt-skjerm/<debrief id>`, som leser et svar uten tekstfelt (ingen navn kan komme med): kjeden i valgt uke med egen skrubber, netto lager per rolle på felles skala, og kostnad per rolle med totalen for kjeden. Låst til alle i gruppen har sendt Forklaringen.
- Tester: backend 2949, Vitest 780, typecheck, `lint:colours`, `check:copy`, bygg, Playwright 138 av 138, ingen ustabile tester.
- Gjennomgang: 24 funn, 5 lave rettet.
- Visuell kontroll (Sonnet, bare rapport, eget worktree): skjermbilder i `screenshots/9.13/`, også ved 1920 px. Én klar feil: ved 200 % tekst forsvinner de fire lagergrafene. I tillegg skalerer ikke siden opp for projektor (samme 13 px tekst ved 1920 px), og lagergrafene er flate striper. Alt går til avslutningen av Epic 9, siden ingen story igjen endrer siden.
- Status: done.

### Åpne punkter
- Issue #171: beslutninger (lås bare på Forklaringene, egen side uten navn).

## Story 8.4: Ta setet tilbake med «Ta tilbake setet» (spor 1)

### Oppgave
Bygge Story 8.4 på `epic-8` i spor 1, og rette to feil på spillskjermen fra den visuelle kontrollen av 8.2.

### Plan
Byggeagent med `bmad-build-auto` og fire gjennomgangsagenter på Sonnet (alle fire leverte via fil). Orkestratoren pekte byggeagenten til edge case-filen. Neste byggeagent startet med en gang, og den visuelle kontrollen gikk samtidig.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-8-4-take-the-seat-back-with-ta-tilbake-setet.md`.
- Commit: 48cd2bb. Migrasjon 0055 (`seat_reclaims`).
- «Ta tilbake setet» på Spill og Hjem; ønsket lagres og setet går tilbake til studenten når neste uke åpner. «Alle rader og kostnad» står over merknaden i alle bredder, og kjeden viser «KI-ordre 9» i vanlig vekt.
- Tester: backend 2927, Vitest 844, typecheck, `lint:colours`, `check:copy`, bygg, Playwright 168 uten ustabile tester.
- Gjennomgang: 29 funn, ingen høye eller middels, 3 lave rettet (blant dem at et ønske som står igjen når spillet er ferdig, slettes).
- Visuell kontroll (Sonnet, bare rapport, eget worktree): 18 skjermbilder i `screenshots/8.4/`, ingen klare feil; de to rettingene fra 8.2 er bekreftet.
- Status: done.

### Åpne punkter
- Issue #172: beslutninger (egen tabell, ønske i siste uke godtas og bortfaller for ikke å avsløre spillets lengde).

## Story 9.14: Les KI-fortelling som bare binder sammen beregnede fakta (spor 2)

### Oppgave
Bygge Story 9.14 på `epic-9` i spor 2.

### Plan
Byggeagent med `bmad-build-auto` mot KI-mocken og fire gjennomgangsagenter på Sonnet. Visuell kontroll som bare rapporterer, i eget worktree.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-9-14-read-ai-narration-that-only-connects-computed-facts.md` (på `epic-9`).
- Commit: 98ab88c. Migrasjon 0112.
- KI-fortelling på steg 4: én jobb per sete, maler med fire setninger der modellen bare velger setninger og fakta og koden skriver alle ord, teksten låses ved første visning, og en ekstra KI-linje under forklaringen ved feil quizsvar. Bruker modelloppsettet til klasseøkta.
- Tester: backend 2981 (117 s), Vitest 782, typecheck, `lint:colours`, `check:copy`, bygg, Playwright 240 av 240 (`homes` feilet én gang under last).
- Gjennomgang: 44 funn, 2 middels og 12 lave rettet.
- Visuell kontroll (Sonnet, bare rapport, eget worktree): 15 skjermbilder i `screenshots/9.14/`, ingen klare feil; KI-tekst er merket og kodetekst ikke. To punkter sendt til 9.15: plasseringen og størrelsen på fortellingen sammenlignet med mockupen, og bryteren «KI-tekst i Debriefen» som ser fylt ut når den er av.
- Status: review. Fortellingen er aldri kjørt mot en ekte modell fordi nøkkelen er sperret for agenter (Issue #9).

### Åpne punkter
- Issue #173: kommandoene grunnleggeren må kjøre med ekte nøkkel, og beslutningene.

## Story 8.5: Sett inn en KI-spiller i ett sete fra Spillstyring (spor 1)

### Oppgave
Bygge Story 8.5 på `epic-8` i spor 1.

### Plan
Byggeagent med `bmad-build-auto` og fire gjennomgangsagenter på Sonnet. Den blinde gjennomgangen leverte via fil, og orkestratoren pekte byggeagenten dit. Neste byggeagent startet med en gang, og den visuelle kontrollen gikk samtidig.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-8-5-put-an-ai-player-in-one-seat-from-spillstyring.md`.
- Commit: 5fe60c5. Ingen migrasjon.
- «Sett inn KI-spiller for …» i Spillstyring på Spillinnsikt og i Varselbåndet, `POST /api/games/{id}/seats/{role}/takeover`, 409 `takeover_exists` som sier hvem som handlet, og merket «KI satt inn av {navn}».
- Tester: backend 2947, Vitest 852, typecheck, `lint:colours`, `check:copy`, bygg, Playwright 179 av 180 (`reclaim` ved 320 px feilet én gang og passerte ved ny kjøring).
- Gjennomgang: 44 funn, 2 middels; den ekte (trykk i siste uke på et sete som har bestilt) og 10 lave er rettet. Fire punkter fra den blinde gjennomgangen er beholdt med vilje, med begrunnelse i specen.
- Visuell kontroll (Sonnet, bare rapport, eget worktree): skjermbilder i `screenshots/8.5/`, ingen klare feil. Tittelen «Spillstyring» har feil typografi (headline i stedet for label); sendt til 8.6. To visuelle kontroller brukte samme compose-prosjekt samtidig, så denne byttet til et eget; fra nå får hver kontroll eget prosjektnavn og egne porter.
- Status: done.

### Åpne punkter
- Issue #174: beslutninger (overtakelse fra neste uke når studenten har bestilt, avvisning i siste uke).

## Story 8.6: Sett klassespillet på pause med «Ta pause» (spor 1)

### Oppgave
Bygge Story 8.6 på `epic-8` i spor 1, med gruppen «Pause» på Oversikt som Story 7.1 lot stå til Epic 8.

### Plan
Byggeagent med `bmad-build-auto` og fire gjennomgangsagenter på Sonnet. Neste byggeagent startet med en gang, og den visuelle kontrollen gikk samtidig med eget compose-prosjekt.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-8-6-pause-the-class-game-with-ta-pause.md`.
- Commits: 3c18bd5 og 7eaa5e1 (to punkter fra 8.5 satt tilbake til slik 8.5 ville ha dem). Migrasjon 0056.
- Studenter kan ta pause fra Spill og Hjem; ingen overtakelse mens spillet står; pauselinja og «Pausen er over»; gruppen «Pause» på Oversikt og pausede spill holdt utenfor Varselbåndet.
- Tester: backend 2953, Vitest 861, typecheck, `lint:colours`, `check:copy`, bygg, Playwright 182 uten ustabile tester.
- Gjennomgang: 39 funn, 1 middels og 10 lave rettet.
- Visuell kontroll (Sonnet, bare rapport, eget compose-prosjekt): 30 skjermbilder i `screenshots/8.6/`. Én klar feil: statusfilteret på Oversikt mangler «Pause n»; sendt til 8.7 sammen med spørsmålet om pauser i «Venter ellers».
- Status: done.

### Åpne punkter
- Issue #175: beslutninger (hvem kan ta pause, frister løper under pause, gruppe på Oversikt).

## Story 9.15: Still avgrensede oppfølgingsspørsmål om spillet mitt (spor 2)

### Oppgave
Bygge Story 9.15 på `epic-9` i spor 2, den siste storyen i Epic 9, og gjøre testene for fortelling fra 9.14 raskere.

### Plan
Byggeagent med `bmad-build-auto` mot KI-mocken og fire gjennomgangsagenter på Sonnet, én av dem med vinkel på injeksjon og lekkasje av data. Den visuelle kontrollen gjøres i avslutningen av Epic 9.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-9-15-ask-bounded-follow-up-questions-about-my-game.md` (på `epic-9`).
- Commit: d248214. Migrasjon 0113.
- Oppfølgingsspørsmål i Debrief der svaret alltid er en hint-mal, aldri en påstand; Forklaringen sendes med etter vasking av navn, e-postadresser og lange tall; tidsfrist 20 s og grense på antall spørsmål.
- Tester: backend 3004 på 106 s, Vitest 785, typecheck, `lint:colours`, `check:copy`, Playwright 141 av 141. Testene for fortelling er raskere (8,6 s ble 5,1 s for den tregeste).
- Rettet to feil fra 9.14: utfall i dev-mocken traff alle kall i prosessen, og testfikstrer slettet maler som andre tester trengte.
- Gjennomgang: 51 funn, 8 middels; 2 middels og 15 lave rettet, 2 utsatt.
- Status: review. Ingen ekte modell har svart ennå (Issue #9).

### Åpne punkter
- Issue #176: kommandoen for ekte kall, beslutninger og to utsatte punkter.

## Story 8.7: Sett et klassespill på pause med avtalt tid som faglærer (spor 1)

### Oppgave
Bygge Story 8.7 på `epic-8` i spor 1, og rette typografien i tittelen «Spillstyring».

### Plan
Byggeagent med `bmad-build-auto` og fire gjennomgangsagenter på Sonnet. Neste byggeagent startet med en gang, og den visuelle kontrollen gikk samtidig med eget compose-prosjekt.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-8-7-pause-a-class-game-with-an-agreed-time-as-lecturer.md`.
- Commit: a658811. Migrasjon 0057.
- Faglæreren kan sette pause fra Spillstyring og Varselbåndet, med eller uten avtalt tid, endre tiden og avslutte pausen. Den avtalte tiden blir tidspunktet studentene kan sette inn en KI-spiller fra; tidspunktet for automatisk overtakelse flyttes aldri.
- Tester: backend 2975, Vitest 869, typecheck, `lint:colours`, `check:copy`, bygg, Playwright 182 av 183 (`spillstyring` måtte telle bare knappene per sete etter at «Pause spillet» kom til).
- Gjennomgang: 42 funn, 1 middels (pause uten tid nullstilte innsettingstidene) og 9 lave rettet.
- Filteret «Pause n» på Oversikt ble holdt utenfor storyen; det går til avslutningen av Epic 8.
- Visuell kontroll (Sonnet, bare rapport, eget compose-prosjekt): skjermbilder i `screenshots/8.7/`, ingen klare feil. Til avslutningen av Epic 8: «Pause n» i statusfilteret, primærknappen «Ta pause» som ikke navngir tiden, og feilmeldingen for tidsrom som bare står under klokkeslettet mens knappen er aktiv.
- Status: done.

### Åpne punkter
- Issue #177: beslutninger (avtalt tid som innsettingstid, kunngjøring én gang, tekst for elevene).

## Story 10.1: Få et standard Replay-scenario som er ulikt for hver student (spor 2)

### Oppgave
Bygge Story 10.1 på `epic-10` i spor 2, den første storyen i Epic 10. `epic-10` er laget fra den ferdige `epic-9`, mens avslutningen av Epic 9 kjører i eget worktree.

### Plan
Byggeagent med `bmad-build-auto` og fire gjennomgangsagenter på Sonnet. Neste byggeagent startet med en gang, og den visuelle kontrollen gikk samtidig med eget compose-prosjekt.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-10-1-get-a-default-replay-scenario-that-differs-per-student.md`, pluss `epic-10-context.md` (på `epic-10`).
- Commit: 86a4606. Migrasjon 0114.
- Mal for Replay-scenario i motoren, festet ved låsing, og en blokk «Replay-scenario» på Klasseøkt som bare kan leses. Simuleringer kan kjøre scenariet; 10 spill med alle kontroller i orden.
- Tester: backend 3046, motoren med 100 % dekning, Vitest 788, typecheck, `check:copy`, `lint:colours`, bygg, Playwright 151.
- Postgres i spor 2 gikk i gjenoppretting etter krasj i rundt 10 minutter under kjøringen; to tester feilet på tilkobling og passerte etterpå.
- Gjennomgang: 34 funn, 11 rettet.
- Visuell kontroll (Sonnet, bare rapport, eget compose-prosjekt): tolv skjermbilder i `screenshots/10.1/`, ingen klare feil. Tre punkter om blokken (overskrift, plassering, bredde) sendt til 10.2, som gjør blokken redigerbar.
- Status: done.

### Åpne punkter
- Issue #178: beslutninger (ny Play guard-sett `placeholder-1`, hvordan etterspørselen trekkes) og oppfølgende gjennomgang anbefalt.

## Story 8.8: Sett inn en KI-spiller i et sete der studenten er borte, som student (spor 1)

### Oppgave
Bygge Story 8.8 på `epic-8` i spor 1.

### Plan
Byggeagent med `bmad-build-auto` og fire gjennomgangsagenter på Sonnet. Orkestratoren ba om en test for at id-en til faglæreren ikke når studenter. Neste byggeagent startet med en gang, og den visuelle kontrollen gikk samtidig med eget compose-prosjekt.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-8-8-put-an-ai-player-in-an-absent-seat-as-a-student.md`.
- Commit: ff759ff. Migrasjon 0058.
- En student med et annet sete kan sette inn en KI-spiller i et fravært sete når innsettingstiden har gått, også under pause. Linja før innsettingstiden, teksten om konsekvensen og «Sett inn KI-spiller for …» på Spill og Hjem; sweepen kunngjør innsettingstiden én gang.
- Tester: backend 2996, Vitest 873, typecheck, `lint:colours`, `check:copy`, bygg, Playwright 178 av 178. To backend-kjøringer døde fordi Postgres gikk i gjenoppretting under last; nye kjøringer passerte.
- Gjennomgang: 32 funn, 1 middels og 8 lave rettet.
- Visuell kontroll (Sonnet, bare rapport, eget compose-prosjekt): 31 skjermbilder i `screenshots/8.8/`, ingen klare feil. Små punkter om tekststørrelse og fullt navn i setelinja er tatt med i lista til slutten av epicen.
- Status: done.

### Åpne punkter
- Issue #181: beslutninger og at Postgres krasjet under last.

## Avslutning av Epic 9

### Oppgave
Avslutte Epic 9 (9.1–9.15; 9.14 og 9.15 står i review) med merge av `main` (Epic 7), visuell kontroll av 9.15, rettinger, stabilisering, PR og CI, i et eget worktree mens spor 1 bygde Epic 8 og spor 2 startet Epic 10.

### Plan
Én agent i `.claude/worktrees/epic9` med egen stack (8090/5434). Orkestratoren merget etter grønn CI.

### Resultat
- Merge av `main` (36eecc1): 20 filer i konflikt, begge sider beholdt, api-klienten generert på nytt. Én Alembic-head (0113), der 0101 nå følger 0052. Debrief-lenkene i Spillinnsikt er koblet inn fast og tilbys bare for ferdige spill, med en test.
- Visuell kontroll av 9.15 i `screenshots/9.15/`, ingen avvik.
- Rettinger: den felles skjermen fra 9.13 beholder grafene ved 200 % tekst, skalerer opp på projektor og har større låst tilstand (69ce009); fortellingen fra 9.14 er en dempet linje i kolonnen for øyeblikket (70efbd7); bekreftelsen av «Forlat gruppen» har fylt primærknapp, og 48 timer regnes fra første åpning i en tilbakeholdt klasseøkt (e5c716e); quizkolonnene flukter og valgknappene har mellomrom (ce1ba00); e2e- og CI-rettinger (7326795, 4ad0a7a, a619663), blant dem `system-states:250`, som feilet på `main`.
- Backend: 3079 tester på 141 s (266 s med 19 feil i første kjøring under tung last). Testene ble ikke raskere; hver av de trege spiller sitt eget spill.
- Playwright: tre kjøringer på rad uten feil, 527 tester hver. Vitest 898, typecheck, `lint:colours`, `check:copy`, bygg.
- PR #179 med grønn CI, merget til `main`.

### Åpne punkter
- Issue #180: utsatte punkter (tilbakeholdt Debrief når et spill aldri blir ferdig, nøytral tekst for tilbakefall, et oppfølgingsspørsmål uten svar da klokka i Docker hoppet, trege tester i Epic 9).
- Issue #173 og #176: 9.14 og 9.15 venter på prøve mot ekte modell.

## Story 10.2: Sett Replay-scenariet fritt (spor 2)

### Oppgave
Bygge Story 10.2 på `epic-10` i spor 2, og ta hensyn til tre punkter fra den visuelle kontrollen av 10.1 på samme blokk.

### Plan
Byggeagent med `bmad-build-auto` og to gjennomgangsagenter på Sonnet. Etter storyen merget orkestratoren `main` (Epic 7 og 9) inn i `epic-10`. Neste byggeagent startet med en gang, og den visuelle kontrollen gikk samtidig med eget compose-prosjekt.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-10-2-set-the-replay-scenario-freely.md`.
- Commit: e7942c1. Migrasjon 0115. Merge av `main`: 3e81126.
- «Standard» og «Eget scenario» på Klasseøkt, et eget skjema med uker og endringsuke som enkeltverdi eller spenn, sjekk når et felt forlates, advarsler når et valg trolig gjør Replay lettere, og låsing og kopiering av eget scenario.
- Tester: backend 3064 (112 s), Vitest 794, typecheck, `check:copy`, `lint:colours`, bygg, Playwright 268. Én backend-kjøring hang til tidsavbrudd mens gjennomgangsagentene arbeidet.
- Merge med `main`: konflikt i `moments-step.tsx` (beholdt versjonen fra `main`) og api-klienten (generert på nytt); Vitest 907 og `test_migrations` passerte.
- Gjennomgang: 26 funn, 7 rettet (1 middels).
- Visuell kontroll (Sonnet, bare rapport, eget compose-prosjekt): skjermbilder i `screenshots/10.2/`. Én klar feil: skjemaet viser bare én feil om gangen når flere felt er feil. Den og tre punkter om overskrift, bredde og omvendt spenn går til avslutningen av Epic 10.
- Status: done.

### Åpne punkter
- Issue #182: beslutninger (advarsler, spenn, eget scenario følger spillinnstillingene).

## Story 8.9: Gi én student mer tid med Tilrettelegging (spor 1)

### Oppgave
Bygge Story 8.9 på `epic-8` i spor 1, og lukke det utsatte punktet fra 8.1 om nærmeste frist per spill.

### Plan
Byggeagent med `bmad-build-auto` og fire gjennomgangsagenter på Sonnet, én med vinkel på personvern. Neste byggeagent startet med en gang, og den visuelle kontrollen gikk samtidig med eget compose-prosjekt.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-8-9-give-one-student-more-time-with-tilrettelegging.md`.
- Commit: ffc06e1. Migrasjon 0059.
- Studentside bare for faglærere med blokken «Tilrettelegging» (faktor 1, 1,5, 2 eller 3), fristene i åpen uke flyttes når faktoren lagres, linje i Spillstyring for faglæreren og to linjer på Hjem for studenten selv. Andre studenter ser ingenting.
- Tester: backend 3032, Vitest 880, typecheck, `lint:colours`, `check:copy`, bygg, Playwright 185. En test i `test_turn_clock.py` ble rettet (ikke ustabil); én mellomkjøring etterlot 20 feilede tester som passerte ved ny kjøring.
- Gjennomgang: 41 funn, 1 middels og 13 lave rettet.
- En tom fil `policy.py` dukket opp i roten av repoet under kjøringen; den er ikke committet.
- Visuell kontroll (Sonnet, bare rapport, eget compose-prosjekt): skjermbilder i `screenshots/8.9/`, ingen klare feil. Bekreftet at Tilrettelegging aldri vises for andre studenter, og at assistenten får 403.
- Status: done.

### Åpne punkter
- Issue #183: beslutninger (faktorer, tilgang bare for faglærere, gulvet fra FR-89).

## Story 10.3: Start Replay etter bestått Debrief-quiz (spor 2)

### Oppgave
Bygge Story 10.3 på `epic-10` i spor 2, første story etter merge av `main` inn i `epic-10`.

### Plan
Byggeagent med `bmad-build-auto` og fire gjennomgangsagenter på Sonnet. Neste byggeagent startet med en gang, og den visuelle kontrollen gikk samtidig med eget compose-prosjekt.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-10-3-start-the-replay-after-passing-the-debrief-quiz.md`.
- Commit: ae5efdf. Migrasjon 0116.
- Modulen `replay` med én Replay per student og klasseøkt, start bare etter bestått quiz og før Testfristen, og «Start Replay» og «Replay · Du er Grossist» på Hjem.
- Tester: backend 3138 på 117 s (på ferske testdatabaser), Vitest 910, typecheck, `check:copy`, `lint:colours`, bygg, Playwright 246 (`homes` og `order-confirm` feilet én gang hver og passerte ved ny kjøring).
- Funn etter merge av `main`: databaser som allerede var på 0115, mangler tabellene fra 0051 og 0052. Testene i spor 2 bruker nå ferske databaser, og utviklingsdatabasen fikk tabellene lagt inn. CI er ikke berørt.
- Gjennomgang: 39 funn, 11 rettet, 1 utsatt til 10.5.
- Visuell kontroll (Sonnet, bare rapport, eget compose-prosjekt): skjermbilder i `screenshots/10.3/`, ingen klare feil. «Fortsett Replay, Uke N» på Hjem mangler; sendt til 10.4, som gjør Replay spillbart.
- Status: done.

### Åpne punkter
- Issue #184: beslutninger og rekkefølgen på migrasjoner etter merge.

## Story 8.10: Start ett klassespill eller alle som faglærer (spor 1)

### Oppgave
Bygge Story 8.10 på `epic-8` i spor 1.

### Plan
Byggeagent med `bmad-build-auto` og fire gjennomgangsagenter på Sonnet. Neste byggeagent startet med en gang, og den visuelle kontrollen gikk samtidig med eget compose-prosjekt.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-8-10-start-one-class-game-or-all-of-them-as-lecturer.md`.
- Commit: 49a7bbe. Migrasjon 0060.
- Faglæreren kan starte ett spill fra Spillstyring («Start spillet») eller alle fra siden «Start spill» via Oversikt; hvem som startet og når, lagres og revideres.
- Tester: backend 3041 (to feil forårsaket av endringen, rettet), Vitest 885, typecheck, lint, `check:copy`, bygg, Playwright 162 av 163 (`game-card` feilet én gang og passerte ved ny kjøring). Testen med 100 spill tar 8–9 s.
- Gjennomgang: 36 funn, 1 middels (spill uten student kunne startes) og 8 lave rettet.
- En tidlig kjøring som normaliserte linjeslutt, skadet skjermbilder og `sprint-status.yaml` i arbeidstreet; satt tilbake med en gang, ingenting skadet er committet. Byggeagentene får nå beskjed om aldri å gjøre slike kjøringer over hele repoet.
- Visuell kontroll (Sonnet, bare rapport, eget compose-prosjekt): 21 skjermbilder i `screenshots/8.10/`, ingen klare feil.
- Status: done.

### Åpne punkter
- Issue #185: beslutninger (bare faglærer, avvisninger, 4 spill om gangen).

## Story 10.4: Spill Replay med projeksjonslinja (spor 2)

### Oppgave
Bygge Story 10.4 på `epic-10` i spor 2, med inngangen «Fortsett Replay, Uke N» på Hjem fra den visuelle kontrollen av 10.3.

### Plan
Byggeagent med `bmad-build-auto` og fire gjennomgangsagenter på Sonnet. Neste byggeagent startet med en gang, og den visuelle kontrollen gikk samtidig med eget compose-prosjekt.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-10-4-play-the-replay-with-the-projection-line.md`.
- Commit: a67de9f.
- Replay spilles på spillskjermen fra Epic 6, med stiplet projeksjonslinje til nå + horisont, hul prikk og en forklarende setning; regnestykket er testet mot motorens fasitverdier. «Fortsett Replay, Uke 9» på Hjem og i Stegene.
- Tester: backend 3141 på 116,6 s, Vitest 1022, typecheck, `lint:colours`, `check:copy`, bygg, Playwright 193 uten ustabile tester.
- Gjennomgang: 37 funn, 4 lave rettet, 1 middels utsatt til 10.5 (sluttskjermen for Replay viser «Gå til Debrief»). En ekte e2e-test for projeksjonen er også sendt til 10.5.
- Visuell kontroll (Sonnet, bare rapport, eget compose-prosjekt): skjermbilder i `screenshots/10.4/`. Én klar feil: projeksjonslinja og prikken går gjennom etiketten «Restordre 20» i grafen. Sendt til 10.5 mens den bygges, sammen med at formelen brytes ved 390 px.
- Status: done.

### Åpne punkter
- Issue #186: beslutninger (horisonten, setningen uten bestilling, linja forbi nå + 4).

## Story 8.11: Merk et klassespill som «I rommet» i en labtime (spor 1)

### Oppgave
Bygge Story 8.11 på `epic-8` i spor 1.

### Plan
Byggeagent med `bmad-build-auto` og fire gjennomgangsagenter på Sonnet. Neste byggeagent startet med en gang, og den visuelle kontrollen gikk samtidig med eget compose-prosjekt.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-8-11-mark-a-class-game-as-i-rommet-during-a-lab-hour.md`.
- Commit: 5bb7bbd. Migrasjon 0061.
- Faglæreren kan merke et spill som «I rommet» i en labtime; da gjelder den kortere grensen for overtakelse. Merket avsluttes av sweepen eller når labtimen flyttes eller fjernes. Skjema i Spillstyring, linje for studenten og merket «I rommet» i veggen.
- Tester: backend 3055, Vitest 895, typecheck, `lint:colours`, `check:copy`, bygg, Playwright 139 uten ustabile tester (to ekte feil i første kjøring ble rettet).
- Gjennomgang: 51 funn, 7 rettet, 1 utsatt (test for ferdige spill).
- Visuell kontroll (Sonnet, bare rapport, eget compose-prosjekt): 36 skjermbilder i `screenshots/8.11/`, ingen klare feil. Hjem har ingen linje for «I rommet», og resultatlinja gjentar statusen; tatt med i lista til slutten av epicen.
- Status: done.

### Åpne punkter
- Issue #187: beslutninger (ny beregning ved merking, avrunding, ett merke per spill).

## Story 10.5: Fullfør Replay og lås opp neste steg (spor 2)

### Oppgave
Bygge Story 10.5 på `epic-10` i spor 2, med to utsatte punkter fra 10.3 og 10.4 og en ekte e2e-test for projeksjonen.

### Plan
Byggeagent med `bmad-build-auto` og fire gjennomgangsagenter på Sonnet. Neste byggeagent startet med en gang, og den visuelle kontrollen gikk samtidig med eget compose-prosjekt.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-10-5-finish-the-replay-and-unlock-the-next-step.md`.
- Commit: 2469010.
- Siste ordre fullfører Replay og registrerer steget som låser opp den individuelle prøven. Egen sluttskjerm for Replay uten «Gå til Debrief», «Se Replay» på Hjem, og Spillinnsikt for Replay for stab.
- Ny dev-rute og en ekte e2e-test som starter en Replay på stacken og ser projeksjonslinja der, og ikke i klassespillet.
- Tester: backend 3144 på 137 s, Vitest 1024, typecheck, `lint:colours`, `check:copy`, bygg, Playwright 180 uten ustabile tester.
- Gjennomgang: 29 funn, 3 lave rettet, 1 middels utsatt. Linja over etiketten fra 10.4 kom ikke med og er sendt til 10.6.
- Visuell kontroll (Sonnet, bare rapport, eget compose-prosjekt): 15 skjermbilder i `screenshots/10.5/`, ingen klare feil. Setelista for en ferdig Replay på Hjem viser «har bestilt»/«venter»; tatt med i lista til slutten av epicen.
- Status: done.

### Åpne punkter
- Issue #188: beslutninger og utsatt punkt om lenken for stab etter overtakelse.

## Story 8.12: Fyll alle seter det ventes på, i én handling (spor 1)

### Oppgave
Bygge Story 8.12 på `epic-8` i spor 1.

### Plan
Byggeagent med `bmad-build-auto` og fire gjennomgangsagenter på Sonnet. Neste byggeagent startet med en gang, og den visuelle kontrollen gikk samtidig med eget compose-prosjekt.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-8-12-fill-every-waited-for-seat-in-one-action.md`.
- Commit: 5ce0bd3. Ingen migrasjon.
- Én regel for hvem det ventes på (`rules.waited_for`). Faglæreren kan sette inn KI-spillere i alle seter det ventes på, per spill i Spillstyring eller for hele klasseøkta på siden `/oversikt/sett-inn`; seter med tilrettelegging tas aldri med.
- Tester: backend 3065 (to fulle kjøringer), Vitest 902, typecheck, `lint:colours`, `check:copy`, bygg, Playwright 138 uten ustabile tester. Testen med 100 spill tar 10–13 s.
- Gjennomgang: 33 funn, 6 middels; 2 middels og 8 lave rettet.
- Visuell kontroll (Sonnet, bare rapport, eget compose-prosjekt): 25 skjermbilder i `screenshots/8.12/`, ingen feil i 8.12. Én klar feil i eldre kode: Varselbåndet på Oversikt klemmes til én bokstav per linje ved 200 % tekst (siden blir 9400 px høy); går til Story 8.14.
- Status: done.

### Åpne punkter
- Issue #189: beslutninger (pausede spill holdes utenfor, bare faglærer, tilrettelegging tas aldri med).

## Story 10.6: Steng Replay som ikke er ferdig, ved Testfristen (spor 2)

### Oppgave
Bygge Story 10.6 på `epic-10` i spor 2, og rette at projeksjonslinja krysset etikettene i grafen (fra den visuelle kontrollen av 10.4).

### Plan
Byggeagent med `bmad-build-auto` og fire gjennomgangsagenter på Sonnet; orkestratoren pekte den til hullene som gjennomgangen av testdekningen fant. Neste byggeagent startet med en gang, og den visuelle kontrollen gikk samtidig med eget compose-prosjekt.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-10-6-close-unfinished-replays-at-the-test-deadline.md`.
- Commit: b211c33. Migrasjon 0117.
- Sweepen stenger en Replay som ikke er ferdig når Testfristen har gått for alle studentene i den; den blir ikke regnet som fullført, og ordrene beholdes. «Replay stengt» på egen skjerm, Hjem, Stegene og Spillinnsikt. Etikettene i grafen flytter seg unna projeksjonslinja, og formelen holder seg samlet.
- Tester: backend 3146 på 133 s, Vitest 1031, typecheck, `lint:colours`, `check:copy`, bygg, Playwright 130. En Vitest-test for farger var ustabil i to kjøringer under last.
- Gjennomgang: 36 funn, 8 rettet (1 middels).
- Visuell kontroll (Sonnet, bare rapport, eget compose-prosjekt): skjermbilder i `screenshots/10.6/`. Rettingen av grafen er bekreftet ved 390 og 1280 px. Én klar feil: ved 200 % tekst blir grafkolonnen på spillskjermen så smal at etikettene kuttes («Pos», «Rest»); trolig eldre, går til avslutningen av Epic 10.
- Status: done.

### Åpne punkter
- Issue #190: beslutninger (når en Replay stenges, KI-ordre før sweepen, etiketter i grafen).

## Story 8.13: Få e-post når spillet venter på ordren din (spor 1)

### Oppgave
Bygge Story 8.13 på `epic-8` i spor 1.

### Plan
Byggeagent med `bmad-build-auto` og fire gjennomgangsagenter på Sonnet i to runder. Ingen skjerm ble endret, så ingen visuell kontroll.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-8-13-get-an-email-when-the-game-waits-for-your-order.md`.
- Commit: 351d946. Migrasjon 0062.
- En student som spillet venter på, får én påminnelse på e-post to timer etter at ventingen begynte, i den daglige samlemeldingen. Ingen påminnelse under pause, før andre har bestilt, eller når spillet ikke lenger venter på studenten.
- Tester: backend 3081, Vitest 902, typecheck, `lint:colours`, `check:copy`, bygg, Playwright 47. `test_pause_view` feilet én gang i en full kjøring og passerte alene og i neste kjøring.
- Gjennomgang: første runde sendte specen tilbake én gang (pause etter at påminnelsen var lagt i kø); andre runde ga tre små rettinger.
- Status: done.

### Åpne punkter
- Issue #191: beslutninger (påminnelse under pause, ingen endring med tilrettelegging eller «I rommet», ingen utfylling bakover).

## Story 10.7: Les gjennomgangen av Replay (spor 2)

### Oppgave
Bygge Story 10.7 på `epic-10` i spor 2.

### Plan
Byggeagent med `bmad-build-auto` mot KI-mocken og fire gjennomgangsagenter på Sonnet. Neste byggeagent startet med en gang, og den visuelle kontrollen gikk samtidig med eget compose-prosjekt.

### Resultat
- Spec: `.docs/implementation-artifacts/spec-10-7-read-the-replay-walkthrough.md`.
- Commit: ff8792a. Migrasjon 0118.
- Siden `/spill/<id>/gjennomgang` setter Replay ved siden av klassespillet i én graf, viser to øyeblikk og en KI-linje som bare viser til øyeblikkene som vises. Bare studenten selv kan lese den.
- Tester: backend 3148 på 134,6 s, Vitest 1038, typecheck, `lint:colours`, `check:copy`, bygg, Playwright 143 uten ustabile tester. Én ny test tar 13–15 s og skal kortes ned i avslutningen av epicen.
- Gjennomgang: 39 funn, 13 rettet (1 middels), 1 utsatt.
- Visuell kontroll (Sonnet, bare rapport, eget compose-prosjekt): 19 skjermbilder i `screenshots/10.7/`, ingen klare feil. Grafen mangler direkte etiketter på linjene slik mockupen har; tatt med i lista til slutten av epicen.
- Status: review. KI-linja er aldri kjørt mot en ekte modell (Issue #9).

### Åpne punkter
- Issue #192: kommandoen for ekte kall og beslutningene.
