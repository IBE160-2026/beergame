---
title: 'Story 5.8: Preview a random allocation and run it again'
type: 'feature'
created: '2026-11-20'
status: 'done'
baseline_revision: 'a54ca871e84c099aeab7858d525db10140623bbd'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-5-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-5-7-mark-obligatory-set-inactivity-limit.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** A Lecturer cannot see how the registered Students would be split into Class games before anyone is told, nor draw again (FR-20). Story 5.9 needs a stored draft (id + `revision`) to confirm.

**Approach:** A pure, deterministic `sessions.allocation.allocate(student_ids, seed)`; one stored current draft per Class session in a new `allocation_drafts` table (migration 0037); read, open (draw if none) and redraw routes; and an in-place «Fordeling» panel on the Klasseøkt with a plain-SVG Fordelingsforhåndsvisning, a «Vis som liste» alternative and «Kjør fordeling på nytt». Names resolve at read time through a new `classes.service` scope helper.

## Boundaries & Constraints

**Always:**
- `allocate(student_ids, seed) -> list[Seat]` (`Seat(user_id, game_number, role)`), pure: ids sorted first, `random.Random(seed)` shuffles them, chunks of four in order (games numbered from 1), each chunk takes a shuffled copy of `engine.settings.ROLES` so a Student's Role is random; a short last chunk (1–3) leaves its remaining Roles empty. 0 ids → `[]`. Same ids (any order) and seed → same result. `draw_seed()` = `secrets.randbelow(2**53)`.
- Migration 0037 `allocation_drafts`: `id` uuid PK, `class_session_id` FK `class_sessions` CASCADE, UNIQUE (`uq_allocation_drafts_class_session`), `revision` int NOT NULL CHECK ≥ 1, `seed` BigInteger NOT NULL, `assignments` JSONB NOT NULL (`[{"user_id","game_number","role"}]`, ids only), `drawn_by` FK users SET NULL nullable, `drawn_at` timestamptz NOT NULL. No names or emails (AD-14).
- Routes (`authz`: read `class_sessions.read`, writes `class_sessions.manage`; FR-5 403 as the other routes; writes pass `_writable` → 409 `class_archived`):
  - `GET /api/class-sessions/{id}/allocation` → `AllocationOut`.
  - `POST /api/class-sessions/{id}/allocation` (open): returns the stored draft unchanged if one exists (never recomputed); else draws from `classes.registered_students` and stores revision 1. With no registered Student it stores nothing.
  - `POST /api/class-sessions/{id}/allocation/redraw`: new seed, the old row replaced by a new draft id, revision 1. With no registered Student the old draft is removed and none stored.
  - Writes lock the `class_sessions` row; once `is_locked`, 409 `session_locked` `{"allocation": "locked"}`. A stored draft emits `session:<id>` only (registry `sessions.draw_allocation: {"session"}`); no notice, no `user:` event, no Game or Seat.
- `AllocationOut`: `registered_count`, `missing_count` (registered Students not in the draft), `draft: null | {id, revision, drawn_at, games: [{number, seats: [{role, user_id|null, name|null}]}]}`; seats in order factory, distributor, wholesaler, retailer; games by number. `name` from `classes.service.student_names(class_id, ids)` (new; only ids that are registered Students of that Class now, via `identity`); a removed Student keeps `user_id` with `name: null`.
- Web, block «Fordeling» in the dates column below the date fields: closed shows a state line («Ikke bekreftet.», or with `registered_count` 0 «Ingen registrerte studenter å fordele ennå.» and nothing else) and Lenke «Se fordelingen» when a draft exists or the User can draw (`can_manage && !locked`). Opening calls POST (can draw) or uses the GET, and moves focus to the panel heading (`tabindex=-1`). Panel: heading «Fordeling: N Klassespill à 4», line «{n} studenter fordeles tilfeldig. Hver søyle er ett spill, hver rad en Rolle. Tomme seter får KI-spiller.», Visningsbryter «Diagram» / «Vis som liste», «Kjør fordeling på nytt» (secondary, only if can draw), «Lukk» Lenke returning focus to the opener. `missing_count` > 0 shows «{n} registrerte studenter er ikke med. Kjør fordeling på nytt for å ta dem med.». No confirm button (Story 5.9).
- Diagram: hand-made SVG in `frontend/src/modules/sessions/`, no chart library, inside `ScrollRegion`; Role labels left, Fabrikk top; one column per game, filled `bar-base` cells, empty Seat `paper` with `ink-muted` border; the selected column framed `ink`; one tab stop (roving) with ←/→/Home/End moving the selection, click selects; ticks 1, selected, last. Under it «Spill 17» + «Ida, Detaljist. Sara, Grossist. …» (retailer → factory), «KI-spiller» for empty, «Ikke lenger i Klassen» for `name: null` with a user id. List view: `<ol>` of the same lines, reflowing.
- All new copy in `nb.ts` (`sessions.allocation`), [ASSUMPTION] except the heading form, «Tomme seter får KI-spiller.», «Vis som liste», «Kjør fordeling på nytt», «Ikke bekreftet.».

