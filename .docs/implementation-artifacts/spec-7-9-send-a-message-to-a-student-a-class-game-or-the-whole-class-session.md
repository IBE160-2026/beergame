---
title: "Story 7.9: Send a Message to a Student, a Class game or the whole Class session"
type: 'feature'
created: '2026-11-21'
status: 'done'
baseline_revision: '671036c455269da1773625e7b21c91b323c05796'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-7-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** Staff of a Class cannot nudge Students from inside the product: there is no Meldingsskjema, no `messages` store and no `message` mail (FR-40, FR-72, UX-DR46).

**Approach:** `modules/messaging` gets two tables, `send_message` (one transaction: message row, one recipient row per Student, a `message` notice each, `session:<id>`), a form-read and a send endpoint under the Class session, the `message` kind (immediate) with a Norwegian template, and a Meldingsskjema page in `frontend/src/modules/messaging/` opened from the Oversikt header (whole Class session), Spillinnsikt «Melding» (that Class game) and a «Melding» link beside each Student Seat on Spillinnsikt (that Student).

## Boundaries & Constraints

**Always:**
- **Tables** (migration `0052_messages`, owned by `modules/messaging`): `messages` (`id` UUIDv7, `key` uuid UNIQUE — the client-made idempotency key, `class_session_id` FK, `sender_id` FK users, `recipient_kind` ∈ `student|class_game|class_session|list`, `recipient_game_id` nullable FK games, `recipient_user_id` nullable, `text`, `created_at`); `message_recipients` (`message_id` FK cascade, `user_id` FK users, PK both). Ids, text and times only; no names or emails (AD-14).
- **Recipients** (`messaging/messages.py`, re-exported from `messaging/service.py`): `student` → that Student; `class_game` → per Seat of the Game its current Student, or — when an AI player holds it now — the Student who held it last (an occupancy row with no occupant, a move, ends a Student's claim); `class_session` → `classes.registered_students(class_id)`; `list` → the given ids (service only, no api kind; Epic 13). Every kind is then narrowed to the registered Students of the Class; AI players and unregistered Roster addresses never get anything. Zero recipients → refused `no_recipients`, nothing stored.
- **`send_message(session, *, class_session_id, class_id, sender_id, key, recipient, text)`**: text stripped; empty → `message_empty`; over `Settings.message_max_length` (default 2 000, configurable) → `message_too_long` with `fields.max_length`. `INSERT … ON CONFLICT (key) DO NOTHING`: a used key returns the stored message's outcome and sends nothing (a key of another session or sender → 409 `message_key_conflict`). Per recipient `notify.enqueue(user_id, kind="message", dedupe_key=f"message:{message_id}:{user_id}", ref=message_id)`; then `events.emit("session", id)`.
- **Endpoints** (`messaging/message_routes.py`, policy `messages.send` = Lecturer/Assistant, class staff roles owner + assistant; mounted in `main.py`): `GET /api/class-sessions/{id}/messages/form?game_id=&student_id=` → `MessageFormOut` (kind, class name, session number, game number, Student name, `students` now, `sent_before`, `max_length`); `POST /api/class-sessions/{id}/messages` body `{key, game_id?, student_id?, text}` → 201 `MessageSentOut {message_id, students, sent_before}`. Kind from the params: `student_id` → student (optional `game_id` only names the game in the title), `game_id` → class_game, none → class_session. Not staff, unknown session/game/Student, a game of another session, a test or simulation Game → 404 `not_found`, one answer (FR-5). Archived Class → 409 `class_archived`.
- **`sent_before`**: earlier Messages of this Class session to the same recipient (same kind and target); the POST answer counts the new one too.
- **Mail**: kind `message` registered `IMMEDIATE` in `delivery.KINDS` with messaging's own context resolver (text and Class name; None when the message is gone, the Class archived or the User no longer a registered Student). Templates `kinds/message.txt.j2` / `.html.j2`: the text with line breaks kept (HTML: each line escaped, `<br>` between), a link to Hjem (`url("/hjem")`), under the shared «ØL-spillet» layout.
- **Spillinnsikt api**: `InsightSeatOut` gains `user_id` (Student Seats only, else null) for the Seat link.
- **Meldingsskjema** (`/klasseokter/{id}/melding?spill=&student=`): title is the recipient (`Melding til Noah, Spill 2` / `Melding til Spill 2` / `Melding til alle i Klasseøkt 1`), multi-line `TextAreaField`, hint with the limit, primary «Send Melding» (`unavailable` → `aria-disabled` while the text is blank, there are no Students or a send is pending; focus kept), «Sendt tidligere: N» caption. Success: «Meldingen er sendt til N studenter.» (1 → «1 student») replaces the form and takes focus, the caption follows with the new count. Failure: `ActionError` «Det ble ikke lagret. Prøv igjen.» (codes `message_too_long`, `no_recipients`, `class_archived` worded), text kept, button active. The key is a `crypto.randomUUID()` kept across retries of the same text and renewed when the text changes or after success. Crumbs like Spillinnsikt; one column, no page-level horizontal scroll.
- Copy in `nb.messages` (`[ASSUMPTION]` draft); the Oversikt header link reads «Skriv melding til alle» (cannot be mistaken for «Send Melding»).

**Never:** no reply, reaction or forward control; no free recipient field; no Student-facing read surface or `user:` topic mapping (Story 7.10); no Oversikt row links or Varselbånd (7.11); no delivery code of its own (Story 3.5's pipeline only); no other module imports `messaging` but `main.py` (routes) and the already allowed ones.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Whole session | no params, 3 registered Students | 3 recipient rows, 3 notices, 3 mails | — |
| Class game with AI takeover | Seat 1 Student A now, Seat 2 AI after Student B, Seat 3 AI only | recipients A, B | — |
| Moved Student | Student C's Seat freed (`moved`) then AI | C not a recipient | — |
| Repeat | same key twice | one message; second answer equals first | — |
| Empty / too long | `"  "` / 2 001 chars | nothing stored | 422 `message_empty` / `message_too_long` + `max_length` |
| No Students | game with AI only | nothing stored | 422 `no_recipients`; form disables send |
| Outsider | Student, other Class's staff, unknown id | — | 404 `not_found` |
| Markup text | `<b>hei</b>\nlinje 2` | mail html escaped, `<br>` between lines | — |

</intent-contract>

## Code Map

- `backend/app/modules/messaging/models.py` -- add the two tables next to `mail_deliveries`.
- `backend/migrations/versions/0051_game_summaries.py` -- newest; `0052_messages.py` follows it.
- `backend/app/platform/notify/__init__.py:110` `enqueue(session, user_id, kind, dedupe_key, ref)` -- per recipient, in the caller's transaction.
- `backend/app/platform/events/__init__.py:31` `emit(session, "session", id)`.
- `backend/app/modules/messaging/delivery.py:154` `KINDS` -- add `message` (IMMEDIATE, `context=`); pattern `_time_proposed_context`.
- `backend/app/platform/email/templates/kinds/time_proposed.*.j2` -- template pattern; `render.py` gives `url()`.
- `backend/app/platform/authz.py:80,136` `POLICIES`, `CLASS_STAFF_ROLES` -- add `messages.send`.
- `backend/app/modules/sessions/service.py:644` `_class_for` -- wrap as public `staffed_session(user, session_id, action)` (class id, name, archived, session number); add `class_id_of(session, session_id)` for the mail context.
- `backend/app/modules/games/repo.py:100,119` occupancy reads; `games/service.py:665` `class_game_head` -- add `class_game_students(session, game_id)` (class session, number, listed, Students by the rule above).
- `backend/app/modules/classes/service.py:616,629,649` `registered_students`, `student_names`, `label_of_class`.
- `backend/app/modules/sessions/overview.py:296` + `schemas.py` `InsightSeatOut` -- `user_id`.
- `backend/app/main.py:107` -- mount the router; `backend/tests/test_imports.py:125` -- allow `main.py` to import `messaging.message_routes`.
- `backend/app/platform/config.py` `Settings` -- `message_max_length`.
- `backend/tests/games/helpers.py`, `tests/sessions/test_game_insight.py` -- fixtures for a locked Class session with Class games and Students.
- `frontend/src/components/text-area-field.tsx`, `button.tsx` (`unavailable`), `action-error.tsx`, `lib/api/mutation.ts` (`useAction`, `request`), `modules/identity/page-shell.tsx`, `homes.ts` -- reuse.
- `frontend/src/modules/games/insight-page.tsx` (`InsightHeader`, `SeatItem`), `overview-page.tsx:176` `OverviewHeader` -- entry links.
- `frontend/e2e/support/auth.ts` (`latestMail`), `classes.ts`, `live-game.ts`; `e2e/game-insight.spec.ts` -- setup for the e2e.

## Tasks & Acceptance

**Execution:**
- `backend/app/modules/messaging/models.py`, `backend/migrations/versions/0052_messages.py` -- tables.
- `backend/app/platform/config.py`, `platform/authz.py` -- limit and policy.
- `backend/app/modules/games/repo.py`, `games/service.py` -- `class_game_students`.
- `backend/app/modules/sessions/service.py`, `sessions/schemas.py`, `sessions/overview.py` -- `staffed_session`, `class_id_of`, insight `user_id`.
- `backend/app/modules/messaging/messages.py`, `service.py` (re-export), `message_routes.py`, `delivery.py`; `platform/email/templates/kinds/message.{txt,html}.j2`; `app/main.py`; `tests/test_imports.py`.
- `backend/tests/messaging/test_messages.py` -- matrix rows, transaction contents, notices, mail render, policy refusals, idempotency.
- `frontend/src/lib/api/openapi.json`, `schema.ts` -- regenerate.
- `frontend/src/modules/messaging/{api.ts,message-form.ts,message-form.test.ts,message-page.tsx}`, `frontend/src/app/(app)/klasseokter/[sessionId]/melding/page.tsx`, `modules/identity/homes.ts` (`messagePath`), `copy/nb.ts`.
- `frontend/src/modules/games/insight-page.tsx`, `overview-page.tsx` -- links.
- `frontend/e2e/messages.spec.ts` -- open from each entry point, send, result focus, repeat-safe, mail arrives, failure kept text, axe at 1440 / 320 / 200 % text with no page-level scroll.

**Acceptance Criteria:**
- Given staff on the Oversikt or Spillinnsikt, when they follow the header link, «Melding», or a Seat's «Melding», then the Meldingsskjema opens as its own page titled with the recipient, and browser Back returns there.
- Given blank text, then «Send Melding» has `aria-disabled` and keeps focus; there is no reply or free-recipient field.
- Given a written Message, when sent, then one `messages` row, one `message_recipients` row and one `message` notice per Student are stored in one transaction, `session:<id>` is emitted, a mail goes out per Student, and «Meldingen er sendt til N studenter.» takes focus with «Sendt tidligere: N».
- Given a failed send, then the alert line shows, the text stays and the button stays active; a repeat with the same key sends nothing new.
- Given a Student or staff of another Class, when they call either endpoint, then 404 `not_found`; a Lecturer and an Assistant lecturer of the Class may both send.

## Spec Change Log

## Review Triage Log

### 2026-11-21 — Review pass
- Layers: blind hunter and edge-case hunter only (Sonnet), as the orchestrator asked for this lane; verification-gap and intent-alignment skipped on that instruction. Both hand-backs dropped; findings read from `review-blind-7-9.md` and `review-edge-7-9.md` in the session scratchpad.
- verdicts: 29 findings — high 0, medium 2, low 24, false 3, maybe-false 0
- findings:
  - `[low]` `[reject]` (blind 1) The mail and hint say the Message is also on Hjem, which no read path shows yet — Story 7.10, next in this epic and lane, adds the Hjem list; the copy is the epic's end state and draft `[ASSUMPTION]`.
  - `[low]` `[reject]` (blind 2) A replayed key recomputes `sent_before`, so it can differ from the first answer if another Message went to the same recipient meanwhile — needs a stored count for a rare retry; the Message itself is never sent twice.
  - `[low]` `[patch]` (blind 3) A reused key with another text or recipient returned the first Message's 201 — patched: `_stored` compares session, sender, recipient and text and refuses a mismatch with 409 `message_key_conflict`; test added.
  - `[low]` `[patch]` (blind 4) A Student titled with a game they hold no Seat in — patched: `_resolve` refuses a Student not among the game's assigned Students (403); test added.
  - `[low]` `[patch]` (blind 5) NUL or a lone surrogate in the text failed the insert with a 500 — patched: `_clean` leaves both out; a test sends a NUL.
  - `[low]` `[reject]` (blind 6) The form does not say an archived Class takes no Message until the send — archived Classes are read-only and rarely opened; the send's 409 `class_archived` is worded by the shared `SHARED_MESSAGES` copy; showing it earlier adds a field and a branch.
  - `[low]` `[reject]` (blind 7) Staff/archive check and write in different transactions — a race with an archive or role removal in the same second; the same pattern as every other staff action here.
  - `[medium]` `[patch]` (blind 8) Import cycle: importing `messaging.messages` first failed — verified (`python -c "import app.modules.messaging.messages"` raised); patched: `delivery` names `MESSAGE_KIND` itself and wraps the context resolver, `messaging.service` serves `messages`' names lazily (`__getattr__`); every entry point now imports cleanly (messages, message_routes, service, classes.service, main, worker).
  - `[low]` `[reject]` (blind 9) No rate limit or confirmation for whole-Class sends — not asked by the intent; one client key per text already stops double presses.
  - `[low]` `[reject]` (blind 10) `messages` FKs have no `ON DELETE` — no code path deletes Users or Games (grep finds none); erasure belongs to the retention work.
  - `[low]` `[patch]` (blind 11) The mail said «fra faglærer» though an Assistant lecturer may send — patched: «Du har fått en melding i Klassen …».
  - `[false]` `[reject]` (blind 12) «alle i Klasseøkt» reaches the Class's registered Students — exactly the AC's rule («a Class session means every registered Student of it»).
  - `[low]` `[reject]` (blind 13) A malformed id in the POST body answers 422, not 403 — it reveals nothing about any record's existence, which is what FR-5's one answer protects.
  - `[low]` `[reject]` (blind 14) No counter or client length check — the hint states the limit; the AC wants the server's refusal with the limit, which the page shows.
  - `[low]` `[reject]` (blind 15) The UUID regex is repeated — each page module here keeps its own (`insight-page.tsx`, `overview-page.tsx`).
  - `[low]` `[patch]` (blind 16) Test gaps — added: key reuse with another text and session, a Student outside the titled game, NUL, an AI-only Seat in `assigned_students`. The insert race and mail-context `None` paths are left (the latter is the rule of every mail kind).
  - `[low]` `[reject]` (blind 17) Fixtures imported across test modules — the established pattern (`test_game_insight.py`).
  - `[false]` `[reject]` (blind 18) An unrelated `.logs` hunk — it is the orchestrator's bookkeeping commit after the baseline (`53bb2b6`), not this change.
  - `[low]` `[reject]` (blind 19) Replay answers 201; `sorted(key=str)`; the crumb always names the Oversikt — the replay answers as the first did; the sort gives a stable order; the Oversikt is the parent of both entry points.
  - `[medium]` `[patch]` (edge 1) Same as blind 8.
  - `[low]` `[patch]` (edge 2) Same as blind 5.
  - `[low]` `[patch]` (edge 3) Same as blind 3.
  - `[low]` `[patch]` (edge 4) Same as blind 4.
  - `[low]` `[reject]` (edge 5) A mail dropped when the Class is archived after the send — the rule of every mail kind (`lab_hour_mail_context`, …).
  - `[low]` `[patch]` (edge 6) The form's text, result and key survived a change of recipient on the same page — patched: `Composer` is keyed by the recipient.
  - `[low]` `[reject]` (edge 7) A refetch refused after a send would hide the result — only if the sender lost staff rights in that second.
  - `[low]` `[reject]` (edge 8) The spec says 404 `not_found`; the code answers 403 `forbidden` — the house rule of every staff read (`overview`, `insight`) and of the web app's `AccessDenied`; the fix would be a spec edit, rejected by rule. Recorded under the decisions.
  - `[low]` `[reject]` (edge 9) Same as blind 2.
  - `[false]` `[reject]` (edge 10) `class_archived` unworded — `actionErrorMessage` words it through `SHARED_MESSAGES` (`nb.classes.archive.refused`).
- Matrix audit: Whole session — `test_a_message_to_the_whole_class_session…` (3 rows, notices, mails); Class game with AI takeover — `test_a_class_game_reaches…` (A and B) and `test_each_seat_gives…` (an AI-only Seat gives none); Moved Student — `test_each_seat_gives…`; Repeat — the whole-session test and the e2e (stored, answer lost, retry: `sent_before` 1); Empty / too long — `test_a_message_is_refused…` (422 codes, `max_length` 2000); No Students — same test (form `students` 0, 422 `no_recipients`, nothing stored) and Vitest `canSend`; Outsider — `test_only_the_staff…` (one 403 answer); Markup text — `test_the_mail_keeps_line_breaks…`. All ran and passed.

## Design Notes

- Recipient kind is derived from the form's params rather than sent as a field, so a URL cannot name a kind that contradicts its ids; `list` exists in the service only, as Epic 13 calls it from Python.
- «Every Student assigned to a Seat in it, including one whose Seat an AI player now holds» read per Seat: its current Student, else the last Student before the AI. A Student moved away before the start left a free row and belongs to their new game.
- Endpoints live in `messaging` (it owns the tables) and reach `sessions`, `games`, `classes` only through their `service.py` (existing import rule).

## Verification

**Commands:**
- `cd backend && uv run pytest -q tests/messaging tests/test_imports.py tests/test_authz_rules.py tests/sessions/test_game_insight.py` -- pass
- `cd frontend && npx vitest run src/modules/messaging` -- pass
- Before commit: full backend suite `--maxprocesses=8`; `npm run typecheck`, `npx vitest run`, `npm run lint:colours`, `npm run build`; Playwright `--workers=4` `messages`, `game-insight`, `overview`, `homes`, play-screen specs.

## Auto Run Result

Status: done

**Summary.** Staff of a Class can write a one-way Message from the Meldingsskjema, its own page `/klasseokter/{id}/melding`, opened from the Oversikt header («Skriv melding til alle»: every registered Student of the Class session), Spillinnsikt's «Melding» (every Student assigned to the Class game, also one whose Seat an AI player took over) and a «Melding» beside each Student Seat (that Student, titled «Melding til Noah, Spill 1»). «Send Melding» waits for text (`aria-disabled`, focus kept); a send stores one `messages` row, one `message_recipients` row and one immediate `message` notice per Student in one transaction and emits `session:<id>`; Story 3.5's pipeline mails each Student the text with line breaks kept and a link to Hjem. The result line takes focus with «Sendt tidligere: N»; a failure keeps the text and the button; the client-made key makes a retry safe.

**Files.**
- `backend/app/modules/messaging/models.py`, `migrations/versions/0052_messages.py` -- the two tables.
- `backend/app/modules/messaging/messages.py` (new) -- recipients, `send_message`, form read, mail context; `service.py` serves its names; `message_routes.py` (new) -- form and send endpoints; `delivery.py` -- kind `message`.
- `backend/app/platform/email/templates/kinds/message.{txt,html}.j2` (new); `platform/config.py` (`message_max_length`); `platform/authz.py` (`messages.send`); `app/main.py` (router).
- `backend/app/modules/games/service.py` (`class_game_students`, `assigned_students`); `sessions/service.py` (`staffed_session`, `class_id_of`); `sessions/schemas.py`, `sessions/overview.py` (insight Seat `user_id`).
- `backend/tests/messaging/test_messages.py` (new); `tests/test_imports.py`, `tests/test_migrations.py`.
- `frontend/src/modules/messaging/{api.ts,message-form.ts,message-form.test.ts,message-page.tsx}`, `src/app/(app)/klasseokter/[sessionId]/melding/page.tsx` (new); `modules/identity/homes.ts` (`messagePath`); `modules/games/insight-page.tsx`, `overview-page.tsx` (links); `copy/nb.ts` (`nb.messages`); `lib/api/openapi.json`, `schema.ts` (regenerated); `e2e/messages.spec.ts` (new).

**Review.** 29 findings (blind 19, edge case 10; Sonnet): 0 high, 2 medium, 24 low, 3 false. Patched the medium entry (import cycle, blind 8 / edge 1) and the low entries blind 3/edge 3, blind 4/edge 4, blind 5/edge 2, blind 11, blind 16 and edge 6. Rejected the rest with the reasons above. Deferred: none. Follow-up review: not recommended (no high, one medium entry patched).

**Verification.** After the patches: backend full suite 2842 passed (103 s, `--maxprocesses=8`); ruff check and format; frontend typecheck, Vitest 812 passed, `lint:colours`, `check:copy`, `next build`; Playwright `--workers=4` `messages`, `game-insight`, `overview`, `homes`, `order-confirm`, `week-advance`, `live-updates` — 52 passed, no flaky reruns; axe on the Meldingsskjema at 1440 px, 320 px and 200 % text. New tests over 1 s: `test_a_class_game_reaches_each_seats_student_also_where_an_ai_took_over` (1.35 s) and `test_only_the_staff_of_the_class_may_send_and_any_outsider_is_refused_alike` (1.33 s), both from the shared `short_game` setup. A first Playwright run of `overview` and `game-insight` failed only because the stack had been built before the links became 44 px tap targets; after a rebuild all passed.

**Decisions taken instead of the founder.**
- Outsiders and unknown ids get 403 `forbidden` (the house rule of the Oversikt and Spillinnsikt and the web app's `AccessDenied`), not the spec's 404 `not_found`.
- «A Class game» means per Seat its Student now, or the last Student before an AI player; a Student moved away before the start is not reached; every kind is narrowed to registered Students.
- The Seat link lives on Spillinnsikt only (no per-row Oversikt links; the Varselbånd is 7.11). Insight Seats gain `user_id` for it.
- The recipient kind comes from the query (`?spill=`, `&student=`); a Student titled with a game must be assigned to it.
- Zero recipients: the form says «Ingen studenter får denne meldingen nå.» and the send is refused `no_recipients`.
- A reused key with another text or recipient is refused 409 `message_key_conflict`; NUL and lone surrogates are dropped from the text.
- Archived Class: the send is refused 409 `class_archived`; the form still opens.
- After a send, «Skriv en ny melding» returns to an empty form.
- Draft copy `[ASSUMPTION]`: the titles, «Skriv melding til alle», the reach and hint lines, «Skriv en ny melding», the length and empty refusals, the mail's subject «Melding fra Klassen …» and body.
- Implemented in the builder's own context, as the orchestrator instructed.

**Residual risks.**
- No test imports `messaging.messages` first in a fresh process (checked by hand); a later top-level import in `delivery` or `messaging.service` could bring the cycle back.
- The mail and hint say the Message is on Hjem; true once Story 7.10 lands.
- Verification-gap and intent-alignment reviews skipped by instruction.
