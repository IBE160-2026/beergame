# Epic 2 Context: LLM players that are safe to teach with

<!-- Generated from planning artifacts. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Make LLM players safe to put in front of Students: every non-student Seat gets its Order from one order source, every LLM call goes through one gateway that pins the model, validates the answer, logs each attempt, enforces time and cost limits and falls back to the Rule-based Order, and a Play guard switches drifting LLM Seats to Rule-based. When done, the founder can run batches of simulated all-AI Games and read cost, tokens, latency, retries, fallback share, Play guard switches and run-to-run variation per model config and Effort level, and the Admin can register, measure, approve and pin a model config and set a cost limit from the command line. No login and no screens yet (Admin screens come in Epic 15). The epic owns `backend/app/ai/` (the only LLM boundary) and `backend/app/modules/players/`, and adds `platform/jobs` plus the `worker-ai` and `worker-batch` processes.

## Stories

- Story 2.1: Give every non-student Seat its Order from one order source
- Story 2.2: Register a model config and an evaluation budget from the command line
- Story 2.3: Make a validated LLM call through the gateway and log every attempt
- Story 2.4: Ask an LLM player for an Order from the Seat state alone
- Story 2.5: Place LLM Orders as jobs, with the Rule-based Order as fallback
- Story 2.6: Keep every LLM Order inside its time budget
- Story 2.7: Call a real EU endpoint within its rate limit
- Story 2.8: Reserve budget per call and switch to Rule-based players at the cost limit
- Story 2.9: Store a near-optimal reference Order for every Seat and Week
- Story 2.10: Switch a drifting LLM Seat to a Rule-based player with the Play guard
- Story 2.11: Measure a model and Effort level on batches of simulated Games
- Story 2.12: Offer only measured Effort levels and pin the model
- Story 2.13: Describe each AI player type in plain Norwegian

## Requirements & Constraints

