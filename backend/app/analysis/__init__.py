"""Pure analysis of stored play (AD-1): no I/O, no clock; imports only the stdlib, pydantic and
`app.engine`.

- `play_guard`: the Play guard statistics (`evaluate`, `is_calibrated`, FR-79).
- `scoring`: computed scoring rules for answers (`score_sum`, the Starting task, FR-85).
- `facts`: the facts set of one Seat of a finished Game (`facts`, FR-44, AD-7), with the Detected
  pattern definitions and their rules in `patterns`; the rules are documented in `facts.md`.
- `sentences`: the sentence templates' shape and the code-rendered Debrief text
  (`demand_heading`, Story 9.4, AD-7).
- `moments`: the own moments rendered from a stored facts set (`render`, Story 9.7, FR-44, AD-7).
"""
