# Epic 6 Context: Students play the Class game

<!-- Generated from planning artifacts. Regenerate with compile-epic-context if planning docs change. -->

## Goal

A group of up to four Students can play a full Class game on their phones or a lab laptop: from the Start date they see their Class game, Role and Seats on Hjem, read the rules briefing, do the Starting task, start the game, place one Order per Week on the graph-over-table play screen, see whom the game waits for, and end on the chain's Total cost. This is the product's core learning loop and also lays down the shared pieces later epics reuse: the SSE stream and topic map, `drafts.ts`, `preview.ts`, the chart module, Graf over tabell, Kjedebånd, Setestatus, Stegene, Spillkort, Kjedens regning and Kjedens kostnad over tid. Pause, Takeover, Reclaim, «I rommet», playout and turn reminders belong to Epic 8 and are not built here.

## Stories

- Story 6.1: See my Class game, Role and Seats on Hjem
- Story 6.2: Read the rules before the first Order
- Story 6.3: Do the Starting task
- Story 6.4: See changes without reloading
- Story 6.5: Start the Class game
- Story 6.6: See my Seat's Week in the week table
- Story 6.7: See Netto lager, Posisjon and cost as a graph over the table
- Story 6.8: See the Landing's Demodata Seat as a graph over its table
- Story 6.9: See my link of the chain in the Kjedebånd
- Story 6.10: Play the Guided Weeks
- Story 6.11: Type an Order and see where it lands
- Story 6.12: Confirm the Order and keep what I typed
- Story 6.13: Never lose or double an Order on a bad connection
- Story 6.14: See which Seats have ordered and whom the game waits for
- Story 6.15: See the new Week within two seconds, on any device
- Story 6.16: See what my Seat has cost so far
- Story 6.17: See on Hjem whether the game waits for me
- Story 6.18: See the chain's Total cost when the game ends
- Story 6.19: Propose and accept a time to play
- Story 6.20: Play a private test Game as a Lecturer (cut list, `FEATURE_LECTURER_TEST_GAME`)
- Story 6.21: See the neighbour numbers the Lecturer switched on (cut list, `FEATURE_INFO_VISIBILITY`)
- Story 6.22: See the capacity in the briefing and on a capped Seat (cut list, `FEATURE_CAPACITY`)

## Requirements & Constraints

- **Hidden information:** Students never see the number of Weeks, the end of the game, a share played or the demand series; only the Retailer (Detaljist) sees customer demand, one Week at a time. They are told to play as if the business continues. The play envelope never contains a reference Order (Rule-based or near-optimal) or anything derived from one; no surface ever recommends an order.
- **Visibility from Start date:** a Student sees game, Role and Seats only from the Start date, even after the allocation is confirmed.
- **Pre-play gate (Class games):** rules briefing → Starting task → «Start spillet». Nothing is stored for "briefing read"; the gate is `progress.has_step(starting_task)`. The Starting task is scored by computed rules (no LLM), counts toward nothing, ends with an optional played-before question, and is still offered if the game ended with no Orders.
- **Orders:** one whole number 0..max per Week, validated inline, confirmed with one press, never changeable, never sent without a press, never duplicated (`409 order_exists`, unique `(game_id, week, seat_id)`). Guided Weeks place the fixed Order automatically; viewing the Week counts as ordering and advances the Week when all Student Seats have viewed. No model call in Guided Weeks.
- **Waiting:** every Student sees which Seats have ordered and whom the game waits for (Role, name or «KI-spiller», duration) on play screen and Hjem.
- **Timing:** a new Week shows within 2 s of the last Order (excluding AI thinking); play pages load within 3 s on 4G; state is stored before shown; reload or device switch loses nothing.
- **Game end:** last Week runs in full; Students see the chain's Total cost first, then cost per Role (never per name), then are led to the Debrief. Every finished Game is verified by replay.
- **AI labelling:** every AI-held Seat reads «KI-spiller» in plain text everywhere; Students never see «LLM-spiller» or the model.
- **Scheduling aid:** propose/accept a date+time only, no free text; never affects Inactivity or Takeover timing.
- **Copy:** Norwegian bokmål only; no «Beer Game» or «bullwhip» in pre-Debrief copy (CI check; «ØL-spillet» allowed); no exclamation marks, praise, ranking or celebration; «enheter», never «øl». Onboarding examples are labelled «Demodata».
- **Accessibility/devices:** WCAG 2.1 AA; works from 320/360 px to laptop; tap targets ≥ 44 px; text ≥ 13 px; no page-level horizontal scroll; state never by colour alone; every chart has a table alternative. Playwright + axe at 320, 360, 1440 px (and 200 % text where stated).
- **Cut-list stories** (6.20–6.22) sit behind `FEATURE_*` flags; with the flag off, nothing shows and routes answer not found.

