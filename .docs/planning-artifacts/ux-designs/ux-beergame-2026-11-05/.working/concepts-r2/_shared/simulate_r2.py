"""Richer synthetic data for round 2. Same rules as PRD FR-11 and FR-26.

Reuses game 17 from round 1 (verified by re-running the same policy), and adds:
references for Sara's Seat, a counterfactual, Sara's Replay, 60 Class games with real
week-by-week series, class distributions and last year's Class session.
Output: fixture.json next to this file.
"""
import json
import random
import statistics
from pathlib import Path

ROLES = ["Detaljist", "Grossist", "Distributør", "Fabrikk"]
HOLD, BACK = 0.5, 1.0
ROUND1 = Path(__file__).resolve().parents[2] / "concepts" / "_shared" / "fixture.json"


def step_demand(week):
    return 4 if week < 5 else 8


class Heuristic:
    """Anchoring and adjustment with a weak supply-line weight. Round 1's player, and the student stand-in."""

    def __init__(self, theta=0.35, alpha_s=0.35, alpha_sl=0.22, s_target=12, sl_target=16, noise=0.8):
        self.theta, self.alpha_s, self.alpha_sl = theta, alpha_s, alpha_sl
        self.s_target, self.sl_target, self.noise = s_target, sl_target, noise

    def observe(self, seat):
        seat["exp"] = self.theta * seat["inc"] + (1 - self.theta) * seat["exp"]

    def order(self, seat, rng, week):
        stock_gap = self.s_target - (seat["inv"] - seat["back"])
        sl_gap = self.sl_target - seat["supply"]
        return seat["exp"] + self.alpha_s * stock_gap + self.alpha_sl * sl_gap + rng.gauss(0, self.noise)


class SupplyAware:
    """Counts everything on the way: orders up to a position scaled by expected demand.

    Reference only. Not a recommendation shown to students while they play.
    """

    def __init__(self, theta=0.1, adjust=0.25, safety=12, lead=4):
        self.theta, self.adjust, self.safety, self.lead = theta, adjust, safety, lead

    def observe(self, seat):
        seat["exp"] = self.theta * seat["inc"] + (1 - self.theta) * seat["exp"]

    def order(self, seat, rng, week):
        target = seat["exp"] * self.lead + self.safety
        position = seat["inv"] - seat["back"] + seat["supply"]
        return seat["exp"] + self.adjust * (target - position)


def run(policies, weeks=36, guided=4, demand=step_demand, seed=17, forced=None, stop_week=None):
    """Run one Game. policies: four players by Role. forced: {(role_index, week): order}."""
    rng = random.Random(seed)
    forced = forced or {}
    seats = [{"inv": 12, "back": 0, "exp": 4.0, "supply": 16, "inc": 4} for _ in range(4)]
    ship_in = [[4, 4] for _ in range(4)]
    order_in = [[4, 4] for _ in range(3)]
    prod = [4, 4]
    fac_order_in = [4, 4]
    total = [0.0] * 4
    rows = []
    for w in range(1, weeks + 1):
        if stop_week and w > stop_week:
            break
        inc = [demand(w)] + [order_in[i][0] for i in range(3)]
        delivered = [ship_in[i][0] for i in range(3)] + [prod[0]]
        shipped = [0] * 4
        for i, seat in enumerate(seats):
            seat["inc"] = inc[i]
            seat["inv"] += delivered[i]
            seat["supply"] -= delivered[i]
            due = seat["back"] + inc[i]
            shipped[i] = min(seat["inv"], due)
            seat["inv"] -= shipped[i]
            seat["back"] = due - shipped[i]
        orders = [0] * 4
        for i, seat in enumerate(seats):
            policies[i].observe(seat)
            orders[i] = 4 if w <= guided else max(0, round(policies[i].order(seat, rng, w)))
            if (i, w) in forced:
                orders[i] = forced[(i, w)]
        row = {"week": w, "demand": demand(w), "seats": {}}
        for i, seat in enumerate(seats):
            on_way = seat["supply"]
            seat["supply"] += orders[i]
            cost = seat["inv"] * HOLD + seat["back"] * BACK
            total[i] += cost
            row["seats"][ROLES[i]] = {
                "lager": seat["inv"], "restordre": seat["back"], "innkommende_ordre": inc[i],
                "levering": delivered[i], "sendt": shipped[i], "ordre": orders[i],
                "paa_vei_foer_ordre": on_way, "ukekost": cost, "kost_sum": total[i],
            }
        for i in range(3):
            ship_in[i] = [ship_in[i][1], shipped[i + 1]]
            order_in[i] = [order_in[i][1], orders[i]]
        prod = [prod[1], fac_order_in[0]]
        fac_order_in = [fac_order_in[1], orders[3]]
        rows.append(row)
    return rows


