"""Felles system for konsept 08 Rapporten: tokens, tekstmaling, grafer og regel-kommentarer."""
import json
import re
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
FX = json.loads((HERE.parent / "_shared" / "fixture.json").read_text(encoding="utf-8"))

# Tokens. Palett: blek grågrønn, skogsvart tekst, én okerrød serie.
BG = "#E7EDE8"       # Grågrønn grunn bak skjermene
PAPER = "#F5F8F4"    # Papir, skjermflate
WASH = "#E2E9E3"     # Stille flate: felt, gap, band
GRID = "#D2DCD4"     # Hjelpelinje
FRAME = "#AEBDB3"    # Ramme rundt enheter
INK = "#12302B"      # Tekst
INK2 = "#43605A"     # Sekundær tekst
INK3 = "#566F68"     # Akseetikett
OCHRE = "#A5471C"    # Fremhevet serie
OCHRE_W = "#EADBCF"  # Okerrød vask, bare mellom inn og ut
FOREST = "#14705F"   # Min ordre
SAGE = "#6C887C"     # Levering og kontekst
WHITE = "#FBFCFA"

ROLES = ["Detaljist", "Grossist", "Distributør", "Fabrikk"]
S17 = FX["spill17"]["serier"]
SARA = S17["Grossist"]
NETTO = [a - b for a, b in zip(SARA["lager"], SARA["restordre"])]
POSISJON = [n + p for n, p in zip(NETTO, SARA["paa_vei"])]
SIM1 = FX["bare_sara_teller_paa_vei"]
SIM2 = FX["alle_teller_paa_vei"]
SIMS = SIM1["serier"]["Grossist"]
NETTO_SIM = [a - b for a, b in zip(SIMS["lager"], SIMS["restordre"])]
KL = FX["klasse"]

FONT_IMPORT = ("@import url('https://fonts.googleapis.com/css2?family=Spectral:wght@400;500;600"
               "&amp;family=Libre+Franklin:wght@400;500;600&amp;display=swap');")
SANS = "'Libre Franklin','Helvetica Neue',Arial,sans-serif"
SERIF = "'Spectral','Iowan Old Style',Georgia,serif"


def v(series, week):
    """Verdi for en Uke (1-basert)."""
    return series[week - 1]


def nb(x, dec=2):
    """Norsk tallformat: 2 266,00."""
    s = f"{abs(x):,.{dec}f}".replace(",", " ").replace(".", ",")
    return ("−" if x < 0 else "") + s


def sg(x):
    return ("−" if x < 0 else "") + str(abs(int(x)))


def fx(x):
    return f"{x:.1f}".replace(".", ",") + "×"


def tw(s, size, fam="s"):
    """Anslått tekstbredde i piksler."""
    s = s.replace("**", "")
    narrow, wide = set("iltfjrI.,:;'|()!·- "), set("mwMWØÆæœ—−")
    n, w, cap, dig = (0.30, 0.76, 0.65, 0.52) if fam == "s" else (0.31, 0.82, 0.68, 0.60)
    base = 0.495 if fam == "s" else 0.545
    total = 0.0
    for c in s:
        if c == " ":
            total += 0.25 if fam == "s" else 0.27
        elif c in narrow:
            total += n
        elif c in wide:
            total += w
        elif c.isdigit():
            total += dig
        elif c.isupper():
            total += cap
        else:
            total += base
    return total * size


def wrap(s, width, size, fam="s"):
    """Bryt tekst med **fet** markering til linjer som passer i width."""
    bold = False
    lines, cur, cur_open = [], [], False
    for word in s.split():
        trial = " ".join(cur + [word])
        if cur and tw(trial, size, fam) > width:
            line = " ".join(cur)
            lines.append(("**" if cur_open else "") + line + ("**" if bold else ""))
            cur, cur_open = [word], bold
        else:
            if not cur:
                cur_open = bold
            cur.append(word)
        bold ^= word.count("**") % 2 == 1
    if cur:
        lines.append(("**" if cur_open else "") + " ".join(cur))
    return lines


