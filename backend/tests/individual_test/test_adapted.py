"""Get Adapted items from my own game and Replay (Story 11.7, FR-53, NFR-9, AD-7, AD-15, AD-23).

`tests.commands.open_attempt` builds the Student's Adapted items from the stored facts sets of
their Seat in their own Class game and in their Replay, in the opening transaction, and freezes
them after the Core items with the Adapted total weight between them; a Student with fewer than 10
own Orders (or whose game, Replay or facts cannot be read) gets the replacement Core items
instead. The golden test plays a Class game and a Replay and re-derives every number of the text
from `seat_weeks`; the other tests stand the two Games in with hand-built facts sets (the seam
`adapted._sources` / `adapted._facts`). The api's clock is fixed."""

import json
import re
import uuid
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from structlog.testing import capture_logs

from app.analysis.adapted import ROLE_NAMES, AdaptedTemplates
from app.analysis.facts import facts
from app.analysis.sentences import format_money, format_number
from app.modules.content import service as content
from app.modules.games import service as games
from app.modules.ops import sweep
from app.modules.replay import service as replay_service
from app.modules.tests import adapted
from tests.analysis.test_facts import PATTERNS, log, student
from tests.classes.test_classes import LECTURER
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import clock, klass
from tests.classes.test_staff import call
from tests.classes.test_student_registration import emitted
from tests.debrief.test_explanation import played, user_id
from tests.individual_test.test_open import REPLACEMENTS, attempts, code, path, replayed
from tests.messaging.helpers import rows
from tests.replay.test_start import passed, start
from tests.sessions.test_dates import START
from tests.sessions.test_lock import MINUTE, _empty
from tests.sessions.test_open_games import confirmed
from tests.sessions.test_play import play
from tests.sessions.test_student_choice import email

__all__ = ["_empty", "clock", "emitted", "klass"]

REPLAY_WEEKS = 4
"""The Replay is shortened to four Weeks: its template reads the outcome, which needs no moment."""
OWN, REPLAY = "tilpasset-eget-spill", "tilpasset-replay"
TEMPLATES = 2
"""The latest Adapted item template version: version 2 adds the wordings (Story 11.8)."""


def unpublish(version: int) -> None:
    """A version a test published, taken out again at once: other tests lock on the latest."""
    execute(
        "DELETE FROM content_records WHERE kind = 'adapted_templates' AND version = %s", version
    )


def answer_url(session_id: str, item_id: str) -> str:
    return f"{path(session_id)}/answers/{item_id}"


def seat_rows(game_id: str, role: str) -> dict[int, tuple[int, dict]]:
    """The Seat's `seat_weeks` rows: Week → (Order, `state_seen`)."""
    found = rows(
        'SELECT w.week, w."order", w.state_seen FROM seat_weeks w JOIN seats s ON s.id = w.seat_id '
        "WHERE w.game_id = %s AND s.role = %s",
        game_id,
        role,
    )
    return {week: (order, seen) for week, order, seen in found}


def costs(seen: dict, kind: str) -> Decimal:
    return sum((Decimal(line["amount"]) for line in seen["cost_lines"] if line["kind"] == kind), 0)


def numbers(text: str) -> list[str]:
    """Every number written in a text: whole numbers with no-break thousands, amounts with a
    decimal comma."""
    return re.findall(r"−?\d+(?: \d{3})*(?:,\d\d)?", text)


