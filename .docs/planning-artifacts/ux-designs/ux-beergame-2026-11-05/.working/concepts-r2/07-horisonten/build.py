"""Bygger konsept 07 Horisonten. Alle grafer tegnes fra ../_shared/fixture.json.

Kjør: uv run python build.py
Grammatikk: en stripe er ett horisontbånd. Én tone = 40 enheter overalt i produktet.
Over null står på gulvet, under null henger fra taket, og hver hele 40 starter neste tone.
"""
import json
import random
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
FX = json.loads((HERE.parent / "_shared" / "fixture.json").read_text(encoding="utf-8"))

# ---------- palett ----------
CANVAS = "#192025"
BG = "#1F272C"
PANEL = "#232C32"
WELL = "#2A343A"
HAIR = "#3D4A52"
INK = "#EAEFEE"
SEC = "#B7C3C5"
MUT = "#98A7AA"
TEAL = ["#3A928C", "#56B8AC", "#9FE0D3", "#DDF5EF"]
COPPER = ["#B26E3E", "#D08B4B", "#F0B982", "#FBE3C9"]
NEU = ["#6D7E88", "#93A3AC", "#BAC6CC", "#E2E8EA"]
BAR = "#5A6A73"
SIGNAL = "#EFD66B"
BAND = 40
FONT = "Commissioner"
ROLES = ["Detaljist", "Grossist", "Distributør", "Fabrikk"]

# ---------- data ----------
S17 = FX["spill17"]
SER = S17["serier"]
G = SER["Grossist"]
SIM1 = FX["bare_sara_teller_paa_vei"]
SIM2 = FX["alle_teller_paa_vei"]
REP = FX["replay_sara"]
KL = FX["klasse"]
SPILL = KL["spill"]


def net(s):
    return [a - b for a, b in zip(s["lager"], s["restordre"])]


GNET = net(G)
GPOS = [a - b + c for a, b, c in zip(G["lager"], G["restordre"], G["paa_vei"])]
GSENDT = [(G["lager"][i - 1] if i else 12) + G["levering"][i] - G["lager"][i] for i in range(36)]
assert GNET[10] == -13 and GPOS[10] == 3 and G["paa_vei"][10] == 16 and G["ordre"][10] == 24
assert G["kost_sum"][10] == 68.0 and GSENDT[10] == 4 and G["levering"][10] == 4
assert all(GNET[i] == GNET[i - 1] + G["levering"][i] - G["innkommende_ordre"][i] for i in range(1, 36))
assert abs(sum(G["restordre"]) + 0.5 * sum(G["lager"]) - 553.5) < 1e-6
assert sum(G["levering"][11:14]) == 16


def nb(x, dec=2):
    s = f"{x:,.{dec}f}".replace(",", " ").replace(".", ",")
    return s.replace("-", "−")


def sgn(v):
    return ("−" + str(abs(v))) if v < 0 else str(v)


def x_(v):
    return f"{v:.1f}".replace(",", ".") + "×" if False else f"{v:.1f}".replace(".", ",") + "×"


# ---------- SVG-hjelpere ----------
def esc(s):
    return escape(str(s), quote=False)


def T(x, y, s, size=14, w=400, c=INK, a="start", num=False, extra=""):
    anchor = "" if a == "start" else f' text-anchor="{a}"'
    cls = "d07-n" if num else "d07-t"
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{w}" fill="{c}" class="{cls}"{anchor}{extra}>{esc(s)}</text>'


def wrap(s, width, size, k=0.485):
    maxc = max(4, int(width / (size * k)))
    lines, cur = [], ""
    for word in s.split(" "):
        if len(cur) + len(word) + (1 if cur else 0) > maxc and cur:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}" if cur else word
    if cur:
        lines.append(cur)
    return lines


def P(x, y, s, width, size=14, lh=None, c=SEC, w=400, a="start"):
    """Returnerer (svg, y etter siste linje)."""
    lh = lh or round(size * 1.42)
    out = []
    for i, line in enumerate(wrap(s, width, size)):
        out.append(T(x, y + i * lh, line, size, w, c, a))
    return "".join(out), y + len(wrap(s, width, size)) * lh


def R(x, y, w, h, fill="none", rx=0, stroke=None, sw=1, extra=""):
    st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    r = f' rx="{rx}"' if rx else ""
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}"{r}{st}{extra}/>'


def L(x1, y1, x2, y2, c=HAIR, sw=1, extra=""):
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{c}" stroke-width="{sw}"{extra}/>'


def G_(x, y, s=1, inner=""):
    sc = f" scale({s})" if s != 1 else ""
    return f'<g transform="translate({x} {y}){sc}">{inner}</g>'


def doc(name, W, H, title, desc, body, bg=CANVAS):
    style = (
        "@import url('https://fonts.googleapis.com/css2?family=Commissioner:wght@300..700&amp;display=swap');"
        f".d07-t{{font-family:'{FONT}','Segoe UI',system-ui,sans-serif}}"
        f".d07-n{{font-family:'{FONT}','Segoe UI',system-ui,sans-serif;font-variant-numeric:tabular-nums lining-nums;font-feature-settings:'tnum' 1,'lnum' 1}}"
    )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="{FONT}, \'Segoe UI\', system-ui, sans-serif">'
        f"<title>{esc(title)}</title><desc>{esc(desc)}</desc><style>{style}</style>"
        f'<rect x="0" y="0" width="{W}" height="{H}" fill="{bg}"/>{body}</svg>'
    )
    (HERE / f"{name}.svg").write_text(svg, encoding="utf-8")


# ---------- horisontstripe ----------
def _band_path(xs, vals, y, h, sign, k, band):
    lo, hi = k * band, (k + 1) * band

    def u(v):
        return max(0.0, min(band, sign * v - lo)) / band * h

    pts = []
    for i, v in enumerate(vals):
        pts.append((xs[i], u(v)))
        if i < len(vals) - 1:
            a, b = sign * v, sign * vals[i + 1]
            knots = []
            for th in (lo, hi):
                if (a - th) * (b - th) < 0:
                    knots.append((th - a) / (b - a))
            for t in sorted(knots):
                pts.append((xs[i] + t * (xs[i + 1] - xs[i]), u(v + t * (vals[i + 1] - v))))
    if max(p[1] for p in pts) <= 0:
        return ""
    base = y + h if sign > 0 else y
    d = [f"M{pts[0][0]:.1f} {base:.1f}"]
    for px, pu in pts:
        d.append(f"L{px:.1f} {base - pu if sign > 0 else base + pu:.1f}")
    d.append(f"L{pts[-1][0]:.1f} {base:.1f}Z")
    return "".join(d)


def hz(x, y, w, h, vals, span=None, ramp="duo", well=True, band=BAND, well_full=False):
    """Én stripe. span = antall uker bredden w dekker; vals kan være kortere."""
    vals = list(vals)
    span = span or len(vals)
    step = w / max(1, span - 1)
    if len(vals) == 1:
        vals = vals * 2
        xs = [x, x + min(step, 3)]
    else:
        xs = [x + i * step for i in range(len(vals))]
    out = []
    if well:
        ww = w if well_full else (xs[-1] - x)
        out.append(R(x, y, ww, h, WELL))
    pos = TEAL if ramp == "duo" else NEU
    for k in range(4):
        d = _band_path(xs, vals, y, h, 1, k, band)
        if d:
            out.append(f'<path d="{d}" fill="{pos[k]}"/>')
    if ramp == "duo":
        for k in range(4):
            d = _band_path(xs, vals, y, h, -1, k, band)
            if d:
                out.append(f'<path d="{d}" fill="{COPPER[k]}"/>')
    return "".join(out)


def axis(x, y, w, span, ticks, now=None, size=13, c=MUT, prefix="Uke "):
    out = []
    step = w / max(1, span - 1)
    for i, t in enumerate(ticks):
        label = f"{prefix}{t}" if i == 0 else str(t)
        anchor = "start" if t == 1 else "middle"
        out.append(T(x + (t - 1) * step, y, label, size, 400, c, anchor, num=True))
    if now:
        out.append(T(x + (now - 1) * step, y, "nå", size, 600, INK, "end"))
    return "".join(out)


def key(x, y, size=13, sw=26, sh=14, ticks=True):
    """Lesenøkkel: fire toner over og under null."""
    out = []
    for i in range(4):
        out.append(R(x + 110 + i * (sw + 2), y - 11, sw, sh, TEAL[i]))
        out.append(R(x + 110 + i * (sw + 2), y + 11, sw, sh, COPPER[i]))
    out.append(T(x, y + 1, "Over null", size, 400, SEC))
    out.append(T(x, y + 23, "Under null", size, 400, SEC))
    for i, lab in enumerate(["40", "80", "120", "160"] if ticks else []):
        out.append(T(x + 110 + (i + 1) * (sw + 2) - 3, y + 44, lab, 12, 400, MUT, "end", num=True))
    return "".join(out)


def btn(x, y, w, h, label, primary=True, size=15):
    if primary:
        return R(x, y, w, h, INK, 6) + T(x + w / 2, y + h / 2 + size * 0.36, label, size, 600, BG, "middle")
    return R(x, y, w, h, "none", 6, HAIR) + T(x + w / 2, y + h / 2 + size * 0.36, label, size, 500, INK, "middle")


def phone(x, y, s, inner):
    return G_(x, y, s, R(0, 0, 390, 844, BG, 26, HAIR, 1.2) + inner)


def demo(x, y, a="start", size=13):
    return T(x, y, "Demodata", size, 400, MUT, a)


def title(x, y, s, sub=None, width=1100, size=28):
    out = T(x, y, s, size, 400, INK)
    if sub:
        p, _ = P(x, y + 28, sub, width, 15, c=SEC)
        out += p
    return out


# ---------- Saras fire striper ----------
def strip_vals(n, pending=False):
    """Hva Sara ser i Uke n. Egen ordre for uke n finnes først etter bekreftelse."""
    o = G["ordre"][: n - 1] if pending else G["ordre"][:n]
    return {
        "Netto lager": GNET[:n],
        "Ordre inn": G["innkommende_ordre"][:n],
        "Egen ordre": o,
        "På vei": G["paa_vei"][:n],
    }


def netto_label(n):
    v = GNET[n - 1]
    return f"Restordre {-v}" if v < 0 else f"Lager {v}"


def sara_strips(n, x, y, w, h, step, typed=None, open_week=True, tsize=14, vsize=15, pv_add=None):
    vals = strip_vals(n, pending=open_week)
    out = []
    labels = {
        "Netto lager": netto_label(n),
        "Ordre inn": str(G["innkommende_ordre"][n - 1]),
        "Egen ordre": (f"{typed} tastet" if typed else (str(G["ordre"][n - 1]) if not open_week else f"{G['ordre'][n - 2]} i Uke {n - 1}")),
        "På vei": (f"{G['paa_vei'][n - 1]} + {typed or pv_add} = {G['paa_vei'][n - 1] + (typed or pv_add)}" if (typed or pv_add) else str(G["paa_vei"][n - 1])),
    }
    stepx = w / max(1, n - 1)
    for i, (name, v) in enumerate(vals.items()):
        yy = y + i * step
        out.append(T(x, yy - 7, name, tsize, 400, SEC))
        out.append(T(x + w - 6, yy - 7, labels[name], vsize, 500, INK, "end", num=True))
        out.append(R(x, yy, w, h, WELL))
        out.append(hz(x, yy, w, h, v, span=n, ramp="duo" if i == 0 else "neu", well=False))
        if typed and name == "Egen ordre":
            x0, x1 = x + (n - 2) * stepx, x + (n - 1) * stepx
            v0 = G["ordre"][n - 2]
            y0 = yy + h - v0 / BAND * h
            y1 = yy + h - typed / BAND * h
            out.append(f'<path d="M{x0:.1f} {y0:.1f}L{x1:.1f} {y1:.1f}L{x1:.1f} {yy + h:.1f}" fill="none" stroke="{INK}" stroke-width="1.6"/>')
        if (typed or pv_add) and name == "På vei":
            pv = G["paa_vei"][n - 1]
            y0 = yy + h - pv / BAND * h
            y1 = yy + h - min(BAND, pv + (typed or pv_add)) / BAND * h
            out.append(R(x + w - 4, y1, 4, y0 - y1, INK))
    # felles nå-linje
    out.append(L(x + w, y - 2, x + w, y + 3 * step + h + 4, INK, 1))
    return "".join(out)


def ticks_for(n):
    base = [1, 5, 10, 15, 20, 25, 30, 35]
    return [t for t in base if t <= n - 2 or (t == 1)]


# ---------- 05 Hovedskjermen ----------
def phone_header(n, right1="Grossist · Sara"):
    out = T(20, 48, f"Uke {n}", 30, 400, INK)
    out += T(370, 40, right1, 14, 400, SEC, "end")
    out += T(370, 60, f"Totalkostnad {nb(G['kost_sum'][n - 1])} kr", 14, 400, SEC, "end", num=True)
    return out


