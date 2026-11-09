"""Felles byggeklosser for konsept 01 Kjedebåndet (runde 3): SVG-dokument, tekstbryting, skalaer, meteogrammet med kostnadsfelt,
kjedebåndet og matrisen. Bygd videre fra runde 2, 02 Meteogrammet.
Alle tall kommer fra ../_shared/fixture.json."""
import json
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
FX = json.loads((HERE.parent / "_shared" / "fixture.json").read_text(encoding="utf-8"))

# Palett
PAPER = "#FFFFFF"
INK = "#0F2A47"      # dyp marine
INK2 = "#44586F"     # sekundærtekst
INK3 = "#5E6F82"     # dempet tekst, 5,1:1 på hvit
HAIR = "#E1E6EC"     # hjelpelinje
HAIR2 = "#C3CDD8"    # akse, ramme
TINT = "#F2F5F8"     # flaten til høyre for nå
BLUE = "#2B6CA3"     # over null
BLUEF = "#CDDFEE"    # fyll over null
RED = "#B5423A"      # under null
REDF = "#F0D5D2"     # fyll under null
GREY = "#6B7785"     # projeksjon
BASE = "#B4C4D4"     # felles del av inn og ut
ORD = "#5F7A95"      # ordrehistorikk
FONT = "'Source Sans 3','Source Sans Pro','Segoe UI',Arial,sans-serif"
ROLES = ["Detaljist", "Grossist", "Distributør", "Fabrikk"]
NAVN = {"Detaljist": "Ida", "Grossist": "Sara", "Distributør": "Mikkel", "Fabrikk": "Jonas"}


def nf(x, dec=2):
    s = f"{abs(x):,.{dec}f}".replace(",", " ").replace(".", ",")
    return ("−" + s) if x < 0 else s


def sg(x):
    """Heltall med ekte minustegn."""
    return f"−{abs(int(x))}" if x < 0 else str(int(x))


def fx1(x):
    return f"{x:.1f}".replace(".", ",") + "×"


NARROW = set("iljtfrI.,:;'|!() ")
WIDE = set("mwMWæÆ—")


def text_w(s, size):
    total = 0.0
    for c in s:
        if c in NARROW:
            total += 0.29
        elif c in WIDE:
            total += 0.8
        elif c.isupper():
            total += 0.6
        else:
            total += 0.5
    return total * size


def wrap(s, width, size):
    lines, cur = [], ""
    for word in s.split():
        test = (cur + " " + word).strip()
        if text_w(test, size) <= width or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


class Doc:
    def __init__(self, name, W, H, title, desc):
        self.name, self.W, self.H, self.title, self.desc = name, W, H, title, desc
        self.b = []
        self.n = 0

    def add(self, s):
        self.b.append(s)

    def uid(self, kind="c"):
        self.n += 1
        return f"e01-{self.name}-{kind}{self.n}"

    def t(self, x, y, s, size=14, w=400, fill=INK, a="start", extra=""):
        self.b.append(
            f'<text class="e01-t" x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{w}" '
            f'fill="{fill}" text-anchor="{a}"{(" " + extra) if extra else ""}>{escape(str(s))}</text>'
        )

    def para(self, x, y, s, width, size=14, lh=None, w=400, fill=INK, a="start"):
        lh = lh or round(size * 1.38)
        for line in wrap(s, width, size):
            self.t(x, y, line, size, w, fill, a)
            y += lh
        return y

    def rect(self, x, y, w, h, fill="none", stroke=None, sw=1, rx=0, extra=""):
        st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
        rxs = f' rx="{rx}"' if rx else ""
        self.b.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(w, 0):.1f}" height="{max(h, 0):.1f}" fill="{fill}"{st}{rxs}{(" " + extra) if extra else ""}/>')

    def line(self, x1, y1, x2, y2, stroke=HAIR, sw=1, dash=None, extra=""):
        ds = f' stroke-dasharray="{dash}"' if dash else ""
        self.b.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{sw}"{ds}{(" " + extra) if extra else ""}/>')

    def path(self, dd, fill="none", stroke=None, sw=2, dash=None, extra=""):
        st = f' stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round" stroke-linecap="round"' if stroke else ""
        ds = f' stroke-dasharray="{dash}"' if dash else ""
        self.b.append(f'<path d="{dd}" fill="{fill}"{st}{ds}{(" " + extra) if extra else ""}/>')

    def circle(self, x, y, r, fill=INK, stroke=None, sw=2):
        st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
        self.b.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}"{st}/>')

    def g(self, transform=None, clip=None):
        attrs = ""
        if transform:
            attrs += f' transform="{transform}"'
        if clip:
            attrs += f' clip-path="url(#{clip})"'
        self.b.append(f"<g{attrs}>")

    def end(self):
        self.b.append("</g>")

    def cliprect(self, x, y, w, h):
        cid = self.uid("clip")
        self.b.append(f'<clipPath id="{cid}"><rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}"/></clipPath>')
        return cid

    def button(self, x, y, w, h, label, primary=True, size=16):
        self.rect(x, y, w, h, INK if primary else PAPER, None if primary else HAIR2, 1, 6)
        self.t(x + w / 2, y + h / 2 + size * 0.34, label, size, 600, PAPER if primary else INK, "middle")

    def demodata(self, x, y, s="Demodata", size=13, a="start"):
        self.t(x, y, s, size, 400, INK3, a)

    def save(self):
        css = (
            "@import url('https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;600;700&amp;display=swap');"
            f".e01-t{{font-family:{FONT};font-variant-numeric:lining-nums tabular-nums;}}"
        )
        out = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.W} {self.H}" font-family="{FONT}">'
            f"<title>{escape(self.title)}</title><desc>{escape(self.desc)}</desc><style>{css}</style>"
            f'<rect x="0" y="0" width="{self.W}" height="{self.H}" fill="{PAPER}"/>' + "".join(self.b) + "</svg>"
        )
        (HERE / f"{self.name}.svg").write_text(out, encoding="utf-8")


