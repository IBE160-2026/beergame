---
title: 'Story 4.7: Follow registration status and send reminders'
type: 'feature'
created: '2026-11-19'
status: 'done'
baseline_revision: '8eeaf94c61d35e790d60ae859b1f0c7f50dc7a8b'
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

**Problem:** After «Send N Invitasjoner» the Lecturer sees only four Invitation counts and the bounced addresses (4.6). They cannot see where each Roster address stands, cannot resend to those who have not registered, do not see Students' «Be om ny Invitasjon» requests (4.5), and Epic 5 has no `registered_students(class_id)` to allocate from.

**Approach:** `classes.service` derives each Roster address's status at read time from `identity`'s Roster facts (entry registration, newest Student Invitation, renewal request) and `messaging`'s delivery state, and serves it as `GET /api/classes/{id}/registrations` (totals + list). A reminder command `POST /api/classes/{id}/reminders` (`valid_days`, optional `roster_entry_id`) voids the open Invitation of each target address and issues a new one in one transaction through `identity.service`. The Class page gets «Status etter utsending» (mockup 02: stacked bar, totals as text, «Send påminnelse til N»), a confirm panel with validity, and a filterable, searchable list with a per-address resend.

## Boundaries & Constraints

**Always:**
- Statuses (api values, first match wins): `registered` (stored registered), `registered_manually` (stored; written by 4.8 — this story adds the value and migration 0029 widening `ck_roster_entries_registration`), `renewal_requested` (an unaccepted Invitation of the entry has `renewal_requested_at`), `bounced` (+`bounce_class`, newest Invitation's mail bounced), `invited` (+`last_valid_day`, newest Invitation open at the api clock), `unregistered` (newest expired or voided, or none). Removed entries are left out of everything.
- Totals: `registered`, `registered_manually`, `unregistered` (= all other statuses); `reminder_count` = `unregistered`. Computed in the api.
- Reminder targets: not registered, not removed; send-all and single both leave out an entry whose newest Invitation bounced hard and return those addresses in `left_out`. Each target: open Invitations of the entry voided, renewal requests on its Invitations cleared, one new Student Invitation (`expires_at` = `student_invitation_expiry(now, valid_days)`), mail enqueued as `immediate` `invitation` by ref with its own dedupe key. Void first, then re-read entries so a Student who accepted meanwhile gets nothing. Serialised per Class by the existing roster-staging lock. `valid_days` 1–60, default 14 (same validator as `RosterSendIn`).
- Answers: 201 `{sent, valid_days, last_valid_day, expires_at, left_out[]}`; `sent == 0` and `left_out` empty → 422 `nothing_to_send`; unknown/foreign `roster_entry_id` → 422 `nothing_to_send`. Both routes behind `classes.manage`, 403 `forbidden` alike for other/unknown/malformed Class ids.
- `classes.service.registered_students(class_id) -> list[uuid]`: Users of entries `registered`/`registered_manually`, not removed, with a `user_id`; unregistered-after-expiry never included.
- Logs hold ids and counts only, never addresses. Copy in `nb.ts`; result line clears when a new action starts; validity error clears as the user types.

**Never:** sending to registered or removed addresses; storing a derived status in `roster_entries`; the manual-registration form or `not_invited` (4.8); Assistant access (4.9); comparing DB time with host time or ordering by timestamps in tests; resetting demo accounts.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Status read | one entry per status | each with its status; totals and `reminder_count` match | other Class → 403 |
| Expiry boundary | api clock = `expires_at` − 1 µs vs = `expires_at` | `invited` vs `unregistered` | – |
| Remind all | 2 invited, 1 expired, 1 soft bounce, 1 hard bounce, 1 registered | `sent: 4`, `left_out: [hard]`; old tokens void; 4 mails | – |
| Remind one | `roster_entry_id` of an expired entry | `sent: 1` | registered/unknown → 422 `nothing_to_send` |
| Only hard bounces left | send-all | 201 `sent: 0`, `left_out: [...]` | – |
| Renewal request | Student asks on expired link | status `renewal_requested`; reminder clears it | – |
| Re-sent Invitation (4.6 deferred) | first mail soft-bounced, reminder delivered | counts `sent 2, bounced 1`, `bounces: []` | – |

</intent-contract>

## Code Map

- `backend/app/modules/identity/schemas.py:25` -- `RosterRegistration`: add `registered_manually`.
- `backend/migrations/versions/0029_*.py` -- drop/recreate `ck_roster_entries_registration` with the new value (expand-only; downgrade restores).
- `backend/app/modules/identity/repo.py:855` -- beside `class_student_invitations`: add `class_roster_facts` (entries not removed + newest Invitation per entry via DISTINCT ON id DESC + bool_or renewal), `void_open_entry_invitations`, `clear_entry_renewals`, `remindable_entries` (re-read), `registered_user_ids`. Reuse `insert_student_invitations`, `lock_roster_staging`.
- `backend/app/modules/identity/service.py:1717` -- model `send_entry_reminders(s, class_id, actor, entry_ids, valid_days, now)` on `send_roster_invitations` (token hash, `notify.enqueue_by_ref`); add `class_roster(class_id)` dataclasses and `registered_users(class_id)`.
- `backend/app/modules/classes/service.py:240` -- `registrations(user, class_id, now)`, `send_reminders(...)`, `registered_students(class_id)`; reads deliveries via `messaging.invitation_deliveries`.
- `backend/app/modules/classes/{schemas,routes}.py` -- `RegistrationStatus`, `RegistrationOut`, `RegistrationsOut`, `ReminderIn`, `ReminderOut`; two routes after `/{class_id}/invitations`.
- `backend/app/modules/classes/README.md` -- decisions.
- Tests: new `backend/tests/classes/test_registrations.py` (reuse `klass`, `staged_id`, `send`, `drain`, `bounce`, `execute`, `accept` from `test_invitation_counts.py`); extend `test_invitation_counts.py` with the re-sent case; `tests/test_migrations.py` if it pins revisions.
- Frontend: `src/modules/classes/api.ts` (hooks), new `registration-status.tsx` (+ `registration.ts` helpers and test), `class-page.tsx`, `copy/nb.ts` `classes.registration`, `lib/api/{openapi.json,schema.ts}` regenerated; new `e2e/registration-status.spec.ts` modelled on `invitation-bounces.spec.ts`.

## Tasks & Acceptance

**Execution:**
- Backend identity: enum, migration 0029, repo, service -- facts, reminders, registered users.
- Backend classes: schemas, service, routes, README -- status derivation, totals, reminders, `registered_students`.
- Backend tests -- every matrix row, each status, expiry boundary with a frozen clock, single resend, left-out hard bounce, no address in logs, scope, re-sent Invitation counts.
- Frontend -- «Status etter utsending» section (owner, once Roster has entries): stacked bar (aria-hidden, totals in text as legend), «Send påminnelse til N» Lenke opening an in-place confirm with «Gyldig i antall dager» prefilled 14 and primary «Send N påminnelser»; result line with count and left-out addresses; list with status select filter and address search, per-row «Send ny Invitasjon» (not for registered or hard-bounced) using the same validity; invalidates summary/registrations; refreshes every 15 s.
- `frontend/e2e/registration-status.spec.ts` -- send 3, hard-bounce one, expire nothing; open status, filter and search, remind all (result names the hard bounce), resend one; axe at 320 px, 200 % text and 1440 px, no horizontal scroll.

**Acceptance Criteria:**
- Given a Class with sent Invitations, when the Lecturer opens the Class page, then «Status etter utsending» shows «Registrert N», «Manuelt N», «Uregistrert N» in text and «Send påminnelse til N».
- Given the list, then each address shows its status in text (invited with last valid day, registered, registered manually, unregistered, bounced with class, asked for new Invitation) and can be filtered by status and searched by address, reflowing at 320 px.
- Given a confirmed reminder, then the result line states how many were sent and names hard-bounced addresses left out.
- Given Playwright with axe at 320 px, 200 % text and 1440 px, then the page passes with no horizontal scroll.

## Spec Change Log

## Review Triage Log

### 2026-11-19 — Review pass
- verdicts: 35 findings — high 0, medium 3, low 26, false 6, maybe-false 0
- findings:
  - `[false]` `[reject]` (blind) The renewal flag is not cleared when a new Invitation comes another way — no other path makes a second Invitation for an entry: the Roster send invites new entries only, and the reminder clears the flag. A request from an old voided link after a reminder is a new request and is shown as one.
  - `[low]` `[reject]` (blind) «Send påminnelse til N» differs from the count sent — the AC defines N as the addresses that have not registered; the confirm panel says how many hard bounces are left out and its button names the count sent.
  - `[medium]` `[patch]` (blind) The confirm panel is a dead end when every waiting address bounced hard — the link is now shown only when at least one reminder could go out; the hard bounces stay named in their rows and in «Kom ikke fram».
  - `[low]` `[reject]` (blind) «Uregistrert» in the totals and in the row mean different things — the total is the UX spine's word; the row and filter option read «Uregistrert, Invitasjonen er utløpt» in full, so they are not the same label.
  - `[low]` `[reject]` (blind) The `unregistered` label says expired for an entry with no or a voided Invitation — no entry without an Invitation exists before Story 4.8 (`not_invited`); a voided newest Invitation needs a deactivated account.
  - `[false]` `[reject]` (blind) The search does not lower-case the stored address — `ck_roster_entries_email_normalised` keeps every address lower-cased.
  - `[low]` `[reject]` (blind) Targets and `left_out` are read before the lock, so a bounce that arrives meanwhile is missed — a window of milliseconds; re-reading delivery state under the lock adds a second read path for no likely case.
  - `[low]` `[reject]` (blind) Nothing limits repeated reminders — the button is unavailable while sending; a second deliberate reminder voiding the first is what the AC asks a reminder to do.
  - `[low]` `[reject]` (blind) The acceptance race is tested only in sequence — the test pins the re-read after the void; a true interleaving needs two connections and timing control.
  - `[low]` `[patch]` (blind) Status cases missing tests — added `test_a_renewal_request_outranks_a_bounce`; an entry with no Invitation and a bounce without class cannot occur in this story (the webhook always stores a class).
  - `[low]` `[patch]` (blind) `registered_students` untested with a manual registration — grouped with verification-gap row 1.
  - `[low]` `[patch]` (blind) The other-Class test checks only the status, and the unknown-entry test has no unregistered address — both now assert `nothing_to_send`, and the unknown/registered cases keep a second invited address that must stay untouched.
  - `[false]` `[reject]` (blind) The result line points to actions that do not exist — the UI copy only names the addresses; the action names are in a schema docstring.
  - `[low]` `[reject]` (blind) No component test of focus and clearing — the e2e checks focus to the field, focus back to the link on «Avbryt», and that a new action clears the result.
  - `[low]` `[reject]` (blind) The 15 s poll of the whole list is heavy — at most a few hundred short rows; the live status follows the counts' interval.
  - `[low]` `[reject]` (blind) 201 for a reminder that creates nothing — the answer carries the left-out addresses the Lecturer acts on.
  - `[low]` `[reject]` (edge) Hard bounce or acceptance between read and lock — as blind row 7; an acceptance is re-read after the void.
  - `[low]` `[reject]` (edge) Two reminder requests back to back — as blind row 8.
  - `[false]` `[reject]` (edge) `nothing_to_send` after open Invitations were voided — the only entries voided then are removed (correct) or registered (their accepted Invitation is not voided).
  - `[medium]` `[patch]` (edge) Dead-end panel when reach is 0 — grouped with blind row 3.
  - `[low]` `[patch]` (edge) Filtering away a row with an open confirmation unmounts it with focus lost — changing the filter or search now closes a row's confirmation.
  - `[low]` `[reject]` (edge) `unregistered` label for no/voided Invitation — as blind row 5.
  - `[medium]` `[patch]` (edge, claim) The hard bounces are never named when they are all that is left — grouped with blind row 3.
  - `[low]` `[patch]` (verification-gap) `registered_students` is not tested with `registered_manually` — the test now adds a manually registered entry and expects both Users.
  - `[low]` `[patch]` (verification-gap) The 4.6 bounce list's exclusion of manual registrations is not pinned — added `test_a_manually_registered_address_is_not_listed_as_bounced`.
  - `[low]` `[patch]` (verification-gap) The renewal-over-bounce precedence is not pinned — added `test_a_renewal_request_outranks_a_bounce` (also asserts not remindable).
  - `[false]` `[reject]` (verification-gap, other) Search case — as blind row 6.
  - `[low]` `[reject]` (intent) Link count differs from the count sent — as blind row 2.
  - `[low]` `[reject]` (intent) One word «Uregistrert» for two sets — as blind row 4.
  - `[low]` `[reject]` (intent) A single resend also leaves out a hard bounce — the AC says the same command runs for one address; recorded as a founder decision.
  - `[low]` `[reject]` (intent) The `registered_students` test does not separate expiry from never registered — status is never stored, so both are the same rule by design.
  - `[low]` `[reject]` (intent) `immediate` is not asserted — the kind's mode is Story 3.5's configuration, tested there; the e2e shows the mail arrives.
  - `[low]` `[reject]` (intent) Playwright shows only invited and bounced rows — every status is covered by api tests and the labels by a unit test.
  - `[low]` `[reject]` (intent) Scope beyond the intent: migration 0029 and the bar — «Manuelt» must be storable to be counted; the bar is mockup 02's.
  - `[false]` `[reject]` (intent) The section shows on `roster_count > 0`, not once Invitations are sent — every Roster entry gets its Invitation in the same transaction in this story.

## Design Notes

- Statuses come only from reads: a bounce or expiry is never written to `roster_entries` (as 4.6).
- Copy [ASSUMPTION]: «Status etter utsending», «Registrert», «Manuelt», «Uregistrert», «Send påminnelse til N» (UX spine); statuses «Invitert, gyldig til og med 3. desember», «Registrert», «Registrert manuelt», «Uregistrert, Invitasjonen er utløpt», «Kom ikke fram, permanent/midlertidig feil», «Ba om ny Invitasjon»; actions «Send N påminnelser», «Send ny Invitasjon», «Avbryt»; result «4 påminnelser sendt. Gyldige til og med …» + «Ikke sendt, permanent feil: a@x.no».
- Layout per mockup 02: full-width bar in `lager` (registered), `ink` (manual), `axis` (unregistered) with a 2 px gap; legend squares + text; link right-aligned, wrapping below on a phone.

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/classes tests/test_migrations.py -q` -- pass.
- `cd backend && uv run pytest -q && uv run ruff check . && uv run ruff format --check .` -- pass.
- `cd frontend && npm run typecheck && npm test && npm run check:copy && npm run lint:colours && npm run build` -- pass.
- `cd frontend && npx playwright test` against the rebuilt stack with `worker-batch` -- pass.

## Auto Run Result

Status: done

**Summary.** The Lecturer can now follow every Roster address and send reminders. `GET /api/classes/{id}/registrations` (owners) works out each address's status when it is read: registered, registered manually, asked for a new Invitation, bounced (hard/soft), invited (with last valid day) or unregistered. It returns the totals and `reminder_count`. `POST /api/classes/{id}/reminders` (`valid_days` 1–60, optional `roster_entry_id`) handles all or one address in one transaction under the Roster lock: it voids the old links, reads the entries again, clears renewal requests and enqueues `invitation` mails. Hard bounces are left out and named in `left_out`. `classes.service.registered_students(class_id)` gives Epic 5 the registered Users. The Class page shows «Status etter utsending» as in mockup 02: an SVG bar, «Registrert N · Manuelt N · Uregistrert N» and «Send påminnelse til N». The link opens an in-place confirmation, prefilled with 14 days. Below it is an address list you can filter and search, with «Send ny Invitasjon» on each row. Students' «Be om ny Invitasjon» requests (Story 4.5) show as «Ba om ny Invitasjon».

**Process note.** The caller required the implementation in this context. The four review layers ran as sub-agents, and their reports were read from their transcripts.

**Files changed**
- `backend/migrations/versions/0029_roster_registered_manually.py`, `identity/schemas.py`: `registered_manually` allowed.
- `identity/{repo,service}.py`: Roster facts, `send_entry_reminders`, `registered_users`; the 4.6 bounce list also leaves out manual registrations.
- `classes/{schemas,service,routes}.py`, `classes/README.md`: status derivation, totals, reminder command, `registered_students`.
- Tests: `tests/classes/test_registrations.py` (new); `test_invitation_counts.py` (re-sent Invitation from 4.6's deferral, manual-registration bounce); `test_migrations.py` (head 0029, downgrade).
- Frontend: `modules/classes/registration-status.tsx`, `registration.ts` and its test (new); `api.ts`, `class-page.tsx`, `roster-upload.tsx`, `copy/nb.ts`, `lib/api/{openapi.json,schema.ts}`; `e2e/registration-status.spec.ts` (new).

**Review findings.** 35 findings: 3 medium (one root cause), 26 low, 6 false. Patched: 1 medium entry (dead-end confirmation when only hard bounces wait) and 7 low (closing a row's confirmation when the filter changes, plus six test additions). Deferred: none. Rejected: the rest, each with its reason in the Review Triage Log.

**Follow-up review recommended: false.** One medium entry was patched, and no high.

**Verification**
- Backend: ruff clean; full pytest 2194 passed, 4 skipped (95 s).
- Frontend: typecheck, `npm test` (358), `check:copy`, `lint:colours` and build pass. Playwright: 153 passed against the rebuilt stack with `worker-batch`, including `registration-status.spec.ts` at 320 px, 200 % text and 1440 px with axe and no horizontal scroll.
- Tests over 1 s (serial run): `test_a_reminder_to_all_voids_old_links_skips_registered_and_names_hard_bounces` (≈1.5 s) and `test_each_status_and_the_totals` (≈1.2 s). Each sends and drains 6 mails and posts 2 bounces.
- Shared test databases: migration 0029 added and migrated once; it was not changed after it ran.
- Layout checked on screenshots at 390 and 1280 px.

**Decisions taken in place of the founder**
- Status order: registered > manual > asked for new Invitation > bounced > invited > unregistered. Statuses are derived at read time and never stored.
- «Uregistrert» and «Send påminnelse til N» count every address not registered, hard bounces included. The confirmation names how many hard bounces it leaves out. The link is hidden when only hard bounces wait.
- A hard bounce is left out of single resends too (no row action); the result names it.
- Migration 0029 adds `registered_manually` now, so «Manuelt» can be counted. Story 4.8 writes it.
- A reminder clears renewal requests. A renewal request from an old link after a reminder shows again.
- 4.6's «Invitasjoner» section is kept beside the new one, so bounced addresses appear in both.
- Validity range 1–60 days, default 14, as for the Roster send. The list refreshes every 15 s.
- Copy [ASSUMPTION]: as listed in Design Notes, plus «Ba om ny Invitasjon», «Uregistrert, Invitasjonen er utløpt» and «Ikke sendt, fordi e-posten ikke kom fram (permanent feil):».

**Residual risks**
- A bounce that arrives between the status read and the reminder transaction is not seen until the next read.
- Two reminders in quick succession void the first one's links (by design).
- Addresses without any Invitation read «Uregistrert, Invitasjonen er utløpt» until Story 4.8 adds `not_invited`.
