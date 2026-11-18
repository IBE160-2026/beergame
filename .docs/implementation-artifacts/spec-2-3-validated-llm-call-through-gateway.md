---
title: 'Story 2.3: Make a validated LLM call through the gateway and log every attempt'
type: 'feature'
created: '2026-11-18'
baseline_revision: '41b7d895f73d469ff5f31676638f10d1fc5731b3'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-2-context.md'
warnings: ['oversized']
deferred:
  - summary: >-
      A cancelled gateway call (job shutdown, killed worker, outer wait_for) writes no llm_call row for the attempt in flight and charges no cost.
    evidence: |-
      Blind review finding. gateway._attempt catches Exception, and asyncio.CancelledError is a BaseException, so the row and the budget charge are skipped. Story 2.6 tests killing the job mid-call and owns late-attempt logging; it should log the cancelled attempt (shielded) or document the gap.
    location: >-
      backend/app/ai/gateway.py _attempt / run
    severity: medium
---

<intent-contract>

## Intent

**Problem:** Nothing yet makes an LLM call: there is no single entry point that pins the model config, validates the answer, scrubs free text, logs each attempt with tokens and cost, and turns every provider problem into a typed failure, so later stories (2.4 player prompt, 2.5 jobs) would have to call a provider directly (FR-32, FR-67, FR-68, AD-6, AD-17, C-1).

**Approach:** Add `app/ai/gateway.py` with `run(purpose, budget_scope, inputs, output_schema, deadline)` built on pydantic-ai (`Agent`, `NativeOutput`, output retries 0) and a deterministic, scriptable mock provider; revision `0007` adds the `llm_call` table; `platform/pii.terms(scope)` plus an offset-mapping scrubber; prompt files with a hash lock and a check; an import check for provider SDKs.

## Boundaries & Constraints

