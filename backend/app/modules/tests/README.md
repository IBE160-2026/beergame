# `modules/tests`: the Starting task (Story 6.3) and, from Epic 11, the Individual test

One table so far, `starting_task_answers`: a Student's answers to the Starting task, once per
Class session and item, with the content version (`content`, AD-23). The final question
(«Har du spilt et spill som ligner dette før?») is the row `item_id = 'played_before'` with a
`choice` (`yes`, `no`, `unknown`, `skipped` for «Hopp over»).

- Routes: `GET /api/me/games/{id}/starting-task`, `POST …/answers {item_id, answer}`,
  `POST …/final {choice}`. Any game that is not the Student's own locked Class game is 403
  `forbidden` (`sessions.service.own_game_session`).
- Scoring is `analysis.scoring.score_sum` (computed rules, no LLM). The answer key is only sent
  for an answered item.
- An answer is stored once; a repeat keeps the first. The final question needs every item
  answered (409 `items_open`) and records `progress` `starting_task` in the same transaction.
- The game's status is not asked: a finished game with no Orders still offers the task (FR-85).

## The question set selection, «Spørsmål og vekter» (Story 11.1)

`test_selections`: one row per Class session, the question set version it was saved on, the items
taken out, each Core item's weight and the Adapted total weight (`selection.py`).

- `GET /api/class-sessions/{id}/question-set` (owners and Assistant lecturers) and `PUT …`
  («Lagre vekter», owners only, `question_set.change`). The weights of the items left in plus the
  Adapted total must be 100 (422 `weights_not_100`); 409 `session_locked` from the Start date,
  `class_archived` for an archived Class. A save is audited and emits `session:<id>`.
- The selection in force is the row when it was saved on the latest version, else the latest
  version's defaults (`outdated`). The Start-date lock pins exactly that under
  `SessionRuntime.pins["question_set"]` (`question_set_pin`, registered with `sessions`); in
  production a `draft` version refuses the lock (`sessions.PinRefused`, `question_set_draft`, told
  to the owners like a missing provider key). `copy_selection` (registered with `sessions`) copies
  the selection, or the pin of a locked source, into a copy (FR-66).

## The Scoring guide, «Sensorveiledning» (Story 11.2)

`test_scoring_guides`: one row per Class session that edited its Scoring guide (or was pinned or
copied): the version in force (`scoring_guide_id`, a `content` record), the default it derives
from (`base_id`) and when the Test-deadline lock pinned it (`guide.py`). No row reads as the
latest default. A trigger refuses any change of a pinned row.

- `GET /api/class-sessions/{id}/scoring-guide` (owners and Assistant lecturers) and `PUT …`
  («Lagre sensorveiledning», owners only, `scoring_guide.change`) with the changed texts only
  (`{guides: {question_id: text}}`). A save publishes a new version made for the Class session
  through the content load's validation; the criteria, the scale and the titles never change. A
  question whose text differs from its base default is «Endret». 409 `scoring_guide_locked` from
  the original Test deadline (also before the sweep has run), `class_archived` for an archived
  Class; 422 `validation_error` for an unknown question or a text the record refuses. A save is
  audited (ids only) and emits `session:<id>`; an unchanged save stores nothing.
- `sessions.lock_test` runs `pin_guide` (registered with `register_test_pinner`) in its
  transaction: the version in force is pinned as of the Test deadline, on the latest default when
  the session never edited it. `copy_guide` (registered with `register_copier`) carries an edited
  version into a copy by its id, never its pin (FR-66).
- Whether the version is checked is asked of `content.service.is_checked` only; the block shows
  «Ikke kontrollert med en Kontrolltest.» while it is False.

## The Individual test: opening it with the own-work statement (Story 11.3)

`test_attempts`: one per Student and Class session, made when the Student accepts the own-work
statement (`statement_accepted_at`): the question set version and selection it opened on (the
Start-date lock's pin; the selection in force for a session locked before the pin existed), the
frozen ordered item list (`[{id, type, weight}]`, the Core items left in, in the set's order;
Adapted items join in Story 11.7), `effective_deadline` (`sessions.effective_test_deadline` at
opening) and the status `open` / `submitted` / `auto_submitted`. `test_answers`: one row per
attempt and item with its revision (written from Story 11.4). Both hold personal data (a User's
attempt, text a Student wrote).

**The write path (`commands.py`).** `tests.commands` is the only writer of an attempt and its
answers, with the commands `open_attempt` (11.3), `save_answer` (11.4), `submit` (11.10),
`close_attempt` (11.11), `extend_deadline` (11.13) and `end_sitting` (11.12). Every command that
acts on an existing attempt takes `SELECT … FOR UPDATE` on the attempt row and runs in one
transaction; `save_answer` and `submit` on an attempt that is not `open` fail with
`attempt_submitted`, and on an open attempt after its `effective_deadline` with
`test_deadline_passed`. Where no attempt row exists yet the lock is named: `open_attempt` relies on
the unique key on User and Class session and returns the existing attempt on a conflict;
`extend_deadline` locks the Student's extension row in `modules/sessions`, and the attempt row too
when there is one. A change of the Class session's Test deadline moves `effective_deadline` of its
open attempts in the save's transaction (`move_deadline`, `sessions.register_test_deadline_mover`);
Story 11.13 must leave Students with their own extension out.

- Routes: `GET /api/me/class-sessions/{id}/test` (`statement`, `open` with the items, `closed`
  when the Test deadline passed with no attempt) and `POST …` (accept the statement: 201 made, 200
  the one the Student has). 403 `replay_required` before `progress.has_step(…, replay)`; 409
  `test_deadline_passed`; 403 `forbidden` for every session that is not the Student's own locked
  one, whether or not an attempt exists (FR-5). No item is served before the statement; no weight
  or answer key is ever sent to the Student.
- `open_attempt` runs under the Class session row's share lock and closes the Student's Debrief
  follow-up questions in the same transaction (`debrief.service.close_follow_up`, FR-45); it emits
  `user:<id>`. No answer text is logged.
