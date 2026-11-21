# `modules/content`: immutable, versioned content (AD-23)

One table, `content_records(kind, version, body)`. A record never changes (a trigger refuses
UPDATE): an edit is a new version, `service.publish(kind, body)`, validated against the kind's
schema (`schemas.py`). Kinds: `starting_task` (Story 6.3), `detected_patterns` (Story 9.1),
`sentence_templates` (Story 9.4); later epics add theirs.

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
