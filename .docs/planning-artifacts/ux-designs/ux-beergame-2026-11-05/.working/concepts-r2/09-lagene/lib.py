"""Felles motor for konsept 09 Lagene: tekst, telefon og den ene grafen."""
import json
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).parent
FX = json.loads((HERE.parent / "_shared" / "fixture.json").read_text(encoding="utf-8"))
S = FX["spill17"]["serier"]
ROLLER = ["Detaljist", "Grossist", "Distributør", "Fabrikk"]
PERSON = {"Detaljist": "Ida", "Grossist": "Sara", "Distributør": "Mikkel", "Fabrikk": "Jonas"}

INK = "#111111"      # Blekk
G1 = "#5C5C5C"       # Grå tekst, 6,7:1 mot hvitt
G2 = "#9C9C9C"       # Eldre lag, linjer
G3 = "#D4D4D4"       # Hjelpelinje, sterk
G4 = "#EDEDED"       # Areal mellom inn og ut, hjelpelinje
VER = "#DB3A12"      # Vermilion: det nye, eller nå
WHITE = "#FFFFFF"

FONT = "Mulish"
FALLBACK = "'Mulish','Segoe UI',Helvetica,Arial,sans-serif"


# ---------- tall ----------
def num(v, d=0):
    """Norsk tallformat med hardt mellomrom som tusenskille og ekte minus."""
    neg = v < 0
    s = f"{abs(v):,.{d}f}".replace(",", " ").replace(".", ",")
    return ("−" if neg else "") + s


def kr(v):
    return num(v, 2) + " kr"


def x_(v):
    return num(v, 1) + "×"


def net(role="Grossist", data=S):
    r = data[role]
    return [a - b for a, b in zip(r["lager"], r["restordre"])]


def pos(role="Grossist", data=S):
    return [a + b for a, b in zip(net(role, data), data[role]["paa_vei"])]


def sendt(role, w, data=S):
    r = data[role]
    forrige = r["lager"][w - 2] if w > 1 else r["lager"][0]
    return forrige + r["levering"][w - 1] - r["lager"][w - 1]


def assert_balanse():
    """Materialbalansen grafen hviler på: endring i netto lager = levering minus ordre inn."""
    for role in ROLLER:
        n = net(role)
        r = S[role]
        for t in range(1, 36):
            assert n[t] - n[t - 1] == r["levering"][t] - r["innkommende_ordre"][t], (role, t)


# ---------- tekst ----------
def est(s, size, w=400):
    """Anslag på tekstbredde i Mulish, godt nok til bryting. Rendringen er kontrollen."""
    tot = 0.0
    for c in s:
        if c in "iljtf.,:;'| ()":
            tot += 0.31
        elif c in "mwMWæ":
            tot += 0.86
        elif c.isupper() or c in "ÆØÅ":
            tot += 0.68
        elif c.isdigit():
            tot += 0.60
        else:
            tot += 0.55
    return tot * size * (1.05 if w >= 700 else 1.0)


def T(x, y, s, size=15, w=400, fill=INK, a="start", u=False, h=False):
    cls = "d09-t d09-u" if u else ("d09-t d09-h" if h else "d09-t")
    anchor = "" if a == "start" else f' text-anchor="{a}"'
    return (f'<text class="{cls}" x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{w}" '
            f'fill="{fill}"{anchor}>{escape(s)}</text>')


def R(x, y, runs, size=15, a="start"):
    """Linje med flere vekter eller farger: runs = [(tekst, vekt, farge), ...]."""
    anchor = "" if a == "start" else f' text-anchor="{a}"'
    body = "".join(f'<tspan font-weight="{w}" fill="{f}">{escape(s)}</tspan>' for s, w, f in runs)
    return f'<text class="d09-t" x="{x:.1f}" y="{y:.1f}" font-size="{size}"{anchor}>{body}</text>'


def wrap(s, maxw, size, w=400):
    out, cur = [], ""
    for word in s.split(" "):
        test = (cur + " " + word).strip()
        if est(test, size, w) > maxw and cur:
            out.append(cur)
            cur = word
        else:
            cur = test
    if cur:
        out.append(cur)
    return out


