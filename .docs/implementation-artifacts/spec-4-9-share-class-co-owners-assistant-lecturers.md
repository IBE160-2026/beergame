---
title: 'Story 4.9: Share a Class with co-owner Lecturers and Assistant lecturers'
type: 'feature'
created: '2026-11-19'
status: 'done'
baseline_revision: '1e734fea9788348dbae319d5947874f73d9d9ae4'
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

**Problem:** A Class has exactly one Lecturer. Colleagues cannot run it together, and Assistant lecturers cannot reach it at all: `class_staff.role` allows only `owner`, and every Class route is owner-only.

**Approach:** Co-owners are extra `owner` rows in `class_staff`, so they have exactly the owner's rights. Assistant lecturers join through a new Invitation kind `assistant`, whose acceptance `classes` performs through a new acceptance-handler registry in `identity.service`. `authz` gains a session role `assistant` (derived from `class_staff`, never stored) and staff-role rules per Class action. A new page «Faglærere og assistenter» lists both groups and holds the two forms and the removals.

## Boundaries & Constraints

**Always:**
- Migration 0031 (expand-only): `ck_class_staff_role` allows `owner`, `assistant`. `ck_invitations_kind` adds `assistant`. `ck_invitations_kind_fields` requires `assistant` ⇔ `class_id` set and `roster_entry_id` null (role null). A partial unique index allows at most one open (unaccepted, not voided) `assistant` Invitation per (class, email).
- Roles: `authz.ASSISTANT = "assistant"` is a session role, not an account role. `identity` gets a session-role registry. `classes` registers a provider that adds `assistant` when the User is Assistant staff of any Class. `load_user`, login and both acceptances return it in `UserOut.roles` (enum `SessionRole` = admin|lecturer|assistant). Admin grant/revoke and `AccountRole` stay unchanged.
- Policies: `lecturer_home.view` and `classes.read` allow {lecturer, assistant}. `classes.create` and `classes.manage` stay {lecturer}. `CLASS_STAFF_ROLES`: `classes.read` → {owner, assistant}, `classes.manage` → {owner}. `ClassOut` gains `can_manage` (from `authz.can`).
- Route answers per staff role. Owner and co-owner answer the same everywhere. An Assistant may read: GET class, list classes, registrations, invitation summary. An Assistant gets 403 `forbidden` on: create, institutions, roster-upload (POST/GET/PUT/DELETE), roster-paste, send invitations, reminders, roster entries add/manual/remove, and every staff route. A Lecturer who is not staff of the Class gets 403 on all of them.
- Staff routes (all `classes.manage`, owners only):
  - `GET /api/classes/{id}/staff`: `{lecturers:[{user_id,name,email}], assistants:[{user_id|null, invitation_id|null, name|null, email, status: active|invited|expired, last_valid_day|null}]}`. Pending rows are the newest unaccepted, unvoided `assistant` Invitation per address that is not staff yet. Each list is sorted by name, then email.
  - `POST /api/classes/{id}/staff/lecturers {email}`: an active User who holds the Lecturer account role (`authz.can(user, "classes.manage")`) becomes `owner`, or an Assistant of the Class is promoted to owner. One transaction: audit `class_staff.added` {class_id, user_id} {role} and `user:<id>`. Refusals answer 422 `invalid_request` `fields.email`. An address with no account, an inactive one, or one without the role all get `not_lecturer` (one reason, no account details). An existing owner gets `already_staff`. A malformed address gets an `address_problem` reason.
  - `POST /api/classes/{id}/staff/assistants {email}`: voids the open `assistant` Invitation for (class, address), then stores a new one, valid to the end of the 14th day (Europe/Oslo, `student_invitation_expiry`). The notice is `invitation` (`immediate`, `ref` = Invitation id, `user_id` null), with audit `class_staff.invited`. An address that is already staff of the Class gets 422 `already_staff`. A malformed address gets its reason. Answers 201 with the row.
  - `DELETE /api/classes/{id}/staff/{user_id}`: removes a staff row. Audit `class_staff.removed`, `user:<id>`, and the User's open `assistant` Invitations to the Class are voided. Removing the last owner answers 422 `last_owner`. A User who is not staff answers 404 `not_found`. The Class row is locked, so two removals cannot both pass the last-owner check.
  - `DELETE /api/classes/{id}/staff/invitations/{invitation_id}`: voids a pending `assistant` Invitation of this Class (audit `class_staff.invitation_voided`). If none is found it answers 404.
