---
title: 'Story 12.4: Be told when the AI assessment is ready'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: 'ef6c9beaa381d6bbf1bc1a288ce482f9fc1c154f'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-12-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-12-2-get-an-ai-assessment-with-scores-and-a-weighted-total.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** A Student never learns that their AI assessment is ready unless they keep checking; a lost or crashed `assess` job (12.2's residual risk: a run that fails before its row exists queues nothing) stays «not ready» for ever; a failed assessment tells no Admin; and there is no way to stop the assessment of a Class session at the cost limit and restart it later (FR-54, FR-55, FR-61, FR-69, NFR-8).

**Approach:** The ready transition of `assessment.assess` records `assessment_ready` through `progress.record_step` and enqueues an `assessment_ready` digest notice in the same transaction; the failed transition enqueues one `assessment_failed` digest per Admin per Class session. `schedule` creates the assessment row in the close's transaction (with the attempt's `effective_deadline` as `due_at`), so the sweep's new `assessment.overdue` action sees every unsettled assessment: 24 hours after `due_at` it logs `assessment_overdue` once and re-defers the job when no job is alive and runs remain. `stop_for_session` / `resume_for_session` set and clear an audited stop mark that the job, the sweep and the Student view honour. Hjem shows «KI-vurderingen er klar.» with the Lenke live through `user:<id>`.

## Boundaries & Constraints

**Always:** `assessment` imports no feature module except `progress.service` (AD-16 lets any module call it; `test_imports` widened to exactly that); Admins come through a reader `sessions.service` registers (`identity.active_admins`); `platform/notify` and `platform/audit` are platform. Notices: `assessment_ready` (user, dedupe `assessment_ready:<attempt>`, ref Class session) and `assessment_failed` (each active Admin, dedupe `assessment_failed:<class_session>:<admin>`, ref Class session), both `digest` in `messaging.delivery.KINDS` with templates in `platform/email/templates/kinds/` and context resolvers in `sessions.service` (class name; the Student must still be a registered Student). The mail holds no score, letter or feedback; it says AI-generated, can be wrong, counts toward nothing, not a grade. Logs and job args: ids only. Overdue after `assessment_overdue_hours` (24, setting). Stop mark on `assessment_switches` (`stopped_at`, `stopped_by`), which the pin trigger lets change after the pin; every other pinned column stays refused. Copy in `nb.ts`, drafts `[ASSUMPTION]`. Migration 0204 revises 0203.

**Never:** No Admin screen (Epic 15), no staff view or flags (12.5), no letter (12.6); no automatic stop at the cost limit (the Admin acts); no second notice on a repeat run; a ready assessment never becomes unreadable through a stop; no real endpoint, no `.env`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Ready | last item scored | same transaction: `ready`, `progress` step `assessment_ready`, one notice, `user`+`session` events | — |
| Repeat run | `ready` | no step, no notice | — |
| Failed | run cap or no config | one `assessment_failed` notice per active Admin; a second failed assessment in the session adds none | — |
| Close | switch on, not stopped | row `incomplete`, runs 0, `due_at`, job deferred | — |
| Close while stopped | stop mark set | row made, no job | — |
| Overdue, lost job | `incomplete`, `due_at` ≤ now−24 h, no live job, runs < max | `assessment_overdue` logged once (`overdue_at`), job re-deferred, `updated_at` = now | sweep repeats only after `assessment_retry_minutes` |
| Overdue, job waiting | live `todo`/`doing` job | logged once, nothing deferred | — |
| Overdue, stopped or runs ≥ max | — | not found / nothing deferred | — |
| Stop | `stop_for_session` | mark with time and actor, audit `assessment.stopped`; job ends before its next call; not-ready view → `switched_off`, ready stays readable | repeat stop: no-op, no audit |
| Resume | `resume_for_session` | mark cleared, audit `assessment.resumed`; every `incomplete`/`failed` reset to `incomplete`, runs 0, and re-deferred | — |
| Extended Student | own `effective_deadline` later | others' jobs at the original deadline; theirs only after their own, with the guide pinned at the original | — |

</intent-contract>

## Code Map

