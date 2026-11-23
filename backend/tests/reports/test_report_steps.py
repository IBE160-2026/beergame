"""Story 13.10 (FR-58, FR-47, FR-34, UJ-8 edge): the Student report's Debrief, Replay and
Individual test sections.

`report_data.build_report_data` is called directly, as the `reports-single` job calls it. Every
section is there whatever the Student did: a Student with no Orders, and one who sent an
Explanation but has no Replay and no test, get the sections marked not done, read from the
database through the owning modules' report reads. A Student with every step is built from those
reads stubbed with their own types: the composition, the AI flags and the sums. What each read
returns from stored rows is asserted beside the module's own tests (`debrief/test_explanation.py`:
no answer on feelings; `replay/test_walkthrough.py`; `reports/test_report_test_section.py`)."""

import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from app.engine import GameSettings
from app.modules.debrief import service as debrief
from app.modules.debrief.schemas import (
    ExplanationOut,
    RenderedTextOut,
    SummaryMomentOut,
)
from app.modules.replay import service as replay
from app.modules.replay.schemas import WalkthroughClassGameOut, WalkthroughWeekOut
from app.modules.reports import report_data
from app.modules.tests import service as tests
from app.modules.tests.schemas import (
    IndividualItemOut,
    StoredAnswerOut,
    TableColumnOut,
    TableOut,
    WordingOut,
)
from tests.classes.test_staff import call
from tests.debrief.test_debrief import open_
from tests.reports.test_report_game import built
from tests.sessions.test_game_end import WEEKS, _empty, clock, klass, play_weeks, short_game
from tests.sessions.test_open_games import confirmed
from tests.sessions.test_student_choice import email

__all__ = ["_empty", "clock", "klass"]

NOW = datetime(2026, 12, 1, 12, tzinfo=UTC)
KINDS = ["completion", "game", "debrief", "replay", "test"]


def sections(data: report_data.ReportDataOut) -> dict[str, object]:
    assert [section.kind for section in data.sections] == KINDS
    return {section.kind: section for section in data.sections}


async def test_a_student_with_no_orders_gets_every_step_section_marked_not_done(klass):
    session_id, (a,) = await confirmed(klass, 1)
    found = sections(await built(a, session_id))
    assert found["debrief"] == report_data.DebriefSectionOut(
        explanation=None,
        explanation_saved_at=None,
        finished_at=None,
        late=False,
        moments=[],
        narration=None,
        reflection=[],
        quiz_attempts=0,
        quiz_passed=False,
    )
    assert found["replay"] == report_data.ReplaySectionOut(replay=None)
    assert found["test"] == report_data.TestSectionOut(test=None)


async def test_an_explanation_without_a_replay_or_a_test_is_documented_as_written(klass):
    session_id, game_id, (a, _) = await short_game(klass)
    await play_weeks(game_id, WEEKS)
    opened = await open_(email(0), session_id)
    assert opened.status_code == 200, opened.text
    text = "Fabrikken svingte mest, fordi\nordrene kom sent."
    sent = await call(
        email(0), "POST", f"/api/debriefs/{opened.json()['id']}/explanation", json={"text": text}
    )
    assert sent.status_code == 201
    found = sections(await built(a, session_id))
    section = found["debrief"]
    assert isinstance(section, report_data.DebriefSectionOut)
    assert (section.explanation, section.finished_at, section.moments, section.quiz_attempts) == (
        text,
        None,
        [],
        0,
    )
    assert section.explanation_saved_at is not None
    assert found["replay"] == report_data.ReplaySectionOut(replay=None)
    assert found["test"] == report_data.TestSectionOut(test=None)


def _text(text: str, ai: bool = False) -> RenderedTextOut:
    return RenderedTextOut(text=text, ai_generated=ai)


def _weeks(*nets: int) -> list[WalkthroughWeekOut]:
    return [
        WalkthroughWeekOut(week=i, net_inventory=n, order=4, total_cost=Decimal(i))
        for i, n in enumerate(nets, start=1)
    ]


