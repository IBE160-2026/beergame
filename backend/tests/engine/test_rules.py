"""Rules versions (Story 1.10, AD-4): one package per version, selected by `rules_version`."""

import importlib
import pkgutil
import sys
import types

import pytest

from app.engine import (
    ROLES,
    RULES_VERSION,
    GameSettings,
    UnknownRulesVersionError,
    advance,
    initial_state,
    rules,
)
from app.engine.rules import v1

FOURS = {role: 4 for role in ROLES}


def test_version_1_is_the_only_packaged_version_and_the_default():
    assert rules.versions() == (1,)
    assert RULES_VERSION == max(rules.versions())
    assert rules.package(1) is v1
    assert rules.has_version(1)


@pytest.mark.parametrize("version", [0, -1, 2, 99, "1", 1.0, True, None])
def test_a_version_without_a_package_is_unknown(version):
    assert not rules.has_version(version)
    with pytest.raises(UnknownRulesVersionError) as caught:
        rules.package(version)
    assert caught.value.version == version


def test_versions_lists_only_version_packages(monkeypatch):
    found = [
        pkgutil.ModuleInfo(None, "v1", True),
        pkgutil.ModuleInfo(None, "v10", True),
        pkgutil.ModuleInfo(None, "v2", True),
        pkgutil.ModuleInfo(None, "v3", False),  # a module, not a package
        pkgutil.ModuleInfo(None, "v0", True),
        pkgutil.ModuleInfo(None, "helpers", True),
    ]
    monkeypatch.setattr(rules.pkgutil, "iter_modules", lambda path: iter(found))
    assert rules.versions() == (1, 2, 10)


def test_a_broken_package_is_not_reported_as_missing(monkeypatch):
    def broken(name):
        raise ModuleNotFoundError("No module named 'gone'", name="gone")

    monkeypatch.setattr(rules.importlib, "import_module", broken)
    with pytest.raises(ModuleNotFoundError):
        rules.package(1)


def test_advance_and_initial_state_run_the_selected_package(monkeypatch):
    settings = GameSettings()
    fake = types.ModuleType("app.engine.rules.v2")
    calls = []

    def fake_initial(s):
        calls.append(("initial", s))
        return v1.initial_state(s)

    def fake_advance(s, state, orders):
        calls.append(("advance", state.week))
        return v1.advance(s, state, orders)

    fake.initial_state = fake_initial
    fake.advance = fake_advance
    monkeypatch.setitem(sys.modules, "app.engine.rules.v2", fake)
    state = initial_state(settings, 2)
    following = advance(settings, state, FOURS, 2)
    assert calls == [("initial", settings), ("advance", 1)]
    assert following == advance(settings, initial_state(settings), FOURS)
    with pytest.raises(UnknownRulesVersionError):
        initial_state(settings, 3)
    with pytest.raises(UnknownRulesVersionError):
        advance(settings, state, FOURS, 3)


def test_the_errors_keep_their_import_paths():
    from app.engine import GameFinishedError, InvalidOrdersError
    from app.engine.week import GameFinishedError as WeekFinished

    assert WeekFinished is GameFinishedError is v1.GameFinishedError
    assert InvalidOrdersError is importlib.import_module("app.engine.errors").InvalidOrdersError