- `backend/app/modules/assessment/service.py` -- `schedule` (~316) gets `user_id`, `question_set_version`, `due_at`, inserts the row (pinned config) and defers unless stopped; `_started` (~629) fills `scoring_guide_id` when NULL; `_finish` (~671) ready/failed side effects; `assess` (~736) stop checks; new `stop_for_session`, `resume_for_session`, `due_overdue`, `overdue_due`, `register_admin_reader`; `Switch.stopped_at`.
- `backend/app/modules/assessment/models.py`, `backend/migrations/versions/0204_assessment_notices.py` (new) -- `assessment_switches.stopped_at/stopped_by` (FK users SET NULL), `ai_assessments.due_at/overdue_at`, partial index on `incomplete`, trigger function compares pinned columns only.
- `backend/app/modules/tests/commands.py` `close_attempt` (~716) -- pass the new args.
- `backend/app/modules/tests/assessed.py` `read` -- stopped and not ready → `switched_off`.
- `backend/app/modules/tests/dev.py` (new), `backend/app/main.py` -- `POST /api/dev/class-sessions/{id}/test/close` (own attempt: deadline to now, `close_attempt`), local only.
- `backend/app/modules/sessions/service.py` -- `assessment_ready_mail_context`, `assessment_failed_mail_context` (pattern `debrief_released_mail_context` ~3445); register Admin reader.
- `backend/app/modules/messaging/delivery.py` -- two digest kinds; templates `kinds/assessment_ready.{txt,html}.j2`, `assessment_failed.{txt,html}.j2`.
- `backend/app/modules/ops/sweep.py` -- `DueAction("assessment.overdue", …)` after `tests.close_attempt`.
- `backend/app/platform/config.py` -- `assessment_overdue_hours` (24). `platform/jobs.live_locks` reused. `platform/events/registry.py` -- `assessment.assess` topics `{user, session}`, stop/resume.
- `backend/tests/test_imports.py`, `tests/test_migrations.py`, `tests/test_worker.py` -- updated.
- Frontend: `src/modules/games/home.ts` (`assessmentReady`), `student-hjem.tsx`, `src/copy/nb.ts`, `e2e/ai-assessment.spec.ts` (live ready on Hjem).

## Tasks & Acceptance

**Execution:**
- Migration, models, service, `tests` close/read, sessions contexts and registration, delivery + templates, sweep, settings, registry -- as in the Code Map.
- `backend/tests/assessment/test_notices.py` (new) -- every matrix row (helpers from `test_assess.py`), the mail body (disclosure, no digit, no feedback), the 400-attempt mock run through `llm-batch` (`long`), stop → resume all ready.
- Frontend Hjem line, Vitest for `assessmentReady`, copy; e2e on the stack: Hjem open, dev close → «KI-vurderingen er klar.» without reload → Lenke → `ready`; axe at 320/1440.

