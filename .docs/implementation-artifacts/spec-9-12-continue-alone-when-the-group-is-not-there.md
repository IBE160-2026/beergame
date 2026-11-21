---
title: 'Story 9.12: Continue alone when the group is not there'
type: 'feature'
created: '2026-11-21'
status: 'done'
baseline_revision: 'd23993bbc9c716025ecbd2f57a78e359c7adf7a4'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-9-context.md'
warnings: ['oversized']
deferred:
  - summary: >-
      A move-on can advance the shared pointer twice when another command moves it between the opener's press and the move.
    evidence: |-
      `commands.move_on` judges the pointer it finds under the lock, not the step the opener saw; a step finished by everyone just before the press is followed by the press's own move. Present since Story 9.11; Story 9.12 split `move_on` into a settle and a move transaction, which keeps the same window. A fix sends the expected step with the press (an api change).
    location: >-
      backend/app/modules/debrief/commands.py (move_on)
    severity: low
---

<intent-contract>

## Intent

**Problem:** In a Group debrief (Story 9.11) a Student's progress depends on the others: the shared step waits for every joined Student, only the opener can move on (and nobody can once the opener is gone, the deferred medium item of 9.11), a Student who has not joined sees only the join panel, and nothing ever turns a Group debrief that never met into a Personal one (FR-43).

**Approach:** A Student of a shared Debrief can go alone (Personal debrief) by leaving, by dropping out (no SSE heartbeat for 2 minutes) or by the sweep's 48-hour fallback. Going alone is stored per Student, keeps everything they saved, lifts the pointer gate for them, and the group no longer waits for them. When the opener is no longer among the joined, the earliest-joined remaining Student becomes the opener.

## Boundaries & Constraints

**Always:**
- New table `debrief_alone(debrief_id, user_id, step, reason, since)` (PK debrief+user; `reason` in `left|dropout|fallback`; `step` = the pointer when a joined Student goes alone, 1 for one who never joined). `debrief_members.last_seen_at` (not null, set at join/open). `debrief_sessions.fallback_due_at` (shared rows: the Game's finish time, the finished Week state's `created_at`, else db now, + 48 h, set by `open`) and `fallback_at`. Migration `0111`. Joined set = members without an alone row.
- `platform/events.on_heartbeat(callback)` registers `async (user_id)` hooks; `events.heartbeat(user_id)` runs them, logging and swallowing failures (type only). `stream.events(..., beat=None)` awaits `beat()` on each heartbeat; the `/api/events` route passes `events.heartbeat(user.id)`. `platform` imports no module.
- `debrief.commands.touch(user_id)` (registered at import of `debrief.commands`): one short session, `last_seen_at = now()` on the user's joined rows of shared, not-fallen-back sessions with pointer < 4; no row lock, no event; registry `debrief.touch: {}`.
- `debrief.commands.leave(game_id, user_id, dropout=False)`: locks the row; `NotGroup` on Personal; at pointer ≥ 4 or already alone: unchanged, no event. `dropout=True` acts only if the user is joined and `last_seen_at < now() - 2 min` (db time). Inserts the alone row, then settles, emits `debrief:<id>`. Registry `debrief.leave: {debrief}`.
- Settle (inside `join`, `save_explanation`, `complete_step`, `move_on`, `leave`, under the lock, shared and not fallen back): joined members (except the caller) silent > 2 min go alone with reason `dropout` (the same insert `leave` uses); an opener not among the joined is replaced by the earliest-joined joined Student (or NULL); then the pointer advances as in 9.11. A command whose settle changed something emits `debrief:<id>`.
- `join` on a fallen-back session or by an alone Student → `GroupClosed` (409 `group_closed`).
- `debrief.commands.open_personal_fallback(debrief_id)`: locks; acts once (shared, `fallback_at` null, pointer < 4): sets `fallback_at`, gives every Student of the game (`games.service.game_students`) without a Debrief summary and not alone an alone row `fallback`, and a `debrief_fallback` notice (digest, dedupe `debrief_fallback:<debrief>:<user>`, ref Class session); emits `debrief:<id>`. Registry `{debrief, user}`.
- Sweep (`ops.sweep`, after `debrief.release`): `debrief.dropouts` (finds joined, stale members of shared sessions with pointer < 4 by db time → `leave(dropout=True)`), `debrief.fallback` (shared, `fallback_at` null, pointer < 4, `fallback_due_at <= now` → `open_personal_fallback`). Ids only.
- Gate: an alone Student's reads are Personal (no `step_locked`); `complete_step`/`move_on` refuse them (403). `GroupOut` gains `alone: 'left'|'dropout'|'fallback'|null` and `alone_from: int|null`; `members` only for joined callers. Hjem `group_open` false for alone Students and fallen-back sessions. Mail kind `debrief_fallback` (context: Class name unless the Debrief step is done).
- Route `POST /api/debriefs/{id}/leave` (`leaveDebrief`, `debriefs.own`): 409 `not_group` on Personal; non-Student 403.
- Web: join panel adds «Ta en Personlig debrief»; a joined Student's bar adds «Forlat gruppen» with an in-place confirm; an alone Student sees every step their own progress opens (`reach`), with an alone line (reason-specific) under the step they were on, focused when they go alone on this page. The new opener's page shows «Gå videre for alle» without reload. Copy in `nb.ts`, draft `[ASSUMPTION]`.

