"""Bygger alle SVG-ene i konsept 04 Graf over tabell fra ../_shared/fixture.json.
Kjør fra denne mappa: uv run python build.py

e04lib stopper bygget (assert) hvis tallene i tabellene, grafene og kostnaden ikke stemmer med loggen:
materialbalanse uke for uke, lager mot sendt, ukeskost = lager × 0,50 + restordre × 1,00, sum per Rolle,
kjedekost for spill 17 og de simulerte referansene, Saras tall i Uke 11, og kjedekost for alle 60 klassespill."""
import screens_core
import screens_dyn
import screens_debrief_teacher
import screens_rest

for fn in (screens_rest.build_01, screens_rest.build_02, screens_rest.build_03, screens_rest.build_04,
           screens_core.build_05, screens_dyn.build_06, screens_debrief_teacher.build_07,
           screens_debrief_teacher.build_08, screens_rest.build_09, screens_dyn.build_10):
    fn()
    print("bygget", fn.__name__)
