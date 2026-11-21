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

## The Explanation before the reveal (Story 9.3, FR-41, AD-14, AD-16)

- `debrief_explanations` holds one Explanation per Student per Class session (key `user_id`,
  `class_session_id`), stored as typed with its length in characters and the database time, and
  never changed (a trigger refuses updates). `commands.save_explanation` locks the Debrief row,
  inserts once (409 `explanation_exists` otherwise) and records `progress` `explanation` in the same
  transaction; registry `debrief.save_explanation` → `debrief`, `session`, `user`.
- Step 1 reads (`debriefs.own`, after the 9.2 availability and ownership rule):
  `GET /api/debriefs/{id}/net-inventory` (`getMyNetInventory`) gives the Student's own Seat's
  Netto lager per logged Uke from `games.service.decision_log` (`state_seen.net_inventory` of
  their own Role only); `GET`/`POST /api/debriefs/{id}/explanation` (`getMyExplanation`,
  `sendMyExplanation`; 422 `validation_error` for white space only or over 5000 characters).
- The gate: `service.require_explanation(user_id, class_session_id)` raises
  `ExplanationRequired` (403 `explanation_required`) until the `explanation` step is recorded.
  Every Debrief read after step 1 calls it first; `GET /api/debriefs/{id}/steps/{2..5}`
  (`getDebriefStep`) is the step endpoint later stories fill.
- Staff read: `GET /api/class-sessions/{id}/students/{user_id}/explanation`
  (`getStudentExplanation`, policy `explanations.read`: the Class's owners and Assistant lecturers
  through `sessions.service.class_staff_may`); 404 `not_found` when none is sent.

## The reveal of customer demand (Story 9.4, FR-44, AD-7, AD-23)

- `GET /api/debriefs/{id}/steps/2` answers `reveal` behind `require_explanation`: the heading
  rendered by code (`analysis.sentences.demand_heading`) from the Game's stored demand series
  (`games.service.demand_series`) with the sentence templates the Class session pinned at the
  lock (`content.sentence_templates`, the latest for a session locked before the pin), and per
  logged Uke of the Student's own Seat: Kundene (`demand_series[week - 1]`), Ordre inn
  (`state_seen.incoming_order`) and Din ordre (`order`), with the largest own Order and its
  first Uke. No other Seat's numbers. Steps 3 to 5 answer `reveal: null`.

## The whole chain (Story 9.5, FR-44, AD-7, UX-DR33, UX-DR34)

- `GET /api/debriefs/{id}/steps/3` answers `chain` behind `require_explanation`: every Role,
  Fabrikk first, with per logged Uke its Order and the Week state it saw when ordering
  (`state_seen`: Ordre inn, Lager, Restordre, På vei), and Forsterkning and the first Uke with an
  Order of 10 or more read from the stored facts set (`games.service.fact_set`: the first read of
  a Seat builds and stores it through `games.facts.get_or_create`, whose unique insert lets a
  racing second read return the stored row; the Debrief never computes facts itself). `capacity` is the Game's cap per Role while
  `FEATURE_CAPACITY` is on, null otherwise. `last_week` is the scrubber's range. Steps 4 and 5
  answer `chain: null` until their stories.

## The reflection questions (Story 9.6, FR-45, FR-43, AD-14, AD-21, AD-23)

- The questions are content of kind `reflection_questions` (`modules/content`), pinned at the
  lock under `pins["reflection_questions"]`; version 1 (migration 0105) holds three placeholders,
  feelings, evidence, structure, until issue #16.
- `GET /api/debriefs/{id}/reflection` answers the pinned version's questions in order, each with
  the caller's own answer or null; never another Student's. Behind `require_explanation`.
- `POST /api/debriefs/{id}/reflection/{question_id}` `{text}` stores one answer through
  `commands.complete_step` (Debrief row locked, `debrief:<id>` emitted) in
  `debrief_reflection_answers`, keyed by `user_id`, Class session and question, with the
  questions' version; never changed (trigger). Only the first unanswered question may be answered
  (409 `reflection_out_of_order`); an answered one answers its stored answer unchanged and emits
  nothing. 404 `not_found` for an unknown id, 422 for blank or over 2000 characters.
