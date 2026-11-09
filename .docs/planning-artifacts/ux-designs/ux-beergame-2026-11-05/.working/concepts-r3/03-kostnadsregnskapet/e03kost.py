"""Kostnadsregnskapet: tillegg til Meteogrammets grammatikk (e03lib.py).
Kostnad per uke, V-en lagt på siden, kjedebånd, kjede med fire ledd og matriser som deler tidsakse med grafen."""
from e03lib import *

LK, RK = 0.50, 1.00          # lagerkost og restordrekost per enhet per uke
B_STEPS = ["#94B7D8", "#6C9CC9", "#2B6CA3", "#1B4F7C"]   # lagerkostnad, kr per uke
R_STEPS = ["#DD9C94", "#D58178", "#B5423A", "#86302A"]   # restordrekostnad, kr per uke
M_STEPS = ["#A3B4C7", "#8197AE", "#44586F", "#0F2A47"]   # kjedekostnad per uke (lærer)
KR_CUTS = (5, 10, 20)        # samme kronegrenser for begge kostnadsarter, så P8 synes i fargen
KJ_CUTS = (20, 40, 80)       # kjedekostnad per uke, fire Roller

DRAWN = []   # alle tall som tegnes i matriser: (kilde, rolle, uke, rad, verdi). build.py sjekker dem mot loggen.


def _step(v, cuts):
    return sum(1 for c in cuts if v > c)


def cost_fill(kind, kr):
    """Celle for én kostnadsart. Returnerer (fyll, tekstfarge). 0 kr er hvit celle med dempet tall."""
    if kr <= 0:
        return PAPER, INK3
    steps = B_STEPS if kind == "lk" else R_STEPS
    i = _step(kr, KR_CUTS)
    return steps[i], (PAPER if i >= 2 else INK)


def chain_fill(kr):
    i = _step(kr, KJ_CUTS)
    return M_STEPS[i], (PAPER if i >= 2 else INK)


def wcost(net):
    return max(net, 0) * LK + max(-net, 0) * RK


Seat.lk = lambda self, w: self.lager[w - 1] * LK
Seat.rk = lambda self, w: self.rest[w - 1] * RK
Seat.wc = lambda self, w: self.lager[w - 1] * LK + self.rest[w - 1] * RK
Seat.cum_lk = lambda self, w: sum(self.lager[:w]) * LK
Seat.cum_rk = lambda self, w: sum(self.rest[:w]) * RK

# Kostnaden må stemme med loggen før noe tegnes.
for _r in ROLES:
    _s = Seat(_r)
    _acc = 0.0
    for _w in range(1, _s.n + 1):
        _acc += _s.wc(_w)
        assert abs(_acc - _s.kostsum(_w)) < 1e-9, (_r, _w)
        assert abs(_s.cum_lk(_w) + _s.cum_rk(_w) - _s.kostsum(_w)) < 1e-9
        assert abs(_s.wc(_w) - wcost(_s.net(_w))) < 1e-9
    assert abs(_s.kostsum(_s.n) - FX["spill17"]["kost_per_rolle"][_r]) < 1e-9
assert Seat().kostsum(11) == 68.0 and Seat().cum_lk(11) == 43.0 and Seat().cum_rk(11) == 25.0


def avg_cost(g, upto=None):
    """Kostnad på snittet: hva jevn drift på gjennomsnittlig netto lager ville kostet, mot det som ble betalt."""
    n = upto or g.n
    avg = sum(g.net(w) for w in range(1, n + 1)) / n
    return avg, wcost(avg) * n, g.kostsum(n)


