# `modules/content`: immutable, versioned content (AD-23)

One table, `content_records(kind, version, body)`. A record never changes (a trigger refuses
UPDATE): an edit is a new version, `service.publish(kind, body)`, validated against the kind's
schema (`schemas.py`). Kinds: `starting_task` (Story 6.3); later epics add theirs.

- Version 1 of the Starting task is stored by migration 0046: placeholder items, among them
  «Regn posisjonen for én Uke». The final items (issue #16) arrive as a new version, with no
  code change: `uv run python -m app.modules.content starting_task items.json`.
- Each item is one column of the week table with given rows and one asked row; its answer is a
  signed sum of given rows (`terms`), scored by `analysis.scoring.score_sum`.
- The lock pins the version: `sessions` registers `starting_task_pin`, so every Class session
  locked from then on stores `{"version": N}` under `SessionRuntime.pins["starting_task"]`.
  Readers take `pinned_version(pins)`, or the latest for a session locked before the pin.
- This module imports no feature module.