- Acceptance: `identity.register_acceptance_handler(kind, handler)`. For `assistant`, `ACCEPTED_KINDS` includes it. The new account gets no account role. `check_invitation` returns the Class label and the inviter. The mail context gets `class_name`, `last_valid_day`. Inside the acceptance transaction, `identity` calls the handler with (session, class_id, user_id, invitation_id, now). The `classes` handler inserts `assistant` staff (an existing owner row stays owner), writes audit `class_staff.joined`, and emits `user:<id>`. A missing Class makes the link invalid. `identity` imports no `classes` code.
- Revoke blocker (3.9): co-owned Classes count, because co-owners are owners. This needs no code change; a test proves it.
- Seed (local): `assistent@example.com` «Demo Assistent», no account role, Assistant of «class-of-1994». Add it to e2e `DEMO_USERS` (home `/laererhjem`).
- UI: the Class page shows a Lenke «Faglærere og assistenter» to `/klasser/{id}/faglaerere` for `can_manage`. The Assistant sees «Klasseliste» with the count, the invitation counts and the status list read-only, with no row actions, reminders or forms. The Lærerhjem hides «Ny Klasse» without the Lecturer role. The staff page has the headings «Faglærere» and «Assistenter», and each row has a status in text. «Legg til Faglærer» and «Inviter Assistent» open in-place forms, one at a time (`one-form.tsx`). «Assistenten får tilgang bare til denne Klassen.» stays visible beside the invite. Each «Fjern» states its consequence above its button. Errors clear as the user types, and result lines clear when a new action starts. Copy goes in `nb.ts`.

**Never:** storing `assistant` in `user_roles` or making it grantable by the Admin. Revealing whether an address has an account (the one reason `not_lecturer`). Archive (4.10). Assistant access to Student answers or AI assessments (later epics). Resetting demo accounts. Comparing DB time with host time, or ordering by timestamps in tests.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Add co-owner | email of a Lecturer | owner row; Class on their Lærerhjem; can manage | no account / no role → `not_lecturer` |
| Promote Assistant | email of the Class's Assistant who is a Lecturer | role becomes owner | owner already → `already_staff` |
| Invite Assistant | new address | `invited` with last valid day; mail with link | staff already → `already_staff` |
| Accept, new account | link, name, password | User, no account role; session roles `[assistant]`; lands on Lærerhjem; sees only this Class | removed/voided → `invitation_link_invalid` |
| Accept, existing User | link + password (e.g. a Student) | same User, assistant staff | – |
| Assistant on two Classes | staff of A only | A readable; B 403; manage routes 403 on A | – |
| Remove | co-owner or Assistant | access ends next request (403), audit, `user:<id>` | last owner → `last_owner` |
| Revoke Lecturer role | co-owner of an active Class | `role_revoke_blocked` | – |

</intent-contract>

## Code Map

- `backend/app/platform/authz.py` -- `ASSISTANT`, POLICIES, `CLASS_STAFF_ROLES`; the docstring explains the session role.
- `backend/migrations/versions/0031_class_staff_assistants.py` (new); `tests/test_migrations.py` HEAD 0031.
- `backend/app/modules/classes/{schemas,models,repo,service,routes,seed}.py`, `README.md` -- `StaffRole.assistant`; staff schemas; repo: staff rows, lock class, count owners, upsert staff, delete staff; service: `may_read`, staff commands, acceptance handler, session-role provider, `can_manage`; reads (registrations, summary) via `may_read`; routes switch those two to `classes.read`.
- `backend/app/modules/identity/{schemas,service,repo,seed,models}.py` -- `InvitationKind.assistant`, `SessionRole`, `UserOut.roles`; session-role and acceptance-handler registries; `active_user_for_email` (UserOut|None); `send_assistant_invitation`, `class_assistant_invitations`, `void_assistant_invitation(s)`, `people(ids)`; acceptance and check paths for `assistant`; mail context; demo user.
- `backend/app/platform/email/templates/kinds/invitation.{txt,html}.j2` -- `assistant` branch.
- Tests: new `backend/tests/classes/test_staff.py` (role × route matrix, forms, acceptance, scope across two Classes, last owner, revoke blocker, import check via `tests/test_imports.py`).
- Frontend: `modules/identity/homes.ts` (+test: assistant → Lærerhjem), `invitation.ts` (+test: assistant lead), `invitation-page.tsx`; `modules/classes/api.ts`, `class-page.tsx`, `lecturer-home.tsx`, `registration-status.tsx` and `invitation-summary.tsx` (`readOnly`), new `staff-page.tsx`, `staff.ts` (+test), `app/(app)/klasser/[classId]/faglaerere/page.tsx`; `one-form.tsx` area `staff`; `copy/nb.ts`; `lib/api/{openapi.json,schema.ts}`; `e2e/support/auth.ts` (assistant); new `e2e/class-staff.spec.ts`.

