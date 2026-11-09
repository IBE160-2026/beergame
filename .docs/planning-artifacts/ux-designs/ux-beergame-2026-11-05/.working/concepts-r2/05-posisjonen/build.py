"""Konsept 05 Posisjon. Genererer alle SVG-er fra ../_shared/fixture.json.

Bruk: uv run python build.py [navn ...]
Ingen tall i grafer tastes inn for haand. Posisjonen regnes ut fra serien.
"""
import json
import sys
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
FX = json.loads((HERE.parent / "_shared" / "fixture.json").read_text(encoding="utf-8"))

ROLES = ["Detaljist", "Grossist", "Distributør", "Fabrikk"]
NAVN = {"Detaljist": "Ida", "Grossist": "Sara", "Distributør": "Mikkel", "Fabrikk": "Jonas"}

# Palett: hvitt, svart, en klar roed, en graa (med to rastertoner av samme graa).
PAPER = "#FFFFFF"
INK = "#101010"
GRAY = "#696969"
TINT = "#C4C4C4"
WASH = "#F1F1F1"
RED = "#E2001A"

FONT = "Archivo"
FAM = "'Archivo','Helvetica Neue',Helvetica,Arial,sans-serif"

# Bredder i em for Archivo 500, maalt med fontTools. Brukes bare til layout og linjebryting.
EM = {'A': 0.695, 'B': 0.702, 'C': 0.725, 'D': 0.731, 'E': 0.674, 'F': 0.611, 'G': 0.795, 'H': 0.734, 'I': 0.274,
      'J': 0.571, 'K': 0.677, 'L': 0.552, 'M': 0.846, 'N': 0.734, 'O': 0.785, 'P': 0.667, 'Q': 0.785, 'R': 0.722,
      'S': 0.67, 'T': 0.612, 'U': 0.728, 'V': 0.659, 'W': 0.938, 'X': 0.683, 'Y': 0.666, 'Z': 0.635, 'a': 0.55,
      'b': 0.579, 'c': 0.532, 'd': 0.579, 'e': 0.554, 'f': 0.293, 'g': 0.573, 'h': 0.573, 'i': 0.238, 'j': 0.236,
      'k': 0.528, 'l': 0.238, 'm': 0.86, 'n': 0.573, 'o': 0.583, 'p': 0.579, 'q': 0.579, 'r': 0.346, 's': 0.524,
      't': 0.305, 'u': 0.572, 'v': 0.516, 'w': 0.74, 'x': 0.529, 'y': 0.516, 'z': 0.503, 'æ': 0.894, 'ø': 0.583,
      'å': 0.55, 'Æ': 0.999, 'Ø': 0.785, 'Å': 0.695, ' ': 0.205, '.': 0.288, ',': 0.288, ':': 0.315, ';': 0.315,
      '-': 0.333, '−': 0.63, '–': 0.5, '+': 0.63, '=': 0.63, '×': 0.63, '(': 0.356, ')': 0.356, '/': 0.296,
      '%': 0.958, '?': 0.595, '!': 0.282, '«': 0.56, '»': 0.56, "'": 0.227, '"': 0.407, '&': 0.71, '@': 0.97,
      '_': 0.5, ' ': 0.205}
DIGIT = 0.578  # tabellsiffer


def tw(text, size, weight=400):
    factor = {400: 0.985, 500: 1.0, 600: 1.025, 700: 1.05}.get(weight, 1.0)
    return sum(DIGIT if c.isdigit() else EM.get(c, 0.58) for c in str(text)) * size * factor


def wrap(text, size, maxw, weight=400):
    lines, cur = [], ""
    for word in str(text).split(" "):
        test = (cur + " " + word).strip()
        if tw(test, size, weight) <= maxw or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def n(v):
    """Tall med norsk minus."""
    return str(v).replace("-", "−")


def kr(v):
    s = f"{float(v):,.2f}".replace(",", " ").replace(".", ",")
    return s


def kr0(v):
    return f"{float(v):,.0f}".replace(",", " ")


def ganger(v):
    return f"{float(v):.1f}".replace(".", ",") + "×"


def f1(v):
    return f"{float(v):.1f}".replace(".", ",")


class Doc:
    def __init__(self, name, w, h, title, desc):
        self.name, self.w, self.h, self.title, self.desc = name, w, h, title, desc
        self.o = []

    def raw(self, s):
        self.o.append(s)

    def t(self, x, y, text, size=15, w=400, fill=INK, anchor="start", prop=False, ls=None, under=False):
        attrs = f'x="{x:.2f}" y="{y:.2f}" font-size="{size}" font-weight="{w}" fill="{fill}"'
        if anchor != "start":
            attrs += f' text-anchor="{anchor}"'
        if ls is not None:
            attrs += f' letter-spacing="{ls}"'
        if under:
            attrs += ' text-decoration="underline"'
        cls = "d05-p" if prop else "d05-t"
        self.o.append(f'<text class="{cls}" {attrs}>{escape(str(text))}</text>')

    def para(self, x, y, text, size=15, maxw=300, w=400, fill=INK, lh=None):
        lh = lh or round(size * 1.38)
        for line in wrap(text, size, maxw, w):
            self.t(x, y, line, size, w, fill)
            y += lh
        return y

    def rect(self, x, y, w, h, fill=INK, stroke=None, sw=1, rx=0):
        s = f'<rect x="{x:.2f}" y="{y:.2f}" width="{max(w, 0):.2f}" height="{max(h, 0):.2f}" fill="{fill}"'
        if stroke:
            s += f' stroke="{stroke}" stroke-width="{sw}"'
        if rx:
            s += f' rx="{rx}"'
        self.o.append(s + "/>")

    def line(self, x1, y1, x2, y2, stroke=INK, sw=1):
        self.o.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{stroke}" stroke-width="{sw}"/>')

    def path(self, d, stroke=INK, sw=1.5, fill="none", join="miter"):
        self.o.append(f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="{join}"/>')

    def open(self, tx=0, ty=0, scale=1):
        self.o.append(f'<g transform="translate({tx:.2f} {ty:.2f}) scale({scale})">')

    def close(self):
        self.o.append("</g>")

    def save(self):
        css = (
            f"@import url('https://fonts.googleapis.com/css2?family={FONT}:wght@400;500;600;700&amp;display=swap');"
            f".d05-t{{font-family:{FAM};font-variant-numeric:tabular-nums lining-nums;}}"
            f".d05-p{{font-family:{FAM};font-variant-numeric:proportional-nums lining-nums;}}"
        )
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" font-family="{FAM}">'
            f"<title>{escape(self.title)}</title><desc>{escape(self.desc)}</desc><style>{css}</style>"
            f'<rect x="0" y="0" width="{self.w}" height="{self.h}" fill="{PAPER}"/>' + "".join(self.o) + "</svg>"
        )
        (HERE / f"{self.name}.svg").write_text(svg, encoding="utf-8")


# ----- Data -----
S17 = FX["spill17"]["serier"]
BARE = FX["bare_sara_teller_paa_vei"]
ALLE = FX["alle_teller_paa_vei"]
REPLAY = FX["replay_sara"]
KL = FX["klasse"]


def posisjon(ser, role):
    x = ser[role]
    return [x["lager"][i] - x["restordre"][i] + x["paa_vei"][i] for i in range(len(x["lager"]))]


POS = {r: posisjon(S17, r) for r in ROLES}
SARA = S17["Grossist"]
SP = POS["Grossist"]


def uke(week, role="Grossist", ser=S17):
    """Alle tall for en Rolle i en Uke (1-indeksert)."""
    x = ser[role]
    i = week - 1
    lager_for = x["lager"][i - 1] if i else 12
    d = {k: x[k][i] for k in ("ordre", "lager", "restordre", "innkommende_ordre", "levering", "paa_vei", "kost_sum")}
    d["posisjon"] = x["lager"][i] - x["restordre"][i] + x["paa_vei"][i]
    d["sendt"] = lager_for + d["levering"] - d["lager"]
    return d


def spill_posisjon(g):
    """Posisjon per Rolle for et Klassespill: 24 ved start, deretter Posisjon + Ordre − ny Ordre inn.

    Stemmer eksakt med spill17-serien (sjekkes ved oppstart).
    """
    out = {}
    for i, r in enumerate(ROLES):
        o = g["ordre"][r]
        p = [SP[0]]
        for t in range(1, len(o)):
            inn = S17["demand"][t] if i == 0 else (g["ordre"][ROLES[i - 1]][t - 2] if t >= 2 else 4)
            p.append(p[-1] + o[t - 1] - inn)
        out[r] = p
    return out


_check = spill_posisjon({"ordre": {r: S17[r]["ordre"] for r in ROLES}})
assert all(_check[r] == POS[r] for r in ROLES), "Posisjonsidentiteten stemmer ikke"
for _r in ROLES:
    _x = S17[_r]
    for _t in range(35):
        assert POS[_r][_t + 1] == POS[_r][_t] + _x["ordre"][_t] - _x["innkommende_ordre"][_t + 1]
assert uke(11)["posisjon"] == 3 and uke(11)["restordre"] == 13 and uke(11)["paa_vei"] == 16


# ----- Regnestykket: konseptets sentrale komponent -----
def eq_layout(rows, size, maxw=None, labels=None, label_size=13):
    """rows: liste av rader. Hver rad: liste med 4 celler (op, tall). Kolonnene deles, saa '+ 24' staar under '+ 16'."""
    def cellw(c, s):
        if not c or (c[0] == "" and c[1] == ""):
            return 0
        op, num = c[0], str(c[1])
        return (0.63 * s + 0.14 * s if op else 0) + max(len(num), 1) * DIGIT * s

    gap = 0.17
    def total(s):
        widths = [max(cellw(r[i], s) for r in rows) for i in range(len(rows[0]))]
        if labels:
            for lr in labels:
                if lr:
                    for i, lab in enumerate(lr[:-1]):
                        if lab:
                            widths[i] = max(widths[i], tw(lab, label_size) + 10 - gap * s)
        return widths, sum(widths) + gap * s * (len(widths) - 1)

    widths, tot = total(size)
    if maxw and tot > maxw:
        size = size * maxw / tot
        widths, tot = total(size)
    xs, x = [], 0
    for w_ in widths:
        xs.append(x)
        x += w_ + gap * size
    return xs, size, tot


def draw_eq(d, x, y, rows, labels, size, maxw=None, row_h=None, label_size=13, weight=500, label_fill=GRAY, label_gap=None, red=None, caret=None, label_dx=0):
    """Tegner regnestykket. red=(rad, kol) gir det ene roede tallet. caret=(rad, kol) gir et inputfelt i tallet."""
    xs, size, tot = eq_layout(rows, size, maxw, labels, label_size)
    row_h = row_h or size * 1.62
    label_gap = label_gap if label_gap is not None else max(label_size + 7, size * 0.40)
    for ri, row in enumerate(rows):
        yy = y + ri * row_h
        for ci, cell in enumerate(row):
            if not cell:
                continue
            op, num = cell[0], str(cell[1])
            cx = x + xs[ci]
            nx = cx + (0.77 * size if op else 0)
            if op:
                d.t(cx, yy, op, size, 400, INK)
            col = RED if red == (ri, ci) else INK
            if num:
                d.t(nx, yy, num, size, weight, col, ls=f"{-0.01 * size:.2f}")
            if caret == (ri, ci):
                nw = max(len(num), 2) * DIGIT * size
                d.rect(nx, yy + size * 0.11, nw, 2.2, INK)
                d.rect(nx + len(num) * DIGIT * size + 2, yy - size * 0.72, 1.8, size * 0.78, INK)
            if labels and labels[ri] and labels[ri][ci]:
                d.t(cx + label_dx, yy + label_gap, labels[ri][ci], label_size, 400, label_fill)
    return xs, size, tot


def eq_row(a, b, c, r):
    return [("", a), ("−", b), ("+", c), ("=", r)]


def eq_u(week, role="Grossist", ser=S17):
    u = uke(week, role, ser)
    return eq_row(u["lager"], u["restordre"], u["paa_vei"], u["posisjon"])


EQ_LABELS = ["Lager", "Restordre", "På vei", "Posisjon"]


def eq_ordre(pos, ordre, tegnet=None):
    res = pos + (ordre or 0)
    return [None, ("", pos), ("+", ordre if ordre is not None else ""), ("=", n(res))]


ORDRE_LABELS = [None, "Posisjon", "Ordre", "Etter ordre"]


