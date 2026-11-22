---
title: 'Story 9.14: Read AI narration that only connects computed facts'
type: 'feature'
created: '2026-11-21'
status: 'done'
baseline_revision: '36aa138a51c3557f7f55868fb698eca58c516650'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-9-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** Debrief step 4 shows only code-rendered moments; there is no AI line that ties a Student's moments together, no shared way to make a facts-only LLM call (helper, validator, fallback), no narration timing, and no Lecturer switch for Debrief AI text (FR-44, FR-34, FR-15, FR-46, AD-7).

**Approach:** A pure `analysis.narration` (output schema of fact ids and template ids, `validate_ai_text`, code renderer `render`) over a new versioned content kind `narration_templates`; a shared `app/ai/text.worded` helper that calls `gateway.run` and returns `{text, ai_generated, llm_call_id}` or the caller's fallback; one `llm-batch` job per Student-held Seat deferred inside the Game's `finish` transaction through a new `games.service.on_game_finished` hook, storing narration and quiz-explanation lines per facts set; step 4 and the quiz result show them, frozen at the Student's first view; a Klasseøkt Bryter turns Debrief AI text off, pinned at the lock.

## Boundaries & Constraints

**Always:**
- LLM output (`AiTextOutput`): 1–3 `sentences`, each `template_id` + `fact_ids` (moment ids `moment:<role>:<week>` or pattern occurrence ids of the Seat). Code fills every number (week, order, supply_line, incoming_order, later_cost of each cited fact) into the template; the LLM writes no word of the shown text.
- `analysis.validate_ai_text(output, fact_set, templates)` (pure) rejects: a fact id not in the set (`unknown_fact`), a template id not in the pinned version (`unknown_template`), a fact count that does not match the template (`wrong_arity`), and any number in the rendered text that is not one of the cited facts' rendered values (`number_outside_facts`). `analysis.render(fact_set, templates)` is the code narration (None when the Seat has no moments or the templates hold no narration).
- `app/ai/text.worded(purpose, scope, inputs, schema, validate=, fallback=)`: one `gateway.run` (`deadline=None`), never retried by the caller; a `GatewayError`, a `Failure` (`timeout`, `invalid_output`, `budget_exhausted`, `provider_error`), a rejection or any exception gives `AiText(fallback(), False, None)`. `app/ai` imports only `platform` and itself.
- New purposes `debrief_narration`, `quiz_explanation` (`attempt_limit=1`, not player, so they may spend the reserve); versioned prompts `prompts/<purpose>/v1.md` locked in `hashes.json`; inputs carry Roles, fact ids, numbers and template text only. A Class-session scope resolves to the model config the Debrief pin names (`BudgetScope.model_config_id`, not part of equality); without one it stays `scope_unresolved` (players unchanged).
- Zero-config (local/test/ci): `MOCK_SPEC`/`ai-configs/mock.json` list both prompts; when the active default is a mock config missing a `MOCK_SPEC` prompt, `ensure_zero_config` derives the new row (`config.derive`, the `config edit … --prompt` path), adds its mock measurement and evaluation budget and pins it.
- Class session field `debrief_ai_text` (bool, default true), saved like `debrief_release`, frozen once locked (409 `session_locked`); pin `debrief_ai_text` = `{enabled, model_config_id, effort_level}` (config marked referenced when enabled); pin `narration_templates` = `{version}`.
- Finish hook: inside `games.commands.finish`, every registered `on_game_finished` hook runs with the session and a `FinishedGame` (ids, purpose, Class session, pins, Seat ids ever held by a Student). `modules/debrief` registers one that defers `debrief.narrate(game_id, seat_id)` on `llm-batch` (queueing lock `narration:<game>:<seat>`) per such Seat when the pin is enabled; nothing otherwise. `games` imports nothing from `debrief`.
- The job: facts set via `games.fact_set`, then one `quiz_explanation` call per pinned quiz question with `in_your_game` text, then the narration; rows in `debrief_ai_texts(fact_set_id, subject, text, ai_generated, llm_call_id, created_at)` (subject `narration` or `quiz:<question_id>`), insert-once; the narration row last marks it done. The sweep re-enqueues a Seat of a finished, enabled Game with no narration row more than 10 minutes after the finish.
- Step 4 `MomentsOut.narration`: the stored narration if stored before the Student's `debrief_fact_sets.recorded_at`, else the code text (`ai_generated` false); quiz `QuizResultOut.ai_explanation`: the stored AI line if stored before the attempt's `submitted_at`, else null. Both database times, so the text never changes under a reader.
- Web: `ai_generated` alone drives «KI-generert, kan ta feil: «…»» and `data-ai-generated="true"` (the print route's marker); an AI line is followed by the note that the AI's explanation can be wrong and the numbers are computed by code. Copy in `nb.ts`, draft `[ASSUMPTION]`.

**Never:** an LLM call on a request path or a step waiting on one; `modules/debrief` importing `modules/players`; a narration job or Debrief `ai.run` call with the switch off; changing the lock mechanism; storing a name or free text in a prompt; changing the player gateway path for Class sessions.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Accepted | mock answer citing two own moments with `narration-orders` | row `ai_generated` true, `llm_call_id` set; step 4 shows it marked | — |
| Rejected | fact id of another Seat / unknown template / literal number in template | code text, `ai_generated` false, `llm_call_id` null | never retried |
| Provider fails | `mock.outage()`, budget spent, no prompt in config | code text | — |
| AI text off | switch off before lock | no job deferred, no `llm_call` row; step 4 code text | — |
| Seen before ready | Student opens step 4, narration stored later | code text stays on every later read | — |
| Mostly AI | Seat with < 10 Student Orders | `narration` null, no call | — |
| Locked | switch changed after lock | 409 `session_locked` | — |

</intent-contract>

## Code Map

- `backend/app/ai/gateway.py:200 _resolve` (evaluation only now), `:537 run`; `ai/purposes.py`; `ai/budget.py:42 BudgetScope`; `ai/mock.py` (`script`, `outage`, `mock_answer`); `ai/seed.py:24 MOCK_SPEC`, `backend/ai-configs/mock.json`; `ai/config.py:449 derive`, `:780 pin`, `:817 active_default`; `ai/prompt_files.py lock`.
- `backend/app/modules/players/jobs.py:59 _decide` -- the `gateway.run` + typed-failure pattern to mirror.
- `backend/app/analysis/sentences.py` (`SentenceTemplate`, `_fields`, `format_number/money`), `moments.py`, `quiz.py:155 render_in_your_game`, `facts.py:160-205` (ids, `Moment`, `PatternOccurrence`), `patterns.py CAUSE_WORDS`.
- `backend/app/modules/content/{models,schemas,service}.py` -- add `Kind.NARRATION_TEMPLATES`, pin; migration pattern `migrations/versions/0106_moment_templates.py`.
- `backend/app/modules/sessions/service.py:842 save_session` (`debrief_release` at :892/:929), `:2878 register_pin_provider`, `:2909 build_snapshot`, `:2952 lock`; `models.py:79`, `repo.py:235`, `schemas.py:202/:367`, `routes.py:242`.
- `backend/app/modules/games/commands.py:1637 finish`, `service.py` (add hook registry; `commands` imports `service`), `repo.occupancy_history:592`.
- `backend/app/modules/debrief/service.py:541 step`, `:605 _moments`, `:1184 _result`; `commands.py:792 record_facts`; `schemas.py:231 RenderedTextOut`, `:273 MomentsOut`, `:471 QuizResultOut`; `models.py`; `dev.py` (dev router); `platform/jobs/__init__.py:50 TASK_MODULES`, `:69 defer`; `platform/events/registry.py:99`; `modules/ops/sweep.py:113 DUE_ACTIONS`.
- Frontend: `modules/debrief/moments-step.tsx:68 Text`, `quiz-step.tsx:227`, `modules/sessions/{class-session-page.tsx:549,choices.ts}`, `components/switch`, `copy/nb.ts` (`debrief.aiPrefix`).
- Tests: `tests/ai/test_gateway.py:396`, `tests/sessions/test_lock.py:92`, `tests/content/test_content.py:77`, `tests/test_migrations.py:111`, `tests/debrief/test_group.py played()`, `tests/debrief/test_explanation.py`; e2e `support/live-game.ts liveClassGame`, `debrief-moments.spec.ts`.

## Tasks & Acceptance

**Execution:**
- `backend/app/analysis/narration.py` (new), `analysis/__init__.py` -- templates shape, output schema, `render`, `render_output`, `validate_ai_text`; re-export `render`, `validate_ai_text`.
- `backend/app/ai/{purposes,budget,gateway,seed}.py`, `ai/text.py` (new), `ai/prompts/{debrief_narration,quiz_explanation}/v1.md`, `hashes.json`, `ai-configs/mock.json`.
- `backend/migrations/versions/0112_debrief_narration.py` -- kind + v1 templates, `class_sessions.debrief_ai_text`, `debrief_ai_texts` (insert-only trigger).
- `backend/app/modules/content/*`, `sessions/*`, `games/{service,commands}.py`, `debrief/{models,commands,narration (new),jobs (new),service,schemas,dev,README}.py`, `platform/jobs`, `platform/events/registry.py`, `ops/sweep.py`.
- `.docs/planning-artifacts/architecture/architecture-beergame-2026-11-12/ARCHITECTURE-SPINE.md:571` -- close the Debrief half of the Deferred timing entry with the decision (Adapted items stay open).
- Tests: `tests/analysis/test_narration.py` (golden accepted + each rejection + render), `tests/ai/test_text.py` (accepted, each failure kind, rejection, GatewayError), `tests/debrief/test_narration.py` (hook defers per Student Seat / not when off; job stores AI and fallback rows; step 4 frozen at first view; quiz line; sweep finder; full Group debrief with the job never run opens every step), updates to pin/migration/session tests.
- Frontend: `moments-step.tsx`, `quiz-step.tsx`, `class-session-page.tsx`, `choices.ts(+test)`, `nb.ts`, regenerated api; `e2e/debrief-narration.spec.ts` (new): a real 10-Uke Class game, two Students; dev narrate Sara's Seat (mock) and Ida's under outage; Sara's step 4 shows the marked line, Ida's the unmarked code text; Lecturer's Bryter on Klasseøkt; axe 360 and 1440 px.

**Acceptance Criteria:**
- Given accepted narration, when a Student opens step 4, then the line reads «KI-generert, kan ta feil: «…»» with `data-ai-generated="true"` and the AI note.
- Given the mock set to fail, when the Student opens step 4, then the same place shows the code text without the prefix or marker.
- Given a Lecturer before the Start date, when they switch «KI-tekst i Debriefen» off and save, then the session stores it, the lock pins `enabled: false`, and a finished game defers no job.
- Given a Group debrief whose narration job never runs, then every step 2–5 opens (api test).

## Spec Change Log

## Review Triage Log

### 2026-11-21 — Review pass
Layers run: blind hunter, edge-case hunter, verification gap and intent alignment (sonnet), four for a risky story (gateway, finish transaction, migration, worker). Every hand-back failed; findings were read from `review-{blind,edge,verification,intent}-9-14.md` in the scratchpad. The diff left out the generated `openapi.json`/`schema.ts` and `.docs`.
- verdicts: 44 findings — high 0, medium 2, low 29, false 13, maybe-false 0
- findings:
  - `[low]` `[patch]` (blind 1) `content/models.py` docstring «…» became «???» (an ASCII write). Restored.
  - `[medium]` `[patch]` (blind 2) A Class session holding a config made before 9.14 pinned AI text on, every call then failing as `prompt_not_in_config` (code text, Lecturer told «På»). `debrief_ai_text_pin` now turns it on only when the config's `prompts` names `debrief_narration`; new test.
  - `[low]` `[reject]` (blind 3) The Bryter says «På» when the session has no model config at all. Only with no default config anywhere (never in local/test, an unconfigured production); a new state on the screen and the api is more than a direct fix.
  - `[low]` `[reject]` (blind 4) Debrief calls share the Class session's budget with the LLM players. That is AD-6/FR-69's design: one budget per scope, the reserve kept for non-player purposes; the story says the call may spend the reserve.
  - `[false]` `[reject]` (blind 5) A transient failure stores code text for good. The AC: on any failure the caller returns the fallback and never retries.
  - `[low]` `[patch]` (blind 6) The sweep's finder joined a `DISTINCT` over all `seat_occupancy` rows every minute. Now a correlated `EXISTS` per Seat of the window's games. The starvation part (50+ Seats failing for 48 h) is rejected as unlikely; a lost job is the case the sweep is for.
  - `[false]` `[reject]` (blind 7) Hook failure rolls back the finish; processes without the hook. Deferring inside the finish transaction is the AC (atomic); a failing `defer` is a database error that fails the transaction anyway. Every process that finishes Class games loads the hook: the api (routes), every worker (`TASK_MODULES` now holds `debrief.jobs`, asserted).
  - `[low]` `[reject]` (blind 8) The quiz line may pick a sentence unrelated to the question; one call per question per Seat up front. The template set and facts-only output are the AC's; lazy calls would put an LLM on the result path or change text under the reader.
  - `[low]` `[patch]` (blind 9) The validator accepted one fact twice in a sentence and a repeated sentence. Now `repeated`; golden tests added.
  - `[medium]` `[patch]` (blind 10) «Ukene etter Uke N kostet … kr» implied every later Uke while `later_cost` covers only the following `later_weeks`. Templates gained `later_first_week`/`later_last_week`; v1 now reads «Etter Uke N: i Uke A til B kostet leddet ditt … kr.» and the validator refuses it for a fact with fewer than two later Uker (`not_applicable`). «med ordre inn» reworded «da ordren inn var». Lane databases re-migrated.
  - `[low]` `[reject]` (blind 11) Draft copy as immutable v1; downgrade leaves dangling pins. Same as every earlier content kind (draft, superseded by a new version); downgrade is a dev operation.
  - `[low]` `[patch]` (blind 12) No frontend check of the quiz's AI line. The e2e spec now answers the quiz and asserts the marked line and the note. The repeated note per wrong answer and the print-route claim (a marker for a later route) are kept.
  - `[low]` `[reject]` (blind 13) Thin observability. Calls are logged per purpose and outcome with `llm_call` rows; a cost view is Epic 15's.
  - `[false]` `[reject]` (edge 1) A raising hook rolls back the finish. As blind 7.
  - `[low]` `[reject]` (edge 2) Sweep starvation. As blind 6.
  - `[low]` `[reject]` (edge 3) A re-defer while a job is `doing` may call twice. Only 10 minutes after the finish; a job takes seconds; the row is insert-once.
  - `[low]` `[patch]` (edge 4) Repeated fact ids. As blind 9; out-of-order Uker stay allowed (still true).
  - `[low]` `[reject]` (edge 5) The number check compares digit runs, weaker than whole values. Defence in depth behind code-filled slots; a literal in a template is the case it catches.
  - `[false]` `[reject]` (edge 6) Empty `llm_call_ids` on a `Result`. `gateway.run` returns a `Result` only after logging the attempt's row.
  - `[low]` `[patch]` (edge 7) `created_at = now()` is the transaction start. Now `clock_timestamp()`.
  - `[low]` `[reject]` (edge 8) The dev outage flag is process-global. Dev and e2e only; the e2e narrates one Seat at a time.
  - `[low]` `[reject]` (edge 9, claim) `render` is None only without moments. Spec wording; the templates type forces every id.
  - `[false]` `[reject]` (edge 10, claim) The sweep stops after 48 hours. Documented bound (README, module docstring).
  - `[low]` `[patch]` (verification 1) `DUE_ACTIONS` membership not asserted. Asserted in the sweep test.
  - `[low]` `[patch]` (verification 2) Worker task registration not asserted. Asserted in `test_worker.py`.
  - `[low]` `[patch]` (verification 3) The sweep's AI-off filter not asserted. Asserted in the AI-off test.
  - `[low]` `[patch]` (verification 4) Quiz AI line not checked in the web app. As blind 12.
  - `[low]` `[reject]` (verification 5) The quiz cutoff only checked positively. The same `_ai_text` cutoff is checked negatively on step 4.
  - `[low]` `[patch]` (verification 6) `worded` with an unexpected exception untested. Test added.
  - `[low]` `[patch]` (verification other 1) «???». As blind 1.
  - `[low]` `[patch]` (verification other 2) Gateway errors printed the scope id as the config id. Now the config id.
  - `[false]` `[reject]` (verification other 3) «Lag fra tidligere» does not copy `debrief_ai_text`. Same as `debrief_release` (sessions README: not copied).
  - `[low]` `[reject]` (intent a) The e2e and api tests run the job in process, not through `worker-batch`. The job function, its deferral rows and the worker's task registration are each asserted; the e2e uses the job's own code through the dev route so the first view is not raced.
  - `[low]` `[reject]` (intent b) The moments game runs the hook by hand. The short games finish through `games.commands.finish` and assert the deferred jobs.
  - `[low]` `[reject]` (intent c) The Group-debrief test has no moments. The AC (every step opens with the job never run) holds; code text before the job is asserted in the moments test.
  - `[low]` `[patch]` (intent d) The AI-off test did not observe the gateway. Asserts no `llm_call` row.
  - `[false]` `[reject]` (intent e) The mock's AI text equals the code text. By design: the mock answers with the code's own choice (AD-17); the AC's visible difference is the marking.
  - `[false]` `[reject]` (intent f) New content kind instead of the 9.4/9.7 sets. Decision (Design Notes): a pinned version of its own.
  - `[false]` `[reject]` (intent g) Per Seat, keyed by Game and Seat. Decision (Design Notes).
  - `[false]` `[reject]` (intent h) Quiz line additive. Decision: the fixed explanation always shows, as the AC's fallback.
  - `[false]` `[reject]` (intent i) The note shows only under AI text. The prefix itself says «kan ta feil»; the note follows each AI text.
  - `[false]` `[reject]` (intent j) No print route. The AC asks for a marker the print route can reuse.
  - `[false]` `[reject]` (intent k) Spine entry not edited. It is (`.docs` was left out of the review diff).
  - `[low]` `[patch]` (intent l) «???». As blind 1.

## Design Notes

Narration is per facts set (Seat), not per Student: its inputs are the Seat's facts only, so one job per Student-held Seat covers every Student ever assigned to it without paying twice for a Seat two Students held; the job key is `game:seat` because the facts set is built by the job (not inside `finish`). "Fixed at first view" uses the immutable `debrief_fact_sets.recorded_at`: a Student who opens step 4 before the narration is stored keeps the code text. The mock answers with the code's own choice as `mock_answer`, so the accepted text equals the code text and differs only in its marking. Production setup: `python -m app.ai.cli config edit <id> --prompt debrief_narration=1 --prompt quiz_explanation=1`, then measure and pin.

## Verification

**Commands:**
- `uv run pytest -n0 tests/analysis/test_narration.py tests/ai/test_text.py tests/debrief/test_narration.py` -- pass
- full backend `--maxprocesses=8`, `ruff check`, `ruff format --check` -- pass
- `npm run typecheck`, `npm test`, `npm run lint:colours`, `npm run check:copy`, `npm run build` -- pass
- Playwright `debrief-narration`, `debrief-*`, `class-session*`, `homes`, play-screen specs `--workers=4` -- pass

## Auto Run Result

Status: done

**Summary.** A facts-only AI narration on Debrief step 4 and an AI line under a wrong quiz answer, both behind a Lecturer's switch. `analysis.narration` (pure, re-exported as `analysis.validate_ai_text` and `analysis.render`) holds the output schema (`AiTextOutput`: sentences of a template id and fact ids, nothing else), the validator (unknown fact, unknown template, wrong arity, repeated, not applicable, number outside the cited facts) and the code narration. A new content kind `narration_templates` (v1 in migration 0112, draft copy, pinned at the lock) holds the four sentences code fills. `app.ai.text.worded` makes one `gateway.run`, returns `{text, ai_generated, llm_call_id}`, and gives the caller's fallback on a `GatewayError`, any typed failure, a rejection or an exception; the purposes `debrief_narration` and `quiz_explanation` (one attempt, may spend the reserve) have versioned prompts. A Class-session scope now names its config (`BudgetScope.model_config_id`, from the Debrief pin); players are unchanged. `games.service.on_game_finished` runs inside `finish`; the Debrief's hook defers one `llm-batch` job per Seat a Student held when the pinned `debrief_ai_text` is on. The job stores the narration and each quiz line once in `debrief_ai_texts`; the sweep re-defers a lost one. Step 4's `narration` is the stored text if stored before the Student's first view of step 4, else the code text, and never changes after. The web app marks AI text only by `ai_generated`: «KI-generert, kan ta feil: «…»», `data-ai-generated="true"` and the note that it can be wrong. The Klasseøkt has the Bryter «KI-tekst i Debriefen», frozen at the lock. Zero-config derives and pins a mock config with the new prompts; the spine's Deferred timing entry is closed for the Debrief.

**Files.**
- `backend/app/analysis/narration.py` (new), `analysis/__init__.py`: schema, validator, code narration.
- `backend/app/ai/text.py` (new), `ai/{purposes,budget,gateway,seed}.py`, `ai/prompts/{debrief_narration,quiz_explanation}/v1.md`, `prompts/hashes.json`, `ai-configs/mock.json`: helper, purposes, Class-session config, zero-config upgrade.
- `backend/migrations/versions/0112_debrief_narration.py` (new): kind + v1, `class_sessions.debrief_ai_text`, `debrief_ai_texts`.
- `backend/app/modules/content/*`: kind, schema, reader and pin.
- `backend/app/modules/sessions/{models,repo,schemas,routes,service,README}`: the switch, its lock refusal, the `debrief_ai_text` pin.
- `backend/app/modules/games/{service,commands,repo}.py`: finish hooks, the sweep's Seat finder.
- `backend/app/modules/debrief/{narration,jobs}.py` (new), `{models,commands,service,schemas,dev,README}`: hook, job, sweep, reads, dev narrate route.
- `backend/app/platform/{jobs,events/registry}`, `modules/ops/sweep.py`: task module, registry entry, due action.
- Tests: `tests/analysis/test_narration.py`, `tests/ai/test_text.py`, `tests/debrief/test_narration.py` (new); updates to `test_migrations`, `test_imports`, `test_authz_rules`, `test_worker`, `ai/conftest`, `ai/test_prompt_files`, `content/test_content`, `sessions/test_lock`, `debrief/test_explanation`, `debrief/test_group` (`played` takes save fields).
- Frontend: `modules/debrief/ai-text.tsx` (new), `{api,moments-step,quiz-step,debrief.test}`, `modules/sessions/{class-session-page,choices,choices.test,api}`, `copy/nb.ts`, regenerated `lib/api/{openapi.json,schema.ts}`, `e2e/debrief-narration.spec.ts` (new), `e2e/support/live-game.ts` (`debriefMode`).
- `.docs/.../ARCHITECTURE-SPINE.md`: the Deferred timing entry closed for the Debrief.

**Decisions for the founder.** Implemented in the builder's own context (orchestrator rule), four review layers. (1) One job per Seat a Student held, keyed `narration:<game>:<seat>`, stored per `fact_set_id`: the narration is the Seat's facts set's, so it serves every Student of the Seat; the facts set is built by the job, not inside `finish`. (2) «Fixed at the first view» means the first view of step 4 (`debrief_fact_sets.recorded_at`): a Student who opens step 4 before the job ran keeps the code text. (3) The narration templates are a new pinned kind with four draft sentences; the LLM picks sentences and facts, code writes every word, so no cause is ever stated. (4) The quiz line is extra, under the fixed explanation, only for a wrong answer to a question with an own-game sentence; generated with the narration, shown only if stored before the attempt. (5) The Debrief uses the Class session's own model config (also in a Rule-based session); the switch pins on only with a config whose prompts name the narration; an older config stays code-only. (6) LLM players of Class sessions still have no config binding (`scope_unresolved`, Story 2.3's note); unchanged here. (7) The 9.2 import rule now lets `modules/debrief` use `app.ai.text`, `app.ai.budget` and `app.ai.gateway`, nothing else of `app/ai`. (8) Production setup: `python -m app.ai.cli config edit <id> --prompt debrief_narration=1 --prompt quiz_explanation=1`, then measure and pin; local/test/ci do it at start. (9) The Playwright test drives the job through `POST /api/dev/games/{id}/seats/{seat}/narrate[?outage=true]` (dev only, not in OpenAPI). (10) Copy is draft `[ASSUMPTION]`.

**Review.** 44 findings (high 0, medium 2, low 29, false 13). Patched 2 medium (a pre-9.14 config pinned AI text on; the later-cost sentence implied every later Uke) and 12 low root causes (repeated facts, insert time, sweep query, gateway messages, «???», tests for the due action, worker task, AI-off sweep, `worded` exceptions, the pin, the quiz line in the web app, no gateway call when off). Nothing deferred. The rest rejected with reasons in the triage log. followup_review_recommended: true (patched: medium 2, low 12): the narration has never run against a real provider (the OpenRouter key is blocked for agents, Issue #9), so how often a real model's output passes `validate_ai_text` and fits the one attempt and budget is unverified. Command for a real call once a key is set: create a Class session on a pinned real config with `config edit … --prompt debrief_narration=1 --prompt quiz_explanation=1`, finish a game, run `worker-batch`, then `SELECT outcome, response FROM llm_call WHERE purpose IN ('debrief_narration','quiz_explanation')` and `SELECT subject, ai_generated FROM debrief_ai_texts`.

**Verification.**
- Backend after the patches: full suite `--maxprocesses=8` 2981 passed, 4 skipped (117 s); `ruff check`, `ruff format --check` clean. Migration 0112 up and down in `test_migrations`. The lane's databases were taken down to 0111 and up again after the template wording changed.
- Frontend: typecheck, Vitest (55 files, 782 tests), `lint:colours`, `check:copy`; `next build` in the lane image build.
- Playwright on the lane stack (8081), rebuilt after the last change, `--workers=4`: `debrief-narration` (360 and 1440 px with axe), every `debrief-*`, every `class-session*`, `homes`, `student-home`, `live-updates`, `game-end`, `order-confirm`, `week-advance`, `game-card`, `order-field`, `seat-status`, `guided-week`: 240 of 240.
- Failed once, passed on rerun: `homes.spec.ts` «each User refused a page gets a link to their own home» (six parallel logins under the full run's load; its 5 s wait ran out), before the patches; the whole set passed after them.
- Tests over 1 s: `test_narration.py::test_the_finish_defers_narration…` about 8.6 s (a 14-Uke game), `…group_debrief_opens_every_step…` about 3.8 s, `…sweep_defers…` about 1.8 s, `…ai_text_off…` about 1.7 s (each plays a Class game through the api).

**Residual risks.** No real-provider run (above). Class-session LLM players still fall back to Rule-based Orders (no config binding, pre-existing). A Seat whose job keeps failing is retried by the sweep for 48 hours, then left with code text. A Student who views step 4 before the job ran keeps the code text. Draft copy awaits review.
