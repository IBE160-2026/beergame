---
title: 'Story 2.7: Call a real EU endpoint within its rate limit'
type: 'feature'
created: '2026-11-18'
baseline_revision: 'c4b693771aece7cc00ad07e5a30ac87704e2eb28'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-2-context.md'
warnings: ['oversized']
deferred:
  - summary: >-
      The rate limiter is per process, so several processes on one endpoint and key can exceed the config's rpm.
    evidence: |-
      maybe-false (blind 7): one worker-ai process runs today; a second replica, worker-batch or a parallel
      `app.sim run` would each pace on their own. Settle with the NFR-3 load test (deferred in the spine).
    location: >-
      backend/app/ai/ratelimit.py
    severity: medium (unverified)
  - summary: >-
      The served model and upstream provider are logged on each llm_call row but not checked on production calls.
    evidence: |-
      maybe-false (blind 3): only `python -m app.sim endpoint` compares them. Settle with a real run that shows
      what OpenRouter reports in `model` and `provider` under `allow_fallbacks: false`.
    location: >-
      backend/app/ai/gateway.py
    severity: medium (unverified)
---

<intent-contract>

## Intent

**Problem:** The gateway has no real provider: `_model` returns "no adapter for provider openai_compatible yet", so no prototype number can come from the endpoint the pilot would use, and nothing paces calls or survives an HTTP 429 (AD-6 items 1 and 4, FR-68, NFR-3, C-1, AD-17).

**Approach:** Add an adapter registry in `app/ai` whose one adapter, `openai_compatible`, builds a pydantic-ai OpenAI chat model from the config (injected base URL, key from the named env var, SDK retries off) and sends router preferences from a new config field `routing`; add a per-endpoint limiter sized from `rate_limit_rpm` and 429 back-off inside the deadline; make `python -m app.sim run` refuse a missing key outside the mock environments; add `python -m app.sim endpoint` to probe a real endpoint by hand.

## Boundaries & Constraints

