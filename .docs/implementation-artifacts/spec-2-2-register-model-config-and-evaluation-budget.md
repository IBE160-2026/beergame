---
title: 'Story 2.2: Register a model config and an evaluation budget from the command line'
type: 'feature'
created: '2026-11-18'
baseline_revision: '7ef46a21f900ce7322fa43a24231fefccca7d34e'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-2-context.md'
warnings: ['oversized']
deferred:
  - summary: >-
      Stored config rows are read back through the current ModelConfigSpec (extra=forbid, all bounds), so a later tightening of the schema would make old, immutable rows unreadable and break config list.
    evidence: |-
      Blind review finding; app.ai.config._row calls ModelConfigSpec.model_validate on every row. Nothing tightens the schema yet. The first story that changes ModelConfigSpec (2.3 or 2.12) should read rows with a lenient or versioned model and validate only on write.
    location: >-
      backend/app/ai/config.py _row
    severity: medium
---

<intent-contract>

## Intent

**Problem:** No LLM call can be made safely yet: there is no stored model config (provider, endpoint, model version, prices, Effort levels, prompt versions) and no budget row to charge, so the gateway of Story 2.3 would have nothing to pin and nothing to limit (FR-68, FR-69, FR-78, NFR-2, AD-6, AD-22).

**Approach:** Revision `0006` adds the `app/ai`-owned tables `ai_model_configs` and `ai_budgets`; `app/ai/config.py` and `app/ai/budget.py` are the only code that reads or writes them; `python -m app.ai.cli` offers `config add|edit|list|show` and `budget set`. Referenced configs are immutable (DB trigger); every edit writes a new row.

## Boundaries & Constraints

