"""Bygger alle SVG-ene i det valgte designet (Graf over tabell, med Debrief og kostnad fra Labtime-skjermen)
fra ../concepts-r3/_shared/fixture.json. Kjør fra denne mappa: uv run python build.py

vlib stopper bygget (assert) hvis tallene ikke stemmer med loggen: materialbalanse uke for uke, lager mot sendt,
ukeskost = lager × 0,50 + restordre × 1,00, sum per Rolle, kjedekost for spill 17 og de simulerte referansene,
Saras tall i Uke 11, kjedekost for alle 60 klassespill, kostnadspanelet (43,00 + 25,00 = 68,00), Kjedens regning
mot kost_per_rolle (901,00 / 1 365,00 / 2 266,00, Simulert 1 507,00 og 1 341,00), skalaregelen for kjedebåndet
på telefon i alle 36 uker, kontrast for celletall og tekst, og at ingen tekst er under 9 px (utenom 09).
Etterpå: uv run python sjekk.py og uv run python ../concepts-r3/_shared/render.py ."""
import screens_core
import screens_dyn
import screens_debrief_teacher
import screens_rest

for fn in (screens_rest.build_01, screens_rest.build_02, screens_rest.build_03, screens_rest.build_04,
           screens_core.build_05, screens_dyn.build_06, screens_debrief_teacher.build_07,
           screens_debrief_teacher.build_08, screens_rest.build_09, screens_dyn.build_10):
    fn()
    print("bygget", fn.__name__)
