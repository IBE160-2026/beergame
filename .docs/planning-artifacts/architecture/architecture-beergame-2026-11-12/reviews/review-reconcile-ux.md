---
title: 'Reconcile review: ARCHITECTURE-SPINE vs UX (EXPERIENCE.md, DESIGN.md)'
reviewed: ARCHITECTURE-SPINE.md (draft, 2026-11-12)
against:
  - ../../../ux-designs/ux-beergame-2026-11-05/EXPERIENCE.md
  - ../../../ux-designs/ux-beergame-2026-11-05/DESIGN.md
  - ../../../prds/prd-beergame-2026-10-29/prd.md (FR-25, FR-26, FR-27, FR-39, FR-43, FR-57, FR-74, FR-86, NFR-1, NFR-3, NFR-5 for context)
created: 2026-11-12
scope: UX requirements with architectural consequences. Pure visual detail ignored. The spine was not edited.
---

# Reconcile review: architecture spine vs UX

## Verdict

The spine is a good fit for the UX's core loop: one write path, a server-owned engine, push-invalidates-pull, a single chart module and a print route. It has six gaps that would block or bend UX behaviour as specified:

1. The Seat view mixes people with game state.
2. Typed but unsent input has nowhere to live on the client.
3. Time passing triggers no events.
4. The Takeover and insert time is a derived rule with no single owner.
5. The Lecturer Oversikt has no fan-out or read-model strategy at 100 games.
6. The live typed-order preview needs game arithmetic in the browser, which AD-1 and AD-10 forbid.

Each gap needs a short rule, not a redesign.

Severity scale:
- **High:** the UX as written cannot be built without breaking a spine rule, or the result is wrong or unfair.
- **Medium:** buildable, but each team would solve it differently, or a spine rule needs an explicit exception or extension.
- **Low:** a clarification or a convention.

## Findings

### F1 (High): The Seat view carries names and presence, but it doubles as `state_seen` and the LLM prompt input

- **UX reference:**
  - EXPERIENCE → Setestatus: «venter, 3 min», name or «KI-spiller».
  - Voice: «Venter på: Jonas (3 min) og deg.»
  - State Patterns → Paused: «Pause, satt av Sara.»
  - Sett inn KI-spiller rows: «KI-spilleren bestiller for Jonas …».
  - PRD FR-25: Seats by Role and name, and how long the game has waited.
- **Gap:**
  - AD-3 makes `seat_view` the *only* producer of in-game data for a Seat.
  - AD-3 says the LLM prompt is built *only* from that object.
  - AD-15 stores it verbatim as `state_seen` in `seat_week`.
  - The game screen needs other Students' names, their order status and wait durations, and the name of whoever paused or inserted an AI. If these go into `seat_view`:
    - (a) Names are copied into `seat_weeks`, which breaks AD-14 (names live only in identity tables), and retention cannot find them.
    - (b) Names reach the LLM prompt, which breaks AD-6's "Seats by Role, people by pseudonymous id". The scrubber would catch them, but only by accident.
  - If these do not go into `seat_view`, AD-3's "only producer" rule forbids the play endpoint from serving them.
- **Suggested fix:** Split AD-3 into two objects:
  - `seat_view`: game state only (Role-keyed, no names, no wall-clock durations). This is what the LLM and `state_seen` get.
  - `seat_screen`: the play endpoint's response. It holds `seat_view` plus a presence and people envelope: occupants by `user_id` with display names resolved at read time from identity, per-Seat `ordered_at` or `waiting_since`, pause actor, pause time and insert times.
  - State that `state_seen` stores `seat_view` only, and that the envelope never enters `seat_weeks` or the AI gateway.

### F2 (High): Typed-but-unsent input must survive offline, page errors, session expiry and failed autosave, but the spine allows no client store beyond the TanStack cache

- **UX reference:**
  - State Patterns → All:
    - Offline: «Det du har skrevet, er tatt vare på på denne enheten.»
    - Page error: "Anything typed stays in its field."
    - Session expired: "Logging in returns to the same page with a typed order or answer kept."
  - Student game → Offline with a typed order: "It is never sent without a press."
  - Individuell test → Autosave failed: «Svarene ligger på denne enheten, og vi prøver igjen.»
  - UJ-6: the test is resumed on later evenings.
