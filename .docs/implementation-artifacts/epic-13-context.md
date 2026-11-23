# Epic 13 Context: Completion and Student reports

<!-- Generated from planning artifacts. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Lecturers can see who met the requirement of an Obligatory class session, correct a Student's status with a logged reason, give a make-up game (Oppfølgingsspill) and message those who fell short. Students and staff can download the Student report as a tagged PDF; the Lecturer can download all reports as a ZIP and export the Completion status. The epic owns `backend/app/modules/reports/` and `frontend/src/modules/reports/`, extends `modules/progress`, and adds the shared pieces `analysis.completion`, `reports.scope` and `platform/storage`.

## Stories

- Story 13.1: Completion computed in one place, shown on the Student's Hjem
- Story 13.2: Studentside with the «Fullføring» block
- Story 13.3: Correct a Student's Completion status with a reason
- Story 13.4: Give a Student an Oppfølgingsspill
- Story 13.5: Continue to Debrief, Replay and test from a finished Oppfølgingsspill
- Story 13.6: Message the Students who have not met the requirement
- Story 13.7: Student downloads the Student report as a tagged PDF
- Story 13.8: Student report shows the game with its charts
- Story 13.9: Student is told when their data will be deleted
- Story 13.10: Report documents the Debrief, Replay and Individual test
- Story 13.11: Person downloading can add the AI assessment section
- Story 13.12: Staff download one Student's report at any time
- Story 13.13: Download all Student reports as one ZIP
- Story 13.14: Export the Completion status (CSV/Excel)

## Requirements & Constraints

- Obligatory requirement is met by completing every step: Class game, Debrief, Debrief quiz, Replay, submitted Individual test. Only the Completion status decides it; the AI assessment and Indicative letter never do.
- Class game step counts only if the Student ordered (`decided_by = student`) in at least the required share of Weeks after the Guided Weeks (default 80%, placeholder; per-Student adjusted share possible). Takeover and playout Weeks count as not ordered. Results also carry the share played in the playout, so a shortfall from playout or group pace can be told apart.
- An auto-submitted test counts only with content in each required part; an Explanation needs a minimum length. Both minimums are configurable placeholders. Time spent and constant Orders are shown to staff as information only and never change status.
- Corrections: Lecturer-only, required reason, logged in `platform/audit`, latest per step applies; Student sees «rettet av faglærer» but never the reason. A correction changes Completion status only, not step events, gates or the funnel.
- Make-up: solo Class game against AI players, open until the Student's effective Test deadline; closed unplayed Weeks count as not ordered; a finished make-up becomes the Student's game for Debrief/Replay/test (always a Personal debrief).
- Student page (FR-63): one page per Student with game, Explanation, Debrief summary, quiz attempts, Replay, test, AI assessment, and a link to the Student report; staff of that Class only, denial must not reveal whether the Student exists.
- Student report: tagged PDF/UA, ready within 30 s (placeholder); available to Student after the effective Test deadline, to staff any time; Norwegian bokmål; documents work, "not a grade"; missing steps marked not done; no other Student's name or free text; reflection-on-feelings answers left out. AI assessment section is opt-in (off by default, never in the ZIP or Completion export; Indicative letter only added by the Student themselves, never in a staff download). AI text is marked from the `ai_generated` flag.
- ZIP of all reports ready within 10 min for 250 Students (placeholder); Completion export has fixed column allow-list, no AI data, Norwegian Excel-safe (æøå, dates, decimal comma), streamed without storing.
- Data deletion date = latest effective Test deadline + retention period (placeholder: course end + 6 months), stored on the Class session; one reminder digest (placeholder 14 days before) per Student.
- Accessibility: reflow at 320 px and 200% text, axe clean, every chart has a table alternative, status never by dot alone.

## Technical Decisions

