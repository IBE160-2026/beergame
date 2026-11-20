---
title: 'Story 5.11: Lock the Class session at the Start date'
type: 'feature'
created: '2026-11-20'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-5-context.md'
  - '{project-root}/backend/app/modules/sessions/README.md'
warnings: ['oversized']
deferred:
  - summary: >-
      The Klasseøkt cannot tell a refused lock (provider_key_missing) from one waiting for the next sweep.
    evidence: |-
      ClassSessionOut carries only locked_at; both states show lock.pending. Owners and Admins learn the cause only from the mail. A lock_refused field and copy would need a stored refusal state.
    location: >-
      backend/app/modules/sessions/schemas.py (ClassSessionOut), frontend class-session-page.tsx
    severity: medium
  - summary: >-
      A lock that fails for a reason other than provider_key_missing (a pin provider raising, invalid stored settings) is retried each minute and tells nobody.
    evidence: |-
      lock_due catches only ProviderKeyMissing; sweep.run logs sweep_item_failed and goes on. No pin provider exists yet (Epics 6, 9, 10, 11 add them), so it is unreachable today.
    location: >-
      backend/app/modules/sessions/service.py lock_due
    severity: medium (unverified)
  - summary: >-
      A session of an archived Class with LLM players and no usable key is refused and logged every minute, forever.
    evidence: |-
      repo.due_locks does not leave out archived Classes; _tell_lock_refused tells nobody for them (tested), but lock_due logs class_session_lock_refused each sweep. Leaving them out needs a join on classes or a classes.service scope helper.
    location: >-
      backend/app/modules/sessions/repo.py due_locks
    severity: low
baseline_revision: '5ca664d0fb82a38befe212550b2c1c30b602aec3'
---

<intent-contract>

## Intent

