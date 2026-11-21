---
title: 'Story 9.2: Open the Debrief when the Class game has ended'
type: 'feature'
created: '2026-11-21'
status: 'done'
baseline_revision: 'b494185ffd8003823bf9904acf4e026943ebd605'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-9-context.md'
warnings: ['oversized']
deferred:
  - summary: >-
      A held Class session stays held as long as one Class game never finishes; nothing on this branch ends a game that is never played.
    evidence: |-
      `debrief.rules.state` answers `held` while any Class game is not `finished`. Epic 8's playout at the Spillfrist (lane 1, not on this branch) is meant to finish every Class game ("no Class game is left unfinished"); its test settles this. If a not-started game is left out of the playout, every Debrief of a held session never opens.
    location: >-
      backend/app/modules/debrief/rules.py
    severity: medium (unverified)
---

<intent-contract>

## Intent

**Problem:** A Student whose Class game has finished has nowhere to go: «Gå til Debrief» points at Hjem, there is no Debrief session, no availability rule, and the Lecturer cannot hold Debriefs until every Class game has ended.

**Approach:** New `modules/debrief` (backend and frontend). `debrief.rules` decides availability from `games.service` (open / not open / held); `debrief.commands.open` creates the one Debrief session of the Student's Game (step 1) and `debrief.commands.release` marks a held session released once and tells its seated Students. `modules/sessions` stores the hold choice («Lagre Klasseøkt», frozen at the Start date) and shows the Debrief state in Stegene and on «Spillet er ferdig». The web app gets `/debrief/{classSessionId}` with open, locked and held states.

## Boundaries & Constraints

