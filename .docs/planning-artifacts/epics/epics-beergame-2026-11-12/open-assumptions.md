# Assumptions in the stories for the founder to confirm

The story writers made these choices where the PRD, the architecture spine and the UX spines were silent or disagreed. Each is written into the story named. The last sections hold the decisions and choices from the validation round of 2026-11-12, and all story numbers are the numbers after that round. Confirm or change them before the story is built. Values marked "placeholder" are configuration and need no decision now.

## Where the sources disagree

**Confirmed by the founder on 2026-11-12:** all four are kept as the stories have them. EXPERIENCE.md followed on 2026-11-14: the invitation and Hjem line (row 1) and the notice rule (row 2). Stories 4.5, 6.1 and 11.2 were changed the same day.

| # | Question | What the stories do | Story |
| --- | --- | --- | --- |
| 1 | When does a Student first see their game, Role and Seats: at the Start date (FR-22) or when the allocation is confirmed (invitation copy in EXPERIENCE.md)? | From the Start date | 6.1 |
| 2 | Does «Ikke kontrollert med en Kontrolltest.» show for the default Scoring guide too (AD-27), or only for edited guides (EXPERIENCE.md)? | For any guide version not yet checked, the default included | 11.2 |
| 3 | FR-86 says Students see Orders per Role for all Class games; the UX plenary view shows net inventory in the wall. | Students see Orders per Role; the Lecturer's plenary view shows the wall with a switch to the Orders charts | 14.5, 14.6 |
| 4 | Where do the AI player descriptions live (FR-33): `modules/content`, `nb.ts`, or with the players? | Versioned files under `modules/players/descriptions/` | 2.13 |

## Behaviour the sources do not specify

**Accounts and Classes**
- The first Admin gets an Admin Invitation by mail at api start when an address in `BOOTSTRAP_ADMIN_EMAILS` has no User (3.8).
- «Be om lærertilgang» is a short public form (name, email, Institution) that the Admin invites from (3.13).
- Guard rules added: the last active Admin cannot be revoked or deactivated; the last owner cannot leave a Class; «Legg til Faglærer» needs a User who already has the Lecturer role (3.9, 3.10, 4.9).
- «Send N Invitasjoner» both saves the valid Roster rows and sends. An uploaded Roster cannot be saved now and sent later (4.4).
- An uploaded Roster file is parsed in memory and never stored; its rows wait in `identity` tables for 24 hours (placeholder) (4.2).

**Class session setup**
- If no allocation is confirmed by the Start date, the lock allocates at random by itself (5.12).
- After «Bekreft fordeling», only move and swap are offered, not a full re-run (5.10).
- A missing provider key in LLM mode refuses the lock, retries each minute and notifies Lecturer and Admin once. It does not switch to Rule-based players (5.11).
- A passed deadline cannot be changed, and a passed Start date cannot be moved (5.2).
- Assistant lecturers see the Klasseøkt read-only (Epic 5).
- The switch «Ja, står i emneplanen» is the whole confirmation for the obligatory mark (5.7).
- A rerun (FR-66) copies neither the obligatory mark nor the model config (5.18).

**Play**
- Before play the order is rules, then Starting task, then «Start spillet»; nothing is stored for "briefing read" (6.2, 6.3, 6.5).
- The scheduling aid (FR-22) is date and time fields only, one open proposal per game, and never affects Takeover timing (6.19).
- A Lecturer test game charges its AI calls to the Class session budget and ends back at the Klasseøkt with no Debrief (6.20).
- "Waiting" on the Oversikt means one Student has ordered and another Student-held Seat has not, with no minimum wait (7.1).
- Messages show on the Student's Hjem with no read state (7.10).
- An agreed pause time does not end the Pause by itself, and stays the insert time for that Week after the Pause ends (8.7, 8.8).
- No turn reminders are sent while a game is paused; the reminder delay is a 2-hour placeholder (8.13).

**Debrief and Replay**
- A new Class session switch, "AI text in Debrief", makes the no-LLM path in FR-15 work; follow-up questions are off when it is off (9.1).
- The shared screen shows no chain data while any joined Student lacks a saved Explanation (9.13).
- The FR-70 plausibility question after a Class game sits on «Spillet er ferdig»; individual ratings are not shown to staff (10.8).
- An unfinished Replay is closed at the Test deadline, not played out, and does not count as done (10.6).
- Students with fewer than 10 own Orders get their three moments from the Replay (10.7).