**Never:** confirm, Games, Seats, notices (5.9); move/swap (5.10); lock auto-allocation (5.11/5.12); a recomputed preview; names or emails stored; a chart library or the AD-18 chart module; touching the demo Class; comparing DB time with host time.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| allocate counts | 1..9, 250 ids | ⌈n/4⌉ games; all full except at most one with n mod 4; every id once; Roles distinct per game | – |
| deterministic | same ids shuffled, same seed | identical result | – |
| Open, none stored | 5 registered | draft rev 1, 2 games, `session` event | – |
| Open, stored | draft exists | same id/revision/assignments | – |
| Only registered | 2 registered + 1 invited | only the 2 allocated | – |
| Redraw | draft exists | new id, rev 1, new seed | – |
| No Students | 0 registered | `draft: null`, `registered_count` 0 | – |
| Missing | registered after draw | `missing_count` 1, draft unchanged | – |
| Removed | Student removed after draw | seat keeps `user_id`, `name: null` | – |
| Locked | Start date passed | GET works | open/redraw 409 `session_locked` |
| Assistant | reads | GET 200 | open/redraw 403 |
| Archived | Class archived | GET 200 | open/redraw 409 `class_archived` |

</intent-contract>

## Code Map

- `backend/app/modules/sessions/allocation.py` (new) -- pure `allocate`, `Seat`, `draw_seed`. Roles from `app.engine.settings.ROLES` (`settings.py:32`, order retailer→factory).
- `backend/app/modules/sessions/models.py` -- add `allocation_drafts` (pattern `lab_hours` :88).
- `backend/migrations/versions/0037_allocation_drafts.py` (new, revises 0036; pattern 0035). `backend/tests/test_migrations.py:70` HEAD → 0037.
- `backend/app/modules/sessions/repo.py` -- `draft_of`, `replace_draft` (delete + insert), `delete_draft`.
- `backend/app/modules/sessions/schemas.py` -- `AllocationOut`, `AllocationDraftOut`, `AllocationGameOut`, `AllocationSeatOut`.
- `backend/app/modules/sessions/service.py` -- `allocation_of`, `open_allocation`, `redraw_allocation`; reuse `_class_for`, `_managed_session` (:991), `_writable` (:444), `is_locked` (:353), `SessionLocked`; module docstring.
- `backend/app/modules/sessions/routes.py` -- three routes; map `SessionLocked` to 409; docstring. `README.md` -- Story 5.8.
- `backend/app/modules/classes/service.py:607` -- `student_names(class_id, ids) -> dict[UUID, str]`; `identity/service.py` + `repo.py:999` -- `student_names` query (users ⋈ roster_entries registered, not removed).
- `backend/app/platform/events/registry.py:33` -- `sessions.draw_allocation`.
- Tests: `backend/tests/sessions/test_allocation.py` (new; pure unit tests + routes; helpers `new_session`, `student_of`, `at`, `refusal` from `test_dates.py`, `ASSISTANT`/`put_staff`/`call` from `tests/classes/test_staff.py`, `emitted`).
- Web: `frontend/src/modules/sessions/allocation.ts` (+ `.test.ts`: heading, game line, role order, ticks); `allocation-panel.tsx` (block + panel + SVG `AllocationChart`); `api.ts` (`useAllocation`, `openAllocation`, `redrawAllocation`, key `allocationKey`); `class-session-page.tsx:276` place the block after `DateFields`; `copy/nb.ts` `sessions.allocation`; reuse `components/{view-toggle,scroll-region,button,link}.tsx`, `LINK_BUTTON`. Regenerate `lib/api/openapi.json` (`cd backend && uv run python -m app.openapi ../frontend/src/lib/api/openapi.json`) and `schema.ts` (`npm run api:generate`).
- E2e: `frontend/e2e/class-session-allocation.spec.ts` (new); fresh Lecturer/Class via `support/classes.ts`; Students via `POST /api/classes/{id}/roster/manual` `{email, name}`.

