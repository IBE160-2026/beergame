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
    # `python -m app.sim probe`: does a model recognise the exercise (FR-31, issue #19)? An
    # evaluation tool, not a player: it places no Order.
    "recognition_probe": Purpose("recognition_probe", attempt_limit=3, player=False),
    # Story 9.14 (AD-7): the Debrief's narration and the Debrief quiz's own-game line. One attempt:
    # the caller never retries and shows the code text instead (`app.ai.text.worded`).
    "debrief_narration": Purpose("debrief_narration", attempt_limit=1, player=False),
    "quiz_explanation": Purpose("quiz_explanation", attempt_limit=1, player=False),
}


def get(name: str) -> Purpose | None:
    return PURPOSES.get(name)
