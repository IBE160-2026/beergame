"""Bygger alle SVG-ene for konsept 08 Rapporten. Bruk: uv run python build.py [navn ...]"""
import importlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

PAGES = {
    "01-landing": ("p_misc", "page_01"),
    "02-laerer-klasse": ("p_teacher", "page_02"),
    "03-laerer-spill": ("p_teacher", "page_03"),
    "04-student-hjem": ("p_misc", "page_04"),
    "05-spill": ("p_game", "page_05"),
    "06-spilldynamikk": ("p_game", "page_06"),
    "07-debrief": ("p_debrief", "page_07"),
    "08-laerer-oversikt": ("p_teacher", "page_08"),
    "09-alle-sider": ("p_misc", "page_09"),
    "10-pedagogikk": ("p_game", "page_10"),
}


def main():
    wanted = sys.argv[1:] or list(PAGES)
    for name in PAGES:
        if not any(w in name for w in wanted):
            continue
        mod, fn = PAGES[name]
        try:
            module = importlib.import_module(mod)
        except ModuleNotFoundError as err:
            print("hopper over", name, err)
            continue
        doc = getattr(module, fn)()
        (HERE / f"{name}.svg").write_text(doc.save(), encoding="utf-8")
        print("skrev", name)


if __name__ == "__main__":
    main()