# ---------- Data ----------
class Seat:
    """Ett setes serier, med ukenummer som indeks (uke 1 = første)."""

    def __init__(self, role="Grossist", src=None):
        src = src or FX["spill17"]
        s = src["serier"][role]
        self.role = role
        self.ordre, self.lager, self.rest = s["ordre"], s["lager"], s["restordre"]
        self.innk, self.lev, self.pv, self.kost = s["innkommende_ordre"], s["levering"], s["paa_vei"], s["kost_sum"]
        self.n = len(self.ordre)
        self.net_ = [a - b for a, b in zip(self.lager, self.rest)]
        prev = 0
        self.sendt_ = []
        for i in range(self.n):
            self.sendt_.append(self.innk[i] + prev - self.rest[i] if self.rest[i] or prev else self.innk[i])
            prev = self.rest[i]

    def net(self, w):
        return self.net_[w - 1]

    def order(self, w):
        return self.ordre[w - 1] if w >= 1 else 4

    def inn(self, w):
        return self.innk[w - 1]

    def levering(self, w):
        return self.lev[w - 1]

    def sendt(self, w):
        return self.sendt_[w - 1]

    def paavei(self, w):
        return self.pv[w - 1]

    def posisjon(self, w):
        return self.net(w) + self.paavei(w)

    def kostsum(self, w):
        return self.kost[w - 1]

    def arrivals(self, w, typed):
        """Kjente ankomster de neste fire ukene. Siste plass er ordren som tastes nå."""
        out = [(w + j, self.order(w + j - 4)) for j in (1, 2, 3)]
        out.append((w + 4, typed))
        return out

    def overdue(self, w):
        """Bestilt, men over fire uker gammelt: ligger hos leverandøren uten kjent dato."""
        return self.paavei(w) - sum(self.order(k) for k in (w - 3, w - 2, w - 1))

    def lagerkost(self, w):
        return self.lager[w - 1] * 0.5

    def restkost(self, w):
        return self.rest[w - 1] * 1.0

    def ukekost(self, w):
        return self.lagerkost(w) + self.restkost(w)

    def cum_lager(self, w):
        return sum(self.lagerkost(k) for k in range(1, w + 1))

    def cum_rest(self, w):
        return sum(self.restkost(k) for k in range(1, w + 1))

    def projection(self, w, typed):
        """Netto lager hvis ordre inn holder seg som nå og bare planlagte ankomster kommer. Sum over uker."""
        rate = self.inn(w)
        net = self.net(w)
        pts = [(w, net)]
        for week, qty in self.arrivals(w, typed):
            net += (qty or 0) - rate
            pts.append((week, net))
        return pts


# Materialbalansen må stemme med loggen før noe tegnes.
_g = Seat()
for _w in range(2, _g.n + 1):
    assert _g.net(_w) == _g.net(_w - 1) + _g.levering(_w) - _g.inn(_w), _w
assert _g.posisjon(11) == 3
# Kostnaden må gå opp: ukekost = lager × 0,50 + restordre × 1,00, og summen er kost_sum, per Rolle og for kjeden.
for _src in (FX["spill17"], FX["bare_sara_teller_paa_vei"], FX["alle_teller_paa_vei"]):
    _tot = 0
    for _r in ROLES:
        _s = Seat(_r, _src)
        for _w in range(1, _s.n + 1):
            _prev = _s.kostsum(_w - 1) if _w > 1 else 0
            assert abs(_s.ukekost(_w) - (_s.kostsum(_w) - _prev)) < 1e-9, (_r, _w)
            assert abs(_s.cum_lager(_w) + _s.cum_rest(_w) - _s.kostsum(_w)) < 1e-9
        assert abs(_s.kostsum(_s.n) - _src["kost_per_rolle"][_r]) < 1e-9, _r
        _tot += _s.kostsum(_s.n)
    assert abs(_tot - _src["kjedekost"]) < 1e-9
# Klassespillene: kjedekost = sum over Roller og uker av (positivt netto lager × 0,50 + restordre × 1,00).
for _sp in FX["klasse"]["spill"]:
    _t = sum(v * 0.5 if v > 0 else -v for _r in ROLES for v in _sp["netto_lager"][_r])
    assert abs(_t - _sp["kjedekost"]) < 0.6, _sp["spill"]
    assert all(len(_sp["netto_lager"][_r]) == _sp["uke"] for _r in ROLES)
