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
