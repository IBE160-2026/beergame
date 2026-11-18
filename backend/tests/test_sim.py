import json
from pathlib import Path
from unittest import mock

import pytest

from app.sim import main

GOLDEN = Path(__file__).parent / "engine" / "golden"


def run(capsys, *argv):
    code = main(["trace", *argv])
    return code, capsys.readouterr().out.splitlines()


def test_trace_classic_constant_orders(capsys):
    code, lines = run(capsys, "--settings", "classic", "--orders", "constant:4")
    assert code == 0
    assert len(lines) == 1 + 36 * 4
    assert lines[0].split() == [
        "week",
        "role",
        "incoming_order",
        "incoming_delivery",
        "shipped",
        "inventory",
        "backlog",
        "order",
        "cost",
    ]
    assert lines[1].split() == ["1", "retailer", "4", "4", "4", "12", "0", "4", "6.00"]
    assert lines[-1].split()[:2] == ["36", "factory"]


def test_trace_pass_through_is_the_default(capsys):
    code, lines = run(capsys)
    assert code == 0
    week5_retailer = lines[1 + 4 * 4].split()
    assert week5_retailer == ["5", "retailer", "8", "4", "8", "8", "0", "8", "4.00"]


@pytest.mark.parametrize("spec", ["constant", "constant:-1", "constant:x", "random:4", ""])
def test_bad_orders_spec_exits_2(capsys, spec):
    with pytest.raises(SystemExit) as info:
        main(["trace", "--orders", spec])
    assert info.value.code == 2
    assert "--orders" in capsys.readouterr().err


def test_order_above_max_order_exits_2(capsys):
    with pytest.raises(SystemExit) as info:
        main(["trace", "--orders", "constant:1000"])
    assert info.value.code == 2
    assert "cannot exceed 999" in capsys.readouterr().err


def test_unknown_settings_and_missing_command_exit_2():
    with pytest.raises(SystemExit) as info:
        main(["trace", "--settings", "modern"])
    assert info.value.code == 2
    with pytest.raises(SystemExit) as info:
        main([])
    assert info.value.code == 2


def test_pass_through_trace_matches_the_hand_worked_golden(capsys):
    golden = json.loads((GOLDEN / "classic-step-pass-through.json").read_text(encoding="utf-8"))
    code, lines = run(capsys, "--settings", "classic")
    assert code == 0
    rows = [line.split() for line in lines[1 : 1 + len(golden["rows"])]]
    expected = [
        [
            str(row["week"]),
            row["role"],
            str(row["incoming_order"]),
            str(row["incoming_delivery"]),
            str(row["shipped"]),
            str(row["inventory"]),
            str(row["backlog"]),
            str(golden["orders"][row["week"] - 1][row["role"]]),
            row["cost"],
        ]
        for row in golden["rows"]
    ]
    assert rows == expected


def test_invalid_orders_print_no_rows(capsys):
    with pytest.raises(SystemExit):
        main(["trace", "--orders", "constant:1000"])
    assert capsys.readouterr().out.splitlines()[1:] == []  # header only, no Week rows


def check(capsys, tmp_path, content):
    path = tmp_path / "settings.json"
    path.write_text(content, encoding="utf-8")
    code = main(["settings", "check", str(path)])
    return code, capsys.readouterr().out.splitlines()


def test_settings_check_reports_a_range_error_and_exits_1(capsys, tmp_path):
    code, lines = check(capsys, tmp_path, '{"order_delay": 4, "weeks": 20}')
    assert code == 1
    errors = [line for line in lines if line.startswith("error ")]
    assert len(errors) == 1
    assert errors[0].startswith("error out_of_range order_delay: ")
    assert "1..3" in errors[0]
    assert "placeholder" not in errors[0]


def test_settings_check_marks_placeholder_ranges(capsys, tmp_path):
    code, lines = check(capsys, tmp_path, '{"weeks": 500}')
    assert code == 1
    assert lines[0].startswith("error out_of_range weeks: ")
    assert lines[0].endswith("[allowed 1..100 (placeholder)]")


def test_settings_check_prints_warnings_and_exits_0(capsys, tmp_path):
    code, lines = check(capsys, tmp_path, '{"weeks": 20}')
    assert code == 0
    assert len(lines) == 1
    assert lines[0].startswith("warning too_few_weeks_for_demand_change weeks: ")
    assert "arrival_week=21" in lines[0]
    assert "weeks=20" in lines[0]


def test_settings_check_classic_is_ok(capsys, tmp_path):
    assert check(capsys, tmp_path, "{}") == (0, ["OK"])


def test_settings_check_reads_rates_as_decimals(capsys, tmp_path):
    code, lines = check(capsys, tmp_path, '{"holding_cost": 0.505}')
    assert code == 1
    assert lines[0].startswith("error too_many_decimal_places holding_cost: ")
    assert "0.505" in lines[0]
    assert lines[0].endswith("[allowed 0.00..100.00 (placeholder)]")


def test_settings_check_shows_a_range_whose_minimum_is_zero(capsys, tmp_path):
    code, lines = check(capsys, tmp_path, '{"starting_inventory": 0, "starting_backlog": 101}')
    assert code == 1
    assert lines[0].endswith("[allowed 0..100 (placeholder)]")


def test_settings_check_reads_a_file_with_a_byte_order_mark(capsys, tmp_path):
    path = tmp_path / "settings.json"
    path.write_bytes(b'\xef\xbb\xbf{"weeks": 20}')
    assert main(["settings", "check", str(path)]) == 0
    assert capsys.readouterr().out.startswith("warning too_few_weeks_for_demand_change")


def test_settings_check_cross_field_error_has_no_range(capsys, tmp_path):
    code, lines = check(capsys, tmp_path, '{"guided_weeks": 5}')
    assert code == 1
    assert lines[0].startswith("error guided_weeks_not_before_demand_change guided_weeks: ")
    assert "allowed" not in lines[0]


def test_settings_check_refuses_capacity_when_feature_capacity_is_off(
    capsys, tmp_path, monkeypatch
):
    monkeypatch.setenv("FEATURE_CAPACITY", "false")
    code, lines = check(capsys, tmp_path, '{"capacity": {"retailer": 6}}')
    assert code == 1
    assert lines[0].startswith("error capacity_disabled capacity: ")


