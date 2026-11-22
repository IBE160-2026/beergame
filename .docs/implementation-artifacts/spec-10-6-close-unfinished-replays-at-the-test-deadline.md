---
title: 'Story 10.6: Close unfinished Replays at the Test deadline'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: '2469010fc0b0431a4645d628e57ca7293a8aa35c'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-10-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-10-5-finish-the-replay-and-unlock-the-next-step.md'
warnings: ['oversized', 'multiple-goals']
deferred: []
---

<intent-contract>

## Intent

**Problem:** A Replay the Student never finishes stays `running` forever: nothing closes it at the Test deadline, its AI players' jobs and the Student may keep ordering after it, and nothing in the data says the Replay ended unfinished. Also (10.4 visual check) the dashed projection line and its hollow dot strike through the «Restordre 20» / «Posisjon −4» labels in the net graph, and the projection sentence's formula breaks inside at 390 px.

**Approach:** A new AD-2 command `games.commands.close(game, reason)` ends a Game as `finished` with `end_reason = test_deadline` (new column), without a finished Week and without finish hooks; a new AD-9 sweep due action closes each unfinished Game of a purpose whose new policy column `closes_at_test_deadline` is on (the Replay) once its Students' `effective_test_deadline` (read through a provider `sessions` registers with `games`) has passed at the sweep's `now`. `place_order` refuses `409 test_deadline_passed` on a closed Game and, for such a purpose, after the deadline. `end_reason` is returned through `games.service` and the api; the Replay's screen, Hjem and Stegene say it was closed at the Testfrist and is not finished. The net graph moves its direct labels clear of the projection and the formula keeps to one line.

## Boundaries & Constraints