def P(x, y, s, maxw, size=15, lh=None, w=400, fill=INK, a="start"):
    """Brutt avsnitt. Returnerer (svg, y etter siste linje)."""
    lh = lh or round(size * 1.45)
    lines = wrap(s, maxw, size, w)
    svg = "".join(T(x, y + i * lh, l, size, w, fill, a) for i, l in enumerate(lines))
    return svg, y + len(lines) * lh


def L(x1, y1, x2, y2, c=INK, sw=1.0, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{c}" '
            f'stroke-width="{sw}"{d} fill="none"/>')


def rect(x, y, w, h, fill=INK, rx=0):
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}" rx="{rx}"/>'


def btn(x, y, w, h, s, size=17):
    return rect(x, y, w, h, INK, 2) + T(x + w / 2, y + h / 2 + size * 0.35, s, size, 700, WHITE, "middle")


# ---------- dokument ----------
class Doc:
    def __init__(self, stem, w, h, title, desc):
        self.stem, self.w, self.h, self.title, self.desc = stem, w, h, title, desc
        self.side = stem.split("-")[0]
        self.parts = []

    def add(self, *items):
        for it in items:
            if isinstance(it, (list, tuple)):
                self.add(*it)
            else:
                self.parts.append(it)

    def hatch(self):
        return f"d09-{self.side}-skravur"

    def save(self):
        style = (
            "@import url('https://fonts.googleapis.com/css2?family=Mulish:wght@300;400;700&amp;display=swap');"
            f".d09-t{{font-family:{FALLBACK};font-variant-numeric:lining-nums tabular-nums;}}"
            ".d09-u{text-decoration:underline;text-underline-offset:3px;text-decoration-thickness:1px;}"
            ".d09-h{paint-order:stroke;stroke:#FFFFFF;stroke-width:4px;stroke-linejoin:round;}"
        )
        defs = (
            f'<pattern id="{self.hatch()}" width="5" height="5" patternUnits="userSpaceOnUse" '
            f'patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="5" stroke="{G2}" stroke-width="1"/></pattern>'
        )
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" '
            f'font-family="{FALLBACK.replace(chr(39), "")}">'
            f"<title>{escape(self.title)}</title><desc>{escape(self.desc)}</desc>"
            f"<style>{style}</style><defs>{defs}</defs>"
            f'<rect id="d09-{self.side}-grunn" x="0" y="0" width="{self.w}" height="{self.h}" fill="{WHITE}"/>'
            + "".join(self.parts) + "</svg>"
        )
        (HERE / f"{self.stem}.svg").write_text(svg, encoding="utf-8")


# ---------- den ene grafen ----------
class Sc:
    """Tid: Uke t slutter ved x(t), og høyre kant er alltid nå. Verdi: samme enhet på én akse."""

    def __init__(self, x, y, w, h, upto, ymin, ymax, start=0):
        self.x0, self.y0, self.w, self.h = x, y, w, h
        self.upto, self.ymin, self.ymax, self.start = upto, ymin, ymax, start

    def X(self, t):
        return self.x0 + (t - self.start) / (self.upto - self.start) * self.w

    def Y(self, v):
        return self.y0 + (self.ymax - v) / (self.ymax - self.ymin) * self.h


def path(pts, c, sw, dash=None, op=None, join="round"):
    d = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    extra = f' stroke-dasharray="{dash}"' if dash else ""
    extra += f' opacity="{op}"' if op else ""
    return (f'<path d="{d}" fill="none" stroke="{c}" stroke-width="{sw}" '
            f'stroke-linejoin="{join}" stroke-linecap="round"{extra}/>')


def stock(sc, vals, upto=None, start=None):
    """Beholdning: et punkt ved slutten av hver Uke."""
    upto = upto or sc.upto
    start = sc.start if start is None else start
    pts = [(sc.X(start), sc.Y(vals[max(start - 1, 0)]))] if start == 0 else []
    for t in range(max(start, 1), upto + 1):
        pts.append((sc.X(t), sc.Y(vals[t - 1])))
    return pts


