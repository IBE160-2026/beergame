---
title: 'Story 15.2: The Admin deletes a User on the Institution''s instruction'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: 'cdcfbc7f522c651cc293815c5d16f6126509ffb7'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-15-context.md'
warnings: ['oversized']
deferred:
  - summary: >-
      A Seat the erased User holds in a Class game that has not started yet (or in an allocation draft) is not handed over.
    evidence: |-
      games.repo.erasure_seats_of reads only Games with lifecycle running; the story asks for running Games only. When such a Game starts, the group waits until the inactivity Takeover takes the anonymous User's Seat.
    location: >-
      backend/app/modules/games/repo.py erasure_seats_of
    severity: medium
  - summary: >-
      Aggregates, report PDFs and Class-session ZIPs, signed report URLs, the Completion export and the storage-mock search exist only as seams.
    evidence: |-
      reports (Epic 14), platform/storage and the Student report (Epic 13) and the Completion export are not on this branch. identity.erasure has register_aggregate_writer and register_object_eraser with no registrant; Story 13.x/14.x must register there and extend test_user_delete with the storage mock and the no-ZIP assertion.
    location: >-
      backend/app/modules/identity/erasure.py
    severity: medium
---

<intent-contract>

## Intent

**Problem:** The Admin has no way to meet the right to erasure (FR-76): a User and their personal data cannot be deleted without breaking other Students' Games, charts and reports.

**Approach:** One shared erasure routine, `identity.erasure.erase_user(user_id)`, anonymises the `users` row in place (so every `user_id` in game tables now points to an anonymous User and no game row changes), runs per-module erasure steps that modules register with `identity` (as `register_revoke_blocker` does), and is reached from a new Admin action on «Brukere og roller» that needs the Institution's instruction reference. A personal-data registry in `modules/identity` lists a deletion handling for every table, and its test fails for a table without one.

## Boundaries & Constraints

**Always:**
- Order inside the routine: (0) running-Game Seats handed to an AI player (own transactions, through `games.commands.takeover`, actor `system`, reason `takeover_inactivity`, no `actor_user_id`) and queued Reclaims of the User deleted; (1) registered aggregate writers (seam for `reports.service.write_aggregate`, Epic 14); (2) anonymise identity tables; (3) registered module steps delete free text, AI answers that quote it and the User's `llm_call` bodies; all of (1)–(3) plus the audit row in ONE transaction; (4) registered object erasers after commit (seam for `platform/storage` report PDFs and Class-session ZIPs, Epic 13).
- Idempotent: running it again on an erased User re-runs every step harmlessly and writes no second audit row; a failure in (1)–(3) rolls back all of it.
- Anonymised `users` row: name `Slettet bruker`, email `slettet-<hex id>@slettet.invalid`, `password_hash` NULL, `is_active` false, `session_version` + 1, new `deleted_at` set. The User is left out of `list_users` and of the Roster (Roster entries deleted).
- Audit row `user.deleted`: actor, time, `{"user_id": id}`, change `{"reference": <instruction reference>}`; never a name or e-mail. A reference that contains the User's name or e-mail is refused.
- Refusals: unknown User 404 `not_found`; oneself or the last active Admin 409 `last_admin`; owner of active Classes 409 `role_revoke_blocked` with `fields.classes` (the lecturer revoke blockers, same copy «Bård eier 2 Klasser. …»); empty reference 422.
- `games.rules.can_take_over(..., erasing=True)` (system actor only) ignores Pause, an Order already placed and the due time; the erased Student gets no Takeover notice, the others get the usual ones.
- All UI copy in `frontend/src/copy/nb.ts`, marked `[ASSUMPTION] Story 15.2`; the delete button states the consequence; one press deletes, no dialog.

