"""07 debrief og 08 lærerens oversikt."""
from statistics import median

from screens_core import *

KL = FX["klasse"]
B = FX["bare_sara_teller_paa_vei"]
A = FX["alle_teller_paa_vei"]
ALL17 = [states(w) for w in range(1, 37)]


def sec_title(d, x, y, n, title, width):
    """Stegnummeret bærer rekkefølgen i Debriefen."""
    d.line(x, y - 26, x + width, y - 26, INK, 1.2)
    d.t(x, y, str(n), 22, 700, INK)
    return d.para(x + 24, y, title, width - 24, 22, 27, 600, INK)


def demand_band(d, ax, y0, h, scale, dem=DEM):
    u = h / scale
    base = y0 + h
    n = len(dem)
    dd = f"M{ax.xl(1):.1f} {base:.1f}"
    for w in range(1, n + 1):
        v = dem[w - 1]
        dd += f" L{ax.xl(w):.1f} {base - v * u:.1f} L{ax.xr(w):.1f} {base - v * u:.1f}"
    dd += f" L{ax.xr(n):.1f} {base:.1f} Z"
    d.path(dd, BLUEF)
    d.line(ax.xl(1), base, ax.xr(n), base, HAIR2, 1)


def split(S, upto=36):
    return sum(S.lager[:upto]) * LK, sum(S.rest[:upto]) * RK


def order_rows(src=SEATS, dem=DEM):
    rows = []
    for r in CHAIN:
        S = src[r]
        rows.append({"label": r, "vals": S.order, "kind": "seq", "role": r})
    rows.append({"label": "Kundene", "vals": lambda k: dem[k - 1], "kind": "seq", "role": "Kunde"})
    return rows


def net_rows(src=SEATS, sub=True):
    return [{"label": r, "sub": (NAVN[r] if sub else None), "vals": src[r].net, "kind": "div", "role": r} for r in CHAIN]