assert _g.projection(11, 24)[-1] == (15, -5)
assert _g.projection(11, 24)[-1][1] == _g.posisjon(11) + 24 - 4 * _g.inn(11)


class Axis:
    def __init__(self, x0, w, wmin, wmax):
        self.x0, self.w, self.wmin, self.wmax = x0, w, wmin, wmax
        self.slot = w / (wmax - wmin + 1)
        self.x1 = x0 + w

    def xc(self, week):
        return self.x0 + (week - self.wmin + 0.5) * self.slot

    def xl(self, week):
        return self.x0 + (week - self.wmin) * self.slot

    def xr(self, week):
        return self.xl(week + 1)


def yscale(y0, h, lo, hi):
    return lambda v: y0 + h - (v - lo) / (hi - lo) * h


def net_area(d, ax, y0, h, vals, wfrom, wto, lo=-40, hi=30, lw=2, fills=True):
    """Netto lager: blått over null, rødt under. vals(w) gir verdien."""
    Y = yscale(y0, h, lo, hi)
    pts = [(ax.xc(w), Y(vals(w))) for w in range(wfrom, wto + 1)]
    line = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    area = line + f" L{pts[-1][0]:.1f} {Y(0):.1f} L{pts[0][0]:.1f} {Y(0):.1f} Z"
    up = d.cliprect(ax.x0, y0 - 2, ax.w, Y(0) - y0 + 2)
    dn = d.cliprect(ax.x0, Y(0), ax.w, y0 + h - Y(0) + 2)
    d.g(clip=up)
    if fills:
        d.path(area, BLUEF)
    d.path(line, stroke=BLUE, sw=lw)
    d.end()
    d.g(clip=dn)
    if fills:
        d.path(area, REDF)
    d.path(line, stroke=RED, sw=lw)
    d.end()
    return Y


def grid(d, ax, y0, h, lo, hi, ticks, size=13, labels=True, x1=None):
    Y = yscale(y0, h, lo, hi)
    x1 = x1 or ax.x1
    for v in ticks:
        d.line(ax.x0, Y(v), x1, Y(v), HAIR2 if v == 0 else HAIR, 1)
        if labels:
            d.t(ax.x0 - 5, Y(v) + size * 0.34, sg(v), size, 400, INK3, "end")
    return Y


def flow_bars(d, ax, y0, h, g, wfrom, wto, scale=32, r=1.5, sendt=False, x1=None):
    """Levering og ordre inn per uke. Avstanden mellom dem er endringen i netto lager (P1)."""
    u = h / scale
    bw = max(ax.slot - 2.5, 2)
    base = y0 + h
    for w in range(wfrom, wto + 1):
        lev, inn = g.levering(w), g.inn(w)
        x = ax.xc(w) - bw / 2
        low = min(lev, inn)
        d.rect(x, base - low * u, bw, low * u, BASE)
        diff = abs(lev - inn) * u
        if diff > 0:
            col = RED if inn > lev else BLUE
            d.rect(x, base - low * u - diff - 1, bw, diff, col)
        if sendt:
            ys = base - g.sendt(w) * u
            d.line(x - 0.5, ys, x + bw + 0.5, ys, INK, 1.5)
    d.line(ax.x0, base, x1 or ax.x1, base, HAIR2, 1)


def order_bars(d, ax, y0, h, vals, wfrom, wto, scale=25, fill=ORD, x1=None):
    u = h / scale
    bw = max(ax.slot - 2.5, 2)
    base = y0 + h
    for w in range(wfrom, wto + 1):
        v = vals(w)
        d.rect(ax.xc(w) - bw / 2, base - v * u, bw, v * u, fill)
    d.line(ax.x0, base, x1 or ax.x1, base, HAIR2, 1)


def xaxis(d, ax, y, weeks, now=None, size=13):
    for w in weeks:
        bold = w == now
        d.t(ax.xc(w), y, w, size, 700 if bold else 400, INK if bold else INK3, "middle")


