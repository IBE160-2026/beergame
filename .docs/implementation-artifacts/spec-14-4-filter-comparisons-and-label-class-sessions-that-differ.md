---
title: 'Story 14.4: Filter comparisons and label Class sessions that differ'
type: 'feature'
created: '2026-11-23'
status: 'done'
baseline_revision: '3f5f621dfe30e6950044c0950af5451eeefccb4d'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-14-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-14-3-compare-class-sessions-in-tverrklasse-statistikk.md'
warnings: ['oversized']
deferred:
  - summary: >-
      The same Game settings may hash to two filter options (and read as differing) if a locked snapshot and an unlocked row serialise them differently.
    evidence: |-
      Edge case 4. compare hashes the stored game_settings dict as written; aggregates are written after the Test deadline, when sessions are locked and keys come from the snapshot, so a mix is unlikely. Settle by writing one locked and one unlocked aggregate with equal settings and comparing tokens.
    location: >-
      backend/app/modules/reports/cross_class.py compare
    severity: medium (unverified)
---

<intent-contract>

## Intent

**Problem:** Tverrklasse-statistikk (14.3) puts every ready Class session side by side even when they were played with other Game settings, AI mode, model, prompts or Effort level, or tested on another question set, Item weights or Scoring guide, so a Lecturer can read a difference in setup as a difference in learning (FR-65, NFR-6). The stored comparability keys are not read or tested yet (14.3's deferred item).

**Approach:** `GET /api/class-statistics` takes one optional filter per dimension (Game settings, AI mode, model, prompt versions, Effort level), matches it against each aggregate's stored `keys`, and returns the filter options with counts, which Class sessions are compared, what each compared session differs in, and whether the Core-only score comparison is comparable. The page draws the filters as text-button toggles with `aria-pressed` and counts, and prints the difference label in each chart row, its `<title>`, and «Vis som tabell».

## Boundaries & Constraints

**Always:**
- Everything is computed in the api (`reports/cross_class.py`, a pure `compare(...)` over `(session_id, keys)` pairs) from `class_aggregates.keys` only; never live tables (AD-10, AD-14). Web formats only.
- Eight key dimensions, codes in the response: `game_settings`, `ai_mode`, `model` (`model_config_id`), `prompt_versions`, `effort_level`, `question_set` (`question_set_version`), `item_weights`, `scoring_guide` (id and version). A key absent from a stored aggregate reads as None and equals only None.
- Filter option value: a token, the first 16 hex of SHA-256 of the key's canonical JSON (`sort_keys`, compact). Query params `game_settings`, `ai_mode`, `model`, `prompt_versions`, `effort_level`, at most one value each, ≤ 64 chars; a token no ready session holds is ignored (reported `selected` nowhere). Sessions compared = ready (aggregate written) and matching every given filter (AND).
- Options per filter dimension: each distinct value among ready sessions, in first-seen order of the session list, `count` = ready sessions holding it that match the other dimensions' filters (faceted), `selected`, `label` (data, never Norwegian copy): `game_settings` → `"classic"` when `sessions.is_classic` holds (seed ignored), else None with `ordinal` (1, 2, … over non-classic values); `ai_mode` → the mode code; `model` → the model config's `spec.name` (read through `sessions.service.model_names`), the id when the config is gone, None without a model; `prompt_versions` → `"purpose version"` pairs sorted and joined with `", "`, None when none; `effort_level` → the level's `label` or name from the config, else the stored name, None when none. Plus `all_count` per dimension (sessions matching the other dimensions).
- Differs per compared session: for each of the eight keys where compared sessions do not all agree, the most common value is the reference; a session holding another value is labelled with that key; with no unique most common value every compared session is labelled. Waiting or filtered-out sessions get `[]`.
- `comparable` on score measures (`core.*` shown: `core.median`): True when every compared session holds the same `question_set`, `item_weights` and `scoring_guide`; False otherwise; None on other measures and with fewer than two compared sessions.
- Page: filters only when two or more sessions are ready; one group per dimension (label, «Alle» + options, one pressed per group, counts in `ink-secondary`), as `WallFilters`' `Group`; a change refetches with the params and a polite live line «Sammenligner {n} av {m} Klasseøkter.»; fewer than two compared → «Færre enn to Klasseøkter passer filtrene.» with filters kept. Each bar row and table row reads «{session} · Ulikt oppsett: KI-modus, modell»; each bar is an `aria-hidden` SVG whose `<title>` holds the row's full reading; the table gets a column «Ulikt oppsett» («–» when none). Score measure: a line «Skårene kan sammenlignes: samme spørsmålssett, vekter og vurderingsveiledning.» or «Skårene kan ikke sammenlignes: spørsmålssett, vekter eller vurderingsveiledning er ulike.» under its title, also in its table caption.
- Copy in `nb.ts` `crossClass`, new strings marked `[ASSUMPTION] Story 14.4`. Works unchanged without 14.7.

**Never:** no figure or label computed in the web app; no colour-only marking; no new table or migration; no name, e-mail or Student data in the response; no filter on question set, weights or guide (not in the story); no rating comparison.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| No filter, same keys | 3 ready, equal keys | all compared, `differs` empty, `comparable` true | — |
| One differs | A, B llm; C rule_based | C `differs=["ai_mode"]` (+ `model`, `effort_level` if those differ) | — |
| Two, tie | A llm, B rule_based | both labelled `ai_mode` | — |
| Filter AI mode | `ai_mode=<llm token>` | only A, B compared; measure values only A, B; counts faceted | — |
| Unknown token | `ai_mode=zzz` | ignored, all compared | — |
| Too long param | 65 chars | 422 | FastAPI validation |
| Score keys differ | item weights differ | `core.median.comparable=false`; sessions labelled `item_weights` | — |
| Old aggregate missing a key | no `scoring_guide` | None value; differs from sessions that hold one | — |
| Filter leaves one | 1 compared | measures over that one; page shows filter line | — |
| Waiting session | no aggregate | `compared=false`, `differs=[]`, not counted | — |

</intent-contract>

## Code Map

- `backend/app/modules/reports/cross_class.py` -- `class_statistics(user)` (lines 45-99): add filter args; read `class_aggregates.keys` beside `written_at`; pure `compare(keys_by_session, filters)` returning options, compared ids, differs, score comparability; `SHOWN` unchanged; `SCORE_MEASURES = {"core.median"}`.
- `backend/app/modules/reports/cross_class_schemas.py` -- add `compared`, `differs: list[DiffKey]` to `ComparedSessionOut`; `comparable: bool | None` to `ComparedMeasureOut`; new `FilterOptionOut` (`value`, `label`, `ordinal`, `count`, `selected`), `FilterOut` (`dimension`, `all_count`, `options`); `CrossClassOut.filters`, `compared`.
- `backend/app/modules/reports/class_report_routes.py` -- `get_class_statistics` (≈line 150): five optional `Query(max_length=64)` params, passed through.
- `backend/app/modules/sessions/service.py` -- `is_classic` (line 426) reused; add `model_names(ids) -> dict[str, tuple[str, dict[str,str]]]` (name and level labels) via `app.ai.config.get` (sessions already imports `config`). `comparability_source` (line 2865) is the stored-key source (read-only).
- `backend/app/modules/tests/service.py` `comparability_keys` (line 520) -- read-only; its keys get asserted.
- `backend/tests/reports/test_aggregates.py` -- `new_session`, `execute`, `statistics`, `header` helpers reused; new tests in `backend/tests/reports/test_cross_class_filters.py` (pure `compare` cases + one api test inserting `class_aggregates` rows for fresh sessions, no game played).
- Frontend: `src/modules/reports/cross-class-api.ts` (`useClassStatistics(filters)`, key includes filters, `placeholderData` keeps the previous answer), `cross-class.ts` (`differsText`, `optionName`, rows carry `differs`), `cross-class-page.tsx` (filter groups, live line, SVG bars with `<title>`, table column, score line), `cross-class.test.ts`, `src/copy/nb.ts` `crossClass`; regenerated `src/lib/api/openapi.json` + `schema.ts` (`uv run python -m app.openapi ../frontend/src/lib/api/openapi.json`, `npm run api:generate`); `e2e/cross-class.spec.ts` stub answers by query params.
- Pattern: `frontend/src/modules/games/wall-filters.tsx` `Group` (text buttons, `aria-pressed`, counts).

## Tasks & Acceptance

**Execution:**
- `backend/app/modules/reports/cross_class_schemas.py`, `cross_class.py`, `class_report_routes.py`, `sessions/service.py` -- filters, options, differs, comparability -- AC 1-3.
- `backend/tests/reports/test_cross_class_filters.py` -- every matrix row; the stored keys from an llm row with a lock snapshot (model, Effort level, prompt versions) and `item_weights`/`scoring_guide.version` present -- 14.3's deferred key item.
- Frontend api, helpers, page, copy, Vitest for `differsText`/`optionName`/rows; regenerate api client.
- `frontend/e2e/cross-class.spec.ts` -- filter toggles (`aria-pressed`, counts, refetch with param, live line), labels in bars, `<title>` and table, score line; axe at 320 and 1440 px.

**Acceptance Criteria:**
- Given three ready Class sessions where one is rule-based, when the Lecturer presses «LLM-spillere» under KI-modus, then the request carries that `ai_mode` token, only the two LLM sessions are drawn, the button has `aria-pressed="true"` and its count, and «Sammenligner 2 av 3 Klasseøkter.» is announced.
- Given compared sessions that differ on AI mode, when any measure is shown, then the differing session's bar row, its SVG `<title>` and its table row say «Ulikt oppsett: KI-modus».
- Given compared sessions with different Item weights, when `core.median` is shown, then it says the scores cannot be compared; with equal question set, weights and guide it says they can.

## Spec Change Log

## Review Triage Log

### 2026-11-23 — Review pass
- verdicts: 24 findings — high 0, medium 4, low 12, false 5, maybe-false 3
- findings:
  - `[medium]` `patch` Blind 1: missing score keys on every aggregate read as equal, scores called comparable — `compare` now requires all three keys present on every compared session; test added.
  - `[low]` `patch` Blind 2: docstring's two-reads claim ignores the model-name reads — docstring corrected.
  - `[false]` `reject` Blind 3: one compared session hides the comparability line — the spec sets `comparable` None under two compared and the page shows «Færre enn to…» instead; nothing is compared.
  - `[medium]` `patch` Blind 4: pressed state only from the server's `selected`, so a click shows no pressed button until the answer — `pressed` now comes from the Lecturer's choice when the options hold it (also Edge 8).
  - `[low]` `reject` Blind 5: equal live text after two changes is not re-announced — rare and needs a counter trick; the pressed button itself reports state.
  - `[low]` `reject` Blind 6: SVG `<title>` inside `aria-hidden` serves hover only — by design: the sr-only reading carries the same text; the story asks for the label in the chart's `<title>`.
  - `[low]` `reject` Blind 7: «Oppsett n» does not say what differs; equal model names collide — draft naming, founder decision recorded; needs a settings describer beyond the story.
  - `[low]` `reject` Blind 8: glossary casing and `Record<string,string>` maps — glossary terms are capitalised project-wide; fallbacks print the code.
  - `[low]` `reject` Blind 9: filters not in the URL, no clear-all — not asked; «Alle» per group resets.
  - `[medium]` `patch` Blind 10: `model_names` test passed vacuously (no seeded config in the test DB) — test now stores the mock config and checks name and level labels; other gap items low and rejected (tie of 3+ covered by the tie rule; booleans compare equal to 1/0 in Python).
  - `[low]` `reject` Blind 11: fixture imports from another test module, private `_keys` — the 14.3 test file uses the same pattern; `_keys` is the unit under 14.3's deferred item.
  - `[low]` `reject` Blind 12: stub hand-fakes faceting; `cn` import order — the backend tests cover `compare`; import order fixed with the pressed patch.
  - `[medium]` `patch` Edge 1: same as Blind 1 — patched there.
  - `[low]` `reject` Edge 2: an Effort level name shared by two models takes the first model's label — rare (levels are config-specific names); would need a compound token.
  - `[maybe-false]` `reject` Edge 3: `{}` vs None prompt versions — aggregates are written after lock, where an LLM session always has its config's map and a rule-based one None; would settle with a config with no prompts (low if real).
  - `[maybe-false]` `defer` Edge 4: snapshot vs row serialisation of equal Game settings — deferred (medium, unverified).
  - `[false]` `reject` Edge 5: non-object `keys` JSON — only `write_aggregate` writes it, always a dict.
  - `[false]` `reject` Edge 6: TypeError from GameSettings validation — pydantic raises `ValidationError`, a `ValueError`.
  - `[false]` `reject` Edge 7: one matching session, page discards measures — the matrix row says the page shows the filter line; the api still returns the one session's values.
  - `[low]` `patch` Edge 8: stale chosen token shows «Alle» while still sent — covered by the Blind 4 patch: an unknown value reads as «Alle» and the api ignores it.
  - `[low]` `reject` Edge 9: same as Blind 5.
  - `[low]` `patch` Edge 10: same as Blind 2.
  - `[maybe-false]` `reject` Edge 11: Effort label claim — same as Edge 2.
  - `[false]` `reject` Edge 12: same as Edge 7.

## Design Notes

Majority reference, not "the newest session": a Lecturer comparing five sessions where one was run with the rule-based players wants that one flagged, not the four others; a tie leaves no defensible reference, so both sides are labelled. Single-select per dimension (like the Matrisevegg's filters) keeps the toggles honest with `aria-pressed` and the query a simple AND. Tokens are hashes so Game settings and prompt-version dicts filter exactly as stored without the URL carrying their JSON.

## Verification

**Commands:**
- `cd backend && uv run pytest tests/reports/test_cross_class_filters.py tests/reports/test_aggregates.py -q -n 8` -- expected: pass
- `cd backend && uv run pytest -q -n 8 --maxprocesses=8` -- expected: pass
- `cd frontend && npm run typecheck && npx vitest run && npm run lint:colours && npm run check:copy && npm run build` -- expected: pass
- `cd frontend && npx playwright test cross-class homes order-field --workers=4` -- expected: pass

## Auto Run Result

Status: done
Blocking condition: none

**Summary.** `GET /api/class-statistics` takes one optional filter per dimension (Game settings, KI-modus, model, prompt versions, Innsatsnivå) as a hash token of the aggregate's stored key, compares only the ready Class sessions holding every given value, and returns per dimension the options (label as data, faceted counts, `selected`) and «Alle»'s count; per compared Class session what it differs in (eight keys, against the most common value, both sides on a tie); and on `core.median` whether the Core-only scores are comparable (same question set, Item weights and Scoring guide, all stored). The page shows the filters as text buttons with `aria-pressed` and counts, refetches on a press keeping the previous answer, announces «Sammenligner n av m Klasseøkter.» politely, labels a differing session «Ulikt oppsett: KI-modus, modell» in the bar row, the bar's SVG `<title>` and the table's new column, and prints the comparability line under the score chart and in its table caption.

**Files.**
- `backend/app/modules/reports/cross_class.py` — `compare` (pure), tokens, labels, filters; `cross_class_schemas.py` — `compared`, `differs`, `comparable`, `FilterOut`, `FilterOptionOut`; `class_report_routes.py` — five query params (≤ 64 chars).
- `backend/app/modules/sessions/service.py` — `model_names` (config name and level labels).
- `backend/tests/reports/test_cross_class_filters.py` (new) — matrix, api, stored keys (14.3's deferred item), model names.
- Frontend: `modules/reports/cross-class{,-api,-page}.ts(x)` + Vitest, `copy/nb.ts` (`[ASSUMPTION] Story 14.4`), regenerated `lib/api/openapi.json` and `schema.ts`, `e2e/cross-class.spec.ts`.

**Review.** Two layers (blind, edge case; sonnet), per the lane brief. Patched 3 medium (score keys absent read as comparable; pressed state from the Lecturer's choice; vacuous model-name test) and 2 low; deferred 1 (Game settings serialisation, unverified); rejected the rest with reasons in the triage log. Implemented in the builder's own context, as the lane brief directs, instead of a step-03 subagent.

**Follow-up review recommended: true** — two or more medium patches; the score-comparability rule change (all three keys must be stored) has been read by no reviewer.

**Verification.** Backend full suite (`-n 8`, lane-3 DB): 4279 passed, 5 skipped; after the patches `tests/reports/test_cross_class_filters.py`, `test_aggregates.py`, `test_imports.py`: 52 passed; new tests each under 1 s; ruff clean. Frontend: typecheck, Vitest 1382 passed, `lint:colours`, `check:copy`, `next build`. Playwright on the rebuilt lane-3 stack: `cross-class`, `homes`, `order-field` — 37 passed, axe at 320 and 1440 px (and 200 % text on the 14.3 test). Screenshots at 320 and 1440 px read by the builder.

**Decisions taken in the founder's place.** Reference for «what differs» is the most common value among the compared Class sessions, both sides labelled on a tie; one value per filter dimension (single-select, «Alle» per group), filters AND together, counts faceted over the other filters; all five dimensions always shown once two Class sessions are ready; Game settings named «Klassisk» or «Oppsett n»; scores comparable only when all three score keys are stored and equal; filters are not kept in the URL; draft copy.

**New personal-data tables.** None (no migration).

**Residual risks.** The deferred item.
