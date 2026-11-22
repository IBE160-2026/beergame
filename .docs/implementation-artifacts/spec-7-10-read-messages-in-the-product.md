---
title: "Story 7.10: Read Messages in the product"
type: 'feature'
created: '2026-11-21'
status: 'done'
baseline_revision: '56c8d6d2e4d6bfd9dd2da1c39340188e278d1077'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-7-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** Story 7.9 sends Messages by mail only: a Student cannot read them on Hjem, and staff cannot see what was sent in a Class session (FR-40, FR-73, UX-DR46).

**Approach:** `modules/messaging` gets two reads — a Student's own Messages through a new `authz` scope helper, and the staff's list of a Class session's sent Messages — and the web app gets a «Meldinger» section on the Student Hjem (live on `user:<id>`) and a staff page `/klasseokter/{id}/meldinger` (live on `session:<id>`) opened from the Oversikt header and the Meldingsskjema.

## Boundaries & Constraints

**Always:**
- **Scope helper** `authz.messages_addressed_to(user)`: the ids of Messages with a `message_recipients` row for the User whose Class session belongs to a Class in `classes_enrolled_by(user)` (tables by name only, as the other helpers). Every Student read joins through it; a Student removed from the Roster no longer reads that Class's Messages.
- **`GET /api/me/messages`** (policy `messages.read_own` = `ANY_USER`) → `MyMessagesOut {items}`, each `{id, class_id, class_name, sender_name, sent_at, text}`, newest first (`created_at`, then id), at most 100 (`MY_MESSAGES_LIMIT`). Names are read at request time (AD-14): sender via `identity.service.people` (null when gone or nameless), Class name via the Student's enrolled Classes. Fixed number of queries, independent of the item count.
- **`GET /api/class-sessions/{id}/messages`** (policy `messages.read_sent` = Lecturer/Assistant; class staff roles owner + assistant) → `SentMessagesOut {class_id, class_name, session_number, items}`, each `{id, kind, game_id, game_number, student_id, student_name, sender_name, sent_at, students, text}`, newest first, at most 200. `kind` ∈ `student|class_game|class_session|list`; `student_name` only when the Student is still a registered Student of the Class (else null); `game_number` from `games.class_game_ids`; `students` = recipient rows. Anyone else, an unknown or malformed id → 403 `forbidden`, one answer (the 7.9 house rule). Fixed query count.
- No Student write route: the route set under `/api/me/messages` is GET only; a test walks the app's routes and asserts no non-GET route other than the 7.9 staff send matches `messages`.
- **Hjem «Meldinger»** (`frontend/src/modules/messaging/my-messages.tsx`, rendered by `StudentHjem` after the Class list): heading «Meldinger» (h2, `text-headline`), an `<ol>` newest first; each item: sender (`font-semibold`), the time as `osloDateText` (Europe/Oslo), the Class name only when the Student is in more than one Class, then the full text in `whitespace-pre-wrap [overflow-wrap:anywhere]` (React escapes; nothing is linkified). No read state, no reply, reaction or forward control. With no Messages the section is not drawn. Loading: a small `Skeleton`; failure: inline page-error line with «Prøv igjen», not blocking the rest of Hjem.
- **Live**: `topics.ts` maps `user` also to `myMessagesKey` and `session` also to `sentMessagesKey(id)`. A polite live region, always mounted and visually hidden, says «Ny melding fra Bård.» (or «Nye meldinger: 2.») when ids arrive that were not in the previous answer, never on first load; focus never moves; items are keyed by id.
- **Staff page** `/klasseokter/{id}/meldinger` (`sent-messages-page.tsx`): `PageShell` titled «Meldinger», crumbs like the Meldingsskjema ending «Meldinger», a line «Klasseøkt N · Class», the Lenke «Skriv melding til alle». Each item: recipient line («Til Noah, Spill 2» / «Til Spill 2» / «Til alle i Klasseøkt 1» / «Til 12 studenter» for `list` / «Til en tidligere student»), meta caption «Fra Bård · to. 26. nov. kl. 14:15 · Sendt til 4 studenter», the text, and a Lenke «Skriv ny melding» with accessible name «Skriv ny melding til …» to `messagePath` with the same recipient (none for `list` or a former Student). Empty: «Ingen meldinger er sendt i denne Klasseøkten ennå.» Non-staff see `AccessDenied`.
- **Entry points**: Oversikt header Lenke «Meldinger» beside «Skriv melding til alle»; on the Meldingsskjema a Lenke «Se sendte meldinger» under «Sendt tidligere: N».
- Copy in `nb.messages` (draft `[ASSUMPTION]`), sizes ≥ 13 px, one column, no page-level horizontal scroll at 320 px.
- A backend test imports `app.modules.messaging.messages` first in a fresh interpreter (subprocess).

