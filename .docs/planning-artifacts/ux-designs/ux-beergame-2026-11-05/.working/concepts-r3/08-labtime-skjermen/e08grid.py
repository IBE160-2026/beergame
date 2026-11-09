"""Runde 3, konsept 08 Labtime-skjermen: kostnad, kjede, matrise og selve rutenettet.
Alt deler Meteogrammets palett og tidsakse. Bygget stopper hvis tallene ikke stemmer med loggen."""
from e08lib import *

HOLD, BACK = 0.50, 1.00

# Matrisetrinn med tall i cellene (lyse; tekst i INK har kontrast >= 6,9:1 på mørkeste trinn)
CELL_B = ["#E3EDF7", "#C2D8EC", "#9CBFDF"]   # lager
CELL_R = ["#F9E8E6", "#EFC9C4", "#E2A49C"]   # restordre
CELL_S = ["#F2F5F8", "#D9E1E9", "#BCC9D6"]   # strømmer, marine/grå
# Matriseveggen uten tall (validert ordinalt, lyseste trinn >= 2:1 mot hvit)
WALL_B = ["#97B9D9", "#6597C6", "#2B6CA3", "#1A4670"]
WALL_R = ["#E2A9A2", "#CD7A70", "#B5423A", "#7E2C26"]
WALL_0 = "#EEF1F4"


def _kost_methods():
    def lagerkost(self, w):
        return self.lager[w - 1] * HOLD

    def restkost(self, w):
        return self.rest[w - 1] * BACK

    def ukekost(self, w):
        return self.lagerkost(w) + self.restkost(w)

    def cum_lager(self, w):
        return sum(self.lagerkost(k) for k in range(1, w + 1))

    def cum_rest(self, w):
        return sum(self.restkost(k) for k in range(1, w + 1))

    for f in (lagerkost, restkost, ukekost, cum_lager, cum_rest):
        setattr(Seat, f.__name__, f)


_kost_methods()

G = Seat()
K = FX["spill17"]
SEATS = {r: Seat(r) for r in ROLES}
BARE = Seat("Grossist", FX["bare_sara_teller_paa_vei"])
ALLE = Seat("Grossist", FX["alle_teller_paa_vei"])
SEATS_ALLE = {r: Seat(r, FX["alle_teller_paa_vei"]) for r in ROLES}
DEM = K["serier"]["demand"]
KL = FX["klasse"]

# ---------- Kontroller: tall, grafer og kostnad må stemme med loggen for alle uker ----------
for _r, _s in SEATS.items():
    for _w in range(1, _s.n + 1):
        assert abs(_s.cum_lager(_w) + _s.cum_rest(_w) - _s.kostsum(_w)) < 1e-9, ("kost", _r, _w)
        assert _s.lager[_w - 1] == 0 or _s.rest[_w - 1] == 0, ("lager og restordre samtidig", _r, _w)
        if _w > 1:
            assert _s.net(_w) == _s.net(_w - 1) + _s.levering(_w) - _s.inn(_w), ("balanse", _r, _w)
    assert abs(_s.kostsum(36) - K["kost_per_rolle"][_r]) < 1e-9, _r
assert abs(sum(s.kostsum(36) for s in SEATS.values()) - K["kjedekost"]) < 1e-9
for _w in range(3, 37):
    assert G.inn(_w) == SEATS["Detaljist"].order(_w - 2), ("P4: ordre inn er Idas ordre", _w)
assert G.kostsum(11) == 68.0 and G.ukekost(11) == 13.0 and G.posisjon(11) == 3
for _S, _src in ((BARE, "bare_sara_teller_paa_vei"), (ALLE, "alle_teller_paa_vei")):
    _c = sum(Seat(r, FX[_src]).kostsum(36) for r in ROLES)
    assert abs(_c - FX[_src]["kjedekost"]) < 1e-9, _src


def kr(v, dec=2):
    return f"{nf(v, dec)} kr"


def cell_net(v):
    if v == 0:
        return PAPER
    a = abs(v)
    i = 0 if a < 10 else (1 if a < 20 else 2)
    return CELL_B[i] if v > 0 else CELL_R[i]


def cell_flow(v):
    if v <= 4:
        return PAPER
    return CELL_S[0] if v < 10 else (CELL_S[1] if v < 20 else CELL_S[2])


def cell_cost(v, kind):
    if v == 0:
        return PAPER
    i = 0 if v < 10 else (1 if v < 25 else 2)
    return (CELL_R if kind == "rest" else CELL_B)[i]


