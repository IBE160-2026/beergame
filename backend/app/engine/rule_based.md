# Rule-based player

The Rule-based player orders by **anchoring and adjustment** (FR-33). It anchors on the orders it
expects to receive and adjusts for the gap between the stock it wants and the stock it has, and
for the gap between the supply line it needs and the supply line it has. It is deterministic: the
same Seat, settings and parameters always give the same Order.

Code: `app.engine.rule_based.order(settings, seat_view, params)`. Guided Weeks do not use it:
`app.engine.guided_order(settings)` returns the starting demand (FR-11).

## Inputs

Only the Seat's own numbers, from `app.engine.SeatView`:

- `L_1 … L_t`: the incoming orders of every Week so far (customer demand for the Retailer).
- `S = inventory − backlog`: effective inventory this Week.
- `SL`: supply line, the units the Seat has ordered and not yet received.

And the Game settings in force: order delay `d`, shipping delay `s` (production delay `p` for the
last Role, the Factory) and the maximum Order `M`. Neighbour numbers from Information visibility
are never read. Holding and backorder costs are not inputs of the rule. The Order history in
`SeatView` reaches the rule only through the supply line. With `theta` 0 the expectation stays
at the first incoming order (no smoothing).

## Formula

```
E_1 = L_1
E_k = θ · L_k + (1 − θ) · E_(k−1)          k = 2 … t     (expected incoming order)
lead = d + s − 1                            (d + p − 1 for the Factory)
SL*  = E_t · lead                           (desired supply line)
O*   = E_t + α_S · ((S* − S) + β · (SL* − SL))
O    = min(M, max(0, round_half_up(O*)))
```

In Sterman's (1989) notation the rule is `O* = L̂ + α_S·(S′ − S − β·SL)` with `β = α_SL/α_S`.
Here `S′ = S* + β·SL*`, with `S* = desired_inventory` and `SL*` recomputed from the expected
incoming order each Week, so `beta` plays the paper's β and `alpha_s` its α_S. The names line
up, but the behaviour need not: the paper's `S′` is a constant, while `SL*` here follows the
expected incoming order, and `E_t` here already includes this Week's incoming order. Whoever
enters the paper's fitted values (issues #8 and #17) must check both points against the paper
and split its `S′` into `desired_inventory` and the supply-line term.

`lead` is the number of Weeks of demand a Seat holds in its supply line just before it orders,
when every Order equals demand. With the Classic delays (2/2/2), `lead` is 3, so a Seat with
demand 4, inventory 12, no backlog and a supply line of 12 orders exactly 4.

## Parameters

| Name | Meaning |
| --- | --- |
| `theta` (θ) | weight of the newest incoming order in the expected incoming order, 0 to 1 |
| `alpha_s` (α_S) | share of the stock gap corrected in one Order, 0 to 1 |
| `beta` (β) | weight of the supply-line gap relative to the stock gap, 0 to 1 (0 = supply line ignored) |
| `desired_inventory` (S*) | effective inventory the Seat aims for, in units |

A parameter set is a JSON file `backend/app/parameter_sets/rule_based/<id>.json` with `id`,
`version`, `verified`, `source` and the four values. A new set is a new file, chosen by id
(`python -m app.sim trace --orders rule_based --rule-based-params <id>`); no code changes.

## Source of the final values

The rule follows Sterman, J. D. (1989), "Modeling Managerial Behavior: Misperceptions of
Feedback in a Dynamic Decision Making Experiment", *Management Science* 35(3), 321–339. The
final parameter values must be taken from that paper (issues #8 and #17).

The only set shipped, `placeholder-unverified`, holds round placeholder values chosen only so the
Classic chain stays in balance. They are not the paper's fitted values, and no value comes from a
calculator site. Every trace played with it prints a warning saying so.
