"""Runde 3, konsept 07 Lag for lag: kjedebånd, lagvelger, matrise, kostnad og lagtrappa.
Bygger på e07lib (Meteogrammets byggeklosser fra runde 2). Alle tall fra ../_shared/fixture.json."""
from e07lib import *

LK, RK = 0.50, 1.00  # lagerkost og restordrekost per enhet per uke

# Matrisetrinn, validert med dataviz validate_palette.js --ordinal (alle PASS),
# og celletall med kontrast >= 4,5:1 (marine på lyse trinn, hvit på mørke).
NET_POS = [(1, "#9ABBD9", INK), (10, "#6E9CC6", INK), (20, "#2B6CA3", PAPER)]
NET_NEG = [(1, "#E2A29A", INK), (10, "#CF7B71", INK), (20, "#B5423A", PAPER)]
FLOW = [(5, "#A6B8CB", INK), (10, "#7F97B0", INK), (15, "#4F6A87", PAPER), (25, "#0F2A47", PAPER)]


def cell_style(v, kind):
    if v is None:
        return PAPER, INK
    if kind == "net":
        steps, a = (NET_POS if v > 0 else NET_NEG), abs(v)
    elif kind == "flow":
        steps, a = FLOW, v
    else:
        return PAPER, INK
    fill, txt = PAPER, INK
    for th, f, t in steps:
        if a >= th:
            fill, txt = f, t
    return fill, txt


def _lk(self, w):
    return self.lager[w - 1] * LK


def _rk(self, w):
    return self.rest[w - 1] * RK


def _ukekost(self, w):
    return self.lk(w) + self.rk(w)


def _akk(self, w, kind="sum"):
    if kind == "lager":
        return sum(self.lk(k) for k in range(1, w + 1))
    if kind == "rest":
        return sum(self.rk(k) for k in range(1, w + 1))
    return sum(self.ukekost(k) for k in range(1, w + 1))


Seat.lk, Seat.rk, Seat.ukekost, Seat.akk = _lk, _rk, _ukekost, _akk


def check_seat(S, label):
    """Bygget stopper hvis materialbalansen eller kostnaden ikke stemmer med loggen."""
    for w in range(1, S.n + 1):
        assert abs(S.akk(w) - S.kostsum(w)) < 1e-6, (label, "kost", w)
        assert not (S.lager[w - 1] > 0 and S.rest[w - 1] > 0), (label, "lager og restordre samtidig", w)
        if w >= 2:
            assert S.net(w) == S.net(w - 1) + S.levering(w) - S.inn(w), (label, "balanse", w)


# ---------- Små tegnehjelpere ----------
def arrow_head(d, x, y, direction="left", size=6, fill=INK):
    s = size
    if direction == "left":
        dd = f"M{x:.1f} {y:.1f} L{x + s:.1f} {y - s * 0.6:.1f} L{x + s:.1f} {y + s * 0.6:.1f} Z"
    else:
        dd = f"M{x:.1f} {y:.1f} L{x - s:.1f} {y - s * 0.6:.1f} L{x - s:.1f} {y + s * 0.6:.1f} Z"
    d.path(dd, fill)


def link(d, x, y, label, size=14, w=600, a="start"):
    d.t(x, y, label, size, w, BLUE, a, 'text-decoration="underline"')


# ---------- Lagvelgeren ----------
def tabs(d, x, y, w, labels, active, locked=(), h=34, size=14):
    """Segmentert lagvelger. Låste lag har stiplet kant og dempet tekst, aldri farge alene."""
    n = len(labels)
    sw = w / n
    for i, lab in enumerate(labels):
        xx = x + i * sw
        if lab in locked:
            d.rect(xx + 2, y, sw - 4, h, PAPER, HAIR2, 1, 5, 'stroke-dasharray="3 3"')
            d.t(xx + sw / 2, y + h / 2 + size * 0.34, lab, size, 400, INK3, "middle")
        elif lab == active:
            d.rect(xx + 2, y, sw - 4, h, INK, None, 1, 5)
            d.t(xx + sw / 2, y + h / 2 + size * 0.34, lab, size, 600, PAPER, "middle")
        else:
            d.rect(xx + 2, y, sw - 4, h, PAPER, HAIR2, 1, 5)
            d.t(xx + sw / 2, y + h / 2 + size * 0.34, lab, size, 600, INK, "middle")
    return y + h


