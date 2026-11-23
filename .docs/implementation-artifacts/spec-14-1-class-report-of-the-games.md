---
title: 'Story 14.1: Class report of the games'
type: 'feature'
created: '2026-11-23'
status: 'done'
baseline_revision: 'd486bf428604a8b72b49f3b133d765501688dc52'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-14-context.md'
warnings: ['oversized']
deferred:
  - summary: >-
      Finished Class games without stored facts sets are never backfilled, and a failed facts job is not retried.
    evidence: |-
      Only the finish hook defers reports.store_class_facts; games finished before the deploy, or whose job failed, stay out of Forsterkning and Mønstre ("Fra N av M ferdige spill") until something builds their sets. Fix: a sweep or admin action that defers the job for finished Class games lacking fact_sets, and a bounded retry.
    location: >-
      backend/app/modules/reports/class_report_jobs.py
    severity: medium
  - summary: >-
      Plausibility ratings have no minimum group size, so an AI mode with one answer shows that answer's value (no name, no user_id).
    evidence: |-
      FR-70 and the AC ask for counts and the median per AI mode with no individual rating shown; with count 1 the value is visible though anonymous. A minimum n is a founder decision.
    location: >-
      backend/app/modules/reports/class_report.py _ratings_out
    severity: low
  - summary: >-
      The report's scope is a local stand-in for Epic 13's reports.scope.reporting_games(purposes={class}); the finish hook repeats the rule.
    evidence: |-
      reports.scope exists only on epic-13. At merge, _class_games and the hook's purpose/kind check should call scope.reporting_games / is_reporting_session so one predicate holds the rule (AD-13).
    location: >-
      backend/app/modules/reports/class_report.py _class_games; class_report_jobs.py _defer_on_finish
    severity: low
---

<intent-contract>

## Intent

**Problem:** A Lecturer has no page that sums up how the Class games of a Class session went, so the plenary is planned from the Oversikt's live wall alone (FR-64, FR-68, FR-70, FR-79).

**Approach:** A Lecturer-only «Klasserapport» page at `/klasseokter/{id}/klasserapport`, fed by one api read `GET /api/class-sessions/{id}/class-report` that computes every figure from `game_summaries`, the Decision log, `seat_occupancy`, stored `fact_sets` and `believability_ratings` over the finished Class games. Fact sets of a finished Class game are stored by a job its finish defers, so the read never builds facts or replays a Game. The page refetches on the existing `session:<id>` topic.

## Boundaries & Constraints

**Always:**
- Scope: the Class games (`purpose=class`) of the Class session; none for a Control test Class session (`sessions.kind_of`). Game figures use the finished ones (`game_summaries.status=finished`); the funnel is the Oversikt's (`progress.funnel` over the Class's registered Students). Plausibility ratings use the finished Class games and Replays of the session (FR-70 asks after both), counts per value and the median per AI mode, never a `user_id` or a single rating.
- Content: status line («Ingen spill er ferdige ennå.» / «Oppdateres etter hvert som studentene blir ferdige. 41 av 60 spill er med.» / all done: «Alle 60 spill er med.»); Trakt; Kjedekost (Kostnadsfordeling over the chain cost); Kostnad per Rolle (a Kostnadsfordeling per Role on one shared axis, Fabrikk at the top, with mean Lager and Restordre printed); Forsterkning per Rolle (same chart form, median and quartiles); «Mønstre» (Student-decided occurrences per pattern and the number of games with one, most common first, names from the latest `detected_patterns` content); KI-spillere (Seats with an AI player in some Week, of them whole-game; Share of LLM Orders per game; fallback Orders per game; every `guard_switch`/`cost_limit` occupancy as game, Role, Week and its AD-15 mark text; share of Seats ever held by an LLM player that the Play guard switched); Troverdighet per AI mode.
- Every number, median, quartile, share and percent comes from the api (AD-10); the web app only formats with `formatNumber`. Each chart has «Vis som tabell» under it; per-Role tables go Detaljist→Fabrikk, Role-ordered charts and lists Fabrikk first; per-game tables in game-number order.
- Access: policy `class_report.read` = account role Lecturer and Class staff role owner. Assistant lecturers, Lecturers of other Classes, Admins without a staff role, Students and unknown/malformed ids all get the same 403 `forbidden` → the permission-denied page. `Cache-Control: no-store`.
- A fixed number of queries whatever the number of games (NFR-3, AD-25); the read writes nothing.
- Fact sets: finish hook `reports.class_facts` defers task `reports.store_class_facts(game_id)` (queue `llm-batch`, queueing lock per game) for Class games only; it stores the four Seats' sets through `games.service.fact_set` and emits `session:<id>` (registry entry `reports.store_class_facts: {session}`). The report states how many finished games its Forsterkning and Mønstre cover when fewer than all.
- Merge with Epic 13: `backend/app/modules/reports/__init__.py` is byte-identical to `origin/epic-13`'s; every other new file has a `class_report*` name. The scope read is a local stand-in documented to be replaced by `reports.scope.reporting_games(purposes={class})` at merge.
- Copy in `nb.ts` under a new top-level `classReport`; drafted strings marked `[ASSUMPTION]`.

