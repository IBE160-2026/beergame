---
title: "Story 15.12: Hold Student Invitations until the Institution's data processing agreement is recorded"
type: 'feature'
created: '2026-11-23'
status: 'done'
baseline_revision: '3facfaf7ea45c4f8947274944d4a8458c515b1f5'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-15-context.md'
warnings: ['oversized']
deferred:
  - summary: >-
      The Lecturer's agreement-missing message on «Send påminnelse» and «Registrer manuelt» has no UI test.
    evidence: |-
      The messages maps in registration-status.tsx and roster-entry-forms.tsx carry processing_agreement_missing; only roster-send.spec.ts checks the message (route-mocked 409). The api refuses both paths (test_processing_agreement.py). Add two route-mocked cases modelled on roster-send.spec.ts.
    location: >-
      frontend/src/modules/classes/registration-status.tsx, frontend/src/modules/classes/roster-entry-forms.tsx
    severity: low
---

<intent-contract>

## Intent

**Problem:** PRD §6.1 says the operator signs a data processing agreement (DPA) with an Institution before any of its Students are invited, but nothing records an agreement or stops a Lecturer from inviting Students of an Institution without one.

**Approach:** Store who signed and when on the Institution (`identity`, migration 0071), recorded by the Admin in «Institusjoner» behind a new `platform/authz` policy and audited; `identity.service.has_processing_agreement(institution_id)` answers it. `classes` asks it inside the transaction of every command that issues a Student Invitation or enrols a Student by hand; `REQUIRE_DPA_FOR_INVITATIONS` (default off, the founder's decision) decides whether a missing agreement refuses (`409 processing_agreement_missing`) or is only logged with ids.

## Boundaries & Constraints

**Always:**
- The gate runs in the same transaction as the send, after the Class row hold, before anything is written: a refusal leaves the staging, the Roster and Invitations untouched and enqueues nothing.
- The gate always passes for a Class whose Institution is operator-owned (read via `identity.service.operator_institution`, Story 12.7) and for any Control test Class (its Roster is test students only, the operator is controller, FR-82) even after the operator mark moved.
- With the flag off, a missing agreement logs `invitation_without_processing_agreement` with `class_id` and `institution_id` only, and the send goes on.
- Lecturer, Admin and Assistant Invitations (Story 3.7, 4.9) and resends of role Invitations are never checked.
- Recording: `signed_by` text trimmed 1–200 chars, `signed_on` a date not after today in Oslo (422 `fields.signed_on = in_future`), recorded again replaces it; identical values write nothing; each change one audit row `institution.processing_agreement_recorded` with ids and `signed_on` only.
- All new UI copy in `frontend/src/copy/nb.ts`, marked `[ASSUMPTION]`.

**Never:** decide the flag's production value; remove a recorded agreement (no v1 need); gate Invitation acceptance, renewal requests or Student links already sent; add a frontend pre-check that hides the send button.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Record | Admin PUT `{signed_by, signed_on}` | 200 InstitutionOut with `processing_agreement`; `has_processing_agreement` true; one audit row | — |
| Not Admin | Lecturer PUT | 403 `forbidden` | nothing stored |
| Bad body | blank `signed_by` / future date / unknown id | 422 `invalid_request` fields / 404 `not_found` | nothing stored |
| Flag on, no DPA | Lecturer sends staged upload / reminder / manual registration | 409 `processing_agreement_missing`; staging kept; no Roster/Invitation/notice row | Lecturer sees nb message |
| Flag on, DPA recorded | same | 201 as before | — |
| Flag off, no DPA | same | 201; warning log with ids only | — |
| Operator Institution or Control test | flag on, no DPA, test student invited | 201 | — |

</intent-contract>

## Code Map

- `backend/migrations/versions/0071_processing_agreement.py` -- new: `institutions.dpa_signed_by` TEXT, `dpa_signed_on` DATE, `dpa_recorded_at` TIMESTAMPTZ, all null or all set (check constraint), down_revision 0070.
- `backend/app/modules/identity/models.py:190` -- `institutions` table; add the three columns + check.
- `backend/app/modules/identity/schemas.py:341` -- `InstitutionOut` (Admin-only consumer); add `processing_agreement: ProcessingAgreementOut | None`; new `ProcessingAgreementIn` (`extra=forbid`, text like `ops/schemas.py:18 AgreementText`).
- `backend/app/modules/identity/repo.py:626` -- pattern of `set_no_letter` / `no_letter_of`; add `set_processing_agreement`, `processing_agreement_of`.
- `backend/app/modules/identity/service.py:1371` -- pattern of `set_institution_no_letter` (lock, audit, log); add `record_processing_agreement`, `has_processing_agreement(institution_id, session=None)`; `_institution_out` maps the columns; `operator_institution` at :1406 reused.
- `backend/app/modules/identity/routes.py:657` -- `admin_router` PUT pattern; add `PUT /institutions/{id}/processing-agreement` (`recordProcessingAgreement`).
- `backend/app/platform/authz.py:87` -- add policy `institutions.processing_agreement: {ADMIN}`.
- `backend/app/platform/config.py:64` -- add `require_dpa_for_invitations: bool = False`.
- `backend/app/modules/classes/service.py:362,522` and `register_manually` -- `send_invitations`, `send_reminders`, manual registration: call a new `_agreement_gate(s, class_id)` after `_hold`; raise `ProcessingAgreementMissing`.
- `backend/app/modules/classes/repo.py:104` -- `class_label` gets `institution_id` (control_test already there).
- `backend/app/modules/classes/routes.py:373,446,~515` -- map `ProcessingAgreementMissing` to 409 `processing_agreement_missing`; add 409 to `documented`.
- `backend/app/modules/identity/personal_data.py:59` -- `institutions` note now names the signatory text.
- `backend/tests/identity/test_processing_agreement.py` -- new api tests; reuse `tests/sessions/test_control_test.py` (`people`, `control`, `mark`), `tests/sessions/test_test_students.py:invite`, `tests/classes/test_roster_send.py` helpers, `flag`-style monkeypatch + `get_settings.cache_clear()`.
- `backend/tests/test_migrations.py:193` -- HEAD `0071`, up/down check.
- `frontend/src/modules/admin/institution-list.tsx` + `api.ts` + `institutions.ts` -- «Databehandleravtale» column with state and an inline form (pattern `evaluation-page.tsx:219 AgreementForm`).
- `frontend/src/modules/classes/roster-upload.tsx:132`, `registration-status.tsx:150`, `roster-entry-forms.tsx:80` -- map the code to the nb message.
- `frontend/src/copy/nb.ts:2724` (admin.institutions), classes roster copy -- new strings.
- `frontend/e2e/admin-institutions.spec.ts`, `roster-send.spec.ts` -- record via UI; refused send message via mocked 409 route.
- `docs/ops/readiness.md`, `ARCHITECTURE-SPINE.md:573`, `SETUP-GUIDE.md`, `.env.example`, `docker-compose.yml` -- flag documented, R15 open founder item.

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0071_processing_agreement.py`, `identity/models.py`, `schemas.py`, `repo.py`, `service.py`, `routes.py`, `platform/authz.py`, `platform/config.py` -- record and read the agreement -- AC 1.
- `classes/repo.py`, `classes/service.py`, `classes/routes.py` -- the gate on send, reminders, manual registration -- AC 2–4.
- `identity/personal_data.py` -- registry note -- 15.2 rule.
- `backend/tests/identity/test_processing_agreement.py`, `tests/test_migrations.py` -- matrix rows, both flag settings, test student with flag on.
- `frontend` admin + classes files, `nb.ts`, `npm run api:generate` -- UI and messages; unit test for the new validation helper.
- e2e specs -- record via UI at phone and laptop; refusal message shown.
- docs listed above -- flag, R15, spine note.

**Acceptance Criteria:**
- Given an Institution in «Institusjoner», when the Admin records who signed and the date, then the row shows them, `has_processing_agreement` is true, and the audit log has `institution.processing_agreement_recorded`.
- Given `REQUIRE_DPA_FOR_INVITATIONS=true` and no agreement, when a Lecturer presses «Send N Invitasjoner», then the page shows the nb message that the Institution's agreement is missing and nothing is sent.
- Given the flag off, when the same send is made, then the Invitations go out and a log line with ids only records the missing agreement.
- Given the flag on and a Control test in the operator-owned Institution without agreement, when the Admin invites a test student, then the Invitation is sent.
- Given the story is done, then the spine's Deferred entry and `docs/ops/readiness.md` R15 say the gate is built, default off, and the founder's decision is open; the flag is not changed by the story.

## Spec Change Log

## Review Triage Log

### 2026-11-23 — Review pass
- verdicts: 29 findings — high 0, medium 3, low 14, false 12, maybe-false 0 (the three medium rows share one root cause, the CHECK constraint)
- findings:
  - Blind hunter
    - `false` `reject` Gate lives in `classes` not in `identity`, other callers bypass it — the verification layer and a grep of `backend/app` show the only callers of `send_roster_invitations`, `send_entry_reminders` and `register_manually` are the three gated commands; the story asks `classes` to ask `identity` (AD-12).
    - `false` `reject` Default is fail-open — the story says the story does not decide; the default keeps today's behaviour and R15 is a go/no-go item (spine, readiness).
    - `low` `patch` The «Signert av» hint invites a person's name — hint now asks for the role at the Institution («Rollen ved Institusjonen …»); registry note stands.
    - `low` `reject` Audit keeps no signer history, no revoke or document reference — AD-15 audit is ids only; nothing in the story asks for history or revoke; adding it is new surface.
    - `low` `reject` Gate runs before the staging/valid-day checks, so a gone staging answers 409 — the 409 is still true and nothing can be sent; the page's line names the real blocker. Reminders differ on purpose (no address, no question).
    - `low` `reject` No lower bound on `signed_on` — a plausible-date rule is new policy; the Admin types the day from the document.
    - `low` `patch` The form ignores the api's 422 `fields.signed_on = in_future` — mapped to the field's reason (`dayRefused` in institution-list.tsx), the general line stays for other failures.
    - `low` `reject` `todayInOslo`/`formatDay` imported from `./evaluation`, `maxLength` counts UTF-16 — same helpers and rule as Story 15.4's agreement form; the api has the last word.
    - `false` `reject` No proactive warning to the Lecturer or Admin of the setting — not asked by the story; the refusal message is the asked surface.
    - `low` `defer` Reminder and manual-registration messages have no UI test — deferred (frontmatter); api refusal of both is tested.
    - `medium` `patch` CHECK constraint untested (and see edge-case finding below) — constraint fixed and `test_the_database_refuses_a_half_recorded_agreement` added; reminder no-target test added (see verification gap).
    - `false` `reject` Empty `REQUIRE_DPA_FOR_INVITATIONS=` in `.env.example` breaks parsing — `.env` feeds compose only, whose `${…:-false}` turns an empty value into `false`; the FEATURE_* flags use the same pattern.
    - `false` `reject` Readiness «R1–R12» stale, R15 without issue — that sentence is about the Proposals of R1–R12 only; the brief forbids touching GitHub issues, R13/R14 also have none.
    - `low` `patch` «Trengs ikke for operatørens egen» reads cut off — now «Trengs ikke: operatørens egen Institusjon». Hand-rolled cancel button and `method="post"` match the existing rename and evaluation forms (rejected part).
  - Edge case hunter
    - `medium` `patch` CHECK lets `dpa_signed_by` NULL through when the other two are set (NULL → constraint passes) — `dpa_signed_by IS NOT NULL AND` added in migration 0071 and the model; tested.
    - `low` `reject` NUL in `signed_by` answers 500 — the same holds for Story 15.4's agreement text; an Admin does not type NUL; a guard is new complexity.
    - `low` `patch` Server `in_future` refusal shown only as generic failure — same as blind finding, patched.
    - `low` `reject` Gate precedence over 404/422 — same as blind finding.
    - `false` `reject` Empty env value fails to parse — same as blind finding.
    - `low` `reject` Unknown id with a future date answers 422 not 404 — validation before lookup, as Story 15.4's route; harmless.
    - `medium` `patch` Claim «all null or all set» not held by the CHECK — same root cause as the first edge finding, patched.
  - Verification gap
    - `low` `patch` Reminder gate's `if targets:` unpinned — `test_with_the_setting_on_a_reminder_with_nothing_to_send_answers_as_before` added (422 `nothing_to_send` with the setting on).
    - `low` `defer` Reminder/manual message mapping not verified in the frontend — same as blind finding, deferred.
  - Intent alignment (descriptive)
    - `false` `reject` Decision AC says «settled» but the spine says «still open» — the story says it does not decide; recorded open with R15 (Design Notes).
    - `false` `reject` Gate also on reminders and manual registration (wider than Story 4.4) — chosen in Design Notes: both give a Student access and mail them.
    - `false` `reject` Control test Classes exempt beyond the operator id — chosen in Design Notes (FR-82, mark may move).
    - `false` `reject` Refusal not carried through a real backend to the browser — the stack runs with the setting off by design; api tests prove the refusal, e2e proves the message.
    - `false` `reject` Expired stagings purged outside the transaction on a refused send — pre-existing purge of expired rows; no Roster row or live staging changes.
    - `false` `reject` Reminder with nothing to send answers 422 first — intended; now tested.

## Design Notes

The founder has not recorded the decision, and the story may not decide it, so the flag ships `false` (today's behaviour) and readiness item R15 keeps it a go/no-go item; the AC's "settled" line is recorded as open, as Story 15.11 did with its founder items. Manual registration (Story 4.8) is gated too: it gives a Student access and mails them without an Invitation, so leaving it open would make the hold a formality. Control test Classes pass even when the operator mark later moved away, since their Roster can only hold test students whose controller is the operator.

## Verification

**Commands:**
- `cd backend && uv run pytest tests/identity/test_processing_agreement.py tests/test_migrations.py -q` -- passes
- full backend suite `--maxprocesses=8`; `npm run typecheck`, `npm test`, `lint:colours`, `check:copy`, `build`; Playwright for touched specs + play-screen + homes -- pass

## Auto Run Result

Status: done

**Summary.** The Admin records an Institution's data processing agreement (who signed, the day) in «Institusjoner»; it is stored on `institutions` (migration 0071, all-or-none CHECK), audited as `institution.processing_agreement_recorded`, behind the policy `institutions.processing_agreement`, and read by `identity.service.has_processing_agreement`. `classes` asks it in the transaction of «Send N Invitasjoner», «Send påminnelse» (when there is an address) and «Registrer manuelt»; with `REQUIRE_DPA_FOR_INVITATIONS` on it answers `409 processing_agreement_missing` and writes nothing, off it logs `invitation_without_processing_agreement` with ids. The operator-owned Institution and every Control test Class always pass; staff and role Invitations are never checked. The founder's decision stays open: default `false`, spine Deferred entry and readiness R15 say so.

**Decisions taken in place of the founder:** default `false` (no behaviour change until decided); manual registration gated too; Control test Classes pass even after the operator mark moved; the signer is stored as the Admin's text (a role), no user id column.

**Files:** migration `0071_processing_agreement.py`; identity models/schemas/repo/service/routes; `platform/authz.py` (policy), `platform/config.py` (flag); classes repo/service/routes (gate, 409); `personal_data.py` (institutions note, handling `keep`); tests `tests/identity/test_processing_agreement.py` (13), `tests/test_migrations.py`; frontend `admin/institution-list.tsx` (column and inline form), `admin/api.ts`, `admin/institutions.ts` (+test), classes roster-upload / registration-status / roster-entry-forms (message), `copy/nb.ts`, generated api client; e2e `admin-institutions.spec.ts`, `roster-send.spec.ts`; docs `docs/ops/readiness.md` (R15), spine, SETUP-GUIDE, `.env.example`, `docker-compose.yml`.

**Implementation note.** The implementation was done in the orchestrating context, not a fresh sub-agent, because the run's brief requires it.

**Review.** Four reviewers (blind, edge case, verification gap, intent alignment). Patched: 1 medium (CHECK let a NULL signer through) and 5 low (server `in_future` beside the field, hint copy, «Trengs ikke» copy, reminder no-target test, constraint test). Deferred: 1 (UI test of the message on reminders and manual registration). Rejected: the rest, reasons in the triage log.

**Follow-up review recommended:** false (no high patched; one medium patched, with a test).

**Verification.** Backend full suite `--maxprocesses=8`: 4017 passed before review; after patches identity, classes and test-student suites 508 passed, new file and migration test 22 passed; no new test over 1 s (slowest new 0.28 s). Frontend: typecheck, Vitest 1267 passed, `check:copy`, `lint:colours`, `next build` (also in the frontend image) pass. Playwright (`--workers=4`): admin-institutions, roster-send, roster-upload, roster-entries, registration-status, homes, order-field, game-card: all passed, axe at 320 and 1440 px in the new tests. Revised constraint also applied by hand to this run's already-migrated databases.

**Residual risks.** The decision AC is not met by design (open founder item R15). The message on reminders and manual registration is shown by the same mapping as the tested send but has no UI test. No new table; the new text column `institutions.dpa_signed_by` is listed in the personal-data registry.

