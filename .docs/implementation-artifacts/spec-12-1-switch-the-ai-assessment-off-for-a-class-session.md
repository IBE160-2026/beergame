---
title: 'Story 12.1: Switch the AI assessment off for a Class session'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: 'e9817a0c7fda28852d5beca4cd16ad38666d7ac7'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-12-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** A Lecturer cannot switch off the AI assessment of the Individual test for a Class session, so an Institution's data protection officer has no way to keep test answers away from the LLM while computed scores and Student reports still exist (FR-61, UX-DR49).

**Approach:** A new `modules/assessment` owns a per-Class-session switch (`assessment_switches`, on by default, row absent = on). «Lagre Klasseøkt» stores it through `assessment.service`; a minimal `sessions.lock_test` (the Epic 11 seam, run by a new sweep due action at the original Test deadline) pins it once and idempotently, after which the API refuses a change with 409 `ai_assessment_pinned`. The Klasseøkt gets a «KI-vurdering» block with the Bryter; a gate `assessment.service.assessment_due` is the one question Story 12.2 asks before any assessment.

## Boundaries & Constraints

**Always:** Bryter «KI-vurdering» with a text label and state word («På»/«Av»), help text «Flervalg og interaktive oppgaver rettes fortsatt automatisk. Studentrapporten finnes som vanlig.»; Assistant lecturers read but never change (authz actions `ai_assessment.read`/`ai_assessment.change`, the latter owner only); a save emits `session:<id>`; `lock_test` runs in one transaction per session with ids only, sets `class_sessions.test_locked_at` once, pins the switch in the same transaction and emits `session:<id>`; a DB trigger refuses changing `enabled` once `pinned_at` is set; `copy_from` copies the switch value (FEATURE_RERUN on, Story 5.18 built); new copy in `nb.ts` marked `[ASSUMPTION]` where drafted; migration numbered 0120.

**Never:** No assessment job, no `ai_assessments` table, no LLM call, no Student view (Story 12.2); no Scoring guide pin (Epic 11 adds it to `lock_test`); no import of `sessions` from `assessment` (sessions → assessment only); no change to the demo Class «class-of-1994»; no edit of `sprint-status.yaml`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Default | New Class session | `ai_assessment.enabled=true`, `open=true`, no row stored | — |
| Owner switches off | PUT with `ai_assessment:false` before the Test deadline (also after the Start-date lock) | stored, `session:<id>` emitted, read gives `enabled=false` | — |
| Unchanged resend | PUT with the stored value after pin | saves the rest, no refusal | — |
| Change after deadline | PUT with a changed value once pinned, or once `test_deadline <= now` (sweep not yet run) | nothing saved | 409 `ai_assessment_pinned`, `fields={"ai_assessment":"pinned"}` |
| Assistant | GET as Assistant lecturer | value readable, `can_change=false`; PUT | 403 `forbidden` |
| Sweep at deadline | `test_deadline <= now`, `test_locked_at` NULL | `lock_test` sets `test_locked_at`, pins the stored value; second run changes nothing | a failing item is logged; next minute retries |
| No Test deadline | `test_deadline` NULL | never due; switch stays open | — |
| Copy | `copy_from` of a source with the switch off | the copy has `enabled=false`, not pinned | flag off: 422 `feature_disabled` as before |
| Gate | `assessment_due(id)` | True only when pinned and on | — |

</intent-contract>

## Code Map