def cost_bars(d, ax, y0, h, g, wfrom, wto, kmax=40, x1=None):
    """Kostnad per uke i kroner, sann null. Blå: lagerkostnad. Rød: restordrekostnad."""
    u = h / kmax
    bw = max(ax.slot - 2.5, 1.5)
    base = y0 + h
    for w in range(wfrom, wto + 1):
        lk, rk = g.lk(w), g.rk(w)
        x = ax.xc(w) - bw / 2
        if lk:
            d.rect(x, base - min(lk, kmax) * u, bw, min(lk, kmax) * u, BLUE)
        if rk:
            d.rect(x, base - min(rk, kmax) * u, bw, min(rk, kmax) * u, RED)
    d.line(ax.x0, base, x1 or ax.x1, base, HAIR2, 1)


def side_v(d, x0, w, Y, lo, hi, net=None, kmax=40, ls=13, trail=(), label=True, head=True, ring=None):
    """V-en lagt på siden: deler y-akse med netto lager, x er kroner per uke.
    Nedre arm går dobbelt så langt ut som øvre, fordi restordre koster dobbelt (P8).
    Den tykke vannrette streken fra null til armen er ukas kostnad."""
    s = w / kmax
    d.line(x0, Y(hi), x0, Y(lo), HAIR2, 1)
    d.path(f"M{x0:.1f} {Y(0):.1f} L{x0 + hi * LK * s:.1f} {Y(hi):.1f}", stroke=BLUE, sw=1.4)
    d.path(f"M{x0:.1f} {Y(0):.1f} L{x0 + (-lo) * RK * s:.1f} {Y(lo):.1f}", stroke=RED, sw=1.4)
    for v in trail:
        d.circle(x0 + wcost(v) * s, Y(v), 2.2, INK3)
    if head:
        d.t(x0, Y(hi) - 6, "kr per uke", ls, 400, INK2)
    if ring is not None:
        d.circle(x0 + wcost(ring) * s, Y(ring), 4, PAPER, GREY, 1.6)
    if net is not None:
        c = wcost(net)
        col = BLUE if net >= 0 else RED
        d.line(x0, Y(net), x0 + c * s, Y(net), col, 3)
        d.circle(x0 + c * s, Y(net), 4, col, PAPER, 1.5)
        if label:
            d.t(x0 - 6, Y(net) - 6, f"{nf(c)} kr", ls, 700, INK, "end")
    return s


