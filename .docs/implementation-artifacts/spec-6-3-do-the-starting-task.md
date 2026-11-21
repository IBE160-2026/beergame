---
title: 'Story 6.3: Do the Starting task'
type: 'feature'
created: '2026-11-20'
status: 'done'
baseline_revision: '215ac1f3f145109a4d6576f589c4228a3f57782c'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-6-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-6-2-read-rules-before-first-order.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** After the briefing (6.2) a Student has no Startoppgave: «Jeg har lest reglene» returns to Hjem, nothing records `starting_task`, so `briefing_first` never turns false and the pre-play gate (FR-85, UX-DR63) cannot be passed. There is no `modules/content`, `modules/tests` or `analysis.scoring` either.

**Approach:** Create `modules/content` (immutable, versioned records; Starting task v1 = placeholder items, pinned by the lock through a registered pin provider), `analysis/scoring.py` (pure signed-sum rule), and `modules/tests` (one answers table + routes under `/api/me/games/{id}/starting-task`). The web app gets the Startoppgave at `/spill/{gameId}/startoppgave` with a reusable one-column item component; the briefing's button leads there; the final question records `progress` `starting_task`.

## Boundaries & Constraints

**Always:**
- `content_records(id, kind, version, body jsonb, created_at)`, unique `(kind, version)`, a trigger refuses UPDATE (immutable). `content.service`: `publish(kind, body)` validates and inserts version max+1; `get(kind, version)`; `latest_version(kind)`; `starting_task(version | None)` → validated `StartingTask` (None → latest). `kind` closed set: `starting_task`. Migration 0046 creates it and inserts v1 as a literal.
- `StartingTask` body: `items: list[Item]` (≥1, unique ids), `Item = {id, prompt, hint|None, column, rows: [{key, label, value:int}], asked_label, terms: [{row, sign: 1|-1}]}` — each `terms.row` names a row key; answer = Σ sign × value. v1 placeholders (Grossist, «Uke 11», the briefing's canonical column; all answers ≥ 0 because `inputmode="numeric"` has no minus on iOS): `to-ship` «Hvor mange enheter skal Grossisten sende i alt?» Restordre før 9 + Ordre inn 8 = 17; `backlog` «Regn restordren etter uka.» 9 + 8 − 4 (Sendt) = 13; `position` «Regn posisjonen for én Uke.» hint «Posisjon = Lager − Restordre + På vei» Lager 0 − Restordre 13 + På vei 16 = 3. Prompt copy lives in the content (Norwegian), draft.
- `sessions.service` registers pin provider `starting_task` → `content.service.latest_version("starting_task")` (an int). `lock`/`build_snapshot` code is not changed. A Student's version = the session snapshot's `session_runtime.pins.starting_task`, else latest (sessions locked before this story).
- `analysis/scoring.py`: pure `score_sum(terms: Sequence[tuple[int, int]], answer: int) -> SumScore(expected, correct)`; no I/O, no LLM.
- `modules/tests`: table `starting_task_answers(id, user_id, class_session_id, content_version, item_id, answer int null, correct bool null, choice text null, answered_at)`, unique `(user_id, class_session_id, item_id)`; an item row has answer+correct, the final row has `item_id = 'played_before'` and `choice ∈ yes|no|unknown|skipped`. Routes (policy `games.read_own` for GET, new `starting_task.answer_own` = ANY_USER for POST), all 403 `forbidden` for a game that is not the Student's own locked game (resolved by a new `sessions.service.own_game_session(user, game_id)` sharing `student_game_of`'s checks):
  - `GET /api/me/games/{id}/starting-task` → `StartingTaskOut {version, items[{id, prompt, hint, column, rows[{label,value}], asked_label, result|null}], played_before|null, done}`; `result = {answer, correct, expected, terms[{sign,value}]}` only for answered items (no answer key before).
  - `POST …/starting-task/answers {item_id, answer:int (−1 000 000..1 000 000)}` → `StartingTaskOut`; unknown item → 422 `unknown_item`; an item already answered keeps its first answer (stored once; repeat returns the state).
  - `POST …/starting-task/final {choice}` → `StartingTaskOut`; 409 `items_open` while an item is unanswered; stores the row and calls `progress.record_step(user, session, starting_task, now, within=s)` in the same transaction; repeat changes nothing. `done` = final row exists.
