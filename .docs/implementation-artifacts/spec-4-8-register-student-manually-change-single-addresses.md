---
title: 'Story 4.8: Register a Student manually and change single addresses'
type: 'feature'
created: '2026-11-19'
status: 'done'
baseline_revision: '53b0b8a4f899ba268c6ca6749d6dcc07a09b3af2'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-4-context.md'
  - '{project-root}/.docs/planning-artifacts/ux-designs/ux-beergame-2026-11-05/DESIGN.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** «Registrer manuelt» on an invalid row does nothing (4.3), there is no way to put a late Student or a corrected address on the Roster without a whole new upload, and no way to take an address off. A Student whose address bounces or who never gets the mail stays out of the Class, and Epic 5 cannot keep a removed Student out.

**Approach:** Three owner-only commands in `classes.service`, each one transaction through `identity.service` under the Roster staging lock: register manually (create or reuse the User, entry `registered_manually`, set-password mail), add one address (validated by `address_problem`, entry not yet invited), remove an entry (marked removed, open Invitations void, `user:<id>`). Re-adding a removed address reactivates its entry. The 4.7 status list gains `not_invited` and per-row «Registrer manuelt» and «Fjern»; «Klasseliste» gains «Legg til adresse» and «Registrer manuelt» forms; the invalid rows' «Registrer manuelt» opens the same form in place.

## Boundaries & Constraints

**Always:**
- Manual registration `POST /api/classes/{id}/roster/manual` `{email, name, roster_entry_id?, upload_row?: {upload_id, row_number}}`: address normalised and checked by `address_problem`; name as `AcceptInvitationIn` (`name_empty`/`name_too_long`). The User of the address is reused (name and password untouched) or created with no password (`users.password_hash` nullable, migration 0030) and no account role. The entry for the address (new, existing unregistered, or removed → reactivated) is linked to the User and set `registered_manually`; its open Invitations are voided and renewal requests cleared; `user:<id>` emitted. Already registered (not removed) → 422 `invalid_request` `fields.email = already_registered`.
- `roster_entry_id` names the row the form opened from: when the address typed differs, that entry (if unregistered and not removed) is removed in the same transaction — this is how a wrong address is changed. `upload_row` deletes that staged row in the same transaction (the invalid row it corrected); a gone staging or row is ignored.
- Mail: notice kind `manual_registration`, `immediate`, addressed to the User, `ref` = the Roster entry id, dedupe key per entry and registration. A User without a password gets a single-use `password_resets` link valid to the end of the `MANUAL_REGISTRATION_LINK_DAYS`-th day (Europe/Oslo, setting default 14) leading to «Nytt passord» (`/nytt-passord#token`); a User with a password gets the same mail without a link («logg inn som vanlig»). Mail names the Class, headed «ØL-spillet». The context resolver answers None (no mail) when the entry is removed, no longer manual, or (no-password case) the link is used or expired.
- Login: a User with no password never authenticates (dummy hash compared, same timing).
- Add `POST /api/classes/{id}/roster/entries` `{email}`: `address_problem` reason or `on_roster` → 422 `invalid_request` `fields.email = <reason>`; new → entry `invited` with no Invitation (derived status `not_invited`); removed → reactivated as it was (a registered Student has access again, no mail). 201 `{id, email, status}`.
- Remove `DELETE /api/classes/{id}/roster/entries/{entry_id}` → 204; entry `removed_at` set, open Invitations voided, `user:<id>` emitted when linked; the User, other Classes and other entries untouched. Unknown, foreign or already removed → 404 `not_found`.
- Roster send (4.4) of a removed address reactivates its entry; unregistered reactivated entries get an Invitation, registered ones none (the count matches «Send N»).
- Status `not_invited` (newest Invitation none, not registered): text «Ikke invitert ennå», in filter and «Uregistrert» total, remindable (reminder sends its first Invitation).
- All three routes `classes.manage` (owners only); other/unknown/malformed Class → 403 `forbidden`. Logs ids/counts only. Copy in `nb.ts`. Field errors clear as the user types; a result line clears when a new action starts. Forms in place, focus to first field, «Avbryt» returns focus to the opener. The removal consequence is written above its button.

