---
title: 'Story 12.5: Flag feedback, and read assessments as staff'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: '8fd86475b8bd8a8e8a34c4328a31b314101d2971'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-12-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-12-4-be-told-when-the-ai-assessment-is-ready.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** A Student who thinks a piece of AI feedback is wrong has no way to say so, and no Lecturer or Assistant lecturer can read a Student's AI assessment at all: `ai_assessments.read` grants no role, the Studentside is closed to Assistant lecturers, and the Klasseøkt shows nothing about the Students' assessments (FR-55, FR-5, AD-12, UX-DR39, UX-DR66).

**Approach:** A `ai_feedback_flags` row per flagged item (owned by `assessment`), set and cleared by the Student with `PUT`/`DELETE …/test/assessment/items/{item_id}/flag`. The Student's view gets `flagged` per AI item. A staff read of the same view (`GET /api/class-sessions/{id}/students/{user_id}/assessment`, policy `ai_assessments.read` for the Class's owners and Assistant lecturers) feeds a «KI-vurdering» block on the Studentside; the Studentside opens for Assistant lecturers through a new `student_pages.read` policy, with «Tilrettelegging» and «Frister» withheld from them. A per-Student list (`GET /api/class-sessions/{id}/assessments`) on the Klasseøkt's «KI-vurdering» block, built on `assessment.service.summaries_for_session`, which Epic 13 reuses.

## Boundaries & Constraints

