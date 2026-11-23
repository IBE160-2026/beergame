---
title: 'Story 13.6: Message the Students who have not met the requirement'
type: 'feature'
created: '2026-11-23'
status: 'done'
baseline_revision: '99cde7136026e04eda06c96a301ea13219ab1da6'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-13-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-13-5-continue-to-the-debrief-the-replay-and-the-test-from-a-finished-oppfolgingsspill.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** A Lecturer of an Obligatory class session has no way to remind everyone who has not met the requirement in one action (FR-17, FR-40, UX-DR54).

**Approach:** A new Message recipient kind `requirement_not_met`, resolved on the server at send time through `reports.service` (AD-9). The Oversikt shows a Lenke under the Trakt with the count; it opens the Story 7.9 Meldingsskjema with that recipient, which shows a table of those Students and their shares above the text field.

## Boundaries & Constraints

**Always:**
- `reports.service.requirement_not_met(class_session_id, *, session)` returns `(user_id, CompletionStatus)` for each `scope.reporting_students()` Student whose `completion_status` has `requirement_met is False`; `[]` at once for a Class session that is not obligatory or unknown. It reuses the one assembler (no second Completion definition).
- `messaging/messages.py`: `RecipientKind.REQUIREMENT_NOT_MET = "requirement_not_met"`; `_resolve` calls `reports.service.requirement_not_met` inside the send's transaction and narrows to registered Students; a Student who met it meanwhile is left out; none left → 422 `no_recipients`. Named game or Student together with this kind → 403 `forbidden` (one answer). `_sent_before` counts earlier Messages of this kind in the session. `messages` table check constraint gains the kind (migration `0303`, Revises `0302`).
- Api: `GET …/messages/form?recipient=requirement_not_met` and `POST …/messages` body `recipient: "requirement_not_met"`. `MessageFormOut.kind` gains the kind and `not_met: list[NotMetStudentOut]` (empty for other kinds): `user_id`, `name`, `ordered_share`, `required_share`, `playout_share`, `share_game`, sorted by name. `SentMessageOut.kind` gains it. Same `messages.send` policy (Lecturer and Assistant lecturer of the Class), so the Lenke and the table follow it (AD-12).
- Delivery unchanged: kind `message` notice per Student (`immediate`), result line «Meldingen er sendt til N studenter.» with the real count.
- Web: `MessageTo.requirement?: true`, `messagePath` writes `?krav=ikke-oppfylt`; `recipientFrom` refuses it combined with `spill`/`student` or another value. Oversikt rail: under the Trakt list a `Link` «Send Melding til 12 som ikke har oppfylt kravet» from `useMessageForm(sessionId, {requirement: true})`, shown only when that read answers with `students > 0` (absent on 403, not obligatory, all met). The `session:<id>` topic invalidates that read. The Meldingsskjema (same `MessagePage`/`Composer`, no second form) renders the title «Melding til dem som ikke har oppfylt kravet» and, above the field, an HTML `<table>` with `<caption>`, `th scope="col"` headings and `th scope="row"` names as Lenker to `studentPagePath`; cells «70 %» (with «i Oppfølgingsspillet» for a make-up share), required «80 %», playout «20 %» or «–». «Meldinger» lists such a Message «Til 4 som ikke hadde oppfylt kravet» and «Skriv ny melding» reopens the same recipient.
- Copy in `nb.ts`, draft `[ASSUMPTION]`.

**Never:** no use of the explicit `list` kind for this; no new table; no count of the requirement in `ClassOverviewOut` (the Oversikt poll stays as is); no reason or correction text in the table.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Obligatory, 2 of 3 not met | form read | kind `requirement_not_met`, `students=2`, two rows sorted by name | — |
| Not obligatory | form read | `students=0`, `not_met=[]`; Lenke absent | send → 422 `no_recipients` |
| All met | form read | `students=0`; Lenke absent | send → 422 `no_recipients` |
| Met between form and send | correction saved after form read | Message goes to the remaining Students only; `students` counts them | — |
| Kind with `student_id` | form/send | — | 403 `forbidden` |
| Assistant lecturer | form/send | allowed as Story 7.9 | — |
| Other Lecturer / Student / Admin | form/send | — | 403 `forbidden` |
| Repeat key | same body | answers as first, sends nothing | — |

</intent-contract>

## Code Map

