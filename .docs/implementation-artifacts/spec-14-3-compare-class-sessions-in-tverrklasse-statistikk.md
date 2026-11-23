---
title: 'Story 14.3: Compare Class sessions in Tverrklasse-statistikk'
type: 'feature'
created: '2026-11-23'
status: 'done'
baseline_revision: '4c067689d78d8d127c8cbff2735d75f993195f73'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-14-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-15-3-student-data-deleted-automatically-when-retention-ends.md'
warnings: ['oversized']
deferred:
  - summary: >-
      The aggregate is refreshed only when it is missing or an AI assessment changed after it; a Class game finished or a rating given after the Test deadline does not rewrite it.
    evidence: |-
      due_sessions compares written_at with assessment.latest_updates only (blind 1, edge 4). Play and Debrief deadlines come before the Test deadline, so this needs a late make-up game or a late rating; needs a founder rule for what counts as the session's final state.
    location: >-
      backend/app/modules/reports/aggregates.py due_sessions
    severity: medium
  - summary: >-
      The due finder reads every course Class session past its Test deadline until retention, each sweep.
    evidence: |-
      aggregate_candidates is not narrowed to sessions without a current aggregate, and a job that always fails is deferred again each minute with no back-off (blind 17, edge 13 and 14). Pilot scale is tens of sessions; move the missing-or-stale test into SQL and add a back-off when it grows.
    location: >-
      backend/app/modules/sessions/repo.py aggregate_candidates; backend/app/modules/reports/aggregates.py due_sessions
    severity: medium
  - summary: >-
      Migration 0401 revises 0072; Epic 15's open work in the main folder has an uncommitted 0073 that also revises 0072.
    evidence: |-
      Seen by two reviewers in the main checkout (not on this branch). At merge the orchestrator relinks 0401 after the last Epic 15 revision and updates tests/test_migrations.py HEAD.
    location: >-
      backend/migrations/versions/0401_class_aggregates.py
    severity: medium
  - summary: >-
      Comparability keys are stored but only partly asserted (model config, Effort level, prompt versions, Item weights, Scoring guide version, snapshot over row).
    evidence: |-
      Nothing in 14.3 reads them; Story 14.4's filters and labels will (verification 5).
    location: >-
      backend/app/modules/sessions/service.py comparability_source; backend/app/modules/tests/service.py comparability_keys
    severity: low
---

<intent-contract>

## Intent

**Problem:** A Lecturer cannot compare a Class session with earlier ones, and once retention (Story 15.3) deletes Student data the Class report measures are gone; 15.3's aggregate gate has no writer and logs `retention_without_aggregate_writer`; the Kostnadsfordeling has no «Fjoråret» mark (FR-65, AD-14, UX-DR51).

**Approach:** `reports.write_aggregate(class_session_id)` stores one anonymised aggregate per Class session (a header with `written_at`, comparability keys and group sizes, plus one scalar row per measure, withheld below 10 Students), from the same assemblers as the Klasserapport (14.1, 14.2). A sweep due action defers it on `reports-bulk` after the latest effective Test deadline when no attempt is open and the aggregate is missing or older than the latest AI assessment; retention's gate registers it. `GET /api/class-statistics` and the page Tverrklasse-statistikk read only those rows; the previous Class session's aggregate draws «Fjoråret» on the Oversikt and the Klasserapport.

## Boundaries & Constraints