class Doc:
    def __init__(self, page, width, height, title, desc, bg=BG):
        self.page, self.W, self.H, self.title, self.desc = page, width, height, title, desc
        self.o = []
        self.defs = []
        self._clip = 0
        self.rect(0, 0, width, height, fill=bg)

    # Grunnformer
    def add(self, s):
        self.o.append(s)

    def rect(self, x, y, w, h, fill="none", stroke=None, rx=0, sw=1, op=None):
        a = f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}"'
        if rx:
            a += f' rx="{rx}"'
        if stroke:
            a += f' stroke="{stroke}" stroke-width="{sw}"'
        if op is not None:
            a += f' opacity="{op}"'
        self.add(a + "/>")

    def line(self, x1, y1, x2, y2, stroke=GRID, sw=1, dash=None, cap=None):
        a = f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{sw}"'
        if dash:
            a += f' stroke-dasharray="{dash}"'
        if cap:
            a += f' stroke-linecap="{cap}"'
        self.add(a + "/>")

    def path(self, d, stroke=INK, sw=1, fill="none", dash=None, op=None):
        a = f'<path d="{d}" fill="{fill}"'
        if stroke:
            a += f' stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round" stroke-linecap="round"'
        if dash:
            a += f' stroke-dasharray="{dash}"'
        if op is not None:
            a += f' opacity="{op}"'
        self.add(a + "/>")

    def circle(self, x, y, r, fill=PAPER, stroke=None, sw=1):
        a = f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}"'
        if stroke:
            a += f' stroke="{stroke}" stroke-width="{sw}"'
        self.add(a + "/>")

    def g(self, x=0, y=0, scale=None):
        tr = f"translate({x:.1f} {y:.1f})" + (f" scale({scale})" if scale else "")
        self.add(f'<g transform="{tr}">')

    def end(self):
        self.add("</g>")

    # Tekst
    def t(self, x, y, s, size=14, fam="f", fill=INK, weight=400, anchor="start", prop=False, halo=None):
        cls = {"s": "d08-s", "f": "d08-p" if prop else "d08-f"}[fam]
        a = f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}" font-size="{size}" fill="{fill}"'
        if halo:
            a += f' stroke="{halo}" stroke-width="3" stroke-linejoin="round" paint-order="stroke"'
        if weight != 400:
            a += f' font-weight="{weight}"'
        if anchor != "start":
            a += f' text-anchor="{anchor}"'
        parts = s.split("**")
        if len(parts) == 1:
            body = escape(s)
        else:
            body = ""
            for i, part in enumerate(parts):
                if not part:
                    continue
                body += f'<tspan font-weight="600">{escape(part)}</tspan>' if i % 2 else escape(part)
        self.add(a + f">{body}</text>")

    def para(self, x, y, width, s, size=16, fam="s", fill=INK, lh=None, weight=400, anchor="start", halo=None):
        """Skriv brutt avsnitt. y er første grunnlinje. Returnerer y for neste grunnlinje."""
        lh = lh or round(size * 1.42)
        for line in wrap(s, width, size, fam):
            self.t(x, y, line, size, fam, fill, weight, anchor, halo=halo)
            y += lh
        return y

    # Regel-kommentaren: konseptets dresskode
    def ring(self, x, y, r=3.5, stroke=INK):
        self.circle(x, y, r, fill=PAPER, stroke=stroke, sw=1.25)

    def note(self, px, py, tx, ty, s, width, size=14, side="r", route="flag", ring=True, lh=None, fill=INK, halo=PAPER):
        """Regel-kommentar festet til punktet (px, py).

        tx: x for regelen ved tekstblokka. ty: toppen av blokka. side: teksten til høyre eller venstre for regelen.
        route: flag = loddrett regel langs blokka, hv = vannrett fra punktet og så loddrett langs blokka,
        vh = loddrett fra punktet og så vannrett til første linje.
        """
        lh = lh or round(size * 1.3)
        lines = wrap(s, width, size, "s")
        h = len(lines) * lh
        top, bot = ty + 1, ty + h - 1
        mid = ty + size * 0.62
        gap = 7
        if route == "vh":
            self.path(f"M{px:.1f} {py:.1f}V{mid:.1f}H{tx:.1f}", stroke=INK2, sw=0.75)
        elif route == "hv":
            far = bot if abs(top - py) > abs(bot - py) else top
            near = top if far == bot else bot
            ystart = py
            self.path(f"M{px:.1f} {ystart:.1f}H{tx:.1f}", stroke=INK2, sw=0.75)
            lo, hi = min(py, top), max(py, bot)
            self.line(tx, lo, tx, hi, stroke=INK2, sw=0.75)
        else:  # flag
            lo, hi = min(py, top), max(py, bot)
            self.line(tx, lo, tx, hi, stroke=INK2, sw=0.75)
        if ring:
            self.ring(px, py)
        x = tx + gap if side == "r" else tx - gap
        anchor = "start" if side == "r" else "end"
        y = ty + size * 0.92
        for line in lines:
            self.t(x, y, line, size, "s", fill, 400, anchor, halo=halo)
            y += lh
        return ty + h

    def bracket(self, x1, y1, x2, y2, ytop, label=None, size=13):
        """Parentes mellom to punkter: slipp fra hvert punkt opp til samme hylle. For forsinkelsen (P2)."""
        self.path(f"M{x1:.1f} {y1:.1f}V{ytop:.1f}H{x2:.1f}V{y2:.1f}", stroke=INK2, sw=0.75)
        self.ring(x1, y1)
        self.ring(x2, y2)
        if label:
            self.t((x1 + x2) / 2, ytop - 5, label, size, "f", INK2, 500, "middle")

    def key(self, x, y, items, size=13, gap=16):
        """Nøkkelen nederst i grafen. items: (type, farge, tekst). type: line, thick, ring, wash, text."""
        cx = x
        for kind, color, label in items:
            if kind in ("line", "thick"):
                self.line(cx, y - size * 0.34, cx + 18, y - size * 0.34, color, 2.5 if kind == "thick" else 1.75)
                cx += 23
            elif kind == "ring":
                self.ring(cx + 4, y - size * 0.34)
                cx += 13
            elif kind == "wash":
                self.rect(cx, y - size * 0.8, 18, size * 0.9, fill=color)
                cx += 23
            self.t(cx, y, label, size, "f", INK2 if kind != "text" else INK3)
            cx += tw(label, size, "f") + gap
        return cx

    # Enheter
    def phone(self, x, y, w=390, h=844, scale=None):
        self.g(x, y, scale)
        self.rect(0, 0, w, h, fill=PAPER, stroke=FRAME, rx=30, sw=1)

    def laptop(self, x, y, w, h):
        self.g(x, y)
        self.rect(0, 0, w, h, fill=PAPER, stroke=FRAME, rx=8, sw=1)

    def button(self, x, y, w, h, label, primary=True, size=15):
        if primary:
            self.rect(x, y, w, h, fill=INK, rx=4)
            self.t(x + w / 2, y + h / 2 + size * 0.35, label, size, "f", WHITE, 500, "middle")
        else:
            self.rect(x, y, w, h, fill="none", stroke=INK2, rx=4, sw=1)
            self.t(x + w / 2, y + h / 2 + size * 0.35, label, size, "f", INK, 500, "middle")

    def chevron(self, x, y, s=5, stroke=INK2, down=False):
        if down:
            self.path(f"M{x - s} {y - s / 2}L{x} {y + s / 2}L{x + s} {y - s / 2}", stroke=stroke, sw=1.25)
        else:
            self.path(f"M{x - s / 2} {y - s}L{x + s / 2} {y}L{x - s / 2} {y + s}", stroke=stroke, sw=1.25)

    def lock(self, x, y, stroke=INK2):
        """Tegnet hengelås, 12 px."""
        self.rect(x, y + 5, 10, 8, fill="none", stroke=stroke, rx=1, sw=1.1)
        self.path(f"M{x + 2} {y + 5}V{y + 3}a3 3 0 0 1 6 0V{y + 5}", stroke=stroke, sw=1.1)

    def save(self):
        css = (
            f"{FONT_IMPORT}"
            f".d08-s{{font-family:{SERIF};font-feature-settings:'lnum' 1,'kern' 1}}"
            f".d08-f{{font-family:{SANS};font-variant-numeric:lining-nums tabular-nums}}"
            f".d08-p{{font-family:{SANS};font-variant-numeric:lining-nums proportional-nums}}"
        )
        out = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.W} {self.H}" font-family="{SERIF}" '
            f'id="d08-{self.page}-root" role="img" aria-labelledby="d08-{self.page}-title d08-{self.page}-desc">'
            f'<title id="d08-{self.page}-title">{escape(self.title)}</title>'
            f'<desc id="d08-{self.page}-desc">{escape(self.desc)}</desc>'
            f"<style>{css}</style>" + ("<defs>" + "".join(self.defs) + "</defs>" if self.defs else "")
            + "\n".join(self.o) + "</svg>"
        )
        return out


