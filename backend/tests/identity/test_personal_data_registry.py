"""The personal-data registry (Story 15.2, AD-14): every table has a deletion handling, every
table that names a User is handled, and every `delete` or `clear` table is erased by a part
registered with `identity.erasure`, so access and deletion cannot drift apart. No database."""

from sqlalchemy import Column, Table, Uuid

import app.main  # noqa: F401  (every module's tables and erasure parts)
from app.modules.identity import erasure
from app.modules.identity.personal_data import REGISTRY
from app.platform.db import metadata

USER_COLUMNS = {"user_id", "opener_id", "sender_id", "recipient_user_id", "actor_user_id"}


def names_a_user(column) -> bool:
    """A column that holds a User's id: a foreign key to `users`, or by its name (the game tables
    keep the id without a key, AD-5)."""
    if any(key.column.table.name == "users" for key in column.foreign_keys):
        return True
    if not isinstance(column.type, Uuid):
        return False
    return column.name in USER_COLUMNS or column.name.endswith(("_user_id", "_by"))


def test_every_table_has_a_deletion_handling():
    missing = sorted(set(metadata.tables) - set(REGISTRY))
    assert missing == [], f"add these tables to identity/personal_data.py: {missing}"
    unknown = sorted(set(REGISTRY) - set(metadata.tables))
    assert unknown == [], f"the registry names tables that do not exist: {unknown}"


def test_a_table_that_names_a_user_is_never_marked_as_holding_none():
    for name, table in metadata.tables.items():
        if any(names_a_user(column) for column in table.columns):
            assert REGISTRY[name].handling != "none", name


def test_every_delete_and_clear_table_is_erased_by_a_registered_part():
    covered = erasure.covered_tables()
    for name, entry in REGISTRY.items():
        if entry.handling in ("delete", "clear", "anonymise"):
            assert covered.get(name), f"no erasure part handles {name} ({entry.handling})"
    for name in covered:
        assert REGISTRY[name].handling in ("delete", "clear", "anonymise"), name


def test_the_check_sees_a_table_without_a_handling():
    """The first check fails for a new table, as it must for any table added later."""
    from app.platform.db import metadata as shared

    extra = Table("story_15_2_probe", shared, Column("user_id", Uuid))
    try:
        assert "story_15_2_probe" not in REGISTRY
        assert set(shared.tables) - set(REGISTRY) == {"story_15_2_probe"}
        assert names_a_user(extra.c.user_id)
    finally:
        shared.remove(extra)


def test_every_table_with_personal_data_is_shown_on_mine_data_or_says_why_not():
    """Story 15.1 (FR-75, AD-14): a table that holds personal data has a «Mine data» category or
    a reason it is not shown, never both and never neither, so no stored category can be missing
    from the page; a table that names a User holds personal data (checked above)."""
    from app.modules.identity.personal_data import NOT_SHOWN, SHOWN
    from app.platform.own_data import CATEGORIES

    for name, entry in REGISTRY.items():
        if entry.handling == "none":
            assert entry.category is None and entry.outside is None, name
            continue
        assert (entry.category is None) != (entry.outside is None), name
    assert set(SHOWN) | set(NOT_SHOWN) <= set(REGISTRY)
    assert set(SHOWN.values()) <= set(CATEGORIES)
    # Every category but the computed letter is backed by a table.
    assert set(CATEGORIES) - set(SHOWN.values()) == {"letter"}


def test_the_report_snapshot_is_listed_with_its_lifetime():
    assert "TOKEN_LIFETIME" in REGISTRY["report_snapshots"].outside
