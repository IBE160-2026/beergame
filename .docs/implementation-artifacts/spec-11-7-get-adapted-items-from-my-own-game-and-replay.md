---
title: 'Story 11.7: Get Adapted items from my own game and Replay'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: 'dad8adaca1b0af5c28bc367fe7c55da8dee49f4f'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-11-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-11-3-open-the-individual-test-with-the-own-work-statement.md'
  - '{project-root}/.docs/implementation-artifacts/spec-11-6-write-long-answers-with-autosave.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** The Individual test serves only Core items: there are no Adapted item templates, `open_attempt` freezes no item about the Student's own Class game or Replay, and the Adapted total weight (default 30 %) is carried by nothing, so the weights of an attempt sum to 70 (FR-53, AD-7, AD-15, AD-23).

**Approach:** A new immutable content kind `adapted_templates` (draft v1 by migration 0125, shipped as `files/adapted_templates.json`) pinned at `sessions.lock`; a pure renderer `analysis/adapted.py` that fills each template from one stored facts set; `tests.commands.open_attempt` builds the Adapted items (or, for a Student with fewer than 10 own Orders, the question set's replacement Core items) in its transaction and freezes them on the attempt with the Adapted total weight between them; the page answers an Adapted item as a long answer.

## Boundaries & Constraints

**Always:**
- Template record: `status` draft|approved; `templates` 1–10, ids unique (`_Key`), each `{id, source: game|replay, fact: moment|pattern|outcome, pick: 1–3 (default 1), share: 1–100, text}`; shares sum to 100; `text` uses only plain `{slot}`s from its fact kind's values and must use the kind's key values (moment: `week`,`order`; pattern: `week`,`pattern`; outcome: `total_cost`); no `!`. Values: moment/pattern = `role, week, order, incoming_order, inventory, backlog, supply_line` (+ `pattern` = the Detected pattern's name); outcome = `role, weeks, total_cost, holding_cost, backorder_cost`. Shipped draft: `tilpasset-eget-spill` (game, moment, 50) and `tilpasset-replay` (replay, outcome, 50) — the ids the Scoring guide of 11.2 already names.
- Fact choice: moment = the Seat's own moments ordered by later cost (desc) then Week, the `pick`-th; pattern = the Seat's occurrences with `decided_by = student`, same order; outcome = the Seat's `chain.by_role` entry. Fact ids: the moment's / occurrence's id; outcome `outcome:<role>`. Code renders numbers (`format_number`; money `format_money`), Roles in Norwegian (Detaljist, Grossist, Distributør, Fabrikk).
- Facts only through `games.service.student_game(s, user, session)` (own game, its Role) and `replay.service.replay_game_of` (Replay Game, same Role), each read with `games.service.fact_set(game, role)` (`games.facts.get_or_create`). Never a query on Class games.
- Frozen Adapted item on `test_attempts.items`: `{id, type: "adapted", weight, template_version, source, fact, fact_set_id, fact_ids, text: {text, ai_generated: false, llm_call_id: null}}`, after the Core items, in template order. Weights: the selection's `adapted_weight` split by `share` with largest remainder (ties: template order), integers summing exactly to it.
- Replacement path: own facts set's `seat.student_orders < MIN_STUDENT_ORDERS` (the one `decided_by = student` count, AD-15) → the pinned question set's `replacements` in order, weights scaled to `adapted_weight` by the same apportionment, each frozen as `{id, type, weight, replaces: "few_orders"}`. The same replacement items (reason `no_game`, `no_replay`, `facts_unavailable` or `unfilled`) when the own game or Replay or its facts set cannot be read or a template finds no fact; a log line names the reason and ids only. `adapted_weight = 0` → neither.
- Template version: the lock's pin `pins["adapted_templates"]` (`content.adapted_templates_pin`, registered in `sessions` like the other content kinds), else the latest. An attempt never changes once opened: a second open returns it as stored; a newer template version changes nothing.
- Item out: `type` adds `"adapted"`; `title` = the frozen text; new field `wording: {text, ai_generated, llm_call_id} | null` (set for Adapted items only). `save_answer` validates an Adapted item's value as a long answer (`_text`). Frontend: «Tilpasset oppgave» type line, `LongItem` (label = title) with 11.6's debounced autosave.

**Never:** No LLM call, no prepared set or job (11.8); no Lecturer preview (11.9); no scoring of Adapted items; no new table; no production lock refusal for draft templates (the question set's refusal stays the only one); no answer text in logs; no change to the demo Class.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Own game ≥ 10 own Orders, Replay finished | open | Core items + 2 Adapted items, 15 + 15, text filled from both facts sets, `fact_set_id`s stored | — |
| Few own Orders | own facts set `student_orders` 9 | replacement items `erstatning-tabell`, `erstatning-langsvar`, weights sum to `adapted_weight`, `replaces: few_orders` | — |
| No own game / no Replay Game / facts refused | | replacement items, reason `no_game` / `no_replay` / `facts_unavailable` | log reason, ids only |
| Adapted total 25 | selection pin `adapted_weight` 25 | Adapted weights 13 + 12; whole attempt sums to 100 | — |
| Adapted total 0 | | no Adapted or replacement item | — |
| Re-open / new template version | after open | items as first frozen | — |
| Save Adapted answer | text ≤ 20 000 | stored as typed | non-text 422 `invalid_answer` |

</intent-contract>

## Code Map

- `backend/app/analysis/adapted.py` (new, pure) -- `FACT_VALUES`, `AdaptedTemplate`, `AdaptedTemplates` (schema rules), `ROLE_NAMES`, `Filled(fact_ids, values, text)`, `fill(template, facts, pattern_names) -> Filled | None`, `apportion(total, shares) -> list[int]`. Reuse `analysis.sentences._fields/_plain_slots`-style checks, `format_number`, `format_money`; `analysis.facts.FactSet`.
- `backend/app/modules/content/{models,schemas,service}.py` -- `Kind.ADAPTED_TEMPLATES`; export `AdaptedTemplates`; `_SCHEMAS`, `adapted_templates(version)`, `adapted_templates_pin` (pattern `narration_templates_pin` ~502); `README.md`, `__main__.py` docstring if it lists kinds.
- `backend/app/modules/content/files/adapted_templates.json` (new) == migration literal.
- `backend/migrations/versions/0125_adapted_templates.py` (new; pattern 0122 kinds swap + row insert) -- kind constraint, v1 row id `01a1f9a0-0000-7000-8000-000000000125`.
- `backend/app/modules/sessions/service.py` (~3372) -- `register_pin_provider(Kind.ADAPTED_TEMPLATES, content.adapted_templates_pin)`.
- `backend/app/modules/tests/adapted.py` (new) -- `build(s, user_id, class_session_id, pins, selection, question_set) -> list[dict]`: reads games/replay services, facts, templates; returns frozen Adapted or replacement items.
- `backend/app/modules/tests/commands.py` (`_frozen` ~114, `open_attempt` ~134, `_valid` ~217, `save_answer` ~290) -- append built items in the transaction; `adapted` validation.
- `backend/app/modules/tests/{attempt.py (_items ~107), schemas.py (IndividualItemOut ~251)}` -- `adapted` type, `wording`; `README.md` section.
- Tests: `backend/tests/individual_test/test_adapted.py` (new): golden (played Class game via `tests.debrief.test_explanation.played` + Replay via `tests.replay.test_start.start` with shortened weeks, every number re-derived from `seat_week`), replacement/no-game/zero/odd weight, frozen after re-open and a v2 template publish, save; `tests/analysis/test_adapted.py` (schema rules, apportion, fill); `tests/content/test_content.py` or new (file == migration, ids == guide's adapted questions, pin); update `test_open.py` (item keys `wording`, replacements in the list), `tests/test_migrations.py` (head 0125).
- Frontend: `src/modules/tests/individual-test-page.tsx` (~155: `adapted` → `LongItem`), `individual-test.ts` (type line), `copy/nb.ts` (`tests.individual.types.adapted`), `npm run api:generate`; `e2e/individual-test.spec.ts` stand-in Adapted item at 320/360/1440 with axe, typing → saved.

## Tasks & Acceptance

**Execution:**
- `backend/app/analysis/adapted.py`, content kind/schema/service/file, migration 0125, sessions pin -- the versioned templates.
- `backend/app/modules/tests/{adapted,commands,attempt,schemas}.py`, README -- build, freeze, serve, save.
- Backend tests as mapped -- every matrix row, golden, migrations head.
- Frontend page, copy, generated client, e2e.

**Acceptance Criteria:**
- Given a Student with ≥ 10 own Orders and a finished Replay, when they open the test, then two Adapted items follow the Core items, each citing its facts set and fact ids, and every number, Week and Role in their text equals the `seat_week` rows of the two Games (golden test).
- Given any opened attempt, then the frozen item weights sum to 100.
- Given an Adapted item, when the Student types, then it saves through 11.6's autosave and «Lagret HH:MM» shows; axe passes at 320/360/1440.

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
Layers: blind hunter, edge-case hunter, verification gap and intent alignment (sonnet; four, since the change adds a content kind, a migration and builds frozen per-Student items from game data inside the opening transaction). Generated `openapi.json`/`schema.ts` and this spec were left out of the review diff.
- verdicts: 32 findings — high 0, medium 0, low 26, false 6, maybe-false 0
- findings:
  - `[low]` `[reject]` Blind: `_replacements` raises in `apportion` when every replacement weight is 0, and errors other than `ViewError` abort the open — reachable only if a published question set had a default Adapted total of 0 and a Lecturer then raised it; `ContentNotFound` for a facts set's `patterns_version` cannot occur (content is never deleted). A loud failure on content no one ships; the guard is a new branch.
  - `[low]` `[patch]` Blind: «Nothing here writes» while `games.fact_set` may store a facts set — docstring now says the module writes no attempt and that a first read is stored by `get_or_create` in its own short transaction.
  - `[low]` `[reject]` Blind: an Adapted total smaller than the number of templates gives a 0-weight item — the same as a Core item a Lecturer weights 0 (served since 11.3); a Lecturer choosing an Adapted total of 1 is not met in use.
  - `[low]` `[reject]` Blind: template ids are tied to the Scoring guide and kept apart from question-set ids only by a test on the shipped files — a cross-kind check on publish adds a new refusal for operator-published content (issue #16 delivers both files together); recorded as a residual risk.
  - `[false]` `[reject]` Blind: «no frontend work in the diff» — the diff changes `individual-test-page.tsx` (adapted → `LongItem`), `nb.ts` (`types.adapted`), the Vitest and the e2e; the generated client was regenerated (left out of the review diff only).
  - `[low]` `[reject]` Blind: `status: "draft"` is not enforced; Students would read «Utkast:» — the question set's production lock refusal (11.1) is the one draft gate until issue #16; a second refusal needs a new reason code, mail and page copy. Recorded as a founder decision.
  - `[low]` `[reject]` Blind: `ROLE_NAMES` duplicates `nb.ts` with no sync test — a cross-language test for four fixed names; the docstring points at the source.
  - `[low]` `[patch]` Blind: test gaps (`unfilled`, the pattern kind through `build`, pre-pin) — new test runs a pattern template through `build` (name from the stored Detected pattern version) and a `pick` past the Seat's occurrences (`unfilled`, logged); the pin test now strips the pin and shows a second Student gets the newer version. The own game's `facts_unavailable` is `test_open.py`'s real path; a double open is 11.3's race test.
  - `[low]` `[reject]` Blind: the Replay's facts get no own-Order check, `pick` is accepted for `outcome` — a Replay is a finished Game the Student played (the `replay` step); a Replay moment template with too few moments is `unfilled` and gives the replacements; `pick` on an outcome is ignored, harmless.
  - `[low]` `[patch]` Blind: weak assertions — the golden test now checks both items' texts are absent from the logs. Rejected parts: the parametrize's `why` labels the case (the repo's pattern); private seams are the documented stand-in.
  - `[low]` `[patch]` Blind: small code issues — the unused `FACT_KINDS` and the `_money` wrapper are removed. Rejected: the Replay lookup when no template reads it (one indexed read), the `!` ban (the sentence-template rule, UX-DR78), tie order (patterns of one Week share the Week and later cost; the set's order is deterministic), log fields (the built line names fact set ids, the replaced line the reason).
  - `[low]` `[reject]` Blind: README says «10», `title` duplicates `wording.text`, no downgrade note — the README names AD-15's count next to it; `title` is the label every item has, `wording` carries the AI mark 11.8 needs; a downgrade below 0125 is a dev operation.
  - `[low]` `[reject]` Edge: replacement weights all 0 → `apportion` raises — same as the first Blind row.
  - `[low]` `[reject]` Edge: no catch-all around the facts build — same as the first Blind row.
  - `[low]` `[reject]` Edge: a 0-weight Adapted item — same as the Blind row.
  - `[low]` `[reject]` Edge: a template id equal to a question-set id — same as the Blind id row.
  - `[low]` `[reject]` Edge: duplicate ids in the frozen list confuse `save_answer` — same root as the id row; not reachable with the shipped files (tested).
  - `[low]` `[reject]` Edge: the open transaction holds its connection while `fact_set` takes another — at most one more pooled connection at a time, once per Student per Class session; opens spread over the test's days.
  - `[low]` `[reject]` Edge: an unfinished or barely played Replay — unfinished gives `facts_unavailable` (`get_or_create` refuses), tested; a short Replay still yields true costs from its Decision log.
  - `[low]` `[reject]` Edge: a session locked before the pin reads the latest version at each open — the rule of every content pin (Starting task, quiz …) for sessions locked before it existed; no such session will have an Individual test.
  - `[low]` `[patch]` Edge (claim): «every Student gets the same templates» is not true for a pre-pin session — docstring and README now qualify it.
  - `[low]` `[patch]` Edge (claim): the CLI docstring did not list `adapted_templates` — added.
  - `[low]` `[reject]` Edge (claim): id parity is enforced only by a test — same as the Blind id row.
  - `[low]` `[patch]` Verification: the pattern path and `unfilled` through `build` were unverified — same new test as the Blind test-gap row.
  - `[false]` `[reject]` Intent: only the golden test goes through the real lookups — no defect: the golden test and `test_open.py` run `student_game`/`replay_game_of`/`get_or_create`; the stand-ins cover branches.
  - `[low]` `[reject]` Intent: Playwright runs on a stood-in api — the repo's pattern (11.3–11.6); the item's shape is the generated client's and the golden test asserts `type`, `title` and `wording` from the real api; a live e2e would need a played Class game and Replay in the browser.
  - `[low]` `[reject]` Intent: the Replay item reads the outcome, not a Week or Order — the shipped templates are draft content (issue #16); the `moment` and `pattern` kinds work on the Replay source too. Recorded as a founder decision.
  - `[false]` `[reject]` Intent: the count is not re-counted from the Decision log — `facts.seat.student_orders` is the `decided_by = student` count `analysis.facts` takes from the Decision log (`facts.py` 393), the one mapping.
  - `[low]` `[patch]` Intent: the newer-version test could not tell a frozen item from a pinned reader — the pin test now removes the pin, shows a second Student's open reads the newer version, and the first Student's items stay as frozen.
  - `[false]` `[reject]` Intent: `test_open.py` expectations edited — descriptive: an unplayed Class game now gives replacement items, asserted.
  - `[false]` `[reject]` Intent: `wording` key added to fixtures — descriptive: the new field of the item out.
  - `[false]` `[reject]` Intent: the pattern kind not covered through `build` — now covered (Verification row).

## Design Notes

- Replacement on every failure path keeps the weights comparable and the templates identical for every Student who gets Adapted items (FR-53); the failure paths should not occur after a real Replay but do for dev-stepped `replay` steps.
- Fact sets are read inside `open_attempt`'s transaction through `games.service.fact_set`, which stores a set in its own short transaction the first time; the attempt's transaction holds only the Class session's share lock, so nothing waits on it.

## Verification

**Commands:**
- `uv run pytest tests/individual_test tests/analysis/test_adapted.py tests/content tests/test_migrations.py tests/test_imports.py -q` -- pass
- `npm run typecheck && npx vitest run src/modules/tests` -- pass
- `npx playwright test e2e/individual-test.spec.ts --workers=4` -- pass

## Auto Run Result

Status: done

**Summary.** Adapted item templates are a new immutable content kind `adapted_templates`. Draft v1 is stored by migration 0125 and shipped as `files/adapted_templates.json`, with two templates: `tilpasset-eget-spill` (own game, a moment, meaning a Week and its Order with what the Seat saw) and `tilpasset-replay` (Replay, the Seat's outcome cost). The Start-date lock pins the version in `SessionRuntime.pins["adapted_templates"]`. The shape and the code renderer are pure (`analysis/adapted.py`): fact kinds `moment`, `pattern` and `outcome`, plain `{slot}`s only, Roles in Norwegian, numbers through `format_number` and `format_money`, and `apportion` for whole weights. `tests.commands.open_attempt` calls `tests.adapted.build` in its transaction. `build` finds the own game through `games.service.student_game` and the Replay through `replay.service.replay_game_of`, reads each stored facts set through `games.service.fact_set` (`get_or_create`), and freezes the Adapted items after the Core items as `{id, type: "adapted", weight, template_version, source, fact, fact_set_id, fact_ids, text: {text, ai_generated: false, llm_call_id: null}}`, carrying the session's Adapted total. With fewer than 10 own Orders (the facts set's `decided_by = student` count) the Student gets the question set's replacement items instead, scaled to the same total and frozen with `replaces: "few_orders"`. So does a Student whose own game, Replay or facts set cannot be read (`no_game`, `no_replay`, `facts_unavailable`), or for whom a template finds no fact (`unfilled`). An Adapted total of 0 serves neither. The page shows an Adapted item as «Tilpasset oppgave», labelled by its frozen text, and answers it as a long answer with 11.6's autosave. `save_answer` validates it as long-answer text.

**Files.**
- `backend/app/analysis/adapted.py` (new): template schema, `fill`, `apportion`, `ROLE_NAMES`.
- `backend/app/modules/content/{models,schemas,service,__main__}.py`, `README.md`, `files/adapted_templates.json` (new): the kind, reader, pin and CLI line.
- `backend/migrations/versions/0125_adapted_templates.py` (new): the kind constraint and v1.
- `backend/app/modules/sessions/service.py`: pin provider registered.
- `backend/app/modules/tests/adapted.py` (new): `build`. `commands.py`: freeze in `open_attempt`, `adapted` validation. `attempt.py` and `schemas.py`: `type: "adapted"`, `wording`. `README.md`.
- Tests: `tests/analysis/test_adapted.py` (new, 26), `tests/individual_test/test_adapted.py` (new, 9, including the golden test), and updated `test_open.py`, `test_content.py`, `test_lock.py`, `test_question_set.py`, `test_migrations.py` (head 0125).
- Frontend: `individual-test-page.tsx`, `nb.ts` (`types.adapted`), Vitest, `e2e/individual-test.spec.ts` (an Adapted item at 320/360/1440 with axe), and the generated `lib/api/{openapi.json,schema.ts}`.

**Review.** Four sonnet reviewers, 32 findings: high 0, medium 0, low 26, false 6. Patched 9 low rows: the docstrings (writes, the same templates only for pinned sessions, the CLI kind list), unused code removed, both texts checked absent from the logs, a new test for the pattern kind and `unfilled` through `build`, and a stronger frozen test (the pin removed, so a second Student reads the newer version and the first Student's items stay as they were). The remaining 17 low and 6 false findings were rejected, each with its reason in the triage log. Nothing deferred.

**Follow-up review: not recommended.** Patched: high 0, medium 0, low 9.

**Verification.**
- Backend: the full suite with `--maxprocesses=8` gave 3308 passed and 4 skipped. `ruff check` and `ruff format --check` are clean. The golden test runs about 8 s; it is marked `long` because it plays a 14-Week Class game and a 4-Week Replay. The other new tests run 1.3–1.6 s under parallel load, which is over the 1 s guideline: each locks a session through the sweep.
- Frontend: `tsc` is clean, Vitest 1070 passed, and `lint:colours`, `check:copy` and `next build` pass.
- Playwright on lane 2 (8081, stack rebuilt with this change): 114 passed across individual-test (now with an Adapted item at 320/360/1440 and axe, plus the live test, which now gets replacement items), homes, student-home, order-confirm, order-field, week-table, game-start and guided-week.

**Decisions taken for the founder.**
- Fact kinds are `moment`, `pattern` and `outcome`. A moment is chosen by highest later cost, then the earlier Week. A pattern counts only on Orders a Student placed. An outcome is the Seat's cost.
- The shipped draft asks about one own-game moment and the Replay's outcome, split 50/50 (both `[ASSUMPTION]` placeholder text, issue #16).
- Weights are whole percents by largest remainder, so 25 splits as 13 + 12.
- Every failure path, not only fewer than 10 Orders, gives the replacement items, tagged with the reason. An Adapted total of 0 gives no Adapted or replacement item.
- Draft templates do not refuse the production lock; the question set's draft refusal remains the gate.
- An Adapted item's `title` is its frozen text, and `wording` carries `{text, ai_generated, llm_call_id}` for 11.8. The type line reads «Tilpasset oppgave» `[ASSUMPTION]`.

**Personal data.** No new table. Frozen Adapted items in `test_attempts.items` hold text built from the Student's own game (facts only, no names). Answers live in `test_answers`, already noted.

**Residual risks.**
- Template ids are kept distinct from question-set ids, and matched to the Scoring guide's `adapted` questions, only by a test on the shipped files. Nothing enforces this when content is published.
- Tests that publish a template version briefly (they unpublish in `finally`) could race a parallel lock that pins `adapted_templates` (the same pattern as `test_interactive.py`).
- The implementation was done in the main context, not a subagent, per the team lead's brief.
