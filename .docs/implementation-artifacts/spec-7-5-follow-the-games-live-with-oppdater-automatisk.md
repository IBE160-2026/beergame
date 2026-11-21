---
title: "Story 7.5: Follow the games live with «Oppdater automatisk»"
type: 'feature'
created: '2026-11-21'
status: 'done'
baseline_revision: '8b9d1a3282e9c4dda9fdd7418ca4ebf501710a9a'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-7-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** The Oversikt already refetches on `session:<id>` (7.1), but it always applies changes at once, re-reads the full list on every event (`cache: "no-store"`, never 304), lets rows jump groups under keyboard focus in the wall, has no «Oppdater automatisk» Bryter, no polite count announcement, a generic stale line, and three deferred gaps from 7.1–7.2: a failed background refetch keeps old data with no notice, a failed week fetch leaves a wall row empty until the game changes, and the page does not refetch when the Start date passes (UX-DR44, FR-39, NFR-5, AD-8, AD-25).

**Approach:** The overview query revalidates with its own ETag (304 keeps the same data object); the page holds a snapshot while «Oppdater automatisk» is off and counts the changed games waiting; the wall keeps its row order while focus is inside it; a throttled polite region announces the headline counts; the Tilkoblingslinje gets the Oversikt's stale and refetch-failed lines; failed week reads retry; the api adds `next_change_at` (the Start date while before it) and the page refetches then.

## Boundaries & Constraints