# ---------- Kjedebåndet: setets eget ledd ----------
def seat_band(d, g, wk, x=20, y=100, w=350, typed=None, u=1.6, posisjon=False, ls=13, vs=16, compact=False, fixed=None):
    """Ett ledd som flyt: på vei (fire plasser) -> levering -> beholdning -> sendt.
    Ordrene går motsatt vei under. Alt på sann skala (u px per enhet).
    Verdiene står i en rad øverst med hjelpelinjer ned til tegningen. Returnerer nederste y."""
    slot = w * 0.115
    px0 = x
    pw = slot * 4
    ax0 = px0 + pw + 4
    ax1 = ax0 + w * 0.165
    tx0 = ax1 + 6
    tw = w * 0.14
    tx1 = tx0 + tw
    sx1 = x + w
    arrs = g.arrivals(wk, typed)
    over = g.overdue(wk)
    pv = g.paavei(wk)
    lev = g.levering(wk)
    net = g.net(wk)
    lag = g.lager[wk - 1]
    rest = g.rest[wk - 1]
    top = max(max((q or 0) for _, q in arrs), lag)
    if fixed:
        top = max(top, fixed[0])
    base = y + ls + vs + 22 + top * u + 6
    cols = [
        (px0 + pw / 2, "På vei", f"{pv} + {typed}" if typed is not None else f"{pv}"),
        ((ax0 + ax1) / 2, "Levering", f"{lev}"),
        ((tx0 + tx1) / 2, "Restordre" if net < 0 else "Lager", f"{rest}" if net < 0 else f"{lag}"),
        ((tx1 + sx1) / 2 + 3, "Sendt", f"{g.sendt(wk)}"),
    ]
    for cx, lab, val in cols:
        d.t(cx, y + ls, lab, ls, 400, INK2, "middle")
        d.t(cx, y + ls + vs + 3, val, vs, 700, INK, "middle")
    top_lead = y + ls + vs + 9
    bw = slot - 10
    for j, (week, qty) in enumerate(reversed(arrs)):
        cx = px0 + slot * j + slot / 2
        is_typed = week == wk + 4
        if qty is None:
            d.rect(cx - bw / 2, base - 14, bw, 14, "none", INK, 1.2, extra='stroke-dasharray="3 3"')
        else:
            hh = max(qty * u, 1.5)
            d.rect(cx - bw / 2, base - hh, bw, hh, PAPER if is_typed else BLUEF, INK if is_typed else BLUE, 1.6 if is_typed else 1.1)
            if not compact:
                d.t(cx, base - hh - 4, qty, ls, 700 if is_typed else 400, INK, "middle")
        d.t(cx, base + ls + 3, week, ls, 700 if is_typed else 400, INK if is_typed else INK3, "middle")
    d.line(px0, base, px0 + pw, base, HAIR2, 1)
    d.line(px0 + pw / 2, top_lead, px0 + pw / 2, base - top * u - ls - 6, HAIR2, 1)
    # levering
    d.line(ax0 + 2, base - 6, ax1 - 6, base - 6, INK, 1.4)
    arrow_head(d, ax1, base - 6, "right", 6)
    d.line((ax0 + ax1) / 2, top_lead, (ax0 + ax1) / 2, base - 12, HAIR2, 1)
    # beholdningen: blått over null, rødt under
    d.line(tx0 - 3, base, tx1 + 3, base, INK, 1.2)
    if lag > 0:
        d.rect(tx0, base - lag * u, tw, lag * u, BLUEF, BLUE, 1.2)
    if rest > 0:
        d.rect(tx0, base, tw, rest * u, REDF, RED, 1.2)
    d.line((tx0 + tx1) / 2, top_lead, (tx0 + tx1) / 2, base - max(lag * u, 0) - 4, HAIR2, 1)
    # sendt
    d.line(tx1 + 6, base - 6, sx1 - 6, base - 6, INK, 1.4)
    arrow_head(d, sx1, base - 6, "right", 6)
    d.line((tx1 + sx1) / 2 + 3, top_lead, (tx1 + sx1) / 2 + 3, base - 12, HAIR2, 1)
    ybelow = base + ls + 3
    if over > 0:
        d.t(px0, ybelow + ls + 6, f"+ {over} forsinket, uten dato", ls, 400, INK2)
        ybelow += ls + 6
    # ordrene, motsatt vei
    yo = max(base + max(rest, fixed[1] if fixed else 0) * u, ybelow) + 16
    d.line(sx1, yo, tx1 + 10, yo, INK, 1.2)
    arrow_head(d, tx1 + 4, yo, "left", 6)
    d.line(tx0 - 6, yo, px0 + 6, yo, INK, 1.2)
    arrow_head(d, px0, yo, "left", 6)
    d.t(sx1, yo + ls + 6, f"Ordre inn {g.inn(wk)}", ls, 600, INK, "end")
    d.t(sx1, yo + 2 * ls + 9, "fra Detaljist", ls, 400, INK2, "end")
    d.t(px0, yo + ls + 6, f"Din ordre {typed}" if typed is not None else "Din ordre", ls, 600, INK)
    d.t(px0, yo + 2 * ls + 9, "til Distributør", ls, 400, INK2)
    yb = yo + 2 * ls + 12
    if posisjon:
        pos = g.posisjon(wk)
        yb += 12
        d.line(px0, yb, tx1, yb, INK, 1)
        d.line(px0, yb - 6, px0, yb, INK, 1)
        d.line(tx1, yb - 6, tx1, yb, INK, 1)
        s = f"Posisjon {lag} − {rest} + {pv} = {pos}"
        if typed is not None:
            s += f". Med {typed}: {pos + typed}"
        d.t(px0, yb + ls + 6, s, ls, 600, INK)
        yb += ls + 10
    return yb


