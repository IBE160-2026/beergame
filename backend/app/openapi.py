"""Write the API's OpenAPI schema as stable JSON (AD-10).

`uv run python -m app.openapi ../frontend/src/lib/api/openapi.json`, then `npm run api:generate`
in `frontend/`. With no path it prints the schema. CI regenerates both and fails on any
difference.
"""

import json
import sys
from pathlib import Path

from app.main import create_app


def schema_json() -> str:
    return json.dumps(create_app().openapi(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


if __name__ == "__main__":
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(schema_json(), encoding="utf-8", newline="\n")
    else:
        sys.stdout.reconfigure(encoding="utf-8", newline="\n")
        sys.stdout.write(schema_json())
