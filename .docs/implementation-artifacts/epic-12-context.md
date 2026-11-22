# Epic 12 Context: AI assessment and Control test

<!-- Generated from planning artifacts. Regenerate with compile-epic-context if planning docs change. -->

## Goal

After the Test deadline a Student can read an AI assessment of their Individual test: computed scores, one overall score with written feedback per long-answer and Adapted item, and a weighted total, always labelled as AI-generated, possibly wrong and not a grade. A Lecturer can switch the assessment off per Class session, read it for their Students, see Student flags and set the Indicative letter. The Admin can run a Control test where named humans score blind, and the product shows how well the AI agrees, which is what lets a Scoring guide be marked "checked" for a model config.

## Stories

- Story 12.1: Switch the AI assessment off for a Class session
- Story 12.2: Get an AI assessment with scores and a weighted total
- Story 12.3: Read written feedback that quotes my answer and matches my games
- Story 12.4: Be told when the AI assessment is ready
- Story 12.5: Flag feedback, and read assessments as staff
- Story 12.6: Show the Indicative letter where it is allowed
- Story 12.7: Set up a Control test in the operator's own Institution
- Story 12.8: Invite test students who consent before they take part
- Story 12.9: Score Control test answers blind
- Story 12.10: Compare human and AI scores and mark the Scoring guide as checked

## Requirements & Constraints

- The assessment counts toward nothing: no pass/fail, no grade. Every view (Student and staff) carries the disclosure «KI-generert, kan ta feil. Teller ikke. Ingen karakter.»; AI text carries the prefix «KI-generert, kan ta feil:». The email notice says the same and contains no score, letter or feedback text.
- The assessment is produced after the Test deadline (target within 24 hours of the attempt's `effective_deadline`, a target until measured). A timed or early submission is still not assessed before the original Test deadline.
- Per long-answer/Adapted item: one overall score on the Scoring guide's five-step scale, never per-criterion scores. Answer-key and Interactive items keep their computed scores and computed explanations; assessment never copies or recomputes them.
- No partial totals: any unassessed item makes the assessment `incomplete` (no total, no letter); after a configured max number of job runs it is `failed`, with notes shown to the Student.
- Switch off (pinned at the original Test deadline, with the Scoring guide): no assessment is created and no LLM call is made for assessment in that Class session; computed scores and the Student report still exist. An Admin stop (cost limit or choice) shows the same switched-off state for unready assessments; ready ones stay readable (assumption pending founder confirmation). Resume is one audited command that re-defers everything unfinished.
- Indicative letter: three Lecturer settings (shown to all, off with Student opt-in as default, unavailable); an Institution-level Admin switch forces "unavailable". Thresholds are editable until the first attempt opens. A Student's own opt-in is never exposed to staff or Admin and never goes into exports/ZIP; no letter for incomplete assessments.
- Feedback must quote the Student's own words, reference missing Scoring guide criteria, and cite only facts from the stored fact set; the Student sees "Ikke kontrollert med en Kontrolltest." unless the guide is checked for the pinned model config.
- Control test: never counts in a Class session or any list/statistic/report; only the Admin creates it; test students must consent (recorded with user, time, text version) before allocation; only the Admin and named scorers read its answers; human scores are immutable; the AI score for an item is hidden from a scorer until their own score for it is submitted.
- Agreement measures: exact agreement, within one step, systematic offset, scale compression, agreement by answer length. Missing human scores mean preliminary results and no "checked" mark.
- All Admin actions are audited; all numbers go through the shared number formatter; privacy: Roster names, emails and student numbers must never reach the provider.
- UI work needs Playwright at 320, 360 and 1440 px with axe, text labels (not colour alone), 44 px tap targets on phone. New Norwegian strings go in the copy file and are listed for founder review.

## Technical Decisions

- Module ownership: `modules/assessment` (backend and frontend) owns `ai_assessments`, `ai_item_scores`, `human_scores`, the assessment switch/stop mark per Class session, and the Student's letter choice. Other modules go through `assessment.service`, `content.service`, `identity.service`, `sessions.service`; `assessment` does not import `messaging`.
- Pure functions in shared `backend/app/analysis/`: `total_score(computed, ai_items, weights)`, `indicative_letter(total, thresholds)`, `agreement(human_scores, ai_scores)`. They are the only source of those values; golden-case pytest for each.
- Only `app/ai` talks to an LLM: `ai.run(purpose="assessment", budget_scope=<Class session>, ...)`, one call per item. Callers pass no model, prompt version or scrub terms, and never retry a typed failure (`timeout`, `provider_error`, `invalid_output`, `budget_exhausted`); retries happen only as a later deferred run of the idempotent `assess` job with back-off. The gateway scrubs PII and returns an offset map; the mock provider is used without a key. Assessment may spend the budget reserve.
- Prompts are versioned files under `backend/app/ai/prompts/assessment/`. A model config is immutable once referenced, so each new prompt version needs a new config row (command from Story 2.2); Class sessions pinned to an older config keep the old output shape.
- Job flow: `tests.commands.close_attempt` defers `assessment.assess(attempt_id)` on the `llm-batch` queue in the same transaction; the job is idempotent on `attempt_id`, reads only pinned versions (Scoring guide, question set, model config), and stores those plus `llm_call_id` on every row. `sessions.lock_test` (from Epic 11) is extended to pin the switch value alongside the Scoring guide, once and idempotently; afterwards the API rejects changes with a stable error code.
- Ready transition (same transaction): `progress.record_step(assessment_ready)` and `platform/notify.enqueue(kind="assessment_ready", dedupe_key=attempt id)` as a `digest` kind (max one mail per User per day, none 22:00-07:00 Europe/Oslo). `assessment_failed` goes once per Class session to each Admin. The Story 3.5 sweep gets an `assessment_overdue` action (structured log, ids only, once per assessment) and re-defers only when there is no live job and the run cap is not reached. Real-time updates via `session:<id>` and `user:<id>` events.
- AI text (AD-7): the LLM output holds quote spans over the scrubbed text, criterion codes, fact ids and approved sentence-template ids; code renders every number/cause. The validator rejects spans out of range and fact ids or numbers outside the item's stored `fact_set_id` (reuse Epic 9's validator; never rebuild the fact set). Spans map through the gateway offset map to the original text, which the view renders. A rejected feedback is regenerated exactly once, then dropped with a stored note while the score is kept. Stored text shape is `{text, ai_generated, llm_call_id}`.
- Authorization via `platform/authz` policies: Assistant lecturers read but do not change the switch; Studentside opens for Assistant lecturers (Tilrettelegging block stays hidden); outsiders get a denial that does not reveal existence; staff views never carry a Student's private letter choice; Control test answers and scores are limited to the Admin and named scorers, and scorers need no Admin role.
- Control test (AD-27): `class_sessions.kind` (`course` default, `control_test`) added in `modules/sessions`; `institutions` gets an operator-owned mark (one Institution at most) and a no-letter switch, both via `identity.service`; `is_test_student` on users plus a consent table via `identity.service`. It uses the ordinary Game purposes `class` and `replay`, its own budget row, and the ordinary Epic 4/5 screens (policies extended to the Control test owner). It pins the Scoring guide version and model config at creation. Allocation refuses users lacking consent. `sessions.service` exposes `kind` and `identity.service` exposes `is_test_student` so `reports.scope` (Epic 13) can exclude them; api tests must prove exclusion from every existing list, overview, funnel and statistic.
- Checked status: `content.service.mark_checked(scoring_guide_version_id, model_config_id)` (table in `modules/content`, created in 12.10) is called only by `assessment`, in the same transaction as the last submitted human score; `content.service.is_checked` (stubbed false from Story 11.2) reads it. Checked is per guide version plus model config; a guide edit or a different config is unchecked.
- With `FEATURE_RERUN` on and Story 5.18 built, the switch value, letter setting and thresholds are added to `sessions.service.copy_from`; otherwise nothing is added there.