**Acceptance Criteria:**
- Given a ready assessment, when the digest goes out, then the Student's mail says it is AI-generated, counts toward nothing and is no grade, with no score, letter or feedback text, never between 22:00 and 07:00 Europe/Oslo.
- Given Hjem open, when the job marks the assessment ready, then «KI-vurderingen er klar.» and the Lenke appear without a reload.
- Given 400 closed attempts on the mock provider, when `llm-batch` runs, then all are `ready`.

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
Layers: blind hunter, edge-case hunter, verification gap, intent alignment (sonnet; four reviewers for a job, retry and data-model change).
- verdicts: 38 findings — high 0, medium 4, low 30, false 4, maybe-false 0
- findings:
  - `[false]` `[reject]` Blind: `stop_for_session`/`resume_for_session` have no caller or route — the AC builds the two commands only; "the Admin screen for this comes in Epic 15" (Story 15.6 calls them).
  - `[low]` `[reject]` Blind: the mails carry no link, no failure reason; the failed mail promises the Studentrapport — every mail ends with the app's address (shared footer); the failed line repeats the Student view's own wording; draft copy.
  - `[low]` `[reject]` Blind: the `assessment_failed` key is permanent, so a failure after a resume tells no one — the AC: "a second failed assessment in the same Class session sends no second notice to anyone".
  - `[low]` `[patch]` Blind: rows made before 0204 have `due_at` NULL and are never swept — 0204 now sets `due_at` from the attempt's `effective_deadline`.
  - `[low]` `[patch]` Blind: the trigger's pinned-column list is untested — a test now changes each pinned column after the pin (refused) and the stop mark (allowed); the downgrade body is 0120's, which 0202/0203 never changed.
  - `[false]` `[reject]` Blind: a stop before the pin is lost or surprises the lock — `pin_switch` updates only the pinned columns of an unpinned row, so the mark stays, and `schedule` reads it after the pin.
  - `[low]` `[reject]` Blind: `resume` is unconditional and keeps `overdue_at` — the AC resets "every incomplete and failed assessment"; the overdue log is "once per assessment".
  - `[low]` `[reject]` Blind: the stop audit row has no reason — the AC asks for the audit record; a reason would be a new parameter for Epic 15 to define.
  - `[low]` `[reject]` Blind: `_announce` reaches only Students with an assessment row — before the close no attempt has a row and the «KI-vurdering» page reads «not ready» from Hjem's Lenke only after the close; a Student lister for a stop before the Test deadline adds a registration for a rare case.
  - `[low]` `[patch]` Blind: the dev close leaves the moved deadline when the close is refused — the attempt's own deadline is put back on a 409.
  - `[low]` `[reject]` Blind: Hjem reads ready from the `report` step — `STEGENE` marks `report` done only by `assessment_ready`, which only the ready run records.
  - `[low]` `[patch]` Blind: the live line has no live region — the line's paragraph is `aria-live="polite"`.
  - `[low]` `[reject]` Blind: duplicated conditions, `updated_at` set when `_defer` returns False, `assert isinstance` — `live_locks` is read in the same transaction just before; the assert is the sweep's pattern for every action.
  - `[low]` `[reject]` Blind: the 400-attempt test is slow and bypasses the close — the AC asks for it on `llm-batch`; marked `long`; its surface is the queue's throughput.
  - `[low]` `[reject]` Blind: the Admin reader is a registration by import — asserted in `test_worker` through the worker's import chain, the same pattern as 12.2's attempt reader.
  - `[low]` `[reject]` Blind: the mail test strips the fixture's Class name; `_stopped` is a query per item — the fixture name is fixed; one indexed read per item next to an LLM call.
  - `[medium]` `[patch]` Edge: an overdue row with a live job is found every minute — every look now stamps `updated_at`, so the finder returns a row at most once per `assessment_retry_minutes`.
  - `[medium]` `[patch]` Edge: 200 such rows starve the lost-job rows behind them — same root and fix as the previous row.
  - `[medium]` `[patch]` Edge: a job that crashes before `_finish` is re-deferred for ever — the sweep's re-defer now counts as a run, so it stops at `assessment_max_runs`; new test.
  - `[low]` `[patch]` Edge: pre-0204 rows never match `due_at` — same fix as the Blind backfill row.
  - `[low]` `[patch]` Edge: a close and a resume at the same time can leave a row with no job — `schedule` share-locks the switch row, which `resume` locks for update.
  - `[low]` `[reject]` Edge: the failed key across a resume — same as the Blind key row.
  - `[low]` `[reject]` Edge: Students without a row get no event on a stop — same as the Blind `_announce` row.
  - `[low]` `[reject]` Edge: a stop for an unknown Class session raises a foreign-key error — the callers pass a Class session they read; a loud error is right for a bad id.
  - `[low]` `[reject]` Edge: Admins are told of a failure in a stopped session — only when the stop lands during the last run's last call; the assessment did fail.
  - `[low]` `[patch]` Edge: the dev close leaves the moved deadline — same fix as the Blind dev-close row.
  - `[medium]` `[patch]` Edge (claim): "repeats only after `assessment_retry_minutes`" did not hold for rows with a live job — same fix as the first Edge row.
  - `[low]` `[reject]` Edge (claim): resume misses closed attempts with no row — only attempts closed before 0204 (local dev data); every later close makes the row.
  - `[low]` `[reject]` Edge (claim): the failed notice is once per session for ever — the AC's rule, as above.
  - `[low]` `[patch]` Verification: the stop's events were checked with a subset that an empty emission passes — a test stops after the close and asserts the exact topics and ids, the stop mark's time and actor.
  - `[low]` `[patch]` Verification: the new trigger is tested for `enabled` only — same test as the Blind trigger row.
  - `[low]` `[patch]` Verification: `_finish`'s no-defer-while-stopped branch is not run — a test stops during the last item's call and finds no later job.
  - `[low]` `[patch]` Verification (other): pre-0204 `due_at` — same fix as the Blind backfill row.
  - `[false]` `[reject]` Intent: Hjem's ready line is inferred from the `report` step — the step is the AD-16 record the AC names; pinned by the api test through `/api/me/class-sessions` and by the live Playwright test.
  - `[low]` `[reject]` Intent: the dedupe key is `assessment_ready:<attempt id>`, no `not_before` — notice keys are unique across kinds, so the attempt id is prefixed; with no `not_before` the digest rules set the time.
  - `[low]` `[reject]` Intent: no staff surface shows the switched-off state — the staff view is Story 12.5, which reads the same switch.
  - `[low]` `[reject]` Intent: the 400-attempt test schedules through the service, not the close — the AC's surface is the `llm-batch` run.
  - `[false]` `[reject]` Intent: a dev route and extra columns outside the story — the dev close serves AC 3's live test (local only); the columns carry the AC's stop mark and 24-hour target.