**Always:** Only the Student flags, only an item whose written feedback their view shows now (not dropped, not hidden by switch-off or stop). Flag and undo are idempotent, emit `user:<student>` and `session:<id>` (`assessment.set_flag` in the events registry). The staff view is the Student's view under a separate schema (`StaffAssessmentOut`), so a field later added to the Student's own view (12.6's letter opt-in) never reaches staff. Outsiders, Students of the Class, the Admin without a staff role, a non-Student `user_id` and an unknown session get one 403 `forbidden`. The flag control: a text button with `aria-pressed`, no icon, no dialog, 44 px tap target; «Marker som feil» → «Markert. Faglærer ser det.» + «Angre»; failure: inline «Det ble ikke lagret. Prøv igjen.» with the button active. Every staff view starts with «KI-generert, kan ta feil. Teller ikke. Ingen karakter.». New copy in `nb.ts`, drafts marked `[ASSUMPTION]`. Migration 0205 revises 0204. `assessment` imports no new module.

**Never:** No letter (12.6), no Control test reading (12.9), no `reports.scope` exclusion (Epic 13), no audit of a flag (the Student's own toggle), no free-text reason on a flag, no change to the Student's states or scores, no edit of feedback by staff.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Flag | ready, item has feedback | 200 view with `flagged: true`; row stored; `user`+`session` events | repeat PUT: same answer, one row |
| Undo | flagged | 200 view with `flagged: false`; row gone | repeat DELETE: same answer |
| Not flaggable | computed item, dropped feedback, no feedback, unknown item, state not showing items | — | 409 `feedback_not_flaggable` |
| Not own | another Student's / unknown session, staff | — | 403 `forbidden` |
| Staff read | owner or Assistant lecturer, `user_id` a Student of the Class | 200 `StaffAssessmentOut` incl. `flagged`, same items/notes/`checked` as Student | — |
| Staff read refused | other Class's staff, Admin w/o staff role, Student of the Class, non-Student `user_id`, unknown session | — | 403 `forbidden` |
| List | owner or Assistant lecturer | each registered Student by name: `state` (ready, not_ready, incomplete, failed, switched_off, no_test) and `flags` | 403 as staff read |
| Studentside, Assistant | Assistant lecturer of the Class | 200, `can_manage: false`, `adjustment` and `deadlines` null; PUTs stay 403 | — |

</intent-contract>

## Code Map

- `backend/app/platform/authz.py` -- `POLICIES["ai_assessments.read"]` = {LECTURER, ASSISTANT}, new `student_pages.read` same; both in `CLASS_STAFF_ROLES` with {OWNER, ASSISTANT_STAFF}.
- `backend/app/modules/assessment/models.py`, `backend/migrations/versions/0205_feedback_flags.py` (new) -- `ai_feedback_flags(assessment_id, item_id, flagged_at)`, PK both, composite FK to `ai_item_scores` ON DELETE CASCADE.
- `backend/app/modules/assessment/service.py` -- `AssessmentRecord.flags: frozenset[str]` filled in `assessment_of` (~462); new `set_flag(attempt_id, item_id, flagged, now)` (emits events), `AssessmentSummary` + `summaries_for_session(s, class_session_id)` (status, runs, flags per user; for Epic 13).
- `backend/app/modules/tests/assessed.py` -- split `read` (~224) into the access check and `_view(class_session_id, user_id)`; `AiScoreOut.flagged`; new `set_flag(user, cs, item_id, flagged)` (raises `NotFlaggable`), `staff_read(user, cs, student_id)`, `staff_list(user, cs)`.
- `backend/app/modules/tests/schemas.py` -- `AiScoreOut.flagged`, `StaffAssessmentOut`, `AssessmentRowOut`, `AssessmentListOut`.
- `backend/app/modules/tests/routes.py` -- the four routes, near `get_my_assessment` (~284).
- `backend/app/modules/sessions/service.py` -- `student_target(…, action=)` (~2108), `session_students(class_session_id)` (registered Students' names). `sessions/adjustments.py` `student_page` / `_page`: `can_manage`, withheld blocks; `sessions/routes.py` `get_student_page` (~1535) → `student_pages.read`; `StudentPageOut.can_manage`, `deadlines` nullable.
- `backend/app/platform/events/registry.py` -- `assessment.set_flag`: {session, user}.
- Tests: `backend/tests/assessment/test_flags.py` (new, helpers from `test_assess.py`, `test_feedback.py`, `tests/classes/test_staff.put_staff`); `tests/test_migrations.py` HEAD 0205; existing Studentside tests that expect the Assistant 403 on GET.
- Frontend: `src/modules/assessment/{api.ts,assessment-page.tsx}` (Body/Item/Feedback reusable with a `viewer`), new `flag-control.tsx`, `staff-block.tsx`, `assessment-list.tsx`; `switch-block.tsx` renders the list; `src/modules/reports/student-page.tsx` (+ `api.ts` types) adds the block, hides the two blocks when `!can_manage`; `src/copy/nb.ts`; `e2e/ai-assessment.spec.ts`.

## Tasks & Acceptance

**Execution:**
- Backend as in the Code Map; `npm run api:generate` after the schema change.
- `backend/tests/assessment/test_flags.py` -- every matrix row, registry topics, `summaries_for_session`, no letter-like key in the staff JSON (exact key set).
- Frontend: flag control (Vitest for its states), staff block, list, Studentside gating; e2e stand-in tests for flag, undo, failure and the staff view at 320/360/1440 with axe and a 44 px check; one live test (Student flags on the stack, Lecturer sees the flag on the Studentside and the count on the Klasseøkt).

**Acceptance Criteria:**
- Given a Student on their ready assessment, when they press «Marker som feil», then the control reads «Markert. Faglærer ser det.» with «Angre» (`aria-pressed="true"`), with no dialog, and a reload keeps it.
- Given a Lecturer or Assistant lecturer of the Class, when they open the Studentside, then the «KI-vurdering» block shows the disclosure, scores, feedback, dropped notes, unchecked notice and which items the Student flagged; an Assistant lecturer sees no «Tilrettelegging».
- Given the Klasseøkt «KI-vurdering» block, when staff open it, then each Student row is a Lenke to their Studentside with the state and the flag count in words.

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
Layers: blind hunter, edge-case hunter, verification gap, intent alignment (sonnet; four reviewers for an access and data-model change).
- verdicts: 27 findings — high 0, medium 1, low 19, false 7, maybe-false 0
- findings:
  - `[low]` `[patch]` Blind: `StudentTarget.can_manage` and `StudentPageOut.can_manage` default to the privileged `True` — both are now required (no default); OpenAPI regenerated.
  - `[false]` `[reject]` Blind: the list's flag count and the Studentside's can disagree when a flag outlives its feedback — feedback is written once (`_store_score` inserts `ON CONFLICT DO NOTHING`), a flag needs feedback shown, and the read-time drop in `_feedback_of` never happens for a closed attempt's own answer; the list zeroes flags in every state with no items.
  - `[false]` `[reject]` Blind: a resume or re-run replaces feedback under an old flag, or deletes and re-inserts scores — scores and feedback are never replaced or deleted by a run; resume only resets the assessment row.
  - `[false]` `[reject]` Blind: `_state_of` can return a status outside `AssessmentState` (500) — `ck_ai_assessments_status` allows only `incomplete`, `ready`, `failed`, all in the literal.
  - `[low]` `[reject]` Blind: nested models (`AssessedItemOut`, `AiScoreOut`) are shared with the staff schema, so a nested Student-only field would pass — Story 12.6's letter is per assessment (beside the total, top level), which the exact key-set test pins; separate nested schemas add a second copy of every model for a field that does not exist.
  - `[low]` `[reject]` Blind: the "feedback shown" check and the write are separate transactions — feedback never changes; only a stop can land between them, and its flag is then hidden from both views until a resume, which is the state the Student chose.
  - `[low]` `[reject]` Blind: `casefold` sorts Å before Æ and Ø — the codebase's convention for every name list (`classes._sort_key`, `admin.service`); a Norwegian collation is a cross-cutting change, not this story's.
  - `[low]` `[patch]` Blind: every toggle has the same name and nothing ties it to its item — the button now has `aria-describedby` naming its item heading («Oppgave 3 · Langsvar»). The changing label with `aria-pressed` is the spine's own wording (UX-DR39), kept.
  - `[low]` `[patch]` Blind: a 409 leaves a stale control and pending clicks are dropped silently — a 409 now reads the view again (`invalidateQueries`); a click during the one in-flight request is ignored by design (no double toggle).
  - `[low]` `[reject]` Blind: each toggle emits `session:<id>`, refetching the staff's queries — the `session` topic reaches only the Class's staff (`class_sessions_staffed_by`), the same pattern as every staff-visible change; a flag is a rare event.
  - `[false]` `[reject]` Blind: the staff copy for `not_ready`, `failed`, `incomplete` addresses the Student — those three lines are neutral («KI-vurderingen kommer …», «… kunne ikke lages …», «… ikke ferdig …»); only `no_test` and `switched_off` speak to the Student, and both have staff variants. Hiding the list when switched off is a design choice: the list says «Slått av» per row.
  - `[low]` `[reject]` Blind: staff reads are not audited; `flagged_at` is unused — no staff read of Student data is audited in the app (Explanation, Debrief summary); `flagged_at` is the row's time for Epic 13 and the personal-data registry.
  - `[low]` `[reject]` Blind: free-form `action` strings raise `KeyError` on a typo — the two callers pass constants, and `authz.can` failing loudly on an unknown action is the closed table's design.
  - `[low]` `[patch]` Blind: test gaps (undo events, removed Student, `staff()` docstring, list at phone width) — undo now asserts its events and a silent repeat; a Student removed from the Roster is refused the staff read; the helper is `admin()` with a true docstring; the live test checks the Klasseøkt list at 360 px with axe and a 44 px Lenke.
  - `[low]` `[patch]` Blind: `reports/api.ts` still says «for now the block «Tilrettelegging»» — doc corrected. The discriminated-union suggestion is rejected: `ManagedStudentPage` narrows at the one call site.
  - `[false]` `[reject]` Edge: the list counts raw flags while the view counts shown ones — same refutation as the Blind flag-count row.
  - `[low]` `[reject]` Edge: the list state can read `ready`/`incomplete` where the view says `not_ready` — only in the instant between a run storing the last score and settling the status (the view's own transient branch); the next event reads it again.
  - `[low]` `[reject]` Edge: a stop between the check and the write stores a hidden flag — same as the Blind transaction row.
  - `[medium]` `[patch]` Edge: after a stop with the assessment not ready, «Angre» answered 409, so the Student could not take back their flag — «Angre» now needs only a stored score; the view need not show the feedback. New assertions: undo after a stop returns 200 with `switched_off`, undo on a dropped item stores nothing.
  - `[low]` `[patch]` Edge: a 409 keeps a stale control — same fix as the Blind 409 row.
  - `[low]` `[patch]` Edge: the list's heading and skeleton flash before a 403 (the Admin of a Control test) — the list renders nothing until the api answers.
  - `[low]` `[patch]` Edge: `can_manage` defaults to `True` — same fix as the Blind row.
  - `[low]` `[patch]` Verification: the list's `incomplete`, `failed` and open-attempt rows were unasserted — the list test now pins `incomplete` with its real flag count, `failed` and `not_ready` with 0, then `switched_off`.
  - `[low]` `[patch]` Intent: the Klasseøkt list is covered in the browser only at 1440 px — the live test now reads it at 360 px with axe and the 44 px Lenke, then follows it at 1440 px.
  - `[low]` `[reject]` Intent: the Assistant lecturer's Studentside is stubbed in the browser — the real access is pinned by the api tests (`test_flags.py`, `test_adjustment.py`); the page guard (`lecturerHome`) already admits Assistant lecturers and is unchanged.
  - `[false]` `[reject]` Intent: `summaries_for_session` gives Epic 13 the raw status, not the list's state — its docstring says the caller judges access and the switch; the story asks for "the same read" of the data.
  - `[false]` `[reject]` Intent: side effects on existing specs (`exact: true`, nullable `deadlines`, the inverted Assistant assertion) — each is the story's own rule (the page opens to Assistant lecturers without «Tilrettelegging»), not drift.

## Design Notes

- The staff schema copies the Student's view field by field (`StaffAssessmentOut.model_validate(view.model_dump())`, extra ignored): a new Student-only field is dropped unless added on purpose.
- «Frister» is withheld from Assistant lecturers too: the block's only action is the owners', and an extension can hint at a Tilrettelegging (decision recorded).

## Verification

**Commands:**
- `uv run pytest tests/assessment tests/individual_test/test_extension.py tests/sessions tests/test_migrations.py tests/test_authz_rules.py -q --maxprocesses=8` -- pass
- `npm run typecheck && npx vitest run src/modules/assessment src/modules/reports` -- pass
- `npx playwright test e2e/ai-assessment.spec.ts --workers=4` -- pass

## Auto Run Result

Status: done

**Summary.** A Student marks a piece of written feedback as wrong with one press of «Marker som feil» under it. The flag is stored at once (`PUT …/test/assessment/items/{item_id}/flag`, new table `ai_feedback_flags`, migration 0205), with no dialog. The control is a text toggle with `aria-pressed`, no icon and a 44 px tap target. Flagged, it reads «Markert. Faglærer ser det.» and the button says «Angre» (`DELETE`). A failed request shows «Det ble ikke lagret. Prøv igjen.» inline, and the button stays active. Flag and undo are idempotent and emit `user` and `session` (`assessment.set_flag` in the registry). Only feedback the Student's view shows can be flagged (409 `feedback_not_flaggable` otherwise); «Angre» works whenever a score is stored, also during a stop. The staff of the Class (owners and Assistant lecturers, `ai_assessments.read`) read the Student's view under its own `StaffAssessmentOut` schema at `GET /api/class-sessions/{id}/students/{user_id}/assessment`. It holds the same states, scores, feedback, dropped notes and unchecked notice, plus which pieces were flagged. The Studentside shows it as the block «KI-vurdering», with the disclosure, a count line, and «Studenten har markert denne tilbakemeldingen som feil.» under each flagged piece. The Studentside now opens for Assistant lecturers (`student_pages.read`). They get `can_manage: false` and neither «Tilrettelegging» nor «Frister», and both PUTs stay owner-only. The Klasseøkt's «KI-vurdering» block lists each Student by name (`GET /api/class-sessions/{id}/assessments`), each row a Lenke to the Studentside, with the state and the flag count in words. `assessment.service.summaries_for_session` gives the same per-Student read (attempt, status, runs, flags) for Epic 13. Outsiders, Students, the Admin without a staff role, a non-Student `user_id` and unknown ids get one 403.

**Process.** Implemented in the build agent's own context, as the lane brief requires, not by the workflow's implementation subagent; review fixes were applied by the build agent too.

**Decisions taken here (founder would otherwise):**
- «Frister» is withheld from Assistant lecturers along with «Tilrettelegging». The page also omits the data, not just the block.
- The staff copy is draft `[ASSUMPTION]`: the block lines, the per-item flagged line, the count line, the list title «Studentenes KI-vurderinger», the row states and «n markert som feil». The flag words are the spine's.
- The list zeroes the flag count in states that show no items (failed, stopped, switched off).
- A flag stores no reason and is not audited (the Student's own toggle).
- «Angre» works while a stop hides the feedback.
- The Admin role alone reads no assessment, not even on a Control test (12.9 handles that).
- Names sort with `casefold`, the codebase convention.

**Files.**
- `backend/migrations/versions/0205_feedback_flags.py` (new), `backend/app/modules/assessment/{models,service}.py`, `README.md`: the table, `set_flag`, `AssessmentRecord.flags`, `summaries_for_session`.
- `backend/app/modules/tests/{assessed,routes,schemas}.py`: the view split (`_view`, `_state_of`), `set_flag`, `staff_read`, `staff_list`, four routes, `StaffAssessmentOut`, `AssessmentRowOut`, `AssessmentListOut`, `AiScoreOut.flagged`.
- `backend/app/modules/sessions/{service,adjustments,routes,schemas}.py`: `student_target(…, action)` with `can_manage`, `session_students`, the Studentside on `student_pages.read`, `StudentPageOut.can_manage` and nullable `deadlines`.
- `backend/app/platform/{authz.py,events/registry.py}`: `student_pages.read`, `ai_assessments.read`, `assessment.set_flag`.
- Tests: `backend/tests/assessment/test_flags.py` (new); `test_assess.py`, `tests/platform/test_authz.py`, `tests/sessions/test_adjustment.py`, `tests/test_migrations.py` updated.
- Frontend: `src/modules/assessment/{flag-control,staff-block,assessment-list}.tsx` (new), `assessment-page.tsx` (`AssessmentView` for both viewers), `api.ts`, `assessment.ts`, `switch-block.tsx`, `flags.test.tsx` (new), `assessment.test.ts`; `src/modules/reports/{student-page,deadline-block}.tsx`, `api.ts`, tests; `src/copy/nb.ts`; `src/lib/api/{openapi.json,schema.ts}` regenerated; `e2e/ai-assessment.spec.ts`, `e2e/ai-assessment-switch.spec.ts` (`exact: true` on a heading the new list title also matches).

**Review.** Four sonnet reviewers reported 27 findings: high 0, medium 1, low 19, false 7.
- Patched: 1 medium («Angre» during a stop) and 10 low (required `can_manage`, `aria-describedby`, refetch on 409, no list flash, test gaps, list at 360 px, doc).
- Rejected: 7 false and 9 low, each with its reason in the triage log. Nothing deferred.

**Follow-up review: not recommended.** Patched entries: high 0, medium 1, low 10.

**Verification.**
- Backend: full suite `--maxprocesses=8` passed after the patches (3761 passed, 4 skipped). `ruff check` and `ruff format --check` are clean. One earlier full run had a single failure in `tests/messaging/test_message_reads.py`, which passed alone and in the final run; it is unrelated (flaky under load).
- Frontend: `tsc` clean, Vitest 1184 passed, `lint:colours` and `check:copy` pass, `next build` ok.
- Playwright on the lane-3 stack (8082), rebuilt after the patches: 71 passed across `ai-assessment` (with the new flag, failure and staff tests at 320/360/1440 with axe, and the live flag test), `ai-assessment-switch`, `tilrettelegging`, `deadline-extension`, `homes` and `class-session`. Before the patches, `order-field`, `week-table`, `individual-test` and `game-start` also passed (87).
- Matrix audit: every row has a passing test in `tests/assessment/test_flags.py` or `tests/sessions/test_adjustment.py`.
- New tests over 1 s: each api test in `test_flags.py` takes about 2 s, from the shared Adapted-session fixture. The live Playwright test takes about 10 s.

**Residual risks.**
- The new staff copy is `[ASSUMPTION]` draft.
- A Student-only field added later to a nested item model would reach staff; only the top-level key set is pinned.
- Name order uses `casefold`, not Norwegian collation (Å before Æ, Ø), as elsewhere in the app.

**Personal data.**
- New table `ai_feedback_flags` (`assessment_id`, `item_id`, `flagged_at`): no `user_id` column, but each row is a Student's own judgment, tied to them through `ai_assessments.user_id`. It holds no text the User wrote. Lane 1's registry (Story 15.2) should list it.

**Follow-up fixes from the blind review (2026-11-22, on the lead's request).** I reconsidered four blind rows that were rejected in the first pass and patched them:
- The flag check and the write now run in one transaction. `assessment.set_flag` judges again, with the switch row share-locked, that the feedback is shown: the item has feedback, the switch is on, there is a finished run, and the assessment is ready, or incomplete and not stopped.
- `_state_of` maps any unknown status to `not_ready`, so the staff list can never answer 500.
- `student_target` refuses (returns None, which gives a 403) for an action that is not a Class action, instead of raising `KeyError`.
- `FlagControl`'s accessible name is now its own words followed by its item heading (`aria-labelledby`), for example «Marker som feil Oppgave 3 · Langsvar». This replaces the first pass's `aria-describedby`.

Unchanged from the first pass: `can_manage` stays required. Norwegian sort order and the nested-schema rows stay rejected, for the reasons in the triage log.

New tests in `test_flags.py`: the write refuses during a stop and on dropped feedback, an unmapped status reads as not ready, and an unknown action is refused. The touched backend tests pass (88), as do `tsc`, Vitest and Playwright (`ai-assessment`, `tilrettelegging`: 33 passed).