**Always:**
- Dependency `pydantic-ai-slim==2.65.0` (no extras; the `openai` extra comes with Story 2.7). Only `app/ai` imports it. The pydantic-ai banner is off.
- `run` keeps five arguments. `budget_scope` is `ai.budget.BudgetScope`, which gains an optional `effort_level` (not part of equality; `None` = the config's first Effort level). An evaluation scope's config is `scope.id`; a `class_session` scope raises `GatewayError("scope_unresolved")` until Epic 5 binds sessions to configs.
- `inputs` = `Inputs(values, caller, mock_answer=None)`: `values` maps template names to scalars (`str`, `int`, `float`, `Decimal`, `bool`); `caller` maps names to ids (`UUID`, a UUID string, or `int`) and is stored on every row, never rendered; `mock_answer` is read only by the mock. Every `str` value is free text and is scrubbed before rendering.
- Purposes are registered in `app/ai/purposes.py` (`player_order`: 6 attempts, player purpose). Prompt version comes from the config's `prompts` map; file `PROMPTS_DIR/<purpose>/v<N>.md` rendered with `string.Template.substitute` (`$name`).
- Caller/config mistakes raise `GatewayError(code)` before any attempt: `unknown_purpose`, `scope_unresolved`, `config_not_found`, `budget_not_found`, `effort_level_unknown`, `prompt_not_in_config`, `prompt_missing`, `render_failed`, `inputs_invalid`. Everything else returns `Result(output, llm_call_ids, offset_maps)` or `Failure(kind, llm_call_ids, detail)`, kind ∈ `timeout | invalid_output | budget_exhausted | provider_error`; no exception from a provider or pydantic-ai escapes.
- Budget (until Story 2.8's reservation): if `spent ≥ limit`, or the purpose is a player purpose and `players_exhausted_at` is set → `budget_exhausted` with no rows. After each attempt its cost is added to `spent` in the same transaction as its row.
- Attempt loop: up to the purpose's limit; per-attempt timeout = min(Effort level `attempt_timeout_s`, time left to `deadline`); a past deadline stops the loop with `timeout`. Any failed attempt (invalid output, timeout, provider error) is retried while attempts and time remain; the returned kind is the last attempt's outcome, or `timeout` when the deadline ended the loop.
- Model choice: provider `mock` in `local|test|ci`, or any provider whose `credential_env` is unset in those envs → mock. In `production` the mock is never used: a mock config or a missing key → one row, `provider_error`, no retry. A set key for `openai_compatible` → `provider_error` "no adapter" (one row) until Story 2.7.
- `llm_call` row per attempt, committed in its own transaction: id, purpose, scope kind/id, caller_ref JSONB, model_config_id (FK), provider, endpoint, model_version, quantisation, effort_level, seed and temperature (from the level's `provider_params`, else null; also passed as model settings), prompt_version, attempt (1-based), input/output/reasoning tokens, cost_usd `NUMERIC(18,8)` = input×input price + output×output price per million (reasoning is inside output tokens in pydantic-ai), latency_ms, outcome ∈ `ok|invalid_output|timeout|provider_error` (CHECK), error, request JSONB (scrubbed prompt, output JSON schema, model settings), response text (scrubbed), started_at, created_at.
- Mock: deterministic. Script steps via `app.ai.mock.script(*steps)` (context manager, consumed one per attempt): `"timeout"` (sleeps past any timeout), `"invalid"` (non-JSON), `"error"` (provider exception), or a raw text. Unscripted: `mock_answer` as JSON if given, else a fixed answer derived from the output JSON schema (first enum/const, `minimum` or 0, `""` padded to `minLength`, `False`, `[]` padded to `minItems`, nested objects, `$ref`).
- Scrubber `app/ai/scrub.py`: case-insensitive whole-word matches of the terms (longest first) become `[REDACTED]`; returns `Scrubbed(text, offsets)` whose `original_span(start, end)` maps a scrubbed span to the original (a span touching a placeholder covers the whole term). `platform/pii.terms(scope)` returns `[]` for evaluation scopes and, with no identity tables yet, for Class sessions too.
- Prompt lock `PROMPTS_DIR/hashes.json` (`"<purpose>/v<N>"` → sha256 of the file text with `\r\n` → `\n`). `app/ai/prompt_files.check(references)` lists problems: referenced version missing, or not locked, or hash differs; any locked file changed or removed. CLI `python -m app.ai.cli prompts check` runs it over every stored config (exit 1 on problems); `prompts lock` adds hashes for unlocked files and never changes an existing entry.
- Import check: outside `app/ai`, nothing under `app/` imports `pydantic_ai`, `openai`, `anthropic`, `google.genai`, `google.generativeai`, `mistralai`, `cohere`, `groq`, `litellm`, `ollama`; `FallbackModel` appears in no file under `app/` or `migrations/`. Other packages may import `app.ai.gateway` besides `app.ai.config`/`app.ai.budget`.

**Never:** No reservation/settle protocol, rate limiter, real provider adapter, deadline column, job, player prompt file, `cost`/`pin` command, HTTP route, change to `ModelConfigSpec` or to games tables. No real endpoint call. No credential printed or stored.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Mock answer | mock config, `mock_answer={"order": 4}` | `Result` order 4, one `ok` row with caller_ref, tokens, cost, latency | — |
| Fixed answer | no mock answer | schema-fitting output; same inputs twice → same output | — |
| Invalid then ok | script `"invalid"` | two rows `invalid_output`, `ok`; `Result` | — |
| All invalid | script 6× `"invalid"` | six rows; `Failure(invalid_output)` with 6 ids | — |
| Out of range | mock answer `{"order": -1}` | counts as invalid, retried | — |
| Timeout | script `"timeout"`, tiny attempt timeout | row `timeout`, next attempt runs | — |
| Deadline passed | deadline in the past | `Failure(timeout)`, no rows | — |
| Provider error | script `"error"` ×6 | six `provider_error` rows; `Failure(provider_error)` | never raises |
| Production | `APP_ENV=production`, mock config | one row `provider_error`; mock not called | — |
| Budget exhausted | spent ≥ limit | `Failure(budget_exhausted)`, no rows | — |
| Scrub | term `Ola Nordmann` in a value | prompt and stored request carry `[REDACTED]`; offset map back to original | — |
| Caller ref | `{"game": uuid, "week": 3}` | stored on every row, absent from request | non-id → `inputs_invalid` |
| Prompt check | config refs v2 missing / v1 edited | check lists both | CLI exit 1 |

</intent-contract>

## Code Map

- `backend/app/ai/config.py` -- `PROMPTS_DIR` (tests monkeypatch it; read it at call time), `prompt_path`, `get`, `list_all`, `ModelConfig.effort_level`.
- `backend/app/ai/budget.py` -- `BudgetScope` (add `effort_level` field, `compare=False`), `get`; add `charge(scope, amount, session)` (one `UPDATE … SET spent_usd = spent_usd + :amount`).
- `backend/app/ai/models.py` -- add `llm_calls` Core table (`llm_call`); `MONEY`.
- `backend/app/ai/db.py` -- `transaction(session)` helper.
- `backend/app/ai/cli.py` -- add `prompts check|lock` subcommands in the existing argparse style.
- `backend/migrations/versions/0006_ai_config_budget.py` -- revision style to copy for `0007_llm_call.py`.
- `backend/app/platform/config.py` -- `get_settings().app_env`.
- `backend/tests/conftest.py` -- `AI_TABLES` truncation (add `llm_call` first), `ai_db`.
- `backend/tests/ai/conftest.py` -- autouse tmp `PROMPTS_DIR` with `player_order/v1.md`; `helpers.mock_config`.
- `backend/tests/test_imports.py` -- `imports()` helper, `AI_PUBLIC`, `AI_TABLES`.
- `backend/tests/test_migrations.py` -- head `0006` asserts → `0007`, `HEAD_TABLES`, AI CHECK map (add `ck_llm_call_outcome`).
- pydantic-ai 2.65: `Agent(model, output_type=NativeOutput(schema), retries={"tools": 0, "output": 0})`; invalid output raises `UnexpectedModelBehavior`; `capture_run_messages()` gives the last `ModelResponse` with `.usage` (`input_tokens`, `output_tokens`, `output_reasoning_tokens`); `FunctionModel(fn, model_name=...)`; `pydantic_ai.BANNER_ENABLED`.

## Tasks & Acceptance

**Execution:**
- `backend/pyproject.toml`, `uv.lock` -- add `pydantic-ai-slim==2.65.0`.
- `backend/app/ai/models.py`, `backend/migrations/versions/0007_llm_call.py` (new) -- `llm_call` table, outcome CHECK, index on (scope_kind, scope_id); downgrade drops it.
- `backend/app/ai/purposes.py` (new) -- `Purpose(name, attempt_limit, player)`, `PURPOSES`, `get(name)`.
- `backend/app/platform/pii.py` (new) -- `terms(scope)`.
- `backend/app/ai/scrub.py` (new) -- `scrub(text, terms) -> Scrubbed`, `OffsetMap.original_span`.
- `backend/app/ai/prompt_files.py` (new), `backend/app/ai/prompts/hashes.json` (new, `{}`) -- load, digest, lock, check.
- `backend/app/ai/mock.py` (new) -- `script()`, `fixed_answer(schema)`, `model(mock_answer, output_schema)` → `FunctionModel`.
- `backend/app/ai/gateway.py` (new) -- `Inputs`, `Result`, `Failure`, `GatewayError`, `run`.
- `backend/app/ai/budget.py`, `cli.py`, `__init__.py` -- `effort_level`, `charge`, `prompts` commands, docstring.
- Tests (new) `backend/tests/ai/test_gateway.py`, `test_scrub.py`, `test_prompt_files.py`, `test_mock.py`; update `tests/test_imports.py`, `tests/test_migrations.py`, `tests/conftest.py`.

**Acceptance Criteria:**
- Given the repository prompt dir, when the prompt-file test runs, then every file has a matching lock entry, every entry has its file, and every `prompts` reference in `backend/ai-configs/*.json` is locked.
- Given CI commands locally, then ruff is clean, the full suite passes, engine coverage stays 100 %, `alembic check` passes, and no new test takes over 1 s (except as reported).

## Spec Change Log

## Review Triage Log

### 2026-11-18 — Review pass
- verdicts: 51 findings — high 0, medium 7, low 34, false 10, maybe-false 0
- findings:
  - `[low]` `[reject]` (intent) entry point is `app.ai.gateway.run`, not an attribute `ai.run` — callers import `from app.ai import gateway as ai`; keeping `app/ai/__init__.py` empty avoids loading pydantic-ai (2 s) for every config read.
  - `[false]` `[reject]` (intent) `BudgetScope.effort_level` changes an interface — open-assumptions fixes `ai.run` at five arguments and the Effort level is frozen with the scope (AD-4, AD-22); the field is optional and outside equality.
  - `[false]` `[reject]` (intent) `GatewayError` is an extra raised channel — the AC forbids raising provider exceptions; GatewayError is raised only for caller/config mistakes before any attempt.
  - `[false]` `[reject]` (intent) retries widened to timeouts and provider errors — AD-6 step 5 makes up to 6 attempts within the deadline, and Story 2.6 starts the next attempt after a timed-out one.
  - `[low]` `[reject]` (intent) a row for the production refusal, none for budget/deadline refusals — matrix rows of the spec; a refusal that touched no model still names the config and reason.
  - `[low]` `[reject]` (intent) stored request is gateway-built, not the wire body — no real adapter exists before Story 2.7; the stored prompt, schema and settings are exactly what is handed to the model layer.
  - `[false]` `[reject]` (intent) prompt-hash CI test is vacuous — no prompt file exists before Story 2.4; the check logic is tested on a temporary directory and against DB rows via `prompts check`.
  - `[false]` `[reject]` (intent) Class session scopes raise `scope_unresolved` — there is no session-to-config binding before Epic 5.
  - `[false]` `[reject]` (intent) gateway scrub test patches `pii.terms` — the AC asks for a test with supplied terms; the real list is empty by the AC.
  - `[false]` `[reject]` (intent) mock determinism is trivial — the AC asks exactly that the same inputs give the same output.
  - `[false]` `[reject]` (intent) import check covers backend only — there is no Python outside `backend/`.
  - `[low]` `[reject]` (intent) `budget.charge` overlaps Story 2.8 — AD-6 forbids summing `llm_call` for limits, so `spent` must be kept from the first logged cost; 2.8 replaces it with reserve/settle.
  - `[low]` `[patch]` (verification-gap) deadline cap never asserted — test now asserts the timeout rows' total latency < 500 ms.
  - `[low]` `[patch]` (verification-gap) seed/temperature never shown to reach the model — the mock records `info.model_settings`; test asserts it.
  - `[low]` `[patch]` (verification-gap) default Effort level untested with two levels — test calls a scope with no level and asserts `standard` and empty settings.
  - `[medium]` `[patch]` (blind) `error` and `Failure.detail` stored unscrubbed — error text is now scrubbed before truncation; test with a raising Agent whose message carries a term.
  - `[medium]` `[patch]` (blind) budget checked only once per call — the budget is re-read before every later attempt; returns `budget_exhausted` with the ids so far; test.
  - `[medium]` `[defer]` (blind) a cancelled call loses the in-flight attempt's row and cost — Story 2.6 owns cancellation and late attempts (frontmatter `deferred`).
  - `[low]` `[reject]` (blind) a DB failure while logging escapes as a SQLAlchemy error — infrastructure errors are not provider exceptions; the job fails and Story 2.6's rescue loop places the fallback.
  - `[low]` `[reject]` (blind) no hash check at call time — the CI test plus `prompts check` cover it; a per-call lock read adds I/O to every attempt.
  - `[low]` `[patch]` (blind) `prompts lock` silent on changed/removed versions — it now runs `check` and exits 1 with the problems; test.
  - `[medium]` `[patch]` (blind) `llm_call` substring guard would reject `llm_call_ids` outside `app/ai` — the import test now matches whole words.
  - `[low]` `[patch]` (blind) `llm_call` integrity weaker than siblings — added `ck_llm_call_scope_kind` and its CHECK test; reasoning ≤ output, FK index and caller_ref index rejected (no query needs them yet).
  - `[low]` `[reject]` (blind) mock script queue is process-global — a ContextVar would not reach Story 2.5's job tasks; tests run one call at a time.
  - `[low]` `[reject]` (blind) `fixed_answer` ignores maximum/pattern/maxLength — such schemas give a loud `invalid_output`; the player schema is covered.
  - `[low]` `[patch]` (blind) `v01.md` collides with `v1.md`; malformed lock JSON crashes — non-canonical versions are skipped (test); malformed JSON rejected: a crash on a corrupt tracked file is acceptable.
  - `[false]` `[reject]` (blind) repository acceptance test vacuous — same as the intent row.
  - `[low]` `[reject]` (blind) full schema stored per row — a few hundred bytes; AD-6 asks for the request body per attempt.
  - `[low]` `[patch]` (blind) untested paths — added a production-without-key test; bool rendering and `charge` rowcount rejected (no code deletes budget rows).
  - `[low]` `[patch]` (edge) ContentFilterError/IncompleteToolCall logged as invalid_output — now `provider_error`.
  - `[medium]` `[patch]` (edge) error column unscrubbed — same fix as the blind row.
  - `[low]` `[patch]` (edge) `Agent(...)` built outside the try — moved inside; test uses a raising Agent.
  - `[low]` `[reject]` (edge) NUL characters break the insert — no provider or caller sends them today; a guard adds surface.
  - `[low]` `[reject]` (edge) `_log` failure loses a valid output — same as the blind DB row.
  - `[low]` `[reject]` (edge) `charge` ignores rowcount — nothing deletes budget rows.
  - `[medium]` `[patch]` (edge) overspend across attempts — same fix as the blind budget row.
  - `[low]` `[reject]` (edge) player purposes may spend the reserve — Story 2.8's AC owns `limit − reserve`.
  - `[low]` `[reject]` (edge) production refusal with a past deadline writes a row — harmless; the row records why.
  - `[low]` `[reject]` (edge) non-Mapping values/caller raise AttributeError — caller bug, still raised before any attempt.
  - `[low]` `[reject]` (edge) non-datetime deadline — caller bug against a typed signature.
  - `[low]` `[reject]` (edge) recursive schema recursion in `fixed_answer` — no such output schema exists.
  - `[low]` `[reject]` (edge) numeric `lt=0` fixed answer — same as the blind fixed-answer row.
  - `[low]` `[reject]` (edge) string pattern/format fixed answer — same.
  - `[low]` `[patch]` (edge) TIMEOUT step `sleep(3600)` could finish at a 3600 s timeout — now waits on an Event that is never set.
  - `[low]` `[reject]` (edge) global script, nested contexts — same as the blind row.
  - `[low]` `[patch]` (edge) term split by other whitespace not scrubbed — words of a term now match across any whitespace; test.
  - `[low]` `[reject]` (edge) malformed `hashes.json` — same as the blind row.
  - `[low]` `[patch]` (edge) `v01.md` — same fix as the blind row.
  - `[medium]` `[patch]` (edge) deadline test flaky (loop clock vs wall clock) — asserts all outcomes `timeout` and total latency instead of exactly one row.
  - `[low]` `[patch]` (edge) Agent construction outside the try (claim) — same fix as above.
  - `[false]` `[reject]` (edge) `mock.model` has a third argument — the spec's task line is a summary, not a contract; the only caller passes it.

## Design Notes

Effort level rides on `BudgetScope` because the open-assumptions file fixes `ai.run` at five arguments and the scope is what a session or batch freezes (AD-4, AD-22). Rows are committed per attempt in their own transaction so a caller that rolls back (a job hitting `409 order_exists`, Story 2.6) still leaves the attempt's cost on record. Mock tokens come from pydantic-ai's `FunctionModel` estimate, so cost is non-zero and deterministic.

## Verification

**Commands:**
- `cd backend && uv run ruff check . && uv run ruff format --check .` -- expected: clean
- `cd backend && uv run pytest tests/ai tests/test_imports.py tests/test_migrations.py -q` -- expected: all pass
- `cd backend && uv run pytest --cov=app/engine --cov=tests/engine --cov-fail-under=100` -- expected: all pass, once before commit

## Auto Run Result

Status: done

**Summary:** `app.ai.gateway.run(purpose, budget_scope, inputs, output_schema, deadline)` is the one LLM entry point. It resolves the evaluation scope's model config and the purpose's prompt version from that config, scrubs every string render value against `platform/pii.terms(scope)` (offset maps returned), renders `prompts/<purpose>/v<N>.md`, and runs its own attempt loop (6 for `player_order`) on pydantic-ai 2.65 with output retries 0, a per-attempt timeout capped by the deadline, and a budget check before each attempt. Each attempt writes one committed `llm_call` row (revision `0007`) with caller reference, config, model, quantisation, provider, endpoint, Effort level, seed/temperature, prompt version, tokens, cost, latency, outcome and the scrubbed request and response, and charges its cost to the budget. The caller gets a `Result` or a typed `Failure`; caller/config mistakes raise `GatewayError`. A deterministic, scriptable mock answers in local/test/ci without a key, never in production. Prompt files have a hash lock (`prompts/hashes.json`) with `python -m app.ai.cli prompts check|lock`; the import test bans provider SDK imports outside `app/ai` and `FallbackModel` everywhere.

**Files:**
- `backend/app/ai/gateway.py` (new): `run`, `Inputs`, `Result`, `Failure`, `GatewayError`.
- `backend/app/ai/mock.py`, `scrub.py`, `purposes.py`, `prompt_files.py`, `prompts/hashes.json` (new): mock provider, scrubber with offset map, purpose registry, prompt lock.
- `backend/app/platform/pii.py` (new): `terms(scope)`, empty until identity tables exist.
- `backend/app/ai/models.py`, `backend/migrations/versions/0007_llm_call.py` (new): the `llm_call` table.
- `backend/app/ai/budget.py`: `BudgetScope.effort_level`, `charge`. `backend/app/ai/cli.py`: `prompts check|lock`. `backend/app/ai/__init__.py`: docstring.
- `backend/pyproject.toml`, `uv.lock`: `pydantic-ai-slim==2.65.0`.
- Tests: `tests/ai/test_gateway.py`, `test_mock.py`, `test_scrub.py`, `test_prompt_files.py` (new); `tests/test_imports.py`, `tests/test_migrations.py`, `tests/conftest.py`.

**Review:** one pass, 51 findings (medium 7, low 34, false 10). Patched: error text scrubbed; budget re-checked before each attempt; whole-word table guard; `ck_llm_call_scope_kind`; content filter → `provider_error`; Agent built inside the try; `prompts lock` reports breaches; `v01.md` ignored; whitespace-tolerant terms; never-ending mock timeout; stronger tests (deadline latency, settings sent, default level, production without key). Deferred: cancelled-call logging (Story 2.6). Rejected with reasons in the triage log.

**Follow-up review recommended:** true. Patched entries: medium 4 (scrubbed errors, budget re-check, table guard, deadline test), low 13. Unverified risk: the per-attempt budget re-check and the Agent-inside-try change were not seen by a second review.

**Verification:**
- `ruff check`, `ruff format --check`: clean. `uv lock --check`: ok.
- Full `pytest --cov=app/engine --cov=tests/engine --cov-fail-under=100`: 1251 passed in 63 s (1 warning, not from the new tests), engine coverage 100 %, including `alembic check` and the CHECK-list test.
- `tests/ai` with `-n0`: 93 passed in 11 s. No new test over 1 s (slowest new: 0.3 s).
- Matrix audit: every row has a passing test in `tests/ai/test_gateway.py`, `test_scrub.py` or `test_prompt_files.py`.

**Decisions taken in place of the founder:**
1. pydantic-ai pinned at `pydantic-ai-slim==2.65.0` (newest release at least two weeks old), no extras; the `openai` extra comes with Story 2.7.
2. The Effort level travels on `BudgetScope.effort_level` (default: the config's first level), keeping `ai.run` at five arguments.
3. An evaluation scope's config is the scope id; a Class session scope raises `scope_unresolved` until Epic 5 binds sessions to configs.
4. Caller/config mistakes raise `GatewayError` (nine codes) before any attempt; provider problems are always typed failures.
5. Every failed attempt (invalid output, timeout, provider error) is retried within the attempt limit and deadline; the last outcome is returned, or `timeout` when the deadline ends the loop.
6. Until Story 2.8, each attempt's cost is added to `spent`; a call stops with `budget_exhausted` when `spent ≥ limit` (or a player purpose finds `players_exhausted_at` set), before the first or any later attempt.
7. Mock selection: provider `mock`, or a missing key, in local/test/ci. In production a mock config or missing key gives one `provider_error` row; a set key for `openai_compatible` gives `provider_error` "no adapter" until Story 2.7.
8. Every string render value is free text and scrubbed to `[REDACTED]`: whole-word, case-insensitive, any whitespace inside a term.
9. Prompt templates use `string.Template` (`$name`); the lock is `prompts/hashes.json` with CRLF-insensitive sha256; DB-stored configs are checked by `prompts check`.
10. Table name `llm_call` (singular, as in the AC).
11. Implementation ran in the orchestrating agent's own context (runbook); the four review layers were independent sub-agents.

**Residual risks:**
- CI not run on GitHub (no push).
- Migration 0007 was edited after the shared `olspillet_test*` databases were migrated, so they lack `ck_llm_call_scope_kind` until rebuilt; constraint tests use the migrations database and passed.
- A cancelled call loses the in-flight attempt's row (deferred to Story 2.6).