def phone_main():
    n = 11
    out = phone_header(n)
    out += sara_strips(n, 20, 106, 350, 62, 88, typed=24)
    out += axis(20, 106 + 3 * 88 + 62 + 22, 350, n, ticks_for(n), now=n)
    y = 490
    out += L(20, y, 370, y)
    out += T(20, y + 34, "Din ordre, Uke 11", 15, 400, SEC)
    out += R(20, y + 48, 350, 66, WELL, 6)
    out += T(195, y + 94, "24", 38, 500, INK, "middle")
    for xx in (42, 348):
        out += L(xx - 8, y + 81, xx + 8, y + 81, SEC, 1.5)
    out += L(348, y + 73, 348, y + 89, SEC, 1.5)
    out += T(20, y + 144, "Posisjon med 24", 14, 400, SEC)
    out += T(370, y + 144, "0 − 13 + 16 + 24 = 27", 15, 500, INK, "end", num=True)
    out += btn(20, y + 162, 350, 54, "Bekreft ordre 24")
    out += T(195, y + 240, "Kan ikke endres etter bekreftelse", 13, 400, MUT, "middle")
    out += T(20, y + 288, "Se tallene for Uke 11", 15, 500, INK)
    out += L(20, y + 293, 168, y + 293, INK, 1)
    out += T(370, y + 288, "Venter på: Jonas, deg", 14, 400, SEC, "end")
    out += demo(20, y + 330)
    return out


def detail_panel(px, py, w=310, h=844):
    n = 11
    x, r = 22, w - 22
    out = R(0, 0, w, h, PANEL, 14, HAIR)
    out += T(x, 42, "Uke 11 i tall", 21, 400, INK)
    rows = [
        ("Lager", G["lager"][10]),
        ("Restordre", G["restordre"][10]),
        ("Ordre inn", G["innkommende_ordre"][10]),
        ("Levering", G["levering"][10]),
        ("Sendt", GSENDT[10]),
        ("På vei", G["paa_vei"][10]),
        ("Neste levering", G["levering"][11]),
        ("Totalkostnad", nb(G["kost_sum"][10]) + " kr"),
    ]
    y = 74
    for k, v in rows:
        out += T(x, y, k, 14, 400, SEC) + T(r, y, v, 14, 500, INK, "end", num=True)
        y += 25
    y += 6
    out += L(x, y - 12, r, y - 12)
    out += T(x, y + 10, "Slik ble −13", 15, 500, INK)
    y += 34
    out += T(x, y, f"{GNET[9]} + {G['levering'][10]} − {G['innkommende_ordre'][10]} = {GNET[10]}".replace("-", "−"), 16, 500, INK, num=True)
    y += 21
    out += T(x, y, "Forrige uke + levering − ordre inn", 13, 400, SEC)
    y += 12
    sw = r - x
    out += T(x, y + 15, "Levering", 13, 400, SEC)
    out += hz(x + 70, y + 2, sw - 70, 34, G["levering"][:n], span=n, ramp="neu")
    out += T(x, y + 56, "Ordre inn", 13, 400, SEC)
    out += hz(x + 70, y + 42, sw - 70, 34, G["innkommende_ordre"][:n], span=n, ramp="neu")
    y += 104
    out += L(x, y - 8, r, y - 8)
    out += T(x, y + 14, "Dette er på vei: 16", 15, 500, INK)
    y += 38
    for i in range(3):
        out += T(x, y, f"Uke {12 + i}", 14, 400, SEC, num=True) + T(r, y, G["levering"][11 + i], 14, 500, INK, "end", num=True)
        y += 22
    p, y = P(x, y + 2, "Ikke garantert: leverandøren kan mangle varer.", sw, 13, c=MUT)
    out += p
    y += 10
    out += L(x, y - 8, r, y - 8)
    out += T(x, y + 14, "Denne ukas kostnad", 15, 500, INK)
    y += 37
    out += T(x, y, "13 × 1,00 + 0 × 0,50 = 13,00", 15, 400, INK, num=True)
    y += 28
    out += T(x, y, "Egne ordre, Uke 1 til 10", 13, 400, SEC)
    y += 22
    cw = sw / 10
    for i in range(10):
        out += T(x + i * cw + cw / 2 - 3, y, G["ordre"][i], 14, 500, INK, "middle", num=True)
    return G_(px, py, 1, out)


def laptop():
    n = 11
    W, H = 730, 520
    out = R(0, 0, W, H, BG, 10, HAIR, 1.2)
    out += T(28, 46, "Uke 11", 30, 400, INK)
    out += T(136, 46, "Grossist · Sara", 15, 400, SEC)
    out += T(W - 28, 46, f"Totalkostnad {nb(G['kost_sum'][10])} kr", 15, 400, SEC, "end", num=True)
    out += sara_strips(n, 28, 96, 450, 58, 86, typed=24)
    out += axis(28, 96 + 3 * 86 + 58 + 22, 450, n, ticks_for(n), now=n)
    x = 510
    out += T(x, 90, "Din ordre, Uke 11", 14, 400, SEC)
    out += R(x, 100, 192, 62, WELL, 6)
    out += T(x + 96, 145, "24", 36, 500, INK, "middle")
    out += T(x, 192, "Posisjon med 24", 14, 400, SEC)
    out += T(x, 214, "0 − 13 + 16 + 24 = 27", 15, 500, INK, num=True)
    out += btn(x, 230, 192, 46, "Bekreft ordre 24", size=14)
    out += T(x, 296, "Kan ikke endres etterpå", 13, 400, MUT)
    out += L(x, 314, x + 192, 314)
    out += T(x, 338, "Venter på", 14, 500, INK)
    seats = [("Ida", "har bestilt"), ("Mikkel", "har bestilt"), ("Jonas", "3 min"), ("Sara", "deg")]
    for i, (a, b) in enumerate(seats):
        out += T(x, 362 + i * 22, a, 14, 400, SEC) + T(x + 192, 362 + i * 22, b, 14, 400, INK if b in ("3 min", "deg") else SEC, "end", num=True)
    out += T(x, 462, "Tallene for Uke 11", 14, 500, INK) + L(x, 467, x + 120, 467, INK, 1)
    out += demo(28, H - 22)
    return out


def build_05():
    b = title(60, 58, "Uke 11: fire striper, ett tall")
    b += phone(60, 90, 1, phone_main())
    b += T(480, 80, "Ett trykk unna", 14, 400, SEC)
    b += detail_panel(480, 90)
    b += T(830, 80, "Samme flate på laptop", 14, 400, SEC)
    b += G_(830, 90, 1, laptop())
    x, y = 830, 650
    b += T(x, y, "Lesemåten, ett blikk", 20, 400, INK)
    b += hz(x, y + 18, 340, 52, GNET[:18], span=18, ramp="duo")
    b += T(x, y + 90, "Lager står på gulvet. Restordre henger fra taket.", 14, 400, INK)
    p, _ = P(x, y + 112, "Formen sier retningen uten farge. Full stripe er 40 enheter. Over 40 begynner neste, lysere tone fra samme kant, og tallet til høyre står alltid som tall.", 345, 14)
    b += p
    b += key(x, y + 200)
    xx = x + 385
    b += T(xx, y, "Hva stripene gjør for neste ordre", 20, 400, INK)
    p, y2 = P(xx, y + 28, "Restordre 13 er stripa som roper. På vei 16 er stripa som avgjør. Når du taster, tegnes 24 inn i Egen ordre og På vei med hvit strek, slik at konsekvensen står i grafen før du bekrefter.", 345, 14)
    b += p
    p, _ = P(xx, y2 + 10, "Ingen anbefaling. Systemet regner ut Posisjon, du bestemmer. Stripa ender alltid i nå og viser aldri hvor mange uker som gjenstår.", 345, 14)
    b += p
    doc("05-spill", 1600, 1000, "Horisont: hovedskjermen i Uke 11",
        "Telefon med fire stablede horisontstriper og 24 tastet inn, åpnet detaljpanel, og laptop. Alle tall fra spill 17, Uke 11. Demodata.", b)


# ---------- 06 Spilldynamikk ----------
def frame_common(n, typed=None, open_week=True, h=64, step=90, y=100, pv_add=None):
    out = phone_header(n)
    out += sara_strips(n, 20, y, 350, h, step, typed=typed, open_week=open_week, pv_add=pv_add)
    out += axis(20, y + 3 * step + h + 20, 350, n, ticks_for(n), now=n)
    return out, y + 3 * step + h + 20


def frame_a():
    out, y = frame_common(11)
    y += 30
    out += L(20, y, 370, y)
    rows = [("Levering denne uka", G["levering"][10]), ("Sendt denne uka", GSENDT[10]), ("Neste levering", G["levering"][11])]
    yy = y + 32
    for a, b in rows:
        out += T(20, yy, a, 15, 400, SEC) + T(370, yy, b, 15, 500, INK, "end", num=True)
        yy += 28
    out += T(20, yy + 22, "Din ordre, Uke 11", 15, 400, SEC)
    out += R(20, yy + 36, 350, 62, WELL, 6)
    out += L(195, yy + 50, 195, yy + 84, INK, 1.5)
    out += R(20, yy + 112, 350, 52, "none", 6, HAIR)
    out += T(195, yy + 144, "Skriv inn ordre for å bekrefte", 14, 400, MUT, "middle")
    out += demo(20, 816)
    return out


def frame_b():
    out, y = frame_common(11, typed=24)
    y += 30
    out += L(20, y, 370, y)
    out += T(20, y + 30, "Din ordre, Uke 11", 15, 400, SEC)
    out += R(20, y + 42, 350, 66, WELL, 6)
    out += T(195, y + 88, "24", 38, 500, INK, "middle")
    out += T(20, y + 136, "Allerede på vei", 15, 400, SEC) + T(370, y + 136, "16", 15, 500, INK, "end", num=True)
    out += T(20, y + 164, "Posisjon med 24", 15, 400, SEC) + T(370, y + 164, "0 − 13 + 16 + 24 = 27", 15, 500, INK, "end", num=True)
    out += btn(20, y + 186, 350, 52, "Bekreft ordre 24")
    out += T(195, y + 262, "Kan ikke endres etter bekreftelse", 13, 400, MUT, "middle")
    out += demo(20, 816)
    return out


def frame_c():
    out, y = frame_common(11, open_week=False, pv_add=24)
    y += 30
    out += L(20, y, 370, y)
    out += T(20, y + 30, "Din ordre 24 er låst", 17, 500, INK)
    out += T(20, y + 58, "Venter på de andre", 15, 400, SEC)
    seats = [("Detaljist", "Ida", "har bestilt"), ("Grossist", "Sara, deg", "har bestilt"), ("Distributør", "Mikkel", "har bestilt"), ("Fabrikk", "Jonas", "venter, 3 min")]
    yy = y + 90
    for a, b, c in seats:
        active = "venter" in c
        out += T(20, yy, a, 14, 400, SEC) + T(110, yy, b, 15, 400, INK) + T(370, yy, c, 15, 500 if active else 400, INK if active else SEC, "end", num=True)
        yy += 30
    p, _ = P(20, yy + 12, "Uka går videre når alle har bestilt.", 350, 14, c=MUT)
    out += p
    out += demo(20, 816)
    return out


def frame_d():
    out, y = frame_common(12)
    y += 30
    out += L(20, y, 370, y)
    out += T(20, y + 30, "Dette skjedde", 17, 500, INK)
    rows = [
        ("Restordre", f"{G['restordre'][10]} → {G['restordre'][11]}"),
        ("Ordre inn", f"{G['innkommende_ordre'][10]} → {G['innkommende_ordre'][11]}"),
        ("Levering", f"{G['levering'][10]} → {G['levering'][11]}"),
        ("På vei", f"{G['paa_vei'][10]} → {G['paa_vei'][11]}"),
    ]
    yy = y + 62
    for a, b in rows:
        out += T(20, yy, a, 15, 400, SEC) + T(370, yy, b, 15, 500, INK, "end", num=True)
        yy += 28
    out += btn(20, yy + 6, 350, 48, "Hopp over", primary=False)
    out += demo(20, 816)
    return out


def frame_e():
    n = 19
    out, y = frame_common(n, h=46, step=66, y=98)
    y += 26
    out += L(20, y, 370, y)
    out += T(20, y + 28, "Pause, så KI-spiller", 17, 500, INK)
    p, yy = P(20, y + 52, "Jonas (Fabrikk) har ikke bestilt på 24 t. KI-spiller har overtatt setet, så gruppa kan spille videre.", 350, 14)
    out += p
    out += R(20, yy + 2, 350, 40, WELL, 6)
    out += T(34, yy + 27, "Fabrikk", 14, 400, SEC) + T(100, yy + 27, "Jonas", 15, 400, INK) + T(356, yy + 27, "KI-spiller", 14, 600, INK, "end")
    yy += 66
    out += L(20, yy - 8, 370, yy - 8)
    out += T(20, yy + 16, "Det Jonas ser", 14, 400, SEC)
    p, yy2 = P(20, yy + 40, "KI-spiller har setet ditt. Du kan ta over fra neste Uke.", 350, 14, c=INK)
    out += p
    out += btn(20, yy2 + 2, 350, 46, "Ta tilbake setet")
    out += demo(20, 824)
    return out