def flow(sc, vals, upto=None, start=1):
    """Strøm: flat gjennom hele Uka, slik at arealet blir nøyaktig enheter."""
    upto = upto or sc.upto
    pts = []
    for t in range(start, upto + 1):
        pts += [(sc.X(t - 1), sc.Y(vals[t - 1])), (sc.X(t), sc.Y(vals[t - 1]))]
    return pts


def axes(sc, weeks=(), yt=(), now=True, size=13, nowlabel="nå", zero=True, ygutter=True):
    out = []
    right = sc.X(sc.upto)
    for v in yt:
        if v == 0:
            continue
        out.append(L(sc.x0, sc.Y(v), right, sc.Y(v), G4, 1))
        if ygutter:
            out.append(T(sc.x0 - 8, sc.Y(v) + size * 0.35, num(v), size, 400, G1, "end"))
    if zero and sc.ymin <= 0 <= sc.ymax:
        out.append(L(sc.x0, sc.Y(0), right, sc.Y(0), G2, 1))
        if ygutter:
            out.append(T(sc.x0 - 8, sc.Y(0) + size * 0.35, "0", size, 400, G1, "end"))
    base = sc.y0 + sc.h + size + 8
    for t in weeks:
        label = f"Uke {t}" if t == weeks[0] else str(t)
        anchor = "start" if t == weeks[0] else "middle"
        xp = sc.X(t - 1) if t == weeks[0] else sc.X(t) - (sc.X(t) - sc.X(t - 1)) / 2
        if now and nowlabel and t != weeks[0] and right - xp < 24:
            continue
        out.append(T(xp, base, label, size, 400, G1, anchor))
    if now:
        out.append(L(right, sc.y0, right, sc.y0 + sc.h + 4, VER, 1))
        if nowlabel:
            out.append(T(right, base, nowlabel, size, 700, VER, "middle"))
    return out


def plot(doc, sc, layers, role="Grossist", data=S, upto=None, new=(), sw=1.0, start=None):
    """Tegner valgte lag i fast rekkefølge. Samme linjespråk overalt i produktet."""
    r = data[role]
    upto = upto or sc.upto
    st = sc.start if start is None else start
    out = []
    n = net(role, data)
    if "band" in layers:  # På vei løftet opp på Lager: toppen er Posisjon
        top = stock(sc, pos(role, data), upto, st)
        bottom = stock(sc, n, upto, st)
        d = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in top + bottom[::-1]) + " Z"
        out.append(f'<path d="{d}" fill="{G4}" stroke="none"/>')
    if "areal" in layers:  # Arealet mellom inn og ut er endringen i lageret
        for t in range(max(st, 0) + 1, upto + 1):
            inn, ut = r["levering"][t - 1], r["innkommende_ordre"][t - 1]
            if inn == ut:
                continue
            x, w = sc.X(t - 1), sc.X(t) - sc.X(t - 1)
            y, h = sc.Y(max(inn, ut)), abs(sc.Y(inn) - sc.Y(ut))
            fill = G4 if ut > inn else f"url(#{doc.hatch()})"
            out.append(rect(x, y, w, h, fill))
    if "vei" in layers:
        c = VER if "vei" in new else G2
        out.append(path(stock(sc, r["paa_vei"], upto, st), c, 1.6 * sw))
    if "inn" in layers:
        c = VER if "inn" in new else G1
        out.append(path(flow(sc, r["innkommende_ordre"], upto, max(st, 0) + 1), c, 1.25 * sw, join="miter"))
    if "lev" in layers:
        c = VER if "lev" in new else G1
        out.append(path(flow(sc, r["levering"], upto, max(st, 0) + 1), c, 1.25 * sw, dash="1 3.5"))
    if "lager" in layers:
        c = VER if "lager" in new else INK
        out.append(path(stock(sc, n, upto, st), c, 2.5 * sw))
    if "pos" in layers:
        c = VER if "pos" in new else INK
        out.append(path(stock(sc, pos(role, data), upto, st), c, 1.25 * sw))
    return out


