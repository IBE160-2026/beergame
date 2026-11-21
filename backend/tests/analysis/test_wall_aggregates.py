"""`analysis.wall.wall_aggregates` (Story 7.4, AD-1, NFR-9): the Matrisevegg's median row with
the middle half of the Games and the mean chain cost row, per Uke over the Games that reached it.
Golden values for an odd, an even, a single and no Game."""

from decimal import Decimal

from app.analysis.wall import Cells, PlayedGame, WallWeek, quartiles, wall_aggregates
from app.engine.state import SeatState, WeekState

CHAIN = ("retailer", "wholesaler", "distributor", "factory")


def seat(role: str, net: int = 0, cost: str = "1") -> SeatState:
    return SeatState(
        role=role,
        incoming_order=4,
        incoming_delivery=4,
        shipped=4,
        inventory=max(net, 0),
        backlog=max(-net, 0),
        cost=Decimal(cost),
        total_cost=Decimal(0),
        incoming_orders=(),
        goods_slots=(),
        production_orders=(),
    )


def week(number: int, factory: int, cost: str = "1", finished: bool = False) -> WeekState:
    """A Week whose Fabrikk has Netto lager `factory` and Kost per uke `cost`; the other three
    Seats cost 1 each, so the chain's cost is `cost` + 3."""
    return WeekState(
        week=number,
        finished=finished,
        seats=tuple(
            seat(r, factory if r == "factory" else 0, cost if r == "factory" else "1")
            for r in CHAIN
        ),
    )


def game(*nets: int, orders: dict[tuple[int, str], int] | None = None) -> PlayedGame:
    return PlayedGame(
        states=tuple(week(i + 1, net) for i, net in enumerate(nets)), orders=orders or {}
    )


def d(text: str) -> Decimal:
    return Decimal(text)


def test_an_odd_number_of_games():
    [uke] = wall_aggregates([game(4), game(-2), game(10)], "factory", Cells.NET)
    assert uke == WallWeek(
        week=1,
        games=3,
        median=d("4"),
        lower_quartile=d("1"),
        upper_quartile=d("7"),
        chain_games=3,
        chain_cost_mean=d("4.00"),
    )


def test_an_even_number_of_games():
    [uke] = wall_aggregates([game(10), game(4)], "factory", Cells.NET)
    assert (uke.games, uke.median, uke.lower_quartile, uke.upper_quartile) == (
        2,
        d("7"),
        d("5.5"),
        d("8.5"),
    )
    four = wall_aggregates([game(1), game(2), game(3), game(4)], "factory", Cells.NET)[0]
    assert (four.median, four.lower_quartile, four.upper_quartile) == (
        d("2.5"),
        d("1.75"),
        d("3.25"),
    )


def test_a_single_game_is_its_own_median_and_middle_half():
    [uke] = wall_aggregates([game(5)], "factory", Cells.NET)
    assert (uke.games, uke.median, uke.lower_quartile, uke.upper_quartile) == (1, 5, 5, 5)


def test_no_game_gives_no_uke():
    assert wall_aggregates([], "factory", Cells.NET) == []
    assert quartiles([]) is None


def test_each_uke_counts_only_the_games_that_reached_it():
    weeks = wall_aggregates([game(1, 2, 3), game(10, 20, 30, 40, 50)], "factory", Cells.NET)
    assert [(w.week, w.games, w.median, w.chain_games) for w in weeks] == [
        (1, 2, d("5.5"), 2),
        (2, 2, d("11"), 2),
        (3, 2, d("16.5"), 2),
        (4, 1, d("40"), 1),
        (5, 1, d("50"), 1),
    ]


def test_an_open_uke_without_an_order_counts_for_the_chain_cost_only():
    placed = {(1, "factory"): 8, (2, "factory"): 12}
    done = game(0, 0, orders=placed)
    open_week = game(0, 0, orders={(1, "factory"): 4})  # Uke 2 open, no Order yet
    weeks = wall_aggregates([done, open_week], "factory", Cells.ORDER)
    assert [(w.week, w.games, w.median, w.chain_games) for w in weeks] == [
        (1, 2, d("6"), 2),
        (2, 1, d("12"), 2),
    ]
    # A Role nobody has ordered for has no median, but the chain still cost something.
    nobody = wall_aggregates([open_week], "retailer", Cells.ORDER)
    assert (nobody[0].games, nobody[0].median, nobody[0].chain_cost_mean) == (0, None, d("4.00"))


def test_the_cost_cells_and_the_chain_cost_mean_in_ore():
    games = [
        PlayedGame(states=(week(1, 0, cost="2.5"),)),
        PlayedGame(states=(week(1, 0, cost="1"),)),
        PlayedGame(states=(week(1, 0, cost="1"),)),
    ]
    [uke] = wall_aggregates(games, "factory", Cells.COST)
    assert uke.median == d("1")
    assert uke.upper_quartile == d("1.75")
    # (5.5 + 4 + 4) / 3 = 4.5
    assert uke.chain_cost_mean == d("4.50")
    third = wall_aggregates(
        [PlayedGame(states=(week(1, 0, cost="1.01"),)), *games[1:]], "factory", Cells.COST
    )
    assert third[0].chain_cost_mean == d("4.00")  # 12.01 / 3 = 4.0033… → 4.00


def test_a_finished_state_is_no_uke_and_other_roles_read_their_own_seat():
    played = PlayedGame(states=(week(1, -3), week(2, 4), week(3, 9, finished=True)))
    weeks = wall_aggregates([played], "factory", Cells.NET)
    assert [w.median for w in weeks] == [d("-3"), d("4")]
    assert [w.median for w in wall_aggregates([played], "retailer", Cells.NET)] == [0, 0]
