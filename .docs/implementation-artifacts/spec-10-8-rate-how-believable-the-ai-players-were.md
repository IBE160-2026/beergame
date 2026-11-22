---
title: 'Story 10.8: Rate how believable the AI players were'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: 'ff8792a6a6aa30e9f0e3d54df6768d6aea16c600'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-10-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-10-7-read-the-replay-walkthrough.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** Nothing asks a Student how believable the AI players' ordering felt (FR-70) or whether they would have wanted another round (FR-50, SM-10), so the people behind the product cannot judge the AI players or the repetition.

**Approach:** `games` stores a believability rating (1–5) once per Student and Game in a new table `believability_ratings` with the Game's purpose and its frozen AI mode (`session_runtime.ai_mode`); `GET/POST /api/me/games/{id}/believability` (sessions routes, own game via `_own_locked_game`) say whether it is offered and store it. `replay` stores the another-round answer once per Student and Class session in `replay_another_round`; `GET/POST /api/me/games/{id}/another-round` for the Replay's own Student. A shared `components/believability-question.tsx` (labelled radio group, five 44 px segments, end points in words) shows on «Spillet er ferdig» under «Gå til Debrief» when offered, and both questions show under the ready Replay-gjennomgang.

## Boundaries & Constraints

**Always:** Offered only on a finished Game that was not closed (`end_reason` NULL) whose policy row allows it: new `games.policy` column `believability` = `ai_held` (Class game: some `seat_weeks` row with occupant `llm` or `rule_based`), `always` (Replay), `never` (Lecturer test, simulation); no purpose compared outside the policy (AD-13). A second answer replaces nothing: `409 already_answered`; not offered: `409 not_offered`; rating outside 1–5: 422. Another-round: closed Replay `409 replay_closed`, unfinished `409 replay_not_finished`, second answer `409 already_answered`. Every endpoint returns a rating only to the Student who gave it; anyone else, staff and Admin included, gets 403 `forbidden`. Both tables have no name column, are written once (update trigger), and no staff screen, export or report reads them (Epic 14 aggregates). Nothing blocks: unanswered questions change no step, gate or link. UI copy in `nb.ts`, draft lines in `open-assumptions.md`. Send buttons are secondary (the screen keeps its one primary).

**Never:** no aggregation or staff view (Epic 14); no change to existing exports; no new event topic; no game played per test; no screenshots.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Class game with an AI Seat | finished, a Week held by AI | GET `{offered: true, rating: null}`; POST 4 → 201 `{offered: true, rating: 4}`, row with purpose `class`, the AI mode | — |
| Second answer | rating stored | POST 2 → 409 `already_answered`; GET still 4 | page shows the saved line |
| No AI Seat ever | finished, every row `student` | `{offered: false}`; POST 409 `not_offered` | question not rendered |
| Not finished / closed Replay | running, or `end_reason` set | `{offered: false}`; POST 409 `not_offered` | — |
| Replay | finished | believability offered; another-round GET `{answer: null}`, POST true → 201, again → 409 | — |
| Another reader | other Student, Lecturer, Admin, bad id | 403 `forbidden` on all four endpoints | access as today |

</intent-contract>

## Code Map

