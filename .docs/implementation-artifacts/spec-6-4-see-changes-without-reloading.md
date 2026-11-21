---
title: 'Story 6.4: See changes without reloading'
type: 'feature'
created: '2026-11-20'
status: 'done'
baseline_revision: '9b40a913bb60a8d9c62623d8180951a26887b6e8'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-6-context.md'
warnings: ['oversized']
deferred:
  - summary: >-
      A Class session or Class game created after a staff member's stream connected is not in that stream's scope until the stream reconnects (at most 13 minutes) or the User's own user event arrives.
    evidence: |-
      resolve_scope runs on connect and on the User's own user:<id> event only; sessions.create emits session:<id> alone, so a co-owner's open Lærerhjem does not see a session the other owner just created until the next reconnect. Re-resolving on every unknown session id would cost a database read per stream per event; a per-Class topic or a staff user event on create would settle it.
    location: >-
      backend/app/platform/events/stream.py (events, resolve_scope)
    severity: medium
---

<intent-contract>

## Intent

**Problem:** Every mutation already emits `NOTIFY events {topic, id, version}` (`platform/events.emit`, registry), but nothing listens: no `GET /api/events`, no `topics.ts`. Open pages (Hjem, Klasseøkt, Lærerhjem) only change after a reload or an own action, and the Tilkoblingslinje cannot tell quiet from stale.

**Approach:** One `LISTEN` hub per `backend` process fans events out in memory to a FastAPI native SSE stream per User at `GET /api/events`, filtered by the User's `platform/authz` scope. The web app opens one `EventSource` while logged in; `frontend/src/lib/api/topics.ts` maps each event to TanStack Query keys, which are invalidated and refetched over REST. Stream health drives the Tilkoblingslinje.

## Boundaries & Constraints

