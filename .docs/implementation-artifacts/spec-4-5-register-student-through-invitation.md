---
title: 'Story 4.5: Register as a Student through the Invitation'
type: 'feature'
created: '2026-11-19'
status: 'done'
baseline_revision: '71e6be3e58ee420f9a3ce9feb6507dda80b7b8a5'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-4-context.md'
  - '{project-root}/.docs/planning-artifacts/ux-designs/ux-beergame-2026-11-05/DESIGN.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** Story 4.4 mails Student Invitations, but «Du er invitert» answers every Student link with `invitation_link_invalid`, so nobody can join a Class; Hjem names no Class, `platform/authz` has no Student scope, and the demo Class has no Students.

**Approach:** Extend the Story 3.8 check/accept/accept-login routes and page to take `kind = 'student'`: the check names the Class, the accept creates (or reuses) the User without an account role and, in the same transaction, links the Roster entry and sets it `registered`. A Student scope helper in `authz` and two `classes` read routes give the Student their own Classes; Hjem lists them. The local seed adds 8 registered demo Students.

## Boundaries & Constraints

**Always:**
- One code path per route (`/api/auth/invitation/check|accept|accept-login|renewal`), branching on `kind`; the rate limits of Story 3.8 apply unchanged. Role-Invitation behaviour stays as it is.
- A Student link is usable only when the Invitation is open, the Class resolves, its Roster entry exists with `removed_at IS NULL`, and the address's User (if any) is active; otherwise `invitation_link_invalid`.
- Acceptance (new or existing account) is one transaction: lock the Invitation, (new: create the User with no account role), `UPDATE roster_entries SET user_id, registration='registered' WHERE id=… AND removed_at IS NULL` (0 rows → refuse `invitation_link_invalid`, nothing changes), mark the Invitation accepted, `events.emit(s, "user", id)`. Never a second User for an address.
- Days left for a Student link = max(1, last valid Oslo day − today in Oslo), so a fresh 14-day sending reads «14 dager».
- `authz.classes_enrolled_by(user)`: ids of Classes whose Roster entry has `user_id = user` and `removed_at IS NULL` (table by name, no module import). Policy `classes.read_enrolled` = any logged-in User. `GET /api/classes/enrolled` lists them; `GET /api/classes/enrolled/{id}` returns one or 403 `forbidden` (another Class, removed entry, unknown or malformed id: same answer).
- `identity` imports no `classes` code: the existing class-name resolver becomes a label resolver (name + course code).
- Seed (`APP_ENV=local` only, idempotent, every start): `student@example.com` plus `student2@example.com`…`student8@example.com` («Demo Student N»), password `olspillet-demo`, each a `registered` Roster entry of the demo Class linked to its User. Existing Users are never changed; an existing entry is left as it is.
- Copy in `nb.ts`; errors clear as the user types; the result line replaces the state it answers.

**Never:** bounce/accepted counts (4.6), registration status list or reminders (4.7), manual registration or removing Roster addresses through the UI (4.8), Assistant Invitations (4.9), archive checks (4.10), a Student Class page in the web app, audit rows for Student acceptance, real mail, comparing DB time with host time or ordering by timestamps in tests, resetting or deactivating demo accounts.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Check | open Student link, no User, sent 14 days at NOW | 200 `{kind:"student", role:null, email, valid_days:14, has_account:false, class_name:"class-of-1994", course_code, invited_by:"Bard"}` | – |
| Accept new | name, password ≥ 8 | 200 session; User without roles; entry `registered` + `user_id`; Invitation accepted; `user:<id>` event row | – |
| Accept existing | address has a User (Student of Class A), password right | 200 session as that User; no new User; entry of Class B linked | wrong password 401 `invalid_credentials` |
| Accept new when User exists | – | 409 `account_exists` | page switches to login form |
| Used / expired / voided / removed entry | – | check and accept 410 `invitation_link_invalid` | «Be om ny Invitasjon» → renewal sets `renewal_requested_at` (expired/voided only) |
| Rate limit | > per-link or per-IP attempts | 429 `rate_limited` with Retry-After | – |
| Enrolled list | Student of A | `GET /api/classes/enrolled` → `[A]` | anonymous 401 |
| Other Class | Student of A asks B (or A after removal) | 403 `forbidden`; account and other Classes unchanged | – |

