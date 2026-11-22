---
title: 'Story 8.5: Put an AI player in one Seat from Spillstyring'
type: 'feature'
created: '2026-11-21'
status: 'done'
baseline_revision: '09de0c12602c3aa5854ba0b9260f01754ae3570e'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-8-context.md'
warnings: [oversized]
deferred: []
---

<intent-contract>

## Intent

**Problem:** A Lecturer or Assistant lecturer cannot hand an absent Student's Seat to an AI player; only the sweep's automatic Takeover (Story 8.2) does, after the Inactivity limit. A Lab-hour group stalls when one Student leaves, and the deferred decision on how a lost race names who acted first is still open.

**Approach:** Extend `games.commands.takeover` and `rules.can_take_over` with a `staff` actor (reason `takeover_staff`, `actor_user_id` = the staff member, audit row). A new route `POST /api/games/{game_id}/seats/{role}/takeover` (policy `games.takeover`, Lecturer and Assistant lecturer, Class staff scope) exposes it. Spillinnsikt gets a «Spillstyring» block under the Seats with one secondary button per Student-held Seat, and the Varselbånd gets «Sett inn KI-spiller for Noah». A lost race answers 409 `takeover_exists` with `fields.acted_by`/`acted_at`, and the Oversikt and Spillinnsikt name who put the AI player in.

## Boundaries & Constraints

