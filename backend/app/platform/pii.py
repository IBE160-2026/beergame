"""The personal-data terms the AI gateway scrubs from free text (AD-6, C-1).

`terms(scope)` is called by the gateway only. For a Class session it will be a read-only query
over the `identity` tables (the Roster's names, emails and student numbers); that query is added
by the first epic that sends Students' free text to a model, since no `identity` table exists
yet. An evaluation scope (simulation runs, the Control test) has no Roster: its list is empty.
"""

import uuid
from typing import Protocol


class Scope(Protocol):
    @property
    def kind(self) -> str: ...

    @property
    def id(self) -> uuid.UUID: ...


def terms(scope: Scope) -> list[str]:
    """The terms to scrub for `scope`; empty for an evaluation scope."""
    if scope.kind == "evaluation":
        return []
    return []  # Class sessions: no identity tables yet (see the module docstring).
