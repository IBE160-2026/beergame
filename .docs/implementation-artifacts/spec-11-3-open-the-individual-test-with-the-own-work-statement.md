---
title: 'Story 11.3: Open the Individual test with the own-work statement'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: 'ec1fcb1f73cbc2e1a45fd9edc6a07b4b2d7a7adc'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-11-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** A Student who has completed the Replay has no way into the Individual test: no attempt record, no own-work statement, no page, and Stegene's current test step leads nowhere (FR-51, FR-45, AD-9, AD-10, AD-12, AD-16, AD-23, UX-DR65).

**Approach:** `modules/tests` gets the attempt write path (`tests/commands.py`, the only writer of `test_attempts` and `test_answers`, migration 0123) with `open_attempt`; a Student-facing api `GET`/`POST /api/me/class-sessions/{id}/test` gated by `progress.has_step(…, replay)`; and a page `/individuell-test/[sessionId]` showing locked, statement, open and closed states, linked from Stegene's current test step.

## Boundaries & Constraints

**Always:** Gate only through `progress.has_step(user, session, replay)`; the session must be the Student's own locked Class session (`sessions.enrolled_locked_row`), every other caller (other Students, Lecturers, Admin without membership, unknown/malformed ids) gets the same 403 `forbidden` whether or not an attempt exists. `GET` answers `{state: statement|open|closed, test_deadline, opened_at, items}`; `items` is empty unless `open` (no item served before the statement is accepted). `POST` (accepting the statement) runs `commands.open_attempt` in one transaction holding the Class session row share-locked: refuses 409 `test_deadline_passed` once `sessions.effective_test_deadline` ≤ now (none set = no deadline), else inserts one `test_attempts` row (`statement_accepted_at`, `question_set_version`, `selection` JSON, frozen ordered `items` = the selection's Core items left in, in question-set order, each `{id, type, weight}`, `effective_deadline`, status `open`) with `ON CONFLICT (user_id, class_session_id) DO NOTHING` and returns the existing row on conflict (201 new / 200 existing); calls `debrief.service.close_follow_up(…, within=s)` in the same transaction; emits `user:<id>` (registry `tests.open_attempt`). Selection = the lock's pin (`selection.pinned_selection(pins)`), else `selection.effective` at open. A returning Student (`open`) never sees the statement again. Closed = no attempt and the deadline passed. A change of the Class session's Test deadline moves `effective_deadline` of its `open` attempts in the save transaction (a registered `sessions.register_test_deadline_mover`; sessions never imports tests). README + `commands.py` docstring record the write path: commands `open_attempt` (here), `save_answer` (11.4), `submit` (11.10), `close_attempt` (11.11), `extend_deadline` (11.13), `end_sitting` (11.12); `SELECT … FOR UPDATE` on the attempt row for every command on an existing attempt, one transaction; `attempt_submitted` / `test_deadline_passed` codes; `open_attempt` relies on the unique key; `extend_deadline` locks the extension row (and attempt). Copy in `nb.ts` under `tests.individual`, spine strings exact, the rest `[ASSUMPTION]`. Loading uses Skjelett via `PageShell` phase. Authz action `tests.take_own` (ANY_USER, held to the scoped query).

**Never:** No answering, autosave, scoring, submit, sweep close, timed sitting or extension (later stories); no Adapted items (11.7); no weights or answer keys sent to the Student; no answer text in logs; no change to the demo Class; no edit of `sprint-status.yaml`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| No Replay | own locked session, no `replay` step | Hjem test step locked line; page shows locked line | GET/POST 403 `replay_required` |
| Statement | `replay` step, no attempt, deadline ahead | `state=statement`, `items=[]` | — |
| Accept | POST | 201, one row, `state=open`, items in order, follow-up closed, `user` emitted | — |
| Again / race | second POST, two at once | 200 same attempt id; one row | — |
| Return | GET with attempt | `open`, items, `opened_at` | — |
| Deadline | no attempt, deadline passed | GET `closed`, POST nothing stored | 409 `test_deadline_passed` |
| Other caller | other Student / Admin / Lecturer / bad id | nothing revealed | 403 `forbidden` |
| Excluded item | selection excludes an item | item absent from frozen list | — |
| Deadline moved | owner moves Test deadline after open | open attempt's `effective_deadline` follows | — |

