"""`games.policy(purpose)`: the one table of behaviour per Game purpose (AD-13).

Commands, sweeps and views ask this table and never compare a purpose themselves. A purpose
gets its row in the story that first creates such Games; until then asking for it fails.
"""

from collections.abc import Mapping
from types import MappingProxyType
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.modules.games.schemas import Purpose


class PurposeNotSupportedError(LookupError):
    """No behaviour is defined for this purpose yet."""


class GamePolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    inactivity_takeover: bool
    pause: bool
    play_deadline_playout: bool
    lecturer_overview: bool
    """Listed in the Lecturer overview, so its commands also emit `session:<id>` (AD-8)."""
    guided_weeks: Literal["settings"]
    """`settings`: Guided Weeks are the Game settings' `guided_weeks`."""
    scripted_occupants: bool
    """Whether a Seat may be held by a scripted policy (AD-22)."""
    snapshot: Literal["at_creation", "at_lock"]
    """When the Game takes its settings snapshot (AD-4): `at_creation`, from the settings
    `games.commands.create` is given; `at_lock`, from its Class session's lock (Story 5.12), so
    `create` takes no settings and `start` answers `game_not_ready` until the snapshot exists."""
    student_occupants: bool
    """Whether a Seat may be held by a Student (`student` occupant with a `user_id`, AD-5)."""
    class_session_game: bool
    """Whether the Game belongs to a Class session: created with its id and a game number."""
    records_class_game_step: bool
    """Whether `games.commands.finish` records the `progress` step `class_game` for every
    Student the Game ever seated (Story 6.18, AD-16)."""
    pre_play_gate: bool
    """Whether the rules briefing and the Starting task come before play (Stories 6.2, 6.3,
    6.5): the Student's start is refused until the `starting_task` step is done."""
    game_number: bool
    """Whether a Game of a Class session takes a game number there (Story 6.20). A Game without
    one belongs to the Class session (its budget, its staff) but is never one of its Class games."""
    played_by_staff: bool
    """Whether a Lecturer of the Class session plays it in a Student Seat (Story 6.20, FR-87): it
    is reached from the Klasseøkt, labelled «Testspill», and its end leads back there."""
    projection: bool
    """Whether the play screen draws the projection of net stock at nå + delay horizon (Story 10.3
    adds the column, Story 10.4 draws it, UX-DR19): only the Replay."""
    staff_insight: bool
    """Whether the staff of its Class open it on Spillinnsikt (Story 7.7, FR-62): every Game the
    Lecturer overview lists, and the Replay, which is no Class game but a Student's own round in
    the Class session (Story 10.5, FR-34). A Lecturer's test Game and a simulation never."""
    closes_at_test_deadline: bool
    """Whether an unfinished Game is closed, not played out, at its Students' Test deadline
    (`games.commands.close`, the sweep's `games.close_at_test_deadline`, Story 10.6, FR-18), and
    takes no Order after it (`409 test_deadline_passed`): only the Replay, which a playout would
    make no longer the Student's own (AD-13)."""
    believability: Literal["never", "ai_held", "always"]
    """When a Student of the finished Game is asked how believable the AI players' ordering felt
    (Story 10.8, FR-70): `ai_held`, when an AI player held some Seat in some Week; `always`, every
    Seat but the Student's is an AI player (the Replay, the Oppfølgingsspill); `never`, nobody is
    asked. A Game closed at the Test deadline is never asked."""
    own_round: Literal["none", "replay", "makeup"]
    """Whether a Game is a Student's own round in its Class session outside the Class games, and
    which: `replay` (Stories 10.4, 10.5) or `makeup`, the Oppfølgingsspill (Story 13.4). Such a
    Game is the Student's while they hold its Seat (`games.service.own_game`); nobody else plays
    it with them, so no time to play is agreed in it."""


