# `modules/assessment`: the AI assessment (Epic 12)

Owns `assessment_switches` (Story 12.1). Other modules import only `assessment.service`; this
module imports no other module (`tests/test_imports.py`).

## The «KI-vurdering» switch (Story 12.1, FR-61, AD-9, AD-12)

- `assessment_switches` (migration 0120): one row per Class session whose switch was saved off (or
  on again) or pinned; no row reads as on (`DEFAULT_SWITCH`). `pinned_at` is set once by the
  Test-deadline lock, as of the original Test deadline even when the sweep runs late; a trigger
  (`assessment_switches_pinned`) refuses any update of a pinned row (not a delete, so a Class
  session's cascade still removes it).
- `set_switch(s, id, enabled, now=)` stores it in the caller's transaction: «Lagre Klasseøkt»
  (`sessions.save_session`, which holds the Class session's row lock and judges the rules first:
  owners only through `ai_assessment.change`, 409 `ai_assessment_pinned` once the original Test
  deadline has passed or the switch is pinned). An unchanged value stores nothing.
- `pin_switch(s, id, now=)` pins the value as it stands, once: `sessions.lock_test`, the sweep's
  `sessions.lock_test` due action at the original Test deadline (Epic 11 adds the Scoring guide pin
  to the same function and closes the attempts after it).
- `copy_switch` gives a copy («Lag kopi», Story 5.18) the source's value, never its pin.
- `assessment_due(id)` is the one gate of the assessment: True only for a pinned switch that is
  on. Story 12.2's `assess` job and `tests.close_attempt` ask it before they create an assessment
  or make any LLM call, so nothing is assessed before the Test deadline and nothing at all while
  the pinned switch is off. The Student report and the computed scores do not depend on it.
- The Klasseøkt reads it as `ClassSessionOut.ai_assessment` (`enabled`, `pinned_at`, `open`,
  `can_change`); Assistant lecturers read it with the Class session (`class_sessions.read`) but
  never change it (`ai_assessment.change` is the owners').

## Flags and the staff read (Story 12.5, FR-55, AD-12)

- `ai_feedback_flags` (migration 0205): one row per piece of written feedback the Student marked
  as wrong, keyed by assessment and item, with a composite foreign key to `ai_item_scores` (gone
  with the score or the assessment). `set_flag(attempt_id, item_id, flagged, now=)` stores or
  removes it idempotently and emits `user` and `session`; `tests.assessed.set_flag` judges first
  that the Student's view shows that feedback now (409 `feedback_not_flaggable` otherwise).
- `AssessmentRecord.flags` carries the flagged items; `summaries_for_session(s, id)` gives each
  Student's attempt, state, runs and flag count (the Klasseøkt's list; Epic 13 reads the same).
- Staff read through `tests` routes: `GET /api/class-sessions/{id}/students/{user_id}/assessment`
  (`StaffAssessmentOut`, a separate schema so a Student-only field never reaches staff) and
  `GET /api/class-sessions/{id}/assessments`, both `ai_assessments.read` (owners and Assistant
  lecturers of the Class; never the Admin role alone).

## The Indicative letter (Story 12.6, FR-56, AD-1, AD-12)

- Migration 0206: `assessment_switches.letter_setting` (`all`, `student_choice` by default,
  `unavailable`) and `letter_thresholds` (the lower bounds of A to E in whole percent of the
  total's maximum; NULL for the configured defaults, `indicative_letter_thresholds`), both pinned
  with the switch (the pin stores the bounds in force; the trigger refuses a later change);
  `ai_assessments.letter_chosen`, the Student's own opt-in; `institutions.no_letter` (owned by
  `identity`).
- `set_letter(s, id, setting=, thresholds=, now=)` stores what «Lagre Klasseøkt» judged
  (`sessions._judge_letter`: owners only, while the switch can change, bounds read-only once a Test
  attempt exists, only `unavailable` while the Institution forbids the letter); `copy_switch` also
  copies the letter setting and the stored bounds.
- `letter_rules(switch, institution_forbids=)` is the rule in force; `sessions.letter_rules(s, id)`
  reads the Institution's mark through `identity.service` for `tests`.
- `letter_for(rules, total=, total_max=, ready=, opted_in=, reader=, requested_by_student=)` is
  the one place that decides who gets a letter: the Student's own view (`all`, or their opt-in),
  the staff only when `all`, never an export or a ZIP, a report only when the Student asks for it.
  The letter itself is `analysis.indicative_letter` only; none for an assessment that is not
  ready. It is never an input to Completion (Epic 13 asserts that).
- `set_letter_choice(attempt_id, on)` stores the Student's «Veiledende bokstav» (emits `user`, not
  audited); `tests.assessed.set_letter_choice` judges first that the view leaves the letter to them
  (409 `letter_not_available`).
