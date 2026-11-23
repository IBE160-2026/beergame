"""Tables owned by `modules/identity` (AD-14, AD-24). Names and e-mails live only here."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Table,
    Text,
    Uuid,
    func,
    text,
    true,
)
from sqlalchemy.dialects.postgresql import JSONB

from app.modules.identity.schemas import AccountRole, InvitationKind, RosterRegistration
from app.platform.db import metadata

users = Table(
    "users",
    metadata,
    Column("id", Uuid, primary_key=True),
    # Stored trimmed and lower-cased, so the unique constraint is case-insensitive.
    Column("email", Text, nullable=False, unique=True),
    Column("name", Text, nullable=False),
    # NULL until a manually registered Student sets the first password (Story 4.8): such an
    # account cannot log in.
    Column("password_hash", Text, nullable=True),
    Column("is_active", Boolean, nullable=False, server_default=true()),
    # Raised by a deactivation and a password reset: every session issued before then ends
    # (Story 3.10, `auth.read_session`).
    Column("session_version", Integer, nullable=False, server_default=text("0")),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    # A test student (Story 12.8, AD-27): set when the User is created from a Control test's
    # Roster, never changed after. Written and read through `service` only.
    Column("is_test_student", Boolean, nullable=False, server_default=text("false")),
    CheckConstraint("email = lower(btrim(email))", name="ck_users_email_normalised"),
)
"""One row per account; exactly one User per e-mail (FR-4)."""

test_student_consents = Table(
    "test_student_consents",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("decision", Text, nullable=False),
    # The version of the consent text the test student read (`service.CONSENT_TEXT_VERSION`).
    Column("text_version", Text, nullable=False),
    Column("decided_at", DateTime(timezone=True), nullable=False),
    CheckConstraint("decision IN ('given', 'declined')", name="ck_test_student_consents_decision"),
    CheckConstraint("text_version <> ''", name="ck_test_student_consents_text_version"),
)
"""One row per decision a test student takes on Hjem (Story 12.8, FR-82, AD-27): `given` or
`declined`, the text version they read and the time (the api's clock). The newest row of the
current text version is the User's decision. Personal data; deleted with the User."""

user_roles = Table(
    "user_roles",
    metadata,
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role", Text, primary_key=True),
    Column("granted_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint(
        f"role IN ({', '.join(repr(role.value) for role in AccountRole)})",
        name="ck_user_roles_role",
    ),
)
"""The account roles a User holds (FR-1, FR-2). Students are not an account role: Class
membership makes a Student (Epic 4)."""

password_resets = Table(
    "password_resets",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
    # SHA-256 of the link token; the token itself is never stored (AD-11, `auth.link_token`).
    Column("token_hash", Text, nullable=False, unique=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("used_at", DateTime(timezone=True), nullable=True),
    Column("voided_at", DateTime(timezone=True), nullable=True),
)
"""One row per password-reset link (Story 3.6, FR-4). A link works once, until `expires_at`;
using one voids the User's other open links. Times come from the api's clock."""

invitations = Table(
    "invitations",
    metadata,
    Column("id", Uuid, primary_key=True),
    # Stored trimmed and lower-cased, as `users.email`.
    Column("email", Text, nullable=False, index=True),
    # The account role a `role` Invitation offers; NULL for every other kind (Story 4.4).
    Column("role", Text, nullable=True),
    # SHA-256 of the link token; the token itself is never stored (AD-11, `auth.link_token`).
    Column("token_hash", Text, nullable=False, unique=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("accepted_at", DateTime(timezone=True), nullable=True),
    Column("voided_at", DateTime(timezone=True), nullable=True),
    # When the holder of the expired or voided link asked for a new one (Story 3.8).
    Column("renewal_requested_at", DateTime(timezone=True), nullable=True),
    # The Admin or Lecturer who sent it; NULL when the system did (the bootstrap Invitation).
    Column("invited_by", Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    Column("kind", Text, nullable=False, server_default=text("'role'")),
    # For a `student` Invitation: the Class (`classes.classes` by name only) and its Roster entry;
    # for an `assistant` Invitation (Story 4.9) the Class alone.
    Column("class_id", Uuid, ForeignKey("classes.id", ondelete="CASCADE"), nullable=True),
    Column(
        "roster_entry_id",
        Uuid,
        ForeignKey("roster_entries.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    ),
    CheckConstraint("email = lower(btrim(email))", name="ck_invitations_email_normalised"),
    CheckConstraint(
        f"role IN ({', '.join(repr(role.value) for role in AccountRole)})",
        name="ck_invitations_role",
    ),
    CheckConstraint(
        f"kind IN ({', '.join(repr(kind.value) for kind in InvitationKind)})",
        name="ck_invitations_kind",
    ),
    CheckConstraint(
        "(kind = 'role') = (role IS NOT NULL) "
        "AND (kind = 'student') = (class_id IS NOT NULL AND roster_entry_id IS NOT NULL) "
        "AND (kind = 'assistant') = (class_id IS NOT NULL AND roster_entry_id IS NULL)",
        name="ck_invitations_kind_fields",
    ),
    Index(
        "uq_invitations_open",
        "email",
        "role",
        unique=True,
        postgresql_where=text("accepted_at IS NULL AND voided_at IS NULL"),
    ),
    Index(
        "uq_invitations_open_assistant",
        "class_id",
        "email",
        unique=True,
        postgresql_where=text("kind = 'assistant' AND accepted_at IS NULL AND voided_at IS NULL"),
    ),
    Index(
        "uq_invitations_open_roster_entry",
        "roster_entry_id",
        unique=True,
        postgresql_where=text(
            "roster_entry_id IS NOT NULL AND accepted_at IS NULL AND voided_at IS NULL"
        ),
    ),
)
"""One row per Invitation: to an account role (Story 3.7, FR-1) or, of kind `student`, to a Class's
Roster (Story 4.4, FR-8). Sending a role Invitation again for the same address and role voids the
open one, so at most one is open per address and role; at most one is open per Roster entry. Times
come from the api's clock; expiry is read from `expires_at`, with no background job."""

roster_entries = Table(
    "roster_entries",
    metadata,
    Column("id", Uuid, primary_key=True),
    # `classes.classes` by name only: `identity` imports no `classes` code.
    Column("class_id", Uuid, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False),
    # Stored trimmed and lower-cased, as `users.email`.
    Column("email", Text, nullable=False),
    # The User the address belongs to, once known (Story 4.5).
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    Column("registration", Text, nullable=False),
    Column("added_at", DateTime(timezone=True), nullable=False),
    # Set when the Lecturer removes the address (Story 4.8); the row stays.
    Column("removed_at", DateTime(timezone=True), nullable=True),
    CheckConstraint("email = lower(btrim(email))", name="ck_roster_entries_email_normalised"),
    CheckConstraint(
        f"registration IN ({', '.join(repr(r.value) for r in RosterRegistration)})",
        name="ck_roster_entries_registration",
    ),
    Index("uq_roster_entries_class_email", "class_id", "email", unique=True),
    # `authz.classes_enrolled_by` reads a Student's entries by User (Story 4.5).
    Index("ix_roster_entries_user_id", "user_id"),
)
"""One row per address on a Class's Roster (Story 4.4, FR-7, FR-8, AD-14). Addresses live only
here and in `invitations`; `classes` reaches them through `identity.service`. Times come from the
api's clock."""

institutions = Table(
    "institutions",
    metadata,
    Column("id", Uuid, primary_key=True),
    # Trimmed with inner whitespace collapsed (`schemas.institution_name`).
    Column("name", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    # The operator's own Institution, where Control tests are set up (Story 12.7, AD-27): one at
    # most (`uq_institutions_operator_owned`), written and read through `service` only.
    Column("operator_owned", Boolean, nullable=False, server_default=text("false")),
    # Story 12.6 (FR-56, FR-3): the Institution's data protection officer requires that no
    # Indicative letter is shown; every Class session of it then reads the letter as unavailable.
    # Written and read through `service` only, each change audited.
    Column("no_letter", Boolean, nullable=False, server_default=text("false")),
    CheckConstraint("name <> ''", name="ck_institutions_name_not_empty"),
)
"""One row per Institution the Admin creates (Story 3.11, FR-3); Classes belong to one (Epic 4).
Names are unique case-insensitively. Times come from the api's clock. No delete in v1."""

Index("uq_institutions_name", func.lower(institutions.c.name), unique=True)
Index(
    "uq_institutions_operator_owned",
    institutions.c.operator_owned,
    unique=True,
    postgresql_where=institutions.c.operator_owned,
)

access_requests = Table(
    "access_requests",
    metadata,
    Column("id", Uuid, primary_key=True),
    # Trimmed with inner whitespace collapsed, as the requester typed them.
    Column("name", Text, nullable=False),
    # Stored trimmed and lower-cased, as `users.email`.
    Column("email", Text, nullable=False),
    Column("institution", Text, nullable=False),
    Column("requested_at", DateTime(timezone=True), nullable=False),
    Column("status", Text, nullable=False, server_default="open"),
    Column("closed_at", DateTime(timezone=True), nullable=True),
    # The Admin who invited from it or dismissed it.
    Column("closed_by", Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    Column("invitation_id", Uuid, ForeignKey("invitations.id", ondelete="SET NULL"), nullable=True),
    CheckConstraint("email = lower(btrim(email))", name="ck_access_requests_email_normalised"),
    CheckConstraint("status IN ('open', 'invited', 'dismissed')", name="ck_access_requests_status"),
    Index(
        "uq_access_requests_open",
        "email",
        unique=True,
        postgresql_where=text("status = 'open'"),
    ),
)
"""One row per request for lecturer access from the Landing (Story 3.13, FR-1). `open` until the
Admin invites from it (`invited`) or dismisses it (`dismissed`); at most one is open per address,
and a repeat updates that row. Times come from the api's clock."""

roster_uploads = Table(
    "roster_uploads",
    metadata,
    Column("id", Uuid, primary_key=True),
    # `classes.classes` by name only: `identity` imports no `classes` code. One per Class.
    Column(
        "class_id", Uuid, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, unique=True
    ),
    Column("uploaded_by", Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("file_name", Text, nullable=False),
    # The header row's cells, one per column ("" for an empty one); all "" with no header row.
    Column("headers", JSONB, nullable=False),
    Column("has_header", Boolean, nullable=False),
    Column("column_count", Integer, nullable=False),
    Column("row_count", Integer, nullable=False),
    # 0-based index of the e-mail column; NULL when no column looked like one.
    Column("chosen_column", Integer, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False, index=True),
    # `file` for an uploaded file, `paste` for pasted addresses (Story 4.3): one column, no header.
    Column("source", Text, nullable=False, server_default=text("'file'")),
    CheckConstraint(
        "chosen_column IS NULL OR (chosen_column >= 0 AND chosen_column < column_count)",
        name="ck_roster_uploads_chosen_column",
    ),
    CheckConstraint("source IN ('file', 'paste')", name="ck_roster_uploads_source"),
)
"""A staged Roster upload (Story 4.2, FR-7, AD-14): the cell values of the file a Lecturer
uploaded for a Class, never the file itself. A new upload for the Class replaces it; it is purged
once `expires_at` has passed (`service.purge_expired_roster_uploads`). Times come from the api's
clock."""

roster_upload_rows = Table(
    "roster_upload_rows",
    metadata,
    Column(
        "upload_id", Uuid, ForeignKey("roster_uploads.id", ondelete="CASCADE"), primary_key=True
    ),
    # The row's number in the file (1-based, counting the header and empty rows).
    Column("row_number", Integer, primary_key=True),
    # The row's cells as strings, one per column up to its last non-empty one.
    Column("cells", JSONB, nullable=False),
)
"""The data rows of a staged Roster upload, without the header row."""
