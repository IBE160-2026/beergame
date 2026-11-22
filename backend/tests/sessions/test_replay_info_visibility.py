"""Information visibility of an own Replay scenario (Story 10.9, cut list, FR-83, FR-49, AD-4,
AD-17): the Replay's own setting, prefilled from the Class session, editable and warned about
while `FEATURE_INFO_VISIBILITY` is on; with the flag off nothing about it shows and a view
switched on is refused, while a stored one is kept. The api's clock is fixed; no Game is
played."""

from app.engine import GameSettings, ReplayTemplate
from app.engine.settings import InfoVisibility
from app.modules.sessions import service
from tests.classes.test_classes import LECTURER
from tests.classes.test_roster_upload import clock, klass
from tests.classes.test_staff import call
from tests.games.test_neighbour_numbers import flag as views_flag
from tests.sessions.test_dates import new_session, refusal
from tests.sessions.test_replay_own import BASE, CLASSIC, EXACT, OWN, _empty, own, save, stored
from tests.sessions.test_rerun import copy
from tests.sessions.test_rerun import flag as rerun_flag

__all__ = ["_empty", "clock", "klass"]

OFF = {"upstream": False, "downstream": False}
UP = {"upstream": True, "downstream": False}
BOTH = {"upstream": True, "downstream": True}


def visible(template: dict, settings: GameSettings = CLASSIC, *, enabled: bool = True) -> list:
    found = service.replay_warnings(
        ReplayTemplate.model_validate(template), settings, info_visibility_enabled=enabled
    )
    return [(w.code, w.field, w.values) for w in found]


# --- The warning rule in the one function of warned changes (pure). ---


def test_a_view_the_class_games_do_not_show_warns_per_view_only_with_the_flag_on():
    assert visible({**BASE, "info_visibility": UP}) == [
        ("replay_neighbour_visible", "info_visibility", {"view": "upstream"})
    ]
    assert [w[2] for w in visible({**BASE, "info_visibility": BOTH})] == [
        {"view": "upstream"},
        {"view": "downstream"},
    ]
    # The same view as the Class games, or fewer: nothing. The flag off: nothing (AD-17).
    upstream_class = CLASSIC.model_copy(update={"info_visibility": InfoVisibility(upstream=True)})
    assert visible({**BASE, "info_visibility": UP}, upstream_class) == []
    assert visible({**BASE, "info_visibility": OFF}, upstream_class) == []
    assert [w[2] for w in visible({**BASE, "info_visibility": BOTH}, upstream_class)] == [
        {"view": "downstream"}
    ]
    assert visible({**BASE, "info_visibility": BOTH}, enabled=False) == []


# --- Judging a draft (pure; the flag from the environment). ---


def test_with_the_flag_on_the_draft_sets_the_replays_own_views(monkeypatch):
    views_flag(monkeypatch, True)
    template, problems, risky = service.judge_replay_template(CLASSIC, own(info_visibility=UP))
    assert problems == {} and template.info_visibility == InfoVisibility(upstream=True)
    assert [w.code for w in risky] == ["replay_neighbour_visible"]
    # Left out: the Class session's; a stored own template's when kept.
    template, _, _ = service.judge_replay_template(CLASSIC, OWN | {"info_visibility": OFF})
    assert not template.info_visibility.on
    no_views = {k: v for k, v in OWN.items() if k != "info_visibility"}
    kept = InfoVisibility(downstream=True)
    template, _, _ = service.judge_replay_template(CLASSIC, no_views, kept_views=kept)
    assert template.info_visibility == kept
    for bad in ({"upstream": "yes"}, {"left": True}, 5):
        _, problems, _ = service.judge_replay_template(CLASSIC, own(info_visibility=bad))
        assert problems["info_visibility"].code == "invalid", bad