def meteo3(d, g, x, y, w, now, typed=None, wmin=None, wmax=None, hk=60, hn=120, ho=44, gap=20, ls=13, left=30,
           sidev=56, proj=False, actual=False, titles=True, xstep=2, kmax=40, omax=25, lo=-40, hi=30,
           ticks=(-40, -20, 0, 20), arrnums=True, nowlabel="Nå", netlabel=True, axis=True, connector=True,
           overduenote=True, trail=False, t_cost="Kostnad per uke, kr", t_net="Lager over null, restordre under",
           t_ord="Din ordre, og når den kommer", cost_label=True, vlabel=True, ordlabel=True, kticks=(0, 20, 40)):
    """Meteogrammet i Kostnadsregnskapet: kostnad per uke øverst, netto lager med V-en på siden, egen ordre nederst.
    Alle felt deler én tidsakse. Høyre kant er nå + 4, aldri slutten av spillet."""
    wmin = wmin if wmin is not None else max(1, now - 11)
    wmax = wmax if wmax is not None else now + 4
    plot_w = w - left - (sidev + 22 if sidev else 0)
    ax = Axis(x + left, plot_w, wmin, wmax)
    th = ls + 8 if titles else 6
    yk = y + th
    yn = yk + (hk + gap + th if hk else 0)
    yo = yn + hn + gap + th
    ybot = yo + ho
    ytop = yk if hk else yn
    fx0, fx1_ = ax.xr(now), ax.xr(min(now + 4, wmax))
    d.rect(fx0, ytop - 2, fx1_ - fx0, ybot - ytop + 2, TINT)

    # Kostnad per uke
    if hk:
        ku = hk / kmax
        for v in kticks:
            d.line(ax.x0, yk + hk - v * ku, fx1_, yk + hk - v * ku, HAIR2 if v == 0 else HAIR, 1)
            d.t(ax.x0 - 5, yk + hk - v * ku + ls * 0.34, v, ls, 400, INK3, "end")
        cost_bars(d, ax, yk, hk, g, wmin, now, kmax, x1=fx1_)
        if cost_label:
            c = g.wc(now)
            if c < 0.55 * kmax:
                d.t(ax.xc(now), yk + hk - c * ku - 4, nf(c), ls, 700, INK, "middle")
            else:
                d.t(ax.xc(now) - ax.slot / 2 - 3, yk + hk - min(c, kmax) * ku + ls * 0.34, nf(c), ls, 700, INK, "end",
                    'stroke="#FFFFFF" stroke-width="3" paint-order="stroke"')
        if actual and now + 4 <= g.n:
            bw = max(ax.slot - 3.5, 2)
            for wk in range(now + 1, now + 5):
                c = g.wc(wk)
                d.rect(ax.xc(wk) - bw / 2, yk + hk - min(c, kmax) * ku, bw, min(c, kmax) * ku, "none", INK, 1)
        if proj and typed is not None:
            pts = g.projection(now, typed)
            bw = max(ax.slot - 3.5, 2)
            tot = 0
            for wk, v in pts[1:]:
                c = wcost(v)
                tot += c
                d.rect(ax.xc(wk) - bw / 2, yk + hk - min(c, kmax) * ku, bw, min(c, kmax) * ku, "none", GREY, 1.2, extra='stroke-dasharray="3 2"')
    # Netto lager
    Y = grid(d, ax, yn, hn, lo, hi, ticks, ls, x1=fx1_)
    net_area(d, ax, yn, hn, g.net, wmin, now, lo, hi)
    if proj and typed is not None:
        pts = g.projection(now, typed)
        d.path("M" + " L".join(f"{ax.xc(a):.1f} {Y(v):.1f}" for a, v in pts), stroke=GREY, sw=2, dash="6 4")
        d.circle(ax.xc(pts[-1][0]), Y(pts[-1][1]), 3.5, PAPER, GREY, 2)
    if actual and now + 4 <= g.n:
        d.path("M" + " L".join(f"{ax.xc(k):.1f} {Y(g.net(k)):.1f}" for k in range(now, now + 5)), stroke=INK, sw=1)
    d.circle(ax.xc(now), Y(g.net(now)), 4, BLUE if g.net(now) >= 0 else RED, PAPER, 2)
    if netlabel:
        lab = f"Lager {g.lager[now - 1]}" if g.net(now) >= 0 else f"Restordre {g.rest[now - 1]}"
        yy = Y(g.net(now)) + (ls + 6 if g.net(now) < 0 else -8)
        d.t(fx0 + 5, yy, lab, ls, 600, INK)
    if sidev:
        side_v(d, ax.x1 + 22, sidev, Y, lo, hi, g.net(now), max(-lo * RK, hi * LK), ls, trail=[g.net(k) for k in range(wmin, now)] if trail else (),
               label=vlabel, head=titles)
    # Egen ordre og kjente ankomster
    if not ho:
        yo = yn + hn
        ybot = yo
    ou = ho / omax if ho else 0
    bwo = max(ax.slot - 2.5, 1.5)
    for k in (range(wmin, now) if ho else ()):
        v = g.order(k)
        d.rect(ax.xc(k) - bwo / 2, yo + ho - min(v, omax) * ou, bwo, min(v, omax) * ou, ORD)
    if not ho:
        pass
    elif typed is None:
        d.rect(ax.xc(now) - bwo / 2, yo + ho - 14, bwo, 14, "none", INK, 1.2, extra='stroke-dasharray="3 3"')
    else:
        d.rect(ax.xc(now) - bwo / 2, yo + ho - min(typed, omax) * ou, bwo, min(typed, omax) * ou, INK)
        if ordlabel:
            d.t(ax.xc(now), yo + ho - min(typed, omax) * ou - 4, typed, ls, 700, INK, "middle")
    bw = max(ax.slot - 3.5, 1.5)
    for wk, qty in (g.arrivals(now, typed) if ho else ()):
        if wk > wmax or qty is None:
            continue
        is_t = wk == now + 4
        hh = min(qty, omax) * ou
        d.rect(ax.xc(wk) - bw / 2, yo + ho - hh, bw, hh, PAPER, INK if is_t else BLUE, 1.6 if is_t else 1.1)
        if arrnums:
            d.t(ax.xc(wk), yo + ho - hh - 4, qty, ls, 700 if is_t else 400, INK, "middle")
    if ho and connector and typed is not None and now + 4 <= wmax:
        hh = min(typed, omax) * ou
        d.path(f"M{ax.xc(now) + bwo / 2:.1f} {yo + ho - hh + 2:.1f} L{ax.xc(now + 4) - bw / 2:.1f} {yo + ho - hh + 2:.1f}", stroke=INK, sw=1, dash="2 3")
    over = g.overdue(now)
    if ho and over > 0 and overduenote:
        d.t(fx1_ + 6, yo + ho - 4, f"+ {over} forsinket", ls, 400, INK2)
    if ho:
        d.line(ax.x0, yo + ho, fx1_, yo + ho, HAIR2, 1)

    # Nå-streken og tidsaksen
    d.line(fx0, ytop - th + 4, fx0, ybot + 4, INK, 1.4)
    if nowlabel:
        d.t(fx0 + 5, ytop - 7, nowlabel, ls, 700, INK)
    if axis:
        wks = [k for k in range(wmin, wmax + 1) if (k - now) % xstep == 0]
        xaxis(d, ax, ybot + ls + 4, wks, now, ls)
    if titles:
        if hk and t_cost:
            d.t(x, yk - 7, t_cost, ls, 600, INK)
        if t_net:
            d.t(x, yn - 7, t_net, ls, 600, INK)
        if t_ord and ho:
            d.t(x, yo - 7, t_ord, ls, 600, INK)
    return {"ax": ax, "yk": yk, "yn": yn, "yo": yo, "ybot": ybot, "Y": Y, "fx0": fx0, "fx1": fx1_, "axisbot": ybot + ls + 6,
            "sx": ax.x1 + 22}


