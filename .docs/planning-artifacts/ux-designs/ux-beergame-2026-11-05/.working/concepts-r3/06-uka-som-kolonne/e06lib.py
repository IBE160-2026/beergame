"""Felles byggeklosser for konsept 06 Uka som kolonne (runde 3).
Visuelt språk fra Meteogrammet (r2/02). Alle tall kommer fra ../_shared/fixture.json.

Grunnideen: hver Uke er en kolonne. Kolonnen har kjedens tilstand som tall (matrisen),
meteogrammet tegner de samme kolonnene som graf, og kjedevisningen øverst er én kolonne forstørret.
Derfor bygges alt fra Seat.col(w), og build stopper hvis noe ikke stemmer med loggen."""
import json
from html import escape
from pathlib import Path
from statistics import median

HERE = Path(__file__).resolve().parent
FX = json.loads((HERE.parent / "_shared" / "fixture.json").read_text(encoding="utf-8"))
P = "e06"

# ---------- Palett (Meteogrammet) ----------
PAPER = "#FFFFFF"
INK = "#0F2A47"
INK2 = "#44586F"
INK3 = "#5E6F82"
HAIR = "#E1E6EC"
HAIR2 = "#C3CDD8"
TINT = "#F2F5F8"
BLUE = "#2B6CA3"
BLUEF = "#CDDFEE"
RED = "#B5423A"
REDF = "#F0D5D2"
GREY = "#6B7785"
BASE = "#B4C4D4"
ORD = "#5F7A95"
FONT = "'Source Sans 3','Source Sans Pro','Segoe UI',Arial,sans-serif"

# ---------- Matrisetrinn (validert med dataviz/validate_palette.js --ordinal, alle PASS) ----------
NETB = ["#98B8D8", "#6E9BC7", "#2B6CA3", "#1B4870"]   # lager, lys til mørk
NETR = ["#E3A79F", "#D27A70", "#B5423A", "#82302A"]   # restordre, lys til mørk
FLOW = ["#A3B4C7", "#7F96AD", "#2C4763"]              # strømmer 10+, 15+, 20+

ROLES = ["Detaljist", "Grossist", "Distributør", "Fabrikk"]
NAVN = {"Detaljist": "Ida", "Grossist": "Sara", "Distributør": "Mikkel", "Fabrikk": "Jonas"}
LAGERKOST, RESTKOST = 0.5, 1.0


def nf(x, dec=2):
    s = f"{abs(x):,.{dec}f}".replace(",", " ").replace(".", ",")
    return ("−" + s) if x < 0 else s


def kc(x):
    """Kostnad i en celle: heltall uten desimaler, ellers én desimal."""
    if abs(x - round(x)) < 1e-9:
        return nf(round(x), 0)
    return nf(x, 1)


def sg(x):
    return f"−{abs(int(x))}" if x < 0 else str(int(x))


def fx1(x):
    return f"{x:.1f}".replace(".", ",") + "×"


def net_fill(v, th=(1, 10, 20, 30)):
    """Divergerende: blå over null, rød under, ingen fyll i null. Gir (fyll, tekstfarge)."""
    if v == 0:
        return None, INK
    a = abs(v)
    i = 3 if a >= th[3] else 2 if a >= th[2] else 1 if a >= th[1] else 0
    ramp = NETB if v > 0 else NETR
    return ramp[i], (PAPER if i >= 2 else INK)


def flow_fill(v):
    if v is None:
        return None, INK
    if v >= 20:
        return FLOW[2], PAPER
    if v >= 15:
        return FLOW[1], INK
    if v >= 10:
        return FLOW[0], INK
    return None, INK


NARROW = set("iljtfrI.,:;'|!() ")
WIDE = set("mwMWæÆ—")