**Always:** Commands, sweeps and views ask `games.policy`, never a purpose (AD-13). The deadline is read only through `sessions.service.effective_test_deadline` and judged on the app clock (`auth.utcnow()`, the sweep's `now`), as `replay.start` does — never DB time against host time (Issue #63). `close` locks the Game row, writes `lifecycle = finished` + `end_reason`, opens no Week, stores no finished Week state, runs no finish hook (so no `replay` step, no narration), bumps `version`, emits `game:<id>` and `user:<id>` for its Students; it is idempotent (a finished Game: no write, returns False) and takes ids only. With `due=` (the sweep) it re-judges the deadline under the row lock. Orders already stored stay unchanged. A closed Game is "not finished" for every reader of a finished Game's numbers (`chain_result`, facts, the finished-game check, `sim check`). `ai-orders` jobs and the rescue loop end on `test_deadline_passed` without retry. UI copy only in `nb.ts`, draft lines in `open-assumptions.md`. Spine: `close` joins the AD-2 list, the due action the AD-9 list, the Deferred entry is closed.

**Never:** no playout by AI players; no walkthrough or rating (10.7, 10.8); no new lifecycle value; no change to the engine; no game per test; no screenshots.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Before deadline | running Replay, sweep at TEST − 1 min | untouched (lifecycle, version) | — |
| At deadline | running Replay, sweep at TEST | `finished`, `end_reason=test_deadline`, version +1, `game:`/`user:` emitted, Week rows and Decision log unchanged, no `replay` step | — |
| Twice | sweep again / `close` again | nothing written | — |
| Finished Replay | finished through `finish` | left alone, `end_reason` null | — |
| Not started | Replay stored, start failed | closed too | — |
| Student orders | closed Replay | 409 `test_deadline_passed` | screen says closed |
| Order after deadline, before sweep | running Replay, app clock ≥ TEST | 409 `test_deadline_passed`, nothing stored | — |
| AI job | `place_order` refused | job ends, no Order, no retry | logged `llm_order_ended` |
| Reads | `/api/me/games/{id}`, Hjem, insight | `status: finished`, `end_reason: test_deadline`; Stegene Replay `current`, `closed: true`; `/result` 409 | — |
| Class game | any purpose with the column off | never closed by this action | `close` → 409 `close_not_allowed` |

</intent-contract>

## Code Map

- `backend/app/modules/games/commands.py` -- `_place` (~1178: lock, `order_exists` before `game_finished`), `view_week`, `finish` (1653), `_commit_change` (252). Add `close`, `__all__`.
- `backend/app/modules/games/{policy,schemas,models,repo}.py` -- policy row/column; `EndReason`; `games.end_reason` + checks; `set_lifecycle`, finders `finished_game_ids`/`unchecked_finished_game_ids` (714-735), new unfinished-by-purpose finder; `named_students` (633).
- `backend/app/modules/games/service.py` -- `PlayStatus` (340), `get_game` (496), registration pattern of `on_game_finished` (654); add `register_test_deadline`, `past_test_deadline`, `test_deadline_closes`.
- `backend/app/modules/games/{views.py:161 chain_result, facts.py:87 _finished, checks.py:49 verify_finished, insight.py:130}`.
- `backend/app/modules/ops/sweep.py` -- `DUE_ACTIONS`; `backend/app/platform/events/registry.py` -- `games.close`.
- `backend/app/modules/players/{jobs,rescue}.py` -- `ENDED`.
- `backend/app/modules/sessions/{service,schemas,overview}.py` -- `effective_test_deadline` (594), `_game_out` (1746), `_replay_out` (1478), `_replay_closed` (1506), `GameInsightOut`.
- `backend/migrations/versions/0117_game_end_reason.py` (new, after 0116).
- Tests: `tests/replay/test_finish.py` (pattern: `running`, dev quiz route, `start`), `tests/games/test_registry.py`, `tests/games/test_policy.py`.
- Frontend: `modules/games/play-page.tsx` (`finished`, `useSendOrder`), `game-end.tsx endTitle`, `modules/replay/{replay.ts,replay-block.tsx,replay-end.tsx}`, `modules/games/home.ts stepItems`, `insight-page.tsx`, `copy/nb.ts` (`games.play`, `homes.student`), `components/charts/net-graph.tsx` (labels at 185-190, `Projection`), `modules/games/week-table-view.tsx ProjectionSentence`, `projection.test.tsx`, e2e `replay-finish.spec.ts` (stub pattern), `replay-play.spec.ts`.

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0117_game_end_reason.py`, `games/models.py`, `games/schemas.py` -- `end_reason` text null, in `EndReason`, only on a finished Game.
- `games/policy.py` -- `closes_at_test_deadline` (replay on).
- `games/repo.py`, `games/service.py` -- provider registration, deadline judgement (all named Students' deadlines passed at `at`), finder, `end_reason` on `PlayStatus`/`GameOverview`; closed Games out of the finished-check finders.
- `games/commands.py` -- `close`; `_place`/`view_week` refusals.
- `games/{views,facts,checks,insight}.py` -- closed is not finished; insight carries `end_reason`.
- `ops/sweep.py`, `events/registry.py`, `players/{jobs,rescue}.py`.
- `sessions/{service,schemas,overview}.py` -- provider; `end_reason` on card, Replay block, insight; Stegene `closed` when deadline passed and the Replay step not done.
- `tests/replay/test_close.py` (new) -- one Class session, one Student's Replay: order after deadline refused, sweep before/at deadline, closed state, idempotence, no step, Decision log unchanged, Hjem/card/result/insight, AI job ends; a finished Replay left alone. `test_registry.py`, `test_policy.py`, worker/rescue as needed.
- `.docs/.../ARCHITECTURE-SPINE.md`, `replay/README.md` -- AD-2/AD-9 lists, Deferred closed.
- Frontend: `replay-closed.tsx` (new) + `play-page.tsx` (closed screen, order outcome `deadline`), `replay.ts`, `replay-block.tsx`, `home.ts`, `insight-page.tsx`, `nb.ts`, `open-assumptions.md`, api client; `net-graph.tsx` labels clear of the projection; `nb.ts` projection formula with non-breaking spaces; Vitest for each.
- `frontend/e2e/replay-close.spec.ts` (new) -- stubbed closed Replay screen and Hjem at 320/360/1440 with axe; refused Order line.

**Acceptance Criteria:**
- Given an unfinished Replay whose Student's Test deadline has passed, when the sweep runs, then it is closed once (`finished`, `end_reason = test_deadline`), not played out, its Orders unchanged, and no `replay` step is recorded.
- Given a closed Replay, when the Student opens it, then the screen states it was closed at the Testfrist and is not finished; Hjem and Stegene say the same, and an Order answers 409 `test_deadline_passed`.
- Given another module reading the Game through `games.service`, then `end_reason` comes with it.
- Given the Replay play screen at 390 px, then no direct label of the net graph overlaps the projection line or its dot, and the formula of the sentence stays on one line.
- Given the closed screen and Hjem at 320/360/1440 px, then axe passes.

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
Four layers (sonnet; the sweep closing Games is a state change under concurrency): blind hunter, edge-case hunter, verification gap, intent alignment. Every hand-back failed; findings were read from `review-{blind,edge,verification,intent}-10-6.md` in the scratchpad.
- verdicts: 36 findings — high 0, medium 1, low 23, false 12, maybe-false 0
- findings:
  - `[low]` `[patch]` (blind 1) Stegene says «stengt …» beside a live «Fortsett Replay» in the minute before the sweep — `_replay_closed` again needs no Replay started or `end_reason` set; `test_close.py` asserts `closed` is False before the close.
  - `[low]` `[reject]` (blind 2) `close` without `due` closes at once — documented caller-judged form; its one production caller (the sweep) passes `due`, and a later make-up close (13.x) judges its own deadline.
  - `[low]` `[reject]` (blind 3) no shared "completed" predicate — the readers of a finished Game's results are the four patched; the others (`debrief.rules`, overview) read Class games, which are never closed.
  - `[low]` `[reject]` (blind 4) per-minute queries per unfinished Replay — bounded by unfinished Replays (one per Student and session); an SQL deadline filter would bypass `effective_test_deadline`.
  - `[false]` `[reject]` (blind 5) unregistered provider silently disables the gate — every process that can close or order imports `sessions.service`: `ops.sweep` directly, the workers through `replay.jobs` (asserted in `test_finish.py`), the api through `main`.
  - `[low]` `[reject]` (blind 6) a 409 on a Guided Week view or `/play` shows a generic error — false in effect: `useGuidedView` leaves a 409 to the next event, and `/play` answers `game_not_running`, which reads the game again and shows the closed screen.
  - `[low]` `[reject]` (blind 7) «Ordrene … er lagret» shown for a never-started Replay; no notice to the Student — reached only after a failed start; draft copy for the founder.
  - `[low]` `[reject]` (blind 8) width estimate, duplicated dot constants, fallback may sit on the other label — the estimate is `labelAt`'s own; `nearest(labels)` keeps labels apart; real boxes are measured in `projectionCrossings` (e2e).
  - `[false]` `[reject]` (blind 9) the NBSP is an invisible literal; `overflow-wrap` breaks words — it is the ` ` escape; `anywhere` only applies where a word cannot fit at all, where it would overflow otherwise.
  - `[low]` `[reject]` (blind 10) `close` docstring mentions `session:`; `EndReasonOut` duplicates the enum — the docstring states `_commit_change`'s generic rule; a second reason is a story of its own.
  - `[false]` `[reject]` (blind 11) no 10.6 screenshots — the runbook gives the visual check to a separate agent; the 10.5 shots in the diff are the visual agent's commit `ab5221f`.
  - `[medium]` `[patch]` (edge 1) an AI Order after the deadline strands a Week the Student ordered in time, so a Replay finished in time is closed — the pre-close deadline refusal now applies to a Student's own Order (`actor`) only; an AI player's completes the Week, and after the close `_refuse_finished` refuses it.
  - `[low]` `[reject]` (edge 2) close while a complete Week awaits its advance — `place_order` advances in its own transaction; only a crash between a commit and `_settle` leaves one, which the rescue loop advances.
  - `[low]` `[patch]` (edge 3) = blind 1.
  - `[low]` `[reject]` (edge 4) = blind 2.
  - `[false]` `[reject]` (edge 5) = blind 5.
  - `[low]` `[patch]` (edge 6) `close` on a finished Game of another purpose raises instead of returning False — the finished check now comes first.
  - `[low]` `[reject]` (edge 7) stale or foreign Orders past the deadline get `test_deadline_passed` — every Student Order on such a Replay is refused; the code says why, and no Seat is revealed.
  - `[low]` `[reject]` (edge 8) = blind 4.
  - `[low]` `[reject]` (edge 9) a stored never-started Replay can be started after the deadline before the sweep — the 10.3 existing-Replay branch; its Orders are refused and the sweep closes it within a minute.
  - `[false]` `[reject]` (edge 10) no reopen after a later extension — no extension exists yet (`effective_test_deadline` is the session's); Epic 11 adds both.
  - `[false]` `[reject]` (edge 11) LLM call paid then refused past the deadline — after the edge-1 patch an AI Order before the close is placed.
  - `[low]` `[patch]` (edge 12, deletion) = blind 1.
  - `[low]` `[patch]` (edge 13, claim) = edge 6.
  - `[false]` `[reject]` (edge 14, claim) the matrix row expects 409 on a repeat of a stored Order — `order_exists` first is the 6.13 rule the spec keeps.
  - `[low]` `[patch]` (verification 1) the facts guard for a closed Replay untested — `test_close.py` asserts `fact_set` raises `game_not_finished`.
  - `[low]` `[patch]` (verification 2) `view_week` refusal untested — `test_close.py` asserts 409 `test_deadline_passed` on a view past the deadline.
  - `[low]` `[patch]` (verification 3) `close(due=)` re-judgement untested — `test_close.py` asserts `close(..., due=TEST − 1 min)` is False and writes nothing.
  - `[low]` `[patch]` (verification 4) the Spillinnsikt closed label untested — `insight.statusText` with a Vitest case; the page uses it.
  - `[low]` `[reject]` (verification other 1) rescue-loop handling of the code only asserted by membership — after the edge-1 patch the code reaches the rescue loop only on a closed Replay, the path the job test runs.
  - `[low]` `[reject]` (verification other 2) label placement with a clipped projection untested — `projectionBand` drops the dot when clipped; the line part is the same code the four cases run.
  - `[false]` `[reject]` (intent 1) fallback with a halo where no clear height exists — descriptive; the reported shots are cleared (e2e `projectionCrossings` at 320/360/390/1440 and the short game), the fallback recorded in `open-assumptions.md`.
  - `[false]` `[reject]` (intent 2) model vs pixels — descriptive; the e2e measures real text boxes.
  - `[false]` `[reject]` (intent 3) the closed UI is tested on stand-ins — descriptive; the api shape is asserted in `test_close.py`.
  - `[false]` `[reject]` (intent 4) wider than the AC — descriptive; recorded decisions.
  - `[false]` `[reject]` (intent 5) no after-screenshots — the visual check is a separate agent's.

## Design Notes

`close` rather than a new lifecycle: the story fixes `lifecycle = finished` plus `end_reason`, so every "is it running" reader (rescue loop, overdue turns, `games_charged_to`, play routes) stops at once, while the few readers of a finished Game's results refuse a closed one. The deadline gate lives in the command (optional `due`) so a deadline moved between find and act (Epic 11) is judged under the row lock. Labels: per label, the y nearest its wanted one whose text box is clear of the projection segment over the label's x span (and of the end dot and the other label); with no such y, the wanted one with a halo in the tint colour.

## Verification

**Commands:**
- `uv run pytest tests/replay tests/games/test_registry.py tests/games/test_policy.py tests/test_migrations.py -q` -- pass
- `npm run typecheck && npx vitest run src/modules/replay src/modules/games src/components/charts` -- pass
- full gate per runbook before commit

## Auto Run Result

Status: done

**Summary.** New AD-2 command `games.commands.close(game, reason, *, due=None)`: locks the Game row, sets `lifecycle = finished` with `end_reason = test_deadline` (new column, migration `0117`, checks: known value, only on a finished Game), opens no Week, stores no finished state, runs no finish hook (no `replay` step, no narration), bumps `version`, emits `game:` and `user:` for its Students; idempotent; only for a purpose whose new policy column `closes_at_test_deadline` is on (the Replay), else 409 `close_not_allowed`; with `due` it re-judges the deadline under the lock. New AD-9 due action `games.close_at_test_deadline` (finder `games.service.due_test_deadline_closes`, every unfinished Replay — started or only stored — whose Students' `effective_test_deadline` has passed at the sweep's `now`, read through a reader `sessions.service` registers with `games.service`). `place_order`/`view_week` answer 409 `test_deadline_passed` on a closed Replay, and a Student's own Order or view past the deadline before the close; `ai-orders` jobs and the rescue loop end on the code. A closed Game is not finished for `/result`, facts, the finished-game check and `sim check`. `end_reason` is on `games.service` (`GameOverview`, `PlayStatus`), the card, Hjem's Replay and Spillinnsikt. Screens: «Replay stengt» (two lines, «Til Hjem», no total, walkthrough or button forward), a refused Order line, Hjem's closed line without «Se Replay», Stegene «stengt ved Testfristen, ikke fullført», Spillinnsikt «Stengt ved Testfristen, ikke fullført». 10.4 defect: the net graph's direct labels move to the nearest height clear of the projection line and dot (Netto lager label first; both orders tried), with a tint halo; the sentence's sum has non-breaking spaces (`overflow-wrap: anywhere` only where a line is narrower than the sum). Spine: `close` in AD-2, the due action in AD-9, Deferred entry closed.

**Files.** Backend: `migrations/versions/0117_game_end_reason.py` (new); `modules/games/{models,schemas,policy,repo,service,commands,views,facts,checks,insight}.py`; `modules/ops/sweep.py`; `modules/players/{jobs,rescue}.py`; `modules/sessions/{service,schemas,overview}.py`; `platform/events/registry.py`; `modules/replay/README.md`. Tests: `tests/replay/test_close.py` (new), `tests/games/{test_registry,test_policy}.py`, `tests/test_migrations.py`. Frontend: `modules/replay/replay-closed.tsx` (new), `replay.ts`, `replay-block.tsx`, `replay.test.ts`; `modules/games/{play-page,game-end,home,insight-page,insight,week-table-view}.tsx/ts`, `insight.test.ts`, `projection.test.tsx`; `components/charts/net-graph.tsx`; `copy/nb.ts`; regenerated `lib/api/{openapi.json,schema.ts}`; e2e `replay-close.spec.ts` (new), `replay-play.spec.ts`, `support/graph.ts`. Docs: `ARCHITECTURE-SPINE.md`, `open-assumptions.md`.

**Decisions the founder would otherwise take.** (1) A Replay closes when the deadline of every Student it ever seated has passed (a Replay has one), on the app's clock like `replay.start`. (2) From the deadline, before the sweep, the Student's own Order and Guided Week view are refused; an AI player's Order may still complete a Week the Student ordered in time (review finding). (3) A Replay stored but never started is closed too. (4) `close` takes an optional `due` and re-judges under the lock; without it the caller has judged. (5) Closed is `finished` + `end_reason`, never a new lifecycle; it has no result, facts or finished-game check. (6) Closed screen copy, Hjem line (no «Se Replay»), Stegene note, Spillinnsikt status and refused-Order line are draft copy in `open-assumptions.md`. (7) Graph labels: move vertically clear of the projection; where a line rising over the whole field leaves room for one label, Netto lager gets it and Posisjon keeps its height with a halo. (8) The formula keeps to one line via non-breaking spaces, breaking only where it cannot fit. (9) The epic context was not recompiled although `open-assumptions.md` was newer (10.5's own copy lines, read directly). (10) Implemented in this context, not by a sub-agent (runbook); four sonnet review layers.

**Review.** 36 findings: 8 patched (1 medium: AI Orders past the deadline; low: Stegene in the pre-close minute, `close` order of checks, four test gaps — facts, `view_week`, `due`, Spillinnsikt label), the rest rejected with reasons above; nothing deferred. `followup_review_recommended: false` (one medium patched, no high).

**Verification.** Full backend suite `--maxprocesses=8` after the last change: 3146 passed, 4 skipped (133 s). ruff format/check clean on changed files. Frontend typecheck, Vitest 1031 passed, `lint:colours`, `check:copy`, `next build` (image) passed. Playwright `--workers=4` after the stack rebuild, on replay-close, replay-play, replay-finish, replay-start, homes, game-insight, game-end, order-failures, order-confirm, order-field, graph-over-table, week-table, student-home, game-card: 130 passed, none flaky; axe at 320, 360 and 1440 px on the closed screen, 360 px on Hjem. New test over 1 s: `tests/replay/test_close.py::test_the_sweep_closes_an_unfinished_replay_at_the_test_deadline` (about 4–6 s alone, one Class session with three Replays; 21 s once under a loaded full run). Failed once and passed on rerun: Vitest `src/theme/text-on-tint.test.ts > class pairs in the components > uses only text-on-background pairs from the table` failed twice in full runs while the machine was loaded (file took 6–8 s) and passed alone and in the next full run.

**Residual risks.** Draft copy. Posisjon may still be crossed (with a halo) when the projection rises over the whole field. No reopen of a closed Replay once Epic 11 adds extensions. The sweep reads every unfinished Replay each minute.