## Tasks & Acceptance

**Execution:**
- Backend: migration, authz, identity (registries, invitation kind, acceptance, mail), classes (staff service, routes, read-role changes, handler, provider, seed), templates, README.
- Backend tests: the matrix rows; a parametrised role × route test (owner, co-owner, assistant, other Lecturer) over every Class route; no address in logs.
- Frontend: staff page and forms, read-only Class page for the Assistant, homes, invitation lead, copy, regenerated api types.
- e2e `class-staff.spec.ts`: a fresh Lecturer adds the demo Lecturer as co-owner, invites an Assistant, the Assistant accepts from the mailbox link and sees the Class read-only, and the owner removes them. Axe at 320 px, 200 % text and 1440 px.

**Acceptance Criteria:**
- Given an owned Class, when «Faglærere og assistenter» opens, then Faglærere and Assistenter are listed, each with a status in text: «Aktiv», or «Invitert, gyldig til og med 3. desember», or «Invitasjonen er utløpt».
- Given «Legg til Faglærer» with an address without the role, then «Adressen tilhører ingen Faglærer. Be Admin gi personen Faglærer-rollen.» appears beside the field.
- Given «Inviter Assistent», then the row reads «Invitert …» and «Assistenten får tilgang bare til denne Klassen.» is shown.
- Given an Assistant logged in, then the Lærerhjem shows only their Classes, with no «Ny Klasse». The Class page shows the Roster without any action, and the manage routes answer 403.
- Given «Fjern» on the last Faglærer, then the refusal reason is shown and the Class keeps its owner.
- Given Playwright with axe at 320 px, 200 % text and 1440 px, then the staff page passes with no horizontal scroll.

## Spec Change Log

## Review Triage Log

