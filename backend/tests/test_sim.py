import json
from pathlib import Path

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
