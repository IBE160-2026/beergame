"""Tables owned by `modules/identity` (AD-14, AD-24). Names and e-mails live only here."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Table,
    Text,
    Uuid,
    func,
    true,
)

from app.modules.identity.schemas import AccountRole
from app.platform.db import metadata

users = Table(
    "users",
    metadata,
    Column("id", Uuid, primary_key=True),
    # Stored trimmed and lower-cased, so the unique constraint is case-insensitive.
    Column("email", Text, nullable=False, unique=True),
    Column("name", Text, nullable=False),
    Column("password_hash", Text, nullable=False),
    Column("is_active", Boolean, nullable=False, server_default=true()),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("email = lower(btrim(email))", name="ck_users_email_normalised"),
)
"""One row per account; exactly one User per e-mail (FR-4)."""

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
