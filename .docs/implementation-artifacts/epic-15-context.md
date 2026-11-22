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

- Access: every stored category of a Student's data must be viewable by that Student only, with a CI registry test failing when a table with personal data is not listed. Each registry entry gets a deletion handling too, so access and deletion cannot drift apart.
- Erasure and retention: deletion anonymises the User but keeps Seats, occupancy, `seat_week` rows and the Decision log unchanged, so other Students' Games, charts and reports still render (Seat shown by Role) and stored states still verify through the engine. Deleting a Lecturer who owns Classes is blocked with the same rule and message as role revocation.
- Retention date is the latest effective Test deadline plus a per-Institution period (placeholder default: course end plus six months). Nothing is deleted before the date; aggregates for Cross-class statistics are written first, only over groups of 10 or more Students, and results must be identical before and after deletion. The Control test follows the operator-owned Institution's own date.
- No names, emails or student numbers may survive anywhere after deletion (tables, job tables, local storage mock, report ZIPs).
- Pseudonymised export requires a recorded Institution agreement, a key that is supplied by someone other than the founder at run time and never persisted (only a fingerprint), and excludes names, emails, AI assessments and letters.
- Cost: figures in USD `NUMERIC(18,8)`; targets are USD 0.10 per Game and USD 0.50 per Student; reserve size and daily alert amount are configuration with stated placeholders. Provider, route and model are still open (issues #8, #9, #28, #29), so do not invent provider values; use the mock config.
- Pilot readiness: 250 Students play at once (NFR-3), 2 s from last Order to new Week, 3 s play page load on throttled 4G; "no mass fallback" is a configurable placeholder threshold. NFR-4 asks for no loss of shown game state, 99.5% availability in Lab hours and a named contact. Founder-owned items (backup level, tracker tool, monitoring, contact, secrets) are recorded as open items with issue numbers, never decided or marked done by a story.
- Accessibility: WCAG-level evidence with Playwright and axe at 320, 360 and 1440 px (and 200%/400% text or zoom), all copy from `frontend/src/copy/nb.ts`, no horizontal scroll, charts have «Vis som tabell».

## Technical Decisions

- Personal data lives only in `identity` tables; everything else, including job arguments, logs and audit, holds ids only. Free text, AI feedback quoting it and scrubbed `llm_call` bodies are keyed by `user_id` and Class session. Report PDFs and ZIPs are the only stored copies with names, in the private `reports` bucket, so deletion must remove the User's PDFs and every ZIP of their Class sessions.
- One shared deletion routine serves both `identity.delete_user` and `ops.retention` (one implementation, tested through both entry points): write aggregates, anonymise, delete free text and bodies, delete bucket objects. It must be idempotent and safe to repeat, one Student per transaction.
- A Seat held in a running Class game is first handed to an AI through `games.commands.takeover` on the system-actor path with reason `takeover_inactivity` (no new occupancy reason; a case is added to `games.rules.can_take_over`).
- Authorization only through `platform/authz` policies (`can(...)`, scope helpers); the Admin has no access to Student answers without Class membership except the pseudonymised export gate. Admin actions are audited via `platform/audit` with ids only.
- Pseudonym is `HMAC(key, user_id)` computed in the request, streamed (not a job). Data is read through `reports.scope` so lecturer test Games, simulations, Control test data and test Students are excluded.
- The sweeper `ops.sweep` (Story 3.5) is the only timer; this epic adds due actions for retention, the cost-limit notice and the daily-spend alert, each idempotent with a dedupe key through `platform/notify.enqueue`. New notice kinds must be registered in the delivery table of Story 3.5 (the daily alert as `immediate`, the cost-limit notice as `digest`).
- AI boundary: only `app/ai` touches model config, budget and `llm_call` tables; `ops` and `admin` read cost, fallback and response figures through `ai.config`, `ai.budget` and an `ai` service, never a second sum. A model config id is frozen in `SessionRuntime` at `sessions.lock`; editing a referenced config creates a new row.
- Per-session errors: an `error_events` table owned by `ops`, written only via `ops.service.record_error(source, code, class_session_id, request_id)` with `source` in `conservation_check`, `job_failed`, `api_error`; ids only; write failure never fails the caller; `platform` receives `record_error` injected from `worker.py` and `main.py` so it imports no module. Rows survive retention. Record the settlement in the spine's Deferred list.
- Error-reporting adapter in `backend/app/platform/` behind one interface, configured by a DSN, with a recording mock when the DSN is missing locally/test/ci; it sends ids, error type and stack only.
- Operations: production uses the Supabase session pooler on port 5432 (refuse to start on 6543 because LISTEN/NOTIFY and procrastinate break); connection budget lives in `docs/ops/connection-budget.md` (revise in place) with placeholder pool sizes `DB_POOL_SIZE` 10/5/5 and `DB_POOLER_SIZE` as a founder-copied setting (unset reports "not checked", never passed). Load driver plays through the public HTTP API and SSE with generated test Students, never through `games.commands`; seed command refuses Institutions without the operator flag. Commands `python -m app.ops.preflight` and `python -m app.ops.verify_restore` change no data and print no secrets. Startup guard refuses to start without required secrets in production.
- `REQUIRE_DPA_FOR_INVITATIONS` flag gates Student Invitations via `identity.service.has_processing_agreement`, always passing for the operator-owned Institution and never holding Lecturer or Admin Invitations.
- The readiness record in the repository is the founder's go/no-go list: items open with issue number until confirmed, no-go until all passed or deviation signed.

## UX & Interaction Patterns

- «Mine data» is reached from a Lenke beside the User's name on Hjem; one row per stored category with «Vis», «Last ned Studentrapport» at top (reusing the Story 13.7 download, stating when it opens before the Test deadline); empty categories say so in text.
- Destructive Admin actions state their consequence in the button copy and complete on one press with no second dialog; one primary button per screen, labelled by its effect.
- Admin area gains «KI-kostnad» (model configs, cost per Class session/Game/day, limit-reached message such as «Grensen er nådd for class-of-1994. LLM-spillerne er byttet til regelbaserte.», with two consequence-labelled actions when the reserve is also used) and an operations view of error counts, fallback, response times and Play guard share.
- Live views refetch on an AD-8 topic or interval, show «Sist oppdatert», and use the Tilkoblingslinje when stale; Skjelett loading with no spinners.

## Cross-Story Dependencies

- 15.1's personal-data registry underpins 15.2 (deletion handling per table), 15.3 (Roster and Invitation handling) and 15.8 (`error_events` listed as holding no personal data).
- 15.2's shared routine is reused by 15.3 and by 15.10 (anonymising load-test Users); 15.4 shows each Class session's deletion date from 15.3.
- 15.5 creates the «KI-kostnad» area that 15.6 and 15.7 extend; 15.6 calls `assessment.service.resume_for_session` and `stop_for_session` from Story 12.4.
- 15.8's `error_events` feeds 15.10's pass lines and 15.11's adapter; 15.9's budget feeds 15.8's view, 15.10 and 15.14.
- 15.11's readiness record is completed by 15.13 (conformance report) and 15.14; 15.14 also references 15.5, 15.9, 15.10, 15.12 and 15.13.
- Builds on earlier epics: Story 3.5 (sweep and notification delivery), 13.7 and 13.9 (report download, deletion date), 8.2 (system-actor takeover), 12.4 and 12.7 (assessment commands, operator Institution), 2.2 and 2.12 (model configs, effort measurements), 3.14 (connection budget doc), 6.18 (finished-game check).