def text_w(s, size):
    total = 0.0
    for c in str(s):
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
        return f"{P}-{self.name}-{kind}{self.n}"

    def t(self, x, y, s, size=14, w=400, fill=INK, a="start", extra=""):
        self.b.append(
            f'<text class="{P}-t" x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{w}" '
            f'fill="{fill}" text-anchor="{a}"{(" " + extra) if extra else ""}>{escape(str(s))}</text>'
        )

    def big(self, x, y, s, size, w=700, fill=INK, a="start"):
        """Store enkelttall med proporsjonale sifre."""
        self.t(x, y, s, size, w, fill, a, 'style="font-variant-numeric:lining-nums proportional-nums"')

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

    def link(self, x, y, s, size=14, a="start"):
        self.t(x, y, s, size, 600, BLUE, a, 'text-decoration="underline"')

    def demodata(self, x, y, s="Demodata", size=13, a="start"):
        self.t(x, y, s, size, 400, INK3, a)

    def arrow_l(self, x, y, col=ORD, s=6):
        """Pilspiss mot venstre, tegnet som form."""
        self.path(f"M{x:.1f} {y:.1f} L{x + s:.1f} {y - s * 0.6:.1f} L{x + s:.1f} {y + s * 0.6:.1f} Z", col)

    def arrow_r(self, x, y, col=INK, s=6):
        self.path(f"M{x:.1f} {y:.1f} L{x - s:.1f} {y - s * 0.6:.1f} L{x - s:.1f} {y + s * 0.6:.1f} Z", col)

    def save(self):
        css = (
            "@import url('https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;600;700&amp;display=swap');"
            f".{P}-t{{font-family:{FONT};font-variant-numeric:lining-nums tabular-nums;}}"
        )
        out = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.W} {self.H}" font-family="{FONT}">'
            f"<title>{escape(self.title)}</title><desc>{escape(self.desc)}</desc><style>{css}</style>"
            f'<rect x="0" y="0" width="{self.W}" height="{self.H}" fill="{PAPER}"/>' + "".join(self.b) + "</svg>"
        )
        assert "d02-" not in out
        (HERE / f"{self.name}.svg").write_text(out, encoding="utf-8")


# ---------- Data ----------
class Seat:
    """Ett setes serier fra loggen. Uke 1 = indeks 0."""

    def __init__(self, role="Grossist", src=None):
        src = src or FX["spill17"]
        s = src["serier"][role]
        self.role = role
        self.ordre, self.lager, self.rest = s["ordre"], s["lager"], s["restordre"]
        self.innk, self.lev, self.pv, self.kost = s["innkommende_ordre"], s["levering"], s["paa_vei"], s["kost_sum"]
        self.n = len(self.ordre)
        self.net_ = [a - b for a, b in zip(self.lager, self.rest)]
        self.sendt_ = []
        prev = 0
        for i in range(self.n):
            self.sendt_.append(self.innk[i] + prev - self.rest[i])
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

    def kost_l(self, w):
        return self.lager[w - 1] * LAGERKOST

    def kost_r(self, w):
        return self.rest[w - 1] * RESTKOST

    def wcost(self, w):
        return self.kost_l(w) + self.kost_r(w)

    def sum_l(self, upto=None):
        return sum(self.kost_l(k) for k in range(1, (upto or self.n) + 1))

    def sum_r(self, upto=None):
        return sum(self.kost_r(k) for k in range(1, (upto or self.n) + 1))

    def arrivals(self, w, typed):
        """Kjente ankomster de neste fire ukene. Siste plass er ordren denne Uka."""
        out = [(w + j, self.order(w + j - 4)) for j in (1, 2, 3)]
        out.append((w + 4, typed))
        return out

    def overdue(self, w):
        return self.paavei(w) - sum(self.order(k) for k in (w - 3, w - 2, w - 1))

    def col(self, w):
        """Én kolonne. Matrisen, meteogrammet og kjedevisningen leser alle herfra."""
        return {"uke": w, "inn": self.inn(w), "lev": self.levering(w), "net": self.net(w), "lager": self.lager[w - 1],
                "rest": self.rest[w - 1], "pv": self.paavei(w), "ordre": self.order(w), "sendt": self.sendt(w),
                "kost": self.wcost(w), "kost_l": self.kost_l(w), "kost_r": self.kost_r(w), "sum": self.kostsum(w),
                "pos": self.posisjon(w)}

    def projection(self, w, typed):
        rate = self.inn(w)
        net = self.net(w)
        pts = [(w, net)]
        for week, qty in self.arrivals(w, typed):
            net += (qty or 0) - rate
            pts.append((week, net))
        return pts


