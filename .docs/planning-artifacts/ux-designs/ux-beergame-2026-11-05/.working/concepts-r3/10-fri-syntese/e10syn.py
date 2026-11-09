"""Runde 3 for konsept 10 Fri syntese: kostnad, matrise, kjedebåndet langs tidsaksen og hele kjeden.
Bygger på e10lib (Meteogrammets byggeklosser). Kontrollen nederst stopper bygget hvis tall, grafer og kostnad
ikke stemmer med loggen."""
from e10lib import *

LAGERKOST, RESTKOST = 0.50, 1.00
ROLES_UP = ["Detaljist", "Grossist", "Distributør", "Fabrikk"]  # nedstrøms til venstre, oppstrøms til høyre
UPSTREAM = {"Detaljist": "Grossist", "Grossist": "Distributør", "Distributør": "Fabrikk", "Fabrikk": "produksjon"}
DOWNSTREAM = {"Detaljist": "kundene", "Grossist": "Detaljist", "Distributør": "Grossist", "Fabrikk": "Distributør"}


def _uke_kost(self, w):
    return self.lager[w - 1] * LAGERKOST + self.rest[w - 1] * RESTKOST


def _lagerkost(self, w):
    return self.lager[w - 1] * LAGERKOST


def _restkost(self, w):
    return self.rest[w - 1] * RESTKOST


def _cum(self, w, kind="sum"):
    f = {"sum": self.uke_kost, "lager": self.lagerkost, "rest": self.restkost}[kind]
    return sum(f(k) for k in range(1, w + 1))


def _overdue_safe(self, w):
    return max(0, self.paavei(w) - sum(self.order(k) for k in (w - 3, w - 2, w - 1)))


Seat.uke_kost = _uke_kost
Seat.lagerkost = _lagerkost
Seat.restkost = _restkost
Seat.cum = _cum
Seat.overdue = _overdue_safe


def kr(v):
    """Kroner i matriseceller: heltall uten desimaler, halve med én."""
    return str(int(v)) if float(v).is_integer() else f"{v:.1f}".replace(".", ",")


# ---------- Kontrollen: tall, grafer og kostnad må stemme med loggen ----------
def check_log():
    for key in ("spill17", "bare_sara_teller_paa_vei", "alle_teller_paa_vei"):
        src = FX[key]
        tot = 0.0
        for r in ROLES:
            S = Seat(r, src)
            c = 0.0
            for w in range(1, S.n + 1):
                assert S.net(w) == S.lager[w - 1] - S.rest[w - 1]
                assert S.lager[w - 1] == 0 or S.rest[w - 1] == 0, (key, r, w)
                if w >= 2:
                    assert S.net(w) == S.net(w - 1) + S.levering(w) - S.inn(w), (key, r, w)
                c += S.uke_kost(w)
                assert abs(c - S.kostsum(w)) < 1e-9, (key, r, w)
                assert abs(S.cum(w, "lager") + S.cum(w, "rest") - S.kostsum(w)) < 1e-9
            assert abs(c - src["kost_per_rolle"][r]) < 1e-9, (key, r)
            tot += c
        assert abs(tot - src["kjedekost"]) < 1e-9, key
    # Klassespillene: ukeskostnad fra netto lager, summert, må gi kjedekosten i oversikten
    for sp in FX["klasse"]["spill"]:
        c = sum(v * LAGERKOST if v > 0 else -v * RESTKOST for r in ROLES for v in sp["netto_lager"][r])
        assert abs(c - sp["kjedekost"]) < 0.51, sp["spill"]
        assert all(len(sp["netto_lager"][r]) == sp["uke"] for r in ROLES), sp["spill"]
    g = Seat()
    assert (g.lager[10], g.rest[10], g.inn(11), g.levering(11), g.sendt(11), g.paavei(11)) == (0, 13, 8, 4, 4, 16)
    assert g.kostsum(11) == 68.0 and g.posisjon(11) == 3
    assert [q for _, q in g.arrivals(11, 24)] == [4, 4, 8, 24]
    assert sum(q for _, q in g.arrivals(11, 24)[:3]) == g.paavei(11)
    assert [g.order(k) for k in range(1, 11)] == [4] * 9 + [8]


check_log()


