---
title: 'Story 11.9: Preview the Adapted item templates with a sample Student'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: '48e59a118e4c2f0f75226c0d0bd864724303659a'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-11-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-11-7-get-adapted-items-from-my-own-game-and-replay.md'
  - '{project-root}/.docs/implementation-artifacts/spec-11-8-read-adapted-items-in-natural-wording.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** A Lecturer sees only «Tilpassede oppgaver» and a weight in «Spørsmål og vekter»; nothing shows what kind of question each Adapted item template asks about a Student's own decisions (FR-53, UX-DR70).

**Approach:** Ship a static sample facts set (the Student-held Retailer of Story 9.1's Takeover golden Game, built by `analysis.facts` from a new repo fixture of that Game's `seat_weeks` rows). `GET /api/class-sessions/{id}/adapted-preview` fills each template of the version the session pins (pinned version once locked, the latest before) with `analysis.adapted.fill` from that set; a Lenke in «Spørsmål og vekter» opens a page `/klasseokter/{id}/tilpassede-oppgaver` that shows them labelled «Demodata» with the Adapted total weight.

## Boundaries & Constraints

**Always:**
- Sample file `backend/app/modules/tests/files/sample_facts.json` = `{"patterns_version": 1, "facts": <FactSet json>}` for Role `retailer`, built with `simulation=None` and detected patterns v1. Both template sources (`game`, `replay`) read this one set.
- Fixture `backend/tests/golden/facts/takeover-seat-weeks.json` = the Takeover golden Game's raw `seat_weeks` rows (week, role, order, decided_by, occupant_kind, state_seen), sorted by week then chain order, plus `roles`; `test_the_takeover_golden_facts` asserts the played Game equals it (rewritten with `UPDATE_GOLDEN=1`, like the facts goldens).
- A DB-free test rebuilds the sample from the fixture (rows → `LoggedOrder` via `games.facts._logged`, `analysis.facts(log, "retailer", V1)`) and compares it with the shipped file (`UPDATE_GOLDEN=1` rewrites it).
- Response `AdaptedPreviewOut {version, draft, pinned, adapted_weight, items: [{id, source, fact, weight, text|null}]}`; item weights = `apportion(adapted_weight, shares)`; `text` null when the sample has no such fact. `draft` = templates `status == "draft"`.
- Adapted total = the pinned selection once locked, else `selection.effective` (the same number «Spørsmål og vekter» shows).
- Access via `sessions.question_set_session` (`class_sessions.read`): owners and Assistant lecturers 200; outsiders, Students and unknown ids 403 `forbidden`.
- Page: crumbs Lærerhjem › Klasse › Klasseøkt › «Tilpassede oppgaver»; «Demodata» caption; the question-set `draft` notice copy when `draft`; total weight line; per item the source («Fra Klassespillet» / «Fra Replay»), its «Vekt n %» and the text. All copy in `nb.tests.adaptedPreview` (reusing `questionSet.draft`).

**Never:** No Game row, no `games.facts.get_or_create`/`fact_set`, no LLM call, no wording choice (code text only), no DB write, no new table, no change to the demo Class.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Owner, open session | default selection | latest templates v2, `draft: true`, `pinned: false`, total 30, items 15/15 with text | — |
| Saved total 40 | selection adapted 40 | `adapted_weight: 40`, items 20/20 | — |
| Locked | lock pinned templates v2, selection 25 | `pinned: true`, version = pin, total 25 | — |
| Assistant lecturer | member as assistant | 200, same body | — |
| Outsider / student / unknown id / bad id | — | 403 `forbidden` | — |
| Template without a sample fact | `pick` beyond the sample's facts | item `text: null`; page says the sample has no such event | — |

</intent-contract>

## Code Map