## Tasks & Acceptance

**Execution:**
- `allocation.py`, `models.py`, migration 0037, `repo.py`, `schemas.py`, `service.py`, `routes.py`, `README.md`, `registry.py`, `classes/service.py`, `identity/{service,repo}.py` -- the draft and its routes.
- `backend/tests/sessions/test_allocation.py`, `tests/test_migrations.py` -- every matrix row; allocate over 1..9 and 250; a fixed-seed golden result.
- `api.ts`, `allocation.ts(+test)`, `allocation-panel.tsx`, `class-session-page.tsx`, `nb.ts`, regenerated api types -- the screen.
- `frontend/e2e/class-session-allocation.spec.ts` -- open (focus in panel), 5 Students → 2 columns, select by keyboard, list view, redraw changes draft id with no Game, no-Students state, Assistant read-only, axe at 320/360/1440 and 400 % zoom, chart scrolls in its region with 100 games (stubbed GET), no page horizontal scroll.

**Acceptance Criteria:**
- Given registered Students, when the Lecturer opens «Fordeling», then a draft is stored and shown, focus is in the panel, and reopening shows the same draft.
- Given the preview, when a column is selected by keyboard or click, then it is framed in `ink` and its four names (or «KI-spiller») show; «Vis som liste» shows every game as a list.
- Given «Kjør fordeling på nytt», then the draft id changes, the preview redraws, and no Game, Seat or notice exists.
- Given no registered Students, then the block says nobody is to allocate, with no draft and no confirm.

## Spec Change Log

## Review Triage Log

