"""Felles byggeklosser for konsept 04 Graf over tabell: SVG-dokument, tekstbryting, skalaer,
matrisetrinn, kjedebånd og selve grafen-over-tabellen. Alle tall kommer fra ../_shared/fixture.json."""
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
        return f"e04-{self.name}-{kind}{self.n}"

    def t(self, x, y, s, size=14, w=400, fill=INK, a="start", extra=""):
        self.b.append(
            f'<text class="e04-t" x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{w}" '
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
            f".e04-t{{font-family:{FONT};font-variant-numeric:lining-nums tabular-nums;}}"
        )
        out = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.W} {self.H}" font-family="{FONT}">'
            f"<title>{escape(self.title)}</title><desc>{escape(self.desc)}</desc><style>{css}</style>"
            f'<rect x="0" y="0" width="{self.W}" height="{self.H}" fill="{PAPER}"/>' + "".join(self.b) + "</svg>"
        )
        (HERE / f"{self.name}.svg").write_text(out, encoding="utf-8")




# ---------- Matrisetrinn ----------
# Kjørt gjennom dataviz-skillens validate_palette.js --ordinal: monoton lyshet, synlige trinn,
# lyseste trinn ≥ 2:1 mot hvit. Tall i cellene: marine på de to lyse trinnene, hvit på de to mørke.
RED_STEPS = ["#E1A098", "#CF776D", "#B5423A", "#8C2C25"]
BLUE_STEPS = ["#93B8DB", "#6A9AC8", "#2B6CA3", "#1B4A75"]
SEQ_STEPS = ["#A7B6C6", "#8396AC", "#56708B", "#0F2A47"]
NEUTRAL = "#F2F5F8"
NET_BINS = (10, 20, 35)      # |netto lager| 1–9, 10–19, 20–34, 35+
SEQ_BINS = (5, 10, 20, 30)   # ordre under 5 er uten fyll


