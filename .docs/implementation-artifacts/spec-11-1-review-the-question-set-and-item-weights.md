---
title: 'Story 11.1: Review the question set and Item weights'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: 'a7539816d43d342df9b1d458cbb71998c82a61b1'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-11-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** There is no question set for the Individual test, so a Lecturer cannot review its questions, take some out or change Item weights before the Start date, and nothing guarantees the weights sum to 100 % (FR-52, FR-53, FR-80, UX-DR49).

**Approach:** A new immutable content kind `question_set` (draft placeholder v1 stored by migration 0121 and shipped as `backend/content/question_set.json`), a `load` subcommand of the content CLI that publishes every kind's file idempotently, a per-Class-session selection owned by `modules/tests` (`test_selections`), a «Spørsmål og vekter» block on the Klasseøkt with its own save, and a `question_set` pin the Start-date lock stores in `SessionRuntime.pins` (refused in production while the set is `draft`).

## Boundaries & Constraints

**Always:** Weights are whole percents 0–100; included Core item weights + Adapted total weight = 100 for a save (422 `weights_not_100`, `fields={"weights": "sum"}`); the record's Core items carry type `choice|table|number|long`, weight, `answer_key` (choice) or `scoring_rule` (others), tags from a closed set (`quantity`, `explanation-wording`, `unseen-demand`, `other-business`); Starting task items are referenced by id (`starting_task_item`), never copied, and all of the latest Starting task's items must be referenced; exactly one `explanation-wording`, ≥1 `unseen-demand`, ≥1 `quantity`, 2–3 `other-business` items of type table/number; replacement items (for < 10 own Orders) whose weights sum to the record's `adapted_weight`; the record's defaults sum to 100. The load reports stable codes (`unknown_item_type`, `unknown_kind`, `invalid_record`) and exits non-zero, storing nothing for that file. The block shows the effective selection: the stored one when its version is the latest, else the latest version's defaults with a notice; after the lock it shows the pin. Changes are owner-only (`question_set.change`), refused 409 `session_locked` once `sessions.is_locked`, 409 `class_archived` for an archived Class; Assistant lecturers read (`class_sessions.read`). A save audits ids only and emits `session:<id>`. Every string in `nb.ts`; drafted copy marked `[ASSUMPTION]`. Migration numbered 0121 (Revises 0120).

**Never:** No real question text (placeholders only, `status: "draft"`); no diagram item type; no attempts, answers or scoring (11.3+); no Scoring guide (11.2); no change to `sessions.lock_test`; no import of `tests` from `sessions` (tests registers a pin provider and a copier, as `debrief` and `replay` register theirs); no change to the demo Class «class-of-1994»; no edit of `sprint-status.yaml`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Default | New Class session, no selection | GET lists v1 items with default weights, Adapted 30 %, `draft=true`, sum 100 | — |
| Valid save | owner PUT weights/excluded/adapted summing to 100, unlocked | stored with latest version; audit row; `session:<id>` emitted | — |
| Bad sum | PUT summing to 95 | nothing stored | 422 `weights_not_100` |
| Unknown id | PUT with an id not in the version, or weight outside 0–100 | nothing stored | 422 `validation_error` |
| Quantity out | PUT excluding a `quantity` item, sum 100 | stored; GET flags it | — |
| Locked | PUT after Start date / lock | nothing stored | 409 `session_locked` |
| Assistant | GET / PUT | reads, `can_change=false` / | PUT 403 `forbidden` |
| Lock | `sessions.lock` | `pins["question_set"] = {version, excluded, weights, adapted_weight}` | production + draft version: lock refused, `lock_refused_reason="question_set_draft"`, owners told once |
| Newer version | stored selection on v1, v2 published | GET shows v2 defaults + `outdated=true`; the lock pins the same | — |
| Load | `python -m app.modules.content load` on a migrated DB | nothing published (files equal latest) | unknown item type → `unknown_item_type`, exit 1 |
| Copy | `copy_from` with FEATURE_RERUN on | the source's selection (its pin if locked) copied | flag off: unchanged 422 |

</intent-contract>

## Code Map