def series(rows, role, key):
    return [r["seats"][role][key] for r in rows]


def amplification(rows, demand_values=None):
    demand_values = demand_values or [r["demand"] for r in rows]
    sd = statistics.pstdev(demand_values) or 1
    return {role: round(statistics.pstdev(series(rows, role, "ordre")) / sd, 1) for role in ROLES}


def costs(rows):
    last = rows[-1]["seats"]
    return {role: last[role]["kost_sum"] for role in ROLES}


def compact(rows):
    """The series a chart needs, per Role."""
    out = {"demand": [r["demand"] for r in rows]}
    for role in ROLES:
        out[role] = {
            "ordre": series(rows, role, "ordre"),
            "lager": series(rows, role, "lager"),
            "restordre": series(rows, role, "restordre"),
            "innkommende_ordre": series(rows, role, "innkommende_ordre"),
            "levering": series(rows, role, "levering"),
            "paa_vei": series(rows, role, "paa_vei_foer_ordre"),
            "kost_sum": series(rows, role, "kost_sum"),
        }
    return out


# Sara's own Orders in game 17: holds at 4, then 8 and the 24 from PRD UJ-5.
SARA = {(1, w): 4 for w in range(5, 10)}
SARA.update({(1, 10): 8, (1, 11): 24})

game17 = run([Heuristic() for _ in ROLES], forced=SARA)
original = json.loads(ROUND1.read_text(encoding="utf-8"))
assert sum(costs(game17).values()) == original["chain_total_cost"], "engine no longer reproduces round 1"
assert game17[10]["seats"]["Grossist"]["paa_vei_foer_ordre"] == 16

# What happens to the same chain if only Sara counts what is on the way from Week 5.
counterfactual = run([Heuristic(), SupplyAware(), Heuristic(), Heuristic()])
# The chain if everyone counts what is on the way.
reference = run([SupplyAware() for _ in ROLES])

# Sara's Replay: random demand around the same levels, spread 2 (FR-49), step in Week 8, 33 Weeks, no Guided Weeks.
replay_rng = random.Random(4242)
replay_demand = [(replay_rng.randint(2, 6) if w < 8 else replay_rng.randint(6, 10)) for w in range(1, 34)]
replay = run([Heuristic(noise=0.5), Heuristic(alpha_sl=0.42, noise=0.6), Heuristic(noise=0.5), Heuristic(noise=0.5)],
             weeks=33, guided=0, demand=lambda w: replay_demand[w - 1], seed=4242)

# 60 Class games, same statuses as round 1 (UJ-7), each with real series up to its current Week.
class_games = []
for meta in original["class_games"]:
    n = meta["spill"]
    rng = random.Random(1000 + n)
    players = [Heuristic(theta=rng.uniform(0.25, 0.5), alpha_s=rng.uniform(0.2, 0.55), alpha_sl=rng.uniform(0.05, 0.4),
                         noise=rng.uniform(0.4, 1.3)) for _ in ROLES]
    if n == 17:
        rows = game17
    else:
        rows = run(players, seed=2000 + n)
    week = meta["uke"]
    rows = rows[:week]
    cost = round(sum(costs(rows).values()))
    entry = {k: v for k, v in meta.items() if k != "kjedekost"}
    entry["kjedekost"] = cost
    entry["ordre"] = {role: series(rows, role, "ordre") for role in ROLES}
    entry["netto_lager"] = {role: [a - b for a, b in zip(series(rows, role, "lager"), series(rows, role, "restordre"))]
                            for role in ROLES}
    if meta["status"] == "ferdig":
        entry["forsterkning"] = amplification(rows)
        entry["kost_per_rolle"] = costs(rows)
    class_games.append(entry)

