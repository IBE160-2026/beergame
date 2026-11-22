"""Tables owned by `modules/ops` (Story 15.4, FR-71, AD-12, AD-14)."""

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    Table,
    Text,
    Uuid,
)

from app.platform.db import metadata

AGREEMENT_TEXT_MAX = 200
"""The longest «Hvem ga avtalen» and «Behandlingsansvarlig», in characters."""

evaluation_agreements = Table(
    "evaluation_agreements",
    metadata,
    Column(
        "class_session_id",
        Uuid,
        ForeignKey("class_sessions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    # Who at the Institution agreed, and who is controller for the evaluation (FR-71): the
    # Admin's text, as the agreement names them.
    Column("agreed_by", Text, nullable=False),
    Column("agreed_on", Date, nullable=False),
    Column("controller", Text, nullable=False),
    # The Admin who recorded it: the id only (AD-14).
    Column("recorded_by", Uuid, nullable=True),
    Column("recorded_at", DateTime(timezone=True), nullable=False),
    CheckConstraint(
        "btrim(agreed_by) <> '' AND btrim(controller) <> ''",
        name="ck_evaluation_agreements_text",
    ),
)
"""One Institution agreement per Class session; only with one may the Admin export it
(`platform/authz`, `export_pseudonymised`). Recording it again replaces it; each recording is
audited."""

pseudonym_key_fingerprints = Table(
    "pseudonym_key_fingerprints",
    metadata,
    Column("id", SmallInteger, primary_key=True),
    Column("fingerprint", Text, nullable=False),
    Column("set_by", Uuid, nullable=True),
    Column("set_at", DateTime(timezone=True), nullable=False),
    CheckConstraint("id = 1", name="ck_pseudonym_key_fingerprints_one_row"),
    CheckConstraint("fingerprint ~ '^[0-9a-f]{64}$'", name="ck_pseudonym_key_fingerprints_hex"),
)
"""At most one row: the fingerprint of the pseudonym key (AD-14). The key itself is never
stored."""

ERROR_SOURCES = ("conservation_check", "job_failed", "api_error")
"""Where a counted error comes from (Story 15.8, NFR-8): the finished-game check found a
violation, a job failed for good, or the api answered 5xx."""

error_events = Table(
    "error_events",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("source", Text, nullable=False),
    # A fixed technical value: `game_check_failed`, a task name, `http_500`. Never free text.
    Column("code", Text, nullable=False),
    # The Class session when one is known. No foreign key: a row is counted even for a session id
    # read from a request path, and the rows are kept at retention (AD-14).
    Column("class_session_id", Uuid, nullable=True),
    # The request id of an api error, the job id of a failed job.
    Column("request_id", Text, nullable=True),
    # The writer's clock, so the hour buckets and their window use one clock.
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    CheckConstraint(
        f"source IN ({', '.join(repr(s) for s in ERROR_SOURCES)})", name="ck_error_events_source"
    ),
    CheckConstraint("code ~ '^[a-z0-9_.:-]{1,80}$'", name="ck_error_events_code"),
    CheckConstraint(
        "request_id IS NULL OR length(request_id) <= 64", name="ck_error_events_request_id"
    ),
    Index("ix_error_events_session_time", "class_session_id", "occurred_at"),
)
"""Per-session error counts (Story 15.8, NFR-8, AD-14): written only by
`ops.service.record_error`; ids and codes only, kept at retention."""
