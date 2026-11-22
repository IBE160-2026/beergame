---
title: 'Story 8.9: Give one Student more time with Tilrettelegging'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: '23081a1dc76db51259bed19ba19ba896e044fdeb'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-8-context.md'
warnings: [oversized, multiple-goals]
deferred: []
---

<intent-contract>

## Intent

**Problem:** A Lecturer cannot give one Student more time before an AI player takes their Seat, or a lower share of Weeks (FR-17). `rules.turn_times` already takes a `time_factor`, but no command passes one, there is no store, no Studentside and no line telling the Student. Also (Story 8.1 deferred item): the Oversikt's `_next_due` only looks at each game's minimum due time, so once Seats of one game have different due times (this story) a game whose earliest due time has passed is dropped although a later Seat's due time lies ahead.

**Approach:** `sessions` stores the adjustment in a new `student_adjustments` table and exposes `get_adjustment`/`time_factors` from `service.py`. A Lecturer-only Studentside (new `frontend/src/modules/reports/` page under the Class session) shows the «Tilrettelegging» block and its in-place form. Saving audits, emits events and runs the new `games.commands.recompute_turn_times` on the Student's Class game, which recomputes the open Week's due and insert times with each Student's factor. `_start_waits` and `_recompute_insert_times` pass the factor too. Hjem shows the Student's own lines; Spillstyring shows the Lecturer «Jonas har tilrettelegging med mer tid.». `_next_due` reads every waited-for Seat's due time.

## Boundaries & Constraints

