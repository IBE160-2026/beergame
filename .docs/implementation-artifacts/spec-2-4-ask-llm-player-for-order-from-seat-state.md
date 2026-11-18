---
title: 'Story 2.4: Ask an LLM player for an Order from the Seat state alone'
type: 'feature'
created: '2026-11-18'
baseline_revision: '90113f6623cb8828a82c92bb36c70e9f565e2d61'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-2-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** The gateway from Story 2.3 can make a validated call, but there is no player prompt, no code that turns a Seat's `SeatState` into prompt values, no Order schema bound to the Seat's Order range, and no way to look at the exact prompt or to probe whether a model recognises the exercise (FR-31, FR-32, AD-3, AD-6, C-1, issue #19).

**Approach:** Add `app/modules/players/llm.py` (`build_inputs`, `order_schema`, `request_inputs`), the prompt files `player_order/v1.md` and `recognition_probe/v1.md` (locked), a `recognition_probe` purpose, a public `gateway.preview` that returns the exact request without calling a model, and `python -m app.sim prompt` and `python -m app.sim probe`.

## Boundaries & Constraints

**Always:**
- `build_inputs(seat_state: SeatState) -> dict[str, Scalar]` is pure: it reads only its argument (no query, no `table_status`, no settings, no demand series). Values: role label and role-specific wording, incoming order, incoming delivery, shipped, inventory, backlog, overdue, position, supply line (as a text list with "in N weeks" relative to the open Week and its stage), order lead time (`preview.order_arrival_week - week`), holding and backorder rates (from `cost_lines`), this Week's cost, own Total cost, min and max Order, and the Seat's own history as a text table. No absolute Week number is rendered: time is relative ("N weeks ago", "in N weeks"), so no Week count or horizon reaches the model.
- Customer wording ("end customers", "customer demand") only for the Retailer; every other Role's incoming order is "orders from your customer business" without the word "customer demand". Role is the only Seat identity; upstream/downstream are generic ("your supplier", "your customers"); the last Role (any `in_production` slot) is told it produces.
- `order_schema(min_order, max_order)` returns a cached pydantic model named `OrderDecision` with one field `order`: strict int, `ge=min_order`, `le=max_order`. Missing, non-integer (also `4.5` and `"4"`), negative or above-max answers fail validation → the gateway's `invalid_output` and retry (Story 2.3 loop).
- `request_inputs(game_id, seat_id, week, seat_state, reference_order) -> gateway.Inputs`: `values = build_inputs(seat_state)`, `caller = {"game", "seat", "week"}`, `mock_answer = {"order": reference_order}`.
- Prompt `player_order/v1.md` (English, `$name` template): situation of a supply chain manager; rules of the job: delays (order lead time), must ship what is ordered plus backlog as far as stock allows, the two costs; asks for the best Order for this stage of the supply chain to keep its own cost low over time; says the business continues with no last week; asks for JSON `{"order": <whole number>}`. It never contains a word for game/player/play/seat/simulation/beer, a number of stages, the chain's total, or that Weeks advance when everyone has ordered.
- `gateway.preview(purpose, inputs, output_schema, budget_scope=None) -> Preview(prompt_version, request)`: same resolution, scrubbing and rendering as `run` (config, Effort level, prompt version, model settings); no budget check, no model, no row. Without a scope: newest prompt file version of the purpose, no terms, empty settings. `run` stores the same `request` dict as `preview` returns.
- Purpose `recognition_probe` (3 attempts, not a player purpose); its prompt renders `$player_prompt` and adds one question asking whether the situation matches a known exercise, game, case or textbook example; output `ProbeAnswer(recognised: bool, name: str, explanation: str)`.
- `sim prompt <game_id> --seat <role|id> [--config <id>]`: reads `seat_state` and `open_turn` of the open Week through `games.service`, prints `prompt_version`, the prompt, then the JSON schema and model settings; notes a Guided Week on stderr; refuses a finished Game (`game_finished`, exit 1). With `--config` the request is resolved for that config (its evaluation scope).
- `sim probe --config <id> [--sample N=4] [--seed S=0] [--game ID ...]`: samples `state_seen` of non-Guided Decision log rows from the given Games (default: the 10 newest finished Games) with `random.Random(seed)`, renders the player prompt via `preview` for the config, calls `gateway.run("recognition_probe", evaluation scope, …, deadline=None)` once per sample (caller = game, seat, week), prints each answer or failure with its `llm_call` ids. Places no Order. Exit 1 when nothing to sample or on a `GatewayError` (code printed).
- Shipped configs `backend/ai-configs/*.json` reference `player_order: 1` and `recognition_probe: 1`; both files locked in `prompts/hashes.json`.
- `players` may import `app.ai.gateway` (public AI surface) but no provider SDK; `players/service.py` and `games` stay free of `app.ai` imports (pydantic-ai is loaded only by `players/llm.py`); `app.sim` imports `players.llm` lazily.

**Never:** No job, no `ensure_order` change for `llm`, no `place_order` call, no model config on `SessionRuntime`, no schema/migration change, no real endpoint call, no name/email/student number in values.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Retailer prompt | Classic Week 6 state | role "retailer", "customer demand" present, own numbers | — |
| Wholesaler prompt | same Week | no "customer demand", "your customers" generic | — |
| Factory | last Role | told it produces, production lead time | — |
| Future demand | two Games differing only after Week 4 | prompts of Weeks 1–4 identical for every Role | — |
| Week count | same play, `weeks` 36 vs 50 | prompts identical for Weeks 1–36 | — |
| Other Seats | other Seats' numbers set to 7777 | prompt unchanged, no "7777" | — |
| Caller/mock | reference 777, ids | absent from prompt and request | — |
| Bad answers | `{}`, `4.5`, `"4"`, `-1`, max+1 | `invalid_output`, retried, then valid | — |
| `sim prompt` | running Game, `--seat wholesaler` | prompt + schema printed, exit 0 | finished Game → exit 1 |
| `sim probe` | finished Game, mock config | N answers printed, N `recognition_probe` rows, no `seat_weeks` change | no states → exit 1 |

</intent-contract>

## Code Map

- `backend/app/modules/games/schemas.py:122` -- `SeatState` (extends engine `SeatView`): role, inventory, backlog, incoming_orders, supply_line, order_history, week, incoming_order/delivery, shipped, supply_line_slots (stage, quantity, arrival_week), overdue, position, cost_lines (kind, rate), week_cost, total_cost, history (`WeekValues`), min/max_order, preview (`order_arrival_week`).
- `backend/app/modules/games/views.py:32` -- `build_seat_state(settings, states, orders, role)` pure; tests use it with engine `initial_state`/`advance` to render every Role and Week.
- `backend/app/modules/games/service.py` -- `seat_state`, `open_turn`, `get_game`, `decision_log`, `finished_game_ids`, `ViewError` for the sim commands.
- `backend/app/ai/gateway.py` -- `_prepare` (refactor: shared resolution for `run` and `preview`), `Inputs`, `Scalar`, `run`.
- `backend/app/ai/prompt_files.py` -- `load`, `files`, `lock`; add a `latest(purpose)` helper.
- `backend/app/ai/purposes.py` -- add `recognition_probe`.
- `backend/app/sim.py` -- argparse `build_parser`, `_run`, `_report`, `db.dispose()` pattern; add `prompt` and `probe`.
- `backend/app/engine/rules` / `app.engine` -- `initial_state`, `advance`, `rule_based` for engine-only test games (see `app/sim.py:_trace`).
- `backend/tests/test_imports.py` -- players rule: allow `app.ai.gateway`.
- `backend/tests/ai/conftest.py` -- autouse tmp prompts dir: add `recognition_probe/v1.md`; `tests/ai/helpers.mock_config`.
- `backend/tests/games/helpers.py` -- `classic_game`, `seat_student` (running Game for `sim prompt`).

## Tasks & Acceptance

**Execution:**
- `backend/app/ai/gateway.py`, `prompt_files.py`, `purposes.py` -- `preview`/`Preview`, `latest`, `recognition_probe`.
- `backend/app/ai/prompts/player_order/v1.md`, `recognition_probe/v1.md`, `hashes.json` -- prompts, locked.
- `backend/ai-configs/mock.json`, `openrouter-deepseek.json` -- prompts map.
- `backend/app/modules/players/llm.py` (new) -- `build_inputs`, `order_schema`, `request_inputs`, `ProbeAnswer`.
- `backend/app/sim.py` -- `prompt`, `probe` subcommands and docstring.
- Tests: `tests/players/test_llm_prompt.py` (leak, invariance, wording, schema, bad answers through the gateway), `tests/test_sim_prompt.py` (prompt and probe commands); update `tests/test_imports.py`, `tests/ai/conftest.py`.

**Acceptance Criteria:**
- Given the repository, when the prompt-file test runs, then both new prompt files are locked and every shipped config reference is locked.
- Given CI commands locally, then ruff is clean, the full suite passes, engine coverage stays 100 %, and no new test takes over 1 s (or it is reported).

## Spec Change Log

## Review Triage Log

### 2026-11-18 — Review pass
- verdicts: 40 findings — high 0, medium 9, low 24, false 7, maybe-false 0
- findings:
  - `[low]` `[patch]` (blind) every `ValueError` (incl. pydantic `ValidationError`) printed as `config_not_found` — only the new `ConfigIdError` from `_scope` maps to that code; others reach `_report`.
  - `[medium]` `[patch]` (blind) `--seat` with a non-canonical Seat id crashes (`StopIteration` → `RuntimeError`) — `_seat_id` compares parsed UUIDs and raises `seat_not_found`; test with an upper-case id.
  - `[medium]` `[patch]` (blind) probe loses answers already charged when a later sample fails — each answer is printed (flushed) as it returns.
  - `[low]` `[reject]` (blind) probe prompt scrubbed twice — the probe runs only on evaluation scopes, whose term list is empty by the AC; the probe's offset maps are unused.
  - `[low]` `[patch]` (blind) `prompt` does not say where its version came from — header ends `from config` / `from newest file`.
  - `[low]` `[patch]` (blind) no note when the Seat has already ordered — stderr note added.
  - `[low]` `[patch]` (blind) history length reveals elapsed Weeks, contradicting the docstring — a Student sees the same history; docstring now says elapsed Weeks are visible, the Week count (what is left) is not.
  - `[low]` `[reject]` (blind) Role wording keyed to Classic Role names — Epic 2 plays the Classic chain only; `SeatState` has no chain position and adding one is a schema change beyond this story; noted in the module docstring.
  - `[medium]` `[patch]` (blind) probe prompt carries two answer formats — `llm.without_answer_format` drops the player prompt's answer paragraph; test asserts `{"order": N}` absent from probe requests.
  - `[medium]` `[patch]` (blind) probe failure paths untested — test with three scripted invalid answers asserts the failure line and exit 1; redundant `!= []` assertion removed.
  - `[low]` `[patch]` (blind) `--config` test cannot tell config path from default — gateway preview test (see verification-gap row).
  - `[low]` `[patch]` (blind) import test misses an indirect `players.llm` import — test forbids importing `app.modules.players.llm` from `players` and `games`.
  - `[low]` `[patch]` (blind) stored configs lack `recognition_probe` — probe help names `config edit ID --prompt recognition_probe=v1`.
  - `[medium]` `[patch]` (edge) non-canonical Seat id crash — same fix as the blind row.
  - `[low]` `[patch]` (edge) unrelated ValueError mislabelled — same fix as the blind row.
  - `[medium]` `[patch]` (edge) answers lost on a mid-loop error — same fix as the blind row.
  - `[low]` `[patch]` (edge) probe exits 0 when every sample failed — exit 1 when no sample got an answer; summary `probed N answered=A recognised=R`.
  - `[low]` `[patch]` (edge) no note when the Seat already ordered — same fix as the blind row.
  - `[low]` `[patch]` (edge) duplicate `--game` samples a state twice — ids de-duplicated; test passes the same id twice.
  - `[low]` `[reject]` (edge) non-Classic chain order mislabels Roles — same as the blind Role row.
  - `[false]` `[reject]` (edge) `cost_lines` may lack a kind — `engine.seat_detail` always builds both lines; `SeatState` schema version 1 is the only one.
  - `[false]` `[reject]` (edge) `min_order > max_order` or reference outside range — `min_order` is 0 and `max_order` ≥ 1 by `RANGES`; the reference is a stored engine Order in range.
  - `[low]` `[reject]` (edge) newest file may be unlocked — the prompt-file CI test fails on any unlocked file; the header now says `from newest file`.
  - `[low]` `[reject]` (edge claim) "newest" Games ordered by creation, not finish — UUIDv7 creation order as `check --all`; irrelevant for a sample.
  - `[low]` `[reject]` (edge claim) a non-last factory is told it produces — Classic chain only, as above.
  - `[low]` `[patch]` (verification-gap) `preview` config and default paths indistinguishable — gateway test: config names v1 with seed/temperature while v2 exists; scoped preview equals the stored request.
  - `[low]` `[patch]` (verification-gap) Guided filter untested — probe with `--sample 1000` asserts the count equals non-Guided rows and the first sampled Week follows the Guided Weeks.
  - `[low]` `[patch]` (verification-gap) default "newest finished Games" path never run with data — the same test runs without `--game`.
  - `[low]` `[patch]` (verification-gap) failure output never run — same test as the blind row.
  - `[medium]` `[patch]` (verification-gap) `--seat <Seat id>` never run — same fix and test as the Seat-id row.
  - `[medium]` `[patch]` (verification-gap other) non-canonical Seat id crash — same fix.
  - `[false]` `[reject]` (intent 1) leak checks split across tests, not "the same test" — every clause has a passing test over every Role and Week; `run` stores exactly the previewed request.
  - `[false]` `[reject]` (intent 2) future demand proven only up to Week 4 — invariance is the stronger proof: any leaked future value would make Weeks 1–4 differ.
  - `[false]` `[reject]` (intent 3) other-Seat test goes through the views layer — that is the real path of every `SeatState`; `7777` never appears.
  - `[low]` `[reject]` (intent 4) strict int rejects `4.0` — FR-32 asks for a whole number; the schema states `integer`.
  - `[false]` `[reject]` (intent 5) provider-side payload not tested — the gateway hands `NativeOutput(schema)` (Story 2.3 tests); no real adapter before 2.7.
  - `[medium]` `[patch]` (intent 6) probe keeps the Order answer line — same fix as the blind answer-format row.
  - `[low]` `[patch]` (intent 7) `prompt --config` equality hides the config path — same as the verification-gap preview row.
  - `[false]` `[reject]` (intent 8) changes outside the named surface — `preview`, config prompt maps and test updates are needed by the AC; no Story 2.5 work present.
  - `[low]` `[reject]` (intent 9) Role names appear in prompts — the AC requires the Seat to be referred to by Role.

## Design Notes

Relative time instead of Week numbers keeps both the Week count and the end of the horizon out of the prompt while giving the model everything a Student sees about its own Seat. The leak test uses invariance (same prompt when only future demand, the Week count or other Seats change) rather than searching numbers, because small numbers like 4 and 8 recur everywhere. The schema is cached per `(min, max)` so the pydantic model name and JSON schema stay stable across calls.

## Verification

**Commands:**
- `cd backend && uv run ruff check . && uv run ruff format --check .` -- expected: clean
- `cd backend && uv run pytest tests/players tests/ai tests/test_imports.py tests/test_sim_prompt.py -q` -- expected: pass
- `cd backend && uv run pytest --cov=app/engine --cov=tests/engine --cov-fail-under=100` -- expected: pass, once before commit

## Auto Run Result

Status: done

**Summary:** `players.llm.build_inputs(seat_state)` builds the `player_order` prompt values from the `SeatState` alone, with no query, no settings, no demand series and no Week number; time is relative ("N weeks ago", "in N weeks"). Customer wording goes only to the Retailer, and the Factory is told it produces. `order_schema(min, max)` is a strict `OrderDecision` model holding one whole-number Order in range. `request_inputs` puts the caller reference (Game, Seat, Week) and the mock answer (the Rule-based reference Order) in their own parts of `gateway.Inputs`. The prompt `player_order/v1.md` frames a supply chain manager's job: delays, the duty to ship, two costs, the best Order for this part of the chain, and a business that continues. `recognition_probe/v1.md` is the probe prompt. Both are locked, and the shipped configs reference both. The new public `gateway.preview` returns the exact request `run` would store, without calling a model. `python -m app.sim prompt <game> --seat <role|id> [--config]` prints that request. `python -m app.sim probe --config <id>` sends a seeded sample of stored non-Guided Seat states under the `recognition_probe` purpose, charges the evaluation budget, prints each answer and places no Order.

**Files:**
- `backend/app/modules/players/llm.py` (new): `build_inputs`, `order_schema`, `request_inputs`, `without_answer_format`, `ProbeAnswer`.
- `backend/app/ai/prompts/player_order/v1.md`, `recognition_probe/v1.md` (new), `prompts/hashes.json`: the prompts and their lock.
- `backend/app/ai/gateway.py`: `_prepare` split into shared helpers; new `preview`/`Preview`.
- `backend/app/ai/prompt_files.py`: `latest`. `backend/app/ai/purposes.py`: `recognition_probe` (3 attempts, not a player purpose).
- `backend/app/sim.py`: `prompt` and `probe` subcommands (lazy gateway import).
- `backend/ai-configs/*.json`: prompts map `player_order: 1, recognition_probe: 1`. `backend/app/modules/players/__init__.py`: docstring.
- Tests:
  - New: `tests/players/test_llm_prompt.py`, `tests/test_sim_prompt.py`.
  - Updated: `tests/ai/test_gateway.py` (preview), `test_prompt_files.py` (`latest`, two prompt files), `test_cli.py`, `test_config.py`, `helpers.py` (`mock_config` starts with an empty prompts map), `conftest.py` (tmp `recognition_probe/v1.md`), `tests/test_imports.py` (only `players/llm.py` may import `app.ai.gateway`; nothing in `players` or `games` may import `players.llm`).

**Review:** one pass, 4 layers, 40 findings (medium 9, low 24, false 7; grouped into 20 root causes).
- Patched:
  - Seat-id resolution, which had crashed on a non-canonical id.
  - `ConfigIdError`.
  - The probe now prints as it goes, exits 1 when no sample got an answer, drops the player prompt's answer format and de-duplicates `--game`.
  - `prompt` shows where its prompt version came from and notes a Seat that has already ordered.
  - Docstring on elapsed Weeks; help text for old configs.
  - New tests for preview's config path, the Guided filter, the default sample path, failures, Seat ids and indirect imports.
- Deferred: none.
- Rejected, with reasons in the triage log: Classic-only Role wording, a double scrub over empty evaluation terms, the strict integer check, and the descriptive intent notes.

**Follow-up review recommended:** true. Patched root causes at medium: 4 (Seat id, lost answers, answer format, probe failure tests). The unverified risk: no second review has seen the restructured `probe` loop (incremental output, exit code) or `without_answer_format`'s reliance on the prompt's last paragraph.

**Verification:**
- `ruff check`, `ruff format --check`: clean.
- Full `pytest --cov=app/engine --cov=tests/engine --cov-fail-under=100`: 1271 passed in 49 s, engine coverage 100 %.
- New tests over 1 s: the four probe tests in `tests/test_sim_prompt.py`, at 1.5–2.2 s each under xdist and 1.0–1.4 s with `-n0`. Each stores and plays a short 8-Week Game. The other new tests take under 0.3 s.
- Matrix audit: every row has a passing test in `tests/players/test_llm_prompt.py` or `tests/test_sim_prompt.py`.

**Decisions taken in place of the founder:**
1. The prompt is in English and gives no absolute Week number, only relative time. It shows the Seat's own full history, as a Student sees it.
2. Customer wording goes to the `retailer` and production wording to the `factory`, or to any Seat with goods in production. This fits the Classic chain only.
3. The Order schema is strict: `4.0`, `"4"` and extra keys are invalid.
4. The probe has its own purpose, `recognition_probe`, at prompt v1: 3 attempts, and not a player purpose, so it may spend the reserve. It asks whether the text matches a known exercise, game, case or textbook example, omits the player prompt's answer line, and answers `{recognised, name, explanation}`.
5. The probe samples non-Guided `state_seen` rows from the `--game` Games, by default the 10 newest finished Games. `--sample` defaults to 4 and `--seed` to 0. It exits 1 when no sample got an answer.
6. Without `--config`, `sim prompt` renders the newest prompt file with no settings, because Games carry no model config until Story 2.5. With `--config` it resolves the request as `run` does.
7. The shipped configs reference `player_order: 1` and `recognition_probe: 1`. Configs already stored need `config edit`.
8. Only `players/llm.py` may import `app.ai.gateway`. `players/service.py` and `games` may not import `players.llm`.
9. Implementation ran in the orchestrator's own context, as the runbook requires. The four review layers were independent sub-agents.

**Residual risks:**
- CI has not run on GitHub, because nothing was pushed. No migration changed.
- No real model has seen the prompt yet. Stories 2.7 and 2.11 will show whether the wording works and whether models recognise the exercise.
