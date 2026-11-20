---
title: 'Story 5.5: Choose AI mode, Effort level and Debrief mode'
type: 'feature'
created: '2026-11-20'
status: 'done'
baseline_revision: 'a62fbe02c072d4e1fc609fcecbf5ffd4518d3ae1'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-5-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-5-4-choose-demand-pattern-and-seed.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** On the Klasseøkt, KI-modus and Debrief-modus are read-only text and there is no Effort level at all, so a Lecturer cannot choose which AI players the Students meet, how hard the LLM thinks, or how the Debrief is held (FR-15, FR-16, FR-78).

**Approach:** Store an Effort level and take `effort_level` and `debrief_mode` in «Lagre Klasseøkt»; the read returns the offered levels of the session's (or the default) model config, the AI player descriptions from `players.service.describe`, and a provider flag. On the screen the two blocks become Valgknapper (extended with an unavailable option) and a new Visningsbryter is added to `components/`; choices take effect only on save.

## Boundaries & Constraints

**Always:**
- Migration 0034: nullable `class_sessions.effort_level` (Text) with check `ai_mode = 'llm' OR effort_level IS NULL`. Creation with a default config stores its default level (first of `offered_effort_levels`); Rule-based stores NULL.
- `ai.config.EffortLevel` gains optional `label` and `effect` (Norwegian text, data in the config; None for rows stored before). `ai-configs/*.json` and `seed.MOCK_SPEC` get placeholder values (still equal). No level name, label or effect is written in `sessions` or the web app.
- Save body (`ClassSessionSaveIn`) adds optional `effort_level: str | None` and `debrief_mode: DebriefMode | None`; left out they keep their stored value. With `ai_mode` Rule-based the stored level becomes NULL and a sent level is ignored. With LLM: the level is the sent one, else the stored one, else the config's default; a level that changes must be among `offered_effort_levels(config)` of the config in force (the session's, or the default it takes in that save), else 422 `invalid_effort_level` `{"effort_level": "not_offered"}`, nothing stored.
- Locked (`is_locked`): a changed AI mode, Effort level or Debrief mode answers 409 `session_locked` with `fields` naming each (`ai_mode`, `effort_level`, `debrief_mode`); unchanged values save.
- `ClassSessionOut` adds `effort_level` (in force: stored, or the default for an LLM row stored before 0034; None for Rule-based), `effort_levels: [{name, label, effect, default, time_per_order_median_s, cost_per_game_usd}]` (offered levels of the session's config, else of the active default, else empty; figures from the newest counting measurement, decimal strings or None), `ai_descriptions: {llm, rule_based}` (texts from `players.service.describe`), `provider_unavailable: bool` (true when AI mode is LLM, the session has a config and that config offers no level here: the production case of a missing key).
- Web: «KI-modus» Valgknapper «LLM-spillere» / «Regelbaserte spillere», help «Gjelder alle KI-spillere i Klassespill og Replay.»; with `llm_unavailable` the LLM segment is `aria-disabled`, cannot be chosen, and the reason stands beside it (`aria-describedby`). Each option's description is reachable under the control (one disclosure per type). «Innsatsnivå» Valgknapper only while the draft says LLM and levels exist, one line per level (config effect, else measured «s per ordre · USD per spill», else a placeholder line); hidden for Rule-based. «Debrief-modus» Valgknapper «Gruppedebrief» / «Personlig debrief» with a help line for the chosen one. `provider_unavailable` shows a warning line in text. Choices are sent with «Lagre Klasseøkt» and take effect only then. Locked or not manageable: values as text, no control.
- `components/`: `SegmentedChoice` gets an optional per-option `unavailable` reason (aria-disabled, `future-tint`/`ink-muted`, never selectable, keyboard skips choosing it); new `ViewToggle` (Visningsbryter) for exactly two options with the same styling, keyboard and 44 px targets.
- All copy in `nb.ts`, new strings marked [ASSUMPTION].

**Never:** a hard-coded level, its label or effect in `sessions` or the web app; a description text written in `sessions`; comparing DB time with host time; touching the demo Class; changing Obligatorisk (5.7); a real LLM call; editing `sprint-status.yaml`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Create with default | default pinned (one level) | `ai_mode` llm, `effort_level` = default, `effort_levels` 1 entry `default: true` | – |
| Choose another level | config with two offered levels; save `effort_level` second | stored; read returns it | – |
| Not offered | `effort_level: "turbo"` | nothing stored | 422 `invalid_effort_level` |
| To Rule-based | save `rule_based` (+ any level) | `effort_level` NULL | – |
| Back to LLM | save `llm` without level | default level stored | – |
| No default model | create, then save `llm` | `llm_unavailable`, `effort_levels` [] | 409 `llm_unavailable` (5.1) |
| Debrief | save `personal` | stored; read `personal` | – |
| Locked | changed mode / level / debrief | nothing stored | 409 `session_locked` fields named |
| Locked unchanged | same values | 200 | – |
| Provider missing | LLM session, then production env with the mock config | `provider_unavailable` true | – |
| Descriptions | any read | `ai_descriptions` = `describe(kind).text` | – |

</intent-contract>

## Code Map

- `backend/app/ai/config.py:69-82` -- `EffortLevel`: add `label`, `effect`. `offered_effort_levels` (739), `OfferedLevel`, `EffortMeasurement` figures, `active_default` (801).
- `backend/app/ai/seed.py:24` `MOCK_SPEC`, `backend/ai-configs/*.json` -- equal (test `tests/ai/test_effort.py:271`).
- `backend/app/modules/players/service.py:161` -- `describe(kind).text` (markdown: `# Title`, paragraphs, `- ` list).
- `backend/app/modules/sessions/models.py`, `migrations/versions/0034_class_session_effort_level.py` (new, after 0033).
- `backend/app/modules/sessions/service.py` -- `create_session` (store default level), `get_session` (new fields), `save_session` (lock checks 512, level/debrief rules, new `InvalidEffortLevel(_FieldsError)` 422), `repo.save` gets `effort_level`, `debrief_mode`.
- `backend/app/modules/sessions/{schemas,routes}.py`, `README.md` -- `OfferedEffortLevelOut`, `AiDescriptionsOut`, save-in fields, route docstring + 422 mapping.
- `backend/tests/sessions/test_class_sessions.py` (`default_model`, `create`, `save`, `stored`), `test_dates.py` (`at`, `PLAN`, `new_session`), `tests/ai/test_effort.py:55` `set_env`/`enter_production` -- new `tests/sessions/test_ai_mode.py`.
- `frontend/src/components/segmented-choice.tsx`, new `view-toggle.tsx`, `components.test.tsx`.
- `frontend/src/modules/sessions/class-session-page.tsx` -- `Choices` (253) becomes the editor; state beside `inputs`; `saveClassSession` call (108).
- `frontend/src/modules/sessions/api.ts` -- `saveClassSession` body; new `choices.ts` (+ test) for effect line, description paragraphs, body.
- `frontend/src/copy/nb.ts:859` `sessions.choices`; `lib/api/{openapi.json,schema.ts}` regenerated (`cd backend && uv run python -m app.openapi ../frontend/src/lib/api/openapi.json`, then `npm run api:generate`).
- `frontend/e2e/class-session-choices.spec.ts` (new); helpers `e2e/support/classes.ts` (`freshLecturer`, `freshClass`, `expectAccessible`), patterns from `class-session-demand.spec.ts`.

## Tasks & Acceptance

**Execution:**
- `backend/app/ai/config.py`, `seed.py`, `ai-configs/*.json` -- `label`/`effect` fields with placeholders.
- `backend/migrations/versions/0034_*.py`, `sessions/models.py`, `repo.py`, `service.py`, `schemas.py`, `routes.py`, `README.md` -- storage, save rules, read fields.
- `backend/tests/sessions/test_ai_mode.py` (new) -- every matrix row through the routes.
- `frontend/src/components/segmented-choice.tsx`, `view-toggle.tsx`, `components.test.tsx` -- unavailable option, Visningsbryter.
- `frontend/src/modules/sessions/choices.ts` + `choices.test.ts`, `class-session-page.tsx`, `api.ts`, `src/copy/nb.ts`, regenerated api types -- the editor.
- `frontend/e2e/class-session-choices.spec.ts` (new) -- choose Rule-based (Innsatsnivå hides), Personal debrief, save and reload; LLM unavailable via fulfilled GET (aria-disabled + reason); provider flag line; locked read-only (fulfilled GET); keyboard choice; axe at 320/360/1440 and 400 % zoom.

**Acceptance Criteria:**
- Given the Klasseøkt, when it renders, then KI-modus and Debrief-modus are Valgknapper from `components/`, operable by keyboard with 44 px targets, and a choice changes nothing stored until «Lagre Klasseøkt».
- Given LLM players, then «Innsatsnivå» shows only the offered levels with one effect line each and the default preselected; given Rule-based, it is hidden.
- Given no model config and no default, then «LLM-spillere» is `aria-disabled` with the reason beside it and Rule-based is selected.
- Given `provider_unavailable`, then the screen states the Class session cannot open with LLM players until the provider is set up.
- Given a locked session, then the values show as text and the api answers 409 `session_locked` for a change.

## Spec Change Log

## Review Triage Log

### 2026-11-20 — Review pass
- verdicts: 33 findings — high 0, medium 2, low 24, false 7, maybe-false 0
- findings:
  - `[medium]` `[patch]` (blind) The config's effect line hides measured figures; the shipped placeholder says "not measured" even for a measured level. `effectLine` now puts measured figures first, then the config line, then the placeholder (`choices.test.ts`).
  - `[false]` `[reject]` (blind) Backend and web pick the default level by different rules. `offered_effort_levels` sets `default` on index 0 only, so `offered[0]` and the flag always name the same level.
  - `[low]` `[patch]` (blind) A stored level no longer offered shows no radio checked and is sent back. `choicesOf` gives way to the default when the level in force is not offered (`choices.test.ts`).
  - `[low]` `[reject]` (blind) An LLM session can hold a NULL level when its config offers nothing. That is the provider-missing state the screen flags and the lock (5.11) refuses; requiring a level would block saving any other change.
  - `[low]` `[reject]` (blind) 0034 does not backfill LLM rows. A backfill would read `ai` tables from a `sessions` migration (AD-6); old rows read their own config's default, which a pin does not change. Now pinned by a test.
  - `[low]` `[patch]` (blind) The read-only view hides the level when nothing is offered. The text line shows whenever a level is in force.
  - `[false]` `[reject]` (blind) `session_locked` names dates. `copy.dates.locked` reads «Klasseøkten har startet. Innstillingene kan ikke endres lenger.», covering every setting.
  - `[low]` `[patch]` (blind) The provider warning (before the Start date / choose Rule-based) shows after the start. Shown only while unlocked.
  - `[false]` `[reject]` (blind) No config and a default that offers nothing goes unflagged. `active_default` skips such configs, so the session reads `llm_unavailable` and LLM is refused.
  - `[low]` `[patch]` (blind) Each level's description repeats its name. The radio points at the effect text only (e2e asserts it).
  - `[low]` `[reject]` (blind) `flex-1` → `flex-auto` changes every Valgknapper. Deliberate: mockup 03 sizes segments to their labels, and «Regelbaserte spillere» wrapped at 1280 px; the invite form's e2e passes.
  - `[false]` `[reject]` (blind) `ViewToggle` is unused code outside the story. The story's first criterion asks for it in `components/` for reuse.
  - `[low]` `[reject]` (blind) Arrow keys can rest focus on the unavailable option. Keeping focus is UX-DR8 for unavailable controls; React restores the checked state at once.
  - `[low]` `[patch]` (blind) The description parser drops any `#` line and keys items by text. Only the title line is dropped; items keyed by index (`choices.test.ts`).
  - `[low]` `[patch]` (blind) `effort_level` in the save body is unbounded. `Field(min_length=1, max_length=64)`.
  - `[false]` `[reject]` (blind) `InvalidEffortLevel` may not be logged. It is a `_FieldsError` raised inside the try and logged as `class_session_refused`.
  - `[low]` `[patch]` (blind) Missing backend tests. Added the pre-0034 row and the CHECK rejecting a level on a Rule-based row; the stale level is covered on the screen side; the Assistant view reuses the tested read-only path (that part rejected).
  - `[low]` `[reject]` (blind) `get_session` reads the config in several transactions. A pin changing mid-read is rare and the next read corrects it; joining them adds plumbing across `ai.config`.
  - `[low]` `[reject]` (edge) A Rule-based row holding an old config whose provider offers nothing does not take the working default on LLM. Production-only after a key is removed; the screen then flags `provider_unavailable`; fixing needs a new adoption branch.
  - `[low]` `[reject]` (edge) The read shows offered levels from that stale config. As above.
  - `[medium]` `[patch]` (edge) Placeholder effect line hides measured figures. As blind row 1.
  - `[low]` `[patch]` (edge) Stale level leaves no radio checked. As blind row 3.
  - `[low]` `[patch]` (edge) Read-only view hides the level when nothing is offered. As blind row 6.
  - `[false]` `[reject]` (edge) The 409 shows a dates message. As blind row 7.
  - `[low]` `[patch]` (edge) Duplicate list keys. As blind row 14.
  - `[low]` `[patch]` (edge) A body line starting with `#` is dropped. As blind row 14.
  - `[low]` `[patch]` (verification-gap) `invalid_effort_level` has no screen test. e2e routes the PUT to 422 and expects `effortRefused` in the alert.
  - `[low]` `[patch]` (verification-gap) Pre-0034 LLM rows untested. `test_an_llm_row_stored_before_the_level_reads_and_saves_the_default`.
  - `[low]` `[patch]` (verification-gap) `label`/`effect` length limits untested. Four cases in `test_config.py`'s refusal table.
  - `[low]` `[reject]` (intent) Some effect wording comes from the web app. Only when the config has no line and the level no figures; no level is named in the web app.
  - `[low]` `[reject]` (intent) Descriptions sit in two disclosures under the control, not on each segment. A multi-paragraph text cannot sit in a segment or its `aria-describedby`; each disclosure names its type.
  - `[false]` `[reject]` (intent) Default by position vs flag. As blind row 2.
  - `[low]` `[reject]` (intent) Unavailable, provider and locked screens are tested with rewritten GETs. The local stack always has the seeded default; the real states are pinned through the routes in `test_ai_mode.py`, as in 5.3 and 5.4.

## Design Notes

- Effect line from data: the config's `effect` text when set, else the measured median time and cost per game, else a placeholder. The seeded mock has no figures, so local screens show the config text (new seeds) or the placeholder (rows seeded earlier).
- `provider_unavailable` is derived from `offered_effort_levels` being empty for a config the session holds: the one public signal `ai.config` gives; `sessions` may not import `ai.adapters`.
- Read-only means text, as the settings list does when locked.

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/sessions tests/ai/test_effort.py -q` -- pass, each test under 1 s.
- `cd backend && uv run pytest -q && uv run ruff check . && uv run ruff format --check .` -- pass.
- `cd frontend && npm run typecheck && npm test && npm run check:copy && npm run lint:colours && npm run build` -- pass.
- `cd frontend && npx playwright test` against `timeout 900 docker compose up -d --build --wait proxy worker-batch` -- pass.

## Auto Run Result

Status: done

**Summary.** KI-modus, Innsatsnivå and Debrief-modus are choices on the Klasseøkt that take effect with «Lagre Klasseøkt». `class_sessions.effort_level` (migration 0034) holds the level in force, empty for Rule-based players. The save takes `effort_level` and `debrief_mode`: a level the config does not offer is 422 `invalid_effort_level`; any changed choice once locked is 409 `session_locked` with the fields named. The read adds the offered levels (`ai.config.offered_effort_levels` with the config's new `label`/`effect` and measured figures), the AI player descriptions (`players.service.describe`) and `provider_unavailable`. Valgknapper gains an unavailable option (`aria-disabled`, reason beside it); Visningsbryter (`components/view-toggle.tsx`) is added for reuse.

**Files changed**
- Backend: `ai/config.py` (`label`, `effect`), `ai/seed.py`, `ai-configs/*.json` (placeholders); `migrations/versions/0034_class_session_effort_level.py`; `sessions/{models,repo,service,schemas,routes}.py`, `README.md`; tests `sessions/test_ai_mode.py` (new), `test_migrations.py` (head 0034, 0034 test), `ai/test_config.py`.
- Frontend: `components/segmented-choice.tsx`, `view-toggle.tsx` (new), `components.test.tsx`; `sessions/choices.ts` + test (new), `class-session-page.tsx`, `api.ts`; `copy/nb.ts`; regenerated `lib/api/{openapi.json,schema.ts}`; e2e `class-session-choices.spec.ts` (new).

**Review findings.** 33: 0 high, 2 medium, 24 low, 7 false. Patched: measured figures before the config's effect line (one medium root cause, reported twice), a stale level gives way to the default, read-only level line, provider warning only before the start, effect-only radio description, title-only Markdown drop and index keys, bounded `effort_level`, and tests (pre-0034 row, CHECK, length limits, `invalid_effort_level` alert). Deferred: none. Rejected: the rest, each with its reason in the triage log.

**Follow-up review recommended: false.** One medium root cause was patched and is pinned by a unit test; no unverified risk can be named.

**Verification**
- Backend: 2393 passed in 63 s; ruff check and format clean. New tests each under 1 s; the 1.6 s seen once was the first test's session setup (0.5 s on rerun).
- Frontend: typecheck, Vitest (406), `check:copy`, `lint:colours`, `build` pass. Playwright 216/216 on the rebuilt stack.
- Screenshots at 390 and 1280 px checked by eye.
- Migration 0034 is new and ran on the shared test databases.
- Implementation and review fixes were done in this context (caller's instruction), not by a step-03 subagent.

**Decisions taken in place of the founder**
- Effort levels get optional `label` and `effect` in the model config (placeholders now). The line shows measured figures first, then the config line, then «ikke målt ennå». The local mock config seeded before this story has neither, so local screens show «standard» with the placeholder line until re-seeded.
- `provider_unavailable` is set when the session's config offers no level here; its warning shows only before the start.
- Descriptions open in two «Slik bestiller …» disclosures under KI-modus.
- Personlig debrief help «Hver student går gjennom det alene.» and the other new strings are [ASSUMPTION].
- Locked or Assistant: choices as text. Valgknapper segments size to their labels.

**Residual risks**
- A Rule-based session holding an old config whose provider lost its key does not take a working default when switched to LLM (production only; flagged on screen).
- The unavailable, provider and locked screens are tested with rewritten GETs; the real states are pinned at the api.
