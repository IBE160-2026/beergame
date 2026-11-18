---
title: 'Story 3.13: Read the Landing page and ask for lecturer access'
type: 'feature'
created: '2026-11-18'
status: 'done'
baseline_revision: '0bebca28b27ce7477d4b5368be1cc50a096bebb5'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-3-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-3-12-read-audit-log.md'
warnings: [oversized]
deferred:
  - summary: >-
      Requests for lecturer access keep the name, e-mail and Institution of people without accounts with no retention rule.
    evidence: |-
      access_requests rows (invited and dismissed) are never deleted or anonymised. Settle by checking whether the data-retention stories (13.9, Epic 15) cover identity's access_requests; if not, add a retention rule.
    location: >-
      backend/migrations/versions/0022_access_requests.py
    severity: medium (unverified)
---

<intent-contract>

## Intent

**Problem:** `/` shows an empty page to a visitor (Story 3.3 placeholder). There is no public face of «ØL-spillet» and no way for a Lecturer to reach the Admin without an open sign-up (FR-1, FR-3, UX-DR61).

**Approach:** `/` renders a static Landing (headline, lead, «Be om lærertilgang», «Logg inn», one Demodata Seat as an HTML week table); a logged-in User is sent on to their home. «Be om lærertilgang» leads to `/laerertilgang`, a short public form stored as an `access_requests` row in `identity` (new migration 0022), rate-limited per IP. «Brukere og roller» lists the open requests; «Inviter» prefills the existing invite form (Faglærer) and sending it closes the request, «Avvis» dismisses it; each writes one audit row.

## Boundaries & Constraints

