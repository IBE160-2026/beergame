---
title: 'Story 13.2: Studentside with the «Fullføring» block'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: '6c6850d355acdc7cb4f3938bb5cb4a75712f3634'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-13-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-13-1-completion-computed-in-one-place-shown-on-hjem.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** The Studentside (Story 8.9) holds only «Tilrettelegging» and «Frister», for Lecturers only. Staff cannot see on one page what a Student has done, nor the Completion status per step with the share behind it, so a shortfall means opening five screens (FR-63, FR-17).

**Approach:** Add one read, `GET /api/class-sessions/{id}/students/{user_id}/record` (`getStudentRecord`), in `modules/reports`, for the Lecturers and Assistant lecturers of the Class (new policy `student_page.read`). It gathers each part through the owning module's `service.py` and the Completion status through `reports.service.completion_status`, plus the participation signals from a new pure `analysis.participation`. The web Studentside renders it as blocks above the unchanged «Tilrettelegging» and «Frister», which stay Lecturer-only (`getStudentPage`).

## Boundaries & Constraints

**Always:**
- Reach: `sessions.service.student_target(user, session, student, action)` with `student_page.read` (staff roles owner + assistant in the Class); None → 403 `forbidden`, the same for a missing Class session, a User who is not a Student of the Class now, a Class outside the caller's scope and an Admin without a staff role (FR-5). Response `Cache-Control: no-store`.
- `reports` imports other modules only through their `service.py` (test_imports rule); no table access from `reports`.
- Fullføring: rows in order Klassespill, Debrief, Debrief-quiz, Replay, Individuell test, each with «gjort»/«ikke gjort» in text and, when recorded, the date. Klassespill share line «Bestilte i 70 % av ukene.» plus « Kravet er 80 %.» when obligatory; «20 % av ukene ble spilt i utspillingen ved Spillfristen.» only when the playout share > 0. Requirement line («Kravet er oppfylt.» / «Kravet er ikke oppfylt.») only when obligatory. All from `completion_status`.
- Participation (information only, labelled so): time spent = sum of `ordered_at - opened_at` over the Student's own Orders (own = `decided_by = student`, reason not in `completion.NOT_OWN_REASONS`), whole seconds; constant = every own Order after the Guided Weeks has the same quantity, None with fewer than two such Orders. Never an input of `analysis.completion`.
- Game part: number, Role, play status (finished / ended early / running / not started) and a link to its Spillinnsikt. Debrief part: the Explanation text, the summary's finished date and lateness, with a link to the existing staff Debrief summary page; quiz attempts (number, time, passed). Replay: whether there is one, finished date, link to its Spillinnsikt. Individual test: attempt status, submitted time and which parts hold content (no answers). AI assessment: `off` when the session's switch is off, else `not_ready` (the 12.5 block replaces this slot at merge). Report slot: empty element `data-report-slot` (13.12 fills it).
- The page refetches on `session:<id>` (key under `["class-sessions","students",session,user]`).
- Links to the Studentside: Spillinnsikt names for every staff member (not only Lecturers); the Roster row of a registered Student gets one «Studentside» link per Class session of the Class.
- Copy in `frontend/src/copy/nb.ts`, draft `[ASSUMPTION]`.

**Never:** no migration or new table; no change to `analysis.completion`'s rules or to step events; no correction form, Oppfølgingsspill or report link (13.3, 13.4, 13.12); no test answers or AI text shown; no Indicative letter field in any staff response; no rebuild of «Tilrettelegging»/«Frister»; no chart.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Lecturer | owner of the Class | 200 record, `can_manage` true; page shows all blocks incl. Tilrettelegging | — |
| Assistant | assistant of the Class | 200 record, `can_manage` false; no Tilrettelegging/Frister | — |
| Outsider | Lecturer of another Class / Admin / Student | — | 403 `forbidden`, same body as unknown Student |
| No game yet | before lock | completion rows «ikke gjort», game part «Ikke noe spill ennå.», participation empty | — |
| Not obligatory | `obligatory=false` | no requirement line, no «Kravet er» | — |
| Playout | 2 of 10 Weeks `playout` | «20 % av ukene ble spilt i utspillingen ved Spillfristen.» | — |
| Constant | own Orders after guided all 4 | constant true | fewer than 2 → None |
| AI off | switch disabled | AI part «KI-vurdering er slått av for denne klasseøkten.» | — |

