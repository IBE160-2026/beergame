"""Pure analysis of stored play (AD-1): no I/O, no clock; imports only the stdlib, pydantic and
`app.engine`.

- `play_guard`: the Play guard statistics (`evaluate`, `is_calibrated`, FR-79).
- `scoring`: computed scoring rules for answers (`score_sum`, the Starting task, FR-85).
- `class_cost`: «Klassens kostnad», the finished games' cost median and split (Story 7.6).
- `wall`: the Matrisevegg's class median and chain cost rows (`wall_aggregates`, Story 7.4).
"""
