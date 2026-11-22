"""The tables owned by `modules/assessment` (Epic 12).

Story 12.1 (FR-61, AD-9): `assessment_switches` holds the «KI-vurdering» switch of a Class
session, one row per session that was ever saved with it or pinned; no row reads as on. The
Test-deadline lock pins it (`pinned_at`), and a trigger then refuses any update of the row, so
the value an assessment reads never moves. A delete is not refused: the Class session's cascade
removes the row with it.

Story 12.2 (FR-54, AD-6, AD-9, AD-23): the lock pins the model config (and Effort level) the
assessment uses on the same row; `ai_assessments` holds one assessment per Test attempt and
`ai_item_scores` the overall score of each long-answer and Adapted item, written once, each with
the pinned versions and the id of the call it came from (`llm_call_id`). The total is never
stored: it comes from `analysis.total_score` when read.

Story 12.3 (FR-54, AD-7): an item's written feedback, or the note that it was left out, on its
`ai_item_scores` row (migration 0203).

Story 12.4 (FR-54, FR-61, FR-69, AD-9): the stop mark of a Class session's assessment
(`stopped_at`, `stopped_by`) on its switch row, which the pin trigger lets change; on an
assessment the attempt's `effective_deadline` (`due_at`), from which the sweep counts the 24-hour
target, and when it was logged as overdue (`overdue_at`) (migration 0204)."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    PrimaryKeyConstraint,
    SmallInteger,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
    true,
)
from sqlalchemy.dialects.postgresql import JSONB

from app.platform.db import metadata

assessment_switches = Table(
    "assessment_switches",
    metadata,
    Column(
        "class_session_id",
        Uuid,
        ForeignKey("class_sessions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("enabled", Boolean, nullable=False, server_default=true()),
    # Set once by `sessions.lock_test` at the original Test deadline; NULL until then.
    Column("pinned_at", DateTime(timezone=True), nullable=True),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    # Story 12.2: the model config the lock pinned with the switch; NULL when none could be.
    Column("model_config_id", Uuid, nullable=True),
    Column("effort_level", Text, nullable=True),
    # Story 12.4: `stop_for_session` sets these, `resume_for_session` clears them; they may
    # change after the pin, the pinned columns never.
    Column("stopped_at", DateTime(timezone=True), nullable=True),
    Column("stopped_by", Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
)

ai_assessments = Table(
    "ai_assessments",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("attempt_id", Uuid, ForeignKey("test_attempts.id", ondelete="CASCADE"), nullable=False),
    Column(
        "class_session_id",
        Uuid,
        ForeignKey("class_sessions.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    # `incomplete` while an item lacks a score, `ready` once every item has one, `failed` after
    # the last allowed job run (or with no pinned model config).
    Column("status", Text, nullable=False),
    Column("runs", Integer, nullable=False, server_default="0"),
    Column("scoring_guide_id", Uuid, nullable=True),
    Column("question_set_version", Integer, nullable=False),
    Column("model_config_id", Uuid, nullable=True),
    # Why it failed, a code: `no_model_config` or `runs_exhausted`.
    Column("reason", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("ready_at", DateTime(timezone=True), nullable=True),
    # Story 12.4: the attempt's `effective_deadline` (set by 0204 for the rows made before it),
    # and when the sweep logged the assessment as overdue, once.
    Column("due_at", DateTime(timezone=True), nullable=True),
    Column("overdue_at", DateTime(timezone=True), nullable=True),
    UniqueConstraint("attempt_id", name="uq_ai_assessments_attempt"),
    CheckConstraint("status IN ('incomplete', 'ready', 'failed')", name="ck_ai_assessments_status"),
    CheckConstraint("runs >= 0", name="ck_ai_assessments_runs"),
    Index("ix_ai_assessments_class_session", "class_session_id"),
    Index("ix_ai_assessments_user", "user_id"),
    Index(
        "ix_ai_assessments_unsettled",
        "due_at",
        postgresql_where=text("status = 'incomplete'"),
    ),
)

ai_item_scores = Table(
    "ai_item_scores",
    metadata,
    Column(
        "assessment_id",
        Uuid,
        ForeignKey("ai_assessments.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("item_id", Text, nullable=False),
    # One overall score on the Scoring guide's five-step scale, never per criterion (FR-81).
    Column("score", SmallInteger, nullable=False),
    # `ai`: from the call `llm_call_id` names; `blank`: an empty answer, step 0 by code.
    Column("source", Text, nullable=False),
    Column("llm_call_id", Uuid, nullable=True),
    Column("scoring_guide_id", Uuid, nullable=True),
    Column("question_set_version", Integer, nullable=False),
    Column("model_config_id", Uuid, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    # Story 12.3: the written feedback as it travels (`{text, ai_generated, llm_call_id, parts}`),
    # or `feedback_note = 'dropped'` when it was rejected twice; both NULL for a score-only prompt
    # and for an empty answer.
    Column("feedback", JSONB(none_as_null=True), nullable=True),
    Column("feedback_note", Text, nullable=True),
    PrimaryKeyConstraint("assessment_id", "item_id", name="pk_ai_item_scores"),
    CheckConstraint("score BETWEEN 0 AND 4", name="ck_ai_item_scores_score"),
    CheckConstraint("source IN ('ai', 'blank')", name="ck_ai_item_scores_source"),
    CheckConstraint("(source = 'ai') = (llm_call_id IS NOT NULL)", name="ck_ai_item_scores_call"),
    CheckConstraint(
        "feedback_note IS NULL OR feedback_note = 'dropped'",
        name="ck_ai_item_scores_feedback_note",
    ),
    CheckConstraint(
        "source = 'ai' OR (feedback IS NULL AND feedback_note IS NULL)",
        name="ck_ai_item_scores_feedback",
    ),
    CheckConstraint(
        "feedback IS NULL OR feedback_note IS NULL", name="ck_ai_item_scores_feedback_one"
    ),
)
