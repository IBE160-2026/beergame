---
status: final
stepsCompleted: [1, 2, 3, 4]
inputDocuments:
  - ../../prds/prd-beergame-2026-10-29/prd.md
  - ../../prds/prd-beergame-2026-10-29/addendum.md
  - ../../architecture/architecture-beergame-2026-11-12/ARCHITECTURE-SPINE.md
  - ../../architecture/architecture-beergame-2026-11-12/SETUP-GUIDE.md
  - ../../ux-designs/ux-beergame-2026-11-05/DESIGN.md
  - ../../ux-designs/ux-beergame-2026-11-05/EXPERIENCE.md
  - ../../ux-designs/ux-beergame-2026-11-05/mockups/
---

# ØL-spillet - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for ØL-spillet, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

Requirement ids are the PRD's own (FR-1 to FR-89, NFR-1 to NFR-10), so every story traces back without a mapping table. The numbering has gaps in reading order because FR-78 to FR-89 were added late; each is listed in the PRD section it belongs to. Glossary terms (PRD §3) are used verbatim. Where the sources disagree, the architecture spine wins over the PRD's assumptions and the UX spines win over the mockups; known conflicts are listed at the end of the inventory.

## Requirements Inventory

### Functional Requirements

**4.1 Accounts, roles and the Admin area**

- FR-1: The Admin can send an Invitation to an email with the Lecturer or Admin role built in; the link creates an account with the role granted; an expired or used link shows a message and a way to ask for a new one.
- FR-2: The Admin can search Users by email or name and grant or revoke the Lecturer or Admin role; the role takes effect at next page load; revoking from a User who owns Classes is blocked until another Lecturer is added or the Classes are archived.
- FR-3: The Admin can list, search, deactivate and reactivate Users, resend Invitations and create Institutions; deactivated Users cannot log in; every Admin action, Takeover by a person and Completion status correction goes to an audit log with actor, time and change.
- FR-4: A person following an Invitation creates an account with password and profile (email prefilled, not editable) and logs in with email and password; password reset by email; one email maps to one User, and an Invitation to an existing account adds the role.
- FR-5: Access is restricted by account role: Students see only their own data; Assistant lecturers only their attached Classes; the Admin sees all Users but no Student answers or AI assessments unless attached to the Class.

**4.2 Classes, Rosters and Invitations**

- FR-6: A Lecturer can create a Class (name, Institution, optional course code), becomes owner, and can archive it; archived Classes are read-only and kept for statistics until retention ends.
- FR-7: A Lecturer can upload a Roster as .xlsx or CSV or paste addresses, pick the email column, see malformed or duplicate addresses by row with a reason while valid ones are accepted, and add or remove single addresses later.
- FR-8: A Lecturer can send Invitations to all unregistered Roster addresses with a validity period (default 14 days) and sees counts of sent, bounced, accepted and expired.
- FR-9: A Lecturer sees each address's status (invited, registered, unregistered after expiry), can resend with a new validity period, and can register a Student manually.
- FR-10: A Lecturer can add co-owner Lecturers and invite Assistant lecturers by email for that Class only.

**4.3 Class session setup**

- FR-11: A Lecturer can create a Class session prefilled with the Classic defaults (inventory 12, 4 per slot, delays 2/2/2, demand 4 stepping to 8 in Week 5, costs 0.50 and 1.00, 36 Weeks, Guided Weeks 1 to 4) and save it unchanged, in under 10 minutes.
- FR-12: A Lecturer can change every Game setting before the Start date (starting inventory or backlog, supply-line contents, delays 1 to 3 Weeks, costs, Weeks, Guided Weeks, maximum Order, Demand pattern, Information visibility, capacity); out-of-range values are rejected with the range shown; listed combinations warn without blocking; settings lock at the Start date.
- FR-13: A Lecturer can choose a Demand pattern: fixed series, step, random (discrete uniform, seeded), or step plus noise; every Class game in the Class session uses the same series; the seed is shown, stored and editable.
- FR-83: A Lecturer can set Information visibility: off by default; optional view of the upstream and/or downstream neighbour's inventory and backlog; applies to all Class games, may differ in the Replay scenario; AI players get the same numbers; the Decision log records what was visible.
- FR-14: Students never see the number of Weeks or the demand series while playing; only the Retailer sees customer demand, one Week at a time; Students are told to play as if the business continues.
- FR-15: A Lecturer can set the AI mode to LLM players (default) or Rule-based players for the Class session; a full no-LLM path exists together with FR-44 code-only Debrief and FR-61.
- FR-16: A Lecturer can set Debrief mode: Group debrief (default) or Personal debrief.
- FR-17: A Lecturer can mark a Class session as obligatory until the Start date. Completion requires every step, with the Class game step needing Orders in a set share of Weeks (default 80%). Includes: Student notices and Takeover warning, shortfall reasons shown to the Lecturer, make-up game, minimums for auto-submitted tests and Explanations, per-Student adjustments, message to those not met, and logged Completion corrections.
- FR-18: A Lecturer can set Start date, Play deadline, Debrief deadline and Test deadline in order (Test defaults to 7 days after Debrief); Students see the next deadline and get a reminder 24 hours before; extensions per Class session or per Student; lock points per setting.
- FR-19: A Lecturer can add Lab hours (date, time, place); Students see them on their home screen and by email.
- FR-87: A Lecturer can play a private test Game with chosen settings against three AI players; it never appears in any report, statistic or export.

**4.4 Groups and Class games**

- FR-20: The system allocates registered Students at random into Class games of four with random Roles; a remainder game gets AI players; the Lecturer previews, can re-run, move or swap before the Start date; late registrants take a free AI-held Seat in a game not yet started, else a make-up.
- FR-21: Optionally, Students choose a Class game and a free Seat (one Seat per Class session); unseated Students are allocated at random at the Start date.
- FR-22: From the Start date every Student sees their Class game, Role and the other Seats; the game starts when the first Student presses start, or when the Lecturer starts one or all; Students can propose and accept a time to play with no free text.
- FR-84: Before the first Order each Student sees a briefing: objective (lowest chain Total cost), same-Week ordering, delays, must-ship rule, Guided Weeks, no discussing Orders; product text never says "Beer Game" or "bullwhip" before the Debrief, except the product name.
- FR-85: Before the first Order (or before the Debrief if none was placed) each Student does the Starting task, about five minutes, scored by computed rules, counting toward nothing, ending with an optional played-before question.

**4.5 Gameplay**

- FR-23: A Student sees for their own Seat: inventory or backlog, incoming order, incoming delivery, units shipped, Supply line contents, own Order history, running Total cost, Week number and Posisjon (row and chart line); nothing of other Seats beyond Information visibility; all visible with the Order input at 360 px without horizontal scroll.
- FR-24: A Student enters one whole-number Order per Week from 0 to the maximum and confirms it; invalid input is rejected inline; a confirmed Order cannot be changed; in Guided Weeks the Order is fixed and automatic and the Week advances when every Student has opened it; the clock for the Inactivity limit runs there from the first Student's opening, and opening counts as ordering for FR-36 and FR-37 (founder decision 2026-11-12, changed in the PRD).
- FR-25: Every Student sees which Seats have ordered and which the game waits for (Role and name or "AI player") and for how long, on the game screen and the home screen.
- FR-26: A Week runs one sequence (receive, fill orders and backlog within stock and capacity, ship, show, order, charge costs on end-of-Week balances, advance slots); the new Week shows within 2 seconds of the last Order; state is stored before it is shown; reload or device switch loses nothing.
- FR-27: A Student gets an email when the game has waited for their Order, gathered in one message per day and never at night.
- FR-28: A Class game ends after the last Week or by playout; the last Week runs in full; on end every Student sees the chain's Total cost first, then cost per Role, and is led to the Debrief.
- FR-29: Bookkeeping is correct by construction (no simultaneous inventory and backlog on an uncapped Seat, units conserved, costs equal rates times units); an automated check runs over every finished Game and logs violations.

**4.6 AI players**

- FR-30: The system places an AI player in every empty Seat at the Start date, in the three other Seats of a Replay, and in a Seat at Takeover.
- FR-31: An AI player receives only what a Student in that Seat would see; the prompt frames a supply chain manager's job, not a game; no customer demand except for the Retailer; no personal data; no model call in Guided Weeks.
- FR-32: Every LLM Order is requested as schema-bound JSON and checked against the schema and game rules; up to 5 retries, then the Rule-based Order for that Week only, marked in the Decision log; per-attempt timeout and per-Order time budget per Effort level; no time limit in the playout.
- FR-33: Each AI player type has a plain-language description for Lecturers; the Rule-based player follows a documented anchoring-and-adjustment rule with primary-source parameters; Lecturers get short material on the AI and why not to grade from it.
- FR-34: Every AI player is labelled as AI wherever Seats are shown, including after Takeover and after a Play guard switch; all AI-generated text is marked for people and in machine-readable form, including in PDFs.
- FR-78: A Lecturer who chose LLM players can set an Effort level for the Class session; only levels the pinned endpoint supports and that were measured inside the cost and time limits are offered; stored with the Class session and in the Decision log.
- FR-79: The Play guard compares each LLM Order with a Rule-based reference and a near-optimal reference over a rolling window and switches the Seat to Rule-based for the rest of the Game when outside the band; no switch before a minimum number of Weeks; the switch is logged and shown; the share of switched Seats is reported.

**4.7 Inactivity, Takeover and deadlines**

- FR-35: The system records per Seat when each Week opened and when the Student ordered.
- FR-36: When a Student has not ordered and another Student has ordered and waited for the Inactivity limit (default 24 h, floor 20 h), an AI player takes over; nothing happens if nobody ordered; none while paused; all parties are notified; games marked as in the room during a Lab hour use a shorter limit (default 10 min, 2 to 120).
- FR-37: A Lecturer or Assistant lecturer can trigger Takeover of any Seat, and fill all absent Seats in one or all Class games in one action; a Student can reclaim at the start of a later Week; AI Weeks stay marked.
- FR-89: Any Student or the Lecturer can pause a Class game; only the Lecturer sets an agreed time; no automatic Takeover while paused; an Order ends the pause; a Student can put an AI player in an absent Seat once that Seat's time has run out; the pause does not move the Play deadline.
- FR-38: At the Play deadline every unfinished Class game is played to its last Week by AI players; Students see that it ended at the deadline and are led to the Debrief.

**4.8 Lecturer overview and Messages**

- FR-39: Staff see all Class games in a Class session with current Week, status, whom each waits for and for how long, each Seat's occupant and running chain Total cost; games near Takeover are highlighted; updates within 5 seconds without reload; shows the Class session funnel.
- FR-40: Staff can send a one-way Message to a Class session, one Class game or one Student; it appears in the product and by email.

**4.9 Debrief and Debrief quiz**

- FR-41: Early in the Debrief, before demand is revealed, each Student writes an Explanation; the Debrief does not move on until it is saved; others do not see it; it is stored unchanged.
- FR-42: The Debrief opens when the Student's Class game has ended; the Lecturer chooses between open Debriefs and holding all until every Class game has ended.
- FR-43: Any Student of a Class game can open a shared Group debrief; joined Students see the same step; step control rules; the reveal is gated per Student on a saved Explanation; fallback to Personal debrief after 48 hours or on dropping out.
- FR-44: The Debrief shows revealed demand, Orders, inventory and backlog per Role in one chart with a text alternative, amplification, at least three own moments per Student with Detected pattern and mechanism, what other Roles saw, the Explanation next to the data, and the AI-held share of chain cost; every number matches the Decision log; narration only connects computed facts; code-only fallback; a path for Students with fewer than 10 own Orders.
- FR-45: The Debrief asks reflection questions in sequence and allows bounded follow-up questions that stay on topic, use the same computed facts, give hints rather than answers, and close when the Student's Individual test opens.
- FR-46: After the Debrief each Student takes the Debrief quiz and must answer every fixed question correctly; wrong answers are explained; unlimited retries until the Test deadline; a Lecturer can exclude a question; attempts are visible to the Lecturer.
- FR-47: At the end of the Debrief the system stores a Debrief summary per Student (key moments, reflection answers, completion time, later quiz attempts), readable by staff.

**4.10 Replay**

- FR-48: A Student who passed the Debrief quiz can start the Replay before the Test deadline, in the same Role, against three AI players in the Class session's AI mode, resumable on any device.
- FR-49: The Replay uses a Replay scenario; the default keeps the Class game's demand levels with random variation (spread 2), a per-Student step Week (5 to 12) and length (30 to 40 Weeks), no Guided Weeks and a fresh seed; the Lecturer may set every Game setting; end and demand stay hidden.
- FR-50: At the end of the Replay the Student gets a short AI walkthrough (Total cost, chart, not-like-for-like comparison with the Class game, one or two own moments) under FR-44's rules, plus two optional questions.

**4.11 Individual test**

- FR-51: A Student can open the Individual test after the Replay until the Test deadline; answers autosave; the Student can return and submits once; a one-sitting time limit is a Lecturer option; unsubmitted answers are auto-submitted at the deadline; the Student states the work is their own.
- FR-52: The product provides a Norwegian question set with Item weights: multiple choice by answer key, Interactive items and long answers; it repeats the Starting task items, asks once in the Explanation's wording, and includes an unseen Demand pattern item; the Lecturer can exclude questions and change weights, which sum to 100%.
- FR-53: The test includes Adapted items from the Student's own Class game and Replay, built from shared templates with facts matching the Decision log, at a fixed total weight (default 30%); previewable by the Lecturer; replaced by Core items for Students with fewer than 10 own Orders.
- FR-80: The test includes Interactive items answered in a graph, table or diagram, scored by computed rules on quantities and consistency with partial credit; table and number entry are built first, drawn items later; all are operable by keyboard and screen reader.
- FR-81: Long-answer and Adapted items are scored against one Scoring guide (5 to 8 coded criteria per question, one five-step scale); a default guide ships; a Lecturer can edit it until the Test deadline; an edited guide is flagged as unchecked until a Control test is run with it.

**4.12 AI assessment and reports**

- FR-54: After the Test deadline the system produces an AI assessment per submitted test: computed scores, one overall score with written feedback per long-answer and Adapted item, and a weighted total; feedback quotes the Student's text; facts match the Decision log or the feedback is regenerated once and then dropped with a note; ready within 24 hours; no pass/fail.
- FR-55: A Student gets an email when the AI assessment is ready and reads it in the product; staff can read it for their Classes; every view states it is AI-generated, can be wrong and is not a grade; a Student can flag feedback with one click.
- FR-56: A Lecturer can turn the Indicative letter on for a Class session; where off, a Student can turn it on for their own view (hidden from staff); it can be made unavailable; thresholds are a Lecturer setting; it never appears in the Completion export or affects Completion.
- FR-57: A Student can download their Student report as a PDF after the Test deadline until data deletion; ready within 30 seconds; Students are told to download before deletion.
- FR-58: The Student report holds, in Norwegian: identity and dates, Completion status, Class game table and chart, Explanation, key moments, quiz attempts, Replay, the test with answers and computed scores, and optionally the AI assessment section (off by default); others appear by Role only; steps not done are marked; it states it is not a grade.
- FR-59: Staff can download any Student report at any time, or all reports as one ZIP (never with the AI assessment section), ready within 10 minutes with a notification.
- FR-60: A Lecturer can export the Completion status as CSV or Excel (name, email, step dates, share of Weeks ordered, requirement met), with no AI scores or feedback.
- FR-61: A Lecturer can turn off the AI assessment for a Class session; computed scoring and the Student report remain.
- FR-82: The Admin can set up a Control test with marked test students whose data never enters any Class session result; humans score blind; the product shows human and AI scores side by side with agreement measures; consent is recorded; it runs with the default or an edited Scoring guide.

**4.13 Insight, Class reports and Cross-class statistics**

- FR-62: Staff can open any Game and see per Week and Seat: incoming order, delivery, inventory, backlog, Order, cost, occupant with Takeover marked, and fallback marks; charts for all Roles plus demand; links to Explanations and Debrief summaries.
- FR-63: Staff can open one Student's page with Class game, Explanation, Debrief summary, quiz attempts, Replay, Individual test, AI assessment and a link to the Student report.
- FR-64: A Lecturer sees a live Class report: funnel, Total cost distribution and Order amplification per Role, most common Detected patterns, Starting task versus test items, results per question, AI assessment score distribution with a Core-only subscore, and the share of AI-played Seats.
- FR-65: A Lecturer can compare accessible Class sessions on Class report measures with filters; differing sessions are labelled; an anonymised aggregate over groups of at least 10 survives deletion; cross-Institution views are Admin only.
- FR-86: After the Play deadline and their own Debrief, Students see an anonymised chart of every Class game's Orders per Role with their own marked; the Lecturer gets a plenary view; no names, no ranking.
- FR-88: A Lecturer can export a Class session's week-by-week Game data as CSV, with no AI assessments.

**4.14 Rerun**

- FR-66: A Lecturer can create a new Class session by copying an earlier one's settings; dates, Lab hours and Roster are not copied; a fresh seed is drawn unless the old one is kept.

**4.15 Decision log and AI operations**

- FR-67: The system stores every Order in every Game with the state the Seat saw, who placed it, the Rule-based reference Order for every Seat, and for LLM players the full call metadata; all other LLM calls are logged with model, prompt version, tokens and cost.
- FR-68: The Admin selects the model for a Class session after all-AI test runs; all LLM use in the Class session stays on one model version, endpoint and prompt versions with no router fallback; reports show the Share of LLM Orders per Game; a model can be frozen across Class sessions.
- FR-69: The Admin sees AI cost per Class session, Game and day and sets a cost limit; at the limit LLM players switch to Rule-based for the rest of the Class session and the Lecturer is notified; budget is reserved for Debrief and AI assessment; a daily spend alert.
- FR-70: At the end of the Replay and after any Class game with AI players, each Student is asked one optional five-point question on how believable the AI players' ordering felt; results per AI mode in the Class report and statistics.
- FR-71: The Admin can export the Decision log, Starting task results, Explanations and test answers of chosen Class sessions with stable pseudonyms, where the Institution has agreed.

**4.16 Language and devices**

- FR-72: All screens, emails, Debriefs, quiz, test, AI assessments and reports are in Norwegian bokmål.
- FR-73: Every Student flow works from 360 px wide, on tablet and on laptop; long answers advise a larger screen on a phone; Lecturer overview and Game insight are laptop-first and usable on a tablet.
- FR-74: A Group debrief can be shown on one shared screen while each Student answers on their own device.

**4.17 Data rights**

- FR-75: A Student can see all data the product stores about them.
- FR-76: The Admin can delete a User and their personal data on the Institution's instruction; their Seats remain as anonymous Seats.
- FR-77: Student personal data in a Class session is deleted automatically a set period after the Test deadline, configurable per Institution.

### NonFunctional Requirements

- NFR-1 Responsiveness: a Week advances for connected Students within 2 seconds after the last Order (excluding AI thinking time); play pages load within 3 seconds on 4G.
- NFR-2 AI player latency: each Effort level has a per-attempt timeout and a per-Order time budget including retries; slower Orders are replaced by fallback. Values come from the prototype.
- NFR-3 Scale: at least 400 Students (100 Class games) per Class session; 250 Students playing at once without degradation, shown by a load test that includes provider rate limits; rate limits do not cause mass fallback; at least 5 such Class sessions at once.
- NFR-4 Reliability: no ordered Student waits longer than the Inactivity limit unless paused; no Class game stalls on an AI provider failure; 99.5% availability during Lab hours; no game state lost once a Week is shown; a named contact during Lab hours.
- NFR-5 Reconnection: a Student who loses connection resumes at the current Week on any device.
- NFR-6 Accessibility: WCAG 2.1 AA on Student and Lecturer screens; chart alternatives; tagged PDF reports with table alternatives; role and status never by colour alone; an accessibility statement and conformance report.
- NFR-7 Security: role check on every request; encryption in transit and at rest; audit log for Admin actions; reports only for an allowed logged-in User; download links expire.
- NFR-8 Observability: per Class session the Admin sees error counts, fallback rate, AI response times and AI cost.
- NFR-9 Correctness: game arithmetic verified on every finished Game; every number the AI shows comes from computed facts.
- NFR-10 Email delivery: authenticated sending domain; bounces reported to the Lecturer.

**Constraints that bind stories (PRD §6, §7)**

- C-1 Privacy: no names, emails or student numbers reach any LLM provider; free text is scrubbed against the whole Roster first; providers are EU-region, zero-retention, no-training sub-processors and stay swappable.
- C-2 AI regulation: all AI output is disclosed and marked; v1 has no grading; AI scores stay out of the Completion export and the ZIP, and out of the Student report by default; Completion rests on system events only.
- C-3 Cost: at most USD 0.10 AI cost per Game and USD 0.50 per Student per Class session; only measured Effort levels are offered.
- C-4 Content: all graphics, texts, Debrief content and test questions are original.
- C-5 Non-goals: no public sign-up or payment, no Feide or LTI, no player chat, no grading, no proctoring, no Student-facing ranking, no native apps, no other language, fixed flow.

### Additional Requirements

**Greenfield scaffold (affects Epic 1, Story 1)**

- No starter template is named. The first story scaffolds the repo by hand from the spine's Structural Seed: `api/` (one uv project, Python 3.14, FastAPI, with `engine/`, `analysis/`, `ai/`, `platform/`, `modules/`, `main.py`, `worker.py`, `sim.py`, Alembic migrations, tests), `web/` (Next.js 16 App Router, standalone output, TypeScript 6, Tailwind 4, shadcn), `proxy/Caddyfile`, `docker-compose.yml` and `railway/` per-service config. Versions are pinned in the spine's Stack table.
- Local runs with zero keys: `docker compose` starts postgres:17, api, worker-ai, worker-batch, web and proxy; every integration is a deterministic mock; an empty database is seeded with a demo Class (Admin, Lecturer, 8 Students) in `APP_ENV=local` only (AD-17).
- Production refuses to start when a required secret is missing or default; LLM-mode Class sessions cannot be locked without a provider key (AD-17).

**Epic shape: vertical slices with shared folders (founder decision 2026-11-12)**

- Each epic is a vertical slice: its code is as isolated as possible, in its own `api/app/modules/<slice>/` and `web/src/modules/<slice>/`, and reaches other slices only through their `service.py` (spine, Module layout).
- Nothing is written twice (DRY). Code that two or more slices need lives in a shared folder, never copied into a slice:
  - backend: `engine/`, `analysis/`, `ai/`, `platform/`;
  - frontend: `web/src/components/` (design-system controls and `charts/`), `web/src/lib/` (API client, drafts, preview, number formatting) and `web/src/copy/`.
- A story that needs something shared adds it to the shared folder in that story, or reuses what an earlier story put there. A story never depends on a later story for a shared component.
- A component stays inside its slice while only that slice uses it, and moves to the shared folder the first time a second slice needs it.

**Build order (PRD §8.1, AD-22)**

- The prototype comes first and is not throwaway: `python -m app.sim` runs headless all-AI Games through the production engine, `games.commands`, players and AI gateway with `purpose=simulation`, supports `scripted` occupants and batches per model config and Effort level, and charges a separate evaluation budget.
- Order after that: engine and AI players; then accounts, Class session setup, allocation and Lecturer overview; then Debrief, quiz, Replay, test and AI assessment; then reports, Completion export and Class report.
- Cut-list items sit behind `FEATURE_*` flags and may wait until after the pilot: FR-21, cross-Institution FR-65, FR-66, FR-83, FR-87, FR-88, capacity in FR-12 (AD-17).

**Architecture rules every story must respect**

- AD-1: all game arithmetic lives in the pure `engine` (`advance(settings, state, orders) -> state`); `engine` and `analysis` do no I/O, read no clock and take randomness only from a passed seed. Rule-based player, near-optimal reference and Play guard statistics are pure functions there.
- AD-2: only `games.commands` mutates Games, Seats, occupancy, turns and Week states, one transaction per command with a row lock on the Game, a `version` increment and the change event; `week_complete` advances exactly one Week; Pause columns and `lifecycle` have named writers; `playout` runs once at the Play deadline.
- AD-3: `seat_state` (numbers only, one versioned Pydantic model) is the single information boundary for the play screen, the LLM prompt and the Decision log; `table_status` carries people and is never stored or sent to an LLM.
- AD-4: `sessions.lock` at the Start date freezes settings, demand series and seed, engine `rules_version` and `SessionRuntime` into every Class game; other Game kinds snapshot at creation; finished Games are replayed by the engine to verify stored states.
- AD-5: occupancy is an append-only history; `players.ensure_order` is the one order source for non-student occupants; LLM Orders run as `ai-orders` jobs with one gateway call; reference Orders are computed once per Seat when the Week opens; a 5-second rescue loop in `worker-ai` places fallback Orders; playout Orders go to `llm-batch` without a deadline.
- AD-6: `app/ai` is the only LLM boundary: pinned model config per scope, budget reservation on one row, Roster scrubbing with an offset map, per-endpoint rate limiter, at most 6 attempts per player Order, schema validation, one `llm_call` row per attempt, versioned prompt files, deterministic mock without a key.
- AD-7: AI text only connects computed facts: stored `fact_sets`, fact ids and sentence-template ids in the output schema, a validator, quotes as character spans mapped back to the original text, and a code-rendered fallback. `modules/debrief` never imports `modules/players`.
- AD-8: push invalidates, pull reads: `NOTIFY` carries `{topic, id, version}` only; a closed topic catalogue with a registry test; one SSE stream per User at `GET /api/events` with scope filtering, coalescing, heartbeat and timed reconnect; the web app maps topics to TanStack Query keys and refetches over REST.
- AD-9: timers are columns; the per-minute `ops.sweep` finds due work and calls the owning command; all jobs are idempotent with id-only arguments; Test close is one ordered chain; queues are split between `worker-ai` and `worker-batch`; notifications go through `platform/notify` and `messaging`, with `immediate` kinds (Invitations, password resets, sent Messages, Takeover notices) and `digest` kinds (one mail per User per day, none between 22:00 and 07:00 Europe/Oslo).
- AD-10: the web app is presentation only, typed from a generated OpenAPI client with a CI drift check; the only client arithmetic is the Order preview in `web/src/lib/preview.ts`; unsent input lives in `web/src/lib/drafts.ts`; test answers autosave with per-answer revisions.
- AD-11: one origin behind Caddy; email and password login with a hashed-then-bcrypt password; HS256 JWT in an `httpOnly; Secure; SameSite=Lax` cookie; `X-Requested-With: olspillet` on every mutating request; single-use hashed tokens for Invitations and resets; Postgres-backed rate limits; the first Admin from `BOOTSTRAP_ADMIN_EMAILS`.
- AD-12: all authorization goes through `platform/authz` policies and scoped query helpers; no `if role ==` in modules; two audited Admin exceptions (pseudonymised export, Control test).
- AD-13: every Game has a `purpose` (`class`, `replay`, `makeup`, `lecturer_test`, `simulation`); `games.policy(purpose)` is the one behaviour table; every report, statistic, export and funnel reads through `reports.scope`.
- AD-14: names, emails and student numbers live only in `identity` tables; one shared routine serves retention and deletion; aggregates for Cross-class statistics are written before deletion over groups of 10 or more; pseudonyms are `HMAC(key, user_id)` with a key held by someone other than the founder and never stored.
- AD-15: `seat_week` rows are written once by `place_order` and never updated; `decided_by` and `fallback` are separate fields with one mapping for all readers; corrections are new rows; staff actions go through `platform/audit`.
- AD-16: step events live in `modules/progress` (`record_step`, `has_step`, a closed step enum); `analysis.completion` is the only definition of Completion and has no AI input.
- AD-18: one chart module, `web/src/components/charts` (Recharts for standard charts, hand-made SVG for the chain band and matrix wall), fixed-width rendering, a table alternative for every chart; the first chart story is a spike on column alignment and WeasyPrint output; reports render from a snapshot through the internal `/print/report/<snapshot_id>` route to tagged PDF in `worker-batch`; signed short-lived download URLs; veraPDF in CI; fonts self-hosted.
- AD-19: UI copy lives in `web/src/copy/nb.ts`, email and PDF copy in Jinja2 templates and the print route; the API returns stable error codes; a CI test fails on «Beer Game» or «bullwhip» in pre-Debrief copy.
- AD-20: `seat_turns` holds one row per Seat per open Week with all due times; `games.rules.turn_times` and `can_take_over` are the only computations of timing and Takeover eligibility.
- AD-21: `debrief.commands` is the only writer of a Debrief session; presence is server-side; the reveal gate is checked in the API; the shared screen uses a server-side anonymised endpoint.
- AD-23: question sets, quiz, Starting task, Adapted item templates, sentence templates, Detected pattern definitions and Scoring guides are immutable versioned records in `modules/content`, pinned at `sessions.lock` (Scoring guide at the Test deadline).
- AD-24: api and both workers are built from one image and commit; Alembic owns every schema change including procrastinate's; migrations are expand-then-contract.
- AD-25: `game_summaries` holds one maintained row per Game and is the only source of Game status for lists and overviews; the funnel is cached per Class session.
- AD-27: a Control test is a Class session with `kind=control_test` in an operator-owned Institution; `human_scores` are write-once; AI scores are hidden from a scorer until their own score is in; `analysis.agreement` is the only source of the agreement measures; the `checked` flag on a Scoring guide comes only from a completed Control test.

**Conventions (spine, Consistency Conventions)**

- Glossary terms in English in code, Norwegian only in copy; module layout `routes.py, service.py, repo.py, models.py, schemas.py, jobs.py`, one owning module per table; UUIDv7 ids; `timestamptz` UTC shown in Europe/Oslo; integer units, `NUMERIC(14,4)` money as decimal strings in JSON; list and error envelopes; AI text as `{text, ai_generated, llm_call_id}`; structlog JSON with no personal data.
- Testing: pytest with golden traces and full branch coverage as the aim for engine and analysis (addendum §B reference trace); Vitest; Playwright at 320, 360 and 1440 px and 400% zoom with axe.

**Infrastructure, deployment and CI (SETUP-GUIDE)**

- Railway project `olspillet`, EU West, five services (`proxy`, `web`, `api`, `worker-ai`, `worker-batch`), private networking, only `proxy` public; `production` branch auto-deploys, `main` is the working branch; pre-deploy `alembic upgrade head`; health checks; no staging environment.
- Supabase Postgres 17 in eu-central-1 through the session pooler on port 5432 only, with a written connection budget; one private Storage bucket `reports`.
- Resend with a verified domain, sending region eu-west-1 and a signed bounce webhook at `/api/webhooks/resend`.
- CI in GitHub Actions: ruff and pytest with Postgres 17 and golden traces; web typecheck, Vitest and build (with the openapi-typescript TypeScript override); OpenAPI contract check; copy check; Playwright with axe against docker compose; veraPDF on a sample report; a simulation smoke run on the mock provider.

**Decisions the spine defers to stories (each story must settle its item)**

- Takeover and Spillstyring stories: ending «I rommet», batch Takeover over many Games, closing Replays at the Test deadline, the actor on an occupancy row, conflict errors naming who acted first.
- Lecturer overview story: how wall filter aggregates (median and average rows) are served.
- Allocation and Roster stories: how a previewed allocation is kept so confirm commits what was shown; where an uploaded Roster file waits (staged rows are personal data with a short expiry).
- Debrief and Individual test stories: when narration and Adapted items are generated; a Group debrief step never waits on an LLM call; an Adapted item never changes after a Student has seen it.
- Replay story: the Replay scenario template with ranged fields and the pure function from template and seed to `GameSettings`.
- Individual test story: the `tests` command list, attempt row lock, save-after-submit error and deadline action order.
- Admin operations story: the store for per-session error counts (NFR-8), decided with error tracking.
- Before the first engine change after a real Game: how older `rules_version`s stay runnable.

**Open inputs from the prototype and issues (stories leave slots, not guesses)**

- LLM provider, route and model (issues #8, #9); Effort levels, timeouts and Order time budgets; budget reserve size; time allowed for the playout.
- Play guard distance measure, window, minimum Weeks and near-optimal algorithm (issue #20).
- Rule-based player parameters from Sterman 1989 (issues #8, #17).
- Operations before the pilot: backup level, error tracking and uptime monitoring, load test, connection budget (issue #28); email provider data residency (issue #29); sub-processor register and data processing agreement gate; CI gating and promotion to production.
- Non-code deliverables that stories depend on: question set, Debrief quiz, Starting task and Scoring guide (issue #16); Lecturer material on AI (FR-33).

**Known conflicts between sources**

- Fonts: DESIGN.md says Source Sans 3 is loaded from Google Fonts; AD-18 self-hosts it through `@fontsource/source-sans-3` and makes no request to Google Fonts. The spine is later and wins.
- Turn reminders: FR-27's assumption (after 2 hours, then 4 hours before Takeover) is superseded by AD-9: reminders are `digest` mail, at most one per User per day and never between 22:00 and 07:00. Takeover notices are immediate.
- Layout: addendum §B's portrait board with goods flowing down is superseded by the horizontal chain in EXPERIENCE.md.
- Posisjon: mockups `05`, `09` and `10` show Posisjon in the Replay only; the spines show it in both rounds, with only the projection Replay-only.

### UX Design Requirements

**Foundation and tokens**

- UX-DR1: Implement the colour tokens from DESIGN.md as the app theme (`paper`, `ink`, `ink-secondary`, `ink-muted`, `hairline`, `axis`, `future-tint`, `lager` and fill, `restordre` and fill, `projection`, `bar-base`, `order-history`, the `net-neg-*`, `net-pos-*`, `net-zero` and `flow-*` steps). Light theme only; `paper` is the only background.
- UX-DR2: Enforce the text-on-tint table: only the listed text tokens on each background, every pair at 4.5:1 or better; links on tinted rows are `ink` underlined.
- UX-DR3: Implement the typography tokens in Source Sans 3 (400, 600, 700), sized in `rem`/`em`, with tabular lining figures in every cell, axis, table, cost panel and matrix, and proportional figures only in `figure-hero` and `figure-amplification`. No all caps or letter-spacing.
- UX-DR4: Text floors: 13 px on phone, 9 px on the matrix wall; text never shrinks to fit, columns get fewer instead.
- UX-DR5: One Norwegian number formatter: space as thousands separator, decimal comma, kroner to two decimals, true minus sign, narrow cells may drop decimals.
- UX-DR6: Shapes and depth: `rounded.sm` on controls and cards, `rounded.xs` on the column highlight, `rounded.full` on dots and the switch, square corners on all data marks; no shadows, gradients, raised cards or layering.
- UX-DR7: Shared interaction states for filled controls, outlined controls and links (idle, hover, focus-visible, pressed, disabled, error); idle borders of interactive controls use `ink-muted`.
- UX-DR8: Focus ring on every interactive element (`focus-ring` with a `paper` gap; `focus-ring-inset` in tables and the wall), never removed; controls that become unavailable while focused use `aria-disabled` and keep focus, never native `disabled`.

**Controls**

- UX-DR9: Knapper: one primary button per screen, labelled with its effect («Bekreft ordre på 24»); secondary buttons never commit irreversible state; a button that cannot act is disabled, not secondary.
- UX-DR10: Lenke: `lager`, weight 600, underlined; navigates or opens a panel, never commits.
- UX-DR11: Tekstfelt: label above; invalid state with a `restordre` border and the reason beside it.
- UX-DR12: Valgknapper, Bryter and Visningsbryter: segmented controls and a switch with a text label; Klasseøkt choices apply on «Lagre Klasseøkt» and state their scope in help text.

**Game screen**

- UX-DR13: Topplinje: Uke, Rolle and Spill, and a Totalkostnad button (hit area at least 44 px) that opens Alle rader og kostnad; never shows the number of Uker.
- UX-DR14: Kjedebånd: the Seat's own link as a horizontal flow with stock or backlog bar, order line on top, goods line below, På vei boxes at true scale, the just-typed order box, overdue goods as a dashed box; updates as the order is typed; reads as text for screen readers. Factory shows «Produksjon», Retailer shows «Kundene».
- UX-DR15: Kjedebånd scale rule: pixels per unit derived from the band width so the worst Uke fits at 320 px; labels wrap rather than overlap; a product test checks every Uke of a Classic game at 320 and 360 px. The four-Role variant is used in the Debrief and staff views.
- UX-DR16: Graf over tabell: Netto lager line with fills above and below a true zero, the Posisjon line (thinner, square markers, no fill, direct label), stacked Kost per uke bars, the week table on the same columns, the now-line labelled «Nå», and `future-tint` right of it.
- UX-DR17: Graf over tabell behaviour: one column per Uke with the right edge at nå + 4; typing an order writes Din ordre at nå and Levering at nå + 4 joined by a line; known arrivals are outlined and marked as ordered, not guaranteed; Netto lager cells use the matrix steps with signed numbers.
- UX-DR18: Graf over tabell at narrow widths: graph and table are one scroll region (`role="region"`, «Graf og tabell», `tabindex="0"`) with a sticky label column, a minimum column width of 1.6 em, a visible scrollbar and «Sveip for tidligere uker»; it scrolls nå into view on load and after each Uke; the table is an HTML `<table>` with `th` scopes; tests at 320 and 360 px at 100% and 200% text.
- UX-DR19: Projection: a dashed line ending in a hollow dot with its explanatory sentence, in the Replay only.
- UX-DR20: Ordrefelt: `type="text" inputmode="numeric"`, − and + segments («Én færre», «Én flere»), always-visible help line, empty, typed, invalid, out-of-range and read-only states, error timing on blur or press, Enter moves focus to the button and never submits.
- UX-DR21: Alle rader og kostnad: a full phone screen with all rows, the two column-sum lines, and Kostnad så langt; returns to the order with the typed value kept and focus on the opening link.
- UX-DR22: Kostnad så langt: Lagerkostnad and Restordrekostnad rows with bars, Totalkostnad, «Totalkostnad over tid» stacked area with «Vis som tabell», and the week's sum line; pinned beside the order on laptop, one tap away on phone; recalculates when a Uke is charged.
- UX-DR23: Uke-overgang: «Uke n er ferdig regnet» with deltas and the week's sum; the now-line moves one column; «Hopp over» skips the animation, which never blocks input and never exceeds 2 s; no animation with reduced motion.
- UX-DR24: Information visibility display: neighbour numbers in the chain band at the neighbour end, labelled with Role and Uke.

**Seats and status**

- UX-DR25: Setestatus: four rows with dot, Role, name or «KI-spiller» and status text («har bestilt», «venter, 3 min», «venter (deg)»), live, on Spill and Hjem.
- UX-DR26: Pausevalg: «Ta pause» with consequence lines and «Ta pause uten avtalt tid»; no date field for Students; pause lines per who paused; ending by ordering.
- UX-DR27: Sett inn KI-spiller: shown to the other Students on the absent Seat's row under the one eligibility rule; consequence line above the button; one press, no dialog; double-press message; the row before the insert time states the time.
- UX-DR28: Spillkort: Hjem card with a mini graph over a three-row table, Totalkostnad and «Gå til Uke n»; variants for waiting on others and Oppfølgingsspill; the mini graph is `aria-hidden` with a text alternative.
- UX-DR29: Stegene: six steps (Klassespill, Debrief, Quiz, Replay, Individuell test, Rapport) with the current one marked and locked steps stating what opens them.

**Game end and Debrief**

- UX-DR30: Spillet er ferdig: chain total first in `figure-hero`, then Kjedens regning per Role (Detaljist to Fabrikk, own row marked «(deg)»), Kjedens kostnad over tid with «Vis som tabell», then «Gå til Debrief».
- UX-DR31: Debrief sequence: five steps with the verbatim headings, the locked-reveal message, reflection questions and follow-up between steps 3 and 4, own moments paged within step 4 on the Student's own device only.
- UX-DR32: Etterspørselsbånd with its table (Uke, Kundene, Ordre inn, Din ordre) in step 2, where the exercise is named.
- UX-DR33: Ordrestolper: one row per Role with Fabrikk at the top, own Role in `ink`, the first order of 10 or more marked and joined by a diagonal, Forsterkning at the right, Rolle × Uke numbers underneath in `flow-*` steps.
- UX-DR34: Ukeskrubber: `role="slider"` with the listed keys, step buttons, a dashed Uke line across the bars, and a polite live-region reading of the chain after 300 ms.
- UX-DR35: Delt skjerm: shared charts only (chain, Netto lager per Role, cost per Role, chain total) with Lager and Restordre numbers printed beside each total; no Forklaringer or personal moments.
- UX-DR36: Kjedens regning in the Debrief adds the «Simulert, samme kunder» rows, the restordre share line and the AI-held share of chain cost; never «optimal» or «fasit».
- UX-DR37: Quizvalg: single choice with wrong and right states in text and border, followed by the explanation naming the column.
- UX-DR38: Interaktiv oppgave: one graph over one value table as one answer; drag or tap to place points; each point a slider with keyboard steps; the table alone answers the item; scoring reads table values only; «Fyll inn kolonnen» is the table without a graph; cells autosave.
- UX-DR39: Flagg: «Marker som feil» toggle with `aria-pressed`, the flagged state and «Angre».

**Faglærer**

- UX-DR40: Oversikt layout: headline counts, the class median graph over the Matrisevegg, the view toggle above the wall, and a right rail with «Venter ellers», «Klassens kostnad» and «Trakt»; one column below 1024 px.
- UX-DR41: Matrisevegg: one row per Class game and one column per Uke in matrix steps, grouped by status, with the cell number-or-minus rule, the always-visible legend, the near-Takeover row tint with «Melding», bottom rows for median and average, and keyboard focus that stays on the same game across updates.
- UX-DR42: «Vis som tabell»: all games with a number in every cell at 13 px, sortable, screen-reader readable; in «Vis i plenum» game-number order, no names, no sorting by cost, larger cells and a caption in words.
- UX-DR43: Veggfiltre: Rolle, Celler and Status as text-button toggles with `aria-pressed` and counts; the legend switches bins with the Celler filter.
- UX-DR44: Oppdater automatisk: a switch, on by default; when off, the change count and «Oppdater»; while focus is in the wall rows do not move; polite announcements at most once a minute.
- UX-DR45: Varselbånd: the game closest to Takeover with «Send Melding», «Pause spillet» and «Sett inn KI-spiller for …»; actions wrap under the text below 1024 px; a paused game leaves the band; Assistent sees a reduced set.
- UX-DR46: Meldingsskjema: its own page with the recipient preset (Student, Class game, Class session, or those who have not met the requirement), disabled send while empty, and the sent-count result.
- UX-DR47: Filopplasting and Lag Klasse: file box, «250 rader lest», «Bytt fil», preselected «E-postkolonne» with its reason, «Lim inn adresser i stedet», invalid rows with a reason and «Registrer manuelt», «Send 246 Invitasjoner», and «Status etter utsending» with «Send påminnelse til 10».
- UX-DR48: Klasseøkt screen: defaults notice, «Kjeden ved start» chain diagram, Valgknapper for AI mode and Debrief mode, the Obligatorisk switch, Datolinje with Labtimer, inline range errors and non-blocking warnings, read-only after the Start date, and «Lagre Klasseøkt».
- UX-DR49: Klasseøkt blocks: «Innsatsnivå» (only offered levels with their effect), «Spørsmål og vekter» (live sum that must be 100%, quantity-item warning), «Sensorveiledning» (Standard or Endret, unchecked notice), «KI-vurdering» switch, «Ventetid før KI tar over» (whole hours, 20 or more), and «Eksport» with its three downloads and notes.
- UX-DR50: Fordelingsforhåndsvisning: 60 columns by 4 Role rows, selecting a game shows its four names, «Kjør fordeling på nytt», «Bekreft fordeling» with «Ingen får beskjed før du bekrefter.», and «Vis som liste».
- UX-DR51: Kostnadsfordeling, Trakt and Datolinje: read-only charts with their listed text or table alternatives.
- UX-DR52: Spillstyring on Spillinnsikt: start, pause with an agreed time, «Marker som i rommet» (only in a Labtime), manual Takeover per Seat, fill all waited-for Seats; consequence above each action; one in-place form at a time; result lines replace forms; the two all-games pages from the Oversikt header.
- UX-DR53: Tilrettelegging on the Studentside: factors for more time, share of Weeks, no reason field, only ever extends; the Student's own lines on Hjem.
- UX-DR54: Fullføringsretting on the Studentside: status per step in text, the share lines, correction with a required reason, «Gi oppfølgingsspill», and the message link to those who have not met the requirement.
- UX-DR55: Spillinnsikt, Studentside, Klasserapport, Tverrklasse-statistikk and Lærers testspill surfaces, each chart with «Vis som tabell»; the test game is labelled as a test game.
- UX-DR56: Lærerhjem (Klassene dine, what is waiting, next deadline; empty state with «Ny Klasse» only) and «Faglærere og assistenter».

**Admin**

- UX-DR57: Admin-område: «Brukere og roller» with search, invite, grant, the blocked-revoke message and deactivate with its consequence; «KI-kostnad» with the limit-reached message; «Kontrolltest» with marked test students and the side-by-side comparison.

**System and states**

- UX-DR58: Tilkoblingslinje for offline, stale data and page errors; Skjelett loading in the real layout with «Laster …» after 1 s; no spinners.
- UX-DR59: All-surface states: offline, reconnected, page error, inline action error, permission denied (never revealing existence), session expired with input kept, not found.
- UX-DR60: Order submit states with their announcements and focus rules: submitting, confirmed, failed («Prøv å sende 24 igjen»), timed out with a server check, offline with a typed order that is never sent without a press.
- UX-DR61: Account surfaces and states: Landing, «Du er invitert», Logg inn, Glemt passord, Nytt passord, with the non-revealing error copy and the deactivated-user message.
- UX-DR62: Student game states: Hjem before allocation, waiting for others, «Velg spill og sete» and its states, Veiledet uke, paused, pause ended, «I rommet», own Seat taken over with «Ta tilbake setet», ended by playout, waiting for an AI player.
- UX-DR63: Rules briefing («Regler før første ordre») and Startoppgave screens with right, wrong and final-question states.
- UX-DR64: Replay and Replay-gjennomgang states (locked, in progress, finished, pending, code fallback, «Ikke like for like.») and «Alle spill side om side» with its locked state.
- UX-DR65: Individuell test states: own-work statement, «Lagret 21:14», autosave failure, review before submit listing unanswered items, submitted, auto-submitted, never opened; the larger-screen advice for long answers.
- UX-DR66: KI-vurdering states: not ready, ready with dropped-feedback notes, switched off; «Teller ikke. Ingen karakter.» on every view; the Veiledende bokstav control.
- UX-DR67: Mine data: one row per stored category with «Vis» and «Last ned Studentrapport».
- UX-DR68: Studentrapport PDF layout: headed «ØL-spillet», graph over table, decisions, cost and Forklaring, tagged, with a table under every chart.

**Cross-cutting rules**

- UX-DR69: KI-merke and AI disclosure: «KI-spiller» on every AI-held Seat from first view, Takeover copy, Play guard switch on the Setestatus row, the prefix «KI-generert, kan ta feil:» on all AI text.
- UX-DR70: Demodata and Simulert labels on every synthetic or simulated number.
- UX-DR71: Hidden information: no week counts or progress anywhere outside the Debrief, the axis stops at nå + 4, no recommended order, staff progress as share of games finished.
- UX-DR72: Cost picture: which costs appear in play, at game end, in the Debrief and for staff; sorting by cost is staff-only.
- UX-DR73: Chain direction: upstream on the left on every surface; Role lists with Fabrikk at the top; per-Role tables Detaljist to Fabrikk.
- UX-DR74: Voice and term mapping: the PRD-term to UI-string table and the do and don't microcopy rules as the source for `nb.ts`; «enheter», never «øl»; no exclamation marks or praise.
- UX-DR75: Responsive rules: phone design target 360 px with a 320 px reflow floor; laptop layout from 1024 px; tablets take phone layout in portrait and laptop layout in landscape; staff and Admin surfaces reflow at 320 px and 200% text; only the listed two-dimensional components scroll inside their own region.
- UX-DR76: Accessibility floor: the chart-alternatives table, the live-announcement list, reduced motion, tap targets of at least 44 px, full keyboard operation with no task needing a drag.
- UX-DR77: Navigation: Hjem as the Student hub with no global nav bar on phone; Lærerhjem → Klasse → Klasseøkt / Oversikt for staff.
- UX-DR78: Banned interactions: recommended orders, player chat, Student-facing ranking or prizes, progress toward the end, confirmation dialogs after a consequence-stating button, celebration animation, pull-to-refresh as the only update path.

### FR Coverage Map

Each FR has one home epic. Where an earlier epic builds a part another epic needs, it is named in brackets.

- FR-1: Epic 3 - Admin invites with a role
- FR-2: Epic 3 - Admin grants or revokes a role
- FR-3: Epic 3 - Admin manages Users, Institutions and the audit log
- FR-4: Epic 3 - Account creation, login and password reset
- FR-5: Epic 3 - Role-scoped access
- FR-6: Epic 4 - Create and archive a Class
- FR-7: Epic 4 - Upload the Roster
- FR-8: Epic 4 - Send Invitations
- FR-9: Epic 4 - Registration status and manual override
- FR-10: Epic 4 - Co-lecturers and Assistant lecturers
- FR-11: Epic 5 - Class session with Classic defaults (settings model in Epic 1)
- FR-12: Epic 5 - Change Game settings (settings model and validation in Epic 1)
- FR-13: Epic 5 - Choose a Demand pattern (demand series in Epic 1)
- FR-14: Epic 6 - Hidden end and demand
- FR-15: Epic 5 - Choose AI mode
- FR-16: Epic 5 - Choose Debrief mode
- FR-17: Epic 13 - Obligatory class session and Completion (the mark in Epic 5, step events from Epic 6, per-Student time adjustment in Epic 8)
- FR-18: Epic 5 - Set dates and lock points (per-Student test extension in Epic 11)
- FR-19: Epic 5 - Schedule Lab hours
- FR-20: Epic 5 - Automatic random allocation
- FR-21: Epic 5 - Student choice (cut list)
- FR-22: Epic 5 - Class games open at the Start date (Student start in Epic 6)
- FR-23: Epic 6 - Weekly state shown to a Seat
- FR-24: Epic 6 - Place an Order
- FR-25: Epic 6 - Who the game waits for
- FR-26: Epic 6 - Week advance (engine sequence in Epic 1)
- FR-27: Epic 8 - Notification when it is your turn
- FR-28: Epic 6 - Game end (engine end in Epic 1)
- FR-29: Epic 1 - Correct bookkeeping
- FR-30: Epic 1 - AI players fill Seats
- FR-31: Epic 2 - Same numbers as a human
- FR-32: Epic 2 - Validated Orders and fallback
- FR-33: Epic 2 - Documented AI behaviour (Rule-based rule in Epic 1)
- FR-34: Epic 6 - Disclosure of AI players (AI text marking in Epic 9)
- FR-35: Epic 8 - Activity tracking
- FR-36: Epic 8 - Automatic Takeover
- FR-37: Epic 8 - Manual Takeover and Reclaim
- FR-38: Epic 8 - Play deadline playout
- FR-39: Epic 7 - Lecturer overview
- FR-40: Epic 7 - Send Messages
- FR-41: Epic 9 - Explanation in the Debrief
- FR-42: Epic 9 - Debrief availability
- FR-43: Epic 9 - Group debrief
- FR-44: Epic 9 - Debrief content
- FR-45: Epic 9 - Guided questions and follow-up
- FR-46: Epic 9 - Debrief quiz
- FR-47: Epic 9 - Debrief summary
- FR-48: Epic 10 - Start the Replay
- FR-49: Epic 10 - Replay scenario
- FR-50: Epic 10 - Replay feedback
- FR-51: Epic 11 - Test availability
- FR-52: Epic 11 - Question set and Item weights
- FR-53: Epic 11 - Adapted items
- FR-54: Epic 12 - AI assessment
- FR-55: Epic 12 - Seeing the AI assessment
- FR-56: Epic 12 - Indicative letter
- FR-57: Epic 13 - Student downloads the report
- FR-58: Epic 13 - Report content
- FR-59: Epic 13 - Lecturer downloads reports
- FR-60: Epic 13 - Completion export
- FR-61: Epic 12 - AI assessment can be switched off
- FR-62: Epic 7 - Game insight
- FR-63: Epic 13 - Student page for lecturers
- FR-64: Epic 14 - Class report
- FR-65: Epic 14 - Cross-class statistics (cross-Institution view on the cut list)
- FR-66: Epic 5 - New Class session from an earlier one (cut list)
- FR-67: Epic 1 - Decision log (LLM call metadata in Epic 2)
- FR-68: Epic 2 - Model pinned per Class session
- FR-69: Epic 2 - AI spending controls (Admin cost view in Epic 15)
- FR-70: Epic 10 - Plausibility rating
- FR-71: Epic 15 - Pseudonymised export
- FR-72: Epic 3 - Norwegian interface (copy home set up here, applied by every epic)
- FR-73: Epic 6 - Mobile-first, classroom laptop equal (applied by every Student-facing epic)
- FR-74: Epic 9 - Group debrief on one screen
- FR-75: Epic 15 - Student data access
- FR-76: Epic 15 - Deletion on request
- FR-77: Epic 15 - Retention
- FR-78: Epic 2 - Effort setting (Lecturer's choice on the Class session screen in Epic 5)
- FR-79: Epic 2 - Play guard
- FR-80: Epic 11 - Interactive items
- FR-81: Epic 11 - Scoring guide
- FR-82: Epic 12 - Control test
- FR-83: Epic 5 - Information visibility (shown on the play screen in Epic 6; cut list)
- FR-84: Epic 6 - Rules before the first Order
- FR-85: Epic 6 - Starting task
- FR-86: Epic 14 - All games side by side
- FR-87: Epic 6 - Lecturer test game (cut list)
- FR-88: Epic 14 - Game data export (cut list)
- FR-89: Epic 8 - Pause

NFR homes: NFR-1 and NFR-5 in Epic 6; NFR-2 in Epic 2; NFR-3 and NFR-8 in Epic 15; NFR-4 in Epics 8 and 15; NFR-6 starts in Epic 3 and applies to every epic with a screen; NFR-7 in Epic 3; NFR-9 in Epics 1 and 9; NFR-10 in Epic 4.

## Epic List

Approved by the founder on 2026-11-12. Each epic is a vertical slice with its own backend and frontend module. Shared code goes in the shared folders named under Additional Requirements, added by the first story that needs it. Epics build only on earlier epics.

### Epic 1: Game engine proven in simulation
The founder can run complete all-AI Games headless with Rule-based players and read a correct Decision log. Holds the repo scaffold as its first story.
**FRs covered:** FR-29, FR-30, FR-67 (and the engine side of FR-11, FR-12, FR-13, FR-26, FR-28)
**Slice:** `engine`, `modules/games`, `sim`

### Epic 2: LLM players that are safe to teach with
The founder can measure cost, latency, fallback and Play guard switches per model and Effort level on simulated Games, and the Admin can pin a model with a cost limit.
**FRs covered:** FR-31, FR-32, FR-33, FR-68, FR-69, FR-78, FR-79
**Slice:** `ai`, `modules/players`

### Epic 3: Accounts and the Admin area
The Admin can invite a Lecturer, who creates an account, logs in and lands on an empty home screen; every User is held to their role. Holds the first production deploy.
**FRs covered:** FR-1, FR-2, FR-3, FR-4, FR-5, FR-72
**Slice:** `modules/identity`, `modules/admin`

### Epic 4: Classes, Roster and Invitations
A Lecturer can create a Class, upload the Roster, send Invitations and get Students registered, with co-lecturers and Assistant lecturers.
**FRs covered:** FR-6, FR-7, FR-8, FR-9, FR-10
**Slice:** `modules/classes`

### Epic 5: Class session setup and allocation
A Lecturer can set up a Class session with defaults, settings, dates and Lab hours, and allocate Students to Class games that open at the Start date.
**FRs covered:** FR-11, FR-12, FR-13, FR-15, FR-16, FR-18, FR-19, FR-20, FR-21, FR-22, FR-66, FR-83
**Slice:** `modules/sessions`

### Epic 6: Students play the Class game
A group can play a full Class game on their phones, from the rules briefing and Starting task to the chain's Total cost.
**FRs covered:** FR-14, FR-23, FR-24, FR-25, FR-26, FR-28, FR-34, FR-73, FR-84, FR-85, FR-87
**Slice:** `modules/games` (Student web), `modules/progress`

### Epic 7: Lecturer overview, Game insight and Messages
A Lecturer or Assistant lecturer can follow all Class games live, open any Game week by week and send Messages.
**FRs covered:** FR-39, FR-40, FR-62
**Slice:** `modules/games` (staff web), `modules/messaging`

### Epic 8: Every game finishes: Pause, Takeover and deadlines
A missing Student never blocks a group, the Lecturer can steer games, and every Class game ends by the Play deadline.
**FRs covered:** FR-27, FR-35, FR-36, FR-37, FR-38, FR-89
**Slice:** `modules/games` (turns), `modules/ops`

### Epic 9: Debrief and Debrief quiz
A group can write Explanations, see the reveal and their own moments, and pass the Debrief quiz, alone or on a shared screen.
**FRs covered:** FR-41, FR-42, FR-43, FR-44, FR-45, FR-46, FR-47, FR-74
**Slice:** `modules/debrief`, `modules/content`

### Epic 10: Replay
A Student can play again alone under harder conditions and get a short walkthrough.
**FRs covered:** FR-48, FR-49, FR-50, FR-70
**Slice:** `modules/replay`

### Epic 11: Individual test
A Student can take the Individual test over several evenings, and a Lecturer can review questions, Item weights and the Scoring guide.
**FRs covered:** FR-51, FR-52, FR-53, FR-80, FR-81
**Slice:** `modules/tests`

### Epic 12: AI assessment and Control test
A Student can read AI feedback that counts toward nothing, and the Admin can check it against human scoring.
**FRs covered:** FR-54, FR-55, FR-56, FR-61, FR-82
**Slice:** `modules/assessment`

### Epic 13: Completion and Student reports
A Lecturer can see who met the requirement and correct it, and Students and Lecturers can download PDF Student reports and the Completion export.
**FRs covered:** FR-17, FR-57, FR-58, FR-59, FR-60, FR-63
**Slice:** `modules/reports`, `modules/progress`

### Epic 14: Class report and statistics
A Lecturer can read the Class report, show all Class games in a plenary, compare Class sessions and export Game data.
**FRs covered:** FR-64, FR-65, FR-86, FR-88
**Slice:** `modules/reports` (class)

### Epic 15: Data rights and pilot readiness
A Student can see their data; the Admin can delete, export pseudonymised data and watch AI cost and errors; the platform passes the load test.
**FRs covered:** FR-71, FR-75, FR-76, FR-77 (and NFR-3, NFR-8)
**Slice:** `modules/ops`, `modules/identity`

## Epic 1: Game engine proven in simulation

When this epic is done, the founder can run complete all-AI Games headless with `python -m app.sim`, with Rule-based players and scripted occupants, and read a correct Decision log and a finished-game check for every Game. There is no login and no screen: the user is the founder at a terminal. The epic owns `api/app/engine/`, `api/app/modules/games/` (commands core, Seats, occupancy, turns, Decision log) and `api/app/sim.py`, and its first story holds the repo scaffold that every later epic builds on.

### Story 1.1: Scaffold the repo so it starts locally with zero keys

As a founder,
I want the repo scaffolded from the architecture's Structural Seed, starting with one command and no keys,
So that every later story has one agreed place to put its code and a CI run that guards it.

**Acceptance Criteria:**

**Given** a fresh clone with no `.env` file
**When** I run `docker compose up`
**Then** `postgres:17`, `api`, `web` and `proxy` start, and `GET http://localhost:8080/api/health` through the proxy answers 200 only after the api has reached the database (AD-17, AD-11)
**And** `/` through the proxy serves an empty Next.js 16 page, and `/print/*` answers 404 at the proxy
**And** the Caddyfile sends `/api/*` to `api` with `flush_interval -1` and everything else to `web`; no auth rule is added here (those come in Epic 3).

**Given** the Structural Seed in the spine
**When** I list the repo
**Then** it holds `api/` as one uv project on Python 3.14 with `app/engine/`, `app/analysis/`, `app/ai/`, `app/platform/`, `app/modules/`, `app/main.py`, `app/worker.py`, `app/sim.py`, `migrations/` and `tests/`; `web/` with Next.js App Router, standalone output, TypeScript, Tailwind, shadcn initialised (`components.json`, no component added yet) and the `src/app`, `src/modules`, `src/components`, `src/lib`, `src/copy` folders; `proxy/Caddyfile` and `proxy/Dockerfile`; `docker-compose.yml`; and `.env.example` with variable names only
**And** every version is pinned to the spine's Stack table, with `uv.lock` and `package-lock.json` committed
**And** `app/worker.py` and the worker services are left as a stub entry point: the job platform and the `worker-ai` and `worker-batch` compose services are added in Epic 2, and `railway/` in Epic 3.

**Given** `platform/db` and `platform/config` are added to `api/app/platform/` for reuse
**When** the api starts
**Then** settings load through one pydantic-settings class, including `APP_ENV` and the seven `FEATURE_*` flags of the cut list (default `true` locally), and the database is reached through one async SQLAlchemy engine on psycopg 3 with `max_overflow=0`
**And** with `APP_ENV=production` and `DATABASE_URL` missing or left at its default the process refuses to start with a message naming the variable (AD-17); later epics add their own required secrets to the same guard.

**Given** Alembic owns every schema change (AD-24)
**When** the api container starts locally or I run `alembic upgrade head`
**Then** an empty baseline revision applies cleanly to an empty Postgres 17 database, and no table is created by any other means.

**Given** structlog is configured in `platform`
**When** a request is handled
**Then** one JSON log line is written with a `request_id`, and a test asserts that the logger setup has no field for names, emails or free text.

**Given** a push or pull request on GitHub
**When** CI runs
**Then** the `api` job runs `uv sync --locked`, ruff and pytest against a Postgres 17 service, and the `web` job runs `npm ci`, typecheck and build with the `openapi-typescript` TypeScript 6.0.3 override in `package.json`
**And** the later CI steps (contract check, copy check, Playwright with axe, veraPDF, simulation smoke run) are not added here; each is added by the story that first needs it.

**Covers:** AD-1 (layer folders), AD-11 (proxy routing), AD-17, AD-24

### Story 1.2: Run the Classic chain Week by Week and match the reference trace

As a founder,
I want the pure engine to play Weeks under the Classic Game settings and print the result,
So that I can see with my own eyes that the game arithmetic matches the reference before anything is stored.

**Acceptance Criteria:**

**Given** `engine.GameSettings` is added to `api/app/engine/` as one Pydantic model with a `schema_version`
**When** I build it with no arguments
**Then** it holds the Classic defaults: four Roles, starting inventory 12 per Seat, 4 units in every supply-line slot, order delay 2, shipping delay 2, Factory production delay 2, demand 4 stepping to 8 in Week 5, holding cost 0.50 and backorder cost 1.00 per unit per Week, 36 Weeks, Guided Weeks 1 to 4, and a maximum Order of 999, a stated placeholder that does not bind in normal play (FR-11, FR-12)
**And** units are integers and cost rates are `Decimal`, written to JSON as decimal strings such as `"0.50"`.

**Given** the Classic settings
**When** `engine.initial_state(settings)` opens Week 1
**Then** the slot layout matches addendum §B: the Retailer's incoming order comes from the customer with no delay, every other Seat has 2 order slots, every Seat has 2 goods slots (shipping, or production for the Factory), and the chain holds 48 units in inventory, 24 in shipping slots and 8 in production slots, 80 in all
**And** an Order placed in Week t reaches the upstream Seat in Week t+2, a shipment sent in Week t arrives in Week t+2, and a Factory Order reaches the Factory's inventory after order delay plus production delay (4 Weeks).

**Given** an open Week and one Order per Seat
**When** `engine.advance(settings, state, orders)` runs
**Then** it follows the FR-26 sequence exactly: costs are charged on the end-of-Week balances, all slots advance, and the next Week opens by receiving the incoming delivery, setting amount to ship = incoming order + backlog, shipping the smaller of inventory and that amount, and leaving the rest as backlog (FR-26, AD-1)
**And** the function does no I/O, reads no clock and uses no randomness, and returns a new state without changing its input.

**Given** the last Week in Game settings
**When** `advance` runs on it
**Then** the Week runs in full, the returned state is marked finished, no further Week opens, and units still in slots carry no cost (FR-28).

**Given** constant demand 4 and every Order 4 for 36 Weeks
**When** the golden-trace test runs
**Then** every Seat keeps inventory 12 with no backlog and is charged 6.00 every Week (addendum §B reference trace)
**And** this trace, and a second hand-checked trace with the Classic step to 8 in Week 5, are stored as golden files under `api/tests/engine/golden/` and run in CI
**And** the step trace is not produced by the engine it tests: its first 10 Weeks are worked out by hand from the FR-26 sequence in a table committed next to the golden file, and the founder checks that table before the golden file is accepted.

**Given** I run `python -m app.sim trace --settings classic --orders constant:4`
**When** it finishes
**Then** it prints one row per Week and Role with incoming order, incoming delivery, shipped, inventory, backlog, Order and cost, computed by the engine alone with no database
**And** the engine and its tests reach full branch coverage, reported in CI.

**Covers:** FR-11 (engine side), FR-26 (engine side), FR-28 (engine side), AD-1, NFR-9

### Story 1.3: Check changed Game settings against ranges and warnings

As a founder,
I want every Game setting validated by pure functions that reject out-of-range values and warn on risky combinations,
So that simulations and, later, the Lecturer's setup screen use one definition of what is allowed.

**Acceptance Criteria:**

**Given** `GameSettings` accepts starting inventory or backlog per Seat, supply-line contents, order delay, shipping delay, Factory production delay, both cost rates, number of Weeks, Guided Weeks and maximum Order (FR-12)
**When** `engine.settings.validate(settings)` runs on a value outside its range
**Then** it returns one error per field with a stable code, the field path and the allowed range, so a caller can show the range (FR-12)
**And** delays are accepted only from 1 to 3 Weeks; the other ranges live in one table, `engine.settings.RANGES`, with placeholder bounds marked as such, to be confirmed with the Class session screen in Epic 5.

**Given** Guided Weeks that are not fewer than the Week of the first demand change, or that leave no Weeks to play
**When** `validate` runs
**Then** the settings are rejected with a code naming the rule.

**Given** valid settings where supply-line contents differ from starting demand, backorder cost is not above holding cost, the maximum Order is low enough to bind in normal play, or the Weeks are too few for a demand change to pass through the chain at the chosen delays
**When** `engine.settings.warnings(settings)` runs
**Then** it returns one non-blocking warning per case with a stable code and the numbers behind it, and `validate` still passes (FR-12)
**And** the too-few-Weeks rule is computed from the delays, and a test shows it reproduces addendum §B's arithmetic (first Factory-made units at the Retailer around Week 21 at 2/2/2 and Week 29 at 3/3/3).

**Given** settings with delays 1/1/1 and 3/3/3 and a non-default starting backlog
**When** `initial_state` and `advance` run
**Then** the slot counts follow the delays, a Seat that starts with backlog starts with no inventory, and a golden trace for each case passes in CI.

**Given** a settings file
**When** I run `python -m app.sim settings check <file>`
**Then** it prints the errors with their ranges and the warnings, and exits non-zero only on errors.

**Covers:** FR-12 (settings model and validation), AD-1

### Story 1.4: Generate the demand series from a Demand pattern and a seed

As a founder,
I want the customer demand series produced by a pure function from the Demand pattern and a seed,
So that the same settings always give the same series and every Game of a batch can share it.

**Acceptance Criteria:**

**Given** a Demand pattern of kind fixed series, step (start level, new level, Week of change), random (mean, spread) or step plus noise
**When** `engine.demand.series(pattern, weeks, seed)` runs
**Then** it returns one whole number per Week for the full number of Weeks (FR-13)
**And** it is added to `api/app/engine/` for reuse and takes randomness only from the seed passed in (AD-1).

**Given** a random or step-plus-noise pattern
**When** the series is drawn
**Then** each Week's value comes from a discrete uniform distribution over the whole numbers from mean minus spread to mean plus spread, never below 0, around the stepped mean where a step is set (FR-13)
**And** the same pattern and seed give the same series on every run and platform, proven by a golden test with stored series.

**Given** a fixed series shorter or longer than the number of Weeks, a spread below 0, or a step Week outside the Game
**When** `validate` runs
**Then** the pattern is rejected with a stable code and the allowed range.

**Given** no seed is supplied
**When** a caller asks for one through `engine.demand.new_seed(entropy)`
**Then** the caller passes the entropy in, the seed is returned as a value that can be shown, stored and entered again, and the engine itself never reads the clock or the system random source (FR-13, AD-1).

**Given** I run `python -m app.sim demand --pattern step+noise --seed 42`
**When** it finishes
**Then** it prints the materialised series and its seed, and running it again prints the same series.

**Covers:** FR-13 (demand series), AD-1

### Story 1.5: Prove the bookkeeping is correct by construction

As a founder,
I want a pure check that confirms conservation of units and cost totals over any sequence of Weeks,
So that a bookkeeping error is caught by a test long before a Student sees it.

**Acceptance Criteria:**

**Given** a list of Week states produced by the engine
**When** `engine.check.conservation(settings, states, orders)` runs
**Then** it confirms for every Week that units on hand and in transit equal the starting units plus units entered production minus units delivered to customers (80 at the start under Classic) (FR-29)
**And** it confirms that each Seat's cost for a Week equals holding rate times inventory plus backorder rate times backlog on the end-of-Week balance, and that the Total cost per Seat and for the chain equals the sum of the Week costs.

**Given** a Seat without capacity
**When** the check runs
**Then** it confirms that inventory and backlog are never both positive in any Week (FR-29).

**Given** a state list where one unit, one cost or one balance has been altered
**When** the check runs
**Then** it returns a violation naming the rule, the Week and the Role, and never raises on bad data.

**Given** a finished Game
**When** the check runs
**Then** units still in slots at the end are counted in the conservation sum and carry no cost (FR-28).

**Given** property-based tests over random valid settings, demand series and Orders from 0 to the maximum
**When** CI runs them
**Then** every generated run passes the check, with a fixed seed so a failure can be reproduced
**And** the check is added to `api/app/engine/` for reuse by the finished-game check (Story 1.10).

**Covers:** FR-29 (pure check), FR-28 (engine side), NFR-9, AD-1

### Story 1.6: Order with the Rule-based player

As a founder,
I want a documented anchoring-and-adjustment rule that returns an Order for any Seat from what that Seat can see,
So that every empty Seat can be played and every Seat gets a Rule-based reference Order.

**Acceptance Criteria:**

**Given** the Rule-based player is added to `api/app/engine/` as a pure function
**When** `engine.rule_based.order(settings, seat_view, params)` runs
**Then** it returns a whole-number Order from 0 to the maximum Order, computed from the Seat's own inventory, backlog, incoming orders, Supply line and Order history only (FR-33, AD-1)
**And** `seat_view` is an `engine.SeatView`, one numbers-only Pydantic model added to `api/app/engine/` in this story (the Seat's Role, inventory, backlog, incoming orders, Supply line, Order history and neighbour numbers); every engine function that looks at one Seat takes this type, so `engine` imports nothing from `modules`
**And** it uses the Game settings in force (delays, costs, maximum Order) and no neighbour numbers from Information visibility, proven by a test that changes the neighbour numbers and gets the same Order.

**Given** the fitted parameters have not been retrieved from the primary source (issues #8 and #17)
**When** the rule needs its parameters
**Then** they come from a named, versioned parameter set held as configuration, and the only set shipped is labelled `placeholder-unverified` with its source field saying so
**And** no value from a calculator site is used, and replacing the set needs no code change.

**Given** a Guided Week
**When** a caller asks for the Order
**Then** `engine.guided_order(settings)` returns the starting demand for every Seat, and the Rule-based rule is not consulted (FR-11).

**Given** the Classic settings in balance
**When** all four Seats order by the rule under constant demand 4
**Then** the chain stays in balance (every Order 4), and a golden trace with the Classic step shows the Orders the rule gives with the placeholder set, stored so a later parameter change shows as a visible diff.

**Given** a short Markdown file next to the function
**When** I read it
**Then** it states the rule as a formula, names each parameter, and names the primary source the final values must come from (FR-33).

**Given** I run `python -m app.sim trace --settings classic --orders rule_based`
**When** it finishes
**Then** it prints the week table for a chain played by four Rule-based players and a warning line that the placeholder parameter set was used.

**Covers:** FR-33 (Rule-based rule), FR-11 (Guided Week Orders), AD-1

### Story 1.7: Create a simulation Game with an AI player in every Seat

As a founder,
I want to create a stored Game of four Seats, each held by a Rule-based or scripted occupant, with its settings frozen at creation,
So that simulation Games use the same tables and commands that real Games will.

**Acceptance Criteria:**

**Given** the `games`, `seats` and `seat_occupancy` tables are created by this story's Alembic revision, owned by `modules/games`
**When** `games.commands.create(purpose="simulation", settings, demand_pattern, seed)` runs
**Then** one Game is stored with `lifecycle = not_started`, `version = 1`, UUIDv7 ids, and four Seats, one per Role
**And** the Game's snapshot holds the `GameSettings` as JSONB with `schema_version`, the materialised demand series with its seed, the engine `rules_version`, and a `SessionRuntime` with the AI mode and the Rule-based parameter set id (AD-4); later epics add their own fields to `SessionRuntime`.

**Given** settings that fail `engine.settings.validate`
**When** `create` is called
**Then** nothing is stored and the error codes from the engine are returned.

**Given** a created Game
**When** `games.commands.assign_seat(game, role, occupant_kind, policy_id)` runs with `rule_based` or `scripted`
**Then** an occupancy row `(seat_id, from_week = 1, occupant_kind, policy_id, reason = initial)` is appended, and no occupancy row is ever updated or deleted (AD-5)
**And** `create` fills no Seat: a Seat stays free until `assign_seat` gives it an occupant, a second `assign_seat` for a Seat that has one answers a stable conflict code, and filling the Seats that are still free belongs to the command that starts the Game, not to `create` (FR-30)
**And** `scripted` is accepted only when `purpose = simulation`, and needs a `policy_id` from the closed registry `engine.scripted.REGISTRY`, which this story starts with one pure policy (a constant Order) that takes only an `engine.SeatView`; the id is stored on the occupancy row, so whoever places the Seat's Orders reads the script from the database (AD-22).

**Given** `games.policy(purpose)` is added as the one behaviour table
**When** it is asked about `simulation`
**Then** it answers that inactivity Takeover, Pause, the Play deadline playout and the Lecturer overview do not apply and that Guided Weeks follow the Game settings, and no command branches on purpose itself (AD-13).

**Given** `platform/events.emit(topic, id)` and `platform/events/registry.py` are added to `api/app/platform/` for reuse
**When** `create` or `assign_seat` commits
**Then** each ran as one transaction that locked the Game row with `SELECT … FOR UPDATE`, incremented `version`, and ran `NOTIFY` for `game:<id>` with `{topic, id, version}` only (AD-2, AD-8)
**And** a registry test asserts that every `games.commands` command has an entry and emits exactly its listed topics; a simulation Game emits no `session:<id>`.

**Given** I run `python -m app.sim create --settings classic --seats rule_based`
**When** it finishes
**Then** it prints the Game id, its four Seats with occupant kind, and the seed, read back from the database.

**Covers:** FR-30, AD-2, AD-4, AD-5, AD-8, AD-13, AD-22

### Story 1.8: Start the Game and read what each Seat sees

As a founder,
I want a started Game to open Week 1 with one open turn per Seat and a Seat state I can print,
So that I can check the exact numbers a player in that Seat will be given.

**Acceptance Criteria:**

**Given** the `game_weeks` and `seat_turns` tables are created by this story's revision
**When** `games.commands.start(game)` runs on a `not_started` Game
**Then** `lifecycle` becomes `running`, the engine's Week 1 state is stored in `game_weeks`, and one `seat_turns` row per Seat is written with `opened_at` (AD-2, AD-20)
**And** before Week 1 opens, `start` gives every Seat that is still free a Rule-based player, as an occupancy row with `from_week = 1` and `reason = initial`, so a started Game never has an empty Seat (FR-30, AD-5)
**And** calling `start` again answers a stable conflict code and changes nothing.

**Given** a Week opens
**When** its `seat_turns` rows are written
**Then** the Rule-based reference Order for every Seat is computed once, in that transaction, from that Seat's state, and stored on the row (AD-5, FR-67)
**And** it is never recomputed later.

**Given** `games.schemas.SeatState` is added as one Pydantic model with a `schema_version`, extending `engine.SeatView` from Story 1.6 so that engine functions accept it as it is
**When** `games.views.seat_state(game, seat, week)` runs
**Then** it returns numbers only: Week, Role, inventory, backlog, incoming order, incoming delivery, units shipped, Supply line slots with arrival Weeks, Posisjon (inventory minus backlog plus the Supply line), running Total cost with this Week's cost lines, the Seat's own history of Orders and Week values, neighbour numbers with their Role and Week (empty while Information visibility is off), the Order limits and the preview coefficients (AD-3, FR-23)
**And** it holds no names, no number of Weeks, no future demand and no other Seat's state, proven by a test that serialises it for every Role and Week of a Classic Game and searches for the series, the Week count and the other Seats' values.

**Given** the four Roles
**When** their Seat states are built
**Then** only the Retailer's incoming order is customer demand, and only for the Weeks already opened (FR-14, AD-3).

**Given** I run `python -m app.sim show <game_id> --seat retailer`
**When** it finishes
**Then** it prints that Seat's `SeatState` as JSON and the open turn's `opened_at` and reference Order.

**Covers:** FR-23 (Seat state model), FR-14 (information boundary), FR-30 (no empty Seat in a started Game), FR-67 (reference Order), AD-2, AD-3, AD-5, AD-20

### Story 1.9: Place Orders, write the Decision log and advance the Week

As a founder,
I want every Order to go through one command that records it with the state the Seat saw and advances the Week when the last Order is in,
So that a Game can be played to its end and every decision can be read back afterwards.

**Acceptance Criteria:**

**Given** the `seat_weeks` table is created by this story's revision
**When** `games.commands.place_order(game, seat, week, order, decided_by)` commits
**Then** exactly one `seat_week` row is written with the Week, the Seat, `state_seen` (the `SeatState`), the Order, `decided_by ∈ {student, llm, rule_based, scripted, guided}`, `fallback = none`, the `occupant_kind` and `reason` of the occupancy row in force, `opened_at`, `ordered_at` and the Rule-based reference Order copied from the `seat_turns` row (FR-67, AD-15)
**And** the row is never updated, enforced by the absence of any update path and a test that tries one.

**Given** an Order that is not a whole number from 0 to the maximum Order, an Order for a Week that is not the open Week, or a second Order for the same Seat and Week
**When** `place_order` is called
**Then** it answers a stable error code (`422 order_invalid` for the value, `409 week_not_open` for the Week, `409 order_exists` for the second Order), stores nothing, and the unique key `(game_id, week, seat_id)` backs this up (AD-2, FR-24).

**Given** `games.rules.week_complete(game)` is the one predicate for the advance
**When** the Order that makes it true is placed
**Then** that same transaction calls `engine.advance`, stores the next Week's state in `game_weeks`, writes the next `seat_turns` rows with their reference Orders, increments `version` once and emits `game:<id>` (AD-2, FR-26)
**And** a concurrency test that places the last two Orders at the same moment sees exactly one advance, with the Week state stored before any reader can see it.

**Given** a Guided Week
**When** its Orders are placed
**Then** each is the fixed Order from `engine.guided_order` with `decided_by = guided`, for every occupant kind (FR-11, AD-15).

**Given** the Order that completes the last Week
**When** `place_order` commits
**Then** it calls `games.commands.finish` in the same transaction, `lifecycle` becomes `finished`, no further turn opens, and a later `place_order` answers a stable conflict code (FR-28).

**Given** a finished Classic Game played by four Rule-based players
**When** I run `python -m app.sim log <game_id>`
**Then** it prints the Decision log, one row per Week and Seat, and the costs in it equal those of the engine-only trace from Story 1.6 for the same settings and seed.

**Covers:** FR-67 (Orders, state seen, who placed it, Rule-based reference), FR-26 (stored before shown, engine sequence), FR-28 (engine end), AD-2, AD-15, AD-20, NFR-4 (no state lost)

### Story 1.10: Verify every finished Game by replaying it

As a founder,
I want every finished Game replayed by the engine and checked for conservation, with any violation logged as an error,
So that I can trust the stored numbers and keep trusting them after the rules change.

**Acceptance Criteria:**

**Given** a Game has just finished
**When** `games.service.verify_finished(game_id)` runs
**Then** it replays the engine at the Game's stored `rules_version` over the stored settings, demand series and Orders and requires the result to equal every stored Week state (AD-4, FR-29)
**And** it runs `engine.check.conservation` over the same Game, and writes one row to `game_checks` (created by this story) with the result, the `rules_version` and the time; the row is written once and never updated.

**Given** a stored Week state, Order or cost that was altered after the fact
**When** the check runs
**Then** it records the violation with rule, Week and Role, and logs one structlog line at error level with ids only (FR-29, NFR-9)
**And** it never changes the Game.

**Given** the check is idempotent and takes only a Game id
**When** it is called twice for the same Game
**Then** the second call returns the stored result, so the simulation runner calls it here and a job can call it in a later epic (AD-9).

**Given** the deferred decision on how older `rules_version`s stay runnable
**When** this story is done
**Then** the decision is made and recorded in `api/app/engine/RULES_VERSIONS.md`: each rules version is its own package `engine/rules/v<N>/`, `engine.advance` selects it from the `rules_version` passed in, a change that alters engine output is made as a new version and never as an edit to a version any stored non-simulation Game references, and a running Class session keeps the version frozen in its snapshot
**And** CI runs the golden traces of every version, and a test fails when a `rules_version` stored on any Game in the test database has no package.

**Given** `rules_version = 1` is the only version so far
**When** a test adds a throwaway `v2` with one changed rule
**Then** a Game finished under `v1` still verifies, and the same Orders replayed at `v2` are reported as differing, which shows the selection works.

**Given** I run `python -m app.sim check --all`
**When** it finishes
**Then** it prints the number of finished Games checked and lists any violations, and exits non-zero if there is one.

**Covers:** FR-29, NFR-9, AD-4, AD-1, AD-9 (idempotent, id-only)

### Story 1.11: Run batches of all-AI Games with scripted occupants

As a founder,
I want one command that plays a batch of complete Games headless through the production commands and summarises them,
So that I have the prototype's baseline and a smoke test before any LLM is involved.

**Acceptance Criteria:**

**Given** a batch file naming settings, Demand pattern, seed, number of Games and the occupant per Role
**When** I run `python -m app.sim run <batch>`
**Then** each Game is created, started, played and finished only through `games.commands` with `purpose = simulation`, with no web app and no direct write to a game table (AD-22, AD-2)
**And** for each open turn the runner places the Guided Order in a Guided Week, the stored Rule-based reference Order for a `rule_based` occupant and, for a `scripted` occupant, the Order of the policy whose id is on the occupancy row, and calls `verify_finished` when the Game ends.

**Given** `scripted` occupants are fixed no-learning policies
**When** I choose one per Role
**Then** the closed registry from Story 1.7 in `api/app/engine/` holds at least two pure policies (the constant Order and, added here, an order-what-came-in policy), each takes only an `engine.SeatView`, which a `SeatState` is, and each Order is logged with `decided_by = scripted` (AD-5, AD-15, AD-22).

**Given** a batch has finished
**When** the runner prints its summary
**Then** it shows per Game and for the batch: Total cost per Role and for the chain, the number of Weeks played, the count of Orders per `decided_by`, and the finished-game check result
**And** every number is read from the Decision log, `game_weeks` and `game_checks`, never from the runner's memory (AD-22).

**Given** the same batch file and seed with only Rule-based and scripted occupants
**When** I run it twice
**Then** both runs give identical Orders and costs in every Week.

**Given** a batch
**When** I add `--export <dir>`
**Then** the Decision log of its Games is written as CSV with one row per Week and Seat, holding ids, Roles and numbers only.

**Given** CI
**When** the simulation smoke step runs
**Then** `python -m app.sim run` plays a few Classic Games to the end on Rule-based and scripted occupants against the CI database and fails the build on any check violation (SETUP-GUIDE §6 step 7).

**Covers:** FR-30 (all-AI Games), FR-67, AD-22, AD-2, AD-5, AD-15, NFR-9

### Story 1.12: Cap what a Seat can ship per Week (cut list, `FEATURE_CAPACITY`)

As a founder,
I want an optional capacity per Seat in the Game settings and the engine,
So that a capped chain can be simulated, and the feature can be left out without touching anything else.

**Acceptance Criteria:**

**Given** `FEATURE_CAPACITY` is on
**When** `GameSettings` sets a capacity for one Seat or for all Seats
**Then** `engine.advance` ships the smallest of inventory, amount to ship and capacity, and units the Seat cannot ship stay as backlog (FR-12, FR-26)
**And** capacity is off by default, and with no capacity set every golden trace from Story 1.2, Story 1.3, Story 1.4 and Story 1.6 is unchanged.

**Given** a capped Seat
**When** the conservation check runs
**Then** it allows inventory and backlog to be positive at once on that Seat only, and still requires it on every uncapped Seat (FR-29).

**Given** a capacity below peak demand
**When** `engine.settings.warnings` runs
**Then** it returns a non-blocking warning with the capacity and the peak demand (FR-12)
**And** a capacity that is not a whole number above 0 is rejected with the allowed range.

**Given** a golden trace with capacity 6 on one Seat and demand 8
**When** CI runs it
**Then** that Seat's backlog grows by 2 a Week once its stock allows, as in addendum §B.

**Given** `FEATURE_CAPACITY` is off
**When** settings with a capacity are validated
**Then** they are rejected with a stable code, and the `SeatState` and Decision log of every Game are the same as before this story.

**Covers:** FR-12 (capacity), FR-26 (capacity in the sequence), FR-29 (capped Seat), AD-1, AD-17

## Epic 2: LLM players that are safe to teach with

When this epic is done, the founder can run batches of simulated Games with LLM players and read cost, tokens, latency, retries, fallback share, Play guard switches and run-to-run variation per model config and Effort level, and the Admin can pin a model and set a cost limit from the command line. There is still no login and no screen: model config and budget are managed by a CLI command, and the Admin screens come in Epic 15. The epic owns `api/app/ai/` (the only LLM boundary) and `api/app/modules/players/`, and adds `platform/jobs` and the two worker processes.

### Story 2.1: Give every non-student Seat its Order from one order source

As a founder,
I want one function to supply the Order for every Seat that no Student holds,
So that Rule-based, scripted, Guided and later LLM Orders all take the same path in simulation and in real Games.

**Acceptance Criteria:**

**Given** `players.ensure_order(game, seat)` is added to `api/app/modules/players/service.py`
**When** a Week opens for a Seat with a non-student occupant
**Then** it is called in the transaction that opened the Week, and for a Guided Week, a `rule_based` occupant or a `scripted` occupant it places the Order through `games.commands.place_order` in that same transaction (AD-5)
**And** the Order for a `rule_based` occupant is the reference Order stored on the `seat_turns` row, never a recomputed one, and the Order for a `scripted` occupant comes from the policy whose id is on the occupancy row (Story 1.7).

**Given** the simulation runner from Story 1.11 chose and placed these Orders in its own loop
**When** this story is done
**Then** that loop is removed and the runner only creates, starts and waits for Games; there is one copy of the order-source logic, in `players`
**And** the Rule-based and scripted batches from Epic 1 give Orders and costs identical to their stored golden results.

**Given** a Seat that already has an Order for the open Week
**When** `ensure_order` is called again
**Then** it does nothing, so the call is safe to repeat (AD-9).

**Given** an open Week in which every Seat orders in the opening transaction (four `rule_based` or `scripted` occupants, or a Guided Week with no Student)
**When** the command that opened the Week commits
**Then** it has advanced at most one Week: an Order that `ensure_order` places joins the running command's transaction, row lock, `version` increment and `game:<id>` event, and neither starts an advance of its own nor finishes the Game, so `games.rules.week_complete` may already hold for the open Week at commit (AD-2)
**And** the new command `games.commands.advance(game)`, added to the AD-2 command list with its entry in the events registry, advances exactly one Week in its own transaction when `week_complete` holds and does nothing otherwise; on a complete last Week it runs that Week in full and calls `games.commands.finish` in the same transaction, as `place_order` does in Story 1.9
**And** every `games.commands` entry point, after its own commit, calls `advance` until it does nothing, so no caller has to drive a Game and none is left complete but open; `start` on a Game with four Rule-based players returns with the Game finished
**And** a test plays such a 36-Week Game and finds 35 advances to a next Week and one that finishes the Game, each in its own transaction with one `version` increment, and a second test stops between two advances and shows that calling `advance` again finishes the Game (NFR-4).

**Given** `games.commands.switch_to_rule_based(game, seat, reason)` is added to the AD-2 command list, with its entry in the events registry
**When** it runs mid-Week on a Seat without an Order
**Then** it appends an occupancy row with `occupant_kind = rule_based` and the reason, never edits an earlier row, and calls `ensure_order` right after, in the same transaction (AD-2, AD-5)
**And** on a Seat that already has an Order for the open Week it appends the row with `from_week = week + 1` and places nothing
**And** the registry test from Story 1.7 passes with the new commands.

**Given** `modules/players` reaches game state only through `games` `service.py` and `games.commands`
**When** the import check in CI runs
**Then** `players` imports no other module's internals, and `modules/games` has no LLM or provider import.

**Covers:** FR-30 (order source for AI-held Seats), NFR-4 (no Game left complete but open), AD-2, AD-5, AD-9

### Story 2.2: Register a model config and an evaluation budget from the command line

As an Admin,
I want to register a model config with its Effort levels and give it a budget, without a screen,
So that every LLM call has a known model and a known limit before the first one is made.

**Acceptance Criteria:**

**Given** the model config and budget tables are created by this story's revision, owned by `app/ai`
**When** I run `python -m app.ai.cli config add <file>`
**Then** one model config row is stored with provider, endpoint, region, model version, quantisation, prices, rate limit, a `prompts` map from purpose to version, and its Effort levels as data: each with a name, the provider parameters it sets, a per-attempt timeout and a per-Order time budget (AD-6, FR-78, NFR-2)
**And** the timeouts, time budgets and the Effort levels themselves are configuration with placeholder values marked as such (the only figure so far is the 8-second p95 placeholder), to be set from the prototype (issues #8, #9).

**Given** a model config that a simulation run or a Class session references
**When** I try to change it
**Then** the change is refused, and `config edit` creates a new row with a new id instead (AD-6, FR-68)
**And** `config edit <id> --prompt <purpose>=<version>` adds a purpose with its prompt version to the `prompts` map, or moves an existing purpose to another version, by writing such a new row, so a later story that brings a new LLM purpose gets it into a config without touching a referenced one
**And** `config list` shows every row with its id, model version, endpoint, region and whether it is referenced.

**Given** a model config
**When** I run `python -m app.ai.cli budget set --evaluation <config_id> --limit <usd> --reserve <usd>`
**Then** one budget row exists for that scope with `limit`, `reserve`, `spent` and `players_exhausted_at`, with money as `NUMERIC(18,8)` USD (AD-6, AD-22)
**And** the same command and row shape serve a Class session scope through `ai.budget`, so Epic 5 creates a Class session's row with the default from `AI_DEFAULT_SESSION_BUDGET_USD` and writes no table of its own.

**Given** the reserve size for Debrief and AI assessment is still open
**When** a budget is created without `--reserve`
**Then** the reserve comes from one configuration value with a stated placeholder, to be set after the prototype (issue #8).

**Given** other modules
**When** they read or change model config or budget
**Then** they do it only through `ai.config` and `ai.budget`, which are added to `api/app/ai/` for reuse, and a CI import check shows that no other package touches these tables (AD-6).

**Given** a config file that names a provider key, a prompt version with no file, or an Effort level without both time values
**When** `config add` runs
**Then** it is rejected with a message naming the field; a credential is never stored in the row, only the name of the environment variable that holds it.

**Covers:** FR-68 (model config), FR-69 (cost limit per scope), FR-78 (Effort levels as data), NFR-2, AD-6, AD-22

### Story 2.3: Make a validated LLM call through the gateway and log every attempt

As a founder,
I want one gateway function that makes an LLM call against the pinned config, validates the answer and logs each attempt,
So that no call anywhere in the product can skip pinning, validation or cost logging.

**Acceptance Criteria:**

**Given** `ai.run(purpose, budget_scope, inputs, output_schema, deadline)` is added to `api/app/ai/` as the only LLM entry point
**When** a caller uses it
**Then** the gateway resolves the scope's model config by id and the prompt version for the purpose from that config's `prompts` map; the caller passes no model, no prompt version and no scrub terms (AD-6, FR-68)
**And** `inputs` is one object with three parts: the values the prompt is rendered from; a caller reference of ids only (for a player Order the Game, Seat and Week), which is stored on every `llm_call` row of the call and never rendered; and an optional mock answer that only the mock provider reads
**And** it returns a validated result or one typed failure (`timeout`, `invalid_output`, `budget_exhausted`, `provider_error`), each carrying the ids of the `llm_call` rows the call wrote, and never raises a provider exception to the caller.

**Given** the `llm_call` table is created by this story's revision
**When** an attempt ends, whatever its outcome
**Then** one row is written with the caller reference, model config id, model, quantisation, provider, endpoint, Effort level, seed and temperature where supported, prompt version, input, output and reasoning tokens, cost, latency and outcome (FR-67, AD-6)
**And** the stored request and response bodies are the scrubbed ones.

**Given** an answer that does not match the output schema
**When** the gateway handles it
**Then** it retries inside its own loop, timing and logging each attempt separately with pydantic-ai's `output_retries` set to 0, up to the attempt limit of the purpose, and returns `invalid_output` when the attempts are used up (FR-32, AD-6).

**Given** no provider key is set and `APP_ENV` is `local`, `test` or `ci`
**When** `ai.run` is called
**Then** a deterministic mock answers: the same inputs give the same output, it returns the mock answer when the caller supplied one (for a player Order, the stored Rule-based reference Order) and otherwise a fixed answer that fits the output schema, and a test can script the mock to time out, return invalid output or fail (AD-17)
**And** with `APP_ENV=production` the mock is never used.

**Given** free-text inputs
**When** the gateway prepares the call
**Then** it scrubs them against the terms from `platform/pii.terms(scope)` and returns an offset map from each scrubbed text to its original, tested with supplied terms (AD-6, C-1)
**And** for an evaluation budget scope the term list is empty; the query over the `identity` tables is added by the first epic that sends Students' free text.

**Given** prompts live as files
**When** a config references `prompts.<purpose> = N`
**Then** the gateway loads `api/app/ai/prompts/<purpose>/v<N>.md`, and a CI test fails if a version referenced by any stored config is missing or its file hash has changed (AD-6).

**Given** the code base
**When** the CI import check runs
**Then** only `app/ai` imports `pydantic-ai` or a provider SDK, and `FallbackModel` appears nowhere (AD-6, FR-68).

**Covers:** FR-32 (schema-bound, validated, retried), FR-67 (LLM call metadata), FR-68 (no router fallback), AD-6, AD-17, C-1

### Story 2.4: Ask an LLM player for an Order from the Seat state alone

As a founder,
I want the LLM player's prompt built only from what a Student in that Seat would see, framed as a supply chain manager's job,
So that an AI player never gets more information than a person and never gets personal data.

**Acceptance Criteria:**

**Given** `players.llm.build_inputs(seat_state)` and the prompt file `api/app/ai/prompts/player_order/v1.md`
**When** an Order is requested for a Seat
**Then** the values the prompt is rendered from are built from the `SeatState` model and nothing else: no query, no `table_status`, no demand series, no number of Weeks (FR-31, AD-3)
**And** a test renders the prompt for every Role and Week of a Classic Game and finds no future demand, no Week count, no other Seat's inventory, backlog or Orders, and customer demand only in the Retailer's prompt
**And** the caller reference (Game, Seat, Week) and the mock answer (the Rule-based reference Order stored on the `seat_turns` row) travel in their own parts of the gateway inputs from Story 2.3, and the same test shows that neither appears in the rendered prompt or in the request.

**Given** the prompt text
**When** I read it
**Then** it describes the situation of a supply chain manager and the rules of that job (delays, must ship what is ordered if in stock, the two costs), asks for the best Order for this part of the chain, and says to act as if the business continues (FR-31)
**And** a test fails if it contains a word for game or player, the number of Seats, the chain's total, or a statement that Weeks advance when everyone has ordered.

**Given** the request
**When** it is sent through `ai.run(purpose="player_order", …)`
**Then** it asks for JSON and carries the JSON schema with one whole-number Order, and the Seat is referred to by Role only, with no name, email or other personal data in the structured inputs (FR-31, FR-32, C-1).

**Given** an answer whose Order is missing, not a whole number, below 0 or above the maximum Order
**When** the gateway validates it
**Then** it counts as a response that does not match and is retried like a schema failure (FR-32).

**Given** the question of whether a model recognises the exercise
**When** I run `python -m app.sim probe --config <id>`
**Then** it sends the player prompt for a sample of stored Seat states with one added question under its own purpose and prompt version, logs the answers as `llm_call` rows on the evaluation budget, and prints them for the founder to read; it places no Order (FR-31, issue #19).

**Given** I run `python -m app.sim prompt <game_id> --seat wholesaler`
**When** it finishes
**Then** it prints the exact prompt and schema that would be sent for that Seat's open Week.

**Covers:** FR-31, FR-32 (schema and range), AD-3, AD-6, C-1

### Story 2.5: Place LLM Orders as jobs, with the Rule-based Order as fallback

As a founder,
I want each LLM Order requested by a background job that places the Rule-based Order when the model fails,
So that a Game with LLM players always moves on and every replacement is marked.

**Acceptance Criteria:**

**Given** `platform/jobs` (procrastinate) is added to `api/app/platform/` for reuse, with its schema applied through an Alembic revision that runs the SQL procrastinate ships
**When** I run `docker compose up`
**Then** `worker-ai` (`python -m app.worker --queues ai-orders`) and `worker-batch` (`python -m app.worker --queues llm-batch`) start from the same image as `api` and need no keys (AD-9, AD-24, AD-17)
**And** later epics add their queues and the sweeper to `worker-batch`; this story adds none of them.

**Given** a simulation Game that is to have LLM players
**When** it is created and its Seats are assigned
**Then** `games.commands.create` accepts a model config id and one of that config's Effort levels for `purpose = simulation` and freezes both into the Game's `SessionRuntime` (AD-4, AD-22, FR-78)
**And** `players` learns which budget a Game's calls are charged to from one function, `games.service.budget_scope(game)`, added here: for a simulation Game it answers that config's evaluation budget, and a later Game purpose adds its own answer there
**And** `games.commands.assign_seat` accepts `llm` as an occupant kind, next to the two kinds of Story 1.7, and refuses it with a stable code for a Game whose `SessionRuntime` holds no model config (AD-5).

**Given** a Guided Week
**When** `ensure_order` runs for an `llm` occupant
**Then** the fixed Order is placed with `decided_by = guided` and no model call is made, proven by a test that counts `llm_call` rows (FR-31).

**Given** an open Week and a Seat with an `llm` occupant and no Order
**When** `players.ensure_order` runs
**Then** it defers one `ai-orders` job keyed `(game, week, seat)` on the same database connection, so the job commits with the Week or not at all, and its arguments are ids only (AD-5, AD-9).

**Given** the job runs
**When** it calls the gateway
**Then** it calls `ai.run` exactly once and never retries itself; the gateway makes at most 6 attempts for one Order (FR-32, AD-5, AD-6)
**And** on a valid answer it calls `games.commands.place_order` with `decided_by = llm` and the `llm_call` ids of every attempt, which `place_order` stores on the `seat_week` row, in a column added by this story's expand-only revision (FR-67).

**Given** the gateway returns a typed failure
**When** the job handles it
**Then** it places the Rule-based reference Order stored on the `seat_turns` row with `decided_by = rule_based`, `fallback` set to the failure type and the `llm_call` ids of the failed attempts on the row, so the retries behind a fallback Order can be counted; `decided_by` and `fallback` are never merged (FR-32, FR-67, AD-15)
**And** the occupancy stays `llm`, so the model is asked again the next Week.

**Given** the job is delivered twice, or runs after the Seat already has an Order
**When** it calls `place_order`
**Then** the second call gets `409 order_exists`, the job ends without error, and exactly one `seat_week` row exists.

**Given** the provider is down for a whole Game on the mock
**When** a simulated Game with four `llm` Seats is run
**Then** it finishes with every non-Guided Order marked `fallback = provider_error`, and the finished-game check passes (NFR-4).

**Covers:** FR-31 (no model call in Guided Weeks), FR-32 (fallback for that Week only, marked), FR-67 (LLM call ids, fallback mark), FR-78 (Effort level frozen into the Game), NFR-4 (no stall on provider failure), AD-4, AD-5, AD-6, AD-9, AD-15, AD-22, AD-24

### Story 2.6: Keep every LLM Order inside its time budget

As a founder,
I want each attempt timed and each Order given a deadline, with a rescue loop that places the fallback when the deadline passes,
So that nobody ever waits for an AI player longer than the Effort level allows.

**Acceptance Criteria:**

**Given** a Seat with an `llm` occupant in a Game with a pinned Effort level
**When** its turn opens
**Then** `ai_deadline_at` is written to the `seat_turns` row as `opened_at` plus that level's per-Order time budget, computed only by `games.rules.turn_times(game, seat, inputs)`, a pure function added to `modules/games` in this story; `inputs` is a named set that later stories extend with their own inputs, and it holds one so far, the per-Order time budget of the Effort level in the Game's `SessionRuntime`; the `ai_deadline_at` column is added to `seat_turns` by this story's expand-only revision (AD-20, NFR-2)
**And** when the Seat became `llm` later in the Week, the deadline counts from that moment.

**Given** an attempt that runs past the Effort level's per-attempt timeout
**When** the gateway handles it
**Then** the attempt is cancelled, logged as its own `llm_call` row with outcome `timeout`, and the next attempt starts only if it can finish inside the deadline; otherwise the gateway returns `timeout` (FR-32, NFR-2, AD-6).

**Given** the `worker-ai` process
**When** it runs
**Then** a rescue loop every 5 seconds places the Rule-based reference Order, with `decided_by = rule_based` and `fallback = timeout`, for any `llm` turn past its `ai_deadline_at` without an Order, through `place_order` (AD-5, NFR-2, NFR-4)
**And** a test that kills the job mid-call shows the Order placed within the time budget plus one loop interval
**And** the same loop calls `games.commands.advance` from Story 2.1 for any running Game whose open Week is complete, so a process that died between two advances cannot stall a Game (NFR-4).

**Given** a late answer from the model after the rescue loop has placed the fallback
**When** the job calls `place_order`
**Then** it gets `409 order_exists`, the fallback Order stands, and the late attempt is still logged with its tokens and cost; its caller reference from Story 2.3 ties it to the Game, Seat and Week, although the `seat_week` row the rescue loop wrote cannot list it.

**Given** a call with no deadline
**When** the gateway runs it
**Then** the attempt limit and the per-attempt timeout still apply and no `ai_deadline_at` is set, so the rescue loop skips the turn; Epic 8 uses this for the playout on `llm-batch` (FR-32, AD-5).

**Given** a finished simulated Game
**When** I read its `llm_call` rows and turns
**Then** latency per attempt and time from `opened_at` to `ordered_at` per Order are both available per Effort level, from stored rows alone.

**Covers:** FR-32 (timeout and time budget), NFR-2, NFR-4, AD-5, AD-6, AD-20

### Story 2.7: Call a real EU endpoint within its rate limit

As a founder,
I want the gateway to reach a real provider endpoint from the model config, respecting its rate limit,
So that prototype numbers come from the endpoint the pilot would use and a busy batch does not turn into mass fallback.

**Acceptance Criteria:**

**Given** the provider, route and model are still open (issues #8, #9)
**When** a model config names a provider adapter and a base URL
**Then** the gateway builds the provider client from the config and injects the base URL (for example an EU in-region endpoint), with no provider name hard-coded outside the adapter registry in `app/ai` (AD-6)
**And** the one adapter built in this story is `openai_compatible`, for any endpoint that speaks the OpenAI chat API at an injected base URL, chosen because it reaches an EU in-region router and EU-hosted open-weight models with one piece of code; the founder confirms or replaces this choice when issues #8 and #9 close
**And** adding a second provider is one adapter and one config row, with no change in `players`.

**Given** a config for a router that supports provider fallback
**When** the adapter builds the request
**Then** it turns router fallback off and asks for zero retention and no data collection where the route offers those switches, and a test asserts the request parameters (FR-68, C-1).

**Given** the config's rate limit
**When** many `ai-orders` jobs run at once
**Then** each call waits on a per-endpoint limiter sized from that value, and an HTTP 429 is treated as back-off inside the deadline, not as a failed attempt (AD-6, NFR-3)
**And** a test with the mock returning 429 for a burst shows the Orders arriving as `decided_by = llm` once the burst ends, and the fallback share staying at zero while deadlines allow.

**Given** the model config names a key variable that is not set
**When** `python -m app.sim run` is started with that config outside `local`, `test` and `ci`
**Then** it refuses to start and names the missing variable; in those three environments it says that the mock is in use (AD-17).

**Given** the endpoint is retired or keeps failing
**When** calls are made
**Then** every one returns a typed failure and falls back to the Rule-based Order; no other model or endpoint is ever tried (FR-68).

**Given** a response that reports reasoning tokens
**When** the attempt is logged
**Then** reasoning tokens are stored separately and included in the cost at the config's price, with the cost summed unrounded (FR-78, FR-67).

**Given** a provider key on the founder's machine and a model config for that endpoint
**When** the founder runs `python -m app.sim probe --config <id>` from Story 2.4
**Then** the answers come from the real endpoint, and the `llm_call` rows hold its real token counts, cost and latency under the region and model version the config names
**And** this check is run by hand and its output is kept with the prototype notes; CI never calls a real endpoint.

**Covers:** FR-68, FR-67 (tokens and cost), FR-78 (actual reasoning tokens), NFR-3 (rate limits), AD-6, AD-17, C-1

### Story 2.8: Reserve budget per call and switch to Rule-based players at the cost limit

As an Admin,
I want every attempt's cost reserved against the scope's budget, and LLM players switched to Rule-based players when the limit is reached,
So that a Class session or a test batch can never spend past its limit and play never stops.

**Acceptance Criteria:**

**Given** a budget row for the scope
**When** the gateway is about to make an attempt
**Then** it reserves the attempt's worst-case cost (max tokens × price) with one conditional `UPDATE` on that row and settles to the actual cost after the attempt; no limit check sums `llm_call` rows (AD-6, FR-69)
**And** a concurrency test with many parallel attempts never takes `spent` plus open reservations above the limit.

**Given** the purposes
**When** a player purpose asks for a reservation
**Then** it may spend only `limit` minus `reserve`, while non-player purposes may also spend the reserve (FR-69, AD-6).

**Given** a player reservation fails
**When** the gateway handles it
**Then** it sets `players_exhausted_at` on the budget row, returns `budget_exhausted`, and the job places the Rule-based reference Order with `fallback = budget_exhausted` (AD-5, AD-6).

**Given** `players_exhausted_at` has just been set
**When** `players` applies the cost-limit switch
**Then** `games.commands.switch_to_rule_based(reason = cost_limit)` is applied to every `llm` Seat of every unfinished Game charged to that scope, and the switch holds for the rest of the scope's life (FR-69, AD-5)
**And** while the state is set, every new occupancy that would be `llm` is created as `rule_based` with reason `cost_limit`.

**Given** the cost-limit state changes
**When** the transaction commits
**Then** one structlog line with ids only records it, and `ai.budget.state(scope)` reports the limit, the reserve, the amount spent and the time the limit was reached
**And** the notice to the Lecturer and the daily spend alert to the Admin are not sent here, because no User and no `platform/notify` exist yet: the epics that own those (Epic 3 for notify, Epic 15 for the cost view) read this state and `AI_DAILY_ALERT_USD`.

**Given** I run `python -m app.ai.cli cost --scope <id>`
**When** it finishes
**Then** it prints AI cost for the scope, per Game and per day, summed from settled `llm_call` costs and grouped by the Game in each row's caller reference (Story 2.3), so failed and late attempts count too, and the budget row's state (FR-69).

**Covers:** FR-69 (cost limit, reservation, switch; cost per scope, Game and day), AD-5, AD-6, C-3

### Story 2.9: Store a near-optimal reference Order for every Seat and Week

As a founder,
I want a second reference Order, computed with full knowledge of the chain, stored next to the Rule-based one,
So that the Play guard and the prototype can see how close an LLM player comes to near-optimal play.

**Acceptance Criteria:**

**Given** the near-optimal reference is added to `api/app/engine/` as a pure function
**When** `engine.near_optimal.order(settings, chain_state, demand_series, week, role)` runs
**Then** it returns a whole-number Order from 0 to the maximum Order and may use the full chain state and the demand series, which no player sees (FR-79, AD-1).

**Given** the algorithm is still open (issue #20)
**When** this story ships
**Then** it ships a placeholder algorithm carrying the label `placeholder-0` as its `algorithm_version`, the label is stored with every reference it produces, and replacing the algorithm is a new version with no change to callers.

**Given** a Week opens
**When** the `seat_turns` rows are written
**Then** the near-optimal reference Order and its algorithm version are computed once per Seat in that transaction and stored on the row, in a column added by this story's expand-only revision, and `place_order` copies them into the `seat_week` row without recomputing (AD-5, AD-15, FR-67)
**And** this holds for every Seat, whoever occupies it.

**Given** the near-optimal reference uses information beyond the Seat state
**When** the `SeatState`, the LLM prompt and `state_seen` are built
**Then** none of them contains it, proven by extending the leak test from Story 2.4 (AD-3, FR-31).

**Given** the Classic settings under constant demand
**When** the two references are computed
**Then** they coincide in every Week, and a golden trace with the Classic step stores both series so a later change of algorithm or parameters shows as a diff.

**Covers:** FR-79 (upper reference), FR-67 (two reference Orders), AD-1, AD-3, AD-5, AD-15

### Story 2.10: Switch a drifting LLM Seat to a Rule-based player with the Play guard

As a founder,
I want the Play guard to compare each LLM Order with both references over a rolling window and switch the Seat when it leaves the band,
So that an LLM player that orders erratically or near-optimally cannot spoil a Game.

**Acceptance Criteria:**

**Given** the Play guard statistics are added to `api/app/analysis/` as a pure function
**When** `analysis.play_guard.evaluate(seat_weeks, params)` runs
**Then** it reads only rows with `decided_by = llm`, so Guided Weeks and fallback Orders are left out, and returns `within_band` or `switch` with the statistic that caused it (FR-79, AD-1, AD-15).

**Given** the band of FR-79
**When** the guard evaluates a window
**Then** it checks two limits: the share of Orders within a set distance of the Rule-based reference (at least 95%), and, over Weeks where the two references differ, that the Orders are on average no closer to the near-optimal reference than a margin (5%); Weeks where the references coincide do not count against the upper limit
**And** the distance measure, the window length, the minimum number of Weeks and both limits are one versioned parameter set held as configuration with placeholder values marked as such, to be set in the prototype (issue #20), and the set's id is stored in the Game snapshot.

**Given** fewer `llm` Orders than the minimum number of Weeks
**When** the guard runs
**Then** it never switches (FR-79).

**Given** an Order with `decided_by = llm`
**When** `place_order` commits it
**Then** it runs the guard over the Seat's stored `seat_week` rows plus the new one in the same transaction, and on `switch` appends an occupancy row `rule_based` with reason `guard_switch` and `from_week = week + 1` (AD-5)
**And** the `ai-orders` job never runs the guard.

**Given** a Seat the guard has switched
**When** later Weeks open
**Then** it stays Rule-based for the rest of the Game, its Orders carry `reason = guard_switch`, and the Week of the switch can be read from the occupancy history (FR-79, FR-67).

**Given** Game settings other than the ones the band was calibrated for (Classic and the default Replay scenario)
**When** the guard runs
**Then** the upper limit is not applied and only a large deviation from the Rule-based reference switches the Seat, with "large" a placeholder in the same parameter set (FR-79)
**And** "calibrated for" is decided by one pure check, `analysis.play_guard.is_calibrated(settings, params)`, against the list of settings profiles in the parameter set: a profile is a named entry in the versioned parameter set, `classic` is the one listed in this story, and a further one, such as `replay_default` for the default Replay scenario once the band has been calibrated on it, is added by a new version of the set, with no code change in `analysis`.

**Given** mock players scripted to order far above the reference, exactly at the near-optimal reference, and within the band
**When** three simulated Games are run
**Then** the first two Seats are switched after the minimum Weeks and the third is never switched.

**Covers:** FR-79, FR-67 (switch Week), AD-1, AD-5, AD-15

### Story 2.11: Measure a model and Effort level on batches of simulated Games

As a founder,
I want to run batches of all-AI Games per model config and Effort level and get one report of what they cost and how they behaved,
So that I can decide from evidence which model and Effort levels are fit for teaching.

**Acceptance Criteria:**

**Given** a batch file naming a model config id, an Effort level, settings, seed, number of Games and the occupant per Role
**When** I run `python -m app.sim run <batch>`
**Then** `llm` occupants are played through `players`, the jobs and the gateway exactly as in a real Game, with `purpose = simulation`, the config id and Effort level frozen into each Game's `SessionRuntime` as Story 2.5 built it, and the Effort level stored on every `llm_call` row and Decision log row (AD-22, AD-4, FR-78)
**And** every call is charged to that model config's evaluation budget, never to a Class session
**And** this story's revision creates `simulation_batches` (id, the batch file as JSONB, its pass lines and the start time) and a nullable `batch_id` on `games`, both owned by `modules/games` and written only through `games.service`; the command prints the batch id.

**Given** a batch has finished
**When** I run `python -m app.sim report <batch_id>`
**Then** it prints per Game and for the batch: AI cost, tokens (input, output, reasoning), latency per attempt and time per Order (median and p95), retries per Order, fallback share by failure type, Play guard switches as a share of `llm` Seats, the Share of LLM Orders per Game, and the coefficient of variation of chain Total cost across the Games (PRD §10.1, SM-3, SM-6)
**And** every figure is computed from the Decision log and `llm_call` tables with the one AD-15 mapping: the Share of LLM Orders is `decided_by = llm` over the Orders with `occupant_kind ≠ student` and `decided_by ≠ guided`.

**Given** the prototype's pass lines must be written down before it runs
**When** a batch file carries pass lines (cost per Game, time per Order, switched share)
**Then** the report states pass or miss against each, the lines are stored with the batch and cannot be changed after its first Game starts
**And** no pass line has a default in code; the cost line of USD 0.10 per Game comes from the batch file (C-3).

**Given** the evaluation budget runs out during a batch
**When** the cost-limit switch applies
**Then** the remaining Games finish on Rule-based players and the report marks the batch as cut short, with the Game where the limit took effect.

**Given** a batch that ran on the mock provider
**When** the report is printed
**Then** it says so at the top, so mock numbers are never read as measurements.

**Given** CI
**When** the simulation smoke step from Story 1.11 runs
**Then** it registers a mock model config and an evaluation budget with the commands of Story 2.2, plays a few Games with `llm` occupants on the mock provider through `worker-ai`, and prints the report.

**Covers:** FR-78 (measured per Effort level), FR-68 (Share of LLM Orders, all-AI test runs), FR-79 (share of switched Seats reported), FR-69 (evaluation budget), NFR-2, AD-22, AD-15, C-3

### Story 2.12: Offer only measured Effort levels and pin the model

As an Admin,
I want to approve the Effort levels that were measured inside the limits and pin one model config as the default,
So that Lecturers are offered only safe choices and a Class session stays on one model from start to end.

**Acceptance Criteria:**

**Given** a batch report for a model config and Effort level
**When** I run `python -m app.sim approve <batch_id> --level <name>`
**Then** the simulation runner computes the report of Story 2.11 for that batch and passes its figures, the pass or miss against each pass line and whether the batch ran on the mock to one function, `ai.config.approve_effort(config_id, level, batch_id, figures)`; `app/ai` reads no games table and imports nothing from `modules` (AD-6)
**And** `approve_effort` stores a measurement row in `effort_measurements`, created by this story's revision and owned by `app/ai`, with the batch id, the measured cost per Game and time per Order, retries included, the fallback share and the share of Seats the Play guard switched (FR-78, C-3)
**And** the approval is refused when the batch missed its cost, time or switched-share pass line, carries no such line, or ran on the mock, so an offered level is one that stayed inside the Play guard's band (FR-78, FR-79)
**And** the model config row itself is not changed.

**Given** a model config
**When** a caller asks `ai.config.offered_effort_levels(config_id)`
**Then** it returns only levels that the endpoint supports and that have an approved measurement, with each level's measured effect on speed and cost, and which one is the default (FR-78)
**And** this function is the one source Epic 5's Class session screen reads.

**Given** a model config with at least one offered Effort level
**When** I run `python -m app.ai.cli pin <config_id>`
**Then** it becomes the active default model config, which a Class session receives when it is created (Epic 5), and the command shows the batch evidence it rests on, read from the `effort_measurements` rows (FR-68)
**And** pinning a config with no offered Effort level is refused.

**Given** a scope that references a config id
**When** the default is changed later
**Then** that scope keeps its config id, model version, endpoint and prompt versions for all its LLM use, and the Admin freezes a model across Class sessions by giving them the same id (FR-68, AD-6).

**Given** `APP_ENV` is `local`, `test` or `ci` and no model config is stored
**When** the api, a worker or `python -m app.sim` starts
**Then** one model config named `mock` is seeded for the mock provider, with one Effort level, a measurement marked `mock` that makes the level offered, and an evaluation budget, and it is pinned as the active default, so every later epic finds a default model config with zero keys (AD-17)
**And** with `APP_ENV=production` nothing is seeded, a `mock` measurement can never be approved and the `mock` config can never be pinned, proven by a test.

**Given** a deploy that adds a prompt file
**When** CI runs
**Then** the check from Story 2.3 confirms that no version referenced by a stored config was changed or removed (AD-6).

**Given** `python -m app.ai.cli config show <id>`
**When** it finishes
**Then** it prints the config, its offered Effort levels with their measurements, and whether it is the active default.

**Covers:** FR-68 (model pinned after all-AI test runs, frozen across Class sessions), FR-78 (only supported and measured levels offered), FR-79 (switched share decides the offer), AD-6, AD-17, C-3

### Story 2.13: Describe each AI player type in plain Norwegian

As a Lecturer,
I want a short plain-language description of how each AI player type decides,
So that I can choose an AI mode knowingly and explain the AI players to my Students.

**Acceptance Criteria:**

**Given** the two AI player types
**When** this story is done
**Then** a Norwegian bokmål description of each exists as a versioned file under `api/app/modules/players/descriptions/v1/`, and `players.service.describe(kind)` returns it with its version (FR-33, FR-72)
**And** the texts are original, use «enheter» and never «øl», and contain neither «Beer Game» nor «bullwhip» (C-4, AD-19).

**Given** the Rule-based player's description
**When** I read it
**Then** it states that the player follows a fixed anchoring-and-adjustment rule, names what it looks at (own stock, backlog, incoming orders and Supply line), says it uses the Game settings in force and no neighbour numbers, and names the source of its parameters
**And** while the placeholder parameter set is in use, the description says the parameters are not yet verified (issues #8, #17).

**Given** the LLM player's description
**When** I read it
**Then** it states that its behaviour varies between runs, that it is not told it is playing a game, that it may play better than a typical Student, and that a Rule-based Order replaces its Order when the model fails or the Play guard switches the Seat (FR-33).

**Given** a test
**When** it reads the descriptions and the code
**Then** it fails if the Rule-based description names an input the rule does not read, or if the LLM description contradicts the checks on the prompt from Story 2.4.

**Given** I run `python -m app.sim describe`
**When** it finishes
**Then** it prints both descriptions, which is how they are read until Epic 5 shows them next to the AI mode choice
**And** the longer Lecturer material on AI players and the AI assessment, and why not to grade from them, is a non-code deliverable owned by the founder (PRD §10.2) and is not written here.

**Covers:** FR-33, FR-72 (Norwegian), AD-19 (forbidden words), C-4

## Epic 3: Accounts and the Admin area

When this epic is done, the Admin can invite a Lecturer, who creates an account, logs in and lands on an empty home screen, and every User is held to their account role on every request. The Admin can search Users, grant and revoke roles, deactivate and reactivate Users, create Institutions and read the audit log. The epic owns `api/app/modules/identity/`, `api/app/modules/admin/` and their `web/src/modules/` mirrors, and it builds the shared `platform/auth`, `platform/authz`, `platform/audit`, `platform/ratelimit`, `platform/email`, `platform/notify`, the `mail` queue with the per-minute sweeper `ops.sweep`, and the web foundation, each inside the first story that needs it. It ends with the first production deploy on Railway.

### Story 3.1: See «Logg inn» in the product's design

As a Lecturer,
I want the «Logg inn» page to look and behave like the rest of the product on my phone and on my laptop,
So that the first page I meet is readable, operable by keyboard and in Norwegian.

**Acceptance Criteria:**

**Given** the «Logg inn» page
**When** it renders
**Then** it uses the colour tokens of DESIGN.md as the app theme with `paper` as the only background and no dark theme (UX-DR1), Source Sans 3 in weights 400, 600 and 700 self-hosted through `@fontsource/source-sans-3` with no request to Google Fonts (UX-DR3, AD-18), sizes in `rem`/`em` with no text under 13 px on phone and no all caps or letter-spacing (UX-DR3, UX-DR4), `rounded.sm` on controls and no shadows or gradients (UX-DR6)
**And** a Vitest contrast test checks every text-on-background pair in the text-on-tint table at 4.5:1 or better and fails on a pair outside the table (UX-DR2)

**Given** the first form in the product
**When** the Knapper, Lenke and Tekstfelt components are built
**Then** they are added to `web/src/components/` for reuse, on the shadcn setup from Story 1.1, with the shared interaction states (idle, hover, focus-visible, pressed, disabled, error), idle borders in `ink-muted`, and the `focus-ring` with its `paper` gap on every interactive element (UX-DR7, UX-DR8)
**And** the page has one primary button, «Logg inn», links are `lager` weight 600 underlined and never commit, and each Tekstfelt has its label above and an invalid state with a `restordre` border and the reason beside it (UX-DR9, UX-DR10, UX-DR11)
**And** a control that becomes unavailable while focused takes `aria-disabled="true"` and keeps focus, never the native `disabled` (UX-DR8)

**Given** the form is not yet connected to the api
**When** a person presses «Logg inn» with an empty field or a malformed e-mail
**Then** the Tekstfelt shows its invalid state with the reason beside it, and nothing is sent (UX-DR11)
**And** the login itself is not part of this story

**Given** the product's copy has one home
**When** this story is built
**Then** every UI string on the page comes from `web/src/copy/nb.ts`, which is created here from the PRD-term to UI-string table and the do and don't microcopy rules, in Norwegian bokmål with no exclamation marks (FR-72, UX-DR74, AD-19)
**And** the CI copy check that fails on «Beer Game» or «bullwhip» in pre-Debrief copy is added (AD-19)

**Given** the Playwright and axe setup added in this story
**When** CI runs against `docker compose`
**Then** the page passes at 320, 360 and 1440 px and at 400 % zoom with no page-level horizontal scroll, the axe check reports no WCAG 2.1 AA violation, every control is reachable and operable by keyboard, and tap targets are at least 44 px on phone (UX-DR75, UX-DR76, NFR-6)

**Covers:** FR-72, NFR-6, AD-18, AD-19, UX-DR1, UX-DR2, UX-DR3, UX-DR4, UX-DR6, UX-DR7, UX-DR8, UX-DR9, UX-DR10, UX-DR11, UX-DR74, UX-DR75, UX-DR76

### Story 3.2: Log in and log out with e-mail and password

As an Admin,
I want to log in with my e-mail and password and log out again,
So that only I can reach my part of the product.

**Acceptance Criteria:**

**Given** the `identity` module gets its first tables
**When** this story's Alembic revision runs
**Then** it creates the `users` table (UUIDv7 id, email unique case-insensitively, name, password hash, `is_active`, timestamps) and a `user_roles` table for the account roles Admin and Lecturer, and names and e-mails are stored only in these `identity` tables (AD-14, AD-24)
**And** the only other table this story adds is the one `platform/ratelimit` needs
**And** when the local stack starts on an empty database with `APP_ENV=local`, the seed adds one demo Admin and one demo Lecturer, with their sign-in details in the README, and no seed runs in any other environment (AD-17)

**Given** a User with a correct e-mail and password
**When** they press «Logg inn»
**Then** `platform/auth` verifies the password as SHA-256, base64, then bcrypt, and sets an HS256 JWT in an `httpOnly; Secure; SameSite=Lax` cookie that carries the `user_id` only (AD-11)
**And** every mutating request without the header `X-Requested-With: olspillet` is rejected, and the generated client sends the header on every mutation (AD-11)
**And** pressing «Logg ut» clears the cookie and returns to «Logg inn»

**Given** a wrong e-mail or a wrong password
**When** the User presses «Logg inn»
**Then** the page shows «Feil e-post eller passord.» and does not say which one was wrong or whether an account exists (UX-DR61)
**And** the API answers with the stable code `invalid_credentials` in the AD-19 error envelope, and the web app maps the code to the copy in `nb.ts` from Story 3.1 (FR-72)

**Given** repeated failed logins
**When** the count passes the limit per IP address or per account
**Then** `platform/ratelimit` (Postgres-backed, added to `platform/` for reuse) rejects further attempts with `rate_limited` until the window ends (AD-11)
**And** the limits are configuration (`LOGIN_RATE_LIMIT_PER_IP`, `LOGIN_RATE_LIMIT_PER_ACCOUNT`, window in minutes) with placeholder defaults to be confirmed before the pilot

**Given** the web app needs typed API calls
**When** this story is built
**Then** the client in `web/src/lib/api/` is generated from the FastAPI OpenAPI schema with `openapi-typescript` and `openapi-fetch`, and a CI job regenerates it and fails on any difference (AD-10)
**And** server state is held in TanStack Query, set up here with one `QueryClient` provider in the app shell, and the login is its first mutation (AD-10)

**Given** the Playwright and axe setup from Story 3.1
**When** CI runs against `docker compose`
**Then** the login flow (right password, wrong password, rate-limited, «Logg ut») passes at 320, 360 and 1440 px with no axe violation and by keyboard alone (UX-DR76, NFR-6, NFR-7)

**Covers:** FR-4, FR-72, NFR-6, NFR-7, AD-10, AD-11, AD-14, AD-17, AD-19, AD-24, UX-DR61, UX-DR76

### Story 3.3: Land on your own home and be held to your role

As a Lecturer,
I want to land on my own home screen after login and never see pages that are not mine,
So that I can trust that each User sees only what their account role allows.

**Acceptance Criteria:**

**Given** a logged-in User
**When** they open the product
**Then** an Admin lands on the «Admin-område», a Lecturer lands on an empty Lærerhjem, and any other User lands on an empty Hjem, each with the User's name and «Logg ut» (UX-DR77)
**And** a User with both the Admin and the Lecturer role lands on the Lærerhjem, which then carries a link to the «Admin-område», and the «Admin-område» carries a link to the Lærerhjem, so one login reaches both (FR-2); the two link texts are written in `nb.ts` in this story
**And** the Lærerhjem and Hjem are placeholders with a heading only; Epic 4 and Epic 6 fill them

**Given** any API route
**When** it is registered
**Then** it declares a `platform/authz` policy as a FastAPI dependency, built on `can(user, action, resource)`, and an api test walks every route and fails if one has no policy or is not on the short public list (login, password reset, Invitation acceptance, the lecturer-access request, health, webhooks) (AD-12, NFR-7)
**And** a CI check fails on a role comparison (`if role ==` or equivalent) inside `api/app/modules/` (AD-12)

**Given** `platform/authz` is added to `platform/` in this story
**When** its policies are tested
**Then** the tests show that an Admin may list and manage Users, that a Lecturer and a User without a role may not, and that the Admin role alone grants no read of Student answers or AI assessments (FR-5)
**And** the module documents that Class-scoped helpers such as `classes_visible_to(user)` are added to it by the epic that creates the tables they join

**Given** a logged-in User whose role does not allow a page
**When** they open its address, for example a Lecturer opening «Brukere og roller»
**Then** the page shows «Du har ikke tilgang til denne siden.» with a link to their own home («Til Hjem» or «Til Lærerhjem»)
**And** the API answers the same way whether or not the item exists, and actions the role lacks are not rendered at all (UX-DR59, FR-5)

**Given** a request with a valid cookie
**When** the API handles it
**Then** it loads the User and their roles from the database on every request, so a granted or revoked role takes effect at the next page load with the same login (FR-2)
**And** a deactivated User is rejected on every request (AD-11)

**Given** an address that matches no page
**When** a User opens it
**Then** the page shows «Fant ikke siden.» with a link home (UX-DR59)

**Given** the navigation rules
**When** the shell is built
**Then** there is no global navigation bar on phone, the Student hub is Hjem, and staff navigation follows Lærerhjem → Klasse → Klasseøkt / Oversikt as a breadcrumb that later epics extend (UX-DR77)
**And** Playwright with axe passes for the three homes and the permission-denied page at 320, 360 and 1440 px (NFR-6)

**Covers:** FR-2, FR-5, NFR-6, NFR-7, AD-11, AD-12, UX-DR59, UX-DR77

### Story 3.4: See what is happening when a page loads, fails or goes offline

As a Lecturer,
I want every page to tell me when it is loading, offline, out of date or failed,
So that I never wonder whether my work was saved.

**Acceptance Criteria:**

**Given** any page that loads data
**When** it is loading
**Then** the Skjelett component, added to `web/src/components/` for reuse, shows the real layout and columns with no numbers, no spinner and no shimmer, «Laster …» appears only after 1 s, and after 10 s the page shows the page-error state (UX-DR58)
**And** the 10 s limit is a named constant marked as an assumption

**Given** the device goes offline
**When** a page is open
**Then** the Tilkoblingslinje component, added to `web/src/components/` for reuse, shows «Frakoblet. Det du har skrevet, er tatt vare på på denne enheten.» at the top of the content as a polite status region that never covers controls, and live values carry «Sist oppdatert 21:14» with the real time (UX-DR58, UX-DR59)
**And** nothing is sent on its own when the connection returns
**And** in this epic the promise in that line holds for text still in its field on the open page, shown by a test that types, goes offline and comes back; keeping it across a reload comes with `web/src/lib/drafts.ts` in Epic 6

**Given** the connection returns
**When** the page detects it
**Then** the Tilkoblingslinje reads «Tilkoblet igjen.» for 5 s and disappears, and the page refetches its TanStack Query data in place without moving focus (UX-DR59)

**Given** a page request fails
**When** the error is shown
**Then** the Tilkoblingslinje shows «Siden kunne ikke lastes.» with the link «Prøv igjen», and anything typed stays in its field (UX-DR59)

**Given** a mutation fails
**When** the API returns an error or the request does not complete
**Then** «Det ble ikke lagret. Prøv igjen.» shows inline beside the action with `role="alert"`, the button stays enabled, the input is kept and focus stays on the button (UX-DR59, UX-DR76)
**And** the shared mutation helper in `web/src/lib/api/` that does this is added here for reuse, and maps unknown error codes to this message

**Given** the session cookie has expired or is invalid
**When** the User makes a request
**Then** the «Logg inn» page opens with focus on «Du er logget ut. Logg inn igjen for å fortsette.», and logging in returns to the same page (UX-DR59, UX-DR76)
**And** the return address is validated as a same-origin path; keeping a typed Order or answer through the login belongs to `web/src/lib/drafts.ts`, which Epic 6 adds

**Given** a User who prefers reduced motion
**When** any of these states change
**Then** no transition is animated (UX-DR76)
**And** Playwright tests force offline, a failed page load, a failed mutation and an expired session at 320 and 1440 px, and axe passes in each state (NFR-6)

**Covers:** NFR-6, AD-10, AD-19, UX-DR58, UX-DR59, UX-DR76

### Story 3.5: Send every mail through one pipeline

As a founder,
I want every mail the product sends to go through one notice pipeline with a sweeper behind it,
So that an Invitation or a reset link leaves at once, reminders are gathered politely, and no mail is lost or sent twice.

**Acceptance Criteria:**

**Given** a module wants someone told
**When** it calls `platform/notify.enqueue(user_id, kind, dedupe_key, ref, not_before)` in its own transaction
**Then** one row is written to the `notices` table, created by this story's revision and owned by `platform/notify`: it is unique on `dedupe_key` and holds ids only, and `user:<id>` is emitted through `platform/events.emit` in that transaction, with its registry entry (AD-9, AD-8)
**And** a notice may name its recipient by reference instead of by User: the caller passes `user_id=None` and, as `ref`, the id of the record that holds the address (for an Invitation, the Invitation id), and the kind's entry in the delivery table names the `service.py` function of the owning module that `messaging` calls to resolve the address when it renders the mail; such a notice emits no `user:<id>`, and the address is never copied into the notice (AD-14)

**Given** mail must be rendered and sent
**When** this story is built
**Then** `platform/email` is added with Jinja2 templates in `api/app/platform/email/templates/`, a Resend sender and a deterministic mock that logs `[email:mock]` when `RESEND_API_KEY` is missing outside production (AD-17, AD-19)
**And** every mail is in Norwegian bokmål, headed «ØL-spillet», sent from `EMAIL_FROM`, with its links built from `PUBLIC_BASE_URL`, and no name, e-mail or token appears in a log line or a job argument (FR-72, AD-14)

**Given** the delivery part of `modules/messaging`
**When** it is added
**Then** it holds the one table of delivery per `kind` (`immediate` or `digest`, each with its template), is the only reader of notices, through `platform/notify.claim_due`, and is the only module that defers the idempotent `mail` job, on the `mail` queue that `worker-batch` now also runs, with id-only arguments (AD-9)
**And** every mail sent gets one row in `mail_deliveries`, created by this story's revision and owned by `messaging`, with the notices it carried, the send time and the provider's message id; a `mail` job that runs twice finds the row and sends nothing

**Given** timers are data and one sweeper acts on them
**When** this story is done
**Then** `ops.sweep` exists in `modules/ops` as the one `procrastinate` periodic task, run every minute by `worker-batch` started with `--sweeper`: it only finds due work and calls the owning module, one item per transaction, with id-only arguments, and later epics add their due actions to it (AD-9)
**And** its first due action lets `messaging` claim the due notices and defer their `mail` jobs
**And** there is no other cron, and an api test runs the sweep twice over the same due notice and gets one mail

**Given** a notice of an `immediate` kind
**When** the transaction that enqueued it commits
**Then** its mail is deferred at once, without waiting for the sweep and also between 22:00 and 07:00: `enqueue` defers a claim job for the notice by its registered name through `platform/jobs`, on the caller's connection, so the job commits with the notice or not at all, and `platform/notify` imports no module (AD-9)
**And** the claim job leaves a notice of a `digest` kind untouched, and a notice whose `not_before` lies ahead waits for the sweep

**Given** notices of a `digest` kind for one User
**When** the sweep runs
**Then** they are gathered into one mail: a User gets at most one digest mail per calendar day in Europe/Oslo, none is sent between 22:00 and 07:00 Europe/Oslo, and a notice that falls due in the night or after that day's mail waits for the next allowed time (AD-9)
**And** a test with a controlled clock and a dummy `digest` kind shows that three notices in one day give one mail, that a notice due at 23:30 is mailed after 07:00, and that a notice due after the day's mail went out is mailed the next day

**Given** the local stack with no keys
**When** I run `python -m app.modules.messaging.cli send-test --user <id> --kind <kind>` with one of the two dummy kinds
**Then** an `immediate` test notice shows as one `[email:mock]` line within seconds and a `digest` one at the next sweep inside the allowed hours, each with its `mail_deliveries` row
**And** the dummy kinds and the command exist only outside production

**Covers:** FR-72, AD-8, AD-9, AD-14, AD-17, AD-19

### Story 3.6: Reset a forgotten password by e-mail

As a Lecturer,
I want to reset my password through a link sent to my e-mail,
So that I can get back in without asking the Admin.

**Acceptance Criteria:**

**Given** the «Logg inn» page
**When** a person follows «Glemt passord?», enters an e-mail and submits
**Then** the page shows «Hvis adressen har en konto, har vi sendt en lenke. Lenken virker i én time.» whether or not the address has an account (UX-DR61)
**And** requests are rate-limited per IP address and per account through `platform/ratelimit` (AD-11)

**Given** the address belongs to an active User
**When** the request is handled
**Then** `identity` stores a random single-use token as a hash with an expiry, in a `password_resets` table created here (AD-11)
**And** the link validity is configuration (`PASSWORD_RESET_VALID_MINUTES`, placeholder 60, the one hour the UX spine assumes)
**And** a `password_reset` notice is enqueued for that User through `platform/notify`, and this story registers `password_reset` as an `immediate` kind with its Jinja2 template in the delivery of Story 3.5, so the mail leaves at once (AD-9)

**Given** the reset mail
**When** it is rendered
**Then** it is in Norwegian bokmål, headed «ØL-spillet», sent from `EMAIL_FROM`, and its link is built from `PUBLIC_BASE_URL` (FR-72, AD-19)
**And** no name, e-mail or token appears in a log line or a job argument (AD-14)

**Given** a valid reset link
**When** the person sets a new password on «Nytt passord» and submits
**Then** the password is stored, the token is marked used, every other open reset token of that User is void, and the page shows «Passordet er endret.» followed by «Logg inn» with the e-mail prefilled (UX-DR61)

**Given** an expired or used link
**When** the person opens it
**Then** the page shows «Lenken er utløpt eller brukt.» with «Send ny lenke», which returns to «Glemt passord» (UX-DR61)

**Given** the address belongs to a deactivated User or to nobody
**When** the request is handled
**Then** no mail is sent and the response is the same as for an active User
**And** api tests cover the three cases and the single-use rule, and Playwright with axe covers both pages at 320, 360 and 1440 px (NFR-6)

**Covers:** FR-4, FR-72, NFR-6, NFR-7, AD-9, AD-11, AD-14, AD-19, UX-DR61

### Story 3.7: Invite a Lecturer or Admin by e-mail

As an Admin,
I want to send an Invitation to an e-mail address with the Lecturer or Admin role built in,
So that a new Lecturer can start without any further approval.

**Acceptance Criteria:**

**Given** the Admin is on «Brukere og roller» in the «Admin-område»
**When** they enter an e-mail, pick the role Faglærer or Admin and send
**Then** `identity` creates an Invitation in an `invitations` table created here (email, role, token hash, `expires_at`, `accepted_at`, inviter id), with a random single-use token stored only as a hash (FR-1, AD-11)
**And** the validity is configuration (`ROLE_INVITATION_VALID_DAYS`, placeholder 14)

**Given** the Invitation is created
**When** its transaction commits
**Then** an `invitation` notice is enqueued through `platform/notify`, addressed by reference to the Invitation because the address has no User yet, and this story registers `invitation` as an `immediate` kind with its Jinja2 template in the delivery of Story 3.5, so the `mail` job sends a Norwegian mail headed «ØL-spillet» with the link (AD-9, FR-72)
**And** `identity.service` gains the function that `messaging` calls to resolve an Invitation id to its address, so the address stays in `identity` tables (AD-14)

**Given** an Admin action happens for the first time
**When** this story is built
**Then** `platform/audit.record(actor, action, target, change)` is added to `platform/` with an `audit_events` table (actor `user_id`, empty when the system acts, action, target ids, change, time), and sending an Invitation writes one row in the same transaction (FR-3, AD-15, NFR-7)
**And** the row holds ids and the role, never a name or an e-mail address (AD-14)

**Given** the e-mail is malformed
**When** the Admin submits
**Then** the Tekstfelt shows its invalid state with the reason beside it and nothing is sent (UX-DR11)

**Given** the address already has an open Invitation for the same role
**When** the Admin sends again
**Then** the earlier token is void, a new one is sent with a new expiry, and an api test finds exactly one open Invitation for that address

**Given** a User who is not an Admin
**When** they call the invite endpoint
**Then** the `platform/authz` policy rejects the request and no Invitation, mail or audit row is created (FR-5, AD-12)

**Given** the invite form and its result line
**When** tested
**Then** the page has one primary button labelled with its effect, the form is one column, and Playwright with axe passes at 320 px (1280 px at 400 % zoom), at 200 % text and at 1440 px with no page-level horizontal scroll (UX-DR57, UX-DR75, NFR-6)

**Covers:** FR-1, FR-3, FR-5, FR-72, NFR-6, NFR-7, AD-9, AD-11, AD-12, AD-14, AD-15, UX-DR57, UX-DR75

### Story 3.8: Create an account from an Invitation

As a Lecturer,
I want to follow my Invitation, set a password and my name, and come straight in,
So that I have an account with my role without waiting for anyone.

**Acceptance Criteria:**

**Given** a valid Invitation link
**When** the person opens it
**Then** «Du er invitert» shows the e-mail prefilled and not editable, fields for name and password, the remaining validity of the Invitation, and the primary button «Opprett konto og gå videre» (FR-4, UX-DR61)
**And** the validity line follows «Invitasjonen er gyldig i 14 dager.» with the real number of days; the sentence about Rolle and spill is shown only for Student Invitations, which Epic 4 adds

**Given** the person submits a valid name and password
**When** the acceptance is handled
**Then** one transaction creates the User, grants the role built into the Invitation, marks the token used and logs the User in (FR-1, FR-4)
**And** a new Lecturer lands on the empty Lærerhjem and a new Admin on the «Admin-område», with no approval step

**Given** the Invitation's e-mail already has a User
**When** that person opens the link
**Then** the page asks them to log in instead of creating an account, and after login the role is added to the existing account (FR-4)
**And** the database holds exactly one User per e-mail address, compared case-insensitively

**Given** an expired or used Invitation link
**When** a person opens it
**Then** the page shows a message that the link is expired or used and one action to ask for a new Invitation, which sets `renewal_requested_at` on that Invitation (a column added here), is rate-limited through `platform/ratelimit`, and answers the same way for any link, without revealing whether an account exists (FR-1, UX-DR61)
**And** the copy for this state is written in `nb.ts` in this story, since the UX spine leaves it open

**Given** repeated acceptance attempts
**When** the count passes the limit per IP address or per Invitation
**Then** `platform/ratelimit` rejects them (AD-11)

**Given** `APP_ENV=production` and an address in `BOOTSTRAP_ADMIN_EMAILS` that has no User and no open Invitation
**When** the api starts
**Then** it creates one Invitation with the Admin role for that address and enqueues its mail, once, and writes an audit row with the system as actor (AD-11)
**And** a User whose address is in the list and who has no Admin role gets it at first login; every later role is granted in the Admin area (FR-1, FR-2)

**Given** the page
**When** tested
**Then** Playwright with axe passes the create-account flow, the existing-account flow and the expired-link state at 320, 360 and 1440 px, with password rules stated in the help line under the field before the person types (NFR-6, UX-DR75)

**Covers:** FR-1, FR-2, FR-4, NFR-6, NFR-7, AD-11, AD-15, UX-DR61, UX-DR75

### Story 3.9: Find Users and grant or revoke roles

As an Admin,
I want to search Users by e-mail or name and grant or revoke the Lecturer or Admin role,
So that the right people can teach and administer.

**Acceptance Criteria:**

**Given** the Admin is on «Brukere og roller»
**When** the page opens
**Then** it lists Users with name, e-mail, account roles and status (active or deactivated), in the list envelope with a cursor, as a table that reflows to one column of rows at 320 px (FR-3, UX-DR57, UX-DR75)

**Given** the Admin types part of an e-mail or a name in the search field
**When** the search runs
**Then** the list shows the matching Users, and «Ingen treff.» when there are none (FR-2, UX-DR57)
**And** the search runs only in `identity` tables and the query text is not logged (AD-14)

**Given** a User without the Lecturer role
**When** the Admin grants it
**Then** the role is stored, an audit row is written in the same transaction, and `user:<id>` is emitted (FR-2, FR-3, AD-8, AD-15)
**And** that User sees the Lærerhjem at their next page load with the same login (FR-2)

**Given** a User with the Lecturer or Admin role
**When** the Admin revokes it
**Then** the role is removed with an audit row and takes effect at that User's next request (FR-2)

**Given** the revoke rule for Lecturers who own Classes
**When** this story is built
**Then** `identity.service.revoke_role` asks a registry of revoke blockers before it removes the Lecturer role, answers `409 role_revoke_blocked` with the count when a blocker reports owned Classes, and the page shows «Bård eier 2 Klasser. Legg til en annen Faglærer eller arkiver Klassene først.» with the User's first name and the real count (FR-2, UX-DR57)
**And** api and Playwright tests prove the blocked state with a test blocker; the blocker that reads Class ownership is registered by the story that creates Classes (Epic 4)

**Given** the Admin tries to revoke their own Admin role while no other active Admin exists
**When** they submit
**Then** the request is rejected with `last_admin`, so the product is never left without an Admin

**Given** each grant and revoke control
**When** it is rendered
**Then** it is a button labelled with its effect and the User's name, with no confirmation dialog, and Playwright with axe passes at 320 px, 200 % text and 1440 px (UX-DR9, UX-DR57, NFR-6)

**Covers:** FR-2, FR-3, FR-5, NFR-6, NFR-7, AD-8, AD-12, AD-14, AD-15, UX-DR9, UX-DR57, UX-DR75

### Story 3.10: Deactivate and reactivate Users and resend Invitations

As an Admin,
I want to deactivate and reactivate a User and resend an Invitation,
So that access follows who should have it today.

**Acceptance Criteria:**

**Given** an active User in «Brukere og roller»
**When** the Admin looks at the deactivate control
**Then** the button states the consequence with the User's first name: «Deaktiver Bård. Bård kan ikke logge inn, og dataene blir værende.» (UX-DR57)

**Given** the Admin presses it
**When** the action commits
**Then** `is_active` is set to false, an audit row is written and `user:<id>` is emitted in the same transaction (FR-3, AD-8, AD-15)
**And** none of the User's data is deleted or changed

**Given** a deactivated User
**When** they try to log in with the right password
**Then** the page shows «Kontoen er deaktivert. Ta kontakt med faglæreren din.» (UX-DR61, FR-3)
**And** a request with their still-valid cookie is rejected at once (AD-11), and their open password reset tokens and Invitations cannot be used

**Given** a deactivated User
**When** the Admin reactivates them
**Then** they can log in again with the same password and the same roles, and an audit row is written (FR-3)

**Given** the list of Invitations on «Brukere og roller»
**When** the Admin opens it
**Then** each Invitation shows its address, role and status (open, accepted, expired), where expiry is read from `expires_at` with no background job (FR-3)
**And** an Invitation whose recipient has asked for a new one (`renewal_requested_at` from Story 3.8) says so in text, with copy written in `nb.ts` in this story (FR-1)

**Given** an open or expired Invitation
**When** the Admin resends it
**Then** the old token is void, a new token with a new expiry is mailed, the request mark is cleared, and an audit row is written (FR-3)
**And** an accepted Invitation offers no resend

**Given** the Admin deactivates themselves or the last active Admin
**When** they submit
**Then** the request is rejected with `last_admin`
**And** api tests cover the login, the live-cookie rejection and the audit rows, and Playwright with axe covers the page at 320 and 1440 px (NFR-6)

**Covers:** FR-1, FR-3, NFR-6, NFR-7, AD-8, AD-11, AD-15, UX-DR57, UX-DR61

### Story 3.11: Create Institutions

As an Admin,
I want to create the Institutions that Classes belong to,
So that data can be kept apart and reported per school.

**Acceptance Criteria:**

**Given** the «Admin-område»
**When** the Admin opens «Institusjoner»
**Then** they see the list of Institutions with name and creation date, or an empty state with the one action to create the first

**Given** the Admin enters a name and saves
**When** the action commits
**Then** an Institution is stored in an `institutions` table created here and owned by `identity`, and an audit row is written in the same transaction (FR-3, AD-15)

**Given** a name that is empty or already used (compared case-insensitively)
**When** the Admin saves
**Then** the Tekstfelt shows its invalid state with the reason beside it and nothing is stored (UX-DR11)

**Given** an existing Institution
**When** the Admin renames it
**Then** the new name is stored with an audit row that holds the old and the new name

**Given** other modules need Institutions
**When** this story is built
**Then** `identity.service` exposes `list_institutions()` and `get_institution(id)` for them, and no delete action exists in v1
**And** only an Admin passes the `platform/authz` policy for create and rename (AD-12)

**Given** the page
**When** tested
**Then** all copy comes from `nb.ts` with the working term «Institusjon», and Playwright with axe passes at 320 and 1440 px (FR-72, NFR-6)

**Covers:** FR-3, FR-72, NFR-6, AD-12, AD-15, UX-DR11

### Story 3.12: Read the audit log

As an Admin,
I want to read who did what and when,
So that every Admin action can be accounted for.

**Acceptance Criteria:**

**Given** the «Admin-område»
**When** the Admin opens the audit log
**Then** it lists audit events newest first with time in Europe/Oslo, actor, action, target and change, in pages through the list envelope (FR-3, NFR-7)
**And** actor and target names are resolved from `identity` at read time, so the stored rows hold ids only, and a row with no actor is shown as done by the system (AD-14)

**Given** the actions built in this epic (Invitation sent and resent, role granted and revoked, User deactivated and reactivated, Institution created and renamed, bootstrap Invitation)
**When** each is performed
**Then** exactly one audit row exists for it, and an api test asserts this for every action in the list (FR-3)

**Given** the audit table
**When** any code path is inspected
**Then** `platform/audit` exposes `record` and read functions only; there is no update or delete of an audit row, and a test asserts that the module has none (AD-15)

**Given** many events
**When** the Admin filters by actor, by action or by a date range
**Then** the list shows the matching events, and «Ingen treff.» when there are none

**Given** a User who is not an Admin
**When** they request the audit log
**Then** the policy rejects the request with the permission-denied state (FR-5, AD-12)

**Given** later epics record a Takeover by a person and a Completion status correction
**When** they call `platform/audit.record`
**Then** their events appear in this list with no change to this page, because the action name and change are rendered from generic fields with a copy entry per action in `nb.ts` (FR-3)
**And** the table scrolls inside its own region at 320 px, and Playwright with axe passes at 320 and 1440 px (UX-DR75, NFR-6)

**Covers:** FR-3, FR-5, NFR-6, NFR-7, AD-12, AD-14, AD-15, UX-DR75

### Story 3.13: Read the Landing page and ask for lecturer access

As a Lecturer,
I want a public page that shows what the product is and lets me ask for access,
So that I can decide to use it and reach the Admin without an open sign-up.

**Acceptance Criteria:**

**Given** a visitor who is not logged in
**When** they open the root address
**Then** the Landing shows the product name «ØL-spillet», the headline «Hver uke har en strek og et tall. Studentene ser begge.» in `display`, a lead paragraph, the primary button «Be om lærertilgang» and the secondary «Logg inn» (UX-DR61, UX-DR9)
**And** a logged-in User who opens the root address goes to their own home

**Given** the Landing shows example numbers
**When** it renders
**Then** it shows one Seat in a Veiledet uke from the synthetic fixture as an HTML week table with tabular lining figures, labelled «Demodata» in `caption` `ink-muted`, and the line «Lagerkurvene for hele klassen ser du først når du er logget inn.» (UX-DR70, UX-DR3)
**And** no chart code is written in this story: the graph over the table and the second «Demodata» figure come from `web/src/components/charts` once Epic 6 and Epic 7 have built it

**Given** the content rules for the Landing
**When** the copy check runs in CI
**Then** the page holds no week counts, no rising Ordre inn, no amplification, no customers, quotes, prices or learning claims, and neither «Beer Game» nor «bullwhip» (AD-19, UX-DR74)
**And** the words «øl» and «kasser øl» appear nowhere except in the product name

**Given** a visitor presses «Be om lærertilgang»
**When** they fill in name, e-mail and Institution in the short form and submit
**Then** the request is stored in an `access_requests` table in `identity` created here, the form is rate-limited per IP address through `platform/ratelimit`, and the page confirms that the Admin will answer by e-mail (UX-DR61)
**And** no account and no Invitation is created by the request (PRD non-goal: no public sign-up)

**Given** open access requests
**When** the Admin opens «Brukere og roller»
**Then** the requests are listed with name, e-mail, Institution and date, each with an action that prefills the invite form of Story 3.7 with the Faglærer role, and an action to dismiss the request
**And** inviting from a request or dismissing it writes an audit row (FR-3, AD-15)

**Given** phone and laptop
**When** the Landing is tested
**Then** on phone the columns stack in the order headline, lead, buttons, Seat table, and Playwright with axe passes the page and the request form at 320, 360 and 1440 px and at 400 % zoom (UX-DR75, NFR-6)

**Covers:** FR-1, FR-3, FR-72, NFR-6, AD-15, AD-19, UX-DR3, UX-DR9, UX-DR61, UX-DR70, UX-DR74, UX-DR75

### Story 3.14: Prepare a strict production configuration in the repo

As a founder,
I want the production configuration, the startup guard and a smoke test in the repo,
So that the first deploy is a matter of following a checklist, not of writing code under pressure.

**Acceptance Criteria:**

**Given** the Structural Seed names `railway/`
**When** this story is done
**Then** `railway/` holds one `railway.toml` per service (`proxy`, `web`, `api`, `worker-ai`, `worker-batch`) with the region pinned to EU West, the start command of SETUP-GUIDE §1, the health check path, `watchPatterns`, and overlap and draining seconds (AD-11)
**And** `api`, `worker-ai` and `worker-batch` build from the same `api/Dockerfile` and commit, and only the `api` service has the pre-deploy command `alembic upgrade head` (AD-24)

**Given** `APP_ENV=production`
**When** `JWT_SECRET`, `DATABASE_URL`, `RESEND_API_KEY` or a storage key (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`) is missing or left at a default
**Then** the api and both workers refuse to start with a message naming the variable, proven by a test that starts each process with one secret removed (AD-17)
**And** the storage keys are in the guard from now on, as AD-17 lists them, although the code that uses them comes with `platform/storage` in a later epic; the founder sets them at the first deploy

**Given** the Supabase session pooler has a fixed pool size
**When** this story is done
**Then** the written connection budget is recorded in `docs/ops/connection-budget.md`: per process the SQLAlchemy pool with no overflow, the procrastinate pool and one LISTEN connection for `api`, doubled for a deploy overlap, with the pooler size it needs
**And** `DB_POOL_SIZE` sets the pool per process, and the production settings require TLS on the database connection (NFR-7)

**Given** the proxy rules from Story 1.1
**When** I run the smoke test `scripts/smoke` against a base URL
**Then** it asserts that `/api/health` answers 200 through the proxy, that `/print/*` answers 404 and that `/` is served by `web`, and it reports every failed request while it runs, so it can watch a deploy (AD-11)
**And** CI runs it against `docker compose`

**Covers:** NFR-7, AD-11, AD-17, AD-24

### Story 3.15: Reach the product in production

As a founder,
I want the product deployed to production on Railway with strict configuration,
So that the bootstrap Admin can log in on the real domain and invite the first Lecturer.

**Acceptance Criteria:**

**Given** steps that need accounts and DNS (Railway, Supabase, Resend, the domain)
**When** this story is worked
**Then** the dev agent writes the runbook `docs/ops/first-deploy.md` as a checklist of those steps with the variable names of SETUP-GUIDE §3, the founder carries them out and ticks them off, and the story is done when the criteria below hold in production
**And** no secret is committed to the repo, which is public

**Given** the Railway project `olspillet`
**When** the services are created from the per-service config in `railway/` (Story 3.14)
**Then** `proxy`, `web`, `api`, `worker-ai` and `worker-batch` run in EU West, only `proxy` has a public domain, and the others are reached on `*.railway.internal` (AD-11)
**And** the smoke test of Story 3.14 passes against the public domain: Caddy sends `/api/*` to `api` with immediate flush, answers 404 for `/print/*` and sends everything else to `web` (AD-11)

**Given** `APP_ENV=production`
**When** one required secret is removed from one service
**Then** that service refuses to start, and the check is run once in production and its result recorded in the runbook (AD-17)

**Given** the Supabase project in eu-central-1
**When** the services connect
**Then** they use the session pooler on port 5432 only, and the pooler's pool size is set to fit the connection budget of Story 3.14
**And** all traffic is HTTPS at the public domain, the database connection requires TLS, and the founder confirms in the project settings that the data is encrypted at rest and notes it in the runbook (NFR-7)

**Given** the Resend account
**When** the sending domain is set up
**Then** SPF, DKIM and DMARC are verified, the sending region is eu-west-1, `EMAIL_FROM` uses the verified domain, and a password reset mail sent from production arrives (NFR-10 groundwork)

**Given** the open decision on CI gating and promotion
**When** this story is done
**Then** the decision is made and recorded in the repo: whether Railway waits for green GitHub checks, and who moves `main` to `production` and how; the `production` branch auto-deploys and `main` stays the working branch

**Given** health checks `api` `/api/health` (checks the database), `web` `/` and `proxy` `/api/health`
**When** a second deploy with a no-op migration runs
**Then** it uses overlap and draining so the old and new code run side by side, and it completes without a failed request in the smoke test (AD-24)

**Given** production is up with `BOOTSTRAP_ADMIN_EMAILS` set
**When** the bootstrap Admin follows the mailed Invitation, creates the account and logs in
**Then** they land on the «Admin-område» and can send an Invitation to a Lecturer, who creates an account and lands on the empty Lærerhjem (FR-1, FR-4)

**Covers:** FR-1, FR-4, NFR-7, NFR-10, AD-11, AD-17, AD-24

## Epic 4: Classes, Roster and Invitations

When this epic is done, a Lecturer can create a Class, upload the Roster from a Canvas export or by pasting addresses, send Invitations with a validity period, follow who has registered, register Students by hand, and share the Class with co-owner Lecturers and Assistant lecturers. A Student can register through the Invitation and become a Student in the Class. The epic owns `api/app/modules/classes/` and `web/src/modules/classes/`; Roster addresses and staged upload rows are personal data and live in `identity` tables, which `classes` reaches only through `identity.service` (AD-14).

### Story 4.1: Create a Class from the Lærerhjem

As a Lecturer,
I want to create a Class with a name, an Institution and an optional course code,
So that I have a place for my Students and own it.

**Acceptance Criteria:**

**Given** a Lecturer with no Classes
**When** they log in
**Then** the Lærerhjem shows an empty state where «Ny Klasse» is the only action (UX-DR56)

**Given** the Lecturer presses «Ny Klasse»
**When** «Lag Klasse» opens and they enter a name, pick an Institution from `identity.service.list_institutions()` and optionally a course code, and save
**Then** a Class is stored in a `classes` table and the Lecturer is stored as owner in a `class_staff` table, both created here and owned by `modules/classes`, in one transaction (FR-6)
**And** the form reuses Tekstfelt and Knapper from `web/src/components/` and is one column with the page title in `title-page`

**Given** a missing name or no Institution chosen
**When** the Lecturer saves
**Then** the field shows its invalid state with the reason beside it and nothing is stored (UX-DR11)

**Given** Class-owned data now exists
**When** this story is built
**Then** `platform/authz` gains the scoped helper `classes_visible_to(user)` and the policies for reading and managing a Class, every `classes` repository query joins through the helper, and the route-policy test from Epic 3 still passes (AD-12)
**And** a Lecturer who is not staff of a Class gets the permission-denied state for its address, the same as for a Class that does not exist (FR-5)

**Given** a Lecturer with Classes
**When** they open the Lærerhjem
**Then** «Klassene dine» lists each Class with name and course code, each a Lenke to the Class, and «Ny Klasse» stays available (UX-DR56)
**And** the page has the places for what is waiting and the next deadline, which stay empty until Class sessions exist (Epic 5)

**Given** the revoke-blocker registry from Epic 3
**When** this story is built
**Then** `classes.service` registers the blocker that counts the active Classes a User owns, so the Admin's revoke of the Lecturer role is blocked with the real count (FR-2)
**And** an api test proves the block end to end with a Lecturer who owns one Class

**Given** the local seed
**When** the stack starts on an empty database with `APP_ENV=local`
**Then** the seed adds one demo Class owned by the demo Lecturer; its 8 registered demo Students are seeded in Story 4.5, the first story in which a Student can be in a Class (AD-17)
**And** Playwright with axe passes the Lærerhjem (empty and filled) and «Lag Klasse» at 320 px (1280 px at 400 % zoom), 200 % text and 1440 px with no page-level horizontal scroll (NFR-6)

**Covers:** FR-2, FR-5, FR-6, NFR-6, AD-12, AD-14, AD-17, UX-DR11, UX-DR56

### Story 4.2: Upload a Roster file and pick the e-mail column

As a Lecturer,
I want to upload the student list I exported from Canvas and choose which column holds the e-mail addresses,
So that I do not have to edit the file first.

**Acceptance Criteria:**

**Given** «Lag Klasse» for a Class the Lecturer owns
**When** no file is chosen
**Then** the Filopplasting component shows an outlined box with «Velg fil» and the link «Lim inn adresser i stedet», and accepts .xlsx and .csv (UX-DR47)

**Given** the Lecturer chooses a readable .xlsx or .csv file
**When** the upload is handled
**Then** the api parses it in memory (openpyxl in read-only mode for .xlsx; CSV with delimiter and encoding detection for comma and semicolon, UTF-8 and Windows-1252), and the page shows the file name, the row count as «250 rader lest» with the real number, and the link «Bytt fil» (FR-7, UX-DR47)
**And** two synthetic fixtures made for the tests, with invented names and addresses, one in the column layout of a Canvas people export and one in the layout of a Canvas grade-book export, are read without editing; a file with no e-mail column makes the page say so and point to «Lim inn adresser i stedet» (PRD assumption under FR-7)
**And** the check against real Canvas exports is not part of this story: it is recorded in the module README as an open point for the founder, who supplies anonymised exports before the pilot

**Given** the deferred decision on Roster upload staging
**When** this story is built
**Then** the decision is made and recorded in the story's notes and the module README: the uploaded file is never written to disk or to a bucket; its cell values are stored as staged rows in `identity` tables `roster_uploads` and `roster_upload_rows` created here (upload id, Class id, uploader id, row number, cells as JSONB, `expires_at`), reached only through `identity.service` (AD-14)
**And** the expiry is configuration (`ROSTER_STAGING_TTL_HOURS`, placeholder 24); expired uploads are never returned, and the idempotent `identity.purge_expired_roster_uploads()` deletes them on every upload and every read of a Class's staging, so it can later be called from `ops.sweep` unchanged
**And** a new upload for the same Class replaces the earlier staged upload, and staged rows are never written to logs or job arguments

**Given** the file is read
**When** the page shows the «E-postkolonne» selector
**Then** the column with the largest share of cells that look like addresses is preselected, with its reason, for example «Kolonne C, E-post. Valgt fordi alle rader unntatt fire ser ut som adresser.» (UX-DR47)
**And** the selector is a native select styled as Tekstfelt and lists every column by letter and header

**Given** the Lecturer chooses another column
**When** the selection changes
**Then** the staged rows are evaluated again against that column at once, from the staged cells, with no new upload (FR-7)

**Given** a file that cannot be parsed, is empty, is of another type or is over the size limit
**When** it is uploaded
**Then** the page shows «Filen kunne ikke leses. Bruk .xlsx eller .csv, eller lim inn adressene.» and nothing is staged (UX-DR47)
**And** the size and row limits are configuration (`ROSTER_MAX_FILE_MB`, `ROSTER_MAX_ROWS`) with placeholder values that cover a Class of at least 400 Students (NFR-3)

**Given** the Lecturer presses «Bytt fil»
**When** the action completes
**Then** the staged upload is deleted and the box returns to its empty state

**Given** the upload flow
**When** tested
**Then** api tests cover both synthetic fixtures, a file with no e-mail column, a semicolon CSV, a file with no header row and an expired staging, and Playwright with axe passes the flow by keyboard only at 320 px, 200 % text and 1440 px (NFR-6)

**Covers:** FR-7, NFR-6, AD-12, AD-14, UX-DR47

### Story 4.3: See invalid rows and paste addresses instead

As a Lecturer,
I want to see which rows cannot be used and why, and to paste addresses when the file does not help,
So that every valid Student is accepted and no bad address is mailed.

**Acceptance Criteria:**

**Given** a staged upload with a chosen e-mail column
**When** the rows are evaluated
**Then** each row is valid or invalid by one validation function in `identity.service`, and the page shows the heading «Ugyldige rader: 4 av 250» with the real counts and one line per invalid row with its row number, its cell value and its reason (FR-7, UX-DR47)
**And** the reasons include «Domene mangler», «Mangler @», «To @» and «Tom celle», each as text and never by colour alone (NFR-6)

**Given** the same address occurs more than once in the file, compared case-insensitively and trimmed
**When** the rows are evaluated
**Then** the first occurrence is valid and each later one is listed as invalid with a duplicate reason that names the first row (FR-7)

**Given** valid and invalid rows
**When** the page shows the result
**Then** the valid rows count as accepted, the primary button reads «Send 246 Invitasjoner» with the number of valid addresses, and the line «Ugyldige rader får ingen e-post før de er rettet.» stands beside the list (FR-7, UX-DR47)
**And** each invalid row carries the link «Registrer manuelt», which Story 4.8 gives its form

**Given** the Lecturer follows «Lim inn adresser i stedet»
**When** they paste text into the multi-line Tekstfelt and continue
**Then** the text is split on line breaks, commas, semicolons and whitespace, staged in the same `identity` tables as one-column rows, and evaluated by the same validation function with the same invalid-row list (FR-7)
**And** addresses pasted in the form `Navn <adresse>` are read as the address

**Given** every row is invalid or the paste is empty
**When** the result shows
**Then** the primary button is disabled, not shown as secondary, and the page says that there is no valid address to invite (UX-DR9)

**Given** the invalid-row list at narrow widths
**When** tested
**Then** the list reflows to 320 px with row number, value and reason stacked, long values wrap rather than clip, and Playwright with axe passes at 320 px, 200 % text and 1440 px (UX-DR47, NFR-6)
**And** api tests cover each reason, duplicates inside the file and the paste formats; duplicates against the Roster are checked in Story 4.4, which creates the Roster table

**Covers:** FR-7, NFR-6, AD-14, UX-DR9, UX-DR47

### Story 4.4: Send Invitations to the Roster with a validity period

As a Lecturer,
I want to send Invitations to every unregistered address on the Roster and choose how long they are valid,
So that my Students can register in good time before the games start.

**Acceptance Criteria:**

**Given** a staged upload with valid rows
**When** the Lecturer presses «Send 246 Invitasjoner»
**Then** one command in `classes.service` writes the valid addresses to the Roster through `identity.service`, in a `roster_entries` table created here and owned by `identity` (Class id, email, optional `user_id`, `registration`, `removed_at`), deletes the staged upload, and creates one Invitation per unregistered address, all in one transaction (FR-7, FR-8, AD-14)
**And** from this story «Klassene dine» on the Lærerhjem of Story 4.1 also shows the number of Roster addresses per Class (UX-DR56)
**And** the `invitations` table from Epic 3 is extended with a Class reference, a Roster entry reference and the kind `student`, in an expand-only migration (AD-24)

**Given** the send form
**When** it is shown
**Then** the validity period is prefilled with 14 days and can be changed for this sending, in whole days within a stated range, with an out-of-range value rejected inline with the range shown (FR-8)

**Given** the Invitations are created
**When** the transaction commits
**Then** each is enqueued through `platform/notify` as the `immediate` kind `invitation` with a `dedupe_key` per Invitation, addressed by reference (the form of Story 3.5: `user_id` empty and `ref` the Invitation id, resolved through `identity.service`, with no `user:<id>` emit, because the address has no User yet), and the `mail` job sends a Norwegian mail headed «ØL-spillet» that names the Class and the last valid day (AD-9, FR-72)
**And** job arguments and log lines hold ids only (AD-14)

**Given** a Class of 400 addresses
**When** the Lecturer sends
**Then** the request returns as soon as the rows are committed, the mails go out from `worker-batch` within the provider's rate limit, and the page shows the result line with the number of Invitations sent (NFR-3)

**Given** the Lecturer presses the button twice or the request is repeated
**When** the second call arrives
**Then** no address gets a second Invitation or a second mail, because the command is idempotent on the Roster entry and the `dedupe_key` (AD-9)

**Given** a staged row whose address is already on the Class's Roster, compared case-insensitively and trimmed
**When** the staged rows are evaluated or Invitations are sent
**Then** the row is listed with a reason that says so and is not added twice (FR-7)
**And** an address that already belongs to a registered Student of the Class gets no Invitation, and the count on the button and in the result excludes it (FR-8)

**Given** a User who is an Assistant lecturer of the Class or not staff at all
**When** they call the send endpoint
**Then** the `platform/authz` policy allows it only for Lecturers who own the Class (AD-12)
**And** api tests cover the transaction, the idempotency, the validity range and duplicates against the Roster, and Playwright covers the send flow at 320 and 1440 px (NFR-6)

**Covers:** FR-7, FR-8, FR-72, NFR-3, NFR-6, AD-9, AD-12, AD-14, AD-24, UX-DR47, UX-DR56

### Story 4.5: Register as a Student through the Invitation

As a Student,
I want to follow my Invitation, set a password and my name, and be in my Class,
So that I am ready when the games start.

**Acceptance Criteria:**

**Given** a valid Student Invitation link
**When** the Student opens it
**Then** «Du er invitert» from Epic 3 is reused and shows the e-mail prefilled and not editable, the Class name, and «Invitasjonen er gyldig i 14 dager. Du får Rolle og spill når Faglærer har bekreftet fordelingen.» with the real number of days left (FR-4, FR-8)

**Given** the Student submits a valid name and password
**When** the acceptance is handled
**Then** one transaction creates the User, links the Roster entry to the `user_id`, sets its `registration` to registered, marks the token used and logs the Student in (FR-8)
**And** `user:<id>` is emitted, and the Student lands on Hjem, which names the Class and repeats that Rolle and spill come when Faglærer has confirmed the allocation

**Given** the Invitation's e-mail already has a User, for example a Student of another Class
**When** that person opens the link and logs in
**Then** the same account becomes a Student in this Class as well, and no second User is created (FR-4)

**Given** an expired or used Student Invitation link
**When** a person opens it
**Then** the expired-link state from Epic 3 shows, and its action to ask for a new Invitation sets `renewal_requested_at` on the Invitation (Story 3.8), which the registration status reads through the Invitation's Roster entry reference, so the Lecturer sees the request (FR-1, FR-9)

**Given** a registered Student
**When** they request data
**Then** `platform/authz` gives them only their own Classes, through a scoped helper added here, and the address of another Class gives the permission-denied state (FR-5, AD-12)

**Given** a Student whose address was removed from the Roster
**When** they open the Class
**Then** they have no access to it, and their account and any other Class stay as they were (FR-7)

**Given** the registration flow on a phone
**When** tested
**Then** Playwright with axe passes at 320 and 360 px with the numeric and text keyboards as the fields ask for, tap targets of at least 44 px, and at 1440 px (NFR-6)
**And** acceptance attempts are rate-limited through `platform/ratelimit` as in Epic 3 (AD-11)
**And** the local seed of Story 4.1 now adds 8 registered demo Students to the demo Class, each with a Roster entry linked to its User, in `APP_ENV=local` only (AD-17)

**Covers:** FR-1, FR-4, FR-5, FR-7, FR-8, FR-9, NFR-6, AD-8, AD-11, AD-12, AD-17

### Story 4.6: See bounced Invitations and the counts

As a Lecturer,
I want to see how many Invitations were sent, bounced, accepted and expired,
So that I know which Students the mail never reached.

**Acceptance Criteria:**

**Given** Resend reports a delivery or bounce event
**When** it posts to `/api/webhooks/resend`
**Then** the route verifies the signature with `RESEND_WEBHOOK_SECRET` and rejects an unsigned or wrongly signed request; it is the one mutating route exempt from the `X-Requested-With` header (AD-11, NFR-10)
**And** the handler finds the row in `mail_deliveries` that Story 3.5 wrote for that mail, by the provider's message id, and stores the event on it; this story adds to that table, owned by `messaging`, the columns for delivery state, bounce class and last event id, and does not create the table
**And** the handler is idempotent on the provider's event id

**Given** a bounce for a Student Invitation
**When** the event is stored
**Then** the Roster entry shows the bounce with its reason class (hard or soft) in the registration status, in text (NFR-10)
**And** `messaging` exposes the delivery state through its `service.py`, and `classes` reads it there and never from the table

**Given** Invitations have been sent for a Class
**When** the Lecturer opens the Class
**Then** the page shows the counts of sent, bounced, accepted and expired Invitations (FR-8)
**And** sent and bounced are counted from the delivery rows, accepted from the Invitations accepted in Story 4.5, and expired from `expires_at` at read time; the four counts are computed in the api, not in the browser (AD-10)

**Given** the local and CI environments without a Resend key
**When** mails are sent
**Then** the mock sender records deliveries, and a test helper posts signed bounce events so the flow is tested without the provider (AD-17)

**Given** a webhook event for a mail the system does not know
**When** it arrives with a valid signature
**Then** it is acknowledged and ignored, and a log line records the event type with no address in it (AD-14)

**Given** the counts and the bounce marks
**When** tested
**Then** api tests cover the signature check, the idempotency and each count, and Playwright with axe passes the Class page at 320 and 1440 px (NFR-6)

**Covers:** FR-8, NFR-6, NFR-10, AD-10, AD-11, AD-14, AD-17

### Story 4.7: Follow registration status and send reminders

As a Lecturer,
I want to see each address's status and resend Invitations with a new validity period,
So that the Students who have not registered get another chance before allocation.

**Acceptance Criteria:**

**Given** a Class whose Invitations have been sent
**When** the Lecturer opens «Status etter utsending»
**Then** it shows the totals as text, for example «Registrert 238», «Manuelt 2» and «Uregistrert 10» with the real numbers, and the link «Send påminnelse til 10» with the number of addresses that have not registered (FR-9, UX-DR47)

**Given** the Roster list under the totals
**When** it renders
**Then** each address shows its status: invited (with the last valid day), registered, registered manually, unregistered after expiry, bounced, or asked for a new Invitation, each as text (FR-9)
**And** the list can be filtered by status and searched by address, and reflows to 320 px

**Given** an Invitation whose validity period has passed without acceptance
**When** the status is read
**Then** the address is unregistered, and `classes.service.registered_students(class_id)` leaves it out, so the allocation in Epic 5 does not place it in a Class game (FR-9)

**Given** the Lecturer follows «Send påminnelse til 10»
**When** they confirm the sending with a validity period, prefilled with 14 days
**Then** each unregistered or still invited address gets a new Invitation with the new expiry, its old token is void, and the mail goes out as the `immediate` kind `invitation` (FR-9, AD-9)
**And** the result line states how many reminders were sent, and registered addresses get nothing

**Given** one address in the list
**When** the Lecturer resends its Invitation alone
**Then** the same command runs for that one address with the chosen validity period (FR-9)

**Given** an address whose last Invitation bounced hard
**When** a reminder is sent to all
**Then** that address is left out and named in the result, so the Lecturer can correct it or register the Student manually (NFR-10)

**Given** the page
**When** tested
**Then** api tests cover each status and the expiry boundary with a frozen clock, and Playwright with axe passes at 320 px, 200 % text and 1440 px (NFR-6)

**Covers:** FR-8, FR-9, NFR-6, NFR-10, AD-9, UX-DR47

### Story 4.8: Register a Student manually and change single addresses

As a Lecturer,
I want to register a Student by hand and add or remove single addresses,
So that a wrong address or a late Student does not keep anyone out.

**Acceptance Criteria:**

**Given** an invalid row or an unregistered address
**When** the Lecturer follows «Registrer manuelt»
**Then** an in-place form opens with the address prefilled where one exists, a field for the Student's name, and one primary button labelled with its effect; focus moves to the first field and «Avbryt» returns focus to the link (UX-DR47)

**Given** the Lecturer submits a valid address and name
**When** the registration commits
**Then** the address is on the Roster with `registration` registered manually, a User exists for it (created without a password, or the existing User for that address), and the Student is in the Class at once (FR-9)
**And** the Student gets a mail with a single-use link to set a password, sent as an `immediate` kind, valid for a configured period (`MANUAL_REGISTRATION_LINK_DAYS`, placeholder 14), and setting the password reuses «Nytt passord» from Epic 3

**Given** the Class page
**When** the Lecturer adds a single address
**Then** it is validated by the same function as an upload and added to the Roster with the status not yet invited, which this story adds as text to the status list and the filter of Story 4.7 (FR-7)
**And** a not yet invited address is counted in «Send påminnelse til 10» and gets its first Invitation from that sending, or alone from the single-address action of Story 4.7, with the chosen validity period (FR-8)
**And** a duplicate of an address already on the Roster is rejected with the reason beside the field

**Given** an address on the Roster
**When** the Lecturer removes it
**Then** the button states the consequence before it is pressed, the Roster entry is marked removed, its open Invitation is void, and a registered Student loses access to the Class from their next request (FR-7)
**And** `user:<id>` is emitted for a removed Student, and the Student's account and other Classes are untouched (AD-8)
**And** `classes.service.registered_students(class_id)` leaves a removed Student out, which is what Epic 5 reads to keep a removed Student out of the Class games

**Given** a removed address is added again
**When** the Lecturer saves
**Then** the Roster entry is active again and a registered Student has access again without a new registration

**Given** these actions change who is in a Class
**When** each commits
**Then** only Lecturers who own the Class pass the policy, and an Assistant lecturer sees the Roster but none of these actions (AD-12, FR-5)
**And** api tests cover the new-User and existing-User cases, the removal and the re-add, and Playwright with axe passes the forms at 320 and 1440 px (NFR-6)

**Covers:** FR-5, FR-7, FR-8, FR-9, NFR-6, AD-8, AD-9, AD-12, AD-14, UX-DR47

### Story 4.9: Share a Class with co-owner Lecturers and Assistant lecturers

As a Lecturer,
I want to add other Lecturers as co-owners and invite Assistant lecturers for this Class only,
So that we can run the Class together.

**Acceptance Criteria:**

**Given** a Class the Lecturer owns
**When** they open «Faglærere og assistenter»
**Then** the page lists Faglærere (co-owners) and Assistenter for this Class, each with a status in text (active, or invited with the last valid day) (FR-10, UX-DR56)

**Given** the Lecturer uses «Legg til Faglærer» with the e-mail of an existing User who has the Lecturer role
**When** they submit
**Then** that User becomes co-owner in `class_staff` with the same rights as the owner, an audit row is written, and `user:<id>` is emitted so the Class appears on their Lærerhjem (FR-10, AD-8, AD-15)
**And** an address that has no account or lacks the Lecturer role is rejected with a reason that tells the Lecturer to ask the Admin for the role, without listing any account details

**Given** the Lecturer uses «Inviter Assistent» with an e-mail
**When** they submit
**Then** an Invitation of kind `assistant` for this Class is created and mailed as an `immediate` kind, addressed by Invitation id as in Story 4.4, and the page shows «Assistenten får tilgang bare til denne Klassen.» (FR-10, UX-DR56)
**And** accepting it through «Du er invitert» creates the account or uses the existing one and adds the person to `class_staff` as Assistant lecturer for this Class only
**And** this story adds an acceptance-handler registry to `identity.service`, shaped like the revoke-blocker registry of Story 3.9: `classes.service` registers the handler for the kind `assistant`, `identity` calls it inside the acceptance transaction, and `identity` imports no `classes` code, proven by the import check

**Given** an Assistant lecturer of the Class
**When** they log in
**Then** they land on the Lærerhjem and see only the Classes they are attached to, through `classes_visible_to(user)` (FR-5, AD-12)
**And** creating, archiving or deleting a Class, changing the Roster, sending Invitations and managing staff are not shown to them and are rejected by policy if called

**Given** a co-owner or an Assistant lecturer in the list
**When** a Lecturer who owns the Class removes them
**Then** their access ends from their next request, with an audit row and `user:<id>` emitted
**And** removing the last owner of a Class is rejected with a reason, so a Class always has a Lecturer

**Given** the staff list and both forms
**When** tested
**Then** api tests cover co-owner rights, Assistant scope across two Classes and the last-owner rule, and Playwright with axe passes at 320 px, 200 % text and 1440 px (NFR-6)

**Covers:** FR-5, FR-10, NFR-6, AD-8, AD-9, AD-12, AD-15, UX-DR56

### Story 4.10: Archive a Class

As a Lecturer,
I want to archive a Class I no longer teach,
So that it is out of my way but kept for statistics.

**Acceptance Criteria:**

**Given** a Class the Lecturer owns
**When** they look at the archive action
**Then** the button states the consequence above it: the Class becomes read-only and is kept until the retention period ends (FR-6)

**Given** the Lecturer presses it
**When** the action commits
**Then** the Class gets `archived_at`, an audit row is written and `user:<id>` is emitted for its staff (FR-6, AD-8, AD-15)

**Given** an archived Class
**When** any staff member opens it
**Then** its pages are read-only: no Roster change, no Invitation, no staff change, and every mutating call on it is rejected with the stable code `class_archived` by one check in `classes.service` (FR-6)
**And** `classes.service.is_writable(class_id)` is exposed so later epics refuse changes to its Class sessions the same way

**Given** the Lærerhjem
**When** a Lecturer has archived Classes
**Then** «Klassene dine» lists active Classes first and archived ones under their own heading, marked as archived in text (UX-DR56)

**Given** an archived Class with open Invitations
**When** a person follows one
**Then** the expired-link state shows and no one is registered into the Class

**Given** a Lecturer whose only owned Classes are archived
**When** the Admin revokes their Lecturer role
**Then** the revoke-blocker counts no active Class and the revoke goes through (FR-2)
**And** api tests cover the read-only rule on every mutating `classes` route, and Playwright with axe passes the archived Class page and the Lærerhjem at 320 and 1440 px (NFR-6)

**Covers:** FR-2, FR-6, NFR-6, AD-8, AD-12, AD-15, UX-DR56

## Epic 5: Class session setup and allocation

A Lecturer can create a Class session that is ready to save with the Classic defaults, change any Game setting, choose AI mode, Effort level and Debrief mode, mark the session obligatory, set the Inactivity limit, the four dates and Lab hours, and allocate the registered Students to Class games. At the Start date the sweeper locks the Class session and opens its Class games on one frozen snapshot. The epic owns `api/app/modules/sessions/` and `web/src/modules/sessions/`, adds its due actions to the per-minute `ops.sweep` that Story 3.5 created, and adds the `class` row to `games.policy`. It puts the Klasseøkt screen on top of the engine's `GameSettings` from Epic 1 and computes nothing in the web app.

### Story 5.1: Create a Class session with the Classic defaults

As a Lecturer,
I want to create a Class session that is already filled in with the Classic defaults,
So that I can save it unchanged and be ready in a few minutes.

**Acceptance Criteria:**

**Given** a Lecturer who owns or co-owns a Class
**When** the Lecturer creates a Class session from the Klasse page
**Then** `sessions.service.create` stores one `class_sessions` row with the Class id, the engine's Classic `GameSettings` as JSONB with `schema_version` (inventory 12, 4 per supply-line slot, delays 2/2/2, demand 4 stepping to 8 in Week 5, costs 0.50 and 1.00, 36 Weeks, Guided Weeks 1 to 4), AI mode LLM players, Debrief mode Group debrief, Inactivity limit 24 hours, not obligatory, a demand seed drawn by the server through `engine.demand.new_seed`, and the id of the active default model config read through `ai.config` (outside production this is the mock config that Story 2.12 seeds) (FR-11, FR-13, AD-4, AD-6)
**And** in the same transaction the Class session's budget row is created through `ai.budget`, so every later LLM call for it has a model config and a budget (AD-6)
**And** the default values come from the engine's Classic preset; neither `sessions` nor the web app holds a second copy of them (AD-1, AD-10)
**And** the story creates only the `class_sessions` table, owned by `modules/sessions`, with a UUIDv7 id
**And** `sessions.service` has one guard that asks `classes.service.is_writable(class_id)` of Story 4.10 before create and before every later mutation of a Class session, and answers the stable code `class_archived` for an archived Class, shown by an api test (FR-6)

**Given** a production deployment in which no model config is pinned as the default
**When** a Lecturer creates a Class session
**Then** the Class session is created without a model config and without a budget row, its AI mode is stored as Rule-based players, and the API returns a flag with the reason, so the screen can say that LLM players are unavailable until the Admin has pinned a model (copy to be written in `nb.ts`) (FR-15, AD-6, AD-17)
**And** when the Lecturer later saves the Class session with LLM players and a default then exists, `sessions.service` attaches that config and creates the budget row in the same transaction; until then that choice is refused with a stable code

**Given** the new Class session
**When** the Klasseøkt screen opens
**Then** it shows the page title «Klasseøkt for {klassenavn}», «Alt er fylt ut med standardene.», «Spillinnstillinger: Klassisk» and «Kildene er uenige om forsinkelsene. Dette er produktets standard, og du kan endre den.» (UX-DR48)
**And** «Kjeden ved start» draws the four Roles with upstream on the left, the delay boxes on the pipe and Lager 12 per Role, captioned «Varer mot høyre, ordre mot venstre», from values the API returned, with the same values as text for screen readers; it is a diagram of this slice, built in `web/src/modules/sessions/` without a chart library, and not a data chart of the AD-18 chart module (UX-DR48, AD-10)
**And** «Lagre Klasseøkt» is the screen's one primary button

**Given** the Lecturer has changed nothing
**When** the Lecturer presses «Lagre Klasseøkt»
**Then** the Class session is saved as it stands, the mutation emits `session:<id>` through `platform/events.emit` with its entry in the registry, and the Klasse page lists the Class session (FR-11, AD-8)
**And** a Playwright flow from the Klasse page to a saved Class session passes without any field being edited, as the product part of the under-10-minutes target (FR-11)

**Given** an Assistant lecturer attached to the Class
**When** the Assistant lecturer opens the Klasse page
**Then** no action to create or delete a Class session is shown, and the create route answers with the permission-denied state from Epic 3 through its `platform/authz` policy, with no `if role ==` in the module (FR-5, AD-12)

**Given** a save that fails on the server or while offline
**When** the Lecturer presses «Lagre Klasseøkt»
**Then** the inline «Det ble ikke lagret. Prøv igjen.» is announced with `role="alert"`, focus stays on the button and the entered values are kept (reusing the all-surface states from Epic 3)

**Given** the Klasseøkt screen
**When** it is tested with Playwright at 320, 360 and 1440 px and at 400% zoom
**Then** it is one column below 1024 px, has no page-level horizontal scroll, passes axe, and all its copy comes from `web/src/copy/nb.ts` and passes the copy check (NFR-6, AD-19)

**Covers:** FR-6, FR-11, FR-13, FR-15, FR-72, NFR-6, AD-1, AD-4, AD-6, AD-8, AD-10, AD-12, AD-17, AD-19, UX-DR48

### Story 5.2: Set the four dates on the Datolinje

As a Lecturer,
I want to set the Start date and the three deadlines and see them on one line,
So that my Students and I know when each part must be done.

**Acceptance Criteria:**

**Given** a Class session
**When** the Lecturer enters Startdato, Spillfrist, Debrieffrist and Testfrist
**Then** each is a labelled date and time field, stored as `timestamptz` in UTC and shown in Europe/Oslo (FR-18)
**And** the Testfrist is prefilled 7 days after the Debrieffrist when that is set, and the Lecturer can change it (FR-18)

**Given** dates that are not in the order Start date, Play deadline, Debrief deadline, Test deadline, or a new date in the past
**When** the Lecturer saves
**Then** the API rejects them with a stable code naming the fields, and the screen shows the reason inline beside the field that breaks the order (FR-18)

**Given** saved dates
**When** the Datolinje renders
**Then** it is a read-only timeline with one labelled tick per date, built as hand-made SVG in `web/src/modules/sessions/` with no chart library, and its text alternative is the labelled date fields themselves; it is a diagram of this slice that never goes into a report, not a data chart of the AD-18 chart module (UX-DR51, NFR-6)
**And** below 1024 px and at 320 px the Datolinje scrolls inside its own region while the date fields reflow in one column (UX-DR75)

**Given** a Class session that has started
**When** the Lecturer moves a deadline that has not yet passed
**Then** the change is saved as an extension for the whole Class session, keeps the order rule, and emits `session:<id>` and `user:<id>` once per affected Student (FR-18, AD-8)
**And** the Start date cannot be changed once it has passed, and a deadline that has passed answers `409 deadline_passed`
**And** `sessions.service.is_locked(class_session)` is added here as the one predicate for the Start-date lock points of FR-18: it is true once the Start date has passed, and every settings route of this epic asks it and answers `409 session_locked` when it is true
**And** per-Student extensions are not part of this story (Epic 11 moves one Student's Debrief and Test deadlines)

**Given** a date plan and a number of Weeks
**When** the configured minimum playing time per Week is set
**Then** the screen warns without blocking when the time between Start date and Play deadline is too short; the value is configuration, unset until SM-11 is known, and while unset no warning is shown (FR-18)

**Given** a Student of the Class
**When** the Student-scoped read `GET /api/me/class-sessions` is called
**Then** `sessions.service` returns, through a `platform/authz` scope helper, the Student's Class sessions with the dates and the next deadline that applies, and never the Game settings, the number of Weeks or the demand series (FR-18, AD-3, AD-12)
**And** this read is what Epic 6's Hjem shows as «Neste frist»
**And** `sessions.service.effective_test_deadline(user, class_session)` and `sessions.service.effective_debrief_deadline(user, class_session)` are created here as the only way another module reads a Student's deadline; both return the Class session's deadline for now, and Epic 11 adds the per-Student extension inside them without changing callers

**Given** a Lecturer or Assistant lecturer with at least one Class session
**When** the Lærerhjem from Epic 4 opens
**Then** its «what is waiting» and «next deadline» parts, left empty by Epic 4, are filled from `sessions.service`: per Class the Class sessions that still lack dates, and the next date across the User's Class sessions with its name and time in Europe/Oslo, scoped through `platform/authz` (UX-DR56, AD-12)
**And** the parts are fetched when the Lærerhjem opens and stay empty, without an error, when the User has no Class session; this epic only emits `session:<id>` and `user:<id>`, and refetching on them without a reload comes with the topic map of Story 6.4

**Covers:** FR-18, NFR-6, AD-3, AD-8, AD-12, UX-DR51, UX-DR56, UX-DR75

### Story 5.3: Change Game settings with range errors and warnings

As a Lecturer,
I want to change any Game setting and be told at once what is out of range or unusual,
So that I can run the game my way without breaking it.

**Acceptance Criteria:**

**Given** a Class session before its Start date
**When** the Lecturer opens the settings block
**Then** the Lecturer can edit starting inventory or backlog per Role, the contents of each supply-line slot, order delay, shipping delay and Factory production delay, holding cost and backorder cost, number of Weeks, Guided Weeks and the maximum Order, each in a Tekstfelt with its label above (FR-12, UX-DR48)
**And** cost rates are entered and shown with a decimal comma and travel as decimal strings; this story adds the one Norwegian number formatter to `web/src/lib/` for reuse (space as thousands separator, decimal comma, true minus sign), with Vitest cases, and Epic 6 reuses it (UX-DR5 stays Epic 6's to complete on the play screen)

**Given** an edited setting
**When** the Lecturer leaves the field or presses «Lagre Klasseøkt»
**Then** the API validates the whole `GameSettings` with the engine's validation from Epic 1 and returns stable error codes with the allowed range in `fields`; the web app only maps them to copy and mirrors no rule the server does not own (AD-1, AD-10, AD-19)
**And** an out-of-range value (for example a delay outside 1 to 3 Weeks) is shown inline under the setting with a `restordre` border and the allowed range, and blocks saving (FR-12, UX-DR48)
**And** Guided Weeks that are not fewer than the Week of the first demand change, or that leave too few Weeks to play, are rejected the same way (FR-12)

**Given** settings that are valid but match a listed combination
**When** the API returns the engine's warnings
**Then** each warning shows inline under its setting and does not block saving: supply-line contents that differ from starting demand, backorder cost not above holding cost, too few Weeks for a demand change to pass through the chain at the chosen delays, and a low maximum Order (FR-12)
**And** warnings are text, never colour alone (NFR-6)

**Given** any setting that differs from the Classic preset
**When** the screen renders
**Then** «Alt er fylt ut med standardene.» is no longer shown, a line states which settings the product's content and Play guard were calibrated for, and «Kjeden ved start» redraws from the values the API returned (FR-12, UX-DR48)

**Given** a Class session that `sessions.service.is_locked` of Story 5.2 reports as locked
**When** anyone opens the settings block or calls the settings route
**Then** every Game setting is read-only on the screen and the route answers `409 session_locked` (FR-12, FR-18, AD-4)

**Given** the settings block
**When** tests run
**Then** api tests cover each range error and each warning through the route, and Playwright with axe covers the error and warning states at 320, 360 and 1440 px

**Covers:** FR-12, FR-18, NFR-6, AD-1, AD-4, AD-10, AD-19, UX-DR48

### Story 5.4: Choose a Demand pattern and its seed

As a Lecturer,
I want to choose the customer demand every Class game will face,
So that all groups meet the same series and I can repeat it later.

**Acceptance Criteria:**

**Given** a Class session before its Start date
**When** the Lecturer opens the Demand pattern block
**Then** the Lecturer can choose a fixed series, a step (start level, new level, Week of change), random demand (mean and spread, discrete uniform, never below 0), or a step with random noise around it (FR-13)
**And** the choice is stored in the Class session's `GameSettings`; the web app holds no demand logic (AD-1, AD-10)

**Given** a Demand pattern that uses randomness
**When** the block renders
**Then** the seed is shown, is the one the server drew when the Class session was created (Story 5.1), and the Lecturer can keep it or enter another whole number (FR-13)
**And** the same settings and seed always give the same series, shown by an api test that materialises it twice through the engine

**Given** a saved Demand pattern
**When** the Lecturer asks to see the series
**Then** the API returns the series materialised by the engine's demand function from Epic 1, and the screen shows it as an HTML table of Week and demand for the Lecturer only (FR-13, AD-1)
**And** no Student-facing endpoint of this epic returns the series, the seed or the number of Weeks (AD-3)

**Given** an invalid pattern
**When** the Lecturer saves
**Then** a fixed series whose length differs from the number of Weeks, a negative level, a step Week outside the game, or a first demand change at or before the last Guided Week is rejected inline with the allowed range, from the engine's validation (FR-12, FR-13)

**Given** a Class session that `sessions.service.is_locked` of Story 5.2 reports as locked
**When** anyone tries to change the Demand pattern or the seed
**Then** both are read-only on the screen and the route answers `409 session_locked` (FR-12, FR-18)

**Covers:** FR-13, FR-12, FR-18, AD-1, AD-3, AD-10, UX-DR48

### Story 5.5: Choose AI mode, Effort level and Debrief mode

As a Lecturer,
I want to choose what kind of AI players my Students meet and how the Debrief is held,
So that the Class session fits my course and my view on AI.

**Acceptance Criteria:**

**Given** the Klasseøkt screen
**When** it renders the choices
**Then** Valgknapper (one segment per option, the active one filled `ink` with `paper` text, inactive ones with an `ink-muted` border) and the two-segment Visningsbryter variant are added to `web/src/components/` for reuse, with the shared interaction states and focus ring from Epic 3, full keyboard operation and 44 px tap targets (UX-DR12)
**And** a choice takes effect only when «Lagre Klasseøkt» is pressed (UX-DR12)

**Given** a Class session before its Start date
**When** the Lecturer sets AI mode
**Then** the options are «LLM-spillere» (default) and regelbaserte KI-spillere, with the help text «Gjelder alle KI-spillere i Klassespill og Replay.» under the control (FR-15, UX-DR12, UX-DR48)
**And** each option carries the plain-language description of that AI player type from `players.service.describe(kind)`; `sessions` writes no description of its own (FR-33)
**And** where the Class session has no model config (the production case of Story 5.1), «LLM-spillere» is shown as unavailable with `aria-disabled` and the reason beside it, regelbaserte KI-spillere is the selected option, and «LLM-spillere» becomes available once a default model config exists (FR-15, AD-17)

**Given** AI mode is «LLM-spillere»
**When** the «Innsatsnivå» block renders
**Then** it offers as Valgknapper only the Effort levels that the Class session's model config marks as supported and measured inside the cost and time limits, read through `ai.config.offered_effort_levels(config_id)`, each with one line on its effect on speed and cost, and the config's default level is preselected (FR-78, UX-DR49)
**And** the levels, their default and their effect lines are data in the model config, placeholders until the prototype sets them (issues #8, #9); no level is hard-coded in `sessions` or the web app

**Given** the Lecturer chooses regelbaserte KI-spillere
**When** the screen updates
**Then** the «Innsatsnivå» block is hidden and no Effort level is stored as in force for the Class session (FR-78, UX-DR49)

**Given** a Class session before its Start date
**When** the Lecturer sets Debrief mode
**Then** the options are «Gruppedebrief» (default) and the Personal debrief, and the choice is stored on the Class session (FR-16, UX-DR48)

**Given** a production deployment where the pinned provider has no key and AI mode is «LLM-spillere»
**When** the Klasseøkt screen renders
**Then** it states that the Class session cannot open with LLM players until the provider is set up, from a flag the API returns, so the Lecturer learns it before the Start date and not at the lock (AD-17)

**Given** a Class session that `sessions.service.is_locked` of Story 5.2 reports as locked
**When** anyone tries to change AI mode, Effort level or Debrief mode
**Then** the controls are read-only and the route answers `409 session_locked` (FR-18)

**Covers:** FR-15, FR-16, FR-33, FR-78, FR-18, AD-6, AD-10, AD-17, UX-DR12, UX-DR48, UX-DR49

### Story 5.6: Add Lab hours

As a Lecturer,
I want to add Lab hours with date, time and place,
So that Students know when staff are present and can plan to play then.

**Acceptance Criteria:**

**Given** a Class session
**When** the Lecturer presses the link «Legg til Labtime»
**Then** an in-place form takes date, start and end time and place, and the saved Lab hour is stored in a `lab_hours` table owned by `modules/sessions`, as many as needed (FR-19)
**And** a Lab hour with an end before its start, or without a place, is rejected inline with the reason

**Given** saved Lab hours
**When** the Datolinje renders
**Then** each Lab hour is a `lager` square on the line with the legend «Blå firkant: Labtime, {sted}.», and the list of Labtimer under it is the text alternative, so the square is never the only carrier (UX-DR51, NFR-6)

**Given** a Lab hour is added
**When** the transaction commits
**Then** `platform/notify.enqueue` is called once per registered Student with the Lab hour notice kind and a dedupe key on the Lab hour, which this story registers as a `digest` kind with its Jinja2 template in the digest delivery of Story 3.5: at most one mail per User per day and none between 22:00 and 07:00 Europe/Oslo; this epic's other notices (obligatory, allocation, deadline reminder) register their kinds the same way and build no delivery of their own (FR-19, AD-9)
**And** the mutation emits `session:<id>` and `user:<id>` per Student, and the notice rows hold ids only (AD-8, AD-14)

**Given** an existing Lab hour
**When** the Lecturer edits or removes it, at any time before or after the Start date
**Then** the change is saved, the Datolinje and list update, and Students are notified of a changed or cancelled Lab hour through the same path (FR-18, FR-19)

**Given** a Student of the Class
**When** `GET /api/me/class-sessions` is called
**Then** it also returns the upcoming Lab hours with date, time and place, for Epic 6's Hjem (FR-19)

**Given** another module that needs to know whether a Lab hour is on
**When** it calls `sessions.service.current_lab_hour(class_session_id, now)`
**Then** it gets the Lab hour in progress or none, so Epic 8's «I rommet» does not read the table itself

**Covers:** FR-19, FR-18, NFR-6, AD-8, AD-9, AD-14, UX-DR51

### Story 5.7: Mark the Class session obligatory and set the Inactivity limit

As a Lecturer,
I want to mark the Class session as a course requirement and set how long a group waits before an AI player takes over,
So that Students know it counts and no group is held up longer than I accept.

**Acceptance Criteria:**

**Given** the Klasseøkt screen
**When** it renders the «Obligatorisk» setting
**Then** a Bryter (on in `ink`, `rounded.full`, with a text label beside it) is added to `web/src/components/` for reuse, operable by keyboard with its state exposed to screen readers and never by colour alone (UX-DR12, NFR-6)
**And** in the Klasseøkt the Bryter follows the Valgknapper rules: it takes effect on «Lagre Klasseøkt» (UX-DR12)

**Given** a Class session before its Start date
**When** the Lecturer switches «Obligatorisk» on
**Then** the label reads «Ja, står i emneplanen», which is the Lecturer's confirmation that the course plan states the requirement, and no second dialog follows (FR-17, UX-DR48, UX-DR78)

**Given** the obligatory mark is saved as on
**When** the transaction commits
**Then** `platform/notify.enqueue` is called once per registered Student with the obligatory notice kind (a `digest` kind, registered in the digest delivery of Story 3.5), and `user:<id>` is emitted (FR-17, AD-9, AD-8)
**And** `GET /api/me/class-sessions` returns the obligatory flag, so Epic 6's Hjem and the deadline reminders can state it
**And** the Completion rules and everything else in FR-17 are not built here (Epic 13)

**Given** «Obligatorisk» is switched on, before the Start date
**When** the Lecturer edits the required share of Weeks (draft copy, not in the spine: «Andel uker som kreves»)
**Then** the field takes a whole percent from 1 to 100, with the default from configuration (`COMPLETION_DEFAULT_SHARE_PERCENT`, placeholder 80 from FR-17's assumption), and an out-of-range value is rejected inline with the range shown (FR-17)
**And** the share is stored on the Class session together with the obligatory mark and exposed as `sessions.service.required_share(class_session)`, the one source that Story 8.9 and Epic 13 read; nothing in this epic computes Completion with it (AD-16)

**Given** a Class session before its Start date
**When** the Lecturer edits «Ventetid før KI tar over»
**Then** the field takes whole hours, default 24, with the always-visible help line «Minst 20 timer. Kortere ventetid kan bare gjelde spill som er i rommet i en Labtime.» (FR-36, UX-DR49)
**And** a value under 20, a decimal or an empty value shows «Skriv et helt antall timer, 20 eller mer.» with `role="alert"` on leaving the field or pressing the button, and the API enforces the same floor (FR-36, UX-DR49)

**Given** a Class session that `sessions.service.is_locked` of Story 5.2 reports as locked
**When** anyone tries to change the obligatory mark, the required share or the Inactivity limit
**Then** all three are read-only on the screen and the route answers `409 session_locked` (FR-17, FR-18)
**And** the Takeover behaviour that uses the limit is not built here (Epic 8)

**Covers:** FR-17, FR-18, FR-36, NFR-6, AD-8, AD-9, AD-16, UX-DR12, UX-DR48, UX-DR49, UX-DR78

### Story 5.8: Preview a random allocation and run it again

As a Lecturer,
I want to see how the registered Students would be split into Class games before anyone is told,
So that I can check the groups and draw again if I want.

**Acceptance Criteria:**

**Given** a Class session before its Start date with registered Students on the Roster
**When** the Lecturer opens the allocation block
**Then** `sessions.service` reads the registered Students through `classes.service`, draws a seed, and runs the pure function `sessions.allocation.allocate(student_ids, seed)`, which places every Student at random in groups of four with a random Role each (FR-20)
**And** when the count is not divisible by four exactly one group has one to three Students, shown by a unit test over counts 1 to 9 and 250, and the same ids and seed always give the same result
**And** invited or unregistered Roster addresses are never allocated (FR-9, FR-20)

**Given** the allocation has been drawn
**When** it is kept for the Lecturer
**Then** it is stored as the Class session's one current draft in an `allocation_drafts` table owned by `modules/sessions`: draft id, a `revision` that starts at 1, Class session id, seed, the assignments as `user_id`, game number and Role, and who drew it; it holds no names or emails (AD-14)
**And** this settles the deferred decision: the preview is a stored server-side draft, and the screen always renders the stored draft, never a recomputation

**Given** a stored draft
**When** the Fordelingsforhåndsvisning renders
**Then** it shows one column per Class game by four Role rows in `bar-base`, with Fabrikk at the top, under a heading of the form «Fordeling: 60 Klassespill à 4», and the line «Tomme seter får KI-spiller.»; it is plain SVG built in `web/src/modules/sessions/` without a chart library, a diagram of this slice and not a data chart of the AD-18 chart module (UX-DR50, UX-DR73)
**And** selecting a column frames it in `ink` and shows that game's four names in the form «Spill 17  Ida, Detaljist. Sara, Grossist. …», with an empty Seat named «KI-spiller»; columns are reachable by keyboard (UX-DR50)
**And** the Visningsbryter offers «Vis som liste»: every Klassespill with its four names as an HTML list, which is the chart's alternative (UX-DR50, NFR-6)

**Given** a stored draft
**When** the Lecturer presses the secondary button «Kjør fordeling på nytt»
**Then** a new seed is drawn, the draft is replaced under a new draft id, and the preview redraws; no Game or Seat exists yet and no Student is notified (FR-20, UX-DR9)

**Given** no registered Students
**When** the allocation block renders
**Then** it states that there is nobody to allocate yet and shows no draft and no confirm button

**Given** the preview at 320 px or with 100 Class games
**When** it is tested with Playwright and axe at 320, 360 and 1440 px
**Then** the chart scrolls inside its own region with a visible focus ring, the list view reflows without horizontal scroll, and names resolve at read time through an AD-12 scope helper (UX-DR75, AD-12)

**Covers:** FR-20, FR-9, NFR-6, AD-12, AD-14, UX-DR9, UX-DR12, UX-DR50, UX-DR73, UX-DR75

### Story 5.9: Confirm the allocation I am looking at

As a Lecturer,
I want to confirm exactly the allocation I am looking at,
So that the groups Students are told about are the ones I approved.

**Acceptance Criteria:**

**Given** a stored draft shown in the preview
**When** the Lecturer presses the primary button «Bekreft fordeling», with «Ingen får beskjed før du bekrefter.» beside it
**Then** the request carries the draft id and the draft `revision`, and `sessions.service.confirm_allocation` commits that draft and nothing else: one Class game per group through `games.commands.create` with `purpose=class`, the Class session id, a game number and **no** settings, and one Seat per Student through `games.commands.assign_seat` (FR-20, AD-2, AD-4)
**And** an api test asserts that the committed Games and Seats equal the stored draft, Student by Student

**Given** the game commands of Epic 1 and Epic 2
**When** this story extends them
**Then** `games.policy` gets a new column that says whether a Game takes its settings snapshot at creation or at the lock; for a purpose that takes it at the lock, `games.commands.create` validates no settings and stores no snapshot, its Seats stay free until they are assigned, and `games.commands.start` answers the stable code `409 game_not_ready` while the Game has no snapshot (AD-4, AD-13)
**And** the `class` row is added to `games.policy`: snapshot at the lock, and inactivity Takeover, Pause, Play deadline playout, Guided Weeks and Lecturer overview all apply (AD-13)
**And** `games.commands.assign_seat`, which so far takes `rule_based` and `scripted` occupants (Story 1.7) and `llm` occupants (Story 2.5), is extended with the `student` occupant kind, and the nullable `user_id` column it needs is added to the Seat occupancy table in `modules/games`; the row holds the id only, never a name (AD-5, AD-14)
**And** the `class_session_id` and `game_number` columns are added to `games` in `modules/games`, and `games.service.budget_scope(game)` of Story 2.5 now answers the Class session for a Game that has a `class_session_id`, so the LLM Orders of a Class game are charged to the budget row that Story 5.1 created (AD-6)

**Given** the draft id or the `revision` in the request is not the Class session's current one (a co-owner ran the allocation again or changed the draft in the meantime)
**When** confirm is called
**Then** it answers `409 allocation_changed`, commits nothing, and the screen shows the current draft for a new press, so nobody confirms groups they have not seen (FR-20)

**Given** a Student in the draft was removed from the Roster after the preview
**When** confirm is called
**Then** nothing is committed, the draft is updated to leave that Seat free with its `revision` raised, and the preview shows the change for a new press (FR-7, FR-20)

**Given** a confirmed allocation
**When** the transaction commits
**Then** each allocated Student gets `user:<id>` and an allocation notice through `platform/notify.enqueue` (a `digest` kind, registered in the digest delivery of Story 3.5), `session:<id>` is emitted, and every command's topics are in the registry and pass the registry test (AD-8, AD-9)
**And** confirm is idempotent: a second press creates no second set of Games, and «Kjør fordeling på nytt» is no longer offered

**Given** a Class session without a confirmed allocation
**When** a Lecturer or Assistant lecturer opens the Lærerhjem
**Then** the «what is waiting» part that Story 5.2 filled now also names the Class sessions that lack a confirmed allocation, and stops naming one when its allocation is confirmed (UX-DR56, AD-12)

**Given** a Class session that `sessions.service.is_locked` reports as locked
**When** anyone calls confirm
**Then** the route answers `409 session_locked` and the control is not shown (FR-20)

**Covers:** FR-20, FR-7, AD-2, AD-4, AD-5, AD-8, AD-9, AD-12, AD-13, AD-14, UX-DR9, UX-DR50, UX-DR56

### Story 5.10: Move or swap Students in the allocation

As a Lecturer,
I want to move a Student to a free Seat or swap two Students, before and after I confirm,
So that I can adjust single groups without drawing everything again.

**Acceptance Criteria:**

**Given** a draft that is not yet confirmed
**When** the Lecturer moves a Student to a free Seat or swaps two Students in the preview, from the selected game's names
**Then** the stored draft is edited under the same draft id and its `revision` goes up by one; the request carries the revision the Lecturer was looking at and answers `409 allocation_changed` when it is no longer current, so confirm in Story 5.9 still commits what is shown (FR-20)

**Given** a confirmed allocation before the Start date
**When** the Lecturer moves a Student to a free Seat or swaps two Students, from the selected game's names
**Then** the change runs through the command `games.commands.move_seat` of the AD-2 list, built in this story with its registry entry, in one transaction that locks the Games involved in id order and emits `game:<id>`, `session:<id>` and `user:<id>` for the Students involved, and the affected Students get the allocation notice of Story 5.9 (FR-20, AD-2, AD-8, AD-9)
**And** a Student holds at most one Seat per Class session, enforced by the command

**Given** the move and swap controls in the preview
**When** they are used by keyboard or on a narrow screen
**Then** each is a button labelled with its effect, naming the Student, the Role and the Klassespill (draft copy to be written in `nb.ts`), no drag is needed, focus returns to the changed row, and Playwright with axe passes at 320, 360 and 1440 px (UX-DR9, UX-DR50, NFR-6)

**Given** a Class session that `sessions.service.is_locked` reports as locked
**When** anyone calls move or swap
**Then** the route answers `409 session_locked` and the controls are not shown (FR-20)

**Covers:** FR-20, NFR-6, AD-2, AD-8, AD-9, UX-DR9, UX-DR50

### Story 5.11: Lock the Class session at the Start date

As a Lecturer,
I want the Class session to lock by itself at the Start date,
So that every group plays on the same settings and I do not have to be online.

**Acceptance Criteria:**

**Given** the per-minute `ops.sweep` that Story 3.5 created
**When** this story is done
**Then** `sessions.lock` is added to it as a due action: the sweep only finds the Class sessions whose Start date has passed and that are not locked, and calls `sessions.service.lock(class_session_id)`, one item per transaction, with id-only arguments (AD-9)
**And** the sweep also gets `identity.purge_expired_roster_uploads()` as a due action, so the expired Roster staging rows that Epic 4 purges lazily now leave on time (AD-14)
**And** this story creates no sweeper and no other cron, and an api test runs the sweep twice over the same due Class session and gets one lock (AD-9)

**Given** a Class session whose Start date has passed and that is not locked
**When** the sweep calls `sessions.service.lock(class_session_id)`
**Then** in one transaction it sets `locked_at` and stores the frozen snapshot on the Class session: the `GameSettings` with `schema_version`, the demand series materialised by the engine with its seed, the engine `rules_version`, and `SessionRuntime` (AI mode, Effort level, Inactivity limit, pinned model config id and its prompt versions) (AD-4, FR-12, FR-13, FR-15, FR-78)
**And** the snapshot is built by one function, `sessions.service.build_snapshot(class_session)`, so a Game that takes its snapshot at creation gets the same shape
**And** `sessions.service.is_locked` of Story 5.2 is now true from `locked_at` as well as from a passed Start date, and `sessions.service.lock` is callable by other modules, so Epic 8 can lock when the Lecturer starts early (AD-4)

**Given** the content that later epics pin per Class session
**When** the lock builds `SessionRuntime`
**Then** it holds an open map of pinned content versions and further runtime fields, empty in this story; `sessions.lock` fills it from a list of registered pin providers, so later epics add their entries without changing the lock's mechanism: Epic 6 the Starting task; Epic 9 the Debrief quiz, sentence templates, Detected pattern definitions and reflection questions; Epic 10 the Replay scenario template; Epic 11 the question set (AD-23)
**And** an api test registers a dummy provider and finds its version in the stored snapshot

**Given** a production deployment, AI mode LLM players and no key for the pinned provider
**When** the lock is attempted
**Then** it is refused with `provider_key_missing`, nothing is frozen, the sweep tries again each minute, and the Lecturer and the Admin are notified once (AD-17)

**Given** a locked Class session
**When** the Lecturer opens the Klasseøkt screen
**Then** Game settings, Demand pattern, AI mode, Effort level, Debrief mode, the obligatory mark with its required share and the Inactivity limit are read-only, while deadlines and Lab hours stay editable (FR-12, FR-18, UX-DR48)
**And** `session:<id>` is emitted to Class staff when the lock commits (AD-8)

**Covers:** FR-12, FR-13, FR-15, FR-18, FR-78, AD-4, AD-8, AD-9, AD-14, AD-17, AD-23, UX-DR48

### Story 5.12: Open the Class games on the frozen snapshot

As a Lecturer,
I want every Class game to open on the locked settings with AI players in the empty Seats,
So that my Students can start as soon as the Start date has come.

**Acceptance Criteria:**

**Given** a locked Class session
**When** the lock continues after the transaction of Story 5.11
**Then** every Class game receives the same snapshot through the new command `games.commands.set_snapshot`, added to the AD-2 list with its registry entry, one Game per transaction with the Game row lock, a `version` increment and `game:<id>` (AD-2, AD-4)
**And** an api test finds the dummy pin provider's version of Story 5.11 in the snapshot of every Class game, and from then on `games.commands.start` no longer answers `409 game_not_ready` for these Games

**Given** a Class game that is receiving its snapshot
**When** `set_snapshot` runs
**Then** in that same transaction every empty Seat gets an AI occupant with reason `initial`, of the kind the AI mode gives, `llm` or `rule_based`, through the same code as `games.commands.assign_seat`, so a Class game is never ready to start with a free Seat and the `start` of Story 1.8 never fills one with a Rule-based player against the AI mode (FR-30, AD-2, AD-5)
**And** in the same transaction a Seat whose Student has been removed from the Roster since the allocation (no longer in `classes.service.registered_students`) also gets the AI occupant, and the removed Student's row stays in the history (FR-7, AD-5)
**And** for this the story extends `games.commands.assign_seat`, which since Story 1.7 answers a conflict code on an occupied Seat, with an explicit replace argument that is accepted only while the Game is `not_started`; without it the conflict code stands (AD-2)
**And** an api test races `start` against `set_snapshot` under the Game row lock and finds either `409 game_not_ready` or a started Game with the AI occupants of the AI mode, never a Rule-based fill
**And** a lock interrupted half way is finished by the next sweep without changing a Game that already has its snapshot, shown by a test that fails the loop after the first Game

**Given** no allocation was confirmed before the Start date
**When** the lock runs
**Then** the registered Students are first allocated at random with the same `allocate` function and committed as in Story 5.9, so no registered Student is left without a Seat (FR-20)

**Given** a locked Class session
**When** the Lecturer opens the Klasseøkt screen
**Then** the allocation block lists every Class game with its number and four Seats, each as the Student's name or «KI-spiller», all not started (FR-22, FR-34)
**And** starting a Class game is not built here: Students start in Epic 6, and the Lecturer starts one or all from Spillstyring in Epic 8

**Given** the Class games are open
**When** events are emitted
**Then** `session:<id>` goes to Class staff and `user:<id>` to each Student with a Seat, so their views can refetch (FR-22, AD-8)

**Covers:** FR-22, FR-7, FR-20, FR-30, FR-34, AD-2, AD-4, AD-5, AD-8, AD-9

### Story 5.13: Seat Students who register after the allocation

As a Student who registered late,
I want to get a Seat in a Class game that has not started,
So that I can still play with a group.

**Acceptance Criteria:**

**Given** a Class session with a confirmed allocation and a registered Student who has no Seat in it
**When** `ops.sweep` runs the due action added in this story
**Then** it calls `sessions.service.seat_late_registrant(class_session_id, user_id)`, so the Student is seated within about a minute of registering, without `classes` importing `sessions` (FR-20, AD-9)
**And** the action is idempotent: a Student who already has a Seat is skipped

**Given** the Start date has not passed
**When** the late registrant is seated
**Then** the Student gets a random Role among the free Seats of a randomly chosen Class game that has one, through `games.commands.assign_seat`; if every Seat is taken a new Class game is created for the Student, whose other Seats get AI players at the lock (FR-20)

**Given** the Class session is locked
**When** the late registrant is seated
**Then** the Student takes a free AI-held Seat of a Class game with `lifecycle = not_started`, through `games.commands.assign_seat` with the replace argument of Story 5.12, which appends the Student as that Seat's occupant from Week 1 with reason `initial`; the AI occupant's row stays in the history (FR-20, AD-2, AD-5)
**And** a Seat in a Game that has started is never given away, shown by a test that races `start` against the seating under the Game row lock

**Given** a locked Class session where no Class game is still not started
**When** the sweep finds the late registrant
**Then** no Seat is assigned, the Student is listed on the Klasseøkt screen as registered without a Seat, and `sessions.service.students_without_seat(class_session_id)` returns them for the make-up in Epic 13 (FR-20)

**Given** a locked Class session and a Student who holds a Seat in a Class game that has not started, and whose Roster entry has been removed (Story 4.8)
**When** `ops.sweep` runs the second due action added in this story
**Then** it calls `sessions.service.replace_removed_student(class_session_id, user_id)`, which gives the Seat an AI occupant of the kind the AI mode gives through `games.commands.assign_seat` with the replace argument of Story 5.12 and reason `initial`, so no group waits for a person without access (FR-7, AD-2, AD-5)
**And** a Seat in a Class game that has started is left as it is, and the Klasseøkt list marks it as held by a removed Student; putting an AI player in there is the Lecturer's Takeover in Epic 8

**Given** a late registrant was seated
**When** the transaction commits
**Then** the Student and the other Students of that Class game get `user:<id>`, the Student gets the allocation notice, staff get `session:<id>`, and the Klasseøkt list shows the new name in place of «KI-spiller» (AD-8, AD-9)

**Covers:** FR-20, FR-7, AD-2, AD-5, AD-8, AD-9

### Story 5.14: Remind Students 24 hours before each deadline

As a Student,
I want a reminder the day before a deadline that applies to me,
So that I do not miss a step by forgetting the date.

**Acceptance Criteria:**

**Given** a Class session with deadlines
**When** `ops.sweep` finds a Play deadline, Debrief deadline or Test deadline that is 24 hours away or less and has no reminder yet
**Then** it calls `sessions.service.send_deadline_reminder(class_session_id, deadline)`, which calls `platform/notify.enqueue` once per Student of the Class session with the deadline reminder kind and a dedupe key of Class session, deadline kind and deadline time (FR-18, AD-9)
**And** running the sweep again enqueues nothing more, shown by a test

**Given** a reminder is enqueued
**When** it is delivered
**Then** it is a `digest` kind, registered in the digest delivery of Story 3.5 and gathered with the User's other notices into at most one mail per day and never sent between 22:00 and 07:00 Europe/Oslo, from a Jinja2 template in `platform/email/templates/` in Norwegian bokmål (AD-9, AD-19, FR-72)
**And** the mail names the deadline and its time in Europe/Oslo, states that the Class session is obligatory when it is, and never names the number of Weeks or uses «Beer Game» or «bullwhip» (FR-14, FR-17, AD-19)

**Given** the Lecturer moves a deadline after its reminder was sent
**When** the new deadline comes within 24 hours
**Then** a new reminder is sent, because the dedupe key holds the deadline time (FR-18)

**Given** a deadline that does not apply to a Student
**When** recipients are resolved
**Then** this story sends to every Student of the Class session, through one function `sessions.service.reminder_recipients(class_session_id, deadline)`; later epics narrow it with `progress.has_step` (a Student who has submitted the Individual test gets no Test deadline reminder) without changing the sweep (FR-18)

**Given** the reminder path
**When** the copy check and api tests run
**Then** the template passes the pre-Debrief forbidden-word test, and the notice rows and job arguments hold ids only (AD-14, AD-19)

**Covers:** FR-18, FR-17, FR-72, AD-9, AD-14, AD-19

### Story 5.15: Set a shipping capacity (cut list, `FEATURE_CAPACITY`)

As a Lecturer,
I want to limit how many units a Seat can ship per Week,
So that I can teach a chain with a bottleneck.

**Acceptance Criteria:**

**Given** `FEATURE_CAPACITY` is off
**When** the Klasseøkt screen renders or a settings request carries a capacity
**Then** no capacity field is shown, the API rejects a non-empty capacity with `feature_disabled`, and every other story of this epic works unchanged (AD-17)

**Given** the flag is on and the Class session is before its Start date
**When** the Lecturer opens the capacity setting
**Then** capacity is off by default and can be set as a whole number of units per Week for one Role or for all, stored in the engine's `GameSettings` field from Epic 1 (FR-12)

**Given** a capacity below the peak of the chosen Demand pattern
**When** the Lecturer saves
**Then** the engine's warning shows inline and does not block saving (FR-12)
**And** a capacity that is not a whole number above 0 is rejected inline with the allowed range

**Given** a capacity is set
**When** the screen renders
**Then** a help line states that a capped Seat can hold inventory and backlog at once and that Students are told the capacity in the briefing, and «Kjeden ved start» marks the capped Role in text (FR-12)
**And** the briefing wording and the capped Seat's play screen belong to Story 6.22, and the Debrief wording to Epic 9

**Given** the Start date has passed
**When** the lock runs
**Then** the capacity is part of the frozen `GameSettings` snapshot and is read-only (AD-4)

**Covers:** FR-12, AD-1, AD-4, AD-17, UX-DR48

### Story 5.16: Set Information visibility (cut list, `FEATURE_INFO_VISIBILITY`)

As a Lecturer,
I want to let each Seat see its neighbour's inventory and backlog,
So that I can teach what shared information does to ordering.

**Acceptance Criteria:**

**Given** `FEATURE_INFO_VISIBILITY` is off
**When** the Klasseøkt screen renders or a settings request switches visibility on
**Then** no visibility setting is shown, the API rejects it with `feature_disabled`, and every Class session stays at the default, off (FR-83, AD-17)

**Given** the flag is on and the Class session is before its Start date
**When** the Lecturer opens the Information visibility setting
**Then** two Bryter controls, off by default, switch on the view of the Seat directly upstream and of the Seat directly downstream, each showing current inventory and backlog (FR-83, UX-DR12)
**And** this story adds the Information visibility field (upstream view and downstream view, both off by default) to `engine.GameSettings` with a `schema_version` change and its validation, so settings stored before the change read as off, and the choice is stored there (AD-1, AD-4)
**And** the help text states the scope (all Class games of the Class session; the Factory has no upstream view and the Retailer no downstream view) and promises no effect on learning or cost (FR-83)

**Given** a saved visibility setting
**When** the Class session is locked
**Then** the setting is in the snapshot of every Class game, so `seat_state`, the LLM prompt and the Decision log all read the same value (AD-3, AD-4)
**And** filling the neighbour numbers of `seat_state` and showing them on the play screen are not built here (Story 6.21, UX-DR24)

**Given** the Start date has passed
**When** anyone tries to change the setting
**Then** it is read-only and the route answers `409 session_locked` (FR-18)

**Covers:** FR-83, FR-18, AD-1, AD-3, AD-4, AD-17, UX-DR12

### Story 5.17: Let Students choose a Class game and a Seat (cut list, `FEATURE_STUDENT_CHOICE`)

As a Student,
I want to pick my Class game and a free Seat before the Start date,
So that I can play with people I have arranged to play with.

**Acceptance Criteria:**

**Given** `FEATURE_STUDENT_CHOICE` is off
**When** the Klasseøkt screen or the Student routes are used
**Then** no allocation-method choice is shown, the «Velg spill og sete» route answers not found, and allocation works as in Story 5.8, Story 5.9, Story 5.10, Story 5.11, Story 5.12 and Story 5.13 (AD-17)

**Given** the flag is on and the Class session is before its Start date with no confirmed allocation
**When** the Lecturer chooses Student choice as Valgknapper and saves
**Then** empty Class games are created through `games.commands.create` without settings, enough for every registered Student, more are added as Students register, and each registered Student is notified that they can choose (FR-21, AD-2, AD-4)

**Given** a Student of the Class session before the Start date
**When** the Student opens «Velg spill og sete»
**Then** it lists the Klassespill, each with its four Seats as «Grossist, ledig» or the holder's name, and pressing a free Seat shows the primary button «Ta setet Grossist i Spill 17» (UX-DR62)
**And** pressing it assigns the Seat through `games.commands.assign_seat`; a Student holds one Seat per Class session, and choosing another moves the Student through `games.commands.move_seat` of Story 5.10 in the same request (FR-21)

**Given** two Students press the same free Seat
**When** the second request arrives
**Then** the Game row lock gives it `409 seat_taken`, the list is refetched, and focus moves to «Setet ble tatt av en annen. Velg et annet.» (`tabindex="-1"`) above the refreshed list, read once on focus (UX-DR62, AD-2)
**And** `user:<id>` is emitted for the Students of the Class session who can still choose; the list is fetched when the screen opens and after each own action, and refetching on the event without a reload comes with the topic map of Story 6.4 (AD-8)

**Given** the Start date arrives
**When** the lock of Story 5.11 and Story 5.12 runs
**Then** every registered Student without a Seat is placed at random in a free Seat, new Class games are added if none is free, empty Seats get AI players, and such a Student is shown «Du fikk et sete ved trekning: Grossist i Spill 17.» (FR-21, UX-DR62)

**Given** the «Velg spill og sete» screen
**When** it is tested with Playwright and axe at 320, 360 and 1440 px
**Then** it works at 360 px with a 320 px reflow floor, Seat state is text and never colour alone, tap targets are at least 44 px, and its copy comes from `web/src/copy/nb.ts` (FR-73, NFR-6, UX-DR75)

**Covers:** FR-21, FR-73, NFR-6, AD-2, AD-4, AD-8, AD-17, UX-DR62, UX-DR75

### Story 5.18: Create a Class session from an earlier one (cut list, `FEATURE_RERUN`)

As a Lecturer,
I want to start next year's Class session from one I have already run,
So that I do not set everything up again.

**Acceptance Criteria:**

**Given** `FEATURE_RERUN` is off
**When** the Lecturer creates a Class session
**Then** no copy option is shown and the copy route answers `feature_disabled` (AD-17)

**Given** the flag is on and the Lecturer has access to at least one earlier Class session, in this or another Class
**When** the Lecturer chooses to create from an earlier one
**Then** only Class sessions the Lecturer may see are offered, through a `platform/authz` scope helper, and `sessions.service.copy_from(source_id, target_class_id)` creates a new Class session with the source's Game settings, AI mode, Debrief mode and Inactivity limit (FR-66, AD-12)
**And** the copy takes the source's editable settings, not a locked Game snapshot, and gets the active default model config, not the source's (AD-4, AD-6)

**Given** a new Class session made by copying
**When** it is created
**Then** dates, Lab hours, the Roster, the allocation and the obligatory mark are not copied, and a fresh seed is drawn unless the Lecturer chooses to keep the old one (FR-66)
**And** an Effort level the new model config does not offer is replaced by that config's default, and the screen says so (FR-78)

**Given** the copied Class session
**When** the Klasseøkt screen opens
**Then** it is prefilled and can be saved unchanged with «Lagre Klasseøkt», the copied settings pass the engine's validation again, and any warnings show as in Story 5.3 (FR-66, FR-12)

**Given** later epics own more copyable settings (Replay scenario in Epic 10, question set, Item weights and Scoring guide in Epic 11)
**When** those epics are built
**Then** each adds its part to `copy_from` in its own story; this story copies only what Epic 5 owns and records that limit in the function's contract

**Covers:** FR-66, FR-12, FR-78, AD-4, AD-6, AD-12, AD-17

## Epic 6: Students play the Class game

When this epic is done, a group of up to four Students can play a full Class game on their phones or on a lab laptop: they see their Class game, Role and Seats on Hjem from the Start date, read the rules, do the Starting task, start the game, place one Order per Week on the graph-over-table play screen, see whom the game waits for, and end on the chain's Total cost. The epic owns the Student side of `api/app/modules/games/` and `web/src/modules/games/`, and creates `modules/progress`, `modules/content` (first with the Starting task) and the Starting task part of `modules/tests`. It also adds the shared pieces later epics reuse: the SSE stream and topic bridge, `drafts.ts`, `preview.ts`, the chart module, Graf over tabell, Kjedebånd, Setestatus, Stegene, Spillkort, Kjedens regning and Kjedens kostnad over tid. It reuses the number formatter Epic 5 put in `web/src/lib/`. Pause, Takeover, Reclaim, «I rommet», playout and turn reminders belong to Epic 8 and are not built here.

### Story 6.1: See my Class game, Role and Seats on Hjem

As a Student,
I want Hjem to show my Class game, my Role, the other Seats and the steps ahead,
So that I know where I play, with whom, and what comes next.

**Acceptance Criteria:**

**Given** a logged-in Student whose Class session has not reached the Start date, or who has no Seat yet
**When** the Student opens Hjem
**Then** Hjem shows no game card and the line «Du får Rolle og spill når Faglærer har bekreftet fordelingen.», with Stegene greyed out (UX-DR62)
**And** the page uses the Skjelett and the all-surface states from Epic 3, and takes all copy from `web/src/copy/nb.ts` (FR-72)

**Given** the Class session is locked at the Start date and the Student holds a Seat
**When** the Student opens Hjem
**Then** Hjem reads «Spill 17 · Du er Grossist» (game number and Role from the data) and lists all four Seats with Role and the Student's name or «KI-spiller» (FR-22)
**And** every AI-held Seat is named «KI-spiller» as plain text from this first view, never by an icon, badge or colour alone (FR-34, UX-DR69)
**And** the Seats are listed with Fabrikk at the top (UX-DR73)

**Given** the home endpoint is called
**When** the api builds the answer
**Then** the people side comes from a new `games.views.table_status(game, viewer)`, which resolves names at read time, is never stored and is never sent to an LLM (AD-3)
**And** the route declares its policy through `platform/authz` and the query joins through the scope helper `own_seat(user, game)`, added to `platform/authz` here; a Student who asks for another Student's game gets the Permission denied state, which never says whether the game exists (AD-12, FR-5)
**And** `games.service.student_game(user, class_session)` is added here as the one way any module finds a Student's game: in this epic it returns the Class game in which the Student holds or has held a Seat, and the home endpoint reads the game through it

**Given** a Student with a Seat
**When** Hjem renders
**Then** Stegene shows the six steps Klassespill, Debrief, Quiz, Replay, Individuell test and Rapport, with the current one filled and marked «pågår» in text, and each later step listed as not active with the line that says what opens it, for example «Replay, åpnes når du har bestått Debrief-quizen.» and «Individuell test, åpnes når du har fullført Replay.» (UX-DR29)
**And** the Stegene component is added to `web/src/components/` for reuse by Epics 9 to 13

**Given** Stegene needs to know which steps are done
**When** this story is built
**Then** `api/app/modules/progress/` is created with one step table, `record_step(user, class_session, step, at)` and `has_step(...)`, and the closed step enum `starting_task`, `class_game`, `explanation`, `debrief`, `quiz_passed`, `replay`, `test_submitted`, `assessment_ready` (AD-16)
**And** `record_step` is idempotent on `(user, class_session, step)`, emits `user:<id>` and `session:<id>` through `platform/events.emit` with its entry in the registry, and `progress` imports no feature module (AD-8, AD-16)
**And** the step states Stegene shows are computed in the api; the web app holds no rule for which step is open (AD-10)

**Given** the Class session has deadlines and Lab hours from Epic 5
**When** Hjem renders
**Then** it shows the next deadline («Neste frist»), the upcoming Labtimer and the Obligatorisk mark, all read from Epic 5's `GET /api/me/class-sessions`; this story adds no second source for them
**And** when `FEATURE_STUDENT_CHOICE` is on and the Class session uses Student choice before the Start date, Hjem links to Epic 5's «Velg spill og sete» route; with the flag off no such link is shown
**And** Hjem is the Student hub: there is no global navigation bar on phone, and Back from any Student page returns to Hjem

**Given** Playwright with axe at 320, 360 and 1440 px, and at 360 px with 200 % text
**When** Hjem is rendered in the before-allocation state and in the state with a Seat
**Then** there is no page-level horizontal scroll, no axe violation, every tap target is at least 44 px, and no text is below 13 px (FR-73, NFR-6)

**Covers:** FR-22, FR-34, FR-72, FR-73, NFR-6, AD-3, AD-8, AD-10, AD-12, AD-16, AD-17, AD-19, UX-DR29, UX-DR62, UX-DR69, UX-DR73

### Story 6.2: Read the rules before the first Order

As a Student,
I want a short briefing before my first Order,
So that I know the objective and the rules without being told what the exercise is called.

**Acceptance Criteria:**

**Given** a Student with a Seat who has not done the Starting task
**When** the Student opens the Class game from Hjem for the first time
**Then** the screen «Regler før første ordre» is shown before anything else of the game (FR-84, UX-DR63)
**And** Hjem's one primary button leads to it (draft copy, not in the spine: «Les reglene»)

**Given** the briefing is shown
**When** the Student reads it
**Then** it states that the objective is the lowest Total cost for the whole chain, that all Seats order in the same Week, how the delays work, that stock must be shipped when it exists, that the first Weeks are Veiledede uker, and that Students may arrange when to play but may not discuss Orders or numbers with other players (FR-84)
**And** it explains one real Uke with the product's own terms (Ordre inn, Levering, Sendt, Lager, Restordre, På vei) and says «enheter», never «øl»
**And** it tells the Student to play as if the business continues, and states no number of Weeks, true or false (FR-14)

**Given** the briefing copy in `web/src/copy/nb.ts`
**When** the CI copy check runs
**Then** it fails if the briefing or any other pre-Debrief string of this epic contains «Beer Game» or «bullwhip»; the product name «ØL-spillet» is the one allowed exception (FR-84, AD-19)
**And** the copy has no exclamation mark, praise or recommended order (UX-DR78)

**Given** the Student has read the briefing
**When** the Student presses the screen's one primary button
**Then** the Startoppgave opens (Story 6.3 adds it; in this story the button returns to Hjem)
**And** no new state is stored for "briefing read": the briefing shows again until `progress.has_step(starting_task)` is true, and afterwards it stays reachable as a Lenke on Hjem; Story 6.6 puts the same Lenke on the play screen

**Given** Playwright with axe at 320, 360 and 1440 px
**When** the briefing is rendered
**Then** it reflows without page-level horizontal scroll, has one primary button, a correct heading order and no axe violation (FR-73, NFR-6)

**Covers:** FR-14, FR-84, FR-72, FR-73, NFR-6, AD-19, UX-DR63, UX-DR78

### Story 6.3: Do the Starting task

As a Student,
I want to do a short stocks-and-flows task before I play,
So that I know the sum behind the numbers on the play screen, and my answers can be compared with the Individual test later.

**Acceptance Criteria:**

**Given** the Starting task content
**When** this story is built
**Then** `api/app/modules/content/` is created with immutable, versioned records and holds the Starting task as its first record type; an edit creates a new version (AD-23)
**And** the Starting task version is added as one entry in the open map of pinned content versions that Epic 5's `sessions.lock` writes to `SessionRuntime`, read through `content.service`; the lock itself is not rewritten (AD-4, AD-23)
**And** the items shipped in this story are placeholders that include «Regn posisjonen for én Uke»; the final items are the non-code deliverable of issue #16 and replace them as a new content version without a code change

**Given** a Student who has read the briefing
**When** the Student opens the Startoppgave
**Then** the items show on one column of the week table, each answered by typing a whole number in a field with `inputmode="numeric"`; letters, decimals or an empty answer give the inline error «Skriv et helt tall.» with the `restordre` border, announced with `role="alert"` when the Student leaves the field or presses the button (FR-85, UX-DR63)
**And** the task states that it counts toward nothing and works by keyboard alone; its length of about five minutes is a target for the content of issue #16 and is not tested here
**And** the item component (one column, number entry, right and wrong states) is added to `web/src/components/` for reuse by Epic 11, which repeats the same items in the Individual test

**Given** the Student sends an answer
**When** the api scores it
**Then** the score comes from computed rules in the pure `analysis.scoring`, added here for reuse by Epic 11, with no LLM call (FR-85, AD-1, AD-9)
**And** a wrong answer shows «Ikke riktig. Svaret er 3: 0 − 13 + 16.» and a right answer shows «Riktig.» with the same sum, each shown in the same column; the Student goes on either way (UX-DR63)
**And** the answers are stored once per Student and Class session with the content version, in a Starting task table owned by `modules/tests` (the spine's home for the Starting task; this story creates that module folder with only these routes and this table)

**Given** the last item is answered
**When** the final question shows
**Then** it reads «Har du spilt et spill som ligner dette før?» with «Ja», «Nei», «Vet ikke» and «Hopp over», it is optional, and it never names the game (FR-84, FR-85)

**Given** the Student finishes or skips the final question
**When** the task is done
**Then** `progress.record_step(user, class_session, starting_task, at)` is called and the screen reads «Ferdig. Gå til Uke 1.» (AD-16)
**And** a Student who closes the task halfway resumes at the first unanswered item, on any device

**Given** a Student who never placed an Order and whose Class game has ended
**When** the Student opens Hjem
**Then** the Starting task is still offered, and `progress.has_step(starting_task)` is the gate later epics read before the Debrief (FR-85)

**Given** Playwright with axe at 320, 360 and 1440 px
**When** the Startoppgave is rendered in its wrong, right, final-question and done states
**Then** it reflows without page-level horizontal scroll and has no axe violation; right and wrong are told in text, not by colour alone (FR-73, NFR-6)

**Covers:** FR-84, FR-85, FR-73, NFR-6, AD-1, AD-4, AD-9, AD-16, AD-23, UX-DR63

### Story 6.4: See changes without reloading

As a Student,
I want the pages I have open to update by themselves when something changes,
So that what I see is always current and I never have to reload.

**Acceptance Criteria:**

**Given** a logged-in User
**When** the web app opens `GET /api/events`
**Then** the api serves one native SSE stream per User, fed from one `LISTEN` connection per `api` process, forwarding only the topics the User's `platform/authz` scope allows; a Student never receives `session:<id>` (AD-8, AD-12)
**And** each event carries `{topic, id, version}` only, never data; `session:<id>` is coalesced to at most one event per 2 seconds; a heartbeat is sent every 15 seconds; the stream holds no database session and is closed by the server after 10 to 13 minutes (AD-8)
**And** the allowed topics are resolved on connect and again on every `user:<id>` event for that User, and the stream closes if the User is deactivated

**Given** an event arrives in the browser
**When** the web app handles it
**Then** `web/src/lib/api/topics.ts` is the only map from topic to TanStack Query keys; every event invalidates its keys and the data is refetched over REST through the generated client; no event is dropped by comparing versions (AD-8, AD-10)
**And** updating never needs a pull-to-refresh or a reload (UX-DR78)

**Given** Epic 4 and Epic 5 emit `user:<id>` and `session:<id>` but refetch nothing live
**When** this story builds the topic map
**Then** `topics.ts` maps `user:<id>` to the query keys of Hjem, of `GET /api/me/class-sessions` and of «Klassene dine» on the Lærerhjem, and `session:<id>` to the query keys of the Klasseøkt screen, its allocation block and the Lærerhjem parts of Story 5.2 and Story 5.9; where Story 5.17 is built, `user:<id>` also maps to the «Velg spill og sete» list (AD-8)
**And** Playwright shows two of them live, with focus not moved: a Lecturer moves a deadline and a Student's Hjem shows the new «Neste frist» within 2 seconds without reload, and a co-owner confirms the allocation and the other Lecturer's Klasseøkt shows it

**Given** the connection drops and returns
**When** the stream reconnects
**Then** the web app refetches everything visible, the Tilkoblingslinje from Epic 3 shows «Frakoblet. Det du har skrevet, er tatt vare på på denne enheten.» while offline and «Tilkoblet igjen.» for 5 s after, and a missed heartbeat marks live values with «Sist oppdatert 21:14» (NFR-5)

**Covers:** NFR-5, AD-8, AD-10, AD-12, UX-DR78

### Story 6.5: Start the Class game

As a Student,
I want to start our Class game when my group is ready,
So that we can begin without waiting for the Lecturer.

**Acceptance Criteria:**

**Given** a Class game that is `not_started` and has received its settings snapshot from the lock (Story 5.12), and a Student who has done the Starting task
**When** the Student opens Hjem or presses «Ferdig. Gå til Uke 1.»
**Then** the one primary button is «Start spillet», with the consequence line «Spillet starter for alle fire. Reglene for ventetid gjelder fra nå.» above it and no second dialog (FR-22, UX-DR78)
**And** the button is not offered while the Game has no snapshot, whether the Start date has not come, the lock is still running or the lock was refused; the api tells the web app whether the Game is ready, and a `start` call on a Game without a snapshot answers `409 game_not_ready` (AD-4)

**Given** the Student presses «Start spillet»
**When** the api handles it
**Then** the game is started only through `games.commands.start`, in one transaction with the row lock on the Game, a `version` increment and the events `game:<id>`, `user:<id>` for each Student in the Game and, because `games.policy` says the Lecturer overview applies to a Class game, `session:<id>` (AD-2, AD-8)
**And** if another Student or the Lecturer started it first, the press is treated as done and the Student lands on the game without an error
**And** the Student lands on the play route, which this story creates in `web/src/modules/games/`, showing «Uke 1», the Role, the game number and the four Seats

**Given** two Students of the same Class game are on Hjem
**When** one of them starts the game
**Then** the other sees the game as started, with «Gå til Uke 1» as the primary button, within 2 seconds and without reloading, through the stream of Story 6.4; focus does not move

**Given** the api test suite
**When** the registry test runs
**Then** `start` and every other command this epic touches has its entry in `platform/events/registry.py` and emits exactly its listed topics, which for a Game on the Lecturer overview include `session:<id>` (AD-8)

**Covers:** FR-22, AD-2, AD-4, AD-8, UX-DR62, UX-DR78

### Story 6.6: See my Seat's Week in the week table

As a Student,
I want to see this Week's numbers for my Seat in a table with one column per Week,
So that I can read my situation on a phone without scrolling the page sideways.

**Acceptance Criteria:**

**Given** a Student with a Seat in a running Class game
**When** the play screen asks for its data
**Then** one play endpoint returns `seat_state` and `table_status` in one envelope with `server_now` and `next_change_at` (AD-3)
**And** `seat_state` is Epic 1's `games.schemas.SeatState` model, numbers and Roles only, with its neighbour fields empty while Information visibility is off; a field the play screen needs and the model lacks is added to that model with a `schema_version` change, never beside it (AD-3)
**And** an api test asserts that the envelope for every Role holds no number of Weeks, no future demand, no other Seat's inventory, backlog or Orders, and customer demand only for the Retailer, one Week at a time (FR-14, FR-23)

**Given** the play screen on a phone
**When** it renders
**Then** the Topplinje shows «Uke 11» with «Grossist, Spill 17» under it and «Totalkostnad» over «68,00 kr» at the right, and never the number of Uker (UX-DR13, FR-14)
**And** the week table shows the rows Uke, Ordre inn, Levering, Netto lager, Posisjon, Din ordre and «Kost, kr», one column per Uke from nå − 7 to nå + 4, with the current Uke number bold (FR-23, UX-DR17)
**And** the right edge is always nå + 4, never the end of the game; no surface shows a week count, a share played or any progress toward the end (UX-DR71, UX-DR78)
**And** a Lenke to «Regler før første ordre» of Story 6.2 stands on the play screen

**Given** the table cells
**When** values are shown
**Then** Netto lager cells use the matrix steps with signed numbers, the Posisjon row has plain numbers with no fill, known arrivals in Levering right of nå sit in outlined boxes and are marked as ordered, not guaranteed, and the Din ordre cell at nå is an empty dashed cell (UX-DR17)
**And** every number is displayed as the api returned it; the web app computes no game quantity (AD-1, AD-10)

**Given** numbers and amounts anywhere in the product
**When** they are displayed
**Then** the one Norwegian number formatter that Epic 5 added to `web/src/lib/` renders them, and no second formatter is written: space as thousands separator, decimal comma, kroner to two decimals («2 266,00 kr»), a true minus sign, and an option for narrow cells to drop decimals (UX-DR5)
**And** where that formatter lacks kroner, the true minus sign or the narrow-cell option, this story extends it in place; it takes the api's decimal strings and the additions are covered by Vitest

**Given** a screen narrower than the columns need, or larger text
**When** the table renders
**Then** it sits in one scroll region with `role="region"`, the name «Graf og tabell» and `tabindex="0"`, a sticky row-label column that may wrap to two lines, columns never narrower than 1.6 em, a visible scrollbar and the caption «Sveip for tidligere uker» while earlier columns are hidden (UX-DR18)
**And** on load the region scrolls so the nå column is in view with as many of nå + 1 to nå + 4 as fit
**And** the table is an HTML `<table>` in relative units with `<th scope="col">` per Uke and `<th scope="row">` per row, and its cells are not focusable

**Given** a screen 1024 px wide or more, or a tablet in landscape
**When** the play screen renders
**Then** it uses the laptop layout with two columns, the table runs from Uke 1 to nå + 4 with the rows Uke, Ordre inn, Levering, Sendt, Netto lager, På vei, Posisjon, Din ordre and «Kost, kr»; a tablet in portrait gets the phone layout (FR-73)

**Given** Playwright with axe at 320, 360 and 1440 px, and at 320 and 360 px with 200 % text
**When** the play screen renders a Classic game fixture
**Then** 12 columns show at 360 px and 10 at 320 px at 100 % text, no cell text is below 13 px or clipped, nothing outside the region scrolls sideways, and there is no axe violation (FR-23, FR-73, NFR-6, UX-DR18)
**And** on a throttled 4G profile the play page shows its Skjelett in the real columns and then its data within 3 seconds (NFR-1)

**Covers:** FR-14, FR-23, FR-73, NFR-1, NFR-6, AD-1, AD-3, AD-10, AD-12, UX-DR5, UX-DR13, UX-DR17, UX-DR18, UX-DR71, UX-DR78

### Story 6.7: See Netto lager, Posisjon and cost as a graph over the table

As a Student,
I want a graph of my Netto lager, Posisjon and weekly cost directly over the table,
So that I see the movement and can read the exact number under every mark.

**Acceptance Criteria:**

**Given** no chart exists yet
**When** this story is built
**Then** the chart module `web/src/components/charts` is created as the only place that imports a chart library; charts take a fixed width from the caller and never use `ResponsiveContainer`, and every chart SVG carries a `<title>` (AD-18)
**And** Graf over tabell (graph plus the week table of Story 6.6 on one x-axis) is added to `web/src/components/` for reuse by Epics 7, 9, 10 and 13

**Given** the spike AD-18 demands
**When** the Netto lager graph is rendered over the week table
**Then** a Playwright test at 320, 360 and 1440 px fails if any Week mark is more than 1 px off the centre of its table column
**And** a CI test renders the same graph and table on the server to static HTML, converts it with WeasyPrint 70.0 (`pdf/ua-1`) and fails if the chart is missing, clipped or out of line with its table columns, or if a font is fetched from outside the app (AD-18)
**And** a chart type that fails either check is rebuilt as hand-made SVG inside the same module, and the outcome per chart type is recorded in the module's README

**Given** the play screen with Graf over tabell
**When** it renders
**Then** Netto lager is one 2 px line, blue with `lager-fill` above a true zero and red with `restordre-fill` below, with a direct label at the now-dot («Restordre 13») and ticks in steps of 20 (UX-DR16)
**And** the Posisjon line is thinner, in `ink-secondary`, with a square marker at every Uke, no fill and the direct label «Posisjon 3»; both lines stop at nå, and the y-range holds both (FR-23, UX-DR16)
**And** Kost per uke is stacked bars, lager cost below and restordre cost above, with the key «restordre 1,00 / lager 0,50» taken from the Game settings' rates
**And** the now-line is labelled «Nå» and runs through graph and table, with `future-tint` to its right up to nå + 4 (UX-DR16, UX-DR71)

**Given** the Klassespill
**When** the graph renders
**Then** no projection line is drawn; the component takes the projection as an option that only Epic 10 turns on (UX-DR19 belongs to Epic 10)
**And** no mark, axis or label shows where the game ends (FR-14)

**Given** a narrow screen or larger text
**When** the region scrolls
**Then** graph and table share one scroll position, so every mark stays over its number, and the y-axis labels stay sticky with the row labels (UX-DR18)

**Given** a screen reader
**When** it reads the play screen
**Then** the visible week table is the graph's alternative; the graph itself adds no second reading of the same numbers (NFR-6)
**And** the two lines differ in stroke, fill, marker and label, never by colour alone

**Given** Playwright with axe at 320, 360 and 1440 px, and at 320 and 360 px with 200 % text
**When** the graph over the table renders a Classic game fixture in an early, a middle and a late Uke
**Then** no label overlaps another, no text is below 13 px, and there is no axe violation (FR-73, NFR-6)

**Covers:** FR-14, FR-23, FR-73, NFR-6, AD-10, AD-18, UX-DR16, UX-DR17, UX-DR18, UX-DR71

### Story 6.8: See the Landing's Demodata Seat as a graph over its table

As a visitor,
I want the Landing to show one Seat as the same graph over a table that Students play on,
So that I see what the product looks like before I have an account.

**Acceptance Criteria:**

**Given** the Landing of Story 3.13, which shows its Demodata Seat as an HTML week table only
**When** this story is done
**Then** the Landing's Seat figure uses the shared Graf over tabell of Story 6.7 over that same table, showing one Seat in a Veiledet uke («Ett sete, Grossist, Uke 4. Veiledet uke.») with the label «Demodata» (UX-DR70)
**And** no second chart implementation is written for the Landing (AD-18)

**Given** the hidden-information rules
**When** the figure renders
**Then** it shows no week count, no end of the axis beyond nå + 4, no customers and no other Seat (UX-DR71)

**Given** Playwright with axe at 320, 360 and 1440 px
**When** the Landing renders
**Then** the figure passes the same alignment check as Story 6.7, the visible table is the graph's alternative, there is no page-level horizontal scroll and no axe violation (NFR-6)

**Covers:** NFR-6, AD-18, UX-DR70, UX-DR71

### Story 6.9: See my link of the chain in the Kjedebånd

As a Student,
I want to see my own link of the chain as a flow with stock, orders, goods and what is on the way,
So that I understand where my units are before I order.

**Acceptance Criteria:**

**Given** the play screen
**When** the Kjedebånd renders
**Then** it shows only the Seat's own link: a node with a blue stock bar above the baseline («Lager 12») or a red backlog bar below it («Restordre 13»), the order line along the top («Ordre inn 8») and the goods line below it («Levering 4», «Sendt 4») (FR-23, UX-DR14)
**And** the upstream neighbour is at the left end and the downstream neighbour at the right, goods flow right and orders flow left; the Fabrikk's band shows «Produksjon» at the left end and the Detaljist's shows «Kundene» at the right (UX-DR73)
**And** only the Detaljist's band shows the customers' number, for the current Uke only (FR-14)

**Given** the Supply line of the Seat
**When** the band draws På vei
**Then** the known arrivals of the next four Uker are boxes on the pipe at true scale with the label «På vei 16», and units overdue with no known date are a dashed, fixed-width box with a marked break and their number written above it (UX-DR14)
**And** the band is not interactive

**Given** bands of different widths
**When** the scale is set
**Then** the pixels per unit are derived from the available band width, with the same factor for pipe and stock and the DESIGN.md values as maxima, so the worst Uke of the game fits at 320 px; labels wrap under the band, never overlap (UX-DR15)
**And** a product test renders every Uke of a Classic game for all four Roles at 320 and 360 px and fails if the band overflows or two labels overlap

**Given** the chart module
**When** the band is built
**Then** it is hand-made SVG (d3-scale, d3-shape) inside `web/src/components/charts`, takes a fixed width, and is added as the shared Kjedebånd component with a four-Role variant slot for the Debrief and staff views of Epics 7 and 9; only the one-Seat variant is built here (AD-18, UX-DR15)
**And** it draws only numbers from `seat_state` and computes no game quantity (AD-1, AD-10)

**Given** a screen reader
**When** it reaches the band
**Then** the band reads as one text, for example «Ordre inn 8, Levering 4, Sendt 4, Restordre 13, På vei 16», and the SVG marks are hidden from it (NFR-6, UX-DR14)

**Given** the play screen on phone and on laptop
**When** it renders
**Then** the reading and focus order is Topplinje, Kjedebånd, Graf over tabell, order input; on phone På vei is shown in the band and not as a table row (FR-73)
**And** Playwright with axe at 320, 360 and 1440 px finds no violation

**Covers:** FR-14, FR-23, FR-73, NFR-6, AD-1, AD-10, AD-18, UX-DR14, UX-DR15, UX-DR73

### Story 6.10: Play the Guided Weeks

As a Student,
I want the first Weeks to be ordered for me while I learn the screen,
So that the game starts in balance and I see how a Week works before I decide.

**Acceptance Criteria:**

**Given** a Class game in a Guided Week
**When** the Student opens the play screen
**Then** the order area shows the label «Din ordre for Uke 2» and the fixed Order from the Game settings (4 in a Classic game) as a read-only field on `future-tint`, there is no confirm button, and the screen states that this is a «Veiledet uke» and that the Order is placed automatically (FR-24, UX-DR20, UX-DR62)
**And** this read-only field is the first state of the Ordrefelt component; its editable states come in Story 6.11
**And** the copy does not say how many Veiledede uker remain beyond what the briefing told (FR-14)

**Given** a Guided Week opens, at `start` or at an advance
**When** the opening transaction writes the `seat_turns` rows
**Then** it places the fixed Order from `engine.guided_order` for every Seat through `games.commands.place_order` with `decided_by = guided`: `players.ensure_order` of Story 2.1 already does this for non-student occupants, and this story makes the same transaction do it for every Student-held Seat; these Orders join the opening transaction and start no advance of their own, as in Story 2.1 (FR-24, AD-2, AD-15)
**And** no model call is made for an AI player in a Guided Week (FR-31)

**Given** the Student has the Guided Week on screen
**When** the play screen loads that Week
**Then** the web app calls the command `games.commands.view_week` of the AD-2 list, built in this story with its entry in the event registry, which sets `viewed_at` on the Seat's `seat_turns` row once, in one transaction with the Game row lock, and emits `game:<id>`, `user:<id>` for each Student whose waiting status changed and, for a Game on the Lecturer overview, `session:<id>`; the `viewed_at` column is added by this story's migration (AD-2, AD-8, AD-20)
**And** calling it again for the same Week changes nothing
**And** `viewed_at` is what counts as ordering in a Guided Week for the wait and for Takeover (founder decision 2026-11-12, which changes FR-24); the wait start is stored in Story 6.14 and Takeover is built in Epic 8

**Given** the `week_complete` rule of Story 1.9, which asks only that every Seat has an Order
**When** this story extends it
**Then** in a Guided Week `games.rules.week_complete` is true only when every Seat has its fixed Order and every Student-held Seat has `viewed_at` set, and the `view_week` call that makes it true advances exactly one Week in its transaction (FR-24, AD-2)
**And** a Game with no Student-held Seat passes its Guided Weeks as before, through `games.commands.advance` of Story 2.1, which `view_week` also calls after its commit like every `games.commands` entry point; the golden results of the simulation batches of Epic 1 are unchanged

**Given** the test suite
**When** it runs
**Then** an api test covers a four-Student Classic game through Weeks 1 to 5 with views arriving in different orders and at the same moment, and asserts one advance per Week and four `guided` Orders in each Guided Week; Playwright with axe covers the Veiledet uke state at 320, 360 and 1440 px (FR-73, NFR-6)

**Covers:** FR-14, FR-24, FR-31, FR-73, NFR-6, AD-2, AD-8, AD-15, AD-20, UX-DR20, UX-DR62

### Story 6.11: Type an Order and see where it lands

As a Student,
I want to type one whole number and see it appear in the table and the chain before I confirm,
So that I make this Week's decision knowing when it arrives.

**Acceptance Criteria:**

**Given** an open Week after the Guided Weeks of Story 6.10, in which the Student has not ordered
**When** the Ordrefelt renders
**Then** it has the label «Din ordre for Uke 11», the field is `type="text" inputmode="numeric" pattern="[0-9]*"`, the help line «Hele tall fra 0 til {maks}.» is always shown and tied with `aria-describedby`, and {maks} is the Game settings maximum from `seat_state` (FR-24, UX-DR20)
**And** empty, it shows «Antall enheter» and «Sist Uke bestilte du 8.» (in the first free Week this line shows the last fixed Order, «Sist Uke bestilte du 4.»), and «Bekreft ordre» is unavailable with `aria-disabled` and still focusable; pressing it shows «Skriv et helt tall fra 0 til {maks}.»
**And** no surface shows a recommended order (UX-DR78)

**Given** the Student types
**When** the text is not a whole number from 0 to {maks}
**Then** letters, decimals, a minus or spaces give «Skriv et helt tall fra 0 til {maks}.» and a too-large number gives «{n} er mer enn {maks}. Skriv et helt tall fra 0 til {maks}.», with the `restordre` border and `aria-invalid="true"` (FR-24, UX-DR20)
**And** the error is announced with `role="alert"` when the Student leaves the field or presses the button, not on every keystroke, and the button stays unavailable until the value is valid; 0 is a valid Order

**Given** the − and + segments
**When** they are used
**Then** they are named «Én færre» and «Én flere», step by 1 and announce the new value politely; − is unavailable at 0 and when empty, + on an empty field gives 1 and is unavailable at {maks}; unavailable means `aria-disabled="true"`, the segment keeps focus and a press does nothing (UX-DR20)

**Given** a valid typed value of 24
**When** the screen updates
**Then** the value shows in the Din ordre cell at nå and in the Levering cell of its arrival Uke, joined by a thin line, the Kjedebånd shows «På vei 16 + 24» with the new box last on the pipe and a 1.5 px `ink` border, the button reads «Bekreft ordre på 24», and the line «Kommer fram om lag Uke 15. Kan ikke endres etter at du har bekreftet.» stands above it (UX-DR14, UX-DR17)
**And** this is the only client arithmetic in the product: it lives in `web/src/lib/preview.ts`, uses only the preview coefficients in `seat_state`, hard-codes no delay, and is tested in Vitest against values from the engine's golden traces (AD-10)
**And** Posisjon at nå and «Kostnad så langt» do not change while typing
**And** sending the Order is not built here: a press on the button with a valid value does nothing yet, and Story 6.12 gives the button its action

**Given** the keyboard
**When** the Student presses Enter in the field
**Then** focus moves to the button and nothing is sent; only the button confirms (UX-DR20)

**Given** Playwright with axe at 320, 360 and 1440 px
**When** the empty, typed, invalid and out-of-range states are rendered
**Then** the field and button fill the width on phone at their token heights, every tap target is at least 44 px, and there is no axe violation (FR-73, NFR-6)

**Covers:** FR-24, FR-73, NFR-6, AD-10, UX-DR14, UX-DR17, UX-DR20, UX-DR78

### Story 6.12: Confirm the Order and keep what I typed

As a Student,
I want to confirm my Order with one press and have a typed number kept if I leave the page,
So that the decision is sent once, cannot be changed, and is never lost or sent behind my back.

**Acceptance Criteria:**

**Given** a valid value in the Ordrefelt of Story 6.11
**When** the Student presses «Bekreft ordre på 24»
**Then** the Order is written only through `games.commands.place_order`, in one transaction with the row lock on the Game, and emits `game:<id>`, `user:<id>` for each Student whose waiting status changed and, for a Game on the Lecturer overview, `session:<id>`; the client sends no expected `version` (AD-2, AD-8)
**And** this story adds an `actor` argument (the User id) to `place_order`: with an actor, the command checks that the actor is the Seat's current occupant and answers `409 seat_not_yours` otherwise; calls without a person (the guided Orders of Story 6.10, the `players` jobs and the rescue loop) pass none and skip the check (AD-2)
**And** while sending, the button reads «Sender ordre på 24 …» with `aria-disabled="true"` and `aria-busy="true"`, keeps focus and ignores further presses, and the field is read-only (UX-DR60)
**And** on success the screen reads «Ordren på 24 er sendt.» and focus moves to that message (`tabindex="-1"`); there is no undo and no confirmation dialog; the «Venter på …» part of the message comes with the Setestatus in Story 6.14 (FR-24, UX-DR60, UX-DR78)

**Given** a typed value
**When** the Student leaves the page, reloads or loses the connection before confirming
**Then** `web/src/lib/drafts.ts` keeps it in `localStorage`, keyed by User and field, restores it into the field, and clears all drafts on logout; a restored Order is never sent without a press (AD-10)
**And** `drafts.ts` is added to `web/src/lib/` for reuse by Epics 9 and 11

**Given** the session expires while an Order is typed
**When** the same User logs in again after «Du er logget ut. Logg inn igjen for å fortsette.»
**Then** Epic 3's return to the same page finds the value restored in the field, and it is not sent until the Student presses the button (UX-DR59)

**Given** Playwright with axe at 320, 360 and 1440 px
**When** the submitting and confirmed states are rendered and a typed value is restored after a reload
**Then** the focus rules above hold, every tap target is at least 44 px, and there is no axe violation (FR-73, NFR-6)

**Covers:** FR-24, FR-73, NFR-6, AD-2, AD-8, AD-10, UX-DR59, UX-DR60, UX-DR78

### Story 6.13: Never lose or double an Order on a bad connection

As a Student,
I want the app to tell me plainly whether my Order was sent when the connection fails,
So that I never order twice and never think I ordered when I did not.

**Acceptance Criteria:**

**Given** the Student pressed «Bekreft ordre på 24»
**When** the request fails
**Then** the screen reads «Ordren ble ikke sendt. Ingenting er bestilt ennå.» as an assertive `role="alert"`, the field keeps 24 and stays editable, and the primary button reads «Prøv å sende 24 igjen» with focus still on it (UX-DR60)

**Given** an Order already stored for the Seat and the open Week
**When** `place_order` is called again for it, by a retry or from a second device
**Then** the api answers `409 order_exists`, the stored Order is never updated, and the unique key `(game_id, week, seat_id)` backs this up (AD-2, FR-24)
**And** the web app then refetches the play envelope and shows the Confirmed state with the stored value, so a retry can never create a second Order

**Given** a Student who no longer holds the Seat, or a Week that is no longer the open Week
**When** `place_order` is called
**Then** the api answers `409 seat_not_yours` (the check of Story 6.12) or `409 week_not_open` (the code of Story 1.9 for an Order outside the open Week); the web app maps each code to Norwegian copy from `nb.ts` and refetches the screen (AD-2, AD-19)

**Given** no answer has come after the order-submit timeout (configuration, placeholder 10 s)
**When** the timeout passes
**Then** the screen reads «Vi vet ikke om ordren kom fram. Sjekker …» politely, focus stays on the button, and the app asks the server: if the Order is there it shows Confirmed, if not it shows Submit failed; the Order is never locked silently (UX-DR60)

**Given** the device is offline with 24 typed
**When** the Student looks at the screen
**Then** the Tilkoblingslinje shows and the order area reads «Ordren på 24 er ikke sendt.», announced politely, with the value kept in the field
**And** when the connection returns it reads «Tilkoblet igjen. Ordren er ikke sendt ennå.» with the normal «Bekreft ordre på 24»; nothing is sent without a press (UX-DR60, AD-10)

**Given** the session expired with 24 typed
**When** the Student logs in again
**Then** the Student returns to the same Week with 24 restored from `drafts.ts` and not yet sent, as Story 6.12 built it; a Playwright test covers expiry in the middle of a submit (UX-DR59)

**Given** the test suite
**When** it runs
**Then** an api test covers two `place_order` calls racing for the same Seat and Week (one succeeds, one gets `409 order_exists`), and Playwright covers the failed, timed-out and offline states with axe at 320, 360 and 1440 px (NFR-6)

**Covers:** FR-24, FR-26, NFR-5, NFR-6, AD-2, AD-10, AD-19, UX-DR59, UX-DR60

### Story 6.14: See which Seats have ordered and whom the game waits for

As a Student,
I want to see who has ordered this Week, whom the game waits for and for how long,
So that I know whether it is my turn or someone else's.

**Acceptance Criteria:**

**Given** a running Class game
**When** the Setestatus renders
**Then** it lists all four Seats, each with a dot, the Role, the name or «KI-spiller», and the status in text: «har bestilt», «venter, 3 min» or «venter (deg)»; a filled dot means ordered and a hollow dot waiting, and the text always repeats the state (FR-25, UX-DR25)
**And** it appears on the play screen after the Student has confirmed an Order, and on Hjem
**And** the component is added to `web/src/components/` for reuse by Epics 7 and 8

**Given** the people side of the play envelope
**When** the api builds it
**Then** `games.views.table_status` gives per Seat the occupant (name or AI), whether it has ordered, and the wait start read from the stored `wait_started_at` of the open turn; nothing else computes a wait (AD-3, AD-20)
**And** this story's migration adds `wait_started_at` to `seat_turns`: when the first Student orders in the open Week, `place_order` sets it, in that same transaction, on the turns of the Seats that have not ordered, and in a Guided Week `view_week` of Story 6.10 sets it on the turns of the Seats that have not viewed when the first Student views the Week; the time comes from `games.rules.turn_times` of Story 2.6, extended here with the clock-start input, and only `games.commands` writes it (FR-25, AD-2, AD-20)
**And** before any Student has ordered or viewed, a waiting row reads «venter» with no duration
**And** the web app shows the running «3 min» from `server_now` and the stored time, and refetches at `next_change_at`

**Given** another Seat orders
**When** the `game:<id>` event arrives
**Then** the Setestatus updates within 2 seconds without reload, never moves focus, and announces the «Venter på: …» line politely (FR-25, NFR-6)
**And** the confirmed message names whom the game waits for by name or Role, with the duration: «Venter på: Jonas (3 min) og deg.» style, never «Venter på andre spillere …»

**Given** a Seat held by an AI player that has not ordered yet
**When** the Setestatus renders
**Then** its row reads «KI-spiller» with «venter» and no spinner or extra copy (UX-DR62)
**And** every AI-held Seat is labelled «KI-spiller» wherever Seats are shown; Students never see «LLM-spiller» or the model (FR-34, UX-DR69)

**Given** a Guided Week in which one Student has not opened the game
**When** the others look at the Setestatus
**Then** opening the Week counts as ordering: a Seat whose Student has viewed the Week reads as ordered, and the absent Student's row shows as waited for with the same texts and the duration from `wait_started_at`, so the group sees why the Week has not advanced (FR-24, FR-25)

**Given** a Seat whose LLM player the Play guard has switched to a Rule-based player
**When** the Setestatus renders
**Then** the same row states that the Seat now uses a rule-based KI-spiller (draft copy, not in the spine), read from the occupancy `reason` through the one mapping of AD-15, which this story adds to `games` `service.py` for every later reader: one function from `decided_by`, `fallback`, `occupant_kind` and `reason` to a mark, with an api test for the `guard_switch` mark; later stories read it and add the marks they need to it (AD-15, FR-34, UX-DR69)

**Given** Epic 8 will add Pause, Takeover, Reclaim and «I rommet»
**When** the Setestatus and the play screen are built
**Then** the Setestatus has named slots for a status line above the list, a control block below it, and a second line and an action under each row, and the play screen has a slot for a notice above the Ordrefelt; none of them renders anything in this epic, and Epic 8 fills them without changing the component's structure

**Given** Playwright with axe at 320, 360 and 1440 px
**When** the Setestatus renders with Students and AI players in ordered and waiting states
**Then** rows reflow without page-level horizontal scroll, state is never told by the dot alone, and there is no axe violation (FR-73, NFR-6)

**Covers:** FR-24, FR-25, FR-34, FR-73, NFR-6, AD-2, AD-3, AD-8, AD-15, AD-20, UX-DR25, UX-DR62, UX-DR69

### Story 6.15: See the new Week within two seconds, on any device

As a Student,
I want the next Week to appear by itself as soon as the last Seat has ordered, and to find the same Week after a reload,
So that play flows in a Lab hour and nothing is lost when I switch device.

**Acceptance Criteria:**

**Given** three Seats have ordered in an open Week
**When** the last Order is placed through `place_order`
**Then** that transaction runs `engine.advance` once, stores the new Week state and the new `seat_turns` rows, updates the Game `version`, and emits `game:<id>`, `user:<id>` for each Student and, for a Game on the Lecturer overview, `session:<id>`, before any client is told (FR-26, AD-1, AD-2, AD-8)
**And** a test with the last human Order and an AI Order arriving at the same moment shows exactly one advance (AD-2)

**Given** Students connected to the game
**When** the Week advances
**Then** each sees the new Week within 2 seconds of the last Order, excluding AI player thinking time, without reload; a Playwright test with four sessions (and one with mock AI players) measures it against the 2-second limit (FR-26, NFR-1)
**And** the new column shows Levering and Ordre inn filled, Netto lager and Posisjon for nå, and an empty dashed Din ordre cell; the region scrolls so nå and «Nå» are in view (UX-DR18)

**Given** the Week has advanced
**When** the Uke-overgang shows
**Then** it reads «Uke 11 er ferdig regnet», then the deltas («Restordre 13 blir 20»), «Denne uka: 20 restordre × 1,00 = 20,00 kr» and the Lenke «Kostnad så langt», all with numbers from the api, and it is announced politely (UX-DR23)
**And** the now-line moves one column in an animation of at most 2 s that never blocks input; «Hopp over» ends it at once; the Ordrefelt for the new Week is usable from the first moment
**And** with reduced motion set there is no animation and the result shows at once; there is no celebration animation in any case (UX-DR23, UX-DR78)

**Given** a Student reloads the page or opens the game on another device
**When** the play screen loads
**Then** it resumes at the current Week from stored state with nothing lost, and shows the Confirmed state if this Week's Order is already placed (FR-26, NFR-5)

**Given** a Student whose connection was lost while the Week advanced
**When** the SSE stream reconnects
**Then** the screen refetches, shows the current Week in place without moving focus, and a typed but unsent Order for a Week that has closed is not sent and is cleared with a line saying so (draft copy, not in the spine) (NFR-5)

**Given** the play screen at 320, 360 and 1440 px
**When** Playwright with axe runs the Uke-overgang with and without reduced motion
**Then** it reflows without page-level horizontal scroll and has no axe violation (FR-73, NFR-6)

**Covers:** FR-26, FR-73, NFR-1, NFR-5, NFR-6, AD-1, AD-2, AD-8, UX-DR18, UX-DR23, UX-DR62, UX-DR78

### Story 6.16: See what my Seat has cost so far

As a Student,
I want to see my running Total cost and how it is made up, with every row of my table one tap away,
So that I understand what my inventory and backlog cost without being told what to order.

**Acceptance Criteria:**

**Given** the play screen on a phone
**When** the Student presses the Totalkostnad pair in the Topplinje or the Lenke «Alle rader og kostnad» above the Ordrefelt
**Then** the Totalkostnad pair is one button named «Totalkostnad 68,00 kr, vis alle rader og kostnad» with a hit area of at least 44 px, and either control opens «Alle rader og kostnad» (UX-DR13, UX-DR21)

**Given** «Alle rader og kostnad» is open
**When** it renders
**Then** it is a full screen on `paper`, not an overlay, titled «Alle rader, Uke 11» with the Lenke «Lukk», and holds the graph over a table with the rows Uke, Ordre inn, Levering, Sendt, Lager, Restordre, Netto lager, På vei, Posisjon, Din ordre, Kost per uke and «Sum, kr» (FR-23, UX-DR21)
**And** below the table stand the two column-sum lines «Netto lager i kolonne 11  −9 + 4 − 8 = −13» and «Posisjon i kolonne 11  −13 + 16 = 3», with terms and results from the api, then «Kostnad så langt»

**Given** the Student presses «Lukk»
**When** the screen closes
**Then** the play screen returns with the typed Order kept and focus on the control that opened the panel (UX-DR21)

**Given** «Kostnad så langt»
**When** it renders
**Then** it shows «Lagerkostnad» and «Restordrekostnad», each with a thin proportional bar and the amount, then «Totalkostnad» under a rule, then «Totalkostnad over tid» as a stacked area from Uke 1 to nå with a true zero, and last the week's sum line «Denne uka: 13 restordre × 1,00 = 13,00 kr» (UX-DR22)
**And** it shows the Seat's own cost only, never another Seat's or the chain's, and never what to order (UX-DR72, UX-DR78)
**And** it recalculates when a Uke is charged, not while typing

**Given** a screen 1024 px wide or more
**When** the play screen renders
**Then** «Kostnad så langt» is pinned under the Ordrefelt in the right column and always visible, and the Lenke «Vis som tabell» under «Totalkostnad over tid» opens the table Uke / Lager / Restordre / «Sum, kr» in place (FR-73, UX-DR22)
**And** on phone the «Sum, kr» row in Alle rader is that table, and the area chart is `aria-hidden` and points to it (NFR-6)

**Given** the charts in this story
**When** they are built
**Then** they come from `web/src/components/charts`, reuse Graf over tabell and the number formatter, and pass the same alignment check as Story 6.7 (AD-18)

**Given** Playwright with axe at 320, 360 and 1440 px, and at 360 px with 200 % text
**When** Alle rader og kostnad and the pinned panel render
**Then** only the graph-and-table region scrolls sideways, no text is below 13 px, and there is no axe violation (FR-73, NFR-6)

**Covers:** FR-23, FR-73, NFR-6, AD-10, AD-18, UX-DR13, UX-DR21, UX-DR22, UX-DR72, UX-DR78

### Story 6.17: See on Hjem whether the game waits for me

As a Student,
I want Hjem to show my game's state and take me straight to the current Week,
So that I can see at a glance whether I must act.

**Acceptance Criteria:**

**Given** a running Class game that waits for this Student's Order
**When** the Student opens Hjem
**Then** the Spillkort is titled «Spillet venter på deg» with «Uke 11» at the right, holds a mini graph over a three-row table (Uke, Netto lager, Din ordre) in the same 12-column window, «Totalkostnad 68,00 kr», and the one primary button «Gå til Uke 11» (FR-25, UX-DR28)
**And** the card never shows a week count, a share played or the end of the axis beyond nå + 4 (FR-14, UX-DR71)

**Given** a running Class game in which the Student has ordered this Week
**When** the Student opens Hjem
**Then** the same card shows the Setestatus and has no primary action (UX-DR28, UX-DR62)

**Given** the mini graph
**When** a screen reader reads the card
**Then** the mini graph is `aria-hidden` and the card's text plus «Netto lager −13 i Uke 11.» is its alternative (NFR-6, UX-DR28)
**And** the card reuses Graf over tabell from `web/src/components/` at mini scale with no new marks, and is added to `web/src/components/` as the shared Spillkort with a title variant, so Epic 13 can show «Oppfølgingsspill» with the same component and no copy of it

**Given** Hjem is open
**When** another Seat orders or the Week advances
**Then** the card and its Setestatus update within 2 seconds through the `user:<id>` and `game:<id>` topics in `topics.ts`, without reload and without moving focus (FR-25, AD-8)

**Given** the home endpoint
**When** it serves the card
**Then** the numbers come from `seat_state` and the people from `table_status`, the same sources as the play screen, so Hjem and Spill never disagree (AD-3)

**Given** Playwright with axe at 320, 360 and 1440 px
**When** Hjem renders the waits-for-you and waiting-for-others states
**Then** the card reflows without page-level horizontal scroll, has at most one primary button, and no axe violation (FR-73, NFR-6)

**Covers:** FR-14, FR-25, FR-73, NFR-6, AD-3, AD-8, UX-DR28, UX-DR62, UX-DR71

### Story 6.18: See the chain's Total cost when the game ends

As a Student,
I want the game to end on what the whole chain cost, per Role and not per name,
So that my group looks at the chain's result together before the Debrief.

**Acceptance Criteria:**

**Given** the Order that completes the last Week in Game settings
**When** `place_order` commits it
**Then** the last Week runs in full through the engine and `games.commands.finish` sets `lifecycle = finished` in the same transaction, with `game:<id>`, `user:<id>` and, for a Game on the Lecturer overview, `session:<id>` emitted (FR-28, AD-2, AD-8)
**And** `finish` calls `progress.record_step(user, class_session, class_game, at)` for every Student who was ever assigned to a Seat of the Game, read from the occupancy history, so a Student whose Seat was later held by an AI player is recorded too; whether the step counts toward Completion is decided later by `analysis.completion`, not here (AD-16)
**And** the finished Class game runs the same finished-game check the simulation runner calls in Epic 1: the engine is replayed at the stored `rules_version` over the stored Orders, conservation of units and cost totals are checked, the result is stored in `game_checks`, and any violation is logged as an error (FR-29, NFR-9, AD-4)
**And** the check is run by a due action that this story adds to the `ops.sweep` of Story 3.5: the sweep finds finished Games without a `game_checks` row and calls `games.service.verify_finished(game_id)` of Story 1.10, one Game per transaction, so the check never blocks or delays the end screen (AD-9)

**Given** `games.policy` decides what applies per purpose
**When** this story is built
**Then** it gets two new columns, "records the Class game step" and "pre-play gate applies", both on for `class` and both off for `simulation`; `finish` records the step only where the first is on, and the briefing and Starting task gate of Story 6.2, Story 6.3 and Story 6.5 is asked only where the second is on (AD-13)
**And** no command or view branches on the purpose itself

**Given** the game has finished
**When** a connected Student's screen updates, or the Student opens the game later
**Then** «Spillet er ferdig» shows, in this order: «Kjedens totalkostnad», the chain total in `figure-hero` («2 266,00 kr»), «Fire Roller, to kostnadsarter, hele spillet.», Kjedens regning, «Kjedens kostnad over tid», «Hvorfor ble den slik? Det finner dere ut i Debriefen, med alle fire Rollene.» and the primary button «Gå til Debrief» (FR-28, UX-DR30)
**And** Hjem shows the game as finished and Stegene marks the next step

**Given** Kjedens regning
**When** it renders
**Then** it is a table with the columns Lager, Restordre and Sum and one row per Role from Detaljist to Fabrikk, never per name, each with a split bar whose numbers stand in the same row; the viewer's own row is marked «(deg)» and the «Kjeden» row stands under a rule (FR-28, UX-DR30, UX-DR73)
**And** there is no sorting by cost, no ranking, no praise and no celebration animation (UX-DR72, UX-DR78)

**Given** «Kjedens kostnad over tid»
**When** it renders
**Then** it is a stacked area of the chain's cumulative cost from Uke 1 to the last Uke with a true zero and the final values labelled at the right, from `web/src/components/charts`, and the Lenke «Vis som tabell» opens Uke / Lager / Restordre / Sum for the chain in place (UX-DR30, NFR-6)
**And** Kjedens regning and Kjedens kostnad over tid are added to `web/src/components/` as shared components for reuse by Epic 9; Kjedens regning has a slot for the Debrief's extra rows, which stays empty here

**Given** the result endpoint
**When** a Student of the game calls it
**Then** it returns chain cost per Role and per Uke only when the Game is finished; before that it answers with a stable error code, so no chain data leaks during play (AD-3, FR-14)
**And** it returns Roles, never names, and no demand series; the demand reveal stays behind the Debrief gates of Epic 9

**Given** the Student presses «Gå til Debrief»
**When** the Debrief of Epic 9 does not exist yet
**Then** the button's target is one route constant that leads to Hjem, where Stegene shows Debrief as the next step; Epic 9 points it at the Debrief
**And** the screen has a slot for a note under the heading, which Epic 8 fills when a game ended by playout; nothing renders there in this epic

**Given** Playwright with axe at 320, 360 and 1440 px
**When** «Spillet er ferdig» renders
**Then** it reflows without page-level horizontal scroll, has one primary button and no axe violation (FR-73, NFR-6)

**Covers:** FR-14, FR-28, FR-29, FR-73, NFR-6, NFR-9, AD-2, AD-3, AD-4, AD-8, AD-9, AD-13, AD-16, AD-18, UX-DR30, UX-DR72, UX-DR73, UX-DR78

### Story 6.19: Propose and accept a time to play

As a Student,
I want to propose a time to play and accept one from my group without writing text,
So that we can arrange play without a chat.

**Acceptance Criteria:**

**Given** a Student with a Seat in a Class game that is not finished, from the Start date
**When** the Student opens the proposal control on Hjem (draft copy, not in the spine: «Foreslå tidspunkt»)
**Then** it opens in place with a date field and a time field and no free-text field of any kind, the primary button states its effect, and «Avbryt» returns focus to the control that opened it (FR-22, UX-DR78)
**And** a time outside now to the Play deadline shows «Velg et tidspunkt mellom nå og Spillfristen, {dato}.» in the Ordrefelt error pattern

**Given** a valid time
**When** the Student sends the proposal
**Then** it is stored through a new command `games.commands.propose_time`, added to the AD-2 command list and the event registry, in a proposal table owned by `modules/games`; it emits `game:<id>` and `user:<id>` for the other Students (AD-2, AD-8)
**And** a Class game has at most one open proposal; a new one replaces the old and clears its acceptances

**Given** an open proposal
**When** the other Students of the game open Hjem or the play screen
**Then** they see who proposed which time, by name, and can accept with one press through `games.commands.accept_time`; all four see who has accepted (draft copy, not in the spine) (FR-22)
**And** the other Students are told through `platform/notify.enqueue` with a `digest` kind, registered in the digest delivery of Story 3.5, and a dedupe key per proposal, which also shows the notice in the app at once (AD-9)

**Given** a proposed or accepted time
**When** `games.rules.turn_times` computes a Seat's times
**Then** the proposal is not among its inputs: it never starts, pauses or shortens an Inactivity limit and never governs when an AI player may be put in (AD-20)
**And** an api test asserts that `seat_turns` is unchanged by `propose_time` and `accept_time`

**Given** the proposed time has passed, or the game has finished
**When** Hjem renders
**Then** the proposal is no longer shown

**Given** Playwright with axe at 320, 360 and 1440 px
**When** the proposal form and the proposal line render
**Then** they reflow without page-level horizontal scroll, work by keyboard alone, and have no axe violation (FR-73, NFR-6)

**Covers:** FR-22, FR-73, NFR-6, AD-2, AD-8, AD-9, AD-20, UX-DR78

### Story 6.20: Play a private test Game as a Lecturer (cut list, behind `FEATURE_LECTURER_TEST_GAME`)

As a Lecturer,
I want to play a private test Game with my chosen Game settings against three AI players,
So that I see what the settings do before the Start date.

**Acceptance Criteria:**

**Given** `FEATURE_LECTURER_TEST_GAME` is off
**When** a Lecturer opens the Klasseøkt screen
**Then** no test game action is shown and the api route answers as not found (AD-17)

**Given** the flag is on and a Lecturer is on a Class session before the Start date
**When** the Lecturer chooses a Role with Valgknapper and presses the action (draft copy, not in the spine: «Start testspill»)
**Then** `games.commands.create` makes a Game with `purpose=lecturer_test`, snapshots the Class session's current Game settings, demand series, seed, `rules_version` and `SessionRuntime` at creation through `sessions.service.build_snapshot` of Story 5.11, puts the Lecturer in the chosen Seat as a `student` occupant with the Lecturer's `user_id` (Story 5.9) and AI players of the Class session's AI mode in the other three, and starts it (FR-87, AD-4, AD-13)
**And** the Class session's own settings stay editable and unlocked; the test Game reads only its snapshot

**Given** the purposes table
**When** this story is built
**Then** `games.policy` gets its `lecturer_test` row: snapshot at creation, no inactivity Takeover, no Pause, no Play deadline playout, not in the Lecturer overview, Guided Weeks as the settings say, and both columns of Story 6.18 off, so the Class game step is not recorded and the Lecturer goes straight to the play screen without briefing or Starting task; no command or view branches on the purpose itself (AD-13)
**And** the test Game carries the Class session id, so `games.service.budget_scope(game)` answers the Class session for it as for a Class game (Story 5.9) and its AI calls are charged to that budget; whether test Games should be charged elsewhere stays open until the prototype settles it (issues #8, #9)

**Given** the Lecturer plays
**When** the play screen renders
**Then** it is the same play screen as the Students', reached from the Klasseøkt, and every screen of the Game carries a plain-text label that it is a test game (draft copy, not in the spine: «Testspill»), not «Demodata» (UX-DR70)
**And** the three other Seats read «KI-spiller» (FR-34)
**And** the Lecturer's access goes through the same `platform/authz` policy as a Student's own Seat; no `if role ==` is added (AD-12)

**Given** a test Game, running or finished
**When** any Class session list, summary, funnel or step query that exists is called
**Then** the Game is absent from each, an api test asserts it for every such endpoint, and no `progress.record_step` is called for it (FR-87, AD-13)
**And** the test names the rule for later epics: every report, statistic and export reads through `reports.scope`, which excludes `lecturer_test`

**Given** the test Game ends
**When** «Spillet er ferdig» shows
**Then** it shows the chain total and Kjedens regning with the test game label, and its button leads back to the Klasseøkt, not to a Debrief

**Covers:** FR-87, FR-34, AD-4, AD-12, AD-13, AD-17, UX-DR70

### Story 6.21: See the neighbour numbers the Lecturer switched on (cut list, behind `FEATURE_INFO_VISIBILITY`)

As a Student,
I want to see my neighbour's inventory and backlog where the Lecturer has switched it on,
So that I can use the same information as everyone else in my Class session.

**Acceptance Criteria:**

**Given** `FEATURE_INFO_VISIBILITY` is off, or Information visibility is off for the Class session
**When** the play screen renders
**Then** the Kjedebånd shows no neighbour numbers and `seat_state` carries none (FR-83, AD-17)

**Given** the flag is on and the Lecturer switched on the upstream view, the downstream view or both
**When** the play screen renders
**Then** the neighbour's inventory and backlog show in the Kjedebånd at that neighbour's end, upstream at the left and downstream at the right, each labelled with the Role and the Uke the numbers refer to (draft copy, not in the spine) (FR-83, UX-DR24, UX-DR73)
**And** the Fabrikk has no upstream view and the Detaljist has no downstream view

**Given** the numbers shown
**When** the api serves them
**Then** `games.views.seat_state` fills the neighbour fields of `games.schemas.SeatState`, left empty since Story 1.8, with the neighbour Seat's inventory and backlog as they stand in the open Week, for each view that the Game's snapshot has switched on (Story 5.16); this story builds that fill (AD-3, FR-83)
**And** the play screen shows these fields and nothing else, so an AI player in that Seat gets exactly the same numbers and the Decision log's `state_seen` records what was visible
**And** an api test asserts that no Seat other than the allowed neighbour appears, and that neighbour Orders, cost and Supply line never do

**Given** a screen reader
**When** it reads the band
**Then** the band's text adds the neighbour numbers with Role and Uke after the Seat's own numbers (NFR-6)

**Given** the Kjedebånd scale test of Story 6.9
**When** it runs with both neighbour views on
**Then** the band still fits at 320 and 360 px in every Uke of a Classic game with no overlapping labels, and Playwright with axe at 320, 360 and 1440 px finds no violation (UX-DR15, FR-73)

**Covers:** FR-83, FR-73, NFR-6, AD-3, AD-17, UX-DR15, UX-DR24, UX-DR73

### Story 6.22: See the capacity in the briefing and on a capped Seat (cut list, behind `FEATURE_CAPACITY`)

As a Student,
I want to be told about a shipping capacity before I play and to see both my stock and my backlog when my Seat is capped,
So that I understand why goods stay in stock while orders wait.

**Acceptance Criteria:**

**Given** `FEATURE_CAPACITY` is off, or the Game settings set no capacity
**When** the briefing and the play screen render
**Then** nothing about capacity is shown and every screen of this epic is as before (AD-17)

**Given** the flag is on and the Game's snapshot sets a capacity (the engine of Story 1.12, set by the Lecturer in Story 5.15)
**When** a Student reads «Regler før første ordre» of Story 6.2
**Then** the briefing states which Roles can ship at most how many units per Week, and that such a Role can have stock and unfilled orders at the same time (draft copy, not in the spine) (FR-12, FR-84)
**And** the api returns the capacities from the Game's snapshot as rules of the game, never another Seat's state, and the copy passes the pre-Debrief copy check and names no number of Weeks (AD-3, AD-19, FR-14)

**Given** a capped Seat with inventory and backlog both above 0
**When** the play screen renders
**Then** the Kjedebånd of Story 6.9 draws the stock bar above the baseline and the backlog bar below it at the same time, each with its label («Lager 6», «Restordre 4»), and the week table of Story 6.6 shows the rows Lager and Restordre above Netto lager for that Seat, on phone and on laptop (FR-23, UX-DR14)
**And** the numbers are the inventory and backlog fields of `seat_state`; the web app computes nothing (AD-3, AD-10)

**Given** a screen reader and narrow screens
**When** the band and the table render for a capped Seat
**Then** the band's text reads both numbers, the scale test of Story 6.9 passes with both bars at 320 and 360 px in every Uke of a capped fixture, and Playwright with axe at 320, 360 and 1440 px finds no violation (UX-DR15, FR-73, NFR-6)

**Covers:** FR-12, FR-23, FR-84, FR-73, NFR-6, AD-3, AD-10, AD-17, AD-19, UX-DR14, UX-DR15

## Epic 7: Lecturer overview, Game insight and Messages

A Lecturer or Assistant lecturer can follow every Class game of a Class session live on the Oversikt, open any Game week by week in Spillinnsikt, and send one-way Messages that reach Students in the product and by email. The epic owns the staff side of `api/app/modules/games/` (`game_summaries`, the overview and insight read endpoints) with `web/src/modules/games/` (staff screens), and all of `api/app/modules/messaging/` (Messages) with `web/src/modules/messaging/`. It adds the Matrisevegg and the staff charts to the shared `web/src/components/charts`, and the wall aggregates to the shared `analysis/`. Pause, Takeover and the other Spillstyring actions come in Epic 8; here the Varselbånd shows the longest-waiting Class game with «Send Melding» only.

### Story 7.1: See the status of every Class game on the Oversikt

As a Lecturer,
I want one page that lists every Class game in my Class session with its status, whom it waits for and its cost,
So that I can see at a glance which groups are playing and which are stuck.

**Acceptance Criteria:**

**Given** a Class session with Class games
**When** any existing `games.commands` command commits (`create`, `assign_seat`, `move_seat`, `start`, `view_week`, `place_order`, `advance`, `switch_to_rule_based`, `finish`)
**Then** the Game's row in `game_summaries` is updated in the same transaction with status, current Week, the Seats the game waits for and since when, the four occupants (occupant kind and `user_id`, never a name) and the running chain Total cost (AD-25, AD-2, AD-14)
**And** this story's Alembic migration creates `game_summaries` (owned by `modules/games`, one row per Game) and backfills a row for every existing Game
**And** an api test runs every command over a scripted Game and asserts after each one that the stored row equals a fresh recomputation from the game tables.

**Given** a Game and its open turns
**When** its status is needed anywhere
**Then** it comes only from `games.rules.game_status(game, turns)`, which this story adds as a pure function returning `not_started`, `running`, `waiting` or `finished` (Epic 8 adds `paused`), and `game_summaries` stores its result (AD-2, FR-39)
**And** `waiting` means that at least one Student has ordered in the open Week and at least one Student-held Seat has not; in a Guided Week, opening the Week counts as ordering (FR-24). The wait is counted from `wait_started_at` on the open turn, the column Story 6.14 added and `table_status` shows Students (FR-25), so staff and Students never see different waits.

**Given** a Lecturer or Assistant lecturer of the Class
**When** the web app calls `GET /api/class-sessions/{id}/overview`
**Then** it gets the compact summary list in the list envelope, the headline counts and `server_now`, read only from `game_summaries` with names resolved at read time, and an `ETag`; a repeat request with `If-None-Match` answers `304` (AD-25, AD-3)
**And** the list holds only Games for which `games.policy(purpose)` says the Lecturer overview applies, so a Lecturer's test Game or a simulation Game never appears (AD-13)
**And** a test with 100 Class games asserts that the endpoint runs a fixed number of queries, with none per Game (NFR-3).

**Given** a Student, a Lecturer of another Class, or an Admin who is not attached to the Class
**When** they open the Oversikt or call its endpoint
**Then** the route's `platform/authz` policy refuses, the page shows «Du har ikke tilgang til denne siden.» with a link to their own home, and the answer is the same whether or not the Class session exists (FR-5, AD-12, NFR-7).

**Given** a Lecturer on the Klasseøkt page
**When** they open the Oversikt
**Then** the page shows the headline counts in the form «41 ferdig · 15 pågår (herav 2 pauset) · 4 venter» (the «herav … pauset» part appears once Epic 8 adds Pause), «Oppdatert 14:02:15» in caption text, and the Class games grouped by status in the order Venter, Pågår, then «Ferdig, lavest kjedekost øverst», each group header with its count («Venter 4») (FR-39, UX-DR40)
**And** each row shows «Spill n», the current Uke number, whom the game waits for by name and Role with the duration, the four Seats with the Student's name or «KI-spiller», and the chain's kjedekost in Norwegian number format from the shared formatter
**And** progress is never shown as Uker played out of a total or as any number that hints at game length; the page shows the share of games finished and their status (FR-14).

**Given** the Start date has not passed, or a Class game has not started after it
**When** the Lecturer opens the Oversikt
**Then** before the Start date the wall area is empty and lists the allocation with no cost figures, and after it Class games that have not started are listed in their own group (copy to be written in `web/src/copy/nb.ts`)
**And** while the page loads it shows the Skjelett in the real layout, never a spinner.

**Given** the Oversikt at 1440 px, at 1280 px with 400 % zoom (320 CSS px) and with 200 % text
**When** the Playwright suite runs with axe
**Then** the page is one column below 1024 px, has no page-level horizontal scroll and no action out of view, passes axe, and takes all copy from `web/src/copy/nb.ts` (NFR-6, FR-72, FR-73).

**Covers:** FR-39, FR-5, FR-14, FR-72, FR-73, NFR-3, NFR-6, NFR-7, AD-2, AD-3, AD-12, AD-13, AD-14, AD-25, UX-DR40

### Story 7.2: Read all Class games week by week on the Matrisevegg

As a Lecturer,
I want every Class game drawn as one row of weekly cells,
So that I can see the same pattern building up across the whole class.

**Acceptance Criteria:**

**Given** a staff member of the Class
**When** the web app calls `GET /api/games/{id}/weeks`
**Then** it gets, per Week and Role, Netto lager, Ordre and Kost per uke as stored by the engine (units as integers, money as decimal strings), with an `ETag` tied to the Game's `version` (AD-25, AD-1)
**And** the web app fetches this per Game on demand and refetches only the Games whose `version` changed in the summary list; it computes no game quantity itself (AD-10).

**Given** the Oversikt with Class games
**When** the wall renders
**Then** the Matrisevegg shows one row per Class game and one column per Uke with Netto lager in the matrix steps (`net-neg-*`, `net-zero`, `net-pos-*`), square corners on all cells and no text under 9 px (UX-DR41, UX-DR4, UX-DR6)
**And** a row shows one Role's Netto lager; the component takes the Role as a prop, and the Oversikt passes Fabrikk until another Role is chosen ([ASSUMPTION] to confirm: Fabrikk is the default Role)
**And** the component is hand-made SVG added to `web/src/components/charts` with a fixed width passed in, for reuse by «Vis i plenum» in Epic 14 (AD-18).

**Given** a cell
**When** it is drawn
**Then** it prints its signed number («−13», «8», «0») when the number fits with 1 px to spare; otherwise a below-zero cell prints only a true minus «−», centred, and other cells stay blank
**And** text is `ink` on steps 1 and 2 and `paper` on steps 3 and 4, so sign is never carried by colour alone (NFR-6, UX-DR2).

**Given** the wall
**When** it is shown
**Then** the legend is always visible above it with the swatches in step order and the bins «−35 og lavere · −34 til −20 · −19 til −10 · −9 til −1 · 0 · 1 til 9 · 10 til 19 · 20 til 34 · 35 og over», and the line «− i en celle: restordre (under null).»

**Given** Class games in several statuses
**When** the wall renders
**Then** rows are grouped under headers such as «Venter 4», «Pågår 13» and «Ferdig, lavest kjedekost øverst 41», and finished games are ordered by lowest chain Total cost; the web app only groups and sorts rows it received (AD-10)
**And** each row label carries the game number, status, wait and kjedekost as text.

**Given** a Lecturer using the keyboard
**When** they move through the wall and the data re-renders
**Then** each row is focusable with `focus-ring-inset`, focus stays on the same Class game by Game id across every re-render, and the wall sits in one scroll region (`role="region"`, name «Alle spill», `tabindex="0"`) with the game column and the Uke header sticky (UX-DR8, UX-DR41).

**Given** the Landing from Epic 3, which left out its second figure because the Matrisevegg did not exist
**When** a visitor opens it
**Then** the Landing shows «Alle spillene på én skjerm» as the shared Matrisevegg component fed with static demo data bundled in the web app (no api call), labelled «Demodata» (UX-DR70)
**And** the figure shows no names, no week counts or Uke total, and nothing from a real Class session (FR-14, UX-DR71).

**Given** the test suites
**When** they run
**Then** Vitest covers the cell number-or-minus rule and the text-on-step rule, and Playwright with axe renders the wall at 1440 px and at 320 CSS px without page-level horizontal scroll.

**Covers:** FR-39, FR-14, FR-73, NFR-6, AD-1, AD-10, AD-18, AD-25, UX-DR41, UX-DR70

### Story 7.3: Switch the wall to «Vis som tabell»

As an Assistant lecturer,
I want the wall as a plain table with a number in every cell,
So that I can read exact values, sort the games and use a screen reader.

**Acceptance Criteria:**

**Given** the Oversikt
**When** it is shown
**Then** a Visningsbryter with the segments «Vegg» and «Vis som tabell» is always visible above the wall, built from the Valgknapper control of Epic 5 (active segment filled `ink` with `paper` text), operable by keyboard and announcing which view is chosen (UX-DR42).

**Given** the Lecturer chooses «Vis som tabell»
**When** the table renders
**Then** it lists every Class game with a signed number in every cell at 13 px or larger, as an HTML `<table>` with `th` scopes for the game column and the Uke header, using the same data as the wall (UX-DR42, UX-DR4)
**And** text never shrinks to fit; the table scrolls inside the same «Alle spill» region with the game column and Uke header sticky.

**Given** the table view
**When** the Lecturer activates a column header for game number, status, wait or kjedekost
**Then** the rows sort by it, the header carries `aria-sort`, and sorting by cost is offered on this staff surface only (UX-DR72).

**Given** a screen-reader user
**When** they reach the wall
**Then** the SVG wall is `aria-hidden` and points to «Vis som tabell» as its alternative, and the table reads each cell with its game and Uke (NFR-6, UX-DR76).

**Given** keyboard focus on a Class game
**When** the Lecturer switches between «Vegg» and «Vis som tabell», or the data updates
**Then** focus stays on the same Class game by Game id.

**Given** the Playwright suite with axe
**When** it runs at 1440 px, at 320 CSS px and with 200 % text
**Then** the table is the reading path at the narrow width, no cell text is below 13 px or clipped, and there is no page-level horizontal scroll (FR-73, UX-DR75).

**Covers:** FR-39, FR-73, NFR-6, AD-10, AD-18, UX-DR42

### Story 7.4: Filter the wall and compare with the class median

As a Lecturer,
I want to choose which Role, which cell value and which statuses the wall shows, with the class median above it,
So that I can compare one group with the whole class.

**Acceptance Criteria:**

**Given** the Oversikt
**When** it is shown
**Then** three Veggfiltre groups sit above the wall, Rolle, Celler (Netto lager / Ordre / Kost per uke) and Status with counts («Pause 2»), as text-button toggles with `aria-pressed`; the active one is weight 600 and underlined, with no pills or fills (UX-DR43)
**And** a filter applies at once to the wall and the table, and the counts update with it; the web app filters rows it already received and makes no request for them (AD-10).

**Given** the Celler filter shows Ordre or Kost per uke
**When** the wall redraws
**Then** the cells and the legend switch to the `flow-*` bins (UX-DR43).

**Given** the deferred decision on wall filter aggregates
**When** this story is built
**Then** the decision is: the overview response carries no aggregates, and one endpoint, `GET /api/class-sessions/{id}/overview/aggregates?role=&cells=&status=`, serves them for one filter combination at a time, with an `ETag`
**And** the values come from a pure function `analysis.wall_aggregates`, added to `api/app/analysis/` for reuse by the Class report, which takes stored Week states and returns per Uke the median row, the average chain cost row and the number of Games counted
**And** the decision is recorded in this story's record and noted against the spine's Deferred item «Wall filter aggregates».

**Given** Class games that have reached different Weeks
**When** the aggregates are computed
**Then** each Uke's value is taken over the Games that have reached that Uke, and golden tests cover an odd and an even number of Games, a single Game, and no Game (AD-1, NFR-9).

**Given** a filter combination
**When** the wall renders
**Then** the class median graph sits over the Matrisevegg on the same Uke columns, drawn by `web/src/components/charts`, and the wall's bottom rows hold the median for the chosen Role («Median, Fabrikk») and «Kjedekost/uke, snitt», each with its numbers printed in the same columns as the graph's marks (UX-DR40, UX-DR41)
**And** the web app renders these rows only from the endpoint's response and computes no median, average or cost (AD-10); a Vitest test renders them from a fixture response.

**Given** the Lecturer changes a filter
**When** the new aggregates are loading
**Then** the previous rows stay in place until the new ones arrive, with no spinner, and a failed request shows the inline action error without clearing the wall.

**Given** a User who is not staff of the Class
**When** they call the aggregates endpoint
**Then** the `platform/authz` policy refuses as in Story 7.1 (AD-12).

**Covers:** FR-39, NFR-6, NFR-9, AD-1, AD-10, AD-12, AD-18, AD-25, UX-DR40, UX-DR41, UX-DR43

### Story 7.5: Follow the games live with «Oppdater automatisk»

As a Lecturer,
I want the Oversikt to update by itself, and to be able to hold it still,
So that I see changes within seconds without the page moving under me.

**Acceptance Criteria:**

**Given** the Oversikt is open
**When** a command changes a listed Class game
**Then** the existing `session:<id>` event reaches the staff member's SSE stream, the mapping added for it in `web/src/lib/api/topics.ts` invalidates the overview queries, and the page shows the change within 5 seconds without a reload (FR-39, AD-8)
**And** an integration test places an Order and asserts the new value on the Oversikt inside 5 seconds with the 2-second coalescing on.

**Given** an invalidation
**When** the web app refetches
**Then** an unchanged list answers `304` and nothing re-renders, and week data is refetched only for Games whose `version` changed (AD-25).

**Given** the Oversikt
**When** it is shown
**Then** the Bryter «Oppdater automatisk» (reused from Epic 5) sits at the top right of the Matrisevegg with its state word, on by default, and «Oppdatert 14:02:15» stays visible in both states (UX-DR44).

**Given** «Oppdater automatisk» is off
**When** changes arrive
**Then** the wall, the table, the right rail and the headline counts stop changing, and a line «3 endringer siden 14:02» with the secondary button «Oppdater» shows what is waiting; pressing it applies the changes.

**Given** «Oppdater automatisk» is on and keyboard focus is inside the wall or the table
**When** changes arrive
**Then** values update in place, rows do not move or re-sort until focus leaves, and no update ever moves focus (UX-DR44, UX-DR76).

**Given** live updates
**When** the headline counts change
**Then** they are announced politely at most once a minute, and nothing else on the page is announced by this story.

**Given** no event and no heartbeat for 15 seconds (configuration, [ASSUMPTION] from the UX spine)
**When** the page notices
**Then** the Tilkoblingslinje shows «Ikke oppdatert siden 14:02. Prøver igjen.» with «Last inn på nytt», the wall keeps its last values and nothing is greyed out
**And** on reconnect the page refetches everything visible and shows «Tilkoblet igjen.» for 5 s (NFR-5, UX-DR58).

**Given** wait durations on the page
**When** time passes without an event
**Then** they tick from the response's `server_now`, and the page refetches at `next_change_at` where the response carries one; the browser clock never decides a status (AD-8).

**Covers:** FR-39, NFR-5, NFR-6, AD-8, AD-10, AD-25, UX-DR44

### Story 7.6: See who waits, the class's cost and the funnel in the right rail

As a Lecturer,
I want the waiting games, the cost distribution and the funnel beside the wall,
So that I know how far the class has come without opening a report.

**Acceptance Criteria:**

**Given** the Oversikt at 1024 px or wider
**When** it renders
**Then** a right rail holds «Venter ellers», «Klassens kostnad» and «Trakt»; below 1024 px the rail stacks under the wall, and its charts scale to the width and keep their printed numbers (UX-DR40, UX-DR75).

**Given** Class games in status waiting
**When** the rail renders
**Then** «Venter ellers» lists them, longest wait first, each with game number, the Student and Role waited for and the duration, read from the summary list; with none waiting it shows a line saying so (copy to be written in `nb.ts`).

**Given** finished Class games
**When** «Klassens kostnad» renders
**Then** the Kostnadsfordeling shows one tick per finished game, a box for the middle half and the labelled median («Median 1 954»), drawn by `web/src/components/charts`
**And** the median and the quartiles come from the api (a pure function in `analysis`, returned with the overview response); the web app computes none (AD-10)
**And** a text summary sits under it («Median 1 954. Midterste halvdel 1 500–2 600.») with «Vis som tabell» (Spill, kjedekost, sorted) (UX-DR51)
**And** the «Fjoråret» mark is not drawn in this epic; Epic 14 adds it when aggregates of earlier Class sessions exist.

**Given** no Class game has finished
**When** the rail renders
**Then** «Klassens kostnad» shows a line saying so instead of an empty chart (copy to be written in `nb.ts`), and before the Start date the cost block is not shown at all.

**Given** the Class session
**When** «Trakt» renders
**Then** it shows the FR-39 stages in order (registered, Class game finished, Debrief done, Debrief quiz passed, Replay done, Individual test submitted, AI assessment ready) with each count printed as a list item; the bars are `aria-hidden` (UX-DR51)
**And** the counts come from `progress.service.funnel(class_session_id, student_ids)`, added in this story: it counts the step events of the Students it is given, cached per Class session and invalidated by `progress.record_step` (AD-25, AD-16)
**And** the overview service passes the ids of the registered Students of the Class session, so `progress` still imports no feature module (AD-16)
**And** a stage whose step no module records yet shows 0, so later epics fill the funnel only by recording their steps.

**Given** a Student finishes a step
**When** `progress.record_step` commits
**Then** the funnel cache is invalidated, `session:<id>` is emitted, and the Trakt shows the new count within 5 seconds under the rules of «Oppdater automatisk».

**Given** the funnel
**When** it is computed
**Then** it reads step events only and takes no AI score or AI text as input (AD-16, C-2), and it counts no Lecturer's test Game or simulation Game (AD-13).

**Covers:** FR-39, NFR-6, AD-10, AD-13, AD-16, AD-18, AD-25, UX-DR40, UX-DR51

### Story 7.7: Open one Game week by week in Spillinnsikt

As a Lecturer,
I want to open any Game and see every Week for every Seat,
So that I can explain to a group what happened and check who played each Week.

**Acceptance Criteria:**

**Given** the Oversikt
**When** the Lecturer activates a wall row or a table row (click or Enter)
**Then** Spillinnsikt opens for that Game, with the game number, its status and the four Seats in chain direction (upstream on the left), each with the Student's name or «KI-spiller», and Back returns to the Oversikt with focus on the same game (UX-DR55, UX-DR73).

**Given** a Game with played Weeks
**When** Spillinnsikt renders
**Then** it shows, per Week and per Seat, incoming order, incoming delivery, inventory, backlog, Order and cost (FR-62), in per-Role tables from Detaljist to Fabrikk that scroll inside their own region with sticky labels
**And** every number is the stored engine value from the Week states and `seat_week`; the web app does no arithmetic (AD-1, AD-10, NFR-9).

**Given** `seat_week` rows with different occupants
**When** the tables render
**Then** each Week shows who played the Seat (Student or AI player), marks Weeks played by an AI player, marks a Takeover and a Play guard or cost-limit switch from `reason`, and marks an Order replaced by the fallback from `fallback`, always in text and never by colour alone (FR-62, FR-34)
**And** all marks come from the one AD-15 mapping of `decided_by`, `fallback`, `occupant_kind` and `reason` in `games` `service.py`, the function Story 6.14 added with the `guard_switch` mark; this story extends it, not adds a second one, with the marks for every other `reason` and `fallback` value (AD-15)
**And** an api test feeds fixture rows for every `reason` and `fallback` value, including the Takeover reasons Epic 8 will write, and asserts the mark for each.

**Given** a staff member of the Game's Class
**When** they call the insight endpoint
**Then** it answers through a `platform/authz` policy and scope helper for any Game they may see (a Class game now, a Replay once Epic 10 creates them), and only this staff endpoint serves the full chain, the demand series and the number of Weeks (AD-3, AD-12)
**And** a Student who calls it gets the permission-denied answer that does not reveal whether the Game exists (FR-5).

**Given** a Class game that has not started, or one that is running
**When** Spillinnsikt is open
**Then** a game not started shows «Spillet har ikke startet.» with the four Seats, and a running game refetches on `game:<id>` so a new Week appears without a reload (AD-8).

**Given** FR-62's links to Explanations and Debrief summaries
**When** Spillinnsikt renders before Epic 9 exists
**Then** each Student-held Seat has a link slot fed by a `links` list in the insight response, which is empty in this epic and shows that nothing is available yet (copy to be written in `nb.ts`); Epic 9 fills the list without changing the page
**And** the list is filled from link providers registered with `games` `service.py` (`register_insight_links(provider)`, the same pattern as the pin providers of Story 5.11), so `modules/games` imports no later module; no provider is registered in this epic.

**Given** the Playwright suite with axe
**When** it runs at 1440 px and at 320 CSS px
**Then** only the per-Role tables scroll sideways, each inside its own region, and the page passes axe (FR-73, NFR-6).

**Covers:** FR-62, FR-34, FR-5, FR-73, NFR-6, NFR-9, AD-1, AD-3, AD-8, AD-10, AD-12, AD-15, UX-DR55

### Story 7.8: See all four Roles' Orders, inventory and backlog as charts in Spillinnsikt

As a Lecturer,
I want charts of every Role's Orders, inventory and backlog next to customer demand,
So that I can show a group how the swings grew up the chain.

**Acceptance Criteria:**

**Given** Spillinnsikt of Story 7.7 for a Game with played Weeks
**When** the charts render
**Then** Spillinnsikt shows charts of Orders, inventory and backlog for all four Roles plus customer demand, with Fabrikk at the top, each with «Vis som tabell» under it (FR-62, UX-DR55)
**And** every number in the charts comes from the insight endpoint of Story 7.7; the web app computes none, and the charts of a running game refetch with the page on `game:<id>` (AD-10).

**Given** the Orders chart
**When** it renders
**Then** it is Ordrestolper: one row per Role with Fabrikk at the top, bars in `order-history`, the first order of 10 or more marked with a dot and «Uke n» and joined by a diagonal, a place for Forsterkning at the right, and the Rolle × Uke table underneath in the same columns in the `flow-*` steps (UX-DR33).

**Given** the Debrief of Epic 9 needs the same chart
**When** this story builds Ordrestolper and the Rolle × Uke table
**Then** they are built in the shared `web/src/components/charts`, with a fixed width passed in and a prop for the viewer's own Role (unset for staff), so Epic 9's Debrief reuses them unchanged and adds only the four-Role Kjedebånd and the Ukeskrubber (AD-18)
**And** Forsterkning is shown when the caller supplies it, which Epic 9 does from `analysis`.

**Given** the Playwright suite with axe
**When** it runs Spillinnsikt with its charts at 1440 px and at 320 CSS px
**Then** only the Rolle × Uke tables and the order bars scroll sideways, each inside its own region, and the page passes axe (FR-73, NFR-6).

**Covers:** FR-62, FR-73, NFR-6, AD-10, AD-18, UX-DR33, UX-DR55

### Story 7.9: Send a Message to a Student, a Class game or the whole Class session

As an Assistant lecturer,
I want to write one Message and send it to a Student, a group or everyone,
So that I can nudge the right people without leaving the product.

**Acceptance Criteria:**

**Given** a staff member on the Oversikt or Spillinnsikt
**When** they follow «Send Melding» in the Oversikt header (whole Class session), «Melding» on Spillinnsikt (that Class game), or the link beside a Student's Seat (that Student)
**Then** the Meldingsskjema opens as its own page with the recipient preset as its title (for example «Melding til Noah, Spill 2»), a multi-line Tekstfelt and the primary «Send Melding», and browser Back returns to where it was opened (FR-40, UX-DR46)
**And** the Meldingsskjema is built in `web/src/modules/messaging/` so Epics 8, 13 and 14 can open it with a preset recipient.

**Given** the Meldingsskjema
**When** the text is empty
**Then** «Send Melding» is unavailable with `aria-disabled` and keeps focus if it had it; there is no reply field and no way to add free recipients (UX-DR46, UX-DR8).

**Given** a written Message
**When** the staff member presses «Send Melding»
**Then** `messaging.service.send_message` stores one `messages` row and one `message_recipients` row per Student in one transaction, calls `platform/notify.enqueue(user_id, kind="message", dedupe_key, ref)` for each recipient, and emits `session:<id>` (AD-9, AD-8)
**And** this story's migration creates the two tables, owned by `modules/messaging`; they hold the text, the Class session, `user_id`s and times, and no copied names or emails (AD-14).

**Given** the three recipient kinds
**When** recipients are resolved
**Then** one Student means that Student; a Class game means every Student assigned to a Seat in it, including one whose Seat an AI player now holds; a Class session means every registered Student of it; AI players and unregistered Roster addresses get nothing
**And** a fourth kind, an explicit list of Students passed by a calling module through `messaging` `service.py`, exists so Epic 13 can preset the Students who have not met the requirement (UX-DR46).

**Given** a sent Message
**When** `messaging` claims its notices
**Then** the kind `message` is registered as `immediate` in the delivery table that Story 3.5 built, and its mail pipeline defers a `mail` job per recipient right after commit, with ids only as arguments; this story builds no delivery of its own (AD-9)
**And** the mail is rendered from a Norwegian Jinja2 template in `api/app/platform/email/templates/`, headed «ØL-spillet», with the Message text and a link to Hjem (FR-72, AD-19); locally it goes to the mock mailer (AD-17).

**Given** a successful send
**When** the page updates
**Then** the result line «Meldingen er sendt til 4 studenter.» with the real count replaces the form and takes focus, and the form shows «Sendt tidligere: 3» with the number of earlier Messages to the same recipient.

**Given** a failed or repeated send
**When** the request fails
**Then** «Det ble ikke lagret. Prøv igjen.» shows inline with `role="alert"`, the text is kept and the button stays active
**And** a repeat of the same request (double press or retry) never sends the Message twice, because the request carries a client-made key that `messages` holds unique
**And** a text over the maximum length (configuration, placeholder 2 000 characters) is refused with a stable error code and the limit shown.

**Given** a Student, or staff of another Class
**When** they call the send endpoint
**Then** the `platform/authz` policy refuses; Lecturers and Assistant lecturers of the Class may both send (FR-40, AD-12)
**And** Playwright with axe renders the Meldingsskjema at 1440 px, at 1280 px with 400 % zoom and with 200 % text, as one column with no page-level horizontal scroll.

**Covers:** FR-40, FR-72, NFR-6, NFR-7, AD-8, AD-9, AD-12, AD-14, AD-17, AD-19, UX-DR46

### Story 7.10: Read Messages in the product

As a Student,
I want to read Messages from my Lecturer on Hjem,
So that I do not miss a notice if I have not opened my email.

**Acceptance Criteria:**

**Given** a Student who has received Messages
**When** they open Hjem
**Then** the Messages are listed newest first, each with the sender's name, the time in Europe/Oslo and the full text (headings and labels to be written in `web/src/copy/nb.ts`), and the list reflows at 320 and 360 px (FR-40, FR-73).

**Given** a Student with Hjem open
**When** a Message is sent to them
**Then** `platform/notify.enqueue` has emitted `user:<id>`, the topic mapping added in `web/src/lib/api/topics.ts` refetches the list, and the Message appears without a reload, announced politely and without moving focus (AD-8).

**Given** a Student
**When** they call the Messages endpoint
**Then** a scope helper returns only Messages addressed to them, and no Message to another Student or another Class game is ever returned (FR-5, AD-12).

**Given** any Student-facing surface
**When** a Message is shown
**Then** there is no reply, reaction or forward control, and the endpoint set has no route for a Student to write a Message (FR-40, C-5, UX-DR78).

**Given** a Message text with line breaks, links or markup characters
**When** it is shown in the product or in the mail
**Then** it is rendered as plain text with line breaks kept and everything else escaped (NFR-7).

**Given** a staff member of the Class
**When** they open «Meldinger» for the Class session
**Then** they see every sent Message with recipient, sender, time and the number of Students it went to, newest first, with a link back to the Meldingsskjema for the same recipient.

**Given** the Playwright suite with axe
**When** it runs Hjem with Messages at 320, 360 and 1440 px
**Then** there is no horizontal scroll, text is 13 px or larger on phone, and the page passes axe (NFR-6).

**Covers:** FR-40, FR-5, FR-72, FR-73, NFR-6, NFR-7, AD-8, AD-12, AD-19

### Story 7.11: Act on the longest-waiting game from the Varselbånd

As a Lecturer,
I want the game that has waited longest shown in one band at the top with a Message one press away,
So that the band is the only thing I have to act on.

**Acceptance Criteria:**

**Given** at least one Class game in status waiting
**When** the Oversikt renders
**Then** the Varselbånd shows the game that has waited longest (the oldest `wait_started_at`, the column of Story 6.14), in the form «Spill 2 venter på Noah (Grossist) i 23 t.», as a full-width `restordre-fill` band with `ink` text, and its primary «Send Melding» opens the Meldingsskjema preset to the Student waited for (FR-39, FR-40, UX-DR45)
**And** the overview response names that game, chosen in the api; the web app does not pick it. Epic 8 changes the choice to the game closest to Takeover and adds the countdown and its other actions.

**Given** no Class game waits
**When** the Oversikt renders
**Then** no band is shown, and the page has no primary button in its place.

**Given** the wall and the table
**When** they render
**Then** every row has a «Melding» link that opens the Meldingsskjema preset to that Class game, and the band's game row is tinted `restordre-fill` with `ink` text and an `ink` underlined «Melding» (UX-DR41, UX-DR2)
**And** time stamps and reasons inside the band are `ink` or `ink-secondary`, never `ink-muted` or `restordre`.

**Given** several waiting games
**When** the rail renders
**Then** the band's game is left out of «Venter ellers», which lists the others (UX-DR45).

**Given** the Oversikt below 1024 px, or at 320 CSS px
**When** it renders
**Then** the band's text comes first and its action wraps under it at full width and stays in view (UX-DR45, UX-DR75).

**Given** live updates
**When** the band appears or changes to another game
**Then** it is announced politely at most once a minute and never moves focus; with «Oppdater automatisk» off the band does not change until «Oppdater» is pressed (UX-DR44).

**Given** an Assistant lecturer
**When** they open the Oversikt
**Then** they see the same band with «Send Melding», and the Playwright suite with axe checks the band at 1440 px and 320 CSS px (NFR-6).

**Covers:** FR-39, FR-40, NFR-6, AD-10, AD-25, UX-DR41, UX-DR44, UX-DR45

## Epic 8: Every game finishes: Pause, Takeover and deadlines

A missing Student never blocks a group: the game records its own clock, an AI player takes over after the Inactivity limit, Students can pause and put an AI player in an absent Seat, and a Student can take the Seat back. The Lecturer can start, pause, mark as in the room and fill Seats for one Class game or all of them, and can give one Student more time. At the Play deadline every unfinished Class game is played to its last Week. In a Guided Week, opening the Week counts as ordering (FR-24), so all of this also works there. The epic owns the turn side of `api/app/modules/games/` (the timing columns on `seat_turns`, `games.rules.turn_times` and `can_take_over`, and the commands `takeover`, `request_reclaim`, `pause`, `resume`, `set_agreed_time`, `mark_in_room`, `end_in_room`, `recompute_turn_times` and `playout`) and the Takeover, in-room, reminder and playout due actions in `api/app/modules/ops/`; its screens extend the Student play screen and the staff screens in `web/src/modules/games/`.

### Story 8.1: Record when each Week opened and when each Seat ordered

As a Lecturer,
I want the product to record when every Week opened for a Seat and when its Order came,
So that waiting, Takeover and reminders all run on one clock and I can see how long each decision took.

**Acceptance Criteria:**

**Given** a Week opens in a Game
**When** the advancing command commits
**Then** each Seat has one `seat_turns` row for the open Week with `opened_at`, written only by `games.commands` (FR-35, AD-20)
**And** this story's migration adds the columns `takeover_due_at` and `insert_allowed_at` to `seat_turns`; the row already has `opened_at`, `ordered_at` and the Rule-based reference Order (Story 1.8), `ai_deadline_at` (Story 2.6), the near-optimal reference Order (Story 2.9), `wait_started_at` (Story 6.14) and `viewed_at` (Story 6.10).

**Given** an open Week in a Class game
**When** the first Student places an Order while another Student-held Seat has not ordered, and Story 6.14 sets `wait_started_at` on the Seats that have not ordered
**Then** the same transaction sets their `takeover_due_at` and `insert_allowed_at` from `wait_started_at`, which is the FR-36 clock start, and the Inactivity limit in the Game's `SessionRuntime` (FR-36, AD-4)
**And** while no Student has ordered in the Week, those three columns stay empty.

**Given** a Guided Week, where Story 6.10 places every Seat's fixed Order when the Week opens and a Student only opens the Week
**When** any story of this epic says that a Seat "has ordered" or "has not ordered"
**Then** in a Guided Week it means that `viewed_at` on the Seat's `seat_turns` row is set or empty: the clock starts at the first Student `viewed_at`, and `view_week` sets the due times as `place_order` does in other Weeks (FR-24, FR-36, FR-37)
**And** the tests of this story cover a Guided Week and a free Week.

**Given** any command that changes an input to the times
**When** it runs
**Then** the times are computed only by the pure function `games.rules.turn_times(game, seat, inputs)`, which Story 2.6 added with the AI-deadline input and Story 6.14 extended with the clock start; this story extends it with the other FR-36 inputs: the Inactivity limit, a per-Student adjustment, an agreed Pause time and an in-room limit (the last three are empty until later stories of this epic)
**And** table-driven unit tests cover the function, and an api test asserts that no other code writes these columns (AD-20).

**Given** a Seat places its Order
**When** `place_order` commits
**Then** `ordered_at` is set and the row's times and reference Orders are copied into the write-once `seat_week` row, which is never updated afterwards (FR-35, AD-15).

**Given** a Game whose `games.policy(purpose)` says inactivity Takeover does not apply (a Replay, a Lecturer's test Game, a simulation Game)
**When** its Weeks open
**Then** `opened_at` and `ordered_at` are recorded and no due time is set (AD-13).

**Given** the play screen, Hjem, the Oversikt and the Varselbånd
**When** they show how long a game has waited for a Seat
**Then** they show the stored times, the play envelope and the overview response carry `server_now` and `next_change_at` (the nearest due time), and nothing else derives a wait or a due time (AD-20, AD-8).

**Given** Spillinnsikt from Story 7.7
**When** a staff member reads a Game
**Then** each Week and Seat also shows when the Week opened, when the Order came and the time between, in Europe/Oslo time, in the same per-Role tables (FR-35).

**Covers:** FR-35, FR-36, FR-24, AD-2, AD-4, AD-8, AD-13, AD-15, AD-20

### Story 8.2: An AI player takes over after the Inactivity limit

As a Student who has ordered,
I want an AI player to take the Seat of someone who does not order within the Inactivity limit,
So that my group is never stuck on one absent player.

**Acceptance Criteria:**

**Given** a Student-held Seat with no Order whose `takeover_due_at` has passed, in a running Class game
**When** the per-minute `ops.sweep` of Story 3.5 runs
**Then** its new Takeover due action finds the turn and calls `games.commands.takeover(game, seat, actor=system)`, one item per transaction (AD-9)
**And** the command, added in this story, locks the Game row, checks `games.rules.can_take_over(game, seat, actor, now)` (also added here, the only eligibility check), appends an occupancy row with reason `takeover_inactivity` from this Week, calls `players.ensure_order` in the same transaction, increments `version` and emits `game:<id>`, `session:<id>` and `user:<id>` for each affected Student, with its registry entry (FR-36, FR-30, AD-2, AD-5, AD-8)
**And** the new occupant is `llm` or `rule_based` by the Class session's AI mode, and `rule_based` if the Seat was switched by the Play guard or the cost-limit state is set.

**Given** the deferred decision on the actor of an occupancy row
**When** this story is built
**Then** the occupancy history gains a nullable `actor_user_id`, added by this story's migration: empty for `initial`, `takeover_inactivity`, `guard_switch`, `cost_limit` and `playout`, and set by the later stories of this epic to the staff member for `takeover_staff`, the Student who pressed for `takeover_peer` and the Student for `reclaim`
**And** the row holds the id only, names are resolved at read time, and the decision is recorded in this story's record and noted against the spine's Deferred item «Remaining Spillstyring commands and sweeps» (AD-14, AD-15).

**Given** a Week in which no Student has ordered, or a Game whose `games.policy(purpose)` says inactivity Takeover does not apply
**When** any amount of time passes before the Play deadline
**Then** nothing happens: there is no clock, no Takeover, and no AI player plays the Class game on its own (FR-36, AD-13); an api test leaves a game idle for several days and asserts no occupancy row.

**Given** the sweep runs twice, or the Student orders at the same moment
**When** the commands race on the Game row lock
**Then** at most one occupancy row is appended; an Order the Student committed first stands and the Takeover is skipped; an Order the Student sends after the Takeover answers `409 seat_not_yours` (AD-2)
**And** a clock-controlled integration test shows the Takeover within one minute of `takeover_due_at`, so no ordered Student waits longer than the Inactivity limit plus the sweep interval (NFR-4).

**Given** a Guided Week in which one Student has opened the Week and another has not, past the absent Seat's `takeover_due_at` (Story 8.1)
**When** `takeover` commits, whoever triggers it
**Then** the occupancy row applies from this Week, the Seat keeps the fixed Order that Story 6.10 placed, and `games.rules.week_complete` is re-evaluated at once: when it is now true the Game advances exactly one Week through `games.commands.advance`, the command Story 2.1 added and every `games.commands` entry point calls (FR-24, FR-36, FR-37, AD-2)
**And** an api test covers it: one Student never opens Week 1, the Takeover happens at the due time, and the Week advances.

**Given** a Takeover has happened
**When** the other Students look at Setestatus on Spill or Hjem
**Then** the Seat's row reads «Fabrikk  KI-spiller  bestiller for Jonas» (with the Seat's own Role), announced politely, and the Seat keeps the label «KI-spiller» everywhere Seats are shown (FR-34, UX-DR69)
**And** a Seat whose LLM player the Play guard has switched shows on the same Setestatus row that it now uses a rule-based player (copy to be written in `nb.ts`), also when the switch outlasts a Takeover or a Reclaim (FR-34, FR-79, UX-DR69).

**Given** the Student whose Seat was taken over
**When** they open Spill or Hjem
**Then** they see «KI-spiller har bestilt for deg.» (UX-DR62)
**And** when the Class session is Obligatorisk, a warning says the Takeover may affect the requirement; its wording never reveals the number of Weeks, in the product or in the Takeover notice mail (FR-17, FR-14)
**And** the copy lives in `web/src/copy/nb.ts` and the mail template, and the CI copy check covers both: it fails if the warning holds a number or a reference to how many Uker the game has or has left. This is the only place the warning is built; Epic 13 does not repeat it.

**Given** a Takeover
**When** the command commits
**Then** it calls `platform/notify.enqueue` with kind `takeover_notice` for the Student and for each other Student in the Class game, with ids only and a dedupe key per Seat and Week (FR-36, AD-9)
**And** the kind is registered as `immediate` in the delivery table of Story 3.5, so the mail is sent at once, also between 22:00 and 07:00, from a Norwegian Jinja2 template headed «ØL-spillet».

**Covers:** FR-36, FR-30, FR-34, FR-79, FR-17, FR-14, FR-24, FR-37, NFR-4, AD-2, AD-5, AD-8, AD-9, AD-13, AD-14, AD-15, AD-19, AD-20, UX-DR62, UX-DR69

### Story 8.3: See on the Oversikt which Class game is closest to Takeover

As a Lecturer,
I want the Oversikt to show the game that an AI player will take over next, and where one has taken over,
So that I can reach the Student before it happens and see afterwards that it did.

**Acceptance Criteria:**

**Given** the Oversikt from Epic 7
**When** a Class game approaches Takeover
**Then** `game_summaries` gains the Game's nearest `takeover_due_at`, the Varselbånd now shows the game closest to Takeover with the countdown («Spill 2 venter på Noah (Grossist) i 23 t. KI overtar om 1 t.»), and the tinted wall row follows it (FR-39, UX-DR45, UX-DR41)
**And** the overview response names that game, chosen in the api by the earliest `takeover_due_at`; this replaces the longest-wait choice of Story 7.11, and «Venter ellers» lists the other waiting games (AD-10, AD-25).

**Given** a due time is reached and no command runs
**When** the sweep crosses it
**Then** the sweep emits the Game's events so the page refetches, and the countdown ticks from `server_now` and is refetched at `next_change_at`; the browser clock never decides it (AD-8, AD-20).

**Given** a Takeover of Story 8.2 has happened
**When** staff look at the Oversikt and Spillinnsikt
**Then** the wall row and Spillinnsikt mark the Seat as «KI-spiller» with the Takeover and its reason, in text, through the AD-15 mapping of Story 7.7, and the game leaves the Varselbånd, which moves on to the next game (FR-36, FR-34, FR-39)
**And** `takeover` updates the occupants and the due time in the Game's `game_summaries` row in its own transaction and joins the recomputation test of Story 7.1 (AD-25).

**Given** the Playwright suite with axe
**When** it runs the Oversikt with a game one hour from Takeover and with a game just taken over, at 1440 px and 320 CSS px
**Then** the band text with its countdown wraps without page-level horizontal scroll and the page passes axe (NFR-6).

**Covers:** FR-39, FR-36, FR-34, NFR-6, AD-8, AD-10, AD-20, AD-25, UX-DR41, UX-DR45

### Story 8.4: Take the Seat back with «Ta tilbake setet»

As a Student whose Seat an AI player took over,
I want to take my Seat back from the next Week,
So that I can keep playing and count toward the requirement.

**Acceptance Criteria:**

**Given** a Student whose Seat is held by an AI player after a Takeover, in an unfinished Class game
**When** they open Spill or Hjem
**Then** «Ta tilbake setet» is shown under «KI-spiller har bestilt for deg.», with a tap target of at least 44 px (UX-DR62, UX-DR76).

**Given** the Student presses «Ta tilbake setet»
**When** `games.commands.request_reclaim(game, seat, user)` commits
**Then** the Reclaim is stored as a queued request and changes no occupancy yet; the button is replaced by a line saying the Seat returns when the next Uke opens (copy to be written in `nb.ts`), which takes focus (FR-37, AD-2)
**And** a second press, or a repeat of the request, changes nothing.

**Given** a queued Reclaim
**When** the command that completes the Week opens the next one
**Then** the same transaction appends an occupancy row with occupant `student`, reason `reclaim` and the Student in `actor_user_id` (the column of Story 8.2), from the new Week; the Student's new `seat_turns` row starts with no clock running; and `game:<id>` and `user:<id>` are emitted (FR-37, AD-5)
**And** the Game's `game_summaries` row is updated in the same transaction, and `request_reclaim` joins the recomputation test of Story 7.1 (AD-25).

**Given** Weeks the AI player ordered in
**When** the Student has the Seat back
**Then** their `seat_week` rows are unchanged, Spillinnsikt still marks them as AI Weeks, and every reader counts them as not ordered by the Student through the one AD-15 mapping (FR-37, AD-15).

**Given** a Seat the Play guard switched before the Student took it back
**When** the Student later loses the Seat again
**Then** the new occupant is a Rule-based player, because the switch outlasts the Reclaim (FR-37, FR-79).

**Given** another Student, or a User who never held the Seat
**When** they call the reclaim endpoint
**Then** it answers `409 seat_not_yours`, and for a finished Class game the control is not shown and the request is refused with a stable error code (AD-12).

**Given** the Playwright suite with axe
**When** it runs the taken-over state at 320, 360 and 1440 px
**Then** the warning, the button and the result line reflow without horizontal scroll and pass axe (NFR-6, FR-73).

**Covers:** FR-37, FR-79, FR-73, NFR-6, AD-2, AD-5, AD-12, AD-15, AD-25, UX-DR62

### Story 8.5: Put an AI player in one Seat from Spillstyring

As an Assistant lecturer,
I want to put an AI player in any Student's Seat with one press,
So that a group in my Lab hour can go on when one of them has left.

**Acceptance Criteria:**

**Given** a started, unfinished Class game on Spillinnsikt
**When** a Lecturer or Assistant lecturer opens it
**Then** a block titled «Spillstyring» sits under the four Seats, and each Student-held Seat row has the secondary button «Sett inn KI-spiller for Jonas» with its consequence directly above it: «KI-spilleren bestiller for Jonas fra denne Uka. Jonas kan ta setet tilbake fra neste Uke.», or «KI-spilleren bestiller for Jonas fra neste Uke.» if Jonas has ordered this Uke (FR-37, UX-DR52)
**And** a finished game shows no Spillstyring actions, and below 1024 px every action is full width.

**Given** a staff member presses the button
**When** `games.commands.takeover(game, seat, actor)` commits
**Then** there is no dialog; the occupancy row has reason `takeover_staff` with the staff member in `actor_user_id` (the column of Story 8.2); the AI player orders from this Week through `players.ensure_order` if the Seat has not ordered, and from the next Week if it has; and the Students see the same rows, warning and notices as in Story 8.2 (FR-37, AD-5)
**And** in a Guided Week "has not ordered" means the Student has not opened the Week (Story 8.1): the Takeover then applies from this Week and the Week advances under the rule of Story 8.2, shown by an api test in which one Student never opens Week 1 and a staff member presses the button (FR-24, FR-37)
**And** names are resolved at read time, the Oversikt and Spillinnsikt mark each Takeover with who triggered it, and every Takeover by a person goes through `platform/audit.record(actor, action, target, change)` (FR-3, AD-14, AD-15).

**Given** the deferred decision on conflict errors
**When** a Takeover or Spillstyring command loses a race
**Then** it answers `409` with a stable code (`takeover_exists`, `already_paused`, `not_paused`, `already_started`, `seat_not_student_held`, `insert_not_allowed_yet`) and `fields.acted_by` (`kind` of `student`, `staff` or `system`, and the `user_id`) with `fields.acted_at`
**And** the web app maps the code to copy that names who acted first, taking the name from the refreshed view, and no name is written to a log line
**And** the decision is recorded in this story's record and noted against the spine's Deferred item «Remaining Spillstyring commands and sweeps».

**Given** a successful press
**When** the page updates
**Then** the result line «KI-spiller satt inn for Jonas.» replaces the button and takes focus (`tabindex="-1"`), and a failure shows the inline action error with the button still active (UX-DR52, UX-DR76).

**Given** the Varselbånd from Epic 7
**When** a Class game is closest to Takeover (Story 8.3)
**Then** the band adds the secondary «Sett inn KI-spiller for Noah» with its consequence line in caption text under the band text, wrapped under the text below 1024 px (UX-DR45).

**Given** an Assistant lecturer
**When** they open Spillinnsikt or the Oversikt
**Then** they get the per-Seat «Sett inn KI-spiller for …» and, in the band, «Send Melding» and «Sett inn KI-spiller for Noah» only; no other Spillstyring action is shown to them, and the api refuses those through `platform/authz` (AD-12, UX-DR45, UX-DR52).

**Given** the Playwright suite with axe
**When** it runs Spillinnsikt with Spillstyring at 1440 px and 320 CSS px
**Then** there is no page-level horizontal scroll and the page passes axe (NFR-6).

**Covers:** FR-37, FR-3, FR-30, FR-24, NFR-6, NFR-7, AD-2, AD-5, AD-12, AD-14, AD-15, AD-19, AD-20, UX-DR45, UX-DR52

### Story 8.6: Pause the Class game with «Ta pause»

As a Student,
I want to pause our Class game when the group agrees to stop for now,
So that no AI player takes anyone's Seat while we are away.

**Acceptance Criteria:**

**Given** a Student in a started, unfinished Class game that is not paused
**When** they look under Setestatus on Spill or Hjem
**Then** the secondary button «Ta pause» is shown; it is not shown in a Replay or any Game whose `games.policy(purpose)` says Pause does not apply (FR-89, UX-DR26, AD-13).

**Given** the Student presses «Ta pause»
**When** the Pausevalg opens in place
**Then** it has no date or time field, shows the lines «Mens spillet har pause, tar ingen KI-spiller over setene. Spillfristen flyttes ikke.» and «Bare faglæreren kan avtale et tidspunkt. Uten det har hver av dere sin vanlige ventetid før en KI-spiller kan settes inn.», the primary «Ta pause uten avtalt tid» and the link «Avbryt»
**And** focus moves to the primary button, and «Avbryt» returns focus to «Ta pause» (UX-DR26, UX-DR76).

**Given** the Student confirms
**When** `games.commands.pause(game, actor)` commits
**Then** it writes `paused_at` and `paused_by` and leaves `resume_at` empty (this story's migration adds the three Pause columns to the Game), leaves `lifecycle` unchanged, and emits its events with a registry entry (AD-2, AD-8)
**And** `games.rules.game_status` now returns `paused`, `game_summaries` gains the pause state, and the Oversikt shows the game under «Pause 2» with since when and by whom, counts it in «herav 2 pauset», and drops it from the Varselbånd at once (FR-89, FR-39, UX-DR45).

**Given** a paused Class game
**When** any of the four Students opens Spill or Hjem
**Then** the line «Pause, satt av Sara.» sits above Setestatus, announced politely, and nothing in it hints at how many Uker remain (UX-DR62, FR-14).

**Given** a paused Class game with a Seat past its `takeover_due_at`
**When** the sweep runs
**Then** `can_take_over` refuses the automatic Takeover, the stored due times are not moved because the clock keeps running, and the Play deadline is unchanged (FR-36, FR-89).

**Given** a paused Class game
**When** any Student places an Order
**Then** `place_order` clears the Pause columns in the same transaction, whoever started the Pause, and the line becomes «Pausen er over. Sara har bestilt.» (FR-89, AD-2)
**And** a Seat whose `takeover_due_at` had already passed is taken over at the next sweep, within one minute.

**Given** two people pause at the same moment
**When** the second command reaches the Game row lock
**Then** it answers `409 already_paused` with who acted first (Story 8.5), and the second person simply sees the pause line.

**Given** the Playwright suite with axe
**When** it runs the Pausevalg, the paused state and the pause-ended state at 320, 360 and 1440 px
**Then** they reflow without horizontal scroll and pass axe (NFR-6, FR-73).

**Covers:** FR-89, FR-36, FR-39, FR-14, FR-73, NFR-4, NFR-6, AD-2, AD-8, AD-13, AD-20, AD-25, UX-DR26, UX-DR45, UX-DR62

### Story 8.7: Pause a Class game with an agreed time as Lecturer

As a Lecturer,
I want to pause a Class game and set the time the group has agreed to continue,
So that everyone knows when to be back and what happens after that.

**Acceptance Criteria:**

**Given** a started, unfinished Class game that is not paused
**When** the Lecturer presses the secondary «Pause spillet» in Spillstyring or in the Varselbånd
**Then** a form opens in place (under the band when opened there): «Når fortsetter spillet?» with date and time from now to the Spillfrist, or the choice «Uten avtalt tid»; the lines «Mens spillet har pause, tar ingen KI-spiller over setene. Spillfristen flyttes ikke.» and «Etter avtalt tid kan studentene sette inn en KI-spiller for den som ikke har bestilt.»; the primary «Ta pause til to. 19:00» (or «Ta pause uten avtalt tid»); and «Avbryt» (FR-89, UX-DR52)
**And** only one in-place form is open at a time, and while the form is open under the band «Send Melding» shows as secondary, so the screen keeps one primary button (UX-DR9, UX-DR45).

**Given** a time outside the range
**When** the Lecturer leaves the field or presses the button
**Then** «Velg et tidspunkt mellom nå og Spillfristen, {dato}.» shows in the Ordrefelt error pattern, and the api applies the same rule and refuses with a stable error code (AD-10, AD-19).

**Given** a valid form
**When** the Lecturer confirms
**Then** `games.commands.pause(game, actor, resume_at)` writes the Pause columns; on a game that is already paused, also one a Student paused, «Endre avtalt tid» opens the same form prefilled and calls `set_agreed_time`, and «Avslutt pausen» calls `resume`, which clears the Pause columns (FR-89, AD-2)
**And** each of the three commands recomputes `insert_allowed_at` for the open turns through `games.rules.turn_times`, so the agreed time becomes the insert time of every Student-held Seat that has not ordered this Uke (AD-20).

**Given** a Pause the Lecturer set or gave a time
**When** the Students open Spill or Hjem
**Then** they see «Pause, satt av faglæreren.» or «Pause til to. 19:00, satt av faglæreren.», and only a Lecturer's agreed time ever appears in a pause line (UX-DR62).

**Given** a paused Class game on Spillinnsikt
**When** the Lecturer views it
**Then** it reads «Pause siden ma. 14:10, satt av Sara.» or «… satt av deg.», with the agreed time if any, then «Endre avtalt tid» and «Avslutt pausen»; after a save the result line «Pause til to. 19:00 er satt.» replaces the form and takes focus (UX-DR52).

**Given** a Student or an Assistant lecturer
**When** they try to set an agreed time, or an Assistant lecturer tries to pause or end a pause from Spillstyring
**Then** the Student pause route accepts no time, the staff routes refuse through `platform/authz`, and the controls are not shown to them (FR-89, AD-12).

**Given** the agreed time is reached
**When** the sweep crosses it
**Then** the Pause does not end by itself and no automatic Takeover runs; the sweep emits the Game's events so every view refetches and the right to put in an AI player can appear (AD-8, AD-9)
**And** every pause, time change and pause end by a Lecturer is recorded through `platform/audit.record` (AD-15).

**Covers:** FR-89, FR-39, NFR-6, AD-2, AD-8, AD-9, AD-10, AD-12, AD-15, AD-19, AD-20, UX-DR45, UX-DR52, UX-DR62

### Story 8.8: Put an AI player in an absent Seat as a Student

As a Student,
I want to put an AI player in the Seat of someone who has not come back when their time has run out,
So that the rest of us can go on, also while the game is paused.

**Acceptance Criteria:**

**Given** a Student-held Seat that has not ordered this Uke, while a Pause runs or an agreed time is set
**When** the other Students look at its Setestatus row before the insert time
**Then** with an agreed time the row reads «Avtalt tid to. 19:00. Etter det kan dere sette inn en KI-spiller.», and without one, once the FR-36 clock runs, «Etter on. 10:00 kan dere sette inn en KI-spiller.» with the Seat's own insert time
**And** the row never says why one Seat's time is later than another's (UX-DR27).

**Given** the one eligibility rule
**When** `table_status` is built for a viewer
**Then** it marks the control as available only while all three hold: a Student holds the Seat and has not ordered this Uke (in a Guided Week: has not opened it, Story 8.1); the Seat's `insert_allowed_at` has passed; and no Takeover of the Seat is done or queued. The api decides this through `games.rules.can_take_over`, and the web app only shows it (AD-20, AD-10)
**And** a running Pause is not a condition: the control shows to every other Student in the game, on Spill and Hjem, until the Seat orders, a Takeover happens or the Uke advances.

**Given** the control is available
**When** it is shown
**Then** the consequence «KI-spilleren bestiller for Jonas fra denne Uka. Jonas kan ta setet tilbake fra neste Uke.» sits directly above the secondary button «Sett inn KI-spiller for Jonas», full width under the row on phone (UX-DR27).

**Given** a Student presses the button
**When** `games.commands.takeover(game, seat, actor)` commits
**Then** there is no dialog; `can_take_over` requires that the actor holds another Seat in the same Game and that `insert_allowed_at` has passed, and otherwise answers `409 insert_not_allowed_yet`; the route's policy checks only that the actor is in the Game (AD-12, AD-20)
**And** the occupancy row has reason `takeover_peer` with the pressing Student in `actor_user_id`, `players.ensure_order` runs in the transaction, the action is audit-logged, the Oversikt marks who triggered it, and the notices of Story 8.2 are sent (FR-89, FR-37, FR-3)
**And** in a Guided Week the Takeover applies from this Week and the Week advances under the rule of Story 8.2 (FR-24).

**Given** a successful press
**When** the screen updates
**Then** the button is replaced by the row «Fabrikk  KI-spiller  bestiller for Jonas» and focus moves to that row's text (`tabindex="-1"`); the absent Student gets «KI-spiller har bestilt for deg.», «Ta tilbake setet» and the requirement warning (UX-DR27, UX-DR62).

**Given** two Students press at the same moment
**When** the second command reaches the Game row lock
**Then** it answers `409 takeover_exists` with who acted first, the pressed button is gone, and focus moves to «Sara har allerede satt inn en KI-spiller.» on that Setestatus row (UX-DR27).

**Given** any Student
**When** they use the product
**Then** no route or parameter lets a Student set or shorten an insert time, and an `insert_allowed_at` that has already passed is kept when an Order ends the Pause, so the right survives the end of the Pause (FR-89).

**Given** the sweep crosses an `insert_allowed_at`, and the Playwright suite with axe
**When** each runs
**Then** the sweep emits the Game's events so the control appears without a reload, and the before, available and done states pass at 320, 360 and 1440 px (AD-8, NFR-6, FR-73).

**Covers:** FR-89, FR-37, FR-3, FR-34, FR-24, FR-73, NFR-6, AD-2, AD-5, AD-8, AD-10, AD-12, AD-15, AD-20, UX-DR27, UX-DR62

### Story 8.9: Give one Student more time with Tilrettelegging

As a Lecturer,
I want to give a Student with a right to it more time before an AI player takes the Seat, and a lower share of Weeks,
So that the time limits never shut that Student out.

**Acceptance Criteria:**

**Given** a Lecturer on Spillinnsikt
**When** they follow a Student's name
**Then** a Studentside for that Student opens with the block «Tilrettelegging» only, built as a page of blocks in `web/src/modules/reports/` with its route under the Class session, so Story 13.2 extends the same page with its own blocks; it reads «Ingen tilrettelegging.» or the summary «Mer tid: 2 ×. Andel uker: 60 %.», with the secondary «Endre tilrettelegging» (UX-DR53)
**And** the block and its api are for Lecturers only; an Assistant lecturer does not see it and is refused through `platform/authz` (AD-12).

**Given** the Lecturer presses «Endre tilrettelegging»
**When** the form opens in place
**Then** it shows «Mer tid før KI tar over» as Valgknapper «Som klassen», «1,5 ×», «2 ×», «3 ×»; «Andel uker som kreves» as a whole percentage from 0 to the class share with the help line «Klassen: 80 %.» and the error «Skriv et helt tall fra 0 til 80.»; the line «Gjelder bare Jonas, fra nå. Ingen andre studenter ser det. Endringen logges.»; the primary «Lagre tilrettelegging»; and «Avbryt»
**And** the class share («Klassen: 80 %.») is the Class session's required share of Weeks, read through `sessions.service.required_share(class_session)` of Story 5.7; this story does not create it (FR-17)
**And** there is no field for a reason, so no health data is stored (UX-DR53, C-1).

**Given** a valid form
**When** the Lecturer saves
**Then** `sessions` `service.py` stores the factor and the share in `student_adjustments`, created by this story and owned by `modules/sessions`, keyed by Class session and `user_id`; records the change through `platform/audit.record`; and emits `user:<id>` and `session:<id>` (FR-17, AD-8, AD-14, AD-15)
**And** other modules read the time factor and the share only through `sessions` `service.py` (`get_adjustment(class_session, user)`): `games` for the turn times here, Epic 11 for the factor on a timed sitting, and Epic 13 for the share of Weeks
**And** the api refuses a factor under 1 or a share above the class share, so an adjustment only ever extends; it can be changed at any time, also after the Start date, as one of the live reads AD-4 allows.

**Given** the Student holds a Seat with an open turn
**When** the adjustment is saved
**Then** the new command `games.commands.recompute_turn_times(game)` recomputes the open rows through `games.rules.turn_times` in the same request: the factor multiplies the Inactivity limit for `takeover_due_at` and `insert_allowed_at`, and an agreed Pause time never gives that Seat an insert time earlier than its own extended limit on the FR-36 clock (FR-17, FR-89, AD-20)
**And** while no FR-36 clock runs for the Seat (no Student has ordered this Uke), there is no extended limit to hold against, so an agreed Pause time stands as that Seat's insert time ([ASSUMPTION] to confirm)
**And** automatic Takeover and the Varselbånd's «KI overtar om …» follow the new times at once, and unit tests cover each factor with and without an agreed time, and with and without a running clock.

**Given** the Student concerned
**When** they open Hjem
**Then** they see, under Stegene, «Du har mer tid før en KI-spiller tar setet ditt (2 × vanlig ventetid).» and, if the share is adjusted, «For deg er kravet 60 % av ukene.»
**And** no other Student sees these lines or any badge; the others only ever see a later insert time (UX-DR53).

**Given** a Seat with Tilrettelegging in Spillstyring
**When** a Lecturer looks at its per-Seat action
**Then** the line «Jonas har tilrettelegging med mer tid.» is added for the Lecturer only (UX-DR52).

**Given** a successful save
**When** the page updates
**Then** «Lagret. Gjelder fra nå.» and the summary replace the form and take focus; the stored share is kept for `analysis.completion` in Epic 13, and this story computes no Completion status (AD-16).

**Given** the Playwright suite with axe
**When** it runs the block and the form at 1440 px and 320 CSS px
**Then** the form is one column with no page-level horizontal scroll and passes axe (NFR-6).

**Covers:** FR-17, FR-36, FR-89, NFR-6, AD-4, AD-8, AD-12, AD-14, AD-15, AD-16, AD-20, UX-DR52, UX-DR53

### Story 8.10: Start one Class game or all of them as Lecturer

As a Lecturer,
I want to start one Class game, or every game that has not started, in one action,
So that a whole room can begin at the same time in a Lab hour.

**Acceptance Criteria:**

**Given** a Class game that has not started and has its settings snapshot, which the lock at the Start date gives it (the same readiness Story 6.5 uses for the Student's button)
**When** the Lecturer opens Spillinnsikt
**Then** Spillstyring shows the primary «Start spillet» with «Spillet starter for alle fire. Reglene for ventetid gjelder fra nå.» above it; before the Start date, and for a Game the lock has not reached yet, no start action is offered anywhere (FR-22, UX-DR52).

**Given** the Lecturer presses «Start spillet»
**When** `games.commands.start` commits with the Lecturer as actor
**Then** the existing `start` command, which this story extends with an `actor` argument, stores `started_by` and `started_at` on the Game (columns added here; a Student's start from Story 6.5 stores the Student) (AD-2)
**And** the game starts for all four Seats, the result line «Spillet er startet.» replaces the action and takes focus, the Students see the started game through the command's events, and the start is recorded through `platform/audit.record` (FR-22, AD-2, AD-15).

**Given** Class games that have not started and have their settings snapshot
**When** the Lecturer opens the Oversikt
**Then** the header has the Lenke «Start spill som ikke har startet (12)» with the real count; with a count of 0 the Lenke is not shown (UX-DR52).

**Given** the Lecturer follows the Lenke
**When** the «Start spill» page opens
**Then** it lists the games not started, shows the line «Spillene starter for alle i dem. Reglene for ventetid gjelder fra nå.» and the primary «Start 12 spill», and Back returns to the Oversikt.

**Given** the Lecturer presses «Start 12 spill»
**When** the service runs
**Then** it loops over the listed Games with one `start` command per Game, each in its own transaction; a Game that was started in the meantime, or that answers `409 game_not_ready` because it has no settings snapshot yet (Story 5.9), is skipped; a failure in one Game does not stop the others; and the response gives the real count (AD-2)
**And** the Oversikt shows «12 spill er startet.» with that count, and a test starts 100 Class games in one action.

**Given** a Student pressed start first
**When** the Lecturer's single start reaches the Game row lock
**Then** it answers `409 already_started` with who acted first, read from `started_by` and `started_at` in the error shape of Story 8.5, and the page shows the running game with a line naming who started it (copy to be written in `nb.ts`).

**Given** an Assistant lecturer or a Student
**When** they call either start route
**Then** `platform/authz` refuses, and the actions are not shown to an Assistant lecturer (AD-12).

**Covers:** FR-22, NFR-7, AD-2, AD-12, AD-15, AD-19, UX-DR52

### Story 8.11: Mark a Class game as «I rommet» during a Lab hour

As a Lecturer,
I want to mark a Class game as played in the room with a short waiting time,
So that a group sitting together in a Lab hour is not held up for a day by one person.

**Acceptance Criteria:**

**Given** a started, unfinished Class game
**When** the Lecturer opens Spillstyring
**Then** while a Lab hour of this Class session is on, the secondary «Marker som i rommet» is active; outside a Lab hour it is shown unavailable with `aria-disabled` and «Kan bare brukes i en Labtime.» (FR-36, UX-DR52, UX-DR8).

**Given** the Lecturer presses «Marker som i rommet»
**When** the form opens in place
**Then** it shows «Ventetid i rommet» in whole minutes with default 10, the line «Studentene i spillet ser den kortere ventetiden. Den gjelder til Labtimen slutter kl. 16:00.», the primary «Marker som i rommet, 10 min» and «Avbryt»
**And** a value outside 2 to 120 minutes shows an error in the Ordrefelt error pattern (copy to be written in `nb.ts`), and the api applies the same range (FR-36).

**Given** a valid form
**When** `games.commands.mark_in_room(game, minutes, actor)` commits
**Then** it stores the in-room limit and `in_room_until` (the Lab hour's end) on the Game (columns added by this story), recomputes the open turns through `games.rules.turn_times` with the in-room limit times each Student's Tilrettelegging factor, and is recorded through `platform/audit.record` (AD-2, AD-15, AD-20)
**And** the api refuses the command outside a Lab hour with a stable error code
**And** `game_summaries` gains the in-room mark, updated in the same transaction by `mark_in_room` and `end_in_room`, and both commands join the recomputation test of Story 7.1 (AD-25).

**Given** a Class game marked as in the room
**When** the Students open Spill
**Then** all four see «I rommet til kl. 16:00. En KI-spiller tar setet etter 10 min uten ordre.» above Setestatus, announced politely when it starts and when it ends, and each Student's line shows that Student's own minutes (UX-DR62, UX-DR53).

**Given** a Seat that has not ordered for the in-room limit after another Student ordered
**When** the sweep runs
**Then** the automatic Takeover of Story 8.2 happens within one minute, which stays inside the 2-minute floor for in-room limits (FR-36, AD-9, NFR-4).

**Given** the deferred decision on ending «I rommet»
**When** this story is built
**Then** a person ends it with «Ikke i rommet lenger», which calls the new command `games.commands.end_in_room(game, actor)`, and the Lab hour's end ends it through a new due action in the `ops.sweep` of Story 3.5 that calls the same command with the system as actor when `in_room_until` has passed
**And** the command clears the mark and recomputes the open turns back to the Class session's Inactivity limit from the same clock start; a Lab hour that is moved or removed updates or ends the marks through `games` `service.py`
**And** `end_in_room` is added to the AD-2 command list and the in-room end to the AD-9 sweep list, and the decision is recorded in this story's record.

**Given** a marked Class game
**When** staff view it
**Then** Spillstyring reads «I rommet til 16:00. KI tar over etter 10 min uten ordre.» with the secondary «Ikke i rommet lenger», the game's wall row label carries «I rommet», and after marking the result line «I rommet til 16:00.» replaces the form and takes focus (UX-DR52).

**Given** an Assistant lecturer or a Student
**When** they call the mark or end route
**Then** `platform/authz` refuses, and the action is not shown to an Assistant lecturer (AD-12).

**Covers:** FR-36, FR-17, NFR-4, NFR-6, AD-2, AD-9, AD-12, AD-15, AD-20, AD-25, UX-DR52, UX-DR53, UX-DR62

### Story 8.12: Fill every waited-for Seat in one action

As a Lecturer,
I want to put AI players in all the Seats the games wait for, in one Class game or in all of them,
So that I can clear every stuck group at the start of a Lab hour.

**Acceptance Criteria:**

**Given** a started, unfinished Class game with waited-for Seats
**When** the Lecturer opens Spillstyring
**Then** the secondary «Sett inn KI-spiller i alle seter som blir ventet på (2)» is shown with its consequence above it (FR-37, UX-DR52)
**And** a waited-for Seat is a Student-held Seat whose open turn has `wait_started_at` set (Story 6.14) and no Order, or in a Guided Week no `viewed_at`; this is the one predicate `games.rules.waited_for(turn)`, added here and used by `games.rules.game_status` for `waiting`, so this count and the «Venter» count of the Oversikt cannot disagree (FR-24, AD-20).

**Given** waited-for Seats in the Class session
**When** the Lecturer opens the Oversikt
**Then** the header has the Lenke «Sett inn KI-spiller i alle seter som blir ventet på (9)» with the real count, not shown when the count is 0
**And** its page lists the Seats per game with name and wait («Spill 2: Noah, 23 t»), the Seats left out under «Ikke med (tilrettelegging): Jonas», the line «Studentene kan ta setene tilbake fra neste Uke.» and the primary «Sett inn 9 KI-spillere»; Back returns to the Oversikt.

**Given** the deferred decision on batch Takeover
**When** the Lecturer presses the primary button
**Then** the request carries the Seat ids that were listed, and the service loops over their Games with one `takeover` command per Seat, each in its own transaction under the Game row lock
**And** a Seat that has ordered since, is no longer Student-held, or now has Tilrettelegging is skipped; a failure in one Game does not undo or stop the others; a repeat of the request inserts nothing twice
**And** the response is `{inserted, skipped: [{seat_id, reason}]}` with real counts, and the decision is recorded in this story's record.

**Given** the action is done
**When** the page updates
**Then** the result reads «2 KI-spillere satt inn.» on Spillinnsikt or «9 KI-spillere er satt inn.» on the Oversikt, with the real number, and takes focus.

**Given** each Seat that was filled
**When** its command commits
**Then** the occupancy row has reason `takeover_staff` with the Lecturer as actor, `players.ensure_order` runs, the Takeover is audit-logged, and the Students get the rows, warning and notices of Story 8.2; in a Guided Week the Takeover applies from this Week and the Week advances under the rule of Story 8.2 (FR-3, FR-24, AD-5, AD-15).

**Given** an Assistant lecturer
**When** they open Spillstyring or the Oversikt
**Then** neither fill action is shown and the api refuses them; the per-Seat action of Story 8.5 still reaches every Seat, also one with Tilrettelegging (AD-12).

**Given** an api test with 100 Class games
**When** the batch runs while some Seats order between the listing and the press
**Then** those Seats are skipped and reported, the counts match the occupancy rows written, and one Game made to fail leaves the others filled.

**Covers:** FR-37, FR-3, FR-17, FR-24, NFR-3, AD-2, AD-5, AD-12, AD-15, AD-20, UX-DR52

### Story 8.13: Get an email when the game waits for your Order

As a Student,
I want one email a day telling me that my Class game waits for my Order,
So that I do not hold my group up without knowing it.

**Acceptance Criteria:**

**Given** a Class game that has waited for a Student's Order for the reminder delay (in a Guided Week: for the Student to open the Week, Story 8.1)
**When** the per-minute `ops.sweep` of Story 3.5 runs its new reminder due action
**Then** it calls `platform/notify.enqueue(user_id, kind="turn_reminder", dedupe_key, ref, not_before)` with a dedupe key per User, Game and Week and ids only (FR-27, FR-24, AD-9)
**And** the due time is a column, `reminder_due_at` on `seat_turns`, added by this story's migration and written by `games.commands` from `games.rules.turn_times`; the delay is configuration with a placeholder of 2 hours, taken from FR-27's assumption and to be confirmed by the founder.

**Given** the kind `turn_reminder`
**When** `messaging` delivers it
**Then** it is registered as `digest` in the digest delivery of Story 3.5, which gathers it with the User's other digest notices into at most one mail per User per day and never sends between 22:00 and 07:00 Europe/Oslo; this story builds no delivery of its own (FR-27, AD-9)
**And** a clock-controlled test with this kind shows that a reminder due at 23:10 is sent after 07:00, and that two waiting games give one mail.

**Given** a queued reminder
**When** the Student orders, the Seat is taken over, or the game finishes before the mail is built
**Then** the reminder is dropped and the mail does not mention that game.

**Given** a Week in which no other Student has ordered, a paused Class game, or a Game whose `games.policy(purpose)` has no inactivity rules
**When** time passes
**Then** no reminder is queued (FR-36, AD-13); not reminding during a Pause is an [ASSUMPTION] to confirm.

**Given** a reminder mail
**When** it is rendered
**Then** it comes from a Norwegian Jinja2 template in `api/app/platform/email/templates/`, headed «ØL-spillet», says that the game waits for the Student's Order with a link to Hjem, and holds no number of Uker, no customer demand and no other Seat's numbers (FR-72, FR-14, AD-19).

**Given** FR-27's superseded assumption
**When** a Takeover comes close
**Then** there is no second reminder "4 hours before Takeover"; the only immediate mail around a Takeover is the Takeover notice of Story 8.2.

**Covers:** FR-27, FR-14, FR-24, FR-72, NFR-10, AD-9, AD-13, AD-19, AD-20

### Story 8.14: Finish every unfinished Class game at the Play deadline

As a Lecturer,
I want every Class game that is not finished at the Play deadline to be played to its last Week by AI players,
So that every Student can go on to the Debrief.

**Acceptance Criteria:**

**Given** the Play deadline of a Class session has passed
**When** the per-minute `ops.sweep` of Story 3.5 runs its new playout due action
**Then** for every unfinished Game where `games.policy(purpose)` applies the playout, it calls `games.commands.playout(game)`, one Game per transaction, reading the live Play deadline of the Class session, so an extension made before the deadline holds and a Pause never moves it (FR-38, AD-9, AD-13, AD-4)
**And** games that were never started and games that are paused are played out too; for a Game that was never started, `playout` first runs the `start` logic in the same transaction, with the system as actor
**And** a Game that has no settings snapshot, because the lock never succeeded, answers `409 game_not_ready` there: the sweep skips it and logs an error with the Game id, so the playout of the other Games does not fail on it.

**Given** `playout` runs for a Game
**When** it commits
**Then** it sets `lifecycle = playing_out`, clears any Pause and in-room mark, drops queued Reclaims, and appends an AI occupant with reason `playout` to every Seat a Student holds, as `rule_based` where the Play guard switched the Seat or the cost-limit state is set (AD-2, AD-5)
**And** the Game's `game_summaries` row is updated in the same transaction, and `playout` joins the recomputation test of Story 7.1 (AD-25)
**And** a second call for the same Game changes nothing.

**Given** a Game in `playing_out`
**When** its Weeks are played
**Then** `players.ensure_order` places Guided and Rule-based Orders in the transaction and defers LLM Orders to `llm-batch` with no `ai_deadline_at`, so the rescue loop skips them; a typed failure gives the Rule-based Order; the sweep re-enqueues a playout turn that has no Order and no live job (FR-32, AD-5)
**And** the Game advances one Week per completed Week until the last Week has run in full and `finish` runs (FR-28).

**Given** a Class game finished by playout
**When** `finish` commits
**Then** it runs the same finished-game check Story 6.18 added for a game that ends normally: the engine is replayed at the stored `rules_version` over the stored Orders and must reproduce the stored Week states, with units conserved and cost totals matching, and any violation is logged as an error (FR-29, AD-4, NFR-9)
**And** `finish` records the `class_game` step for every Student ever assigned to a Seat of the Game, as Story 6.18 built it from the occupancy history; an api test plays a game out and asserts that the check ran and passed, and that a Student whose Seat was played out and a Student whose Seat was taken over earlier and never reclaimed both have the step, so the Trakt counts them (FR-38, AD-16).

**Given** a person acts on the Game after `playout`
**When** they call `place_order`, `pause`, `takeover` or `request_reclaim`
**Then** the command answers `409 play_deadline_passed`; an Order committed before `playout` stands, and an api test races an Order against `playout` on the Game row lock and asserts one consistent outcome (AD-2).

**Given** a Student whose Class game ended by playout
**When** they open Spill or Hjem
**Then** they see «Spillet er ferdig» with a note that it ended at the Spillfrist (copy to be written in `nb.ts`), the chain's Total cost and the cost per Role as in Epic 6, and are led on with «Gå til Debrief» (FR-38, FR-28, UX-DR62)
**And** the note holds no blame and does not say how many Uker were played by AI players.

**Given** the playout has run
**When** staff open the Oversikt and Spillinnsikt
**Then** the games move to «Ferdig», the Trakt moves, and Spillinnsikt marks the playout Weeks from `reason = playout`; those Orders have `decided_by` of `llm` or `rule_based`, so every reader counts them as not ordered by the Student (FR-17, AD-15, AD-25).

**Given** a Class session with 100 unfinished Class games on the mock provider
**When** the playout test runs
**Then** no Class game is left unfinished (FR-38, NFR-4, NFR-3)
**And** the time allowed for the playout to finish is configuration with a placeholder, an open input set after the prototype (spine, Deferred); a Game still in `playing_out` after it is logged as an error with its Game id.

**Covers:** FR-38, FR-28, FR-29, FR-32, FR-17, NFR-3, NFR-4, NFR-9, AD-2, AD-4, AD-5, AD-9, AD-13, AD-15, AD-16, AD-25, UX-DR62

## Epic 9: Debrief and Debrief quiz

When this epic is done, the Students of a finished Class game can write their Explanations, see the reveal, the whole chain and their own moments, answer reflection questions and pass the Debrief quiz, alone or together with a shared screen. The Debrief is built code-only first, so it works under any AI mode and with no LLM; narration and follow-up are added on top through the AI gateway. The epic owns `api/app/modules/debrief/` and `web/src/modules/debrief/`, adds the quiz, sentence templates and Detected pattern definitions to `modules/content`, and adds the shared facts, validator and renderer to `analysis/`, `ai/` and `modules/games` (`fact_sets`).

### Story 9.1: Compute the facts of a finished Game

As a founder,
I want every finished Game to have one stored set of computed facts per Seat,
So that every number and cause shown after a Game comes from the Decision log and can be checked.

**Acceptance Criteria:**

**Given** a finished Game with its `seat_week` rows
**When** `analysis.facts(decision_log, seat, pattern_definitions)` is called
**Then** it returns a facts set for that Seat with ids, values and Roles only: the Order amplification per Role (standard deviation of the Seat's Orders divided by that of customer demand over the whole Game), the first Week with an Order of 10 or more per Role, cost per Role and cost type, the share of chain Total cost incurred in AI-held Seats, and the count of the Seat's Orders with `decided_by = student` (FR-44, AD-7, AD-15)
**And** the function is pure: no I/O, no clock, no randomness (AD-1)

**Given** the three Detected patterns of the PRD glossary (an Order well above incoming orders after a shortage, a large Order while the Supply line already holds a lot, very low Orders after an overshoot)
**When** the story is done
**Then** each pattern is an immutable versioned record in `modules/content` with an exact definition, its thresholds as parameters and its mechanism (delay, Supply line, demand information lost in orders), worded as a pattern and not a cause (AD-23)
**And** the thresholds are placeholders marked "to be reviewed by two lecturers before pilot" (FR-44), and the Class session's pattern version is pinned by `sessions.lock` as a new entry in `SessionRuntime`'s open map of pinned content versions, with no change to the lock's mechanism; the later stories of this epic add their entries (sentence templates, reflection questions, quiz, the AI-text switch) the same way (AD-4, AD-23)

**Given** a Seat's Decision log
**When** the facts are built
**Then** every Detected pattern occurrence gets the deterministic id `<pattern>:<role>:<week>` and carries the Week, what the Seat saw (`state_seen`), the Order, the cost over the following Weeks and what the other three Roles saw in that Week (FR-44, AD-7)
**And** for a Seat with at least 10 Orders with `decided_by = student`, at least three own moments are selected by a documented rule over the Decision log, also when fewer than three pattern occurrences exist, and only from Weeks where `decided_by = student`
**And** a Seat with fewer than 10 such Orders gets an empty moment list and the flag that leaves the Student out of SM-1 and SM-2, which is what the golden Game played fully by Rule-based players shows (FR-44)

**Given** a finished Game and a Seat
**When** `games.facts.get_or_create(game, seat)` is called twice
**Then** the first call stores one row in `fact_sets(id, game_id, seat_id, analysis_version, payload)` and the second returns the same row; the payload holds no names (AD-7, AD-14)
**And** the chain-level part of the payload is identical for all four Seats of the Game, checked by a test

**Given** the addendum §B reference trace and at least two further golden Games (one with a Takeover, one played fully by Rule-based players)
**When** the pytest suite runs
**Then** golden tests fix the facts set for each, every number in the set equals the value recomputed from the `seat_week` rows, and branch coverage of the new `analysis` code is reported with full coverage as the aim (NFR-9)

**Given** a finished `purpose=simulation` Game
**When** the founder runs `python -m app.sim facts <game_id>`
**Then** the facts set of each Seat is printed as JSON, so the patterns can be reviewed on simulated Games before any Student sees them (AD-22)

**Covers:** FR-44, NFR-9, AD-1, AD-7, AD-14, AD-15, AD-22, AD-23

### Story 9.2: Open the Debrief when the Class game has ended

As a Student,
I want the Debrief to open when my Class game has ended,
So that I can start reviewing while the game is fresh.

**Acceptance Criteria:**

**Given** a Student whose game, read through `games.service.student_game(user, class_session)` (Story 6.1), has `lifecycle = finished`, and a Class session with open Debriefs (the default)
**When** the Student presses «Gå til Debrief» on «Spillet er ferdig» or opens the Debrief step in Stegene
**Then** `debrief.commands.open` creates the Debrief session for that Game if none exists, with its step pointer at step 1, and the Student lands on step 1 (FR-42, AD-21)
**And** every Debrief story of this epic finds a Student's game only through `games.service.student_game`, never by querying Class games directly, so the Debrief follows whatever game that function returns
**And** «Gå til Debrief» on «Spillet er ferdig», which Story 6.18 pointed at Hjem, is repointed to the Debrief in this story
**And** `debrief.commands` is the only writer of the Debrief session tables, each command locks the Debrief row and emits `debrief:<id>`, and the registry test in `platform/events/registry.py` covers `open` (AD-8, AD-21)

**Given** a Student whose Class game is still running
**When** the Student requests any Debrief endpoint
**Then** the API answers `403 debrief_not_open` and returns no demand series, number of Weeks or other Seats' data (AD-3, FR-14)
**And** Stegene lists the Debrief step as locked with the text that states what opens it

**Given** a Lecturer on the Klasseøkt screen before the Start date
**When** the Lecturer opens the Debrief block
**Then** a Valgknapper control offers open Debriefs (default) and holding all Debriefs until every Class game has ended, with help text explaining that open Debriefs can reveal the Demand pattern to Students still playing (FR-42, UX-DR12)
**And** the choice applies on «Lagre Klasseøkt», is read-only after the Start date, and is stored on the Class session by `modules/sessions`

**Given** a Class session set to hold Debriefs, and at least one `purpose=class` Game not finished
**When** a Student of a finished Class game requests the Debrief
**Then** the API answers `403 debrief_held`, the check being one function `debrief.rules.available(user, class_session)` that reads Game status through `games.service` (AD-25)
**And** «Spillet er ferdig» and Stegene state that the Debrief opens when all Class games have ended, without naming how many remain

**Given** a held Class session whose last `purpose=class` Game finishes (by the last Week or the playout)
**When** the next `ops.sweep` runs
**Then** a new due action, added to the sweep of Story 3.5, marks the Class session's Debriefs as released, once, and calls `platform/notify.enqueue` for every Student with a Seat, which emits `user:<id>` so Hjem updates without reload (AD-9, AD-8)
**And** the action is idempotent and its arguments are ids only

**Given** the Debrief pages
**When** Playwright runs at 320, 360 and 1440 px with axe
**Then** the open, locked and held states pass, all copy comes from `web/src/copy/nb.ts`, and the Debrief routes are typed from the generated API client (NFR-6, AD-10, AD-19)

**Covers:** FR-42, FR-14, AD-3, AD-8, AD-9, AD-21, AD-25, UX-DR12, UX-DR31

### Story 9.3: Write the Explanation before the reveal

As a Student,
I want to write my own Explanation of what happened before I see customer demand,
So that my account is my own and is kept as I wrote it.

**Acceptance Criteria:**

**Given** a Student on Debrief step 1
**When** the step shows
**Then** the heading is «Skriv Forklaringen først», the chart «Ditt netto lager, hele spillet» is drawn from the Student's own Decision log in their game (`games.service.student_game`) by `web/src/components/charts` with «Vis som tabell» (Uke, Netto lager), the prompt is «Hvorfor svingte lageret ditt?» and the primary button is «Send Forklaring» (UX-DR31, AD-18)
**And** the chart shows only the Student's own Seat and no customer demand

**Given** a Student typing an Explanation
**When** the connection drops, the page reloads or the session expires
**Then** the text is restored from `web/src/lib/drafts.ts` and is never sent without a press on «Send Forklaring» (AD-10)

**Given** a Student who presses «Send Forklaring» with text
**When** `debrief.commands.save_explanation` runs
**Then** the Explanation is stored once, unchanged, keyed by `user_id` and Class session, with its length and time, and a second save answers `409 explanation_exists` (FR-41, AD-14)
**And** `progress.record_step(user, class_session, explanation, at)` is called in the same transaction (AD-16)

**Given** a Student with no saved Explanation
**When** the Student requests step 2 or later, the demand series, or another Seat's Orders, inventory or backlog
**Then** the API answers `403 explanation_required`; the gate is checked in the API and not only in the UI (FR-41, FR-43, AD-21)
**And** an api test calls every Debrief data endpoint without a saved Explanation and asserts that none returns demand or another Seat's Orders, inventory or backlog
**And** the number of Weeks is not gated: once the game is finished it is no longer hidden, since «Spillet er ferdig» (Story 6.18) and the step 1 chart already show every Uke of the game (FR-14)

**Given** an empty Explanation field
**When** the Student presses «Send Forklaring»
**Then** the button is `aria-disabled`, the Tekstfelt shows its reason beside it, and a failed save shows «Det ble ikke lagret. Prøv igjen.» with the text kept (UX-DR11, UX-DR59)

**Given** another Student of the same Class game, an Assistant lecturer of the Class, and an Admin not attached to the Class
**When** each requests the Explanation
**Then** the other Student and the Admin are refused and the Assistant lecturer can read it, through `platform/authz` policies (FR-41, FR-5, AD-12)

**Given** step 1
**When** Playwright runs at 320, 360 and 1440 px with axe and at 360 px with 200 % text
**Then** the step is fully keyboard-operable and has no page-level horizontal scroll (FR-73, NFR-6)

**Covers:** FR-41, FR-5, FR-14, FR-73, AD-10, AD-12, AD-14, AD-16, AD-18, AD-21, UX-DR11, UX-DR31

### Story 9.4: See the reveal of customer demand

As a Student,
I want to see what the customers actually ordered next to what I saw and ordered,
So that I can compare my own picture of demand with the real one.

**Acceptance Criteria:**

**Given** a Student with a saved Explanation
**When** step 2 opens
**Then** the heading is rendered by code from the Game's demand series in the form «Kundene bestilte 4, så 8. Etter det endret de seg aldri.» for a step pattern, with a code-rendered variant per Demand pattern from the sentence templates (FR-44)
**And** the sentence templates are immutable versioned records in `modules/content`, pinned by `sessions.lock` (AD-23)

**Given** step 2
**When** the page shows
**Then** the Etterspørselsbånd is added to `web/src/components/charts` and drawn with «Ordre inn: det eneste du så» and the Student's own Orders (for example «Din ordre, 24 i Uke 11»), not interactive (UX-DR32, AD-18)
**And** the table Uke / Kundene / Ordre inn / Din ordre sits under it on the same columns as an HTML `<table>` with `th` scopes and is the band's alternative (NFR-6)

**Given** step 2
**When** the Student reads it
**Then** the exercise is named with «Øvelsen heter Beer Game.», and this string lives in a post-reveal section of `web/src/copy/nb.ts` that the CI copy check for «Beer Game» and «bullwhip» does not treat as pre-Debrief copy (FR-84, AD-19)
**And** the copy check still fails if either word appears in any copy reachable before a saved Explanation

**Given** the numbers in the band and the table
**When** a test compares them with the Game's stored demand series and `seat_week` rows
**Then** every number matches exactly; the web app computes none of them (FR-44, NFR-9, AD-10)

**Given** a narrow screen or 200 % text
**When** the table has more Weeks than fit
**Then** band and table scroll sideways together in one region with a sticky label column, and the page itself does not scroll sideways (UX-DR75, FR-73)

**Given** step 2
**When** Playwright runs at 320, 360 and 1440 px with axe
**Then** the step passes, the links on the tinted band are `ink` underlined, and numbers use the shared Norwegian number formatter from `web/src/lib/` (UX-DR2, UX-DR5)

**Covers:** FR-44, FR-73, FR-84, NFR-6, NFR-9, AD-10, AD-18, AD-19, AD-23, UX-DR31, UX-DR32

### Story 9.5: Scrub the whole chain and see the amplification

As a Student,
I want to see all four Roles' Orders, inventory and backlog over the Weeks and spool through them,
So that I can see the swings grow upstream and arrive later.

**Acceptance Criteria:**

**Given** a Student with a saved Explanation
**When** step 3 opens
**Then** the heading is «Hele kjeden: svingningene vokser oppstrøms og kommer senere» and the full four-Role chain is shown with the four-Role Kjedebånd variant from `web/src/components/charts`, upstream on the left, «Produksjon» at the left end and «Kundene» at the right (UX-DR31, UX-DR73)
**And** the four-Role variant is added in this story to the existing Kjedebånd component in the shared chart module, never as a copy

**Given** step 3
**When** the Ordrestolper show
**Then** the Ordrestolper and the Rolle × Uke table are reused unchanged from `web/src/components/charts`, where Story 7.8 put them; there is one row per Role with Fabrikk at the top, the viewer's own Role in `ink`, the first Order of 10 or more marked with a dot and «Uke n» and joined by a diagonal, and Forsterkning at the right in `figure-amplification` (for example 1,8× to 7,6×) (UX-DR33, FR-44)
**And** the Rolle × Uke numbers sit underneath in the same columns in `flow-*` steps, each cell printing its number, and are the chart's alternative together with Forsterkning as text (NFR-6)

**Given** the Order amplification and the marked Weeks
**When** they are shown
**Then** they are read from the stored facts set through the Debrief endpoint and equal the Story 9.1 values; inventory and backlog per Role and Week come from the stored Week states (FR-44, NFR-9, AD-7)

**Given** the Ukeskrubber, added to `web/src/components/` for reuse
**When** the Student drags it, presses «Én uke tilbake» or «Én uke fram», or uses the keys
**Then** the chain spools to the chosen Uke with a dashed line across the bars; the control has `role="slider"`, the name «Velg uke», `aria-valuemin="1"`, `aria-valuemax` equal to the last Uke and `aria-valuetext` such as «Uke 15»; Left/Down is −1, Right/Up +1, PageDown/PageUp ±4, Home/End the first and last Uke (UX-DR34)
**And** the step buttons are at least 44 px and no task needs a drag (UX-DR76)
**And** the scrubber shows its range as «Uke 1» to the last Uke, served with the chain data past the Explanation gate (AD-3)

**Given** the scrubber has not changed for 300 ms
**When** the live region updates
**Then** it reads the chain politely as text, Fabrikk first, in the form «Uke 15. Fabrikk: restordre 3, ordre 22. Distributør: restordre 34, ordre 12. …» (UX-DR34)

**Given** `FEATURE_CAPACITY` is on and the Game's settings cap what a Seat can ship per Week
**When** step 3 shows
**Then** the step states the capacity of each capped Role, and a capped Seat shows both stock and backlog for the same Uke in the four-Role Kjedebånd and in the scrubber's reading, with the numbers from the stored Week states, as Story 6.22 shows them on the play screen (FR-12, FR-23, FR-44)
**And** with the flag off none of this renders and the story is complete without it

**Given** step 3
**When** Playwright runs at 320, 360 and 1440 px with axe, and with reduced motion
**Then** Ordrestolper and the Rolle × Uke numbers scroll together inside their own region, the columns of chart and table line up, and spooling shows its result at once with reduced motion (UX-DR75, UX-DR76)

**Covers:** FR-44, FR-14, FR-12, FR-23, FR-73, NFR-6, NFR-9, AD-3, AD-7, AD-18, UX-DR31, UX-DR33, UX-DR34

### Story 9.6: Answer the reflection questions

As a Student,
I want to answer a short series of reflection questions about feelings, evidence and structure,
So that I think through why the chain behaved as it did before I look at my own moments.

**Acceptance Criteria:**

**Given** a Student who has finished step 3
**When** the Debrief continues
**Then** the reflection questions show between steps 3 and 4, one at a time, in the order feelings, then evidence, then structure (FR-45, UX-DR31)
**And** the questions are an immutable versioned record in `modules/content`, pinned by `sessions.lock`, written fresh and in Norwegian (AD-23, FR-72)

**Given** a reflection question
**When** the Student writes an answer and continues
**Then** the answer is saved through `debrief.commands.complete_step`, stored keyed by `user_id` and Class session, and an unsent answer is kept in `web/src/lib/drafts.ts` (AD-10, AD-14, AD-21)
**And** a failed save shows «Det ble ikke lagret. Prøv igjen.» with the text kept

**Given** a Group debrief
**When** Students answer the reflection questions
**Then** each Student answers on their own device and no Student sees another's answers (FR-43)

**Given** the question wording
**When** the copy is reviewed
**Then** it asks why and not who, in the second person, with no praise, blame or exclamation marks, as in «Struktur gir atferd, derfor spør vi hvorfor og ikke hvem.» (UX-DR74)

**Given** the reflection step
**When** Playwright runs at 320, 360 and 1440 px with axe
**Then** it passes and is fully keyboard-operable (NFR-6, FR-73)

**Covers:** FR-45, FR-43, FR-72, FR-73, AD-10, AD-14, AD-21, AD-23, UX-DR31

### Story 9.7: See my own moments, rendered from the facts

As a Student,
I want to see at least three specific moments from my own Seat with what I saw, what I ordered and what it cost later,
So that I can connect my own Orders to what happened in the chain.

**Acceptance Criteria:**

**Given** a Student past the reflection questions with at least 10 own Orders
**When** step 4 opens
**Then** the heading is rendered by code from the first moment's facts in the form «Ditt øyeblikk: Uke 11. Du bestilte 24 med 16 på vei. Og hva det kostet kjeden.» and at least three moments are paged within the step (FR-44, UX-DR31)
**And** each moment shows «Dette så du» (the Graf over tabell from `web/src/components/charts` at that Uke), «Dette regnet du» (the Posisjon sum, for example «Posisjon 0 − 13 + 16 = 3. Med 24 ble den 27.»), «Dette kostet det senere» and «Dette så de andre i Uke 11»

**Given** a moment
**When** its text is produced
**Then** the pure renderer `analysis.render(fact_set, template_ids)` is added to `analysis/` for reuse: it fills approved sentence templates from `modules/content` with numbers and causes from the stored facts set, and names the Detected pattern and its mechanism as a pattern, not a cause (FR-44, AD-7)
**And** the text travels as `{text, ai_generated: false, llm_call_id: null}` and is shown without the AI prefix

**Given** the moment endpoints
**When** they build a response
**Then** they load the facts set by `fact_set_id` through `games.facts.get_or_create`, never rebuild it, and store the `fact_set_id` on the Debrief record (AD-7)
**And** a test asserts that every number in every rendered moment of the golden Games appears in the facts set and equals the `seat_week` rows (NFR-9)

**Given** the Student's own Explanation
**When** step 4 shows
**Then** the Explanation is shown next to what the data shows, to that Student only (FR-44, FR-41)

**Given** a Group debrief
**When** any member or the shared screen requests another Student's moments or Explanation
**Then** the API refuses; own moments are served only to the Student whose Seat they come from (FR-43, AD-12, AD-21)

**Given** a Student with fewer than 10 own Orders in their game (`games.service.student_game`)
**When** step 4 opens
**Then** the Debrief states that the Class game was played mostly by AI players and that the Student's own moments come from their Replay, shows the chain content of steps 2 and 3 as for everyone else, and the Student can still finish the Debrief (FR-44)
**And** the facts set carries the flag that leaves the Student out of SM-1 and SM-2

**Given** `modules/debrief`
**When** an import-linter test runs in CI
**Then** it fails if `modules/debrief` imports `modules/players`, and the whole Debrief passes an api test on a Game played with Rule-based players and the mock provider switched off (AD-7, FR-15)

**Given** step 4
**When** Playwright runs at 320, 360 and 1440 px with axe
**Then** it passes, and paging between moments is keyboard-operable with focus moving to the new moment's heading (NFR-6, FR-73)

**Covers:** FR-44, FR-41, FR-43, FR-15, FR-73, NFR-9, AD-7, AD-12, AD-21, UX-DR31

### Story 9.8: See the chain's bill and finish the Debrief

As a Student,
I want to see what the chain's cost was made of and close the Debrief,
So that I see the cost of the structure and my Debrief is recorded.

**Acceptance Criteria:**

**Given** step 4 after the moments
**When** Kjedens regning shows
**Then** it reuses Kjedens regning and Kjedens kostnad over tid from the shared folder, where Epic 6 put them, keeps the «Kjeden» row (for example «Kjeden 901,00 / 1 365,00 / 2 266,00») and the rows per Role from Detaljist to Fabrikk with the viewer's row marked «(deg)» as Story 6.18 built them, and fills the slot for the Debrief's extra rows, starting with the restordre share line in the form «Restordre er 60 % av kjedens regning, fordi den koster dobbelt.» (UX-DR36, UX-DR73)
**And** the Lager / Restordre / Sum numbers in each row are the alternative for the split bars

**Given** the «Simulert, samme kunder» block
**When** it shows
**Then** it has two rows, one where only the viewer's Seat counts På vei and one where all four Seats count På vei, each computed by a pure `analysis` function that runs `engine.advance` over the Game's stored demand series and settings, stored in the facts set (FR-44, AD-1, AD-7)
**And** the block is labelled «Simulert», carries «Simulert viser sammenhengen, ikke en fasit.», and no copy says «optimal» or «fasit» as a claim (UX-DR36, UX-DR70)
**And** the ordering rule used in the simulated rows takes its parameters from configuration with the Rule-based player's placeholders (issues #8, #17)

**Given** a Class game where AI players held Seats for some Weeks
**When** Kjedens regning shows
**Then** a line under it states the share of chain Total cost incurred in AI-held Seats, from the facts set (FR-44, UX-DR36)

**Given** a Student who has seen step 4
**When** the Student presses the button that ends the Debrief
**Then** `debrief.commands.finish` stores the Debrief summary for that Student (key moments by fact id, the reflection answers, completion time, the `fact_set_id`) and calls `progress.record_step(user, class_session, debrief, at)` in the same transaction (FR-47, AD-16, AD-7)
**And** lateness against the Debrief deadline is derivable from the stored time, and the Debrief stays open until the Test deadline (FR-18)

**Given** a finished Debrief
**When** the Student returns to it
**Then** all steps can be read again and nothing can be changed

**Given** a Lecturer or an Assistant lecturer of the Class
**When** they open a Student's Debrief summary from the Spillinnsikt page of the Game
**Then** the empty `links` slot of Story 7.7 is filled with links to each Student's Explanation and Debrief summary, by a link provider that `modules/debrief` registers through `register_insight_links` in `games` `service.py`, so `modules/games` imports nothing from `modules/debrief`, and they read the key moments, reflection answers, completion time and the Explanation; an Admin not attached to the Class and any Student other than the owner are refused (FR-47, FR-5, AD-12)
**And** the read goes through `debrief.service`, so later epics (Studentside, Student report) reuse it

**Given** the end of step 4 and the staff summary page
**When** Playwright runs at 320, 360 and 1440 px with axe
**Then** both pass (NFR-6)

**Covers:** FR-44, FR-47, FR-18, FR-5, NFR-6, AD-1, AD-7, AD-12, AD-16, UX-DR36

### Story 9.9: Pass the Debrief quiz

As a Student,
I want to take the Debrief quiz and retry until every answer is right,
So that I have the basic mechanism straight before the Replay.

**Acceptance Criteria:**

**Given** a Student with the `debrief` step recorded
**When** step 5 «Debrief-quiz» opens
**Then** the fixed questions come from the quiz record in `modules/content`, pinned by `sessions.lock`, each as a Quizvalg single choice in full-width rows; Quizvalg is added to `web/src/components/` for reuse by the Individual test (FR-46, AD-23, UX-DR37)
**And** a Student without the `debrief` step gets `403 debrief_required` from the API, checked with `progress.has_step` (AD-16)
**And** the quiz content is a non-code deliverable (issue #16); the story ships with a clearly marked placeholder quiz

**Given** a submitted attempt
**When** it is scored
**Then** scoring is by answer key on the server only, one `quiz_attempts` row is stored per attempt with the answers, the result and the quiz version, and the row is never updated (FR-46, AD-23)

**Given** an attempt with wrong answers
**When** the result shows
**Then** each wrong choice shows «Ditt svar, ikke riktig» and the right one «Riktig», in text and border and never by colour alone, followed by the explanation from the content record, which names the column where it applies, as in «Det står i kolonne 11 i din egen tabell.» (UX-DR37, FR-46)
**And** values in an explanation that refer to the Student's own Game are rendered from the stored facts set by `analysis.render`

**Given** an attempt with at least one wrong answer
**When** the Student retries
**Then** a new attempt opens with no limit on retries, the question order may be reshuffled, and the retry stays available until the Test deadline (FR-46)

**Given** an attempt where every question that is not excluded is answered correctly
**When** it is stored
**Then** `progress.record_step(user, class_session, quiz_passed, at)` is called in the same transaction, the number of attempts is added to the Student's Debrief summary, and Stegene shows the Quiz step as done (FR-46, FR-47, AD-16)

**Given** the Test deadline has passed
**When** a Student submits an attempt
**Then** the API answers `409 test_deadline_passed` and the step stays not done (FR-18)
**And** the deadline is read only through `sessions.service.effective_test_deadline(user, class_session)`

**Given** a Group debrief
**When** the group reaches the quiz
**Then** each Student takes it individually on their own device, and the result counts toward nothing and feeds no score (FR-46)

**Given** the quiz
**When** Playwright runs at 320, 360 and 1440 px with axe
**Then** it passes, is fully keyboard-operable, and after submit focus moves to the result summary (NFR-6, UX-DR76)

**Covers:** FR-46, FR-47, FR-18, FR-73, NFR-6, AD-16, AD-23, UX-DR31, UX-DR37

### Story 9.10: Exclude a quiz question and see quiz attempts

As a Lecturer,
I want to exclude a Debrief quiz question and see how many attempts each Student used,
So that a weak question does not block my Students and I can see who struggles.

**Acceptance Criteria:**

**Given** a Lecturer on the Klasseøkt screen
**When** the Lecturer opens the Debrief quiz block
**Then** the pinned quiz questions are listed with their answer keys and a Bryter per question to exclude it, with help text stating the scope (FR-46, UX-DR12)
**And** an Assistant lecturer can read the list but gets no exclude control (AD-12)

**Given** a Lecturer who excludes a question
**When** the change is saved
**Then** the exclusion is stored as a Class session row owned by `modules/debrief`, never as an edit of the content record, and is recorded through `platform/audit` (AD-23, AD-15)
**And** it can be set or lifted until the Class session's Test deadline

**Given** an excluded question and a Student who has not yet passed
**When** the Student opens a new attempt
**Then** the question is not asked and passing needs only the remaining questions (FR-46)
**And** a Student who already passed stays passed if an exclusion is lifted later

**Given** a Student whose last stored attempt was right on every question except the one now excluded
**When** the exclusion is saved
**Then** the Student is not passed automatically; their next attempt applies the exclusion, and Hjem tells them the quiz has changed through `platform/notify.enqueue`

**Given** a Lecturer or Assistant lecturer on the Debrief summary of a Student (Story 9.8)
**When** the Student has quiz attempts
**Then** the number of attempts, their times and whether the quiz is passed are shown, read through `debrief.service` (FR-46, FR-47)

**Given** the Lecturer tries to exclude every question
**When** the last one is switched
**Then** the save is rejected with a reason beside the control, since the quiz needs at least one question

**Covers:** FR-46, FR-47, AD-12, AD-15, AD-23, UX-DR12

### Story 9.11: Go through the Debrief together as a group

As a Student,
I want to open a Group debrief that the others in my Class game can join,
So that we go through the same steps together, each on our own device.

**Acceptance Criteria:**

**Given** a Class session with Debrief mode Group debrief and a finished Class game that is the game (`games.service.student_game`) of at least two active Students, where an active Student is one assigned to a Seat of it with at least one Order with `decided_by = student` ([ASSUMPTION] to confirm)
**When** one Student opens the Debrief
**Then** `debrief.commands.open` marks the Debrief session as shared with that Student as opener and joined, and `platform/notify.enqueue` tells the other Students of the Class game, which emits `user:<id>` so their Hjem shows a way to join (FR-43, AD-9, AD-21)
**And** in a Class session with Debrief mode Personal debrief, or a Class game with one active Student, the Debrief opens as a Personal debrief with no shared step (FR-16, FR-43)

**Given** a shared Debrief session
**When** another Student of the Class game presses join
**Then** `debrief.commands.join` adds them to the joined set and emits `debrief:<id>`; a User who has no Seat in that Class game is refused by the `platform/authz` policy (AD-12, AD-21)
**And** the web app reads the Debrief session id from the Debrief endpoint and maps `debrief:<id>` to its query keys only in `web/src/lib/api/topics.ts` (AD-8)

**Given** joined Students on step 1
**When** some have sent their Explanation and some have not
**Then** those who have sent see «Avsløringen er låst til alle fire har sendt. Ida og Mikkel har sendt, Jonas skriver.» with the names resolved at read time, a time guide for writing is shown, and the unlocking of the reveal is announced politely (FR-43, UX-DR31, UX-DR76)
**And** no Student sees another's Explanation text

**Given** a shared step
**When** every joined Student has finished it through `debrief.commands.complete_step`
**Then** the step pointer moves to the next step for all joined Students, within the SSE refetch, without reload (FR-43, AD-8)

**Given** a shared step that not all have finished
**When** the opener presses the button to move on
**Then** `debrief.commands.move_on` moves the pointer only if the minimum wait since the step opened has passed, and otherwise answers `409 too_early` with the time it becomes possible; the minimum wait is configuration with a placeholder value
**And** a Student who is not the opener gets no move-on control and `403` from the API

**Given** the pointer has moved past step 1 while one joined Student has no saved Explanation
**When** that Student's device refetches
**Then** it stays on step 1, the API still answers `403 explanation_required` for reveal data, and after saving the Student enters at the current step; a late joiner is treated the same way (FR-43, AD-21)

**Given** a Group debrief
**When** the group reaches the reflection questions, step 4 and the quiz
**Then** each Student works on their own device, a Student's step is finished per Student, and one joined Student can go through the whole Group debrief alone (FR-43)

**Given** two Students in two browser contexts
**When** a Playwright test runs the group flow at 360 and 1440 px with axe
**Then** open, join, the locked reveal, step advance and the opener's move-on pass, and the registry test covers `join`, `save_explanation`, `complete_step`, `move_on` (AD-8, NFR-6)

**Covers:** FR-43, FR-16, FR-41, AD-8, AD-9, AD-12, AD-21, UX-DR31

### Story 9.12: Continue alone when the group is not there

As a Student,
I want to continue in a Personal debrief when my group has not met or I have dropped out,
So that my progress never depends on the others showing up.

**Acceptance Criteria:**

**Given** a joined Student with an open SSE stream
**When** the stream is alive
**Then** on each 15-second heartbeat the stream fires a presence hook, which this story adds to `platform/events` (`on_heartbeat(callback)`) and `modules/debrief` registers at startup; the hook calls the new command `debrief.commands.touch(user_id)`, which writes `last_seen_at` on that Student's joined row in a short database session of its own, so the stream itself still holds none and `platform` imports no module (AD-8, AD-21)
**And** `touch` is added to the `debrief.commands` list as its one command that takes no Debrief row lock and emits no event, with an empty topic set in the registry; presence is never reported by the client

**Given** a joined Student whose `last_seen_at` is older than 2 minutes
**When** the joined set is next evaluated by a `debrief.commands` command or the sweep
**Then** the Student is treated as dropped out through `debrief.commands.leave`, the shared step no longer waits for them, and the remaining Students move on when all of them have finished the step (FR-43, AD-21)
**And** the dropped Student, on return, continues in a Personal debrief from the step they were on, with their saved Explanation and answers kept

**Given** a Student who presses the control to leave the Group debrief
**When** `debrief.commands.leave` runs
**Then** the same rule applies: Personal debrief from the same step, and `debrief:<id>` is emitted to the others

**Given** a Group debrief Class session and a Class game that ended 48 hours ago with no Group debrief finished
**When** `ops.sweep` runs
**Then** a due action, added to the sweep of Story 3.5, calls the new command `debrief.commands.open_personal_fallback(debrief_id)`, added to the `debrief.commands` list, which opens the Personal debrief fallback for each Student of that Class game who has not finished, once, with ids only as arguments, and notifies them through `platform/notify.enqueue` (FR-43, AD-9)
**And** the 48 hours are a column value computed from the Game's finish time, not a scheduled job

**Given** a Student who missed a Group debrief that the others have already finished
**When** the Student opens the Debrief
**Then** it opens as a Personal debrief at once, without waiting for the 48 hours (FR-43)

**Given** a Student who continues in a Personal debrief
**When** they go through the remaining steps
**Then** every gate still holds: the Explanation before the reveal, the `debrief` step on finish, and the quiz after it (FR-41, AD-21)

**Given** these paths
**When** api tests run with a controlled clock
**Then** the 2-minute dropout, the leave, the missed group and the 48-hour fallback each pass, the sweep action is shown to be idempotent, and the registry test covers `leave`, `touch` and `open_personal_fallback` (AD-8, AD-9)

**Covers:** FR-43, FR-41, AD-8, AD-9, AD-21, UX-DR31

### Story 9.13: Show the Group debrief on a shared screen

As a Student,
I want to put the chain on one shared screen while each of us answers on our own device,
So that the group can look at the same charts together in the room.

**Acceptance Criteria:**

**Given** a joined Student in a Group debrief
**When** the Student opens «Delt skjerm: hele kjeden» on a laptop or projector
**Then** it is that Student's own session opened in display mode, in the laptop layout, and it shows the chain, Netto lager per Role, «Kostnad, kr» per Role and the chain total (for example «Kjeden 2 266,00») (FR-74, UX-DR35)
**And** Lager and Restordre numbers are printed beside each Role total, not only the total

**Given** the shared screen
**When** it loads data
**Then** it calls only `GET /api/debriefs/<id>/shared`, which returns shared charts with Roles and never names, Explanations, reflection answers or own moments (FR-74, AD-21)
**And** an api test asserts on the response schema that no `user_id`, name or free-text field can be present

**Given** a Group debrief where at least one joined Student has no saved Explanation
**When** the shared endpoint is called
**Then** it returns no demand series and no chain data, and the screen states that the reveal is locked until all joined Students have sent, without names (FR-43, AD-21)

**Given** a User who is not joined to that Debrief session
**When** they call the shared endpoint
**Then** the API answers as for permission denied, without revealing whether the Debrief exists (AD-12, UX-DR59)

**Given** the shared screen
**When** the Ukeskrubber is used on it
**Then** it is operated on that device only; each phone keeps its own scrubber, not synced (UX-DR34)

**Given** the shared screen
**When** the shared step moves on
**Then** it follows `debrief:<id>` and refetches, with the chain drawn upstream on the left and Role rows with Fabrikk at the top (AD-8, UX-DR73)

**Given** the shared screen
**When** Playwright runs at 1440 px and at 320 px with axe
**Then** it passes and every chart has its alternative (NFR-6)

**Covers:** FR-74, FR-43, NFR-6, AD-8, AD-12, AD-21, UX-DR34, UX-DR35

### Story 9.14: Read AI narration that only connects computed facts

As a Student,
I want a short AI-written line that ties my moments together, clearly marked as AI,
So that the Debrief reads as an explanation and I know which words came from an AI.

**Acceptance Criteria:**

**Given** a facts set and the approved sentence templates
**When** narration is requested
**Then** a shared helper in `app/ai` calls `ai.run(purpose=debrief_narration, budget_scope=<Class session>, …)` with an output schema that references fact ids and sentence-template ids only; code renders every number and cause into the text (FR-44, AD-6, AD-7)
**And** the helper takes the validator and the fallback renderer as arguments from its caller, so `app/ai` imports only `platform`; `modules/debrief` passes `analysis.validate_ai_text` and `analysis.render`, and later callers pass their own
**And** the prompt is a versioned file under `api/app/ai/prompts/debrief_narration/`, its inputs carry Roles and numbers only, and the call may spend the budget `reserve` (AD-6, FR-69)
**And** the default model config gets each new purpose of this story (`debrief_narration`, `quiz_explanation`) in its `prompts` map as a new config row made with `config edit … --prompt` of Story 2.2, since a config is immutable once referenced (AD-6)

**Given** an LLM output
**When** the pure validator `analysis.validate_ai_text(output, fact_set, templates)`, added to `analysis/` for reuse, checks it
**Then** it rejects any output that cites a fact id outside the set, a template id outside the pinned version, or a number outside the rendered facts (FR-44, AD-7, NFR-9)
**And** golden tests cover an accepted output and one rejection of each kind

**Given** a rejection or a typed failure (`timeout`, `invalid_output`, `budget_exhausted`, `provider_error`)
**When** the helper returns
**Then** it returns the text of the fallback renderer it was given, here `analysis.render`, as `{text, ai_generated: false, llm_call_id: null}`; the caller never retries; the Student sees the same content without AI text (FR-44, AD-6, AD-7)

**Given** the deferred decision on the timing of Debrief narration
**When** this story is done
**Then** the decision is recorded in the story and the spine's Deferred entry is closed: narration is generated on `llm-batch` in `worker-batch`, deferred when the Class game finishes, one idempotent job per Student ever assigned to a Seat of the Game, keyed by `fact_set_id`, with ids only as arguments; the sweep of Story 3.5 re-enqueues a job that was lost (AD-9)
**And** the job is deferred inside the `finish` transaction through a finish hook, which this story adds to `games` `service.py` (`on_game_finished(hook)`, the same pattern as the pin providers of Story 5.11) and `modules/debrief` registers, so `modules/games` imports nothing from `modules/debrief`
**And** no Debrief step ever waits on an LLM call: step 4 shows the code-rendered text until the narration is stored, and the text shown to a Student is fixed at that Student's first view of the moment, so it never changes under a reader
**And** an api test runs a full Group debrief with the narration job never completing and asserts that every step opens

**Given** accepted narration
**When** it is shown in step 4
**Then** it carries the prefix «KI-generert, kan ta feil:» with the text in «», the marking is driven only by `ai_generated` in `{text, ai_generated: true, llm_call_id}`, and the markup carries a machine-readable marker that the print route can reuse (FR-34, UX-DR69)
**And** the Debrief states that the AI's explanation can be wrong (FR-44)

**Given** a Lecturer on the Klasseøkt screen before the Start date
**When** the Lecturer switches the Debrief's AI text off with a Bryter
**Then** the Class session uses the code-only Debrief: no narration job is deferred and no Debrief call reaches `ai.run`; the choice is pinned at `sessions.lock` as an entry in `SessionRuntime`'s open map, with no change to the lock's mechanism (FR-15, FR-44, AD-4)

**Given** Debrief quiz explanations
**When** the LLM words one
**Then** it goes through the same helper, validator and marking with the purpose `quiz_explanation`, and on any failure the fixed explanation from the content record shows (FR-46, FR-34)

**Given** `APP_ENV` is local, test or ci with no provider key
**When** narration runs
**Then** the deterministic mock produces it, and a Playwright test shows the marked AI line and, with the mock set to fail, the unmarked code text (AD-17)

**Covers:** FR-44, FR-34, FR-15, FR-46, FR-69, NFR-9, AD-4, AD-6, AD-7, AD-9, AD-17, UX-DR31, UX-DR69

### Story 9.15: Ask bounded follow-up questions about my Game

As a Student,
I want to ask follow-up questions about my own Game and get hints grounded in its numbers,
So that I can clear up what I did not understand without being handed answers.

**Acceptance Criteria:**

**Given** a Student past the reflection questions in a Class session with Debrief AI text on
**When** the Student sends a follow-up question
**Then** the api calls `ai.run(purpose=debrief_follow_up, budget_scope=<Class session>, …)` once with the Student's question, the stored facts set and the sentence templates; the gateway scrubs the question against the Roster before it leaves (FR-45, AD-6, C-1)
**And** the output schema, validator and code rendering are the ones from Story 9.14, so an answer can only connect computed facts (AD-7)
**And** the prompt is a versioned file under `api/app/ai/prompts/debrief_follow_up/`, and the default model config gets the purpose in its `prompts` map as a new config row made with `config edit … --prompt` of Story 2.2 (AD-6)
**And** this is the first Student free text sent to an LLM, so `platform/pii.terms(class_session_id)` now queries the `identity` tables for the whole Roster's names, emails and student numbers; an import test shows that only the gateway calls it, and a test with a Roster name typed into a follow-up question and into an Explanation asserts that the name is absent from the request the provider receives and from the stored `llm_call` body (AD-6, AD-14, PRD §6.1)

**Given** a question outside the Game and Beer Game concepts
**When** the model answers
**Then** the schema's decline flag is set and the Student sees a fixed, code-rendered decline line; no free LLM text is shown (FR-45)
**And** for a question that asks for a model answer to a test-like question, the answer uses only hint templates that point to where to look (a Uke, a row, a mechanism) and gives no worked answer; the prompt version states this rule (FR-45)

**Given** an accepted answer
**When** it shows
**Then** it carries «KI-generert, kan ta feil:» from the `ai_generated` flag, and question and answer are stored keyed by `user_id` and Class session with the `fact_set_id` and `llm_call_id` (FR-34, AD-7, AD-14)

**Given** a rejection, a typed failure or `budget_exhausted`
**When** the call returns
**Then** the Student sees an inline line that no answer could be given, with the question kept in the field, and the Debrief continues; the follow-up never blocks a step (FR-44, FR-45)

**Given** a Student sending many questions
**When** the per-account or per-IP limit in `platform/ratelimit` is reached
**Then** the API answers `429 rate_limited` with the time to wait, shown inline; the limits are configuration with placeholder values (AD-11)

**Given** follow-up closing
**When** `debrief.commands.close_follow_up(user, class_session)` has been called for that Student, or `sessions.service.effective_test_deadline(user, class_session)` has passed, which is the backstop
**Then** the API answers `409 follow_up_closed` and the field is replaced by a line saying so (FR-45)
**And** `close_follow_up` is added to the `debrief.commands` list and exposed in `debrief/service.py`, the one entry point other slices use to close follow-up when a Student's Individual test opens; an api test calls it through the service and asserts the close

**Given** a Class session with Debrief AI text off, or no provider available
**When** the Debrief shows
**Then** the follow-up field is not shown at all (FR-15)

**Given** the follow-up field
**When** Playwright runs at 320, 360 and 1440 px with axe
**Then** it passes; the answer is announced politely and focus stays in the field (NFR-6)

**Covers:** FR-45, FR-34, FR-15, FR-44, FR-18, NFR-6, AD-6, AD-7, AD-11, AD-14, AD-21, UX-DR31, UX-DR69

## Epic 10: Replay

When this epic is done, a Student who has passed the Debrief quiz can play one Replay alone in the same Role against three AI players, under a Replay scenario that differs per Student, on the same play screen with the projection line, and then read a short walkthrough that compares it with the Class game. A Lecturer can keep the default Replay scenario or set every Game setting. The epic owns `api/app/modules/replay/` and `web/src/modules/replay/`; it creates `purpose=replay` Games through `games.commands` and reuses Epic 6's play screen and Epic 9's facts, renderer and validator.

### Story 10.1: Get a default Replay scenario that differs per Student

As a Lecturer,
I want every Class session to come with a default Replay scenario that varies per Student,
So that the Replay is harder than the Class game and cannot be played from memory, without any setup from me.

**Acceptance Criteria:**

**Given** the deferred decision on the Replay scenario template
**When** this story is done
**Then** the decision is recorded in the story and the spine's Deferred entry is closed: `engine.ReplayTemplate` is a Pydantic model with `schema_version` that holds every `GameSettings` field as either a fixed value or a whole-number range, and `engine.replay_settings(template, seed) -> GameSettings` is the one pure function that resolves it (AD-1, AD-4)
**And** the function does no I/O, reads no clock, and draws every ranged value and the demand series only from the passed seed

**Given** a Class session whose Replay scenario is the default
**When** its Replay scenario is read
**Then** the Class session stores only the choice `default`, never a copy of the template, and the template is derived from the Class session's current Game settings by the pure function `engine.default_replay_template(game_settings) -> ReplayTemplate`, so an edit of the Game settings before the Start date never leaves a stale template (FR-49, AD-1)
**And** with the Classic defaults the derived template keeps the Class game's demand levels (4, then 8) with random variation drawn per Week from a discrete uniform distribution with a spread of 2 around the level, a step Week ranged 5 to 12, a number of Weeks ranged 30 to 40, no Guided Weeks, and every other setting equal to the Class session's Game settings (FR-49)

**Given** a Class session whose Demand pattern is not the Classic step
**When** the default template is derived
**Then** one rule per Demand pattern kind applies, each with its own test: a step or a step plus noise keeps the Class session's own start level and new level, with a spread of 2 or the Class session's own spread where that is larger, and the step Week ranged 5 to 12; random demand keeps the Class session's mean with a spread of 2 or its own spread where that is larger, and has no step Week; a fixed series keeps each Week's value as the level with a spread of 2 around it, holds the last value for Weeks beyond the series, and has no step Week [ASSUMPTION: founder confirms the rules for random demand and a fixed series; FR-49 defines the default only for a step] (FR-49, FR-13)
**And** in every kind the number of Weeks is ranged 30 to 40, there are no Guided Weeks, no demand value is below 0, and every other setting equals the Class session's Game settings

**Given** the default template and a fixed seed
**When** `engine.replay_settings` is called twice
**Then** both calls return identical `GameSettings` and an identical materialised demand series (AD-4)
**And** golden tests fix the result for at least three seeds, and a property test over many seeds asserts that the step Week is in 5 to 12, the Weeks in 30 to 40, Guided Weeks 0, every demand value a whole number of 0 or more and within the spread of its level

**Given** a template whose ranges could produce invalid `GameSettings` (for example a step Week after the last Week)
**When** the template is validated
**Then** it is rejected with the field and the range shown, using the same validation as Game settings (FR-12)

**Given** a Lecturer on the Klasseøkt screen
**When** the Replay block shows
**Then** it states that the Replay uses the default scenario and describes it in words (demand levels as in the Class game with variation, the step Week and the length differ per Student and stay hidden), with copy from `web/src/copy/nb.ts` (FR-49, FR-72)
**And** the choice is one column on `class_sessions`, added by this story through `modules/sessions`, and the block passes axe at 320 and 1440 px (NFR-6)

**Given** a Class session at its Start date
**When** `sessions.lock` runs
**Then** a pin provider registered by this story derives the template from the Game settings being frozen and stores it as an entry in `SessionRuntime`'s open map, with no change to the lock's mechanism from Story 5.11; this frozen template is the only one a Replay reads (AD-4)
**And** an api test edits the Game settings before the Start date, locks, and finds the template derived from the edited settings

**Given** the founder
**When** `python -m app.sim` is run with the default Replay template and a batch of seeds
**Then** simulation Games run on the resolved settings, so the Play guard band can be calibrated on the default Replay scenario (FR-79, AD-22)
**And** this story adds the profile of the default Replay scenario, as derived from the Classic settings, as the named entry `replay_default` in a new version of the Play guard parameter set, in the list of settings profiles that `analysis.play_guard.is_calibrated` of Story 2.10 reads, with a test that a default Replay counts as calibrated and an own scenario with other settings does not

**Covers:** FR-49, FR-12, FR-13, FR-72, NFR-6, AD-1, AD-4, AD-22

### Story 10.2: Set the Replay scenario freely

As a Lecturer,
I want to set every Game setting of the Replay scenario myself,
So that I can make the Replay harder or different in the way my course needs.

**Acceptance Criteria:**

**Given** a Lecturer on the Klasseøkt Replay block before the Start date
**When** the Lecturer chooses to set the scenario
**Then** a Valgknapper control switches between the default and an own scenario, and the own scenario opens every Game setting prefilled from the Class session's Game settings: starting inventory or backlog, supply-line contents, delays, costs, Weeks, Guided Weeks, maximum Order and Demand pattern (FR-49, UX-DR12)
**And** the form reuses the Game settings fields and validation of the Klasseøkt screen from Epic 5, with out-of-range values rejected inline with the range shown (FR-12)

**Given** an own scenario
**When** the Lecturer sets a single value for the step Week and the number of Weeks, or the Class game's exact settings
**Then** it is accepted and stored as an `engine.ReplayTemplate` with fixed values in a JSONB column on `class_sessions`, added by this story through `modules/sessions`, so one model serves both the default and the own scenario (FR-49)

**Given** an own scenario with a change that is likely to make the Replay easier (shorter delays than the Class game, lower or less variable demand, Guided Weeks, higher starting inventory)
**When** the form is shown or saved
**Then** a non-blocking warning names the change and says it probably makes the Replay easier; the save still succeeds (FR-49, UX-DR48)
**And** the list of warned changes is one function in `modules/sessions`, tested per rule

**Given** an own scenario
**When** it is saved
**Then** the choice applies on «Lagre Klasseøkt», and every Replay still draws a fresh demand seed per Student (FR-49)

**Given** the Start date has passed
**When** anyone opens the Replay block
**Then** it is read-only, and the pin provider of Story 10.1 has frozen the template in force, the own scenario where one was chosen and the derived default otherwise, in `SessionRuntime`'s open map; a save answers `409 session_locked` (FR-18, AD-4)

**Given** `FEATURE_RERUN` is on and Story 5.18 is built
**When** a Lecturer creates a Class session from an earlier one
**Then** the Replay scenario choice and the own template are copied, because this story adds them to `sessions.service.copy_from` of Story 5.18, and the copied template passes the template validation again; with the flag off, or Story 5.18 not built, this story adds nothing there (FR-66, AD-17)

**Given** an Assistant lecturer
**When** they open the Klasseøkt Replay block
**Then** they can read it and get no edit controls, through `platform/authz` (AD-12)

**Given** the block
**When** Playwright runs at 320 and 1440 px with axe and 200 % text
**Then** the form is one column at narrow widths and passes (NFR-6, UX-DR75)

**Covers:** FR-49, FR-12, FR-18, FR-66, NFR-6, AD-4, AD-12, AD-17, UX-DR12, UX-DR48

### Story 10.3: Start the Replay after passing the Debrief quiz

As a Student,
I want to start my Replay once I have passed the Debrief quiz,
So that I can meet the same structure again on my own.

**Acceptance Criteria:**

**Given** a Student without the `quiz_passed` step
**When** Stegene shows
**Then** the Replay step reads «Replay, åpnes når du har bestått Debrief-quizen.» and the API answers `403 quiz_required` to a start request, checked with `progress.has_step` (FR-48, AD-16, UX-DR64)

**Given** a Student with `quiz_passed`, before the Test deadline
**When** the Student presses the button to start the Replay
**Then** `replay.service.start` draws a fresh seed, resolves the Class session's locked template with `engine.replay_settings`, and calls `games.commands.create` with `purpose=replay`, which snapshots the `GameSettings`, the materialised demand series, the seed, the engine `rules_version` and the Class session's `SessionRuntime` at creation (FR-48, FR-49, AD-2, AD-4, AD-13)
**And** the seed is stored with the Game, so the Decision log can be replayed by the engine
**And** the `SessionRuntime` and the `rules_version` come from the Class session's frozen snapshot, read through `sessions.service.build_snapshot(class_session)` of Story 5.11, and only the Game settings, the demand series and the seed are replaced by the Replay's own; where `games.commands.create` does not yet take a Class session id and a ready snapshot for a purpose that snapshots at creation, this story extends it, and nothing here relies on cut-list Story 6.20, which does the same for its own purpose

**Given** the new Replay Game
**When** its Seats are assigned through `games.commands.assign_seat`
**Then** the Student holds the same Role as in their own game, read through `games.service.student_game(user, class_session)` from Story 6.1 and never by querying Class games directly, and the three other Seats get AI players in the Class session's AI mode; while the cost-limit state is set, they are created as `rule_based` with reason `cost_limit` (FR-48, FR-30, AD-5)
**And** `games.commands.start` then starts the Replay, so the Student never meets an empty Seat or a Game that is not started
**And** `modules/replay` writes no game table itself and imports other slices only through their `service.py`

**Given** `games.policy`
**When** this story is done
**Then** it has a `replay` row: no inactivity Takeover, no Pause, no Play deadline playout, Guided Weeks only if the scenario sets them, not listed on the Lecturer overview, the column of Story 5.9 set to snapshot at creation, the two columns of Story 6.18, "records the Class game step" and "pre-play gate applies", both off, and the projection on (AD-13)
**And** the projection is a new column of `games.policy`, added by this story and off for every other purpose
**And** a test asserts that `ops.sweep`'s Takeover and playout actions skip `purpose=replay` Games

**Given** a Student who already has a Replay
**When** a second start request arrives, also from another device at the same moment
**Then** the existing Replay is returned and no second Game is created; a unique key on Student and Class session backs this up (FR-48)

**Given** `sessions.service.effective_test_deadline(user, class_session)` has passed
**When** a Student tries to start the Replay
**Then** the API answers `409 test_deadline_passed` and Stegene shows the step as not done (FR-18)

**Given** a started Replay
**When** the Student opens Hjem
**Then** the Replay shows as in progress in Stegene, and all AI-held Seats are named «KI-spiller» from the first view (FR-34, UX-DR64)

**Covers:** FR-48, FR-49, FR-30, FR-34, FR-18, AD-2, AD-4, AD-5, AD-13, AD-16, UX-DR64

### Story 10.4: Play the Replay with the projection line

As a Student,
I want to play my Replay on the screen I already know, with a line showing where my net stock is heading,
So that I can try to order on the sum of what is on its way.

**Acceptance Criteria:**

**Given** a Student with a running Replay
**When** the Replay opens
**Then** it uses the play screen, Kjedebånd, Graf over tabell, Ordrefelt, Setestatus and order submit states from Epic 6 unchanged, reads `seat_state` and `table_status` from the same play endpoint, and places Orders only through `games.commands.place_order` (FR-48, AD-2, AD-3)
**And** no component of the play screen is copied into `web/src/modules/replay/`

**Given** the play envelope of a Game whose `games.policy` row has the projection on
**When** the Graf over tabell renders
**Then** the projection is drawn as a dashed `projection` line ending in a hollow dot at nå + 4, with the sentence «Den stiplede linja viser netto lager om fire uker: 3 + 24 − 4 × 8 = −5 hvis ordre inn holder seg. Ikke garantert.» filled with the Seat's numbers (UX-DR19)
**And** the number of Uker in the sentence, the factor in the sum and the column of the hollow dot come from the delay horizon in `SeatState`, which is four with the Classic delays, because Story 10.2 lets the Lecturer change the delays; a test renders a Replay with shorter delays
**And** the projection never shows in a Class game, checked by a Playwright test on both

**Given** the projection value
**When** the Student types an Order
**Then** the value is display arithmetic in `web/src/lib/preview.ts` from fields the API returned in `SeatState` (Posisjon, incoming order, the delay horizon) plus the typed Order, and it updates as the Order is typed (AD-10)
**And** if a field is missing it is added to `games.schemas.SeatState`, never beside it, and a Vitest test checks the projection against golden values produced by `engine` (AD-3)

**Given** the projection line
**When** a screen reader reads the screen
**Then** the line is `aria-hidden` and its sentence is the text alternative; the line differs from the Netto lager and Posisjon lines in stroke and marker, not by colour alone (NFR-6, UX-DR76)

**Given** a Replay in play
**When** any screen shows
**Then** the number of Weeks and future demand are never shown, the axis stops at nå + 4, only a Retailer sees customer demand one Week at a time, and no Pausevalg or «Sett inn KI-spiller» shows (FR-49, FR-14, UX-DR71)

**Given** a Student who leaves and returns, on the same or another device
**When** Hjem and Stegene show
**Then** they read «Fortsett Replay, Uke 9.» with the current Uke, and the Replay resumes at that Uke with nothing lost (FR-48, NFR-5, UX-DR64)

**Given** a confirmed Order
**When** the three AI players have not yet ordered
**Then** Setestatus shows their rows as «venter», the wait is bounded by the Order time budget of the Effort level (NFR-2), and the new Uke shows within 2 seconds of the last Order (NFR-1)

**Given** the Replay screen
**When** Playwright runs at 320, 360 and 1440 px with axe
**Then** it passes, including the projection sentence wrapping without overlap at 320 px (FR-73)

**Covers:** FR-48, FR-49, FR-14, FR-73, NFR-1, NFR-2, NFR-5, NFR-6, AD-2, AD-3, AD-10, UX-DR19, UX-DR64

### Story 10.5: Finish the Replay and unlock the next step

As a Student,
I want the Replay to end with my Total cost and count as done,
So that I can go on to the walkthrough and the Individual test.

**Acceptance Criteria:**

**Given** a Replay in its last Week
**When** the last Order is placed
**Then** the last Week runs in full, `games.commands.finish` sets `lifecycle = finished`, and the Student sees «Replay er ferdig», their Totalkostnad, then «Gå til gjennomgangen» (FR-50, UX-DR64)
**And** nothing before that moment hinted that the Week was the last (FR-49)

**Given** a finished Replay
**When** `replay.service` handles the finish
**Then** `progress.record_step(user, class_session, replay, at)` is called once, idempotently, which emits `user:<id>` so Stegene updates without reload (AD-16, AD-8)
**And** lateness against the Debrief deadline is derivable from the stored time (FR-18)

**Given** a finished Replay
**When** `games.commands.finish` completes
**Then** the same finished-game check that Epic 6 runs for a Class game runs for the Replay: the engine replays the stored Orders at the stored `rules_version` and must reproduce the stored Week states, and a violation is logged (FR-29, AD-4)
**And** an api test finishes a Replay and asserts that the check ran

**Given** a finished Replay
**When** the Student opens Hjem
**Then** Stegene shows Replay as done and the next step as available, and the Replay screen can be read again but takes no Order (`409` from `place_order`)

**Given** a finished Replay
**When** staff open Spillinnsikt for it
**Then** it opens as any Game, labelled as a Replay, with the three AI-held Seats marked (FR-34, AD-12)

**Given** the finish screen
**When** Playwright runs at 320, 360 and 1440 px with axe
**Then** it passes, with one primary button and Totalkostnad formatted by the shared number formatter (NFR-6, UX-DR5)

**Covers:** FR-48, FR-50, FR-18, FR-29, FR-34, NFR-6, AD-4, AD-8, AD-16, UX-DR64

### Story 10.6: Close unfinished Replays at the Test deadline

As a Lecturer,
I want every unfinished Replay closed at the Test deadline,
So that no Game stays open after the Class session ends and the records show plainly who finished.

**Acceptance Criteria:**

**Given** the deferred decision on closing Replays at the Test deadline
**When** this story is done
**Then** the decision is recorded in the story and the spine's Deferred entry is closed: a new command `games.commands.close(game, reason)` is added to the AD-2 command list, and a new due action is added to the AD-9 sweep list (AD-2, AD-9)
**And** an unfinished Replay is closed, not played out by AI players, because a played-out Replay would not be the Student's own (AD-13)

**Given** a `purpose=replay` Game that is not finished, and the Student's `effective_test_deadline` has passed
**When** `ops.sweep` runs
**Then** it calls `games.commands.close(game, reason=test_deadline)` once per Game in its own transaction; the command locks the Game row, sets `lifecycle = finished` with an `end_reason` of `test_deadline`, opens no further Week, increments `version` and emits `game:<id>` and `user:<id>` (AD-2, AD-8)
**And** the `end_reason` column on `games` is added by this story; a Game that ends through `finish` has it empty
**And** the action is idempotent, takes ids only, and the registry test covers `close`

**Given** a closed Replay
**When** the Student's steps are read
**Then** no `replay` step is recorded, the step stays not done, and the stored Orders remain in the Decision log unchanged (FR-18, AD-15, AD-16)

**Given** a closed Replay
**When** the Student opens it or tries to order
**Then** `place_order` answers `409 test_deadline_passed` and the screen states that the Replay was closed at the Testfrist and is not finished, with copy from `web/src/copy/nb.ts`

**Given** an `ai-orders` job still running for a Replay that is closed meanwhile
**When** the job calls `place_order`
**Then** it gets the same `409` and ends without an Order and without a retry; the Game row lock settles the race (AD-2, AD-5)

**Given** a closed Replay
**When** another module reads the Game through `games.service`
**Then** the `end_reason` is returned with it, so later reports and statistics never compare a closed Replay as a finished one (AD-13)

**Given** the Test deadline of a Student
**When** the sweep, `replay.service.start` or `place_order` on a Replay reads it
**Then** it is read only through `sessions.service.effective_test_deadline(user, class_session)` from Epic 5 (FR-18)
**And** an api test with a controlled clock covers: closed at the deadline, untouched before it, and a finished Replay left alone

**Covers:** FR-48, FR-18, AD-2, AD-5, AD-8, AD-9, AD-13, AD-15, AD-16

### Story 10.7: Read the Replay walkthrough

As a Student,
I want a short walkthrough of my Replay next to my Class game,
So that I can see what I did differently, knowing the two runs are not the same.

**Acceptance Criteria:**

**Given** a Student with a finished Replay
**When** the Student opens «Gå til gjennomgangen»
**Then** the Replay-gjennomgang shows the Student's Total cost, a chart of the run, a comparison with the Class game with both on one axis, and one or two specific moments from the Student's own Orders (FR-50)
**And** every chart comes from `web/src/components/charts` and has «Vis som tabell» or a table on the same columns (AD-18, NFR-6)
**And** a Replay that Story 10.6 closed (`end_reason = test_deadline`) has no walkthrough: the API answers a stable error code and the screen keeps the closed message of Story 10.6

**Given** the walkthrough data
**When** it is built
**Then** the facts set of the Student's Replay Seat comes from `games.facts.get_or_create`, with `analysis.facts` from Epic 9 unchanged, the moments are rendered by `analysis.render` with the pinned sentence templates, and the walkthrough record stores both `fact_set_id`s (Replay and the game compared with) (AD-7)
**And** the game compared with is the Student's own game, read through `games.service.student_game(user, class_session)` from Story 6.1 and never by querying Class games directly
**And** a golden test asserts that every number in the walkthrough equals the `seat_week` rows of the two Games (NFR-9)

**Given** the comparison
**When** it shows
**Then** it carries «Ikke like for like.» and states the reasons in words: the neighbours are AI players, demand differs and the run may be shorter (FR-50, UX-DR64, UX-DR70)
**And** no text ranks the Student, praises or says which run was better

**Given** a finished Replay in a Class session with Debrief AI text on
**When** the Replay finishes
**Then** one idempotent narration job is deferred on `llm-batch`, keyed by the Replay's `fact_set_id`, calling the shared `app/ai` helper from Story 9.14 with the purpose `replay_walkthrough`; the helper takes the validator and the fallback renderer as arguments, and this story passes `analysis.validate_ai_text` and its own code renderer of the walkthrough, so `app/ai` imports only `platform` (FR-50, AD-6, AD-7, AD-9)
**And** the prompt is a versioned file under `api/app/ai/prompts/replay_walkthrough/`, and the default model config gets the new purpose in its `prompts` map as a new config row made with the command of Story 2.2, since a config is immutable once referenced (AD-6)
**And** accepted text shows with «KI-generert, kan ta feil:» from the `ai_generated` flag (FR-34)

**Given** the narration job is still live when the Student opens the walkthrough
**When** the page shows
**Then** it shows «Gjennomgangen lages.» in a Skjelett of the chart, refetches on `user:<id>`, and after a wait limit from configuration (placeholder: under one minute) shows the code-rendered walkthrough (UX-DR64, UX-DR58)

**Given** a rejection, a typed failure, or a Class session with Debrief AI text off
**When** the walkthrough shows
**Then** the same chart and numbers show from code, without AI text and without the prefix (FR-50, FR-44, FR-15)

**Given** a Student with fewer than 10 own Orders in their own game (`games.service.student_game`)
**When** the walkthrough shows
**Then** it shows at least three own moments from the Replay, with Detected pattern and mechanism, and leaves out the Class game comparison of own Orders, stating that the Class game was played mostly by AI players (FR-44)

**Given** the walkthrough
**When** Playwright runs at 320, 360 and 1440 px with axe
**Then** the pending, ready and code-fallback states pass, and another Student or an unattached Admin is refused by the API (NFR-6, AD-12)

**Covers:** FR-50, FR-44, FR-34, FR-15, NFR-6, NFR-9, AD-6, AD-7, AD-9, AD-12, AD-18, UX-DR64

### Story 10.8: Rate how believable the AI players were

As a Student,
I want to say how believable the AI players' ordering felt and whether I would have played another round,
So that the people behind the product learn whether the AI players and the repetition work.

**Acceptance Criteria:**

**Given** a Student on the Replay-gjennomgang
**When** the walkthrough has shown
**Then** two optional questions follow: a five-point scale on how believable the AI players' ordering felt, and a yes or no on whether the Student would have wanted to play another round (FR-50, FR-70)
**And** neither blocks anything: the Student can leave them unanswered and every later step stays open
**And** a Replay that Story 10.6 closed has no walkthrough (Story 10.7), so its Student is not asked

**Given** a Student whose Class game had at least one AI-held Seat in any Week
**When** the Student is on «Spillet er ferdig»
**Then** the same five-point question is offered once, below «Gå til Debrief», as a shared component added to `web/src/components/` (FR-70)
**And** a Student whose Class game had no AI-held Seat is not asked

**Given** an answer
**When** it is saved
**Then** it is stored once per Student and Game through `games.service`, with the Game's purpose and the AI mode of the Class session, and a second answer for the same Game replaces nothing and answers `409` (FR-70, AD-15)
**And** the another-round answer is stored once per Student and Class session by `modules/replay`
**And** this story only stores the answers, in tables it creates for them; the rating per AI mode is aggregated and shown by the Class report in Epic 14 (AD-13)

**Given** staff of the Class
**When** they read a Student's data
**Then** no rating is shown beside the Student's name on any staff screen, and no endpoint of this epic returns a rating to anyone but the Student who gave it

**Given** the two questions
**When** Playwright runs at 320, 360 and 1440 px with axe
**Then** the scale is a labelled radio group operable by keyboard, each option at least 44 px, with the end points labelled in words (NFR-6, UX-DR76)

**Covers:** FR-70, FR-50, NFR-6, AD-13, AD-15, UX-DR64

### Story 10.9: Let Information visibility differ in the Replay (cut list, behind `FEATURE_INFO_VISIBILITY`)

As a Lecturer,
I want to give the Replay another Information visibility than the Class games,
So that I can let Students try the same chain with more or less to see.

**Acceptance Criteria:**

**Given** `FEATURE_INFO_VISIBILITY` is off, or cut-list Story 5.16 is not built
**When** a Lecturer opens the own Replay scenario of Story 10.2
**Then** no Information visibility field is shown, every Replay runs with none, and this story is skipped as a whole; no earlier story of this epic depends on it (FR-83, AD-17)

**Given** the flag is on and Story 5.16 has added Information visibility to `GameSettings`
**When** the Lecturer edits the own Replay scenario
**Then** Information visibility is one more field of the form, prefilled from the Class session, and it can differ from the Class games; it is stored in the `engine.ReplayTemplate` of Story 10.2 and frozen by the pin provider of Story 10.1 (FR-83, FR-49, AD-4)

**Given** an own scenario with more Information visibility than the Class games
**When** the form is shown or saved
**Then** the non-blocking warning of Story 10.2 names the change and says it probably makes the Replay easier; the rule is added to the one function in `modules/sessions` that holds the warned changes, with its own test (FR-49, UX-DR48)

**Given** a Replay created from a template with Information visibility on
**When** the Student plays it
**Then** the Game's snapshot carries the setting, the Student sees the neighbour numbers where cut-list Story 6.21 is built, the three AI players get the same numbers through `seat_state`, and the Decision log records what was visible (FR-83, AD-3)

**Given** the form with the field
**When** Playwright runs at 320 and 1440 px with axe, with the flag on and off
**Then** both states pass, and the field states its scope in help text with copy from `web/src/copy/nb.ts` (NFR-6, UX-DR12)

**Covers:** FR-83, FR-49, NFR-6, AD-3, AD-4, AD-17, UX-DR12, UX-DR48

## Epic 11: Individual test

A Student who has completed the Replay can open the Individual test, answer multiple-choice items, Interactive items, long answers and Adapted items over several evenings with autosave, and submit once; what is saved is submitted automatically at the Test deadline. A Lecturer can review the question set and Item weights, preview the Adapted item templates, edit the Scoring guide, require one timed sitting and extend one Student's deadline. The epic owns `api/app/modules/tests/` and `web/src/modules/tests/`, adds the question set, Adapted item templates and Scoring guide to `modules/content`, and adds computed scoring to the shared `analysis/` folder. The real question texts and the default Scoring guide are a non-code deliverable (issue #16); the product ships with a clearly marked draft set loaded as versioned records.

### Story 11.1: Review the question set and Item weights

As a Lecturer,
I want to review the question set, take questions out and change Item weights before the Start date,
So that the Individual test fits my course and its weights always sum to 100%.

**Acceptance Criteria:**

**Given** `modules/content` from Epic 6 holds versioned records
**When** this story is built
**Then** the question set (Core items of type multiple choice, table, number and long answer, each with an Item weight, an answer key or scoring rule reference, and tags) is a new immutable versioned record type in `modules/content`, loaded from files in the repo by a content load command, and an edit always creates a new version (FR-52, AD-23)
**And** no earlier story names a content load command, so this story adds one to `modules/content` (`python -m app.content load`): it reads every record type from files, is idempotent, and rejects an item type it does not know with a stable error code
**And** the load rejects a set that lacks any of: the Starting task items referenced from the Starting task record of Story 6.3 (not copied), exactly one item tagged as using the Explanation's wording, one item tagged as an unseen Demand pattern, at least one quantity item, two or three Interactive items tagged as set in a business other than the beer chain, and the replacement Core items that a Student with fewer than 10 own Orders gets in place of Adapted items, carrying the same total weight (FR-52, FR-53, FR-80)
**And** no diagram item type is built in v1; FR-80 names a diagram only as an example, and a question on causes is a multiple-choice item [ASSUMPTION: founder confirms that diagram items wait]
**And** the shipped set is marked `draft` and holds placeholder items only; no real question text is invented in code (issue #16, C-4)

**Given** a Lecturer opens Klasseøkt → «Spørsmål og vekter» before the Start date
**When** the block loads
**Then** it lists every question with its type, its Vekt in % and «Ta ut», plus one line for the Adapted items with their total weight, default 30%, which the Lecturer can change like any other Vekt; it is one total per Class session, the same for every Student (FR-52, FR-53, UX-DR49)
**And** a draft set shows a notice that the questions are a draft and not approved, with copy from `web/src/copy/nb.ts` (issue #16)

**Given** the Lecturer changes weights or takes a question out so that the sum is not 100%
**When** the sum is shown
**Then** it updates live from the values the API accepts, reads «Sum 95 %. Vektene må bli 100 %.» and saving is blocked; the server rejects such a save with a stable error code as well (FR-52, AD-10, AD-19)

**Given** the Lecturer takes out an item tagged as a quantity item
**When** it is taken out
**Then** «Du tar ut en oppgave som måler mengder.» is shown and saving is not blocked (FR-52, UX-DR49)

**Given** the Lecturer saves a valid selection
**When** the save succeeds
**Then** the Class session stores its selection (question set version, excluded items, weights, Adapted total weight) through `tests.service`, and `sessions.lock` pins that question set version and selection at the Start date by adding them to the open map of pinned content versions in Epic 5's `SessionRuntime` (AD-23, AD-4)
**And** in `APP_ENV=production` no Class session can be locked while its question set is a `draft` version; the lock fails with a stable error code that the Lecturer sees in words [ASSUMPTION: founder confirms this block] (issue #16)

**Given** the Start date has passed
**When** a Lecturer or Assistant lecturer opens the block
**Then** it is read-only, and the API rejects any change with a stable error code (FR-18 lock points)
**And** an Assistant lecturer can never change it, by a `platform/authz` policy (AD-12)

**Given** `FEATURE_RERUN` is on and Story 5.18 is built
**When** a Lecturer creates a Class session from an earlier one
**Then** the question set version, the excluded items, the weights and the Adapted total weight are copied, because this story adds its selection to `sessions.service.copy_from` of Story 5.18; with the flag off, or Story 5.18 not built, this story adds nothing there (FR-66, AD-17)

**Given** the block is built
**When** CI runs
**Then** Playwright covers it at 320, 360 and 1440 px with an axe check, the form is one column at 320 px, the sum message is announced politely, and every string comes from `web/src/copy/nb.ts` (NFR-6, UX-DR75, AD-19)

**Covers:** FR-52, FR-53 (total weight, replacement items in the record), FR-80 (load check on items from another business), FR-18 (lock point for the question set), FR-66, FR-72, NFR-6, AD-10, AD-12, AD-17, AD-19, AD-23, UX-DR49 (Spørsmål og vekter)

### Story 11.2: Edit the Scoring guide for a Class session

As a Lecturer,
I want to read the default Scoring guide and edit it for my Class session until the Test deadline,
So that long answers and Adapted items are judged by criteria I stand behind.

**Acceptance Criteria:**

**Given** `modules/content` holds versioned records
**When** this story is built
**Then** the Scoring guide is an immutable versioned record: per long-answer question and per Adapted item template it states what is asked for, 5 to 8 coded criteria with weights, what strong and weak answers look like, and one fixed five-step scale shared by all questions; the load rejects a guide with fewer than 5 or more than 8 criteria for a question (FR-81, AD-23)
**And** the shipped default guide is marked `draft` until the founder approves it; its text is a non-code deliverable (issue #16)

**Given** a Lecturer opens Klasseøkt → «Sensorveiledning» before the Test deadline
**When** the block loads
**Then** it shows one Tekstfelt per question, each marked «Standard» or «Endret» (FR-81, UX-DR49)
**And** the Tekstfelt holds the question's descriptive guide text: what is asked for and what strong and weak answers look like; the coded criteria with their codes, wording and weights are shown read-only under it and cannot be edited in v1, so the 5-to-8 rule and the criterion codes always hold [ASSUMPTION: founder confirms that a Lecturer edits the descriptive text only]

**Given** the Lecturer edits a question's guide text and saves
**When** the save succeeds
**Then** a new Scoring guide version is created for that Class session and the earlier version is unchanged (AD-23)
**And** the server runs the same validation as the load on every save, and the question is marked «Endret»

**Given** a Scoring guide version and the Class session's model config
**When** the block or any later reader asks whether the guide is checked
**Then** the answer comes only from `content.service.is_checked(scoring_guide_version_id, model_config_id)`, added here; in this epic it always answers false and creates no table, because the `checked` record is created and written by the Control test in Epic 12 (AD-27)
**And** a version that is not checked shows «Ikke kontrollert med en Kontrolltest.» to the Lecturer (FR-81, UX-DR49)

**Given** the original Test deadline has passed
**When** a Lecturer opens the block
**Then** it is read-only, the API rejects edits with a stable error code, and the block shows the version that was in force at the deadline (FR-18, FR-81)

**Given** `FEATURE_RERUN` is on and Story 5.18 is built
**When** a Lecturer creates a Class session from an earlier one
**Then** the earlier Class session's Scoring guide version is carried over by its version id, so an edited guide stays «Endret» and keeps its checked status, because this story adds it to `sessions.service.copy_from` of Story 5.18; with the flag off, or Story 5.18 not built, this story adds nothing there (FR-66, AD-17)

**Given** the block is built
**When** CI runs
**Then** Playwright covers it at 320, 360 and 1440 px with an axe check, each Tekstfelt has its label above it, and an Assistant lecturer can read but not edit, by a `platform/authz` policy (NFR-6, AD-12, UX-DR11)

**Covers:** FR-81, FR-18 (lock point for the Scoring guide), FR-66, NFR-6, AD-12, AD-17, AD-23, AD-27 (reading the `checked` flag), UX-DR49 (Sensorveiledning)

### Story 11.3: Open the Individual test with the own-work statement

As a Student,
I want to open the Individual test once I have completed the Replay and state that the work is my own,
So that I can start answering and come back to it until the Test deadline.

**Acceptance Criteria:**

**Given** a Student has not completed the Replay
**When** they look at Stegene on Hjem
**Then** the step reads «Individuell test, åpnes når du har fullført Replay.» and the API refuses to open the test, with the gate read only through `progress.has_step(…, replay)` (FR-51, AD-16, UX-DR65)

**Given** a Student has the `replay` step and the Test deadline has not passed
**When** they open the Individual test
**Then** the own-work statement is shown first, with one primary button labelled with its effect, and no item is served by the API before the statement is accepted (FR-51, UX-DR65, UX-DR9)

**Given** the Student accepts the statement
**When** `tests.commands.open_attempt(user, class_session)` runs
**Then** one `test_attempts` row is created with the acceptance time, the pinned question set version and selection, `effective_deadline` (read from Epic 5's `sessions.service.effective_test_deadline(user, class_session)`) and status `open`, together with the attempt's frozen ordered item list; a second call returns the same attempt (FR-51, AD-23)
**And** in the same transaction `open_attempt` calls `close_follow_up` in `debrief/service.py` (Epic 9), so the Student's Debrief follow-up questions close when their Individual test opens; a test proves that a follow-up question is refused afterwards (FR-45)
**And** the tables `test_attempts` and `answers` are created in this story and owned by `modules/tests`

**Given** the Deferred item "Test attempt write path"
**When** this story is built
**Then** it records the decision in the module's README and in code: `tests.commands` is the only writer of an attempt and its answers, with the commands `open_attempt`, `save_answer`, `submit`, `close_attempt` and `extend_deadline`; every command that acts on an existing attempt takes `SELECT … FOR UPDATE` on the attempt row and runs in one transaction; `save_answer` and `submit` on an attempt that is not `open` fail with `attempt_submitted`, and on an open attempt after its `effective_deadline` fail with `test_deadline_passed` (AD-9, AD-10)
**And** where no attempt row exists yet, the lock is named: `open_attempt` relies on the unique key on User and Class session and returns the existing attempt on a conflict, and `extend_deadline` locks the Student's extension row in `modules/sessions`, and the attempt row too when there is one
**And** this story implements `open_attempt`; the other commands arrive in Story 11.4, Story 11.10, Story 11.11 and Story 11.13, and Story 11.12 adds `end_sitting` to the list

**Given** a Student with an open attempt returns on any device
**When** they open the Individual test
**Then** the statement is not asked again and the items show with the answers saved so far (FR-51, NFR-5)

**Given** another User requests an attempt
**When** the request is checked
**Then** a Student reaches only their own attempt, the Admin reaches no attempt without Class membership, and a denied request does not reveal whether the attempt exists, all through `platform/authz` policies and scoped queries (FR-5, AD-12, UX-DR59)

**Given** the screens are built
**When** CI runs
**Then** Playwright covers locked, statement and open states at 320, 360 and 1440 px with an axe check, loading uses Skjelett from Epic 3, and all copy comes from `web/src/copy/nb.ts` (FR-73, NFR-6, UX-DR75)

**Covers:** FR-51, FR-45 (follow-up closes when the test opens), FR-5, FR-72, FR-73, NFR-5, NFR-6, AD-9, AD-10, AD-12, AD-16, AD-23, UX-DR65 (locked, own-work statement, open)

### Story 11.4: Answer multiple-choice items with autosave

As a Student,
I want my multiple-choice answers saved as I go,
So that I can close the test and return without losing anything.

**Acceptance Criteria:**

**Given** an open attempt with multiple-choice items
**When** the Student opens an item
**Then** it shows as single choice with the Quizvalg control reused from `web/src/components/` (Epic 9), and no right or wrong state or explanation is shown at any time before the AI assessment (FR-52, FR-54)

**Given** the Student picks or changes a choice
**When** the web app autosaves
**Then** it calls `tests.commands.save_answer(attempt, item, value, revision)` with a per-answer revision number that rises by one per change; the server stores the answer only if the revision is higher than the stored one, and otherwise returns the stored revision without an error (AD-10)
**And** «Lagret 21:14» is shown with the time in Europe/Oslo and announced politely (FR-51, UX-DR65)

**Given** an autosave fails or the device is offline
**When** the Student keeps working
**Then** «Ikke lagret. Svarene ligger på denne enheten, og vi prøver igjen.» is shown, the answer is kept through `web/src/lib/drafts.ts` keyed by User and item, and the save is retried until it succeeds (FR-51, AD-10, UX-DR65)

**Given** the same attempt is open on two devices
**When** both save the same item
**Then** the attempt row lock serialises the saves and the highest revision is the one stored (AD-10)

**Given** a multiple-choice answer and the item's answer key
**When** it is scored
**Then** the score comes only from the pure function `analysis.scoring.score_choice`, added to the existing `api/app/analysis/scoring.py` that Epic 6 created for the Starting task (extended, never a second copy), with no I/O and with pytest covering right, wrong and unanswered (FR-52, AD-1, AD-9)
**And** no score is computed in the web app or returned to the Student while the attempt is open (AD-10)

**Given** the item screens are built
**When** CI runs
**Then** Playwright covers idle, selected, saved and save-failed states at 320, 360 and 1440 px with an axe check, each choice is a 44 px tap target and is operable by keyboard (NFR-6, UX-DR76)

**Covers:** FR-51, FR-52, NFR-6, AD-1, AD-9, AD-10, UX-DR65 («Lagret 21:14», autosave failure)

### Story 11.5: Answer table and number Interactive items

As a Student,
I want to answer Interactive items by filling in a value table or a number,
So that I can show quantities and consistency, with keyboard or screen reader alone.

**Acceptance Criteria:**

**Given** an open attempt with a «Fyll inn kolonnen» item
**When** the Student opens it
**Then** the Interaktiv oppgave component shows the value table without a graph: an HTML `<table>` with `th` scopes and one outlined numeric cell per Uke, where unanswered Uker show an empty cell and «Ikke besvart» beside the row label (FR-80, UX-DR38)
**And** the component is built in `web/src/modules/tests/` so that Story 11.14 can add the graph over the same table

**Given** the Student types in a cell
**When** the value is not a whole number (with a leading minus only where the item allows negative quantities)
**Then** the cell shows the Ordrefelt error pattern with «Skriv et helt tall.» on leaving the cell, and the invalid value is not saved (UX-DR38, UX-DR20)

**Given** the Student changes a valid cell or a number-entry answer
**When** the change is made
**Then** it autosaves through `tests.commands.save_answer` with the per-answer revision and shows «Lagret 21:14», reusing Story 11.4's save path (FR-51, AD-10, UX-DR38)

**Given** the Starting task items that the question set repeats
**When** they appear in the test
**Then** they render with the Starting task item component reused from `web/src/components/` (Epic 6), are scored by the Starting task rules already in `analysis/scoring.py`, and no right or wrong state is shown (FR-52, FR-85)

**Given** a stored table or number answer and the item's scoring rule
**When** it is scored
**Then** the score comes only from `analysis.scoring.score_interactive(values, rule)`, a pure function that gives partial credit per coded criterion on quantities and consistency (units added equal units missing; the stock agrees with its flows) and never on whether the answer looks like oscillation; it also returns the computed explanation per criterion (FR-80, AD-1, AD-9)
**And** pytest golden cases cover a fully right answer, each single criterion failing, an empty answer and a partly filled table

**Given** an Interactive item's introduction
**When** the Student reads it
**Then** it says that these items are hard, also for well-educated adults, with copy from `web/src/copy/nb.ts`, and the item uses «enheter», never «øl» (FR-80, UX-DR74)

**Given** the item screens are built
**When** CI runs
**Then** Playwright answers a table item by keyboard alone at 320, 360 and 1440 px and at 200% text, with an axe check; at narrow widths the value table scrolls inside its own region with a sticky label column and the page has no horizontal scroll (FR-73, FR-80, NFR-6, UX-DR75)

**Covers:** FR-80 (table and number entry, computed scoring), FR-52, FR-73, NFR-6, AD-1, AD-9, AD-10, UX-DR38 (value table, «Fyll inn kolonnen», cells autosave, scoring reads table values)

### Story 11.6: Write long answers with autosave

As a Student,
I want to write long answers that save automatically,
So that I can build my argument over several evenings.

**Acceptance Criteria:**

**Given** an open attempt with long-answer items
**When** the Student opens one
**Then** it shows the question and a multi-line Tekstfelt with its label above, and the item tagged as using the Explanation's wording shows that wording unchanged from the pinned question set (FR-52, UX-DR11)

**Given** the Student types
**When** typing pauses, the field loses focus or the page is hidden
**Then** the text autosaves through `tests.commands.save_answer` with the per-answer revision, and «Lagret 21:14» is shown and announced politely without moving focus (FR-51, AD-10, UX-DR65)
**And** the debounce interval is configuration with a placeholder value

**Given** a save fails or the session has expired
**When** the Student continues or logs in again
**Then** the text is kept in `web/src/lib/drafts.ts`, «Ikke lagret. Svarene ligger på denne enheten, og vi prøver igjen.» is shown, and after login the kept text is saved with a higher revision (AD-10, UX-DR59, UX-DR65)

**Given** the Student is on a phone-width screen
**When** a long-answer item opens
**Then** the advice to use a larger screen is shown above the field, and the Student can still write and save there (FR-73, UX-DR65)

**Given** a long answer is stored
**When** it is saved
**Then** the Student's text is stored unchanged as the original; no LLM is called and no score is computed for long answers in this epic (FR-54, AD-7)
**And** no answer text is written to logs (structlog convention)

**Given** the screen is built
**When** CI runs
**Then** Playwright covers typing, saved, save-failed and restored-draft states at 320, 360 and 1440 px with an axe check (NFR-6)

**Covers:** FR-51, FR-52, FR-73, NFR-6, AD-10, UX-DR65 (larger-screen advice, «Lagret 21:14», autosave failure)

### Story 11.7: Get Adapted items from my own game and Replay

As a Student,
I want some questions to be about specific Weeks and Orders in my own game and Replay,
So that the test asks about decisions I actually made.

**Acceptance Criteria:**

**Given** `modules/content` and the `fact_sets` of Story 9.1
**When** this story is built
**Then** Adapted item templates are immutable versioned records in `modules/content`, the same templates for every Student, each naming the kind of fact it needs (a Week, an Order, an outcome, a Detected pattern) and pinned at `sessions.lock` through the map of pinned content versions in `SessionRuntime`; the shipped templates are marked `draft` (FR-53, AD-23, issue #16)

**Given** a Student opens the Individual test
**When** `tests.commands.open_attempt` of Story 11.3 runs
**Then** this story extends it to build the Student's Adapted items from code in the same transaction and to store them on the attempt as frozen items, so opening never waits on a job or an LLM call (FR-53)
**And** the items carry the Adapted total weight of Story 11.1 between them

**Given** the Adapted items of a Student are built
**When** the templates are filled
**Then** the facts come only from the stored fact sets of the Student's Seat in their own game and of their Replay Seat, through `games.facts.get_or_create`; the Student's own game is read through `games.service.student_game(user, class_session)` from Story 6.1, never by querying Class games directly (FR-53, AD-7)
**And** each item stores its `fact_set_id` and fact ids, code renders every number, Week and Role into the text, and the text travels as `{text, ai_generated: false, llm_call_id: null}`
**And** a golden test asserts that every number in every item equals the `seat_week` rows of the two Games (NFR-9)

**Given** a Student with fewer than 10 own Orders in their own game, counted from the Decision log through the one `decided_by` mapping
**When** their items are built
**Then** they get the replacement Core items that the question set of Story 11.1 names instead, carrying the same total weight (FR-53, AD-15)

**Given** an attempt has been opened
**When** a newer template version is loaded, or `open_attempt` is called again
**Then** the items frozen on the attempt do not change, and a test proves it (Deferred: an Adapted item never changes after a Student has seen it)

**Given** an Adapted item is shown in the test
**When** the Student answers it
**Then** it is answered as a long answer with the autosave of Story 11.6, and Playwright covers an Adapted item at 320, 360 and 1440 px with an axe check (FR-53, NFR-6, UX-DR65)

**Covers:** FR-53, NFR-6, NFR-9, AD-7, AD-15, AD-23, UX-DR65 (items in the open test)

### Story 11.8: Read Adapted items in natural wording

As a Student,
I want my Adapted items worded as plain questions where an AI has written them, and marked as such,
So that they read well and I know which text an AI produced.

**Acceptance Criteria:**

**Given** the Deferred item "Timing of Adapted items"
**When** this story is built
**Then** it records and implements this decision: `ops.sweep` gets a due action that finds each Student with the `replay` step, no opened attempt and no prepared set, and defers the idempotent job `tests.prepare_adapted(user_id, class_session_id)` on `llm-batch`; the job stores one prepared set per Student, and `tests.commands.open_attempt` copies the prepared set into the attempt as its frozen items (AD-9)
**And** if no prepared set exists when the Student opens the test, the code-built items of Story 11.7 are frozen as before, so opening never waits on an LLM call

**Given** the job prepares a Student's set
**When** it asks for wording
**Then** it starts from the code-built items of Story 11.7 and requests the wording through `ai.run` with the purpose `adapted_item_wording` and the Class session as `budget_scope`; the output schema references fact ids and sentence-template ids only, and code renders every number, Week and Role into the text (FR-53, AD-6, AD-7)
**And** the prompt is a versioned file under `api/app/ai/prompts/adapted_item_wording/`, and the default model config gets the new purpose in its `prompts` map as a new config row made with the command of Story 2.2, since a config is immutable once referenced (AD-6)

**Given** the wording comes back
**When** it is checked
**Then** the AI-text validator of Story 9.14 checks it against the item's stored `fact_set_id`, and on a rejection or a typed failure the code-rendered text of Story 11.7 stays; the job never retries the call itself, and text travels as `{text, ai_generated, llm_call_id}` (AD-6, AD-7)

**Given** an attempt has been opened
**When** the prepare job runs again or the LLM text arrives late
**Then** the items frozen on the attempt do not change, and a test proves it (Deferred: an Adapted item never changes after a Student has seen it)

**Given** an Adapted item is shown in the test
**When** its text was produced by an LLM
**Then** it carries the prefix «KI-generert, kan ta feil:» and the machine-readable mark, taken from the `ai_generated` flag only; a code-rendered item carries neither (FR-34, FR-53, UX-DR69)

**Given** this story is built
**When** CI runs
**Then** pytest covers on the mock provider: a prepared set copied on open, a rejected wording, a typed failure, a job that runs after the attempt was opened, and a sweep run twice; Playwright covers a marked item at 360 and 1440 px with an axe check (AD-9, AD-17, NFR-6)

**Covers:** FR-53, FR-34 (AI text mark on Adapted items), NFR-6, AD-6, AD-7, AD-9, AD-17, UX-DR65 (items in the open test), UX-DR69 (prefix on AI text)

### Story 11.9: Preview the Adapted item templates with a sample Student

As a Lecturer,
I want to preview the Adapted item templates filled with a sample Student's games before the Start date,
So that I know what kind of questions my Students will get about their own decisions.

**Acceptance Criteria:**

**Given** a Lecturer opens the Adapted item preview from «Spørsmål og vekter» before the Start date
**When** the preview loads
**Then** each template of the version the Class session will pin is shown filled for one sample Student, labelled «Demodata», with the Adapted total weight of Story 11.1 beside it (FR-53, UX-DR70)

**Given** the sample
**When** this story is built
**Then** it ships a static sample facts set in the repo, built with `analysis.facts` from a golden Decision log fixture of Story 9.1 in which a Student placed the Orders (its golden Game with a Takeover), because an engine trace has no `decided_by` and a Seat with fewer than 10 own Orders has no moments to fill a template with; the preview renders from that set with the code renderer of Story 11.7, creates no Game row, does not call `games.facts.get_or_create` and makes no LLM call (FR-53, AD-7)
**And** a test asserts that every number in the preview equals that fixture's `seat_week` rows, and that the sample set is rebuilt from the fixture and compared in CI, so it cannot drift from `analysis.facts`

**Given** the templates are a `draft` version
**When** the preview shows
**Then** it carries the same draft notice as «Spørsmål og vekter» in Story 11.1 (issue #16)

**Given** an Assistant lecturer of the Class, or a User outside it
**When** they open the preview
**Then** the Assistant lecturer can read it and the User outside the Class is refused, through `platform/authz` (AD-12)

**Given** the preview is built
**When** CI runs
**Then** Playwright covers it at 320, 360 and 1440 px with an axe check, and all copy comes from `web/src/copy/nb.ts` (NFR-6, AD-19)

**Covers:** FR-53 (Lecturer preview), NFR-6, NFR-9, AD-7, AD-12, AD-19, UX-DR70 (Demodata label)

### Story 11.10: Review and submit the Individual test

As a Student,
I want to review what I have not answered and submit once,
So that I know exactly what I hand in.

**Acceptance Criteria:**

**Given** an open attempt
**When** the Student presses «Lever testen»
**Then** a review opens that lists the unanswered items, for example «3 oppgaver er ikke besvart: 4, 7 og 9.», each number a link to its item, and shows «Du kan ikke endre svarene etter at du har levert.» above the one primary button «Lever testen»; no further confirmation dialog follows (FR-51, UX-DR65, UX-DR78)

**Given** every item is answered
**When** the review opens
**Then** it says so in text and shows the same primary button

**Given** the Student confirms in the review
**When** `tests.commands.submit(attempt)` runs
**Then** in one transaction under the attempt row lock it sets the status to `submitted` with the time, computes the answer-key and Interactive scores through `analysis.scoring` and stores them on the answers with the question set version they were scored with, and calls `progress.record_step(user, class_session, test_submitted, at)` (FR-51, AD-9, AD-16, AD-23)
**And** a second submit returns the already submitted attempt without changing it

**Given** a submitted attempt
**When** any device sends `save_answer` or `submit`, including a retried autosave from `drafts.ts`
**Then** the API rejects it with the error code `attempt_submitted`, the web app drops the draft and shows the submitted state (Deferred: Test attempt write path)

**Given** the submit succeeds
**When** the Student sees the result
**Then** «Levert to. 18. des kl. 21:40. Du kan ikke endre svarene.» is shown with the real time in Europe/Oslo, focus moves to that message, the answers are readable but read-only, and Stegene on Hjem marks the step done through the `user:<id>` event from `record_step` (FR-51, AD-8, UX-DR65, UX-DR29)

**Given** the submit request fails or times out
**When** the Student sees the error
**Then** the inline «Det ble ikke lagret. Prøv igjen.» is shown with `role="alert"`, the button stays active, and the attempt is still open (UX-DR59)

**Given** the Test deadline reminder of Story 5.14
**When** its recipients are resolved
**Then** a Student with the `test_submitted` step gets no Test deadline reminder: this story narrows `sessions.service.reminder_recipients(class_session_id, deadline)` for the Test deadline with `progress.has_step`, as Story 5.14 left open, without changing the sweep; an api test covers a submitted and a not submitted Student (FR-18, AD-16)

**Given** the screens are built
**When** CI runs
**Then** Playwright covers review with and without unanswered items, submitted, and save-after-submit at 320, 360 and 1440 px with an axe check; an api test asserts that `record_step` emits exactly its registered topics (NFR-6, AD-8)

**Covers:** FR-51, FR-18 (no Test deadline reminder after submit), NFR-6, AD-8, AD-9, AD-10, AD-16, AD-23, UX-DR65 (review before submit, submitted)

### Story 11.11: Have saved answers submitted automatically at the Test deadline

As a Student,
I want my saved answers handed in automatically when the Test deadline passes,
So that my work counts even if I did not press submit.

**Acceptance Criteria:**

**Given** a Class session whose original Test deadline has passed
**When** `ops.sweep` runs
**Then** it first calls `sessions.lock_test(class_session)`, added in this story, which pins the Scoring guide version in force for the Class session into the map of pinned content versions in `SessionRuntime`, once and idempotently; only after that does it handle due attempts (AD-9, AD-23, FR-81)

**Given** an attempt whose `effective_deadline` has passed
**When** the sweep calls `tests.commands.close_attempt(attempt_id)`
**Then** if the attempt is still `open` it is set to `auto_submitted`, its saved answers are scored through `analysis.scoring` and stored exactly as in Story 11.10, and `test_submitted` is recorded through `progress.record_step`; if it was already submitted nothing changes (FR-51, AD-9, AD-16)
**And** the sweep handles one attempt per transaction, the job arguments are ids only, and running it twice gives the same result
**And** `effective_deadline` is only ever the Class session's Test deadline or the Student's extension (AD-9), never earlier, so `close_attempt` runs for every attempt, submitted or not, and always after `sessions.lock_test`; it is the one place where Epic 12 later starts the AI assessment

**Given** the order of the Test deadline actions (Deferred: Test attempt write path)
**When** this story is built
**Then** the recorded order is: `sessions.lock_test`, then `tests.close_attempt` per due attempt; a `save_answer` that arrives after the `effective_deadline` but before the sweep is rejected with `test_deadline_passed`, so what is submitted is what was saved before the deadline

**Given** a Student whose attempt was auto-submitted
**When** they open the Individual test
**Then** they see «Testfristen er passert. Svarene dine ble levert automatisk.» and their answers read-only (FR-51, UX-DR65)

**Given** a Student who never opened the test
**When** the Test deadline has passed
**Then** no attempt is created, the test shows «Testfristen er passert. Testen er ikke levert.», the step stays «ikke gjort» and the API refuses `open_attempt` with `test_deadline_passed` (FR-18, FR-51, UX-DR65)

**Given** an auto-submitted attempt
**When** Completion is later computed (Epic 13)
**Then** the attempt exposes, through `tests.service`, which required parts have content, so the FR-17 minimum can be applied without reading answers from another module (FR-17, AD-16)

**Given** this story is built
**When** CI runs
**Then** pytest covers the chain with a frozen clock: lock before close, repeat runs, an already submitted attempt, a never-opened Student and a late save; Playwright covers the two deadline states at 360 and 1440 px (AD-9)

**Covers:** FR-51, FR-18 (saved answers submitted at the Test deadline), FR-81 (guide in force at the deadline), AD-9, AD-16, AD-23, UX-DR65 (auto-submitted, never opened)

### Story 11.12: Require one timed sitting

As a Lecturer,
I want to require that the Individual test is taken in one sitting with a time limit,
So that I can use the test where my course needs a bounded attempt.

**Acceptance Criteria:**

**Given** a Lecturer is on the Klasseøkt screen before the Start date
**When** they turn on the one-sitting option in the test settings and enter a time limit in whole minutes
**Then** the choice is stored with the Class session through `tests.service`, uses the Bryter and Tekstfelt controls from earlier epics, states its scope in help text and applies on «Lagre Klasseøkt»; an out-of-range value is rejected with the range shown (FR-51, UX-DR12)
**And** the limit's allowed range is configuration with placeholder values, and the setting is read-only after the Start date [ASSUMPTION: locked with the question set]

**Given** the option is on
**When** a Student sees the own-work statement
**Then** it also states the time limit and that the time starts when they open the test and cannot be paused, before the button is pressed (FR-51, UX-DR9)

**Given** the Student opens the test
**When** `open_attempt` runs
**Then** the attempt gets `sitting_ends_at`, a column this story adds to `test_attempts`: the opening time plus the limit, where the limit is first multiplied by the Student's time factor from `sessions.service.get_adjustment(class_session, user)` of Story 8.9 where one is recorded (FR-17, FR-51)
**And** `effective_deadline` stays what AD-9 says, the Class session's Test deadline or the Student's extension, and the time limit never changes it; one function, `tests.rules.answering_ends_at(attempt)`, returns the earlier of `sitting_ends_at` and `effective_deadline`, and `save_answer` and `submit` are refused after it

**Given** a timed attempt is open
**When** the Student works
**Then** the remaining time is shown from the API's `server_now` and `answering_ends_at`, in text and not by colour alone, and is announced politely at most once a minute and at the last minute (AD-8, NFR-6)
**And** closing the browser does not stop the clock, and the Student can return within the time

**Given** the time runs out before the Test deadline
**When** `ops.sweep` finds an open attempt whose `sitting_ends_at` has passed
**Then** it calls the new command `tests.commands.end_sitting(attempt_id)`, added to the command list of Story 11.3: under the attempt row lock it sets the attempt to `auto_submitted`, scores and stores the saved answers exactly as in Story 11.10 and records `test_submitted`; it is idempotent and takes ids only (FR-51, AD-9)
**And** `end_sitting` does not call `close_attempt` and starts nothing else: `close_attempt` of Story 11.11 still runs for this attempt at its `effective_deadline`, after `sessions.lock_test`, so nothing that hangs on the Test deadline happens early for a timed sitting (FR-54, AD-9)
**And** the Student sees that the time ran out and that the saved answers were handed in; a save between the end of the sitting and the sweep is rejected with `sitting_ended`, and a later save with `attempt_submitted`

**Given** the option is off
**When** a Student opens the test
**Then** nothing about a time limit is shown, `sitting_ends_at` is empty and the attempt stays open until the Test deadline (FR-51)

**Given** `FEATURE_RERUN` is on and Story 5.18 is built
**When** a Lecturer creates a Class session from an earlier one
**Then** the one-sitting option and its time limit are copied, because this story adds them to `sessions.service.copy_from` of Story 5.18; with the flag off, or Story 5.18 not built, this story adds nothing there (FR-66, AD-17)

**Given** the option is built
**When** CI runs
**Then** pytest covers with a frozen clock: a sitting that ends before the Test deadline, one that would end after it, a Student with a time factor, and `close_attempt` at the Test deadline on an attempt that `end_sitting` already submitted; Playwright covers the statement with the limit and the running time at 360 and 1440 px with an axe check (AD-9, NFR-6)

**Covers:** FR-51 (one-sitting time limit), FR-17 (per-Student adjustment of a timed sitting), FR-66, NFR-6, AD-8, AD-9, AD-17, UX-DR65

### Story 11.13: Extend one Student's Test deadline

As a Lecturer,
I want to move one Student's Debrief and Test deadlines together,
So that a Student with a valid reason can finish without holding back the rest of the Class session.

**Acceptance Criteria:**

**Given** a Lecturer opens a Student's Studentside (the minimal page from Epic 8, Story 8.9) and its new deadline block, added in this story as an in-place form following that page's one-form-at-a-time rule
**When** they enter a new Test deadline later than the Class session's and save
**Then** `tests.commands.extend_deadline(user, class_session, new_test_deadline)` stores the extension through `sessions.service` (a per-Student extension row owned by `modules/sessions`, moving the Debrief and Test deadlines by the same amount) and, in the same transaction, updates `effective_deadline` on the Student's open attempt if one exists (FR-18, AD-9)
**And** a timed sitting keeps its `sitting_ends_at` from Story 11.12, so an extension never lengthens a running time limit; the command locks the Student's extension row, and the attempt row when there is one, as Story 11.3 recorded
**And** the form has no field for a reason, the action is recorded through `platform/audit`, and `user:<id>` is emitted for that Student (AD-8, AD-15)

**Given** a date that is not later than the Class session's Test deadline, or a Student whose attempt is already submitted
**When** the Lecturer saves
**Then** the save is rejected inline with the reason; an extension only ever extends (FR-18)

**Given** a Student with an extension
**When** they look at Hjem or open the Individual test
**Then** their next deadline shows their own date and the test stays open until it (FR-18)
**And** this story extends both functions of Story 5.2, `sessions.service.effective_test_deadline(user, class_session)` and `sessions.service.effective_debrief_deadline(user, class_session)`, to return the per-Student value where one exists; it creates no second function, so the Debrief, Debrief quiz and Replay gates of Epics 9 and 10, which already read through them, stay open for this Student until their own date, and a test proves it

**Given** a Student with an extension and the deadline reminders of Story 5.14
**When** the sweep looks for reminders that are due
**Then** this story adds a per-Student due action: `sessions.service.send_deadline_reminder` gains the case of one Student's own Debrief or Test deadline, enqueued 24 hours before the Student's own date as the same `digest` kind, with a dedupe key that holds the user id, the deadline kind and the deadline time (FR-18, AD-9)
**And** `sessions.service.reminder_recipients` leaves that Student out of the class-wide Debrief and Test deadline reminders, so the Student gets one reminder per deadline and for their own date; an api test with a controlled clock covers both

**Given** the Class session's original Test deadline passes
**When** the sweep runs
**Then** `sessions.lock_test` still pins the Scoring guide at the original deadline, the other Students' attempts are closed, and the extended Student's attempt is closed only at its own `effective_deadline` (FR-18, AD-9)

**Given** an Assistant lecturer or a Lecturer of another Class
**When** they try to extend
**Then** the `platform/authz` policy denies it (AD-12)

**Given** the form is built
**When** CI runs
**Then** Playwright covers save, rejected date and the Student's own view at 360 and 1440 px with an axe check; the form's Norwegian strings are not given in EXPERIENCE.md, so they are added to `web/src/copy/nb.ts` and listed for founder review; the result line replaces the form and receives focus, as for the other Studentside blocks

**Covers:** FR-18 (per-Student test extension), NFR-6, AD-8, AD-9, AD-12, AD-15

### Story 11.14: Answer drawn Interactive items in a graph (after the rehearsal, may be skipped for the pilot)

As a Student,
I want to place points in a graph that is backed by the value table,
So that I can draw a stock over time, by pointer or by keyboard.

**Acceptance Criteria:**

**Given** this story is not built, which is the state until computed scoring of table items has been checked against hand scoring in the rehearsal (FR-80; spine Deferred "Drawn Interactive items")
**When** the content load command of Story 11.1 reads a question set with an item of type `drawn`
**Then** the load rejects the set as an unknown item type, and no other story of any epic depends on this one, so the pilot can run without it
**And** from this story on the load accepts `drawn` items, and an api test loads a set that holds one

**Given** a drawn item in an open attempt
**When** the Student opens it
**Then** the Interaktiv oppgave shows one graph over the value table of Story 11.5, built from `web/src/components/charts` with a fixed width: an 8 px `ink` point per Uke joined by a 2 px `ink` line, and unanswered Uker with no point (FR-80, AD-18, UX-DR38)

**Given** the Student drags a point or taps a column
**When** the point is placed
**Then** the value is written into that Uke's table cell, and typing in a cell redraws the curve; graph and table are one answer, saved through the same `save_answer` path with «Lagret 21:14» (UX-DR38, AD-10)

**Given** a keyboard user
**When** they tab into the graph
**Then** each point is a `role="slider"` named «Uke 3» with `aria-valuetext` «Uke 3: 14 enheter», Up and Down change it by 1 unit, PageUp and PageDown by 10, Tab moves to the next Uke's point and after the last into the table; no task needs a drag (FR-80, UX-DR38, UX-DR76)

**Given** a screen reader user
**When** they answer the item
**Then** the table alone answers it, and the graph is presented as a view of the table (FR-80, NFR-6)

**Given** a drawn answer is scored
**When** `analysis.scoring.score_interactive` runs
**Then** it reads the table values only, so pointer and keyboard answers with the same values score the same, and a test proves it (FR-80, UX-DR38)

**Given** the item is built
**When** CI runs
**Then** Playwright places points by pointer and by keyboard at 320, 360 and 1440 px and at 200% text with an axe check, the graph columns line up with the table columns, and the graph and table scroll as one region at narrow widths (NFR-6, AD-18, UX-DR75)

**Covers:** FR-80 (drawn items), FR-73, NFR-6, AD-10, AD-18, UX-DR38 (graph over value table, drag or tap, point sliders)

## Epic 12: AI assessment and Control test

After the Test deadline a Student can read an AI assessment of their Individual test: computed scores, one overall score with written feedback per long-answer and Adapted item, and a weighted total, always labelled as AI-generated, possibly wrong and not a grade. A Lecturer can switch the AI assessment off, read it for their Students, see flags and set the Indicative letter; the Admin can run a Control test where humans score blind and the product shows how well the AI agrees. The epic owns `api/app/modules/assessment/` and `web/src/modules/assessment/`, adds `total_score`, `indicative_letter` and `agreement` to the shared `analysis/` folder, and adds the `control_test` kind to `modules/sessions`.

### Story 12.1: Switch the AI assessment off for a Class session

As a Lecturer,
I want to turn off the AI assessment for a Class session until the Test deadline,
So that I can follow my Institution's data protection officer and still get computed scores and Student reports.

**Acceptance Criteria:**

**Given** a Lecturer opens Klasseøkt → «KI-vurdering» before the Test deadline
**When** the block loads
**Then** it shows the Bryter «KI-vurdering» (reused from Epic 5), on by default, with the help text «Flervalg og interaktive oppgaver rettes fortsatt automatisk. Studentrapporten finnes som vanlig.» (FR-61, UX-DR49)

**Given** the Lecturer changes the switch and presses «Lagre Klasseøkt»
**When** the save succeeds
**Then** the value is stored on the Class session through `assessment.service`, and `session:<id>` is emitted (FR-61, AD-8)

**Given** the original Test deadline passes
**When** `sessions.lock_test` runs (built in Epic 11)
**Then** this story extends it to pin the switch value for the Class session in the same step that pins the Scoring guide, once and idempotently (AD-9, FR-18)
**And** after that the block is read-only and the API rejects a change with a stable error code

**Given** the pinned switch is off
**When** attempts are closed and scored
**Then** answer-key and Interactive scores are stored as before, no AI assessment is created, and no LLM call is made for assessment in that Class session, proved by a test (FR-61, AD-9)

**Given** an Assistant lecturer
**When** they open the block
**Then** they can read the value but not change it, by a `platform/authz` policy (AD-12)

**Given** `FEATURE_RERUN` is on and Story 5.18 is built
**When** a Lecturer creates a Class session from an earlier one
**Then** the value of the «KI-vurdering» switch is copied, because this story adds it to `sessions.service.copy_from` of Story 5.18; with the flag off, or Story 5.18 not built, this story adds nothing there (FR-66, AD-17)

**Given** the block is built
**When** CI runs
**Then** Playwright covers on, off and locked at 320, 360 and 1440 px with an axe check, and the switch has a text label and is never state by colour alone (NFR-6, UX-DR12)

**Covers:** FR-61, FR-18 (lock point for the AI assessment switch), FR-66, NFR-6, AD-8, AD-9, AD-12, AD-17, UX-DR49 (KI-vurdering switch)

### Story 12.2: Get an AI assessment with scores and a weighted total

As a Student,
I want my submitted test assessed after the Test deadline, with a score per item and a total,
So that I can see where I stand without it counting toward anything.

**Acceptance Criteria:**

**Given** `tests.commands.close_attempt` from Story 11.11 and a pinned switch that is on
**When** an attempt is closed at its `effective_deadline`, whether the Student submitted it earlier, a timed sitting ended it earlier (Story 11.12) or it is auto-submitted now
**Then** this story extends `close_attempt` to defer `assessment.assess(attempt_id)` on the `llm-batch` queue in the same transaction, through `assessment.service`; nothing else enqueues a first AI assessment, and an attempt submitted before the deadline is not assessed before the deadline (FR-54, AD-9)
**And** because `effective_deadline` is never before the Class session's original Test deadline, `sessions.lock_test` has always pinned the Scoring guide and the switch before any assessment starts; an api test with a timed sitting that ended days earlier proves that it is assessed at the Test deadline and not before

**Given** the `assess` job runs
**When** it scores a long-answer or Adapted item
**Then** it makes one `ai.run(purpose="assessment", budget_scope=<Class session>, …)` call per item, passing the question, the Student's answer, the pinned Scoring guide entry and, for Adapted items, the item's stored fact set; the output schema holds one overall score on the guide's five-step scale and never per-criterion scores (FR-54, FR-81, AD-6)
**And** the job reads only the pinned Scoring guide version, question set version and model config, passes no model, prompt version or scrub terms, and never retries a typed failure itself; the prompt is a versioned file under `api/app/ai/prompts/assessment/`, and the default model config gets the `assessment` purpose in its `prompts` map as a new config row made with the command of Story 2.2, since a config is immutable once referenced (AD-6, AD-9, AD-23)
**And** scrubbing relies on the gateway and on `platform/pii.terms` querying the Roster (Story 9.15); this story adds its own test that a Roster name, email and student number written in a test answer do not appear in the request the provider receives (C-1, AD-6)

**Given** the item scores exist
**When** the total is computed
**Then** it comes only from the pure function `analysis.total_score(computed, ai_items, weights)`, added to `api/app/analysis/`, using the pinned Item weights; `assessment` stores AI item scores only and never copies or recomputes the computed scores that `tests` stored (FR-54, AD-9)
**And** pytest covers the function with golden cases, including excluded questions and the fixed Adapted weight

**Given** an assessment is stored
**When** it is written
**Then** the tables `ai_assessments` and `ai_item_scores` are created in this story and owned by `modules/assessment`; each row stores the Scoring guide version, question set version, model config id and `llm_call_id` it was produced with; the job is idempotent on `attempt_id` and a repeat run adds no second assessment (AD-23, AD-9)

**Given** a call returns `timeout`, `provider_error`, `invalid_output` or `budget_exhausted`
**When** the job handles it
**Then** the item is left unassessed and that job run makes no second call for it, since callers never retry (AD-6); the run ends by deferring one later run of the same idempotent job, with a back-off delay from configuration, and that run makes one new call per item that is still unassessed
**And** while any item is unassessed the assessment is `incomplete`, has no total, and the Student sees a note saying which items lack an assessment [ASSUMPTION: no partial total] (FR-54, AD-6)
**And** the assessment row counts its job runs, and a maximum from configuration (a placeholder) caps them: at the maximum the assessment gets the final state `failed`, no further run is deferred, there is no total and no letter, and the Student sees a note that the AI assessment could not be made and that the computed scores are in the Student report

**Given** a Student opens «KI-vurdering» from Hjem
**When** the assessment is not ready
**Then** they see «KI-vurderingen kommer innen ett døgn etter testfristen.»; when the pinned switch is off they see «Faglærer har slått av KI-vurdering for denne Klasseøkten. Studentrapporten finnes som vanlig.» (FR-54, FR-61, UX-DR66)

**Given** the assessment is ready
**When** the Student opens it
**Then** the view starts with «KI-generert, kan ta feil. Teller ikke. Ingen karakter.», then shows per item the computed score with its computed explanation for answer-key and Interactive items, the overall score for each long-answer and Adapted item, and the weighted total; there is no pass or fail and no letter (FR-54, FR-55, FR-80, UX-DR66)
**And** all numbers go through the shared number formatter, and Playwright covers not ready, switched off, ready, incomplete and failed at 320, 360 and 1440 px with an axe check (NFR-6, UX-DR5)

**Covers:** FR-54, FR-55 (Student reads it, disclosure), FR-61 (Student's switched-off state), FR-80 (computed explanation shown), NFR-6, NFR-9, AD-6, AD-9, AD-23, UX-DR66 (not ready, ready, switched off, «Teller ikke. Ingen karakter.»)

### Story 12.3: Read written feedback that quotes my answer and matches my games

As a Student,
I want feedback on each long answer that quotes what I wrote and says plainly what is missing,
So that I can trust it refers to my own text and my own games.

**Acceptance Criteria:**

**Given** the `assess` call for an item
**When** the output schema is extended in a new prompt version
**Then** besides the overall score it holds feedback built from quotes, references to Scoring guide criterion codes that are missing, fact ids and approved sentence-template ids; code renders every number, Week and cause into the text, and the stored text travels as `{text, ai_generated, llm_call_id}` (FR-54, AD-7)
**And** the new prompt version is referenced by a new model config row made with the command of Story 2.2, since a config is immutable once referenced; a Class session pinned to the earlier config keeps the score-only output of Story 12.2 (AD-6)

**Given** the feedback cites the Student's answer
**When** the output is validated
**Then** each quote is a character span over the scrubbed text the LLM saw; the validator rejects a span outside that text, maps it through the gateway's offset map, and the feedback stores the span over the Student's original text; the view renders the quote from that original text and the LLM never retypes it (FR-54, AD-6, AD-7)
**And** a test with a Roster name inside the quoted passage proves that the Student sees their original words while the LLM saw the scrubbed ones (C-1)

**Given** feedback on an Adapted item or any feedback that states a fact about the Student's games
**When** it is validated
**Then** Epic 9's AI-text validator, reused from the shared code, loads the item's stored `fact_set_id` and rejects a fact id outside that set or a number outside the rendered facts; the fact set is never rebuilt (FR-54, NFR-9, AD-7)

**Given** the feedback for an item is rejected
**When** the job handles it
**Then** it regenerates that item's feedback exactly once with a new `ai.run` call; if the second output is rejected too, the feedback text is left out, the item's overall score is kept, and a note is stored for the Student (FR-54)
**And** both attempts have their own `llm_call` rows, written by the gateway

**Given** the Student opens a ready assessment
**When** an item has feedback
**Then** the feedback is shown under the item's score with the prefix «KI-generert, kan ta feil:», each quote set apart as a quotation of the Student's answer; where feedback was left out a note in text says so in its place (FR-34, FR-54, UX-DR66, UX-DR69)

**Given** the pinned Scoring guide version is not `checked` for the Class session's model config
**When** the Student or staff read the feedback
**Then** the view shows «Ikke kontrollert med en Kontrolltest.», read only from `content.service.is_checked` (FR-81, AD-27)

**Given** this story is built
**When** CI runs
**Then** pytest covers, on the mock provider: a valid output, a span out of range, a foreign fact id, one regeneration that succeeds and one that is dropped; Playwright covers feedback, dropped-feedback note and the unchecked notice at 360 and 1440 px (AD-7, AD-17)

**Covers:** FR-54, FR-34, FR-81 (unchecked notice in the feedback), NFR-9, AD-6, AD-7, AD-27, UX-DR66 (ready with dropped-feedback notes), UX-DR69 (prefix on AI text)

### Story 12.4: Be told when the AI assessment is ready

As a Student,
I want a notice when my AI assessment is ready,
So that I do not have to keep checking.

**Acceptance Criteria:**

**Given** the `assess` job has finished every item of an attempt (scored, or feedback dropped with a note)
**When** it marks the assessment ready
**Then** in the same transaction it calls `progress.record_step(user, class_session, assessment_ready, at)` and `platform/notify.enqueue(user_id, kind="assessment_ready", dedupe_key=<attempt id>, ref, not_before)`; both are idempotent, and a repeat run sends no second notice (FR-55, AD-9, AD-16)

**Given** the notice kind
**When** this story is built
**Then** `assessment_ready` is registered as a `digest` kind in the digest delivery of Story 3.5, with its Jinja2 template in `api/app/platform/email/templates/`: at most one mail per User per day and none between 22:00 and 07:00 Europe/Oslo; `assessment` does not import `messaging` (AD-9, AD-19)
**And** the mail says that the assessment is AI-generated, counts toward nothing and is not a grade, and holds no score, no letter and no feedback text (FR-55, C-2)

**Given** the notice is enqueued
**When** the Student has the app open
**Then** Hjem shows that the KI-vurdering is ready with a Lenke to it, through the `user:<id>` event, without a reload (AD-8)

**Given** a Student with an extended Test deadline
**When** the Class session's original Test deadline passes
**Then** the other Students' assessments are produced without waiting, and this Student's assessment is produced after their own `effective_deadline` with the Scoring guide pinned at the original deadline (FR-18, AD-9)

**Given** the 24-hour target
**When** an assessment is still not ready 24 hours after its attempt's `effective_deadline`
**Then** the sweep of Story 3.5 gets a due action that writes a structured `assessment_overdue` log event with ids only, once per assessment, so the delay is visible to the Admin, and re-defers the idempotent `assess` job only when the assessment has no live job and has not reached the maximum number of runs of Story 12.2 (FR-54, AD-9, NFR-8)
**And** when an assessment reaches the final state `failed`, each Admin gets one `assessment_failed` notice per Class session through `platform/notify.enqueue`, one row per Admin with a dedupe key of the Class session id and that Admin's user id, registered as a `digest` kind in the delivery of Story 3.5; a second failed assessment in the same Class session sends no second notice to anyone
**And** a test on the mock provider runs 400 submitted attempts through `llm-batch` and asserts that all become ready; the real duration is checked in the rehearsal against the provider's rate limit [ASSUMPTION: 24 hours stays a target until measured]

**Given** the cost limit is reached, or the Admin decides to leave the AI assessment out for a Class session (the Admin screen for this comes in Epic 15)
**When** `assessment.service.stop_for_session(class_session, actor)` runs
**Then** it sets a stop mark with time and actor on the Class session's assessment setting, owned by `modules/assessment`, and records the action through `platform/audit`; from then on the `assess` job and the sweep action skip that Class session, a running job ends without a further `ai.run` call, and an assessment that is not ready shows the switched-off state of Story 12.2 to the Student and to staff, while an assessment that was already ready stays readable [ASSUMPTION: founder confirms that ready assessments stay readable after a stop] (FR-61, FR-69, AD-9)
**And** what restarts assessment after the cost limit is raised is one command, `assessment.service.resume_for_session(class_session, actor)`, audited in the same way: it clears the stop mark, resets the run count of every `incomplete` and `failed` assessment of the Class session and defers `assess` for each of them and for every closed attempt that has no assessment yet; an api test stops, raises the limit, resumes and finds every assessment ready

**Covers:** FR-55 (email when ready), FR-54 (24-hour target), FR-61 (stopping the assessment for a Class session), FR-18 (extended Student), NFR-8, AD-8, AD-9, AD-16, AD-19

### Story 12.5: Flag feedback, and read assessments as staff

As a Student,
I want to mark a piece of feedback as wrong with one click, and as a Lecturer I want to read my Students' assessments and see those flags,
So that mistakes by the AI are seen by a person.

**Acceptance Criteria:**

**Given** a Student reads a piece of feedback
**When** they press «Marker som feil» under it
**Then** the flag is stored at once with no dialog, the control shows «Markert. Faglærer ser det.» with the text button «Angre», and it is a toggle with `aria-pressed` and no icon (FR-55, UX-DR39, UX-DR78)

**Given** a flagged piece of feedback
**When** the Student presses «Angre»
**Then** the flag is removed and the control returns to «Marker som feil»; a failed request shows the inline «Det ble ikke lagret. Prøv igjen.» with the button still active (UX-DR39, UX-DR59)

**Given** a Lecturer or Assistant lecturer of the Class
**When** they open the «KI-vurdering» block on that Student's Studentside (the minimal page from Epic 8, Story 8.9; the block is added in this story)
**Then** they see the same scores, feedback, dropped-feedback notes and unchecked notice as the Student, the line «KI-generert, kan ta feil. Teller ikke. Ingen karakter.», and which pieces the Student flagged (FR-55, UX-DR66)
**And** the Studentside page itself opens for an Assistant lecturer of the Class, by a `platform/authz` policy that this story extends where Story 8.9 opened the page for Lecturers only; the «Tilrettelegging» block of Story 8.9 stays hidden from Assistant lecturers
**And** a short list on the Klasseøkt «KI-vurdering» block shows per Student whether the assessment is ready and how many flags it has, each row a Lenke to that Student's Studentside; `assessment.service` exposes the same read for Epic 13

**Given** the staff view
**When** it is served
**Then** it never holds an Indicative letter that a Student turned on only for themselves (FR-56, AD-12)

**Given** a User outside the Class, or the Admin without Class membership
**When** they request an assessment or the list
**Then** the `platform/authz` policy denies it without revealing whether it exists; a Student reaches only their own (FR-5, AD-12, UX-DR59)

**Given** the screens are built
**When** CI runs
**Then** Playwright covers flag, undo and the staff view at 320, 360 and 1440 px with an axe check, and the flag control is a 44 px tap target on phone (NFR-6, UX-DR76)

**Covers:** FR-55 (flag, staff reading, disclosure on every view), FR-5, NFR-6, AD-12, UX-DR39, UX-DR66 («Teller ikke. Ingen karakter.» on the staff view)

### Story 12.6: Show the Indicative letter where it is allowed

As a Student,
I want to turn on an Indicative letter for my own AI assessment where my Lecturer allows it,
So that I can read the total as a letter, knowing it is not a grade.

**Acceptance Criteria:**

**Given** a Lecturer is in Klasseøkt → «KI-vurdering»
**When** they set the Indicative letter
**Then** Valgknapper (reused from Epic 5) offer three settings: shown to everyone in the Class session, off with each Student free to turn it on for themselves (default), and unavailable; the choice applies on «Lagre Klasseøkt» and states its scope in help text (FR-56, UX-DR12)
**And** with `FEATURE_RERUN` on and Story 5.18 built, this story adds the letter setting and the thresholds to `sessions.service.copy_from` of Story 5.18; otherwise it adds nothing there (FR-66, AD-17)

**Given** an Institution whose data protection officer requires that no letter is shown
**When** the Admin opens the Institution list of Story 3.11 in the Admin-område and turns on a Bryter for that Institution
**Then** the value is stored in a column this story adds to `institutions`, written and read only through `identity.service`, and the change is recorded through `platform/audit` (FR-56, FR-3)
**And** in every Class session of that Institution only «unavailable» can be chosen, the block says why, and no letter is derived or shown even where a Lecturer or a Student had turned it on before

**Given** the thresholds
**When** the Lecturer edits them
**Then** each letter A to F has a lower bound on the total score, the bounds must fall in order, and the defaults are configuration with placeholder values to be set after the first Control test; they are read-only once the first Test attempt in the Class session has been opened (FR-56) [ASSUMPTION: "before the Individual test opens" means before the first attempt is opened]

**Given** a total score and thresholds
**When** a letter is derived
**Then** it comes only from the pure function `analysis.indicative_letter(total, thresholds)`, added to `api/app/analysis/`, with pytest covering every bound; no letter is derived for an `incomplete` assessment (FR-56, AD-1)

**Given** the setting is off with Student choice
**When** a Student opens their ready KI-vurdering
**Then** the Veiledende bokstav control lets them turn it on for their own view; the letter then shows beside the total, labelled as an AI-generated indication that is not a grade; they can turn it off again (FR-56, UX-DR66)
**And** the Student's choice is stored on their own assessment and is never returned by any staff or Admin endpoint, proved by an api test (FR-56, AD-12)

**Given** the setting is on for the whole Class session
**When** the Student or staff open an assessment
**Then** the letter shows with the same label on both views; when the setting is unavailable no control and no letter are shown anywhere (FR-56)

**Given** the Completion status and any export that exists at this point
**When** the letter is on
**Then** `assessment.service` gives no letter to a read made for an export or a ZIP, gives a letter that a Student turned on only for themselves to no one but that Student, and gives the letter to a report read only when the Student themself asks for the report; a test asserts each, and that the letter is no input to Completion is asserted where Completion is built, in Epic 13 (FR-56, C-2)

**Given** the screens are built
**When** CI runs
**Then** Playwright covers the three settings and the Student control at 320, 360 and 1440 px with an axe check; strings that EXPERIENCE.md does not give are added to `web/src/copy/nb.ts` and listed for founder review (NFR-6)

**Covers:** FR-56, FR-66, NFR-6, AD-1, AD-12, AD-17, UX-DR66 (Veiledende bokstav control)

### Story 12.7: Set up a Control test in the operator's own Institution

As an Admin,
I want to set up a Control test as its own Class session in the operator's Institution,
So that the AI assessment can be checked on real answers that never enter a course's results.

**Acceptance Criteria:**

**Given** the Institution list of Story 3.11 in the Admin-område
**When** the Admin marks one Institution as the operator's own
**Then** the mark is stored in a column this story adds to `institutions`, written and read only through `identity.service`; at most one Institution carries it, the change is recorded through `platform/audit`, and `identity.service` exposes which Institution is operator-owned (FR-82, AD-27, AD-15)

**Given** the Admin opens Admin-område → «Kontrolltest»
**When** they create a Control test
**Then** one transaction creates, through `classes.service` and `sessions.service`, a Class in the operator-owned Institution with the Admin as its owner, and in it a Class session with `kind=control_test`; the `kind` column, with `course` as default for all existing rows, is added to `class_sessions` through `modules/sessions` in this story (FR-82, AD-27)
**And** only the Admin can create this kind, by a `platform/authz` policy; with no operator-owned Institution marked the creation is refused with a stable error code and the screen says what to do first (AD-12)

**Given** the Control test's Class and Class session exist
**When** the Admin sets dates, uploads the Roster, sends Invitations and allocates
**Then** they do so as the owner of that Class on the ordinary screens of Epics 4 and 5, and no second set of screens is built; where a policy of those epics asks for the Lecturer account role, this story extends that policy to the owner of a `control_test` Class (AD-12, AD-27)

**Given** a Control test is created
**When** its settings are stored
**Then** creation pins the Scoring guide version under test (the default, or a Lecturer's edited version chosen from a list) and the model config under test; neither can change afterwards, so «Sensorveiledning» of Story 11.2 is read-only for this Class session, and `sessions.lock_test` of Story 11.11 pins that same version (AD-27, AD-23, AD-6)
**And** the draft block of Story 11.1 applies unchanged: in production a Control test cannot be locked on a `draft` question set either

**Given** any Lecturer, Assistant lecturer or Student of an ordinary Class
**When** they open any list, overview, funnel or statistic that exists at this point
**Then** no Control test Class, Class session or Game appears in it, proved by api tests, and `sessions.service` exposes `kind` to other modules; later reports and exports leave Control tests out through `reports.scope` in Epic 13 (FR-82, AD-13)

**Given** the screen is built
**When** CI runs
**Then** it shows «Teller aldri med i en Klasseøkt.» and the pinned Scoring guide version and model config, Playwright covers the operator mark and the setup at 320, 360 and 1440 px with an axe check, and every Admin action here is recorded through `platform/audit` (NFR-6, NFR-7, UX-DR57)

**Covers:** FR-82, NFR-6, NFR-7, AD-6, AD-12, AD-13, AD-15, AD-23, AD-27, UX-DR57 (Kontrolltest: setup)

### Story 12.8: Invite test students who consent before they take part

As an Admin,
I want the people in a Control test to be marked as test students and to consent before they are given a Seat,
So that their data is collected on a clear basis and never counts in a Class session.

**Acceptance Criteria:**

**Given** a Control test from Story 12.7
**When** the Admin adds test students by email on its Roster and they are invited and register through the flow of Story 4.4 and Story 4.5
**Then** each such User carries `is_test_student`, a column this story adds to the `identity` tables and sets through `identity.service`, and is listed with the label «Teststudent» (FR-82, AD-13, UX-DR57)
**And** the Roster of a Control test accepts only such Users: an address that belongs to an existing User without the mark is refused with a stable error code and a reason in words

**Given** a test student logs in for the first time
**When** they reach Hjem
**Then** they are told what the Control test is for and that the operator of ØL-spillet is the data controller, and they give consent with one button; a consent record with the User, the time and the text version is stored in a table this story creates, and declining leaves them unallocated (FR-82, AD-27)

**Given** the allocation of the Control test's Class session
**When** it is previewed or confirmed with the allocation of Story 5.8 and Story 5.9
**Then** it refuses a User without a consent record, with a stable error code that names how many lack consent; this story adds the check for Class sessions of kind `control_test` only (AD-27)

**Given** a Control test with allocated test students
**When** they play the Class game, do the Debrief, the Debrief quiz, the Replay and the Individual test
**Then** every step runs unchanged with the ordinary Game purposes `class` and `replay`, and the AI assessment runs after the Control test's own Test deadline on that Class session's own budget row (FR-82, AD-27, AD-6)

**Given** any Lecturer, Assistant lecturer or Student of an ordinary Class
**When** they open any list, overview, funnel or statistic that exists at this point
**Then** no test student appears in it, proved by api tests, and `identity.service` exposes `is_test_student` to other modules; later reports, exports and Completion leave test students out through `reports.scope` in Epic 13 (FR-82, AD-13)

**Given** the screens are built
**When** CI runs
**Then** Playwright covers the test student list and the consent screen, accepted and declined, at 320, 360 and 1440 px with an axe check; the consent text is draft copy in `web/src/copy/nb.ts`, listed for founder review (NFR-6, UX-DR57)

**Covers:** FR-82 (marked test students, consent), NFR-6, AD-6, AD-13, AD-27, UX-DR57 (Kontrolltest: marked test students)

### Story 12.9: Score Control test answers blind

As an Admin,
I want named human scorers to score each long-answer and Adapted item with the Scoring guide, without seeing the AI's score,
So that the comparison is not coloured by the AI.

**Acceptance Criteria:**

**Given** a Control test
**When** the Admin names scorers among existing Users
**Then** only the Admin and those scorers can read that Control test's answers, by a `platform/authz` policy, and each naming and each read by the Admin is recorded through `platform/audit` (FR-82, AD-12, AD-27)

**Given** a scorer opens their scoring list after the Control test's Test deadline
**When** the list loads
**Then** it holds one entry per long-answer and Adapted item per test student, shown with a neutral number and never a name or email, and marks each as scored or not scored in text (FR-82, NFR-6)
**And** a scorer reaches the list through a Lenke on their own home screen (Lærerhjem, Hjem or Admin-område), shown only while they are a named scorer of a Control test and served under the scorer policy; the scorer needs no Admin role and sees nothing else of the Admin-område

**Given** the scorer opens an item
**When** it loads
**Then** they see the question, the answer's original text, the facts of an Adapted item, and the pinned Scoring guide entry with its criteria and five-step scale; the API response holds no AI score and no AI feedback for that item (FR-82, AD-27)

**Given** the scorer picks a step on the scale and presses the primary button labelled with its effect
**When** the score is submitted
**Then** one row is written to `human_scores(answer_id, scorer_id, score, submitted_at)`, a table created in this story and owned by `modules/assessment`; a second submit for the same answer and scorer is rejected with a stable error code, and no update path exists (FR-82, AD-27)
**And** the consequence, that the score cannot be changed afterwards, is stated above the button, and no dialog follows (UX-DR9, UX-DR78)

**Given** the scorer has submitted their score for an item
**When** they open that item again
**Then** the AI's score for that item becomes visible to them, and still not for items they have not scored; an api test proves both directions (AD-27)

**Given** the scoring screens are built
**When** CI runs
**Then** Playwright covers list, item, submit and rejected resubmit at 320, 360 and 1440 px with an axe check, and the scale is a Valgknapper control operable by keyboard (NFR-6, UX-DR12)

**Covers:** FR-82 (blind human scoring), NFR-6, NFR-7, AD-12, AD-27, UX-DR57 (Kontrolltest)

### Story 12.10: Compare human and AI scores and mark the Scoring guide as checked

As an Admin,
I want to see human and AI scores side by side with agreement measures,
So that I know whether the AI assessment can be relied on with this Scoring guide and model.

**Acceptance Criteria:**

**Given** human scores and AI item scores of a Control test
**When** the measures are computed
**Then** they come only from the pure function `analysis.agreement(human_scores, ai_scores)`, added to `api/app/analysis/`: exact agreement, agreement within one step, systematic offset, compression of the scale, and agreement by answer length; pytest covers it with golden cases including a constant offset and a compressed scale (FR-82, AD-27, AD-1)

**Given** the Admin opens the results in «Kontrolltest»
**When** the page loads
**Then** it shows each item's human score and AI score side by side in an HTML table, and the five measures as numbers with a label each, formatted by the shared number formatter; any chart comes from `web/src/components/charts` with «Vis som tabell» (FR-82, NFR-6, UX-DR57)
**And** the page shows «Teller aldri med i en Klasseøkt.» and the Scoring guide version and model config the Control test is pinned to

**Given** some human scores are still missing
**When** the results are shown
**Then** the page says how many are missing, the measures are marked as preliminary in text, and the Scoring guide is not marked as checked (AD-27)

**Given** every named scorer has submitted a score for every long-answer and Adapted item
**When** the last score is submitted
**Then** `assessment` calls `content.service.mark_checked(scoring_guide_version_id, model_config_id)` in the same transaction; this is the only caller, and `content.service.is_checked` from Story 11.2 then returns true for exactly that pair (FR-81, AD-27)
**And** the `checked` record (Scoring guide version, model config, Control test and time) is a table this story creates in `modules/content`, together with `mark_checked`; `is_checked`, which answered false until now, reads it from this story on
**And** a guide checked with one model config stays unchecked for another, and a later edit of the guide is a new version and so unchecked; tests prove both

**Given** a Class session that pins the checked Scoring guide version and the same model config
**When** the Lecturer opens «Sensorveiledning» or anyone reads feedback
**Then** «Ikke kontrollert med en Kontrolltest.» is no longer shown (FR-81)

**Given** a Lecturer asks for their edited guide to be checked
**When** the Admin creates a Control test pinned to that version (Story 12.7)
**Then** the same flow applies, and the Lecturer cannot read the Control test's answers or scores (FR-82, AD-12)

**Given** the results page is built
**When** CI runs
**Then** Playwright covers preliminary and complete results at 320, 360 and 1440 px with an axe check, and an api test confirms that no endpoint outside the Control test policies returns these scores (NFR-6, AD-12)

**Covers:** FR-82 (side-by-side comparison, agreement measures, default or edited guide), FR-81 (checked status), NFR-6, AD-1, AD-12, AD-27, UX-DR57 (Kontrolltest: side-by-side comparison)

## Epic 13: Completion and Student reports

A Lecturer can see who met the requirement of an Obligatory class session, correct it with a logged reason, give a make-up game and message those who fell short. Students and staff can download the Student report as a tagged PDF, and the Lecturer can download all reports as a ZIP and the Completion export. The epic owns `api/app/modules/reports/` and `web/src/modules/reports/`, extends `modules/progress`, and adds the shared pieces `analysis.completion`, `reports.scope` and `platform/storage`.

### Story 13.1: Completion is computed in one place and shown on the Student's Hjem

As a Student,
I want to see on Hjem which steps I have done and whether I have met the requirement,
So that I know where I stand without asking the Lecturer.

**Acceptance Criteria:**

**Given** the step events from `modules/progress` and the Decision log
**When** `analysis.completion(steps, decision_log_summary, corrections, settings) -> CompletionStatus` is called
**Then** it returns, per step (Class game, Debrief, Debrief quiz, Replay, submitted Individual test), done or not done with the date, the share of Weeks ordered, and whether the requirement is met (FR-17, AD-16)
**And** the function is pure, lives in `api/app/analysis/`, does no I/O, reads no clock, and has no input from the AI assessment or the Indicative letter (AD-1, AD-16, C-2).

**Given** a Student's Class game
**When** the share of Weeks ordered is computed
**Then** it counts `seat_week` rows with `decided_by = student` over the Weeks after the Guided Weeks, and Takeover Weeks and playout Weeks count as not ordered (FR-17, AD-15)
**And** the Class game step is done only when the share is at least the Class session's required share or the Student's adjusted share; the assembler reads the required share through `sessions.service.required_share(class_session)`, built in Story 5.7 (default 80%, a placeholder), and the adjusted share only through `sessions.service.get_adjustment(class_session, user)` (Story 8.9), and passes both in; this story creates neither
**And** the result carries the share of Weeks that were played in the playout at the Play deadline, so a shortfall caused by the playout or the group's pace can be shown.

**Given** an Individual test that was auto-submitted at the Test deadline, and a saved Explanation
**When** Completion is computed
**Then** the test step counts only if the attempt has content in each required part, and the Debrief step counts only if the Explanation has the minimum length (FR-17)
**And** both minimums are configuration with stated placeholders (PRD §13 assumption "these minimums"), not final numbers
**And** time spent and constant Orders are never inputs.

**Given** any reader of a Student's Completion status (Student Hjem in this story, and later the Studentside, the Completion export and the Student report)
**When** it needs the status
**Then** it calls one assembler, `reports.service.completion_status(user_id, class_session_id)`, which gathers the inputs through the `progress`, `sessions`, `games`, `debrief` and `tests` services and calls `analysis.completion`
**And** the status carries, per step, both whether a step event is recorded (with its date) and whether the step counts as done after the share, the minimums and any correction.

**Given** the funnel of Story 7.6, `progress.service.funnel(class_session_id, student_ids)`, which takes the Student ids from its caller
**When** this story is done
**Then** the Oversikt gets the funnel through `reports.service.funnel(class_session_id)`, which passes the Students in `reports.scope.reporting_students()`; the funnel itself stays in `progress`, which still imports no feature module (AD-16, AD-25)
**And** the funnel counts step events, not the requirement: for the stages Class game finished, Debrief done, Debrief quiz passed, Replay done and Individual test submitted, each count equals the number of those Students whose Completion status has a recorded step event for `class_game`, `debrief`, `quiz_passed`, `replay` and `test_submitted`; a test asserts the five equalities for one Class session
**And** the number of Students who have met the requirement is a separate figure from the assembler and is never read from the funnel.

**Given** reports, statistics, exports and the funnel must leave out test data
**When** this story adds `reports.scope.reporting_games()` and `reporting_students()` to `modules/reports`
**Then** they exclude `lecturer_test` and `simulation` Games, `control_test` Class sessions and Users with `is_test_student` (AD-13, AD-27)
**And** a Replay is a reporting Game: `reporting_games()` returns `purpose=replay` Games with their `end_reason`, and a test asserts it
**And** the Completion assembler, the funnel caller above and the staff lists of AI assessments from Story 12.5 now read through them, with a test per excluded kind (a lecturer test Game, a simulation Game, a Control test Class session, a test Student); the lecturer test Game is a fixture row with `purpose=lecturer_test`, so the test does not need the cut-list Story 6.20.

**Given** a Student in an Obligatory class session
**When** the Student opens Hjem
**Then** Stegene (reused from Epic 6) shows each step's status from the assembler, and one line states whether the requirement is met, in copy from `web/src/copy/nb.ts` (FR-17, UX-DR29)
**And** where the Student's share is adjusted, the existing line «For deg er kravet 60 % av ukene.» shows the Student's own figure
**And** no line reveals the number of Weeks while the Class game is running (FR-14).

**Given** the pure function
**When** CI runs
**Then** pytest covers `analysis.completion` with table-driven cases aiming at full branch coverage: share exactly at the limit, Takeover Weeks, playout Weeks, an adjusted share, a correction, an auto-submitted test without content, a short Explanation, and a Class session that is not obligatory
**And** a test asserts that neither a recorded `assessment_ready` step nor an Indicative letter changes the result (AD-16, C-2).

**Covers:** FR-17, AD-1, AD-13, AD-15, AD-16, AD-25, AD-27, UX-DR29

### Story 13.2: Studentside with the «Fullføring» block

As a Lecturer or Assistant lecturer,
I want one page per Student with everything the Student has done and the Completion status per step,
So that I can answer a Student's question or check a shortfall without opening five screens.

**Acceptance Criteria:**

**Given** a Lecturer or Assistant lecturer attached to the Class
**When** they open a Student from the Oversikt, Spillinnsikt or the Roster
**Then** the Studentside, extending the minimal page that Story 8.9 created, shows the Student's game, read through `games.service.student_game` from Story 6.1 (with a link to Spillinnsikt), Explanation, Debrief summary, Debrief quiz attempts, Replay, Individual test, AI assessment with the Student's flags, and a slot for the link to the Student report (FR-63, UX-DR55)
**And** the slot is empty in this story; Story 13.12 adds the link
**And** each part is read through the owning module's `service.py` (`games`, `debrief`, `replay`, `tests`, `assessment`), with no direct table access from `reports`
**And** the page of blocks in `web/src/modules/reports/` already holds «Tilrettelegging» (Story 8.9), the test extension form (Story 11.13) and the «KI-vurdering» block (Story 12.5); these are kept unchanged and not rebuilt, and the AI assessment part of this page is that existing block.

**Given** the «Fullføring» block
**When** the page loads
**Then** it shows one row per step (Klassespill, Debrief, Debrief-quiz, Replay, Individuell test) with the status in text, «gjort» or «ikke gjort», never by a dot alone (UX-DR54)
**And** the Klassespill row adds the share line in the form «Bestilte i 70 % av ukene. Kravet er 80 %.» and, where it applies, «20 % av ukene ble spilt i utspillingen ved Spillfristen.» (FR-17)
**And** the requirement line shows only when the Class session is obligatory
**And** all values come from `reports.service.completion_status` (Story 13.1).

**Given** FR-17 lets the Lecturer see participation signals that never change the status
**When** the Fullføring block is shown
**Then** it lists time spent (the sum, over the Student's own Orders, of the time from `opened_at` to `ordered_at` in `seat_week`) and whether the Student's Orders were constant (every own Order after the Guided Weeks has the same quantity), both computed in the api and labelled as information only
**And** a test shows that changing these values does not change the Completion status.

**Given** the AI assessment is switched off, not ready, or the Student turned on the Indicative letter only for themselves
**When** staff open the Studentside
**Then** the AI assessment part shows the matching state from Epic 12, and a self-enabled Indicative letter is never served to staff (FR-56, AD-12).

**Given** a User who is not staff in the Student's Class, or an Admin without Class membership
**When** they request the Studentside or its API
**Then** the policy in `platform/authz` denies it with the permission-denied state that does not reveal whether the Student exists (FR-5, AD-12, UX-DR59)
**And** every repository query joins through a scope helper.

**Given** a step is recorded or corrected while the page is open
**When** the change event arrives on the SSE stream
**Then** the page refetches over REST through the topic-to-query bridge from Epic 6 (AD-8).

**Given** the page at 320 px, 1440 px and 200% text
**When** the Playwright and axe checks run
**Then** it reflows without horizontal page scroll, every chart has «Vis som tabell», and axe reports no violations (NFR-6, UX-DR55).

**Covers:** FR-63, FR-17, FR-5, NFR-6, AD-8, AD-12, AD-16, UX-DR54, UX-DR55

### Story 13.3: Correct a Student's Completion status with a reason

As a Lecturer,
I want to correct a step's status for one Student and give the reason,
So that a Student who kept up but fell short through the playout or the group's pace is treated fairly.

**Acceptance Criteria:**

**Given** the Fullføring block on the Studentside
**When** the Lecturer presses «Rett Klassespill» (or the same action on another step)
**Then** a form opens in place with Valgknapper «Gjort» / «Ikke gjort», the Tekstfelt «Begrunnelse», the line «Rettingen logges med navnet ditt, tidspunktet og begrunnelsen.», the primary button «Lagre retting» and «Avbryt» (UX-DR54)
**And** focus moves to the first field, and «Avbryt» returns focus to the button that opened the form
**And** only one in-place form is open on the Studentside at a time; opening another closes the first and keeps nothing.

**Given** the form with an empty «Begrunnelse»
**When** the Lecturer presses «Lagre retting»
**Then** nothing is saved and the field shows «Skriv en begrunnelse.» in the invalid state (UX-DR11)
**And** the API rejects an empty reason with a stable error code.

**Given** a valid correction
**When** it is saved
**Then** a new row is written to a `completion_corrections` table owned by `modules/progress` (Student, Class session, step, new status, reason, actor, time), and no step event or `seat_week` row is changed (AD-15)
**And** `platform/audit.record(actor, action, target, change)` is called in the same transaction (FR-3)
**And** `analysis.completion` applies the latest correction per step; a correction changes the Completion status only: it records no step event, opens no gate that is read through `progress.has_step`, and leaves the funnel stages, which count step events, as they are (AD-16)
**And** the save emits `session:<id>` and, for the Student, `user:<id>` through `platform/events.emit`, with its entry in the registry and the registry test, so the open Studentside and the Student's Hjem refetch (AD-8).

**Given** a saved correction
**When** the Studentside shows the step
**Then** the result line replaces the form and reads in the form «Gjort, rettet av Bård 12. des.» with the reason under it
**And** a later correction of the same step is a new row, and the page shows the latest while the audit log keeps all.

**Given** the corrected Student
**When** the Student opens Hjem
**Then** Stegene shows the new status marked «rettet av faglærer» and never the reason (UX-DR54)
**And** the reason is not served by any Student-facing endpoint.

**Given** an Assistant lecturer or a Lecturer of another Class
**When** they call the correction endpoint
**Then** the `platform/authz` policy denies it and nothing is written (AD-12).

**Covers:** FR-17, FR-3, AD-8, AD-12, AD-15, AD-16, UX-DR54

### Story 13.4: Give a Student an Oppfølgingsspill

As a Lecturer,
I want to give a Student who fell short, was ill or registered late a make-up game,
So that the Student can still complete the Class game step before the Test deadline.

**Acceptance Criteria:**

**Given** the Klassespill row of the Fullføring block, after the Class session is locked and before the Test deadline
**When** the Lecturer presses «Gi oppfølgingsspill»
**Then** a form opens in place with the consequence in the form «Jonas får et eget Klassespill mot tre KI-spillere, åpent til Testfristen fr. 18. des. Jonas får beskjed på Hjem og på e-post.», the primary button «Gi oppfølgingsspill» and «Avbryt» (UX-DR54)
**And** before `sessions.lock` has run the action is not offered and the API refuses it with a stable error code, because no frozen snapshot exists yet
**And** after the Test deadline the action is not offered either, and the API rejects it with a stable error code.

**Given** the Lecturer confirms
**When** the make-up is created
**Then** a Game with `purpose=makeup` is created through `games.commands.create`, which snapshots the Class session's frozen Game settings, demand series, seed, `rules_version` and `SessionRuntime` at creation, read unchanged through `sessions.service.build_snapshot(class_session)` of Story 5.11, as Story 10.3 does for a Replay; before `start`, `games.commands.assign_seat` gives the Student their own Role, or a Role drawn at random if they never had a Seat, and gives each of the three other Seats an AI player of the kind the Class session's AI mode gives, so `start` finds no free Seat to fill with a Rule-based player (FR-17, FR-30, AD-2, AD-4)
**And** this story adds the `makeup` row to `games.policy`: the snapshot taken at creation (the column of Story 5.9; without it `start` would answer `409 game_not_ready`), no inactivity Takeover, no Pause, no Play deadline playout, not listed on the Lecturer overview wall, Guided Weeks as in the Game settings, and, in the two columns Story 6.18 added, the pre-play gate on and "records the Class game step" off (AD-13)
**And** the action is recorded through `platform/audit`, and a second press for a Student who already has an open make-up returns the existing one.

**Given** a make-up was given
**When** the Studentside and the Student's Hjem are shown
**Then** the Studentside reads in the form «Oppfølgingsspill gitt 12. des. Åpent til fr. 18. des.»
**And** the Student's Hjem shows a Spillkort titled «Oppfølgingsspill», reusing the title variant from Story 6.17, and the Student is told through `platform/notify`, with the kind registered in the digest delivery of Story 3.5 (UX-DR28, AD-9).

**Given** a Student plays the make-up
**When** they order and finish
**Then** the play screen from Epic 6 is reused with no second copy, waiting is only for AI players, and «Spillet er ferdig» shows the result as for any Game (FR-17)
**And** the Decision log, reference Orders and the finished-game check run as for any Game (AD-15, FR-29)
**And** which game the Debrief and the later steps use is not changed in this story; Story 13.5 adds that.

**Given** a finished or partly played make-up
**When** `analysis.completion` computes the Class game step
**Then** the assembler passes in the make-up's Decision log summary beside the Class game's, the step is done when the share of Weeks ordered in either game meets the Student's share, and the share lines name which game the figure comes from
**And** `reports.scope.reporting_games()` takes a purpose filter, so per-Class-game measures can read `purpose=class` only and a make-up never changes a group's result.

**Given** a make-up that is not finished at the Student's effective Test deadline
**When** the sweep of Story 3.5 runs the due action this story adds
**Then** it calls `games.commands.close(game, reason=test_deadline)` from Story 10.6, which closes the make-up without a playout; the Weeks not played count as not ordered, and the sweep action is idempotent (AD-2, AD-9).

**Given** a Student who registered after allocation and has no Seat (FR-20)
**When** the Lecturer opens that Student's Studentside
**Then** the Klassespill row reads «ikke gjort» and offers «Gi oppfølgingsspill» in the same way.

**Covers:** FR-17, FR-20, FR-29, FR-30, AD-2, AD-4, AD-9, AD-13, AD-15, UX-DR28, UX-DR54

### Story 13.5: Continue to the Debrief, the Replay and the test from a finished Oppfølgingsspill

As a Student,
I want my finished make-up game to be my game for the Debrief, the Replay and the Individual test,
So that I can complete the whole Class session even though I missed the Class game or fell short in it.

**Acceptance Criteria:**

**Given** the founder decision of 2026-11-12 on the make-up game
**When** `games.service.student_game(user, class_session)` from Story 6.1 is extended in this story
**Then** it returns the Student's make-up game once that game has finished by playing its last Week, and otherwise the Class game where the Student holds or held a Seat; a Student with neither gets none (FR-17, AD-13)
**And** a make-up that was closed at the Test deadline is not finished and never becomes the Student's game
**And** table-driven tests cover a Class game only, a Class game with an unfinished make-up, a Class game with a finished make-up, a finished make-up only, and an unfinished make-up only.

**Given** a Student finishes the make-up
**When** `games.commands.finish` commits
**Then** `progress.record_step(user, class_session, class_game, at)` is called for the Student, because this story turns on "records the Class game step" in the `makeup` row of `games.policy`; no command branches on the purpose itself (AD-13, AD-16)
**And** the call is idempotent, so a Student who already has the step from the Class game keeps one step event, and whether the step counts is still decided only by `analysis.completion`.

**Given** a Student whose game is a finished make-up and who has not opened a Debrief
**When** the Student presses «Gå til Debrief» on «Spillet er ferdig» or opens the Debrief step in Stegene
**Then** `debrief.commands.open` creates a Personal debrief for the make-up, whatever the Class session's Debrief mode, read from a new `games.policy` column "Debrief is always personal" that is on for `makeup` only (FR-17, AD-21, UX-DR54)
**And** the Debrief runs unchanged on the make-up's stored fact set from `games.facts.get_or_create`.

**Given** a Student who had already started a step on the Class game before the make-up finished (a Debrief session opened, a Replay started, or Adapted items generated)
**When** the make-up becomes the Student's game
**Then** that step keeps the game it was started on, nothing already recorded is redone or changed, and an Adapted item the Student has seen never changes; only steps started afterwards use the make-up
**And** each of these records already stores its Game or its `fact_set_id`, so no stored row is rewritten.

**Given** a Student whose game is a finished make-up and who goes on to the later steps
**When** the Replay is started and the Adapted items are generated
**Then** api tests prove that `replay.service.start` from Story 10.3 takes the Role from the make-up, and that the Adapted items of Story 11.7 are built from the make-up's fact set, both through `games.service.student_game` with no direct query on Class games
**And** the Studentside of Story 13.2 shows the make-up as the Student's game, marked «Oppfølgingsspill».

**Given** a Student who registered late and has no Class game
**When** they open Hjem before and after the make-up is finished
**Then** before, Stegene states that the Debrief opens when the Oppfølgingsspill is finished (draft copy in `nb.ts`); after, the Debrief step is open
**And** Playwright with axe covers the path from the last Order of the make-up to step 1 of the Debrief at 360 and 1440 px (NFR-6).

**Covers:** FR-17, FR-20, NFR-6, AD-13, AD-16, AD-21, UX-DR54

### Story 13.6: Message the Students who have not met the requirement

As a Lecturer,
I want to send one Message to everyone who has not met the requirement,
So that I can remind them in one action instead of one by one.

**Acceptance Criteria:**

**Given** an Obligatory class session with Students who have not met the requirement
**When** the Lecturer opens the Oversikt
**Then** under the Trakt a Lenke reads in the form «Send Melding til 12 som ikke har oppfylt kravet», with the count from `reports.service.completion_status` over `reporting_students()` (FR-17, UX-DR54)
**And** the Lenke is absent when the Class session is not obligatory or when every Student has met the requirement.

**Given** the Lenke
**When** the Lecturer follows it
**Then** the Meldingsskjema from Story 7.9 opens with those Students preset as the recipient, and no second form component is written (FR-40, UX-DR46)
**And** this story adds a recipient kind `requirement_not_met` to `messaging` `service.py`; its list is resolved on the server when the Message is sent, by `messaging` calling `reports.service`, so a Student who met the requirement in the meantime is left out
**And** the explicit-list kind of Story 7.9 is not used here, because its list would be fixed when the form opens (AD-9).

**Given** the Meldingsskjema opened with this recipient
**When** the Lecturer looks at who will get the Message
**Then** a table above the text field lists the Students who have not met the requirement: the name as a Lenke to the Studentside, the share of Weeks ordered against the required share, and the share of Weeks played in the playout at the Play deadline where there is one, so a shortfall caused by the playout or the group's pace can be told from one the Student caused (FR-17)
**And** the rows come from `reports.service.completion_status`, the table is an HTML `<table>` with `th` scopes, and its headings are draft copy in `web/src/copy/nb.ts` for review.

**Given** the Message is sent
**When** delivery runs
**Then** it appears in the product and by email as an `immediate` kind, and the sent-count result shows the number actually sent (FR-40, AD-9).

**Given** an Assistant lecturer
**When** they open the Oversikt
**Then** the Lenke and the table follow the same `platform/authz` policy as sending a Message to a Class session in Story 7.9 (AD-12).

**Covers:** FR-17, FR-40, AD-9, AD-12, AD-13, UX-DR46, UX-DR54

### Story 13.7: A Student downloads the Student report as a tagged PDF

As a Student,
I want to download a PDF report with my Completion status,
So that I can document the work for approval or in another application.

**Acceptance Criteria:**

**Given** a Student whose effective Test deadline (`sessions.service.effective_test_deadline` from Story 5.2) has passed and whose data is not deleted
**When** the Student presses the download action on the «Rapport» step that Stegene already lists
**Then** the api checks the `platform/authz` policy, records the request and defers a job on the `reports-single` queue with ids only (requester, Student, Class session, options); the api builds no report content itself (FR-57, AD-9, AD-12, AD-18)
**And** the PDF is ready within 30 seconds (placeholder target from the PRD), measured in a test on the mock storage
**And** while it is made the step shows a pending state, and the page updates without reload through the Student's `user:<id>` topic, which the finished job emits (AD-8).

**Given** the job runs in `worker-batch`
**When** it renders the report
**Then** it calls `reports.build_report_data(student, class_session, options)`, the only assembler of report content, stores the result as a report snapshot with a single-use render token that expires after 5 minutes, fetches `WEB_INTERNAL_URL/print/report/<snapshot_id>` with the token, converts the page with WeasyPrint in its `pdf/ua-1` variant, and stores the PDF through `platform/storage` in the private `reports` bucket under a path keyed by Class session and `user_id` (AD-14, AD-18)
**And** the snapshot row is deleted when the render ends, whether it succeeded or failed, so no copy of the name or the free text stays outside the bucket; a retried job builds a new snapshot and a new token (AD-14)
**And** `platform/storage` is added in this story for reuse: Supabase Storage in production, `./.local-storage/` as the mock when the keys are missing and `APP_ENV` is local, test or ci; the storage keys are already in the production startup guard of Story 3.14 (AD-17)
**And** the job is idempotent, and a second request while one is running does not start a second render.

**Given** the print route `web` `/print/report/<snapshot_id>`
**When** it is requested
**Then** it is server-rendered, needs no JavaScript, reads only that snapshot with the render token, and a used or expired token gives an error with no data (AD-18)
**And** a request for `/print/*` through the proxy is refused, checked by a test against Docker Compose (AD-11)
**And** all PDF copy lives in the print route and its templates, in Norwegian bokmål (AD-19, FR-72).

**Given** the report content of this story
**When** the PDF is opened
**Then** it is headed «ØL-spillet» and holds the Student's name, the Class and Class session, the dates, the time the report was generated, the Completion status per step and whether an obligatory requirement is met, all from `reports.service.completion_status` (FR-58, AD-16, UX-DR68)
**And** it states that it documents the Student's work and is not a grade
**And** the sections for the game, the Debrief, the Replay and the Individual test are added by Story 13.8 and Story 13.10 and are not in the report yet.

**Given** the report page
**When** it renders in the print route
**Then** fonts are self-hosted through `@fontsource/source-sans-3`, numbers use the shared Norwegian number formatter, and every table has header cells with scopes (AD-18, NFR-6, UX-DR68)
**And** CI runs veraPDF on a sample Student report and fails on a PDF/UA violation
**And** the sample comes from a test fixture that adds a locked Class session with step events to the seeded demo Class, because the seed of Story 4.1 and Story 4.5 has no Class session.

**Given** a finished PDF
**When** the Student downloads it
**Then** the api creates a signed URL with the lifetime `SIGNED_URL_TTL_SECONDS` (default 300) only after the policy allowed the request, and a Student can never get a URL for another Student's report (NFR-7, AD-12)
**And** the PDF is regenerated on request, so a later correction or step shows in the next download.

**Given** a Student before their effective Test deadline, or a render that fails
**When** the «Rapport» step is shown
**Then** before the deadline the step is locked and states what opens it (UX-DR29), and the API refuses the request with a stable error code
**And** a failed render shows an inline error with a retry action, and the failure is logged without names or free text.

**Covers:** FR-57, FR-58, FR-72, NFR-6, NFR-7, AD-8, AD-9, AD-11, AD-12, AD-14, AD-16, AD-17, AD-18, AD-19, UX-DR29, UX-DR68

### Story 13.8: The Student report shows the game with its charts

As a Student,
I want the report to show my game week by week with the whole chain in a chart,
So that it documents what I did and what happened around me.

**Acceptance Criteria:**

**Given** a Student with a game
**When** the report is built
**Then** it holds the game section: Role, Weeks played, final Total cost, the week-by-week table for the Student's own Seat, and a chart of Orders, inventory and backlog for all four Roles plus customer demand, with AI players and Takeover Weeks marked in text through the one mapping of AD-15 (FR-58, FR-34, AD-15)
**And** the game is the Student's game from `games.service.student_game`, and the chain data is read through `games` `service.py`, as Spillinnsikt of Story 7.7 reads it
**And** other Students appear by Role only, never by name.

**Given** the charts in the report
**When** they render in the print route
**Then** they come from `web/src/components/charts` with a fixed width, reusing the four-Role charts of Story 7.8 with no second chart implementation, each SVG carries a `<title>`, and a table follows every chart (AD-18, NFR-6, UX-DR68).

**Given** a Student whose game is a finished make-up (Story 13.5)
**When** the report is built
**Then** the game section shows the make-up, headed «Oppfølgingsspill», and a test builds the report for such a Student and for a Student with only a Class game (FR-17, AD-13).

**Given** the sample report in CI
**When** veraPDF runs
**Then** the fixture of Story 13.7 is extended with a Class game played to its end through `games.commands`, the sample holds the game section with its charts, and veraPDF passes with the reading order matching the visual order (NFR-6, AD-18).

**Covers:** FR-58, FR-34, FR-17, NFR-6, AD-13, AD-15, AD-18, UX-DR68

### Story 13.9: A Student is told when their data will be deleted

As a Student,
I want to see when my data will be deleted and be reminded before it happens,
So that I download my report in time.

**Acceptance Criteria:**

**Given** Student data is deleted a set period after the Test deadline (FR-77)
**When** this story adds the Class session's deletion date
**Then** the date is the latest effective Test deadline of the Class session (its Test deadline, or the latest per-Student extension from Story 11.13) plus the Institution's retention period, stored as a column on the Class session and written only through `sessions` `service.py`
**And** the retention period is configuration with a stated placeholder (PRD assumption: course end plus six months); Epic 15 adds the Admin setting and the deletion itself (AD-9).

**Given** the Test deadline is moved (Story 5.2) or one Student's deadline is extended (Story 11.13)
**When** the change is saved
**Then** `sessions` `service.py` recomputes the deletion date in the same transaction, and a test covers both cases, so no Student's data can fall due before their own period has run (FR-77).

**Given** a Student on Hjem
**When** the «Rapport» step is shown
**Then** it states the deletion date and that the Student should download the report before it, in copy from `web/src/copy/nb.ts` (FR-57, UX-DR29).

**Given** the deletion date is a configurable number of days away (placeholder 14)
**When** the sweep of Story 3.5 runs the due action this story adds
**Then** each Student of the Class session gets one `digest` notice through `platform/notify` and the digest delivery of Story 3.5, deduplicated per Student and Class session, telling them to download the report (FR-57, AD-9)
**And** the action is idempotent and takes ids only.

**Covers:** FR-57, FR-77, AD-9, UX-DR29

### Story 13.10: The Student report documents the Debrief, the Replay and the Individual test

As a Student,
I want the report to hold my Explanation, key moments, Replay and test answers,
So that it documents the whole Class session and not only the game.

**Acceptance Criteria:**

**Given** a Student who has done the Debrief
**When** the report is built
**Then** it holds the Explanation as written, the key moments from the Debrief summary and the number of Debrief quiz attempts, read through `debrief.service` (FR-58, FR-47)
**And** answers to reflection questions on feelings are left out, and the reflection step of the Debrief (Story 9.6) gets one line, as draft copy in `web/src/copy/nb.ts` for review, that tells the Student who reads the answers (the Lecturers and Assistant lecturers of the Class) and that they are not in the report (FR-58)
**And** no other Student's Explanation or name is included.

**Given** a Student who has played the Replay
**When** the report is built
**Then** it holds the Replay scenario, the Total cost and a chart with its table, read through `replay.service`, and the Replay comparison carries «Ikke like for like.» (FR-58, UX-DR70).

**Given** a Student who has submitted the Individual test
**When** the report is built
**Then** it holds every question, the Student's answers and the scores on answer-key and Interactive items from `analysis.scoring` as stored by `tests`, and no AI score, feedback or Indicative letter (FR-58, C-2)
**And** each Interactive item is rendered as an image of the Student's answer with its value table underneath, using the Interaktiv oppgave rendering from Epic 11, which moves to `web/src/components/` in this story because a second slice now needs it.

**Given** a Student who has not done a step
**When** the report is built
**Then** that section is present and marked as not done, and the report is still produced (FR-58, UJ-8 edge)
**And** a test builds reports for a Student with no Orders, one without a test and one with every step.

**Given** any AI-generated text reaches the report (for example Debrief narration in a key moment)
**When** it is rendered
**Then** it is marked from the `ai_generated` flag only, with the prefix «KI-generert, kan ta feil:» for readers and a machine-readable mark in the tagged PDF (FR-34, UX-DR69).

**Given** the full report
**When** CI runs veraPDF on the sample report, whose fixture from Story 13.8 is extended with a Debrief, a Replay and a submitted Individual test
**Then** it passes with every section present, each chart followed by a table, and the reading order matching the visual order (NFR-6, AD-18, UX-DR68).

**Covers:** FR-58, FR-34, FR-47, NFR-6, AD-7, AD-18, UX-DR68, UX-DR69, UX-DR70

### Story 13.11: The person downloading can add the AI assessment section

As a Student,
I want to choose whether my AI assessment is in the report,
So that a report meant for approval does not carry an AI score unless I want it to.

**Acceptance Criteria:**

**Given** a Student with a ready AI assessment
**When** the Student opens the download action
**Then** a Bryter for adding the AI assessment section is shown and is off by default (FR-58)
**And** downloading without touching it produces a PDF with no AI score, feedback or letter anywhere.

**Given** the Student turns the Bryter on
**When** the report is built
**Then** `build_report_data` receives the option and the AI assessment appears in its own section, labelled as AI-generated, able to be wrong, counting toward nothing and not a grade, with «Teller ikke. Ingen karakter.» (FR-55, FR-58, C-2)
**And** feedback that was dropped by the fact check keeps its note
**And** the section's text is marked for people and in machine-readable form in the tagged PDF (FR-34).

**Given** the Indicative letter
**When** the Student adds the AI assessment section
**Then** the letter appears only if it is turned on for that Student's view and the Student adds it, labelled as an AI-generated indication that is not a grade (FR-56)
**And** where the letter is unavailable for the Class session it never appears.

**Given** the AI assessment is switched off for the Class session, or not ready
**When** the download action is shown
**Then** the Bryter is not offered, and the report is produced without the section (FR-61).

**Given** the stored PDF
**When** a report with the AI section was made
**Then** it is stored under a separate object name from the default report, so a later download without the option never serves the version with the section.

**Covers:** FR-58, FR-55, FR-56, FR-61, FR-34, AD-18

### Story 13.12: Staff download one Student's report at any time

As a Lecturer or Assistant lecturer,
I want to download any Student's report from the Studentside,
So that I can document a Student's work when the course needs it.

**Acceptance Criteria:**

**Given** a Lecturer or Assistant lecturer attached to the Class
**When** they follow the report link on the Studentside, before or after the Test deadline
**Then** the report is built through the same snapshot, print route and `reports-single` job as Story 13.7, with no second pipeline, and is ready within 30 seconds (FR-59, AD-18)
**And** this story adds that link in the slot Story 13.2 left on the Studentside (FR-63)
**And** steps not yet done are marked as not done.

**Given** staff who may read the Student's AI assessment (FR-55)
**When** they download a single report
**Then** the AI assessment section is off by default and can be added by the person downloading (FR-58)
**And** a staff download never holds the Indicative letter, whether the Lecturer turned it on for the Class session or the Student for themselves, because only the Student can add it to a report (FR-56, AD-12).

**Given** a staff member outside the Student's Class, or an Admin without Class membership
**When** they request a report or a signed URL
**Then** the policy denies it and no snapshot is created (FR-5, NFR-7, AD-12).

**Given** a long job is running on `reports-bulk`
**When** a single report is requested
**Then** it still meets the 30-second target, because `worker-batch` keeps `REPORTS_SINGLE_RESERVED` slots (default 2) for `reports-single` (AD-9)
**And** a test runs a single report while a slow test job occupies `reports-bulk`; the ZIP job itself comes in Story 13.13.

**Given** a Student whose data has been deleted
**When** staff open the report link
**Then** the action states that the data is deleted and nothing is built (FR-57, FR-77).

**Covers:** FR-59, FR-63, FR-58, FR-56, FR-5, NFR-7, AD-9, AD-12, AD-18

### Story 13.13: Download all Student reports as one ZIP

As a Lecturer or Assistant lecturer,
I want all Student reports of a Class session in one ZIP file,
So that I can file them for the course without downloading them one by one.

**Acceptance Criteria:**

**Given** the Klasseøkt screen
**When** staff open the «Eksport» block
**Then** it shows the action «Last ned alle Studentrapporter (ZIP)» with the note «ZIP-filen har aldri med KI-vurderingen.» (UX-DR49)
**And** the block is added to the Klasseøkt screen from Epic 5, and the actions for the Completion export and the Game data export are added by their own stories.

**Given** staff press the ZIP action
**When** the job is deferred on `reports-bulk`
**Then** the block reads «ZIP-filen lages. Du får beskjed når den er klar, innen 10 minutter.» (FR-59)
**And** the job builds one report per Student in `reporting_students()` through `build_report_data` with the AI assessment option forced off, whatever the caller sent (AD-13, AD-18)
**And** a test opens the ZIP and asserts that no file contains an AI score, feedback or Indicative letter (C-2).

**Given** a Class session with 250 Students
**When** the ZIP job runs
**Then** it is ready within 10 minutes (placeholder target from the PRD), shown by a timed test on generated data
**And** the ZIP is stored through `platform/storage` under the Class session's path, and files inside are named so a Lecturer can find a Student.

**Given** the ZIP is ready
**When** the job finishes
**Then** the requester is told through `platform/notify` and the block offers the download as a signed URL that expires (NFR-7, AD-9)
**And** the URL is created only after the `platform/authz` policy allowed that User.

**Given** the job fails, or is retried
**When** the block is shown
**Then** it reads «ZIP-filen kunne ikke lages.» with «Prøv igjen»
**And** the job is idempotent on Class session and request, so a retry does not leave two ZIPs.

**Given** the «Eksport» block at 320 px and 200% text
**When** Playwright and axe run
**Then** it reflows, the status line is announced politely, and axe reports no violations (NFR-6).

**Covers:** FR-59, NFR-6, NFR-7, AD-9, AD-12, AD-13, AD-14, AD-18, UX-DR49

### Story 13.14: Export the Completion status

As a Lecturer,
I want the Completion status of a Class session as a CSV or Excel file,
So that I can approve the course requirement in the course's own system.

**Acceptance Criteria:**

**Given** the «Eksport» block
**When** the Lecturer presses «Last ned fullføringsliste (CSV eller Excel)» and chooses a format
**Then** a file downloads with one row per Student in `reporting_students()`: name, email, the date each step was done, the share of Class game Weeks the Student ordered in, and whether an obligatory requirement is met (FR-60, AD-13)
**And** every value comes from `reports.service.completion_status`, so the file agrees with the Studentside, Hjem and the funnel (AD-16).

**Given** a Student who fell short because of the playout or the group's pace, or whose status was corrected
**When** the row is written
**Then** it carries the share of Weeks played in the playout and a mark that the status was corrected by a Lecturer (FR-17)
**And** a make-up game is shown as its own column with its date.

**Given** the export must not rest on an AI judgement
**When** the file is built
**Then** it holds no AI score, AI feedback or Indicative letter, and a test asserts the column list against a fixed allow-list (FR-60, FR-56, C-2)
**And** the block shows the note «Ingen av filene har KI-vurderinger.»

**Given** names and emails live only in `identity` tables
**When** the file is built
**Then** they are read through `identity.service` at export time and the file is streamed to the Lecturer without being stored (AD-14).

**Given** a file opened in Excel with Norwegian settings
**When** the Lecturer opens the CSV or the .xlsx
**Then** æ, ø and å, dates and the decimal comma show correctly, checked by a test on both formats.

**Given** an Assistant lecturer
**When** they open the «Eksport» block
**Then** they see the report downloads only, and the Completion export endpoint denies them through `platform/authz` (AD-12).

**Covers:** FR-60, FR-17, FR-56, AD-12, AD-13, AD-14, AD-16, UX-DR49

## Epic 14: Class report and statistics

A Lecturer can read a live Class report for a Class session, compare it with earlier Class sessions on written aggregates, and show all Class games in a plenary without names or ranking. Students can see all Class games side by side once their own Debrief is done and the Play deadline has passed. The epic owns the class part of `api/app/modules/reports/` and `web/src/modules/reports/`, and reuses `reports.scope`, the chart module and `game_summaries`.

### Story 14.1: Class report of the games

As a Lecturer,
I want a report of how the Class games went across the Class session,
So that I can plan the plenary from what the class actually did.

**Acceptance Criteria:**

**Given** a Lecturer of the Class
**When** they open the Klasserapport from the Oversikt or the Klasse
**Then** it shows the funnel (the cached funnel from Epic 7), the distribution of Total cost per Role, Order amplification per Role, the most common Detected patterns across Class games, and the share of Seats played by AI players (FR-64, UX-DR55)
**And** every figure is computed in the api from `game_summaries`, the Decision log and the `analysis` facts of Epic 9, read through `reports.scope.reporting_games()` with `purpose=class`, so lecturer test Games, make-up games, simulations and Control test data are left out (AD-13, AD-25)
**And** the web app computes no medians or costs (AD-10).

**Given** FR-68 and FR-70 name the Class report
**When** the report is shown
**Then** it lists the Share of LLM Orders per Game, records when a cost limit or a Play guard switch took effect, gives the share of Seats switched by the Play guard, and shows the plausibility rating per AI mode (FR-68, FR-70, FR-79)
**And** these read `decided_by`, `fallback` and `reason` through the one mapping of AD-15
**And** this story adds the aggregate of the plausibility ratings that Story 10.8 stores: counts and the median per AI mode over the Games in `reports.scope`, with no `user_id`, read through `games` `service.py`; an individual rating is never shown (FR-70, AD-13).

**Given** no Class game has finished, or only some have
**When** the report is shown
**Then** it reads «Ingen spill er ferdige ennå.», or «Oppdateres etter hvert som studentene blir ferdige. 41 av 60 spill er med.» with the real counts (FR-64).

**Given** the report is open while Students progress
**When** a Game finishes or a step is recorded
**Then** the page refetches over REST through the topic-to-query bridge, on a topic of the AD-8 catalogue; if a new topic is needed it is added to the catalogue and the registry test (AD-8)
**And** the report endpoint for a Class session of 100 Class games answers from maintained summaries and stored facts, not by replaying Games (AD-25).

**Given** each chart on the page
**When** it renders
**Then** it comes from `web/src/components/charts`, reuses Kostnadsfordeling and Trakt from Epic 7, has «Vis som tabell» underneath, lists Roles with Fabrikk at the top in Role lists and Detaljist to Fabrikk in per-Role tables, and uses the shared number formatter (AD-18, UX-DR55, UX-DR73)
**And** cost is split into Lager and Restordre with both numbers printed, and Detected patterns are titled «Mønstre».

**Given** an Assistant lecturer, a Lecturer of another Class, or an Admin without Class membership
**When** they request the Klasserapport
**Then** the `platform/authz` policy denies each of them with the permission-denied state; the Klasserapport is for the Lecturers of the Class, as FR-64 and the UX spine have it (FR-5, AD-12).

**Given** the page at 320 px, 1440 px and 200% text
**When** Playwright and axe run
**Then** it reflows without horizontal page scroll and axe reports no violations (NFR-6).

**Covers:** FR-64, FR-68, FR-70, FR-79, FR-5, NFR-6, AD-8, AD-10, AD-12, AD-13, AD-15, AD-18, AD-25, UX-DR55, UX-DR73

### Story 14.2: Class report of learning results

As a Lecturer,
I want to see Starting task results next to the matching test items, and results per question,
So that I can see what the class learned and which questions were hard.

**Acceptance Criteria:**

**Given** Students have done the Starting task and submitted the Individual test
**When** the Lecturer opens the learning part of the Klasserapport
**Then** it shows Starting task results beside the matching Individual test items, for the Students who did both, with the counts (FR-64)
**And** it shows results per Individual test question from the computed scores stored by `tests`, read through `tests.service` over `reporting_students()` (AD-13).

**Given** AI assessments are ready
**When** the report is shown
**Then** it shows the distribution of AI assessment total scores with the Core-only subscore next to the total, and a note that Adapted items differ between Students (FR-64)
**And** the Core-only subscore comes from a pure function this story adds to `api/app/analysis/` beside `analysis.total_score` of Story 12.2: the same weighting over Core items only, with Adapted items left out and the remaining Item weights rescaled to 100%, covered by pytest golden cases (AD-1)
**And** the distribution is labelled as AI-generated and not a grade, with «Teller ikke. Ingen karakter.» (FR-55, C-2)
**And** no Indicative letter and no self-enabled letter appears in any figure (FR-56).

**Given** the AI assessment is switched off for the Class session, or not ready yet
**When** the report is shown
**Then** the AI assessment part states that state and the computed parts are shown as usual (FR-61).

**Given** a question the Lecturer excluded, or a Student with an extended Test deadline
**When** results per question are shown
**Then** excluded questions are listed as excluded and left out of totals, and the count of Students still to submit is stated.

**Given** the Lecturer reads results per question
**When** fewer than 10 Students answered a question or a group
**Then** the figures are still shown to the Class's own staff, since they may read each Student's answers (FR-63); the threshold of 10 applies to stored aggregates and cross-Institution views, not to this live report.

**Given** each chart
**When** it renders
**Then** it has «Vis som tabell», and Playwright with axe passes at 320 and 1440 px (NFR-6, UX-DR55).

**Covers:** FR-64, FR-55, FR-56, FR-61, NFR-6, AD-1, AD-13, AD-18, UX-DR55

### Story 14.3: Compare Class sessions in Tverrklasse-statistikk

As a Lecturer,
I want to compare this Class session with my earlier ones on the Class report measures,
So that I can see whether a change in setup made a difference, also after last year's Student data is deleted.

**Acceptance Criteria:**

**Given** a Class session
**When** `reports.write_aggregate(class_session_id)` runs
**Then** it writes one anonymised aggregate row set for the Class session into a table owned by `modules/reports`: the Class report measures of Story 14.1 and Story 14.2 with Core-only scores, and the keys needed to judge comparability (Game settings, AI mode, model config id, prompt versions, Effort level, question set version, Item weights, Scoring guide version) (FR-65, AD-14)
**And** a measure is written only where its group holds 10 or more Students; smaller groups are stored as withheld
**And** the rows hold no `user_id`, `seat_id`, Game id, name or free text.

**Given** the aggregate must exist before data is deleted
**When** the sweep of Story 3.5 runs the due action this story adds
**Then** it finds each Class session whose latest effective Test deadline has passed (the value Story 13.9 uses), for which `tests.service` reports no open attempt, and whose aggregate is missing or older than its latest AI assessment, read from a `written_at` column on the aggregate's header row; it defers the idempotent job on `reports-bulk`, keyed by Class session, and the job replaces that Class session's rows (AD-9)
**And** a test shows that no aggregate is written while the test is still open, also when no Student has opened it or the first Students have submitted early, and that a Class session with the AI assessment switched off gets its aggregate once, after the deadline
**And** `reports.service.write_aggregate` is exposed so the shared deletion routine of Epic 15 can call it first.

**Given** a Lecturer with access to two or more Class sessions
**When** they open Tverrklasse-statistikk
**Then** the page reads only the written aggregates, never live tables, so the comparison gives the same answer before and after deletion (AD-14)
**And** it shows the Class report measures per Class session side by side, with «Samme mål, samme regnestykke.», each chart with «Vis som tabell» (FR-65, UX-DR55)
**And** a test deletes the live rows of a seeded Class session directly and finds the same figures on the page; the test against the real deletion routine belongs to Story 15.3.

**Given** the Lecturer has only one Class session, or a Class session whose aggregate is not written yet
**When** the page is shown
**Then** it reads «Du har ingen tidligere Klasseøkter å sammenligne med.», or lists the Class session as not ready for comparison.

**Given** a Lecturer
**When** the list of Class sessions is built
**Then** it comes from `classes_visible_to(user)` in `platform/authz`, an archived Class is included, and a Class session of another Lecturer's Class is never listed (FR-6, AD-12)
**And** Control test Class sessions are never listed (AD-13, AD-27).

**Given** Epic 7 left the last-year mark off the Kostnadsfordeling because it needs aggregates
**When** the Kostnadsfordeling is shown on the Oversikt and the Klasserapport, and a written aggregate exists for the previous Class session of the same Class
**Then** this story draws the dashed «Fjoråret» mark at that aggregate's median chain Total cost, and adds it to the text summary in the form «Median 1 954. Midterste halvdel 1 500–2 600. Fjoråret 2 740.» (UX-DR51)
**And** the mark and the text are absent when there is no previous aggregate or its group was under 10 Students, and the median is served by the api, never computed in the web app (AD-10).

**Covers:** FR-65, FR-6, AD-9, AD-10, AD-12, AD-13, AD-14, AD-27, UX-DR51, UX-DR55

### Story 14.4: Filter comparisons and label Class sessions that differ

As a Lecturer,
I want to filter the comparison and be told when two Class sessions are not comparable,
So that I do not read a difference in setup as a difference in learning.

**Acceptance Criteria:**

**Given** Tverrklasse-statistikk with several Class sessions
**When** the Lecturer filters by Game settings, AI mode, model, prompt version or Effort level
**Then** only matching Class sessions are compared, the filters are text-button toggles with `aria-pressed` and counts, and filtering is done on the aggregates' stored keys (FR-65).

**Given** two compared Class sessions that differ on Game settings, AI mode, model, prompt version, Effort level, question set, Item weights or Scoring guide version
**When** any comparison of them is shown
**Then** each differing Class session is labelled with what differs, in text and not by colour alone, in the chart, in «Vis som tabell» and in the chart's `<title>` (FR-65, NFR-6)
**And** the label is computed in the api from the stored keys.

**Given** test scores are compared
**When** the question set, Item weights and Scoring guide version are the same
**Then** the scores are called comparable, and otherwise the score comparison is labelled as not comparable (FR-65)
**And** score comparisons use Core-only scores only.

**Given** a measure that was withheld in one Class session because its group had fewer than 10 Students
**When** the comparison is shown
**Then** that cell states that the group was too small, and no figure can be derived from the other cells (AD-14).

**Given** the plausibility rating (FR-70)
**When** it is compared
**Then** it is shown per AI mode across Class sessions.

**Given** the page with filters applied
**When** Playwright and axe run at 320 and 1440 px
**Then** the filters and labels are operable by keyboard, announced politely on change, and axe reports no violations (NFR-6).

**Covers:** FR-65, FR-70, NFR-6, AD-14, UX-DR55

### Story 14.5: Students see all Class games side by side

As a Student,
I want to see every Class game's Orders next to my own after the Debrief,
So that I can see whether all teams behaved alike.

**Acceptance Criteria:**

**Given** a Student whose own Debrief is not done, or a Class session whose Play deadline has not passed
**When** the Student opens Hjem
**Then** the entry for «Alle spill side om side» is locked and reads «Åpnes når Debriefen din er ferdig og Spillfristen er passert.» (FR-86, UX-DR64)
**And** the gate is checked in the api through `progress.has_step` and the Class session's Play deadline, and the endpoint refuses with a stable error code while locked.

**Given** both conditions hold
**When** the Student opens the view
**Then** it shows, per Role, the Orders per Week of every Class game in the Class session, with the Student's own Class game marked in text and by line style, not by colour alone (FR-86, NFR-6)
**And** the charts come from `web/src/components/charts`, with «Vis som tabell» in game-number order.

**Given** the view must be anonymous and unranked
**When** the data is served
**Then** a server-side endpoint returns Orders per Role and Week keyed by game number only, with no names, no `user_id`, no occupant data and no Total cost, and it marks only the requesting Student's own game (FR-86, AD-12)
**And** nothing in the view sorts, ranks or highlights a game by cost or result (UX-DR72, UX-DR78)
**And** a test asserts the response schema holds no identifying field.

**Given** the games to show
**When** the endpoint builds the list
**Then** it reads `reporting_games()` with `purpose=class` for the Student's own Class session only, so lecturer test Games, make-up games and Replays are left out (AD-13).

**Given** a Student who took a make-up game or whose Seat was taken over
**When** they open the view
**Then** the Class game they were allocated to is the one marked as their own.

**Given** the view on a phone
**When** Playwright and axe run at 320 and 360 px
**Then** only the two-dimensional chart and table scroll inside their own region, and axe reports no violations (UX-DR75, NFR-6).

**Covers:** FR-86, NFR-6, AD-12, AD-13, AD-16, AD-18, UX-DR64, UX-DR72, UX-DR75, UX-DR78

### Story 14.6: The Lecturer shows all Class games in a plenary

As a Lecturer,
I want a view of all Class games that I can put on the projector,
So that the class can see the pattern repeat without anyone being named or ranked.

**Acceptance Criteria:**

**Given** the Oversikt after Class games have been played
**When** the Lecturer presses the secondary button «Vis i plenum»
**Then** a plenary page opens that reuses the Matrisevegg and the laptop layout on `paper`, with larger cells and fewer columns, and the line «Mønsteret går igjen, uten navn og uten rangering.» (FR-86, UX-DR42)
**And** the caption under the wall reads «Rødt: restordre, under null. Blått: lager, over null. Tallet i cellen er netto lager.», and the legend is always visible.

**Given** the plenary page is shown on a shared screen
**When** its data is fetched
**Then** it comes from a server-side anonymised endpoint that returns game numbers and per-Week values only, with no Student names, occupants, «Venter ellers», Varselbånd or Spillstyring data, so nothing private can be shown by mistake (AD-21 principle, FR-86)
**And** the page does not call the staff overview endpoints.

**Given** the Visningsbryter on the plenary page
**When** the Lecturer chooses «Vis som tabell»
**Then** the table lists the games in game-number order with a number in every cell, has no names, and offers no sorting by cost (UX-DR42)
**And** the Rolle filter from Epic 7 is offered, and cost sorting and the near-Takeover tint are not.

**Given** FR-86 asks for Orders per Role
**When** the Lecturer switches the plenary page to Orders
**Then** the same per-Role Orders charts as Story 14.5 are shown with no game marked, reusing that story's components.

**Given** the plenary page before any Class game has finished, or opened by an Assistant lecturer
**When** it loads
**Then** it shows the games played so far with their real counts, and access follows the same `platform/authz` policy as the Oversikt (AD-12).

**Given** the plenary page at 1440 px and at 320 px
**When** Playwright and axe run
**Then** text stays at or above the wall floor of 9 px, the wall keeps keyboard focus on the same game across updates, and axe reports no violations (UX-DR4, NFR-6).

**Covers:** FR-86, NFR-6, AD-12, AD-13, AD-18, UX-DR42

### Story 14.7: The Admin compares across Institutions (cut list)

As an Admin,
I want to compare anonymised aggregates across Institutions,
So that I can see how the exercise works in different places without seeing any Student.

**Acceptance Criteria:**

**Given** `FEATURE_CROSS_INSTITUTION_STATS` is off
**When** any User opens the Admin area or calls the endpoint
**Then** the view and its endpoint do not exist, and Story 14.3 and Story 14.4 work unchanged (AD-17).

**Given** the flag is on
**When** the Admin opens the cross-Institution view
**Then** it shows the written aggregates of Story 14.3 grouped by Institution, over groups of at least 10 Students only, with the comparability labels of Story 14.4 (FR-65)
**And** it reads only the aggregate table, never live tables, and shows no Class name, Lecturer name or Student data (AD-14, FR-5).

**Given** a Lecturer or Assistant lecturer
**When** they request the cross-Institution view
**Then** the `platform/authz` policy denies it; the view is Admin only in v1 (FR-65, AD-12).

**Given** an Institution with a single Class session
**When** the view is shown
**Then** it is listed only if every shown measure rests on 10 or more Students, and otherwise it is withheld.

**Covers:** FR-65, FR-5, AD-12, AD-14, AD-17

### Story 14.8: Export a Class session's Game data (cut list)

As a Lecturer,
I want the week-by-week Game data of a Class session as a CSV file,
So that I can analyse the games in my own tools.

**Acceptance Criteria:**

**Given** `FEATURE_GAME_DATA_EXPORT` is off
**When** the «Eksport» block is shown
**Then** the action «Last ned spilldata (CSV)» is absent and the endpoint does not exist (AD-17).

**Given** the flag is on
**When** the Lecturer presses «Last ned spilldata (CSV)» in the «Eksport» block from Story 13.13
**Then** a CSV downloads with one row per Game, Week and Seat, for the Class games, make-up games and Replays of the Class session: game number, the Game's purpose in its own column, Role, incoming order, incoming delivery, inventory, backlog, Order, cost, who decided the Order and the fallback mark, using the one mapping of AD-15 (FR-88)
**And** it reads `reporting_games()` for that Class session, so lecturer test Games, simulations and Control test data are left out (AD-13).

**Given** the file must hold no AI assessments
**When** it is built
**Then** it has no AI score, feedback or Indicative letter, checked by a test against a fixed column allow-list, and the block shows «Ingen av filene har KI-vurderinger.» (FR-88, C-2).

**Given** names live only in `identity` tables
**When** the file is built
**Then** Seats are identified by game number and Role, with an occupant kind (Student or AI player) and no name or email, and the file is streamed without being stored (AD-14).

**Given** an Assistant lecturer, or a Lecturer of another Class
**When** they call the endpoint
**Then** the `platform/authz` policy denies it (AD-12).

**Covers:** FR-88, AD-12, AD-13, AD-14, AD-15, AD-17, UX-DR49

## Epic 15: Data rights and pilot readiness

A Student can see all data the product stores about them. The Admin can delete a User on instruction, let retention delete on schedule, export pseudonymised data, pin a model, watch AI cost and errors per Class session, and the founder can show that the platform is ready for the pilot. The epic owns `api/app/modules/ops/` and `web/src/modules/ops/`, extends `modules/identity` and `modules/admin`, and settles the per-session error counts store, the load test method and the pre-pilot operations checks.

### Story 15.1: A Student sees their own data in «Mine data»

As a Student,
I want to see every category of data the product stores about me,
So that I can use my right of access without asking anyone.

**Acceptance Criteria:**

**Given** a logged-in Student
**When** they open «Mine data» from Hjem through the profile
**Then** the page shows one row per stored category: konto og profil, ordrer, Forklaring, refleksjonssvar, Debrief-quiz, testsvar, KI-vurdering, veiledende bokstav, and tilrettelegging if any, each with «Vis» (FR-75, UX-DR67)
**And** «Last ned Studentrapport» is at the top and reuses the report download of Story 13.7
**And** this story adds the way in, since no earlier story builds a profile page: a Lenke «Mine data» beside the User's name on Hjem.

**Given** a category row
**When** the Student presses «Vis»
**Then** the stored data of that category is shown, including reflection and follow-up text, Debrief summaries, Starting task results, Messages received and the Student's own flags, read through each owning module's `service.py` (FR-75)
**And** a category with nothing stored says so in text.

**Given** the data belongs to one person
**When** any «Mine data» endpoint is called
**Then** the `platform/authz` policy allows only the User's own data, and every query joins through a scope helper (FR-5, AD-12)
**And** other Students appear by Role only.

**Given** a new table that holds personal data is added later
**When** CI runs
**Then** a registry test reads the database metadata and fails unless every table with a `user_id` column, or with a column of text that a User wrote, is listed in a personal-data registry in `modules/identity`, either with its «Mine data» category or as holding no personal data with the reason, so no stored category can be missing from the page (AD-14)
**And** the short-lived report snapshot of Story 13.7 is listed with its lifetime.

**Given** the Student's effective Test deadline has not passed
**When** «Mine data» is shown
**Then** «Last ned Studentrapport» states when it opens, and every «Vis» works at any time.

**Given** the page at 320 px, 360 px and 200% text
**When** Playwright and axe run
**Then** it reflows without horizontal scroll, copy comes from `web/src/copy/nb.ts`, and axe reports no violations (NFR-6, FR-72).

**Covers:** FR-75, FR-5, FR-72, NFR-6, AD-12, AD-14, UX-DR67

### Story 15.2: The Admin deletes a User on the Institution's instruction

As an Admin,
I want to delete a User and their personal data when the Institution instructs it,
So that the right to erasure is met without breaking other Students' Games.

**Acceptance Criteria:**

**Given** the Admin on a User in «Brukere og roller»
**When** they choose to delete the User
**Then** the button states the consequence in copy from `nb.ts`, a reference to the Institution's instruction is required, and one press starts the deletion with no second dialog (FR-76, UX-DR9)
**And** the action is recorded through `platform/audit` with actor, time and target id, and no name or email in the record (FR-3, AD-14).

**Given** `identity.delete_user(user_id)`
**When** it runs
**Then** it runs the one shared routine in this order: write anonymised aggregates for each affected Class session through `reports.service.write_aggregate`, anonymise the User in the `identity` tables, delete the free text the Student wrote, the AI feedback that quotes it and the scrubbed `llm_call` bodies, and delete the objects in the `reports` bucket through `platform/storage`: the User's own report PDFs and every ZIP of the Class sessions the User was in, since such a ZIP holds that User's report (AD-14)
**And** the routine is idempotent and safe to repeat after a failure part-way
**And** the personal-data registry from Story 15.1 gains a deletion handling per table, and its test fails for a table without one, so access and deletion cannot drift apart.

**Given** the User held Seats
**When** the routine has run
**Then** every Seat, occupancy row and `seat_week` row remains with its `user_id` now pointing to an anonymous User, no Decision log row is changed, and the other Students' Games, Debrief charts and reports still render with the Seat shown by Role only (FR-76, AD-15)
**And** a test replays a finished Game through the engine after deletion and the stored states still verify (AD-4).

**Given** the User holds a Seat in a Class game that is still running
**When** the deletion runs
**Then** the Seat is first handed to an AI player through `games.commands.takeover` on the system-actor path that Story 8.2 built, which writes the reason `takeover_inactivity`, so the group is not left waiting and no reason is added to the AD-5 list; the occupancy row has no `actor_user_id`, and the Admin is named only in the audit record (AD-2, AD-5, NFR-4)
**And** `games.rules.can_take_over` gets one added case for this: the system may take over at once a Seat whose User is being deleted, whatever its wait times; the other Students get the same notices as for any Takeover, and no Reclaim is possible.

**Given** the deletion is done
**When** anyone looks for the User
**Then** the User cannot log in, does not appear in search, the Roster, the Studentside or the Completion export, and a signed URL to an old report no longer resolves (FR-76, NFR-7).

**Given** a User who owns Classes as a Lecturer
**When** the Admin tries to delete them
**Then** the deletion is blocked with the same rule and message as revoking the role in Epic 3: «Bård eier 2 Klasser. Legg til en annen Faglærer eller arkiver Klassene først.» (FR-2).

**Given** names must not survive elsewhere
**When** the deletion test finishes
**Then** it searches every table, the job tables and the local storage mock for the User's name, email and student number and finds none (AD-14)
**And** it asserts that no ZIP of the User's Class sessions remains in the storage mock, because a text search cannot see inside one.

**Covers:** FR-76, FR-2, FR-3, NFR-4, NFR-7, AD-2, AD-4, AD-5, AD-12, AD-14, AD-15, UX-DR9

### Story 15.3: Student data is deleted automatically when retention ends

As an Admin,
I want Student personal data in a Class session to be deleted a set period after the Test deadline,
So that the Institution's retention rule is kept without anyone remembering to do it.

**Acceptance Criteria:**

**Given** an Institution in the Admin area
**When** the Admin sets its retention period
**Then** it is stored per Institution, the default is configuration with a stated placeholder (PRD assumption: course end plus six months, extendable by the Institution), and the change is audited (FR-77, FR-3)
**And** each Class session's deletion date is recomputed by the rule of Story 13.9 (the latest effective Test deadline plus the retention period), and Students see the new date where Story 13.9 shows it.

**Given** a Class session whose deletion date has passed
**When** the sweep of Story 3.5 runs the due action this story adds
**Then** it finds the Class session due and calls `ops.retention`, one Student per transaction, which runs the same shared routine as `identity.delete_user`, scoped to that Class session's data (FR-77, AD-9, AD-14)
**And** there is one implementation of the routine, proven by a test that calls both entry points and compares the result
**And** a User with no other Class session is anonymised, and a User with a later Class session keeps the account and that later data.

**Given** the aggregates for Cross-class statistics
**When** retention is about to delete a Class session's data
**Then** `reports.service.write_aggregate` has run successfully first, only over groups of 10 or more Students, and retention does not proceed for that Class session if it fails (FR-65, AD-14)
**And** Tverrklasse-statistikk gives the same figures before and after.

**Given** Roster addresses and Invitations of people who never registered, which are personal data with no User behind them
**When** retention has run for the last Class session of a Class
**Then** those Roster rows and Invitations are deleted through `classes` and `identity` `service.py`, and they are listed in the personal-data registry of Story 15.1 with this handling (FR-77, AD-14)
**And** this is what "kept until the retention period ends" means for an archived Class in Story 4.10: the deletion date of its last Class session, or, for a Class that never had one, its archive time plus the Institution's retention period; the Class row itself stays, with no personal data, as the owner of its aggregates (FR-6)
**And** a test with a Student whose Test deadline was extended shows that nothing of that Class session is deleted before the date of Story 13.9.

**Given** a Control test Class session
**When** retention runs
**Then** it follows the operator-owned Institution's own retention date, not that of any course Institution (AD-27).

**Given** the sweep is interrupted or runs twice
**When** it runs again
**Then** it continues where it stopped and deletes nothing twice, and the run is logged with counts and ids only (AD-9).

**Given** retention has run for a Class session
**When** the Lecturer opens the Class session
**Then** Games, the Class report and Spillinnsikt still render with Seats by Role, and the Studentside, report downloads and the Completion export state that the Student data is deleted.

**Covers:** FR-77, FR-65, FR-6, FR-3, AD-9, AD-14, AD-27

### Story 15.4: The Admin exports pseudonymised data for evaluation

As an Admin,
I want to export the Decision log and Students' answers with stable pseudonyms,
So that AI players and learning outcomes can be evaluated without names.

**Acceptance Criteria:**

**Given** a Class session
**When** the Admin opens the pseudonymised export
**Then** the Class session can be chosen only if an Institution agreement is recorded for it (who agreed, when, who is controller for the evaluation), and recording the agreement is an audited Admin action (FR-71, AD-12)
**And** `can(admin, "export_pseudonymised", class_session)` in `platform/authz` is the only gate, with a test that it fails without the agreement.

**Given** the key holder, someone other than the founder
**When** the export is run
**Then** the pseudonym key is supplied in the run form at that moment, is used in memory for that request only, and is never written to the database, a job argument, a log line, an environment variable or the audit record (AD-14, AD-9)
**And** the export therefore runs inside the request and streams the file, not as a job
**And** a test searches the database and the captured logs for the key after a run.

**Given** the first export ever
**When** the key is supplied
**Then** the system stores only a fingerprint of the key; on every later run a key with another fingerprint is refused with a stable error code and a message that the key has changed (AD-14)
**And** replacing the stored fingerprint is a separate audited Admin action.

**Given** an allowed export
**When** the file is built
**Then** it holds, for the chosen Class sessions, the Decision log (with `state_seen`, `decided_by`, `fallback`, reference Orders and LLM call metadata), Starting task results, Explanations and Individual test answers, with each Student replaced by `HMAC(key, user_id)` (FR-71, FR-67, AD-15)
**And** it holds no name, email, student number, AI assessment or Indicative letter
**And** the same Student gets the same pseudonym across files and across runs with the same key.

**Given** the data scope
**When** rows are selected
**Then** they are read through `reports.scope`, so lecturer test Games, simulations, Control test data and test Students are left out (AD-13).

**Given** each run
**When** it finishes or is refused
**Then** `platform/audit` records actor, time, Class sessions and key fingerprint, and the Admin's export list shows each export with the Class session's deletion date from Story 15.3, by which the exported data must also be deleted (FR-3, FR-71, FR-77).

**Given** a Lecturer, or an Admin for a Class session without an agreement
**When** they call the export endpoint
**Then** it is denied and nothing is read (AD-12).

**Covers:** FR-71, FR-77, FR-67, FR-3, AD-9, AD-12, AD-13, AD-14, AD-15

### Story 15.5: The Admin pins and freezes a model for Class sessions

As an Admin,
I want to choose the model config for a Class session and freeze it across several,
So that no model change happens during a Class session or a learning study.

**Acceptance Criteria:**

**Given** the Admin-område
**When** the Admin opens «KI-kostnad», the area this story adds with its first page, and there a Class session's model setting
**Then** the page lists the model configs from the tables of Story 2.2 with provider, endpoint, region, model version, Effort levels and the results of their all-AI test runs from `python -m app.sim` (cost per Game, fallback rate, share of Seats switched by the Play guard) (FR-68, UX-DR57)
**And** cost per Game, the fallback share and the share of Seats switched by the Play guard are read from the `effort_measurements` rows of Story 2.12 through `ai.config`, so no figure is computed a second way
**And** all reads and writes go through `ai.config`, and no code outside `app/ai` touches the model config tables (AD-6).

**Given** a Class session before its Start date
**When** the Admin pins a model config
**Then** the Class session references that config id, replacing the default it got when created (Story 5.1), and the change is audited (FR-68, FR-3)
**And** the Lecturer's «Innsatsnivå» block offers only the Effort levels of the pinned config that were measured inside the cost and time limits (FR-78).

**Given** a Class session after `sessions.lock`
**When** the Admin tries to change its model config
**Then** the change is refused with a stable error code, because the config id is frozen in `SessionRuntime` (AD-4, FR-68)
**And** the page shows the pinned model version, endpoint and prompt versions as read-only.

**Given** a learning study over several Class sessions
**When** the Admin freezes a model config
**Then** the chosen Class sessions get the same config id, new Class sessions get it as their default until the freeze is lifted, and editing a referenced config creates a new row and never changes the frozen one (FR-68, AD-6).

**Given** a model config whose provider has no key in production
**When** the Admin pins it for a Class session in LLM mode
**Then** the page warns that the Class session cannot be locked without the key (AD-17).

**Given** the provider, route and model are still open (issues #8, #9)
**When** this story is built
**Then** it uses the mock provider's config and whatever configs the prototype recorded, and invents no provider-specific values.

**Covers:** FR-68, FR-78, FR-3, AD-4, AD-6, AD-17, UX-DR57

### Story 15.6: The Admin sees AI cost and sets the cost limit

As an Admin,
I want to see AI cost per Class session, Game and day and set a cost limit,
So that a Class session cannot spend more than agreed.

**Acceptance Criteria:**

**Given** the «KI-kostnad» area that Story 15.5 added
**When** the Admin opens its cost page
**Then** it shows AI cost per Class session, and for a chosen Class session per Game and per day, with the budget row's limit, reserve and spent (FR-69, NFR-8, UX-DR57)
**And** the figures are read through `ai.budget` and an `ai` service over `llm_call`, summed unrounded as `NUMERIC(18,8)` USD and shown with the shared number formatter (AD-6)
**And** cost per Game is shown against USD 0.10 and cost per Student against USD 0.50, with a text mark where a figure is above (C-3).

**Given** a Class session
**When** the Admin sets or raises its cost limit
**Then** the limit is written through `ai.budget` on the one budget row, the default for a new Class session is `AI_DEFAULT_SESSION_BUDGET_USD`, and the change is audited (FR-69, FR-3)
**And** the size of the reserve for the Debrief and the AI assessment is configuration with a stated placeholder until the prototype sets it.

**Given** a Class session whose players budget is exhausted (`players_exhausted_at` is set)
**When** the screen is shown
**Then** it reads in the form «Grensen er nådd for class-of-1994. LLM-spillerne er byttet til regelbaserte.» with the time it happened (FR-69, UX-DR57)
**And** the state is read through `ai.budget.state(scope)`, and the switch to Rule-based players remains Epic 2's and is not rebuilt.

**Given** Epic 2 only records the cost-limit state and sends nothing
**When** a Class session's `players_exhausted_at` is set
**Then** this story tells every Lecturer of the Class once, through `platform/notify.enqueue` with a dedupe key per Class session, in the product and by mail, that the LLM players have switched to Rule-based players for the rest of the Class session (FR-69, AD-9)
**And** the notice is found by a due action this story adds to the sweep of Story 3.5, reading `ai.budget.state`, so `app/ai` imports no module and a lost event is repaired on the next sweep
**And** the notice kind is registered as a `digest` kind in the delivery of Story 3.5, with a test that a second sweep sends nothing.

**Given** the reserve is also used up
**When** the screen is shown
**Then** it states that the Debrief now runs from code and that the AI assessment waits for the Admin's decision (FR-69, FR-44)
**And** the Admin has two actions, each with its consequence stated above the button: raise the limit, which also calls `assessment.service.resume_for_session(class_session, actor)` so that assessment restarts; or stop the AI assessment for that Class session, which calls `assessment.service.stop_for_session(class_session, actor)`, so the retries end and Students see the switched-off state; both functions come from Story 12.4
**And** this story builds neither the retry rule nor the two commands; it only calls them, and both actions are audited (FR-3).

**Given** evaluation budgets used by simulation runs (AD-22)
**When** cost is listed
**Then** they are shown apart from Class sessions, so prototype spend never counts against a Class session.

**Given** a Lecturer or a User without the Admin role
**When** they request the screen
**Then** the `platform/authz` policy denies it (AD-12)
**And** Playwright with axe passes at 320 and 1440 px, with «Vis som tabell» under each chart (NFR-6).

**Covers:** FR-69, FR-3, NFR-6, NFR-8, AD-6, AD-9, AD-12, AD-22, UX-DR57

### Story 15.7: The Admin is alerted when daily AI spend is high

As an Admin,
I want an alert when AI spend in one day passes a set amount,
So that a runaway cost is noticed the same day.

**Acceptance Criteria:**

**Given** Epic 2 sends no alert, and the amount `AI_DAILY_ALERT_USD`
**When** a due action this story adds to the sweep of Story 3.5 finds that today's AI spend across all scopes has passed it
**Then** it calls `platform/notify.enqueue` for each Admin with a dedupe key for that date, so one alert is sent per Admin per day (FR-69, AD-9)
**And** the alert is delivered as an `immediate` kind; this story registers the kind in the delivery table of Story 3.5 and records that choice, since the spine lists only the founder-decided kinds.

**Given** the alert
**When** the Admin opens it, in the product or by email
**Then** it links to «KI-kostnad» for that day and names the Class sessions with the highest spend by their Class session name, with no Student data.

**Given** the day is the Europe/Oslo calendar day
**When** spend is summed
**Then** the sum comes from the `ai` service, not from a sum inside `ops`, and a test covers a day boundary (AD-6).

**Given** the amount is not set
**When** the sweep runs
**Then** no alert is sent and the «KI-kostnad» cost page of Story 15.6 states that no daily alert is set.

**Covers:** FR-69, AD-6, AD-9

### Story 15.8: The Admin sees errors, fallback and response times per Class session

As an Admin,
I want error counts, fallback rate, AI response times and AI cost per Class session on one screen,
So that I can see during a Lab hour whether something is going wrong.

**Acceptance Criteria:**

**Given** the spine defers the store for per-session error counts
**When** this story is built
**Then** it settles the decision: an `error_events` table owned by `modules/ops`, written only through `ops.service.record_error(source, code, class_session_id, request_id)`, with `source` in a closed enum (`conservation_check`, `job_failed`, `api_error`) and ids only, no names, emails or free text (NFR-8, AD-14)
**And** the decision is recorded in the architecture spine's Deferred list as settled, with the note that the counts do not depend on which external error-tracking tool the founder later chooses (issue #28).

**Given** the three sources
**When** the finished-game check (FR-29) that the sweep action of Story 6.18 runs on every finished Game, played-out games (Story 8.14) and Replays (Story 10.5) included, logs a violation, a procrastinate job fails for good, or the api error handler returns a 5xx
**Then** each calls `record_error` with the Class session id where one is known, and a failure to record never fails the caller (FR-29, NFR-9)
**And** the job-failure hook and the api error handler get `record_error` passed in from `worker.py` and `main.py`, so `platform` still imports no module
**And** this story wires the existing check for Class games, played-out games and Replays to the store, so every violation is counted under its Class session with `source = conservation_check`
**And** a test triggers each source, including a violation in a Class game, a playout and a Replay, and finds one row each.

**Given** the operations view for a Class session
**When** the Admin opens it
**Then** it shows error counts by source and hour, the fallback rate by fallback kind, AI response times (median and 95th percentile) per Effort level, the share of Seats switched by the Play guard, and AI cost, the AI figures read through the `ai` service over `llm_call` and `seat_week` through the AD-15 mapping (NFR-8, FR-79)
**And** each chart has «Vis som tabell».

**Given** a Lab hour is running
**When** the view is open
**Then** it refetches on an AD-8 topic or at a stated interval, shows the time of the last update, and uses the Tilkoblingslinje when stale (UX-DR58).

**Given** the Admin has no Class membership
**When** the view is shown
**Then** it holds counts and timings only, with no Student names, answers or AI assessments (FR-5, AD-12).

**Given** old rows
**When** retention runs for a Class session
**Then** its `error_events` rows are kept, since they hold no personal data, and this is listed in the registry of Story 15.1.

**Covers:** NFR-8, NFR-9, FR-29, FR-79, FR-5, AD-6, AD-12, AD-14, AD-15, UX-DR58

### Story 15.9: The database connection budget is written and checked

As a founder,
I want a written connection budget that the running system is checked against,
So that a full Lab hour or a deploy overlap does not run out of database connections.

**Acceptance Criteria:**

**Given** the Supabase session pooler on port 5432
**When** this story is done
**Then** the connection budget that Story 3.14 recorded in `docs/ops/connection-budget.md` is revised in place, not written a second time: per process (`api`, `worker-ai`, `worker-batch`) the SQLAlchemy pool with `max_overflow=0`, the procrastinate pool and the one LISTEN connection for `api`, the total, and the total times two for a deploy overlap (SETUP-GUIDE §5)
**And** the starting values are `DB_POOL_SIZE` 10, 5 and 5 as stated placeholders, to be tuned under load (issue #28).

**Given** each process starts
**When** it reads its pool settings
**Then** it logs its configured connections, and `api` exposes the sum against the budget on the Admin operations view of Story 15.8
**And** in production a process refuses to start if `DATABASE_URL` points at the transaction pooler on port 6543, because it breaks LISTEN/NOTIFY and procrastinate.

**Given** the pooler's pool size cannot be read over the session pooler
**When** the Admin opens the operations view, or `ops.service.check_connection_budget()` is called
**Then** it compares `DB_POOLER_SIZE`, a configuration value the founder copies from Supabase (Database → Connection pooling), with twice the budget total and reports a failure with the two numbers if the pool is too small
**And** an unset value is reported as not checked, never as passed.

**Given** a deploy with overlap during simulated play
**When** old and new processes run side by side
**Then** no request fails for lack of a connection, shown by a test against Docker Compose that starts a second set of processes while scripted Games are played through `python -m app.sim`.

**Covers:** NFR-3, NFR-4, AD-24

### Story 15.10: A load test shows 250 Students playing at once

As a founder,
I want a repeatable load test of a full Lab hour, including the provider's rate limits,
So that I know the pilot will not degrade before 250 Students are in the room.

**Acceptance Criteria:**

**Given** the spine defers the load test method
**When** this story is built
**Then** it settles the method: a load driver checked into the repository that logs in generated Users and plays through the public HTTP API and the SSE stream, as a browser would, with no shortcut into `games.commands`; the tool chosen and the reason are recorded in the spine's Deferred list as settled (NFR-3)
**And** the generated Users come from a seed command this story adds, `python -m app.ops.loadtest seed`: it creates Users with `is_test_student`, their Classes and course Class sessions directly through `identity`, `classes` and `sessions` `service.py`, with no Invitation mail and with generated passwords handed to the driver, and it refuses to run for any Institution without the operator flag of Story 12.7 (AD-13, AD-27)
**And** because the Users are test Students, the data never reaches a report, statistic or export.

**Given** the scenario
**When** the test runs
**Then** 250 simulated Students in Class games of four play at the same time, with AI players in the remainder Seats, and a second run holds 5 such Class sessions at once with a spread of activity (NFR-3)
**And** a Class session of 400 Students (100 Class games) is created, allocated and locked as part of the setup.

**Given** the provider's rate limits must be included
**When** the test runs
**Then** one run uses the mock provider set to the confirmed rate limit of the pinned endpoint, answering HTTP 429 above it, and one run before the pilot uses the real pinned endpoint with cost charged to that test Class session's budget (NFR-3, AD-6)
**And** the rate limit value is `AI_RATE_LIMIT_RPM` or the model config's, a stated placeholder until the provider confirms it in writing (issues #8, #9).

**Given** the pass lines
**When** the run ends
**Then** the report states, against limits written down before the run: the time from the last Order to the new Week on the SSE stream (2 seconds, excluding AI thinking time), play page load (3 seconds, measured by a Playwright run on a throttled 4G profile against the play page while the load is on, since the HTTP driver loads no page), the share of AI Orders replaced by fallback because of rate limits or timeouts, error counts from Story 15.8, database connections against the budget of Story 15.9, a deploy with overlap during the run, and worker queue delay (NFR-1, NFR-2, NFR-3)
**And** "no mass fallback" is a configured threshold with a stated placeholder, not an invented final number.

**Given** a run
**When** it finishes
**Then** a dated load test report is committed to the repository with the commit, the settings (`WORKER_CONCURRENCY`, `DB_POOL_SIZE`, replicas), the measured values and pass or fail per line
**And** a failed line names the setting to change, and the test is rerun until every line passes or the founder records an accepted deviation.

**Given** the test data
**When** the run is over
**Then** the generated Users are anonymised and their free text deleted by the shared deletion routine of Story 15.2; their Class sessions, Games and Seats remain as anonymous test data in the operator-owned Institution, and the load test report says so
**And** a check confirms that `reports.scope` returned none of them at any time.

**Covers:** NFR-1, NFR-2, NFR-3, NFR-4, AD-6, AD-8, AD-13, AD-27

### Story 15.11: Errors reach an error tracker without personal data, and backup and monitoring are laid out for decision

As a founder,
I want errors sent to an error tracker without personal data, a restore I can verify, and the open operations decisions laid out in one record,
So that game state is not lost and a failure in a Lab hour reaches a named person.

**Acceptance Criteria:**

**Given** the error-tracking tool is a founder decision (issue #28)
**When** this story is built
**Then** it does not choose the tool: it adds one error-reporting adapter in `api/app/platform/` behind one interface, configured by a DSN in the environment, with a recording mock when the DSN is missing and `APP_ENV` is local, test or ci (AD-17)
**And** the story is done when the adapter and its tests pass on the mock; choosing and connecting the real tool is an item in the readiness record, not a condition for finishing this story.

**Given** an error is raised while personal data is in scope
**When** the adapter reports it
**Then** no name, email or free text leaves the process: the adapter sends ids, the error type and the stack only, checked by a test that raises an error with a name, an email and an Explanation in local variables and in the request body (AD-14)
**And** the same error is counted as a row in `error_events` through `ops.service.record_error` (Story 15.8), so the per-session counts do not depend on the tool (NFR-8).

**Given** the backup level is a founder decision (issue #28)
**When** this story is built
**Then** it adds the command `python -m app.ops.verify_restore <database_url>`, which reads a restored copy of the database, replays a finished Game through the engine at its stored `rules_version` and reports whether the stored Week states verify (NFR-4, AD-4)
**And** the command changes no data and is tested in CI against a copy of the test database.

**Given** the founder decisions and manual checks that no code can make
**When** this story creates the readiness record in the repository
**Then** it lists these items, each open with its issue number until the founder records it with a date: the backup level, with the options the Supabase plan offers and what each means for NFR-4 ("game state is never lost once a Week has been shown"); the error-tracking tool and the uptime-monitoring tool, each with its region and the data it receives; one restore into a separate database checked with `verify_restore`; a deliberate error in production seen in the tracker and in `error_events`; and a stopped `api` health check that raises an uptime alert and reaches the named contact (NFR-4)
**And** the story decides none of them; when the founder decides, the decision is also noted against the spine's Deferred list and issue #28.

**Given** the DPIA pack needs a sub-processor register
**When** this story is done
**Then** the register is started in the repository with Railway, Supabase, Resend, the LLM provider and the DNS provider, each with the data it receives, its region and its transfer basis, and with open rows for the error tracker and the uptime tool (PRD §6.1).

**Given** NFR-4 asks for a named contact during Lab hours and 99.5% availability
**When** the readiness record is created
**Then** it has items for the contact, the response route, how availability during Lab hours is measured from the uptime tool, and naming the contact in the Lecturer material of Story 2.13; they are the founder's to fill in.

**Covers:** NFR-4, NFR-8, AD-4, AD-14, AD-17

### Story 15.12: Hold Student Invitations until the Institution's data processing agreement is recorded

As an Admin,
I want to record an Institution's data processing agreement and have Student Invitations held until it exists,
So that no Student is invited before the Institution and the operator have an agreement.

**Acceptance Criteria:**

**Given** an Institution in the Admin-område (Story 3.11)
**When** the Admin records its data processing agreement
**Then** who signed and when are stored on the Institution through `identity.service`, the action is an audited Admin action allowed by a `platform/authz` policy, and `identity.service.has_processing_agreement(institution_id)` returns true (AD-12).

**Given** `REQUIRE_DPA_FOR_INVITATIONS` is on
**When** a Lecturer sends Invitations to Students of a Class in an Institution without a recorded agreement
**Then** `classes` asks `identity.service.has_processing_agreement` before the send of Story 4.4, refuses with a stable error code, and the Lecturer sees a message that the Institution's agreement is missing, as draft copy in `web/src/copy/nb.ts` (FR-8, PRD §6.1)
**And** nothing is sent and no Roster row changes state.

**Given** `REQUIRE_DPA_FOR_INVITATIONS` is off
**When** the same send is made
**Then** the Invitations go out and the missing agreement is only logged, with ids only
**And** Invitations to Lecturers and Admins (Story 3.7) are never held by this check, and api tests cover both settings
**And** the check always passes for the operator-owned Institution, read through `identity.service` from Story 12.7, because the operator is the data controller for test students there (FR-82); an api test invites a test student with the setting on.

**Given** the spine defers whether Invitations to Students are refused for an Institution with no recorded data processing agreement
**When** this story is done
**Then** the founder's decision is recorded with date in the spine's Deferred list as settled, and the configuration value is set to that decision; the story does not decide it.

**Covers:** FR-8, FR-82, AD-12

### Story 15.13: Publish the accessibility statement and the conformance report

As a founder,
I want an accessibility statement in the product and a conformance report I can give to Institutions,
So that NFR-6 is met with evidence.

**Acceptance Criteria:**

**Given** NFR-6 asks for an accessibility statement
**When** this story is done
**Then** the statement is published in the product, linked from the Landing (Story 3.13) and from the footer, in Norwegian bokmål from `web/src/copy/nb.ts`, with the contact route and the known deviations (NFR-6).

**Given** the CI runs of Playwright with axe at 320, 360 and 1440 px and 400% zoom, and the veraPDF result
**When** the founder runs the report command this story adds
**Then** it generates the conformance report, listing each surface with pass or the violations found, and the dated report is committed and named in the readiness record of Story 15.11.

**Given** checks that tools cannot make (screen reader, keyboard only)
**When** the report is generated
**Then** it lists them as the founder's, each with who did it and when, and shows them as open until they are filled in.

**Given** the statement page
**When** Playwright with axe runs at 320 and 1440 px and with 200% text
**Then** it reflows without horizontal scroll and axe reports no violations (NFR-6).

**Covers:** NFR-6

### Story 15.14: The pre-pilot checks pass before the first Class session

As a founder,
I want one command and one record that show every pre-pilot check,
So that I can decide go or no-go on facts and not on memory.

**Acceptance Criteria:**

**Given** SETUP-GUIDE section 7
**When** the founder runs `python -m app.ops.preflight` against production
**Then** it prints pass or fail per check it can test itself: required secrets present and not defaults, `APP_ENV=production`, the database reached through the session pooler on port 5432 with TLS, `DB_POOLER_SIZE` against the connection budget (Story 15.9), the private `reports` bucket and a signed URL that expires, the pinned model config of the pilot Class session with a provider key (Story 15.5), the Resend domain verified with sending region eu-west-1, read from the provider, and the `FEATURE_*` flags as set (AD-17, NFR-7, NFR-10)
**And** the command changes no data, sends no mail and prints no secret values.

**Given** the startup guard
**When** one required secret is removed in a production-mode start
**Then** the api and the workers refuse to start, shown by a test and confirmed once on Railway (AD-17).

**Given** the checks a command cannot make
**When** the readiness record started in Story 15.11 is completed
**Then** it lists, each with who confirmed it and when: new values for every secret, the pseudonym key held by someone other than the founder, Supabase on a paid plan in eu-central-1 with the database and Storage encrypted at rest (NFR-7), Railway services pinned to EU West, the provider's terms and rate limit confirmed in writing, the sub-processor register for the DPIA pack, the data processing agreement gate (Story 15.12), the backup and monitoring decisions (Story 15.11), the load test report (Story 15.10), the conformance report (Story 15.13), CI gating and who promotes `main` to `production`, and the rehearsal Class session and Control test run in production
**And** a test bounce in the rehearsal Class session, which reaches `/api/webhooks/resend` and shows as bounced for the Lecturer, is one of these manual items, because the preflight command changes no data (NFR-10)
**And** the open question of the email provider's data residency (issue #29) is listed as decided or open
**And** items that are not code are marked as the founder's, not as done by the story.

**Given** an item is open or failed
**When** the record is read
**Then** it shows as open with its issue number, and the record states no-go until every item is passed or carries an accepted deviation signed by the founder.

**Given** CI
**When** the pipeline runs
**Then** the preflight command runs against Docker Compose in its local mode and its checks are unit-tested, so the command itself cannot rot before the pilot.

**Covers:** NFR-3, NFR-4, NFR-7, NFR-10, AD-14, AD-17, AD-24