**Never:** no read/unread state or badge; no reply, reaction, forward or Student write route; no Varselbånd or Oversikt row links (7.11); no names or addresses copied into tables; no new mail kind.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Own Messages | Student A got a session Message then a Student Message | both, newest first, sender name, text | — |
| Others' Messages | Student B got a Message A did not | A's list never contains it | — |
| Removed Student | A removed from the Roster | A's list empty | — |
| Two Classes | A in Classes X and Y | each item names its Class | — |
| Markup text | `<b>hei</b>\nhttps://x.no` | shown literally, line break kept, no link | — |
| Staff list | 3 kinds sent | 3 items newest first with recipient, sender, time, count | — |
| Former Student | Student Message, then Student removed | `student_name` null, no link | — |
| Outsider | Student or other Class's staff on staff list | — | 403 `forbidden` |

</intent-contract>

## Code Map

- `backend/app/modules/messaging/messages.py` -- 7.9 send; add `my_messages(user)` and `sent_messages(user, session_id)`; `RecipientKind`, `SEND`.
- `backend/app/modules/messaging/message_routes.py` -- 7.9 routes; add the two GET routes and schemas. Mounted in `main.py` already.
- `backend/app/modules/messaging/models.py` -- `messages`, `message_recipients` tables (migration 0052, which already indexes `message_recipients(user_id)` and `messages(class_session_id, …)`): no migration.
- `backend/app/platform/authz.py:80,139,173-254` -- `POLICIES`, `CLASS_STAFF_ROLES`, scope helpers pattern (`table(...)` by name).
- `backend/app/modules/sessions/service.py:667` `staffed_session(user, id, action)`; add `class_ids_of(session, session_ids) -> dict` for the Student read.
- `backend/app/modules/classes/service.py:629,684` `student_names`, `enrolled_classes(user, session=)`.
- `backend/app/modules/identity/service.py:2444` `people(s, ids)` -- sender names.
- `backend/app/modules/games/service.py:176` `class_game_ids(session, class_session_id)` -- number → id.
- `backend/app/platform/notify/__init__.py:110` -- `enqueue` already emits `user:<id>`; nothing to add.
- `backend/tests/messaging/test_messages.py` -- fixtures (`klass`, `students`, `short_game`, `send`, `call`, `email`); `tests/test_imports.py`.
- `frontend/src/lib/api/topics.ts` (+ `topics.test.ts`) -- add keys.
- `frontend/src/modules/games/student-hjem.tsx:97` -- render `<MyMessages />` after the Class list.
- `frontend/src/modules/sessions/dates.ts:101` `osloDateText`.
- `frontend/src/modules/messaging/{api.ts,message-page.tsx,message-form.ts}`; `modules/games/overview-page.tsx:184` `OverviewHeader`; `modules/identity/homes.ts:59` `messagePath`.
- `frontend/e2e/messages.spec.ts`, `e2e/support/live-game.ts` (`liveClassGame` students with `context`).

## Tasks & Acceptance