### 2026-11-19 — Review pass
- verdicts: 38 findings — high 0, medium 2, low 21, false 15, maybe-false 0
- findings:
  - `[low]` `[patch]` (blind) `withdraw_assistant_invitation` did not take the Class lock that every other staff command takes. It now locks the Class row first.
  - `[low]` `[reject]` (blind) Other Faglærere's open staff pages are not told about changes live. The page reads again on each of its own actions and on reload; a Class-level event topic would be new surface for little gain.
  - `[false]` `[reject]` (blind) The validity line is wrong for an Assistant link. Refuted: `validityLine(days)` reads «gyldig i N dager» with N counted to the last valid day (`_student_days_left`). Only the Student start-date line is left out, and it should be.
  - `[low]` `[reject]` (blind) Inviting the address of a deactivated User mails a dead link. Refusing it would reveal account state to a Lecturer, which Story 4.8 ruled out. Acceptance refuses the link.
  - `[low]` `[reject]` (blind) A Student of the Class can be invited as its Assistant. The owner decides who assists, and the story sets no rule. Recorded as a decision.
  - `[false]` `[reject]` (blind) There is no index for the per-request role lookup. Refuted: `class_staff.user_id` is declared `index=True` (migration 0023).
  - `[low]` `[reject]` (blind) The Lecturer check goes through `authz.can(…, "classes.manage")`. This is the project rule: modules never compare roles (`test_authz_rules.py`). If that policy is ever widened, co-owner eligibility should follow it.
  - `[medium]` `[patch]` (blind) The promotion test did not test voiding. Split into `test_an_assistant_who_is_a_lecturer_is_promoted` (event, audit `previous_role`) and `test_a_lecturer_added_has_their_open_assistant_invitation_voided` (old link answers 410).
  - `[low]` `[reject]` (blind) There is no concurrency test for the last-owner rule. The Class row lock serialises removals, and a parallel-database test would be slow and flaky.
  - `[false]` `[reject]` (blind) `join_as_assistant` fails when the Class is missing. Refuted: Classes are never deleted (there is no route, and archive keeps the row). The Invitation row would cascade with its Class and is locked during acceptance, so this state cannot be reached.
  - `[low]` `[reject]` (blind) `_staff_refused` words only the last-owner case. That is the only command-level reason.
  - `[low]` `[reject]` (blind) There is no rate limit on Assistant Invitations. Only owners of the Class can send them, the same as Story 4.7's reminders.
  - `[low]` `[patch]` (blind) Withdrawing an expired Invitation said the link «slutter å virke». It now has its own line: «Den utløpte Invitasjonen til … fjernes fra lista.»
  - `[false]` `[reject]` (blind) `InvitationSummary` has actions an Assistant would see. Refuted: it shows counts and bounced addresses only.
  - `[false]` `[reject]` (blind) «Ny Klasse» flickers while `/me` loads. Refuted: `LecturerHome` renders inside `GuardedPage`, after `/me` has loaded.
  - `[false]` `[reject]` (blind) The downgrade leaves mail jobs for deleted Invitations. Refuted: the mail resolver answers None for a missing Invitation, so nothing is sent.
  - `[low]` `[patch]` (blind) The header comment of the txt template was not updated; fixed. The two identical consequence strings stay, because they are separate texts per role.
  - `[low]` `[patch]` (edge) When `useClass` failed with an error other than 403, the staff page kept loading. It now shows the failed state, and the retry reads both queries again.
  - `[false]` `[reject]` (edge) The staff list answers 403 while the Class is still pending. The reviewer itself marks this path as handled.
  - `[false]` `[reject]` (edge) The Class is gone in the acceptance handler. As blind row 10.
  - `[low]` `[reject]` (edge) The address of a deactivated User is invited. As blind row 4.
  - `[low]` `[reject]` (edge) A Student is invited as Assistant. As blind row 5.
  - `[low]` `[patch]` (edge) Withdrawal runs without the lock. The same fix as blind row 1.
  - `[false]` `[reject]` (edge) An `invited` row has no last day. Refuted: the api always sets `last_valid_day` for `invited` (`service.staff`, `invite_assistant`).
  - `[low]` `[patch]` (edge) Removing oneself flashed the access-denied page. It now invalidates only the Lærerhjem list and navigates away.
  - `[low]` `[reject]` (edge, claim) The e2e never adds the demo Lecturer as co-owner. Deliberate: demo accounts are never changed, so a second fresh Lecturer is used.
  - `[low]` `[patch]` (verification-gap) The login answer was not checked for the role `assistant`. Added `test_an_assistant_logging_in_gets_the_assistant_role`, and `homes.spec.ts` now lands the demo Assistant on the Lærerhjem at three viewports.
  - `[medium]` `[patch]` (verification-gap) Voiding on promotion was untested. As blind row 8.
  - `[low]` `[patch]` (verification-gap) Hiding the reminder button from read-only staff was untested. The demo-Assistant e2e now checks there is no «Send påminnelse …» and runs axe on the read-only Class page.
  - `[low]` `[patch]` (verification-gap, other) `TITLE.assistant` was never exercised. The landing loop in `homes.spec.ts` now runs for the Assistant: one Class link and no «Ny Klasse».
  - `[low]` `[reject]` (intent 1) Assistants read the Invitation counts and the registration status. The epic context says Assistants "see the Roster", and the status list is where the Roster is shown. Recorded as a decision.
  - `[low]` `[reject]` (intent 2) The Lærerhjem landing is done through a session role. The UX outcome needs a mechanism, and this is it. Recorded as a decision.
  - `[low]` `[reject]` (intent 3) The scope sentence is standing text rather than a line after the send. It is shown beside the form before and after the send, and the mail repeats it.
  - `[low]` `[patch]` (intent 4) Hiding in the UI was only partly asserted. Covered by verification-gap row 3.
  - `[false]` `[reject]` (intent 5) The registry is only partly kind-agnostic. It has the shape of the revoke-blocker registry, as the AC asks; `CLASS_KINDS` only marks which kinds carry a Class label. `test_imports.py` proves that `identity` imports no `classes` code.
  - `[low]` `[reject]` (intent 6) Deactivated accounts fall under `not_lecturer`. They must, so that no account details are revealed.
  - `[low]` `[patch]` (intent 7) The Assistant's read-only Class page had no axe check. Added to the demo-Assistant e2e; the Lærerhjem is checked with axe at three viewports in `homes.spec.ts`.
  - `[false]` `[reject]` (intent 8) No test shows the Lærerhjem updating live. The `user:<id>` emits are tested at the api; the live rendering is the existing event plumbing from Epic 3.

