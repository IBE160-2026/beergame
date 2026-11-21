"""Pure analysis of stored play (AD-1): no I/O, no clock; imports only the stdlib, pydantic and
`app.engine`.

- `play_guard`: the Play guard statistics (`evaluate`, `is_calibrated`, FR-79).
- `scoring`: computed scoring rules for answers (`score_sum`, the Starting task, FR-85).
- `facts`: the facts set of one Seat of a finished Game (`facts`, FR-44, AD-7), with the Detected
  pattern definitions and their rules in `patterns`; the rules are documented in `facts.md`.
- `sentences`: the sentence templates' shape and the code-rendered Debrief text
  (`demand_heading`, Story 9.4, AD-7).
- `moments`: the own moments rendered from a stored facts set (`render`, Story 9.7, FR-44, AD-7).
- `simulated`: «Simulert, samme kunder», the Game played again by the Rule-based rule with only
  the viewer's Seat, then every Seat, counting På vei (`simulate`, Story 9.8, FR-44); stored in
  the facts set.
- `quiz`: the Debrief quiz's shape, its scoring by answer key and the own-game sentence of an
  explanation from a stored facts set (`score`, `render_in_your_game`, Story 9.9, FR-46).
"""
