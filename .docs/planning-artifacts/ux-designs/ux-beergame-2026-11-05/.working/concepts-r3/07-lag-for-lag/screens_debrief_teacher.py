"""07 Debrief og 08 lærerens Oversikt."""
from statistics import median

from e07parts import *
from screens_core import G, BARE, ALLE, K, SEATS, DEM

KL = FX["klasse"]
SIM = {r: Seat(r, FX["alle_teller_paa_vei"]) for r in ROLES}
for _r, _s in SIM.items():
    check_seat(_s, "sim " + _r)
    assert abs(_s.akk(36) - FX["alle_teller_paa_vei"]["kost_per_rolle"][_r]) < 1e-6


class Chain:
    """Kjedens kostnad: summen av fire Roller."""

    def __init__(self, seats):
        self.seats = seats

    def akk(self, w, kind="sum"):
        return sum(s.akk(w, kind) for s in self.seats.values())

    def lk(self, w):
        return sum(s.lk(w) for s in self.seats.values())

    def rk(self, w):
        return sum(s.rk(w) for s in self.seats.values())

    def ukekost(self, w):
        return self.lk(w) + self.rk(w)


CH = Chain(SEATS)
CHS = Chain(SIM)
assert abs(CH.akk(36) - K["kjedekost"]) < 1e-6 and abs(CHS.akk(36) - FX["alle_teller_paa_vei"]["kjedekost"]) < 1e-6


# ---------- Klasseaggregater, regnet fra klasse.spill ----------
def game_cost(sp, upto=None):
    return sum((v * LK if v > 0 else -v * RK) for r in ROLES for v in sp["netto_lager"][r][:upto])


for _sp in KL["spill"]:
    assert len(_sp["netto_lager"]["Fabrikk"]) == _sp["uke"], _sp["spill"]
    assert abs(game_cost(_sp) - _sp["kjedekost"]) <= 0.5, _sp["spill"]  # fixturen runder til hele kroner
FERDIG = [s for s in KL["spill"] if s["status"] == "ferdig"]
assert len(FERDIG) == KL["ferdige"]["antall"]
assert median(s["kjedekost"] for s in FERDIG) == KL["ferdige"]["kjedekost"]["median"]
MED_NET = {r: [median(s["netto_lager"][r][k] for s in FERDIG) for k in range(36)] for r in ROLES}
CLASS_WEEK = [(sum(max(s["netto_lager"][r][k], 0) * LK for s in FERDIG for r in ROLES),
               sum(max(-s["netto_lager"][r][k], 0) * RK for s in FERDIG for r in ROLES)) for k in range(36)]
assert abs(sum(a + b for a, b in CLASS_WEEK) - sum(game_cost(s) for s in FERDIG)) < 1e-6


def sec_title(d, x, y, n, title, width):
    d.line(x, y - 26, x + width, y - 26, INK, 1.2)
    d.t(x, y, str(n), 22, 700, INK)
    return d.para(x + 24, y, title, width - 24, 22, 27, 600, INK)


def demand_band(d, ax, y0, h, scale):
    u = h / scale
    base = y0 + h
    dd = f"M{ax.xl(1):.1f} {base:.1f}"
    for w in range(1, 37):
        v = DEM[w - 1]
        dd += f" L{ax.xl(w):.1f} {base - v * u:.1f} L{ax.xr(w):.1f} {base - v * u:.1f}"
    dd += f" L{ax.xr(36):.1f} {base:.1f} Z"
    d.path(dd, BLUEF)
    d.line(ax.xl(1), base, ax.xr(36), base, HAIR2, 1)


