---
title: 'Story 15.3: Student data is deleted automatically when retention ends'
type: 'feature'
created: '2026-11-23'
status: 'done'
baseline_revision: '32f52158f50d3b7d0a217957faf7c0c59c74ad0d'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-15-context.md'
warnings: ['oversized']
deferred:
  - summary: >-
      No per-Class-session aggregate writer is registered yet, so retention deletes without writing Cross-class aggregates.
    evidence: |-
      `reports.service.write_aggregate` belongs to Story 14.3 (backlog, not on this branch). The gate `identity.register_session_aggregate_writer` exists and is tested with fake writers (failure stops deletion); with zero writers retention goes on and logs `retention_without_aggregate_writer`. Story 14.3 must register its writer there and add the "same figures before and after" test against `ops.retention`.
    location: >-
      backend/app/modules/identity/erasure.py write_session_aggregates; backend/app/modules/ops/retention.py retain
    severity: medium
  - summary: >-
      Name readers outside the Oversikt/Spillinnsikt views still show a kept-account Student's name for a Class session whose deletion date has come.
    evidence: |-
      `_student_names` in sessions/overview.py gates the four staff game views. `sessions.service` allocation, Seat choice, time-proposal and takeover mail contexts, `messaging/messages.py` and `debrief/service.py:354` read `classes.student_names` by Class without the date. A Student erased whole is off the Roster and is named nowhere; only one who keeps the account (later Class session in the same Class) is affected.
    location: >-
      backend/app/modules/sessions/service.py, backend/app/modules/messaging/messages.py
    severity: medium
  - summary: >-
      A Class session that never had a Test deadline has no deletion date and is never retained; its Class's unregistered Roster rows wait with it.
    evidence: |-
      Story 13.9's rule gives NULL without a Test deadline; `due_retention` needs a date and `_purge_class_if_done` needs every session marked. Needs a rule (e.g. creation or archive time plus the period) from the founder.
    location: >-
      backend/app/modules/sessions/repo.py due_retention
    severity: medium
  - summary: >-
      Scoped erasure of Debrief text, test answers, AI feedback and call bodies, reports/ZIPs and running Seats has no test with a non-None scope.
    evidence: |-
      tests/ops/test_retention.py checks messages, completion corrections and Tilrettelegging per session; the other parts carry the same one-line class_session_id filter but a dropped filter would not fail a test. Settle with a two-session fixture per part (games, attempts, a storage fake).
    location: >-
      backend/tests/ops/test_retention.py
    severity: medium
---

<intent-contract>

## Intent

**Problem:** Story 13.9 stores each Class session's deletion date and Epic 13 refuses reports after it, but nothing deletes the Student data, the retention period is one global placeholder, and Roster addresses of people who never registered are kept for ever (FR-77, FR-6).

**Approach:** The Admin sets a per-Institution retention period (audited; NULL = placeholder `RETENTION_MONTHS`); `sessions` recomputes the deletion dates it rules in the same transaction. A sweep due action `ops.retention` finds each Class session whose date has come and runs the one shared routine `identity.erase_user` per Student, after the per-Class-session aggregate gate: a Student with no other live Class session is erased whole, one who keeps the account gets the same parts scoped to that Class session (`class_session_id`). Then the session is marked `data_deleted_at`, audited once, and when every Class session of the Class is marked, unregistered Roster rows and unaccepted Student Invitations go.

## Boundaries & Constraints

