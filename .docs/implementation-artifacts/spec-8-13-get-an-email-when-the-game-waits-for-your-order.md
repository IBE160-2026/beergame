---
title: 'Story 8.13: Get an email when the game waits for your Order'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: '5ce0bd3782e769e499d8fb7c7a166655cd95093b'
review_loop_iteration: 1
followup_review_recommended: false
context: []
warnings: ['oversized']
deferred:
  - summary: >-
      The archived-Class and no-longer-registered branches of turn_reminder_mail_context are not exercised by a test.
    evidence: |-
      Verification-gap review of Story 8.13: dropping either guard would let a reminder reach a Student removed from or archived out of a Class with no failing test; the same guard pair is unpinned in every sibling mail context of sessions/service.py.
    location: >-
      backend/app/modules/sessions/service.py:turn_reminder_mail_context
    severity: low
  - summary: >-
      The registry test's -1 slice for queue_turn_reminder cannot detect extra game or session topics emitted before the user event.
    evidence: |-
      Verification-gap review of Story 8.13: CLASS_SETUP_EVENTS counts from the end, so only the last event is compared with COMMAND_TOPICS; an added game emit would go unnoticed (spurious refetches only).
    location: >-
      backend/tests/games/test_registry.py:CLASS_SETUP_EVENTS
    severity: low
---

<intent-contract>

## Intent

**Problem:** A Student whose Class game waits for their Order is told nothing until an AI player takes the Seat over, so they can hold the group up without knowing it (FR-27).

**Approach:** Each waited-for turn gets a stored `reminder_due_at` (wait start + a configured 2-hour placeholder) from `games.rules.turn_times`. A new sweep due action queues one digest notice `turn_reminder` per User, Game and Week through `platform/notify.enqueue`; the existing Story 3.5 digest delivery gathers it into at most one mail a day outside 22:00–07:00. At mail build time the notice is dropped if the Seat no longer waits.

## Boundaries & Constraints

