---
title: 'Story 8.3: See on the Oversikt which Class game is closest to Takeover'
type: 'feature'
created: '2026-11-21'
status: 'done'
baseline_revision: 'd52d84c3678ca825c4e5636f00b0397f515e6bce'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-8-context.md'
warnings: [oversized]
deferred: []
---

<intent-contract>

## Intent

**Problem:** The Varselbånd (Story 7.11) names the longest-waiting game, not the one an AI player takes over next, and shows no countdown; after a Takeover (Story 8.2) the Oversikt and Spillinnsikt say only «KI-spiller», not that it took over or why.

**Approach:** `game_summaries` stores each waited-for Seat's own `takeover_due_at` and each Seat's occupancy `reason`; the overview api's pure `_alert` picks the earliest due (else the old longest-wait rule) and sends the due time; the band adds «KI overtar om 1 t.» counted from `server_now`; Oversikt rows and Spillinnsikt Seats show the AD-15 mark in text; the sweep emits the Game's events when a due Takeover does not run.

## Boundaries & Constraints

**Always:**
- **Summary** (`games/overview.recompute`): each `waiting_for` entry gains `takeover_due_at` (ISO or null, the turn's stored value); each `occupants` entry gains `reason` (latest row's). No migration: readers treat a missing key as null (rows rewrite on the Game's next command). `takeover` keeps joining the 7.1 recomputation test.
- **Alert** (`sessions/overview._alert`, pure): among `waiting` games with a waited-for Seat, the smallest game `takeover_due_at` first (games without one after all games with one, then by the 7.11 rule: wait start, game number, id); within the game the Seat with the earliest own due (missing dues last), then earliest `since`, then chain order. `OverviewAlertOut.takeover_due_at` = that Seat's due, else the game's; null when neither. Past dues still count (the sweep acts within the minute).
- **Seat marks**: `OverviewSeatOut.mark` and `InsightSeatOut.mark` = `games.service.seat_mark(None, None, occupant_kind, reason)` for an AI-held Seat, else null. Oversikt game list: «Fabrikk: KI-spiller (KI tok over etter ventetiden)»; wall row's full detail and name append «Fabrikk: KI tok over etter ventetiden» per marked Seat (short detail unchanged); Spillinnsikt Seat: the mark as caption text under the holder. Text from `nb.insight.marks` (the 7.7 mapping).
- **Band**: «Spill 2 venter på Noah (Grossist) i 23 t. KI overtar om 1 t.» — remaining = due − now (server clock, `useServerNow`), `waitDuration` words; ≤ 0 → «KI overtar nå.»; no due → the 7.11 text alone. Announcement unchanged (no times). Band accessible name becomes «Spillet nærmest at KI tar over» [ASSUMPTION]. Wraps at 320 px without page-level horizontal scroll.
- **Sweep**: when `games.takeover` is refused as a race (`TAKEOVER_RACES`), `games.service.announce(game_id)` emits `game:<id>` (current version) and, for a Class game, `session:<id>` in one transaction; registry key `ops.takeover_skipped`. `next_change_at` stays the nearest due after `server_now`.
- **Dev route** (local only, like the dev lock): `POST /api/dev/games/{game_id}/seats/{role}/takeover` runs `commands.takeover(..., actor="system", now=<that turn's stored takeover_due_at>)`; 404 without a due turn, 409 with the command's code. For e2e only.
- Copy in `nb.ts`, new strings `[ASSUMPTION]`; regenerate `openapi.json`/`schema.ts`.

**Never:** no «Pause spillet» or «Sett inn KI-spiller» (8.5–8.7); no browser-side choice of the band's game or due time; no browser clock deciding the countdown; no change to the demo Class; no waiting for real time in tests.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Due beats wait | game 1 waits since T−2h due T+22h; game 2 since T−1h due T+1h | alert = game 2, due T+1h | — |
| Tie on due | same due | lower game number | — |
| Seats differ | one game, Seat A due T+3h since earlier, Seat B due T+1h | Seat B | — |
| No dues | waiting games without due | 7.11 rule, `takeover_due_at` null, no countdown text | — |
| Mixed | game with due, game without | game with due | — |
| Old row | waits lack per-Seat due, game has due | Seat by earliest `since`, due = game's | — |
| Past due | due < now | still chosen; band «KI overtar nå.» | — |
| Taken over | only waited-for Seat taken over | game not waiting → leaves band; next game shown; Seat `mark` `takeover_inactivity` | — |
| Race skip | sweep refused `order_exists` | `game` + `session` events, no row | — |

</intent-contract>

## Code Map

- `backend/app/modules/games/overview.py:24-90` `recompute` -- add per-wait `takeover_due_at`, per-occupant `reason` (from `repo.seats_with_occupant`, which selects `reason`).
- `backend/app/modules/games/service.py:611-682` `SummarySeat`, `SummaryWait`, `ClassGameSummary`, `class_overview` -- add `reason`, `takeover_due_at` (parsed, `.get`). Add `announce(game_id)`; `seat_mark` exported (line 164).
- `backend/app/modules/games/insight.py:73-80,250-258` `InsightSeat` -- add `reason`; `games/repo` held seats query must carry `reason` (check the source of `held`).
- `backend/app/modules/sessions/overview.py:137-165` `_alert`; `_game_out:214`; `game_insight:343` seats -- marks.
- `backend/app/modules/sessions/schemas.py:768-799,946` `OverviewSeatOut`, `OverviewAlertOut`, `InsightSeatOut` -- `mark`, `takeover_due_at`; `ClassOverviewOut.alert` doc.
- `backend/app/modules/ops/sweep.py:129-143` `_take_over` -- announce on race refusal.
- `backend/app/platform/events/registry.py` -- `ops.takeover_skipped: {game, session}`.
- `backend/app/modules/sessions/dev.py` -- dev takeover route; games side `games.service.take_over_when_due(game_id, role)`.
- `frontend/src/modules/games/overview.ts:128-152,264-327` -- `bandText` countdown, `seatTexts` marks, `wallGroups` detail/rowName; `overview-band.tsx` unchanged except doc; `insight.ts`/`insight-page.tsx:170` Seat mark caption; `copy/nb.ts:2109` band copy, `overview.seatMarked`.
- Tests: `backend/tests/sessions/test_overview_alert.py` (pure matrix), `test_overview.py` (api: due on alert, mark after takeover via `tests/games/test_takeover.py` `class_game`/`due_of`), `tests/games/test_game_summaries.py` (exact occupant dict line 65, backfill test ignores new keys), `tests/ops` sweep test for the announce; Vitest `overview-band.test.ts`, `overview.test.ts`, `insight.test.ts`; e2e `varselband.spec.ts` (live regex gains «KI overtar om …»), new `frontend/e2e/takeover-overview.spec.ts`.

## Tasks & Acceptance

**Execution:**
- `backend/app/modules/games/{overview.py,service.py,insight.py,repo.py}` -- summary keys, dataclasses, `announce`, `take_over_when_due`.
- `backend/app/modules/sessions/{schemas.py,overview.py,dev.py}` -- fields, `_alert`, marks, dev route.
- `backend/app/modules/ops/sweep.py`, `platform/events/registry.py` -- announce on skipped race.
- `frontend/src/lib/api/{openapi.json,schema.ts}` -- regenerate.
- `frontend/src/modules/games/{overview.ts,overview-band.tsx,insight.ts,insight-page.tsx}`, `copy/nb.ts` -- band countdown, marks.
- Backend tests: alert matrix, api answer with `takeover_due_at` and after a takeover (mark, band moves on), summary keys, sweep announce emits exactly the registered topics, dev route 404.
- Vitest: `bandText` with future, past and missing due; `seatTexts`/`wallGroups` marks; insight Seat mark.
- E2E `takeover-overview.spec.ts`: live game with one Order → band «… KI overtar om … t.»; overview answer with the alert's due set to `server_now + 1 h` → «KI overtar om 1 t.»; dev takeover → band gone, list row and wall row name «KI tok over etter ventetiden», Spillinnsikt Seat shows it; axe and no horizontal scroll at 1440 and 320 px. Update `varselband.spec.ts` regex.

**Acceptance Criteria:**
- Given two waiting Class games, when the Oversikt loads, then the band names the one with the earliest `takeover_due_at` with «KI overtar om d.», its row is tinted, and «Venter ellers» lists the other.
- Given the countdown, when time passes, then it ticks from `server_now` and the page reads again at `next_change_at`.
- Given a Takeover, when staff read the Oversikt and Spillinnsikt, then the Seat reads «KI-spiller» with «KI tok over etter ventetiden» in text, and the band moves on or goes away.
- Given a due Takeover refused as a race, when the sweep runs, then `game` and `session` events are emitted.
- Given 1440 and 320 CSS px, when the band shows a countdown or a game was just taken over, then no page-level horizontal scroll and axe passes.

## Spec Change Log

## Review Triage Log

### 2026-11-21 — Review pass
- Layers: blind hunter and edge-case hunter only (Sonnet), as the orchestrator asked (two by default); verification-gap and intent-alignment skipped on that instruction. Both hand-backs dropped; findings read from `review-blind-8-3.md` and `review-edge-8-3.md` in the session scratchpad.
- verdicts: 25 findings (blind 14, edge 11) — high 0, medium 0, low 17, false 8, maybe-false 0
- findings:
  - `[low]` `[reject]` blind-1: `games.announce` failing inside the refusal branch is logged as a sweep item failure — the sweep logs it and retries next minute like any item; a try/except adds a branch for a case not met in use.
  - `[false]` `[reject]` blind-2: a same-version `game` event may be dropped by clients — the Oversikt reads again on `session:<id>` (`lib/api/topics.ts` invalidates the Class session's queries, version-less), which `announce` emits.
  - `[false]` `[reject]` blind-3: a persistent race code makes the sweep announce every minute — `due_takeovers` filters every candidate through `can_take_over` first, so only a change between the finder and the lock reaches the refusal.
  - `[low]` `[reject]` blind-4: registry entry not tied to the emission, test "circular" — the registry is the contract; the sweep test asserts emitted topics, ids and version against it, as every command test does.
  - `[low]` `[reject]` blind-5: no backfill of `reason` and per-Seat due in old rows — nothing is deployed; a local row rewrites at the Game's next command (every Order), and readers take a missing key as None.
  - `[false]` `[reject]` blind-6: an old row pairs the named Seat with another Seat's due — without Story 8.9's factor every due is the wait start plus the one limit, so the earliest `since` is the earliest due.
  - `[low]` `[reject]` blind-7: a past due pins the band at «KI overtar nå.» if the Takeover keeps failing — the sweep logs that failure each minute and the band says the truth (overdue); a staleness rule adds state.
  - `[low]` `[reject]` blind-8: the turn-clock guard's allowlist gains `sessions/overview.py` — the list already names the read models that copy the stored value by keyword (`games/service.py`).
  - `[low]` `[reject]` blind-9: `mark`/`takeover_due_at` optional in the schema — same pattern as `InsightSeatOut.user_id`; the page treats a missing value as none.
  - `[low]` `[reject]` blind-10: dev route details (`str(role)`, status codes, message, newest Week) — local-only e2e helper; `Role` is a StrEnum (the route test passes), the command refuses an ordered or finished Seat with its 409.
  - `[low]` `[reject]` blind-11: `__all__` order and positional `None`s to `seat_mark` — `__all__` was not alphabetical before; the positional call matches the other callers.
  - `[low]` `[patch]` blind-12: `status != "waiting"` was weak — the api test now asserts `("running", 2)`; the other gaps listed (announce for non-Class Games, 422) cover branches with no reachable caller.
  - `[low]` `[reject]` blind-13: every mark kind joins the wall row note — by design: every AI player is marked (UX-DR69 «alle merket»); the short note stays «Venter, 23 t».
  - `[low]` `[reject]` blind-14: band label wording; countdown not announced — the label is draft copy `[ASSUMPTION]`; the announcement leaves out times by Story 7.11's rule.
  - `[low]` `[patch]` edge-1: a tie on the due time went to the longer wait, not the lower game number — `started(g)` removed from the key; the tie test gives the higher-numbered game the longer wait.
  - `[low]` `[reject]` edge-2: as blind-7.
  - `[low]` `[reject]` edge-3: as blind-5.
  - `[low]` `[reject]` edge-4: `open_takeover_due` reads the newest Week, not the open one — dev route only; a finished game answers the command's 409 instead of 404.
  - `[low]` `[reject]` edge-5: invalid Role gives an undocumented 422 — FastAPI's standard validation answer on a local-only route.
  - `[false]` `[reject]` edge-6: a `CommandError` status other than 404/409 — `takeover` refuses only with 404 and 409.
  - `[false]` `[reject]` edge-7: as blind-6.
  - `[false]` `[reject]` edge-8: `MARKS[seat.mark]` could be undefined — `Record<SeatMark, string>` over the generated type fails the typecheck for a mark without words.
  - `[low]` `[patch]` edge-9: the e2e read `answer.alert.role` unguarded — now `expect(answer.alert).not.toBeNull()` first.
  - `[false]` `[reject]` edge-10: as blind-1 (same claim).
  - `[false]` `[reject]` edge-11: registry says `game`+`session` while a non-Class Game emits `game` alone — the registry convention (e.g. `games.start`) lists the Class game's set; only Class games have due Takeovers.
- Matrix audit: Due beats wait, Tie on due, Seats differ, No dues, Mixed, Old row, Past due — `test_overview_alert.py` (pure, ran); Past due on the page — `overview-band.test.ts`; Taken over — `test_overview.py::test_a_takeover_marks_the_seat_and_the_game_leaves_the_band` and `takeover-overview.spec.ts`; Race skip — `test_takeover.py::test_the_sweep_skips_a_race_and_reports_any_other_refusal`. All ran and passed.

## Design Notes

Per-Seat due in the summary (not recomputed from the limit) keeps AD-20: Story 8.9's factor makes Seats of one game differ, and the band must name the Seat whose clock runs out first. The marks reuse the one AD-15 mapping; the wall's short detail stays «Venter, 23 t» so narrow walls are unchanged. The dev route is the e2e stand-in for elapsed time: it runs the real command at the stored due time (injected clock), so the e2e sees real rows.

## Verification

**Commands:**
- `cd backend && uv run pytest -q tests/sessions/test_overview_alert.py tests/sessions/test_overview.py tests/games/test_game_summaries.py tests/games/test_takeover.py` -- pass
- `cd frontend && npx vitest run src/modules/games` -- pass
- Before commit: full backend `--maxprocesses=8`; typecheck, Vitest, `lint:colours`, `check:copy`, build; rebuilt stack; Playwright `--workers=4` takeover-overview, varselband, overview, game-insight, seat-status, live-updates, takeover, homes, play-screen specs.

## Auto Run Result

Status: done

**Summary.** The Varselbånd now names the Class game an AI player takes over first. `game_summaries` stores each waited-for Seat's own `takeover_due_at` and each Seat's occupancy `reason` (no migration; readers take a missing key as None). The overview api's pure `_alert` picks the waiting game with the earliest due time (games without one after it, by Story 7.11's longest wait; ties to the lower game number), names the Seat due first and sends `takeover_due_at`. The band reads «Spill 2 venter på Noah (Grossist) i 23 t. KI overtar om 1 t.», counted on the server clock, and «KI overtar nå.» once the time has passed; its accessible name is «Spillet nærmest at KI tar over». Every AI-held Seat carries its AD-15 mark (`mark`) on the Oversikt and Spillinnsikt: «Grossist: KI-spiller (KI tok over etter ventetiden)» in the game list, «Grossist: KI tok over etter ventetiden» in the wall row's note and name, and the mark as a caption on the Spillinnsikt Seat. After a Takeover the game no longer waits and leaves the band. When a due Takeover is refused as a race, the sweep emits the Game's `game` and `session` events (`ops.takeover_skipped`). A local-only dev route runs the real Takeover at the stored due time for e2e.

**Files.**
- `backend/app/modules/games/{overview.py,service.py,insight.py}` -- per-Seat due and reason in the summary; `announce`, `open_takeover_due`; Seat reason in insight.
- `backend/app/modules/sessions/{overview.py,schemas.py,dev.py}` -- `_alert` by due time, `mark` on Seats, `takeover_due_at` on the alert, dev Takeover route.
- `backend/app/modules/ops/sweep.py`, `platform/events/registry.py` -- announce on a skipped race.
- `frontend/src/modules/games/{overview.ts,overview-band.tsx,insight.ts,insight-page.tsx}`, `copy/nb.ts`, `lib/api/{openapi.json,schema.ts}` -- countdown, marks, copy, types.
- Tests: `backend/tests/sessions/{test_overview_alert.py,test_overview.py,test_turn_clock.py}`, `tests/games/{test_game_summaries.py,test_takeover.py}`, `tests/test_authz_rules.py`; Vitest `overview-band.test.ts`, `overview.test.ts`, `insight.test.ts`; e2e `takeover-overview.spec.ts` (new), `varselband.spec.ts` (countdown), `takeover.spec.ts` (an NBSP regex the merge with main broke).
- `.docs/implementation-artifacts/epic-8-context.md` -- recompiled (ARCHITECTURE-SPINE.md changed in Story 8.2).

**Review.** 25 findings (blind 14, edge case 11; Sonnet): 0 high, 0 medium, 17 low, 8 false. Patched (low): ties on the due time go to the lower game number, a firmer api assertion, an e2e guard. Deferred: none. Rejected: the rest, each with its reason in the Review Triage Log. Follow-up review: not recommended (patched: high 0, medium 0, low 3).

**Verification.** After the patches: backend full suite 2916 passed (`--maxprocesses=8`), ruff check and format clean; frontend typecheck, Vitest 842 passed, `lint:colours`, `check:copy`, `next build`; stack rebuilt, then Playwright `--workers=4` takeover-overview, varselband, overview, game-insight, seat-status, live-updates, takeover, homes, student-home, order-confirm, order-field, order-failures, chain-band, week-table, week-advance, guided-week, game-card, messages: 138 passed, 1 failed once (`homes.spec.ts` «320 px › lecturer opens the product and lands on their own home»: the redirect to /laererhjem not reached within 5 s under load) and passed on rerun (homes 23/23). axe at 1440 and 320 px on the Oversikt with the band one hour from Takeover and after the Takeover. New tests over 1 s: `test_overview.py::test_the_dev_takeover_runs_the_takeover_at_the_stored_due_time` and `::test_a_takeover_marks_the_seat_and_the_game_leaves_the_band` (about 1.4 s each; each starts a real Class game); `takeover-overview.spec.ts` (about 7 s, one live e2e).

**Decisions taken instead of the founder.**
- The band names the Seat due first (then the longest wait, then chain order); games with no due time come after those with one, by Story 7.11's rule; ties on the due time go to the lower game number.
- A due time that has passed still ranks first and reads «KI overtar nå.» (draft) until the sweep acts.
- The countdown uses the wait words rounded down («KI overtar om 59 min.» at 59 min 59 s).
- Every AI player's mark is shown (not only Takeovers), from the one AD-15 mapping: «Rolle: KI-spiller (merknad)» in the game list, «Rolle: merknad» in the wall row's full note and row name; the short note is unchanged. On Spillinnsikt the mark is a caption under the holder.
- The mark reads the latest occupancy row: a Play guard switch after a Takeover shows the switch.
- No migration: old summary rows lack the new keys until the Game's next command.
- The race-skip event is registered as `ops.takeover_skipped`, not as a `games.*` command.
- A local-only `POST /api/dev/games/{id}/seats/{role}/takeover` for e2e; the one-hour state is the api answer with its due time moved by a Playwright route.
- Draft copy `[ASSUMPTION]`: `overview.band.label`, `band.takeoverNow`, `overview.seatMarked`, `overview.seatMark`.
- Implemented in the builder's own context and reviewed by two Sonnet layers, as the orchestrator instructed.

**Residual risks.**
- Rows written before this story show no mark and no per-Seat due until the Game's next command (local data only).
- When Story 8.9's factor makes Seats' due times differ, an old row's fallback pairs the longest wait with the game's nearest due.
- Verification-gap and intent-alignment reviews skipped by instruction; the visual check is left to the separate visual agent.
