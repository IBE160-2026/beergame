---
title: 'Story 10.1: Get a default Replay scenario that differs per Student'
type: 'feature'
created: '2026-11-21'
status: 'done'
baseline_revision: 'd3a95ecc127b9900199a54ba9772ea90e89364e2'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-10-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** FR-49 gives the Replay a per-Student scenario (ranged step Week and length, varied demand), but `engine.GameSettings` holds single values, the spine leaves "Replay scenario as a template" deferred, and a Class session has no Replay scenario at all.

**Approach:** Add a pure, versioned `engine.ReplayTemplate` (every `GameSettings` field fixed or a whole-number range), `engine.default_replay_template(settings)` (one rule per Demand pattern kind), `engine.replay_settings(template, seed)` (the one resolver), template validation through `engine.validate`, and `engine.replay_template_admits` (is these settings one draw of the template). Store only the choice `default` on `class_sessions`, pin the derived template at the lock, show it in words on the Klasseøkt, let `python -m app.sim run` play default-Replay batches, and calibrate the Play guard for it through a new parameter set.

## Boundaries & Constraints

**Always:** engine code stays pure (no I/O, no clock, all randomness from the passed seed; SHA-256 draws like `demand.py`). The template is derived from the session's current Game settings on every read before the lock; after the lock the pinned template is read. Validation of a template reuses `engine.validate` (same codes, same `SettingsError` with the range). UI copy only in `frontend/src/copy/nb.ts`. The Lecturer sees the ranges; no Student surface shows the template.

**Never:** no copy of the default template in `class_sessions`; no change to `sessions.lock`'s mechanism; no editing of the scenario (Story 10.2), no Replay Game creation (10.3); no change to the existing `placeholder-0` Play guard set (Games frozen at its version 1 must keep working); no new Python dependency; no tests that play a Game each.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Classic default | `default_replay_template(GameSettings())` | step 4→8, spread 2, change Week 5–12, Weeks 30–40, Guided 0, rest Classic | — |
| Step+noise spread 3 | Class `step+noise` spread 3, start 6, new 10 | template keeps 6/10, spread 3 | — |
| Random | Class `random` mean 5 spread 1 | template random mean 5 spread 2, no change Week | — |
| Fixed | Class fixed series of 36 values | template fixed, those values, spread 2; resolved series holds the last value past Week 36 | — |
| Resolve twice | same template, same seed | identical `GameSettings` and `demand_series` | — |
| Bad seed | seed −1, > `SEED_MAX`, or not an `int` | — | `ValueError` |
| Change Week after the Game | template change Week 5–40, Weeks 30–40 | `validate_template` → `demand_change_week_outside_game`, range 1–30 | rejected |
| Inverted range | Weeks `{minimum: 40, maximum: 30}` | `validate_template` → `range_inverted` on `weeks` | rejected; `replay_settings` raises `ValueError` |
| Out-of-range bound | order delay 1–4 | `out_of_range` on `order_delay`, range 1–3 | rejected |
| Guided vs change | Guided 0–6, change Week 5–12 | `guided_weeks_not_before_demand_change` | rejected |

</intent-contract>

## Code Map

