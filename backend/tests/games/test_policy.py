import pytest

from app.modules.games import service
from app.modules.games.policy import POLICIES, PurposeNotSupportedError, policy, purposes_with
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


def test_simulation_class_lecturer_test_and_replay_have_a_row_so_far():
    assert set(POLICIES) == {
        Purpose.SIMULATION,
        Purpose.CLASS,
        Purpose.LECTURER_TEST,
        Purpose.REPLAY,
    }


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


@pytest.mark.parametrize("purpose", ["makeup", "other"])
def test_other_purposes_raise(purpose):
    with pytest.raises(PurposeNotSupportedError):
        service.policy(purpose)


def test_only_a_class_game_records_its_step_and_has_the_pre_play_gate():
    """AD-13 (Story 6.18): `finish` records `class_game` and the briefing and Starting task come
    first only where these columns are on."""
    assert (
        service.policy("class").records_class_game_step,
        service.policy("class").pre_play_gate,
    ) == (
        True,
        True,
    )
    simulation = service.policy("simulation")
    assert (simulation.records_class_game_step, simulation.pre_play_gate) == (False, False)


def test_the_lecturer_test_row_is_a_snapshot_at_creation_with_no_lecturer_behaviour():
    """AD-13: the `lecturer_test` row, and the lists' filter that leaves it out."""
    rules = policy("lecturer_test")
    assert (rules.snapshot, rules.student_occupants, rules.class_session_game) == (
        "at_creation",
        True,
        True,
    )
    assert not any(
        (
            rules.inactivity_takeover,
            rules.pause,
            rules.play_deadline_playout,
            rules.lecturer_overview,
            rules.records_class_game_step,
            rules.pre_play_gate,
            rules.game_number,
            rules.scripted_occupants,
        )
    )
    assert rules.guided_weeks == "settings" and rules.played_by_staff
    assert purposes_with("lecturer_overview") == ["class"]
    assert purposes_with("played_by_staff") == ["lecturer_test"]


def test_the_replay_row_snapshots_at_creation_and_only_it_has_the_projection():
    """AD-13 (Story 10.3): the `replay` row. Nobody waits on a Replay, so the Takeover, Pause and
    playout filters (`purposes_with`, which the sweep's finders use) leave it out."""
    rules = policy("replay")
    assert (rules.snapshot, rules.student_occupants, rules.class_session_game) == (
        "at_creation",
        True,
        True,
    )
    assert not any(
        (
            rules.inactivity_takeover,
            rules.pause,
            rules.play_deadline_playout,
            rules.lecturer_overview,
            rules.records_class_game_step,
            rules.pre_play_gate,
            rules.game_number,
            rules.scripted_occupants,
            rules.played_by_staff,
        )
    )
    assert rules.guided_weeks == "settings"
    assert purposes_with("projection") == ["replay"]
    for column in ("inactivity_takeover", "pause", "play_deadline_playout", "lecturer_overview"):
        assert "replay" not in purposes_with(column)  # type: ignore[arg-type]


def test_staff_open_class_games_and_replays_on_spillinnsikt_and_nothing_else():
    """Story 10.5 (FR-34, AD-13): the Replay is no Class game, yet its Class's staff open it on
    Spillinnsikt; a Lecturer's test Game and a simulation never."""
    assert purposes_with("staff_insight") == ["class", "replay"]
    assert set(purposes_with("lecturer_overview")) <= set(purposes_with("staff_insight"))


def test_only_the_replay_is_closed_at_the_test_deadline_and_never_played_out():
    """Story 10.6 (FR-18, AD-13): an unfinished Replay is closed at the Test deadline, not played
    out, since a played-out Replay would not be the Student's own; a Class game is played out."""
    assert purposes_with("closes_at_test_deadline") == ["replay"]
    assert not set(purposes_with("closes_at_test_deadline")) & set(
        purposes_with("play_deadline_playout")
    )