def build_07():
    d = Doc("07-debrief", 2100, 1200, "Lag for lag, Gruppedebrief i fem steg",
            "Forklaring, avsløring av etterspørselen, alle fire Rollers ordre med matrise Rolle × uke, ditt øyeblikk med hele kjeden i Uke 11, kjedens kostnad, quiz, og den delte skjermen.")
    d.t(40, 44, "Debrief, Spill 17: her åpnes lagene du ikke hadde under spillet", 28, 600, INK)

    # Steg 1
    x, w = 40, 300
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
    x2, w2 = 380, 560
    sec_title(d, x2, y, 2, "Kundene kjøpte 4, så 8. Etter det endret de seg aldri.", w2)
    ax2 = Axis(x2 + 28, w2 - 28, 1, 36)
    y0 = y + 50
    h = 330
    scale = 26
    u = h / scale
    for v in (0, 8, 16, 24):
        yy = y0 + h - v * u
        d.line(ax2.x0, yy, ax2.x1, yy, HAIR, 1)
        d.t(ax2.x0 - 5, yy + 4, v, 13, 400, INK3, "end")
    demand_band(d, ax2, y0, h, scale)
    for k in range(1, 37):
        d.rect(ax2.xc(k) - 2.5, y0 + h - G.order(k) * u, 5, G.order(k) * u, INK)
    d.path("M" + " L".join(f"{ax2.xc(k):.1f} {y0 + h - G.inn(k) * u:.1f}" for k in range(1, 37)), stroke=GREY, sw=1.6)
    d.t(ax2.xc(11) + 8, y0 + h - 24 * u + 12, "Din ordre, 24 i Uke 11", 15, 600, INK)
    d.t(ax2.xc(29.5), y0 + h - 8 * u - 10, "Kundene: 8", 16, 700, BLUE, "middle", 'stroke="#FFFFFF" stroke-width="4" paint-order="stroke"')
    d.t(ax2.xc(2.5), y0 + h - 4 * u - 8, "4", 18, 700, BLUE, "middle")
    d.t(ax2.xc(18) + 6, y0 + h - 14 * u, "Ordre inn: det eneste du så", 15, 600, INK2)
    xaxis(d, ax2, y0 + h + 18, [1, 5, 10, 15, 20, 25, 30, 36], None)
    d.para(x2, y0 + h + 44, "Øvelsen heter Beer Game. Nesten alle grupper svinger slik, også i år. Det du så, var Idas ordrer, ikke kundene. Struktur gir atferd, derfor spør vi hvorfor og ikke hvem.", w2, 15, 20, fill=INK)
    d.t(x2, y0 + h + 104, "P4, P6", 13, 400, INK3)

    # Steg 3: fire Rollers ordre + matrisen Rolle × uke
    x3, w3 = 980, 1080
    sec_title(d, x3, y, 3, "Oppstrøms vokser svingningene, og de kommer senere", w3)
    ax3 = Axis(x3 + 120, w3 - 120 - 70, 1, 36)
    y3 = y + 24
    rh = 52
    fs = 32
    onset = {}
    for i, r in enumerate(CHAIN):
        yy = y3 + i * (rh + 4)
        S = SEATS[r]
        d.line(ax3.x0, yy, ax3.x1, yy, HAIR, 1)
        order_bars(d, ax3, yy, rh, S.order, 1, 36, fs, fill=INK if r == "Grossist" else ORD)
        d.t(x3, yy + rh - 20, r, 15, 600, INK)
        d.t(x3, yy + rh - 3, NAVN[r] if r != "Grossist" else "Sara, du", 13, 400, INK2)
        d.t(ax3.x1 + 70, yy + rh - 4, fx1(K["forsterkning"][r]), 20, 700, INK, "end", 'style="font-variant-numeric:lining-nums proportional-nums"')
        first = next(k for k in range(1, 37) if S.order(k) >= 10)
        onset[r] = (ax3.xc(first), yy + rh - S.order(first) * rh / fs, first)
    pts = [onset[r] for r in CHAIN]
    d.path("M" + " L".join(f"{a:.1f} {b - 3:.1f}" for a, b, _ in pts), stroke=RED, sw=1.2)
    for a, b, k in pts:
        d.circle(a, b - 3, 4, RED, PAPER, 1.5)
        d.t(a - 8, b - 6, f"Uke {k}", 13, 600, RED, "end")
    yd = y3 + 4 * (rh + 4)
    demand_band(d, ax3, yd, 8 * rh / fs + 1, 8)
    d.t(x3, yd + 12, "Kundene", 15, 600, INK)
    ym = yd + 8 * rh / fs + 30
    d.t(x3, ym + 4, "Netto lager, tall", 13, 600, INK2)
    rows = [(r, (lambda S: (lambda k: S.net(k)))(SEATS[r]), "net") for r in CHAIN]
    ym += 10
    yb = matrix(d, ax3, ym, rows, range(1, 37), rh=21, size=12, lx=x3, lsize=13, gap=1)
    xaxis(d, ax3, yb + 16, [1, 5, 10, 15, 20, 25, 30, 36])
    d.para(x3 + 120, yb + 40, "Over: ordre per uke, samme skala i alle rader. Rødt punkt er første Uke med ordre på 10 eller mer. Under: netto lager som tall, minus er restordre. Tallet til høyre er Forsterkning. P5.", w3 - 190, 14, 19, fill=INK2)

    # Rad 2
    yb2 = 700
    # Steg 4
    x4, w4 = 40, 840
    sec_title(d, x4, yb2, 4, "Ditt øyeblikk: Uke 11. Du bestilte 24 med 16 på vei.", w4)
    d.t(x4, yb2 + 32, "Hele kjeden i Uke 11: det hver av dere så", 15, 600, INK)
    # ukeskrubber
    sax = Axis(x4, 500, 1, 36)
    sy = yb2 + 52
    d.line(sax.x0, sy, sax.x1, sy, HAIR2, 3)
    d.line(sax.x0, sy, sax.xc(11), sy, INK, 3)
    d.circle(sax.xc(11), sy, 7, PAPER, INK, 2)
    d.t(sax.xc(11), sy + 22, "Uke 11", 13, 700, INK, "middle")
    d.t(sax.x0, sy + 22, "1", 13, 400, INK3)
    d.t(sax.x1, sy + 22, "36", 13, 400, INK3, "end")
    yc, _ = chain4(d, SEATS, DEM, 11, x4, sy + 36, 520, u=2.2, cost=lambda r: SEATS[r].akk(11))
    d.t(x4, yc + 16, "Under hver Rolle: kostnad hittil. Dra i skrubberen for å spole kjeden.", 13, 400, INK2)
    tx = x4 + 560
    tw = w4 - 560
    d.t(tx, yb2 + 32, "Dette regnet du", 15, 600, INK)
    ny = d.para(tx, yb2 + 54, f"Posisjon {G.lager[10]} − {G.rest[10]} + {G.paavei(11)} = {G.posisjon(11)}. Med 24 ble den {G.posisjon(11) + 24}.", tw, 14, 19)
    d.t(tx, ny + 12, "Dette kostet det senere", 15, 600, INK)
    late = G.akk(36) - G.akk(24)
    assert all(G.rest[k - 1] == 0 for k in range(25, 37))
    ny = d.para(tx, ny + 32, f"{G.levering(15)} av de 24 kom i Uke 15. På vei toppet på {max(G.pv)}, og i Uke {G.lager.index(max(G.lager)) + 1} hadde du lager {max(G.lager)}. Lager i Uke 25 til 36 kostet {nf(late)} kr.", tw, 14, 19)
    d.t(tx, ny + 12, "Samme kjede, Sara teller alt på vei", 15, 600, INK)
    B = FX["bare_sara_teller_paa_vei"]
    d.t(tx, ny + 30, "Simulert. Viser sammenhengen, ikke en fasit.", 13, 400, INK2)
    rows = [("", "Spill 17", "Simulert"), ("Din ordre, Uke 11", "24", str(BARE.order(11))),
            ("Grossist, kr", nf(K["kost_per_rolle"]["Grossist"]), nf(B["kost_per_rolle"]["Grossist"])),
            ("Kjeden, kr", nf(K["kjedekost"]), nf(B["kjedekost"]))]
    yy = ny + 54
    for i, row in enumerate(rows):
        bold = 600 if i == 0 else 400
        d.t(tx, yy, row[0], 14, bold, INK)
        d.t(tx + tw - 80, yy, row[1], 14, bold, INK, "end")
        d.t(tx + tw, yy, row[2], 14, bold, INK, "end")
        d.line(tx, yy + 7, tx + tw, yy + 7, HAIR, 1)
        yy += 24
    d.para(tx, yy + 8, "KI-generert, kan ta feil: «Du reagerte på restordren du så, ikke på posisjonen. Mikkel fikk 24 fra deg uten å vite hvorfor.»", tw, 13, 17, fill=INK2)
    d.t(x4, 1180, "P2, P3, P7", 13, 400, INK3)

    # Kjedens kostnad
    xk, wk = 920, 520
    sec_title(d, xk, yb2, " ", "Kjedens kostnad", wk)
    d.t(xk, yb2 + 40, "Kjeden betalte", 15, 400, INK2)
    d.t(xk, yb2 + 78, f"{nf(K['kjedekost'])} kr", 34, 700, INK, extra='style="font-variant-numeric:lining-nums proportional-nums"')
    rest_all, lag_all = CH.akk(36, "rest"), CH.akk(36, "lager")
    d.t(xk + 250, yb2 + 56, f"Restordre {nf(rest_all)} kr", 14, 600, INK)
    d.t(xk + 250, yb2 + 76, f"Lager {nf(lag_all)} kr", 14, 600, INK)
    d.rect(xk + 236, yb2 + 46, 10, 10, RED)
    d.rect(xk + 236, yb2 + 66, 10, 10, BLUE)
    yy = yb2 + 114
    mx = 750
    sc = (wk - 170) / mx
    for r in CHAIN[::-1]:
        S = SEATS[r]
        rr, ll = S.akk(36, "rest"), S.akk(36, "lager")
        d.t(xk, yy + 12, r, 14, 600 if r == "Grossist" else 400, INK)
        bx = xk + 90
        d.rect(bx, yy, rr * sc - 1, 14, RED)
        d.rect(bx + rr * sc + 1, yy, ll * sc - 1, 14, BLUE)
        sv = SIM[r].akk(36)
        d.line(bx + sv * sc, yy - 4, bx + sv * sc, yy + 18, INK, 1.6, dash="3 2")
        d.t(xk + wk, yy + 12, f"{nf(S.akk(36))}", 14, 600, INK, "end")
        yy += 27
    d.para(xk, yy + 4, f"Stiplet strek: simulert referanse der alle fire teller på vei. Kjeden {nf(FX['alle_teller_paa_vei']['kjedekost'])} kr. Simulert, ikke fasit. P8: restordre koster dobbelt, og målet er hele kjeden.", wk, 13, 17, fill=INK2)
    # per uke og samlet for kjeden
    axk = Axis(xk + 44, wk - 44 - 70, 1, 36)
    yw = yy + 52
    d.t(xk, yw - 8, "Kjeden per uke, kr", 13, 600, INK)
    hb = 56
    mxw = max(CH.ukekost(k) for k in range(1, 37))
    top = 50 * (int(mxw // 50) + 1)
    Yw = grid(d, axk, yw, hb, 0, top, (0, top), 13)
    cost_week_bars(d, axk, yw, hb, CH, 1, 36, top)
    kmax = max(range(1, 37), key=CH.ukekost)
    d.t(axk.xc(kmax) + 8, Yw(CH.ukekost(kmax)) + 4, f"Uke {kmax}: {nf(CH.ukekost(kmax))}", 13, 600, INK)
    yc2 = yw + hb + 28
    d.t(xk, yc2 - 8, "Kjeden samlet, kr", 13, 600, INK)
    Yc = grid(d, axk, yc2, 80, 0, 2400, (0, 1200, 2400), 13)
    cost_cum_area(d, axk, yc2, 80, CH, 1, 36, 2400, ref=CHS)
    d.t(axk.x1 + 6, Yc(CH.akk(36)) + 4, nf(CH.akk(36), 0), 13, 700, INK)
    d.t(axk.x1 + 6, Yc(CHS.akk(36)) + 4, nf(CHS.akk(36), 0), 13, 600, GREY)
    d.t(axk.x1 + 6, Yc(CHS.akk(36)) + 20, "Simulert", 13, 400, GREY)
    xaxis(d, axk, yc2 + 80 + 16, [1, 12, 24, 36])

    # Steg 5
    x5, w5 = 1480, 300
    sec_title(d, x5, yb2, 5, "Debrief-quiz", w5)
    ny = d.para(x5, yb2 + 34, f"Uke 11: lager {G.lager[10]}, restordre {G.rest[10]}, {G.paavei(11)} på vei. Hva er posisjonen før du bestiller?", w5, 15, 20, 600)
    opts = [(sg(-13), "wrong"), (str(G.posisjon(11)), "right"), ("16", None), ("29", None)]
    yy = ny + 4
    for lab, st in opts:
        col = RED if st == "wrong" else (INK if st == "right" else HAIR2)
        d.rect(x5, yy, w5, 38, PAPER, col, 1.4 if st else 1, 6)
        d.t(x5 + 12, yy + 25, lab, 15, 600, INK)
        if st == "wrong":
            d.t(x5 + w5 - 12, yy + 25, "Ditt svar, ikke riktig", 13, 600, RED, "end")
        if st == "right":
            d.t(x5 + w5 - 12, yy + 25, "Riktig", 13, 600, INK, "end")
        yy += 44
    ny = d.para(x5, yy + 8, "−13 er lager minus restordre. Da mangler det du allerede har bestilt: 0 − 13 + 16 = 3.", w5, 14, 19)
    d.t(x5, ny + 14, "Nye lag i Replay", 15, 600, INK)
    tabs(d, x5, ny + 26, w5, ["Posisjon", "Kjeden", "Projeksjon"], "Posisjon", h=30, size=13)
    d.para(x5, ny + 76, "Når quizen er bestått, står regnestykket ferdig i kjedebåndet ditt. Projeksjonen åpnes i Replay.", w5, 13, 17, fill=INK2)
    d.t(x5, 1180, "P3", 13, 400, INK3)

    # Delt skjerm
    xs, ws = 1820, 240
    sec_title(d, xs, yb2, " ", "Delt skjerm", ws)
    fy = yb2 + 18
    d.rect(xs, fy, ws, 330, PAPER, HAIR2, 1.4, 8)
    d.t(xs + 12, fy + 24, "Uke 11, hele kjeden", 13, 600, INK)
    axs = Axis(xs + 64, ws - 76, 1, 36)
    yr = fy + 40
    for r in CHAIN:
        S = SEATS[r]
        Ys = yscale(yr, 44, -70, 60)
        d.line(axs.x0, Ys(0), axs.x1, Ys(0), HAIR2, 1)
        net_area(d, axs, yr, 44, S.net, 1, 36, -70, 60, lw=1.4)
        d.t(xs + 12, Ys(0) + 4, r[:4] + ".", 13, 600, INK)
        yr += 50
    d.line(axs.xc(11), fy + 36, axs.xc(11), yr, INK, 1.2)
    demand_band(d, axs, yr, 14, 8)
    d.t(xs + 12, yr + 12, "Kunde", 13, 600, INK)
    xaxis(d, axs, yr + 32, [1, 12, 24, 36])
    d.para(xs, fy + 352, "Gruppa ser kjeden og kostnaden sammen. Hver student ser sitt eget steg på telefonen.", ws, 13, 17, fill=INK2)
    d.demodata(2060, 1188, "Demodata. Simulerte tall er merket Simulert.", 13, "end")
    d.save()


# ---------- 08 ----------
def status_txt(sp):
    return {"ferdig": "Ferdig", "pågår": "Pågår", "pauset": "Pause", "venter": "Venter"}[sp["status"]]


def wall_row(d, x, y, sp, role, cw, ch):
    vals = sp["netto_lager"][role]
    for k, v in enumerate(vals):
        fill, _ = cell_style(v, "net")
        d.rect(x + k * cw, y, cw - 1, ch, fill if v else "#EEF1F4")
    if sp["status"] != "ferdig":
        xe = x + len(vals) * cw
        d.line(xe + 1, y - 1, xe + 1, y + ch + 1, INK, 1.6)


def strip(d, x, y, sp, cw=4.3, lane=4, roles=("Fabrikk", "Distributør", "Grossist", "Detaljist")):
    for i, r in enumerate(roles):
        for k, v in enumerate(sp["netto_lager"][r]):
            fill, _ = cell_style(v, "net")
            d.rect(x + k * cw, y + i * (lane + 0.5), cw + 0.2, lane, fill if v else "#EEF1F4")


def build_08():
    d = Doc("08-laerer-oversikt", 1600, 1000, "Lag for lag, Oversikt for Faglærer",
            "60 Klassespill på én skjerm: status, hvem spillet venter på, KI-seter og nær overtakelse, trakten, matriseveggen med netto lager per uke, og klassens kostnadsbilde mot fjoråret.")
    fx0, fy0, fw, fh = 40, 20, 1520, 960
    d.rect(fx0, fy0, fw, fh, PAPER, HAIR2, 1.2, 8)
    X = fx0 + 24
    spill = KL["spill"]
    counts = {k: sum(1 for s in spill if s["status"] == k) for k in ("venter", "pauset", "pågår", "ferdig")}
    assert counts == {"venter": 4, "pauset": 2, "pågår": 13, "ferdig": 41}
    d.t(X, fy0 + 36, "Oversikt", 24, 700, INK)
    d.t(X + 104, fy0 + 36, "class-of-1994, IBE160", 15, 400, INK2)
    d.t(fx0 + fw - 24, fy0 + 36, f"{counts['ferdig']} ferdig · {counts['pågår'] + counts['pauset']} pågår ({counts['pauset']} pauset) · {counts['venter']} venter · Spillfrist ti. 8. des", 15, 400, INK, "end")

    near = sorted([s for s in spill if s["status"] == "venter"], key=lambda s: -s["ventet_timer"])
    top = near[0]
    yn = fy0 + 76
    d.rect(X, yn - 20, 760, 36, REDF, None, 1, 4)
    d.t(X + 12, yn + 3, f"Spill {top['spill']} venter på {top['navn']} ({top['venter_paa']}) i {top['ventet_timer']} t. KI overtar om {24 - top['ventet_timer']} t.", 15, 600, INK)
    d.button(X + 560, yn - 15, 92, 26, "Send Melding", size=13)
    d.button(X + 658, yn - 15, 92, 26, "Pause spillet", primary=False, size=13)
    d.t(X, yn + 38, "Venter også: " + ", ".join(f"spill {s['spill']} {s['navn']} ({s['venter_paa']}) {s['ventet_timer']} t" for s in near[1:]), 14, 400, INK)
    pa = [s for s in spill if s["status"] == "pauset"]
    ki = sum(1 for s in spill if s["ki_seter"] > 0)
    kisum = sum(s["ki_seter"] for s in spill)
    d.t(X, yn + 60, "Pause: " + ", ".join(f"spill {s['spill']} (Uke {s['uke']})" for s in pa) + f", fortsetter {pa[0]['fortsetter']}. {kisum} KI-spillere i {ki} spill.", 14, 400, INK)

    # Trakt
    tx = fx0 + 840
    tr = KL["traktA"]
    steps = [("Registrert", tr["registrert"]), ("Klassespill ferdig", tr["klassespill_ferdig"]), ("Debrief ferdig", tr["debrief_ferdig"]),
             ("Quiz bestått", tr["quiz_bestått"]), ("Replay ferdig", tr["replay_ferdig"]), ("Test levert", tr["test_levert"]), ("KI-vurdering klar", tr["ki_vurdering_klar"])]
    col_w = (fx0 + fw - 24 - tx) / 7
    d.t(tx, yn - 4, "Trakten", 14, 600, INK)
    for i, (lab, v) in enumerate(steps):
        xx = tx + i * col_w
        hh = 34 * v / steps[0][1]
        base = yn + 40
        d.rect(xx, base - hh, col_w - 8, max(hh, 1), ORD if v else HAIR)
        d.t(xx, base + 17, v, 14, 600, INK)
        for j, ln in enumerate(wrap(lab, col_w - 6, 12)):
            d.t(xx, base + 31 + j * 14, ln, 12, 400, INK2)

    # Filter og lagvelger
    yf = fy0 + 196
    d.line(X, yf - 24, fx0 + fw - 24, yf - 24, HAIR, 1)
    labs = [("Alle", len(spill)), ("Venter", counts["venter"]), ("Pause", counts["pauset"]), ("Pågår", counts["pågår"]), ("Ferdig", counts["ferdig"]), ("Med KI", ki)]
    xx = X
    for i, (lab, c) in enumerate(labs):
        s = f"{lab} {c}"
        wd = text_w(s, 13) + 18
        d.rect(xx, yf - 13, wd, 24, INK if i == 0 else PAPER, None if i == 0 else HAIR2, 1, 4)
        d.t(xx + wd / 2, yf + 4, s, 13, 600, PAPER if i == 0 else INK, "middle")
        xx += wd + 6
    tabs(d, X + 470, yf - 13, 300, ["Netto lager", "Ordre", "Kostnad"], "Netto lager", h=24, size=13)
    rl = ["Detaljist", "Grossist", "Distributør", "Fabrikk"]
    xx = X + 790
    d.t(xx, yf + 4, "Rolle:", 13, 400, INK2)
    xx += 42
    for r in rl:
        wd = text_w(r, 13) + 14
        d.rect(xx, yf - 13, wd, 24, INK if r == "Fabrikk" else PAPER, None if r == "Fabrikk" else HAIR2, 1, 4)
        d.t(xx + wd / 2, yf + 4, r, 13, 600, PAPER if r == "Fabrikk" else INK, "middle")
        xx += wd + 4

    # Matriseveggen
    rank = {"venter": 0, "pauset": 1, "pågår": 2, "ferdig": 3}
    ordered = sorted(spill, key=lambda s: (rank[s["status"]], -(s.get("ventet_timer") or 0),
                                           -s["uke"] if s["status"] != "ferdig" else s["kjedekost"]))
    cw, ch = 12.5, 9
    wx = X + 96
    yh = yf + 40
    d.t(X, yh, "Spill", 12, 600, INK2)
    d.t(X + 30, yh, "Status", 12, 600, INK2)
    for k in (1, 12, 24, 36):
        d.t(wx + (k - 0.5) * cw, yh, k, 12, 400, INK3, "middle")
    ex = wx + 36 * cw + 10
    d.t(ex + 20, yh, "Uke", 12, 600, INK2, "end")
    d.t(ex + 30, yh, "Venter på", 12, 600, INK2)
    d.t(ex + 200, yh, "KI", 12, 600, INK2, "end")
    d.t(ex + 262, yh, "Kjede, kr", 12, 600, INK2, "end")
    y = yh + 10
    grp = None
    for sp in ordered:
        g = "Ferdig, lavest kjedekost øverst" if sp["status"] == "ferdig" else ("Venter og pause" if sp["status"] in ("venter", "pauset") else "Pågår")
        if g != grp:
            grp = g
            y += 4
            d.t(X, y + 9, g, 12, 600, INK)
            y += 13
        if sp["spill"] == top["spill"]:
            d.rect(X - 6, y - 2, ex + 270 - X + 6, ch + 4, REDF, None, 1, 2)
        d.t(X, y + 8.5, sp["spill"], 11, 600, INK)
        d.t(X + 30, y + 8.5, status_txt(sp), 11, 400, INK if sp["status"] != "ferdig" else INK2)
        wall_row(d, wx, y, sp, "Fabrikk", cw, ch)
        d.t(ex + 20, y + 8.5, sp["uke"], 11, 400, INK, "end")
        if sp["status"] == "venter":
            d.t(ex + 30, y + 8.5, f"{sp['navn']}, {sp['venter_paa']}, {sp['ventet_timer']} t", 11, 600 if sp is top else 400, INK)
        elif sp["status"] == "pauset":
            d.t(ex + 30, y + 8.5, f"Pause, {sp['fortsetter']}", 11, 400, INK2)
        if sp["ki_seter"]:
            d.t(ex + 200, y + 8.5, f"KI {sp['ki_seter']}", 11, 400, INK, "end")
        d.t(ex + 262, y + 8.5, nf(sp["kjedekost"], 0), 11, 400, INK, "end")
        y += ch + 1.6
    d.t(X, fy0 + fh - 12, "Celle: netto lager per uke for valgt Rolle. Blått er lager, rødt restordre, grått null. Svart strek: der spillet er nå.", 12, 400, INK2)
    link(d, ex + 262, fy0 + fh - 12, "Vis som tabell", 13, a="end")

    # Høyre: klassens kostnadsbilde og klassens kjede
    rx = ex + 300
    rw = fx0 + fw - 24 - rx
    yr = yf + 40
    d.t(rx, yr, "Kjedekost per spill", 16, 600, INK)
    F = KL["ferdige"]["kjedekost"]
    FJ = KL["fjoraaret"]
    lo_, hi_ = 0, 4000
    sx = lambda v: rx + (v - lo_) / (hi_ - lo_) * rw
    yd = yr + 50
    d.line(rx, yd + 30, rx + rw, yd + 30, HAIR2, 1)
    for v in (0, 1000, 2000, 3000, 4000):
        d.line(sx(v), yd + 30, sx(v), yd + 34, HAIR2, 1)
        d.t(sx(v), yd + 48, nf(v, 0), 12, 400, INK3, "middle")
    d.rect(sx(F["q1"]), yd - 18, sx(F["q3"]) - sx(F["q1"]), 40, TINT)
    # prikker, stablet i søyler av 100 kr
    stack = {}
    for s in sorted(FERDIG, key=lambda s: s["kjedekost"]):
        b = int(s["kjedekost"] // 100)
        n = stack.get(b, 0)
        stack[b] = n + 1
        d.circle(sx(b * 100 + 50), yd + 24 - n * 8, 3.4, ORD)
    d.line(sx(F["median"]), yd - 26, sx(F["median"]), yd + 30, INK, 1.6)
    d.t(sx(F["median"]) + 4, yd - 30, f"Median {nf(F['median'], 0)}", 12, 700, INK)
    d.line(sx(FJ["median_kjedekost"]), yd - 10, sx(FJ["median_kjedekost"]), yd + 30, INK, 1.2, dash="3 3")
    d.t(sx(FJ["median_kjedekost"]) + 4, yd - 12, f"Fjoråret {nf(FJ['median_kjedekost'], 0)}", 12, 400, INK2)
    d.para(rx, yd + 70, f"{len(FERDIG)} ferdige spill, ett punkt per spill. Lys flate: midterste halvdel ({nf(F['q1'], 0)} til {nf(F['q3'], 0)} kr). Fjoråret: {FJ['spill']} spill.", rw, 12, 16, fill=INK2)

    # Klassen per uke
    yw = yd + 130
    d.t(rx, yw, "Klassens kostnad per uke, ferdige spill", 14, 600, INK)
    axw = Axis(rx + 40, rw - 40, 1, 36)
    hb = 80
    mxw = max(a + b for a, b in CLASS_WEEK)
    topv = 1000 * (int(mxw // 1000) + 1)
    Y = grid(d, axw, yw + 12, hb, 0, topv, (0, topv), 12)
    u = hb / topv
    for k in range(36):
        a, b = CLASS_WEEK[k]
        x0 = axw.xc(k + 1) - (axw.slot - 1.5) / 2
        d.rect(x0, yw + 12 + hb - a * u, axw.slot - 1.5, a * u, BLUE)
        d.rect(x0, yw + 12 + hb - (a + b) * u, axw.slot - 1.5, b * u, RED)
    xaxis(d, axw, yw + 12 + hb + 15, [1, 12, 24, 36], size=12)
    rs = sum(b for _, b in CLASS_WEEK)
    ls_ = sum(a for a, _ in CLASS_WEEK)
    d.t(rx, yw + 12 + hb + 36, f"Restordre {nf(rs, 0)} kr · Lager {nf(ls_, 0)} kr", 12, 600, INK)

    # Klassens kjede: median netto lager per Rolle og uke
    yk = yw + 172
    d.t(rx, yk, "Klassens kjede: median netto lager", 14, 600, INK)
    axk = Axis(rx + 66, rw - 66, 1, 36)
    rows = [(r, (lambda rr: (lambda k: int(round(MED_NET[rr][k - 1]))))(r), "net") for r in CHAIN]
    yb = yk + 10
    for i, (lab, fn, kind) in enumerate(rows):
        yy = yb + i * 18
        d.t(rx, yy + 13, lab, 12, 400, INK)
        for k in range(1, 37):
            fill, _ = cell_style(fn(k), "net")
            d.rect(axk.xl(k), yy, axk.slot - 1, 16, fill if fn(k) else "#EEF1F4")
        mn = min(range(1, 37), key=fn)
        d.t(axk.xc(mn), yy + 12.5, sg(fn(mn)), 11, 700, PAPER if abs(fn(mn)) >= 20 else INK, "middle")
    xaxis(d, axk, yb + 4 * 18 + 14, [1, 12, 24, 36], size=12)
    d.para(rx, yb + 4 * 18 + 34, "Tallet i raden er laveste median. Samme form som i nesten hvert spill: struktur, ikke personer.", rw, 12, 16, fill=INK2)
    ym = yb + 4 * 18 + 84
    d.t(rx, ym, "Mønstre i beslutningsloggen, hele klassen", 14, 600, INK)
    ym += 22
    for k, v in KL["moenstre"].items():
        d.t(rx, ym, k, 13, 400, INK)
        d.t(rx + rw, ym, v, 13, 600, INK, "end")
        d.line(rx, ym + 7, rx + rw, ym + 7, HAIR, 1)
        ym += 24
    link(d, rx, ym + 6, "Åpne Spillinnsikt for ett spill", 13)
    d.button(rx, fy0 + fh - 60, rw / 2 - 5, 36, "Vis i plenum", primary=False, size=13)
    d.button(rx + rw / 2 + 5, fy0 + fh - 60, rw / 2 - 5, 36, "Klasserapport", primary=False, size=13)
    d.demodata(fx0 + fw - 24, fy0 + fh - 12, a="end")
    d.save()


if __name__ == "__main__":
    build_07()
    build_08()