**Always:**
- **304:** `useClassOverview` keeps the last answer's `ETag` and sends it as `If-None-Match` (`cache: "no-store"`, so the browser never revalidates by itself); a 304 returns the previous query data object unchanged (no new `server_now`, nothing re-renders from it). Query data = `{ overview, etag, receivedAt }` so wait ticking stays tied to the answer that carried `server_now`.
- **Bryter «Oppdater automatisk»** (`components/switch.tsx`, visible label «Oppdater automatisk», state word «På»/«Av» [ASSUMPTION]) at the right of the headline-counts row, above the wall; on by default, page state only. «Oppdatert hh:mm:ss» stays visible in both states.
- **Off:** headline counts, wall, table, game list and aggregates show the snapshot taken when it was switched off (same Veggfiltre still apply; a filter change while off fetches that combination's aggregates). The live query keeps refetching. Under the Bryter, when the latest answer differs from the snapshot: «N endringer siden hh:mm» [ASSUMPTION «1 endring»] in `body` `ink` with a secondary «Oppdater»; N = games added, removed or with another `version` (at least 1 when only the ETag differs). «Oppdater» applies the latest answer and keeps the Bryter off; switching on applies it too. Wait durations keep ticking from the snapshot's `server_now` (time, not a change).
- **Focus hold:** while keyboard focus is inside the wall's grid (or the table, which already holds order, 7.3), the wall's groups and row order stay as they were at focus-in; values update in place; a new game goes at the end of its old group or a last group; rows re-group when focus leaves. Focus never moves on an update.
- **Announcement:** a visually hidden `role="status"` announces the headline counts text when it changes, at most once per 60 s (a change within the minute is announced when the minute is up, latest text only); not on first load; nothing else added is live.
- **Tilkoblingslinje on the Oversikt:** stream stale (existing `STALE_MS`) → «Ikke oppdatert siden hh:mm. Prøver igjen.» with «Last inn på nytt» (reloads the page); a background refetch that failed while data is shown → «Ikke oppdatert siden hh:mm.» [ASSUMPTION] with «Prøv igjen» (refetches); offline and «Tilkoblet igjen.» as today. Last values stay, nothing is greyed. Other pages keep their lines.
- **Weeks:** a failed `/weeks` read is retried every 10 s while it stays failed; successful ones are never refetched for the same version.
- **`next_change_at`** on `ClassOverviewOut`: `start_at` while `before_start` and a Start date is set, else null. The page refetches the overview at that moment, measured as `next_change_at − server_now` from the answer's arrival (+1 s), never by comparing with the browser clock.
- Copy in `nb.overview.live` / `nb.system`; new copy `[ASSUMPTION]`.

**Never:** no change to the SSE stream, topics or coalescing; no persistence of the Bryter; no rail or Varselbånd (7.6, 7.11); no greyed-out or hidden values while stale; no computing of statuses from the browser clock; no announcement of anything but the headline counts.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Order placed | page live, Student orders | headline and wall show the change ≤ 5 s | — |
| Unchanged | refetch, same ETag | 304, same data object, no `/weeks` read | — |
| Held | Bryter off, 2 games change | snapshot stays; «2 endringer siden 14:02» + «Oppdater» | — |
| Apply | press «Oppdater» | latest shown, line gone, Bryter still off | — |
| Focus in wall | game moves Pågår → Venter | row stays under Pågår, focus stays; after Tab out it moves | — |
| Refetch fails | data shown, 500 | data kept; «Ikke oppdatert siden hh:mm.» + «Prøv igjen» | retry refetches |
| Weeks fail | `/weeks` 500 once | row retried within 10 s and filled | — |
| Start date | `next_change_at` 30 s ahead | refetch ~31 s after the answer | — |
| Reconnect | stream drops and returns | active queries refetched (overview 304), «Tilkoblet igjen.» | — |

</intent-contract>

## Code Map

- `backend/app/modules/sessions/schemas.py:804` `ClassOverviewOut` -- add `next_change_at: AwareDatetime | None`.
- `backend/app/modules/sessions/overview.py:46-88` `class_overview` -- set it (`row["start_at"]` when `before_start`); `etag_of` covers it.
- `backend/tests/sessions/test_overview.py:37,71` -- before-start and running tests: assert the field.
- `frontend/src/lib/api/openapi.json`, `schema.ts` -- regenerate (`backend/app/openapi.py`, `npm run api:generate`).
- `frontend/src/modules/games/api.ts:25-83` -- `useClassOverview` (ETag/304, wrapper data), `useGameWeeks` (`refetchInterval` on error).
- `frontend/src/modules/games/overview-page.tsx` -- `OverviewView`/`OverviewBody`: snapshot hold, Bryter row, changes line, announcer, `next_change_at` timer, stale/failed line via `PageShell`.
- `frontend/src/modules/games/overview.ts` -- pure helpers: `changedGames(snapshot, latest)`, `holdGroups(groups, held)`.
- `frontend/src/modules/games/overview-wall.tsx` -- focus-in/out tracking around the wall; `held` prop freezes aggregates display.
- `frontend/src/components/charts/matrix-table.tsx:119-125` -- already keeps order while focused (no change).
- `frontend/src/components/connection-notice.tsx` `ConnectionLine`; `frontend/src/modules/identity/page-shell.tsx` -- a `live` option for page-specific stale/failed lines.
- `frontend/src/lib/api/live.ts` -- `useLive`, `STALE_MS` 20 s (15 s beat + slack), reconnect refetch (exists).
- `frontend/src/components/switch.tsx` -- Bryter.
- `frontend/src/copy/nb.ts:2039` `nb.overview`, `:2195` `nb.system`.
- `frontend/e2e/overview.spec.ts:94-99` -- focus test now expects the row held; `e2e/support/live-game.ts` `liveClassGame`, `orderByApi`.

## Tasks & Acceptance

**Execution:**
- `backend/app/modules/sessions/schemas.py`, `overview.py`, `tests/sessions/test_overview.py` -- `next_change_at`.
- `frontend/src/lib/api/openapi.json`, `schema.ts` -- regenerate.
- `frontend/src/modules/games/api.ts` (+ `api.test.ts` new: 304 keeps the same object, sends `If-None-Match`) -- ETag revalidation, weeks retry.
- `frontend/src/modules/games/overview.ts` (+ `overview.test.ts`) -- `changedGames`, `holdGroups`.
- `frontend/src/lib/announce.ts` (new, + test) -- `useThrottledAnnouncement(text, 60_000)`.
- `frontend/src/components/connection-notice.tsx`, `page-shell.tsx` (+ `components.test.tsx`) -- Oversikt stale/failed lines.
- `frontend/src/modules/games/overview-page.tsx`, `overview-wall.tsx` -- hold, Bryter, changes line, focus hold, timer.
- `frontend/src/copy/nb.ts` -- copy.
- `frontend/e2e/overview.spec.ts` -- live test: order → change ≤ 5 s; Bryter off holds and counts, «Oppdater» applies; focus hold; reconnect → overview 304 and «Tilkoblet igjen.»; refetch failure line; axe at 1440/320/200 % with the Bryter off.

**Acceptance Criteria:**
- Given the Oversikt open and live, when a Student places an Order, then the headline counts and the wall show it within 5 s without reload (2 s coalescing on).
- Given a refetch with nothing changed, then the overview answers 304, the page keeps the same data and no `/weeks` request is made.
- Given the Oversikt, then «Oppdater automatisk» (role switch, checked) with its state word sits above the wall at the right, and «Oppdatert hh:mm:ss» shows in both states.
- Given the Bryter off, when a game changes, then counts, wall and list stay and «1 endring siden hh:mm» with «Oppdater» shows; pressing «Oppdater» shows the change.
- Given focus on a wall cell, when its game changes group, then the row stays in place and keeps focus until focus leaves.
- Given the headline counts change, then the hidden polite region announces them at most once a minute.
- Given a failed background refetch or a stale stream, then the matching Tilkoblingslinje shows and the wall keeps its values.

## Spec Change Log

## Review Triage Log

### 2026-11-21 — Review pass
- Layers: blind hunter and edge-case hunter only (Sonnet), as the orchestrator asked for this lane; verification-gap and intent-alignment were skipped on that instruction. Both handbacks dropped; the findings were read from `review-blind-7-5.md` and `review-edge-7-5.md` in the session scratchpad.
- verdicts: 20 findings — high 0, medium 1, low 13, false 6, maybe-false 0
- findings:
  - `[medium]` `[patch]` (blind) `useHeld` holds the previous combination's placeholder rows when a Veggfilter changes while off — patched: `useHeld` takes `isPlaceholderData` and captures again until it holds the combination's own answer (`overview-wall.tsx`).
  - `[low]` `[patch]` (blind) A 304 never advances the clock in «Ikke oppdatert siden» — patched: the failed line shows `dataUpdatedAt`, the last successful read, 304 included (`overview-page.tsx`). «Oppdatert» stays the `server_now` of the last changed answer (see the edge row below).
  - `[low]` `[patch]` (blind) A failed background read is never retried — patched: the overview query refetches every 10 s while it has an answer and the last read failed (`api.ts` `OVERVIEW_RETRY_MS`); with no answer the page error and «Prøv igjen» stand as before.
  - `[low]` `[reject]` (blind) `/weeks` retries every 10 s with no cap or backoff — a game that leaves the Class leaves the overview and its query unmounts; during an outage one read per failing game per 10 s is the self-healing the deferred item asked for.
  - `[low]` `[reject]` (blind) Held rows sit under a group header that no longer matches their status — this is EXPERIENCE.md's rule (rows do not move while focus is inside); the row header reads the game's real status.
  - `[low]` `[patch]` (blind) A held game whose new status falls outside the Status filter vanished from under focus — patched: `holdGroups` runs over all groups and `admit` filters only new games (`overview.ts`, `overview-wall.tsx`); Vitest «keeps a held game outside the Status filter».
  - `[false]` `[reject]` (blind) `changedGames` counts 1 for an identical 200 — the ETag is a hash of the body without `server_now` (`etag_of`), so an identical list always answers 304 and returns the same object.
  - `[low]` `[reject]` (blind) Hooks (`useThrottledAnnouncement`, `useReadAt`, `useHeld`) lack unit tests; one long e2e — the scheduling rule is the pure `announceIn` (Vitest); the hooks run in the e2e (announcement, hold, Oppdater, 304); the unit environment is `node` with no DOM.
  - `[low]` `[reject]` (blind) The e2e uses literal 5 s/11 s/25 s windows — they are the story's 5 s target and the 10 s retry and 20 s stale limits plus slack, named in comments; importing `api.ts` into Playwright would pull the app client in.
  - `[low]` `[reject]` (blind) `ConnectionNotice` ignores `onRetry` when `action` is given; reload drops filters — no caller passes both; «Last inn på nytt» reloads by its own words.
  - `[false]` `[reject]` (blind) Synthetic `Response` and closure flags in `readOverview` are fragile; a missing ETag is untested — the 200 path reads the header (Vitest asserts `etag`), a missing header degrades to full 200s, the same-origin `ETag` is readable.
  - `[false]` `[reject]` (blind) No guard that the ETag flips with `next_change_at`/`before_start` — `etag_of` hashes the whole body but `server_now`, so any change to them changes the ETag.
  - `[medium]` `[patch]` (edge) Placeholder aggregates held under a new filter — duplicate of the first finding, same patch.
  - `[low]` `[patch]` (edge) Failed line uses `server_now` that a 304 never advances — duplicate, same patch.
  - `[low]` `[reject]` (edge) «Oppdatert» does not advance on a 304 — AC: an unchanged list answers 304 and nothing re-renders; «Oppdatert» names when the list last changed, and the Tilkoblingslinje says when it is not current.
  - `[low]` `[reject]` (edge) `onWallBlur` returns early for a removed cell, so the order may stay held — the focused cell leaves the DOM only when its game leaves the Class; MatrixWall then moves focus to another cell in the wall, and the next blur clears the hold.
  - `[low]` `[reject]` (edge) Duplicate of the `/weeks` retry cap finding — same reason.
  - `[low]` `[reject]` (edge) After 7 timed reads a DB/host clock skew over 36 s leaves the page on the allocation — needs a 36 s skew between the api host and its database; any later `session:` event or reload reads it again.
  - `[false]` `[reject]` (edge) Counts announced when the Start date passes break «not on first load» — the counts appear after the page opened, a real change; the first load says nothing.
  - `[false]` `[reject]` (edge) A backward clock step makes the wait exceed a minute — `announceIn` takes `Math.max(0, said.at + everyMs − now)`; a backward step of the browser clock is outside every other timer's model too and recovers on the next change.
- Matrix audit: Order placed, Held, Apply, Refetch fails, Weeks fail, Reconnect — `overview.spec.ts` «Oppdater automatisk …» (ran, passed); Focus in wall — `overview.spec.ts` «the Matrisevegg reads …» and Vitest `holdGroups`; Unchanged — Vitest `readOverview` (304 → same object) and the e2e reconnect step (304 with `If-None-Match`); no `/weeks` read follows because week queries are keyed by `version` with `staleTime: ∞` (7.4's e2e counts them); Start date — `test_overview.py` (`next_change_at` equals `start_at` before it, null after) and Vitest «readAgainAt» (the read lands 1 s after the api's clock reaches it, independent of the browser clock); the timer loop in `useReadAt` itself has no browser test (a Start date seconds ahead cannot be set through the api's date rules). All listed tests ran and passed.

## Design Notes

- Hold is a snapshot of the *answer*, not a pause of the query: the live query keeps reading so the change count is honest and «Oppdater» is instant.
- Change count = games whose `version` differs (plus added/removed): bounded by the class size and meaningful to a Lecturer; per-event counting would count coalesced pulses and 304s.
- `STALE_MS` stays 20 s: the stream beats every 15 s, so a 15 s limit would flag every slightly late beat.

## Verification

**Commands:**
- `cd backend && uv run pytest -q tests/sessions/test_overview.py` -- pass
- `cd frontend && npx vitest run src/modules/games src/lib src/components` -- pass
- Before commit: full backend suite; `npm run typecheck && npx vitest run && npm run lint:colours && npm run check:copy && npm run build`; Playwright `overview`, `live-updates`, `homes`, `order-confirm`, `week-advance` -- pass

## Auto Run Result

Status: done

**Summary.** The Oversikt follows the games live and can be held still.
- The overview query revalidates with its own ETag: `If-None-Match`, and a 304 hands back the same answer object, so nothing re-renders; `server_now` stays tied to the answer that carried it.
- Bryter «Oppdater automatisk» (role switch, state word «På»/«Av») at the right of the headline-counts row above the wall, on by default. Off holds the answer it showed (counts, wall, table, list, median rows) while the query keeps reading; «N endringer siden hh:mm» with a secondary «Oppdater» shows the games added, dropped or with another `version`; «Oppdater» applies them. «Oppdatert hh:mm:ss» stays in both states.
- While keyboard focus is inside the wall, rows keep their groups and places and values update in place; they re-group when focus leaves (the table already held its order).
- A visually hidden polite region says the headline counts when they change, at most once a minute, never on first load.
- Tilkoblingslinje on the Oversikt: stale stream «Ikke oppdatert siden hh:mm. Prøver igjen.» with «Last inn på nytt»; a failed background read «Ikke oppdatert siden hh:mm.» with «Prøv igjen», retried every 10 s; the last values stay, nothing greyed.
- Deferred items closed: failed `/weeks` reads retry every 10 s; a failed background read is shown; the api's new `next_change_at` (the Start date while before it) makes the page read again then.

**Files.**
- `backend/app/modules/sessions/schemas.py`, `overview.py` (`next_change_at`), `backend/tests/sessions/test_overview.py`.
- `frontend/src/lib/api/openapi.json`, `schema.ts` (regenerated).
- `frontend/src/modules/games/api.ts` (`readOverview`, `OverviewAnswer`, overview and weeks retry), `api.test.ts` (new).
- `frontend/src/modules/games/overview.ts` (`changedGames`, `orderOf`, `holdGroups`, `readAgainAt`), `overview.test.ts`.
- `frontend/src/modules/games/overview-page.tsx` (hold, Bryter, changes line, announcer, `useReadAt`, live lines), `overview-wall.tsx` (focus hold, held median rows).
- `frontend/src/lib/announce.ts` (+ test, new): `announceIn`, `useThrottledAnnouncement`.
- `frontend/src/components/connection-notice.tsx` (`action`, `LiveLines`), `frontend/src/modules/identity/page-shell.tsx` (`liveLines`), `components.test.tsx`.
- `frontend/src/copy/nb.ts` (`nb.overview.live`), `frontend/e2e/overview.spec.ts` (new live test; the focus test now expects the row held).

**Review.** 20 findings (blind 12, edge case 8; Sonnet): 0 high, 1 medium, 13 low, 6 false. Patched: 4 entries (1 medium, 3 low): placeholder median rows held under a new filter, the failed line's clock, retry of a failed overview read, a held game outside the Status filter. Deferred: none. Rejected: 6 false and 8 low, with reasons in the triage log. Follow-up review: not recommended (no high, one medium patched, covered by its own code path and the e2e).

**Verification.**
- Backend: full suite 2809 passed in 97.5 s (the other lane shares the machine). Slowest are pre-existing (`test_migrations` 13.1 s, `test_sim`/`test_sim_golden` 10–11.4 s). The new asserts sit in existing tests.
- Frontend: typecheck, Vitest (61 files, 776 tests, none over 1 s), `lint:colours`, `check:copy`, build pass.
- Playwright after the last change: `overview`, `live-updates`, `homes`, `order-confirm`, `week-advance` — 47 passed, no flaky test. The new e2e runs axe at 1280 px (Bryter off, changes line) and 320 px (stale line); the existing first test runs axe at 320 px, 200 % text and 1440 px with the Bryter on.

**Decisions taken instead of the founder.**
- State words «På»/«Av»; singular «1 endring»; failed-read line «Ikke oppdatert siden hh:mm.» with «Prøv igjen» (all `[ASSUMPTION]`).
- «N endringer» counts Class games whose `version` changed, plus added or dropped games (at least 1 for any other change), not SSE events.
- «Oppdatert» shows the `server_now` of the last changed answer; a 304 does not move it. The failed line shows the last successful read, 304 included.
- Wait durations keep ticking while held (time, not a change).
- The stale limit stays 20 s (15 s heartbeat plus slack) instead of 15 s.
- «Last inn på nytt» reloads the page; the Bryter is not remembered.
- A filter chosen while off shows that combination's current median rows.
- The Bryter sits at the right of the headline-counts row, above the filters, with the changes line under it.
- Failed `/weeks` and background overview reads retry every 10 s, with no cap.
- The page reads again 1 s after `next_change_at`, then up to 6 more times 5 s apart while the answer stays the same.
- The builder implemented in its own context, as the orchestrator instructed.

**Residual risks.**
- `useReadAt`'s timer loop has no browser test; only its time computation is unit-tested.
- With several games, the changes count and the held order are tested with one game in e2e and with several only in Vitest.
- Verification-gap and intent-alignment reviews were skipped by instruction.