def test_with_the_flag_off_a_new_view_is_refused_and_a_kept_one_stays(monkeypatch):
    views_flag(monkeypatch, False)
    template, problems, risky = service.judge_replay_template(CLASSIC, own(info_visibility=UP))
    assert template is None and problems["info_visibility"].code == "feature_disabled"
    # A view stored while the flag was on: sent back or left out, kept; switched off, allowed.
    kept = InfoVisibility(upstream=True)
    for draft in (
        own(info_visibility=UP),
        {k: v for k, v in OWN.items() if k != "info_visibility"},
    ):
        template, problems, risky = service.judge_replay_template(CLASSIC, draft, kept_views=kept)
        assert problems == {} and template.info_visibility == kept
        assert risky == []  # nothing about it shows
    template, problems, _ = service.judge_replay_template(
        CLASSIC, own(info_visibility=OFF), kept_views=kept
    )
    assert problems == {} and not template.info_visibility.on


async def test_a_stored_own_view_survives_a_class_settings_change_and_is_pinned(monkeypatch):
    views_flag(monkeypatch, True)
    stored_own = ReplayTemplate.model_validate({**EXACT, **own(info_visibility=UP)})
    row = {"replay_scenario": "own", "replay_template": stored_own.model_dump(mode="json")}
    downstream = CLASSIC.model_copy(update={"info_visibility": InfoVisibility(downstream=True)})
    assert service._replay_to_store(row, downstream, "own", None, locked=False) is None
    views_flag(monkeypatch, False)
    assert service._replay_to_store(row, downstream, "own", None, locked=False) is None
    # The lock's pin provider freezes the Replay's own views (Story 10.1, AD-4).
    pinned = await service.replay_template_pin(None, row)
    assert pinned["info_visibility"] == UP


# --- Over the api: one Class session, the flag switched within the test. ---


async def test_the_replays_views_are_saved_warned_hidden_and_copied_by_the_flag(klass, monkeypatch):
    session_id = await new_session(klass)
    views_flag(monkeypatch, True)
    response = await save(session_id, "own", own(info_visibility=UP))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["info_visibility_enabled"] is True
    assert body["replay_template"]["info_visibility"] == UP
    assert body["game_settings"]["info_visibility"] == OFF  # the Class games keep theirs
    assert [(w["code"], w["values"]) for w in body["replay_warnings"]] == [
        ("replay_neighbour_visible", {"view": "upstream"})
    ]
    assert stored(session_id)[1]["info_visibility"] == UP
    # The check answers the same warning without storing.
    checked = await call(
        LECTURER,
        "POST",
        f"/api/class-sessions/{session_id}/replay-scenario-check",
        json={"replay_template": own(info_visibility=BOTH)},
    )
    assert [w["values"]["view"] for w in checked.json()["warnings"]] == ["upstream", "downstream"]

    # The flag off: no warning shows, a new view is refused, the stored one is kept.
    views_flag(monkeypatch, False)
    seen = (await call(LECTURER, "GET", f"/api/class-sessions/{session_id}")).json()
    assert seen["info_visibility_enabled"] is False and seen["replay_warnings"] == []
    refused = await save(session_id, "own", own(info_visibility=BOTH))
    status, code, fields = refusal(refused)
    assert (status, code, fields["info_visibility"]["code"]) == (
        422,
        "invalid_replay_scenario",
        "feature_disabled",
    )
    checked = await call(
        LECTURER,
        "POST",
        f"/api/class-sessions/{session_id}/replay-scenario-check",
        json={"replay_template": own(info_visibility=BOTH)},
    )
    assert checked.json()["errors"]["info_visibility"]["code"] == "feature_disabled"
    screen = {k: v for k, v in own(weeks=31).items() if k != "info_visibility"}
    assert (await save(session_id, "own", screen)).status_code == 200
    assert stored(session_id)[1]["info_visibility"] == UP

    # A copy (FEATURE_RERUN) leaves a view out while the flag is off, and takes it while on.
    rerun_flag(monkeypatch, True)
    copied = await copy(klass, session_id)
    assert copied.status_code == 201, copied.text
    assert copied.json()["replay_template"]["info_visibility"] == OFF
    views_flag(monkeypatch, True)
    copied = await copy(klass, session_id)
    assert copied.json()["replay_template"]["info_visibility"] == UP