**Execution:**
- `backend/app/platform/authz.py` -- `messages_addressed_to`, policies `messages.read_own`, `messages.read_sent`.
- `backend/app/modules/sessions/service.py` -- `class_ids_of`.
- `backend/app/modules/messaging/messages.py`, `message_routes.py` -- reads and routes.
- `backend/tests/messaging/test_message_reads.py` -- matrix rows, query count independent of items, no Student write route, fresh-interpreter import.
- `frontend/src/lib/api/openapi.json`, `schema.ts` -- regenerate.
- `frontend/src/modules/messaging/{api.ts,my-messages.tsx,sent-messages-page.tsx,message-list.ts,message-list.test.ts}`, `src/app/(app)/klasseokter/[sessionId]/meldinger/page.tsx`, `homes.ts` (`sentMessagesPath`), `topics.ts`, `copy/nb.ts`, `student-hjem.tsx`, `overview-page.tsx`, `message-page.tsx`.
- `frontend/e2e/messages.spec.ts` -- Student sees a Message on Hjem live without reload, announced, focus kept; staff list with link back; axe at 1440 / 320 / 200 % text.

**Acceptance Criteria:**
- Given a Student with Messages, when they open Hjem, then «Meldinger» lists them newest first with sender, Europe/Oslo time and full text, reflowing at 320 px with no page-level horizontal scroll.
- Given a Student with Hjem open, when a Message is sent to them, then it appears without reload, the live region announces it politely and focus stays where it was.
- Given a Student, when they call `GET /api/me/messages`, then only Messages addressed to them in Classes they are in are returned.
- Given any Student surface, then there is no reply, reaction or forward control, and the api has no Student write route for Messages.
- Given text with line breaks, links or markup, then the product shows it as plain text with breaks kept.
- Given staff of the Class, when they open «Meldinger» for the Class session, then every sent Message is listed newest first with recipient, sender, time and number of Students, each with a link to the Meldingsskjema for the same recipient.

## Spec Change Log

## Review Triage Log

### 2026-11-21 — Review pass
- Layers: blind hunter and edge-case hunter only (Sonnet), as the orchestrator asked for this lane; verification-gap and intent-alignment skipped on that instruction. Both hand-backs dropped; findings read from `review-blind-7-10.md` and `review-edge-7-10.md` in the session scratchpad.
- verdicts: 23 findings — high 0, medium 0, low 19, false 4, maybe-false 0
- findings:
  - `[false]` `[reject]` (blind 1) An unrelated `.logs` hunk and no 7.10 log — the hunk is the orchestrator's Story 9.9 bookkeeping committed on the branch after the baseline (`45437d3`, `8f83b6e`), not this change; the runbook forbids this builder to edit session logs.
  - `[low]` `[reject]` (blind 2) Both lists cut at 100 / 200 with no sign — a Student with over 100 Messages or a Class session with over 200 is unlikely; a truncation flag or paging adds api and page surface.
  - `[low]` `[patch]` (blind 3) The Python enrolment filter after `.limit()` can disagree with the scope — verified: `enrolled_classes` leaves archived Classes out, the scope did not, so an archived Class's Messages took slots and were dropped. Patched with edge 1: the scope helper now leaves archived Classes out; test added.
  - `[low]` `[patch]` (blind 4) The query-count test used one sender and one kind — patched: both samples hold a Student Message, and the larger one adds an Assistant lecturer as a second sender.
  - `[low]` `[patch]` (blind 5) Missing tests — patched the Assistant lecturer reading «Meldinger»; rejected the rest: the Student's read goes through recipient rows whatever the kind, 401 is the shared policy's, a sender cannot be deleted (FK, no delete path), the caps are rejected above.
  - `[low]` `[reject]` (blind 6) No e2e for the access-denied page on «Meldinger» — the `AccessDenied` branch is the shared pattern of every staff page; the api's one 403 answer is tested.
  - `[low]` `[reject]` (blind 7) The fresh-interpreter test is slow; the write-route walk filters on `messages` — the test was asked for by the orchestrator (2.8 s, reported); a Student write route under another name is not something any code here adds.
  - `[low]` `[patch]` (blind 8) Cached Messages announced as new on return to Hjem; the same-text repeat appends a no-break space — the first patched with edge 6; the second rejected: whether a reader drops it is unverified, and the alternatives (clear, then set on a timer) add timing.
  - `[low]` `[reject]` (blind 9) Skeleton flashes, then nothing for a Student with no Messages — the spec asks for the Skjelett while loading; the section sits after the Classes, so nothing above it moves.
  - `[low]` `[patch]` (blind 10) «Faglærer» fallback duplicated in the copy — patched: `arrived` takes the name `senderName` gives.
  - `[low]` `[reject]` (blind 11) Full text, no clamp — the text is at most 2 000 characters (Story 7.9) and the AC asks for the full text.
  - `[low]` `[reject]` (blind 12) `class_id` unused, `list` has no producer — `class_id` lets Hjem group later at no cost; `list` is Epic 13's kind (Story 7.9) and the page must name it.
  - `[low]` `[reject]` (blind 13) No index for the staff list's order — `ix_messages_recipient` leads with `class_session_id`; at most a few hundred rows per Class session are sorted.
  - `[low]` `[patch]` (edge 1) Same as blind 3.
  - `[low]` `[reject]` (edge 2) Same as blind 2.
  - `[false]` `[reject]` (edge 3) A game `class_game_ids` no longer lists — a Message can only name a listed game (Story 7.9 `_resolve`), a Game's purpose never changes and no path deletes Games.
  - `[false]` `[reject]` (edge 4) Same claim on the web side — refuted as edge 3.
  - `[low]` `[patch]` (edge 5) A failed background refetch replaced the shown Messages with the error block — patched: the error shows only when no answer is held.
  - `[low]` `[patch]` (edge 6) A remount with cached Messages announced older ones as new — patched: the live region counts only answers read after the page opened (`isFetchedAfterMount`).
  - `[false]` `[reject]` (edge 7) An empty sender name — `users.name` is NOT NULL and every name passes a validator that refuses blank (`identity/schemas.py` `_name`).
  - `[low]` `[reject]` (edge 8) An empty list takes fewer queries — "fixed" here means independent of the number of Messages; the early return only saves queries.
  - `[low]` `[patch]` (edge 9) Hjem «Meldinger» untested at 200 % text — patched: the e2e opens Hjem at 1280 px with 200 % text and runs axe and the reflow check.