- `backend/app/modules/messaging/messages.py` -- `RecipientKind`, `Recipient.__post_init__`, `recipient_of`, `_resolve` (:127), `_sent_before`, `_stored`, `MessageForm`, `message_form`, `send`; imports `reports.service` (no cycle: `reports` never imports `messaging`; `classes.service` loads `messages` lazily).
- `backend/app/modules/messaging/message_routes.py` -- `MessageFormOut`, `MessageIn`, `SentMessageOut`, form/send routes.
- `backend/app/modules/messaging/models.py:77` `RECIPIENT_KINDS`; `migrations/versions/0052_messages.py` original constraint; new `0303_message_requirement_not_met.py`; `tests/test_migrations.py:294`.
- `backend/app/modules/reports/service.py` -- `completion_status`; add `requirement_not_met`; `scope.reporting_students`; `sessions.completion_terms(s, cs).obligatory`.
- `backend/app/platform/authz.py:126,221` -- `messages.send` (Lecturer, Assistant) reused.
- Tests: `tests/messaging/test_messages.py` (`form`, `send`, `stored`, `message_notices`, fixtures `klass`, `emitted`), `tests/reports/test_corrections.py` (`correct`, `dated`, `students`, `obligatory`), `tests/sessions/test_game_end.py` `short_game`. New `tests/reports/test_message_not_met.py`.
- Web: `frontend/src/modules/messaging/{api.ts,message-form.ts,message-page.tsx,message-list.ts}` (+ tests), `frontend/src/modules/identity/homes.ts:80` `messagePath`, `frontend/src/modules/games/overview-rail.tsx` `Funnel`, `overview-page.tsx:330,360` (pass `sessionId`), `frontend/src/lib/api/topics.ts` `session` case, `frontend/src/modules/reports/record.ts` `percent`, `frontend/src/copy/nb.ts` (`messages`, `overview.rail.funnel`). E2E `frontend/e2e/` messaging spec (pattern of Story 7.9) — new `message-not-met.spec.ts`.

## Tasks & Acceptance

**Execution:**
- `backend/app/modules/reports/service.py` -- add `requirement_not_met` -- one source for the list.
- `backend/app/modules/messaging/{models,messages,message_routes}.py`, migration `0303` -- kind, resolve, form rows, api fields.
- `backend/tests/reports/test_message_not_met.py` -- matrix rows: form count and rows (with shares from a short game), not obligatory, all met, met between form and send, forbidden combinations and roles, Assistant allowed, notices and sent list kind; migration assertion.
- `frontend` -- copy, `messagePath`/`recipientFrom`/`messageTitle`/`recipientLine`/`againTo` (+ unit tests), table in `Composer`, rail Lenke, topic key, `npm run api:generate`.
- `frontend/e2e/message-not-met.spec.ts` -- Oversikt Lenke → form with table → send → result line; axe at 360 and 1440 px.

**Acceptance Criteria:**
- Given an Obligatory class session with Students who have not met the requirement, when the Lecturer opens the Oversikt, then under the Trakt a Lenke reads «Send Melding til N som ikke har oppfylt kravet», absent when not obligatory or all met.
- Given the Lenke, when followed, then the Meldingsskjema opens titled for this recipient with a table (name Lenke to the Studentside, ordered share, required share, playout share) above the text field.
- Given a send, when delivery runs, then each remaining Student gets one `message` notice and the result line shows the number sent.

## Spec Change Log

## Review Triage Log