- **Gap:**
  - AD-8 says "No feature computes or caches state client-side beyond TanStack Query's cache".
  - AD-10 says "there is no other global store".
  - A login redirect, a reload or a closed tab loses both TanStack memory and React state. Session expiry also means a full navigation to Logg inn and back.
  - There are two policies here with no architectural home:
    - Orders are kept but never auto-sent.
    - Test answers are kept and automatically retried.
  - Shared lab PCs make device-local copies a privacy concern, and the spine is silent on that.
- **Suggested fix:** Add a narrow exception to AD-8 and AD-10: a **draft store**.
  - It is a single `web/src/lib/drafts` module over `sessionStorage` (orders, Forklaring) and `localStorage` or IndexedDB (test answers).
  - It is keyed by `user_id` + resource + version, holds user input only (never server state), and is cleared on logout, on user switch and on successful submit.
  - Write the two policies into the spine:
    - Order drafts are restored but never sent without a press.
    - Test-answer drafts are re-sent by the autosave loop.
  - Session expiry redirects with `?next=` and the draft store restores the input. The SSE bridge must detect 401 (use a fetch-based SSE client, not raw `EventSource`) so the UI can show «Du er logget ut».

### F3 (High): State that changes because time passes emits no event, so live views go stale under push-invalidates

- **UX reference:**
  - Sett inn KI-spiller → Shown: the button appears when the insert time *passes*.
  - Varselbånd: «KI overtar om 1 t». The band moves on when a game is no longer nearest.
  - Setestatus: «venter, 3 min».
  - Spillstyring → I rommet: the button is available only while a Labtime is on, and the mark ends with the Labtime.
  - «Alle spill side om side» opens after the Spillfrist.
  - Before the insert time: «Etter on. 10:00 kan dere sette inn en KI-spiller.»
  - Pause ended: «A right … that has already arisen survives».
- **Gap:**
  - AD-8 emits NOTIFY only from mutating transactions.
  - AD-9's sweeper acts on due timers, but only some crossings cause a mutation:
    - Takeover does.
    - "The insert right arises", "a Labtime starts or ends", "a deadline passes" and "the agreed pause time passes" do not.
  - A Student's Setestatus would never show «Sett inn KI-spiller» until something else invalidates the query.
- **Suggested fix:** Add to AD-8 and AD-9: every read model that has time-dependent state returns `next_change_at`, and returns `server_now` for durations.
  - The web bridge schedules an invalidation at `next_change_at`, with jitter.
  - Alternatively, or in addition, the minute sweeper emits a NOTIFY (`game:<id>` or `session:<id>`) when it crosses a display-relevant boundary: insert time, Labtime start and end, Spillfrist, Testfrist, Debrief 48 h.
  - State that relative times («3 min», «om 1 t») are rendered by the client from server timestamps and `server_now`. This is presentation, not computation under AD-10.

### F4 (High): Takeover and insert time is a multi-input derived rule shown in four places and acted on by the sweeper, with no single owner

- **UX reference:**
  - Sett inn KI-spiller → Insert time: the FR-36 clock starts at the first other order this Uke, or the agreed pause time.
  - The Tilrettelegging factor sets a floor.
  - «I rommet» sets a shorter limit until the Labtime ends.
  - Tilrettelegging → What it extends and Timing: "a running clock is recomputed at once".
  - The result is displayed in Setestatus (Students), the Varselbånd «KI overtar om …», the Spillstyring «Sett inn KI-spillere» page («Spill 2: Noah, 23 t») and the Student's own Hjem line.
- **Gap:**
  - AD-9 says "Deadlines, Inactivity limits, agreed Pause times … are columns". It does not say who computes the effective due time or when it is recomputed.
  - If the sweeper, the Student view and the Varselbånd compute it separately, they can disagree. One wrong case is an AI inserted before a Student's extended limit, which is an accessibility and fairness failure. Another is a band that says «om 1 t» after the sweeper has already acted.
  - The AD-2 command list lacks the inputs that change it: Tilrettelegging, «Endre avtalt tid», «Ikke i rommet lenger».
