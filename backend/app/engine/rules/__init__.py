"""Rules versions (AD-4): each version of the Week arithmetic is its own package `v<N>`.

A stored Game names its `rules_version`; `package(rules_version)` returns the module that
computes it, so a Game is always replayed and advanced by the rules it was created under. An
edit that changes any engine output is a new package, never an edit to one a stored
non-simulation Game references. See `app/engine/RULES_VERSIONS.md`.

Every package exposes `initial_state(settings)` and `advance(settings, state, orders)`.
"""

import importlib
import pkgutil
import re
from types import ModuleType

from app.engine.errors import UnknownRulesVersionError

RULES_VERSION = 1
"""The version new Games are created under (AD-4)."""

_PACKAGE = re.compile(r"v([1-9][0-9]*)")


def versions() -> tuple[int, ...]:
    """The rules versions packaged with this engine, oldest first."""
    found = []
    for module in pkgutil.iter_modules(__path__):
        match = _PACKAGE.fullmatch(module.name)
        if module.ispkg and match is not None:
            found.append(int(match.group(1)))
    return tuple(sorted(found))


def package(version: object) -> ModuleType:
    """The rules package of `version`; `UnknownRulesVersionError` when there is none."""
    if type(version) is not int or version < 1:
        raise UnknownRulesVersionError(version)
    name = f"{__name__}.v{version}"
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as error:
        if error.name != name:
            raise
        raise UnknownRulesVersionError(version) from None


def has_version(version: object) -> bool:
    """Whether `version` has a rules package."""
    try:
        package(version)
    except UnknownRulesVersionError:
        return False
    return True
