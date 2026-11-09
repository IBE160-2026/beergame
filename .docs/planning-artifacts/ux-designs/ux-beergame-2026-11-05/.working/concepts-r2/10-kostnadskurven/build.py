"""Konsept 10 Kostnadskurven («Kurve»). Genererer alle SVG-er fra ../_shared/fixture.json.

Kjør: uv run python build.py
Alle tall i grafer og tekst om spill leses eller regnes fra fixturen. V-en er c(x) = 0,50·max(x,0) + 1,00·max(−x,0).
"""
import json
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
FX = json.loads((HERE.parent / "_shared" / "fixture.json").read_text(encoding="utf-8"))
S17 = FX["spill17"]["serier"]
ROLLER = ["Detaljist", "Grossist", "Distributør", "Fabrikk"]
NAVN = {"Detaljist": "Ida", "Grossist": "Sara", "Distributør": "Mikkel", "Fabrikk": "Jonas"}
G = S17["Grossist"]
SIM_SARA = FX["bare_sara_teller_paa_vei"]
SIM_ALLE = FX["alle_teller_paa_vei"]
REPLAY = FX["replay_sara"]
KL = FX["klasse"]
YR_KL = max(abs(v) for sp_ in KL["spill"] for r_ in ROLLER for v in sp_["netto_lager"][r_])  # Sann felles skala, uten kutt.

# Palett
BG = "#EEF2F6"       # Lys blågrå grunn
PAPER = "#FFFFFF"    # Skjermflate
INK = "#13294B"      # Dyp marineblå, tekst og hovedlinje
SEC = "#44546E"      # Sekundærtekst
MUT = "#5F6F88"      # Dempet tekst
GRID = "#E1E6ED"     # Hjelpelinje
HAIR = "#C5CEDA"     # Akser og rammer
OKER = "#B4711A"     # Restordrekostnad
BLA = "#1C76B8"      # Lagerkostnad
OKER_F = "#EBD3AC"   # Oker flate
BLA_F = "#BFD9EC"    # Blå flate
SIG = "#A5232F"      # Signal, bare for nær overtakelse
SIG_F = "#F9ECED"
TINT = "#F4F6F9"
ROLLE_TONE = {"Detaljist": "#A3B3C8", "Grossist": "#2F5C94", "Distributør": "#7C90AC", "Fabrikk": "#54698A"}

FONT_R = "'Alegreya',Georgia,'Times New Roman',serif"
FONT_S = "'Alegreya Sans','Gill Sans','Trebuchet MS',Verdana,sans-serif"
STYLE = f"""@import url('https://fonts.googleapis.com/css2?family=Alegreya:wght@400;500;700&amp;family=Alegreya+Sans:wght@400;500;700&amp;display=swap');
.d10-r{{font-family:{FONT_R};font-variant-numeric:lining-nums proportional-nums}}
.d10-s{{font-family:{FONT_S};font-variant-numeric:lining-nums proportional-nums}}
.d10-n{{font-variant-numeric:lining-nums tabular-nums}}"""


# ---------- tall og tekst ----------
def kr(v, d=2):
    s = f"{abs(v):,.{d}f}".replace(",", " ").replace(".", ",")
    return ("−" + s) if v < 0 else s


def sgn(v):
    if v > 0:
        return f"+{v:g}".replace(".", ",")
    return f"{v:g}".replace("-", "−").replace(".", ",")


def c_of(x):
    return 0.5 * max(x, 0) + max(-x, 0)


def nets(s):
    return [a - b for a, b in zip(s["lager"], s["restordre"])]


def sendt(s, wk):
    i = wk - 1
    prev_l = s["lager"][i - 1] if i else 12
    prev_r = s["restordre"][i - 1] if i else 0
    return min(s["innkommende_ordre"][i] + prev_r, prev_l + s["levering"][i])


def posisjon(s, wk):
    i = wk - 1
    return s["lager"][i] - s["restordre"][i] + s["paa_vei"][i]


NG = nets(G)


def tw(s, size, bold=False):
    n = 0.0
    for ch in str(s):
        if ch in "iljtfrI.,:;'· () ":
            n += 0.29
        elif ch in "mwMWÆæ":
            n += 0.78
        elif ch.isupper():
            n += 0.62
        else:
            n += 0.5
    return n * size * (1.04 if bold else 1)


def wrap(s, width, size, bold=False):
    lines, cur = [], ""
    for word in s.split(" "):
        test = (cur + " " + word).strip()
        if tw(test, size, bold) <= width or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


# ---------- primitive ----------
def t(x, y, s, size=14, f="s", c=INK, w=400, a="start", num=False):
    cls = f"d10-{f}" + (" d10-n" if num else "")
    wt = f' font-weight="{w}"' if w != 400 else ""
    an = f' text-anchor="{a}"' if a != "start" else ""
    return f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}" font-size="{size}" fill="{c}"{wt}{an}>{escape(str(s), quote=False)}</text>'


def para(x, y, s, width, size=14, lh=None, f="s", c=INK, w=400, a="start"):
    lh = lh or size * 1.36
    return "".join(t(x, y + i * lh, ln, size, f, c, w, a) for i, ln in enumerate(wrap(s, width, size, w >= 600)))


def para_h(s, width, size=14, lh=None, w=400):
    lh = lh or size * 1.36
    return len(wrap(s, width, size, w >= 600)) * lh


def rect(x, y, w, h, fill="none", stroke=None, r=0, sw=1, op=None):
    st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    rr = f' rx="{r}"' if r else ""
    oo = f' opacity="{op}"' if op is not None else ""
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}"{st}{rr}{oo}/>'


def line(x1, y1, x2, y2, c=HAIR, sw=1, dash=None, cap=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    cp = f' stroke-linecap="{cap}"' if cap else ""
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{c}" stroke-width="{sw}"{d}{cp}/>'


def circ(x, y, r, fill=INK, stroke=None, sw=1, op=None):
    st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    oo = f' opacity="{op}"' if op is not None else ""
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}"{st}{oo}/>'


def poly(pts, c=INK, sw=2, dash=None, fill="none", op=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    oo = f' opacity="{op}"' if op is not None else ""
    p = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    return f'<polyline points="{p}" fill="{fill}" stroke="{c}" stroke-width="{sw}" stroke-linejoin="round" stroke-linecap="round"{d}{oo}/>'


def area(pts, fill):
    p = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    return f'<polygon points="{p}" fill="{fill}"/>'


def chevron(x, y, c=SEC, s=5):
    return poly([(x, y - s), (x + s, y), (x, y + s)], c, 1.6)


def button(x, y, w, h, label, primary=True, size=16, c=INK):
    fill = c if primary else PAPER
    tx = PAPER if primary else c
    return rect(x, y, w, h, fill, None if primary else c, 6, 1.2) + t(x + w / 2, y + h / 2 + size * 0.34, label, size, "s", tx, 500 if not primary else 700, "middle")


def field(x, y, w, h, label, value, size=14, muted=False):
    return (
        t(x, y - 7, label, 13, "s", SEC)
        + rect(x, y, w, h, PAPER, HAIR, 4)
        + t(x + 10, y + h / 2 + size * 0.34, value, size, "s", MUT if muted else INK)
    )


def demodata(x, y, a="start", size=13, extra=""):
    return t(x, y, "Demodata" + extra, size, "s", MUT, 400, a)


class Page:
    def __init__(self, name, side, W, H, title, desc, bg=BG):
        self.name, self.side, self.W, self.H = name, side, W, H
        self.title, self.desc, self.bg = title, desc, bg
        self.o = []

    def add(self, *parts):
        self.o.extend(parts)

    def save(self):
        body = "".join(self.o)
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" id="d10-{self.side}-root" viewBox="0 0 {self.W} {self.H}" '
            f'font-family="{FONT_S}"><title>{escape(self.title, quote=False)}</title><desc>{escape(self.desc, quote=False)}</desc>'
            f"<style>{STYLE}</style>{rect(0, 0, self.W, self.H, self.bg)}{body}</svg>"
        )
        (HERE / f"{self.name}.svg").write_text(svg, encoding="utf-8")


def phone(x, y, content, scale=1.0, side="", label=""):
    frame = rect(0, 0, 390, 844, PAPER, HAIR, 34, 1.2)
    return f'<g transform="translate({x},{y}) scale({scale})">{frame}{content}</g>'


# ---------- V-diagrammet ----------
class V:
    """Lærebokdiagrammet. Sann skala: x er netto lager, y er kroner denne uka."""

    def __init__(self, x, y, w, h, xr=40, yr=40):
        self.x, self.y, self.w, self.h, self.xr, self.yr = x, y, w, h, xr, yr

    def sx(self, v):
        return self.x + (v + self.xr) / (2 * self.xr) * self.w

    def sy(self, c):
        return self.y + self.h - c / self.yr * self.h

    def frame(self, fs=13, ticks=None, ygrid=(10, 20, 30), arm=2.4, axis="Netto lager, enheter", ytitle="Kroner denne uka", ylab=True):
        o = []
        ticks = ticks if ticks is not None else (-40, -20, 0, 20, 40)
        for c in ygrid:
            yy = self.sy(c)
            o.append(line(self.x, yy, self.x + self.w, yy, GRID, 1))
            if ylab:
                lab = f"{c} kr"
                o.append(t(self.x, yy - 4, lab, fs, "s", MUT, num=True))
        o.append(line(self.x, self.sy(0), self.x + self.w, self.sy(0), HAIR, 1))
        for v in ticks:
            xx = self.sx(v)
            o.append(line(xx, self.sy(0), xx, self.sy(0) + 4, HAIR, 1))
            o.append(t(xx, self.sy(0) + 4 + fs + 1, sgn(v) if v else "0", fs, "s", SEC, a="middle" if abs(v) < self.xr else ("start" if v < 0 else "end"), num=True))
        if ytitle:
            o.append(t(self.x, self.y - 8, ytitle, fs, "s", SEC))
        if axis:
            o.append(t(self.x + self.w / 2, self.sy(0) + 4 + 2 * fs + 6, axis, fs, "s", SEC, a="middle"))
        xl = min(self.xr, self.yr)
        o.append(poly([(self.sx(0), self.sy(0)), (self.sx(-xl), self.sy(xl))], OKER, arm))
        xh = min(self.xr, self.yr * 2)
        o.append(poly([(self.sx(0), self.sy(0)), (self.sx(xh), self.sy(xh * 0.5))], BLA, arm))
        return "".join(o)

    def arm_labels(self, fs=13, lower=True):
        lx, ly = self.x, self.sy(0) - fs * 2.6
        rx = self.x + self.w
        return (
            t(lx, ly, "Restordre", fs, "s", INK, 700)
            + t(lx, ly + fs * 1.3, "1,00 kr per enhet", fs, "s", SEC)
            + t(rx, ly, "Lager", fs, "s", INK, 700, "end")
            + t(rx, ly + fs * 1.3, "0,50 kr per enhet", fs, "s", SEC, a="end")
        )

    def trail(self, ns, week, n=8, rmin=2.6, rmax=4.2):
        """Sporet av de siste ukene, eldst lysest. Uker på samme punkt tegnes én gang."""
        o, seen = [], {}
        first = max(0, week - 1 - n)
        for i in range(first, week - 1):
            seen[ns[i]] = i
        for v, i in sorted(seen.items(), key=lambda kv: kv[1]):
            age = (week - 1 - i) / max(1, n)
            r = rmax - (rmax - rmin) * age
            o.append(circ(self.sx(v), self.sy(c_of(v)), f"{r:.1f}", INK, PAPER, 1, f"{1 - 0.62 * age:.2f}"))
        return "".join(o)

    def allpts(self, ns, r=3, fill=INK, op=0.75):
        return "".join(circ(self.sx(v), self.sy(c_of(v)), r, fill, PAPER, 0.8, op) for v in ns)

    def nowpt(self, v, r=7):
        return circ(self.sx(v), self.sy(c_of(v)), r, INK, PAPER, 2)

    def ring_on_axis(self, v, label, color=INK, fs=13, up=16, a="middle"):
        xx = self.sx(v)
        y0 = self.sy(0)
        return (
            circ(xx, y0, 5.5, PAPER, color, 2)
            + line(xx, y0 - 6, xx, y0 - up, color, 1)
            + t(xx, y0 - up - 4, label, fs, "s", INK, 700, a)
        )


class TS:
    """Tidsgraf der høyre kant er nå."""

    def __init__(self, x, y, w, h, w0, w1, v0, v1):
        self.x, self.y, self.w, self.h, self.w0, self.w1, self.v0, self.v1 = x, y, w, h, w0, w1, v0, v1

    def sx(self, wk):
        return self.x + (wk - self.w0) / max(1e-9, self.w1 - self.w0) * self.w

    def sy(self, v):
        return self.y + self.h - (v - self.v0) / (self.v1 - self.v0) * self.h


def cost_line(ts, s, upto, sw=2.4):
    """Løpende Totalkostnad. Hver ukes stykke får fargen til armen på V-en den uka lå på."""
    o = []
    cum = s["kost_sum"]
    ns = nets(s)
    for i in range(0, upto):
        x0 = ts.sx(i) if i else ts.sx(ts.w0)
        y0 = ts.sy(cum[i - 1] if i else 0)
        x1, y1 = ts.sx(i + 1), ts.sy(cum[i])
        col = OKER if ns[i] < 0 else BLA
        if i == 0 and ts.w0 == 1:
            x0, y0 = x1, y1
            continue
        o.append(line(x0, y0, x1, y1, col, sw, cap="round"))
    return "".join(o)


def cum_parts(s, upto=None):
    upto = upto or len(s["lager"])
    a, b, la, lb = [], [], 0.0, 0.0
    for i in range(upto):
        la += 0.5 * s["lager"][i]
        lb += s["restordre"][i]
        a.append(la)
        b.append(lb)
    return a, b


def cum_stack(ts, s, upto=None, line_total=True):
    a, b = cum_parts(s, upto)
    n = len(a)
    base = ts.sy(0)
    lower = [(ts.sx(i + 1), ts.sy(a[i])) for i in range(n)]
    upper = [(ts.sx(i + 1), ts.sy(a[i] + b[i])) for i in range(n)]
    o = [
        area([(ts.sx(1), base)] + lower + [(ts.sx(n), base)], BLA_F),
        area(lower + list(reversed(upper)), OKER_F),
        poly(lower, BLA, 1.2),
    ]
    if line_total:
        o.append(poly(upper, INK, 2))
    return "".join(o)


def sim_line(ts, s, upto=None, sw=1.8, c=INK, dash="5 4"):
    upto = upto or len(s["kost_sum"])
    return poly([(ts.sx(i + 1), ts.sy(s["kost_sum"][i])) for i in range(upto)], c, sw, dash)


def inout_chart(ts, s, upto):
    """P1: Levering (inn) og innkommende ordre (ut). Arealet mellom er endringen i netto lager."""
    o = []
    inn, ut = s["levering"], s["innkommende_ordre"]
    w0 = int(ts.w0)
    for i in range(w0 - 1, upto - 1):
        x0, x1 = ts.sx(i + 1), ts.sx(i + 2)
        a0, a1, b0, b1 = inn[i], inn[i + 1], ut[i], ut[i + 1]
        fill = BLA_F if (a0 + a1) >= (b0 + b1) else OKER_F
        o.append(area([(x0, ts.sy(a0)), (x1, ts.sy(a1)), (x1, ts.sy(b1)), (x0, ts.sy(b0))], fill))
    o.append(poly([(ts.sx(i + 1), ts.sy(ut[i])) for i in range(w0 - 1, upto)], SEC, 1.4))
    o.append(poly([(ts.sx(i + 1), ts.sy(inn[i])) for i in range(w0 - 1, upto)], INK, 1.8))
    return "".join(o)


def order_chart(ts, s, upto, typed=None):
    """P2: Egen ordre som stolper og levering som linje, i samme skala."""
    o = []
    bw = max(2.0, (ts.sx(2) - ts.sx(1)) * 0.5)
    w0 = int(ts.w0)
    for i in range(w0 - 1, upto):
        v = s["ordre"][i]
        if typed is not None and i == upto - 1:
            v = typed
        o.append(rect(ts.sx(i + 1) - bw / 2, ts.sy(v), bw, ts.sy(0) - ts.sy(v), "#9DB0C9"))
    o.append(poly([(ts.sx(i + 1), ts.sy(s["levering"][i])) for i in range(w0 - 1, upto)], INK, 1.8))
    return "".join(o)


