---
title: 'Story 11.2: Edit the Scoring guide for a Class session'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: '7359735ba175abf06743d173f153d585d9db3b11'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-11-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** There is no Scoring guide, so a Lecturer cannot read the criteria long answers and Adapted items will be judged by, nor adapt the descriptive guide text for a Class session before the Test deadline (FR-81, FR-18, AD-23, AD-27, UX-DR49).

**Approach:** A new immutable content kind `scoring_guide` (draft v1 stored by migration 0122 and shipped as `files/scoring_guide.json`); a Lecturer's save publishes a new version of that kind scoped to the Class session (`content_records.class_session_id`), and `modules/tests` keeps a per-session pointer (`test_scoring_guides`) to the version in force, which the existing `sessions.lock_test` pins at the original Test deadline through a registered pinner. A «Sensorveiledning» block on the Klasseøkt edits the descriptive text per question; criteria are read-only.

## Boundaries & Constraints

**Always:** Guide record: `status` draft|approved; one `scale` of exactly five steps 0–4 with labels; `questions` (1–40, ids unique) each `{id, kind: long|adapted, title, guide (1–4000 chars, what is asked for and strong/weak answers), criteria}` with 5–8 criteria `{code (^[A-Z][A-Z0-9]{0,9}$, unique per question), text, weight 1–100}` summing to 100. Fewer than 5 or more than 8 criteria is refused by stable code `criteria_count` (load and save alike); other shape errors `invalid_record`. Default versions have `class_session_id NULL`; `latest_version`, `latest_body` and the load's "stored already" check consider defaults only; version numbers stay one sequence per kind. A save sends only changed texts (`{guides: {question_id: text}}`), builds the new body from the version in force (criteria, scale, titles unchanged), runs `content.normalised` (the load's validation), publishes it with the session id in the caller's transaction under the Class session row lock, points the session at it, keeps `base_id` (the default it derives from), audits ids only, emits `session:<id>`. An unchanged save stores nothing. A question is «Endret» when its text differs from its base default's text. `content.service.is_checked(version_id, model_config_id)` is added and always False, no table; the block shows «Ikke kontrollert med en Kontrolltest.» whenever it is False. Owners change (`scoring_guide.change`); Assistant lecturers read (`class_sessions.read`). Refused 409 `scoring_guide_locked` once the original `test_deadline <= now` or the pin exists; 409 `class_archived`; 422 `validation_error` for an unknown question id, 422 `criteria_count`/`invalid_record` from the content validation. `lock_test` calls registered test-lock pinners in its transaction after `assessment.pin_switch`; the guide pinner sets `pinned_at` (inserting a row on the latest default when none exists), idempotent. Copy (FEATURE_RERUN, `register_copier`) carries an edited version by its id with its base; an unedited source copies nothing. Every string in `nb.ts`, drafted copy `[ASSUMPTION]`. Migration 0122 (Revises 0121).

**Never:** No real guide text (placeholders, `status: "draft"`); no editing of criteria, codes, weights or the scale; no `checked` table or Control test (Epic 12); no second `lock_test`; no attempts, answers or scoring; `sessions` never imports `tests`; no change to the demo Class; no edit of `sprint-status.yaml`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Default | new session | GET: v1 questions, all `changed=false`, `edited=false`, `checked=false`, `draft=true`, `open=true` | — |
| Edit | owner PUT one changed text | new content version with the session id; earlier unchanged; that question `changed=true`; audit; `session:<id>` | — |
| Unchanged | PUT same text | nothing stored | — |
| Unknown id / empty text | PUT `{x: "…"}` / `""` | nothing stored | 422 `validation_error` |
| Deadline | PUT after original `test_deadline` (sweep not run) or after pin | nothing stored | 409 `scoring_guide_locked` |
| Assistant | GET / PUT | reads, `can_change=false` / | 403 `forbidden` |
| Pin | `lock_test` | row `pinned_at` set (row created on latest default if absent); second run no change; GET `pinned=true`, `open=false`, shows that version | — |
| Load | 4 or 9 criteria in a file | nothing stored | `criteria_count`, exit 1 |
| Copy | source edited | copy points at the same version id, `changed` kept | flag off: 422 as before |