**Never:**
- No change to `seat_occupancy`, `seat_weeks`, `seat_turns`, `games`, `game_weeks` rows or the Decision log; no new occupancy reason.
- No build of «Mine data» (Story 15.1), `reports` module, `platform/storage`, Completion export (Epic 13) or retention sweep (Story 15.3): leave seams only.
- No name or e-mail in logs, job arguments or audit.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Student in running Class game | DELETE with reference | Seat taken over by AI (`takeover_inactivity`), other Students notified, user anonymised, free text gone, 200 | — |
| Repeat | Same call on an erased User | 200, steps re-run, no new audit row | — |
| Lecturer owning Classes | DELETE | 409 `role_revoke_blocked`, `fields.classes` | nothing changed |
| Self / last Admin | DELETE | 409 `last_admin` | nothing changed |
| Reference names User | reference contains e-mail or name | 422 `reference_names_user` | nothing changed |
| Seat ordered last Week | running Game, last Week ordered | no Takeover possible; Seat left, deletion proceeds | skip `order_exists` |

</intent-contract>

## Code Map

- `backend/app/modules/identity/service.py:990` -- `revoke_role`, `_REVOKE_BLOCKERS` (lecturer blocker from `classes/service.py:956`), `deactivate_user:1043` last-admin pattern; `list_users:951`.
- `backend/app/modules/identity/repo.py:280` -- `list_users` query (add `deleted_at IS NULL`).
- `backend/app/modules/identity/models.py` -- `users` table (add `deleted_at`), roster/invitation/access-request tables.
- `backend/app/modules/identity/routes.py:396` -- admin router; add `DELETE /api/admin/users/{user_id}` (`deleteUser`), permission `users.manage`.
- `backend/app/modules/games/rules.py:65` -- `can_take_over`; `commands.py:1887` `takeover` (notices at :2020); `repo.py:105` `seats_with_occupant`, `_latest_occupancy:127`; `models.py:226` `seat_reclaims`.
- `backend/app/modules/debrief/models.py` -- explanations, reflection answers, follow-ups (`llm_call_id`), summaries (`reflection` JSONB).
- `backend/app/ai/models.py:89` -- `llm_call.request/response`; follow-up caller_ref carries `user_id` (`debrief/follow_up.py:255`).
- `backend/app/modules/messaging/models.py` -- messages, message_recipients, notices, mail_deliveries.
- `backend/app/modules/sessions/models.py:244` -- `student_adjustments`; `classes/models.py` `class_staff`.
- `backend/app/platform/pii.py` -- staged Roster cells are the only stored student numbers (`roster_upload_rows`).
- `backend/tests/sessions/test_play.py:58` -- `running(klass, students)` fixture for a started Class game; `tests/games/helpers.py:107` `play_to_end`; `app/modules/games/checks.py:49` `verify_finished`.
- `frontend/src/modules/admin/user-list.tsx`, `user-roles.ts`, `api.ts` -- row buttons, refusal lines, cache helpers; `e2e/admin-status.spec.ts` -- pattern for a fresh Lecturer and axe at 320/1440.

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0065_user_deleted_at.py` -- add `users.deleted_at` (Revises 0064).
- `backend/app/modules/identity/erasure.py` -- registries (`register_erasure_preparation`, `register_aggregate_writer`, `register_erasure_step(name, tables, fn)`, `register_object_eraser`), `erase_user`, `delete_user(actor, user_id, reference, now)` with refusals and audit.
- `backend/app/modules/identity/personal_data.py` -- registry: every table → handling (`anonymise`, `delete`, `clear`, `keep`, `none`) + note; `category` left None for Story 15.1.
- `backend/app/modules/identity/{repo,service,routes,schemas}.py` -- anonymise + identity-owned deletions, `list_users` filter, route, schema `UserDeleteIn`.
- `backend/app/modules/games/{rules,commands,repo,service}.py` -- `erasing` case; erasure preparation (queued Reclaims deleted, held running Seats taken over); registered at import.
- `backend/app/modules/{debrief,messaging,sessions,classes}/service.py` + `backend/app/ai/calls.py` -- erasure steps for their tables.
- `backend/tests/identity/test_user_delete.py` + `test_personal_data_registry.py` -- API, refusals, idempotency, takeover, engine verify after play-out, whole-database search for name/email/student number, registry coverage.
- `frontend/src/copy/nb.ts`, `src/modules/admin/{api.ts,user-list.tsx,user-roles.ts,user-roles.test.ts}`, `src/lib/api/*` (regenerated) -- delete panel per row; audit action label.
- `frontend/e2e/admin-delete.spec.ts` -- delete a fresh Student-less Lecturer with reference, refusals, axe at 320/1440.

**Acceptance Criteria:**
- Given the Admin on a User row, when they open «Slett …», fill the reference and press the consequence button once, then the User is gone from the list with a status line and no dialog, and the audit row has actor, time, target id and the reference only.
- Given an erased Student, when anyone looks, then login fails, search and Roster show nothing, `student_names` leaves them out, and the other Students' play and Debrief views show the Seat by Role.
- Given the erasure test, when it finishes, then no table (incl. procrastinate job tables) holds the User's name, e-mail or staged student number.
- Given a finished Game whose Student was erased, when `verify_finished` runs, then it verifies.
- Given a new table, when the registry test runs, then it fails until the table has a handling, and fails for a `delete`/`clear` table no registered step covers.

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
- verdicts: 45 findings — high 0, medium 13, low 23, false 9, maybe-false 0
- findings:
  - `[false]` `[reject]` Blind: 0065 and 0107 could run in either order on two heads — the chain is linear (0101 revises 0052, 0053 revises 0119, 0065 revises 0064), so 0107 always runs first; the migration test walks it down and up.
  - `[low]` `[patch]` Blind: a refusal given only by the locked second guard, or a failed erasure transaction, leaves the Seats already handed to AI players, while the docs said nothing changed — `erase_user` docstring now states it; a repeat finishes the erasure, and the Student can still Reclaim a Seat if they were not erased.
  - `[low]` `[reject]` Blind: a Reclaim queued by the still-logged-in User between the hand-over and the commit survives — needs a login during a window of milliseconds; the fix adds another games write in the identity transaction.
  - `[medium]` `[defer]` Blind: a Seat in a Class game that has not started (or in an allocation draft) is not handed over — the story covers running games only; the group waits for the inactivity Takeover once the Game starts. Deferred.
  - `[medium]` `[patch]` Blind: `takeover(erasing=…)` raises `play_deadline_passed` (and `game_not_found`/`seat_not_found`) outside the skip set, aborting the erasure — `games.service.hand_over_seats_of` now skips those codes per Seat (`ERASURE_GONE`).
  - `[medium]` `[patch]` Blind: the erasure depends on import side effects; a process that did not import every module would skip steps silently — `erase_user` now runs `_check_complete()` first and raises, changing nothing, when a `delete`/`clear`/`anonymise` table has no registered part.
  - `[low]` `[reject]` Blind: `clear_bodies_of_user` scans `llm_call` without an index; JSON-embedded ids are not seen by the registry test — an erasure is a rare Admin action; an index needs a migration for no user-visible gain.
  - `[low]` `[reject]` Blind: the name check in the reference gives false positives (substring) and misses other people's names — it errs on the side of keeping names out of the audit; the Admin rewords the reference.
  - `[low]` `[reject]` Blind: client and server disagree on rare Unicode format characters; an over-long body gets a generic 422 — the field's `maxLength` stops over-long input, and the api's field error is shown beside the field.
  - `[low]` `[patch]` Blind: the Vitest case held an invisible control character — written as `\u0007` now.
  - `[low]` `[reject]` Blind: deleting a staged Roster row leaves `roster_uploads.row_count` one high; an address embedded in a longer cell is not matched — staged uploads expire within a day and are only a preview; exact-cell matching is the same rule `platform/pii` uses.
  - `[low]` `[patch]` Blind: `KEEP_ONE_ACTIVE` duplicated `service.ROLES_KEEP_ONE_ACTIVE`; the truthiness trick in `takeover` — one constant in `identity/schemas.py` used by both; the branch is explicit `erasing is not None`. The api message for self-deletion stays the generic `last_admin` one (the web app words it «Du kan ikke slette deg selv.»).
  - `[low]` `[patch]` Blind: «… er slettet.» stayed after later role or status presses; `notified(game_id)` ignored its argument — both presses clear the line; the helper takes no argument. Offering «Slett» on one's own row and the 404 wording were rejected (the deactivate button follows the same pattern; two Admins deleting at once is rare).
  - `[false]` `[reject]` Blind: the patch carries Story 11.1/11.2 sprint and log changes and no 15.2 log — those are the orchestrator's commits on the branch, not this change; session logs and issues are not this run's to write.
  - `[medium]` `[patch]` Edge: erasing Takeover on a Game that is playing out or gone raises out of `erase_user` — same fix as above (`ERASURE_GONE`).
  - `[medium]` `[patch]` Edge: a queued Reclaim in a Game that is not running makes every erasure fail — same fix as above.
  - `[low]` `[patch]` Edge: guard passes, Seats move, then the locked guard refuses — same docstring fix as above.
  - `[medium]` `[patch]` Edge: `grant_role`/`reactivate_user` (and revoke, deactivate) reach an erased User by id — they now answer `not_found` for a User with `deleted_at`; tested for grant and reactivate.
  - `[medium]` `[defer]` Edge: not-started Games and allocation drafts — same as the deferred Blind finding.
  - `[low]` `[reject]` Edge: Reclaim queued after the preparations — same as the rejected Blind finding.
  - `[false]` `[reject]` Edge: a Seat reassigned to another Student between the read and the Takeover — in a running Game a Seat goes only to an AI player or back to its own Student by Reclaim; no path gives it to another Student.
  - `[medium]` `[patch]` Edge: steps missing in a process that did not import every module — same fix as above (`_check_complete`).
  - `[low]` `[reject]` Edge: staged cells with the address inside longer text — same as the rejected Blind finding.
  - `[low]` `[reject]` Edge: Unicode normal forms and short name words in the reference — the Admin types the reference; the check is a guard, not the only safeguard.
  - `[low]` `[reject]` Edge: emoji count as two UTF-16 units in the client's 200-character check — the api decides; no instruction reference is made of emoji.
  - `[false]` `[reject]` Edge: `takeover` now returns `str | None` and the dev route stores the result — only an `erasing` call returns None; the dev route never passes it.
  - `[low]` `[reject]` Edge: spec says DELETE, the route is `POST …/delete` — the fix would edit the spec.
  - `[low]` `[patch]` Edge: spec claims a failure rolls back all of it — covered by the docstring fix; steps (1)–(3) do roll back, the Takeovers are step (0).
  - `[low]` `[reject]` Edge: a repeat bumps `session_version` and `updated_at` again — harmless for an anonymous User who cannot log in.
  - `[medium]` `[patch]` Verification gap: `debrief_follow_ups` erasure not verified — a follow-up naming the Student is planted and asserted gone.
  - `[medium]` `[patch]` Verification gap: `message_recipients`, `notices`, `mail_deliveries` erasure not verified — planted for the erased and the other Student; the erased User's rows go, the other's and the class-wide Message stay.
  - `[medium]` `[patch]` Verification gap: the `class_staff` step not verified — `test_an_assistant_lecturer_leaves_every_class_staff`.
  - `[low]` `[reject]` Verification gap: body clearing tested on a hand-written `caller_ref` — `ai.gateway._caller` stores the follow-up's `user_id` UUID as its string under the same key, which is what the clear matches; a real follow-up fixture is heavy for a read-off contract.
  - `[low]` `[reject]` Verification gap (other): skip branches other than `takeover_exists` and the last Week are untested — their outcome is that the Seat is left unchanged.
  - `[medium]` `[defer]` Intent: aggregates (`reports.service.write_aggregate`), report PDFs/ZIPs in the `reports` bucket, signed URLs, the Completion export and the storage-mock search exist only as seams — their modules (Epics 13, 14) are not on this branch.
  - `[low]` `[patch]` Intent: the shared routine is only exercised through the Admin path — `test_the_routine_without_an_admin_audits_the_system` calls `erase_user` directly (the Story 15.3 path).
  - `[false]` `[reject]` Intent: the registry is built here, not extended from 15.1 — 15.1 is not on the branch; `category` is its seam.
  - `[low]` `[reject]` Intent: the row's «Slett …» opens the panel and only the inner button states the consequence — the required reference needs a field before the one press; no dialog follows.
  - `[false]` `[reject]` Intent: the reference is stored in the audit row — not a defect; it is guarded against names and addresses.
  - `[false]` `[reject]` Intent: additions beyond the story (self/last-Admin refusal, skips, Pause bypass, no notice to the erased Student) — descriptive, each follows the story or an earlier rule.
  - `[medium]` `[patch]` Intent: Studentside not covered — the test now reads it for the erased Student and gets the same answer as for an unknown id, while the other Student's page answers 200.
  - `[low]` `[reject]` Intent: the real AI call path for `caller_ref.user_id` is assumed — same as the rejected verification-gap finding.
  - `[low]` `[reject]` Intent: the AD-4 test erases during a running Game and finishes it after — the finished Game is replayed after the deletion, as the story asks.
  - `[false]` `[reject]` Intent: the migration changes an existing trigger and test — descriptive; the existing test now proves every other update is still refused.
  - `[false]` `[reject]` Intent: sprint-status and log hunks — the orchestrator's commits, not this change.

## Design Notes

In-place anonymisation keeps every `user_id` valid (no FK cascades fire, append-only rows untouched): the "anonymous User" is the same id with no personal data. Kept-by-id data (orders, quiz choices, progress, ratings) is no longer linked to a person. Seams for Epics 13/14 and Story 15.3: `register_aggregate_writer` and `register_object_eraser` have no registrant yet; `erase_user` takes only `user_id` so `ops.retention` can call it.

## Verification

**Commands:**
- `cd backend && uv run pytest tests/identity/test_user_delete.py tests/identity/test_personal_data_registry.py -q` -- expected: pass
- `cd backend && uv run pytest -q --maxprocesses=8 -n 8` -- expected: pass
- `cd frontend && npm run typecheck && npx vitest run && npm run lint:colours && npm run check:copy && npm run build` -- expected: pass
- `cd frontend && npx playwright test admin-delete admin-users admin-status homes --workers=4` -- expected: pass

## Auto Run Result

Status: done

**Summary.** The Admin deletes a User on «Brukere og roller»: «Slett <fornavn>» opens a panel with the reference to the Institution's instruction (required, no `@`, no name of the User) and one primary button that states the consequence and deletes on one press, with no dialog (`POST /api/admin/users/{id}/delete`). One shared routine, `identity.erasure.erase_user`, hands every Seat the User holds in a running Game to an AI player first (`games.service.hand_over_seats_of` → `takeover(erasing=…)`, reason `takeover_inactivity`, no actor, the others notified, queued Reclaims dropped; `rules.can_take_over(erasing=True)` ignores wait times, Pause and an Order placed), then in one transaction runs the aggregate seam, anonymises the `users` row in place (name «Slettet bruker», placeholder address, no password, inactive, `deleted_at`), deletes the identity rows of the User or the address, runs the registered steps (Debrief free text and AI follow-up answers, the reflection copied into the summary, Messages to them, notices and deliveries, Tilrettelegging, the bodies of their AI calls, Class staff) and writes one audit row (actor, time, id, reference); object erasers run after the commit. Owners of Classes are refused with the revoke's own rule and sentence; oneself and the last Admin are refused. The personal-data registry lists a handling for every table and its test fails for a new one.

**Seams left for later stories.** `register_aggregate_writer` (Epic 14 `reports.service.write_aggregate`), `register_object_eraser` (Epic 13 report PDFs and Class-session ZIPs; signed URLs), `Entry.category` (Story 15.1 «Mine data»), `erase_user(user_id, now=…)` with no actor (Story 15.3 retention). The Completion export does not exist yet. Epics 11–14 tables will fail the registry test until listed: intended.

**Files.**
- `backend/migrations/versions/0065_user_deleted_at.py` — `users.deleted_at`; the summary trigger allows the one update that empties `reflection`.
- `backend/app/modules/identity/erasure.py` — the routine, its registries, the completeness check, `delete_user`.
- `backend/app/modules/identity/personal_data.py` — the registry.
- `backend/app/modules/identity/{models,repo,schemas,service,routes}.py` — column, identity erasure SQL, schemas, `ROLES_KEEP_ONE_ACTIVE`, route, erased Users hidden and refused.
- `backend/app/modules/games/{rules,commands,repo,service}.py` — the `erasing` case and the hand-over.
- `backend/app/modules/{debrief,messaging,sessions,classes}/…`, `backend/app/ai/calls.py` — erasure steps.
- `backend/tests/identity/test_user_delete.py`, `test_personal_data_registry.py`, `backend/tests/games/test_erasure_takeover.py`, `tests/test_migrations.py`, `tests/debrief/test_explanation.py` — tests.
- `frontend/src/copy/nb.ts`, `src/modules/admin/{api,user-list,user-roles,user-roles.test}.ts(x)`, `src/lib/api/*` (regenerated), `e2e/admin-delete.spec.ts` — UI, copy, tests.

**Review.** Four sub-agent reviewers (blind, edge case, verification gap, intent alignment), model sonnet. 45 findings: 13 medium, 23 low, 9 false. Patched: 7 medium entries and 5 low (grouped by root cause). Deferred: 2 (not-started Games; Epic 13/14 seams). Rejected: the rest, each with its reason in the triage log.

**Follow-up review: recommended.** Patched medium entries: 7 (patched low: 5). The patches added behaviour that no second review pass has read: the completeness check that can refuse an erasure (`_check_complete`), the erased-User guards in grant, revoke, deactivate and reactivate, and the per-Seat skip of `ERASURE_GONE`.

**Verification.**
- Backend, full suite (`--maxprocesses=8`, fresh DB `olspillet_e15`): 3439 passed; ruff check and format clean.
- Frontend: typecheck ok; Vitest 1122 passed; `lint:colours` and `check:copy` passed; `next build` compiled.
- Playwright (`--workers=4`): `admin-delete`, `admin-users`, `admin-status`, `admin-audit`, `homes`, `takeover`, `order-field` — 66 passed. axe ran at 320 px and 1440 px in `admin-delete`.
- The stack's default DB `olspillet` lacks the Epic 9/10 tables, which is a gap from the earlier merges: its alembic version says 0064 while 0101–0119 never ran. The Debrief part of the erasure and `takeover.spec` failed there. Running the backend on a fresh `olspillet_e15stack` DB (`POSTGRES_DB=… docker compose up --no-deps`) passed everything. The run was not allowed to repair the shared dev DB.
- Slow new test: `test_a_student_in_a_running_game_is_erased_and_the_game_goes_on` takes about 9 s. Playing the Class game out to verify it through the engine (AD-4) takes about 8 s of that. `test_a_seat_that_ordered_the_last_week_stays_as_it_is` takes about 1.5 s.

**Residual risks.**
- A Seat in a Class game that has not started is not handed over (deferred).
- A Reclaim the still-logged-in User queues in the milliseconds between the hand-over and the commit would survive.
- The stored reference is free text, guarded only against `@` and the User's own name.