**Always:**
- Migration 0072 (Revises 0071): `institutions.retention_months` INT NULL, check 1–120; `class_sessions.data_deleted_at` timestamptz NULL.
- `PUT /api/admin/institutions/{id}/retention` (`setInstitutionRetention`, policy `institutions.manage`), body `{months: int 1..120 | null}`; audit `institution.retention_changed` `{months, previous_months}`; same value writes nothing; unknown id 404; listener redates only sessions whose date has not come and that are not marked.
- `InstitutionOut` gains `retention_months` and `retention_default_months`. A Control test's Class belongs to the operator-owned Institution, so its date follows that Institution's period (AD-27).
- Every registered erasure preparation, step and object eraser takes `scope` (Class session id or None); one implementation, `erase_user(..., class_session_id=)`. Scoped runs never touch identity tables, write no `user.deleted` audit row and skip the guard.
- Keep the account when the User holds an account role, a Class staff place, a Roster entry (removed too) in a Class with another Class session not yet marked, or a current entry in an unarchived Class with no Class session.
- Aggregate gate: `identity.register_session_aggregate_writer` (Story 14.3 registers `reports.service.write_aggregate`); any failure → nothing deleted for that session, retried next sweep.
- Idempotent: an interrupted run repeats; erased Users are skipped; one audit row `class_session.data_deleted` (system actor, ids + counts) per session; logs ids and counts only.
- After the date: staff Oversikt/Spillinnsikt show Seats by Role (no names), the Studentside record answers 409 `data_deleted` and the page says so; reports and the Completion export already refuse (Epic 13).
- Archived Class with no Class session: its unregistered Roster rows and Invitations go at archive day (Oslo) + its Institution's period.
- All UI copy in `nb.ts`, marked `[ASSUMPTION] Story 15.3`.

**Never:** no deletion before the stored date; no change to game tables or the Decision log; no build of `write_aggregate` or Tverrklasse-statistikk (Story 14.3); no deletion of the Class row; no name or e-mail in logs, audit or job arguments.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Admin sets 12 months | session dated 2027-06-18 | date 2027-12-18, Hjem shows it, audit row | — |
| Bad period | 0, 121, "6", 2.5 | 422, nothing stored | non-Admin 403, unknown 404 |
| Date already come | Admin changes period | stored date kept | — |
| Control test | operator Institution 2 months, course 24 | date = Test deadline + 2 months | — |
| Extension | own Test deadline +20 days | not due before 2027-07-07 (Oslo) | `retain` answers `not_due` |
| Only session | Student with no other session | anonymised, data gone | — |
| Later session | Student on another Class with a live session | account kept; this session's data gone, the other's stays | — |
| Aggregate fails | writer raises | `aggregate_failed`, nothing deleted, still due | logged by type |
| Interrupted | one Student erased, session unmarked | rerun finishes, one session audit row | — |
| Both entry points | Admin delete vs retention, same data | same users row and footprint | — |
| Last session of Class | all sessions marked | unregistered entries + Invitations gone, Class row stays | — |
| Archived, no session | archived 200 days ago, 6 months | roster purged; 150 days: not yet | — |
| Studentside after date | staff GET record | 409 `data_deleted`; outsider 403 | — |
| Games after retention | Oversikt, Spillinnsikt | 200, no Student names, Roles shown | — |

</intent-contract>

## Code Map