</intent-contract>

## Code Map

- `backend/app/modules/content/models.py` -- `Kind.SCORING_GUIDE` (after QUESTION_SET), column `class_session_id` (Uuid, nullable, no FK: an edited version outlives its session for copies).
- `backend/app/modules/content/schemas.py` -- `ScaleStep`, `GuideCriterion`, `GuideQuestion`, `ScoringGuide` (pattern `QuestionSet` ~206).
- `backend/app/modules/content/service.py` -- `_SCHEMAS`, `_criteria_counted` (pattern `_item_types_known` ~118) in `publish`/`normalised`; `_latest` filters `class_session_id IS NULL`, next number from all; `stored_version_of` defaults only; new `publish_in(session, kind, body, *, class_session_id)`, `scoring_guide_record(id)`, `latest_scoring_guide(session)`, `is_checked`.
- `backend/app/modules/content/files/scoring_guide.json` (new) == migration 0122 literal; `__main__.py` docstring codes; `README.md`.
- `backend/migrations/versions/0122_scoring_guide.py` (new; pattern 0121) -- kind constraint, column, v1 row id `01a1f9a0-0000-7000-8000-000000000122`, table `test_scoring_guides(class_session_id PK FK cascade, scoring_guide_id FK content_records cascade, base_id FK content_records cascade, pinned_at, updated_by FK users set null, updated_at)` + trigger refusing changes once pinned.
- `backend/app/modules/tests/{models,schemas,routes}.py`, new `guide.py`, `README.md` -- table; `read_block`, `save`, `pin_guide`, `copy_guide`; routes `GET/PUT /api/class-sessions/{id}/scoring-guide` (`getSessionScoringGuide`, `setSessionScoringGuide`).
- `backend/app/modules/sessions/service.py` -- `register_test_pinner` + call in `lock_test` (~3869) after `pin_switch`; `scoring_guide_session` / `lock_for_scoring_guide` (pattern `question_set_session` ~1781); `ScoringGuideLocked(_FieldsError)` code `scoring_guide_locked`.
- `backend/app/modules/ops/sweep.py` (~23) -- import `tests.guide` so the worker's `lock_test` pins.
- `backend/app/platform/authz.py` (~147, ~174), `platform/events/registry.py` (~159) -- `scoring_guide.change`, `tests.save_scoring_guide: {session}`.
- Tests: `backend/tests/scoring_guide/test_scoring_guide.py` (new; helpers from `tests/question_set/test_question_set.py`), `tests/question_set/test_question_set.py` (load line), `tests/test_migrations.py` (HEAD 0122), `tests/test_authz_rules.py` if it lists actions.
- Frontend: `src/modules/tests/{api.ts,scoring-guide-block.tsx,scoring-guide.test.ts}`, `components/text-area-field.tsx` (label id), `modules/sessions/class-session-page.tsx` (~459 after QuestionSetBlock), `copy/nb.ts` (`tests.scoringGuide`), `npm run api:generate`.
- e2e: `frontend/e2e/scoring-guide.spec.ts` (new; pattern `question-set.spec.ts`, helpers `support/{auth,classes}.ts`, dev route `/api/dev/class-sessions/{id}/lock-test`).

## Tasks & Acceptance

**Execution:**
- `backend/app/modules/content/*`, `files/scoring_guide.json`, migration 0122 -- kind, schema, scoped publish, is_checked, seed.
- `backend/app/modules/tests/*` -- table, guide service, routes, pinner, copier.
- `backend/app/modules/sessions/service.py`, `ops/sweep.py`, `platform/authz.py`, `platform/events/registry.py` -- hooks and policy.
- Tests -- every matrix row, file == migration literal, guide covers every long item's `scoring_rule` of the shipped question set, migrations head 0122.
- Frontend block + Vitest for the touched-only body; e2e at 320/360/1440 with axe, Assistant read-only, deadline read-only.

