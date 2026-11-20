---
title: 'Story 5.2: Set the four dates on the Datolinje'
type: 'feature'
created: '2026-11-19'
status: 'done'
baseline_revision: 'fc6c173b20b7557aea4b77b470a70348a253ee3d'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-5-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-5-1-create-class-session-classic-defaults.md'
warnings: ['oversized', 'multiple-goals']
deferred: []
---

<intent-contract>

## Intent

**Problem:** A Class session has no dates, so nobody knows when it starts or when each part is due, nothing can lock it, the Student has no «Neste frist», and the Lærerhjem's «Venter» and «Neste frist» are empty. Issue #98 also left two flaws on the same screens: the chain diagram scrolls at 390 px with no sign of it, and two sessions created in the same minute share one list label.

**Approach:** Add the four dates to `class_sessions` (migration 0033), set them through «Lagre Klasseøkt» with server-side order, past and passed-deadline rules, draw them as a read-only SVG Datolinje, add `is_locked`, the effective-deadline functions, the Student read and the Lærerhjem read. Fix #98 (a) with a shared scroll region that shows fading edges, and #98 (b) with a per-Class running number.

## Boundaries & Constraints

**Always:**
- Columns `start_at`, `play_deadline`, `debrief_deadline`, `test_deadline`: `timestamptz` NULL (a new session has none). CHECK for every pair that is set: start < play < debrief < test.
- Save body `ClassSessionSaveIn` gets `dates: DatesIn | None` (`extra="forbid"`; four `AwareDatetime | None`). Omitted means unchanged; present replaces all four. Times go in as UTC (the web app converts Europe/Oslo wall time), are stored UTC and are shown in Europe/Oslo.
- Rules, checked in the save transaction with the row locked, in this order (each answer changes nothing):
  1. 403, then 409 `class_archived` (5.1).
  2. `is_locked` and `ai_mode` differs from stored → 409 `session_locked`, `fields: {"ai_mode": "locked"}`.
  3. A changed date whose stored value has passed (`stored <= now`) → 409 `deadline_passed`, `fields: {name: "passed"}`. This covers the Start date.
  4. A changed date that is `<= now` → 422 `invalid_dates`, `fields: {name: "past"}`. Clearing a date after the lock → `{name: "required"}`.
  5. Order among the set dates → 422 `invalid_dates`, `fields: {later_name: "order"}` for the field that breaks the order (the later of the pair).
  Unchanged dates are never judged (a passed Start date can be resent).
- `sessions.service.is_locked(class_session, *, now)`: true once `start_at` is set and `<= now`. It is the one lock predicate. Story 5.11 adds `locked_at` inside it.
- `effective_debrief_deadline(user, class_session)` and `effective_test_deadline(user, class_session)` return the session's value. Epic 11 adds per-Student values inside them.
- A save that changes any date emits `session:<id>` and `user:<id>` once per registered Student of the Class (`classes.service.registered_students`). The registry entry `sessions.save` becomes {`session`, `user`}. A move after the start is the same write ("an extension for the whole Class session"), logged as `class_session_dates_moved` with ids only.
- `ClassSessionOut` adds `number`, the four dates, `locked`, `passed_dates` (names of set dates `<= now`) and `play_time_warning: bool`. The warning is true only when the config value `min_play_minutes_per_week` (default None, SM-11) is set, both dates are set, and `play_deadline - start_at < weeks × value`. While unset it is always false.
- `ClassSessionListItem` adds `number`: 1-based by creation order (UUIDv7 id) within the Class. The list label is «Klasseøkt {n}, opprettet {dato}».
- `GET /api/me/class-sessions` (new policy `class_sessions.read_enrolled`, any User): the sessions of Classes from `authz.classes_enrolled_by(user)`, each with `id`, `class_id`, `class_name`, `number`, `start_at`, `play_deadline`, the effective debrief and test deadlines, `next_deadline` (`{kind, at}` for the earliest of play/debrief/test after now, else null) and `obligatory`. It never returns Game settings, Weeks, demand or seed.
- `GET /api/lecturer-home/class-sessions` (policy `class_sessions.read`): scoped by `authz.classes_visible_to(user)` and only Classes that are not archived. `waiting`: per Class, its sessions missing any of the four dates (`class_id`, `class_name`, `sessions: [{id, number}]`). `next_date`: the earliest set date after now across those sessions, with `kind` ∈ {start, play, debrief, test}, `at`, `session_id`, `number`, `class_name`; null when none. Empty lists and null with no session.
- Web, Klasseøkt: a «Datoer» section in the right column (mockup 03): the Datolinje from the saved dates, then four labelled `datetime-local` fields (Startdato, Spillfrist, Debrieffrist, Testfrist) in Europe/Oslo, one column below 1024 px. Testfrist is prefilled to Debrieffrist + 7 days when the Lecturer sets the Debrieffrist and has not set the Testfrist by hand. «Lagre Klasseøkt» sends the fields. `invalid_dates` and `deadline_passed` show their reason under the field in question (TextField `error`) and the alert line; fields for passed dates and, for Assistants or archived Classes, all fields are read-only. The play-time warning is a text line, never blocking.
- Datolinje: hand-made SVG in `frontend/src/modules/sessions/date-line.tsx`, no chart library, one labelled tick per set date on one axis, read-only, `aria-hidden` with the fields as its text alternative (a visible note says so in text only if needed). Below 1024 px it scrolls inside its own region. With no saved date it shows «Ingen datoer ennå.».
- Shared `ScrollRegion` in `frontend/src/components/scroll-region.tsx`: a focusable labelled region with `overflow-x-auto` that shows a fading edge (token `paper` gradient, `aria-hidden`) on each side that has more content. Used by the chain diagram and the Datolinje.
- Lærerhjem: «Venter» lists «{klasse}: Klasseøkt {n} mangler datoer» as Lenker; «Neste frist» shows «{Datonavn}, Klasseøkt {n}, {klasse}» and the time in Europe/Oslo. Kept empty lines when there is nothing.
- All copy in `nb.ts` → `sessions` (new strings marked [ASSUMPTION]); «Startdato», «Spillfrist», «Debrieffrist», «Testfrist» are EXPERIENCE.md's.