# ----- Grafer -----
def bars(d, x, y, w, h, vals, vmin, vmax, ppw=None, color=INK, add=None, add_color=RED, labels=None, bw=None,
         label_size=13, baseline=True, hollow=None, base_color=INK, label_w=500):
    """Soeyler fra sann null. Hoeyre kant er naa. ppw gir felles tidsskala mellom grafer."""
    N = len(vals)
    ppw = ppw or w / N
    bw = bw or max(1.5, min(ppw * 0.62, 18))
    scale = h / (vmax - vmin)
    yz = y + vmax * scale
    xend = x + w

    def bx(i):
        return xend - (N - i) * ppw + (ppw - bw) / 2

    if baseline:
        left = xend - N * ppw
        d.line(left, yz, xend, yz, base_color, 1)
    for i, v in enumerate(vals):
        bh = abs(v) * scale
        if hollow and i in hollow:
            d.rect(bx(i) + 0.5, (yz - bh if v >= 0 else yz) + 0.5, bw - 1, max(bh - 1, 0), PAPER, INK, 1)
        else:
            d.rect(bx(i), yz - bh if v >= 0 else yz, bw, bh, color)
    if add:
        i = N - 1
        v = vals[i]
        d.rect(bx(i), yz - (v + add) * scale, bw, add * scale, add_color)
    if labels:
        for i, text in labels.items():
            top = vals[i] + (add if add and i == N - 1 else 0)
            d.t(bx(i) + bw / 2, yz - max(top, 0) * scale - 7, text, label_size, label_w, INK, "middle")
    return bx, yz, scale, bw


def axis_now(d, x, w, y, venstre="Uke 1", hoyre="nå", size=13):
    if venstre:
        d.t(x, y, venstre, size, 400, GRAY)
    d.t(x + w, y, hoyre, size, 600, INK, "end")


def steps(d, x, y, w, h, vals, vmax, ppw, color=INK, sw=1.8, vmin=0):
    """Trappelinje, hoeyre kant er naa."""
    N = len(vals)
    xend = x + w
    scale = h / (vmax - vmin)
    yz = y + h + vmin * scale
    p = []
    for i, v in enumerate(vals):
        x0 = xend - (N - i) * ppw
        yy = yz - v * scale
        p.append(("M" if i == 0 else "L") + f"{x0:.1f} {yy:.1f}")
        p.append(f"L{x0 + ppw:.1f} {yy:.1f}")
    d.path("".join(p), color, sw)
    return yz, scale


def balance_fill(d, x, y, w, h, a, b, vmax, ppw):
    """Arealet mellom to trappelinjer per uke. Over: raster. Under: lys rute."""
    N = len(a)
    xend = x + w
    scale = h / vmax
    yz = y + h
    for i in range(N):
        x0 = xend - (N - i) * ppw
        top, bot = max(a[i], b[i]), min(a[i], b[i])
        if a[i] == b[i]:
            continue
        d.rect(x0, yz - top * scale, ppw, (top - bot) * scale, TINT if a[i] > b[i] else WASH)


def stacked(d, x, y, w, h, role_ser, week, vmin, vmax, ppw, labels=True, label_size=13):
    """Lager og Paa vei over null, Restordre under, Posisjon som en strek. Saldoen kan leses av."""
    lager, rest, pv = role_ser["lager"][:week], role_ser["restordre"][:week], role_ser["paa_vei"][:week]
    scale = h / (vmax - vmin)
    yz = y + vmax * scale
    xend = x + w
    bw = max(2, ppw * 0.72)
    d.line(xend - week * ppw, yz, xend, yz, INK, 1)
    for i in range(week):
        bx = xend - (week - i) * ppw + (ppw - bw) / 2
        # lager nederst, paa vei paa toppen
        d.rect(bx, yz - lager[i] * scale, bw, lager[i] * scale, INK)
        d.rect(bx, yz - (lager[i] + pv[i]) * scale, bw, max(pv[i] * scale - 0.0, 0), TINT)
        d.rect(bx, yz, bw, rest[i] * scale, GRAY)
    # Posisjon som tynn svart strek med hvit ring
    for i in range(week):
        bx = xend - (week - i) * ppw + (ppw - bw) / 2
        py = yz - (lager[i] - rest[i] + pv[i]) * scale
        d.rect(bx - 1, py - 1.6, bw + 2, 3.2, PAPER)
        d.rect(bx - 1, py - 0.8, bw + 2, 1.6, INK)
    return yz, scale


# ----- Telefon og felles spillskjerm -----
def phone_frame(d, x, y, scale=1.0):
    d.open(x, y, scale)
    d.rect(0, 0, 390, 844, PAPER, TINT, 1, rx=30)


def backspace(d, cx, cy):
    d.path(f"M{cx - 10} {cy}L{cx - 4} {cy - 7}H{cx + 10}V{cy + 7}H{cx - 4}Z", INK, 1.4)
    d.path(f"M{cx - 1} {cy - 3}L{cx + 5} {cy + 3}M{cx + 5} {cy - 3}L{cx - 1} {cy + 3}", INK, 1.4)


def keys(d, y, h=54):
    d.rect(0, y, 390, h, WASH)
    kw = (390 - 16) / 11
    for i, c in enumerate("1234567890"):
        d.t(8 + kw * i + kw / 2, y + h / 2 + 7, c, 20, 500, INK, "middle")
    backspace(d, 8 + kw * 10 + kw / 2, y + h / 2)


def button(d, x, y, w, h, text, primary=True, size=16, enabled=True):
    if primary and enabled:
        d.rect(x, y, w, h, INK)
        d.t(x + w / 2, y + h / 2 + size * 0.36, text, size, 600, PAPER, "middle")
    else:
        d.rect(x + 0.5, y + 0.5, w - 1, h - 1, PAPER, INK if enabled else TINT, 1)
        d.t(x + w / 2, y + h / 2 + size * 0.36, text, size, 500, INK if enabled else GRAY, "middle")


def head_play(d, role="Grossist", week=11, extra=None):
    d.t(20, 62, f"{role}, Spill 17", 15, 600)
    d.t(370, 62, f"Uke {week}", 15, 600, INK, "end")
    if extra:
        d.t(20, 84, extra, 13, 400, GRAY)


def play_main(d, week=11, typed=24, state="typed", ser_role="Grossist"):
    """Hovedskjermen paa telefon. state: open, typed, locked."""
    u = uke(week, ser_role)
    head_play(d, ser_role, week)
    pos = u["posisjon"]
    rows = [eq_u(week, ser_role), eq_ordre(pos, typed)]
    labels = [EQ_LABELS, ORDRE_LABELS]
    caret = (1, 2) if state in ("open", "typed") else None
    draw_eq(d, 20, 142, rows, labels, 52, maxw=350, row_h=92, red=(1, 3), caret=caret)
    vals = POS[ser_role][:week]
    ymax = max(28, max(vals), vals[-1] + (typed or 0)) * 1.04
    lab = {0: n(vals[0]), week - 1: n(vals[-1]) if not typed else n(pos + typed)}
    bars(d, 20, 300, 350, 226, vals, 0, ymax, add=typed or None, labels=lab)
    axis_now(d, 20, 350, 548)
    return u


def status_lines(d, y, u):
    d.t(20, y, "Ordre inn", 13, 400, GRAY)
    d.t(20 + tw("Ordre inn ", 13), y, u["innkommende_ordre"], 15, 600)
    x2 = 118
    d.t(x2, y, "Levering", 13, 400, GRAY)
    d.t(x2 + tw("Levering ", 13), y, u["levering"], 15, 600)
    d.t(370, y, "Alle tall", 14, 500, INK, "end", under=True)


def screen_decide(d, typed=24, state="typed"):
    u = play_main(d, 11, typed, state)
    status_lines(d, 590, u)
    d.t(20, 616, "Venter på deg og Jonas, Fabrikk, 3 min", 13, 400, GRAY)
    keys(d, 640)
    if typed:
        button(d, 20, 708, 350, 56, f"Bekreft ordre {typed}")
    else:
        button(d, 20, 708, 350, 56, "Bekreft ordre", primary=False, enabled=False)
    d.t(20, 790, "Kan ikke endres etter bekreftelse.", 13, 400, GRAY)


def equation_lines(d, x, y, w, week=11):
    """Alle tall som regnestykker: inn minus ut, for hver beholdning."""
    u, p = uke(week), uke(week - 1)
    o_for = p["ordre"]
    linjer = [
        ("Lager", f"{p['lager']} + {u['levering']} − {u['sendt']}", u["lager"], "Levert inn, sendt ut"),
        ("Restordre", f"{p['restordre']} + {u['innkommende_ordre']} − {u['sendt']}", u["restordre"], "Ordre inn, sendt ut"),
        ("På vei", f"{p['paa_vei']} + {o_for} − {u['levering']}", u["paa_vei"], "Bestilt i Uke %d, levert nå" % (week - 1)),
        ("Posisjon", f"{p['posisjon']} + {o_for} − {u['innkommende_ordre']}", u["posisjon"], "Bestilt, ordre inn"),
    ]
    yy = y
    for lab, expr, res, note in linjer:
        d.t(x, yy, lab, 13, 400, GRAY)
        d.t(x, yy + 26, f"{expr} = {res}", 22, 500)
        d.t(x + w, yy + 26, note, 13, 400, GRAY, "end")
        yy += 56
    return yy


def sheet_alle(d, week=11):
    """Panelet bak ett trykk."""
    u, p = uke(week), uke(week - 1)
    d.t(20, 62, f"Uke {week}, alle tall", 15, 600)
    d.t(370, 62, "Lukk", 14, 500, INK, "end", under=True)
    yy = equation_lines(d, 20, 104, 350, week)
    # Kostnad
    d.t(20, yy, "Totalkostnad", 13, 400, GRAY)
    d.t(20, yy + 26, f"{kr(p['kost_sum'])} + {u['restordre']} × 1,00 + {u['lager']} × 0,50 = {kr(u['kost_sum'])} kr", 17, 500)
    yy += 64
    d.t(20, yy, "Neste levering", 13, 400, GRAY)
    d.t(20, yy + 26, uke(week + 1)["levering"], 22, 500)
    d.t(370, yy + 26, "Ikke garantert: leverandøren kan mangle varer", 13, 400, GRAY, "end")
    yy += 64
    d.t(20, yy, "Ordrene dine, Uke 1 til %d" % (week - 1), 13, 400, GRAY)
    o = SARA["ordre"][: week - 1]
    cw = 350 / 10
    for i, v in enumerate(o):
        h = v * 2.6
        d.rect(20 + i * cw, yy + 44 - h, cw * 0.5, h, INK)
        d.t(20 + i * cw, yy + 62, v, 13, 400)
    yy += 96
    d.t(20, yy, "Uka venter på", 13, 400, GRAY)
    rad = [("Ida, Detaljist", "har bestilt"), ("Mikkel, Distributør", "har bestilt"), ("Jonas, Fabrikk", "venter, 3 min"), ("Sara, Grossist (deg)", "venter")]
    yy += 24
    for a, b in rad:
        vent = "venter" in b
        d.t(20, yy, a, 15, 600 if vent else 400)
        d.t(370, yy, b, 15, 600 if vent else 400, INK, "end")
        yy += 25


def demodata(d, x, y, extra=""):
    d.t(x, y, "Demodata" + extra, 13, 400, GRAY)


# ----- 05 Hovedskjermen -----
def page_05():
    d = Doc("05-spill", 1600, 1000, "Posisjon: hovedskjermen", "Telefon i Uke 11 med 24 tastet inn, åpnet panel med alle tall, laptop, og det som låses opp i Replay.")
    d.t(40, 56, "Ligningen er grensesnittet", 34, 500, ls="-0.5")
    d.t(1560, 56, "Sara, Grossist, Spill 17, Uke 11. Demodata", 14, 400, GRAY, "end")
    phone_frame(d, 40, 96, 1)
    screen_decide(d)
    d.close()
    phone_frame(d, 462, 96, 1)
    sheet_alle(d)
    d.close()

    # Laptop
    lx, ly, lw, lh = 884, 96, 676, 432
    d.rect(lx, ly, lw, lh, PAPER, TINT, 1, rx=8)
    d.open(lx, ly)
    u = uke(11)
    d.t(28, 38, "Grossist, Spill 17", 14, 600)
    d.t(lw - 28, 38, "Uke 11", 14, 600, INK, "end")
    draw_eq(d, 28, 118, [eq_u(11), eq_ordre(u["posisjon"], 24)], [EQ_LABELS, ORDRE_LABELS], 52, maxw=396, row_h=96, red=(1, 3), caret=(1, 2), label_gap=22)
    bars(d, 28, 278, 396, 112, SP[:11], 0, 30, add=24, labels={0: "24", 10: "27"}, bw=16)
    axis_now(d, 28, 396, 410)
    # Hoeyrekolonne
    rx = 452
    pairs = [("Ordre inn", u["innkommende_ordre"]), ("Levering", u["levering"]), ("Sendt", u["sendt"]), ("Neste levering", uke(12)["levering"]), ("Totalkostnad", kr(u["kost_sum"]) + " kr")]
    yy = 72
    for a, b in pairs:
        d.t(rx, yy, a, 13, 400, GRAY)
        d.t(lw - 28, yy, b, 15, 500, INK, "end")
        yy += 25
    d.t(rx, yy + 14, "Levering er ikke garantert.", 13, 400, GRAY)
    d.t(rx, yy + 58, "Venter på", 13, 400, GRAY)
    d.t(rx, yy + 80, "deg", 15, 600)
    d.t(rx, yy + 102, "Jonas, Fabrikk, 3 min", 15, 400)
    d.t(rx, yy + 124, "Ida og Mikkel har bestilt", 13, 400, GRAY)
    button(d, rx, 346, lw - 28 - rx, 46, "Bekreft ordre 24", size=15)
    d.t(rx, 410, "Kan ikke endres etterpå.", 13, 400, GRAY)
    d.close()

    # Under laptopen: Hjelpegrad
    x0 = 884
    d.t(x0, 576, "Det samme regnestykket, to hjelpegrader", 22, 500)
    d.para(x0, 606, "I Klassespillet står bare aritmetikken på skjermen. I Replay, etter Debriefen, kan Sara åpne hvordan tallet ble til, uke for uke.", 15, 640)
    # Klassespill-kolonnen
    d.t(x0, 672, "Klassespill", 14, 600)
    d.para(x0, 694, "Regnestykket og søylene. Ingen målstrek, ingen fasit, ingen forklaring av hva tallet burde være.", 13, 280, fill=GRAY, lh=18)
    bars(d, x0, 760, 280, 130, SP[:11], 0, 30, add=24, labels={10: "27"}, bw=12)
    axis_now(d, x0, 280, 912)
    d.t(x0, 940, "3 + 24 = 27", 22, 500)
    # Replay-kolonnen
    x1 = 1220
    w_r = 340
    rw = 12
    d.t(x1, 672, "Replay", 14, 600)
    d.para(x1, 694, "Tallene deles opp: Lager svart, På vei grå, Restordre under null. Streken er Posisjonen, og den avstemmes mot neste uke. Tilfeldig etterspørsel og tre KI-spillere, så ikke like for like.", 13, w_r, fill=GRAY, lh=18)
    ser = REPLAY["serier"]["Grossist"]
    ppw = w_r / 18
    stacked(d, x1, 760, w_r, 130, ser, rw + 6, -14, 42, ppw)
    wk = rw + 6
    rv = uke(wk, "Grossist", REPLAY["serier"])
    d.t(x1, 912, "Uke 1", 13, 400, GRAY)
    d.t(x1 + w_r, 912, "nå", 13, 600, INK, "end")
    nxt = uke(wk + 1, "Grossist", REPLAY["serier"])
    d.t(x1, 940, f"{rv['posisjon']} + {rv['ordre']} − {nxt['innkommende_ordre']} = {nxt['posisjon']}", 22, 500)
    d.t(x1 + w_r, 940, "Avstemt mot Uke %d" % (wk + 1), 13, 400, GRAY, "end")
    d.save()


