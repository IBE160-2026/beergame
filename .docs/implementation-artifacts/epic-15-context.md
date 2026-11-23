# Epic 15 Context: Data rights and pilot readiness

<!-- Generated from planning artifacts. Regenerate with compile-epic-context if planning docs change. -->

## Goal

A Student can see all personal data the product stores about them, and the Admin can meet data-rights duties (delete a User on instruction, automatic retention deletion, pseudonymised export for evaluation). The Admin can also pin and freeze models, watch AI cost and per-session errors, and the founder can show the platform is ready for the pilot (connection budget, load test of 250 concurrent Students, error tracking and restore verification, accessibility evidence, a go/no-go preflight). The epic owns `backend/app/modules/ops/` and `frontend/src/modules/ops/` and extends `modules/identity` and `modules/admin`.

## Stories

- Story 15.1: A Student sees their own data in «Mine data»
- Story 15.2: The Admin deletes a User on the Institution's instruction
- Story 15.3: Student data is deleted automatically when retention ends
- Story 15.4: The Admin exports pseudonymised data for evaluation
- Story 15.5: The Admin pins and freezes a model for Class sessions
- Story 15.6: The Admin sees AI cost and sets the cost limit
- Story 15.7: The Admin is alerted when daily AI spend is high
- Story 15.8: The Admin sees errors, fallback and response times per Class session
- Story 15.9: The database connection budget is written and checked
- Story 15.10: A load test shows 250 Students playing at once
- Story 15.11: Errors reach an error tracker without personal data, and backup and monitoring are laid out for decision
- Story 15.12: Hold Student Invitations until the Institution's data processing agreement is recorded
- Story 15.13: Publish the accessibility statement and the conformance report
- Story 15.14: The pre-pilot checks pass before the first Class session

## Requirements & Constraints

