"""07 debrief og 08 lærerens oversikt."""
import statistics

from e01lib import *
from screens_core import G, BARE, ALLE, K, NAME, flow_title, cost_split_bars

SEATS = {r: Seat(r) for r in ROLES}
DEM = FX["spill17"]["serier"]["demand"]
KL = FX["klasse"]
UP = ["Fabrikk", "Distributør", "Grossist", "Detaljist"]


def sec_title(d, x, y, n, title, width):
    """Stegnummeret bærer rekkefølgen i Debriefen."""
    d.line(x, y - 26, x + width, y - 26, INK, 1.2)
    if n:
        d.t(x, y, str(n), 22, 700, INK)
        return d.para(x + 24, y, title, width - 24, 22, 27, 600, INK)
    return d.para(x, y, title, width, 22, 27, 600, INK)


def demand_band(d, ax, y0, h, scale, label=True, ls=14):
    u = h / scale
    base = y0 + h
    dd = f"M{ax.xl(1):.1f} {base:.1f}"
    for w in range(1, 37):
        v = DEM[w - 1]
        dd += f" L{ax.xl(w):.1f} {base - v * u:.1f} L{ax.xr(w):.1f} {base - v * u:.1f}"
    dd += f" L{ax.xr(36):.1f} {base:.1f} Z"
    d.path(dd, BLUEF)
    d.line(ax.xl(1), base, ax.xr(36), base, HAIR2, 1)


def chain_cost_week(src, w):
    """Kjedens kostnad i Uke w, delt i lager og restordre."""
    S = {r: Seat(r, src) for r in ROLES}
    return sum(S[r].lagerkost(w) for r in ROLES), sum(S[r].restkost(w) for r in ROLES)


