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
- The `debrief:` topic is forwarded by the event stream to the Students of the game (Story 9.11).

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

## The own moments (Story 9.7, FR-44, FR-43, AD-7, AD-12, AD-21, AD-23)

- `GET /api/debriefs/{id}/steps/4` answers `moments` behind `require_explanation`: the facts set
  of the Student's own Seat from `games.service.fact_set` (`games.facts.get_or_create`, never
  rebuilt), its id recorded for the Student at the first view by `commands.record_facts` in
  `debrief_fact_sets` (key `user_id`, Class session; stored once, trigger; Debrief row locked,
  `debrief:<id>` emitted on insert only; registry `debrief.record_facts` → `debrief`).
- The texts are rendered by the pure `analysis.moments.render(fact_set, templates, patterns)`
  from the `moment_templates` the Class session pinned (migration 0106, version 1) and the
  Detected pattern version the facts were built with; each travels as `{text, ai_generated:
  false, llm_call_id: null}`. Each moment also carries the other Roles' numbers that Uke
  (`others_seen`) and the Seat's `state_seen` of that Uke for «Dette så du».
- With fewer than 10 own Orders (`seat.sm_excluded`): `mostly_ai`, no heading, no moments; the
  facts set carries the flag that leaves the Student out of SM-1 and SM-2.
- Only the caller's own Seat: the route takes no Student or Seat, so no Group member or shared
  screen reads another Student's moments (FR-43).

## Kjedens regning and finishing (Story 9.8, FR-44, FR-47, FR-18, AD-1, AD-7, AD-12, AD-16)

- Step 4 also answers `bill`, from the same stored facts set: the chain's Total and backorder
  cost, the restordre share (whole percent, half up), whether backlog costs twice inventory, the
  AI-held cost and share, and «Simulert, samme kunder» (`seat.simulated`, analysis version 2:
  `analysis.simulated.simulate` over the Game's settings, stored demand series and frozen
  Rule-based set; row `own`, only the viewer counts På vei; row `all`, every Seat does). A set
  stored under version 1 has no rows (`simulated` null). The Role rows and Kjedens kostnad over
  tid are the game result's (`/api/me/games/{id}/result`, Story 6.18).
- `POST /api/debriefs/{id}/finish` («Fullfør Debriefen») runs `commands.finish`: the Debrief row
  locked; 409 `debrief_incomplete` until every pinned reflection question is answered and step 4
  was read (`debrief_fact_sets`), 409 `test_deadline_passed` once the database time is past the
  Student's `effective_test_deadline`; then one `debrief_summaries` row (moment ids, reflection
  answers with their version, the cited `fact_set_id`, `finished_at` in database time; never
  changed, trigger) and `progress.record_step(debrief, finished_at)` in the same transaction;
  `debrief:<id>` emitted (registry `debrief.finish`). A repeat answers the stored summary and
  emits nothing. `GET /api/debriefs/{id}/summary` reads the own summary (null until finished).