def endlabels(sc, items, size=13, gap=None, xoff=8, x=None):
    """Direkte etiketter ved høyre kant. items = (verdi, navn, tall, farge). Skyves fra hverandre ved trengsel."""
    gap = gap or size + 5
    items = sorted(items, key=lambda it: -it[0])
    ys = [sc.Y(it[0]) + size * 0.35 for it in items]
    for _ in range(40):
        moved = False
        for i in range(len(ys) - 1):
            d = ys[i + 1] - ys[i]
            if d < gap:
                shift = (gap - d) / 2
                ys[i] -= shift
                ys[i + 1] += shift
                moved = True
        if not moved:
            break
    out = []
    xp = (sc.X(sc.upto) + xoff) if x is None else x
    for (val, name, valtxt, col), yp in zip(items, ys):
        out.append(R(xp, yp, [(name + " ", 400, col), (valtxt, 700, col)], size))
    return out


def lagerlabel(role, w, data=S, col=INK):
    v = net(role, data)[w - 1]
    if v < 0:
        return (v, "Restordre", num(-v), col)
    return (v, "Lager", num(v), col)


def std_labels(sc, w, layers=("lager", "inn", "lev", "vei"), role="Grossist", new=(), data=S):
    r = data[role]
    items = []
    if "lager" in layers:
        items.append(lagerlabel(role, w, data, VER if "lager" in new else INK))
    if "inn" in layers:
        items.append((r["innkommende_ordre"][w - 1], "Ordre inn", num(r["innkommende_ordre"][w - 1]), VER if "inn" in new else G1))
    if "lev" in layers:
        items.append((r["levering"][w - 1], "Levering", num(r["levering"][w - 1]), VER if "lev" in new else G1))
    if "vei" in layers:
        items.append((r["paa_vei"][w - 1], "På vei", num(r["paa_vei"][w - 1]), VER if "vei" in new else G1))
    return items


# ---------- telefon ----------
def phone(x, y, s, body, title=None):
    w, h = 390, 844
    out = [f'<g transform="translate({x} {y}) scale({s})">']
    out.append(f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="38" fill="{WHITE}" stroke="{G3}" stroke-width="1"/>')
    out += body if isinstance(body, list) else [body]
    out.append("</g>")
    return out


def keypad(y=606, rows=52):
    out = []
    digs = ["12345", "67890"]
    xs = [55, 125, 195, 265, 335]
    for i, row in enumerate(digs):
        for j, ch in enumerate(row):
            out.append(T(xs[j], y + 22 + i * rows, ch, 27, 400, INK, "middle"))
    return out


def yd(week):
    """Skalaen vokser bare når tallene krever det. Sann null. Avsløres aldri av slutten."""
    if week <= 6:
        return (0, 18, [0, 10])
    if week <= 13:
        return (-22, 44, [-20, 0, 20, 40])
    return (-42, 92, [-40, -20, 0, 20, 40, 60, 80])


def weeks_for(week):
    if week <= 6:
        return [1, 5]
    if week <= 13:
        return [1, 5, 10]
    if week <= 22:
        return [1, 5, 10, 15, 20]
    return [1, 10, 20, 30]


def game_graph(doc, week, gy=84, gh=350, layers=("areal", "vei", "inn", "lev", "lager"), new=(), role="Grossist",
               typed=None, yrange=None, labels=True, x=40, w=238):
    lo, hi, yt = yrange or yd(week)
    sc = Sc(x, gy, w, gh, week, lo, hi)
    out = axes(sc, weeks_for(week), yt)
    out += plot(doc, sc, layers, role=role, new=new)
    if labels:
        items = std_labels(sc, week, layers, role, new)
        if typed is not None:
            top = S[role]["paa_vei"][week - 1] + typed
            xr = sc.X(week)
            out.append(L(xr, sc.Y(S[role]["paa_vei"][week - 1]), xr, sc.Y(top), VER, 3))
            items.append((top, "Med ordren", num(top), VER))
        out += endlabels(sc, items, 13)
    return out, sc


def head(week, right="Alle tall"):
    return [T(20, 62, f"Uke {week}", 17, 700), T(370, 62, right, 15, 400, INK, "end", u=True)]