- No game-status check: a finished game with no Orders still offers the task.
- Web: `frontend/src/components/column-item.tsx` (one column table: caption, given rows, asked row with `TextField`-style input `inputMode="numeric"`, `restordre` border + `role="alert"` error, optional result line; Epic 11 reuses it without result). Page shows answered items in their result state, then the first unanswered with one primary button «Send svar»; validation on blur and press: not a whole number (letters, decimals, empty) → «Skriv et helt tall.»; accepts `−`/`-`. Feedback «Riktig. Svaret er 3: 0 − 13 + 16.» / «Ikke riktig. Svaret er 3: 0 − 13 + 16.» (words carry right/wrong; focus moves to the feedback). Then the final question (fieldset «Har du spilt et spill som ligner dette før?», radios Ja/Nei/Vet ikke, primary «Send svar», secondary «Hopp over»; no choice → «Velg et svar, eller hopp over.»). Done: «Ferdig. Gå til Uke 1.» and a primary link «Til Hjem». Lead says it counts toward nothing; «Demodata» label. Skjelett/error/403 as `briefing-page.tsx`. Copy in `nb.games.startingTask` (`[ASSUMPTION]` for drafts).
- Briefing primary «Jeg har lest reglene» → `/spill/{id}/startoppgave`.

**Never:** No LLM, no Start button or play screen (6.5/6.6), no SSE (6.4), no `games.policy` columns (6.18), no change to `lock`'s body, no client-side scoring or sum, no edit of `sprint-status.yaml`, no change to the demo Class.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| First open | seated, locked, nothing answered | 3 items, no `result`, `done: false` | — |
| Wrong | `position`, answer 5 | `result {correct:false, expected:3, terms:[+0,−13,+16]}` | — |
| Repeat | `position` again, answer 3 | first answer kept | — |
| Final early | item open | — | 409 `items_open` |
| Finish | all answered, `skipped` | `done: true`; `progress` `starting_task`; Hjem `briefing_first: false` | — |
| Resume | 1 answered, new device | state lists it answered; web shows item 2 | — |
| Version | session pinned v1, v2 published | still v1 | — |
| Not own | other/unknown/malformed id | — | 403 `forbidden` |
| Bad input | answer 1.5 / "x" / missing | — | 422 `invalid_request` |

</intent-contract>

## Code Map

- `backend/app/modules/sessions/service.py:1239` `student_game_of` -- extract checks into `own_game_session` (returns class session id + pinned version); `:2116` `register_pin_provider` -- register `starting_task` at module end. `repo.py` -- read `snapshot->session_runtime->pins->starting_task`.
- `backend/app/modules/progress/service.py` `record_step(..., within=)`.
- `backend/app/platform/authz.py:77` POLICIES -- add `starting_task.answer_own`.
- `backend/app/main.py` -- include `tests.routes.router`.
- `backend/migrations/versions/0045_progress_steps.py` -- pattern; new `0046_content_and_starting_task.py`.
- `backend/tests/test_imports.py` -- add: `content` imports no feature module; `analysis.scoring` no I/O imports.
- Tests: new `backend/tests/content/`, `backend/tests/starting_task/` (helpers from `tests/sessions/test_student_home.py`), `tests/analysis/test_scoring.py`; fold migration check into the migration walk test.
- `frontend/src/modules/games/{api.ts,briefing-page.tsx}`, `identity/homes.ts` (`startingTaskPath`), `copy/nb.ts`, `components/text-field.tsx` (pattern), `lib/number-format.ts` (format sums).
- E2E pattern: `frontend/e2e/briefing.spec.ts` (answers overlaid; a locked game needs the Start date).

## Tasks & Acceptance

**Execution:**
- `backend/app/modules/content/{__init__,models,schemas,service,README}.py/md` + `__main__.py` (`publish` from a JSON file) -- versioned records.
- `backend/app/analysis/scoring.py` -- `score_sum`.
- `backend/app/modules/tests/{__init__,models,schemas,service,routes,README}` -- table, routes.
- `backend/migrations/versions/0046_content_and_starting_task.py` -- tables, trigger, v1.
- `backend/app/modules/sessions/{service,repo}.py`, `platform/authz.py`, `main.py` -- wiring.
- Backend tests for every matrix row, publish/immutability, pin at lock, scoring.
- Frontend: regenerate api; `column-item.tsx` (+ component test); `starting-task.ts` (+ tests: parse, sum text); `starting-task-page.tsx`, route, api hooks, copy, briefing button; `e2e/starting-task.spec.ts` (states wrong, right, final, done at 320/360/1440 with axe; keyboard-only flow; error on blur).

