---
title: 'Story 3.3: Land on your own home and be held to your role'
type: 'feature'
created: '2026-11-18'
status: 'done'
baseline_revision: 'a734891acb08f207c2f609faa5452de0890d9eca'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-3-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-3-2-log-in-and-log-out-email-password.md'
warnings: [oversized]
deferred: []
---

<intent-contract>

## Intent

**Problem:** After login every User lands on the same placeholder at `/`. The API has no authorization layer, so nothing stops a route from going out without a role check, and nothing shows a User a refusal or a missing page.

**Approach:** Add `platform/authz` with `can(user, action, resource)` and policies that every route declares as a FastAPI dependency, guarded by a route-walking test and a role-comparison check. On the web, send each User to their own home (Admin-område, Lærerhjem or Hjem) under one shared header, with a permission-denied page and a not-found page.

## Boundaries & Constraints

**Always:**
- `platform/authz` imports no `app.modules`. It defines the roles it knows as strings (`admin`, `lecturer`), a `Principal` protocol (`id`, `roles`), `can(user, action, resource=None) -> bool` on a closed action table, `require(action)` (a FastAPI dependency that returns the principal or raises `Forbidden`), `public` (a dependency that marks a route as public), and `current_principal` (reads the cookie through `platform/auth` and calls a loader that `identity` registers at app start; it raises `NotAuthenticated`).
- Actions: `users.list`, `users.manage`, `institutions.manage`, `audit.read`, `admin_area.view` → admin. `lecturer_home.view` → lecturer. `session.read` → any logged-in User. `student_answers.read` and `ai_assessments.read` → no account role (Class-scoped grants come with the epics that create those tables). An unknown action is a programming error (`KeyError`), never a silent allow.
- `Forbidden` → 403 `forbidden`, the same body for every refusal. The policy runs before the handler, so the answer is the same whether or not the item exists. `NotAuthenticated` → 401 `not_authenticated` as before.
- Every request loads the User and roles from the database (unchanged `identity.service.load_user`); a deactivated or deleted User gets 401.
- Public routes: `GET /api/health`, `POST /api/auth/login`, `POST /api/auth/logout`. The test's public list also names the categories later stories add (password reset, Invitation acceptance, lecturer-access request, webhooks).
- Web URLs: `/admin` (Admin-område), `/laererhjem` (Lærerhjem), `/hjem` (Hjem). Home: Lecturer role → `/laererhjem`; else Admin → `/admin`; else `/hjem`. `/` and a successful login go to the home. A protected page opened anonymously goes to `/logg-inn`.
- Who may view: `/admin` needs Admin, `/laererhjem` needs Lecturer, `/hjem` needs neither staff role. Otherwise the page shows «Du har ikke tilgang til denne siden.» (h1) with one Lenke to the User's own home, at the same URL.
- One `AppHeader` for every page: product name, then on signed-in pages the User's name and «Logg ut» (secondary). The product name sits at the same height on «Logg inn» and on the homes (Issue #68). No global nav bar.
- New copy in `nb.ts`, marked `[ASSUMPTION]` where EXPERIENCE.md gives none.

**Never:**
- No Admin lists, no Klasse pages, no Hjem content (3.9–3.12, Epics 4 and 6). No Skjelett, offline line or return-after-login (3.4). No `if role ==` or equivalent inside `backend/app/modules/`.
- No edits to `sprint-status.yaml`, `.env` or `.claude/settings*.json`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Admin opens the product | Admin only, `/` | `/admin`, h1 «Admin-område», name and «Logg ut» in the header | — |
| Lecturer opens the product | Lecturer only, `/` | `/laererhjem`, h1 «Lærerhjem», no link to the Admin-område | — |
| Admin and Lecturer | Both roles, `/` | `/laererhjem` with Lenke «Til Admin-område»; `/admin` has Lenke «Til Lærerhjem» | — |
| No account role | User without roles, `/` | `/hjem`, h1 «Hjem» | — |
| Lecturer opens `/admin` | Lecturer only | «Du har ikke tilgang til denne siden.» and «Til Lærerhjem» | — |
| API refusal | Lecturer calls an admin-policy route, existing or missing id | 403 `forbidden`, identical bodies | — |
| Role granted or revoked | Role row changed between two requests, same cookie | The next request follows the new roles | — |
| Deactivated | `is_active=false`, valid cookie | 401 `not_authenticated` on every policy route | — |
| Unknown address | `/finnes-ikke` | «Fant ikke siden.» and a Lenke home (anonymous: «Til innlogging») | — |
| Anonymous on a home | No cookie, `/admin` | Goes to `/logg-inn` | — |