def _lum(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    c = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contrast(a, b):
    la, lb = sorted([_lum(a), _lum(b)], reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _step(a, bins):
    for i, b in enumerate(bins):
        if a < b:
            return i
    return len(bins)


def net_cell(v):
    """(fyll, tekstfarge) for netto lager. Blå over null, rød under, grå null."""
    if v == 0:
        return NEUTRAL, INK
    steps = BLUE_STEPS if v > 0 else RED_STEPS
    i = _step(abs(v), NET_BINS)
    return steps[i], (INK if i < 2 else PAPER)


def seq_cell(v):
    """(fyll, tekstfarge) for strømmer (ordre). Under 5: uten fyll."""
    if v < SEQ_BINS[0]:
        return None, INK
    i = _step(v, SEQ_BINS[1:])
    return SEQ_STEPS[i], (INK if i < 2 else PAPER)


for _steps in (RED_STEPS, BLUE_STEPS, SEQ_STEPS):
    for _i, _c in enumerate(_steps):
        _txt = INK if _i < 2 else PAPER
        assert contrast(_c, _txt) >= 4.5, (_c, contrast(_c, _txt))
assert contrast(NEUTRAL, INK) >= 4.5


def fmt_k(v):
    """Kroner i smale celler: 13 eller 6,5."""
    if abs(v - round(v)) < 1e-9:
        return sg(round(v))
    return (("−" if v < 0 else "") + f"{abs(v):.1f}").replace(".", ",")


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
        return self.kost[w - 1] if w >= 1 else 0.0

    def lagerkost(self, w):
        return self.lager[w - 1] * 0.5

    def restkost(self, w):
        return self.rest[w - 1] * 1.0

    def ukekost(self, w):
        return self.kostsum(w) - self.kostsum(w - 1)

    def sum_lk(self, upto=None):
        return sum(self.lagerkost(k) for k in range(1, (upto or self.n) + 1))

    def sum_rk(self, upto=None):
        return sum(self.restkost(k) for k in range(1, (upto or self.n) + 1))

    def arrivals(self, w, typed):
        """Kjente ankomster de neste fire ukene. Siste plass er ordren som tastes nå."""
        out = [(w + j, self.order(w + j - 4)) for j in (1, 2, 3)]
        out.append((w + 4, typed))
        return out

    def overdue(self, w):
        """Bestilt, men over fire uker gammelt: ligger hos leverandøren uten kjent dato."""
        return self.paavei(w) - sum(self.order(k) for k in (w - 3, w - 2, w - 1))

    def projection(self, w, typed):
        rate = self.inn(w)
        net = self.net(w)
        pts = [(w, net)]
        for week, qty in self.arrivals(w, typed):
            net += (qty or 0) - rate
            pts.append((week, net))
        return pts


def check_source(src, label):
    """Bygget stopper hvis regnestykket i tabellene ikke stemmer med loggen."""
    tot = 0.0
    for r in ROLES:
        g = Seat(r, src)
        for w in range(1, g.n + 1):
            assert abs(g.ukekost(w) - (g.lagerkost(w) + g.restkost(w))) < 1e-9, (label, r, w)
            assert g.lager[w - 1] == 0 or g.rest[w - 1] == 0, (label, r, w)
            if w > 1:
                assert g.net(w) == g.net(w - 1) + g.levering(w) - g.inn(w), (label, r, w)
                assert g.lager[w - 1] == g.lager[w - 2] + g.levering(w) - g.sendt(w), (label, r, w)
        assert abs(g.sum_lk() + g.sum_rk() - src["kost_per_rolle"][r]) < 1e-9, (label, r)
        assert abs(g.kostsum(g.n) - src["kost_per_rolle"][r]) < 1e-9, (label, r)
        tot += src["kost_per_rolle"][r]
    assert abs(tot - src["kjedekost"]) < 1e-9, label


for _k in ("spill17", "bare_sara_teller_paa_vei", "alle_teller_paa_vei", "replay_sara"):
    check_source(FX[_k], _k)

G = Seat()
SEATS = {r: Seat(r) for r in ROLES}
BARE = Seat("Grossist", FX["bare_sara_teller_paa_vei"])
ALLE = Seat("Grossist", FX["alle_teller_paa_vei"])
RE = Seat("Grossist", FX["replay_sara"])
K = FX["spill17"]
KL = FX["klasse"]
DEM = K["serier"]["demand"]

# Saras skjerm i Uke 11, slik briefen sier den
assert (G.lager[10], G.rest[10], G.inn(11), G.levering(11), G.sendt(11), G.paavei(11), G.order(8)) == (0, 13, 8, 4, 4, 16, 4)
assert G.kostsum(11) == 68.0 and G.posisjon(11) == 3
assert G.ordre[:10] == [4] * 9 + [8]
assert G.projection(11, 24)[-1] == (15, -5)

# Klassespillene: kjedekost må stemme med netto lager uke for uke
for _sp in KL["spill"]:
    _c = sum(v * 0.5 if v > 0 else -v for r in ROLES for v in _sp["netto_lager"][r])
    assert abs(_c - _sp["kjedekost"]) < 0.51, _sp["spill"]


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


def pts_path(pts):
    return "M" + " L".join(f"{a:.1f} {b:.1f}" for a, b in pts)


def net_area(d, ax, y0, h, vals, wfrom, wto, lo=-40, hi=30, lw=2, fills=True):
    """Netto lager: blått over null, rødt under. vals(w) gir verdien."""
    Y = yscale(y0, h, lo, hi)
    pts = [(ax.xc(w), Y(vals(w))) for w in range(wfrom, wto + 1)]
    line = pts_path(pts)
    area = line + f" L{pts[-1][0]:.1f} {Y(0):.1f} L{pts[0][0]:.1f} {Y(0):.1f} Z"
    up = d.cliprect(ax.x0 - 4, y0 - 4, ax.w + 8, Y(0) - y0 + 4)
    dn = d.cliprect(ax.x0 - 4, Y(0), ax.w + 8, y0 + h - Y(0) + 4)
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


def grid(d, ax, y0, h, lo, hi, ticks, size=13, labels=True, x1=None, lx=None):
    Y = yscale(y0, h, lo, hi)
    x1 = x1 or ax.x1
    for v in ticks:
        d.line(ax.x0, Y(v), x1, Y(v), HAIR2 if v == 0 else HAIR, 1)
        if labels:
            d.t((lx if lx is not None else ax.x0 - 5), Y(v) + size * 0.34, sg(v), size, 400, INK3, "end")
    return Y


def cost_bars(d, ax, y0, h, parts, wfrom, wto, cmax=40, x1=None, gap=2.5):
    """Kost per uke som stolpe: lagerkost (blå) nederst, restordrekost (rød) over, luft mellom."""
    u = h / cmax
    bw = max(ax.slot - gap, 1.5)
    base = y0 + h
    for w in range(wfrom, wto + 1):
        lk, rk = parts(w)
        x = ax.xc(w) - bw / 2
        yy = base
        if lk > 0:
            d.rect(x, yy - lk * u, bw, lk * u, BLUE)
            yy -= lk * u + (1.5 if rk > 0 else 0)
        if rk > 0:
            d.rect(x, yy - rk * u, bw, rk * u, RED)
    d.line(ax.x0, base, x1 or ax.x1, base, HAIR2, 1)


def chip(d, x, y, col, label, size=13, w=600, fill=INK):
    """Liten fargeprøve + tekst. Returnerer x etter teksten."""
    d.rect(x, y - size * 0.72, size * 0.72, size * 0.72, col)
    d.t(x + size * 0.72 + 5, y, label, size, w, fill)
    return x + size * 0.72 + 5 + text_w(label, size) + 12


def xaxis(d, ax, y, weeks, now=None, size=13):
    for w in weeks:
        bold = w == now
        d.t(ax.xc(w), y, w, size, 700 if bold else 400, INK if bold else INK3, "middle")


ROWLAB = {"uke": "Uke", "inn": "Ordre inn", "lev": "Levering", "net": "Netto lager", "pv": "På vei", "sendt": "Sendt",
          "ord": "Din ordre", "kost": "Kost, kr", "lk": "Lagerkost", "rk": "Restordrekost", "sum": "Sum, kr",
          "pos": "Posisjon", "lager": "Lager", "rest": "Restordre"}


def gtable(d, g, x, y, w, now, typed=None, wmin=None, wmax=None, lw=74, ls=13, rh=20, hn=84, hc=30,
           rows=("inn", "lev", "net", "ord", "kost"), labels=None, cmax=40, lo=-40, hi=30, ticks=(-40, -20, 0, 20),
           proj=False, connector=True, titles=True, nowlabel="Nå", netlabel=True, cost_field=True, actual=False,
           uke_every=1, gapf=8, futnote=None, hlcol=None, t_net="Lager over null, restordre under", ord_label="Din ordre",
           cost_title=True, vs=None, cost_tick=True):
    """Grafen over tabellen. Felles tidsakse: hver uke er en kolonne med både strek og tall.
    Høyre kant er nå + 4, aldri slutten av spillet."""
    wmin = wmin if wmin is not None else max(1, now - 7)
    wmax = wmax if wmax is not None else now + 4
    ax = Axis(x + lw, w - lw, wmin, wmax)
    th = ls + 9 if titles else 0
    ynet = y + th
    ycost = ynet + hn + gapf + th + (10 if titles and cost_tick else 0)
    ytab = (ycost + hc + 4) if cost_field else (ynet + hn + 4)
    allrows = ["uke"] + list(rows)
    ybot = ytab + len(allrows) * rh
    horizon = min(now + 4, wmax)          # høyre kant: nå + 4, aldri slutten
    fx0, fx1 = ax.xr(min(now, wmax)), ax.xr(horizon)
    labels = dict(ROWLAB, **(labels or {}))
    labels["ord"] = ord_label
    if wmax > now:
        d.rect(fx0, y - 2, fx1 - fx0, ybot - y + 2, TINT)
    vs = vs or ls

    # Felt 1: netto lager
    Y = grid(d, ax, ynet, hn, lo, hi, ticks, ls, x1=fx1)
    net_area(d, ax, ynet, hn, g.net, wmin, min(now, g.n), lo, hi)
    if proj and typed is not None:
        pts = g.projection(now, typed)
        d.path(pts_path([(ax.xc(a), Y(v)) for a, v in pts]), stroke=GREY, sw=2, dash="6 4")
        d.circle(ax.xc(now + 4), Y(pts[-1][1]), 3.5, PAPER, GREY, 2)
    if actual and now + 4 <= g.n:
        d.path(pts_path([(ax.xc(k), Y(g.net(k))) for k in range(now, now + 5)]), stroke=INK, sw=1)
    if now <= g.n:
        d.circle(ax.xc(now), Y(g.net(now)), 4, BLUE if g.net(now) >= 0 else RED, PAPER, 2)
    if netlabel and wmax > now:
        lab = f"Lager {g.lager[now - 1]}" if g.net(now) >= 0 else f"Restordre {g.rest[now - 1]}"
        d.t(fx0 + 6, Y(g.net(now)) + ls * 0.34, lab, ls, 600, INK)
    if titles and t_net:
        d.t(x, y + ls - 1, t_net, ls, 600, INK)

    # Felt 2: kost per uke
    if cost_field:
        cost_bars(d, ax, ycost, hc, lambda k: (g.lagerkost(k), g.restkost(k)), wmin, min(now, g.n), cmax, x1=fx1)
        if titles and cost_title:
            xx = x
            d.t(xx, ycost - 8, "Kost per uke", ls, 600, INK)
            xx += text_w("Kost per uke", ls) + 14
            xx = chip(d, xx, ycost - 8, RED, "restordre 1,00", ls, 400, INK2)
            chip(d, xx, ycost - 8, BLUE, "lager 0,50", ls, 400, INK2)
        if cost_tick:
            d.line(ax.x0, ycost, fx1, ycost, HAIR, 1)
            d.t(ax.x0 - 5, ycost + ls * 0.34, f"{cmax} kr", ls, 400, INK3, "end")

    # Tabellen
    rowy = {}
    for i, key in enumerate(allrows):
        ry = ytab + i * rh
        rowy[key] = ry
        base = ry + rh / 2 + vs * 0.36
        lab = labels.get(key, key)
        d.t(x, base, lab, ls, 600 if key == "uke" else 400, INK if key != "uke" else INK2)
        if key != "uke":
            d.line(x, ry, fx1, ry, HAIR, 1)
        for k in range(wmin, wmax + 1):
            cx = ax.xc(k)
            past = k <= min(now, g.n)
            if key == "uke":
                if k <= horizon and ((k - wmin) % uke_every == 0 or k == now):
                    d.t(cx, base, k, vs, 700 if k == now else 400, INK if k == now else INK3, "middle")
                continue
            val = None
            fill, col = None, INK
            if key == "net" and past:
                v = g.net(k)
                fill, col = net_cell(v)
                val = sg(v)
            elif key == "inn" and past:
                val = g.inn(k)
            elif key == "lev" and past:
                val = g.levering(k)
            elif key == "pv" and past:
                val = g.paavei(k)
            elif key == "sendt" and past:
                val = g.sendt(k)
            elif key == "lager" and past:
                val = g.lager[k - 1]
            elif key == "rest" and past:
                val = g.rest[k - 1]
            elif key == "ord":
                if k < now or (k == now and now > g.n):
                    val = g.order(k)
            elif key == "kost" and past:
                val = fmt_k(g.ukekost(k))
            elif key == "lk" and past:
                val = fmt_k(g.lagerkost(k))
            elif key == "rk" and past:
                val = fmt_k(g.restkost(k))
            elif key == "sum" and past:
                val = sg(int(g.kostsum(k) + 0.5))
            elif key == "pos" and past:
                val = sg(g.posisjon(k))
            if fill:
                d.rect(ax.xl(k) + 0.75, ry + 1.5, ax.slot - 1.5, rh - 3, fill)
            if val is not None:
                fs = vs
                while text_w(str(val), fs) > ax.slot - 3 and fs > 9:
                    fs -= 0.5
                d.t(cx, base, val, fs, 400, col, "middle")
        # ankomster og ordren som tastes
        if key == "lev" and now < wmax:
            for week, qty in g.arrivals(now, typed):
                if week > wmax:
                    continue
                cx = ax.xc(week)
                bx, bw = ax.xl(week) + 1.5, ax.slot - 3
                if qty is None:
                    d.rect(bx, ry + 2, bw, rh - 4, "none", HAIR2, 1, 2, 'stroke-dasharray="3 2"')
                    continue
                is_typed = week == now + 4
                d.rect(bx, ry + 2, bw, rh - 4, PAPER, INK if is_typed else BLUE, 1.5 if is_typed else 1, 2)
                d.t(cx, base, qty, vs, 700 if is_typed else 400, INK, "middle")
        if key == "ord" and now <= g.n and now <= wmax:
            bx, bw = ax.xl(now) + 1, ax.slot - 2
            if typed is None:
                d.rect(bx, ry + 2, bw, rh - 4, PAPER, INK, 1.2, 2, 'stroke-dasharray="3 2"')
            else:
                d.rect(bx, ry + 2, bw, rh - 4, INK, None, 1, 2)
                d.t(ax.xc(now), base, typed, vs, 700, PAPER, "middle")
    d.line(x, ybot, fx1, ybot, HAIR, 1)

    # Ordren tegnet to ganger: beslutning og ankomst, med en tynn linje mellom
    if connector and typed is not None and "ord" in rowy and "lev" in rowy and now + 4 <= wmax:
        x1_, y1_ = ax.xr(now) - 1, rowy["ord"] + rh / 2
        x2_, y2_ = ax.xl(now + 4) + 1.5, rowy["lev"] + rh / 2
        d.path(f"M{x1_:.1f} {y1_:.1f} L{x2_:.1f} {y2_:.1f}", stroke=INK, sw=1)

    if hlcol is not None:
        top = rowy.get("inn", ytab)
        bot = rowy.get("net", ytab) + rh
        d.rect(ax.xl(hlcol), top + 0.5, ax.slot, bot - top - 1, "none", INK, 1.4, 2)

    # Nå-streken går gjennom graf og tabell
    if now <= wmax:
        d.line(fx0, y - 2, fx0, ybot, INK, 1.4)
        if nowlabel:
            d.t(fx0 + 5, y + ls - 1, nowlabel, ls, 700, INK)
    if futnote and wmax > now:
        wid = fx1 - fx0 - 10
        lines_ = wrap(futnote, wid, ls)
        yy = ynet + hn - 4 - 16 * (len(lines_) - 1)
        for ln in lines_:
            d.t(fx0 + 6, yy, ln, ls, 400, INK2)
            yy += 16
    return {"ax": ax, "ynet": ynet, "ycost": ycost, "ytab": ytab, "ybot": ybot, "Y": Y, "fx0": fx0, "fx1": fx1,
            "rowy": rowy, "rh": rh}


def arrow(d, x1, y, x2, col=INK, sw=1.2, head=6):
    """Rett pil fra x1 til x2 på samme høyde, spiss ved x2."""
    s = 1 if x2 > x1 else -1
    d.line(x1, y, x2 - s * head * 0.6, y, col, sw)
    d.path(f"M{x2:.1f} {y:.1f} L{x2 - s * head:.1f} {y - head * 0.6:.1f} L{x2 - s * head:.1f} {y + head * 0.6:.1f} Z", col)


def chain_seat(d, g, x, y, w, wk, typed=None, ls=13, up="Distributør", down="Detaljist", un=0.82, upipe=1.6):
    """Setets eget ledd: varer inn fra venstre, ut til høyre, ordre den andre veien.
    Beholdningen er en boks på sann skala: lager opp, restordre ned, samme fortegn som grafen."""
    xn = x + w * 0.56
    nw = 40
    nl, nr = xn - nw / 2, xn + nw / 2
    yo = y + 22          # ordrelinja (informasjon), mot venstre
    yg = y + 50          # varelinja, mot høyre
    d.t(x, y + 12, up, ls, 400, INK3)
    d.t(x + w, y + 12, down, ls, 400, INK3, "end")
    lab_o = f"Din ordre {typed}" if typed is not None else "Din ordre"
    d.t(nl - 8, y + 12, lab_o, ls, 600, INK, "end")
    d.t(nr + 8, y + 12, f"Ordre inn {g.inn(wk)}", ls, 600, INK)
    arrow(d, x + w, yo, nr + 1, INK, 1.1, 5)
    if typed is not None:
        arrow(d, nl - 1, yo, x, INK, 1.1, 5)
    else:
        d.line(nl - 1, yo, x, yo, HAIR2, 1, "3 3")
    lag, rest = g.lager[wk - 1], g.rest[wk - 1]
    d.rect(nl, yo, nw, 62, PAPER, HAIR2, 1)
    if lag:
        d.rect(nl + 3, yg - lag * un, nw - 6, lag * un, BLUE)
    if rest:
        d.rect(nl + 3, yg, nw - 6, rest * un, RED)
    d.line(nl, yg, nr, yg, HAIR2, 1)
    pend = nl - 40
    d.line(x, yg, pend, yg, ORD, 2)
    arrow(d, pend, yg, nl - 1, ORD, 2, 6)
    arrow(d, nr + 1, yg, x + w, ORD, 2, 6)
    d.t(nl - 6, yg - 9, f"Levering {g.levering(wk)}", ls, 400, INK, "end")
    d.t(nr + 8, yg - 9, f"Sendt {g.sendt(wk)}", ls, 400, INK)
    items = [(q, wkk == wk + 4) for wkk, q in g.arrivals(wk, typed) if q is not None]
    over = g.overdue(wk)
    total = sum(q for q, _ in items) + max(over, 0)
    avail = pend - x - 8 - 4 * (len(items) + 1)
    u = min(upipe, avail / max(total, 1))
    bx = pend - 6
    for q, is_typed in items:
        bw = q * u
        bx -= bw
        d.rect(bx, yg - 6, bw, 12, PAPER, INK if is_typed else BLUE, 1.5 if is_typed else 1)
        bx -= 4
    if over > 0:
        bw = over * u
        bx -= bw
        d.rect(bx, yg - 6, bw, 12, TINT, HAIR2, 1, extra='stroke-dasharray="3 2"')
    pv = g.paavei(wk)
    pvl = f"På vei {pv}" + (f" + {typed}" if typed is not None else "")
    d.t(x, yg + 26, pvl, ls, 600, INK)
    if over > 0:
        d.t(x, yg + 26 + ls + 4, f"herav {over} forsinket, uten dato", ls, 400, INK2)
    st = f"Lager {lag}" if rest == 0 else f"Restordre {rest}"
    d.t(nr + 8, yg + 26, st, ls, 700, INK)
    return max(yo + 62, yg + 30 + (ls + 4 if over > 0 else 0))


def chain_full(d, seats, x, y, w, wk, ls=14, un=0.62, upipe=0.9, cost=True, you="Grossist", demand=True,
               names=True, order_row=True):
    """Hele kjeden med fire ledd og kundene. Varer går mot høyre, ordre mot venstre.
    Beholdning som boks på sann skala, det som er på vei som stolpe på røret."""
    order = ["Fabrikk", "Distributør", "Grossist", "Detaljist"]
    lo = max(max(seats[r].rest) for r in order)
    hi = max(max(seats[r].lager) for r in order)
    nw = 46
    span = w - 70
    xs = [x + 40 + span * (i + 0.5) / 4.15 for i in range(4)]
    yo = y + 6
    yg = yo + 4 + hi * un
    ybox_b = yg + lo * un + 4
    xk = x + w - 30
    for i, r in enumerate(order):
        S = seats[r]
        xn = xs[i]
        nl, nr = xn - nw / 2, xn + nw / 2
        d.rect(nl, yo, nw, ybox_b - yo, PAPER, INK if r == you else HAIR2, 1.4 if r == you else 1)
        lag, rest = S.lager[wk - 1], S.rest[wk - 1]
        if lag:
            d.rect(nl + 3, yg - lag * un, nw - 6, lag * un, BLUE)
        if rest:
            d.rect(nl + 3, yg, nw - 6, rest * un, RED)
        d.line(nl, yg, nr, yg, HAIR2, 1)
        nx = xs[i + 1] - nw / 2 if i < 3 else xk - 26
        arrow(d, nr + 1, yg, nx - 1, ORD, 2, 6)
        if i < 3:
            pv = seats[order[i + 1]].paavei(wk)
            pw = min(pv * upipe, nx - nr - 26)
            mid = (nr + nx) / 2
            d.rect(mid - pw / 2, yg - 6, pw, 12, PAPER, BLUE, 1)
            d.t(mid, yg - 12, f"På vei {pv}", ls - 1, 400, INK2, "middle")
        yt = ybox_b + ls + 8
        d.t(xn, yt, r, ls, 700 if r == you else 600, INK, "middle")
        if names:
            d.t(xn, yt + ls + 4, NAVN[r] + (", du" if r == you else ""), ls - 1, 400, INK2, "middle")
        st = f"Lager {lag}" if rest == 0 else f"Restordre {rest}"
        d.t(xn, yt + 2 * ls + 10, st, ls - 1, 600, INK, "middle")
        if cost:
            d.t(xn, yt + 3 * ls + 14, f"{nf(S.kostsum(wk))} kr", ls - 1, 400, INK2, "middle")
    arrow(d, x, yg, xs[0] - nw / 2 - 1, ORD, 2, 6)
    d.t(x, yg - 10, "Produksjon", ls - 1, 400, INK3)
    if demand:
        d.t(xk, yg - 10, "Kundene", ls - 1, 600, INK, "middle")
        d.t(xk, yg + 22, DEM[wk - 1], ls, 700, BLUE, "middle")
    yb = ybox_b + (4 * ls + 34 if cost else 3 * ls + 30)
    if order_row:
        d.t(x, yb + 4, "Ordre", ls - 1, 600, INK)
        pts = xs + [xk]
        for i in range(4):
            a, b = pts[i + 1] - 16, pts[i] + 16
            src = order[i + 1] if i < 3 else None
            v = seats[src].order(wk) if src else DEM[wk - 1]
            d.line(a, yb, b + 6, yb, INK, 1)
            d.path(f"M{b:.1f} {yb:.1f} L{b + 6:.1f} {yb - 3.6:.1f} L{b + 6:.1f} {yb + 3.6:.1f} Z", INK)
            d.t((a + b) / 2, yb - 6, v, ls - 1, 600, INK, "middle")
    return yb + 10
