---
title: "Story 6.12: Confirm the Order and keep what I typed"
type: 'feature'
created: '2026-11-20'
status: 'done'
baseline_revision: 'bdd5b92efaaa4a2b43b3ebd6b7a0f39179a100dd'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-6-context.md'
warnings: ['multiple-goals', 'oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** «Bekreft ordre på 24» (Story 6.11) does nothing: a Student cannot send an Order, and a typed number is lost on reload, navigation or session expiry (FR-24, AD-2, AD-8, AD-10, UX-DR59, UX-DR60). Story 6.11 also deferred a test that the typed number clears when the Uke moves on.

**Approach:** A new api route `POST /api/me/games/{id}/weeks/{week}/order` places the Student's Order only through `games.commands.place_order`, which gains an `actor` (User id) checked against the Seat's current occupant (`409 seat_not_yours`) and emits `user:<id>` for each Student whose waiting status changed. The Ordrefelt gets its Submitting and Confirmed states, and a new `frontend/src/lib/drafts.ts` keeps unsent input in `localStorage` per User and field, cleared on logout.

## Boundaries & Constraints

**Always:**
- `place_order(..., actor=None)`: with an actor, the occupant in force for the Week must be a Student with that `user_id`, else `CommandError("seat_not_yours", 409)` before anything is written; without an actor (guided Orders, `players` jobs, rescue loop, `within`) no check. Same transaction, Game row lock, one version bump; topics `game:<id>`, `session:<id>` where `games.policy` lists the Game on the Lecturer overview, and `user:<id>` for the actor and, when the Order completed the Week (advanced or finished), for every Student holding a Seat. Registry entry becomes `{"game","session","user"}`. Client sends no `version`.
- Route body `{order: int}`; 204 on success. Command codes pass through as `409` (`seat_not_yours`, `week_not_open`, `order_exists`, `game_not_started`, `game_finished`) or `422` (`order_invalid`, `guided_order_required`); any other game answers `403 forbidden` like the other `/me/games` routes. `decided_by = "student"`.
- Submitting: button «Sender ordre på 24 …» with `aria-disabled="true"` and `aria-busy="true"`, keeps focus, ignores presses; field `readOnly`; − / + unavailable; one request per press sequence (double-press sends once).
- Success: the play envelope is read again. While the Uke is open with the own non-guided Order placed, the Confirmed state shows «Ordren på 24 er sendt.» (`tabindex="-1"`, focused right after the send) and under it «Skjermen går videre når alle har bestilt. Du får e-post hvis spillet venter på deg.» [draft copy]; no field, no undo, no dialog. The table and Kjedebånd keep the Order as in 6.11 (Din ordre at nå, Levering at the arrival Uke, thin line, band box, «På vei 16 + 24»), screen-reader cell text «din ordre» without «ikke bekreftet». If the send completed the Week, the new Uke shows with an empty field and focus moves to the Topplinje heading.
- Failure (any error): back to the typed state with the value kept and editable, focus on the button, envelope read again; messaging is Story 6.13.
- `drafts.ts`: `loadDraft(userId, field)`, `saveDraft(userId, field, value)` (empty value removes), `clearDraft`, `clearDrafts(userId, fieldPrefix)`, `clearAllDrafts()`; keys `olspillet:draft:{userId}:{field}`; every storage access in try/catch, works with storage unavailable. Order field name `order:{gameId}:{week}`. Saved on every change, removed after a successful send; drafts of the same game's other Uker are removed when an Uke is shown. Restored only into the field: never sent without a press. `useLogout` success calls `clearAllDrafts()`; session expiry does not clear.

**Never:** No «Venter på …» (6.14), no failure/timeout/offline copy or «Prøv å sende igjen» (6.13), no race test for `order_exists` (6.13), no Uke-overgang animation (6.15), no `type="number"`, no recommended or prefilled order (UX-DR78), no draft written to the server.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Confirm | Uke 11, 24 typed, press | POST `{order: 24}` once; «Sender ordre på 24 …»; then «Ordren på 24 er sendt.» focused | — |
| Last to order | send completes the Week | new Uke, empty field, focus on «Uke 12» | — |
| Not my Seat | actor ≠ occupant | `409 seat_not_yours`, nothing written | client: typed state, refetch |
| Already ordered | second POST | `409 order_exists` (existing check) | client: refetch shows Confirmed |
| Reload | 24 typed, reload | field shows 24, «Bekreft ordre på 24», nothing sent | — |
| Uke moves on | 30 typed, envelope now Uke 14 | empty field, no typed box/cell/line; Uke 11 draft removed | — |
| Session expiry | 24 typed, session ends | «Logg inn» with return; after login field shows 24, nothing sent | — |
| Logout | drafts stored | all `olspillet:draft:` keys gone | — |
| No storage | `localStorage` throws | field works as in 6.11, nothing kept | swallowed |

</intent-contract>

## Code Map

- `backend/app/modules/games/commands.py:1095` `_place` (checks + write; `occupancy` read at :1143) and `:1236` `place_order` (own transaction path calls `_commit_change`, then `_settle`); pattern for actor check and `told` user set: `view_week` :1303–1366 (`_actor` :1296).
- `backend/app/platform/events/registry.py:15` `"games.place_order"` topics.
- `backend/tests/games/test_registry.py:65` `_run_place_order` (simulation, emits `game` only) → becomes a Class runner like `_run_view_week` :101 with `FREE` settings in the snapshot (`tests/games/test_set_snapshot.py:24` `snapshot()`); add to `CLASS_SETUP_EVENTS`.
- `backend/app/modules/sessions/service.py:1325` `ViewRefused` / `view_own_week` -- pattern for `OrderRefused` / `place_own_order` (`_own_locked_game` :1247).
- `backend/app/modules/sessions/routes.py:618` view route -- pattern for the order route (`games.play_own`, `documented(...)`, `error_response`); body model in `sessions/schemas.py`.
- `backend/tests/sessions/test_guided_weeks.py` (`call`, `running`, `weeks_and_orders`) and `tests/sessions/test_play.py:67` `played_to` -- api test helpers.
- `frontend/src/lib/api/openapi.json`, `schema.ts` -- regenerate: `cd backend && uv run python -m app.openapi ../frontend/src/lib/api/openapi.json`, `cd frontend && npm run api:generate`.
- `frontend/src/modules/games/api.ts` -- add `placeOrder(gameId, week, order)` like `viewWeek`.
- `frontend/src/modules/games/play-page.tsx:119` `Running` -- typed state keyed by game+Uke; add draft load/save, send state, confirmed preview from `turn.order`, focus after send; `Topplinje` h1 gets `tabIndex={-1}`; `PlayView` passes `user.id`.
- `frontend/src/modules/games/order-field.tsx` -- `OrderField` routes `turn.order != null` to `ReadOnly`; add `Confirmed` for non-guided placed Orders; `Editable` gets `sending` and `onConfirm`.
- `frontend/src/modules/games/week-table.ts:86` `TypedOrder` (+ `confirmed?`), `week-table-view.tsx:289–309` sr text `copy.typed`.
- `frontend/src/modules/identity/api.ts:40` `useLogout` onSuccess -- `clearAllDrafts()`.
- `frontend/src/copy/nb.ts` `games.play.order` (~1485) and `table` (~1513) -- new strings.
- `frontend/e2e/order-field.spec.ts` -- stub pattern (`openPlay`, routes on `play`); its «press sends nothing» assertion at :153 changes; `e2e/system-states.spec.ts:210` expired-cookie pattern; `e2e/support/auth.ts` `loginAs`, `loginByApi`.

## Tasks & Acceptance

**Execution:**
- `backend/app/modules/games/commands.py` -- `actor` on `place_order`/`_place`, `seat_not_yours` check, `user:` events.
- `backend/app/platform/events/registry.py`, `backend/tests/games/test_registry.py` -- topics and Class runner.
- `backend/tests/games/test_place_order_actor.py` (new) -- actor accepted, other user / no Student refused with nothing written, no actor skips, `user:` events for actor only vs all Students on advance.
- `backend/app/modules/sessions/{service,routes,schemas}.py` -- `place_own_order` and route.
- `backend/tests/sessions/test_orders.py` (new) -- one Student (others Rule-based) plays to Uke 5 and orders through the api: 204, row `decided_by student`, advance; `order_exists`, `week_not_open`, `order_invalid` (−1, 1000, "24", 2.5), guided Uke `guided_order_required`, other game 403.
- `frontend/src/lib/api/openapi.json`, `schema.ts` -- regenerated.
- `frontend/src/lib/drafts.ts` + `drafts.test.ts` -- API and storage-failure cases.
- `frontend/src/modules/games/{api.ts,order-field.tsx,play-page.tsx,week-table.ts,week-table-view.tsx}`, `order-field.test.tsx`, `week-table.test.tsx`; `frontend/src/modules/identity/api.ts`; `frontend/src/copy/nb.ts`.
- `frontend/e2e/order-confirm.spec.ts` (new) -- stubbed: send (one POST with `{order:24}`, Submitting attrs and focus, held response), Confirmed (message focused, line, table and band keep 24) with axe at 320/360/1440; reload restores 24 with no POST (axe at each width); Uke moves on (deferred 6.11 test); last-to-order focus; session expiry and login restores 24, no POST; logout clears drafts (own `loginAs` session).
- `frontend/e2e/order-field.spec.ts` -- drop the «sends nothing yet» press.

**Acceptance Criteria:**
- Given 24 typed in an open non-guided Uke, when the Student presses «Bekreft ordre på 24», then exactly one Order is written through `place_order` with the actor checked, the screen shows «Sender ordre på 24 …» then «Ordren på 24 er sendt.» with focus on it and the «Skjermen går videre …» line, and nothing can change it.
- Given a typed value, when the Student reloads, leaves and returns, or logs in again after expiry, then the field holds it and nothing is sent until a press; after logout no draft remains.
- Given 30 typed in Uke 11, when the envelope moves to Uke 14, then the field is empty and no typed cell, box or line shows.
- Given Playwright with axe at 320, 360 and 1440 px, when the Submitting, Confirmed and restored states render, then there is no violation and every tap target is ≥ 44 px.

## Spec Change Log

## Review Triage Log

### 2026-11-20 — Review pass
- verdicts: 31 findings — high 0, medium 0, low 21, false 10, maybe-false 0
- findings:
  - `[false]` `[reject]` blind: the `within` path never emits `user:` — `within` is called with `advance_week=False` (commands.py `_place`), so it never completes a Week; the outer command emits, and a later Order without `within` (players jobs, rescue) that completes the Week tells every Student.
  - `[false]` `[reject]` blind: the confirmed Order may be counted twice in the preview — `stored_play` passes only the Orders of the Weeks before the open one; `test_orders.py` now asserts the whole `seat_state` (preview bases included) is unchanged after the Order.
  - `[low]` `[reject]` blind: a failed send says nothing — the intent leaves failure copy to Story 6.13 («Ordren ble ikke sendt …»); the value, focus and editability return, which this story asks.
  - `[low]` `[patch]` blind: route answers 409 `seat_not_yours` where `view` answers 403 for a lost Seat — `_own_locked_game` answers 403 for a Student who no longer holds a Seat, so 409 is only the race between that check and the write; route and `OrderRefused` docstrings now say so.
  - `[low]` `[reject]` blind: `place_own_order` resolves the Role before the lock; return type carries no information — a Seat move between the read and the lock is refused `seat_not_yours` and the screen reads again; same shape as `view_own_week`.
  - `[low]` `[reject]` blind: `loadDraft` runs on every render / SSR mismatch — `Running` renders only after the client-side play query; one `getItem` per render is negligible.
  - `[false]` `[reject]` blind: rejected promises in `useSendOrder` unhandled — `refetchQueries` resolves on query errors (no `throwOnError`), so neither branch rejects.
  - `[low]` `[reject]` blind: Confirmed shows for any non-guided placed Order — Orders by another occupant need a Takeover or guard switch (Epic 8 / LLM Seats, never a Student's); then `own_game` no longer finds the Student's Seat. «Du får e-post …» is the spine's draft copy (founder decision 2026-11-14).
  - `[false]` `[reject]` blind: drafts outlive an expired session — the AC requires it (UX-DR59); drafts are keyed by User, and a failed logout leaves the User logged in.
  - `[low]` `[patch]` blind: `guided_order_required` documented but unreachable through the route — a Guided Week's fixed Order exists at opening, so the route answers `order_exists` (tested); docs fixed. `game_not_started`/HTTP `seat_not_yours` untested: rejected, the command tests cover both.
  - `[low]` `[reject]` blind: magic 10 in `CLASS_SETUP_EVENTS`, nested imports, duplicated snapshot — same pattern as the existing `view_week` runner.
  - `[low]` `[patch]` blind: registry comment contradicts the entry — reworded: an Order without actor that completes no Week in a Game the Lecturer overview does not list emits `game` alone.
  - `[low]` `[reject]` blind: «Sender ordre på 24 …» announced twice — EXPERIENCE.md asks for a polite announcement; a focused button's label change alone is not reliably read.
  - `[low]` `[patch]` blind: send state crosses into a new Uke mid-send — `sending` now holds the Uke of the Order on its way; another Uke shown meanwhile is not Submitting.
  - `[false]` `[reject]` edge: `within` + `actor` skips user events — no caller combines them; `within` never completes a Week (as above).
  - `[low]` `[reject]` edge: `_settle` advances emit no `user:` — after a Student's Order the next Week waits for that Student, so `_settle` advances it only in Games with no Student to tell.
  - `[low]` `[reject]` edge: `seats_with_occupant` reads the latest occupancy, not the one in force — differs only after a future-dated occupancy row (Epic 8 Takeover/Reclaim), and an extra `user:` only triggers a re-read.
  - `[low]` `[patch]` edge: new Uke's field shows «Sender ordre …» if the Uke changes mid-send — same fix as the blind row.
  - `[low]` `[reject]` edge: 204 then a failed re-read leaves the field editable — the next `game:` event or reconnect re-reads; a second press gets `order_exists`, which Story 6.13 maps to Confirmed copy.
  - `[low]` `[reject]` edge: the Order that ends the game leaves focus on a removed element — the end screen is Story 6.18.
  - `[low]` `[reject]` edge: Role resolved before the lock — as the blind row on `place_own_order`.
  - `[low]` `[patch]` edge (claim): spec task said a guided Uke answers `guided_order_required`; it answers `order_exists` — the fixed Order is placed when a Guided Week opens (6.10); test asserts `order_exists`, route docs fixed.
  - `[false]` `[reject]` edge (claim): user events missed in `within` and later advances — as the rows above.
  - `[low]` `[patch]` verification-gap: no test ties the draft key to the signed-in User — the reload e2e now asserts the exact key `olspillet:draft:{me.id}:order:{game}:11`.
  - `[low]` `[patch]` verification-gap: no test that a failed send keeps the stored draft — the 503 e2e now reloads and finds 24.
  - `[low]` `[patch]` verification-gap (other): `seat_not_yours` reachable over HTTP only in a race — docstrings fixed (grouped with the blind row).
  - `[low]` `[reject]` intent: `seat_not_yours` tested only at command level — the AC places the check in the command; HTTP reach is a race.
  - `[false]` `[reject]` intent: connection loss not tested apart from reload — one mechanism (a draft saved on every change); offline states are Story 6.13.
  - `[false]` `[reject]` intent: logout clears every User's drafts — the AC says «clears all drafts on logout».
  - `[false]` `[reject]` intent: no e2e through the real route — the house pattern (6.10, 6.11) stubs the envelope; the route is held by `test_orders.py`, the stub shapes by `test_play_fixture.py`.
  - `[false]` `[reject]` intent: «who is waited for» changes for other Students not emitted — Setestatus/«Venter på» is Story 6.14; Hjem's waiting status changes for the actor and, on a Week change, for all.

## Design Notes

Founder-level calls taken here: the api answers 204 and the screen reads the envelope again (no new response model); `seat_not_yours` is `409` on this route (6.13 names it) although `view` maps it to 403; a Student whose send completes the Week sees the new Uke with focus on its heading, not the confirmation; after confirming, the table and band keep the Order as in mockup `06` C; the confirmed cells read «24, din ordre» [ASSUMPTION]; a failed send silently returns to the typed state (6.13 adds copy); drafts of other Uker of the same game are dropped when an Uke shows; `user:` is emitted for every Student only when the Order completed the Week (advances later done by `_settle` keep emitting `game` only).

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/games/test_place_order_actor.py tests/games/test_registry.py tests/sessions/test_orders.py -q` -- pass
- `cd frontend && npx vitest run src/lib/drafts.test.ts src/modules/games` -- pass
- `cd frontend && npx playwright test e2e/order-confirm.spec.ts e2e/order-field.spec.ts --workers=2` -- pass
- full: backend pytest; frontend typecheck, Vitest, check:copy, build, Playwright `--workers=2` -- pass

## Auto Run Result

Status: done

**Summary.** «Bekreft ordre på 24» now sends the Order: `POST /api/me/games/{id}/weeks/{week}/order` (`{order}`, no `version`, 204) places it only through `games.commands.place_order`, which gained an `actor`: with one, the Seat's occupant in force must be that Student or the command refuses `409 seat_not_yours` before anything about the Seat's Order is told; calls without a person skip the check. The command emits `game:`, `session:` (Lecturer overview) and `user:` for the actor and, when the Order completed the Week, for every Student of the Game (registry updated). On screen: Submitting («Sender ordre på 24 …», `aria-disabled`, `aria-busy`, focus kept, presses ignored, field read-only, − / + unavailable), then Confirmed («Ordren på 24 er sendt.» focused, `tabindex="-1"`, and «Skjermen går videre når alle har bestilt. Du får e-post hvis spillet venter på deg.»); the table and Kjedebånd keep the sent Order as in mockup `06` C. A send that completes the Uke shows the next Uke with focus on its heading. New `frontend/src/lib/drafts.ts` keeps unsent input in `localStorage` per User and field: the typed Order survives reload, leaving and session expiry, is never sent without a press, is dropped after a send and when another Uke shows, and «Logg ut» clears all drafts. The 6.11-deferred test (typed number clears when the Uke moves on) is in `order-confirm.spec.ts`.

**Files.**
- `backend/app/modules/games/commands.py` -- `actor` on `place_order`/`_place`, `seat_not_yours`, `user:` events.
- `backend/app/platform/events/registry.py` -- `games.place_order` topics `{game, session, user}`.
- `backend/app/modules/sessions/{routes,service,schemas}.py` -- order route, `place_own_order`, `OrderRefused`, `OrderIn`.
- `backend/tests/games/test_place_order_actor.py` (new), `test_registry.py` (Class runner), `test_place_order.py` (now expects the Students' `user:` events); `backend/tests/sessions/test_orders.py` (new).
- `frontend/src/lib/drafts.ts`, `drafts.test.ts` (new); `frontend/src/lib/api/{openapi.json,schema.ts}` regenerated.
- `frontend/src/modules/games/{api.ts,order-field.tsx,play-page.tsx,week-table.ts,week-table-view.tsx}` + tests -- send, Submitting, Confirmed, drafts, confirmed cells.
- `frontend/src/modules/identity/api.ts` -- logout clears drafts; `frontend/src/copy/nb.ts` -- new strings.
- `frontend/e2e/order-confirm.spec.ts` (new); `frontend/e2e/order-field.spec.ts` -- dropped «press sends nothing».

**Review.** One pass, four layers, 31 findings (high 0, medium 0, low 21, false 10). Patched (all low): `sending` tied to the Uke of the Order on its way; route/`OrderRefused`/registry docs (409 `seat_not_yours` only in a race, Guided Week answers `order_exists`); e2e asserts the exact per-User draft key and that a failed send keeps the draft over a reload; api test asserts `seat_state` is unchanged by the own Order (no double count in the preview). Deferred: none. Rejections with reasons in the triage log.

**Follow-up review:** false. Patched entries: 0 high, 0 medium, 6 low.

**Founder-level decisions taken (no human in the loop).** The route answers 204 and the screen re-reads the envelope (no response model). Over HTTP a Student who lost the Seat gets 403 like any other game; 409 `seat_not_yours` only when the Seat changes hands between the check and the write. The actor check runs before `order_exists`, so nothing about another Seat's Order is told. A Guided Week's Order through the route answers 409 `order_exists` (its fixed Order stands). `user:` goes to the actor, and to every Student when the Order completed the Week; later `_settle` advances emit `game` only. A send that completes the Uke moves focus to the new Uke's heading (no confirmation shown for the old Uke). After confirming, table and Kjedebånd keep the Order; confirmed cells read «24, din ordre» [ASSUMPTION]. A failed send returns silently to the typed state with value, draft and focus kept (copy is 6.13). Drafts of the game's other Uker are removed when an Uke shows. The Submitting text is also put in a polite live region. Draft copy «Skjermen går videre …» from open-assumptions.md. Implementation ran in the orchestrating agent's context (caller's runbook); reviewers were sub-agents.

**Verification.**
- Backend: 2712 passed (69 s) after the review patches; ruff clean.
- Frontend: typecheck; Vitest 638 passed; `check:copy`; build (local and compose image).
- Playwright full `--workers=2`: 382 passed (6.6 min) before the review patches; after them the play specs (23) passed.
- Slow new tests: `test_orders.py` tests take 0.9–1.8 s each (the Class session setup and four Guided Weeks through the api); `order-confirm.spec.ts` per-width tests take 1.2–2.0 s (axe twice per width, as the AC asks); the rest are under 1 s. No fixed sleeps.
- No migration.

**Residual risks.** Failure, timeout and offline copy wait for Story 6.13. The e2e uses stand-in envelopes; the real route is held by `test_orders.py`. Draft copy awaits the founder (#31).
