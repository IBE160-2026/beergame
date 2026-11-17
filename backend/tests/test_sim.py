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
        (["--seats", "llm"], "unknown Seat spec 'llm'"),
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


def test_create_without_a_database_exits_1(capsys, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://nobody:secretpw@127.0.0.1:1/none")
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


def test_start_prints_the_running_game_and_its_seats(capsys, games_db):
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
        "lifecycle running",
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
    from tests.games.helpers import query

    game_id = created_game(capsys)
    main(["start", game_id])
    capsys.readouterr()
    code = main(["show", game_id, "--seat", "retailer"])
    out = capsys.readouterr().out
    assert code == 0
    out = out[out.index("{") :]  # structlog lines precede the report under pytest
    body, opened, reference = out.rstrip("\n").rsplit("\n", 2)
    state = SeatState.model_validate_json(body)
    assert (state.role, state.week, state.inventory, state.incoming_order) == (
        "retailer",
        1,
        12,
        4,
    )
    ((opened_at, order),) = query(
        games_db,
        "SELECT t.opened_at, t.rule_based_reference_order FROM seat_turns t "
        "JOIN seats s ON s.id = t.seat_id WHERE t.game_id = %s AND s.role = 'retailer'",
        (game_id,),
    )
    assert opened == f"opened_at {opened_at.isoformat()}"
    assert reference == f"reference_order {order}"


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


def test_show_without_a_database_exits_1(capsys, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://nobody:secretpw@127.0.0.1:1/none")
    game_id = "01a1eb10-f299-75a6-8ec2-a251c50791e1"
    assert main(["show", game_id, "--seat", "retailer"]) == 1
    assert capsys.readouterr().err.strip() == "error db_unavailable: cannot reach the database"
