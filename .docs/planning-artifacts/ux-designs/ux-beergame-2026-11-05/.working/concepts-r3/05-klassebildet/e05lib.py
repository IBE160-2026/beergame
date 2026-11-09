"""Felles byggeklosser for konsept 05 Klassebildet (runde 3): SVG-dokument, tekstbryting, skalaer, meteogrammet,
kjedebåndet, kjeden med fire ledd, matrisen, kostnadsbildet og klasseaggregatene.
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
        return f"e05-{self.name}-{kind}{self.n}"

    def t(self, x, y, s, size=14, w=400, fill=INK, a="start", extra=""):
        self.b.append(
            f'<text class="e05-t" x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{w}" '
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
            f".e05-t{{font-family:{FONT};font-variant-numeric:lining-nums tabular-nums;}}"
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



# ================= Runde 3: kjede, matrise, kostnad, klasse =================
LAGERKOST, RESTKOST = 0.50, 1.00

# Matrisetrinn. Kjørt gjennom validate_palette.js --ordinal (hver arm og den marine rampen: PASS).
# Tekstfarge per trinn valgt slik at kontrasten er minst 4,5:1.
R1, R2, R3, R4 = "#DAA09C", "#CB7B75", "#B5423A", "#7E2C25"
B1, B2, B3, B4 = "#95B6D1", "#6B98BF", "#2B6CA3", "#1A4670"
S1, S2, S3, S4, S5 = "#A7B6C5", "#8FA2B5", "#56718D", "#3B5674", "#0F2A47"
NEUTRAL = "#F2F5F8"


def net_cell(v):
    """Netto lager: blå arm over null, rød arm under, nøytral null. Returnerer (fyll, tekstfarge)."""
    if v <= -30:
        return R4, PAPER
    if v <= -15:
        return R3, PAPER
    if v <= -5:
        return R2, INK
    if v <= -1:
        return R1, INK
    if v == 0:
        return NEUTRAL, INK
    if v <= 4:
        return B1, INK
    if v <= 14:
        return B2, INK
    if v <= 29:
        return B3, PAPER
    return B4, PAPER


def flow_cell(v):
    """Strømmer (ordre, levering): marine sekvensiell skala."""
    if v <= 0:
        return NEUTRAL, INK
    if v <= 4:
        return S1, INK
    if v <= 9:
        return S2, INK
    if v <= 14:
        return S3, PAPER
    if v <= 24:
        return S4, PAPER
    return S5, PAPER


def week_cost(net):
    """Kostnad for én Uke fra netto lager: lager × 0,50, restordre × 1,00. Returnerer (lagerkost, restordrekost)."""
    return (net * LAGERKOST, 0.0) if net > 0 else (0.0, -net * RESTKOST)


def kr0(x):
    return nf(x, 0)


def arrow_l(d, x, y, col=INK, s=5):
    """Pilspiss mot venstre, tegnet som form."""
    d.path(f"M{x:.1f} {y:.1f} L{x + s:.1f} {y - s * 0.7:.1f} L{x + s:.1f} {y + s * 0.7:.1f} Z", col)


def arrow_r(d, x, y, col=INK, s=5):
    d.path(f"M{x:.1f} {y:.1f} L{x - s:.1f} {y - s * 0.7:.1f} L{x - s:.1f} {y + s * 0.7:.1f} Z", col)


def halo(extra=""):
    return 'stroke="#FFFFFF" stroke-width="4" paint-order="stroke"' + ((" " + extra) if extra else "")


def stockbox(d, xs, base, ws, net, u, cap, ls=13, label=True, lab=None):
    """Beholdning som boks på sann skala: blått over null, rødt under."""
    d.rect(xs, base - cap * u, ws, 2 * cap * u, "none", HAIR, 1)
    if net > 0:
        hh = min(net, cap) * u
        d.rect(xs, base - hh, ws, hh, BLUEF)
        d.line(xs, base - hh, xs + ws, base - hh, BLUE, 2)
    elif net < 0:
        hh = min(-net, cap) * u
        d.rect(xs, base, ws, hh, REDF)
        d.line(xs, base + hh, xs + ws, base + hh, RED, 2)
    d.line(xs - 3, base, xs + ws + 3, base, INK, 1.2)
    if label:
        if lab is None:
            lab = f"Lager {net}" if net > 0 else (f"Restordre {-net}" if net < 0 else "Lager 0")
        yl = base - min(max(net, 0), cap) * u - 5 if net >= 0 else base + min(-net, cap) * u + ls + 2
        d.t(xs + ws / 2, yl, lab, ls, 700, INK, "middle", halo())


# ---------- Kjedebåndet: setets eget ledd ----------
def chain_seat(d, x, y, w, g, wk, typed, u=1.0, cap=40, show_pos=False, up="Distributør", down="Detaljist", ls=13, slot=38):
    """Ett ledd som flyt, på sann skala (u px per enhet).
    Venstre: røret med fire rom, ett per Uke fram til levering, pluss det som er forsinket uten dato.
    Midten: lageret som boks, blått over null og rødt under. Høyre: sendt videre.
    Ordrene går motsatt vei, som tynn marine linje øverst."""
    top = y
    yline = y + 36
    base = yline + 24 + cap * u
    arrs = g.arrivals(wk, typed)
    over = g.overdue(wk)
    xo = x
    wo = 44
    xp = xo + wo + 6
    gap_ls = 40
    xs = xp + 4 * slot + gap_ls
    ws = 52
    xe = x + w
    d.t(x, top + 12, up, ls - 1, 400, INK3)
    d.t(xe, top + 12, down, ls - 1, 400, INK3, "end")
    d.line(x + 2, yline, xe, yline, INK, 1.2)
    arrow_l(d, x, yline, INK)
    arrow_l(d, xs + ws / 2 + 2, yline, INK)
    d.t(xe, yline - 6, f"Ordre inn {g.inn(wk)}", ls, 600, INK, "end")
    if typed is not None:
        d.t(x + 12, yline - 6, f"Din ordre {typed}", ls, 700, INK)
    else:
        d.t(x + 12, yline - 6, "Din ordre", ls, 400, INK2)
    d.rect(xp - 3, base - cap * u - 2, 4 * slot + 6, cap * u + 2, "none", HAIR2, 1, 3)
    for i, (week, qty) in enumerate(reversed(arrs)):
        cx = xp + i * slot + slot / 2
        is_t = week == wk + 4
        bw = min(slot - 12, 28)
        if qty is None:
            d.rect(cx - bw / 2, base - 16, bw, 16, "none", INK, 1.2, extra='stroke-dasharray="3 3"')
        else:
            hh = min(qty, cap) * u
            d.rect(cx - bw / 2, base - hh, bw, hh, PAPER, INK if is_t else BLUE, 1.6 if is_t else 1.2)
            d.t(cx, base - hh - 4, qty, ls, 700 if is_t else 400, INK, "middle")
        d.t(cx, base + ls + 3, week, ls, 700 if is_t else 400, INK if is_t else INK3, "middle")
    if over > 0:
        cx = xo + wo / 2
        hh = min(over, cap) * u
        d.rect(cx - 13, base - hh, 26, hh, PAPER, GREY, 1.2, extra='stroke-dasharray="3 2"')
        d.t(cx, base - hh - 4, over, ls, 600, INK, "middle")
        d.t(cx, base + ls + 3, "uten dato", ls - 2, 400, INK3, "middle")
    else:
        d.t(xp - 8, base + ls + 3, "Uke", ls, 400, INK3, "end")
    d.line(xp + 4 * slot + 4, base, xs - 3, base, INK2, 1.6)
    arrow_r(d, xs - 1, base, INK2)
    d.line(xs + ws + 3, base, xe - 4, base, INK2, 1.6)
    arrow_r(d, xe, base, INK2)
    gx = (xp + 4 * slot + xs) / 2
    d.t(gx, base - 6, g.levering(wk), ls, 700, INK, "middle")
    d.t(gx, base + ls + 3, "inn", ls - 1, 400, INK3, "middle")
    d.t(xe, base - 6, g.sendt(wk), ls, 700, INK, "end")
    d.t(xe, base + ls + 3, "sendt", ls - 1, 400, INK3, "end")
    stockbox(d, xs, base, ws, g.net(wk), u, cap, ls)
    pv = g.paavei(wk)
    yb = base + 2 * ls + 10
    d.t(xp - 3, yb, f"På vei {pv}" + (f" + {typed}" if typed is not None else ""), ls, 600, INK)
    bottom = max(yb, base + min(max(-g.net(wk), 0), cap) * u + ls + 4)
    if show_pos:
        yq = bottom + 14
        d.line(xp - 3, yq - 9, xs + ws, yq - 9, INK, 1)
        d.line(xp - 3, yq - 13, xp - 3, yq - 9, INK, 1)
        d.line(xs + ws, yq - 13, xs + ws, yq - 9, INK, 1)
        txt = f"Posisjon {g.lager[wk - 1]} − {g.rest[wk - 1]} + {pv} = {g.posisjon(wk)}"
        if typed is not None:
            txt += f". Med {typed}: {g.posisjon(wk) + typed}"
        d.t(xp - 3, yq + 8, txt, ls, 700, INK)
        bottom = yq + 10
    return {"base": base, "bottom": bottom, "xs": xs, "ws": ws, "xp": xp, "slot": slot}


# ---------- Kjeden med fire ledd ----------
CHAIN_ORDER = ["Fabrikk", "Distributør", "Grossist", "Detaljist"]


def chain_full(d, x, y, w, nodes, demand, u=0.9, cap=65, ls=13, flows=None, you="Grossist", pv=None,
               kunde_lab="Kundene", cost=None, names=True, ws=54, stocklabels=None):
    """Hele kjeden: Fabrikk til venstre, kundene til høyre, varene går mot høyre og ordrene mot venstre.
    nodes: {rolle: netto lager}. flows: {rolle: ordre sendt oppstrøms}. pv: {rolle: på vei inn}. cost: {rolle: tekst}."""
    n = len(CHAIN_ORDER)
    kw = 60
    gapw = (w - kw - n * ws) / n
    yname = y + 14
    yline = y + (50 if names else 16)
    base = yline + 24 + cap * u
    xs_ = {r: x + gapw + i * (ws + gapw) for i, r in enumerate(CHAIN_ORDER)}
    xk = x + w - kw
    d.line(x + 4, yline, xk + kw / 2, yline, INK, 1.1)
    arrow_l(d, x, yline, INK, 4.5)
    for i, r in enumerate(CHAIN_ORDER):
        xs = xs_[r]
        cx = xs + ws / 2
        bold = r == you
        if names:
            d.t(cx, yname, r, ls + 1, 700 if bold else 600, INK, "middle")
            d.t(cx, yname + ls + 4, NAVN[r] + (", du" if bold else ""), ls - 1, 400, INK2, "middle")
        if flows is not None:
            xl = xs - gapw / 2
            arrow_l(d, xl - 14, yline, INK, 4.5)
            d.t(xl, yline - 6, flows[r], ls, 700, INK, "middle", halo())
        lab = stocklabels[r] if stocklabels else None
        stockbox(d, xs, base, ws, nodes[r], u, cap, ls, lab=lab)
        prv = xs_[CHAIN_ORDER[i - 1]] + ws if i else x
        d.line(prv + 3, base, xs - 4, base, INK2, 1.4)
        arrow_r(d, xs - 2, base, INK2, 4.5)
        if pv is not None:
            q = pv[r]
            mx = (prv + xs) / 2
            hh = min(q, cap) * u
            d.rect(mx - 9, base - hh, 18, hh, PAPER, BLUE, 1.1)
            d.t(mx, base - hh - 4, q, ls - 1, 400, INK, "middle")
        if cost is not None:
            d.t(cx, base + max(cap * u, 0) + ls + 14, cost[r], ls, 700 if bold else 600, INK, "middle")
    last = xs_[CHAIN_ORDER[-1]] + ws
    d.line(last + 3, base, xk + 8, base, INK2, 1.4)
    arrow_r(d, xk + 10, base, INK2, 4.5)
    d.t(xk + kw / 2 + 4, yname, kunde_lab, ls + 1, 600, INK, "middle")
    d.t(xk + kw / 2 + 4, yline - 6, demand, ls, 700, BLUE, "middle", halo())
    if pv is not None:
        d.t(x + gapw / 2, base + ls + 3, "produksjon", ls - 2, 400, INK3, "middle")
    return {"base": base, "bottom": base + cap * u, "x": xs_, "ws": ws, "yline": yline}


# ---------- Matrisen ----------
def cell_text(v, kind):
    if kind == "cost":
        return nf(v, 0) if v >= 100 or v == int(v) else nf(v, 1)
    if kind == "plain":
        return str(v)
    return sg(v)


def matrix(d, ax, y, rows, wfrom, wto, ch=20, ls=12, label_x=None, gap=1.5, label_size=13, numbers=True, hi_week=None, label_anchor=None):
    """rows: liste av (etikett, verdi(uke), kind). kind: net | flow | cost | plain.
    Cellene står på samme tidsakse som grafen over (ax), så hver Uke har både strek og tall."""
    yy = y
    lx = label_x if label_x is not None else ax.x0 - 8
    anchor = label_anchor or ("end" if label_x is None else "start")
    for lab, fn, kind in rows:
        if lab:
            d.t(lx, yy + ch / 2 + label_size * 0.34, lab, label_size, 400, INK, anchor)
        for k in range(wfrom, wto + 1):
            v = fn(k)
            if v is None:
                continue
            x0 = ax.xl(k) + gap / 2
            cw = ax.slot - gap
            if kind == "net":
                f, tc = net_cell(v)
            elif kind == "flow":
                f, tc = flow_cell(v)
            elif kind == "cost":
                lk, rk = v
                f, tc = (REDF if rk > 0 else (BLUEF if lk > 0 else NEUTRAL)), INK
                v = lk + rk
            else:
                f, tc = NEUTRAL, INK
            d.rect(x0, yy + gap / 2, cw, ch - gap, f)
            if numbers:
                d.t(ax.xc(k), yy + ch / 2 + ls * 0.36, cell_text(v, kind), ls, 700 if k == hi_week else 400, tc, "middle")
        yy += ch
    if hi_week is not None:
        d.rect(ax.xl(hi_week), y - 1, ax.slot, yy - y + 2, "none", INK, 1.6)
    return yy


def net_legend(d, x, y, sw=22, ls=12, labels=True):
    steps = [(-30, "≤ −30"), (-15, ""), (-5, ""), (-1, ""), (0, "0"), (1, ""), (5, ""), (15, ""), (30, "≥ 30")]
    for i, (v, lab) in enumerate(steps):
        f, _ = net_cell(v)
        d.rect(x + i * sw, y, sw - 1.5, 11, f)
        if labels and lab:
            d.t(x + i * sw + sw / 2, y + 25, lab, ls, 400, INK3, "middle")
    return x + len(steps) * sw


# ---------- Kostnad ----------
def cost_bars(d, ax, y, h, fn, wfrom, wto, scale, x1=None):
    """Kostnad per Uke på sann skala: restordrekost (rød) nederst, lagerkost (blå) over. fn(uke) -> (lager, rest)."""
    u = h / scale
    bw = max(ax.slot - 2.5, 1.5)
    base = y + h
    for k in range(wfrom, wto + 1):
        lk, rk = fn(k)
        x = ax.xc(k) - bw / 2
        if rk > 0:
            d.rect(x, base - rk * u, bw, rk * u, RED)
        if lk > 0:
            off = 1 if rk > 0 else 0
            d.rect(x, base - rk * u - lk * u - off, bw, lk * u, BLUE)
    d.line(ax.x0, base, x1 or ax.x1, base, HAIR2, 1)
    return u


def split_bar(d, x, y, w, h, lk, rk, scale):
    """Liggende stablet stolpe: restordrekost først, så lagerkost. Sann skala (scale kr = w px)."""
    wr = rk / scale * w
    wl = lk / scale * w
    d.rect(x, y, wr, h, RED)
    d.rect(x + wr + (1 if rk and lk else 0), y, wl, h, BLUE)
    return x + wr + wl


# ---------- Klassen ----------
KL = FX["klasse"]
SPILL = KL["spill"]
FERDIGE = [s for s in SPILL if s["status"] == "ferdig"]


def median(xs):
    xs = sorted(xs)
    n = len(xs)
    if not n:
        return None
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def quart(xs):
    xs = sorted(xs)
    n = len(xs)

    def q(p):
        i = (n - 1) * p
        lo = int(i)
        hi = min(lo + 1, n - 1)
        return xs[lo] + (xs[hi] - xs[lo]) * (i - lo)
    return q(0.25), q(0.5), q(0.75)


def class_net(role, week, games=None):
    games = FERDIGE if games is None else games
    return [s["netto_lager"][role][week - 1] for s in games if len(s["netto_lager"][role]) >= week]


def class_median_net(role, week, games=None):
    return median(class_net(role, week, games))


def class_quart_net(role, week, games=None):
    return quart(class_net(role, week, games))


def class_median_order(role, week, games=None):
    games = FERDIGE if games is None else games
    return median([s["ordre"][role][week - 1] for s in games if len(s["ordre"][role]) >= week])


def game_week_cost(s, week, roles=None):
    lk = rk = 0.0
    for r in roles or ROLES:
        a, b = week_cost(s["netto_lager"][r][week - 1])
        lk += a
        rk += b
    return lk, rk


def class_week_cost(week, games=None, roles=None):
    """Summen for alle spill som har nådd uka: (lagerkost, restordrekost)."""
    lk = rk = 0.0
    for s in (SPILL if games is None else games):
        if s["uke"] >= week:
            a, b = game_week_cost(s, week, roles)
            lk += a
            rk += b
    return lk, rk


def game_cost_split(s, roles=None):
    lk = rk = 0.0
    for k in range(1, s["uke"] + 1):
        a, b = game_week_cost(s, k, roles)
        lk += a
        rk += b
    return lk, rk


def seat_week_cost(g, week):
    return g.lager[week - 1] * LAGERKOST, g.rest[week - 1] * RESTKOST


def series_split(src, role):
    s = src["serier"][role]
    return sum(s["lager"]) * LAGERKOST, sum(s["restordre"]) * RESTKOST


def first_onset(vals, thr=10):
    return next((k + 1 for k, v in enumerate(vals) if v >= thr), None)


# ---------- Kontroll: tall, grafer og kostnad må stemme med loggen ----------
def _check():
    S = FX["spill17"]
    tot = 0.0
    for r in ROLES:
        s = S["serier"][r]
        acc = 0.0
        for i in range(36):
            lk, rk = s["lager"][i] * LAGERKOST, s["restordre"][i] * RESTKOST
            acc += lk + rk
            assert abs(acc - s["kost_sum"][i]) < 1e-9, (r, i)
            assert s["lager"][i] == 0 or s["restordre"][i] == 0, (r, i)
            if i:
                net = s["lager"][i] - s["restordre"][i]
                prev = s["lager"][i - 1] - s["restordre"][i - 1]
                assert net == prev + s["levering"][i] - s["innkommende_ordre"][i], (r, i)
        assert abs(acc - S["kost_per_rolle"][r]) < 1e-9, r
        tot += acc
    assert abs(tot - S["kjedekost"]) < 1e-9
    for key in ("bare_sara_teller_paa_vei", "alle_teller_paa_vei"):
        src = FX[key]
        assert abs(sum(sum(series_split(src, r)) for r in ROLES) - src["kjedekost"]) < 1e-9, key
    for s in SPILL:
        for r in ROLES:
            assert len(s["netto_lager"][r]) == s["uke"] == len(s["ordre"][r])
        lk, rk = game_cost_split(s)
        assert abs(lk + rk - s["kjedekost"]) <= 0.5, s["spill"]
        if s["status"] == "ferdig":
            for r in ROLES:
                a, b = game_cost_split(s, [r])
                assert abs(a + b - s["kost_per_rolle"][r]) < 1e-9
    s17 = next(s for s in SPILL if s["spill"] == 17)
    for r in ROLES:
        g = S["serier"][r]
        assert s17["netto_lager"][r] == [g["lager"][i] - g["restordre"][i] for i in range(s17["uke"])], r
        assert s17["ordre"][r] == g["ordre"][:s17["uke"]], r
    F = KL["ferdige"]
    assert len(FERDIGE) == F["antall"]
    ks = sorted(s["kjedekost"] for s in FERDIGE)
    assert ks[0] == F["kjedekost"]["min"] and ks[-1] == F["kjedekost"]["max"]
    assert median(ks) == F["kjedekost"]["median"]
    for r in ROLES:
        fs = sorted(s["forsterkning"][r] for s in FERDIGE)
        assert abs(median(fs) - F["forsterkning_per_rolle"][r]["median"]) < 1e-9, r


_check()
