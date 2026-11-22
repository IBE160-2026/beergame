# Facts set of a finished Game (FR-44, AD-7) — rules

Status: **analysis version 2** (version 2 adds the Seat's «Simulert, samme kunder» rows; a set stored under version 1 has none and is never rebuilt); the Detected pattern thresholds are **placeholders**, to be reviewed by two lecturers before pilot (FR-44). The pattern thresholds live in the `detected_patterns` content record (version 1 stored by migration 0101), not in code; a reviewed set is a new version of that record. The other numbers here (an Order of 10 or more, 10 Student Orders, three moments) are code constants of `analysis/facts.py`: changing one is a new `ANALYSIS_VERSION`.

`analysis.facts(decision_log, seat, pattern_definitions)` reads the whole Decision log of a finished Game (one row per Role per Week, `state_seen` as the Seat saw it) and returns the facts set of one Seat. `games.facts.get_or_create(game, seat)` stores it once in `fact_sets`; everything that cites a fact stores that row's id.

## Numbers

- **Money** is summed exactly from the Decision log (`state_seen.cost_lines`, `week_cost`). The cost of Week *t* is the cost on Week *t*'s balances, as the play screen shows it; the chain's Total cost is the sum over every Role and Week.
- **Ratios and standard deviations** are rounded to 0.001 (half to even). Standard deviations are population standard deviations over the whole Game, Guided Weeks included.

## Chain part (the same for every Seat of the Game)

- `demand`: customer demand by Week, the first Role's incoming order.
- Per Role: `orders_std`; `amplification` = `orders_std / demand_std` (None when demand never varied, as in the constant-demand reference trace); `first_large_order_week`, the first Week with an Order of 10 or more (None when none); `holding_cost`, `backorder_cost` and `total_cost`.
- `ai_held_cost`: the cost of every Week in which a Seat's occupant was not a Student (`occupant_kind` ≠ `student`, the occupant in force when the Order was placed); `ai_held_share` = `ai_held_cost / total_cost` (None when the chain cost nothing).

## Seat part

- `student_orders`: the Seat's rows with `decided_by = student`. Fewer than 10: `sm_excluded` is true (the Student is left out of SM-1 and SM-2) and the Seat gets no own moments.
- `patterns`: every Detected pattern occurrence on the Seat's rows, except Guided Weeks (`decided_by = guided`: the Order is the starting demand, not a decision). AI Weeks are included and carry their `decided_by`. Id `<pattern>:<role>:<week>`. Each carries the Week, the Order, what the Seat saw, the later cost and what the other Roles saw that Week.
- **Later cost**: the Seat's cost over the `following_weeks` Weeks after the Week (4 in version 1), fewer at the end of the Game (`later_weeks` says how many; ranking uses the sum as it is). It is the Seat's cost whoever held the Seat in those Weeks, so after a Takeover it includes Weeks an AI player decided.

- `simulated` (version 2, Story 9.8): «Simulert, samme kunder», from `analysis.simulated.simulate`. The Game is played again from Week 1 with `engine.advance` over its settings (whose demand must equal the stored demand series) and its rules version. Guided Weeks order the starting demand; every later Order is the Rule-based rule's with the Game's frozen parameter set (`session_runtime.rule_based_params`, placeholders until issues #8 and #17). Row `own`: only this Seat counts På vei, the three others order with `beta` 0. Row `all`: every Seat orders with the set's `beta`. Each row is the chain's holding, backorder and total cost over the whole Game (inventory × holding cost and backlog × backorder cost of every Seat in every Week). None when the Game's frozen set is gone or has another version than the one it froze.

## Detected patterns (version 1, placeholders)

`inc` is the Seat's incoming order of the Week; "cover" of *k* Weeks means at least *k* × max(`inc`, 1) units.

| Pattern | Rule (all must hold) | Mechanism |
|---|---|---|
| `surge-after-shortage` — an Order well above incoming orders after a shortage | backlog > 0 in the Week or one of the 2 Weeks before (`lookback_weeks`); Order ≥ 1.5 × `inc` (`min_ratio`); Order − `inc` ≥ 4 (`min_excess`) | demand information lost in orders |
| `large-order-full-supply-line` — a large Order while the Supply line already holds a lot | Order ≥ 1.5 × `inc`; Order − `inc` ≥ 4; the Supply line the Seat saw covers 6 Weeks (`min_cover_weeks`) | Supply line |
| `low-after-overshoot` — very low Orders after an overshoot | Order ≤ 0.5 × `inc` (`max_ratio`); `inc` − Order ≥ 2 (`min_shortfall`); inventory covers 4 Weeks (`min_cover_weeks`), more than the Classic starting inventory of 12 at demand 4 | delay |

One Week can match more than one pattern.

## Own moments (at least 10 Student Orders only)

Exactly three, from Weeks with `decided_by = student` only, whatever the number of pattern occurrences:

1. Weeks with at least one pattern occurrence, highest later cost first, then the earlier Week (`chosen_by = pattern`).
2. If fewer than three, the other Student Weeks with the largest |Order − `inc`|, then the higher later cost, then the earlier Week (`chosen_by = order_gap`).

The moments are listed by Week, id `moment:<role>:<week>`, each with the ids of its Week's pattern occurrences (empty for an `order_gap` moment).
