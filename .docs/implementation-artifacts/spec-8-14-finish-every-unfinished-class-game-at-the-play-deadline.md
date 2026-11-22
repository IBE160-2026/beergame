---
title: 'Story 8.14: Finish every unfinished Class game at the Play deadline'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: '87975cd4a2e50d4b9df8d5aac3274c649241b961'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-8-context.md'
warnings: ['oversized', 'multiple-goals']
deferred:
  - summary: >-
      No test shows the playout finder leaves a Lecturer's test Game of the same Class session alone.
    evidence: |-
      repo.playout_games filters on purposes_with("play_deadline_playout") and the command refuses
      playout_not_allowed, but no test puts a lecturer_test Game in a Class session past its deadline.
      Dropping the filter would only cause one logged refusal per Game and process (playout_due logs
      refusals once since the review patch), so no data is at risk.
    location: >-
      backend/app/modules/games/repo.py:playout_games
    severity: low
---

<intent-contract>

## Intent

**Problem:** A Class game that is not finished when the Class session's Play deadline passes never ends, so its Students never reach «Spillet er ferdig», the Debrief or the Trakt's «Klassespill ferdig», and a held Debrief (Epic 9, Issue #180) would stay held. Separately, at 200 % text on the Oversikt the Varselbånd's message column collapses to one letter per line (page ≈ 9400 px tall, screenshot `8.12/oversikt-lenke-1280t200.png`).

**Approach:** A new AD-2 command `games.commands.playout` hands every Student-held Seat to an AI player (reason `playout`), sets `lifecycle = playing_out` and lets the existing advance loop play every Week to `finish`; a new per-minute sweep due action calls it for each unfinished Class game whose Class session's live Play deadline has passed. Person commands answer `409 play_deadline_passed` afterwards; Students see a played-out note on Spill, Hjem and «Spillet er ferdig». The Varselbånd's row layout wraps on a rem-based basis so the text keeps its width and the buttons go under it.

## Boundaries & Constraints

**Always:** One Game per transaction under the Game row lock; the Play deadline is read live in the command's transaction (an extension before the deadline holds; a Pause never moves it). A never-started Game is started in the same transaction with no actor; a Game without a snapshot is refused `409 game_not_ready` and the sweep logs `playout_game_not_ready` with the Game id and goes on. `playout` clears Pause (no `pause_ended_by`) and in-room mark, drops queued Reclaims, closes the open Week's unqueued reminders, appends one AI occupant per Student-held Seat (`_takeover_occupant`: `llm` per AI mode, `rule_based` after a guard switch or at the cost limit; from the open Week if the Seat has not ordered, from the next Week if it has, none if it ordered the last Week), stores `games.played_out_at` (migration 0063), refreshes `game_summaries` via `_commit_change`, emits `game`, `session` and `user` for every Student who held a Seat. A second call returns False and writes nothing. In `playing_out` no turn gets an `ai_deadline_at`, LLM Orders are deferred on `llm-batch` (key `llm-batch:<game>:<week>:<seat>`), and the sweep re-defers a playout LLM turn with no Order and no `todo`/`doing` job. `finish` is unchanged, so the finished-game check and the `class_game` step run as for a normal end. `place_order` with an actor or `decided_by = student`, `view_week`, `pause`, `takeover`, `request_reclaim` on a played-out Game answer `409 play_deadline_passed`; an AI Order in `playing_out` is accepted. Playout Weeks keep `seat_week.reason = playout` and `decided_by` `llm`/`rule_based`. Copy in `nb.ts`, no blame, no Week count. Tests use injected clocks only, never host vs DB time.

**Never:** No Takeover notice mail for a playout. No change to `sprint-status.yaml`, session logs, issues, committed screenshots, or the demo Class. No Debrief module work (not on this branch). No Week count anywhere in the new copy.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Running game past deadline | Rule-based mode, Students hold 2 Seats, one paused + in-room | Finished in the same sweep; Pause/mark cleared; seats' new rows `playout`; check ran and passed; both Students have `class_game` | — |
| Never started | snapshot, `not_started` | started (`started_by` NULL) and played out | — |
| No snapshot | lock never succeeded | skipped, others played out | `game_not_ready` logged as error with Game id |
| Deadline extended | finder saw old deadline, live one later | nothing written | `play_deadline_not_passed` skipped quietly |
| Seat ordered this Week | Student ordered open Week | their Order stands; AI from next Week | — |
| LLM mode | `llm` occupant | jobs on `llm-batch`, no `ai_deadline_at`; lost job re-deferred by sweep | typed failure → Rule-based Order (existing job) |
| Person after playout | `place_order`/`pause`/`takeover`/`request_reclaim` | `409 play_deadline_passed` | — |
| Order vs playout race | both on the lock | either Order stored and AI from next Week, or Order refused | — |
| Overdue | `playing_out` longer than `playout_allowed_minutes` | `playout_overdue` error once per Game per process | — |

</intent-contract>

## Code Map

- `backend/app/modules/games/commands.py` -- `start` (l.1024) body to extract into `_start_in(session, game, actor_id)` reused by `playout`; `_open_week` (l.919: no AI deadline while `playing_out`); `_complete_week`/`_advance_once` (l.1705/1720: accept `PLAYING_OUT`); `_place` (l.1241), `view_week`, `takeover` (l.1819), `request_reclaim` (l.2014), `_pausable_game` (l.2611): `play_deadline_passed`; `_takeover_occupant` (l.2706) reuse; `finish` (l.2738) unchanged; `Latest` (l.2789) reuse for the deadline.
- `backend/app/modules/games/repo.py` -- `_open_weeks` (l.1209) and `running_*` finders: include `playing_out` where the rescue must see it; add `set_played_out`, `clear_pause`, `playout_games(class_session_ids)`, `overdue_playouts(before)`, `playout_llm_turns()`.
- `backend/app/modules/games/models.py` + `backend/migrations/versions/0063_game_played_out.py` -- `games.played_out_at`.
- `backend/app/modules/games/turns.py` `pending_turn` (l.54) -- accept `PLAYING_OUT`, carry `playout: bool`.
- `backend/app/modules/players/service.py` `ensure_order` (l.67) -- defer on `LLM_BATCH` with its own key when `turn.playout`.
- `backend/app/modules/games/service.py` -- `play_status` gains `played_out`; finders exported for ops/sessions; `complete_running_games` must include `playing_out`.
- `backend/app/modules/games/views.py` `table_status` -- nothing new needed (can_pause/can_insert already false off `running`).
- `backend/app/modules/sessions/service.py` -- `due_playouts(now)` (class sessions with `play_deadline <= now`, their unfinished Games where policy has `play_deadline_playout`) and `playout_due(item, now)`; `_game_out` adds `played_out`; schema `StudentGameOut.played_out`.
- `backend/app/modules/ops/sweep.py` -- due actions `sessions.playout`, `games.playout_orders`, `games.playout_overdue` before `games.verify_finished`; `TAKEOVER_RACES` += `play_deadline_passed`.
- `backend/app/platform/jobs/__init__.py` -- `live_locks(session, locks)`.
- `backend/app/platform/config.py` -- `playout_allowed_minutes` placeholder (60).
- `backend/app/platform/events/registry.py` -- `games.playout` (`game`,`session`,`user`), `sessions.playout`.
- `backend/tests/games/test_game_summaries.py` -- recomputation test gains `playout`.
- `frontend/src/modules/games/{play-page,student-hjem,game-end,game-action}.tsx`, `home.ts` -- played-out note; no Ordrefelt/Spillkort while `played_out`.
- `frontend/src/modules/games/overview-band.tsx` (l.87-106) -- wrapping row layout.
- `frontend/src/copy/nb.ts` (l.1720 `end`, `homes.student`) -- draft copy.

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0063_game_played_out.py`, `models.py`, `tests/test_migrations.py` HEAD -- add column.
- `backend/app/modules/games/commands.py`, `repo.py`, `turns.py`, `service.py`, `rules.py` (`can_take_over` unchanged), `schemas.py` -- `playout`, `ensure_playout_order`, refusals, advance in `playing_out`.
- `backend/app/modules/players/service.py`, `backend/app/platform/jobs/__init__.py`, `backend/app/platform/config.py` -- llm-batch defer, live locks, allowed time.
- `backend/app/modules/sessions/service.py`, `schemas.py`, `backend/app/modules/ops/sweep.py`, `registry.py` -- finder, act, view flag, due actions.
- `backend/tests/games/test_playout.py` -- command tests (idempotent, never started, no snapshot, pause/in-room/reclaim cleared, ordered seat, refusals, race, LLM defer + re-defer, overdue log, summaries) on a shared state built directly, no full Classic game.
- `backend/tests/sessions/test_playout.py` -- api level: short game, takeover earlier, `sweep.run(PLAY)` → finished, check passed, both Students have the step, Hjem `played_out`, insight marks `playout`; 100 unfinished not-started Class games of 2 Weeks all finished by one sweep.
- `frontend/src/copy/nb.ts`, play/home/end components + Vitest -- note and gating.
- `frontend/src/modules/games/overview-band.tsx` -- wrapping layout; e2e `frontend/e2e/playout.spec.ts` (Student sees the note after playout set up through the dev/test api or DB) and axe at 200 % on the band in `varselband.spec.ts`.

**Acceptance Criteria:**
- Given a played-out Class game, when a Student opens Spill or Hjem, then «Spillet er ferdig» shows the note that it ended at the Spillfrist, the chain's cost and «Gå til Debrief»; no Week count, no blame.
- Given the Oversikt at 1280 px with 200 % text and a Varselbånd, when it renders, then the message text stays readable on full lines and the buttons stand under it; at 100 % from 1024 px the band stays one row.
- Given the full backend suite, then `playout` passes the Story 7.1 recomputation test and the registry test.

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
- verdicts: 36 findings — high 0, medium 8, low 20, false 8, maybe-false 0
- findings:
  - `[low]` `[reject]` blind: a failed `llm-batch` playout job is re-deferred every minute with no cap — the AC requires the sweep to re-enqueue a playout turn with no Order and no live job; the job catches every model failure and places the Rule-based Order, so only repeated database failures reach `failed`; a cap adds a branch for a rare case.
  - `[false]` `[reject]` blind: a Game with no snapshot never ends — the AC says the sweep skips it and logs an error with its id; it has no settings to play.
  - `[medium]` `[patch]` blind: the finder sends every Class session ever past its deadline as one IN list each minute — fixed: `games.service.sessions_with_playout_games` lists only Class sessions with a Game still to play out, and `sessions.repo.passed_play_deadlines` filters those.
  - `[low]` `[reject]` blind: playouts share `llm-batch` with mail — the queue is the one AD-5 names for playout Orders; no new contention beyond the spine's design.
  - `[low]` `[patch]` blind: playout in a Guided Week untested — added `test_in_a_guided_week_an_unviewed_seat_is_taken_from_it_and_a_viewed_one_from_the_next`.
  - `[medium]` `[patch]` blind: the staff side (Oversikt «Ferdig», Trakt, marks) unverified — the api test now asserts the Oversikt item is `finished`, carries the `playout` mark and the Trakt's `class_game` count; the marks already existed (Story 7.7).
  - `[low]` `[reject]` blind: «Gå til Uke n» under the playing-out line names a Week number — it is the open Week the Topplinje shows too, never the number of Weeks (FR-14).
  - `[low]` `[patch]` blind: the refusal copy repeats a present-tense sentence that is wrong once the game finished — the five refusal maps now read «Spillfristen er nådd, og KI-spillere har tatt over spillet.»
  - `[low]` `[reject]` blind: no CHECK tying `playing_out` to `played_out_at` — one writer (`set_played_out`) sets both; not met in everyday use.
  - `[false]` `[reject]` blind: the race test accepts both outcomes — the AC asks for one consistent outcome of a real race, which the test asserts for either winner; the other sub-points (setup counts, cross-module helpers, module-level log set) are existing conventions.
  - `[false]` `[reject]` blind: the Varselbånd change is unrelated work — the intent asks for it.
  - `[low]` `[reject]` blind: the spine bullet is long — it follows the bullet's existing «Decided in Story …» convention.
  - `[low]` `[reject]` blind: raw SQL on `procrastinate_jobs` — procrastinate is pinned; the LLM playout test checks a waiting job counts as alive.
  - `[low]` `[reject]` blind: frontend nits (`?? false`, the `note` slot) — harmless; the slot is Story 6.18's.
  - `[medium]` `[patch]` edge: a playout refused with `snapshot_mismatch`/`parameter_set_changed` was re-raised each minute with no Game id — `playout_due` now logs every refusal as an error once per Game and code, with the id, and goes on.
  - `[medium]` `[patch]` edge: `apply_cost_limit` skipped Games `playing_out` — `running_games_of_session` and `running_games_of_config` now include `playing_out`.
  - `[low]` `[patch]` edge: a playout turn whose job is still on `ai-orders` (no AI deadline) could be deferred twice — `stalled_playout_turns` now checks both keys.
  - `[low]` `[reject]` edge: failed job re-deferred forever — same as the first blind finding.
  - `[low]` `[reject]` edge: `ensure_playout_order` placing a Rule-based Order inline bumps no version — a playout turn of a Rule-based Seat always gets its Order when the Week opens; unreachable in practice and the fix adds a branch.
  - `[false]` `[reject]` edge: `propose_time`/`accept_time` on a Game playing out — no Student holds a Seat then, so `_scheduling_game` refuses `seat_not_yours`.
  - `[low]` `[reject]` edge: a deadline extended after the playout does not restore the Game — the playout runs once (AD-2); not reversible by design.
  - `[medium]` `[patch]` edge: finder IN list — same root cause as the blind finder finding.
  - `[false]` `[reject]` edge: a retry of the Student's own stored Order answers `order_exists` — Story 6.13's retry rule, kept on purpose; another Seat holder's stored Order now answers `play_deadline_passed`.
  - `[low]` `[reject]` edge: the in-process log sets grow — bounded by the number of Games.
  - `[false]` `[reject]` edge claim: other codes for some person commands — the four AC commands and `view_week` answer `play_deadline_passed`; the own-Order retry is intentional.
  - `[medium]` `[patch]` verification: `played_out` while `playing_out` not asserted at the api — the api test holds the settle and asserts Hjem and Spill read `running` with `played_out` true.
  - `[low]` `[patch]` verification: Spill's playing-out branch unreached — added a stand-in e2e (`playout.spec.ts`): no Ordrefelt, the note, no primary, axe.
  - `[low]` `[patch]` verification: never-started Game with LLM seats — added `test_a_never_started_game_with_llm_seats_plays_out_with_no_ai_deadline`.
  - `[low]` `[patch]` verification: `play_deadline_passed` in `TAKEOVER_RACES` untested — the refusal test runs `sweep._take_over` on a played-out Seat and asserts the quiet skip.
  - `[low]` `[defer]` verification: no test of the finder against a Lecturer test Game — deferred (frontmatter).
  - `[medium]` `[patch]` verification other: cost limit and `playing_out` — same root cause as the edge cost-limit finding.
  - `[medium]` `[patch]` intent: staff Oversikt/Spillinnsikt AC not exercised — same root cause as the blind staff finding.
  - `[low]` `[patch]` intent: the 9400 px page symptom not asserted — the e2e now also asserts the band stays under 800 px tall at 200 % text.
  - `[low]` `[reject]` intent: the 100-game test has no LLM seats — the LLM path is tested on one Game; 100 LLM Games would add minutes to a suite already above 120 s.
  - `[false]` `[reject]` intent: conditional rather than always stacking — the band stacks whenever its text would collapse, which is the defect; normal text at 1440 px keeps one row.
  - `[false]` `[reject]` intent: the dev playout route is extra scope — a local-only test aid like Story 8.3's dev Takeover, not mounted in production.

## Design Notes

Played-out games stay `running` for `game_status` (the Oversikt shows them as running until `finish`, normally the same sweep for Rule-based seats). `played_out_at` marks both the transient `playing_out` and the finished state, so the end note and `play_deadline_passed` survive `finish`. Issue #180: once every Class game finishes by the playout, Story 9.2's release sweep releases a held Debrief; no extra code on this branch.

## Verification

**Commands:**
- `cd backend && uv run pytest tests/games/test_playout.py tests/sessions/test_playout.py -q` -- pass
- full backend `--maxprocesses=8`, `npm run typecheck`, `npm test`, `lint:colours`, `check:copy`, `build`, Playwright `--workers=4` per runbook -- pass

## Auto Run Result

Status: done
Blocking condition: none

**Summary.** `games.commands.playout` takes an unfinished Class game over under the Game row lock: it starts a never-started Game with no actor, sets `playing_out` and `played_out_at` (migration 0063), clears Pause and «I rommet», drops queued Reclaims, closes open reminders and gives each Student-held Seat an AI occupant (`playout`), from the open Week or, after the Student's Order, from the next; the advance loop then plays every Week to `finish` (finished-game check and `class_game` step as normal). The sweep's `sessions.playout` finds the Games of Class sessions past their live Play deadline; `games.playout_orders` re-defers a lost `llm-batch` job; `games.playout_overdue` logs a Game playing out past `playout_allowed_minutes` (placeholder 60). A person's `place_order`, `view_week`, `pause`, `takeover`, `request_reclaim` answer 409 `play_deadline_passed`. Students see «Spillfristen er nådd. KI-spillere spiller spillet ferdig.» while it plays out and «Spillet ble avsluttet ved Spillfristen. KI-spillere spilte det ferdig.» on «Spillet er ferdig». The Varselbånd wraps its buttons under the text on a rem basis, so at 200 % text the text keeps whole lines.

**Files.** backend: `games/commands.py` (playout, ensure_playout_order, `_start_in`, refusals, advance in `playing_out`), `games/repo.py` (finders, `set_played_out`, `playing_out` in open Weeks and cost-limit lists), `games/service.py`, `games/turns.py`, `games/schemas.py`, `games/models.py`, `migrations/versions/0063_game_played_out.py`, `players/service.py` (llm-batch defer), `platform/jobs` (`live_locks`), `platform/config.py`, `platform/events/registry.py`, `ops/sweep.py`, `sessions/service.py`, `sessions/repo.py`, `sessions/schemas.py` (`played_out`), `sessions/dev.py` (local dev playout); tests `games/test_playout.py`, `sessions/test_playout.py`, registry, summaries, authz list, migration head. frontend: `nb.ts`, `game-end.tsx`, `game-action.tsx`, `play-page.tsx`, `student-hjem.tsx`, `home.ts`, `overview-band.tsx`, api client, `playout.test.tsx`, `e2e/playout.spec.ts`, `e2e/varselband.spec.ts`. Spine: «Decided in Story 8.14».

**Review.** 36 findings: 15 patched (8 medium findings in 4 root causes), 1 deferred, 20 rejected with reasons in the triage log. Follow-up review recommended: true — patched medium entries ≥ 2; the unverified risk is the cost-limit switch reaching Games `playing_out` (`running_games_of_session`/`_of_config` now include it), which no test exercises.

**Verification.** Backend full suite `--maxprocesses=8`: 3095 passed (145 s); ruff clean. Frontend: typecheck, Vitest 905 passed, `lint:colours`, `check:copy`, build passed. Playwright `--workers=4` on the rebuilt stack: playout, overview, varselband, takeover, live-updates, homes, student-home, game-end, order-field, order-confirm, seat-status, guided-week, reclaim, pause, time-proposal: 101 passed, axe at 320 px, 1280 px with 200 % text and 1440 px. New tests over 1 s: the 100-game playout (27–33 s), LLM playout (4.5 s), sweep playout (4.2 s), api playout (3.3 s), five command tests at 2–2.3 s, the dev route test (1.9 s). No test failed once and then passed.

**Decisions taken in place of the founder.** Draft copy (above, `[ASSUMPTION]`). The epic context was used although the spine was newer (that change was Story 8.12's decision, read from its spec). Implemented in the agent's own context, as the runbook says, instead of an implementation sub-agent. A played-out Game reads `running` on the Oversikt until `finish`. No notice mail for a playout. `game_not_ready` and other refusals are logged once per Game and process. The 100-game test uses one-Week, never-started, Rule-based Games for speed. A local dev route plays one Game out for e2e. Issue #180 needs no code here: once the playout finishes every Class game, Story 9.2's release sweep releases a held Debrief.

**Residual risks.** The cost-limit switch during `playing_out` is untested. The 100-game test costs about 30 s of one worker.