## Design Notes

- Co-owner = `owner` row. The epic context names three roles, but "co-owners have exactly the owner's rights" and "a Class always keeps at least one owner" are simplest and safest if there is one owner role. The creator is just the first owner and can be removed when another owner remains.
- The `assistant` session role is derived on every request (from `class_staff`), so a removal takes effect at the next request with no stored role to drift. The PRD calls it an account role "for that Class only". Deriving it keeps it Class-bound.
- The staff list is owner-only. The Assistant's view is the Roster and the counts.

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/classes/test_staff.py tests/test_migrations.py tests/test_authz_rules.py tests/test_imports.py -q` -- pass.
- `cd backend && uv run pytest -q && uv run ruff check . && uv run ruff format --check .` -- pass.
- `cd frontend && npm run typecheck && npm test && npm run check:copy && npm run lint:colours && npm run build` -- pass.
- `cd frontend && npx playwright test` against the rebuilt stack with `worker-batch` -- pass.

## Auto Run Result

Status: done

**Summary.** A Class can now be shared with more Faglærere and with Assistant lecturers.

- **Co-owners.** «Legg til Faglærer» makes an active User with the Lecturer role an extra `owner`, so a co-owner has exactly the creator's rights. An Assistant who is also a Lecturer is promoted the same way. Every other address gets one reason, `not_lecturer` («Be Admin gi personen Faglærer-rollen»), with no account details.
- **Assistant Invitations.** «Inviter Assistent» creates an Invitation of the new kind `assistant`. It is valid to the end of the 14th day (Europe/Oslo) and is mailed as the `immediate` `invitation` kind, addressed by Invitation id.
- **Accepting.** The Assistant accepts through «Du er invitert» with a new or an existing account. `identity`'s new acceptance-handler registry calls `classes.join_as_assistant` inside the acceptance transaction.
- **The `assistant` role.** It is a session role, read from `class_staff` on every request and never stored or granted. It lands the Assistant on the Lærerhjem, which shows only their Classes. They can read the Class, its Invitation counts and its status list. Every other Class route answers them 403.
- **«Faglærere og assistenter».** The page is at `/klasser/{id}/faglaerere`, for owners only. It lists both groups with a status in text («Aktiv», «Invitert, gyldig til og med …», «Invitasjonen er utløpt»). It holds the two in-place forms, one open at a time, and «Fjern» with its consequence above the button. «Fjern» either removes a person or withdraws an Invitation.
- **Rules on every change.** Removing the last owner is refused with `last_owner`. Every staff change takes the Class row lock, writes an audit row (`class_staff.*`, ids only) and emits `user:<id>`.

**Process note.** The caller required the implementation to be done in this context rather than by an implementation subagent. The four review layers ran as subagents, and their reports were read from their transcripts.

**Files changed**

Backend:
- `backend/migrations/versions/0031_class_staff_assistants.py` (new): the staff role `assistant`, the Invitation kind `assistant`, and at most one open Assistant Invitation per Class and address.
- `platform/authz.py`: the session role `assistant`, the read policies, and `CLASS_STAFF_ROLES`.
- `identity/{schemas,models,repo,service,seed}.py`: `SessionRole` in `UserOut.roles`; the session-role and acceptance-handler registries; sending, listing, voiding and accepting Assistant Invitations, and their mail context; the demo Assistant.
- `classes/{schemas,repo,service,routes,seed}.py`, `README.md`: `can_manage`; `may_read` for registrations and counts; the five staff routes; the handler and the role provider; attaching the demo Assistant.
- `email/templates/kinds/invitation.{txt,html}.j2`: an `assistant` branch.

Tests:
- `tests/classes/test_staff.py` (new, 24): includes a role × route matrix over every Class route for six roles.
- `tests/test_migrations.py`: head 0031 and its downgrade.
- `tests/identity/test_seed.py`: five demo Users.

Frontend and docs:
- New: `classes/staff-page.tsx`, `staff.ts` (+ test), `app/(app)/klasser/[classId]/faglaerere/page.tsx`.
- Changed: `class-page.tsx`, `lecturer-home.tsx`, `registration-status.tsx` (`readOnly`), `api.ts`; `identity/homes.ts`, `invitation.ts`, `invitation-page.tsx` (+ tests); `copy/nb.ts`; `lib/api/{openapi.json,schema.ts}`.
- e2e: `class-staff.spec.ts` (new), `support/{auth,classes}.ts`, `homes.spec.ts`.
- The root `README.md` lists the demo Assistant.

**Review findings.** 38 findings: 2 medium (one root cause), 21 low, 15 false.
- **Patched:** the medium (voiding on promotion was untested), plus 9 low:
  - the withdrawal lock;
  - the copy for withdrawing an expired Invitation;
  - a template comment;
  - the staff page stuck loading when the Class read fails;
  - the access-denied flash on removing oneself;
  - a test of the role in the login answer;
  - Assistant landing in `homes.spec.ts`;
  - the reminder button hidden from an Assistant;
  - axe on the read-only Class page.
- **Deferred:** none.
- **Rejected:** the rest, each with its reason in the Review Triage Log.

**Follow-up review recommended: false.** One medium entry was patched (a test gap) and nothing high was found.

**Verification**
- Backend: ruff is clean. The full pytest run passed 2250 tests in 88 s before review. After the patches, the classes, identity, authz-rules and imports suites passed 470.
- Test speed: the first case of the role × route matrix takes about 1.5 s with setup, as the first Class fixture of the session. The other cases take about 0.95 s each, and no other new test takes over 0.9 s.
- Frontend: typecheck, `npm test` (367), `check:copy`, `lint:colours` and the build all pass.
- Playwright: the full run passed 160 of 160 before review. After the patches the full run passed 161 of 163. The two failures were `admin-status` resend width and `roster-upload` at 320 px. This story does not touch either of them, and the run started seconds after the stack restarted. Both passed on a rerun together with the touched specs (47 of 47).
- Shared test databases: migration 0031 was added and migrated once, and not changed after it ran.
- Screenshots at 390 and 1280 px were checked by eye: the staff page, its form, the Assistant's Class page and the Assistant's Lærerhjem.

**Decisions taken in place of the founder**
- A co-owner is an `owner` row, with no separate role. The creator can be removed once another owner exists.
- The Lecturer-revoke blocker counts co-owned Classes.
- «Legg til Faglærer» on an Assistant of the Class who has the Lecturer role promotes them, and their open Assistant Invitations are voided.
- The session role `assistant` is derived on every request, not stored in `user_roles`. A removal therefore takes effect at the next request. An Assistant with no account role lands on the Lærerhjem.
- Assistants read the Class, its Roster status list and the Invitation counts, all read-only. The staff list is for owners only.
- One refusal, `not_lecturer`, covers no account, a deactivated account and an account without the role.
- An Assistant Invitation is valid to the last day in Europe/Oslo, 14 days, and this is not configurable. Inviting again voids the old link. An expired Invitation stays listed as «Invitasjonen er utløpt» until it is withdrawn or sent again.
- The address of a deactivated User can be invited, so no account state is revealed. A Student of the Class may also be invited as its Assistant.
- Demo account: `assistent@example.com` («Demo Assistent», password `olspillet-demo`, no account role), Assistant of «class-of-1994».
- All copy in `nb.ts → classes.staff` is marked [ASSUMPTION]. The exceptions are the title, «Legg til Faglærer», «Inviter Assistent» and the scope sentence, which come from the UX spine. The Assistant lines on «Du er invitert» and the mail's `assistant` branch are [ASSUMPTION] too.

**Residual risks**
- The open staff pages of other owners update only on their own actions or a reload. There is no Class-level live event.
- Every request now makes one more query: the indexed `class_staff` lookup for the session role.
- `UserOut.roles` changed from `AccountRole` to `SessionRole`. The regenerated client handles this, but any other consumer of `/api/auth/me` must accept `assistant`.