**Always:**
- Config file = one JSON object, validated by pydantic with `extra="forbid"`: `name`, `provider` (`mock` | `openai_compatible`), `endpoint` (`https://…` for `openai_compatible`), `region`, `model_version`, `quantisation`, `credential_env` (env var name `^[A-Z][A-Z0-9_]*$`; required for `openai_compatible`, absent/null for `mock`), `prices` {`input_usd_per_mtok`, `output_usd_per_mtok`} (Decimal ≥ 0, ≤ 8 places), `rate_limit_rpm` (int > 0), `prompts` {purpose `^[a-z][a-z0-9_]*$` → version int ≥ 1, may be empty}, `effort_levels` (≥ 1, unique names): each `name`, `provider_params` (object, default {}), `attempt_timeout_s` and `order_time_budget_s` (both required, > 0, timeout ≤ budget), `placeholder` (bool, default true).
- Rejections name the field (`error <code> <field>: <message>`, exit 1): a credential anywhere in the file (a key named `api_key`, `key`, `secret`, `token`, `password`, `authorization` at any depth, or a string value starting `sk-`) → `credential_in_file`; a prompt version with no file `app/ai/prompts/<purpose>/v<N>.md` → `prompt_missing`; an Effort level missing a time value → that field; unreadable / non-object JSON → exit 2. Only the env var name is ever stored.
- `ai_model_configs`: id (uuid7), name, provider, endpoint, region, model_version, quantisation, credential_env, price columns `NUMERIC(18,8)`, rate_limit_rpm, `prompts` JSONB, `effort_levels` JSONB, `derived_from` (self FK, null), `referenced_at` (null), created_at. A trigger refuses UPDATE and DELETE of a row whose `referenced_at` is set (`restrict_violation`); `ai.config.mark_referenced(id)` (for Story 2.11 runs and Epic 5 `sessions.lock`) sets it once and is idempotent.
- `config edit <id> [--prompt <purpose>=<version> …] [--from <file>]` (at least one option) always inserts a new row with `derived_from = <id>`, prints `config <new id>`; `--prompt` adds or moves one purpose (version `N` or `vN`); the source row is never changed. Unknown id → `config_not_found` exit 1.
- `config list`: one line per row, oldest first: `config <id> name=<…> model=<…> endpoint=<…> region=<…> referenced=yes|no`. `config show <id>`: the row as JSON.
- `ai_budgets`: id, `scope_kind` (`evaluation` | `class_session`, CHECK), `scope_id` uuid, `limit_usd`, `reserve_usd`, `spent_usd` (all `NUMERIC(18,8)`, ≥ 0, reserve ≤ limit, spent default 0), `players_exhausted_at` (null), created_at, updated_at; unique (scope_kind, scope_id). `ai.budget.Budget` exposes them as `limit`, `reserve`, `spent`, `players_exhausted_at`.
- `budget set (--evaluation <config_id> | --session <class_session_id>) [--limit <usd>] [--reserve <usd>]` upserts the scope's one row (a second set changes limit and reserve, keeps spent and `players_exhausted_at`) and prints `budget <kind> <scope_id> limit=… reserve=… spent=… players_exhausted_at=-`. Evaluation needs `--limit` and an existing config (`config_not_found`); a session scope defaults the limit to `AI_DEFAULT_SESSION_BUDGET_USD` (no session table exists yet, so its id is not checked). Without `--reserve` the reserve is `AI_BUDGET_RESERVE_USD`. reserve > limit → `reserve_above_limit` exit 1.
- Settings (`platform/config.py`): `ai_default_session_budget_usd` = 15.00 and `ai_budget_reserve_usd` = 1.00, both commented as placeholders (issue #8).
- `ai.config` / `ai.budget` public async functions open their own transaction, or join one passed as `session=`.
- Shipped example files `backend/ai-configs/mock.json` and `backend/ai-configs/openrouter-deepseek.json` (`deepseek/deepseek-v4.1-flash-1017`, `https://eu.openrouter.ai/api/v1`, `OPENROUTER_API_KEY`) with empty `prompts` and one Effort level marked placeholder (attempt timeout 4 s, Order time budget 8 s — the 8 s p95 placeholder), prices/rate limit placeholder.
- Import check (pytest): outside `backend/app/ai`, no file under `backend/app` imports `app.ai.*` other than `app.ai.config` / `app.ai.budget`, nor mentions `ai_model_configs` / `ai_budgets`; `app/ai` imports nothing from `app.modules`. `migrations/` is exempt.
- Tests stay fast: one `ai_db` fixture truncating the two tables; tests point `PROMPTS_DIR` at a tmp dir with monkeypatch.

**Never:** No gateway, provider SDK, pydantic-ai, `llm_call` table, reservation logic, seeding of a default config, `pin`/`cost` commands, HTTP route or screen. No change to games tables or engine. No credential value stored or printed.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Add | valid file, prompt file present | one row, `config <id>`, exit 0 | — |
| Credential | `"api_key": "x"` or `provider_params.token` or `"sk-…"` value | nothing stored | `credential_in_file <field>` exit 1 |
| Prompt missing | `prompts: {"player_order": 2}`, no v2.md | nothing stored | `prompt_missing prompts.player_order` exit 1 |
| Level incomplete | Effort level without `order_time_budget_s` | nothing stored | message names `effort_levels.0.order_time_budget_s`, exit 1 |
| Bad file | missing file / `[]` | nothing stored | exit 2 |
| Edit prompt | `edit <id> --prompt player_order=v1` | new row, `derived_from=<id>`, map updated, source unchanged | — |
| Referenced | `mark_referenced`, then raw UPDATE/DELETE | refused | DB `restrict_violation` |
| Edit referenced | `edit <ref id> --prompt …` | new row; source row byte-identical | — |
| List | two rows, one referenced | two lines, `referenced=yes` / `no` | — |
| Budget eval | `budget set --evaluation <id> --limit 2` | row limit 2, reserve 1 (setting), spent 0 | unknown id `config_not_found` |
| Budget again | second set `--limit 3 --reserve 0.5` | same row, new limit/reserve, spent kept | — |
| Budget session | `budget set --session <uuid>` | row with limit `AI_DEFAULT_SESSION_BUDGET_USD` | — |
| Reserve too big | `--limit 0.5` without `--reserve` | nothing stored | `reserve_above_limit` exit 1 |

</intent-contract>

## Code Map

- `backend/app/ai/__init__.py` -- empty package today; becomes the docstring of the gateway package.
- `backend/app/platform/db.py` -- `metadata`, `get_sessionmaker()` (`.begin()` for a transaction).
- `backend/app/modules/games/models.py` -- Core `Table` pattern with `_in(...)` CHECK helper to copy.
- `backend/migrations/versions/0005_game_checks.py` -- revision style and append-only trigger pattern (`restrict_violation`).
- `backend/migrations/env.py` -- imports `app.modules.games.models` to register tables; add `app.ai.models`.
- `backend/app/sim.py` -- CLI conventions: argparse subparsers with `handler`/`command_parser`, `_run` (Selector loop on Windows), `_report`, `finally: await db.dispose()`, `main(argv)`, `configure_logging(..., stream=sys.stderr)`.
- `backend/app/platform/config.py` -- `Settings` (add two placeholder Decimal fields).
- `backend/tests/conftest.py` -- `test_database`, `GAMES_TABLES` truncation pattern, `libpq_dsn`.
- `backend/tests/test_migrations.py` -- `HEAD_TABLES`, version `0005` asserts, `CHECKS` map (add `ck_ai_budgets_scope_kind`).
- `backend/tests/test_imports.py` -- `imports(package)` AST helper to reuse.
- `backend/tests/test_sim.py` -- CLI test style: sync tests calling `main([...])` with `capsys`.

## Tasks & Acceptance

**Execution:**
- `backend/app/ai/models.py` (new) -- the two Core tables on `metadata`.
- `backend/migrations/versions/0006_ai_config_budget.py` (new) -- tables, constraints, immutability trigger; downgrade drops them and the function. `migrations/env.py` imports `app.ai.models`.
- `backend/app/ai/config.py` (new) -- `PROMPTS_DIR`, `ModelConfigSpec`/`EffortLevel` pydantic models, `parse(data)` raising `ConfigInvalid(errors=[FieldError(code, field, message)])`, `add`, `derive`, `get`, `list_all`, `mark_referenced`, `ConfigNotFound`.
- `backend/app/ai/budget.py` (new) -- `BudgetScope`, `Budget`, `set_budget`, `get`, `BudgetRefused`.
- `backend/app/ai/cli.py` (new) -- `config add|edit|list|show`, `budget set`; exit codes as in the matrix.
- `backend/app/platform/config.py` -- two placeholder settings.
- `backend/ai-configs/{mock,openrouter-deepseek}.json` (new) -- example configs.
- `backend/tests/ai/test_config.py`, `test_budget.py`, `test_cli.py` (new) -- matrix rows; `backend/tests/test_imports.py` -- AI import/table check; `backend/tests/test_migrations.py`, `conftest.py` -- head 0006, `ai_db`.

**Acceptance Criteria:**
- Given the shipped example files, when parsed by `ai.config.parse`, then both are valid and every Effort level is marked placeholder.
- Given CI commands locally, then ruff is clean, all tests pass, engine coverage stays 100 %, and `alembic check` passes (`test_the_revisions_match_the_module_tables`).

## Spec Change Log

## Review Triage Log

### 2026-11-18 — Review pass
- verdicts: 43 findings — high 0, medium 3, low 28, false 12, maybe-false 0
- findings:
  - `[false]` `[reject]` (intent) CLI tested in-process, `__main__` not run — now run as a subprocess by `test_the_cli_as_a_program_prints_only_the_report_on_stdout` (patched under verification-gap).
  - `[false]` `[reject]` (intent) "referenced" is a stored flag, not a join — `app/ai` may not read Class session or batch tables (AD-6); `mark_referenced` is the documented hook (Design Notes).
  - `[false]` `[reject]` (intent) refusal shown only at the DB — the CLI has no in-place change to refuse; `config edit` writes a new row (tested at both levels), the trigger refuses everything else.
  - `[false]` `[reject]` (intent) prompt check runs against a temp dir — no prompt files exist before Story 2.4; the CLI smoke run against the real tree gave `prompt_missing` as expected.
  - `[false]` `[reject]` (intent) rejections tested at both levels — descriptive, no defect.
  - `[false]` `[reject]` (intent) session scope not shown from Epic 5's side — Epic 5 does not exist; `set_budget(BudgetScope.class_session(...))` is tested.
  - `[false]` `[reject]` (intent) import check is a pytest test that skips `migrations/` — CI runs pytest; `migrations/env.py` must import the tables for `alembic check`.
  - `[low]` `[patch]` (intent) placeholder marking uneven for prices/rate limits — CLI docstring now states the example files' prices, rate limits and Effort levels are placeholders (issues #8, #9).
  - `[false]` `[reject]` (intent) features beyond the story (`show`, `--from`, upsert, provider rules) — small, tested, and implied by "config edit creates a new row" and "one budget row per scope".
  - `[low]` `[patch]` (verification-gap) CLI DB-failure paths untested — added `test_the_cli_without_a_database_exits_1` and `test_the_cli_reports_other_database_errors`.
  - `[low]` `[patch]` (verification-gap) `python -m app.ai.cli` entry never run — added subprocess test (1.3 s).
  - `[low]` `[patch]` (verification-gap) "too large" budget amount untested — parametrize row added.
  - `[low]` `[patch]` (verification-gap, other) trailing zeros beyond 8 places refused for budgets — `_amount` now compares with `quantize(1e-8)`; test uses `3.000000000`.
  - `[low]` `[patch]` (blind) infinite time values reach JSONB — `Seconds` = strict finite float, 0 < s ≤ 3600; tests for `inf` and `true`.
  - `[low]` `[patch]` (blind) `rate_limit_rpm` unbounded overflows the Integer column — `le=1_000_000`; test.
  - `[low]` `[patch]` (blind) `parse` docstring claims every bad field — docstring now describes the three stages.
  - `[medium]` `[patch]` (blind) credentials in the endpoint URL pass — userinfo or a key-like query parameter in any URL value is `credential_in_file`; two tests.
  - `[low]` `[patch]` (blind) prompt purposes like `order_token` flagged as credentials — `prompts` keys skipped by the scan; test.
  - `[low]` `[patch]` (blind) value-prefix heuristic narrow — added `sk_` and `basic ` and a comment that the scan is a heuristic.
  - `[medium]` `[defer]` (blind) stored rows re-validated with the current schema — no tightening exists yet; deferred to the first story that changes `ModelConfigSpec`.
  - `[low]` `[patch]` (blind) unreferenced rows and the freezing UPDATE mutable — trigger now refuses any UPDATE that changes a column other than `referenced_at`; tests.
  - `[low]` `[reject]` (blind) orphan evaluation budget if its config is deleted — no code deletes configs; a guard adds surface for a path nothing takes.
  - `[low]` `[reject]` (blind) limit below spent / exhausted state not recomputed — spec keeps spent and `players_exhausted_at`; cost-limit semantics belong to Story 2.8.
  - `[low]` `[reject]` (blind) no cross-check reserve ≤ session default — misconfiguration gives a clear `reserve_above_limit`; a Settings validator adds surface for an operator error.
  - `[low]` `[patch]` (blind) `CHECKS` task from the Code Map missing — the CHECK test now also compares `ck_ai_budgets_scope_kind` and `ck_ai_model_configs_provider` with the Python literals.
  - `[low]` `[patch]` (blind) duplicated allowed-value lists can drift — same fix as the row above.
  - `[low]` `[patch]` (blind) import test skips top-level modules — it now scans every file under `app/` outside `app/ai`.
  - `[low]` `[patch]` (blind) `--from` + `--prompt` docs contradict the code — docstring now says `--prompt` is laid over the file's map.
  - `[low]` `[reject]` (blind) `db_error` hides the cause — same contract as `app.sim`; the bounds above remove the known overflow paths.
  - `[low]` `[patch]` (blind) shipped prices/rate limit not marked placeholder — same fix as the intent row (CLI docstring).
  - `[low]` `[patch]` (edge) UTF-8 BOM config rejected — read with `utf-8-sig`; test.
  - `[low]` `[patch]` (edge) infinite timeouts — same fix as the blind row.
  - `[low]` `[reject]` (edge) NaN in `provider_params` stored as null — needs a hand-written `NaN` token in a config file; a recursive guard is not worth it.
  - `[low]` `[patch]` (edge) boolean timeout coerced to 1 s — strict float; test.
  - `[low]` `[patch]` (edge) `rate_limit_rpm` overflow — same fix as the blind row.
  - `[low]` `[patch]` (edge) trailing zeros refused — same fix as the verification-gap row.
  - `[false]` `[reject]` (edge) reserve/default mismatch breaks Epic 5 — same as the blind row; the refusal is explicit and names the cause.
  - `[false]` `[reject]` (edge) limit below spent — the spec keeps spent; enforcement is Story 2.8's.
  - `[false]` `[reject]` (edge) orphan evaluation budget — nothing deletes configs.
  - `[false]` `[reject]` (edge) edit refused when the source's prompt file was removed — AD-6 forbids removing a referenced prompt version and Story 2.3 adds the CI check; the error names the field.
  - `[low]` `[patch]` (edge) `prompt_cache_key` taken for a credential — suffixes narrowed to `api_key`, `secret_key`, `access_key`, `_secret`, `_token`, `_password`; test.
  - `[low]` `[patch]` (edge) CHECK lists untested — same root cause and fix as the blind `CHECKS` row.
  - `[medium]` `[patch]` (edge) credential in endpoint URL — same root cause and fix as the blind medium row.

## Design Notes

`referenced_at` makes immutability a property of the row, not a query into tables `app/ai` may not read (Class sessions, simulation batches): the referencing module calls `ai.config.mark_referenced` in its own transaction (Story 2.11, Epic 5). Because every edit writes a new row, unreferenced rows are never updated either; the trigger is the hard guard for referenced ones.

Budget column names carry `_usd` because `limit` is an SQL keyword; the API keeps the AC's names.

## Verification

**Commands:**
- `cd backend && uv run ruff check . && uv run ruff format --check .` -- expected: clean
- `cd backend && uv run pytest tests/ai tests/test_imports.py tests/test_migrations.py -q` -- expected: all pass
- `cd backend && uv run pytest --cov=app/engine --cov=tests/engine --cov-fail-under=100` -- expected: all pass, once before commit

## Auto Run Result

Status: done

**Summary:** Revision `0006` adds the `app/ai`-owned tables `ai_model_configs` and `ai_budgets` (money `NUMERIC(18,8)` USD). `ai.config` parses and stores model configs (provider, endpoint, region, model version, quantisation, prices, rate limit, `prompts` map, Effort levels as data with per-attempt timeout, per-Order time budget and a `placeholder` mark), refuses credentials, missing prompt files and incomplete Effort levels by field name, and never changes a row: `derive` (CLI `config edit`) writes a new row with `derived_from`, and a trigger refuses any change to a referenced row (set by `mark_referenced`, for Story 2.11 and Epic 5) and any change other than setting `referenced_at` to an unreferenced one. `ai.budget.set_budget` upserts one row per scope (evaluation or Class session) with `limit`, `reserve`, `spent`, `players_exhausted_at`; the Class session limit defaults to `AI_DEFAULT_SESSION_BUDGET_USD` and the reserve to `AI_BUDGET_RESERVE_USD`, both placeholders (issue #8). `python -m app.ai.cli` offers `config add|edit|list|show` and `budget set`.

**Files:**
- `backend/app/ai/{models,config,budget,db,cli}.py` (new), `app/ai/__init__.py`: tables, config and budget API, transaction helper, CLI.
- `backend/migrations/versions/0006_ai_config_budget.py` (new), `migrations/env.py`: tables, immutability trigger.
- `backend/app/platform/config.py`: two placeholder settings.
- `backend/ai-configs/{mock,openrouter-deepseek}.json` (new): example configs.
- Tests: `tests/ai/{conftest,helpers,test_config,test_budget,test_cli}.py` (new); `tests/test_imports.py` (AI boundary check), `tests/test_migrations.py` (head 0006, AI CHECKs), `tests/conftest.py` (`ai_db`).

**Review:** one pass, 43 findings (medium 3, low 28, false 12). Patched: credentials in URLs, prompt-purpose false positives, narrower suffixes and wider prefixes in the credential scan; strict finite time values and a rate-limit bound; stricter trigger; trailing-zero amounts; BOM files; docstrings; tests for DB failures, the program entry, oversize amounts and the AI CHECK constraints; import check covers top-level modules. Deferred: lenient reading of stored rows (frontmatter). Rejected with reasons in the triage log.

**Follow-up review recommended:** false. Patched entries: medium 1 (URL credentials, two rows), low 17 entries.

**Verification:**
- `ruff check`, `ruff format --check`: clean.
- Full `pytest --cov=app/engine --cov=tests/engine --cov-fail-under=100`: 1223 passed in 46 s, engine coverage 100 %.
- `tests/ai` + `test_imports.py`: 72 passed in 6.8 s. New test over 1 s: `test_the_cli_as_a_program_prints_only_the_report_on_stdout` (1.3 s, a subprocess).
- Manual: `python -m app.ai.cli config add ai-configs/mock.json`, `config list`, `budget set --evaluation <id> --limit 2` against the test database gave the expected lines; `config edit --prompt player_order=1` gave `prompt_missing` (no prompt files before Story 2.4).
- Matrix audit: every row has a passing test in `tests/ai/` (Add, Credential, Prompt missing, Level incomplete, Bad file, Edit prompt, Referenced, Edit referenced, List, Budget eval/again/session, Reserve too big).

**Decisions taken in place of the founder:**
1. Config files are JSON; providers `mock` and `openai_compatible`; `openai_compatible` needs an https endpoint and `credential_env`.
2. "Referenced" is a stored `referenced_at` set by `ai.config.mark_referenced` (callers: Story 2.11 runs, Epic 5 `sessions.lock`), since `app/ai` may not read their tables.
3. Every edit writes a new row, referenced or not; the trigger allows only setting `referenced_at`.
4. `config edit --from FILE` replaces the content; `--prompt` accepts `N` or `vN`.
5. A credential is a key named like `api_key`/`token`/`secret`/`authorization`, a value starting `sk-`/`sk_`/`bearer `/`basic `, or a URL with a user, password or key-like query parameter.
6. Placeholder values: Effort level 4 s attempt timeout, 8 s Order time budget; example prices 0.10/0.40 USD per million tokens and rate limits 60/600 rpm; `AI_DEFAULT_SESSION_BUDGET_USD` = 15.00, `AI_BUDGET_RESERVE_USD` = 1.00.
7. `budget set` upserts: limit and reserve change (reserve back to the default when `--reserve` is left out); spent and `players_exhausted_at` stay. A Class session id is not checked (no table yet).
8. Budget columns are `limit_usd`, `reserve_usd`, `spent_usd` (`limit` is an SQL keyword); the API keeps the AC's names.
9. Implementation ran in the orchestrating agent's own context (runbook); the four review layers were independent sub-agents.

**Residual risks:**
- CI not run on GitHub (no push).
- The edited migration 0006 required dropping the local `olspillet_test*` databases so they re-migrate; any other agent using them at that moment would have seen its test databases vanish (conftest recreates them).
- Stored-row re-validation (deferred).