def check_dataset(key):
    """Bygget stopper her hvis matrisen, grafene eller kostnaden ikke stemmer med loggen."""
    src = FX[key]
    total = 0.0
    for r in ROLES:
        S = Seat(r, src)
        for w in range(1, S.n + 1):
            c = S.col(w)
            # P1: kolonnen er regnestykket
            if w > 1:
                assert c["net"] == S.net(w - 1) + c["lev"] - c["inn"], (key, r, w, "materialbalanse")
                assert c["pv"] == S.paavei(w - 1) + S.order(w - 1) - c["lev"], (key, r, w, "på vei")
                avail = max(S.lager[w - 2], 0) + c["lev"]
                assert 0 <= c["sendt"] <= avail, (key, r, w, "sendt")
            # P8: ukeskostnaden er lager × 0,50 + restordre × 1,00, og summen er loggens kost_sum
            assert abs(c["sum"] - (S.kostsum(w - 1) + c["kost"])) < 1e-9, (key, r, w, "kost")
            assert c["lager"] == 0 or c["rest"] == 0, (key, r, w, "lager og restordre samtidig")
            assert S.overdue(w) >= 0, (key, r, w, "forsinket")
        assert abs(S.sum_l() + S.sum_r() - src["kost_per_rolle"][r]) < 1e-9, (key, r, "kost per rolle")
        total += src["kost_per_rolle"][r]
    assert abs(total - src["kjedekost"]) < 1e-9, (key, "kjedekost")


for _k in ("spill17", "bare_sara_teller_paa_vei", "alle_teller_paa_vei", "replay_sara"):
    check_dataset(_k)

G = Seat()
SEATS = {r: Seat(r) for r in ROLES}
BARE = Seat("Grossist", FX["bare_sara_teller_paa_vei"])
ALLE = Seat("Grossist", FX["alle_teller_paa_vei"])
RE = Seat("Grossist", FX["replay_sara"])
K = FX["spill17"]
KL = FX["klasse"]
DEM = K["serier"]["demand"]

# Saras skjerm i Uke 11 slik briefen beskriver den
_c = G.col(11)
assert (_c["lager"], _c["rest"], _c["inn"], _c["lev"], _c["sendt"], _c["pv"], _c["sum"]) == (0, 13, 8, 4, 4, 16, 68.0)
assert _c["pos"] == 3 and _c["pos"] + 24 == 27
assert [G.order(k) for k in range(1, 11)] == [4] * 9 + [8]
assert G.arrivals(11, 24)[0] == (12, 4)
assert K["kjedekost"] == 2266.0


def chain_week_cost(w, seats=SEATS):
    return sum(S.wcost(w) for S in seats.values())


for _w in range(1, 37):
    assert abs(sum(SEATS[r].kostsum(_w) for r in ROLES) - sum(chain_week_cost(k) for k in range(1, _w + 1))) < 1e-9


# ---------- Klassen, aggregert ----------
def game_week_cost(sp, k):
    return sum((v * LAGERKOST if v > 0 else -v * RESTKOST) for r in ROLES for v in [sp["netto_lager"][r][k - 1]])


def class_aggregates():
    spill = KL["spill"]
    for sp in spill:
        c = sum(game_week_cost(sp, k) for k in range(1, sp["uke"] + 1))
        assert abs(c - sp["kjedekost"]) < 0.6, ("klasse", sp["spill"])
        for r in ROLES:
            assert len(sp["netto_lager"][r]) == sp["uke"]
    agg = {"n": [], "median_net": {r: [] for r in ROLES}, "median_cost": [], "sum_cost": [], "cum": []}
    cum = 0.0
    for k in range(1, 37):
        ins = [sp for sp in spill if sp["uke"] >= k]
        agg["n"].append(len(ins))
        for r in ROLES:
            agg["median_net"][r].append(median(sp["netto_lager"][r][k - 1] for sp in ins))
        costs = [game_week_cost(sp, k) for sp in ins]
        agg["median_cost"].append(median(costs))
        agg["sum_cost"].append(sum(costs))
        cum += sum(costs)
        agg["cum"].append(cum)
    assert abs(cum - sum(sp["kjedekost"] for sp in spill)) < 30
    return agg


AGG = class_aggregates()


