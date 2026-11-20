---
title: 'Story 5.7: Mark the Class session obligatory and set the Inactivity limit'
type: 'feature'
created: '2026-11-20'
status: 'done'
baseline_revision: '9042fd4982a98e03340adacee4a542aedc9f428c'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-5-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-5-6-add-lab-hours.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** The Klasseøkt shows «Obligatorisk» and the Inactivity limit read-only, so a Lecturer can neither mark the Class session as a course requirement (with the required share of Weeks) nor change how long a group waits before an AI player takes over (FR-17, FR-36).

**Approach:** Add a shared Bryter, make «Obligatorisk», «Andel uker som kreves» and «Ventetid før KI tar over» editable drafts that take effect on «Lagre Klasseøkt», store the share in a new column, enforce the rules and the Start-date lock in `save_session`, tell each registered Student once through a new digest notice when the mark is switched on, and expose `sessions.service.required_share`.

## Boundaries & Constraints

**Always:**
- Migration 0036: `class_sessions.required_share_percent` int NOT NULL, CHECK `BETWEEN 1 AND 100` (`ck_class_sessions_required_share`); existing rows backfilled with 80, then no server default. `create_session` stores `get_settings().completion_default_share_percent` (new config `COMPLETION_DEFAULT_SHARE_PERCENT`, `Field(80, ge=1, le=100)`, PLACEHOLDER FR-17).
- `ClassSessionSaveIn` gains `obligatory: bool | None`, `required_share_percent: int | None`, `inactivity_limit_hours: int | None` (schema guard `le=8760`); None keeps the stored value. `ClassSessionOut` gains `required_share_percent`.
- Rules in `save_session`, in the existing order: once locked, any of the three that differs from the stored value joins the 409 `session_locked` `fields` (`"locked"`); then 422 `invalid_session_values` with `fields`: `inactivity_limit_hours` `below_minimum` (< `MIN_INACTIVITY_LIMIT_HOURS` 20), `required_share_percent` `out_of_range` (outside 1..100). Unchanged values are never judged. A non-integer is the schema's 422.
- Notice: when a save turns `obligatory` from false to true, in the same transaction `notify.enqueue(s, student, "class_session_obligatory", f"class_session_obligatory:{session_id}:{now.isoformat()}:{student}", ref=session_id)` per registered Student (`classes.service.registered_students`); `notify` emits `user:<id>`. Kind `digest` in `messaging.delivery.KINDS` (literal name, lazy resolver as the Lab hour kinds), txt+html Jinja2 templates in bokmål that never name the number of Weeks, «Beer Game» or «bullwhip». Resolver `sessions.service.obligatory_mail_context` reads at send time: `{class_name}`; None when the session is gone or no longer obligatory, the Class is archived, or the User is no longer a registered Student. Turning it off tells nobody.
- `sessions.service.required_share(class_session) -> int`: the stored percent (1..100), whether or not the session is obligatory; the one source for Story 8.9 and Epic 13. `GET /api/me/class-sessions` keeps `obligatory`.
- Web: `frontend/src/components/switch.tsx` Bryter: `<button type="button" role="switch" aria-checked>`, track `rounded-full` 52×28, on: `ink` fill with `paper` knob at the right; off: `paper` with `ink-muted` border and `ink-muted` knob at the left (position, not colour, carries the state); visible state text beside, inside the 44 px target; accessible name from `labelledBy` plus the state text; shared focus ring; Space/Enter toggle (native button).
- Klasseøkt «Obligatorisk» column, editable while `can_manage && !locked`: heading «Obligatorisk», Bryter with state text «Ja, står i emneplanen» / «Nei», no dialog. When on: help «Studentene ser at øvelsen er obligatorisk.» (mockup 03) and Tekstfelt «Andel uker som kreves» (hint «Et helt tall fra 1 til 100 %.»), error «Skriv et helt tall fra 1 til 100.» on blur, on save, or from the api. Read-only: the state text, and when on «Andel uker som kreves: 80 %».
- «Ventetid før KI tar over» is a Tekstfelt inside the open settings block (replacing its read-only row there), prefilled with the stored hours, help «Minst 20 timer. Kortere ventetid kan bare gjelde spill som er i rommet i en Labtime.» always visible; empty, decimal, non-digit or under 20 shows «Skriv et helt antall timer, 20 eller mer.» with `role="alert"` on blur or on «Lagre Klasseøkt» (nothing sent then), or from the api. Sent only while the block is open; closed, the list row stays «24 t, så KI overtar».
- A client check that fails blocks the save without a request; `invalid_session_values` from the api maps to its field; failure keeps the values. All new copy in `nb.ts`, [ASSUMPTION] where not from EXPERIENCE.md / mockup 03 / the story.