# ---------- Hele kjeden ----------
CHAIN = ["Fabrikk", "Distributør", "Grossist", "Detaljist"]


def chain4(d, seats, demand, wk, x, y, w, u=1.2, cost=None, names=True, ls=13, you="Grossist", pvscale=0.5):
    """Fire ledd pluss kunde i én flyt, med på vei mellom leddene og ordre under. Sann skala.
    cost: None, eller funksjon Rolle -> kroner som skrives under hver node."""
    gapw = w / 4.75
    nodew = min(gapw * 0.34, 54)
    xs = [x + gapw * (i + 0.85) for i in range(4)]
    kx = x + w - 24
    maxlag = max(seats[r].lager[wk - 1] for r in CHAIN)
    maxpv = max(seats[r].paavei(wk) for r in CHAIN)
    head = 3 * ls + 22
    base = y + head + max(maxlag * u, maxpv * u * pvscale + ls + 4) + 8
    for i, r in enumerate(CHAIN):
        cx = xs[i]
        S = seats[r]
        d.t(cx, y + ls + 1, r, ls + 1, 700 if r == you else 600, INK, "middle")
        if names:
            d.t(cx, y + 2 * ls + 5, NAVN[r] + (", du" if r == you else ""), ls, 400, INK2, "middle")
        lag, rest = S.lager[wk - 1], S.rest[wk - 1]
        lab = f"Lager {lag}" if rest == 0 else f"Restordre {rest}"
        d.t(cx, y + 3 * ls + 10, lab, ls, 600, INK, "middle")
        d.line(cx - nodew / 2 - 3, base, cx + nodew / 2 + 3, base, INK, 1.2)
        if lag:
            d.rect(cx - nodew / 2, base - lag * u, nodew, lag * u, BLUEF, BLUE, 1.1)
        if rest:
            d.rect(cx - nodew / 2, base, nodew, rest * u, REDF, RED, 1.1)
    maxrest = max(seats[r].rest[wk - 1] for r in CHAIN)
    ycost = base + maxrest * u + ls + 8
    if cost:
        for i, r in enumerate(CHAIN):
            d.t(xs[i], ycost, f"{nf(cost(r))} kr", ls, 600, INK, "middle")
    # på vei til hvert ledd, som stolpe på sann skala (halv skala, merket)
    for i, r in enumerate(CHAIN):
        S = seats[r]
        pv = S.paavei(wk)
        mx = (xs[i - 1] + xs[i]) / 2 if i else xs[0] - gapw * 0.55
        bw = 12
        hh = pv * u * pvscale
        d.rect(mx - bw / 2, base - hh, bw, hh, PAPER, BLUE, 1)
        d.t(mx, base - hh - 5, pv, ls, 600, INK, "middle")
        d.line(mx + bw / 2 + 3, base - 6, xs[i] - nodew / 2 - 8, base - 6, INK, 1)
        arrow_head(d, xs[i] - nodew / 2 - 4, base - 6, "right", 5)
    d.t(xs[0] - gapw * 0.55, base + ls + 4, "i produksjon", ls - 1, 400, INK2, "middle")
    # kunden
    d.line(xs[-1] + nodew / 2 + 6, base - 6, kx - 22, base - 6, INK, 1)
    arrow_head(d, kx - 18, base - 6, "right", 5)
    d.t(kx, y + ls + 1, "Kunde", ls + 1, 600, INK, "middle")
    d.t(kx, base - 2, demand[wk - 1], ls + 3, 700, INK, "middle")
    d.t(kx, base + ls + 4, "kjøpte", ls, 400, INK2, "middle")
    # ordrene, motsatt vei
    yo = (ycost + 14) if cost else (base + maxrest * u + 16)
    for i, r in enumerate(CHAIN):
        S = seats[r]
        right = xs[i + 1] - nodew / 2 if i < 3 else kx - 18
        d.line(right - 4, yo, xs[i] + nodew / 2 + 10, yo, INK2, 1)
        arrow_head(d, xs[i] + nodew / 2 + 4, yo, "left", 5, INK2)
        d.t((right + xs[i] + nodew / 2) / 2, yo + ls + 4, f"ordre {S.inn(wk)}", ls, 400, INK, "middle")
    return yo + ls + 10, xs