## Design Notes

- The row at close replaces "every closed attempt that has no assessment yet": with the switch due, every closed attempt has a row from its close, so `resume` re-defers every `incomplete` one (runs 0 included). A row with runs 0 still reads «not ready» (12.2).
- The sweep's look is throttled by `updated_at` (set by every run and by every look of the overdue action), so a row is examined at most once per `assessment_retry_minutes`; a re-defer counts as a run, so a job that crashes before `_finish` is deferred at most `assessment_max_runs` times.

## Verification

**Commands:**
- `uv run pytest tests/assessment tests/test_imports.py tests/test_migrations.py tests/test_worker.py tests/messaging -q` -- pass
- `npm run typecheck && npx vitest run src/modules/games` -- pass
- `npx playwright test e2e/ai-assessment.spec.ts --workers=4` -- pass

## Auto Run Result

Status: done

**Summary.** The run of `assessment.assess` that marks an assessment `ready` now records `progress.record_step(user, class_session, assessment_ready, at)` and enqueues `notify.enqueue(user, "assessment_ready", "assessment_ready:<attempt id>", ref=<Class session>)` in the same transaction (a repeat run adds neither). Hjem's last step «Rapport» turns done, and the open Hjem says «KI-vurderingen er klar.» before its «KI-vurdering» Lenke, live through `user:<id>` (`aria-live="polite"`). `assessment_ready` and `assessment_failed` are `digest` kinds in `messaging.delivery` with Jinja2 templates. The Student's mail says the assessment is AI-generated, can be wrong, counts toward nothing and is no grade, and holds no score, letter or feedback. A `failed` run tells each active Admin once per Class session (key `assessment_failed:<session>:<admin>`; the Admins come through a reader `sessions.service` registers, since `assessment` may import only `progress.service` besides itself). `schedule` now creates the assessment row at the close, with `due_at` set to the attempt's own `effective_deadline` (migration 0204, which also sets it for older rows), so every closed attempt of a due session has a row. The new sweep action `assessment.overdue` (after `tests.close_attempt`) logs `assessment_overdue` once, with ids only, for an assessment still `incomplete` 24 hours (`assessment_overdue_hours`) after `due_at`. It defers the job again when no job is alive and runs remain; a re-defer counts as a run, and a row is looked at no more than once per `assessment_retry_minutes`. That closes 12.2's residual risk of a run lost before its row existed. `stop_for_session(class_session, actor)` sets an audited stop mark (`stopped_at`, `stopped_by` on `assessment_switches`; the pin trigger now refuses changes only to the pinned columns). From then on, `schedule` defers nothing, a running job ends before its next call, `_finish` defers no later run, the sweep skips the session, and the Student's view reads `switched_off` unless the assessment was ready. `resume_for_session` clears the mark, resets every `incomplete` and `failed` assessment to `incomplete` with runs 0, and defers each one, also audited. An extended Student is closed and assessed only at their own deadline, with the guide the lock pinned at the original one. A dev route `POST /api/dev/class-sessions/{id}/test/close` (local only) serves the live Playwright test.

**Process.** Implemented in the build agent's own context, as the lane brief requires, not by the workflow's implementation subagent; review fixes were applied by the build agent too.

**Decisions taken here (founder would otherwise):**
- The row is made at the close. This is how "every closed attempt that has no assessment yet" is reached on resume.
- The notice keys are prefixed with the kind.
- The ready mail text and the Admin's failed mail text are draft copy, with the failed mail naming the Class and the Klasseøkt number.
- Hjem's line «KI-vurderingen er klar.» is draft copy.
- `assessment` may import `progress.service`.
- A re-defer by the sweep counts as a run.
- Resume is unconditional: it also restarts failed assessments without a stop.
- A stop before the Test deadline is kept for the pin.
- A failure that lands during a stop still tells the Admins.
- Ready assessments stay readable after a stop. This is the epic's [ASSUMPTION].