### 2026-11-20 — Review pass
- verdicts: 28 findings — high 0, medium 3, low 24, false 1, maybe-false 0
- findings:
  - `[medium]` `[patch]` (blind) Opening a stored draft answers 409 once the Start date passed on a page loaded before it. `draw_allocation` now returns a stored draft before the lock check; only a draw is refused. Pinned in `test_once_locked_the_draft_is_read_but_never_drawn`.
  - `[low]` `[patch]` (blind) A redraw that empties the draft leaves `open` true and focus on body. The block now closes the panel and focuses the opener when the draft becomes null.
  - `[low]` `[patch]` (blind) A second redraw is not announced. The status line is cleared before each redraw.
  - `[low]` `[reject]` (blind) `class_archived` falls to the generic copy. An archived Class gives `can_manage` false, so the screen offers no draw; only a race at the archive moment reaches it.
  - `[low]` `[patch]` (blind) The missing line tells a reader who cannot draw to redraw. The redraw sentence (`missingRedraw`) now shows only when the User can draw.
  - `[medium]` `[patch]` (blind) A draft stored before every Student left is unreachable. The opener shows whenever a draft exists; the nobody line only when there is no draft either.
  - `[low]` `[reject]` (blind) An Assistant sees «Ikke bekreftet.» with no draft. A true statement: nothing is confirmed; Story 5.11 allocates at the lock.
  - `[low]` `[reject]` (blind) Students are read outside the locked transaction. Roster writes never take the Class session lock, so moving the read closes no race; `missing_count` shows late registrants and Story 5.9 handles removals at confirm.
  - `[false]` `[reject]` (blind) A Student with no name looks removed. `users.name` is NOT NULL.
  - `[low]` `[patch]` (blind) Tick numbers overlap at a 10 px pitch next to the first or last game. `ticks` takes a `minGap` and drops the first or last number near the selected one; unit-tested.
  - `[low]` `[reject]` (blind) A fast double click sends two POSTs. Opening is idempotent; two redraws leave the second shown, which is the stored one.
  - `[low]` `[reject]` (blind) The allocation query is not refetched on `session:<id>`. Refetch on events is Story 6.4's, as for every other Klasseøkt read.
  - `[low]` `[patch]` (blind) Stale `SESSION_TABLES` docstring. Corrected.
  - `[low]` `[patch]` (blind) `drawn_by` and `drawn_at` not asserted. Asserted now; a concurrency test is not added (unique constraint plus row lock).
  - `[low]` `[reject]` (blind) The seed-limit comment though the seed is not exposed. The bound keeps the BigInteger exact if an audit or Story 5.18 exposes it; harmless.
  - `[low]` `[patch]` (blind) Route docstrings leave out `class_archived` and the read after the lock. Docstring updated.
  - `[low]` `[reject]` (edge) Students read outside the lock. As blind row 8.
  - `[medium]` `[patch]` (edge) Stored draft hidden when `registered_count` is 0. As blind row 6.
  - `[low]` `[patch]` (edge) Stale `locked` gives 409 on opening. As blind row 1.
  - `[low]` `[reject]` (edge) Selected game out of range after a refetch. The fallback to game 1 keeps chart and line consistent; the next selection resets it.
  - `[low]` `[patch]` (edge) A redraw to null leaves `open` true. As blind row 2.
  - `[low]` `[patch]` (edge, claim) The nobody line shows while a draft exists. As blind row 6.
  - `[low]` `[patch]` (verification-gap) The delete path of a redraw with nobody left was untested. The test now reads back, counts rows and checks the `session` event.
  - `[low]` `[patch]` (verification-gap) The missing line was never rendered in a test. The e2e registers a late Student, reloads and asserts `missing(1)` with the redraw sentence.
  - `[low]` `[patch]` (intent) «Tomme seter får KI-spiller.» was joined to the lead. It is now its own line (`emptySeats`).
  - `[low]` `[reject]` (intent) The draw happens on the Lenke press, not on render. Deliberate: rendering a page should not write, and «opens the allocation block» names the opening (Design Notes).
  - `[low]` `[reject]` (intent) The 100-game and axe checks use a stubbed draft. Drawing 400 registered Students per viewport would make the suite slow (founder rule); the draw is pinned at the api.
  - `[low]` `[reject]` (intent) Locked and Assistant screens use rewritten GETs. As in Stories 5.3 to 5.7; the real refusals are pinned in `test_allocation.py`.

## Design Notes

