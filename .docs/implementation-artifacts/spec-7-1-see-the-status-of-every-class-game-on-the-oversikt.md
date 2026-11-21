---
title: "Story 7.1: See the status of every Class game on the Oversikt"
type: 'feature'
created: '2026-11-21'
status: 'done'
baseline_revision: '059affcaa81c1b7fa1906628e608fb45ea29043a'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-7-context.md'
warnings: ['oversized']
deferred:
  - summary: >-
      No rebuild or reconcile path for game_summaries outside migration 0051.
    evidence: |-
      A row lost or written by a bug is only repaired by the Game's next command; overview.recompute exists but no job or CLI calls it over many Games.
    location: >-
      backend/app/modules/games/overview.py
    severity: low
  - summary: >-
      A failed background refetch of the Oversikt keeps the old data with no inline marker.
    evidence: |-
      overview-page.tsx shows the error only while there is no data; Story 7.5 (live updates, Tilkoblingslinje) owns stale-state display.
    location: >-
      frontend/src/modules/games/overview-page.tsx
    severity: low
  - summary: >-
      A Roster removal or a rename emits no session:<id> event, so an open Oversikt keeps the old name until the next change or reload.
    evidence: |-
      Names are resolved at read time and enter the ETag, but nothing invalidates classOverviewKey on a Roster change.
    location: >-
      frontend/src/lib/api/topics.ts
    severity: low
  - summary: >-
      game_summaries.occupants and waiting_for hold user ids with no foreign key; an erasure routine (Epic 15 data rights) must cover the table or rebuild it.
    evidence: |-
      The ids mirror the append-only seat_occupancy rows, so today they add no new exposure; any later scrub must include this read model.
    location: >-
      backend/app/modules/games/models.py
    severity: low
  - summary: >-
      groupsOf drops a row whose status it does not know; Epic 8's paused must add its group (or an exhaustive switch).
    evidence: |-
      overview.ts filters rows by the four statuses of Story 7.1 only.
    location: >-
      frontend/src/modules/games/overview.ts
    severity: low
---

<intent-contract>

## Intent

**Problem:** A Lecturer has no page that shows how the Class games of a Class session stand: which play, which wait and for whom, which have finished and at what chain cost (FR-39). Status is also not defined in one place yet (AD-2, AD-25).

**Approach:**
- Backend: a pure `games.rules.game_status`, a `game_summaries` read model that every `games.commands` command refreshes in its own transaction (migration 0051 with a backfill), and `GET /api/class-sessions/{id}/overview` that reads only that table, resolves names at read time and answers with an `ETag`.
- Frontend: the Oversikt page `/klasseokter/{id}/oversikt`, reached from the Klasseøkt, with headline counts, «Oppdatert hh:mm:ss» and the Class games grouped by status as text rows. The Matrisevegg, filters, live toggle and right rail come in Stories 7.2–7.6.

## Boundaries & Constraints

