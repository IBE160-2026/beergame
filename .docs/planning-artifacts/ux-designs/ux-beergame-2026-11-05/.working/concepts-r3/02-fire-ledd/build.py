"""Bygger alle SVG-ene i konsept 02 Fire ledd fra ../_shared/fixture.json.
Kjør fra denne mappa: uv run python build.py"""
import importlib

for mod, fns in (("screens_core", ("build_05", "build_06", "build_10")),
                 ("screens_debrief_teacher", ("build_07", "build_08")),
                 ("screens_rest", ("build_01", "build_02", "build_03", "build_04", "build_09"))):
    try:
        m = importlib.import_module(mod)
    except ModuleNotFoundError as err:
        print("hopper over", mod, err)
        continue
    for fn in fns:
        getattr(m, fn)()
        print("bygget", fn)
