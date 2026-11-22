# Epic 11 Context: Individual test

<!-- Generated from planning artifacts. Regenerate with compile-epic-context if planning docs change. -->

## Goal

A Student who has completed the Replay can open the Individual test, answer multiple-choice, Interactive (table/number), long-answer and Adapted items over several evenings with autosave, and submit once; saved answers are submitted automatically at the Test deadline. A Lecturer can review the question set and Item weights, preview Adapted item templates, edit the Scoring guide, require one timed sitting and extend one Student's deadline. The test produces no grade and no right/wrong feedback in v1; scoring is stored for the later AI assessment (Epic 12).

## Stories

- Story 11.1: Review the question set and Item weights
- Story 11.2: Edit the Scoring guide for a Class session
- Story 11.3: Open the Individual test with the own-work statement
- Story 11.4: Answer multiple-choice items with autosave
- Story 11.5: Answer table and number Interactive items
- Story 11.6: Write long answers with autosave
- Story 11.7: Get Adapted items from my own game and Replay
- Story 11.8: Read Adapted items in natural wording
- Story 11.9: Preview the Adapted item templates with a sample Student
- Story 11.10: Review and submit the Individual test
- Story 11.11: Have saved answers submitted automatically at the Test deadline
- Story 11.12: Require one timed sitting
- Story 11.13: Extend one Student's Test deadline
- Story 11.14: Answer drawn Interactive items in a graph (after the rehearsal, may be skipped for the pilot)

## Requirements & Constraints