**Never:** changing the address or name of a registered User's account (no edit of a registered address; remove and add instead); revealing whether an address already has an account; storing a derived status; Assistant lecturers (4.9); archive (4.10); resetting demo accounts or changing demo Students' addresses; comparing DB time with host time or ordering by timestamps in tests.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Manual, new address | `ny@x.no`, «Kari» | User without password, entry `registered_manually`, in `registered_students`, enrolled; one mail with link | – |
| Manual, existing User | address of a User with password | same User, name unchanged; mail without link | – |
| Manual, invited entry | entry with open Invitation | entry manual; Invitation voided | – |
| Manual, changed address | row `feil@x` (unregistered), typed `rett@x.no` | `rett@x.no` manual; old entry removed | registered address → 422 `already_registered` |
| Manual from invalid row | `upload_row` of staged row 3 | staged row 3 gone, staging re-evaluated | gone staging ignored |
| Set password | manual link → «Nytt passord» | password set once; login works | second use → link invalid |
| Add | `late@x.no` | `not_invited`, remindable; reminder gives first Invitation | `x@` → `missing_domain`; on Roster → `on_roster` |
| Remove registered | entry of Student | no access (enrolled 403), not in `registered_students`, `user:<id>`, account kept | unknown → 404 |
| Re-add removed | add or send same address | entry active again; registered Student has access, no new mail | – |

</intent-contract>

## Code Map

- `backend/app/modules/identity/models.py:30` -- `password_hash` nullable; `backend/migrations/versions/0030_users_password_optional.py` (new; downgrade gives NULL rows the unusable hash `'!'`, which never verifies, then sets NOT NULL).
- `backend/app/modules/identity/repo.py:756` -- `insert_roster_entries` (reactivate removed on send), `roster_entry_by_email(lock)`, `reactivate_entry`, `remove_entry`, `set_manual_entry`, `delete_staged_row`, newest usable reset for a User; reuse `void_open_entry_invitations`, `clear_entry_renewals`, `lock_roster_staging`, `insert_password_reset`, `insert_user`.
- `backend/app/modules/identity/service.py` -- `authenticate` (None hash), `register_manually`, `add_roster_entry`, `remove_roster_entry`, `manual_registration_mail_context`, `MANUAL_REGISTRATION` kind; `send_roster_invitations` reactivation. Model on `send_entry_reminders` (1903) and `request_password_reset` (223).
- `backend/app/platform/config.py:113` -- `manual_registration_link_days: int = Field(14, ge=1)`.
- `backend/app/modules/messaging/delivery.py:76` -- `manual_registration` kind; templates `backend/app/platform/email/templates/kinds/manual_registration.{txt,html}.j2` modelled on `invitation.*`.
- `backend/app/modules/classes/{schemas,service,routes}.py` -- `RegistrationStatus.not_invited`, `_status` (no Invitation → `not_invited`), `ManualRegistrationIn/Out`, `RosterEntryIn/Out`; three routes after `/reminders`; README section.
- Tests: new `backend/tests/classes/test_roster_entries.py` (reuse `klass`, `sent_class`, `accept`, `execute`, `drain`, `mails`, `rows`, `as_user`, `OTHER`); `tests/test_migrations.py` HEAD 0030.
- Frontend: `src/modules/classes/api.ts` (calls), new `roster-entry.tsx` (ManualForm, AddForm, RemoveConfirm) + `roster-entry.ts` (field reasons) and test; `roster-upload.tsx` InvalidRows button opens ManualForm in place; `class-page.tsx` («Legg til adresse», «Registrer manuelt» Lenker in Klasseliste); `registration-status.tsx` rows get «Registrer manuelt» (unregistered) and «Fjern»; `registration.ts` STATUSES + `not_invited`; `copy/nb.ts`; `lib/api/{openapi.json,schema.ts}` regenerated; new `e2e/roster-entries.spec.ts`.

## Tasks & Acceptance

**Execution:**
- Backend identity: migration 0030, config, repo, service (manual, add, remove, reactivation on send, mail context, login with no password).
- Backend messaging: kind + templates.
- Backend classes: schemas, service, routes, README.
- Backend tests: every matrix row; scope (other Lecturer, unknown, malformed → 403); no address in logs; mail rendered with link and without; `registered_students` after removal; 4.4 re-send of removed.
- Frontend: forms and row actions as in the Approach; invalidate class, classes, registrations, invitations, roster-upload queries after each command; result line per command («a@x.no er registrert manuelt og får en e-post.», «a@x.no er lagt til. Ikke invitert ennå.», «a@x.no er fjernet fra Klasselista.»).
- `frontend/e2e/roster-entries.spec.ts`: on a fresh Class add one address, register one manually, remove one, re-add; set password from the mailbox link and log in; axe at 320 and 1440 px, no horizontal scroll.