finished = [g for g in class_games if g["status"] == "ferdig"]


def quartiles(values):
    q = statistics.quantiles(values, n=4)
    return {"min": min(values), "q1": round(q[0], 1), "median": round(q[1], 1), "q3": round(q[2], 1), "max": max(values)}


result = {
    "note": "Syntetiske demodata fra simulate_r2.py med PRD FR-11-standarder. Merk som demodata i konseptene.",
    "spill17": {
        "forsterkning": amplification(game17), "kost_per_rolle": costs(game17),
        "kjedekost": sum(costs(game17).values()), "serier": compact(game17),
    },
    "bare_sara_teller_paa_vei": {
        "merknad": "Simulert: samme kjede, men Grossist regner med alt som er på vei fra Uke 5. Viser sammenhengen, ikke et fasitsvar.",
        "forsterkning": amplification(counterfactual), "kost_per_rolle": costs(counterfactual),
        "kjedekost": sum(costs(counterfactual).values()), "serier": compact(counterfactual),
    },
    "alle_teller_paa_vei": {
        "merknad": "Simulert referanse: alle fire regner med alt som er på vei.",
        "forsterkning": amplification(reference), "kost_per_rolle": costs(reference),
        "kjedekost": sum(costs(reference).values()), "serier": compact(reference),
    },
    "replay_sara": {
        "merknad": "Saras Replay: same Rolle, tre KI-spillere, tilfeldig etterspørsel, 33 uker. Ikke like for like med Klassespillet.",
        "etterspoersel": replay_demand, "forsterkning": amplification(replay, replay_demand),
        "kost_per_rolle": costs(replay), "kjedekost": sum(costs(replay).values()), "serier": compact(replay),
    },
    "klasse": {
        "spill": class_games,
        "ferdige": {
            "antall": len(finished),
            "kjedekost": quartiles([g["kjedekost"] for g in finished]),
            "forsterkning_per_rolle": {r: quartiles([g["forsterkning"][r] for g in finished]) for r in ROLES},
        },
        "traktA": original["funnel"],
        "roster": original["roster"],
        "moenstre": {
            "Stor ordre mens mye allerede er på vei": 212,
            "Ordre langt over innkommende ordre etter mangel": 174,
            "Svært lave ordre etter overskudd": 139,
        },
        "fjoraaret": {"klasse": "class-of-1993", "median_kjedekost": 2740, "median_forsterkning_fabrikk": 6.9, "spill": 58},
    },
}
out = Path(__file__).with_name("fixture.json")
out.write_text(json.dumps(result, ensure_ascii=False, indent=None, separators=(",", ":")), encoding="utf-8")

for name in ["spill17", "bare_sara_teller_paa_vei", "alle_teller_paa_vei", "replay_sara"]:
    block = result[name]
    print(name, "kjede", block["kjedekost"], "forst", block["forsterkning"], "per rolle", block["kost_per_rolle"])
print("Fabrikk ordre spill17", block and result["spill17"]["serier"]["Fabrikk"]["ordre"])
print("alle teller, Fabrikk ordre", result["alle_teller_paa_vei"]["serier"]["Fabrikk"]["ordre"])
print("bare Sara, Grossist ordre", result["bare_sara_teller_paa_vei"]["serier"]["Grossist"]["ordre"])
print("ferdige", result["klasse"]["ferdige"]["kjedekost"], result["klasse"]["ferdige"]["forsterkning_per_rolle"]["Fabrikk"])
print("størrelse KB", out.stat().st_size // 1024)
