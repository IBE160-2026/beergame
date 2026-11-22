---
title: 'Story 10.5: Finish the Replay and unlock the next step'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: '35aa56016b964891dd94c318dbe27a5e24f79d20'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-10-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-10-4-play-the-replay-with-the-projection-line.md'
warnings: ['oversized']
deferred:
  - summary: >-
      Staff cannot reach a Replay from the Class game's Spillinnsikt once an AI player has taken
      over the Student's Seat there.
    evidence: |-
      `replay.service.insight_links` offers the `replay` link per Seat, and `games/insight.py`
      (~line 225) attaches links to Student-held Seats only, a Story 7.7 rule that
      `tests/sessions/test_game_insight.py` pins (a taken-over Seat has no links; the Debrief's
      links behave the same). Letting a taken-over Seat carry its Student's links changes that
      rule for every provider (blind review finding 5).
    location: >-
      backend/app/modules/games/insight.py:225
    severity: medium
---

<intent-contract>

## Intent

**Problem:** A Replay played to its last Week finishes (`games.commands.finish`), but nothing records the `replay` step, so Stegene never moves on to the Individual test; the Student then sees the Class game's «Spillet er ferdig» with «Gå til Debrief» (10.4 deferral); staff cannot open it on Spillinnsikt (only listed Games); and the Debrief's finish hook and its narration sweep (`games.repo.finished_student_seats`, 10.3 deferral) treat a finished Replay as a Class game.

**Approach:** `modules/replay` registers a `games.service.on_game_finished` hook that records `progress` `replay` for the Game named by a `replays` row, in the finishing transaction (emits `user:<id>`). The play page shows a Replay's own end («Replay er ferdig», the Student's own Totalkostnad, «Gå til gjennomgangen»). A new policy column `staff_insight` opens Spillinnsikt to the Replay, labelled «Replay»; the Class game's Spillinnsikt links each Student Seat to that Student's Replay. The Debrief's narration hook, insight links and sweep filter on the Lecturer-overview policy. A local-only dev route records the steps up to `quiz_passed` so a Playwright spec can start a real Replay.

## Boundaries & Constraints

**Always:** Commands, sweeps and views ask `games.policy`, never compare a purpose (AD-13). `modules/replay` imports only `games.service`, `games.commands`, `sessions.service`, `progress.service`. The step is recorded once (`record_step` is idempotent) at database time, in the transaction that finishes the Game. The finished-game check is the existing `games.verify_finished` sweep action; it already takes every finished Game. Totalkostnad is the Student's own Seat's `total_cost` from `/result`, formatted by `formatNumber(…, {kroner: true})`. One primary button on the end screen. UI copy only in `nb.ts`, draft lines recorded in `open-assumptions.md`. The dev route is mounted only when `APP_ENV != production`, not in the OpenAPI schema.