**Acceptance Criteria:**
- Given an invalid row or an unregistered address, when the Lecturer follows «Registrer manuelt», then an in-place form opens with the address prefilled where one exists and a name field, primary button «Registrer studenten», focus on the first field, and «Avbryt» returns focus to the link.
- Given a valid submit, then the address is «Registrert manuelt» in the list, the Student is in the Class at once, and a mail with a single-use link to «Nytt passord» arrives.
- Given «Legg til adresse», then a valid address shows «Ikke invitert ennå» and counts in «Send påminnelse til N»; a duplicate is refused beside the field.
- Given «Fjern» on a row, then the consequence is written above the button before it is pressed, and after removal the row is gone and a registered Student no longer reaches the Class.
- Given Playwright with axe at 320 and 1440 px, then the forms pass with no horizontal scroll.

## Spec Change Log

## Review Triage Log

### 2026-11-19 — Review pass
- verdicts: 36 findings — high 0, medium 3, low 30, false 3, maybe-false 0
- findings:
  - `[low]` `[patch]` (blind) `_entry_status` raises IndexError (500) when the entry vanishes between commit and read — it now falls back to the status the command wrote.
  - `[false]` `[reject]` (blind) Other readers of `password_hash` may get None — only `authenticate` verifies a stored hash (grep); reset and acceptance write it.
  - `[false]` `[reject]` (blind) Downgrade hash `'!'` may raise in bcrypt — `auth.verify_password` catches `ValueError` and returns False.
  - `[medium]` `[patch]` (blind) A put-back entry keeps old renewal requests — removal now clears the entry's renewal requests (`_remove_entry`); test `test_a_request_for_a_new_invitation_goes_with_the_removal`.
  - `[low]` `[reject]` (blind) A voided Invitation reads «Invitasjonen er utløpt» — 4.7's decided copy; a voided newest Invitation needs a removal and put-back of an unregistered address, rare, and the address is remindable either way.
  - `[low]` `[patch]` (blind) Removal consequence speaks of an Invitation on a `not_invited` row — own line `removeNotInvited`.
  - `[low]` `[reject]` (blind) Re-adding a removed never-invited address says «er lagt til» rather than «står på Klasselista igjen» — rare, and telling them apart needs a new api field.
  - `[low]` `[reject]` (blind) Result lines in other areas stay when an action starts elsewhere — each area clears its own line on its own next action; cross-area clearing needs page-level state for a cosmetic gain.
  - `[low]` `[patch]` (blind) Focus lost when removal answers `not_found` — the panel now closes with «Adressen står ikke lenger på Klasselista.» as the focused result line. The pending-unmount half is rejected as edge row 6.
  - `[low]` `[patch]` (blind) Re-sending a removed registered address is untested — added `test_a_removed_registered_student_sent_again_has_access_and_no_invitation`.
  - `[low]` `[patch]` (blind) Cross-Class `roster_entry_id` / entry ids untested — added `test_an_entry_of_another_class_is_not_found_and_that_class_is_untouched`.
  - `[low]` `[reject]` (blind) Extra set-password links stay valid and the dedupe key is random — each link works once and using one voids the rest; the key is per registration, which is what is mailed.
  - `[low]` `[patch]` (blind) Email over 320 characters gets no wording — `string_too_long` now reads «Adressen er for lang.» beside the field (unit test). The control-character name half is rejected: same rule and code as Story 3.8's acceptance.
  - `[false]` `[reject]` (blind) `replaces` voids Invitations of a row it keeps — a registered row has no open Invitation (accepted) and a removed one had its links voided at removal, so nothing changes.
  - `[medium]` `[patch]` (edge) Roster send reactivation keeps a renewal request — grouped with blind row 4.
  - `[medium]` `[patch]` (edge) Add restore keeps a renewal request — grouped with blind row 4.
  - `[low]` `[patch]` (edge) IndexError after commit — grouped with blind row 1.
  - `[low]` `[patch]` (edge) `string_too_long` unworded — grouped with blind row 13.
  - `[low]` `[patch]` (edge) `not_invited` removal copy — grouped with blind row 6.
  - `[low]` `[reject]` (edge) A row form unmounts if the filter changes or a resend opens while it is saving — needs a deliberate second action during a sub-second request; guarding it adds state across components.
  - `[low]` `[reject]` (edge) Switching between «Legg til adresse» and «Registrer manuelt» while one saves — as edge row 6.
  - `[low]` `[reject]` (edge) Opening another invalid row while one saves — as edge row 6.
  - `[low]` `[patch]` (edge) Remove `not_found` drops the message — grouped with blind row 9.
  - `[low]` `[reject]` (edge, claim) «Send N» can exceed `sent` when a removed registered address is staged — the address is put back with access (its purpose), only the count line is off; rare (re-uploading a removed registered Student) and fixing it changes 4.3's evaluation.
  - `[low]` `[reject]` (edge, claim) Dedupe key random — as blind row 12.
  - `[low]` `[reject]` (edge, claim) Result line per area — as blind row 8.
  - `[low]` `[patch]` (verification-gap) Mail suppression untested — the removal test now asserts no mail after drain, and `test_a_used_link_mails_no_link_and_an_expired_one_no_mail` covers used and expired links.
  - `[low]` `[patch]` (verification-gap) Another Class's entry → 404 untested — grouped with blind row 11.
  - `[low]` `[patch]` (verification-gap) Removed registered re-send untested — grouped with blind row 10.
  - `[low]` `[reject]` (verification-gap, other) «Send N» vs `sent` — as edge row 10.
  - `[low]` `[patch]` (intent) «Other Classes untouched» not shown at access level — the cross-Class test removes the Student from one Class and checks the other still answers 200.
  - `[low]` `[patch]` (intent) First Invitation «alone» for a `not_invited` address untested — added `test_a_not_invited_address_gets_its_first_invitation_alone`.
  - `[low]` `[patch]` (intent) Focus and «Avbryt» from the invalid-row trigger untested — the e2e now checks both.
  - `[low]` `[reject]` (intent) Assistant lecturer cannot be shown — Assistants arrive in Story 4.9; only owners pass the policy now.
  - `[low]` `[reject]` (intent) Correction only through manual registration, no correct-and-invite — a design decision recorded below; remove + add covers correct-and-invite.
  - `[low]` `[reject]` (intent) Changes reach 4.4's send, login and a 4.7 e2e assertion — each follows from a 4.8 criterion (re-add, no password, new row actions).

