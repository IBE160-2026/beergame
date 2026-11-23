---
title: 'Story 14.7: The Admin compares across Institutions (cut list)'
type: 'feature'
created: '2026-11-23'
status: 'done'
baseline_revision: 'a5c9fc191d8f6fcfed3fbdeca06ebf9ccc37fb80'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-14-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-14-3-compare-class-sessions-in-tverrklasse-statistikk.md'
  - '{project-root}/.docs/implementation-artifacts/spec-14-4-filter-comparisons-and-label-class-sessions-that-differ.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** The Admin cannot see how the exercise works at different Institutions; FR-65's cross-Institution view (cut list, `FEATURE_CROSS_INSTITUTION_STATS`) does not exist, and the stored aggregates (14.3) do not record which Institution they belong to.

**Approach:** Store the Institution in each aggregate header (migration 0402, backfilled). Behind the flag, `GET /api/institution-statistics` (Admin only) reads only `class_aggregates`/`class_aggregate_measures` (plus Institution names), applies 14.4's filters and difference labels over the stored keys, and combines each Institution's compared Class sessions per measure. The Admin-område gets «Tverrinstitusjonell statistikk» with the same bars, tables and filters as Tverrklasse-statistikk, Institutions instead of Class sessions.

## Boundaries & Constraints

**Always:**
- Migration `0402_aggregate_institution.py` (Revises 0401): `class_aggregates.institution_id` Uuid NOT NULL, FK `institutions.id` ON DELETE RESTRICT, indexed; backfilled from `class_sessions`→`classes` before NOT NULL. `write_aggregate` stores the Class's Institution at writing (via `classes.class_facts`). Registry entry stays `none` (an Institution id is no personal data).
- Flag off: the route answers FastAPI's plain 404 before any policy or read (as 14.8's `_game_data_export_exists`); `UserOut.cross_institution_stats` is false, so the Admin-område has no link and the page renders the not-found page. `/api/class-statistics` and its page are untouched (14.3/14.4 unchanged).
- New action `institution_statistics.read`: account role Admin only. Lecturer, Assistant lecturer, Student → 403 `forbidden`; not logged in → 401.
- `UserOut.cross_institution_stats: bool` = flag on and the User holds the Admin account role.
- Reads: all aggregate headers (keys, institution_id) and the `SHOWN` measures of 14.3 — two reads whatever the number of sessions — plus Institution names (`identity.institution_labels`) and model names (`sessions.model_names`). Never `class_sessions`, `classes`, games, tests or any Student table.
- Filters and labels: the same five query params (≤ 64 chars) and pure `cross_class.compare` over every aggregate (all Institutions); options, faceted counts, `all_count` as 14.4. An Institution's `differs` = union (in `DiffKey` order) of its compared sessions' `differs`; `comparable` on `core.median` = `compare`'s score comparability.
- Institutions listed: those with ≥ 1 compared session, Norwegian name order (`nb_sort_key`), each with `sessions` (compared count). An Institution with exactly one compared session is `withheld` unless none of that session's `SHOWN` measure rows is withheld (missing rows — not measured — do not withhold it); a withheld Institution has every cell withheld, no value, and `differs = []`.
- Cell per (measure, Institution): the median of the non-withheld stored values of its compared sessions (Decimal, `statistics.median`), with `sessions` = how many values went in; none but some withheld → withheld; no row at all → not measured. Each stored value already rests on ≥ 10 Students, so every shown figure does.
- Response holds no Class name, Class session id, Class session number, Lecturer, Student, `user_id`, e-mail or `written_at`; a test asserts the schema's field names.
- Page `/admin/tverrinstitusjonell-statistikk` (GuardedPage `adminArea`): crumbs Admin-område › title; intro «Samme mål, samme regnestykke.»; an «about» line saying each figure is the median of the Institution's Class sessions and groups under 10 are not shown; filters (reused component) when two or more sessions are ready; bars, «Vis som tabell» tables (columns Institusjon, Verdi, Klasseøkter, Ulikt oppsett), score comparability line; a withheld Institution reads «Holdt tilbake: én Klasseøkt med et mål under 10 studenter.»; none listed → «Ingen institusjoner har lagrede tall ennå.»; 403 → permission-denied page. Copy in `nb.ts` `crossInstitution`, marked `[ASSUMPTION] Story 14.7`; measure names, filter and difference words reused from `crossClass`.