# ---------- Akse og skala ----------
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
    Y = yscale(y0, h, lo, hi)
    pts = [(ax.xc(w), Y(vals(w))) for w in range(wfrom, wto + 1)]
    line = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    area = line + f" L{pts[-1][0]:.1f} {Y(0):.1f} L{pts[0][0]:.1f} {Y(0):.1f} Z"
    up = d.cliprect(ax.x0 - 2, y0 - 4, ax.w + 4, Y(0) - y0 + 4)
    dn = d.cliprect(ax.x0 - 2, Y(0), ax.w + 4, y0 + h - Y(0) + 4)
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


def flow_bars(d, ax, y0, h, g, wfrom, wto, scale=32, x1=None):
    """Levering og ordre inn. Den fargede delen er nøyaktig endringen i netto lager (P1)."""
    u = h / scale
    bw = max(ax.slot - 3, 2)
    base = y0 + h
    for w in range(wfrom, wto + 1):
        lev, inn = g.levering(w), g.inn(w)
        x = ax.xc(w) - bw / 2
        low = min(lev, inn)
        d.rect(x, base - low * u, bw, low * u, BASE)
        diff = abs(lev - inn) * u
        if diff > 0:
            d.rect(x, base - low * u - diff - 1, bw, diff, RED if inn > lev else BLUE)
    d.line(ax.x0, base, x1 or ax.x1, base, HAIR2, 1)


def order_bars(d, ax, y0, h, vals, wfrom, wto, scale=25, fill=ORD, x1=None, hi=None):
    u = h / scale
    bw = max(ax.slot - 3, 2)
    base = y0 + h
    for w in range(wfrom, wto + 1):
        v = vals(w)
        d.rect(ax.xc(w) - bw / 2, base - v * u, bw, v * u, INK if w == hi else fill)
    d.line(ax.x0, base, x1 or ax.x1, base, HAIR2, 1)


def week_row(d, ax, y, weeks, now=None, sel=None, size=13, every=1):
    for w in weeks:
        if every > 1 and (w - weeks[0]) % every and w not in (now, sel):
            continue
        bold = w in (now, sel)
        d.t(ax.xc(w), y, w, size, 700 if bold else 400, INK if bold else INK3, "middle")


# ---------- Matrisen ----------
def matrix(d, ax, y, rows, wfrom, wto, rh=21, size=13, lx=None, lsize=13, lw=600, sep=True, gap=1):
    """rows: (etikett, art, hent(w)). hent gir None, en verdi, eller (verdi, stil) der stil er 'open' eller 'typed'.
    art: net, flow, plain, cost, sum, pos, kr. Tall i cellene leses fra Seat.col, aldri tastet inn."""
    lx = ax.x0 - 8 if lx is None else lx
    for i, (label, kind, get) in enumerate(rows):
        yy = y + i * rh
        if label:
            d.t(lx, yy + rh / 2 + lsize * 0.34, label, lsize, lw, INK, "start" if lx < ax.x0 - 30 else "end")
        if sep:
            d.line(ax.x0, yy + rh, ax.x1, yy + rh, HAIR, 1)
        for w in range(wfrom, wto + 1):
            v = get(w)
            if v is None:
                continue
            style = None
            if isinstance(v, tuple) and v[1] in ("open", "typed", "late"):
                v, style = v
            x0 = ax.xl(w) + gap
            cw = ax.slot - 2 * gap
            tc = INK
            wt = 400
            fill = None
            if kind == "net":
                fill, tc = net_fill(v)
                s = sg(v)
            elif kind == "netw":
                fill, tc = net_fill(v, (1, 12, 24, 48))
                s = sg(v)
            elif kind == "flow":
                fill, tc = flow_fill(v)
                s = sg(v)
            elif kind == "cost":
                c, art = v
                fill = REDF if art == "R" else (BLUEF if art == "L" else None)
                s = kc(c)
            elif kind == "sum":
                s = kc(v)
                wt = 600
            elif kind == "kr":
                s = nf(v, 0)
            else:
                s = sg(v) if isinstance(v, int) else str(v)
            if style == "open":
                d.rect(x0 + 1, yy + gap + 1, cw - 2, rh - 2 * gap - 2, PAPER, BLUE, 1.1)
                fill = None
                tc = INK
            elif style == "typed":
                d.rect(x0 + 1, yy + gap + 1, cw - 2, rh - 2 * gap - 2, PAPER, INK, 1.6)
                fill = None
                tc = INK
                wt = 700
            elif style == "late":
                d.rect(x0 + 1, yy + gap + 1, cw - 2, rh - 2 * gap - 2, PAPER, HAIR2, 1, extra='stroke-dasharray="3 2"')
                fill = None
                tc = INK2
            if fill:
                d.rect(x0, yy + gap, cw, rh - 2 * gap, fill)
            d.t(ax.xc(w), yy + rh / 2 + size * 0.34, s, size, wt, tc, "middle")
    return y + len(rows) * rh


