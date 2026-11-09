"""Synthetic game 17 for the design concepts. Rules and defaults from PRD FR-11 and FR-26.

Week sequence: delivery and incoming order arrive, fill orders and backlog, ship;
Seats place Orders; costs charged on end-of-Week balances; slots advance.
Sara (Grossist) places 24 in Week 11 (PRD UJ-5). Output: fixture.json next to this file.
"""
import json
import random
import statistics
from pathlib import Path

ROLES = ["Detaljist", "Grossist", "Distributør", "Fabrikk"]
WEEKS, GUIDED, HOLD, BACK = 36, 4, 0.5, 1.0
THETA, ALPHA_S, ALPHA_SL, S_TARGET, SL_TARGET = 0.35, 0.35, 0.22, 12, 16


def demand(week):
    return 4 if week < 5 else 8


def simulate(seed=17):
    rng = random.Random(seed)
    inv, back = [12] * 4, [0] * 4
    ship_in = [[4, 4] for _ in range(4)]    # arrives in week+1, week+2 (shipping delay 2)
    order_in = [[4, 4] for _ in range(3)]   # orders travelling up to Seat i+1 (order delay 2)
    prod = [4, 4]                           # Factory production pipeline (production delay 2)
    fac_order_in = [4, 4]                   # Factory Order travelling to production (order delay 2)
    expected = [4.0] * 4
    supply = [16, 16, 16, 16]
    rows, total = [], [0.0] * 4

    for w in range(1, WEEKS + 1):
        row = {"week": w, "demand": demand(w), "seats": {}}
        inc_order = [demand(w)] + [order_in[i][0] for i in range(3)]
        delivered = [ship_in[i][0] for i in range(3)] + [prod[0]]
        shipped = [0] * 4
        for i in range(4):
            inv[i] += delivered[i]
            supply[i] -= delivered[i]
            due = back[i] + inc_order[i]
            shipped[i] = min(inv[i], due)
            inv[i] -= shipped[i]
            back[i] = due - shipped[i]
        orders = [0] * 4
        for i in range(4):
            expected[i] = THETA * inc_order[i] + (1 - THETA) * expected[i]
            if w <= GUIDED:
                orders[i] = 4
            else:
                stock_gap = S_TARGET - (inv[i] - back[i])
                sl_gap = SL_TARGET - supply[i]
                raw = expected[i] + ALPHA_S * stock_gap + ALPHA_SL * sl_gap + rng.gauss(0, 0.8)
                orders[i] = max(0, round(raw))
        # PRD UJ-5: Sara holds at 4 until shortage, then orders 24 with 16 already on the way.
        if 5 <= w <= 9:
            orders[1] = 4
        if w == 10:
            orders[1] = 8
        if w == 11:
            orders[1] = 24
        for i in range(4):
            on_the_way = supply[i]
            supply[i] += orders[i]
            cost = inv[i] * HOLD + back[i] * BACK
            total[i] += cost
            next_delivery = ship_in[i][1] if i < 3 else prod[1]
            row["seats"][ROLES[i]] = {
                "lager": inv[i], "restordre": back[i], "innkommende_ordre": inc_order[i],
                "levering": delivered[i], "sendt": shipped[i], "ordre": orders[i],
                "paa_vei_foer_ordre": on_the_way, "neste_levering": next_delivery,
                "ukekost": cost, "kost_sum": total[i],
            }
        # advance slots
        for i in range(3):
            ship_in[i] = [ship_in[i][1], shipped[i + 1]]
        for i in range(3):
            order_in[i] = [order_in[i][1], orders[i]]
        prod = [prod[1], fac_order_in[0]]
        fac_order_in = [fac_order_in[1], orders[3]]
        rows.append(row)
    return rows


rows = simulate()
sd_demand = statistics.pstdev([r["demand"] for r in rows])
amp = {
    role: round(statistics.pstdev([r["seats"][role]["ordre"] for r in rows]) / sd_demand, 1)
    for role in ROLES
}
last = rows[-1]["seats"]