**Never:** no live-table read; no Class or Lecturer name, Class session number or Student data in response or page; no audit row (no Student data is read); no change to 14.3/14.4 behaviour; no figure computed in the web app; no rating comparison.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Flag off | any User, `GET /api/institution-statistics` | 404 as an unknown route; `cross_institution_stats` false; class-statistics unchanged | — |
| Not Admin | Lecturer / Assistant / Student | — | 403 `forbidden` |
| Two Institutions | X: 2 sessions (chain 1000, 2000); Y: 2 sessions (3000, withheld) | X chain 1500 (`sessions` 2); Y chain 3000 (`sessions` 1) | — |
| Single session, all ≥ 10 | Z: 1 session, no withheld row | listed with its values | — |
| Single session, one withheld | W: 1 session, `core.median` withheld | `withheld` true, every cell withheld, `differs` [] | — |
| Filter leaves one | X filtered to 1 session with a withheld row | X withheld | — |
| Differing setup | X sessions llm, Y rule_based | Y (or both on a tie) `differs` holds `ai_mode` | — |
| No aggregate | none stored | `institutions` [], `measures` [], `filters` [] | — |
| Not measured | no row for `core.median` at X | neither value nor withheld | — |

</intent-contract>

## Code Map

- `backend/migrations/versions/0402_aggregate_institution.py` (new); `backend/tests/test_migrations.py` -- `HEAD = "0401"` (line 211) → 0402, walk downgrades through it.
- `backend/app/modules/reports/models.py` -- `class_aggregates`: add `institution_id`.
- `backend/app/modules/reports/aggregates.py:193` `write_aggregate` -- header gets `institution_id` from `classes.class_facts(s, [target.class_id])` (`classes/service.py:767`).
- `backend/app/modules/reports/cross_class.py` -- reuse `compare`, `SHOWN`, `SCORE_MEASURES`, `token`; `class_statistics` unchanged.
- `backend/app/modules/reports/cross_institution.py` (new) -- `READ = "institution_statistics.read"`, `enabled()`, pure `combine(...)`, `institution_statistics(chosen)`; `cross_institution_schemas.py` (new) -- `InstitutionOut`, `InstitutionValueOut`, `InstitutionMeasureOut`, `InstitutionStatisticsOut` (reusing `FilterOut`, `DiffKey`, `MeasureUnit`).
- `backend/app/modules/reports/class_report_routes.py:150` -- add `_cross_institution_exists` dependency and `GET /institution-statistics` (`getInstitutionStatistics`), same five params.
- `backend/app/platform/authz.py:~234` -- `"institution_statistics.read": frozenset({ADMIN})`.
- `backend/app/modules/identity/schemas.py:170` `UserOut` + `identity/service.py:99` `_user_out` -- `cross_institution_stats`.
- `backend/app/modules/identity/personal_data.py:203` -- text mentions the Institution id.
- `backend/app/platform/collation.py` `nb_sort_key`; `identity.institution_labels` (`identity/service.py:1729`).
- Tests: `backend/tests/reports/test_cross_institution.py` (new; reuse `test_cross_class_filters.keys`/`store` pattern, `tests/sessions/test_test_game.py:flag` for the flag); fix the raw inserts at `tests/reports/test_aggregates.py:469` and `tests/reports/test_cross_class_filters.py:139` to set `institution_id`.
- Frontend: `src/modules/reports/cross-class-page.tsx` -- export `Filters`, `CompareBars`; new `cross-institution{-api.ts,.ts,.test.ts,-page.tsx}`; `src/app/(app)/admin/tverrinstitusjonell-statistikk/page.tsx`; `src/modules/identity/homes.ts` path; `home-page.tsx` `AdminSections` link when `user.cross_institution_stats`; `src/copy/nb.ts`; regenerated `src/lib/api/openapi.json`/`schema.ts`; e2e `e2e/cross-institution.spec.ts` (stubbed answer at 320/1440 px with axe, real api: Admin sees the page, Lecturer gets permission-denied).

