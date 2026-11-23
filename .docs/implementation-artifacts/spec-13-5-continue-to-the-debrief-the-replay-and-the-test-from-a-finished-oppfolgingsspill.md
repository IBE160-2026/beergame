---
title: 'Story 13.5: Continue to the Debrief, the Replay and the test from a finished Oppfølgingsspill'
type: 'feature'
created: '2026-11-23'
status: 'done'
baseline_revision: '213b19aad4a806aee030d77c51ad8cd1276ab32b'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-13-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-13-4-give-a-student-an-oppfolgingsspill.md'
warnings: ['oversized']
deferred:
  - summary: >-
      `_has_debrief` returning None for an unfinished or closed Oppfølgingsspill card is untested.
    evidence: |-
      Verification-gap layer: only the finished make-up's `debrief` field is asserted; a change
      making it True for every make-up would pass. Small UI-state edge.
    location: >-
      backend/app/modules/sessions/service.py (_has_debrief)
    severity: low
  - summary: >-
      Hiding the Spillinnsikt link for a make-up game on the Studentside has no test.
    evidence: |-
      Verification-gap layer: `data-record-insight` is asserted nowhere for the make-up case.
    location: >-
      frontend/src/modules/reports/record-blocks.tsx
    severity: low
---

<intent-contract>

## Intent

**Problem:** A finished Oppfølgingsspill (Story 13.4) leads nowhere: `games.service.student_game` returns only the Class game, so a late registrant has no Debrief, Replay or test, the make-up records no `class_game` step, and its «Gå til Debrief» opens the Class game's Debrief (FR-17, FR-20, AD-13).

**Approach:** `student_game` returns the Student's make-up once it finished by its last Week, else the Class game (the old read, kept as `class_game_of`). The `makeup` policy row turns on `records_class_game_step` and a new column `debrief_always_personal`. The Debrief keeps the game a Student already started it on; Hjem, Stegene and the Studentside show the make-up as the Student's game.

## Boundaries & Constraints

**Always:**
- `games.service.student_game(s, user, cs)`: a Game of an `own_round == "makeup"` purpose in the Class session whose Seat the Student holds, `lifecycle=finished` and `end_reason` None (closed at the Test deadline never counts) wins; else `class_game_of` (the current body, unchanged). `StudentGame.makeup` and new `debrief_personal` are set from the policy in both `student_game` and `own_game`. `own_game` of a Class game matches `class_game_of`, so the Student keeps their Class game's play screen and result.
- Policy `makeup`: `records_class_game_step=True`; new `GamePolicy.debrief_always_personal: bool` (True for `makeup` only, in `BoolColumn`). `_record_class_game_step` is unchanged: it records `class_game` for the make-up because `student_game` now names it; idempotent through `progress.record_step`.
- Completion (`reports.service.completion_status`) reads the Class game through `games.class_game_of` (never the make-up twice).
- Debrief: `debrief.rules.debrief_game(s, user, cs)` = the game of a Debrief the Student already started in the Class session (any row of theirs in `debrief_explanations`, `debrief_fact_sets`, `debrief_summaries`, `quiz_attempts`, or `debrief_members`/`debrief_step_marks`/`debrief_alone` through `debrief_sessions`), read through `games.own_game`; else `student_game`. `state`, `available`, `group_open` and `staff_summary` use it. `open_mine` never makes a shared session for a game with `debrief_personal`. The narration finish hook also defers for `debrief_always_personal` Games. No stored row is rewritten.
- Replay (`replay.service.start`) and Adapted items (`tests.adapted._sources`) need no change: they read `student_game`; api tests prove the make-up's Role and facts set.
- Hjem (`sessions.enrolled_sessions`): `game` is the `student_game` card (a finished make-up then, with its `debrief` state); `makeup` is None when it is that same game. `_game_out` gets the Debrief state for a make-up only when it is the Student's game (`student_game_of` too). Stegene: with no Class game card but an unfinished make-up card, `has_game` is true and the not-done Debrief step is `locked` with `after_makeup=True` (`StepOut.after_makeup: bool = False`).
- Studentside: `RecordGameOut.makeup: bool`; the game line reads «Oppfølgingsspill · Grossist» and has no Spillinnsikt link for a make-up (`staff_insight` off).
- Copy (`nb.ts`, draft [ASSUMPTION]): `homes.student.locked.debriefAfterMakeup` «Debrief, åpnes når Oppfølgingsspillet er ferdig.»; record game name «Oppfølgingsspill».

