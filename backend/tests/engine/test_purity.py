"""AD-1: the engine imports only stdlib and pydantic, and nothing that reads a clock or chance."""

import ast
import sys
from pathlib import Path

ENGINE = Path(__file__).parents[2] / "app" / "engine"
ALLOWED_THIRD_PARTY = {"pydantic"}
FORBIDDEN_STDLIB = {"time", "datetime", "random", "secrets", "os", "io", "socket", "pathlib"}


def imported_roots(source: str) -> set[str]:
    roots = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            roots |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def test_imported_roots_reads_both_import_forms():
    source = "import time.x\nfrom a.b import c\nfrom . import d"
    assert imported_roots(source) == {"time", "a"}


def test_engine_imports_only_stdlib_pydantic_and_itself():
    files = sorted(ENGINE.rglob("*.py"))
    assert ENGINE / "rules" / "v1" / "__init__.py" in files  # every rules version is scanned
    for path in files:
        roots = imported_roots(path.read_text(encoding="utf-8"))
        outside = roots - {"app"} - ALLOWED_THIRD_PARTY - set(sys.stdlib_module_names)
        assert not outside, f"{path.name} imports {outside}"
        assert not roots & FORBIDDEN_STDLIB, f"{path.name} imports {roots & FORBIDDEN_STDLIB}"
        source = path.read_text(encoding="utf-8")
        assert "app.modules" not in source and "app.platform" not in source, path.name