def matrix(d, ax, y, rows, weeks, label_x, rh=24, ls=13, src="", role="Grossist", head=True, now=None, dec=None):
    """Tall per uke, kolonne for kolonne på samme tidsakse som grafen over.
    rows: (etikett, funksjon(uke) -> tall eller None, art). Art: 'n' enheter, 'lk', 'rk', 'wc' uka, 'cum' akkumulert, 'kj' kjeden."""
    cw = ax.slot - 2
    yy = y
    if head:
        for k in weeks:
            bold = k == now
            d.t(ax.xc(k), yy + ls, k, ls, 700 if bold else 400, INK if bold else INK3, "middle")
        yy += ls + 8
    y_cells = yy
    for lab, fn, kind in rows:
        if lab is None:
            yy += 10
            continue
        d.t(label_x, yy + rh / 2 + ls * 0.36, lab, ls, 600 if kind in ("wc", "cum") else 400, INK)
        for k in weeks:
            v = fn(k)
            if v is None:
                continue
            DRAWN.append((src, role, k, lab, v))
            x = ax.xc(k) - cw / 2
            cy = yy + rh / 2 + ls * 0.36
            if kind in ("lk", "rk"):
                fill, tc = cost_fill(kind, v)
                if fill != PAPER:
                    d.rect(x, yy + 1, cw, rh - 2, fill)
                dd = dec if dec is not None else (0 if cw < 30 else 2)
                d.t(ax.xc(k), cy, nf(v, dd) if v else "0", ls, 400, tc, "middle")
            elif kind == "kj":
                fill, tc = chain_fill(v)
                d.rect(x, yy + 1, cw, rh - 2, fill)
                d.t(ax.xc(k), cy, nf(v, 0), ls, 400, tc, "middle")
            elif kind in ("wc", "cum"):
                dd = dec if dec is not None else (0 if cw < 30 else 2)
                if kind == "cum" and cw < 44 and dec is None:
                    dd = 0
                d.t(ax.xc(k), cy, nf(v, dd), ls, 600 if kind == "cum" else 400, INK, "middle")
            else:
                d.t(ax.xc(k), cy, sg(v) if isinstance(v, int) else v, ls, 400, INK, "middle")
        d.line(label_x, yy + rh, ax.xr(weeks[-1]), yy + rh, HAIR, 1)
        yy += rh
    if now is not None and now in weeks:
        d.rect(ax.xl(now) + 0.5, y_cells, ax.slot - 1, yy - y_cells, "none", INK, 1.2)
    return yy