**Files.**
- `backend/migrations/versions/0204_assessment_notices.py` (new), `backend/app/modules/assessment/{models,service}.py`: stop mark, `due_at`/`overdue_at`, the row at close, ready/failed notices, stop/resume, the overdue action.
- `backend/app/modules/tests/{commands,assessed}.py`: close passes the attempt's data; the view honours the stop. `backend/app/modules/tests/dev.py` (new), `backend/app/main.py`: the dev close.
- `backend/app/modules/sessions/service.py`: the two mail contexts and the Admin reader. `backend/app/modules/messaging/delivery.py` and `backend/app/platform/email/templates/kinds/assessment_{ready,failed}.{txt,html}.j2`: the kinds.
- `backend/app/modules/ops/sweep.py`, `backend/app/platform/{config.py,events/registry.py}`: the due action, the setting, the topics.
- Tests: `backend/tests/assessment/test_notices.py` (new); `tests/assessment/test_assess.py`, `tests/test_{imports,migrations,worker}.py` updated.
- Frontend: `src/modules/games/{home.ts,student-hjem.tsx}`, `src/copy/nb.ts`, `src/modules/assessment/assessment.test.ts`, `e2e/ai-assessment.spec.ts`.

**Review.** Four sonnet reviewers (blind, edge case, verification gap, intent alignment) reported 38 findings: high 0, medium 4, low 30, false 4.
- Patched, medium (two entries): the overdue finder now stamps each look, so a row with a live job is no longer returned every minute and the 200-row window advances; a sweep re-defer counts as a run, so a job that keeps crashing is bounded.
- Patched, low: `due_at` backfill; share lock between close and resume; the dev close restores the deadline; `aria-live`; tests for exact stop events, every pinned column, and no later run when the stop lands during the last call.
- Rejected: 19 low and 4 false, each with its reason in the triage log. Nothing deferred.

**Follow-up review: recommended.** Two medium entries were patched (patched entries: high 0, medium 2, low 7). The unverified risk is the overdue action's pacing over a long worker outage with many rows, which was tested on one row only. Counting a sweep re-defer as a run can also fail an assessment one run earlier than 12.2's back-off alone would.

**Verification.**
- Backend: full suite `--maxprocesses=8` 3753 passed, 4 skipped, after the review patches (3749 before). `ruff check` and `ruff format --check` are clean.
- Frontend: `tsc` clean, Vitest 1180 passed, `lint:colours` and `check:copy` pass, `next build` ok. No OpenAPI change (the dev route is not in the schema).
- Playwright on the lane-3 stack (8082), rebuilt after the patches:
  - `ai-assessment`: 22 passed, including the new live test, in which Hjem is open, the lock and the close run, `worker-batch` assesses on the mock, «KI-vurderingen er klar.» appears without a reload, axe passes at 320 and 1440 px, and the Lenke leads to `ready`.
  - `homes` and `student-home`: passed after the patches.
  - `individual-test`, `order-field`, `week-table` and `game-start`: passed before the patches (114 in all for the six specs).
- Matrix audit: every row has a passing test in `tests/assessment/test_notices.py`.
- New tests over 1 s:
  - `test_four_hundred_submitted_attempts_all_become_ready_through_llm_batch` takes about 30 s and is marked `long`; the AC asks for it.
  - Each other api test in `test_notices.py` takes about 1.4–2.4 s, from the shared `adapted_session`/`locked_with` fixture.
  - The new live Playwright test is under 10 s.

**Residual risks.**
- See the follow-up risk.
- The 24 hours stays a target until it is measured against the real provider's rate limit.
- The failed notice is once per Class session for good, so a failure after a resume tells no one again (the AC's rule).
- A Student whose attempt has no row yet gets no live event on a stop (they read it on their next load).
- All new Norwegian copy is [ASSUMPTION] draft: the two mails and the Hjem line.

**Personal data.**
- New column with a `user_id`: `assessment_switches.stopped_by` (the acting Admin; FK `users` ON DELETE SET NULL).
- No new table, and no new text a User wrote.
- `notices` rows of kinds `assessment_ready` and `assessment_failed` hold ids only.
