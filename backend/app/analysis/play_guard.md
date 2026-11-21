# Play guard (FR-79) — placeholder parameters

Status: **placeholder** (`placeholder-0`, `verified: false`). The distance measure, the window, the minimum number of Weeks, both limits and the large deviation are to be set in prototype testing (issue #20). The near-optimal reference it compares with is itself a placeholder (`engine/near_optimal.md`).

## What the guard reads

The Seat's Decision log rows with `decided_by = llm`. Guided Weeks and fallback Orders (`decided_by = rule_based`, which equal the Rule-based reference) never count. Each row holds the Order and the two reference Orders stored on the turn when the Week opened: Rule-based (RB) and near-optimal (NO).

## The band

The window is the Seat's newest `window_weeks` `llm` Orders. With fewer than `minimum_weeks` `llm` Orders the guard never switches.

1. **Lower limit (sensible play):** the share of the window's Orders with |Order − RB| ≤ `lower_distance` must be at least `lower_share`. Otherwise the result is `switch`, statistic `lower_share`.
2. **Upper limit (not suspiciously near-optimal):** over the window's Weeks where NO ≠ RB, the mean of |Order − NO| / |RB − NO| (0 = at near-optimal, 1 = at Rule-based) must be at least `upper_margin`. Otherwise the result is `switch`, statistic `upper_closeness`. Weeks where the references coincide do not count, and neither do Weeks with no stored NO (turns opened before Story 2.9). With no Week left the limit is not applied.

## Uncalibrated settings

The band is calibrated only for the settings profiles named in the set (`calibrated_profiles`; `classic` = `GameSettings()`, the demand seed ignored). Under any other settings the upper limit is not applied. Only a large deviation switches: the lower limit with `large_distance` instead of `lower_distance` (statistic `large_deviation`).

Story 10.1 added the profile `replay_default` in the set `placeholder-1` (the default for new Games): a profile may be a `ReplayTemplate` instead of one `GameSettings`, and then every draw of it counts as calibrated (`engine.replay_template_admits`). `replay_default` is `engine.default_replay_template(GameSettings())`: the Classic settings with demand 4 then 8 and a spread of 2, the step Week 5 to 12, 30 to 40 Weeks and no Guided Weeks. An own Replay scenario with other settings is not calibrated. `placeholder-1` is a new set rather than version 2 of `placeholder-0`, so Games that froze `placeholder-0` version 1 keep running; its other values are `placeholder-0`'s.

## Placeholder values (`placeholder-0` and `placeholder-1`)

Both sets hold these values; `placeholder-1` only adds the `replay_default` profile (a test keeps the two equal). Calibrating the band (issue #20) is a new set that the default then names.

| Parameter | Value |
|---|---|
| distance | `absolute_units` (|Order − reference| in units) |
| window_weeks | 8 |
| minimum_weeks | 8 |
| lower_distance | 4 units |
| lower_share | 0.95 |
| upper_margin | 0.05 |
| large_distance | 16 units |

With a window of 8, a share of 0.95 means a single Order outside the distance in the window switches the Seat. The values were chosen so that the scripted test players separate clearly. They are not calibrated.

## Where it runs

`games.commands.place_order` runs it for every `decided_by = llm` Order, in the same transaction, over the Seat's stored rows plus the new one. On `switch` it appends an occupancy row `rule_based`, reason `guard_switch`, `from_week = week + 1`. The Seat is Rule-based for the rest of the Game. A switch on the last Week's Order still writes its row (`from_week` = Weeks + 1), so the switch is recorded. The occupancy history (`games.service.occupancy_history`) gives the Week. The `ai-orders` job never runs the guard. A Game freezes the set's id and version in its `SessionRuntime`. A changed version is refused (`parameter_set_changed`), as for the Rule-based set.
