---
title: 'Story 15.1: A Student sees their own data in «Mine data»'
type: 'feature'
created: '2026-11-23'
status: 'done'
baseline_revision: 'cf7116275735c8a5c549fbefd89fad79e931dd04'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-15-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** A Student cannot use the right of access (FR-75): no page shows what the product stores about them, and the personal-data registry of Story 15.2 has no «Mine data» category per table, so a new table could hold Student data that no page shows.

**Approach:** A new page «Mine data» (`/mine-data`), reached by a Lenke beside the User's name on Hjem, shows «Last ned Studentrapport» at the top (the Story 13.7 block per Class session) and one row per category with «Vis». One api call, `GET /api/me/data`, assembles the categories in `reports/my_data.py` from an own-data reader in each owning module's `service.py`, each filtered by the caller's own id through a scope helper. The registry gains a category (or a reason the table is not shown) for every table that names a User, checked by its test.

## Boundaries & Constraints

**Always:**
- Policy `my_data.read_own` (`ANY_USER`) in `platform/authz`; every reader takes the principal's id only and filters by `user_id = me`, `authz.own_seat(me)` or `authz.messages_addressed_to(me)`. No path or query parameter names another User. `Cache-Control: no-store`.
- Categories, in page order (keys): `account` (konto og profil), `orders`, `game`, `explanation`, `reflection`, `follow_ups`, `debrief`, `quiz`, `starting_task`, `test`, `assessment` (incl. the Student's own flags), `letter`, `adjustments` (only listed when it holds something), `messages`, `completion`.
- Each item: optional Class and Klasseøkt number (context), optional time, and fields `{key, kind, value}` with `kind` in `text|number|bool|datetime|date|code`; the frontend labels every key and every code from `nb.ts`.
- Other Students never appear: orders are the Student's own Seat weeks only (Role and game number, no other Seat); messages show the staff sender's name as «Meldinger» does today.
- Registry (`identity/personal_data.py`): each Entry has `category` (one of the keys) or `outside` (why the table is not shown: staff-only ids, transient secrets, content); a table that names a User has exactly one of the two; `report_snapshots` says its lifetime. The test reads the metadata.
- «Last ned Studentrapport» reuses `ReportDownload` for each enrolled Class session with a Game (before the Testfrist it says when it opens); every «Vis» works at any time.
- All copy in `frontend/src/copy/nb.ts` (`myData`), new copy marked `[ASSUMPTION] Story 15.1`. Reflows at 320/360 px and 200 % text; axe clean.

**Never:**
- No new table, migration, job or audit row (reading one's own data is not audited, as `/me` is not).
- No second Student report or PDF; no edit or delete action on the page.
- No computed derivatives shown as stored data (moments, narration, charts); the letter is shown only where the Student's own AI-assessment view gives it.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Student with data | GET `/api/me/data` | Every category key in order; own rows only | — |
| Nothing stored in a category | Student with no Explanation | Category present with no items; page says «Ingenting er lagret.» | — |
| No Tilrettelegging | No adjustment/extension rows | `adjustments` absent from the page | — |
| Other Student's rows | Two Students in one Game | Only own Seat weeks, own answers; the other's text never in the body | — |
| Not logged in | No session | 401 | standard |
| Before Testfrist | Locked session, deadline ahead | Report block says when it opens; «Vis» still works | — |

</intent-contract>

## Code Map

- `backend/app/modules/identity/personal_data.py` -- REGISTRY; add `category`/`outside`, `CATEGORIES`.
- `backend/tests/identity/test_personal_data_registry.py` -- `names_a_user`; add the category/outside checks.
- `backend/app/platform/authz.py:82` POLICIES; `own_seat` (352), `messages_addressed_to` (456), `classes_enrolled_by` (337).
- `backend/app/platform/own_data.py` (new) -- `OwnRecord`/`OwnField` dataclasses every module's reader returns (platform, so modules need not import `reports`).
- Readers (new, each in the module's `service.py`, SQL in its repo or inline): `identity` (users, roles, consent, roster entries), `games` (seat_weeks via own seat, occupancy, believability, time proposals/acceptances, reclaims), `debrief` (explanations, reflection answers, follow-ups, summaries/step marks/members/alone/closures, quiz attempts), `tests` (starting task, attempts/answers, prepared items; letter via `assessed.read` — `tests/assessed.py:289`), `assessment` (ai_assessments, item scores feedback, flags, human scores), `sessions` (adjustments, extensions, deadline reminders), `messaging` (`messages.my_messages` — `messaging/messages.py:503`; notices and mail counts), `progress` (steps, corrections), `replay` (replays, another round, walkthrough narration), `reports` (makeup_games).
- `backend/app/modules/reports/my_data.py` (new), `routes.py`, `schemas.py` -- assembler and `GET /api/me/data` (`getMyData`), context names via `sessions`/`classes` services.
- `frontend/src/modules/identity/session-header.tsx`, `page-shell.tsx`, `home-page.tsx` -- Lenke «Mine data» beside the name on Hjem.
- `frontend/src/app/(app)/mine-data/page.tsx`, `frontend/src/modules/reports/my-data-page.tsx` (new), `api.ts` -- page; `report-download.tsx` `ReportDownload` reused.
- `frontend/src/copy/nb.ts` -- `myData`; `frontend/e2e/my-data.spec.ts` (new).

## Tasks & Acceptance

**Execution:**
- `backend/app/platform/own_data.py`, module `service.py` readers -- own-data reads by id -- one reader per owning module (FR-75, AD-12).
- `backend/app/modules/reports/my_data.py`, `routes.py`, `schemas.py`, `platform/authz.py` -- assemble, policy, route.
- `backend/app/modules/identity/personal_data.py` + test -- categories and reasons for every user-naming table.
- `backend/tests/reports/test_my_data.py` -- own rows per category, another Student's text absent, empty and adjustments cases, 401.
- frontend page, Lenke, copy, Vitest for the field formatter, Playwright `e2e/my-data.spec.ts` (Hjem → Mine data → Vis, empty text, 320/360 px, 200 % text, axe).

**Acceptance Criteria:**
- Given a logged-in Student on Hjem, when they press «Mine data» beside their name, then the page shows «Last ned Studentrapport» at the top and one row per category with «Vis».
- Given a category row, when «Vis» is pressed, then its stored data shows, or «Ingenting er lagret.».
- Given a table that names a User without a category or reason in the registry, when the registry test runs, then it fails.

## Spec Change Log

## Review Triage Log

### 2026-11-23 — Review pass
- verdicts: 53 findings — high 0, medium 6, low 21, false 6, maybe-false 2; 18 descriptive (intent)
- findings:
  - `[false]` `[reject]` blind 1: occupancy ordered by random UUID — ids are UUIDv7 (time-ordered), the convention `authz.seat_held_by` relies on; a span unit test now pins the order.
  - `[medium]` `[patch]` blind 2 / edge 1 / edge 17 / verification other 1: Messages capped at 100 and filtered to enrolled, unarchived Classes — `messaging/own_data.py` now reads every `message_recipients` row of the caller, no limit; test seeds one.
  - `[low]` `[patch]` blind 3 / edge 2 / verification other 2: notices and mails only as counts — each mail delivery now shown (mode, sent, delivery state, skip reason); notices hold only a kind, kept as a count.
  - `[low]` `[reject]` blind 4: staff data not shown — the story is the Student's right of access («As a Student»); staff tables carry a `NOT_SHOWN` reason.
  - `[low]` `[reject]` blind 5 / edge 13: Lenke only on Hjem — the story places it on Hjem.
  - `[low]` `[patch]` blind 6 / edge 8: category lists hand-kept — `test_the_category_lists_agree` checks the Literal against `CATEGORIES`.
  - `[low]` `[reject]` blind 7: unlabelled codes such as item ids — show as stored by design; labelling every item id needs the question-set copy.
  - `[medium]` `[patch]` blind 8 / verification 2: most readers untested with rows — seeded reflection answer, correction, Message and reminder, read back with fields; rest deferred.
  - `[medium]` `[patch]` blind 9 / verification 1: span logic untested — `test_the_orders_are_only_the_weeks_the_student_held_the_seat` (takeover, same-week replacement).
  - `[low]` `[reject]` blind 10: letter N+1 and possible duplicates — one attempt per Student and Class session (unique), a handful of reads.
  - `[low]` `[reject]` blind 11: reclaim row without context when the Seat is not the caller's — a Reclaim is only queued for a Seat the Student held.
  - `[low]` `[reject]` blind 12: rows with few fields (replay, makeup) — they carry Class, Klasseøkt and time, which is what is stored.
  - `[low]` `[reject]` blind 13: sequential reads, no paging — one Student's rows, bounded by their Class sessions.
  - `[low]` `[reject]` blind 14: `evaluation_sessions` reused for labels — reads by id, no lifecycle filter.
  - `[low]` `[reject]` blind 15: bottom-of-file imports — needed to avoid an import cycle; consistent `noqa`.
  - `[low]` `[patch]` blind 16: messaging reader took a Principal — now takes the id like the others.
  - `[low]` `[patch]` blind 17: enrolled-sessions failure hid the page — the page now stands on its data; the report block shows the error alone.
  - `[low]` `[reject]` blind 18: index keys, no export — rows are static per read; the Studentrapport is the portable copy (FR-75 names it).
  - `[low]` `[reject]` blind 19: DST case untested — `osloDateText` is tested in `sessions`.
  - `[maybe-false]` `[defer]` verification 3: registry vs reader linkage — deferred (frontmatter).
  - `[maybe-false]` `[defer]` verification 4: letter gate untested — deferred (frontmatter).
  - `[low]` `[patch]` verification 5: `myDataKey` invalidation untested — Vitest asserts `topicKeys(user)` holds it.
  - `[low]` `[patch]` edge 3: score and feedback note not shown — `feedback_note` added; attempt timings left as stored status (low).
  - `[low]` `[reject]` edge 4 / edge 5: one failing reader gives 500 — readers are plain selects; a fault should surface, not hide a category.
  - `[low]` `[reject]` edge 6: label fallback when `evaluation_sessions` drops a session — it reads by id, so it never drops an existing one.
  - `[low]` `[patch]` edge 9: dict-shaped reflection could print «None» — reader now reads the stored list shape only.
  - `[low]` `[reject]` edge 10: feedback with parts only — the stored feedback always carries `text`; `feedback_note` now shown.
  - `[low]` `[reject]` edge 11: starting-task choice as text — the stored choice is shown as stored.
  - `[low]` `[patch]` edge 12: Orders interleaved across games — sorted by game number and week.
  - `[low]` `[patch]` edge 14: prototype names as code — `Object.hasOwn` guards labels, kinds and codes; tested.
  - `[false]` `[reject]` edge 15: moments and narration shown as derivatives — shown are the stored `moment_ids` count and the stored walkthrough text, not computed views.
  - `[false]` `[reject]` edge 16: guarantee only table-level — the AC asks for table-level; column coverage deferred with the reader linkage.
  - `[low]` `[reject]` edge 18: no shared snapshot across readers — a right-of-access read, not a transaction.
  - `[false]` `[reject]` intent R3 vs R4 (15 vs 9 categories) — the story's list plus the data it names under «Vis» (follow-ups, summaries, Starting task, Messages, flags) and the registry's tables.
  - `[false]` `[reject]` intent «not shown» third state — the AC allows a table to be listed «as holding no personal data with the reason»; `NOT_SHOWN` is that reason.
  - `[false]` `[reject]` intent scope helper — every reader filters by the principal's id (the scope); games through `own_seat`.
  - intent (descriptive, no verdict): snapshot lifetime asserted as the name `TOKEN_LIFETIME`; Role-only check covers one teammate; page checks run only in e2e (passed locally); `test_imports` loosened for `my_data` → `messaging.service`; generated client outside the reviewed diff.

## Design Notes

The own-data readers are deliberately plain table reads (not the per-page views such as `own_reflection`, which are gated by Debrief steps), so every stored row shows at any time. The assembler lives in `reports`, which may import every `service.py` and which nothing imports but `main.py` (`tests/test_imports.py`).

## Verification

**Commands:**
- `cd backend && uv run pytest tests/reports/test_my_data.py tests/identity -q` -- expected: pass
- `cd frontend && npm run typecheck && npx vitest run && npm run lint:colours && npm run check:copy && npm run build` -- expected: pass
- `cd frontend && npx playwright test e2e/my-data.spec.ts e2e/homes.spec.ts --workers=4` -- expected: pass

## Auto Run Result

Status: done
Blocking condition: none

**Summary.** «Mine data» (`/mine-data`), reached by a Lenke beside the User's name on Hjem: «Last ned Studentrapport» at the top (the Story 13.7 block per Klasseøkt with a game; before the Testfrist it says when it opens), then 15 categories in page order, each with its row count and «Vis», showing every stored row with Class, Klasseøkt, time and labelled fields, or «Ingenting er lagret.». `GET /api/me/data` (`getMyData`, policy `my_data.read_own`, `no-store`) assembles `reports/my_data.py` from an `own_records` reader in each owning module's `service.py`, all filtered by the principal's id (games through `authz.own_seat`). The registry gives every table with personal data a «Mine data» category (`SHOWN`) or a reason it is not shown (`NOT_SHOWN`), checked by its test; `report_snapshots` states its lifetime.

**Files.**
- `backend/app/platform/own_data.py` (new): `OwnRecord`, `CATEGORIES`, `record`, `merge`.
- `backend/app/modules/{identity,games,debrief,tests,assessment,sessions,messaging,progress,replay}/own_data.py` (new) and their `service.py` (re-export `own_records`).
- `backend/app/modules/reports/my_data.py` (new), `routes.py`, `schemas.py`; `backend/app/platform/authz.py` (policy).
- `backend/app/modules/identity/personal_data.py`: `category`/`outside`, `SHOWN`, `NOT_SHOWN`.
- Tests: `backend/tests/reports/test_my_data.py` (new), `tests/identity/test_personal_data_registry.py`, `tests/test_imports.py` (`my_data` may read `messaging.service`).
- Frontend: `src/app/(app)/mine-data/page.tsx`, `src/modules/reports/{my-data-page.tsx,my-data.ts,my-data.test.ts}` (new), `api.ts`, `identity/{session-header,page-shell,home-page}.tsx`, `homes.ts`, `lib/api/topics.ts`, `copy/nb.ts` (`myData`, [ASSUMPTION] draft copy), regenerated api client; `e2e/my-data.spec.ts` (new).

**Review.** Four layers (blind, edge case, verification gap, intent; sonnet). Patched: 3 medium (all Messages without cap or enrolment filter; seeded rows read back per category; span unit test), 9 low (mail rows, feedback note, reflection shape, Orders order, `Object.hasOwn`, page not blanked by the sessions read, `myDataKey` test, category Literal test, reader signature). Deferred 2 (registry↔reader linkage; letter gate test). Rejected with reasons in the triage log.

**Follow-up review recommended: true** (3 medium patched): the unverified risk is a reader that silently drops a `SHOWN` table, and the letter row against the Student's own «KI-vurdering» view (both deferred).

**Verification.** Backend full suite 4185 passed, 1 skipped (`-n 8`); `test_my_data` main test ~8 s (marked `long`, plays a 14-Uke game). Frontend: typecheck, Vitest 1337 passed, `lint:colours`, `check:copy`, build (local and in the image). Playwright on the local stack: `my-data.spec.ts` (320 px, 360 px, 200 % text, axe) and `homes.spec.ts` (24 passed); the merged `student-report.spec.ts` passed before the review patches.

**Decisions taken in the founder's place.** 15 categories (the story's nine plus the data it names under «Vis»: follow-ups, Debrief summary, Starting task, Messages; plus game/Replay and Fullføring); AI scores and feedback shown as stored whatever the switch, the letter only where the Student's own view gives it; staff-only tables not shown (reason recorded); the Lenke only on Hjem; Messages from archived or left Classes included; draft copy marked [ASSUMPTION].

**Residual risks.** The deferred items above; notices shown as a count (they hold only a kind).

## Epic 15 close-out (2026-11-23)

- `tests/reports/test_my_data.py::test_every_shown_table_is_read_by_the_readers_of_mine_data` records the SQL the page runs and fails for any `SHOWN` table no reader reads.
- `tests/assessment/test_letter.py::test_mine_data_shows_the_letter_exactly_as_the_students_own_view` compares the letter row with the Student's own KI-vurdering for `student_choice` (off, then on) and `all`.
- Follow-up review: each Debrief-quiz answer (question, choice, right or not) is now shown, not only counted; the `games` reason now names `started_by`/`paused_by` as not shown [ASSUMPTION].

Left (design questions for the founder): a removed Student still sees their letter on «Mine data» though their own KI-vurdering no longer opens; kept rows (Orders, attempts) of a Class session whose data is deleted are still shown to a Student who keeps the account; the «Vis» buttons rely on `aria-describedby` for their name.