- **Same information as a human:** an LLM player sees only what a Student in that Seat would see (the `SeatState`), framed as a supply chain manager's job, never as a game; no Week count, no future demand, no other Seat's numbers, customer demand only for the Retailer; no personal data; no model call in Guided Weeks. Prompt must not contain words for game/player, Seat count, chain total, or "Weeks advance when everyone has ordered".
- **Validated Orders with fallback:** schema-bound JSON with one whole-number Order in 0..max Order; invalid answers are retried (at most 6 attempts per Order); on any typed failure the stored Rule-based reference Order is placed for that Week only, marked with the failure type. Occupancy stays `llm`, so the model is asked again next Week.
- **Time:** each Effort level has a per-attempt timeout and a per-Order time budget (retries included); values are placeholders until the prototype (only figure so far: 8 s p95). Playout calls (Epic 8) run without a deadline.
- **Cost:** budget reserved per attempt against one row; player purposes may spend only `limit − reserve`; at the limit, every LLM Seat in the scope switches to Rule-based for the rest of the scope's life. Targets: at most USD 0.10 per Game and USD 0.50 per Student per Class session; pass lines come from the batch file, never from code defaults.
- **Model pinning:** one model version, endpoint and prompt versions per scope; no router or provider fallback ever; a referenced config is immutable (edits create a new row); only measured, approved, endpoint-supported Effort levels are offered.
- **Play guard:** compares `decided_by = llm` Orders to the Rule-based and near-optimal references over a rolling window; never switches before a minimum number of Weeks; band parameters, distance measure, window and near-optimal algorithm are versioned placeholders (issue #20).
- **Logging:** one `llm_call` row per attempt (caller reference, config id, model, quantisation, provider, endpoint, Effort level, seed/temperature, prompt version, input/output/reasoning tokens, cost, latency, outcome); `seat_week` rows carry the `llm_call` ids; `decided_by` and `fallback` are separate fields.
- **Reliability:** no Game stalls on provider failure; no Game left complete but open.
- **Privacy:** no names, emails or student numbers reach a provider; free text scrubbed (empty term list for evaluation scopes); EU-region, zero-retention, no-training routes where switches exist.
- **Copy:** player descriptions in Norwegian bokmål, use «enheter», never «øl», «Beer Game» or «bullwhip».

## Technical Decisions

- **LLM provider (Issue #9, decided):** OpenRouter with model `deepseek/deepseek-v4.1-flash-1017`, reached through the `openai_compatible` adapter with the base URL injected from the model config. The deterministic **mock provider is the default locally and in CI** (`APP_ENV` = `local`/`test`/`ci` with no key); with `APP_ENV=production` the mock is never used. **Only Stories 2.7 and 2.11 may call a real endpoint**, and only by hand on the founder's machine; CI never does. Router fallback must be turned off and zero retention / no data collection requested in the request.
- **Gateway:** `ai.run(purpose, budget_scope, inputs, output_schema, deadline)` is the only LLM entry point. `inputs` = render values + caller reference (ids only, stored, never rendered) + optional mock answer. Returns a validated result or a typed failure (`timeout`, `invalid_output`, `budget_exhausted`, `provider_error`) carrying `llm_call` ids; never raises provider exceptions. Retries run in the gateway's own loop with pydantic-ai `output_retries=0`. Only `app/ai` imports pydantic-ai or provider SDKs; `FallbackModel` is banned (CI import check).
- **Config and budget:** owned by `app/ai`, accessed only via `ai.config` and `ai.budget`. Effort levels are data on the config (name, provider params, per-attempt timeout, per-Order time budget). Credentials are never stored, only the env var name. Budget money is `NUMERIC(18,8)` USD; reservation is one conditional `UPDATE`, never a sum over `llm_call`. CLI: `python -m app.ai.cli config add|edit|list|show`, `budget set`, `cost`, `pin`.
- **Prompts:** files at `backend/app/ai/prompts/<purpose>/v<N>.md`; a CI test fails if a version referenced by any stored config is missing or its hash changed.
- **Order source (AD-5):** `players.ensure_order(game, seat)` is the one order source for non-student occupants. Guided / `rule_based` / `scripted` place in the opening transaction; `llm` defers one `ai-orders` procrastinate job keyed `(game, week, seat)` on the same connection, id-only args. The job calls `ai.run` once and never retries; duplicate delivery gets `409 order_exists` and ends cleanly.
- **Commands (AD-2):** new `games.commands.advance(game)` (exactly one Week per transaction; every command loops it after commit) and `switch_to_rule_based(game, seat, reason)` (append-only occupancy). `games.service.budget_scope(game)` decides which budget a Game charges. `games.rules.turn_times` alone computes `ai_deadline_at`.
- **Workers (AD-9, AD-24):** `worker-ai` (`--queues ai-orders`) and `worker-batch` (`--queues llm-batch`) from the backend image; procrastinate schema via Alembic. `worker-ai` runs a 5-second rescue loop placing timeout fallbacks and advancing complete Weeks.
- **Pure functions (AD-1):** `engine.near_optimal.order(...)` (label `placeholder-0`), `analysis.play_guard.evaluate` and `is_calibrated`; no I/O, no clock. Both references computed once per Seat when the Week opens and stored on `seat_turns`, copied into `seat_week` by `place_order`. The Play guard runs inside `place_order`, never in the job.
- **Simulation (AD-22):** `python -m app.sim run|report|approve|probe|prompt|describe`; LLM occupants run through the real players/jobs/gateway path with `purpose = simulation`, config id and Effort level frozen into `SessionRuntime`, charged to the config's evaluation budget. New tables: `simulation_batches` and `games.batch_id` (owned by `modules/games`), `effort_measurements` (owned by `app/ai`). Mock batches are labelled as such and can never be approved or pinned.
- **Zero-config (AD-17):** in local/test/ci with no stored config, a `mock` model config with one Effort level, a mock measurement, an evaluation budget, pinned as default, is seeded; nothing is seeded in production.
- **Module boundaries:** `players` reaches game state only via `games` service/commands; `modules/games` has no LLM/provider import; `app/ai` imports nothing from `modules`. Schema changes are expand-only Alembic revisions.
- Folder naming: code lives in `backend/` (FastAPI, uv) and `frontend/` (Next.js); older docs saying `api/`/`web/` mean these.

## Cross-Story Dependencies

- Builds on Epic 1: engine, `SeatState`, Rule-based reference on `seat_turns`, `scripted` occupants and occupancy (1.7), `place_order`/`finish` (1.9), simulation runner (1.11) whose order loop 2.1 removes; golden results must stay identical.
- In-epic order: 2.1 → 2.2 → 2.3 → 2.4 → 2.5 → 2.6/2.7/2.8; 2.9 before 2.10; 2.11 needs 2.5–2.10; 2.12 needs 2.11; 2.13 is checked against 2.4's prompt rules.
- Later epics consume: Epic 3 (`platform/notify`) and Epic 15 (cost view) read `ai.budget.state`; Epic 5 creates Class session budgets via `ai.budget` and reads `ai.config.offered_effort_levels` and the pinned default; Epic 8 uses no-deadline calls on `llm-batch` for playout and adds queues/sweeper to `worker-batch`.
- Open placeholders: Effort level values, timeouts, reserve size (issue #8); Play guard parameters and near-optimal algorithm (issue #20); Rule-based parameters (issues #8, #17); model-recognition probe (issue #19).