def wall_net(v):
    a = abs(v)
    if a <= 2:
        return WALL_0
    i = 0 if a <= 10 else (1 if a <= 25 else (2 if a <= 45 else 3))
    return WALL_B[i] if v > 0 else WALL_R[i]


def arrow(d, x1, y, x2, col=INK, sw=1.2, head=6):
    """Vannrett pil fra x1 til x2, hodet tegnet som trekant."""
    s = 1 if x2 > x1 else -1
    d.line(x1, y, x2 - s * head * 0.6, y, col, sw)
    d.path(f"M{x2:.1f} {y:.1f} L{x2 - s * head:.1f} {y - head * 0.55:.1f} L{x2 - s * head:.1f} {y + head * 0.55:.1f} Z", col)


def matrix(d, ax, y, rows, wfrom, wto, now=None, rh=17, size=12, lx=None, lsize=None, dec=0, frame_now=True, lw=None):
    """Uker som kolonner på samme akse som grafen over. rows: (etikett, fn(uke) -> verdi|None|(verdi, art), art).
    art: net, flow, plain, cost_l, cost_r, cost, open (kjent ankomst), typed (tastet nå), lock (låst rad)."""
    lsize = lsize or size
    lx = lx if lx is not None else ax.x0 - 8
    cw = ax.slot
    for i, (lab, fn, kind) in enumerate(rows):
        yy = y + i * rh
        ty = yy + rh * 0.5 + size * 0.34
        d.t(lx, yy + rh * 0.5 + lsize * 0.34, lab, lsize, 600 if kind == "bold" else 400, INK if kind != "lock" else INK3,
            "end" if lx < ax.x0 else "start")
        if kind == "lock":
            d.rect(ax.xl(wfrom) + 0.5, yy + 0.5, ax.x1 - ax.xl(wfrom) - 1, rh - 1, TINT)
            d.t(ax.xl(wfrom) + 8, ty, fn if isinstance(fn, str) else "Åpnes i Replay", size, 400, INK2)
            continue
        for w in range(wfrom, wto + 1):
            v = fn(w)
            if v is None:
                continue
            xx = ax.xl(w) + 0.5
            k = kind
            if isinstance(v, tuple):
                v, k = v
            if k == "open":
                d.rect(xx + 1.5, yy + 2, cw - 4, rh - 4, PAPER, BLUE, 1)
                d.t(xx + cw / 2 - 0.5, ty, v, size, 400, INK, "middle")
                continue
            if k == "typed":
                d.rect(xx + 1.5, yy + 2, cw - 4, rh - 4, PAPER, INK, 1.5)
                d.t(xx + cw / 2 - 0.5, ty, v, size, 700, INK, "middle")
                continue
            if k == "net":
                fill, s = cell_net(v), sg(v)
            elif k == "flow":
                fill, s = cell_flow(v), str(v)
            elif k in ("cost_l", "cost_r"):
                fill = cell_cost(v, "rest" if k == "cost_r" else "lager")
                s = nf(v, dec) if v else "0"
            elif k == "cost":
                fill, s = PAPER, (nf(v, dec) if v else "0")
            else:
                fill, s = PAPER, (v if isinstance(v, str) else sg(v))
            d.rect(xx, yy + 0.5, cw - 1, rh - 1, fill)
            d.t(xx + cw / 2 - 0.5, ty, s, size, 700 if (now == w and frame_now) else 400, INK, "middle")
    if now is not None and frame_now:
        d.rect(ax.xl(now), y, cw, rh * len(rows), "none", INK, 1.2)
    return y + rh * len(rows)


def cost_bars(d, ax, y0, h, g, wfrom, wto, scale=40, x1=None):
    """Ukekostnad: lagerkost i blått, restordrekost i rødt. Bare én av dem kan være over null i en uke."""
    u = h / scale
    bw = max(ax.slot - 2.5, 2)
    base = y0 + h
    for w in range(wfrom, wto + 1):
        lk, rk = g.lagerkost(w), g.restkost(w)
        x = ax.xc(w) - bw / 2
        if lk:
            d.rect(x, base - lk * u, bw, lk * u, BLUE)
        if rk:
            d.rect(x, base - (lk + rk) * u, bw, rk * u, RED)
    d.line(ax.x0, base, x1 or ax.x1, base, HAIR2, 1)