</intent-contract>

## Code Map

- `backend/app/platform/auth.py` -- `COOKIE_NAME`, `read_token`. `authz.current_principal` reads the cookie through these.
- `backend/app/modules/identity/service.py:30,99,108` -- `NotAuthenticated`, `load_user`, `current_user`. Move `NotAuthenticated` to `platform/authz` (re-export from identity), replace `current_user` by `authz.require("session.read")`, keep `load_user` as the registered loader.
- `backend/app/modules/identity/routes.py` -- add `Depends(authz.public)` to login and logout; `me` uses `authz.require("session.read")`.
- `backend/app/main.py` -- `/api/health` gets `authz.public`; register the loader and the `Forbidden` handler in `create_app()`.
- `backend/app/modules/identity/seed.py` -- `DEMO_USERS`; today it seeds only an empty table. Add the Admin+Lecturer and no-role Users and add every missing demo e-mail (local only).
- `backend/tests/identity/{helpers,test_seed,test_auth}.py` -- the ASGI client and login helpers; update the seed tests.
- `backend/tests/test_imports.py` -- the AST `imports` walker pattern to copy for the role check.
- `frontend/src/modules/identity/{api.ts,signed-in.tsx,login-form.tsx,logout-button.tsx}` -- `useMe`; the 3.2 placeholder (`signed-in.tsx`) is replaced; login pushes to `/`.
- `frontend/src/app/(auth)/logg-inn/page.tsx`, `src/app/page.tsx` -- the header that Issue #68 measured (`/` used `items-center` against the 44 px button).
- `frontend/src/components/link.tsx` -- `Link standalone` for the home links.
- `frontend/e2e/{login-flow,logg-inn}.spec.ts`, `e2e/support/auth.ts` -- `DEMO_USERS`, `loginByApi`, `expectAccessible` patterns.

## Tasks & Acceptance

**Execution:**
- `backend/app/platform/authz.py` -- the module above, with a docstring that Class-scoped helpers such as `classes_visible_to(user)` are added by the epic that creates their tables.
- `backend/app/modules/identity/{service,routes,seed}.py`, `backend/app/main.py` -- wire the policies, loader, handler and seed.
- `backend/tests/platform/test_authz.py` -- `can` for every action and principal (Admin, Lecturer, both, none), unknown action, the identical 403 for an existing and a missing item, grant/revoke at the next request, deactivated 401 (a test-only router on `create_app()`).
- `backend/tests/test_authz_rules.py` -- walk every `APIRoute` of `create_app()`: each has `require(...)` or `public`, and the `public` ones are exactly the allowed list; an AST check that fails on a comparison with `AccountRole`, a role string literal or a `.roles` attribute under `app/modules/`, with a self-test on bad samples.
- `backend/tests/identity/test_seed.py` -- four demo Users, idempotent, missing ones added.
- `frontend/src/modules/identity/homes.ts` (+ `homes.test.ts`) -- `homeOf(user)` and `canView(page, user)`.
- `frontend/src/components/app-header.tsx`, `breadcrumb.tsx` (+ Vitest) -- the shared header; the staff breadcrumb (renders from two items, current item `aria-current="page"`), for later epics.
- `frontend/src/modules/identity/{home-page.tsx,access-denied.tsx}`, `src/app/{page.tsx,not-found.tsx}`, `src/app/(app)/{admin,laererhjem,hjem}/page.tsx`, `(auth)/logg-inn/page.tsx` -- redirect from `/`, the three homes, the denied and not-found pages; delete `signed-in.tsx`.
- `frontend/src/copy/nb.ts` -- `homes`, `access` and `navigation` strings.
- `frontend/e2e/support/auth.ts`, `e2e/homes.spec.ts`; update `login-flow.spec.ts` -- the matrix rows at 320, 360 and 1440 with axe.
- `README.md` -- the two new demo logins and the authz rule.

