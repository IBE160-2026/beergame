"""Story 2.4: the LLM player's prompt is built from the `SeatState` alone (FR-31, FR-32, AD-3,
C-1). Games are played in the pure engine; only the gateway tests touch the database."""

import inspect
import json
import re
import string
import uuid
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.ai import budget, config, gateway, mock
from app.ai.gateway import Failure, Result
from app.engine import GameSettings, WeekState, advance, initial_state, rule_based
from app.engine.settings import DemandStep
from app.modules.games.schemas import SeatState
from app.modules.games.views import build_seat_state
from app.modules.players import llm
from app.sim import load_rule_based_params, rule_based_policy
from tests.ai.helpers import mock_config, query
from tests.test_imports import imports

REAL_PROMPTS = Path(config.__file__).parent / "prompts"
GAME = uuid.UUID("00000000-0000-7000-8000-00000000000a")
SEAT = uuid.UUID("00000000-0000-7000-8000-00000000000b")
REFERENCE = 777
"""A reference Order no Classic prompt contains."""

_played: dict[GameSettings, tuple[list[WeekState], list[dict[str, int]]]] = {}


def play(settings: GameSettings) -> tuple[list[WeekState], list[dict[str, int]]]:
    """Every opened Week of a Game of four Rule-based players and the Orders of each Week."""
    if settings not in _played:
        policy = rule_based_policy(load_rule_based_params(rule_based.DEFAULT_SET_ID))
        state = initial_state(settings)
        states: list[WeekState] = []
        orders: list[dict[str, int]] = []
        while not state.finished:
            states.append(state)
            placed = dict(policy(settings, states, orders))
            state = advance(settings, state, placed)
            orders.append(placed)
        _played[settings] = (states, orders)
    return _played[settings]


def render(values: dict) -> str:
    template = (REAL_PROMPTS / "player_order" / "v1.md").read_text(encoding="utf-8")
    return string.Template(template).substitute(values)


def prompts(settings: GameSettings) -> dict[tuple[int, str], str]:
    """The rendered prompt of every Role and Week of the Game."""
    states, orders = play(settings)
    return {
        (week, str(role)): render(
            llm.build_inputs(build_seat_state(settings, states[:week], orders[: week - 1], role))
        )
        for week in range(1, len(states) + 1)
        for role in settings.roles
    }


CLASSIC = GameSettings()


@pytest.fixture(autouse=True)
def real_prompts(monkeypatch):
    """These tests read the shipped prompt files."""
    monkeypatch.setattr(config, "PROMPTS_DIR", REAL_PROMPTS)


def test_build_inputs_reads_the_seat_state_and_nothing_else():
    """A plain function of one `SeatState`: no coroutine (so no query), and the module imports
    nothing that reads game state besides the `SeatState` type of `games.service`."""
    assert list(inspect.signature(llm.build_inputs).parameters) == ["seat_state"]
    assert not inspect.iscoroutinefunction(llm.build_inputs)
    names = {name for path, _, name in imports(Path(llm.__file__).parent) if path.stem == "llm"}
    assert names <= {
        "uuid",
        "functools.cache",
        "pydantic.BaseModel",
        "pydantic.ConfigDict",
        "pydantic.Field",
        "pydantic.create_model",
        "app.ai.gateway",
        "app.modules.games.service",
    }, names


def test_every_role_and_week_renders_without_a_week_count_or_future_demand():
    rendered = prompts(CLASSIC)
    assert len(rendered) == 36 * 4
    # The same play with a longer horizon renders the same prompts: no Week count.
    longer = prompts(GameSettings(weeks=50))
    for key, text in rendered.items():
        assert longer[key] == text, key
    # Demand that changes only from Week 9 on renders the same prompts up to then.
    later = prompts(
        GameSettings(demand=DemandStep(kind="step", start=4, new_level=8, change_week=9))
    )
    for (week, role), text in rendered.items():
        if week <= 4:
            assert later[(week, role)] == text, (week, role)
    assert any(later[k] != rendered[k] for k in rendered if k[0] == 5)  # the test can see it
    for text in rendered.values():
        assert not re.search(r"\bweek \d", text, re.IGNORECASE)  # no absolute Week number


def test_customer_demand_only_in_the_retailer_prompt():
    for (week, role), text in prompts(CLASSIC).items():
        retailer = role == "retailer"
        assert ("customer demand" in text.lower()) == retailer, (week, role)
        assert ("end customers" in text) == retailer, (week, role)