def test_settings_check_capacity_warns_below_peak_demand(capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("FEATURE_CAPACITY", "true")
    code, lines = check(capsys, tmp_path, '{"capacity": {"retailer": 6}}')
    assert code == 0
    assert lines == [
        "warning capacity_below_peak_demand capacity.retailer: the retailer can ship at most 6 "
        "a Week, below peak demand (8), so it cannot keep up while demand is at its peak "
        "[role=retailer, capacity=6, peak_demand=8]"
    ]


@pytest.mark.parametrize("value", ["0", "6.5", '"6"'])
def test_settings_check_capacity_shows_its_range(capsys, tmp_path, monkeypatch, value):
    monkeypatch.setenv("FEATURE_CAPACITY", "true")
    code, lines = check(capsys, tmp_path, f'{{"capacity": {{"retailer": {value}}}}}')
    assert code == 1
    assert lines[0].startswith("error ")
    assert " capacity.retailer: " in lines[0]
    assert lines[0].endswith("[allowed 1..100 (placeholder)]")


@pytest.mark.parametrize("capacity", ['{"shop": 6}', "6", '{"factory": 6}'])
def test_settings_check_capacity_shape_errors_show_no_range(capsys, tmp_path, capacity):
    content = f'{{"roles": ["retailer", "wholesaler"], "capacity": {capacity}}}'
    code, lines = check(capsys, tmp_path, content)
    assert code == 1
    assert lines[0].startswith("error invalid capacity")
    assert "allowed" not in lines[0]


def test_settings_check_reports_pydantic_errors_as_invalid(capsys, tmp_path):
    content = '{"order_delay": 0, "colour": "red", "demand": {"kind": "step"}}'
    code, lines = check(capsys, tmp_path, content)
    assert code == 1
    assert all(line.startswith("error invalid ") for line in lines)
    by_field = {line.split()[2].rstrip(":"): line for line in lines}
    assert by_field["order_delay"].endswith("[allowed 1..3]")
    assert "allowed" not in by_field["colour"]
    assert "demand.start" in by_field


@pytest.mark.parametrize("content", [b"not json", b"[1, 2]", b"4", b"\xff\xfe"])
def test_settings_check_bad_file_exits_2(capsys, tmp_path, content):
    path = tmp_path / "settings.json"
    path.write_bytes(content)
    with pytest.raises(SystemExit) as info:
        main(["settings", "check", str(path)])
    assert info.value.code == 2
    assert "settings.json" in capsys.readouterr().err


def test_settings_check_missing_file_exits_2(capsys, tmp_path):
    with pytest.raises(SystemExit) as info:
        main(["settings", "check", str(tmp_path / "missing.json")])
    assert info.value.code == 2
    assert "cannot read" in capsys.readouterr().err


def test_settings_needs_a_subcommand():
    with pytest.raises(SystemExit) as info:
        main(["settings"])
    assert info.value.code == 2


# Story 1.4: `demand` prints a series and its seed.

GOLDEN_STEP_NOISE_42 = (
    "4 3 2 2 7 10 6 7 7 8 7 10 10 7 7 9 9 8 7 8 8 9 9 8 10 6 10 7 6 8 8 7 10 7 9 6"
)


def demand(capsys, *argv):
    code = main(["demand", *argv])
    return code, capsys.readouterr().out.splitlines()


def test_demand_step_plus_noise_with_a_seed_repeats(capsys):
    first = demand(capsys, "--pattern", "step+noise", "--seed", "42")
    again = demand(capsys, "--pattern", "step+noise", "--seed", "42")
    assert first == again == (0, ["seed 42", f"series {GOLDEN_STEP_NOISE_42}"])


def test_demand_without_a_seed_draws_one_that_reproduces_the_series(capsys):
    code, lines = demand(capsys, "--pattern", "random")
    assert code == 0
    seed = lines[0].removeprefix("seed ")
    assert 0 <= int(seed) <= 999_999_999
    assert demand(capsys, "--pattern", "random", "--seed", seed)[1] == lines


def test_demand_defaults_to_the_classic_step(capsys):
    code, lines = demand(capsys, "--weeks", "7", "--seed", "1")
    assert (code, lines) == (0, ["seed 1", "series 4 4 4 4 8 8 8"])


def test_demand_fixed_series(capsys):
    code, lines = demand(capsys, "--pattern", "fixed", "--values", "4,6,9", "--weeks", "3")
    assert (code, lines[1]) == (0, "series 4 6 9")


def test_demand_reports_rule_errors_with_their_range(capsys):
    code, lines = demand(
        capsys, "--pattern", "random", "--spread", "-1", "--seed", "3", "--weeks", "10"
    )
    assert code == 1
    assert lines == [
        "seed 3",
        "error out_of_range demand.spread: demand.spread must be from 0 to 20, not -1"
        " [allowed 0..20 (placeholder)]",
    ]
    code, lines = demand(capsys, "--pattern", "fixed", "--values", "4,4", "--weeks", "3")
    assert code == 1 and lines[1].startswith("error fixed_series_length demand.values")


@pytest.mark.parametrize(
    ("argv", "message"),
    [
        (["--pattern", "fixed"], "--values is required"),
        (["--pattern", "fixed", "--values", "4,x"], "comma-separated"),
        (["--start", "-1"], "invalid Demand pattern: start:"),
        (["--pattern", "poisson"], "invalid choice"),
    ],
)
def test_demand_bad_input_exits_2(capsys, argv, message):
    with pytest.raises(SystemExit) as exc:
        main(["demand", *argv])
    assert exc.value.code == 2
    assert message in capsys.readouterr().err


def test_settings_check_reports_demand_type_errors_with_their_range(capsys, tmp_path):
    content = '{"demand": {"kind": "random", "mean": -1, "spread": 2}, "demand_seed": "x"}'
    code, lines = check(capsys, tmp_path, content)
    assert code == 1
    by_field = {line.split()[2].rstrip(":"): line for line in lines}
    assert by_field["demand.mean"].endswith("[allowed 0..100 (placeholder)]")
    assert by_field["demand_seed"].endswith("[allowed 0..999999999]")


def test_settings_check_reports_a_missing_seed(capsys, tmp_path):
    code, lines = check(capsys, tmp_path, '{"demand": {"kind": "random", "mean": 4, "spread": 2}}')
    assert code == 1
    assert lines[0].startswith("error demand_seed_required demand_seed: ")


@pytest.mark.parametrize("weeks", ["0", "-1", "101"])
def test_demand_weeks_outside_the_game_range_exit_2(capsys, weeks):
    with pytest.raises(SystemExit) as exc:
        main(["demand", "--pattern", "random", "--seed", "1", "--weeks", weeks])
    assert exc.value.code == 2
    assert "--weeks must be from 1 to 100" in capsys.readouterr().err


def test_settings_check_fixed_item_errors_carry_the_values_range(capsys, tmp_path):
    content = '{"demand": {"kind": "fixed", "values": [4, -1]}, "start": 3}'
    code, lines = check(capsys, tmp_path, content)
    assert code == 1
    by_field = {line.split()[2].rstrip(":"): line for line in lines}
    assert by_field["demand.values"].endswith("[allowed 0..100 (placeholder)]")
    assert "allowed" not in by_field["start"]


def test_trace_rule_based_prints_the_table_and_the_placeholder_warning(capsys):
    golden = json.loads((GOLDEN / "rule-based-classic-step.json").read_text(encoding="utf-8"))
    code, lines = run(capsys, "--settings", "classic", "--orders", "rule_based")
    assert code == 0
    assert len(lines) == 1 + 36 * 4 + 1
    rows = [line.split() for line in lines[1:-1]]
    roles = ("retailer", "wholesaler", "distributor", "factory")
    assert [row[7] for row in rows] == [
        str(orders[role]) for orders in golden["orders"] for role in roles
    ]
    assert lines[-1].startswith(
        "warning: Rule-based parameter set placeholder-unverified v1 is a placeholder (unverified)"
    )


@pytest.mark.parametrize("spec", ["constant:4", "pass-through"])
def test_other_traces_print_no_warning(capsys, spec):
    code, lines = run(capsys, "--orders", spec)
    assert code == 0
    assert not any(line.startswith("warning") for line in lines)


def test_trace_rule_based_with_another_set_needs_no_code_change(capsys, tmp_path, monkeypatch):
    import app.platform.parameter_sets as parameter_sets

    (tmp_path / "rule_based").mkdir()
    data = {
        "id": "verified-test",
        "version": 2,
        "verified": True,
        "source": "test set",
        "theta": "1",
        "alpha_s": "1",
        "beta": "1",
        "desired_inventory": 12,
    }
    (tmp_path / "rule_based" / "verified-test.json").write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(
        "app.sim.read_parameter_set",
        lambda kind, set_id: parameter_sets.read_parameter_set(kind, set_id, root=tmp_path),
    )
    code, lines = run(capsys, "--orders", "rule_based", "--rule-based-params", "verified-test")
    assert code == 0
    assert len(lines) == 1 + 36 * 4  # verified set: no warning line
    # theta 1 and alpha_s 1: the Retailer's Week 5 Order is 8 + (12 - 8) + (24 - 12) = 24
    assert lines[1 + 4 * 4].split()[:2] == ["5", "retailer"]
    assert lines[1 + 4 * 4].split()[7] == "24"


@pytest.mark.parametrize(
    ("set_id", "content"),
    [
        ("nope", None),
        ("../escape", None),
        ("broken", "{not json"),
        ("mismatch", '{"id": "other"}'),
    ],
)
def test_trace_rule_based_bad_parameter_set_exits_2(capsys, tmp_path, monkeypatch, set_id, content):
    import app.platform.parameter_sets as parameter_sets

    (tmp_path / "rule_based").mkdir()
    if content is not None:
        (tmp_path / "rule_based" / f"{set_id}.json").write_text(content, encoding="utf-8")
    monkeypatch.setattr(
        "app.sim.read_parameter_set",
        lambda kind, name: parameter_sets.read_parameter_set(kind, name, root=tmp_path),
    )
    with pytest.raises(SystemExit) as info:
        main(["trace", "--orders", "rule_based", "--rule-based-params", set_id])
    assert info.value.code == 2
    assert "--rule-based-params" in capsys.readouterr().err


def write_set(tmp_path, set_id, **values):
    (tmp_path / "rule_based").mkdir(exist_ok=True)
    data = {
        "id": set_id,
        "version": 1,
        "verified": True,
        "source": "test set",
        "theta": "0.5",
        "alpha_s": "0.5",
        "beta": "0.5",
        "desired_inventory": 12,
    } | values
    (tmp_path / "rule_based" / f"{set_id}.json").write_text(json.dumps(data), encoding="utf-8")


def test_trace_rule_based_guided_weeks_order_the_starting_demand(capsys, tmp_path, monkeypatch):
    import app.platform.parameter_sets as parameter_sets

    write_set(tmp_path, "stock-30", desired_inventory=30)
    monkeypatch.setattr(
        "app.sim.read_parameter_set",
        lambda kind, set_id: parameter_sets.read_parameter_set(kind, set_id, root=tmp_path),
    )
    code, lines = run(capsys, "--orders", "rule_based", "--rule-based-params", "stock-30")
    assert code == 0
    rows = [line.split() for line in lines[1:]]
    assert all(row[7] == "4" for row in rows if int(row[0]) <= 4)
    # Week 5, Wholesaler: E 4, S 12, SL 12, SL* 12 -> 4 + 0.5 * (30 - 12) = 13
    week5 = {row[1]: row[7] for row in rows if row[0] == "5"}
    assert week5["wholesaler"] == "13"
    assert all(value != "4" for value in week5.values())


@pytest.mark.parametrize("guided_weeks", [0, 3])
def test_rule_based_policy_skips_the_rule_only_in_guided_weeks(guided_weeks):
    from app.engine import GameSettings, advance, initial_state
    from app.sim import load_rule_based_params, rule_based_policy

    settings = GameSettings(guided_weeks=guided_weeks)
    policy = rule_based_policy(load_rule_based_params("placeholder-unverified"))
    states, placed = [initial_state(settings)], []
    called_in = []
    with mock.patch("app.sim.rule_based.order", return_value=7) as rule:
        for _ in range(guided_weeks + 1):
            calls = rule.call_count
            orders = policy(settings, states, placed)
            called_in.append(rule.call_count > calls)
            placed.append(orders)
            states.append(advance(settings, states[-1], orders))
    assert called_in == [False] * guided_weeks + [True]
    assert all(set(orders.values()) == {4} for orders in placed[:guided_weeks])
    assert set(placed[guided_weeks].values()) == {7}


# Story 1.7: `create` stores a simulation Game through games.commands.


def create(capsys, *argv):
    code = main(["create", *argv])
    captured = capsys.readouterr()
    lines = [line for line in captured.out.splitlines() if line.split(" ")[0] in REPORT]
    return code, lines, captured.err


REPORT = {"game", "seed", "lifecycle", "seat"}


def test_create_prints_the_game_its_seed_and_seats_from_the_database(capsys, games_db):
    from tests.games.helpers import query

    code, lines, _ = create(capsys, "--settings", "classic", "--seats", "rule_based")
    assert code == 0
    game_id = lines[0].removeprefix("game ")
    ((seed,),) = query(games_db, "SELECT demand_seed FROM games WHERE id = %s", (game_id,))
    assert lines == [
        f"game {game_id}",
        f"seed {seed}",
        "lifecycle not_started",
        "seat retailer rule_based",
        "seat wholesaler rule_based",
        "seat distributor rule_based",
        "seat factory rule_based",
    ]


def test_create_takes_one_occupant_per_role_and_a_seed(capsys, games_db):
    spec = "rule_based,scripted:constant-4,rule_based,scripted:constant-4"
    code, lines, _ = create(capsys, "--seats", spec, "--seed", "42")
    assert code == 0
    assert lines[1:] == [
        "seed 42",
        "lifecycle not_started",
        "seat retailer rule_based",
        "seat wholesaler scripted constant-4",
        "seat distributor rule_based",
        "seat factory scripted constant-4",
    ]


@pytest.mark.parametrize(
    ("argv", "message"),
    [
        (["--seats", "robot"], "unknown Seat spec 'robot'"),
        (["--seats", "scripted:nope"], "unknown Seat spec 'scripted:nope'"),
        (["--seats", "scripted:"], "unknown Seat spec"),
        (["--seats", "rule_based,rule_based"], "--seats needs one occupant or 4, not 2"),
    ],
)
def test_create_bad_seat_spec_exits_2_and_stores_nothing(capsys, games_db, argv, message):
    from tests.games.helpers import counts

    with pytest.raises(SystemExit) as info:
        main(["create", *argv])
    assert info.value.code == 2
    assert message in capsys.readouterr().err
    assert counts(games_db) == (0, 0, 0)


def test_create_reports_the_engine_codes_and_exits_1(capsys, games_db):
    from tests.games.helpers import counts

    code, lines, err = create(capsys, "--seed", "-1")
    assert (code, lines) == (1, [])
    assert err.splitlines() == [
        "error invalid_settings: the Game settings break the engine's rules",
        "error out_of_range demand_seed",
    ]
    assert counts(games_db) == (0, 0, 0)


def test_create_with_an_unknown_parameter_set_exits_1(capsys, games_db):
    code, _, err = create(capsys, "--rule-based-params", "nope")
    assert code == 1
    assert err.startswith("error unknown_parameter_set: ")


def test_create_without_a_database_exits_1(capsys, monkeypatch, unreachable_database):
    monkeypatch.setenv("DATABASE_URL", unreachable_database)
    code, lines, err = create(capsys)
    assert (code, lines) == (1, [])
    assert err.strip() == "error db_unavailable: cannot reach the database"


def test_create_reports_a_game_left_with_free_seats(capsys, games_db, monkeypatch):
    from app.modules.games import commands as game_commands

    async def refuse(*args):
        raise game_commands.CommandError("seat_occupied", "taken", 409)

    monkeypatch.setattr(game_commands, "assign_seat", refuse)
    code, lines, err = create(capsys)
    assert (code, lines) == (1, [])
    first, note = err.splitlines()
    assert first == "error seat_occupied: taken"
    assert note.startswith("note: game ") and note.endswith(" was stored with Seats still free")


def test_create_reports_other_database_errors_and_exits_1(capsys, monkeypatch):
    from sqlalchemy.exc import ProgrammingError

    from app.modules.games import commands as game_commands

    async def broken(*args, **kwargs):
        raise ProgrammingError("SELECT", {}, Exception("relation games does not exist"))

    monkeypatch.setattr(game_commands, "create", broken)
    code, lines, err = create(capsys)
    assert (code, lines) == (1, [])
    assert err.strip() == "error db_error: Exception"


def test_create_seat_spec_allows_spaces(capsys, games_db):
    code, lines, _ = create(
        capsys, "--seats", "rule_based, scripted:constant-4, rule_based, rule_based"
    )
    assert code == 0
    assert lines[4] == "seat wholesaler scripted constant-4"


def test_create_as_a_program_prints_only_the_report_on_stdout(games_db):
    import os
    import subprocess
    import sys

    env = {**os.environ, "DATABASE_URL": os.environ["DATABASE_URL"]}
    result = subprocess.run(
        [sys.executable, "-m", "app.sim", "create", "--seed", "1"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert [line.split(" ")[0] for line in lines] == ["game", "seed", "lifecycle"] + ["seat"] * 4
    assert '"event": "game_created"' in result.stderr


# Story 1.8: `start` opens Week 1; `show` prints what one Seat sees.


def created_game(capsys) -> str:
    code, lines, _ = create(capsys, "--seats", "rule_based", "--seed", "7")
    assert code == 0
    return lines[0].removeprefix("game ")


def test_start_prints_the_game_and_its_seats(capsys, games_db):
    """Four Rule-based players: the order source plays the Game to its end inside `start`."""
    game_id = created_game(capsys)
    code = main(["start", game_id])
    out = [
        line
        for line in capsys.readouterr().out.splitlines()
        if line.split(" ")[0] in REPORT | {"week"}
    ]
    assert code == 0
    assert out == [
        f"game {game_id}",
        "lifecycle finished",
        "week 1",
        "seat retailer rule_based",
        "seat wholesaler rule_based",
        "seat distributor rule_based",
        "seat factory rule_based",
    ]


def test_start_twice_reports_the_conflict(capsys, games_db):
    game_id = created_game(capsys)
    assert main(["start", game_id]) == 0
    capsys.readouterr()
    assert main(["start", game_id]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("error game_already_started: ")


def test_show_prints_the_seat_state_and_the_open_turn(capsys, games_db):
    from app.modules.games.schemas import SeatState
    from tests.games.helpers import query, seat_student

    game_id = created_game(capsys)
    seat_student(games_db, game_id, "retailer")  # the Game waits in Week 1 for the Student
    main(["start", game_id])
    capsys.readouterr()
    code = main(["show", game_id, "--seat", "retailer"])
    out = capsys.readouterr().out
    assert code == 0
    out = out[out.index("{") :]  # structlog lines precede the report under pytest
    body, opened, reference, near = out.rstrip("\n").rsplit("\n", 3)
    state = SeatState.model_validate_json(body)
    assert (state.role, state.week, state.inventory, state.incoming_order) == (
        "retailer",
        1,
        12,
        4,
    )
    ((opened_at, order, near_order),) = query(
        games_db,
        "SELECT t.opened_at, t.rule_based_reference_order, t.near_optimal_reference_order "
        "FROM seat_turns t "
        "JOIN seats s ON s.id = t.seat_id WHERE t.game_id = %s AND s.role = 'retailer'",
        (game_id,),
    )
    assert opened == f"opened_at {opened_at.isoformat()}"
    assert reference == f"reference_order {order}"
    assert near == f"near_optimal_reference_order {near_order} placeholder-0"
    assert near_order == 8  # Classic step: 12 + (4 + 4 + 4 + 8) - 24 (Story 2.9)


@pytest.mark.parametrize(
    ("argv", "error"),
    [
        (["show", "nope", "--seat", "retailer"], "error game_not_found: "),
        (["start", "nope"], "error game_not_found: "),
    ],
)
def test_start_and_show_report_refusals(capsys, games_db, argv, error):
    assert main(argv) == 1
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err.startswith(error)


def test_show_of_a_game_not_started_exits_1(capsys, games_db):
    game_id = created_game(capsys)
    assert main(["show", game_id, "--seat", "factory"]) == 1
    assert capsys.readouterr().err.startswith("error game_not_started: ")


def test_show_needs_a_seat(capsys):
    with pytest.raises(SystemExit) as info:
        main(["show", "x"])
    assert info.value.code == 2


def test_show_without_a_database_exits_1(capsys, monkeypatch, unreachable_database):
    monkeypatch.setenv("DATABASE_URL", unreachable_database)
    game_id = "01a1eb10-f299-75a6-8ec2-a251c50791e1"
    assert main(["show", game_id, "--seat", "retailer"]) == 1
    assert capsys.readouterr().err.strip() == "error db_unavailable: cannot reach the database"


# Story 1.9: `play` places every Order through `place_order`; `log` prints the Decision log.


def report(capsys, prefixes: set[str]) -> list[str]:
    """The report lines (structlog lines precede them under pytest)."""
    return [line for line in capsys.readouterr().out.splitlines() if line.split(" ")[0] in prefixes]


def played_game(capsys, seats: str = "rule_based") -> str:
    """A Game created, started and played to its end with `create`, `start` and `play`. The
    first call per `seats` runs the commands; later ones store a copy of that Game's rows."""
    from tests.conftest import TEST_DATABASE_URL
    from tests.games.helpers import remember, stored_copy

    copy = stored_copy(TEST_DATABASE_URL, ("sim play", seats))
    if copy is not None:
        return copy
    code, lines, _ = create(capsys, "--seats", seats, "--seed", "7")
    assert code == 0
    game_id = lines[0].removeprefix("game ")
    assert main(["start", game_id]) == 0
    capsys.readouterr()
    assert main(["play", game_id]) == 0
    assert report(capsys, {"game", "lifecycle", "weeks"}) == [
        f"game {game_id}",
        "lifecycle finished",
        "weeks 36",
    ]
    remember(TEST_DATABASE_URL, ("sim play", seats), game_id)
    return game_id


def log_lines(capsys, game_id: str) -> list[str]:
    assert main(["log", game_id]) == 0
    out = capsys.readouterr().out.splitlines()
    start = next(i for i, line in enumerate(out) if line.lstrip().startswith("week"))
    return out[start:]


def test_log_of_a_rule_based_game_matches_the_engine_only_trace(capsys, games_db):
    game_id = played_game(capsys)
    lines = log_lines(capsys, game_id)
    assert lines[0].split() == [
        "week",
        "role",
        "incoming_order",
        "incoming_delivery",
        "shipped",
        "inventory",
        "backlog",
        "order",
        "cost",
        "decided_by",
        "reference",
    ]
    rows = [line.split() for line in lines[1:]]
    assert len(rows) == 36 * 4
    code, trace = run(capsys, "--orders", "rule_based")
    assert code == 0
    traced = [line.split() for line in trace[1:] if not line.startswith("warning")]
    # Week, Role, the Week's numbers, the Order and the cost equal the engine-only game.
    assert [row[:9] for row in rows] == traced
    assert {row[9] for row in rows if int(row[0]) <= 4} == {"guided"}
    assert {row[9] for row in rows if int(row[0]) > 4} == {"rule_based"}
    assert all(row[7] == row[10] for row in rows if int(row[0]) > 4)


def test_play_with_scripted_occupants_logs_scripted_orders(capsys, games_db):
    game_id = played_game(capsys, "scripted:constant-4")
    rows = [line.split() for line in log_lines(capsys, game_id)[1:]]
    assert {(row[7], row[9]) for row in rows if int(row[0]) > 4} == {("4", "scripted")}


@pytest.mark.parametrize(
    ("argv", "error"),
    [
        (["play", "nope"], "error game_not_found: "),
        (["log", "nope"], "error game_not_found: "),
    ],
)
def test_play_and_log_report_refusals(capsys, games_db, argv, error):
    assert main(argv) == 1
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err.startswith(error)


def test_play_of_a_game_not_started_exits_1(capsys, games_db):
    game_id = created_game(capsys)
    assert main(["play", game_id]) == 1
    assert capsys.readouterr().err.startswith("error game_not_started: ")


def test_play_of_a_finished_game_reports_it_again(capsys, games_db):
    game_id = played_game(capsys)
    assert main(["play", game_id]) == 0
    assert report(capsys, {"lifecycle", "weeks", "check"}) == [
        "lifecycle finished",
        "weeks 36",
        "check ok",
    ]


def test_play_of_a_game_waiting_for_a_student_exits_1(capsys, games_db):
    from tests.games.helpers import seat_student

    game_id = created_game(capsys)
    seat_student(games_db, game_id, "factory")
    assert main(["start", game_id]) == 0
    capsys.readouterr()
    assert main(["play", game_id]) == 1
    assert capsys.readouterr().err.startswith("error game_not_finished: ")


def test_log_of_a_game_without_orders_prints_the_header_only(capsys, games_db):
    game_id = created_game(capsys)
    assert len(log_lines(capsys, game_id)) == 1


def test_play_moves_on_a_game_stopped_between_two_advances(capsys, games_db, monkeypatch):
    """Story 2.1: the runner chooses no Order; it moves a complete open Week on with
    `advance`, which plays the rest of the Game."""
    from app.modules.games import commands

    async def no_settle(game_id: str) -> None:
        return None

    game_id = created_game(capsys)
    monkeypatch.setattr(commands, "_settle", no_settle)
    assert main(["start", game_id]) == 0
    assert "lifecycle running" in report(capsys, {"lifecycle"})
    monkeypatch.undo()
    assert main(["play", game_id]) == 0
    assert report(capsys, {"lifecycle", "weeks"}) == ["lifecycle finished", "weeks 36"]
    assert len(log_lines(capsys, game_id)) == 1 + 36 * 4


# Story 1.10: `play` ends with the finished-game check; `check` runs or reads it back.


def test_play_and_check_report_the_finished_game_check(capsys, games_db):
    from tests.games.helpers import query

    code, lines, _ = create(capsys, "--seats", "rule_based", "--seed", "7")
    game_id = lines[0].removeprefix("game ")
    assert main(["start", game_id]) == 0
    capsys.readouterr()
    assert main(["play", game_id]) == 0
    assert report(capsys, {"weeks", "check"}) == ["weeks 36", "check ok"]
    for _ in range(2):
        assert main(["check", game_id]) == 0
        assert report(capsys, {"check", "violation"}) == ["check ok"]
    assert query(
        games_db, "SELECT ok, rules_version FROM game_checks WHERE game_id = %s", (game_id,)
    ) == [(True, 1)]


def test_check_prints_each_violation_and_exits_1(capsys, games_db):
    from tests.games.helpers import tamper

    game_id = played_game(capsys)
    # `play` stored a passing check; drop it so the tampered Game is checked afresh.
    tamper(games_db, "DELETE FROM game_checks WHERE game_id = %s", (game_id,))
    tamper(
        games_db,
        "UPDATE game_weeks SET state = jsonb_set(state, '{seats,1,backlog}', '5') "
        "WHERE game_id = %s AND week = 15 AND NOT finished",
        (game_id,),
    )
    for _ in range(2):  # the second call prints the stored result
        assert main(["check", game_id]) == 1
        lines = report(capsys, {"check", "violation"})
        count = int(lines[0].removeprefix("check failed "))
        assert len(lines) == 1 + count
        assert "violation replay week 15 role wholesaler" in lines
        assert "violation backlog_balance week 15 role wholesaler" in lines


@pytest.mark.parametrize(
    ("argv", "error"),
    [
        (["check", "nope"], "error game_not_found: "),
    ],
)
def test_check_reports_refusals(capsys, games_db, argv, error):
    assert main(argv) == 1
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err.startswith(error)


def test_check_of_a_running_game_exits_1(capsys, games_db):
    from tests.games.helpers import seat_student

    game_id = created_game(capsys)
    seat_student(games_db, game_id, "retailer")
    assert main(["start", game_id]) == 0
    capsys.readouterr()
    assert main(["check", game_id]) == 1
    assert capsys.readouterr().err.startswith("error game_not_finished: ")


def test_play_exits_1_when_the_finished_game_check_fails(capsys, games_db, monkeypatch):
    from app import sim
    from app.engine import Violation

    async def failed(game_id):
        return sim.game_service.GameCheck(
            id="c",
            game_id=game_id,
            rules_version=1,
            ok=False,
            checked_at="2026-11-17T00:00:00Z",
            violations=(Violation(rule="replay", week=None, role=None, message="x"),),
        )

    monkeypatch.setattr(sim.game_service, "verify_finished", failed)
    code, lines, _ = create(capsys, "--seats", "rule_based", "--seed", "7")
    game_id = lines[0].removeprefix("game ")
    assert main(["start", game_id]) == 0
    capsys.readouterr()
    assert main(["play", game_id]) == 1
    assert report(capsys, {"check", "violation"}) == [
        "check failed 1",
        "violation replay week - role -",
    ]


CHECK_ALL = {"game", "violation", "checked"}


def test_check_all_of_an_empty_database_checks_nothing_and_exits_0(capsys, games_db):
    assert main(["check", "--all"]) == 0
    assert report(capsys, CHECK_ALL) == ["checked 0 ok=0 failed=0"]


def test_check_all_counts_the_finished_games_and_lists_only_failures(capsys, games_db):
    from tests.games.helpers import query, seat_student, tamper

    good, bad, refused = (played_game(capsys) for _ in range(3))
    running = created_game(capsys)
    seat_student(games_db, running, "retailer")
    assert main(["start", running]) == 0
    tamper(games_db, "DELETE FROM game_checks WHERE game_id IN (%s, %s)", (bad, refused))
    tamper(
        games_db,
        "UPDATE game_weeks SET state = jsonb_set(state, '{seats,1,backlog}', '5') "
        "WHERE game_id = %s AND week = 15 AND NOT finished",
        (bad,),
    )
    tamper(games_db, "UPDATE games SET rules_version = 99 WHERE id = %s", (refused,))
    capsys.readouterr()
    for _ in range(2):  # the second run reads the stored checks back
        assert main(["check", "--all"]) == 1
        lines = report(capsys, CHECK_ALL)
        assert lines[-1] == "checked 3 ok=1 failed=2"
        assert not any(good in line for line in lines)
        assert not any(running in line for line in lines)
        failed = lines.index(next(line for line in lines if line.startswith(f"game {bad} ")))
        count = int(lines[failed].removeprefix(f"game {bad} check failed "))
        assert all(line.startswith("violation ") for line in lines[failed + 1 : failed + 1 + count])
        assert "violation replay week 15 role wholesaler" in lines
        assert (
            f"game {refused} check refused rules_version_unsupported: "
            "no rules package for rules version 99" in lines
        )
    # A refused check stores nothing; the tampered Game's failed check is stored once.
    assert query(games_db, "SELECT game_id::text, ok FROM game_checks ORDER BY ok") == [
        (bad, False),
        (good, True),
    ]


def test_check_all_checks_a_finished_game_without_a_stored_check(capsys, games_db):
    from tests.games.helpers import query, tamper

    game_id = played_game(capsys)
    tamper(games_db, "DELETE FROM game_checks WHERE game_id = %s", (game_id,))
    capsys.readouterr()
    assert main(["check", "--all"]) == 0
    assert report(capsys, CHECK_ALL) == ["checked 1 ok=1 failed=0"]
    assert query(games_db, "SELECT ok FROM game_checks WHERE game_id = %s", (game_id,)) == [(True,)]


@pytest.mark.parametrize("argv", [["check"], ["check", "x", "--all"]])
def test_check_needs_a_game_id_or_all(capsys, argv):
    with pytest.raises(SystemExit) as info:
        main(argv)
    assert info.value.code == 2
    assert "give a Game id or --all" in capsys.readouterr().err


def test_check_all_without_a_database_exits_1(capsys, monkeypatch, unreachable_database):
    monkeypatch.setenv("DATABASE_URL", unreachable_database)
    assert main(["check", "--all"]) == 1
    assert capsys.readouterr().err.strip() == "error db_unavailable: cannot reach the database"


# Story 1.11: `run` plays a batch of Games through `games.commands` and summarises them.

SMOKE = Path(__file__).parents[1] / "batches" / "classic-smoke.json"
SHORT = {"weeks": 8}
"""Settings of a short Game, for batch tests that do not need the Classic 36 Weeks."""
SUMMARY = {"game", "cost", "orders", "batch"}


def run_batch(capsys, *argv) -> tuple[int, list[str], str]:
    code = main(["run", *argv])
    captured = capsys.readouterr()
    lines = [line for line in captured.out.splitlines() if line.split(" ")[0] in SUMMARY]
    return code, lines, captured.err


def batch_ids(lines: list[str]) -> list[str]:
    return [line.split(" ")[1] for line in lines if line.startswith("game ")]


def batch_file(tmp_path, data, name: str = "batch.json") -> str:
    path = tmp_path / name
    path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
    return str(path)


def test_run_plays_the_smoke_batch_and_summarises_it_from_the_tables(capsys, games_db):
    from tests.games.helpers import query

    code, lines, _ = run_batch(capsys, str(SMOKE))
    assert code == 0
    assert len(lines) == 3 * 3 + 3
    ids = batch_ids(lines)
    assert len(ids) == 3
    for index, game_id in enumerate(ids):
        head, cost, orders = lines[3 * index : 3 * index + 3]
        assert head == f"game {game_id} seed {7 + index} weeks 36 check ok"
        stored = query(
            games_db,
            "SELECT seat->>'role', seat->>'total_cost' FROM game_weeks, "
            "jsonb_array_elements(state->'seats') WITH ORDINALITY AS t(seat, n) "
            "WHERE game_id = %s AND finished ORDER BY n",
            (game_id,),
        )
        ((chain,),) = query(
            games_db,
            "SELECT sum((state_seen->>'week_cost')::numeric) FROM seat_weeks WHERE game_id = %s",
            (game_id,),
        )
        assert cost == "cost " + " ".join(f"{r}={c}" for r, c in stored) + f" chain={chain}"
        assert orders == "orders rule_based=64 scripted=64 guided=16"
    batch, cost, orders = lines[-3:]
    assert batch == "batch games 3 weeks 108 checks ok=3 failed=0"
    assert orders == "orders rule_based=192 scripted=192 guided=48"
    ((total,),) = query(games_db, "SELECT sum((state_seen->>'week_cost')::numeric) FROM seat_weeks")
    assert cost.endswith(f" chain={total}")
    assert query(
        games_db, "SELECT purpose, lifecycle, count(*) FROM games GROUP BY purpose, lifecycle"
    ) == [("simulation", "finished", 3)]
    assert query(games_db, "SELECT ok, count(*) FROM game_checks GROUP BY ok") == [(True, 3)]


def smoke(tmp_path, games: int) -> str:
    """The smoke batch with fewer Games, for tests where the batch size is not the point."""
    return batch_file(tmp_path, {**json.loads(SMOKE.read_text(encoding="utf-8")), "games": games})


def test_run_places_the_order_of_each_scripted_policy(capsys, games_db, tmp_path):
    from tests.games.helpers import query

    code, _, _ = run_batch(capsys, smoke(tmp_path, 1))
    assert code == 0
    rows = query(
        games_db,
        "SELECT s.role, w.decided_by, w.order, (w.state_seen->>'incoming_order')::int, "
        "o.policy_id FROM seat_weeks w JOIN seats s ON s.id = w.seat_id "
        "JOIN seat_occupancy o ON o.seat_id = s.id WHERE w.week > 4",
    )
    by_role: dict[str, set] = {}
    for role, decided_by, order, incoming, policy_id in rows:
        if role == "wholesaler":
            assert (decided_by, policy_id, order) == ("scripted", "order-incoming", incoming)
        elif role == "distributor":
            assert (decided_by, policy_id, order) == ("scripted", "constant-4", 4)
        else:
            assert (decided_by, policy_id) == ("rule_based", None)
        by_role.setdefault(role, set()).add(order)
    assert len(by_role["wholesaler"]) > 1  # it follows its incoming order, not a constant


def test_run_twice_gives_identical_orders_and_costs(capsys, games_db, tmp_path):
    from tests.games.helpers import query

    def weeks(game_id: str) -> list[tuple]:
        return query(
            games_db,
            "SELECT w.week, s.role, w.order, w.state_seen->>'week_cost', "
            "w.state_seen->>'total_cost' FROM seat_weeks w JOIN seats s ON s.id = w.seat_id "
            "WHERE w.game_id = %s ORDER BY w.week, s.position",
            (game_id,),
        )

    path = smoke(tmp_path, 1)
    first = run_batch(capsys, path)
    second = run_batch(capsys, path)
    assert first[0] == second[0] == 0
    pairs = list(zip(batch_ids(first[1]), batch_ids(second[1]), strict=True))
    assert len(pairs) == 1
    for one, other in pairs:
        assert one != other
        assert len(weeks(one)) == 36 * 4
        assert weeks(one) == weeks(other)
    # The summaries differ only in the Game ids.
    strip = [line for line in first[1] if not line.startswith("game ")]
    assert strip == [line for line in second[1] if not line.startswith("game ")]


def test_run_exports_the_decision_log_as_csv(capsys, games_db, tmp_path):
    import csv

    out = tmp_path / "new" / "dir"
    code, lines, _ = run_batch(capsys, smoke(tmp_path, 2), "--export", str(out))
    assert code == 0
    with (out / "decision-log.csv").open(encoding="utf-8", newline="") as file:
        rows = list(csv.reader(file))
    assert rows[0] == [
        "game_id",
        "week",
        "seat_id",
        "role",
        "occupant_kind",
        "decided_by",
        "fallback",
        "order",
        "rule_based_reference_order",
        "incoming_order",
        "incoming_delivery",
        "shipped",
        "inventory",
        "backlog",
        "supply_line",
        "position",
        "week_cost",
        "total_cost",
    ]
    body = rows[1:]
    assert len(body) == 2 * 36 * 4
    assert [row[0] for row in body[:: 36 * 4]] == batch_ids(lines)
    assert [(row[1], row[3]) for row in body[:4]] == [
        ("1", "retailer"),
        ("1", "wholesaler"),
        ("1", "distributor"),
        ("1", "factory"),
    ]
    assert {row[5] for row in body} == {"guided", "rule_based", "scripted"}
    from tests.games.helpers import query

    stored = query(
        games_db,
        "SELECT w.game_id::text, w.week::text, w.seat_id::text, s.role, w.occupant_kind, "
        "w.decided_by, w.fallback, w.order::text, w.rule_based_reference_order::text, "
        "w.state_seen->>'incoming_order', w.state_seen->>'incoming_delivery', "
        "w.state_seen->>'shipped', w.state_seen->>'inventory', w.state_seen->>'backlog', "
        "w.state_seen->>'supply_line', w.state_seen->>'position', "
        "w.state_seen->>'week_cost', w.state_seen->>'total_cost' "
        "FROM seat_weeks w JOIN seats s ON s.id = w.seat_id",
    )
    assert sorted(body) == sorted(list(row) for row in stored)
    for row in body:  # ids, Roles, fixed codes and numbers only
        assert all(
            cell.replace(".", "").replace("-", "").replace("_", "").isalnum() for cell in row
        )
        assert all(int(row[i]) >= 0 for i in (1, 7, 8, 9, 10, 11, 12, 13, 14))
        int(row[15]), float(row[16]), float(row[17])


def test_run_with_a_seeded_demand_pattern_gives_each_game_its_own_seed(capsys, games_db, tmp_path):
    from app.engine.demand import series
    from app.sim import DEMAND_PATTERN
    from tests.games.helpers import query

    pattern = {"kind": "random", "mean": 4, "spread": 2}
    path = batch_file(
        tmp_path,
        {
            "seed": 41,
            "games": 2,
            "seats": "scripted:order-incoming",
            "settings": {"weeks": 12, "holding_cost": 0.5},
            "demand": pattern,
        },
    )
    code, lines, _ = run_batch(capsys, path)
    assert code == 0
    assert [line.split(" ")[3] for line in lines if line.startswith("game ")] == ["41", "42"]
    assert lines[-3] == "batch games 2 weeks 24 checks ok=2 failed=0"
    assert lines[-1] == "orders scripted=64 guided=32"
    for game_id, seed in zip(batch_ids(lines), (41, 42), strict=True):
        ((stored,),) = query(games_db, "SELECT demand_series FROM games WHERE id = %s", (game_id,))
        assert stored == list(series(DEMAND_PATTERN.validate_python(pattern), 12, seed))


@pytest.mark.parametrize(
    ("data", "detail"),
    [
        (None, "cannot read"),
        ("{not json", "is not JSON"),
        ("[]", "file: "),
        ({"seed": 1, "games": 1, "seats": "rule_based", "colour": "red"}, "colour"),
        ({"seed": 1, "games": 0, "seats": "rule_based"}, "games"),
        ({"seed": 1, "games": 101, "seats": "rule_based"}, "games"),
        ({"seed": "1", "games": 1, "seats": "rule_based"}, "seed"),
        ({"games": 1, "seats": "rule_based"}, "seed"),
        ({"seed": 1, "games": 1, "seats": {"retailer": "rule_based"}}, "one spec for each Role"),
        ({"seed": 1, "games": 1, "seats": "scripted:constant-5"}, "seats: unknown Seat spec"),
        ({"seed": 1, "games": 1, "seats": "robot"}, "seats: unknown Seat spec"),
        ({"seed": 1, "games": 1, "seats": "llm"}, "model_config: llm Seats need a model config"),
        ({"seed": 1, "games": 1, "seats": "rule_based,rule_based"}, "seats: "),
        ({"seed": 999_999_999, "games": 2, "seats": "rule_based"}, "must not exceed"),
        ({"seed": 1, "games": 1, "seats": "rule_based", "settings": {"weeks": "x"}}, "weeks"),
        ({"seed": 1, "games": 1, "seats": "rule_based", "demand": {"kind": "x"}}, "demand"),
        (
            {"seed": 1, "games": 1, "seats": "rule_based", "settings": {"demand_seed": 5}},
            "settings.demand_seed: use seed",
        ),
        (
            {
                "seed": 1,
                "games": 1,
                "seats": {
                    "retailer": "rule_based",
                    "wholesaler": "rule_based",
                    "distributor": "rule_based",
                    "factory": "rule_based",
                    "brewery": "rule_based",
                },
            },
            "one spec for each Role",
        ),
    ],
)
def test_run_refuses_a_bad_batch_file_and_stores_nothing(capsys, games_db, tmp_path, data, detail):
    from tests.games.helpers import counts

    path = str(tmp_path / "missing.json") if data is None else batch_file(tmp_path, data)
    code, lines, err = run_batch(capsys, path)
    assert code == 2 and lines == []
    assert err.startswith("error invalid_batch: ")
    assert detail in err
    assert counts(games_db) == (0, 0, 0)


def test_run_refuses_a_non_utf8_batch_file(capsys, tmp_path):
    path = tmp_path / "batch.json"
    path.write_bytes(b"\xff\xfe\x00")
    assert main(["run", str(path)]) == 2
    assert "is not UTF-8 text" in capsys.readouterr().err


def test_run_takes_one_seat_spec_per_role(capsys, games_db, tmp_path):
    from tests.games.helpers import query

    seats = {
        "factory": "scripted:constant-4",
        "retailer": "scripted:order-incoming",
        "wholesaler": "rule_based",
        "distributor": "rule_based",
    }
    path = batch_file(tmp_path, {"seed": 3, "games": 1, "seats": seats, "settings": SHORT})
    code, _, _ = run_batch(capsys, path)
    assert code == 0
    stored = query(
        games_db,
        "SELECT s.role, o.occupant_kind, o.policy_id FROM seats s "
        "JOIN seat_occupancy o ON o.seat_id = s.id ORDER BY s.position",
    )
    assert stored == [
        ("retailer", "scripted", "order-incoming"),
        ("wholesaler", "rule_based", None),
        ("distributor", "rule_based", None),
        ("factory", "scripted", "constant-4"),
    ]


def test_run_reports_settings_that_break_the_engine_rules(capsys, games_db, tmp_path):
    path = batch_file(
        tmp_path, {"seed": 1, "games": 1, "seats": "rule_based", "settings": {"guided_weeks": 10}}
    )
    code, lines, err = run_batch(capsys, path)
    assert code == 1 and lines == []
    assert err.startswith("error invalid_settings: ")


def test_run_refuses_an_export_path_that_is_a_file(capsys, tmp_path):
    taken = tmp_path / "taken"
    taken.write_text("x", encoding="utf-8")
    assert main(["run", str(SMOKE), "--export", str(taken)]) == 2
    assert capsys.readouterr().err.startswith("error invalid_export: ")


def test_run_exits_1_and_counts_a_failed_check(capsys, games_db, tmp_path, monkeypatch):
    from app import sim
    from tests.games.helpers import tamper

    verify = sim.game_service.verify_finished

    async def tampered_then_verified(game_id):
        tamper(
            games_db,
            "UPDATE game_weeks SET state = jsonb_set(state, '{seats,0,inventory}', '99') "
            "WHERE game_id = %s AND week = 10 AND NOT finished",
            (game_id,),
        )
        return await verify(game_id)

    monkeypatch.setattr(sim.game_service, "verify_finished", tampered_then_verified)
    path = batch_file(
        tmp_path, {"seed": 7, "games": 1, "seats": "rule_based", "settings": {"weeks": 12}}
    )
    code, lines, _ = run_batch(capsys, path)
    assert code == 1
    assert lines[0].split(" ")[6:8] == ["check", "failed"]
    assert int(lines[0].split(" ")[8]) > 0
    assert lines[-3] == "batch games 1 weeks 12 checks ok=0 failed=1"


def test_run_reports_a_failing_export_write(capsys, games_db, tmp_path, monkeypatch):
    from app import sim

    monkeypatch.setattr(sim, "EXPORT_FILE", "missing-dir/decision-log.csv")
    path = batch_file(tmp_path, {"seed": 7, "games": 1, "seats": "rule_based", "settings": SHORT})
    assert main(["run", path, "--export", str(tmp_path / "out")]) == 1
    captured = capsys.readouterr()
    assert captured.err.startswith("error export_failed: ")
    # The Games were played and checked: their summary is still printed.
    assert "batch games 1 weeks 8 checks ok=1 failed=0" in captured.out.splitlines()


def test_run_uses_the_batch_rule_based_parameter_set(capsys, games_db, tmp_path, monkeypatch):
    import app.platform.parameter_sets as parameter_sets
    from app.modules.games import commands
    from tests.games.helpers import query

    write_set(tmp_path, "stock-30", desired_inventory=30)
    shipped = parameter_sets.read_parameter_set
    monkeypatch.setattr(
        commands,
        "read_parameter_set",
        lambda kind, set_id: (
            shipped(kind, set_id, root=tmp_path) if kind == "rule_based" else shipped(kind, set_id)
        ),
    )
    path = batch_file(
        tmp_path,
        {
            "seed": 7,
            "games": 1,
            "seats": "rule_based",
            "rule_based_params": "stock-30",
            "settings": SHORT,
        },
    )
    code, _, _ = run_batch(capsys, path)
    assert code == 0
    assert query(games_db, "SELECT session_runtime->>'rule_based_params' FROM games") == [
        ("stock-30",)
    ]
    # Week 5, Wholesaler: 4 + 0.5 * (30 - 12) = 13 under this set (4 under the default).
    assert query(
        games_db,
        "SELECT w.order FROM seat_weeks w JOIN seats s ON s.id = w.seat_id "
        "WHERE w.week = 5 AND s.role = 'wholesaler'",
    ) == [(13,)]


def test_run_refuses_an_unknown_rule_based_parameter_set(capsys, games_db, tmp_path):
    path = batch_file(
        tmp_path, {"seed": 7, "games": 1, "seats": "rule_based", "rule_based_params": "nope"}
    )
    code, lines, err = run_batch(capsys, path)
    assert code == 1 and lines == []
    assert err.startswith("error unknown_parameter_set: ")


def test_run_stopped_partway_names_the_games_already_stored(
    capsys, games_db, tmp_path, monkeypatch
):
    from app import sim

    verify = sim.game_service.verify_finished
    calls: list[str] = []

    async def refuse_the_second(game_id):
        calls.append(game_id)
        if len(calls) == 2:
            raise sim.game_service.ViewError("game_not_finished", "refused in a test", 409)
        return await verify(game_id)

    monkeypatch.setattr(sim.game_service, "verify_finished", refuse_the_second)
    path = batch_file(tmp_path, {"seed": 7, "games": 3, "seats": "rule_based", "settings": SHORT})
    code, lines, err = run_batch(capsys, path)
    assert code == 1 and lines == []
    first, note = err.strip().splitlines()[-2:]
    assert first.startswith("error game_not_finished: ")
    assert note == f"note: games stored before the stop: {' '.join(calls)}"


def test_summary_lines_count_a_missing_check_as_failed():
    from decimal import Decimal

    from app import sim

    summary = sim.game_service.GameSummary(
        game_id="g",
        demand_seed=3,
        weeks=2,
        total_cost=(("retailer", Decimal("1.50")),),
        chain_cost=Decimal("1.50"),
        orders=((sim.game_service.DecidedBy.GUIDED, 2),),
        check=None,
    )
    assert sim.summary_lines([summary, summary]) == [
        "game g seed 3 weeks 2 check missing",
        "cost retailer=1.50 chain=1.50",
        "orders guided=2",
        "game g seed 3 weeks 2 check missing",
        "cost retailer=1.50 chain=1.50",
        "orders guided=2",
        "batch games 2 weeks 4 checks ok=0 failed=2",
        "cost retailer=3.00 chain=3.00",
        "orders guided=4",
    ]