</intent-contract>

## Code Map

- `backend/migrations/versions/0123_test_attempts.py` (new; Revises 0122) -- `test_attempts` (id uuid PK; user_id FK users CASCADE; class_session_id FK class_sessions CASCADE; question_set_version int ≥1; selection jsonb; items jsonb; statement_accepted_at; effective_deadline null; status text check open|submitted|auto_submitted default open; submitted_at null; sitting_ends_at null; unique (user_id, class_session_id) `uq_test_attempts_user_session`), `test_answers` (id; attempt_id FK CASCADE; item_id text; value jsonb; revision int ≥1; saved_at; unique (attempt_id, item_id)).
- `backend/app/modules/tests/models.py` -- the two Tables + `AttemptStatus`.
- `backend/app/modules/tests/commands.py` (new) -- write-path docstring, `open_attempt(user, class_session_id, now) -> (row, created)`, `DeadlinePassed`, `move_deadline` (the registered mover).
- `backend/app/modules/tests/attempt.py` (new) -- `read(user, id, now)`, `open_(user, id, now)`, `ReplayRequired`; `_out` → `MyTestOut`.
- `backend/app/modules/tests/selection.py` -- reuse `pinned_selection`, `effective`.
- `backend/app/modules/tests/{schemas,routes}.py`, `README.md` -- `MyTestOut`, `TestItemOut`; routes `getMyTest`, `openMyTest`.
- `backend/app/modules/sessions/service.py` -- `test_session_of(s, user, id)` (enrolled_locked_row + share lock + pins, pattern `replay_session_of` ~1674); `register_test_deadline_mover` called after `repo.save` (~1155) when `test_deadline` in `changed`.
- `backend/app/modules/debrief/{commands,service}.py` (~1271, ~1104) -- `close_follow_up(..., within=None)`.
- `backend/app/platform/authz.py` (~128), `platform/events/registry.py` (~162) -- `tests.take_own`, `tests.open_attempt: {user}`.
- `backend/app/modules/replay/dev.py` -- dev route `POST /api/dev/class-sessions/{id}/replay-done` (steps through `replay`) for e2e.
- Tests: `backend/tests/individual_test/test_open.py` (new; fixtures as `tests/replay/test_start.py`: `confirmed`, `sweep.run(START+MINUTE)`, `progress.record_step`), `tests/test_migrations.py` (head 0123).
- Frontend: `src/modules/tests/{individual-test-page.tsx,individual-test.ts,individual-test.test.ts}` (new), `api.ts` (`useMyTest`, `openMyTest`, key `["tests","mine",id]`), `app/(app)/individuell-test/[sessionId]/page.tsx` (pattern debrief route), `modules/identity/homes.ts` (`TEST_PATH`), `modules/games/home.ts` `stepHref` (test → TEST_PATH), `lib/api/topics.ts` (`user` → `["tests","mine"]`), `copy/nb.ts`, `npm run api:generate`.
- e2e: `frontend/e2e/individual-test.spec.ts` (new): stand-ins for locked/statement/open/closed at 320/360/1440 with axe and reflow; one live test (`liveClassGame`, dev `replay-done`, Hjem link → statement → accept → items, reload keeps open).

## Tasks & Acceptance

**Execution:**
- Migration + models + commands + attempt service + schemas + routes + README -- tables, write path, api.
- sessions/debrief/authz/registry/dev hooks -- as mapped.
- Backend tests -- every matrix row, race (gather), emitted topics, follow-up closed (`debrief.follow_up.closed`), head 0123.
- Frontend page, api, Stegene link, copy, Vitest of the view logic; e2e as mapped.

