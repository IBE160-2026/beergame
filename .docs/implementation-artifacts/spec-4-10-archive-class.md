---
title: 'Story 4.10: Archive a Class'
type: 'feature'
created: '2026-11-19'
status: 'done'
baseline_revision: '97266fb359e7de1b9089264db961e3b8366417df'
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

**Problem:** A Lecturer cannot put away a Class they no longer teach. `classes.archived_at` exists (4.1) but nothing sets it, and nothing stops changes to an archived Class: its Student Invitations can still be accepted, and Students still see it (carried over from 4.5).

**Approach:** An owner archives the Class from its page, after reading the consequence above the button. One transaction sets `archived_at`, voids the open Invitations, drops the staged upload, writes an audit row and emits `user:<id>` to the staff. From then on one check in `classes.service` refuses every mutating Class route with 409 `class_archived`. Reads stay open to staff. `is_writable(class_id)` is exposed for Epic 5.

## Boundaries & Constraints

**Always:**
- Route: `POST /api/classes/{id}/archive` (policy `classes.manage`, owners only). Answers 200 with the `ClassOut` (`archived: true`). A second archive answers 409 `class_archived`.
- Archive transaction: the Class row is locked `FOR UPDATE`. Every open Invitation of the Class (kinds `student` and `assistant`, not accepted, not voided) is voided. The staged upload is deleted under the staging lock. Audit `class.archived` with targets {class_id} and change {voided_invitations: n}. `user:<id>` is emitted for every staff row.
- One check: `classes.service` raises `ClassArchived` from one function. `main.py` maps it to 409 `class_archived`. Order of answers: 403 when the User may not manage (non-staff, Assistant, Student, non-existent), then 409 when archived, then the route's own 404/422. An archived Class is never revealed to someone who may not manage it.
- Inside each mutating transaction that already exists (send, reminders, add, manual, remove, the staff commands), the Class row is read `FOR SHARE` (or `FOR UPDATE` where it is locked already) and checked, so an archive cannot interleave with a mutation. The staging routes (upload, paste, column, discard) are checked before they run.
- `is_writable(class_id, session=None) -> bool`: False for archived or missing. With a session it reads under `FOR SHARE`.
- Route matrix on an archived Class (role × route test, parametrised per role: owner, co-owner, assistant, lecturer_assistant, outsider, student):
  - Reads (GET class, list, registrations, invitations): 200 for owners and Assistants, 403 otherwise.
  - Owner-only reads (GET roster-upload → `upload: null`, GET staff): 200 for owners, 403 otherwise.
  - Every mutation (roster-upload POST/PUT/DELETE, roster-paste, send invitations, reminders, entries add/manual/remove, staff lecturers/assistants/remove/withdraw, archive): 409 `class_archived` for owners, 403 otherwise.
  - Students: `/api/classes/enrolled` leaves archived Classes out, and `/api/classes/enrolled/{id}` answers 403.
- Acceptance: a Student or Assistant link to an archived Class is unusable (`check` 410, accept `invitation_link_invalid`), so «Du er invitert» shows the expired-link state and no one joins. `ClassLabel` gains `archived`, which `identity` reads through the existing resolver (no `classes` import). Asking for a new Invitation from such a link marks nothing.
- Revoke blocker: counts non-archived owned Classes, co-owned included. Tests: only archived owned Classes → the revoke goes through; one archived plus one co-owned active → blocked with 1.
- `ClassListItem` gains `archived`. Lærerhjem: «Klassene dine» lists active Classes; archived ones follow under «Arkiverte Klasser», each marked «Arkivert» in text.
- Class page, owner, active Class: «Arkiver Klassen» opens an in-place panel (one form at a time, area `archive`). The consequence stands above the primary button. Cancel returns focus to the opener. After archiving, the page reads again and focus goes to the archived notice.
- Class page, archived Class: a notice «Klassen er arkivert …» under the facts; the Roster, counts and status list are read-only (as for an Assistant). The staff Lenke stays for owners, and the staff page is read-only (no forms, no «Fjern»).
- A `class_archived` answer to any action in the web app shows «Klassen er arkivert og kan ikke endres.» and reads the Class again (shared in `useAction` and the query client), so a stale page becomes read-only.
- Copy in `nb.ts` → `classes.archive`, marked [ASSUMPTION].