**Never:** Completion rules or any use of the share (Epic 13, Story 8.9); Takeover (Epic 8); a confirmation dialog; a notice when switched off or when saved on again; names or text in `notices`; a new sweeper; touching the demo Class; comparing DB time with host time; editing `sprint-status.yaml`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Defaults | new session | `obligatory` false, share 80, limit 24 | – |
| Switch on | 2 registered Students; `obligatory: true` | stored; 2 `class_session_obligatory` notices (ref = session); `session` + 2 `user` events | – |
| Saved on again | `obligatory: true` while on | no new notice | – |
| Off | `obligatory: false` | stored; no notice | – |
| Share | 1, 100 | stored | – |
| Share out of range | 0, 101 | nothing stored | 422 `invalid_session_values` `{required_share_percent: out_of_range}` |
| Limit | 20, 48 | stored | – |
| Limit too low | 19 | nothing stored | 422 `{inactivity_limit_hours: below_minimum}` |
| Decimal | 24.5 | nothing stored | 422 (schema) |
| Locked, changed | any of the three differs | nothing stored | 409 `session_locked` naming each |
| Locked, unchanged | same values | 200 | – |
| Student read | obligatory on | `obligatory: true` | – |
| Digest | on, sweep in the day | one mail naming the Class | off before the sweep → no mail |

</intent-contract>

## Code Map

