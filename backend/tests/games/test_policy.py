import pytest

from app.modules.games import service
from app.modules.games.policy import POLICIES, PurposeNotSupportedError
from app.modules.games.schemas import Purpose


@pytest.mark.parametrize("purpose", ["simulation", Purpose.SIMULATION])
def test_simulation_has_no_takeover_pause_playout_or_overview(purpose):
    rules = service.policy(purpose)
    assert rules.inactivity_takeover is False
    assert rules.pause is False
    assert rules.play_deadline_playout is False
    assert rules.lecturer_overview is False
    assert rules.guided_weeks == "settings"
    assert rules.scripted_occupants is True


def test_simulation_and_class_have_a_row_so_far():
    assert set(POLICIES) == {Purpose.SIMULATION, Purpose.CLASS}


def test_simulation_takes_its_snapshot_at_creation_and_seats_no_student():
    rules = service.policy("simulation")
    assert (rules.snapshot, rules.student_occupants, rules.class_session_game) == (
        "at_creation",
        False,
        False,
    )


def test_a_class_game_has_every_lecturer_behaviour_and_its_snapshot_at_the_lock():
    """AD-13: the `class` row (Story 5.9)."""
    rules = service.policy("class")
    assert rules.inactivity_takeover and rules.pause and rules.play_deadline_playout
    assert rules.lecturer_overview and rules.guided_weeks == "settings"
    assert rules.scripted_occupants is False
    assert (rules.snapshot, rules.student_occupants, rules.class_session_game) == (
        "at_lock",
        True,
        True,
    )


@pytest.mark.parametrize("purpose", ["replay", "makeup", "lecturer_test", "other"])
def test_other_purposes_raise(purpose):
    with pytest.raises(PurposeNotSupportedError):
        service.policy(purpose)
