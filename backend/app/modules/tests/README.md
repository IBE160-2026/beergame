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