def seat_rows(S, now, typed=None, short=False, pos=False, cost=True, sumrow=True, future=True, labels=None):
    """Setets egne rader. Til høyre for nå står bare kjente ankomster."""
    arr = dict(S.arrivals(now, typed)) if future else {}

    def lev(w):
        if w <= now:
            return S.levering(w)
        if w in arr and arr[w] is not None:
            return (arr[w], "typed" if w == now + 4 else "open")
        return None

    def ordre(w):
        if w < now:
            return S.order(w)
        if w == now:
            return (typed, "typed") if typed is not None else None
        return None

    def past(f):
        return lambda w: f(w) if w <= now else None

    L = labels or {}
    rows = [
        (L.get("inn", "Ordre inn"), "flow", past(S.inn)),
        (L.get("lev", "Levering"), "flow", lev),
        (L.get("net", "Lager"), "net", past(S.net)),
        (L.get("pv", "På vei"), "plain", past(S.paavei)),
        (L.get("ordre", "Din ordre"), "flow", ordre),
    ]
    if pos:
        rows.append((L.get("pos", "Posisjon"), "plain", lambda w: (S.posisjon(w) if w <= now else None)))
    if cost:
        rows.append((L.get("kost", "Kostnad"), "cost",
                     lambda w: ((S.wcost(w), "R" if S.rest[w - 1] else ("L" if S.lager[w - 1] else None)) if w <= now else None)))
    if sumrow:
        rows.append((L.get("sum", "Sum, kr"), "sum", lambda w: (S.kostsum(w) if w <= now else None)))
    return rows


def col_box(d, ax, w, ytop, ybot, sw=1.4, col=INK):
    d.rect(ax.xl(w), ytop, ax.slot, ybot - ytop, "none", col, sw, 2)


def zoom(d, x0, x1, ychain, ax, w, ycol, col=HAIR2):
    """Kjedevisningen er kolonnen forstørret: to tynne linjer fra kjedens hjørner til kolonnens topp."""
    d.path(f"M{x0:.1f} {ychain:.1f} L{ax.xl(w):.1f} {ycol:.1f} M{x1:.1f} {ychain:.1f} L{ax.xr(w):.1f} {ycol:.1f}", stroke=col, sw=1)


def diag(d, ax, w_from, y_from, w_to, y_to):
    """Ordren tegnet to ganger: fra beslutningen til ankomsten om lag 4 uker senere (P2)."""
    d.path(f"M{ax.xr(w_from) - 1:.1f} {y_from:.1f} L{ax.xl(w_to) + 1:.1f} {y_to:.1f}", stroke=INK, sw=1)


