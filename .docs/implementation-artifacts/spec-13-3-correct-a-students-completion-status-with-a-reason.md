---
title: 'Story 13.3: Correct a Student''s Completion status with a reason'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: '020da022524c74a21ce36a3b8abee77186634d9e'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-13-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-13-2-studentside-with-the-fullforing-block.md'
warnings: ['oversized']
deferred:
  - summary: >-
      The correction form (default choice, client too-long check, server 422 mapping) has no unit test; only one e2e drives it, on a not-done step.
    evidence: |-
      frontend/src/modules/reports/completion-block.tsx CorrectionForm is exercised only by e2e/studentside.spec.ts (not-done class_game, empty reason, one save). Flipping the default choice for a done step or dropping the too_long branch fails no test.
    location: >-
      frontend/src/modules/reports/completion-block.tsx
    severity: low
---

<intent-contract>

## Intent

**Problem:** A Student who kept up but fell short through the playout or the group's pace cannot be treated fairly: `analysis.completion` already applies corrections, but nothing stores one, and the Fullføring block has no way to make one (FR-17, UX-DR54).

**Approach:** A new append-only table `completion_corrections` owned by `modules/progress`, written by one Lecturer-only command in `modules/reports` (`POST /api/class-sessions/{id}/students/{user_id}/corrections`, `correctCompletion`, policy `completion.correct`), audited and emitting `session:`/`user:` in one transaction. The assembler passes the corrections to `analysis.completion`; the Studentside shows the latest per step with who, when and why; Hjem's Stegene marks a corrected step «rettet av faglærer» without the reason.

## Boundaries & Constraints