- `backend/app/engine/settings.py` -- `GameSettings`, `RANGES`, `validate`, `_check_range`, `SettingsError`; the template mirrors its fields.
- `backend/app/engine/demand.py` -- pattern kinds, `_noise(seed, week, spread)`, `SEED_MAX`; reuse `_noise` for the fixed-series variation so it matches `step+noise` draws.
- `backend/app/engine/__init__.py` -- public engine surface; export the new names. `engine/replay.py` is the Decision-log replay (unrelated name clash: new module is `engine/scenario.py`).
- `backend/app/analysis/play_guard.py` -- `PlayGuardParams.calibrated_profiles: dict[str, GameSettings]`, `is_calibrated` (exact match minus seed).
- `backend/app/parameter_sets/play_guard/placeholder-0.json` -- current set (version 1, `classic`). `games/commands.py:111` `DEFAULT_PLAY_GUARD_SET`; `_frozen_play_guard` refuses a changed version (409), hence a new set id instead of a version bump.
- `backend/app/modules/sessions/service.py:2878-2938` -- `register_pin_provider`, `debrief_ai_text_pin` pattern; `build_snapshot` sorts providers; `get_session` (~743) builds `ClassSessionOut`.
- `backend/app/modules/sessions/{models.py:83,schemas.py:187}` -- `class_sessions` table, `ClassSessionOut`.
- `backend/migrations/versions/0112_debrief_narration.py` -- add-column pattern; next is `0114`.
- `backend/app/sim.py:1035-1166` -- `BatchFile`, `Batch`, `load_batch`, `_play_one` (Game i uses demand seed `seed + i`).
- `backend/tests/sessions/test_lock.py:84-101` -- asserts the full pins map; `tests/sessions/test_settings.py:25` PUT body with `game_settings`.
- `backend/tests/{analysis/test_play_guard.py,games/test_create.py:64,games/test_play_guard_switch.py:229}` -- pin the default set id.
- `backend/tests/test_migrations.py:117,300` -- `HEAD`, downgrade walk.
- `frontend/src/modules/sessions/class-session-page.tsx:408-416` -- `Choices` then save row; the Replay block goes between.
- `frontend/src/modules/sessions/api.ts`, `frontend/src/lib/api/{openapi.json,schema.ts}` -- `ClassSession` type from the generated schema (`npm run api:generate` after exporting openapi).
- `frontend/e2e/support/classes.ts` -- `freshLecturer`, `freshClass`, `expectAccessible`.
- `.docs/planning-artifacts/architecture/architecture-beergame-2026-11-12/ARCHITECTURE-SPINE.md:369,572` -- Settings convention row, Deferred entry to close.

## Tasks & Acceptance

**Execution:**
- `backend/app/engine/scenario.py` (new) -- `IntRange`, `Ranged = int | IntRange`, demand templates `ReplayStep{start,new_level,change_week:Ranged,spread}`, `ReplayRandom{mean,spread}`, `ReplayFixed{values,spread}`, `ReplayTemplate{schema_version: 1, every GameSettings field; int fields Ranged}`; `default_replay_template`, `replay_settings`, `validate_template`, `replay_template_admits`; constants `DEFAULT_SPREAD=2`, `DEFAULT_CHANGE_WEEK=5–12`, `DEFAULT_WEEKS=30–40`.
- `backend/app/engine/__init__.py` -- export them.
- `backend/tests/engine/test_scenario.py` (new) -- per-kind default rules, determinism, golden for seeds 1/2/3, property over 500 seeds, validation errors (matrix), admits, purity (engine purity test already covers the package).
- `backend/app/analysis/play_guard.py` + `play_guard.md` -- profiles accept `GameSettings | ReplayTemplate` (left-to-right union); `is_calibrated` uses `replay_template_admits` for templates.
- `backend/app/parameter_sets/play_guard/placeholder-1.json` (new) -- placeholder-0's values plus `replay_default` = `default_replay_template(GameSettings())`; `games/commands.py` `DEFAULT_PLAY_GUARD_SET = "placeholder-1"`; tests updated; test that a default Replay counts as calibrated and an own scenario does not, and that the JSON equals the derived template.
- `backend/migrations/versions/0114_replay_scenario.py` (new) -- `class_sessions.replay_scenario text NOT NULL DEFAULT 'default'`, check `IN ('default')`; `test_migrations.py` HEAD + downgrade.
- `backend/app/modules/sessions/{models,schemas,service,README}` -- column; `ClassSessionOut.replay_scenario` + `replay_template`; pin provider `replay_template` (template JSON); view reads the pin once locked, else derives.
- `backend/tests/sessions/test_replay_scenario.py` (new) + `test_lock.py` -- view derives from edited settings; edit settings, lock, pinned template equals the edited derivation.
- `backend/app/sim.py` + `tests/test_sim.py` -- batch key `scenario: "replay_default"` (not with `demand`); Game i plays `replay_settings(default_replay_template(settings), seed + i)`; test the load and the per-Game settings without playing.
- `frontend/src/copy/nb.ts`, `frontend/src/modules/sessions/replay-scenario.{ts,tsx,test.ts}` (new), `class-session-page.tsx` -- block «Replay-scenario»: «Standard», a short data list (demand, change Week range, Weeks range, Guided Weeks), and the line that the drawn values differ per Student and stay hidden.
- `frontend/e2e/class-session-replay.spec.ts` (new) -- block text follows an api edit of the settings; axe at 320 and 1440.
- Spine Settings row + Deferred entry closed; `open-assumptions.md` draft-copy line.