# ---------- Kjedevisningen: setets ledd ----------
def seat_chain(d, x, y, w, S, wk, typed=None, u=1.4, ls=13, vs=15, down="Detaljist", up="Distributør", show_slots_weeks=True, yb_off=84):
    """Setets ledd for Uke wk, som en forstørret kolonne. Varene kommer fra høyre (oppstrøms) og går mot venstre.
    Beholdninger og varer på vei er bokser på sann skala, u piksler per enhet."""
    c = S.col(wk)
    typed_eff = typed
    yb = y + yb_off
    x1 = x + w
    # soner
    sx0 = x + w * 0.18
    sw_ = w * 0.145
    px0 = x + w * 0.52
    px1 = x1 - 4
    slots = S.arrivals(wk, typed_eff)
    nsl = 4
    over = S.overdue(wk)
    gapw = 4
    slw = (px1 - px0 - gapw * (nsl - 1)) / nsl
    # transportbåndet
    d.line(x + 8, yb, x1, yb, ORD, 2)
    d.arrow_l(x, yb, ORD, 8)
    d.arrow_l(sx0 + sw_ + 4, yb, ORD, 6)
    # lager / restordre på sann skala
    if c["lager"] > 0:
        d.rect(sx0, yb - c["lager"] * u, sw_, c["lager"] * u, BLUEF, BLUE, 1.2)
    if c["rest"] > 0:
        d.rect(sx0, yb + 1, sw_, c["rest"] * u, REDF, RED, 1.2)
    d.line(sx0, yb - 1, sx0 + sw_, yb - 1, INK, 2)
    # på vei
    for i, (week, q) in enumerate(slots):
        xx = px0 + i * (slw + gapw)
        if q is None:
            d.rect(xx, yb - 14, slw, 13, "none", INK, 1.2, extra='stroke-dasharray="3 3"')
            continue
        is_t = week == wk + 4
        hh = q * u
        d.rect(xx, yb - hh - 1, slw, hh, PAPER, INK if is_t else BLUE, 1.6 if is_t else 1.2)
        d.t(xx + slw / 2, yb - hh - 6, q, ls, 700 if is_t else 600, INK, "middle")
        if show_slots_weeks:
            d.t(xx + slw / 2, yb + 16, f"{week}", ls, 400, INK3, "middle")
    if show_slots_weeks:
        d.t(px0 - 6, yb + 16, "Uke", ls, 400, INK3, "end")
    # ordre inn fra nedstrøms: tynn pil inn mot lageret, det som ikke kan sendes blir restordre
    yo = yb + 16
    d.line(x + 2, yo, sx0 - 6, yo, INK, 1)
    d.arrow_r(sx0 - 2, yo, INK, 6)
    d.t(x, yo + 18, f"Ordre inn {c['inn']}", ls, 600, INK)
    # etiketter over, med hjelpelinjer
    ylab = y + 14
    stock = ("Lager", str(c["lager"])) if c["rest"] == 0 else ("Restordre", str(c["rest"]))
    items = [
        (x, "Sendt", str(c["sendt"]), x + 24, yb - 3),
        (sx0, stock[0], stock[1], sx0 + 8, (yb - c["lager"] * u - 2) if c["lager"] else yb - 3),
        (sx0 + sw_ + 10, "Levering", str(c["lev"]), sx0 + sw_ + 18, yb - 3),
    ]
    pvs = f"{c['pv']}" + (f" + {typed_eff}" if typed_eff is not None else "")
    items.append((px0, "På vei", pvs, None, None))
    for xx, lab, val, lxx, ly in items:
        d.t(xx, ylab, lab, ls, 400, INK2)
        d.t(xx, ylab + vs + 3, val, vs, 700, INK)
        if lxx is not None:
            d.line(lxx, ylab + vs + 8, lxx, ly, HAIR2, 1)
    if over > 0:
        d.t(px1, yb + 34, f"+ {over} forsinket, uten dato", ls, 400, INK2, "end")
    # nedstrøms og oppstrøms
    bottom = max(yb + c["rest"] * u + 6, yo + 22, yb + (40 if over > 0 else 24))
    return {"yb": yb, "bottom": bottom, "sx0": sx0, "sw": sw_, "px0": px0, "slw": slw}