def nowline(ts, label="nå", fs=13):
    xx = ts.x + ts.w
    return line(xx, ts.y, xx, ts.y + ts.h, HAIR, 1) + t(xx, ts.y + ts.h + fs + 3, label, fs, "s", SEC, a="end")


# ---------- spillskjermen ----------
def play_v(week, y0=112, h=240, x0=22, w=346, callout=True, s=None, net_series=None, fs=13, n=8):
    s = s or G
    ns = net_series or nets(s)
    v = V(x0, y0, w, h)
    o = [v.frame(fs=fs, ygrid=(20, 30) if h < 200 else (10, 20, 30)), v.arm_labels(fs=fs), v.trail(ns, week, n=n), v.nowpt(ns[week - 1])]
    cur = ns[week - 1]
    if callout:
        cx = x0 + w / 2
        cy = y0 + 18
        word = f"{abs(cur)} i restordre" if cur < 0 else (f"{cur} på lager" if cur > 0 else "Verken lager eller restordre")
        o.append(line(v.sx(cur), v.sy(c_of(cur)) - 8, cx, cy + 34, HAIR, 1))
        o.append(t(cx, cy, word, 16, "s", INK, 700, "middle"))
        o.append(t(cx, cy + 22, f"{kr(c_of(cur))} kr denne uka", 15, "s", SEC, a="middle"))
    return "".join(o)


def play_header(week, s=None, rolle="Grossist · Sara"):
    s = s or G
    return (
        t(22, 62, f"Uke {week}", 32, "r", INK, 700)
        + t(22, 86, rolle, 14, "s", SEC)
        + t(368, 44, "Totalkostnad", 13, "s", SEC, a="end")
        + t(368, 72, f"{kr(s['kost_sum'][week - 1])} kr", 26, "r", INK, 700, "end")
    )