- `backend/app/modules/sessions/service.py` -- `save_session` (~927): add `ai_assessment: bool | None`, judge after the `locked` block, call `assessment.set_switch` inside the same transaction; `get_session` (~818): add `ai_assessment` out; `copy_from` (~4814): copy the value; add `lock_test`, `due_test_locks`, `lock_test_due`, `AiAssessmentPinned(_FieldsError)` (pattern: `SessionLocked` ~237, `due_locks`/`lock_due` ~3704).
- `backend/app/modules/sessions/{schemas,routes,repo,models,dev}.py` -- `ClassSessionSaveIn.ai_assessment` (~390), `ClassSessionOut.ai_assessment: AiAssessmentOut`; route maps `AiAssessmentPinned` to 409 (~478); repo `due_test_locks`, `set_test_locked`; models column `test_locked_at`; dev route `POST /api/dev/class-sessions/{id}/lock-test`.
- `backend/app/modules/assessment/{__init__,models,service}.py`, `README.md` -- new module: `assessment_switches` table, `switch_of`, `set_switch`, `pin_switch`, `copy_switch`, `assessment_due`.
- `backend/migrations/versions/0120_ai_assessment_switch.py`, `backend/migrations/env.py` -- table, trigger, `class_sessions.test_locked_at`; register models.
- `backend/app/modules/ops/sweep.py` -- `DueAction("sessions.lock_test", …)` after `games.close_at_test_deadline`.
- `backend/app/platform/authz.py` -- `ai_assessment.read`/`ai_assessment.change` in `POLICIES` and `CLASS_STAFF_ROLES`.
- `backend/app/platform/events/registry.py` -- `"sessions.lock_test": {"session"}`.
- `backend/tests/test_migrations.py` -- HEAD 0120, table set, downgrade check; `backend/tests/test_imports.py` -- assessment imports no feature module.
- `frontend/src/modules/assessment/switch-block.tsx` (new), `frontend/src/modules/sessions/class-session-page.tsx` (~418–429 placement, save body, SaveRow labels), `frontend/src/copy/nb.ts` (`assessment` copy, `sessions.lock`), `frontend/src/lib/api/schema.ts` via `npm run api:generate`.
- Reuse: `frontend/src/components/switch.tsx` (Bryter), the `debrief_ai_text` block (~594) as the pattern; e2e helpers `frontend/e2e/support/{auth,classes}.ts`.

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0120_ai_assessment_switch.py` -- create table + immutability trigger + column -- storage and DB guard.
- `backend/app/modules/assessment/*` -- module, service API above -- ownership (AD-2).
- `backend/app/modules/sessions/*`, `ops/sweep.py`, `platform/authz.py`, `platform/events/registry.py` -- save, read, lock_test, copy, dev route -- AC 1–6.
- `backend/tests/assessment/test_switch.py` -- api tests: default, save + event, Assistant read/403, pinned 409 and deadline-passed 409, unchanged resend, sweep pins once (idempotent, `session` topic), copy, gate, DB trigger; plus migrations/imports updates.
- `frontend/src/modules/assessment/switch-block.tsx`, `class-session-page.tsx`, `nb.ts` -- block (editable / read-only / pinned line), body field, save row at the bottom while the switch is open after the Start-date lock.
- `frontend/e2e/ai-assessment-switch.spec.ts` -- on, off, locked at 320/360/1440 with axe; Assistant read-only.

**Acceptance Criteria:**
- Given a Lecturer opens the Klasseøkt before the Test deadline, when it loads, then «KI-vurdering» shows the Bryter on with the help text.
- Given the Lecturer switches it and presses «Lagre Klasseøkt», when the save succeeds, then the value is stored via `assessment.service` and `session:<id>` is emitted.
- Given the original Test deadline passes, when the sweep's `sessions.lock_test` runs, then the value is pinned once and idempotently, the block is read-only and a changed value answers 409 `ai_assessment_pinned`.
- Given the pinned switch is off, when Story 12.2 asks `assessment_due`, then it is False (no assessment, no LLM call); proved by a test of the gate.
- Given an Assistant lecturer, when they open the block, then they read the value as text and cannot change it (authz policy).
- Given FEATURE_RERUN on, when a Class session is copied, then the switch value is copied.

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
Layers: blind hunter and edge-case hunter (sonnet, per the runbook's two-reviewer rule); verification-gap and intent-alignment skipped.
- verdicts: 19 findings — high 0, medium 3, low 10, false 6, maybe-false 0
- findings:
  - `[low]` `[reject]` Blind: sessions past their Testfrist at deploy are pinned on by the first sweep, in a burst, unbounded — on is the default those sessions already had, the class_sessions table is small, and a late pin now stamps the deadline (next row); a backfill or batching adds a migration branch for no user-visible harm.
  - `[medium]` `[patch]` Blind: `pinned_at` is the sweep time but the copy says «Låst ved testfristen {when}» — `lock_test` now pins as of `min(now, test_deadline)`; the api test runs the sweep five minutes late and asserts the pin at the deadline.
  - `[medium]` `[patch]` Blind: the draft seeded once and always sent can revert another owner's change — the draft is now null until touched, sent only then, reset to null after a save.
  - `[low]` `[patch]` Blind: `ai_assessment.read` declared but never enforced — removed; staff read the switch with `class_sessions.read`, the owners-only `ai_assessment.change` stays (README updated).
  - `[low]` `[reject]` Blind: a session with no Testfrist is never pinned while the copy promises a lock — once the Start-date lock has run a Testfrist cannot be cleared (`required`), and the copy says it locks at the Testfrist; no wrong behaviour.
  - `[low]` `[reject]` Blind: the `llm_call` count assertion is vacuous and the sweep test only checks order — the gate test is the proof the AC asks for; running the whole sweep adds slow cross-module setup.
  - `[low]` `[reject]` Blind: the Assistant e2e fakes the answer and `unrouteAll` is not in `finally` — the real 403 and read are pinned by the api test; the overlay is the repo's pattern for Assistant screens.
  - `[low]` `[patch]` Blind: the trigger docs claim more than it guards — docstring and README now say it refuses any update, not a delete (a delete guard would break the Class session cascade).
  - `[false]` `[reject]` Blind: `test_locked_at` and `pinned_at` can diverge — both are written in one transaction under the row lock by their only writer, `lock_test`.
  - `[low]` `[patch]` Blind: the comma in «…passert, og KI-vurdering blir lagret.» — now «…passert, og KI-vurdering, blir lagret.», as the existing «og Labtimer,» line.
  - `[false]` `[reject]` Blind: the read-only «På»/«Av» has no label — it sits under the block's h2 in a labelled section, the same pattern as the Debrief AI text and Obligatorisk read-only states.
  - `[low]` `[reject]` Blind: no partial index for `due_test_locks` — the table holds a few hundred rows; an index is a migration for no measurable gain.
  - `[false]` `[reject]` Blind: the required `ai_assessment` on `ClassSessionOut` may be missed by a builder — `get_session` is the only constructor; `tsc` passes over every fixture.
  - `[low]` `[reject]` Edge: historic sessions pinned in a burst (same root as the first row) — same reason.
  - `[medium]` `[patch]` Edge: stale draft after a refetch reverts another owner's change (same root as the draft row) — same fix.
  - `[low]` `[patch]` Edge: after a 409 `ai_assessment_pinned` the switch stays editable and every save repeats the 409 — the catch now clears the draft and refetches the session, so the block turns read-only.
  - `[false]` `[reject]` Edge: `lock_test` pins with a null or future deadline — only the sweep (whose finder judges the deadline) and the local dev route call it; documented in its docstring.
  - `[false]` `[reject]` Edge: a non-owner passing `class_sessions.manage` gets the not-found path — both actions hold the same roles today, and the route answers 403 `forbidden`, one answer for everything not reachable (FR-5), as the api test asserts.
  - `[false]` `[reject]` Edge: `get_session` reads its own clock after the save — the read reports the state at read time, which is what the screen needs; the accepted change stays stored.

## Design Notes

- Epic 11's `lock_test` does not exist yet: this story adds the minimal one (`test_locked_at`, sweep action, pin of the switch). Epic 11 extends the same function with the Scoring guide pin and the `close_attempt` sweep after it.
- After the Start-date lock the switch stays open until the Test deadline, so the locked save row («Lagre frister», under Datoer) becomes «Lagre Klasseøkt» at the bottom while the switch can change, with the hint «Bare frister som ikke er passert, og KI-vurdering blir lagret.» — the only save of the page then saves both.
- `assessment_due` is False until pinned: nothing is assessed before the Test deadline (AD-9).

## Verification

**Commands:**
- `uv run pytest tests/assessment tests/sessions tests/test_migrations.py tests/test_imports.py tests/platform` -- pass
- `npm run typecheck && npm run test && npm run lint:colours && npm run check:copy && npm run build` -- pass
- `npx playwright test e2e/ai-assessment-switch.spec.ts e2e/class-session-lock.spec.ts --workers=4` -- pass

## Auto Run Result

Status: done

**Summary.** A new `modules/assessment` owns the «KI-vurdering» switch per Class session (`assessment_switches`, migration 0120, no row = on). «Lagre Klasseøkt» takes `ai_assessment` and stores it through `assessment.set_switch` in the save's transaction (emits `session:<id>`), also after the Start-date lock, until the original Test deadline; then 409 `ai_assessment_pinned`. A minimal `sessions.lock_test` (the Epic 11 seam: `class_sessions.test_locked_at`, sweep due action `sessions.lock_test`, dev route `POST /api/dev/class-sessions/{id}/lock-test`) pins the switch once, as of the Test deadline; a trigger refuses updates of a pinned row. Owners only change it (`ai_assessment.change`); Assistant lecturers read it. «Lag kopi» copies the value. `assessment.assessment_due` is the gate Story 12.2 must ask (True only when pinned and on). The Klasseøkt has a «KI-vurdering» block with the Bryter, help text and an open / pinned / deadline-passed line; after the Start-date lock, while the switch can change, the one save is «Lagre Klasseøkt» at the bottom (hint names the deadlines and KI-vurdering).

**Files.**
- `backend/app/modules/assessment/{__init__,models,service}.py`, `README.md` — new module: table, switch API, gate.
- `backend/migrations/versions/0120_ai_assessment_switch.py`, `backend/migrations/env.py` — table, trigger, `test_locked_at`.
- `backend/app/modules/sessions/{service,schemas,routes,repo,models,dev}.py`, `README.md` — save, read, `lock_test`, finder, copy, dev route.
- `backend/app/modules/ops/sweep.py` — due action `sessions.lock_test`.
- `backend/app/platform/authz.py`, `backend/app/platform/events/registry.py` — `ai_assessment.change`, `sessions.lock_test` topics.
- `backend/tests/sessions/test_ai_assessment_switch.py` (new), `tests/test_migrations.py`, `tests/test_imports.py`, `tests/test_authz_rules.py`.
- `frontend/src/modules/assessment/switch-block.tsx` (new), `frontend/src/modules/sessions/{class-session-page.tsx,api.ts}`, `frontend/src/copy/nb.ts`, `frontend/src/lib/api/{openapi.json,schema.ts}` (generated).
- `frontend/e2e/ai-assessment-switch.spec.ts` (new); `class-session-lock`, `class-session-dates`, `class-session-obligatory` specs follow the new save and switch.

**Review.** 19 findings (two sonnet reviewers: blind, edge case). Patched: pin as of the Test deadline (medium), touched-only draft so a save never reverts another owner's value (medium, two rows), 409 refetch (low), unused `ai_assessment.read` removed (low), trigger docs (low), comma in the save hint (low). Rejected: 7 low and 6 false, each with its reason in the triage log. Nothing deferred.

**Follow-up review: recommended.** Two medium entries were patched (counts: high 0, medium 2, low 4). Unverified risk: the touched-only draft and the 409 refetch on the Klasseøkt have no e2e test of two owners editing at once or of the Testfrist passing while the page is open.

**Verification.** Backend: full suite with `--maxprocesses=8` 3170 passed, 4 skipped, 1 failed (`test_authz_rules`: the new dev route was not on the public list), fixed and re-run green; `ruff check` and `ruff format --check` clean. Frontend: `tsc` clean, Vitest 1044 passed, `lint:colours` and `check:copy` pass, `next build` ok. Playwright on the lane-2 stack (8081): the new spec (on, off, locked at 320/360/1440 with axe, 44 px target), `class-session-*` specs, `debrief-narration`, `debrief-quiz-exclusions`, `test-game`, `homes`, `order-confirm`, `order-field`, `guided-week`, `week-table`, `game-start`: 186 passed before the review patches; after them the new spec and the class-session lock, dates, obligatory and base specs: 48 passed. No new test call over 1 s (the slowest is 0.73 s).

**Residual risks.** Epic 11 must extend `sessions.lock_test` (Scoring guide pin, `close_attempt` after it) rather than add a second one, and Story 12.2 must call `assessment.assessment_due` before it creates an assessment; the «no LLM call when off» AC is proved here at that gate only, since no attempt or assessment exists yet. Sessions whose Testfrist passed before deploy are pinned on at the first sweep, as of their deadline. All new copy except the title and help text is [ASSUMPTION] draft copy.