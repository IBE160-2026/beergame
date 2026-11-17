"""Errors the engine raises; every rules version raises these same types."""


class GameFinishedError(ValueError):
    """`advance` was called on a finished Game."""


class InvalidOrdersError(ValueError):
    """The Orders for a Week are incomplete or out of bounds; `role` names the culprit."""

    def __init__(self, role: str, reason: str) -> None:
        self.role = role
        super().__init__(f"{role}: {reason}")


class UnknownRulesVersionError(ValueError):
    """No rules package exists for the requested `rules_version`."""

    def __init__(self, version: object) -> None:
        self.version = version
        super().__init__(f"no rules package for rules version {version!r}")