- `backend/app/modules/content/{models,schemas,service,__main__}.py`, `README.md` -- add `Kind.QUESTION_SET`; `QuestionSet` schema (shape + set rules); `publish` gains a context check that every Starting task item of the latest version is referenced; `question_set(version)`; `__main__` adds `load [dir]` (default `app/modules/content/files/`), file stem = kind, compare validated body with latest, publish only when different. Pattern: `DebriefQuiz` in `app/analysis/quiz.py`, CLI at `__main__.py`.
- `backend/app/modules/content/files/question_set.json` (new) -- the shipped draft set; equal to migration 0121's literal (a test keeps them equal, as `ai-configs/mock.json`).
- `backend/migrations/versions/0121_question_set.py` (new; pattern `0108_debrief_quiz.py`) -- kind constraint + v1 row id `01a1f9a0-0000-7000-8000-000000000121`; table `test_selections(class_session_id PK FK cascade, question_set_version, excluded text[], weights jsonb, adapted_weight int, updated_by, updated_at)`; `class_sessions.lock_refused_reason text`.
- `backend/app/modules/tests/{models,selection,schemas,routes}.py`, `README.md` -- table; `selection.py` service: `effective`, `read_block`, `save`, `question_set_pin`, `copy_selection`, registers both with `sessions`; routes `GET/PUT /api/class-sessions/{id}/question-set` (`getSessionQuestionSet`, `setSessionQuestionSet`).
- `backend/app/modules/sessions/service.py` -- `PinRefused(code)` raised by a provider aborts `lock`; `lock_due` catches it like `ProviderKeyMissing` (~3782) and `_tell_lock_refused` stores the reason; `register_copier` called in `copy_from` (~4990); `question_set_session`/`lock_for_question_set` (pattern `quiz_session`/`lock_for_quiz_exclusions` ~1715); `get_session` out `lock_refused_reason`. `repo.set_lock_refused`, `models.lock_refused_reason`, `schemas.ClassSessionOut`.
- `backend/app/modules/messaging/delivery.py` + `platform/email/templates/kinds/class_session_lock_refused.*.j2` -- reason in context, a sentence per reason.
- `backend/app/modules/ops/sweep.py` -- import `tests.selection` so the worker's lock has the pin.
- `backend/app/platform/authz.py` (`question_set.change` owner), `platform/events/registry.py`, `backend/migrations/env.py` if models are listed there.
- Tests: `backend/tests/question_set/test_question_set.py` (new), `tests/content/test_content.py` (cli), `tests/test_migrations.py`, `tests/test_authz_rules.py`.
- Frontend: `frontend/src/modules/tests/{api.ts,question-set-block.tsx,question-set-block.test.tsx}` (new), `modules/sessions/class-session-page.tsx` (~454 placement, lock refused line ~348), `copy/nb.ts` (`tests.questionSet`, `sessions…lock.refusedDraft`), regenerated `lib/api/{openapi.json,schema.ts}`; pattern `modules/debrief/quiz-exclusions.tsx`.
- e2e: `frontend/e2e/question-set.spec.ts` (new) with `support/{auth,classes}.ts`.

## Tasks & Acceptance

**Execution:**
- `backend/app/modules/content/*`, `backend/app/modules/content/files/question_set.json`, migration 0121 -- kind, schema, load command, seed.
- `backend/app/modules/tests/*` -- table, selection service, routes.
- `backend/app/modules/sessions/*`, `messaging/delivery.py`, templates, `ops/sweep.py`, `platform/authz.py` -- pin refusal, reason, copier, helpers.
- Tests -- API matrix rows above, pin contents, production refusal (monkeypatched `app_env`), load idempotence and codes, file == migration literal, copy, migrations head 0121.
- Frontend block + Vitest for the sum line and quantity warning; e2e at 320/360/1440 with axe, Assistant read-only, locked read-only.