**Always:**
- Landing copy (all in `nb.landing`, drafts [ASSUMPTION] except the story's own strings): product name «ØL-spillet» in the header; h1 «Hver uke har en strek og et tall. Studentene ser begge.» in `text-display` (phone: `text-title-phone`); lead in `body-lead`; primary «Be om lærertilgang» → `/laerertilgang`, secondary «Logg inn» → `/logg-inn` (Next links styled as Knapper via an exported `buttonClassName`). Laptop: headline left, lead + buttons right, Seat block below; phone: one column in the order headline, lead, buttons, Seat table.
- Seat block: caption «Ett sete, Grossist, Uke 4. Veiledet uke.»; table rows Ordre inn, Levering, Netto lager, På vei, Din ordre over columns Uke 1–4 (row and column `th` with scope), `tabular-nums lining-nums`; under it «Studenten ser bare sine egne tall.» and «Demodata» in `text-caption text-ink-muted`; then «Lagerkurvene for hele klassen ser du først når du er logget inn.» Numbers come from `frontend/src/modules/landing/demo-seat.ts` (the synthetic fixture, reused by Story 6.8): one Seat, Grossist, Veiledet uker 1–4, Ordre inn 4 every week, Levering 4, Netto lager 12, På vei 12, Din ordre 4. No chart code.
- `/` is static: the Landing renders without waiting for `/api/auth/me`; a client effect replaces the URL with the User's home when `me` returns a User.
- Copy check: `check-copy.mjs` gets landing rules applied only to strings in section `landing`: no customers (`kunde`), prices (`pris`, `kr`, `kroner`, `gratis`), amplification (`forsterk`), quotes (`«`, `»`, `“`, `”`, `"`), learning claims (`lærer seg`, `læring`, `forstå`), week counts (`uker spilt`, a number followed by `uker`). Unit tests cover the new rules. A Vitest test on the fixture: one Seat, weeks 1–4 only, Ordre inn never rises.
- `/laerertilgang` (in `(auth)`): h1 «Be om lærertilgang», lead, fields Navn, E-post, Institusjon (free text), primary «Send forespørsel». Client checks: name 1–200 chars after trim/collapse; e-mail by `validateEmail`; Institusjon by the Institution name rule (`institutions.ts`: not empty, ≤ 200, no `@`/control char). On 202 the form is replaced by «Forespørselen er sendt. Admin svarer deg på e-post.» (focused, `role="status"`) and a Lenke «Til forsiden». 429 → «For mange forespørsler. Prøv igjen om en time.»; other failure → «Forespørselen ble ikke sendt. Prøv igjen.» (inline `role="alert"`, input kept).
- `POST /api/auth/access-request` (public, on `PUBLIC_ROUTES`) body `{name, email, institution}` → `202` empty, the same whether or not the address has an account. 422 `fields.name = name_empty|name_too_long`, `fields.email = invalid_email`, `fields.institution = name_empty|name_too_long|name_invalid`. Counts per IP first (`platform/ratelimit`, bucket `access_request_ip`, settings `access_request_rate_limit_per_ip`=20, `access_request_rate_limit_window_minutes`=60); over the limit → 429 `rate_limited` with `Retry-After`, nothing stored. One open request per address (lower-case): a repeat updates name, institution and `requested_at`. Never creates a User or an Invitation.
- `access_requests` (owned by `identity`): `id`, `name`, `email`, `institution`, `requested_at`, `status` (`open|invited|dismissed`, check), `closed_at`, `closed_by` (FK users), `invitation_id` (FK invitations); partial unique index on `email` where `status='open'`.
- `GET /api/admin/access-requests?cursor=&limit=` (policy `users.manage`) → list envelope of open requests `{id, name, email, institution, requested_at}` newest first, keyset cursor as the Institution list. `POST /api/admin/access-requests/{id}/dismiss` (`users.manage`) → 204; not open or unknown → 404 `not_found`; writes audit `access_request.dismissed` (targets `access_request_id`, change `{}`).
- `InvitationIn` gains optional `access_request_id`. When it names an open request: in the same transaction the request becomes `invited` with `invitation_id`, and the single audit row has action `access_request.invited`, targets `invitation_id` + `access_request_id`, change `{role}` (instead of `invitation.sent`). When it names no open request the Invitation is sent as before (`invitation.sent`).
- Audit labels: `identity.service.access_request_labels` (requester's name) registered for `access_request_id`; `nb.admin.audit` gets the two actions and the target «Forespørsel fra {name}».
- «Brukere og roller»: section «Forespørsler om lærertilgang» between «Inviter» and «Brukere»; table Navn / E-post / Institusjon / Mottatt («18. nov. 2026», `formatDate`) / Endre, reflowing into labelled blocks below 60em (`Cell`). Per row: «Inviter {name} som Faglærer» fills the invite form (address, role Faglærer), shows «Fyller inn fra forespørselen til {name}.» above the field, scrolls to and focuses the e-mail field; «Avvis forespørselen fra {name}» dismisses at once (no dialog) with a status line «Forespørselen fra {name} er avvist.» Empty: «Ingen åpne forespørsler.» A sent Invitation from a request re-reads the request list.
- Playwright + axe at 320, 360, 1440 px and 400 % zoom (320 × 256) on `/` and `/laerertilgang`, no page-level horizontal scroll.

**Never:** no chart code or second Demodata figure (Epics 6–7); no account or Invitation created by a request; no mail sent to the requester or the Admin by this story; names or e-mails in audit rows or logs; DB-clock vs host-clock comparisons in tests; edits to `sprint-status.yaml`, `.env`, `.claude/settings*.json`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Request | `{Ola, OLA@usn.no, USN}` | 202; row `open`, email `ola@usn.no`; no users/invitations row; no audit row | — |
| Repeat | same address again, new institution | still one open row, updated | — |
| Bad input | empty name / `x@` / institution with `@` | 422 with the field code; nothing stored | — |
| Rate limit | 21st request from one IP in the window | 429 `rate_limited`, `Retry-After`; nothing stored | — |
| List | 3 open, 1 dismissed, limit 2 | newest two + cursor; then the third | bad cursor → 422 |
| Invite from request | `access_request_id` of an open request | 201; request `invited`; one audit row `access_request.invited` | — |
| Stale request | id already dismissed / unknown | 201; plain `invitation.sent` | — |
| Dismiss | open id | 204; `dismissed`; one audit row | closed/unknown → 404 |
| Not Admin | Lecturer / no session on admin routes | 403 / 401 | — |
| Landing, logged in | Admin opens `/` | lands on `/admin` | — |

</intent-contract>

## Code Map

- `frontend/src/app/page.tsx`, `frontend/src/modules/identity/go-home.tsx` -- `/` today renders `GoHome` (client, empty for visitors); becomes Landing + redirect-only `GoHome`.
- `frontend/src/components/{button.tsx,app-header.tsx,link.tsx,text-field.tsx,action-error.tsx}` -- Knapper styles (`base`, `variants`), header, Lenke, Tekstfelt.
- `frontend/src/app/(auth)/glemt-passord/page.tsx`, `frontend/src/modules/identity/forgot-form.tsx` -- public form page pattern (closest analogue for `/laerertilgang`).
- `frontend/src/modules/identity/validate-login.ts` (`validateEmail`), `frontend/src/modules/admin/institutions.ts` (`cleanName`, `nameError`) -- client checks to reuse.
- `frontend/src/modules/admin/{users-page.tsx,invite-form.tsx,api.ts,institution-list.tsx,user-list.tsx (Cell, RowMessage, RowLine),invitations.ts (formatDate)}` -- page, form, list patterns.
- `frontend/src/copy/nb.ts` -- `terms` (row labels), `admin.audit.actions/targets`, new `landing`, `accessRequest`, `admin.users.requests`.
- `frontend/scripts/{check-copy.mjs,scripts.test.mjs}` -- copy rules by section (`topLevelSection`).
- `frontend/e2e/{homes.spec.ts,admin-invite.spec.ts,logg-inn.spec.ts (400 % zoom viewport)}`, `e2e/support/auth.ts`.
- `backend/app/modules/identity/{models.py,repo.py,service.py,routes.py,schemas.py}` -- `_issue_invitation` (service L342) takes action + change, targets fixed to `invitation_id`; `request_password_reset` (L200) is the public rate-limited pattern; `institution_page` / `_encode_cursor` the keyset list; `labels_of` (repo) the label read; `institution_name`, `email_is_valid`, `AcceptInvitationIn._name` the validators.
- `backend/app/platform/{ratelimit.py,config.py (L59-77 limits),authz.py,audit.py}`; `backend/app/main.py` -- `register_labels` calls.
- `backend/migrations/versions/0021_institutions.py` -- migration pattern; new `0022_access_requests.py`.
- `backend/tests/{test_authz_rules.py (PUBLIC_ROUTES),test_migrations.py (HEAD, table sets),conftest.py (IDENTITY_TABLES)}`, `tests/identity/test_institutions.py` (fixtures `clock`, `admin`, helpers).
- Regenerate client: `cd backend && uv run python -m app.openapi ../frontend/src/lib/api/openapi.json`, then `cd frontend && npm run api:generate`.

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0022_access_requests.py` (new); `backend/app/modules/identity/models.py` -- table + indexes.
- `backend/app/platform/config.py` (+ `.env.example` if it lists rate limits) -- two settings.
- `backend/app/modules/identity/{schemas,repo,service,routes}.py` -- request/list/dismiss, invite-from-request, label reader.
- `backend/app/main.py` -- register `access_request_id` labeler.
- `backend/tests/identity/test_access_requests.py` (new) -- every matrix row; `tests/test_authz_rules.py`, `tests/test_migrations.py`, `tests/conftest.py` -- public route, head 0022, truncate.
- `frontend/src/copy/nb.ts`; `frontend/src/components/button.tsx` (`buttonClassName`); `frontend/src/modules/landing/{demo-seat.ts,demo-seat.test.ts,landing-page.tsx,seat-table.tsx}` (new); `frontend/src/modules/identity/go-home.tsx`; `frontend/src/app/page.tsx`.
- `frontend/src/modules/access-request/{validate.ts,validate.test.ts,request-form.tsx}` (new), `frontend/src/app/(auth)/laerertilgang/page.tsx` (new).
- `frontend/src/modules/admin/{api.ts,access-request-list.tsx (new),invite-form.tsx,users-page.tsx}`; regenerated `lib/api/{openapi.json,schema.ts}`.
- `frontend/scripts/{check-copy.mjs,scripts.test.mjs}` -- landing rules.
- `frontend/e2e/landing.spec.ts` (new): content, order at 320 px, axe at four sizes on both pages, form validation and submit; `frontend/e2e/admin-access-requests.spec.ts` (new): request appears, «Inviter» prefills and sends, row leaves, «Avvis» removes, audit page shows both actions; `homes.spec.ts` unchanged behaviour.

**Acceptance Criteria:**
- Given a visitor at `/`, then the Landing shows the name, headline, lead, both buttons, the Demodata table and the Lagerkurvene line; at 320 px they stack headline, lead, buttons, table.
- Given a logged-in User at `/`, then they land on their own home.
- Given the copy check, when a landing string holds a price, customer, quote, learning claim, week count or «Beer Game»/«bullwhip»/«øl», then it fails.
- Given a submitted request, then the Admin sees it in «Brukere og roller» and can invite (prefilled Faglærer) or dismiss it, each leaving one audit row shown in «Revisjonslogg».
- Given the full suites, then everything passes and no new test takes over 1 s.

## Spec Change Log

## Review Triage Log

### 2026-11-18 — Review pass
- verdicts: 45 findings — high 0, medium 6, low 35, false 3, maybe-false 1
- note: the four reviewers ran as background subagents (the run's brief); their final reports were read from their transcripts once each had ended its turn. The diff excluded the regenerated `lib/api/{openapi.json,schema.ts}`.
- findings:
  - Blind Hunter:
    - `[medium]` `patch` A request closed as invited whatever address or role the Invitation went to. `send_invitation` now links the request only for a Lecturer Invitation to the request's own address (`ACCESS_REQUEST_ROLE`); otherwise it sends a plain `invitation.sent` and the request stays open. New test `test_an_invitation_to_another_address_or_role_leaves_the_request_open`.
    - `[low]` `patch` (same root) The prefill could not be dropped. `InviteForm` clears the link when the address is changed away from the request's or the role is switched to Admin.
    - `[low]` `reject` A visitor can overwrite another address's open request. Costs the per-IP budget, changes only what the Admin reads before inviting the address itself; a per-address limit adds a second bucket for an unlikely abuse.
    - `[maybe-false]` `defer` No retention for requests of people without accounts. Real if no later data-retention story covers `access_requests`; settle by checking the deletion stories (13.9, Epic 15) — medium if not covered.
    - `[low]` `reject` No undo of a dismissal. The epic asks for buttons that act at once with no dialog; the requester can ask again (a new row opens, tested).
    - `[low]` `patch` A 404 dismissal (already answered) said «Prøv igjen». Now «Forespørselen fra … er allerede besvart.» as a status line.
    - `[low]` `reject` The form ignores server field codes. The client runs the same checks; only format characters such as U+200B differ, and the generic line then shows (same as the Institution form).
    - `[low]` `reject` A name with control characters reads «Skriv navnet ditt.». Same rule as the Invitation name (Story 3.8); rare.
    - `[low]` `patch` Column header «Svar» differed from the spec's «Endre». Now «Endre», as the other Admin lists.
    - `[low]` `reject` The Landing rules cover only `nb.landing` and miss spelled-out forms. The other strings on `/` are glossary terms and the product name, already under the general rules; a fuller lexicon is guesswork.
    - `[low]` `patch` Caption and fixture could drift. `demo-seat.test.ts` now checks the caption names the fixture's Role and current week.
    - `[low]` `patch` The headline switched to `display` at `md` while the grid splits at `lg`. Now `lg:text-display`.
    - `[low]` `reject` No DB constraint ties closing fields to status. Single writer under a row lock; a constraint adds migration surface for no observed fault.
    - `[low]` `reject` Keyset on `requested_at`, which a repeat changes. Needs more than 50 open requests and a repeat between two page loads.
    - `[low]` `reject` The Admin is not told the address already has an account. An Invitation to an existing account adds the role (Story 3.8), so nothing breaks.
    - `[low]` `patch` Missing tests. Added the mismatched address/role test and the re-file-after-close test; limit bounds, invite/dismiss races and component tests rejected (declared FastAPI bounds; row lock; e2e covers the UI).
    - `[false]` `reject` `.env.example` not updated. It lists no rate-limit settings (grep), so there is nothing to add; `docker-compose.yml` was updated as for the other limits.
    - `[low]` `reject` e2e hard-codes the base URL, a colour and 48 px. The colour and size are what the AC asks to observe; the base URL matches the config default.
    - `[low]` `patch` No way back from `/laerertilgang` before sending. Added «Til forsiden» under the form. (`/` takes the root layout's title «ØL-spillet».)
  - Edge Case Hunter:
    - `[medium]` `patch` Edited address still closes the request (same entry as the first Blind Hunter row).
    - `[medium]` `patch` Role switched to Admin still closes the request (same entry).
    - `[low]` `reject` Keyset on a mutable `requested_at` (same as Blind Hunter).
    - `[low]` `reject` Over-long fields answer `string_too_long`. Same `max_length` guard pattern as `AcceptInvitationIn` and `InstitutionIn`; needs over 800 characters.
    - `[low]` `reject` U+200B passes the client (same as Blind Hunter).
    - `[low]` `patch` Stale `from` after a retyped address (same entry as the first row).
    - `[low]` `patch` 404 dismissal says «Prøv igjen» (same entry as Blind Hunter).
    - `[low]` `reject` An expired cookie on `/` goes to «Logg inn». Story 3.4's rule for every page; the User then lands on their home.
    - `[low]` `reject` e2e cleanup reads only 100 open requests. Every test answers its own request.
    - `[low]` `patch` The invited audit row was not checked on «Revisjonslogg». The 1440 px invite test now asserts the row with «Invitert fra forespørsel», «Invitasjon til …» and «Forespørsel fra …».
    - `[low]` `patch` Column header (same entry as Blind Hunter).
    - `[medium]` `patch` Claim: closes for any address and role (same entry as the first row).
  - Intent Alignment (divergences):
    - `[low]` `reject` The copy rules cover the copy section, not the rendered page (same as Blind Hunter).
    - `[false]` `reject` Buttons are links. They navigate, so they are Next links in the Knapper look (Design Notes); the story's button roles are visual.
    - `[low]` `reject` The confirmation shows on `/laerertilgang`, the page the button leads to; the Landing stays static.
    - `[low]` `reject` A logged-in User sees the Landing until `/me` answers, and `system-states.spec.ts` now expects the Landing at `/` when `/me` fails. Recorded as a decision: the public page never waits on the session.
    - `[medium]` `patch` Inviting from a request may close it for another address (same entry as the first row).
    - `[low]` `reject` The Ordre-inn rule is a Vitest test on the fixture, not the copy script; both run in CI and a copy check cannot read numbers.
    - `[low]` `reject` The rate limit is not exercised end to end. The api test lowers the limit; the local stack raises it as for the other limits.
    - `[false]` `reject` Extra surfaces. Each serves the story (button look, redirect, local limit, audit label, paging, axe run).
  - Verification Gap:
    - `[low]` `patch` 429 and failure lines of the form untested. New e2e test routes the endpoint to 429 and 500 and checks the line and kept input.
    - `[low]` `patch` The invited audit row not checked end to end (same entry as Edge Case Hunter).
    - `[low]` `patch` No re-file after a close. Added `test_a_new_request_after_a_closed_one_opens_a_new_row`.
    - `[low]` `reject` «Vis flere forespørsler» and the dismiss-failure line untested. Same untested pattern as the other Admin lists; needs over 50 open requests.
    - `[medium]` `patch` Request closed for another address (same entry as the first row).
    - `[low]` `patch` The sent line lacked `role="status"`. Added.

## Design Notes

- **Separate request page:** `/laerertilgang` keeps the Landing static and gives the form its own axe run; the Landing's two "buttons" navigate, so they are links styled as Knapper.
- **One audit row per Admin action:** inviting from a request is one action, recorded as `access_request.invited` with both targets, not as `invitation.sent` plus a second row.
- **Repeat requests** update the open row, so the Admin sees one row per address.

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/identity/test_access_requests.py tests/test_authz_rules.py tests/test_migrations.py` -- expected: pass
- `cd backend && uv run pytest --durations=15 && uv run ruff check . && uv run ruff format --check .` -- expected: pass
- `cd frontend && npm run typecheck && npm test && npm run check:copy && npm run lint:colours && npm run build` -- expected: pass
- `docker compose up -d --build --wait proxy worker-batch && cd frontend && npx playwright test` -- expected: pass

## Auto Run Result

Status: done

**Summary.** `/` is now the Landing: «ØL-spillet» in the header, the headline in `display`, the lead, «Be om lærertilgang» (primary) and «Logg inn» (secondary), and one Demodata Seat (Grossist, Veiledede uker 1–4) as an HTML week table with tabular lining figures, «Demodata» in `caption` `ink-muted` and «Lagerkurvene for hele klassen ser du først når du er logget inn.». No chart code. It renders statically; a logged-in User is sent on to their home. «Be om lærertilgang» leads to `/laerertilgang` (Navn, E-post, Institusjon), stored as an `access_requests` row in `identity` (migration 0022), rate-limited per IP (20 per hour, configurable); a repeat from the same address updates the open row; no User or Invitation is created. «Brukere og roller» lists open requests; «Inviter … som Faglærer» prefills the invite form, and sending it (Faglærer, same address) closes the request with one `access_request.invited` audit row; «Avvis» dismisses with one `access_request.dismissed` row. The copy check holds `nb.landing` to the Landing rules (no customers, prices, amplification, quotes, learning claims, week counts); a Vitest test holds the fixture to one Seat, weeks 1–4, and an Ordre inn that never rises.

**Implementation note.** The run's brief said to implement in this context, not through a step-03 subagent; only the review used subagents.

**Files changed:** backend migration `0022_access_requests.py` (new); `identity/{models,repo,schemas,service,routes}.py` (table, request/list/dismiss, invite-from-request, label reader); `main.py` (label registration); `platform/config.py` (two settings); tests `identity/test_access_requests.py` (new), `test_authz_rules.py` (public route), `test_migrations.py` (head 0022), `conftest.py` (truncate). `docker-compose.yml` (local limit raised, as for the other limits). Frontend `copy/nb.ts`; `components/button.tsx` (`buttonClassName`); `modules/landing/{demo-seat.ts,demo-seat.test.ts,seat-table.tsx,landing-page.tsx}` (new); `modules/identity/go-home.tsx` (redirect only); `app/page.tsx`; `modules/access-request/{validate.ts,validate.test.ts,request-form.tsx}` and `app/(auth)/laerertilgang/page.tsx` (new); `modules/admin/{api.ts,access-request-list.tsx (new),invite-form.tsx,users-page.tsx}`; regenerated `lib/api/{openapi.json,schema.ts}`; `scripts/{check-copy.mjs,scripts.test.mjs}`; e2e `landing.spec.ts`, `admin-access-requests.spec.ts` (new), `system-states.spec.ts` (`/` now shows the Landing when `/me` fails).

**Review.** 45 findings: 0 high, 6 medium, 35 low, 3 false, 1 maybe-false. Patched: one medium entry (a request closed by an Invitation to another address or role; now linked only for a Faglærer Invitation to its own address, and the form drops the link when the address or role changes) and low entries (already-answered dismissal line, «Endre» header, caption/fixture test, `lg` headline breakpoint, «Til forsiden» link, `role="status"` on the sent line, e2e for 429/500 and the invited audit row, api tests for mismatch and re-filing). Deferred: retention of request data (unverified medium). Every rejection has its reason in the triage log.

**Follow-up review recommended: false.** Patched: 0 high, 1 medium entry, 11 low entries.

**Verification:**
- Backend `pytest` 1881 passed in 71 s; ruff check and format clean. Slowest new test 0.65 s (setup); none over 1 s.
- Frontend: typecheck, Vitest 319, check:copy, lint:colours and build pass.
- Playwright on the rebuilt compose stack: 116/118 on the full run; the two failures were the known `system-states.spec.ts` 1440 px tests under full-suite load, which passed 18/18 when rerun alone. `landing.spec.ts` and `admin-access-requests.spec.ts` 14/14.
- Migration 0022 is new; it was applied to the shared test databases by the test session and has not been changed since.

**Decisions taken in place of the founder:**
- The request form is its own page, `/laerertilgang`; the Landing's two buttons are links in the Knapper look.
- Institution is free text (a visitor's Institution may not exist yet); same name rule as Institutions.
- One open request per address; a repeat updates it. Rate limit 20 per IP per hour (placeholder `ACCESS_REQUEST_RATE_LIMIT_PER_IP`); no limit per address.
- Inviting from a request writes one audit row `access_request.invited` (both ids) instead of `invitation.sent`; it closes the request only for a Faglærer Invitation to the request's own address. Dismiss is immediate, no undo.
- `/` renders the Landing without waiting for the session, so a logged-in User sees it briefly before the redirect, and `/` shows the Landing (not the page error) when `/me` fails.
- Demodata Seat values from the mockup (Ordre inn 4, Levering 4, Netto lager 12, På vei 12, Din ordre 4, weeks 1–4); no «Kost per uke» row (costs are Story 6.16's panel); no future columns.
- [ASSUMPTION] copy: the lead (mockup lead with «ØL-spillet» as subject), «Studenten ser bare sine egne tall.», «Din ordre», all of `nb.accessRequest`, `nb.admin.users.requests`, `invite.fromRequest`, the two audit action names and «Forespørsel fra …».

**Residual risks:**
- Request data is kept with no retention rule (deferred).
- The `system-states.spec.ts` flake under full-suite load remains.
- Keyset paging of requests can repeat or skip a row if a request is re-filed between page loads (over 50 open).