**Always:**
- Only `games.commands.takeover` writes the occupancy row, under the Game row lock in one transaction with `_commit_change`, the 8.2 events, notices (`takeover_notice`, dedupe per Seat and the row's `from_week`) and `_settle`. Staff actor: reason `takeover_staff`, `actor_user_id` = staff id, and `platform/audit.record(actor, "seat.taken_over", {game_id, seat_id, occupancy_id}, {reason, from_week}, now)` in the same transaction.
- `rules.can_take_over(game, turn, actor, now, *, guided, seat)` stays the one check. `seat` is the Seat's latest occupancy row. Not running gives `game_not_running`; a policy without inactivity Takeover gives `takeover_not_allowed`; a latest row that is not a Student's gives `takeover_exists` when its reason is a Takeover reason, else `seat_not_student_held`. For `system`: `order_exists` and `takeover_not_due` as today. For `staff`: no due check, and ordered is allowed.
- Staff on a Seat that has not ordered (`has_ordered`; in a Guided Week, not viewed): the row is `from_week = week`, with `players.ensure_order` and the LLM deadline as in 8.2. Staff on a Seat that has ordered: `from_week = week + 1`, with no Order now (the pattern of `switch_to_rule_based`).
- 409 `takeover_exists` carries `fields.acted_by = {kind: staff|student|system, user_id|null}` (from `takeover_staff`/`takeover_peer`/`takeover_inactivity` and `actor_user_id`) and `fields.acted_at` (the row's `created_at`, ISO). No name in any log line. The sweep treats `takeover_exists` as a race.
- Route: 403 `forbidden` for a non-staff User, another Class, an unlisted Game or an unknown id. 404-type command refusals also read 403. 422/409 `seat_not_found` for an unknown Role. Success returns the refreshed `GameInsightOut`.
- `InsightSeatOut` gains `takeover: "this_week" | "next_week" | null` (the server decides; set only on a Student-held Seat of a running Game whose policy allows it) and `mark_by: str | null`. `OverviewSeatOut` gains `mark_by`. The name of a `takeover_staff`/`takeover_peer` actor is resolved now (Student or Class staff), else null. `game_summaries` occupants store `actor_user_id`; it joins the 7.1 recomputation.
- UI copy in `nb.ts`; strings not in the epic are marked `[ASSUMPTION]`. Secondary buttons at least 44 px, full width below 1024 px. Success: «KI-spiller satt inn for Jonas.» replaces the button (`tabindex=-1`, focused, `role="status"`). `takeover_exists`: the line naming who acted first replaces the button and takes focus. Other failures: inline `ActionError`, button active. Mark text «KI satt inn av {name}» when `mark_by` is set.
- Spillstyring shows only while the game's status is `running`/`waiting`. The Varselbånd's button is secondary («Send Melding» stays primary). The consequence caption sits under the band text, and the band wraps below 1024 px. An Assistant lecturer sees the same per-Seat and band actions (there are no other actions yet).

**Never:** no peer Takeover (8.8), Pause (8.6/8.7), batch fill (8.12), Tilrettelegging line (8.9), start or «I rommet» actions. No dialog. No change to earlier occupancy or `seat_week` rows. No change to the demo Class. No waiting on real time in tests.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Not ordered | Student Seat, Week 3 open, not ordered | row `takeover_staff`, actor = staff, from Week 3, AI Order placed, notices, audit row | — |
| Ordered | Seat ordered in Week 3 | row from Week 4; Week 3 Order untouched; insight `takeover` null | — |
| Guided, unviewed | Week 1 Guided, one Student never opened it, others did | row from Week 1; Week 1 completes and Week 2 opens | — |
| Lost race | Seat already has a Takeover row | — | 409 `takeover_exists`, `acted_by` {staff, id}, `acted_at` |
| AI seat | Seat initially AI / guard switch | — | 409 `seat_not_student_held` |
| Not started / finished | lifecycle not running | no Spillstyring | 409 `game_not_running` |
| Assistant | Assistant lecturer of the Class | allowed | — |
| Outsider | Student, other Class's Lecturer | — | 403 `forbidden` |

</intent-contract>

## Code Map

- `backend/app/modules/games/rules.py:36-72` -- `TakeoverActor`, `can_take_over` (add `staff`, `seat` arg, `takeover_exists`).
- `backend/app/modules/games/commands.py:1700-1788` -- `takeover`; `CommandError.fields` (line 114) becomes `Mapping[str, Any]`; `switch_to_rule_based` (1647) is the from-next-Week precedent; `_unviewed_guided_student`.
- `backend/app/modules/games/repo.py` -- `seats_with_occupant`/`_latest_occupancy` (101-135) add `actor_user_id`, `created_at`; `TAKEOVER_REASONS` (538).
- `backend/app/modules/ops/sweep.py:116` -- `TAKEOVER_RACES` plus `takeover_exists`.
- `backend/app/modules/games/{overview.py:80-90 recompute occupants, service.py:644 SummarySeat/719 reader, insight.py:74 InsightSeat/251}` -- `actor_user_id`, insight `takeover`.
- `backend/app/modules/sessions/{overview.py game_insight/_game_out, schemas.py InsightSeatOut 959/OverviewSeatOut, routes.py ~296}` -- fields, `take_over_seat` service, route.
- `backend/app/modules/classes/service.py` -- `staff_names(class_id, ids, session)` via `repo.staff_of` + `identity.people`.
- `backend/app/platform/authz.py:82-154` -- `games.takeover` in `POLICIES` and `CLASS_STAFF_ROLES`.
- `frontend/src/modules/games/{api.ts, insight-page.tsx SeatItem, insight.ts seatMarkText, overview.ts:144-163 marks, overview-band.tsx, reclaim-view.tsx pattern}`, `frontend/src/copy/nb.ts:2397 marks`, `frontend/src/lib/api/{openapi.json,schema.ts}`.
- Tests: `backend/tests/games/test_takeover.py` (`class_game`, `due_of` setup), `tests/sessions/test_takeover_view.py`/`test_reclaim_view.py` (api pattern), `tests/games/test_game_summaries.py`; e2e `frontend/e2e/takeover.spec.ts`, `reclaim.spec.ts`, `support/live-game.ts`.

## Tasks & Acceptance

**Execution:**
- `rules.py`, `commands.py`, `repo.py`, `sweep.py` -- the staff actor, `takeover_exists` with acted fields, the audit row, from-next-Week.
- `games/{overview,service,insight}.py`, `sessions/{schemas,overview,routes}.py`, `classes/service.py`, `authz.py` -- the fields, name resolution, the route.
- `frontend/src/lib/api/{openapi.json,schema.ts}` -- regenerate.
- `frontend/src/modules/games/{spillstyring.tsx (new), insight-page.tsx, overview-band.tsx, api.ts, insight.ts, overview.ts}`, `copy/nb.ts` -- the block, the band action, the marks with name.
- Backend tests `tests/games/test_staff_takeover.py` (matrix rows, audit, events, recomputation) and `tests/sessions/test_staff_takeover_view.py` (route: Lecturer, Assistant, outsider, 409 shape, the Guided api test). Vitest for the takeover-control states and mark text. e2e `frontend/e2e/spillstyring.spec.ts`: press, then the focused line; `takeover_exists` names who; band button; axe and no horizontal scroll at 320 and 1440.

**Acceptance Criteria:**
- Given a running Class game on Spillinnsikt, when a Lecturer or Assistant lecturer opens it, then «Spillstyring» sits under the Seats, and each Student-held Seat has «Sett inn KI-spiller for Jonas» with the matching consequence directly above it. A finished game shows none.
- Given the press, when the api commits, then «KI-spiller satt inn for Jonas.» replaces the button and takes focus, and the Seat's mark reads «KI satt inn av {staff name}» on Spillinnsikt and the Oversikt.
- Given the Varselbånd with a game closest to Takeover, when it shows, then it has the secondary «Sett inn KI-spiller for Noah» with the consequence caption under the band text.
- Given 320 and 1440 px, when Spillinnsikt with Spillstyring shows, then there is no horizontal scroll and axe passes.

## Spec Change Log

## Review Triage Log

### 2026-11-21 — Review pass
- Layers: blind hunter, edge-case hunter, verification gap, intent alignment (Sonnet, as the orchestrator asked). All four hand-backs dropped; findings read from `review-{blind,edge,verification,intent}-8-5.md` in the session scratchpad.
- verdicts: 44 findings — high 0, medium 2, low 33, false 9, maybe-false 0
- findings:
  - `[medium]` `[patch]` blind-1: a staff press on a Seat that has ordered the last Week wrote a row from a Week that never opens, with notices and «satt inn». Fixed: `takeover` now refuses `order_exists` there, and `_takeover_from` offers no `next_week` in the last Week. `order_exists` has its own copy, and `test_the_seat_that_has_ordered_the_last_week_is_refused` covers it.
  - `[false]` `[reject]` blind-2: "has ordered" is decided twice. For a Student-held turn, `insight._ordered_at(turn, STUDENT, guided) is not None` is equivalent to `rules.has_ordered` (Guided: ordered and viewed; otherwise ordered).
  - `[low]` `[reject]` blind-3: the band's caption is fixed to «fra denne Uka». By definition the band's Seat is one the game waits for (not ordered). Only a seconds-old stale view could differ, and the live read replaces it.
  - `[low]` `[reject]` blind-4: the band's result line stays after the band moves on. It is the action's result for the game it names, so it stays true; a new press replaces it.
  - `[low]` `[reject]` blind-5: a press refused for another reason keeps its row. The inline line («Ingen student har dette setet nå.») then says why, and dropping the row would hide it.
  - `[low]` `[patch]` blind-6: the next-Week row reads as in force at once, and a Reclaim before that Week was untested. The design keeps the future-dated row (Design Notes). Added `test_a_reclaim_before_the_next_week_keeps_the_seat_with_its_student`.
  - `[low]` `[reject]` blind-7: `acted_by` is not typed in OpenAPI. The envelope's `fields` is a free map for every route (AD-19), and the route docstring documents it.
  - `[false]` `[reject]` blind-8: other callers match `seat_not_student_held` for a lost race. A grep finds only `ops/sweep.py`, which now also lists `takeover_exists`.
  - `[low]` `[patch]` blind-9: a parametrized row overrode its own expectation. The `guard_switch` row now states `seat_not_student_held`, and the override is gone.
  - `[low]` `[patch]` blind-10: the audit row did not name whose Seat it was, and it read the clock twice. The target now carries the Student's `user_id`, which the audit page's labeler names, and the row uses the command's `at`. Not auditing refused presses is rejected: FR-3 covers a Takeover by a person.
  - `[low]` `[reject]` blind-11: draft copy is marked `[ASSUMPTION]`, the project convention. «fra neste Uke» without the reclaim sentence, and «Uka/Uke», are the epic's verbatim copy.
  - `[false]` `[reject]` blind-12: an import cycle, and a 403 after a commit. `sessions/service.py` already imports `games.commands`. `head.listed` is fixed by purpose, so the post-commit read cannot turn None. The route always passes the staff id.
  - `[low]` `[patch]` blind-13: the risky paths were thin. Added tests for an LLM occupant after the Order (no AI deadline on the Student's turn), a Guided Week opened (next Week) or not opened (this Week), the last Week, and staff who left the Class (`mark_by` None).
  - `[low]` `[reject]` blind-14: the generated files are left out of the diff by design. The extra `open_week` and `actor_names` reads are one query each on a staff page.
  - `[medium]` `[patch]` edge-1: as blind-1; patched with it.
  - `[low]` `[patch]` edge-2: a second Takeover in the same Week, after a Reclaim, shared the notice dedupe key and was not told. The key is now per occupancy row (`takeover_notice:<occupancy>:<user>`), and the 8.2 test is updated.
  - `[low]` `[reject]` edge-3: as blind-5.
  - `[low]` `[patch]` edge-4: the `takeover_exists` line first read «En KI-spiller er allerede satt inn.», then changed. The line now waits for the read again (`invalidateQueries` awaited) before it shows and takes focus.
  - `[low]` `[reject]` edge-5: as blind-3.
  - `[low]` `[reject]` edge-6: as blind-4.
  - `[false]` `[reject]` edge-7: a committed Takeover answered 403. Unreachable, as blind-12.
  - `[false]` `[reject]` edge-8: the spec claims an unknown Role gives `seat_not_found`. An invalid Role is refused 422 by validation, and every Game has all four Seats; the only fix would edit this spec.
  - `[false]` `[reject]` edge-9: the claim that Ordered gives `takeover` null. The matrix row describes the Seat after the press, when it is AI-held and `takeover` is null (`test_staff_takeover_view.py`).
  - `[low]` `[patch]` verification-1: as blind-13 (LLM and Guided cases added).
  - `[low]` `[patch]` verification-2: the band's lost-race name lookup was untested. Extracted `markBy(items, game, role)` and covered it in Vitest.
  - `[low]` `[patch]` verification-3: the inline refusal copy was untested. A Vitest test now checks each code's line and the fallback.
  - `[low]` `[patch]` verification-4: the `actor_names` exclusion was not pinned. The api test now removes the Assistant lecturer and asserts `mark_by` is None.
  - `[low]` `[patch]` verification-5: the 403 for an unlisted Game was untested. A `lecturer_test` Game row is added to the refusal list.
  - `[medium]` `[patch]` verification-other-1: as blind-1.
  - `[low]` `[patch]` verification-other-2: as blind-9.
  - `[false]` `[reject]` verification-other-3: the fixture re-export via `__all__` is the pattern every api test module here uses.
  - `[low]` `[patch]` verification-other-4: as blind-6.
  - `[low]` `[reject]` intent-1: only `takeover_exists` carries `acted_by`. The other listed codes belong to commands built by later stories (8.6, 8.7, 8.10), and the spine note sets the shape they will use. `seat_not_student_held` is never a person acting first.
  - `[false]` `[reject]` intent-2: the `actor_user_id` keyword. It takes the same inputs (Game, Seat, staff member) as the epic's `takeover(game, seat, actor)`.
  - `[low]` `[reject]` intent-3: the Student-side warning is not exercised. It is Story 8.2's unchanged path, read from the same occupancy row.
  - `[low]` `[reject]` intent-4: the Seat reads as AI-held before its Week. This is the documented design, and the Reclaim interplay is now tested.
  - `[low]` `[reject]` intent-5: there is no Assistant lecturer e2e. The rights live in the api policy, which is tested; the page has no role-specific UI.
  - `[false]` `[reject]` intent-6: authz refusal of other actions. No other Spillstyring action exists yet.
  - `[low]` `[reject]` intent-7: the Oversikt mark is not asserted in e2e. The api test asserts `mark_by` on the Oversikt, and Vitest asserts the words.
  - `[low]` `[reject]` intent-8: full width is measured at 320 px only. The class flips at the 1024 px breakpoint, and Vitest asserts the class.
  - `[low]` `[patch]` intent-9: the decision was not noted against the spine's Deferred item. Added a *Decided in Story 8.5* sentence to «Remaining Spillstyring commands and sweeps» in `ARCHITECTURE-SPINE.md`.
  - `[low]` `[reject]` intent-10: no test checks that logs carry no names. `seat_taken_over` logs ids and the actor kind only, as before.
  - `[low]` `[patch]` intent-11: as verification-3.
  - `[low]` `[reject]` intent-12: as blind-11.
- Matrix audit (all ran and passed):
  - Not ordered: `test_a_seat_that_has_not_ordered_is_taken_from_this_week`.
  - Ordered: `test_a_seat_that_has_ordered_is_taken_from_the_next_week`, and the api test (`takeover` is `next_week`, then null once AI-held).
  - Guided, unviewed: `test_a_lecturer_puts_an_ai_player_in_the_seat_of_a_student_who_never_opened_uke_1` and `test_in_a_guided_week_opening_it_is_ordering_it`.
  - Lost race: `test_two_presses_at_once_append_one_row_and_name_the_first`, the api 409, and `spillstyring.spec.ts` (stale page).
  - AI seat: the pure test, the command test and the api test.
  - Not started / finished: the pure test, the command test, and Vitest (no block).
  - Assistant and Outsider: `test_an_assistant_may_and_anyone_else_is_refused`.

## Design Notes

The from-next-Week case appends a future-dated row, as `switch_to_rule_based` already does. The Seat then reads as AI-held at once on the Oversikt and Spillinnsikt (it was the staff member's decision), while `week_turns_with_occupant` keeps the Student in force for the open Week. A Reclaim before the next Week appends a later row with the same `from_week`, which wins. Conflict decision (the epic's deferred item): the 409 body names the kind and id only. The web app reads the name from the view it refetches (`mark_by`), so names never travel in errors or logs.

## Verification

**Commands:**
- `cd backend && uv run pytest -q tests/games/test_staff_takeover.py tests/sessions/test_staff_takeover_view.py tests/games/test_takeover.py tests/games/test_game_summaries.py` -- pass
- `cd frontend && npx vitest run src/modules/games` -- pass
- Before commit: the full suites and the e2e specs named in the runbook.

## Auto Run Result

Status: done

**Summary.** A Lecturer or Assistant lecturer can now put an AI player in one Student's Seat, from Spillinnsikt or from the Varselbånd. `games.commands.takeover` takes a `staff` actor with the staff member's id. Under the Game row lock and in one transaction it appends a `takeover_staff` occupancy row with the staff member in `actor_user_id`, writes the audit row `seat.taken_over` (target: game, Seat, occupancy row and the Student), sends Story 8.2's events and `takeover_notice`s, then settles. A Seat whose Student has not ordered (in a Guided Week: not opened it) is taken from this Week, with `players.ensure_order` in the same transaction, so the Week can advance. A Seat that has ordered is taken from the next Week by a future-dated row. In the game's last Week that press is refused `order_exists`. `rules.can_take_over` stays the one check and now reads the Seat's latest row: a lost race answers 409 `takeover_exists` with `fields.acted_by` (`kind` `staff`/`student`/`system` and `user_id`) and `fields.acted_at`, ids only, and the sweep treats it as a race. The route is `POST /api/games/{game_id}/seats/{role}/takeover` (policy `games.takeover`, Class staff scope, 403 for anyone else and any unlisted Game) and answers Spillinnsikt. Spillinnsikt's Seats now carry `takeover` (`this_week`/`next_week`, decided by the api) and `mark_by`, and the Oversikt's Seats carry `mark_by`. These are names resolved now through `classes.actor_names` (staff or Students of the Class), and `game_summaries` stores `actor_user_id`. On the page, «Spillstyring» sits under the four Seats while the game runs. It has one row per Student Seat (Fabrikk first) with its consequence directly above the secondary «Sett inn KI-spiller for Jonas», which is full width below 1024 px. After a press, «KI-spiller satt inn for Jonas.» replaces the button and takes focus. A lost race shows «Sara har allerede satt inn en KI-spiller.», with the name read again from the view. The Varselbånd adds the consequence caption under its text and the secondary «Sett inn KI-spiller for Noah» beside the primary «Send Melding»; the result line stands under the band. Marks read «KI satt inn av Bård». The conflict decision is noted against the spine's Deferred item.

**Files changed**
- `backend/app/modules/games/{rules,commands,repo}.py`: the `staff` actor, `takeover_exists` with `acted_by`/`acted_at`, the audit row, the from-next-Week and last-Week rules, a notice key per occupancy row, and the actor and time on the latest-occupancy reads.
- `backend/app/modules/ops/sweep.py`: `takeover_exists` counted as a race.
- `backend/app/modules/games/{insight,overview,service}.py`: `takeover` per Seat, and `actor_user_id` in `game_summaries` and on insight Seats.
- `backend/app/modules/sessions/{overview,schemas,routes}.py`, `backend/app/modules/classes/service.py` (`actor_names`), `backend/app/platform/authz.py`: the route, `mark_by`, `takeover`, and the `games.takeover` policy.
- `frontend/src/modules/games/spillstyring.tsx` (new), `insight-page.tsx`, `overview-band.tsx`, `overview-page.tsx`, `insight.ts` (`markWords`), `overview.ts`, `api.ts` (`takeOverSeat`); `frontend/src/copy/nb.ts` (`spillstyring`, `insight.markedBy`); `frontend/src/lib/api/{openapi.json,schema.ts}` regenerated.
- `.docs/planning-artifacts/architecture/.../ARCHITECTURE-SPINE.md`: the Story 8.5 decision.
- Tests: `backend/tests/games/test_staff_takeover.py` (new), `tests/sessions/test_staff_takeover_view.py` (new), `tests/games/test_takeover.py` (race code, notice key), `tests/games/test_game_summaries.py`; Vitest `spillstyring.test.tsx` (new); e2e `frontend/e2e/spillstyring.spec.ts` (new), `varselband.spec.ts` and `takeover-overview.spec.ts` (band text hook `data-band-text`).

**Review.** Four Sonnet reviewers (blind, edge case, verification gap, intent alignment): 44 findings, of which 0 high, 2 medium, 33 low and 9 false.
- Patched, medium (one entry): the last-Week press.
- Patched, low: the notice key per occupancy row, the `takeover_exists` line waiting for the read again, the audit target naming the Student, the parametrized test, the spine note, and tests (LLM after the Order, Guided Week opened or not, Reclaim before the next Week, staff who left, unlisted Game 403, refusal copy, band name lookup).
- Deferred: none.
- Rejected: the rest, each with its reason in the Review Triage Log.
- Follow-up review: not recommended (patched: high 0, medium 1, low 10 entries).

**Verification** (after the patches)
- Backend full suite `--maxprocesses=8`: 2947 passed; ruff check and format are clean.
- Frontend: typecheck, Vitest (852 passed), `lint:colours`, `check:copy` and `next build` all pass.
- The stack was rebuilt after the last frontend change. Playwright `--workers=4` ran 180 tests over spillstyring, takeover, takeover-overview, reclaim, varselband, seat-status, live-updates, homes, student-home, game-insight, overview, chain-band, order-confirm, order-field, order-failures, week-table, week-advance, guided-week, game-card, cost-panel, graph-over-table, week-transition and time-proposal: 179 passed, 1 failed.
- The failure was `reclaim.spec.ts` «320 px › Ta tilbake setet…». It failed once and passed on rerun (6/6). In the run before the patches, `chain-band.spec.ts` at 320 and 360 px and `graph-over-table.spec.ts` at 360 px also failed once each and passed on rerun. The stubbed student screens are untouched by this change.
- axe passes at 320 and 1440 px on Spillinnsikt with Spillstyring and on the Oversikt with the band.
- New tests over 1 s: `tests/sessions/test_staff_takeover_view.py::test_a_lecturer_puts_an_ai_player_in_the_seat_of_a_student_who_never_opened_uke_1` (about 1.4–1.7 s: a real Class game, the Guided view, and api reads of Spillinnsikt and the Oversikt) and `test_an_assistant_may_and_anyone_else_is_refused` (about 1.2 s).

**Decisions taken instead of the founder.**
- A Seat that has ordered is taken from the next Week by a future-dated occupancy row, as `switch_to_rule_based` does. The Oversikt and Spillinnsikt show it AI-held at once, and the Student sees the 8.2 note and «Ta tilbake setet»; a Reclaim before that Week keeps the Seat.
- In the last Week, a staff press on a Seat that has ordered is refused `order_exists` («Studenten har bestilt, og det er ingen neste Uke.»), and Spillinnsikt offers no button there.
- Conflict errors carry the kind and the id only (`acted_by`, `acted_at`); the web app names the person from the view it reads again. For a system Takeover it reads «KI-spilleren har allerede tatt over setet etter ventetiden.»
- The route is `POST /api/games/{id}/seats/{role}/takeover` and answers Spillinnsikt. The api decides per Seat from when (`takeover`).
- The `takeover_notice` dedupe key is now per occupancy row (it was per Seat and Week).
- The audit row's target includes the Student whose Seat it was.
- Spillstyring shows only rows for Student Seats; with none, there is no block. The band's result line stands under the band, since the band moves on to the next game.
- Draft copy `[ASSUMPTION]`: «KI satt inn av {name}», «Fabrikk: Jonas», the refusals, the failure line, the system and unknown lines.
- Implemented in the builder's own context, as the orchestrator instructed.

**Residual risks.**
- The Seat reads AI-held on staff and Student views during the Week its Student already ordered.
- Editing `ARCHITECTURE-SPINE.md` makes `epic-8-context.md` older than a planning file, so the next story recompiles it.
- A visual check of Spillstyring and the band is left to the separate visual agent.
