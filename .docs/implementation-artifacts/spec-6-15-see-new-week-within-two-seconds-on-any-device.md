---
title: "Story 6.15: See the new Week within two seconds, on any device"
type: 'feature'
created: '2026-11-21'
status: 'done'
baseline_revision: 'f155cd8dd841f6db27133e1c35604f2500618bff'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-6-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** When the last Seat orders, every Student's play screen must show the new Week by itself within 2 s (NFR-1), say what the Week cost (Uke-overgang, UX-DR23) and lose nothing on reload, device switch or a dropped connection (FR-26, NFR-5). The backend already advances in the last Order's transaction and the SSE path exists (6.4); nothing measures the 2 s end to end, there is no Uke-overgang, no now-line move and a typed draft of a closed Week vanishes silently.

**Approach:** Measure first, on the real stack: a Playwright spec with four Student sessions (and one with two mock AI players) on a real started Class game times last Order → new Week heading on every page, and a timing breakdown (order response, SSE event, envelope refetch, render) is recorded; fix what is slow. A local-only dev route locks a Class session now so the spec can start a real game. Backend tests pin the advance transaction and a human/AI race. The web app gets the Uke-overgang summary above the Ordrefelt, a skippable ≤ 2 s now-line move (none with reduced motion), and a «not sent» line for a typed draft whose Week closed.

## Boundaries & Constraints