# ---------- 07 ----------
def build_07():
    d = Doc("07-debrief", 2100, 1200, f"{NAME}, Gruppedebrief i fem steg",
            "Forklaring, avsløring av etterspørselen, hele kjeden med fire ledd og ukeskrubber over matrisen Rolle × uke, ditt øyeblikk i Uke 11 med kjedens kostnad, og quiz. Delt skjerm med kjeden.")
    d.t(40, 44, "Debrief, Spill 17: fra «hadde jeg rett?» til «hvorfor skjedde det?»", 28, 600, INK)

    # Steg 1
    x, w = 40, 330
    y = 104
    sec_title(d, x, y, 1, "Skriv Forklaringen først", w)
    d.t(x, y + 32, "Ditt netto lager, hele spillet", 14, 600, INK)
    ax = Axis(x + 30, w - 30, 1, 36)
    grid(d, ax, y + 42, 96, -40, 30, (-40, 0, 20), 13)
    net_area(d, ax, y + 42, 96, G.net, 1, 36)
    xaxis(d, ax, y + 156, [1, 12, 24, 36])
    d.t(x, y + 192, "Hvorfor svingte lageret ditt?", 15, 600, INK)
    d.rect(x, y + 202, w, 112, PAPER, HAIR2, 1, 6)
    d.para(x + 12, y + 226, "Restordren vokste, så jeg bestilte mye for å ta den igjen. Det som var på vei, regnet jeg lite med.", w - 24, 15, 20)
    d.button(x, y + 324, w, 44, "Send Forklaring", size=15)
    d.circle(x + 7, y + 391, 5, PAPER, INK, 1.5)
    d.para(x + 20, y + 396, "Avsløringen er låst til alle fire har sendt. Ida og Mikkel har sendt, Jonas skriver.", w - 20, 14, 19, fill=INK2)
    d.para(x, y + 460, "Kjeden og kostnaden til de andre er skjult til dere har sendt. Da åpnes steg 2.", w, 14, 19, fill=INK2)

    # Steg 2: klimaks
    x2, w2 = 410, 560
    sec_title(d, x2, y, 2, "Kundene kjøpte 4, så 8. Etter det endret de seg aldri.", w2)
    ax2 = Axis(x2 + 28, w2 - 28, 1, 36)
    y0 = y + 52
    h = 330
    scale = 26
    u = h / scale
    for v in (0, 8, 16, 24):
        yy = y0 + h - v * u
        d.line(ax2.x0, yy, ax2.x1, yy, HAIR, 1)
        d.t(ax2.x0 - 5, yy + 4, v, 13, 400, INK3, "end")
    demand_band(d, ax2, y0, h, scale)
    bw = 4.5
    for k in range(1, 37):
        d.rect(ax2.xc(k) - bw / 2, y0 + h - G.order(k) * u, bw, G.order(k) * u, INK)
    d.path("M" + " L".join(f"{ax2.xc(k):.1f} {y0 + h - G.inn(k) * u:.1f}" for k in range(1, 37)), stroke=GREY, sw=1.6)
    d.t(ax2.xc(11) + 8, y0 + h - 24 * u + 12, "Din ordre, 24 i Uke 11", 15, 600, INK)
    d.t(ax2.xc(29.5), y0 + h - 8 * u - 10, "Kundene: 8", 16, 700, INK, "middle", 'stroke="#FFFFFF" stroke-width="4" paint-order="stroke"')
    d.t(ax2.xc(2.5), y0 + h - 4 * u - 8, "4", 18, 700, INK, "middle")
    d.t(ax2.xc(18) + 6, y0 + h - 13.5 * u, "Ordre inn: det eneste du så", 15, 600, INK2)
    xaxis(d, ax2, y0 + h + 18, [1, 5, 10, 15, 20, 25, 30, 36], None)
    d.para(x2, y0 + h + 44, "Øvelsen heter Beer Game. Nesten alle grupper svinger slik, også i år. Det du så, var Idas ordrer, ikke kundene. Struktur gir atferd, derfor spør vi hvorfor og ikke hvem.", w2, 15, 20, fill=INK)
    d.t(x2, y0 + h + 112, "P4, P6", 13, 400, INK3)

    # Steg 3: hele kjeden, skrubber, matrise
    x3, w3 = 1010, 1050
    sec_title(d, x3, y, 3, "Hele kjeden, uke for uke. Spol, og se beholdningene vokse og krympe.", w3)
    sel = 15
    c = chain4(d, x3, y + 26, w3, ALL17[sel - 1], u=0.85, fit=ALL17, customer=DEM[sel - 1], cost=True, ls=13)
    ax3 = Axis(x3 + 112, w3 - 112 - 64, 1, 36)
    ys = c["bottom"] + 22
    scrub_controls(d, x3, ys)
    scrubber(d, ax3, ys, sel)
    d.t(ax3.x1 + 64, ys + 5, "Forsterkning", 12, 600, INK2, "end")
    # Ordrene som graf og som tall, på samme tidsakse
    yg = ys + 30
    gh = 96
    Yg = lambda v: yg + gh - v * gh / 32
    for v in (0, 10, 20, 30):
        d.line(ax3.x0, Yg(v), ax3.x1, Yg(v), HAIR2 if v == 0 else HAIR, 1)
        d.t(ax3.x0 - 6, Yg(v) + 4, v, 12, 400, INK3, "end")
    d.t(x3, yg + 12, "Ordre, alle fire", 13, 600, INK)
    d.t(x3, yg + 29, "samme skala", 12, 400, INK2)
    shade = {"Fabrikk": BASE, "Distributør": ORD, "Detaljist": GREY, "Grossist": INK}
    for r in ["Detaljist", "Fabrikk", "Distributør", "Grossist"]:
        S = SEATS[r]
        d.path("M" + " L".join(f"{ax3.xc(k):.1f} {Yg(S.order(k)):.1f}" for k in range(1, 37)),
               stroke=shade[r], sw=2.2 if r == "Grossist" else 1.6)
        pk = max(range(1, 37), key=lambda k: S.order(k))
        if r != "Detaljist":
            d.t(ax3.xc(pk) + 6, Yg(S.order(pk)) + 4, f"{r} {S.order(pk)}", 12, 600, INK)
    d.t(ax3.xc(30), Yg(10) - 4, "Detaljist", 12, 600, INK, "middle")
    d.line(ax3.xl(sel), yg - 4, ax3.xl(sel), yg + gh, INK, 1)
    d.line(ax3.xr(sel), yg - 4, ax3.xr(sel), yg + gh, INK, 1)
    ym = yg + gh + 10
    onset = {}

    def fz(row, yy, hh):
        if row["role"] in K["forsterkning"]:
            d.t(ax3.x1 + 64, yy + hh / 2 + 6, fx1(K["forsterkning"][row["role"]]), 17, 700, INK, "end",
                'style="font-variant-numeric:lining-nums proportional-nums"')
            S = SEATS[row["role"]]
            onset[row["role"]] = (next(k for k in range(1, 37) if S.order(k) >= 10), yy + hh / 2)

    ye = matrix(d, ax3, ym, order_rows(), ch=24, sel=sel, ls=11.5, right=fz, label_x=x3 + 104)
    pts = [(ax3.xc(onset[r][0]), onset[r][1]) for r in CHAIN]
    for r in CHAIN:
        k, yy = onset[r]
        d.rect(ax3.xl(k) + 0.5, yy - 11, ax3.slot - 1, 21, "none", RED, 1.6)
    d.para(x3 + 112, ye + 22, "Rød ramme: første Uke med ordre på 10 eller mer, Uke " + ", ".join(str(onset[r][0]) for r in reversed(CHAIN)) +
           ". Svingningen vokser og kommer senere for hvert ledd. Tallet til høyre er Forsterkning. P5.", w3 - 112, 14, 19, fill=INK2)

    # Rad 2
    yb = 760
    # Steg 4
    x4, w4 = 40, 1120
    sec_title(d, x4, yb, 4, "Ditt øyeblikk: Uke 11. Du bestilte 24 med 16 på vei.", w4)
    d.t(x4, yb + 30, "Dette så hver av dere i Uke 11", 15, 600, INK)
    s11 = states(11)
    c4 = chain4(d, x4, yb + 46, 600, s11, u=1.2, fit=[s11], customer=DEM[10], cost=False, ls=12)
    tx, tw = x4, 290
    ty = c4["bottom"] + 26
    d.t(tx, ty, "Dette regnet du", 15, 600, INK)
    ny = d.para(tx, ty + 22, f"Posisjon {G.lager[10]} − {G.rest[10]} + {G.paavei(11)} = {G.posisjon(11)}. Med 24 ble den {G.posisjon(11) + 24}.", tw, 14, 19)
    late = G.kostsum(36) - G.kostsum(24)
    d.t(tx + tw + 20, ty, "Dette kostet det senere", 15, 600, INK)
    d.para(tx + tw + 20, ty + 22, f"{G.levering(15)} av de 24 kom i Uke 15. På vei toppet på {max(G.pv)} i Uke {G.pv.index(max(G.pv)) + 1}. Lager i Uke 25 til 36 kostet {nf(late)} kr.", tw, 14, 19)
    d.para(tx, ty + 92, "KI-generert, kan ta feil: «Du reagerte på restordren du så, ikke på posisjonen. Mikkel fikk 24 fra deg i Uke 13 uten å vite hvorfor.»", 600, 14, 19, fill=INK2)

    # Kjedens kostnad
    kx, kw = x4 + 650, 470
    d.t(kx, yb + 30, f"Kjeden betalte {nf(K['kjedekost'])} kr", 18, 700, INK)
    d.t(kx, yb + 52, f"Simulert referanse, alle fire teller det som er på vei: {nf(A['kjedekost'])} kr. Ingen fasit.", 13, 400, INK2)
    cmax = max(K["kost_per_rolle"].values())
    bx0 = kx + 104
    bwid = kw - 104 - 132
    yy = yb + 86
    d.t(bx0, yy - 8, "Lager", 12, 600, INK2)
    d.t(bx0 + 52, yy - 8, "Restordre", 12, 600, INK2)
    d.t(kx + kw, yy - 8, "Simulert", 12, 600, INK2, "end")
    tot_l = tot_r = 0
    for r in CHAIN:
        cl, cr = split(SEATS[r])
        tot_l += cl
        tot_r += cr
        sl, sr = split(SIM[r])
        assert abs(sl + sr - A["kost_per_rolle"][r]) < 1e-6
        d.t(kx, yy + 13, r, 14, 700 if r == "Grossist" else 400, INK)
        cost_bar(d, bx0, yy + 2, bwid, cl, cr, cmax, 14)
        xs_ = bx0 + bwid * (sl + sr) / cmax
        d.line(xs_, yy - 2, xs_, yy + 20, INK, 1.4, dash="2 2")
        d.t(bx0 + bwid * (cl + cr) / cmax + 6, yy + 14, nf(cl + cr), 13, 600, INK)
        d.t(kx + kw, yy + 14, nf(sl + sr), 13, 400, INK2, "end")
        yy += 30
    assert abs(tot_l + tot_r - K["kjedekost"]) < 1e-6
    d.line(kx, yy - 4, kx + kw, yy - 4, HAIR2, 1)
    d.t(kx, yy + 16, "Kjeden", 14, 700, INK)
    d.t(bx0, yy + 16, f"lager {nf(tot_l)} + restordre {nf(tot_r)} = {nf(tot_l + tot_r)}", 13, 600, INK)
    d.t(kx + kw, yy + 16, nf(A["kjedekost"]), 13, 400, INK2, "end")
    d.para(kx, yy + 40, f"Stiplet strek: simulert kostnad per Rolle. {nf(tot_r / (tot_l + tot_r) * 100, 0)} % av regningen var restordre, som koster det dobbelte. P8.", kw, 13, 17, fill=INK2)
    # akkumulert kjedekost over tid
    yk = yy + 104
    axk = Axis(kx + 40, kw - 110, 1, 36)
    hk = 84
    Yk = yscale(yk, hk, 0, 2400)
    for v in (0, 1000, 2000):
        d.line(axk.x0, Yk(v), axk.x1, Yk(v), HAIR2 if v == 0 else HAIR, 1)
        d.t(axk.x0 - 6, Yk(v) + 4, nf(v, 0), 11.5, 400, INK3, "end")
    accL = [sum(sum(SEATS[r].lager[:k]) * LK for r in CHAIN) for k in range(1, 37)]
    accR = [sum(sum(SEATS[r].rest[:k]) * RK for r in CHAIN) for k in range(1, 37)]
    accS = [sum(SIM[r].kostsum(k) for r in CHAIN) for k in range(1, 37)]
    pl = [(axk.xc(k), Yk(accL[k - 1])) for k in range(1, 37)]
    pt = [(axk.xc(k), Yk(accL[k - 1] + accR[k - 1])) for k in range(1, 37)]
    d.path("M" + " L".join(f"{a:.1f} {b:.1f}" for a, b in pl) + f" L{axk.xc(36):.1f} {Yk(0):.1f} L{axk.xc(1):.1f} {Yk(0):.1f} Z", BLUEF)
    d.path("M" + " L".join(f"{a:.1f} {b:.1f}" for a, b in pt) + " L" + " L".join(f"{a:.1f} {b:.1f}" for a, b in reversed(pl)) + " Z", REDF)
    d.path("M" + " L".join(f"{a:.1f} {b:.1f}" for a, b in pt), stroke=INK, sw=1.6)
    d.path("M" + " L".join(f"{axk.xc(k):.1f} {Yk(accS[k - 1]):.1f}" for k in range(1, 37)), stroke=INK, sw=1.2, dash="4 3")
    d.t(axk.x1 + 6, Yk(accL[-1] + accR[-1]) + 4, f"Spill 17 {nf(accL[-1] + accR[-1], 0)}", 12, 600, INK)
    d.t(axk.x1 + 6, Yk(accS[-1]) + 4, f"Simulert {nf(accS[-1], 0)}", 12, 400, INK2)
    d.t(axk.xc(33), Yk(accL[32] + accR[32] * 0.85) + 4, "Restordre", 12, 600, INK, "end")
    d.t(axk.xc(31), Yk(accL[30] / 2) + 4, "Lager", 12, 600, INK, "middle")
    xaxis(d, axk, yk + hk + 15, [1, 12, 24, 36], None, 11.5)
    d.t(kx, yk - 12, "Kjedens kostnad, akkumulert", 13, 600, INK)

    # Steg 5
    x5, w5 = 1200, 400
    sec_title(d, x5, yb, 5, "Debrief-quiz", w5)
    ny = d.para(x5, yb + 34, f"Uke 11: lager {G.lager[10]}, restordre {G.rest[10]}, {G.paavei(11)} på vei. Hva er posisjonen før du bestiller?", w5, 16, 22, 600)
    opts = [(sg(-13), "wrong"), (str(G.posisjon(11)), "right"), ("16", None), ("29", None)]
    yy = ny + 6
    for lab, st in opts:
        col = RED if st == "wrong" else (INK if st == "right" else HAIR2)
        d.rect(x5, yy, w5, 40, PAPER, col, 1.4 if st else 1, 6)
        d.t(x5 + 14, yy + 26, lab, 16, 600, INK)
        if st == "wrong":
            d.t(x5 + w5 - 14, yy + 26, "Ditt svar, ikke riktig", 14, 600, RED, "end")
        if st == "right":
            d.t(x5 + w5 - 14, yy + 26, "Riktig", 14, 600, INK, "end")
        yy += 48
    ny = d.para(x5, yy + 10, "−13 er lager minus restordre. Da mangler det du allerede har bestilt: 0 − 13 + 16 = 3.", w5, 15, 20)
    ny = d.para(x5, ny + 6, "I kjeden er det de tre åpne boksene i røret foran deg.", w5, 14, 19, fill=INK2)
    d.t(x5, ny + 14, "P3", 13, 400, INK3)

    # Delt skjerm
    xs, ws = 1640, 420
    sec_title(d, xs, yb, " ", "Delt skjerm: kjeden over matrisen", ws)
    fy = yb + 14
    s18 = ALL17[17]
    top = len(d.b)
    cs = chain4(d, xs + 12, fy + 16, ws - 24, s18, u=0.42, fit=ALL17, customer=None, cost=True, cost_label=False, ls=10.5,
                pv_label=False, orders=False, sub_names=False, frame_me=False)
    axs = Axis(xs + 80, ws - 96, 1, 36)
    ysc = cs["bottom"] + 16
    scrubber(d, axs, ysc, 18, ls=10.5, step=6)
    yem = matrix(d, axs, ysc + 24, net_rows(sub=False), ch=14, sel=18, ls=10, numbers=False, label_x=xs + 72, gap=0.8)
    legend_div(d, xs + 12, yem + 12, ls=10.5)
    fh = yem + 40 - fy
    d.b.insert(top, f'<rect x="{xs}" y="{fy}" width="{ws}" height="{fh}" fill="{PAPER}" stroke="{HAIR2}" stroke-width="1.4" rx="8"/>')
    d.para(xs, fy + fh + 24, "Netto lager uke for uke, Fabrikk øverst. Gruppa spoler sammen på storskjermen, og hver student har tallene på telefonen. Uten farge: trykk for tabell.", ws, 14, 19, fill=INK2)
    d.demodata(2060, 1188, "Demodata. Simulerte tall er merket Simulert.", 13, "end")
    d.save()