**Always:**
- Founder decision (Issue #9): OpenRouter, model `deepseek/deepseek-v4.1-flash-1017`. Region, upstream provider, routing switches, prices and rate limit live in the config file, never in code. The only provider and router names in code are the keys of the adapter and router registries in `app/ai/adapters.py`.
- Config field `routing: {router: "openrouter", order?, only?, ignore?, quantizations?, require_parameters?, sort?} | null` (validated, `extra="forbid"`). A config with a router gets, on every request, `extra_body.provider` = the configured keys plus the forced switches `allow_fallbacks: false`, `data_collection: "deny"`, `zdr: true`. A config may not set the forced switches to anything else (`ConfigInvalid`), and `models`/`route` (model fallback) are never sent. Routing needs `provider = openai_compatible`.
- Effort-level `provider_params` other than `seed`/`temperature` (for example `reasoning`) go into `extra_body`; a param named `provider`, `models` or `route` is refused at parse time. The request stored on each row shows the full `model_settings`, routing included.
- Alembic `0010` (expand-only): `ai_model_configs.routing JSONB NULL`; `llm_call.served_model TEXT NULL` and `llm_call.served_by TEXT NULL` (the model id and upstream provider the response reports). Downgrade drops them.
- `openai_compatible`: `AsyncOpenAI(base_url=spec.endpoint, api_key=env[spec.credential_env], max_retries=0)` through pydantic-ai's `OpenAIProvider`/`OpenAIChatModel`, `NativeOutput` as today; a module-level transport hook (`adapters.use_transport`) lets tests inject an `httpx2.MockTransport`. `tests/conftest.py` installs a transport that fails every request, so no test can reach a real endpoint.
- `adapters.availability(spec, app_env, environ)` decides `mock` / `real` / `refused(reason)` with today's rules (mock in `local`/`test`/`ci` when the provider is mock or the key is unset; production never mocks). The gateway and the sim CLI both use it.
- Rate limiter (`app/ai/ratelimit.py`): one in-process limiter per `(endpoint, credential_env)`, spacing request starts `60 / rpm` seconds apart (smallest rpm seen for that key); a wait that would end after the deadline is not taken, the call returns `Failure("timeout")`. Real endpoints are paced; the mock is not.
- 429 (`ModelHTTPError.status_code == 429`, mock step `mock.RATE_LIMITED`): no `llm_call` row, the attempt number is not used up; the endpoint pauses for `Retry-After` seconds (header) or `1, 2, 4 … ≤ 30` s, and the call retries while the deadline allows (a retry after a 429 counts as the same attempt for the "whole timeout fits" rule). Past the deadline: `Failure("timeout")`. With no deadline, after 10 consecutive 429s: `Failure("provider_error")`. Each 429 is logged (`llm_rate_limited`, endpoint, wait).
- Clock: the gateway's "now", the limiter and the back-off sleep read one injectable clock (`ratelimit.clock`); tests use a skipping clock (sleep advances virtual time at once). No real sleep in tests.
- `python -m app.sim run`: when the batch names a config whose availability is `refused`, exit 2 with `error key_missing: <VAR> is not set` (or the reason); when it is `mock` for a non-mock provider, or the provider is mock, print `note: mock provider in use for config <id>` on stderr and go on.
- `python -m app.sim endpoint --config ID [--orders 3] [--burst 5]`: refuses (exit 2) unless availability is `real`; then prints a short report: model id listed by `GET {endpoint}/models`, `--orders` sequential `player_order` calls through the gateway with the deadline of the config's first Effort level (outcome, Order, served model and provider, latency, cost per call), a burst of `--burst` concurrent calls (ok count, 429 count, longest limiter wait), totals, and a last line `endpoint ok` or `endpoint failed: <reasons>`; exit 0/1. Seat states come from stored finished Games; with none, one all-`rule_based` Classic Game is played first.
- Shipped configs: `openrouter-deepseek.json` → `https://openrouter.ai/api/v1`, region `eu-provider`, routing `{router: openrouter, order: ["nebius/fp8"], require_parameters: true}`, quantisation `fp8`, prices 0.12/0.48 USD per Mtok; new `openrouter-deepseek-eu.json` → `https://eu.openrouter.ai/api/v1` (OpenRouter EU in-region, Business/Enterprise plan), region `eu`, same routing. Both stay `placeholder` Effort levels.

**Never:** No real call in any test or CI; no reading `.env` or any key in this build; no budget reservation (2.8); no cross-process limiter; no provider fallback, `FallbackModel` or OpenRouter `models` list; no change to `modules/players` code (adding a provider stays one adapter + one config row); no change to golden sim output.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Real call | openrouter config, key set, fake transport answers `{"order":7}` | `Result(order 7)`; request URL = endpoint + `/chat/completions`, `Authorization: Bearer <key>`, body `provider` = order + forced switches, `response_format` json_schema; row has `served_model`, `served_by` | — |
| Routing refused | config `routing.allow_fallbacks: true` or `data_collection: "allow"` or provider mock | `ConfigInvalid` naming the field | — |
| Pacing | rpm 60, 3 concurrent calls, skipping clock | starts 0 s, 1 s, 2 s apart; all `Result` | — |
| Pace past deadline | rpm 1, second call with 5 s deadline | `Failure("timeout", ())`, no row | — |
| 429 then ok | fake transport 429 `Retry-After: 2`, then 200 | one row `ok` attempt 1; virtual wait ≥ 2 s | — |
| 429 past deadline | 429 every time, deadline 8 s | `Failure("timeout")`, no row | — |
| 429 no deadline | 429 every time, `deadline=None` | `Failure("provider_error")` after 10 | — |
| Burst in a Game | 4 `llm` Seats, mock `RATE_LIMITED` × 6, skipping clock | every Order `decided_by = llm`, `fallback = none` | — |
| Sim key missing | batch config with unset key, `APP_ENV=production` | exit 2, `error key_missing: OPENROUTER_API_KEY is not set` | — |
| Sim mock note | same in `test` | note `mock provider in use`, batch runs | — |
| Endpoint probe | fake transport, key set | report lines and `endpoint ok`; exit 0 | 4xx from `/models` → `endpoint failed`, exit 1 |

</intent-contract>

## Code Map

- `backend/app/ai/gateway.py:322` `_model` (replace with `adapters`), `:158` `_settings` (extra_body), `:344` `_attempt` (429 → back-off signal, served model/provider), `:399` `_log` (new columns), `:442` `run` loop (limiter, back-off, clock).
- `backend/app/ai/config.py:71` `ModelConfigSpec` (+`routing`), `:176` `_rules`, `:263` `_row`, `:285` `_values`.
- `backend/app/ai/models.py` -- `model_configs.routing`, `llm_calls.served_model/served_by`.
- `backend/app/ai/mock.py` -- `RATE_LIMITED` step (`ModelHTTPError(429, …, headers={"retry-after": "1"})`).
- `backend/app/ai/adapters.py` (new) -- registries, `availability`, `build_model`, `use_transport`, `list_models`.
- `backend/app/ai/ratelimit.py` (new) -- `Clock`, `SkippingClock`, `Limiter`, module `clock`/`limiter`.
- `backend/app/ai/calls.py` (new) -- `get(ids)` read of `llm_call` rows for the probe report.
- `backend/app/sim.py:1076` `_run_command` (key check), `:762` `_probe_states` (reuse), `:1093` parser (`endpoint`).
- `backend/ai-configs/*.json`; `backend/pyproject.toml` (`pydantic-ai-slim[openai]`, done in planning).
- `backend/migrations/versions/0010_ai_routing.py` (new), `0009_ai_deadlines.py` style.
- pydantic-ai 2.65: `OpenAIChatModel._process_provider_details` hook for the OpenRouter `provider` field; `ModelHTTPError.headers` (lowercased) for `retry-after`; openai 3.54 uses `httpx2` (`httpx2.MockTransport`).
- Tests: `tests/ai/test_gateway.py` (`scope_for`, `call`, `rows`; update `test_a_real_provider_without_a_key…` "no adapter"), `tests/ai/test_config.py`, `tests/ai/test_cli.py:50` (endpoint text), `tests/players/test_llm_jobs.py` (`llm_game`, `rows`), `tests/test_migrations.py` (`HEAD`), `tests/test_imports.py`, `tests/conftest.py`.

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0010_ai_routing.py` -- columns above.
- `backend/app/ai/{models,config}.py` -- `routing` field and rules; refused provider params.
- `backend/app/ai/ratelimit.py`, `adapters.py`, `calls.py` (new) -- as above.
- `backend/app/ai/{gateway,mock}.py` -- adapter use, extra_body, limiter, 429 back-off, served fields, `RATE_LIMITED`.
- `backend/app/sim.py` -- key check in `run`, `endpoint` command.
- `backend/ai-configs/openrouter-deepseek.json`, `openrouter-deepseek-eu.json` -- configs above.
- `backend/tests/conftest.py` -- refusing transport; tests: new `tests/ai/test_adapters.py` (request parameters, served fields, availability, 429/Retry-After, routing validation), `tests/ai/test_ratelimit.py` (pacing, deadline, back-off), gateway rows, `tests/players/test_llm_jobs.py` burst, `tests/test_sim_endpoint.py` (probe report with fake transport; `run` key check); update migrations/config/cli tests.
- `README.md` -- the probe command.

**Acceptance Criteria:**
- Given a second provider, then adding it is one adapter entry and one config row; `players` imports nothing new (import test).
- Given CI commands locally, then ruff is clean, the full suite passes, engine coverage stays 100 %, golden outputs are unchanged, and any new test over 1 s is reported.
- Given the founder's key, when `python -m app.sim endpoint --config <id>` runs, then it prints the report — recorded in the result as **not run: needs the founder's key**, with the exact commands.

## Spec Change Log

## Review Triage Log

### 2026-11-18 — Review pass
- verdicts: 43 findings — high 0, medium 7, low 25, false 7, maybe-false 4
- findings:
  - `[low]` `[reject]` (intent a) the main config points at the global router, not `eu.openrouter.ai` — founder named `https://openrouter.ai/api/v1`; the EU in-region file ships beside it; README now says the global router is not EU-only.
  - `[low]` `[reject]` (intent b) the limiter is not exercised through jobs — the mock is not paced by design; jobs share `gateway.run`, whose pacing is tested.
  - `[medium]` `[patch]` (intent c) a second provider also needs the `Literal`, `_rules` and the DB check — `provider` is now validated against `adapters.ADAPTERS`, `_rules` branches on `!= "mock"`, and 0010 drops `ck_ai_model_configs_provider`.
  - `[low]` `[reject]` (intent d) no job-level test of a retired real endpoint — the typed-failure → fallback path is Story 2.5's and tested there; the gateway test covers a refused connection.
  - `[low]` `[patch]` (intent e) the sim parses the reason text — `Availability.missing_key` field.
  - `[medium]` `[patch]` (intent f) switches depend on `routing` — see blind 1.
  - `[low]` `[reject]` (intent g) no batch-level paced test — the jobs burst test and the gateway pacing tests cover the parts; a real batch is Story 2.11.
  - `[medium]` `[patch]` (gap 1) the retry reservation (`number > 1`) for slot wait and 429 is untested — two new virtual-time tests in `test_adapters.py`.
  - `[medium]` `[patch]` (blind 1) a router endpoint without `routing` sends no switches, including rows stored before 0010 — `adapters.ROUTER_HOSTS`; `config.parse` refuses it (`routing_missing`) and `availability` refuses such a stored row.
  - `[low]` `[patch]` (blind 2) default config sends prompts through a non-EU router — README says so; config choice is the founder's URL.
  - `[maybe-false]` `[defer]` (blind 3) served model/provider are logged but not checked in production — would settle with a real run showing what OpenRouter reports; medium if a different model is served.
  - `[low]` `[patch]` (blind 4) `served_matches` accepts `…-11017` / other years' suffixes — now only exact id or `YYYY`+pinned `MMDD`.
  - `[medium]` `[patch]` (blind 5) 401/400/404 retried up to 6 times — `adapters.final`: a 4xx other than 408/409/425/429 ends the call after its row.
  - `[low]` `[patch]` (blind 6) `Retry-After` unbounded — clamped to `BACK_OFF_MAX_S`, non-finite ignored.
  - `[maybe-false]` `[defer]` (blind 7) per-process limiter: several processes exceed the rpm — documented in Design Notes; one `worker-ai` process today; medium once replicas or a parallel batch run (NFR-3 load test).
  - `[low]` `[reject]` (blind 8) limiter keeps the smallest rpm for the process life — configs on one endpoint share its limit; restart resets.
  - `[low]` `[reject]` (blind 9) a 429 leaves no DB row — designed (Design Notes); the log line records it.
  - `[false]` `[reject]` (blind 10) error text unscrubbed — `_attempt` stores `scrub(error, call.terms)`.
  - `[low]` `[reject]` (blind 11) client cache keyed by `id()` — one loop per process in workers and CLI; the transport is replaced only in tests.
  - `[low]` `[patch]` (blind 12) `httpx2` used but not declared — added `httpx2==2.16.2` to dependencies.
  - `[low]` `[patch]` (blind 13) English message parsing — as intent e.
  - `[low]` `[patch]` (blind 14) bad id exits 1, help says 2; stored Game undocumented — `ConfigIdError` exits 2; help says the Game stays stored.
  - `[false]` `[reject]` (blind 15) probe and gateway Effort level differ — the probe's scope has no level, so `_resolve` takes the first, as the probe prints.
  - `[low]` `[reject]` (blind 16) first attempt may get a tiny timeout after a slot wait — needs a pacing backlog that fills the whole deadline; the attempt then logs `timeout` as any late call.
  - `[low]` `[patch]` (blind 17a) tautological limiter assert — now asserts the 429 count only.
  - `[low]` `[reject]` (blind 17b) other test gaps (cancel in back-off, 5xx, cache) — 401 and 5xx now tested; the rest are rare.
  - `[low]` `[reject]` (blind 17c) fixtures imported across test files — works; style only.
  - `[false]` `[reject]` (blind 18) private pydantic-ai hook silently breaks — `served_by == "Nebius"` is asserted end to end and fails loudly.
  - `[false]` `[reject]` (blind 19) prices unsourced — Design Notes record the listing and the date.
  - `[false]` `[reject]` (edge 1) `requests` empty → ZeroDivisionError — after the Rule-based Game the decision log has 16 non-Guided rows and `--orders ≥ 1`.
  - `[low]` `[patch]` (edge 2) `Retry-After: inf/nan` — as blind 6.
  - `[low]` `[patch]` (edge 3) no cap without a deadline — as blind 6.
  - `[medium]` `[patch]` (edge 4) router without routing — as blind 1.
  - `[medium]` `[patch]` (edge 5) `model`, `messages`, `response_format`, `stream` in provider_params override the pinned request — `RESERVED_PARAMS` extended (also `n`, `tools`, `tool_choice`); test covers them.
  - `[false]` `[reject]` (edge 6) stored rows skip `_rules` — `model_settings` filters `RESERVED_PARAMS`; an unknown router cannot be stored.
  - `[low]` `[reject]` (edge 7) a mistyped seed is dropped silently — pre-existing (Story 2.3).
  - `[low]` `[patch]` (edge 8) `left == timeout` refuses a free slot — `acquire` refuses only `wait > left_s`.
  - `[low]` `[reject]` (edge 9) cancel during the slot sleep loses the slot — costs one interval, rare.
  - `[false]` `[reject]` (edge 10) client cache — as blind 11.
  - `[maybe-false]` `[reject]` (edge 11) a GatewayError in the burst — the sequential calls with the same inputs raise first; low if true.
  - `[low]` `[patch]` (edge 12) longest wait is lifetime — labelled `longest_slot_wait_s … (whole run)`; the CLI is a fresh process.
  - `[low]` `[patch]` (edge 13) `routing` None stored as JSON `null` — `JSONB(none_as_null=True)`.
  - `[maybe-false]` `[reject]` (edge 14) one adapter + one row claim — duplicate of intent c, patched.

## Design Notes

OpenRouter public listing, read 2026-11-18 without a key (`GET /api/v1/models/deepseek/deepseek-v4.1-flash-1017/endpoints`, `GET /api/v1/endpoints/zdr`): the model id exists ("DeepSeek V4.1 Flash 1017", the 2026-10-17 snapshot) with 50 upstream endpoints. 43 of them are on the ZDR list, including `nebius/fp8` (Nebius, Amsterdam-based, 0.12/0.48 USD per Mtok) and `mistral/fp8` (Mistral, Paris, 0.24/0.96). DeepSeek's own endpoint (`deepseek`) is not ZDR. The listing gives no region per endpoint; some tags say `/us`, none says `/eu`. So "an EU provider with ZDR" is answered only as far as the company: Nebius and Mistral are EU companies on the ZDR list, but where they run this model is not public. OpenRouter's EU in-region routing (`eu.openrouter.ai`, Business/Enterprise plan) keeps prompts in the EU regardless of upstream; it has no request switch, only the base URL — hence the second config file. `allow_fallbacks: false` with `order: ["nebius/fp8"]` pins one upstream endpoint and quantisation, which matches "one model version and endpoint per scope".

A 429 is not an attempt: it costs nothing and says nothing about the model, so it gets no row and does not count toward the 6 attempts or the fallback share; the log line keeps it visible. The limiter is in-process because `worker-ai` runs one process (concurrency 1 by default); several replicas would each get the full rpm (NFR-3 load test, deferred in the spine).

## Verification

**Commands:**
- `cd backend && uv run ruff check . && uv run ruff format --check .` -- expected: clean
- `cd backend && uv run pytest -n0 tests/ai tests/players/test_llm_jobs.py tests/test_sim_endpoint.py tests/test_migrations.py tests/test_imports.py -q` -- expected: pass
- `cd backend && uv run pytest --cov=app/engine --cov=tests/engine --cov-fail-under=100` -- expected: pass, once before commit

## Auto Run Result

Status: done (the only open item is the real-call probe, which needs the founder's key)

**Summary:** the gateway can now call a real OpenAI-compatible endpoint, OpenRouter first.
- `app/ai/adapters.py` (new): the adapter registry (`openai_compatible`: pydantic-ai `OpenAIChatModel` over `AsyncOpenAI` with the config's base URL, the key from the named variable, SDK retries off) and the router registry (`openrouter`: always `allow_fallbacks: false`, `data_collection: deny`, `zdr: true`, plus the config's `order`/`only`/... preferences; never `models` or `route`). `availability()` decides mock / real / refused for the gateway and the sim CLI. A router endpoint without `routing` is refused, also for rows stored before 0010.
- Config field `routing` (validated); Effort-level `provider_params` other than seed/temperature go into `extra_body`; request fields that would override the model, prompt, schema or routing are refused. `provider` is validated against the registry, so a second provider is one adapter entry and one config row.
- `app/ai/ratelimit.py` (new): in-process limiter per (endpoint, key variable), spacing starts `60/rpm` s apart; one injectable clock for the gateway (tests use a skipping clock, no real sleeps).
- Gateway: real endpoints wait for a slot inside the deadline; HTTP 429 writes no row and uses no attempt, waits `Retry-After` (else 1, 2, 4 ... s, between 0.25 and 30 s) while the deadline allows; a 4xx that cannot succeed (401, 400, 404) ends the call; rows store `served_model` and `served_by`.
- `python -m app.sim run` exits 2 with `error key_missing: <VAR> is not set` outside local/test/ci, and notes the mock in those three.
- `python -m app.sim endpoint --config ID [--orders 3] [--burst 5]` (new, via `app/ai/endpoint.py`): model listing, valid Orders, served model/provider, burst with 429 count and slot waits, latency, tokens, cost; `endpoint ok` / `endpoint failed: ...`.

**Real-call probe: not run: needs the founder's key.** Exact commands (compose `postgres` running, key in the environment):
```sh
cd backend
uv run python -m app.ai.cli config add ai-configs/openrouter-deepseek.json   # or openrouter-deepseek-eu.json (eu.openrouter.ai, Business plan)
uv run python -m app.ai.cli budget set --evaluation <ID> --limit 1 --reserve 0
uv run python -m app.sim endpoint --config <ID>
```

**Files:**
- `backend/app/ai/{adapters,ratelimit,endpoint,calls}.py` (new): adapters and routers, limiter and clock, probe, `llm_call` read.
- `backend/app/ai/{gateway,config,models,mock}.py`: adapter use, limiter, 429 back-off, final 4xx, served fields; `routing`, reserved params, registry-validated provider; columns; `mock.RATE_LIMITED`.
- `backend/migrations/versions/0010_ai_routing.py` (new): `ai_model_configs.routing`, `llm_call.served_model/served_by`, drops `ck_ai_model_configs_provider`.
- `backend/app/sim.py`: key check in `run`, `endpoint` command.
- `backend/ai-configs/openrouter-deepseek.json` (global router, `nebius/fp8`, fp8, 0.12/0.48), `openrouter-deepseek-eu.json` (new, `eu.openrouter.ai`).
- `backend/pyproject.toml`, `uv.lock`: `pydantic-ai-slim[openai]`, `httpx2`.
- `README.md`: the probe commands.
- Tests: new `tests/ai/test_adapters.py`, `tests/ai/test_ratelimit.py`, `tests/test_sim_endpoint.py`; burst test in `tests/players/test_llm_jobs.py`; `tests/conftest.py` refuses every real request and installs the skipping clock; updates in `test_gateway.py`, `test_config.py`, `test_cli.py`, `test_migrations.py`, `test_imports.py`.

**Review:** one pass, 4 layers, 43 findings (high 0, medium 7, low 25, false 7, maybe-false 4).
- Patched by verdict: medium 6 entries (provider registry and DB check; router without routing; untested retry reservation; non-retryable 4xx; reserved request fields; gap tests), low 12 (Retry-After cap and non-finite, served-model match, `httpx2` declared, `missing_key` field, exit code and help, tautological assert, slot boundary, wait label, JSON null, README note).
- Deferred: per-process limiter; served model not checked in production (both medium, unverified).
- Rejected, with reasons in the triage log: default config URL (founder's), mock not paced, job-level retired endpoint, batch-level pacing, limiter min-rpm, no row for 429, client cache, near-zero first timeout, other rare test gaps, fixture imports, mistyped seed (pre-existing), cancel during slot sleep, GatewayError in burst; false: error scrubbing, Effort level, private hook, prices, empty requests, stored rows, cache.

**Follow-up review recommended:** true. Six medium entries were patched after the reviewers read the code, unseen by them: notably the provider now validated against the adapter registry with 0010 dropping the DB check, and the early stop on non-retryable 4xx inside the retry loop.

**Verification:**
- `ruff check`, `ruff format --check`: clean.
- Full suite with coverage: 1371 passed in about 55 s; engine coverage 100 %; golden outputs unchanged.
- Matrix audit: every row has a passing test in `test_adapters.py`, `test_ratelimit.py`, `test_llm_jobs.py` or `test_sim_endpoint.py`.
- No real endpoint was called; no key was read.
- New tests over 1 s (under xdist, each first test of a process includes the pydantic-ai/openai import): the three probe/run tests in `test_sim_endpoint.py` (about 2.2 s, each plays an 8-Week Rule-based Game or a short batch), `test_a_burst_of_429s_...` (about 1.8 s).

**Decisions taken in place of the founder:**
1. Main config `openrouter-deepseek.json` uses the founder's base URL `https://openrouter.ai/api/v1`, pinned with `order: ["nebius/fp8"]`, `allow_fallbacks: false`, ZDR, no data collection, `require_parameters: true`, quantisation fp8, prices 0.12/0.48 USD per Mtok, region label `eu-provider`. A second file keeps `eu.openrouter.ai` (EU in-region, Business/Enterprise plan).
2. Nebius chosen as the one upstream: an EU company on OpenRouter's ZDR list at the lowest ZDR price among EU companies; where it runs the model is not public (Design Notes).
3. A 429 writes no `llm_call` row and does not count as an attempt or toward the fallback share; it is logged.
4. Back-off: `Retry-After`, else 1, 2, 4 ... s; clamped to 0.25–30 s; without a deadline, 10 consecutive 429s give `provider_error`.
5. The limiter is per process and spaces starts evenly (no burst allowance); the mock is not paced.
6. A 4xx other than 408/409/425/429 stops the call after one row.
7. The provider DB check constraint is dropped; the registry in code is the one list.
8. The probe plays one stored 8-Week Rule-based Game when no finished Game exists.

**Residual risks:**
- The real call is unverified until the founder runs the probe (model id form, `provider` field, response_format support, `eu.openrouter.ai` access on the plan).
- Migration 0010 was changed after its first run: the shared test databases `olspillet_test`, `olspillet_test_gw0`–`gw11` and the `olspillet_test_migrations*` copies at 0010 had `ck_ai_model_configs_provider` dropped by hand (the new upgrade step); none was dropped. The dev database `olspillet` is still at 0009.
- CI has not run; nothing was pushed.