def frame_f():
    out = T(20, 48, "Spillet er slutt", 26, 400, INK)
    out += T(20, 74, "Uke 36", 14, 400, SEC)
    out += T(20, 128, "Kjeden", 15, 400, SEC)
    out += T(20, 176, f"{nb(S17['kjedekost'])} kr", 44, 400, INK)
    y = 212
    out += L(20, y, 370, y)
    yy = y + 32
    for r in ROLES:
        me = r == "Grossist"
        out += T(20, yy, r + (", deg" if me else ""), 15, 500 if me else 400, INK if me else SEC)
        out += T(370, yy, nb(S17["kost_per_rolle"][r]) + " kr", 15, 500 if me else 400, INK if me else SEC, "end", num=True)
        yy += 30
    yy += 12
    out += T(20, yy + 6, "Ditt netto lager, Uke 1 til 36", 15, 400, SEC)
    out += hz(20, yy + 18, 350, 62, GNET, span=36, ramp="duo")
    out += axis(20, yy + 100, 350, 36, [1, 10, 20, 30, 36], size=13)
    p, y3 = P(20, yy + 138, "Hvorfor svingte det? Det er det Debriefen handler om.", 350, 15, c=INK)
    out += p
    out += btn(20, y3 + 10, 350, 52, "Videre til Debrief")
    out += demo(20, 816)
    return out


def build_06():
    b = title(40, 60, "Én Uke, seks tilstander. Grafen er den samme gjennom alle")
    s = 0.82
    frames = [
        ("A  Uka åpner", "Ny kolonne i nå. Levering og Ordre inn er allerede regnet. Sara har ett felt å fylle.", frame_a),
        ("B  Beslutningen", "24 med 16 på vei. Hvit strek viser konsekvensen i stripene. Posisjon 3 blir 27. Ingen fasit.", frame_b),
        ("C  Bekreftet", "Ordren er låst. Skjermen viser hvem det venter på, med Rolle, navn og tid.", frame_c),
        ("D  Uka går videre", "Stripene vokser ett steg. Tallene bytter under 2 sek., og kan hoppes over.", frame_d),
        ("E  Jonas er borte", "Pause til 24 t, deretter KI-spiller, merket. Jonas kan ta tilbake setet.", frame_e),
        ("F  Spillet slutter", "Kjedens totalkostnad først, så per Rolle. Først her finnes en sluttuke.", frame_f),
    ]
    gap = (2100 - 80 - 6 * 390 * s) / 5
    for i, (h, note, f) in enumerate(frames):
        x = 40 + i * (390 * s + gap)
        b += T(x, 108, h, 16, 500, INK)
        b += phone(x, 122, s, f())
        p, _ = P(x, 122 + 844 * s + 26, note, 390 * s, 14)
        b += p
    y = 122 + 844 * s + 92
    b += L(40, y - 8, 2060, y - 8)
    text = (
        "Uke for uke lærer spilleren lesemåten uten en eneste forklaringsboks: i Veiledede uker er stripene nesten flate, og den første restordren henger fra taket der den ikke kan overses. "
        "Etter hvert blir det synlig at kobberstripa reagerer med en gang, mens På vei legger seg tone på tone lenge før noe av det er framme. "
        "Egen ordre og det som kommer inn står på samme tidsakse, fire uker forskjøvet, så det spilleren ser nå kommer av det spilleren gjorde før. "
        "Grafen sier aldri hva som er riktig. Den gjør bare det stille tallet like synlig som det høylytte."
    )
    p, _ = P(40, y + 26, text, 1180, 18, lh=28, c=INK)
    # samme stripe vokser: netto lager ved Uke 11, 19 og 36 på felles akse
    sx, sw, sy0 = 1330, 730, y + 10
    for i, n in enumerate((11, 19, 36)):
        yy = sy0 + i * 40
        b += T(sx - 12, yy + 22, f"Uke {n}", 14, 400, SEC, "end", num=True)
        b += hz(sx, yy, (n - 1) * sw / 35, 34, GNET[:n], span=n, ramp="duo")
        b += L(sx + (n - 1) * sw / 35, yy - 1, sx + (n - 1) * sw / 35, yy + 35, INK, 1)
        b += T(sx + (n - 1) * sw / 35 + (8 if n < 36 else -6), yy + 22, sgn(GNET[n - 1]), 14, 500, INK, "start" if n < 36 else "end", num=True)
    b += T(sx, sy0 + 3 * 40 + 14, "Netto lager i Saras spill: samme stripe, tre uker. Høyre kant er nå til spillet er slutt.", 13, 400, MUT)
    b += p
    doc("06-spilldynamikk", 2100, 1200, "Horisont: spilldynamikk i seks telefonruter",
        "Uka åpner, beslutningen, bekreftet, uka går videre, Jonas er borte med KI-spiller, og slutt med kjedens totalkostnad. Demodata.", b)


# ---------- 10 Pedagogikk ----------
def build_10():
    b = title(60, 62, "Fire striper, samme grammatikk: Saras spill ved Uke 5, 11, 18 og 29",
              "Hver rad er det Sara faktisk ser. Tidsaksen er felles, og høyre kant er alltid nå. Ved Uke 5 er det nesten ingenting å lese. Ved Uke 29 står hele svingningen der, i samme stripe, i samme skala.", 1500, 30)
    # venstre: lesemåten
    x, y, w = 60, 150, 410
    b += T(x, y, "Lesemåten, ett blikk", 21, 400, INK)
    p, yy = P(x, y + 26, "Fra vanlig graf til stripe, med Saras eget netto lager fram til Uke 29.", w, 14)
    b += p
    # vanlig graf
    n = 29
    vals = GNET[:n]
    top, bot = 30, -40
    ch = 150
    y0 = yy + 6
    sy = lambda v: y0 + (top - v) / (top - bot) * ch
    xs = [x + i * w / (n - 1) for i in range(n)]
    posd = "M" + " L".join(f"{xs[i]:.1f} {sy(max(0, v)):.1f}" for i, v in enumerate(vals)) + f" L{xs[-1]:.1f} {sy(0):.1f} L{xs[0]:.1f} {sy(0):.1f}Z"
    negd = "M" + " L".join(f"{xs[i]:.1f} {sy(min(0, v)):.1f}" for i, v in enumerate(vals)) + f" L{xs[-1]:.1f} {sy(0):.1f} L{xs[0]:.1f} {sy(0):.1f}Z"
    b += R(x, y0, w, ch, WELL)
    b += f'<path d="{posd}" fill="{TEAL[0]}"/><path d="{negd}" fill="{COPPER[0]}"/>'
    b += L(x, sy(0), x + w, sy(0), SEC, 1)
    b += T(x + 6, sy(0) - 5, "null", 13, 400, INK)
    b += T(x + w - 6, sy(30) + 15, "+30", 13, 400, INK, "end", num=True)
    b += T(x + 6, y0 + ch - 7, "−40", 13, 400, INK, "start", num=True)
    p, yy = P(x, y0 + ch + 22, "Vanlig graf: 150 px. Null midt i, mye tom plass.", w, 14)
    b += p
    # brett
    H2 = 40 / (top - bot) * ch
    y1 = yy + 2
    b += hz(x, y1, w, H2, vals, span=n, ramp="duo", band=BAND)
    p, yy = P(x, y1 + H2 + 22, "Brettet: det som var under null henger nå fra taket. Samme høyde per enhet.", w, 14)
    b += p
    y2 = yy + 2
    b += hz(x, y2, w, 40, vals, span=n, ramp="duo")
    p, yy = P(x, y2 + 40 + 22, "Stripe: 40 px er 40 enheter. Da får fire variabler plass der én graf var.", w, 14)
    b += p
    y3 = yy + 2
    b += T(x, y3 + 12, "På vei", 14, 400, SEC)
    b += hz(x, y3 + 20, w, 40, G["paa_vei"][:n], span=n, ramp="neu")
    i_max = max(range(n), key=lambda i: G["paa_vei"][i])
    b += T(x + i_max * w / (n - 1), y3 + 12, f"{G['paa_vei'][i_max]} i Uke {i_max + 1}", 14, 500, INK, "middle", num=True)
    p, yy = P(x, y3 + 60 + 22, "Over 40 begynner neste, lysere tone fra samme kant. To hele toner er 80. Tallet står alltid ved siden.", w, 14)
    b += p
    b += key(x, yy + 14)
    p, yy = P(x, yy + 80, "I Veiledede uker (1 til 4) står dette skrevet rett på stripa: «Lager 12: står på gulvet.» Det er hele opplæringen. Den første restordren forklarer resten.", w, 14, c=INK)
    b += p

    # midt: fire uker
    weeks = [
        (5, "P2 · P4  Stille, og du kan ikke se hvorfor det snart endrer seg",
         f"Netto lager {GNET[4]}, Ordre inn {G['innkommende_ordre'][4]}, På vei {G['paa_vei'][4]}. Ingen stripe har rørt seg.",
         "Neste ordre: Det du ser er ordrer fra neste ledd, ikke kundene. Stripene sier bare hva som kom til deg."),
        (11, "P1 · P3  Restordre roper, På vei er stille",
         f"Restordre {G['restordre'][10]} henger fra taket. På vei {G['paa_vei'][10]} står lavt i neutral tone. Posisjon = 0 − 13 + 16 = {GPOS[10]}.".replace("neutral", "nøytral"),
         f"Neste ordre: Kobberet endret seg med {GNET[9]} + {G['levering'][10]} − {G['innkommende_ordre'][10]} = {GNET[10]}, altså inn minus ut. Se på begge stripene før du taster. Sara tastet 24.".replace("-9", "−9").replace("-13", "−13")),
        (18, "P2 · P3 · P8  Du har bestilt, men det kommer senere",
         f"Restordre {G['restordre'][17]}, men På vei har lagt seg i tre toner: {G['paa_vei'][17]}. Posisjon = 0 − {G['restordre'][17]} + {G['paa_vei'][17]} = {GPOS[17]}. 24 bestilt i Uke 11 ble {G['levering'][14]} levert i Uke 15.",
         "Neste ordre: Hver restordre koster 1,00 i uka, dobbelt av lager. Men mer bestilling nå kommer først om fire uker, når dette allerede er framme."),
        (29, "P1 · P7  Stripa har snudd",
         f"Lager {G['lager'][28]}, Ordre inn {G['innkommende_ordre'][28]}, På vei {G['paa_vei'][28]}. Inn minus ut fra Uke 18: {sgn(GNET[17])} + {sum(G['levering'][18:29])} − {sum(G['innkommende_ordre'][18:29])} = {GNET[28]}.",
         f"Neste ordre: Sara bestiller {G['ordre'][28]}. Overskuddet kommer av ordrene i Uke 11 til 18, og nye bråkutt lager neste bølge oppstrøms. Rolig tilpasning og å telle på vei må til sammen."),
    ]
    sx, pxw = 620, 20.5
    block_h = 212
    yb = 170 - 12
    names = [("Netto lager", "P1 P8"), ("Ordre inn", "P4"), ("Egen ordre", "P2"), ("På vei", "P3")]
    for bi, (n, head, seen, ins) in enumerate(weeks):
        ytop = yb + bi * block_h
        b += T(520, ytop + 6, f"Uke {n}", 21, 400, INK)
        vals = strip_vals(n)
        sh, st = 30, 36
        for i, ((nm, pr), v) in enumerate(zip(names, vals.values())):
            yy = ytop + 20 + i * st
            b += T(520, yy + 14, nm, 13, 400, SEC)
            b += T(520, yy + 28, pr, 12, 400, MUT)
            b += hz(sx, yy, (n - 1) * pxw, sh, v, span=n, ramp="duo" if i == 0 else "neu")
            b += T(sx + (n - 1) * pxw + 8, yy + 21, sgn(v[-1]), 14, 500, INK, num=True)
        xn = sx + (n - 1) * pxw
        b += L(xn, ytop + 16, xn, ytop + 20 + 3 * st + sh + 4, INK, 1)
        yax = ytop + 20 + 3 * st + sh + 18
        for t in [1, 5, 10, 15, 20, 25]:
            if t < n - 1:
                b += T(sx + (t - 1) * pxw, yax, t, 13, 400, MUT, "start" if t == 1 else "middle", num=True)
        b += T(xn, yax, "nå", 13, 600, INK, "middle")
        # notat
        nx, nw = 1290, 650
        b += T(nx, ytop + 6, head, 16, 500, INK)
        p, y9 = P(nx, ytop + 32, seen, nw, 14)
        b += p
        p, _ = P(nx, y9 + 6, ins, nw, 14, c=INK)
        b += p
        if bi < 3:
            b += L(520, ytop + block_h - 18, 1940, ytop + block_h - 18)
    # P2-kobling på uke 18-blokken: bestilt uke 11, levert uke 15
    yt = yb + 2 * block_h
    x1 = sx + 10 * pxw
    x2 = sx + 14 * pxw
    ya = yt + 20 + 2 * 36 + 3
    b += f'<path d="M{x1:.1f} {ya + 8:.1f} V{ya:.1f} H{x2:.1f} V{ya + 8:.1f}" fill="none" stroke="{INK}" stroke-width="1"/>'
    b += T(x1 - 6, ya + 10, f"{G['ordre'][10]} bestilt, {G['levering'][14]} levert 4 uker etter", 12, 500, INK, "end", num=True)

    # bunn: etter Debriefen
    yB = 1040
    b += L(60, yB - 16, 1940, yB - 16, SEC, 1)
    b += T(60, yB + 14, "Låst opp etter Debriefen", 21, 400, INK)
    b += T(330, yB + 14, "Klassespillet viser bare dine egne fire. Alt under her åpnes først når Forklaringen er skrevet.", 14, 400, SEC)
    # P5
    px, py, pw = 60, yB + 54, 400
    b += T(px, py, "P5  Forsterkning og forskyvning", 16, 500, INK)
    b += T(px, py + 22, "Ordre per Rolle, spill 17", 14, 400, SEC)
    for i, r in enumerate(ROLES):
        yy = py + 34 + i * 40
        b += T(px, yy + 21, r, 13, 400, SEC)
        b += hz(px + 78, yy, pw - 130, 34, SER[r]["ordre"], span=36, ramp="neu")
        first = next(j for j, v in enumerate(SER[r]["ordre"]) if v > 8)
        fx = px + 78 + first * (pw - 130) / 35
        b += L(fx, yy - 2, fx, yy + 36, INK, 1)
        b += T(px + pw - 2, yy + 22, x_(S17["forsterkning"][r]), 14, 500, INK, "end", num=True)
    b += T(px, py + 34 + 4 * 40 + 8, "Strek: første uke med ordre over 8", 13, 400, MUT)
    # P6
    px = 500
    pw = 420
    b += T(px, py, "P6  Struktur gir atferd", 16, 500, INK)
    b += T(px, py + 22, "Grossist, netto lager, alle 60 spill", 14, 400, SEC)
    rows = class_rows()
    rh = 3.1
    for i, s in enumerate(rows):
        yy = py + 34 + i * rh
        vals = GNET if s["spill"] == 17 else s["netto_lager"]["Grossist"]
        b += hz(px, yy, pw, rh - 0.4, vals, span=36, ramp="duo", well=False)
    me = next(i for i, s in enumerate(rows) if s["spill"] == 17)
    b += L(px + pw + 3, py + 34 + me * rh - 1, px + pw + 3, py + 34 + (me + 1) * rh + 1, INK, 2)
    b += T(px + pw + 8, py + 34 + me * rh + 5, "Ditt", 12, 600, INK)
    # P7 / referanse
    px = 960
    pw = 480
    b += T(px, py, "P3 · P7  Mot simulert referanse", 16, 500, INK)
    b += T(px, py + 22, "Grossist, netto lager. Simulert, ikke fasit", 14, 400, SEC)
    refs = [("Spill 17", GNET, S17["kjedekost"], S17["forsterkning"]), ("Simulert: Sara teller på vei", net(SIM1["serier"]["Grossist"]), SIM1["kjedekost"], SIM1["forsterkning"]),
            ("Simulert: alle fire", net(SIM2["serier"]["Grossist"]), SIM2["kjedekost"], SIM2["forsterkning"])]
    for i, (nm, v, kost, fo) in enumerate(refs):
        yy = py + 36 + i * 56
        b += T(px, yy + 12, nm, 13, 400, SEC)
        b += T(px + pw, yy + 12, f"Kjede {nb(kost)} kr · Fabrikk {x_(fo['Fabrikk'])}", 13, 500, INK, "end", num=True)
        b += hz(px, yy + 20, pw, 28, v, span=36, ramp="duo")
    p, _ = P(px, py + 36 + 3 * 56 + 14, "Å telle på vei er ikke nok alene: i simuleringen ga en regel som jaget siste ordre for hardt, Fabrikk 12×.", pw, 13, c=SEC, lh=18)
    b += p
    # Hjelpegrad
    px = 1480
    pw = 454
    b += T(px, py, "Hjelpegrad: Replay åpner Posisjon", 16, 500, INK)
    b += T(px, py + 22, "Replay, Uke 14. Ikke like for like", 14, 400, SEC)
    rg = REP["serier"]["Grossist"]
    n = 14
    rv = [("Netto lager", net(rg)[:n], "duo"), ("Ordre inn", rg["innkommende_ordre"][:n], "neu"), ("Egen ordre", rg["ordre"][:n], "neu"), ("På vei", rg["paa_vei"][:n], "neu")]
    pos = [a - c + d for a, c, d in zip(rg["lager"], rg["restordre"], rg["paa_vei"])][:n]
    for i, (nm, v, rp) in enumerate(rv):
        yy = py + 34 + i * 27
        b += T(px, yy + 16, nm, 13, 400, SEC)
        b += hz(px + 84, yy, pw - 130, 22, v, span=n, ramp=rp)
        b += T(px + pw, yy + 16, sgn(v[-1]), 13, 500, INK, "end", num=True)
    yy = py + 34 + 4 * 27 + 4
    b += R(px - 6, yy - 4, pw + 12, 34, "none", 4, INK, 1)
    b += T(px, yy + 18, "Posisjon", 13, 600, INK)
    b += hz(px + 84, yy, pw - 130, 26, pos, span=n, ramp="duo")
    b += T(px + pw, yy + 18, sgn(pos[-1]), 13, 600, INK, "end", num=True)
    p, _ = P(px, yy + 48, "Klassespillet har de fire øverste, og Posisjon bare som regnestykke etter tasting. Replay gir stripa, slik at innsikten kan brukes.", pw, 13, lh=18)
    b += p
    b += demo(1940, 1385, "end")
    doc("10-pedagogikk", 2000, 1400, "Horisont: grafgrammatikk og prinsipper",
        "Saras fire striper ved Uke 5, 11, 18 og 29, lesemåten for horisontgrafer, og det som låses opp etter Debriefen: forsterkning, 60 spill, simulert referanse og Posisjon i Replay. Demodata og Simulert er merket.", b)