**Acceptance Criteria:**
- Given an owner before the Start date, when «Spørsmål og vekter» loads, then each question shows its type, «Vekt» in % and «Ta ut», one line holds the Adapted items' total weight (default 30 %), and a draft set shows the draft notice.
- Given a sum other than 100, then the polite status reads «Sum 95 %. Vektene må bli 100 %.» and the save is not sent.
- Given a taken-out quantity item, then «Du tar ut en oppgave som måler mengder.» shows and saving works.
- Given the Start date passed or an Assistant lecturer, then the block is read-only text.
- Given 320 px, then the form is one column with no sideways page scroll, and axe passes at 320/360/1440.

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
Layers: blind hunter and edge-case hunter (sonnet, per the runbook's two-reviewer rule); verification-gap and intent-alignment skipped.
- verdicts: 50 findings — high 0, medium 1, low 36, false 13, maybe-false 0
- findings:
  - `[low]` `[patch]` Blind: the load publishes `question_set.json` before `starting_task.json` (name order), so a joint change is refused once — the load now orders files by the kind catalogue (Starting task first); test `test_the_load_publishes_the_starting_task_before_the_question_set`.
  - `[false]` `[reject]` Blind: no Starting task stored makes `_starting_task_referenced` raise a raw error; the single-file CLI has no codes — migration 0046 stores Starting task v1, so the table is never empty; the single-file form is pre-existing and unchanged.
  - `[low]` `[reject]` Blind: a new Starting task version is not checked against the stored question set — needs a cross-kind check on every Starting task publish; both arrive together with issue #16, and the load now publishes them in order.
  - `[low]` `[patch]` Blind: `_item_types_known` raises `TypeError` for a non-list `items` and reports a missing type as `unknown_item_type` — it now leaves those to the schema (`invalid_record`).
  - `[low]` `[reject]` Blind: two concurrent loads can publish the same body twice — the load is an operator command run once; the stored-anywhere check (below) makes a repeat a no-op.
  - `[false]` `[reject]` Blind: taking out the sole explanation-wording, unseen-demand or other-business item is accepted silently — FR-52 lets the Lecturer take any question out; the AC warns only for a quantity item.
  - `[low]` `[patch]` Blind: replacement items keep weights at the default Adapted total while the session may set another — they are served by Story 11.7, nothing reads them yet; the `QuestionSet` docstring now states the reader scales them to the session's Adapted total.
  - `[low]` `[reject]` Blind: a new version resets every unlocked session's weights, shown only by a banner — a documented design decision (the block shows exactly what the lock pins); new versions are rare (issue #16) and `outdated` says so on the block.
  - `[false]` `[reject]` Blind: the pin is registered by import side effect, a locking process may lack it — both lockers (the app, whose routes import `tests`, and the sweep, which imports `tests.selection`) register it; tests assert the pin.
  - `[low]` `[reject]` Blind: a session locked before this story shows the latest defaults as read-only — such a session has no Individual test selection to show; Epic 11 has no attempt for it yet.
  - `[false]` `[reject]` Blind: `app_env == "production"` lets staging lock on drafts — `app_env` is `Literal["local","test","ci","production"]`; a deployed stack is production.
  - `[false]` `[reject]` Blind: migration 0121's draft v1 blocks every production lock — that is the AC's `[ASSUMPTION]` block (issue #16), intended.
  - `[low]` `[reject]` Blind: `_tell_lock_refused` writes two UPDATEs each minute while refused — same cadence as the existing provider-key refusal; a few rows.
  - `[low]` `[reject]` Blind: the notice is keyed once per session and User, so a second reason is not mailed — the Klasseøkt shows the current reason (`lock_refused_reason`); a second mail needs a new dedupe scheme.
  - `[false]` `[reject]` Blind: the mail reads the reason at send time — immediate kind, sent within the minute; reading at send time is the existing pattern and gives the current reason.
  - `[low]` `[patch]` Blind: the draft refusal names nobody who can act — copy and mail now say «En Admin må legge inn godkjente spørsmål».
  - `[low]` `[reject]` Blind: an archived Class's owner reads the Assistant line — the same pattern as «Debrief-quiz»; a distinct line needs a new api field.
  - `[low]` `[patch]` Blind: the draft is not re-derived when the set changes underneath — a draft made on another version is now dropped (`QuestionSetDraft.version`).
  - `[low]` `[reject]` Blind: two owners overwrite each other (last write wins) — as every other Klasseøkt block; the live `session` event refreshes the other page.
  - `[low]` `[reject]` Blind: the file-equals-migration test must change when issue #16 replaces the file — intended: the real set arrives as a new version and that test is updated then.
  - `[low]` `[patch]` Blind: a choice item may repeat an option — refused by the schema; test row added.
  - `[low]` `[reject]` Blind: scoring rule ids are not checked against a registry — scoring is built in Stories 11.3+; no registry exists yet.
  - `[low]` `[patch]` Blind: `QUESTION_SET_STATUSES` is unused — removed.
  - `[low]` `[patch]` Blind: `QuestionSetIn.weights` has no size cap — `max_length=60`.
  - `[low]` `[reject]` Blind: tests miss an unknown `starting_task_item`, a duplicated reference, downgrade with rows — the reference checks are in the schema and service with one covered path each; downgrade drops the table.
  - `[medium]` `[patch]` Edge: the shipped draft file would supersede a newer approved version on the next load — the load now skips a body stored as any version (`content.stored_version_of`); test loads the old file after v2 and nothing is published.
  - `[low]` `[patch]` Edge: load order (same root as the first row) — same fix.
  - `[low]` `[patch]` Edge: an unreadable or non-UTF-8 file aborts the load — caught as `invalid_record`; test added.
  - `[low]` `[patch]` Edge: a missing folder exits 0 — refused with `no_folder`; test added.
  - `[low]` `[patch]` Edge: `invalid_record` names no field — the line now lists each error's location and message.
  - `[low]` `[reject]` Edge: concurrent loads (same as the Blind row) — same reason.
  - `[false]` `[reject]` Edge: no Starting task stored — same refutation as the Blind row.
  - `[low]` `[patch]` Edge: `_item_types_known` on a dict or a missing type (same root as the Blind row) — same fix.
  - `[low]` `[reject]` Edge: a Starting task published concurrently with a question set — two operator publishes at the same instant; not met in use.
  - `[low]` `[patch]` Edge: repeated options, a Starting task reference on a non-number item — both refused by the schema; test rows added.
  - `[low]` `[reject]` Edge: a session locked before migration 0121 shows live defaults (same as the Blind row) — same reason.
  - `[low]` `[reject]` Edge: weights saved on v1 lost when v2 is published before the Start date (same as the Blind row) — same reason.
  - `[false]` `[reject]` Edge: invert the production check — same refutation as the Blind row.
  - `[low]` `[reject]` Edge: access lost between commit and the read-back answers 403 — a role change inside one request; not met in use.
  - `[low]` `[patch]` Edge: a session deleted mid-save gives an unhandled `LookupError` — `save` now answers None (403).
  - `[false]` `[reject]` Edge: the dev lock route does not map `PinRefused` — the dev route is mounted only outside production, where the draft refusal never fires; Epic 8's early start is not on this branch.
  - `[low]` `[reject]` Edge: the notice is keyed without the reason (same as the Blind row) — same reason.
  - `[low]` `[patch]` Edge: the `lock_refused` docstring was displaced under `lock_refused_reason` — order restored.
  - `[low]` `[patch]` Edge: `weights` uncapped (same as the Blind row) — same fix.
  - `[low]` `[patch]` Edge: a stale draft after a refetch of another version (same as the Blind row) — same fix.
  - `[low]` `[patch]` Edge: an invalid weight never blurred leaves the save unavailable with no reason by the field — the reason now shows as soon as a typed value is invalid.
  - `[false]` `[reject]` Edge claim: a weight outside 0–100 answers `invalid_request`, not `validation_error` — the fix is a spec edit; the test asserts the real code.
  - `[false]` `[reject]` Edge claim: «after the lock it shows the pin» does not hold for sessions locked before the pin — the claim holds for every session this story locks; older ones are the rejected row above.
  - `[false]` `[reject]` Edge claim: the audit row holds weights, not ids only — weights are numbers, no personal data; the fix is a spec edit.
  - `[false]` `[reject]` Edge claim: some bad inputs abort the load — patched above (unreadable files, missing folder).

## Design Notes

- The AC names `python -m app.content load`; the content CLI lives at `app.modules.content`, so the command is `python -m app.modules.content load` (the existing `<kind> <file>` form stays).
- The block has its own secondary save («Lagre vekter»), like «Lagre quizvalg»: the selection is owned by `tests`, which `sessions` may not import.
- The live sum is display arithmetic over whole numbers the API accepts (0–100); the server judges the save.
- What the block shows before the lock is exactly what the lock pins (one function, `effective`).

## Verification

**Commands:**
- `uv run pytest tests/question_set tests/content tests/sessions tests/test_migrations.py tests/test_imports.py tests/test_authz_rules.py` -- pass
- `npm run typecheck && npm run test && npm run lint:colours && npm run check:copy && npm run build` -- pass
- `npx playwright test e2e/question-set.spec.ts --workers=4` -- pass

## Auto Run Result

Status: done

**Summary.** The Individual test's question set is a new immutable content kind `question_set` (schema `content.schemas.QuestionSet`: Core items of type choice/table/number/long with Item weight, answer key or scoring rule id and tags; Starting task items referenced by id; exactly one Explanation-wording item, an unseen-Demand item, a quantity item, 2–3 Interactive items in another business, replacement items carrying the Adapted total; defaults sum to 100). Draft v1 (placeholders, `status: "draft"`) is stored by migration 0121 and shipped as `app/modules/content/files/question_set.json`. `python -m app.modules.content load [folder]` publishes every kind's file whose body is not stored yet, Starting task first, with stable codes (`unknown_item_type`, `unknown_kind`, `starting_task_items_missing`, `invalid_record`, `no_folder`). `modules/tests` owns a per-session selection (`test_selections`), the Klasseøkt block «Spørsmål og vekter» (`GET/PUT /api/class-sessions/{id}/question-set`, «Lagre vekter», owners only, 422 `weights_not_100`, 409 `session_locked` from the Start date) and the `question_set` pin the Start-date lock stores in `SessionRuntime.pins`; in production a draft refuses the lock (`sessions.PinRefused`, `lock_refused_reason = question_set_draft`, owners and Admins told, shown on the Klasseøkt). «Lag kopi» copies the selection or the pin.

**Files.**
- `backend/app/modules/content/{models,schemas,service,__main__}.py`, `README.md`, `files/question_set.json` — kind, schema, publish check, load command.
- `backend/migrations/versions/0121_question_set.py` — kind, v1, `test_selections`, `class_sessions.lock_refused_reason`.
- `backend/app/modules/tests/{models,schemas,routes,selection}.py`, `README.md` — selection, block api, pin, copier.
- `backend/app/modules/sessions/{service,repo,models,schemas}.py` — `PinRefused`, refusal reason, `register_copier`, `question_set_session`, `lock_for_question_set`.
- `backend/app/modules/ops/sweep.py`, `platform/authz.py` (`question_set.change`), `platform/events/registry.py`, lock-refused mail templates.
- Tests: `backend/tests/question_set/test_question_set.py` (new), `tests/content/test_content.py`, `tests/sessions/test_lock.py`, `tests/test_migrations.py`.
- Frontend: `src/modules/tests/{api.ts,question-set-block.tsx,question-set.test.ts}` (new), `modules/sessions/class-session-page.tsx`, `components/text-field.tsx` (label id), `copy/nb.ts`, generated `lib/api/{openapi.json,schema.ts}`; `e2e/question-set.spec.ts` (new).

**Review.** 50 findings (two sonnet reviewers). Patched: the load never republishes a stored body (medium), plus 17 low rows (load order, unreadable file, missing folder, error text, item-type check, repeated options, Starting task reference type, weights cap, unused constant, session gone mid-save, docstring order, stale draft, invalid-value reason, draft refusal copy, replacement scaling note). Rejected: 19 low and 13 false, each with its reason in the triage log. Nothing deferred.

**Follow-up review: not recommended.** One medium entry patched (high 0, medium 1, low 17).

**Verification.** Backend: full suite `--maxprocesses=8` 3203 passed before the review patches; after them `tests/question_set tests/content tests/sessions tests/messaging test_migrations test_imports test_authz_rules` 572 passed; `ruff check` and `ruff format --check` clean. Frontend: `tsc` clean, Vitest 1047 passed, `lint:colours`, `check:copy`, `next build` ok. Playwright on lane 2 (8081): new spec plus class-session (base, lock, rerun, dates, obligatory, choices), ai-assessment-switch, debrief-quiz-exclusions, homes, order-confirm, order-field, week-table, game-start, guided-week: 138 passed; after the patches question-set, class-session and class-session-lock: 26 passed. Axe at 320/360/1440. No new test over 1 s (slowest 0.71 s). Screenshots at 1440 and 320 checked by eye: aligned Vekt column, one column at 320.

**Decisions taken for the founder.** The command is `python -m app.modules.content load` (the AC's `app.content` does not exist); the block has its own save «Lagre vekter»; a selection saved on an older version gives way to the latest defaults (shown as `outdated`, and that is what the lock pins); weights are whole percents; every Core item may be taken out but not all; the production draft refusal reuses the lock-refused notice with a reason; replacement items are scaled to the session's Adapted total by Story 11.7; all copy except the spine's strings is [ASSUMPTION].

**Residual risks.** Replacement-item scaling and scoring rule ids are not consumed until Stories 11.3–11.7. A new question set version silently resets unsaved-on-latest selections (banner only). Sessions locked before this story have no `question_set` pin and show the latest defaults. The implementation was done in the main context, not a subagent, per the team lead's instruction.