**Acceptance Criteria:**
- Given the Classic settings, when `replay_settings(default_replay_template(GameSettings()), seed)` runs for any seed, then the change Week is 5–12, Weeks 30–40, Guided 0, every demand value a whole number ≥ 0 within 2 of its level, and the settings pass `engine.validate`.
- Given a Class session before the Start date, when a Lecturer edits its Game settings and reads it, then `replay_template` is derived from the edited settings and `replay_scenario` is `default`; when it is locked, then `SessionRuntime.pins.replay_template` holds that derivation.
- Given the Klasseøkt, when the Replay block shows, then it names the default scenario and describes it in words, passes axe at 320 and 1440 px.
- Given a batch file with `"scenario": "replay_default"`, when `python -m app.sim run` loads it, then Game i is created with the resolved settings of seed `seed + i`.

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
Four layers (sonnet): blind hunter, edge-case hunter, verification gap, intent alignment. Every hand-back failed; findings were read from `review-{blind,edge,verification,intent}-10-1.md` in the scratchpad.
- verdicts: 34 findings — high 0, medium 8, low 13, false 13, maybe-false 0 (the 7 intent observations are descriptive and logged as false: scope of later stories)
- findings:
  - `[low]` `[patch]` (blind 1) `ReplayFixed.spread` never range-checked — `_fixed_noise_errors` checks it against `DEMAND_RANGES["spread"]`; test added.
  - `[medium]` `[patch]` (blind 2) a fixed series near 100 plus spread draws values over 100, which `validate` (and so `games.commands.create`) refuses — drawn values are bounded at the values maximum (or the level, were it higher) as they are floored at 0; `admits` uses the same bound; test over 60 seeds.
  - `[false]` `[reject]` (blind 3) the lock pins an unvalidated default — a default derived from valid settings is always valid (Guided 0, change Week ≤ 12 < 30 Weeks, levels copied); tests validate the default of every kind.
  - `[medium]` `[patch]` (blind 4) pre-10.1 pin-less fallback untested — grouped with verification 1.
  - `[false]` `[reject]` (blind 5) Students may see the ranges — no route returns `GameOverview.session_runtime`; `ClassSessionOut` needs `class_sessions.read` (staff only, existing authz tests).
  - `[low]` `[reject]` (blind 6) `hiddenNone` wrong with spread 0 / other ranged fields — unreachable while only the default exists; Story 10.2 owns the own-scenario copy and needs new branches.
  - `[low]` `[patch]` (blind 7) `{0,0}` shows «0», fixed 0 «Ingen» — `count` treats a one-value range as its value; Vitest case added.
  - `[false]` `[reject]` (blind 8) generated api types missing — left out of the review diff on purpose; regenerated, typecheck passes.
  - `[low]` `[patch]` (blind 9) sim batch silently overrides `settings.weeks`/`guided_weeks` under a scenario — refused with `BatchError`; test added.
  - `[low]` `[patch]` (blind 10) `play_guard.md` names only `placeholder-0` values — heading and note cover both sets; a test keeps their values equal.
  - `[low]` `[reject]` (blind 11) union of profiles gives mixed errors — developer-only config file; invalid sets are refused by existing tests; a discriminator adds surface.
  - `[low]` `[reject]` (blind 12) `week_noise` pass-through — keeps `_noise` private for its cached caller; renaming touches more code.
  - `[false]` `[reject]` (blind 13) 500-seed loop slow, goldens brittle, short fixed admits untested — the loop is under 0.3 s (durations), goldens are the AC, the short-series test asserts `admits`.
  - `[medium]` `[patch]` (edge 1) fixed series with spread and Guided Weeks ≥ 2 validates on levels but noisy draws change from Week 2 — `_fixed_noise_errors` refuses Guided Weeks above 1 then (range 0–1); test resolves 40 draws through `validate`.
  - `[medium]` `[patch]` (edge 2) = blind 2.
  - `[medium]` `[patch]` (edge 3) empty/duplicate roles or capacity outside the chain escape as `ValidationError` from a draw — `ReplayTemplate` now applies the `GameSettings` chain rules at parse; tests added.
  - `[low]` `[patch]` (edge 4) other `GameSettings` refusals at a corner — grouped with edge 3; remaining field types (`Whole`, `Level`) already match.
  - `[low]` `[reject]` (edge 5) a future template `schema_version` — no bump exists; an upgrade comes with it, as `GameSettings` did.
  - `[false]` `[reject]` (edge 6) unreadable `game_settings` breaks the read — `get_session` already validates them (service.py ~765) before the template.
  - `[low]` `[reject]` (edge 7) `hiddenLine` with only the change Week ranged — as blind 6.
  - `[low]` `[patch]` (edge 8) = blind 7.
  - `[low]` `[patch]` (edge 9) = blind 9.
  - `[medium]` `[patch]` (edge 10) Design Notes claim corners reach every rule — false for a noisy fixed series; fixed by edge 1's code (spec text outside the code not edited).
  - `[medium]` `[patch]` (edge 11) AC1 claim for a fixed series near 100 — fixed by blind 2's bound.
  - `[medium]` `[patch]` (verification 1) the read of the pin is not observable — `test_replay_scenario.py` now rewrites the pinned `weeks` and expects it back, then removes the pin and expects the derived default on the locked session.
  - `[low]` `[reject]` (verification other 1) `test_content` compares the pin to itself — the full value is asserted in `test_lock.py`.
  - `[false]` `[reject]` (verification other 2) no Vitest render of the block — the e2e asserts the rendered rows and axe.
  - `[false]` `[reject]` (intent 1) no Replay reads the pin, no Student seed — Story 10.3 owns Replay creation.
  - `[false]` `[reject]` (intent 2) the choice is not selectable — Story 10.2.
  - `[false]` `[reject]` (intent 3) template validation not wired to an api — no api takes a template until Story 10.2.
  - `[false]` `[reject]` (intent 4) sim not played in tests — the shipped batch was run on the lane stack: 10 Games, Weeks 33/37/36… matching the goldens, all checks ok.
  - `[false]` `[reject]` (intent 5) new set id instead of version 2 — a recorded decision (see Auto Run Result).
  - `[false]` `[reject]` (intent 6) decision recorded in spine, not story — recorded in this spec too.
  - `[false]` `[reject]` (intent 7) copy is draft — listed in `open-assumptions.md` as the AC asks for nb.ts copy.

