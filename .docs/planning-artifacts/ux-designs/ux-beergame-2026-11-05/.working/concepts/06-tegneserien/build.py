"""Bygger alle SVG-ene for konsept 06 Tegneserien. Kjør: uv run python build.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from c06_ink import *  # noqa: E402,F403
import c06_game  # noqa: E402
import c06_debrief  # noqa: E402
import c06_laerer  # noqa: E402
import c06_rest  # noqa: E402


def main():
    only = sys.argv[1:] or None
    pages = {
        "01": c06_rest.landing, "02": c06_laerer.klasse, "03": c06_laerer.oppsett, "04": c06_game.student_hjem,
        "05": c06_game.spill, "06": c06_game.dynamikk, "07": c06_debrief.debrief, "08": c06_laerer.oversikt,
        "09": c06_rest.alle_sider,
    }
    for key, fn in pages.items():
        if only is None or key in only:
            fn()
            print("bygget", key)


if __name__ == "__main__":
    main()
