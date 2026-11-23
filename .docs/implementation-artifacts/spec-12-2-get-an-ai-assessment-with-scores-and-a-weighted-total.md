---
title: 'Story 12.2: Get an AI assessment with scores and a weighted total'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: '7eaa53b3b466e85c4741cd9f0dce4d059afe7b99'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-12-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** A closed Individual test is never assessed: long answers and Adapted items have no score, there is no weighted total, and the Student has no «KI-vurdering» to open (FR-54, FR-55, FR-61, FR-80).

**Approach:** `tests.close_attempt` defers the idempotent job `assessment.assess(attempt_id)` on `llm-batch` in its transaction through `assessment.service` when the pinned switch is on. The job makes one `gateway.run(purpose="assessment")` call per unscored long/Adapted item on the model config pinned by `sessions.lock_test`, stores `ai_assessments` + `ai_item_scores`, and re-defers itself with back-off until every item is scored (`ready`) or the run cap is hit (`failed`). The Student reads «KI-vurdering» from Hjem; the total comes only from the pure `analysis.total_score`.

## Boundaries & Constraints

**Always:** `assessment` stays a leaf (imports no `app.modules.*`); `tests` registers an attempt reader with `assessment.service` and builds the Student view (tests → assessment.service only). The job asks `assessment_due` first; reads only the pinned Scoring guide version, question set version and model config; passes no model, prompt version or scrub terms; never retries a typed failure or `GatewayError` in the same run. Output schema: one `score` 0–4, no criteria. Every `ai_item_scores` row stores `scoring_guide_id`, `question_set_version`, `model_config_id`, `llm_call_id`. Back-off and run cap from settings (placeholders). Free text in the prompt has `<`/`>` replaced by look-alikes. Every view starts «KI-generert, kan ta feil. Teller ikke. Ingen karakter.»; numbers through `formatNumber`; text labels, no colour alone; ids only in logs and job args. New copy in `nb.ts`, `[ASSUMPTION]` where drafted. Migration 0202 revises 0201.

**Never:** No feedback text, quotes or fact validation (12.3), no notice, `assessment_ready` step or sweep re-defer (12.4), no flags or staff view (12.5), no letter (12.6). No partial total. No copy or recompute of the computed scores `tests` stored. No second enqueue path. No real endpoint in tests; no `.env`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Close, switch on | `close_attempt` at `effective_deadline`, pinned on | one `assessment.assess` job (lock `assessment:<attempt>`) in the close's transaction | — |
| Close, switch off | pinned off | no job, no row, no `llm_call` | — |
| Early hand-in / timed sitting ended days before | submitted or `end_sitting` before the deadline | no job until `close_attempt` at the deadline | — |
| Job, all calls ok | long + Adapted items | one call per item, `ready`, rows with versions and `llm_call_id` | — |
| Blank long/Adapted answer | no or whitespace text | step 0 stored by code, no call, `llm_call_id` NULL | — |
| Typed failure / GatewayError | e.g. `provider_error` | item left unassessed, no second call this run; `incomplete`, `runs+1`, one later run deferred at now + backoff | logged by id |
| Run cap | `runs == assessment_max_runs` still missing | `failed`, nothing deferred | — |
| No config pinned | config without the `assessment` prompt, no usable default | `failed` at first run, no call | — |
| Repeat run | `ready`/`failed` | nothing stored, nothing deferred | — |
| Student view | no attempt / open or no row / switch off / incomplete / failed / ready | `no_test` / `not_ready` / `switched_off` / items + unassessed list, no total / note only / items + total | outsider 403 `forbidden` |

</intent-contract>

## Code Map

