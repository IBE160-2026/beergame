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