- `backend/app/analysis/adapted.py` -- `fill`, `picked`, `apportion` (the 11.7 code renderer; reused unchanged).
- `backend/app/analysis/facts.py` -- `facts(decision_log, seat, patterns, simulation=None)`, `DecisionLog`, `FactSet`.
- `backend/app/modules/games/facts.py` `_logged` (~67) -- seat_weeks row → `LoggedOrder` (used by the rebuild test).
- `backend/tests/games/test_facts.py` -- `takeover_game`, `raw_rows`, `assert_golden`; add the rows fixture check.
- `backend/tests/golden/facts/takeover.json` -- existing golden facts of the same Game (retailer has 12 student Orders, 3 moments).
- `backend/app/modules/tests/selection.py` -- `pinned_selection`, `effective`; `routes.py` (`_id`, question-set GET pattern), `schemas.py` (`QuestionSetOut`).
- `backend/app/modules/content/service.py` -- `adapted_templates(version)`, `pinned_version(pins, Kind.ADAPTED_TEMPLATES)`, `detected_patterns`.
- `backend/app/modules/sessions/service.py` `question_set_session` (~1837) -- authz + pins.
- `backend/tests/question_set/test_question_set.py` -- api test helpers (`call`, `EMAIL`, `klass`, `shared`, `planned`, `new_session`).
- Frontend: `src/modules/tests/{api.ts,question-set-block.tsx}`, `src/modules/messaging/sent-messages-page.tsx` (sub-page pattern), `src/modules/identity/homes.ts` (paths), `src/app/(app)/klasseokter/[sessionId]/meldinger/page.tsx` (route pattern), `src/copy/nb.ts` (`tests.questionSet`), `e2e/question-set.spec.ts`.

## Tasks & Acceptance

**Execution:**
- `backend/tests/golden/facts/takeover-seat-weeks.json` + `tests/games/test_facts.py` -- write/assert the rows fixture.
- `backend/app/modules/tests/files/sample_facts.json`, `backend/app/modules/tests/preview.py` (new) -- `sample()`, `read_preview(user, id)`.
- `backend/app/modules/tests/{schemas.py,routes.py,README.md}` -- schema, `GET …/adapted-preview` (`getAdaptedPreview`).
- `backend/tests/individual_test/test_preview.py` (new) -- rebuild check, numbers-equal-rows check, matrix rows, no Game/fact_set/LLM call.
- Frontend: `npm run api:generate`; `api.ts` hook; `adapted-preview-page.tsx` (new) + route; `homes.ts` path; Lenke in `question-set-block.tsx`; `nb.ts` copy; `e2e/adapted-preview.spec.ts` (320/360/1440 + axe, draft notice, Demodata, weight, link from the block).