def test_the_factory_is_told_it_produces():
    text = prompts(CLASSIC)[(6, "factory")]
    assert "You produce the units yourself." in text
    assert "in production" in text
    assert "your supplier" not in text


def test_other_seats_numbers_never_reach_a_prompt():
    states, orders = play(CLASSIC)
    week = 12
    for role in CLASSIC.roles:
        plain = render(
            llm.build_inputs(build_seat_state(CLASSIC, states[:week], orders[: week - 1], role))
        )
        changed = [
            state.model_copy(
                update={
                    "seats": tuple(
                        seat
                        if seat.role == role
                        else seat.model_copy(
                            update={"inventory": 7777, "backlog": 7777, "total_cost": Decimal(7777)}
                        )
                        for seat in state.seats
                    )
                }
            )
            for state in states[:week]
        ]
        tampered = render(
            llm.build_inputs(build_seat_state(CLASSIC, changed, orders[: week - 1], role))
        )
        assert tampered == plain, role
        assert "7777" not in tampered


BANNED = re.compile(
    r"\b(games?|gaming|gamif\w*|players?|play\w*|seats?|simulat\w*|beer|bullwhip|"
    r"four|4 (stages|businesses|roles)|chain'?s total|total of the chain|everyone|"
    r"all businesses)\b",
    re.IGNORECASE,
)


def test_the_prompt_text_frames_a_supply_chain_job_and_never_a_game():
    template = (REAL_PROMPTS / "player_order" / "v1.md").read_text(encoding="utf-8")
    for text in [template, *prompts(CLASSIC).values()]:
        assert not BANNED.search(text), BANNED.search(text)
        assert not re.search(r"advance|next week (opens|starts) when", text, re.IGNORECASE)
    assert "supply chain manager" in template
    assert "must ship what your customers ordered" in template
    assert "$delay_rule" in template and "reaches your inventory in" in render_retailer_week(6)
    assert "costs $holding_rate" in template and "costs $backorder_rate" in template
    assert "Decide the best order for your part of the supply chain" in template
    assert "There is no last week" in template
    assert '{"order": N}' in template


def render_retailer_week(week: int) -> str:
    return prompts(CLASSIC)[(week, "retailer")]


def test_a_rendered_prompt_reads_as_expected():
    text = render_retailer_week(6)
    assert "Your business is the retailer." in text
    assert "reaches your inventory in 4 weeks at the earliest" in text
    assert "costs 0.50" in text and "costs 1.00" in text
    assert "weeks ago | customer demand | received" in text
    assert "a whole number from 0 to 999" in text
    assert render_retailer_week(1).count("(no earlier weeks)") == 1


def test_the_order_schema_takes_one_whole_number_in_the_order_range():
    schema = llm.order_schema(0, 999)
    assert schema is llm.order_schema(0, 999)
    assert schema.model_validate_json('{"order": 12}').order == 12
    for answer in (
        "{}",
        '{"order": 4.5}',
        '{"order": 4.0}',
        '{"order": "4"}',
        '{"order": -1}',
        '{"order": 1000}',
        '{"order": 4, "note": "x"}',
    ):
        with pytest.raises(ValidationError):
            schema.model_validate_json(answer)
    json_schema = schema.model_json_schema()
    assert json_schema["properties"]["order"]["type"] == "integer"
    assert (
        json_schema["properties"]["order"]["minimum"],
        json_schema["properties"]["order"]["maximum"],
    ) == (0, 999)
    assert json_schema["required"] == ["order"]


def state(week: int = 6, role: str = "wholesaler"):
    states, orders = play(CLASSIC)
    return build_seat_state(CLASSIC, states[:week], orders[: week - 1], role)


async def test_caller_and_mock_answer_stay_out_of_prompt_and_request():
    seat_state = state()
    inputs = llm.request_inputs(GAME, SEAT, seat_state.week, seat_state, REFERENCE)
    assert inputs.caller == {"game": str(GAME), "seat": str(SEAT), "week": 6}
    assert inputs.mock_answer == {"order": REFERENCE}
    assert inputs.values == llm.build_inputs(seat_state)
    shown = await gateway.preview(
        llm.PURPOSE, inputs, llm.order_schema(seat_state.min_order, seat_state.max_order)
    )
    request = json.dumps(shown.request)
    assert shown.prompt_version == 1
    for secret in (str(GAME), str(SEAT), str(REFERENCE)):
        assert secret not in request
    assert "player" not in request.lower()
    assert shown.request["output_schema"]["title"] == "OrderDecision"
    assert shown.request["prompt"].startswith("You are the supply chain manager")


