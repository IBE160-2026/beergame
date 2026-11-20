---
title: 'Story 5.6: Add Lab hours'
type: 'feature'
created: '2026-11-20'
status: 'done'
baseline_revision: '1d9c62932dbe4a842a1b8b85ebaabad44a03dbd1'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-5-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-5-5-choose-ai-mode-effort-level-debrief-mode.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** A Lecturer cannot add Lab hours (date, time, place) to a Class session, so Students cannot learn when staff are present, and Epic 8's «I rommet» has no way to ask whether a Lab hour is on (FR-19).

**Approach:** A `lab_hours` table owned by `modules/sessions` with add, change and remove routes that save at once (not with «Lagre Klasseøkt»), notify each registered Student through `platform/notify` with three new `digest` kinds, and show on the Klasseøkt as `lager` squares on the Datolinje with a legend and a «Labtimer» list; `GET /api/me/class-sessions` returns upcoming Lab hours and `sessions.service.current_lab_hour` answers other modules.

## Boundaries & Constraints

**Always:**
- Migration 0035 `lab_hours`: `id` (UUIDv7), `class_session_id` FK `class_sessions` ON DELETE CASCADE (indexed), `starts_at`, `ends_at` (timestamptz, UTC), `place` (Text), `revision` int default 1, `cancelled_at` nullable, `created_by` FK users SET NULL, `created_at`, `updated_at`. CHECKs: `ends_at > starts_at`, `char_length(place) BETWEEN 1 AND 120`. A removed Lab hour is kept with `cancelled_at` set, so its cancellation mail can still name it; it is never listed again.
- Routes (manage = Class owner; Assistant reads only; archived Class 409 `class_archived` through `_writable`; any unknown, cancelled or out-of-scope id 403 `forbidden`): `POST /api/class-sessions/{id}/lab-hours` → 201 `LabHourOut`; `PUT /api/class-sessions/{id}/lab-hours/{lab_hour_id}` → 200 `LabHourOut`; `DELETE …/{lab_hour_id}` → 204. Body `LabHourIn {starts_at, ends_at, place}` (instants with an offset).
- Rules, in this order: a Lab hour that has ended (`ends_at <= now`) cannot change or go: 409 `lab_hour_ended`. Then 422 `invalid_lab_hour` with `fields`: `place` `required` (blank after trimming) or `too_long` (> 120); `ends_at` `not_after_start` (≤ start), `too_long` (more than 12 h after start) or `past` (≤ now, for a new or changed time). The Start-date lock never applies (FR-18). Values are stored trimmed and to the whole minute; an unchanged PUT stores nothing, raises no revision and tells nobody.
- Notices (AD-9): per registered Student (`classes.service.registered_students`), `notify.enqueue` in the mutation's transaction with `ref` = Lab hour id and `user_id` = Student: kind `lab_hour_added` (key `lab_hour_added:{id}:{user}`), `lab_hour_changed` (key `lab_hour_changed:{id}:{revision}:{user}`), `lab_hour_cancelled` (key `lab_hour_cancelled:{id}:{user}`). All three are `digest` in `messaging.delivery.KINDS` with Jinja2 templates (txt + html, bokmål) and a context resolver in `sessions.service` that reads the Lab hour at send time (class name, weekday, date, start, end, place in Europe/Oslo). The resolver returns None (left out of the digest) when the User is no longer a registered Student, and for added/changed when the Lab hour is cancelled or has ended. Templates never name the number of Weeks, «Beer Game» or «bullwhip».
- Events: each mutation emits `session:<id>`; `notify.enqueue` emits `user:<id>` per Student. Registry gets `sessions.add_lab_hour`, `sessions.change_lab_hour`, `sessions.remove_lab_hour` → `{session, user}`.
- Reads: `ClassSessionOut.lab_hours` lists the session's Lab hours that are not cancelled, by start, each `{id, starts_at, ends_at, place, ended}`. `EnrolledSessionOut.lab_hours` lists the upcoming ones (`ends_at > now`, not cancelled) with `{id, starts_at, ends_at, place}`. `service.current_lab_hour(class_session_id, now)` → the Lab hour with `starts_at <= now < ends_at`, not cancelled (earliest start if several), else None.
- Web (`frontend/src/modules/sessions/`): under the Datolinje a row with the legend «Blå firkant: Labtime, {sted}.» (distinct places joined «A, B og C»; shown only when Lab hours exist) and the Lenke «Legg til Labtime» (managers only). Then «Labtimer»: one line per Lab hour «to. 26. nov. 14:15–16:00, Datalab A2», ended ones marked «(ferdig)», each with a Lenke «Endre» whose accessible name names the Lab hour, except ended ones. The Datolinje draws each Lab hour as a `lager` square under the axis at its start, labelled with its day and time; the x range covers dates and Lab hours, and Lab hours alone still draw the line.
- In-place form (one open at a time): «Dato» (`type=date`), «Start» and «Slutt» (`type=time`), «Sted» (text, maxLength 120), primary «Lagre Labtime» (add) or «Lagre endringen» (change), secondary «Fjern Labtimen» (change only), «Avbryt». The consequence line «Studentene får beskjed på e-post.» stands above the buttons. While it is open «Lagre Klasseøkt» shows as secondary. Focus moves to «Dato» on open; «Avbryt» returns focus to the Lenke that opened it; after a save or removal focus moves to a result line (`tabindex=-1`, «Labtimen er lagt til.» / «… endret.» / «… fjernet.»). The form checks before sending: a field the browser holds half-typed (`validity.badInput`) or empty gets its own reason, never read as empty silently (Issue #100 pattern); Slutt not after Start gets «Slutt må være etter start.». API refusals show under their field; a failure keeps the values and shows «Det ble ikke lagret. Prøv igjen.» (`role="alert"`). The response updates `lab_hours` in the cached Class session; drafts elsewhere on the page are kept.
- All copy in `nb.ts`, new strings marked [ASSUMPTION] where not from EXPERIENCE.md / mockup 03.

**Never:** a Lab hour saved through «Lagre Klasseøkt»; a lock check on Lab hours; names, addresses or free text in `notices`; another module reading `lab_hours`; a new sweeper or delivery path; touching the demo Class; comparing DB time with host time; Story 5.7 (Obligatorisk, Inactivity limit) or Epic 8's «I rommet» UI; editing `sprint-status.yaml`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Add | 2 registered Students; valid body | 201; listed; 2 `lab_hour_added` notices (ref = id); `session` + 2 `user` events | – |
| Many | add three | all three listed by start | – |
| End before start | `ends_at` = start − 1 h | nothing stored, no notice | 422 `invalid_lab_hour` `{ends_at: not_after_start}` |
| No place | `place: "  "` | nothing stored | 422 `{place: required}` |
| Too long | 13 h; place of 121 chars | nothing stored | 422 `{ends_at: too_long}`, `{place: too_long}` |
| Past | `ends_at` ≤ now | nothing stored | 422 `{ends_at: past}` |
| Change | new place | revision 2; `lab_hour_changed` per Student | – |
| Unchanged | same values | 200; no notice, no revision | – |
| Remove | DELETE | 204; not listed; `cancelled_at` set; `lab_hour_cancelled` per Student | – |
| Ended | PUT/DELETE after `ends_at` | nothing changes | 409 `lab_hour_ended` |
| After start | session locked | add/change/remove work | – |
| Archived / Assistant / unknown id | – | nothing changes | 409 `class_archived` / 403 / 403 |
| Student read | 1 past, 1 upcoming, 1 cancelled | only the upcoming one | – |
| current_lab_hour | now inside / outside | the Lab hour / None | – |
| Digest | added notice, sweep in the day | one mail naming class, day, times, place | resolver None → left out |

</intent-contract>

## Code Map

- `backend/app/modules/sessions/models.py` -- add `lab_hours` Table; `migrations/versions/0035_lab_hours.py` (after `0034_class_session_effort_level`).
- `backend/app/modules/sessions/repo.py` -- insert/update/cancel/list/get Lab hours; `enrolled_sessions` rows feed the Student read.
- `backend/app/modules/sessions/service.py` -- `_class_for` (388), `_writable` (380), `get_session` (484, add `lab_hours`), `enrolled_sessions` (751), new `add_lab_hour`, `change_lab_hour`, `remove_lab_hour`, `current_lab_hour`, `lab_hour_mail_context(kind)`, `LabHourEnded`, `InvalidLabHour(_FieldsError)`; kind constants.
- `backend/app/modules/sessions/{schemas,routes}.py`, `README.md` -- `LabHourIn`, `LabHourOut`, `EnrolledLabHourOut`; three routes; error mapping as `save_class_session` (106).
- `backend/app/modules/messaging/delivery.py:76` `KINDS` -- three `Delivery(DIGEST, …, context=…)`. Import cycle: `sessions.service` → `classes.service` → `messaging.service` → `delivery`; so `delivery` names the kinds as literals and wraps the resolver lazily (call-time attribute lookup), with a test that the literals equal the `sessions.service` constants. `tests/test_imports.py:121` allows `app.modules.sessions.service`.
- `backend/app/platform/email/templates/kinds/` -- `lab_hour_{added,changed,cancelled}.{txt,html}.j2`, pattern `manual_registration.*.j2` (months list, `#2B6CA3` link colour, `#44586F` secondary).
- `backend/app/platform/events/registry.py` -- three commands.
- `backend/tests/sessions/test_dates.py` helpers (`new_session`, `student_of`, `at`, `refusal`, `emitted`, `klass`, `rows`); `tests/messaging/helpers.py` (`drain`, `mails`, `oslo`), `tests/messaging/test_digest.py` (`sweep_at`) -- new `tests/sessions/test_lab_hours.py`; `tests/test_migrations.py` head → 0035.
- `frontend/src/modules/sessions/date-line.tsx` -- `place()` range and Lab hour squares; `dates.ts` `osloDayAndTime`, `fromOsloInput`, `toOsloInput`.
- `frontend/src/modules/sessions/class-session-page.tsx:232` dates section -- mount `LabHours`; `SaveRow` gets a `secondary` flag.
- New `frontend/src/modules/sessions/lab-hours.ts` (+ test: body from inputs, client checks, refusal mapping, list line, places legend) and `lab-hours.tsx` (list, form). `api.ts` -- add/change/remove calls. Reuse `TextField`, `Button`, `ActionError`, `LINK_BUTTON`, `PANEL` pattern of `classes/roster-entry-forms.tsx`.
- `frontend/src/copy/nb.ts:921` `sessions.dates` -- new `labHours` block; regenerate `lib/api/{openapi.json,schema.ts}`.
- `frontend/e2e/class-session-lab-hours.spec.ts` (new), pattern `class-session-dates.spec.ts` (`osloInput`, `newSession`).

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0035_lab_hours.py`, `sessions/models.py`, `repo.py` -- table and SQL.
- `sessions/schemas.py`, `service.py`, `routes.py`, `README.md` -- rules, notices, reads, `current_lab_hour`, mail context.
- `messaging/delivery.py`, the six templates, `events/registry.py`, `tests/test_imports.py` -- digest kinds.
- `backend/tests/sessions/test_lab_hours.py` (new), `tests/test_migrations.py` -- every matrix row through the routes, the resolver cases and one digest mail.
- `frontend/src/modules/sessions/lab-hours.ts(x)` + `lab-hours.test.ts`, `date-line.tsx`, `class-session-page.tsx`, `api.ts`, `copy/nb.ts`, regenerated api types -- the screen.
- `frontend/e2e/class-session-lab-hours.spec.ts` (new) -- add (square, legend, list), end-before-start and missing place inline, half-typed date refused, change, remove, Assistant/locked view via the api, axe at 320/360/1440 and 400 % zoom with the form open.

**Acceptance Criteria:**
- Given the Klasseøkt, when the Lecturer presses «Legg til Labtime», then the in-place form opens with focus in «Dato», and a saved Lab hour appears as a square on the Datolinje, in the legend and in the «Labtimer» list without a page reload.
- Given an end before its start, a missing place or a half-typed date, then the form says why under that field and sends nothing (or shows the API's reason).
- Given a Lab hour is added, changed or removed, then each registered Student gets one notice of the matching digest kind holding ids only, and the next digest mail names the Lab hour.
- Given a locked Class session, then Lab hours can still be added, changed and removed; given an Assistant, they are text only.
- Given a Student, then `GET /api/me/class-sessions` returns the upcoming Lab hours; given another module, `current_lab_hour` answers without reading the table.

## Spec Change Log

## Review Triage Log

### 2026-11-20 — Review pass
- verdicts: 38 findings — high 0, medium 4, low 28, false 6, maybe-false 0
- findings:
  - `[medium]` `[patch]` (blind) «Avbryt» on a change form sends focus to «Legg til Labtime»: the «Endre» ref is deleted while the form is open. The opener is now looked up after the form unmounts; e2e asserts focus returns to that «Endre».
  - `[low]` `[reject]` (blind) A Lab hour added and removed before the digest gives a cancellation the Student never heard of. Mild; fixing needs a way to see or withdraw other notices, which `platform/notify` does not offer. Residual risk.
  - `[low]` `[reject]` (blind) Added + changed notices in one digest repeat the same current values. Cosmetic; same missing notify API as above. Residual risk.
  - `[low]` `[reject]` (blind) Registered Students are read before the write transaction. Same pattern as the date save (5.2); a Student registering in that instant still reads the Lab hour from `/api/me/class-sessions`.
  - `[low]` `[reject]` (blind) One Student-list query per notice at send time. One notice per Lab hour change per Student; a class-sized list per notice is small, and `classes` offers no session-bound membership check.
  - `[low]` `[reject]` (blind) Lab hours cannot cross midnight in the form, and the mail prints only the end time. A Lab hour is one date with two times by design (EXPERIENCE: date, start, end, place).
  - `[low]` `[reject]` (blind) A place over 1000 characters gets a schema 422, not `too_long`. Unreachable from the form (maxLength 120); the bound guards the api.
  - `[false]` `[reject]` (blind) HTML injection in mail. `platform/email/render.py` enables autoescape for `*.html.j2`.
  - `[low]` `[patch]` (blind) Stale state after 409 `lab_hour_ended` or 403. The form now reads the session again on those codes, and closes when the Lab hour it changes is gone or ended.
  - `[low]` `[reject]` (blind) No limit on Lab hours or notices. A Lecturer's own action, one digest per day per Student caps the mail.
  - `[low]` `[reject]` (blind) Opening another form drops typed input. One form at a time is EXPERIENCE.md's rule.
  - `[low]` `[reject]` (blind) Datolinje tick anchors now follow position, not index. Needed once Lab hours widen the range (the first date is no longer at the edge); the 5.2 e2e passes unchanged.
  - `[low]` `[patch]` (blind) No test for ended or archived omission in the mail. Added `test_a_lab_hour_over_before_the_digest_or_an_archived_class_gets_no_mail`.
  - `[low]` `[reject]` (blind) The Assistant/locked e2e uses a rewritten GET. The real roles and lock are pinned at the api (`test_lab_hours.py`), as in 5.3 to 5.5.
  - `[false]` `[reject]` (blind) `assert` as a guard. `LabHourIn` makes both times required, so `_minute` never returns None; the assert only narrows the type.
  - `[low]` `[reject]` (blind) 120 and 12 h copied in copy and frontend. The copy must name the number; the api answers the same codes either way.
  - `[low]` `[reject]` (blind) Import cycle `delivery → sessions.service`. Deliberate, commented, and a test keeps the kind names equal.
  - `[false]` `[reject]` (blind) 403 for a missing Lab hour. FR-5: one answer for anything the User may not reach, as every sessions route.
  - `[medium]` `[patch]` (edge) Focus after cancelling a change. As blind row 1.
  - `[low]` `[patch]` (edge) A refetch that drops the edited Lab hour leaves «Lagre Klasseøkt» secondary. The panel closes the form (and tells the page) when that Lab hour is gone or ended.
  - `[low]` `[reject]` (edge) Cross-midnight Lab hours. As blind row 6.
  - `[low]` `[reject]` (edge) Cancellation of a Lab hour the Student never heard of. As blind row 2.
  - `[low]` `[reject]` (edge) Repeated added/changed lines. As blind row 3.
  - `[low]` `[patch]` (edge) A cancellation mail for a Lab hour already over. The resolver now leaves out every kind once the Lab hour has ended (test above).
  - `[low]` `[reject]` (edge) Student registering between read and commit. As blind row 4.
  - `[low]` `[reject]` (edge) Mail shows no end date across midnight. As blind row 6.
  - `[low]` `[reject]` (edge) Place over 1000 characters. As blind row 7.
  - `[low]` `[reject]` (edge) Date tick anchors changed. As blind row 12.
  - `[medium]` `[patch]` (edge) Spec claim «Avbryt returns focus» broken for change. As blind row 1.
  - `[low]` `[patch]` (verification-gap) Ended and archived omission untested. As blind row 13.
  - `[low]` `[patch]` (verification-gap) «Lagre Klasseøkt» stepping back is unasserted. e2e compares its computed background with the form's primary while open and after «Avbryt».
  - `[low]` `[patch]` (verification-gap) Whole-minute rounding untested. Added `test_times_are_stored_to_the_whole_minute` (also an unchanged PUT with seconds).
  - `[medium]` `[patch]` (verification-gap, other) Focus after cancelling a change. As blind row 1.
  - `[low]` `[reject]` (intent) Ended Lab hours cannot change ("at any time"). Read as "the Start-date lock does not apply"; changing a Lab hour that is over would only mail Students about the past.
  - `[low]` `[reject]` (intent) Extra rules (12 h, past, 120 characters). Keep `current_lab_hour` meaningful and the column bounded; each has its reason in the form.
  - `[low]` `[reject]` (intent) Server refusals reach the form only through a unit-tested mapping. The form checks the two named rules itself; the api codes are pinned in `test_lab_hours.py`.
  - `[false]` `[reject]` (intent) «Legg til Labtime» is a button. It is the project's Lenke (`LINK_BUTTON`): opens a panel, commits nothing (EXPERIENCE.md → Lenke).
  - `[false]` `[reject]` (intent) Quiet hours and one mail per day not exercised for these kinds. They are the shared digest's (Story 3.5, `test_digest.py`); the kinds are asserted `digest`.
  - `[false]` `[reject]` (intent) No Student Datolinje. The story returns Lab hours "for Epic 6's Hjem"; no Student screen is in scope.

## Design Notes

- Lab hours save on their own, because they stay editable after the lock, notify Students at once and are many; mixing them into «Lagre Klasseøkt» would tie their notices to unrelated drafts.
- Soft delete keeps ids-only notices renderable: the cancellation mail reads the cancelled row.
- The 12 h cap keeps `current_lab_hour` meaningful (a Lab hour is hours, not weeks).

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/sessions/test_lab_hours.py tests/test_imports.py -q` -- pass, each test under 1 s.
- `cd backend && uv run pytest -q && uv run ruff check . && uv run ruff format --check .` -- pass.
- `cd frontend && npm run typecheck && npm test && npm run check:copy && npm run lint:colours && npm run build` -- pass.
- `cd frontend && npx playwright test` against `timeout 900 docker compose up -d --build --wait proxy worker-batch` -- pass.

## Auto Run Result

Status: done

**Summary.** Lab hours are added, changed and removed in place under the Datolinje and saved at once (`POST`/`PUT`/`DELETE /api/class-sessions/{id}/lab-hours[/{lab_hour_id}]`), before and after the Start date. `lab_hours` (migration 0035) keeps a removed Lab hour as cancelled. Each change enqueues one ids-only notice per registered Student (`lab_hour_added`, `lab_hour_changed` with the revision in its key, `lab_hour_cancelled`), all three digest kinds whose Jinja2 mail reads the Lab hour at send time. The Datolinje draws each Lab hour as a `lager` square with day and time, the legend «Blå firkant: Labtime, {sted}.» names the places, and «Labtimer» lists them as the text alternative. `GET /api/me/class-sessions` returns the upcoming Lab hours; `sessions.service.current_lab_hour` answers other modules.

**Files changed**
- Backend: `migrations/versions/0035_lab_hours.py` (new); `sessions/{models,repo,service,schemas,routes}.py`, `README.md`; `messaging/delivery.py` (three digest kinds, lazy resolver); `platform/email/templates/kinds/lab_hour_*.j2` and `_lab_hour.j2` (new); `platform/events/registry.py`; tests `sessions/test_lab_hours.py` (new), `test_migrations.py` (head 0035, 0035 test), `sessions/test_dates.py` (Student read field).
- Frontend: `sessions/lab-hours.ts` + `lab-hours.test.ts` and `lab-hours-panel.tsx` (new), `date-line.tsx` (squares, position-based anchors), `class-session-page.tsx` («Lagre Klasseøkt» secondary while a form is open), `api.ts`; `copy/nb.ts` (`sessions.labHours`, [ASSUMPTION]); regenerated `lib/api/{openapi.json,schema.ts}`; e2e `class-session-lab-hours.spec.ts` (new).

**Review findings.** 38: 0 high, 4 medium (one root cause, reported four times), 28 low, 6 false. Patched: focus back to the «Endre» that opened a form; the form reads the session again on `lab_hour_ended`/403 and closes when its Lab hour is gone; every notice is left out once the Lab hour is over; tests for ended/archived mail omission, whole-minute rounding and «Lagre Klasseøkt» stepping back. Deferred: none. Rejected: the rest, each with its reason in the triage log.

**Follow-up review recommended: false.** One medium root cause was patched and is pinned by e2e; no unverified risk can be named.

**Verification**
- Backend: 2412 passed, 4 skipped in 65 s; ruff check and format clean. Lab-hour tests each under 1 s (slowest 0.78 s).
- Frontend: typecheck, Vitest (414), `check:copy`, `lint:colours`, `build` pass. Playwright 224/224 on the rebuilt stack.
- Matrix audit: every I/O row has a passing test in `test_lab_hours.py` (current_lab_hour, digest and Student read included).
- Screenshots at 390 and 1280 px checked by eye (scratchpad, not committed): squares under the axis with tiered day/time labels, legend and list, form errors under each field, «Lagre Klasseøkt» secondary while the form is open.
- Migration 0035 is new and ran on the shared test databases.
- Implementation and review fixes were done in this context (caller's instruction), not by a step-03 subagent.

**Decisions taken in place of the founder**
- Lab hours save on their own, not with «Lagre Klasseøkt»; while their form is open «Lagre Klasseøkt» is secondary.
- Rules beyond the story: a Lab hour that has ended cannot change or go (409 `lab_hour_ended`); at most 12 hours; not ending in the past; place 1–120 characters, trimmed; times to the whole minute; overlapping Lab hours allowed (`current_lab_hour` gives the earliest started).
- Removal is a soft delete (`cancelled_at`); three notice kinds; a notice is left out of the digest when the Student left the Class, the Class is archived, the Lab hour is over, or an added/changed one was removed.
- One date with start and end time (no Lab hour across midnight). Removal is a «Fjern Labtimen» button inside the change form, one press, with «Studentene får beskjed på e-post.» above it.
- Half-typed date/time fields get «… er ikke fylt ut helt.» (`validity.badInput`), never read as empty.
- Legend joins distinct places («Datalab A2 og Rom 101»); ended Lab hours stay listed with «(ferdig)» and no «Endre».
- Datolinje tick labels now anchor by position (centred unless at an edge) so dates and Lab hours share one range.
- All new copy is [ASSUMPTION] (mail: «Ny Labtime …», «… er endret. Den er nå …», «Labtimen … er avlyst.»).

**Residual risks**
- A Lab hour added and removed before the day's digest gives a cancellation line for one the Student never saw; added + changed notices in one digest repeat the same values (needs a notify API to see sibling notices).
- The Assistant, locked and ended screens are tested with rewritten GETs; the real states are pinned at the api.