def cum_cost_area(d, ax, y0, h, g, wfrom, wto, top, lw=1.6):
    """Akkumulert kostnad, stablet: lager nederst (blå), restordre over (rød). Sann null."""
    Y = yscale(y0, h, 0, top)
    pl = [(ax.xc(w), Y(g.cum_lager(w))) for w in range(wfrom, wto + 1)]
    pt = [(ax.xc(w), Y(g.cum_lager(w) + g.cum_rest(w))) for w in range(wfrom, wto + 1)]
    ln = lambda pts: "M" + " L".join(f"{a:.1f} {b:.1f}" for a, b in pts)
    d.path(ln(pt) + " L" + " L".join(f"{a:.1f} {b:.1f}" for a, b in reversed(pl)) + " Z", REDF)
    d.path(ln(pl) + f" L{pl[-1][0]:.1f} {Y(0):.1f} L{pl[0][0]:.1f} {Y(0):.1f} Z", BLUEF)
    d.path(ln(pt), stroke=INK, sw=lw)
    d.line(ax.xl(wfrom), Y(0), ax.xr(wto), Y(0), HAIR2, 1)
    return Y


# ---------- Kjedevisningen ----------
def node_box(d, cx, yb, net, u, bw, lw=1.2):
    """Netto lager som boks på sann skala: lager over grunnlinja (blått), restordre under (rødt)."""
    if net > 0:
        d.rect(cx - bw / 2, yb - net * u, bw, net * u, BLUEF, BLUE, lw)
    elif net < 0:
        d.rect(cx - bw / 2, yb, bw, -net * u, REDF, RED, lw)
    else:
        d.line(cx - bw / 2, yb, cx + bw / 2, yb, INK, 2.4)


def chain_seat(d, x, y, w, g, wk, typed=None, u=1.5, ls=13, pos=False, compact=False):
    """Setets eget ledd. Nedstrøms til venstre, oppstrøms til høyre, i samme rekkefølge som Rollene.
    Varer går mot venstre, ordre mot høyre. På vei leses i samme retning som tidsaksen: neste Uke nærmest.
    Returnerer bunnen av båndet."""
    yo = y + ls                        # ordrelinja
    ypv = yo + ls + 12                 # linja med På vei
    yb = ypv + 8 + ls + 26 * u         # grunnlinja for varer
    lab_w = text_w("Distributør", ls) + 4
    xD = x
    nbw = 40 if not compact else 30
    xS = x + lab_w + (78 if not compact else 52)
    over = g.overdue(wk)
    nslot = 4 + (1 if over > 0 else 0)
    px0 = xS + nbw / 2 + (70 if not compact else 52)
    xU = x + w - lab_w - 10
    pw = (xU - px0) / nslot
    d.t(xD, yb - 4, "Detaljist", ls, 600, INK)
    d.t(xD, yb + ls + 4, "nedstrøms", ls, 400, INK2)
    d.t(x + w, yb - 4, "Distributør", ls, 600, INK, "end")
    d.t(x + w, yb + ls + 4, "oppstrøms", ls, 400, INK2, "end")
    s_in = f"Ordre inn {g.inn(wk)}"
    d.t(xD, yo, s_in, ls, 600, INK)
    arrow(d, xD + text_w(s_in, ls) + 6, yo - ls * 0.32, xS - 4, INK, 1)
    if typed is not None:
        s = f"Din ordre {typed}"
        d.t(x + w, yo, s, ls, 700, INK, "end")
        arrow(d, xS + 4, yo - ls * 0.32, x + w - text_w(s, ls) - 8, INK, 1.4)
    else:
        s = "Din ordre"
        d.t(x + w, yo, s, ls, 400, INK3, "end")
        d.line(xS + 4, yo - ls * 0.32, x + w - text_w(s, ls) - 8, yo - ls * 0.32, HAIR2, 1, dash="3 3")
    net = g.net(wk)
    d.line(xS - nbw / 2 - 6, yb, xS + nbw / 2 + 6, yb, INK, 1)
    node_box(d, xS, yb, net, u, nbw)
    lab = f"Lager {g.lager[wk - 1]}" if net >= 0 else f"Restordre {g.rest[wk - 1]}"
    d.t(xS, yb - max(net, 0) * u - 6, lab, ls, 700, INK, "middle")
    ya = yb + ls + 4 - ls * 0.32
    gx = xD + text_w("nedstrøms", ls) + 8
    arrow(d, xS - nbw / 2 - 6, ya, gx, BLUE, 1.6)
    d.t(xS - nbw / 2 - 4, ya + ls + 4, f"Sendt {g.sendt(wk)}", ls, 400, INK, "end")
    arrow(d, px0 - 4, ya, xS + nbw / 2 + 6, BLUE, 1.6)
    d.t(xS + nbw / 2 + 4, ya + ls + 4, f"Levering {g.levering(wk)}", ls, 400, INK)
    arrs = g.arrivals(wk, typed)
    d.line(px0, yb, xU, yb, HAIR2, 1)
    bw = min(pw - 8, 30)
    for i, (week, qty) in enumerate(arrs):
        cx = px0 + (i + 0.5) * pw
        if qty is None:
            d.rect(cx - bw / 2, yb - 14, bw, 14, "none", INK, 1.1, extra='stroke-dasharray="3 3"')
        else:
            is_t = week == wk + 4
            d.rect(cx - bw / 2, yb - qty * u, bw, qty * u, PAPER, INK if is_t else BLUE, 1.6 if is_t else 1.1)
            d.t(cx, yb - qty * u - 4, qty, ls, 700 if is_t else 400, INK, "middle")
        d.t(cx, yb + ls + 4, (f"Uke {week}" if not compact else str(week)), ls, 400, INK3, "middle")
    if over > 0:
        cx = px0 + (nslot - 0.5) * pw
        hh = min(over, 26) * u
        d.rect(cx - bw / 2, yb - hh, bw, hh, PAPER, GREY, 1.1, extra='stroke-dasharray="3 2"')
        d.t(cx, yb - hh - 4, over, ls, 400, INK, "middle")
        d.t(cx, yb + ls + 4, "uten dato" if not compact else "?", ls, 400, INK3, "middle")
    pv = g.paavei(wk)
    s = f"På vei {pv}" + (f" + {typed}" if typed is not None else "")
    d.t(px0, ypv, s, ls, 600, INK)
    if not compact:
        d.t(px0 + text_w(s, ls) + 14, ypv, "kommer om lag 4 uker etter ordren. Bestilt, ikke garantert.", ls, 400, INK2)
    yend = max(ya + ls + 8, yb + max(-net, 0) * u + 4)
    if pos:
        p = g.posisjon(wk)
        s2 = f"Posisjon = {g.lager[wk - 1]} − {g.rest[wk - 1]} + {pv} = {p}" + (f".  Med {typed}: {p + typed}" if typed is not None else "")
        d.t(xS - nbw / 2, yend + ls + 6, s2, ls, 600, INK)
        yend += ls + 10
    return yend