- Opening the panel is the draw (AC: «when the Lecturer opens the allocation block … draws a seed»), idempotent while a draft exists, so the screen always renders the stored draft. Assistants and locked sessions only read.
- `missing_count` exists because a draft is never recomputed: a Student who registers after the draw would otherwise vanish silently until 5.13.
- Columns are narrow (mockup density); the list view and the selected-game line are the equivalent controls for touch (WCAG 2.5.8 equivalent exception).

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/sessions/test_allocation.py tests/test_migrations.py -q` -- pass, each test under 1 s (migration tests aside).
- `cd backend && uv run pytest -q && uv run ruff check . && uv run ruff format --check .` -- pass.
- `cd frontend && npm run typecheck && npm test && npm run check:copy && npm run lint:colours && npm run build` -- pass.
- `cd frontend && npx playwright test` against `timeout 900 docker compose up -d --build --wait proxy worker-batch` -- pass.

## Auto Run Result

Status: done

**Summary.** The Klasseøkt has a «Fordeling» block under the dates. Closed, it states «Ikke bekreftet.» (or «Ingen registrerte studenter å fordele ennå.») with the Lenke «Se fordelingen». Opening draws a draft when none is stored: `sessions.allocation.allocate(student_ids, seed)` (pure and deterministic: ids sorted, then shuffled with the seed, groups of four, one Role shuffle per group, only the last group short) over `classes.registered_students`. The draft is the session's one row in `allocation_drafts` (migration 0037: id, revision 1, seed, assignments as ids/game/Role, drawn_by, drawn_at). The panel always shows the stored draft: «Fordeling: N Klassespill à 4», a plain-SVG chart in its own scroll region (Fabrikk at the top, `bar-base` cells, outlined empty Seats, the selected column framed in `ink`, one tab stop with arrows/Home/End), the selected game's line, and «Vis som liste». «Kjør fordeling på nytt» (secondary) stores a new draft under a new id. Names are read at request time through the new scope helper `classes.service.student_names`. A draw emits `session:<id>` only; no Game, Seat or notice exists.

**Files changed**
- Backend: `sessions/allocation.py` (new), `models.py`, `repo.py`, `schemas.py`, `service.py`, `routes.py`, `README.md`; `migrations/versions/0037_allocation_drafts.py` (new); `classes/service.py` and `identity/{service,repo}.py` (`student_names`); `events/registry.py` (`sessions.draw_allocation`). Tests: `tests/sessions/test_allocation.py` (new), `tests/test_migrations.py` (head 0037, constraint test).
- Frontend: `sessions/allocation.ts` + test (new), `allocation-panel.tsx` (new), `api.ts`, `class-session-page.tsx`, `copy/nb.ts`; regenerated `lib/api/{openapi.json,schema.ts}`; e2e `class-session-allocation.spec.ts` (new).

**Review findings.** 28 findings: 0 high, 3 medium, 24 low, 1 false. 16 patched (3 medium, 13 low): reading a stored draft after the lock, a stale draft hidden when every Student left, the panel left open on an emptied draft, the redraw announcement, the missing line for readers who cannot draw, tick overlap, the separate «Tomme seter får KI-spiller.» line, docstrings, and tests for the delete path, `drawn_by`/`drawn_at` and the missing line. Nothing deferred. The rest were rejected, each with its reason in the triage log.

**Follow-up review recommended: false.** The three mediums share two root causes, each pinned by a test (`test_once_locked_the_draft_is_read_but_never_drawn`, `test_a_redraw_after_every_student_left_removes_the_draft`); no high was found.

**Verification**
- Backend: 2462 passed in 62 s; ruff check and format clean. New tests each under 1 s, except the 0037 migration test (about 5 s under parallel load, like the other migration tests).
- Frontend: typecheck, Vitest (425), `check:copy`, `lint:colours` and `build` pass. Playwright 242/242 on the rebuilt stack; the new spec's 8 tests take about 9 s in parallel.
- Matrix audit: every I/O row has a passing test in `test_allocation.py`.
- Screenshots at 390 and 1280 px (scratchpad, not committed) checked against mockup 03: heading, lead, chart with the framed column, the game line and «Kjør fordeling på nytt» match; at 390 px the chart scrolls with a fade and the page does not.
- Migration 0037 is new and ran on the shared test databases; it was not changed after it ran.
- Implementation and review fixes were done in this context (caller's instruction), not by a step-03 subagent. The four reviewers were sub-agents.

**Decisions taken in place of the founder**
- The draw happens when a Lecturer opens the panel (the Lenke press), not when the page renders; reopening shows the stored draft. A redraw starts a new draft at revision 1.
- The chart and list put Fabrikk at the top (the story), not Detaljist as in mockup 03; the game line reads Detaljist to Fabrikk as in the story's example.
- An empty Seat is an outlined `paper` cell with an `ink-muted` border; the game line and the list name it «KI-spiller».
- `missing_count` and «N registrerte studenter er ikke med.» (plus «Kjør fordeling på nytt for å ta dem med.» for those who can draw) report Students registered after the draw; a removed Student shows «Ikke lenger i Klassen».
- Once locked, a stored draft is still shown, also to the Lecturer; drawing is refused (`session_locked`). Assistants read only.
- With nobody registered, a redraw removes a stale draft.
- [ASSUMPTION] copy: «Se fordelingen», «Ingen registrerte studenter å fordele ennå.», the lead (from mockup 03), «Visning», «Diagram», «Lukk», «Fordelingen er trukket på nytt.», the missing lines, «Ikke lenger i Klassen», the failure and locked lines. «Ingen får beskjed før du bekrefter.» already stands beside the redraw.
- Columns are narrow at mockup density (10 px at 100 games); the list view and the game line are the equivalent controls for touch (WCAG 2.5.8 exception).

**Residual risks**
- The allocation read is not refetched on `session:<id>`; a co-owner's redraw shows after a reload (Story 6.4 adds event refetch). Story 5.9's revision check guards the confirm.
- The 100-game, locked and Assistant screens are tested with stubbed api answers; the real behaviour is pinned at the api.