**Acceptance Criteria:**
- Given any API route of `create_app()`, when the test walks the routes, then it fails on a route with no policy or a public route off the list.
- Given a role comparison inside `backend/app/modules/`, when the backend tests run in CI, then the check fails.
- Given the stack at `http://127.0.0.1:8080`, when Playwright opens the three homes, the denied page and the not-found page at 320, 360 and 1440 px, then axe reports no WCAG 2.1 AA violation and nothing scrolls sideways.
- Given «Logg inn» and a home at the same width, when both render, then the product name's top differs by less than 1 px.

## Spec Change Log

## Review Triage Log

### 2026-11-18 — Review pass
- verdicts: 34 findings — high 0, medium 0, low 31, false 3, maybe-false 0
- findings:
  - Blind Hunter:
    - `[low]` `reject` The homes show an empty shell when `/me` fails with a non-401 error. Story 3.4 owns Skjelett, the page error and the offline line (epics.md); a fix here would be redone there.
    - `[low]` `reject` An anonymous `/` is blank. The Landing is Story 3.13; the homes already send anonymous visitors to «Logg inn».
    - `[low]` `patch` The tab title still named the page that was refused. Patch: `PageShell` sets `document.title` from its h1, and the e2e refusal test asserts the title.
    - `[low]` `reject` `homes.ts` repeats the role rules of `authz.POLICIES`. No product route serves a home yet; the pages are presentation and the API enforces every request. A parity test across two languages adds machinery for no named divergence.
    - `[low]` `reject` The role-comparison guard misses set operations, `match`, `.count()` and renamed constants. The AC names `if role ==` or equivalent; the guard catches comparisons with role literals, `AccountRole`, `authz.ADMIN/LECTURER` and `.roles`, with a self-test. Wider AST matching adds complexity for patterns nobody writes today.
    - `[low]` `reject` The route walk skips WebSocket routes. There are none; the story that adds one adds its walk.
    - `[low]` `patch` A stale `PUBLIC_ROUTES` entry would whitelist a later route silently. Patch: the test also requires every listed route to be public.
    - `[low]` `reject` `require()` does not add 403 to the OpenAPI responses. `/api/auth/me` (`session.read`) never answers 403; routes that can will document it with `documented(403)` as today.
    - `[low]` `patch` A deleted demo account returns at the next start. Patch: README says so.
    - `[false]` `reject` The seed log lost its count. `platform/logging` drops unlisted fields (`ALLOWED_FIELDS`), so a count was never logged.
    - `[false]` `reject` Six parallel `loginByApi` calls may hit the per-IP limit. Successful logins give their IP count back (`service.authenticate`), and the limit is 300.
    - `[low]` `reject` A revoked role keeps the cached home until a refetch. FR-2 asks for the next page load; a reload fetches `/me` afresh.
    - `[low]` `reject` `Breadcrumb` is not mounted. The AC asks for a breadcrumb later epics extend; there is no Klasse page yet.
    - `[low]` `patch` `Breadcrumb` keyed by href collides on equal hrefs. Patch: key by index and href.
    - `[low]` `reject` The docstring test guards only a phrase. The AC is that the module documents it; the test pins exactly that.
    - `[low]` `reject` The header switches from anonymous to signed-in while `/me` loads. Loading states are Story 3.4 (Skjelett).
  - Edge Case Hunter:
    - `[low]` `reject` Homes stay an empty shell on a non-401 `/me` error. Same as the Blind Hunter row; Story 3.4.
    - `[low]` `patch` The not-found page showed no link on a non-401 `/me` error. Patch: «Til innlogging» shows whenever no User is known and the query is not pending.
    - `[low]` `reject` `/` stays blank for a logged-in User during an API outage. Story 3.4's page error.
    - `[low]` `patch` Breadcrumb key collision (duplicate of the Blind Hunter row). Patched.
    - `[low]` `reject` WebSocket or mounted routes escape the walk (duplicate). None exist.
    - `[low]` `reject` Role checks without a Compare node escape the guard (duplicate). As above.
    - `[low]` `patch` Browser contexts leaked when one case of the parallel refusal test failed. Patch: `try … finally context.close()`.
    - `[low]` `patch` The spec says the public routes are exactly the list; the test checked a subset (duplicate of the stale-entry row). Patched.
    - `[low]` `reject` The guard does not cover every "equivalent" (duplicate). As above.
    - `[low]` `reject` An anonymous visitor with a broken `/me` is stuck on a blank page (duplicate). Story 3.4.
    - `[low]` `patch` The not-found page sometimes has no link (duplicate). Patched above.
  - Verification Gap: no gaps found.
  - Intent Alignment (descriptive divergences):
    - `[low]` `reject` No product route carries an admin policy, so the same-answer rule is shown on a test-only route. «Brukere og roller» is Story 3.9; the AC asks that the API answers the same way, which the probe route proves through the real `create_app()` stack.
    - `[low]` `reject` FR-5 is tested on `can()` only. The AC says "when its policies are tested".
    - `[false]` `reject` Page access is decided in the browser. The AC's API rule is enforced on every request; a page bundle reveals no data, and the denial never says whether an item exists.
    - `[low]` `reject` No e2e reloads a page after a role change. There is no web surface to change a role until Story 3.9; the API test changes the row between two requests with one cookie.
    - `[low]` `reject` `POST /api/auth/logout` is public but not on the AC's list. It needs no session and only clears the cookie; recorded under Design Notes.
    - `[low]` `reject` `can()` ignores `resource`. The signature is the AC's; Class-scoped checks use it later, as documented.
    - `[low]` `reject` Out-of-story changes (deadlock fix, per-e-mail seed, header alignment). The deadlock blocked the new e2e logins, the seed gives the Roles the story's tests need, and Issue #68 was handed to this story.