- **Suggested fix:** Add a pure function `engine` or `analysis.takeover_times(seat_state, occupancy, pause, in_room, tilrettelegging, settings) -> {auto_takeover_at, insert_right_at}`.
  - The views, the Varselbånd ordering and the sweeper all call it.
  - Either store the result as a materialised column, recomputed inside every command that changes an input (including a new `set_accommodation` call from `sessions` into `games.commands`), or compute it on read. Do not do both.
  - Golden tests cover Tilrettelegging × agreed time × I rommet.

### F5 (High): The Lecturer Oversikt at 60–100 games × 5 concurrent sessions has no read-model, coalescing or payload strategy

- **UX reference:**
  - Faglærer live → Oversikt: "Updates within 5 s" (FR-39).
  - Matrisevegg: one row per game, one column per Uke, with Celler filters (Netto lager / Ordre / Kost per uke) and Rolle filters, plus the median graph and «Median, Fabrikk» and «Kjedekost/uke, snitt» rows.
  - Right rail: Kostnadsfordeling, Trakt (the funnel over every Student) and «Venter ellers».
  - Headline counts.
  - NFR-3: 100 games per session, 250 Students playing at once, 5 sessions.
- **Gap:**
  - The spine names a "games (overview read model)" in the capability map but sets no rule for it.
  - Under AD-8 as written, each Order emits `game:<id>`. An Oversikt that subscribes to 100 game topics, or to an unspecified `session:<id>`, would refetch the whole overview on every Order. That is several times a second in a full Lab hour, for each open staff tab.
  - Each refetch recomputes the AD-16 completion funnel for up to 400 Students, plus cost distributions and medians.
  - The payload is about 100 games × 4 Roles × 40+ Uker × 3 cell types ≈ 50k numbers.
- **Suggested fix:** Add to AD-8 or the capability map:
  - (a) `games.commands` also emits `session:<id>` and the Oversikt listens only to that.
  - (b) The API coalesces `session:<id>` events to at most one every 2 s per session, which is inside FR-39's 5 s.
  - (c) There is a `game_summaries` read model (status, current Uke, waiting-for, chain cost, takeover times from F4, per-Uke cells), updated in the command transaction or by a cheap projection. The overview reads summaries, not full game state.
  - (d) The funnel and distributions are cached per `(session_id, session_version)`.
  - (e) The matrix uses a compact columnar JSON shape with ETag or version so an unchanged refetch is a 304.
  - Add an Oversikt scenario to the NFR-3 load test.

### F6 (High): The live typed-order preview needs game arithmetic in the browser, which AD-1 and AD-10 forbid

- **UX reference:**
  - Graf over tabell → Typing: "writes … Din ordre at nå, and Levering at nå + 4".
  - Kjedebånd: "updates as the order is typed: «På vei 16 + 24»".
  - Hidden information → Projection (Replay): «3 + 24 − 4 × 8 = −5 hvis ordre inn holder seg». It includes the typed 24, so it changes on every keystroke.
  - Alle rader: «Netto lager i kolonne 11 −9 + 4 − 8 = −13», «Posisjon i kolonne 11 −13 + 16 = 3».
- **Gap:**
  - AD-1: "No other code computes game quantities: the frontend displays what the API returns."
  - AD-10: "computes no game … values".
  - The column of arrival (the lead time from the delay settings), the På vei sum and the projection all have to be computed client-side while typing. A server round-trip per keystroke would be absurd.
  - The column-sum lines need the operands, not just the result. Without them the frontend reconstructs them by re-deriving engine logic.
- **Suggested fix:**
  - Have `seat_view` return preview coefficients and operands: `arrival_week_for_order`, `supply_line_items[]`, the projection `{base, horizon, assumed_incoming}`, and the operand lists for each displayed column sum.
  - Add an explicit AD-10 exception: "display arithmetic of the form base + typed value, with coefficients from the API, is allowed in one tested helper `web/src/lib/preview.ts`".
  - Golden traces from the engine check that helper (see F19).

### F7 (Medium): Stale-data detection needs an SSE heartbeat

