"""Publish content versions (Story 6.3, Story 11.1, AD-23).

One file, one new version of its kind:

    uv run python -m app.modules.content starting_task path/to/starting-task.json
    uv run python -m app.modules.content detected_patterns path/to/patterns.json
    uv run python -m app.modules.content sentence_templates path/to/templates.json
    uv run python -m app.modules.content moment_templates path/to/moment-templates.json
    uv run python -m app.modules.content debrief_quiz path/to/debrief-quiz.json
    uv run python -m app.modules.content narration_templates path/to/narration-templates.json
    uv run python -m app.modules.content question_set path/to/question-set.json
    uv run python -m app.modules.content scoring_guide path/to/scoring-guide.json

The content load (Story 11.1): every `<kind>.json` in a folder (default: the files shipped in the
repo, `app/modules/content/files/`), the Starting task first, each published only when its body
is not stored as a version of its kind yet, so a second run, or an older file, publishes nothing:

    uv run python -m app.modules.content load [folder]

Every file is validated like every record; the new versions are printed. A file that is refused
prints `<file>: <code>: <detail>` with a stable code (`unknown_kind`, `unknown_item_type`,
`interactive_missing`, `starting_task_items_missing`, `criteria_count`, `invalid_record`,
`no_folder`) and the command exits 1; the other files are still loaded. Class sessions locked
from then on pin the new versions; sessions locked before keep theirs. No code change is needed
for new items."""

import asyncio
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from app.modules.content import service
from app.modules.content.models import Kind

SHIPPED = Path(__file__).resolve().parent / "files"
"""The content files shipped in the repo (Story 11.1): `<kind>.json`."""


def _order(path: Path) -> tuple[int, str]:
    """Kinds in catalogue order (the Starting task before the question set that references it),
    unknown names last."""
    kinds = [kind.value for kind in Kind]
    return (kinds.index(path.stem) if path.stem in kinds else len(kinds), path.name)


def _why(invalid: ValidationError) -> str:
    return "; ".join(
        f"{'.'.join(map(str, error['loc'])) or 'body'}: {error['msg']}"
        for error in invalid.errors()
    )


async def load(folder: Path) -> tuple[list[str], list[str]]:
    """Publish each `<kind>.json` in `folder` whose body is not stored as any version of its kind
    yet, the Starting task first: (lines for what was published or left, lines for what was
    refused). A body stored already is left, so a second run, or an older file, publishes
    nothing."""
    if not folder.is_dir():  # noqa: ASYNC240 (a command, run alone)
        return [], [f"{folder}: no_folder: not a folder"]
    done: list[str] = []
    refused: list[str] = []
    for path in sorted(folder.glob("*.json"), key=_order):  # noqa: ASYNC240
        try:
            kind = Kind(path.stem)
        except ValueError:
            refused.append(f"{path.name}: unknown_kind: {path.stem!r}")
            continue
        try:
            body = json.loads(path.read_text(encoding="utf-8"))
            wanted = service.normalised(kind, body)
            stored = await service.stored_version_of(kind, wanted)
            if stored is not None:
                done.append(f"{kind} unchanged (v{stored})")
                continue
            version = await service.publish(kind, body)
        except service.ContentRejected as rejected:
            refused.append(f"{path.name}: {rejected.code}: {rejected.detail}")
            continue
        except ValidationError as invalid:
            refused.append(f"{path.name}: invalid_record: {_why(invalid)}")
            continue
        except (ValueError, OSError) as unreadable:  # bad JSON or encoding, an unreadable file
            refused.append(f"{path.name}: invalid_record: {unreadable}")
            continue
        done.append(f"{kind} v{version}")
    return done, refused


def main(argv: list[str]) -> int:
    if argv[:1] == ["load"] and len(argv) <= 2:
        folder = Path(argv[1]) if len(argv) == 2 else SHIPPED
        done, refused = asyncio.run(load(folder))
        for line in done:
            sys.stdout.write(f"{line}\n")
        for line in refused:
            sys.stderr.write(f"{line}\n")
        return 1 if refused else 0
    if len(argv) != 2:
        sys.stderr.write(
            "usage: python -m app.modules.content <kind> <file.json>\n"
            "       python -m app.modules.content load [folder]\n"
        )
        return 2
    kind, path = argv
    body = json.loads(Path(path).read_text(encoding="utf-8"))
    version = asyncio.run(service.publish(kind, body))
    sys.stdout.write(f"{kind} v{version}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