**Never:** no learning results (14.2), no aggregates or «Fjoråret» (14.3), no Student names, user ids or individual ratings in the response; no medians or costs computed in the web app; no new event topic; no change to the demo Class; no migration (no new table).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| None finished | Class games running | `finished=0`, `games=N`; page shows «Ingen spill er ferdige ennå.» and the Trakt; no game sections | — |
| Partial | 1 of 2 finished | figures over the 1; «… 1 av 2 spill er med.» | — |
| Facts pending | finished game without stored fact sets | cost and AI figures include it; `facts_games` < `finished` and the page says so | — |
| Test games | finished `lecturer_test`/`simulation` Game in the session | counted nowhere | — |
| Control test | Control test Class session | owner reads an empty report (0 games) | — |
| Ratings | ratings on a Class game and a Replay | counts per value and median per `ai_mode`; no `user_id` | — |
| Assistant / other Lecturer / Admin / Student / bad id | GET | — | 403 `forbidden`, same body |
| 100 games | 100 Class games with summaries | same query count as 2 games | — |
| Live | a Game finishes or a step is recorded | `session:<id>` → page refetches | — |

</intent-contract>

## Code Map

- `backend/app/modules/sessions/overview.py:102` `class_overview` -- pattern for reading `game_summaries`, `cost_parts`, `progress.funnel`, `_cost_out` (reuse `analysis.class_cost`); add `class_report: bool` to the Oversikt (`authz.can(user, "class_report.read", found)`), field in `sessions/schemas.py` `ClassOverviewOut` (~1263).
- `backend/app/analysis/class_cost.py`, `analysis/wall.py` `quartiles` -- median/quartiles (inclusive) for every distribution.
- `backend/app/modules/games/models.py` -- `game_summaries` (433), `seat_weeks` (317: `decided_by`, `fallback`, `occupant_kind`), `seat_occupancy` (196: `from_week`, `reason`, `occupant_kind`), `fact_sets` (416: `payload.facts.chain.by_role[].amplification`, `payload.facts.seat.patterns[].{pattern,decided_by}`), `believability_ratings` (470).
- `backend/app/modules/games/marks.py` `seat_mark` -- the AD-15 mapping for switch marks; `games/service.py:871` `fact_set` (get_or_create), `:1027` `on_game_finished`, `:1191` `cost_parts`.
- `backend/app/modules/sessions/service.py:948` `staffed_session(user, id, action)` (access + crumbs), `:851` `kind_of`, `:972` `class_id_of`; `classes.service.registered_students`; `progress.service.funnel`; `content.service.detected_patterns(None)`.
- `backend/app/modules/debrief/narration.py:97` -- finish-hook + `jobs.defer` pattern; `replay/jobs.py` task pattern; `platform/jobs/__init__.py` `TASK_MODULES`; `platform/events/registry.py`; `platform/authz.py` POLICIES / CLASS_STAFF_ROLES; `backend/app/main.py` router includes.
- `backend/app/modules/messaging/message_routes.py:242` -- route pattern (`authz.require`, `_id`, `Forbidden`).
- Tests: `backend/tests/sessions/test_overview.py` (`short_game`, `play_weeks`, `klass`, query-count test with straight inserts), `backend/tests/games/helpers.py`.
- Frontend: `frontend/src/modules/games/overview-rail.tsx` (Trakt, Kostnadsfordeling use, Lager/Restordre bars), `overview.ts` `funnelRows`; `components/charts/cost-distribution.tsx` (add optional shared `highest`); `modules/messaging/sent-messages-page.tsx` (page/guard/403 pattern); `lib/api/topics.ts` (`session` keys); `modules/identity/homes.ts` (paths); `modules/games/overview-page.tsx:194` header links; `modules/sessions/class-sessions.tsx:76` Klasse list.
- e2e: `frontend/e2e/support/{classes,live-game,auth}.ts`, `playout.spec.ts` (live Class game + dev playout).

## Tasks & Acceptance