**Always:**
- Store: migration `0059_student_adjustments.py`: table `student_adjustments` (`class_session_id` FK `class_sessions` CASCADE, `user_id` FK `users` CASCADE, PK both; `time_factor numeric(3,1) NOT NULL` CHECK `time_factor IN (1.0,1.5,2.0,3.0)`; `share_percent int NULL` CHECK 0..100; `updated_by` FK users SET NULL; `updated_at timestamptz NOT NULL`). No reason column. Model in `sessions/models.py`. `HEAD` in `tests/test_migrations.py` → 0059 and the table in the head set.
- `sessions/service.py`: `Adjustment(time_factor: Decimal, share_percent: int | None)`; `get_adjustment(session, class_session_id, user_id) -> Adjustment | None` and `time_factors(session, class_session_id, user_ids) -> dict[UUID, float]` (only rows with a factor above 1). The only read path for other modules.
- New `sessions/adjustments.py` (as `overview.py`): `student_page(user, session_id, user_id)` and `save_adjustment(user, session_id, user_id, body)`. Both through policy `class_sessions.manage` (Lecturer/owner only, so Assistant lecturers get the same 403 `forbidden` as an outsider, FR-5) and only for a User who is a Student of the Class now (`classes.student_names`), else None → 403. Save: `_writable` (archived → 409 `class_archived`); refuses with 422 `invalid_adjustment` and `fields` (`time_factor: not_offered`, `share_percent: out_of_range`) a factor not in {1, 1.5, 2, 3} or a share outside 0..`required_share(row)`; a share equal to the class share is stored as NULL. Upsert, `audit.record(actor, "student_adjustment.saved", {class_session_id, user_id}, {time_factor, share_percent}, now)`, emit `user:<student>` and `session:<id>` in the same transaction. After commit: `games_commands.recompute_turn_times(game_id)` for the Student's game (`games_service.student_game`), any refusal ignored. No log line names the Student, the factor or the share.
- Routes (sessions `routes.py`): `GET /api/class-sessions/{session_id}/students/{user_id}` (operation `getStudentPage`) → `StudentPageOut` {class_session_id, class_id, class_name, session_number, user_id, name, class_share, adjustment: {time_factor: float, share_percent: int | None} | None}; `PUT …/students/{user_id}/adjustment` (operation `saveAdjustment`, body `AdjustmentIn` {time_factor: float, share_percent: int | None}) → `StudentPageOut`. Api client regenerated.
- Command `games.commands.recompute_turn_times(game_id) -> bool` (registry `games.recompute_turn_times`: `game`, `session`, `user`): under the Game lock, for a running Game with settings, for each open-Week turn a Student holds that has not ordered: `turn_times` with its stored `wait_started_at`, `_inactivity_limit`, the Student's factor (`sessions.service.time_factors`, imported inside the function; `tests/test_imports.py` allows `app.modules.sessions.service`), and the agreed time = the Game's `resume_at` while paused, else the stored insert time when it differs from the stored due time (an agreed time carried past the Pause), else None. Writes changed `takeover_due_at`/`insert_allowed_at` (new `repo.set_due_times`, which also clears `insert_announced_at`); only on a change: `_commit_change` and `user:<id>` for every seated Student. Returns whether anything changed. No audit (the save is audited).
- `_start_waits` and `_recompute_insert_times` pass each turn's Student factor (one `time_factors` read per call). With no clock, an agreed time stands as the insert time (existing rule, [ASSUMPTION] of the epic).
- Views: `EnrolledSessionOut.adjustment: OwnAdjustmentOut | None` ({time_factor: float | None (only above 1), share_percent}) for the reading Student only, None when neither applies. `InsightSeatOut.extra_time: bool = False` true only for a Lecturer viewer (`class_sessions.manage`) and a Student-held Seat with a factor above 1. `GameInsightOut.can_adjust: bool` (Lecturer). Other Students' views gain nothing.
- `sessions/overview.py:_next_due`: the minimum over every waiting game's Seat due times (`waiting_for[].takeover_due_at`) and the game's own, each after `now`.
- Frontend: route `app/(app)/klasseokter/[sessionId]/studenter/[userId]/page.tsx` → `modules/reports/student-page.tsx` (GuardedPage lecturerHome, PageShell, crumbs Lærerhjem / Class / Klasseøkt / name; title the Student's name; 403 → AccessDenied). Block `modules/reports/adjustment-block.tsx`: idle «Ingen tilrettelegging.» or «Mer tid: 2 ×. Andel uker: 60 %.» (a part only when it applies; share part shows the stored share) with secondary «Endre tilrettelegging»; form in place: Valgknapper «Mer tid før KI tar over» («Som klassen», «1,5 ×», «2 ×», «3 ×»), TextField «Andel uker som kreves» (inputMode numeric, prefilled with the stored or class share) with hint «Klassen: 80 %.» and error «Skriv et helt tall fra 0 til 80.», the line «Gjelder bare Jonas, fra nå. Ingen andre studenter ser det. Endringen logges.», primary «Lagre tilrettelegging», «Avbryt» (focus back to the opener). Focus to the first Valgknapp on open, to the share field on error. Success: «Lagret. Gjelder fra nå.» and the summary replace the form; the line takes focus. Pure helpers in `modules/reports/adjustment.ts`. Api in `modules/reports/api.ts`; key `["class-sessions","students",sessionId,userId]`, invalidated by `session:<id>` in `lib/api/topics.ts`. Spillinnsikt `SeatItem`: the Student name is a Lenke to the Studentside when `can_adjust`. Spillstyring row: the caption «Jonas har tilrettelegging med mer tid.» when `extra_time`. Hjem `SessionBlock`: under Stegene «Du har mer tid før en KI-spiller tar setet ditt (2 × vanlig ventetid).» and «For deg er kravet 60 % av ukene.».
- Copy in `nb.ts` (`reports.studentPage`, `reports.adjustment`, `homes.student.adjustment`, `spillstyring.extraTime`); factors formatted Norwegian («1,5 ×»).

**Never:** no reason/health field; no adjustment in mail, logs, other Students' views or errors. No Completion computation (Epic 13). No «I rommet» (8.11). No change to the demo Class. No DB-vs-host time comparison; no real waiting in tests. Assistant lecturers never see the block, link or line.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Save 2× while waited for | clock runs, due = W+24h | due = W+48h, insert = W+48h, version +1, events, Varselbånd follows | — |
| 2× with agreed time earlier | paused, agreed A < W+48h | insert = W+48h | — |
| 2× with agreed time later | agreed A > W+48h | insert = A | — |
| No clock, agreed | paused, nobody ordered | due None, insert = A | — |
| Back to «Som klassen» | was 2× | due/insert = W+24h | — |
| Factor 1.2 / share 81 with class 80 | body | nothing stored | 422 `invalid_adjustment` |
| Assistant / outsider / non-Student | GET or PUT | — | 403 `forbidden` |
| Archived Class | PUT | — | 409 `class_archived` |
| Seat ordered / AI-held | recompute | untouched | — |
| `_next_due` mixed | game min passed, other Seat ahead | next_change_at = the later Seat's due | — |

</intent-contract>

## Code Map

- `backend/app/modules/games/rules.py:159-251` -- `TurnInputs.time_factor`, `turn_times`, `_due_times` (already apply the factor and the FR-89 floor; no change needed).
- `backend/app/modules/games/commands.py:1540` `_start_waits`, `:2218` `_recompute_insert_times` (pass factor), `:2106` `reach_agreed_time` (pattern for a new command), `:251` `_commit_change`, `seated_students`, `_inactivity_limit:1580`, `__all__`.
- `backend/app/modules/games/repo.py:463` `set_insert_allowed` (pattern for `set_due_times`), `:567` `week_turns_with_occupant` (has `user_id`), `open_week`.
- `backend/app/platform/events/registry.py` -- `games.recompute_turn_times`; `backend/tests/games/test_registry.py` RUNNERS.
- `backend/app/modules/sessions/service.py:554` `required_share`, `:645` `_class_for`, `:637` `_writable`, `:1162` `enrolled_sessions` (add `adjustment`), `games_service.student_game`.
- `backend/app/modules/sessions/overview.py:137` `_next_due`; `:377` `game_insight` (add `can_adjust`, `extra_time`).
- `backend/app/modules/sessions/{models.py, repo.py, schemas.py (EnrolledSessionOut 616, InsightSeatOut, GameInsightOut), routes.py}`.
- `backend/app/platform/authz.py` -- reuse `class_sessions.manage` (Lecturer/owner).
- `backend/tests/test_imports.py:60` -- allow `app.modules.sessions.service` in games.
- Tests: `tests/games/test_takeover.py` (`class_game`, `due_of`), `test_staff_pause.py` (`db_now`, `insert_of`, `LECTURER`), `test_game_summaries.check`; `tests/sessions/test_pause_view.py` (`three_students_in_uke_2`, `call`), `test_game_end.py` (`klass`, `short_game`), `test_student_home.home`, `tests/classes/test_staff.py` (`ASSISTANT`, `put_staff`), `test_overview.overview`.
- Frontend: `src/modules/games/{insight-page.tsx SeatItem, spillstyring.tsx rows, student-hjem.tsx SessionBlock}`, `src/components/{segmented-choice,text-field,button,link}.tsx`, `src/modules/games/staff-pause.tsx` (form/focus/result pattern), `src/modules/identity/homes.ts` (paths), `src/lib/api/topics.ts`, `src/copy/nb.ts`.
- e2e: `frontend/e2e/support/{live-game.ts liveClassGame, classes.ts lecturerPage/expectAccessible/expectReflow/VIEWPORTS}`, `spillstyring.spec.ts` (pattern).

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0059_student_adjustments.py`, `sessions/models.py`, `sessions/repo.py` -- table, upsert/read.
- `sessions/service.py` -- `Adjustment`, `get_adjustment`, `time_factors`, `enrolled_sessions.adjustment`.
- `sessions/adjustments.py` (new), `schemas.py`, `routes.py` -- Studentside api.
- `games/repo.py`, `games/commands.py`, `platform/events/registry.py` -- `recompute_turn_times`, factor in `_start_waits`/`_recompute_insert_times`.
- `sessions/overview.py` -- `_next_due`, `can_adjust`, `extra_time`.
- Regenerate `frontend/src/lib/api/{openapi.json,schema.ts}`.
- Frontend: `modules/reports/{api.ts,adjustment.ts,adjustment-block.tsx,student-page.tsx}`, route page, `identity/homes.ts` (`studentPagePath`), `topics.ts`, `insight-page.tsx`, `spillstyring.tsx`, `student-hjem.tsx`, `nb.ts`.
- Tests: `tests/games/test_turn_factor.py` (pure: each factor × agreed/no agreed × clock/no clock; commands with a stubbed `time_factors`: recompute moves due/insert, idempotent, ordered/AI Seats untouched, `_start_waits` with factor, `_recompute_insert_times` floor, registry runner, summary check); `tests/sessions/test_adjustment.py` (one short game: GET/PUT, 422s, Assistant/outsider/non-Student 403, audit row, events, recompute through the api, Hjem lines only for the Student, insight `extra_time`/`can_adjust` for Lecturer not Assistant, `_next_due` unit); Vitest `modules/reports/adjustment.test.ts(x)`; e2e `tilrettelegging.spec.ts` (Spillinnsikt name link → Studentside, form, save → focused line, Spillstyring line, Hjem lines, axe + reflow at 320 and 1440).

**Acceptance Criteria:**
- Given a Lecturer on Spillinnsikt, when they follow a Student's name, then the Studentside shows «Ingen tilrettelegging.» and «Endre tilrettelegging»; an Assistant lecturer sees no link and the api answers 403.
- Given the form, when the Lecturer chooses «2 ×», types 60 and saves, then «Lagret. Gjelder fra nå.» and «Mer tid: 2 ×. Andel uker: 60 %.» replace the form and the line has focus; a share of 81 with class 80 shows «Skriv et helt tall fra 0 til 80.» on the field.
- Given the Student waits with the clock running, when the adjustment is saved, then the stored due and insert times double the limit at once and the Oversikt's Varselbånd shows the new due time.
- Given the Student opens Hjem, then they see both lines under Stegene; another Student of the game sees neither.
- Given Spillstyring for a Lecturer, then the Seat's row shows «Jonas har tilrettelegging med mer tid.»; an Assistant does not see it.
- Given 1440 and 320 px, then the block and form have no horizontal scroll, the form is one column, and axe passes.

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
- Layers: blind hunter (with the privacy angle the orchestrator asked for), edge-case hunter, verification gap and intent alignment, all on Sonnet as the orchestrator asked. All four hand-backs dropped, so the findings were read from `review-{blind,edge,verification,intent}-8-9.md` in the session scratchpad. The diff was taken against `HEAD` (the orchestrator committed `09058ef` on `epic-8` after the baseline) and leaves out the generated api client and `.docs`.
- verdicts: 41 findings — high 0, medium 2, low 28, false 11, maybe-false 0
- findings:
  - `[false]` `[reject]` blind-1: other Students can infer Tilrettelegging from a later insert time. The epic says so on purpose: "the others only ever see a later insert time (UX-DR53)". No reason, factor or badge reaches them, and an Assistant lecturer's `takeover` field carries no time.
  - `[false]` `[reject]` blind-2: `recompute_turn_times` emits to every seated Student. The other Students' views show that Seat's insert time («Etter on. 10:00 …», Story 8.8), so they must read again. The events carry ids only.
  - `[low]` `[reject]` blind-3: the request log and the path name the Student and the word «adjustment». The generic request log writes every path; no factor, share or name is logged, and `turn_times_recomputed` names the game only. Hiding the path would mean changing the route shape or the shared logging middleware, which is beyond a direct correction.
  - `[low]` `[patch]` blind-4: the two personal answers had no cache header. `GET` and `PUT` now answer `Cache-Control: no-store`, asserted in `test_adjustment.py`.
  - `[medium]` `[patch]` blind-5 / edge-7: a stored share above a later-lowered class share was read as a higher requirement. Reads now join the class share; a share no lower than the class's own reads as the class's (`_adjustment`), so `get_adjustment` (Epic 13's source), Hjem and the Studentside never raise it. Test added.
  - `[low]` `[reject]` blind-6 / edge-1 / edge-claim-1: an agreed time carried past the Pause is forgotten once a raised factor's floor hides it and the factor is lowered again. It needs a Pause ended by an Order and then two Tilrettelegging changes in the same Uke, and the fix is a new stored column. The insert time then falls back to the Seat's own limit, which FR-89 allows.
  - `[low]` `[reject]` blind-7 / edge-5 / verification-other-1: a non-`CommandError` from the recompute after the save's commit answers 500. Only a database failure does that; the save is repeat-safe, so the Lecturer's retry recomputes. The story asks for the recompute in the same request, which it is.
  - `[low]` `[reject]` blind-8 / edge-4: lowering the factor can make the due time already passed, and the sweep then takes the Seat. That is the class limit applying again, as the Lecturer chose; the spec gives the form no warning line, and a clamp would change FR-36.
  - `[low]` `[patch]` blind-9: a repeat save left no trace of what it changed. The audit row's `change` now holds `was` (the previous factor and share, or null). Asserted.
  - `[low]` `[patch]` blind-10: «Som klassen» with the class share kept a row about the Student. That save now deletes the row (data minimisation); the audit keeps the change. Asserted. Cleanup on removal from the Class is left to Epic 15's data handling.
  - `[low]` `[patch]` blind-11: Hjem read the adjustment once per Class session. One read for all of them now (`repo.adjustments_of_user`).
  - `[low]` `[reject]` blind-12: no index on `user_id` for the cascade. A User is deleted rarely and the table holds few rows per Class session.
  - `[low]` `[reject]` blind-13: the permission check runs outside the write transaction. Every staff action of `sessions` does the same (`add_lab_hour`, `_managed_session`); the window is one request.
  - `[false]` `[reject]` blind-14: the Spillstyring line names the Student on a screen that may be projected. The epic and UX-DR52 ask for exactly this line, for the Lecturer.
  - `[false]` `[reject]` blind-15: the function-level import of `sessions.service` from `games`. The epic names `sessions.service` as the only read path; `test_imports.py` allows exactly that module.
  - `[false]` `[reject]` blind-16: the `_next_due` change is scope creep, and the privacy negatives are untested. The intent asks for `_next_due`. The privacy negatives are tested: other Students' Hjem, an Assistant's Spillinnsikt and Studentside, an outsider and a Lecturer of another Class (added).
  - `[false]` `[reject]` blind-17: an unknown stored factor reads as «Som klassen» in the form. The table's check constraint allows only 1, 1.5, 2 and 3.
  - `[low]` `[patch]` edge-2: the recompute cleared the sweep's announcement mark even when only the due time moved. `set_due_times` now clears it only when the insert time moves (`insert_moved`).
  - `[low]` `[reject]` edge-3 / edge-claim-3: a raised factor withdraws an insert right that had already arisen. It is intended: FR-89 says a Student with Tilrettelegging never gets an insert time before their own extended limit (Design Notes).
  - `[false]` `[reject]` edge-6: a Student holding Seats in two games of one Class session. The allocation gives each Student one Seat per Class session; `student_game` is the one way to find it.
  - `[low]` `[reject]` edge-8: a Student seated mid-Uke inherits the previous holder's due times. It needs a Student with Tilrettelegging replaced mid-Uke; the fix is a new call in the seating commands. The next Uke computes the new Student's own times.
  - `[false]` `[reject]` edge-claim-2: a peer reads a later insert time. Same as blind-1; the epic allows it.
  - `[low]` `[patch]` verification-1: the Class scope of the Studentside was not tested. A Lecturer of another Class now gets 403 on GET and PUT.
  - `[low]` `[patch]` verification-2: the save's `user` and `session` events were not asserted. A share-only save now asserts both (`emitted` spy).
  - `[low]` `[patch]` verification-3: the carried-agreed-time branch of `recompute_turn_times` was not tested. The no-clock test now ends the Pause with an Order, recomputes with no factor (the agreed time stays) and then with 2 × (the floor applies).
  - `[low]` `[patch]` verification-4: clearing the announcement mark was not asserted. The main command test now marks the turns and asserts that only the moved one is cleared.
  - `[low]` `[patch]` verification-5: the `session` topic's new Studentside key was not tested. `topics.test.ts` now lists `studentPageKey` for two sessions.
  - `[low]` `[patch]` verification-other-2: the `TurnInputs` docstring still said the factor was empty until 8.9. Corrected.
  - `[low]` `[reject]` intent-1: no test asserts the Oversikt response's `next_change_at` after a save. The response field is the unchanged wiring of `_next_due`, which is tested with mixed due times; `test_turn_clock.py` asserts the field end to end.
  - `[false]` `[reject]` intent-2: "game-level minimum" read as each Seat's own due time. Story 8.1's deferred item offers exactly this ("let `_next_due` see every due time ahead").
  - `[false]` `[reject]` intent-3: the recompute runs in a second transaction. The story asks for the same request, which it is; commands own their transactions (AD-2).
  - `[false]` `[reject]` intent-4: `games` reads a batch variant. `get_adjustment` exists as named; `time_factors` reads the same rows for several Students.
  - `[low]` `[reject]` intent-5: a closed set of factors is narrower than "a factor under 1". Recorded as a decision: the form offers only these four.
  - `[low]` `[reject]` intent-6: the save's events are emitted from `sessions/adjustments.py`, not `service.py`. Same module, same transaction; `service.py` stays the read path other modules use.
- Count: 17 blind, 8 edge-case plus 3 claims, 5 verification gaps plus 2 other, 6 intent observations. Findings with the same root cause share one row, named by every member.

## Design Notes

The carried agreed time: after a Pause ended by an Order (Story 8.7) the agreed time stays a turn's insert time while it differs from the due time, so `recompute_turn_times` reads it back as the agreed time; `turn_times` then applies the FR-89 floor (`max(agreed, extended due)`). An insert right that had arisen is withdrawn when the factor now puts the Seat's own limit later: FR-89 says such a Student never gets an insert time before their own extended limit.

`games` reads the factor through `sessions.service` with a function-level import, which the epic names as the only read path; sessions already imports games at module level, so a top-level import would be circular.

## Verification

**Commands:**
- `cd backend && uv run pytest -q tests/games/test_turn_factor.py tests/sessions/test_adjustment.py tests/games/test_registry.py tests/test_imports.py tests/test_migrations.py` -- pass
- `cd frontend && npx vitest run src/modules/reports` -- pass
- Before the commit: full suites and the e2e specs the runbook names, plus `tilrettelegging.spec.ts`.

## Auto Run Result

Status: done

**Summary.** A Lecturer can give one Student more time before an AI player takes their Seat, and a lower share of Weeks, from a new Studentside. The game follows at once.

- **Store.** Migration 0059 adds `student_adjustments`: per Class session and Student, the factor (1, 1,5, 2 or 3) and the share. It has no reason field. «Som klassen» with the class share keeps no row.
- **Read path.** `sessions.service.get_adjustment` and `time_factors` are the only reads. A share no lower than the class's own reads as the class's.
- **Studentside api.** `GET /api/class-sessions/{id}/students/{user_id}` and `PUT …/adjustment` are for the Class's Lecturers only. Everyone else gets 403, Assistant lecturers included. A save is audited (with `was`) and emits `user` and `session`. The answers are `no-store`.
- **Turn times.** The new command `games.commands.recompute_turn_times` recomputes the open Uke's due and insert times with each Student's factor (FR-89 floor; with no clock an agreed time stands). `_start_waits` and the Lecturer's Pause commands pass the factor too. Automatic Takeover, the Varselbånd and «Sett inn KI-spiller» follow.
- **Screens.**
  - On Spillinnsikt the Student's name leads to the Studentside (Lecturer only).
  - The block «Tilrettelegging» has an in-place form, and «Lagret. Gjelder fra nå.» takes focus after a save.
  - Spillstyring shows «Jonas har tilrettelegging med mer tid.» to the Lecturer.
  - Hjem shows the Student their own two lines.
- **Story 8.1's deferred item.** `_next_due` reads every waited-for Seat's own due time, so the Oversikt reads again at a later Seat's due time when the game's earliest has passed.

**Files changed**
- Backend:
  - `migrations/versions/0059_student_adjustments.py` (new) and `sessions/models.py`: the table.
  - `sessions/repo.py`: the reads, upsert and delete.
  - `sessions/service.py`: `Adjustment`, `get_adjustment`, `time_factors`, `own_adjustment`, `adjustment_out`, and Hjem's `adjustment`.
  - `sessions/adjustments.py` (new): the Studentside and the save.
  - `sessions/routes.py` and `schemas.py`: the routes and the fields.
  - `sessions/overview.py`: `_next_due`, `can_adjust` and `extra_time`.
  - `games/commands.py`, `games/repo.py` and `games/rules.py` (docstring): `recompute_turn_times`, `_time_factors` and `set_due_times`.
  - `games/models.py`: a comment.
  - `platform/events/registry.py`: the registry entry.
- Frontend:
  - `modules/reports/{api.ts,adjustment.ts,adjustment-block.tsx,student-page.tsx}` (new) and the route `app/(app)/klasseokter/[sessionId]/studenter/[userId]/page.tsx`.
  - `games/{insight-page,spillstyring,student-hjem}.tsx`, `identity/homes.ts`, `lib/api/topics.ts` and `copy/nb.ts`.
  - `lib/api/{openapi.json,schema.ts}`: regenerated.
- Tests:
  - New: `tests/games/test_turn_factor.py` and `tests/sessions/test_adjustment.py`.
  - Updated: `test_registry.py` (runner), `test_imports.py` (allows `sessions.service` in games), `test_migrations.py` (HEAD 0059), `test_dates.py` and `test_game_insight.py` (new keys), `test_turn_clock.py` (its tampering now also sets the Seats' own due times back).
  - Vitest: `reports/adjustment.test.tsx` (new), `topics.test.ts`, and fixtures in four games tests.
  - e2e: `tilrettelegging.spec.ts` (new).

**Review.** Four Sonnet reviewers returned 41 findings: high 0, medium 2 (one root cause), low 28, false 11.
- Patched (medium): a share above a later-lowered class share is read as the class's.
- Patched (low):
  - `no-store` on the personal answers;
  - `was` in the audit row;
  - no row kept for «Som klassen»;
  - one Hjem read;
  - the announcement mark cleared only when the insert time moves;
  - the `TurnInputs` docstring;
  - new tests for the Class scope, the save's events, the carried agreed time, the cleared mark and the topic key.
- Deferred: none.
- Rejected: the rest, each with its reason in the Review Triage Log.
- Follow-up review: not recommended. Patched entries: high 0, medium 1, low 13.

**Verification** (after the patches)
- **Backend.** The full suite with `--maxprocesses=8` passed: 3032 tests. ruff check and format are clean.
  - The first full run failed on `tests/sessions/test_turn_clock.py::test_the_overview_reads_again_at_the_nearest_takeover_due_time`. It tampered only the game-level due time, which `_next_due` no longer reads alone. The test now sets the Seats' own due times back too; this was not a flake.
  - A second full run's summary was not captured (its output was cut). pytest's last-failed cache then held 20 tests, among them `tests/games/test_peer_insert.py::test_the_finder_skips_a_game_that_no_longer_runs`. All 20 passed with `--lf`, and the next full run passed all 3032. Treat these as possible one-off failures under load; the shared Postgres went through crash recovery tonight.
- **Frontend.** Typecheck, Vitest (72 files, 880 tests), `lint:colours`, `check:copy` and `next build` all pass.
- **End to end.** The stack was rebuilt after the last frontend change. Playwright with `--workers=4` ran 185 tests, and all passed on the first run. The specs were tilrettelegging, spillstyring, game-insight, homes, student-home, pause, staff-pause, takeover, takeover-overview, peer-insert, varselband, overview, seat-status, live-updates, order-field, order-confirm, order-failures, guided-week, week-advance, week-transition, week-table, chain-band, cost-panel, game-card, graph-over-table and reclaim.
- **Accessibility.** axe ran on the Studentside block and the open form at 1440 px and 320 px, with reflow checks.
- **Slow tests (over 1 s).** `test_adjustment.py::test_a_lecturer_gives_a_student_more_time_and_the_game_follows_at_once` takes 2.8 s and `…::test_the_form_is_judged_and_only_students_of_the_class_have_a_studentside` takes 2.3 s. Each plays one short Class game through the api. The new games tests stay under 1 s (0.5–0.6 s).

**Decisions taken instead of the founder.**
- The api accepts only the four offered factors (1, 1,5, 2, 3) and refuses anything else with `not_offered`. The epic only says "refuses a factor under 1".
- A share equal to the class share is stored as the class's own. «Som klassen» with the class share deletes the row. A share left above a class share lowered later reads as the class's own.
- The Studentside and its api use `class_sessions.manage` (Lecturer/owner). An Assistant lecturer gets the same 403 as an outsider and sees no name link and no Spillstyring line.
- `games` reads the factor through `sessions.service.time_factors` with a function-level import, which avoids a circular import. `test_imports.py` allows exactly that module.
- After a Pause ended by an Order, the agreed time kept as insert time is read back when it differs from the due time. A raised factor may withdraw an insert right that had already arisen (FR-89 floor).
- `_next_due` reads every waited-for Seat's own due time; Story 8.1 offered this option.
- Draft copy `[ASSUMPTION]`: «Klasseøkt n» under the name, the link's label «Studentside for Jonas», the refusal and failure lines.
- The orchestrator asked for the implementation to be done in the builder's own context, so the skill's implementation subagent was not used.

**Residual risks.**
- If the recompute after a committed save fails on a database error, the save answers 500 and the times stay old until the next save or recompute.
- The request log carries the Studentside path with the Student's id.
- The visual check is left to the separate visual agent.
