# `modules/content`: immutable, versioned content (AD-23)

One table, `content_records(kind, version, body)`. A record never changes (a trigger refuses
UPDATE): an edit is a new version, `service.publish(kind, body)`, validated against the kind's
schema (`schemas.py`). Kinds: `starting_task` (Story 6.3), `detected_patterns` (Story 9.1),
`sentence_templates` (Story 9.4), `reflection_questions` (Story 9.6), `moment_templates`
(Story 9.7); later epics add theirs.

- Version 1 of the Starting task is stored by migration 0046: placeholder items, among them
  «Regn posisjonen for én Uke». The final items (issue #16) arrive as a new version, with no
  code change: `uv run python -m app.modules.content starting_task items.json`.
- Each item is one column of the week table with given rows and one asked row; its answer is a
  signed sum of given rows (`terms`), scored by `analysis.scoring.score_sum`.
- The lock pins the version: `sessions` registers `starting_task_pin`, so every Class session
  locked from then on stores `{"version": N}` under `SessionRuntime.pins["starting_task"]`.
  Readers take `pinned_version(pins)`, or the latest for a session locked before the pin.
- This module imports no feature module.
- Version 1 of the Detected pattern definitions is stored by migration 0101: the three patterns
  of FR-44 with placeholder thresholds, each marked "to be reviewed by two lecturers before pilot".
  Their shape is `analysis.patterns.PatternSet` and their rules are in `app/analysis/facts.md`. A
  reviewed set is a new version: `uv run python -m app.modules.content detected_patterns file.json`.
  The lock pins it under `SessionRuntime.pins["detected_patterns"]` (`detected_patterns_pin`);
  `pinned_version(pins, Kind.DETECTED_PATTERNS)` reads it.
- Version 1 of the sentence templates is stored by migration 0104: the five variants of the
  Debrief's step-2 heading (`demand-flat`, `demand-step`, `demand-step-noise`, `demand-random`,
  `demand-varied`). Their shape is `analysis.sentences.SentenceTemplates`: every demand variant
  present, each using only the values its id is given, no exclamation mark. Code fills every
  number (AD-7). The lock pins the version under `SessionRuntime.pins["sentence_templates"]`
  (`sentence_templates_pin`); `pinned_version(pins, Kind.SENTENCE_TEMPLATES)` reads it.
- Version 1 of the own moments' templates is stored by migration 0106 (draft copy, Issue #31):
  step 4's heading, each moment's heading, «Dette regnet du» (the Posisjon sum), «Dette kostet
  det senere», a Detected pattern by name and definition, its mechanism, and the gap sentences of
  a moment with no pattern. Their shape is `analysis.sentences.MomentTemplates`: exactly the ids
  of `MOMENT_TEMPLATES`, each using only its values, no exclamation mark and no cause word;
  `analysis.moments.render` fills them (AD-7). The lock pins the version under
  `SessionRuntime.pins["moment_templates"]` (`moment_templates_pin`).
- Version 1 of the narration templates (Story 9.14) is stored by migration 0112 (draft copy): the
  sentences an LLM may connect with fact ids (`narration-orders`, `narration-supply-line`,
  `narration-later-cost`, `narration-weeks`). Their shape is
  `analysis.narration.NarrationTemplates`: exactly those ids, slots `<value>_<n>` for the `n`-th
  cited fact, every cited fact used, no cause word. The lock pins the version under
  `SessionRuntime.pins["narration_templates"]` (`narration_templates_pin`).
- Version 2 of the narration templates (Story 9.15) is stored by migration 0113: version 1's four
  sentences and the follow-up's hint templates (`hint-row`, `hint-supply-line`, `hint-later`,
  `hint-compare`, draft copy), which point to where to look. A version holds every narration id
  and may hold the hint ids (`analysis.narration.HINT_TEMPLATES`); a Class session locked on
  version 1 has no follow-up questions.

- Version 1 of the question set (Story 11.1) is stored by migration 0121 and shipped as
  `files/question_set.json` (a test keeps them equal): placeholder Core items marked
  `status: "draft"` until issue #16, each with a type (`choice`, `table`, `number`, `long`; no
  diagram in v1), a default Item weight, an answer key or scoring rule id and tags; the Starting
  task items are referenced by id (`starting_task_item`), never copied, and `publish` refuses a set
  that misses one of the latest Starting task's items (`starting_task_items_missing`). Its shape
  and rules are `schemas.QuestionSet`. The selection per Class session and its pin belong to
  `modules/tests` (`selection.py`, `SessionRuntime.pins["question_set"]`).
- Version 2 of the question set (Story 11.5) is stored by migration 0124 and is now what
  `files/question_set.json` holds: every table item and every number item that is not a Starting
  task item has its own table and computed rule (`interactive`: prompt, rows, given columns, asked
  label, `negative`, coded criteria whose shape is `analysis.scoring.InteractiveRule`); the load
  refuses one without it (`interactive_missing`). Version 1 stays as it was for sessions pinned to
  it. Interactive text says «enheter», never «øl».
- The content load (Story 11.1): `uv run python -m app.modules.content load [folder]` publishes
  every `<kind>.json` of `files/` (or the folder) that differs from its kind's newest version;
  a second run publishes nothing. A refused file prints a stable code (`unknown_kind`,
  `unknown_item_type`, `interactive_missing`, `starting_task_items_missing`, `invalid_record`)
  and the command exits 1.
- Version 1 of the Scoring guide (Story 11.2) is stored by migration 0122 and shipped as
  `files/scoring_guide.json` (a test keeps them equal): one fixed five-step scale (0 to 4) and,
  per long-answer question (its id the item's `scoring_rule`) and Adapted item template, a title,
  the descriptive guide text and 5 to 8 coded criteria whose weights sum to 100, marked
  `status: "draft"` until issue #16. Its shape is `schemas.ScoringGuide`; a question with fewer
  than 5 or more than 8 criteria is refused with `criteria_count`. A Lecturer's edit is a new
  version made for one Class session (`publish_in(..., class_session_id=…)`,
  `content_records.class_session_id`): it takes the kind's next number but is never the latest
  default, and the load never compares a file with it. Which version a Class session uses, and
  its pin at the Test deadline, belong to `modules/tests` (`guide.py`).
- Version 1 of the Adapted item templates (Story 11.7) is stored by migration 0125 and shipped as
  `files/adapted_templates.json` (a test keeps them equal): per template its id (the Scoring
  guide's `adapted` question), the Game it reads (`game` or `replay`), the fact kind it needs
  (`moment`, `pattern` or `outcome`), which fact (`pick`), its share of the Adapted total weight
  (the shares sum to 100) and its text with `{slot}`s code fills, marked `status: "draft"` until
  issue #16. Its shape and renderer are `analysis.adapted`; the lock pins the version
  (`adapted_templates_pin`, `SessionRuntime.pins["adapted_templates"]`).
- `is_checked(scoring_guide_version_id, model_config_id)` is the one answer to whether a Control
  test has checked a Scoring guide version (AD-27); it is False until Epic 12 adds the record.
