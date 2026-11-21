---
title: "Story 6.13: Never lose or double an Order on a bad connection"
type: 'feature'
created: '2026-11-20'
status: 'done'
baseline_revision: '137776ce2d1e5bba89e60610fd9e667369d2584b'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-6-context.md'
warnings: ['multiple-goals', 'oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** A failed, slow or offline send of «Bekreft ordre på 24» (Story 6.12) silently returns to the typed state: the Student is not told whether the Order was sent, so may think they ordered when they did not, or press again not knowing (FR-24, FR-26, NFR-5, AD-2, AD-10, AD-19, UX-DR59, UX-DR60). Also Issue #130: «Sender ordre på 24 …» can wrap the «…» alone.

**Approach:** The backend already refuses a second Order (`409 order_exists`, row lock, unique `(game_id, week, seat_id)`); an api race test proves it. The play screen's send learns the failure states: after any failure it asks the server (re-reads the play envelope) and shows Confirmed when the Order is stored, else Submit failed or the code's Norwegian copy; a send unanswered after the order-submit timeout shows «Vi vet ikke om ordren kom fram. Sjekker …» and does the same check; offline with a typed value says «Ordren på 24 er ikke sendt.». Copy in `nb.ts`, with a non-breaking space before every «…» in the order copy.

## Boundaries & Constraints

**Always:**
- Submit failed: assertive visible `role="alert"` «Ordren ble ikke sendt. Ingenting er bestilt ennå.»; field keeps the value, editable; button active «Prøv å sende 24 igjen» and keeps focus. Typing a new value clears the message and the button reads «Bekreft ordre på N» again.
- After every failed send (any code, network error, timeout) the envelope is read again before anything is shown. If the Order is stored (own turn has an Order, or the Uke moved on), it is Confirmed exactly as a success (draft dropped, focus on «Ordren på N er sendt.» or the new Uke heading). `order_exists` always counts as stored.
- `week_not_open` → «Uke 11 er over. Ordren på 24 ble ikke sendt.»; `seat_not_yours` → «Du har ikke dette setet lenger. Ordren på 24 ble ikke sendt.» [ASSUMPTION draft copy], both as the alert, after the re-read; any other code or a re-read that fails → Submit failed.
- Timeout: `ORDER_SUBMIT_TIMEOUT_MS = 10_000` (placeholder, one named constant in `play-page.tsx`). When it passes the request is aborted, a visible polite «Vi vet ikke om ordren kom fram. Sjekker …» shows, the button stays busy («Sender ordre på 24 …») with focus; the check re-reads the envelope (itself bounded by the same timeout) and ends in Confirmed or Submit failed — never left in Submitting.
- Offline (`useConnection()`) with a valid typed value and nothing on its way: visible polite «Ordren på 24 er ikke sendt.» in the order area (the Tilkoblingslinje shows too); on return for `RECONNECTED_MS`: «Tilkoblet igjen. Ordren er ikke sendt ennå.» with «Bekreft ordre på 24». Nothing is ever sent without a press; a press while offline fails at once (Submit failed).
- The send runs through `useMutation` so the shared `MutationCache` sends a `session_expired` answer to «Logg inn» with the way back; the draft stays, so after login 24 is restored and unsent.
- Live regions exist before their text; focus moves only on Confirmed (as 6.12).
- `nb.ts`: `sending` and the new `checking` use ` …` (Issue #130).

**Never:** No automatic resend or queueing; no client `version`; no backend behaviour change; no «Venter på …» (6.14); no Uke-overgang (6.15); no fixed sleeps in tests.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Fails, not stored | POST 503 / network error; envelope has no Order | alert «Ordren ble ikke sendt. …», «Prøv å sende 24 igjen», focus on it, 24 editable | draft kept |
| Fails, but stored | POST fails; envelope turn.order 24 | Confirmed «Ordren på 24 er sendt.» focused | draft dropped |
| Retry / 2nd device | POST 409 `order_exists`; stored 9 | Confirmed «Ordren på 9 er sendt.» | — |
| Week gone | 409 `week_not_open`; envelope Uke 14 | Uke 14 empty field + «Uke 11 er over. Ordren på 24 ble ikke sendt.» | — |
| Seat gone | 409 `seat_not_yours`, same Uke | seat copy alert | — |
| Timed out | no answer 10 s | «Vi vet ikke om … Sjekker …», busy, focus on button; then Confirmed or Submit failed | request aborted |
| Offline typed | offline, 24 typed | «Ordren på 24 er ikke sendt.» + Tilkoblingslinje; online → «Tilkoblet igjen. Ordren er ikke sendt ennå.», no POST | — |
| Expiry mid-submit | POST 401 `session_expired` | «Logg inn» with return; after login 24 restored, unsent | — |
| Race | two POSTs at once | one 204, one 409 `order_exists`, one row | — |

</intent-contract>

## Code Map

- `frontend/src/modules/games/play-page.tsx:197` `useSendOrder` -- today `placeOrder(...).then(ok, reread)`; becomes a `useMutation` send with timeout/abort, re-read check (`queryClient.refetchQueries(..., {throwOnError:true})` then `getQueryData<PlayEnvelope>(playKey)`), outcome state `{week, kind, value}`; `Running:167` passes new props to `OrderField`; `onText` clears the outcome.
- `frontend/src/modules/games/api.ts:42` `placeOrder` -- add optional `signal` (openapi-fetch 0.17 passes RequestInit `signal`); `lib/api/mutation.ts:15` `request` maps AbortError to `network_error`.
- `frontend/src/modules/games/order-field.tsx:97` `Editable` -- add props `checking`, `failure` (alert text), `retry`; visible alert + polite regions above the button; offline/reconnected line from `useConnection()` (`lib/connection.ts:31`); sr-only polite (sending/stepped) silent while checking.
- `frontend/src/app/providers.tsx:27` `MutationCache.onError` -- already redirects on `session_expired`; reused by running the send as a mutation.
- `frontend/src/copy/nb.ts:1505` `games.play.order` -- `sending` nbsp; new `failed`, `retry`, `checking`, `offline`, `reconnected`, `weekGone`, `seatGone`.
- `frontend/src/modules/games/order-field.test.tsx:94` -- render-state tests (regex on `Sender ordre på 24 …` must take the nbsp).
- `frontend/e2e/order-confirm.spec.ts` -- stub pattern (`openPlay`, `stub.answer`, `refetch`, `drafts`, expiry login); its «a send that fails …» test changes (now Submit failed copy, retry label).
- `backend/tests/sessions/test_orders.py:67` -- api helpers `free_week`, `order`, `code`, `weeks_and_orders`; `tests/games/test_place_order.py:422` `asyncio.gather` race pattern.

## Tasks & Acceptance

**Execution:**
- `backend/tests/sessions/test_orders.py` -- add race test: two api POSTs for the same Seat and Week via `asyncio.gather` (values 9 and 24), repeated a few times on fresh Uker or games as cheap: exactly one 204 and one `409 order_exists`; one `seat_weeks` row holding the 204's value.
- `frontend/src/copy/nb.ts` -- new strings and nbsp.
- `frontend/src/modules/games/api.ts` -- `signal`.
- `frontend/src/modules/games/order-field.tsx` + `order-field.test.tsx` -- failure/retry/checking/offline rendering; unit tests for failed, retry label, checking, the nbsp.
- `frontend/src/modules/games/play-page.tsx` -- send states as above.
- `frontend/e2e/order-failures.spec.ts` (new) -- per 320/360/1440 with `page.clock`: failed (alert text, retry label, focus, axe), offline then online (texts, Tilkoblingslinje, no POST, axe), timed out (fast-forward 10 s with held POST and held re-read: checking text, focus, busy, axe; then stored → Confirmed); plus single-width: timed out then not stored → Submit failed; failed but stored → Confirmed; `week_not_open`; `seat_not_yours`; expiry in the middle of a submit.
- `frontend/e2e/order-confirm.spec.ts` -- update the 503 test's expectations to the Submit-failed state.

**Acceptance Criteria:**
- Given 24 typed and pressed, when the request fails and the Order is not stored, then the alert reads «Ordren ble ikke sendt. Ingenting er bestilt ennå.», 24 stays editable and the focused button reads «Prøv å sende 24 igjen».
- Given an Order already stored, when the Student retries or a second device sends, then the api answers `409 order_exists`, the stored Order is unchanged and the screen shows Confirmed with the stored value; an api test races two sends and gets one 204 and one 409.
- Given no answer after 10 s, then «Vi vet ikke om ordren kom fram. Sjekker …» shows politely with focus on the button, and the screen ends in Confirmed or Submit failed.
- Given offline with 24 typed, then «Ordren på 24 er ikke sendt.» and the Tilkoblingslinje show; back online «Tilkoblet igjen. Ordren er ikke sendt ennå.» and «Bekreft ordre på 24»; nothing is sent.
- Given the session expires during a submit, when the Student logs in again, then the same Uke shows 24 unsent.
- Given Playwright with axe at 320, 360 and 1440 px, when the failed, timed-out and offline states render, then there is no violation and tap targets are ≥ 44 px.

## Spec Change Log

## Review Triage Log

### 2026-11-21 — Review pass
- verdicts: 37 findings — high 0, medium 5, low 26, false 6, maybe-false 0
- findings:
  - `[medium]` `[patch]` blind: `week_not_open` shown as «ikke sendt» although the Order is stored (retry after an Order that completed the Uke; api checks `week_not_open` before `order_exists`) — `week_not_open` now goes through `stored()`; e2e «a retry of an Order that arrived and completed the Uke» added; the backend race test shows the loser of the Week-completing race gets `week_not_open`.
  - `[low]` `[reject]` blind: «unknown» reported as «Ingenting er bestilt ennå» when the check read fails — the spine's Timed out row ends in Confirmed or Submit failed, no third state; a retry is safe (`order_exists`/history check).
  - `[low]` `[patch]` blind: `seatGone` needs a successful re-read, which a lost Seat usually loses (403) — `seat_not_yours` now maps to `seatGone` unless the Order is stored.
  - `[false]` `[reject]` blind: another device's different Order confirmed without explanation — the AC asks for exactly this: «shows the Confirmed state with the stored value».
  - `[low]` `[patch]` blind: missing history row read as `other` — now `null` (unknown).
  - `[medium]` `[patch]` blind: re-reads after 204 / `order_exists` / `week_not_open` unbounded, Submitting could hang — `reread()` now bounded by `within(…, ORDER_SUBMIT_TIMEOUT_MS)` and never throws.
  - `[low]` `[patch]` blind: draft cleared twice, before the re-read — cleared once in `confirmed()`; a 204 means the Order is stored, so dropping the draft is right.
  - `[low]` `[reject]` blind: no «Sjekker …» on a fast network failure — the spine shows it only after the timeout; the check after a fast failure takes one read.
  - `[low]` `[reject]` blind: `weekGone` stays until the next typing — typing an Order in the next Uke clears it; the case needs an Epic 8 Takeover to arise.
  - `[false]` `[reject]` blind: abort classification untested — the timeout e2e aborts the request and depends on `network_error` to reach the check.
  - `[low]` `[reject]` blind: no e2e pressing Confirm while offline — same path as the 503 failure (immediate network error), which is tested.
  - `[low]` `[patch]` blind: the check's own timeout untested — e2e «timed out, and the check gets no answer either» added (merged with verification-gap row 2).
  - `[low]` `[reject]` blind: `TIMEOUT_MS` duplicated in the e2e — importing the client module into Playwright pulls React; a drift fails the timeout tests loudly.
  - `[low]` `[patch]` blind: race may not race / runs once — now races for both Students; the second race completes the Week and shows the `week_not_open` ordering (real contention observed).
  - `[low]` `[patch]` blind: fixture-only assertion in the expiry test — removed.
  - `[false]` `[reject]` blind: nbsp test unreadable — the test writes ` ` explicitly.
  - `[low]` `[patch]` blind: stale doc comments / overlong line — `useSendOrder` and `OrderField` docs rewritten.
  - `[medium]` `[patch]` edge: `week_not_open` retry claim (high confidence) — as blind row 1.
  - `[low]` `[patch]` edge: unbounded `reread()` after 204 — as blind row 6.
  - `[low]` `[patch]` edge: unbounded `reread()` after 409 — as blind row 6.
  - `[low]` `[reject]` edge: `game_finished`/`order_invalid`/`forbidden` show a retry — the re-read then shows the finished game or the access page; `order_invalid` cannot be sent (client validates).
  - `[low]` `[patch]` edge: `seat_not_yours` with a failed read — as blind row 3.
  - `[false]` `[reject]` edge: Seat changes hands within the Uke and the new Seat ordered — `own_game` follows the Student; another Seat's Order needs Epic 8 Takeover, and then the play read is refused.
  - `[low]` `[patch]` edge: missing history row — as blind row 5.
  - `[low]` `[reject]` edge: `weekGone` persists — as blind row 9.
  - `[low]` `[patch]` edge: «Uke 11 er over» while Uke 11 still shown after a failed read — `week_not_open` now runs `stored()`; a failed read with that code still reads weekGone, which the api's code states.
  - `[low]` `[reject]` edge: timer runs after unmount — React ignores updates on unmounted hooks; the send itself must finish.
  - `[low]` `[patch]` edge (claim): race repeated once — as blind row 14.
  - `[medium]` `[patch]` edge (claim): retry of a stored Order told not sent — as blind row 1.
  - `[medium]` `[patch]` edge (claim): `week_not_open` skips the check — as blind row 1.
  - `[low]` `[patch]` edge (claim): tap targets not measured in the failure states — measured at 320/360/1440 in the per-width failure test.
  - `[low]` `[patch]` verification-gap: «Uke moved on» branches of `stored()` never run — two e2e added (same value → Confirmed with focus on Uke 14; other value → weekGone).
  - `[low]` `[patch]` verification-gap: check timeout never exercised — as blind row 12.
  - `[false]` `[reject]` intent: api codes tested only through stubs on the UI side — the house pattern (6.10–6.12); the api codes are held by `test_orders.py` and the command tests.
  - `[false]` `[reject]` intent: a different stored value not exercised — `order-confirm.spec.ts` «already ordered» stores 9 after 24 was typed.
  - `[low]` `[reject]` intent: timeout is a constant, not configuration — founder-level call recorded in Design Notes; one named constant, 10 s placeholder.
  - `[low]` `[reject]` intent: timed-out-not-there not axe-checked at three widths — its screen is the Submit-failed state, axe-checked at all three.

## Design Notes

Founder-level calls: every failure is checked against the server before speaking, so «Ingenting er bestilt ennå» is only said when the re-read shows no Order (or the re-read itself failed — then a retry is safe because it answers `order_exists`). An Uke that moved on counts as stored only when its history row holds the typed value; otherwise «Uke 11 er over. Ordren på 24 ble ikke sendt.». Editing after a failure clears the message. Messages sit between the «Kommer fram …» line and the button. The timeout is a front-end constant, not a server setting. Draft copy for `week_not_open`/`seat_not_yours` marked [ASSUMPTION].

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/sessions/test_orders.py -q` -- pass
- `cd frontend && npx vitest run src/modules/games` -- pass
- `cd frontend && npx playwright test e2e/order-failures.spec.ts e2e/order-confirm.spec.ts --workers=2` -- pass
- full: backend pytest; frontend typecheck, Vitest, check:copy, build, Playwright `--workers=2` -- pass

## Auto Run Result

Status: done

**Summary.** The play screen now says plainly whether an Order was sent. Any failed send re-reads the play envelope (bounded by the order-submit timeout) before speaking: a stored Order (`order_exists`, the open Uke's own Order, or a moved-on Uke whose history holds the typed value) shows Confirmed like a success; otherwise an assertive alert reads «Ordren ble ikke sendt. Ingenting er bestilt ennå.» with the value editable and the focused button «Prøv å sende 24 igjen», or the code's words («Uke 11 er over. Ordren på 24 ble ikke sendt.», «Du har ikke dette setet lenger. …» [ASSUMPTION]). A send unanswered after `ORDER_SUBMIT_TIMEOUT_MS` (10 s) is aborted and «Vi vet ikke om ordren kom fram. Sjekker …» shows politely with focus kept, ending in Confirmed or Submit failed. Offline with a typed value: «Ordren på 24 er ikke sendt.» beside the Tilkoblingslinje, then «Tilkoblet igjen. Ordren er ikke sendt ennå.»; nothing is sent without a press. The send runs as a mutation, so an expired session mid-submit goes to «Logg inn» and the draft returns afterwards. Issue 130: «Sender ordre på 24 …» and «Sjekker …» carry a non-breaking space before «…». No backend code changed; an api test races two sends per Student.

**Files.**
- `frontend/src/modules/games/play-page.tsx` -- `useSendOrder` as a mutation with timeout/abort, server check, outcomes; `outcomeProps`.
- `frontend/src/modules/games/order-field.tsx` -- failure alert, polite status (checking/offline/reconnected), retry label.
- `frontend/src/modules/games/api.ts` -- `placeOrder` takes a `signal`.
- `frontend/src/copy/nb.ts` -- nbsp in `sending`; `failed`, `retry`, `checking`, `offline`, `reconnected`, `weekGone`, `seatGone`.
- `frontend/src/modules/games/order-field.test.tsx` -- failure, retry, checking, nbsp tests.
- `frontend/e2e/order-failures.spec.ts` (new), `frontend/e2e/support/play.ts` (new, shared play stub), `frontend/e2e/order-confirm.spec.ts` (uses it; failed send now shows the retry label), `frontend/e2e/order-field.spec.ts` (locators for the two live regions).
- `backend/tests/sessions/test_orders.py` -- race test.

**Review.** One pass, four layers, 37 findings (high 0, medium 5, low 26, false 6). Patched: `week_not_open` now checked against the stored history (a retry of an Order that completed the Uke reads Confirmed — the race test shows the api answers `week_not_open` there); every re-read bounded so Submitting can never hang; `seat_not_yours` worded even when the read is refused; missing history row is unknown; draft cleared once; docs; tests for the moved-on branches, the check's own timeout, tap targets in failure states, a race per Student; a fixture-only assertion removed. Deferred: none. Rejections with reasons in the triage log.

**Follow-up review:** true. Patched entries: 0 high, 2 medium (grouped: `week_not_open` check; bounded re-reads), several low. Unverified risk: the reworked failure branch of `useSendOrder` (`stored()` for `week_not_open`, bounded `reread`) was verified by tests but not by a second review pass.

**Founder-level decisions taken (no human in the loop).** Every failure is checked against the server before speaking; a failed check reads as Submit failed (no third «unknown» state; retry is safe). A moved-on Uke counts as stored only if its history holds the typed value. `week_not_open`/`seat_not_yours` copy is draft [ASSUMPTION]. Editing after a failure clears the message and the button returns to «Bekreft ordre på N». Messages sit between «Kommer fram …» and the button, failure in bold `ink`, status in `ink`. The timeout is one front-end constant (10 s placeholder), not server configuration. A press while offline fails at once as Submit failed. The non-breaking space is also put in «Sjekker …». The play-screen e2e stub moved to `e2e/support/play.ts`. Implementation ran in the orchestrator's context per the runbook; reviewers were sub-agents.

**Verification.**
- Backend: full suite 2713 passed (79 s) before the review patches (which touched only `test_orders.py`; that file then 5 passed); ruff clean.
- Frontend: typecheck; Vitest 644 passed; `check:copy`; colour lint; build (compose image).
- Playwright full `--workers=2`: 390 passed, 1 failed (`order-field.spec.ts` locator now ambiguous — fixed) before the review patches; after them the order specs (30) passed.
- Slow new tests: the per-width failure test takes 3.5–4.0 s (three axe runs, as the AC asks); `test_two_sends_racing…` about 2 s (Class session setup); the rest under 1 s. No fixed sleeps (Playwright clock, held routes).
- No migration.

**Residual risks.** The e2e uses stand-in envelopes; the real route is held by `test_orders.py`. Draft copy awaits the founder. A check that fails after a timed-out send says «Ingenting er bestilt ennå» although the Order may have arrived; a retry then confirms it.