# ---------- Matrisens trinn (validert med validate_palette.js, se concept.md) ----------
NEG = ("#E3A7A0", "#D1837A", "#B5423A")   # restordre 1–9, 10–24, 25+
POS = ("#97BBDC", "#6F9DC8", "#2B6CA3")   # lager 1–9, 10–24, 25+
SEQ = ("#A5B8CA", "#8399B0", "#4D6680")   # strøm 6–11, 12–19, 20+ (0–5 uten fyll)


def _lin(c):
    c = c / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def lum(hx):
    r, g, b = (int(hx[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def net_fill(v):
    if v == 0:
        return None, INK
    a = abs(v)
    i = 0 if a < 10 else (1 if a < 25 else 2)
    return (POS if v > 0 else NEG)[i], (PAPER if i == 2 else INK)


def flow_fill(v):
    if v < 6:
        return None, INK
    i = 0 if v < 12 else (1 if v < 20 else 2)
    return SEQ[i], (PAPER if i == 2 else INK)


for _fill, _txt in [(c, PAPER if i == 2 else INK) for ramp in (NEG, POS, SEQ) for i, c in enumerate(ramp)] + \
        [(REDF, INK), (BLUEF, INK), (TINT, INK)]:
    assert contrast(_fill, _txt) >= 4.5, (_fill, _txt, contrast(_fill, _txt))


def mcell(d, x, y, w, h, v, kind="net", size=13, bold=False, text=None, gap=1.0, outline=False):
    """Én celle. Tallet står alltid i cellen; fargen er bare en ekstra lesning."""
    if kind == "net":
        fill, tc = net_fill(v)
    elif kind == "flow":
        fill, tc = flow_fill(v)
    elif kind == "rest":
        fill, tc = (REDF, INK) if v else (None, INK)
    elif kind == "lager":
        fill, tc = (BLUEF, INK) if v else (None, INK)
    else:
        fill, tc = None, INK
    if fill:
        d.rect(x + gap, y + gap, w - 2 * gap, h - 2 * gap, fill, rx=2)
    else:
        d.rect(x + gap, y + gap, w - 2 * gap, h - 2 * gap, PAPER, HAIR, 1, 2)
    if outline:
        d.rect(x + gap / 2, y + gap / 2, w - gap, h - gap, "none", INK, 1.6, 2)
    if text != "":
        d.t(x + w / 2, y + h / 2 + size * 0.35, text if text is not None else sg(v), size, 700 if bold else 400, tc, "middle")


def cost_cell(d, x, y, w, h, g, wk, size=13, bold=False, outline=False):
    """Ukeskostnaden i én celle: rød tone når det er restordre, blå når det er lager."""
    v = g.uke_kost(wk)
    kind = "rest" if g.rest[wk - 1] else ("lager" if g.lager[wk - 1] else "plain")
    mcell(d, x, y, w, h, v, kind, size, bold, kr(v), outline=outline)


def arrow_head(d, x, y, direction="left", s=5, col=INK, sw=1.4):
    if direction == "left":
        d.path(f"M{x + s:.1f} {y - s * 0.8:.1f} L{x:.1f} {y:.1f} L{x + s:.1f} {y + s * 0.8:.1f}", stroke=col, sw=sw)
    elif direction == "right":
        d.path(f"M{x - s:.1f} {y - s * 0.8:.1f} L{x:.1f} {y:.1f} L{x - s:.1f} {y + s * 0.8:.1f}", stroke=col, sw=sw)
    elif direction == "up":
        d.path(f"M{x - s * 0.8:.1f} {y + s:.1f} L{x:.1f} {y:.1f} L{x + s * 0.8:.1f} {y + s:.1f}", stroke=col, sw=sw)


# ---------- Kjedebåndet: setets ledd tegnet langs tidsaksen ----------
def band_height(u=1.0, ls=13, maxup=30, maxdn=40, header=True):
    up = (ls + 8 if header else 0) + ls + 6 + maxup * u
    return up, up + max(maxdn * u, 36) + 4


def chain_band(d, g, ax, top, now, typed=None, u=1.0, ls=13, x_left=None, header=True, left=True, posisjon=False,
               maxup=30, maxdn=40, numbers=True, show_typed=True, labels=True, overdue_note=True, head_left=None, mark_week=None):
    """Det som er på vei står over uka det ventes, lageret står ved nå, det som er sendt går ut til venstre.
    Oppstrøms ligger til høyre fordi det som kommer senere ligger til høyre på tidsaksen.
    Samme skala (u piksler per enhet) i alle uker, så en stor uke ser stor ut."""
    up, tot = band_height(u, ls, maxup, maxdn, header)
    yb = top + up
    bw = max(ax.slot - 3.5, 2)
    fx0, fx1 = ax.xr(now), ax.xr(now + 4)
    xsb = ax.xc(now) - bw / 2
    L, R = g.lager[now - 1], g.rest[now - 1]
    arrs = g.arrivals(now, typed if show_typed else None)
    # transportbåndet: tynn strek med små piler mot venstre
    d.line(xsb + bw, yb, fx1, yb, HAIR2, 1)
    for k in range(now + 1, now + 5):
        arrow_head(d, ax.xl(k) + 1.5, yb, "left", 3.2, INK3, 1)
    for week, qty in arrs:
        xx = ax.xc(week) - bw / 2
        if qty is None:
            d.rect(xx, yb - 16, bw, 16, "none", INK, 1.1, extra='stroke-dasharray="3 3"')
            continue
        is_t = (week == mark_week) if mark_week else (week == now + 4)
        d.rect(xx, yb - qty * u, bw, qty * u, PAPER, INK if is_t else BLUE, 1.6 if is_t else 1.2)
        if numbers:
            d.t(ax.xc(week), yb - qty * u - 4, qty, ls, 700 if is_t else 400, INK, "middle")
    # beholdningen ved nå, på sann skala
    if L > 0:
        d.rect(xsb, yb - L * u, bw, L * u, BLUEF, BLUE, 1.2)
        if labels:
            d.t(xsb - 5, yb - 5, f"Lager {L}", ls, 600, INK, "end")
    if R > 0:
        d.rect(xsb, yb, bw, R * u, REDF, RED, 1.2)
        if labels:
            d.t(xsb - 5, yb + ls + 1, f"Restordre {R}", ls, 600, INK, "end")
    if L == 0 and R == 0:
        d.line(xsb, yb, xsb + bw, yb, INK, 2.5)
        if labels:
            d.t(xsb - 5, yb - 5, "Lager 0", ls, 600, INK, "end")
    # varer ut og ordre inn, til venstre for nå
    if left and x_left is not None:
        xe = xsb - 3
        d.line(x_left + 1, yb, xe, yb, INK, 1.4)
        arrow_head(d, x_left, yb, "left", 6, INK, 1.4)
        slab = f"Sendt {g.sendt(now)} til {DOWNSTREAM[g.role]}"
        need = text_w(slab, ls) + (text_w(f"Lager {L}", ls) if R == 0 else 0) + 18
        below = R == 0 and need > (xsb - x_left)
        d.t(x_left, (yb + ls + 1) if below else (yb - 6), slab, ls, 600, INK)
        yi = yb + (34 if below else 30)
        d.line(x_left, yi, xe - 1, yi, INK2, 1, dash="3 3")
        arrow_head(d, xe, yi, "right", 6, INK2, 1.2)
        d.t(x_left, yi - 6, f"Ordre inn {g.inn(now)}", ls, 400, INK2)
    if header:
        pv = g.paavei(now)
        s = f"På vei {pv}" + (f" + {typed}" if (typed is not None and show_typed) else "") + f", fra {UPSTREAM[g.role]}"
        over = g.overdue(now)
        if over and overdue_note:
            s = f"På vei {pv}, {over} uten dato, fra {UPSTREAM[g.role]}"
        d.t(fx1, top + ls, s, ls, 600, INK, "end")
        if x_left is not None and head_left is not False:
            d.t(x_left, top + ls, head_left or "Ditt ledd", ls, 600, INK)
    if posisjon:
        pos = g.posisjon(now)
        yr = yb + max(R * u, ls + 6) + 10
        d.line(xsb, yr, fx1, yr, INK2, 1)
        d.line(xsb, yr - 4, xsb, yr + 1, INK2, 1)
        d.line(fx1, yr - 4, fx1, yr + 1, INK2, 1)
        txt = f"Posisjon {L} − {R} + {g.paavei(now)} = {pos}" + (f", med {typed}: {pos + typed}" if typed is not None else "")
        d.t(fx1, yr + ls + 3, txt, ls, 600, INK, "end", 'stroke="#FFFFFF" stroke-width="4" paint-order="stroke"')
    return {"yb": yb, "bottom": top + tot, "bw": bw, "xsb": xsb, "fx0": fx0, "fx1": fx1}


def cost_bars(d, ax, y0, h, g, wfrom, wto, scale=40, x1=None, label_now=None, ls=13):
    """Kostnad per uke: lager × 0,50 i blått, restordre × 1,00 i rødt, på felles kroneskala."""
    u = h / scale
    bw = max(ax.slot - 2.5, 2)
    base = y0 + h
    for w in range(wfrom, wto + 1):
        lk, rk = g.lagerkost(w), g.restkost(w)
        x = ax.xc(w) - bw / 2
        if lk:
            d.rect(x, base - lk * u, bw, lk * u, BLUE)
        if rk:
            d.rect(x, base - rk * u - (lk * u if lk else 0), bw, rk * u, RED)
    d.line(ax.x0, base, x1 or ax.x1, base, HAIR2, 1)
    if label_now:
        v = g.uke_kost(label_now)
        d.t(ax.xc(label_now), base - v * u - 4, kr(v), ls, 700, INK, "middle")


def syn(d, g, x, y, w, now, typed=None, wmin=None, wmax=None, left=34, u=1.0, ls=13, hord=40, omax=25, hflow=0, fmax=32,
        hnet=130, lo=-40, hi=30, ticks=(-40, -20, 0, 20), hcost=34, cmax=40, gap=18, titles=True, proj=False, posisjon=False,
        actual=False, x_left=None, xstep=2, connector=True, maxup=30, maxdn=40, netlabel=True, show_typed=True, axislabel=True,
        cost_title="Kostnad per uke, kr", band=True, overdue_note=True, head_left=None, cost_label=True):
    """Konseptets grafgrammatikk: kjedebånd, din ordre, (inn og ut), netto lager og kostnad, på én tidsakse."""
    wmin = wmin if wmin is not None else max(1, now - 11)
    wmax = wmax if wmax is not None else now + 4
    ax = Axis(x + left, w - left, wmin, wmax)
    fx0, fx1 = ax.xr(now), ax.xr(now + 4)
    th = ls + 7 if titles else 0
    yy = y
    out = {"ax": ax, "fx0": fx0, "fx1": fx1}
    if band:
        _, bh = band_height(u, ls, maxup, maxdn, True)
        out["yband"] = yy
        yy += bh + 6
    if hord:
        out["yord"] = yord = yy + th
        yy = yord + hord + gap
    else:
        out["yord"] = yord = yy
    if hflow:
        out["yflow"] = yflow = yy + th
        yy = yflow + hflow + gap
    out["ynet"] = ynet = yy + th
    yy = ynet + hnet + gap
    if hcost:
        out["ycost"] = ycost = yy + th
        yy = ycost + hcost
    else:
        yy -= gap
    ybot = yy
    out["ybot"] = ybot
    top_tint = (out["yband"] + ls + 8) if band else yord - 2
    d.rect(fx0, top_tint, fx1 - fx0, ybot - top_tint + 2, TINT)
    # bånd
    if band:
        b = chain_band(d, g, ax, out["yband"], now, typed, u, ls, x_left if x_left is not None else x, True, True, posisjon,
                       maxup, maxdn, show_typed=show_typed, overdue_note=overdue_note, head_left=head_left)
        out["b"] = b
    # ordre
    uo = hord / omax
    if not hord:
        typed_draw = False
    else:
        typed_draw = True
    if typed_draw:
        order_bars(d, ax, yord, hord, g.order, wmin, now - 1, omax, x1=fx1)
    bwo = max(ax.slot - 2.5, 2)
    if not typed_draw:
        pass
    elif typed is None:
        d.rect(ax.xc(now) - bwo / 2, yord + hord - 16, bwo, 16, "none", INK, 1.2, extra='stroke-dasharray="3 3"')
    else:
        d.rect(ax.xc(now) - bwo / 2, yord + hord - typed * uo, bwo, typed * uo, INK)
        d.t(ax.xc(now), yord + hord - typed * uo - 4, typed, ls, 700, INK, "middle")
        if connector and band and show_typed:
            x1_, y1_ = ax.xc(now) + bwo / 2, yord + hord - typed * uo + 2
            x2_, y2_ = ax.xc(now + 4), out["b"]["yb"] + 1
            d.path(f"M{x1_:.1f} {y1_:.1f} L{x2_:.1f} {y2_:.1f}", stroke=INK, sw=1)
            d.t(fx1 - 3, yord + hord - 4, "om lag 4 uker", ls - 1, 400, INK2, "end")
    # inn og ut
    if hflow:
        flow_bars(d, ax, yflow, hflow, g, wmin, now, fmax, sendt=False, x1=fx1)
    # netto lager
    Y = grid(d, ax, ynet, hnet, lo, hi, ticks, ls, x1=fx1)
    net_area(d, ax, ynet, hnet, g.net, wmin, now, lo, hi)
    if proj and typed is not None:
        pts = g.projection(now, typed)
        over = g.overdue(now)
        if over > 0:
            topp = [(a, min(v + over, hi)) for a, v in pts]
            dd = "M" + " L".join(f"{ax.xc(a):.1f} {Y(v):.1f}" for a, v in topp) + " L" + " L".join(
                f"{ax.xc(a):.1f} {Y(v):.1f}" for a, v in reversed(pts)) + " Z"
            d.path(dd, GREY, extra='fill-opacity="0.16"')
        d.path("M" + " L".join(f"{ax.xc(a):.1f} {Y(v):.1f}" for a, v in pts), stroke=GREY, sw=2, dash="6 4")
        d.circle(ax.xc(now + 4), Y(pts[-1][1]), 3.5, PAPER, GREY, 2)
        out["proj"] = pts
    if actual and now + 4 <= g.n:
        pts = [(k, g.net(k)) for k in range(now, now + 5)]
        d.path("M" + " L".join(f"{ax.xc(a):.1f} {Y(v):.1f}" for a, v in pts), stroke=INK, sw=1)
    d.circle(ax.xc(now), Y(g.net(now)), 4, BLUE if g.net(now) >= 0 else RED, PAPER, 2)
    if netlabel:
        lab = f"Lager {g.lager[now - 1]}" if g.net(now) >= 0 else f"Restordre {g.rest[now - 1]}"
        yl = Y(g.net(now)) + (-8 if g.net(now) >= 0 else ls + 6)
        if yl > ynet + hnet:
            yl = Y(g.net(now)) - 8
        d.t(fx0 + 6, yl, lab, ls, 600, INK)
    out["Y"] = Y
    # kostnad
    if hcost:
        cost_bars(d, ax, ycost, hcost, g, wmin, now, cmax, x1=fx1, label_now=now if cost_label else None, ls=ls)
    # nå-streken og aksen
    ytop = (out["yband"] + ls + 8) if band else yord - th
    d.line(fx0, ytop, fx0, ybot + 4, INK, 1.4)
    if axislabel:
        wks = [k for k in range(wmin, wmax + 1) if (k - now) % xstep == 0]
        xaxis(d, ax, ybot + ls + 4, wks, now, ls)
    if titles:
        if hord:
            d.t(x, yord - 7, "Din ordre", ls, 600, INK)
        if hflow:
            d.rect(x, yflow - 7 - ls + 2, 10, 10, BASE)
            s1 = f"Levering {g.levering(now)}"
            d.t(x + 14, yflow - 7, s1, ls, 600, INK)
            xx2 = x + 14 + text_w(s1, ls) + 14
            d.rect(xx2, yflow - 7 - ls + 2, 10, 10, RED)
            d.t(xx2 + 14, yflow - 7, f"Ordre inn {g.inn(now)}, rødt er det lageret falt", ls, 600, INK)
        d.t(x, ynet - 7, "Lager over null, restordre under", ls, 600, INK)
        if hcost:
            d.t(x, ycost - 7, cost_title, ls, 600, INK)
    out["axisbot"] = ybot + ls + 6
    return out


# ---------- Hele kjeden: fire ledd, oppstrøms til høyre ----------
def chain_full(d, seats, x, y, w, week, u=1.0, ls=13, maxup=40, maxdn=60, demand=None, cost=True, names=None, you=None,
               node_w=34, kunde_w=86, show_pipe_numbers=True, title_size=None, end_label="Produksjon"):
    """Fire ledd og kundene i én flyt i uke `week`. Hver beholdning er en boks på sann skala, og mellom leddene
    står det som er på vei de neste fire ukene. Varene går mot venstre, ordrene mot høyre."""
    title_size = title_size or ls
    seg = (w - kunde_w) / 4
    yb = y + title_size + ls + 14 + maxup * u
    pos = {}
    d.t(x, y + title_size, "Kundene", title_size, 600, INK)
    if demand is not None:
        d.t(x, yb - 6, f"Kjøpte {demand[week - 1]}", ls, 400, INK2)
    d.line(x + 1, yb, x + kunde_w - 6, yb, INK, 1.4)
    arrow_head(d, x, yb, "left", 6, INK, 1.4)
    for i, r in enumerate(ROLES_UP):
        S = seats[r]
        nx = x + kunde_w + i * seg
        pos[r] = nx
        L, R = S.lager[week - 1], S.rest[week - 1]
        d.t(nx, y + title_size, r, title_size, 700 if r == you else 600, INK)
        if names is not False:
            d.t(nx, y + title_size + ls + 4, (names or NAVN)[r] + (", du" if r == you else ""), ls, 400, INK2)
        if L > 0:
            d.rect(nx, yb - L * u, node_w, L * u, BLUEF, BLUE, 1.2)
            d.t(nx + node_w / 2, yb - L * u - 4, L, ls, 600, INK, "middle")
        if R > 0:
            d.rect(nx, yb, node_w, R * u, REDF, RED, 1.2)
            d.t(nx + node_w / 2, yb + R * u + ls + 2, f"−{R}", ls, 600, INK, "middle")
        if L == 0 and R == 0:
            d.line(nx, yb, nx + node_w, yb, INK, 2.5)
            d.t(nx + node_w / 2, yb - 5, "0", ls, 600, INK, "middle")
        px0 = nx + node_w + 8
        px1 = nx + seg - 10
        sl = (px1 - px0) / 4
        d.line(nx + node_w, yb, nx + seg, yb, HAIR2, 1)
        arr = S.arrivals(week, S.order(week))
        for j, (wk, q) in enumerate(arr):
            bx = px0 + j * sl + 1.5
            if q:
                d.rect(bx, yb - q * u, sl - 3, q * u, PAPER, BLUE, 1)
                if show_pipe_numbers:
                    d.t(bx + (sl - 3) / 2, yb - q * u - 3, q, ls - 2, 400, INK2, "middle")
            arrow_head(d, bx - 1.5, yb, "left", 3, INK3, 1)
        over = S.overdue(week)
        if over:
            d.t(px1, yb + ls + 2, f"+{over} uten dato", ls - 1, 400, INK2, "end")
        if cost:
            d.t(nx, yb + maxdn * u + ls + 22, f"{nf(S.kostsum(week))} kr", ls, 600 if r == you else 400, INK)
    if end_label:
        d.t(x + w, y + title_size, end_label, ls, 400, INK2, "end")
    if cost:
        d.t(x, yb + maxdn * u + ls + 22, "Kostnad hittil", ls, 400, INK2)
    return {"yb": yb, "bottom": yb + maxdn * u + ls + 28, "pos": pos, "seg": seg}


def cum_cost_area(d, ax, y0, h, series_l, series_r, wfrom, wto, scale, refs=()):
    """Akkumulert kostnad: lagerkost nederst i blått, restordrekost over i rødt. refs = [(punkter, tekst)] som stiplede linjer."""
    Yc = yscale(y0, h, 0, scale)
    cl, cr = [], []
    a = b = 0.0
    for k in range(wfrom, wto + 1):
        a += series_l(k)
        b += series_r(k)
        cl.append((ax.xc(k), a))
        cr.append((ax.xc(k), a + b))
    base = Yc(0)
    pl = f"M{cl[0][0]:.1f} {base:.1f} L" + " L".join(f"{xx:.1f} {Yc(v):.1f}" for xx, v in cl) + f" L{cl[-1][0]:.1f} {base:.1f} Z"
    pr = "M" + " L".join(f"{xx:.1f} {Yc(v):.1f}" for xx, v in cr) + " L" + " L".join(f"{xx:.1f} {Yc(v):.1f}" for xx, v in reversed(cl)) + " Z"
    d.path(pr, REDF)
    d.path(pl, BLUEF)
    d.path("M" + " L".join(f"{xx:.1f} {Yc(v):.1f}" for xx, v in cr), stroke=INK, sw=1.8)
    d.path("M" + " L".join(f"{xx:.1f} {Yc(v):.1f}" for xx, v in cl), stroke=BLUE, sw=1)
    for pts, _txt in refs:
        d.path("M" + " L".join(f"{ax.xc(k):.1f} {Yc(v):.1f}" for k, v in pts), stroke=GREY, sw=1.6, dash="5 4")
    return Yc, a, b
