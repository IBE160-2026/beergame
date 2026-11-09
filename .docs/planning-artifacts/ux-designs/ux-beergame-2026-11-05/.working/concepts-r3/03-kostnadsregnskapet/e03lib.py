"""Felles byggeklosser for konsept 03 Kostnadsregnskapet: SVG-dokument, tekstbryting, skalaer og selve meteogrammet.
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
        return f"e03-{self.name}-{kind}{self.n}"

    def t(self, x, y, s, size=14, w=400, fill=INK, a="start", extra=""):
        self.b.append(
            f'<text class="e03-t" x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{w}" '
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
            f".e03-t{{font-family:{FONT};font-variant-numeric:lining-nums tabular-nums;}}"
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
          arrnums=True, ordlabel=True, wmax=None, overduenote=True, projlabel=True, overdue_out=False):
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
    ybot = yord + ho
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
    return {"ax": ax, "ynet": ynet, "yflow": yflow, "yord": yord, "ybot": ybot, "Y": Y, "fx0": fx0, "fx1": fx1_, "ho": ho, "u": u,
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