</intent-contract>

## Code Map

- `backend/app/platform/authz.py` -- `POLICIES`, `CLASS_STAFF_ROLES`: add `student_page.read` (LECTURER, ASSISTANT / OWNER, ASSISTANT_STAFF).
- `backend/app/modules/sessions/service.py:2100` `StudentTarget`, `student_target` (action fixed to `class_sessions.manage`; add `action` parameter), `:826` `_class_for`, `:2219` `class_staff_may`, `required_share`, `get_adjustment`; `repo.number_of`.
- `backend/app/modules/sessions/adjustments.py` -- the 8.9 page (`student_page`, `_page`); unchanged.
- `backend/app/modules/reports/service.py` -- `completion_status`; `scope.py`; README.
- `backend/app/modules/debrief/service.py:1252` `staff_summary(user, session, student)` -- Explanation, summary, quiz attempts for staff; reuse as is.
- `backend/app/modules/games/service.py:507` `student_game`, `:544` `seat_log`, `:628` `play_status`, `:650` `finished_at`; `repo.py:1151` `seat_log` query pattern; `models.py` `seat_weeks` (`order`, `opened_at`, `ordered_at`).
- `backend/app/modules/replay/service.py:65` `replay_game_of(session, user, class_session)`.
- `backend/app/modules/tests/service.py:234` `parts_with_content`, `:270` `attempt_status`; `models.test_attempts.submitted_at`.
- `backend/app/modules/assessment/service.py:57` `switch_of(session, class_session_id)`.
- `backend/app/analysis/completion.py` -- `NOT_OWN_REASONS`, `CompletionStatus`.
- `backend/app/modules/classes/service.py:429` `RegistrationOut` builder; `schemas.py:240`.
- `backend/app/main.py:105` routers.
- `backend/tests/test_imports.py:220` reports rule; `backend/tests/reports/` (13.1 fixtures); `backend/tests/sessions/test_adjustment.py` (Studentside api tests pattern); `backend/tests/games/helpers.py`.
- `frontend/src/modules/reports/student-page.tsx` (page of blocks, `Editing` one-form rule), `api.ts` (`studentPageKey`), `adjustment-block.tsx` (block style).
- `frontend/src/modules/games/insight-page.tsx:211` link gated by `canAdjust`.
- `frontend/src/modules/classes/registration-status.tsx:536` Roster rows; `frontend/src/modules/sessions/api.ts:34` `useClassSessions`.
- `frontend/src/modules/identity/homes.ts` `studentPagePath`, `gameInsightPath`, staff debrief summary path (`:116`).
- `frontend/src/lib/api/topics.ts` -- `["class-sessions","students",id]` already under `session`.
- `frontend/e2e/tilrettelegging.spec.ts`, `completion.spec.ts`, `support/live-game.ts`, `support/classes.ts`.

## Tasks & Acceptance

**Execution:**
- `backend/app/analysis/participation.py` + `backend/tests/analysis/test_participation.py` -- pure `participation(rows, guided_weeks) -> Participation(seconds, own_orders, constant)`; table tests; a test that the same Decision log with other times and quantities gives the same `completion(...)` but another participation.
- `backend/app/modules/games/service.py` + `repo.py` -- `seat_timing(session, game_id, role)` rows (week, decided_by, reason, order, seconds).
- `backend/app/modules/tests/service.py` -- `attempt_summary(user_id, class_session_id)` (status, submitted_at).
- `backend/app/modules/sessions/service.py` -- `student_target(..., action=...)`.
- `backend/app/platform/authz.py` -- the policy.
- `backend/app/modules/reports/{schemas,studentside,routes}.py`, README, `app/main.py` -- the record read and route.
- `backend/app/modules/classes/{schemas,service}.py` -- `user_id` on registered Roster rows.
- `backend/tests/reports/test_studentside.py` -- access matrix (owner, assistant, other Lecturer, Admin, Student, unknown Student), parts, participation, AI off/not ready, no letter key, completion equality with `completion_status`.
- `frontend/src/copy/nb.ts`, `modules/reports/{api.ts,student-page.tsx,record-blocks.tsx,completion-block.tsx,record.ts,record.test.ts}` -- blocks; `npm run api:generate`.
- `frontend/src/modules/games/insight-page.tsx`, `modules/classes/registration-status.tsx` -- the links.
- `frontend/e2e/studentside.spec.ts` -- Lecturer and Assistant open the page from Spillinnsikt and the Roster; Fullføring rows; live refetch on a recorded step; axe and reflow at 320, 1440 and 200 % text.