**Problem:** A Class session is "locked" only because its Start date has passed. Nothing freezes the settings, the model config or the content versions. No sweep acts at the Start date. A locked Klasseøkt still shows «Lagre Klasseøkt» and editable inputs for frozen dates (Issue #103).

**Approach:** Add `locked_at` and a frozen `snapshot` to `class_sessions`. `sessions.service.lock` sets both in one transaction from `build_snapshot`, which includes an open `pins` map filled by registered pin providers. Add `sessions.lock` and `identity.purge_expired_roster_uploads` as due actions of `ops.sweep`. In production, LLM players with no usable provider key make the lock refuse (`provider_key_missing`) and notify the owners and the Admins once. Once locked, the Klasseøkt shows every frozen value, and every passed date, as text. Its only save is «Lagre frister», and it shows only while a deadline can still move.

## Boundaries & Constraints

**Always:**
- One transaction per lock: row lock on the session, `locked_at`, `snapshot`, `ai.config.mark_referenced` (LLM players), and `session:<id>`. A second lock of a locked session changes nothing.
- The snapshot holds `settings` (with `schema_version`), `demand_series` (from `engine.demand_series`), `demand_seed`, `rules_version` (`engine.RULES_VERSION`) and `session_runtime`. These are the names of `games.models.SNAPSHOT_COLUMNS`. `session_runtime` is a `games.SessionRuntime`: AI mode, Effort level, model config id, the default Rule-based and Play-guard parameter sets, `inactivity_limit_hours`, `prompt_versions` (the config's `prompts`), and `pins` (name → value from each provider).
- `is_locked` is true when `locked_at` is set or the Start date has passed. `lock` locks on call, whatever the date, so Epic 8 can start early.
- The sweep finds only sessions with `start_at <= now` and `locked_at IS NULL`. It passes ids only and handles one item per transaction.
- `provider_key_missing` applies when the AI mode is `llm` and `adapters.availability(spec, APP_ENV).kind == "refused"` (in local, test and ci the mock always answers). Nothing is stored. Each owner of the Class and each active Admin gets one immediate notice, deduped per session and per User.
- Deadlines that have not passed and Lab hours stay editable after the lock. The api's rules from 5.2 to 5.10 are unchanged.

**Never:** No new cron, sweeper or job. No Class-game snapshot, no AI fill and no automatic allocation (those are Story 5.12). No sleeps in tests, and no comparison of database time with host time.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Due lock | start passed, not locked, Rule-based | `locked_at = now`, snapshot stored, `session:<id>` | — |
| Swept twice | same due session, two sweeps | one lock (second run counts 0) | — |
| Not due | start in future or unset | not found by the sweep | — |
| LLM, mock env | `llm`, local/test | locks; config marked referenced; runtime has config, level, prompt versions | — |
| LLM, production, no key | `llm`, availability refused | nothing frozen; notices to owners + Admins once; next sweep tries again | `provider_key_missing` logged |
| Pin provider | dummy provider registered | its value in `snapshot.session_runtime.pins[name]` | — |
| Locked screen | `locked: true`, a deadline not passed | frozen values and passed dates as text; «Lagre frister» saves the dates | refusal copy as before |
| Locked screen, all passed | every date passed | no save button at all | — |

</intent-contract>

## Code Map

- `backend/migrations/versions/0040_class_session_lock.py` -- new: `locked_at` timestamptz NULL, `snapshot` JSONB NULL, CHECK `(locked_at IS NULL) = (snapshot IS NULL)`.
- `backend/app/modules/sessions/models.py` -- the two columns and the check.
- `backend/app/modules/sessions/repo.py` -- `due_locks(s, now)` (ids, ordered), `set_locked(s, id, locked_at, snapshot)`.
- `backend/app/modules/sessions/service.py:410` `is_locked` -- add `locked_at`. New `register_pin_provider`, `build_snapshot`, `lock`, `due_locks`, `lock_refused_mail_context`, and `LOCK_REFUSED_NOTICE`. `get_session` returns `locked_at`.
- `backend/app/modules/sessions/schemas.py` -- `ClassSessionOut.locked_at`.
- `backend/app/modules/games/schemas.py:86` `SessionRuntime` -- optional `inactivity_limit_hours`, `prompt_versions`, `pins` (defaults keep old rows valid).
- `backend/app/modules/games/commands.py:149-172` -- public `default_runtime(...)`, reusing `_rule_based_params`/`_play_guard_params`, so sessions builds the same runtime as an at-creation Game.
- `backend/app/modules/ops/sweep.py:48` `DUE_ACTIONS` -- add `sessions.lock` and `identity.roster_purge`.
- `backend/app/modules/identity/service.py` -- `active_admins(session)`. `classes/service.py` -- `owners_of(session, class_id)`.
- `backend/app/modules/messaging/delivery.py` -- `class_session_lock_refused` IMMEDIATE with a context resolver. The templates go in `platform/email/templates/kinds/`.
- `backend/app/platform/events/registry.py` -- `sessions.lock: {session, user}`.
- `frontend/src/modules/sessions/class-session-page.tsx`, `date-fields.tsx`, `api.ts`, `frontend/src/copy/nb.ts` -- the locked view.
- Tests: `backend/tests/sessions/test_lock.py` (new), `tests/test_migrations.py` (HEAD 0040, folded into the 0037–0039 test), `frontend/e2e/class-session-lock.spec.ts` (new), and an update to `class-session-dates.spec.ts:145`.

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0040_class_session_lock.py`, `sessions/models.py`, `sessions/repo.py` -- columns, check, queries.
- `backend/app/modules/games/schemas.py`, `games/commands.py` -- runtime fields and `default_runtime`.
- `backend/app/modules/sessions/service.py`, `schemas.py`, `README.md` -- lock, snapshot, pin providers, refusal notices, `locked_at` out.
- `backend/app/modules/identity/service.py`, `repo.py`, `classes/service.py` -- recipients.
- `backend/app/modules/ops/sweep.py`, `messaging/delivery.py`, templates, `events/registry.py` -- wiring.
- `backend/tests/sessions/test_lock.py`, `tests/test_migrations.py` -- api tests for the matrix rows (frozen clock).
- `frontend/src/modules/sessions/*`, `frontend/src/copy/nb.ts` -- locked view (Issue #103).
- `frontend/e2e/class-session-lock.spec.ts`, `class-session-dates.spec.ts` -- the screen, locked (route-faked as in the other specs), with axe.

**Acceptance Criteria:**
- Given a due session, when `sweep.run` runs twice, then exactly one lock is stored and `session:<id>` is emitted once.
- Given a locked session, when the Lecturer saves a changed setting, then 409 `session_locked` (as before), and `GET` returns `locked: true` and `locked_at`.
- Given a session locked early through `service.lock` before its Start date, then `is_locked` is true and frozen fields answer 409 `session_locked`.
- Given a locked session with a deadline still ahead, when the Lecturer opens the Klasseøkt, then Game settings, Demand pattern, AI mode, Effort level, Debrief mode, Obligatorisk, the share and the Inactivity limit are text. A passed Startdato is text with «Passert». The deadline still ahead is an input, and the button reads «Lagre frister», not «Lagre Klasseøkt».
- Given the sweep, then it also purges expired Roster staging rows.

## Spec Change Log

## Review Triage Log

### 2026-11-20 — Review pass
- verdicts: 50 findings — high 0, medium 8, low 17, false 15, maybe-false 10
- findings:
  - `[maybe-false]` `[defer]` blind: lock_due catches only ProviderKeyMissing; other failures retry silently — sweep.run isolates items (logs, goes on); no pin provider exists yet. Deferred (medium, unverified).
  - `[low]` `[patch]` blind: a deleted config / mock-in-production is worded as a missing key — a referenced config cannot be deleted (pinned, so referenced); the mail now says «En Admin må sette den opp» instead of naming the key.
  - `[low]` `[defer]` blind: archived Classes retried forever — real, log noise only; deferred.
  - `[low]` `[reject]` blind: no backoff or refusal state — one small query per minute; the UI half is deferred below.
  - `[medium]` `[defer]` blind: the page cannot show a refused lock — needs a stored refusal state and an API field; deferred.
  - `[low]` `[reject]` blind: mail context does not re-check owner/Admin at send time — the kind is immediate, so the window is under a minute; a fix adds guards for a negligible case.
  - `[low]` `[reject]` blind: mail has no link, one text for all — copy is [ASSUMPTION] draft; wording improved under the patch above.
  - `[false]` `[reject]` blind: no index for due_locks — class_sessions holds one row per session; no measurable cost.
  - `[false]` `[reject]` blind: «oldest first» docstring wrong — ids are UUIDv7, which sort by creation (repo `_number` relies on the same).
  - `[false]` `[reject]` blind: assert in sweep actions — same pattern as the existing ratelimit action; items come from find().
  - `[false]` `[reject]` blind: is_locked duplicates _value — `_value` raises KeyError on a mapping without locked_at; the .get is intentional.
  - `[low]` `[reject]` blind: config fetched twice in lock — same transaction, same immutable row; negligible.
  - `[low]` `[reject]` blind: build_snapshot does not re-check the stored Effort level — checked at save; referenced configs never change.
  - `[false]` `[reject]` blind: roster purge is unrelated scope — it is in Story 5.11's first AC.
  - `[medium]` `[patch]` blind: missing backend tests (archived Class, Assistant, inactive Admin) — added to test_lock.py.
  - `[false]` `[reject]` blind: locked save body sends passed dates — unchanged dates are never judged (judge_dates, to the minute); the e2e save passes against the real api.
  - `[maybe-false]` `[reject]` edge: config row missing raises ProviderKeyMissing — unreachable: the config was pinned, so referenced, so never deleted.
  - `[low]` `[patch]` edge: no adapter / router without routing is called a missing key — same wording patch as above.
  - `[maybe-false]` `[defer]` edge: a failure other than ProviderKeyMissing tells nobody — same as the first deferred item.
  - `[low]` `[defer]` edge: archived Class refused and logged every minute — same deferred item.
  - `[maybe-false]` `[reject]` edge: lock() locks an archived Class's session — harmless, nothing plays; a recorded design decision.
  - `[false]` `[reject]` edge: owners_of includes deactivated owners — identity.mail_recipient returns None for an inactive User, so no mail goes.
  - `[low]` `[reject]` edge: recipient no longer owner/Admin at send time — as the blind row above.
  - `[maybe-false]` `[reject]` edge: NULL effort_level falls back to the spec's first level — only rows stored before migration 0034; the first level is the default by definition.
  - `[medium]` `[patch]` edge: after an early lock the Startdato still moves — save now answers 409 session_locked {start_at: locked} when locked_at is set; api test added.
  - `[medium]` `[patch]` edge: after an early lock the UI keeps Startdato as a field — frozenDates() shows it as text with «Klasseøkten er låst. Startdatoen kan ikke flyttes.»; Vitest and e2e added.
  - `[maybe-false]` `[reject]` edge: claim "refusal only for a missing key" — wording patched; never falling back is the AC's.
  - `[medium]` `[patch]` verification-gap: Lærerhjem early-lock path untested — test_an_early_lock_ends_the_lecturer_homes_wait_for_an_allocation added.
  - `[medium]` `[patch]` verification-gap: the lock-refused mail is never rendered — the test now drains the sweep and asserts both mails' subject and text.
  - `[low]` `[patch]` verification-gap: recipients tested with owner + one Admin only — Assistant, inactive Admin and archived Class added.
  - `[maybe-false]` `[reject]` verification-gap other: missing config named as a missing key — as the edge row above.
  - `[low]` `[defer]` verification-gap other: archived Class retried forever — same deferred item.
  - `[false]` `[reject]` intent: «Lagre frister» sends ai_mode and all dates — the api accepts unchanged values; only deadlines can change.
  - `[maybe-false]` `[reject]` intent: e2e fakes the lock — no api route locks; the real lock is pinned by api tests, as in specs 5.3 to 5.10.
  - `[false]` `[reject]` intent: Lab hours on a locked session untested — class-session-lab-hours.spec.ts:189 covers it.
  - `[low]` `[patch]` intent: "same shape" untested — test_the_snapshot_runtime_has_the_shape_of_a_games_runtime added.
  - `[maybe-false]` `[reject]` intent: a real provider with no key is approximated — availability() is covered by tests/ai; may_answer in production tested with the mock.
  - `[low]` `[reject]` intent: dates as text also for archived/Assistant views — deliberate: one rendering for a date that cannot change; recorded as a decision.
  - `[false]` `[reject]` intent: the recipients reading — documented decision (owners and every active Admin).
  - `[false]` `[reject]` intent: the pending state is not in the AC — is_locked is true then and the screen follows it.
  - `[low]` `[patch]` visual 1: «Frister som ikke er passert…» when none is left — now «Labtimer kan fortsatt endres.».
  - `[low]` `[reject]` visual 2: two wordings (stamped vs pending) — two real states; both name what is frozen.
  - `[maybe-false]` `[reject]` visual 3: empty «Fordeling» — the allocation block of 5.8; Story 5.12 fills it after the lock; the shot was taken before its fetch settled.
  - `[medium]` `[patch]` visual 4: «Lagre frister» far from its fields — locked, it now sits in the Datoer section under the fields; e2e asserts it.
  - `[low]` `[reject]` visual 5: input shows US format — the headless browser's locale on a native datetime-local; pre-existing.
  - `[low]` `[reject]` visual 6: no "now" mark on the timeline — the Datolinje of 5.2, outside this story.
  - `[low]` `[reject]` visual 7: Innsatsnivå styled inline — Story 5.5's design, pre-existing.
  - `[low]` `[reject]` visual 8: «Tidene er norsk tid.» placement — pre-existing (5.2).
  - `[low]` `[reject]` visual 9: text vs input baseline in one row — cosmetic.
  - `[false]` `[reject]` visual 10: phone timeline has no scroll hint — it has the fading edge of Issue #98 (tested in class-session-dates.spec.ts).


## Design Notes

Founder-level decisions taken here (recorded for the hand-back):
- A `refused` availability of any kind (no key, no adapter, a router without routing) counts as `provider_key_missing`. The lock never falls back to Rule-based.
- The refusal notice is `immediate`, not `digest`, because the Start date has passed and the games are waiting. Its dedupe key is `class_session_lock_refused:{session}:{user}`, so each User gets one notice per session. Its mail is skipped once the session has locked.
- Sessions of archived Classes are locked too. The refusal mail is skipped for an archived Class.
- Locked view: the save button is renamed «Lagre frister» and sends the dates only. It disappears when no date can move. Dates that cannot be edited (passed, or for an Assistant) render as text, not as read-only inputs. A lock line «Låst {dato}.» stands under the title.
- `SessionRuntime` stays at `schema_version` 1, and its new fields have defaults, so stored Games still validate.

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/sessions/test_lock.py tests/ops -q` -- expected: pass, each test under 1 s
- `cd backend && uv run pytest -q && uv run ruff check . && uv run ruff format --check .` -- expected: pass
- `cd frontend && npm run typecheck && npm test && npm run check:copy && npm run lint:colours && npm run build` and Playwright -- expected: pass

## Auto Run Result

Status: done

**Summary.** The sweep's `sessions.lock` locks a Class session once its Start date has passed. One transaction sets `locked_at` and stores the frozen snapshot from `build_snapshot`: settings, demand series, seed, `rules_version`, and a `SessionRuntime` with AI mode, Effort level, Inactivity limit, config id, prompt versions and an open `pins` map filled by registered pin providers. The same transaction marks the model config referenced and emits `session:<id>`. `lock` also locks early, for Epic 8. When the players are LLM players and the provider may not answer (production with no key), the lock is refused. Nothing is frozen, each owner and each active Admin gets one immediate notice, and the next sweep retries. The sweep also purges expired Roster staging rows. Once locked, the Klasseøkt shows every frozen value and every frozen date as text. «Lagre Klasseøkt» is gone. «Lagre frister» sits under the date fields, only while a deadline can move (GitHub issue 103).

**Files.**
- `backend/migrations/versions/0040_class_session_lock.py`: `locked_at`, `snapshot`, and a CHECK.
- `backend/app/modules/sessions/{models,repo,schemas,service}.py` and `README.md`: the lock, the snapshot, pin providers, refusal notices, `locked_at` in the read, and the Startdato frozen after an early lock.
- `backend/app/modules/games/{schemas,commands}.py`: `SessionRuntime` gets optional `inactivity_limit_hours`, `prompt_versions` and `pins`; new `default_runtime`.
- `backend/app/ai/config.py`: `may_answer`.
- `backend/app/modules/identity/{repo,service}.py`: `active_admins`.
- `backend/app/modules/classes/service.py`: `owners_of`.
- `backend/app/modules/ops/sweep.py`: two due actions.
- `backend/app/modules/messaging/delivery.py` and two templates: the immediate kind `class_session_lock_refused`.
- `backend/app/platform/events/registry.py`: `sessions.lock`.
- `frontend/src/modules/sessions/{class-session-page.tsx,date-fields.tsx,dates.ts}` and `frontend/src/copy/nb.ts`: the locked view. `openapi.json` and `schema.ts` regenerated.
- Tests:
  - new: `backend/tests/sessions/test_lock.py` and `frontend/e2e/class-session-lock.spec.ts`
  - `test_migrations.py`: 0040 folded into the 0037–0040 test
  - `tests/games/test_create.py`: the three new runtime keys
  - updated e2e specs: dates, choices, demand, settings, class-session
  - `dates.test.ts`

**Review.** 50 findings. 11 were patched, 3 deferred (listed in the frontmatter), and the rest rejected with reasons in the triage log.
- Patched, medium (6): the Startdato frozen after an early lock, in the api and on screen; the Lærerhjem test; the refusal mail rendered in a test; «Lagre frister» moved under the date fields; the recipient tests.
- Patched, low (5): the mail wording; the line that names only Labtimer; the same-shape test; the recipient edge cases.

An independent visual reviewer checked four screenshots at 1440 and 390 px in place of the founder. Every requirement held, and its two material remarks are patched.

**Follow-up review: true.** More than one medium was patched. The unverified risk is the new 409 `session_locked {start_at}` after an early lock: no caller locks early until Epic 8, so only the api test and a faked screen state cover it.

**Verification.**
- Backend: `uv run pytest -q` → 2510 passed. `ruff check` and `ruff format --check` are clean. Each new test runs in under 0.5 s.
- Frontend: typecheck, Vitest (431 passed), check:copy, lint:colours and build pass.
- Playwright, full suite: 256 passed, 1 failed. The failure is the `system-states` «ended session» test, a flake under load that passes on its own (18/18). The allocation 360 px move flaked once earlier and also passes on its own.
- Migration 0040 is new. No migration that had already run was changed.

**Residual risks.** A real provider with no key is approximated by the mock in production and by a patched `may_answer`. The e2e tests fake the locked answer, because no api route locks a session.