@pytest.mark.long
async def test_the_items_are_filled_from_the_seat_week_rows_of_both_games(klass, monkeypatch):
    drawn = replay_service.replay_settings
    monkeypatch.setattr(
        replay_service,
        "replay_settings",
        lambda template, seed: drawn(template, seed).model_copy(update={"weeks": REPLAY_WEEKS}),
    )
    session_id, game_id, debrief, _, me = await played(klass)
    role = debrief["role"]
    student_id = user_id(me)
    await passed(student_id, session_id)
    replay_id = (await start(session_id, me)).json()["game_id"]
    for week in range(1, REPLAY_WEEKS + 1):
        assert (await play(me, replay_id)).json()["seat_state"]["week"] == week
        ordered = await call(
            me, "POST", f"/api/me/games/{replay_id}/weeks/{week}/order", json={"order": 3 + week}
        )
        assert ordered.status_code == 204

    with capture_logs() as logs:
        opened = await call(me, "POST", path(session_id))
    assert opened.status_code == 201
    [(_, _, _, selection, items, *_)] = attempts(session_id)
    [own, replayed_] = [item for item in items if item["type"] == "adapted"]
    assert [item["id"] for item in items][-2:] == [OWN, REPLAY]
    assert (own["weight"], replayed_["weight"]) == (15, 15)
    assert (
        sum(item["weight"] for item in items)
        == 100
        == selection["adapted_weight"]
        + sum(selection["weights"][i["id"]] for i in items if i["type"] != "adapted")
    )
    _, templates = await content.adapted_templates(None)
    text_of = {t.id: t.text for t in templates.templates}

    # The own game's item: the moment the facts set holds, every number from that Week's row.
    stored = await games.fact_set(game_id, role)
    assert own["fact_set_id"] == stored.id and own["template_version"] == TEMPLATES
    [fact_id] = own["fact_ids"]
    assert fact_id in {moment.id for moment in stored.facts.seat.moments}
    week = int(fact_id.rsplit(":", 1)[1])
    order, seen = seat_rows(game_id, role)[week]
    expected = text_of[OWN].format(
        week=format_number(week),
        role=ROLE_NAMES[role],
        order=format_number(order),
        incoming_order=format_number(seen["incoming_order"]),
        inventory=format_number(seen["inventory"]),
        backlog=format_number(seen["backlog"]),
        supply_line=format_number(seen["supply_line"]),
    )
    assert own["text"] == {"text": expected, "ai_generated": False, "llm_call_id": None}
    row_numbers = {format_number(week), format_number(order)} | {
        format_number(seen[k]) for k in ("incoming_order", "inventory", "backlog", "supply_line")
    }
    assert set(numbers(own["text"]["text"])) <= row_numbers

    # The Replay's item: the Seat's cost summed over its rows, the number of Weeks it ran.
    replay_rows = seat_rows(replay_id, role)
    assert sorted(replay_rows) == list(range(1, REPLAY_WEEKS + 1))
    assert replayed_["fact_set_id"] == (await games.fact_set(replay_id, role)).id
    assert replayed_["fact_ids"] == [f"outcome:{role}"]
    total = sum((Decimal(seen["week_cost"]) for _, seen in replay_rows.values()), Decimal(0))
    holding = sum((costs(seen, "holding") for _, seen in replay_rows.values()), Decimal(0))
    backorder = sum((costs(seen, "backorder") for _, seen in replay_rows.values()), Decimal(0))
    assert holding + backorder == total
    expected = text_of[REPLAY].format(
        role=ROLE_NAMES[role],
        weeks=format_number(REPLAY_WEEKS),
        total_cost=format_money(total),
        holding_cost=format_money(holding),
        backorder_cost=format_money(backorder),
    )
    assert replayed_["text"]["text"] == expected
    # The two facts sets are the stored ones (AD-7), and no text reached a log line.
    assert {fid for (fid,) in rows("SELECT id::text FROM fact_sets")} >= {
        own["fact_set_id"],
        replayed_["fact_set_id"],
    }
    assert own["text"]["text"] not in str(logs) and expected not in str(logs)

    # The page: the item's text is its question, typed «adapted», no fact or weight sent.
    body = opened.json()
    shown = next(item for item in body["items"] if item["id"] == OWN)
    assert shown["type"] == "adapted" and shown["title"] == own["text"]["text"]
    assert shown["wording"] == own["text"]
    assert not {"fact_ids", "fact_set_id", "weight"} & set(shown)

    # Frozen: a second open changes nothing (a newer version: the test after the stand-ins).
    again = await call(me, "POST", path(session_id))
    assert (again.status_code, again.json()) == (200, body)
    assert attempts(session_id)[0][4] == items

    # Answered as a long answer (Story 11.6).
    text = "Jeg så på restordren og bestilte mer."
    saved = await call(me, "PUT", answer_url(session_id, OWN), json={"value": text, "revision": 1})
    assert (saved.status_code, saved.json()["value"]) == (200, text)
    refused = await call(me, "PUT", answer_url(session_id, OWN), json={"value": 3, "revision": 2})
    assert code(refused) == (422, "invalid_answer")
    read = (await call(me, "GET", path(session_id))).json()
    assert next(i for i in read["items"] if i["id"] == OWN)["answer"]["value"] == text


def stored_set(
    student_weeks: range, game_id: uuid.UUID, changes: dict | None = None
) -> games.StoredFactSet:
    """A stored facts set of the Detaljist from a hand-built Decision log of 12 Weeks: the Student
    ordered in `student_weeks`, with `changes` to single rows."""
    rows_ = student(student_weeks)
    for key, change in (changes or {}).items():
        rows_[key] = rows_.get(key, {}) | change
    built = facts(log(12, rows_), "retailer", PATTERNS)
    return games.StoredFactSet(
        id=str(uuid.uuid7()),
        game_id=str(game_id),
        seat_id=str(uuid.uuid7()),
        analysis_version=built.analysis_version,
        patterns_version=1,
        facts=built,
    )