**Never:** no new table or migration; no command compares a purpose; no rewrite of a started Debrief, Replay, walkthrough or Adapted item; no change to the end screen (it already offers «Gå til Debrief»); no Group debrief for a make-up.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Class game only | Seat in Class game | `student_game` = Class game | — |
| Class + unfinished make-up | make-up ready/running | Class game | — |
| Class + finished make-up | make-up played to last Week | make-up, `makeup=True`, `debrief_personal=True` | — |
| Finished make-up only | late registrant | make-up | — |
| Unfinished make-up only | late registrant | None; Stegene Debrief locked `after_makeup` | — |
| Closed make-up | `end_reason=test_deadline` | never the Student's game | — |
| Finish | last Week of make-up | one `class_game` step event (kept if already there) | — |
| Started Debrief | explanation saved on Class game, then make-up finishes | Debrief stays on the Class game | — |
| Group mode | Debrief mode group, finished make-up | Personal debrief (not shared) | — |

</intent-contract>

## Code Map

- `backend/app/modules/games/policy.py` -- `GamePolicy`, `POLICIES[MAKEUP]`, `BoolColumn`, add `debrief_always_personal`, helper for own-round purposes.
- `backend/app/modules/games/service.py:512` `student_game`, `:857` `own_game`, `:487` `StudentGame`, `:631` `game_students` (reads `student_game`: a Student whose make-up finished leaves the Class game's group, intended).
- `backend/app/modules/games/repo.py:154` `student_seats`, `:203` `own_game`, `held_role` -- add a finished own-round read through `authz.own_seat`.
- `backend/app/modules/games/commands.py:2809` `finish` → `:2893` `_record_class_game_step` (lifecycle set before; reads `student_game`).
- `backend/app/modules/debrief/rules.py` `state`, `available`, `group_open`; `debrief/service.py:378` `open_mine`, `:1252` `staff_summary`; `debrief/narration.py:98` `_defer_on_finish`; `debrief/models.py` per-Student tables.
- `backend/app/modules/reports/service.py:69` Completion's Class game read; `reports/studentside.py:130` record game; `reports/schemas.py` `RecordGameOut`.
- `backend/app/modules/sessions/service.py:1496-1569` Hjem assembly, `:1588` `stegene`, `:1883` `_makeup_card`, `:2474` `_student_card`, `:2509` `_game_out` (`debrief=` line 2557), `:2698` `student_game_of`; `schemas.py` `StepOut`.
- Unchanged readers proven by tests: `replay/service.py:152` `start`, `tests/adapted.py:64` `_sources`.
- Tests to reuse: `tests/reports/test_makeup.py` (give, `play_weeks`, `late`, `dated`), `tests/games/test_policy.py`, `tests/debrief/` open tests, `tests/replay/` start tests, `tests/tests/` adapted tests, `tests/sessions/test_student_home.py` `home`.
- Web: `frontend/src/copy/nb.ts`; `modules/games/home.ts` `stepItems` (+ test); `modules/reports/record.ts` `gameLines`, `record-blocks.tsx`; e2e `frontend/e2e/studentside.spec.ts` or a new `makeup-debrief.spec.ts`.

## Tasks & Acceptance

**Execution:**
- `games/policy.py`, `games/repo.py`, `games/service.py` -- column, row, `class_game_of`, `student_game`, `own_game`, flags.
- `debrief/rules.py`, `debrief/service.py`, `debrief/narration.py` -- `debrief_game`, personal-only, narration.
- `reports/service.py`, `reports/studentside.py`, `reports/schemas.py` -- Class game read, record `makeup`.
- `sessions/service.py`, `sessions/schemas.py` -- Hjem card and `makeup`, `_game_out` Debrief state, Stegene `after_makeup`.
- Tests: `tests/games/test_student_game_makeup.py` (table: the five cases + closed), policy test, `tests/reports/test_makeup_continue.py` (finish records one step; late registrant Hjem before/after; started Debrief kept; group mode personal; Replay Role from make-up; Adapted items from make-up facts; Studentside `makeup`).
- Web: `nb.ts`, `home.ts` (+ test), `record.ts`/`record-blocks.tsx` (+ test); `npm run api:generate`.
- e2e: from the last Order of a make-up on the play screen, «Spillet er ferdig» → «Gå til Debrief» → Debrief step 1, at 360 and 1440 px with axe.

**Acceptance Criteria:**
- Given a finished make-up, when the Student presses «Gå til Debrief», then a Personal debrief of the make-up opens at step 1 whatever the Debrief mode.
- Given a late registrant, when Hjem is read before and after the make-up finishes, then before Stegene's Debrief step reads «Debrief, åpnes når Oppfølgingsspillet er ferdig.» and after it is current.
- Given a finished make-up, when the Lecturer opens the Studentside, then the game block reads «Oppfølgingsspill · …» and Completion counts the Class game and the make-up once each.

## Spec Change Log

## Review Triage Log

### 2026-11-23 — Review pass
- layers: four (blind, edge case, verification gap, intent alignment) on Sonnet, as the lane brief directs for a change to game choice, access and deadlines.
- verdicts: 37 findings — high 0, medium 0, low 27, false 6, maybe-false 0, plus 4 descriptive intent rows graded low
- findings:
  - `[low]` `[reject]` Blind: `_started_on` union has no ORDER BY. Once a Debrief is started, `debrief_game` pins every later row to the same game, so two games appear only after a pre-existing Seat move; a rare case, and ordering adds a branch.
  - `[low]` `[reject]` Blind: a Student with a Debrief started on the Class game gets Replay and Adapted items from the make-up. The story says exactly this: started steps keep their game, steps started afterwards use the make-up.
  - `[low]` `[reject]` Blind: A's make-up card says the Debrief is open and leads to the Class game's Debrief. The Debrief state is per Student and session; the page names the game it runs on.
  - `[low]` `[patch]` Blind/Edge: a finished make-up dropped the Student from `game_students` of their Class game, so a Group debrief they had joined lost them. `game_students` now reads `class_game_of`; a Group debrief is offered only while `debrief_game` is that game (`group_open`); test asserts both stay counted; README says so.
  - `[low]` `[reject]` Blind: extra query in `student_game`. One indexed query per call; no measured hot path.
  - `[low]` `[reject]` Blind: a late registrant whose make-up closed gets no explanation. The Studentside offers no second make-up by the 13.4 decision; a new line adds copy for a rare state.
  - `[false]` `[reject]` Blind/Verification: `_started_on` branches untested, a mistyped column would pass. All seven branches compile into the one UNION query every test of `debrief_game` runs, so a bad column fails at once; the fallback exclusion is now tested (patched test row).
  - `[low]` `[reject]` Blind: staff lose the Spillinnsikt link to the Class game. Spillinnsikt is reached from the overview wall; `staff_insight` off for make-ups is a 13.4 decision.
  - `[low]` `[reject]` Blind: thin frontend tests. The e2e runs the path at two widths; `stepItems` and `gameLines` have unit cases.
  - `[low]` `[reject]` Blind: draft copy has no follow-up item. Draft copy is marked `[ASSUMPTION]` and listed in the report, as in every story of the epic.
  - `[false]` `[reject]` Blind: a make-up's narration job could overwrite the Class game's. `narration_key` is per game and Seat; the make-up's is its own.
  - `[low]` `[patch]` Blind/Edge: `adjustments.py` recomputed turn times of `student_game` (the finished make-up) instead of the running Class game. Now `class_game_of`.
  - `[false]` `[reject]` Blind: `makeup.give` draws the Role of a second make-up from the first. There is one make-up per Student and session.
  - `[low]` `[reject]` Edge: the narration sweep (`due_narrations`) does not retry a lost make-up job. Widening `finished_student_seats` changes a shared listing; the Debrief falls back to the code text.
  - `[low]` `[patch]` Edge: a make-up closed at the Test deadline made Stegene's Klassespill step current for a Student with no Class game. `has_game` now counts only a make-up still to play; test asserts the step is locked.
  - `[low]` `[reject]` Edge: a make-up finished while the Class game still runs replaces it. The story says the finished make-up is the Student's game.
  - `[low]` `[reject]` Edge: a Personal debrief opened but untouched does not pin the Class game. Design note: nothing of the Student's is stored, so nothing is redone.
  - `[false]` `[reject]` Edge: reflection answers or follow-ups alone do not pin. Both come after step 1, whose Explanation row is always stored first.
  - `[low]` `[reject]` Edge: `limit(1)` picks an arbitrary game. Same as the first Blind row.
  - `[low]` `[reject]` Edge: Replay/Adapted split from the Debrief. Same as the second Blind row.
  - `[low]` `[patch]` Edge: `staff_summary` of a make-up Debrief has no number and read «Testspill». `StaffSummaryOut.makeup`; the summary page names «Oppfølgingsspill»; test asserts both Students' summaries.
  - `[false]` `[reject]` Edge: `finished_own_rounds` "newest first" false for random uuids. Ids are UUIDv7, time-ordered, and there is one make-up per Student.
  - `[low]` `[patch]` Edge (claim): closed make-up flips Klassespill to current. Same patch as above.
  - `[low]` `[reject]` Edge (claim): narration sweep coverage. Same as the sweep row.
  - `[low]` `[reject]` Edge (claim): Replay/Adapted not following a started Debrief. Same as the second Blind row.
  - `[low]` `[patch]` Verification: make-up narration at finish untested. `test_finish.py` now runs `makeup` through `_defer_on_finish` and expects its job.
  - `[low]` `[patch]` Verification: fallback exclusion and other `_started_on` tables untested. Added a `fallback` row for B, who still moves to the make-up.
  - `[low]` `[patch]` Verification: `staff_summary` via `debrief_game` untested. Test asserts A's summary names the Class game, B's the make-up.
  - `[low]` `[defer]` Verification: `_has_debrief` false branch untested. Deferred.
  - `[low]` `[defer]` Verification: hidden Spillinnsikt link untested. Deferred.
  - `[false]` `[reject]` Verification (other): the `debrief_personal` guard in `open_mine` changes nothing today. True that one Seat cannot reach two active Students; the guard is the AC's policy column and costs nothing.
  - `[low]` `[reject]` Verification (other): A's make-up card Debrief state not asserted. Same as the third Blind row.
  - `[low]` `[reject]` Intent: «Gå til Debrief» proven on the screen only by one e2e. The e2e renders it at 360 and 1440 px with axe and follows it to step 1.
  - `[low]` `[reject]` Intent: idempotent step for a Student with a Class game cannot tell "records again" from "does not record". The late registrant's test proves the recording; `progress.record_step` is idempotent by its own tests.
  - `[low]` `[reject]` Intent: the late registrant's path is api-tested, not in the browser. Hjem's Stegene copy is a unit case of `stepItems` from the api's flag.
  - `[low]` `[reject]` Intent: Group mode not in the browser. Api-tested with `debrief_mode=group`.

## Design Notes

«Started» means a stored per-Student Debrief row: a Personal debrief opened but untouched stores nothing of the Student's, so moving to the make-up redoes nothing. The Replay and Adapted items store their Game and facts set at creation, so they stay on whatever game they were made from.

## Verification

**Commands:**
- `uv run pytest tests/games tests/reports tests/debrief tests/replay tests/sessions/test_student_home.py -q` (lane env) -- pass
- `npm run typecheck && npx vitest run src/modules/games src/modules/reports` -- pass
- `npx playwright test e2e/makeup-debrief.spec.ts e2e/studentside.spec.ts e2e/homes.spec.ts --workers=4` -- pass

## Auto Run Result

Status: done

**Summary.** A finished Oppfølgingsspill is now the Student's game for the Debrief, the Replay and the Individual test (FR-17, FR-20, AD-13). `games.service.student_game` returns the make-up once it has finished by its last Week (never one closed at the Test deadline), else the Class game, now `class_game_of`. The `makeup` policy row records the `class_game` step at its finish (idempotent, through the unchanged `_record_class_game_step`), and a new column `debrief_always_personal` makes its Debrief a Personal debrief in any Debrief mode. `debrief.rules.debrief_game` keeps a Debrief the Student already started (any stored row of theirs) on its game. Hjem shows the finished make-up as the game with its Debrief state and no second make-up block; a late registrant's Stegene says «Debrief, åpnes når Oppfølgingsspillet er ferdig.» until it finishes. The Debrief page, the staff summary and the Studentside name it «Oppfølgingsspill».

**Files.**
- Backend: `games/{policy,repo,service}.py` (column, `purposes_with_own_round`, `finished_own_rounds`, `student_game`/`class_game_of`, `own_game`, `game_students`); `debrief/{rules,service,narration,schemas}.py` and README (`debrief_game`, personal only, narration, `makeup` on `DebriefOut`/`StaffSummaryOut`); `reports/{service,studentside,schemas}.py` and README (Completion reads `class_game_of`, record `game.makeup`); `sessions/{service,schemas,adjustments}.py` (Hjem card, `_has_debrief`, Stegene `after_makeup`, turn times of the Class game).
- Backend tests: `tests/reports/test_makeup_continue.py` (new, the five `student_game` cases plus the closed one, step once, started Debrief kept, Group mode personal, Replay Role, Adapted facts, Studentside, staff summary); `tests/games/test_policy.py`, `tests/replay/test_finish.py`, `tests/reports/test_makeup.py`, step-dict tests.
- Frontend: `copy/nb.ts`; `modules/games/home.ts`; `modules/reports/{record.ts,record-blocks.tsx}`; `modules/debrief/{debrief-page,summary-page}.tsx`; unit tests; regenerated `lib/api/{openapi.json,schema.ts}`; `e2e/makeup-debrief.spec.ts` (new).

**Review.** Four layers, 37 findings: 0 high, 0 medium, 27 low (+4 descriptive intent rows), 6 false. Patched 9 low rows (6 fixes): `game_students` keeps the Class game's Students, Tilrettelegging recomputes the Class game, a closed make-up leaves Stegene locked, the staff summary names the make-up, and tests for make-up narration, the fallback row and the staff summary. Deferred 2 low test gaps. Rejections and reasons are in the Review Triage Log. Follow-up review: **false** (no high or medium patched).

**Verification.**
- Full backend suite (8 processes): 3743 passed, 4 skipped. ruff check and format pass.
- New tests over 1 s: `test_a_finished_makeup_becomes_the_students_game_but_a_started_debrief_stays` about 6 s and `test_a_late_registrants_makeup_opens_the_debrief_replay_and_test` about 4 s (each plays a short Class game and make-ups).
- Frontend: typecheck, Vitest 1201 passed, lint:colours, check:copy; the build passes inside the image.
- Playwright (4 workers) on the lane stack: `makeup-debrief` (new: last Order on the play screen → «Spillet er ferdig» → «Gå til Debrief» → step 1, 360 and 1440 px, axe on both screens), `homes`, `debrief-open`, `student-home`, `game-end`, `playout`, `studentside`, `replay-finish`, `debrief-bill`: 71 passed.

**Decisions taken for the founder [ASSUMPTION].**
- A started Debrief is one with a stored row of the Student's (Explanation, facts set, summary, quiz attempt, group membership, step mark, going alone); a Personal debrief opened but untouched moves to the make-up.
- A Student whose make-up finished stays among their Class game's Students for its Group debrief, which is offered to them only while their Debrief runs there.
- A finished make-up replaces the Class game even while the Class game still runs.
- The Studentside shows no Spillinnsikt link for a make-up game (13.4's `staff_insight` off).
- Draft copy: «Debrief, åpnes når Oppfølgingsspillet er ferdig.», «Debrief, Oppfølgingsspill», «Grossist, Oppfølgingsspill», record «Oppfølgingsspill · Grossist».

**Personal data.** No new table.

**Residual risks.**
- The narration sweep does not retry a lost make-up narration job (the code text shows instead).
- Replay and Adapted items follow the make-up even when the Debrief stayed on the Class game, as the story says.