- **UX reference:**
  - Faglærer live → Oversikt, connection lost or stale: "No update for 15 s": «Ikke oppdatert siden 14:02. Prøver igjen.»
  - «Oppdatert 14:02:15».
  - Tilkoblingslinje: "when live data is stale".
  - Offline: «Sist oppdatert 21:14».
- **Gap:** AD-8 defines the event stream but no keep-alive. A quiet period (nobody orders) is indistinguishable from a dead stream, so the 15 s rule would raise false «Ikke oppdatert» banners. Idle SSE connections behind Caddy and Railway may also be closed silently.
- **Suggested fix:** The `/api/events` stream sends a heartbeat comment or event every ≤ 10 s, carrying `server_now`.
  - The client treats "no heartbeat for 15 s" as stale and "a heartbeat with no events" as fresh.
  - «Oppdatert hh:mm:ss» means the last heartbeat or refetch, whichever is later.
  - On reconnect, refetch everything visible (already in AD-8).

### F8 (Medium): Group debrief needs presence, step control and dropout detection, but the spine models only mutations

- **UX reference:**
  - Debrief → Forklaring not sent: «Ida og Mikkel har sendt, Jonas skriver.»
  - FR-43: "All joined Students see the same Debrief step"; the step moves on when all have finished, or when the opener moves it on "after a short wait"; "A joined Student who dropped out continues in a Personal debrief"; the 48 h fallback; "others are notified and can join".
- **Gap:**
  - «Jonas skriver» and "dropped out" are presence, not committed state.
  - The spine has no presence mechanism, no group-step state machine owner and no rule for the "short wait".
  - The 48 h fallback is not in AD-9's sweeper list.
- **Suggested fix:**
  - `modules/debrief` owns a `group_debrief` row: joined members, `current_step`, `step_started_at`, `opener`. It has the commands `join`, `finish_step`, `advance` and `leave` (each emitting `debrief:<id>`).
  - Presence comes from either a draft autosave of the Forklaring («skriver» = a draft exists and nothing has been sent) or a light `POST …/presence` ping every 30 s, with the expiry applied on read.
  - Add "group debrief 48 h fallback and dropout" to the AD-9 sweep actions.

### F9 (Medium): Shared-screen and plenary views need server-side anonymisation and their own gates, not UI hiding

- **UX reference:**
  - Debrief → «Delt skjerm: hele kjeden»: shared charts only, no Forklaringer and no personal moments (FR-43, FR-74).
  - «Vis i plenum»: 60 games «uten navn og uten rangering», with the table in game-number order and no sorting by cost.
  - «Alle spill side om side»: FR-86, Student-facing, own game marked, gated by the Student's own Debrief being done and the Spillfrist having passed.
  - Cost picture: "Sorting by cost … never in plenum".
- **Gap:**
  - AD-3 mentions "Debrief and insight endpoints" gated by FR-42 and FR-43, but not:
    - (a) a shared-screen endpoint that a projector device logged in as one Student can call without receiving that Student's moments or Forklaring into its cache;
    - (b) the FR-86 gate, which is different from FR-42 and FR-43;
    - (c) a plenum variant of the overview with no names and no cost ordering.
  - Under AD-10, names and ordering must be removed by the API. A UI flag cannot be trusted on a projector.
- **Suggested fix:**
  - Define three explicit endpoints, each with its own AD-12 policy:
    - `debrief/<id>/shared` (chain-level data only, for any joined member or staff);
    - `sessions/<id>/all-games` for Students (anonymised, own game flagged, FR-86 gate, stable game-number order);
    - `sessions/<id>/plenum` for staff (anonymised, no cost sort).
  - A CI test asserts that no name, email or Forklaring field appears in their schemas.

### F10 (Medium): Staff need live full-chain in-game data, which AD-3's endpoint classes do not cover

- **UX reference:**
  - Matrisevegg cells per Role and Uke for running games.
  - Spillinnsikt (running): Rolle × Uke table and Ordrestolper.
  - Varselbånd names.
  - Assistent access.