# ---------- klasserekker ----------
def class_rows():
    rows = list(SPILL)
    random.Random(1994).shuffle(rows)
    return rows


def urgency_rows():
    def k(s):
        st = s["status"]
        if st == "venter":
            return (0, -s["ventet_timer"], s["spill"])
        if st == "pauset":
            return (1, -s["uke"], s["spill"])
        if st == "pågår":
            return (2, -s["uke"], s["spill"])
        return (3, 0, s["spill"])
    return sorted(SPILL, key=k)


# ---------- 07 Debrief ----------
def panel(x, y, w, h, head, inner):
    o = R(x, y, w, h, BG, 10, HAIR)
    o += T(x + 24, y + 38, head, 19, 500, INK)
    return o + G_(x, y, 1, inner)


def build_07():
    b = T(40, 48, "Debrief: fra ett spill til hele klassen", 28, 400, INK)
    b += T(1000, 48, "Alle tall fra loggen. Øvelsen får sitt navn her, ikke før.", 15, 400, SEC)
    # 1 Forklaring
    x, y, w, h = 40, 72, 450, 540
    o = ""
    p, yy = P(24, 72, "Hvorfor svingte kjeden? Du skriver først. Det du skriver nå blir ditt eget utgangspunkt senere.", w - 48, 15)
    o += p
    o += R(24, yy + 6, w - 48, 136, WELL, 6)
    p, _ = P(38, yy + 34, "Jeg så restordren vokse og bestilte mer. Det som var på vei kom senere enn jeg regnet med, og da kom alt samtidig.", w - 76, 15, c=INK)
    o += p
    o += btn(24, yy + 156, w - 48, 48, "Lever Forklaring")
    yy += 236
    o += T(24, yy, "Avsløringen er låst", 15, 500, INK)
    o += T(w - 24, yy, "2 av 4 har levert", 14, 400, SEC, "end", num=True)
    o += R(24, yy + 12, w - 48, 40, WELL)
    o += T(w / 2, yy + 38, "Kundeetterspørsel: vises når alle har levert", 14, 400, SEC, "middle")
    yy += 80
    for a, c in [("Ida, Detaljist", "levert"), ("Mikkel, Distributør", "levert"), ("Jonas, Fabrikk", "skriver"), ("Sara, deg", "skriver")]:
        o += T(24, yy, a, 14, 400, SEC) + T(w - 24, yy, c, 14, 400, INK, "end")
        yy += 24
    b += panel(x, y, w, h, "1  Skriv Forklaring", o)
    # 2 Avsløring
    x, w = 510, 720
    o = ""
    p, yy = P(24, 76, "Kundene bestilte 4 i fire uker, så 8. Deretter endret det seg aldri.", w - 48, 26, lh=34, c=INK)
    o += p
    yy += 8
    sw = w - 48
    o += T(24, yy + 10, "Kundeetterspørsel", 15, 500, INK)
    o += T(24 + sw, yy + 10, "4, så 8 fra Uke 5", 15, 500, INK, "end", num=True)
    o += hz(24, yy + 20, sw, 100, SER["demand"], span=36, ramp="neu")
    o += T(24, yy + 142, "Din ordre", 15, 400, SEC)
    o += T(24 + sw, yy + 142, f"Høyest {max(G['ordre'])}, Uke {G['ordre'].index(max(G['ordre'])) + 1}", 15, 400, SEC, "end", num=True)
    o += hz(24, yy + 152, sw, 100, G["ordre"], span=36, ramp="neu")
    o += axis(24, yy + 274, sw, 36, [1, 5, 10, 15, 20, 25, 30, 36])
    p, yy2 = P(24, yy + 306, "Øvelsen heter Beer Game. Samme skala på begge stripene: alt som er høyere enn den øverste, ble laget inne i kjeden.", sw, 15)
    o += p
    b += panel(x, y, w, h, "2  Etterspørselen avsløres", o)
    # 3 Fire roller
    x, w = 1250, 810
    o = ""
    p, yy = P(24, 72, "Ordrene vokser oppover i kjeden og kommer senere. Alle fire ser ut som svar på noe stort, men kundene hadde bare gått fra 4 til 8.", w - 48, 15)
    o += p
    sx, sw = 110, w - 110 - 90
    yy += 2
    o += T(24, yy + 26, "Kunder", 14, 400, SEC)
    o += hz(sx, yy + 4, sw, 44, SER["demand"], span=36, ramp="neu")
    o += T(w - 24, yy + 30, "4 → 8", 14, 400, SEC, "end", num=True)
    fr_prev = None
    for i, r in enumerate(ROLES):
        yt = yy + 58 + i * 70
        me = r == "Grossist"
        o += T(24, yt + 22, r, 14, 500 if me else 400, INK if me else SEC)
        if me:
            o += T(24, yt + 40, "deg", 13, 400, MUT)
        o += hz(sx, yt, sw, 62, SER[r]["ordre"], span=36, ramp="neu")
        first = next(j for j, v in enumerate(SER[r]["ordre"]) if v > 8)
        fx = sx + first * sw / 35
        o += L(fx, yt - 4, fx, yt + 66, INK, 1.2)
        if fr_prev:
            o += L(fr_prev, yt - 8, fx, yt - 4, INK, 1)
        o += T(fx + 5, yt + 13, f"Uke {first + 1}", 13, 500, INK, num=True)
        fr_prev = fx
        o += T(w - 24, yt + 34, x_(S17["forsterkning"][r]), 22, 400, INK, "end", num=True)
    yb = yy + 58 + 4 * 70
    o += axis(sx, yb + 8, sw, 36, [1, 10, 20, 30, 36])
    o += T(24, yb + 36, "Strek: første uke med ordre over 8. Tallet til høyre: Forsterkning, spill 17.", 14, 400, SEC)
    b += panel(x, y, w, h, "3  Alle fire Roller", o)
    # 4 Ditt øyeblikk
    x, y, w, h = 40, 630, 930, 550
    o = ""
    colw = 270
    o += T(24, 76, "Dette så du", 15, 500, INK)
    for i, (a, v) in enumerate([("Restordre", G["restordre"][10]), ("Ordre inn", G["innkommende_ordre"][10]), ("På vei", G["paa_vei"][10]), ("Posisjon", GPOS[10])]):
        o += T(24, 102 + i * 24, a, 15, 400, SEC) + T(24 + colw - 70, 102 + i * 24, v, 15, 500, INK, "end", num=True)
    o += T(24, 216, "Dette bestilte du", 15, 500, INK)
    o += T(24, 256, "24", 40, 400, INK)
    p, _ = P(24, 290, f"Uke 11 til 18 bestilte du {sum(G['ordre'][10:18])}, mens ordre inn var {sum(G['innkommende_ordre'][10:18])}.", colw - 40, 15, c=INK)
    o += p
    o += T(24, 356, "Dette kostet det senere", 15, 500, INK)
    p, _ = P(24, 382, f"Lager toppet på {max(G['lager'])} i Uke {G['lager'].index(max(G['lager'])) + 1}. Uke 26 til 36 betalte du {nb(G['kost_sum'][35] - G['kost_sum'][24])} kr for lager mens ordre inn var {min(G['innkommende_ordre'][25:])} til {max(G['innkommende_ordre'][25:])}.", colw - 40, 15, c=INK)
    o += p
    o += T(24, h - 22, "KI-generert, kan ta feil. Tallene er fra loggen.", 13, 400, MUT)
    # høyre: stripene
    sx = 300
    sw = w - sx - 24
    o += T(sx, 76, "Spill 17 mot simulert referanse", 15, 500, INK)
    o += T(w - 24, 76, "Simulert", 14, 500, INK, "end")
    groups = [("Ditt netto lager", GNET, "duo", "Spill 17"), ("Simulert: du teller alt på vei fra Uke 5", net(SIM1["serier"]["Grossist"]), "duo", "Simulert"),
              ("Din ordre", G["ordre"], "neu", "Spill 17"), ("Simulert: ordre", SIM1["serier"]["Grossist"]["ordre"], "neu", "Simulert")]
    yy = 92
    wk_x = sx + 10 * sw / 35
    for nm, v, rp, _ in groups:
        o += T(sx, yy + 12, nm, 13, 400, SEC)
        o += hz(sx, yy + 18, sw, 36, v, span=36, ramp=rp)
        o += L(wk_x, yy + 16, wk_x, yy + 56, INK, 1.2)
        yy += 66
    o += T(wk_x + 5, yy + 6, "Uke 11", 13, 600, INK, num=True)
    o += axis(sx, yy + 6, sw, 36, [1, 36], prefix="Uke ", size=13)
    yy += 26
    o += L(sx, yy, w - 24, yy)
    colsx = [sx, sx + 210, sx + 400]
    for cx, (h1, a, c) in zip(colsx, [("Kjeden", nb(S17["kjedekost"]), nb(SIM1["kjedekost"])), ("Grossist", nb(S17["kost_per_rolle"]["Grossist"]), nb(SIM1["kost_per_rolle"]["Grossist"])), ("Din Forsterkning", x_(S17["forsterkning"]["Grossist"]), x_(SIM1["forsterkning"]["Grossist"]))]):
        o += T(cx, yy + 24, h1, 14, 400, SEC)
        o += T(cx, yy + 50, a, 19, 500, INK, num=True) + T(cx, yy + 72, c + "  simulert", 14, 400, SEC, num=True)
    p, _ = P(sx, yy + 98, f"Da du tastet 24, så de andre noe annet: Ida netto {sgn(net(SER['Detaljist'])[10])}, Mikkel {sgn(net(SER['Distributør'])[10])}, Jonas {sgn(net(SER['Fabrikk'])[10])}. Mikkel fikk din 24 som ordre inn i Uke 13. Referansen viser sammenhengen, ikke en fasit.", sw, 14, c=SEC)
    o += p
    b += panel(x, y, w, h, "4  Ditt øyeblikk: Uke 11", o)
    # 5 Quiz
    x, w = 990, 400
    o = ""
    p, yy = P(24, 76, f"Hvorfor hadde du {max(G['lager'])} på lager i Uke {G['lager'].index(max(G['lager'])) + 1}?", w - 48, 17, c=INK, w=400)
    o += p
    yy += 6
    opts = [("Kundene kjøpte mindre", "wrong"), ("Ordrene fra Uke 11 til 18 kom fram etter at restordren var dekket", "right"), ("Leverandøren sendte for mye", None)]
    for lab, st in opts:
        ls = wrap(lab, w - 90, 15)
        hh = 18 + len(ls) * 21
        o += R(24, yy, w - 48, hh, WELL if st else "none", 6, INK if st == "wrong" else HAIR)
        for j, l in enumerate(ls):
            o += T(38, yy + 23 + j * 21, l, 15, 400, INK)
        if st == "wrong":
            o += T(w - 36, yy + 23, "Ditt svar", 13, 500, INK, "end")
        if st == "right":
            o += T(w - 36, yy + hh - 9, "Riktig", 13, 500, INK, "end")
        yy += hh + 10
    yy += 6
    o += T(24, yy + 8, "Hvorfor ikke kundene", 15, 500, INK)
    p, yy = P(24, yy + 34, "Kundeetterspørselen lå på 8 fra Uke 5 og ut spillet. Se stripa i steg 2. Lageret kom av levering minus ordre inn: det som var bestilt ble levert selv om du trengte det mindre da.", w - 48, 15)
    o += p
    o += hz(24, yy + 2, w - 48, 34, SER["demand"], span=36, ramp="neu")
    o += T(32, yy + 17, "Kundeetterspørsel", 13, 400, INK)
    o += T(w - 32, yy + 17, "4, så 8", 13, 500, INK, "end", num=True)
    o += btn(24, 490, w - 48, 44, "Neste spørsmål", primary=False)
    b += panel(x, y, w, h, "5  Debrief-quiz", o)
    # Delt skjerm
    x, w = 1410, 650
    o = ""
    rows = class_rows()
    sx, sw = 24, w - 48 - 70
    ry, rh = 104, 6.3
    me_y = 0
    n_ferdig = 0
    for i, s in enumerate(rows):
        yt = ry + i * rh
        if s["spill"] == 17:
            v = GNET
            me_y = yt
        else:
            v = s["netto_lager"]["Grossist"]
        if len(v) == 36:
            n_ferdig += 1
        o += hz(sx, yt, sw, rh - 0.8, v, span=36, ramp="duo", well=True)
    o += R(sx - 2, me_y - 2, sw + 4, rh + 3.2, "none", 2, INK, 1.2)
    o += T(sx + sw + 8, me_y + 7, "Ditt spill", 14, 600, INK)
    back = sum(1 for s in rows if (s["spill"] == 17 or len(s["netto_lager"]["Grossist"]) == 36)
               and min(GNET if s["spill"] == 17 else s["netto_lager"]["Grossist"]) < 0 and (GNET if s["spill"] == 17 else s["netto_lager"]["Grossist"])[-1] > 0)
    o += T(24, 84, "60 grupper. Samme kjede. Nesten samme form.", 21, 400, INK)
    o += T(24, 106 - 2, "", 13)
    o += axis(sx, ry + 60 * rh + 16, sw, 36, [1, 10, 20, 30, 36], size=13)
    under = sum(1 for s in rows if len(GNET if s["spill"] == 17 else s["netto_lager"]["Grossist"]) == 36 and min(GNET if s["spill"] == 17 else s["netto_lager"]["Grossist"]) < 0)
    b_ = f"Alle {under} ferdige spill gikk under null som Grossist. {60 - n_ferdig} pågår ennå og slutter i sin uke. Tilfeldig rekkefølge, ingen navn."
    p, _ = P(24, ry + 60 * rh + 36, b_, w - 48, 14, lh=19)
    o += p
    b += panel(x, y, w, h, "Delt skjerm", o)
    doc("07-debrief", 2100, 1200, "Horisont: Gruppedebrief i fem steg og delt skjerm",
        "Forklaring, avsløring av etterspørselen, alle fire Rollers ordre, Uke 11 mot simulert referanse, quiz, og 60 spill som striper. Demodata og Simulert er merket.", b)