- Matrix audit: Own Messages, Others' Messages and Removed Student — `test_a_student_reads_only_their_own_messages…`; Two Classes — `test_a_student_in_two_classes…` (also archived); Markup text — the first test (api returns it as written) and the e2e (shown literally, break kept, no element); Staff list — `test_the_staff_list_every_message…` (student, former Student, class session, class game with number); Former Student — same; Outsider — `test_only_the_staff_read_the_list…`. All ran and passed.

## Design Notes

- Hjem places «Meldinger» after the Classes: the hub keeps its one primary game action at the top (UX-DR8), and the Messages are a read, not an action. No read state (`open-assumptions.md` line 39).
- The announcement compares ids with the previous answer, not counts, so a Message removed and another added still announces; it is not throttled, since Messages are rare and each is worth hearing.
- Staff read uses its own policy `messages.read_sent` with the same roles as `messages.send`, so the two can part later without touching routes.

## Verification

**Commands:**
- `cd backend && uv run pytest -q tests/messaging tests/test_imports.py tests/test_authz_rules.py` -- pass
- `cd frontend && npx vitest run src/modules/messaging src/lib/api/topics.test.ts` -- pass
- Before commit: full backend suite `--maxprocesses=8`; `npm run typecheck`, `npx vitest run`, `npm run lint:colours`, `npm run build`; Playwright `--workers=4` `messages`, `overview`, `homes`, `live-updates`, play-screen specs.

## Auto Run Result

Status: done

**Summary.** A Student now reads the Messages written to them on Hjem: «Meldinger» after the Classes lists them newest first with the sender, the time in Europe/Oslo and the full text as plain text (line breaks kept, nothing made a link), with no read state and no reply, reaction or forward. A Message's notice already emitted `user:<id>`; `topics.ts` now refetches the list on it, and a polite live region says «Ny melding fra Bård.» without moving focus. `GET /api/me/messages` reads only through the new scope helper `authz.messages_addressed_to` (recipient rows of the User in a Class they are a Student in, not archived). Staff get «Meldinger» at `/klasseokter/{id}/meldinger` (`GET /api/class-sessions/{id}/messages`, policy `messages.read_sent`): each Message with recipient, sender, time, «Sendt til N studenter», the text and «Skriv ny melding» back to the Meldingsskjema for the same recipient; opened from the Oversikt header and the Meldingsskjema, live on `session:<id>`. No migration: 0052 already indexes `message_recipients(user_id)`.