## Design Notes

- **Lecturer first.** A User with both roles teaches daily and administers rarely, so the Lærerhjem is home (open-assumptions.md, 3.3).
- **Admin-område in this story** is a heading (and the cross-link) only. Its sections («Brukere og roller», «KI-kostnad», …) arrive with 3.9–3.12; links to pages that do not exist would be dead.
- **Strict Hjem.** Hjem is the home of a User with no staff role; staff opening it get the denied page with a link to their own home, so no page a User sees is someone else's.
- **Logout is public.** It needs no session and only clears the cookie (3.2), so it sits with login in the public list.
- **Seed per e-mail.** Existing local databases already hold the two 3.2 Users; adding only missing demo e-mails gives them the two new ones without touching anything else.

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/platform/test_authz.py tests/test_authz_rules.py tests/identity` -- expected: pass
- `cd backend && uv run pytest && uv run ruff check . && uv run ruff format --check .` -- expected: pass
- `cd frontend && npm run typecheck && npx vitest run && npm run check:copy && npm run build` -- expected: pass
- `docker compose up -d --build --wait proxy && cd frontend && npx playwright test` -- expected: pass

## Auto Run Result

Status: done

**Summary.**
- **Backend.** `platform/authz`: `can(user, action, resource)` on a closed action table, `require(action)` and `public` as FastAPI dependencies, and `current_principal`, which loads the User and roles from the database on every request through the loader `identity` registers. A refusal is 403 `forbidden`, the same for an existing and a missing item. Every route declares a policy (`/api/auth/me` → `session.read`; login, logout and health → `public`).
- **Guards.** `tests/test_authz_rules.py` walks every API route (through included routers) and fails on a missing policy or a public route off the exact list. An AST check fails on a comparison with an account role inside `app/modules/`. Both run in CI's backend `pytest`.
- **Frontend.** `/` and a login send each User home: Lecturer → `/laererhjem`, otherwise Admin → `/admin`, otherwise `/hjem`. One `AppHeader` (product name, the User's name, «Logg ut»). Admin+Lecturer get «Til Admin-område» / «Til Lærerhjem». Permission denied («Du har ikke tilgang til denne siden.» + own-home link) at the same URL; «Fant ikke siden.» for unknown addresses; anonymous visitors on a home go to «Logg inn». A `Breadcrumb` component for later epics.
- **Issue #68 settled.** The product name sits in a box as tall as a button on every page; an e2e test checks it is at the same height on «Logg inn» and a home.
- **Test logins.** The seed now adds each missing demo e-mail: `admin-faglaerer@example.com` (Admin and Lecturer) and `student@example.com` (no role) join the two from 3.2. `DEMO_USERS` roles: `admin`, `lecturer`, `adminLecturer`, `student`.
- **Bug fixed from 3.2.** Parallel right logins to one account from one address deadlocked (the success transaction locked account before IP). The lock order is now the same; a test reproduces the deadlock without the fix.

**Files changed:**
- `backend/app/platform/authz.py` (new), `platform/auth.py` (docstring).
- `backend/app/main.py`: loader, `forbidden` handler, health policy.
- `backend/app/modules/identity/{routes,service,seed,repo}.py`: policies, `current_user` replaced, lock order, per-e-mail seed, `any_user` removed.
- `backend/tests/platform/test_authz.py`, `tests/test_authz_rules.py` (new); `tests/identity/{test_seed,test_login}.py`.
- `frontend/src/components/{app-header,breadcrumb}.tsx` (new), `components.test.tsx`.
- `frontend/src/modules/identity/{homes,homes.test,home-page,page-shell,session-header,go-home,not-found-page}.ts(x)` (new); `login-form.tsx`; `signed-in.tsx` removed.
- `frontend/src/app/(app)/{admin,laererhjem,hjem}/page.tsx`, `app/not-found.tsx` (new); `app/page.tsx`, `(auth)/logg-inn/page.tsx`.
- `frontend/src/copy/nb.ts`: `homes`, `navigation`, `access`; the 3.2 placeholder line removed.
- `frontend/e2e/homes.spec.ts` (new), `login-flow.spec.ts`, `support/auth.ts`.
- `README.md`: four demo logins, the authz rule.

**Review.** 34 findings: 6 distinct patches (all low: tab title, exact public list, README seed note, breadcrumb key, not-found link on `/me` error, context cleanup in e2e), 0 deferred, the rest rejected with reasons in the triage log (mostly Story 3.4's loading/error states and the Landing in 3.13). Verification Gap: none.

**Follow-up review recommended: false.** No high or medium entry was patched.

**Verification:**
- Backend `uv run pytest`: 1629 passed in 69 s; `ruff check` and `ruff format --check` clean. New backend tests each under 0.5 s.
- Frontend: typecheck passed, Vitest 206 passed, `check:copy` passed, `npm run build` passed (colour lint included).
- `docker compose up -d --build --wait proxy`, then `npx playwright test`: 35 passed. With one worker every new test is under 1 s (0.23–0.92 s). The three 3.2 keyboard login tests now take about 1.8 s each (they were about 1.4 s).
- The regenerated OpenAPI schema and client show no drift.
- Matrix audit: Admin, Lecturer, no-role homes → `homes.spec.ts` role tests ×3 widths; Admin+Lecturer → its own test; Lecturer on `/admin` → refusal test ×3 widths plus the six-case refusal test; API refusal identical → `test_a_refusal_is_the_same_whether_or_not_the_item_exists`; role granted/revoked → `test_a_granted_or_revoked_role_counts_at_the_next_request`; deactivated → `test_a_deactivated_user_is_refused_on_every_request`; unknown address → not-found tests (logged in ×3 widths, anonymous); anonymous on a home → `a visitor who is not logged in goes from a home to «Logg inn»`.

**Decisions taken in place of the founder:**
- URLs `/admin`, `/laererhjem`, `/hjem`. Admin+Lecturer lands on the Lærerhjem (open-assumptions.md).
- Hjem is only for Users with no staff role; staff get the denied page with a link to their own home.
- The Admin-område is a heading (and the cross-link) only until Stories 3.9–3.12.
- Logout is a public route, next to login.
- A refusal is 403 `forbidden`; the policy runs before any lookup.
- New copy, `[ASSUMPTION]`: «Til Admin-område», «Til innlogging», breadcrumb name «Du er her». «Til Hjem», «Til Lærerhjem», «Du har ikke tilgang til denne siden.», «Fant ikke siden.» are EXPERIENCE.md's own.
- The seed adds each missing demo e-mail instead of only seeding an empty table, and gets two more demo Users.
- The role-comparison "CI check" is a pytest test in the backend CI job, not a separate step.
- Implementation and review fixes were done in the orchestrating context, not in a subagent, as the caller instructed.

**Residual risks:**
- The page gate is in TypeScript (`homes.ts`) beside `authz.POLICIES`; the API stays the enforcement point.
- No migration was added or changed.