# ---------- 08 ----------
def class_state(w, spill=None):
    """Klassens kjede i Uke w: median netto lager og median ordre per Rolle over spill som har nådd w,
    og klassens samlede kostnad til og med w, delt på lager og restordre."""
    games = [sp for sp in (spill or KL["spill"]) if sp["uke"] >= w]
    out = {}
    for r in ROLES:
        nets = [sp["netto_lager"][r][w - 1] for sp in games]
        cl = sum(max(v, 0) * LK for sp in games for v in sp["netto_lager"][r][:w])
        cr = sum(max(-v, 0) * RK for sp in games for v in sp["netto_lager"][r][:w])
        out[r] = {"net": int(round(median(nets))), "order": int(round(median(sp["ordre"][r][w - 1] for sp in games))),
                  "cl": cl, "cr": cr, "cost": cl + cr, "pipe": None}
    return out, len(games)


def class_week_costs():
    """Klassens kostnad per uke, delt på lager og restordre, summert over alle spill som har nådd uka."""
    res = []
    for w in range(1, 37):
        cl = cr = 0.0
        for sp in KL["spill"]:
            if sp["uke"] >= w:
                for r in ROLES:
                    v = sp["netto_lager"][r][w - 1]
                    cl += max(v, 0) * LK
                    cr += max(-v, 0) * RK
        res.append((cl, cr))
    return res