- AD-1/AD-16: `analysis.completion(steps, decision_log_summary, corrections, settings) -> CompletionStatus` is pure (no I/O, no clock, no AI input) in `backend/app/analysis/` and is the only definition of Completion. Hjem, Studentside, funnel, export and report all go through the one assembler `reports.service.completion_status(user_id, class_session_id)`, which gathers inputs through service layers of `progress`, `sessions`, `games`, `debrief`, `tests`. Step events live in `modules/progress`, recorded only through `progress.record_step` and read through `progress.has_step`; steps are a closed enum. The funnel counts step events (not the requirement) and stays in `progress` (takes student ids from caller; `reports.service.funnel` supplies `reporting_students()`); it is cached per Class session and invalidated by `record_step` (AD-25).
- AD-13: Game `purpose` ∈ class, replay, makeup, lecturer_test, simulation. `games.policy(purpose)` is the single behaviour table; commands never branch on purpose. This epic adds the `makeup` row (snapshot at creation, no Takeover/Pause/playout, hidden from overview wall, pre-play gate on, "records Class game step" on from 13.5, "Debrief always personal" on). `reports.scope.reporting_games()` (with purpose filter) and `reporting_students()` exclude lecturer_test/simulation games, control_test Class sessions (AD-27) and test Students; every report, statistic, export, funnel and Completion read goes through them.
- AD-15: `seat_week` is append-only; `decided_by` and `reason` are separate fields read through one mapping. Corrections are new rows in a separate `completion_corrections` table owned by `progress`; admin/staff actions go through `platform/audit.record`.
- AD-12: `platform/authz` policies for every route; repository queries on Class-owned data join through scope helpers; no `if role ==` in modules; Admin without Class membership sees no Student data; a self-enabled Indicative letter is never served to staff; signed URLs only after the policy allows.
- AD-8: mutations emit topics through `platform/events.emit(topic, id)` inside the transaction (ids only); the client refetches over REST via the topic-to-query bridge; new emissions need registry entries and the registry test.
- AD-9: deadlines/retention dates are columns; the `ops.sweep` runs due actions idempotently with ids-only jobs; notices go through `platform/notify.enqueue` (dedupe key). Queues `reports-single` and `reports-bulk` run in `worker-batch` with reserved slots (`REPORTS_SINGLE_RESERVED`, default 2) so a single report meets 30 s while a ZIP builds.
- AD-14: names/emails live only in `identity`; PDFs and ZIPs are the only stored copies with names, in the private `reports` bucket under a path keyed by Class session and `user_id`, regenerated on demand; report snapshots deleted when render ends; retention deletes bucket objects.
- AD-18: `reports.build_report_data(student, class_session, options)` is the only assembler of report content; the job stores a snapshot with a single-use 5-minute render token; `frontend` `/print/report/<snapshot_id>` is server-rendered, no JavaScript, blocked at the proxy (AD-11); WeasyPrint `pdf/ua-1` converts it; veraPDF runs in CI. Charts come only from `frontend/src/components/charts` at fixed width (no `ResponsiveContainer`), each with `<title>` and a following table. Fonts self-hosted (`@fontsource/source-sans-3`).
- `platform/storage`: Supabase Storage in production, `./.local-storage/` mock when keys are missing in local/test/ci; signed URL lifetime `SIGNED_URL_TTL_SECONDS` (default 300).
- AD-25: overview data comes from maintained summaries (`game_summaries`), not recomputation.
- AD-27: Control test Class sessions are excluded from reporting scope.
- Copy lives in `frontend/src/copy/nb.ts`; reuse existing components (Stegene, Meldingsskjema, play screen, Spillkort); no second form or chart implementation.

## UX & Interaction Patterns

- UX-DR29 Stegene: six steps (Klassespill, Debrief, Quiz, Replay, Individuell test, Rapport), current one marked, locked steps state what opens them; «Rapport» is locked until the effective Test deadline.
- UX-DR54 Fullføringsretting: status per step in text («gjort»/«ikke gjort»), share lines («Bestilte i 70 % av ukene. Kravet er 80 %.»), in-place correction form (Valgknapper, required «Begrunnelse», one form open at a time, focus moves to first field, Avbryt returns focus, result line takes focus), «Gi oppfølgingsspill», and a message link to those who have not met the requirement.
- UX-DR55: Studentside, Spillinnsikt, Klasserapport and similar surfaces; each chart has «Vis som tabell»; test games labelled.
- Student's Hjem shows no line revealing the number of Weeks while the Class game runs; «Oppfølgingsspill» appears as a Spillkort.
- Klasseøkt «Eksport» block: ZIP action with note «ZIP-filen har aldri med KI-vurderingen.», Completion export with «Ingen av filene har KI-vurderinger.»; Assistant lecturers see report downloads only; status line announced politely.

## Cross-Story Dependencies

- 13.1 is the base: 13.2, 13.3, 13.4, 13.6, 13.7, 13.14 all read `completion_status`; 13.3 adds the corrections table 13.1's function consumes.
- 13.2 leaves a report-link slot that 13.12 fills; 13.4 adds the `makeup` policy row, 13.5 extends it and `games.service.student_game`.
- 13.7 creates the report pipeline (`platform/storage`, snapshot, print route, `reports-single`); 13.8, 13.10, 13.11 add sections/options to it; 13.12 and 13.13 reuse it (13.13 adds `reports-bulk`); 13.9 feeds the retention date used by 13.7/13.12.
- Epic 5: `sessions.service` (`required_share`, `effective_test_deadline`, `build_snapshot`, Test deadline changes), Klasseøkt screen, Stegene. Epic 6: `games.service.student_game`, play screen, Stegene, Spillkort, `games.policy` columns, topic-to-query bridge. Epic 7: funnel (7.6), Meldingsskjema (7.9), four-Role charts (7.8), Spillinnsikt (7.7). Epic 8: adjustment (`get_adjustment`, 8.9), minimal Studentside. Epic 9: Debrief, `debrief.service`, `debrief.commands.open`. Epic 10: Replay, `replay.service`, `games.commands.close`. Epic 11: Individual test, Adapted items, Interaktiv oppgave rendering (moves to `components/`), test extension (11.13). Epic 12: AI assessment block (12.5), AI switch, Indicative letter.
- Epic 15 adds the Admin retention setting and the actual deletion; Epic 14 later reuses `reports.scope`.