**Always:**
- **`rules.game_status(game, turns) -> GameStatus`** (pure, `games/rules.py`; `GameStatus` StrEnum in `schemas.py`: `not_started`, `running`, `waiting`, `finished`). `game` is a mapping with `lifecycle`, `purpose`, `settings`; `turns` are the open Week's `seat_turns` rows with the `occupant_kind` in force (`repo.week_turns_with_occupant`). `not_started`/`finished` from `lifecycle`; `running` and `playing_out` give `waiting` when at least one Student-held turn `has_ordered` and at least one Student-held turn has not (Guided Week from `rules.guided_week`, so viewing counts as ordering, FR-24), else `running`.
- **`game_summaries`** (owned by `modules/games`, `models.py`, migration `0051`): `game_id` PK FK `games.id` ON DELETE CASCADE; `class_session_id` uuid NULL (no FK, like `games`); `game_number` int NULL; `purpose` text; `status` text CHECK in the four values; `week` int NULL (open Week while running, the finished state's Week when finished, NULL before start); `wait_started_at` timestamptz NULL (earliest wait among `waiting_for`); `waiting_for` JSONB list `[{role, user_id, since}]` in chain order — Student-held turns (in force) of the open Week that have not ordered and carry `wait_started_at`, only when status is `waiting`; `occupants` JSONB list `[{role, occupant_kind, user_id}]` in chain order from the latest occupancy row (as `table_status`), `occupant_kind` null for a free Seat; `chain_cost` NUMERIC(14,4) NULL (sum of `total_cost` over the seats of the newest stored Week state, the finished one when finished; NULL before start); `version` int (the Game's version after the bump); `updated_at` timestamptz default now(). Index on `(class_session_id)`. Never a name or email.
- **Refresh:** `games/overview.py: refresh(session, game)` recomputes the row from the game tables and upserts it; `commands._commit_change` calls it after `bump_version` and before the events, so every command that commits a change (all of AD-2's list, plus `set_snapshot`, `propose_time`, `accept_time`) updates the row in the same transaction. A command that changes nothing (already viewed, already accepted) writes no row. `recompute(session, game_id)` returns the same values, for the test.
- **Backfill:** migration 0051 inserts a row for every existing Game in SQL that mirrors `game_status` and the column rules above exactly; an api test runs that SQL over played Games and compares with `recompute`.
- **Endpoint** `GET /api/class-sessions/{id}/overview` (`operation_id="getClassOverview"`, route in `sessions/routes.py`, service in new `sessions/overview.py`): new authz action `class_sessions.overview` (account roles Lecturer, Assistant; Class staff roles owner, assistant) through `_class_for`; any refusal, unknown id or malformed id is 403 `forbidden`, the same for all. Body `ClassOverviewOut`: `items` + `next_cursor: null` (list envelope), `counts {waiting, running, not_started, finished}`, `server_now` (database clock), `before_start` (`not sessions.is_locked(row)`), `start_at`, `class_name`, `session_number`. Each item `OverviewGameOut`: `game_id`, `game_number`, `status`, `week`, `version`, `chain_cost` (decimal string or null), `wait_started_at`, `waiting_for [{role, name|null, since}]`, `seats [{role, holder: student|ai|free, name|null}]` Fabrikk first. Names via `classes.student_names` at read time (a removed Student reads as null). `week` and `chain_cost` are null while `before_start`. Rows only for purposes with `policy.lecturer_overview` (`purposes_with`), ordered by `game_number`.
- **ETag:** strong, a hash of the body without `server_now`; header `Cache-Control: private, no-cache`; a matching `If-None-Match` answers 304 with no body. Query count is fixed whatever the number of Games (test with 100).
- **Frontend:** route `src/app/(app)/klasseokter/[sessionId]/oversikt/page.tsx`; module `src/modules/games/overview*.ts(x)`; `useClassOverview` fetches with `cache: "no-store"`; `topics.ts` maps `session:<id>` to the overview key too. Page: crumbs Lærerhjem › Class › Klasseøkt › Oversikt; h1 «Oversikt»; headline «41 ferdig · 15 pågår · 4 venter» (+ «· 3 ikke startet» when any) and «Oppdatert hh:mm:ss» (Europe/Oslo, from `server_now`) in caption text; groups Venter (longest wait first), Pågår, «Ikke startet», «Ferdig, lavest kjedekost øverst» (lowest first), each header «Venter 4», empty groups left out. Row: «Spill n», «Uke n», for a waiting game «Venter på Noah (Grossist), 23 t» per waited Seat (Role when no name; duration from `waitDuration` against `server_now` plus elapsed time), the four Seats Fabrikk first as «Fabrikk: Mikkel» or «KI-spiller» (free Seat «Ledig»), and the kjedekost in whole kroner, «1 058 kr», via `formatNumber(cost, { decimals: 0 })` + `KRONER`, with the label «Kjedekost» for assistive technology. Before the Start date: no headline counts, a line naming the Start date, the allocation rows (game number and Seats only), or «Ingen spill er fordelt ennå.». Loading shows the Skjelett in the PageShell; 403 shows `AccessDenied`. Klasseøkt gets a Lenke «Oversikt» for staff. All copy in `nb.ts` (`nb.overview`), draft copy marked `[ASSUMPTION]`.
- Layout one column below 1024 px, no page-level horizontal scroll, data-centric look with tokens from `DESIGN.md`, numbers `tabular-nums`, no pills or metaphors.

**Never:** no Matrisevegg, filters, «Oppdater automatisk», right rail, Varselbånd or Messages (7.2–7.11); no Pause status (Epic 8); no progress shown as Weeks of a total or any game length (FR-14); no quantity, status or cost computed in the web app; no names stored in `game_summaries`; no second status definition in Python.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Waiting | One Student ordered, another Student Seat has not | status `waiting`, `waiting_for` the unordered Student Seat with its `wait_started_at` | — |
| Guided view | Guided Week, one Student viewed, other not | `waiting` | — |
| AI only waits | Students all ordered, LLM Seat not | `running` | — |
| No Students | Game of AI players only | `running` until finished | — |
| Test Game | `lecturer_test` Game in the session | not listed, not counted | — |
| Not staff | Student, other Class's Lecturer, unattached Admin, unknown id | 403 `forbidden`, page «Du har ikke tilgang til denne siden.» | same answer for all |
| Repeat | `If-None-Match` equal to the ETag | 304, empty body | — |
| Before start | session not locked | `before_start: true`, week/cost null | — |

</intent-contract>

## Code Map

- `backend/app/modules/games/commands.py:243` -- `_commit_change`: lock, bump, emit; called last in every command (create 433, assign 547, set_snapshot 660, move_seat 784 per Game, start 1025, place_order 1386, view_week 1460, advance 1558, switch 1631, propose 1743, accept 1784); `finish` runs inside `_step` before it.
- `backend/app/modules/games/rules.py` -- `has_ordered`, `guided_week`, `week_complete`: reuse in `game_status`.
- `backend/app/modules/games/repo.py:99,447,424` -- `seats_with_occupant`, `week_turns_with_occupant`, `open_week`; `_listed()`/`purposes_with` for AD-13.
- `backend/app/modules/games/views.py:295` -- `table_status`: same holder/name rules (free/student/ai, Fabrikk first).
- `backend/app/modules/games/summaries.py` -- the sim runner's `game_summary` (unrelated name; leave it).
- `backend/app/modules/games/service.py` -- add `class_overview(session, class_session_id)` read for `sessions`.
- `backend/app/modules/sessions/service.py:644,538,1204` -- `_class_for`, `is_locked`, `_names_in` pattern; `routes.py:172` route style.
- `backend/app/platform/authz.py:80,130` -- `POLICIES`, `CLASS_STAFF_ROLES`.
- `backend/migrations/versions/0050_test_games.py` -- revision chain; new `0051_game_summaries.py`.
- `backend/tests/conftest.py:162` -- `GAMES_TABLES` (add `game_summaries`); `tests/games/helpers.py` `_ONE_GAME` dump/restore (add `game_summaries`), `classic_game`, `play_week`, `seat_student`.
- `backend/tests/games/test_place_order.py:143-170` -- statement-order test that must learn the summary upsert.
- `frontend/src/modules/sessions/class-session-page.tsx` -- add «Oversikt» Lenke; `AccessDenied`, `GuardedPage`, `PageShell` from `modules/identity`.
- `frontend/src/modules/games/seat-status.ts:19` -- `waitDuration`; `src/lib/number-format.ts` -- `formatNumber`; `src/lib/api/topics.ts` -- `session` case.
- `frontend/e2e/support/live-game.ts` -- `liveClassGame` for a started Class game; `classes.ts` -- `test`, `freshLecturer`, `freshClass`, `VIEWPORTS`, `expectAccessible`.

## Tasks & Acceptance

**Execution:**
- `backend/app/modules/games/schemas.py`, `rules.py` -- `GameStatus`, `game_status` -- one definition (AD-2).
- `backend/app/modules/games/models.py`, `backend/migrations/versions/0051_game_summaries.py` -- table + SQL backfill -- AD-25.
- `backend/app/modules/games/repo.py`, `overview.py`, `commands.py` -- recompute/upsert, call from `_commit_change` -- same transaction.
- `backend/app/modules/games/service.py` -- `class_overview` read -- for `sessions`.
- `backend/app/platform/authz.py` -- `class_sessions.overview` -- FR-5.
- `backend/app/modules/sessions/schemas.py`, `overview.py`, `routes.py` -- endpoint with ETag/304 -- AD-3, AD-25.
- `backend/tests/games/test_game_summaries.py` (with the `game_status` matrix), `backend/tests/sessions/test_overview.py`; update `conftest.py`, `helpers.py`, `test_place_order.py` -- status matrix, recompute after every command, backfill equality, endpoint authz/ETag/AD-13/fixed queries (100 Games).
- `frontend/src/lib/api/openapi.json`, `schema.ts` -- regenerate.
- `frontend/src/copy/nb.ts`, `src/modules/games/overview.ts` (+ `overview.test.ts`), `overview-page.tsx`, `src/app/(app)/klasseokter/[sessionId]/oversikt/page.tsx`, `src/modules/identity/homes.ts`, `src/lib/api/topics.ts`, `src/modules/sessions/class-session-page.tsx` -- the page.
- `frontend/e2e/overview.spec.ts` -- started game, before-start, refusal, axe at 1440/320/200 % text.

**Acceptance Criteria:**
- Given any command in AD-2's list commits, when the test reads `game_summaries`, then the row equals `recompute` for that Game.
- Given a Lecturer or Assistant of the Class, when they open the Oversikt of a started session, then they see headline counts, «Oppdatert …», grouped rows with «Spill n», «Uke n», waits, Seats and kjedekost, and no Week total.
- Given the Oversikt at 1440 px, 320 px and 200 % text, when Playwright runs axe, then there are no violations and no page-level horizontal scroll.

## Spec Change Log

## Review Triage Log

### 2026-11-21 — Review pass
- Layers: blind hunter and edge-case hunter only (Sonnet), as the orchestrator asked for this lane; verification-gap and intent-alignment were skipped on that instruction. Both reviewers' reports came back through files, because the handback channel dropped their final messages.
- verdicts: 24 findings — high 0, medium 1, low 13, false 8, maybe-false 2
- findings:
  - `[low]` `[patch]` nb.ts: the «Links between pages» doc comment ended up above `overview` — moved back above `navigation`.
  - `[false]` `[reject]` Backfill Guided-Week test ignores `policy.guided_weeks` — `GamePolicy.guided_weeks` is `Literal["settings"]` for every purpose, and `GameSettings` always dumps `guided_weeks`, so the SQL and `rules.guided_week` agree.
  - `[low]` `[patch]` Backfill-equality test is narrow — added a Game whose Student Seat was taken over in the open Week after the other Student ordered (occupant in force by `from_week`). It is compared with `recompute` and is `waiting`.
  - `[low]` `[patch]` Fixed-query test reused one Student and had no waits — the 99 added Games now have distinct Students and a waited-for Seat each.
  - `[low]` `[reject]` Every-command test omits `propose_time`/`accept_time` — they are not in the AC's command list, and they run through the same `_commit_change`.
  - `[low]` `[reject]` Waiting is derived in `game_status` and again per Seat in `recompute` — the status comes only from `game_status`; `recompute` reuses `rules.has_ordered` to list Seats. No named divergence.
  - `[maybe-false]` `[reject]` `waiting` with an empty `waiting_for` — reachable only for turns opened before 0048 or a future mid-Week reclaim. The row still lists under Venter. If true it is low and needs a fallback branch.
  - `[low]` `[patch]` ETag matching ignores `W/` and `*` — now uses weak comparison, accepts `*`, and the test sends a multi-tag header with a weak tag.
  - `[false]` `[reject]` Refresh silently skipped when `game is None` — `lock_game` returns None only for a Game that does not exist, so it has no row to keep.
  - `[low]` `[reject]` Heavier write path — measured: the full backend suite runs in 70–74 s, as before. The extra statements are three reads and one upsert on the locked Game.
  - `[low]` `[reject]` `before_start` (api clock) and `server_now` (db clock) — this is the same rule the Klasseøkt uses (`get_session`). Tests fix the api clock (Issue #63).
  - `[low]` `[reject]` Matrix gaps (Assistant in e2e, removed Student, Ikke startet group) — covered at the api (`test_overview`) and in Vitest (`groupsOf`, `seatTexts`).
  - `[false]` `[reject]` No live refresh — the app-wide event stream invalidates `classOverviewKey` on `session:<id>` (topics test). Live behaviour is Story 7.5's.
  - `[low]` `[reject]` Empty `<p>` cells and `lg:sr-only` cost label — empty paragraphs are not announced; the cost reads «… kr» with the label for assistive technology.
  - `[low]` `[reject]` Spec and context gaps (longest-waiting game, `BACKFILL.format`) — the longest-waiting game belongs to 7.11. Fixing these means editing the spec.
  - `[false]` `[reject]` (edge) Backfill guided for other purposes — the same refutation as above.
  - `[maybe-false]` `[reject]` (edge) Empty `waiting_for` while waiting — duplicate of the finding above.
  - `[low]` `[patch]` (edge) Weak or `*` ETag — duplicate, patched above.
  - `[low]` `[reject]` (edge) A 304 carries no fresh `server_now` — no client sends `If-None-Match` yet. The Design Notes leave re-anchoring to Story 7.5.
  - `[false]` `[reject]` (edge) `number_of` may return None — it is a `count()` and always an int.
  - `[false]` `[reject]` (edge) Erasure leaves user ids in `game_summaries` — the row mirrors the append-only `seat_occupancy`, which keeps the same ids, and `recompute` rebuilds it from there.
  - `[false]` `[reject]` (edge) Refresh runs for every purpose — intended: the AC asks for one row per Game.
  - `[medium]` `[patch]` (edge) A finished game shows its last Uke, which tells the game's length (FR-14) — the api now sends `week: null` for finished games. The stored row keeps it.
  - `[low]` `[patch]` (edge) Fixed-query test with one Student — duplicate, patched above.

### 2026-11-21 — Review pass (relayed findings)
- The orchestrator relayed the same two reviewers' full lists (15 blind, 9 + 5 edge). Items already triaged above keep their verdicts (carried).
- verdicts: 29 findings — high 0, medium 1, low 17, false 8, maybe-false 3
- findings:
  - `[low]` `[patch]` (carried) nb.ts orphaned comment — fixed in the first pass.
  - `[low]` `[patch]` (carried) weak and `*` If-None-Match — fixed in the first pass.
  - `[low]` `[patch]` e2e asserts «under 1 min» at three widths, which a slow CI could pass beyond — the regex now accepts «under 1 min» or «n min».
  - `[low]` `[patch]` (carried) fixed-query test with one Student — fixed in the first pass.
  - `[low]` `[reject]` before_start masking untested, two clocks, early lock — `is_locked` counts `locked_at`, so an early lock counts. The before-start api test asserts week and cost are null. The clock is the Klasseøkt's.
  - `[low]` `[patch]` The spec named `test_game_status.py` — the Tasks line now names `test_game_summaries.py`. propose/accept stay as rejected (carried).
  - `[false]` `[reject]` Backfill guided_weeks key missing or other purpose — the same refutation as the first pass. Migration 0051 is unchanged.
  - `[low]` `[defer]` No rebuild path outside 0051 — deferred.
  - `[low]` `[defer]` Stale data on a failed refetch — deferred to Story 7.5's live and stale display.
  - `[false]` `[reject]` The Start-date transition is never re-evaluated — the lock at the Start date runs `set_snapshot` per Class game, which emits `session:<id>`, and the page refetches.
  - `[low]` `[defer]` A rename or Roster removal emits no event — deferred.
  - `[false]` `[reject]` The second e2e test never closes its student context — the `ownContextsClosed` auto fixture closes every context a test opens. Long names at 320 px: rows wrap with `overflow-wrap:anywhere`.
  - `[low]` `[reject]` (carried) Refresh cost under the row lock.
  - `[false]` `[reject]` NUMERIC(14,4) against the unrounded sum — every `total_cost` has at most 4 decimals, so the sum does too. The every-command test compares stored with recomputed values exactly.
  - `[low]` `[reject]` Fixtures re-exported through `__all__` — the existing pattern of `tests/sessions/*`.
  - `[maybe-false]` `[reject]` (carried) waiting with an empty waiting_for.
  - `[false]` `[reject]` (carried) Backfill ignores policy guided_weeks.
  - `[low]` `[defer]` user ids in game_summaries on erasure — deferred to Epic 15 data rights.
  - `[low]` `[defer]` An unknown status (Epic 8 paused) drops rows — deferred to Epic 8.
  - `[low]` `[reject]` (carried) A 304 with a stale server_now.
  - `[false]` `[reject]` (carried) number_of returns None.
  - `[false]` `[reject]` (carried) Refresh for every purpose.
  - `[medium]` `[patch]` (carried) A finished game reveals its length — fixed in the first pass.
  - `[maybe-false]` `[reject]` (carried) Confirm waiting_for is never empty.
  - Remaining relayed rows are duplicates of the rows above (=), each with the same verdict.
- Follow-up review: not recommended. No high was patched in this pass.

## Design Notes

- **Why `_commit_change`:** every command calls it after its writes, inside its transaction, with the Game row locked, so one call site covers all commands and those added later; the upsert sits between the version bump and the NOTIFY.
- **ETag and the browser:** with `no-cache` a browser would revalidate by itself and hand JS a cached body whose `server_now` is old, so waits and «Oppdatert» would lag. The web app fetches with `cache: "no-store"`; the 304 path serves explicit clients (tests, Story 7.5 may send `If-None-Match` itself and re-anchor on the previous `server_now`).
- **Backfill in SQL:** migrations import no app code; a test keeps the SQL and `recompute` equal.

## Verification

**Commands:**
- `cd backend && uv run pytest tests/games tests/sessions/test_overview.py -q` -- passes
- `cd backend && uv run pytest -q -n auto` -- full suite passes once before commit
- `cd frontend && npm run typecheck && npx vitest run && npm run lint:colours && npm run build` -- pass
- `cd frontend && npx playwright test e2e/overview.spec.ts e2e/homes.spec.ts e2e/class-session.spec.ts e2e/order-confirm.spec.ts` -- pass

## Auto Run Result

Status: done

**Summary.** The Oversikt of a Class session.
- `games.rules.game_status` is the single status definition.
- `game_summaries` (migration 0051, with an SQL backfill) is rewritten by `commands._commit_change` in every command's transaction.
- `GET /api/class-sessions/{id}/overview` reads it in a fixed number of queries. It has an ETag, a 304, and a uniform 403 through the new `class_sessions.overview` policy.
- The page `/klasseokter/{id}/oversikt` shows the headline counts, «Oppdatert hh:mm:ss», the groups Venter, Pågår, Ikke startet and Ferdig, and a row per game. Before the Start date it shows the allocation only.
- The Klasseøkt links to it, and `session:<id>` refreshes it.

**Files.**
- Backend, `games` module:
  - `rules.py` adds `game_status`; `schemas.py` adds `GameStatus`; `models.py` adds `game_summaries`.
  - `repo.py` adds `newest_week`, `upsert_summary` and `class_summaries`.
  - `overview.py` adds `recompute` and `refresh`; `commands.py` calls the refresh; `service.py` adds `class_overview`.
- Backend, `sessions` module: `overview.py` holds the service and the ETag, `routes.py` the route, and `schemas.py` the response models.
- Backend, other:
  - `platform/authz.py` adds the policy.
  - `migrations/versions/0051_game_summaries.py` adds the migration.
  - Tests: `tests/games/test_game_summaries.py` and `tests/sessions/test_overview.py` are new. `conftest.py`, `helpers.py`, `test_place_order.py` and `test_migrations.py` are updated.
- Frontend:
  - `modules/games/overview.ts` (and its test), `overview-page.tsx`, and `api.ts` (the hook).
  - The route `app/(app)/klasseokter/[sessionId]/oversikt/page.tsx`.
  - `copy/nb.ts` (`nb.overview`), `identity/homes.ts`, and `lib/api/topics.ts` (and its test).
  - `sessions/class-session-page.tsx` (the link).
  - The regenerated `openapi.json`/`schema.ts`, and `e2e/overview.spec.ts`.

**Review.**
- 24 findings.
- 6 patches: 1 medium (finished Uke hidden, FR-14) and 5 low (the nb.ts comment, the weak ETag, the fixed-query test, the backfill test, and one duplicate).
- None deferred. The rest were rejected; the triage log gives the reasons.
- Patched counts: high 0, medium 1, low 5. A follow-up review is not recommended.

**Verification.**
- Backend:
  - Full suite: 2793 tests pass in 70 s; Ruff is clean.
  - New tests over 1 s: `test_game_summaries.py` has three tests at 1.1–1.6 s, because they play short games.
  - `test_overview.py` has three tests that each spend about 2.9 s in fixture setup to make a Class.
- Frontend: typecheck, Vitest (718), `lint:colours`, `check:copy` and the build all pass.
- Playwright:
  - `overview.spec.ts` passes, with axe at 1440 px, 320 px and 200 % text.
  - `class-session`, `homes`, `order-confirm` and `live-updates` pass (47 tests).
  - The weak-ETag and finished-`week` patches came after the review. They are verified by api tests only; the e2e ran on the build from before them and touches neither.

**Decisions taken instead of the founder.**
- The route lives in `sessions`, like every `/class-sessions` route.
- New authz action: `class_sessions.overview`.
- «Ikke startet» is its own group, between Pågår and Ferdig. The headline adds «· n ikke startet» only when n > 0.
- The cost is shown in whole kroner. A free Seat reads «Ledig».
- A finished game shows no Uke (FR-14).
- The browser fetches with `cache: "no-store"`, so `server_now` stays fresh. The 304 path is for explicit clients.
- The builder implemented the story in its own context, as the orchestrator instructed, not through a separate subagent.

**Residual risks.**
- The backfill SQL mirrors the Python, and a test keeps the two equal. Epic 8 must extend both for `paused`.
- Waits on turns opened before 0048 show no «Venter på» line.

**Second triage pass (relayed findings):** 2 low patches: the e2e wait regex and the spec's test file name. 5 low deferred, listed in the frontmatter. No change to migration 0051.
