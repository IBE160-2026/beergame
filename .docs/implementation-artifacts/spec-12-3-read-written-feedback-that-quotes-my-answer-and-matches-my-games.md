---
title: 'Story 12.3: Read written feedback that quotes my answer and matches my games'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: '39dc046abfd9ee8f163e4ec4f7d60181bce8514c'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-12-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-12-2-get-an-ai-assessment-with-scores-and-a-weighted-total.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** The AI assessment of Story 12.2 gives each long-answer and Adapted item a bare step on the scale: no written feedback, nothing that shows it read the Student's own text or game, and no notice that the Scoring guide is not checked by a Control test (FR-54, FR-34, FR-81, AD-7).

**Approach:** Prompt `assessment/v2` asks, besides the score, for 1–4 feedback sentences built only from approved template ids, character spans over the scrubbed answer, Scoring guide criterion codes and fact ids. A pure validator (`analysis.feedback`) checks them, reusing Epic 9's `validate_ai_text` on the Adapted item's stored facts set; code renders the text, quote spans are mapped through the gateway's offset map to the original answer. A rejected feedback is asked for once more; then dropped with a note, the score kept. The «KI-vurdering» page shows the feedback, the dropped note and «Ikke kontrollert med en Kontrolltest.».

## Boundaries & Constraints