**Acceptance Criteria:**
- Given the statement state, then the page shows the own-work statement and one primary button «Bekreft og åpne testen», and no item.
- Given the Student accepts, then the items show numbered («Oppgave 1») with their type, focus moves to the heading, and a reload or another device shows them without the statement.
- Given 320 px, then one column without sideways scroll, and axe passes at 320/360/1440 for locked, statement, open and closed.

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
Layers: blind hunter, edge-case hunter, verification gap and intent alignment (sonnet; four per the runbook, since the change adds a data model, access rules, a race and a deadline). Generated `openapi.json`/`schema.ts` left out of the review diff.
- verdicts: 36 findings — high 0, medium 0, low 24, false 12, maybe-false 0
- findings:
  - `[low]` `[patch]` Blind: `debrief_follow_up_closed` was logged inside the transaction, before commit — the standalone path now logs after its commit; within `open_attempt` the open's own log line carries `follow_up_closed`.
  - `[low]` `[patch]` Blind: `user:<id>` emitted twice per open (closure and open) — `open_attempt` emits only when the closure did not; the test asserts exactly one event.
  - `[false]` `[reject]` Blind: a moved Test deadline emits nothing — `sessions.save` emits `user:<id>` per registered Student when a date changes, and the `user` topic now reads `["tests","mine"]` again.
  - `[low]` `[reject]` Blind: `move_deadline` writes the Class deadline rather than computing `effective_test_deadline` — equal until 11.13 adds extensions; the rule is in the README and the command's docstring for 11.13; computing per attempt now adds code for a case that does not exist.
  - `[low]` `[reject]` Blind: the mover is registered by import — the only process that saves a session (the api) imports `tests.routes` → `attempt` → `commands`; same registration pattern as 11.1 and 11.2; the moved-deadline test proves it in the app.
  - `[low]` `[reject]` Blind: GET takes `FOR SHARE` on the Class session row — a short read transaction; a lock-free variant needs a second accessor for no measurable gain.
  - `[false]` `[reject]` Blind: `titles[item["id"]]` KeyError — the frozen ids are taken from that same immutable question set version, and no content record is ever deleted.
  - `[low]` `[reject]` Blind: an attempt past its deadline still reads `open` — closing at the Test deadline is Story 11.11 (`close_attempt`); nothing can be answered yet.
  - `[low]` `[patch]` Blind: test gaps — added the pre-pin fallback, a cross-session and submitted-attempt mover test, a deterministic lost-race test and a post-deadline re-open; the other listed gaps (unlocked session, other Class, rollback, dev route) are covered by the shared `enrolled_locked_row` tests or are dev-only.
  - `[low]` `[reject]` Blind: test hygiene (`__all__` fixture re-exports, positional rows) — the repo's established pattern (11.2, 10.3).
  - `[low]` `[reject]` Blind: copy promises autosave before 11.4, and lines repeat between `tests.individual` and `homes.student.locked` — FR-51's behaviour, which the epic ships together; the repeated spine sentence is checked by Vitest and e2e against both keys.
  - `[low]` `[reject]` Blind: `assert attempt is not None` and the `DeadlinePassed` name — under READ COMMITTED the conflict's winner is committed and visible to the next statement; the class lives in `tests.commands` and is always qualified.
  - `[false]` `[reject]` Blind: `test_answers`, `submitted_at`, `sitting_ends_at` unused — the story's AC says the tables are created in this story; the columns are the ones the epic context lists.
  - `[low]` `[reject]` Blind: e2e uses stand-ins, a date regex, and no live 409/follow-up/second device — the backend tests carry those; the repo's pattern is stand-ins per width plus one live test.
  - `[false]` `[reject]` Edge: a submitted attempt is served as `open` — no code can set another status before 11.10/11.11, which own that state.
  - `[false]` `[reject]` Edge: every Core item excluded gives an empty list — `selection._judge` refuses taking every Core item out (422 `validation_error`, `excluded: all`).
  - `[false]` `[reject]` Edge: KeyError/ContentNotFound in `_items` — same refutation as the Blind row.
  - `[low]` `[reject]` Edge: mover registration by import — same as the Blind row.
  - `[low]` `[patch]` Edge: log before commit — same fix as the Blind row.
  - `[false]` `[reject]` Edge: `assert` fails under stricter isolation — the app runs READ COMMITTED (SQLAlchemy/Postgres default); nothing sets another level.
  - `[false]` `[reject]` Edge: moving the deadline reopens a passed attempt — a passed Test deadline cannot be changed (`judge_dates` refuses passed dates), and without extensions the stored deadline is the Class's.
  - `[low]` `[patch]` Verification: the mover was tested with one attempt in one session — test now holds a second Class session and a submitted attempt, both untouched.
  - `[low]` `[patch]` Verification: the gather race does not force the conflict branch — new test makes `attempt_of` read nothing once; the conflict path answers 200 with the first attempt, one row.
  - `[low]` `[patch]` Verification: POST after the deadline with an attempt was untested — asserted 200.
  - `[low]` `[patch]` Verification: the pre-pin fallback was untested — new test deletes the pin and checks version, items and weights against the selection in force.
  - `[low]` `[reject]` Verification: no backend test of the dev route `replay-done` — dev-only, never mounted in production, exercised by the live e2e.
  - `[false]` `[reject]` Verification: stand-in e2e not checked against the real shape — the reviewer files no defect; the live test runs on the real api and the types come from the generated client.
  - `[low]` `[patch]` Intent: Hjem's locked line was checked at data level only — the live e2e now reads it on Hjem (no link) before the Replay; this surfaced the Stegene link's tap target under 44 px (`replay-finish.spec`), fixed in `components/stegene.tsx` with padding taken back by a negative margin.
  - `[low]` `[reject]` Intent: viewport/axe runs use stand-ins — the repo's pattern; one live test covers the real stack.
  - `[low]` `[reject]` Intent: the follow-up refusal is shown through `follow_up.closed`, not the ask route — that predicate is what the ask refuses on (`test_follow_up.py` proves the 409); the ask needs a played game and an LLM mock.
  - `[low]` `[reject]` Intent: no rollback test for the shared transaction — `within=s` is one session; forcing a mid-transaction failure adds test-only hooks.
  - `[false]` `[reject]` Intent: `FOR UPDATE` only in prose — the commands that act on an existing attempt arrive in 11.4–11.13; the story asks for the decision recorded.
  - `[low]` `[reject]` Intent: a second device receiving the event is not exercised — the `user` topic mapping is unit-tested and the reload path is live-tested.
  - `[false]` `[reject]` Intent: the policy is a pass-through — `ANY_USER` plus the scoped query is the repo's pattern for own-resource actions (`debriefs.own`, `starting_task.answer_own`).
  - `[low]` `[reject]` Intent: scope additions (closed state, mover, dev route) — the closed state is EXPERIENCE.md's, the mover keeps AD-9's stored deadline true, the dev route serves the required live test.
  - `[false]` `[reject]` Intent: generated clients outside the diff — they are regenerated in the tree and committed.

