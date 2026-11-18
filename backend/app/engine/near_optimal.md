# Near-optimal reference Order

The second reference Order of every Seat and Week (FR-67, FR-79). The Rule-based reference
shows what a plain human-like rule orders; the near-optimal reference shows what a Seat would
order **with knowledge beyond its own view**. The function receives every Seat's state and the
customer demand of every Week; `placeholder-0` uses the Seat itself, its supplier's order queue
and backlog, and future customer demand. It is not a whole-chain (echelon) optimiser.
No player ever sees it: it is stored on the turn and in the Decision log, never in the
`SeatState`, the LLM prompt or `state_seen` (AD-3).

Code: `app.engine.near_optimal.order(settings, chain_state, demand_series, week, role)`. The
turn stores the Order and `near_optimal.ALGORITHM_VERSION`.

## Algorithm `placeholder-0`

A placeholder until the prototype settles the algorithm (issue #20). It is order-up-to with
known customer demand: the Seat brings its inventory position up to a target plus the demand of
the Weeks before a new Order can arrive.

```
g        = production delay for the last Role (the Factory), else shipping delay
cover    = D(t+1) + … + D(t + order_delay + g)      (D after the last Week = last value)
target   = starting_inventory − starting_backlog
SL       = Σ own goods_slots
           + Σ upstream incoming_orders[1:] + upstream backlog      (not the last Role)
           + Σ own production_orders[1:]                            (the last Role)
position = inventory − backlog + SL
O        = min(max_order, max(0, target + cover − position))
```

- `D(k)` is customer demand in Week `k`. Every Seat plans on customer demand, as if the chain
  passed it on unchanged; that is the full-knowledge part.
- `SL` is the supply line read from the chain state: index 0 of an order queue was received
  when the Week opened, so it is already in the goods or the supplier's backlog. It equals the
  supply line of the Seat's own view (`seat_view`), which counts it from the Order history.
- `cover` deliberately runs past the last Week (with the last demand value): no end-of-Game
  run-down, so under constant demand it coincides with the Rule-based reference in every Week,
  as Story 2.9 requires. Capacity caps are not taken into account either.
- `target` is the Game's opening effective inventory. With it, the reference coincides with the
  Rule-based reference in the Classic equilibrium: `12 + 4·4 − (12 + 12) = 4`.

Worked example, Classic step (4, then 8 from Week 5), Week 1, any Role: `cover = 4+4+4+8 = 20`,
`position = 12 + 12 = 24`, so `O = 12 + 20 − 24 = 8`.

## A new algorithm

A new algorithm is a new function in `ALGORITHMS` under a new label, and `ALGORITHM_VERSION`
names it. Callers do not change; stored references keep the label they were computed with, and
the golden file `tests/engine/golden/near-optimal-classic-step.json` shows the change as a diff.