- `backend/app/modules/games/{models.py games/seat_weeks, repo.py get_game, policy.py GamePolicy/POLICIES, service.py, schemas.py SessionRuntime.ai_mode/OccupantKind}` -- table, offered rule, store.
- `backend/app/modules/sessions/{service.py:1855 _own_locked_game/1963 student_result_of (pattern), routes.py:843 result route (pattern), schemas.py:496 alias pattern}` -- own-game checks and the believability routes.
- `backend/app/modules/replay/{models.py, repo.py replay_owner, routes.py, walkthrough.py:388 owner/closed/not-finished checks, README.md}` -- another-round table and routes.
- `backend/migrations/versions/0118_replay_walkthrough.py` -- immutable-trigger pattern; new 0119.
- `backend/app/platform/events/registry.py` -- `games.rate_believability`, `replay.answer_another_round` (no topics).
- Tests: `tests/sessions/test_play.py running`, `tests/replay/test_start.py start`, `tests/replay/test_finish.py` (dev quiz route, short Replay), `tests/test_migrations.py` (HEAD 0118), `tests/games/test_policy*.py`.
- Frontend: `components/segmented-choice.tsx` (radio group to reuse), `components/action-error.tsx`, `lib/api/mutation.ts useAction`, `modules/games/{game-end.tsx, api.ts myGameKey}`, `modules/replay/{walkthrough-page.tsx Ready, api.ts}`, `copy/nb.ts` (`replay`, `games.play.end`), e2e `game-end.spec.ts` (stubs + live two-Uke test), `replay-walkthrough.spec.ts`.

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0119_ratings.py`, `games/models.py`, `replay/models.py` -- `believability_ratings(game_id, user_id) pk, purpose, ai_mode, rating 1–5, created_at` and `replay_another_round(user_id, class_session_id) pk, answer, created_at`, both immutable.
- `games/policy.py` -- `believability` column; `games/{repo,service,schemas}.py` -- `believability(game_id, user_id)`, `rate_believability(...)`, `BelievabilityRefused`.
- `sessions/{service,routes,schemas}.py` -- GET/POST `/api/me/games/{id}/believability` (`getMyBelievability`, `rateMyBelievability`).
- `replay/{questions.py (new), routes.py, schemas.py, README.md}` -- GET/POST `/api/me/games/{id}/another-round`.
- `backend/tests/games/test_believability.py` (new) -- one module-scoped setup: a started Class game (seat_weeks with an AI row) marked finished in SQL, a one-Uke Replay; matrix rows above, plus policy and registry asserts. `test_migrations.py`.
- Frontend: `components/believability-question.tsx` (new), `modules/games/{believability.tsx (new), api.ts, game-end.tsx}`, `modules/replay/{another-round.tsx (new), api.ts, walkthrough-page.tsx}`, `copy/nb.ts`, `open-assumptions.md`, api client; Vitest for the component.
- e2e: `game-end.spec.ts` (stubbed offered/answered/not offered at 320/360/1440 with axe, keyboard; the live test answers it for real), `replay-walkthrough.spec.ts` (both questions on ready, not on pending).

**Acceptance Criteria:**
- Given a Student on the ready Replay-gjennomgang, then the five-point question and the yes/no question follow the walkthrough, both optional; leaving them changes no step.
- Given «Spillet er ferdig» of a Class game with an AI-held Seat, then the five-point question stands below «Gå til Debrief»; with no AI Seat it is absent.
- Given an answer, then it is stored once with purpose and AI mode; a second answers 409 and the first stays.
- Given staff or another Student, then no endpoint returns the rating (403).
- Given the questions at 320/360/1440 px, then axe passes, the scale is a labelled radio group operable by arrow keys, each option ≥ 44 px, end points labelled in words.

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
Two layers (sonnet, per the runbook): blind hunter and edge-case hunter. Both hand-backs failed; findings were read from `review-{blind,edge}-10-8.md` in the scratchpad.
- verdicts: 20 findings — high 0, medium 0, low 12, false 8, maybe-false 0
- findings:
  - `[low]` `[reject]` (blind 1) `believability_ratings.user_id` has no FK to `users`, unlike `replay_another_round` — `games` keeps no FK to `users` anywhere (`seat_occupancy`, `time_acceptances`); the row holds an id only, and erasure on request (FR-76) is its own story.
  - `[low]` `[patch]` (blind 2) the write-once triggers are untested; migration hard-codes the purpose list — the test now updates both tables and expects `RestrictViolation`; a migration freezes its constraint values by design (rejected part).
  - `[low]` `[reject]` (blind 3) registry: `replay.answer_another_round` listed, the believability write not — `test_registry` requires every `games.*` entry to be a `games.commands` command; the asymmetry is documented in the registry and `ratings.py`.
  - `[low]` `[reject]` (blind 4) aggregates in a small Class could identify a Student; no test that staff cannot read the tables — no staff endpoint, export or report reads them (none exists); aggregation and its thresholds are Epic 14's.
  - `[false]` `[reject]` (blind 5) an inactivity Takeover of the Student's own Seat counts as AI-held — the story's rule is "at least one AI-held Seat in any Week", which that is; the other Students did face it.
  - `[low]` `[reject]` (blind 6) a full Game row is read to answer — one read on a finished screen.
  - `[false]` `[reject]` (blind 7) the diff omits generated files and bundles 10.7 material — the generated client was left out of the review diff on purpose; the `epic-10-context.md` edit is the recompile step-01 requires (planning docs were newer); no 10.7 file is in the diff.
  - `[false]` `[reject]` (blind 8) no screenshots — the runbook gives the visual check to a separate agent.
  - `[low]` `[patch]` (blind 9) «To frivillige spørsmål» heads one question when the other is not asked; no retry on a failed read — heading is now «Frivillige spørsmål»; a failed read leaving an optional question out is the design (rejected part).
  - `[low]` `[reject]` (blind 10) `AnotherRound` repeats `BelievabilityQuestion`'s pattern; `as Scale` cast — two small call sites; a shared answer-once abstraction adds surface for no user harm.
  - `[low]` `[reject]` (blind 11) no Vitest for `BelievabilityBlock`/`ReplayQuestions` — their behaviour is pinned by Playwright (offered, answered, not offered, both questions, 409 on the live stack).
  - `[low]` `[reject]` (blind 12) one long backend test, raw SQL state, no concurrency test — by the founder's speed rule (no game per test); the second answer's 409 is the `on_conflict_do_nothing` path, tested.
  - `[low]` `[patch]` (blind 13) README says the believability routes are `games`'; `__all__` order; 403 for a non-owner of an unfinished Replay not asserted — README now names `sessions/routes.py`; the rest rejected (cosmetic; the owner check runs before the finished check, tested for a finished Replay).
  - `[false]` `[reject]` (edge 1) stored `ai_mode` is the frozen session mode, not who ordered — the story asks for "the AI mode of the Class session".
  - `[low]` `[reject]` (edge 2) another-round skips the Class enrolment check that believability applies — the same owner rule as the walkthrough (Story 10.7) it follows; an archived Class's Student answering their own question harms no one.
  - `[false]` `[reject]` (edge 3) `policy()` raises for a purpose without a row (makeup) — no such Game can exist: `games.commands.create` needs the row.
  - `[low]` `[reject]` (edge 4) = blind 1.
  - `[false]` `[reject]` (edge 5) a stale `sent` ref moves focus on a later refetch — only after this Student pressed «Send svar» on this page; moving focus to the line that now answers it is the intended behaviour.
  - `[false]` `[reject]` (edge 6, claim) the Code Map lists `games.rate_believability` in the registry — the registry test forbids it (blind 3); the fix would be a spec edit.
  - `[false]` `[reject]` (edge 7, claim) = blind 5.

## Design Notes

«Offered once»: the question shows until answered; after it, one line «Takk. Du svarte 4 av 5.» replaces it (the Student's own answer only). Choose then «Send svar» (a stray tap is not final). The scale reuses Valgknapper (`SegmentedChoice`) with labels 1–5; under it «1: ikke troverdige» left and «5: svært troverdige» right, tied to options 1 and 5 by `aria-describedby`. A read failure hides the block (optional question, never a page error). Ratings key the Game, so the Class game and the Replay each get one.

## Verification

**Commands:**
- `uv run pytest tests/games/test_believability.py tests/test_migrations.py tests/games/test_policy.py -q` -- pass, new test file under 3 s
- `npm run typecheck && npx vitest run src/components` -- pass
- full gate per runbook before commit

## Auto Run Result

Status: done

**Summary.** Believability (FR-70): `games` stores one answer (1–5) per Student and Game in `believability_ratings` (migration 0119; id only, purpose, the Game's frozen `session_runtime.ai_mode`, created_at; update trigger) through `games.service.believability` / `rate_believability` (`games/ratings.py`). A new `games.policy` column `believability` decides who is asked: `ai_held` (Class game: some Decision log row by an `llm` or `rule_based` occupant), `always` (Replay), `never` (Lecturer test, simulation); a Game not finished or closed at the Test deadline asks nobody. `GET`/`POST /api/me/games/{id}/believability` (`getMyBelievability`, `rateMyBelievability`) live in `sessions/routes.py` beside the result route and use its own-game check (`_own_locked_game`): 403 for anyone else, 409 `not_offered` / `already_answered`, 422 outside 1–5. Another round (FR-50, SM-10): `replay_another_round` (one per Student and Class session, update trigger) via `replay/questions.py`, `GET`/`POST /api/me/games/{id}/another-round` for the Replay's own Student (403 otherwise; 409 `replay_closed`, `replay_not_finished`, `already_answered`). Web: shared `components/believability-question.tsx` (Valgknapper 1–5, ≥ 44 px, end points in words as visible text and as descriptions of options 1 and 5, «Send svar» secondary, then «Takk. Du svarte 4 av 5.» with focus moved there); `modules/games/believability.tsx` renders it under «Et frivillig spørsmål» below «Gå til Debrief» on «Spillet er ferdig» when offered; `modules/replay/questions.tsx` puts «Frivillige spørsmål» (believability + «Ville du spilt en runde til?» Ja/Nei) under the ready walkthrough. Nothing blocks; a failed read leaves an optional question out. No staff screen, export or report reads either table.

**Files.** Backend: `migrations/versions/0119_ratings.py` (new); `games/{ratings.py (new), models.py, policy.py, repo.py, schemas.py, service.py}`; `sessions/{routes,schemas,service}.py`; `replay/{questions.py (new), models.py, repo.py, routes.py, schemas.py, README.md}`; `platform/events/registry.py`. Tests: `tests/games/test_believability.py` (new), `tests/games/test_policy.py`, `tests/test_migrations.py` (HEAD 0119). Frontend: `components/believability-question.tsx` + `.test.tsx` (new), `modules/games/{believability.tsx (new), api.ts, game-end.tsx}`, `modules/replay/{questions.tsx (new), api.ts, walkthrough-page.tsx}`, `copy/nb.ts` (`believability`, `replay.questions`), regenerated `lib/api/{openapi.json,schema.ts}`; e2e `game-end.spec.ts`, `replay-walkthrough.spec.ts`. Docs: `open-assumptions.md` (draft copy), `epic-10-context.md` (recompiled: planning docs were newer).

**Decisions the founder would otherwise take.** (1) «Offered once» = asked until answered, then one line with the Student's own answer; never asked again. (2) Choose, then «Send svar» (secondary, so each screen keeps one primary); a stray tap is not the answer. (3) A Class game asks when any Decision log row was ordered by an AI occupant (a Takeover counts); a Lecturer's test Game never asks; a closed Replay never. (4) The stored AI mode is the Game's frozen `session_runtime.ai_mode` (the Class session's, also for a Replay with cost-limit Rule-based Seats). (5) The believability write lives in `games/ratings.py`, not `games.commands` (no game state, no event); its routes sit in `sessions/routes.py` with the other `/me/games` routes. (6) `believability_ratings.user_id` has no FK (games convention); `replay_another_round` cascades like `replays`. (7) Another-round uses the walkthrough's owner rule (no enrolment re-check). (8) Heading «Frivillige spørsmål» on the walkthrough, «Et frivillig spørsmål» on «Spillet er ferdig»; all copy is draft (`open-assumptions.md`). (9) Implemented in this context, not by a sub-agent; two sonnet review layers (blind, edge case), per the runbook.

**Review.** 20 findings: 3 patched (low: trigger test for both tables, heading wording, README route location), 0 deferred, 17 rejected with reasons in the triage log (9 low, 8 false). `followup_review_recommended: false` (no high or medium patched).

**Verification.** Full backend suite `--maxprocesses=8` after the last change: 3150 passed, 4 skipped (124.1 s). ruff format/check clean. Frontend typecheck, full Vitest 1040 passed, `lint:colours`, `check:copy`, `next build` (image) passed. Playwright `--workers=4` after the stack rebuild: game-end, replay-walkthrough, replay-close/finish/play/start, class-session-replay, homes, student-home, graph-over-table, game-start: 118 passed, none flaky; axe and reflow at 320/360/1440 on the questions; the live two-Uke game answers the question on the real stack (201, then 409). New test over 1 s: `tests/games/test_believability.py::test_students_rate_the_ai_players_once_and_only_they_read_it` (2.7–3.5 s: one started Class game marked finished in SQL, two one-Uke Replays). No test failed once and passed on rerun.

**Residual risks.** Draft copy. Small-Class aggregates could identify a Student (Epic 14 must set a floor). A Takeover of the Student's own Seat makes the Class game ask.