# ----- 10 Pedagogikk -----
def page_10():
    d = Doc("10-pedagogikk", 2000, 1400, "Posisjon: grafgrammatikken", "Samme regnestykke og samme grafer for Sara ved Uke 5, 11, 18 og 29, og sammenligning med simulert referanse etter Debriefen.")
    X = [340, 750, 1160, 1570]
    CW = 370
    UKER = [5, 11, 18, 29]
    PPW = CW / 29

    d.t(60, 78, "Hele spillet er ett regnestykke", 54, 500, ls="-0.9")
    d.para(1160, 52, "Lager minus Restordre pluss På vei er Posisjonen. Tallene i ligningen er de samme som i grafen. Sara, Grossist, Spill 17. Samme tidsskala og samme høyde i alle fire kolonner.", 15, 620)
    d.t(1160, 98, "Demodata", 13, 400, GRAY)

    def head(y, title, tags, text, unlock=False):
        d.t(60, y, title, 17, 600)
        d.t(60, y + 22, tags, 13, 600, INK)
        d.para(60, y + 44, text, 13, 240, fill=GRAY, lh=18)

    for x, w in zip(X, UKER):
        d.t(x, 162, f"Uke {w}", 22, 600)

    # A: Regnestykket
    head(196, "Regnestykket", "P3", "Det som er på vei står i ligningen, med samme vekt som lageret. Den andre linjen viser hva ordren gjør, og ingenting mer.")
    SIZE = 45
    for x, w in zip(X, UKER):
        u = uke(w)
        draw_eq(d, x, 232, [eq_u(w), eq_ordre(u["posisjon"], u["ordre"])], [EQ_LABELS, ORDRE_LABELS], SIZE, maxw=CW, row_h=76, red=(1, 3), label_gap=21)

    # B: Soeylene
    y_b, h_b = 396, 190
    head(y_b, "Posisjonen over tid", "P3", "Søylene er siste tall i ligningen, uke for uke. Etter 3 i Uke 10 og 11 fylles hullet, og Posisjonen går langt forbi der den startet.")
    for x, w in zip(X, UKER):
        vals = SP[:w]
        u = uke(w)
        # mest utslag for merket: forste og siste
        lab = {w - 1: n(u["posisjon"] + u["ordre"])}
        if w > 1:
            lab[0] = n(vals[0])
        if w >= 18:
            imin = min(range(w - 1), key=lambda i: vals[i])
            lab[imin] = n(vals[imin])
        bars(d, x, y_b, CW, h_b, vals, 0, 62, ppw=PPW, add=u["ordre"], labels=lab, bw=PPW * 0.66)
        axis_now(d, x, CW, y_b + h_b + 19, venstre=None)

    innsikt = {
        5: f"Fem uker med samme tall. Inn og ut er like, {uke(5)['innkommende_ordre']} og {uke(5)['ordre']}, så Posisjonen står stille på {uke(5)['posisjon']}.",
        11: f"Restordre {uke(11)['restordre']} roper høyest, men {uke(11)['paa_vei']} er på vei. Regnestykket sier {uke(11)['posisjon']}. Med {uke(11)['ordre']} blir det {uke(11)['posisjon'] + uke(11)['ordre']}.",
        18: f"Lager {uke(18)['lager']} og Restordre {uke(18)['restordre']} føles som krise. Med {uke(18)['paa_vei']} på vei er Posisjonen {uke(18)['posisjon']}, og {uke(18)['ordre']} legges på toppen.",
        29: f"Lager {uke(29)['lager']} er det som ble bestilt i ukene med mangel. Bare {uke(29)['paa_vei']} er igjen på vei, og Posisjonen er {uke(29)['posisjon']}.",
    }
    d.t(60, y_b + h_b + 46, "Innsikt for neste ordre", 17, 600)
    for x, w in zip(X, UKER):
        d.para(x, y_b + h_b + 46, innsikt[w], 15, CW - 10, lh=20)

    # Skille: Laases opp
    y_u = 690
    d.line(60, y_u, 1940, y_u, INK, 1)
    d.t(60, y_u + 28, "Låses opp etter Debriefen", 17, 600)
    d.t(340, y_u + 28, "I Klassespillet ser Sara alt over denne streken. I Replay kan hen åpne det som står under.", 15, 400, GRAY)

    # C: Oppdeling
    y_c, h_c = 754, 164
    head(y_c, "Hva tallet består av", "P1, P3", "Lager (svart) og På vei (grå) over null, Restordre under. Streken er Posisjonen: over minus under.")
    vmax, vmin = 92, -42
    for x, w in zip(X, UKER):
        yz, sc = stacked(d, x, y_c, CW, h_c, SARA, w, vmin, vmax, PPW)
        u = uke(w)
        tx = x + CW - w * PPW - 8
        if w >= 18:
            # direkte etiketter for den siste uka, til venstre for soeylene der det er plass
            pass
    # direkte etiketter i Uke 5-kolonnen, der det er tomt til venstre
    u5 = uke(5)
    x5r = X[0] + CW - 5 * PPW - 10
    yz5 = y_c + vmax * h_c / (vmax - vmin)
    sc5 = h_c / (vmax - vmin)
    d.t(x5r, yz5 - (u5["lager"] + u5["paa_vei"]) * sc5 + 12, "På vei", 13, 400, GRAY, "end")
    d.t(x5r, yz5 - u5["lager"] * sc5 / 2 + 5, "Lager", 13, 400, INK, "end")
    d.t(x5r, yz5 + 16, "Restordre under null", 13, 400, GRAY, "end")
    for x, w in zip(X[1:], UKER[1:]):
        u = uke(w)
        tx = x + CW
        yy = yz5 + 34
        # lesbar sum under grafen
    for x, w in zip(X, UKER):
        u = uke(w)
        d.t(x, y_c + h_c + 20, f"{u['paa_vei'] + u['lager']} over, {u['restordre']} under, Posisjon {u['posisjon']}", 13, 500)

    # D: Balansen
    y_d, h_d = 956, 96
    head(y_d, "Inn og ut", "P1, P4", "Ordre ut og Ordre inn. Rutene mellom linjene er endringen i Posisjon: mørk når den stiger, lys når den synker. Ordre inn er ikke kundenes etterspørsel.")
    for x, w in zip(X, UKER):
        o, inn = SARA["ordre"][:w], SARA["innkommende_ordre"][:w]
        balance_fill(d, x, y_d, CW, h_d, o, inn, 30, PPW)
        steps(d, x, y_d, CW, h_d, inn, 30, PPW, GRAY, 1.4)
        steps(d, x, y_d, CW, h_d, o, 30, PPW, INK, 1.8)
        d.line(x + CW - w * PPW, y_d + h_d, x + CW, y_d + h_d, INK, 1)
        if w < 36:
            u, nx = uke(w), uke(w + 1)
            d.t(x, y_d + h_d + 20, f"{u['posisjon']} + {u['ordre']} − {nx['innkommende_ordre']} = {nx['posisjon']}", 15, 500)
            d.t(x + CW, y_d + h_d + 20, f"Uke {w + 1} stemmer", 13, 400, GRAY, "end")
    xr = X[0] + CW - 5 * PPW - 8
    d.t(xr, y_d + h_d - 40, "Ordre ut", 13, 600, INK, "end")
    d.t(xr, y_d + h_d - 22, "Ordre inn", 13, 400, GRAY, "end")

    # E: Forsinkelsen
    y_e, h_e = 1096, 70
    d.t(60, y_e, "Bestilt og levert", 17, 600)
    d.t(60, y_e + 22, "P2", 13, 600)
    d.para(60, y_e + 44, "Søyler: levert. Linje: bestilt. Det du ser nå kommer av det du gjorde før.", 13, 240, fill=GRAY, lh=18)
    for x, w in zip(X, UKER):
        lev = SARA["levering"][:w]
        bars(d, x, y_e, CW, h_e, lev, 0, 34, ppw=PPW, color=GRAY, bw=PPW * 0.5)
        steps(d, x, y_e, CW, h_e, SARA["ordre"][:w], 34, PPW, INK, 1.6)
        if w >= 18:
            bestilt, levert = uke(11)["ordre"], uke(15)["levering"]
            d.t(x, y_e + h_e + 20, f"{bestilt} bestilt i Uke 11, {levert} levert i Uke 15", 13, 500)

    # Referanse
    y_r = 1216
    d.line(60, y_r, 1940, y_r, INK, 1)
    d.t(60, y_r + 28, "Etter Debriefen: Simulert", 17, 600)
    d.t(60, y_r + 50, "P5, P6, P7, P8", 13, 600)
    d.para(60, y_r + 72, "Samme etterspørsel, samme kjede. Viser sammenhengen, ikke en fasit.", 13, 240, fill=GRAY, lh=18)
    refs = [
        ("Spill 17, slik det ble", S17, FX["spill17"]),
        ("Simulert: bare Sara teller alt på vei", BARE["serier"], BARE),
        ("Simulert: alle fire teller, rolig regel", ALLE["serier"], ALLE),
    ]
    for x, (name, ser, full) in zip(X, refs):
        d.t(x, y_r + 28, name, 15, 600)
        vals = posisjon(ser, "Grossist")
        bars(d, x, y_r + 38, CW, 70, vals, 0, 72, ppw=CW / 36, bw=CW / 36 * 0.66)
        d.t(x, y_r + 132, f"Grossist {kr(full['kost_per_rolle']['Grossist'])} kr", 15, 500)
        d.t(x, y_r + 152, f"Kjeden {kr(full['kjedekost'])} kr", 13, 400, GRAY)
        d.t(x + CW, y_r + 132, ganger(full["forsterkning"]["Grossist"]), 15, 500, INK, "end")
        d.t(x + CW, y_r + 152, "Forsterkning, Grossist", 13, 400, GRAY, "end")
    xn = X[3]
    f = FX["spill17"]["forsterkning"]
    yy = d.para(xn, y_r + 26, "Å telle det som er på vei er ikke nok. I simuleringen ga en regel som jaget siste ordre for hardt, Fabrikk 12×, mer enn Spill 17. Rolig tilpasning og telling må til sammen.", 14, CW, lh=18)
    yy = d.para(xn, yy + 4, f"Forsterkning, Detaljist til Fabrikk: {ganger(f['Detaljist'])}, {ganger(f['Grossist'])}, {ganger(f['Distributør'])}, {ganger(f['Fabrikk'])}. Median for Fabrikk i klassen er {ganger(KL['ferdige']['forsterkning_per_rolle']['Fabrikk']['median'])}: strukturen gjør dette, ikke personene.", 14, CW, lh=18)
    d.para(xn, yy + 4, "Restordre koster 1,00, lager 0,50. Målet er lavest kostnad for hele kjeden.", 14, CW, lh=18)
    d.save()