</intent-contract>

## Code Map

- `backend/app/modules/identity/service.py` -- `check_invitation` (535, drop the kind filter, add Student branch), `_usable_invitation` (522), `accept_invitation_new` (585), `accept_invitation_existing` (635), `InvitationChecked` (507), `_days_left` (339), `request_invitation_renewal` (674, already kind-agnostic), class-name registry `register_class_name`/`_class_name` (1589–1606), `last_valid_day` (1616), `OSLO`; add `link_roster_entry`, demo-student helper.
- `backend/app/modules/identity/repo.py` -- add `register_roster_entry(s, entry_id, user_id)` (UPDATE … RETURNING), `roster_entry_by_id`, `ensure_registered_entry` for the seed; `roster_entries` model in `identity/models.py`.
- `backend/app/modules/identity/schemas.py:92` -- `InvitationCheckOut` gains `kind`, nullable `role`, `class_name`, `course_code`, `invited_by`.
- `backend/app/modules/identity/routes.py:180-234` -- check/accept routes map the new fields.
- `backend/app/platform/authz.py` -- `POLICIES`, `_class_staff` pattern (118) for `_roster_entries`, `classes_enrolled_by`.
- `backend/app/modules/classes/{repo,service,routes,schemas,seed}.py` -- `class_name` resolver (repo 92, service 235) → label; enrolled routes declared before `/{class_id}`; seed after `ensure_demo_class`.
- `backend/app/modules/identity/seed.py` -- `DEMO_USERS`, `DEMO_PASSWORD`.
- Tests: `tests/classes/test_roster_send.py` (`klass`, `send`, `staged_id`, `LINK`, 410 assertion at 240 flips), `tests/classes/test_classes.py` (`make`, `as_user`, seed tests), `tests/identity/test_invitations.py`, `tests/platform/test_authz.py`, route-policy test.
- Frontend: `modules/identity/{invitation-page.tsx,invitation.ts,invitation.test.ts,api.ts}`, `app/(app)/hjem/page.tsx`, new `modules/classes/student-home.tsx`, `modules/classes/api.ts`, `copy/nb.ts:239-292`, `lib/api/{openapi.json,schema.ts}`; e2e `invitation.spec.ts` (`expectAccessible`, phone targets), `roster-send.spec.ts` (send + mailbox), `homes.spec.ts` (student Hjem has no main links), `support/auth.ts`.

## Tasks & Acceptance

**Execution:**
- `identity/{schemas,repo,service,routes}.py` -- Student check/accept, roster linking, label resolver, days left, seed helper.
- `platform/authz.py` -- `classes_enrolled_by`, `classes.read_enrolled`.
- `classes/{schemas,repo,service,routes,seed}.py`, `classes/README.md` -- enrolled list/one, label resolver, 8 demo Students.
- `backend/tests/classes/test_student_registration.py` (new) -- every matrix row, one transaction, emit, no duplicate User, scope, removal, seed idempotency and local-only; adjust `test_roster_send.py`, `test_authz.py`.
- `frontend/src/lib/api/{openapi.json,schema.ts}` -- regenerate.
- `frontend/src/modules/identity/*`, `frontend/src/copy/nb.ts` -- Student variant of «Du er invitert»; unit tests.
- `frontend/src/modules/classes/{student-home.tsx,api.ts}`, `app/(app)/hjem/page.tsx` -- Hjem lists the Student's Classes with the Start-date line.
- `frontend/e2e/student-registration.spec.ts` (new) -- one mailed Student Invitation registered by phone at 320/360/1440 with axe and 44 px targets, landing on Hjem naming the Class; existing-account join via API.

**Acceptance Criteria:**
- Given a valid Student link, when opened, then «Du er invitert» shows «Faglærer X har lagt deg til i class-of-1994, IBE160.», name field, the address read-only labelled «E-post, fra Klasselista», password, «Opprett konto og gå videre», and «Invitasjonen er gyldig i 14 dager. Du får Rolle og spill på startdatoen.».
- Given the form submitted validly, then the Student lands on Hjem, which names «class-of-1994, IBE160» with «Du får Rolle og spill på startdatoen.».
- Given an address with an account, then the page asks for its password («Logg inn og bli med i Klassen») and the same account joins the Class.
- Given an expired or used Student link, then the Epic 3 expired state shows and «Be om ny Invitasjon» answers with the result line.
- Given Playwright with axe at 320, 360 and 1440 px, then registration passes with no horizontal scroll, text/email/password input types, and targets ≥ 44 px on phones.
- Given `APP_ENV=local`, then the demo Class has 8 registered Students and `student@example.com`'s Hjem names it.