def cost_split_bar(d, x, y, w, lk, rk, h=10, last=None, last_kind=None, ls=13, labels=True):
    """Totalkostnad som én stolpe delt i lagerkostnad og restordrekostnad. last: ukas bidrag, rammet inn i sin del."""
    tot = lk + rk
    wl = w * lk / tot if tot else 0
    if lk:
        d.rect(x, y, wl - (1 if rk else 0), h, BLUE)
    if rk:
        d.rect(x + wl + (1 if lk else 0), y, w - wl - (1 if lk else 0), h, RED)
    if last:
        lw = w * last / tot
        lx = x + w - lw if last_kind == "rk" else x + wl - lw
        d.rect(lx, y - 3, lw, h + 6, "none", INK, 1.4)
    if labels:
        d.t(x, y + h + ls + 6, f"Lagerkostnad {nf(lk)}", ls, 400, INK2)
        d.t(x + w, y + h + ls + 6, f"Restordrekostnad {nf(rk)}", ls, 400, INK2, "end")
    return y + h + ls + 6


def ledger(d, x, y, w, g, wk, ls=13, big=28, split=True):
    """Regnskapslinja som åpner hver flate: hva uka kostet, og hva spillet har kostet, fordelt på to arter."""
    c = g.wc(wk)
    PN = 'style="font-variant-numeric:lining-nums proportional-nums"'
    d.t(x, y, "Uka kostet", ls, 400, INK2)
    d.t(x, y + big + 2, f"{nf(c)} kr", big, 700, INK, extra=PN)
    rx = x + w * 0.42
    d.t(rx, y, "Totalkostnad så langt", ls, 400, INK2)
    d.t(rx, y + big + 2, f"{nf(g.kostsum(wk))} kr", big, 700, INK, extra=PN)
    why = f"{g.rest[wk - 1]} restordre × 1,00" if g.rest[wk - 1] else f"{g.lager[wk - 1]} på lager × 0,50"
    d.t(x, y + big + ls + 10, why, ls, 400, INK2)
    yy = y + big + ls + 10
    if split:
        yy = cost_split_bar(d, rx, y + big + 10, w - (rx - x), g.cum_lk(wk), g.cum_rk(wk), h=8,
                            last=c, last_kind="rk" if g.rest[wk - 1] else "lk", ls=ls, labels=False)
        d.t(rx, y + big + 18 + ls + 4, f"Lager {nf(g.cum_lk(wk))} kr", ls, 400, INK2)
        d.t(x + w, y + big + 18 + ls + 4, f"Restordre {nf(g.cum_rk(wk))} kr", ls, 400, INK2, "end")
        yy = max(yy, y + big + 18 + ls + 4)
    return yy