**Test and assessment**
- A Class session cannot be locked in production while its question set is a draft (issue #16); this also holds for a Control test (11.1, 12.7).
- The one-sitting option locks at the Start date (11.12).
- When AI feedback fails the fact check twice, the text is dropped but the item score is kept; a typed AI failure leaves the assessment incomplete, with no partial total and no letter (12.3).
- Indicative letter thresholds lock when the first test attempt is opened (12.6).

**Completion, reports and data**
- A make-up game has no Takeover, Pause or playout, is not on the wall, and closes at the Test deadline; either game meets the Class game step (13.4).
- Staff may add the AI section to a single Student report; the ZIP never has it (13.11, 13.12, 13.13).
- Students are told 14 days (placeholder) before their data is deleted (13.9).
- The pseudonymised export runs inside the request, and free text is exported as written, not scrubbed (15.4).
- Deleting a User who is in a running Class game first hands the Seat to an AI player (15.2).
- The daily spend alert is sent at once; the Lecturer's cost-limit notice goes in the daily digest (15.6, 15.7).
- Pre-pilot checks are a command (`python -m app.ops.preflight`) plus a readiness record in the repo, not an Admin screen (15.14).
- Whether Invitations are refused for an Institution with no data processing agreement is recorded as a founder decision, behind `REQUIRE_DPA_FOR_INVITATIONS` (15.12).

## Additions to the architecture

- **New `games.commands`** beyond the AD-2 list: `set_snapshot` (5.12), `propose_time` and `accept_time` (6.19), `close` (10.6), `recompute_turn_times` (8.9), `end_in_room` (8.11). AD-2 allows new commands as long as they are added there.
- **`rules_version`:** one package per engine version in `engine/rules/v<N>/`, never edited once a real Game references it, with golden traces per version in CI (1.10).
- **Allocation preview:** a stored server-side draft that confirm commits by id and revision (5.8, 5.9).
- **`python -m app.sim probe`** checks whether a model recognises the game (FR-31, issue #19) (2.4).

## Norwegian copy still to be written

EXPERIENCE.md has no string for these, so the stories add draft copy to `nb.ts` for review: expired Invitation, duplicate Roster row, archive consequence, Takeover requirement warning, playout note, Reclaim confirmation, Play guard row, neighbour labels, scheduling aid, Lecturer test game, own-work statement, larger-screen advice, time limit, test extension form, Indicative letter control, Control test consent and scoring screens, deletion notice, delete-User consequence.

## Decisions and choices from the validation round (2026-11-12)

The final validation found gaps that the fix round closed. Story numbers below are the numbers after the renumbering (199 stories).

### Decided by the founder

- **Guided Weeks:** the clock for the Inactivity limit runs in a Guided Week, from the moment the first Student has opened it. Opening counts as ordering for Takeover, the Student's insert and reminders. FR-24 is changed in the PRD (6.10, 6.14, 8.1, 8.2).
- **Make-up game:** once a Student's make-up game is finished it is that Student's game for the Debrief, the Replay, the Individual test and the report; otherwise the Class game is (6.1, 13.4, 13.5).

### Choices made while fixing, for the founder to confirm

**Engine and AI players**
- `games.commands.advance(game)` is a new command. Every command calls it after its own commit, so a Week advances one transaction at a time (2.1).
- `ai.run` keeps the spine's five arguments; `inputs` carries the prompt values, a caller reference stored on `llm_call`, and a mock answer (2.3).
- The first provider adapter is `openai_compatible` with an injected base URL (2.7).
- The maximum Order placeholder is 999, and the founder checks a hand-worked table of the first 10 Weeks of the step trace (1.2).
- A mock model config is seeded and pinned as default in `local`, `test` and `ci`. Approving an Effort level also needs the switched-share pass line, and the approval command lives in the simulation runner (2.12).
- `start` fills every still-empty Seat with a Rule-based player; `create` fills none (1.7, 1.8).

**Accounts and mail**
- A User with both the Admin and the Lecturer role lands on the Lærerhjem, with links both ways (3.3).
- `ops.sweep` is created with the mail pipeline. A digest is at most one mail per User per calendar day in Europe/Oslo, never between 22:00 and 07:00 (3.5).
- The dev agent writes `docs/ops/first-deploy.md`; the founder does the account steps for the first deploy (3.15).
- Accepting an Invitation runs a handler registered per Invitation kind in `identity.service` (4.9).

**Classes and Class sessions**
- In production with no pinned model, a new Class session defaults to Rule-based players, against FR-11's LLM default (5.1, 5.5).
- The required share of Weeks is a field «Andel uker som kreves» (draft copy), 1 to 100 %, placeholder 80. It locks at the Start date and is not copied by a rerun (5.7).
- A Student removed from the Roster after allocation: the lock gives the Seat an AI player; a game that has started is left to the Lecturer's Takeover (5.12, 5.13).
- **Decided 2026-11-17:** before the Start date, a late registrant with no free Seat gets a new Class game (5.13); FR-20 is aligned.
- `sessions.service.is_locked` is true when the Start date has passed or the lock has run (5.2, 5.11).
- «Kjeden ved start», the Datolinje and the allocation preview are diagrams of their own slice, not charts under AD-18 (5.1, 5.2, 5.8).
- The Roster parser is tested on synthetic files in the Canvas layout. The check against real Canvas exports is still open (4.2).

**Play**
- Capacity for Students: the briefing names the capped Roles and their numbers, and a capped Seat gets the extra table rows Lager and Restordre (6.22).
- The finished-game check runs from the sweeper, so up to a minute after the game ends (6.18).

**Overview, Takeover and Debrief**
- A wall row shows the Fabrikk's Netto lager by default (7.2).
- An "active Student" in the Group debrief is one with at least one own Order (9.11).
- When no clock runs for a Seat, a Lecturer's agreed Pause time stands as its insert time, also for a Student with Tilrettelegging (8.9).
- In a Guided Week only the Lecturer can end a Pause, because opening the Week is not an Order under FR-89 (Epic 8).
- The playout starts a never-started Game itself, and skips a Game that has no settings snapshot (8.14).

**Replay, test and assessment**
- The default Replay scenario for random demand keeps the mean with a spread of 2 or more; for a fixed series each Week's value becomes the level with spread 2 (10.1).
- «Start Replay» stands on Hjem under the Class game once the quiz is passed, and is the primary button when no game action is; the started Replay shows its Setene there until Story 10.4 adds the way to play it. A Student with no Seat in the Class session (so no game of their own) gets no Replay (10.3).
- «Start Replay» opens the Replay's play screen at once. While it runs, Hjem's Replay block has «Fortsett Replay, Uke 9» (the primary button when no game action is) and Stegene's Replay step reads «Fortsett Replay, Uke 9.»; the block's button is the way there, the step is no second link (10.4).
- The projection's delay horizon is the Order's lead time (order delay plus shipping or production delay). With nothing typed, the projection counts the Order as 0 and its sentence says so. A horizon past nå + 4 (delays of 3) keeps the axis at nå + 4: the line is drawn to the last column with no dot, and the sentence still gives the value at nå + horizon (10.4).
- The Replay's briefing and play screen state the Replay's own delays and rates, not the Class game's. The Replay has no time proposal, no Starting task and no Debrief link of its own (10.4).
- An own Replay scenario warns when, against the Class game, a delay is shorter, the peak demand level lower, the spread smaller, a change of level gone, any Guided Weeks are set, or the starting inventory is higher; a range counts by its easier end. Only Weeks and the change Week take a range in the form; the chain, capacity and Information visibility follow the Game settings (10.2).
- No diagram item type in v1. The Lecturer can edit the total weight of the Adapted items (11.1).
- A Lecturer edits the descriptive text of the Scoring guide only; criterion codes, count and weights are fixed (11.2).
- A timed sitting has its own end time on the attempt. The attempt itself still closes at the Test deadline, which is when the AI assessment starts (11.12).
- The AI assessment job has a maximum number of runs, then the state `failed` with a note to the Student and one notice per Admin. Assessments that are ready stay readable after a stop (12.2, 12.4).
- The Admin marks the operator-owned Institution, owns the Control test's Class and uses the ordinary screens. A Control test is also refused on a draft question set (12.7).
- A scorer reaches the scoring list through a link on their own home screen (12.9).
- The Institution setting that makes the Indicative letter unavailable is a control on the Institution list (12.6).

**Completion, reports and data**
- A make-up game closed at the Test deadline never becomes the Student's game. A step already started on the Class game keeps that game (13.5).
- A late registrant without a Role gets one at random in the make-up game (13.4).
- The Meldingsskjema shows a table of the Students who have not met the requirement, with their shares. This screen is not in EXPERIENCE.md (13.6).
- A report downloaded by staff never holds the Indicative letter (13.12).
- The Klasserapport is not open to Assistant lecturers (14.1).
- The Game data export also holds make-up games and Replays, with a purpose column (14.8).
- Roster addresses and Invitations of people who never registered are deleted at the deletion date of the Class's last Class session (15.3).
- When a User is deleted, the system may take over that User's Seat at once (15.2).
- The error tracker story can finish on a mock adapter; the tool choice, the restore and the alert test are items in the readiness record (15.11).
- The pooler size is a hand-copied config value, `DB_POOLER_SIZE` (15.9).
- Load-test Class sessions and Games stay as anonymous test data in the operator-owned Institution (15.10).
- The data processing agreement check always passes for the operator-owned Institution (15.12).

### More additions to the architecture

- **`games.commands`:** `advance` (2.1), `move_seat` (5.10), an `actor` argument on `place_order` (6.12) and on `start` with `started_by` and `started_at` (8.10), an explicit replace argument on `assign_seat` (5.12).
- **`games.policy` columns:** snapshot at creation or at the lock (5.9); records the Class game step, and pre-play gate applies (6.18); Debrief is always personal (13.5).
- **`games.service`:** `student_game` (6.1), `budget_scope` (2.5), `register_insight_links` (7.7), `on_game_finished` (9.14). **`games.rules`:** `turn_times` now starts in 2.6, `waited_for` (8.12).
- **Other commands and hooks:** `tests.commands.end_sitting` (11.12); `assessment.service.stop_for_session` and `resume_for_session` (12.4); `debrief.commands.touch`, which takes no row lock and emits no event (an exception to AD-21), `debrief.commands.open_personal_fallback` and `platform/events.on_heartbeat` (9.12).
- **Tables and columns:** `simulation_batches`, `effort_measurements` (2.11, 2.12); `notices`, `mail_deliveries` (3.5); `invitations.renewal_requested_at` (3.8); `viewed_at` (6.10) and `wait_started_at` (6.14) on the open turn.

## Decisions and fixes after the readiness check (2026-11-14)

The readiness check of 2026-11-12 (`../../implementation-readiness.md`) found 29 gaps between the stories and the UX spines. The founder took six decisions on 2026-11-14, and the stories and both UX spines were changed the same day. The option figures are in `../../ux-designs/ux-beergame-2026-11-05/.working/valg-2026-11-13/`.

### Decided by the founder

- **Matrisevegg:** the whole wall can be read. It is a table to assistive technology, never `aria-hidden`, and every cell is read where it stands (7.2, 7.3, 7.7).
- **Pause:** the Setestatus is on the play screen through the whole Uke, also before the Order. The pause line and «Ta pause» stand by it (6.14, 8.6).
- **After the Order:** «Du får beskjed når Uke 12 åpner.» is replaced by a line that says what happens. No notice is sent when a Uke opens (6.12).
- **Klasseøkt:** the allocation preview is an in-place panel. «Bekreft fordeling» is the primary button while it is open, and «Lagre Klasseøkt» is then secondary (5.1, 5.8, 5.9).
- **Kost per uke:** the axis has no maximum and grows by 40 kr at a time: 40, 80, 120, 160 (6.7).
- **Timed test:** it stays in v1 and shows the time left at the top of the test. Tilrettelegging applies to the time limit (11.12).

### Draft copy for the founder to confirm

These strings are in EXPERIENCE.md or DESIGN.md marked `[ASSUMPTION: copy]`, and in the story named.

| String | Story |
| --- | --- |
| «Skjermen går videre når alle har bestilt. Du får e-post hvis spillet venter på deg.» | 6.12 |
| «Du får Rolle og spill på startdatoen.» | 4.5, 6.1 |
| «Tid igjen 38 min», «5 minutter igjen. Svarene dine er lagret.», «Tiden er ute. Testen er levert.» | 11.12 |
| The wall cell reading «Spill 2, Uke 14: Netto lager −13.» | 7.2 |

### Norwegian copy still to be written (added 2026-11-14)

The stories add draft copy to `nb.ts` for these, because the UX spines have no string:

- the lock lines of Debrief, Quiz and Rapport in Stegene, and the text of a finished step (6.1);
- the label on known arrivals that says ordered, not guaranteed (6.6);
- the line shown in the Uke the Kost per uke axis grows (6.7);
- the title of the Spillkort while the game waits for others (6.17);
- the state lines and the Lenke of the allocation block (5.8, 5.9);
- the Lenke for a Message to the whole Class session in the Oversikt header (7.9);
- the consequence line over «Sett inn KI-spiller i alle seter som blir ventet på» on one game (8.12);
- the statement of the time limit on the own-work statement, and the setting on the Klasseøkt (11.12);
- the Klasseøkt's «Replay-scenario» block: «Standard», the demand, step Week and length in words, and the line that they differ per Student and stay hidden (10.1);
- the own Replay scenario: «Eget scenario», the help line under the Valgknapper, «Antall uker, minst/høyst» and «Endres fra uke, tidligst/senest», and the warning lines that a change probably makes the Replay easier (10.2);
- the Replay on Hjem: the consequence line over «Start Replay», «Replay · Du er Grossist» once started, the refusal lines, and the Replay step's «ikke gjort, Testfristen er ute» when the Testfrist passed with no Replay started (10.3);
- the Replay on the play screen: «Grossist, Replay» under the Uke, the button «Fortsett Replay, Uke 9» (the spine's line without its full stop), and the projection sentence with nothing typed, «… 3 − 4 × 8 = −29 hvis du ikke bestiller og ordre inn holder seg. Ikke garantert.» (10.4).

### Choices made while fixing, for the founder to confirm

- With the Setestatus always shown, the one-line «Venter på: …» under the order button is not drawn. Its text is the live announcement only (6.14).
- The wall is one Tab stop. Arrow keys move cell by cell, Home and End go to the row's ends, and Enter on a cell opens Spillinnsikt (7.2, 7.7).
- The Uke-overgang summary stays above the Ordrefelt until the next Order is confirmed. Its Lenke «Kostnad så langt» opens «Alle rader og kostnad» on phone and is not shown on a laptop, where the panel is pinned (6.15, 6.16).
- «Tid igjen» counts whole minutes and is announced once, at 5 minutes (11.12).
- The Kost per uke axis never shrinks during a game (6.7).
- The Landing's «Demodata» Seat gets the «Kostnad så langt» panel under its figure (6.16).
- A Message to the whole Class session is opened from a Lenke in the Oversikt header. This entry point is not in EXPERIENCE.md (7.9).
- The theme is built from a token file copied from DESIGN.md's front matter, with a test that fails on a missing or changed token. The CI copy check also fails on an exclamation mark, on «øl» outside the product name, and on «optimal» or «fasit» (3.1).
- The token `rounded.xs` (column highlight frame) is in the theme, but no component in the spines uses it, so no story draws it.
- Spillinnsikt gets Forsterkning and the four-Role Kjedebånd when Story 9.5 builds them, not in Epic 7 (7.8, 9.5).
- The Tilrettelegging label «Mer tid før KI tar over» is unchanged, although the factor now also extends the test's time limit (8.9, 11.12).

### Decided on 2026-11-17

- Before the Start date, a late registrant with no free Seat gets a new Class game, as Story 5.13 says. The founder chose this on 2026-11-17, and FR-20 in the PRD now says the same. After the lock, with no Class game still not started, the Student gets a make-up (FR-17).
- The assumptions and draft copy in this file are built as they stand. The founder will correct the copy in `nb.ts` after seeing the site (Issue #31 stays open until then).