### 2026-11-23 — Review pass
- layers: four (blind, edge case, verification gap, intent alignment) on Sonnet, as the lane brief directs for a change to who gets Messages.
- verdicts: 31 findings — high 0, medium 2, low 29, false 0, maybe-false 0 (7 descriptive intent rows graded low)
- findings:
  - `[low]` `[patch]` Verification: `required_share` and `share_game` never asserted through the form. The played-out test now gives one Student a Tilrettelegging share of 50 and asserts 50 against 80 per row; `share_game` is now typed `Literal["class", "makeup"]` end to end. No make-up case added (a direct field copy, at test cost).
  - `[low]` `[reject]` Verification: 0303's downgrade with a stored row is never run. Rollback only; the downgrade now keeps such rows (see the Blind downgrade row), no data loss path left.
  - `[low]` `[patch]` Verification: mojibake in the e2e header comment. Fixed (written by a PowerShell round trip).
  - `[low]` `[patch]` Verification: overlong `MessagePage` docstring line. Rewrapped.
  - `[low]` `[reject]` Verification: no component test of `NotMetLink`/`NotMetTable`. The e2e renders both at two widths with axe, and now the Lenke's absence too.
  - `[low]` `[reject]` Intent: the count comes from the form read, not the Oversikt answer. Same `reports.service.requirement_not_met` over `reporting_students()`; kept off the Oversikt poll (Design Notes).
  - `[low]` `[patch]` Intent: Lenke absence not shown in the browser. The e2e now meets the requirement for the last Student, waits for the Lenke's read (`students: 0`) and asserts no Lenke.
  - `[low]` `[reject]` Intent: the Assistant's Oversikt not in the browser. Same endpoint and `messages.send` policy, api-tested for the form and the send.
  - `[low]` `[reject]` Intent: ordered/playout cell values not in the e2e. Asserted at the api (20/80/80, 50 adjusted) and in `notMetCells` unit cases.
  - `[low]` `[reject]` Intent: `immediate` not asserted. Delivery is Story 7.9's unchanged `message` kind; the api test asserts the notices and the e2e the mail.
  - `[low]` `[reject]` Intent: the kind lives in `messages.py`, not `service.py`. `messaging/service.py` serves `messages.py`'s names (Story 7.9 layout); the kind is reachable as `service.RecipientKind`.
  - `[low]` `[patch]` Intent: e2e mojibake. Same fix as above.
  - `[medium]` `[patch]` Edge: `requirement_not_met` re-read the scope and the registered Students once per Student (O(N²)). `completion_status` now delegates to `_status(s, user, cs, terms)`; the list reads terms and scope once.
  - `[low]` `[reject]` Edge: before the Start date everyone is «not met», so the Lenke shows for the whole class. The story's rule: absent only when not obligatory or all met. Listed as a founder decision.
  - `[low]` `[reject]` Edge: the count can go stale without a `session:<id>` event (Orders, deadlines). Reread on every visit; the recipients are judged again at send.
  - `[low]` `[patch]` Edge: `?krav=` empty with a `student` id read as a one-Student form. Any `krav` other than `ikke-oppfylt` is refused now; unit case added.
  - `[low]` `[patch]` Edge: rows sorted by code point (Å before Æ before Ø). Sort key maps Æ, Ø, Å after Z; unit test.
  - `[low]` `[reject]` Edge: two sends with different keys send twice. As for every recipient since Story 7.9; «Sendt tidligere: N» shows it.
  - `[low]` `[reject]` Edge (claim): the Code Map says no cycle with a top-level import. The code imports on use and the fresh-interpreter test now covers the worker's import order; the fix would edit this spec.
  - `[low]` `[reject]` Edge (claim): Design Notes' refetch claim. As the stale-count row; spec edit only.
  - `[low]` `[patch]` Blind: e2e mojibake. Same fix.
  - `[medium]` `[patch]` Blind: N-Student recomputation on every Lenke read. Same root and patch as the O(N²) row; it never runs on the Oversikt poll.
  - `[low]` `[reject]` Blind: the Lenke ignores «Oppdater automatisk» off. Its own read refetches only on mount and `session:<id>`; holding it adds state for a link.
  - `[low]` `[reject]` Blind: staleness from `session` events only. Corrections do emit `session:<id>` (api test); same as the Edge row.
  - `[low]` `[reject]` Blind: «not met» from day one; `None` statuses dropped. Story rule; `None` means outside the reporting scope.
  - `[low]` `[patch]` Blind: test gaps. Added the Tilrettelegging share and the Lenke's absence; the rest (unknown name, «Skriv ny melding» end to end, shrinking list on a repeat key) rejected as rare or covered by unit cases.
  - `[low]` `[patch]` Blind: 0303 downgrade deletes sent Messages. It now maps them to `list`, which keeps their recipients.
  - `[low]` `[patch]` Blind: sort not Norwegian. Same patch as the Edge row.
  - `[low]` `[reject]` Blind: `[ASSUMPTION]` copy and its wording. The story asks for draft copy for review; listed in the report.
  - `[low]` `[patch]` Blind: `share_game` typed `str` in `messages.py`. Now `Literal["class", "makeup"] | None`.
  - `[low]` `[reject]` Blind: smaller points. Empty `krav` and the docstring patched above; the `krav` constants sit beside `messagePath` in `homes.ts`; `td.nth(1)` is the e2e's column read; `messaging` has no README to update.

## Design Notes

The count is read through the form endpoint rather than the Oversikt answer: Completion per Student costs a dozen reads, and the Oversikt is re-read on every Game change; the form read refetches only on `session:<id>`.

## Verification

