"""Tables owned by `modules/classes` (Story 4.1, AD-24)."""

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Table, Text, Uuid

from app.modules.classes.schemas import StaffRole
from app.platform.db import metadata

classes = Table(
    "classes",
    metadata,
    Column("id", Uuid, primary_key=True),
    # Trimmed with inner whitespace collapsed (`schemas.class_name`).
    Column("name", Text, nullable=False),
    # NULL when the Class has none; never an empty string.
    Column("course_code", Text, nullable=True),
    Column(
        "institution_id",
        Uuid,
        ForeignKey("institutions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    ),
    Column("created_by", Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    # Set by the archive (Story 4.10).
    Column("archived_at", DateTime(timezone=True), nullable=True),
    CheckConstraint("name <> ''", name="ck_classes_name_not_empty"),
    CheckConstraint(
        "course_code IS NULL OR course_code <> ''", name="ck_classes_course_code_not_empty"
    ),
)
"""One row per Class (FR-6). Times come from the api's clock."""

class_staff = Table(
    "class_staff",
    metadata,
    Column("class_id", Uuid, ForeignKey("classes.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True
    ),
    Column("role", Text, nullable=False),
    Column("added_at", DateTime(timezone=True), nullable=False),
    CheckConstraint(
        f"role IN ({', '.join(repr(role.value) for role in StaffRole)})",
        name="ck_class_staff_role",
    ),
)
"""Who works in a Class and as what. `platform/authz.classes_visible_to` reads it by name."""
