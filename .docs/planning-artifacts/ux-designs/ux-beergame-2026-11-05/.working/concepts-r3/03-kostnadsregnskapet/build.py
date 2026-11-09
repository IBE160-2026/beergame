"""Bygger alle SVG-ene i konsept 03 Kostnadsregnskapet fra ../_shared/fixture.json.
Kjør fra denne mappa: uv run python build.py

Etter bygget kontrolleres hvert tall som er tegnet i en matrise mot loggen, og at
materialbalansen og kostnaden stemmer for alle Roller og alle uker. Bygget stopper hvis noe avviker."""
import sys

import e03kost as K3
import screens_core
import screens_debrief_teacher
import screens_rest
from e03kost import FX, ROLES, Seat, wcost

for fn in (screens_core.build_05, screens_core.build_06, screens_core.build_10,
           screens_debrief_teacher.build_07, screens_debrief_teacher.build_08,
           screens_rest.build_01, screens_rest.build_02, screens_rest.build_03, screens_rest.build_04, screens_rest.build_09):
    fn()
    print("bygget", fn.__name__)

# 1. Loggen: materialbalanse og kostnad for alle Roller og uker
log = FX["spill17"]["serier"]
for r in ROLES:
    s = log[r]
    S = Seat(r)
    acc = 0.0
    for i in range(36):
        net = s["lager"][i] - s["restordre"][i]
        if i:
            prev = s["lager"][i - 1] - s["restordre"][i - 1]
            assert net == prev + s["levering"][i] - s["innkommende_ordre"][i], ("balanse", r, i + 1)
        acc += s["lager"][i] * 0.5 + s["restordre"][i] * 1.0
        assert abs(acc - s["kost_sum"][i]) < 1e-9, ("kost", r, i + 1)
        assert abs(wcost(net) - S.wc(i + 1)) < 1e-9
    assert abs(acc - FX["spill17"]["kost_per_rolle"][r]) < 1e-9
assert abs(sum(FX["spill17"]["kost_per_rolle"].values()) - FX["spill17"]["kjedekost"]) < 1e-9

# 2. Hvert tall i matrisene mot loggen
G = Seat("Grossist")
expect = {
    "Lager": lambda r, k: log[r]["lager"][k - 1],
    "Restordre": lambda r, k: log[r]["restordre"][k - 1],
    "Lagerkostnad": lambda r, k: log[r]["lager"][k - 1] * 0.5,
    "Restordrekostnad": lambda r, k: log[r]["restordre"][k - 1] * 1.0,
    "Uka kostet": lambda r, k: log[r]["lager"][k - 1] * 0.5 + log[r]["restordre"][k - 1],
    "Ukekost": lambda r, k: log[r]["lager"][k - 1] * 0.5 + log[r]["restordre"][k - 1],
    "Totalkostnad": lambda r, k: log[r]["kost_sum"][k - 1],
    "Ordre inn": lambda r, k: log[r]["innkommende_ordre"][k - 1],
    "Levering": lambda r, k: log[r]["levering"][k - 1],
    "På vei": lambda r, k: log[r]["paa_vei"][k - 1],
    "Din ordre": lambda r, k: (24 if k == 11 else log[r]["ordre"][k - 1]),
    "Sendt": lambda r, k: Seat(r).sendt(k),
}
bad = 0
for src, role, k, lab, v in K3.DRAWN:
    want = expect[lab](role, k)
    if abs(want - v) > 1e-9:
        print("AVVIK", src, role, k, lab, v, want)
        bad += 1
print(f"kontrollert {len(K3.DRAWN)} matrisetall mot loggen, avvik: {bad}")
# Saras tastede 24 i Uke 11 er det som faktisk står i loggen
assert log["Grossist"]["ordre"][10] == 24
if bad:
    sys.exit(1)