**Always:**
- The Debrief finds the Student's game only through `games.service.student_game`; Game status only through `games.service` (`play_status`, `class_games`).
- One availability function: `debrief.rules.state(session, user_id, class_session_id, hold)` → `"open" | "not_open" | "held" | None` (None = no Class game for that Student). `available(user, class_session_id)` wraps it with the Class session read through `sessions.service`. `sessions` reaches it only through a provider `debrief` registers (`sessions.service.register_debrief_state`), so `sessions` never imports `debrief`.
- Held = setting `hold` AND at least one Game of `games.service.class_games` (Lecturer-overview purposes only, so test Games never count) not `finished`. Once all have finished the Debrief is open even before the sweep's release.
- `debrief.commands` is the only writer of `debrief_sessions` and `debrief_releases`; `open` inserts ON CONFLICT DO NOTHING, then `SELECT … FOR UPDATE` the row, and emits `debrief:<id>` only when it created the row. Registry entries `debrief.open: {debrief}` and `debrief.release: {user}`; a registry test runs both.
- Refusals carry only the error envelope: `403 debrief_not_open`, `403 debrief_held`, `403 forbidden` (not a Student of a listed Class of that locked session, unknown id, another Student's Debrief). No demand, Weeks or other Seats' data on any refusal (FR-14).
- The release due action finds held, locked sessions whose Class games have all finished and that have no `debrief_releases` row; `release(class_session_id)` takes ids only, is idempotent (insert ON CONFLICT DO NOTHING) and enqueues one `debrief_released` notice (digest, dedupe `debrief_released:<session>:<user>`) per Student holding a Seat now, which emits `user:<id>`.
- All UI copy in `frontend/src/copy/nb.ts` (draft copy marked `[ASSUMPTION]`); no «Beer Game»/«bullwhip». Debrief routes typed from the regenerated OpenAPI client.
- New migration `0102` (down_revision `0101`).

**Never:** no Explanation, chart, reveal or step content beyond the step-1 heading (Stories 9.3+); no Group-debrief join/presence or `debrief:` scope in the SSE stream (Story 9.11 decides who is joined; the event is emitted now); no copy of the hold choice when a Class session is made from an earlier one; no change to `games` or `players`; no import of `modules/players` from `modules/debrief`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| First open | Student, own game finished, setting open | 200 `{id, class_session_id, game_id, game_number, role, step: 1}`; one `debrief_sessions` row; `debrief:<id>` emitted | — |
| Second open / another Student of same Game | same | same row id, no new row, no event | — |
| Game running / playing out / not started | Student with Seat | 403 `debrief_not_open` on POST open and GET by id | envelope only |
| Held | setting hold, own game finished, another Class game running | 403 `debrief_held` | envelope only |
| Held, all finished | setting hold, every Class game finished, no sweep yet | 200 open | — |
| Not a Student of the session / bad id / staff | — | 403 `forbidden` | — |
| GET `/api/debriefs/{id}` of another Game | Student of other game | 403 `forbidden` | — |
| Release twice | held session, all finished | one release row, one notice per seated Student; second sweep acts on nothing | idempotent |
| Locked session, hold changed | «Lagre Klasseøkt» with other `debrief_release` | 409 `session_locked`, `fields.debrief_release = locked` | unchanged value saves |
| Stegene | class_game done, held | Debrief step `locked` with `held: true`; open → `current` (linked) | — |

</intent-contract>

## Code Map

- `backend/app/modules/games/service.py:235` -- `student_game`, `play_status:274`, `class_games:167` (purpose-filtered via `repo._listed`), `ClassGameSeat` (occupant per Seat).
- `backend/app/modules/sessions/models.py:30-90` -- `class_sessions`; add `debrief_release TEXT NOT NULL DEFAULT 'open'` + check.
- `backend/app/modules/sessions/schemas.py:23,188,351,543,551` -- `DebriefMode` pattern for new `DebriefRelease`; `ClassSessionOut`, `ClassSessionSaveIn`, `StepOut` (add `held: bool = False`), `StudentGameOut` (add `debrief`).
- `backend/app/modules/sessions/service.py:741` `get_session`, `:839` `save_session` (locked refusal list `:912`), `:1111` `enrolled_sessions`, `:1176` `STEGENE`/`stegene`, `:1251` `_game_out`, `:1339` `_own_locked_game` (enrolment + lock checks to reuse), `:2549` `register_pin_provider` (registry pattern).
- `backend/app/modules/sessions/repo.py:223` -- `save`; add `debrief_release`.
- `backend/app/modules/sessions/routes.py:283` -- pass `debrief_release` from body.
- `backend/app/modules/progress/service.py` -- `Step.CLASS_GAME`/`DEBRIEF`.
- `backend/app/modules/ops/sweep.py:112` -- `DUE_ACTIONS`; append `debrief.release`.
- `backend/app/platform/notify/__init__.py:110` -- `enqueue`.
- `backend/app/modules/messaging/delivery.py:154` -- `KINDS`; add `debrief_released` (digest) with a context resolver in `debrief.service`; templates in `backend/app/platform/email/templates/kinds/`.
- `backend/app/platform/events/registry.py` -- add entries; `stream.py:84` leaves `debrief:` unforwarded (9.11).
- `backend/app/platform/authz.py:80` -- `POLICIES`; add `debriefs.own` (ANY_USER).
- `backend/app/main.py:105` -- mount `debrief.routes`.
- `backend/tests/sessions/test_play.py:58` `running`, `tests/sessions/test_open_games.py` `confirmed`, `games_of`; `execute("UPDATE games SET lifecycle='finished' …")` pattern; `tests/classes/test_staff.call`.
- `frontend/src/modules/identity/homes.ts:54` -- `DEBRIEF_PATH` → `/debrief/{classSessionId}`.
- `frontend/src/modules/games/game-end.tsx:48` -- held line instead of the button; `home.ts:32` `stepItems`; `components/stegene.tsx` (add optional `href`); `student-hjem.tsx:169`.
- `frontend/src/modules/sessions/{choices.ts,class-session-page.tsx:517,api.ts:70}` -- hold Valgknapper in the Debrief block.
- `frontend/src/lib/api/topics.ts` -- `debrief` topic and `user` → `["debriefs"]`.
- `frontend/e2e/support/{auth,classes}.ts`, `POST /api/dev/class-sessions/{id}/lock` -- e2e setup.

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0102_debrief_sessions.py` -- `class_sessions.debrief_release` (+check), `debrief_sessions(id, game_id UNIQUE FK, class_session_id FK, step SMALLINT 1..5 default 1, opened_at)`, `debrief_releases(class_session_id PK FK, released_at)`.
- `backend/app/modules/debrief/{__init__,models,rules,commands,service,schemas,routes}.py` + `README.md` -- tables, availability rule, `open`/`release`, due finder, mail context, `POST /api/me/class-sessions/{id}/debrief` (`openMyDebrief`) and `GET /api/debriefs/{id}` (`getMyDebrief`).
- `backend/app/modules/sessions/*` -- `DebriefRelease`, store/read/lock the choice, `register_debrief_state`, `debrief_session_of(user, id)` (enrolled + locked read for debrief), `held_release_sessions(session)`, Stegene `held`, `StudentGameOut.debrief`.
- `backend/app/modules/ops/sweep.py`, `messaging/delivery.py`, templates, `platform/events/registry.py`, `platform/authz.py`, `main.py` -- wiring.
- `backend/tests/debrief/test_debrief.py` -- every matrix row, registry topics, import rule (`debrief` never imports `players`), Stegene and StudentGameOut states; updates to `test_migrations.py`, sessions save tests as needed.
- `frontend/src/copy/nb.ts`, `modules/debrief/{api.ts,debrief-page.tsx,debrief.test.ts}`, `app/(app)/debrief/[sessionId]/page.tsx`, `homes.ts`, `game-end.tsx`, `home.ts`, `stegene.tsx`, `student-hjem.tsx`, sessions choices/page, `topics.ts`, regenerated `openapi.json`/`schema.ts`.
- `frontend/e2e/debrief-open.spec.ts` -- open, locked and held states at 320/360/1440 with axe; Lecturer hold choice saved.

**Acceptance Criteria:**
- Given a finished Class game, when the Student presses «Gå til Debrief» on «Spillet er ferdig» or the Debrief step's link in Stegene, then they land on `/debrief/{classSessionId}` showing «Debrief, Spill N» and step 1 «Skriv Forklaringen først», and a Debrief session with step 1 exists.
- Given a running game, when the Student opens `/debrief/{id}`, then the page says the Debrief opens when the Klassespill is finished, and Stegene lists Debrief locked with that text.
- Given a held session with a Class game still running, when the finished Student opens Hjem, «Spillet er ferdig» or the Debrief page, then each says the Debrief opens when all Class games are finished, without a count.
- Given a Lecturer before the Start date, when they choose hold and press «Lagre Klasseøkt», then the choice is stored and shown; after the lock it is read-only text.
- Given the held session's last Class game finishes, when `ops.sweep` runs twice, then one release row and one notice per seated Student exist.

## Spec Change Log

## Review Triage Log

### 2026-11-21 — Review pass
Layers run: blind hunter and edge-case hunter (sonnet), following the orchestrator's two-reviewer rule; verification-gap and intent-alignment were skipped for the same reason. Both reviewers' hand-back failed; their findings were read from the scratchpad files they wrote.
- verdicts: 19 findings — high 0, medium 2, low 11, false 4, maybe-false 2
- findings:
  - `[medium]` `[patch]` (blind 1) `GET /api/debriefs/{id}` judged availability before ownership, so another Game's Debrief id answered `debrief_not_open`/`debrief_held` instead of `forbidden` (FR-5). `service.mine` now checks the game first; the held test asserts `forbidden` for another game's id.
  - `[false]` `[reject]` (blind 2) Personal Debrief mode shares one step pointer. No command in this story moves the step; per-Student step state is Story 9.11/9.12's (Design Notes).
  - `[low]` `[reject]` (blind 3) «Lag fra tidligere» does not copy the hold choice. The choice can only be set before the Start date, on the same Klasseøkt screen where the copy shows it, so the reset to the default is visible; a documented decision.
  - `[low]` `[patch]` (blind 4) The release told only current Seat holders, not a Student whose Seat an AI player took over (who still has a Debrief through `student_game`). Recipients are now the Students with `progress` `class_game` in the session (recorded at the end for every Student a Game ever seated), through the new `progress.users_with_step`.
  - `[low]` `[reject]` (blind 5) The rule reaches `sessions` through an import-time registration. Same pattern as `register_pin_provider`; the api imports `debrief.routes` in `main.py`, and a test pins the registration.
  - `[low]` `[reject]` (blind 6) Extra reads per Hjem card and in `available`. A Student has one or two sessions; the cost is a few indexed reads.
  - `[maybe-false]` `[defer]` (blind 7) A held session with a game that never finishes stays held. Depends on Epic 8's playout; deferred with what settles it.
  - `[low]` `[reject]` (blind 8) The page reads through the idempotent POST as a query, so refetches POST again. Idempotent by design and documented in `api.ts`; the GET route serves later steps.
  - `[low]` `[reject]` (blind 9) Smaller backend points: `commands.open` is the name the story requires; `release` relies on the sweep's finder for `hold`; `now` is part of the `DueAction` and mail-context signatures; the `assert isinstance` matches the other sweep acts.
  - `[low]` `[reject]` (blind 10) Test gaps (mail template render, test Games in the count, step upper bound, concurrency, component tests). Coverage suggestions, not defects; the copy check reads the templates and `class_games` is purpose-filtered by `repo._listed` with its own tests.
  - `[low]` `[patch]` (blind 11) Frontend duplication; one real defect: a step other than 1 would say «Steg N av 5» twice. Steps 2 to 5 now show the step in words once. The rest (inline Lenke classes in Stegene to avoid a class-merge clash, the step count constant, one sentence in three contexts) rejected as cosmetic.
  - `[false]` `[reject]` (blind 12) Mail copy: «Draft copy» is a Jinja comment (not rendered), the HTML templates of other kinds also set no subject, and other digest kinds also point to Hjem without a link.
  - `[low]` `[patch]` (blind 13) `ClassSessionOut.debrief_release` had a default, so the client typed it optional. Now required; the web-side fallback and `NonNullable` are gone.
  - `[medium]` `[patch]` (edge 1) Same as blind 1; same fix.
  - `[low]` `[patch]` (edge 2) Same as blind 4; same fix.
  - `[maybe-false]` `[defer]` (edge 3) Same as blind 7; deferred.
  - `[low]` `[reject]` (edge 4) When another group's last game finishes, a held Student's open pages update only on the sweep's release (`user` event, within a minute). That release is the story's notification mechanism.
  - `[false]` `[reject]` (edge 5) A test Game could get a Debrief. `games.service.student_game` never returns a test Game (`own_game` docstring and `repo._listed`), so `rules.state` answers None.
  - `[false]` `[reject]` (edge 6) The finder reads released sessions forever. It reads held locked session ids and filters released ones in one more read; the set is small. An archived Class's release writes a row and its mail is skipped by the context resolver, as intended.

## Design Notes

Decisions taken for the founder: Debrief URL keyed by Class session (`/debrief/{classSessionId}`), since a Student has one Debrief per Class session; one `debrief_sessions` row per Game (the Group debrief shares it; per-Student step state comes with 9.11/9.12); the page opens through the idempotent POST so «Gå til Debrief» and Stegene share one path; a non-Student gets `forbidden`, a Student without a finished game `debrief_not_open`; the release mail is a digest kind `debrief_released`; the hold choice is not copied by «Lag fra tidligere Klasseøkt» (its copy line names what is copied).

Draft copy (`[ASSUMPTION]`): Valgknapper «Når Debriefen åpner»: «Når eget spill er ferdig» / «Når alle spill er ferdige»; help «Studentene kan starte Debriefen så snart deres eget spill er ferdig. Da kan de fortelle om Etterspørselen til Studenter som fortsatt spiller.» / «Alle Debriefer åpner når det siste Klassespillet er ferdig.»; held «Debriefen åpner når alle Klassespillene er ferdige.»; Stegene «Debrief, åpnes når alle Klassespillene er ferdige.»

## Verification

**Commands:**
- `uv run pytest -n0 tests/debrief tests/sessions/test_ai_mode.py tests/sessions/test_student_home.py tests/test_imports.py` -- pass
- full `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` -- pass
- `npm run typecheck`, `npm test`, `npm run lint:colours`, `npm run check:copy`, `npm run build` -- pass
- Playwright: `debrief-open`, `class-session-choices`, `game-end`, `homes`, play-screen specs on the lane stack -- pass

## Auto Run Result

Status: done

**Summary.** The Debrief opens. `modules/debrief` (new) holds `rules.state`, the one availability rule (`not_open` until the Student's game, found through `games.service.student_game`, has finished; `held` while the Class session holds its Debriefs and a Class game has not finished; else `open`), `commands.open` (one Debrief session per Game, step 1, locked row, `debrief:<id>` on creation) and `commands.release` (once, with a `debrief_released` digest notice per Student of the session). Routes: `POST /api/me/class-sessions/{id}/debrief` and `GET /api/debriefs/{id}`, refusing with 403 `debrief_not_open`, `debrief_held` or `forbidden` and the error envelope only. `modules/sessions` stores `debrief_release` (`open`/`hold`, frozen at the Start date), shows `game.debrief` and Stegene's `held`, and reads the rule through `register_debrief_state`. The sweep releases held sessions. The web app has `/debrief/{classSessionId}` (open: «Debrief, Spill N» and «1 Skriv Forklaringen først»; locked; held), «Gå til Debrief» and Stegene's Debrief step lead there, «Spillet er ferdig» shows the held line instead of the button, and the Klasseøkt's Debrief block has «Når Debriefen åpner».

**Files.**
- `backend/migrations/versions/0102_debrief_sessions.py`: `class_sessions.debrief_release`, `debrief_sessions`, `debrief_releases`.
- `backend/app/modules/debrief/{__init__,models,rules,commands,service,schemas,routes}.py`, `README.md`: the module.
- `backend/app/modules/sessions/{models,schemas,repo,routes,service}.py`, `README.md`: the choice, Stegene `held`, `game.debrief`, the provider, `debrief_session_of`, `held_debrief_sessions`, the mail context.
- `backend/app/modules/progress/service.py`: `users_with_step`.
- `backend/app/modules/ops/sweep.py`, `messaging/delivery.py`, `platform/email/templates/kinds/debrief_released.*`, `platform/events/registry.py`, `platform/authz.py`, `main.py`, `migrations/env.py`: wiring.
- Tests: `backend/tests/debrief/test_debrief.py` (new); `test_imports.py` (debrief imports no `players`), `test_migrations.py`, `sessions/test_student_home.py` updated.
- Frontend: `copy/nb.ts` (`debriefEntry`, held lines, the choice), `modules/debrief/{api.ts,debrief-page.tsx,debrief.test.ts}`, `app/(app)/debrief/[sessionId]/page.tsx`, `identity/homes.ts`, `games/{game-end.tsx,home.ts,student-hjem.tsx}`, `components/stegene.tsx`, `sessions/{choices.ts,api.ts,class-session-page.tsx}`, `lib/api/topics.ts`, regenerated `openapi.json`/`schema.ts`, unit tests; `e2e/debrief-open.spec.ts` (new), `e2e/game-end.spec.ts` updated.

**Deviations and decisions.** The builder implemented in its own context, as the orchestrator instructed, instead of a step-03 subagent. Decisions for the founder are in Design Notes: Debrief URL by Class session, one Debrief session per Game, page opens through the idempotent POST, `forbidden` for non-Students, digest release mail, hold choice not copied, draft copy. Also: the `debrief:` topic is emitted but not forwarded by the event stream until Story 9.11 defines who is joined; the pre-reveal Debrief copy is in a new `nb.debriefEntry` section held to the pre-Debrief copy rules (the `debrief` section is exempt from them); the sweep action runs before the deadline reminders, which a test keeps last; release recipients are the Students with the `class_game` step (review patch).

**Review.** 19 findings: 6 rows patched (2 medium and 4 low rows; 4 distinct fixes), 2 rows deferred (one root cause: a game that never finishes keeps a held session held, settled by Epic 8's playout), 11 rejected with reasons in the triage log. followup_review_recommended: false (no high patched; the two medium rows are one entry, fixed and tested).

**Verification.**
- Full backend suite: 2864 passed in 69 s; ruff check and format clean; the migration walk test covers 0102 up and down.
- Frontend: typecheck, Vitest (719), `check:copy`, `lint:colours` and `next build` pass.
- Playwright on the lane stack (port 8081): `debrief-open` (open, locked and held at 320, 360 and 1440 px with axe; a live two-Uke game opened through «Gå til Debrief» and Stegene; the Faglærer's choice), `game-end`, `homes`, `student-home`, `test-game`, `class-session-choices`, `order-confirm`, `week-advance`, `game-card`, `live-updates`: 78 passed.

Tests over 1 s: `test_held_debriefs_wait_for_every_class_game_and_are_released_once` (about 1.5 s) and `test_a_finished_game_opens_one_debrief_at_step_one` (about 1.2 s); both set up a Class session with an allocation and a lock through the api, as the sessions tests do.

**Residual risks.** Draft copy awaits the founder's copy review (Issue #31). The held state depends on every Class game finishing (deferred above). The Debrief page has no live update until the `debrief:` topic is forwarded (Story 9.11); the release's `user` event refreshes it meanwhile.