**Always:**
- Migration `0401_class_aggregates.py` (Revises 0072), tables owned by `modules/reports`: `class_aggregates` (PK `class_session_id` → `class_sessions` ON DELETE CASCADE; `written_at`, `students`, `game_students`, `games_finished`, `keys` JSONB) and `class_aggregate_measures` (PK `class_session_id`+`measure` → header CASCADE; `group_size` int ≥ 0, `value` numeric NULL, `withheld` bool; check `NOT withheld OR value IS NULL`). No `user_id`, `seat_id`, Game id, name or free text. Personal-data registry: both `none`.
- Measures (codes, `reports/aggregates.py` `MIN_GROUP = 10`): game group G = distinct Students who held a Seat in the finished Class games — `chain.{median,lower_quartile,upper_quartile,holding,backorder}`, `cost.<role>.{median,holding,backorder}`, `amplification.<role>.median`, `pattern.<id>.{occurrences,games}`, `ai.{seats_percent,llm_percent,guard_percent}`; registered group R — `funnel.<stage>`, `learning.submitted_percent`; per question its Students — `question.<id>.percent` (computed items only); `starting.<item>.{start_percent,test_percent}` over Students who did both; Core-only — `core.{median,lower_quartile,upper_quartile}` over ready assessments (never the total, never a letter); `rating.<mode>.{median,count}` over that mode's ratings. A group under 10 stores the row with `withheld = true`, value NULL. A measure with no value (no game, AI off) has no row.
- Keys: Game settings without `demand_seed`, AI mode, model config id, prompt versions, Effort level (from the lock's snapshot, else the row), question set version, Item weights (`Selection.as_json` minus version), Scoring guide id and version.
- `write_aggregate` replaces the session's rows in one transaction; skips a Control test session (AD-13, AD-27) and a session marked `data_deleted_at`. `reports.service.write_aggregate` re-exports it. Retention's writer (`identity.register_session_aggregate_writer`) writes only when no aggregate exists yet, so an interrupted retention never rewrites over half-erased data.
- Due action `reports.write_aggregate` (sweep, last): course sessions with a Test deadline, latest effective deadline (Story 13.9's value, extensions included) ≤ now, deletion date not come, no attempt with `closed_at IS NULL` and no Student whose own deadline is ahead, aggregate missing or `written_at` < latest `ai_assessments.updated_at`, no live job (`jobs.live_locks`). Act defers `reports.write_aggregate` on `reports-bulk`, lock `class-aggregate:<id>`, ids only. Host clock on both sides.
- Page list: Class sessions of every Class where the caller is owner (`class_report.read`, via `classes`/`authz.classes_visible_to`), archived included, Control test excluded, by Class name then number; sessions without an aggregate listed «Ikke klar for sammenligning ennå.»; fewer than two sessions → «Du har ingen tidligere Klasseøkter å sammenligne med.»
- Page charts (one per measure, «Samme mål, samme regnestykke.», bars per ready session, «Vis som tabell»): `chain.median`, `cost.<role>.median` (Fabrikk first), `amplification.<role>.median`, `ai.seats_percent`, `learning.submitted_percent`, `core.median`. Withheld: «For få studenter (under 10).»; missing: «Ikke målt.».
- «Fjoråret»: previous Class session of the same Class (highest lower number); its `chain.median` when stored and not withheld → `previous_median` on `ClassCostOut` (Oversikt) and `ReportCostOut` (Klasserapport) via a reader `reports` registers with `sessions`; dashed mark in `CostDistribution`, summary «Median 1 954. Midterste halvdel 1 500–2 600. Fjoråret 2 740.».
- Copy in `nb.ts`, new strings marked `[ASSUMPTION] Story 14.3`.

**Never:** no filters, comparability labels or rating comparison (Story 14.4); no cross-Institution view (14.7); no figure computed in the web app; no aggregate while any attempt can still bring answers; no rewrite after `data_deleted_at`; no name or e-mail in logs or job args.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Group ≥ 10 | 12 Students in finished games | measures stored with values | — |
| Group < 10 | 2 Students | rows `withheld`, value NULL | — |
| Test open | deadline ahead / nobody opened / early submits | not due | — |
| Open attempt after deadline | extension or open attempt | not due | — |
| AI off | deadline passed | written once, then not due | — |
| New assessment | `updated_at` > `written_at` | due again, rows replaced | — |
| Retention | no aggregate | written, then data deleted; page same figures | writer raises → `aggregate_failed` |
| Retention rerun | aggregate exists | not rewritten | — |
| Control test / deleted | — | no aggregate written | — |
| Page, one session | — | empty-state line | — |
| Other Lecturer's Class | — | never listed | — |
| Previous aggregate withheld/missing | — | no «Fjoråret» mark or text | — |

</intent-contract>

## Code Map

- `backend/app/modules/reports/class_report.py` -- `class_report`; split out `report_parts(class_session_id)` (cost, amplification, patterns, ai, ratings, funnel) for the aggregate.
- `backend/app/modules/reports/class_report_learning.py` -- split out `learning_of(class_session_id, now)`.
- `backend/app/modules/reports/models.py` -- new tables; `backend/migrations/versions/0401_class_aggregates.py`; `tests/test_migrations.py` HEAD/tables/walk.
- `backend/app/modules/reports/aggregates.py` (new) -- measures, `write_aggregate`, `ensure_aggregate`, due finder/act, task, previous median reader; `reports/service.py` re-export; `platform/jobs/__init__.py` TASK_MODULES; `ops/sweep.py` due action.
- `backend/app/modules/reports/cross_class.py` + schemas + route in `class_report_routes.py` (`getClassStatistics`).
- `backend/app/modules/games/class_figures.py` + `games/service.py` -- `student_count(s, game_ids)`.
- `backend/app/modules/sessions/{service,repo}.py` -- aggregate candidates, previous session, comparability source, owner sessions list, previous-cost reader hook; `sessions/overview.py` `_cost_out`, `sessions/schemas.py` `ClassCostOut.previous_median`.
- `backend/app/modules/tests/service.py` -- sessions with open attempts, comparability keys; `assessment/service.py` -- latest update per session.
- `backend/app/modules/identity/personal_data.py` -- registry entries.
- Frontend: `src/app/(app)/tverrklasse-statistikk/page.tsx`, `src/modules/reports/{cross-class-api.ts,cross-class.ts,cross-class.test.ts,cross-class-page.tsx}`, `src/modules/identity/homes.ts`, `src/components/charts/cost-distribution.tsx`, `src/modules/games/{overview.ts,overview-rail.tsx}`, `src/modules/reports/{class-report.ts,class-report-page.tsx,class-report-parts.tsx}`, `src/copy/nb.ts`, regenerated `src/lib/api/*`; e2e `cross-class.spec.ts`.

## Tasks & Acceptance

**Execution:**
- Migration, models, registry, migration test.
- `aggregates.py` + helpers in games/sessions/tests/assessment; sweep, task module, retention writer.
- `cross_class.py`, schemas, route; `previous_median` on Oversikt and Klasserapport.
- `backend/tests/reports/test_aggregates.py` -- every matrix row, the live-delete test, the real `ops.retention` test, the schema-has-no-identifier test.
- Frontend page, link from the Klasserapport, Fjoråret mark and summary, Vitest helpers, e2e at 320/1440 px with axe.

**Acceptance Criteria:**
- Given two Class sessions with aggregates, when the Lecturer opens Tverrklasse-statistikk, then each measure is a chart with one bar per session and «Vis som tabell», and the same figures show after the live rows are deleted.
- Given a previous Class session's aggregate with `chain.median` 2740, when the Oversikt or the Klasserapport shows the Kostnadsfordeling, then a dashed «Fjoråret 2 740» mark and the summary sentence appear.
- Given `ops.retention` for a due session, when it runs, then the aggregate is written first and `retention_without_aggregate_writer` is not logged.

## Design Notes

Scalar rows (not a JSON blob) keep withholding per measure explicit and let 14.4 filter and label in SQL. The game group is counted from the occupancy rows' `user_id` so a game played mostly by AI players with few Students is withheld. Retention's writer is "ensure", not "rewrite": 15.3's reruns erase Students one at a time, and a rewrite mid-run would store a smaller group.

## Verification

**Commands:**
- `cd backend && uv run pytest tests/reports tests/ops/test_retention.py tests/identity tests/test_migrations.py -q -n 8` -- expected: pass
- `cd backend && uv run pytest -q -n 8 --maxprocesses=8` -- expected: pass
- `cd frontend && npm run typecheck && npx vitest run && npm run lint:colours && npm run check:copy && npm run build` -- expected: pass
- `cd frontend && npx playwright test cross-class class-report overview homes --workers=4` -- expected: pass

## Auto Run Result

Status: done
Blocking condition: none

**Summary.** `reports.write_aggregate` stores one anonymised aggregate per Class session (migration 0401: `class_aggregates` header with `written_at`, group sizes and comparability keys; `class_aggregate_measures`, one scalar per measure code, withheld with no value under 10 Students), from the Klasserapport's own assemblers (`report_parts`, `learning_of`), Core-only scores only. The sweep's last due action `reports.write_aggregate` defers the job on `reports-bulk` (lock `class-aggregate:<id>`) once the latest effective Test deadline has passed, no attempt is open and the aggregate is missing or older than the latest AI assessment; a job writes nothing from the deletion date on. Retention (15.3) now runs `ensure_aggregate` through `identity.register_session_aggregate_writer`, so `retention_without_aggregate_writer` no longer fires; an existing aggregate is kept. `GET /api/class-statistics` and `/tverrklasse-statistikk` compare the Lecturer's own Class sessions (archived included, Control tests never) from the aggregates only: 12 measures as bars with «Vis som tabell», withheld and unmeasured cells in words, Class sessions without an aggregate listed as not ready, «Du har ingen tidligere Klasseøkter å sammenligne med.» for one. The Oversikt and Klasserapport Kostnadsfordeling draw the dashed «Fjoråret» mark and summary from the previous Class session's stored median.

**Files.**
- `backend/migrations/versions/0401_class_aggregates.py`, `reports/models.py`, `tests/test_migrations.py` — tables, walk.
- `backend/app/modules/reports/aggregates.py` (new) — measures, writer, gate, finder, job, «Fjoråret» reader; `reports/service.py` re-export; `platform/jobs` task module; `ops/sweep.py` due action; `ops/retention.py` comment.
- `reports/cross_class.py`, `cross_class_schemas.py` (new), `class_report_routes.py` — `getClassStatistics`.
- `reports/class_report.py`, `class_report_learning.py`, `class_report_schemas.py` — parts split out, `previous_median`.
- `games/class_figures.py`, `games/service.py` — `student_count`, `rating_students`; `sessions/{service,repo,overview,schemas}.py` — candidates, previous session, keys, owned sessions, previous-cost hook; `tests/service.py`, `assessment/service.py` — open attempts, comparability keys, latest assessment.
- `identity/personal_data.py` — both tables `none`.
- `backend/tests/reports/test_aggregates.py` (new), `tests/test_imports.py`, `tests/ops/test_verify_restore.py` (revision prefix).
- Frontend: `app/(app)/tverrklasse-statistikk/page.tsx`, `modules/reports/cross-class{,-api,-page}.ts(x)` + Vitest, `components/charts/cost-distribution.tsx`, Oversikt and Klasserapport wiring, `identity/homes.ts`, `sessions/class-sessions.tsx` link, `copy/nb.ts` ([ASSUMPTION] Story 14.3), regenerated `lib/api/*`, `e2e/cross-class.spec.ts`.

**Review.** Four layers (blind, edge case, verification gap, intent; sonnet). Patched 7 medium (job guard under the row lock; rating group by Students; four test gaps; Assistant case) and 6 low. Deferred 4 (refresh after late games or ratings; finder scale and back-off; 0073/0401 head at merge; keys asserted with 14.4). Rejected with reasons in the triage log.

**Follow-up review recommended: true** — the medium patch in `write_aggregate` (row-locked re-check of `data_deleted_at` and the deletion date, with the `for_retention` path) changes when a write may happen and has been read by no reviewer.

**Verification.** Backend full suite (`-n 8`, lane-3 DB): 4267 passed, 1 skipped; two failures fixed or explained (`test_verify_restore` expected a revision starting `00`, fixed; `tests/ai/test_effort.py` failed once on leftover state of a killed run in the shared `ai_db` and passes alone), one error from my `-p no:logging` flag (`caplog`), passes without it; ruff clean. `tests/reports/test_aggregates.py`: 20 passed; tests that play a short game take 2–3.5 s each (as the Klasserapport tests do). Frontend: typecheck, Vitest 1379 passed, `lint:colours`, `check:copy`, `next build`. Playwright on the rebuilt lane-3 stack: `cross-class`, `class-report`, `overview`, `homes`, `order-field` — 52 passed, axe at 320 and 1440 px and 200 % text.

**Decisions taken in the founder's place.** Game measures' group is the Students who held a Seat in the finished Class games; ratings' group is the Students who rated; header counts are stored exactly even when every measure is withheld; retention keeps an existing aggregate rather than rewriting it; from the deletion date only retention writes; «Fjoråret» is the immediately previous Class session of the same Class whatever its settings; the page shows 12 measures (store holds about 40 for 14.4); charts need two Class sessions with aggregates; draft copy.

**New personal-data tables.** None: `class_aggregates` and `class_aggregate_measures` hold no `user_id` or user text (registry `none`).

**Residual risks.** The deferred items.