- The test opens only after the Replay step is complete and stays open until the Test deadline (default 7 days after the Debrief deadline). The Student states the work is their own before any item is served. No retakes; one submit.
- Question set: Norwegian; Item weights always sum to 100%; Lecturer may exclude questions and change weights before the Start date (read-only afterwards). Taking out a quantity item warns but does not block. Must include: the Starting task items (referenced, not copied), exactly one item using the Explanation's wording, one item on an unseen Demand pattern, quantity items, and 2-3 Interactive items set in a non-beer business. No diagram item type in v1.
- Adapted items: same templates for every Student, filled from that Student's own game and Replay facts; every cited fact must match the Decision log; fixed total weight per Class session (default 30%); a Student with fewer than 10 own Orders (counted via `decided_by = student`) gets replacement Core items of equal weight.
- Interactive items: scored by computed rules on quantities and consistency (units added equal units missing; stock agrees with flows), partial credit per coded criterion, never on whether the answer looks like oscillation; students are told these are hard; keyboard and screen-reader operable via the table; use "enheter", never "øl". Table and number entry first; drawn items (11.14) optional and nothing depends on them.
- Scoring guide: per long-answer question and Adapted template, 5-8 coded criteria, one fixed five-step scale; Lecturer edits only the descriptive text (criteria read-only); editable until the original Test deadline; the version in force at the deadline scores the whole Class session; a guide not checked by a Control test shows "Ikke kontrollert med en Kontrolltest." (Epic 12 owns the `checked` record).
- Optional one-sitting mode with a time limit (range is configuration); time factor from per-Student adjustments extends it; per-Student deadline extensions move Debrief and Test deadlines together.
- Real question texts and the default Scoring guide are a non-code deliverable (issue #16): ship clearly marked `draft` placeholder items only; never invent real question text in code. In production a Class session cannot be locked while its question set is a `draft` version (assumption pending founder confirmation).
- No answer text in logs (structlog JSON, ids only). No right/wrong state or explanation shown to the Student before the AI assessment. No LLM call for long answers in this epic.
- Every screen: Playwright at 320/360/1440 px with axe; copy only from `frontend/src/copy/nb.ts`; Norwegian strings given in the epic are exact where quoted.

## Technical Decisions

- Ownership: `backend/app/modules/tests/` and `frontend/src/modules/tests/` (layout `routes/service/repo/models/schemas/jobs`; other modules import only `service.py`; `tests` owns `test_attempts` and `answers`). Question set, Adapted item templates and Scoring guide are new immutable versioned record types in `modules/content` (edit creates a new version), loaded from repo files by `python -m app.content load` (idempotent; rejects unknown item types with a stable error code; `drawn` is unknown until 11.14). Computed scoring goes into the existing shared `backend/app/analysis/scoring.py` (`score_choice`, `score_interactive`) as pure functions, never a second copy and never in the web app. Units are integers.
- Pinning (AD-23, AD-4): `sessions.lock` pins question set version and selection at the Start date; `sessions.lock_test` (added in 11.11) pins the Scoring guide at the original Test deadline (and later also the AI-assessment switch, added by Epic 12); both via the pinned-versions map in Epic 5's `SessionRuntime`. Scored answers store the versions used. `content.service.is_checked(scoring_guide_version_id, model_config_id)` always returns false here, with no table.
- Write path: `tests.commands` is the only writer of attempts and answers: `open_attempt`, `save_answer`, `submit`, `close_attempt`, `extend_deadline`, plus `end_sitting` (11.12). Every command on an existing attempt takes `SELECT ... FOR UPDATE` on the attempt row in one transaction. `test_attempts` (unique on User and Class session; pinned set version/selection, frozen ordered item list, `effective_deadline`, status `open`/`submitted`/`auto_submitted`, `sitting_ends_at`) and `answers` are created by 11.3. Stable error codes (API errors are `{"error": {"code", "message", "fields"}}`, web maps codes to Norwegian): `attempt_submitted`, `test_deadline_passed`, `sitting_ended`.
- Autosave (AD-10): per-answer revision rising by one per change; server keeps the highest revision and returns the stored one without error otherwise; client keeps unsent input in `frontend/src/lib/drafts.ts` (localStorage, keyed by User and item, cleared on logout) and retries; a retried save after submit gets `attempt_submitted` and the draft is dropped. Free-text answers are personal data keyed by `user_id` and Class session, removed by the retention routine.
- Deadlines (AD-9): `effective_deadline` is only the Class session's Test deadline or the Student's extension, never earlier. `ops.sweep` (one item per transaction, ids only, idempotent) first runs `sessions.lock_test`, then `tests.close_attempt` per due attempt; `close_attempt` submits still-open attempts and is the single place Epic 12 later defers the AI assessment. `end_sitting` submits a timed attempt early but starts nothing else. `tests.rules.answering_ends_at(attempt)` returns the earlier of `sitting_ends_at` and `effective_deadline`; clocks use the API's `server_now`; times are UTC, shown in Europe/Oslo. Extensions live in a per-Student row owned by `modules/sessions`; extend the existing `sessions.service.effective_test_deadline` and `effective_debrief_deadline` (no second function), audited via `platform/audit`, `user:<id>` emitted.
- Adapted items: built from code in the same transaction as `open_attempt` from stored fact sets via `games.facts.get_or_create` and `games.service.student_game`; frozen on the attempt and never change afterwards. Optional wording (11.8) via the idempotent `tests.prepare_adapted(user_id, class_session_id)` job on `llm-batch` (worker-batch), found by `ops.sweep`; `ai.run` purpose `adapted_item_wording`, output schema references fact and sentence-template ids only, checked by the AI-text validator (9.14) against the item's `fact_set_id`; code-rendered text is the fallback; text travels as `{text, ai_generated, llm_call_id}`; LLM text carries the prefix "KI-generert, kan ta feil:". Opening never waits on an LLM. No names reach the LLM (scrubbed by the gateway). The Lecturer preview (11.9) uses a static sample fact set built from a golden Decision log fixture, no Game row, no LLM.
- Integration: gate via `progress.has_step(..., replay)`; submit and auto-submit call `progress.record_step(test_submitted)`, which emits `session:<id>` and `user:<id>` (registered topics only, in `platform/events/registry.py`, asserted by an api test); `open_attempt` calls `close_follow_up` in `debrief/service.py` in the same transaction; `reminder_recipients` excludes submitted Students and Students with their own deadline; per-Student reminders go through `platform/notify.enqueue` as the `digest` kind (at most one mail per day, none 22:00-07:00) with a dedupe key of user id, deadline kind and deadline time. Under `FEATURE_RERUN`, selections, scoring guide version and sitting settings are copied via `sessions.service.copy_from` (Story 5.18).
- Authorization through `platform/authz` policies and scoped queries (no `if role ==` in modules): Student reaches only own attempt, Admin none without Class membership, denied requests do not reveal existence; Assistant lecturer reads but never edits question set, Scoring guide or extensions.
- Frontend (AD-10): API client generated from OpenAPI; no scoring or business rules in the browser; reuse components from earlier epics (Quizvalg, Starting task item, Tekstfelt, Bryter, Skjelett, Ordrefelt error pattern); the Interaktiv oppgave component is built so 11.14 can add a graph (from `frontend/src/components/charts`, fixed width) over the same table.

## UX & Interaction Patterns

- Lecturer blocks on the Klasseøkt screen: "Spørsmål og vekter" (live sum, "Sum 95 %. Vektene må bli 100 %.", saving blocked; draft notice) and "Sensorveiledning" (one Tekstfelt per question, marked "Standard" or "Endret"), plus a time-limit setting that uses Bryter and Tekstfelt. Form is one column at 320 px.
- Student flow: Stegene on Hjem shows the locked step "Individuell test, åpnes når du har fullført Replay."; own-work statement with one effect-labelled primary button; statement not asked again on return; autosave indicator "Lagret 21:14" (Europe/Oslo, announced politely, no focus move); failure message "Ikke lagret. Svarene ligger på denne enheten, og vi prøver igjen."
- Value table: HTML `<table>` with `th` scopes, one numeric cell per Uke, "Ikke besvart" beside empty rows, "Skriv et helt tall." on leaving an invalid cell; scrolls in its own region with sticky label column at narrow widths. Long answers show larger-screen advice on phones.
- Submit: review lists unanswered items as links, one primary button "Lever testen", no extra confirmation dialog; after submit "Levert ... Du kan ikke endre svarene." with focus on it, answers read-only. Submit failure: inline "Det ble ikke lagret. Prøv igjen." with `role="alert"`. Deadline states: auto-submitted and never-opened messages.
- Timed sitting: "Tid igjen 38 min" fixed at the top, in text, not announced on each change, one polite "5 minutter igjen" announcement (draft copy).
- All interactive controls: 44 px tap targets, keyboard operable; drawn graph (11.14) uses per-Uke `role="slider"` points with the table as the screen-reader answer.

## Cross-Story Dependencies

- 11.3 defines the commands and tables that 11.4, 11.5, 11.6, 11.7, 11.10, 11.11, 11.12 and 11.13 extend; 11.4's `save_answer` path is reused by 11.5, 11.6 and Adapted items (answered as long answers).
- 11.1 defines the question set record, content load command and selection stored with the Class session that 11.3, 11.7 and 11.9 read; 11.7 and 11.9 use the Adapted total weight and replacement items from 11.1; 11.8 builds on 11.7; 11.14 builds on 11.5 and nothing depends on it.
- 11.11 adds `sessions.lock_test` and `close_attempt` behaviour; 11.12's `end_sitting` and 11.13's extension must stay consistent with it; 11.2's guide pinning happens through 11.11.
- Depends on earlier epics: Epic 5 (`SessionRuntime`, `sessions.lock`, effective deadlines, reminders, `copy_from`), Epic 6 (`modules/content`, Starting task items, `analysis/scoring.py`, `student_game`), Epic 8 (Studentside, adjustments), Epic 9 (fact sets, `close_follow_up`, Quizvalg, AI-text validator), Epic 10 (Replay step), Epic 2 (model config command, `ai.run`), Epic 3 (Skjelett).
- Epic 12 consumes this epic: `close_attempt` starts the AI assessment, `lock_test` also pins its switch, and Epic 12 writes the `checked` record read by `is_checked`; Epic 13 reads which required parts have content through `tests.service`.