**Always:**
- Backend: the completing `place_order` runs `engine.advance` once, writes the new `game_weeks` row and four `seat_turns`, bumps `version` once and emits `game:<id>`, `session:<id>` (class) and `user:<id>` per Student in that transaction (already so; pin it with a test). A last human Order and an LLM Order at once → exactly one advance (pin it).
- Dev route `POST /api/dev/class-sessions/{id}/lock` → `sessions.service.lock(id)`; mounted only where the dev mailbox is (`APP_ENV != production`), `include_in_schema=False`, public like the dev mailbox, listed in `PUBLIC_ROUTES`; 404 `not_found` for an unknown session. It stands in for Epic 8's early lock in tests only.
- Uke-overgang (`week-summary`), from the envelope only: shown when the Seat's state has a previous Week (`history` non-empty) and, in a free Week, until the Seat's own Order is placed (in a Guided Week while the Week is open). Content: heading «Uke {N−1} er ferdig regnet»; rows Levering / Ordre inn / Sendt (this Week's values); delta rows «Lager a blir b» and/or «Restordre a blir b» (previous Week's history row → current state; a row shows when either value is non-zero; both zero → the Lager row); then «Denne uka: 20 restordre × 1,00 = 20,00 kr» from `cost_lines` (non-zero lines joined with « + », units 0 omitted; none → «Denne uka: 0,00 kr»). The Lenke «Kostnad så langt» is not rendered (6.16). It stands above the Ordrefelt. A polite live region announces the summary text only when the Week advances while the page is open (not on load).
- Now-line: when the Week advances on an open page, the line slides from the previous Week's column to nå in ≤ 2 s (1.5 s) via the Web Animations API, never blocking input; «Hopp over» (Lenke in the summary header, shown only while it moves) finishes it at once; with `prefers-reduced-motion: reduce` nothing moves and no «Hopp over». No celebration.
- The new column shows Levering and Ordre inn, Netto lager and Posisjon at nå and the dashed empty Din ordre cell; the region scrolls so nå and «Nå» are in view (existing `toNow`; keep it).
- A non-empty typed, unsent draft of a Week that closes while the page is open is dropped (already cleared by `clearDrafts`) and a line says so: «Uke 11 er over. Du skrev 24, men ordren ble ikke sendt.» [ASSUMPTION draft copy]; the line goes when the Student types or sends.
- Live updates never move focus. Reload/another device: the page reads stored state (Confirmed if this Week's Order exists) — already so; pin in e2e.
- UI strings in `nb.ts` (`games.play.summary`), draft ones marked [ASSUMPTION].

**Never:** the «Kostnad så langt» target (6.16); a fixed sleep in tests; a game quantity computed in the web app beyond reading api numbers (the «a blir b» values and cost lines are read, not computed; only the « + » join and formatting); celebration; changing «class-of-1994» or leaving demo Students on Rosters (fresh invited Students only).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Others ordered, I order last | 4 Students, page open | own page: new Week, focus to heading (6.12); others: new Week ≤ 2 s, focus kept | — |
| Week advances, page open | backlog 13 → 20, cost 20 | summary «Uke 11 er ferdig regnet», «Restordre 13 blir 20», «Denne uka: 20 restordre × 1,00 = 20,00 kr»; announced; line slides | reduced motion: no slide, no «Hopp over» |
| Reload in new Week, not ordered | — | summary shown (not announced), no slide | — |
| Own Order placed | — | summary gone; Confirmed | — |
| Draft typed, Week closes | typed 24, unsent | field empty, «Uke 11 er over. Du skrev 24, men ordren ble ikke sendt.» | — |
| SSE reconnect after missed advance | stream `ready` again | refetch, new Week in place, focus kept | — |
| Week 1 | no history | no summary | — |

</intent-contract>

## Code Map

- `backend/app/modules/games/commands.py:1249` `place_order` / `_place:1095` / `_step:1070` / `_commit_change:228` -- advance-in-transaction and events (read-only unless measurement shows a slow part).
- `backend/app/platform/events/{hub,stream}.py` -- LISTEN fan-out; `stream.events:76`: `user:` events re-resolve scope before forwarding (read-only unless slow).
- `backend/app/modules/sessions/service.py:2373` `lock(class_session_id)` -- what the dev route calls.
- `backend/app/modules/messaging/routes.py` -- pattern for a dev router; `backend/app/main.py:107` mounts dev routers outside production.
- `backend/tests/test_authz_rules.py:15` `PUBLIC_ROUTES` -- add the dev lock route.
- `backend/tests/sessions/test_orders.py` `free_week`, `order`; `test_play.py` `play`, `running`; `tests/games/helpers.py` `listening`, `seat_student`, `query`; `tests/games/test_place_order.py:45` `started`, `counts`; `tests/games/test_play_guard_switch.py:155` LLM seat via `stored_config` + `place_order(..., "llm", llm_call_ids=[uuid4()])` (fixtures `games_db`, `ai_db`).
- `frontend/src/modules/games/play-page.tsx:135` `Running` -- summary placement above `OrderField`, advance detection (previous week ref), dropped-draft line, `movedFrom` to the table.
- `frontend/src/modules/games/week-table-view.tsx:174` `WeekTable` -- pass the move through to `GraphOverTable`.
- `frontend/src/components/graph-over-table.tsx:332` now-line `data-now-line` -- animate from the previous column; expose skip.
- `frontend/src/lib/api/live.ts`, `topics.ts` -- refetch path (`game:` → `["games","mine",id]` prefix, `user:` → `["games","mine"]`); change only if measured slow.
- `frontend/src/copy/nb.ts:1499` `games.play` -- add `summary` strings.
- `frontend/e2e/support/{classes,auth}.ts` -- `test` with `lecturerSession`, `freshClass`, `nextMail`, `latestMail`, `expectAccessible`; `student-registration.spec.ts:24` roster-paste + invitations flow; `live-updates.spec.ts` `untilLive`.
- `frontend/e2e/support/play.ts` -- stubbed play screen (`openPlay`, `refetchPlay`) and fixtures `src/modules/games/fixtures/play-week-*.json` for the stubbed Uke-overgang checks.

## Tasks & Acceptance

**Execution:**
- `backend/app/modules/sessions/dev.py` (new) + `backend/app/main.py` -- dev lock route; `backend/tests/sessions/test_dev_lock.py` (new) locks and opens the game, 404 unknown; `test_authz_rules.py` PUBLIC_ROUTES.
- `backend/tests/sessions/test_week_advance.py` (new) -- class game, 3 Students: the last Order's transaction leaves one new Week + 4 turns, version +1, events `game`, `session`, `user` × 3 (via `listening`); every Student's envelope shows the new Week, a second login reads the same; human/LLM race ×3 → one advance each.
- Measurement -- run the real-stack e2e with timing marks; record the breakdown in Design Notes; fix the slow parts found (files named there).
- `frontend/src/copy/nb.ts` -- `games.play.summary` strings.
- `frontend/src/modules/games/week-summary.ts` (+ `.test.ts`) -- pure `weekSummary(state)` → rows/cost text or null; `week-summary-view.tsx` -- the block with «Hopp over» and live region.
- `frontend/src/components/graph-over-table.tsx`, `week-table-view.tsx` -- `movedFrom`/`onMoveEnd` + skip handle for the now-line animation, reduced motion respected.
- `frontend/src/modules/games/play-page.tsx` -- wiring; dropped-draft line.
- `frontend/e2e/week-advance.spec.ts` (new, real stack) -- four Students and two Students + two mock AI: ≤ 2 s on every page, focus kept on others, reload and second device resume (Confirmed after ordering).
- `frontend/e2e/week-transition.spec.ts` (new, stubbed) -- summary text, announcement, slide + «Hopp over», reduced motion, dropped draft, reconnect refetch keeps focus; axe + no page scroll at 320/360/1440 with and without reduced motion (one axe per width).

**Acceptance Criteria:**
- Given four Students with the play screen open, when the last one confirms, then every page shows the new Week heading within 2 s of the press, measured in Playwright; likewise with two mock AI players once they have ordered.
- Given the Week advanced, then the summary reads as the matrix, is announced politely, stays until the own Order, and the Ordrefelt is usable at once.
- Given 320, 360 and 1440 px, with and without reduced motion, then no page-level horizontal scroll and no axe violation.

## Spec Change Log

## Review Triage Log

### 2026-11-21 — Review pass
- layers: blind hunter and edge-case hunter only (the orchestrator capped reviewers at two); verification-gap and intent-alignment skipped.
- verdicts: 31 findings — high 0, medium 1, low 25, false 5, maybe-false 0
- findings:
  - `[low]` `[reject]` blind: the dev lock is public — same pattern as the dev mailbox and bounce (Stories 3.6, 4.6): mounted only outside production, and Story 3.14's strict production guard refuses a non-production config there.
  - `[low]` `[reject]` blind: existence check and lock in two DB sessions; malformed id answers 404 — Class sessions are never deleted; dev-only route; 404 for any id that names no session is the documented answer.
  - `[low]` `[reject]` blind: no test for 409 `provider_key_missing`, the CSRF refusal, and the production route check — CSRF is the shared middleware's (tested); `test_dev_mailbox.py::test_it_is_not_routed_in_production` asserts no path starts with `/api/dev`.
  - `[false]` `[reject]` blind: summary numbers come from the new Uke under «Uke 11 er ferdig regnet» — exactly `06-spilldynamikk.png` D: on the Uke 12 screen «Levering 4, Ordre inn 11, Sendt 4, Restordre 13 blir 20» are the new column's values (its table shows Ordre inn 11 at Uke 12), and «Denne uka» is that column's cost.
  - `[low]` `[reject]` blind: «… men ordren ble ikke sendt» when another device's Order counted — the sentence is about the typed value, which was not sent; the stored Order shows in the table and Kjedebånd. Draft copy for the founder.
  - `[low]` `[patch]` blind + edge: the dropped-draft line stays into later Uker — cleared on the next Uke change.
  - `[low]` `[reject]` blind: old draft parsed against the new Uke's `max_order` — `max_order` is a frozen Game setting.
  - `[low]` `[patch]` blind + edge: a jump of several Uker slides across several columns — only a one-Uke step now moves the line and is announced; a jump shows the summary from stored state silently.
  - `[low]` `[patch]` blind + edge ×2: the move effect never cancels a running animation (second advance, unmount, reduced motion turning on) — the previous animation is cancelled before a new move («Hopp over» hidden), and on unmount.
  - `[low]` `[patch]` blind: `refresh` skipped an idle query under a busy prefix — every query under the key is invalidated at once with `cancelRefetch: false` (idle ones read at once, busy ones joined); one more read follows only when something was busy.
  - `[low]` `[reject]` blind: `refresh` tests share the `connectLive` client and switch to real timers — `afterEach` restores timers and stops the stream; the full Vitest run passes.
  - `[low]` `[patch]` blind + edge: `liveClassGame` did not assert one shared game — it now asserts every Student holds a Seat in the one Class game.
  - `[low]` `[reject]` blind: Student contexts leak when setup fails — only on a failing test; Playwright closes the browser.
  - `[low]` `[reject]` blind: the 2 s timed only at 360 px — width does not touch the live path (event, read, render); the 1440 px context checks the device switch.
  - `[low]` `[reject]` blind: the race test does not check events — the first backend test pins the completing transaction's events; the race test now pins the version.
  - `[false]` `[reject]` blind: «Kostnad så langt» missing — the AC says it is not rendered before Story 6.16; the e2e asserts no link in the summary.
  - `[low]` `[reject]` blind: two polite regions update in one render — both polite and short; screen readers queue them.
  - `[low]` `[reject]` edge: resize during the 1.5 s move uses stale px — the move ends within 1.5 s and the line then sits at the measured nå.
  - `[low]` `[reject]` edge: the earlier column not shown → no move — in both layouts nå − 1 is shown; the effect returns quietly otherwise.
  - `[false]` `[reject]` edge: own send in flight when the Uke advances shows the dropped line and weekGone — if the own send completed the Uke the history holds the typed value (no line); otherwise `outcome.week === was.week` suppresses it.
  - `[false]` `[reject]` edge: dev lock returns 200 for a session deleted in between — sessions are never deleted.
  - `[low]` `[reject]` edge: `ConfigNotFound` from `build_snapshot` gives 500 — dev-only route; the local seed always has the mock config.
  - `[low]` `[patch]` edge: an undefined `__weekShown` gave a NaN message — the e2e asserts it is defined first.
  - `[low]` `[patch]` edge: the race test's comment counted the version but sliced it off — now asserts the version rose by exactly two.
  - `[medium]` `[patch]` edge (claim): reduced motion checked only at 360 px — each width test now also reloads with reduced motion and checks the summary, no «Hopp over» and no page scroll (axe stays one per width; the 360 px reduced-motion test runs axe).
  - `[false]` `[reject]` edge (claim, low confidence): "moves one column" contradicted by jumps — resolved by the one-step patch above.

## Design Notes

Founder-level calls: summary visible from stored state after a reload too (it lasts until the own Order; announced only on a live advance); in a Guided Week it lasts the whole Week; delta rows show Lager/Restordre only when non-zero; the slide lasts 1.5 s; «Hopp over» shows only while the line moves; dropped-draft line is draft copy; the dev lock route is the test stand-in for Epic 8's early lock.

**Measurement (local stack, `week-advance.spec.ts`, ms after the last press, one clock).** Before: SSE `game:` event 211–223, its envelope read discarded, the read that showed finished 586–649, heading 593–655 (two-Student + AI run: 643–706). Cause: one change sends `game:` then `user:` about 50 ms apart (the stream re-reads the User's scope before forwarding `user:`); the second invalidation cancelled the read the first had started, so every page waited one whole extra read (about 150 ms, with four pages reading at once each read takes 130–160 ms on the server). Fix: `lib/api/live.ts` `refresh` lets a read already on its way finish and show, then reads once more (that read may predate the change). After: event 308, heading 513–538 on the other pages, 714 on the pressing page (POST of the completing Order 250–330 ms incl. the advance, then its own read). Trying to forward `user:` before the scope re-read was dropped: `test_event_stream.py` pins that a deactivated User's stream ends without sending it. Remaining budget is the completing transaction (~250 ms) and one envelope read; both far inside 2 s.

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/sessions/test_week_advance.py tests/sessions/test_dev_lock.py tests/test_authz_rules.py -q` -- pass
- `cd frontend && npx vitest run src/modules/games src/components` -- pass
- `cd frontend && npx playwright test e2e/week-advance.spec.ts e2e/week-transition.spec.ts e2e/homes.spec.ts e2e/order-confirm.spec.ts e2e/seat-status.spec.ts --workers=2` -- pass

## Auto Run Result

Status: done

**Summary.** Measured first, on the real stack: `week-advance.spec.ts` plays a real Class game (fresh invited Students, no Veiledede uker, locked at once through a new local-only dev route) with four Student pages, and with two Students and two mock LLM players, and times the last press to each page's new «Uke 2» heading on one clock, recording the SSE event and envelope reads. Before: 590–655 ms (AI run 643–706); one change's `game:` and `user:` events arrive ~50 ms apart and the second invalidation cancelled the read the first had started. Fix in `lib/api/live.ts` (`refresh`): a read on its way is joined and shown, then one more read follows. After: 385–612 ms on the other pages, ~820 ms on the pressing page; all under 2 s. The backend already advanced in the last Order's transaction; tests now pin its rows, one version step and its events (`game`, `session`, `user` × Students), and a last-human vs LLM race advancing once. The play screen gains the Uke-overgang above the Ordrefelt («Uke 11 er ferdig regnet», Levering / Ordre inn / Sendt, «Restordre 20 blir 27», «Denne uka: 27 restordre × 1,00 = 27,00 kr») until the own Order; announced politely only on a live one-Uke step; the now-line slides one column in 1.5 s with «Hopp over», none with reduced motion; a typed, unsent draft of a closed Uke is dropped with a line saying so. Reload and another device resume the stored Week (Confirmed shown).

**Files.**
- `backend/app/modules/sessions/dev.py` (new), `backend/app/main.py` -- dev lock route, mounted outside production only.
- `backend/tests/sessions/test_dev_lock.py`, `backend/tests/sessions/test_week_advance.py` (new); `backend/tests/test_authz_rules.py` -- public dev route listed.
- `frontend/src/lib/api/live.ts` (+ test) -- `refresh`: no cancelled reads.
- `frontend/src/modules/games/week-summary.ts` (+ test), `week-summary-view.tsx` (new) -- the Uke-overgang.
- `frontend/src/components/graph-over-table.tsx`, `frontend/src/modules/games/week-table-view.tsx` -- now-line move (`movedFrom`, `skip`, `onMoving`, `MOVE_MS`).
- `frontend/src/modules/games/play-page.tsx` -- wiring, announcement, dropped-draft line.
- `frontend/src/copy/nb.ts` -- `games.play.summary`.
- `frontend/e2e/support/live-game.ts` (new), `frontend/e2e/support/play.ts` (`week12`), `frontend/e2e/week-advance.spec.ts`, `frontend/e2e/week-transition.spec.ts` (new).

**Review.** Two layers (blind, edge case), 31 findings: high 0, medium 1, low 25, false 5. Patched: reduced-motion reflow at every width (medium); animation cancel and cleanup; one-step-only move; dropped line cleared on the next Uke; `refresh` for idle siblings; one-game assert; NaN guard; race version assert. Deferred: none. Rejections with reasons in the triage log.

**Follow-up review:** false (patched 1 medium, 7 low; no high).

**Founder-level decisions taken (no human in the loop).** The summary shows from stored state after a reload too and lasts until the own Order (all Uke in a Veiledet uke); it is announced and the line moves only when the page saw a one-Uke step. Delta rows: Lager and/or Restordre when either value is non-zero (Lager when both are zero). The cost line joins non-zero cost lines; the Lager part «6 lager × 0,50» is draft copy. The move lasts 1.5 s; «Hopp over» shows only while it moves. Dropped-draft copy «Uke 11 er over. Du skrev 24, men ordren ble ikke sendt.» is draft. A local-only `POST /api/dev/class-sessions/{id}/lock` (public, like the dev mailbox) stands in for Epic 8's early lock so e2e can play a real Class game. Forwarding `user:` before the scope re-read was tried and reverted (pinned rule: a deactivated User's stream ends without it). Implementation ran in the builder's own context per the runbook; two reviewers only.

**Verification.**
- Backend: full suite 2731 passed (96 s); after review patches `test_week_advance.py` 2 passed; ruff clean.
- Frontend: typecheck; Vitest 658 passed; `check:copy`; colour lint; build (compose image).
- Playwright: full suite once (406 passed; 4 failed only because a parallel local run of mine deleted their trace files; all 4 files rerun and passed); after patches week-advance, week-transition, live-updates, homes, order-confirm, order-failures, seat-status, game-start, guided-week, week-table, graph-over-table, landing: 123 passed.
- Slow new tests: `week-advance.spec.ts` 6–11 s each (Invitations through the worker, lock, Starting task); per-width transition tests ~1.3 s (axe); `test_week_advance.py` ~4 s each. No fixed sleeps.
- No migration.

**Residual risks.** The 2 s are measured on the local stack, not on 4G; the pressing page still waits for its own POST and one read (~0.8 s). The dev lock route must never reach production (it is not mounted there). Draft copy awaits the founder.