## Technical Decisions

- **Engine is the only arithmetic** (pure, no I/O/clock). The web app computes no game quantity; the sole client arithmetic is the Order preview in `frontend/src/lib/preview.ts`, using only `seat_state` preview coefficients, tested against golden traces.
- **Only `games.commands` mutates** Games/Seats/turns/Weeks: one transaction, row lock on the Game, `version` increment, change events. New/extended commands here: `start`, `view_week`, `place_order` (adds `actor` → `409 seat_not_yours`), `finish`, `propose_time`, `accept_time`. Every command has an entry in `platform/events/registry.py` and emits exactly its listed topics (`game:<id>`, `user:<id>`, and `session:<id>` where `games.policy` says the Lecturer overview applies). `week_complete` advances exactly one Week.
- **Information boundary:** `seat_state` (Epic 1's `games.schemas.SeatState`, numbers only, versioned) is the single source for play screen, LLM prompt and Decision log; missing fields are added to that model with a `schema_version` bump. `games.views.table_status` carries people, resolved at read time, never stored or sent to an LLM. One play endpoint returns both plus `server_now` and `next_change_at`; Hjem uses the same sources.
- **Live updates:** push invalidates, pull reads. One SSE stream per User at `GET /api/events`, fed by Postgres `LISTEN/NOTIFY`, events `{topic, id, version}` only, scope-filtered via `platform/authz` (Students never get `session:<id>`), `session:` coalesced to 1/2 s, heartbeat 15 s, server close after 10–13 min. `frontend/src/lib/api/topics.ts` is the only topic→TanStack Query key map; data is refetched over REST via the generated OpenAPI client.
- **Authz:** all through `platform/authz`; add scope helper `own_seat(user, game)`; no `if role ==`. Denied access never reveals whether a game exists.
- **Purposes:** `games.policy(purpose)` is the one behaviour table; add columns "records the Class game step" and "pre-play gate applies" (on for `class`, off for `simulation`; `lecturer_test` row in 6.20). No branching on purpose itself. Reports/stats read through `reports.scope`, which excludes `lecturer_test`.
- **Timing columns:** `seat_turns` gains `viewed_at` (6.10) and `wait_started_at` (6.14); waits are computed only by `games.rules.turn_times`; only `games.commands` writes them.
- **Decided-by mapping:** one function in `games` `service.py` from `decided_by`/`fallback`/`occupant_kind`/`reason` to a display mark (incl. `guard_switch`), shared by all readers.
- **New modules:** `modules/progress` (step table, idempotent `record_step`, `has_step`, closed enum `starting_task, class_game, explanation, debrief, quiz_passed, replay, test_submitted, assessment_ready`; imports no feature module; step states computed in the api). `modules/content` (immutable versioned records; Starting task first; pinned version added to `SessionRuntime` via Epic 5's lock map). `modules/tests` (Starting task answers table/routes only). `analysis.scoring` (pure, reused by Epic 11). `games.service.student_game(user, class_session)` is the one way to find a Student's game.
- **Finished-game check** runs from `ops.sweep` (finished Games without a `game_checks` row → `games.service.verify_finished`), never blocking the end screen.
- **Charts:** `frontend/src/components/charts` is the only chart-library importer (Recharts; hand-made SVG with d3-scale/d3-shape for Kjedebånd); fixed width from caller, no `ResponsiveContainer`, `<title>` on every SVG. First chart story is a spike: ≤ 1 px column alignment in Playwright and a WeasyPrint `pdf/ua-1` render check; failing chart types are rebuilt as SVG and recorded in the module README. Fonts self-hosted.
- **Copy & errors:** UI strings in `frontend/src/copy/nb.ts`; api returns stable error codes mapped to Norwegian in the web app. Draft copy not in the spec goes to `nb.ts` marked for review.
- **Conventions:** money as `NUMERIC(14,4)` decimal strings, rendered by the single Norwegian number formatter Epic 5 put in `frontend/src/lib/` (extend in place for kroner, true minus, narrow-cell option; never write a second one). Unsent input lives in `frontend/src/lib/drafts.ts` (localStorage keyed by User+field, cleared on logout).

## UX & Interaction Patterns

- **Hjem is the Student hub:** no global nav on phone; Back returns to Hjem; one primary button per screen. Shows Stegene (six steps, current «pågår», later steps with what unlocks them), next deadline, Lab hours, Obligatorisk mark, Spillkort and Setestatus.
- **Play screen order** (reading and focus): Topplinje («Uke 11», Role + game number, Totalkostnad button) → Kjedebånd (own link only, upstream left, goods flow right) → Graf over tabell → Ordrefelt → Setestatus (always visible).
- **Week table:** HTML `<table>`, columns nå − 7 to nå + 4 on phone (Uke 1 to nå + 4 on ≥ 1024 px two-column layout); right edge always nå + 4; one labelled scroll region with sticky row labels, scrolled to nå on load; graph and table share one x-axis and scroll position.
- **Graph tokens:** Netto lager 2 px line, `lager-fill` above zero, `restordre-fill` below; Posisjon thinner `ink-secondary` with square markers; «Nå» line with `future-tint` to the right; Kost per uke stacked bars, axis grows in 40 kr steps and never shrinks. No projection line in the Klassespill (Epic 10 option).
- **Ordrefelt states:** Guided read-only → empty → typed (preview in table + Kjedebånd, button «Bekreft ordre på N») → invalid → sending → confirmed → failed / timed-out / offline. Enter moves focus to the button; errors announced on blur/press, not per keystroke; disabled controls use `aria-disabled` and stay focusable.
- **Uke-overgang:** polite announcement of the computed deltas and week cost; ≤ 2 s animation, skippable, none with reduced motion, never blocks input; no celebration.
- **End screen:** «Spillet er ferdig» with chain total in `figure-hero`, Kjedens regning per Role (own row «(deg)», no sorting), Kjedens kostnad over tid with «Vis som tabell», and «Gå til Debrief».
- Connection states use Epic 3's Tilkoblingslinje; live updates never move focus.

## Cross-Story Dependencies

- **From earlier epics:** engine, `seat_state`, `place_order`, `advance`, `players.ensure_order`, `turn_times`, `verify_finished` (Epics 1–2); Skjelett, all-surface states, Tilkoblingslinje, session-expiry return, `ops.sweep`, `platform/notify` digest (Epic 3); `sessions.lock`/snapshot, `GET /api/me/class-sessions`, number formatter, Landing figure of Story 3.13, feature flags for capacity/visibility/student choice (Epic 5).
- **Within the epic:** 6.4 (SSE + `topics.ts`) underpins every live update in 6.5, 6.14, 6.15, 6.17. 6.6 → 6.7 (Graf over tabell, chart spike) → 6.8, 6.16, 6.17. 6.9 Kjedebånd → 6.11 preview, 6.21, 6.22. 6.10 creates the Ordrefelt read-only state → 6.11 editable → 6.12 submit + `drafts.ts` → 6.13 failure handling. 6.12 «Venter på» comes with 6.14. 6.15's «Kostnad så langt» link gets its target in 6.16. 6.18 adds the `games.policy` columns that gate 6.2/6.3/6.5 and are reused by 6.20.
- **Slots left for later epics:** Setestatus status line, control block and per-row actions (Epic 8); end-screen playout note (Epic 8); «Gå til Debrief» route constant pointing to Hjem until Epic 9; Kjedens regning extra-rows slot and four-Role Kjedebånd variant (Epic 9); projection option on the graph (Epic 10); Spillkort title variant (Epic 13); Starting task item component and `analysis.scoring` reused by Epic 11.
- **Open inputs:** final Starting task items come from issue #16 as a new content version (placeholders ship now); test-game budget charging stays open (issues #8, #9).