**Acceptance Criteria:**
- Given a Lecturer on the Klasseøkt before the Start date, when they follow the Lenke in «Spørsmål og vekter», then each template appears filled with the sample's numbers, labelled «Demodata», with the Adapted total weight and the draft notice.
- Given the shipped sample, when CI runs, then rebuilding it from the fixture equals the file, and every number in each preview text equals a value derived from the fixture's `seat_weeks` rows.
- Given the preview is read, then the counts of `games`, `fact_sets` and `llm_calls` rows are unchanged and `games.facts.get_or_create` is not called.

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
Layers: blind hunter and edge-case hunter (sonnet; two, per the team lead's brief: a read-only endpoint behind the existing access check, no table, no migration). Verification-gap and intent-alignment were skipped. The generated `openapi.json`/`schema.ts`, the 124 kB rows fixture and this spec were left out of the review diff.
- verdicts: 17 findings — high 0, medium 0, low 12, false 5, maybe-false 0
- findings:
  - `[false]` `[reject]` Blind: pattern names read from Detected patterns v1, not the session's pin — a Student's items are named by the version their facts set was built with (`adapted.pattern_names(stored)`), and the sample was built with v1, so v1 is the same rule.
  - `[low]` `[reject]` Blind: pins and the selection are read in two transactions — a lock in between pins exactly the selection `effective` reads (saves are refused once locked); the only difference is a content version published in that instant.
  - `[low]` `[patch]` Blind: the page does not say an AI may choose another approved wording (Story 11.8) — new line `adaptedPreview.wordings` under the lead.
  - `[low]` `[patch]` Blind: the «Fra Replay» item reads the same sample game without saying so — `adaptedPreview.sample` now says the Replay item uses numbers from the same game.
  - `[low]` `[reject]` Blind: `sources` typed `Record<string, string>` — the pattern of `questionSet.types` and `scoringGuide.kinds`; the `??` fallback covers a new value.
  - `[false]` `[reject]` Blind: title equals crumb and the draft notice reuses «Spørsmål og vekter»'s copy — the story asks for that same notice; title and crumb are equal on other pages too; «Demodata» is asserted on every item in e2e.
  - `[low]` `[reject]` Blind: tests pin the shipped ids, weights and `Utkast:` prefix, import `_logged` and `_empty` — the pattern of `test_question_set.py` and `test_adapted.py`; an approved version is a deliberate content change that updates these tests.
  - `[low]` `[patch]` Blind: test gaps — the `text: null` state now has an e2e test (route-fulfilled). Rejected parts: a non-draft pinned version, the pattern-name api path, the load-failed and 403 page states (shared `PageShell`/`AccessDenied` paths), a no-write check on every table.
  - `[low]` `[patch]` Blind: the fixture empties `history`, so nothing proved the rebuilt set equals the played Game's — the rebuild test now also compares with `takeover.json`'s Retailer (with `simulated` left out).
  - `[low]` `[patch]` Blind: cosmetic — the over-long docstring line in `question-set-block.tsx` rewrapped. Rejected: the Lenke's `<p>` spacing (the Lenke's own 44 px target spaces it), `blockquote` for the shown question; `later_cost` "0" is `analysis.facts` output, not this diff.
  - `[false]` `[reject]` Edge: a saved total leaves the preview cache stale — the save emits `session:<id>`, which `lib/api/topics.ts` maps to `["class-sessions", id]`, a prefix of `adaptedPreviewKey`.
  - `[low]` `[reject]` Edge: lock between the two reads — same as the second Blind row.
  - `[false]` `[reject]` Edge: a session locked before the templates pin shows `pinned: false` — correct: such a session reads the latest templates at each open (Story 11.7), which is what the preview shows; the page does not use `pinned`.
  - `[false]` `[reject]` Edge: an empty `text` shows the no-fact line — `fill` renders a template of at least one character with its key values; it is never empty.
  - `[low]` `[reject]` Edge: tests hard-code the draft state and 30 % — same as the seventh Blind row.
  - `[low]` `[patch]` Edge: the no-fact matrix row had no frontend test — same patch as the eighth Blind row.
  - `[low]` `[reject]` Edge: a failed refetch keeps stale data silently — the shared `usePageState` behaviour of every page.

## Design Notes

- A static set keeps the preview free of Game rows and LLM calls (AD-7) and identical for every Class; the CI rebuild ties it to `analysis.facts`, and the rows fixture ties it to the engine via the existing Takeover golden Game.
- One sample set for both sources: a Replay template shows the same Student's outcome. The preview illustrates the kind of question, not real Replay results.

## Verification

**Commands:**
- `uv run pytest tests/individual_test/test_preview.py tests/games/test_facts.py tests/question_set -q` -- pass
- `npm run typecheck && npx vitest run src/modules/tests` -- pass
- `npx playwright test e2e/adapted-preview.spec.ts e2e/question-set.spec.ts --workers=4` -- pass

## Auto Run Result

Status: done

