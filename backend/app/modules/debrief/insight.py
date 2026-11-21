"""The Debrief's links on Spillinnsikt (Story 9.8, FR-47, FR-62, AD-12).

`links(session, game_id)` offers, for each Seat a Student holds, a link to that Student's
Explanation and one to their Debrief summary, both on the staff page
`/klasseokter/<session>/studenter/<student>/debrief`. The provider is registered with
`games.service.register_insight_links` (Story 7.7), so `games` imports nothing from `debrief`;
the page reads through `debrief.service.staff_summary`, which refuses every caller who is not
the Class's staff. Ids and Roles only, never a name (AD-14).

Story 7.7 is built on another branch: until it is merged, `games.service` has no
`register_insight_links` and nothing is registered here (`register()` returns False)."""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.games import service as games

__all__ = ["DebriefLink", "links", "register", "summary_path"]

EXPLANATION = "explanation"
SUMMARY = "debrief_summary"


@dataclass(frozen=True)
class DebriefLink:
    """The shape of `games.service.InsightLink` (Story 7.7): `kind` names the link, the page
    words it; `href` is the web app's path."""

    role: str
    kind: str
    href: str


def summary_path(class_session_id: object, student_id: object) -> str:
    """The staff page of a Student's Explanation and Debrief summary in the web app."""
    return f"/klasseokter/{class_session_id}/studenter/{student_id}/debrief"


async def links(session: AsyncSession, game_id: uuid.UUID) -> Sequence[DebriefLink]:
    """The Explanation and Debrief summary links of every Student-held Seat of the Game; none for
    a Game outside a Class session. `session` is the caller's; the Game is read through
    `games.service`."""
    found = await games.get_game(str(game_id))
    if found is None or found.class_session_id is None:
        return []
    offered = []
    for seat in found.seats:
        if seat.user_id is None:
            continue
        path = summary_path(found.class_session_id, seat.user_id)
        offered.append(DebriefLink(role=seat.role, kind=EXPLANATION, href=f"{path}#forklaring"))
        offered.append(DebriefLink(role=seat.role, kind=SUMMARY, href=path))
    return offered


def register() -> bool:
    """Registers `links` with Spillinnsikt when `games.service` offers the hook (Story 7.7);
    False while it does not. The one place the Debrief checks for Story 7.7."""
    # TODO(merge epic-7): register unconditionally
    hook = getattr(games, "register_insight_links", None)
    if hook is None:
        return False
    hook(links)
    return True


register()
