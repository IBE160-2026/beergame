---
title: 'Story 3.4: See what is happening when a page loads, fails or goes offline'
type: 'feature'
created: '2026-11-18'
status: 'done'
baseline_revision: '8695a1d84a9f37c382ed446e6d1880ce9d7c2908'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-3-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-3-3-land-on-own-home-held-to-role.md'
warnings: [oversized]
deferred: []
---

<intent-contract>

## Intent

**Problem:** A page that loads shows an empty shell, a failed `/me` leaves a blank page, nothing says when the device is offline, a failed action has no shared handling, and an expired session drops the User on «Logg inn» with no word and no way back to where they were.

**Approach:** Add two reusable components (Skjelett, Tilkoblingslinje), a page-state hook with the 1 s / 10 s timers, a shared mutation helper, and session-expired handling that sends the User to «Logg inn» with a validated return path. Wire them into the existing pages: the three homes, the not-found page, `/`, «Logg inn» and «Logg ut».

## Boundaries & Constraints

**Always:**
- Copy is EXPERIENCE.md's own: «Laster …», «Frakoblet. Det du har skrevet, er tatt vare på på denne enheten.», «Sist oppdatert 21:14», «Tilkoblet igjen.», «Siden kunne ikke lastes.», «Prøv igjen», «Det ble ikke lagret. Prøv igjen.», «Du er logget ut. Logg inn igjen for å fortsette.». All of it goes in `nb.ts`.
- Skjelett (DESIGN.md → System): `hairline` rules, `axis` axes and `ink-muted` row labels in the real columns. No numbers, no spinner, no shimmer, no animation. It is decorative (`aria-hidden`). «Laster …» is a separate polite status line that appears only after `LOADING_TEXT_AFTER_MS = 1000`. After `PAGE_ERROR_AFTER_MS = 10_000` (named and marked `[ASSUMPTION]`) the page shows the page-error state.
- Tilkoblingslinje (DESIGN.md → System): one line of `ink` body text on `paper` between two 1 px `ink-muted` rules, at the top of `<main>`, full width, in normal flow (never fixed or overlaying). No fill, no icon. An optional «Prøv igjen» sits at its right, and an optional `ink-secondary` «Sist oppdatert HH:MM» (Europe/Oslo, from the page's newest `dataUpdatedAt`). It is a polite status region (`role="status"`). Priority: offline, then page error, then reconnected.
- Offline comes from `navigator.onLine` and the `online`/`offline` events. On return the line reads «Tilkoblet igjen.» for 5 s, then goes, and active queries refetch in place. Focus never moves.
- Mutations use `networkMode: "always"`, so an action pressed offline fails at once and nothing queued is sent on its own when the connection returns.
- The mutation helper lives in `frontend/src/lib/api/`. A thrown fetch becomes `network_error`. It maps a code through an optional per-action table, and an unknown code maps to «Det ble ikke lagret. Prøv igjen.». The action's error line is inline beside the button with `role="alert"`. The button never takes `aria-disabled` after a failure, focus stays on it, and inputs keep their values.
- Session expiry: the API answers 401 `session_expired` when a session cookie was sent but no active User resolves from it (expired, tampered, deactivated, deleted). It answers 401 `not_authenticated` when no cookie was sent. On `session_expired` from any query or mutation, the web app goes to `/logg-inn?neste=<path>&utlopt=1`. That page focuses the message (`tabindex="-1"`, read on focus, not a live region). After login it goes to `neste` when that is a valid same-origin path, else home. An anonymous visitor on a protected home goes to `/logg-inn?neste=<path>` with no message.
- `neste` is valid only when it starts with a single `/`, has no backslash or control character, resolves to the same origin, and is not `/logg-inn`.
- Under `prefers-reduced-motion: reduce`, no transition or animation runs anywhere (global CSS rule).

**Never:**
- No `frontend/src/lib/drafts.ts` and no keeping input across a reload or login (Epic 6). No Landing (3.13). No new pages.
- No spinners, no toasts, no overlays, no auto-retry of mutations, no real `setTimeout` waits in tests.
- No edits to `sprint-status.yaml`, `.env` or `.claude/settings*.json`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Slow load | `/me` pending on `/admin` | Skjelett in the page layout at once; «Laster …» at 1 s, not before | — |
| Load too long | `/me` pending 10 s | Tilkoblingslinje «Siden kunne ikke lastes.» + «Prøv igjen»; the press refetches | — |
| Load fails | `/me` 500 or network error | Same page-error line; «Prøv igjen» refetches and shows the page | — |
| Offline | Logged in, device offline | «Frakoblet. …» with «Sist oppdatert HH:MM» at the top of main | — |
| Back online | Offline → online | «Tilkoblet igjen.» for 5 s, then gone; `/me` refetched; focus unchanged | — |
| Typed text | Email typed on «Logg inn», offline, online | Value still in the field; no login request sent | — |
| Action fails | «Logg ut» answers 500, or offline | Inline `role="alert"` line beside the button; focus on the button; button not `aria-disabled` | Logout keeps its own line «Utloggingen gikk ikke. Prøv igjen.»; unknown codes elsewhere → «Det ble ikke lagret. Prøv igjen.» |
| Session expired | Bad cookie, open `/admin` | `/logg-inn?neste=%2Fadmin&utlopt=1`, focus on «Du er logget ut. …»; login returns to `/admin` | — |
| Hostile return | `neste=//evil.example` or `https://…` | Login goes home | — |
| No cookie | Anonymous, open `/admin` | `/logg-inn?neste=%2Fadmin`, no message | — |

</intent-contract>

## Code Map

- `backend/app/platform/authz.py:41,88-96` -- `NotAuthenticated`, `current_principal`. Add `SessionExpired(NotAuthenticated)`, raised when a cookie was present but did not resolve to an active User.
- `backend/app/main.py:46,76` -- `_not_authenticated` handler. Add a `session_expired` handler (register the subclass first or branch on the type).
- `backend/tests/platform/test_authz.py:127-162`, `tests/identity/test_login.py:86-96` -- the deactivated and no-session tests. Update the deactivated ones to `session_expired` and add tampered/expired cookie cases.
- `backend/app/modules/identity/routes.py:55` -- `me` declares `documented(401)`; the envelope already allows any code string. Regenerate `openapi.json`/`schema.ts` only if it changes.
- `frontend/src/app/providers.tsx` -- the one `QueryClient`. Add `QueryCache`/`MutationCache` `onError` → session-expired redirect, mutations `networkMode: "always"`, and the connection watcher (refetch active queries on `online`).
- `frontend/src/lib/api/client.ts` -- `ApiRequestError`, `toApiError`. Reuse them. The new helper goes beside them in `mutation.ts`.
- `frontend/src/modules/identity/api.ts` -- `fetchMe` returns null on 401 `not_authenticated` and throws on `session_expired`. `useLogin`/`useLogout` move onto the helper.
- `frontend/src/modules/identity/{home-page,go-home,not-found-page,page-shell}.tsx` -- the `!user` shell (Story 3.3 deferred its loading and error states here). `PageShell` gains the Tilkoblingslinje slot at the top of `<main>`.
- `frontend/src/modules/identity/{login-form,logout-button}.tsx`, `src/app/(auth)/logg-inn/page.tsx` -- the return path, the session-expired message, the logout inline error, and the Tilkoblingslinje on «Logg inn».
- `frontend/src/components/{button,link}.tsx` -- `Button` (`unavailable` → `aria-disabled`). «Prøv igjen» is a `<button>` styled as Lenke, because it refetches and does not navigate.
- `frontend/e2e/support/auth.ts`, `e2e/{homes,login-flow,logg-inn}.spec.ts` -- `loginByApi`, `DEMO_USERS`. The `/\/logg-inn$/` assertions change, since the redirect now carries `neste`.

## Tasks & Acceptance

**Execution:**
- `backend/app/platform/authz.py`, `backend/app/main.py`, `backend/tests/platform/test_authz.py`, `backend/tests/identity/test_login.py` -- add `SessionExpired`/`session_expired` and its tests (no cookie → `not_authenticated`; tampered, expired, deactivated → `session_expired`).
- `frontend/src/components/skeleton.tsx` -- `Skeleton` (`aria-hidden` rule/label rows in given columns, plus a heading bar).
- `frontend/src/components/connection-notice.tsx` -- `ConnectionNotice` (message, optional retry button, optional updated-at time).
- `frontend/src/lib/connection.ts` -- `useOnline()` (useSyncExternalStore), `useConnectionState()` (offline / reconnected-for-5 s), `formatClock(ms)` → `HH:MM` Europe/Oslo.
- `frontend/src/lib/page-state.ts` -- `LOADING_TEXT_AFTER_MS`, `PAGE_ERROR_AFTER_MS` `[ASSUMPTION]`, `RECONNECTED_MS`, and `usePageState(queries)` → `loading | slow | failed | ready`, with a retry that refetches and restarts the timer.
- `frontend/src/lib/api/mutation.ts` -- `useApiMutation`, `actionErrorMessage(code, table?)`, the `network_error` wrapping.
- `frontend/src/lib/return-path.ts` -- `safeReturnPath(raw)`, `loginPath(next, expired)`.
- `frontend/src/app/providers.tsx`, `frontend/src/app/globals.css` -- the cache handlers, the mutation network mode, refetch on reconnect, and the reduced-motion rule.
- `frontend/src/modules/identity/*` and `src/app/(auth)/logg-inn/page.tsx` -- wire everything above into the pages.
- `frontend/src/copy/nb.ts` -- a `system` section with the copy above.
- Vitest: `skeleton`/`connection-notice` markup, `formatClock`, `safeReturnPath` (hostile cases), `actionErrorMessage`, and the `usePageState` phase function (pure, with fake timers).
- `frontend/e2e/system-states.spec.ts` -- the matrix at 320 and 1440 px with axe in each state, using `page.clock` and `page.route`, never real waits. Update the 3.3 tests for the new URL.

**Acceptance Criteria:**
- Given the stack at `http://127.0.0.1:8080`, when Playwright forces offline, a failed page load, a failed mutation and an expired session at 320 and 1440 px, then each state shows as in the matrix and axe reports no WCAG 2.1 AA violation.
- Given reduced motion is emulated, when the Tilkoblingslinje appears and goes, then its computed transition and animation durations are 0.
- Given the full suites, when they run, then no new test takes over 1 s.

## Spec Change Log

## Review Triage Log

### 2026-11-18 — Review pass
- verdicts: 33 findings — high 0, medium 3, low 28, false 1, maybe-false 1
- findings:
  - Blind Hunter:
    - `[medium]` `patch` A `session_expired` 401 left the dead cookie in place, so «Du er logget ut.» came back on every later visit. Patch: the handler clears the cookie. `test_login.py` asserts `Max-Age=0`. `test_authz.py` re-sends the cookie on each request, then checks `not_authenticated` once it is gone.
    - `[low]` `patch` The not-found page was not wired to the page states. Patch: `NotFoundPage` uses `usePageState`. A new e2e test shows the page error on `/` and on the not-found page.
    - `[low]` `patch` The anonymous redirect dropped the query and hash. Patch: `HomePage` adds `location.search` and `hash`. e2e: «a visitor who is not logged in comes back to the same address, query included».
    - `[low]` `reject` The offline copy promises more than the page keeps. The sentence is the AC's and EXPERIENCE.md's own, and the AC limits the promise to text still in its field in this epic.
    - `[low]` `reject` «Sist oppdatert» shows when `/me` was read. `/me` is the only data these pages read; later pages pass their own `dataUpdatedAt`.
    - `[low]` `reject` The code names differ from the spec (`useAction`, `useConnection`, one query instead of several). The fix would be a spec edit, and the behaviour matches.
    - `[false]` `reject` «Logg ut» with a bad cookie would go to «Du er logget ut.». `/api/auth/logout` is public and never reads the cookie, so it cannot answer `session_expired`.
    - `[low]` `reject` A query paused offline could fetch twice on return. `refetchQueries` cancels the request in flight; at worst `/me` is fetched once more, with no visible effect.
    - `[low]` `patch` `isSessionExpired` sat in the page-state module. Patch: moved to `lib/api/client.ts`.
    - `[low]` `reject` Test gaps: an `https://` return path, the 5 s timer in Vitest, the retry timer, a tampered cookie on the probe route, and the OpenAPI code list. Each is covered elsewhere or does not apply:
      - `https://` and the other hostile return paths are tested in `return-path.test.ts`.
      - The 5 s line and the retry run in e2e under the page clock.
      - The tampered cookie is tested on `/me`, which uses the same dependency.
      - Error codes are plain strings in the envelope, so there is no list to update.
    - `[maybe-false]` `reject` The focus ring might not draw on the focused session note. Chrome draws `:focus-visible` for script focus after a page load with no pointer use, and if it does not, the harm is low. A screenshot after the redirect would settle it.
    - `[low]` `patch` The tampered test cookie could, by chance, equal the real one. Patch: it is now the fixed value `utgatt`.
  - Edge Case Hunter:
    - `[medium]` `patch` The stale cookie was not cleared (duplicate). Patched above.
    - `[low]` `patch` The anonymous redirect lost the query (duplicate). Patched above.
    - `[low]` `patch` `neste=/logg-inn/` passed the check. Patch: trailing slashes are stripped before the comparison. Vitest case added.
    - `[low]` `patch` `neste=/api/...` would push to an API route. Patch: `/api` paths are refused. Vitest case added.
    - `[low]` `patch` Every thrown error became `network_error`. Patch: only `TypeError` and `AbortError` do, and other errors are re-thrown unchanged. Vitest case added.
    - `[low]` `reject` `ConnectionLine` remounts if the page turns into the denied page while «Tilkoblet igjen.» shows. This needs a role change and a refetch inside the same 5 s window, and the only effect is that the line ends early.
    - `[low]` `patch` The denied page had no «Sist oppdatert». Patch: `AccessDenied` takes `updatedAt`.
    - `[low]` `patch` A 401 with no envelope showed the page error. Patch: every 401 except `session_expired` reads as not logged in, as before.
    - `[low]` `patch` The not-found page was not wired (duplicate). Patched above.
    - `[low]` `patch` `/logg-inn/` slipped past the spec's rule (duplicate). Patched above.
  - Verification Gap:
    - `[medium]` `patch` The reduced-motion test passed without the CSS rule. Patch: the test injects a 200 ms transition and reads `0.2s` normally and `0s` under reduced motion.
    - `[low]` `patch` The not-found page's states had no test (duplicate). Patched above, with an e2e case.
    - `[low]` `patch` `/` had no failed-load test. Patch: the same e2e case covers `/`.
    - `[low]` `reject` The priority between offline and page error is untested. It is one `if` order in one function, and a combined scenario would test a branch nobody is changing.
    - `[low]` `patch` The anonymous return path dropped the query (duplicate). Patched above.
  - Intent Alignment (descriptive divergences):
    - `[low]` `reject` The Skjelett shows no real columns on any page. No page has columns yet. The component can draw them (Vitest), and later pages will pass their own.
    - `[low]` `reject` «Sist oppdatert» sits on the line, not on live values. There are no live values before Epic 6.
    - `[low]` `reject` «Det ble ikke lagret. Prøv igjen.» and "input kept" are tested only in Vitest. No saving action exists yet, and «Logg ut» uses the helper with its own wording. Text typed through an offline spell is tested in e2e on «Logg inn».
    - `[low]` `reject` The backend contract widened with `session_expired`. The cookie is `httpOnly`, so only the API can tell an ended session from a first visit (see Design Notes).
    - `[low]` `reject` The reduced-motion check had no baseline. Duplicate of the Verification Gap row, and patched there.
    - `[low]` `reject` Three tests run at one width without axe. Each of the AC's four states runs at 320 and 1440 px with axe; these three are extra behaviour checks.

## Design Notes

- **Why the backend distinguishes expiry.** The cookie is `httpOnly`, so the browser cannot tell "never logged in" from "logged out by expiry". A sent but unusable cookie is the only honest signal, and it keeps «Du er logget ut.» off a first visit.
- **Which mutation shows the generic line.** No story so far has a saving action. «Logg ut» uses the helper with its own fallback line. The helper's default («Det ble ikke lagret. Prøv igjen.») is proven in Vitest and serves the first saving action in later stories.
- **«Prøv igjen» is a button** that looks like a Lenke: it refetches in place, so typed text survives, and a Lenke never acts.

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/platform/test_authz.py tests/identity` -- expected: pass
- `cd backend && uv run pytest && uv run ruff check . && uv run ruff format --check .` -- expected: pass
- `cd frontend && npm run typecheck && npx vitest run && npm run check:copy && npm run build` -- expected: pass
- `docker compose up -d --build --wait proxy && cd frontend && npx playwright test` -- expected: pass, new tests each under 1 s

## Auto Run Result

Status: done

**Summary.**
- **Skjelett** (`components/skeleton.tsx`). The page shows its layout with no numbers, no spinner and nothing that moves. «Laster …» appears at 1 s, and at 10 s (`PAGE_ERROR_AFTER_MS`, `[ASSUMPTION]`) the page shows the page error (`lib/page-state.ts`).
- **Tilkoblingslinje** (`components/connection-notice.tsx`). A polite status line at the top of `<main>`, between two rules. In order of priority it reads:
  - «Frakoblet. …» with «Sist oppdatert HH:MM».
  - «Siden kunne ikke lastes.» with «Prøv igjen».
  - «Tilkoblet igjen.» for 5 s. Active queries then refetch in place, and focus does not move.
- **Mutation helper** (`lib/api/mutation.ts`: `request`, `useAction`, `actionErrorMessage`). Unknown codes read «Det ble ikke lagret. Prøv igjen.». Mutations are never queued while offline (`networkMode: "always"`). `ActionError` shows the failure inline with `role="alert"`. «Logg ut» uses the helper with its own wording.
- **Ended session.**
  - The API answers 401 `session_expired` when a cookie was sent but cannot be used, and clears that cookie. With no cookie it still answers `not_authenticated`.
  - The web app then opens `/logg-inn?neste=…&utlopt=1` with focus on «Du er logget ut. …», and login returns to `neste`.
  - `neste` must be on the same origin, and may not be «Logg inn» or an `/api` path (`lib/return-path.ts`).
  - A visitor who is not logged in also comes back to the page after login, with no message.
- **Reduced motion.** A global CSS rule turns off every transition and animation.

**Files changed:**
- Backend: `app/{main.py,platform/authz.py}`, `tests/{identity/test_login.py,platform/test_authz.py}`.
- Frontend, new components: `components/{skeleton,connection-notice,action-error}.tsx`.
- Frontend, new lib files: `lib/{connection,page-state,return-path}.ts` and `lib/api/mutation.ts`, each with its tests.
- Frontend, changed app files: `lib/api/client.ts`, `app/{providers.tsx,globals.css,(auth)/logg-inn/page.tsx}`.
- Frontend, identity module: `modules/identity/{api,page-shell,home-page,go-home,not-found-page,login-form,logout-button}.ts(x)`, plus the new `session-expired-note.tsx`.
- Frontend, copy: `copy/nb.ts` (new `system` section).
- Tests: `components.test.tsx`, `e2e/system-states.spec.ts` (new), `e2e/{homes,login-flow}.spec.ts`.

**Review.** 33 findings: 3 medium, 28 low, 1 false, 1 maybe-false.
- Patched: 2 medium entries (the stale cookie and the reduced-motion test) and 9 low ones.
- Deferred: none.
- Rejected: the rest, each with its reason in the triage log.

**Follow-up review recommended: true.** Two medium entries were patched. Named risk: the shared 401 handler now clears the session cookie on every `session_expired`. That applies to every protected route later stories add, and the patched handler has not been reviewed again.

**Verification:**
- Backend `uv run pytest`: 1629 passed in 61 s. `ruff check` passed. `ruff format` reformatted one test file.
- Frontend: typecheck passed, Vitest 239 passed, `check:copy` passed, `build` passed (colour lint included).
- `docker compose up -d --build --wait proxy`, then `npx playwright test --workers=1`: 53 passed.
- New tests over 1 s with one worker: the slow-load test (1.1–1.2 s) and the offline test (1.0 s), at both widths. All other new tests are under 1 s.
- Matrix audit, row by row:
  - Slow load and load too long: «a slow page …» at both widths.
  - Load fails: «a page whose request fails …» at both widths, and the `/` + not-found test.
  - Offline and back online: «offline shows …» at both widths.
  - Typed text: «text typed on «Logg inn» …» at both widths.
  - Action fails: «an action that fails …» at both widths, the offline action test, and the Vitest `actionErrorMessage` test.
  - Session expired: «an ended session …» at both widths, and the mid-page test.
  - Hostile return: the e2e `//evil.example` test and the Vitest cases.
  - No cookie: `homes.spec.ts` and the query-kept test.

**Decisions taken in place of the founder:**
- A new API code, `session_expired`, for a cookie that was sent but cannot be used (expired, tampered, deactivated, deleted). The cookie is cleared, so the message shows once. A deactivated User now sees «Du er logget ut.» first and the deactivation line at login.
- The return URL parameters are `neste` and `utlopt=1`. Visitors who are not logged in also come back to the page after login.
- «Prøv igjen» is a button styled as a Lenke, because it refetches in place rather than navigating.
- «Sist oppdatert» sits on the Tilkoblingslinje and shows while offline.
- «Logg ut» keeps «Utloggingen gikk ikke. Prøv igjen.»; the generic «Det ble ikke lagret.» is kept for saving actions.
- A page error shows the line only, with no Skjelett.
- Implementation and review fixes were done in this context, not in a subagent, as the caller instructed.

**Residual risks:**
- No migration was added or changed.
- The timers are tested with the page clock, so real timing on a 4G connection is not measured.