- Access: every stored category of a Student's data is viewable by that Student only. A CI registry test fails when a table with personal data (a `user_id` column or User-written text) is not listed; each entry also gets a deletion handling, so access and deletion cannot drift apart.
- Erasure and retention: deletion anonymises the User but keeps Seats, occupancy, `seat_week` rows and the Decision log unchanged, so other Students' Games, charts and reports still render (Seat shown by Role) and stored states still verify through the engine. Deleting a Lecturer who owns Classes is blocked with the same rule and message as role revocation.
- Retention date is the latest effective Test deadline plus a per-Institution period (placeholder default: course end plus six months). Nothing is deleted before it; aggregates for Cross-class statistics are written first, only over groups of 10 or more Students, and figures must be identical before and after deletion. A Control test (a Class session of kind `control_test`, created only by the Admin, Roster of test Students with stored consent records) belongs to the operator-owned Institution and follows that Institution's own retention date, never a course Institution's.
- No names, emails or student numbers may survive anywhere after deletion (tables, job tables, local storage mock, report ZIPs).
- Personal data introduced by Epics 11 and 12 is in scope for access and deletion: Individual test answers (free text, Adapted items), AI assessment feedback that quotes answers, human scores and consent records of test Students. Scores/aggregates may stay as ids and numbers; quoted text and bodies are deleted.
- Pseudonymised export requires a recorded Institution agreement, a key supplied at run time by someone other than the founder and never persisted (only a fingerprint), and excludes names, emails, AI assessments and letters.
- Cost: USD `NUMERIC(18,8)`; targets USD 0.10 per Game and USD 0.50 per Student; reserve size and daily alert amount are configuration with stated placeholders. Provider, route and model are decided only provisionally (OpenRouter, issue #9) and the EU/ZDR check is still open, so use the mock config and invent no provider values.
- Pilot readiness: 250 Students play at once (NFR-3), 2 s from last Order to new Week, 3 s play page load on throttled 4G; "no mass fallback" is a configurable placeholder threshold. NFR-4 asks for no loss of shown game state, 99.5% availability in Lab hours and a named contact. Founder-owned items (backup level, tracker tool, monitoring, contact, secrets) are recorded as open items with issue numbers, never decided or marked done by a story.
- Accessibility: WCAG evidence with Playwright and axe at 320, 360 and 1440 px (and 200% text, 400% zoom), all copy from `frontend/src/copy/nb.ts`, no horizontal scroll, charts have «Vis som tabell».

## Technical Decisions

- Personal data lives only in `identity` tables; everything else, including job arguments, logs and audit, holds ids only. Free text, AI feedback quoting it and scrubbed `llm_call` bodies are keyed by `user_id` and Class session. Report PDFs and ZIPs are the only stored copies with names, in the private `reports` bucket, so deletion removes the User's PDFs and every ZIP of their Class sessions.
- One shared deletion routine serves both `identity.delete_user` and `ops.retention` (tested through both entry points): write aggregates, anonymise, delete free text and bodies, delete bucket objects. Idempotent, one Student per transaction. A Seat in a running Class game is first handed to an AI via `games.commands.takeover` on the system-actor path with reason `takeover_inactivity` (a case is added to `games.rules.can_take_over`; no new occupancy reason).
- Authorization only through `platform/authz` policies; Admin actions audited via `platform/audit` with ids only. The Admin has no access to Student answers except through the pseudonymised-export gate. Data is read through `reports.scope` (`reporting_games`, `reporting_students`), which excludes lecturer test Games, simulations, `control_test` Class sessions (AD-27) and test Students from every report, statistic, export and funnel. The Admin's only exceptions to "no access to Student answers" are the pseudonymised-export gate and reading Control test data under AD-27, each audited; an Indicative letter a Student turned on is never served to staff. Pseudonym is `HMAC(key, user_id)`, computed in the request and streamed (not a job).
- The sweeper `ops.sweep` is the only timer; this epic adds due actions (retention, cost-limit notice, daily-spend alert), each idempotent with a dedupe key via `platform/notify.enqueue`. New notice kinds are registered in the delivery table (daily alert `immediate`, cost-limit notice `digest`).
- AI boundary: only `app/ai` touches model config, budget and `llm_call`; `ops` and `admin` read cost, fallback and response figures through `ai.config`, `ai.budget` and an `ai` service, never a second sum. The model config id is frozen in `SessionRuntime` at `sessions.lock` (AD-4); editing a referenced config creates a new row. A Class session in LLM mode cannot be locked unless its pinned provider has a key (AD-17).
- Per-session errors (settled in Story 15.8, recorded in the spine's Deferred list): `error_events` table owned by `ops` (migration 0069), written only via `ops.service.record_error(source, code, class_session_id, request_id)`, `source` in `conservation_check`, `job_failed`, `api_error`, fixed code and ids only (no message text); a write failure never fails the caller. `platform/jobs` middleware (hook passed from `worker.py`) and the request log middleware (hook passed from `main.py`) feed it, so `platform` imports no module. Rows hold no personal data and survive retention. Counts do not depend on the external tracker chosen later (issue #28). The Admin reads them on «Drift» (`/admin/drift`).
- Error-reporting adapter (AD-17, Story 15.11): one interface in `backend/app/platform/`, configured by a DSN, recording mock when the DSN is missing and `APP_ENV` is local/test/ci; sends ids, error type and stack only, and also counts the error via `record_error`. The tool itself is not chosen by the story.
- Connection budget (settled in Story 15.9, `docs/ops/connection-budget.md`, revised in place; `BUDGET` in `backend/app/modules/ops/connection_budget.py` must match, enforced by a test): production uses the Supabase session pooler on port 5432 and processes refuse to start on 6543. Placeholder pool sizes `DB_POOL_SIZE` 10/5/5 (backend/worker-ai/worker-batch, `max_overflow=0`), total 25, 50 during deploy overlap, 51 with migration. Each process logs `db_connections_configured`; «Drift» shows the sum. `DB_POOLER_SIZE` is a founder-copied value checked by `ops.service.check_connection_budget()`; unset means "not checked", never passed. Raising worker concurrency changes the budget and must update the file, `BUDGET`, start commands and `scripts/deploy-overlap` together (Story 15.10 owns that tuning).
- Operations commands: load driver plays through the public HTTP API and SSE with generated test Students, never through `games.commands`; `python -m app.ops.loadtest seed` refuses Institutions without the operator flag. `python -m app.ops.preflight` and `python -m app.ops.verify_restore` change no data and print no secrets. Startup guard refuses production start without required secrets.
- Deferred items this epic settles or records: load test method (15.10), whether Invitations are refused without a data processing agreement (15.12, founder decision, flag `REQUIRE_DPA_FOR_INVITATIONS`, always passing for the operator-owned Institution, never holding Lecturer or Admin Invitations), sub-processor register (15.11). Backup level, error/uptime tool and email provider residency stay open founder decisions (issues #28, #29).
- The readiness record in the repository is the founder's go/no-go list: items open with issue number until confirmed; no-go until all passed or a deviation is signed.

## UX & Interaction Patterns

- «Mine data» is reached from a Lenke beside the User's name on Hjem; one row per stored category with «Vis», «Last ned Studentrapport» at top (reusing the report download, stating when it opens before the Test deadline); empty categories say so in text.
- Destructive Admin actions state their consequence in the button copy and complete on one press with no second dialog; one primary button per screen, labelled by its effect.
- Admin area gains «KI-kostnad» (model configs, cost per Class session/Game/day, limit-reached message such as «Grensen er nådd for class-of-1994. LLM-spillerne er byttet til regelbaserte.», two consequence-labelled actions when the reserve is also used) and the operations view («Drift») with error counts, fallback, response times and Play guard share.
- Live views refetch on an AD-8 topic or interval, show «Sist oppdatert», and use the Tilkoblingslinje when stale; Skjelett loading, no spinners.

## Cross-Story Dependencies

- 15.1's personal-data registry underpins 15.2 (deletion handling per table), 15.3 (Roster and Invitation handling) and 15.8 (`error_events` listed as holding no personal data).
- 15.2's shared routine is reused by 15.3 and by 15.10 (anonymising load-test Users); 15.4 shows each Class session's deletion date from 15.3.
- 15.5 creates the «KI-kostnad» area that 15.6 and 15.7 extend; 15.6 calls `assessment.service.resume_for_session` and `stop_for_session` from Story 12.4.
- 15.8's `error_events` feeds 15.10's pass lines and 15.11's adapter; 15.9's budget feeds 15.8's view, 15.10 and 15.14 (preflight prints the pooler check).
- 15.11's readiness record is completed by 15.13 (conformance report) and 15.14; 15.14 also references 15.5, 15.9, 15.10, 15.12 and 15.13.
- Builds on earlier epics: Story 3.5 (sweep and notification delivery), 3.14 (connection budget doc), 13.7 and 13.9 (report download, deletion date), 8.2 (system-actor takeover), 12.4 and 12.7 (assessment commands, operator Institution), 2.2 and 2.12 (model configs, effort measurements), 6.18 (finished-game check).