## Design Notes

- Table named `test_answers`, not `answers`: the module prefixes its tables, and `answers` would sit ambiguously beside `starting_task_answers` and `debrief_reflection_answers`.
- `effective_deadline` is stored (AD-9 sweep reads ids and stored deadlines); the mover keeps it equal to `effective_test_deadline` until 11.13 adds per-Student extensions, which must skip extended Students.

## Verification

**Commands:**
- `uv run pytest tests/individual_test tests/debrief/test_follow_up.py tests/sessions tests/test_migrations.py tests/test_imports.py tests/test_authz_rules.py` -- pass
- `npm run typecheck && npm run test && npm run lint:colours && npm run check:copy && npm run build` -- pass
- `npx playwright test e2e/individual-test.spec.ts e2e/homes.spec.ts --workers=4` -- pass

## Auto Run Result

Status: done

**Summary.** A Student who has the `replay` step opens the Individual test at `/individuell-test/{sessionId}`, reached from Stegene's current test step. The page shows the own-work statement «Eget arbeid» first, with one primary «Bekreft og åpne testen»; the api serves no item before it is accepted. Accepting runs `tests.commands.open_attempt`: one `test_attempts` row (unique per Student and Class session) with the acceptance time, the question set version and selection the Start-date lock pinned, the frozen ordered item list (Core items left in, with type and weight), `effective_deadline` from `sessions.effective_test_deadline` and status `open`. The Student's Debrief follow-up closes in the same transaction. A second open (another device, or two at once) returns the same attempt, and the statement is not asked again. Before the Replay the api answers 403 `replay_required` and the page shows the spine's lock line. After the Testfrist with no attempt the page reads «Testfristen er passert. Testen er ikke levert.» and an open is refused with 409 `test_deadline_passed`. Every other caller gets 403 `forbidden`, whether or not an attempt exists. The write-path decision (commands, row lock, error codes, the named lock where no row exists) is in `commands.py` and the README. A change of the Class session's Test deadline moves open attempts' stored deadline in the same save.

