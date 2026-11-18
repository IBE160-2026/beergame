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