async def test_every_step_is_composed_with_ai_text_flagged_and_the_computed_scores_summed(
    klass, monkeypatch
):
    session_id, (a,) = await confirmed(klass, 1)
    saved = datetime(2026, 11, 20, 18, tzinfo=UTC)

    async def report_debrief(user_id, class_session_id):
        assert (user_id, class_session_id) == (a, uuid.UUID(session_id))
        return debrief.ReportDebrief(
            explanation=ExplanationOut(text="Min forklaring.", length=15, saved_at=saved),
            finished_at=saved,
            late=True,
            moments=[
                SummaryMomentOut(
                    id="moment:retailer:9",
                    week=9,
                    heading=_text("Uke 9: du bestilte 20."),
                    reckoning=_text("Posisjon 3."),
                    later=_text("Det kostet 54,00 kr."),
                    patterns=[_text("Stor ordre.")],
                )
            ],
            narration=_text("Øyeblikkene henger sammen.", ai=True),
            reflection=[("Hva viste tallene?", "Fabrikken svingte mest.")],
            quiz_attempts=2,
            quiz_passed=True,
        )

    async def report_replay(user_id, class_session_id):
        return replay.ReplayReport(
            state="finished",
            role="wholesaler",
            settings=GameSettings(
                weeks=3,
                guided_weeks=0,
                starting_inventory=9,
                starting_backlog=2,
                order_delay=1,
                shipping_delay=3,
                production_delay=2,
                holding_cost=Decimal("0.25"),
                backorder_cost=Decimal("2.00"),
            ),
            replay=replay.WalkthroughRunOut(weeks=_weeks(4, -2, 1), total_cost=Decimal(3)),
            class_game=WalkthroughClassGameOut(
                weeks=_weeks(0, 5), total_cost=Decimal(2), game_number=17
            ),
            mostly_ai=False,
        )

    table = TableOut(
        prompt="Fyll inn lageret.",
        hint=None,
        caption="Lager per uke",
        rows=["Uke 1", "Uke 2"],
        columns=[TableColumnOut(label="Inn", values=[20, 20])],
        asked_label="Lager",
        negative=False,
    )

    def item(number, kind, title, points, weight, answer=None, wording=None, table=None):
        return tests.ReportItem(
            item=IndividualItemOut(
                id=f"item-{number}",
                number=number,
                type=kind,
                title=title,
                options=["a", "b"] if kind == "choice" else [],
                table=table,
                column=None,
                wording=wording,
                answer=None
                if answer is None
                else StoredAnswerOut(value=answer, revision=1, saved_at=saved),
            ),
            weight=weight,
            points=points,
        )

    async def report_test(user_id, class_session_id):
        return tests.ReportTest(
            state="submitted",
            submitted_at=saved,
            items=[
                item(1, "choice", "Hvorfor?", Decimal("10.00"), 10, answer="b"),
                item(2, "table", "Tabell", Decimal("7.50"), 15, answer=[18, None], table=table),
                item(3, "long", "Forklar.", None, 30, answer="Et svar."),
                item(
                    4,
                    "adapted",
                    "Uke 9 i spillet ditt.",
                    None,
                    20,
                    wording=WordingOut(
                        text="Uke 9 i spillet ditt.", ai_generated=True, llm_call_id="x"
                    ),
                ),
            ],
        )

    monkeypatch.setattr(report_data.debrief, "report_debrief", report_debrief)
    monkeypatch.setattr(report_data.replay, "report_replay", report_replay)
    monkeypatch.setattr(report_data.tests, "report_test", report_test)

    data = await built(a, session_id)
    found = sections(data)
    section = found["debrief"]
    assert isinstance(section, report_data.DebriefSectionOut)
    assert (section.explanation, section.late, section.quiz_attempts, section.quiz_passed) == (
        "Min forklaring.",
        True,
        2,
        True,
    )
    assert section.narration == report_data.ReportTextOut(
        text="Øyeblikkene henger sammen.", ai_generated=True
    )
    assert [m.heading.text for m in section.moments] == ["Uke 9: du bestilte 20."]
    assert not section.moments[0].heading.ai_generated
    assert section.reflection == [
        report_data.ReportReflectionOut(prompt="Hva viste tallene?", text="Fabrikken svingte mest.")
    ]

    played = found["replay"]
    assert isinstance(played, report_data.ReplaySectionOut) and played.replay is not None
    assert (played.replay.state, played.replay.role, played.replay.class_game_number) == (
        "finished",
        "wholesaler",
        17,
    )
    assert played.replay.scenario == report_data.ReportScenarioOut(
        weeks=3,
        guided_weeks=0,
        starting_inventory=9,
        starting_backlog=2,
        order_delay=1,
        shipping_delay=3,
        production_delay=2,
        holding_cost=Decimal("0.25"),
        backorder_cost=Decimal("2.00"),
    )
    assert [
        (w.week, w.net_inventory, w.order, w.total_cost) for w in played.replay.replay.weeks
    ] == [(1, 4, 4, Decimal(1)), (2, -2, 4, Decimal(2)), (3, 1, 4, Decimal(3))]
    assert played.replay.replay.total_cost == Decimal(3)
    assert played.replay.class_game is not None
    assert played.replay.class_game.total_cost == Decimal(2)

    test = found["test"]
    assert isinstance(test, report_data.TestSectionOut) and test.test is not None
    assert (test.test.points, test.test.points_of) == (Decimal("17.50"), 25)
    by_number = {each.number: each for each in test.test.items}
    assert by_number[2].answer == [18, None] and by_number[2].table == table
    assert by_number[4].title == report_data.ReportTextOut(
        text="Uke 9 i spillet ditt.", ai_generated=True
    )
    assert (by_number[3].points, by_number[4].points) == (None, None)
    # No LLM call id, id or criterion reaches what the print route reads.
    dumped = json.dumps(data.model_dump(mode="json"), ensure_ascii=False)
    for word in ("llm_call_id", "item-1", "criteria", str(a)):
        assert word not in dumped
