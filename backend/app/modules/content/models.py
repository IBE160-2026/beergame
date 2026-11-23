"""The tables owned by `modules/content` (Stories 6.3, 9.1, 9.4, 9.6, 9.7, 9.9, 9.14, 11.1,
11.2, 11.7, 12.10, AD-23, AD-27)."""

from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    PrimaryKeyConstraint,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB

from app.platform.db import metadata


class Kind(StrEnum):
    """The closed catalogue of content kinds. Later epics add theirs (quiz, question set …)."""

    STARTING_TASK = "starting_task"
    DETECTED_PATTERNS = "detected_patterns"
    SENTENCE_TEMPLATES = "sentence_templates"
    REFLECTION_QUESTIONS = "reflection_questions"
    MOMENT_TEMPLATES = "moment_templates"
    DEBRIEF_QUIZ = "debrief_quiz"
    NARRATION_TEMPLATES = "narration_templates"
    QUESTION_SET = "question_set"
    SCORING_GUIDE = "scoring_guide"
    ADAPTED_TEMPLATES = "adapted_templates"


content_records = Table(
    "content_records",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("kind", Text, nullable=False),
    Column("version", Integer, nullable=False),
    Column("body", JSONB, nullable=False),
    # Story 11.2: the Class session a Lecturer's edited Scoring guide was made for; NULL for a
    # published default. No foreign key: a copied Class session uses the same version (FR-66).
    Column("class_session_id", Uuid, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint(
        "kind IN (" + ", ".join(f"'{kind.value}'" for kind in Kind) + ")",
        name="ck_content_records_kind",
    ),
    CheckConstraint("version >= 1", name="ck_content_records_version"),
    UniqueConstraint("kind", "version", name="uq_content_records_kind_version"),
)
"""A trigger (migration 0046) refuses every UPDATE: a record never changes once stored. The
version numbers are one sequence per kind; a default is a record without `class_session_id`."""


scoring_guide_checks = Table(
    "scoring_guide_checks",
    metadata,
    Column(
        "scoring_guide_id",
        Uuid,
        ForeignKey("content_records.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    # No foreign key: only `app/ai` owns the model config table (AD-6).
    Column("model_config_id", Uuid, nullable=False),
    # No foreign key: the check outlives the Control test that made it.
    Column("control_test_id", Uuid, nullable=False),
    Column("checked_at", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint("scoring_guide_id", "model_config_id", name="pk_scoring_guide_checks"),
)
"""Story 12.10 (FR-81, AD-27): a Scoring guide version a Control test checked with a model config
(every named scorer scored every listed answer). Written once by `mark_checked` (the first check
of a pair stays) and read by `is_checked`; a trigger (migration 0209) refuses every UPDATE."""