# ---------- Kjedevisningen: fire ledd ----------
def chain4(d, x, y, w, seats, wk, kunde=None, u=1.0, ls=13, show_cost=False, h_up=70, typed_last=True, title=None, names=True,
           sel_role=None):
    """Hele kjeden for Uke wk: Kunde, Detaljist, Grossist, Distributør, Fabrikk fra venstre.
    Ordrene går mot høyre, varene kommer mot venstre. Beholdninger og på vei på sann skala."""
    order = ROLES
    kz = 64 if kunde is not None else 0
    nw = 56
    lane = (w - kz - nw * 4) / 4
    maxup = max(max(seats[r].col(wk)["lager"], max((q or 0) for _, q in seats[r].arrivals(wk, seats[r].order(wk)))) for r in ROLES)
    maxdn = max(seats[r].col(wk)["rest"] for r in ROLES)
    h_up = max(h_up, 58 + maxup * u + 14)
    yb = y + h_up
    d.line(x + 8, yb, x + w, yb, ORD, 2)
    d.arrow_l(x, yb, ORD, 8)
    out = {}
    if kunde is not None:
        d.t(x, y + 12, "Kunden", ls, 700, INK)
        d.t(x, y + 30, f"bestilte {kunde}", ls, 400, INK2)
    for i, r in enumerate(order):
        S = seats[r]
        c = S.col(wk)
        nx = x + kz + i * (nw + lane)
        # node
        if c["lager"] > 0:
            d.rect(nx, yb - c["lager"] * u, nw, c["lager"] * u, BLUEF, BLUE, 1.2)
        if c["rest"] > 0:
            d.rect(nx, yb + 1, nw, c["rest"] * u, REDF, RED, 1.2)
        d.line(nx, yb - 1, nx + nw, yb - 1, INK, 2.4 if r == sel_role else 2)
        if names:
            d.t(nx, y + 12, r, ls, 700, INK)
            d.t(nx, y + 30, NAVN[r] + (", du" if r == sel_role else ""), ls, 400, INK2)
        st = f"Lager {c['lager']}" if c["net"] >= 0 else f"Restordre {c['rest']}"
        yv = yb + max(c["rest"] * u, 0) + 17
        d.t(nx, yv, st, ls, 700, INK)
        d.t(nx, yv + 17, f"Ordre inn {c['inn']}", ls, 400, INK2)
        if show_cost:
            d.t(nx, yv + 34, f"{nf(S.kostsum(wk))} kr", ls, 400, INK2)
        # på vei til denne noden, i banen til høyre
        typed = S.order(wk) if typed_last else None
        arr = S.arrivals(wk, typed)
        lx0 = nx + nw + 10
        lx1 = nx + nw + lane - 10
        sw_ = (lx1 - lx0 - 9) / 4
        for j, (week, q) in enumerate(arr):
            xx = lx0 + j * (sw_ + 3)
            if q is None:
                continue
            hh = q * u
            d.rect(xx, yb - hh - 1, sw_, hh, PAPER, BLUE, 1)
            if sw_ >= 16:
                d.t(xx + sw_ / 2, yb - hh - 5, q, 12 if sw_ < 22 else ls, 400, INK, "middle")
        ov = S.overdue(wk)
        pvt = f"På vei {c['pv']}"
        d.t(lx1, yb + 17, pvt, 12, 400, INK2, "end")
        if ov > 0:
            d.t(lx1, yb + 32, f"{ov} uten dato", 12, 400, INK2, "end")
        # ordren denne uka går mot høyre
        d.line(lx1 - 26, y + 46, lx1 + 6, y + 46, INK, 1)
        d.arrow_r(lx1 + 10, y + 46, INK, 6)
        d.t(lx1 - 30, y + 50, f"Ordre {S.order(wk)}", 12, 600, INK, "end")
        out[r] = (nx, nw)
    if kunde is not None:
        d.line(x + 2, y + 46, x + kz - 8, y + 46, INK, 1)
        d.arrow_r(x + kz - 4, y + 46, INK, 6)
    out["yb"] = yb
    out["bottom"] = yb + maxdn * u + 17 + 17 + (17 if show_cost else 0) + 6
    return out


# ---------- Telefon ----------
def phone(d, x, y, s=1.0):
    d.rect(x, y, 390 * s, 844 * s, PAPER, HAIR2, 1.4, 36 * s)
    d.g(f"translate({x},{y}) scale({s})")


def game_header(d, wk, kost, role="Grossist", spill="Spill 17", x=20):
    d.t(x, 66, f"Uke {wk}", 30, 700, INK)
    d.t(x, 88, f"{role}, {spill}", 14, 400, INK2)
    d.t(370, 62, "Totalkostnad", 13, 400, INK2, "end")
    d.t(370, 84, f"{nf(kost)} kr", 18, 600, INK, "end")


def waiting_rows(d, y, rows, x=20, width=350, lh=30, size=14):
    for rolle, navn, status, done in rows:
        if done:
            d.circle(x + 6, y - 5, 5, INK)
        else:
            d.circle(x + 6, y - 5, 5, PAPER, INK, 1.5)
        d.t(x + 20, y, rolle, size, 600, INK)
        d.t(x + 104, y, navn, size, 400, INK)
        d.t(x + width, y, status, size, 400, INK2, "end")
        y += lh
    return y