- `backend/app/modules/sessions/models.py` -- add column + CHECK; `MIN_INACTIVITY_LIMIT_HOURS` (18) exists; add `SHARE_RANGE` constants.
- `backend/migrations/versions/0036_class_session_required_share.py` (new, after 0035).
- `backend/app/platform/config.py:121` -- `completion_default_share_percent`.
- `backend/app/modules/sessions/schemas.py` -- `ClassSessionSaveIn` (223), `ClassSessionOut` (141).
- `backend/app/modules/sessions/service.py` -- `create_session` (433), `get_session` (518), `save_session` (592: locked `refused` block 637, students fetched 618), `repo.save` call (693); new `InvalidSessionValues(_FieldsError)`, `OBLIGATORY_NOTICE`, `required_share`, `obligatory_mail_context` (pattern `lab_hour_mail_context` 1077).
- `backend/app/modules/sessions/repo.py:155` `save` -- accept the three values.
- `backend/app/modules/sessions/routes.py:103` -- pass fields, map `InvalidSessionValues` to 422; docstring. `README.md` -- Story 5.7.
- `backend/app/modules/messaging/delivery.py:80-97` -- `OBLIGATORY_KIND` literal + lazy resolver.
- `backend/app/platform/email/templates/kinds/class_session_obligatory.{txt,html}.j2` (new).
- `backend/app/platform/events/registry.py:24` -- comment only (`sessions.save` already `{session, user}`).
- Tests: new `backend/tests/sessions/test_obligatory.py` (helpers from `test_dates.py`: `new_session`, `save`, `student_of`, `at`, `refusal`, `PLAN`; `test_lab_hours.py`: `notices`, `sweep_at`, `emitted`; `tests/messaging/helpers.py` `mails`); `tests/test_migrations.py` head → 0036.
- `frontend/src/components/switch.tsx` (new) + case in `components.test.tsx`; `text-field.tsx` -- optional `errorAlert` (error line `role="alert"`).
- `frontend/src/modules/sessions/obligatory.ts` (new, + test): `wholeHoursProblem`, `shareProblem`, body helpers, api-field mapping.
- `frontend/src/modules/sessions/choices.ts` -- `ChoicesDraft` gains `obligatory`, `requiredShare` (text); `choicesBody` sends them.
- `frontend/src/modules/sessions/class-session-page.tsx` -- `Choices` third column (388), save flow (123), inactivity draft passed to `SettingsBlock`; `settings-form.tsx:104` replace `ReadOnlyRows only=[inactivity]` with the field. `api.ts` `saveClassSession` takes extra body. `copy/nb.ts:859` `choices` and `edit`; regenerate `lib/api/{openapi.json,schema.ts}`.
- `frontend/e2e/class-session-obligatory.spec.ts` (new), patterns of `class-session-choices.spec.ts`.

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0036_*.py`, `models.py`, `config.py`, `schemas.py`, `repo.py`, `service.py`, `routes.py`, `README.md` -- column, rules, lock, notice, `required_share`, mail context.
- `messaging/delivery.py`, two templates, `events/registry.py` comment -- digest kind.
- `backend/tests/sessions/test_obligatory.py`, `tests/test_migrations.py` -- every matrix row through the routes, `required_share`, the digest and its omission.
- `frontend/src/components/switch.tsx`, `text-field.tsx`, `components.test.tsx` -- Bryter.
- `frontend/src/modules/sessions/obligatory.ts(+test)`, `choices.ts`, `class-session-page.tsx`, `settings-form.tsx`, `api.ts`, `copy/nb.ts`, regenerated api types -- the screen.
- `frontend/e2e/class-session-obligatory.spec.ts` -- switch on by keyboard, share and limit errors, save and reload, locked/Assistant read-only via rewritten GET, axe at 320/360/1440 and 400 % zoom.

**Acceptance Criteria:**
- Given the Klasseøkt before the Start date, when the Lecturer switches «Obligatorisk» on (mouse or keyboard), then it reads «Ja, står i emneplanen», `aria-checked="true"`, «Andel uker som kreves» shows 80, no dialog opens, and nothing is stored until «Lagre Klasseøkt».
- Given a share of 0 or a Ventetid of 19, «2,5» or empty, when the field is left or «Lagre Klasseøkt» pressed, then the reason shows under the field (Ventetid's with `role="alert"`) and no request is sent.
- Given a saved switch-on, then each registered Student gets one `class_session_obligatory` notice and the next digest mail says the Class session is obligatory.
- Given a locked session or an Assistant, then the three are text only, and the api answers 409 `session_locked` for a changed value.

## Spec Change Log

## Review Triage Log

### 2026-11-20 — Review pass
- verdicts: 35 findings — high 0, medium 1, low 31, false 3, maybe-false 0
- findings:
  - `[low]` `[reject]` (blind) The web accepts a Ventetid over 8760 h, which the schema answers with a generic 422. Nobody types a limit over a year; a further bound and message would add a rule and copy the story does not have.
  - `[low]` `[patch]` (blind) Lax ints let `"48"`, `true` and `48.0` through. The share and the limit are now `StrictInt`; `test_a_limit_or_share_that_is_no_json_integer_is_refused` pins `invalid_request` for each.
  - `[low]` `[reject]` (blind) On, off and on again before one digest repeats the line. Rare; needs a way to see sibling notices that `platform/notify` lacks (as 5.6). Residual risk.
  - `[low]` `[reject]` (blind) The mail names the Class, not the Class session, the share or a link. The Lab hour mails name the Class the same way; the share's meaning is Epic 13's.
  - `[false]` `[reject]` (blind) Students never see the share. The story returns the obligatory flag only; Completion and its share reach Students in Epic 13.
  - `[low]` `[reject]` (blind) One roster query per notice at send time. Same accepted pattern as 5.6; one notice per Student per switch-on.
  - `[low]` `[reject]` (blind) Students are read before the write transaction. Same pattern as 5.2 and 5.6; the Student read still shows the flag.
  - `[low]` `[patch]` (blind) The share error is not announced. It now has `role="alert"` like the Ventetid's.
  - `[low]` `[reject]` (blind) A blocked save does not move focus. The screen's rule is that a failed save keeps focus; the reasons stand under their fields.
  - `[false]` `[reject]` (blind) The Ventetid hint promises a missing feature. The line is EXPERIENCE.md's; «I rommet» is Epic 8's.
  - `[low]` `[reject]` (blind) `required_share` answers even when not obligatory. Deliberate and documented: the share is stored either way, the mark says whether it applies (Epic 13 reads both).
  - `[low]` `[reject]` (blind) The backfill is 80 whatever the config says. The config is a placeholder of 80; only rows stored before 0036 are concerned.
  - `[low]` `[patch]` (blind) `ReadOnlyRows` docstring stale. Docstring corrected; the "" errors are shown in the open block.
  - `[low]` `[patch]` (blind) `shareChecked` stays true across a toggle. A blocked save now marks only the fields on screen as checked. The stale api error until the next save is rejected: the web check blocks those values before the api sees them.
  - `[low]` `[patch]` (blind) Leftovers. Redundant parentheses removed. The `_obligatory_context` wrapper stays: it is the lazy call-time lookup the import cycle needs (as the Lab hour kinds).
  - `[low]` `[patch]` (blind) Test gaps. The 422 tests now pin the error code; a Class without Students and a share sent while off are ordinary paths of the same code and are not added.
  - `[low]` `[reject]` (edge) Ventetid over 8760. As blind row 1.
  - `[low]` `[reject]` (edge) Values beyond the schema guards get a generic 422. Only reachable outside the screen; the guards keep the integer in range.
  - `[low]` `[patch]` (edge) Lax ints. As blind row 2.
  - `[low]` `[reject]` (edge) Repeated digest line. As blind row 3.
  - `[low]` `[reject]` (edge) Student registering mid-save. As blind row 7.
  - `[low]` `[reject]` (edge) Stale api error under a corrected field. As blind row 14.
  - `[low]` `[patch]` (edge) Share error shown before the field is left. As blind row 14.
  - `[false]` `[reject]` (edge) An Assistant gets 403, not 409. The 409 clause is the locked case; FR-5's 403 is the Assistant's answer on every sessions route.
  - `[low]` `[patch]` (edge) No Assistant screen case. Added e2e «an Assistant reads the mark and the share as text, with no control».
  - `[low]` `[reject]` (edge) Several notices for one session. As blind row 3.
  - `[medium]` `[patch]` (verification-gap) The archived-Class omission of the mail was untested. Added `test_an_archived_class_gets_no_obligatory_mail`.
  - `[low]` `[patch]` (verification-gap) 0036's backfill and bounds were untested. The migration test now stores a row at 0035, upgrades and reads 80, and inserts 0, 1, 100 and 101 against the CHECK.
  - `[low]` `[reject]` (verification-gap, other) Ventetid over 8760. As blind row 1.
  - `[low]` `[reject]` (intent) The locked screen is tested with a rewritten GET. The real lock is pinned at the api, as in 5.3 to 5.6.
  - `[low]` `[reject]` (intent) The api refusal on screen uses a stubbed 422. The web blocks those values first; the codes are pinned in `test_obligatory.py`.
  - `[low]` `[reject]` (intent) The Ventetid is edited behind «Endre spillinnstillinger». Deliberate (mockup 03 lists it among the settings); the help line is always shown with the field.
  - `[low]` `[reject]` (intent) A decimal gets the generic 422. The story's code is not named; `invalid_request` is now pinned.
  - `[low]` `[patch]` (intent) Enter was not tested on the Bryter. The e2e now toggles it with Enter both ways.
  - `[low]` `[reject]` (intent) The backfill is a fixed 80. As blind row 12.

## Design Notes

- The dedupe key holds the moment of the switch, so off→on later tells again; the resolver drops the notice if the mark is off at send time.
- The Inactivity limit sits with the other settings (mockup 03 lists it there), so it opens with «Endre spillinnstillinger»; it is not a `GameSettings` field, so the engine check is not asked about it and the web checks the floor itself.

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/sessions/test_obligatory.py tests/test_migrations.py -q` -- pass, each under 1 s.
- `cd backend && uv run pytest -q && uv run ruff check . && uv run ruff format --check .` -- pass.
- `cd frontend && npm run typecheck && npm test && npm run check:copy && npm run lint:colours && npm run build` -- pass.
- `cd frontend && npx playwright test` against `timeout 900 docker compose up -d --build --wait proxy worker-batch` -- pass.

