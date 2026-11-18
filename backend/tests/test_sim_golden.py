"""Story 2.1: the order source in `players` gives the Epic 1 batches the Orders and costs they
had when the runner chose the Orders itself. The golden files were captured from `sim run` before
the runner's order loop was removed: the exported Decision log without its ids, and the summary
with each Game id replaced by its index in the batch. To keep the test fast it plays only the
first Game of each batch and compares it with that Game's rows and summary block."""

import csv
import json
import re
from pathlib import Path

import pytest

from app import sim

BATCHES = Path(__file__).parents[1] / "batches"
GOLDEN = Path(__file__).parent / "golden" / "batches"


def masked_log(path: Path) -> tuple[list[str], dict[str, int]]:
    with path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.reader(file))
    head = rows[0]
    keep = [i for i, name in enumerate(head) if name not in ("game_id", "seat_id")]
    ids: dict[str, int] = {}
    lines = [",".join(["game", *(head[i] for i in keep)])]
    for row in rows[1:]:
        index = ids.setdefault(row[0], len(ids))
        lines.append(",".join([str(index), *(row[i] for i in keep)]))
    return lines, ids


@pytest.mark.parametrize("name", ["classic-smoke", "classic-rule-based", "classic-scripted"])
def test_epic_1_batches_equal_their_golden_results(name, games_db, tmp_path, capsys):
    batch = json.loads((BATCHES / f"{name}.json").read_text(encoding="utf-8"))
    first = tmp_path / "first.json"
    first.write_text(json.dumps({**batch, "games": 1}), encoding="utf-8")
    code = sim.main(["run", str(first), "--export", str(tmp_path)])
    out = capsys.readouterr().out.splitlines()
    assert code == 0
    log, ids = masked_log(tmp_path / sim.EXPORT_FILE)
    golden_log = (GOLDEN / f"{name}.csv").read_text(encoding="utf-8").splitlines()
    assert log == [golden_log[0], *(line for line in golden_log[1:] if line.startswith("0,"))]
    block = [line for line in out if line.split(" ")[0] in {"game", "cost", "orders"}][:3]
    block[0] = re.sub(r"^game (\S+) seed", lambda m: f"game {ids[m.group(1)]} seed", block[0])
    golden_summary = (GOLDEN / f"{name}.summary.txt").read_text(encoding="utf-8").splitlines()
    assert block == golden_summary[:3]