class Chart:
    """Ukegraf med sann skala. Høyre kant er det siste viste punktet."""

    def __init__(self, d, x, y, w, h, w0, w1, v0, v1):
        self.d, self.x, self.y, self.w, self.h = d, x, y, w, h
        self.w0, self.w1, self.v0, self.v1 = w0, w1, v0, v1

    def X(self, week):
        return self.x + (week - self.w0) / (self.w1 - self.w0) * self.w

    def Y(self, val):
        return self.y + self.h - (val - self.v0) / (self.v1 - self.v0) * self.h

    def P(self, week, val):
        return self.X(week), self.Y(val)

    def grid(self, ticks, labels=True, size=13, x2=None, lx=None):
        for tick in ticks:
            yy = self.Y(tick)
            self.d.line(self.x, yy, x2 or self.x + self.w, yy, INK2 if tick == 0 else GRID, 1 if tick == 0 else 0.75)
            if labels:
                self.d.t((lx if lx is not None else self.x - 7), yy + size * 0.35, sg(tick), size, "f", INK3, 400, "end")

    def weeks(self, ticks, size=13, first_word=True, y=None):
        yy = y if y is not None else self.y + self.h + size + 6
        for i, tick in enumerate(ticks):
            label = (f"Uke {tick}" if (i == 0 and first_word) else str(tick))
            anchor = "start" if (i == 0 and first_word) else "middle"
            self.d.t(self.X(tick) - (2 if anchor == "start" else 0), yy, label, size, "f", INK3, 400, anchor)

    def now(self, week, label="nå", size=13, top=None):
        xx = self.X(week)
        y0 = top if top is not None else self.y
        self.d.line(xx, y0, xx, self.y + self.h + 4, INK, 1)
        self.d.t(xx, self.y + self.h + size + 6, label, size, "f", INK, 600, "middle")

    def poly(self, s, wf, wt, stroke=OCHRE, sw=2.5, dash=None, op=None):
        pts = [f"{self.X(k):.1f} {self.Y(v(s, k)):.1f}" for k in range(wf, wt + 1)]
        self.d.path("M" + "L".join(pts), stroke=stroke, sw=sw, dash=dash, op=op)

    def step(self, s, wf, wt, stroke=FOREST, sw=1.75, op=None):
        """Trappelinje for strømmer: en Ukes verdi gjelder fram til ukas slutt."""
        d = f"M{self.X(wf):.1f} {self.Y(v(s, wf)):.1f}"
        for k in range(wf + 1, wt + 1):
            d += f"V{self.Y(v(s, k)):.1f}H{self.X(k):.1f}"
        self.d.path(d, stroke=stroke, sw=sw, op=op)

    def gap(self, a, b, wf, wt, fill=OCHRE_W):
        """Flaten mellom to trappelinjer, a over og b under der a > b. Arealet er endringen i netto lager."""
        for k in range(wf + 1, wt + 1):
            x1, x2 = self.X(k - 1), self.X(k)
            y1, y2 = self.Y(v(a, k)), self.Y(v(b, k))
            top, bot = min(y1, y2), max(y1, y2)
            if bot - top > 0.1:
                self.d.rect(x1, top, x2 - x1, bot - top, fill=fill)