**Always:**
- Hub (`backend/app/platform/events/hub.py`): one psycopg `AsyncConnection` (autocommit, libpq DSN from `settings.database_url`) running `LISTEN events`, started on the first subscriber; each subscriber gets an `asyncio.Queue`. A malformed payload is skipped and logged. If the LISTEN connection fails, every subscriber is ended (its stream closes, the browser reconnects and refetches) and the next subscriber starts a new connection. `close()` runs in the app lifespan's shutdown.
- Scope (`platform/authz`, tables by name only): add `class_sessions_staffed_by(user)` (Class sessions of Classes the User is staff of) and `class_games_staffed_by(user)` (Games of those sessions). Allowed topics = `user:<own id>`; `game:<id>` for `own_seat(user)` ∪ staffed games; `session:<id>` for staffed sessions only (a Student never gets one). `debrief:` is forwarded to nobody until Epic 9 adds its scope. Resolved on connect and again on every own `user:<id>` event, each with a short-lived DB session; the stream holds none between.
- Stream (`backend/app/platform/events/stream.py`, route `GET /api/events`, policy `events.read` = ANY_USER, `response_class=EventSourceResponse`): first event `ready` (sent after subscribing, `retry: 2000`); each forwarded event is the default `message` event with data exactly `{topic, id, version}`; `heartbeat` event every 15 s; `session:<id>` coalesced per id to at most one per 2 s (the first goes at once, later ones within the window collapse into one sent at the window's end); the server ends the stream after a random 600–780 s. On an own `user:<id>` event the principal is re-loaded through the registered loader with the cookie's session version; if None (deactivated, password reset) the stream ends before forwarding. Timings are module constants a test may override.
- Caddy: `/api/*` already has `flush_interval -1`; add a backend test asserting it stays (extend `tests/test_proxy_config.py`).
- Web: `frontend/src/lib/api/topics.ts` is the only topic → key map and imports the key constructors from the modules' `api.ts`: `user` → `meKey`, `enrolledSessionsKey` (Hjem, `GET /api/me/class-sessions`), `enrolledClassesKey`, `classesKey` («Klassene dine»), `lecturerHomeKey`, `["class-sessions","seat-choice"]`, `["games","mine"]`; `session:<id>` → `classSessionKey(id)`, `allocationKey(id)`, `lecturerHomeKey`, `["class-sessions","of-class"]`; `game:<id>` → `["games","mine",id]`; unknown topic → none. Prefix invalidation; no version comparison, every event invalidates.
- `frontend/src/lib/api/live.ts`: a store (`useSyncExternalStore`) with `status: connecting | live | stale` and `lastBeat`; `LiveUpdates` (rendered in `Providers`) opens `EventSource("/api/events")` only while the cached `meKey` holds a User (observer with `enabled: false`, so it never fetches `/me` itself) and closes it on logout. `ready` → live; a `ready` after an earlier one (reconnect) refetches every active query. `message` → invalidate `topicKeys(event)`. Stale when no `ready`/`heartbeat`/`message` for 20 s (checked each 5 s); on stale → back to live the line shows «Tilkoblet igjen.» for 5 s. An `EventSource` that ends `CLOSED` (e.g. 401) is reopened after 5 s while the User is still cached.
- `ConnectionLine` order: offline («Frakoblet. …» + «Sist oppdatert HH:MM» of the page's data) → page error → stale (new copy `nb.system.stale` [ASSUMPTION] «Siden oppdateres ikke av seg selv akkurat nå.» + «Sist oppdatert HH:MM» of `lastBeat`) → reconnected (network or stream). Polite status region, never moves focus.

**Never:** No data in events; no client-side merge of event data; no polling fallback; no change to emitters, registry entries or commands; no websockets; no `debrief` scope; no edit of `sprint-status.yaml`; no change to «class-of-1994».

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Connect | logged-in User | `ready`, then forwarded events, heartbeat each 15 s | — |
| Not logged in | no cookie / expired | — | 401 `not_authenticated` / `session_expired` |
| Student, own game | `game:<own>` | forwarded | — |
| Student, session | `session:<their session>` | dropped | — |
| Staff, session ×3 in 2 s | `session:<staffed>` | 1 at once, 1 at window end | — |
| Other user | `user:<other>` | dropped | — |
| Newly seated | own `user:` then `game:<new>` | scope re-resolved, game forwarded | — |
| Deactivated | own `user:` after deactivation | stream ends, user event not sent | — |
| Lifetime | 600–780 s | stream ends; browser reconnects, refetches active queries | — |
| Bad payload | non-JSON / unknown topic | skipped | logged |

</intent-contract>

## Code Map

- `backend/app/platform/events/__init__.py` -- `CHANNEL`, `TOPICS`, `payload`; export hub/stream pieces here or keep them in submodules.
- `backend/app/platform/events/registry.py` -- read-only (no command added).
- `backend/app/platform/authz.py:180` `own_seat`, `:151` `classes_visible_to`, `:77` POLICIES (add `events.read`), `:208` `current_principal`, `_loader` (re-check via `(user_id, session_version)`).
- `backend/app/platform/auth.py` -- `COOKIE_NAME`, `read_session(token)` → `.user_id`, `.version`.
- `backend/app/platform/db.py` -- `get_sessionmaker()`; `settings.database_url` is `postgresql+psycopg://`, convert with `make_url(...).set(drivername="postgresql")` as `tests/conftest.py:libpq_dsn`.
- `backend/.venv/.../fastapi/sse.py` -- `EventSourceResponse`, `ServerSentEvent(data|raw_data, event, id, retry)`; FastAPI pings `: ping` on its own every 15 s idle (invisible to `EventSource`, so the explicit `heartbeat` event is needed).
- `backend/app/main.py:43` lifespan (close hub), `:95` include router.
- `backend/tests/test_events.py` -- LISTEN test pattern; `tests/identity/helpers.py` `client`, `login`; `tests/sessions/test_student_home.py` helpers for seated Students and staff; `tests/test_proxy_config.py`.
- `frontend/src/app/providers.tsx` -- QueryClient; mount `LiveUpdates`. `refetchOnReconnect: false` and the `online` listener stay.
- `frontend/src/components/connection-notice.tsx` `ConnectionLine`; `frontend/src/lib/connection.ts` `useConnection`, `RECONNECTED_MS`, `formatClock`.
- Keys: `modules/identity/api.ts:13` `meKey`; `modules/sessions/api.ts` `classSessionKey`, `allocationKey`, `lecturerHomeKey`, `enrolledSessionsKey`, `seatChoiceKey`; `modules/classes/api.ts` `classesKey`, `enrolledClassesKey`; `modules/games/api.ts` `myGameKey`.
- `frontend/src/modules/games/home.ts:46` `deadlineText` (e2e expectation); `modules/games/student-hjem.tsx:126` «Neste frist».
- E2E patterns: `e2e/student-choice.spec.ts` (`register`, `studentPage` with demo `studentN@`), `e2e/class-session-allocation.spec.ts` (`sessionWithStudents`, draw + confirm through the api, `a.confirmed`), `e2e/class-session-dates.spec.ts` (`saveDates`), `e2e/support/classes.ts` (`freshLecturerWithAddress`, `lecturerPage`, `test.lecturerSession`).

## Tasks & Acceptance

**Execution:**
- `backend/app/platform/authz.py` -- `events.read`, `class_sessions_staffed_by`, `class_games_staffed_by`; docstring.
- `backend/app/platform/events/hub.py` -- `Hub` (subscribe/unsubscribe context, listener task, end-all on failure, close) and module `hub`.
- `backend/app/platform/events/stream.py` -- `Scope`, `resolve_scope(user_id)`, `events(user_id, session_version, hub, ...)` async generator, `router` with `GET /api/events`.
- `backend/app/main.py` -- include router, close hub on shutdown.
- `backend/tests/platform/test_event_stream.py` -- generator with a fake hub for every matrix row (scope, coalescing, heartbeat, lifetime, deactivation, bad payload, re-resolve), hub with real `NOTIFY`, route end-to-end through a raw ASGI driver (login cookie, `ready`, a committed `emit`, disconnect) and 401; no fixed sleeps (short timings, awaited events).
- `backend/tests/test_proxy_config.py` -- already asserts `flush_interval -1` on `/api` (no change needed).
- `frontend/src/lib/api/openapi.json`, `schema.ts` -- regenerate.
- `frontend/src/lib/api/topics.ts` (+ `topics.test.ts`) -- `topicKeys(event)`, `parseEvent(data)`.
- `frontend/src/lib/api/live.ts` (+ `live.test.ts` with fake timers and a fake `EventSource`) -- store, `LiveUpdates`.
- `frontend/src/app/providers.tsx`, `frontend/src/components/connection-notice.tsx`, `frontend/src/copy/nb.ts` (`system.stale`) -- wiring and line.
- `frontend/e2e/live-updates.spec.ts` -- the two live flows, reconnect, missed heartbeat.

**Acceptance Criteria:**
- Given a Student (demo `student8@`, registered on a fresh Class, removed again at the end) on Hjem with focus on an element, when the Lecturer moves the Spillfrist through the api, then Hjem shows the new «Spillfrist …» within 2 s without reload and focus has not moved.
- Given two co-owners, one on the Klasseøkt with focus on an element, when the other draws and confirms the allocation through the api, then the first sees «Fordelingen er bekreftet.» without reload and focus has not moved.
- Given a live page, when the stream is cut and comes back (network offline/online), then «Frakoblet. Det du har skrevet, er tatt vare på på denne enheten.» shows while offline, «Tilkoblet igjen.» after, and the page's data is fetched again.
- Given a live page with a page clock, when 25 s pass without a heartbeat, then the Tilkoblingslinje shows the stale line with «Sist oppdatert HH:MM».

## Spec Change Log

## Review Triage Log

### 2026-11-20 — Review pass
- verdicts: 46 findings — high 0, medium 5, low 34, false 7, maybe-false 0
- findings:
  - `[medium]` `[patch]` blind: a LISTEN connection lost without a reset waits silently while heartbeats go on. The hub now connects with TCP keepalives (`KEEPALIVES`), so such a drop fails within about two minutes and ends every stream.
  - `[medium]` `[defer]` blind: scope refreshes only on the User's own `user:` event; a staff member misses a session created after connecting. Deferred (frontmatter): the fix needs a new topic or emission, not a direct correction.
  - `[false]` `[reject]` blind: deactivation may not emit `user:<id>`. `identity.deactivate_user` emits `user` (registry), and the new route test deactivates a User and sees the stream end.
  - `[low]` `[reject]` blind: subscriber queues unbounded. A queue grows only while its own stream awaits one short read; a cap and overflow policy add state for a case not shown to occur.
  - `[medium]` `[patch]` blind: a refused stream (401) retried every 5 s for ever with no way to «Logg inn». On `CLOSED` the web app now invalidates `meKey`: an ended session goes to «Logg inn» through the existing handler, a logged-out one closes the stream (tested in `live.test.ts`).
  - `[low]` `[reject]` blind: reconnects without jitter. The server's lifetime is already random (600–780 s); a restart storm is one REST read per open page.
  - `[low]` `[reject]` blind: each lifetime rollover refetches every visible query. The story asks for exactly that on reconnect; one read per 10–13 minutes per page.
  - `[low]` `[reject]` blind: one EventSource per tab may hit the HTTP/1.1 limit of 6. Needs six tabs on one origin over HTTP/1.1; production runs behind an HTTP/2 edge.
  - `[false]` `[reject]` blind: `version` unused. AD-8: clients never drop an event by comparing versions; every event invalidates.
  - `[low]` `[reject]` blind: `session:` invalidates every Class's session list. The event carries no Class id; the extra reads are inactive queries marked stale.
  - `[low]` `[reject]` blind: prefix keys hard-coded beside the factories. Prefixes are not factory outputs; `topics.test.ts` checks them against the factories' keys.
  - `[false]` `[reject]` blind: staff get `game:` with no staff view invalidated. No staff game view exists yet; the map gains one with its story.
  - `[false]` `[reject]` blind: Admins would hold every id. `classes_visible_to` reads `class_staff` only; an Admin who is not staff gets `user:` only.
  - `[low]` `[reject]` blind: `ENDED` may be queued twice. The stream returns on the first; the queue is then dropped.
  - `[low]` `[reject]` blind: subscribe after `close()` starts a new connection. Only in the instant of shutdown; the process ends right after.
  - `[low]` `[reject]` blind: lifespan without try/finally. Same pattern as the existing `db.dispose()`; a crashing lifespan ends the process.
  - `[low]` `[patch]` blind: no test of a lost LISTEN connection. Added `test_the_hub_ends_its_subscribers_when_the_connection_is_lost` (`pg_terminate_backend`, then a new subscriber receives again).
  - `[low]` `[reject]` blind: no test that pending coalesced events are dropped at the end. Harmless; the browser reconnects and reads everything.
  - `[low]` `[reject]` blind: e2e stale test stops before recovery. Recovery is pinned in `live.test.ts`; a real beat would add up to 15 s to the suite.
  - `[low]` `[patch]` blind: Student context not closed in `finally`. Moved into `finally`.
  - `[low]` `[reject]` blind: lifetime draw not tested. One `random.uniform` over the asserted constants.
  - `[low]` `[patch]` blind: web `parseEvent` accepts an empty id. Now refused (tested).
  - `[low]` `[reject]` blind: `data-live` attribute in production. One attribute on `<html>`, no behaviour; it lets the e2e tests wait without sleeps.
  - `[false]` `[reject]` blind: stale copy `[ASSUMPTION]`. Draft copy is marked for the founder's review by convention (#31).
  - `[low]` `[patch]` edge: a pending `session:` event sent after the scope narrowed. Pending events are filtered by the new scope on re-resolve.
  - `[low]` `[reject]` edge: a database error in `resolve`/`still_active` breaks the stream. The stream ends with an error and the browser reconnects and reads again, the same outcome as a clean end.
  - `[low]` `[reject]` edge: unbounded queue. As blind 4.
  - `[low]` `[patch]` edge: orphaned `ready.wait()` task on cancel. `waiter.cancel()` now in `finally`.
  - `[low]` `[reject]` edge: subscribe after close. As blind 15.
  - `[medium]` `[patch]` edge: 401 retried for ever. As blind 5.
  - `[low]` `[reject]` edge: «Tilkoblet igjen.» after a first connect slower than 20 s. The page showed itself stale before; saying it is connected now is true.
  - `[low]` `[reject]` edge: «Sist oppdatert» shows the connect start when the stream never opened. The page's data was read at about that time.
  - `[low]` `[patch]` edge: e2e context leak. As blind 20.
  - `[low]` `[reject]` edge (claim): spec says an observer with `enabled: false`; code reads the cache directly. The code avoids an observer bringing its own options to `/me`; the fix is a spec edit.
  - `[low]` `[reject]` edge (claim): spec's `events(...)` signature differs. Internal signature; the fix is a spec edit.
  - `[low]` `[patch]` verification-gap: the route never checked against a really deactivated User. Added `test_a_deactivated_users_stream_ends_without_their_event` over raw ASGI.
  - `[low]` `[patch]` verification-gap: lost LISTEN connection untested. As blind 17.
  - `[medium]` `[patch]` verification-gap (other): 401 loop. As blind 5.
  - `[low]` `[reject]` intent: no real Student over the real endpoint withheld a `session:`. `resolve_scope` (real data: a Student gets no session) and `allows` are each tested; the route test joins hub, scope and stream.
  - `[low]` `[reject]` intent: "holds no database session" untested. By construction: the policy and each re-read use their own short session.
  - `[low]` `[reject]` intent: the reconnect e2e cannot tell the stream's refetch from the `online` one. The stream path is pinned in `live.test.ts`; both refetch, which is the intent.
  - `[low]` `[reject]` intent: a short stream drop with the network up shows no line. AD-8 marks staleness by a missed heartbeat; the browser reconnects within 2 s and the page reads again.
  - `[low]` `[reject]` intent: one page-level stale line with a lead sentence. The Tilkoblingslinje is EXPERIENCE.md's place for stale data and needs a sentence; the time stamp is the one asked for.
  - `[false]` `[reject]` intent: «Neste frist» depends on an emission the diff does not pin. `sessions.save` emits `user` per Student (registry and its tests), and the e2e covers it end to end.
  - `[low]` `[reject]` intent: no e2e of the Lærerhjem live. The story asks Playwright for two flows; `topics.test.ts` pins the Lærerhjem key.
  - `[false]` `[reject]` intent: generated client not in the reviewed diff. Excluded on purpose (generated); regenerated with `python -m app.openapi` and `npm run api:generate`.

All four reviewers finished; their reports were read from their transcripts because their completion notices did not arrive. No visual reviewer: the only visible change is the Tilkoblingslinje's new stale sentence in the existing component (axe-checked at 320 px).

## Design Notes

Founder-level decisions: `ready` event (not `onopen`) marks a live stream, so a refetch after reconnect never races the subscription; heartbeat as a named event because `EventSource` ignores comments; stale after 20 s (one missed 15 s beat plus slack); stale copy drafted; staff get `game:` of their sessions' Class games, Admin gets only `user:`; a lost LISTEN connection ends all streams rather than silently missing events.

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/platform/test_event_stream.py tests/test_events.py tests/test_proxy_config.py -q` -- pass
- `cd backend && uv run pytest -q && uv run ruff check . && uv run ruff format --check .` -- pass
- `cd frontend && npm run typecheck && npm test && npm run check:copy && npm run build && npx playwright test --workers=2` -- pass

## Auto Run Result

Status: done

**Summary.** Open pages now follow changes by themselves. Each `backend` process holds one `LISTEN events` connection (`platform/events/hub.py`, with TCP keepalives) and fans events out in memory to `GET /api/events`, a FastAPI native SSE stream per logged-in User (`platform/events/stream.py`). The stream sends `ready` once subscribed, then `{topic, id, version}` only for topics the User's `platform/authz` scope allows (own `user:`; `game:` of own Seats and of staffed Class sessions; `session:` for Class staff only), a `heartbeat` event every 15 s, coalesces `session:<id>` to one per 2 s, re-resolves the scope and re-checks the User on each own `user:` event (ending the stream when deactivated), and ends after a random 600–780 s. A lost LISTEN connection ends every stream so the browser reconnects and reads again. The web app opens one `EventSource` while `/me` holds a User (`lib/api/live.ts`); `lib/api/topics.ts` is the only topic → query-key map; every event invalidates and TanStack Query refetches over REST; a `ready` after a reconnect refetches every visible query; a refused stream reads `/me` again (an ended session goes to «Logg inn»). No beat for 20 s shows the Tilkoblingslinje «Siden oppdateres ikke av seg selv akkurat nå.» with «Sist oppdatert HH:MM»; the line returns to «Tilkoblet igjen.» for 5 s. Caddy already flushed `/api/*` immediately (`flush_interval -1`, existing `tests/test_proxy_config.py`), so it was not changed.

**Files.**
- `backend/app/platform/events/hub.py` (new) -- one LISTEN connection, fan-out, payload parsing, end-all on loss.
- `backend/app/platform/events/stream.py` (new) -- `Scope`, `resolve_scope`, `allows`, `events()` generator, `GET /api/events`.
- `backend/app/platform/authz.py` -- `events.read`, `class_sessions_staffed_by`, `class_games_staffed_by`, `load_principal`.
- `backend/app/main.py` -- router; hub closed on shutdown.
- `backend/tests/platform/test_event_stream.py` (new) -- every matrix row; real NOTIFY; lost connection; route end to end over raw ASGI incl. a deactivated User; 401.
- `frontend/src/lib/api/{topics.ts,topics.test.ts,live.ts,live.test.ts}` (new) -- map, stream client, store.
- `frontend/src/app/providers.tsx`, `components/connection-notice.tsx`, `copy/nb.ts` (`system.stale`, [ASSUMPTION]) -- wiring and the stale line.
- `frontend/src/lib/api/{openapi.json,schema.ts}` -- regenerated (`streamEvents`).
- `frontend/e2e/live-updates.spec.ts` (new) -- Spillfrist moved → Student Hjem within 2 s, focus kept; co-owner confirms → Klasseøkt, focus kept; offline/online; missed heartbeat at 320 px with axe.
- `frontend/e2e/class-archive.spec.ts`, `class-session-allocation.spec.ts` -- three tests of a page changed "meanwhile" now block `/api/events`, since the page otherwise updates live before the refused action (the first full run failed one of them).

**Review.** One pass, 46 findings (high 0, medium 5, low 34, false 7). Patched: 2 medium entries (TCP keepalives on the LISTEN connection; refused stream re-reads `/me` instead of retrying for ever) and 7 low (pending coalesced event filtered on scope change, waiter cancelled in `finally`, empty event id refused, e2e context closed in `finally`, two new backend tests: lost LISTEN connection, deactivated User over the real route). Deferred 1 medium: a Class session created after a staff member's stream connected is outside its scope until reconnect. All rejections with reasons in the triage log.

**Follow-up review:** true. Two medium entries were patched; the patched code was verified by the full suites but not reviewed again. The named unverified risk: the keepalive settings were not exercised against a silent network drop, and the `/me` re-read on a refused stream was tested only with a fake `EventSource`.

**Founder-level decisions taken (no human in the loop).** `ready` event marks a live stream and drives the reconnect refetch (not `onopen`); heartbeat as a named SSE event (browsers ignore comments); stale after 20 s; stale copy «Siden oppdateres ikke av seg selv akkurat nå.» drafted; staff receive `game:` of their sessions' Class games, an Admin only `user:`; `debrief:` forwarded to nobody until Epic 9; a lost LISTEN connection ends all streams; a refused stream retries after 5 s and re-reads `/me`; `user:` also invalidates `/me`, the Class lists and own games, `session:` every Class's session list (the event carries no Class id); demo Student `student8@` is registered on a fresh Class for the e2e and removed afterwards; a `data-live` attribute on `<html>` lets e2e wait without sleeps. The implementation ran in the orchestrating agent's own context (caller's runbook), not a separate implementation subagent.

**Verification.**
- Backend: 2651 passed (64 s); ruff check and format clean. New tests each under 1 s (slowest: scope test 0.6–1.0 s).
- Frontend: typecheck, Vitest 493 passed, `check:copy`, build; compose rebuilt; Playwright full run `--workers=2`: 309 passed (5.8 min). The four new e2e tests take about 8 s together; none uses a fixed sleep (they wait on `data-live` and on page clocks).
- No migration.

**Residual risks.** Draft stale copy awaits the founder (#31). Scope gap for sessions created after connect (deferred). One stream per tab; on plain HTTP/1.1 more than six tabs on one origin would starve REST.
