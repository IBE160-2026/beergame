"""Bygger alle SVG-ene i konsept 01 Modellen. Kjør: uv run python build.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from modell import *  # noqa: E402,F403
from sider_spill import spill05, spill06, pedagogikk10  # noqa: E402
from sider_debrief import debrief07, oversikt08  # noqa: E402
from sider_rest import landing01, klasse02, klasseokt03, hjem04, alle09  # noqa: E402

if __name__ == "__main__":
    only = sys.argv[1:] or None
    pages = {
        "01": landing01, "02": klasse02, "03": klasseokt03, "04": hjem04, "05": spill05,
        "06": spill06, "07": debrief07, "08": oversikt08, "09": alle09, "10": pedagogikk10,
    }
    for key, fn in pages.items():
        if only and key not in only:
            continue
        fn()
        print("bygd", key)