POLICIES: Mapping[Purpose, GamePolicy] = MappingProxyType(
    {
        Purpose.SIMULATION: GamePolicy(
            inactivity_takeover=False,
            pause=False,
            play_deadline_playout=False,
            lecturer_overview=False,
            guided_weeks="settings",
            scripted_occupants=True,
            snapshot="at_creation",
            student_occupants=False,
            class_session_game=False,
            records_class_game_step=False,
            pre_play_gate=False,
            game_number=False,
            played_by_staff=False,
            projection=False,
            staff_insight=False,
            closes_at_test_deadline=False,
            believability="never",
            own_round="none",
        ),
        # A Class game (Story 5.9): created when the allocation is confirmed, its snapshot taken
        # at the Class session's lock.
        Purpose.CLASS: GamePolicy(
            inactivity_takeover=True,
            pause=True,
            play_deadline_playout=True,
            lecturer_overview=True,
            guided_weeks="settings",
            scripted_occupants=False,
            snapshot="at_lock",
            student_occupants=True,
            class_session_game=True,
            records_class_game_step=True,
            pre_play_gate=True,
            game_number=True,
            played_by_staff=False,
            projection=False,
            staff_insight=True,
            closes_at_test_deadline=False,
            believability="ai_held",
            own_round="none",
        ),
        # A Lecturer's private test Game (Story 6.20, FR-87): snapshot of its Class session's
        # current settings at creation, the Lecturer in one Seat and AI players in the others. It
        # belongs to the Class session (its budget) but is never one of its Class games: no number,
        # not in the Lecturer overview or any Class session list, no step recorded, no gate.
        Purpose.LECTURER_TEST: GamePolicy(
            inactivity_takeover=False,
            pause=False,
            play_deadline_playout=False,
            lecturer_overview=False,
            guided_weeks="settings",
            scripted_occupants=False,
            snapshot="at_creation",
            student_occupants=True,
            class_session_game=True,
            records_class_game_step=False,
            pre_play_gate=False,
            game_number=False,
            played_by_staff=True,
            projection=False,
            staff_insight=False,
            closes_at_test_deadline=False,
            believability="never",
            own_round="none",
        ),
        # A Student's Replay (Story 10.3, FR-48, AD-13): one round alone in the Class game's Role
        # against three AI players, on the Class session's frozen runtime with its own drawn
        # settings, snapshotted at creation. It belongs to the Class session (its budget) but is no
        # Class game: no number, not on the overview, no `class_game` step, no gate. Nobody waits on
        # the Student, so no Takeover, Pause or playout; Guided Weeks only where its settings say.
        Purpose.REPLAY: GamePolicy(
            inactivity_takeover=False,
            pause=False,
            play_deadline_playout=False,
            lecturer_overview=False,
            guided_weeks="settings",
            scripted_occupants=False,
            snapshot="at_creation",
            student_occupants=True,
            class_session_game=True,
            records_class_game_step=False,
            pre_play_gate=False,
            game_number=False,
            played_by_staff=False,
            projection=True,
            staff_insight=True,
            closes_at_test_deadline=True,
            believability="always",
            own_round="replay",
        ),
        # A Student's Oppfølgingsspill (Story 13.4, FR-17, FR-20, AD-13): a Lecturer gives it to
        # one Student; alone in their Class game's Role (or a drawn one) against three AI players,
        # on the Class session's frozen snapshot unchanged, snapshotted at creation. No number, not
        # on the overview wall, so no group result or Class session list counts it. Nobody waits on
        # the Student, so no Takeover, Pause or playout; it is closed, never played out, at the
        # Student's Test deadline. The Student passes the pre-play gate as in a Class game. Story
        # 13.5 turns on `records_class_game_step`.
        Purpose.MAKEUP: GamePolicy(
            inactivity_takeover=False,
            pause=False,
            play_deadline_playout=False,
            lecturer_overview=False,
            guided_weeks="settings",
            scripted_occupants=False,
            snapshot="at_creation",
            student_occupants=True,
            class_session_game=True,
            records_class_game_step=False,
            pre_play_gate=True,
            game_number=False,
            played_by_staff=False,
            projection=False,
            staff_insight=False,
            closes_at_test_deadline=True,
            believability="always",
            own_round="makeup",
        ),
    }
)


BoolColumn = Literal[
    "inactivity_takeover",
    "pause",
    "play_deadline_playout",
    "lecturer_overview",
    "scripted_occupants",
    "student_occupants",
    "class_session_game",
    "records_class_game_step",
    "pre_play_gate",
    "game_number",
    "played_by_staff",
    "projection",
    "staff_insight",
    "closes_at_test_deadline",
]


def purposes_with(column: BoolColumn) -> list[str]:
    """The purposes whose row has `column` on, for a SQL filter (`purpose IN (...)`), so no query
    names a purpose itself (AD-13). `lecturer_overview` is also the rule of every Class session
    list: a Game the overview does not list is in none of them (Story 6.20)."""
    return sorted(purpose.value for purpose, row in POLICIES.items() if getattr(row, column))


def policy(purpose: Purpose | str) -> GamePolicy:
    """What applies to Games of `purpose`; raises PurposeNotSupportedError for any other."""
    try:
        return POLICIES[Purpose(purpose)]
    except KeyError, ValueError:
        raise PurposeNotSupportedError(f"no Game policy for purpose {purpose!r}") from None