## Design Notes

Resolution draws each ranged field independently: `minimum + int(SHA-256("replay:{seed}:{field}")) mod (span)`; the demand seed of the resolved settings is the passed seed itself, so step+noise and random series come from `demand.series` and a fixed series uses the same `_noise(seed, week, spread)`. A step template with spread 0 resolves to `step`, else `step+noise`; random keeps `random`; fixed resolves to a `fixed` series of the drawn length (last value held, noise added, floored at 0).

Validation runs `engine.validate` on four corner draws (all minima; all maxima; Weeks min with change Week max and Guided max; Weeks min with change Week min and Guided max), after bound checks of each range against `RANGES`; the first error per field is kept. That catches every cross-field rule `validate` has, since each is monotone in its fields.

## Auto Run Result

Status: done

**Summary.** `engine/scenario.py` adds `ReplayTemplate` (schema 1; whole numbers fixed or `IntRange`; demand `step`/`random`/`fixed` with a spread), `default_replay_template`, `replay_settings(template, seed)` (SHA-256 draws per field; the seed is the `demand_seed`), `validate_template` (corner draws through `engine.validate`, plus inverted ranges, bounds and the fixed-series variation) and `replay_template_admits`. `class_sessions.replay_scenario` (0114, `default` only) holds the choice; the Klasseøkt reads `replay_template` (derived before the lock, the pin after); the lock pins `replay_template`. A read-only «Replay-scenario» block shows it in words. `python -m app.sim run` takes `"scenario": "replay_default"` (shipped `batches/replay-default-rule-based.json`). The Play guard accepts template profiles; `placeholder-1` adds `replay_default` and is the new default set. Spine Settings row and Deferred entry closed.

