"""`analysis.class_cost` (Story 7.6, AD-1, AD-10): the finished games' chain cost median with its
middle half, and the mean lager and restordre per finished game for the chain and per Role.
Golden values for one, two (even), three (odd) and no Game."""

from decimal import Decimal as D

from app.analysis.class_cost import ClassCost, FinishedGame, RoleMean, class_cost

CHAIN = ("retailer", "wholesaler", "distributor", "factory")


def game(chain: str, **roles: tuple[str, str]) -> FinishedGame:
    return FinishedGame(D(chain), {role: (D(h), D(b)) for role, (h, b) in roles.items()})


def test_no_game_gives_none():
    assert class_cost([], CHAIN) is None


def test_one_game_is_its_own_median_and_quartiles():
    one = game("800", retailer=("100", "50"), wholesaler=("0", "650"))
    assert class_cost([one], CHAIN) == ClassCost(
        games=1,
        median=D("800"),
        lower_quartile=D("800"),
        upper_quartile=D("800"),
        holding_cost=D("100.00"),
        backorder_cost=D("700.00"),
        roles=(
            RoleMean("retailer", D("100.00"), D("50.00"), D("150.00")),
            RoleMean("wholesaler", D("0.00"), D("650.00"), D("650.00")),
            RoleMean("distributor", D("0.00"), D("0.00"), D("0.00")),
            RoleMean("factory", D("0.00"), D("0.00"), D("0.00")),
        ),
    )


def test_two_games_interpolate_and_average_to_the_ore():
    found = class_cost(
        [
            game("1000", retailer=("10.5", "0"), factory=("0", "989.5")),
            game("1501", retailer=("11", "0"), factory=("1", "1489")),
        ],
        CHAIN,
    )
    assert found is not None
    assert (found.games, found.lower_quartile, found.median, found.upper_quartile) == (
        2,
        D("1125.25"),
        D("1250.5"),
        D("1375.75"),
    )
    assert found.roles[0] == RoleMean("retailer", D("10.75"), D("0.00"), D("10.75"))
    assert found.roles[3] == RoleMean("factory", D("0.50"), D("1239.25"), D("1239.75"))
    assert (found.holding_cost, found.backorder_cost) == (D("11.25"), D("1239.25"))


def test_three_games_take_the_middle_one_in_any_order():
    found = class_cost(
        [
            game("3000", retailer=("1", "1")),
            game("1000", retailer=("1", "1")),
            game("2000", retailer=("1", "2")),
        ],
        CHAIN,
    )
    assert found is not None
    assert (found.lower_quartile, found.median, found.upper_quartile) == (
        D("1500"),
        D("2000"),
        D("2500"),
    )
    assert found.roles[0] == RoleMean("retailer", D("1.00"), D("1.33"), D("2.33"))
