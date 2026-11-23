---
title: 'Story 15.11: Errors reach an error tracker without personal data, and backup and monitoring are laid out for decision'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: 'c2c2b9d9f07ed6b742b9bdd85e72aeeba2ffb097'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-15-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** An exception in the api or a worker reaches only the logs: no error tracker can be wired in without new code, nothing shows a restored database still holds verifiable Games (NFR-4, AD-4), and the founder's open operations decisions (backup level, error-tracking and uptime tool, contact, sub-processors) live scattered in the spine and issue #28.

**Approach:** One error-reporting adapter in `backend/app/platform/error_reporting.py`, configured by `ERROR_TRACKER_DSN`, that builds each report from structure (error type, stack frames, allowlisted ids) so no message, local, header or body can leave; a recording mock when the DSN is empty outside production. The api's request log middleware and the worker's failure middleware hand it unhandled exceptions beside the existing `error_events` count. `python -m app.ops.verify_restore <database_url>` replays every finished Game of a restored copy in a read-only transaction. Two repository documents, `docs/ops/readiness.md` and `docs/ops/sub-processors.md`, lay out the decisions and checks, each open with its issue number.

## Boundaries & Constraints

**Always:**
- `Settings.error_tracker_dsn: str = ""` (env `ERROR_TRACKER_DSN`). A non-empty value must parse as `<scheme>://<public_key>@<host>[:port][/<prefix>]/<project_id>` (scheme http/https, key and project id non-empty); a malformed value refuses at load naming the variable, never its value. In production a non-https DSN is a `production_problems` entry. Empty in production is allowed: the process starts and logs `error_tracker_not_configured` once (the tool is the founder's open decision; the readiness record carries it).
- `error_reporting.get_reporter()`: DSN set → `DsnReporter`; empty and `APP_ENV` local/test/ci → `RecordingReporter` (keeps reports in memory, logs `[errors:mock]` with ids only); empty in production → `LogOnlyReporter` (logs `error_report_not_sent` with type and ids). `use_reporter(r)` context manager for tests.
- `capture(exc, **ids) -> None` never raises; a failure is logged with its type only. `build_report` reads only: the exception's class (module and qualified name, filtered to `[A-Za-z0-9_.<>]`), its chain (`__cause__`/`__context__`, at most 5), and per frame `filename` (relative: `app/…` or the part after `site-packages/`, else the base name), `module`, `function`, `lineno`, `in_app` (at most 50 frames, innermost kept). Never the message, `args`, frame locals, the source line, request headers or body. Ids pass only for keys `request_id`, `class_session_id`, `game_id`, `job_id`, `task`, `status` with values matching `^[A-Za-z0-9_.:-]{1,80}$`; anything else is dropped. No `user_id` is sent. Report carries `event_id` (uuid4 hex), `occurred_at`, `app_env`, `release` (`RAILWAY_GIT_COMMIT_SHA` when set).
- `DsnReporter` speaks the Sentry envelope protocol (accepted by Sentry, GlitchTip and Bugsink, so the tool stays open): POST `<scheme>://<host>[:port][/<prefix>]/api/<project_id>/envelope/` with `X-Sentry-Auth: Sentry sentry_version=7, sentry_key=<key>, sentry_client=olspillet/1`, body = envelope header, item header `{"type":"event"}`, event JSON (`event_id`, `timestamp`, `platform` python, `level` error, `environment`, `release`, `tags` = ids, `exception.values[]` = type/module/stacktrace frames, no `value`). Stdlib `urllib` behind an injectable transport, timeout 5 s, sent from one daemon thread through a bounded queue (50); a full queue drops the report and logs `error_report_dropped`; `flush(timeout)` for tests.
- Hooks: `RequestLogMiddleware` captures an unhandled exception with `request_id`, the route's UUID path ids and `status=500`, then re-raises (the 5xx hook still counts it as `api_error` in `error_events` with the same `request_id`). `jobs.failure_middleware` captures a job that fails for good with `job_id`, `task` and the UUID `class_session_id`/`game_id` kwargs, beside `on_failure` (which counts `job_failed`). `platform` still imports no module.
- `POST /api/admin/operations/class-sessions/{class_session_id}/test-error` (new Admin-only policy `operations.test_error`): 404 `not_found` for an unknown Class session, else raises `DeliberateTestError`, so one deliberate error shows in the tracker and on «Drift» for that session. Changes no other data.
- `python -m app.ops.verify_restore <database_url> [--game ID ...] [--limit N]`: own engine on that URL (`NullPool`, `postgres://` normalised to psycopg), one `REPEATABLE READ, READ ONLY` transaction; prints the database's `alembic_version`, then one line per finished Game (`lifecycle=finished`, no `end_reason`, oldest first; `--limit` keeps the newest N) with its `rules_version` and `verified` or `FAILED` plus violation rules; a final pass/fail line. Exit 0 when ≥ 1 Game checked and all verify, 1 when any fails, 2 when nothing can be checked (unreachable, no schema, no finished Game, unknown `--game`). Never prints the URL or an exception message (type only). Replay reuses `games.checks` through a new read-only `games.service.replay_check(session, game_id)` that `verify_finished` also uses.
- `docs/ops/readiness.md` (the go/no-go record, "No-go" until every item is passed or carries a signed deviation): items, each `open` with issue #28 (backup, tracker, uptime, restore drill, deliberate error, stopped health check alert, contact, response route, Lab-hour availability measure, contact named in Lecturer material of Story 2.13) or #29 (email residency, listed for 15.14), a "Recorded (who, date)" column empty. Backup item lists the Supabase options and what each means for NFR-4. The independent review's proposal is written beside each ops item as "Proposal (independent review, not a founder decision)"; the item stays open.
- `docs/ops/sub-processors.md`: Railway, Supabase, Resend, LLM provider (OpenRouter, issue #9), DNS provider, each with data received, region, transfer basis; open rows for the error tracker (data = exactly the report fields above) and the uptime tool.
- Spine Deferred entries «Backup level», «Error tracking and uptime monitoring» and «Sub-processor register…» note what Story 15.11 added and that the decisions stay open; SETUP-GUIDE gets the `ERROR_TRACKER_DSN` row and §7 items 7–8 point at the two documents; `.env.example` gets `ERROR_TRACKER_DSN=`.

**Never:**
- No account with any tracker or cloud service, no real endpoint reached (tests use an injected fake transport); no tool, backup level or contact decided by the story.
- No exception message, local variable, request body, header, cookie, name, email, free text or `user_id` in a report; no new table or migration.
- `verify_restore` writes nothing (no `game_checks` row) and is never pointed at production by a test.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| PII in scope (api) | route raises with name, email, Explanation in locals, request body and exception message | 500; the bytes the DSN transport sent contain none of them; type, frames, request id and session id present; one `api_error` row with the same request id | — |
| PII in scope (job) | job with `game_id` raises with PII in locals and message | one report (job id, task, game id), no PII; one `job_failed` row | — |
| No DSN, test env | `ERROR_TRACKER_DSN` empty | `RecordingReporter` holds the report | — |
| No DSN, production | empty | `LogOnlyReporter`; start logs `error_tracker_not_configured` | — |
| Bad DSN | `not-a-dsn` / production `http://…` | `ConfigError` naming `ERROR_TRACKER_DSN` | refuse start |
| Tracker down | transport raises / 500 | logged `error_report_failed` with type; caller unaffected | swallowed |
| Queue full | > 50 pending | report dropped, `error_report_dropped` | — |
| Restore verifies | copy of test DB with a finished Game | `verified`, pass, exit 0, data unchanged | — |
| Tampered copy | a stored Week state changed in the copy | `FAILED` with rule, exit 1 | — |
| Nothing to check | empty DB / unreachable / unknown `--game` | message without URL, exit 2 | type only |
| Test error | Admin POST for existing / unknown session; Lecturer | 500 + report + row / 404 / 403 | — |

</intent-contract>

## Code Map

- `backend/app/platform/config.py:47` `Settings`, `production_problems`, `_unset_alert` -- add `error_tracker_dsn`, its validator and production rule.
- `backend/app/platform/logging.py:118` `RequestLogMiddleware.__call__` -- capture in an `except Exception` before re-raise; `_path_ids`; `ALLOWED_FIELDS` (`[errors:mock]` keys: reuse `request_id`, `exc_type`, `game_id`, `job_id`; add `task`, `class_session_id`, `event_id` if logged).
- `backend/app/platform/jobs/__init__.py:178` `failure_middleware` -- capture beside `on_failure`.
- `backend/app/platform/email/senders.py` -- pattern: Protocol, mock with in-memory list, stdlib `urllib` transport injectable, `get_sender()` choice by key and env.
- `backend/app/main.py:55` lifespan -- log `error_tracker_not_configured` in production when empty; `worker.py:_start` same.
- `backend/app/modules/games/checks.py:50` `verify_finished`, `_violations` -- extract read-only `replay_check`; `games/service.py:18` re-export; `games/repo.py:1248` `finished_game_ids(session)`.
- `backend/app/modules/ops/operations_routes.py` -- add the test-error route; `operations.session_figures` or a light existence read for 404; `platform/authz.py:174` policies.
- `backend/app/sim.py` -- CLI pattern (`asyncio.run` with `SelectorEventLoop` on Windows, as `worker.py:main`).
- `backend/tests/ops/test_error_events.py:40,180` -- `boom` task and 5xx test patterns (`ASGITransport(raise_app_exceptions=False)`, `events()`); `tests/conftest.py` `kept_connection`, `_engines`, `libpq_dsn`, `TEST_DATABASE_URL`; `tests/games/helpers.py:255` `classic_game`, `tamper`; `tests/identity/helpers.py` `client`, `CSRF`.
- `.docs/planning-artifacts/architecture/architecture-beergame-2026-11-12/{ARCHITECTURE-SPINE.md:561-573,SETUP-GUIDE.md:46-60,183-194}`, `.env.example`, `docs/ops/connection-budget.md` (doc style).

## Tasks & Acceptance

**Execution:**
- `backend/app/platform/config.py` -- DSN setting, parse helper, production rule.
- `backend/app/platform/error_reporting.py` (new) -- report model, builder, three reporters, envelope, `capture`, `get_reporter`, `use_reporter`.
- `backend/app/platform/logging.py`, `platform/jobs/__init__.py`, `app/main.py`, `app/worker.py` -- hooks and start log.
- `backend/app/modules/games/{checks,service}.py` -- `replay_check`.
- `backend/app/ops/{__init__,verify_restore}.py` (new) -- the command.
- `backend/app/modules/ops/operations_routes.py`, `app/platform/authz.py` -- test-error route and policy.
- `backend/tests/platform/test_error_reporting.py` (new) -- matrix rows 1–7 and DSN/envelope shape; `backend/tests/ops/test_verify_restore.py` (new) -- rows 8–10 on a `CREATE DATABASE … TEMPLATE` copy of the worker's test database (this process's connections to it closed first; named `verify_restore_copy<suffix>`, dropped after), data checksum unchanged; `tests/ops/test_error_events.py` or new file -- test-error route row; `tests/test_config.py` -- DSN rows.
- `frontend/src/lib/api/*` -- regenerated (`npm run api:generate`) for the new route.
- `docs/ops/readiness.md`, `docs/ops/sub-processors.md` (new); spine Deferred notes; SETUP-GUIDE rows; `.env.example`.

**Acceptance Criteria:**
- Given an api route and a job that raise while a name, an email and an Explanation are in locals, the request body and the exception message, when the adapter reports through the DSN transport, then the sent bytes hold none of them and hold the error type, the stack frames and the ids, and `error_events` holds the matching row.
- Given a restored copy of the test database, when `verify_restore` runs, then it reports each finished Game verified at its `rules_version`, exits 0 and leaves the data unchanged; a tampered Week makes it exit 1.
- Given the repository, when the readiness record and the register are read, then every item named in the story is listed open with its issue number, the backup item lists the Supabase options against NFR-4, and the independent review's proposals are marked as proposals.

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
- layers: Blind Hunter and Edge Case Hunter (sonnet); Verification Gap and Intent Alignment skipped, as the lead asked for two reviewers. A third sonnet agent, outside the review, proposed the ops values (readiness record, "Proposals").
- verdicts: 33 findings — high 0, medium 7, low 21, false 5, maybe-false 0
- findings:
  - `[medium]` `[patch]` Blind: one Game whose replay raises something other than `ViewError` aborts `verify_restore` as exit 2 — each Game is replayed under a savepoint and any error fails that Game alone by type (`FAILED (KeyError)`), the others still checked; test added.
  - `[low]` `[patch]` Blind: only finished Games are checked; running Games and other tables are not — the story asks for finished Games (a running Game has no last Week to replay); R4 now states what the drill does not show.
  - `[low]` `[patch]` Blind: the revision is printed but not compared with the code's head — R4 now says to compare it with `alembic heads`; a comparison in code would make the command load the migration scripts.
  - `[low]` `[patch]` Blind: no connect timeout, no progress, `--limit` ignored with `--game` — `connect_timeout` 10 s; `--game` with `--limit` refused (exit 2, test); a repeated `--game` counted once (test). Progress output rejected: the lines print within seconds for a pilot's Games.
  - `[low]` `[reject]` Blind: handler-built 5xx, the sweep, background tasks and the frontend are not reported — the spec's Design Notes choose unhandled api exceptions and failed jobs so the tracker and `error_events` count the same errors; listed as a residual risk; R2 states exactly what is sent.
  - `[medium]` `[patch]` Blind: queued reports are lost at process exit — each `DsnReporter` registers an `atexit` flush of at most 2 s.
  - `[medium]` `[patch]` Blind: `urlopen` follows redirects, possibly to http with the key — a no-redirect opener; a 3xx is a failed send; a test with a local server shows the target is never called.
  - `[low]` `[patch]` Blind: `log_start` and `reporter_for` decide the kind twice — `reporter_for` now uses `reporter_for_kind`.
  - `[low]` `[reject]` Blind: `get_reporter` has no lock — `capture` runs on the event loop thread (request and job middleware); a reporter made twice in a race would only send through its own thread.
  - `[low]` `[reject]` Blind: the test error can target any real Class session and is not audited — Admin only, documented for the rehearsal Class session; the row it adds is the point of the drill.
  - `[low]` `[patch]` Blind: the test route stays on the cached app — a fixture removes both test routes after the test.
  - `[false]` `[reject]` Blind: the diff adds a Story 15.9 log section — that is the orchestrator's commit on the branch after the baseline. Its small true part (`RAILWAY_GIT_COMMIT_SHA` undocumented) is patched with a SETUP-GUIDE row; the spine bullet keeps the open decision and the delivered adapter apart by its «Story 15.11» mark.
  - `[low]` `[patch]` Blind: the readiness record says "R1-R10" though it has R1–R12 — corrected; the proposals' "to confirm" marks are intended.
  - `[low]` `[patch]` Blind: the register understates the tracker's ids and has no retention — the row now calls them pseudonymous ids joinable to Students and lists retention as open. GitHub, fonts and analytics rejected: CI holds no personal data, fonts are self-hosted (AD-18), there is no analytics.
  - `[medium]` `[patch]` Edge: a route naming its Class session `session_id` sends no `class_session_id` to the tracker — the middleware maps it as the 5xx hook does; test with a `session_id` route.
  - `[medium]` `[patch]` Edge: a non-`ViewError` in one Game aborts the run — same root cause as Blind 1, patched with it.
  - `[low]` `[patch]` Edge: no connect timeout — same as Blind 4.
  - `[low]` `[patch]` Edge: a restored copy reached without TLS — R4 gives the URL with `sslmode=require` (a local copy needs none, so the command does not refuse it).
  - `[low]` `[patch]` Edge: a repeated `--game`, `--game` with `--limit` — same as Blind 4.
  - `[low]` `[reject]` Edge: partial results discarded on a later failure — with per-Game savepoints only a lost connection reaches that path, where nothing more can be read.
  - `[low]` `[patch]` Edge: the URL is in argv and shell history — the story names the argument; R4 says to run it in a one-off shell without history.
  - `[medium]` `[patch]` Edge: queued reports lost at exit — same as Blind 6.
  - `[low]` `[reject]` Edge: an `ExceptionGroup` hides its members — no middleware here uses task groups (all pure ASGI) and jobs raise directly; the group's class and stack are still sent.
  - `[low]` `[patch]` Edge: the mock's list grows without bound — a deque of the last 1000; test.
  - `[false]` `[patch]` Edge: a `ConfigError` (SystemExit) in `capture` escapes — settings are loaded and cached at start, so it cannot happen in a running process; caught anyway beside `Exception`, test.
  - `[low]` `[patch]` Edge: an exception after a started 200 is tagged 500 — the tag is now the status the middleware saw; disconnect errors are 5xx in `error_events` too, so they stay reported.
  - `[medium]` `[patch]` Edge: redirects resend the key — same as Blind 7.
  - `[low]` `[reject]` Edge: no rate limit per fingerprint — the bounded queue (50) drops a storm and the proposal sets the tracker's spike protection and a key rate limit; `error_events` counts every error regardless.
  - `[low]` `[patch]` Edge: an IPv6 DSN host loses its brackets — kept; test.
  - `[false]` `[reject]` Edge: the test error inflates «Drift» counts — that is the drill's stated outcome (R5).
  - `[false]` `[reject]` Edge: a revision mismatch gives a cryptic error — a missing table now fails that Game by type, and the revision line shows the copy's migration; R4 says to compare it.
  - `[false]` `[reject]` Edge (claim): tracker and «Drift» are independent, so R5 may pass on one — the drill checks both and records the request id seen in both; their independence is the design (NFR-8).
  - `[low]` `[patch]` Edge (claim): reports from `session_id` routes lack the Class session — same root cause as Edge 1, patched with it.

## Design Notes

Reports are built, not scrubbed: the builder never reads text that could hold personal data, so no pattern list can miss a name. The ids allowlist excludes `user_id` because the tracker is a sub-processor outside the DPIA's data map; a `request_id` joins a report to the logs and to `error_events`. Only unhandled api exceptions and failed jobs are reported, which keeps the tracker and `error_events` counting the same errors; errors caught and logged elsewhere (sweep items, rescue loop) stay in the logs (listed as a residual risk).

## Verification

**Commands:**
- `cd backend && uv run pytest tests/platform/test_error_reporting.py tests/ops/test_verify_restore.py tests/ops/test_error_events.py tests/test_config.py tests/test_imports.py -q` -- expected: pass
- `cd backend && uv run pytest -q -n 8 --maxprocesses=8` -- expected: pass
- `cd backend && uv run ruff check . && uv run ruff format --check .` -- expected: clean
- `cd frontend && npm run typecheck && npx vitest run && npm run lint:colours && npm run check:copy && npm run build` -- expected: pass
- `cd frontend && npx playwright test homes play --workers=4` -- expected: pass

## Auto Run Result

Status: done

**Summary.** One error-reporting adapter, `backend/app/platform/error_reporting.py`, configured by `ERROR_TRACKER_DSN` (`https://<key>@<host>/<project>`; refused at load when malformed, refused in production without https). It builds each report from structure only: the error's class and chain, per frame the relative file, module, function and line, and the ids `request_id`, `class_session_id`, `game_id`, `job_id`, task and status. No message, argument, local, source line, header, body, name, e-mail or User id is read. `DsnReporter` posts a Sentry envelope (accepted by Sentry, GlitchTip and Bugsink, so the tool stays open) from one daemon thread through a bounded queue, never follows a redirect, and flushes for up to 2 s at exit. `RecordingReporter` is the mock when the DSN is empty in local, test or ci; `LogOnlyReporter` logs `error_report_not_sent` in production without a DSN, and each process logs at start which reporter it uses (`error_tracker_not_configured` in that case). The request log middleware reports unhandled api exceptions (the 5xx hook still counts them in `error_events` under the same request id and Class session); the worker's failure middleware reports jobs that fail for good beside `record_job_failure`. `POST /api/admin/operations/class-sessions/{id}/test-error` (Admin only, 404 for an unknown session) raises `DeliberateTestError` for the readiness drill. `python -m app.ops.verify_restore <database_url> [--game ID] [--limit N]` replays the finished Games of a restored copy at their stored `rules_version` in one read-only transaction (each Game under a savepoint), through the new read-only `games.service.replay_check`, which `verify_finished` now uses too; exit 0, 1 or 2; it prints no URL and no error text. `docs/ops/readiness.md` (the no-go record: R1–R12 open with issue #28 or #29, the Supabase backup options against NFR-4, the drills) and `docs/ops/sub-processors.md` (Railway, Supabase, Resend, OpenRouter, DNS; open rows for the tracker and the uptime monitor) are new; the spine's Deferred entries and the SETUP-GUIDE point to them.

**Ops values proposed by an independent review agent in place of the founder** (in `docs/ops/readiness.md`, "Proposals"; every item stays open): backup PITR add-on, 7 days, on Pro (about 2 minutes of loss; a manual `pg_dump` before risky changes); error tracker Sentry SaaS in the EU region (Germany), Developer plan, IP storage off, server-side scrubbing on as a second guard, spike protection and a key rate limit (fallback GlitchTip EU); uptime UptimeRobot Solo, 1-minute HTTPS keyword check on `/api/health` from EU probes, alert after 2 failures, push and SMS, no public status page (fallback Better Stack); an alert within 5 minutes of a stopped `backend`; contact = the founder with a named stand-in, escalation after 5 minutes; the Lecturer told at 5 minutes and the session moved at 15; Lab-hour availability = share of checks answered in the union of the sessions' Lab-hour windows (target 99.5 %); transfer basis SCCs (and DPF if certified) for the tracker, none needed for the monitor beyond the contact's own data. Every price and limit is marked "to confirm".

**Other decisions taken in place of the founder.** Protocol: Sentry envelope over stdlib `urllib` (no SDK). Production without a DSN starts and logs instead of refusing (the tool is open). No `user_id` is sent. Only unhandled api exceptions and failed jobs are reported (the errors `error_events` counts as `api_error` and `job_failed`). Queue 50, send timeout 5 s, exit flush 2 s, mock keeps 1000. The drill is an Admin-only API route called from the browser console (no UI). `verify_restore` checks every finished Game by default, refuses `--game` with `--limit`, connect timeout 10 s. The readiness items take issue #28, the e-mail residency #29.

**Personal data.** No new table, no migration. The error tracker is a new sub-processor (register row, open).

**Files.**
- `backend/app/platform/error_reporting.py` (new): the adapter.
- `backend/app/platform/{config,logging,authz}.py`, `platform/jobs/__init__.py`, `app/main.py`, `app/worker.py`: DSN setting, hooks, start log, policy.
- `backend/app/modules/games/{checks,service}.py`: `replay_check`, `finished_game_ids_in`.
- `backend/app/ops/{__init__,verify_restore}.py` (new): the command.
- `backend/app/modules/ops/{operations,operations_routes}.py`: the deliberate test error.
- `backend/tests/platform/test_error_reporting.py`, `tests/ops/test_error_tracking.py`, `tests/ops/test_verify_restore.py` (new); `tests/ops/test_error_events.py` (the mock's log line).
- `frontend/src/lib/api/{openapi.json,schema.ts}`: regenerated.
- `docs/ops/readiness.md`, `docs/ops/sub-processors.md` (new); `ARCHITECTURE-SPINE.md` Deferred notes; `SETUP-GUIDE.md` rows and §7; `.env.example`; `epic-15-context.md` recompiled (the spine and SETUP-GUIDE were newer).

**Review.** Two sonnet sub-agents (blind, edge case); 33 findings. Patched: 7 medium rows in 4 root causes (one Game aborting `verify_restore`; reports lost at exit; redirects; `session_id` routes without the Class session), 15 low rows and 1 false row fixed anyway. Deferred: none. Rejected: 10 (4 false, 6 low), each with its reason in the triage log.

**Follow-up review: recommended (true).** Patched by entry verdict: high 0, medium 4 entries, low 15 rows. Two or more medium entries were patched on a first pass. Three of the four are covered by new or extended tests (a Game failing alone, a redirect not followed, the `session_id` route tag). The exit flush is not exercised by any test: whether `atexit` runs in time when Railway stops a container (SIGTERM, then SIGKILL) is the unverified risk.

**Verification.**
- Backend full suite (`-n 8 --maxprocesses=8`, DB `olspillet_e15`): 3534 passed. ruff check and format clean. The OpenAPI schema is unchanged by the patches.
- Frontend: typecheck ok, Vitest 1144 passed, `lint:colours` and `check:copy` passed, `next build` compiled (no frontend code changed; the client was regenerated).
- Playwright (`--workers=4`, stack on `olspillet_e15stack`): `homes`, `order-field`, `playout` 30 passed with axe at 320, 360 and 1440 px. The stack's backend logged `error_tracker` `kind=mock` at start.
- Matrix: rows 1–2 in `test_error_tracking.py` (an api route and a job with a name, an e-mail and an Explanation in locals, body and message; the bytes sent hold none of them; the `error_events` row carries the same id); rows 3–7 in `test_error_reporting.py`; rows 8–10 in `test_verify_restore.py` (a `CREATE DATABASE … TEMPLATE` copy of the worker's test database; checksum unchanged; a tampered Week fails; unreachable, no schema, unknown Game exit 2); row 11 in `test_error_tracking.py`.
- New tests over 1 s: `test_a_restored_copy_verifies_…` (its fixture plays two Classic Games, shared per run, and copies the database: about 9 s alone; not among the suite's slowest in the full run).

**Residual risks.**
- Errors caught and logged elsewhere (sweep items, the rescue loop, handler-built 5xx such as the health check's 503) reach the logs, and for 5xx `error_events`, but not the tracker.
- The proposals' prices, plan limits and hosts come from the reviewer's memory and third-party pages, all marked "to confirm".
- The test's database copy is dropped in a background thread at teardown (the drop waits for a checkpoint under load) and joined at the worker's exit; a copy left by an interrupted run is dropped by the next run.
- The existing logging allowlist keeps an `exception` field whose formatted traceback can include an exception's message (pre-existing, not this story's adapter).
