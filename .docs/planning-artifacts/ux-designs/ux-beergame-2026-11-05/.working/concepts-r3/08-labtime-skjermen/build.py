"""Bygger alle SVG-ene i konsept 08 Labtime-skjermen fra ../_shared/fixture.json.
Kontrollene i e08grid.py og screens_debrief_teacher.py stopper bygget hvis tall, grafer og kostnad ikke stemmer med loggen.
Kjør fra denne mappa: uv run python build.py"""
import importlib

for mod, fns in (("screens_core", ("build_05", "build_06", "build_10")),
                 ("screens_debrief_teacher", ("build_07", "build_08")),
                 ("screens_rest", ("build_01", "build_02", "build_03", "build_04", "build_09"))):
    m = importlib.import_module(mod)
    for fn in fns:
        getattr(m, fn)()
        print("bygget", fn)