## Tasks & Acceptance

**Execution:**
- Migration, model, writer, migration test, raw-insert fixes.
- authz action, `UserOut` flag, `cross_institution.py` + schemas + route.
- `backend/tests/reports/test_cross_institution.py` -- every matrix row; schema field names hold no identifier; the writer stores the Institution; the figures come only from stored rows (tests insert aggregate rows for fresh Class sessions with no game played, and the answer is the same after the Class session's Class is renamed).
- Frontend api, helpers + Vitest, page, link, copy; regenerate the client; e2e.

**Acceptance Criteria:**
- Given the flag off, when any User calls `/api/institution-statistics`, then it answers 404 as an unknown route, the Admin-område has no link, and `/api/class-statistics` answers as before.
- Given the flag on and aggregates in two Institutions, when the Admin opens «Tverrinstitusjonell statistikk», then each measure shows one bar per Institution with «Vis som tabell», differing Institutions are labelled «Ulikt oppsett: …», and no Class name appears.
- Given a Lecturer or Assistant lecturer, when they request the view, then the api answers 403 and the page shows the permission-denied page.
- Given an Institution with a single Class session that has a withheld shown measure, when the view is shown, then it is listed as withheld with no figure.

## Spec Change Log

## Review Triage Log

### 2026-11-23 — Review pass
- verdicts: 28 findings — high 0, medium 4, low 13, false 11, maybe-false 0 (plus descriptive intent notes, rejected as by-design)
- findings:
  - `[low]` `patch` Edge 1: invitation acceptance builds `UserOut` without `cross_institution_stats` — set there too, through one helper.
  - `[low]` `patch` Edge 2: flag off after `/me` was read shows the error state — the page shows the not-found page on a 404; e2e serves a `/me` with the flag off.
  - `[low]` `patch` Edge 3: header and measures read in two statements — both now in one REPEATABLE READ snapshot.
  - `[false]` `reject` Edge 4: `class_facts` None in retention's write — the Class session row is locked and `class_sessions.class_id` is a FK to `classes`; the branch cannot be reached.
  - `[false]` `reject` Edge 5: a multi-session Institution can show one session's figure — every stored figure rests on ≥ 10 Students; the AC withholds only a single-session Institution, and that one session's figure is what the AC allows for one; recorded as a founder decision.
  - `[low]` `patch` Edge 6: withheld line differs from the spec sentence — the line per withheld Institution now reads «<name>. Holdt tilbake: én Klasseøkt med et mål under 10 studenter.» (the bar cell keeps «Holdt tilbake.» so names do not wrap letter by letter at 320 px).
  - `[medium]` `patch` Edge 7 / Verification 5: no test of the answer after a live rename — `test_the_answer_reads_only_the_stored_rows` renames the Class and compares the answers.
  - `[low]` `patch` Edge 8: 401 not tested — added to `test_only_the_admin_may_read_it`.
  - `[medium]` `patch` Verification 1 / Blind 5: 0402 backfill never ran on data — the migration walk now stores an aggregate at 0401, upgrades, checks the Institution, and removes the rows.
  - `[medium]` `patch` Verification 2: page flag-off branch untested — e2e with a `/me` saying the flag is off: not-found page, no link in the Admin-område.
  - `[medium]` `patch` Verification 3: filter wiring on this page untested — e2e presses a KI-modus option: request carries the token, `aria-pressed`, live line, one Institution drawn.
  - `[low]` `patch` Verification 4: same as Edge 6.
  - `[low]` `patch` Blind 1: docstrings said no Class session "counted" — corrected (Class sessions are counted, not named).
  - `[false]` `reject` Blind 2: same as Edge 5.
  - `[false]` `reject` Blind 3: missing measure row treated as not withheld — the spec rule: a missing row is "not measured", which does not withhold; partial writes are impossible (one transaction) and now one snapshot.
  - `[low]` `reject` Blind 4: unweighted median vs «Samme mål, samme regnestykke.» — the about line says each figure is the median of the Institution's Class sessions; founder decision recorded.
  - `[false]` `reject` Blind 6: same as Edge 4.
  - `[false]` `reject` Blind 7: blank or duplicate Institution names — the FK is RESTRICT and Institutions are never deleted; names are unique case-insensitively (`uq_institutions_name`).
  - `[low]` `patch` Blind 8: flag-off e2e/Vitest claim and stale-session 404 — covered by Edge 2 and Verification 2 patches.
  - `[low]` `patch` Blind 9: flag test undid the monkeypatch in the body — a `flag_off` fixture restores it whatever the outcome.
  - `[low]` `patch` Blind 10a: `withheldNote` singular for several names — one line per Institution (Edge 6 patch).
  - `[low]` `reject` Blind 10b-d: hard-coded 10 in copy, period in table cells, [ASSUMPTION] strings — copy convention project-wide; 10 is the fixed threshold of FR-65.
  - `[false]` `reject` Blind 11a: no audit of Admin reads — no Student data is read (AD-12's audited exceptions read Student data); recorded as a founder decision.
  - `[low]` `reject` Blind 11b: all aggregates loaded, no cache — two reads at pilot scale (tens of Class sessions).
  - `[false]` `reject` Blind 11c: RESTRICT blocks Institution deletion — no Institution delete in v1 (`identity/models.py`).
  - `[false]` `reject` Blind 11d: moved Class keeps old Institution undocumented — Design Notes state it.
  - `[false]` `reject` Intent R7: the route stays in OpenAPI while off — as Story 14.8's flag (unknown-route 404 at runtime); the generated client is built with flags on.
  - `[false]` `reject` Intent R3: live name lookups — Institution and model names are labels, not live measure data; the figures, keys and Institution id come only from the aggregate tables.
  - Intent notes (stubbed UI e2e vs real stack, `UserOut` field, 14.3 table column, exported 14.4 components, multi-session single figure): descriptive; the real-api e2e and backend api tests cover the data path; rejected as by-design.

## Design Notes

Institution in the header, not joined at read: the view must read only the aggregate table (AD-14), and the Institution a Class session belonged to when its aggregate was written is the one its figures speak for. Median of the session values (not a group-weighted mean) keeps every shown figure a statistic of stored, unwithheld figures each resting on ≥ 10 Students; nothing is derivable about a withheld session. The single-session rule is applied after filtering, so a filter cannot isolate a small session.

## Verification

**Commands:**
- `cd backend && uv run pytest tests/reports/test_cross_institution.py tests/reports/test_cross_class_filters.py tests/reports/test_aggregates.py tests/test_migrations.py tests/identity -q -n 8` -- expected: pass
- `cd backend && uv run pytest -q -n 8 --maxprocesses=8` -- expected: pass
- `cd frontend && npm run typecheck && npx vitest run && npm run lint:colours && npm run check:copy && npm run build` -- expected: pass
- `cd frontend && npx playwright test cross-institution cross-class homes order-field --workers=4` -- expected: pass

## Auto Run Result

Status: done
Blocking condition: none

**Summary.** Migration 0402 stores each aggregate's Institution (`class_aggregates.institution_id`, NOT NULL, FK RESTRICT, backfilled from the Class); `write_aggregate` stamps it at writing. Behind `FEATURE_CROSS_INSTITUTION_STATS`, `GET /api/institution-statistics` (policy `institution_statistics.read`, Admin only; 404 as an unknown route while off) reads only the two aggregate tables in one snapshot, plus Institution and model names, applies Story 14.4's five filters and `compare`, and groups the compared Class sessions by Institution: each cell the median of the sessions' stored unwithheld values with how many went in; an Institution with one compared session and any withheld shown measure is withheld whole (after filtering). `UserOut.cross_institution_stats` drives the Admin-område link; `/admin/tverrinstitusjonell-statistikk` reuses Tverrklasse-statistikk's bars, filters and tables, names only Institutions, and shows the not-found page while the flag is off. 14.3/14.4 unchanged.

**Files.**
- `backend/migrations/versions/0402_aggregate_institution.py`, `reports/models.py`, `reports/aggregates.py` — column, writer; `tests/test_migrations.py` (HEAD 0402, backfill on data in the walk).
- `reports/cross_institution.py`, `cross_institution_schemas.py` (new), `class_report_routes.py` — view, flag gate, route; `platform/authz.py` — action.
- `identity/schemas.py`, `identity/service.py` — `cross_institution_stats` via `authz.can`; `identity/personal_data.py` — text.
- Tests: `tests/reports/test_cross_institution.py` (new), raw inserts in `test_aggregates.py`, `test_cross_class_filters.py`; `tests/identity/test_login.py`.
- Frontend: `modules/reports/cross-institution{,-api,-page}.ts(x)` + Vitest, `cross-class-page.tsx` (exports), `app/(app)/admin/tverrinstitusjonell-statistikk/page.tsx`, `identity/{homes.ts,home-page.tsx}`, `copy/nb.ts` (`[ASSUMPTION] Story 14.7`), regenerated `lib/api/*`, `e2e/cross-institution.spec.ts`, `e2e/homes.spec.ts` (new Admin link).

**Review.** Four layers (blind, edge case, verification gap, intent; sonnet). Patched 4 medium (rename test, 0402 backfill on data, page flag-off e2e, filter wiring e2e) and 11 low; deferred none; rejected the rest with reasons in the triage log.

**Follow-up review recommended: true** — two or more medium patches; the REPEATABLE READ snapshot in `institution_statistics` and the `_cross_institution_stats` helper (also on invitation acceptance) have been read by no reviewer.

**Verification.** Backend full suite (`-n 8`, lane-3 DB): 4291 passed, 5 skipped (an earlier run caught `test_authz_rules` on a role comparison, fixed through `authz.can`, and the known DB-vs-host clock flake in `tests/ai/test_gateway.py`, which passes alone); ruff clean; no new test among the 40 slowest (the migration walk grew by a few hundred ms). Frontend: typecheck, Vitest 1385 passed, `lint:colours`, `check:copy`, `next build`. Playwright on the rebuilt lane-3 stack: `cross-institution`, `cross-class`, `homes`, `order-field` — 45 passed, axe at 320 and 1440 px and 200 % text. Screenshots at 320 and 1440 px read by the builder (a long withheld text squeezed the name at 320 px; moved to one line above the charts).

**Decisions taken in the founder's place.** Institution stored in the aggregate at writing (a moved Class keeps old figures where they were); an Institution's figure is the median of its compared Class sessions' stored figures (unweighted), with the session count shown; withheld sessions are left out of a cell; the single-session rule applies after filtering, and missing (unmeasured) rows do not withhold; a multi-session Institution may show a cell resting on one session's stored (≥ 10) figure; filters reuse 14.4 across all Institutions; no audit row for the Admin's reads (no Student data); route registered but 404 while off (as 14.8); link and page gated by a new `/me` field; page name and draft copy.

**New personal-data tables.** None (one column added to `class_aggregates`, an Institution id; registry stays `none`).

**Residual risks.** Pilot-scale reads (all aggregates per request).

## Close-out of Epic 14 (2026-11-23)

Follow-up review (sonnet, `review-closeout14-access`): no defect. The REPEATABLE READ read is set before the first statement on one connection and does not leak; `_cross_institution_stats` is in-memory (flag and `authz.can`) and false for non-Admins or with the flag off; the route is 404 with the flag off; figures are medians of stored, non-withheld rows. Founder decision recorded earlier stands: an Institution with one compared Class session shows that session's figures (each over at least 10 Students).
