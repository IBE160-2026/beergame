# Rules versions

Decision (Story 1.10, AD-4): how older `rules_version`s stay runnable.

- **One package per version.** Each rules version is its own package `app/engine/rules/v<N>/`,
  exposing `initial_state(settings)` and `advance(settings, state, orders)`. A package refuses
  bad input only with a `ValueError` (`InvalidOrdersError`, `GameFinishedError` from
  `app/engine/errors.py`), so `engine.replay` can record the refusal as a violation.
- **Selection.** `engine.advance(settings, state, orders, rules_version)` and
  `engine.initial_state(settings, rules_version)` run the package that
  `app.engine.rules.package(rules_version)` returns. A missing package raises
  `UnknownRulesVersionError`.
- **New Games.** `games.commands.create` stores `RULES_VERSION` (in `app/engine/rules/__init__.py`)
  in the Game's snapshot. Every later command and the finished-game check use the stored version,
  so a running Class session keeps the version frozen in its snapshot.
- **Changing the rules.** A change that alters any engine output is made as a new package
  `v<N+1>` (start from a copy of the newest), and `RULES_VERSION` moves to it. A version that any
  stored non-simulation Game references is never edited. Refactors that keep every output equal
  may touch an existing version only if all its golden traces still pass unchanged.
- **Proof.** CI runs the golden traces of every packaged version
  (`tests/engine/test_golden.py`, `GOLDEN_TRACES`; a version without traces fails). A test fails
  when a `rules_version` stored on a Game has no package
  (`games.service.rules_versions_without_package`). `games.service.verify_finished` replays every
  finished Game at its stored version.
- **Capacity (Story 1.12).** `GameSettings.capacity` was added to v1, not to a new v2: with
  `capacity` unset (the default, and the only value any Game stored before it existed could
  have) every v1 output is unchanged, which its golden traces prove; the capped arithmetic has
  its own v1 trace (`capped-retailer-6.json`). The shared conservation check was extended in
  place the same way (capacity in `shipment`; `inventory_and_backlog` skips capped Seats).
  `FEATURE_CAPACITY` gates only new settings (`validate`); a stored Game always runs, replays
  and is checked with the capacity in its snapshot, whatever the flag says now. The Rule-based
  player and the Guided Order do not read capacity.
- **Not versioned yet.** The conservation check (`engine.check`), the demand series, the
  Rule-based player, the Guided Order and the Seat views are shared by all versions. A version
  that changes what they must compute brings its own variant then and selects it the same way.