def stand_in(
    monkeypatch,
    *,
    own: range | None,
    replay: bool = True,
    replay_facts: bool = True,
    changes: dict | None = None,
):
    """The Student's two Games stood in: `own` the Weeks of their own Orders (None: no game)."""
    game_id, replay_id = uuid.uuid7(), uuid.uuid7()
    sets = {game_id: stored_set(own or range(0), game_id, changes)}
    if replay_facts:
        sets[replay_id] = stored_set(range(1, 13), replay_id)

    async def sources(s, user, class_session_id):
        game = None if own is None else SimpleNamespace(game_id=game_id, role="retailer")
        return game, replay_id if replay else None

    async def fact_set(game, role):
        return sets.get(game)

    monkeypatch.setattr(adapted, "_sources", sources)
    monkeypatch.setattr(adapted, "_facts", fact_set)
    return sets


async def locked_with(
    klass: str, adapted_weight: int, n: int = 1, ai_mode: str = "rule_based"
) -> tuple[str, list]:
    """A locked Class session of `n` Students, all through the Replay, whose selection sets the
    Adapted total (`ai_mode` `llm` with the default model config: the Debrief AI text is on)."""
    session_id, seated = await confirmed(klass, n, ai_mode)
    url = f"/api/class-sessions/{session_id}/question-set"
    block = (await call(LECTURER, "GET", url)).json()
    weights = {item["id"]: item["weight"] for item in block["items"]}
    first = block["items"][-1]["id"]
    weights[first] += block["adapted"]["weight"] - adapted_weight
    saved = await call(
        LECTURER,
        "PUT",
        url,
        json={"weights": weights, "excluded": [], "adapted_weight": adapted_weight},
    )
    assert saved.status_code == 200, saved.text
    await sweep.run(START + MINUTE)
    for each in seated:
        await replayed(each, session_id)
    return session_id, seated


async def frozen(session_id: str, who: int = 0) -> list[dict]:
    """The items frozen on Student `who`'s attempt, opened (or opened again) now."""
    opened = await call(email(who), "POST", path(session_id))
    assert opened.status_code in (200, 201), opened.text
    [items] = [row[4] for row in attempts(session_id) if row[1] == user_id(email(who))]
    return items


async def test_an_odd_adapted_total_is_split_into_whole_weights(klass, monkeypatch):
    sets = stand_in(monkeypatch, own=range(1, 13))
    session_id, _ = await locked_with(klass, 25)
    items = await frozen(session_id)
    adapted_items = [item for item in items if item["type"] == "adapted"]
    assert [(i["id"], i["weight"]) for i in adapted_items] == [(OWN, 13), (REPLAY, 12)]
    assert sum(item["weight"] for item in items) == 100
    own_set = next(s for s in sets.values() if s.facts.seat.student_orders == 12)
    assert adapted_items[0]["fact_set_id"] == own_set.id
    assert not any(item["id"] in REPLACEMENTS for item in items)


@pytest.mark.parametrize(
    ("own", "replay", "replay_facts", "reason"),
    [
        (range(1, 10), True, True, "few_orders"),  # nine own Orders (AD-15's one count)
        (None, True, True, "no_game"),
        (range(1, 13), False, True, "no_replay"),
        (range(1, 13), True, False, "facts_unavailable"),
    ],
)
async def test_otherwise_the_replacement_items_carry_the_adapted_total(
    klass, monkeypatch, own, replay, replay_facts, reason
):
    stand_in(monkeypatch, own=own, replay=replay, replay_facts=replay_facts)
    session_id, _ = await locked_with(klass, 25)
    with capture_logs() as logs:
        items = await frozen(session_id)
    assert [(i["id"], i["weight"], i.get("replaces")) for i in items[-2:]] == [
        ("erstatning-tabell", 13, reason),
        ("erstatning-langsvar", 12, reason),
    ]
    assert not any(item["type"] == "adapted" for item in items)
    assert sum(item["weight"] for item in items) == 100
    assert [e["reason"] for e in logs if e["event"] == "adapted_items_replaced"] == [reason]
    # The replacement items are answered as the Core items they are.
    body = (await call(email(0), "GET", path(session_id))).json()
    long_ = next(i for i in body["items"] if i["id"] == "erstatning-langsvar")
    assert (long_["type"], long_["wording"]) == ("long", None)
    saved = await call(
        email(0),
        "PUT",
        answer_url(session_id, "erstatning-langsvar"),
        json={"value": "Svar.", "revision": 1},
    )
    assert saved.status_code == 200


async def test_a_first_open_builds_the_facts_sets_before_its_transaction(klass, monkeypatch):
    """Epic 11 close-out: a facts set not stored yet is built before the opening transaction
    (`adapted.warm`), so inside it `build` only reads; an attempt opened again builds nothing."""
    stand_in(monkeypatch, own=range(1, 13))
    calls: list[str] = []
    read, build = adapted._facts, adapted.build

    async def facts(game, role):
        calls.append("facts")
        return await read(game, role)

    async def building(*args):
        calls.append("build")
        return await build(*args)

    monkeypatch.setattr(adapted, "_facts", facts)
    monkeypatch.setattr(adapted, "build", building)
    session_id, _ = await locked_with(klass, 30)
    await frozen(session_id)
    assert calls[:3] == ["facts", "facts", "build"]
    calls.clear()
    await frozen(session_id)
    assert calls == []


