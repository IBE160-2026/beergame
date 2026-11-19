---
title: 'Story 4.4: Send Invitations to the Roster with a validity period'
type: 'feature'
created: '2026-11-19'
status: 'done'
baseline_revision: '5a0e1bbe1e66cb7c1be2c5447495297914676a84'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-4-context.md'
  - '{project-root}/.docs/planning-artifacts/ux-designs/ux-beergame-2026-11-05/DESIGN.md'
warnings: ['oversized']
deferred:
  - summary: >-
      The page's recovery after a refused send (404 not_found or 422 nothing_to_send: message plus staging refetch) has no Playwright test.
    evidence: |-
      `sendGone`/`nothingToSend` appear only in nb.ts and the messages map of roster-upload.tsx; roster-send.spec.ts covers the happy path and the client-side 61-day refusal. The api side is pinned by test_a_replaced_staging_is_not_sent and test_a_staging_with_no_valid_row_is_refused_and_kept. A route-intercept Playwright case would settle it.
    location: >-
      frontend/src/modules/classes/roster-upload.tsx (onSend onError, send ActionError)
    severity: medium
---

<intent-contract>

## Intent

**Problem:** After Story 4.3 the Lecturer sees «Send N Invitasjoner», but pressing it does nothing: there is no Roster, no Student Invitation and no mail. Three copy defects from 4.3's visual check remain (Issue #86): the column reason and the invalid-row heading count differently, the invalid-row list header says «E-post i fila» whatever the column, and the invalid-row note shows after an empty paste.

**Approach:** One command in `classes.service` opens one transaction and, through `identity.service`, writes the staged valid addresses to a new `roster_entries` table, deletes the staging and creates one Student Invitation per new entry, each enqueued as the `immediate` notice `invitation` addressed by reference. The send form has a validity in whole days, prefilled 14, range 1–60. The mail names the Class and the last valid day. Staged rows already on the Roster are listed as invalid with their own reason. The Lærerhjem and the Class page show the Roster count.

## Boundaries & Constraints