**Files.**
- `backend/app/platform/authz.py` -- `messages_addressed_to`, policies `messages.read_own`, `messages.read_sent`.
- `backend/app/modules/messaging/messages.py` -- `my_messages`, `sent_messages` (fixed query count); `message_routes.py` -- the two GET routes and schemas.
- `backend/app/modules/sessions/repo.py`, `service.py` -- `class_ids_of`.
- `backend/tests/messaging/test_message_reads.py` (new) -- matrix rows, query count, no Student write route, fresh-interpreter import of `messaging.messages`.
- `frontend/src/modules/messaging/{api.ts,message-list.ts,message-list.test.ts,my-messages.tsx,sent-messages-page.tsx}`, `src/app/(app)/klasseokter/[sessionId]/meldinger/page.tsx` (new page) -- reads, Hjem section, staff page.
- `frontend/src/lib/api/topics.ts`, `topics.test.ts` -- `user` → Messages, `session` → «Meldinger».
- `frontend/src/modules/games/student-hjem.tsx`, `overview-page.tsx`, `messaging/message-page.tsx`, `identity/homes.ts`, `copy/nb.ts` -- section, entry links, path, draft copy.
- `frontend/src/lib/api/openapi.json`, `schema.ts` -- regenerated; `frontend/e2e/messages.spec.ts` -- two new tests.

**Review.** 23 findings (blind 13, edge case 10; Sonnet): 0 high, 0 medium, 19 low, 4 false. Patched low entries: archived Classes out of the Student scope (blind 3 / edge 1), query-count sample (blind 4), Assistant reads the list (blind 5), no announcement of cached Messages (blind 8 / edge 6), one sender fallback (blind 10), a failed refetch keeps the list (edge 5), Hjem at 200 % text (edge 9). Rejected the rest with the reasons above. Deferred: none. Follow-up review: not recommended (patched: high 0, medium 0, low 7).

**Verification.** After the patches: backend full suite 2849 passed (96 s, `--maxprocesses=8`); ruff check and format; frontend typecheck, Vitest 817 passed, `lint:colours`, `check:copy`, `next build`; stack rebuilt, then Playwright `--workers=4` `messages`, `overview`, `homes`, `student-home`, `game-card`, `live-updates`, `order-confirm`, `week-advance`: 66 passed, no reruns; axe on Hjem with Messages at 320 px and 200 % text, on «Meldinger» at 1440 px, 320 px and 200 % text. New tests over 1 s: `test_the_messages_module_imports_first_in_a_fresh_interpreter` (2.8 s, a subprocess importing the app, asked for by the orchestrator). No test failed once and passed on rerun.

**Decisions taken instead of the founder.**
- «Meldinger» sits on Hjem after the Classes (the game's primary action stays first); it is not drawn when there is no Message; the Class name shows only for a Student in more than one Class.
- No read state, per `open-assumptions.md` (7.10).
- A Student removed from the Roster, or whose Class is archived, no longer reads that Class's Messages.
- The Student list holds the newest 100, the staff list the newest 200, without paging.
- Staff «Meldinger» also shows each Message's text, and lists Epic 13's `list` Messages as «Til N studenter» with no link back; a removed Student reads «Til en tidligere student», also with no link.
- Entry points: a Lenke «Meldinger» in the Oversikt header and «Se sendte meldinger» on the Meldingsskjema.
- The live announcement is «Ny melding fra Bård.» / «Nye meldinger: 2.», not throttled.
- A gone sender reads «Faglærer» (unreachable today: Users are never deleted).
- Outsiders get 403 `forbidden`, as in Story 7.9.
- Draft copy `[ASSUMPTION]`: all `nb.messages.mine` and `nb.messages.sentList` strings.
- Implemented in the builder's own context and reviewed by two Sonnet layers, as the orchestrator instructed.

**Residual risks.**
- A second Message with the same announcement text relies on an appended no-break space to be read again; untested with real screen readers.
- Verification-gap and intent-alignment reviews skipped by instruction; the visual check is left to the separate visual agent.