**Acceptance Criteria:**
- Given an Assistant lecturer of the Class, when they open a Student from Spillinnsikt, then the Studentside shows the record blocks and no «Tilrettelegging»/«Frister».
- Given the page open, when the Student's step is recorded, then the Fullføring row changes without reload.
- Given a non-staff caller, when they request the record, then 403 `forbidden` whether or not the Student exists.

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
- layers: Blind Hunter and Edge Case Hunter, as the lane brief directs: two layers, or four only when the completion rules change, and they do not change here. The verification-gap and intent-alignment layers were skipped.
- verdicts: 24 findings — high 0, medium 0, low 21, false 3, maybe-false 0
- findings:
  - `[false]` `[reject]` Blind: `seat_timing` subtracts NULL times for unordered Weeks. False: `seat_weeks.opened_at` and `ordered_at` are NOT NULL (`games/models.py`), and a Week that has not been ordered has no `seat_weeks` row, only a `seat_turns` row. `order` is NOT NULL too.
  - `[low]` `[reject]` Blind: time spent counts idle time from the Week's opening. This is how the story defines the signal («the time from `opened_at` to `ordered_at`»). It is labelled «Til informasjon» and «Endrer ikke fullføringen».
  - `[low]` `[reject]` Blind: `adjusted` is derived beside the assembler. It reads the same stored adjustment with the same rule (`share_percent is not None`). The two could only drift if one of them were changed by hand.
  - `[low]` `[reject]` Blind: separate reads can show a mixed snapshot, and `staff_summary` authorises a second time. The next `session:` event corrects the mix. `staff_summary` grants the same two staff roles as `student_page.read`, so its None branch is a guard only.
  - `[false]` `[reject]` Blind: the `Literal` types turn a new state into a 500. False: `AttemptStatus` and `PlayStatusName` are closed enums with exactly these values, and `ended` comes only from `_game_state`.
  - `[low]` `[patch]` Blind: the record's parts are untested with data at the api. Added `test_the_studentside_shows_the_attempt_and_its_parts_never_an_answer`, which runs `open`, then `auto_submitted`, then checks the parts as flags only, plus the tests before the lock. The quiz and Replay reads are already tested in their own modules.
  - `[low]` `[patch]` Blind: frontend tests do not cover the game, Debrief, quiz and Replay lines, and 59 s reads «0 min». Added Vitest cases. They found a double full stop after the Oslo day («des..»), now fixed in five strings. Under a minute now reads «under 1 min».
  - `[low]` `[reject]` Blind: Tilrettelegging and Frister load after the record and fail silently. The second request fails only when the first one has just succeeded, and an error and retry branch would add surface. A saved adjustment reaches the record through the `session:` event.
  - `[low]` `[reject]` Blind: the Roster shows one link per Class session, Control test sessions included. Classes have one or a few sessions. Control test sessions are not on this branch, and at the Epic 12 merge they come with `reports.scope`.
  - `[low]` `[patch]` Blind: `can_adjust` keeps a stale contract, and `schema.ts` is missing from the diff. Corrected the `InsightOut.can_adjust` docstring. The `schema.ts` part is false: the generated client was left out of the review diff on purpose, regenerated with `npm run api:generate`, and typechecked.
  - `[low]` `[patch]` Blind: quiz and Replay have no «not counted» reason, corrections show no mark, and «ennå» is wrong for a finished game. Quiz and Replay always count once recorded, and corrections are Story 13.3. «Ingen egne bestillinger ennå.» is now «Ingen egne bestillinger.».
  - `[low]` `[reject]` Blind: the tests import helpers from other test modules and hard-code copy. Story 13.1's tests follow the same convention. The spine's share lines are asserted word for word on purpose.
  - `[low]` `[patch]` Blind: «constant» claims «hver uke» from a few own Orders. `Participation.after_guided` and the api field are added, and the line now says how many own Orders it compares («De 4 egne bestillingene etter de veiledede ukene hadde samme antall.»).
  - `[low]` `[reject]` Edge: participation is shown where Completion does not count the game. `student_game` is the Student's Class game. Completion is None only for a Student outside the reporting scope, and the information is still true there.
  - `[low]` `[reject]` Edge: after a Reclaim the time counts from the turn's opening. The story defines the signal this way, as information only.
  - `[low]` `[reject]` Edge: one overnight Order inflates the time, and there is no cap. Same as above: the definition is the story's, and a cap would add a rule nobody asked for.
  - `[low]` `[reject]` Edge: the second query fails with no retry. Same as the Blind finding.
  - `[low]` `[reject]` Edge: separate sessions give an inconsistent record mid-play. Same as the Blind finding.
  - `[false]` `[reject]` Edge: Spillinnsikt links a Student who has left the Roster. False: Spillinnsikt names only current Students (`classes.student_names`), and the link needs a name.
  - `[low]` `[reject]` Edge: many sessions crowd the Roster. Same as the Blind finding.
  - `[low]` `[reject]` Edge: Orders do not refresh the record. The AC asks for a refetch when a step is recorded or corrected (`session:`), and the e2e test verifies it. A `game:` event names a game, not the Student's record.
  - `[low]` `[patch]` Edge: the `can_adjust` docstring is stale. Fixed together with the Blind finding.
  - `[low]` `[patch]` Edge: the participation docstring claims «the same rule Completion counts by». The docstring now says that time counts own Orders in every Week, while Completion counts only the Weeks after the Guided Weeks.