# ---------- Matrisen ----------
def matrix(d, ax, y, rows, weeks, rh=22, size=13, lx=None, lsize=13, gap=1.5, lw=None):
    """rows: (etikett, fn(uke) -> tall | (tall, art) | None, art). art: net, flow, plain, cost, known, typed.
    Cellene ligger på samme tidsakse som grafen (ax)."""
    for i, (lab, fn, kind) in enumerate(rows):
        yy = y + i * rh
        if lx is not None:
            d.t(lx, yy + rh / 2 + lsize * 0.34, lab, lsize, 400, INK)
        for wv in weeks:
            v = fn(wv)
            if v is None:
                continue
            k = kind
            if isinstance(v, tuple):
                v, k = v
            x0 = ax.xl(wv) + gap / 2
            cw = ax.slot - gap
            if k == "known":
                d.rect(x0 + 1, yy + gap / 2 + 1, cw - 2, rh - gap - 2, PAPER, BLUE, 1)
                txt = INK
            elif k == "typed":
                d.rect(x0 + 1, yy + gap / 2 + 1, cw - 2, rh - gap - 2, PAPER, INK, 1.6)
                txt = INK
            else:
                fill, txt = cell_style(v, k)
                d.rect(x0, yy + gap / 2, cw, rh - gap, fill)
            if k == "cost":
                s = (nf(v, 1) if v % 1 else str(int(v))) if v else "0"
            else:
                s = sg(v)
            d.t(ax.xc(wv), yy + rh / 2 + size * 0.34, s, size, 700 if k == "typed" else 400, txt, "middle")
        d.line(lx if lx is not None else ax.x0, yy + rh, ax.x1, yy + rh, HAIR, 1)
    return y + len(rows) * rh


# ---------- Kostnad ----------
def cost_week_bars(d, ax, y0, h, g, wfrom, wto, scale=40, x1=None):
    """Kostnad per uke: blå del er lagerkost, rød del er restordrekost. Sann null."""
    u = h / scale
    bw = max(ax.slot - 3, 2)
    base = y0 + h
    for wv in range(wfrom, wto + 1):
        lk, rk = g.lk(wv), g.rk(wv)
        yy = base
        if lk:
            d.rect(ax.xc(wv) - bw / 2, yy - lk * u, bw, lk * u, BLUE)
            yy -= lk * u
        if rk:
            d.rect(ax.xc(wv) - bw / 2, yy - rk * u, bw, rk * u, RED)
    d.line(ax.x0, base, x1 or ax.x1, base, HAIR2, 1)
    return lambda v: base - v * u


def cost_cum_area(d, ax, y0, h, g, wfrom, wto, scale, x1=None, lw=1.8, ref=None, refs=()):
    """Akkumulert kostnad, stablet: lagerkost (blått) nederst, restordrekost (rødt) over. Toppen er Totalkostnad."""
    Y = yscale(y0, h, 0, scale)
    pl = [(ax.xc(k), Y(g.akk(k, "lager"))) for k in range(wfrom, wto + 1)]
    pt = [(ax.xc(k), Y(g.akk(k))) for k in range(wfrom, wto + 1)]
    b = Y(0)
    d.path("M" + " L".join(f"{a:.1f} {c:.1f}" for a, c in pl) + f" L{pl[-1][0]:.1f} {b:.1f} L{pl[0][0]:.1f} {b:.1f} Z", BLUEF)
    d.path("M" + " L".join(f"{a:.1f} {c:.1f}" for a, c in pt) + " L" + " L".join(f"{a:.1f} {c:.1f}" for a, c in reversed(pl)) + " Z", REDF)
    d.path("M" + " L".join(f"{a:.1f} {c:.1f}" for a, c in pt), stroke=INK, sw=lw)
    d.line(ax.x0, b, x1 or ax.x1, b, HAIR2, 1)
    for R, dash in ((ref, "6 4"),) + tuple(refs):
        if R is None:
            continue
        pr = [(ax.xc(k), Y(R.akk(k))) for k in range(wfrom, wto + 1)]
        d.path("M" + " L".join(f"{a:.1f} {c:.1f}" for a, c in pr), stroke=GREY, sw=1.6, dash=dash)
    return Y