async def scope(**changes) -> budget.BudgetScope:
    row = await config.add(config.parse(mock_config(prompts={"player_order": 1}, **changes)))
    target = budget.BudgetScope.evaluation(row.id)
    await budget.set_budget(target, limit=Decimal(1), reserve=Decimal(0))
    return target


async def test_the_request_is_sent_as_previewed_and_bad_answers_are_retried(ai_db):
    target = await scope()
    seat_state = state()
    inputs = llm.request_inputs(GAME, SEAT, seat_state.week, seat_state, REFERENCE)
    schema = llm.order_schema(seat_state.min_order, seat_state.max_order)
    bad = ["{}", '{"order": 4.5}', '{"order": "4"}', '{"order": -1}', '{"order": 1000}']
    with mock.script(*bad):
        result = await gateway.run(llm.PURPOSE, target, inputs, schema, None)
    assert isinstance(result, Result) and result.output.order == REFERENCE
    rows = query(
        ai_db,
        "SELECT outcome, request, caller_ref FROM llm_call ORDER BY started_at, attempt",
    )
    assert [row[0] for row in rows] == ["invalid_output"] * 5 + ["ok"]
    shown = await gateway.preview(llm.PURPOSE, inputs, schema, target)
    for _, request, caller in rows:
        assert request == json.loads(json.dumps(shown.request))
        assert caller == {"game": str(GAME), "seat": str(SEAT), "week": 6}
        assert str(GAME) not in json.dumps(request) and str(REFERENCE) not in json.dumps(request)


async def test_six_bad_answers_end_in_invalid_output(ai_db):
    target = await scope()
    seat_state = state()
    inputs = llm.request_inputs(GAME, SEAT, seat_state.week, seat_state, REFERENCE)
    with mock.script(*['{"order": 1000}'] * 6):
        result = await gateway.run(
            llm.PURPOSE, target, inputs, llm.order_schema(0, seat_state.max_order), None
        )
    assert isinstance(result, Failure) and result.kind == "invalid_output"
    assert len(result.llm_call_ids) == 6


def test_the_seat_state_has_no_near_optimal_field():
    """Story 2.9 (AD-3): the near-optimal reference uses the whole chain and demand series; the
    `SeatState` and the function that builds it take neither."""
    fields = set(SeatState.model_fields)
    assert not {name for name in fields if "near" in name or "reference" in name}
    assert list(inspect.signature(build_seat_state).parameters) == [
        "settings",
        "states",
        "orders",
        "role",
    ]


async def test_the_near_optimal_reference_never_reaches_state_seen_or_the_prompt(
    games_db, ai_db, monkeypatch
):
    """Story 2.9 (AD-3, FR-31): with the near-optimal reference patched to a sentinel, the
    sentinel is stored on the turns and Decision log rows of an LLM Game but appears in no
    `state_seen`, no `SeatState` and no request sent to the model."""
    from app.engine import near_optimal
    from app.platform import jobs
    from tests.games.helpers import query as games_query
    from tests.players.test_llm_jobs import llm_game

    monkeypatch.setattr(near_optimal, "order", lambda *args: 987)
    monkeypatch.setattr(near_optimal, "ALGORITHM_VERSION", "canary-9")
    game_id = await llm_game(("wholesaler",))
    await jobs.run_until_idle([jobs.AI_ORDERS])
    stored = games_query(
        games_db,
        "SELECT w.near_optimal_reference_order, w.near_optimal_algorithm_version, w.state_seen, "
        "w.decided_by FROM seat_weeks w WHERE w.game_id = %s",
        (game_id,),
    )
    assert {(row[0], row[1]) for row in stored} == {(987, "canary-9")}
    assert "llm" in {row[3] for row in stored}
    for _, _, seen, _ in stored:
        text = json.dumps(seen)
        assert "987" not in text and "canary" not in text and "near" not in text
    requests = games_query(games_db, "SELECT request FROM llm_call")
    assert requests
    for (request,) in requests:
        text = json.dumps(request)
        assert "987" not in text and "canary" not in text


def test_no_personal_data_in_the_structured_inputs():
    for value in llm.build_inputs(state()).values():
        assert isinstance(value, (str, int))
    keys = set(llm.build_inputs(state()))
    assert not keys & {"name", "email", "student_number", "user_id", "game", "seat", "week"}
