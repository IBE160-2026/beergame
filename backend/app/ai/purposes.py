"""The purposes an LLM call can have (AD-6).

A purpose names the prompt (`prompts/<purpose>/v<N>.md`, version from the model config) and
fixes how many attempts one call may make. Player purposes may not spend a budget's reserve and
stop when the budget's cost-limit state is set (FR-69); other purposes (the Debrief and the AI
assessment, later epics) may.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Purpose:
    name: str
    attempt_limit: int
    player: bool


PURPOSES: dict[str, Purpose] = {
    # At most 6 attempts for one player Order (FR-32).
    "player_order": Purpose("player_order", attempt_limit=6, player=True),
}


def get(name: str) -> Purpose | None:
    return PURPOSES.get(name)