# ---------- 08 Oversikt ----------
def status_text(s):
    st = s["status"]
    if st == "venter":
        return f"venter på {s['navn']} ({s['venter_paa']})", f"{s['ventet_timer']} t"
    if st == "pauset":
        return f"pauset, fortsetter {s['fortsetter']}", ""
    if st == "pågår":
        return "pågår", ""
    return "ferdig", ""


def build_08():
    X, Y, W, H = 80, 24, 1440, 952
    o = R(0, 0, W, H, BG, 8, HAIR)
    o += T(24, 36, "Oversikt", 24, 400, INK)
    o += T(128, 36, "IBE160 · class-of-1994", 15, 400, SEC)
    o += T(W - 24, 36, "Faglærer Bård", 14, 400, SEC, "end")
    # filter
    fy = 58
    fx = 24
    for i, (lab, on) in enumerate([("Alle 60", True), ("Venter 4", False), ("Pauset 2", False), ("Pågår 13", False), ("Ferdig 41", False), ("Med KI-seter", False)]):
        wd = len(lab) * 7.4 + 22
        o += R(fx, fy, wd, 26, WELL if on else "none", 4, HAIR)
        o += T(fx + wd / 2, fy + 18, lab, 13, 500 if on else 400, INK if on else SEC, "middle", num=True)
        fx += wd + 6
    o += T(fx + 16, fy + 18, "Sortert: trenger deg først", 13, 400, SEC)
    # kolonner
    cx_sp, cx_st = 24, 62
    sx0, cw, cg = 278, 208, 12
    rtop, rh = 124, 12.75
    rows = urgency_rows()
    for j, r in enumerate(ROLES):
        cx = sx0 + j * (cw + cg)
        o += T(cx, 112, r, 14, 500, INK)
    o += T(cx_sp, 112, "Spill", 13, 400, SEC) + T(cx_st, 112, "Status og ventetid", 13, 400, SEC)
    rx = sx0 + 4 * (cw + cg)
    o += T(rx, 112, "Kjede", 13, 400, SEC) + T(rx + 74, 112, "KI", 13, 400, SEC, "end")
    sb = rx + 96
    for i, s in enumerate(rows):
        y = rtop + i * rh
        near = s["status"] == "venter" and s["ventet_timer"] >= 23
        if near:
            o += R(18, y - 1, sb - 26, rh + 0.5, "none", 2, SIGNAL, 1.2)
        ferdig = s["status"] == "ferdig"
        o += T(cx_sp, y + 9.8, s["spill"], 11, 400, MUT if ferdig else INK, num=True)
        a, c = status_text(s)
        col = MUT if ferdig else INK if s["status"] != "pågår" else SEC
        o += T(cx_st, y + 9.8, a, 11, 400, col, num=True)
        if c:
            o += T(sx0 - 10, y + 9.8, c, 11, 700 if near else 500, SIGNAL if near else INK, "end", num=True)
        for j, r in enumerate(ROLES):
            cx = sx0 + j * (cw + cg)
            o += hz(cx, y + 0.6, cw, rh - 1.5, s["netto_lager"][r], span=36, ramp="duo")
        o += T(rx + 46, y + 9.8, f"{s['kjedekost']:,}".replace(",", " "), 11, 400, MUT if ferdig else SEC, "end", num=True)
        if s["ki_seter"]:
            o += T(rx + 74, y + 9.8, s["ki_seter"], 11, 500, INK, "end", num=True)
    yb = rtop + 60 * rh + 16
    for j, r in enumerate(ROLES):
        cx = sx0 + j * (cw + cg)
        for t in [1, 12, 24, 36]:
            o += T(cx + (t - 1) * cw / 35, yb, ("Uke 1" if t == 1 else t), 12, 400, MUT, "start" if t == 1 else ("end" if t == 36 else "middle"), num=True)
        q = KL["ferdige"]["forsterkning_per_rolle"][r]
        o += T(cx, yb + 18, f"Forsterkning, median {x_(q['median'])}", 12, 400, SEC, num=True)
    o += T(cx_sp, yb, "Netto lager. Pågående spill slutter på sin uke.", 12, 400, SEC)
    o += demo(cx_sp, yb + 18, size=12)
    # sidepanel
    x = sb + 2
    wp = W - x - 20
    o += L(x - 12, 58, x - 12, H - 16)
    o += T(x, 72, "Nær overtakelse", 15, 500, INK)
    o += T(x, 98, "Spill 2", 20, 400, INK)
    o += T(x + wp, 98, "23 t", 20, 500, SIGNAL, "end", num=True)
    o += T(x, 120, "Venter på Noah, Grossist", 13, 400, SEC)
    o += T(x, 138, "KI overtar ved 24 t", 13, 400, SEC)
    o += btn(x, 150, wp, 32, "Send Melding til Noah", size=13)
    o += btn(x, 188, wp, 32, "Sett Pause", primary=False, size=13)
    o += T(x, 248, "Venter", 15, 500, INK)
    yy = 272
    for s in rows[1:4]:
        o += T(x, yy, f"Spill {s['spill']}, {s['navn']}", 13, 400, SEC, num=True) + T(x + wp, yy, f"{s['ventet_timer']} t", 13, 500, INK, "end", num=True)
        yy += 22
    o += T(x, yy + 22, "Pauset", 15, 500, INK)
    yy += 46
    for s in [q for q in rows if q["status"] == "pauset"]:
        o += T(x, yy, f"Spill {s['spill']}, Uke {s['uke']}", 13, 400, SEC, num=True) + T(x + wp, yy, "19:00", 13, 400, INK, "end", num=True)
        yy += 22
    # trakt
    yy += 22
    o += T(x, yy, "Trakt", 15, 500, INK)
    yy += 12
    tr = KL["traktA"]
    labs = [("registrert", "Registrert"), ("klassespill_ferdig", "Klassespill ferdig"), ("debrief_ferdig", "Debrief"), ("quiz_bestått", "Quiz"), ("replay_ferdig", "Replay"), ("test_levert", "Test"), ("ki_vurdering_klar", "KI-vurdering")]
    for k, lab in labs:
        v = tr[k]
        yy += 28
        o += T(x, yy - 4, lab, 13, 400, SEC) + T(x + wp, yy - 4, v, 13, 500, INK, "end", num=True)
        o += R(x, yy + 1, wp, 4, WELL) + (R(x, yy + 1, wp * v / tr["registrert"], 4, NEU[2]) if v else "")
    yy += 34
    o += T(x, yy, "Ferdige spill", 15, 500, INK)
    f = KL["ferdige"]["kjedekost"]
    o += T(x, yy + 24, "Kjede, median", 13, 400, SEC) + T(x + wp, yy + 24, f"{f['median']:,.0f}".replace(",", " "), 13, 500, INK, "end", num=True)
    fj = KL["fjoraaret"]
    o += T(x, yy + 46, "Fjoråret, median", 13, 400, SEC) + T(x + wp, yy + 46, f"{fj['median_kjedekost']:,}".replace(",", " "), 13, 400, SEC, "end", num=True)
    o += key(x, yy + 84, size=13, sw=15, sh=11, ticks=False)
    o += T(x, yy + 126, "Hver tone er 40 enheter", 13, 400, SEC)
    o += btn(x, H - 54, wp, 36, "Skriv Melding", primary=False, size=13)
    b = G_(X, Y, 1, o)
    doc("08-laerer-oversikt", 1600, 1000, "Horisont: Oversikt for faglærer",
        "60 Klassespill i fire Rolle-kolonner med ekte netto lager, status, ventetid, KI-seter, trakt og Spill 2 uthevet like før KI overtar. Demodata.", b)