## Auto Run Result

Status: done

**Summary.** The Klasseøkt's «Obligatorisk» is now a Bryter (new shared `components/switch.tsx`: `role="switch"`, ink track, knob position carries the state, 44 px target). When it is on, «Ja, står i emneplanen», the mockup's help line and «Andel uker som kreves» (1 to 100 %, default from `COMPLETION_DEFAULT_SHARE_PERCENT` = 80) appear. «Ventetid før KI tar over» is a field in the open settings block, with the help line and «Skriv et helt antall timer, 20 eller mer.» (`role="alert"`). All three take effect on «Lagre Klasseøkt». The api judges a changed share (`out_of_range`) and limit (`below_minimum`) as 422 `invalid_session_values`, and answers 409 `session_locked` for any change once locked. Switching the mark on enqueues one `class_session_obligatory` digest notice per registered Student (ids only; `user:<id>` from notify). Its mail is read at send time and left out if the mark is off, the Class is archived or the Student has left. `sessions.service.required_share` is the one source for Story 8.9 and Epic 13.

**Files changed**
- Backend: `migrations/versions/0036_class_session_required_share.py` (new); `sessions/{models,schemas,repo,service,routes}.py`, `README.md`; `platform/config.py`; `messaging/delivery.py`; templates `class_session_obligatory.{txt,html}.j2` (new); `events/registry.py` (comment). Tests: `tests/sessions/test_obligatory.py` (new), `test_migrations.py` (head 0036, backfill/CHECK test), `test_class_sessions.py` (`obligatory` is now a valid field).
- Frontend: `components/switch.tsx` (new), `text-field.tsx` (`errorAlert`), `components.test.tsx`; `sessions/obligatory.ts` + test (new), `choices.ts` + test, `class-session-page.tsx`, `settings-form.tsx`, `api.ts`; `copy/nb.ts`; regenerated `lib/api/{openapi.json,schema.ts}`; e2e `class-session-obligatory.spec.ts` (new).