def meteo(d, g, x, y, w, now, typed=None, wmin=None, hn=170, hf=64, gap=24, ls=13, left=34, xstep=2,
          proj=False, ghost=None, actual=False, sendt=False, titles=True, connector=True, lo=-40, hi=30,
          fmax=32, omax=25, futnote="Bestilt, ikke garantert", netlabel=True, ticks=(-40, -20, 0, 20),
          t_net="Lager over null, restordre under", t_flow=None, t_ord="Din ordre", nowlabel="Nå", axislabel=True,
          arrnums=True, ordlabel=True, wmax=None, overduenote=True, projlabel=True, overdue_out=False,
          cost=False, hc=36, cmax=40, t_cost="Kostnad per uke", costsum=True, costnum=True):
    """Hele meteogrammet: netto lager, inn og ut, egen ordre. Deler én tidsakse.
    Til høyre for nå ligger bare det som er kjent. Høyre kant er alltid nå + 4."""
    wmin = wmin if wmin is not None else max(1, now - 11)
    wmax = wmax if wmax is not None else now + 4
    ax = Axis(x + left, w - left, wmin, wmax)
    u = hf / fmax
    ho = omax * u
    title_h = ls + 7 if titles else 0
    ynet = y + (title_h if titles else 15)
    yflow = ynet + hn + gap + title_h
    yord = yflow + hf + gap + title_h
    ycost = yord + ho + gap + title_h
    ybot = (ycost + hc) if cost else (yord + ho)
    fx0 = ax.xr(now)
    fx1_ = ax.xr(now + 4)
    # Flaten til høyre for nå
    d.rect(fx0, ynet - 2, fx1_ - fx0, ybot - ynet + 2, TINT)

    # Panel 1: netto lager
    Y = grid(d, ax, ynet, hn, lo, hi, ticks, ls, x1=fx1_)
    net_area(d, ax, ynet, hn, g.net, wmin, now, lo, hi)
    arrs = g.arrivals(now, typed)
    if proj and typed is not None:
        pts = g.projection(now, typed)
        over = g.overdue(now)
        if over > 0:
            top = [(a, min(v + over, hi)) for a, v in pts]
            dd = "M" + " L".join(f"{ax.xc(a):.1f} {Y(v):.1f}" for a, v in top) + " L" + " L".join(
                f"{ax.xc(a):.1f} {Y(v):.1f}" for a, v in reversed(pts)) + " Z"
            d.path(dd, GREY, extra='fill-opacity="0.16"')
        if ghost is not None:
            gp = g.projection(now, ghost)
            d.path("M" + " L".join(f"{ax.xc(a):.1f} {Y(v):.1f}" for a, v in gp), stroke=GREY, sw=1, dash="2 4")
        d.path("M" + " L".join(f"{ax.xc(a):.1f} {Y(v):.1f}" for a, v in pts), stroke=GREY, sw=2, dash="6 4")
        ex, ey = ax.xc(now + 4), Y(pts[-1][1])
        d.circle(ex, ey, 3.5, PAPER, GREY, 2)
    if actual and now + 4 <= g.n:
        pts = [(k, g.net(k)) for k in range(now, now + 5)]
        d.path("M" + " L".join(f"{ax.xc(a):.1f} {Y(v):.1f}" for a, v in pts), stroke=INK, sw=1)
    d.circle(ax.xc(now), Y(g.net(now)), 4, BLUE if g.net(now) >= 0 else RED, PAPER, 2)
    if netlabel:
        lab = f"Lager {g.lager[now - 1]}" if g.net(now) >= 0 else f"Restordre {g.rest[now - 1]}"
        yy = Y(g.net(now)) + ls * 0.34
        if proj:
            yy = (Y(g.net(now)) - 12) if g.net(now) >= 0 else (Y(g.net(now)) + ls + 8)
        d.t(fx0 + 6, yy, lab, ls, 600, INK)

    # Panel 2: inn og ut, med kjente ankomster til høyre
    flow_bars(d, ax, yflow, hf, g, wmin, now, fmax, sendt=sendt, x1=fx1_)
    bw = max(ax.slot - 3.5, 2)
    for week, qty in arrs:
        xx = ax.xc(week) - bw / 2
        if qty is None:
            d.rect(xx, yflow + hf - 16, bw, 16, "none", HAIR2, 1, extra='stroke-dasharray="3 3"')
            continue
        is_typed = week == now + 4
        hh = qty * u
        d.rect(xx, yflow + hf - hh, bw, hh, PAPER, INK if is_typed else BLUE, 1.6 if is_typed else 1.2)
        if arrnums:
            d.t(ax.xc(week), yflow + hf - hh - 4, qty, ls, 700 if is_typed else 400, INK, "middle")
    over = g.overdue(now)
    if over > 0 and overduenote:
        if overdue_out:
            d.t(fx1_ + 8, yflow + hf - 4, f"+ {over} forsinket, uten dato", ls, 400, INK2)
        else:
            d.t(fx0 + 6, yflow + ls, f"+ {over} forsinket, uten dato", ls, 400, INK2)

    # Panel 3: egen ordre
    order_bars(d, ax, yord, ho, g.order, wmin, now - 1, omax, x1=fx1_)
    bwo = max(ax.slot - 2.5, 2)
    if typed is None:
        d.rect(ax.xc(now) - bwo / 2, yord + ho - 16, bwo, 16, "none", INK, 1.2, extra='stroke-dasharray="3 3"')
    else:
        d.rect(ax.xc(now) - bwo / 2, yord + ho - typed * u, bwo, typed * u, INK)
        if ordlabel:
            d.t(ax.xc(now), yord + ho - typed * u - 4, typed, ls, 700, INK, "middle")
        if connector:
            d.path(f"M{ax.xc(now) + bwo / 2:.1f} {yord + ho - typed * u + 2:.1f} L{ax.xc(now + 4):.1f} {yflow + hf + 1:.1f}", stroke=INK, sw=1)
            d.t(fx0 + 12 + ax.slot * 0.9, yord + ho - 4, "4 uker", ls, 400, INK2)

    # Panel 4: kostnad per uke, lager i blått og restordre i rødt (P8)
    if cost:
        cu = hc / cmax
        bwc = max(ax.slot - 2.5, 2)
        for k in range(wmin, now + 1):
            lk, rk = g.lagerkost(k), g.restkost(k)
            yb_ = ycost + hc
            if lk:
                d.rect(ax.xc(k) - bwc / 2, yb_ - lk * cu, bwc, lk * cu, BLUE)
                yb_ -= lk * cu
            if rk:
                d.rect(ax.xc(k) - bwc / 2, yb_ - rk * cu, bwc, rk * cu, RED)
        d.line(ax.x0, ycost + hc, fx1_, ycost + hc, HAIR2, 1)
        if costnum:
            uk = g.ukekost(now)
            d.t(ax.xc(now), ycost + hc - uk * cu - 4, nf(uk, 0) if uk == int(uk) else nf(uk, 1), ls, 700, INK, "middle")
        if costsum:
            d.t(fx0 + 6, ycost + hc - 4, f"Sum {nf(g.kostsum(now))} kr", ls, 600, INK)

    # Nå-streken og tidsaksen
    d.line(fx0, y if titles else ynet - 15, fx0, ybot + 4, INK, 1.4)
    if nowlabel:
        d.t(fx0 + 5, y + ls - 2 if titles else ynet - 4, nowlabel, ls, 700, INK)
    if futnote and titles:
        pass
    if axislabel:
        wks = [k for k in range(wmin, now + 5) if (k - now) % xstep == 0]
        xaxis(d, ax, ybot + ls + 4, wks, now, ls)
    if titles:
        if t_net:
            d.t(x, y + ls - 2, t_net, ls, 600, INK)
        if t_flow is None:
            d.rect(x, yflow - 7 - ls + 2, 10, 10, BASE)
            d.t(x + 14, yflow - 7, "Levering", ls, 600, INK)
            xx2 = x + 14 + text_w("Levering", ls) + 14
            d.rect(xx2, yflow - 7 - ls + 2, 10, 10, RED)
            d.t(xx2 + 14, yflow - 7, "Ordre inn utover levering", ls, 600, INK)
        elif t_flow:
            d.t(x, yflow - 7, t_flow, ls, 600, INK)
        if t_ord:
            d.t(x, yord - 7, t_ord, ls, 600, INK)
        if cost and t_cost:
            cost_title(d, x, ycost - 7, g, now, ls, t_cost)
    return {"ax": ax, "ynet": ynet, "yflow": yflow, "yord": yord, "ycost": ycost, "ybot": ybot, "Y": Y, "fx0": fx0, "fx1": fx1_, "ho": ho, "u": u,
            "axisbot": ybot + ls + 6}