def class_games():
    """60 Class games matching PRD UJ-7: 41 finished, 15 running (2 paused), 4 waiting."""
    rng = random.Random(1994)
    names = ["Ida", "Jonas", "Mikkel", "Sara", "Emma", "Ola", "Nora", "Elias", "Maja", "Liam", "Thea", "Noah",
             "Vilde", "Oskar", "Ingrid", "Sander", "Hanna", "Tobias", "Sofie", "Henrik", "Amalie", "Jakob"]
    status = ["ferdig"] * 41 + ["pågår"] * 13 + ["pauset"] * 2 + ["venter"] * 4
    rng.shuffle(status)
    # Game 17 is Sara's and is running in Week 11: swap a running status into its slot.
    running = next(i for i, st in enumerate(status) if st == "pågår")
    status[16], status[running] = status[running], status[16]
    games = []
    for n, st in enumerate(status, 1):
        week = 36 if st == "ferdig" else rng.randint(6, 33)
        cost = round(rng.uniform(1800, 6200) if st == "ferdig" else week * rng.uniform(30, 150))
        game = {"spill": n, "status": st, "uke": week, "kjedekost": cost}
        game["ki_seter"] = rng.choices([0, 1, 2], weights=[8, 2, 1])[0]
        if st == "venter":
            game.update(venter_paa=rng.choice(ROLES), navn=rng.choice(names), ventet_timer=rng.randint(3, 20))
        if st == "pauset":
            game["fortsetter"] = rng.choice(["torsdag 14:15", "i kveld 19:00"])
        games.append(game)
    week11 = rows[10]["seats"]
    games[16].update(uke=11, ki_seter=0, kjedekost=round(sum(week11[r]["kost_sum"] for r in ROLES)))
    # One game close to Takeover, for the highlighted state (FR-39).
    next(g for g in games if g["status"] == "venter")["ventet_timer"] = 23
    return games


result = {
    "note": "Syntetiske demodata fra simulate.py med PRD FR-11-standarder. Merk som demodata i konseptene.",
    "amplification": amp,
    "total_cost_per_role": {r: last[r]["kost_sum"] for r in ROLES},
    "chain_total_cost": sum(last[r]["kost_sum"] for r in ROLES),
    "weeks": rows,
    "class_games": class_games(),
    "funnel": {"registrert": 240, "klassespill_ferdig": 164, "debrief_ferdig": 121, "quiz_bestått": 97,
               "replay_ferdig": 58, "test_levert": 12, "ki_vurdering_klar": 0},
    "roster": {"paa_lista": 250, "registrert": 238, "manuelt_registrert": 2, "uregistrert": 10, "ugyldige_rader": 4},
}
Path(__file__).with_name("fixture.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")

w = rows[10]["seats"]["Grossist"]
print("WEEK 11 Grossist:", w)
print("WEEK 11 all:", rows[10]["seats"])
import collections
print("status:", collections.Counter(g["status"] for g in result["class_games"]))
print("g17:", result["class_games"][16], "waiting:", [g for g in result["class_games"] if g["status"]=="venter"], "paused:", [g for g in result["class_games"] if g["status"]=="pauset"])
print("Grossist orders:", [r["seats"]["Grossist"]["ordre"] for r in rows])
print("Detaljist orders:", [r["seats"]["Detaljist"]["ordre"] for r in rows])
print("Distributor orders:", [r["seats"]["Distributør"]["ordre"] for r in rows])
print("Fabrikk orders:", [r["seats"]["Fabrikk"]["ordre"] for r in rows])
print("Grossist lager:", [r["seats"]["Grossist"]["lager"] for r in rows])
print("Grossist restordre:", [r["seats"]["Grossist"]["restordre"] for r in rows])
print("amp:", amp, "costs:", result["total_cost_per_role"], "chain:", result["chain_total_cost"])
