"""Konsept 09 Kjedens regning: kostnadsdata, kontroller og tegnefunksjoner for kjedebånd, kostnadsfelt,
kostnadsmatrise, akkumulert kostnad og regningen linje for linje. Alt regnes fra ../_shared/fixture.json."""
from e09lib import *

# Kostnadstrinn for matrisen. Validert med dataviz validate_palette.js --ordinal (lys ende >= 2:1 mot hvit),
# og tekstkontrast i cellene >= 4,5:1 (sjekkes under).
LK = ("#94B8D9", "#6A99C6", "#2B6CA3")   # lagerkost, lys til mørk
RK = ("#E0A099", "#D07B72", "#B5423A")   # restordrekost, lys til mørk
SQ = ("#A9B6C4", "#7F93A8", "#44586F", "#0F2A47")  # strømmer, sekvensiell marine/grå
LAGERKOST, RESTKOST = 0.50, 1.00
UP = {"Detaljist": "Grossist", "Grossist": "Distributør", "Distributør": "Fabrikk", "Fabrikk": "produksjon"}
DOWN = {"Detaljist": "kundene", "Grossist": "Detaljist", "Distributør": "Grossist", "Fabrikk": "Distributør"}


def _lum(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    c = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contrast(a, b):
    la, lb = sorted([_lum(a), _lum(b)])
    return (lb + 0.05) / (la + 0.05)


def cell_style(kind, kr_, bins=(10, 25)):
    """Celle i kostnadsmatrisen: farge etter kostnadsart, trinn etter kroner. Gir (fyll, tekstfarge, vekt).
    Restordre står i tillegg med halvfete tall, så arten aldri bæres av farge alene."""
    if kr_ <= 0 or kind is None:
        return None, INK3, 400
    ramp = LK if kind == "lager" else RK
    i = 0 if kr_ <= bins[0] else (1 if kr_ <= bins[1] else 2)
    return ramp[i], (PAPER if i == 2 else INK), (700 if kind == "rest" else 400)


for _r in (LK, RK):
    assert contrast(_r[0], INK) >= 4.5 and contrast(_r[1], INK) >= 4.5 and contrast(_r[2], PAPER) >= 4.5, _r
    assert contrast(_r[0], PAPER) >= 2.0
assert contrast(SQ[0], INK) >= 4.5 and contrast(SQ[1], INK) >= 4.5 and contrast(SQ[2], PAPER) >= 4.5


def kr(x):
    """Kroner i celler: heltall uten desimaler, halve med ,5."""
    if abs(x - round(x)) < 1e-9:
        return sg(round(x))
    return f"{x:.1f}".replace(".", ",")


Seat.lk = lambda self, w: self.lager[w - 1] * LAGERKOST
Seat.rk = lambda self, w: self.rest[w - 1] * RESTKOST
Seat.ck = lambda self, w: self.lager[w - 1] * LAGERKOST + self.rest[w - 1] * RESTKOST
Seat.kind = lambda self, w: "lager" if self.lager[w - 1] > 0 else ("rest" if self.rest[w - 1] > 0 else None)
Seat.lsum = lambda self, a=1, b=None: sum(self.lk(k) for k in range(a, (b or self.n) + 1))
Seat.rsum = lambda self, a=1, b=None: sum(self.rk(k) for k in range(a, (b or self.n) + 1))

DATASETS = {"spill17": FX["spill17"], "bare": FX["bare_sara_teller_paa_vei"], "alle": FX["alle_teller_paa_vei"]}
CHAIN = {k: {r: Seat(r, v) for r in ROLES} for k, v in DATASETS.items()}
S17, REF = CHAIN["spill17"], CHAIN["alle"]

# Regningen må gå opp: uke for uke, per Rolle og for kjeden, mot loggen. Ellers stopper bygget.
for _k, _seats in CHAIN.items():
    _tot = 0
    for _r, _s in _seats.items():
        _cum = 0
        for _w in range(1, _s.n + 1):
            assert not (_s.lager[_w - 1] and _s.rest[_w - 1]), (_k, _r, _w)
            _cum += _s.ck(_w)
            assert abs(_cum - _s.kostsum(_w)) < 1e-9, (_k, _r, _w)
            if _w > 1:
                assert _s.net(_w) == _s.net(_w - 1) + _s.levering(_w) - _s.inn(_w), (_k, _r, _w)
        assert abs(_s.lsum() + _s.rsum() - DATASETS[_k]["kost_per_rolle"][_r]) < 1e-9, (_k, _r)
        _tot += _s.lsum() + _s.rsum()
    assert abs(_tot - DATASETS[_k]["kjedekost"]) < 1e-9, _k
assert S17["Grossist"].kostsum(11) == 68.0
assert DATASETS["spill17"]["kjedekost"] == 2266.0 and DATASETS["alle"]["kjedekost"] == 1341.0


def chain_week(seats, w):
    return sum(s.ck(w) for s in seats.values())


def chain_cum(seats, w):
    return sum(s.kostsum(w) for s in seats.values())


def chain_sums(seats):
    L = sum(s.lsum() for s in seats.values())
    R = sum(s.rsum() for s in seats.values())
    return L, R


# ---------- Klassens aggregater, regnet fra ekte serier i klasse.spill ----------
def week_cost_from_net(v):
    return v * LAGERKOST if v > 0 else -v * RESTKOST


def class_week_costs(sp):
    """Kjedens ukeskostnad for ett Klassespill, delt i (lager, restordre), regnet fra netto lager per Rolle."""
    n = len(sp["netto_lager"]["Grossist"])
    out = []
    for k in range(n):
        lg = sum(sp["netto_lager"][r][k] * LAGERKOST for r in ROLES if sp["netto_lager"][r][k] > 0)
        rs = sum(-sp["netto_lager"][r][k] * RESTKOST for r in ROLES if sp["netto_lager"][r][k] < 0)
        out.append((lg, rs))
    return out


def role_split(sp, r):
    v = sp["netto_lager"][r]
    return sum(x * LAGERKOST for x in v if x > 0), sum(-x * RESTKOST for x in v if x < 0)


for _sp in FX["klasse"]["spill"]:
    assert abs(sum(a + b for a, b in class_week_costs(_sp)) - _sp["kjedekost"]) < 0.6, _sp["spill"]
    if _sp["status"] == "ferdig":
        for _r in ROLES:
            assert abs(sum(role_split(_sp, _r)) - _sp["kost_per_rolle"][_r]) < 0.6


def median(xs):
    xs = sorted(xs)
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def quart(xs):
    """Kvartiler med samme metode som fixture (lineær interpolasjon)."""
    xs = sorted(xs)

    def q(p):
        i = (len(xs) - 1) * p
        lo = int(i)
        hi = min(lo + 1, len(xs) - 1)
        return xs[lo] + (xs[hi] - xs[lo]) * (i - lo)
    return q(0.25), q(0.5), q(0.75)


FERDIGE = [s for s in FX["klasse"]["spill"] if s["status"] == "ferdig"]
assert len(FERDIGE) == FX["klasse"]["ferdige"]["antall"]
assert median([s["kjedekost"] for s in FERDIGE]) == FX["klasse"]["ferdige"]["kjedekost"]["median"]


# ---------- Kjedebåndet: ett ledd, beholdning på sann skala ----------
def chain_band(d, g, x, y, w, wk, typed=None, u=1.2, ls=13, cost=True, pos=False, over_note=True,
               top=44, bottom=40, labels=True, cost_txt=None, weeks=True, mark=None, node_w=80):
    """Setets eget ledd. Varer går fra venstre mot høyre: det som er på vei (fire plasser, nærmest leddet kommer først),
    inn, lager eller restordre i leddet, ut. Ordre inn kommer fra høyre som tynn marine linje (informasjon mot strømmen).
    Alle bokser i enheter på samme skala (u px per enhet). Returnerer bunnen."""
    role = g.role
    base = y + ls + 14 + top
    pipe_x0 = x
    pipe_w = w * 0.46
    slot = (pipe_w - 3 * 5) / 4
    node_x = x + pipe_w + (w - pipe_w - node_w) * 0.42
    out_x0 = node_x + node_w
    arrs = g.arrivals(wk, typed)  # (uke, antall), nærmeste først
    d.line(pipe_x0, base, x + w, base, HAIR2, 1)
    for j, (week, qty) in enumerate(reversed(arrs)):  # lengst unna til venstre
        sx = pipe_x0 + j * (slot + 5)
        is_typed = (week == wk + 4) if mark is None else (week == mark)
        if qty is None:
            d.rect(sx, base - 14, slot, 14, "none", INK, 1.2, extra='stroke-dasharray="3 3"')
        else:
            hh = max(qty * u, 1.5)
            d.rect(sx, base - hh, slot, hh, PAPER, INK if is_typed else BLUE, 1.6 if is_typed else 1.2)
            if labels:
                d.t(sx + slot / 2, base - hh - 4, qty, ls, 700 if is_typed else 400, INK, "middle")
        if labels and weeks:
            d.t(sx + slot / 2, base + ls + 3, f"Uke {week}" if j == 0 else str(week), ls, 400, INK3, "middle")
    # inn til leddet
    lev = g.levering(wk)
    ax0 = pipe_x0 + pipe_w + 6
    d.line(ax0, base - 7, node_x - 5, base - 7, INK2, 1.4)
    d.path(f"M{node_x - 10:.1f} {base - 11:.1f} L{node_x - 4:.1f} {base - 7:.1f} L{node_x - 10:.1f} {base - 3:.1f}", stroke=INK2, sw=1.4)
    if labels:
        d.t((ax0 + node_x) / 2, base + ls + 3, f"inn {lev}", ls, 600, INK, "middle")
    # leddet: lager over grunnlinja, restordre under, på samme skala som røret
    lg, rs = g.lager[wk - 1], g.rest[wk - 1]
    d.rect(node_x, base - top, node_w, top + bottom - 4, "none", HAIR2, 1, 3)
    if lg:
        d.rect(node_x + 7, base - min(lg * u, top - 2), node_w - 14, min(lg * u, top - 2), BLUEF, BLUE, 1)
    if rs:
        d.rect(node_x + 7, base, node_w - 14, min(rs * u, bottom - 6), REDF, RED, 1)
    if labels:
        lab = f"Restordre {rs}" if rs else f"Lager {lg}"
        if rs:
            rh_ = min(rs * u, bottom - 6)
            yl = base + rh_ - 5 if rh_ >= ls + 6 else base + rh_ + ls + 2
            d.t(node_x + node_w / 2, yl, lab, ls, 600, INK, "middle")
        else:
            lh_ = min(lg * u, top - 2)
            yl = base - lh_ + ls + 1 if lh_ >= ls + 6 else base - lh_ - 5
            d.t(node_x + node_w / 2, yl, lab, ls, 600, INK, "middle")
    # ut fra leddet
    sendt = g.sendt(wk)
    d.line(out_x0 + 5, base - 7, x + w - 3, base - 7, INK2, 1.4)
    d.path(f"M{x + w - 9:.1f} {base - 11:.1f} L{x + w - 3:.1f} {base - 7:.1f} L{x + w - 9:.1f} {base - 3:.1f}", stroke=INK2, sw=1.4)
    if labels:
        d.t((out_x0 + x + w) / 2, base + ls + 3, f"ut {sendt}", ls, 600, INK, "middle")
    # ordre inn og på vei: øverste linje
    yi = y + ls
    if labels:
        d.t(x + w, yi, f"Ordre inn {g.inn(wk)}", ls, 600, INK, "end")
        xo = x + w - text_w(f"Ordre inn {g.inn(wk)}", ls) - 6
        d.path(f"M{xo:.1f} {yi - 4:.1f} L{node_x + node_w - 8:.1f} {yi - 4:.1f} L{node_x + node_w - 8:.1f} {base - top:.1f}", stroke=INK, sw=1)
        pv = g.paavei(wk)
        s1 = f"På vei {pv}" + (f" + {typed}" if typed else "")
        d.t(x, yi, s1, ls, 600, INK)
        d.t(x + text_w(s1, ls) + 6, yi, f"fra {UP[role]}", ls, 400, INK2)
    yb = base + bottom
    over = g.overdue(wk)
    if over > 0 and over_note and labels:
        d.t(x, yb + ls - 2, f"+ {over} forsinket hos {UP[role]}, uten dato", ls, 400, INK2)
        yb += ls + 4
    if pos:
        p = g.posisjon(wk) + (typed or 0)
        yy = yb + 4
        d.line(pipe_x0, yy, node_x + node_w, yy, INK, 1.2)
        d.line(pipe_x0, yy - 5, pipe_x0, yy + 1, INK, 1.2)
        d.line(node_x + node_w, yy - 5, node_x + node_w, yy + 1, INK, 1.2)
        d.t(pipe_x0, yy + ls + 5, f"Posisjon {g.lager[wk - 1]} − {rs} + {g.paavei(wk) + (typed or 0)} = {sg(p)}", ls, 700, INK)
        yb = yy + ls + 8
    if cost:
        c = g.ck(wk)
        txt = cost_txt or (f"Uka koster {nf(c)} kr: {rs} i restordre × 1,00" if rs else f"Uka koster {nf(c)} kr: {lg} på lager × 0,50")
        d.t(x, yb + ls + 2, txt, ls, 400, INK2)
        yb += ls + 6
    return yb


# ---------- Kostnadsfeltet i meteogrammet ----------
def cost_field(d, ax, y, h, g, wfrom, wto, cap=40, x1=None, nums=False, ls=13):
    """Ukas kostnad som stolpe, blå for lager og rød for restordre, på samme tidsakse som meteogrammet."""
    u = h / cap
    bw = max(ax.slot - 2.5, 2)
    base = y + h
    for w in range(wfrom, wto + 1):
        c = g.ck(w)
        if c <= 0:
            continue
        col = BLUE if g.kind(w) == "lager" else RED
        hh = min(c, cap) * u
        d.rect(ax.xc(w) - bw / 2, base - hh, bw, hh, col)
        if nums:
            d.t(ax.xc(w), base - hh - 3, kr(c), ls, 400, INK, "middle")
    d.line(ax.x0, base, x1 or ax.x1, base, HAIR2, 1)
    return base


def cost_matrix(d, x, y, ax, seats, roles, rowh=26, ls=13, wfrom=1, wto=36, bins=(10, 25), totals=True, tot_x=None,
                chainrow=True, highlight=None, bold_role=None, sub=None, tot_w=230, cell_ls=None):
    """Rolle × uke i kroner. Hver celle er ukas kostnad for leddet. Høyre: lagerkost, restordrekost og sum.
    Nederste rad: kjeden per uke."""
    yy = y
    cl = cell_ls or ls - 1
    tot_x = tot_x or ax.x1 + 12
    cw = ax.slot
    c1, c2, c3 = tot_x + tot_w * 0.30, tot_x + tot_w * 0.65, tot_x + tot_w
    if totals:
        for xx, h in ((c1, "Lager"), (c2, "Restordre"), (c3, "Sum, kr")):
            d.t(xx, yy - 8, h, ls, 600, INK2, "end")
    for r in roles:
        s = seats[r]
        d.t(x, yy + rowh / 2 + ls * 0.34 - (6 if sub else 0), r, ls, 700 if r == bold_role else 600, INK)
        if sub:
            d.t(x, yy + rowh / 2 + ls * 0.34 + 9, sub[r], ls - 1, 400, INK2)
        for w in range(wfrom, wto + 1):
            c = s.ck(w)
            fill, txt, wt = cell_style(s.kind(w), c, bins)
            cx = ax.xl(w)
            if fill:
                d.rect(cx + 1, yy + 1, cw - 2, rowh - 2, fill)
                d.t(cx + cw / 2, yy + rowh / 2 + cl * 0.34, kr(c), cl, wt, txt, "middle")
            else:
                d.rect(cx + 1, yy + 1, cw - 2, rowh - 2, "none", HAIR, 1)
        if totals:
            L, R = s.lsum(wfrom, wto), s.rsum(wfrom, wto)
            yt = yy + rowh / 2 + ls * 0.34
            d.t(c1, yt, nf(L), ls, 400, INK, "end")
            d.t(c2, yt, nf(R), ls, 700, INK, "end")
            d.t(c3, yt, nf(L + R), ls, 600, INK, "end")
        yy += rowh
    if chainrow:
        d.line(x, yy + 3, c3 if totals else ax.x1, yy + 3, INK, 1)
        yy += 6
        d.t(x, yy + rowh / 2 + ls * 0.34, "Kjeden", ls, 700, INK)
        for w in range(wfrom, wto + 1):
            c = sum(seats[r].ck(w) for r in roles)
            d.t(ax.xc(w), yy + rowh / 2 + cl * 0.34, kr(c), cl, 600, INK, "middle")
        if totals:
            L = sum(seats[r].lsum(wfrom, wto) for r in roles)
            R = sum(seats[r].rsum(wfrom, wto) for r in roles)
            yt = yy + rowh / 2 + ls * 0.34
            d.t(c1, yt, nf(L), ls, 600, INK, "end")
            d.t(c2, yt, nf(R), ls, 700, INK, "end")
            d.t(c3, yt, nf(L + R), ls, 700, INK, "end")
        yy += rowh
    if highlight:
        d.rect(ax.xl(highlight) + 0.5, y - 2, cw - 1, yy - y + 2, "none", INK, 1.6)
    return yy


def cum_lines(seats, roles, wfrom=1, wto=36):
    """Akkumulert lagerkost og total per uke."""
    sl = sr = 0
    out = []
    for w in range(wfrom, wto + 1):
        sl += sum(seats[r].lk(w) for r in roles)
        sr += sum(seats[r].rk(w) for r in roles)
        out.append((w, sl, sl + sr))
    return out


def cum_area(d, ax, y, h, seats, roles, hi, wfrom=1, wto=36, ref=None, ls=13, ticks=(), x1=None):
    """Akkumulert kostnad, stablet: lagerkost nederst (blå), restordrekost over (rød). Valgfri stiplet referanse."""
    Y = yscale(y, h, 0, hi)
    for v in ticks:
        d.line(ax.x0, Y(v), x1 or ax.x1, Y(v), HAIR2 if v == 0 else HAIR, 1)
        d.t(ax.x0 - 6, Y(v) + ls * 0.34, nf(v, 0), ls, 400, INK3, "end")
    pts = cum_lines(seats, roles, wfrom, wto)
    cl = [(ax.xc(w), Y(a)) for w, a, _ in pts]
    ct = [(ax.xc(w), Y(b)) for w, _, b in pts]
    x0 = ax.xc(wfrom)
    d.path(f"M{x0:.1f} {Y(0):.1f} " + " ".join(f"L{a:.1f} {b:.1f}" for a, b in cl) + f" L{cl[-1][0]:.1f} {Y(0):.1f} Z", BLUEF)
    d.path("M" + " L".join(f"{a:.1f} {b:.1f}" for a, b in cl) + " " + " ".join(f"L{a:.1f} {b:.1f}" for a, b in reversed(ct)) + " Z", REDF)
    d.path("M" + " L".join(f"{a:.1f} {b:.1f}" for a, b in cl), stroke=BLUE, sw=1.4)
    d.path("M" + " L".join(f"{a:.1f} {b:.1f}" for a, b in ct), stroke=INK, sw=2)
    rpts = None
    if ref is not None:
        rpts = [(ax.xc(w), Y(b)) for w, _, b in cum_lines(ref, roles, wfrom, wto)]
        d.path("M" + " L".join(f"{a:.1f} {b:.1f}" for a, b in rpts), stroke=INK, sw=1.4, dash="6 4")
    return Y, pts, rpts


def ledger(d, x, y, w, seats, roles, ref=None, ls=14, rowh=25, bar_x=None, total_scale=None, ref_name="Simulert",
           head=True, col1=None, col2=None):
    """Regningen, linje for linje: Rolle og kostnadsart, med fossefall som ender i kjedens sum.
    Simulert referanse som egen kolonne og som tynn grå strek under hver linje."""
    col1 = col1 or x + 218
    col2 = col2 or x + 300
    bar_x = bar_x or col2 + 22
    bar_w = x + w - bar_x
    L, R = chain_sums(seats)
    tot = L + R
    rtot = sum(chain_sums(ref)) if ref else 0
    sc = bar_w / (total_scale or max(tot, rtot))
    yy = y
    if head:
        d.t(col1, yy, "Spill 17, kr", ls - 1, 600, INK2, "end")
        if ref:
            d.t(col2, yy, ref_name, ls - 1, 600, INK2, "end")
        d.line(x, yy + 8, x + w, yy + 8, HAIR2, 1)
        yy += rowh + 2
    run = rrun = 0
    for r in roles:
        for kind, lab in (("lager", "lager"), ("rest", "restordre")):
            v = seats[r].lsum() if kind == "lager" else seats[r].rsum()
            rv = (ref[r].lsum() if kind == "lager" else ref[r].rsum()) if ref else 0
            d.t(x, yy, f"{r}, {lab}", ls, 400, INK)
            d.t(col1, yy, nf(v), ls, 700 if kind == "rest" else 400, INK, "end")
            if ref:
                d.t(col2, yy, nf(rv), ls, 400, INK2, "end")
            col = BLUE if kind == "lager" else RED
            fill = BLUEF if kind == "lager" else REDF
            d.rect(bar_x + run * sc, yy - ls + 3, v * sc, ls - 2, fill, col, 1)
            if ref:
                d.rect(bar_x + rrun * sc, yy + 3, rv * sc, 3, INK3)
            run += v
            rrun += rv
            yy += rowh
    d.line(x, yy - rowh + 10, x + w, yy - rowh + 10, INK, 1)
    yy += 6
    d.t(x, yy, "Kjeden", ls + 2, 700, INK)
    d.t(col1, yy, nf(tot), ls + 2, 700, INK, "end")
    if ref:
        d.t(col2, yy, nf(rtot), ls + 2, 600, INK2, "end")
    d.rect(bar_x, yy - ls + 1, tot * sc, ls - 1, INK)
    if ref:
        d.rect(bar_x, yy + 4, rtot * sc, 4, INK3)
    assert abs(run - tot) < 1e-9 and (not ref or abs(rrun - rtot) < 1e-9)
    return yy, sc, bar_x


def phone_head(d, wk, cost, role="Grossist", spill="Spill 17"):
    d.t(20, 62, f"Uke {wk}", 30, 700, INK)
    d.t(20, 84, f"{role}, {spill}", 14, 400, INK2)
    d.t(370, 58, "Din del av regningen", 13, 400, INK2, "end")
    d.t(370, 82, f"{nf(cost)} kr", 20, 700, INK, "end", 'style="font-variant-numeric:lining-nums proportional-nums"')


# ---------- Meteogrammet med kostnadsfelt: fire felt på én tidsakse ----------
def swatch_title(d, x, y, items, ls=13):
    xx = x
    for lab, col in items:
        if col:
            d.rect(xx, y - 10, 10, 10, col)
            xx += 14
        d.t(xx, y, lab, ls, 600, INK)
        xx += text_w(lab, ls) + 14
    return xx


def stack_chart(d, g, x, y, w, now, typed=None, panels=(("net", 100), ("flow", 36), ("ord", 30), ("cost", 34)),
                wmin=None, wmax=None, left=30, gap=16, ls=13, titles=True, xstep=2, lo=-40, hi=30, ticks=(-40, -20, 0, 20),
                fmax=32, omax=25, cmax=40, cost_cells=False, arrnums=True, axis=True, now_label="Nå", connector=True,
                side_labels=None, show_future=True, ord_label=True, net_label=True, cost_label=True, bins=(10, 25)):
    """Netto lager, inn og ut, egen ordre og ukas kostnad, på samme tidsakse. Til høyre for nå: bare det som er kjent."""
    wmin = wmin if wmin is not None else max(1, now - 11)
    wmax = wmax if wmax is not None else (now + 4 if show_future else now)
    ax = Axis(x + left, w - left, wmin, wmax)
    th = (ls + 7) if titles else 0
    ys = {}
    yy = y
    for name, h in panels:
        yy += th
        ys[name] = (yy, h)
        yy += h + gap
    ybot = yy - gap
    fx0, fx1_ = ax.xr(now), ax.xr(wmax)
    if wmax > now:
        d.rect(fx0, y + (th if titles else 0) - 4, fx1_ - fx0, ybot - y - (th if titles else 0) + 4, TINT)
    out = {"ax": ax, "fx0": fx0, "fx1": fx1_, "ybot": ybot, "ys": ys}
    bw = max(ax.slot - 2.5, 2)
    for name, h in panels:
        y0, _ = ys[name]
        if name == "net":
            Y = grid(d, ax, y0, h, lo, hi, ticks, ls, x1=fx1_)
            net_area(d, ax, y0, h, g.net, wmin, now, lo, hi)
            d.circle(ax.xc(now), Y(g.net(now)), 4, BLUE if g.net(now) >= 0 else RED, PAPER, 2)
            if net_label:
                lab = f"Lager {g.lager[now - 1]}" if g.net(now) >= 0 else f"Restordre {g.rest[now - 1]}"
                d.t(fx0 + 6, Y(g.net(now)) + ls * 0.34, lab, ls, 600, INK)
            out["Y"] = Y
            if titles:
                d.t(x, y0 - 7, "Lager over null, restordre under", ls, 600, INK)
        elif name == "flow":
            flow_bars(d, ax, y0, h, g, wmin, now, fmax, x1=fx1_)
            u = h / fmax
            if show_future:
                for week, qty in g.arrivals(now, typed):
                    if week > wmax:
                        continue
                    xx = ax.xc(week) - (bw - 1) / 2
                    if qty is None:
                        d.rect(xx, y0 + h - 14, bw - 1, 14, "none", INK, 1, extra='stroke-dasharray="3 3"')
                        continue
                    it = week == now + 4
                    d.rect(xx, y0 + h - qty * u, bw - 1, qty * u, PAPER, INK if it else BLUE, 1.5 if it else 1.1)
                    if arrnums:
                        d.t(ax.xc(week), y0 + h - qty * u - 3, qty, ls, 700 if it else 400, INK, "middle")
            if titles:
                lev, inn = g.levering(now), g.inn(now)
                if lev <= inn:
                    swatch_title(d, x, y0 - 7, [(f"Levering {lev}", BASE), (f"Ordre inn {inn}", RED if inn > lev else BASE)], ls)
                else:
                    swatch_title(d, x, y0 - 7, [(f"Ordre inn {inn}", BASE), (f"Levering {lev}", BLUE)], ls)
            out["yflow"] = y0
        elif name == "ord":
            order_bars(d, ax, y0, h, g.order, wmin, now - 1, omax, x1=fx1_)
            u = h / omax
            if typed is None:
                d.rect(ax.xc(now) - bw / 2, y0 + h - 14, bw, 14, "none", INK, 1.2, extra='stroke-dasharray="3 3"')
            else:
                d.rect(ax.xc(now) - bw / 2, y0 + h - min(typed, omax) * u, bw, min(typed, omax) * u, INK)
                if ord_label:
                    d.t(ax.xc(now), y0 + h - min(typed, omax) * u - 4, typed, ls, 700, INK, "middle")
                if connector and "flow" in ys and show_future and now + 4 <= wmax:
                    yf, hf_ = ys["flow"]
                    d.path(f"M{ax.xc(now) + bw / 2:.1f} {y0 + h - min(typed, omax) * u + 2:.1f} L{ax.xc(now + 4):.1f} {yf + hf_ + 1:.1f}", stroke=INK, sw=1)
            if titles:
                d.t(x, y0 - 7, "Din ordre", ls, 600, INK)
            out["yord"] = y0
        elif name == "cost":
            if cost_cells:
                for k in range(wmin, now + 1):
                    c = g.ck(k)
                    fill, txt, wt = cell_style(g.kind(k), c, bins)
                    if fill:
                        d.rect(ax.xl(k) + 1, y0, ax.slot - 2, h, fill)
                        d.t(ax.xc(k), y0 + h / 2 + (ls - 2) * 0.34, kr(c), ls - 2, wt, txt, "middle")
                    else:
                        d.rect(ax.xl(k) + 1, y0, ax.slot - 2, h, "none", HAIR, 1)
            else:
                cost_field(d, ax, y0, h, g, wmin, now, cmax, x1=fx1_)
                if cost_label:
                    d.t(fx0 + 6, y0 + h - 2, f"{nf(g.ck(now))} kr", ls, 600, INK)
            if titles:
                swatch_title(d, x, y0 - 7, [("Kostnad per uke:", None), ("lager", BLUE), ("restordre", RED)], ls)
            out["ycost"] = y0
    first = ys[panels[0][0]][0]
    d.line(fx0, first - (th if titles else 4) - 2, fx0, ybot + 3, INK, 1.4)
    if now_label and wmax > now:
        d.t(fx0 + 5, first - (th if titles else 4) + ls - 4, now_label, ls, 700, INK)
    if axis:
        wks = [k for k in range(wmin, wmax + 1) if (k - now) % xstep == 0]
        xaxis(d, ax, ybot + ls + 4, wks, now, ls)
    out["axisbot"] = ybot + ls + 6
    if side_labels:
        for name, lab in side_labels.items():
            if name in ys:
                y0, h = ys[name]
                d.t(x - 8, y0 + h / 2 + 4, lab, ls, 400, INK2, "end")
    return out