**Always:**
- Output v2 (`AssessmentFeedbackOutput`): `score` 0–4 and `feedback` 1–4 sentences, each `template_id`, optional `quote {start, end}`, optional `criterion` (code), `fact_ids` (0–3). Feedback templates (code constants, draft Norwegian, [ASSUMPTION]): `quote-covers` (quote + criterion), `quote-lacks` (quote + criterion), `missing` (criterion). A fact sentence uses a narration template id (`NARRATION_TEMPLATES`) of the Class session's pinned `narration_templates` version with fact ids only.
- Validator `analysis.feedback.validate_feedback(output, scrubbed_length, criteria_codes, fact_set, narration_templates) -> FeedbackVerdict` (pure), reasons: `unknown_template`, `wrong_arity` (slots present ≠ template's), `span_out_of_range` (not `0 ≤ start < end ≤ scrubbed_length`, longer than 300, or blank), `unknown_criterion`, `no_quote` (no sentence quotes), `repeated`, and the fact sentences' verdict from `narration.validate_ai_text` on the item's stored facts set (`unknown_fact` when the item has none, i.e. a long answer). Every number in the shown text comes from code: fact sentences are rendered by `narration.render_output`; feedback templates hold no digit.
- Rendering: quote spans map through `Result.offset_maps["answer"]` (`original_span`) to the stored answer, trimmed of edge whitespace; criterion renders `{code} ({text})` from the pinned guide entry. Stored on `ai_item_scores.feedback` as `{text, ai_generated: true, llm_call_id, parts}`; `parts` are `{"text": …}` or `{"quote": [start, end]}` over the original answer; `text` joins them with the quote as «…».
- Regeneration: a rejected first output → exactly one more `gateway.run` with the same inputs; its feedback is used when accepted (its `llm_call_id`); else `feedback` NULL and `feedback_note = 'dropped'`. The first call's score is kept in every case. A typed failure on the second call counts as rejected. A typed failure on the first call leaves the item unscored (12.2).
- Version choice: the job reads the pinned config's `prompts["assessment"]`; v1 → 12.2's score-only path, inputs and schema unchanged; v2 and above → feedback. `MOCK_SPEC`/`ai-configs/mock.json` name `assessment: 2`; `seed._missing_prompts` also derives (via `config.derive`, Story 2.2's command path) when the mock default holds a lower version of a `MOCK_SPEC` prompt.
- `tests.assessed` reader gives each item its `FactSet` (Adapted, from `games.fact_set_by_id`) and its fact ids, and the attempt the pinned narration templates; v2 prompt gets `$facts` as `narration.fact_lines` (moved from `debrief.narration`) and `$templates`.
- View `MyAssessmentOut`: `checked` from `content.service.is_checked(scoring_guide_id, model_config_id)` of the assessment row; each AI item `feedback {ai_generated, text, parts[{kind: text|quote, text}]}` (quote text sliced at read from the stored answer) and `feedback_dropped`.
- Web: under the item's score, `data-ai-generated="true"` block starting «KI-generert, kan ta feil:», quotes in `<q data-quote>` set apart; a dropped note in text in its place; «Ikke kontrollert med en Kontrolltest.» after the disclosure whenever items are shown and `checked` is false. Copy in `nb.ts`, drafts `[ASSUMPTION]`.
- Migration 0203 (revises 0202): `ai_item_scores.feedback jsonb NULL`, `feedback_note text NULL CHECK IN ('dropped')`, both NULL for `source='blank'`.

**Never:** An LLM-typed quote, number, Week or cause in the shown text; rebuilding a facts set; a retry of the score call or a third feedback call; per-criterion scores; touching v1 sessions' output; notice/sweep (12.4), flags or staff view (12.5), letter (12.6); real endpoints, `.env`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Valid output | v2, spans in range, known criterion, own fact ids | score + feedback stored, one call | — |
| Span out of range | `end > scrubbed length` | second call; accepted → its feedback | — |
| Foreign fact id | fact of another Seat / on a long answer | `unknown_fact` → second call | — |
| Both rejected | two bad outputs | score kept, `feedback_note='dropped'`, two `llm_call` rows | log reason only |
| Second call fails | `provider_error` on call 2 | same as both rejected | — |
| Roster name quoted | answer holds a Roster name inside the span | request has `[REDACTED]`; view quote shows the name | — |
| v1 session | pinned config names `assessment: 1` | score only, no feedback, no note | — |
| Blank answer | empty | step 0 by code, no feedback, no note | — |
| Unchecked | `is_checked` false | `checked: false`, notice shown | — |

</intent-contract>

## Code Map

- `backend/app/analysis/feedback.py` (new) -- schema, `FEEDBACK_TEMPLATES`, `validate_feedback`, `render_feedback(output, answer, offsets, criteria, fact_set, templates) -> (text, parts)`; reuses `narration.validate_ai_text`, `render_output`, `AiTextOutput`.
- `backend/app/analysis/narration.py` -- add `fact_lines` (from `debrief/narration.py:119`, which then imports it).
- `backend/app/modules/assessment/service.py` -- `_score_item`/`_assess_item` (~369/567): version from `ai.config.get(pin).spec.prompts`; v2 inputs/schema/mock, validation with `result.offset_maps["answer"]`, one regeneration; `_store_score` writes feedback; `ItemToAssess.fact_set/fact_ids`, `AttemptToAssess.narration_templates`; `AssessmentRecord` gains `scoring_guide_id`, `model_config_id`, per-item feedback.
- `backend/app/modules/assessment/models.py`, `backend/migrations/versions/0203_assessment_feedback.py` (new), `tests/test_migrations.py` (HEAD 0203).
- `backend/app/ai/prompts/assessment/v2.md` (new), `prompts/hashes.json`, `ai/seed.py` (`MOCK_SPEC`, `_missing_prompts`), `ai-configs/mock.json`.
- `backend/app/modules/tests/assessed.py` -- reader facts/templates (pins via `sessions.locked_pins` + `content.narration_templates`); `read` adds `checked`, feedback, dropped; `schemas.py` `FeedbackOut`, `FeedbackPartOut`.
- Tests: `tests/analysis/test_feedback.py` (new), `tests/assessment/test_feedback.py` (new; helpers from `test_assess.py`), `tests/ai/*` (seed/prompt files), `test_migrations.py`.
- Frontend: `src/modules/assessment/{assessment-page.tsx,assessment.ts,assessment.test.ts}`, `src/copy/nb.ts`, `npm run api:generate`, `e2e/ai-assessment.spec.ts`.

## Tasks & Acceptance

**Execution:**
- `analysis/feedback.py` + `tests/analysis/test_feedback.py` -- every reason, rendering with an offset map.
- Migration, models, prompt v2, seed/mock, assessment service, reader and view -- as above.
- `tests/assessment/test_feedback.py` -- every matrix row on the mock (scripted answers via `mock.script`).
- Frontend page, copy, api client, e2e at 360/1440 with axe: feedback, dropped note, unchecked notice.

**Acceptance Criteria:**
- Given a ready v2 assessment, when the Student opens it, then each AI item with feedback shows «KI-generert, kan ta feil:» and quotes of their original words; a dropped item shows the note; the page shows «Ikke kontrollert med en Kontrolltest.».
- Given a rejection, then exactly two `llm_call` rows exist for that item and the score is the first call's.

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
Layers: blind hunter, edge-case hunter, verification gap, intent alignment (sonnet; four reviewers for a data-model and AI-output change).
- verdicts: 37 findings — high 0, medium 4, low 26, false 7, maybe-false 0
- findings:
  - `[low]` `[reject]` Blind: quote spans rely on the LLM counting characters — the story's AC mandates character spans over the scrubbed text; a miss costs one regeneration then a drop with the score kept, and a span cutting a word is now widened to whole words (Edge row below). Real-provider accuracy is the residual risk.
  - `[low]` `[reject]` Blind: `mock_feedback` computes its span on the unscrubbed answer — mock-only (local, test, e2e) and only when a Roster term comes before the first full stop; a real model computes its own spans; tests script such cases.
  - `[false]` `[reject]` Blind: the mock answer is built eagerly and could break real calls — `mock_feedback` builds pydantic objects from typed reader data with no raising path (`criterion=None` is valid); Story 12.2 built its mock answer the same way.
  - `[low]` `[reject]` Blind: the score comes from the first call, the feedback maybe from the second — the AC keeps the score and regenerates the feedback; template sentences carry no score.
  - `[low]` `[reject]` Blind: template claims ("covers", "lacks") are not verifiable by code — inherent in AI feedback, labelled «KI-generert, kan ta feil:»; the Control test (12.9, 12.10) measures agreement.
  - `[low]` `[patch]` Blind: «Ordrene svinger.». double punctuation — when the template's sentence goes on after the quote (`.` or `,`), the quote's own final full stop is left out of the span; tests updated.
  - `[false]` `[reject]` Blind: facts offered beyond the item's own fact — the AC rejects "a fact id outside that set" (the stored facts set), so any fact of the Student's own game is valid; nothing outside the set is accepted.
  - `[medium]` `[patch]` Blind: v2 replaced the item's own fact line (and emptied it when the templates were unreadable) — `$facts` keeps v1's picked line (names and values the question is about); the citable facts go in a new `$citable` block of prompt v2 (relocked).
  - `[low]` `[reject]` Blind: only the mock default moves to v2 — the real provider's config does not name `assessment` at all yet (12.2 residual); an operator adds it with the config command.
  - `[low]` `[patch]` Blind: an unreadable stored span is shown as dropped with no log — `assessment_feedback_span_unreadable` is logged (no ids, no text).
  - `[low]` `[reject]` Blind: untested span edge cases (inside a placeholder, emoji, end of answer, overlaps) and no 320 px feedback e2e — placeholder mapping is the scrubber's tested rule and the Roster test quotes through one; the AC names 360 and 1440 px.
  - `[low]` `[reject]` Blind: no Vitest for the `Feedback` component — it renders the api's parts and is covered by Playwright at both widths with axe.
  - `[low]` `[patch]` Blind: unrelated reformatting of `ai-assessment.spec.ts` (and `api.ts`) — restored to the original formatting; only the Story 12.3 lines remain.
  - `[low]` `[patch]` Blind: production `assert`s and loose part typing — the import-time digit `assert` is removed (a test checks the templates); the two in-function asserts restate invariants the validator established and stay.
  - `[low]` `[reject]` Blind: the migration test checks columns, not the CHECK constraints — the model carries the same constraints and the api tests insert every legal combination.
  - `[low]` `[reject]` Blind: regeneration cost unbounded and `feedback_note` single-valued — at most one extra call per item by the AC; another note reason would be a later story's migration.
  - `[medium]` `[patch]` Edge: facts forced empty when the templates or the set are unreadable — same root and fix as the Blind fact-line row.
  - `[medium]` `[patch]` Edge: a pattern item's named fact line is lost under v2 — same root and fix.
  - `[medium]` `[patch]` Edge: a span starting or ending inside a word shows a fragment as the Student's words — `_passage` widens the span to whole words before the blank check and before it is stored; new test.
  - `[low]` `[reject]` Edge: one criterion both covered and lacked in one output — rare; a polarity guard is new validation the story does not ask for.
  - `[low]` `[reject]` Edge: mock span on unscrubbed text — same as the second Blind row.
  - `[false]` `[reject]` Edge: an item with empty criteria always fails `wrong_arity` — an item gets no call without its guide entry (12.2), and the content schema requires criteria.
  - `[low]` `[reject]` Edge: a transient failure on the second call stores `dropped` for good — the spec counts a failed regeneration as rejected, so the score is kept and calls stay bounded at two.
  - `[low]` `[reject]` Edge: the regeneration's score may differ — same as the fourth Blind row.
  - `[false]` `[reject]` Edge (claim): more than two `llm_call` rows per item — purpose `assessment` has `attempt_limit=1`, one row per call; the regeneration tests assert exactly two.
  - `[low]` `[patch]` Verification: `MAX_QUOTE` never fires in a test — 300 accepted and 301 rejected on a 400-character answer.
  - `[low]` `[patch]` Verification: the four-sentence cap is untested — a five-sentence output raises `ValidationError`.
  - `[low]` `[patch]` Verification: degraded fact paths untested — a test makes the narration templates unreadable: the Adapted item is scored, the prompt holds no citable facts or fact templates, and the feedback has no game sentence.
  - `[low]` `[patch]` Verification (other): the "a too long one" comment did not match its cases — comment fixed; the length case is its own test.
  - `[low]` `[reject]` Intent: Playwright runs on stand-ins — the repo's pattern for state screens (12.2); the api's feedback, quotes and C-1 are pinned by pytest on a real job run.
  - `[false]` `[reject]` Intent: the quote guarantee is not proven in the browser — the page renders only the api's `parts`, which the api test asserts are the original words.
  - `[low]` `[reject]` Intent: no staff surface for the unchecked notice — the staff view is Story 12.5; it reads the same `content.service.is_checked`.
  - `[low]` `[reject]` Intent: tests read mock-driven content — AD-17 and the AC ("on the mock provider").
  - `[false]` `[reject]` Intent: the config row is not made with the Story 2.2 command — the seed derives it with `config.derive`, the command's path, as 9.14, 11.8 and 12.2 did; tested in `test_text.py`.
  - `[low]` `[reject]` Intent: v1 score-only shown by swapping the lock's config choice — the lock's choice is 12.2's tested code; the test pins the job's version switch.
  - `[low]` `[patch]` Intent: unrelated reformatting — same patch as the Blind reformatting row; the `fact_lines` move serves the reuse and keeps debrief's name.
  - `[false]` `[reject]` Intent: `openapi.json` and `schema.ts` not in the patch — generated files, left out of the review diff on purpose; regenerated with `npm run api:generate` and typechecked.

## Design Notes

- Approved sentence templates are code constants in `analysis.feedback` (draft copy for the founder); stored text is rendered at assessment time, so a later template change never alters a stored feedback. Fact sentences reuse the Debrief narration templates and validator so the "matches my games" rule is Epic 9's, verbatim.
- Feedback-template sentences hold only guide text and the Student's own quoted words, so the 9.14 number rule applies to the fact sentences, where code renders every number.

## Verification

**Commands:**
- `uv run pytest tests/analysis/test_feedback.py tests/assessment tests/ai tests/test_migrations.py tests/debrief -q` -- pass
- `npm run typecheck && npx vitest run src/modules/assessment` -- pass
- `npx playwright test e2e/ai-assessment.spec.ts --workers=4` -- pass

## Auto Run Result

Status: done

**Summary.** On a model config naming prompt `assessment/v2` (new, locked), each `assessment` call also returns 1–4 feedback sentences built only from references: approved template ids (`quote-covers`, `quote-lacks`, `missing`, draft Norwegian in `analysis.feedback`, or a Debrief narration template for a sentence about the Student's game), quote spans over the scrubbed answer, Scoring guide criterion codes and fact ids. The pure `analysis.feedback.validate_feedback` rejects spans outside the scrubbed text, blank or longer than 300 characters, unknown templates or slots, unknown criteria, output with no quote, repeats, and fact sentences that fail Epic 9's `validate_ai_text` on the Adapted item's stored facts set (read by `fact_set_id`, never rebuilt; a long answer has none, so `unknown_fact`). Code renders the text: quotes are mapped through the gateway's offset map to the original answer, widened to whole words, and lose their own final full stop when the template's sentence goes on. A criterion renders as `code (text)` from the pinned guide, and a game fact through the narration templates the Class session pinned. A rejected feedback is asked for once more with a new call (its own `llm_call` row); if that is rejected or fails, the feedback is left out (`feedback_note = 'dropped'`) and the first call's score stays. Stored on `ai_item_scores.feedback` as `{text, ai_generated, llm_call_id, parts}` (migration 0203). A config naming `assessment/v1` keeps 12.2's score-only call. `MOCK_SPEC` and `mock.json` name v2, and the zero-config seed now also derives a row (Story 2.2's `config.derive`) when the mock default holds a lower prompt version. The Student's «KI-vurdering» shows the feedback under the item's score: «KI-generert, kan ta feil:», `data-ai-generated`, each quote in `<q>` cut from their original answer by the stored span. Where feedback was left out, a text note stands in its place. While `content.service.is_checked` is false, «Ikke kontrollert med en Kontrolltest.» shows under the disclosure.

**Process.** Implemented in the build agent's own context, as the lane brief requires, not by the workflow's implementation subagent.

**Decisions taken here (founder would otherwise):** The approved feedback sentences are three code constants with draft copy, and game facts reuse the Debrief narration templates. A feedback must quote at least once, at most 4 sentences, a quote at most 300 characters. A failed second call counts as rejected, so the item ends `dropped` with its score. The unchecked notice shows whenever items are shown, including score-only items. The quote's final full stop is dropped before the template's own punctuation. Spans are widened to whole words.

**Files.**
- `backend/app/analysis/feedback.py` (new): schema, templates, `validate_feedback`, `render_feedback`, `template_lines`.
- `backend/app/analysis/narration.py`: `fact_lines`, moved from `modules/debrief/narration.py`, which keeps the name.
- `backend/app/modules/assessment/{service,models}.py`, `backend/migrations/versions/0203_assessment_feedback.py`: version switch, regeneration, storage, record read.
- `backend/app/ai/prompts/assessment/v2.md`, `prompts/hashes.json`, `ai/seed.py`, `ai-configs/mock.json`: prompt v2 and its config.
- `backend/app/modules/tests/{assessed,schemas}.py`: the reader's facts set and templates, and the view's `feedback`, `feedback_dropped` and `checked`.
- Tests: `tests/analysis/test_feedback.py`, `tests/assessment/test_feedback.py` (new); `tests/assessment/test_assess.py`, `tests/ai/{conftest,test_prompt_files,test_text}.py`, `tests/test_migrations.py` updated.
- `frontend/src/modules/assessment/{assessment-page.tsx,api.ts,assessment.test.ts}`, `src/copy/nb.ts`, `src/lib/api/{openapi.json,schema.ts}` (generated), `e2e/ai-assessment.spec.ts`.

**Review.** 37 findings from four sonnet reviewers: high 0, medium 4, low 26, false 7. Patched entries: medium 2 (the item's own fact line kept with citable facts in a separate prompt block; spans widened to whole words) and low 7 (quote punctuation, span log, reformatting restored, import-time assert removed, `MAX_QUOTE` and sentence-cap tests, degraded-templates test). Rejected: 17 low and 7 false, each with its reason in the triage log. Nothing deferred.

**Follow-up review: recommended.** Two medium entries were patched (patched: high 0, medium 2, low 7). Unverified risk: no real model has produced v2 output yet, so how often its character spans land on the intended words is unmeasured. Each miss costs a second call and can end in `dropped`.

**Verification.** Backend: full suite `--maxprocesses=8`, 3742 passed. An earlier full run, before the review patches, had one failure, `tests/ai/test_config.py::test_a_referenced_config_cannot_change_and_an_edit_writes_a_new_row`, which passed alone and in `tests/ai` in parallel and did not recur. `ruff check` and `ruff format --check` are clean. Frontend: `tsc` clean, Vitest 1179 passed, `lint:colours` and `check:copy` pass, `next build` ok, OpenAPI regenerated. Playwright on the lane-3 stack (8082, rebuilt after the patches): `ai-assessment` (feedback, dropped note and unchecked notice at 360 and 1440 px with axe, plus 12.2's states), `homes`, `student-home`, `individual-test`, `order-field`, `week-table` and `game-start`, 135 passed. Matrix audit: every row has a passing test in `tests/assessment/test_feedback.py`, `tests/analysis/test_feedback.py` or `test_assess.py` (blank). New tests over 1 s: each api test in `tests/assessment/test_feedback.py` takes 1.7–2.3 s, from the shared `adapted_session` fixture as in 12.2.

**Residual risks.** See the follow-up risk. The real provider's config does not name `assessment` yet (12.2). Feedback template texts, the dropped note and the quote punctuation are draft copy ([ASSUMPTION]). A transient failure of the second call drops the feedback for good.

**Personal data.** No new table. `ai_item_scores` (Story 12.2) now holds text a User wrote: `feedback.text` repeats the quoted passages of the Student's answer. Its `parts` spans also point into `test_answers`.