**Execution:**
- `backend/app/modules/reports/__init__.py` -- copy of `origin/epic-13`'s file.
- `backend/app/modules/games/class_figures.py` (new) + re-exports in `games/service.py` -- one query each over a list of game ids: finished Class games of a session from `game_summaries` (+ count of all), amplification per game/Role and Student pattern counts per game from `fact_sets` (JSON in SQL), Seats with facts per game, LLM/fallback/ordered counts per game, AI-held Seats, switch occupancies, LLM-held Seats, rating counts per AI mode/value, finished Replays of the session.
- `backend/app/modules/reports/class_report.py` (new) -- scope stand-in, assembler `class_report(user, session_id)` → schema or None; pure helpers for distributions/median of ratings.
- `backend/app/modules/reports/class_report_schemas.py`, `class_report_routes.py` (new) -- `GET /api/class-sessions/{session_id}/class-report` (`getClassReport`), 401/403.
- `backend/app/modules/reports/class_report_jobs.py` (new) -- finish hook + task; `platform/jobs/__init__.py` TASK_MODULES; `main.py` import + router; `events/registry.py`; `authz.py`.
- `backend/app/modules/sessions/{schemas,overview}.py` -- `class_report` flag.
- `backend/tests/reports/test_class_report.py` (new) -- matrix rows, query count, job emits `session`, registry.
- `frontend/src/modules/reports/class-report-api.ts`, `class-report.ts` (+ `class-report.test.ts`), `class-report-page.tsx` (new); `app/(app)/klasseokter/[sessionId]/klasserapport/page.tsx` (new); `homes.ts` `classReportPath`; `topics.ts`; `nb.ts` `classReport`; overview header link (when `class_report`); Klasse list link for owners; `cost-distribution.tsx` `highest`; regenerate `lib/api/{openapi.json,schema.ts}` with `npm run api:generate`.
- `frontend/e2e/class-report.spec.ts` (new) -- live finished game shows in the report and the status line; stubbed rich report at 320/1440/200 % with axe and reflow; table toggles; Assistant gets the permission-denied page.

**Acceptance Criteria:**
- Given a Lecturer owner on the Oversikt or the Klasse page, when they follow «Klasserapport», then the page shows the sections above with every number from the api and «Vis som tabell» under each chart.
- Given a Class game finishes while the report is open, when `session:<id>` arrives, then the page refetches and the counts move without reload.
- Given the page at 320 px, 1440 px and 200 % text, when Playwright and axe run, then there is no horizontal page scroll and no axe violation.

## Spec Change Log

## Review Triage Log

### 2026-11-23 — Review pass
- verdicts: 24 findings — high 0, medium 2, low 9, false 13, maybe-false 0
- findings:
  - `[low]` `[patch]` Finish hook defers the facts job for Control test Class games — the hook now skips `sessions.kind_of == control_test`.
  - `[low]` `[defer]` Scope stand-in duplicates the rule of Epic 13's reports.scope — relink at merge (deferred).
  - `[low]` `[patch]` Oversikt shows «Klasserapport» for a Control test session — the `class_report` flag is now false for a Control test Class.
  - `[medium]` `[defer]` No backfill of facts sets for games finished before deploy — needs a sweep or admin action (deferred).
  - `[medium]` `[defer]` A failed facts job is never retried — grouped with the backfill (deferred).
  - `[low]` `[reject]` Missing cost_parts counted as zero per Role — a finished game with a chain cost always has Week states and so parts; same rule as the Oversikt's `class_cost`.
  - `[low]` `[patch]` `type: ignore` and index pairing in `_cost_out` — typed (game, cost) pairs zipped with the quantized values.
  - `[false]` `[reject]` Cost None while games finished — a finished game always has `chain_cost` in its summary row.
  - `[false]` `[reject]` Module-boundary docstring vs schema imports — type imports of other modules' schemas are the codebase's practice; behaviour reads go through service.py.
  - `[false]` `[reject]` Coverage `>=` / mixed analysis versions — fact_sets is unique per (game, seat) and never rebuilt; the chain part is identical in every set of a Game.
  - `[false]` `[reject]` Decimal from a JSON float — facts are stored with `model_dump(mode="json")`, which writes Decimals as strings.
  - `[false]` `[reject]` Query-count test misses the other reads — they run with non-empty ids in both measurements, so their statements are counted.
  - `[low]` `[defer]` Ratings with count 1 reveal that answer's value — minimum n is a founder decision (deferred).
  - `[low]` `[patch]` «Fra 0 av N …» doubled with «Ingen spill er analysert ennå.» — the covered line is hidden when none is analysed.
  - `[low]` `[reject]` Copy and a11y nits (aria-pressed, tick comma, «Alle 1 spill») — a toggle whose label changes takes no aria-pressed; the rest is correct bokmål.
  - `[low]` `[patch]` Unused `log` and seat_mark before the reason filter in `_ai_out` — removed and reordered.
  - `[false]` `[reject]` ai_seats numerator vs seats denominator — every Seat of a finished game has Decision log rows.
  - `[low]` `[reject]` (edge) One failing Role stops the other Roles' facts — get_or_create fails at game level (not finished, facts unavailable); the job fails whole and is logged.
  - `[low]` `[defer]` (edge) Ratings with count 1 — same as the blind row above.
  - `[false]` `[reject]` (edge) patterns null in a payload — `SeatFacts.patterns` is a tuple, always an array in JSON.
  - `[false]` `[reject]` (edge) by_role missing in an older analysis version — versions 1 and 2 both store `chain.by_role` with role and amplification.
  - `[false]` `[reject]` (edge) missing cost_parts — as the blind row above.
  - `[false]` `[reject]` (edge) Oversikt link for a Control test — duplicate of the patched blind row.
  - `[false]` `[reject]` (edge) ratings include Replays — by design (FR-70 asks after the Replay; spec Always); a rating is stored only for a finished Game.