def chain_seat(d, x, y, w, g, wk, typed=None, ls=13, up="Distributør", down="Detaljist", show_cost=True, mark_week=None):
    """Setets ledd i kjeden. Varene går fra venstre mot høyre, ordre går tynt tilbake.
    Beholdningen er en boks på sann skala (1 px per enhet): lager over grunnlinja, restordre under.
    Røret viser det som er på vei, delt i kjente ankomster, med det som kommer først nærmest noden."""
    base = y + 44
    d.t(x, base - 2, up, ls, 400, INK2)
    d.t(x + w, base - 2, down, ls, 400, INK2, "end")
    pipe_x = x + text_w(up, ls) + 8
    node_w = 54
    node_x = x + w * 0.58 - node_w / 2
    pipe_end = node_x - 16
    arr = [(a, q) for a, q in g.arrivals(wk, typed) if q is not None]
    over = max(g.overdue(wk), 0)
    total = sum(q for _, q in arr) + over
    unit = (pipe_end - pipe_x) / max(total, 40)
    xx = pipe_end
    ph = 12
    pv = f"På vei {g.paavei(wk)}" + (f" + {typed}" if typed is not None else "")
    d.t(x, base - ph - 8, pv, ls, 600, INK)
    for a, q in arr:
        ww = q * unit
        is_t = (typed is not None and a == wk + 4 and mark_week is None) or a == mark_week
        d.rect(xx - ww + 1, base - ph, ww - 1.5, ph, PAPER, INK if is_t else BLUE, 1.6 if is_t else 1.1)
        xx -= ww
    if over:
        ww = over * unit
        d.rect(xx - ww + 1, base - ph, ww - 1.5, ph, TINT, GREY, 1, extra='stroke-dasharray="3 2"')
        xx -= ww
    d.line(pipe_x, base, pipe_end, base, HAIR2, 1)
    # levering inn til noden
    d.line(pipe_end, base - ph / 2, node_x - 2, base - ph / 2, INK, 1.4)
    d.path(f"M{node_x - 7:.1f} {base - ph / 2 - 4:.1f} L{node_x - 2:.1f} {base - ph / 2:.1f} L{node_x - 7:.1f} {base - ph / 2 + 4:.1f}", stroke=INK, sw=1.4)
    d.t(pipe_end - 2, base + ls + 4, f"Levering {g.levering(wk)}", ls, 400, INK2, "end")
    # noden
    lag, rest = g.lager[wk - 1], g.rest[wk - 1]
    d.rect(node_x, base - 30, node_w, 30, PAPER, HAIR2, 1)
    if lag:
        hh = min(lag, 30)
        d.rect(node_x + 1, base - hh, node_w - 2, hh, BLUEF)
        d.line(node_x + 1, base - hh, node_x + node_w - 1, base - hh, BLUE, 1.6)
    if rest:
        hh = min(rest, 40)
        d.rect(node_x + 1, base, node_w - 2, hh, REDF)
        d.line(node_x + 1, base + hh, node_x + node_w - 1, base + hh, RED, 1.6)
    d.line(node_x, base, node_x + node_w, base, INK, 1.2)
    d.t(node_x + node_w / 2, base - 36, "Du", ls, 700, INK, "middle")
    # sendt ut
    sx0 = node_x + node_w + 2
    sx1 = x + w - text_w(down, ls) - 8
    d.line(sx0, base - 8, sx1, base - 8, INK, 1.4)
    d.path(f"M{sx1 - 5:.1f} {base - 12:.1f} L{sx1:.1f} {base - 8:.1f} L{sx1 - 5:.1f} {base - 4:.1f}", stroke=INK, sw=1.4)
    d.t(sx0 + 4, base - 14, f"Sendt {g.sendt(wk)}", ls, 400, INK2)
    # ordre inn, tynt tilbake
    d.path(f"M{sx1:.1f} {base + 10:.1f} L{sx0 + 2:.1f} {base + 10:.1f}", stroke=INK3, sw=1, dash="3 3")
    d.path(f"M{sx0 + 7:.1f} {base + 6:.1f} L{sx0 + 2:.1f} {base + 10:.1f} L{sx0 + 7:.1f} {base + 14:.1f}", stroke=INK3, sw=1)
    d.t(x + w, base + 10 + ls + 3, f"Ordre inn {g.inn(wk)}", ls, 600, INK, "end")
    # status og kostnad under noden
    yb = base + max(rest, 0) + ls + 4 if rest else base + ls + 4
    lab = f"Restordre {rest}" if rest else f"Lager {lag}"
    d.t(node_x + node_w / 2, yb, lab, ls, 600, INK, "middle")
    if show_cost:
        d.t(node_x + node_w / 2, yb + ls + 3, f"{nf(g.wc(wk))} kr", ls, 400, INK2, "middle")
        yb += ls + 3
    return yb