**Never:** un-archiving; deleting the Class or its data (retention is Epic 15); a migration (the column exists); emitting events to Students; refusing the manual-registration set-password link (it is account-level, not Class membership); archiving the demo Class in tests; comparing DB time with host time or ordering by timestamps in tests.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Archive | owner, active Class with open Invitations and a staging | `archived_at` set; Invitations voided; staging gone; audit; `user:<id>` per staff | second archive → 409 `class_archived` |
| Archive by Assistant / outsider | – | 403 `forbidden` | – |
| Mutation after archive | owner, any mutating route | 409 `class_archived`, nothing changes | – |
| Follow old link | Student or Assistant link of archived Class | check 410; accept `invitation_link_invalid`; no Roster/staff change | renewal marks nothing |
| Student reads | Student of archived Class | not on Hjem list; enrolled detail 403 | – |
| Revoke | Lecturer owning only archived Classes | revoke goes through | active co-owned → `role_revoke_blocked` |

</intent-contract>

## Code Map

- `backend/app/modules/classes/service.py` -- `may_manage` (l.166) used by every mutation; add `ClassArchived`, `_refuse_archived`, `manageable`, `_hold_writable`, `is_writable`, `archive_class`; `label_of_class` passes `archived`; `list_classes` sets `archived`; staff commands use `repo.lock_class` (make it return the row's `archived_at`).
- `backend/app/modules/classes/repo.py` -- `lock_class` (l.141), new `class_state(s, id, share)`, `set_archived`, `_enrolled` (l.102) filters `archived_at IS NULL`, `class_label` selects `archived_at`; `count_owned_active` (l.77) unchanged.
- `backend/app/modules/classes/routes.py` -- new archive route; `upload_roster` and the malformed-id branches call `service.manageable`.
- `backend/app/modules/classes/schemas.py` -- `ClassListItem.archived`.
- `backend/app/main.py` -- exception handler for `ClassArchived` → 409.
- `backend/app/modules/identity/service.py` -- `ClassLabel.archived` (l.1727); `_usable_invitation` (l.589) refuses archived; `request_invitation_renewal` (l.810) skips archived; new `void_class_invitations`, `discard_class_staging`.
- `backend/app/modules/identity/repo.py` -- new `void_class_invitations` beside `void_assistant_invitations` (l.1124); `lock_roster_staging`, `delete_roster_upload` reused.
- `backend/app/modules/classes/README.md` -- archive section.
- Tests: new `backend/tests/classes/test_archive.py` (reuse `class_routes`, `shared`, `EMAIL`, `ROLES` from `test_staff.py`).
- Frontend: `modules/classes/{class-page,lecturer-home,staff-page,one-form,api}.tsx/ts`, new `archive-panel.tsx`, `lib/api/mutation.ts` (shared message), `app/providers.tsx` (MutationCache invalidation), `copy/nb.ts`, regenerated `lib/api/{openapi.json,schema.ts}`, new `e2e/class-archive.spec.ts`.

## Tasks & Acceptance

**Execution:**
- Backend service/repo/routes/main/identity changes as above; README.
- `backend/tests/classes/test_archive.py` -- archive transaction (audit, emits, voided, staging), role × route × archived matrix, acceptance and renewal of old links, Student reads, revoke blocker, `is_writable`, logs carry ids only.
- Frontend: archive panel, archived page state, Lærerhjem grouping, read-only staff page, shared `class_archived` handling, copy, regenerated types; unit test for Lærerhjem grouping helper.
- e2e `class-archive.spec.ts`: a fresh Lecturer archives a fresh Class with one sent Invitation; the page turns read-only; the Lærerhjem shows it under «Arkiverte Klasser»; the mailed link shows the expired-link state. Axe at 320 and 1440 px on the archived Class page and the Lærerhjem.

**Acceptance Criteria:**
- Given an owned active Class, when the owner opens «Arkiver Klassen», then the consequence (read-only, kept until the retention period ends, open Invitations stop working) stands above the button.
- Given the owner presses it, then the Class is archived, an audit row `class.archived` is written and `user:<id>` is emitted for each staff member.
- Given an archived Class, then its page shows no Roster change, no Invitation, no staff change, and every mutating route answers 409 `class_archived` for owners.
- Given archived and active Classes, then the Lærerhjem lists active ones under «Klassene dine» and archived ones under «Arkiverte Klasser», marked «Arkivert».
- Given Playwright with axe at 320 and 1440 px, then the archived Class page and the Lærerhjem pass with no horizontal scroll.

## Spec Change Log

## Review Triage Log

### 2026-11-19 — Review pass
- verdicts: 36 findings — high 0, medium 3, low 20, false 13, maybe-false 0
- findings:
  - `[false]` `[reject]` (blind) `join_as_assistant` ignores the lock result, so an Assistant could join an archived Class. Refuted: acceptance locks the Invitation row first. An archive that commits earlier has voided it (`_locked_open_invitation` refuses). An archive that starts later waits on that row lock until the acceptance commits. Classes are never deleted, so `GONE` cannot happen.
  - `[false]` `[reject]` (blind) Student acceptance takes no Class lock, so a Student can join during an archive. Refuted: the archive's voiding UPDATE waits on the Invitation lock the acceptance holds. The Student is then registered just before the archive, which is a consistent order, never into an archived Class.
  - `[low]` `[reject]` (blind) Lock order: the archive takes Class then Invitation; an Assistant acceptance takes Invitation then Class, so the two can deadlock. Real but rare: it needs an Assistant accepting in the same instant the Class is archived. Postgres aborts one transaction cleanly (500, retry works). The fix would rework lock order across two modules. Recorded as a residual risk.
  - `[false]` `[reject]` (blind) Queued mails still go out after the archive. Refuted: `invitation_mail_recipient` answers None for a voided Invitation, so `worker-batch` sends nothing.
  - `[low]` `[reject]` (blind) A staging upload racing the archive can land on the archived Class. The window is milliseconds wide. The staging is never sent (send holds the share lock and refuses) and expires within 24 h. Holding the lock inside `identity`'s staging transactions would spread the check into `identity`. Documented in the README.
  - `[false]` `[reject]` (blind) The revoke-blocker filter is missing from the diff. Refuted: `repo.count_owned_active` already filters `archived_at IS NULL`, and `test_the_revoke_blocker_counts_active_owned_and_co_owned_classes_only` passes.
  - `[low]` `[patch]` (blind) The README's error order ignores FastAPI body validation (422 first). The README now says so.
  - `[low]` `[reject]` (blind) The archive could commit and then answer 403 if `get_class` misses. That needs another owner to remove the archiver within the same instant. Unlikely, and the fix adds a second response builder.
  - `[low]` `[reject]` (blind) `can_manage` stays true on an archived Class. Deliberate: it states the staff role's authority; `archived` sits beside it, and the schema docstring says changes are refused whatever it says.
  - `[false]` `[reject]` (blind) The `["classes"]` prefix invalidation may miss keys. Refuted: every Class query key in `api.ts` starts with `"classes"`.
  - `[low]` `[patch]` (blind) After a `class_archived` refusal the form vanished and focus was lost. The Class page now moves focus to the archived notice whenever the Class turns archived while open, whether by its own archive or by a refusal. Covered by the new e2e «a page left open turns read-only…».
  - `[low]` `[patch]` (blind) The notice carried `role="status"` and was also focused, so it could be announced twice. The role is removed; focus alone announces it.
  - `[low]` `[reject]` (blind) The archive panel has no Escape key. No in-place panel in the project has one (4.8, 4.9); «Avbryt» is the way out, as elsewhere.
  - `[medium]` `[patch]` (blind) Race tests are missing for the in-transaction check. Grouped with verification-gap row 1: the race test is now parametrised over all nine routes that hold the Class row.
  - `[false]` `[reject]` (blind) The e2e regex is built from unescaped copy. Refuted: «Fjern» has no regex metacharacters.
  - `[false]` `[reject]` (blind) Class names can collide across parallel workers. Refuted: each test uses its own fresh Lecturer, and names are looked up only on that Lecturer's pages.
  - `[false]` `[reject]` (blind) The separate import block in `classes.test.ts` breaks the import-order lint. Refuted: the project has no import-order lint; typecheck and Vitest pass.
  - `[low]` `[reject]` (edge) The same deadlock as blind row 3.
  - `[false]` `[reject]` (edge) The ignored `class_state` result. As blind row 1.
  - `[false]` `[reject]` (edge) A Student registered during the archive. As blind row 2.
  - `[low]` `[reject]` (edge) The archive commits, then answers 403. As blind row 8.
  - `[low]` `[reject]` (edge) No `user:<id>` for enrolled Students. The AC names the staff; a Student's Hjem reads the list again on its next load.
  - `[false]` `[reject]` (edge) `_class_archived` treats a gone Class as archived, so renewal is skipped. Refuted: Classes are never deleted, and an Invitation row cascades with its Class, so `invitation_by_hash` would find nothing first.
  - `[low]` `[patch]` (edge) The staff page's «Fjern» panel stayed open when the Class turned archived. `StaffLists` now closes any open form when `readOnly` turns true.
  - `[low]` `[patch]` (edge) The staff page's add/invite form state survived `readOnly`. The same fix as the row above.
  - `[low]` `[patch]` (edge) The status list's reminder and row panels stayed open when `readOnly` flipped. `StatusView` now closes them when `readOnly` turns true.
  - `[low]` `[reject]` (edge, claim) The staging routes are checked only before they run. As blind row 5.
  - `[medium]` `[patch]` (verification-gap) The in-transaction check was tested on one route only. `test_a_change_under_way_when_the_class_is_archived_is_refused` now covers invitations, reminders, entries add/remove, manual, staff lecturers/assistants/remove/withdraw. It asserts 409 and an unchanged row footprint. Removing `_hold` from any of them now fails (404/201 instead of 409).
  - `[medium]` `[patch]` (verification-gap) The query client's reload after `class_archived` was untested. New e2e: a page left open, the Class archived through the api, then «Legg til»; the notice gets focus and the forms are gone.
  - `[false]` `[reject]` (verification-gap, other) Renewal is skipped for a deleted Class. As edge row 6.
  - `[low]` `[reject]` (intent) The consequence shows in a panel after the opener is pressed, not on the page at once. This is the pattern of 4.8's and 4.9's «Fjern» («states its consequence above its button»). An irreversible action gets a confirm step. Recorded as a decision.
  - `[low]` `[reject]` (intent) `class_archived` goes only to those who may manage; others get 403. FR-5: a refusal never reveals a Class's state to non-staff. Recorded as a decision.
  - `[low]` `[reject]` (intent) The staging routes lack the in-transaction check. As blind row 5.
  - `[low]` `[reject]` (intent) The Invitation side is not in the role matrix. Acceptance routes are public and token-based, so roles do not apply. Both kinds of link are tested on an archived Class. The manual-registration set-password link runs unchanged code and is decided to stay usable.
  - `[low]` `[reject]` (intent) There is no e2e of the Student's view. Hjem renders the api list unchanged, and the api test pins that the archived Class is left out.
  - `[false]` `[reject]` (intent) The revoke is tested only at service level. Refuted: the Admin HTTP route for an owner with only archived Classes is covered by `tests/classes/test_classes.py::test_revoking_the_lecturer_role_of_an_owner_is_blocked_with_the_count`.

## Design Notes

- 409 for `class_archived`: the request is valid but conflicts with the Class's state; 403 stays reserved for permission so archive state never leaks to non-staff.
- Voiding at archive rather than only refusing at acceptance makes the status list honest (no «Invitert, gyldig til …» on a read-only Class) and stops queued mails (the mail resolver skips voided Invitations).
- Students lose sight of an archived Class: nothing in it is open to them in Epic 4. Epic 5+ may widen this for finished Class sessions.

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/classes/test_archive.py -q` -- pass, each test under 1 s.
- `cd backend && uv run pytest -q && uv run ruff check . && uv run ruff format --check .` -- pass.
- `cd frontend && npm run typecheck && npm test && npm run check:copy && npm run lint:colours && npm run build` -- pass.
- `cd frontend && npx playwright test` against the rebuilt stack with `worker-batch` -- pass.

## Auto Run Result

Status: done

**Summary.** A Faglærer can archive a Class they own, and an archived Class is read-only on every route.

- **Archiving.** «Arkiver Klassen» is the last item on an active Class's page. It opens an in-place panel, one form at a time, with the consequence above «Arkiver nå». `POST /api/classes/{id}/archive` runs one transaction holding the Class row lock. It sets `archived_at` and voids every open Invitation (Student and Assistant; expired ones stay, so the count of expired ones holds). It deletes the staged upload, writes the audit row `class.archived` with ids and a count, and emits `user:<id>` to every staff member.
- **One check.** Every mutation passes `manageable` and, inside its own transaction, `_hold`. Both end in `_refuse_archived`, which raises `ClassArchived`, and `main.py` answers 409 `class_archived`. The order is 403 first (non-staff never learn the state), then 409, then 404/422. `is_writable(class_id, session=None)` is exposed for Epic 5.
- **What an archived Class allows** (carried item 1). Owners and Assistants keep every read: the Class, the list, registrations and counts. Owners also keep the staff list and `GET roster-upload`, which answers `null`. Every mutation answers 409 to owners and 403 to everyone else. Students no longer see the Class: `/enrolled` leaves it out and `/enrolled/{id}` answers 403. Student and Assistant links show the expired-link state, no one joins, and a renewal request marks nothing.
- **Revoke blocker** (carried item 2). It counts active Classes the Lecturer owns or co-owns. Archived ones never block. No code change was needed; a test covers it.
- **UI.**
  - The Lærerhjem lists «Arkiverte Klasser» under its own heading, each marked «Arkivert · N adresser på Klasselista». When nothing is active it says «Ingen aktive Klasser.».
  - The archived Class page shows a notice. Its Roster, counts and status list are read-only for owners too.
  - The staff page is read-only, with no forms and no «Fjern».
  - A `class_archived` refusal anywhere shows «Klassen er arkivert og kan ikke endres.» and reads the Class again. The page then turns read-only and focus moves to the notice.

**Process note.** The caller required the implementation to be done in this context rather than by an implementation subagent. The four review layers ran as subagents, and their reports were read from their transcripts.

**Files changed**
- Backend:
  - `classes/{service,repo,routes,schemas}.py`: `ClassArchived`, `manageable`, `_hold`, `is_writable`, `archive_class`; `class_state`/`set_archived`; the archive route; `ClassListItem.archived`; archived Classes left out of the Student scope.
  - `classes/README.md`: an archive section.
  - `identity/{service,repo}.py`: `ClassLabel.archived`, which makes links unusable and skips renewals; `close_class` and `void_class_invitations`.
  - `main.py`: the 409 handler.
- Tests: `backend/tests/classes/test_archive.py` (new, 22 tests), `frontend/src/modules/classes/classes.test.ts` (+2), `frontend/e2e/class-archive.spec.ts` (new, 4 tests).
- Frontend:
  - New: `modules/classes/archive-class.tsx`.
  - Changed: `class-page.tsx`, `lecturer-home.tsx`, `staff-page.tsx`, `registration-status.tsx`, `one-form.tsx` (area `archive`), `classes.ts` (`splitArchived`), `api.ts` (`archiveClass`).
  - Shared and generated: `lib/api/mutation.ts` (`SHARED_MESSAGES`), `app/providers.tsx` (reads again on `class_archived`), `copy/nb.ts` (`classes.archive`, [ASSUMPTION]), regenerated `lib/api/{openapi.json,schema.ts}`.

**Review findings.** 36 findings: 0 high, 3 medium, 20 low, 13 false.
- **Patched (9 rows):** the 3 medium rows (race tests over all nine in-transaction routes; an e2e for a page left open), plus 6 low:
  - the README error order;
  - focus to the notice when the Class turns archived;
  - no double announcement;
  - stale forms closed on the staff page and the status list.
- **Deferred:** none.
- **Rejected:** the rest, each with its reason in the Review Triage Log.

**Follow-up review recommended: true.** Two medium entries were patched. The named unverified risk is the lock order between an Assistant acceptance (Invitation, then Class) and the archive (Class, then Invitation). It can deadlock in a same-instant race, and no test covers it.

**Verification**
- Backend: ruff is clean. The full pytest run passed 2270 (4 skipped) in 101 s.
- Over 1 s: `test_archiving_closes_the_class_in_one_transaction_and_tells_its_staff` takes about 1.5 s (two sends, an Assistant invite, a staging and the archive). Every other new test is under 1.05 s including setup.
- Frontend: typecheck, `npm test` (369), `check:copy`, `lint:colours` and the build all pass.
- Playwright: the full run passed 167 of 167 on the rebuilt stack with `worker-batch`. Before the review patches, one run had one failure, `logg-inn.spec.ts:234` (not touched), which passed on a rerun.
- Screenshots at 390 and 1280 px were checked by eye: the archive panel, the archived Class page and the Lærerhjem with both headings.
- Migrations: none added or changed.

**Decisions taken in place of the founder**
- 409 `class_archived` goes only to those who may manage the Class. Everyone else keeps 403, so the archived state is never revealed. A second archive also answers 409. There is no un-archive.
- Open Invitations (Student and Assistant) are voided at archive. Expired ones are left alone, so they still count as expired. The staged upload is deleted.
- Archived Classes stay readable to owners and Assistants, including the staff list and the Invitation counts. The Assistant session role stays.
- Students no longer see an archived Class (Hjem, and `/enrolled/{id}` 403). It gets no events to Students. Epic 5+ may widen this for finished Class sessions.
- A manual-registration set-password link still works after the archive, because it belongs to the account. A renewal request from an archived Class's link marks nothing.
- The staging routes are checked before they run only (a millisecond race window, documented).
- The consequence stands in an in-place panel above «Arkiver nå», as with 4.8 and 4.9 «Fjern». The opener is «Arkiver Klassen».
- `can_manage` keeps its staff-role meaning, and the UI combines it with `archived`.
- All `classes.archive` copy is [ASSUMPTION].

**Residual risks**
- The deadlock described above: rare, and the aborted transaction leaves no partial state.
- A staging written during the archive's instant stays until it expires (24 h). It can never be sent.