## Design Notes

Page order: header, Fullføring, Spillet, Debrief, Debrief-quiz, Replay, Individuell test, KI-vurdering, Studentrapport (slot), then Tilrettelegging and Frister for Lecturers. Each block a `section` with an `h2` in `label`, text in `body`, data in tabular numerals. «Oversikt» reaches a Student through its game rows to Spillinnsikt (the Oversikt lists games, not Students); no extra Oversikt control [ASSUMPTION].

## Verification

**Commands:**
- `uv run pytest tests/analysis/test_participation.py tests/reports tests/sessions/test_adjustment.py tests/test_imports.py tests/test_authz_rules.py -q` -- pass
- `npm run typecheck && npx vitest run src/modules/reports src/modules/classes src/modules/games` -- pass
- `npx playwright test e2e/studentside.spec.ts e2e/tilrettelegging.spec.ts e2e/deadline-extension.spec.ts e2e/registration-status.spec.ts --workers=4` -- pass

## Auto Run Result

Status: done

**Summary.** The Studentside now shows a Student's whole record to the Lecturers and Assistant lecturers of the Class (FR-63). One read, `GET /api/class-sessions/{id}/students/{user_id}/record` (`getStudentRecord`, policy `student_page.read`), lives in `modules/reports`. Each part is read through the owning module's `service.py`.

The page shows these blocks:
- «Fullføring»: the five steps with «gjort» or «ikke gjort» in text, the share lines, and the requirement line when the session is obligatory. All of it comes from `completion_status`.
- «Til informasjon»: the time on the Student's own Orders and whether they were constant, computed by the pure `analysis.participation`. These signals never change the status.
- «Spillet», with a link to Spillinnsikt.
- «Debrief»: the Explanation as written and the summary's state, with a link to the staff Debrief summary.
- «Debrief-quiz»: every attempt.
- «Replay», with a link to its Spillinnsikt.
- «Individuell test»: the status and which parts hold content, never an answer.
- «KI-vurdering»: `off` or `not_ready`.
- An empty `data-report-slot`.