**Always:**
- `roster_entries` (identity-owned): `id`, `class_id` (FK `classes` by name, cascade), `email` (normalised CHECK), `user_id` (nullable FK `users`, SET NULL), `registration` (`invited` | `registered`, CHECK), `added_at`, `removed_at`; unique `(class_id, email)`.
- `invitations` extended expand-only (migration 0026): `kind` (`role` | `student`, default `role`), `role` nullable with CHECK that `role` is set exactly for `kind = 'role'`, `class_id` and `roster_entry_id` (nullable FKs, set exactly for `student`), and a partial unique index on `roster_entry_id` for open Invitations.
- Every Epic 3 role-Invitation path (Admin list, resend, «Du er invitert» check/accept) reads only `kind = 'role'`; a Student link reads as `invitation_link_invalid` until Story 4.5 builds Student registration.
- Send is idempotent: entries insert with ON CONFLICT DO NOTHING under the staging lock, only new entries get an Invitation, `dedupe_key` = `invitation:<invitation id>`; a repeat finds no staging and answers 404 `not_found`.
- The validity runs through the last valid day in Europe/Oslo: last day = today (Oslo, from the api's clock) + N; `expires_at` = the next Oslo midnight after it.
- Logs, job args and notices hold ids and counts only. `identity` imports no `classes` code: the Class name reaches the mail through a resolver `classes.service` registers with `identity.service`.
- Copy in `nb.ts`; errors clear as the user types; the result line clears when a new upload, paste or send starts.

**Never:** Student registration or acceptance (4.5); bounces and counts beyond «sent» (4.6); reminders, re-inviting expired or already-listed addresses (4.7); manual registration (4.8); Assistant lecturers (4.9 — the policy test uses a non-owner Lecturer); comparing DB time with host time or ordering by timestamps in tests; real mail.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Send | staged upload `id`, 3 valid + 1 invalid, `valid_days` 14 at 2026-11-19 09:00Z | 201 `{sent: 3, valid_days: 14, last_valid_day: "2026-12-03"}`; 3 entries `invited`; 3 open `student` Invitations, `expires_at` 2026-12-03T23:00Z; 3 notices `(user_id NULL, invitation, ref)`; staging gone | – |
| Validity | `valid_days` 0, 61, 1.5 | 422 `invalid_request`, `fields.valid_days` set; nothing changes | inline «Velg et helt antall dager mellom 1 og 60.» |
| Repeat | same body again | 404 `not_found`; no new entry, Invitation or notice | – |
| Stale | `upload_id` of a replaced staging | 404 `not_found`; nothing changes | page reloads the staging |
| On Roster | staged `Ola@X.no` with entry `ola@x.no` (invited or registered) | row reason `on_roster`; excluded from `valid_count` and from the send | «Står allerede på Klasselista» |
| Nothing valid | staging with `valid_count` 0 | 422 `nothing_to_send`; staging kept | – |
| Scope | other Lecturer, unknown Class | 403 `forbidden`; nothing changes | – |
| Mail | job runs | to the address; text names the Class, «gyldig til og med 3. desember 2026», `/invitasjon#<token>` | expired/voided → skipped `no_recipient` |
| 400 | paste of 400 addresses, send | 201 `sent: 400` once rows commit; 400 notices | – |

</intent-contract>

## Code Map

- `backend/app/modules/identity/models.py` -- `invitations` (line 70), `roster_uploads`; add `roster_entries`, new invitation columns, `uq_invitations_open_roster_entry`.
- `backend/migrations/versions/0025_roster_upload_source.py` -- pattern for 0026; `backend/tests/test_migrations.py:65` HEAD, `:509` CHECK-vs-enum test (add `ck_invitations_kind`, `ck_roster_entries_registration`; `ck_invitations_role` stays).
- `backend/app/modules/identity/repo.py:127-443` -- invitation SQL; `list_invitations` (380) must filter `kind = 'role'`; add roster-entry and bulk Student-Invitation SQL; `lock_roster_staging` (651), `roster_upload_for_class` (707), `roster_rows` (726).
- `backend/app/modules/identity/service.py` -- `_issue_invitation` (413) pattern; `invitation_mail_recipient` (459) gains the Student branch; `check_invitation` (529) and `resend_invitation` (951) refuse non-role kinds; `register_revoke_blocker` (707) registry pattern for `register_class_name`; `evaluate_roster_rows` (1436) gains `on_roster`; `stage_roster_upload/paste`, `_staged_out` read Roster addresses; add `send_roster_invitations(s, …)`, `roster_counts`.
- `backend/app/modules/identity/schemas.py:374-412` -- `RosterInvalidRow.reason` adds `on_roster`; `RosterUploadOut` adds `id`.
- `backend/app/modules/classes/{service,routes,schemas,repo}.py` -- `may_manage` (service 126); add `send_invitations` command, `POST /api/classes/{id}/invitations` (`classes.manage`), `RosterSendIn/Out`, `roster_count` on `ClassListItem`/`ClassOut`, class-name resolver.
- `backend/app/platform/email/templates/kinds/invitation.{txt,html}.j2` -- branch on `kind`.
- `backend/app/platform/email/senders.py:64` -- `ResendSender` paces sends to `MAIL_PROVIDER_PER_SECOND` (config, default 2).
- `backend/tests/classes/test_roster_upload.py` -- `klass`, `upload`, `settings_env`, `NOW`; `tests/messaging/helpers.py` `drain`, `mails`, `rows`; `tests/identity/test_invitations.py:23` link regex.
- `frontend/src/modules/classes/{roster-upload.tsx,roster.ts,api.ts,lecturer-home.tsx,class-page.tsx}`, `frontend/src/copy/nb.ts:296-408`, `frontend/src/components/text-field.tsx`.
- `frontend/e2e/roster-upload.spec.ts` -- `classPage`, `tabTo`, `answerTo`; `frontend/e2e/support/auth.ts:93` dev-mailbox read.

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0026_roster_entries_student_invitations.py`, `identity/models.py` -- tables, columns, CHECKs, indexes.
- `identity/schemas.py`, `identity/repo.py`, `identity/service.py` -- `on_roster`, upload `id`, roster entries, Student Invitations, mail context, role-path filters, counts, class-name registry.
- `classes/{schemas,repo,service,routes}.py` -- send command and route, counts, resolver registration.
- `platform/email/templates/kinds/invitation.*.j2`, `platform/email/senders.py`, `platform/config.py` -- Student mail, pacing.
- `backend/tests/classes/test_roster_send.py` (new), `tests/test_migrations.py`, `tests/identity/test_invitation_list.py` -- matrix tests, list ignores Student rows.
- `frontend/src/lib/api/{openapi.json,schema.ts}` -- regenerate.
- `frontend/src/modules/classes/*`, `frontend/src/copy/nb.ts` -- send form, result line, counts, Issue #86 fixes, unit tests in `roster.test.ts`/`classes.test.ts`.
- `frontend/e2e/roster-send.spec.ts` (new) -- send flow at 320 and 1440 px by keyboard with axe, validity error, one mail check through the dev mailbox.
- `backend/app/modules/classes/README.md` -- Roster and send decisions.

**Acceptance Criteria:**
- Given a staging with valid rows, then the send area shows «Gyldig i antall dager» prefilled 14 with «Mellom 1 og 60 dager.», and «Send N Invitasjoner»; when pressed, the page shows «N Invitasjoner sendt. Gyldige til og med 3. desember.» with focus on it, and the upload box returns to «Velg fil».
- Given an out-of-range or non-whole validity, then the field shows the error and nothing is sent; typing clears it.
- Given sent Invitations, then «Klassene dine» shows each Class's Roster count and the Class page states how many addresses are on its Roster.
- Given Issue #86, then the column reason counts the same invalid rows as «Ugyldige rader: N av M», the invalid-row header names the chosen column (its header, or «Kolonne X»), and the invalid-row note is absent when no rows are staged.
- Given Playwright with axe, then the send flow passes by keyboard at 320 and 1440 px with no page-level horizontal scroll, and the mail in the dev mailbox names the Class and the last valid day.

## Spec Change Log

## Review Triage Log

### 2026-11-19 — Review pass
- verdicts: 40 findings — high 0, medium 4, low 30, false 6, maybe-false 0
- findings:
  - `[low]` `[reject]` (blind) A removed address passes as valid but ON CONFLICT drops it — nothing sets `removed_at` before Story 4.8, which owns removal and re-adding.
  - `[low]` `[reject]` (blind) Button count and result count can differ — only via removed rows (above); under the staging lock the Roster read and the insert agree.
  - `[false]` `[reject]` (blind) Student tokens reach the accept paths — both accept functions call `check_invitation` first, which refuses non-role kinds; renewal marking a Student Invitation is wanted (4.7's «asked for new Invitation»).
  - `[low]` `[reject]` (blind) Student links are dead until 4.5 — the intent says build only this story; stated in the spec, the README and a test.
  - `[low]` `[patch]` (blind) The Student mail says «Opprett konto» to addresses that may have an account — wording changed to «Bli med her» / «Bli med i Klassen».
  - `[low]` `[reject]` (blind) No composite FK ties the Invitation's Class to its Roster entry — one writer sets both from the same row.
  - `[low]` `[reject]` (blind) No index on `invitations.class_id` / `roster_entries.user_id` — Classes are archived, not deleted, in v1.
  - `[low]` `[patch]` (blind) The downgrade path for Student Invitations is untested — grouped with the verification-gap downgrade row; the test now inserts a Student Invitation. Leftover notices resolve to `no_recipient`.
  - `[false]` `[reject]` (blind) Resolver registration by import side effect fails silently — the api imports `classes.routes`, the worker imports it via `messaging.delivery`, and a missing resolver raises, never skips.
  - `[low]` `[reject]` (blind) The cached Pacer lock may bind to another event loop — the worker runs one loop; tests use the mock sender.
  - `[low]` `[reject]` (blind) No 429 backoff — failed sends are already retried by the delivery retry of Story 3.5.
  - `[low]` `[reject]` (blind) «Gyldig i N dager» is ambiguous about today — deliberate: valid through today + N in Oslo, and the result line names the last day.
  - `[low]` `[reject]` (blind) The year is in the mail but not on the page; month names in three places — deliberate (the page omits the current year); templates cannot import nb.ts.
  - `[low]` `[reject]` (blind) The page's year uses the browser date, not Oslo — matters only for a send around New Year abroad; day and month are the api's.
  - `[false]` `[reject]` (blind) Sending is not audited — the epic asks for audit rows on staff changes and archive only; logs hold ids and counts.
  - `[low]` `[patch]` (blind) Missing tests: archived Class, deleted Class, lax `valid_days` — `valid_days` is now strict (`"14"` and `true` refused, tested); archive arrives in 4.10, which must cover every mutating route; Classes are not deleted in v1.
  - `[low]` `[reject]` (blind) The 400-address timing bound is loose — the test pins counts; the bound catches only a gross regression by design.
  - `[false]` `[reject]` (blind) `defer_many` is untested against procrastinate internals — the 400-address test counts the deferred jobs and their distinct locks in `procrastinate_jobs`.
  - `[low]` `[patch]` (blind) `nothing_to_send` does not refetch the staging — the page refetches on `not_found` and `nothing_to_send`.
  - `[low]` `[reject]` (blind) The Lærerhjem count mixes invited and registered; the refused-send log lacks `user_id` — the count is the Roster size UX-DR56 asks for; the status split is 4.7.
  - `[low]` `[reject]` (edge) A removed Roster row matches a staged address — as the first blind row.
  - `[low]` `[reject]` (edge) All addresses lose the conflict, 201 with `sent` 0 — unreachable before 4.8 (as above).
  - `[low]` `[reject]` (edge) An archived Class can be sent to — `archived_at` is never set before Story 4.10, which adds `is_writable` to every mutating route.
  - `[false]` `[reject]` (edge) Renewal on a Student Invitation is lost — kept for 4.7's «asked for new Invitation» status, read from the Roster side.
  - `[medium]` `[patch]` (edge) After a 404 the refetch can remove the staging, unmounting SendArea and its error — the send error now renders outside SendArea.
  - `[low]` `[patch]` (edge) Lax int accepts `true`/"14" — grouped with the blind missing-tests row; `strict=True`.
  - `[low]` `[reject]` (edge) Pacer lock bound to another loop — as the blind row.
  - `[low]` `[reject]` (edge) A Class deleted between the check and the send gives a 500 — no Class delete in v1.
  - `[low]` `[reject]` (intent) Idempotency comes from the staging lock and `upload_id`, not the dedupe key — the AC's outcome (no second Invitation or mail) holds and is tested; each notice still carries its `dedupe_key`.
  - `[low]` `[reject]` (intent) The UI double press is untested — the button is unavailable while sending; the api double send is tested.
  - `[low]` `[reject]` (intent) The Assistant lecturer is not tested at the endpoint — the role arrives in 4.9; the policy rule is unit-tested and a non-owner Lecturer is tested.
  - `[low]` `[reject]` (intent) A server 422 for validity would not show under the field — the form refuses every value the api would, before sending.
  - `[low]` `[reject]` (intent) The Fix 1 reason now cites validity and reads «0 av N» on a re-upload of a sent list — the count is true and the list gives each row's reason; the issue asked for the counts to agree.
  - `[low]` `[reject]` (intent) Fix 3 is implemented literally (no rows), not «no invalid rows» — the issue's own wording.
  - `[low]` `[reject]` (intent) The Class page also shows the Roster count — a small addition; the page otherwise gives no Roster size after sending.
  - `[medium]` `[patch]` (verification-gap) `get_sender` / `ResendSender` pacing wiring is untested — a test sends two mails through a paced `ResendSender` and checks `get_sender` shares `pacer(2.0)`.
  - `[medium]` `[patch]` (verification-gap) Batches over 1000 are never exercised — batch sizes are module constants; the 400-address test runs with 150 and checks entries, Invitations, notices and jobs.
  - `[low]` `[patch]` (verification-gap) The downgrade never meets a Student Invitation — the test inserts a Class, Roster entry and Student Invitation before downgrading.
  - `[medium]` `[defer]` (verification-gap) The sendGone recovery path has no UI test — deferred (frontmatter `deferred`); the api side is pinned.
  - `[false]` `[reject]` (verification-gap, other) Renewal on a Student link is silently lost — as the edge renewal row.

## Design Notes

- Copy: `on_roster` «Står allerede på Klasselista»; reason line «Valgt fordi alle rader unntatt seks er gyldige adresser.» built from `valid_count`/`invalid_rows` (so it matches the heading), «Ingen rader i denne kolonnen ser ut som adresser.» still from `chosen_count`.
- Student mail: «Du er invitert til Klassen class-of-1994 i ØL-spillet.», «Opprett konto», «Invitasjonen er gyldig til og med 3. desember 2026 og kan brukes én gang.» Subject unchanged.
- The Student link lands on «Du er invitert» (`/invitasjon`), which says the link does not work until Story 4.5 adds Student acceptance.
- Pacing: one `asyncio.Lock` and a minimum interval per process in `ResendSender`; the `worker-batch` mail queue runs one job at a time, so one process paces all sends. The mock sender is not paced.

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/classes tests/identity/test_invitation_list.py tests/identity/test_invitations.py tests/test_migrations.py -q` -- pass.
- `cd backend && uv run pytest -q && uv run ruff check . && uv run ruff format --check .` -- pass.
- `cd frontend && npm run typecheck && npm test && npm run check:copy && npm run lint:colours && npm run build` -- pass.
- `cd frontend && npx playwright test` against the rebuilt compose stack with `worker-batch` -- pass.

## Auto Run Result

Status: done

**Summary.** «Send N Invitasjoner» now sends. `POST /api/classes/{id}/invitations` (`classes.manage`) takes the staging's `upload_id` and `valid_days` (1–60, default 14). One transaction in `classes.service`, through `identity.service`: valid staged addresses go to the new `roster_entries` table, the staging is deleted, and each new entry gets a `student` Invitation (migration 0026: `invitations.kind`, `class_id`, `roster_entry_id`, nullable `role`) with its `invitation` notice by reference and claim job, each kind enqueued in one statement. Links work through the last valid day in Europe/Oslo. The mail names the Class and «gyldig til og med 3. desember 2026»; the link lands on `/invitasjon`, which refuses Student tokens until Story 4.5. Staged addresses already on the Roster are listed «Står allerede på Klasselista». The Lærerhjem and the Class page show the Roster count. The Resend sender paces to `MAIL_PROVIDER_PER_SECOND` (2). Issue #86: the column reason counts valid rows like the heading; the invalid-row header names the chosen column; the note hides when no rows are staged.

**Process note.** The caller required the implementation in the orchestrating context. The four review layers ran as sub-agents; their reports were read from their transcripts.

**Files changed**
- `backend/migrations/versions/0026_roster_entries_student_invitations.py`, `identity/models.py`, `identity/schemas.py`: Roster table, Invitation kinds, `on_roster`, upload `id`.
- `identity/repo.py`, `identity/service.py`: Roster SQL, send command, mail context, class-name registry, role-only filters, counts.
- `classes/{schemas,repo,service,routes}.py`, `classes/README.md`: send route, counts, resolver, decisions.
- `messaging/delivery.py`: imports `classes.service` so the worker has the resolver.
- `platform/notify`, `platform/jobs`: `enqueue_by_ref`, `defer_many`. `platform/email/senders.py`, `platform/config.py`: pacer. `templates/kinds/invitation.*.j2`: Student mail.
- Tests: `tests/classes/test_roster_send.py` (new), `tests/test_migrations.py`, `tests/platform/test_email.py`, `tests/conftest.py`.
- Frontend: `modules/classes/{roster-upload.tsx,roster.ts,roster.test.ts,api.ts,class-page.tsx,lecturer-home.tsx}`, `copy/nb.ts`, `lib/api/{openapi.json,schema.ts}`, `e2e/roster-send.spec.ts` (new), `e2e/roster-upload.spec.ts`.

**Review findings.** 40: 4 medium, 30 low, 6 false. Patched: 3 medium and 6 low (some grouped). Deferred: 1 medium (browser test of the refused-send recovery). Rejected: 24 low and 6 false, each with its reason in the Review Triage Log.

**Follow-up review recommended: true.** Three medium entries were patched. Named unverified risk: the page's recovery after a refused send (message kept outside the send area, staging refetched) has no browser test.

**Verification**
- Backend: ruff clean; full pytest 2101 passed (72 s).
- Frontend: typecheck, `npm test` (348), `check:copy`, `lint:colours` and build pass; Playwright 142 passed against the rebuilt stack with `worker-batch`, including the dev-mailbox mail check.
- No new test takes over 1 s (slowest 0.94 s, the 400-address send).
- Shared test databases: revision 0026 added and migrated; not changed after it ran.
- Layout checked on screenshots at 390 and 1280 px (send form, error, result line, Lærerhjem count).

**Decisions taken in place of the founder**
- Validity range 1–60 whole days, default 14; valid through the last day in Europe/Oslo (expiry at the next Oslo midnight).
- Send invites only addresses new to the Roster; addresses already on it (invited or registered) are listed `on_roster`; re-inviting is 4.7's reminder.
- A repeated or stale send answers 404 `not_found`; nothing valid answers 422 `nothing_to_send`; the page says «Klasselista er endret …» and reloads the staging.
- `invitations.kind` `role`/`student`, `role` made nullable (expand-only); the Admin list, resend and «Du er invitert» take role Invitations only until 4.5.
- Student mail: subject unchanged, «Du er invitert til Klassen X i ØL-spillet. Bli med her:», «gyldig til og med D. måned ÅÅÅÅ».
- Result line «N Invitasjoner sendt. Gyldige til og med 3. desember.» (year only when not the current one); the Roster count also on the Class page.
- Provider pacing at 2 mails/s per process (`MAIL_PROVIDER_PER_SECOND`).
- Issue #86: reason «Valgt fordi alle rader unntatt seks er gyldige adresser.»; header uses the column header or «Kolonne X»; note hidden when no rows are staged.
- All new copy is [ASSUMPTION] except «Send N Invitasjoner».

**Residual risks**
- Student links do not work until Story 4.5.
- Removing and re-adding a Roster address (4.8) must handle the unique `(class_id, email)` row.
- Real Canvas exports are still untested (open point from 4.2).