def phone(d, x, y, s=1.0):
    """Åpner en telefonflate i 390×844-skala. Husk d.end()."""
    d.rect(x, y, 390 * s, 844 * s, PAPER, HAIR2, 1.4, 36 * s)
    d.g(f"translate({x},{y}) scale({s})")


def game_header(d, wk, kost, role="Grossist", spill="Spill 17", x=20):
    d.t(x, 66, f"Uke {wk}", 30, 700, INK)
    d.t(x, 88, f"{role}, {spill}", 14, 400, INK2)
    d.t(370, 62, "Totalkostnad", 13, 400, INK2, "end")
    d.t(370, 84, f"{nf(kost)} kr", 18, 600, INK, "end")


def facts_row(d, y, items, x=20, width=350):
    """Tre tall i rad: etikett under tall."""
    step = width / len(items)
    for i, (lab, val) in enumerate(items):
        d.t(x + i * step, y, val, 22, 600, INK)
        d.t(x + i * step, y + 20, lab, 13, 400, INK2)


def fmt_sum(a, b):
    return f"{a} + {b}"


# ---------- Runde 3: matrisetrinn ----------
# Divergerende for netto lager: blått over null, rødt under, grå null. Mørke trinn: CVD-avstand 16,2.
POS = ["#C3D8EA", "#84AED3", BLUE]
NEG = ["#EBC3BD", "#D98D84", RED]
ZERO = "#EEF1F4"
# Sekvensiell marine/grå for strømmer (ordre, ordre inn, levering, sendt).
SEQ = [(4, "#E3E8EE"), (8, "#C9D3DE"), (14, "#9EB0C3"), (22, "#536D88"), (10 ** 9, INK)]


def div_cell(v):
    """(fyll, tekstfarge). Tall i cellen har kontrast >= 4,5:1, og fortegnet bærer status, ikke fargen."""
    a = abs(v)
    if a == 0:
        return ZERO, INK
    i = 0 if a <= 10 else (1 if a <= 25 else 2)
    ramp = POS if v > 0 else NEG
    return ramp[i], (PAPER if i == 2 else INK)


def seq_cell(v):
    for lim, col in SEQ:
        if v <= lim:
            return col, (PAPER if col in ("#536D88", INK) else INK)


def kr(v):
    """Kroner uten unødvendige desimaler: 6, 6,5, 13."""
    return nf(v, 0) if v == int(v) else nf(v, 1)


