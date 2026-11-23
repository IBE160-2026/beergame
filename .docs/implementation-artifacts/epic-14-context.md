# Epic 14 Context: Class report and statistics

<!-- Generated from planning artifacts. Regenerate with compile-epic-context if planning docs change. -->

## Goal

A Lecturer can read a live Class report for a Class session (games and learning results), compare it with earlier Class sessions on written, anonymised aggregates that survive deletion of Student data, and show all Class games in a plenary without names or ranking. Students can see all Class games side by side once their own Debrief is done and the Play deadline has passed. The epic owns the class part of `backend/app/modules/reports/` and `frontend/src/modules/reports/`, and reuses `reports.scope`, the chart module and `game_summaries`.

## Stories

- Story 14.1: Class report of the games
- Story 14.2: Class report of learning results
- Story 14.3: Compare Class sessions in Tverrklasse-statistikk
- Story 14.4: Filter comparisons and label Class sessions that differ
- Story 14.5: Students see all Class games side by side
- Story 14.6: The Lecturer shows all Class games in a plenary
- Story 14.7: The Admin compares across Institutions (cut list)
- Story 14.8: Export a Class session's Game data (cut list)

## Requirements & Constraints

- Klasserapport is for the Lecturers of the Class only; Assistant lecturers, Lecturers of other Classes and Admins without Class membership are denied through `platform/authz` (permission-denied state). The plenary page follows the Oversikt's policy.
- Game report content: funnel (cached, from Epic 7), distribution of Total cost and Order amplification per Role, most common Detected patterns (titled «Mønstre»), share of Seats played by AI players, Share of LLM Orders per Game, when a cost limit or Play guard switch took effect, share of Seats switched by the Play guard, plausibility rating per AI mode (counts and median only, never an individual rating, no `user_id`). Cost is split into Lager and Restordre with both numbers printed.
- Empty/partial states: «Ingen spill er ferdige ennå.» and «Oppdateres etter hvert som studentene blir ferdige. 41 av 60 spill er med.» with real counts.
- Learning part: Starting task results beside matching Individual test items (only Students who did both, with counts); results per test question; distribution of AI assessment total scores with a Core-only subscore (same weighting over Core items only, Adapted left out, remaining weights rescaled to 100%), labelled AI-generated with «Teller ikke. Ingen karakter.». No Indicative letter in any figure. If the AI assessment is off or not ready, state that and show computed parts as usual. Excluded questions are listed as excluded and left out of totals; count of Students still to submit is stated. The 10-Student threshold does not apply to the live report (staff may read each Student's answers); it applies to stored aggregates and cross-Institution views.
- Aggregates: written once per Class session, only for groups of 10 or more Students (smaller groups stored as withheld), with no `user_id`, `seat_id`, Game id, name or free text. Comparability keys: Game settings, AI mode, model config id, prompt versions, Effort level, question set version, Item weights, Scoring guide version. Score comparisons use Core-only scores and are called comparable only when question set, Item weights and Scoring guide version match.
- Student view «Alle spill side om side»: locked with «Åpnes når Debriefen din er ferdig og Spillfristen er passert.» until own Debrief done and Play deadline passed; shows Orders per Role and Week keyed by game number only, own game marked in text and line style (not colour alone); no names, `user_id`, occupant data or Total cost; nothing sorts, ranks or highlights by cost or result. Make-up/taken-over Students see their allocated Class game as their own.
- Plenary: no names, occupants, «Venter ellers», Varselbånd or Spillstyring data; table view in game-number order, no cost sorting, no near-Takeover tint; Rolle filter offered; must not call staff overview endpoints.
- Cut list (behind flags): 14.7 `FEATURE_CROSS_INSTITUTION_STATS` (Admin only, aggregates grouped by Institution, groups of 10+, no Class/Lecturer names; absent when off); 14.8 `FEATURE_GAME_DATA_EXPORT` (CSV, one row per Game/Week/Seat, who decided and fallback via the one mapping, no AI scores/feedback/letter, fixed column allow-list, Seats by game number and Role with occupant kind, streamed not stored; absent when off). Stories 14.3 and 14.4 must work unchanged without 14.7.
- Every screen: Playwright and axe at 320/1440 px (and 360 px for 14.5, 200% text where stated), no horizontal page scroll; copy only from `frontend/src/copy/nb.ts`; Norwegian strings in the epic are exact; use "enheter", never "øl".

## Technical Decisions

- Every report, statistic and export reads through `reports.scope` (`reporting_games()` with `purpose=class`, `reporting_students()`), so lecturer test Games, make-up games, simulations, Replays and Control test data are excluded unless a story states otherwise (14.8 includes make-up games and Replays, with `purpose` in its own column). Control test Class sessions are never listed.
- All figures (medians, costs, shares, Core-only score) are computed in the api from `game_summaries` (maintained one row per Game; the only source of Game status for lists), the Decision log and Epic 9 `analysis` facts; the web app computes nothing and formats with the shared number formatter. A report for 100 Class games answers from summaries and stored facts, never by replaying Games.
- Other modules are read only through their `service.py` (`tests.service` for computed scores and open attempts, `games` service for plausibility rating aggregates, `progress.has_step`). Core-only subscore is a pure function in `backend/app/analysis/` beside `analysis.total_score` (Story 12.2), covered by pytest golden cases.
- `decided_by`, `fallback` and `reason` are read through the one mapping of AD-15.
- Live refresh: the page refetches over REST via the topic-to-query bridge on a topic from the AD-8 catalogue; a new topic must be added to the catalogue and the registry test.
- Aggregates (14.3): `reports.write_aggregate(class_session_id)` writes into a table owned by `modules/reports`, with a header row holding `written_at`; the job is idempotent, keyed by Class session, on the `reports-bulk` queue, replacing that session's rows. A due action added to the sweep (Story 3.5) finds sessions whose latest effective Test deadline (the value Story 13.9 uses) has passed, with no open attempt per `tests.service`, and whose aggregate is missing or older than the latest AI assessment. No aggregate while the test is open; one aggregate after the deadline even with AI assessment off. `reports.service.write_aggregate` is exposed for Epic 15's shared deletion routine, which calls it first.
- Tverrklasse-statistikk reads only written aggregates, never live tables, so figures are identical before and after deletion; Class session list comes from `classes_visible_to(user)` in `platform/authz` (archived Classes included, other Lecturers' never). Comparability labels and filtering (on stored keys) are computed in the api. A withheld cell states the group was too small and no figure may be derivable from the other cells.
- Kostnadsfordeling «Fjoråret» mark (dashed, median chain Total cost of the previous Class session of the same Class) is added by 14.3 on the Oversikt and Klasserapport, with text form «Median 1 954. Midterste halvdel 1 500–2 600. Fjoråret 2 740.»; absent without a previous aggregate or if its group had under 10 Students.
- Student and plenary endpoints (14.5, 14.6) are dedicated server-side anonymised endpoints returning game numbers and per-Week values only; a test asserts the response schema holds no identifying field.

## UX & Interaction Patterns

- Charts come from `frontend/src/components/charts`; reuse Kostnadsfordeling and Trakt from Epic 7; each chart has «Vis som tabell» beneath it. Role lists put Fabrikk at the top; per-Role tables go Detaljist to Fabrikk; per-game tables are in game-number order.
- Klasserapport opened from the Oversikt or the Klasse. Student entry «Alle spill side om side» sits on Hjem.
- Plenary: secondary button «Vis i plenum» on the Oversikt; reuses the Matrisevegg and laptop layout on `paper` with larger cells and fewer columns; line «Mønsteret går igjen, uten navn og uten rangering.»; caption «Rødt: restordre, under null. Blått: lager, over null. Tallet i cellen er netto lager.» with an always-visible legend; Visningsbryter to «Vis som tabell» and to per-Role Orders charts (same components as 14.5, no game marked). Wall text at or above 9 px; keyboard focus stays on the same game across updates.
- Comparison page: «Samme mål, samme regnestykke.»; empty state «Du har ingen tidligere Klasseøkter å sammenligne med.»; filters are text-button toggles with `aria-pressed` and counts, operable by keyboard, announced politely on change; differing Class sessions labelled with what differs in text (chart, table and chart `<title>`), not colour alone.
- Phones: only the two-dimensional chart and table scroll, inside their own region.

## Cross-Story Dependencies

- 14.1 defines the Klasserapport page and chart set that 14.2 extends (learning part) and that 14.3 and 14.4 build their aggregate measures on; 14.3 writes aggregates from the 14.1 and 14.2 measures, and 14.4 and 14.7 read them.
- 14.5 builds the per-Role Orders charts and anonymised endpoint that 14.6 reuses.
- 14.7 and 14.8 are cut-list stories behind feature flags; 14.8 uses the «Eksport» block from Story 13.13.
- Depends on earlier epics: Epic 7 (funnel, Kostnadsfordeling, Trakt, Matrisevegg, Oversikt, `game_summaries`, Rolle filter), Epic 9 (analysis facts), Epic 10 (stored plausibility ratings, Story 10.8), Epic 11 (`tests.service`, question set, Item weights), Epic 12 (AI assessment, `analysis.total_score`, Story 12.2), Epic 13 (Test deadline value from Story 13.9, report download, Eksport block), Epic 3 (sweep, Story 3.5), Epic 5/8 (Play deadline, `progress.has_step`).
- Epic 15 consumes this epic: the shared deletion routine calls `reports.service.write_aggregate` before anonymising; Story 15.3 tests that routine against the real deletion.