## Design Notes

- Manual registration sets a first password through the existing `password_resets` table and «Nytt passord» page; its link lives `MANUAL_REGISTRATION_LINK_DAYS` instead of an hour. The mail's `ref` is the Roster entry, so it can name the Class; the link is the User's newest usable reset.
- A deactivated User's address can be registered (no account state is revealed); the pipeline drops their mail as for any deactivated User.
- Copy [ASSUMPTION]: «Legg til adresse», «Registrer manuelt» (UX spine), «Navn», «E-post», «Registrer studenten», «Legg til», «Fjern», consequence «a@x.no mister tilgangen til Klassen. Kontoen og andre Klasser beholdes.» / «Invitasjonen til a@x.no slutter å virke.», «Fjern fra Klasselista», «Ikke invitert ennå», «Er allerede registrert i Klassen», mail subject «Du er registrert i ØL-spillet».

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/classes tests/test_migrations.py tests/identity -q` -- pass.
- `cd backend && uv run pytest -q && uv run ruff check . && uv run ruff format --check .` -- pass.
- `cd frontend && npm run typecheck && npm test && npm run check:copy && npm run lint:colours && npm run build` -- pass.
- `cd frontend && npx playwright test` against the rebuilt stack with `worker-batch` -- pass.

## Auto Run Result

Status: done

**Summary.** A Lecturer can now register a Student by hand and add or remove single addresses. `POST /api/classes/{id}/roster/manual` reuses the User of the address unchanged, or creates one without a password (migration 0030) and no account role. It links the Roster entry as `registered_manually`, so the Student is in the Class at once, voids the entry's open links and emits `user:<id>`. The mail `manual_registration` (`immediate`) names the Class. A User with no password gets a single-use link to «Nytt passord», valid to the end of the `MANUAL_REGISTRATION_LINK_DAYS`-th day (default 14). The same command corrects a wrong unregistered address (`roster_entry_id`) and deletes the staged invalid row it came from (`upload_row`). `POST /api/classes/{id}/roster/entries` adds one address, checked by `address_problem` or refused as `on_roster`. It gets no Invitation (`not_invited`, counted and remindable), and a removed address is put back as it was. `DELETE /api/classes/{id}/roster/entries/{entry_id}` removes an entry, voids its links and ends the Student's access. A Roster send also puts a removed address back. On the page: «Legg til adresse» and «Registrer manuelt» under «Klasseliste»; the invalid rows' «Registrer manuelt» opens the form in place; each status row has «Registrer manuelt» (not registered) and «Fjern», with the consequence above the button.

**Process note.** The caller required the implementation in this context. The four review layers ran as sub-agents; their completion notices did not arrive, so their reports were read from their transcripts.

**Files changed**
- `backend/migrations/versions/0030_users_password_optional.py`, `identity/models.py`: `users.password_hash` nullable.
- `identity/{repo,service}.py`: login refuses a User without a password; `register_manually`, `add_roster_entry`, `remove_roster_entry`, mail context; the send puts removed entries back.
- `platform/config.py`: `manual_registration_link_days`. `messaging/delivery.py`, `email/templates/kinds/manual_registration.{txt,html}.j2`: the new kind.
- `classes/{schemas,service,routes}.py`, `README.md`: `not_invited`, the three commands.
- Tests: `tests/classes/test_roster_entries.py` (new, 28); `tests/test_migrations.py` (head 0030, downgrade).
- Frontend: `roster-entry.ts` (+ test), `roster-entry-forms.tsx` (new); `api.ts`, `class-page.tsx`, `roster-upload.tsx`, `registration-status.tsx`, `registration.ts` (+ test), `copy/nb.ts`, `lib/api/{openapi.json,schema.ts}`; `e2e/roster-entries.spec.ts` (new); `e2e/registration-status.spec.ts` (bounced row now has row actions, so the check names the resend button).

**Review findings.** 36: 3 medium (one root cause), 30 low, 3 false. Patched: the medium entry (renewal requests outlived a removal) and 12 low (fallback status after commit, `not_invited` removal copy, `not_found` removal, email-length wording, and tests for mail suppression, other Classes, re-sent registered Students, a first single Invitation and focus from the invalid row). Deferred: none. Rejected: the rest, each with its reason in the Review Triage Log.

**Follow-up review recommended: false.** One medium entry patched, no high.

**Verification**
- Backend: ruff clean; full pytest 2227 passed (86 s). No new test over 1 s (slowest new: 0.97 s, the cross-Class test).
- Frontend: typecheck, `npm test` (362), `check:copy`, `lint:colours`, build pass. Playwright 155 passed against the rebuilt stack with `worker-batch`, including `roster-entries.spec.ts` with axe at 320 and 1440 px and no horizontal scroll. One earlier full run, made while the backend suite ran at the same time, had 3 failures (both new specs and 4.7's 200 % case); they passed alone and in two later full runs.
- Shared test databases: migration 0030 added and migrated once; not changed after it ran.
- Layout checked on screenshots at 390 and 1280 px; the row grid was fixed so status columns align.

**Decisions taken in place of the founder**
- A registered Student's address is never edited in place: the account e-mail is their login in every Class. The Lecturer removes it and adds the new address. Only an unregistered address can be corrected, by opening «Registrer manuelt» from its row; the wrong row is then removed.
- A manually registered User is created without a password (migration 0030); the first password is set through the existing `password_resets` / «Nytt passord» flow. Until then the account cannot log in.
- An existing User is reused unchanged (name ignored); one with a password gets the mail without a link («Logg inn som vanlig»). Whether an address had an account is never shown to the Lecturer. A deactivated User's address can be registered; the pipeline sends them no mail.
- The link is valid to the end of the 14th day in Europe/Oslo, like Invitations; the setting is limited to 1–60 days.
- «Not yet invited» is derived (entry `invited`, no Invitation), not stored.
- Re-adding (by add or by a Roster send) puts a removed entry back as it was. A registered Student has access again with no mail; an unregistered one is re-invited by the send. Removal clears renewal requests.
- Registering from an invalid row deletes that staged row.
- Copy [ASSUMPTION]: as in Design Notes, plus «Ikke invitert ennå», «Adressen er for lang.», «… har ikke fått noen Invitasjon og får ingen påminnelser.», mail «Du er registrert i ØL-spillet».

**Residual risks**
- The Klasseliste forms and the status-list row forms can be open at the same time (one in-place form per area, not per page).
- «Send N» can count a removed registered address that the send puts back without an Invitation, so `sent` is lower than N.
- A User without a password who gets a Student Invitation to another Class must use «Glemt passord» first: «Du er invitert» asks for the existing account's password.
