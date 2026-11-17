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


def test_only_simulation_has_a_row_so_far():
    assert set(POLICIES) == {Purpose.SIMULATION}


@pytest.mark.parametrize("purpose", ["class", "replay", "makeup", "lecturer_test", "other"])
def test_other_purposes_raise(purpose):
    with pytest.raises(PurposeNotSupportedError):
        service.policy(purpose)