def build_07():
    d = Doc("07-debrief", 2100, 1200, f"{NAME}, Gruppedebrief i fem steg",
            "Forklaring, avsløring av etterspørselen, hele kjeden med fire ledd og alle ordre, ditt øyeblikk i Uke 11, "
            "kjedens kostnad mot simulert referanse, quiz, og delt skjerm med matrisen Rolle × uke.")
    d.t(40, 44, "Debrief, Spill 17: fra «hadde jeg rett?» til «hvorfor skjedde det?»", 28, 600, INK)

    # Steg 1
    x, w = 40, 320
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

    # Steg 2: klimaks
    x2, w2 = 400, 620
    sec_title(d, x2, y, 2, "Kundene bestilte 4, så 8. Etter det endret de seg aldri.", w2)
    ax2 = Axis(x2 + 28, w2 - 28, 1, 36)
    y0 = y + 26
    h = 320
    scale = 26
    u = h / scale
    for v in (0, 8, 16, 24):
        yy = y0 + h - v * u
        d.line(ax2.x0, yy, ax2.x1, yy, HAIR, 1)
        d.t(ax2.x0 - 5, yy + 4, v, 13, 400, INK3, "end")
    demand_band(d, ax2, y0, h, scale)
    bw = 5
    for k in range(1, 37):
        d.rect(ax2.xc(k) - bw / 2, y0 + h - G.order(k) * u, bw, G.order(k) * u, INK)
    d.path("M" + " L".join(f"{ax2.xc(k):.1f} {y0 + h - G.inn(k) * u:.1f}" for k in range(1, 37)), stroke=GREY, sw=1.6)
    d.t(ax2.xc(11) + 8, y0 + h - 24 * u + 12, "Din ordre, 24 i Uke 11", 15, 600, INK)
    d.t(ax2.xc(29.5), y0 + h - 8 * u - 10, "Kundeetterspørsel: 8", 16, 700, BLUE, "middle", 'stroke="#FFFFFF" stroke-width="4" paint-order="stroke"')
    d.t(ax2.xc(2.5), y0 + h - 4 * u - 8, "4", 18, 700, BLUE, "middle")
    d.t(ax2.xc(19) + 6, y0 + h - 13 * u, "Ordre inn: det eneste du så", 15, 600, INK2)
    xaxis(d, ax2, y0 + h + 18, [1, 5, 10, 15, 20, 25, 30, 36], None)
    d.para(x2, y0 + h + 42, "Øvelsen heter Beer Game. Nesten alle grupper svinger slik, også i år. Det du så, var Idas ordrer, ikke kundene. Struktur gir atferd, derfor spør vi hvorfor og ikke hvem.", w2, 15, 20, fill=INK)
    d.t(x2, y0 + h + 92, "P4, P6", 13, 400, INK3)

    # Steg 3: hele kjeden + fire Rollers ordre
    x3, w3 = 1060, 1000
    sec_title(d, x3, y, 3, "Hele kjeden: svingningene vokser oppstrøms og kommer senere", w3)
    # ukeskrubber
    ys = y + 30
    sx0, sx1 = x3 + 130, x3 + w3 - 90
    d.t(x3, ys + 5, "Kjeden i Uke 11", 15, 600, INK)
    d.line(sx0, ys, sx1, ys, HAIR2, 3)
    hx = sx0 + (11 - 1) / 35 * (sx1 - sx0)
    d.line(sx0, ys, hx, ys, INK, 3)
    d.circle(hx, ys, 7, PAPER, INK, 2)
    d.t(sx0, ys + 20, "Uke 1", 13, 400, INK3)
    d.t(sx1, ys + 20, "Uke 36", 13, 400, INK3, "end")
    d.t(sx1 + 12, ys + 5, "Spol", 13, 600, BLUE, "start", 'text-decoration="underline"')
    c = chain4(d, x3, ys + 34, w3, 11, k=3.4, lead=90)
    # Sara uthevet
    gx_, gw_ = c["geo"]["Grossist"]
    d.t(gx_ + 66, c["yc"] + 22 + 13 + 8, "(du)", 13, 400, INK2)
    ax3 = Axis(x3 + 130, w3 - 130 - 90, 1, 36)
    y3 = c["bottom"] + 22
    rh = 52
    fs = 32
    onset = {}
    for i, r in enumerate(UP):
        yy = y3 + i * (rh + 6)
        S = SEATS[r]
        ou = rh / fs
        d.line(ax3.x0, yy, ax3.x1, yy, HAIR, 1)
        order_bars(d, ax3, yy, rh, S.order, 1, 36, fs, fill=INK if r == "Grossist" else ORD)
        d.t(x3, yy + rh - 20, r, 15, 600, INK)
        d.t(x3, yy + rh - 3, NAVN[r] if r != "Grossist" else "Sara, du", 13, 400, INK2)
        d.t(ax3.x1 + 90, yy + rh - 6, fx1(K["forsterkning"][r]), 22, 700, INK, "end",
            'style="font-variant-numeric:lining-nums proportional-nums"')
        first = next(k for k in range(1, 37) if S.order(k) >= 10)
        onset[r] = (ax3.xc(first), yy + rh - S.order(first) * ou, first)
    pts = [onset[r] for r in UP]
    d.path("M" + " L".join(f"{a:.1f} {b - 3:.1f}" for a, b, _ in pts), stroke=RED, sw=1.2)
    for a, b, k in pts:
        d.circle(a, b - 3, 4, RED, PAPER, 1.5)
        d.t(a - 8, b - 6, f"Uke {k}", 13, 600, RED, "end")
    yd = y3 + 4 * (rh + 6)
    demand_band(d, ax3, yd, 8 * rh / fs + 1, 8)
    d.t(x3, yd + 13, "Kundene", 15, 600, INK)
    xaxis(d, ax3, yd + 8 * rh / fs + 18, [1, 5, 10, 15, 20, 25, 30, 36])
    d.t(x3 + 130, yd + 8 * rh / fs + 40, "Rødt punkt: første Uke med ordre på 10 eller mer. Samme skala i alle rader. Tallet til høyre er Forsterkning. P5.", 14, 400, INK2)

    # Rad 2
    yb = 626
    x4, w4 = 40, 760
    sec_title(d, x4, yb, 4, "Ditt øyeblikk: Uke 11. Du bestilte 24 med 16 på vei.", w4)
    mm = meteo(d, G, x4, yb + 14, 340, 11, 24, left=30, hn=92, hf=34, gap=8, t_flow="", t_ord="Din ordre",
               t_net="Dette så du", futnote=None, cost=True, hc=28, cmax=40, t_cost="Kostnad per uke", ls=13)
    flow_title(d, x4, mm["yflow"] - 7, G, 11)
    tx = x4 + 372
    tw = w4 - 372
    d.t(tx, yb + 28, "Dette regnet du", 15, 600, INK)
    ny = d.para(tx, yb + 50, f"Posisjon {G.lager[10]} − {G.rest[10]} + {G.paavei(11)} = {G.posisjon(11)}. Med 24 ble den {G.posisjon(11) + 24}.", tw, 15, 20)
    d.t(tx, ny + 10, "Dette kostet det senere", 15, 600, INK)
    late = G.kostsum(36) - G.kostsum(24)
    assert all(G.rest[k - 1] == 0 for k in range(25, 37))
    ny = d.para(tx, ny + 32, f"{G.levering(15)} av de 24 kom i Uke 15. På vei toppet på {max(G.pv)} i Uke {G.pv.index(max(G.pv)) + 1}. Restordren kostet deg {nf(G.cum_rest(36))} kr, og lageret i Uke 25 til 36 kostet {nf(late)} kr.", tw, 15, 20)
    d.t(tx, ny + 10, "Dette så de andre i Uke 11", 15, 600, INK)
    yy = ny + 32
    for r in ("Detaljist", "Distributør", "Fabrikk"):
        S = SEATS[r]
        d.t(tx, yy, f"{NAVN[r]}, {r}", 14, 400, INK)
        st = f"lager {S.lager[10]}" if S.net(11) >= 0 else f"restordre {S.rest[10]}"
        d.t(tx + tw, yy, f"{st}, ordre inn {S.inn(11)}", 14, 400, INK2, "end")
        d.line(tx, yy + 7, tx + tw, yy + 7, HAIR, 1)
        yy += 24
    yy += 6
    B = FX["bare_sara_teller_paa_vei"]
    yy = d.para(tx, yy, f"Simulert, Sara teller alt på vei: ordre {BARE.order(11)} i Uke 11, Grossist {nf(B['kost_per_rolle']['Grossist'])} kr. Ingen fasit.", tw, 14, 19, fill=INK2)
    yy = d.para(tx, yy + 2, "KI-generert, kan ta feil: «Du så restordren, ikke posisjonen.»", tw, 14, 19, fill=INK2)
    d.t(tx, yy + 2, "P1, P2, P3, P8", 13, 400, INK3)

    # Kjedens kostnad
    xk, wk_ = 840, 620
    sec_title(d, xk, yb, None, "Kjedens kostnad: målet var lavest kostnad for hele kjeden", wk_)
    A = FX["alle_teller_paa_vei"]
    d.t(xk, yb + 46, f"{nf(K['kjedekost'])} kr", 32, 700, INK, extra='style="font-variant-numeric:lining-nums proportional-nums"')
    d.t(xk + 210, yb + 32, "Spill 17, fire Roller", 14, 400, INK2)
    d.t(xk + 210, yb + 50, f"Simulert referanse, alle teller på vei: {nf(A['kjedekost'])} kr", 14, 400, INK2)
    cost_split_bars(d, xk, yb + 80, wk_, K, ls=14, rowh=31)
    # akkumulert kjedekost over tid
    gy = yb + 80 + 4 * 31 + 6
    gh = 84
    axk = Axis(xk + 40, wk_ - 40 - 150, 1, 36)
    Yk = yscale(gy, gh, 0, 2400)
    for v in (0, 1000, 2000):
        d.line(axk.x0, Yk(v), axk.x1, Yk(v), HAIR2 if v == 0 else HAIR, 1)
        d.t(axk.x0 - 5, Yk(v) + 4, nf(v, 0), 12, 400, INK3, "end")
    cl, ct = 0, 0
    lo, hi = [], []
    for wk in range(1, 37):
        a, b = chain_cost_week(K, wk)
        cl += a
        ct += a + b
        lo.append((axk.xc(wk), Yk(cl)))
        hi.append((axk.xc(wk), Yk(ct)))
    assert abs(ct - K["kjedekost"]) < 1e-9
    base = Yk(0)
    d.path("M" + " L".join(f"{p:.1f} {q:.1f}" for p, q in lo) + f" L{lo[-1][0]:.1f} {base:.1f} L{lo[0][0]:.1f} {base:.1f} Z", BLUEF)
    d.path("M" + " L".join(f"{p:.1f} {q:.1f}" for p, q in hi) + " L" + " L".join(f"{p:.1f} {q:.1f}" for p, q in reversed(lo)) + " Z", REDF)
    d.path("M" + " L".join(f"{p:.1f} {q:.1f}" for p, q in hi), stroke=INK, sw=2)
    ca = 0
    pa = []
    for wk in range(1, 37):
        a, b = chain_cost_week(A, wk)
        ca += a + b
        pa.append((axk.xc(wk), Yk(ca)))
    d.path("M" + " L".join(f"{p:.1f} {q:.1f}" for p, q in pa), stroke=GREY, sw=1.6, dash="5 3")
    d.t(axk.x1 + 8, hi[-1][1] + 4, f"Spill 17: {nf(K['kjedekost'], 0)}", 13, 600, INK)
    d.t(axk.x1 + 8, pa[-1][1] + 4, f"Simulert: {nf(A['kjedekost'], 0)}", 13, 600, INK2)
    d.t(axk.x0 + 4, gy + 10, "Kjeden, akkumulert, kr", 13, 600, INK)
    xaxis(d, axk, gy + gh + 16, [1, 12, 24, 36], None, 12)
    d.t(axk.x1 + 8, gy + gh - 4, "Blått: lager", 13, 400, INK2)
    d.t(axk.x1 + 8, gy + gh - 22, "Rødt: restordre", 13, 400, INK2)

    # Steg 5
    x5, w5 = 1500, 560
    sec_title(d, x5, yb, 5, "Debrief-quiz", w5)
    ny = d.para(x5, yb + 32, f"Uke 11: lager {G.lager[10]}, restordre {G.rest[10]}, {G.paavei(11)} på vei. Hva er posisjonen før du bestiller?", w5, 16, 22, 600)
    opts = [(sg(-13), "wrong"), (str(G.posisjon(11)), "right"), ("16", None), ("29", None)]
    yy = ny + 4
    for lab, st in opts:
        col = RED if st == "wrong" else (INK if st == "right" else HAIR2)
        d.rect(x5, yy, w5, 38, PAPER, col, 1.4 if st else 1, 6)
        d.t(x5 + 14, yy + 25, lab, 16, 600, INK)
        if st == "wrong":
            d.t(x5 + w5 - 14, yy + 25, "Ditt svar, ikke riktig", 14, 600, RED, "end")
        if st == "right":
            d.t(x5 + w5 - 14, yy + 25, "Riktig", 14, 600, INK, "end")
        yy += 44
    ny = d.para(x5, yy + 8, "−13 er lager minus restordre. Da mangler det du allerede har bestilt: 0 − 13 + 16 = 3. I båndet ditt står de 16 som bokser til venstre for lageret.", w5, 15, 20)
    d.t(x5, ny + 6, "P3", 13, 400, INK3)

    # Rad 3: delt skjerm, matrisen Rolle × uke
    yr = 1000
    sec_title(d, 40, yr, None, "Delt skjerm: alle ordre som tall, Rolle × uke", 2020)
    d.t(560, yr, "Tallene viser det grafen i steg 3 viser: tallene vokser og kommer senere for hvert ledd oppover.", 15, 400, INK2)
    axm = Axis(250, 1730, 1, 36)
    cw = axm.slot - 2
    ym = yr + 22
    xaxis(d, axm, ym, list(range(1, 37)), None, 12)
    ym += 8
    rows = [("Kundene", None)] + [(r, SEATS[r]) for r in ["Detaljist", "Grossist", "Distributør", "Fabrikk"]]
    rh2 = 21
    for lab, S in rows:
        d.t(40, ym + 15, lab + (" (du)" if lab == "Grossist" else ""), 14, 600, INK)
        if S:
            d.t(160, ym + 15, NAVN[lab], 14, 400, INK2)
        for wk in range(1, 37):
            v = DEM[wk - 1] if S is None else S.order(wk)
            fill, tc = seq_cell(v)
            if S is None:
                fill, tc = BLUEF, INK
            d.rect(axm.xc(wk) - cw / 2, ym, cw, rh2, fill)
            d.t(axm.xc(wk), ym + 15, v, 13, 700 if (lab == "Grossist" and wk == 11) else 400, tc, "middle")
        if S:
            d.t(2060, ym + 15, fx1(K["forsterkning"][lab]), 14, 700, INK, "end")
        ym += rh2 + 3
    # kjedens kostnad per uke som rad
    d.t(40, ym + 15, "Kjeden, kr per uke", 14, 600, INK)
    tot = 0
    for wk in range(1, 37):
        a, b = chain_cost_week(K, wk)
        tot += a + b
        fill = NEG[0] if b > a else POS[0]
        d.rect(axm.xc(wk) - cw / 2, ym, cw, rh2, fill)
        d.t(axm.xc(wk), ym + 15, kr(a + b), 13, 400, INK, "middle")
    assert abs(tot - K["kjedekost"]) < 1e-9
    d.t(2060, ym + 15, f"{nf(tot, 0)}", 14, 700, INK, "end")
    d.t(40, ym + 46, "Mørkere celle: større ordre. Rød kostnadscelle: mest restordre den Uka, blå: mest lager. Kolonnen til høyre er Forsterkning, og sum kroner for kjeden.", 13, 400, INK2)
    d.demodata(2060, 1192, "Demodata. Simulerte tall er merket Simulert.", 13, "end")
    d.save()