**Review findings.** 35: 0 high, 1 medium, 31 low, 3 false. 14 patched (1 medium, 13 low): untested archived-Class mail omission, migration backfill and bounds, StrictInt for share and limit, `role="alert"` on the share error, the checked flags, Enter on the Bryter, an Assistant e2e case, a docstring and the error codes in tests. Nothing deferred. The rest were rejected, each with its reason in the triage log.

**Follow-up review recommended: false.** One medium was patched and is pinned by a test, and no high was found.

**Verification**
- Backend: 2435 passed, 4 skipped in 63 s. ruff check and format are clean. New tests each run under 1 s (slowest 0.52 s), except the 0036 migration test at 1.67 s, which is in line with the other migration tests.
- Frontend: typecheck, Vitest (422), `check:copy`, `lint:colours` and `build` pass. Playwright passed 234/234 on the rebuilt stack. The new spec's 10 tests take 8.4 s in parallel.
- Matrix audit: every I/O row has a passing test in `test_obligatory.py`.
- Screenshots at 390 and 1280 px were checked by eye (scratchpad, not committed). The Bryter matches mockup 03: an ink track with the knob at the right and the label beside it, the share field below, and the Ventetid error under its field.
- Migration 0036 is new and ran on the shared test databases. It was not changed after it ran.
- Implementation and review fixes were done in this context (caller's instruction), not by a step-03 subagent.

**Decisions taken in place of the founder**
- The state text beside the Bryter reads «Nei» when off. The help line «Studentene ser at øvelsen er obligatorisk.» is from mockup 03 and shows only when the switch is on.
- The share field shows only while the mark is on. It is stored and kept when the mark goes off. `required_share` returns it whether or not the session is obligatory.
- The Inactivity limit is edited inside «Endre spillinnstillinger», where mockup 03 lists it, and is sent only while that block is open.
- Notify rule: one notice per Student each time the mark goes off→on. The switch moment is in the key. Switching off tells nobody, and the mail is dropped if the mark is off at send time.
- Mail copy: «Øvelsen i Klassen {klasse} er obligatorisk. Den står i emneplanen.» [ASSUMPTION]. Further [ASSUMPTION] copy: the share's hint, its error and its read-only line, and «Klasseøkten ble ikke lagret. Se feltene.».
- Rows that existed before 0036 get 80. The schema accepts at most 8760 h as a guard. Non-integers get the generic 422 `invalid_request`.
- The Bryter's off knob is `ink-secondary`, because the colour-pair table has no entry for `ink-muted`.

**Residual risks**
- Switching on, off and on again before one digest gives two identical lines in it.
- The locked and Assistant screens are tested with rewritten GETs; the real states are pinned at the api.
