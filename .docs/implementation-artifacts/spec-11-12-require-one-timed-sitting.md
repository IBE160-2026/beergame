---
title: 'Story 11.12: Require one timed sitting'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: '42bb8aecf1042bce3176e2945806e97cb981b8f6'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-11-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-11-11-have-saved-answers-submitted-automatically-at-the-test-deadline.md'
  - '{project-root}/.docs/implementation-artifacts/spec-12-1-switch-the-ai-assessment-off-for-a-class-session.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** A Lecturer cannot require the Individual test to be taken in one bounded sitting: every attempt stays open until the Test deadline, with no time limit, no clock for the Student and nothing that hands a timed attempt in when its time is up (FR-51, FR-17, AD-9).

**Approach:** A tests-owned per-Class-session setting (minutes, or none) is sent with «Lagre Klasseøkt» and stored through `tests.service` (registered with `sessions`, which never imports `tests`), read-only once the session is locked. `open_attempt` sets `sitting_ends_at` (limit × the Student's time factor); `tests.rules.answering_ends_at` gates `save_answer`/`submit`; a new sweep action `tests.end_sitting` auto-submits an open attempt whose sitting has ended before its deadline, without closing it. The statement names the limit, the open test shows «Tid igjen N min» fixed at the top.

## Boundaries & Constraints

**Always:**
- Migration `0129_test_sittings.py`: table `test_sittings` (`class_session_id` PK FK `class_sessions` CASCADE, `minutes INT NOT NULL CHECK minutes > 0`, `updated_by` FK `users` SET NULL, `updated_at`). Row present = timed; no row = off. Partial index on `test_attempts.sitting_ends_at WHERE status = 'open' AND sitting_ends_at IS NOT NULL`.
- Range is configuration: `Settings.test_sitting_min_minutes = 15`, `test_sitting_max_minutes = 240` (PLACEHOLDERS). Out of range, or not a whole number → 422 `invalid_session_values`, `{"test_sitting_minutes": "out_of_range"}`; a changed value once `is_locked` → 409 `session_locked` `{"test_sitting": "locked"}` [ASSUMPTION: locked with the question set]. Unchanged resend is never judged.
- Save body `test_sitting: {"minutes": int | null} | absent` (absent keeps; null switches off). `ClassSessionOut.test_sitting = {minutes, min_minutes, max_minutes, can_change}` (`can_change` = may manage, not archived, not locked). Assistant lecturers read it as text.
- `sessions.register_test_sitting(read, write)`; `save_session` judges and writes inside its transaction before `repo.save`; `copy_from` copies it through a `register_copier` copier (only reached with FEATURE_RERUN on).
- `tests.rules` (pure): `sitting_end(opened_at, minutes, factor)`, `answering_ends_at(attempt)` = earlier of `sitting_ends_at` and `effective_deadline` (either may be None), `sitting_ended(attempt, now)` = `sitting_ends_at <= now` and it is before (`<`) `effective_deadline` or there is none.
- Time factor: `tests.sitting.time_factor(s, class_session_id, user_id)` reads Story 8.9's `sessions.get_adjustment` when present (`.time_factor` > 1), else 1. Story 8.9 is on branch `epic-8`, not here; the lookup needs no edit at merge.
- `save_answer`/`submit` on an open attempt: `SittingEnded` (409 `sitting_ended`) when `sitting_ended`, else `DeadlinePassed` past `answering_ends_at`; `attempt_submitted` after the sweep (status check first, unchanged).
- `end_sitting(attempt_id, now) -> bool`: session share-lock (`individual_test_session_of` is per-user; use `sessions.repo.session_row(share=True)` through a sessions helper `test_session_pins`), attempt `FOR UPDATE`; only `open` attempts with `sitting_ended`; `score_answers`, `status='auto_submitted'`, `submitted_at = sitting_ends_at`, `record_step(TEST_SUBMITTED, sitting_ends_at)`; never touches `closed_at`; idempotent. Finder `due_sitting_ends(now)` (≤ 200, oldest first). Due action `tests.end_sitting` placed directly before `sessions.lock_test`. `COMMAND_TOPICS["tests.end_sitting"] = {"session","user"}`.
- `MyTestOut` adds `time_limit_minutes` (the Student's own, factor applied, rounded up; null untimed), `sitting_ends_at`, `answering_ends_at`, `server_now`, `sitting_ended` (auto-submitted with `submitted_at == sitting_ends_at`).
- Web: statement adds «Testen har en tidsgrense på N minutter. Tiden starter når du åpner testen, og den kan ikke stoppes.» and a timed how-it-works line; open test shows sticky «Tid igjen N min» (ceil minutes from `useServerNow`), no live region on it; one polite «5 minutter igjen. Svarene dine er lagret.» when ≤ 5 min remain; at 0 the page shows «Tiden er ute. Testen er levert.» with read-only answers and re-reads the test; `sitting_ended` auto-submitted shows the same line. Copy in `nb.ts`, draft marked [ASSUMPTION].
- Klasseøkt block «Tidsgrense» (Bryter + Tekstfelt minutes + help with scope and range), applies on «Lagre Klasseøkt».

**Never:** No change to `effective_deadline` from the limit; `end_sitting` never calls `close_attempt`, sets `closed_at` or starts anything else; no extension logic (11.13); no change to the demo Class; no answer text in logs; no LLM call.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Set on | owner PUT `test_sitting.minutes=90` before start | stored, read back, `session:<id>` | — |
| Out of range | 5 or 500 | nothing stored | 422 `invalid_session_values` `test_sitting_minutes` |
| Locked change | change after lock | nothing stored | 409 `session_locked` `test_sitting` |
| Open timed | limit 60, open at T | `sitting_ends_at=T+60m`, `effective_deadline` unchanged | — |
| Factor | factor 1.5, limit 60 | `T+90m`, statement says 90 | — |
| Late open | sitting would end after deadline | `answering_ends_at` = deadline; `end_sitting` not due; `close_attempt` hands in | — |
| Ended, before sweep | save/submit at `sitting_ends_at` | refused | 409 `sitting_ended` |
| Sweep | open, sitting ended | `auto_submitted`, `submitted_at=sitting_ends_at`, scored, step, `closed_at` NULL; repeat no-op | — |
| After sweep | save | refused | 409 `attempt_submitted` |
| Deadline | `close_attempt` at deadline on that attempt | only `closed_at` set | — |
| Off | no row | `sitting_ends_at` NULL, `time_limit_minutes` null, nothing timed shown | — |
| Copy | `copy_from` source timed | copy has the same minutes | — |

</intent-contract>

## Code Map

- `backend/app/modules/tests/commands.py` -- `open_attempt` (~191) insert values; `save_answer` (~349) and `submit` (~495) checks; add `SittingEnded`, `end_sitting`, `due_sitting_ends`, `end_due`; `close_attempt` (~543): after review, an open attempt whose sitting ended before the deadline is handed in as of `sitting_ends_at`.
- `backend/app/modules/tests/rules.py` (new), `backend/app/modules/tests/sitting.py` (new: read/write/copy/time_factor, registers with `sessions`), `backend/app/modules/tests/service.py` (re-export `sitting_minutes` as the AC names `tests.service`).
- `backend/app/modules/tests/{models.py,attempt.py,schemas.py,routes.py,README.md}` -- table + index; `_open`/`read` new fields; `MyTestOut`; routes map `SittingEnded`.
- `backend/migrations/versions/0129_test_sittings.py`; `backend/tests/test_migrations.py` head.
- `backend/app/modules/sessions/{service.py,schemas.py,routes.py}` -- `register_test_sitting`, `save_session` (~978, refused map ~1071, write before `repo.save` ~1156), `get_session` (~837), `ClassSessionSaveIn` (~411), `ClassSessionOut` (~334), `TestSittingIn/Out`; route passes `test_sitting`, maps errors (existing).
- `backend/app/platform/config.py` -- range settings. `backend/app/modules/ops/sweep.py` (~166) due action; `backend/app/platform/events/registry.py` (~174) topics.
- Tests: `backend/tests/individual_test/test_submit.py` helpers (`opened`, `put`, `submit_path`), `test_auto_submit.py` (sweep, clock), `tests/sessions/test_ai_assessment_switch.py` (save + copy pattern, sweep order ~146).
- Frontend: `src/modules/tests/{individual-test-page.tsx,individual-test.ts,api.ts}`, new `src/modules/tests/timed-sitting-block.tsx` + `sitting.ts`; `src/modules/sessions/class-session-page.tsx` (~173 body, ~455 block); `src/modules/games/seat-status.ts` `useServerNow`; `src/components/{switch,text-field}.tsx`; `src/copy/nb.ts` (`tests.individual`, new `tests.sitting`); `e2e/individual-test.spec.ts` stand-ins, a new `e2e/timed-sitting.spec.ts`.

## Tasks & Acceptance

**Execution:**
- Migration, models, config -- storage and range.
- `tests/rules.py`, `tests/sitting.py`, `tests/commands.py`, `attempt.py`, `schemas.py`, `routes.py` -- sitting on open, gates, `end_sitting`, read model.
- `sessions/*`, `ops/sweep.py`, `registry.py` -- save/read/copy hook, due action, topics.
- `backend/tests/individual_test/test_timed_sitting.py` (new) -- every matrix row with a fixed clock (factor via monkeypatched `sessions.get_adjustment`), sweep order, `close_attempt` after `end_sitting`; `test_rules` pure cases.
- Frontend: `npm run api:generate`; block + page body; test page statement, clock, ended view; `nb.ts`; Vitest for `sitting.ts`; Playwright statement-with-limit and running time at 360/1440 with axe, block on/off/out-of-range.

**Acceptance Criteria:**
- Given a Lecturer before the Start date, when they switch «Én økt med tidsgrense» on, type 90 and press «Lagre Klasseøkt», then the value is stored and read back; 500 is refused with the range shown.
- Given a timed Class session, when a Student reads the statement, then it states the limit and that the time starts at opening and cannot be paused.
- Given a timed open attempt, when the Student scrolls, then «Tid igjen N min» stays at the top; at 0 the page reads «Tiden er ute. Testen er levert.».

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
Layers: blind hunter, edge-case hunter, verification gap and intent alignment (sonnet; four, per the team lead's brief for deadlines and sweeps). The implementation was done in the main context per the brief, not by a step-03 subagent.
- verdicts: 37 findings — high 0, medium 0, low 23, false 14, maybe-false 0
- findings:
  - `[false]` `[reject]` Blind: the time factor is a silent stub with a guessed `get_adjustment` signature — the signature `get_adjustment(session, class_session_id, user_id) -> Adjustment | None` with a Decimal `time_factor` was read from Story 8.9's commit `ffc06e13` on `epic-8`; the lookup needs no edit at merge, and the AC's "where one is recorded" makes 1 correct while none can be. Reported for the merge.
  - `[low]` `[reject]` Blind: `sitting_ended` is inferred from `submitted_at == sitting_ends_at`, the rule lives in three places — the API sends the one flag; the page's `sittingEnd` only decides the copy of the minute before the sweep. Storing a reason column adds state for no reader. The equality edge is patched below (Edge row 5).
  - `[low]` `[patch]` Blind: the 200 cap or a failing `end_sitting` lets the Test-deadline close stamp `submitted_at` = deadline although saves were refused from the sitting's end — `close_attempt` now hands an open attempt whose sitting ended before the deadline in as of `sitting_ends_at` (step too); new `test_a_sitting_the_sweep_missed_is_handed_in_at_its_end_by_the_close`.
  - `[low]` `[reject]` Blind: no cross-field check that `test_sitting_min_minutes <= test_sitting_max_minutes` — operator configuration of placeholders, the sibling ranges have none either; a validator is new surface for a mistake not shown.
  - `[low]` `[reject]` Blind: the save is a silent no-op when the `tests` writer is not registered — every API process imports `tests.routes` → `tests.service`, which registers it; `test_the_owner_sets_and_clears…` proves the round trip through the app. A guard would protect a state not demonstrated.
  - `[low]` `[reject]` Blind: no check of the limit against the date window, no warning with attempts, no audit row — none is asked by the AC; attempts exist only after the lock, from which the limit is frozen; the other «Lagre Klasseøkt» settings are not audited either.
  - `[low]` `[patch]` Blind: the page's reactions are untested, and the five-minute line may not be announced when the page opens with under five minutes — the line is now set in an effect after the first render, so the status region changes and is announced; the rest is covered by the stand-in specs and the api tests.
  - `[low]` `[reject]` Blind: `TimeUp` drops unsent drafts — the clock is the server's (`useServerNow` lags rather than leads), and text not stored by the sitting's end is refused (`sitting_ended`) and cannot count.
  - `[low]` `[reject]` Blind: only one warning, no pause, sticky bar unverified with the header, threshold fixed — the AC names one polite line and no pause; the e2e checks the bar at the top after scrolling on the real page shell at 360 and 1440 px.
  - `[false]` `[reject]` Blind: `useServerNow` imported from `games`, the "can change" rule repeated — the Replay block imports the same shared clock; the page holds the block to its own choosing state like the other Start-date choices (see Design Notes).
  - `[false]` `[reject]` Blind: «1 minutter», statement lacks the Testfrist — the range starts at 15 and the factor never lowers it; the statement already shows the Testfrist line under the limit.
  - `[low]` `[reject]` Blind: missing tests (factor below 1, moved deadline, archived, concurrency, constraint) — the NULL-deadline path is patched (Verification row 1); the rest is guarded by code paths shared with Stories 11.3/11.11 and their tests.
  - `[false]` `[reject]` Blind: regenerated client and docs missing from the diff — `openapi.json`/`schema.ts` were regenerated with `npm run api:generate` and left out of the review diff on purpose; `tests/README.md` and `sessions/README.md` are in the diff.
  - `[low]` `[patch]` Edge: >200 due sittings or a failing `end_sitting` then the deadline close stamps the deadline — same root and patch as the third Blind row.
  - `[low]` `[reject]` Edge: poison rows fill the 200 window — as in Story 11.11's rejected row: each failure is logged every minute; 200 permanently failing attempts are needed.
  - `[false]` `[reject]` Edge: `get_adjustment` returning a non-numeric factor gives a 500 — Story 8.9's `time_factor` is a NOT NULL numeric column limited to its offered factors.
  - `[low]` `[reject]` Edge: the statement promises the full limit when the Testfrist is nearer — the statement shows the Testfrist right below the limit, and once opened «Tid igjen» counts to the earlier end (`answering_ends_at`).
  - `[low]` `[patch]` Edge: `sitting_ended` true when the sitting ends exactly at the deadline and the close hands it in — `_open` now also requires `sitting_ends_at < effective_deadline`, as `rules.sitting_ended` does.
  - `[low]` `[patch]` Edge: «Lever testen» answered `sitting_ended` does not re-read the test — the submit's error handler now invalidates the test on `sitting_ended` too.
  - `[low]` `[reject]` Edge: unsent drafts cleared at 0 — same as the eighth Blind row.
  - `[low]` `[reject]` Edge: writer not registered — same as the fifth Blind row.
  - `[low]` `[patch]` Edge: a stored limit outside a later-changed range blocks every Klasseøkt save on the page — the page now judges the limit only when it is changed, as the api does.
  - `[low]` `[reject]` Edge: min above max in configuration — same as the fourth Blind row.
  - `[false]` `[reject]` Edge (claim): the factor is always 1 on this branch — stated in the spec and the code as the merge-time state; not a defect of this story.
  - `[false]` `[reject]` Edge (claim): the page says «Testen er levert» up to a minute before the sweep, and uses the deadline line when the sitting ends with the deadline — both by design (Design Notes); nothing can be saved in that minute.
  - `[low]` `[patch]` Verification: the finder's NULL-deadline branch never ran against the database — new `test_a_sitting_with_no_test_deadline_is_handed_in_by_the_sweep`.
  - `[false]` `[reject]` Verification (other): the 8.9 signature is unverified — read from commit `ffc06e13` (first Blind row).
  - `[low]` `[reject]` Verification (other): archived `can_change` untested — the page also gates on `can_manage`, which includes the archive, as the reviewer notes.
  - `[low]` `[reject]` Intent: the Student states are tested on stand-ins — the project's e2e pattern (as in 11.10/11.11); the api side is pinned by pytest on the same fields, and the typed client is generated from the same schema.
  - `[false]` `[reject]` Intent: 8.9 stubbed with a guessed shape — first Blind row.
  - `[low]` `[reject]` Intent: no test of an actual tick — `minutesLeft` is unit-tested and `useServerNow` is the shared clock other screens' specs cover.
  - `[false]` `[reject]` Intent: the page shows the end before the sweep — the reading the epic's copy supports; Design Notes.
  - `[false]` `[reject]` Intent: `end_sitting` takes `now` — every sweep action takes `(item, now)`; ids only are passed and logged.
  - `[false]` `[reject]` Intent: `sitting_ends_at` already existed — migration 0123 made it for this story; behaviour matches.
  - `[false]` `[reject]` Intent: a new `tests`-owned table — the AC's "through `tests.service`"; `sessions` cannot import `tests`.
  - `[low]` `[reject]` Intent: `time_limit_minutes` computed by two paths — both round the same limit up to whole minutes; the open one reads what was stored at opening.
  - `[false]` `[reject]` Intent: Lecturer axe at one width — the AC asks 360/1440 for the statement and the running time, which run at both.

## Design Notes

- `sessions` cannot import `tests` (tests imports sessions); the hook pair mirrors `register_copier`/`register_test_deadline_mover`.
- `tests.end_sitting` sits before `games.close_at_test_deadline` and so before `sessions.lock_test` and `tests.close_attempt` in the sweep (Story 12.1's test keeps `lock_test` directly after the Replay close): when a late sweep finds both due, the sitting's end is the earlier and truer hand-in time.
- The Klasseøkt block is editable only while the api says so and the page itself is choosing (`can_manage`, not locked), like the other Start-date choices.
- The page treats a passed sitting as handed in before the sweep has run (at most a minute): nothing can be saved then (`sitting_ended`), and it re-reads until the state is `auto_submitted`.

## Verification

**Commands:**
- `uv run pytest tests/individual_test tests/sessions/test_ai_assessment_switch.py tests/test_migrations.py -q` -- pass
- `npm run typecheck && npx vitest run src/modules/tests src/modules/sessions` -- pass
- `npx playwright test e2e/individual-test.spec.ts e2e/timed-sitting.spec.ts --workers=4` -- pass

## Auto Run Result

Status: done

**Summary.** A Lecturer can now require the Individual test in one timed sitting. The Klasseøkt has a block «Tidsgrense på testen»: a Bryter («Én økt med tidsgrense» / «Ingen tidsgrense») and, while on, a Tekstfelt for whole minutes with the range and the scope under it. It is saved with «Lagre Klasseøkt» as `test_sitting: {minutes}` (null: off). `sessions.save_session` judges the configured range (15-240, PLACEHOLDERS; 422 `invalid_session_values` `test_sitting_minutes`), freezes it from the Start date (409 `session_locked` `test_sitting`) and stores it through `tests.service`, which registers `tests.sitting` with `sessions` (new table `test_sittings`, migration 0129); «Lag kopi» copies it. `open_attempt` sets `sitting_ends_at` = opening + limit × the Student's time factor (Story 8.9's `sessions.get_adjustment` when present; 1 on this branch) and never changes `effective_deadline`. `tests.rules.answering_ends_at` is the earlier of the two; `save_answer` and `submit` answer 409 `sitting_ended` once the sitting has ended before the deadline. A new sweep action `tests.end_sitting` (before the Test-deadline actions) hands such an attempt in (`auto_submitted`, `submitted_at = sitting_ends_at`, scored, `test_submitted` recorded) and starts nothing else; `close_attempt` still runs at the deadline and only marks it closed. The statement states the Student's limit and that the time cannot be paused; the open test keeps «Tid igjen N min» sticky at the top (from `server_now`), says «5 minutter igjen. Svarene dine er lagret.» once, politely, and at 0 shows «Tiden er ute. Testen er levert.» with the answers read-only.

**Files.**
- `backend/migrations/versions/0129_test_sittings.py` (new), `backend/app/modules/tests/models.py`: `test_sittings`, the finder's partial index.
- `backend/app/modules/tests/rules.py` (new): `answering_ends_at`, `sitting_ended`, `sitting_end`, `limit_minutes`.
- `backend/app/modules/tests/sitting.py` (new): read, write, copy, `time_factor`; `tests/service.py` registers them.
- `backend/app/modules/tests/commands.py`: sitting on open, `SittingEnded` gates, `end_sitting`, `due_sitting_ends`, `end_due`; `close_attempt` hands a missed sitting in at its end.
- `backend/app/modules/tests/{attempt.py, schemas.py, routes.py, README.md}`: `MyTestOut` fields, 409 `sitting_ended`, docs.
- `backend/app/modules/sessions/{service.py, schemas.py, routes.py, README.md}`: `register_test_sitting`, `test_session`, `_judge_sitting`, save/read of `test_sitting`.
- `backend/app/modules/ops/sweep.py`, `backend/app/platform/events/registry.py`, `backend/app/platform/config.py`.
- Tests: `backend/tests/individual_test/test_timed_sitting.py` (new, 22 tests), `test_open.py` (statement shape), `tests/test_migrations.py` (head 0129).
- Frontend: `src/modules/tests/{sitting.ts, sitting.test.ts, timed-sitting-block.tsx}` (new), `individual-test-page.tsx`, `individual-test.ts`, `individual-test.test.ts`, `src/modules/sessions/class-session-page.tsx`, `src/copy/nb.ts`, regenerated `src/lib/api/{openapi.json, schema.ts}`, `e2e/timed-sitting.spec.ts` (new).

**Review.** Four sonnet reviewers reported 37 findings: high 0, medium 0, low 23, false 14. Patched (low, six root causes): a missed sitting handed in at its end by the close; `sitting_ended` false when the sitting ends exactly at the deadline; the five-minute line set after the first render; «Lever testen» re-reads on `sitting_ended`; the page judges the limit only when changed; a NULL-deadline sweep test. Nothing deferred. Every rejection has its reason in the triage log.

**Follow-up review: not recommended.** Patched: high 0, medium 0, low 6.

**Verification.**
- Backend: full suite with `--maxprocesses=8`: 3391 passed (a first run after the patches had 2 failures that did not recur on the rerun; not in the touched files' tests). `ruff check` and `ruff format --check` clean; the migration round trip passes. New tests over 1 s: eight in `test_timed_sitting.py` (1.0-2.2 s), from the shared locked-session setup and full `sweep.run` calls.
- Frontend: `tsc` clean, Vitest 1081 passed, `lint:colours`, `check:copy` and `next build` pass.
- Playwright on lane 2 (8081, stack rebuilt after the patches): timed-sitting, individual-test, homes, class-session (+ choices, lock, obligatory, rerun, replay), ai-assessment-switch, question-set, scoring-guide, order-confirm, order-field, week-table, game-start, guided-week, student-home: 217 passed (axe at 360 and 1440 px for the Student states).

**Decisions taken for the founder.**
- The time limit is stored with the Class session in a `tests`-owned table, saved with «Lagre Klasseøkt», and frozen from the Start date with the question set [ASSUMPTION from the AC].
- The range is 15-240 minutes (PLACEHOLDERS); a switched-on limit starts at 90 minutes.
- The time factor applies only where Story 8.9 records one; on this branch every factor is 1 until Epic 8 merges.
- A sitting that would end after the Test deadline ends with the deadline and is handed in by the Test-deadline close.
- The page shows «Tiden er ute. Testen er levert.» as soon as the server clock passes the sitting's end, before the sweep (at most a minute) hands it in.
- The sweep hands in at most 200 ended sittings a minute.
- All new Klasseøkt and Student copy is draft [ASSUMPTION] in `nb.ts`.

**Personal data.** New table `test_sittings` has an `updated_by` user id (the Lecturer who last saved it) and no text a User wrote.

**Residual risks.**
- At the merge with Epic 8 the `getattr` lookup of `sessions.get_adjustment` must find the 8.9 function; a test with the real Tilrettelegging should then replace the monkeypatched one.
- Story 11.13 must keep `sitting_ends_at` as it is when it extends a deadline.