**Files.** Backend: `engine/{scenario.py (new),__init__,demand}` (`week_noise`), `analysis/play_guard.{py,md}`, `parameter_sets/play_guard/placeholder-1.json` (new), `modules/games/commands.py` (default set), `modules/sessions/{models,schemas,service,README}`, `migrations/versions/0114_replay_scenario.py` (new), `sim.py`, `batches/replay-default-rule-based.json` (new); tests `engine/test_scenario.py`, `sessions/test_replay_scenario.py`, `test_sim_replay.py` (new), `analysis/test_play_guard.py`, `sessions/test_lock.py`, `content/test_content.py`, `games/{test_create,test_play_guard_switch}.py`, `test_migrations.py`. Frontend: `copy/nb.ts`, `modules/sessions/{replay-scenario.ts,replay-scenario-block.tsx,replay-scenario.test.ts}` (new), `class-session-page.tsx`, regenerated `lib/api/{openapi.json,schema.ts}`, `e2e/class-session-replay.spec.ts` (new). Docs: spine, `open-assumptions.md`, `epic-10-context.md` (new).

**Decisions the founder would otherwise take.** (1) New Play guard set `placeholder-1` instead of version 2 of `placeholder-0`: `_frozen_play_guard` refuses a Game whose frozen version changed, so a bump would break every running Game frozen on version 1. (2) Template profiles in `calibrated_profiles` count every draw (`replay_template_admits`). (3) The resolved demand: a step template with spread 0 is `step`, else `step+noise`; random stays `random`; fixed becomes a `fixed` series of the drawn length (last value held, noise added, bounded 0 to 100). (4) Only whole-number top-level fields and the change Week can be ranged; levels and costs are fixed. (5) The Lecturer sees the ranges (5–12, 30–40); the block lists demand, change Week, Weeks, Guided Weeks, «Resten: Som Spillinnstillingene» (draft copy). (6) The lock line now names «Replay-scenario» among the frozen values. (7) The pin holds the template JSON only (the choice stays in the column). (8) The random/fixed default rules follow the story's [ASSUMPTION].

**Review.** 34 findings: 11 patched (4 medium entries, low ones direct), 0 deferred, the rest rejected with reasons in the triage log. `followup_review_recommended: true`: the medium patches (bounded fixed-series noise, Guided Weeks vs a varying fixed series, template chain validators, pin-read tests) were not re-reviewed independently.

**Verification.** Full backend suite `--maxprocesses=8`: 3046 passed, 4 skipped (after fixes). Engine coverage 100 %. ruff check/format clean. Frontend typecheck, Vitest 788 passed, `check:copy`, `lint:colours`, build passed. Playwright (`--workers=4`): class-session (replay, base, lock, choices, settings), homes and the play-screen specs passed before the review fixes (62 + 89); after the fixes and a stack rebuild the same set ran again: 151 passed (axe at 320 and 1440 px in the new spec). `python -m app.sim run batches/replay-default-rule-based.json`: 10 Games, all checks ok. Slowest new test: `test_the_klasseokt_reads_the_default_derived_from_the_current_settings` 1.4 s (api setup). No test failed once and passed on rerun; one run of the targeted tests hit Postgres connection errors while the lane's Postgres went into crash recovery (not test-related).

**Residual risks.** Classes locked before 10.1 have no pin and froze `placeholder-0`, so their default Replays read the derived template and count as uncalibrated. Own-scenario copy (`hiddenLine`) needs work in 10.2.

## Verification

**Commands:**
- `uv run pytest tests/engine/test_scenario.py tests/analysis/test_play_guard.py tests/sessions/test_replay_scenario.py tests/sessions/test_lock.py tests/test_sim.py -q` -- pass
- `npm run typecheck && npx vitest run src/modules/sessions` -- pass
- full gate per runbook before commit