## Design Notes

Decisions the founder would otherwise take (all `[ASSUMPTION]`, listed in the report):
- Mønstre counts Student-decided occurrences only (AI Weeks' occurrences describe AI players, not the class); Guided Weeks are already out by the facts rules.
- «Seats played by AI players» = Seats of finished Class games with ≥1 Decision log Week held by a non-Student occupant; «hele spillet» = no Student Week at all.
- Ratings include finished Replays of the session (FR-70 asks after the Replay and names the Class report).
- Fact sets are stored by a job at finish, not at read: the read stays a fixed number of queries and never runs the simulation part of the facts.

## Verification

**Commands:**
- `uv run pytest tests/reports -q` (lane env) -- pass
- `npm run typecheck && npx vitest run src/modules/reports && npm run lint:colours && npm run check:copy` -- pass
- `npx playwright test e2e/class-report.spec.ts --workers=4` (lane stack) -- pass

## Auto Run Result

Status: done

Summary: the Lecturer-only Klasserapport (`GET /api/class-sessions/{id}/class-report`, page `/klasseokter/{id}/klasserapport`) with Trakt, Kjedekost, Kostnad per Rolle (Lager/Restordre), Forsterkning per Rolle, «Mønstre», KI-spillere (AI Seats, Share of LLM Orders per game, fallback, cost-limit and Play-guard switches through AD-15, guard share) and Troverdighet per AI mode; every figure computed in the api in a fixed number of queries; facts sets stored by a finish-hook job (`reports.store_class_facts`, emits `session:<id>`); links from the Oversikt header and the Klasse's session list for owners.

Files: `backend/app/modules/games/class_figures.py` (reads) and `games/service.py` (re-exports); `modules/reports/{__init__ (byte-identical to epic-13), class_report, class_report_schemas, class_report_routes, class_report_jobs}.py`; `sessions/{overview,schemas}.py` (`class_report` flag); `platform/{authz,events/registry,jobs/__init__}.py`; `main.py`; `backend/tests/reports/test_class_report.py`; frontend `modules/reports/class-report-api.ts`, `class-report.ts` (+ test), `class-report-page.tsx`, route page, `nb.ts` `classReport`, `topics.ts`, `homes.ts`, Oversikt header, Klasse page and `class-sessions.tsx`, `cost-distribution.tsx` (`highest`), regenerated `openapi.json`/`schema.ts`; `e2e/class-report.spec.ts`.

Review: two layers (blind, edge case; verification-gap and intent-alignment skipped by the orchestrator's brief). 24 findings: 6 patched (all low), 4 deferred rows (backfill and retry medium, ratings minimum n, scope relink), 14 rejected with reasons above. followup_review_recommended: false (no high or medium patched).

Verification: backend full suite 3893 passed before the patches, touched tests 24 passed after; frontend typecheck, Vitest 1228 passed, lint:colours, check:copy, build passed; Playwright class-report, overview, homes, order-field, classes 49 passed after the patches, axe on the report at 320 px, 1280 px with 200 % text and 1440 px.

Residual risks: games finished before deploy have no facts sets (deferred backfill); the scope stand-in must be relinked to reports.scope at the Epic 13 merge; `main.py`, `jobs/__init__.py`, `authz.py`, `topics.ts`, `nb.ts` touch lines near Epic 13's changes (small mechanical conflicts possible).

## Close-out of Epic 14 (2026-11-23)

The deferred backfill and retry are done: the sweep's `reports.class_facts` (`class_report_jobs.due_games`) defers the facts job again for a finished Class game of a reporting, undeleted Class session whose Seats lack facts sets ten minutes after it finished (games from before the job existed included), unless a job is alive or three failed in the last 24 hours (`jobs.failed_counts`, by procrastinate's `failed` events). The scope relink was done at the Epic 13 merge. Still open as a founder decision: plausibility ratings have no minimum group size in the live report.
