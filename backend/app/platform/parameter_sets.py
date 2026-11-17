"""Read named parameter sets held as configuration files (FR-33).

A set is `app/parameter_sets/<kind>/<id>.json`. This module only finds and reads the text; the
engine validates it (for example `app.engine.rule_based.parse_params`).
"""

import re
from pathlib import Path

PARAMETER_SETS = Path(__file__).parents[1] / "parameter_sets"
_KIND = re.compile(r"[a-z0-9][a-z0-9_-]*")
_SET_ID = re.compile(r"[a-z0-9][a-z0-9-]*")
"""The same pattern as `RuleBasedParams.id`."""


class UnknownParameterSetError(LookupError):
    """No parameter set of that kind and id exists."""


def read_parameter_set(kind: str, set_id: str, root: Path = PARAMETER_SETS) -> str:
    """The JSON text of parameter set `set_id` of `kind` (e.g. `rule_based`)."""
    if not (_KIND.fullmatch(kind) and _SET_ID.fullmatch(set_id)):
        raise UnknownParameterSetError(f"no {kind} parameter set {set_id!r}")
    path = root / kind / f"{set_id}.json"
    if not path.is_file():
        raise UnknownParameterSetError(f"no {kind} parameter set {set_id!r}")
    return path.read_text(encoding="utf-8")