**Commands:**
- `uv run pytest tests/reports/test_message_not_met.py tests/messaging -q` (lane env) -- pass
- `npm run typecheck && npx vitest run src/modules/messaging src/modules/games` -- pass
- `npx playwright test e2e/message-not-met.spec.ts --workers=4` -- pass

## Auto Run Result

Status: done

**Summary.** A Lecturer (or Assistant lecturer) of an Obligatory class session can write one Message to everyone who has not met the requirement (FR-17, FR-40, UX-DR54). `messaging` has a new recipient kind `requirement_not_met`, resolved on the server through `reports.service.requirement_not_met` (the one Completion assembler over `reporting_students()`) when the form is read and again in the send's transaction, so a Student who met it meanwhile is left out. The Oversikt shows «Send Melding til N som ikke har oppfylt kravet» under the Trakt, absent when not obligatory, all met, or refused. It opens the Story 7.9 Meldingsskjema (`?krav=ikke-oppfylt`, no second form) with a `<table>` above the field: name as a Lenke to the Studentside, share ordered, share required (Tilrettelegging included) and share played in the playout. «Meldinger» lists such a Message «Til N som ikke hadde oppfylt kravet».

**Files.**
- Backend: `reports/service.py` (`requirement_not_met`, `_status`), `reports/README.md`; `messaging/messages.py` (kind, resolve, table rows, Norwegian order), `messaging/message_routes.py` (`recipient` param/body, `not_met`, kinds), `messaging/models.py`; migration `0303_message_requirement_not_met.py` (check constraint; downgrade keeps rows as `list`).
- Backend tests: `tests/reports/test_message_not_met.py` (new), `tests/test_migrations.py` (HEAD 0303), `tests/messaging/test_message_reads.py` (worker import order), `tests/test_imports.py` (`messages.py` may call `reports.service`).
- Frontend: `copy/nb.ts`, `identity/homes.ts`, `messaging/{api,message-form,message-list,message-page}`, `games/overview-{rail,page}.tsx`, `lib/api/topics.ts`, unit tests, regenerated `lib/api/{openapi.json,schema.ts}`, `e2e/message-not-met.spec.ts` (new).

**Review.** Four layers, 31 findings: 0 high, 2 medium, 29 low. Patched one medium entry (the list reread the scope per Student) and 13 low rows; nothing deferred; the rest rejected with reasons in the Review Triage Log. Follow-up review: **false** (one medium entry patched, no high).

**Verification.**
- Full backend suite (8 processes): 3751 passed, 1 failed: `tests/debrief/test_group_alone.py::test_leaving_and_dropping_out_hand_the_group_on`, which passes alone (6/6) and touches no changed code; an earlier run's `tests/ai/test_effort.py` failure also passed alone. The first run found `test_imports` refusing `messaging → reports`, fixed above. ruff check and format pass.
- New tests over 1 s: `test_the_message_goes_to_those_who_have_not_met_the_requirement_when_it_is_sent` (about 3 s), `test_the_table_shows_the_share_ordered_and_the_share_the_playout_played` (about 3 s, a played-out game), `test_the_messages_module_imports_first_in_a_fresh_interpreter[app.modules.ops.jobs]` (about 6 s, a fresh interpreter).
- Frontend: typecheck, Vitest 1203 passed, lint:colours, check:copy; build in the image.
- Playwright (4 workers, lane stack): `message-not-met` (Lenke → form → table → send → mail → Lenke gone; axe at 1440 and 320 px), `messages`, `overview`, `takeover-overview`, `homes`, `order-field`, `order-confirm`, `game-end`: 63 passed.

**Decisions taken for the founder [ASSUMPTION].**
- The Lenke shows whenever someone has not met the requirement, also before the Start date and while the game runs (the story's rule).
- The count is the form endpoint's read, not a field of the Oversikt answer (Completion per Student is too costly for the Oversikt poll); it refetches on `session:<id>`.
- `messaging/messages.py` calls `reports.service` on use; the import rule of Story 13.1 now allows exactly that.
- Draft copy: «Send Melding til N som ikke har oppfylt kravet», «Melding til dem som ikke har oppfylt kravet», table «Studenter som ikke har oppfylt kravet» with «Student», «Bestilte selv», «Kravet», «Spilt i utspillingen», «–», «… i Oppfølgingsspillet», the note «Listen sjekkes på nytt når du sender. …», and «Til N som ikke hadde oppfylt kravet».

**Personal data.** No new table.

**Residual risks.**
- Each read of the form for this recipient computes Completion for every reporting Student (about a dozen reads each).
- The Lenke's count is not refreshed by Orders or deadlines while the Oversikt stays open.