# Kryssjekk: klassens kostnad regnet fra netto lager stemmer med kjedekost per spill
for _sp in KL["spill"]:
    assert abs(sum(class_week_cost([_sp["netto_lager"][r][k] for r in ROLES]) for k in range(_sp["uke"])) - _sp["kjedekost"]) <= 0.5, _sp["spill"]  # kjedekost er rundet til hele kroner


def lanes(d, x, y, sp, cw, lane=4.0, gap=0.6):
    """Fire ledd per rad: Fabrikk øverst, Detaljist nederst, samme rekkefølge som kjeden."""
    for i, r in enumerate(CHAIN):
        for k, v in enumerate(sp["netto_lager"][r]):
            d.rect(x + k * cw, y + i * (lane + gap), cw + 0.15, lane, div_step(v))


def status_txt(sp):
    return {"ferdig": "Ferdig", "pågår": "Pågår", "pauset": "Pause", "venter": "Venter"}[sp["status"]]


RANK = {"venter": 0, "pauset": 1, "pågår": 2, "ferdig": 3}


def ordered_games():
    spill = KL["spill"]
    return sorted(spill, key=lambda s: (RANK[s["status"]], -(s.get("ventet_timer") or 0), -s["uke"] if s["status"] == "pågår" else s["kjedekost"]))


