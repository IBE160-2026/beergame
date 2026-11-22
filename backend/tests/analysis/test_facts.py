"""Story 9.1: the facts set of one Seat as a pure function of the Decision log (FR-44, AD-1, AD-7).

The logs here are built by hand, so each rule is tested on the numbers that decide it; the
golden Games in `tests/games/test_facts.py` check the same function on played Games."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.analysis import facts as analysis
from app.analysis.facts import DecisionLog, LoggedOrder, facts
from app.analysis.patterns import PatternSet
from app.engine import ROLES
from tests.analysis.test_patterns import V1

PATTERNS = PatternSet.model_validate(V1)


def row(week: int, role: str, **changes) -> LoggedOrder:
    """A steady row (demand 4, inventory 12) of a Rule-based Seat, with `changes`."""
    values = {
        "week": week,
        "role": role,
        "order": 4,
        "decided_by": "rule_based",
        "occupant_kind": "rule_based",
        "incoming_order": 4,
        "incoming_delivery": 4,
        "shipped": 4,
        "inventory": 12,
        "backlog": 0,
        "supply_line": 16,
    } | changes
    holding = Decimal("0.50") * values["inventory"]
    backorder = Decimal("1.00") * values["backlog"]
    values.setdefault("holding_cost", holding)
    values.setdefault("backorder_cost", backorder)
    values.setdefault("week_cost", values["holding_cost"] + values["backorder_cost"])
    return LoggedOrder(**values)


def log(weeks: int, changes: dict | None = None) -> DecisionLog:
    """`weeks` steady Weeks of the Classic chain; `changes[(week, role)]` alters one row."""
    changes = changes or {}
    return DecisionLog(
        roles=ROLES,
        rows=tuple(
            row(week, role, **changes.get((week, role), {}))
            for week in range(1, weeks + 1)
            for role in ROLES
        ),
    )


def student(weeks: range, role: str = "retailer", **changes) -> dict:
    return {
        (week, role): {"decided_by": "student", "occupant_kind": "student", **changes}
        for week in weeks
    }


def test_the_reference_trace_has_no_amplification_and_six_per_seat_per_week():
    """Addendum §B: constant demand 4 and every Order 4 keep inventory at 12 and cost 6.00."""
    built = facts(log(36), "wholesaler", PATTERNS)
    chain = built.chain
    assert (chain.weeks, chain.demand, chain.demand_std) == (36, (4,) * 36, Decimal("0.000"))
    for role in chain.by_role:
        assert role.amplification is None and role.orders_std == Decimal("0.000")
        assert role.first_large_order_week is None
        assert (role.holding_cost, role.backorder_cost) == (Decimal("216.00"), Decimal("0.00"))
        assert role.total_cost == Decimal("216.00")
    assert chain.total_cost == Decimal("864.00") == chain.ai_held_cost
    assert chain.ai_held_share == Decimal("1.000")
    assert built.seat.role == "wholesaler" and built.analysis_version == analysis.ANALYSIS_VERSION
    assert (built.seat.student_orders, built.seat.sm_excluded) == (0, True)
    assert built.seat.patterns == () and built.seat.moments == ()


def test_amplification_first_large_order_and_cost_types_per_role():
    demand = {(w, "retailer"): {"incoming_order": d} for w, d in [(1, 4), (2, 8), (3, 4), (4, 8)]}
    orders = {(w, "factory"): {"order": o, "backlog": 3} for w, o in [(1, 0), (2, 12), (3, 0)]}
    built = facts(log(4, demand | orders | {(4, "factory"): {"order": 12}}), "factory", PATTERNS)
    by_role = {role.role: role for role in built.chain.by_role}
    assert built.chain.demand == (4, 8, 4, 8) and built.chain.demand_std == Decimal("2.000")
    # Factory Orders 0, 12, 0, 12: population sd 6; 6 / 2 = 3.
    assert by_role["factory"].orders_std == Decimal("6.000")
    assert by_role["factory"].amplification == Decimal("3.000")
    assert by_role["factory"].first_large_order_week == 2
    assert by_role["retailer"].amplification == Decimal("0.000")
    assert by_role["factory"].backorder_cost == Decimal("9.00")
    assert by_role["factory"].holding_cost == Decimal("24.00")
    assert by_role["factory"].total_cost == Decimal("33.00")


def test_ratios_and_the_ai_share_are_rounded_at_three_places():
    # Demand 4, 5 (sd 0.5); Retailer Orders 0, 1 (sd 0.5) and Factory 1, 4 (sd 1.5).
    changes = {(2, "retailer"): {"incoming_order": 5, "order": 1}, (1, "retailer"): {"order": 0}}
    changes |= {(1, "factory"): {"order": 1}}
    built = facts(log(2, changes), "retailer", PATTERNS)
    by_role = {role.role: role for role in built.chain.by_role}
    assert by_role["retailer"].amplification == Decimal("1.000")
    assert by_role["factory"].amplification == Decimal("3.000")
    # Students hold Retailer and Wholesaler (24.00); the Distributor costs nothing; the AI-held
    # Factory 12.00 of 36.00: 0.333.
    third = {
        (w, r): {"decided_by": "student", "occupant_kind": "student"}
        for w in (1, 2)
        for r in ("retailer", "wholesaler")
    }
    split = facts(
        log(2, third | {(w, "distributor"): {"inventory": 0} for w in (1, 2)}), "retailer", PATTERNS
    )
    assert split.chain.ai_held_share == Decimal("0.333")


def test_no_chain_cost_gives_no_ai_share():
    zero = {(w, r): {"inventory": 0} for w in (1, 2) for r in ROLES}
    assert facts(log(2, zero), "retailer", PATTERNS).chain.ai_held_share is None


def test_the_chain_part_is_the_same_for_every_seat():
    changes = student(range(1, 13)) | {(5, "retailer"): {"order": 20, "backlog": 2}}
    chains = {facts(log(12, changes), role, PATTERNS).chain for role in ROLES}
    assert len(chains) == 1


def test_ai_held_cost_counts_weeks_the_occupant_was_not_a_student():
    """A Takeover: the Student holds the Retailer for Weeks 1-3, a Rule-based player after."""
    held = student(range(1, 4))
    built = facts(log(5, held), "retailer", PATTERNS)
    # 20 Seat-Weeks at 6.00; the Student held 3 of them.
    assert built.chain.ai_held_cost == Decimal("102.00")
    assert built.chain.ai_held_share == Decimal("0.850")
    assert built.seat.student_orders == 3 and built.seat.sm_excluded


def test_a_surge_after_a_shortage_needs_the_shortage_and_a_well_above_order():
    changes = {
        (3, "retailer"): {"backlog": 5},  # the shortage
        (5, "retailer"): {"order": 10},  # two Weeks after it: 10 ≥ 1.5·4 and 10 − 4 ≥ 4
        (6, "retailer"): {"order": 12},  # three Weeks after: too late
        (8, "retailer"): {"backlog": 1, "order": 7},  # 7 − 4 < 4
        (9, "retailer"): {"backlog": 1, "order": 8, "decided_by": "guided"},  # not a decision
    }
    built = facts(log(10, changes), "retailer", PATTERNS)
    assert [o.id for o in built.seat.patterns] == ["surge-after-shortage:retailer:5"]
    found = built.seat.patterns[0]
    assert (found.pattern, found.mechanism, found.week, found.order) == (
        "surge-after-shortage",
        "demand_information_lost",
        5,
        10,
    )
    assert found.decided_by == "rule_based" and found.state_seen.role == "retailer"
    assert [seen.role for seen in found.others_seen] == ["wholesaler", "distributor", "factory"]
    # Weeks 6-9 at 6.00, except Week 8 (6.00 + 1.00) and Week 9 (7.00).
    assert (found.later_cost, found.later_weeks) == (Decimal("26.00"), 4)


def test_a_large_order_with_a_full_supply_line():
    changes = {
        (2, "wholesaler"): {"order": 10, "supply_line": 24},  # 24 ≥ 6·4
        (3, "wholesaler"): {"order": 10, "supply_line": 23},
        (4, "wholesaler"): {"order": 10, "supply_line": 6, "incoming_order": 0},  # cover 6·1
    }
    built = facts(log(5, changes), "wholesaler", PATTERNS)
    assert [o.id for o in built.seat.patterns] == [
        "large-order-full-supply-line:wholesaler:2",
        "large-order-full-supply-line:wholesaler:4",
    ]
    assert built.seat.patterns[0].mechanism == "supply_line"
    # The last Week has fewer following Weeks.
    assert built.seat.patterns[1].later_weeks == 1


def test_a_very_low_order_after_an_overshoot():
    changes = {
        (2, "factory"): {"order": 2, "inventory": 16},  # 2 ≤ 0.5·4, 4 − 2 ≥ 2, 16 ≥ 4·4
        (3, "factory"): {"order": 2, "inventory": 15},  # no overshoot
        (4, "factory"): {"order": 3, "inventory": 40},  # not low enough
        (5, "factory"): {"order": 0, "incoming_order": 0, "inventory": 40},  # 0 − 0 < 2
    }
    built = facts(log(5, changes), "factory", PATTERNS)
    assert [o.id for o in built.seat.patterns] == ["low-after-overshoot:factory:2"]
    assert built.seat.patterns[0].mechanism == "delay"


def test_one_week_can_match_two_patterns():
    changes = {(2, "retailer"): {"order": 12, "backlog": 1, "supply_line": 30}}
    built = facts(log(3, changes), "retailer", PATTERNS)
    assert [o.pattern for o in built.seat.patterns] == [
        "surge-after-shortage",
        "large-order-full-supply-line",
    ]


def test_fewer_than_ten_student_orders_give_no_moments_but_keep_the_patterns():
    changes = student(range(1, 10))
    changes[(5, "retailer")] |= {"order": 12, "backlog": 2}
    built = facts(log(12, changes), "retailer", PATTERNS)
    assert built.seat.student_orders == 9 and built.seat.sm_excluded is True
    assert built.seat.moments == () and len(built.seat.patterns) == 1


def test_ten_student_orders_without_patterns_still_give_three_moments_by_order_gap():
    gaps = {(w, "retailer"): {"order": o} for w, o in [(3, 7), (6, 1), (9, 5), (11, 8)]}
    changes = student(range(2, 12))
    for key, value in gaps.items():
        changes[key] |= value
    # Week 12: the largest gap, but a Rule-based Week: never a moment.
    changes[(12, "retailer")] = {"order": 0}
    built = facts(log(12, changes), "retailer", PATTERNS)
    assert built.seat.student_orders == 10 and built.seat.sm_excluded is False
    assert built.seat.patterns == ()
    # Gaps: Week 11 → 4, Week 6 → 3, Week 3 → 3 (Week 9: 1). Equal gaps: the higher later
    # cost, then the earlier Week; listed by Week.
    assert [m.id for m in built.seat.moments] == [
        "moment:retailer:3",
        "moment:retailer:6",
        "moment:retailer:11",
    ]
    assert {m.chosen_by for m in built.seat.moments} == {"order_gap"}
    assert all(m.patterns == () for m in built.seat.moments)


def test_pattern_weeks_come_first_by_later_cost_then_the_gap_fills_up():
    changes = student(range(1, 13))
    changes[(3, "retailer")] |= {"order": 12, "backlog": 1}  # a surge, later cost 26
    changes[(4, "retailer")] |= {"backlog": 1}
    changes[(8, "retailer")] |= {"order": 2}  # gap 2: the filler
    changes[(10, "retailer")] |= {"order": 1}  # gap 3: the filler before Week 8
    changes[(9, "retailer")] |= {"order": 12, "backlog": 1}  # a surge, later cost 18
    changes[(7, "retailer")] = {"order": 20, "backlog": 1}  # a surge in a Rule-based Week
    built = facts(log(12, changes), "retailer", PATTERNS)
    ids = [o.id for o in built.seat.patterns]
    assert "surge-after-shortage:retailer:7" in ids  # listed, though no moment
    moments = built.seat.moments
    assert [(m.week, m.chosen_by) for m in moments] == [
        (3, "pattern"),
        (9, "pattern"),
        (10, "order_gap"),
    ]
    assert moments[0].patterns == ("surge-after-shortage:retailer:3",)
    assert moments[0].id == "moment:retailer:3" and moments[0].order == 12
    assert len(moments[0].others_seen) == 3


def test_at_most_three_pattern_moments_by_later_cost_then_week():
    changes = student(range(1, 13))
    for week in (2, 4, 6, 8):
        changes[(week, "retailer")] |= {"order": 12, "backlog": 1}
    changes[(7, "retailer")] |= {"inventory": 14}
    changes[(10, "retailer")] |= {"inventory": 30}
    # Later cost: Week 2 26.00, Week 4 27.00, Week 6 35.00, Week 8 33.00.
    built = facts(log(12, changes), "retailer", PATTERNS)
    assert [(m.week, m.chosen_by) for m in built.seat.moments] == [
        (4, "pattern"),
        (6, "pattern"),
        (8, "pattern"),
    ]


def test_the_function_is_deterministic_and_unknown_roles_are_refused():
    one = facts(log(3), "retailer", PATTERNS)
    assert one == facts(log(3), "retailer", PATTERNS)
    with pytest.raises(ValueError):
        facts(log(3), "nope", PATTERNS)
    short = DecisionLog(roles=ROLES[:2], rows=tuple(row(1, r) for r in ROLES[:2]))
    with pytest.raises(ValueError, match="not a Role"):
        facts(short, "factory", PATTERNS)


@pytest.mark.parametrize(
    "rows",
    [
        (),  # no Week
        tuple(row(1, r) for r in ROLES[:3]),  # a Role missing
        tuple(row(w, r) for w in (1, 3) for r in ROLES),  # a Week missing
        (*(row(1, r) for r in ROLES), row(1, "retailer")),  # a row twice
    ],
)
def test_an_incomplete_log_is_refused(rows):
    with pytest.raises(ValidationError):
        DecisionLog(roles=ROLES, rows=rows)


def test_a_chain_with_a_role_twice_and_cost_parts_that_do_not_add_up_are_refused():
    with pytest.raises(ValidationError, match="repeats"):
        DecisionLog(roles=(*ROLES, ROLES[0]), rows=())
    with pytest.raises(ValidationError, match="add up"):
        row(1, "retailer", week_cost=Decimal("1.00"))


def test_the_facts_set_serialises_to_json_and_back_unchanged():
    changes = student(range(1, 13)) | {(5, "retailer"): {"order": 20, "backlog": 2}}
    built = facts(log(12, changes), "retailer", PATTERNS)
    dumped = built.model_dump(mode="json")
    assert analysis.FactSet.model_validate(dumped) == built
    assert dumped["chain"]["total_cost"] == "290.00"
