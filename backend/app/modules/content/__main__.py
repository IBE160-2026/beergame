"""Publish a new content version from a JSON file (Story 6.3, AD-23):

    uv run python -m app.modules.content starting_task path/to/starting-task.json
    uv run python -m app.modules.content detected_patterns path/to/patterns.json
    uv run python -m app.modules.content sentence_templates path/to/templates.json
    uv run python -m app.modules.content moment_templates path/to/moment-templates.json
    uv run python -m app.modules.content debrief_quiz path/to/debrief-quiz.json
    uv run python -m app.modules.content narration_templates path/to/narration-templates.json

The file is validated like every record; the new version is printed. Class sessions locked from
then on pin it; sessions locked before keep theirs. No code change is needed for new items."""

import asyncio
import json
import sys
from pathlib import Path

from app.modules.content import service


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        sys.stderr.write("usage: python -m app.modules.content <kind> <file.json>\n")
        return 2
    kind, path = argv
    body = json.loads(Path(path).read_text(encoding="utf-8"))
    version = asyncio.run(service.publish(kind, body))
    sys.stdout.write(f"{kind} v{version}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
