"""The table owned by `modules/progress` (Story 6.1, AD-16)."""

from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
)

from app.platform.db import metadata


class Step(StrEnum):
    """The closed catalogue of steps a Student can do in a Class session (AD-16)."""

    STARTING_TASK = "starting_task"
    CLASS_GAME = "class_game"
    EXPLANATION = "explanation"
    DEBRIEF = "debrief"
    QUIZ_PASSED = "quiz_passed"
    REPLAY = "replay"
    TEST_SUBMITTED = "test_submitted"
    ASSESSMENT_READY = "assessment_ready"


progress_steps = Table(
    "progress_steps",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column(
        "class_session_id",
        Uuid,
        ForeignKey("class_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    Column("step", Text, nullable=False),
    # When the step was done, as the recording module says (not the insert time).
    Column("at", DateTime(timezone=True), nullable=False),
    CheckConstraint(
        "step IN (" + ", ".join(f"'{step.value}'" for step in Step) + ")",
        name="ck_progress_steps_step",
    ),
    UniqueConstraint("user_id", "class_session_id", "step", name="uq_progress_steps_step"),
)
