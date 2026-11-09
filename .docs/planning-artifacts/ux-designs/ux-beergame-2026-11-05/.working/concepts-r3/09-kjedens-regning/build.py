"""Bygger alle SVG-ene i konsept 09 Kjedens regning fra ../_shared/fixture.json.
Kjør fra denne mappa: uv run python build.py
e09cost.py stopper bygget hvis regningen ikke går opp mot loggen: uke for uke, per Rolle, per kostnadsart og for kjeden,
for spill 17 og begge simuleringene, og for alle 60 Klassespill (regnet fra netto lager)."""
import importlib

import e09cost  # noqa: F401  kontrollene kjører ved import

for mod, fns in (("screens_core", ("build_05", "build_06", "build_10")),
                 ("screens_debrief_teacher", ("build_07", "build_08")),
                 ("screens_rest", ("build_01", "build_02", "build_03", "build_04", "build_09"))):
    m = importlib.import_module(mod)
    for fn in fns:
        getattr(m, fn)()
        print("bygget", fn)