## Spec Change Log

## Review Triage Log

### 2026-11-19 — Review pass
- verdicts: 36 findings — high 0, medium 5, low 23, false 7, maybe-false 1
- findings:
  - `[low]` `[reject]` (blind) The Student countdown reads «én dag» on the last two days — deliberate: days = last valid Oslo day − today, so a 14-day sending reads «14 dager» the day it is sent, as the Lecturer's «Gyldig i 14 dager»; the last day cannot read 0. Documented in the schema and README.
  - `[low]` `[reject]` (blind) `accept` answers `account_exists` before the Roster check — reachable only when the entry is removed between `check_invitation` (which refuses removed entries) and the lock; the race leaks only what the link holder's own address already has.
  - `[low]` `[patch]` (blind) `_join_class` ignores `register_roster_entry`'s result — now raises, so the transaction rolls back rather than accepting without the link.
  - `[low]` `[reject]` (blind) Archived Classes stay in the Student scope and accept Invitations — `archived_at` is never set before Story 4.10, which adds `is_writable` to every mutating path and decides what archived means for Students.
  - `[low]` `[reject]` (blind) The scope does not test `registration = 'registered'` — `user_id` is set only on registration; 4.8 adds «registered manually», which the scope must include, so a value filter would be wrong then.
  - `[medium]` `[patch]` (blind) Hjem's Classes may come from a cache after accepting — real: the app's `staleTime` is 30 s. `useAcceptInvitation` now invalidates every non-auth query on success.
  - `[low]` `[reject]` (blind) `invitationLead` falls back silently on a missing Class name or role — the api always sends them for the kind; a guard adds branches for an unreachable state.
  - `[low]` `[reject]` (blind) Hjem has no empty state — Hjem had none before; Epic 6 fills it; not asked by the story.
  - `[medium]` `[patch]` (blind) The removal race is tested only for `accept` — grouped with verification-gap row 1; `test_an_address_removed_while_logging_in_leaves_nothing_behind` added.
  - `[low]` `[reject]` (blind) `DEMO_PASSWORD` is duplicated in `classes/seed.py` — `identity.seed` is not importable by other modules (only `identity.service`), and `identity.service` cannot import its own seed; the docstring names the source.
  - `[low]` `[reject]` (blind) The seed reuses a deactivated or differently named demo User — local seed only; existing Users are deliberately never changed.
  - `[low]` `[reject]` (blind) The seed hashes up to seven passwords under the advisory lock — once, on a fresh local database.
  - `[low]` `[reject]` (blind) Migration 0027 uses a plain `CREATE INDEX` — the table is small in v1 and every migration here runs before the api starts.
  - `[medium]` `[patch]` (blind) The new test file was double-encoded (mojibake) — re-saved as clean UTF-8.
  - `[low]` `[patch]` (blind) Missing newline at end of `invitation.test.ts`; over-long comment in `home-page.tsx` — fixed.
  - `[false]` `[reject]` (blind) The e2e Class name can collide — each test makes a fresh Lecturer, and the name now uses the full run tag.
  - `[low]` `[patch]` (blind) `InvitationCheckOut.course_code` has no docstring — added.
  - `[false]` `[reject]` (edge) The countdown repeats 1 — as the first blind row.
  - `[low]` `[reject]` (edge) A Lecturer or Admin who joins as a Student cannot open Hjem — real, but staff joining their own Classes as Students is not an everyday case in v1, and the fix changes the homes' access rules (`homes.ts`, `canView`); Epic 6 owns the Student's game view.
  - `[low]` `[reject]` (edge) The seed leaves an already invited, unlinked demo address unlinked — only if someone invites a demo address by hand locally.
  - `[low]` `[reject]` (edge) Archived Classes stay listed on Hjem — as the blind archive row (Story 4.10).
  - `[low]` `[reject]` (edge) A Student can register into an archived Class — as the blind archive row (Story 4.10).
  - `[low]` `[reject]` (edge) The seed links a deactivated demo User — as the blind seed row.
  - `[low]` `[patch]` (edge, claim) No authz unit test for the Student scope — `test_any_user_may_ask_for_their_enrolled_classes_held_to_the_student_scope` added to `tests/platform/test_authz.py`.
  - `[medium]` `[patch]` (edge, claim) The e2e has no existing-account join — the e2e now has a second Class invite the 1440 px Student, who logs in on «Du er invitert» («Logg inn og bli med i Klassen», axe) and lands on Hjem naming both Classes.
  - `[medium]` `[patch]` (verification-gap) The in-transaction Roster recheck of `accept-login` is never exercised — test added: 410, no `accepted_at`, entry stays `invited`.
  - `[low]` `[patch]` (verification-gap) The existing-account Student branch of the page is never rendered — grouped with the edge e2e claim; patched there.
  - `[low]` `[patch]` (verification-gap, other) `_join_class` ignores its result — as the blind row.
  - `[low]` `[patch]` (verification-gap, other) A 30 s cache can hide the new Class after `accept-login` — as the blind Hjem-cache row.
  - `[false]` `[reject]` (intent) «The address of another Class» has no app surface — the app's Class address `/klasser/{id}` gives the permission-denied state to a Student; the e2e now checks it, and the api scope is tested.
  - `[false]` `[reject]` (intent) «When they open the Class» is api-only — a removed Class leaves Hjem's list (`GET /api/classes/enrolled`, tested) and the Class address is denied as above; there is no Student Class page until Epic 6.
  - `[medium]` `[patch]` (intent) The renewal confirmation tells a Student that Admin sees the request — the line now reads «… ser den som sendte den nå at du ber om en ny …», the same for every link (it may not reveal the kind). The Lecturer's view of the request is Story 4.7's status list.
  - `[false]` `[reject]` (intent) The existing-account variant is never rendered under Playwright — patched with the edge claim row.
  - `[low]` `[reject]` (intent) A staff account joining lands on its own home — as decided in Design Notes; see the edge staff row.
  - `[false]` `[reject]` (intent) «Numeric keyboard» is not exercised — no field asks for one; the e2e checks the types the fields have.
  - `[maybe-false]` `[reject]` (intent) The expired state runs axe only at 1440 px and not in the Student flow — the same Story 3.8 component, covered by axe at 320, 360 and 1440 in `invitation.spec.ts`; would only be low.