# ---------- 08 ----------
def strip(d, x, y, sp, cw=4.3, lane=4, roles=("Fabrikk", "Distributør", "Grossist", "Detaljist")):
    for i, r in enumerate(roles):
        vals = sp["netto_lager"][r]
        for k, v in enumerate(vals):
            d.rect(x + k * cw, y + i * (lane + 0.5), cw + 0.2, lane, div_cell(v)[0])


def heat(v, cap=45):
    return div_cell(v)[0]


def status_txt(sp):
    return {"ferdig": "Ferdig", "pågår": "Pågår", "pauset": "Pause", "venter": "Venter"}[sp["status"]]


def class_cost_per_week():
    """Klassens kostnad per uke: snitt per spill over spillene som har nådd den uka, delt i lager og restordre."""
    out = []
    for wk in range(1, 37):
        games = [s for s in KL["spill"] if s["uke"] >= wk]
        lag = sum(v * 0.5 for s in games for r in ROLES for v in [s["netto_lager"][r][wk - 1]] if v > 0)
        res = sum(-v for s in games for r in ROLES for v in [s["netto_lager"][r][wk - 1]] if v < 0)
        out.append((wk, len(games), lag / len(games), res / len(games)))
    return out


def build_08():
    d = Doc("08-laerer-oversikt", 1600, 1000, f"{NAME}, Oversikt for Faglærer",
            "60 Klassespill på én skjerm: matrisen 60 spill × uker med netto lager for valgt Rolle, status, hvem spillet venter på, "
            "KI-seter og kjedekost per spill. Til høyre: nær overtakelse, trakten og klassens kostnadsbilde.")
    spill = KL["spill"]
    F = KL["ferdige"]
    FJ = KL["fjoraaret"]
    counts = {k: sum(1 for s in spill if s["status"] == k) for k in ("venter", "pauset", "pågår", "ferdig")}
    assert counts == {"venter": 4, "pauset": 2, "pågår": 13, "ferdig": 41}
    fer = [s for s in spill if s["status"] == "ferdig"]
    assert statistics.median(s["kjedekost"] for s in fer) == F["kjedekost"]["median"]
    X = 40
    d.t(X, 50, "Oversikt", 26, 700, INK)
    d.t(X + 112, 50, "class-of-1994, IBE160", 15, 400, INK2)
    d.t(X + 300, 50, f"{counts['ferdig']} ferdig · {counts['pågår'] + counts['pauset']} pågår (herav {counts['pauset']} pauset) · {counts['venter']} venter", 15, 600, INK)
    d.t(1560, 50, "Spillfrist ti. 8. des", 15, 400, INK2, "end")
    # Filtre
    yf = 92
    ki = sum(1 for s in spill if s["ki_seter"] > 0)
    labs = [("Alle", len(spill)), ("Venter", counts["venter"]), ("Pause", counts["pauset"]), ("Pågår", counts["pågår"]), ("Ferdig", counts["ferdig"]), ("Med KI-spiller", ki)]
    xx = X
    for i, (lab, c) in enumerate(labs):
        s = f"{lab} {c}"
        wd = text_w(s, 14) + 22
        d.rect(xx, yf - 17, wd, 28, INK if i == 0 else PAPER, None if i == 0 else HAIR2, 1, 5)
        d.t(xx + wd / 2, yf + 2, s, 14, 600, PAPER if i == 0 else INK, "middle")
        xx += wd + 8
    # Visning
    xx += 20
    d.t(xx, yf + 2, "Rolle", 13, 400, INK2)
    xx += 40
    for r in ROLES:
        on = r == "Fabrikk"
        d.t(xx, yf + 2, r, 14, 600 if on else 400, INK)
        if on:
            d.line(xx, yf + 8, xx + text_w(r, 14), yf + 8, INK, 2)
        xx += text_w(r, 14) + 14
    xx += 10
    d.t(xx, yf + 2, "Størrelse", 13, 400, INK2)
    xx += 64
    for s_ in ("Netto lager", "Ordre", "Kostnad"):
        on = s_ == "Netto lager"
        d.t(xx, yf + 2, s_, 14, 600 if on else 400, INK)
        if on:
            d.line(xx, yf + 8, xx + text_w(s_, 14), yf + 8, INK, 2)
        xx += text_w(s_, 14) + 14

    # Matrisevegg
    rank = {"venter": 0, "pauset": 1, "pågår": 2, "ferdig": 3}
    ordered = sorted(spill, key=lambda s: (rank[s["status"]], -(s.get("ventet_timer") or 0), -s["uke"] if s["status"] == "pågår" else s["kjedekost"]))
    near = sorted([s for s in spill if s["status"] == "venter"], key=lambda s: -s["ventet_timer"])
    top = near[0]
    mx = X + 70
    cw = 14.6
    ax = Axis(mx, cw * 36, 1, 36)
    yh = 130
    cols = [(X, "Spill", "start"), (mx, "Netto lager, Fabrikk, Uke 1 til 36", "start"), (mx + cw * 36 + 34, "Uke", "end"),
            (mx + cw * 36 + 104, "Kjede, kr", "end"), (mx + cw * 36 + 134, "KI", "end"), (mx + cw * 36 + 150, "Venter på, eller Forsterkning", "start")]
    for cx, h, a in cols:
        d.t(cx, yh, h, 13, 600, INK2, a)
    for wk in (1, 12, 24, 36):
        d.t(ax.xc(wk), yh + 16, wk, 11, 400, INK3, "middle")
    y = yh + 24
    rowh = 12.2
    grp = None
    gname = {"venter": "Venter", "pauset": "Pauset", "pågår": "Pågår", "ferdig": "Ferdig, lavest kjedekost øverst"}
    for sp in ordered:
        if sp["status"] != grp:
            grp = sp["status"]
            y += 15
            n = counts[grp]
            d.t(X, y - 2, f"{gname[grp]} {n}", 12, 700, INK)
            y += 2
        isnear = sp["spill"] == top["spill"]
        if isnear:
            d.rect(X - 6, y - 1, 1000 - X + 6, rowh + 1, REDF)
        d.t(X + 26, y + 9.5, sp["spill"], 11, 600, INK, "end")
        vals = sp["netto_lager"]["Fabrikk"]
        for k, v in enumerate(vals):
            d.rect(ax.xl(k + 1) + 0.3, y, cw - 0.6, rowh - 1.4, div_cell(v)[0])
        if sp["status"] != "ferdig":
            xe = ax.xr(sp["uke"])
            d.line(xe + 1, y - 0.5, xe + 1, y + rowh - 1, INK, 1.6)
        d.t(mx + cw * 36 + 34, y + 9.5, sp["uke"], 11, 400, INK, "end")
        d.t(mx + cw * 36 + 104, y + 9.5, nf(sp["kjedekost"], 0), 11, 400, INK, "end")
        if sp["ki_seter"]:
            d.t(mx + cw * 36 + 134, y + 9.5, f"KI {sp['ki_seter']}", 11, 400, INK, "end")
        if sp["status"] == "venter":
            d.t(mx + cw * 36 + 150, y + 9.5, f"{sp['navn']}, {sp['venter_paa']}, {sp['ventet_timer']} t" + (". KI overtar om 1 t" if isnear else ""), 11, 700 if isnear else 400, INK)
        elif sp["status"] == "pauset":
            d.t(mx + cw * 36 + 150, y + 9.5, f"Pause, fortsetter {sp['fortsetter']}", 11, 400, INK2)
        elif sp["status"] == "ferdig":
            d.t(mx + cw * 36 + 150, y + 9.5, fx1(sp['forsterkning']['Fabrikk']), 11, 400, INK2)
        y += rowh
    # skala
    yl = y + 18
    d.t(X, yl + 10, "Restordre", 12, 400, INK2)
    xx = X + 62
    for v in (-30, -15, -5, 0, 5, 15, 30):
        d.rect(xx, yl, 22, 12, div_cell(v)[0])
        xx += 24
    d.t(xx + 4, yl + 10, "Lager", 12, 400, INK2)
    d.t(xx + 50, yl + 10, "Trinn: 1–10, 11–25, over 25. Mørk strek: der et pågående spill står nå.", 12, 400, INK2)

    # Høyre kolonne
    rx, rw = 1030, 530
    d.line(rx - 16, 116, rx - 16, 960, HAIR, 1)
    ry = 134
    d.t(rx, ry, "Nær overtakelse", 16, 600, INK)
    d.rect(rx, ry + 12, rw, 84, REDF, None, 1, 6)
    d.t(rx + 14, ry + 38, f"Spill {top['spill']} venter på {top['navn']} ({top['venter_paa']}) i {top['ventet_timer']} t.", 15, 700, INK)
    d.t(rx + 14, ry + 58, f"KI-spiller overtar setet om {24 - top['ventet_timer']} t.", 14, 400, INK)
    d.button(rx + 14, ry + 66, 150, 24, f"Send Melding til {top['navn']}", size=12)
    d.button(rx + 172, ry + 66, 110, 24, "Pause spillet", primary=False, size=12)
    yy = ry + 122
    for s in near[1:]:
        d.t(rx, yy, f"Spill {s['spill']}", 13, 600, INK)
        d.t(rx + 64, yy, f"{s['navn']}, {s['venter_paa']}, {s['ventet_timer']} t", 13, 400, INK)
        d.t(rx + rw, yy, "Send Melding", 13, 600, BLUE, "end", 'text-decoration="underline"')
        yy += 20
    # Trakt
    yt = yy + 22
    d.t(rx, yt, "Trakten", 16, 600, INK)
    tr = KL["traktA"]
    steps = [("Registrert", tr["registrert"]), ("Klassespill ferdig", tr["klassespill_ferdig"]), ("Debrief ferdig", tr["debrief_ferdig"]),
             ("Quiz bestått", tr["quiz_bestått"]), ("Replay ferdig", tr["replay_ferdig"]), ("Test levert", tr["test_levert"]), ("KI-vurdering klar", tr["ki_vurdering_klar"])]
    yy = yt + 20
    for lab, v in steps:
        d.t(rx, yy, lab, 13, 400, INK)
        d.t(rx + 150, yy, v, 13, 600, INK, "end")
        d.rect(rx + 160, yy - 9, (rw - 160) * v / 240, 10, ORD if v else HAIR)
        yy += 17
    # Klassens kostnad
    yk = yy + 26
    d.t(rx, yk, "Kjedekostnad per spill", 16, 600, INK)
    d.t(rx + rw, yk, "Bare Faglærer ser dette", 13, 400, INK2, "end")
    axd = Axis(rx, rw, 0, 36)
    lo_, hi_ = 0, 3600
    Xd = lambda v: rx + v / hi_ * rw
    yb_ = yk + 92
    # dot strip, stablet per 100 kr
    bins = {}
    for s in sorted(spill, key=lambda s: s["kjedekost"]):
        b = int(s["kjedekost"] // 100)
        n = bins.get(b, 0)
        bins[b] = n + 1
        cx = Xd(b * 100 + 50)
        cy = yb_ - 6 - n * 9
        if s["status"] == "ferdig":
            d.circle(cx, cy, 3.6, INK)
        else:
            d.circle(cx, cy, 3.2, PAPER, INK, 1.2)
    d.line(rx, yb_, rx + rw, yb_, HAIR2, 1)
    for v in (0, 1000, 2000, 3000):
        d.t(Xd(v), yb_ + 15, nf(v, 0), 12, 400, INK3, "middle" if v else "start")
    med = F["kjedekost"]["median"]
    d.line(Xd(med), yk + 16, Xd(med), yb_, INK, 1.4)
    d.t(Xd(med) - 4, yk + 26, f"Median {nf(med, 0)}", 12, 600, INK, "end")
    d.line(Xd(FJ["median_kjedekost"]), yk + 16, Xd(FJ["median_kjedekost"]), yb_, INK2, 1, dash="3 3")
    d.t(Xd(FJ["median_kjedekost"]) + 4, yk + 26, f"Fjoråret {nf(FJ['median_kjedekost'], 0)}", 12, 600, INK2)
    d.t(rx, yb_ + 34, f"Fylt: ferdig. Ring: pågår, kostnad så langt. Midtre halvdel av ferdige: {nf(F['kjedekost']['q1'], 0)} til {nf(F['kjedekost']['q3'], 0)} kr.", 12, 400, INK2)
    # kostnad per uke
    yw = yb_ + 66
    d.t(rx, yw, "Klassens kostnad per uke, snitt per spill", 16, 600, INK)
    cc = class_cost_per_week()
    gh = 88
    axw = Axis(rx + 34, rw - 34, 1, 36)
    Yw = yscale(yw + 14, gh, 0, max(a + b for _, _, a, b in cc) * 1.05)
    top_ = max(a + b for _, _, a, b in cc)
    for v in (0, 50, 100):
        if v <= top_ * 1.05:
            d.line(axw.x0, Yw(v), axw.x1, Yw(v), HAIR2 if v == 0 else HAIR, 1)
            d.t(axw.x0 - 5, Yw(v) + 4, v, 12, 400, INK3, "end")
    bw = axw.slot - 2
    for wk, n, a, b in cc:
        d.rect(axw.xc(wk) - bw / 2, Yw(a), bw, Yw(0) - Yw(a), BLUE)
        d.rect(axw.xc(wk) - bw / 2, Yw(a + b), bw, Yw(a) - Yw(a + b) - (1 if a else 0), RED)
    pk = max(cc, key=lambda c: c[2] + c[3])
    xaxis(d, axw, yw + 14 + gh + 15, [1, 12, 24, 36], None, 12)
    d.t(rx, yw + gh + 50, f"Blått: lager. Rødt: restordre. Høyest i Uke {pk[0]}: {nf(pk[2] + pk[3], 0)} kr. Spill som har nådd uka teller med.", 12, 400, INK2)
    ym_ = yw + gh + 84
    d.t(rx, ym_, "Mønstre i ordrene, alle spill", 16, 600, INK)
    ym_ += 22
    for k_, v_ in KL["moenstre"].items():
        d.t(rx, ym_, k_, 13, 400, INK)
        d.t(rx + rw, ym_, v_, 13, 600, INK, "end")
        d.line(rx, ym_ + 6, rx + rw, ym_ + 6, HAIR, 1)
        ym_ += 21
    d.button(rx, 924, 150, 36, "Vis som tabell", primary=False, size=14)
    d.button(rx + 162, 924, 150, 36, "Vis i plenum", primary=False, size=14)
    d.button(rx + rw - 150, 924, 150, 36, "Send Melding", size=14)
    d.demodata(1560, 990, a="end")
    d.save()


if __name__ == "__main__":
    build_07()
    build_08()