# ---------- Lagtrappa: Hjelpegrad som tegnet system ----------
LAYERS = [
    ("Kjedebånd og ordrefelt", "Ditt ledd: på vei, levering, lager eller restordre, sendt, ordre inn og ut"),
    ("Graf", "Meteogrammet: netto lager, inn og ut, din ordre og kjente ankomster"),
    ("Tall", "Samme uker som tabell: ordre inn, levering, sendt, lager, på vei, din ordre"),
    ("Kostnad", "Din kostnad per uke og samlet, delt i lager og restordre"),
    ("Posisjon", "Lager − Restordre + På vei regnet ut i kjedebåndet"),
    ("Hele kjeden", "Fire ledd og kunden, med kostnad per Rolle og for kjeden"),
    ("Simulert referanse", "Samme kjede regnet med en rolig regel. Simulert, ikke fasit"),
    ("Projeksjon", "Stiplet linje for netto lager fire uker fram, ikke garantert"),
]
STAGES = ["Veiledede uker 1–4", "Klassespill", "Etter Debriefen", "Replay"]
# Første trinn der laget er åpent (indeks i STAGES). Veiledede uker åpner ett lag per uke.
OPEN_AT = {"Kjedebånd og ordrefelt": 0, "Graf": 0, "Tall": 0, "Kostnad": 0, "Posisjon": 2, "Hele kjeden": 2,
           "Simulert referanse": 2, "Projeksjon": 3}
GUIDED_WEEK = {"Kjedebånd og ordrefelt": 1, "Graf": 2, "Tall": 3, "Kostnad": 4}


def layer_ladder(d, x, y, w, rh=34, ls=14, desc=True, label_w=None, highlight=None, compact=False):
    """Lagtrappa: rader er lag, kolonner er trinn. Fylt celle = åpent. Tekst i hver celle, så farge aldri bærer alene."""
    lw = label_w or (w * 0.42 if desc else w * 0.3)
    cw = (w - lw) / len(STAGES)
    yh = y
    for j, st in enumerate(STAGES):
        cx = x + lw + j * cw + cw / 2
        for k, ln in enumerate(wrap(st, cw - 8, ls - 1)):
            d.t(cx, yh + k * (ls + 2), ln, ls - 1, 600, INK, "middle")
    y0 = yh + 2 * (ls + 2) + 6
    d.line(x, y0 - 4, x + w, y0 - 4, HAIR2, 1)
    for i, (name, ds) in enumerate(LAYERS):
        yy = y0 + i * rh
        d.t(x, yy + (rh * 0.42 if desc else rh / 2 + ls * 0.34), name, ls, 600, INK)
        if desc:
            d.t(x, yy + rh * 0.42 + ls + 2, ds if text_w(ds, ls - 2) < lw - 8 else wrap(ds, lw - 8, ls - 2)[0] + " …", ls - 2, 400, INK2)
        o = OPEN_AT[name]
        for j in range(len(STAGES)):
            cx0 = x + lw + j * cw + 3
            if j >= o:
                fill = INK if (j == o and o > 0) else "#4F6A87"
                d.rect(cx0, yy + 5, cw - 6, rh - 10, fill, None, 1, 3)
                if j == 0 and name in GUIDED_WEEK:
                    s = f"fra Uke {GUIDED_WEEK[name]}"
                elif j == o and o > 0:
                    s = "åpnes"
                else:
                    s = "åpen"
                d.t(cx0 + (cw - 6) / 2, yy + rh / 2 + (ls - 2) * 0.34, s, ls - 2, 600, PAPER, "middle")
            else:
                d.rect(cx0, yy + 5, cw - 6, rh - 10, PAPER, HAIR2, 1, 3, 'stroke-dasharray="3 3"')
                d.t(cx0 + (cw - 6) / 2, yy + rh / 2 + (ls - 2) * 0.34, "låst", ls - 2, 400, INK3, "middle")
        d.line(x, yy + rh, x + w, yy + rh, HAIR, 1)
    return y0 + len(LAYERS) * rh
