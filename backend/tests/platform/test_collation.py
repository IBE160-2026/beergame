"""Names sort in Norwegian order: æ, ø, å after z, case-insensitively, in Python and in SQL."""

from sqlalchemy import String as SAString
from sqlalchemy import column, select, values
from sqlalchemy.dialects import postgresql

from app.platform.collation import nb_sort_key, nb_sort_sql
from tests.conftest import kept_connection

NAMES = ["Øyvind", "åse", "Zara", "ærlig", "anna", "Åge", "Ola", "Émile", "Ærlend", "Ödön", "Ärla"]
NORWEGIAN = [
    "anna",
    "Émile",
    "Ola",
    "Zara",
    "Ärla",
    "Ærlend",
    "ærlig",
    "Ödön",
    "Øyvind",
    "Åge",
    "åse",
]


def test_the_key_puts_ae_oe_aa_after_z_and_ignores_case() -> None:
    assert sorted(NAMES, key=nb_sort_key) == NORWEGIAN
    assert nb_sort_key("ÅSE") == nb_sort_key("åse")
    assert nb_sort_key(None) == ""


def test_a_class_staff_list_uses_it() -> None:
    from app.modules.classes.service import _sort_key

    staff = [("Åse", "c@x.no"), ("Ærlig", "b@x.no"), (None, "zed@x.no"), ("Øyvind", "a@x.no")]
    ordered = sorted(staff, key=lambda each: _sort_key(*each))
    assert [each[1] for each in ordered] == ["zed@x.no", "b@x.no", "a@x.no", "c@x.no"]


def test_the_database_order_is_the_same(test_database: str) -> None:
    name = column("name", SAString)
    rows = values(name, name="names").data([(each,) for each in NAMES])
    query = select(rows.c.name).order_by(nb_sort_sql(rows.c.name))
    sql = str(query.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
    found = [row[0] for row in kept_connection(test_database).execute(sql)]
    assert found == NORWEGIAN