def arrow(d, x, y, direction="right", col=INK2, s=5):
    if direction == "right":
        d.path(f"M{x - s:.1f} {y - s * 0.7:.1f} L{x:.1f} {y:.1f} L{x - s:.1f} {y + s * 0.7:.1f} Z", col)
    else:
        d.path(f"M{x + s:.1f} {y - s * 0.7:.1f} L{x:.1f} {y:.1f} L{x + s:.1f} {y + s * 0.7:.1f} Z", col)


def upstream_of(role):
    i = ROLES.index(role)
    return ROLES[i + 1] if i < 3 else "Produksjon"


def downstream_of(role):
    i = ROLES.index(role)
    return ROLES[i - 1] if i > 0 else "Kundene"


def pipe_cells(g, now, typed):
    """Venstre mot høyre: forsinket uten dato, ordren som tastes nå, så kjente ankomster. Nærmest lageret kommer først."""
    cells = []
    over = g.overdue(now)
    if over > 0:
        cells.append((over, "over", None))
    cells.append((typed, "typed", now + 4))
    for week, qty in reversed(g.arrivals(now, typed)[:3]):
        cells.append((qty, "arr", week))
    return cells


def draw_pipe(d, x, ytop, bh, k, cells, ls=13, nums=True, gapc=2, hl=None):
    xx = x
    for qty, style, week in cells:
        if qty is None:
            d.rect(xx, ytop + 4, 16, bh - 4, PAPER, INK, 1.2, extra='stroke-dasharray="3 3"')
            xx += 16 + gapc
            continue
        wd = max(qty * k, 2)
        if style == "over":
            d.rect(xx, ytop, wd, bh, PAPER, INK3, 1, extra='stroke-dasharray="3 2"')
        elif hl is not None and week == hl:
            d.rect(xx, ytop, wd, bh, "#E3E8EE", INK, 2)
        elif style == "typed" and hl is None:
            d.rect(xx, ytop, wd, bh, PAPER, INK, 1.6)
        else:
            d.rect(xx, ytop, wd, bh, PAPER, BLUE, 1.2)
        if nums and qty and text_w(str(qty), ls) + 2 <= wd:
            d.t(xx + wd / 2, ytop + bh / 2 + ls * 0.34, qty, ls, 700 if style == "typed" else 400, INK, "middle")
        xx += wd + gapc
    return xx - gapc


def pipe_width(cells, k, gapc=2):
    return sum((max(c[0] * k, 2) if c[0] is not None else 16) for c in cells) + gapc * (len(cells) - 1)


def draw_stock(d, x, yc, bh, k, lager, rest, ls=13, nums=True, minw=12):
    """Lager som blå boks over linja, restordre som rød boks under, på samme skala som det som er på vei."""
    wl, wr = lager * k, rest * k
    if lager > 0:
        d.rect(x, yc - bh, wl, bh, BLUEF, BLUE, 1.2)
        if nums and text_w(str(lager), ls) + 4 <= wl:
            d.t(x + wl / 2, yc - bh / 2 + ls * 0.34, lager, ls, 700, INK, "middle")
    else:
        d.rect(x, yc - bh, minw, bh, PAPER, HAIR2, 1, extra='stroke-dasharray="2 2"')
    if rest > 0:
        d.rect(x, yc, wr, bh, REDF, RED, 1.2)
        if nums and text_w(str(rest), ls) + 4 <= wr:
            d.t(x + wr / 2, yc + bh / 2 + ls * 0.34, rest, ls, 700, INK, "middle")
    return max(wl, wr, minw)