**Files.**
- `backend/migrations/versions/0123_test_attempts.py` (new): `test_attempts`, `test_answers`.
- `backend/app/modules/tests/{models,schemas,routes}.py`, `README.md`; new `commands.py` (write path, `open_attempt`, `move_deadline`) and `attempt.py` (the page's read and open).
- `backend/app/modules/sessions/service.py`: `individual_test_session_of`, `register_test_deadline_mover` (called in `save_session`).
- `backend/app/modules/debrief/{commands,service}.py`: `close_follow_up(..., within=)`.
- `backend/app/platform/authz.py` (`tests.take_own`), `platform/events/registry.py` (`tests.open_attempt`), `modules/replay/dev.py` (dev `replay-done`).
- Tests: `backend/tests/individual_test/test_open.py` (new, 8 tests), `tests/test_migrations.py` (head 0123).
- Frontend: `src/modules/tests/{individual-test-page.tsx,individual-test.ts,individual-test.test.ts}` (new), `api.ts`; `src/app/(app)/individuell-test/[sessionId]/page.tsx` (new); `modules/identity/homes.ts` (`TEST_PATH`), `modules/games/home.ts` (test step link), `lib/api/topics.ts`, `copy/nb.ts` (`tests.individual`), `components/stegene.tsx` (44 px tap target on the step link); generated `lib/api/{openapi.json,schema.ts}`.
- e2e: `frontend/e2e/individual-test.spec.ts` (new).

**Review.** Four sonnet reviewers, 36 findings: high 0, medium 0, low 24, false 12. Patched 10 low rows: the closure's log line after commit, one `user` event per open, five added or sharpened tests (mover across sessions and on a submitted attempt, a deterministic lost race, a post-deadline re-open, the pre-pin fallback), and Hjem's locked line read live (which surfaced the Stegene link's tap target, fixed). Rejected: 14 low and 12 false findings, each with its reason in the triage log. Nothing deferred.

**Follow-up review: not recommended.** No high or medium entry was patched (patched: high 0, medium 0, low 10).

**Verification.**
- Backend: full suite with `--maxprocesses=8`: 3233 passed, 4 skipped. `ruff check` and `ruff format --check` clean. The new tests run 0.9–1.7 s each under the parallel load (`test_a_moved_test_deadline_moves_open_attempts` 1.73 s: two Class sessions, a lock and a save); these are over 1 s.
- Frontend: `tsc` clean, Vitest 1056 passed, `lint:colours`, `check:copy` and `next build` pass.
- Playwright on lane 2 (8081), 122 passed: individual-test (new; locked, statement, open, closed at 320/360/1440 with axe, a refusal, the denied page, one live test), homes, student-home, replay-finish/close/play/start, debrief-open/group, order-confirm, order-field, week-table, game-start, guided-week.
- Screenshots at 320 and 1440 of the statement and open states, checked by eye: one column, no sideways scroll, one primary.

**Decisions taken for the founder.**
- The answers table is `test_answers`, not `answers` (the module prefixes its tables).
- The page lives at `/individuell-test/{sessionId}`; the api at `GET`/`POST /api/me/class-sessions/{id}/test`.
- A stored `effective_deadline` follows a changed Class-session Test deadline for open attempts (registered mover); 11.13 must leave extended Students out.
- After the Testfrist with no attempt the page says «Testfristen er passert. Testen er ikke levert.» (the spine's line) rather than the statement.
- The open test lists each item as «Oppgave n», its type in words (Flervalg, Fyll inn kolonnen, Tallsvar, Langsvar) and its text; answering comes with 11.4–11.6.
- The own-work statement text, its button «Bekreft og åpne testen», «Tallsvar» and the other non-spine lines are [ASSUMPTION] draft copy.
- The Stegene step link got a 44 px tap target (padding with a negative margin, layout unchanged).

**Personal data.** `test_attempts` (`user_id`) and `test_answers` (text a Student writes, from 11.4) must be listed in Story 15.2's registry at merge.

**Residual risks.**
- An attempt whose deadline has passed still reads `open` until Story 11.11 closes it.
- The implementation was done in the main context, not a subagent, per the team lead's brief.