- **Gap:** AD-3 says "full-chain data … served only by Debrief and insight endpoints" and ties them to the Debrief gates (FR-42, FR-43). Read literally, a running game's full chain would be unavailable to the Faglærer, because the Debrief gates are not met.
- **Suggested fix:** Name a third endpoint class in AD-3: **staff live views** (`games` overview and Spillinnsikt). They are full-chain, staff-only through AD-12, never reachable with a Student session, and not gated by the Debrief. Reaffirm that they never show «Uker spilt» or game length, per EXPERIENCE → "Week counts outside the game".

### F11 (Medium): A Veiledet uke advances when every Student has opened it, but "opened" has no write path

- **UX reference:**
  - State Patterns → Spill → Veiledet uke: "The Uke advances when all Students have opened it" (FR-24).
  - Reload or new device resumes.
- **Gap:**
  - AD-15 writes `seat_week` once, in `place_order`, including `opened_at`.
  - In a Veiledet uke the Order is placed by `open_week` (AD-5) before anyone opens the week, so `opened_at` cannot mean "the Student saw it".
  - Advancing on "all have opened" needs a mutation triggered by a read, and that command is missing from AD-2's list.
  - For normal Weeks, `opened_at` (used by SM metrics and the Decision log) has to be recorded before the row exists.
- **Suggested fix:**
  - Add a `games.commands.mark_seen(game, seat, week)` command. It is idempotent and called by the play page on first render of a Week. It records `first_seen_at` in a small `seat_week_seen` table, or on the Seat's current-week row.
  - In a Veiledet uke, the transaction that records the last `mark_seen` advances the Week.
  - Clarify that `seat_week.opened_at` is copied from `first_seen_at`.

### F12 (Medium): The Seat view contract is underspecified for what the game screen draws

- **UX reference:**
  - Graf over tabell window nå − 7 … nå + 4 (phone), and Uke 1 … nå + 4 on laptop.
  - Known arrivals marked as ordered, not guaranteed; overdue units with no known date.
  - Uke-overgang deltas «Restordre 13 blir 20» and «20 restordre × 1,00 = 20,00 kr».
  - «Sist Uke bestilte du 8.»
  - Cost rates in the key.
  - Spillkort mini graph on Hjem.
  - Timed out: "The app asks the server: if the order is there, it shows Confirmed".
