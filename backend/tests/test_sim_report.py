"""Story 2.11: the batch report's figures, computed from Decision log, occupancy and `llm_call`
rows alone (AD-15, AD-22). Pure: no database."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app import sim_report
from app.modules.games.schemas import (
    DecidedBy,
    DecisionLogRow,
    Fallback,
    GameSummary,
    OccupancyReason,
    OccupancyRow,
    OccupantKind,
)

T0 = datetime(2026, 11, 18, 12, 0, tzinfo=UTC)


@dataclass(frozen=True)
class Attempt:
    id: str
    started_at: datetime
    latency_ms: int
    input_tokens: int = 100
    output_tokens: int = 20
    reasoning_tokens: int = 5
    cost_usd: Decimal = Decimal("0.001")


def row(
    seat: str,
    week: int,
    decided_by: DecidedBy,
    occupant: OccupantKind = OccupantKind.LLM,
    fallback: Fallback = Fallback.NONE,
    calls: tuple[str, ...] = (),
) -> DecisionLogRow:
    return DecisionLogRow.model_construct(
        week=week,
        seat_id=seat,
        decided_by=decided_by,
        occupant_kind=occupant,
        fallback=fallback,
        llm_call_ids=calls,
    )


def occupancy(
    seat: str, kind: OccupantKind, reason: OccupancyReason = OccupancyReason.INITIAL, week: int = 1
) -> OccupancyRow:
    return OccupancyRow(
        role="retailer",
        seat_id=seat,
        from_week=week,
        occupant_kind=kind,
        policy_id=None,
        reason=reason,
    )


def summary(game_id: str, chain: str) -> GameSummary:
    return GameSummary(
        game_id=game_id,
        demand_seed=1,
        weeks=3,
        total_cost=(("retailer", Decimal(chain)),),
        chain_cost=Decimal(chain),
        orders=(),
        check=None,
    )


def game(game_id: str, chain: str = "100", **parts) -> sim_report.GameInput:
    return sim_report.GameInput(
        summary=summary(game_id, chain),
        log=parts.get("log", ()),
        occupancy=parts.get("occupancy", ()),
        attempts=parts.get("attempts", ()),
        effort_level=parts.get("effort_level", "standard"),
    )


def measure(games, pass_lines=None, mock=False) -> sim_report.BatchFigures:
    return sim_report.measure(
        "b",
        T0,
        mock=mock,
        model_config_id="c",
        pass_lines=pass_lines or {},
        games=games,
    )


def llm_game(game_id: str = "g1", chain: str = "100", cost: str = "0.001") -> sim_report.GameInput:
    """One `llm` Seat (s1) and one Rule-based Seat (s2): a Guided Week, then three LLM-path
    Orders (one with a retry, one fallback after 2 failed attempts)."""
    attempts = [
        Attempt("a1", T0, 300, cost_usd=Decimal(cost)),
        Attempt("a2", T0 + timedelta(seconds=10), 500, cost_usd=Decimal(cost)),
        Attempt("a3", T0 + timedelta(seconds=11), 400, cost_usd=Decimal(cost)),
        Attempt("a4", T0 + timedelta(seconds=20), 1000, cost_usd=Decimal(cost)),
        Attempt("a5", T0 + timedelta(seconds=22), 1000, cost_usd=Decimal(cost)),
    ]
    log = [
        row("s1", 1, DecidedBy.GUIDED),
        row("s2", 1, DecidedBy.GUIDED, OccupantKind.RULE_BASED),
        row("s1", 2, DecidedBy.LLM, calls=("a1",)),
        row("s2", 2, DecidedBy.RULE_BASED, OccupantKind.RULE_BASED),
        row("s1", 3, DecidedBy.LLM, calls=("a2", "a3")),
        row("s2", 3, DecidedBy.RULE_BASED, OccupantKind.RULE_BASED),
        row("s1", 4, DecidedBy.RULE_BASED, fallback=Fallback.TIMEOUT, calls=("a4", "a5")),
        row("s2", 4, DecidedBy.RULE_BASED, OccupantKind.RULE_BASED),
    ]
    seats = [occupancy("s1", OccupantKind.LLM), occupancy("s2", OccupantKind.RULE_BASED)]
    return game(game_id, chain, log=log, occupancy=seats, attempts=attempts)


def test_the_figures_of_one_game_follow_the_one_mapping():
    figures = measure([llm_game()]).games[0].figures
    assert (figures.calls, figures.ai_cost_usd) == (5, Decimal("0.005"))
    assert (figures.input_tokens, figures.output_tokens, figures.reasoning_tokens) == (500, 100, 25)
    # Attempt latencies 300, 400, 500, 1000, 1000: nearest-rank median 500, p95 1000.
    assert figures.latency_ms == sim_report.Spread(500, 1000)
    # Spans: 300; 10.0 s to 11.4 s = 1400; 20.0 s to 23.0 s = 3000.
    assert figures.order_time_ms == sim_report.Spread(1400, 3000)
    assert (figures.llm_orders, figures.retries_mean, figures.retries_max) == (
        3,
        Decimal(2) / 3,
        1,
    )
    assert figures.fallbacks == ((Fallback.NONE, 2), (Fallback.TIMEOUT, 1))
    # AD-15: decided_by = llm over occupant ≠ student and decided_by ≠ guided: 2 of 6.
    assert (figures.llm_decided, figures.llm_share_base) == (2, 6)
    assert (figures.llm_seats, figures.switched_seats) == (1, 0)


def test_student_rows_and_guided_weeks_stay_out_of_the_share_of_llm_orders():
    log = [
        row("s1", 2, DecidedBy.LLM, calls=("a",)),
        row("s3", 2, DecidedBy.STUDENT, OccupantKind.STUDENT),
        row("s3", 1, DecidedBy.GUIDED, OccupantKind.STUDENT),
        row("s1", 1, DecidedBy.GUIDED),
    ]
    figures = measure([game("g", log=log, attempts=[Attempt("a", T0, 10)])]).total
    assert (figures.llm_decided, figures.llm_share_base) == (1, 1)


def test_a_guard_switched_seat_counts_once_and_only_when_it_started_as_llm():
    seats = [
        occupancy("s1", OccupantKind.LLM),
        occupancy("s1", OccupantKind.RULE_BASED, OccupancyReason.GUARD_SWITCH, 10),
        occupancy("s2", OccupantKind.LLM),
        occupancy("s3", OccupantKind.RULE_BASED),
        occupancy("s3", OccupantKind.RULE_BASED, OccupancyReason.GUARD_SWITCH, 5),
    ]
    figures = measure([game("g", occupancy=seats)])
    assert (figures.total.llm_seats, figures.total.switched_seats) == (2, 1)
    lines = sim_report.report_lines(figures)
    assert "  guard_switched seats=1/2 share=0.5000" in lines


def test_the_batch_adds_the_games_and_takes_the_cv_of_chain_cost():
    figures = measure([llm_game("g1", "100"), llm_game("g2", "200")])
    assert figures.total.calls == 10
    assert figures.cost_per_game_usd == Decimal("0.005")
    # Sample standard deviation 70.71… over the mean 150.
    assert figures.chain_cost_cv.quantize(Decimal("0.0001")) == Decimal("0.4714")
    assert measure([llm_game()]).chain_cost_cv is None
    assert sim_report.coefficient_of_variation([Decimal(0), Decimal(0)]) is None


@pytest.mark.parametrize(
    ("lines", "verdicts"),
    [
        (
            {"cost_per_game_usd": 0.10, "time_per_order_p95_s": 8, "switched_share": 0.25},
            ["pass", "pass", "pass"],
        ),
        (
            {"cost_per_game_usd": 0.001, "time_per_order_p95_s": 2, "switched_share": 0},
            ["miss", "miss", "pass"],
        ),
        ({}, ["no line", "no line", "no line"]),
        ({"cost_per_game_usd": "0.005"}, ["pass", "no line", "no line"]),
    ],
)
def test_pass_lines_pass_or_miss_and_have_no_default(lines, verdicts):
    figures = measure([llm_game()], lines)
    assert [line.verdict for line in figures.pass_lines] == verdicts
    report = sim_report.report_lines(figures)
    for name, verdict in zip(sim_report.PASS_LINES, verdicts, strict=True):
        (printed,) = [line for line in report if line.startswith(f"pass_line {name} ")]
        assert printed.endswith(verdict)


def test_a_value_on_its_line_passes():
    (cost, *_) = measure([llm_game()], {"cost_per_game_usd": "0.005"}).pass_lines
    assert (cost.measured, cost.verdict) == (Decimal("0.005"), "pass")


def test_a_batch_cut_short_misses_every_line_it_carries():
    limited = [
        occupancy("x1", OccupantKind.LLM),
        occupancy("x1", OccupantKind.RULE_BASED, OccupancyReason.COST_LIMIT, 3),
    ]
    figures = measure([llm_game("g1"), game("g2", occupancy=limited)], {"cost_per_game_usd": 0.10})
    assert [line.verdict for line in figures.pass_lines] == [
        "miss (cut short)",
        "no line",
        "no line",
    ]


def test_the_printed_measured_values():
    report = sim_report.report_lines(
        measure(
            [llm_game()],
            {"cost_per_game_usd": 0.10, "time_per_order_p95_s": 8, "switched_share": 0.25},
        )
    )
    assert report[-3:] == [
        "pass_line cost_per_game_usd line=0.1 measured=0.00500000 pass",
        "pass_line time_per_order_p95_s line=8 measured=3.000 pass",
        "pass_line switched_share line=0.25 measured=0.0000 pass",
    ]


def test_a_batch_without_llm_seats_has_nothing_to_measure():
    seats = [occupancy("s1", OccupantKind.RULE_BASED)]
    log = [row("s1", 2, DecidedBy.RULE_BASED, OccupantKind.RULE_BASED)]
    figures = measure(
        [game("g", log=log, occupancy=seats)],
        {"cost_per_game_usd": 0.1, "time_per_order_p95_s": 8, "switched_share": 0.25},
    )
    assert [line.verdict for line in figures.pass_lines] == ["n/a", "n/a", "n/a"]
    report = sim_report.report_lines(figures)
    assert report[0] == "provider none (no llm Seats)"
    assert "  llm_share orders=0/1 share=0.0000" in report
    assert "  time_per_order_ms median=n/a p95=n/a" in report
    assert "  retries_per_order mean=n/a max=n/a" in report
    assert "  ai_cost_per_game usd=n/a" in report
    assert "  chain_cost_cv n/a" in report
    assert "  guard_switched seats=0/0 share=n/a" in report


def test_a_mock_batch_says_so_on_its_first_line():
    assert sim_report.report_lines(measure([llm_game()], mock=True))[0] == sim_report.MOCK_WARNING
    assert sim_report.report_lines(measure([llm_game()]))[0] == "provider real"


def test_cut_short_names_the_first_game_with_a_cost_limit_row():
    limited = [
        occupancy("x1", OccupantKind.LLM),
        occupancy("x1", OccupantKind.RULE_BASED, OccupancyReason.COST_LIMIT, 7),
        occupancy("x2", OccupantKind.LLM),
        occupancy("x2", OccupantKind.RULE_BASED, OccupancyReason.COST_LIMIT, 6),
    ]
    later = [
        occupancy("y1", OccupantKind.LLM),
        occupancy("y1", OccupantKind.RULE_BASED, OccupancyReason.COST_LIMIT, 1),
    ]
    figures = measure([llm_game("g1"), game("g2", occupancy=limited), game("g3", occupancy=later)])
    assert figures.cut_short == sim_report.CutShort("g2", 6)
    assert sim_report.report_lines(figures)[-4].startswith("cut_short game g2 week 6 ")
    assert measure([llm_game()]).cut_short is None
    assert "cut_short no" in sim_report.report_lines(measure([llm_game()]))


def test_the_report_has_a_head_a_block_per_game_and_a_batch_block():
    report = sim_report.report_lines(measure([llm_game("g1"), llm_game("g2")]))
    assert report[1] == (
        f"batch b started {T0.isoformat()} games 2 model_config c effort_level standard"
    )
    heads = [line for line in report if line.startswith("game ")]
    assert heads == ["game g1 seed 1 weeks 3 check missing", "game g2 seed 1 weeks 3 check missing"]
    assert "batch games 2" in report
    assert "  fallback llm_orders=6 none=0.6667 timeout=0.3333" in report
    assert "  retries_per_order mean=0.67 max=1" in report


@pytest.mark.parametrize(
    ("values", "share", "expected"),
    [([], "0.5", None), ([7], "0.95", 7), ([1, 2, 3, 4], "0.5", 2), ([5, 1, 3], "0.95", 5)],
)
def test_nearest_rank(values, share, expected):
    assert sim_report.nearest_rank(values, Decimal(share)) == expected
