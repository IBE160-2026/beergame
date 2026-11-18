---
title: 'Story 3.5: Send every mail through one pipeline'
type: 'feature'
created: '2026-11-18'
status: 'done'
baseline_revision: '2389699349847b596b2930496b98f4d3480b93e6'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-3-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-3-4-see-loading-failure-offline-states.md'
warnings: [oversized]
deferred: []
---

<intent-contract>

## Intent

**Problem:** Stories 3.6, 3.7 and 3.8 must send Invitation and reset mails, and later epics send reminders, but there is no notice table, no mail renderer or sender, no `mail` queue and no sweeper. Each story would otherwise build its own path, and mails could be lost, sent twice or sent at night.

**Approach:** Add `platform/notify` (the `notices` table, `enqueue`, `claim_due`), `platform/email` (Jinja2 templates, a sender adapter with a Resend sender and a deterministic `[email:mock]` sender), the delivery part of `modules/messaging` (the one delivery table per kind, the claim and `mail` jobs, `mail_deliveries`), and `modules/ops` with `ops.sweep`, the one periodic task. Two dummy kinds and a `send-test` CLI prove the pipe end to end, outside production only.

## Boundaries & Constraints

**Always:**
- `notify.enqueue(session, user_id, kind, dedupe_key, ref=None, not_before=None)` runs on the caller's session. It inserts one `notices` row (ids only), unique on `dedupe_key`: a repeat key inserts nothing and returns False. With a `user_id` it emits `user:<id>` (registry entry `notify.enqueue`). With `user_id=None` it needs a `ref` and emits nothing. It always defers the claim job `messaging.claim_notice(notice_id)` by name on queue `mail` through `jobs.defer` on the same session. `platform/notify` imports no module.
- Time is passed in as `now` (host clock in production, a fixed value in tests). No logic compares database `now()` with host time (Issue #63). `not_before` NULL means due at once.
- The delivery table lives in `modules/messaging/delivery.py`: kind → mode (`immediate` | `digest`), template name and, for a by-reference kind, the owning module's `service.py` resolver `(session, ref) -> Recipient | None`. A digest kind cannot be by reference. User-addressed kinds resolve through `identity.service.mail_recipient(session, user_id)` (None for a missing or deactivated User). The dummy kinds `test_immediate` and `test_digest` are in the table only when `APP_ENV != production`.
- The claim job claims only an unclaimed notice of an immediate kind that is due. A digest notice, a notice whose `not_before` lies ahead, and an unknown kind are left alone.
- Claiming writes one `mail_deliveries` row (`id`, `user_id` or NULL, `mode`, `notice_ids uuid[]`, `claimed_at`, `sent_at`, `provider_message_id`, `skipped_reason`) and defers the `mail` job `messaging.send_mail(delivery_id)`, keyed by the delivery id, in the same transaction. The `mail` job locks the row (`FOR UPDATE SKIP LOCKED`), sends nothing when the row is gone, locked or already sent or skipped, renders, sends, and stores `sent_at` and the provider's id. A missing recipient sets `skipped_reason = 'no_recipient'` and sends nothing.
- Digest: at most one digest delivery per User per Europe/Oslo calendar day, never claimed at 22:00–07:00 Oslo. At the first sweep inside allowed hours, all of the User's due digest notices go into one mail. A notice due after that day's mail waits for the next day from 07:00.
- `ops.sweep` (task name `ops.sweep`, queue `sweep`, `queueing_lock` `ops.sweep`) is registered as a periodic every-minute task only when `worker-batch` runs with `--sweeper`. It only finds due items and calls `messaging.service` for each, one transaction per item. Its due action list starts with `messaging`. There is no other cron.
- Mail: Norwegian bokmål, no exclamation marks, a text and an HTML part, headed «ØL-spillet», from `EMAIL_FROM`, with links from `PUBLIC_BASE_URL`. HTML uses DESIGN.md colours inline (`paper`, `ink`, `ink-secondary`, `hairline`, links in `lager`).
- Sender: `RESEND_API_KEY` set → Resend over HTTPS with an `Idempotency-Key` of the delivery id. Not set and not production → the mock, which logs `[email:mock]` with ids only and returns `mock-<delivery_id>`. Not set in production → refuse to send. The provider stays behind the `Sender` protocol so it can be swapped (Issue #29).
- No name, e-mail, link or token in a log line, a job argument, a notice or a delivery row.

**Never:**
- No real mail and no provider account; compose does not pass `RESEND_API_KEY`. No `resend` SDK. No `httpx` in `app/platform`.
- No real kinds (Invitation, reset), no in-app notice list, no webhook columns (3.6–3.8, Story 14.x), no production config guard for `RESEND_API_KEY` (3.14).
- No edits to `sprint-status.yaml`, `.env` or `.claude/settings*.json`. No real waits in tests.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Immediate | `test_immediate` enqueued at 23:00 Oslo, commit | Claim job → delivery → one `[email:mock]` | — |
| Rolled back | enqueue, then rollback | No notice, no job, no event | — |
| Same key | Same `dedupe_key` twice | One notice; second call returns False | — |
| By reference | `user_id=None`, `ref` set, by-reference kind | No `user:` event; address from the resolver | resolver None → `skipped_reason` |
| Later | Immediate with `not_before` in 1 h | Claim job leaves it; a sweep after that time sends it | — |
| Digest | Three `test_digest` at 09:00–09:20, sweep 09:30 | One mail with three notices | — |
| Night | Digest due 23:30, sweeps 23:31 and 06:59 | Nothing; sweep 07:00 sends it | — |
| After the day's mail | Digest due 15:00 after a 09:30 mail | Nothing that day; 07:00 next day | — |
| Twice | Sweep twice over one due notice; `mail` job run twice | One delivery row, one mail | — |
| Production without key | `APP_ENV=production`, no key | No mock: sender refuses | `mail` job fails, row stays unsent |

</intent-contract>

## Code Map

- `backend/app/platform/jobs/__init__.py` -- `QUEUES`, `TASK_MODULES`, `defer(session, task, queue=, queueing_lock=, **ids)`, `run_until_idle`, `run_worker` (validates queue names). Add `MAIL`, `SWEEP`, and the task modules `app.modules.messaging.jobs`, `app.modules.ops.jobs`. The periodic registry is shared by `with_connector` apps; the deferrer runs only when a periodic task is registered.
- `backend/app/worker.py` -- argument parsing, `serve`. Add `--sweeper`: registers the periodic `ops.sweep` and adds queue `sweep`.
- `backend/app/platform/events/{__init__,registry}.py` -- `emit`; `user` topic exists. Add `notify.enqueue: {user}` to `COMMAND_TOPICS` (`tests/games/test_registry.py` iterates only `games.*`).
- `backend/app/platform/config.py` -- add `email_from`, `public_base_url`, `resend_api_key`.
- `backend/app/platform/logging.py` -- `ALLOWED_FIELDS`; add `delivery_id`, `notice_id`, `kind`, `notice_count`, `provider_ref`. `tests/test_logging.py:62` forbids field names containing `mail`/`message`/`text`.
- `backend/app/modules/identity/{service,repo}.py` -- `load_user`, `repo.user_by_id`. Add `mail_recipient(session, user_id)`.
- `backend/migrations/versions/0015_identity_users_ratelimit.py`, `migrations/env.py` -- revision style; env imports each table module. New `0016_notices_mail_deliveries.py`.
- `backend/tests/conftest.py` -- `identity_db`, `games_db` (truncates `procrastinate_jobs`), `REFUSE` transport. Add a `mail_db` fixture.
- `backend/tests/test_imports.py:62` -- `app/platform` may not import `app.modules` or anything starting with `httpx` (so the Resend sender uses `urllib.request` in a thread, with an injectable transport).
- `backend/tests/test_migrations.py:36-40` -- `HEAD`, `HEAD_TABLES`; add the new tables and a downgrade test.
- `backend/tests/test_worker.py:12` -- uses `mail` as an unknown queue; change to another name.
- `docker-compose.yml` -- `worker-batch` command `--queues llm-batch,mail --sweeper`; `EMAIL_FROM`, `PUBLIC_BASE_URL` defaults for backend and workers; no `RESEND_API_KEY`.
- `frontend/scripts/check-copy.mjs` -- already reads `backend/app/**/templates/**` (`.j2`, `.txt`, `.html`).

## Tasks & Acceptance

**Execution:**
- `backend/pyproject.toml`, `uv.lock` -- add `jinja2` and `tzdata` (Windows has no system zone data).
- `backend/app/platform/config.py`, `logging.py` -- new settings and log fields.
- `backend/app/platform/notify/{__init__,models}.py` -- `notices` table; `Notice`; `enqueue`, `claim_due(session, now, *, kinds, notice_id=None, user_id=None)` (atomic claim with `FOR UPDATE SKIP LOCKED`), `due(session, now, kinds)`, `get(session, ids)`; `CLAIM_TASK`.
- `backend/app/platform/email/{__init__,render,senders}.py`, `templates/{layout.txt.j2,layout.html.j2,digest.txt.j2,digest.html.j2,kinds/test_immediate.*,kinds/test_digest.*}` -- `Recipient`, `Mail`, `render(...)`, `Sender` protocol, `MockSender`, `ResendSender`, `get_sender()`.
- `backend/app/modules/messaging/{__init__,delivery,models,repo,service,jobs,cli}.py` -- delivery table, `mail_deliveries`, `claim_notice`, `due_items(now)`, `claim(item, now)`, `send(delivery_id)`, the two tasks, and `cli send-test` (refuses in production).
- `backend/app/modules/ops/{__init__,sweep,jobs}.py` -- `DUE_ACTIONS`, `run(now)`, the `ops.sweep` task and `schedule()`.
- `backend/app/platform/jobs/__init__.py`, `app/worker.py`, `app/platform/events/registry.py`, `migrations/env.py`, `migrations/versions/0016_notices_mail_deliveries.py`, `docker-compose.yml` -- wiring as in the Code Map.
- Tests: `tests/platform/test_notify.py`, `tests/platform/test_email.py`, `tests/messaging/test_delivery.py`, `tests/messaging/test_digest.py`, `tests/messaging/test_cli.py`, `tests/ops/test_sweep.py`, plus updates to `test_worker.py`, `test_migrations.py`, `test_imports.py` (messaging/ops boundaries), `conftest.py`. Jobs are driven with `run_until_idle`, never a clock wait.

**Acceptance Criteria:**
- Given the matrix, when the tests run, then each row holds, and the digest rows use a controlled `now` with the dummy `test_digest` kind.
- Given every new Python file, when `test_imports.py` runs, then `platform/notify` and `platform/email` import no module, no module but `messaging` and `ops` imports `messaging`, and only `ops` imports `ops`.
- Given the local stack with no keys, when `python -m app.modules.messaging.cli send-test --user <demo id> --kind test_immediate` runs in the backend container, then `worker-batch` logs one `[email:mock]` line within seconds and a `mail_deliveries` row exists; `--kind test_digest` gives its line at the next sweep inside allowed hours.
- Given `APP_ENV=production`, then the dummy kinds are not in the delivery table and `send-test` exits non-zero.
- Given the full suites, then no new test takes over 1 s.

## Spec Change Log

## Review Triage Log

### 2026-11-18 — Review pass
- verdicts: 34 findings — high 0, medium 5, low 21, false 3, maybe-false 5
- findings:
  - Blind Hunter:
    - `[low]` `reject` Production starts without `RESEND_API_KEY`, `PUBLIC_BASE_URL` or `EMAIL_FROM` checked. The production guard belongs to Story 3.14 (epics: "Prepare a strict production configuration"), and `get_sender` already refuses to send without a key in production.
    - `[low]` `reject` A User-addressed kind cannot get template variables. No kind needs them yet. Story 3.6 adds that field to `Delivery` when it registers `password_reset`; noted under residual risks.
    - `[low]` `patch` The CLI docstring promised the notice id. The docstring now says it prints the kind and the User id.
    - `[low]` `patch` The `RETRY_AFTER` comment said "about two hours". It now gives the real schedule: 2 (lost job), 4, 8, 16, 32 and 64 minutes after the claim.
    - `[low]` `reject` Template and config errors are retried like provider errors. The retries are bounded (6, about an hour), each is logged with its type, and a template error shows in the first test of that kind.
    - `[maybe-false]` `reject` The row lock is held during the HTTP call. It is bounded by the 10 s timeout and is what makes a double send impossible. Load at pilot scale would settle it; if true it is low.
    - `[low]` `reject` An unknown kind is never claimed and nothing flags it. Kinds come from code, and the test covers the behaviour; a guard adds a branch for a programming error.
    - `[maybe-false]` `reject` The sweep queries are unbounded and relist Users already mailed today. At the pilot's size (a few hundred Users) the cost is a few empty transactions per minute. A load measurement would settle it; if true it is low.
    - `[medium]` `patch` `log.exception` in the sweep could put an exception's text, possibly with an address, in the logs. It now logs `exc_type` only. (The heartbeat part is rejected as low: procrastinate already logs every `ops.sweep` run.)
    - `[false]` `reject` Missing docs, import test, retention, index. `SETUP-GUIDE.md` already lists `RESEND_API_KEY`, `EMAIL_FROM`, `PUBLIC_BASE_URL` and the `--sweeper` command. `test_the_platform_imports_no_module_and_no_llm_library` already walks all of `app/platform`. Retention is a later due action (AD-9). Users are never deleted, so a `user_id` index for the cascade is not needed. The DST point is patched under Edge Case Hunter.
    - `[low]` `reject` Digests have no opt-out. No real digest kind exists yet; the first digest story owns that choice.
  - Edge Case Hunter:
    - `[medium]` `patch` An exception from `notify.get` or a resolver before the `try` left `attempts` at 0, so the delivery was retried forever. Resolution now runs inside the failure handling (`_failed`), and a test with a failing resolver checks `attempts == 1`.
    - `[medium]` `patch` A digest claimed at 21:59 whose job ran late or was retried could go out at night. `send` now holds a digest in the quiet hours (`held`, no attempt counted), and the sweep re-defers digest retries only inside the allowed hours. Test: `test_a_late_digest_is_held_through_the_night_and_sent_from_0700`.
    - `[maybe-false]` `reject` Resend answers 409 when a retry renders a different body under the same key. It happens only if the name changed between tries. Resend's documented behaviour on a body mismatch would settle it; if true it is low.
    - `[low]` `patch` `{"id": null}` was stored as the string `None`. An empty or non-string id is now `provider_answer_unreadable`, with a test case.
    - `[low]` `reject` Users already mailed today are relisted every minute (duplicate of the unbounded-query row).
    - `[maybe-false]` `reject` One sweep could run past the minute during a backlog (duplicate). The queueing lock stops sweeps from stacking.
    - `[low]` `reject` A by-reference digest notice is never claimed. `Delivery` forbids a digest kind by reference, so only a caller bug can write one.
    - `[low]` `patch` `--sweeper --queues ,` skipped the "no queue" error. The check now runs before `sweep` is added, with a test.
    - `[low]` `patch` The CLI prints the User id, not the notice id (duplicate). The docstring is fixed. A dedupe hit cannot happen, because the key is a fresh uuid.
    - `[low]` `patch` Retry comment (duplicate). Fixed above.
    - `[medium]` `patch` Sweep tracebacks may carry personal data (duplicate). Fixed above.
    - `[low]` `reject` The spec names `layout.*`/`digest.html.j2`; the code ships `mail.*` and `digest.txt.j2`. The fix would be a spec edit.
    - `[medium]` `patch` Digests sent at night after a retry (duplicate of the claim above). Fixed above.
  - Verification Gap:
    - `[low]` `patch` No test re-defers a lost `mail` job at `attempts = 0`. Added `test_a_lost_mail_job_is_deferred_again_by_the_sweep`. It exposed an off-by-one: the cutoff was `<` while `_retry_due` used `<=`. Both are now `<=`.
    - `[low]` `patch` No test shows that an immediate mail leaves the day's digest alone. Added `test_an_immediate_mail_leaves_the_days_digest_alone`.
    - `[low]` `patch` CLI docstring (duplicate). Fixed above.
    - `[low]` `patch` The `notify.enqueue` registry entry was not checked. `test_notify` now compares the emitted topics with `COMMAND_TOPICS["notify.enqueue"]`.
  - Intent Alignment (descriptive divergences):
    - `[low]` `reject` `ratelimit.purge` is a second due action the story does not name. `platform/ratelimit.py` (Story 3.2) assigned it to "`ops.sweep` in Story 3.5". It is idempotent and has its own test.
    - `[false]` `reject` The local-stack `send-test` is untested. It was run on the compose stack twice (Verification): one `[email:mock]` line in about 1 s, the digest at the next sweep, `mail_deliveries` rows present.
    - `[low]` `reject` A skipped digest delivery uses up the User's day. A skipped digest has no recipient, so there is no one to mail that day.
    - `[low]` `reject` The night case for immediate mail calls `claim_notice` directly. The claim job is one line around it and runs in the other tests.
    - `[false]` `reject` By-reference recipients have no real owning-module resolver. The story builds the mechanism; Story 3.7 binds `invitation`.
    - `[maybe-false]` `reject` The dummy templates and the CLI ship in the production image. The story says the kinds and the command "exist only outside production", which the code enforces at run time. Whether the founder meant the image would settle it; if true it is low.

## Design Notes

- **When a digest goes out.** The digest is sent at the first sweep in allowed hours after a notice is due, carrying every due digest notice of that User; later notices that day wait for tomorrow. This meets "at most one per day, never at night" with no extra delay. A fixed daily hour was rejected: it would hold a same-day reminder until the next morning.
- **Render at send time.** The address and any link are resolved inside the `mail` job, so no address reaches a job argument or a table outside `identity`. The cost is that a mail is rendered from the state at send time.
- **Exactly once.** The row lock stops two `mail` jobs sending one delivery. If the process dies after the provider accepted the mail but before `sent_at` is stored, the retry carries the same `Idempotency-Key`, and Resend drops the duplicate.
- **Its own `sweep` queue.** A backlog of mails or reports never delays the sweep, and only the `--sweeper` process runs it.

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/platform/test_notify.py tests/platform/test_email.py tests/messaging tests/ops` -- expected: pass
- `cd backend && uv run pytest --durations=15 && uv run ruff check . && uv run ruff format --check .` -- expected: pass, no new test over 1 s
- `cd frontend && npm run check:copy` -- expected: pass, templates counted
- `docker compose up -d --build --wait worker-batch` then `docker compose exec backend python -m app.modules.messaging.cli send-test --user <demo admin id> --kind test_immediate` and `docker compose logs worker-batch` -- expected: one `[email:mock]` line

## Auto Run Result

Status: done

**Summary.**
- `platform/notify` holds `notices` (ids only, unique `dedupe_key`). `enqueue` runs in the caller's transaction, emits `user:<id>` (registry entry `notify.enqueue`), or nothing for a notice by reference, and defers the claim job by name. `claim_due`, `due` and `get` are the reads; `messaging` is their only caller.
- `platform/email` renders Jinja2 templates: a text and an HTML part, headed «ØL-spillet», from `EMAIL_FROM`, with links on `PUBLIC_BASE_URL`, and DESIGN.md colours inline. It sends through the `Sender` protocol, so the provider can be swapped (Issue #29):
  - `ResendSender` uses stdlib HTTPS with `Idempotency-Key` = delivery id;
  - `MockSender` logs `[email:mock]` with ids only;
  - in production with no key, sending is refused.
- `modules/messaging` holds the delivery table, `mail_deliveries`, the `messaging.claim_notice` and `messaging.send_mail` jobs on queue `mail`, retry with backoff (6 tries, about 1 h, then `send_failed`), the digest rules, and `cli send-test`. The two dummy kinds exist outside production only.
- `modules/ops` holds `ops.sweep` on its own queue `sweep`, registered as periodic only by `worker --sweeper`. Its due actions are `messaging.mail` and `ratelimit.purge`.
- Compose: `worker-batch` runs `--queues llm-batch,mail --sweeper`. `EMAIL_FROM` and `PUBLIC_BASE_URL` have defaults. `RESEND_API_KEY` is never passed.
- `platform/jobs.run_worker` now opens the shared app with `replace_connector` instead of a `with_connector` copy. Without that the periodic deferrer failed with `AppNotOpen`, which the local stack showed.

**Files changed:**
- Backend app:
  - `app/platform/{notify/__init__.py,email/*,config.py,logging.py,jobs/__init__.py,events/registry.py}`
  - `app/modules/messaging/*`, `app/modules/ops/*`
  - `app/modules/identity/service.py` (`mail_recipient`)
  - `app/worker.py` (`--sweeper`)
- Migration: `0016_notices_mail_deliveries.py` (`env.py` imports the new tables).
- Dependencies: `pyproject.toml`/`uv.lock` add `jinja2==3.1.6` and `tzdata==2026.6`.
- Tests:
  - new: `tests/platform/{test_notify,test_email}.py`, `tests/messaging/{helpers,test_delivery,test_digest,test_cli}.py`, `tests/ops/test_sweep.py`;
  - updated: `conftest.py` (`mail_db`, `RESEND_API_KEY` popped), `test_worker.py`, `test_imports.py`, `test_migrations.py`.
- Compose: `docker-compose.yml`.

**Review.** 34 findings: 5 medium, 21 low, 3 false, 5 maybe-false.
- Patched: the 5 medium rows, which are 3 distinct defects (unbounded retry when resolving fails, digest mailed at night after a late or failed job, exception text in sweep logs), and 9 low rows. One of the low patches was a cutoff off-by-one that a new test exposed.
- Deferred: none.
- Rejected: the rest, each with its reason in the triage log.

**Follow-up review recommended: true.** Two or more medium entries were patched. The named risk is the new failure path in `send`: the quiet-hours hold and the `_failed` handling now share the delivery row lock, and the sweep's mode-filtered retry has not been reviewed again.

**Verification:**
- Backend `uv run pytest`: 1688 passed in 63 s. `ruff check` and `ruff format --check` passed.
- New tests, run with `-n0`, each take under 1 s; the slowest is 0.63 s.
- Frontend `npm run check:copy` passed (7 templates).
- Local stack, run twice:
  - `docker compose up -d --build --wait worker-batch`, then `send-test --kind test_immediate` as the demo Admin: one `[email:mock]` line about 1 s later and a `mail_deliveries` row. The second run after the patches showed the same, with no error lines.
  - `--kind test_digest`: sent at the next periodic `ops.sweep`, about 25 s later.
- The services I started (`backend`, `worker-batch`) are stopped and removed; `postgres` is left running.
- Migration 0016 is new. It ran once on the shared `olspillet_test*` databases and was not changed after that.
- Matrix audit, one test per row:
  - Immediate at night: `test_an_immediate_notice_leaves_at_once_even_at_night`.
  - Rolled back: `test_a_rolled_back_enqueue_…`.
  - Same key: `test_the_same_dedupe_key_gives_one_notice`.
  - By reference: `test_a_notice_by_reference_emits_nothing…` and `test_a_notice_by_reference_is_addressed_through_the_owning_resolver`.
  - Later: `test_the_claim_job_leaves_a_digest_and_a_later_notice_to_the_sweep`.
  - Digest, Night, After the day's mail: the three `test_digest.py` tests.
  - Twice: `test_two_sweeps_over_one_due_notice_give_one_mail` and `test_a_mail_job_that_runs_twice_sends_one_mail`.
  - Production without key: `test_in_production_without_a_key_the_mail_fails_and_stays_unsent`.

**Decisions taken in place of the founder:**
- A digest is sent at the first sweep inside 07:00–22:00 Oslo after a notice falls due. Later notices that day wait until the next day from 07:00. A fixed daily hour was not chosen.
- Address and template are resolved at send time; nothing is stored in a job or a row.
- A failed send is tried 6 times, at 2/4/8/16/32/64 minutes after the claim, then given up as `send_failed`. A deactivated or missing recipient is `no_recipient`, with no mail.
- The sweep has its own queue, `sweep`, with a queueing lock. The rate-limit purge (cutoff 1 day) is its second due action.
- The Resend sender uses the stdlib (no SDK, no `httpx` in `app/platform`). Compose never passes `RESEND_API_KEY`, so local mail is always the mock.
- Dummy kinds: `test_immediate` and `test_digest`. The mail copy is in Norwegian; the sign-off reads «Hilsen ØL-spillet» with the note that replies are not read.
- `notices.user_id` and `mail_deliveries.user_id` reference `users` with `ON DELETE CASCADE`.
- The implementation and the review fixes were done in this context, not in a subagent, as the caller instructed.

**Residual risks:**
- User-addressed kinds cannot pass template variables yet. Story 3.6 must add a context resolver to `Delivery` for the reset link.
- A digest delivery that was claimed but then skipped still counts as that day's digest.
- No production config guard for the mail settings yet (Story 3.14).