«Tilrettelegging» and «Frister» stay unchanged and Lecturer-only. They are fetched only when `can_manage` is true. Spillinnsikt now links a Student's name for every staff member. Each registered Roster row links to the Studentside of every Class session of the Class. The page refetches on `session:<id>`, since the record key is under the Studentside's prefix.

There is no migration and no new table. The builder did the implementation in its own context, as the lane brief requires, instead of handing it to a subagent.

**Seams (not built here).**
- Story 12.5: its «KI-vurdering» block replaces the `assessment` part (`record-blocks.tsx`, `RecordAssessmentOut`) at the merge. Student flags come with it.
- Story 13.12: it fills `data-report-slot` and the `report` field, which is always null for now.

**Files.**
- `backend/app/analysis/participation.py`: the pure participation signals.
- `backend/app/modules/reports/{routes,schemas,studentside}.py`, `README.md` and `app/main.py`: the record and its route.
- `games/service.py` and `repo.py`: `seat_timing`.
- `tests/service.py`: `attempt_summary`.
- `sessions/service.py`: `student_target(..., action)`.
- `sessions/schemas.py`: the `can_adjust` docstring.
- `platform/authz.py`: `student_page.read`.
- `identity/{repo,service}.py` and `classes/{schemas,service}.py`: `user_id` on registered Roster rows.
- Frontend: `copy/nb.ts`, `modules/reports/{api.ts,student-page.tsx,completion-block.tsx,record-blocks.tsx,record.ts,record.test.ts}`, `modules/games/insight-page.tsx`, `modules/classes/registration-status.tsx`, the regenerated `lib/api/{openapi.json,schema.ts}` and `e2e/studentside.spec.ts`.
- Backend tests: `tests/analysis/test_participation.py`, `tests/reports/test_studentside.py`, and one added test in `tests/reports/test_completion_test_step.py`.

**Review.** Two layers ran, blind and edge case, as the lane brief directs. The completion rules are unchanged, so four were not needed. They reported 24 findings: 21 low and 3 false.
- Patched: 7 low findings. A double full stop after the Oslo day was found and fixed, «under 1 min» was added, the constant line now names the number of Orders it compares (`after_guided`), «ennå» was dropped from the empty line, two docstrings were corrected, and api and Vitest coverage was added.
- Deferred: none.
- Every rejected finding and its reason is in the Review Triage Log.
- Follow-up review: false. No high or medium finding was patched.

**Verification.**
- Full backend suite (8 processes): 3732 passed. No new test takes over 3 s. The `tests/reports/test_studentside.py` tests take 0.8 to 2.9 s each on the short-game fixture, like Story 13.1's.
- ruff check and format: pass.
- Frontend: typecheck passes, and Vitest has 1194 passed. lint:colours and check:copy pass. The build passes inside the image.
- Playwright on 4 workers: `studentside`, `tilrettelegging`, `deadline-extension`, `registration-status`, `class-staff`, `game-insight`, `homes`, `order-field`, `game-card` and `completion`, 49 passed in all. The `studentside` spec runs axe and checks reflow at 320 px, at 1280 px with 200 % text and at 1440 px. It also checks the live refetch after the playout records the Klassespill step.

**Decisions taken for the founder [ASSUMPTION].**
- The Oversikt reaches a Student through its game rows and Spillinnsikt, and gets no control of its own.
- The Roster shows one «Studentside, økt N» link per Class session.
- The Individual test part shows the status and which parts hold content, never the answers.
- Time spent covers the Student's own Orders in every Week, Guided Weeks included. Constant is judged after the Guided Weeks only, and is None with fewer than two Orders.
- All new copy is draft.

**Residual risks.**
- The participation time counts from the turn's opening, including waits and the time before a Reclaim, as the story defines it.
- The Decision log is read per Seat role, as in Story 13.1.
- Tilrettelegging and Frister load after the record, and if that second read fails, they are missing without a message.