- `GET /api/class-sessions/{id}/students/{user_id}/debrief-summary` (`debrief_summaries.read`:
  the Class's owners and Assistant lecturers) answers `service.staff_summary`: the Explanation
  and the summary (moments rendered from the cited set, answers with their prompts,
  `finished_at`, `late` against the effective Debrief deadline), each null while missing; ids and
  Roles only. Studentside and the Student report read through the same function.
- `insight.links` offers Spillinnsikt (Story 7.7) one `explanation` and one `debrief_summary`
  link per Student-held Seat, to `/klasseokter/<session>/studenter/<student>/debrief`; it is
  registered through `games.service.register_insight_links` when that hook exists (Story 7.7 is
  on another branch until the merge), so `games` imports nothing from `debrief`.

## The Debrief quiz (Story 9.9, FR-46, FR-47, FR-18, AD-16, AD-23)

- Content kind `debrief_quiz` (`analysis.quiz.DebriefQuiz`): fixed single-choice questions with
  an answer key, a fixed explanation and an optional `in_your_game` template whose slots are
  values of the Student's own Game (`analysis.quiz.QUIZ_VALUES`), filled from the facts set of
  their Seat; a value the Game lacks leaves the sentence out. Version 1 (migration 0108) is a
  placeholder (`placeholder: true`, issue #16), pinned at the lock as `debrief_quiz`.
- `GET /api/debriefs/{id}/quiz` and `POST /api/debriefs/{id}/quiz/attempts` answer 403
  `debrief_required` until `progress.has_step(debrief)`. GET gives the next attempt's questions
  without the answer key (content order first, then shuffled with a seed of the Student and the
  attempt number; none once passed) and the latest attempt's result.
- POST scores on the server (`analysis.quiz.score`: every asked question once, 422
  `validation_error` otherwise) and runs `commands.submit_quiz`: the Debrief row locked; 409
  `quiz_passed` once passed, 409 `test_deadline_passed` once the database time is past the
  effective Test deadline; one `quiz_attempts` row (number, quiz version, answers with
  `correct`, `passed`, `submitted_at` in database time; never changed, trigger); a passing
  attempt records `progress.record_step(quiz_passed, submitted_at)` in the same transaction;
  `debrief:<id>` emitted (registry `debrief.submit_quiz`). A wrong answer's result carries the
  explanation; the quiz counts toward no score. In a Group debrief each Student takes it on
  their own device: nothing here is shared.
- The Debrief summary answers `quiz_attempts` (until and with the passing one) and
  `quiz_passed_at`, read from `quiz_attempts` at request time; the summary row never changes.

## Quiz exclusions and attempts for the staff (Story 9.10, FR-46, FR-47, AD-12, AD-15, AD-23)

- `quiz_exclusions` (migration 0109): one row per question a Lecturer took out of a Class
  session's quiz; never an edit of the content record. Written only by
  `commands.set_quiz_exclusions`: the Class session row locked (`sessions.lock_for_quiz_exclusions`,
  which refuses an archived Class), 422 for an unknown id, 409 `last_question` when nothing would
  be asked, 409 `test_deadline_passed` once the database time is past the Class session's Test
  deadline; a change writes one `platform/audit` row `debrief_quiz.exclusions_changed` (ids
  only), emits `session:<id>`, and enqueues a `quiz_changed` notice (digest) for each Student who
  has not passed and whose last attempt got wrong only questions now taken out, at least one
  of them in this change; a lift that ends «quizen er endret» for a Student emits `user:<id>`.
- `GET /api/class-sessions/{id}/debrief-quiz` (`debrief_quiz.read`: owners and Assistant
  lecturers) and `PUT …/debrief-quiz/exclusions` (`debrief_quiz.exclude`: owners).
- Every attempt asks the pinned questions not taken out; an answer to a taken-out question from
  a stale form is dropped. Nobody is passed by an exclusion, and a passed Student stays passed
  when one is lifted. `rules.quiz_changed` (registered with `sessions`) marks Stegene's current
  Quiz step `quiz_changed` until the next attempt.
- The staff summary adds the Student's Roster name (read now through `sessions.student_name`,
  never stored) and every attempt's number, time and result.

## Continue alone (Story 9.12, FR-43, AD-8, AD-9, AD-21)

- `debrief_alone` (migration 0111): a Student of a shared Debrief session who goes on as a
  Personal debrief, with the shared step they were on and why: `left` (`POST
  /api/debriefs/{id}/leave`, `leaveDebrief`, joined or not), `dropout` (two minutes without an
  SSE heartbeat), `fallback` (48 hours) or `missed` (`open` by a Student who never joined, once
  the pointer is at 4: the group finished without them; `join` then does the same). Final:
  `join` answers 409 `group_closed`. The joined set is the members without such a row; an
  alone Student reads every step as in a Personal debrief (no `step_locked`), keeps what they
  saved, and `GroupOut.alone`/`alone_from` say why.
- Presence: `platform/events.on_heartbeat(commands.touch)`, registered at import; each 15-second
  heartbeat of the User's stream writes `debrief_members.last_seen_at` in a short session of its
  own. No row lock, no event (registry `debrief.touch` → nothing).
- Every command that evaluates the joined set settles it first under the row lock: silent joined
  Students (not the caller) drop out, an opener no longer joined hands over to the earliest-joined
  Student who is (`commands.effective_opener`, which the read uses too), then the pointer moves as
  in 9.11. `move_on` commits its settle before judging the caller.
- Sweep: `debrief.dropouts` (`service.due_dropouts`, database time) → `commands.leave(dropout=True)`;
  `debrief.fallback` (`service.due_fallbacks`: shared, not run, pointer < 4,
  `fallback_due_at` = the Game's finish time + 48 h, stored at the open; in a held Class
  session the first open + 48 h, so a late release does not fall back at once) →
  `commands.open_personal_fallback(debrief_id)`: once, each Student of the game who has not
  finished goes alone and gets a `debrief_fallback` notice (digest). Registry `debrief.leave` →
  `debrief`; `debrief.open_personal_fallback` → `debrief`, `user`.

## Shared screen (Story 9.13, FR-74, AD-12, AD-21)

- `GET /api/debriefs/{id}/shared` (`getSharedDebrief`, `service.shared_mine`): «Delt skjerm: hele
  kjeden», a joined Student's own session in display mode. Only shared charts by Role: every
  Role's Uker from the Decision log (Order, Ordre inn, Lager, Restordre, På vei, Netto lager),
  Fabrikk first, Forsterkning and cost per Role and the chain's cost from the stored facts set.
  `SharedOut` has no text field, so no name, Explanation, answer or moment can be in it (a schema
  test asserts it). `locked` with `chain` None while a joined Student has no saved Explanation.
  Anyone not joined (Personal debrief, not joined, alone, another game, no such id) gets the
  same 403 `forbidden`. No Debrief write and no event (the facts set is read through
  `games.fact_set`, which stores it on its first use, as step 3 does); the screen refetches on
  `debrief:<id>`.

## AI narration that only connects computed facts (Story 9.14, FR-44, FR-46, FR-34, AD-6, AD-7, AD-9)

- Timing (the spine's deferred decision, closed): narration is generated on `llm-batch` in
  `worker-batch`, deferred inside the Class game's `finish` transaction by the
  `games.service.on_game_finished` hook `narration.py` registers (so `games` imports nothing from
  `debrief`): one idempotent job `debrief.narrate(game_id, seat_id)` per Seat a Student ever held,
  queueing lock `narration:<game>:<seat>`, ids only. The narration is the Seat's facts set's, so one
  job serves every Student assigned to it. Nothing is deferred when the Class session's pinned
  `debrief_ai_text` is off (or the session was locked before the pin). The sweep's
  `debrief.narration` (`due_narrations`/`narrate_due`) defers the job of a Seat with no narration
  row again 10 minutes after the finish, for 48 hours.
- The job (`narration.narrate`): the facts set through `games.fact_set`; one `quiz_explanation`
  call per pinned quiz question with an own-game sentence, then the `debrief_narration` call, each
  through `app.ai.text.worded` with `analysis.validate_ai_text` as validator and the code text
  (`analysis.render`) as fallback, scope `BudgetScope.class_session(<session>, model_config_id=
  <the pin's config>)`; mock answer: the code's own choice of sentences (AD-17). Each result is
  stored once in `debrief_ai_texts` (`commands.store_ai_text`, no lock, no event; registry
  `debrief.store_ai_text` → nothing); the narration row last marks the Seat done.
- Reads: step 4's `moments.narration` is the stored text when it was stored before the Student's
  first view of step 4 (`debrief_fact_sets.recorded_at`), else the code text, so it never changes
  under a reader. A wrong quiz answer's `ai_explanation` is the stored AI line when it was stored
  before the attempt (`submitted_at`). Both database times. `ai_generated` alone drives the
  «KI-generert, kan ta feil:» marking.
- Dev only: `POST /api/dev/games/{game_id}/seats/{seat}/narrate[?outage=true]` runs the job now in
  the api process; with `outage` the Seat's AI texts are deleted first and the mock fails.
- Production setup of a model config: `python -m app.ai.cli config edit <id> --prompt
  debrief_narration=1 --prompt quiz_explanation=1`, then measure and pin the new row; in
  `local`/`test`/`ci` the zero-config seed does the same for the mock config.


## Bounded follow-up questions (Story 9.15, FR-45, FR-15, FR-34, AD-6, AD-7, AD-11, AD-14)

- `GET`/`POST /api/debriefs/{id}/follow-up` (`follow_up.py`, through `service.own_follow_up` and
  `service.ask_follow_up_mine`): the field under the reflection questions, before step 4. Gates in
  order: own Debrief, the Explanation, the Group pointer, every reflection question answered (403
  `reflection_required`), then `follow_up_off` (AI text off, no provider for the pinned config
  (`app.ai.text.can_word`), templates pinned before version 2, or a Seat with no moments),
  `follow_up_closed`, 422 (blank, over 500 characters), 429 `rate_limited` (per account and per
  address, `follow_up_rate_limit_*` placeholder settings; `fields.retry_after` and `Retry-After`).
- One question is one call on the request: `app.ai.text.worded("debrief_follow_up", <Class
  session scope on the pin's config>, …)`, deadline `follow_up_deadline_seconds`, never retried.
  Inputs: the Role, the facts (`narration.fact_lines`), the pinned version's hint templates, the
  Student's Explanation and question (both free text: the gateway scrubs them against
  `platform/pii.terms`, the Class's Roster and staff). Output `analysis.follow_up.FollowUpOutput`:
  a decline flag, or 1–3 hints checked by `validate_follow_up` (Story 9.14's `validate_ai_text`
  with the hint ids only) and rendered by code. Mock answer (AD-17): a decline for a question with
  no game word, else the row hint on the earliest fact.
- `answered` (the hint text, marked by `ai_generated`) and `declined` (a fixed line in the web
  app) are stored once in `debrief_follow_ups` keyed by `user_id` and Class session with the facts
  set and the call (`commands.store_follow_up`, no event); `unanswered` (a failure, a rejected
  output, a spent budget) stores nothing.
- Closing: `service.close_follow_up(user_id, class_session_id)` → `commands.close_follow_up`
  (a `debrief_follow_up_closures` row, emits `user`), the entry point Epic 11 calls when the
  Student's Individual test opens; the database time past `sessions.student_deadlines`' Test
  deadline closes it too.
- Production setup of a model config: `python -m app.ai.cli config edit <id> --prompt
  debrief_follow_up=1`, then measure and pin the new row.
