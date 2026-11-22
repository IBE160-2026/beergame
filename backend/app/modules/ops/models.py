"""Tables owned by `modules/ops` (Story 15.4, FR-71, AD-12, AD-14)."""

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
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