**Never:** no walkthrough page or its data (10.7: «Gå til gjennomgangen» links to `/spill/{id}/gjennomgang`, which 10.7 builds); no close at the Test deadline or `end_reason` (10.6); no rating prompt (10.8); no hint of the last Week in any payload; no game per test; no change to the engine.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Last Order | Replay in its last Week, Student orders | 204; Game `finished`; `progress_steps` has `replay` with `at` (DB time); `user:<id>` emitted; Hjem: Replay `done`, Individuell test `current`, Replay block `status: finished` | — |
| Finish again / Class game finish | any other finish | no `replay` step for a Game no `replays` row names | — |
| Order after finish | POST order on the finished Replay | 409 | `game_finished` (or the play route's own 409) |
| Read again | GET card, `/result` | 200; `/play` not offered (`status: finished`) | — |
| Finished-game check | sweep after finish | `game_checks` row for the Replay, `ok` | violation logged as for any Game |
| Spillinnsikt | staff of the Class GET `/api/games/{replay}/insight` | 200, `replay: true`, `game_number: null`, three Seats `ai` | other Class / Student → 403 |
| Class game insight | finished Class game, Student with a Replay | that Seat has link `{kind: "replay", href: /klasseokter/{s}/oversikt/spill/{replay}}` | none without a Replay |
| Debrief narration | Replay finishes, AI text pin on | no narration job; sweep `finished_student_seats` leaves it out | — |

</intent-contract>

## Code Map

- `backend/app/modules/games/commands.py:1653 finish` -- calls `run_finish_hooks` in the finishing transaction (row locked).
- `backend/app/modules/games/service.py:629-680 FinishedGame/on_game_finished/run_finish_hooks`, `:795 ClassGameHead`, `:825 class_game_head`, `:442 own_game` (Replay rule: `class_session_game`, no `game_number`, not `played_by_staff`).
- `backend/app/modules/games/policy.py` -- add `staff_insight` (class, replay true).
- `backend/app/modules/games/repo.py:956 finished_student_seats` -- add `_listed()`.
- `backend/app/modules/debrief/narration.py:98 _defer_on_finish`, `debrief/insight.py:39 links` -- filter on `policy(purpose).lecturer_overview`.
- `backend/app/modules/sessions/overview.py:289 game_insight` (refuses `not head.listed`), `sessions/schemas.py:1088 GameInsightOut`.
- `backend/app/modules/replay/{service,repo}.py` -- finish hook, insight link provider; new `dev.py`; `main.py:115` dev mounts.
- `backend/app/modules/progress/service.py:43 record_step(within=)`.
- `backend/app/modules/ops/sweep.py:144` -- `games.verify_finished` over every finished Game (`repo.unchecked_finished_game_ids`).
- Tests: `tests/replay/test_play.py` (setup), `test_start.py` (`passed`, `start`), `tests/games/test_policy.py`.
- Frontend: `modules/games/play-page.tsx:120-160`, `game-end.tsx` (`GameEnd`, `heroTotal`), `modules/replay/{replay-block.tsx,replay.ts}`, `modules/games/insight-page.tsx`, `insight.ts linkTexts`, `modules/identity/homes.ts`, `copy/nb.ts games.play.end`, `insight`, `homes.student.replay`.
- E2E: `e2e/support/live-game.ts liveClassGame` (fresh Class, dev lock), `e2e/replay-play.spec.ts`, `e2e/support/axe.ts`.

## Tasks & Acceptance

**Execution:**
- `backend/app/modules/games/{policy,service,repo}.py` -- `staff_insight` column; `ClassGameHead.insight/replay`; `finished_student_seats` listed only.
- `backend/app/modules/debrief/{narration,insight}.py` -- Class games only.
- `backend/app/modules/sessions/{overview,schemas}.py` -- insight by `head.insight`, `GameInsightOut.replay`.
- `backend/app/modules/replay/{service,repo,dev}.py`, `main.py`, `README.md` -- finish hook recording `replay`; insight link `replay`; `POST /api/dev/class-sessions/{id}/quiz-passed` (own steps `class_game`, `debrief`, `quiz_passed`).
- `backend/tests/replay/test_finish.py` (new) -- one short Replay (weeks patched to 3) played to its end over the api: step once with time, Hjem, 409 order, check ran, Spillinnsikt, insight link, no narration; `test_policy.py`, debrief tests as needed.
- `frontend/src/modules/replay/replay-end.tsx` (new), `play-page.tsx`, `game-end.tsx`, `replay-block.tsx`, `insight-page.tsx`, `insight.ts`, `homes.ts`, `nb.ts`, `open-assumptions.md`, api client regenerated.
- `frontend/e2e/replay-finish.spec.ts` (new) -- stubbed finished Replay end at 320/360/1440 with axe, one primary button, formatted total; Hjem «Se Replay»; real stack: fresh Class game, dev quiz route, start Replay, its play screen has `[data-mark=projection]`, the Class game's has none.

**Acceptance Criteria:**
- Given a Replay in its last Week, when the last Order is placed, then the Game is finished, the `replay` step is recorded once at DB time and emits `user:<id>`, and the play page shows «Replay er ferdig», the Student's Totalkostnad and one primary «Gå til gjennomgangen» — never «Gå til Debrief».
- Given a finished Replay, then Hjem's Stegene shows Replay done and Individuell test current, the Replay block links «Se Replay», and an Order answers 409.
- Given a finished Replay, when the sweep runs, then a `game_checks` row exists for it.
- Given staff of the Class, when they open Spillinnsikt for the Replay, then it opens labelled «Replay» with three «KI-spiller» Seats; it is reached from the Student's Seat on the Class game's Spillinnsikt.
- Given the end screen at 320, 360 and 1440 px, then axe passes with one primary button.
- Given the real stack, when a Student starts a Replay, then its play screen draws the projection and the Class game's does not.

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
Four layers (sonnet; the story widens who reads Spillinnsikt and adds a finish hook and a dev route, so it counts as risky): blind hunter, edge-case hunter, verification gap, intent alignment. Every hand-back failed; findings were read from `review-{blind,edge,verification,intent}-10-5.md` in the scratchpad.
- verdicts: 29 findings — high 0, medium 1, low 17, false 11, maybe-false 0
- findings:
  - `[false]` `[reject]` (blind 1) a failing `record_step` rolls the finish back — the same in-transaction `record_step(within=)` that `_record_class_game_step` runs in every Class game finish; an `ON CONFLICT DO NOTHING` insert has no shown failure path, and an atomic step with the finish is the intent (AD-16).
  - `[low]` `[reject]` (blind 2) the hook reads `replays` on every finish — one indexed lookup per finished Game; a purpose shortcut would compare a purpose.
  - `[low]` `[reject]` (blind 3) Debrief judged from `lecturer_overview` — that column is the documented rule of every Class session list (policy docstring); the Debrief is the Class games'.
  - `[low]` `[reject]` (blind 4) Replay derived from three columns — the 10.4 rule, now named once (`_own_round`) for both readers; a new purpose gets its own row and review.
  - `[medium]` `[defer]` (blind 5) a taken-over Student Seat loses the Replay link — Spillinnsikt's links reach Student-held Seats only (Story 7.7, pinned by `test_game_insight.py`); deferred in frontmatter. The running-Replay part: the page states the status (`Pågår`); rejected.
  - `[low]` `[reject]` (blind 6) the web path is built in the backend — the pattern of `debrief.insight.summary_path`; the live e2e follows the link.
  - `[low]` `[patch]` (blind 7) the dev route has no backend test — `test_finish.py` now passes the quiz through it (404 for another session, 204 twice, the three steps stored). Its mounting follows the other dev routes (`APP_ENV != production`).
  - `[low]` `[patch]` (blind 8) the worker test checks a string only — it now asserts `replay.jobs` holds `replay.service` and the `replay.step` hook is that module's. Lateness: the step's `at` is stored and asserted; reject the rest.
  - `[low]` `[reject]` (blind 9) one long test, private narration hook — the runbook's one-session style; the hook is called directly to drive the pin-on case without an LLM job.
  - `[low]` `[reject]` (blind 10) null total / walkthrough link without a page — `/result` always has every Role (one builder); the link leads where Story 10.7 builds the page, as Story 6.18 linked «Gå til Debrief» before Story 9.2 (Design Notes).
  - `[low]` `[reject]` (blind 11) `replay` booleans across the page — three readers of one api field; a forgotten argument only shows the old «kommer» line.
  - `[low]` `[reject]` (blind 12) literal spaces in the test regex, e2e restates `heroTotal` — the regex uses `\u` escapes; the e2e states the expected text, which is its job.
  - `[false]` `[reject]` (blind 13) no focus move at the end — the Class game's end swaps the same way (page title and heading change); unchanged pattern.
  - `[low]` `[reject]` (blind 14) «to kostnadsarter» and the link label — both cost kinds exist in every game (a rate of 0 is still a kind); the link sits in the Student's own Seat item. Draft copy in `open-assumptions.md`.
  - `[low]` `[reject]` (edge 1) = blind 10.
  - `[low]` `[reject]` (edge 2) = blind 10.
  - `[false]` `[reject]` (edge 3) other terminal statuses — `PlayStatusName` is `not_ready|ready|running|finished`; Story 10.6 adds the close and its own screen.
  - `[low]` `[reject]` (edge 4) a Replay finished after the Testfrist records the step — Story 10.6 closes unfinished Replays at the deadline; until then the AC's «finish records the step» holds.
  - `[false]` `[reject]` (edge 5) test Games lose Debrief links and narration — a test Game has no Debrief (policy row, Story 6.20); intended.
  - `[low]` `[patch]` (verification 1) the Replay's per-Student «Melding» was not asserted — the live e2e now asserts `[data-message-student]` count 0.
  - `[low]` `[patch]` (verification 2) = blind 8.
  - `[low]` `[patch]` (verification other) = blind 7.
  - `[false]` `[reject]` (intent 1) the finish screen is stubbed in the browser — descriptive; the finish is real in `test_finish.py`, the screen from the api's shapes (as 10.4).
  - `[false]` `[reject]` (intent 2) the live test stops at Uke 1 — descriptive; the intent asks for the projection on a real running Replay.
  - `[false]` `[reject]` (intent 3) the play-page branch not joined to a real finished envelope — descriptive; `card["replay"]` is asserted over the api.
  - `[false]` `[reject]` (intent 4) deferral 2 fixed wider — descriptive.
  - `[false]` `[reject]` (intent 5) the walkthrough is a link only — descriptive; Story 10.7.
  - `[false]` `[reject]` (intent 6) the check runs from the sweep — descriptive; that is how Epic 6 runs it for a Class game (AC: «the same check»).
  - `[false]` `[reject]` (intent 7) surface beyond the AC (dev route, Seat link, no Messages) — descriptive; recorded decisions.

## Design Notes

The step hook asks `replays` (the Replay's own table), not the purpose: a Game is a Replay for this module exactly when its row names it. `record_step(within=session)` puts the step and its `user`/`session` events in the finish's transaction, so a failed finish records nothing. The walkthrough link points at the path Story 10.7 fills, as Story 6.18 linked «Gå til Debrief» before Story 9.2 built the Debrief.

## Verification

**Commands:**
- `uv run pytest tests/replay tests/games/test_policy.py tests/debrief/test_narration.py tests/sessions/test_insight*.py -q` -- pass
- `npm run typecheck && npx vitest run src/modules/replay src/modules/games` -- pass
- full gate per runbook before commit

## Auto Run Result

Status: done

**Summary.** The Student's last Order finishes the Replay through `games.commands.finish`, whose transaction now runs `replay`'s finish hook `replay.step`: for the Game a `replays` row names, it records `progress` `replay` once at database time (`user:<id>`, `session:<id>`), so Stegene shows Replay done and the Individual test current. Every worker imports `replay.jobs`, so an AI player's last Order records it too. The finished Replay's play page shows «Replay er ferdig» over «Grossist, Replay», the Student's own Totalkostnad (shared formatter), «Grossist, to kostnadsarter, hele Replay.» and the one primary «Gå til gjennomgangen» (`/spill/<id>/gjennomgang`), never the Class game's «Gå til Debrief» (10.4 deferral). Hjem's Replay block offers «Se Replay» once finished; an Order then answers 409. The finished-game check is the sweep's `games.verify_finished`, which already takes every finished Game; the api test runs it on the Replay. A new policy column `staff_insight` (Class game and Replay) opens Spillinnsikt to the Replay for its Class's staff, `replay: true`, titled «Replay», three «KI-spiller» Seats, no Messages and no Debrief links; the Class game's Spillinnsikt links the Student's Seat to it. The Debrief's narration hook, its Spillinnsikt links and `games.repo.finished_student_seats` take Class games only (10.3 deferral). A local-only dev route `POST /api/dev/class-sessions/{id}/quiz-passed` records the logged-in Student's steps up to `quiz_passed`, so a Playwright test starts a real Replay.

**Files.** Backend: `modules/games/{policy,service,repo}.py` (`staff_insight`, `_own_round`, `ClassGameHead.insight/replay`, `_listed()` in the narration sweep), `modules/debrief/{narration,insight}.py`, `modules/sessions/{overview,schemas}.py` (`GameInsightOut.replay`), `modules/replay/{service,repo,README}` (finish hook, insight links), `modules/replay/{jobs,dev}.py` (new), `platform/jobs/__init__.py`, `main.py`. Tests: `tests/replay/test_finish.py` (new), `tests/games/test_policy.py`. Frontend: `modules/replay/replay-end.tsx` (new), `replay.ts`, `replay-block.tsx`, `replay.test.ts`, `modules/games/{play-page,game-end,insight-page,insight}.tsx/ts`, `insight.test.ts`, `modules/identity/homes.ts` (`walkthroughPath`), `copy/nb.ts`, regenerated `lib/api/{openapi.json,schema.ts}`, e2e `replay-finish.spec.ts` (new). Docs: `open-assumptions.md`, refreshed `epic-10-context.md`.

**Decisions the founder would otherwise take.** (1) «Replay er ferdig» shows only the Student's own Totalkostnad with a one-line note, no Kjedens regning or chart. (2) «Gå til gjennomgangen» links to `/spill/<id>/gjennomgang` before Story 10.7 builds it (as 6.18 did for the Debrief). (3) Hjem offers a finished Replay through the Lenke «Se Replay», not a primary button. (4) Staff reach a Replay from the Student's Seat on the Class game's Spillinnsikt (link «Replay»); it is not on the Oversikt. (5) A Replay's Spillinnsikt has no «Melding» links and no Explanation/Debrief links. (6) A new policy column `staff_insight` rather than widening `lecturer_overview`. (7) A Lecturer's test Game no longer gets Debrief narration jobs or Debrief links (it has no Debrief). (8) The dev quiz route uses the Student's own login and `games.start_own`. (9) The step hook asks the `replays` table, not the purpose. (10) Draft copy recorded in `open-assumptions.md`. (11) Implementation in this context; four review layers.

**Review.** 29 findings (four sonnet layers): 3 patched (all low: the dev route tested through `test_finish.py`, the worker hook test asserts the registration, the e2e asserts no per-Student «Melding» on a Replay), 1 deferred (medium: a taken-over Student Seat loses the Replay link, because Spillinnsikt links reach Student-held Seats only, Story 7.7), the rest rejected with reasons in the triage log. `followup_review_recommended: false`: no medium or high entry was patched.

**Verification.** Full backend suite `--maxprocesses=8` on fresh test databases (`…/olspillet_m`): 3144 passed, 4 skipped (137 s), after the last backend change (a first try at keeping the link on a taken-over Seat failed its own test against Spillinnsikt's Student-Seat rule and was undone, hence the deferral). ruff check and format clean. Frontend typecheck, Vitest 1024 passed, `lint:colours`, `check:copy`, and `next build` (in the image) passed. Playwright `--workers=4` on replay-finish, replay-play, replay-start, homes, student-home, game-end, game-insight, graph-over-table, week-table, order-field, order-confirm, test-game, briefing and every debrief-* spec: 180 passed, none flaky. axe at 320, 360 and 1440 px on the end screen, 360 px on Hjem. New test over 1 s: `tests/replay/test_finish.py::test_the_last_order_finishes_the_replay_and_unlocks_the_next_step` (about 2.6 s, one session through the whole chain); the live e2e takes a fresh Class game (`test.slow()`).

**Residual risks.** «Gå til gjennomgangen» leads to a missing page until Story 10.7. A Replay finished after the Testfrist still records its step until Story 10.6 closes Replays. A taken-over Student Seat shows no Replay link (deferred). The end-screen copy is draft.
