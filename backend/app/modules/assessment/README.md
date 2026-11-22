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