**Summary.** A Lecturer or Assistant lecturer opens «Tilpassede oppgaver» through a new Lenke in the Adapted line of «Spørsmål og vekter» (`/klasseokter/{id}/tilpassede-oppgaver`). The page shows each Adapted item template of the version the Class session pins (the lock's pin, the latest version before the lock). Each is filled by the code renderer of Story 11.7 (`analysis.adapted.fill`) from a static sample facts set, captioned «Demodata», with its source, its Vekt (its share of the Adapted total in force) and the total itself. A draft version carries «Spørsmål og vekter»'s draft notice. The api is `GET /api/class-sessions/{id}/adapted-preview` (`getAdaptedPreview`, `class_sessions.read` through `sessions.question_set_session`; 403 `forbidden` for everyone else). The sample `backend/app/modules/tests/files/sample_facts.json` is the Retailer of Story 9.1's Takeover golden Game, where a Student placed the Orders of Weeks 3-14. It is built by `analysis.facts` (Detected patterns v1, no simulated rows) from a new fixture of that Game's `seat_weeks` rows. `test_facts.py` checks the fixture against the played Game. `test_preview.py` rebuilds the sample from the fixture, compares it with the shipped file and with the stored golden set, and re-derives every number of the preview from the rows. The preview creates no Game, reads no stored facts set, makes no LLM call and writes nothing.

**Files.**
- `backend/app/modules/tests/preview.py` (new): `sample()`, `preview_items`, `read_preview`.
- `backend/app/modules/tests/files/sample_facts.json` (new): the sample facts set.
- `backend/app/modules/tests/{schemas.py (AdaptedPreviewOut, AdaptedPreviewItemOut), routes.py (the route), README.md}`.
- `backend/tests/golden/facts/takeover-seat-weeks.json` (new; `history` emptied), `backend/tests/games/test_facts.py` (`golden_rows`, `assert_golden_rows`).
- `backend/tests/individual_test/test_preview.py` (new, 12 tests).
- Frontend: `src/modules/tests/adapted-preview-page.tsx` (new), `src/app/(app)/klasseokter/[sessionId]/tilpassede-oppgaver/page.tsx` (new), `src/modules/tests/{api.ts, question-set-block.tsx}`, `src/modules/identity/homes.ts` (`adaptedPreviewPath`), `src/copy/nb.ts` (`tests.adaptedPreview`, `questionSet.adaptedPreview`), `src/lib/api/{openapi.json, schema.ts}` (regenerated), `e2e/adapted-preview.spec.ts` (new).
- `.docs/implementation-artifacts/epic-11-context.md`: recompiled because the architecture spine was newer.

**Review.** Two sonnet reviewers reported 17 findings: high 0, medium 0, low 12, false 5. Six low entries were patched: the wording note, the Replay-sample note, the no-fact e2e test (two rows), the golden-set comparison and a docstring wrap. Six low and five false findings were rejected, each with its reason in the triage log. Nothing was deferred.

**Follow-up review: not recommended.** Patched: high 0, medium 0, low 6.

**Verification.**
- Backend: the full suite with `--maxprocesses=8` gave 3350 passed. `ruff check` and `ruff format --check` are clean. No new test is over 1 s (the slowest new test runs 0.5 s).
- Frontend: `tsc` clean, Vitest 1071 passed, `lint:colours`, `check:copy` and `next build` pass.
- Playwright on lane 2 (8081, stack rebuilt with this change): 78 passed across adapted-preview (with axe at 320/360/1440), question-set, homes, order-confirm, order-field, week-table, game-start and guided-week.
- Visual check of the page at 360 and 1440 px and of the Lenke in the block, from screenshots.

**Decisions taken for the founder.**
- The preview is its own page, reached by a Lenke in the Adapted line of «Spørsmål og vekter».
- The sample is the Takeover golden Game's Retailer, and both the Class-game and the Replay templates read it. The page says so.
- Before the lock, the preview shows the latest template version and the Adapted total in force. Once locked, it shows the pinned version and total.
- Code text only. A note says that an AI may choose another approved wording when AI text is on.
- The fixture stores `seat_weeks` rows with `history` emptied (it repeats earlier rows): 124 kB instead of 390 kB.
- The copy is `[ASSUMPTION]` draft copy.

**Personal data.** No new table.

**Residual risks.**
- When the templates are approved, the tests that pin the draft state, the ids and the 30 % default will need updating.
- The implementation was done in the main context, not a subagent, per the team lead's brief.