def band(d, g, x, y, w, now, typed=None, k=2.5, ls=13, names=True, posisjon=False, sub=True, orders=True, bh=22,
         segmin=58, hl=None):
    """Kjedebåndet for ett Sete: varer går mot høyre, ordrer går mot venstre. Boksene står på sann skala.
    Returnerer geometri og bunn-y."""
    up, down = upstream_of(g.role), downstream_of(g.role)
    y0 = y + (24 if posisjon else 0)
    ynames = y0 + ls - 2
    yval = (ynames + ls + 10) if names else (y0 + ls - 2)
    ytop = yval + 6
    yc = ytop + bh
    yo = yc + bh + 22
    xs = x + 12
    cells = pipe_cells(g, now, typed)
    pw = pipe_width(cells, k)
    lev = g.levering(now)
    seg1 = max(segmin, text_w(f"Levering {lev}", ls) + 14)
    sx = xs + pw + seg1
    lager, rest = g.lager[now - 1], g.rest[now - 1]
    sw = max(lager * k, rest * k, 12)
    se = sx + sw
    # Varestrømmen
    d.line(x, yc, x + w, yc, INK2, 1.2)
    arrow(d, sx - 3, yc, "right", INK2)
    arrow(d, x + w, yc, "right", INK2)
    draw_pipe(d, xs, ytop, bh, k, cells, ls, hl=hl)
    draw_stock(d, sx, yc, bh, k, lager, rest, ls)
    # Etiketter
    if names:
        d.t(x, ynames, f"Fra {up}", ls, 400, INK2)
        d.t(x + w, ynames, f"Til {down}", ls, 400, INK2, "end")
    pv = g.paavei(now)
    pvlab = f"På vei {pv}" + (f" + {typed}" if typed is not None else "")
    d.t(xs, yval, pvlab, ls, 600, INK)
    levlab = f"Levering {lev}"
    levx = max(xs + pw + seg1 / 2, xs + text_w(pvlab, ls) + 12 + text_w(levlab, ls) / 2)
    d.t(levx, yval, levlab, ls, 400, INK, "middle")
    lab = f"Lager {lager}"
    lx_ = max(sx, levx + text_w(levlab, ls) / 2 + 10)
    d.t(lx_, yval, lab, ls, 600, INK)
    sendt = g.sendt(now)
    sxm = max(se + (x + w - se) / 2, lx_ + text_w(lab, ls) + 12 + text_w(f"Sendt {sendt}", ls) / 2)
    d.t(sxm, yval, f"Sendt {sendt}", ls, 400, INK, "middle")
    if rest > 0:
        d.t(se + 6, yc + bh / 2 + ls * 0.34, f"Restordre {rest}", ls, 600, INK)
    if sub:
        d.t(xs, yc + ls + 3, "om lag 4 uker", ls, 400, INK2)
    # Ordrestrømmen går mot venstre
    if orders:
        inn = g.inn(now)
        d.line(se + 6, yo, x + w, yo, INK, 1.2)
        arrow(d, se + 6, yo, "left", INK)
        d.t(x + w, yo - 6, f"Ordre inn {inn}", ls, 600, INK, "end")
        d.line(x, yo, sx - 6, yo, INK, 1.2)
        arrow(d, x, yo, "left", INK)
        d.t(sx - 8, yo - 6, "Din ordre" + (f" {typed}" if typed is not None else ""), ls, 700 if typed is not None else 400,
            INK, "end")
    if posisjon:
        yb = y + 14
        d.path(f"M{xs:.1f} {yb + 8:.1f} L{xs:.1f} {yb:.1f} L{se:.1f} {yb:.1f} L{se:.1f} {yb + 8:.1f}", stroke=GREY, sw=1.2)
        s = f"Posisjon {lager} − {rest} + {pv} = {g.posisjon(now)}"
        if typed is not None:
            s += f". Med {typed}: {g.posisjon(now) + typed}"
        d.t(xs, yb - 5, s, ls, 600, INK)
    bottom = (yo + 6) if orders else (yc + bh + 6)
    return {"yc": yc, "ytop": ytop, "xs": xs, "sx": sx, "se": se, "bottom": bottom, "yo": yo, "pw": pw}


def chain_cells(S, week):
    cells = []
    over = S.pv[week - 1] - sum(S.order(k_) for k_ in (week - 3, week - 2, week - 1))
    if over > 0:
        cells.append((over, "over", None))
    for k_ in (week - 1, week - 2, week - 3):
        cells.append((S.order(k_), "arr", k_ + 4))
    return cells


def chain4(d, x, y, w, week, k=3.0, ls=13, src=None, names=None, lead=86, tail=150, toplabels=True):
    """Hele kjeden ved starten av en Uke: Produksjon, fire ledd og kundene. Samme tegnespråk som setets bånd."""
    src = src or FX["spill17"]
    seats = {r: Seat(r, src) for r in ROLES}
    order = ["Fabrikk", "Distributør", "Grossist", "Detaljist"]
    bh = 22
    yval = y + ls
    ytop = yval + 6
    yc = ytop + bh
    pipes = {r: chain_cells(seats[r], week) for r in order}
    stockw = {r: max(seats[r].lager[week - 1] * k, seats[r].rest[week - 1] * k, 12) for r in order}
    pipew = {r: pipe_width(pipes[r], k) for r in order}
    used = sum(stockw.values()) + sum(pipew.values())
    seg = (w - used - lead - tail) / 8
    d.line(x, yc, x + w, yc, INK2, 1.2)
    d.t(x, yc + ls + 4, "Produksjon", ls, 400, INK2)
    xx = x + lead
    geo = {}
    for r in order:
        S = seats[r]
        xx += seg * 0.5
        draw_pipe(d, xx, ytop, bh, k, pipes[r], ls)
        if toplabels:
            d.t(xx, yval, f"På vei {S.pv[week - 1]}", ls, 400, INK)
        xx += pipew[r] + seg * 0.5
        arrow(d, xx - 3, yc, "right", INK2)
        xx += seg * 0.5
        lag, rest = S.lager[week - 1], S.rest[week - 1]
        draw_stock(d, xx, yc, bh, k, lag, rest, ls)
        geo[r] = (xx, stockw[r])
        nm = (names or NAVN).get(r, "")
        d.t(xx, yc + bh + ls + 8, r, ls, 600, INK)
        d.t(xx, yc + bh + 2 * ls + 12, nm, ls, 400, INK2)
        if rest == 0:
            if toplabels:
                d.t(xx, yval, f"Lager {lag}", ls, 600, INK)
        else:
            d.t(xx + stockw[r] + 4, yc + bh / 2 + 4, f"Restordre {rest}", ls, 600, INK)
            d.t(xx, yval, "Lager 0", ls, 600, INK)
        xx += stockw[r] + seg * 0.5
    arrow(d, x + w, yc, "right", INK2)
    d.t(x + w, yc + ls + 4, "Kundene", ls, 400, INK2, "end")
    return {"yc": yc, "bottom": yc + bh + 2 * ls + 16, "geo": geo}