async def test_an_adapted_total_of_0_serves_neither(klass, monkeypatch):
    stand_in(monkeypatch, own=range(1, 13))
    session_id, _ = await locked_with(klass, 0)
    items = await frozen(session_id)
    assert not any(item["type"] == "adapted" or "replaces" in item for item in items)
    assert sum(item["weight"] for item in items) == 100


async def test_the_lock_pins_the_template_version_and_an_opened_attempt_never_changes(
    klass, monkeypatch
):
    stand_in(monkeypatch, own=range(1, 13))
    session_id, _ = await locked_with(klass, 30, n=2)
    [(pin,)] = rows(
        "SELECT snapshot->'session_runtime'->'pins'->'adapted_templates' FROM class_sessions "
        "WHERE id = %s",
        session_id,
    )
    assert pin == {"version": TEMPLATES}
    _, templates = await content.adapted_templates(TEMPLATES)
    changed = templates.model_dump(mode="json")
    changed["templates"][0]["text"] = "Utkast: annen tekst om uke {week}, ordre {order}."
    changed["templates"][0]["wordings"] = []  # theirs use the old text's values (Story 11.8)
    newer = await content.publish("adapted_templates", changed)
    try:
        # A version published after the lock is not the one this Class session uses.
        items = await frozen(session_id)
        own = next(item for item in items if item["id"] == OWN)
        assert own["template_version"] == TEMPLATES
        assert own["text"]["text"].startswith("Utkast: I uke")
        # Without the pin the reader takes the newer version, as the second Student's open shows;
        # the first Student's items stay as frozen, even after their own game changes.
        execute(
            "UPDATE class_sessions SET snapshot = snapshot #- "
            "'{session_runtime,pins,adapted_templates}' WHERE id = %s",
            session_id,
        )
        other = next(item for item in await frozen(session_id, 1) if item["id"] == OWN)
        assert other["template_version"] == newer
        assert other["text"]["text"].startswith("Utkast: annen tekst")
        stand_in(monkeypatch, own=range(1, 10))
        assert await frozen(session_id) == items
    finally:
        unpublish(newer)


async def test_a_pattern_template_names_the_pattern_and_a_missing_fact_gives_the_replacements(
    klass, monkeypatch
):
    """Through `build`: the pattern's name comes from the Detected pattern version the facts set
    was built with; a template whose fact the set lacks makes every template give way."""
    surge = {(3, "retailer"): {"order": 12, "backlog": 1}, (4, "retailer"): {"backlog": 1}}
    stand_in(monkeypatch, own=range(1, 13), changes=surge)
    text = "Utkast: I uke {week} viste ordren på {order} enheter mønsteret «{pattern}»."
    pattern = {"id": "tilpasset-monster", "source": "game", "fact": "pattern", "share": 100}
    shown: list[int] = [1]

    async def templates(version):
        body = {"status": "draft", "templates": [{**pattern, "pick": shown[0], "text": text}]}
        return 1, AdaptedTemplates.model_validate(body)

    monkeypatch.setattr(content, "adapted_templates", templates)
    session_id, _ = await locked_with(klass, 30, n=2)
    _, patterns = await content.detected_patterns(1)
    name = next(p.name for p in patterns.patterns if p.id == "surge-after-shortage")
    [item] = [i for i in await frozen(session_id) if i["type"] == "adapted"]
    assert item["fact_ids"] == ["surge-after-shortage:retailer:3"] and item["weight"] == 30
    assert item["text"]["text"] == f"Utkast: I uke 3 viste ordren på 12 enheter mønsteret «{name}»."
    shown[0] = 3  # the Seat has one Student occurrence of a pattern, not three
    with capture_logs() as logs:
        items = await frozen(session_id, 1)
    assert [(i["id"], i.get("replaces")) for i in items[-2:]] == [
        ("erstatning-tabell", "unfilled"),
        ("erstatning-langsvar", "unfilled"),
    ]
    assert [e["reason"] for e in logs if e["event"] == "adapted_items_replaced"] == ["unfilled"]


async def test_the_shipped_file_is_the_latest_version_as_the_migration_stored_it():
    stored = (await content.get("adapted_templates", TEMPLATES)).model_dump(mode="json")
    path_ = Path(adapted.__file__).parents[1] / "content" / "files" / "adapted_templates.json"
    assert json.loads(path_.read_text(encoding="utf-8")) == stored