## UX & Interaction Patterns

- Reuse Bryter («KI-vurdering»), Valgknapper (letter settings, scoring scale), shared chart components with «Vis som tabell», and the shared number formatter. Reused patterns: Lenke for list rows, text-labelled controls.
- Student states for «KI-vurdering» from Hjem: not ready («KI-vurderingen kommer innen ett døgn etter testfristen.»), switched off, ready, incomplete (note lists unassessed items), failed (note says computed scores are in the Student report). Feedback quotes are set apart as quotations of the Student's own text; dropped feedback shows a text note in its place.
- Flag control «Marker som feil»: a toggle with `aria-pressed`, no icon, no dialog; flagged state reads «Markert. Faglærer ser det.» with the text button «Angre»; failure shows «Det ble ikke lagret. Prøv igjen.».
- Lecturer block in Klasseøkt: switch with help text, letter setting with scope help text, thresholds, and a per-Student list (ready, flag count) linking to each Studentside; saved with «Lagre Klasseøkt».
- Student letter: a «Veiledende bokstav» control beside the total, labelled as an AI-generated indication that is not a grade, switchable off again.
- Admin «Kontrolltest»: shows «Teller aldri med i en Klasseøkt.» and the pinned guide version and model config; test students are labelled «Teststudent»; scorers see neutral item numbers (no names) and are marked scored/not scored in text; a one-way submit button labelled with its effect, the irreversibility stated above it, no dialog; the AI score appears only after the scorer's own score. Results page: side-by-side HTML table, five labelled measures, missing-count and "preliminary" text.

## Cross-Story Dependencies

- Depends on Epic 11: `tests.commands.close_attempt` (11.11), `sessions.lock_test`, timed sitting (11.12), Scoring guide and `content.service.is_checked` (11.2), draft block (11.1), Item weights; on Epic 9: AI-text validator, fact sets, `platform/pii.terms` Roster scrubbing (9.15); on Epic 8: Studentside page (8.9); on Epic 5: Bryter and Valgknapper, allocation (5.8, 5.9), optional `copy_from` (5.18); on Epic 4: Roster and invitation flow (4.4, 4.5); on Epics 2, 3: model config command (2.2), digest delivery and sweep (3.5), Institution list (3.11).
- Within the epic: 12.2 creates the tables and the `assess` job that 12.3 to 12.6 and 12.10 build on; 12.1's pinned switch must exist before 12.2 can skip assessment; 12.4 relies on 12.2 and 12.3 reaching "ready", and holds stop/resume commands that 12.2 and the sweep honour; 12.7 introduces `kind=control_test` and the pinned guide/config used by 12.8 to 12.10; 12.8 (consent) is required before allocation; 12.9's human scores feed 12.10's agreement and `mark_checked`, which then clears the unchecked notice shown in 12.3.
- Downstream: Epic 13 consumes the assessment read from `assessment.service`, applies `reports.scope` exclusion of Control tests and test students, and must assert the letter is no input to Completion; Epic 15 supplies the Admin screen that calls `stop_for_session`.