def play_cost(week, y0, h=62, s=None, labels=True):
    s = s or G
    ymax = max(10, s["kost_sum"][week - 1] * 1.08)
    ts = TS(22, y0, 346, h, 1, week, 0, ymax)
    o = [t(22, y0 - 8, "Totalkostnad over tid", 13, "s", SEC)]
    o.append(line(22, ts.sy(0), 368, ts.sy(0), HAIR, 1))
    o.append(cost_line(ts, s, week))
    o.append(circ(ts.sx(week), ts.sy(s["kost_sum"][week - 1]), 3.5, INK))
    o.append(t(22, ts.sy(0) + 17, "Uke 1", 13, "s", MUT))
    o.append(t(368, ts.sy(0) + 17, "nå", 13, "s", SEC, a="end"))
    if labels:
        ns = nets(s)
        lag = [i for i in range(week) if ns[i] > 0]
        res = [i for i in range(week) if ns[i] < 0]
        if lag:
            i = lag[len(lag) // 2]
            o.append(t(ts.sx(i + 1), ts.sy(s["kost_sum"][i]) - 8, "Lager", 13, "s", SEC, a="middle"))
        if res and tw("Restordre", 13) < (ts.sx(res[-1] + 1) - ts.sx(res[0] + 1)) + 30:
            o.append(t(ts.sx(res[len(res) // 2] + 1) - 12, ts.sy(s["kost_sum"][res[len(res) // 2]]) - 8, "Restordre", 13, "s", SEC, a="end"))
    return "".join(o)


def play_strip(week, y0, s=None, link=True):
    s = s or G
    i = week - 1
    cols = [("Innkommende ordre", s["innkommende_ordre"][i]), ("Levering", s["levering"][i]), ("På vei", s["paa_vei"][i])]
    xs = [22, 170, 288]
    o = [line(22, y0, 368, y0, GRID, 1)]
    for (lab, val), xx in zip(cols, xs):
        o.append(t(xx, y0 + 22, lab, 13, "s", SEC))
        o.append(t(xx, y0 + 50, val, 24, "r", INK, 700))
    if link:
        o.append(t(22, y0 + 80, "Alle tall og regnestykket", 14, "s", INK, 500))
        o.append(line(22, y0 + 85, 22 + tw("Alle tall og regnestykket", 14), y0 + 85, HAIR, 1))
        o.append(chevron(22 + tw("Alle tall og regnestykket", 14) + 8, y0 + 75, SEC, 4))
    return "".join(o)


def play_order(week, typed, y0, note=True):
    o = [t(22, y0 + 36, f"Ordre, uke {week}", 16, "s", INK, 500)]
    o.append(rect(216, y0, 152, 56, PAPER, INK if typed else HAIR, 6, 1.6 if typed else 1))
    if typed:
        o.append(t(356, y0 + 40, typed, 34, "r", INK, 700, "end"))
    else:
        o.append(t(356, y0 + 36, "Tast antall", 15, "s", MUT, a="end"))
    label = f"Bekreft ordre på {typed}" if typed else "Bekreft ordre"
    if typed:
        o.append(button(22, y0 + 68, 346, 52, label, True, 17))
    else:
        o.append(rect(22, y0 + 68, 346, 52, TINT, HAIR, 6) + t(195, y0 + 100, label, 16, "s", MUT, 500, "middle"))
    if note:
        o.append(t(195, y0 + 142, "Ordren kan ikke endres etter bekreftelse.", 13, "s", SEC, a="middle"))
        o.append(t(195, y0 + 162, "Ida og Mikkel har bestilt. Jonas og du gjenstår.", 13, "s", SEC, a="middle"))
    return "".join(o)


def screen_play(week=11, typed=24):
    return (
        play_header(week)
        + play_v(week, y0=128, h=236)
        + play_cost(week, 430, 58)
        + play_strip(week, 526, link=True)
        + play_order(week, typed, 632, note=True)
    )


def screen_panel(week=11, typed=24):
    i = week - 1
    o = [
        rect(0, 0, 390, 844, PAPER, HAIR, 34, 1.2),
        t(22, 62, f"Alle tall, uke {week}", 26, "r", INK, 700),
        t(368, 58, "Lukk", 15, "s", INK, 500, "end"),
        line(345, 63, 368, 63, HAIR, 1),
    ]
    rows = [
        ("Lager", G["lager"][i]),
        ("Restordre", G["restordre"][i]),
        ("Innkommende ordre", G["innkommende_ordre"][i]),
        ("Levering", G["levering"][i]),
        ("Sendt", sendt(G, week)),
        ("På vei", G["paa_vei"][i]),
        ("Neste levering", G["levering"][i + 1]),
    ]
    yy = 92
    for lab, val in rows:
        o.append(t(22, yy + 18, lab, 15, "s", SEC))
        o.append(t(368, yy + 18, val, 16, "s", INK, 500, "end", True))
        o.append(line(22, yy + 28, 368, yy + 28, GRID, 1))
        yy += 30
    yy += 26
    pos = posisjon(G, week)
    o.append(t(22, yy, "Regnestykket", 20, "r", INK, 700))
    o.append(t(22, yy + 28, "Posisjon = Lager − Restordre + På vei", 14, "s", SEC))
    o.append(t(22, yy + 56, f"{G['lager'][i]} − {G['restordre'][i]} + {G['paa_vei'][i]} = {pos}", 20, "s", INK, 500, num=True))
    o.append(t(22, yy + 86, f"Med {typed} i ordre blir Posisjon {pos + typed}", 16, "s", INK, 500))
    o.append(para(22, yy + 110, "På vei er ikke garantert. Leverandøren kan mangle varer. Tallet er regnet ut fra dine egne tall.", 346, 13, 18, c=SEC))
    yy += 170
    o.append(t(22, yy, "Egen ordre og levering", 20, "r", INK, 700))
    ts = TS(32, yy + 22, 322, 100, 1, week, 0, 26)
    for v in (10, 20):
        o.append(line(22, ts.sy(v), 368, ts.sy(v), GRID, 1))
        o.append(t(22, ts.sy(v) - 3, v, 13, "s", MUT, num=True))
    o.append(line(22, ts.sy(0), 368, ts.sy(0), HAIR, 1))
    o.append(order_chart(ts, G, week, typed))
    o.append(t(ts.sx(week) - 16, ts.sy(typed) + 13, f"{typed} tastet", 13, "s", INK, 700, "end"))
    o.append(t(ts.sx(5), ts.sy(4) - 8, "Levering", 13, "s", INK, 500, "middle"))
    o.append(t(22, ts.sy(0) + 18, "Uke 1", 13, "s", MUT))
    o.append(t(368, ts.sy(0) + 18, "nå", 13, "s", SEC, a="end"))
    o.append(t(22, ts.sy(0) + 40, "Stolper: egen ordre. Linje: levering.", 13, "s", SEC))
    return "".join(o)


def build_spill():
    p = Page("05-spill", "spill", 1600, 1000, "Kurve: spillskjermen i Uke 11", "Telefon med V-diagrammet, åpnet panel med alle tall og regnestykket, og laptop. Sara har tastet 24.")
    p.add(t(40, 56, "Uke 11: Sara står på venstre arm og har tastet 24", 30, "r", INK, 700))
    p.add(t(40, 84, "Grafen viser hva uka koster. Regnestykket ligger ett trykk unna. Ingen av dem sier hva ordren bør være.", 16, "s", SEC))
    p.add(demodata(1560, 56, "end", 14))
    p.add(phone(40, 110, screen_play()))
    p.add(f'<g transform="translate(450,110)">{screen_panel()}</g>')
    p.add(t(40, 978, "Telefon: én hovedgraf", 14, "s", SEC))
    p.add(t(450, 978, "Bak ett trykk: alle tall og regnestykket", 14, "s", SEC))

    # Laptop
    lx, ly, lw, lh = 870, 110, 690, 540
    p.add(rect(lx, ly, lw, lh, PAPER, HAIR, 10, 1.2))
    p.add(rect(lx - 26, ly + lh, lw + 52, 10, "#D7DEE7", None, 3))
    wk = 11
    i = wk - 1
    p.add(t(lx + 24, ly + 46, f"Uke {wk}", 28, "r", INK, 700))
    p.add(t(lx + 112, ly + 46, "Grossist · Sara · Spill 17", 14, "s", SEC))
    p.add(t(lx + lw - 24, ly + 46, f"Totalkostnad {kr(G['kost_sum'][i])} kr", 18, "r", INK, 700, "end"))
    p.add(line(lx + 24, ly + 60, lx + lw - 24, ly + 60, GRID, 1))
    vv = V(lx + 24, ly + 96, 410, 250)
    p.add(vv.frame(fs=13), vv.arm_labels(13), vv.trail(NG, wk), vv.nowpt(NG[i]))
    cx = vv.x + vv.w / 2
    p.add(line(vv.sx(NG[i]), vv.sy(c_of(NG[i])) - 8, cx, vv.y + 46, HAIR, 1))
    p.add(t(cx, vv.y + 18, f"{G['restordre'][i]} i restordre", 16, "s", INK, 700, "middle"))
    p.add(t(cx, vv.y + 38, f"{kr(c_of(NG[i]))} kr denne uka", 14, "s", SEC, a="middle"))
    ts = TS(lx + 24, ly + 424, 410, 66, 1, wk, 0, G["kost_sum"][i] * 1.08)
    p.add(t(lx + 24, ly + 414, "Totalkostnad over tid", 13, "s", SEC))
    p.add(line(lx + 24, ts.sy(0), lx + 434, ts.sy(0), HAIR, 1), cost_line(ts, G, wk), circ(ts.sx(wk), ts.sy(G["kost_sum"][i]), 3.5, INK))
    p.add(t(lx + 24, ts.sy(0) + 17, "Uke 1", 13, "s", MUT), t(lx + 434, ts.sy(0) + 17, "nå", 13, "s", SEC, a="end"))
    rx, rw = lx + 462, 204
    rows = [("Lager", G["lager"][i]), ("Restordre", G["restordre"][i]), ("Innkommende ordre", G["innkommende_ordre"][i]), ("Levering", G["levering"][i]), ("Sendt", sendt(G, wk)), ("På vei", G["paa_vei"][i]), ("Neste levering", G["levering"][i + 1])]
    yy = ly + 84
    for lab, val in rows:
        p.add(t(rx, yy, lab, 14, "s", SEC), t(rx + rw, yy, val, 14, "s", INK, 500, "end", True), line(rx, yy + 8, rx + rw, yy + 8, GRID, 1))
        yy += 26
    yy += 16
    pos = posisjon(G, wk)
    p.add(t(rx, yy, "Regnestykket", 16, "r", INK, 700))
    p.add(t(rx, yy + 22, f"{G['lager'][i]} − {G['restordre'][i]} + {G['paa_vei'][i]} = Posisjon {pos}", 14, "s", INK, 500, num=True))
    p.add(t(rx, yy + 42, f"Med 24: Posisjon {pos + 24}", 14, "s", SEC))
    p.add(para(rx, yy + 62, "På vei er ikke garantert.", rw, 13, 16, c=SEC))
    yy += 88
    p.add(t(rx, yy + 26, "Ordre", 15, "s", INK, 500), rect(rx + rw - 90, yy, 90, 40, PAPER, INK, 5, 1.5), t(rx + rw - 10, yy + 29, 24, 26, "r", INK, 700, "end"))
    p.add(button(rx, yy + 50, rw, 42, "Bekreft ordre på 24", True, 15))
    p.add(t(rx, yy + 112, "Kan ikke endres etter bekreftelse.", 13, "s", SEC))
    p.add(t(lx, ly + lh + 36, "Laptop: samme graf, og tallene får plass uten trykk", 14, "s", SEC))
    p.add(para(lx, ly + lh + 74, "Punktet er uka di. Sporet er ukene før. Høyden på V-en er det uka koster, og samme tall blir stigningen på kurven under.", 660, 18, 26, "r", INK))
    p.add(para(lx, ly + lh + 150, f"Uke 11: {kr(c_of(NG[10]))} kr høyt på V-en, og Totalkostnad går fra {kr(G['kost_sum'][9])} til {kr(G['kost_sum'][10])} kr. Alle uker kan regnes på samme måte.", 660, 15, 21, c=SEC))
    p.save()


# ---------- spilldynamikk ----------
def seat_row(x, y, role, name, state, kind, w=346):
    """Sete i venteliste. Status er tekst og form, aldri bare farge."""
    o = []
    if kind == "ok":
        o.append(circ(x + 6, y - 5, 5, INK))
    elif kind == "wait":
        o.append(circ(x + 6, y - 5, 5, PAPER, INK, 1.6))
    else:
        o.append(rect(x + 1, y - 10, 10, 10, PAPER, INK, 2, 1.6))
    o.append(t(x + 20, y, f"{name} ({role})", 15, "s", INK, 500))
    o.append(t(x + w, y, state, 14, "s", SEC, a="end"))
    return "".join(o)


def screen_a():
    return screen_v_state(11, None, "Uka åpner. Punktet har flyttet seg fra −9 til −13, og denne uka koster 13,00 kr.")


def screen_v_state(week, typed, note):
    return (
        play_header(week)
        + play_v(week, y0=128, h=236)
        + play_cost(week, 430, 58)
        + play_strip(week, 526, link=True)
        + play_order(week, typed, 632, note=False)
        + para(22, 780, note, 346, 13, 18, c=SEC)
    )


def screen_b():
    wk = 11
    o = [play_header(wk), play_v(wk, y0=128, h=170, callout=True)]
    i = wk - 1
    y0 = 350
    o.append(t(22, y0 + 18, "Innkommende ordre", 13, "s", SEC) + t(22, y0 + 44, G["innkommende_ordre"][i], 22, "r", INK, 700))
    o.append(t(170, y0 + 18, "Levering", 13, "s", SEC) + t(170, y0 + 44, G["levering"][i], 22, "r", INK, 700))
    o.append(t(288, y0 + 18, "På vei", 13, "s", INK, 700) + t(288, y0 + 44, G["paa_vei"][i], 22, "r", INK, 700))
    o.append(line(288, y0 + 52, 330, y0 + 52, INK, 1.6))
    o.append(t(22, y0 + 88, f"Ordre, uke {wk}", 16, "s", INK, 500))
    o.append(rect(216, y0 + 60, 152, 48, PAPER, INK, 6, 1.6) + t(356, y0 + 96, "24", 32, "r", INK, 700, "end"))
    # Tallrad
    yy = y0 + 122
    keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]
    kw, kh = 66, 46
    for n, k in enumerate(keys):
        col, row = n % 5, n // 5
        xx = 22 + col * (kw + 4)
        ky = yy + row * (kh + 4)
        o.append(rect(xx, ky, kw, kh, TINT, HAIR, 5) + t(xx + kw / 2, ky + 30, k, 19, "s", INK, 500, "middle"))
    o.append(t(368, yy + 2 * (kh + 4) + 20, "Slett", 15, "s", INK, 500, "end"))
    o.append(button(22, yy + 2 * (kh + 4) + 34, 346, 50, "Bekreft ordre på 24", True, 17))
    o.append(t(195, yy + 2 * (kh + 4) + 106, "Ordren kan ikke endres etter bekreftelse.", 13, "s", SEC, a="middle"))
    return "".join(o)


def screen_c():
    wk = 11
    o = [play_header(wk), play_v(wk, y0=128, h=170)]
    y0 = 360
    o.append(line(22, y0, 368, y0, GRID, 1))
    o.append(t(22, y0 + 34, "Ordre 24 er bekreftet", 22, "r", INK, 700))
    o.append(t(22, y0 + 60, "Uka går videre når alle har bestilt.", 15, "s", SEC))
    yy = y0 + 104
    for role, st, kind in [("Detaljist", "har bestilt", "ok"), ("Distributør", "har bestilt", "ok"), ("Grossist", "du har bestilt", "ok"), ("Fabrikk", "venter, 3 min", "wait")]:
        o.append(seat_row(22, yy, role, NAVN[role], st, kind))
        o.append(line(22, yy + 12, 368, yy + 12, GRID, 1))
        yy += 40
    o.append(para(22, yy + 16, "Du får varsel når Uke 12 åpner. Du kan lukke appen.", 346, 14, 19, c=SEC))
    return "".join(o)


def screen_d():
    wk = 12
    i = wk - 1
    v = V(22, 128, 346, 236)
    o = [play_header(wk), v.frame(fs=13), v.arm_labels(13), v.trail(NG, wk - 1, n=6)]
    a, b = NG[i - 1], NG[i]
    o.append(poly([(v.sx(a), v.sy(c_of(a))), (v.sx(b), v.sy(c_of(b)))], INK, 4))
    o.append(circ(v.sx(a), v.sy(c_of(a)), 4.5, PAPER, INK, 1.6))
    o.append(v.nowpt(b))
    cx = 195
    o.append(line(v.sx(b), v.sy(c_of(b)) - 8, cx, 180, HAIR, 1))
    o.append(t(cx, 146, f"{sgn(a)} til {sgn(b)}", 16, "s", INK, 700, "middle"))
    o.append(t(cx, 168, f"{kr(c_of(b))} kr denne uka", 15, "s", SEC, a="middle"))
    o.append(play_cost(wk, 430, 58))
    o.append(line(22, 526, 368, 526, GRID, 1))
    o.append(t(22, 562, f"Levering {G['levering'][i]}, innkommende ordre {G['innkommende_ordre'][i]}", 16, "s", INK, 500))
    o.append(t(22, 590, f"{sgn(a)} + {G['levering'][i]} − {G['innkommende_ordre'][i]} = {sgn(b)}", 20, "s", INK, 500, num=True))
    o.append(t(22, 622, f"Totalkostnad {kr(G['kost_sum'][i - 1])} + {kr(c_of(b))} = {kr(G['kost_sum'][i])} kr", 15, "s", SEC))
    o.append(button(22, 690, 346, 50, "Hopp over", False, 16))
    o.append(t(195, 770, "Går videre av seg selv innen 2 sekunder.", 13, "s", SEC, a="middle"))
    return "".join(o)


def screen_e():
    wk = 11
    F = S17["Fabrikk"]
    o = [play_header(wk, F, "Fabrikk · Jonas"), play_v(wk, y0=128, h=170, s=F)]
    y0 = 360
    o.append(line(22, y0, 368, y0, GRID, 1))
    o.append(rect(22, y0 + 18, 86, 26, INK, None, 4) + t(65, y0 + 36, "KI-spiller", 14, "s", PAPER, 700, "middle"))
    o.append(t(118, y0 + 36, "bestiller for deg nå", 15, "s", INK, 500))
    o.append(para(22, y0 + 72, "Spillet sto på Pause mens det ventet på deg. Etter 24 timer overtok en KI-spiller setet, så gruppa kan fortsette.", 346, 15, 21, c=SEC))
    yy = y0 + 150
    o.append(t(22, yy, "Slik ser de andre det", 14, "s", SEC))
    o.append(t(368, yy, "Fabrikk: KI-spiller", 14, "s", INK, 700, "end"))
    o.append(line(22, yy + 10, 368, yy + 10, GRID, 1))
    o.append(t(22, yy + 36, "Ordre lagt av KI-spiller", 14, "s", SEC))
    o.append(t(368, yy + 36, "merket i loggen", 14, "s", INK, 500, "end"))
    o.append(line(22, yy + 46, 368, yy + 46, GRID, 1))
    o.append(button(22, 690, 346, 52, "Ta tilbake setet", True, 17))
    o.append(t(195, 772, "Du bestiller selv fra neste Uke.", 13, "s", SEC, a="middle"))
    return "".join(o)


def screen_f():
    o = [t(22, 62, "Spillet er slutt", 32, "r", INK, 700)]
    o.append(t(22, 98, "Kjeden betalte til sammen", 16, "s", SEC))
    o.append(t(22, 150, f"{kr(FX['spill17']['kjedekost'])} kr", 50, "r", INK, 700))
    o.append(para(22, 186, "Målet var lavest kostnad for hele kjeden, ikke for ett sete.", 346, 15, 21, c=SEC))
    o.append(line(22, 232, 368, 232, GRID, 1))
    ymax = max(FX["spill17"]["kost_per_rolle"].values())
    yy = 264
    for r in ROLLER:
        a, b = cum_parts(S17[r])
        tot = FX["spill17"]["kost_per_rolle"][r]
        mine = r == "Grossist"
        o.append(t(22, yy, r + (" (du)" if mine else ""), 16, "s", INK, 700 if mine else 400))
        o.append(t(368, yy, f"{kr(tot)} kr", 16, "s", INK, 700 if mine else 400, "end", True))
        sc = 346 / ymax
        la = a[-1] * sc
        lb = b[-1] * sc
        o.append(rect(22, yy + 9, la - 1, 12, BLA_F) + rect(22 + la + 1, yy + 9, lb - 1, 12, OKER_F))
        yy += 66
    o.append(t(22, yy - 6, "Lys blå: lagerkostnad. Oker: restordrekostnad.", 13, "s", SEC))
    o.append(button(22, 690, 346, 52, "Videre til Debrief", True, 17))
    o.append(t(195, 772, "Du møter gruppa og skriver din Forklaring først.", 13, "s", SEC, a="middle"))
    return "".join(o)


def build_dyn():
    p = Page("06-spilldynamikk", "dyn", 2100, 1200, "Kurve: en Uke i seks ruter", "Seks telefoner fra Uka åpner til spillet slutter, med korte notater og hva spilleren lærer.")
    p.add(t(40, 56, "En Uke, og hele spillet: punktet flytter seg, kurven stiger", 30, "r", INK, 700))
    p.add(demodata(2060, 56, "end", 14))
    sc = 0.82
    pw = 390 * sc
    gap = (2100 - 80 - 6 * pw) / 5
    screens = [
        (screen_v_state(11, None, "Ida har bestilt. Mikkel, Jonas og du gjenstår."), "A Uka åpner", f"Punktet har flyttet seg fra {sgn(NG[9])} til {sgn(NG[10])}. Uka koster {kr(c_of(NG[10]))} kr, som er {kr(c_of(NG[10]) - c_of(NG[9]))} kr mer enn sist. Ingen ros og ingen straff, bare et nytt punkt."),
        (screen_b(), "B Beslutningen", "24 med 16 på vei. På vei er streket under, men ingen regel sier hva det betyr. Talltastene ligger i appen, slik at grafen blir synlig mens hen taster."),
        (screen_c(), "C Bekreftet", "Ordren er låst. Spillet viser hvem det venter på, Jonas i 3 minutter, og at hen kan lukke appen. Status er tekst og form."),
        (screen_d(), "D Uka går videre", "Kan hoppes over og varer aldri over 2 sekunder. Punktet glir langs armen. Regnestykket under viser hvorfor det havnet der."),
        (screen_e(), "E Jonas er borte", "Jonas sin skjerm. Pause først, så KI-spiller, alltid merket. Sara ser «Fabrikk: KI-spiller». Ett fravær stopper ikke gruppa."),
        (screen_f(), "F Spillet slutter", "Kjedens totalkostnad først, så per Rolle. Ingen rangering. Etterspørselen er fortsatt skjult, og neste steg er Debrief."),
    ]
    for n, (content, head, note) in enumerate(screens):
        x = 40 + n * (pw + gap)
        p.add(phone(x, 84, content, sc))
        p.add(t(x, 84 + 844 * sc + 34, head, 20, "r", INK, 700))
        p.add(para(x, 84 + 844 * sc + 60, note, pw - 6, 15, 21, c=SEC))
    p.add(line(40, 960, 2060, 960, HAIR, 1))
    p.add(t(40, 1004, "Hva spilleren lærer av å se grafen uke for uke", 24, "r", INK, 700))
    lærer = (
        f"Først ligger punktet rolig på høyre arm, og uka koster {kr(c_of(NG[0]))} kr. Så glir det forbi bunnen og opp venstre arm, der hver enhet koster dobbelt så mye. "
        f"I Uke 18 koster en uke {kr(c_of(NG[17]))} kr, og i Uke 29 står hen på motsatt arm og betaler {kr(c_of(NG[28]))} kr for varer som kom samlet. "
        "Hen ser at begge armene koster, og at store utslag til begge sider koster mest. "
        "Grafen viser hvor hen er, og den regner ut hva det koster. Den forteller ikke hvor hen bør være."
    )
    p.add(para(40, 1042, lærer, 1700, 20, 30, "r", INK))
    p.save()


# ---------- pedagogikk ----------
def tag(x, y, s):
    wd = tw(s, 14, True) + 14
    return rect(x, y - 15, wd, 21, INK, None, 3) + t(x + 7, y, s, 14, "s", PAPER, 700), wd


def tags(x, y, items):
    o = []
    for s in items:
        a, wd = tag(x, y, s)
        o.append(a)
        x += wd + 6
    return "".join(o)


def build_ped():
    p = Page("10-pedagogikk", "ped", 2000, 1400, "Kurve: grafgrammatikken", "Samme grafer for Sara i Uke 5, 11, 18 og 29, merket med prinsipp og innsikt, og sammenligning med simulert referanse etter Debriefen.")
    p.add(t(50, 62, "Ett punkt på en kurve forteller hva uka kostet", 38, "r", INK, 700))
    p.add(t(50, 92, "Saras egne tall. V-en har samme skala hele tiden, og tidsgrafene har samme skala i alle fire ruter. Høyre kant på tidsgrafene er nå.", 16, "s", SEC))
    p.add(demodata(1950, 62, "end", 14))
    weeks = [5, 11, 18, 29]
    x0, cw, gap = 310, 395, 20
    txt = {
        5: ("Hver uke på lager koster også.", f"Lager {G['lager'][4]} koster {kr(c_of(NG[4]))} kr per uke. Ingenting ser galt ut ennå. Hva gjør du med en rolig uke?"),
        11: ("Her koster hver enhet dobbelt.", f"{sgn(NG[10])} koster {kr(c_of(NG[10]))} kr. {sgn(-NG[10])} hadde kostet {kr(c_of(-NG[10]))} kr. Punktet teller ikke de {G['paa_vei'][10]} på vei, så sjekk regnestykket før du taster."),
        18: ("Hele veien opp armen.", f"{sgn(NG[17])} koster {kr(c_of(NG[17]))} kr per uke, med {G['paa_vei'][17]} på vei. Det du betaler for nå kommer av ukene før. Hva er allerede bestilt?"),
        29: ("Over på den andre armen.", f"{sgn(NG[28])} koster {kr(c_of(NG[28]))} kr per uke. Bunnen ble passert på noen få uker, fra {sgn(NG[23])} i Uke 24 til {sgn(NG[25])} i Uke 26. Hva gjør en ordre nå om fire uker?"),
    }
    # Radetiketter
    yV, hV = 158, 190
    yC = 476
    yCap = yV + hV + 44
    labels = [
        (yV - 6, ["P8", "P7"], "V-en", f"Kostnad som funksjon av netto lager. Dobbelt så bratt til venstre. Punktet er denne uka, sporet er ukene før. Alltid synlig."),
        (yC + 20, ["P8"], "Totalkostnad", f"Høyden på V-en blir stigningen her. Uke 11: {kr(G['kost_sum'][9])} + {kr(c_of(NG[10]))} = {kr(G['kost_sum'][10])} kr. Alltid synlig."),
        (yC + 136, ["P1", "P4"], "Inn og ut", f"Areal mellom linjene er endringen i netto lager. Uke 11: {sgn(NG[9])} + {G['levering'][10]} − {G['innkommende_ordre'][10]} = {sgn(NG[10])}. Bak ett trykk."),
        (yC + 252, ["P2", "P3"], "Ordre og levering", f"En ordre kommer fram etter om lag 4 uker. 24 bestilt i Uke 11, {G['levering'][14]} levert i Uke 15. Bak ett trykk, med Posisjon."),
    ]
    for yy, tg, title, body in labels:
        p.add(tags(50, yy, tg))
        p.add(t(50, yy + 30, title, 21, "r", INK, 700))
        p.add(para(50, yy + 52, body, 232, 14, 19, c=SEC))
    ppw = cw / 29.5
    for n, wk in enumerate(weeks):
        x = x0 + n * (cw + gap)
        i = wk - 1
        p.add(t(x, 136, f"Uke {wk}", 22, "r", INK, 700))
        p.add(t(x + cw, 136, f"{sgn(NG[i])} · {kr(c_of(NG[i]))} kr denne uka", 15, "s", INK, 500, "end", True))
        v = V(x, yV, cw, hV)
        p.add(v.frame(fs=13, ytitle="", axis="Netto lager, enheter", ygrid=(10, 20, 30)), v.trail(NG, wk, n=8), v.nowpt(NG[i], 6.5))
        title, body = txt[wk]
        yc = yV + hV + 62
        # Innsikt
        p.add(t(x, yc, title, 15, "s", INK, 700))
        p.add(para(x, yc + 19, body, cw - 4, 14, 18, c=SEC))
        # Tidsrader
        rx = x + cw - 6
        px = rx - (wk - 1) * ppw
        ts = TS(px, yC + 28, (wk - 1) * ppw, 66, 1, wk, 0, 560)
        p.add(line(x, ts.sy(0), x + cw, ts.sy(0), HAIR, 1))
        p.add(cost_line(ts, G, wk), circ(ts.sx(wk), ts.sy(G["kost_sum"][i]), 3.2, INK))
        p.add(t(rx, ts.sy(G["kost_sum"][i]) - 7 if G["kost_sum"][i] > 80 else ts.sy(G["kost_sum"][i]) - 7, f"{kr(G['kost_sum'][i])} kr", 13, "s", INK, 700, "end", True))
        p.add(t(px, ts.sy(0) + 15, "Uke 1", 12, "s", MUT, a="middle" if wk > 5 else "end"))
        p.add(t(rx, ts.sy(0) + 15, "nå", 12, "s", SEC, a="end"))
        ts2 = TS(px, yC + 142, (wk - 1) * ppw, 66, 1, wk, 0, 32)
        p.add(line(x, ts2.sy(0), x + cw, ts2.sy(0), HAIR, 1))
        p.add(inout_chart(ts2, G, wk))
        p.add(t(rx, ts2.y - 7, f"inn {G['levering'][i]}, ut {G['innkommende_ordre'][i]}", 13, "s", SEC, a="end", num=True))
        ts3 = TS(px, yC + 258, (wk - 1) * ppw, 66, 1, wk, 0, 32)
        p.add(line(x, ts3.sy(0), x + cw, ts3.sy(0), HAIR, 1))
        p.add(order_chart(ts3, G, wk))
        p.add(t(rx, ts3.y - 16, f"På vei {G['paa_vei'][i]} · Posisjon {posisjon(G, i + 1)}", 13, "s", INK, 500, "end", True))
        if wk >= 18:
            xa, xb = ts3.sx(11), ts3.sx(15)
            ya = ts3.sy(G["ordre"][10]) - 5
            p.add(poly([(xa, ya), (xa, ya - 6), (xb, ya - 6), (xb, ts3.sy(G["levering"][14]) - 3)], INK, 1))
            p.add(t((xa + xb) / 2, ya - 11, "4 uker", 12, "s", INK, 500, "middle"))
    # Tidsradenes felles forklaring
    p.add(t(50, 852, "Tidsgrafene: Blå linje eller flate hører til lager og oker til restordre, som på V-en. Stolper er egen ordre. Linjen i nederste rad er levering.", 14, "s", SEC))

    # Etter Debriefen
    yB = 866
    p.add(line(50, yB, 1950, yB, HAIR, 1))
    p.add(t(50, yB + 40, "Etter Debriefen: det samme diagrammet får flere lag", 26, "r", INK, 700))
    # A: Hvorfor svingning koster
    ax, ay = 50, yB + 66
    mean_net = sum(NG) / 36
    tot = G["kost_sum"][-1]
    p.add(tags(ax, ay + 12, ["P7", "P8"]))
    p.add(t(ax + 80, ay + 12, "Hvorfor svingning koster", 20, "r", INK, 700))
    v = V(ax, ay + 58, 520, 250)
    p.add(v.frame(fs=13, ytitle="", axis=""), v.arm_labels(13))
    p.add(v.allpts(NG, 3.4, INK, 0.5))
    # Rug
    for val in NG:
        p.add(line(v.sx(val), v.sy(0) + 28, v.sx(val), v.sy(0) + 38, INK, 1, None))
    p.add(t(v.x + v.w / 2, v.sy(0) + 54, "Alle 36 uker langs netto lager", 13, "s", SEC, a="middle"))
    avg = tot / 36
    p.add(line(v.sx(-avg), v.sy(avg), v.sx(2 * avg), v.sy(avg), INK, 1.4))
    p.add(t(v.sx(mean_net) + 8, v.sy(avg) - 7, f"Snitt per uke: {kr(avg)} kr", 14, "s", INK, 700, "start", True))
    mx = v.sx(mean_net)
    p.add(line(mx, v.sy(avg), mx, v.sy(c_of(mean_net)), INK, 1.4))
    p.add(circ(mx, v.sy(c_of(mean_net)), 5, PAPER, INK, 2))
    p.add(t(mx + 8, v.sy(11), "Kostnad på snittet:", 13, "s", SEC), t(mx + 8, v.sy(11) + 17, f"{kr(c_of(mean_net))} kr", 13, "s", INK, 700, num=True))
    p.add(para(ax, ay + 58 + 250 + 76, f"Snittet ditt var {kr(mean_net, 1)} enheter. Å ligge jevnt der hadde kostet {kr(c_of(mean_net) * 36)} kr. Du betalte {kr(tot)} kr. Forskjellen, {kr(tot - c_of(mean_net) * 36)} kr, kommer av at uker på hver side av null ikke veier hverandre opp. Et regnestykke, ikke et mål: med forsinkelser kan ingen ligge stille.", 540, 14, 19, c=INK))

    # B: Simulert
    bx, by, bw = 640, yB + 66, 610
    p.add(tags(bx, by + 12, ["P3", "P6"]))
    p.add(t(bx + 80, by + 12, "Samme kjede, regnet med alt på vei", 20, "r", INK, 700))
    ts = TS(bx + 34, by + 40, bw - 150, 210, 1, 36, 0, 600)
    for val in (200, 400, 600):
        p.add(line(bx, ts.sy(val), bx + bw - 116, ts.sy(val), GRID, 1), t(bx, ts.sy(val) - 3, f"{val} kr", 13, "s", MUT, num=True))
    p.add(cum_stack(ts, G))
    p.add(line(ts.x, ts.sy(0), ts.x + ts.w, ts.sy(0), HAIR, 1))
    p.add(sim_line(ts, SIM_SARA["serier"]["Grossist"]), sim_line(ts, SIM_ALLE["serier"]["Grossist"], c=SEC, sw=1.4, dash="2 4"))
    ex = ts.x + ts.w + 8
    p.add(t(ex, ts.sy(G["kost_sum"][-1]) + 4, f"{kr(G['kost_sum'][-1])} kr", 14, "s", INK, 700, num=True))
    p.add(t(ex, ts.sy(G["kost_sum"][-1]) + 21, "Spilt", 13, "s", SEC))
    yy = ts.sy(SIM_SARA["serier"]["Grossist"]["kost_sum"][-1])
    p.add(t(ex, yy + 4, f"{kr(SIM_SARA['kost_per_rolle']['Grossist'])} kr", 14, "s", INK, 500, num=True), t(ex, yy + 21, "Simulert: bare du", 13, "s", SEC))
    yy = ts.sy(SIM_ALLE["serier"]["Grossist"]["kost_sum"][-1])
    p.add(t(ex, yy + 4, f"{kr(SIM_ALLE['kost_per_rolle']['Grossist'])} kr", 14, "s", INK, 500, num=True), t(ex, yy + 21, "Simulert: alle fire", 13, "s", SEC))
    p.add(t(ts.sx(1), ts.sy(0) + 16, "Uke 1", 13, "s", MUT), t(ts.sx(36), ts.sy(0) + 16, "Uke 36", 13, "s", MUT, a="end"))
    p.add(t(ts.sx(32), ts.sy(50), "Lager", 13, "s", INK, 500, "middle"), t(ts.sx(30), ts.sy(200), "Restordre", 13, "s", INK, 500, "middle"))
    # Fire V-er
    fy = by + 300
    p.add(tags(bx, fy + 12, ["P5", "P6"]))
    p.add(t(bx + 80, fy + 12, "Alle fire punktene har reist langt", 20, "r", INK, 700))
    fw = (bw - 30) / 4
    for n, r in enumerate(ROLLER):
        fx = bx + n * (fw + 10)
        fv = V(fx, fy + 54, fw, 68, 70, 70)
        p.add(t(fx, fy + 38, f"{r}: {FX['spill17']['forsterkning'][r]:.1f}×".replace(".", ","), 13, "s", INK, 500))
        p.add(fv.frame(fs=11, ticks=(), ygrid=(), arm=1.6, axis="", ytitle="", ylab=False), fv.allpts(nets(S17[r]), 2, INK, 0.5))
        p.add(t(fx + fw / 2, fy + 54 + 68 + 16, f"{sgn(min(nets(S17[r])))} til {sgn(max(nets(S17[r])))}", 12, "s", SEC, a="middle", num=True))

    # C: Hjelpegrad
    cx, cy = 1290, yB + 66
    p.add(tags(cx, cy + 12, ["P3"]))
    p.add(t(cx + 44, cy + 12, "Hjelpegrad: to skjermer, samme graf", 20, "r", INK, 700))
    cw2 = 315
    # Klassespill
    p.add(t(cx, cy + 46, "Klassespill, Uke 11", 15, "s", INK, 700))
    v1 = V(cx, cy + 62, cw2, 170)
    p.add(v1.frame(fs=13, ytitle="", axis="", ygrid=(10, 20, 30)), v1.trail(NG, 11), v1.nowpt(NG[10], 6.5))
    p.add(para(cx, cy + 62 + 170 + 44, "Punkt og spor. Du opplever konsekvensen. Regnestykket ligger bak ett trykk.", cw2 - 6, 14, 19, c=SEC))
    # Replay
    R = REPLAY["serier"]["Grossist"]
    rw = 14
    nr = nets(R)
    rpos = posisjon(R, rw)
    rord = R["ordre"][rw - 1]
    x2 = cx + cw2 + 30
    p.add(t(x2, cy + 46, f"Replay, Uke {rw}", 15, "s", INK, 700))
    v2 = V(x2, cy + 62, cw2, 170)
    p.add(v2.frame(fs=13, ytitle="", axis="", ygrid=(10, 20, 30)), v2.trail(nr, rw), v2.nowpt(nr[rw - 1], 6.5))
    p.add(v2.ring_on_axis(rpos, f"Posisjon {rpos}", INK, 13, 88))
    p.add(v2.ring_on_axis(rpos + rord, f"med {rord}: {rpos + rord}", INK, 13, 122, "end" if rpos + rord > 26 else "middle"))
    p.add(para(x2, cy + 62 + 170 + 44, "Låst opp etter Debriefen. Posisjon ligger på samme akse som punktet, og flytter seg når du taster. Fortsatt ingen fasit.", cw2 - 6, 14, 19, c=SEC))
    p.add(line(cx, cy + 340, 1950, cy + 340, GRID, 1))
    p.add(para(cx, cy + 366, f"Hvorfor: Punktet alene viser kostnaden og frister til å bestille for mye, slik svingningen oppstår. Etter Debriefen vet studenten hvorfor, og da hjelper Posisjon på aksen. Replay er tilfeldig etterspørsel, tre KI-spillere, ikke like for like med Klassespillet.", 660, 15, 21, c=INK))
    p.add(t(cx, 1384, "Simulert viser sammenhengen, ikke en fasit. Regelen er valgt for å illustrere.", 13, "s", SEC))
    p.save()


# ---------- debrief ----------
def sheet(x, y, w, h, fill=PAPER):
    return rect(x, y, w, h, fill, HAIR, 8, 1)


def step_head(x, y, n, title, wd=None):
    return t(x, y, f"{n}" if n else "", 20, "r", MUT, 700) + t(x + (22 if n else 0), y, title, 20, "r", INK, 700)


def build_debrief():
    p = Page("07-debrief", "debrief", 2100, 1200, "Kurve: Gruppedebrief i fem steg og delt skjerm", "Forklaring, avsløring av etterspørsel, alle fire Rollers ordre, ditt øyeblikk i Uke 11 med simulert referanse, og quiz.")
    p.add(t(40, 52, "Debrief: kostnaden var hele tiden et svar på hvordan kjeden er bygd", 30, "r", INK, 700))
    p.add(demodata(2060, 52, "end", 14, ". Alle tall fra loggen."))
    r1y, r1h = 74, 500
    # Steg 1
    x, w = 40, 300
    p.add(sheet(x, r1y, w, r1h), step_head(x + 18, r1y + 34, 1, "Skriv din Forklaring"))
    p.add(para(x + 18, r1y + 66, "Hvorfor tror du kostnaden din ble som den ble?", w - 36, 16, 22, "r", INK))
    ts = TS(x + 18, r1y + 124, w - 36, 70, 1, 36, 0, 600)
    p.add(line(ts.x, ts.sy(0), ts.x + ts.w, ts.sy(0), HAIR, 1), cost_line(ts, G, 36, 2))
    p.add(t(x + w - 18, ts.y - 2, f"Du: {kr(G['kost_sum'][-1])} kr", 14, "s", INK, 700, "end", True))
    p.add(rect(x + 18, r1y + 214, w - 36, 130, TINT, HAIR, 4))
    p.add(para(x + 30, r1y + 240, "Ordrene jeg fikk gikk opp, og jeg hadde ingenting å sende. Jeg bestilte mye i uke 11 fordi restordren vokste. Etterpå kom alt på en gang.", w - 60, 14, 19))
    p.add(button(x + 18, r1y + 356, w - 36, 42, "Lagre Forklaring", True, 15))
    p.add(line(x + 18, r1y + 414, x + w - 18, r1y + 414, GRID, 1))
    p.add(t(x + 18, r1y + 438, "Avsløringen er låst til alle har skrevet.", 14, "s", INK, 700))
    p.add(t(x + 18, r1y + 460, "Ida og Mikkel er ferdige. Jonas skriver.", 14, "s", SEC))
    # Steg 2
    x, w = 360, 430
    p.add(sheet(x, r1y, w, r1h), step_head(x + 18, r1y + 34, 2, "Etterspørselen avsløres"))
    d = S17["demand"]
    p.add(para(x + 18, r1y + 72, f"Kundene kjøpte {d[0]} per uke. I Uke 5 ble det {d[4]}. Deretter endret ingenting seg.", w - 36, 22, 28, "r", INK, 500))
    ts = TS(x + 40, r1y + 170, w - 76, 240, 1, 36, 0, 32)
    for val in (10, 20, 30):
        p.add(line(x + 18, ts.sy(val), x + w - 18, ts.sy(val), GRID, 1), t(x + 18, ts.sy(val) - 3, val, 13, "s", MUT, num=True))
    p.add(line(x + 18, ts.sy(0), x + w - 18, ts.sy(0), HAIR, 1))
    pts = []
    for i, v in enumerate(d):
        if i and d[i - 1] != v:
            pts.append((ts.sx(i + 1), ts.sy(d[i - 1])))
        pts.append((ts.sx(i + 1), ts.sy(v)))
    p.add(poly(pts, INK, 3.2))
    p.add(t(ts.sx(36), ts.sy(8) - 10, "Kundeetterspørsel", 14, "s", INK, 700, "end"))
    p.add(t(ts.sx(5) + 6, ts.sy(4) + 18, f"Uke 5: {d[3]} til {d[4]}", 14, "s", INK, 500))
    p.add(t(ts.sx(1), ts.sy(0) + 18, "Uke 1", 13, "s", MUT), t(ts.sx(36), ts.sy(0) + 18, "Uke 36", 13, "s", MUT, a="end"))
    p.add(para(x + 18, r1y + 450, "Øvelsen heter ølspillet (the Beer Game). Sammenlign med det du skrev.", w - 36, 14, 19, c=SEC))
    # Steg 3
    x, w = 810, 500
    p.add(sheet(x, r1y, w, r1h), step_head(x + 18, r1y + 34, 3, "Alle fire Rollers ordre"))
    p.add(para(x + 18, r1y + 66, "Samme skala som i forrige steg. Hvert ledd så bare ordrene fra nærmeste ledd, og svingningen vokser oppover i kjeden.", w - 36, 15, 20, c=SEC))
    ts = TS(x + 40, r1y + 170, w - 76, 240, 1, 36, 0, 32)
    for val in (10, 20, 30):
        p.add(line(x + 18, ts.sy(val), x + w - 18, ts.sy(val), GRID, 1), t(x + 18, ts.sy(val) - 3, val, 13, "s", MUT, num=True))
    p.add(line(x + 18, ts.sy(0), x + w - 18, ts.sy(0), HAIR, 1))
    for r in ["Detaljist", "Distributør", "Fabrikk", "Grossist"]:
        s = S17[r]["ordre"]
        p.add(poly([(ts.sx(i + 1), ts.sy(v)) for i, v in enumerate(s)], ROLLE_TONE[r], 2.6 if r == "Grossist" else 1.6))
    p.add(poly(pts, INK, 3.2))
    peak = {r: max(range(36), key=lambda i: S17[r]["ordre"][i]) for r in ROLLER}
    p.add(t(ts.sx(peak["Fabrikk"] + 1) + 8, ts.sy(S17["Fabrikk"]["ordre"][peak["Fabrikk"]]) + 4, "Fabrikk", 14, "s", INK, 500))
    p.add(t(ts.sx(13), ts.sy(28), "Distributør", 14, "s", INK, 500, "end"), line(ts.sx(13) + 2, ts.sy(27.5), ts.sx(15), ts.sy(22.5), HAIR, 1))
    p.add(t(ts.sx(peak["Grossist"] + 1) - 8, ts.sy(S17["Grossist"]["ordre"][peak["Grossist"]]) + 4, "Grossist (du)", 14, "s", INK, 700, "end"))
    p.add(t(ts.sx(9.5), ts.sy(12.5), "Detaljist", 14, "s", INK, 500, "end"))
    p.add(t(ts.sx(15.5), ts.sy(2.2), "Kundeetterspørsel", 14, "s", INK, 700))
    p.add(t(ts.sx(1), ts.sy(0) + 18, "Uke 1", 13, "s", MUT), t(ts.sx(36), ts.sy(0) + 18, "Uke 36", 13, "s", MUT, a="end"))
    yy = r1y + 450
    p.add(t(x + 18, yy + 24, "Forsterkning", 14, "s", SEC))
    for n, r in enumerate(ROLLER):
        xx = x + 112 + n * 92
        p.add(t(xx, yy, r, 13, "s", SEC), t(xx, yy + 26, f"{FX['spill17']['forsterkning'][r]:.1f}×".replace(".", ","), 22, "r", INK, 700))
    # Delt skjerm
    x, w = 1330, 730
    p.add(sheet(x, r1y, w, r1h, "#F8FAFC"))
    p.add(t(x + 18, r1y + 34, "Delt skjerm: Alle fire punktene har reist langt", 20, "r", INK, 700))
    p.add(para(x + 18, r1y + 60, f"Målet var lavest kostnad for kjeden. Kjeden betalte {kr(FX['spill17']['kjedekost'])} kr. Ingen av dere kunne se de andre punktene mens de flyttet seg.", w - 36, 15, 20, c=SEC))
    cw = (w - 36 - 3 * 14) / 4
    for n, r in enumerate(ROLLER):
        cx = x + 18 + n * (cw + 14)
        s = S17[r]
        ns = nets(s)
        kost = FX["spill17"]["kost_per_rolle"][r]
        p.add(t(cx, r1y + 122, r, 15, "s", INK, 700))
        p.add(t(cx, r1y + 142, f"{NAVN[r]} · {kr(kost)} kr", 14, "s", SEC, num=True))
        v = V(cx, r1y + 160, cw, 120, 70, 70)
        p.add(v.frame(fs=12, ticks=(-70, 0, 70), ygrid=(35,), arm=1.8, axis="", ytitle="", ylab=False), v.allpts(ns, 2.6, INK, 0.55))
        p.add(t(cx + cw / 2, r1y + 160 + 120 + 36, f"{sgn(min(ns))} til {sgn(max(ns))}", 14, "s", INK, 500, "middle", True))
        ts2 = TS(cx, r1y + 342, cw, 104, 1, 36, 0, 720)
        p.add(cum_stack(ts2, s), line(cx, ts2.sy(0), cx + cw, ts2.sy(0), HAIR, 1))
        p.add(sim_line(ts2, SIM_ALLE["serier"][r], sw=1.4))
    p.add(para(x + 18, r1y + 466, "Øverst: alle 36 uker på samme V. Under: løpende kostnad, lager i lys blå og restordre i oker. Stiplet: Simulert, alle fire teller det som er på vei (Kjede " + kr(SIM_ALLE["kjedekost"]) + " kr).", w - 36, 13, 17, c=SEC))

    # Rad 2: Steg 4
    r2y, r2h = 590, 590
    x, w = 40, 1530
    p.add(sheet(x, r2y, w, r2h))
    p.add(step_head(x + 18, r2y + 34, 4, "Ditt øyeblikk: Uke 11"))
    # Kol A
    ax, aw = x + 18, 320
    i = 10
    pos = posisjon(G, 11)
    p.add(t(ax, r2y + 68, "Dette så du", 16, "r", INK, 700))
    v = V(ax, r2y + 92, aw, 150)
    p.add(v.frame(fs=13, ytitle="", axis="", ygrid=(20,), ylab=False), v.trail(NG, 11), v.nowpt(NG[10], 6))
    rows = [("Lager", G["lager"][i]), ("Restordre", G["restordre"][i]), ("Innkommende ordre", G["innkommende_ordre"][i]), ("Levering", G["levering"][i]), ("På vei", G["paa_vei"][i]), ("Posisjon", pos)]
    yy = r2y + 292
    for lab, val in rows:
        p.add(t(ax, yy, lab, 14, "s", SEC), t(ax + aw, yy, val, 14, "s", INK, 700 if lab == "Posisjon" else 400, "end", True), line(ax, yy + 7, ax + aw, yy + 7, GRID, 1))
        yy += 24
    yy += 14
    p.add(t(ax, yy + 6, "Dette bestilte du", 16, "r", INK, 700))
    p.add(t(ax, yy + 34, f"Ordre 24. Posisjon {pos} ble {pos + 24}.", 17, "s", INK, 700))
    p.add(para(ax, yy + 58, f"{G['paa_vei'][i]} var allerede på vei. Av {G['ordre'][10]} kom {G['levering'][14]} fram i Uke 15.", aw, 14, 19, c=SEC))
    # Kol B
    bx, bw = x + 370, 650
    a_, b_ = cum_parts(G)
    r_sum = b_[-1]
    l_sum = a_[-1]
    rw = [i2 for i2 in range(36) if G["restordre"][i2] > 0]
    lw_late = [i2 for i2 in range(24, 36) if G["lager"][i2] > 0]
    lev_seg = G["levering"][rw[0]:rw[-1] + 1]
    p.add(t(bx, r2y + 68, f"Du betalte {kr(G['kost_sum'][-1])} kr. Her ble det dyrt.", 22, "r", INK, 700))
    ts = TS(bx + 42, r2y + 96, bw - 170, 300, 1, 36, 0, 600)
    for val in (200, 400, 600):
        p.add(line(bx, ts.sy(val), bx + bw - 120, ts.sy(val), GRID, 1), t(bx, ts.sy(val) - 3, f"{val} kr", 13, "s", MUT, num=True))
    # marker restordreperioden
    p.add(cum_stack(ts, G), line(ts.x, ts.sy(0), ts.x + ts.w, ts.sy(0), HAIR, 1))
    p.add(sim_line(ts, SIM_SARA["serier"]["Grossist"]), sim_line(ts, SIM_ALLE["serier"]["Grossist"], c=SEC, sw=1.4, dash="2 4"))
    p.add(line(ts.sx(11), ts.sy(0), ts.sx(11), ts.sy(G["kost_sum"][10]) - 40, INK, 1), circ(ts.sx(11), ts.sy(G["kost_sum"][10]), 5, INK, PAPER, 1.6))
    p.add(t(ts.sx(11) - 5, ts.sy(G["kost_sum"][10]) - 46, f"Uke 11: {kr(G['kost_sum'][10])} kr", 14, "s", INK, 700, "middle", True))
    ex = ts.x + ts.w + 8
    p.add(t(ex, ts.sy(G["kost_sum"][-1]) + 4, f"{kr(G['kost_sum'][-1])} kr", 14, "s", INK, 700, num=True), t(ex, ts.sy(G["kost_sum"][-1]) + 21, "Spilt", 13, "s", SEC))
    yy2 = ts.sy(SIM_SARA["serier"]["Grossist"]["kost_sum"][-1])
    p.add(t(ex, yy2 + 8, f"{kr(SIM_SARA['kost_per_rolle']['Grossist'])} kr", 14, "s", INK, 500, num=True), t(ex, yy2 + 25, "Simulert: bare du", 13, "s", SEC))
    yy3 = ts.sy(SIM_ALLE["serier"]["Grossist"]["kost_sum"][-1])
    p.add(t(ex, yy3 + 4, f"{kr(SIM_ALLE['kost_per_rolle']['Grossist'])} kr", 14, "s", INK, 500, num=True), t(ex, yy3 + 21, "Simulert: alle fire", 13, "s", SEC))
    p.add(t(ts.sx(1), ts.sy(0) + 17, "Uke 1", 13, "s", MUT), t(ts.sx(36), ts.sy(0) + 17, "Uke 36", 13, "s", MUT, a="end"))
    p.add(t(ts.sx(29), ts.sy(200), f"Restordre {kr(r_sum)} kr", 14, "s", INK, 700, "middle", True))
    p.add(t(ts.sx(31), ts.sy(36), f"Lager {kr(l_sum)} kr", 14, "s", INK, 700, "middle", True))
    wr0, wr1 = rw[0] + 1, rw[-1] + 1
    pv_mx = max(G["paa_vei"][rw[0]:rw[-1] + 1])
    pv_wk = G["paa_vei"].index(pv_mx) + 1
    nar = (
        f"I uke {wr0} til {wr1} sto du på venstre arm og betalte {kr(r_sum)} kr. På vei vokste til {pv_mx} i Uke {pv_wk}, mens levering lå på {min(lev_seg)} til {max(lev_seg)}, "
        f"fordi Distributør selv hadde restordre fra Uke {next(k for k, v_ in enumerate(S17['Distributør']['restordre']) if v_ > 0) + 1}. Så kom alt: {G['levering'][24]} og {G['levering'][25]} i Uke 25 og 26, og du gikk over på høyre arm. Det er kjedens forsinkelser, ikke én ordre, som gir formen."
    )
    p.add(para(bx, r2y + 438, nar, bw - 20, 15, 21))
    p.add(rect(bx, r2y + 512, 146, 22, TINT, HAIR, 3), t(bx + 8, r2y + 528, "KI-generert, kan ta feil", 13, "s", INK, 500))
    p.add(t(bx + 156, r2y + 528, "Tallene er fra loggen.", 13, "s", SEC))
    # Simulert merknad
    fm = lambda v_: f"{v_:.1f}×".replace(".", ",")
    p.add(t(bx, r2y + 556, f"Simulert: du regner med alt på vei fra Uke 5. Grossist {kr(SIM_SARA['kost_per_rolle']['Grossist'])} kr, Kjede {kr(SIM_SARA['kjedekost'])} kr, Forsterkning {fm(SIM_SARA['forsterkning']['Grossist'])} mot {fm(FX['spill17']['forsterkning']['Grossist'])}.", 13, "s", SEC))
    p.add(t(bx, r2y + 574, "Viser sammenhengen, ikke en fasit.", 13, "s", SEC))
    # Kol C
    cx, cw3 = x + 1050, 462
    p.add(t(cx, r2y + 68, "Dette så de andre i Uke 11", 16, "r", INK, 700))
    yy = r2y + 96
    for r in ["Detaljist", "Distributør", "Fabrikk"]:
        s = S17[r]
        lag = s["lager"][10]
        res = s["restordre"][10]
        st = f"restordre {res}" if res else f"lager {lag}"
        p.add(t(cx, yy, f"{NAVN[r]} ({r})", 14, "s", INK, 500), t(cx + cw3, yy, f"{s['innkommende_ordre'][10]} inn, {st}", 14, "s", SEC, a="end", num=True), line(cx, yy + 7, cx + cw3, yy + 7, GRID, 1))
        yy += 26
    d13 = S17["Distributør"]["innkommende_ordre"][12]
    p.add(para(cx, yy + 6, f"Mikkel kunne ikke se din ordre før den kom inn: {d13} i Uke 13. Ingen så det hele.", cw3, 14, 19, c=SEC))
    yy += 62
    p.add(t(cx, yy + 10, "Hvorfor svingning koster", 16, "r", INK, 700))
    mean_net = sum(NG) / 36
    tot = G["kost_sum"][-1]
    avg = tot / 36
    v = V(cx, yy + 28, cw3, 170)
    p.add(v.frame(fs=13, ytitle="", axis="", ygrid=(20,), ylab=False), v.allpts(NG, 3, INK, 0.5))
    p.add(line(v.sx(-avg), v.sy(avg), v.sx(2 * avg), v.sy(avg), INK, 1.3), t(v.sx(mean_net) + 8, v.sy(avg) - 6, f"Snitt {kr(avg)} kr per uke", 13, "s", INK, 700, "start", True))
    mx = v.sx(mean_net)
    p.add(line(mx, v.sy(avg), mx, v.sy(c_of(mean_net)), INK, 1.3), circ(mx, v.sy(c_of(mean_net)), 4.5, PAPER, INK, 1.8))
    p.add(para(cx, yy + 28 + 170 + 42, f"Netto lager var i snitt {kr(mean_net, 1)}. Jevn drift på det snittet er {kr(c_of(mean_net) * 36)} kr. Uker på hver side av null veier ikke hverandre opp, så du betalte {kr(tot)} kr. Et regnestykke, ikke et mål.", cw3, 14, 19))

    # Steg 5
    x, w = 1590, 470
    p.add(sheet(x, r2y, w, r2h), step_head(x + 18, r2y + 34, 5, "Debrief-quiz"))
    p.add(para(x + 18, r2y + 72, "Netto lager er −20 én uke og +20 neste uke. Hva koster de to ukene til sammen?", w - 36, 18, 25, "r", INK))
    opts = [("0 kr: snittet er null", "feil"), (f"{kr(c_of(-20) / 2 + c_of(20) / 2)} kr", ""), (f"{kr(c_of(-20) + c_of(20))} kr", "riktig"), ("40,00 kr", "")]
    yy = r2y + 138
    for lab, st in opts:
        strong = st != ""
        p.add(rect(x + 18, yy, w - 36, 42, PAPER, INK if strong else HAIR, 5, 1.6 if strong else 1))
        p.add(t(x + 32, yy + 27, lab, 15, "s", INK, 700 if strong else 400))
        if st == "feil":
            p.add(t(x + w - 32, yy + 27, "Ditt svar: feil", 14, "s", INK, 500, "end"))
        if st == "riktig":
            p.add(t(x + w - 32, yy + 27, "Riktig", 14, "s", INK, 700, "end"))
        yy += 50
    v = V(x + 18, yy + 22, 210, 120, 40, 40)
    p.add(v.frame(fs=13, ticks=(-20, 0, 20), ygrid=(), arm=1.8, axis="", ytitle="", ylab=False))
    a1, a2 = v.sx(-20), v.sx(20)
    p.add(circ(a1, v.sy(20), 5, INK, PAPER, 1.5), circ(a2, v.sy(10), 5, INK, PAPER, 1.5))
    p.add(t(a1 + 10, v.sy(20) + 4, "20,00", 13, "s", INK, 700, "start", True), t(a2 - 10, v.sy(10) - 2, "10,00", 13, "s", INK, 700, "end", True))
    p.add(para(x + 242, yy + 40, "Hvorfor: kostnaden regnes for hver uke, ikke på snittet. Restordre koster 1,00 og lager 0,50 per enhet. 20,00 + 10,00 = 30,00 kr.", w - 262, 14, 19))
    p.save()


# ---------- lærer oversikt ----------
def swarm(values, sx, r, base, step=None):
    """Enkel bikube: stabler punkter oppover uten overlapp."""
    step = step or r * 2 + 1
    placed = []
    out = []
    for item, val in sorted(values, key=lambda kv: kv[1]):
        xx = sx(val)
        level = 0
        while any(abs(px - xx) < step and lv == level for px, lv in placed):
            level += 1
        placed.append((xx, level))
        out.append((item, xx, base - r - level * step))
    return out


def status_shape(x, y, status, near=False):
    if near:
        return f'<polygon points="{x},{y - 9} {x + 10},{y + 1} {x - 10 + 10},{y + 1}" fill="none"/>' + f'<polygon points="{x + 5},{y - 10} {x + 11},{y + 1} {x - 1},{y + 1}" fill="{SIG}"/>'
    if status == "ferdig":
        return circ(x + 5, y - 4, 4.5, INK)
    if status == "pågår":
        return circ(x + 5, y - 4, 3.2, INK)
    if status == "venter":
        return circ(x + 5, y - 4, 4.5, PAPER, INK, 1.6)
    return rect(x + 1, y - 9, 3, 10, INK) + rect(x + 6, y - 9, 3, 10, INK)


def mini_net(x, y, w, h, spill, yr=None, weeks=36, sw=1.0):
    yr = yr or YR_KL
    mid = y + h / 2
    o = [line(x, mid, x + w, mid, GRID, 1)]
    tones = {"Detaljist": 0.35, "Grossist": 0.55, "Distributør": 0.75, "Fabrikk": 1.0}
    for r in ROLLER:
        n = spill["netto_lager"][r]
        pts = [(x + i / (weeks - 1) * w, mid - max(-yr, min(yr, v)) / yr * (h / 2)) for i, v in enumerate(n)]
        o.append(poly(pts, INK, sw, None, "none", tones[r]))
    return "".join(o)


def dot_plot(x, y, w, h, spill_list, size=13, labels=True, band=True):
    F = KL["ferdige"]["kjedekost"]
    fj = KL["fjoraaret"]
    xmax = 3800
    sx = lambda v: x + v / xmax * w
    base = y + h
    o = []
    if band:
        o.append(rect(sx(F["q1"]), y + 6, sx(F["q3"]) - sx(F["q1"]), h - 6, TINT))
    for v in range(0, 4000, 1000):
        o.append(line(sx(v), base, sx(v), base + 5, HAIR, 1))
        o.append(t(sx(v), base + 21, f"{kr(v, 0)}", size, "s", SEC, a="middle", num=True))
    o.append(t(x + w, base + 21, "kr", size, "s", SEC, a="end"))
    o.append(line(x, base, x + w, base, HAIR, 1))
    o.append(line(sx(F["median"]), y + 2, sx(F["median"]), base, INK, 1.4))
    o.append(line(sx(fj["median_kjedekost"]), y + 2, sx(fj["median_kjedekost"]), base, SEC, 1.2, "4 3"))
    if labels:
        o.append(t(sx(F["median"]) - 6, y + 14, f"Median i år {kr(F['median'], 0)}", size, "s", INK, 700, "end", True))
        o.append(t(sx(fj["median_kjedekost"]) + 6, y + 14, f"Fjorårets median {kr(fj['median_kjedekost'], 0)}", size, "s", SEC, 400, "start", True))
    return o, sx, base


def build_oversikt():
    p = Page("08-laerer-oversikt", "oversikt", 1600, 1000, "Kurve: Oversikt for faglærer", "60 Klassespill: kjedekostnad i prikkdiagram med fjorårets median, trakt, statustabell med netto lager, og ferdige spill.")
    sp = KL["spill"]
    p.add(rect(40, 20, 1520, 960, PAPER, HAIR, 8))
    p.add(t(64, 62, "Oversikt", 28, "r", INK, 700))
    n_f = sum(1 for s in sp if s["status"] == "ferdig")
    n_p = sum(1 for s in sp if s["status"] == "pågår")
    n_pa = sum(1 for s in sp if s["status"] == "pauset")
    n_v = sum(1 for s in sp if s["status"] == "venter")
    p.add(t(180, 62, f"class-of-1994 · IBE160 · 60 Klassespill: {n_f} ferdig, {n_p + n_pa} pågår (herav {n_pa} pauset), {n_v} venter", 16, "s", SEC, num=True))
    p.add(demodata(1536, 62, "end", 13))
    # Filter
    fx = 64
    for lab, on in [("Alle 60", True), (f"Venter {n_v}", False), (f"Pauset {n_pa}", False), (f"Pågår {n_p}", False), (f"Ferdig {n_f}", False), ("Med KI-seter", False)]:
        wd = tw(lab, 14) + 24
        p.add(rect(fx, 80, wd, 28, INK if on else PAPER, None if on else HAIR, 4), t(fx + 12, 99, lab, 14, "s", PAPER if on else INK, 500))
        fx += wd + 6
    p.add(button(1376, 80, 160, 30, "Send Melding", True, 14))
    # Prikkdiagram
    lx, lw = 64, 500
    p.add(t(lx, 146, "Kjedekostnad per spill", 20, "r", INK, 700))
    p.add(para(lx, 170, "Hvert punkt er ett spill. Fylt: ferdig. Ring: pågår, foreløpig kostnad. Bare faglærer ser dette.", lw, 14, 19, c=SEC))
    els, sx, base = dot_plot(lx, 212, lw, 268, sp)
    p.add(*els)
    vals = [(s, s["kjedekost"]) for s in sp]
    placed = swarm(vals, sx, 6.4, base - 1, 13.6)
    for s, xx, yy in placed:
        if s["status"] == "ferdig":
            p.add(circ(xx, yy, 6.1, INK, PAPER, 0.8))
        else:
            near = s.get("ventet_timer", 0) >= 23
            p.add(circ(xx, yy, 5.2, PAPER, SIG if near else INK, 2 if near else 1.4))
        if s["spill"] == 2:
            p.add(line(xx, yy - 6, xx, base - 148, SIG, 1), t(xx, base - 153, "Spill 2", 13, "s", SIG, 700, "middle"))
    fin = [s for s in sp if s["status"] == "ferdig"]
    lo = min(fin, key=lambda s: s["kjedekost"])
    hi = max(fin, key=lambda s: s["kjedekost"])
    hy_ = next(yy for s, xx, yy in placed if s["spill"] == hi["spill"])
    p.add(t(sx(hi["kjedekost"]), hy_ - 11, f"Spill {hi['spill']}", 13, "s", SEC, a="middle"))
    F = KL["ferdige"]["kjedekost"]
    p.add(t(lx, 520, f"Midtre halvdel av ferdige spill: {kr(F['q1'], 0)} til {kr(F['q3'], 0)} kr. Spenn: {kr(F['min'], 0)} til {kr(F['max'], 0)} kr.", 14, "s", INK, num=True))
    p.add(t(lx, 540, f"Fjoråret: class-of-1993, {KL['fjoraaret']['spill']} spill. Ikke et mål for studentene, og de ser det ikke.", 14, "s", SEC))
    # Trakt
    fy = 584
    p.add(line(lx, fy - 14, lx + lw, fy - 14, GRID, 1))
    p.add(t(lx, fy + 10, "Hvor studentene er", 20, "r", INK, 700))
    trakt = KL["traktA"]
    labs = [("registrert", "Registrert"), ("klassespill_ferdig", "Klassespill ferdig"), ("debrief_ferdig", "Debrief ferdig"), ("quiz_bestått", "Quiz bestått"), ("replay_ferdig", "Replay ferdig"), ("test_levert", "Test levert"), ("ki_vurdering_klar", "KI-vurdering klar")]
    yy = fy + 36
    mx = trakt["registrert"]
    for k, lab in labs:
        v = trakt[k]
        p.add(t(lx, yy + 12, lab, 14, "s", INK))
        p.add(rect(lx + 140, yy, max(1, v / mx * (lw - 190)), 16, "#8EA2BD"))
        p.add(t(lx + lw, yy + 13, v, 14, "s", INK, 500, "end", True))
        yy += 25
    yy += 18
    p.add(line(lx, yy - 12, lx + lw, yy - 12, GRID, 1))
    p.add(t(lx, yy + 12, "Mønstre i ordrene", 20, "r", INK, 700))
    yy += 36
    for lab, v in KL["moenstre"].items():
        p.add(t(lx, yy, lab, 14, "s", INK), t(lx + lw, yy, v, 14, "s", INK, 500, "end", True))
        yy += 21
    # Tabell
    tx, tw_ = 590, 946
    cols = {"spill": 0, "status": 54, "uke": 158, "venter": 200, "lenge": 372, "ki": 426, "kost": 520, "net": 540, "tiltak": 736}
    hy = 146
    p.add(t(tx, hy, "Trenger noe, eller pågår", 20, "r", INK, 700))
    hy += 26
    for k, lab, a in [("spill", "Spill", "start"), ("status", "Status", "start"), ("uke", "Uke", "start"), ("venter", "Venter på", "start"), ("lenge", "Tid", "start"), ("ki", "KI-seter", "start"), ("kost", "Kost", "end"), ("net", "Netto lager, fire Roller", "start"), ("tiltak", "Tiltak", "start")]:
        p.add(t(tx + cols[k], hy, lab, 13, "s", SEC, 500, a))
    p.add(line(tx, hy + 7, tx + tw_, hy + 7, HAIR, 1))
    aktive = [s for s in sp if s["status"] != "ferdig"]
    order = {"venter": 0, "pauset": 1, "pågår": 2}
    aktive.sort(key=lambda s: (order[s["status"]], -s.get("ventet_timer", 0), -s["uke"]))
    yy = hy + 12
    rh = 27
    for s in aktive:
        near = s.get("ventet_timer", 0) >= 23
        if near:
            p.add(rect(tx - 6, yy, tw_ + 12, rh, SIG_F))
        by = yy + 17
        p.add(t(tx + cols["spill"], by, s["spill"], 14, "s", INK, 700, num=True))
        p.add(status_shape(tx + cols["status"], by, s["status"], near))
        p.add(t(tx + cols["status"] + 16, by, s["status"].capitalize(), 14, "s", SIG if near else INK, 700 if near else 400))
        p.add(t(tx + cols["uke"], by, s["uke"], 14, "s", INK, num=True))
        if s.get("venter_paa"):
            p.add(t(tx + cols["venter"], by, f"{s['navn']} ({s['venter_paa']})", 14, "s", INK))
            p.add(t(tx + cols["lenge"], by, f"{s['ventet_timer']} t", 14, "s", SIG if near else INK, 700 if near else 400, num=True))
        elif s.get("fortsetter"):
            p.add(t(tx + cols["venter"], by, f"Fortsetter {s['fortsetter']}", 14, "s", SEC))
        if s["ki_seter"]:
            p.add(t(tx + cols["ki"], by, f"{s['ki_seter']} KI", 14, "s", INK, 500, num=True))
        p.add(t(tx + cols["kost"], by, kr(s["kjedekost"], 0), 14, "s", INK, 400, "end", True))
        p.add(mini_net(tx + cols["net"], yy + 3, 180, rh - 6, s))
        if near:
            p.add(rect(tx + cols["tiltak"], yy + 2, 104, rh - 4, SIG), t(tx + cols["tiltak"] + 52, by - 1, "Send Melding", 13, "s", PAPER, 700, "middle"))
            p.add(t(tx + tw_, by, "KI overtar om 1 t", 13, "s", SIG, 700, "end"))
        elif s["status"] == "venter":
            p.add(t(tx + cols["tiltak"], by, "Send Melding", 14, "s", INK, 500), line(tx + cols["tiltak"], by + 3, tx + cols["tiltak"] + tw("Send Melding", 14), by + 3, HAIR, 1))
        elif s["status"] == "pauset":
            p.add(t(tx + cols["tiltak"], by, "Gjenoppta", 14, "s", INK, 500), line(tx + cols["tiltak"], by + 3, tx + cols["tiltak"] + tw("Gjenoppta", 14), by + 3, HAIR, 1))
        else:
            p.add(t(tx + cols["tiltak"], by, "Pause", 14, "s", SEC))
        p.add(line(tx, yy + rh, tx + tw_, yy + rh, GRID, 1))
        yy += rh
    yy += 30
    p.add(t(tx, yy, f"Ferdig ({n_f}): netto lager, fire Roller, og kjedekostnad", 20, "r", INK, 700))
    p.add(t(tx + tw_, yy, f"Samme skala i alle ruter, ±{YR_KL} enheter", 13, "s", SEC, a="end"))
    yy += 12
    cells = sorted(fin, key=lambda s: s["spill"])
    per = 14
    cw = tw_ / per
    ch = 54
    for n, s in enumerate(cells):
        cx = tx + (n % per) * cw
        cy = yy + (n // per) * ch
        p.add(mini_net(cx, cy + 2, cw - 8, 32, s, sw=0.7))
        p.add(t(cx, cy + 48, s["spill"], 12, "s", INK, 700, num=True), t(cx + cw - 8, cy + 48, kr(s["kjedekost"], 0), 12, "s", SEC, 400, "end", True))
    p.save()


# ---------- landing ----------
def build_landing():
    p = Page("01-landing", "landing", 1440, 1200, "Kurve: landingsside for faglærere", "Første skjermbilde med ett setes V-diagram, og starten på seksjonen om lærerens oversikt.")
    p.add(t(90, 52, "Kurve", 28, "r", INK, 700))
    p.add(t(1350, 50, "Logg inn", 16, "s", INK, 500, "end"))
    p.add(line(90, 72, 1350, 72, GRID, 1))
    lines = ["Hele øvelsen om", "forsyningskjeder, fra", "invitasjon til PDF-rapport"]
    yy = 164
    for ln in lines:
        p.add(t(90, yy, ln, 50, "r", INK, 700))
        yy += 60
    p.add(para(90, yy + 10, "Fire studenter styrer hvert sitt ledd i kjeden, med ett heltall i uka. Systemet regner, og grafen viser hva uka kostet. Du følger alle spillene på én skjerm.", 500, 20, 29, c=SEC))
    yy += 134
    p.add(button(90, yy, 220, 56, "Be om lærertilgang", True, 18))
    p.add(button(322, yy, 120, 56, "Logg inn", False, 18))
    # V
    vx, vy, vw, vh = 680, 120, 670, 450
    v = V(vx, vy, vw, vh)
    p.add(v.frame(fs=15, ygrid=(10, 20, 30), arm=3), v.trail(NG, 11), v.nowpt(NG[10], 9))
    p.add(t(vx, v.sy(0) - 50, "Restordre", 17, "s", INK, 700), t(vx, v.sy(0) - 28, "1,00 kr per enhet per uke", 15, "s", SEC))
    p.add(t(vx + vw, v.sy(0) - 50, "Lager", 17, "s", INK, 700, "end"), t(vx + vw, v.sy(0) - 28, "0,50 kr per enhet per uke", 15, "s", SEC, a="end"))
    cx = vx + vw / 2
    p.add(line(v.sx(NG[10]), v.sy(c_of(NG[10])) - 12, cx, vy + 68, HAIR, 1))
    p.add(t(cx, vy + 28, "Én uke for ett sete", 22, "r", INK, 700, "middle"))
    p.add(t(cx, vy + 54, f"{G['restordre'][10]} i restordre: {kr(c_of(NG[10]))} kr denne uka", 17, "s", SEC, a="middle"))
    p.add(demodata(vx, vy + vh + 74, "start", 14, ". Ett sete ser bare sine egne tall."))
    # Neste seksjon
    y2 = 740
    p.add(line(90, y2, 1350, y2, HAIR, 1))
    p.add(t(90, y2 + 62, "Alle spillene på én skjerm", 38, "r", INK, 700))
    p.add(para(90, y2 + 100, "Hvert punkt er ett Klassespill. Du ser spredningen i klassen med ett blikk, og hvilke spill som venter på noen.", 500, 18, 26, c=SEC))
    facts = ["Kjører hele øvelsen fra invitasjon til PDF-rapport", "Klasser på rundt 250 studenter", "KI-spillere fyller tomme seter, alltid merket", "Ett fravær stopper ikke gruppa", "Ingen spill blir stående uferdig", "På mobil og på norsk", "Studentlisten kommer fra Canvas-eksport"]
    yy = y2 + 180
    for f in facts:
        p.add(t(90, yy, f, 17, "s", INK), line(90, yy + 10, 590, yy + 10, GRID, 1))
        yy += 32
    els, sx, base = dot_plot(680, y2 + 50, 670, 240, KL["spill"], 15, True, False)
    p.add(*els)
    for s, xx, yy2 in swarm([(s, s["kjedekost"]) for s in KL["spill"]], sx, 6, base - 1, 13):
        if s["status"] == "ferdig":
            p.add(circ(xx, yy2, 5.8, INK, PAPER, 0.8))
        else:
            p.add(circ(xx, yy2, 5, PAPER, INK, 1.6))
    p.add(t(680, base + 50, "Kjedekostnad per spill. Fylt: ferdig. Ring: pågår. Demodata.", 15, "s", SEC))
    p.save()


# ---------- klasse ----------
def build_klasse():
    p = Page("02-laerer-klasse", "klasse", 1440, 1000, "Kurve: lag Klasse", "Navn og emnekode, last opp Canvas-fil, velg e-postkolonne, ugyldige rader, send Invitasjoner og status.", PAPER)
    R = KL["roster"]
    p.add(t(60, 58, "Lag Klasse", 34, "r", INK, 700))
    p.add(demodata(1380, 58, "end", 14))
    p.add(line(60, 76, 1380, 76, GRID, 1))
    lx, lw = 60, 400
    p.add(field(lx, 124, lw, 44, "Navn på Klassen", "class-of-1994"))
    p.add(field(lx, 208, 180, 44, "Emnekode", "IBE160"))
    p.add(t(lx, 306, "Studentliste", 20, "r", INK, 700))
    p.add(rect(lx, 322, lw, 76, TINT, HAIR, 4))
    p.add(t(lx + 16, 352, "ibe160_canvas_eksport.xlsx", 16, "s", INK, 700))
    p.add(t(lx + 16, 376, f"{R['paa_lista']} rader lest fra Canvas-eksporten", 14, "s", SEC))
    p.add(t(lx + lw - 16, 352, "Bytt fil", 14, "s", INK, 500, "end"))
    p.add(field(lx, 444, 240, 44, "Hvilken kolonne er e-post?", "SIS Login ID"))
    p.add(t(lx, 512, "Forslag fra kolonnenavn og innhold. Du kan velge en annen.", 14, "s", SEC))
    p.add(t(lx, 572, "Invitasjoner", 20, "r", INK, 700))
    gyldige = R["paa_lista"] - R["ugyldige_rader"]
    p.add(para(lx, 600, f"{gyldige} gyldige adresser får Invitasjon. Invitasjonen er gyldig i 14 dager. {R['ugyldige_rader']} rader må rettes eller registreres manuelt.", lw, 15, 21, c=SEC))
    p.add(button(lx, 660, 280, 50, f"Send {gyldige} Invitasjoner", True, 17))
    # Tabell med forhåndsvisning
    tx, tw2 = 520, 860
    p.add(t(tx, 106, "Forhåndsvisning av fila", 22, "r", INK, 700))
    pv_cols = [("Student", 0), ("ID", 220), ("SIS Login ID", 340), ("Seksjon", 640)]
    p.add(rect(tx + 330, 122, 280, 128, TINT, INK, 3, 1.2))
    for lab, dx in pv_cols:
        p.add(t(tx + dx, 144, lab, 14, "s", INK if dx == 340 else SEC, 700 if dx == 340 else 500))
    p.add(t(tx + 600, 144, "E-post", 13, "s", INK, 700, "end"))
    p.add(line(tx, 152, tx + tw2, 152, HAIR, 1))
    for n, (a_, b_, c_, d_) in enumerate([("Ida Solberg", "204411", "ida.solberg@stud.no", "IBE160 V01"), ("Sara Lunde", "204412", "sara.lunde@stud.no", "IBE160 V01"), ("Mikkel Aas", "204413", "mikkel.aas@stud.no", "IBE160 V02")]):
        yy_ = 176 + n * 28
        p.add(t(tx, yy_, a_, 15, "s", INK), t(tx + 220, yy_, b_, 15, "s", SEC, num=True), t(tx + 340, yy_, c_, 15, "s", INK), t(tx + 640, yy_, d_, 15, "s", SEC))
    p.add(t(tx, 298, f"Ugyldige rader: {R['ugyldige_rader']} av {R['paa_lista']}", 22, "r", INK, 700))
    heads = [("Rad", 0), ("Student", 60), ("SIS Login ID", 280), ("Hva er feil", 530), ("Tiltak", 730)]
    for lab, dx in heads:
        p.add(t(tx + dx, 332, lab, 14, "s", SEC, 500))
    p.add(line(tx, 340, tx + tw2, 340, HAIR, 1))
    rows = [(37, "Emma Hansen", "emma.hansen@stud", "Mangler domene"), (88, "Oskar Berg", "oskar.berg.stud.no", "Mangler @"), (141, "Liv Moe", "", "Tom celle"), (203, "Nora Dahl", "nora dahl@stud.no", "Mellomrom i adressen")]
    yy = 366
    for r, name, mail, err in rows:
        p.add(t(tx, yy, r, 15, "s", INK, 700, num=True), t(tx + 60, yy, name, 15, "s", INK), t(tx + 280, yy, mail or "tom", 15, "s", INK if mail else MUT), t(tx + 530, yy, err, 15, "s", INK))
        p.add(t(tx + 730, yy, "Rett adressen", 15, "s", INK, 500), line(tx + 730, yy + 4, tx + 730 + tw("Rett adressen", 15), yy + 4, HAIR, 1))
        p.add(line(tx, yy + 14, tx + tw2, yy + 14, GRID, 1))
        yy += 40
    yy += 30
    p.add(t(tx, yy, "Status etter utsending", 22, "r", INK, 700))
    tot = R["paa_lista"]
    sc = tw2 / tot
    bx = tx
    yb = yy + 22
    segs = [(R["registrert"], INK, f"{R['registrert']} registrert"), (R["manuelt_registrert"], "#7C90AC", f"{R['manuelt_registrert']} manuelt registrert"), (R["uregistrert"], HAIR, f"{R['uregistrert']} uregistrert")]
    for v, col, lab in segs:
        p.add(rect(bx, yb, v * sc - 2, 26, col))
        bx += v * sc
    p.add(t(tx, yb + 50, segs[0][2], 16, "s", INK, 700, num=True))
    p.add(t(tx + tw2 - 170, yb + 50, segs[1][2], 15, "s", INK, 400, "end", True))
    p.add(t(tx + tw2, yb + 50, segs[2][2], 15, "s", INK, 400, "end", True))
    yy = yb + 86
    p.add(t(tx, yy, "Uregistrerte studenter", 16, "s", INK, 700))
    p.add(t(tx + tw2, yy, "Send påminnelse til alle 10", 15, "s", INK, 500, "end"))
    p.add(line(tx + tw2 - tw("Send påminnelse til alle 10", 15), yy + 4, tx + tw2, yy + 4, HAIR, 1))
    p.add(line(tx, yy + 12, tx + tw2, yy + 12, GRID, 1))
    p.add(para(tx, yy + 40, "Fravær stopper ikke spillet: KI-spillere fyller tomme seter når Klasseøkten starter. Studentene må ikke ha logget inn før fordelingen er bekreftet.", 720, 15, 21, c=SEC))
    p.save()


# ---------- oppsett ----------
def build_oppsett():
    p = Page("03-laerer-spill", "oppsett", 1440, 1100, "Kurve: Klasseøkt", "Forhåndsutfylte standarder, KI-modus, Debrief-modus, Obligatorisk, datoer, Labtimer og fordelingsforhåndsvisning.", PAPER)
    p.add(t(60, 58, "Klasseøkt for class-of-1994", 34, "r", INK, 700))
    p.add(t(60, 88, "Standardene «Klassisk» er fylt ut. Du kan lagre uten å endre noe.", 16, "s", SEC))
    p.add(button(1180, 44, 200, 46, "Lagre Klasseøkt", True, 16))
    p.add(line(60, 106, 1380, 106, GRID, 1))
    # Spillinnstillinger
    x1 = 60
    p.add(t(x1, 146, "Spillinnstillinger", 22, "r", INK, 700))
    rows = [("Startlager", "12"), ("I hvert ledd ved start", "4 enheter"), ("Ordreforsinkelse", "2 uker"), ("Fraktforsinkelse", "2 uker"), ("Produksjonsforsinkelse", "2 uker"), ("Etterspørsel", "4, så 8 fra Uke 5"), ("Antall uker", "36"), ("Veiledede uker", "1 til 4")]
    yy = 176
    for lab, val in rows:
        p.add(t(x1, yy + 5, lab, 15, "s", SEC))
        p.add(rect(x1 + 210, yy - 16, 190, 32, PAPER, HAIR, 4), t(x1 + 220, yy + 5, val, 15, "s", INK, num=True))
        yy += 46
    p.add(para(x1, yy + 8, "Kildene er uenige om forsinkelsene. Dette er produktets standard.", 400, 14, 19, c=SEC))
    yy += 56
    p.add(t(x1, yy, "Kostnad", 22, "r", INK, 700))
    p.add(t(x1, yy + 34, "Lagerkost", 15, "s", SEC), rect(x1 + 210, yy + 13, 190, 32, PAPER, HAIR, 4), t(x1 + 220, yy + 34, "0,50 per enhet per uke", 15, "s", INK))
    p.add(t(x1, yy + 74, "Restordrekost", 15, "s", SEC), rect(x1 + 210, yy + 53, 190, 32, PAPER, HAIR, 4), t(x1 + 220, yy + 74, "1,00 per enhet per uke", 15, "s", INK))
    v = V(x1, yy + 130, 400, 170)
    p.add(v.frame(fs=13, ygrid=(), axis="Netto lager", ytitle="Slik blir V-en studentene ser", ylab=False))
    # Midtkolonne
    x2 = 520
    p.add(t(x2, 146, "Gjennomføring", 22, "r", INK, 700))
    p.add(t(x2, 180, "KI-modus", 15, "s", SEC))
    for n, (lab, on) in enumerate([("LLM-spillere", True), ("Regelbaserte", False)]):
        wd = 132
        p.add(rect(x2 + 130 + n * (wd + 6), 160, wd, 32, INK if on else PAPER, None if on else HAIR, 4), t(x2 + 130 + n * (wd + 6) + wd / 2, 181, lab, 15, "s", PAPER if on else INK, 500, "middle"))
    p.add(t(x2, 224, "Debrief-modus", 15, "s", SEC))
    for n, (lab, on) in enumerate([("Gruppedebrief", True), ("Individuell", False)]):
        wd = 132
        p.add(rect(x2 + 130 + n * (wd + 6), 204, wd, 32, INK if on else PAPER, None if on else HAIR, 4), t(x2 + 130 + n * (wd + 6) + wd / 2, 225, lab, 15, "s", PAPER if on else INK, 500, "middle"))
    p.add(t(x2, 268, "Inaktivitetsgrense", 15, "s", SEC), rect(x2 + 130, 248, 100, 32, PAPER, HAIR, 4), t(x2 + 140, 269, "24 t", 15, "s", INK), t(x2 + 244, 269, "før KI overtar", 15, "s", SEC))
    p.add(rect(x2, 298, 20, 20, INK, None, 3), poly([(x2 + 5, 308), (x2 + 9, 313), (x2 + 15, 303)], PAPER, 2), t(x2 + 30, 314, "Obligatorisk", 15, "s", INK, 700))
    p.add(t(x2 + 130, 314, "Studentene ser at øvelsen er obligatorisk.", 15, "s", SEC))
    p.add(t(x2, 370, "Datoer", 22, "r", INK, 700))
    yy = 400
    for lab, val in [("Start", "ti. 24. nov 2026"), ("Spillfrist", "ti. 8. des"), ("Debrief-frist", "fr. 11. des"), ("Testfrist", "fr. 18. des")]:
        p.add(t(x2, yy + 5, lab, 15, "s", SEC), rect(x2 + 130, yy - 16, 190, 32, PAPER, HAIR, 4), t(x2 + 140, yy + 5, val, 15, "s", INK))
        yy += 46
    p.add(t(x2, yy + 26, "Labtimer, Datalab A2", 22, "r", INK, 700))
    yy += 56
    for val in ["to. 26. nov 14:15", "ma. 30. nov 10:15", "to. 3. des 14:15", "ma. 7. des 10:15"]:
        p.add(t(x2, yy, val, 15, "s", INK), line(x2, yy + 11, x2 + 400, yy + 11, GRID, 1), t(x2 + 400, yy, "Fjern", 14, "s", SEC, a="end"))
        yy += 38
    p.add(t(x2, yy + 8, "Legg til Labtime", 15, "s", INK, 500), line(x2, yy + 12, x2 + tw("Legg til Labtime", 15), yy + 12, HAIR, 1))
    # Fordeling
    x3 = 980
    p.add(t(x3, 146, "Fordeling", 22, "r", INK, 700))
    p.add(para(x3, 174, "240 studenter fordeles tilfeldig i 60 spill à 4. Hver gruppe på fire seter er ett spill.", 400, 15, 21, c=SEC))
    cols = 10
    cw, chh = 40, 60
    sx0 = x3
    yy0 = 226
    for n in range(60):
        cx = sx0 + (n % cols) * cw
        cy = yy0 + (n // cols) * chh
        p.add(t(cx, cy, n + 1, 12, "s", MUT, num=True))
        for k in range(4):
            p.add(rect(cx + k * 7.6, cy + 6, 6, 30, "#8EA2BD"))
    yy = yy0 + 6 * chh + 10
    for r, (lab) in enumerate(["Spill 17: Ida (Detaljist), Sara (Grossist),", "Mikkel (Distributør), Jonas (Fabrikk)"]):
        p.add(t(x3, yy + r * 20, lab, 14, "s", SEC))
    yy += 54
    p.add(button(x3, yy, 190, 46, "Kjør fordeling på nytt", False, 15))
    p.add(button(x3 + 200, yy, 200, 46, "Bekreft fordelingen", True, 15))
    p.add(para(x3, yy + 70, "Fordelingen er ikke låst før du bekrefter. Tomme seter fylles av KI-spillere og merkes.", 400, 14, 19, c=SEC))
    p.save()


# ---------- student ----------
def build_student():
    p = Page("04-student-hjem", "student", 1000, 900, "Kurve: student på mobil", "To telefoner: registrering fra Invitasjon og hjem under spill for Sara.")
    p.add(t(70, 30, "Registrering", 16, "s", SEC), t(540, 30, "Hjem under spill", 16, "s", SEC), demodata(930, 30, "end", 14))
    r = [t(22, 66, "Kurve", 24, "r", INK, 700)]
    r.append(t(22, 124, "Du er invitert", 32, "r", INK, 700))
    r.append(para(22, 158, "Bård har invitert deg til Klassen class-of-1994 i IBE160. Invitasjonen er gyldig i 14 dager.", 346, 16, 23, c=SEC))
    r.append(field(22, 252, 346, 48, "Navn", "Sara Lunde", 16))
    r.append(field(22, 332, 346, 48, "E-post, fra klasselista", "sara.lunde@stud.no", 16, True))
    r.append(field(22, 412, 346, 48, "Passord", "Minst 10 tegn", 16, True))
    r.append(button(22, 490, 346, 52, "Opprett konto", True, 17))
    r.append(line(22, 576, 368, 576, GRID, 1))
    r.append(t(22, 610, "Dette skjer videre", 20, "r", INK, 700))
    r.append(para(22, 638, "Du får et spill og en Rolle når faglæreren har fordelt klassen. Dere spiller på telefonen, over flere kvelder hvis dere vil. Tomme seter fylles av KI-spillere, og de er alltid merket.", 346, 15, 22, c=SEC))
    p.add(phone(70, 44, "".join(r)))
    h = [t(22, 66, "Kurve", 24, "r", INK, 700), t(368, 64, "Sara", 15, "s", SEC, a="end")]
    h.append(t(22, 112, "Spill 17 · Grossist", 26, "r", INK, 700))
    h.append(t(22, 138, "Spillet venter på deg, Uke 11", 16, "s", INK, 700))
    i = 10
    h.append(t(22, 162, f"{G['restordre'][i]} i restordre · {kr(c_of(NG[i]))} kr denne uka", 15, "s", SEC))
    h.append(button(22, 178, 346, 50, "Legg inn ordre for Uke 11", True, 17))
    y0 = 262
    h.append(t(22, y0, "Setene", 18, "r", INK, 700))
    yy = y0 + 26
    for role, st, kind in [("Detaljist", "har bestilt", "ok"), ("Grossist", "venter på deg", "you"), ("Distributør", "har bestilt", "ok"), ("Fabrikk", "venter, 3 min", "wait")]:
        h.append(seat_row(22, yy, role, NAVN[role], st, kind))
        yy += 26
    yy += 8
    h.append(line(22, yy, 368, yy, GRID, 1))
    yy += 30
    h.append(t(22, yy, "Dine steg", 18, "r", INK, 700))
    yy += 24
    steps = [("Klassespill", "pågår, Spillfrist ti. 8. des"), ("Debrief", "Debrief-frist fr. 11. des"), ("Quiz", "etter Debrief"), ("Replay", "etter Quiz"), ("Individuell test", "Testfrist fr. 18. des"), ("Rapport", "PDF etter test")]
    for n, (st, nt) in enumerate(steps):
        h.append(circ(28, yy - 5, 4.5, INK) if n == 0 else circ(28, yy - 5, 4.5, PAPER, HAIR, 1.6))
        h.append(t(44, yy, st, 15, "s", INK, 700 if n == 0 else 400) + t(368, yy, nt, 14, "s", INK if n == 0 else SEC, a="end"))
        yy += 25
    yy -= 8
    h.append(line(22, yy, 368, yy, GRID, 1))
    yy += 30
    h.append(t(22, yy, "Neste frist", 15, "s", SEC) + t(368, yy, "Spillfrist ti. 8. des", 15, "s", INK, 700, "end"))
    yy += 12
    h.append(line(22, yy, 368, yy, GRID, 1))
    yy += 28
    h.append(t(22, yy, "Labtimer, Datalab A2", 15, "s", SEC))
    yy += 22
    h.append(t(22, yy, "to. 26. nov 14:15", 15, "s", INK) + t(368, yy, "ma. 30. nov 10:15", 15, "s", INK, a="end"))
    yy += 22
    h.append(t(22, yy, "to. 3. des 14:15", 15, "s", INK) + t(368, yy, "ma. 7. des 10:15", 15, "s", INK, a="end"))
    p.add(phone(540, 44, "".join(h)))
    p.save()


# ---------- kontaktark ----------
def box_rows(x, y, w, n, rh=12, sc=INK):
    o = []
    for k in range(n):
        o.append(rect(x, y + k * rh, w * (0.92 - 0.11 * (k % 3)), 4, "#CCD5E0"))
    return "".join(o)


def thumb(p, x, y, title, sub, draw, w=298, h=178):
    p.add(rect(x, y, w, h, PAPER, HAIR, 4))
    p.add(draw(x, y, w, h))
    p.add(t(x, y + h + 22, title, 16, "s", INK, 700))
    p.add(para(x, y + h + 41, sub, w, 13, 17, c=SEC))


def build_alle():
    p = Page("09-alle-sider", "alle", 2000, 1400, "Kurve: alle andre sider", "Kontaktark over øvrige sider, gruppert per rolle, med tittel og én linje.")
    p.add(t(50, 58, "Alle andre sider, gruppert etter rolle", 34, "r", INK, 700))
    p.add(demodata(1950, 58, "end", 14))

    def hdr(x, y, w, h, s):
        return t(x + 12, y + 24, s, 15, "r", INK, 700)

    def d_reg(x, y, w, h):
        return hdr(x, y, w, h, "Du er invitert") + rect(x + 12, y + 38, w - 24, 22, TINT, HAIR, 3) + rect(x + 12, y + 70, w - 24, 22, TINT, HAIR, 3) + rect(x + 12, y + 110, w - 24, 26, INK, None, 3) + t(x + w / 2, y + 128, "Opprett konto", 12, "s", PAPER, 700, "middle")

    def d_login(x, y, w, h):
        return hdr(x, y, w, h, "Logg inn") + rect(x + 12, y + 38, w - 24, 22, TINT, HAIR, 3) + rect(x + 12, y + 70, w - 24, 22, TINT, HAIR, 3) + rect(x + 12, y + 110, w - 24, 26, INK, None, 3) + t(x + w / 2, y + 128, "Logg inn", 12, "s", PAPER, 700, "middle")

    def d_regler(x, y, w, h):
        v = V(x + 110, y + 34, w - 124, 110)
        return hdr(x, y, w, h, "Slik regnes uka") + v.frame(fs=11, ticks=(0,), ygrid=(), arm=2, axis="", ytitle="", ylab=False) + para(x + 12, y + 54, "Ett heltall i uka. Restordre 1,00. Lager 0,50.", 92, 12, 15, c=SEC)

    def d_start(x, y, w, h):
        v = V(x + 12, y + 38, w - 24, 104)
        return hdr(x, y, w, h, "Plasser punktet: netto lager −6") + v.frame(fs=11, ticks=(-40, 0, 40), ygrid=(), arm=2, axis="", ytitle="", ylab=False) + v.nowpt(-6, 5)

    R = REPLAY["serier"]["Grossist"]
    nr = nets(R)

    def d_replay(x, y, w, h):
        v = V(x + 12, y + 38, w - 24, 104)
        return hdr(x, y, w, h, "Replay, Uke 14") + v.frame(fs=11, ticks=(-40, 0, 40), ygrid=(), arm=2, axis="", ytitle="", ylab=False) + v.trail(nr, 14) + v.nowpt(nr[13], 5) + v.ring_on_axis(posisjon(R, 14), "Posisjon", INK, 12, 62)

    def d_replay_g(x, y, w, h):
        ts = TS(x + 12, y + 40, w - 24, 104, 1, 33, 0, 260)
        return hdr(x, y, w, h, f"Replay: {kr(REPLAY['kost_per_rolle']['Grossist'])} kr") + cum_stack(ts, R) + line(x + 12, ts.sy(0), x + w - 12, ts.sy(0), HAIR, 1) + t(x + 12, y + h - 12, "Ikke like for like med Klassespillet", 12, "s", SEC)

    def d_test1(x, y, w, h):
        o = hdr(x, y, w, h, "Hva koster uka ved −8?")
        for k, s in enumerate(["4,00 kr", "8,00 kr", "12,00 kr"]):
            o += rect(x + 12, y + 40 + k * 32, w - 24, 26, PAPER, INK if k == 1 else HAIR, 3, 1.4 if k == 1 else 1) + t(x + 22, y + 58 + k * 32, s, 12, "s", INK)
        return o

    def d_test2(x, y, w, h):
        v = V(x + 12, y + 38, 160, 104)
        o = hdr(x, y, w, h, "Tegn V-en, fyll inn tabellen") + v.frame(fs=11, ticks=(0,), ygrid=(), arm=2, axis="", ytitle="", ylab=False)
        for k, val in enumerate([-20, -5, 10]):
            o += t(x + 186, y + 58 + k * 26, f"{sgn(val)}: ___", 12, "s", INK)
        return o

    def d_test3(x, y, w, h):
        return hdr(x, y, w, h, "Forklar svingningen i din kjede") + rect(x + 12, y + 38, w - 24, 120, TINT, HAIR, 3) + box_rows(x + 22, y + 50, w - 44, 7)

    def d_ki(x, y, w, h):
        return hdr(x, y, w, h, "KI-vurdering") + t(x + 12, y + 44, "Teller ikke og er ikke en karakter", 12, "s", INK, 700) + box_rows(x + 12, y + 58, w - 24, 8) + t(x + 12, y + h - 10, "KI-generert, kan ta feil", 12, "s", SEC)

    def d_rapport(x, y, w, h):
        ts = TS(x + 110, y + 40, w - 124, 100, 1, 36, 0, 600)
        return hdr(x, y, w, h, "Studentrapport (PDF)") + box_rows(x + 12, y + 46, 86, 8) + cum_stack(ts, G) + line(x + 110, ts.sy(0), x + w - 14, ts.sy(0), HAIR, 1)

    def d_alle(x, y, w, h):
        o = hdr(x, y, w, h, "Alle spill side om side")
        for n, s in enumerate(KL["spill"][:24]):
            o += mini_net(x + 12 + (n % 6) * 46, y + 38 + (n // 6) * 32, 40, 26, s, sw=0.6)
        return o

    def d_lhjem(x, y, w, h):
        o = hdr(x, y, w, h, "class-of-1994") + t(x + 12, y + 46, "Klasseøkt pågår. 19 spill ikke ferdige.", 12, "s", SEC)
        for k, s in enumerate(["Oversikt", "Klasserapport", "Meldinger", "Lærers testspill"]):
            o += t(x + 12, y + 72 + k * 22, s, 13, "s", INK, 500) + line(x + 12, y + 78 + k * 22, x + w - 12, y + 78 + k * 22, GRID, 1)
        return o

    def d_krapport(x, y, w, h):
        els, sx, base = dot_plot(x + 12, y + 34, w - 24, 110, KL["spill"], 11, False)
        o = hdr(x, y, w, h, "Klasserapport") + "".join(els)
        for s, xx, yy in swarm([(s, s["kjedekost"]) for s in KL["spill"] if s["status"] == "ferdig"], sx, 2.4, base - 1, 5.2):
            o += circ(xx, yy, 2.3, INK)
        return o

    def d_innsikt(x, y, w, h):
        ts = TS(x + 12, y + 44, w - 24, 100, 1, 36, 0, 32)
        o = hdr(x, y, w, h, "Spillinnsikt: Spill 17, uke for uke")
        for r in ROLLER:
            o += poly([(ts.sx(i + 1), ts.sy(v)) for i, v in enumerate(S17[r]["ordre"])], ROLLE_TONE[r], 1.2)
        o += line(ts.sx(11), ts.y, ts.sx(11), ts.y + ts.h, INK, 1) + t(ts.sx(11) + 4, ts.y + 10, "Uke 11", 11, "s", INK, 700)
        return o

    def d_student(x, y, w, h):
        v = V(x + 12, y + 38, 140, 104)
        return hdr(x, y, w, h, "Sara, Grossist, Spill 17") + v.frame(fs=11, ticks=(0,), ygrid=(), arm=1.6, axis="", ytitle="", ylab=False) + v.allpts(NG, 2, INK, 0.5) + box_rows(x + 166, y + 44, 120, 8)

    def d_plenum(x, y, w, h):
        o = rect(x, y, w, h, INK, None, 4) + t(x + 12, y + 24, "Alle spill i plenum", 15, "r", PAPER, 700)
        for n, s in enumerate(KL["spill"][:40]):
            sxx = x + 12 + (n % 8) * 34.5
            syy = y + 38 + (n // 8) * 26
            mid = syy + 10
            pts = [(sxx + i / 35 * 30, mid - max(-YR_KL, min(YR_KL, v)) / YR_KL * 10) for i, v in enumerate(s["netto_lager"]["Fabrikk"])]
            o += poly(pts, "#BCCADC", 0.7)
        return o

    def d_tverr(x, y, w, h):
        F = KL["ferdige"]["kjedekost"]
        fj = KL["fjoraaret"]
        sx = lambda v: x + 16 + v / 3800 * (w - 32)
        return (
            hdr(x, y, w, h, "Tverrklasse-statistikk")
            + t(x + 12, y + 62, "class-of-1993", 12, "s", SEC) + line(x + 16, y + 74, x + w - 16, y + 74, GRID, 1) + circ(sx(fj["median_kjedekost"]), y + 74, 4, PAPER, INK, 1.6)
            + t(sx(fj["median_kjedekost"]) + 8, y + 70, kr(fj["median_kjedekost"], 0), 12, "s", INK, num=True)
            + t(x + 12, y + 110, "class-of-1994", 12, "s", SEC) + line(x + 16, y + 122, x + w - 16, y + 122, GRID, 1) + rect(sx(F["q1"]), y + 118, sx(F["q3"]) - sx(F["q1"]), 8, "#9DB0C9") + circ(sx(F["median"]), y + 122, 4, INK)
            + t(sx(F["median"]) + 8, y + 112, kr(F["median"], 0), 12, "s", INK, num=True)
        )

    def d_meld(x, y, w, h):
        o = hdr(x, y, w, h, "Meldinger")
        for k, s in enumerate(["Til alle: Spillfrist 8. des", "Til Noah (Spill 2): uka venter", "Til Spill 21: vi fortsetter kl. 19"]):
            o += t(x + 12, y + 56 + k * 28, s, 12, "s", INK) + line(x + 12, y + 64 + k * 28, x + w - 12, y + 64 + k * 28, GRID, 1)
        return o

    def d_test(x, y, w, h):
        v = V(x + 12, y + 38, w - 24, 100)
        return hdr(x, y, w, h, "Lærers testspill") + t(x + w - 12, y + 24, "3 KI-spillere", 12, "s", SEC, a="end") + v.frame(fs=11, ticks=(0,), ygrid=(), arm=2, axis="", ytitle="", ylab=False) + v.trail(NG, 8) + v.nowpt(NG[7], 5)

    def d_admin(x, y, w, h):
        o = hdr(x, y, w, h, "Admin-område")
        for k, s in enumerate(["Institusjoner og klasser", "Brukere og roller", "KI-kostnad", "Driftslogg"]):
            o += t(x + 12, y + 56 + k * 26, s, 13, "s", INK) + line(x + 12, y + 64 + k * 26, x + w - 12, y + 64 + k * 26, GRID, 1)
        return o

    def d_brukere(x, y, w, h):
        o = hdr(x, y, w, h, "Brukere og roller")
        for k, (a, b) in enumerate([("Bård", "Faglærer"), ("Assistent", "Hjelpelærer"), ("Sara", "Student"), ("Admin", "Admin")]):
            o += t(x + 12, y + 56 + k * 26, a, 13, "s", INK) + t(x + w - 12, y + 56 + k * 26, b, 13, "s", SEC, a="end") + line(x + 12, y + 64 + k * 26, x + w - 12, y + 64 + k * 26, GRID, 1)
        return o

    def d_kikost(x, y, w, h):
        o = hdr(x, y, w, h, "KI-kostnad per Klasse")
        for k, (a, sh) in enumerate([("KI-spillere", 0.72), ("Debrief-tekst", 0.45), ("KI-vurdering", 0.2)]):
            o += t(x + 12, y + 58 + k * 36, a, 12, "s", INK) + rect(x + 12, y + 64 + k * 36, (w - 24) * sh, 10, "#8EA2BD")
        return o

    groups = [
        ("Student", 110, [
            ("Invitasjon og registrering", "Fra e-post til konto, navn hentes fra klasselista.", d_reg),
            ("Logg inn", "E-post og passord. Ingen offentlig registrering.", d_login),
            ("Regler før første ordre", "V-en forklart med to tall: 1,00 og 0,50.", d_regler),
            ("Startoppgave", "Plasser et punkt på V-en og les av kostnaden.", d_start),
            ("Replay", "Posisjon på aksen er låst opp. Tilfeldig etterspørsel.", d_replay),
            ("Replay-gjennomgang", "Kostnad over tid, merket ikke like for like.", d_replay_g),
            ("Individuell test: flervalg", "Regnestykker fra V-en, ikke bare mønstre.", d_test1),
            ("Individuell test: tegne og tabell", "Tegn V-en, regn ut uker fra tabell.", d_test2),
            ("Individuell test: langsvar", "Forklar med egne tall og med struktur.", d_test3),
            ("KI-vurdering", "Formativ, teller ikke, aldri en karakter.", d_ki),
            ("Studentrapport (PDF)", "Kostnad over tid og din Forklaring.", d_rapport),
            ("Alle spill side om side", "Klassens netto lager, uten navn eller rangering.", d_alle),
        ]),
        ("Faglærer", 730, [
            ("Lærerhjem", "Klasser, gjeldende Klasseøkt og neste frist.", d_lhjem),
            ("Klasserapport", "Fordeling av kjedekostnad, trakt og mønstre.", d_krapport),
            ("Spillinnsikt (uke for uke)", "Alle Roller i ett spill, med Uke-valg.", d_innsikt),
            ("Studentside", "Ett sete: V-en, Forklaring, quiz, test.", d_student),
            ("Alle spill i plenum", "Mørk visning for projektor. Ingen navn.", d_plenum),
            ("Tverrklasse-statistikk", "Kjedekostnad år mot år.", d_tverr),
            ("Meldinger", "Til alle, et spill eller en student.", d_meld),
            ("Lærers testspill", "Prøv selv med tre KI-spillere.", d_test),
        ]),
    ]
    cw, gx = 298, 22
    cols = 6
    x0 = 50
    rowh = 300
    for name, y0, items in groups:
        p.add(t(50, y0, name, 24, "r", INK, 700))
        for n, (title, sub, dr) in enumerate(items):
            x = x0 + (n % cols) * (cw + gx)
            y = y0 + 14 + (n // cols) * rowh
            thumb(p, x, y, title, sub, dr)
    # Admin ved siden av Faglærer siste rad
    p.add(t(50 + 2 * (cw + gx), 730 + rowh, "Admin", 24, "r", INK, 700))
    adm = [("Admin-område", "Inngang for driftsansvarlig.", d_admin), ("Brukere og roller", "Hvem er hva, per institusjon.", d_brukere), ("KI-kostnad", "Forbruk per Klasse og type.", d_kikost)]
    for n, (title, sub, dr) in enumerate(adm):
        x = x0 + (n + 2) * (cw + gx)
        y = 730 + 14 + rowh
        thumb(p, x, y, title, sub, dr)
    p.save()


if __name__ == "__main__":
    build_ped()
    build_spill()
    build_dyn()
    build_debrief()
    build_oversikt()
    build_landing()
    build_klasse()
    build_oppsett()
    build_student()
    build_alle()
    print("ok")