**Acceptance Criteria:**
- Given the Startoppgave, when an answer is not a whole number and the field is left or the button pressed, then «Skriv et helt tall.» shows with the `restordre` border and `role="alert"`.
- Given a sent answer, when scored, then the result comes from `analysis.scoring` and reads «Riktig.»/«Ikke riktig.» with «Svaret er N: sum» in text.
- Given the final question answered or skipped, then Hjem shows the Lenke «Regler før første ordre» and the screen reads «Ferdig. Gå til Uke 1.»
- Given Playwright with axe at 320, 360, 1440 px, when the wrong, right, final-question and done states render, then no page-level horizontal scroll and no axe violation.

## Spec Change Log

## Review Triage Log

### 2026-11-20 — Review pass
- verdicts: 55 findings — high 0, medium 6, low 41, false 8, maybe-false 0
- findings:
  - `[low]` `[patch]` blind: client accepted 7 digits, api ±1 000 000. `parseWholeNumber` now refuses past ±1 000 000 (tested).
  - `[low]` `[patch]` blind: content could hold a right answer past the api's bound (12 × 100 000). `ColumnRow.value` is now ±80 000 (tested).
  - `[low]` `[reject]` blind: old versions validated against today's schema. No later schema exists yet; the fix is per-version schemas, more than a direct correction.
  - `[low]` `[reject]` blind: missing content → lock refused / 500. v1 is stored by the migration and no product path deletes records; not met in use.
  - `[false]` `[reject]` blind: concurrent finish records the step twice. `progress.record_step` is idempotent (`on_conflict_do_nothing` on `uq_progress_steps_step`).
  - `[low]` `[reject]` blind: ownership read outside the write transaction. A Student removed in the same instant could store one answer; harmless, and a lock adds complexity.
  - `[low]` `[patch]` blind: `pinned_version` took `True`. Now `type(version) is int and version >= 1` (tested with True, 0, "2", 1.0).
  - `[low]` `[reject]` blind: CLI tracebacks, no happy-path test. A five-line operator tool; `publish` itself is tested; a traceback is an acceptable failure for it.
  - `[low]` `[patch]` blind: row label as React key. Now the row index.
  - `[low]` `[patch]` blind: e2e docstring said the stand-in is version 1. Now «two of the migration's version 1 items».
  - `[low]` `[patch]` blind: unused copy `rowHeader`, `valueHeader`, `yourAnswer`. Removed.
  - `[medium]` `[patch]` blind: done line «Ferdig. Gå til Uke 1.» vs button «Til Hjem». Group "done line": added «Spillet starter fra Hjem.» under it until Story 6.5 (e2e asserts it).
  - `[medium]` `[patch]` blind: Hjem's cache not refreshed after done. Group "Hjem cache": `enrolledSessionsKey` is invalidated too; a new e2e goes Hjem → briefing → Startoppgave → done → Hjem by in-app navigation and asserts the Lenke replaces «Les reglene».
  - `[false]` `[reject]` blind: `GuardedPage page="home"` wrong. The briefing page uses the same guard; these are Student pages under Hjem.
  - `[low]` `[patch]` blind: unused `code` attributes on the two errors. Removed.
  - `[low]` `[patch]` blind: test gaps. `played_before` sent to `/answers` is now asserted `unknown_item`; finished game grouped with verification-gap 2; concurrency, leaving the Class and per-object downgrade rejected (idempotent inserts, 6.1's own-game tests, the migration walk).
  - `[low]` `[patch]` blind: needless JSON round-trip in migration 0046. Removed (stored data identical).
  - `[low]` `[reject]` edge: lock with no content row. As blind 4.
  - `[low]` `[reject]` edge: missing pinned version → 500. As blind 4.
  - `[low]` `[reject]` edge: two first answers around a publish on a pre-pin session. Needs a pre-story lock, two concurrent first answers and a publish at once; each answer is still scored right.
  - `[low]` `[reject]` edge: old bodies under a new schema. As blind 3.
  - `[low]` `[reject]` edge: a `Kind` without a schema gives `KeyError`. A developer error that fails loudly at once.
  - `[low]` `[reject]` edge: CLI tracebacks. As blind 8.
  - `[low]` `[patch]` edge: pin `True`/0. Same patch as blind 7.
  - `[low]` `[patch]` edge: 7-digit answers. Same patch as blind 1.
  - `[low]` `[patch]` edge: duplicate row labels as keys. Same patch as blind 9.
  - `[low]` `[patch]` edge: «−0» when the first term is a subtracted 0. `sumText` writes «0» (tested).
  - `[medium]` `[patch]` edge: Hjem cache after done. Group "Hjem cache".
  - `[medium]` `[patch]` edge (claim): Hjem keeps «Les reglene» for 30 s. Group "Hjem cache".
  - `[low]` `[patch]` verification-gap: no test that Hjem drops `briefing_first` after done. Group "Hjem cache" (new e2e).
  - `[low]` `[patch]` verification-gap: finished game not tested. `test_a_finished_game_with_no_orders_still_offers_the_starting_task` stores a finished Week row and runs GET, answers and final; `briefing_first` holds until done.
  - `[low]` `[reject]` verification-gap: CLI publish path untested. As blind 8.
  - `[false]` `[reject]` verification-gap (other): the working tree already invalidates `enrolledSessionsKey`. True; now also tested.
  - `[low]` `[patch]` intent: Hjem for an ended game untested. Covered by the finished-game api test; Hjem's button reads only `briefing_first` (6.2's e2e).
  - `[low]` `[reject]` intent: e2e uses a stand-in api. Repo pattern (6.1, 6.2): a locked game needs the Start date; the api is pinned by pytest against real data.
  - `[low]` `[reject]` intent: UI resume tested on stand-in state only. Same reason; the api's resume is tested.
  - `[low]` `[reject]` intent: result line under the table, not inside it (R2). It sits directly under its own column; a sentence in a cell would not reflow at 320 px; the visual reviewer accepted it.
  - `[medium]` `[patch]` intent: «Gå til Uke 1» vs Hjem. Group "done line".
  - `[low]` `[reject]` intent: no copy says it works by keyboard alone. Read as a behaviour (keyboard-only e2e).
  - `[low]` `[patch]` intent: content prompts escape the copy check. `StartingTaskItem` now refuses «Beer Game», «bullwhip» and «!» (tested).
  - `[false]` `[reject]` intent: locked sessions keep v1 (R10). AD-23 pins at the lock; new versions reach sessions locked later.
  - `[false]` `[reject]` intent: optional only in the UI (R6). All four answers exist; «Hopp over» sends `skipped`.
  - `[false]` `[reject]` intent: one row per item (R4). Each row stored once per Student and session, as the story says.
  - `[false]` `[reject]` intent: sessions module changed (R9). The lock function is unchanged; the provider goes through the open map.
  - `[low]` `[patch]` visual: the Student's answer looked like a given cell. It now sits in a read-only box (`future-tint`, `axis` border).
  - `[medium]` `[patch]` visual: done text vs button. Group "done line".
  - `[low]` `[reject]` visual: «Til Hjem» between h1 and lead, twice when done. The shared Student page pattern; the done button is the screen's one primary action.
  - `[low]` `[reject]` visual: error after the hint. Same order as the shared `TextField`.
  - `[low]` `[patch]` visual: the choice wider than the column at 1440 px. Capped at `max-w-xs`.
  - `[low]` `[reject]` visual: «Svaret er frivillig.» after the choices. Tied by `aria-describedby`; moving it needs a change to the shared `SegmentedChoice`.
  - `[low]` `[reject]` visual: final question weaker hierarchy. A fieldset with legend after a 40 px gap; an h2 would repeat it.
  - `[low]` `[reject]` visual: placeholder prompts inconsistent. Placeholders, replaced by issue #16 as a new version; changing them changes a migration that has run.
  - `[low]` `[patch]` visual: «teller ikke på noe» colloquial. Now «Oppgaven teller ikke, og du går videre uansett hva du svarer.»
  - `[low]` `[reject]` visual: «Demodata» per item. It sits under each column, as DESIGN.md's `demo-label`.
  - `[false]` `[reject]` visual: layout deviates from the mockup acceptably. No change asked.