CHAIN = ["Fabrikk", "Distributør", "Grossist", "Detaljist"]


def chain_full(d, x, y, w, seats, wk=None, ls=13, me="Grossist", kunde=True, cost=True, kscale=None, names=True,
               show_vals=True, node_w=64, px=1.0, cost_label=True):
    """Hele kjeden med fire ledd og kundene. Varene går mot høyre. Beholdning som boks på sann skala.
    Under hver node: akkumulert kostnad delt i lagerkostnad (blå) og restordrekostnad (rød), samme kroneskala for alle."""
    n = len(CHAIN) + (1 if kunde else 0)
    step = w / n
    base = y + 30 * px + ls + 14
    xs = [x + i * step for i in range(n)]
    out = {}
    for i, r in enumerate(CHAIN):
        nx = xs[i]
        S = seats[r]
        k = wk or S.n
        lag, rest = S.lager[k - 1], S.rest[k - 1]
        d.rect(nx, base - 30 * px, node_w, 30 * px, PAPER, HAIR2, 1)
        if lag:
            hh = min(lag, 30) * px
            d.rect(nx + 1, base - hh, node_w - 2, hh, BLUEF)
            d.line(nx + 1, base - hh, nx + node_w - 1, base - hh, BLUE, 1.6)
        if rest:
            hh = min(rest, 40) * px
            d.rect(nx + 1, base, node_w - 2, hh, REDF)
            d.line(nx + 1, base + hh, nx + node_w - 1, base + hh, RED, 1.6)
        d.line(nx, base, nx + node_w, base, INK, 1.6 if r == me else 1.1)
        d.t(nx, base - 30 * px - 8, r, ls, 700 if r == me else 600, INK)
        if names:
            d.t(nx + text_w(r, ls) + 6, base - 30 * px - 8, NAVN[r] + (" (deg)" if r == me else ""), ls, 400, INK2)
        if show_vals and wk:
            lab = f"Restordre {rest}" if rest else f"Lager {lag}"
            d.t(nx + node_w + 6, base + (ls + 2 if rest else -4), lab, ls, 600, INK)
        if i < n - 1:
            a0 = nx + node_w + 3
            a1 = xs[i + 1] - 5
            d.line(a0, base - 8, a1, base - 8, INK, 1.1)
            d.path(f"M{a1 - 5:.1f} {base - 12:.1f} L{a1:.1f} {base - 8:.1f} L{a1 - 5:.1f} {base - 4:.1f}", stroke=INK, sw=1.1)
        if cost:
            cy = base + 40 * px + 10
            lk, rk = S.cum_lk(k), S.cum_rk(k)
            sc = kscale or (step - 20) / 700
            d.rect(nx, cy, lk * sc, 9, BLUE)
            d.rect(nx + lk * sc + 1, cy, rk * sc, 9, RED)
            if cost_label:
                d.t(nx, cy + 9 + ls + 4, f"{nf(lk + rk)} kr", ls, 700 if r == me else 600, INK)
            out[r] = (nx, cy)
    if kunde:
        kx = xs[-1]
        d.t(kx, base - 30 * px - 8, "Kundene", ls, 600, INK)
    return {"xs": xs, "base": base, "node_w": node_w, "cost": out}