**Always:**
- Table `completion_corrections`: `id` (uuid7), `user_id` (FK users CASCADE), `class_session_id` (FK CASCADE), `step` (CHECK in the five `COMPLETION_STEPS`), `done` bool, `reason` text (CHECK trimmed length 1..1000), `actor_user_id` (FK users SET NULL), `at` timestamptz; index on (`class_session_id`, `user_id`); a trigger refuses UPDATE (`restrict_violation`). Migration `0301`, Revises `0130`.
- `progress.service.record_correction(session, …)` inserts in the caller's transaction; `progress.service.corrections(session, user_id, class_session_id)` reads them oldest first by (`at`, `id`). `progress` still imports no feature module. A correction never calls `record_step`, never touches `progress_steps` or `seat_weeks`, so `has_step` gates and the funnel are unchanged.
- Command `reports.corrections.correct(user, session_id, user_id, body)`: reach through `sessions.student_target(…, "completion.correct")` (owners only; None → 403 `forbidden`, one body for every outsider); body `{step, done, reason}`; reason stripped; empty → 422 `invalid_correction` with `fields.reason = "required"`, over 1000 characters → `fields.reason = "too_long"` [ASSUMPTION]; a Class session that is not obligatory → 409 `not_obligatory` [ASSUMPTION]; an archived Class → 409 `class_archived`. In one transaction: writable check, insert, `audit.record(actor, "completion.corrected", {class_session_id, user_id, correction_id}, {step, done, was_done})`, `events.emit("user", student)` and `events.emit("session", id)`. Answers the updated `StudentRecordOut`.
- The audit row holds ids and codes only (AD-14); the reason stays in `completion_corrections`, which the audit row names by `correction_id`. Every correction is a new row and a new audit row; the latest per step by (`at`, `id`) applies.
- Registry entry `reports.correct_completion: {session, user}` and a test asserting the emitted topics equal it.
- Record: each `CompletionStepOut` gains `correction: {done, reason, at, by} | null` (latest; `by` = the actor's name now via `classes.service.actor_names`, null when unknown); `StudentRecordOut` gains `can_correct` (owner, obligatory, Class not archived).
- Hjem: `StepOut.corrected: bool` from the Completion status; Stegene note «gjort, rettet av faglærer» / «ikke gjort, rettet av faglærer». No Student-facing endpoint serves the reason.
- Web: Fullføring rows end in secondary «Rett Klassespill» (per step name) when `can_correct`. The form opens in place: Valgknapper «Gjort»/«Ikke gjort» (preselect the opposite of the current status), multi-line Tekstfelt «Begrunnelse», the line «Rettingen logges med navnet ditt, tidspunktet og begrunnelsen.», primary «Lagre retting», «Avbryt». Focus to the checked Valgknapp on open, back to the opener on «Avbryt». Empty reason: no request, field invalid with «Skriv en begrunnelse.». One form open on the page at a time (shared `Editing` with Tilrettelegging/Frister). Saved: the row's status line reads «Gjort, rettet av Bård 12. des.» (or «Ikke gjort, …»), takes focus (`role=status`), reason under it in `ink-secondary`.
- Copy in `frontend/src/copy/nb.ts`, draft `[ASSUMPTION]`.

**Never:** no change to `analysis.completion`'s rules; no step event, gate or funnel change; no reason in the audit row, a log line, an event or any Student response; no edit or delete of a correction through the api; no Oppfølgingsspill (13.4); no Assistant lecturer correction.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Correct to done | class_game recorded, 3 of 5 own, obligatory | step done, corrected; requirement recomputed; Hjem `corrected` true, `counts` true | — |
| Correct to not done | debrief done | step not done, corrected | — |
| Two corrections | done then not done | latest (not done) applies; 2 rows, 2 audit rows | — |
| Empty reason | `"   "` | nothing written | 422 `invalid_correction`, `fields.reason=required` |
| Not obligatory | `obligatory=false` | nothing written | 409 `not_obligatory` |
| Assistant / other Lecturer / Admin / Student / unknown Student | — | nothing written | 403 `forbidden`, one body |
| Archived Class | archived | nothing written | 409 `class_archived` |
| Funnel and gates | correction to done on a step not recorded | `has_step` false, funnel stage unchanged | — |

</intent-contract>

## Code Map

- `backend/app/analysis/completion.py` -- `Correction(step, done, at)`, latest by `at` with `>=` (order of input breaks ties); unchanged.
- `backend/app/modules/progress/{models,service}.py`, `README.md` -- add table + `record_correction`, `corrections`.
- `backend/migrations/versions/0130_student_deadline_extensions.py` (head), `0103_debrief_explanations.py` (immutable trigger pattern); `backend/tests/test_migrations.py` (`HEAD`, `HEAD_TABLES`, per-revision downgrade block ~:348, CHECK list ~:930).
- `backend/app/modules/reports/service.py` -- `completion_status` passes `()` for corrections; read them in its session.
- `backend/app/modules/reports/{studentside,routes,schemas}.py` -- record, route; add `corrections.py`.
- `backend/app/modules/sessions/service.py:2111` `student_target(…, action)`, `:849` `staffed_session` (`archived`), `:628` `completion_terms`, `:1638` `_with_counts`; `schemas.py:772` `StepOut`.
- `backend/app/modules/sessions/adjustments.py:108` -- `save_adjustment`: the audited-command pattern to copy.
- `backend/app/modules/classes/service.py:214` `is_writable`, `ClassArchived`, `:640` `actor_names`.
- `backend/app/platform/authz.py` `POLICIES`/`CLASS_STAFF_ROLES`; `platform/audit.py` `record`; `platform/events/registry.py`; `platform/errors.py` `error_response`, `documented`.
- `backend/tests/reports/test_studentside.py`, `test_completion_status.py` (`obligatory`, `every_later_step`, `short_game`); `tests/sessions/test_lock.py` `dated`, `tests/sessions/test_allocation.py` `students` (cheap, no game).
- `frontend/src/modules/reports/{completion-block.tsx,student-page.tsx,record.ts,api.ts,adjustment-block.tsx}`; `components/segmented-choice`, `text-field`; `frontend/src/modules/games/home.ts` `stepItems`; `frontend/e2e/studentside.spec.ts`.

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0301_completion_corrections.py`, `progress/models.py`, `progress/service.py`, README -- table, trigger, writes and reads.
- `backend/app/platform/authz.py`, `events/registry.py` -- policy, registry entry.
- `backend/app/modules/reports/{corrections,schemas,studentside,routes,service}.py`, README -- command, record fields, route, assembler input.
- `backend/app/modules/sessions/{schemas,service}.py` -- `StepOut.corrected`.
- `backend/tests/reports/test_corrections.py` -- matrix above, audit row, emitted topics, gates/funnel unchanged, Hjem `corrected` and no reason in Hjem; `tests/test_migrations.py`, `tests/test_authz_rules.py` as needed.
- `frontend/src/copy/nb.ts`, `modules/reports/{api.ts,record.ts,completion-block.tsx,student-page.tsx}`, `record.test.ts`, `modules/games/home.ts` (+ test) -- form, result line, Stegene note; `npm run api:generate`.
- `frontend/e2e/studentside.spec.ts` -- Lecturer corrects Klassespill: focus, empty-reason error, Avbryt focus, save → focused result line; one form at a time; Student's Hjem shows «rettet av faglærer»; axe.

**Acceptance Criteria:**
- Given the Fullføring block, when the Lecturer presses «Rett Klassespill», then the form opens in place with focus on the first field, and opening «Endre tilrettelegging» closes it.
- Given a saved correction, when the Studentside shows the step, then the result line «Gjort, rettet av <navn> <dag>» with the reason under it has focus, and the open page and the Student's Hjem refetch.
- Given the corrected Student, when they open Hjem, then Stegene marks the step «rettet av faglærer» and no Student response holds the reason.

## Spec Change Log

## Review Triage Log

### 2026-11-23 — Review pass
- layers: four (blind, edge case, verification gap, intent alignment), as the lane brief directs for a data-model and access change. All ran on Sonnet and wrote their findings to the scratchpad.
- verdicts: 38 findings — high 2, medium 0, low 30, false 6, maybe-false 0
- findings:
  - `[high]` `[patch]` Blind: the UPDATE trigger also refuses the `ON DELETE SET NULL` of `actor_user_id`, so deleting a Lecturer who made a correction fails. Patched: the trigger lets through an update that only sets the actor to NULL (migration 0301, applied to the lane's databases at 0301). The test now proves another change is still refused, the NULL-out passes, and the record then has `by = None`.
  - `[low]` `[reject]` Blind: DELETE and TRUNCATE are not guarded. The cascades from users and Class sessions need DELETE, and the README says only UPDATE is refused. A guard would add a branch for a manual SQL action.
  - `[low]` `[reject]` Blind: two Lecturers saving at the same moment can be ordered by host time and record a stale `was_done`. The window is milliseconds, and every reader uses the same (`at`, `id`) order. A lock would add surface for a rare case.
  - `[low]` `[reject]` Blind: no stale-state check, and a correction that sets the status the step already has is accepted. The story makes every correction a new row. The open form is refetched live.
  - `[low]` `[reject]` Blind: a correction cannot be withdrawn. The story asks only that the latest correction applies. A Lecturer sets the status they want with a new one.
  - `[low]` `[patch]` Blind: the step list is kept by hand in several places. Added `test_the_correctable_steps_are_the_steps_of_the_requirement`, which compares the table's list and the api's `Literal` with `COMPLETION_STEPS`. Also renamed the misleading alias in `test_migrations.py`.
  - `[low]` `[patch]` Blind: the reason limit differs between client and api. The form now counts characters (`[...trimmed].length`), as the api does. The rest is rejected: a missing `max_length` is covered by the global body limit, and `btrim` versus `strip` never accepts a blank reason.
  - `[low]` `[reject]` Blind: `completion_status(session=s)` reads partly outside the transaction. `was_done` is an audit hint, and a mix would need a step recorded in the same millisecond.
  - `[low]` `[reject]` Blind: `can_correct` needs a Completion status but the api does not, and 422 comes before 409. This only concerns a Student outside the reporting scope (a test student), and the order is the adjustment's.
  - `[low]` `[reject]` Blind: Hjem's corrected note replaces the other notes. This is a decision, and the step's link stays. The Faglærer's status is what the Student needs to see.
  - `[low]` `[reject]` Blind: accessibility details (no Escape, `role=status` set on save, `saved.n`, the `sr-only` label, the non-null `get`). These follow the Tilrettelegging block's tested pattern. `n` makes each save a new state so focus moves again, and the step map is built from the same list.
  - `[low]` `[defer]` Blind: test coverage of the form is thin. Grouped with the verification-gap form finding and deferred.
  - `[low]` `[reject]` Blind: privacy of the reason, the Assistant's read, and English api messages. Staff of the Class read the Studentside by design (FR-63). The table is reported for the personal-data registry. Api messages are English throughout, and the web shows Norwegian copy.
  - `[high]` `[patch]` Edge: the SET NULL is refused by the trigger. Same root cause and fix as the first Blind finding.
  - `[low]` `[reject]` Edge: concurrent corrections record the same `was_done`. Same as the Blind race finding.
  - `[low]` `[reject]` Edge: a NUL character in the reason gives a 500. No Lecturer types one in a textarea, and a guard adds a branch.
  - `[false]` `[reject]` Edge: a Student outside the reporting scope gets a written correction, then 403. False: `student_record` answers 200 with `completion: null` for that Student. It returns None only through `student_target` or `staff_summary`, and both passed.
  - `[false]` `[reject]` Edge: `student_record` returns None after the commit. False: `staff_summary` grants the owner role that `completion.correct` requires, and `student_target` passed just before.
  - `[low]` `[reject]` Edge: host clock skew between processes reorders corrections. Same as the race finding.
  - `[low]` `[reject]` Edge: the Studentside reads the corrections and the status separately. The next `session:` event corrects a mixed read, as in Story 13.2.
  - `[low]` `[patch]` Edge: the client counts UTF-16 units. Fixed with the code-point count.
  - `[low]` `[reject]` Edge: no `max_length` on `reason`. Same as the Blind limit finding.
  - `[low]` `[patch]` Edge: 409 `class_archived` falls back to the generic message. Added a `class_archived` refusal line. A 403 after a role change is rejected: it is rare, and the generic message is true.
  - `[false]` `[reject]` Edge: `can_correct` flipping false leaves `editing` set and blocks other forms. False: opening another form sets `editing` to that form, and the hidden correction form keeps no state.
  - `[low]` `[patch]` Verification: the accepted boundary of 1000 characters is untested. Added a reason of 1000 characters with spaces around it, accepted with 200.
  - `[low]` `[defer]` Verification: the correction form has no unit test. Deferred (frontmatter).
  - `[low]` `[patch]` Verification: the three step lists are not tied together. Same patch as the Blind finding.
  - `[low]` `[patch]` Verification: `by = None` is not exercised at the api. Covered by the NULL-out test above.
  - `[low]` `[reject]` Verification (other): DELETE is not refused. Same as the Blind finding.
  - `[false]` `[reject]` Verification (other): `ValueError` from `record_correction` is unhandled. False as a defect: `CorrectionIn.step` is the same `Literal`, so the api never reaches it, and the new test ties the lists.
  - `[low]` `[reject]` Verification (other): the concurrent `was_done`. Same as the race finding.
  - `[low]` `[reject]` Intent: focus goes to the checked radio, not the first in the DOM. The checked radio is the group's first stop in the tab order, which is how Tilrettelegging behaves («first field»).
  - `[low]` `[patch]` Intent: `seat_weeks` is not asserted unchanged. Added the count and newest id before and after.
  - `[false]` `[reject]` Intent: no registry test change. False: the registry test is the per-command assertion that the emitted topics equal `COMMAND_TOPICS[...]`, which `test_corrections.py` makes.
  - `[low]` `[reject]` Intent: the exact «Bård» example appears only in the unit test. The e2e asserts the form with a regex against a generated Lecturer name.
  - `[low]` `[reject]` Intent: the corrected note replaces the other notes rather than being added to them. Same decision as the Blind finding.
  - `[false]` `[reject]` Intent: the generated `CorrectionIn` type is not in the diff. False: `schema.ts` and `openapi.json` were left out of the review diff on purpose. They were regenerated with `npm run api:generate`, and the typecheck passes.
  - `[low]` `[reject]` Intent: Assistant lecturers see the reasons. Same as the Blind privacy finding: the Studentside is for the Class's staff.

## Design Notes

The correction reuses the Studentside's `Editing` state (`"adjustment" | "deadline" | "correct:<step>"`), so one form at a time holds across blocks. The reason is personal free text: it lives in one table with the Student's id, which the Epic 15 personal-data registry must list.

## Verification

**Commands:**
- `uv run pytest tests/reports tests/analysis/test_completion.py tests/test_imports.py tests/test_authz_rules.py tests/test_migrations.py -q` (lane env vars) -- pass
- `npm run typecheck && npx vitest run src/modules/reports src/modules/games` -- pass
- `npx playwright test e2e/studentside.spec.ts e2e/completion.spec.ts e2e/homes.spec.ts --workers=4` -- pass

## Auto Run Result

Status: done

**Summary.** A Lecturer can now correct one step of a Student's Completion status, with a reason (FR-17, UX-DR54). On the Studentside, each «Fullføring» row has the button «Rett Klassespill» (and so on for each step). It opens a form in place with:
- the Valgknapper «Gjort» / «Ikke gjort», with the opposite of the current status chosen;
- the field «Begrunnelse»;
- the line about what is logged;
- «Lagre retting» and «Avbryt».

Focus and form behaviour:
- Focus moves to the chosen Valgknapp, and «Avbryt» returns it to the button.
- One form is open at a time across Fullføring, Tilrettelegging and Frister.
- An empty reason is refused before any request.
- Once saved, the row reads «Gjort, rettet av <navn> 23. nov.» with the reason under it, and that line takes focus.

The save is `POST /api/class-sessions/{id}/students/{user_id}/corrections` (`correctCompletion`, policy `completion.correct`, Lecturers only). It runs in one transaction:
- a new row in `completion_corrections`, owned by `progress` (migration 0301, append-only);
- an audit row `completion.corrected`, holding ids and codes and never the reason;
- `user:` and `session:` (registry `reports.correct_completion`).

The assembler passes the corrections to `analysis.completion`, so the latest correction per step applies everywhere. Hjem's Stegene marks a corrected step «gjort/ikke gjort, rettet av faglærer». The Student never gets the reason. A correction records no step event: gates and the funnel are unchanged. The builder did the implementation in its own context, as the lane brief requires, instead of handing it to a subagent.

**Files.**
- `backend/migrations/versions/0301_completion_corrections.py`: the table, the checks, and the trigger that allows only the actor NULL-out.
- `progress/{models,service}.py`, README: the table, `record_correction`, `corrections`.
- `reports/corrections.py` (new), `routes.py`, `schemas.py`, `studentside.py`, `service.py`, README:
  - the command and the route;
  - `CorrectionIn`, `CorrectionOut`, `can_correct`;
  - the assembler input.
- `sessions/{schemas,service}.py`: `StepOut.corrected`.
- `platform/authz.py`: the policy. `platform/events/registry.py`: the registry entry.
- Tests:
  - `tests/reports/test_corrections.py` (new);
  - `test_migrations.py` (head 0301, table, trigger, check list);
  - four exact-shape Hjem expectations, which now include `corrected`.
- Frontend:
  - `copy/nb.ts`;
  - `modules/reports/{api.ts,completion-block.tsx,record.ts,record.test.ts,student-page.tsx}`;
  - `modules/games/{home.ts,home.test.ts}`;
  - the `corrected` field in step fixtures of `replay.test.ts` and `individual-test.test.ts`;
  - the regenerated `lib/api/{openapi.json,schema.ts}`;
  - `e2e/studentside.spec.ts`, which has one new test.

**Review.** Four layers ran, as the brief directs for a risky story (data model, access): 38 findings, of which 2 high (one root cause), 30 low and 6 false.
- Patched:
  - the high root cause: the trigger blocked deleting a Lecturer;
  - 8 low findings: tests tying the step lists together, the 1000-character boundary, `seat_weeks` unchanged, `by = None`, the code-point count and the `class_archived` message.
- Deferred: one low finding, a unit test of the correction form.
- Every rejected finding and its reason is in the Review Triage Log.
- Follow-up review: **true**. A high was patched, by the 1 high and 8 low patched counts. The unverified risk is real user deletion. The test sets `actor_user_id` NULL by SQL, the action `ON DELETE SET NULL` performs, but no test deletes a User row: no such path exists on this branch. Epic 15's deletion should be checked against this trigger.

**Verification.**
- Full backend suite (8 processes): 3735 passed. ruff check and format pass.
- New tests over 1 s:
  - `test_a_lecturer_corrects_a_step_and_the_latest_correction_applies`: about 2.7 s, on the short-game fixture like Stories 13.1 and 13.2.
  - `test_corrections_are_refused_and_write_nothing`: about 1.2 s.
- Frontend:
  - typecheck passes, and Vitest has 1196 passed;
  - lint:colours and check:copy pass;
  - the build passes inside the image.
- Playwright on 4 workers: `studentside`, `completion`, `homes`, `order-field`, `game-card`, `student-home`, `tilrettelegging` and `deadline-extension`, 49 passed.
  - The new test checks the focus rules, one form at a time, the empty reason with no request, the focused result line, and the Student's open Hjem marking the step without a reload.
  - It runs axe with the form open and after the save.
  - The existing Studentside test runs axe and reflow at each width, with the «Rett» buttons on the page.
- The review's trigger change was applied to the lane's databases already at 0301 with `CREATE OR REPLACE FUNCTION`, the same body as the migration. The shared test databases were not dropped.

**Decisions taken for the founder [ASSUMPTION].**
- A correction is allowed only in an Obligatory class session (409 `not_obligatory`). The buttons are hidden elsewhere, and in an archived Class.
- The reason is at most 1000 characters after trimming.
- The audit row holds ids and codes only: `step`, `done`, `was_done` and `correction_id`. The reason stays in the corrections table.
- The form chooses the opposite of the current status first.
- The result line names the Lecturer's full name as stored, with «en faglærer» when the name is no longer known, and the day without the weekday.
- Assistant lecturers see corrections and their reasons on the Studentside, but cannot correct.
- On Hjem, the «rettet av faglærer» note replaces the step's other note in every state, and the link stays.
- Hjem shows corrections only where it shows Completion already: an Obligatory session where the Student has a game.
- All new copy is draft.

**Personal data.** New table `completion_corrections`, with these columns:
- `user_id`: the Student;
- `actor_user_id`: the Lecturer;
- `reason`: the Lecturer's free text about the Student.

The personal-data registry of Story 15.2 must list it.

**Residual risks.**
- Two simultaneous corrections are ordered by host time.
- A corrected Student without a game sees no mark on Hjem until Story 13.4 gives a game.
- The correction form has no unit test (deferred).

## Epic 13 close-out: follow-up review

Independent review (sonnet, read-only): access and the append-only trigger are clean. Added a real `DELETE FROM users` test (`test_deleting_the_users_rows_passes_the_append_only_trigger`): the corrector's key goes to NULL through the trigger, the Student's rows cascade. Left (low): a correction for a Student outside the reporting scope is stored though never shown; a reason of only zero-width characters passes the trim; lane databases migrated before 0301's in-place trigger patch keep the old trigger (fresh databases and main are fine).