def chain_full(d, x, y, w, wk, seats, u=1.0, ls=13, cost=True, demand=None, hi=60, names=True, you="Grossist"):
    """Hele kjeden, fire ledd pluss kundene. Kundene til venstre, Fabrikk til høyre, samme skala i alle bokser.
    Øverst: ordren hvert ledd sendte oppstrøms. Under grunnlinja: restordre. Åpen boks til høyre: på vei inn til leddet."""
    order = ["Detaljist", "Grossist", "Distributør", "Fabrikk"]
    kund_w = 70
    seg = (w - kund_w) / 4
    yo = y + ls
    ynm = yo + ls + 10
    yb = ynm + (ls + 4 if names else 0) + 8 + ls + hi * u
    nbw = 24
    d.line(x, yb, x + w, yb, HAIR2, 1)
    d.t(x, ynm, "Kundene", ls, 600, INK)
    if demand is not None:
        d.t(x, yb + ls + 4, f"kjøpte {demand}", ls, 400, INK)
    d.t(x, yo, "Ordre", ls, 400, INK2)
    for i, r in enumerate(order):
        S = seats[r]
        x0 = x + kund_w + i * seg
        cx = x0 + nbw / 2
        net = S.net(wk)
        node_box(d, cx, yb, net, u, nbw)
        d.t(x0, ynm, r + (" (deg)" if r == you else ""), ls, 600, INK)
        if names:
            d.t(x0, ynm + ls + 4, NAVN[r], ls, 400, INK2)
        st = f"Lager {S.lager[wk - 1]}" if net >= 0 else f"Restordre {S.rest[wk - 1]}"
        yst = yb + ls + 4 + max(-net, 0) * u
        d.t(x0, yst, st, ls, 600 if net < 0 else 400, INK)
        if cost:
            d.t(x0, yst + ls + 4, kr(S.kostsum(wk)), ls, 400, INK2)
        pv = S.paavei(wk)
        pxx = x0 + nbw + 6
        d.rect(pxx, yb - pv * u, 16, pv * u, PAPER, BLUE, 1)
        d.t(pxx + 8, yb - pv * u - 4, pv, ls - 1, 400, INK, "middle")
        d.t(x0, yo, S.order(wk), ls, 700 if r == you else 600, INK)
        arrow(d, x0 + text_w(str(S.order(wk)), ls) + 6, yo - ls * 0.32, x0 + seg - 10, INK3, 0.8, 5)
    return yb
