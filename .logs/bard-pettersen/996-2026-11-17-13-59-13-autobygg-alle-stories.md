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