- **Gap:** AD-3 says what the Seat view hides, not what it must contain. If the contract does not include a history window, previous-week values, the cost breakdown and the own-order status, the web app must derive them, which AD-1 forbids, or make many calls.
- **Suggested fix:** List in AD-3 (or the module's `schemas.py`) the minimum `seat_view` fields:
  - per-Week history rows from Uke 1 to nå;
  - known future arrivals with a `guaranteed: false` flag, and overdue units;
  - `previous_week` and `this_week` for the transition (the deltas are computed by the engine);
  - the cost breakdown per Week and cumulative, as decimal strings;
  - the rates and `max_order`;
  - the own Order for this Week, if placed (this is the answer to the 10 s timeout check);
  - the F6 preview coefficients.
  - The laptop's Uke 1 … nå window is fine under FR-14, because it never reaches past nå + 4.

### F13 (Medium): The single Student report must be ready in 30 s, but it shares the `reports` queue with 400-PDF ZIP jobs, and the UI has no pending state for it

- **UX reference:**
  - UJ-8: Sara downloads the Studentrapport, and «The AI section is left out unless Sara adds it».
  - Mine data: «Last ned Studentrapport» at the top.
  - Eksport → ZIP being made: «… innen 10 minutter».
  - PRD FR-57: a single report within 30 s.
- **Gap:**
  - AD-18 sends every PDF through the `reports` worker queue. One ZIP of up to 400 WeasyPrint renders can hold that queue for minutes, so a Student's single report misses 30 s.
  - The UX draws a pending state only for the ZIP. A Student's download is drawn as immediate, so an async job needs a «Rapporten lages …» state (or a synchronous-feel wait up to 30 s) and a `user:<id>` notification.
  - The variant with the AI section has to be a separate cached artifact. The spine does not say how variants and staleness are keyed.
- **Suggested fix:**
  - Split the queue into `reports-single` (high priority, its own concurrency slot) and `reports-batch`. The ZIP job renders each PDF via `reports-batch` or reuses cached singles.
  - Key cached PDFs by `(student, session, variant{with_ai}, data_version)`.
  - Add a UX state, «Rapporten lages. Den er klar om et øyeblikk.», driven by `user:<id>`. Feed this back to the UX as an open point.

### F14 (Medium): Test autosave needs ordering and multi-device rules

- **UX reference:**
  - Individuell test → Open: «Lagret 21:14» after each autosave.
  - Interaktiv oppgave → Cells: "Every change autosaves".
  - Autosave failed, keep working, then retry (F2).
  - UJ-6: returns on later evenings, possibly on another device.
  - Auto-submit at the Testfrist (FR-51).
- **Gap:**
  - AD-2's discipline (version check, idempotency) covers games only.
  - With rapid autosaves, retries and two devices, an older save can arrive after a newer one and overwrite it. An auto-submit by the sweeper can also race a late autosave.
- **Suggested fix:**
  - Per-answer upsert with a client-generated monotonically increasing `revision` (or `client_saved_at` + device id). The server keeps the highest revision.
  - Submit and auto-submit take `SELECT … FOR UPDATE` on the `test_attempt` and freeze it, so later autosaves get `409 attempt_submitted`.
  - The UI maps that code to the Submitted state.

### F15 (Medium): The AD-2 command list and the AD-9 sweep list miss actions and timers that the UX specifies

- **UX reference:**
  - Spillstyring: «Endre avtalt tid» (also on a Student's pause), «Avslutt pausen», «Ikke i rommet lenger», «Sett inn KI-spiller i alle seter som blir ventet på (9)» (a batch over many games, with "the result gives the real count").
  - The Oversikt marks "who triggered" each Takeover.
  - «Sara har allerede satt inn en KI-spiller.» (the conflict names the actor).
  - Oppfølgingsspill open until the Testfrist.
  - «I rommet» ends with the Labtime.
  - FR-27 turn emails: one per day, never at night.
- **Gap:**
  - AD-2 lists `pause`, `resume`, `mark_in_room` and `takeover`, but not `set_pause_time`, `end_pause` (by the Faglærer), `unmark_in_room` or a batch takeover.
  - AD-5's occupancy history has a `reason` but no `actor`.
  - AD-19 errors have `fields`, but nothing says a conflict returns who won.
  - AD-9's sweep list lacks: the I rommet expiry, the Oppfølgingsspill close, the group debrief 48 h fallback (F8) and the quiet-hours window for digests.
- **Suggested fix:**
  - Extend the AD-2 list, or state that it is illustrative and that every Spillstyring action is a `games.commands` entry.
  - Add `actor_user_id` to `seat_occupancy`.
  - Define a batch-takeover service that loops per-game commands (one transaction per game) and returns `{done, skipped_already_ordered, skipped_accommodation}`.
  - Conflict errors carry `fields.actor_display`, resolved at read time.
  - Add the missing sweep actions and a "no mail between 22 and 07 Europe/Oslo" rule (the hours are an assumption to confirm).

### F16 (Low): Wall filters change aggregates, so either the API serves every filter permutation or the browser computes medians

- **UX reference:** Veggfiltre "apply at once; the counts update with it"; the bottom rows «Median, Fabrikk» and «Kjedekost/uke, snitt»; the median graph over the wall; the sortable table.
- **Gap:** Recomputing medians or averages per Rolle or Celler filter client-side is "computing … cost values" (AD-10).
- **Suggested fix:**
  - The overview response includes the aggregate rows for every Rolle × Celler combination (4 × 3 small arrays).
  - Client-side filtering, grouping and sorting of server rows is explicitly allowed.

### F17 (Low): Allocation preview and roster upload hold temporary state that the spine does not place

- **UX reference:**
  - Fordelingsforhåndsvisning: «Kjør fordeling på nytt» redraws, and «Bekreft fordeling» commits *what is shown* (FR-20).
  - Filopplasting: choosing another «E-postkolonne» re-reads the rows at once. «Bytt fil» resets.
- **Gap:**
  - If confirm re-runs the allocation, the result differs from the preview.
  - Re-reading the file needs the upload kept server-side (openpyxl). Those are emails outside the identity tables (AD-14).
- **Suggested fix:**
  - The allocation preview is stored as a draft with a seed and id. Confirm takes that id and fails with `allocation_stale` if the roster changed.
  - Roster uploads go into an `identity.roster_upload` staging table with a TTL of 24 h, deleted on send, and covered by the retention sweep.

### F18 (Low): Font hosting contradicts DESIGN.md, and the PDF path needs fonts and AI marking

- **UX reference:**
  - DESIGN → Typography: Source Sans 3 «Loaded from Google Fonts», with tabular figures everywhere.
  - EXPERIENCE → AI disclosure: machine-readable AI marking, "including in PDFs" (FR-34).
  - PDF tagged, with a table under every chart.
- **Gap:**
  - The spine's stack self-hosts via `@fontsource/source-sans-3`, which is right for GDPR (no Google request with the Student's IP), but DESIGN.md says otherwise.
  - WeasyPrint in the worker must resolve the same font files from the print route, and the `tnum` feature must be in the subset used.
  - AD-18 does not say how "machine-readable AI marking" is expressed in the tagged PDF.
- **Suggested fix:**
  - Record in AD-18 or the conventions: fonts are self-hosted only (no Google Fonts), the print route links the same `@fontsource` files by absolute internal URL, and the latin subset with OpenType features is kept.
  - AI text in the PDF is a tagged structure element with an `ActualText` or `Lang` attribute and a custom role, plus an XMP note.
  - Ask the UX to change «Loaded from Google Fonts».

### F19 (Low): The test conventions miss the UX's mandated widths, and the web tests need engine fixtures

- **UX reference:**
  - DESIGN → Layout: tests at 320 px and 360 px, each at 100 % and 200 % text. The Oversikt, Klasseøkt, Lag Klasse, Meldingsskjema and an Admin list at 1280 px with 400 % zoom.
  - The Kjedebånd fits "in every Uke of a Classic game".
  - Table text ≥ 13 px.
- **Gap:**
  - The spine's Testing row says Playwright at 360 px and 1440 px only.
  - Because the web app cannot compute game states, the "every Uke of a Classic game" check needs engine-produced fixtures.
- **Suggested fix:**
  - Extend the Testing convention with these viewports and text scales.
  - Add a CI step that exports engine golden traces (addendum §B) as JSON fixtures for Vitest and Playwright. This also checks the F6 preview helper.

### F20 (Low): Smaller clarifications

- **Clock skew.** Relative durations («3 min», «om 1 t») need `server_now` in responses. This is covered by the F3 fix.
- **«Oppdater automatisk» off.** The SSE-to-query bridge needs a "hold" mode per query key that counts events («3 endringer siden 14:02») instead of invalidating. That is a bridge feature to name in `src/lib/api`.
- **Order retry after a lost response.** AD-2 is idempotent on `(game_id, week, seat_id)`, but the Student can edit the value after «Ordren ble ikke sendt». Define the response when a different value arrives for an already confirmed key: `409 order_exists` with the confirmed value. The UI then shows Confirmed with the real number.
- **Permission denied never reveals existence** (EXPERIENCE → Permission denied). AD-12 should state that out-of-scope resources return the same `404 not_found` as missing ones.

## Checked, no architectural gap

- Reduced motion, the Uke-overgang ≤ 2 s and «Hopp over»: web-only, with no server dependency. The FR-26 2 s budget is supported by AD-2 (advance in the same transaction) and AD-8.
- 200 % text, 320 px reflow, sticky labels and scroll regions: web-only; only the test convention is affected (F19).
- Light theme only, no dark mode: no impact.
- AD-19 copy homes and forbidden words: consistent with the UX's «ØL-spillet» exception, provided the CI word check allows the product name. Confirm the regex excludes «ØL-spillet».
- Reload or new device resumes (NFR-5): covered by AD-2 and AD-8.
- Charts with table alternatives and one chart module for web and PDF (AD-18): consistent with every chart in the Accessibility Floor list.
- Messages «i produktet og på e-post», and the ZIP-ready notification: `user:<id>` topic plus the `mail` queue.
- Mine data and the Indicative letter being hidden from staff: AD-12 already states the rule.