# ---------- 01 Landing ----------
def build_01():
    W, H = 1440, 1200
    b = ""
    b += T(80, 56, "Horisont", 22, 500, INK)
    b += T(W - 80, 54, "Logg inn", 15, 500, INK, "end")
    # helt: venstre tekst, høyre striper
    head = ["Hele øvelsen,", "fra invitasjon", "til PDF-rapport."]
    for i, l in enumerate(head):
        b += T(80, 190 + i * 66, l, 58, 300, INK)
    p, yy = P(80, 392, "Forsyningskjede-øvelsen for klasser på rundt 250 studenter. KI-spillere fyller tomme seter, ett fravær stopper ikke gruppa, og ingen spill blir stående uferdig.", 500, 19, lh=29, c=SEC)
    b += p
    b += btn(80, yy + 22, 218, 54, "Be om lærertilgang", size=16)
    b += btn(310, yy + 22, 112, 54, "Logg inn", primary=False, size=16)
    # 60 striper, en rolle, ingen ukeakse
    rows = urgency_rows()
    sx, sw = 650, 560
    top, rh = 110, 10
    for i, s in enumerate(rows):
        y = top + i * rh
        v = s["netto_lager"]["Grossist"]
        b += hz(sx, y, sw, rh - 1.2, v, span=36, ramp="duo")
    n_open = sum(1 for s in rows if s["status"] != "ferdig")
    b += T(sx + sw + 12, top + 9, "Spill 2 venter", 14, 500, SIGNAL)
    b += T(sx + sw + 12, top + 28, "23 t", 14, 400, SEC, num=True)
    b += L(sx + sw + 5, top, sx + sw + 5, top + n_open * rh - 2)
    b += T(sx + sw + 12, top + n_open * rh - 26, f"{n_open} underveis,", 14, 400, SEC, num=True)
    b += T(sx + sw + 12, top + n_open * rh - 7, "hver i sin uke", 14, 400, SEC)
    b += L(sx + sw + 5, top + n_open * rh, sx + sw + 5, top + 60 * rh)
    b += T(sx + sw + 12, top + n_open * rh + 14, f"{60 - n_open} ferdige", 14, 400, SEC, num=True)
    y9 = top + 60 * rh + 26
    b += T(sx, y9, "Alle spillene på én skjerm.", 18, 400, INK)
    p, y10 = P(sx, y9 + 24, "Hver stripe er ett Klassespill, ett sete. Blågrønt står over null, kobber henger under, og stripa slutter der spillet er nå.", 560, 14)
    b += p
    b += T(sx, y10 + 2, "Demodata", 13, 400, MUT)
    # neste seksjon
    y = 846
    b += L(80, y, W - 80, y)
    b += T(80, y + 64, "Ett sete, én beslutning per uke", 34, 300, INK)
    p, yy = P(80, y + 102, "Studenten taster ett heltall. Systemet regner. På telefonen står setets egne tall som fire striper på én akse.", 500, 17, lh=26)
    b += p
    facts = ["Kjører hele øvelsen, fra invitasjon til PDF-rapport", "På mobil, på norsk", "Studentlisten fra Canvas-eksport"]
    yy += 14
    for f in facts:
        b += L(80, yy - 18, 580, yy - 18)
        b += T(80, yy + 2, f, 15, 400, INK)
        yy += 38
    # seksjon: Saras striper
    sx, y0 = 650, y + 30
    n = 11
    w = 560
    vals = strip_vals(n, pending=True)
    for i, (nm, v) in enumerate(vals.items()):
        yt = y0 + i * 66 + 20
        b += T(sx, yt - 6, nm, 14, 400, SEC)
        b += R(sx, yt, w, 42, WELL)
        b += hz(sx, yt, w, 42, v, span=n, ramp="duo" if i == 0 else "neu", well=False)
        b += T(sx + w - 6, yt - 6, {0: netto_label(n), 1: G["innkommende_ordre"][10], 2: f"{G['ordre'][9]} i Uke 10", 3: G["paa_vei"][10]}[i], 15, 500, INK, "end", num=True)
    b += L(sx + w, y0 + 12, sx + w, y0 + 3 * 66 + 66, INK, 1)
    b += axis(sx, y0 + 3 * 66 + 82, w, n, ticks_for(n), now=n)
    b += T(sx, y0 + 3 * 66 + 108, "Ett setes egne tall. Høyre kant er nå. Demodata.", 13, 400, MUT)
    doc("01-landing", W, H, "Horisont: landingsside for faglærere",
        "Første skjermbilde med 60 striper for ett sete per spill uten ukeakse, og starten av neste seksjon med ett setes fire striper. Demodata.", b, bg=BG)


# ---------- 02 Lag Klasse ----------
def field(x, y, w, label, val, h=44, mono=False):
    o = T(x, y, label, 14, 400, SEC)
    o += R(x, y + 8, w, h, WELL, 4) + T(x + 14, y + 8 + h / 2 + 5, val, 15, 400, INK)
    return o


def appbar(W, crumb):
    o = T(40, 44, "Horisont", 18, 500, INK) + T(130, 44, crumb, 14, 400, SEC)
    o += T(W - 40, 44, "Faglærer Bård", 14, 400, SEC, "end") + L(0, 66, W, 66)
    return o