- `backend/app/modules/tests/commands.py` -- `close_attempt` (~653): after the update, `await assessment.schedule(s, attempt_id, class_session_id)`.
- `backend/app/modules/assessment/{service,models}.py` -- 12.1 switch API; add `pin_switch(..., model_config_id, effort_level)`, tables, `schedule`, `assess`, `register_attempt_reader`, `assessment_of`, dataclasses `AttemptToAssess`/`ItemToAssess`/`AssessmentRecord`; new `jobs.py` (task `assessment.assess`).
- `backend/app/modules/sessions/service.py` -- `lock_test` (~4615) passes the chosen config: the row's `model_config_id` when its config names `assessment`, else for `kind=course` the active default if it names it; `config.mark_referenced`. Pattern: `debrief_ai_text_pin` (~4033).
- `backend/app/ai/{purposes.py,seed.py,prompts/assessment/v1.md,prompts/hashes.json}`, `backend/ai-configs/mock.json` -- purpose `assessment` (1 attempt, not player), mock spec prompts → zero-config derives a new default row (Story 2.2 `config.derive`).
- `backend/app/ai/gateway.py` -- `run`, `Inputs`, `Result`, `Failure`, `GatewayError`; `BudgetScope.class_session(id, effort_level, model_config_id)`.
- `backend/app/platform/jobs/__init__.py` -- `defer(..., schedule_at=)`; `TASK_MODULES` += `app.modules.assessment.jobs`.
- `backend/app/platform/config.py` -- `assessment_retry_minutes` (30), `assessment_max_runs` (4), placeholders.
- `backend/app/analysis/total.py` -- pure `total_score(computed, ai_items, weights) -> float | None`.
- `backend/app/modules/tests/assessed.py` (new) -- the reader (frozen items, answers, guide via `guide.in_force`, Adapted fact lines via `analysis.adapted.picked` + new `games.service.fact_set_by_id`), and the Student view; registered at import from `tests/commands.py`.
- `backend/app/modules/games/{service,repo}.py` -- `fact_set_by_id`.
- `backend/app/modules/tests/{routes,schemas}.py` -- `GET /api/me/class-sessions/{id}/test/assessment` (`tests.take_own`), `MyAssessmentOut`.
- `backend/migrations/versions/0202_ai_assessments.py`, `migrations/env.py` -- pin columns, `ai_assessments`, `ai_item_scores`.
- `backend/app/platform/events/registry.py` -- `assessment.assess`: `{"user"}`.
- `frontend/src/modules/assessment/{assessment-page.tsx,assessment.ts,api.ts}`, `src/app/(app)/ki-vurdering/[sessionId]/page.tsx`, `src/modules/games/student-hjem.tsx` (Lenke «KI-vurdering» after Stegene once the test step is done), `src/modules/identity/homes.ts` (`ASSESSMENT_PATH`), `src/copy/nb.ts`. Patterns: `individual-test-page.tsx`, `submitted-items.tsx`, `itemLines`.
- Tests: `backend/tests/assessment/test_assess.py`, `tests/analysis/test_total_score.py`; helpers `tests/individual_test/test_answer.py::opened`, `test_auto_submit.py`; `frontend/e2e/ai-assessment.spec.ts` (stand-ins as `individual-test.spec.ts`).

## Tasks & Acceptance

**Execution:**
- `migrations/versions/0202_ai_assessments.py` -- `assessment_switches.model_config_id`/`effort_level`; `ai_assessments` (id, attempt_id unique FK cascade, class_session_id, user_id FK cascade, status check `incomplete|ready|failed`, runs, scoring_guide_id, question_set_version, model_config_id, reason, created/updated/ready_at); `ai_item_scores` (assessment_id FK cascade, item_id, score 0–4 check, source `ai|blank`, llm_call_id, the three versions, created_at; PK assessment+item).
- `app/analysis/total.py` + `tests/analysis/test_total_score.py` -- golden cases: full, excluded item ignored, Adapted split weight, missing item → None.
- `app/ai/*`, `ai-configs/mock.json` -- purpose, prompt v1 + hash, mock spec.
- `app/modules/assessment/*`, `platform/jobs`, `platform/config`, `events/registry`, `sessions.lock_test`, `tests/commands.py`, `tests/assessed.py`, `games` -- as in the Code Map.
- `tests/assessment/test_assess.py` -- matrix rows, PII (Roster name, email, staged student number absent from `llm_call.request`), timed sitting days earlier, versions on rows, idempotency, view states, 403; migrations/imports/authz tests updated.
- Frontend page, Hjem Lenke, copy, `npm run api:generate`; `e2e/ai-assessment.spec.ts` -- five states at 320/360/1440 with axe (stand-ins), one stack test: hand in → Hjem «KI-vurdering» → not ready.