**Never:** Lab hours (5.6), per-Student extensions (Epic 11), `locked_at` or the lock itself (5.11), editing settings (5.3+), refetch on events (6.4), the demand line under «Kundene» (#98's third item, Story 5.4), Student-facing UI (Epic 6), comparing DB time with host time in tests, touching the demo Class in tests.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Set four dates | owner, future, ordered | 200; stored UTC; `session` + `user` per registered Student | – |
| Save without `dates` | 5.1 body | 200; dates unchanged; no `user` emits | – |
| Out of order | play ≤ start | nothing stored | 422 `invalid_dates` `{play_deadline: order}` |
| Gap in the plan | start + debrief only, ordered | 200 | – |
| New date in the past | start ≤ now | nothing stored | 422 `{start_at: past}` |
| After start, move future deadline | start passed | 200; emits | – |
| After start, move passed deadline / start | stored ≤ now | nothing stored | 409 `deadline_passed` |
| After start, change AI mode | locked | nothing stored | 409 `session_locked` |
| After start, clear a date | locked | nothing stored | 422 `{name: required}` |
| Student read | registered Student | own Classes' sessions, no settings | outsider gets `items: []` |
| Lærerhjem read | owner/Assistant | waiting + next_date; archived Classes left out | Student 403 |
| Play time short | config set, span too short | `play_time_warning: true` | unset → false |

</intent-contract>

## Code Map

- `backend/app/modules/sessions/{models,repo,schemas,service,routes}.py` -- the 5.1 module; `save_session` (service.py) holds the transaction to extend; `get_session` builds `ClassSessionOut`.
- `backend/migrations/versions/0032_class_sessions.py` -- pattern for 0033; `backend/tests/test_migrations.py:69` `HEAD`.
- `backend/app/platform/authz.py:73,139,153` -- `POLICIES`, `classes_visible_to`, `classes_enrolled_by` (scope subqueries).
- `backend/app/platform/config.py:51` -- `Settings`; add `min_play_minutes_per_week: int | None` (PLACEHOLDER, SM-11).
- `backend/app/platform/events/registry.py:26` -- `sessions.save`.
- `backend/app/modules/classes/service.py:117,607,626` -- `list_classes` (names, archived), `registered_students`, `enrolled_classes` (names for the Student read).
- `backend/tests/sessions/test_class_sessions.py` -- fixtures `klass`, `clock` (NOW 2026-11-19 09:00 UTC via `auth.utcnow`), `emitted`, `call`, `rows`; new tests in `tests/sessions/test_dates.py`.
- Frontend: `src/modules/sessions/{api,sessions,class-session-page,class-sessions,chain-diagram}.tsx?`, `src/modules/classes/lecturer-home.tsx` (the two empty parts), `src/components/text-field.tsx` (error/hint/read-only), `src/modules/admin/audit.ts` (`formatTime`, Oslo), `src/copy/nb.ts:697`.
- API types: `cd backend && uv run python -m app.openapi ../frontend/src/lib/api/openapi.json`, then `npm run api:generate`.
- e2e: `frontend/e2e/class-session.spec.ts` (`freshClass`, `SIZES`), `e2e/support/classes.ts` (`freshLecturer`, `expectAccessible`).

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0033_class_session_dates.py`, `models.py`, `test_migrations.py` -- the columns and the order CHECK; HEAD 0033.
- `backend/app/platform/config.py`, `authz.py`, `events/registry.py` -- the setting, the policy, the topics.
- `backend/app/modules/sessions/{schemas,repo,service,routes}.py`, `README.md` -- dates, rules, `is_locked`, effective deadlines, numbers, the two reads.
- `backend/tests/sessions/test_dates.py` -- every matrix row through the routes; 5.1 tests updated for the new fields.
- `frontend/src/components/scroll-region.tsx` -- shared region with fading edges; used by `chain-diagram.tsx` and `date-line.tsx`.
- `frontend/src/modules/sessions/{dates.ts,dates.test.ts,date-line.tsx,date-fields.tsx}` -- Oslo ↔ UTC conversion, +7 days prefill, field errors, the SVG.
- `frontend/src/modules/sessions/{api.ts,class-session-page.tsx,class-sessions.tsx}`, `src/modules/classes/lecturer-home.tsx`, `src/copy/nb.ts`, regenerated `lib/api/{openapi.json,schema.ts}`.
- `frontend/e2e/class-session-dates.spec.ts` -- set four dates (Testfrist prefilled), save, Datolinje ticks, order error inline, Lærerhjem «Venter» and «Neste frist», labels distinct, fade edge present at 390 px, axe and no page scroll at 320/360/1440 px and 400 % zoom.

**Acceptance Criteria:**
- Given a Klasseøkt, when the Lecturer enters Startdato, Spillfrist and Debrieffrist and saves, then the Testfrist was prefilled 7 days after the Debrieffrist, the four dates are stored, and the Datolinje shows four labelled ticks in Europe/Oslo.
- Given a Spillfrist before the Startdato, when the Lecturer saves, then the reason shows under «Spillfrist» and nothing is stored.
- Given the Klasseøkt at 390 px, then the chain diagram's region shows a fading right edge while more of it lies to the right.
- Given two sessions of one Class created in the same minute, then the Klasse page shows two different labels.
- Given a Lecturer with a session lacking dates, when the Lærerhjem opens, then «Venter» names it; given one with dates, «Neste frist» names the next one.

## Spec Change Log

## Review Triage Log

### 2026-11-19 — Review pass
- verdicts: 31 findings — high 0, medium 4, low 20, false 4, maybe-false 3
- findings:
  - `[medium]` `[patch]` (blind) An unedited date stored with seconds counts as changed; once passed, every save from the screen answers `deadline_passed`. `judge_dates` now compares and stores to the whole minute; `test_dates_count_to_the_minute_the_fields_hold`.
  - `[low]` `[reject]` (blind) `locked` is not shown as a state on screen. The spec asks for read-only passed dates and the refusal copy; a lock banner belongs with the settings stories (5.3+).
  - `[low]` `[reject]` (blind) Date inputs are fixed at mount and not refreshed on refetch. Usual form behaviour (last save wins); refetch on events is Story 6.4.
  - `[low]` `[reject]` (blind) Field errors stay after the field is edited. They clear on the next save; tying them to sent values adds state for a cosmetic gain.
  - `[false]` `[reject]` (blind) The play-time warning shows only after a save. By design: the server computes it (no rules in the web app), Design Notes.
  - `[low]` `[reject]` (blind) A saved prefilled Testfrist no longer follows the Debrieffrist. A saved date counts as set; the prefill is for a date not yet set.
  - `[false]` `[reject]` (blind) Students see unfinished sessions. Dates are only written by a save, so a session the Lecturer never saved carries no data but its number and obligatory flag.
  - `[low]` `[reject]` (blind) The Student list is read outside the save transaction. A same-instant registration race, as accepted in Stories 4.10 and 5.1.
  - `[low]` `[reject]` (blind) The Lærerhjem parts show their empty lines when the read fails. The story asks for the parts to stay empty without an error; a retry would add a branch for a rare failure.
  - `[medium]` `[patch]` (blind) The Datolinje's scroll region was a focusable stop with nothing readable. The SVG is now `role="img"` named by the same dates in one line.
  - `[low]` `[patch]` (blind) Summer-time edges untested. `dates.test.ts` now covers the skipped and the repeated hour and `addDays` across the October change.
  - `[low]` `[patch]` (blind) The e2e `osloInput` could shift a day near a summer-time change. It now counts calendar days from today in Oslo.
  - `[low]` `[reject]` (blind) The 5.1 topic assertion became a subset check. The date test asserts the full `sessions.save` set.
  - `[low]` `[reject]` (blind) The DB CHECK is not exercised by an insert. The service refuses first; the migration test reads the constraint.
  - `[low]` `[reject]` (blind) `get_session` counts the number before the permission check. One cheap query; no data is returned to a refused caller.
  - `[false]` `[reject]` (blind) The Oslo time comes from `admin/audit`. `formatTime` is the project's shared Oslo formatter, already used by the Klasse page list (5.1).
  - `[medium]` `[patch]` (edge) Sub-minute stored dates: the same root cause as blind row 1.
  - `[low]` `[reject]` (edge) A co-owner's dates can be overwritten by stale inputs. As blind row 3.
  - `[maybe-false]` `[reject]` (edge) A half-typed `datetime-local` gives "" and clears the stored date. Needs a check of `validity.badInput` in each browser; if real it is low (before the start only, and visible in the field), so rejected.
  - `[low]` `[patch]` (edge) An order error fell on a passed, read-only date when only the earlier date changed. That case now answers `before` on the changed date (`test_an_earlier_date_set_after_a_later_one_passed_carries_the_reason`), with «Må komme før …».
  - `[low]` `[reject]` (edge) The registered-Student race. As blind row 8.
  - `[low]` `[patch]` (verification-gap) The Lærerhjem refresh after a save was untested. New e2e: save on the Klasseøkt, back by the breadcrumb, «Venter» is empty without a reload.
  - `[low]` `[patch]` (verification-gap) Passed, read-only and play-time UI untested. New e2e with a fulfilled GET (passed Startdato read-only with its hint, warning shown, save enabled); the archived-Class e2e now asserts read-only date fields.
  - `[medium]` `[patch]` (verification-gap, other) Sub-minute dates: as blind row 1.
  - `[low]` `[reject]` (intent) `user:<id>` is emitted on any date change, not only after the start. A superset: Students read the dates before the start too (Hjem «Neste frist»).
  - `[low]` `[reject]` (intent) A move after the start overwrites the column instead of a separate extension record. The story's extension is for the whole session; per-Student extensions are Epic 11.
  - `[maybe-false]` `[reject]` (intent) `session_locked` exists only for `ai_mode`. It is the only setting on the save route today; 5.3+ add theirs through `is_locked`.
  - `[low]` `[reject]` (intent) Only the `order` error is seen on screen in e2e. `dateErrors` covers every reason; the new e2e covers the passed hint.
  - `[false]` `[reject]` (intent) The Datolinje hides itself from assistive technology. Fixed by blind row 10.
  - `[low]` `[reject]` (intent) The fade is checked by attribute, not pixels. Screenshots at 390 px were checked by eye.
  - `[maybe-false]` `[reject]` (intent) The running number goes beyond the label fix. It is the label's source and the Lærerhjem names sessions by it; a client-side index would differ between screens.

## Design Notes

- Dates travel with «Lagre Klasseøkt» because choices take effect only on save (EXPERIENCE.md). The route stays one, so after the lock it refuses only a changed locked field (`session_locked`) and still takes dates.
- `passed_dates` and `locked` come from the server's clock, so the screen never compares times itself.
- The Datolinje is `aria-hidden`: the labelled fields directly below carry the same values (UX-DR51's text alternative).

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/sessions -q` -- pass, each test under 1 s.
- `cd backend && uv run pytest -q && uv run ruff check . && uv run ruff format --check .` -- pass.
- `cd frontend && npm run typecheck && npm test && npm run check:copy && npm run lint:colours && npm run build` -- pass.
- `cd frontend && npx playwright test` against `timeout 900 docker compose up -d --build --wait proxy worker-batch` -- pass.

## Auto Run Result

Status: done

**Summary.** A Faglærer sets Startdato, Spillfrist, Debrieffrist and Testfrist on the Klasseøkt (Europe/Oslo fields; the Testfrist is prefilled 7 days after the Debrieffrist) and saves them with «Lagre Klasseøkt». The Datolinje draws the saved dates. The api keeps the order, refuses new dates in the past, moves only deadlines that have not passed after the start, and locks settings once the Start date has passed (`is_locked`). Students get `GET /api/me/class-sessions` with the next deadline, the Lærerhjem gets «Venter» and «Neste frist». Issue #98: the chain diagram and the Datolinje show a fading edge while they scroll, and list labels carry a running number.

**Files changed**
- Backend: migration `0033_class_session_dates.py` (four columns and an order CHECK); `sessions/{models,repo,schemas,service,routes}.py` and `README.md` (dates, rules, `is_locked`, `effective_*_deadline`, numbers, Student and Lærerhjem reads); `platform/config.py` (`min_play_minutes_per_week`, unset), `authz.py` (`class_sessions.read_enrolled`), `events/registry.py` (`sessions.save` → session, user); tests `sessions/test_dates.py` (new, 18), `test_class_sessions.py`, `test_migrations.py` (HEAD 0033).
- Frontend: `components/scroll-region.tsx` (new, fading edges); `sessions/{dates,dates.test,date-line,date-fields,lecturer-home-sessions}.ts(x)` (new); `sessions/{api,class-session-page,class-sessions,chain-diagram}.tsx`; `classes/lecturer-home.tsx`; `copy/nb.ts`; regenerated `lib/api/{openapi.json,schema.ts}`; e2e `class-session-dates.spec.ts` (new, 11), `class-session.spec.ts`, `homes.spec.ts` (Lærerhjem links may now lead to a Klasseøkt), `support/classes.ts` (`freshClass`).

**Review findings.** 31: 0 high, 4 medium, 20 low, 4 false, 3 maybe-false. Patched: minute precision (3 rows, one root cause), the Datolinje's accessible name, `before` attribution, summer-time unit tests, the e2e date helper, two new e2e tests and the read-only assertion. Deferred: none. Rejected: the rest, each with its reason above.

**Follow-up review recommended: false.** Two medium entries were patched (minute precision; the Datolinje's name), which would count toward a follow-up, but both now have covering tests (api test; axe and e2e), so no unverified risk can be named. No high.

**Verification**
- Backend: 2315 passed in 57 s; ruff check and format clean. New tests each under 1 s (a first migration test I wrote took 10 s and was folded into an existing upgrade test).
- Frontend: typecheck, Vitest (378), `check:copy`, `lint:colours`, `build` pass. Playwright 193/193 on the rebuilt stack (before the last review patches; the session specs, 19 tests, passed again after them).
- Screenshots at 390 and 1280 px checked by eye: fading edges visible at 390 px; the Datolinje fits the 1280 px column.
- Migration 0033 is new; the shared test database was migrated to it in this run.
- Implementation was done in this context (caller's instruction); the four review layers ran as subagents and their reports were read from their transcripts, since no completion notice arrived.

**Decisions taken in place of the founder**
- Dates travel with «Lagre Klasseøkt»; without `dates` they stay. Partial plans are allowed before the start; after the start no date may be cleared.
- Error codes: 422 `invalid_dates` (`past`, `order`, `before`, `required`), 409 `deadline_passed` (also for a passed Start date), 409 `session_locked`. Dates count to the minute.
- `user:<id>` goes to every registered Student on any date change, before or after the start.
- The Student's next deadline leaves out the Start date; the Lærerhjem's next date includes it. «Venter» means missing any of the four dates; archived Classes are left out.
- The play-time warning is a server flag from saved dates; the setting `MIN_PLAY_MINUTES_PER_WEEK` is unset.
- The running number is server-side per Class (oldest = 1); labels «Klasseøkt N, opprettet …». Issue #98 (a) solved with fading edges, also on the Datolinje.
- Draft copy marked [ASSUMPTION] in `nb.ts`; the mockup's «Debrief-frist» was written «Debrieffrist» as EXPERIENCE.md has it.

**Residual risks**
- A half-typed `datetime-local` field reads as empty and would clear that date before the start.
- The fields show the browser's locale format (en-US in Playwright); a Norwegian browser shows Norwegian.
- Issue #98's third item (demand under «Kundene») is left for Story 5.4.