All five reviewers (blind, edge case, verification gap, intent alignment, and a visual reviewer standing in for the founder's eye) finished; their reports were read from their transcripts because their completion notices did not arrive.

## Design Notes

Founder-level decisions: items are linear signed sums over the column's rows (covers Posisjon, Netto lager, Restordre; new content can add items without code); placeholder answers kept non-negative for phone keypads; answer key hidden until answered; first answer kept (stored once); «Hopp over» stored as `skipped` and also finishes; done screen's button leads to Hjem until 6.5; version from the lock's pin, latest for older locks; route `/spill/{id}/startoppgave`.

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/content tests/starting_task tests/analysis -q` -- pass
- `cd backend && uv run pytest -q && uv run ruff check . && uv run ruff format --check .` -- pass
- `cd frontend && npm run typecheck && npm test && npm run check:copy && npm run build && npx playwright test --workers=2` -- pass

## Auto Run Result

Status: done

**Summary.** A seated Student goes Hjem «Les reglene» → briefing «Jeg har lest reglene» → Startoppgave at `/spill/{gameId}/startoppgave`. Each item is one column of the week table (Demodata) with an asked row answered by a whole number (`inputmode="numeric"`; «Skriv et helt tall.» with the `restordre` border and `role="alert"` on blur or press). The api scores each answer once with `analysis.scoring.score_sum` (no LLM); the line under the column reads «Riktig. Svaret er 3: 0 − 13 + 16.» or «Ikke riktig. …», and the Student goes on either way. After the last item the optional «Har du spilt et spill som ligner dette før?» (Ja/Nei/Vet ikke, «Hopp over») records `progress` `starting_task` and shows «Ferdig. Gå til Uke 1.», «Spillet starter fra Hjem.» and «Til Hjem»; Hjem then shows the Lenke «Regler før første ordre». The task resumes at the first unanswered item on any device and stays offered for a finished game.
- **content:** `content_records` (immutable by trigger), `publish`/`get`/`latest_version`, Starting task v1 placeholders (to-ship 17, backlog 13, position 3) stored by migration 0046, CLI `python -m app.modules.content`. The lock pins `{"version": N}` through a registered pin provider; the lock function is unchanged.
- **tests module:** `starting_task_answers`; `GET /api/me/games/{id}/starting-task`, `POST …/answers`, `POST …/final`; 403 for any game that is not the Student's own locked game (`sessions.service.own_game_session`).

**Files.**
- `backend/app/modules/content/*` (new) -- versioned content, schemas (with a pre-Debrief word check), pin provider, CLI, README.
- `backend/app/modules/tests/*` (new) -- answers table, service, routes, README.
- `backend/app/analysis/scoring.py` (new), `analysis/__init__.py` -- `score_sum`.
- `backend/migrations/versions/0046_content_and_starting_task.py` (new), `migrations/env.py` -- tables, trigger, v1.
- `backend/app/modules/sessions/{service,repo}.py`, `README.md` -- `own_game_session`, `_own_locked_game`, `session_pins`, provider registration.
- `backend/app/platform/authz.py` (`starting_task.answer_own`), `backend/app/main.py` (router).
- Tests: `backend/tests/{content,starting_task}/` (new), `tests/analysis/test_scoring.py` (new), `test_migrations.py` (walk, check constraints), `test_imports.py`, `sessions/test_lock.py` (pin).
- `frontend/src/components/column-item.tsx` (new, for reuse by Epic 11) + `components.test.tsx`.
- `frontend/src/modules/games/{starting-task.ts,starting-task.test.ts,starting-task-page.tsx}` (new), `api.ts`, `briefing-page.tsx` (button → Startoppgave), `identity/homes.ts`, route `app/(app)/spill/[gameId]/startoppgave/page.tsx`, `copy/nb.ts` (`games.startingTask`).
- `frontend/src/lib/api/{openapi.json,schema.ts}` -- regenerated.
- `frontend/e2e/starting-task.spec.ts` (new), `briefing.spec.ts` (button target).

**Review.** One pass, 55 findings (high 0, medium 6, low 41, false 8): two medium entry groups patched ("Hjem cache" with a new e2e; "done line"), 16 low entries patched, nothing deferred, the rest rejected with reasons in the triage log. Patched counts by entry verdict: high 0, medium 2, low 16.

**Follow-up review:** false. No high was patched and both medium groups are covered by new assertions; the implementation was not re-reviewed after the patches, which were small and verified by the full suites.

**Founder-level decisions taken (no human in the loop).** Items are linear signed sums over the column's rows; placeholder items to-ship/backlog/position with non-negative answers (phone number pads lack a minus); the answer key is sent only after an answer; the first answer is kept; «Hopp over» is stored as `skipped` and finishes the task; api under `/api/me/games/{id}/starting-task`, page `/spill/{id}/startoppgave`; the version comes from the lock's pin (latest for sessions locked earlier) and a Student stays on the version they began with; the done screen adds «Spillet starter fra Hjem.» and leads to Hjem until Story 6.5; the Student's own number sits in a read-only box; content refuses «Beer Game», «bullwhip» and «!»; all new copy is drafted for review. The implementation ran in the orchestrating agent's own context (caller's runbook), not in a separate implementation subagent.

**Verification.**
- Backend: 2628 passed (90 s); ruff check and format clean. New tests under 1 s except `test_a_student_answers_each_item_once_and_finishes` (about 1.1 s, one full api flow).
- Frontend: typecheck, Vitest 480 passed, `check:copy`, build; compose stack rebuilt; Playwright full run `--workers=2`: 305 passed (6.2 min).
- Migration 0046 is new. It ran on the shared test databases and was then edited only to drop a no-op JSON round-trip; the stored data is identical.

**Residual risks.** Draft copy and placeholder items await the founder (issues #31, #16). The e2e answers come from a stand-in (a locked game needs the Start date); the api is pinned by pytest. No Start button yet (6.5).