def build_02():
    W, H = 1440, 1000
    b = appbar(W, "Klasser / Ny Klasse")
    b += T(40, 118, "Lag Klasse", 30, 300, INK)
    b += field(40, 162, 340, "Navn", "class-of-1994")
    b += field(400, 162, 200, "Emnekode", "IBE160")
    # opplasting
    b += T(40, 248, "Klasseliste fra Canvas-eksport", 14, 400, SEC)
    b += R(40, 258, 560, 56, WELL, 4)
    b += T(54, 292, "ibe160-eksport.xlsx", 15, 500, INK) + T(586, 292, "250 rader", 15, 400, SEC, "end", num=True)
    # e-postkolonne
    b += T(40, 350, "Velg e-postkolonne", 14, 400, SEC)
    cols = ["Student", "ID", "E-post", "Seksjon"]
    colw = [170, 90, 220, 80]
    data = [["Sara Nilsen", "48213", "sara.nilsen@uia.example", "A"], ["Ida Berg", "48107", "ida.berg@uia.example", "A"], ["Noah Lie", "48455", "noah.lie@uia.example", "B"], ["Rad 37: Emil Moe", "48390", "emil.moe@uia", "B"]]
    x = 40
    xs = []
    for c, wd in zip(cols, colw):
        xs.append(x)
        x += wd
    b += R(xs[2], 358, colw[2], 152, "none", 3, INK, 1.2)
    for c, cx in zip(cols, xs):
        b += T(cx + 10, 380, c, 13, 600 if c == "E-post" else 400, INK if c == "E-post" else SEC)
    b += L(40, 390, 600, 390)
    for i, row in enumerate(data):
        for cell, cx in zip(row, xs):
            b += T(cx + 10, 414 + i * 26, cell, 14, 400, SEC if cell not in ("emil.moe@uia",) else INK, num=True)
    # ugyldige
    b += T(40, 560, "4 ugyldige adresser", 20, 400, INK)
    b += T(40, 584, "Rett dem her, eller send uten. Bare disse radene stopper.", 14, 400, SEC)
    bad = [(37, "emil.moe@uia"), (88, "h.olsen@uia,example"), (141, "tuva haugen@uia.example"), (203, "omar.ali@")]
    for i, (r, a) in enumerate(bad):
        y = 612 + i * 42
        b += T(40, y + 21, f"Rad {r}", 14, 500, INK, num=True)
        b += R(104, y, 346, 32, WELL, 4) + T(116, y + 21, a, 14, 400, INK)
        b += T(462, y + 21, "Ugyldig adresse", 13, 400, SEC)
    b += btn(40, 790, 280, 50, "Send 246 Invitasjoner", size=16)
    b += T(334, 820, "Invitasjon gyldig i 14 dager", 14, 400, SEC)
    # status høyre
    x, w = 680, 720
    b += L(x - 40, 90, x - 40, H - 40)
    b += T(x, 118, "Status etter Invitasjon", 22, 300, INK)
    ros = KL["roster"]
    # 250 kolonner, én per student
    y = 150
    cw = w / 50
    rowsn = 5
    rowh = 26
    seq = [TEAL[1]] * ros["registrert"] + [TEAL[2]] * ros["manuelt_registrert"] + [NEU[0]] * ros["uregistrert"]
    for i, col in enumerate(seq):
        cx, cy = x + (i % 50) * cw, y + (i // 50) * rowh
        b += R(cx, cy, cw - 2, rowh - 2, col)
    y2 = y + rowsn * rowh + 26
    for i, (v, lab, col) in enumerate([(ros["registrert"], "registrert", TEAL[1]), (ros["manuelt_registrert"], "manuelt registrert", TEAL[2]), (ros["uregistrert"], "uregistrert", NEU[0])]):
        xx = x + i * 220
        b += R(xx, y2 - 11, 12, 12, col)
        b += T(xx + 20, y2, f"{v} {lab}", 15, 400, INK, num=True)
    b += T(x, y2 + 26, "Én rute per student på Klasselisten. 250 på lista.", 14, 400, SEC, num=True)
    # tabell
    y3 = y2 + 70
    b += T(x, y3, "Uregistrert", 16, 500, INK)
    b += T(x + w, y3, "Send påminnelse til alle 10", 14, 500, INK, "end")
    b += L(x + w - 182, y3 + 5, x + w, y3 + 5, INK, 1)
    y3 += 14
    un = [("Emil Moe", "Rad 37, ugyldig adresse", "ikke sendt"), ("Tuva Haugen", "Rad 141, ugyldig adresse", "ikke sendt"), ("Omar Ali", "Rad 203, ugyldig adresse", "ikke sendt"), ("Hanne Olsen", "Rad 88, ugyldig adresse", "ikke sendt"),
          ("Mina Dahl", "sendt ti. 3. nov", "gyldig 12 dager til"), ("Lars Vik", "sendt ti. 3. nov", "gyldig 12 dager til"), ("Sofie Lund", "sendt ti. 3. nov", "gyldig 12 dager til")]
    for i, (a, c, d) in enumerate(un):
        y = y3 + 32 + i * 42
        b += L(x, y - 26, x + w, y - 26)
        b += T(x, y, a, 15, 400, INK) + T(x + 180, y, c, 14, 400, SEC, num=True) + T(x + w, y, d, 14, 400, SEC, "end", num=True)
    b += T(x, y3 + 32 + 7 * 42 - 6, "Tre til", 14, 400, SEC)
    b += demo(40, H - 28)
    doc("02-laerer-klasse", W, H, "Horisont: Lag Klasse",
        "Navn og emnekode, Canvas-fil, valg av e-postkolonne, ugyldige rader per rad, send Invitasjoner og status. Demodata.", b, bg=BG)


# ---------- 03 Klasseøkt ----------
def build_03():
    from datetime import date
    W, H = 1440, 1100
    b = appbar(W, "class-of-1994 / Klasseøkt")
    b += T(40, 118, "Klasseøkt", 30, 300, INK)
    b += T(200, 118, "Alt er utfylt. Du kan lagre uten å endre noe.", 15, 400, SEC)
    b += btn(W - 240, 88, 200, 44, "Lagre Klasseøkt", size=15)
    # venstre: innstillinger
    x, w = 40, 620
    y = 170
    b += T(x, y, "Spillinnstillinger", 20, 400, INK) + T(x + 200, y, "Klassisk", 14, 500, INK)
    rows = [("Startlager", "12"), ("I hvert ledd ved start", "4 enheter"), ("Ordreforsinkelse", "2 uker"), ("Fraktforsinkelse", "2 uker"), ("Produksjonsforsinkelse", "2 uker"), ("Lagerkost", "0,50 per enhet per uke"), ("Restordrekost", "1,00 per enhet per uke"), ("Lengde", "36 uker"), ("Veiledede uker", "1 til 4"), ("Inaktivitetsgrense", "24 t")]
    y += 16
    for a, c in rows:
        y += 35
        b += L(x, y + 12, x + w, y + 12)
        b += T(x, y, a, 15, 400, SEC) + T(x + w, y, c, 15, 400, INK, "end", num=True)
    p, y = P(x, y + 34, "Kildene er uenige om forsinkelsene. Dette er produktets standard.", w, 14, c=MUT)
    b += p
    # etterspørsel
    y += 14
    b += T(x, y + 2, "Etterspørsel", 15, 400, SEC) + T(x + w, y + 2, "4, så 8 fra Uke 5. Bare du ser denne.", 15, 400, INK, "end")
    b += hz(x, y + 12, w, 40, SER["demand"], span=36, ramp="neu")
    b += axis(x, y + 70, w, 36, [1, 5, 10, 20, 30, 36])
    y += 112
    b += T(x, y, "Modus", 20, 400, INK)
    y += 26
    for lab, opts, sel, desc in [("KI-modus", ["LLM-spillere", "Regelbaserte spillere"], 0, "Fyller tomme seter. Alltid merket som KI-spiller."), ("Debrief-modus", ["Gruppedebrief", "Personlig debrief"], 0, "Gruppa skriver Forklaring før avsløringen."), ("Krav", ["Obligatorisk", "Ikke obligatorisk"], 0, "Du godkjenner i emnets eget system, basert på fullføring.")]:
        b += T(x, y + 19, lab, 15, 400, SEC)
        cx = x + 200
        for j, op in enumerate(opts):
            wd = len(op) * 8 + 28
            b += R(cx, y, wd, 30, WELL if j == sel else "none", 4, INK if j == sel else HAIR)
            b += T(cx + wd / 2, y + 20, op, 14, 500 if j == sel else 400, INK if j == sel else SEC, "middle")
            cx += wd + 8
        b += T(x + 200, y + 50, desc, 14, 400, SEC)
        y += 72
    # høyre: tidslinje
    x, w = 720, 680
    b += L(x - 30, 150, x - 30, H - 40)
    y = 170
    b += T(x, y, "Datoer og Labtimer", 20, 400, INK)
    d0, d1 = date(2026, 11, 24), date(2026, 12, 18)
    span = (d1 - d0).days
    sx = lambda d: x + (d - d0).days / span * w
    y += 62
    frister = [(d0, "Start", "ti. 24. nov", "start"), (date(2026, 12, 8), "Spillfrist", "ti. 8. des", "middle"), (date(2026, 12, 11), "Debrief-frist", "fr. 11. des", "start"), (d1, "Testfrist", "fr. 18. des", "end")]
    b += R(x, y, sx(frister[1][0]) - x, 26, BAR)
    b += T(x + 10, y + 18, "Klassespill", 13, 500, INK)
    b += R(sx(frister[1][0]) + 1, y, sx(frister[2][0]) - sx(frister[1][0]) - 1, 26, NEU[1])
    b += R(sx(frister[2][0]) + 1, y, sx(d1) - sx(frister[2][0]) - 1, 26, BAR)
    b += T(sx(frister[2][0]) + 10, y + 18, "Test", 13, 500, INK)
    b += T(sx(frister[1][0]) + 8, y + 18, "Debrief", 13, 500, BG)
    for d, a, c, an in frister:
        ax = sx(d)
        if a == "Spillfrist":
            ax -= 0
            an = "end"
        b += L(sx(d), y - 8, sx(d), y + 26, INK, 1)
        b += T(ax, y - 30, a, 14, 500, INK, an)
        b += T(ax, y - 13, c, 13, 400, SEC, an, num=True)
    labs = [(date(2026, 11, 26), "to. 26. nov 14:15"), (date(2026, 11, 30), "ma. 30. nov 10:15"), (date(2026, 12, 3), "to. 3. des 14:15"), (date(2026, 12, 7), "ma. 7. des 10:15")]
    for d, a in labs:
        b += R(sx(d) - 3, y + 34, 6, 12, INK)
    y += 66
    b += T(x, y, "Labtimer, Datalab A2", 14, 500, INK)
    for i, (d, a) in enumerate(labs):
        b += T(x + 180 + (i % 2) * 180, y + (i // 2) * 22, a, 14, 400, SEC, num=True)
    # fordeling
    y += 74
    b += L(x, y - 26, x + w, y - 26)
    b += T(x, y, "Fordeling", 20, 400, INK)
    b += T(x + w, y, "240 studenter, 60 spill à 4, tilfeldig", 15, 400, SEC, "end", num=True)
    y += 20
    rng = random.Random(3)
    cols, rows_ = 12, 5
    cw = w / cols
    tiles = list(range(1, 61))
    for i, n in enumerate(tiles):
        cx = x + (i % cols) * cw
        cy = y + (i // cols) * 52
        b += T(cx, cy + 12, n, 12, 400, INK if n == 17 else MUT, num=True)
        for j in range(4):
            b += R(cx + j * 11, cy + 18, 9, 16, NEU[2] if n == 17 else NEU[0])
        if n == 17:
            b += R(cx - 4, cy - 2, 50, 40, "none", 3, INK, 1)
    y += rows_ * 52 + 14
    b += T(x, y + 10, "Spill 17", 15, 500, INK)
    y += 16
    for i, (r, a) in enumerate(zip(ROLES, ["Ida Berg", "Sara Nilsen", "Mikkel Sand", "Jonas Hauge"])):
        b += T(x + i * 170, y + 16, r, 13, 400, SEC) + T(x + i * 170, y + 36, a, 15, 400, INK)
    y += 72
    b += btn(x, y, 220, 46, "Bekreft fordeling", size=15)
    b += btn(x + 232, y, 190, 46, "Kjør på nytt", primary=False, size=15)
    b += T(x + w, y + 28, "Du kan bekrefte etter første kjøring.", 14, 400, SEC, "end")
    b += demo(40, H - 28)
    doc("03-laerer-spill", W, H, "Horisont: Klasseøkt",
        "Forhåndsutfylte standarder, KI-modus, Debrief-modus, Obligatorisk, datoer på tidsakse, Labtimer og fordeling av 240 studenter i 60 spill. Demodata.", b, bg=BG)


# ---------- 04 Studenthjem ----------
def build_04():
    W, H = 1000, 900
    b = T(90, 42, "Registrering fra Invitasjon", 16, 400, SEC) + T(530, 42, "Hjem under spill", 16, 400, SEC)
    s = 0.97
    # registrering
    o = T(20, 56, "Horisont", 18, 500, INK)
    o += T(20, 118, "Du er invitert til", 15, 400, SEC)
    o += T(20, 150, "IBE160, class-of-1994", 24, 400, INK)
    o += T(20, 176, "Faglærer Bård", 14, 400, SEC)
    o += field(20, 226, 350, "Navn", "Sara Nilsen", h=48)
    o += field(20, 306, 350, "E-post", "sara.nilsen@uia.example", h=48)
    o += field(20, 386, 350, "Passord", "••••••••••", h=48)
    p, y = P(20, 480, "Du spiller i en gruppe på fire. Du får Rolle og spill når faglæreren har fordelt klassen.", 350, 15)
    o += p
    o += btn(20, y + 14, 350, 52, "Registrer meg")
    o += T(195, y + 94, "Invitasjonen er gyldig i 14 dager", 13, 400, MUT, "middle")
    b += phone(90, 60, s, o)
    # hjem
    o = T(20, 46, "Spill 17", 26, 400, INK) + T(370, 46, "Grossist", 15, 500, INK, "end")
    seats = [("Detaljist", "Ida"), ("Grossist", "Sara, deg"), ("Distributør", "Mikkel"), ("Fabrikk", "Jonas")]
    y = 74
    for i, (a, c) in enumerate(seats):
        cx = 20 + (i % 2) * 180
        cy = y + (i // 2) * 24
        o += T(cx, cy, a, 13, 400, SEC) + T(cx + 76, cy, c, 13, 500 if "deg" in c else 400, INK)
    y = 132
    o += R(20, y, 350, 170, PANEL, 8, HAIR)
    o += T(34, y + 32, "Spillet venter på deg", 19, 500, INK)
    o += T(356, y + 32, "Uke 11", 15, 400, SEC, "end")
    o += hz(34, y + 46, 322, 54, GNET[:11], span=11, ramp="duo")
    o += btn(34, y + 112, 322, 44, "Bestill for Uke 11", size=15)
    y = 336
    o += T(20, y, "Dine seks steg", 15, 400, SEC)
    steps = [("Klassespill", "pågår"), ("Debrief", "etter spillet"), ("Quiz", "etter Debrief"), ("Replay", "etter quiz"), ("Individuell test", "frist fr. 18. des"), ("Rapport", "PDF når alt er ferdig")]
    y += 24
    for i, (a, c) in enumerate(steps):
        on = i == 0
        o += f'<circle cx="28" cy="{y + i * 37 - 5}" r="{5 if on else 4}" fill="{INK if on else "none"}" stroke="{INK if on else NEU[1]}" stroke-width="1.2"/>'
        if i < 5:
            o += L(28, y + i * 37 + 2, 28, y + (i + 1) * 37 - 11, HAIR)
        o += T(46, y + i * 37, a, 15, 500 if on else 400, INK if on else SEC)
        o += T(370, y + i * 37, c, 13, 400, INK if on else MUT, "end")
    y += 6 * 37 + 4
    o += L(20, y - 10, 370, y - 10)
    o += T(20, y + 14, "Neste frist", 15, 400, SEC) + T(370, y + 14, "Spillfrist ti. 8. des", 15, 500, INK, "end")
    o += T(20, y + 46, "Labtime", 15, 400, SEC) + T(370, y + 46, "to. 26. nov 14:15", 15, 500, INK, "end", num=True)
    o += T(370, y + 68, "Datalab A2", 13, 400, SEC, "end")
    o += T(20, y + 68, "Også ma. 30. nov, to. 3. des, ma. 7. des", 13, 400, MUT)
    o += demo(20, 820)
    b += phone(530, 60, s, o)
    doc("04-student-hjem", W, H, "Horisont: Sara på mobil",
        "To telefoner: registrering fra Invitasjon, og hjem under spill med setene, seks steg, neste frist, Labtimer og «spillet venter på deg». Demodata.", b)


# ---------- 09 Kontaktark ----------
def bars(x, y, ws, c=NEU[0], h=5, g=9):
    return "".join(R(x, y + i * g, w, h, c) for i, w in enumerate(ws))


def build_09():
    W, H = 2000, 1400
    b = T(40, 50, "Alle andre sider", 28, 300, INK)
    b += T(280, 50, "Samme stripe overalt. Grupper per rolle. Demodata.", 15, 400, SEC)
    tw, th = 252, 176
    cols = 7
    gapx = (W - 80 - cols * tw) / (cols - 1)
    rows_y = [76, 404, 732, 1060]
    cell = lambda i, r: (40 + i * (tw + gapx), rows_y[r] + 28)

    def thumb(i, r, name, line, inner):
        x, y = cell(i, r)
        o = R(0, 0, tw, th, BG, 6, HAIR) + inner
        out = G_(x, y, 1, o)
        out += T(x, y + th + 26, name, 16, 500, INK)
        p, _ = P(x, y + th + 48, line, tw, 13, lh=18)
        return out + p

    gv = GNET
    g4 = lambda n, x, y, w, h, gap: "".join(hz(x, y + i * (h + gap), w, h, v, span=n, ramp="duo" if i == 0 else "neu") for i, v in enumerate(strip_vals(n).values()))
    rows = class_rows()

    def many(x, y, w, h, role="Grossist", nrows=60):
        rh = h / nrows
        o = ""
        for i, s in enumerate(rows[:nrows]):
            v = GNET if (s["spill"] == 17) else s["netto_lager"][role]
            o += hz(x, y + i * rh, w, rh - 0.3, v, span=36, ramp="duo", well=False)
        return o

    def lab(x, y, s, size=11, c=SEC, w=400, a="start"):
        return T(x, y, s, size, w, c, a, num=True)

    b += T(40, rows_y[0] + 12, "Student", 20, 400, INK)
    b += T(40 + 5 * (tw + gapx), rows_y[1] + 12, "Faglærer", 20, 400, INK)
    b += T(40, rows_y[1] + 12, "Student, forts.", 20, 400, INK)
    b += T(40, rows_y[3] + 12, "Admin", 20, 400, INK)
    b += T(40, rows_y[2] + 12, "Faglærer, forts.", 20, 400, INK)

    # Student
    b += thumb(0, 0, "Invitasjon og registrering", "Fra e-post til sete på ett skjema.",
               lab(16, 28, "Du er invitert", 14, INK) + bars(16, 46, [220, 220, 220], WELL, 18, 26) + R(16, 130, 220, 26, INK, 4))
    b += thumb(1, 0, "Logg inn", "E-post og passord, ingen selvregistrering.",
               lab(16, 34, "Logg inn", 14, INK) + bars(16, 52, [220, 220], WELL, 20, 30) + R(16, 118, 220, 28, INK, 4))
    b += thumb(2, 0, "Regler før første ordre", "Viser lesemåten på din egen første stripe.",
               lab(16, 26, "Lager 12: står på gulvet", 12, INK) + hz(16, 34, 220, 34, [GNET[0]] * 8, span=8) + lab(16, 92, "Restordre: henger fra taket", 12, INK) + hz(16, 100, 220, 34, [GNET[10]] * 8, span=8) + lab(16, 158, "Hver tone er 40 enheter", 12))
    b += thumb(3, 0, "Startoppgave", "Les en ferdig stripe før du spiller: hva er lageret i tredje uke?",
               lab(16, 26, "Hva er lageret i tredje uke?", 12, INK) + hz(16, 36, 220, 40, GNET[4:12], span=8) + bars(16, 90, [220, 220], WELL, 22, 30) + R(16, 92, 70, 18, "none", 2, INK))
    # Replay: forskjellen
    rg = REP["serier"]["Grossist"]
    pos = [a - c + d for a, c, d in zip(rg["lager"], rg["restordre"], rg["paa_vei"])]
    n = 20
    rs = "".join(hz(16, 34 + i * 26, 220, 22, v, span=n, ramp=rp) for i, (v, rp) in enumerate([(net(rg)[:n], "duo"), (rg["innkommende_ordre"][:n], "neu"), (rg["ordre"][:n], "neu"), (rg["paa_vei"][:n], "neu")]))
    rs += hz(16, 34 + 4 * 26, 220, 22, pos[:n], span=n) + R(14, 32 + 4 * 26, 224, 26, "none", 2, INK)
    b += thumb(4, 0, "Replay", "Tre KI-spillere, tilfeldig etterspørsel. Posisjon har egen stripe.",
               lab(16, 24, "Uke 20. Ikke like for like", 12, INK) + rs)
    rr = hz(16, 34, 220, 36, net(rg), span=36) + lab(16, 86, "Klassespillet", 11) + hz(16, 92, 220, 36, GNET, span=36)
    b += thumb(5, 0, "Replay-gjennomgang", "Replay over Klassespillet, med merknad: ikke like for like.",
               lab(16, 24, "Replay, 33 uker", 11) + rr + lab(16, 150, f"Kjede {nb(REP['kjedekost'])} · {nb(S17['kjedekost'])}", 12, INK))
    b += thumb(6, 0, "Individuell test: flervalg", "Spørsmål med stripe fra et ukjent spill.",
               lab(16, 26, "Hvilken Rolle er dette?", 12, INK) + hz(16, 36, 220, 36, net(SER["Fabrikk"]), span=36) + bars(16, 86, [220, 220, 220], WELL, 18, 25))
    b += thumb(0, 1, "Individuell test: tegne og tabell", "Tegn en stripe for neste uker, eller fyll inn tabellen.",
               lab(16, 26, "Tegn netto lager", 12, INK) + hz(16, 36, 150, 50, GNET[:16], span=26, well_full=False) + R(16, 36, 220, 50, "none", 0, HAIR)
               + f'<path d="M136 62 L160 50 L190 44 L222 60" fill="none" stroke="{INK}" stroke-width="1.5"/>' + "".join(R(16 + i * 44, 104, 40, 22, WELL) for i in range(5)) + "".join(R(16 + i * 44, 130, 40, 22, WELL) for i in range(5)))
    b += thumb(1, 1, "Individuell test: langsvar", "Forklar hvorfor det svingte, med tall fra loggen ved siden av.",
               lab(16, 26, "Hvorfor svingte kjeden?", 12, INK) + R(16, 36, 220, 92, WELL) + bars(26, 48, [190, 170, 186, 120, 180, 90], NEU[0], 4, 11) + lab(16, 150, "Teller ikke før levert", 11))
    b += thumb(2, 1, "KI-vurdering", "Teller ikke, er aldri en karakter, og sier det øverst.",
               lab(16, 26, "KI-vurdering. Teller ikke.", 12, INK, 500) + lab(16, 44, "KI-generert, kan ta feil", 11) + bars(16, 58, [220, 190, 210, 150], NEU[0], 4, 10) + hz(16, 104, 220, 30, GNET, span=36) + lab(16, 156, "Ikke en karakter", 12))
    b += thumb(3, 1, "Studentrapport (PDF)", "Dine striper, din Forklaring, din quiz og test.",
               R(66, 12, 120, 152, INK, 2) + hz(76, 24, 100, 20, GNET, span=36, well=False, band=BAND) + bars(76, 54, [100, 86, 96, 70, 94, 60, 84], NEU[1], 3, 8) + hz(76, 118, 100, 20, G["ordre"], span=36, ramp="neu", well=False))
    b += thumb(4, 1, "Alle spill side om side", "Etter Debriefen: 60 striper for din Rolle, ditt spill markert.",
               many(16, 14, 220, 148))
    # Faglærer (rad 2 fra kol 5, rad 3)
    b += thumb(5, 1, "Lærerhjem", "Klassene dine og det som trenger deg nå.",
               lab(16, 26, "class-of-1994", 12, INK) + many(16, 36, 140, 90) + bars(166, 40, [70, 56, 66, 50], NEU[0], 4, 13) + lab(16, 150, "41 ferdig · 15 pågår · 4 venter", 11))
    tr = KL["traktA"]
    tb = "".join(R(16, 34 + i * 16, 220 * v / tr["registrert"], 10, NEU[2]) for i, v in enumerate(tr.values()))
    b += thumb(6, 1, "Klasserapport", "Trakt, kvartiler og Detected patterns for hele klassen.",
               lab(16, 24, "Klasserapport", 12, INK) + tb + lab(16, 160, f"Median kjede {KL['ferdige']['kjedekost']['median']:,.0f}".replace(",", " "), 11))
    sp = "".join(hz(50, 28 + i * 30, 186, 26, SER[r]["ordre"], span=36, ramp="neu") + lab(12, 46 + i * 30, r[:4], 11) for i, r in enumerate(ROLES))
    sp += L(50 + 10 * 186 / 35, 22, 50 + 10 * 186 / 35, 150, INK, 1)
    b += thumb(0, 2, "Spillinnsikt (uke for uke)", "Ett spill: fire Roller, flytt uka og les loggen.",
               lab(16, 18, "Spill 17, Uke 11", 11, INK) + sp + lab(16, 166, "Ordre 24 · På vei 16 · Restordre 13", 11))
    b += thumb(1, 2, "Studentside", "Én student: steg, frister, Forklaring, KI-vurdering.",
               lab(16, 26, "Sara Nilsen", 13, INK) + lab(16, 44, "Spill 17, Grossist", 11) + hz(16, 54, 220, 30, GNET, span=36) + "".join(f'<circle cx="{26 + i * 40}" cy="110" r="4" fill="{INK if i < 2 else "none"}" stroke="{NEU[1]}"/>' for i in range(6)) + bars(16, 130, [200, 150], NEU[0], 4, 11))
    cols4 = "".join(many(12 + j * 58, 28, 54, 136, r) for j, r in enumerate(ROLES))
    b += thumb(2, 2, "Alle spill i plenum", "60 spill, fire Rolle-kolonner, uten navn og uten status.",
               lab(16, 20, "Stor skjerm", 11, INK) + cols4)
    b += thumb(3, 2, "Tverrklasse-statistikk", f"{KL['fjoraaret']['klasse']} mot class-of-1994. Median, aldri enkeltspill.",
               lab(16, 24, "Fabrikk, Forsterkning", 12, INK) + "".join(R(16, 40 + i * 36, 220 * v / 13, 14, NEU[2 - i]) + lab(236, 36 + i * 36, x_(v), 11, INK, 500, "end") for i, v in enumerate([KL["fjoraaret"]["median_forsterkning_fabrikk"], KL["ferdige"]["forsterkning_per_rolle"]["Fabrikk"]["median"]])) + lab(16, 130, "Median kjede", 11) + lab(236, 130, f"{KL['fjoraaret']['median_kjedekost']:,} · {KL['ferdige']['kjedekost']['median']:,.0f}".replace(",", " "), 11, INK, 500, "end"))
    b += thumb(4, 2, "Meldinger", "Til én student, ett spill eller hele klassen, ingen svar mellom spillere.",
               lab(16, 26, "Til: Noah, Spill 2", 12, INK) + R(16, 38, 220, 74, WELL) + bars(26, 50, [190, 170, 120], NEU[0], 4, 12) + R(16, 124, 100, 28, INK, 4) + lab(66, 142, "Send", 12, BG, 600, "middle"))
    b += thumb(5, 2, "Lærers testspill", "Spill alle fire seter selv, med KI-spillere. Teller ikke.",
               lab(16, 24, "Testspill, ikke i klassen", 12, INK) + g4(8, 16, 34, 220, 22, 4) + lab(16, 158, "Bytt sete: Grossist", 11))
    # Admin: bruk rad 3 kol 6 + egen rad
    y4 = rows_y[3] + 28
    def thumb_admin(i, name, line, inner):
        x = 40 + i * (tw + gapx)
        o = R(0, 0, tw, th - 20, BG, 6, HAIR) + inner
        out = G_(x, y4, 1, o)
        out += T(x, y4 + th + 6, name, 16, 500, INK)
        p, _ = P(x, y4 + th + 28, line, tw, 13, lh=18)
        return out + p
    b += thumb_admin(0, "Admin-område", "Klasser, kjøringer og feil på ett sted.", lab(16, 26, "Admin", 13, INK) + bars(16, 40, [220, 220, 220, 220], NEU[0], 4, 22))
    b += thumb_admin(1, "Brukere og roller", "Faglærer, assistent, student, admin.", "".join(lab(16, 28 + i * 24, a, 12, INK) + lab(236, 28 + i * 24, c, 11, SEC, 400, "end") for i, (a, c) in enumerate([("Bård", "faglærer"), ("Assistent", "assistent"), ("Sara", "student"), ("Admin", "admin")])))
    b += thumb_admin(2, "KI-kostnad", "Per Klasse og per uke. Kostnad, ikke kvalitet.", lab(16, 26, "Per Klasse, per uke", 12, INK) + bars(16, 42, [190, 150, 210, 96], NEU[1], 6, 18) + lab(16, 134, "Bruk og kostnad, ingen spilldata", 11))
    doc("09-alle-sider", W, H, "Horisont: kontaktark over alle andre sider",
        "Studentsider, faglærersider og adminsider på lavere detaljnivå, gruppert per rolle, hver med tittel og én linje. Demodata.", b)


def _lum(h):
    r = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    r = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in r]
    return 0.2126 * r[0] + 0.7152 * r[1] + 0.0722 * r[2]


def _cr(a, b):
    x, y = sorted((_lum(a), _lum(b)), reverse=True)
    return (x + 0.05) / (y + 0.05)


def main():
    for fg, bg_, name in [(INK, BG, "ink/grunn"), (SEC, BG, "sek/grunn"), (MUT, BG, "mut/grunn"), (MUT, PANEL, "mut/panel"), (SEC, WELL, "sek/brønn"), (MUT, CANVAS, "mut/lerret"),
                          (BG, INK, "knapp"), (INK, BAR, "ink/stolpe"), (BG, NEU[1], "grunn/nøytral2"), (SIGNAL, BG, "signal/grunn"),
                          (TEAL[0], WELL, "tone1 over/brønn"), (COPPER[0], WELL, "tone1 under/brønn"), (NEU[0], WELL, "nøytral1/brønn")]:
        print(f"{name}: {_cr(fg, bg_):.2f}")
    build_01()
    build_02()
    build_03()
    build_04()
    build_05()
    build_06()
    build_07()
    build_08()
    build_09()
    build_10()
    print("OK")


if __name__ == "__main__":
    main()
