---
title: 'Story 12.8: Invite test students who consent before they take part'
type: 'feature'
created: '2026-11-23'
status: 'done'
baseline_revision: '6f1a7898101e1b1c2b673d4e82583eb86aa97fe1'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-12-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** A Control test (Story 12.7) has no notion of test students: anyone can be put on its Roster, nobody is asked for consent, and nothing stops a person from being given a Seat or from showing up in an ordinary Class (FR-82, AD-13, AD-27).

**Approach:** `users.is_test_student` is set when a User is created from a Control test Roster (Invitation or manual registration); a Control test Roster takes only such Users and an ordinary Roster takes none of them, so a test student is never a Student of an ordinary Class. On Hjem a test student reads what the Control test is for and who the data controller is, and consents or declines; each decision is a row (User, time, text version). Allocation of a `control_test` Class session refuses while any registered Student lacks consent, and every automatic seating path leaves them out.

## Boundaries & Constraints

**Always:**
- Migration `0207` (Revises `0206`): `users.is_test_student` (bool, default false); table `test_student_consents` (id uuid7 pk, `user_id` FK users cascade, `decision` check `given|declined`, `text_version` text, `decided_at` timestamptz; index on `user_id`). Written and read only through `identity.service`.
- The mark: a User created by `accept_invitation_new` for a Student Invitation of a Control test Class, or by `register_manually` on one, gets `is_test_student = true`; nothing else sets or clears it. `identity` learns the Class kind through `ClassLabel.control_test` (resolver in `classes.service.label_of_class`).
- Roster rule (both ways, one reason per Class kind): on a Control test Roster an address of an existing User without the mark is refused `not_test_student`; on an ordinary Roster an address of a marked User is refused `test_student`. Applies to staged upload/paste evaluation (invalid row, so «Send N» leaves it out), the send itself, «Legg til adresse», «Registrer manuelt», and an Invitation link whose address now belongs to a User of the other kind (link unusable, as a removed entry's).
- Consent: `GET /api/me/test-student-consent` → `{decision: given|declined|null, text_version, decided_at}` (403 for a non-test-student); `PUT` same path `{decision, text_version}`: `text_version` must equal `identity.service.CONSENT_TEXT_VERSION` (else 409 `consent_text_changed`); `declined` after `given` is refused 409 `consent_given`; repeating the current decision writes nothing. Each change emits `user:<id>`. `UserOut.is_test_student` tells the web app.
- Allocation (kind `control_test` only): `POST .../allocation` (open/draw), `.../redraw` and `.../confirm` refuse with 409 `consent_missing`, `fields {"allocation": "consent_missing", "missing": "<N>"}` while N registered Students have no `given` decision; nothing stored. `AllocationOut.consent_missing` (int, 0 for a course) lets the block say it before opening. The lock's random allocation, the Student-choice draw at the lock, late-registrant seating (finder and command) and «Ta setet» leave a test student without consent unseated (take_seat: 409 `consent_missing`).
- `identity.service.test_students(session, user_ids) -> set[UUID]` (the `reports.scope.register_test_students` signature of Story 13.1) and `consented_users(session, user_ids)`.
- UI: «Status etter utsending» rows of a test student carry «Teststudent» and the consent state («Samtykket», «Takket nei», «Ikke svart»); a Control test Class page says only test students can be on its Klasseliste. Hjem shows the consent block first for a test student: purpose, «Operatøren av ØL-spillet er behandlingsansvarlig», «Jeg samtykker» (primary) and «Nei takk»; declined shows its line and «Jeg samtykker likevel»; given shows one line with the date. Allocation block shows the missing count and the 409 in words. All new copy in `nb.ts` marked `[ASSUMPTION]` and listed for founder review.

**Never:** withdrawing consent after it is given, or removing a seated test student (open point); scorers and human scores (12.9); `reports.scope` itself (Epic 13); an Admin command to set or clear the mark; changes to the demo Class or seeds; edits of `sprint-status.yaml`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| New address on Control test | paste, send, accept link | User created with mark; row «Teststudent», «Ikke svart» | — |
| Existing ordinary User | address on Control test Roster | staged row invalid; add/manual refused | 422 `invalid_request`, `fields.email = not_test_student` |
| Test student on ordinary Class | address of marked User | staged row invalid; add/manual refused | `fields.email = test_student` |
| Link of the other kind | address got a User of the other kind after the send | link unusable | `invitation_link_invalid` |
| Consent | PUT given, current version | row stored, `user:<id>` | stale version: 409 `consent_text_changed` |
| Decline then consent | PUT declined, then given | two rows; latest wins | given then declined: 409 `consent_given` |
| Non test student | GET/PUT consent | — | 403 |
| Allocation | 2 of 3 consented, open/confirm | nothing stored | 409 `consent_missing`, `missing: "1"` |
| Course session | any consent state | unchanged allocation | — |
| Lock / late seat | no consent | Student stays without a Seat | — |

</intent-contract>

## Code Map

- `backend/app/modules/identity/models.py` -- `users` (~23), add column and `test_student_consents`.
- `backend/app/modules/identity/repo.py` -- `insert_user`, `user_by_email`, `class_roster_facts` (~971: add `test_student`, latest consent via `users` join on `roster_entries.user_id`), new mismatch read `users_of_kind(addresses, mark)`, consent insert/latest.
- `backend/app/modules/identity/service.py` -- `ClassLabel` (~1893), `_usable_invitation` (~604), `accept_invitation_new` (~733), `accept_invitation_existing` (~814), `evaluate_roster_rows`/`_roster_upload_out`/`_staged_out`/`stage_*`/`send_roster_invitations` (~1622–2034: pass a `refused: Mapping[str, str]`), `add_roster_entry` (~2275), `register_manually` (~2317), `RosterFacts` (~2120), `_user_out` (~98); new consent API, `test_students`, `consented_users`, `CONSENT_TEXT_VERSION`.
- `backend/app/modules/identity/{schemas,routes}.py` -- `UserOut.is_test_student`, `RosterInvalidRow.reason` (+`not_test_student`, `test_student`), consent schemas and `/api/me/test-student-consent` routes.
- `backend/app/modules/classes/{repo,service,schemas}.py` -- `class_label` adds `_control_test`; `label_of_class`; `RegistrationOut.test_student`/`consent`; `_status`.
- `backend/app/modules/sessions/{service,schemas,routes}.py` -- `draw_allocation` (~3839), `confirm_allocation` (~3934), `_allocate_at_lock` (~4696), `_draw_at_lock` (~5603), `late_registrants` (~5021), `seat_late_registrant` (~5084), `take_seat` (~5762), `_allocation_out`/`_out_for` (`consent_missing`), new `ConsentMissing(_FieldsError)`; routes `_draw` (~909), confirm, take_seat.
- `backend/migrations/versions/0207_test_students.py`; `backend/tests/test_migrations.py` (HEAD).
- Tests: new `backend/tests/sessions/test_test_students.py` reusing `tests/sessions/test_control_test.py` fixtures (`people`, `control`, `mark`, `create`), `tests/classes/test_student_registration.py` (`accept`, `check`), `tests/classes/test_roster_send.py` (`send`, `staged_id`).
- Frontend: `src/modules/identity/{api.ts,test-student-consent.tsx (new)}`, `src/modules/games/student-hjem.tsx`, `src/modules/classes/{registration-status.tsx,roster.ts,roster-entry.ts,class-page.tsx}`, `src/modules/sessions/{allocation-panel.tsx,allocation.ts}`, `src/copy/nb.ts`, generated `src/lib/api/{openapi.json,schema.ts}`.
- E2E: new `frontend/e2e/test-student.spec.ts` (helpers `e2e/support/{auth,classes}.ts`, invitation mail as in `e2e/student-registration.spec.ts`).

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0207_test_students.py` -- column and table -- storage.
- `backend/app/modules/identity/*` -- mark on creation, roster rule, link rule, consent API, reads for Epic 13 -- AC 1, 2, 5.
- `backend/app/modules/classes/*` -- label kind, registration rows -- AC 1.
- `backend/app/modules/sessions/*` -- consent gate on allocation and seating -- AC 3, 4.
- `backend/tests/sessions/test_test_students.py` -- every matrix row; exclusion from an ordinary Lecturer's/Assistant's/Student's lists; Control test Class game purpose `class` and its own budget row; migrations test head.
- Frontend files above, `npm run api:generate` -- screens -- AC 1, 2, 6.
- `frontend/e2e/test-student.spec.ts` -- test student list, consent accepted and declined, at 320/360/1440 with axe.

**Acceptance Criteria:**
- Given a test student registered on a Control test, when an ordinary Lecturer, Assistant lecturer or Student opens any list, overview or allocation, then the test student is not in it, and their address cannot be put on an ordinary Roster (api tests).
- Given the screens, when Playwright runs at 320, 360 and 1440 px, then the «Teststudent» list and the consent block, accepted and declined, pass axe.

## Spec Change Log

## Review Triage Log

### 2026-11-23 — Review pass
Layers: blind hunter, edge-case hunter, verification gap, intent alignment (four sonnet reviewers, per the runbook's rule for consent and personal data). The implementation ran in the builder's own context (the brief's rule), so patches were applied directly.
- verdicts: 32 findings — high 0, medium 3, low 18, false 6, maybe-false 5
- findings:
  - `[low]` `[reject]` Blind: Users registered on a Control test before 0207 are unmarked and block the allocation forever — only local data from Story 12.7 testing can be in that state (12.7 is unreleased); a backfill could mark an ordinary demo Student, which is worse; the Admin removes such an address from the Klasseliste.
  - `[low]` `[reject]` Blind: a test student can be granted a role or invited as Assistant elsewhere — the operator's own test persons; no AC asks, and guarding every role path is new surface. Noted under residual risks.
  - `[false]` `[reject]` Blind: a decliner blocks the allocation like a non-answer — the AC refuses a User without a consent record; a decline is no consent, and the Fordeling line tells the Admin to take decliners off the Klasseliste. The lock leaving them out is the AC's «declining leaves them unallocated».
  - `[medium]` `[patch]` Blind: the ordinary-Roster reason `test_student` tells any Lecturer that an address belongs to a Control test participant — the ordinary side now answers `address_unavailable` («Adressen kan ikke brukes i denne Klassen»), naming no Control test; tests updated.
  - `[low]` `[patch]` Blind: `CONSENT_TEXT_VERSION` and `nb.homes.consent.version` are hand-synced — a backend test now reads `nb.ts` and asserts they agree.
  - `[maybe-false]` `[reject]` Blind: the consent text lacks retention, rights and withdrawal wording, and given consent cannot be withdrawn — the AC asks for purpose, data controller and one button; the copy is [ASSUMPTION] draft for the founder's review, and withdrawal is listed as an open decision.
  - `[low]` `[reject]` Blind: consent rows cascade with the User and are not audited — the decision row is the record the AC asks for (User, time, version); deletion with the User follows the personal-data rule of the other identity tables.
  - `[low]` `[reject]` Blind: the Admin's Klasseliste and Fordeling do not refresh live on a decision — the Klasseliste has no live topic for ordinary registrations either; both read on open.
  - `[low]` `[patch]` Blind: a stale tab's 409 `consent_given` reads the generic line and keeps the old state — mapped to «Du har allerede samtykket.», and the consent is read again on any failure.
  - `[low]` `[patch]` Blind: `take_seat` and the Student-choice draw have no consent test — same root as the verification gap below; test added.
  - `[low]` `[reject]` Blind: repeated label reads, `_refuse_other_kind` naming, extra read on Control test allocation reads, `is_test_student` on `/me` — a few cheap reads on rare paths; ruff and format pass.
  - `[medium]` `[patch]` Edge: same as the Blind leak row — patched as above.
  - `[maybe-false]` `[reject]` Edge: pre-0207 unmarked Students on a Control test — same as the Blind row; rejected for the same reason.
  - `[medium]` `[patch]` Edge: `draw_allocation` answered `consent_missing` where the session was locked or the allocation confirmed — the consent check now runs after those refusals (confirm already checked the lock first).
  - `[low]` `[reject]` Edge: the registered Students are read before the row lock — the pattern of Stories 5.8/5.9; a Student who registers in that instant is not in the draft and is gated again on the late-seating path.
  - `[low]` `[reject]` Edge: role or staff invitations to a test student — same as the Blind row.
  - `[low]` `[patch]` Edge: a failed consent read showed nothing on Hjem — the block now shows «Samtykket kunne ikke hentes.» with «Prøv igjen».
  - `[false]` `[reject]` Edge: `consentRefusal` reads NaN as 0 — both refusals always send `missing` as a count (routes and tests).
  - `[maybe-false]` `[reject]` Edge: skewed api clocks could order a later decision first — decisions of one User are serialised under the User row lock; would need clocks skewed between two clicks of one person.
  - `[maybe-false]` `[reject]` Edge: a very large staging could exceed the bind-parameter limit — `ROSTER_MAX_ROWS` is 5000, far below it.
  - `[low]` `[patch]` Verification: Student choice on a Control test (`take_seat`, `_draw_at_lock`) is untested — new test: 409 `consent_missing` on «Ta setet», and the lock draws no Seat for the non-consenting test student.
  - `[low]` `[reject]` Verification (other): the exclusion test passes by structure — that is the design (Design Notes); the Roster rule that makes it true is tested both ways.
  - `[low]` `[reject]` Verification (other): the re-check of `_same_kind` under the lock is not exercised alone — a race guard for a change between check and accept; the unlocked check is tested.
  - `[false]` `[reject]` Verification (other): the Hjem and Fordeling behaviour is e2e-only — the Playwright spec ran and passed at three widths with axe (Verification).
  - `[low]` `[reject]` Intent: AC4 (the lifecycle after allocation) is barely asserted — no step changes for a Control test; the test asserts Class games of purpose `class` and the session's own budget row, and Story 12.2 asserts the assessment's calls run on the Class session's budget scope.
  - `[low]` `[reject]` Intent: AC5 is proved by structure — as above.
  - `[low]` `[reject]` Intent: most backend tests seed state by SQL — the invitation and registration paths are tested through HTTP; seeding keeps the consent and seating tests fast.
  - `[low]` `[reject]` Intent: Roster refusal copy and allocation refusals are not clicked in e2e — the api tests pin codes and Vitest the wording.
  - `[false]` `[reject]` Intent: decliners block preview/confirm — the AC's own rule (see the Blind row).
  - `[false]` `[reject]` Intent: scope beyond the AC (other seating paths, inverse Roster rule) — needed for «consent before a Seat» and «no test student appears» to hold.
  - `[false]` `[reject]` Intent: no founder-review list in the diff — the list is in the Auto Run Result and the report.
  - `[maybe-false]` `[reject]` Intent: a test student with no Class may not reach the consent block — such a User has nothing to consent to; the e2e shows the block for a registered test student.

## Design Notes

- Refusing test students on ordinary Rosters (and ordinary Users on Control test Rosters) keeps the invariant "a test student is a Student of Control test Classes only", so every existing list leaves them out with no per-list filter; `reports.scope` (Epic 13) still filters by `test_students` as a second guard.
- Consent is per User, not per Control test: the text names the Control test purpose generally and carries a version; a new text version asks again (the latest `given` must match `CONSENT_TEXT_VERSION` to count).

## Verification

**Commands:**
- `uv run pytest tests/sessions/test_test_students.py tests/sessions/test_control_test.py tests/classes tests/test_migrations.py tests/test_imports.py` -- pass
- `npm run typecheck && npm run test && npm run lint:colours && npm run check:copy && npm run build` -- pass
- `npx playwright test e2e/test-student.spec.ts e2e/control-test.spec.ts e2e/homes.spec.ts --workers=4` -- pass

## Auto Run Result

Status: done

**Summary.** A User created from a Control test's Roster (accepted Invitation or «Registrer manuelt») carries `users.is_test_student` (migration 0207). A Control test Roster refuses an address of an existing User without the mark (`not_test_student`); an ordinary Roster refuses a test student with a neutral reason (`address_unavailable`). The rule covers staging, the send, «Legg til adresse», «Registrer manuelt» and an Invitation link whose address became a User of the other kind. «Status etter utsending» labels each test student «Teststudent» with their consent («Samtykket», «Takket nei», «Ikke svart ennå»). On Hjem a test student reads the purpose, what is stored and that the operator of ØL-spillet is the data controller, then «Jeg samtykker» or «Nei takk»; a decline offers «Jeg samtykker likevel». Each decision is a row in `test_student_consents` (User, decision, text version, time) through `GET/PUT /api/me/test-student-consent`. A Control test's allocation (open, redraw, confirm) answers 409 `consent_missing` with the count while any registered Student lacks consent, and «Fordeling» says how many. The lock's allocation, the Student-choice draw, late seating and «Ta setet» leave them unseated. For Epic 13, `identity.service.test_students(session, user_ids)` matches `reports.scope.register_test_students`; `is_test_student` and `consented_users` are there too.

**Files.**
- `backend/migrations/versions/0207_test_students.py` (new): the mark and the consent table.
- `backend/app/modules/identity/{models,repo,service,schemas,routes}.py`: the mark on creation, the Roster rule, the link rule, the consent API, the Epic 13 reads, `UserOut.is_test_student`.
- `backend/app/modules/classes/{repo,service,schemas}.py`, `README.md`: `ClassLabel.control_test`, `RegistrationOut.test_student` and `consent`.
- `backend/app/modules/sessions/{service,repo,schemas,routes}.py`, `README.md`: `ConsentMissing`, `_without_consent` and `_seatable` on every seating path, `AllocationOut.consent_missing`.
- `backend/app/main.py`, `backend/app/platform/events/registry.py`: the `/api/me` router, the `identity.decide_consent` topic.
- `backend/tests/sessions/test_test_students.py` (new); `tests/test_migrations.py`, `tests/identity/test_login.py`, `tests/sessions/test_allocation{,_confirm}.py` (new fields).
- `frontend/src/modules/identity/{test-student-consent.tsx,test-student-consent.test.ts}` (new), `identity/api.ts`, `games/student-hjem.tsx`, `classes/{registration.ts,registration-status.tsx,registration.test.ts,class-page.tsx}`, `sessions/{allocation.ts,allocation-panel.tsx,allocation.test.ts}`, `copy/nb.ts`, `lib/api/{openapi.json,schema.ts}` (generated).
- `frontend/e2e/test-student.spec.ts` (new), `e2e/class-session-allocation.spec.ts` (fixture field).

**Review.** 32 findings from four sonnet reviewers. Patched: 2 medium entries (the ordinary-Roster reason named the Control test; the draw's consent refusal masked `session_locked` and `allocation_confirmed`) and 4 low entries (5 rows): a version-sync test, `consent_given` worded with a re-read, an error line for a failed consent read, and a Student-choice consent test (two rows). Deferred: none. Rejected: 13 low, 6 false and 5 maybe-false, each with its reason in the triage log.

**Follow-up review: recommended.** Two medium entries were patched (entries: high 0, medium 2, low 4). The unverified risk is the consent text and its legal sufficiency: it has no retention period, no rights and no withdrawal path, and consent once given cannot be withdrawn in the product. The founder must decide this before any real test student consents.

**Verification.**
- Backend: full suite with `--maxprocesses=8`: 3835 passed, 4 skipped, before the review patches. After them: 3837 passed, 4 skipped. `ruff` is clean. The new tests' slowest call is 0.69 s, so no new test is over 1 s.
- Frontend: `tsc` clean, Vitest 1191 passed, `lint:colours` and `check:copy` pass, `next build` ok.
- Playwright on the lane-3 stack (8082) after the patches: `test-student` (Klasseliste, Fordeling line, consent declined then given, axe at 320/360/1440), `control-test`, `homes`, `student-home`, `class-session-allocation`, `registration-status`, `roster-entries`, `roster-upload`, `game-start`, `order-field`, `student-choice`: 101 passed.

**Decisions taken in place of the founder.**
1. The Roster rule runs both ways: a test student is never a Student of an ordinary Class, so every existing list leaves them out by construction. The ordinary side gives a neutral reason.
2. Consent is per User and per text version. A new version asks again.
3. Consent once given cannot be withdrawn in the product (409 `consent_given`). A decline can become consent.
4. A decliner blocks a Control test's preview and confirm until taken off the Klasseliste (AC: refuse Users without consent). The lock and late seating skip them instead.
5. Student choice and late seating are gated too.
6. All new copy is [ASSUMPTION] draft for founder review: the consent block (purpose, data, controller, Seat line, buttons, decided lines), the two Roster reasons, «Samtykket»/«Takket nei»/«Ikke svart ennå», the Fordeling count line and the Klasseliste note.

**Residual risks.**
- A test student can still be granted an account role or invited as Assistant to an ordinary Class (not guarded).
- Staff pages show consent changes on their next read, not live.
- Personal data: the new table `test_student_consents` (`user_id`, the User's decision) and the new column `users.is_test_student` belong in the 15.2 registry.