**Acceptance Criteria:**
- Given an owner before the Test deadline, when «Sensorveiledning» loads, then each question shows its title, «Standard»/«Endret», one Tekstfelt with its label above it holding the guide text, the criteria (code, text, weight) as read-only text under it, the five-step scale once, and «Ikke kontrollert med en Kontrolltest.».
- Given a changed text saved, when the save succeeds, then the question reads «Endret» and a reload keeps it.
- Given the Test deadline passed or an Assistant lecturer, then the block is read-only text.
- Given 320 px, then one column without sideways page scroll, and axe passes at 320/360/1440.

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
Layers: blind hunter and edge-case hunter (sonnet, per the runbook's two-reviewer rule); verification-gap and intent-alignment skipped.
- verdicts: 24 findings — high 0, medium 1, low 18, false 5, maybe-false 0
- findings:
  - `[low]` `[reject]` Blind: an edit freezes the guide on its base default; a newer default never reaches an edited session and there is no reset — the block says so (`outdated`); a rebase or reset path is a new feature, and the real guide (issue #16) arrives before Lecturers edit in use.
  - `[low]` `[reject]` Blind: an archived Class's owner reads the Assistant line — the same pattern as «Spørsmål og vekter» (11.1 triage); a distinct line needs a new api field.
  - `[low]` `[patch]` Blind: a guide text with U+0000 fails the JSONB insert (500) — `GuideQuestion` now refuses a NUL character (422 `validation_error`); test row added.
  - `[low]` `[reject]` Blind: readers by version number do not filter edits, and default numbers have gaps — no reader resolves a Scoring guide by number (pins, copies and `is_checked` use the record id); gaps are cosmetic.
  - `[low]` `[reject]` Blind: pointer FKs cascade on a content delete and the trigger guards UPDATE only — no code deletes a content record; a delete guard adds a trigger for a path that does not exist.
  - `[low]` `[reject]` Blind: edited versions outlive a deleted Class session — intended (a copy uses them, Design Notes); the text is Lecturer guidance, not personal data.
  - `[false]` `[reject]` Blind: `lock_test` ignores a pinner's result and a missing default rolls the lock back forever — migration 0122 stores v1 and nothing deletes it, so `latest_scoring_guide` always answers; the lock does not need the return value.
  - `[false]` `[reject]` Blind: no Test deadline keeps the guide editable forever; the helper name may be collected by pytest — a locked session cannot clear its Testfrist (12.1), editing before that is intended; no test module imports the helper.
  - `[low]` `[patch]` Blind: the 4000-character limit is written twice in the backend — `tests.schemas` now imports `content.schemas.GUIDE_TEXT_MAX` (the frontend mirrors it as the api's limit).
  - `[false]` `[reject]` Blind: regenerated `openapi.json`/`schema.ts`, authz and personal-data registry missing — the client files are regenerated and left out of the review diff on purpose; `test_authz_rules` passes over the new action; `identity/personal_data.py` is Epic 15, not on this branch.
  - `[low]` `[reject]` Blind: no frontend test of `outdated`/`pinned`/`checked=true`, and the Assistant e2e fakes the answer — the api tests pin each state; the overlay is the repo's pattern for Assistant screens.
  - `[low]` `[reject]` Blind: another owner's save drops unsaved typing — the same design as 11.1 and 12.1 (a draft of another version is dropped so a save never reverts another owner); rare.
  - `[low]` `[reject]` Blind: the 422 shows one generic line and `UnknownQuestions` covers invalid text — the block refuses empty and too-long text before sending, so a 422 needs a crafted request.
  - `[low]` `[reject]` Blind: each read loads the latest default and a save reads the block again — a few small JSON rows; same shape as 11.1.
  - `[medium]` `[patch]` Edge: deleting a User who edited a pinned guide sets `updated_by` NULL, which the trigger refused, so the deletion failed — the trigger now refuses only changes of `scoring_guide_id`, `base_id` or `pinned_at`; test sets `updated_by` NULL on a pinned row; the already-migrated lane databases got the new function.
  - `[low]` `[reject]` Edge: sessions test-locked before 0122 have no pin and read the newest default — they predate the Individual test; no attempt exists for them.
  - `[low]` `[reject]` Edge: a late sweep may pin a default published after the deadline — judging by `created_at` compares DB time with host time (Issue #63); defaults change rarely.
  - `[false]` `[reject]` Edge: no default guide makes the lock roll back each minute — v1 is stored by the migration (same refutation as above).
  - `[low]` `[reject]` Edge: archived owner reads the Assistant line (same as the Blind row) — same reason.
  - `[low]` `[patch]` Edge: U+0000 gives 500 (same as the Blind row) — same fix.
  - `[false]` `[reject]` Edge: `publish_in` with a session id for another kind — no caller does; only `tests.guide` passes it, for `scoring_guide`.
  - `[low]` `[reject]` Edge: draft dropped mid-edit on another version (same as the Blind row) — same reason.
  - `[low]` `[reject]` Edge: access lost between commit and the read-back answers 403 — a role change inside one request; same as 11.1.
  - `[low]` `[reject]` Edge claim: the save never answers `criteria_count`/`invalid_record` — the matrix row fixes `validation_error` for the only content refusals a save can reach (empty or bad text); the criteria are copied, so `criteria_count` cannot occur on a save.

## Design Notes

- Pin location: the Start-date pins live in the frozen snapshot (`SessionRuntime.pins`); the Test-deadline pin is later, so like Story 12.1's switch it lives in the owning module's row (`test_scoring_guides.pinned_at`) and `lock_test` reaches it through a registered pinner, since `sessions` may not import `tests`.
- Session-scoped versions share the kind's version sequence; the version id (`content_records.id`) is what `is_checked` and a copy use.
- A newer default published after an edit leaves the edit in force; the block says so (`outdated`).

## Verification

**Commands:**
- `uv run pytest tests/scoring_guide tests/question_set tests/content tests/sessions tests/test_migrations.py tests/test_imports.py tests/test_authz_rules.py` -- pass
- `npm run typecheck && npm run test && npm run lint:colours && npm run check:copy && npm run build` -- pass
- `npx playwright test e2e/scoring-guide.spec.ts --workers=4` -- pass

## Auto Run Result

Status: done

**Summary.** The Scoring guide is a new immutable content kind `scoring_guide` (schema `content.schemas.ScoringGuide`): one fixed five-step scale (0–4), and for each long-answer question and Adapted item template a title, the descriptive guide text and 5–8 coded criteria whose weights sum to 100. Draft v1 holds placeholders (`status: "draft"`); migration 0122 stores it and `files/scoring_guide.json` ships it. The load refuses a question with fewer than 5 or more than 8 criteria (`criteria_count`).

A Lecturer's save («Lagre sensorveiledning», owners only, `scoring_guide.change`) sends only the changed texts. It goes through the load's validation and publishes a new version made for the Class session (`content_records.class_session_id`). That version is never the latest default. `test_scoring_guides` points the session at it and keeps its base default, so a question that differs from the base reads «Endret». `content.service.is_checked` always answers False, so every version shows «Ikke kontrollert med en Kontrolltest.».

From the original Test deadline the api answers 409 `scoring_guide_locked`. The existing `sessions.lock_test` pins the version in force through a registered pinner (`register_test_pinner`); a session that never edited is pinned on the latest default. «Lag kopi» carries an edited version over by its id. Assistant lecturers can read the guide but not edit it.

**Files.**
- `backend/app/modules/content/{models,schemas,service,__main__}.py`, `README.md`, `files/scoring_guide.json`: the kind and its schema, scoped publish (`publish_in`), `latest_scoring_guide`, `scoring_guide_record` and `is_checked`.
- `backend/migrations/versions/0122_scoring_guide.py`: the kind, v1, `content_records.class_session_id`, and `test_scoring_guides` with its pin trigger.
- `backend/app/modules/tests/{guide,models,schemas,routes}.py`, `README.md`: the block api, the save, the pinner and the copier.
- `backend/app/modules/sessions/service.py`: `register_test_pinner` in `lock_test`, `lock_for_scoring_guide`, `test_deadline_reached`, `ScoringGuideLocked` and `question_set_session(change_action)`.
- `backend/app/modules/ops/sweep.py`, `platform/authz.py`, `platform/events/registry.py`.
- Tests: `backend/tests/scoring_guide/test_scoring_guide.py` (new), `tests/question_set/test_question_set.py` (load line), `tests/test_migrations.py` (head 0122).
- Frontend:
  - `src/modules/tests/{scoring-guide-block.tsx,scoring-guide.test.ts}` (new) and `api.ts`
  - `components/text-area-field.tsx` (label id)
  - `modules/sessions/class-session-page.tsx` and `copy/nb.ts`
  - generated `lib/api/{openapi.json,schema.ts}`
  - `e2e/scoring-guide.spec.ts` (new)

**Review.** Two sonnet reviewers reported 24 findings. Patched:
- The pin trigger no longer blocks deleting a User who edited a pinned guide (medium).
- NUL characters are refused with 422 (low, two rows).
- The backend now has one 4000-character limit (low).

Rejected: 15 low and 5 false findings, each with its reason in the triage log. Nothing deferred.

**Follow-up review: not recommended.** One medium entry was patched (high 0, medium 1, low 2).

**Verification.**
- Backend: the full suite with `--maxprocesses=8` gave 3225 passed and 4 skipped after the review patches. `ruff check` and `ruff format --check` are clean. No new test runs over 1 s; the slowest is 0.80 s, in setup.
- Frontend: `tsc` is clean, Vitest 1050 passed, and `lint:colours`, `check:copy` and `next build` are ok.
- Playwright on lane 2 (8081): 144 passed across these specs:
  - scoring-guide (new; 320/360/1440 with axe) and question-set
  - class-session (base, lock, dates, rerun, obligatory, choices)
  - ai-assessment-switch, debrief-quiz-exclusions and homes
  - order-confirm, order-field, week-table, game-start and guided-week
- Screenshots at 1440 and 320, checked by eye: one column, the criteria table aligned, no sideways scroll.

**Decisions taken for the founder.**
- Edited guides are versions of the same content kind, scoped by `content_records.class_session_id`. The kind keeps one number sequence, and the record id is the version id that `is_checked` and copies use.
- The Test-deadline pin lives in `test_scoring_guides.pinned_at`, reached through a pinner that `lock_test` calls (as with 12.1's switch). It is not in the Start-date snapshot `SessionRuntime.pins`.
- One Tekstfelt per question holds both what is asked for and what strong and weak answers look like.
- «Endret» compares a question with the default its edit derives from. A newer default leaves an edit in force and shows a notice; there is no reset button.
- A copy carries only an edited guide; an unedited copy reads the latest default.
- The save sends only the texts the Lecturer touched.
- Two Adapted templates have placeholder guide entries (`tilpasset-eget-spill`, `tilpasset-replay`) until Story 11.7 names them.
- All copy except the spine's strings is [ASSUMPTION].

**Residual risks.**
- The Adapted template ids are placeholders until Story 11.7.
- Nothing ties guide questions to the question set when either is published; only a test checks the shipped files.
- An edited session never picks up a newer default's criteria.
- The implementation was done in the main context, not a subagent, per the team lead's instruction.
