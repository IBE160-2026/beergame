"""The tables owned by `modules/progress` (Story 6.1, Story 13.3, AD-15, AD-16)."""

from enum import StrEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
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


CORRECTABLE_STEPS: tuple[str, ...] = (
    Step.CLASS_GAME.value,
    Step.DEBRIEF.value,
    Step.QUIZ_PASSED.value,
    Step.REPLAY.value,
    Step.TEST_SUBMITTED.value,
)
"""The steps of the requirement a Lecturer can correct (FR-17): `analysis.completion`'s
`COMPLETION_STEPS`, in order."""

completion_corrections = Table(
    "completion_corrections",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column(
        "class_session_id",
        Uuid,
        ForeignKey("class_sessions.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("step", Text, nullable=False),
    Column("done", Boolean, nullable=False),
    # The Lecturer's reason: free text about the Student, personal data (AD-14).
    Column("reason", Text, nullable=False),
    Column("actor_user_id", Uuid, ForeignKey("users.id", ondelete="SET NULL")),
    Column("at", DateTime(timezone=True), nullable=False),
    CheckConstraint(
        "step IN (" + ", ".join(f"'{step}'" for step in CORRECTABLE_STEPS) + ")",
        name="ck_completion_corrections_step",
    ),
    CheckConstraint(
        "char_length(btrim(reason)) BETWEEN 1 AND 1000",
        name="ck_completion_corrections_reason",
    ),
    Index("ix_completion_corrections_student", "class_session_id", "user_id"),
)
"""A Lecturer's corrections of a Student's Completion status (Story 13.3, AD-15): append-only
(migration 0301 refuses UPDATE but the actor set to NULL); the latest per step applies."""