**Never:** no rejoin after going alone; presence never reported by the client; no names in events, notices or facts; no shared screen (9.13); no change to 9.11's step rules for joined Students; no growth of `test_group.py`, `test_explanation.py` beyond one-line fixes.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Leave | A (opener), B joined, pointer 1; A leaves | A alone `left` from 1, reads step 2 after sending; B opener; event | Personal 409 `not_group` |
| Dropout | B silent > 2 min, A finishes the step | B alone `dropout`, pointer moves for A | — |
| Touch | heartbeat of A | A's `last_seen_at` now, no event | hook failure logged |
| Alone without joining | C never joined, leaves | C alone from 1; C join → 409 `group_closed` | — |
| Fallback | 48 h after finish, pointer < 4 | each unfinished Student alone `fallback`, notice once; second run nothing | — |
| No fallback | pointer 4, or Personal | nothing | — |

</intent-contract>

## Code Map

- `backend/app/modules/debrief/commands.py` -- `open:110`, `_members:186`, `_advance:227`, `join:240`, `move_on:263`, `save_explanation:329`, `complete_step:398`; `release` (notify pattern). Add `GroupClosed`, `_alone`, `_settle`, `leave`, `touch`, `open_personal_fallback`.
- `backend/app/modules/debrief/service.py` -- `DebriefRow` reader flag via `_own:333`; `require_step:362`; `_group:246`; `join_mine`; `due_releases:1206` pattern for `due_dropouts`/`due_fallbacks`; add `leave_mine`.
- `backend/app/modules/debrief/{models,rules,schemas,routes}.py`, `README.md` -- tables; `group_open:132`; `GroupOut:43`; `_answer` error map `:179`, routes `:259-301`.
- `backend/app/platform/events/{__init__,stream,registry}.py` -- hooks, `events():95` heartbeat branch `:129`, route `:174`; registry `:98-131`.
- `backend/app/modules/games/{repo,service}.py` -- `finished_state:639` pattern; add `finished_at`.
- `backend/app/modules/ops/sweep.py:147` -- due actions. `messaging/delivery.py:174-203`, `sessions/service.py:1333` (mail context), templates `kinds/group_debrief_opened.*`.
- Tests: `tests/debrief/test_group.py:49` `played()` and helpers (reuse by import), `tests/platform/test_event_stream.py:92`.
- Frontend: `modules/debrief/{api.ts:50 reach, group.tsx, debrief-page.tsx:106}`, `copy/nb.ts:2103`, regenerated `lib/api/{openapi.json,schema.ts}`; e2e `debrief-group.spec.ts` pattern.

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0111_debrief_alone.py`, `debrief/models.py` -- columns and table above.
- `backend/app/platform/events/{__init__,stream}.py` -- `on_heartbeat`, `heartbeat`, `beat`.
- `backend/app/modules/games/{repo,service}.py` -- `finished_at`.
- `backend/app/modules/debrief/{commands,service,rules,schemas,routes}.py`, `README.md` -- as above.
- `backend/app/modules/{ops/sweep.py,messaging/delivery.py,sessions/service.py}`, templates `debrief_fallback.{txt,html}.j2`, `platform/events/registry.py` -- wiring.
- `backend/tests/debrief/test_group_alone.py` (new) -- matrix rows, registry topics for `leave`, `touch`, `open_personal_fallback`, sweep both actions, mail context; `tests/platform/test_event_stream.py` -- beat on heartbeat. `tests/test_migrations.py` head.
- Frontend: `api.ts` (`reach`, `leaveDebrief`), `group.tsx` (leave in join panel and bar, `AloneLine`), `debrief-page.tsx`, `nb.ts`, regenerated client; Vitest for `reach` alone.
- `frontend/e2e/debrief-alone.spec.ts` (new) -- 360 and 1440 px with axe: Sara opens, Ida joins, Sara leaves (confirm) → alone line focused under step 1, after sending she sees step 2; Ida becomes opener live (sees «Gå videre for alle»).
- Missed group (loop 1): `debrief.commands.open` on an existing shared row whose pointer is at `INDIVIDUAL_STEP` (the group has finished the shared steps), not fallen back, for a Student neither joined nor alone, stores their alone row with reason `missed` from step 1 and emits `debrief:<id>` (migration check `reason IN ('left','dropout','fallback','missed')`, `GroupOut.alone` literal, `nb.ts` `aloneLine.missed`); `rules.group_open` is false once the pointer is at `INDIVIDUAL_STEP`. Test in `test_group_alone.py`.
- Review patches (loop 1): a command by a joined caller refreshes their `last_seen_at`; `events.heartbeat` bounds each hook with a timeout; `open_personal_fallback` also covers joined members missing from `game_students`; migration 0111 backfills `fallback_due_at` of existing shared rows; `debrief_alone.step` 1..3; the page moves focus to the alone line only after the Student's own leave; the join panel's alone action has its own failure copy; the fallback mail claims nothing was written. Tests: the real `/api/events` heartbeat reaches the hooks; the two sweep actions are registered; the `debrief_fallback` kind is a digest wired to its context; a command-time dropout, a silent caller kept, the move-on whose settle moved the pointer; `alone_from` 2; a finished Student skipped by the fallback; a refreshed Student not dropped by a stale sweep item.

**Acceptance Criteria:**
- Given a joined Student with an open stream, when 15 s heartbeats pass, then `last_seen_at` follows and no event is emitted.
- Given a group whose opener has left, dropped out or been deleted, when the next command or sweep settles it, then the earliest-joined remaining Student may move on.
- Given a Student who left, dropped out or fell back, when they open the Debrief, then every step their own progress opens is readable, their saved Explanation and answers kept, and the line says why they go alone.
- Given a Student who missed a Group debrief whose joined Students have already finished the shared steps (pointer at 4), when they open the Debrief, then it opens as a Personal debrief at once (`alone: missed`), without waiting for the 48 hours, and Hjem no longer offers to join.

## Spec Change Log

### 2026-11-21 — Loop 1 (bad_spec)
- Trigger: intent-alignment divergence (a) and blind finding 8: the story's AC «a Student who missed a Group debrief that the others have already finished opens it as a Personal debrief at once» had no task, AC or code; a never-joined Student at pointer 4 saw only «Bli med» and Hjem still said the Group debrief was under way.
- Amended: Tasks & Acceptance (the missed-group task, the review patches) and Acceptance Criteria (the missed-group AC). The intent-contract is unchanged; the `missed` reason extends its `reason` list the same way the other three are stored.
- Known-bad state avoided: a Student who never met the group waiting for a join that leads into a group already past its shared steps, or for the 48-hour fallback, which never comes once the pointer is at 4.
- KEEP: the whole reviewed implementation, saved as `keep-9-12-loop1.patch` in the build scratchpad (`debrief_alone`, `_settle`, `leave`, `touch`, `open_personal_fallback`, the heartbeat hook, the sweep actions, `effective_opener`, the leave controls and alone line, the tests and the e2e); re-derive by applying it and adding the amendments above.

## Review Triage Log

### 2026-11-21 — Review pass
Layers run: blind hunter, edge-case hunter, verification gap, intent alignment (sonnet, four for a concurrency and access change). Hand-backs failed; findings were read from `review-{blind,edge,verification,intent}-9-12.md` in the scratchpad. The diff left out the generated `openapi.json`/`schema.ts` and `.docs`.
- verdicts: 43 findings — high 0, medium 8, low 26, false 9, maybe-false 0
- findings:
  - `[medium]` `[reject]` (blind 1) The fallback due time counts from the Game's finish, so a held session released after 48 h falls back at the next sweep. Real, but the story's AC fixes the anchor («a column value computed from the Game's finish time»); kept as a residual risk for the founder.
  - `[low]` `[patch]` (blind 2) Shared rows from 9.11 get no `fallback_due_at`. Migration 0111 now backfills them from the finished Week state (else the open) + 48 h.
  - `[medium]` `[patch]` (blind 3) The stream's `beat` wiring and the import-time registration are untested. Same root as verification 1: a test now drives the real `/api/events` stream with a short heartbeat.
  - `[medium]` `[patch]` (blind 4) A Student's own command does not count as presence, so one whose SSE is down is dropped by the next settle. A command by a joined caller now writes their `last_seen_at` under the lock.
  - `[false]` `[reject]` (blind 5) Two silent minutes drop a Student for good. The story's AC sets both (2 minutes; «on return, continues in a Personal debrief»).
  - `[low]` `[reject]` (blind 6) `move_on` settles before it authorises; the opener's click is consumed by a settle's move. The settle does only what any command or the sweep would do; the consumed click is the documented rule (no double move).
  - `[low]` `[patch]` (blind 7) `touch` is awaited inline with no bound. `events.heartbeat` now bounds each hook (5 s) and logs a timeout like a failure.
  - `[medium]` `[bad_spec]` (blind 8) A never-joined Student has no way out once the group is past the shared steps. Same root as intent (a): the missed-group AC; amended in the spec (loop 1).
  - `[low]` `[patch]` (blind 9) The join panel's alone action used «Det ble ikke lagret». Now its own copy `aloneFailed`.
  - `[low]` `[patch]` (blind 10) Focus jumps to the alone line when a dropout or fallback arrives over the stream. Focus now moves only after the Student's own leave.
  - `[low]` `[patch]` (blind 11) Missing tests (touch skips, last member leaving, mail context after finishing, UI). Covered in part by the verification-gap patches; component tests and an e2e click of «Ta en Personlig debrief» are not worth a new suite (the api path is tested).
  - `[low]` `[patch]` (blind 12) The fallback mail says «det du har skrevet, er lagret» also to Students who wrote nothing. Reworded; the html subject follows the existing templates (txt only).
  - `[low]` `[patch]` (blind 13) `ck_debrief_alone_step` allows 1..5 where only 1..3 occur. Now 1..3; the generated client was regenerated (left out of the diff only).
  - `[low]` `[reject]` (blind 14) Two reads per request, no index on `last_seen_at`/`fallback_due_at`, the kind constant duplicated. Small tables; the duplicated constant is the module pattern and a test now ties it (verification 3).
  - `[medium]` `[patch]` (edge 1) Same as blind 4.
  - `[low]` `[patch]` (edge 2) Presence only through SSE. Same root as blind 4.
  - `[medium]` `[reject]` (edge 3) Same as blind 1.
  - `[low]` `[patch]` (edge 4) Same as blind 2.
  - `[low]` `[patch]` (edge 5) Same as blind 7.
  - `[low]` `[defer]` (edge 6) A move-on can advance twice when another command moves the pointer between its two transactions. Pre-existing in 9.11 (a click arriving after the auto-move); the fix needs the expected step in the api.
  - `[low]` `[reject]` (edge 7) Same as blind 6.
  - `[low]` `[reject]` (edge 8) The stored opener stays NULL until a command. Reads and `move_on` use `effective_opener`; the stored value is internal and the next command writes it.
  - `[low]` `[patch]` (edge 9) The fallback skips a joined member missing from `game_students`. It now covers joined ∪ game Students.
  - `[low]` `[reject]` (edge 10) `_own`'s alone read can race a dropout into one `step_locked`. The next read is right; negligible.
  - `[low]` `[patch]` (edge 11, claim) «The caller is never dropped by it». Same as blind 4.
  - `[low]` `[reject]` (edge 12, claim) The sweep does not persist the opener. Same as edge 8.
  - `[medium]` `[patch]` (verification 1) Same as blind 3.
  - `[low]` `[patch]` (verification 2) The two sweep registrations are untested. Asserted now.
  - `[low]` `[patch]` (verification 3) The `debrief_fallback` kind's constant, mode and context are untested. Asserted now.
  - `[low]` `[patch]` (verification 4) Command-time dropout, the caller exemption and move-on's settle shortcut are untested. Tests added.
  - `[low]` `[patch]` (verification 5) `alone_from` after step 1, the finished exclusion and the sweep's recheck are untested. Tests added.
  - `[low]` `[patch]` (verification other 1) Same as blind 4.
  - `[low]` `[patch]` (verification other 2) Same as blind 2.
  - `[medium]` `[bad_spec]` (intent a) The missed-group AC is not implemented. Spec amended (loop 1).
  - `[false]` `[reject]` (intent b) Alone is a flag on a shared session, not a conversion. Every read is Personal for that Student; the `group` object only carries why.
  - `[false]` `[reject]` (intent c) The command-time dropout bypasses `leave`. Both go through the same `_go_alone` insert; `leave` is the command form of it.
  - `[false]` `[reject]` (intent d) «No Group debrief finished» read as pointer < 4. The shared steps are the Group debrief; from 4 each works alone.
  - `[false]` `[reject]` (intent e) Registration at import. The app imports `debrief.commands` at startup through its routes; now tested through the real stream.
  - `[false]` `[reject]` (intent f) Same as verification 1, patched there.
  - `[false]` `[reject]` (intent g) Opener hand-over shown only for a left opener in the browser. The api test covers the deleted opener; the read rule is the same.
  - `[false]` `[reject]` (intent h) Registry coverage: satisfied.
  - `[low]` `[reject]` (intent i) Finish and quiz gates untested for an alone Student. `require_debrief` and the finish rules are unchanged code; only the pointer gate is lifted, which is tested.
  - `[false]` `[reject]` (intent j) Notice: satisfied.

### 2026-11-21 — Review pass (loop 1)
Layers run again on the re-derived diff: blind, edge-case, verification gap, intent alignment (sonnet). Hand-backs failed; findings read from `review-*-9-12-loop1.md`.
- verdicts: 39 findings — high 0, medium 2, low 25, false 12, maybe-false 0
- findings:
  - `[medium]` `[reject]` (blind 1) Fallback anchored at the Game's finish. carried: the AC fixes it; residual risk.
  - `[false]` `[reject]` (blind 2) Two silent minutes drop a Student for good. carried: the AC.
  - `[false]` `[reject]` (blind 3) The hook depends on an import side effect. The real-stream test now asserts `touch` is registered once the app is built and that the heartbeat reaches the hooks.
  - `[low]` `[reject]` (blind 4) Every stream writes each 15 s. One indexed UPDATE by `user_id`, bounded by the timeout; small.
  - `[low]` `[patch]` (blind 5) The hook timeout is untested. The presence-hook test now registers a stalled hook under a shortened timeout.
  - `[low]` `[patch]` (blind 6) The confirmation focused the leave button, so a second Enter left. Focus now goes to «Avbryt»; e2e updated.
  - `[low]` `[reject]` (blind 7) Focus may miss the alone line if the Explanation read has not loaded. The page loads it before any step shows; rare.
  - `[low]` `[reject]` (blind 8) Thin UI coverage of the dropout, fallback and missed lines. The api tests cover each state; the lines are copy-linted.
  - `[low]` `[patch]` (blind 9) Fallback test gaps. Same root as verification 1.
  - `[low]` `[reject]` (blind 10) «fra steget du var på» for a Student who never joined. They were on step 1; still true.
  - `[low]` `[reject]` (blind 11) `move_on`'s two transactions. carried (the double step is deferred).
  - `[low]` `[reject]` (blind 12) The joined/alone set is read in three places. One rule (`debrief_alone` minus), small reads.
  - `[low]` `[patch]` (blind 13) Small inconsistencies. The README wrap is fixed; the rest are cosmetic.
  - `[low]` `[patch]` (edge 1) A never-joined Student could join a group at pointer 4 by calling `join` without `open`. `join` now marks them `missed` too; test added.
  - `[false]` `[reject]` (edge 2) A Student left without an alone row after the fallback. The fallback covers every unfinished Student of the game and every joined one.
  - `[false]` `[reject]` (edge 3) A joined Student's second join after the fallback answers 409. After the fallback every unfinished Student goes alone, so 409 is right.
  - `[medium]` `[reject]` (edge 4) Same as blind 1.
  - `[low]` `[reject]` (edge 5) A dropped Student's click answers a bare 403. The next read shows the alone line; rare.
  - `[false]` `[reject]` (edge 6) A present but idle Student never drops out. Presence is the heartbeat (AC); the opener's move-on covers the idle one.
  - `[low]` `[reject]` (edge 7) The hook is awaited inline. Bounded by the timeout now.
  - `[low]` `[reject]` (edge 8) A write per stream. Same as blind 4.
  - `[low]` `[reject]` (edge 9) A touch not yet committed at the 2-minute boundary. A race of milliseconds after two silent minutes.
  - `[false]` `[reject]` (edge 10) A finished joined Student shown as opener after the fallback. A joined Student cannot finish before pointer 4, where no fallback runs.
  - `[low]` `[defer]` (edge 11) The move-on double step. carried (deferred).
  - `[low]` `[reject]` (edge 12) `due_fallbacks` compares with the sweep's host time. The sweep's convention for every due time.
  - `[low]` `[patch]` (edge 13, claim) «missed … join answers group_closed». Same as edge 1.
  - `[low]` `[patch]` (verification 1) A never-joined Student in the fallback is untested. The fallback test now has a third Student who never opens it.
  - `[low]` `[patch]` (verification 2) The mail context's finished branch is untested. Asserted now.
  - `[low]` `[patch]` (verification 3) Same as blind 5.
  - `[low]` `[reject]` (verification 4) The migration backfill is untested. One statement for pre-0111 rows that exist only on unreleased branches.
  - `[low]` `[reject]` (intent 1) No test runs `ops.sweep` itself. The registrations are asserted and the find/act pairs run; `sweep.run` is the generic loop tested elsewhere.
  - `[false]` `[reject]` (intent 2) Time controlled by stored timestamps. The repo's way (no host/db clock comparison, Issue #63).
  - `[low]` `[reject]` (intent 3) The browser covers only `left`. The other states are api-tested.
  - `[low]` `[reject]` (intent 4) `missed` only on `open` (now also `join`). The page always opens first; a bare `GET` changes nothing.
  - `[false]` `[reject]` (intent 5) «No Group debrief finished» as pointer < 4. carried.
  - `[false]` `[reject]` (intent 6) Registration at import. carried; tested.
  - `[false]` `[reject]` (intent 7) «From the same step» and the gates. carried.
  - `[false]` `[reject]` (intent 8) The 9.11 deferral at the command and read layers. That is where move-on lives; the page follows `GroupOut.opener`.
  - `[false]` `[reject]` (intent 9) Scope additions. Each supports an AC.

## Design Notes

Going alone is final and stored as its own row, so 9.11's member table keeps its meaning (who joined) and the joined set is a difference. The caller of a command is never dropped by it (the command shows they are there). The opener hand-over settles 9.11's deferred item without a new control. Dropout reads only db time in both settle and sweep (Issue #63); the fallback due time follows the sweep's existing host-`now` convention.

## Verification

**Commands:**
- `uv run pytest -n0 tests/debrief/test_group_alone.py tests/debrief/test_group.py tests/platform/test_event_stream.py` -- pass
- full backend `--maxprocesses=8`, `ruff check`, `ruff format --check` -- pass
- `npm run typecheck`, `npm test`, `npm run lint:colours`, `npm run check:copy`, `npm run build` -- pass
- Playwright `debrief-alone`, `debrief-*`, `homes`, `live-updates`, play-screen specs `--workers=4` -- pass

## Auto Run Result

Status: done

**Summary.** A Student of a Group debrief now goes on alone as a Personal debrief, and the group no longer waits for them. There are four ways in:

- leaving. A joined Student uses «Forlat gruppen» with an in-place confirmation; a Student who never joined uses «Ta en Personlig debrief» on the join panel.
- dropping out after two minutes without an SSE heartbeat. A command or the sweep judges this.
- the sweep's 48-hour fallback.
- `missed`: the group has finished the shared steps without the Student, so opening (or joining) gives a Personal debrief at once.

Going alone is stored in `debrief_alone` (reason and the shared step the Student was on) and is final: `join` answers 409 `group_closed`. The Student keeps what they saved and reads every step without the pointer gate. The Explanation gate still holds. `GroupOut.alone` and `alone_from` say why and from where, and the page shows a line under that step.

Presence comes from a new `platform/events.on_heartbeat` hook. The real `/api/events` heartbeat calls it, bounded by a timeout. `debrief.commands.touch` writes `last_seen_at` without a lock or an event. A joined caller's own command also counts as presence. Every command that evaluates the joined set settles it: silent Students drop out, then the opener hands over to the earliest-joined Student still there (`effective_opener`, the same rule the read uses), then the pointer advances. This settles Story 9.11's deferred item: a group whose opener left, dropped out or was deleted can move on.

The sweep has `debrief.dropouts` and `debrief.fallback`. `fallback_due_at` is computed at the open from the Game's finish time + 48 h, and backfilled for existing rows. `open_personal_fallback` runs once and sends a `debrief_fallback` digest notice. Hjem stops offering to join once a Student goes alone, the fallback has run or the group is past the shared steps.

**Files.**
- `backend/migrations/versions/0111_debrief_alone.py` (new), `debrief/models.py`: `debrief_alone`, `debrief_members.last_seen_at`, `debrief_sessions.fallback_due_at/fallback_at`.
- `backend/app/modules/debrief/commands.py`: `leave`, `touch`, `open_personal_fallback`, `_settle`, `effective_opener`, `missed` on `open`/`join`, `GroupClosed`; `service.py`: `leave_mine`, the alone read, the gate, the sweep finds and acts; `rules.py` (`group_open`), `schemas.py` (`GroupOut.alone/alone_from`), `routes.py` (`POST /api/debriefs/{id}/leave`), `README.md`.
- `backend/app/platform/events/{__init__,stream,registry}.py`: `on_heartbeat`, `heartbeat`, `beat`, registry entries.
- `backend/app/modules/games/{repo,service}.py`: `finished_at`. `ops/sweep.py`, `messaging/delivery.py`, `sessions/service.py`, templates `debrief_fallback.{txt,html}.j2`: wiring.
- Tests: `backend/tests/debrief/test_group_alone.py` (new); `tests/platform/test_event_stream.py`; `tests/test_migrations.py` (head 0111).
- Frontend: `modules/debrief/{api.ts,group.tsx,debrief-page.tsx,debrief.test.ts}`, `copy/nb.ts`, regenerated `lib/api/{openapi.json,schema.ts}`; e2e `frontend/e2e/debrief-alone.spec.ts` (new).

**Decisions for the founder.** I implemented this in my own context (the orchestrator's rule), with four review layers.

1. Going alone is final; there is no rejoin. The AC says that a Student continues as a Personal debrief «on return».
2. A Student who never joined may also go alone from the join panel while the group is on the shared steps.
3. Alone is stored per Student on the shared session, not as a converted session.
4. The opener role passes to the earliest-joined Student still there. This settles the 9.11 deferral without adding a new control.
5. A joined caller's own command counts as presence, and the caller is never dropped by it.
6. «No Group debrief finished» means the shared pointer has not reached step 4. The fallback skips Students who have finished the Debrief.
7. `missed` means the pointer is at step 4 and the Student never joined. It is triggered on `open` and on `join`.
8. The fallback mail is a digest notice. It is left out once the Student has finished.
9. The leave confirmation puts focus on «Avbryt».
10. The dropout time (2 min) and the fallback time (48 h) are constants from FR-43, not settings.
11. All copy is a draft marked `[ASSUMPTION]`.

**Review.**
- Two passes, four layers each, 82 findings in all. Details are in the triage log.
- First pass: a bad_spec loopback for the missed-group AC, which was not in the spec. The spec was amended outside the intent-contract, and the code was re-derived with KEEP from the reviewed patch. Eleven root causes were patched: 2 medium (presence by command; real-stream wiring test) and 9 low.
- Second pass: 7 root causes patched, all low:
  - `join` marks a missed Student.
  - «Avbryt» gets focus in the leave confirmation.
  - a test for the hook timeout.
  - a never-joined Student in the fallback test.
  - the mail context after finishing.
  - the README.
- Deferred: 1 low (a move-on double step, which was already present in 9.11).
- Rejected with reasons: the rest. These include the fallback anchor, which the AC fixes; it is kept as a residual risk.
- `followup_review_recommended: false`: the last pass patched only low findings.

**Verification.**
- Backend:
  - The story's tests passed after each patch (36 in the three files).
  - Full suite `--maxprocesses=8`: 2946 passed, 4 skipped (91 s), run after the last patch.
  - `ruff check` and `ruff format --check` are clean.
  - Migration 0111 is re-applied to the lane's `olspillet` and `olspillet_test`. The first version was changed in place during the loop, so I downgraded to 0110 and upgraded again; nothing was dropped.
- Frontend: typecheck, Vitest (55 files, 776 tests), `check:copy`, `lint:colours` and `next build` (in the lane image) all pass.
- Playwright on the lane stack (8081), rebuilt after the last frontend change, `--workers=4`. Specs: `debrief-alone` (360 and 1440 px with axe), `debrief-group`, every `debrief-*`, `homes`, `student-home`, `live-updates`, `game-end`, `order-confirm`, `week-advance`, `game-card`, `order-field`, `seat-status`, `guided-week`. Result: 136 of 137 on the first run.
  - `order-confirm.spec.ts:25` (1440 px, «sending, then confirmed») failed once on its transient «sending» text under load. It passed on rerun (12 of 12). It is unrelated to this change.
  - `debrief-alone` failed once on a bug in the test itself: it read the open route with GET. Fixed, then passed.
- Tests over 1 s:
  - `test_group_alone.py::test_leaving_and_dropping_out_hand_the_group_on`: about 4.4 s, plus about 2 s setup.
  - `test_a_student_who_missed_the_group_opens_a_personal_debrief_at_once`: about 2.6 s.
  - `test_a_group_that_never_met_falls_back_after_48_hours`: about 2.5 s.
  - `test_a_personal_debrief_has_nobody_to_leave`: about 1.2 s.
  - Each plays a Class session and a two-Uke game through the api.
- The first targeted run of the missed-group test failed on the stale 0111 constraint in the shared test database. It passed after the re-migration; this was an environment problem, not a flaky test.

**Residual risks.**
- The fallback counts from the Game's finish, as the AC says. A held session released more than 48 h after a game ended therefore falls back at the next sweep.
- A phone that locks for over two minutes drops out for good, as the AC says.
- Every SSE stream runs one small UPDATE per heartbeat.
- The move-on double-step window is still there (deferred).
- The copy is a draft.