## Design Notes

- Copy [ASSUMPTION] except where marked: lead `Faglærer ${inviter} har lagt deg til i ${label}.` (mockup 04), fallback `Du er lagt til i ${label}.` when the inviter is gone; validity line = existing `validity(days)` + « Du får Rolle og spill på startdatoen.» (EXPERIENCE.md draft); existing-account lead `Adressen har allerede en konto. Logg inn, så blir du med i ${label}.`, submit «Logg inn og bli med i Klassen», failed «Du ble ikke med i Klassen. Prøv igjen.».
- Hjem keeps no links (homes.spec): each Class an `h2`-level text row on a hairline list, the line beneath. No Class: nothing beyond the heading (Epic 6 fills Hjem).
- A Lecturer who accepts a Student link lands on the Lærerhjem, as `homeOf` decides.

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/classes tests/identity/test_invitations.py tests/platform/test_authz.py -q` -- pass.
- `cd backend && uv run pytest -q && uv run ruff check . && uv run ruff format --check .` -- pass.
- `cd frontend && npm run typecheck && npm test && npm run check:copy && npm run lint:colours && npm run build` -- pass.
- `cd frontend && npx playwright test` against the rebuilt compose stack with `worker-batch` -- pass.

## Auto Run Result

Status: done

**Summary.** A Student Invitation now works. «Du er invitert» (`/invitasjon`) names the Class and its Lecturer («Faglærer X har lagt deg til i class-of-1994, IBE160.»), locks the address («E-post, fra Klasselista») and reads «Invitasjonen er gyldig i 14 dager. Du får Rolle og spill på startdatoen.» with the real days left. The Story 3.8 routes (`check`, `accept`, `accept-login`, `renewal`, same rate limits) branch on `kind`: accepting creates the User without an account role, or proves an existing account by its password (never a second User), and in one transaction locks and links the Roster entry, sets it `registered`, marks the Invitation accepted and emits `user:<id>`. A removed entry refuses the link and writes nothing. `authz.classes_enrolled_by` is the Student scope; `GET /api/classes/enrolled` and `/enrolled/{id}` (403 for any other Class) read through it. Hjem names each Class with the Start-date line. The local seed adds 8 registered demo Students (`student@example.com`, `student2…8@example.com`).

**Process note.** The caller required the implementation in this context. The four review layers ran as sub-agents; their reports were read from their transcripts.

**Files changed**
- `backend/app/modules/identity/{service,repo,schemas,routes,models}.py`: Student check/accept, Roster linking, class-label resolver, days left, seed helper.
- `backend/app/platform/authz.py`: `classes_enrolled_by`, `classes.read_enrolled`.
- `backend/app/modules/classes/{repo,service,routes,schemas,seed}.py`, `classes/README.md`: enrolled routes, label resolver, demo Students, decisions.
- `backend/migrations/versions/0027_roster_entries_user_index.py`: index on `roster_entries.user_id`.
- Tests: `tests/classes/test_student_registration.py` (new, 15 tests), `test_roster_send.py`, `identity/test_invitation_accept.py`, `platform/test_authz.py`, `test_migrations.py`.
- Frontend: `modules/identity/{invitation-page.tsx,invitation.ts,invitation.test.ts,api.ts,home-page.tsx}`, `modules/classes/{student-home.tsx,api.ts}`, `app/(app)/hjem/page.tsx`, `copy/nb.ts`, `lib/api/{openapi.json,schema.ts}`, `e2e/student-registration.spec.ts` (new).

**Review findings.** 36: 5 medium, 23 low, 7 false, 1 maybe-false. Patched: 5 medium and 8 low (some grouped). Deferred: none. Rejected: 15 low, 7 false and 1 maybe-false, each with its reason in the Review Triage Log.

**Follow-up review recommended: true.** Five medium entries were patched. Named unverified risk: the query invalidation after accepting (Hjem's Classes after `accept-login` in a tab with a fresh cache) has no test of its own.

**Verification**
- Backend: ruff clean; full pytest 2113 passed, 4 skipped (73 s).
- Frontend: typecheck, `npm test` (351), `check:copy`, `lint:colours` and build pass; Playwright 146 passed against the rebuilt stack with `worker-batch`, including the one mailed Student registration at 320, 360 and 1440 px with axe and 44 px targets.
- No new test takes over 1 s (slowest new 0.95 s setup, 0.80 s call).
- Shared test databases: revision 0027 added and migrated; not changed after it ran.
- Layout checked on screenshots at 390 and 1280 px («Du er invitert» for a Student, Hjem) against mockup 04.

**Decisions taken in place of the founder**
- The Student page names the inviting Lecturer as mockup 04 does; without that User it reads «Du er lagt til i …».
- Days left for a Student link count to the last valid day in Europe/Oslo (at least 1), so a 14-day sending reads «14 dager» the day it is sent.
- A Student is no account role: the new User has no role; a Lecturer or Admin who joins keeps their roles and lands on their own home.
- An existing account joins by its password on «Du er invitert» («Logg inn og bli med i Klassen»); a session alone does not join.
- Student acceptance writes no audit row (the epic audits staff changes and archive only).
- The renewal line is now the same for both kinds: «Hvis lenken kom fra en Invitasjon, ser den som sendte den nå at du ber om en ny. Den kommer på e-post.»
- Student Class reads live under `/api/classes/enrolled`; there is no Student Class page until Epic 6. Hjem lists Classes as text, not links.
- Demo Students: `student@example.com` (the existing demo Student) plus `student2…8@example.com`, «Demo Student N», password `olspillet-demo`, seeded on every local start.
- Index `ix_roster_entries_user_id` (migration 0027) for the Student scope.
- All new copy is [ASSUMPTION] except «Du er invitert», «Navn», «Velg passord», «Opprett konto og gå videre» and the validity sentence.

**Residual risks**
- Archived Classes (Story 4.10) stay in the Student scope and still accept Invitations until 4.10 decides.
- A Lecturer or Admin who is also a Student cannot open Hjem, so never sees their Student Classes.
- The Lecturer sees renewal requests only from Story 4.7.