**Always:** ids only in notices (dedupe key `turn_reminder:<user>:<game>:<week>`, `ref` = the `seat_turns.id`); only `games.commands` writes `seat_turns`; times only from `rules.turn_times`; one waiting predicate `rules.waited_for`; no reminder while paused, before any other Student has ordered (no wait start), or for a Game whose policy has no inactivity rules (no limit → no due time); Norwegian Jinja2 template headed «ØL-spillet» linking to Hjem; times from injected clocks in tests (Issue #63).

**Never:** a second «4 hours before Takeover» reminder; a delivery path of its own; any number of Uker, demand or other Seat's numbers in the mail; naming Tilrettelegging; a UI change; editing the demo Class.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Due | Running Class game, another Student ordered, Seat not ordered, `reminder_due_at <= now` | One `turn_reminder` notice for the holder, turn marked `reminder_queued_at` | No error |
| Repeat sweep | Same turn later | Nothing new (mark + dedupe key) | Idempotent |
| Paused | Game paused at due time | No notice, no mark; queued after the Pause ends if still waited for | Finder skips paused games |
| No wait | Nobody else ordered | No `reminder_due_at`, no notice | — |
| No inactivity policy | Replay/test/simulation Game | No `reminder_due_at` | — |
| Ordered/taken over/finished before mail | Notice queued, then state changes | Section dropped; mail does not mention the game (no mail if nothing else) | Context resolver returns None |
| Quiet hours | Reminder queued at 23:10 Oslo | Mail sent at/after 07:00 | Story 3.5 gating |
| Two games | Two waiting games for one User | One digest mail with both sections | Story 3.5 gathering |

</intent-contract>

## Code Map

- `backend/app/modules/games/rules.py` -- `TurnInputs`/`TurnTimes`/`turn_times` (l.174–267): add `reminder_delay` input and `reminder_due_at` output; set only for a Student occupant with a wait start and a limit in force.
- `backend/app/modules/games/commands.py` -- `_start_waits` (l.1586) is the only writer of wait starts: pass the delay, store `reminder_due_at`. Mirror `announce_insert_time` (l.2241) for the new command `queue_turn_reminder(game_id, seat_id, *, now)`; `_policy`, `_inactivity_limit` reused.
- `backend/app/modules/games/repo.py` -- `set_wait_times` (l.714) gains `reminder_due_at`; mirror `due_insert_times`/`mark_insert_announced` (l.585–612) for `due_turn_reminders` (adds `games.paused_at IS NULL`) and `mark_reminder_queued`.
- `backend/app/modules/games/models.py` -- `seat_turns` (l.237): columns `reminder_due_at`, `reminder_queued_at`, partial index.
- `backend/migrations/versions/0062_turn_reminder.py` -- new, revises 0061.
- `backend/app/modules/games/service.py` -- `due_turn_reminders(now)` like `due_insert_times` (l.218); `turn_reminder_of(session, turn_id, user_id)` like `takeover_of` (l.540), re-checking waiting with `rules.waited_for`.
- `backend/app/modules/sessions/service.py` -- `turn_reminder_mail_context` like `takeover_mail_context` (l.2284).
- `backend/app/modules/messaging/delivery.py` -- register `turn_reminder` as `DIGEST` in `KINDS`.
- `backend/app/modules/ops/sweep.py` -- `DueAction("games.queue_turn_reminder", …)` after the Takeover.
- `backend/app/platform/events/registry.py` -- `games.queue_turn_reminder: {"user"}`; `tests/games/test_registry.py` runner and command set.
- `backend/app/platform/config.py` -- `turn_reminder_delay_minutes = 120`.
- `backend/app/platform/email/templates/kinds/turn_reminder.{txt,html}.j2` -- new, modelled on `takeover_notice`.
- Tests: `tests/games/test_turn_times.py` (pure), new `tests/games/test_turn_reminder.py` (command + sweep, shares `tests/games/test_takeover.class_game`), new `tests/sessions/test_turn_reminder_mail.py` (real Class session via `tests/sessions/test_play.running`, digest at 23:10 → 07:00, two games one mail, render has no «uke»).

## Tasks & Acceptance

**Execution:**
- `backend/app/platform/config.py` -- add the delay setting -- configuration placeholder (FR-27).
- `backend/app/modules/games/rules.py` -- add `reminder_delay`/`reminder_due_at` -- one computation (AD-20).
- `backend/app/modules/games/models.py`, `backend/migrations/versions/0062_turn_reminder.py` -- columns + index.
- `backend/app/modules/games/repo.py` -- store, find, mark.
- `backend/app/modules/games/commands.py` -- write in `_start_waits`; new `queue_turn_reminder`; export in `__all__`.
- `backend/app/modules/games/service.py`, `backend/app/modules/sessions/service.py` -- finder and mail context.
- `backend/app/modules/messaging/delivery.py`, templates -- digest kind and Norwegian mail.
- `backend/app/modules/ops/sweep.py`, `backend/app/platform/events/registry.py` -- due action and topics.
- tests listed in the Code Map -- cover every matrix row.

**Acceptance Criteria:**
- Given a waited-for Student turn, when `rules.turn_times` runs, then `reminder_due_at` = wait start + delay; None for other occupants, no wait start, or no limit.
- Given the sweep at or after `reminder_due_at`, when the Seat still waits in a running, unpaused Class game, then exactly one `turn_reminder` notice exists with key `turn_reminder:<user>:<game>:<week>` and ref the turn id.
- Given `delivery.KINDS["turn_reminder"]`, then its mode is `digest`, and the rendered mail starts «ØL-spillet», says the game waits for the Student's Order, links to `/hjem` and has no «uke».
- Given the frontend, then no screen changes (no e2e spec added; regression specs run).

## Spec Change Log

### 2026-11-22 — Review pass 1 (bad_spec)
- Trigger: edge-case findings E2/E7 — a reminder queued before a Pause began was dropped at digest build (paused) while the turn stayed marked, so the Student got no reminder that Week after the Pause.
- Amended: Design Notes — no drop for a Pause at build time; also the text part links to Hjem, `queue_turn_reminder` returns the `enqueue` result, the delay is bounded, and tests cover the finder after a Week change and the reminder time written by a Guided-Week view.
- Known-bad state avoided: a lost reminder after a Pause; a text-only mail without a link; a silent True on a used dedupe key; sweeps re-reading past-Week turns unnoticed.
- KEEP: the whole first-pass design — `reminder_due_at`/`reminder_queued_at` with partial index (migration 0062), `rules.turn_times` computing it from wait start + config delay when a limit is in force, `_start_waits` as the only writer, the finder skipping paused/non-running games and past Weeks, the command's lock/mark/re-check with `rules.waited_for`, dedupe key `turn_reminder:<user>:<game>:<week>` with `ref` = turn id, the digest kind registration, the Norwegian templates, the registry entry `{"user"}`, and the test files.

## Review Triage Log

### 2026-11-22 — Review pass
- verdicts: 31 findings — high 0, medium 2, low 15, false 14, maybe-false 0
- findings:
  - `[false]` `[reject]` B1 reminder time not recomputed on reclaim/occupant change — a Reclaim takes effect only when the next Week opens (a new turn); within a Week a Seat only goes Student→AI, so no Student regains a turn mid-Week.
  - `[false]` `[reject]` B2 mark written before transient checks — the marked conditions are terminal: a turn in the open Week of a Game that left `running` never returns to it, the policy is fixed, a Student occupant always has a `user_id`.
  - `[low]` `[reject]` B3 reminder later than the in-room Takeover / fires at Pause end — the Takeover makes the Seat no longer waited for, so the sweep marks it quietly; a reminder after the Pause ends is the intended hold. No user harm; clamping adds branches.
  - `[low]` `[bad_spec]` B4 text part has no Hjem URL — real; folded into the pass-1 amendment (txt links to `url('/hjem')`, tests assert both parts).
  - `[low]` `[reject]` B5 duplicated role map / `game_number` None — same pattern as `takeover_notice`; Class games always carry a number.
  - `[false]` `[reject]` B6 digest unsuited to a nudge / empty digest — digest is the spine's founder decision (AD-9); an all-stale digest is skipped as `stale` (Story 3.5), and the taken-over test shows no mail.
  - `[low]` `[reject]` B7 roster load per notice / duplicated waiting checks — same as every sibling mail context; a handful of notices per digest; both checks call `rules.waited_for`.
  - `[low]` `[bad_spec]` B8 `enqueue` result ignored — unreachable today (nothing clears the mark) but a direct fix; folded into the amendment.
  - `[low]` `[reject]` B9 migration coverage / no backfill — `test_migrations` runs every step down and up; the suite writes `reminder_queued_at` through the trigger; no backfill is the documented choice (no production data yet).
  - `[false]` `[reject]` B10 brittle tests / loosened registry check — the 2-hour assertion pins the placeholder on purpose; the registry's `game` id check is skipped only for a command not registered for `game`, which is this one alone.
  - `[false]` `[reject]` B11 no opt-out or docs / stray `policy.py` — no notice kind has preferences (outside the story); `policy.py` is a known leftover the orchestrator told this run to ignore.
  - `[low]` `[bad_spec]` E1 delay has no upper bound — direct fix `le=10080`; folded into the amendment.
  - `[medium]` `[bad_spec]` E2 a Pause between queueing and the digest drops the Week's only reminder — real (`turn_reminder_of` returned None when paused while the turn stayed marked); Design Notes amended.
  - `[false]` `[reject]` E3 a digest already sent today holds the reminder to the next day — that is the story's «at most one mail per User per day» (FR-27, AD-9).
  - `[low]` `[reject]` E4 `game_number` None — as B5.
  - `[low]` `[bad_spec]` E5 `enqueue` result ignored — as B8.
  - `[low]` `[reject]` E6 no backfill — as B9.
  - `[medium]` `[bad_spec]` E7 spec claim about reminders after a Pause — same root cause as E2.
  - `[false]` `[reject]` E8 the 2-hour reminder may arrive a day later — the story makes it a digest kind; the delay is when it is queued.
  - `[low]` `[bad_spec]` V1 finder's open-Week filter untested — pre-verified gap; test added in the amendment.
  - `[low]` `[defer]` V2 archived-Class / unregistered branches of the mail context untested — pre-verified gap; the guard pair is the repo-wide convention of every mail context, equally unpinned elsewhere.
  - `[low]` `[defer]` V3 registry `-1` slice cannot see extra topics — pre-verified gap; low impact.
  - `[false]` `[reject]` V-O1 AI-held Seat reclaimed gets no reminder — the Reclaim applies from the next Week, whose turn gets its own wait start.
  - `[low]` `[reject]` V-O2 `_start_waits` leaving NULL for a simulation only unit-tested — `_start_waits` passes no limit for such a policy (`_inactivity_limit`), and `turn_times` is tested for it.
  - `[false]` `[reject]` I1 text part lacks the link — counted under B4.
  - `[false]` `[reject]` I2 the mail test writes due times directly — required: time is injected, never the host's (Issue #63); the derivation is tested in `test_turn_reminder.py`.
  - `[low]` `[bad_spec]` I3 the Guided-Week reminder time is not asserted before it is overwritten — one-line assertion added in the amendment.
  - `[false]` `[reject]` I4 Pause read as «held», not «never» — both satisfy «no reminder is queued» for a paused game; the hold is recorded as a decision.
  - `[false]` `[reject]` I5 extra column `reminder_queued_at` — needed to act once (AD-9 idempotent due actions).
  - `[false]` `[reject]` I6 extra build-time drops (archived, unregistered) — the convention of every mail context.
  - `[false]` `[reject]` I7 stray file, founder markers, no frontend — known leftover; the placeholder is in config and `open-assumptions.md`; the story changes no screen.

### 2026-11-22 — Review pass (loop 1)
- verdicts: 29 findings — high 0, medium 1, low 17, false 11, maybe-false 0
- findings:
  - `[medium]` `[patch]` P2-B1 turns whose Student ordered before the reminder time stay in the partial index forever (unqueued), so the finder's index scan grows every Week — fixed: `repo.close_reminders` marks a completed Week's unqueued reminders in `commands._step`; `test_the_finder_leaves_a_past_week_alone` asserts 0 left and still pins the finder's open-Week filter.
  - `[low]` `[reject]` P2-B2 finder lacks an ordered/occupant filter — each such open-Week turn costs one lock once, then is marked; a guided Week sets `ordered_at` at opening, so an SQL `ordered_at` filter would be wrong anyway.
  - `[false]` `[reject]` P2-B3 «venter på bestillingen din» while paused contradicts the finder — the game does wait for the Student (only an Order or the Lecturer ends the Pause); keeping a queued reminder is the pass-1 decision.
  - `[false]` `[reject]` P2-B4 reclaim/occupant change — carried B1.
  - `[low]` `[reject]` P2-B5 delay not validated against the limits / no tracking issue — carried B3; the placeholder is already in `open-assumptions.md`, and this run does not edit issues.
  - `[false]` `[reject]` P2-B6 digest delivery lags the 2-hour delay — carried B6/E8.
  - `[low]` `[reject]` P2-B7 duplicated eligibility checks and role map — carried B7; the Role set is fixed.
  - `[low]` `[reject]` P2-B8 test coupling and untested bounds/in-room/later Week — the 2-hour assertion pins the placeholder (B10); in-room is covered in `test_turn_times.py`; the Week is part of the dedupe key; bound validation is pydantic's.
  - `[false]` `[reject]` P2-B9 registry test loosened — carried B10.
  - `[low]` `[reject]` P2-B10 copy lacks waited time / Takeover hint; quiet paths unlogged — the mail must reveal no limit (Tilrettelegging, FR-14); logs on quiet marks add noise for no user.
  - `[low]` `[reject]` P2-B11 no CHECK pairing the columns; trigger docstring — `reminder_queued_at` is only ever written for a turn with a due time; the docstring lists guarded columns only.
  - `[low]` `[reject]` P2-E1 `game_number` None — carried B5/E4.
  - `[false]` `[reject]` P2-E2 mark before checks — carried B2.
  - `[low]` `[defer]` P2-E3 registry `-1` slice — carried V3.
  - `[low]` `[reject]` P2-E4 reminder right after a Lecturer resumes a long Pause — carried B3 (the intended hold).
  - `[low]` `[patch]` P2-V1 the mail context's `waited_for` clause untested with the Week still open — pre-verified gap; `test_a_seat_no_longer_waited_for_is_marked_quietly` now asserts `turn_reminder_of` is None for Wholesaler after its Order while Factory still waits.
  - `[low]` `[defer]` P2-V2 archived/unregistered branches — carried V2.
  - `[low]` `[defer]` P2-V3 registry cannot see extra topics — carried V3.
  - `[low]` `[reject]` P2-V-O1 simulation `_start_waits` path — carried V-O2.
  - `[low]` `[reject]` P2-V-O2 migration test only bumps HEAD — carried B9.
  - `[false]` `[reject]` P2-I1 23:10 forced by SQL — carried I2.
  - `[false]` `[reject]` P2-I2 ordered/finished drops checked at the function, finished set by SQL — the pipeline drop is shown by the taken-over case; playing to the end would cost seconds per test.
  - `[false]` `[reject]` P2-I3 Pause after queueing decided by the diff — carried I4.
  - `[low]` `[reject]` P2-I4 no-inactivity path only unit-tested — carried V-O2.
  - `[low]` `[patch]` P2-I5 «no Uker» not checked on the HTML part — the render test now asserts it on `mail.html` too.
  - `[false]` `[reject]` P2-I6 registry test changed — carried B10.
  - `[false]` `[reject]` P2-I7 `/hjem` route untested — an existing route used by `message` and `takeover_notice`.
  - `[low]` `[reject]` P2-I8 environment override untested — pydantic settings, as every other setting.
  - `[false]` `[reject]` P2-I9 no frontend — carried I7.

## Design Notes

- The delay ignores Tilrettelegging and the in-room limit: a reminder reveals no limit, and a Seat taken over first is dropped by the waiting re-check. Since the wait start never moves and the delay is not scaled, recompute paths need not touch `reminder_due_at`.
- A paused game is left unmarked, so the reminder goes once the Pause ends if the Seat still waits (FR-27 ASSUMPTION: no reminder during a Pause). A notice already queued before a Pause began is **not** dropped at build time for the Pause: the mail drops a game only when the Seat no longer waits (ordered, taken over, Week moved on, game no longer running), the Class is archived or the Student is no longer registered. Otherwise a Pause that starts between queueing and the morning digest would lose the Week's only reminder, since the turn is already marked.
- The text part of the mail carries the Hjem URL too (`url('/hjem')`), like `message.txt.j2`; tests assert it in both parts.
- `queue_turn_reminder` returns what `notify.enqueue` returned, so a used dedupe key counts as nothing queued. The delay setting is bounded to one week (`le=10080`).
- The command bumps no version: nothing a game view shows changes; `notify.enqueue` emits `user:<id>`.
- `seat_weeks` does not copy the reminder times: they are notification state, not play history.
- Epic context validity: the spine is newer only because Story 8.12 appended its «Decided in» record in the same commit; the context was used as is.

## Verification

**Commands:**
- `cd backend && uv run pytest tests/games/test_turn_times.py tests/games/test_turn_reminder.py tests/sessions/test_turn_reminder_mail.py tests/games/test_registry.py tests/messaging -q` -- expected: pass.
- Full gates before commit: backend suite `--maxprocesses=8`, ruff, frontend typecheck, Vitest, `lint:colours`, `check:copy`, build, Playwright (`live-updates`, play-screen, `homes`, axe).

## Auto Run Result

Status: done
Blocking condition: none

**Summary.** A Student the Class game has waited for gets a `turn_reminder` digest notice once the wait has lasted the reminder delay (2-hour placeholder, `turn_reminder_delay_minutes`). `games.rules.turn_times` computes `seat_turns.reminder_due_at` (wait start + delay, Student occupant, a limit in force) and `_start_waits` stores it. The sweep's `games.queue_turn_reminder` finds due, unqueued turns in the open Week of running, unpaused Games and calls `games.commands.queue_turn_reminder`. Under the Game lock that command marks the turn and, while `rules.waited_for` holds, calls `notify.enqueue(user, "turn_reminder", "turn_reminder:<user>:<game>:<week>", ref=turn id)`. The digest delivery of Story 3.5 gathers and times the mail. At build time `sessions.turn_reminder_mail_context` leaves out a game that no longer waits for the Student. The mail is a Norwegian template with a Hjem link and no Uker. A completed Week closes its unqueued reminders. No screen changes.

**Files.**
- `backend/migrations/versions/0062_turn_reminder.py`: adds `reminder_due_at`, `reminder_queued_at` and a partial index.
- `backend/app/modules/games/models.py`: the same columns and index on `seat_turns`.
- `backend/app/modules/games/rules.py`: `TurnInputs.reminder_delay` and `TurnTimes.reminder_due_at`.
- `backend/app/modules/games/commands.py`:
  - `_start_waits` writes the reminder time;
  - `_step` closes the completed Week's reminders;
  - adds `TURN_REMINDER_NOTICE` and `queue_turn_reminder`.
- `backend/app/modules/games/repo.py`:
  - `set_wait_times(reminder_due_at)`;
  - adds `due_turn_reminders`, `mark_reminder_queued`, `close_reminders` and `turn_with_role`.
- `backend/app/modules/games/service.py`: adds `due_turn_reminders`, `turn_reminder_of` and `TurnReminderInfo`.
- `backend/app/modules/sessions/service.py`: adds `turn_reminder_mail_context`.
- `backend/app/modules/messaging/delivery.py`: registers `turn_reminder` as a `digest` kind.
- `backend/app/modules/ops/sweep.py`: adds the `games.queue_turn_reminder` due action after the Takeover.
- `backend/app/platform/events/registry.py`: `games.queue_turn_reminder` emits `{"user"}`.
- `backend/app/platform/config.py`: `turn_reminder_delay_minutes` = 120 (1 to 10080).
- `backend/app/platform/email/templates/kinds/turn_reminder.{txt,html}.j2`: the Norwegian draft copy.
- Tests:
  - `tests/games/test_turn_reminder.py` and `tests/sessions/test_turn_reminder_mail.py` are new;
  - `tests/games/test_turn_times.py` and `tests/games/test_registry.py` are extended;
  - `tests/test_migrations.py` has HEAD 0062.

**Review.** Four layers on Sonnet (blind, edge case, verification gap, intent). All hand-backs dropped, so findings were read from `review-*-8-13*.md` in the session scratchpad.
- Pass 1 had 31 findings and led to one bad_spec loop. A Pause between queueing and the digest dropped the Week's only reminder. The low items B4, B8, E1, V1 and I3 were folded into the same amendment.
- Pass 2 had 29 findings:
  - 3 patches applied: index growth, a medium, fixed by closing reminders at Week completion; the `waited_for` mail-context test, low; the HTML «no Uker» check, low.
  - 2 deferred items in the frontmatter: V2 and V3.
  - Every rejection and its reason is in the triage log.
- Follow-up review: `false` (one medium and two low patched on this pass, none high).

**Verification.**
- Targeted tests passed.
- Full backend suite (`-n 8 --maxprocesses=8`): 3081 passed. One run had a single failure, `tests/sessions/test_pause_view.py::test_a_student_pauses_and_another_students_order_ends_it`. It passed alone and in the next full run. It uses no reminder path, so it is a load flake.
- ruff check and format were run on the changed files.
- Frontend (unchanged by this story): `typecheck`, Vitest 902 passed, `lint:colours`, `check:copy` and `build` all passed.
- After rebuilding the stack, Playwright (`--workers=4`) ran `live-updates`, `homes`, `order-confirm` (play screen, axe) and `takeover`: 47 passed.
- New tests over 1 s under load: `test_two_waiting_games_give_one_morning_mail_without_any_week` (about 2.6–3.3 s; a real Class session, two games and five sweeps) and `test_a_reminder_whose_seat_was_taken_over_gives_no_mail` (about 1 s).

**Decisions taken without the founder.**
- A Pause holds the reminder: it is queued after the Pause ends if the Seat still waits. A reminder queued before a Pause began is still mailed.
- The delay is not scaled by Tilrettelegging and is not moved by «I rommet».
- No backfill for waits that started before migration 0062.
- `seat_weeks` does not copy the reminder times.
- Draft copy: «Spill N i Klassen X venter på bestillingen din som <Rolle>. Gruppen spiller videre når du har bestilt. Du bestiller fra Hjem.» Subject (immediate rendering only) «Spillet venter på deg».
- The epic context was used even though the spine is newer: the spine change was only Story 8.12's «Decided in» record.
- Implementation was done in this context, not by a subagent, on the orchestrator's instruction.

**Residual risks.**
- The 2-hour delay is a placeholder. With «I rommet» (10-minute limit) the reminder never fires, because the Takeover comes first.
- The digest may deliver the reminder up to a day after it was queued, by design (AD-9).
- An untracked `walkthrough-chart.tsx` from another agent appeared at the repo root during this run. It was not touched or staged.
