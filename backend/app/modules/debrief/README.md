# modules/debrief

The Debrief (Epic 9, FR-41 to FR-47, AD-21). Never imports `modules/players`
(`tests/test_imports.py`), and reads Games only through `games.service`.

## Opening the Debrief (Story 9.2, FR-42, AD-25)

- `rules.state(session, user_id, class_session_id, hold)` is the one availability rule:
  `not_open` while the Student's game (`games.service.student_game`) has not finished, `held`
  while the Class session holds its Debriefs and a Class game (`games.service.class_games`, so
  never a test Game) has not finished, else `open`; None with no Class game. `rules.available`
  wraps it with the Class session read through `sessions.service.debrief_session_of`.
  `sessions` reads the rule through `sessions.service.register_debrief_state`, so Hjem's
  Stegene and «Spillet er ferdig» judge as the routes do.
- `commands` is the only writer of `debrief_sessions` (one per Game, step pointer 1 to 5) and
  `debrief_releases`. `open(game_id, class_session_id)` inserts once, locks the row and emits
  `debrief:<id>` when it created it. `release(class_session_id, now)` writes the release once
  when every Class game has finished and enqueues one `debrief_released` notice (digest) per
  Student holding a Seat. Registry: `debrief.open` → `debrief`, `debrief.release` → `user`.
- The sweep's `debrief.release` due action: `service.due_releases` finds held, locked, unreleased
  sessions whose Class games have all finished; `service.release_due` acts with the id only.
- Routes (`debriefs.own`): `POST /api/me/class-sessions/{id}/debrief` (`openMyDebrief`) and
  `GET /api/debriefs/{id}` (`getMyDebrief`) answer `DebriefOut`, or 403 `debrief_not_open`,
  `debrief_held` or `forbidden` with the error envelope only (FR-14, FR-5).
- The `debrief:` topic is emitted but not yet forwarded by the event stream: Story 9.11 decides
  who is joined to a Debrief session.