# ----- 06 Spilldynamikk -----
def wait_list(d, y):
    rad = [("Ida, Detaljist", "har bestilt", False), ("Mikkel, Distributør", "har bestilt", False),
           ("Sara, Grossist (deg)", "har bestilt", False), ("Jonas, Fabrikk", "venter, 3 min", True)]
    for a, b, vent in rad:
        d.t(20, y, a, 15, 600 if vent else 400)
        d.t(370, y, b, 15, 600 if vent else 400, INK, "end")
        y += 28
    return y


def page_06():
    d = Doc("06-spilldynamikk", 2100, 1200, "Posisjon: spilldynamikk", "Seks telefonruter gjennom en Uke og slutten av spillet.")
    d.t(50, 62, "En Uke, seks tilstander", 34, 500, ls="-0.5")
    d.t(2050, 62, "Demodata", 13, 400, GRAY, "end")
    SC = 0.8
    W = 390 * SC
    xs = [50 + i * (W + (2000 - 6 * W) / 5) for i in range(6)]
    y0 = 92
    titler = ["Uka åpner", "Beslutningen", "Bekreftet", "Uka går videre", "Jonas er borte", "Spillet slutter"]
    notater = [
        "Regnestykket er satt før Sara rører noe. Uten ordre er svaret fortsatt 3.",
        "24 med 16 på vei: tallet skrives inne i ligningen, og søylen vokser mens hen taster. Ingen anbefaling.",
        "Ordren er låst. Skjermen sier hvem Uka venter på, med Rolle, navn og tid, aldri bare en farge.",
        "27 minus ny Ordre inn er 16, og den nye ligningen gir også 16. To veier til samme tall. Kan hoppes over, aldri over 2 sek.",
        "Pause er avtalt, tiden gikk ut, og en KI-spiller sitter i setet. Uker med KI er hule søyler merket med tekst.",
        "Kjedens Totalkostnad først, så hver Rolle. Summen kan regnes etter. Etterspørselen er fortsatt skjult.",
    ]
    # A
    for i, x in enumerate(xs):
        d.t(x, y0 + 14, titler[i], 17, 600)
    yp = y0 + 30
    phone_frame(d, xs[0], yp, SC)
    screen_decide(d, typed=None, state="open")
    d.close()
    phone_frame(d, xs[1], yp, SC)
    screen_decide(d, typed=24)
    d.close()
    # C
    phone_frame(d, xs[2], yp, SC)
    u = play_main(d, 11, 24, "locked")
    status_lines(d, 590, u)
    d.t(20, 628, "Uka venter på", 13, 400, GRAY)
    wait_list(d, 654)
    d.t(20, 790, "Ordre 24 er bekreftet og kan ikke endres.", 13, 400, GRAY)
    d.close()
    # D
    phone_frame(d, xs[3], yp, SC)
    u12, u11 = uke(12), uke(11)
    head_play(d, "Grossist", 12)
    rows = [[None, ("", u11["posisjon"] + u11["ordre"]), ("−", u12["innkommende_ordre"]), ("=", u12["posisjon"])], eq_u(12)]
    assert u11["posisjon"] + u11["ordre"] - u12["innkommende_ordre"] == u12["posisjon"]
    draw_eq(d, 20, 142, rows, [[None, "Etter ordre", "Ordre inn", "Posisjon"], EQ_LABELS], 52, maxw=350, row_h=92, red=(1, 3))
    vals = SP[:12]
    bars(d, 20, 300, 350, 226, vals, 0, 28 * 1.04, labels={0: n(vals[0]), 11: n(vals[-1])})
    axis_now(d, 20, 350, 548)
    d.t(20, 590, "Ordre inn", 13, 400, GRAY)
    d.t(20 + tw("Ordre inn ", 13), 590, u12["innkommende_ordre"], 15, 600)
    d.t(118, 590, "Levering", 13, 400, GRAY)
    d.t(118 + tw("Levering ", 13), 590, u12["levering"], 15, 600)
    d.t(195, 700, "Hopp over", 16, 500, INK, "middle", under=True)
    d.close()
    # E
    phone_frame(d, xs[4], yp, SC)
    head_play(d, "Fabrikk", 14)
    d.t(20, 92, "KI-spiller sitter i setet ditt nå", 15, 600)
    rows = [eq_u(14, "Fabrikk")]
    draw_eq(d, 20, 170, rows, [EQ_LABELS], 52, maxw=350, red=(0, 3))
    vals = POS["Fabrikk"][:14]
    ki = {11, 12, 13}
    bx, yz, sc, bw = bars(d, 20, 240, 350, 170, vals, 0, 36, hollow=ki, labels={0: n(vals[0]), 13: n(vals[-1])})
    d.t(370, 240 + 2, "KI-spiller", 13, 600, INK, "end")
    axis_now(d, 20, 350, 432)
    d.t(20, 476, "Dette bestilte KI-spilleren", 13, 400, GRAY)
    yy = 502
    for w in (12, 13):
        d.t(20, yy, f"Uke {w}", 15)
        d.t(370, yy, uke(w, "Fabrikk")["ordre"], 15, 600, INK, "end")
        yy += 26
    yy = d.para(20, yy + 20, "Dere satte Pause og avtalte en tid. Tiden gikk ut, og Mikkel satte inn en KI-spiller så gruppa kunne fortsette.", 14, 350, lh=20)
    d.para(20, yy + 6, "Uker med KI-spiller teller ikke som dine ordrer og kan påvirke kravet for å fullføre.", 13, 350, fill=GRAY, lh=18)
    button(d, 20, 708, 350, 56, "Ta tilbake setet")
    d.t(20, 790, "Gjelder fra neste Uke.", 13, 400, GRAY)
    d.close()
    # F
    phone_frame(d, xs[5], yp, SC)
    d.t(20, 62, "Grossist, Spill 17", 15, 600)
    d.t(370, 62, "Slutt", 15, 600, INK, "end")
    d.t(20, 112, "Kjedens Totalkostnad", 13, 400, GRAY)
    d.t(20, 166, kr(FX["spill17"]["kjedekost"]) + " kr", 48, 500, RED, prop=True, ls="-0.6")
    yy = 216
    for r in ROLES:
        me = r == "Grossist"
        d.t(20, yy, f"{r}, {NAVN[r]}" + (" (deg)" if me else ""), 15, 600 if me else 400)
        d.t(370, yy, kr(FX["spill17"]["kost_per_rolle"][r]), 15, 600 if me else 400, INK, "end")
        yy += 27
    assert abs(sum(FX["spill17"]["kost_per_rolle"].values()) - FX["spill17"]["kjedekost"]) < 0.01
    d.line(20, yy - 16, 370, yy - 16, INK, 1)
    d.t(20, yy + 4, "Sum", 15, 500)
    d.t(370, yy + 4, kr(FX["spill17"]["kjedekost"]), 15, 500, INK, "end")
    d.t(20, yy + 60, "Posisjonen din, hele spillet", 13, 400, GRAY)
    imax = max(range(36), key=lambda i: SP[i])
    imin = min(range(36), key=lambda i: SP[i])
    bars(d, 20, yy + 78, 350, 200, SP, 0, 60, labels={0: n(SP[0]), imin: n(SP[imin]), imax: n(SP[imax])}, bw=350 / 36 * 0.66)
    d.t(20, yy + 300, "Uke 1", 13, 400, GRAY)
    d.t(370, yy + 300, "Uke 36", 13, 400, GRAY, "end")
    button(d, 20, 708, 350, 56, "Videre til Debrief")
    d.t(20, 790, "Der ser du hva kundene faktisk bestilte.", 13, 400, GRAY)
    d.close()

    # Notater
    yn = yp + 844 * SC + 30
    for x, text in zip(xs, notater):
        d.para(x, yn, text, 15, W - 4, lh=20)
    # Hva spilleren laerer
    yb = 1040
    d.line(50, yb - 44, 2050, yb - 44, INK, 1)
    d.t(50, yb, "Hva spilleren lærer uke for uke", 17, 600)
    text = (f"I Uke {10} og 11 viser søylene {SP[9]}, og det føles som at noe må gjøres. Etter ordren på 24 stiger søylen uke etter uke "
            f"selv om lageret står på 0: {SP[11]}, {SP[12]}, {SP[13]}, {SP[14]}. Regnestykket forklarer det som skjer, for restordren gjør vondt nå, mens det du har bestilt bare er et tall i ligningen. "
            f"Sara kan se at Posisjonen hens er {SP[22]} i Uke 23, mens hen fortsatt har {uke(23)['restordre']} i restordre, og det er nok til å spørre hvorfor. Skjermen svarer aldri med hva hen burde bestilt.")
    d.para(420, yb - 2, text, 24, 1630, lh=34)
    d.save()


# ----- 07 Debrief -----
def tabellgraf(d, x, y, colw, rader, labelw, rowh=64, vmax=None, skala=44, tall=13, mark_uke=None, heads=True):
    """Tall som soeyler: et tall per Uke, med soeylen rett over tallet. rader: (etikett, verdier)."""
    vmax = vmax or max(max(v) for _, v in rader)
    x0 = x + labelw
    N = max(len(v) for _, v in rader)
    if mark_uke:
        d.rect(x0 + (mark_uke - 1) * colw, y - 18, colw, rowh * len(rader) + 20, WASH)
    if heads:
        for w in range(1, N + 1):
            if w == 1 or w % 5 == 0:
                d.t(x0 + (w - 1) * colw + colw / 2, y - 4, w, 12, 400, GRAY, "middle")
        d.t(x, y - 4, "Uke", 12, 400, GRAY)
    yy = y
    for lab, vals in rader:
        base = yy + rowh - 20
        d.t(x, base + 15, lab, 14 if tall >= 13 else 13, 500)
        peak = max(vals)
        first_peak = vals.index(peak)
        for i, v in enumerate(vals):
            cx = x0 + i * colw + colw / 2
            h = v * skala / vmax
            bw = colw * 0.5
            d.rect(cx - bw / 2, base - h, bw, h, INK)
            d.t(cx, base + 15, v, tall, 700 if i == first_peak and peak > 8 else 400, INK, "middle")
        d.line(x0, base, x0 + N * colw, base, INK, 1)
        yy += rowh
    return yy