def build_08():
    d = Doc("08-laerer-oversikt", 1600, 1000, f"{NAME}, Oversikt for Faglærer",
            "60 Klassespill på én skjerm: klassens kjede med fire ledd og ukeskrubber, matrisen 60 spill × uker med fire ledd per rad, hvem hvert spill venter på, trakten og klassens kostnadsbilde.")
    spill = KL["spill"]
    X = 40
    d.t(X, 50, "Oversikt", 28, 700, INK)
    d.t(X + 124, 50, "class-of-1994, IBE160", 15, 400, INK2)
    counts = {k: sum(1 for s in spill if s["status"] == k) for k in ("venter", "pauset", "pågår", "ferdig")}
    assert (counts["ferdig"], counts["pågår"] + counts["pauset"], counts["pauset"], counts["venter"]) == (41, 15, 2, 4)
    d.t(1110, 50, "Spillfrist ti. 8. des", 15, 400, INK2, "end")
    yf = 84
    ki = sum(1 for s in spill if s["ki_seter"] > 0)
    labs = [("Alle", len(spill)), ("Venter", counts["venter"]), ("Pause", counts["pauset"]), ("Pågår", counts["pågår"]), ("Ferdig", counts["ferdig"]), ("Med KI-spiller", ki)]
    xx = X
    for i, (lab, c) in enumerate(labs):
        s_ = f"{lab} {c}"
        wd = text_w(s_, 14) + 22
        d.rect(xx, yf - 13, wd, 26, INK if i == 0 else PAPER, None if i == 0 else HAIR2, 1, 4)
        d.t(xx + wd / 2, yf + 5, s_, 14, 600, PAPER if i == 0 else INK, "middle")
        xx += wd + 8
    xx += 20
    d.t(xx, yf + 5, "Vis", 14, 400, INK2)
    xx += 30
    for i, lab in enumerate(("Netto lager", "Ordre", "Kostnad")):
        wd = text_w(lab, 14) + 22
        d.rect(xx, yf - 13, wd, 26, INK if i == 0 else PAPER, None if i == 0 else HAIR2, 1, 4)
        d.t(xx + wd / 2, yf + 5, lab, 14, 600, PAPER if i == 0 else INK, "middle")
        xx += wd + 8

    # Klassens kjede
    sel = 20
    cs, n = class_state(sel)
    allc = [class_state(w)[0] for w in range(1, 37)]
    yk = 132
    d.t(X, yk, f"Klassens kjede i Uke {sel}", 17, 700, INK)
    d.t(X + 214, yk, f"Median netto lager og median ordre over de {n} spillene som har nådd Uke {sel}. Kostnaden er klassens sum til og med uka.", 13, 400, INK2)
    c = chain4(d, X, yk + 18, 1070, cs, u=0.75, fit=allc, customer="", cost=True, ls=12.5, me=None, frame_me=False,
               sub_names=False, order_label="Median ordre", production=False)
    axc = Axis(X + 70, 1000, 1, 36)
    ysc = c["bottom"] + 18
    scrub_controls(d, X, ysc)
    scrubber(d, axc, ysc, sel, ls=12)

    # Matrisen: 60 spill × uker, fire ledd per rad
    ordered = ordered_games()
    near = max((s for s in spill if s["status"] == "venter"), key=lambda s: s["ventet_timer"])
    colw = 528
    yh = ysc + 46
    rowh = 17.6
    cwk = 6.6
    for cidx in range(2):
        cx = X + cidx * (colw + 14)
        mx = cx + 76
        d.t(cx, yh, "Spill", 12, 600, INK2)
        d.t(cx + 28, yh, "Status", 12, 600, INK2)
        d.t(mx, yh, "Netto lager per ledd, Uke 1 til 36", 12, 600, INK2)
        d.t(mx + 36 * cwk + 30, yh, "Uke", 12, 600, INK2, "end")
        d.t(mx + 36 * cwk + 86, yh, "Kjede, kr", 12, 600, INK2, "end")
        d.t(mx + 36 * cwk + 104, yh, "KI", 12, 600, INK2, "end")
        d.t(mx + 36 * cwk + 114, yh, "Venter på" if cidx == 0 else "Forsterkning", 12, 600, INK2)
        d.line(cx, yh + 6, cx + colw, yh + 6, HAIR2, 1)
        for i in range(30):
            sp = ordered[cidx * 30 + i]
            y = yh + 12 + i * rowh
            if sp is near:
                d.rect(cx - 4, y - 1, colw + 8, rowh, REDF, None, 1, 3)
            ty = y + rowh / 2 + 4
            d.t(cx, ty, sp["spill"], 12, 600, INK)
            d.t(cx + 28, ty, status_txt(sp), 12, 600 if sp["status"] in ("venter", "pauset") else 400, INK if sp["status"] != "ferdig" else INK2)
            lanes(d, mx, y + 1.5, sp, cwk, lane=3.4, gap=0.6)
            d.t(mx + 36 * cwk + 30, ty, sp["uke"], 12, 400, INK, "end")
            d.t(mx + 36 * cwk + 86, ty, nf(sp["kjedekost"], 0), 12, 400, INK, "end")
            d.t(mx + 36 * cwk + 104, ty, sp["ki_seter"] if sp["ki_seter"] else "", 12, 400, INK, "end")
            tx = mx + 36 * cwk + 114
            if sp["status"] == "venter":
                d.t(tx, ty, f"{sp['navn']}, {sp['ventet_timer']} t", 12, 700 if sp is near else 400, INK)
            elif sp["status"] == "pauset":
                d.t(tx, ty, "Pause", 12, 400, INK2)
            elif sp["status"] == "ferdig":
                d.t(tx, ty, fx1(sp["forsterkning"]["Fabrikk"]), 12, 400, INK2)
        d.rect(mx + (sel - 1) * cwk - 0.5, yh + 9, cwk + 1, 30 * rowh + 4, "none", INK, 1.4)
    yend = yh + 12 + 30 * rowh
    lx_ = legend_div(d, X, yend + 12, ls=12)
    d.t(lx_ + 16, yend + 23, f"Ramme: Uke {sel}, samme uke som kjeden. Fire striper per spill, Fabrikk øverst. Forsterkning gjelder Fabrikk.", 12, 400, INK2)

    # Høyre kolonne
    rx, rw = 1150, 410
    d.line(rx - 18, 24, rx - 18, 976, HAIR, 1)
    d.t(rx, 50, "Nær overtakelse", 17, 700, INK)
    d.rect(rx, 64, rw, 100, REDF, None, 1, 6)
    d.t(rx + 14, 90, f"Spill {near['spill']} venter på {near['navn']} ({near['venter_paa']})", 15, 700, INK)
    d.t(rx + 14, 110, f"i {near['ventet_timer']} t. KI overtar om {24 - near['ventet_timer']} t.", 15, 400, INK)
    d.button(rx + 14, 122, 168, 30, f"Send Melding til {near['navn']}", size=13)
    d.button(rx + 190, 122, 112, 30, "Pause spillet", primary=False, size=13)
    y = 194
    d.t(rx, y, "Venter ellers", 15, 600, INK)
    y += 22
    for sp in sorted((s for s in spill if s["status"] in ("venter", "pauset") and s is not near), key=lambda s: (RANK[s["status"]], -(s.get("ventet_timer") or 0))):
        d.t(rx, y, f"Spill {sp['spill']}", 13, 600, INK)
        if sp["status"] == "venter":
            d.t(rx + 62, y, f"{sp['navn']}, {sp['venter_paa']}, {sp['ventet_timer']} t", 13, 400, INK)
            d.t(rx + rw, y, "Send Melding", 13, 600, BLUE, "end", 'text-decoration="underline"')
        else:
            d.t(rx + 62, y, f"Pause i Uke {sp['uke']}, fortsetter {sp['fortsetter']}", 13, 400, INK2)
        y += 21
    y += 18
    d.t(rx, y, "Trakten", 15, 600, INK)
    tr = KL["traktA"]
    steps = [("Registrert", tr["registrert"]), ("Klassespill ferdig", tr["klassespill_ferdig"]), ("Debrief ferdig", tr["debrief_ferdig"]),
             ("Quiz bestått", tr["quiz_bestått"]), ("Replay ferdig", tr["replay_ferdig"]), ("Test levert", tr["test_levert"]), ("KI-vurdering klar", tr["ki_vurdering_klar"])]
    y += 20
    for lab, v in steps:
        d.t(rx, y, lab, 13, 400, INK)
        d.t(rx + 150, y, v, 13, 600, INK, "end")
        if v:
            d.rect(rx + 160, y - 9, (rw - 160) * v / steps[0][1], 9, ORD)
        y += 19
    # Klassens kostnad
    y += 22
    F = KL["ferdige"]
    FJ = KL["fjoraaret"]
    fer = [s for s in spill if s["status"] == "ferdig"]
    assert len(fer) == F["antall"]
    assert median(s["kjedekost"] for s in fer) == F["kjedekost"]["median"]
    d.t(rx, y, "Kjedekost i ferdige spill", 15, 600, INK)
    d.t(rx, y + 18, f"Median {nf(F['kjedekost']['median'], 0)} kr. Fjoråret {nf(FJ['median_kjedekost'], 0)} kr ({FJ['spill']} spill).", 13, 400, INK2)
    ys = y + 62
    lo_, hi_ = 0, 3600
    sx = lambda v: rx + 8 + (rw - 16) * (v - lo_) / (hi_ - lo_)
    d.line(rx, ys + 22, rx + rw, ys + 22, HAIR2, 1)
    d.rect(sx(F["kjedekost"]["q1"]), ys - 2, sx(F["kjedekost"]["q3"]) - sx(F["kjedekost"]["q1"]), 24, TINT)
    cnt = {}
    for s_ in sorted(fer, key=lambda s: s["kjedekost"]):
        b = int(s_["kjedekost"] // 150)
        cnt[b] = cnt.get(b, 0) + 1
        d.circle(sx(s_["kjedekost"]), ys + 22 - cnt[b] * 5.5 + 1, 2.5, ORD)
    d.line(sx(F["kjedekost"]["median"]), ys - 8, sx(F["kjedekost"]["median"]), ys + 26, INK, 1.8)
    d.line(sx(FJ["median_kjedekost"]), ys - 8, sx(FJ["median_kjedekost"]), ys + 26, INK, 1.2, dash="3 2")
    d.t(sx(F["kjedekost"]["median"]) - 4, ys - 12, "Median", 12, 600, INK, "end")
    d.t(sx(FJ["median_kjedekost"]) + 4, ys - 12, "Fjoråret", 12, 400, INK2)
    for v in (0, 1000, 2000, 3000):
        d.t(sx(v), ys + 38, nf(v, 0), 11.5, 400, INK3, "middle")
    y2 = ys + 72
    wc = class_week_costs()
    d.t(rx, y2, "Klassens kostnad per uke", 15, 600, INK)
    d.t(rx, y2 + 18, "Sum over spillene som har nådd uka", 13, 400, INK2)
    axw = Axis(rx + 40, rw - 40, 1, 36)
    hb = 70
    yb0 = y2 + 36
    mxc = max(a + b for a, b in wc)
    top_ = 1000 * (int(mxc // 1000) + 1)
    Yb = yscale(yb0, hb, 0, top_)
    for v in (0, top_ // 2, top_):
        d.line(axw.x0, Yb(v), axw.x1, Yb(v), HAIR2 if v == 0 else HAIR, 1)
        d.t(axw.x0 - 5, Yb(v) + 4, nf(v, 0), 11, 400, INK3, "end")
    for k, (a, b) in enumerate(wc, start=1):
        bw_ = axw.slot - 1.5
        d.rect(axw.xc(k) - bw_ / 2, Yb(a), bw_, Yb(0) - Yb(a), BLUE)
        d.rect(axw.xc(k) - bw_ / 2, Yb(a + b), bw_, max(Yb(a) - Yb(a + b) - 0.8, 0), RED)
    pk = max(range(36), key=lambda k: wc[k][1])
    d.t(axw.x0 + 4, Yb(top_) + 4, f"Mest restordre: {nf(wc[pk][1], 0)} kr i Uke {pk + 1}", 12, 600, INK)
    xaxis(d, axw, yb0 + hb + 15, [1, 12, 24, 36], None, 11)
    d.t(rx, yb0 + hb + 38, "Lager i blått, restordre i rødt.", 12, 400, INK2)
    d.button(rx, 924, 150, 36, "Vis i plenum", primary=False, size=14)
    d.button(rx + 160, 924, 150, 36, "Vis som tabell", primary=False, size=14)
    d.demodata(rx + rw, 960, a="end")
    d.save()


if __name__ == "__main__":
    build_07()
    build_08()
