"""Norwegian alphabetical order for names (every list of people, Classes or Institutions).

`casefold()` alone puts «Åse» before «Ærlig» and «Øyvind» (Unicode order), while Norwegian puts
æ, ø and å after z, in that order. `nb_sort_key` gives a case-insensitive key in Norwegian order;
`nb_sort_sql` is the same order in SQL, for lists sorted (and paged) in the database. Both fold
by one table so the two orders agree: æ and ä sort as one letter after z, then ø and ö, then å;
ü sorts as y, and the other common accented letters as their base letter (é as e).
"""

from sqlalchemy import ColumnElement, func

# Placed right after «z» in code point order: { | }
_AE, _OE, _AA = "{", "|", "}"

_FOLD = {
    "æ": _AE,
    "ä": _AE,
    "ø": _OE,
    "ö": _OE,
    "å": _AA,
    "ü": "y",
    **{
        accented: base
        for base, group in {
            "a": "áàâã",
            "c": "ç",
            "e": "éèêë",
            "i": "íìîï",
            "n": "ñ",
            "o": "óòôõ",
            "u": "úùû",
            "y": "ýÿ",
        }.items()
        for accented in group
    },
}

_TABLE = str.maketrans(_FOLD)
# For SQL, both cases (the database's lower() may leave non-ASCII capitals as they are).
_SQL_FROM = "".join(_FOLD) + "".join(each.upper() for each in _FOLD if each.upper() != each)
_SQL_TO = "".join(_FOLD.values()) + "".join(_FOLD[each] for each in _FOLD if each.upper() != each)


def nb_sort_key(text: str | None) -> str:
    """A case-insensitive key that sorts `text` in Norwegian order (None sorts as "")."""
    return (text or "").casefold().translate(_TABLE)


def nb_sort_sql(column: ColumnElement[str]) -> ColumnElement[str]:
    """`column` as a key in Norwegian order, compared byte-wise (`COLLATE "C"`) so the database's
    own locale cannot reorder it; the same order as `nb_sort_key` for the letters it folds."""
    return func.translate(func.lower(column), _SQL_FROM, _SQL_TO).collate("C")