def page_07():
    d = Doc("07-debrief", 2100, 1200, "Posisjon: Debrief", "Gruppedebrief i fem steg og delt skjerm. Forklaring først, så avsløres etterspørselen, så regnestykkene.")
    d.t(50, 58, "Debrief: først din Forklaring, så tallene", 34, 500, ls="-0.5")
    d.t(2050, 58, "Spill 17. Alle tall fra loggen. Demodata", 13, 400, GRAY, "end")

    def step(x, y, nr, title):
        d.t(x, y, f"Steg {nr}", 14, 400, GRAY)
        d.t(x + 52, y, title, 14, 600)

    # Steg 1
    x = 50
    y = 108
    step(x, y, 1, "Skriv Forklaring")
    imax = max(range(36), key=lambda i: SP[i])
    d.para(x, y + 40, f"Posisjonen din gikk fra {SP[10]} i Uke 11 til {SP[imax]} i Uke {imax + 1}. Hvorfor?", 24, 400, w=500, lh=31)
    d.rect(x + 0.5, y + 112.5, 400, 96, PAPER, INK, 1)
    d.para(x + 14, y + 138, "Restordren vokste, så jeg bestilte mer. Jeg regnet nok ikke med det som allerede var på vei.", 15, 370, lh=21)
    bars(d, x, y + 222, 400, 62, SP, 0, 60, bw=400 / 36 * 0.6, labels=None)
    button(d, x, y + 296, 170, 40, "Lever Forklaring", size=14)
    d.para(x + 184, y + 313, "Etterspørselen er låst til Forklaringen er levert.", 13, 216, fill=GRAY, lh=17)

    # Steg 2: klimaks
    x = 510
    step(x, y, 2, "Etterspørselen avsløres")
    d.t(x, y + 72, "Kundene bestilte 4, så ", 58, 500, prop=True, ls="-1")
    tx = x + tw("Kundene bestilte 4, så ", 58, 500) - 26
    d.t(tx, y + 72, S17["demand"][4], 58, 500, RED, prop=True)
    d.para(x, y + 108, "Etterspørselen endret seg én gang, i Uke 5, og lå fast resten av spillet. Alt annet du så, ble laget av kjeden selv. Øvelsen heter Beer Game, og nesten alle grupper svinger slik.", 15, 770, lh=21)
    tabellgraf(d, x, y + 170, 19.4, [("Kundene", S17["demand"]), ("Du", SARA["ordre"])], 90, rowh=74, vmax=max(SARA["ordre"]), skala=46, tall=12)

    # Delt skjerm
    x = 1330
    fw = 720
    d.rect(x + 0.5, 92.5, fw - 1, 340, PAPER, TINT, 1, rx=6)
    d.t(x + 22, 124, "Delt skjerm: fire regnestykker i Uke 11", 16, 600)
    d.t(x + fw - 22, 124, "Gruppa ser det samme", 13, 400, GRAY, "end")
    cw = (fw - 44 - 3 * 16) / 4
    for i, r in enumerate(ROLES):
        cx = x + 22 + i * (cw + 16)
        d.t(cx, 158, r, 14, 600)
        d.t(cx, 176, NAVN[r], 13, 400, GRAY)
        draw_eq(d, cx, 216, [eq_u(11, r)], None, 24, maxw=cw, red=(0, 3) if r == "Grossist" else None)
        u = uke(11, r)
        d.t(cx, 244, f"Ordre {u['ordre']}", 15, 500)
        vals = POS[r]
        pk = max(range(36), key=lambda t: vals[t])
        bars(d, cx, 268, cw, 110, vals, 0, 66, bw=cw / 36 * 0.62, labels={pk: n(vals[pk])}, label_size=13)
        d.t(cx, 398, "Posisjon, Uke 1", 13, 400, GRAY)
        d.t(cx + cw, 398, "36", 13, 400, GRAY, "end")
    d.t(x + 22, 420, "Samme uke, fire ulike tall. Ingen av dere så noe annet enn sitt eget.", 13, 400, GRAY)

    # Steg 3
    y3 = 466
    d.line(50, y3 - 22, 2050, y3 - 22, INK, 1)
    step(50, y3, 3, "Alle fire Rollers ordre, uke for uke")
    d.t(420, y3, "Tallene vokser oppover i kjeden, og toppen kommer senere: 24 i Uke 11, 22 i Uke 14, 31 i Uke 18.", 14, 400, INK)
    d.t(1860, y3, "Forsterkning", 14, 400, GRAY)
    rader = [("Kundene", S17["demand"])] + [(r, S17[r]["ordre"]) for r in ROLES]
    y_t = y3 + 26
    colw = (1860 - 50 - 110 - 20) / 36
    tabellgraf(d, 50, y_t, colw, rader, 110, rowh=64, vmax=max(max(S17[r]["ordre"]) for r in ROLES), skala=40, mark_uke=11, heads=True)
    forst = FX["spill17"]["forsterkning"]
    for i, r in enumerate(ROLES):
        yy = y_t + 64 * (i + 1) + 64 - 22
        d.t(1860, yy, ganger(forst[r]), 34, 500, RED if r == "Fabrikk" else INK, prop=True, ls="-0.4")

    # Steg 4
    y4 = 842
    d.line(50, y4 - 22, 2050, y4 - 22, INK, 1)
    step(50, y4, 4, "Ditt øyeblikk: Uke 11")
    u = uke(11)
    d.t(50, y4 + 36, "Det du så, og det du bestilte", 14, 400, GRAY)
    draw_eq(d, 50, y4 + 84, [eq_u(11), eq_ordre(u["posisjon"], u["ordre"])], [EQ_LABELS, ORDRE_LABELS], 44, row_h=76, red=(1, 3), label_gap=21)
    tekst_x = 50
    d.para(tekst_x, y4 + 210, f"Du hadde {u['paa_vei']} på vei, men {u['restordre']} i restordre var det som synte. Restordren gjør vondt nå. Det som er på vei gjør ingenting ennå.", 15, 350, lh=20)
    d.t(tekst_x, y4 + 274, "KI-generert, kan ta feil", 13, 600)

    x2 = 440
    d.t(x2, y4 + 36, "Hva det kostet senere", 14, 400, GRAY)
    lev15 = uke(15)["levering"]
    imaxL = max(range(36), key=lambda t: SARA["lager"][t])
    imaxR = max(range(36), key=lambda t: SARA["restordre"][t])
    linjer = [
        (f"{u['ordre']} bestilt, {lev15} levert i Uke 15", "leverandøren manglet varer"),
        (f"Restordre {SARA['restordre'][imaxR]} i Uke {imaxR + 1}", "ordrene var på vei hele tiden"),
        (f"Posisjon {SP[imax]} i Uke {imax + 1}", "alt kom fram samtidig"),
        (f"Lager {SARA['lager'][imaxL]} i Uke {imaxL + 1}", f"{kr(SARA['lager'][imaxL] * 0.5)} kr hver uke"),
        (f"{kr(u['kost_sum'])} kr i Uke 11", f"{kr(FX['spill17']['kost_per_rolle']['Grossist'])} kr ved slutt"),
    ]
    yy = y4 + 66
    for a, b in linjer:
        d.t(x2, yy, a, 17, 500)
        d.t(x2, yy + 19, b, 13, 400, GRAY)
        yy += 48

    x3 = 800
    d.t(x3, y4 + 36, "Hva de andre så", 14, 400, GRAY)
    mik, jon = S17["Distributør"], S17["Fabrikk"]
    assert mik["innkommende_ordre"][12] == 24
    kjede = [
        ("Uke 13", f"Mikkel ser {mik['innkommende_ordre'][12]} inn og bestiller {mik['ordre'][12]}, uten å vite hvorfor."),
        ("Uke 15", f"Jonas ser {jon['innkommende_ordre'][14]} inn og bestiller {jon['ordre'][14]}, så {jon['ordre'][15]}, {jon['ordre'][16]} og {jon['ordre'][17]}."),
        ("Ingen", "av dere så kundene. Hver leste ordrene fra leddet under, og det var alt som fantes å lese."),
    ]
    yy = y4 + 66
    for a, b in kjede:
        d.t(x3, yy, a, 15, 600)
        yy = d.para(x3 + 70, yy, b, 15, 300, lh=20) + 10

    # Referanse under
    xr = 800
    yr = y4 + 214
    d.t(xr, yr, "Posisjonen din, og Simulert med alt på vei talt", 14, 400, GRAY)
    wr = 280
    bars(d, xr, yr + 12, wr, 58, SP, 0, 60, bw=wr / 36 * 0.62)
    b_pos = posisjon(BARE["serier"], "Grossist")
    bars(d, xr + wr + 30, yr + 12, wr, 58, b_pos, 0, 60, bw=wr / 36 * 0.62)
    d.t(xr, yr + 90, f"Spill 17: Grossist {kr(FX['spill17']['kost_per_rolle']['Grossist'])}, {ganger(forst['Grossist'])}", 13, 500)
    d.t(xr + wr + 30, yr + 90, f"Simulert: {kr(BARE['kost_per_rolle']['Grossist'])}, {ganger(BARE['forsterkning']['Grossist'])}", 13, 500)
    d.t(xr, yr + 110, f"Kjeden {kr(FX['spill17']['kjedekost'])} kr", 13, 400, GRAY)
    d.t(xr + wr + 30, yr + 110, f"Kjeden {kr(BARE['kjedekost'])} kr. Viser sammenhengen, ikke en fasit.", 13, 400, GRAY)

    # Steg 5
    x5 = 1480
    step(x5, y4, 5, "Debrief-quiz")
    u18 = uke(18)
    d.para(x5, y4 + 44, f"Lager {u18['lager']}, Restordre {u18['restordre']}, På vei {u18['paa_vei']}. Hva er Posisjonen?", 24, 560, w=500, lh=31)
    alts = [(n(-u18["restordre"]), "Ditt svar", True), (str(u18["posisjon"]), "Riktig", False), (str(u18["paa_vei"]), "", False), (str(u18["paa_vei"] + u18["restordre"]), "", False)]
    yy = y4 + 122
    for v, tag, wrong in alts:
        right = tag == "Riktig"
        d.t(x5, yy, v, 26, 500, RED if right else (INK if wrong else GRAY))
        if tag:
            d.t(x5 + 70, yy - 2, tag, 15, 600)
        yy += 37
    d.para(x5, yy + 2, f"Du regnet Lager minus Restordre og fikk {n(-u18['restordre'])}. Det er det skjermen roper, men det mangler det som er på vei: {n(-u18['restordre'])} + {u18['paa_vei']} = {u18['posisjon']}.", 15, 560, lh=21)
    d.save()


# ----- 08 Laereroversikt -----
def micro_left(d, x, base, vals, ppw, scale, color=INK, bw=None):
    bw = bw or ppw - 1
    d.line(x, base, x + len(vals) * ppw, base, TINT, 0.6)
    for i, v in enumerate(vals):
        h = abs(v) * scale
        d.rect(x + i * ppw, base - h if v >= 0 else base, bw, h, color)