**Acceptance Criteria:**
- Given the job runs, when it scores, then each call's request holds the question, the answer, the pinned guide entry (title, guide text, criteria, scale) and, for an Adapted item, its fact lines, and no Roster term.
- Given a ready assessment, when the Student opens it, then they see the disclosure, per item its number, type, points of weight, the computed explanation for answer-key and Interactive items and «n av 4» with the scale label for long/Adapted items, and the weighted total; no pass/fail, no letter.
- Given incomplete or failed, then no total; incomplete lists the unassessed item numbers, failed says the computed scores are in the Studentrapport.

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
Layers: blind hunter, edge-case hunter, verification gap, intent alignment (sonnet; four reviewers for a data-model, concurrency and deadline change).
- verdicts: 48 findings — high 0, medium 8, low 27, false 13, maybe-false 0
- findings:
  - `[low]` `[patch]` Blind: a question with no Scoring guide entry is still sent with an empty guide — the job now makes no call for an item without its guide entry (logged by attempt id); it stays unassessed.
  - `[medium]` `[patch]` Blind: a run that raises before `_finish` defers no later run — every item's work runs under its own guard, so a provider, database or validation exception leaves that item unscored and the run still counts and re-defers; a failure before the row exists (reader, `_started`) is left to Story 12.4's sweep re-defer (residual risk below).
  - `[low]` `[patch]` Blind: `jobs.defer`'s False in `_finish` is ignored — now logged (`assessment_rerun_not_deferred`); a waiting run of the same attempt is the only cause and goes on.
  - `[low]` `[reject]` Blind: «innen ett døgn» is not tied to the back-off settings — the line is the spine's, the epic calls 24 hours a target until measured, and both settings are placeholders.
  - `[low]` `[reject]` Blind: a failed assessment is terminal with no re-run path or staff view — Story 12.4 holds stop/resume and the sweep, 12.5 the staff view; outside "build only this story".
  - `[low]` `[reject]` Blind: failed calls cannot be traced to an item — each `llm_call` row stores the scrubbed request, which holds the question, and the caller reference names the attempt.
  - `[low]` `[patch]` Blind: the scale's top step is defined twice — `assessment.service` now imports `SCALE_TOP` from `analysis.total`; the content schema fixes the scale at steps 0 to 4.
  - `[false]` `[reject]` Blind: item points and the total may differ by rounding — computed credits are criteria weights over 100 (or 0/1) and AI shares quarter steps of whole weights, so every item's points are exact at two decimals and the total equals their sum.
  - `[false]` `[reject]` Blind: a corrupt stored credit or a frozen id missing from the question set makes the view 500 — credits come only from `score_answer` (0 to 1) and the frozen ids come from the very version the view reads.
  - `[low]` `[patch]` Blind: `incomplete` with an empty `unassessed` list renders «mangler vurdering: .» — the view now reads `not_ready` until the run that stored the last score settles the state.
  - `[false]` `[reject]` Blind: an empty scale label, and labels read from the guide in force rather than the pinned one — the content schema requires five labelled steps, and the guide in force is the pinned one from the Test-deadline lock on, before any score exists.
  - `[low]` `[reject]` Blind: the session's player config grades; sessions locked before 0202 have no pinned config — the config choice is this story's recorded decision (Design Notes); sessions locked before 0202 exist only in local dev data.
  - `[low]` `[patch]` Blind: prompt-injection hardening thin and untested — facts and scale labels are now quoted too, and a test proves an answer with `</answer>`/`<answer>` cannot close its block (answers are capped at 20 000 characters by `save_answer`).
  - `[low]` `[patch]` Blind: the lock's config branches are untested and `pin_switch` builds its values oddly — a test now covers own config with and without its Effort level, the default fallback, the Control test without fallback and the switch off; the values are one literal.
  - `[medium]` `[patch]` Blind: the reader registration depends on import order — `test_worker` now asserts `assessment.jobs` in `TASK_MODULES`, its queue, and that the worker's chain (`tests.jobs` → `tests.assessed`, registering at top level) registers the reader.
  - `[false]` `[reject]` Blind: the Hjem link text is the same in every session, and the failed copy promises the Studentrapport — the link sits in its session's block, labelled «Klasseøkt n» when there are several (purpose from context, WCAG 2.4.4), and the failed line is the AC's own wording.
  - `[low]` `[patch]` Blind: tests coupled to draft copy; `created_at` is the run's start — each score now stores its own time; the draft-guide assertions read the shipped content on purpose.
  - `[medium]` `[patch]` Edge: any non-gateway exception mid-run kills the chain — same root and fix as the Blind run-abort row.
  - `[medium]` `[patch]` Edge: a reader or content read failure raises before any call — same root; the reader's failures before the row exists are the residual left to Story 12.4's sweep.
  - `[low]` `[patch]` Edge: a long item with no guide entry or scoring rule is called with an empty guide — same fix as the Blind guide row.
  - `[false]` `[reject]` Edge: `by_id[item_id]` KeyError in `read` — frozen ids are taken from the attempt's own question set version.
  - `[false]` `[reject]` Edge: a frozen type outside the five-value Literal — the frozen list holds only `QuestionSetItem.type` values and `adapted`.
  - `[false]` `[reject]` Edge: per-item rounding against the exact total — see the Blind rounding row.
  - `[false]` `[reject]` Edge: a stored credit outside 0 to 1 — see the Blind stored-value row.
  - `[low]` `[reject]` Edge: overlapping runs make duplicate calls — the queueing lock allows one waiting job per attempt and only a finishing run defers the next; Story 12.4's sweep re-defers only with no live job.
  - `[low]` `[reject]` Edge: sessions locked before 0202 fail with `no_model_config`; a repeat `lock_test` marks a config referenced — local dev data only; a repeat `lock_test` returns before it chooses a config.
  - `[low]` `[patch]` Edge: facts and scale labels unquoted — quoted now.
  - `[false]` `[reject]` Edge: an empty `llm_call_ids` on a Result — the gateway builds a `Result` only from an attempt it logged.
  - `[false]` `[reject]` Edge: a failed assessment hides stored partial scores — the AC's failed state shows the note only, with no total and no letter.
  - `[low]` `[reject]` Edge (claim): no trigger keeps item scores written once — the only writer inserts with `ON CONFLICT DO NOTHING`; a trigger adds a migration branch for no reachable path.
  - `[low]` `[patch]` Edge (claim): each call holds the guide entry — true now: an item without its entry gets no call.
  - `[low]` `[reject]` Edge (claim): idempotent only for sequential runs — see the overlapping-runs row.
  - `[medium]` `[patch]` Verification: `assessment.assess` in `TASK_MODULES` unverified — asserted in `test_worker`.
  - `[medium]` `[patch]` Verification: the worker's reader registration unverified — asserted through the import chain in `test_worker`.
  - `[low]` `[patch]` Verification: `games.fact_set_by_id` never runs unmocked — `tests/games/test_facts.py` reads a stored set back by id and gets None for an unknown or malformed id.
  - `[low]` `[patch]` Verification: the guide entry reaching the prompt is not asserted — guide titles and coded criterion lines asserted for a long and an Adapted item.
  - `[medium]` `[patch]` Verification: `_assessment_config` branches unverified — same test as the Blind lock-branches row.
  - `[low]` `[patch]` Verification: `_quoted` untested — test added.
  - `[low]` `[patch]` Verification: `partly`/`not_answered` mapping unasserted — a test reads a blank choice as `not_answered` with 0 points and each table item's result, criteria and points from its stored score.
  - `[low]` `[patch]` Verification (other): no config with only blank answers turns `ready` — `_finish` now fails `no_model_config` first.
  - `[medium]` `[patch]` Verification (other): a non-gateway exception skips `_finish` — same root as the Blind run-abort row.
  - `[low]` `[patch]` Verification (other): `SCALE_TOP` duplicated — same fix as the Blind row.
  - `[false]` `[reject]` Intent: the default config is a seed edit, not a row made with the Story 2.2 command — the zero-config seed derives a new row from the default with `config.derive` (the command's path) and pins it, as Stories 9.14 and 11.8 did; a referenced row never changes.
  - `[low]` `[reject]` Intent: the rendered ready, incomplete and failed pages are tested on stand-ins — the repo's pattern for state screens; the api's output of each state is pinned by the api tests and the shape by the generated types.
  - `[low]` `[patch]` Intent: direct calls instead of the worker, and a loose sitting assertion — the sitting test now asserts `ready`; direct calls keep the tests fast and the sweep order is pinned by Story 11.11's tests.
  - `[low]` `[patch]` Intent: the stored-facts read is mocked — same fix as the Verification facts row.
  - `[false]` `[reject]` Intent: the scrub test reads the stored request, not the wire — the gateway stores exactly the request it hands the model.
  - `[false]` `[reject]` Intent: the view lives in `modules/tests` — `assessment` may import no feature module (`test_imports`); tables stay `assessment`'s, as the epic says.

## Design Notes

- Pinned model config (settles 12.7's deferred row): `lock_test` stores it on the switch row with the pin, from `class_sessions.model_config_id` (kept by 12.7's trigger, set also for Rule-based sessions), not from `SessionRuntime`; a course session whose config predates the `assessment` prompt takes the active default that names it. A Control test never falls back.
- Total = Σ weight × share, share = computed credit or step/4, out of the frozen weights (sum 100); every weighted item must have a share, else None. An unanswered computed item has credit 0.
- The «KI-vurdering» Lenke is shown when the test step is `done`; before the pin the page reads the current switch value.

## Verification

**Commands:**
- `uv run pytest tests/assessment tests/analysis/test_total_score.py tests/individual_test tests/sessions/test_ai_assessment_switch.py tests/test_migrations.py tests/test_imports.py tests/ai` -- pass
- `npm run typecheck && npm run test && npm run lint:colours && npm run check:copy && npm run build` -- pass
- `npx playwright test e2e/ai-assessment.spec.ts --workers=4` -- pass

## Auto Run Result

Status: done

**Summary.** `tests.commands.close_attempt` defers `assessment.assess(attempt_id)` on `llm-batch` in its own transaction through `assessment.schedule`, only when the pinned «KI-vurdering» switch is on (`assessment_due`); nothing else enqueues a first assessment, so an early hand-in or a timed sitting that ended days before is assessed only at the Test deadline. `sessions.lock_test` now pins the assessment's model config and Effort level with the switch (migration 0202, `assessment_switches.model_config_id`/`effort_level`): the session's own `model_config_id` when its config names the `assessment` prompt (this also settles 12.7's deferred row: a Rule-based Control test keeps its config), else for a course session the active default that names it, never for a Control test. The job (`modules/assessment`, a leaf: `tests` registers a Test-attempt reader) keeps one `ai_assessments` row per attempt and makes one `gateway.run(purpose="assessment")` call per long-answer or Adapted item without a score, on the Class session's budget, with the question, the answer, the pinned guide entry (title, text, coded criteria, scale) and, for an Adapted item, its fact line from the stored facts set (`games.service.fact_set_by_id`); output is one `score` 0–4. An empty answer is step 0 by code with no call. Typed failures and other per-item errors leave the item unscored; the run counts and defers one later run after a back-off (`assessment_retry_minutes`, doubled; placeholder 30) until every item has a score (`ready`) or `assessment_max_runs` (placeholder 4) is reached (`failed`); with no pinned config it fails at once with no call. Every `ai_item_scores` row stores the guide version, question set version, model config and call id. The total comes only from the pure `analysis.total_score` (golden cases). The Student reads «KI-vurdering» (`GET /api/me/class-sessions/{id}/test/assessment`, `/ki-vurdering/{id}`, a Lenke on Hjem once the test step is done): disclosure first, then not ready, switched off, no test, failed (note), incomplete (items, the unassessed numbers, no total) or ready (each item's computed result with its criteria or AI step with its label, points of its weight, and the weighted total). Prompt `assessment/v1.md` (locked), purpose `assessment` (one attempt), mock spec names it, so the zero-config seed derives and pins a new default row.

**Process.** Implemented in the build agent's own context, as the lane brief requires, not by the workflow's implementation subagent.

**Decisions taken here (founder would otherwise):** the assessment's model config is pinned at the Test-deadline lock from the session's row, falling back to the active default for a course session made before the prompt existed; an empty answer scores step 0 with no call; `incomplete` is shown only after a finished run (before that «not ready»); before the pin the page reads the current switch value; weights are shown per item; placeholders 30 min back-off and 4 runs; the Hjem link appears when the test step is done.

**Files.**
- `backend/migrations/versions/0202_ai_assessments.py`, `backend/app/modules/assessment/{models,service,jobs}.py` — tables, pin columns, `schedule`, `assess`, reader registry, `assessment_of`.
- `backend/app/analysis/total.py` — `total_score`.
- `backend/app/ai/{purposes,seed}.py`, `backend/app/ai/prompts/assessment/v1.md`, `prompts/hashes.json`, `backend/ai-configs/mock.json` — purpose and prompt.
- `backend/app/modules/sessions/service.py` — `_assessment_config` and the pin in `lock_test`.
- `backend/app/modules/tests/{commands,assessed,routes,schemas,jobs}.py` — the enqueue, the reader, the Student view and route.
- `backend/app/modules/games/{repo,facts,service}.py` — `fact_set_by_id`.
- `backend/app/platform/{config.py,jobs/__init__.py,events/registry.py}` — settings, `defer(schedule_at=)`, task module, topic.
- `backend/tests/assessment/test_assess.py` (new), `tests/analysis/test_total_score.py` (new), `tests/test_migrations.py`, `tests/test_worker.py`, `tests/games/test_facts.py`, `tests/ai/{conftest,test_prompt_files}.py`.
- `frontend/src/modules/assessment/{api.ts,assessment.ts,assessment-page.tsx,assessment.test.ts}`, `frontend/src/app/(app)/ki-vurdering/[sessionId]/page.tsx`, `frontend/src/modules/games/{home.ts,student-hjem.tsx}`, `frontend/src/modules/identity/homes.ts`, `frontend/src/copy/nb.ts`, `frontend/src/lib/api/{openapi.json,schema.ts}` (generated), `frontend/e2e/ai-assessment.spec.ts` (new).

**Review.** 48 findings from four sonnet reviewers (blind, edge case, verification gap, intent alignment). Patched: 3 medium entries (a run that raised before settling: per-item guard so the run counts and re-defers; the worker's task and reader registration asserted; the lock's config branches tested) and the low ones in the triage log (no call without a guide entry, `defer` refusal logged, one `SCALE_TOP`, no empty «mangler vurdering» list, facts and scale quoted, block-closing answer test, per-score time, `fact_set_by_id` test, guide entry in prompt asserted, `partly`/`not_answered` asserted, no-config before ready, tight sitting assertion). Rejected: 9 low and 13 false, each with its reason in the triage log. Nothing deferred.

**Follow-up review: recommended.** Three medium entries were patched (patched entries: high 0, medium 3, low 11). Unverified risk: a run that raises before its assessment row exists or outside the item loop (the reader's content reads, `_started`) defers no later run; until Story 12.4's sweep re-defers lost assessment jobs, such an attempt reads «not ready».

**Verification.** Backend: full suite `--maxprocesses=8` 3709 passed, 4 skipped (before the review patches 3705 passed); `ruff check` and `ruff format --check` clean. Frontend: `tsc` clean, Vitest 1179 passed, `lint:colours` and `check:copy` pass, `next build` ok, OpenAPI regenerated and current. Playwright on the lane-3 stack (8082, rebuilt after the patches): `ai-assessment` (five states at 320/360/1440 with axe, denied page, live hand-in → Hjem link → not ready), `homes`, `student-home`, `individual-test`, `order-field`, `week-table`, `game-start`: 131 passed. Matrix audit: every row has a passing api test in `tests/assessment/test_assess.py`. New tests over 1 s: each `test_assess.py` test takes about 1.7–2.8 s (the shared `locked_with` fixture locks a session and opens its Class game, as in `test_prepare.py`); no other new test over 1 s.

**Residual risks.** See the follow-up risk above. Sessions whose switch was pinned before 0202 (local dev only) have no pinned config and fail with `no_model_config`. The real provider's config (`openrouter-deepseek*.json`) does not name `assessment` yet; an operator adds it with the config command before the pilot, as for the Debrief prompts. All new Student copy except the disclosure, «kommer innen ett døgn» and the switched-off line is [ASSUMPTION] draft copy.

**Personal data.** New table with `user_id`: `ai_assessments` (one row per Test attempt: user, Class session, state, versions). `ai_item_scores` holds scores and ids only, no text a User wrote.
