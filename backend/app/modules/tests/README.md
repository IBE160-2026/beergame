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