def page_08():
    d = Doc("08-laerer-oversikt", 1600, 1000, "Posisjon: Oversikt for faglærer", "60 Klassespill på én skjerm, gruppert etter hva faglærer må gjøre, med ekte posisjonsserier og trakten som regnestykke.")
    spill = KL["spill"]
    for g in spill:
        g["_pos"] = spill_posisjon(g)
    vent = sorted([g for g in spill if g["status"] == "venter"], key=lambda g: -g["ventet_timer"])
    pause = [g for g in spill if g["status"] == "pauset"]
    gaar = sorted([g for g in spill if g["status"] == "pågår"], key=lambda g: -g["uke"])
    ferdig = sorted([g for g in spill if g["status"] == "ferdig"], key=lambda g: g["kjedekost"])
    n_f, n_p, n_v = len(ferdig), len(gaar) + len(pause), len(vent)
    assert (n_f, n_p, n_v) == (41, 15, 4)

    L = 40
    d.t(L, 52, "Oversikt", 30, 500, ls="-0.4")
    d.t(L + 128, 52, "class-of-1994, IBE160", 15, 400, GRAY)
    # Regnestykket i toppen
    eqx = 560
    _, _, tot = draw_eq(d, eqx, 54, [[("", n_f), ("+", n_p), ("+", n_v), ("=", len(spill))]], [["Ferdig", "Pågår", "Venter", "Klassespill"]], 36, label_size=13, label_gap=20)
    d.t(eqx + tot + 28, 52, f"Av de {n_p} som pågår, spiller {len(gaar)} og {len(pause)} har Pause.", 13, 400, GRAY)
    d.t(1560, 42, "Demodata", 13, 400, GRAY, "end")

    # Filter
    fy = 104
    fx = L
    for text, on in [(f"Alle {len(spill)}", True), (f"Venter {n_v}", False), (f"Pauset {len(pause)}", False), (f"Pågår {len(gaar)}", False), (f"Ferdig {n_f}", False), ("KI-seter", False)]:
        d.t(fx, fy, text, 14, 600 if on else 400, INK, under=on)
        fx += tw(text, 14) + 22
    # Kolonner
    cS, cH, cT, cU, cK, cC, cM = L, 84, 322, 372, 416, 500, 566
    PPW = 3.0
    cellw = 36 * PPW + 12
    aktive = vent + pause + gaar
    scale = 20.0 / max(max(g["_pos"][r]) for g in aktive for r in ROLES)
    y = 132
    d.t(cS, y, "Spill", 13, 400, GRAY)
    d.t(cH, y, "Venter på", 13, 400, GRAY)
    d.t(cT + 34, y, "Tid", 13, 400, GRAY, "end")
    d.t(cU + 28, y, "Uke", 13, 400, GRAY, "end")
    d.t(cK + 40, y, "KI-seter", 13, 400, GRAY, "end")
    d.t(cC + 46, y, "Kost", 13, 400, GRAY, "end")
    for i, r in enumerate(ROLES):
        d.t(cM + i * cellw, y, r, 13, 400, GRAY)
    d.t(1070, y, "", 13)
    MX = cM + 4 * cellw

    def row(g, y, hi=False):
        base = y + 6
        if hi:
            d.rect(L - 8, y - 15, MX + 92 - L + 8, 24, WASH)
        w_ = 700 if hi else 400
        d.t(cS, y, g["spill"], 13, w_ if hi else 500)
        if g["status"] == "venter":
            d.t(cH, y, f"{g['navn']}, {g['venter_paa']}", 13, w_)
            d.t(cT + 34, y, f"{g['ventet_timer']} t", 13, 700 if hi else 500, RED if hi else INK, "end")
        elif g["status"] == "pauset":
            d.t(cH, y, f"Pause, fortsetter {g['fortsetter']}", 13)
        else:
            d.t(cH, y, "Spiller", 13, 400, GRAY)
        d.t(cU + 28, y, g["uke"], 13, 400, INK, "end")
        d.t(cK + 40, y, g["ki_seter"] if g["ki_seter"] else "", 13, 400, INK, "end")
        d.t(cC + 46, y, kr0(g["kjedekost"]), 13, 400, INK, "end")
        for i, r in enumerate(ROLES):
            micro_left(d, cM + i * cellw, base, g["_pos"][r], PPW, scale, color=INK, bw=PPW)

    y += 30
    d.t(cS, y, "Må følges opp", 15, 600)
    d.t(cS + 110, y, "Spill 2: KI overtar om 1 t", 13, 400, INK)
    y += 22
    for g in vent:
        hi = g["spill"] == 2
        row(g, y, hi)
        if hi:
            d.t(MX + 84 - 8, y, "Send Melding", 13, 600, INK, "end", under=True)
        else:
            d.t(MX + 84 - 8, y, "Send Melding", 13, 400, GRAY, "end", under=True)
        y += 24
    y += 14
    d.t(cS, y, "Avtalt Pause", 15, 600)
    y += 22
    for g in pause:
        row(g, y)
        y += 24
    y += 14
    d.t(cS, y, "Går av seg selv", 15, 600)
    y += 22
    for g in gaar:
        row(g, y)
        y += 24

    # Ferdige
    y += 18
    d.t(cS, y, f"Ferdig: {n_f} spill, Fabrikkens Posisjon, lavest Kost først", 15, 600)
    yf = y + 14
    cols = 14
    cw = (MX + 84 - L) / cols
    rowh = (984 - yf) / 3
    for i, g in enumerate(ferdig):
        cx = L + (i % cols) * cw
        cy = yf + (i // cols) * rowh
        base = cy + rowh - 24
        micro_left(d, cx, base, g["_pos"]["Fabrikk"], (cw - 10) / 36, (rowh - 30) / 170, bw=(cw - 10) / 36)
        d.t(cx, base + 18, g["spill"], 12, 500)
        d.t(cx + cw - 10, base + 18, kr0(g["kjedekost"]), 12, 400, GRAY, "end")

    # Hoeyre: trakten som regnestykke
    X = 1180
    W = 380
    d.t(X, 132, "Trakten", 15, 600)
    d.t(X + W, 132, "Hver linje er linjen over minus de som gjenstår", 13, 400, GRAY, "end")
    tr = KL["traktA"]
    steg = [("Registrert", "registrert"), ("Klassespill ferdig", "klassespill_ferdig"), ("Debrief ferdig", "debrief_ferdig"), ("Quiz bestått", "quiz_bestått"), ("Replay ferdig", "replay_ferdig"), ("Test levert", "test_levert"), ("KI-vurdering klar", "ki_vurdering_klar")]
    yy = 174
    prev = None
    for lab, k in steg:
        v = tr[k]
        d.t(X, yy, lab, 15, 400)
        if prev is not None:
            d.t(X + 232, yy, "− " + str(prev - v), 15, 400, GRAY, "end")
        d.t(X + W, yy, v, 28, 500, INK, "end")
        d.rect(X, yy + 7, W * v / tr["registrert"], 2, INK)
        prev = v
        yy += 45
    yy += 14
    d.t(X, yy, "Det klassen gjør oftest", 15, 600)
    yy += 26
    for k, v in KL["moenstre"].items():
        for i, l in enumerate(wrap(k, 14, W - 60)):
            d.t(X, yy + i * 18, l, 14)
        d.t(X + W, yy, v, 15, 500, INK, "end")
        yy += 18 * len(wrap(k, 14, W - 60)) + 8
    yy += 16
    d.t(X, yy, "Kjedekost, median", 15, 600)
    yy += 30
    fer = KL["ferdige"]["kjedekost"]
    fj = KL["fjoraaret"]
    d.t(X, yy, kr0(fer["median"]), 28, 500, prop=True)
    d.t(X + 110, yy, f"{KL['ferdige']['antall']} ferdige i år", 13, 400, GRAY)
    yy += 34
    d.t(X, yy, kr0(fj["median_kjedekost"]), 28, 500, GRAY, prop=True)
    d.t(X + 110, yy, f"{fj['klasse']}, {fj['spill']} spill", 13, 400, GRAY)
    yy += 40
    d.t(X, yy, "Forsterkning i ferdige spill, median", 15, 600)
    yy += 34
    fp = KL["ferdige"]["forsterkning_per_rolle"]
    for i, r in enumerate(ROLES):
        cx = X + i * W / 4
        d.t(cx, yy, ganger(fp[r]["median"]), 24, 500, prop=True)
        d.t(cx, yy + 20, r, 13, 400, GRAY)
    button(d, X, 936, W, 44, "Send Melding til dem som venter", size=15)
    d.save()


# ----- 01 Landing -----
def page_01():
    d = Doc("01-landing", 1440, 1200, "Posisjon: landingsside for faglærere", "Første skjermbilde med ett regnestykke og ett setes Posisjon over tid, og starten på lærerens oversikt.")
    L = 60
    d.t(L, 58, "Posisjon", 20, 600)
    y = d.para(L, 136, "Forsyningskjeden som øvelse, for hele kurset.", 58, 900, w=500, lh=64)
    d.para(1000, 102, "Studentene spiller på mobil, én ordre i uka. Du ser alle spillene på én skjerm. Fra Invitasjon til PDF-rapport.", 18, 380, lh=26)
    button(d, 1000, 192, 220, 52, "Be om lærertilgang", size=16)
    d.t(1244, 224, "Logg inn", 16, 500, INK, under=True)

    # Plakaten
    week = 11
    u = uke(week)
    draw_eq(d, L - 10, 440, [eq_u(week)], [EQ_LABELS], 212, maxw=1336, label_size=18, label_gap=44, red=(0, 3), label_dx=10)
    vals = SP[:week]
    bars(d, L, 520, 1320, 300, vals, 0, 26, labels={0: n(vals[0]), week - 1: n(vals[-1])}, bw=26, label_size=18)
    d.t(L, 848, f"Én Grossist, Uke 1 til {week}. Samme tall i ligningen og i grafen.", 15, 400, GRAY)
    d.t(1380, 848, "Demodata", 13, 400, GRAY, "end")

    # Neste seksjon
    yb = 930
    d.line(L, yb - 40, 1380, yb - 40, INK, 1)
    d.t(L, yb, "Alle spillene på én skjerm", 34, 500, ls="-0.4")
    spill = KL["spill"]
    rader = sorted([g for g in spill if g["status"] == "venter"], key=lambda g: -g["ventet_timer"])[:3] + [g for g in spill if g["status"] == "pauset"][:1] + [g for g in spill if g["status"] == "pågår"][:2]
    y = yb + 42
    colx = [L, 120, 340, 410]
    for x, t in zip(colx, ["Spill", "Venter på", "Uke", "Posisjon, Grossist"]):
        d.t(x, y, t, 13, 400, GRAY)
    y += 26
    mx = max(max(spill_posisjon(g)["Grossist"]) for g in rader)
    for g in rader:
        p = spill_posisjon(g)["Grossist"]
        d.t(colx[0], y, g["spill"], 15, 500)
        if g["status"] == "venter":
            d.t(colx[1], y, f"{g['navn']}, {g['ventet_timer']} t", 15)
        elif g["status"] == "pauset":
            d.t(colx[1], y, "Avtalt Pause", 15)
        else:
            d.t(colx[1], y, "Spiller", 15, 400, GRAY)
        d.t(colx[2], y, g["uke"], 15)
        micro_left(d, colx[3], y + 4, p, 6, 22 / mx, bw=4)
        y += 30
    # Fakta, som et flush-left sett
    facts = ["Klasser på rundt 250 studenter.", "Studentlisten fra Canvas-eksport.", "KI-spillere fyller tomme seter.", "Ett fravær stopper ikke gruppa.", "Ingen spill blir stående uferdig.", "På mobil. På norsk."]
    fx = 780
    yf = yb + 42
    for i, t in enumerate(facts):
        col = i % 2
        d.para(fx + col * 300, yf + (i // 2) * 62, t, 20, 270, w=500, lh=26)
    d.save()


# ----- 02 Lag Klasse -----
def page_02():
    d = Doc("02-laerer-klasse", 1440, 1000, "Posisjon: lag Klasse", "Navn og emnekode, Canvas-fil, e-postkolonne, ugyldige rader og Invitasjoner.")
    R_ = KL["roster"]
    L = 60
    d.t(L, 70, "Lag Klasse", 40, 500, ls="-0.5")
    d.t(1380, 70, "Demodata. Navn og adresser er oppdiktet.", 13, 400, GRAY, "end")
    # Felt
    y = 124
    d.t(L, y, "Navn", 13, 400, GRAY)
    d.t(L, y + 28, "class-of-1994", 22, 500)
    d.line(L, y + 38, L + 300, y + 38, INK, 1)
    d.t(L + 340, y, "Emnekode", 13, 400, GRAY)
    d.t(L + 340, y + 28, "IBE160", 22, 500)
    d.line(L + 340, y + 38, L + 500, y + 38, INK, 1)

    y = 208
    d.t(L, y, "Klasseliste fra Canvas", 13, 400, GRAY)
    d.t(L, y + 28, "ibe160-eksport.xlsx", 22, 500)
    d.t(L + 340, y + 28, "Bytt fil", 15, 500, INK, under=True)

    # Regnestykket
    gyldige = R_["paa_lista"] - R_["ugyldige_rader"]
    draw_eq(d, L, 396, [[("", R_["paa_lista"]), ("−", R_["ugyldige_rader"]), ("=", gyldige)]], [["Rader i fila", "Ugyldige adresser", "Kan inviteres"]], 96, label_size=14, label_gap=34, red=(0, 1))

    # Filstripe: hver rad en strek, med ugyldige paa sann plass
    y = 480
    ugyldige = [37, 88, 141, 203]
    assert len(ugyldige) == R_["ugyldige_rader"]
    cw = 700 / R_["paa_lista"]
    for i in range(R_["paa_lista"]):
        bad = i + 1 in ugyldige
        d.rect(L + i * cw, y if not bad else y - 6, max(cw - 0.8, 1), 26 if not bad else 38, RED if bad else INK)
    d.t(L, y + 50, "Rad 1", 13, 400, GRAY)
    d.t(L + 700, y + 50, f"Rad {R_['paa_lista']}", 13, 400, GRAY, "end")

    # Velg e-postkolonne
    y = 640
    d.t(L, y, "E-postkolonne", 17, 600)
    d.t(L + 140, y, "Vi fant denne. Trykk på en annen kolonne hvis den er feil.", 14, 400, GRAY)
    cols = [("Navn", ["Noah Berg", "Ida Solheim", "Sara Lunde"]), ("SIS-ID", ["216041", "216042", "216043"]), ("E-post", ["noah.berg@stud.example.no", "ida.solheim@stud.example.no", "sara.lunde@stud.example.no"]), ("Seksjon", ["IBE160-1", "IBE160-1", "IBE160-2"])]
    cx = [L, L + 170, L + 280, L + 560]
    y += 34
    d.rect(cx[2] - 10, y - 18, 268, 104, WASH)
    for x, (h, vals) in zip(cx, cols):
        sel = h == "E-post"
        d.t(x, y, h, 14, 600 if sel else 400, INK if sel else GRAY)
        for i, v in enumerate(vals):
            d.t(x, y + 26 + i * 24, v, 14)
    d.t(cx[2], y + 110, "Valgt kolonne: E-post", 13, 600)

    # Ugyldige rader
    X = 860
    d.t(X, 124, "Ugyldige rader", 17, 600)
    d.t(X + 520, 124, "Rett i fila, eller her", 13, 400, GRAY, "end")
    bad_rows = [(37, "Emil Aas", "emil.aas@stud.example", "mangler .no"), (88, "Live Dahl", "live.dahl stud.example.no", "mangler @"), (141, "Jon Moe", "", "tom celle"), (203, "Tiril Vik", "tiril.vik@@stud.example.no", "to @")]
    y = 166
    for r, navn, epost, feil in bad_rows:
        d.t(X, y, f"Rad {r}", 15, 600)
        d.t(X + 70, y, navn, 15)
        d.t(X + 520, y, feil, 15, 500, INK, "end")
        d.t(X + 70, y + 22, epost or "Ingen adresse", 14, 400, GRAY)
        d.t(X + 520, y + 22, "Rett", 14, 500, INK, "end", under=True)
        y += 66
    button(d, X, y + 18, 270, 52, f"Send {gyldige} Invitasjoner", size=16)
    d.para(X + 290, y + 40, "Gyldig i 14 dager. De 4 ugyldige får ingen e-post før de er rettet.", 13, 230, fill=GRAY, lh=18)

    # Status
    y = 640
    d.t(X, y, "Status etter utsending", 17, 600)
    y += 62
    draw_eq(d, X, y, [[("", R_["registrert"]), ("+", R_["manuelt_registrert"]), ("+", R_["uregistrert"]), ("=", R_["paa_lista"])]], [["Registrert", "Manuelt", "Uregistrert", "På lista"]], 52, maxw=520, label_size=14, label_gap=26)
    # Stolpe
    y += 58
    w_ = 520
    a = w_ * R_["registrert"] / R_["paa_lista"]
    b = w_ * R_["manuelt_registrert"] / R_["paa_lista"]
    d.rect(X, y, a - 2, 12, INK)
    d.rect(X + a, y, max(b - 2, 2), 12, GRAY)
    d.rect(X + a + b, y, w_ - a - b, 12, TINT)
    y += 46
    rows = [("Registrerte: klare for fordeling", f"{R_['registrert'] + R_['manuelt_registrert']}"), ("Send påminnelse til uregistrerte", f"{R_['uregistrert']}"), ("Registrer en student manuelt", "")]
    for a_, b_ in rows:
        d.t(X, y, a_, 15, 400, INK, under=b_ != "" and "påminnelse" in a_ or b_ == "")
        d.t(X + w_, y, b_, 15, 500, INK, "end")
        y += 28
    d.save()


# ----- 03 Klasseoekt -----
def page_03():
    d = Doc("03-laerer-spill", 1440, 1100, "Posisjon: Klasseøkt", "Forhåndsutfylte standarder, KI-modus, Debrief-modus, datoer, Labtimer og fordeling i 60 spill.")
    L = 60
    d.t(L, 70, "Klasseøkt", 40, 500, ls="-0.5")
    d.t(L + 200, 70, "class-of-1994, IBE160", 15, 400, GRAY)
    d.t(1380, 70, "Demodata", 13, 400, GRAY, "end")
    d.para(L, 112, "Alt er fylt ut med standarden «Klassisk». Du kan lagre uten å endre noe.", 18, 700, lh=26)

    def tabell(x, y, title, rader, w_=420):
        d.t(x, y, title, 17, 600)
        y += 30
        for a, b in rader:
            d.t(x, y, a, 15, 400, GRAY)
            d.t(x + w_, y, b, 15, 500, INK, "end")
            y += 31
        return y

    s17 = S17["Grossist"]
    y1 = tabell(L, 180, "Kjeden", [("Startlager", s17["lager"][0]), ("I hvert ledd", "4 enheter"), ("Ordreforsinkelse", "2 uker"), ("Fraktforsinkelse", "2 uker"), ("Produksjonsforsinkelse", "2 uker"), ("Lagerkost", "0,50"), ("Restordrekost", "1,00"), ("Etterspørsel", f"{S17['demand'][0]}, så {S17['demand'][4]} i Uke 5"), ("Uker", len(s17["lager"])), ("Veiledede uker", "1 til 4"), ("Inaktivitetsgrense", "24 t")])
    d.para(L, y1 + 8, "Kildene er uenige om forsinkelsene. Dette er produktets standard.", 13, 420, fill=GRAY, lh=18)

    y = y1 + 60
    u1 = uke(1)
    d.t(L, y, "Slik starter hvert sete", 17, 600)
    draw_eq(d, L, y + 62, [eq_u(1)], [EQ_LABELS], 44, label_gap=22, maxw=420)

    # Modus
    X = 540
    def choice(x, y, title, opts, on):
        d.t(x, y, title, 17, 600)
        y += 30
        for o in opts:
            sel = o == on
            d.rect(x + 0.5, y - 12.5, 13, 13, INK if sel else PAPER, INK, 1)
            d.t(x + 22, y, o, 15, 600 if sel else 400)
            y += 31
        return y

    y2 = choice(X, 180, "KI-modus", ["LLM-spillere", "Regelbaserte spillere"], "LLM-spillere")
    y2 = choice(X, y2 + 20, "Debrief-modus", ["Gruppedebrief", "Individuell Debrief"], "Gruppedebrief")
    y2 = choice(X, y2 + 20, "Krav", ["Obligatorisk"], "Obligatorisk")
    y2 += 20
    d.t(X, y2, "Datoer", 17, 600)
    y2 += 30
    for a, b in [("Start", "ti. 24. nov 2026"), ("Spillfrist", "ti. 8. des"), ("Debrief-frist", "fr. 11. des"), ("Testfrist", "fr. 18. des")]:
        d.t(X, y2, a, 15, 400, GRAY)
        d.t(X + 320, y2, b, 15, 500, INK, "end")
        y2 += 31
    y2 += 20
    d.t(X, y2, "Labtimer, Datalab A2", 17, 600)
    y2 += 30
    for b in ["to. 26. nov 14:15", "ma. 30. nov 10:15", "to. 3. des 14:15", "ma. 7. des 10:15"]:
        d.t(X, y2, b, 15, 500)
        y2 += 31

    # Fordeling
    Xf = 940
    d.t(Xf, 180, "Fordeling", 17, 600)
    spill = KL["spill"]
    tr = KL["traktA"]["registrert"]
    assert tr / 4 == len(spill)
    draw_eq(d, Xf, 282, [[("", tr), ("÷", 4), ("=", len(spill))]], [["Studenter", "Per spill", "Klassespill"]], 84, label_size=14, label_gap=30, maxw=440, red=(0, 2))
    # 60 grupper a 4 prikker
    y = 340
    cw, ch = 44, 44
    for i in range(60):
        cx = Xf + (i % 10) * cw
        cy = y + (i // 10) * ch
        for k in range(4):
            d.rect(cx + (k % 2) * 10, cy + (k // 2) * 10, 8, 8, INK)
        d.t(cx + 24, cy + 16, i + 1, 13, 400, GRAY)
    y += 6 * ch + 20
    d.para(Xf, y, "Tilfeldig fordelt. Roller trekkes per spill. Tomme seter får KI-spiller ved start.", 14, 440, fill=GRAY, lh=20)
    y += 58
    d.t(Xf, y, "Spill 1", 15, 600)
    for i, (r, name) in enumerate(zip(ROLES, ["Emma", "Noah", "Lukas", "Maja"])):
        d.t(Xf + 70, y + i * 25, r, 15, 400, GRAY)
        d.t(Xf + 200, y + i * 25, name, 15, 500)
    y += 124
    button(d, Xf, y, 200, 48, "Kjør på nytt", primary=False, size=15)
    button(d, Xf + 220, y, 220, 48, "Bekreft fordelingen", size=15)
    y += 100
    button(d, L, 1020, 320, 52, "Lagre Klasseøkt uten endring", size=16)
    d.t(L + 340, 1052, "Kan endres fram til start, ti. 24. nov.", 13, 400, GRAY)
    d.save()


# ----- 04 Studenthjem -----
def page_04():
    d = Doc("04-student-hjem", 1000, 900, "Posisjon: Sara på mobil", "Registrering og hjem under spill.")
    SC = 0.95
    d.t(40, 44, "Registrering og hjem", 24, 500)
    d.t(960, 44, "Demodata", 13, 400, GRAY, "end")
    yp = 68
    phone_frame(d, 40, yp, SC)
    d.t(20, 62, "Posisjon", 15, 600)
    d.para(20, 124, "Du er invitert til class-of-1994.", 36, 340, w=500, lh=42)
    d.t(20, 228, "IBE160, faglærer Bård", 15, 400, GRAY)
    yy = 290
    for lab, val in [("E-post", "sara.lunde@stud.example.no"), ("Navn", "Sara Lunde"), ("Passord", "")]:
        d.t(20, yy, lab, 13, 400, GRAY)
        d.t(20, yy + 26, val or "Minst 12 tegn", 18, 500 if val else 400, INK if val else GRAY)
        d.line(20, yy + 38, 370, yy + 38, INK, 1)
        yy += 76
    button(d, 20, yy + 14, 350, 56, "Opprett konto")
    d.para(20, yy + 100, "Invitasjonen er gyldig i 14 dager. Du får vite Rolle og spill når klassen er fordelt.", 14, 350, fill=GRAY, lh=20)
    d.close()

    phone_frame(d, 440, yp, SC)
    u = uke(11)
    d.t(20, 62, "Sara", 15, 600)
    d.t(370, 62, "Spill 17, Grossist", 15, 400, GRAY, "end")
    d.t(20, 120, "Spillet venter på deg", 28, 500, ls="-0.3")
    draw_eq(d, 20, 186, [eq_u(11)], [EQ_LABELS], 44, maxw=350, red=(0, 3), label_gap=21)
    button(d, 20, 240, 350, 52, "Legg inn ordre, Uke 11", size=15)
    yy = 336
    d.t(20, yy, "Setene", 13, 400, GRAY)
    yy += 24
    for r in ROLES:
        me = r == "Grossist"
        st = {"Detaljist": "har bestilt", "Grossist": "venter på deg", "Distributør": "har bestilt", "Fabrikk": "venter, 3 min"}[r]
        d.t(20, yy, f"{r}, {NAVN[r]}" + (" (deg)" if me else ""), 15, 600 if me else 400)
        d.t(370, yy, st, 15, 600 if me else 400, INK, "end")
        yy += 27
    yy += 22
    d.t(20, yy, "Stegene", 13, 400, GRAY)
    yy += 24
    for i, (s_, st) in enumerate([("Klassespill", "pågår"), ("Debrief", "låst"), ("Quiz", "låst"), ("Replay", "låst"), ("Individuell test", "låst"), ("Rapport", "låst")]):
        d.t(20, yy, i + 1, 15, 400, GRAY)
        d.t(44, yy, s_, 15, 600 if i == 0 else 400)
        d.t(370, yy, st, 15, 600 if i == 0 else 400, INK if i == 0 else GRAY, "end")
        yy += 27
    yy += 22
    d.t(20, yy, "Neste frist", 13, 400, GRAY)
    d.t(370, yy, "Labtime", 13, 400, GRAY, "end")
    d.t(20, yy + 24, "Spillfrist, ti. 8. des", 15, 500)
    d.t(370, yy + 24, "to. 26. nov 14:15", 15, 500, INK, "end")
    d.t(370, yy + 46, "Datalab A2", 15, 400, INK, "end")
    d.close()

    x = 830
    d.para(x, 110, "Hjem viser det samme regnestykket som spillet.", 15, 130, w=600, lh=20)
    d.para(x, 200, "Ingen ukeantall og ingen framdrift for selve spillet, bare hvor langt Sara er i de seks stegene.", 14, 130, fill=GRAY, lh=19)
    d.para(x, 340, "Andre seter vises som status, aldri med tall.", 14, 130, fill=GRAY, lh=19)
    d.save()


# ----- 09 Alle sider -----
def page_09():
    d = Doc("09-alle-sider", 2000, 1400, "Posisjon: alle andre sider", "Kontaktark over alle andre sider, gruppert per rolle.")
    d.t(60, 76, "Alle andre sider", 40, 500, ls="-0.5")
    d.t(1940, 76, "Demodata. Lavere detaljnivå.", 13, 400, GRAY, "end")
    TW, TH = 250, 250
    gut = (1880 - 7 * TW) / 6
    spill = KL["spill"]
    for g in spill:
        g["_pos"] = spill_posisjon(g)

    def mini_eq(d_, x, y, week, size=24, role="Grossist", ser=S17, maxw=210, labels=False, red=True):
        draw_eq(d_, x, y, [eq_u(week, role, ser)], [EQ_LABELS] if labels else None, size, maxw=maxw, red=(0, 3) if red else None, label_size=9, label_gap=14)

    def rad(d_, y, a, b="", size=11):
        d_.t(14, y, a, size)
        if b != "":
            d_.t(TW - 14, y, b, size, 500, INK, "end")

    def s_inv(d_):
        d_.para(14, 42, "Du er invitert til class-of-1994.", 20, 220, w=500, lh=24)
        for i, l in enumerate(["E-post", "Navn", "Passord"]):
            d_.t(14, 118 + i * 34, l, 10, 400, GRAY)
            d_.line(14, 130 + i * 34, 236, 130 + i * 34, INK, 0.7)
        d_.rect(14, 212, 222, 24, INK)
        d_.t(125, 228, "Opprett konto", 11, 600, PAPER, "middle")

    def s_login(d_):
        d_.t(14, 44, "Logg inn", 22, 500)
        for i, l in enumerate(["E-post", "Passord"]):
            d_.t(14, 90 + i * 40, l, 10, 400, GRAY)
            d_.line(14, 104 + i * 40, 236, 104 + i * 40, INK, 0.7)
        d_.rect(14, 170, 222, 26, INK)
        d_.t(125, 187, "Logg inn", 11, 600, PAPER, "middle")
        d_.t(14, 220, "Glemt passordet?", 11, 400, INK, under=True)

    def s_regler(d_):
        d_.t(14, 34, "Slik regner du", 16, 600)
        mini_eq(d_, 14, 82, 1, size=26, labels=True, red=False)
        d_.para(14, 128, "Du bestemmer ett tall per Uke. Levering tar tid. Restordre koster 1,00, lager 0,50.", 11, 222, lh=15)
        d_.rect(14, 212, 222, 24, INK)
        d_.t(125, 228, "Jeg forstår, start", 11, 600, PAPER, "middle")

    def s_start(d_):
        u = uke(8)
        d_.t(14, 34, "Startoppgave", 16, 600)
        d_.t(14, 74, f"{u['lager']} − {u['restordre']} + {u['paa_vei']} =", 26, 500)
        d_.rect(14, 86, 60, 2, INK)
        d_.t(14, 118, "Hva er Posisjonen?", 12)
        for i, v in enumerate([u["posisjon"], u["lager"], u["paa_vei"]]):
            d_.t(14, 150 + i * 26, v, 16, 500)
        d_.t(TW - 14, 228, "Svar", 12, 600, INK, "end", under=True)

    def s_replay(d_):
        d_.t(14, 30, "Replay, Grossist, Uke 19", 11, 600)
        rs = REPLAY["serier"]
        mini_eq(d_, 14, 66, 19, size=24, ser=rs)
        stacked(d_, 14, 92, 222, 120, rs["Grossist"], 19, -12, 44, 222 / 19)
        d_.t(TW - 14, 232, "nå", 10, 600, INK, "end")

    def s_gjenn(d_):
        d_.t(14, 30, "Klassespill og Replay", 11, 600)
        d_.t(14, 48, "Ikke like for like", 10, 400, GRAY)
        bars(d_, 14, 62, 222, 62, SP, 0, 60, bw=222 / 36 * 0.6)
        d_.t(14, 142, f"Spill 17, Grossist {kr(FX['spill17']['kost_per_rolle']['Grossist'])}", 10, 500)
        rp = posisjon(REPLAY["serier"], "Grossist")
        bars(d_, 14 , 154, 222 * 33 / 36, 56, rp, 0, 60, bw=222 / 36 * 0.6)
        d_.t(14, 228, f"Replay, Grossist {kr(REPLAY['kost_per_rolle']['Grossist'])}", 10, 500)

    def s_test(d_):
        d_.t(14, 30, "Individuell test", 11, 600)
        d_.t(14, 56, "Flervalg", 11, 400, GRAY)
        d_.t(70, 56, "Tegn", 11, 600, INK, under=True)
        d_.t(108, 56, "Langsvar", 11, 400, GRAY)
        d_.t(14, 82, "Tegn lageret fra inn og ut:", 11)
        vals = [12, 12, 9, 4, 2, 3, 6]
        for i, v in enumerate(vals):
            d_.rect(14 + i * 32, 200 - v * 7, 22, v * 7, INK if i < 4 else PAPER, INK, 1)
        d_.line(14, 200, 236, 200, INK, 1)
        d_.t(14, 224, "Fylte søyler er tegnet, hule gjenstår", 10, 400, GRAY)

    def s_ki(d_):
        d_.t(14, 30, "KI-vurdering", 11, 600)
        d_.para(14, 62, "Du skiller godt mellom Lager og Posisjon, men sier lite om hvorfor ordren kom fram senere.", 13, 222, lh=18)
        d_.t(14, 170, "KI-generert, kan ta feil.", 11, 600)
        d_.para(14, 190, "Teller ikke, og er aldri en karakter.", 11, 222, fill=GRAY, lh=15)

    def s_rapport(d_):
        d_.t(14, 30, "Studentrapport, PDF", 11, 600)
        d_.t(14, 54, "Sara Lunde, Grossist, Spill 17", 10, 400, GRAY)
        mini_eq(d_, 14, 92, 11, size=22, red=False)
        bars(d_, 14, 104, 222, 66, SP, 0, 60, bw=222 / 36 * 0.6)
        for i, v in enumerate(["Forklaring", "Quiz", "Replay", "Test"]):
            d_.t(14, 192 + i * 13, v, 10)
            d_.t(TW - 14, 192 + i * 13, "levert", 10, 400, GRAY, "end")

    def grid_micro(d_, y, cols, cellw, cellh, antall, role="Fabrikk", tall=True):
        for i, g in enumerate(spill[:antall]):
            cx = 14 + (i % cols) * cellw
            base = y + (i // cols) * cellh + cellh - 4
            vals = g["_pos"][role]
            micro_left(d_, cx, base, vals, (cellw - 4) / 36, (cellh - 6) / 170, bw=max(0.8, (cellw - 4) / 36 * 0.7))

    def s_alle(d_):
        d_.t(14, 30, "Alle spill side om side", 11, 600)
        d_.t(14, 46, "Anonymt, uten rangering.", 10, 400, GRAY)
        grid_micro(d_, 56, 6, 37, 30, 36)

    def f_hjem(d_):
        d_.t(14, 34, "Lærerhjem", 16, 600)
        for i, (a, b) in enumerate([("class-of-1994", "60 spill"), ("class-of-1993", "58 spill")]):
            d_.t(14, 66 + i * 22, a, 12, 500)
            d_.t(TW - 14, 66 + i * 22, b, 12, 400, GRAY, "end")
        d_.t(14, 134, "Neste Labtime", 10, 400, GRAY)
        d_.t(14, 152, "to. 26. nov 14:15", 12, 500)
        d_.t(14, 186, "4 spill venter", 16, 500)
        d_.t(14, 206, "Spill 2 nær overtakelse", 11)

    def f_rapport(d_):
        d_.t(14, 30, "Klasserapport", 11, 600)
        fer = KL["ferdige"]["kjedekost"]
        d_.t(14, 66, kr0(fer["median"]), 30, 500, prop=True)
        d_.t(14, 84, "median Kjedekost", 10, 400, GRAY)
        fp = KL["ferdige"]["forsterkning_per_rolle"]
        for i, r in enumerate(ROLES):
            y = 114 + i * 26
            d_.t(14, y, r, 10)
            s_ = 136 / 13.0
            d_.rect(82 + fp[r]["q1"] * s_, y - 8, (fp[r]["q3"] - fp[r]["q1"]) * s_, 9, TINT)
            d_.rect(82 + fp[r]["median"] * s_ - 1, y - 10, 2, 13, INK)
        d_.t(14, 226, "Forsterkning, kvartiler og median", 10, 400, GRAY)

    def f_innsikt(d_):
        d_.t(14, 30, "Spillinnsikt, Spill 17, uke for uke", 11, 600)
        for i, r in enumerate(ROLES):
            base = 72 + i * 42
            d_.t(14, base + 12, r, 9, 400, GRAY)
            bars(d_, 14, base - 34, 222, 34, S17[r]["ordre"], 0, 32, bw=222 / 36 * 0.6)
        d_.rect(14 + 222 / 36 * 10.5, 40, 1, 170, RED)
        d_.t(14 + 222 / 36 * 11, 234, "Uke 11", 10, 600)

    def f_student(d_):
        d_.t(14, 34, "Studentside: Sara Lunde", 14, 600)
        d_.t(14, 54, "Grossist, Spill 17", 10, 400, GRAY)
        for i, (s_, st) in enumerate([("Klassespill", "pågår"), ("Debrief", "ikke åpen"), ("Quiz", ""), ("Replay", ""), ("Individuell test", ""), ("Rapport", "")]):
            d_.t(14, 82 + i * 18, s_, 11)
            d_.t(TW - 14, 82 + i * 18, st or "låst", 10, 400, GRAY, "end")
        d_.t(14, 208, "Registrer manuelt", 11, 500, INK, under=True)
        d_.t(14, 228, "Send Melding", 11, 500, INK, under=True)

    def f_plenum(d_):
        d_.t(14, 30, "Alle spill i plenum", 11, 600)
        grid_micro(d_, 40, 10, 22.2, 33, 60, tall=False)

    def f_tverr(d_):
        d_.t(14, 30, "Tverrklasse-statistikk", 11, 600)
        fj = KL["fjoraaret"]
        fp = KL["ferdige"]
        d_.t(14, 70, kr0(fp["kjedekost"]["median"]), 26, 500, prop=True)
        d_.t(120, 70, "class-of-1994", 10, 400, GRAY)
        d_.t(14, 106, kr0(fj["median_kjedekost"]), 26, 500, GRAY, prop=True)
        d_.t(120, 106, fj["klasse"], 10, 400, GRAY)
        d_.t(14, 138, "Forsterkning, Fabrikk, median", 10, 400, GRAY)
        d_.t(14, 170, ganger(fp["forsterkning_per_rolle"]["Fabrikk"]["median"]), 22, 500, prop=True)
        d_.t(120, 170, ganger(fj["median_forsterkning_fabrikk"]), 22, 500, GRAY, prop=True)
        d_.para(14, 204, "Ulike klasser. Sammenlign forsiktig.", 10, 222, fill=GRAY, lh=14)

    def f_meld(d_):
        d_.t(14, 34, "Meldinger", 16, 600)
        for i, (a, b) in enumerate([("Noah, Spill 2", "i dag"), ("Spill som venter (4)", "i går"), ("Hele klassen", "24. nov")]):
            d_.t(14, 66 + i * 22, a, 12)
            d_.t(TW - 14, 66 + i * 22, b, 10, 400, GRAY, "end")
        d_.rect(14.5, 140.5, 221, 56, PAPER, INK, 0.7)
        d_.para(22, 158, "Hei Noah. Gruppa di venter på ordren din i Uke 19.", 11, 204, lh=15)
        d_.t(TW - 14, 224, "Send Melding", 11, 600, INK, "end", under=True)

    def f_test(d_):
        d_.t(14, 30, "Lærers testspill", 11, 600)
        d_.t(14, 46, "Du spiller. Tre KI-spillere.", 10, 400, GRAY)
        mini_eq(d_, 14, 92, 6, size=24, red=False)
        bars(d_, 14, 110, 222, 92, SP[:6], 0, 30, bw=20)
        d_.t(TW - 14, 222, "nå", 10, 600, INK, "end")

    def a_omr(d_):
        d_.t(14, 34, "Admin-område", 16, 600)
        for i, (a, b) in enumerate([("Klasser", 2), ("Klassespill", len(spill) + KL["fjoraaret"]["spill"]), ("Studenter", KL["roster"]["registrert"] + KL["roster"]["manuelt_registrert"])]):
            d_.t(14, 70 + i * 26, a, 13)
            d_.t(TW - 14, 70 + i * 26, b, 15, 500, INK, "end")
        d_.t(14, 170, "Revisjonslogg", 12, 500, INK, under=True)
        d_.t(14, 194, "Brukere og roller", 12, 500, INK, under=True)
        d_.t(14, 218, "KI-kostnad", 12, 500, INK, under=True)

    def a_bruk(d_):
        d_.t(14, 34, "Brukere og roller", 16, 600)
        for i, (a, b) in enumerate([("Bård", "Faglærer"), ("Sara Lunde", "Student"), ("Ida Solheim", "Student"), ("Mikkel Rye", "Student"), ("Assistent", "Hjelpelærer"), ("Drift", "Admin")]):
            d_.t(14, 66 + i * 26, a, 12)
            d_.t(TW - 14, 66 + i * 26, b, 11, 400, GRAY, "end")

    def a_ki(d_):
        d_.t(14, 34, "KI-kostnad", 16, 600)
        ki = [g["ki_seter"] for g in spill]
        d_.t(14, 74, sum(ki), 30, 500, prop=True)
        d_.t(14, 92, "KI-seter i class-of-1994", 10, 400, GRAY)
        bars(d_, 14, 110, 222, 80, ki, 0, 3, bw=222 / 60 * 0.6)
        d_.t(14, 212, "Per spill. Kostnaden føres per Klasse.", 10, 400, GRAY)

    student = [("Invitasjon og registrering", "Lenken fra e-posten gir konto.", s_inv), ("Logg inn", "Bare e-post og passord.", s_login), ("Regler før første ordre", "Regnestykket forklares med startverdier.", s_regler), ("Startoppgave", "Regn ut én Posisjon før du spiller.", s_start), ("Replay", "Tre KI-spillere. Oppdelingen er låst opp.", s_replay), ("Replay-gjennomgang", "Klassespill og Replay på samme skala.", s_gjenn), ("Individuell test", "Flervalg, tegneoppgave og langsvar.", s_test), ("KI-vurdering", "Merket, formativ, teller ikke.", s_ki), ("Studentrapport (PDF)", "Dine tall, din Forklaring og dine svar.", s_rapport), ("Alle spill side om side", "Klassen svinger likt. Ingen rangering.", s_alle)]
    faglaerer = [("Lærerhjem", "Klasser, neste Labtime, det som haster.", f_hjem), ("Klasserapport", "Kjedekost og Forsterkning i klassen.", f_rapport), ("Spillinnsikt", "Ett spill, uke for uke.", f_innsikt), ("Studentside", "Steg, logg og Melding for én student.", f_student), ("Alle spill i plenum", "60 grafer som kan vises på lerret.", f_plenum), ("Tverrklasse-statistikk", "I år og fjoråret.", f_tverr), ("Meldinger", "Til én, til dem som venter, til alle.", f_meld), ("Lærers testspill", "Prøv det selv før start.", f_test)]
    admin = [("Admin-område", "Drift av plattformen.", a_omr), ("Brukere og roller", "Hvem som er hva.", a_bruk), ("KI-kostnad", "KI-seter og forbruk per Klasse.", a_ki)]

    alle = [("Student", x) for x in student] + [("Faglærer", x) for x in faglaerer] + [("Admin", x) for x in admin]
    y0 = 136
    rh = TH + 92
    seen = set()
    for i, (group, (title, line, fn)) in enumerate(alle):
        cx = 60 + (i % 7) * (TW + gut)
        cy = y0 + (i // 7) * (rh + 70)
        if group not in seen:
            d.t(cx, cy - 12, group, 22, 600)
            seen.add(group)
        d.rect(cx + 0.5, cy + 0.5, TW - 1, TH - 1, PAPER, TINT, 1)
        d.open(cx, cy)
        fn(d)
        d.close()
        d.t(cx, cy + TH + 24, title, 15, 600)
        d.para(cx, cy + TH + 44, line, 13, TW - 4, fill=GRAY, lh=17)
    d.save()


PAGES = {"01-landing": page_01, "02-laerer-klasse": page_02, "03-laerer-spill": page_03, "04-student-hjem": page_04,
         "05-spill": page_05, "06-spilldynamikk": page_06, "07-debrief": page_07, "08-laerer-oversikt": page_08,
         "09-alle-sider": page_09, "10-pedagogikk": page_10}


def main():
    want = sys.argv[1:]
    for name, fn in PAGES.items():
        if not want or any(w in name for w in want):
            fn()
            print("skrev", name)


if __name__ == "__main__":
    main()
