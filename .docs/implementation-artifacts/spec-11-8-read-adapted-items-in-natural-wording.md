---
title: 'Story 11.8: Read Adapted items in natural wording'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: '44f171284ef3e65420b3da3f7c4ef5fbc1035d91'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-11-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-11-7-get-adapted-items-from-my-own-game-and-replay.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** Adapted items are always the code-rendered template text: no LLM ever words them, so the Deferred item "Timing of Adapted items" is open, and nothing marks an AI-worded item (FR-53, FR-34, AD-6, AD-7, AD-9).

**Approach:** The sweep defers an idempotent `llm-batch` job per Student who has the `replay` step but no attempt and no prepared set; the job builds the 11.7 items, asks `adapted_item_wording` to choose one of the template's approved wordings for each Adapted item (template id + fact id only), validates and stores one prepared set; `open_attempt` freezes the prepared set when one exists, else builds as in 11.7. The page marks AI text with «KI-generert, kan ta feil:» and `data-ai-generated`.

## Boundaries & Constraints

**Always:**
- Wordings are content: `adapted_templates` v2 (migration 0126, `files/adapted_templates.json` == its literal) gives each template `wordings` (0–4 `{id, text}`; ids unique across the whole record incl. template ids; each text under the same rules as the template text: plain slots of its fact kind, its key values, no `!`). v1 stays valid (`wordings` default empty). Wording texts are `Utkast:` placeholders (issue #16).
- Due action `tests.prepare_adapted` in `ops.sweep.DUE_ACTIONS` (after `debrief.narration`): finds `(user_id, class_session_id)` with the `replay` step recorded within `PREPARE_WINDOW` (30 days), no `test_attempts` row and no prepared row, at most 50; act defers task `tests.prepare_adapted(user_id, class_session_id)` on `llm-batch`, queueing lock `adapted:<user>:<session>`, ids only.
- Job (`tests.prepare.prepare`): nothing when an attempt or prepared row exists. Reads the pins and selection (as `_frozen`), builds via `adapted.build` (now also exposing the facts sets it used, keyed by `fact_set_id`), outside any transaction during calls. For each Adapted item whose template has wordings, when the pinned `debrief_ai_text` switch is on (`enabled`, model config): one `app.ai.text.worded("adapted_item_wording", BudgetScope.class_session(session, effort_level, model_config_id), …)` with output `narration.AiTextOutput`, mock answer = the template's first wording with the item's fact id, fallback = the code text. Accepted → item `text` = `{text, ai_generated: true, llm_call_id}`; else unchanged. Then insert the prepared row once (`ON CONFLICT DO NOTHING`), and not at all when an attempt appeared meanwhile. Never retries a call.
- Validator `analysis.adapted.validate_wording(output, template, facts, pattern_names, fact_ids) -> narration.Verdict` (the 9.14 validator's rules and reasons on Adapted facts): exactly one sentence; `fact_ids` equal the item's frozen ones (`unknown_fact`); `template_id` one of the template's wordings (`unknown_template`); rendered by the code from the same values as `fill`; every number in the text one of the values' numbers (`number_outside_facts`). Facts are the set whose id is the item's `fact_set_id`.
- Table `test_prepared_items(user_id FK users CASCADE, class_session_id FK class_sessions CASCADE, PK both, question_set_version int, adapted_weight int, items jsonb, prepared_at timestamptz default now())`, written only by `tests.prepare`, never updated. `open_attempt` uses its `items` in place of `adapted.build` when `question_set_version` and `adapted_weight` equal the chosen selection's, in the same transaction.
- Purpose `adapted_item_wording` (attempt_limit 1, not a player), prompt `app/ai/prompts/adapted_item_wording/v1.md` locked in `hashes.json`, `seed.MOCK_SPEC` and `ai-configs/mock.json` name it (the seed derives a new config row, Story 2.2 `config.derive`).
- Frontend: an Adapted item with `wording.ai_generated` shows its label as `nb.debrief.aiText(text)` with `data-ai-generated="true"` on the item's field wrapper and the `aiNote` hint; code text carries neither.

**Never:** No LLM call while opening; no change to a frozen attempt; no LLM-written word or number; no retry; no answer or item text in logs; no new switch (the Debrief AI-text pin gates it); no change to the demo Class.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Prepared then open | job ran, AI on | attempt items == prepared items, Adapted `ai_generated: true`, `llm_call_id` set | — |
| Rejected wording | mock answers unknown wording / fact | code text kept, `ai_generated: false` | log reason only |
| Typed failure | `mock.outage()` | code text kept, prepared row still stored | — |
| AI off / v1 templates | pin disabled or no wordings | prepared set with code items, no `llm_call` | — |
| Job after open | attempt exists | no call, no prepared row; attempt unchanged | — |
| Prepared after open race | attempt inserted during calls | prepared row not stored; attempt unchanged | — |
| Sweep twice | same minute | one waiting job (queueing lock) | — |
| Replacement path | few Orders | prepared set = replacement items, no call | — |
| Selection mismatch | prepared `adapted_weight` ≠ chosen | `build` as in 11.7 | — |

</intent-contract>

## Code Map

- `backend/app/analysis/adapted.py` -- add `Wording`, `AdaptedTemplate.wordings`, record-wide id uniqueness, `values(template, facts, pattern_names) -> (fact_ids, values)` shared by `fill` and `render_wording`, `validate_wording` (reuse `narration.Verdict`, `AiTextOutput`).
- `backend/app/modules/content/files/adapted_templates.json`, `backend/migrations/versions/0126_adapted_wording.py` (new) -- v2 record `01a1f9a0-0000-7000-8000-000000000126`, table `test_prepared_items`.
- `backend/app/modules/tests/adapted.py` -- `build` keeps its signature; new `build_with_sets` returns `(items, {fact_set_id: StoredFactSet})`.
- `backend/app/modules/tests/models.py` -- `test_prepared_items`.
- `backend/app/modules/tests/prepare.py` (new) -- `PREPARE_TASK`, `PURPOSE`, `due_prepares`, `prepare_due`, `prepare`, `prepare_key`.
- `backend/app/modules/tests/jobs.py` (new) + `app/platform/jobs/__init__.py` `TASK_MODULES` -- the task.
- `backend/app/modules/tests/commands.py` (`_frozen` ~115) -- `_selection` factored out; prepared items used when matching.
- `backend/app/modules/progress/service.py` -- `steps_since(session, step, since)`.
- `backend/app/modules/sessions/service.py` -- `locked_pins(s, class_session_id)` (repo.session_pins).
- `backend/app/modules/ops/sweep.py` -- due action.
- `backend/app/ai/{purposes.py,seed.py,prompts/adapted_item_wording/v1.md,prompts/hashes.json}`, `backend/ai-configs/mock.json`.
- `backend/app/modules/tests/README.md` -- section.
- Tests: `tests/individual_test/test_prepare.py` (new; stand-ins of 11.7 `stand_in`, `locked_with`); `tests/analysis/test_adapted.py` (wordings rules, validate_wording); update `test_adapted.py` (v2 is latest; shipped file == v2), `tests/sessions/test_lock.py` if it asserts v1, `tests/test_migrations.py` (head 0126, table), `tests/ai/{conftest,test_prompt_files}.py`, `tests/test_worker.py`.
- Frontend: `src/modules/tests/long-item.tsx` (AI label + mark), `e2e/individual-test.spec.ts` (marked item at 360/1440 + axe), Vitest if a pure helper is added; regenerate api only if the schema changes.

## Tasks & Acceptance

**Execution:**
- Content, analysis, migration 0126 -- wordings and the validator.
- Tests module: models, adapted, prepare, jobs, commands; progress, sessions, sweep, jobs registry; AI purpose, prompt, seed, mock.
- Backend tests for every matrix row.
- Frontend marking and e2e.

**Acceptance Criteria:**
- Given a prepared set with an accepted wording, when the Student opens the test, then the frozen Adapted item carries the chosen wording's code-rendered text with `ai_generated: true` and the `llm_call_id` of a `llm_call` row with purpose `adapted_item_wording` and scope the Class session.
- Given an opened attempt, when the job runs again or finishes late, then the attempt's items are byte-equal to before.
- Given an AI-worded Adapted item at 360 and 1440 px, then its label starts «KI-generert, kan ta feil:», the wrapper has `data-ai-generated="true"`, and axe passes; a code-rendered item has neither.

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
Layers: blind hunter, edge-case hunter, verification gap and intent alignment (sonnet; four, since the change adds a table, a migration, a sweep action, a job and a race with the open). This spec was left out of the review diff.
- verdicts: 33 findings — high 0, medium 1, low 26, false 6, maybe-false 0
- findings:
  - `[low]` `[reject]` Blind: `due_prepares` reads every `replay` step of 30 days and binds them all in a tuple `IN` — the parameter limit needs about 16 000 Students through the Replay in 30 days; the pilot has a few Classes. An anti-join in SQL would make `tests` read `progress_steps` (module boundary).
  - `[low]` `[reject]` Blind: a Student whose job always raises is deferred every minute and can fill the oldest-first batch of 50 — `build_with_sets` turns every Game or facts failure into replacement items and `worded` never raises; no raising path was shown. A failure counter is new state.
  - `[low]` `[patch]` Blind: a set prepared with replacement items for a passing reason (`no_game`, `no_replay`, `facts_unavailable`) was frozen for good — `adapted.PASSING_REASONS`; `_prepared` ignores such a set, so the open builds again; new test `test_replacements_prepared_for_a_passing_reason_are_built_again_at_the_open`.
  - `[low]` `[reject]` Blind: the attempt check and the insert are not atomic, so an open committed in between leaves a prepared row — the row is never read (`open_attempt` returns the existing attempt first); a lock against the open adds contention for no visible effect.
  - `[low]` `[reject]` Blind: `test_prepared_items` holds personal data with no retention — rows go with the User (`ON DELETE CASCADE`) and the Class session; the table is reported for lane 1's personal-data registry (Story 15.2) at merge.
  - `[low]` `[reject]` Blind: the chosen wording id is not stored on the item — the item keeps `llm_call_id`, whose `llm_call` row holds the scrubbed response naming the id; the text itself is stored.
  - `[medium]` `[patch]` Blind: the draft wordings gave the Students different facts (one left out the supply line and backlog), so the choice changed the question (FR-53) — schema rule: a wording uses exactly its template's values; both templates' draft wordings rewritten (two each) and migration 0126's literal regenerated; refusal cases added.
  - `[low]` `[reject]` Blind: the number check only catches digits typed into a wording, and a literal equal to a value's digit run passes — code renders every value, so the check is the 9.14 rule's last guard for content digits; a digit ban in content is a new rule for draft text.
  - `[low]` `[reject]` Blind: `_word` calls the LLM when `picked` is None and for a single wording — `picked` cannot be None (the item was filled from the same set and template); every shipped template has two wordings (tested).
  - `[low]` `[patch]` Blind: errors named a wording a «template» and the repeat error did not say which kind — `_check_text` takes the owner's label; the repeat error says a wording id counts.
  - `[low]` `[patch]` Blind: test gaps — a pattern wording through `validate_wording` (with and without the pattern's name) added; the shipped-wordings test renamed to what it checks. Rejected parts: `enabled_pin` variants (the 9.14/10.7 helper's twin), `steps_since` (run by every sweep test), the batch cap and window edge (constants).
  - `[low]` `[reject]` Blind: `pins` None before the lock makes the job read unpinned versions — the `replay` step only follows the lock; a session locked before the pins existed reads the latest version at each open, as in 11.7.
  - `[low]` `[reject]` Blind: the downgrade deletes version 2 while sessions pin it, and `items` has no array check — the pattern of every content migration (0125); a downgrade is a dev operation; only `tests.prepare` writes the column.
  - `[low]` `[patch]` Blind: the spine's AD-9 list of due actions lacked the new one — added (`tests.prepare_adapted`, Story 11.8).
  - `[low]` `[reject]` Edge: a sweep while the job runs can defer a second one (the queueing lock holds only waiting jobs) — the second finds the prepared row and calls nothing unless both run at once on a worker with concurrency above 1; `llm-batch` runs one at a time in `worker-batch`.
  - `[low]` `[reject]` Edge: failing pairs starve the batch — same as the second Blind row.
  - `[low]` `[reject]` Edge: the tuple `IN` parameter limit — same as the first Blind row.
  - `[low]` `[reject]` Edge: the job may word items for a Student past their Test deadline — the sweep defers within a minute of the `replay` step, days before the deadline; checking the deadline adds a sessions read for a case not met in use.
  - `[low]` `[reject]` Edge: an open between the check and the insert — same as the fourth Blind row.
  - `[low]` `[patch]` Edge: transient replacement reasons frozen — same patch as the third Blind row.
  - `[false]` `[reject]` Edge: a paid call when `picked` is None — unreachable, as in the ninth Blind row.
  - `[low]` `[reject]` Edge: the downgrade under pinned sessions — same as the thirteenth Blind row.
  - `[low]` `[reject]` Edge (claim): «not at all when an attempt appeared meanwhile» holds only up to the insert — same as the fourth Blind row; the check runs in the inserting transaction just before it.
  - `[low]` `[patch]` Verification: a pattern template's wording was never validated — new analysis test (Blind test-gap row).
  - `[low]` `[patch]` Verification: the `question_set_version` condition of the prepared lookup was unpinned — the selection test is parametrized over both columns.
  - `[low]` `[reject]` Verification (other): the oldest-first batch with failing jobs — same as the second Blind row.
  - `[false]` `[reject]` Intent: «sentence-template ids» read as the item's own wordings rather than the narration templates — the decision is the spec's (Design Notes): narration templates are Debrief sentences about moments and cannot cite the outcome fact; the wordings are versioned content like them.
  - `[false]` `[reject]` Intent: text marked «KI-generert» though no AI-written word appears — the same marking rule as 9.14 and 10.7, where the LLM also only chooses templates (AD-7, FR-34).
  - `[low]` `[reject]` Intent: the call is gated on the Debrief AI-text pin — recorded as a founder decision; one Lecturer switch for text sent to an AI.
  - `[false]` `[reject]` Intent: the config row comes from the seed, not a command — the seed derives the new row through `config.derive`, Story 2.2's command function, as 9.14 and 10.7 did.
  - `[false]` `[reject]` Intent: the CI list — descriptive; every listed case is covered.
  - `[low]` `[reject]` Intent: Playwright stands the api in — the repo's pattern (11.3–11.7); the api's `wording` is asserted in pytest from a real job and open.
  - `[false]` `[reject]` Intent: the spine's deferred item rewritten — descriptive; the story asks to record the decision.

## Design Notes

- The LLM chooses among approved phrasings of the same question, each with exactly the template's values (a schema rule since review), so every Student still gets the same template (FR-53) and code writes every word and number (AD-7). `narration.validate_ai_text` only knows narration templates and moment/pattern facts; the outcome fact (`outcome:<role>`) needs the Adapted values, so `validate_wording` applies the same rules and verdict reasons to them.
- Reusing the Debrief AI-text pin keeps one Lecturer switch for "text to an AI" (its Off help already says no text goes to an AI).

## Verification

**Commands:**
- `uv run pytest tests/individual_test tests/analysis/test_adapted.py tests/content tests/test_migrations.py tests/test_imports.py tests/ai tests/test_worker.py tests/ops -q` -- pass
- `npm run typecheck && npx vitest run src/modules/tests` -- pass
- `npx playwright test e2e/individual-test.spec.ts --workers=4` -- pass

## Auto Run Result

Status: done

**Summary.** The Deferred item "Timing of Adapted items" is closed. `ops.sweep` gets the due action `tests.prepare_adapted`. It finds each Student whose `replay` step is under 30 days old and who has no attempt and no prepared set (at most 50 a minute), and defers the idempotent job `tests.prepare_adapted(user_id, class_session_id)` on `llm-batch` (lock `adapted:<user>:<session>`, ids only). The job builds the items exactly as opening would (`adapted.build_with_sets`, Story 11.7). When the Class session's pinned Debrief AI-text switch is on with a model config, it makes one `adapted_item_wording` call per Adapted item through `app.ai.text.worded`, with the Class session as budget scope. The output names one of the template's approved wordings and the item's fact id only (`AiTextOutput`). `analysis.adapted.validate_wording` checks it against the facts set whose id the item stores, using the 9.14 verdict reasons, and code renders the text. A rejection or a typed failure keeps the code text, and the call is never retried. The set is stored once in the new table `test_prepared_items`, and not stored when the Student opened the test meanwhile. `open_attempt` freezes the prepared items when they were prepared for the selection it opens on. Replacement items prepared for a reason that may have passed are built again at the open. Without a prepared set, opening builds the code items as before, so it never waits on an LLM call. The wordings are content: `adapted_templates` v2 (migration 0126, the shipped file) gives each template two draft wordings, each with exactly the template's values. The page labels an AI-worded item «KI-generert, kan ta feil: «…»», adds the AI note as its hint and sets `data-ai-generated="true"`, from `wording.ai_generated` only.

**Files.**
- `backend/app/analysis/adapted.py`: `Wording`, `wordings` (same values as the template, ids unique across the record), `picked`, `render_wording`, `validate_wording`.
- `backend/app/modules/content/files/adapted_templates.json`, `backend/migrations/versions/0126_adapted_wording.py` (new): v2 with wordings and the `test_prepared_items` table. `content/README.md`.
- `backend/app/modules/tests/{prepare.py (new), jobs.py (new), adapted.py (build_with_sets, PASSING_REASONS, pattern_names), commands.py (selection_of, _prepared), models.py, README.md}`.
- `backend/app/modules/{progress/service.py (steps_since), sessions/service.py (locked_pins), ops/sweep.py (due action)}`, `backend/app/platform/jobs/__init__.py` (task module).
- `backend/app/ai/{purposes.py, seed.py, prompts/adapted_item_wording/v1.md (new), prompts/hashes.json}`, `backend/ai-configs/mock.json`.
- Tests: `tests/individual_test/test_prepare.py` (new, 10), `tests/analysis/test_adapted.py` (wordings, validator), updated `test_adapted.py`, `test_migrations.py` (head 0126), `tests/ai/{conftest,test_prompt_files}.py`, `test_worker.py`, `content/test_content.py`, `sessions/test_lock.py`, `question_set/test_question_set.py`.
- Frontend: `src/modules/tests/{individual-test.ts (itemLabel), individual-test.test.ts, long-item.tsx}`, `e2e/individual-test.spec.ts` (a marked item at 320/360/1440 with axe). The api schema is unchanged (`wording` exists since 11.7), so the client was not regenerated.
- Docs: `ARCHITECTURE-SPINE.md` (the deferred item closed, the due action listed).

**Review.** Four sonnet reviewers reported 33 findings: high 0, medium 1, low 26, false 6. Seven entries were patched: 1 medium and 6 low. The medium patch makes wordings carry the template's exact values. The low patches are: replacement sets prepared for a passing reason are rebuilt at the open; the error labels; a pattern-wording test; the prepared lookup tested on both columns; a renamed test; and the spine's sweep list. The other 20 low and 6 false findings were rejected, each with its reason in the triage log. Nothing was deferred.

**Follow-up review: not recommended.** Patched: high 0, medium 1, low 6.

**Verification.**
- Backend: the full suite with `--maxprocesses=8` gave 3334 passed and 4 skipped. `ruff check` and `ruff format --check` are clean. The new tests in `test_prepare.py` run 1.0–2.0 s each under parallel load, over the 1 s guideline, because each locks a session through the sweep (as in 11.7).
- Frontend: `tsc` clean, Vitest 1071 passed, `lint:colours`, `check:copy` and `next build` pass.
- Playwright on lane 2 (8081, stack rebuilt with this change): 117 passed across individual-test (with the new AI-marked item at 320/360/1440 and axe), homes, student-home, order-confirm, order-field, week-table, game-start and guided-week.
- The lane's databases at 0126 had 0126 run again after the wording literal changed (downgrade to 0125, upgrade head). No database was dropped.

**Decisions taken for the founder.**
- "Sentence-template ids" are approved per-template wordings in `adapted_templates` v2. The LLM chooses one, and code renders it. Every wording must use exactly its template's values, so every Student gets the same facts. The texts are `Utkast:` placeholders (issue #16).
- The call is gated on the existing Debrief AI-text switch (`debrief_ai_text` pin); there is no new switch.
- One call per Adapted item; the mock answers the first wording.
- Sweep window 30 days, 50 jobs a minute. A prepared set is used only for the same question set version and Adapted total. Replacement sets prepared for `no_game`, `no_replay` or `facts_unavailable` are rebuilt at the open.
- The AI note under a marked item reuses `nb.debrief.aiNote`.

**Personal data.** New table `test_prepared_items` (`user_id`, plus text rendered from the Student's own game's facts) for lane 1's registry. It cascades with the User and the Class session.

**Residual risks.**
- `due_prepares` binds every replay step of 30 days in one query (fine at pilot scale).
- A job that keeps raising would be deferred every minute; no such path is known.
- An open that commits between the job's attempt check and its insert leaves an unused prepared row.
- The implementation was done in the main context, not a subagent, per the team lead's brief.

