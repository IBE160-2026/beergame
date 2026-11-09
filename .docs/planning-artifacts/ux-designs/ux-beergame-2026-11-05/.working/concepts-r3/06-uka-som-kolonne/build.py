"""Bygger alle SVG-ene i konsept 06 Uka som kolonne (runde 3) fra ../_shared/fixture.json.
Kjør fra denne mappa: uv run python build.py
e06lib kontrollerer ved import at matrisen, grafene og kostnaden stemmer med loggen for alle uker, og stopper ellers."""
import screens_core
import screens_dyn
import screens_debrief_teacher
import screens_rest

for fn in (screens_rest.build_01, screens_rest.build_02, screens_rest.build_03, screens_rest.build_04,
           screens_core.build_05, screens_dyn.build_06, screens_debrief_teacher.build_07,
           screens_debrief_teacher.build_08, screens_rest.build_09, screens_dyn.build_10):
    fn()
    print("bygget", fn.__name__)