- `backend/app/platform/retention.py` -- the pure rule (Story 13.9), `add_months`, `OSLO`.
- `backend/app/modules/sessions/service.py` `_store_deletion_date`, `retention_months_of_class`, `_redate_institution` (listener), `RetentionTarget`, `due_retention`, `mark_data_deleted`; `data_deleted(row, now)` is Epic 13's check.
- `backend/app/modules/identity/erasure.py` -- `erase_user` (shared routine), registries, `register_session_aggregate_writer`, `write_session_aggregates`.
- Scoped erasure parts: `debrief/commands.py erase_user_text`, `messaging/repo.py erase_user`, `reports/service.py _erase_reports` + `reports/repo.py`, `progress/service.py delete_corrections_of`, `sessions/service.py _hand_over_seats/_erase_session_data` + `sessions/repo.py`, `games/service.py hand_over_seats_of` + `games/repo.py erasure_seats_of`, `tests/service.py _erase_test_data`, `assessment/service.py erase_feedback_of_user`, `ai/calls.py clear_bodies_of_user`, `classes/repo.py delete_staff_rows_of`.
- `backend/app/modules/ops/retention.py` (new) -- due actions; `ops/sweep.py` registers them; `platform/events/registry.py` `ops.retention`.
- `backend/app/modules/identity/{models,repo,schemas,service,routes,personal_data}.py`, `classes/{repo,service}.py` -- period, roster helpers, purge.
- `backend/app/modules/sessions/overview.py` `_student_names`; `reports/studentside.py` `RecordDeleted`, `reports/routes.py`.
- Frontend: `src/modules/admin/{institution-list.tsx,institutions.ts,api.ts}`, `src/modules/reports/student-page.tsx`, `src/copy/nb.ts`, regenerated `src/lib/api/*`.

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0072_retention.py`, models, `tests/test_migrations.py` -- columns and walk.
- identity/sessions/classes -- period, listener, retention reads, purge.
- erasure parts -- `scope` parameter everywhere; `erase_user(class_session_id=)`.
- `backend/app/modules/ops/retention.py`, `sweep.py`, `registry.py` -- due actions.
- overview/studentside -- names hidden, 409.
- `backend/tests/ops/test_retention.py` -- every matrix row.
- Frontend -- «Oppbevaring» column and inline form, Studentside deleted state, audit labels, Vitest `retentionMonths`, e2e in `admin-institutions.spec.ts` and `studentside.spec.ts`.

**Acceptance Criteria:**
- Given an Institution in «Institusjoner», when the Admin saves 12 in «Endre oppbevaringstiden for …», then the row reads «12 måneder etter Testfristen», focus returns to the button and a status line says the dates were recomputed.
- Given the sweep at or after a Class session's deletion date, when `ops.retention` runs, then the Students' data of that session is deleted through `identity.erase_user` and the session is marked once.
- Given a Studentside of a session whose date has come, when staff open it, then the page says the Student data is deleted.

## Spec Change Log

## Review Triage Log

### 2026-11-23 — Review pass
- verdicts: 38 findings — high 0, medium 9, low 17, false 6, maybe-false 0; 6 intent rows descriptive (no verdict)
- findings:
  - `[medium]` `[defer]` blind 1 / edge 2: zero aggregate writers pass the gate — real; Story 14.3 owns `write_aggregate`. Retention keeping the date wins over keeping data for an aggregate (founder decision recorded); now logs `retention_without_aggregate_writer`. Deferred.
  - `[low]` `[reject]` blind 2: a kept account stays linked by id to Seats, Orders and attempts — those are `keep` tables by the 15.2 registry (no name, address or text); the name is hidden from the date on.
  - `[low]` `[reject]` blind 3: views say «deleted» between the date and the run — deliberate (Design Notes): Epic 13 already refuses reports from the date; the date is the rule.
  - `[low]` `[reject]` blind 4 / edge 5: `aggregate_failed` counted as done and retried each sweep — the sweep's model is retry-next-minute; the failure is logged by type; adding `Backoff` needs an import of `sweep` from `retention` (cycle).
  - `[low]` `[reject]` blind 5 / edge 10: one failing Student blocks marking — the session stays due and is retried, the failure logged; skipping a Student would mark a session whose data is not all gone.
  - `[medium]` `[patch]` blind 6a / edge 1: date not re-checked under the final lock — `retain` now re-reads `deletion_date` under the row lock and does not mark a session whose date moved.
  - `[low]` `[reject]` blind 6b: a Student joining the Roster during the run — joining a Class session months past its Test deadline; their data there is none.
  - `[medium]` `[defer]` blind 7 / edge 6: no deletion date without a Test deadline — needs a rule; deferred.
  - `[low]` `[reject]` blind 8 / edge 8: shortening the period can make data due at once, with no reminder — the Admin's deliberate act on the Institution's instruction; recorded as a founder decision.
  - `[low]` `[reject]` blind 9 / edge 11: archived-Class finder rescans every archived Class — a few hundred rows a minute at pilot scale; a LIMIT/SQL rewrite adds complexity for no user-visible gain.
  - `[low]` `[reject]` blind 10a / edge 13: notices keyed by a game id, `mail_deliveries` and the kept account's Roster entry stay — ids only (no text) and the Roster entry is account data the full erasure removes.
  - `[false]` `[reject]` blind 10b: calls under another scope kind keep their bodies — Student follow-up calls are recorded with `scope_kind = class_session` (`ai.models.SCOPE_KINDS`: evaluation is the Admin's batch, no Student text).
  - `[medium]` `[defer]` blind 11 / verification 3: scoped parts beyond three tables untested — deferred (frontmatter).
  - `[low]` `[reject]` blind 12: 1–120 bounds in four places, `?? 6` fallback — the SQL check, the schema and the client each enforce at their layer, as the other Institution fields do.
  - `[false]` `[reject]` blind 13a / intent 1: report downloads and the Completion export do not say deleted — Epic 13 already answers 409 `data_deleted` from the date (`reports/report.py`, `bundle.py`, `completion_export.py`) with copy in `nb.ts`.
  - `[low]` `[reject]` blind 13b: two aggregate hooks; Admin deletion writes no session aggregates — the per-User hook is 15.2's seam; one Student's deletion before the Test deadline leaves the Class session to write its aggregate at retention.
  - `[medium]` `[patch]` verification 1: the name mask was not observed (retain erased the Students first) — `test_from_the_date_on_the_staff_views_show_no_names_before_the_run` sets the date only and asserts no names while the names are still stored.
  - `[medium]` `[patch]` verification 2: `_keeps_account` branches untested — `test_a_student_keeps_the_account_for_each_reason` (account role, Class staff, Class with no session yet).
  - `[low]` `[reject]` verification other 1: `ops.retention` in `COMMAND_TOPICS` is not asserted — documentation of the topics, like the other sweep actions.
  - `[medium]` `[defer]` verification other 2 / edge 7: other name readers ungated for kept accounts — deferred (frontmatter).
  - `[medium]` `[defer]` edge 3: a date moved later after `data_deleted_at` is never re-run — the Test deadline save after the date is past is out of the normal flow; `_redate_institution` skips marked sessions. Grouped with the no-date rule decision; recorded here only.
  - `[low]` `[reject]` edge 4: two sweeps in parallel — one sweeper process runs the sweep (AD-9).
  - `[low]` `[patch]` edge 9: redated sessions not announced — `_redate_institution` now emits `session` and each registered Student's `user`.
  - `[false]` `[reject]` edge 12: a Student who played without a Roster entry — every Class session Student, Control test ones included, is on the Roster (Story 12.8 invites them there).
  - `[low]` `[reject]` blind (verification) `before.status_code != 409` weak — it guards that the 409 appears only after the date; the 200 path is Story 13.2's test.
  - `[false]` `[reject]` blind: `__all__` re-export trick brittle — the suite's fixture convention.
  - `[false]` `[reject]` blind: `assert isinstance` as a guard — the sweep hands its own finder's ids, as `cost_limit.notice_due` does.
  - `[false]` `[reject]` blind: erasure docstring says none registered — it names the per-User hook, which is still unregistered.
  - `[low]` `[reject]` edge 3 duplicate — see above.
  - intent (descriptive): reading R2 implemented; aggregates gate tested with fakes (14.3 absent); Control test checked by date, not by a run (the run is Institution-agnostic); interruption simulated by a hand erasure; «both entry points» compares an unscoped run (the scoped run is the same routine with a filter, checked on three tables); Class report (Epic 14) not on this branch.

## Design Notes

"Scoped" erasure reuses every registered part with a Class-session filter, so there is one routine and the registry test still guards coverage. Names are hidden by the date (Epic 13's `data_deleted`), not by the run marker, so staff views agree with the 409s from the first day.

## Verification

**Commands:**
- `cd backend && uv run pytest tests/ops/test_retention.py tests/identity tests/sessions/test_deletion_date.py tests/test_migrations.py tests/test_imports.py -q` -- expected: pass
- `cd backend && uv run pytest -q -n 8 --maxprocesses=8` -- expected: pass
- `cd frontend && npm run typecheck && npx vitest run && npm run lint:colours && npm run check:copy && npm run build` -- expected: pass
- `cd frontend && npx playwright test admin-institutions studentside homes --workers=4` -- expected: pass

## Auto Run Result

Status: done
Blocking condition: none

**Summary.** The Admin sets each Institution's retention period in «Institusjoner» (column «Oppbevaring», inline form, 1–120 months or empty for the placeholder; `PUT /api/admin/institutions/{id}/retention`, audited `institution.retention_changed`); `sessions` recomputes every not-yet-due deletion date in the same transaction and Hjem shows it. The sweep's `ops.retention` deletes a Class session's Student data once its stored date has come: the per-Class-session aggregate gate first, then `identity.erase_user` per Roster Student — whole for one with no other live Class session, scoped to the session (`class_session_id`, every registered erasure part now takes `scope`) for one who keeps the account — then `data_deleted_at` and one audit row `class_session.data_deleted`; when every session of the Class is marked, unregistered Roster rows and unaccepted Student Invitations go. `ops.retention_archived_classes` purges an archived Class with no session at archive day + period. From the date on, Oversikt/Spillinnsikt/start/waited views show Seats by Role, and the Studentside answers 409 `data_deleted` with its own page.

**Files.**
- `backend/migrations/versions/0072_retention.py`, `identity/models.py`, `sessions/models.py`, `tests/test_migrations.py` — `institutions.retention_months`, `class_sessions.data_deleted_at`.
- `backend/app/modules/identity/{erasure,service,repo,schemas,routes,personal_data}.py` — scoped routine, session aggregate gate, period, Roster helpers, registry notes.
- `backend/app/modules/sessions/{service,repo,overview}.py` — Institution's period, redating listener, retention reads, name mask.
- `backend/app/modules/ops/{retention,sweep}.py`, `platform/events/registry.py` — due actions.
- Scoped erasure parts: `debrief/commands.py`, `messaging/repo.py`, `reports/{service,repo}.py`, `progress/service.py`, `games/{service,repo}.py`, `tests/service.py`, `assessment/service.py`, `ai/calls.py`, `classes/{repo,service}.py`.
- `backend/app/modules/reports/{studentside,routes}.py` — 409 `data_deleted`.
- `backend/tests/ops/test_retention.py` (new), `tests/sessions/test_deadline_reminders.py` (sweep order).
- Frontend: `src/modules/admin/{institution-list.tsx,institutions.ts,api.ts,institutions.test.ts}`, `src/modules/reports/student-page.tsx`, `src/copy/nb.ts` ([ASSUMPTION] Story 15.3), regenerated `src/lib/api/*`, `e2e/admin-institutions.spec.ts`, `e2e/studentside.spec.ts`.

**Review.** Four layers (blind, edge case, verification gap, intent; sonnet). Patched: 3 medium (date re-checked under the final lock; name-mask test without a run; keep-account reasons test) and 1 low (redated sessions announced). Deferred 4 (aggregate writer from 14.3; other name readers for kept accounts; sessions with no Test deadline; scoped coverage of the remaining parts). Rejected with reasons in the triage log.

**Follow-up review recommended: true** — two medium patches changed behaviour no reviewer has read: the final-lock date re-check in `ops.retention.retain`, and `_redate_institution` emitting events while it reads the registered Students on a second connection.

**Decisions taken in the founder's place.** Retention goes on with no aggregate writer registered (logs `retention_without_aggregate_writer`) rather than keep data past the date; a Student keeps the account for an account role, a Class staff place, another live Class session (removed Roster entries count) or a current unarchived Class with no session; names are hidden from the date, not from the run; the period is changed by `institutions.manage` with no notice when it makes sessions due at once; a Class's unregistered addresses go once all its sessions are deleted, archived or not; a kept Student's Roster entry, mail deliveries and id-only rows stay; draft copy.

**Verification.** Backend full suite (`-n 8`, fresh DB `olspillet_e15bm`): 4200 passed, 1 skipped, then one sweep-order test updated and re-run (29 passed); ruff clean. New tests each under 1.2 s. Frontend: typecheck, Vitest 1349 passed, `lint:colours`, `check:copy`, `next build`. Playwright on the stack (`POSTGRES_DB=olspillet_e15m`): `admin-institutions`, `studentside`, `homes`, `game-insight`, `start-games`, `order-field`, `admin-audit` — 55 passed; axe at 320 and 1440 px.

**New personal-data tables.** None; `institutions.retention_months` and `class_sessions.data_deleted_at` hold no personal data (registry notes updated).

**Residual risks.** The deferred items; the archived-Class finder scans every archived Class each sweep.