MLAB = {"net": "Lager over null, restordre under", "inn": "Ordre inn", "lev": "Levering", "sendt": "Sendt",
        "ordre": "Din ordre", "pv": "På vei", "kost": "Kostnad per uke, kr", "sum": "Totalkostnad, kr",
        "pos": "Posisjon"}
MSHORT = {"net": "Netto lager", "inn": "Ordre inn", "lev": "Levering", "sendt": "Sendt", "ordre": "Din ordre",
          "pv": "På vei", "kost": "Kostnad, kr", "sum": "Sum, kr", "pos": "Posisjon"}


def mvalue(g, key, k):
    return {"net": g.net, "inn": g.inn, "lev": g.levering, "sendt": g.sendt, "ordre": g.order, "pv": g.paavei,
            "pos": g.posisjon, "kost": g.ukekost, "sum": g.kostsum}[key](k)


def matrix(d, g, ax, y, now, typed, rows, rh=22, ls=13, wmin=None, label="above", gx=None, future=True, sep=6,
           wto=None):
    """Setets tall i uker som kolonner, på samme tidsakse som meteogrammet. Returnerer bunn-y."""
    wmin = wmin if wmin is not None else ax.wmin
    wto = wto or now
    cw = ax.slot - 2
    yy = y
    fx0, fx1_ = ax.xr(now), ax.xr(min(now + 4, ax.wmax))
    for key in rows:
        if label == "above":
            d.t(gx if gx is not None else ax.x0, yy + ls - 1, MLAB[key], ls, 600, INK2)
            yy += ls + 5
        else:
            d.t(gx, yy + rh / 2 + ls * 0.34, MSHORT[key], ls, 600, INK2)
        if future and wto == now:
            d.rect(fx0, yy - 1, fx1_ - fx0, rh + 2, TINT)
        for k in range(wmin, wto + 1):
            cx = ax.xc(k)
            bold = 700 if k == now else 400
            fill, tc = None, INK
            v = mvalue(g, key, k)
            if key == "net":
                fill, tc = div_cell(v)
                s = sg(v)
            elif key in ("inn", "lev", "sendt", "ordre"):
                if key == "ordre" and k == now and wto == now:
                    v = typed
                if v is None:
                    d.rect(cx - cw / 2, yy + 1, cw, rh - 2, PAPER, INK, 1.2, extra='stroke-dasharray="3 3"')
                    continue
                fill, tc = seq_cell(v)
                s = str(v)
            elif key == "pv":
                s = str(v)
            elif key == "pos":
                s = sg(v)
            elif key == "kost":
                lk, rk = g.lagerkost(k), g.restkost(k)
                fill = POS[0] if lk else (NEG[0] if rk else ZERO)
                s = kr(v)
            else:
                s = kr(v)
                bold = 700 if k == now else 400
            if fill:
                d.rect(cx - cw / 2, yy, cw, rh, fill)
            fs = ls
            while text_w(s, fs) > cw - 2 and fs > 9:
                fs -= 0.5
            d.t(cx, yy + rh / 2 + ls * 0.34, s, fs, bold, tc, "middle")
        if key == "lev" and future and wto == now:
            for week, qty in g.arrivals(now, typed):
                cx = ax.xc(week)
                if qty is None or week > ax.wmax:
                    continue
                d.rect(cx - cw / 2 + 0.6, yy + 0.6, cw - 1.2, rh - 1.2, PAPER, INK if week == now + 4 else BLUE,
                       1.4 if week == now + 4 else 1.1)
                d.t(cx, yy + rh / 2 + ls * 0.34, qty, ls, 700 if week == now + 4 else 400, INK, "middle")
        yy += rh + sep
    return yy


def seg_toggle(d, x, y, opts, active, w=None, h=32, size=14):
    w = w or sum(text_w(o, size) + 34 for o in opts)
    each = w / len(opts)
    d.rect(x, y, w, h, PAPER, HAIR2, 1, 6)
    for i, o in enumerate(opts):
        if i == active:
            d.rect(x + i * each + 2, y + 2, each - 4, h - 4, INK, rx=4)
        d.t(x + i * each + each / 2, y + h / 2 + size * 0.36, o, size, 600, PAPER if i == active else INK, "middle")
    return x + w


def cost_title(d, x, y, g, now, ls, title):
    """Tittellinja i kostnadsfeltet: to arter med faste farger, og ukas tall."""
    lk, rk = g.lagerkost(now), g.restkost(now)
    d.t(x, y, title, ls, 600, INK)
    xx = x + text_w(title, ls) + 12
    for lab, col in (("lager", BLUE), ("restordre", RED)):
        d.rect(xx, y - 10, 10, 10, col)
        d.t(xx + 14, y, lab, ls, 400, INK2)
        xx += 14 + text_w(lab, ls) + 12
