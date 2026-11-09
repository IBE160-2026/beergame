"""Konsept 08 Meterbroen. Bygger 9 SVG-filer fra ../_shared/fixture.json.

Kjor: uv run python build.py

Maalerens faste mapping (samme funksjon overalt):
    vinkel = A * sign(n) * ln(1 + |n|/k) / ln(1 + M/k), A=52 grader, k=8, M=64
    der n = restordre - lager, slik at hoyre er restordre og venstre er lager.
Lærerstripene bruker samme form med k=12, M=100 paa (kr per uke - null).
"""
import json
import math
from html import escape
from pathlib import Path

HERE = Path(__file__).parent
FX = json.loads((HERE.parent / "_shared" / "fixture.json").read_text(encoding="utf-8"))
WK = FX["weeks"]
GAMES = FX["class_games"]
ROLES = ["Detaljist", "Grossist", "Distributør", "Fabrikk"]
NAMES = {"Detaljist": "Ida", "Grossist": "Sara", "Distributør": "Mikkel", "Fabrikk": "Jonas"}
SHORT = {"Detaljist": "Det", "Grossist": "Gro", "Distributør": "Dis", "Fabrikk": "Fab"}

# Palett
WAL0, WAL1, WAL2, WAL3 = "#1E120A", "#35200F", "#553319", "#7C4F2A"
STL0, STL1, STL2, STL3, STL4 = "#15181A", "#24282B", "#41474B", "#858C90", "#C3C8CA"
IV, IV2, IVD = "#F4E9CB", "#E9DAB0", "#D6CAA8"
INK, INK2 = "#15110C", "#463C2C"
RED = "#BE2219"
AMB, GRN, KIC = "#F2AE33", "#94C96F", "#86CFDD"
PAPER = "#E7E3D5"

FONTS = ("https://fonts.googleapis.com/css2?family=Michroma&amp;family=Saira+Condensed:wght@400;500;600;700;800"
         "&amp;family=Saira+Semi+Condensed:wght@400;500;600;700&amp;display=swap")
SIDE = "x"
SEQ = 0


def I(name):
    return f"c08-{SIDE}-{name}"


def U(name):
    return f"url(#{I(name)})"


def uid(prefix="u"):
    global SEQ
    SEQ += 1
    return I(f"{prefix}{SEQ}")


FW = {"m": 0.80, "c": 0.44, "b": 0.51}


def tw(s, size, f="b"):
    return len(s) * size * FW[f]


def t(x, y, s, size=14, f="b", fill=IV, a="start", w=400, extra=""):
    return (f'<text x="{x:.1f}" y="{y:.1f}" class="c08-{f}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{a}" font-weight="{w}" {extra}>{escape(str(s))}</text>')


def wrap(s, maxpx, size, f="b"):
    lines, cur = [], ""
    for word in s.split():
        trial = (cur + " " + word).strip()
        if tw(trial, size, f) > maxpx and cur:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def para(x, y, s, maxpx, size=15, f="b", fill=IV, lh=1.34, w=400):
    out, yy = [], y
    for line in wrap(s, maxpx, size, f):
        out.append(t(x, yy, line, size, f, fill, w=w))
        yy += size * lh
    return "".join(out), yy


def rect(x, y, w, h, fill, rx=0, extra=""):
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" {extra}/>'


def line(x1, y1, x2, y2, stroke=INK, sw=1.0, extra=""):
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{sw}" {extra}/>'


def circ(x, y, r, fill, extra=""):
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{fill}" {extra}/>'


def poly(pts, fill, extra=""):
    return '<polygon points="' + " ".join(f"{a:.1f},{b:.1f}" for a, b in pts) + f'" fill="{fill}" {extra}/>'


def kr(v):
    s = f"{v:,.2f}".replace(",", " ").replace(".", ",")
    return s


def kr0(v):
    return f"{int(round(v)):,}".replace(",", " ")


# ---------- Materialer ----------
def defs():
    return f"""<defs>
<filter id="{I('woodf')}" x="0" y="0" width="1" height="1" color-interpolation-filters="sRGB">
<feTurbulence type="fractalNoise" baseFrequency="0.0035 0.13" numOctaves="5" seed="11" result="n"/>
<feColorMatrix in="n" type="matrix" values="0 0 0 0 0.06  0 0 0 0 0.03  0 0 0 0 0.01  2.1 0 0 0 -0.72" result="g"/>
<feComposite in="g" in2="SourceAlpha" operator="in" result="gg"/>
<feMerge><feMergeNode in="SourceGraphic"/><feMergeNode in="gg"/></feMerge></filter>
<filter id="{I('steelf')}" x="0" y="0" width="1" height="1" color-interpolation-filters="sRGB">
<feTurbulence type="fractalNoise" baseFrequency="0.003 0.9" numOctaves="2" seed="4" result="n"/>
<feColorMatrix in="n" type="matrix" values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0.46 0 0 0 -0.18" result="g"/>
<feComposite in="g" in2="SourceAlpha" operator="in" result="gg"/>
<feMerge><feMergeNode in="SourceGraphic"/><feMergeNode in="gg"/></feMerge></filter>
<filter id="{I('soft')}" x="-15%" y="-15%" width="130%" height="140%"><feDropShadow dx="0" dy="8" stdDeviation="10" flood-color="#000" flood-opacity="0.5"/></filter>
<filter id="{I('softs')}" x="-20%" y="-20%" width="140%" height="150%"><feDropShadow dx="0" dy="2" stdDeviation="2" flood-color="#000" flood-opacity="0.55"/></filter>
<linearGradient id="{I('steel')}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#9BA2A6"/><stop offset=".5" stop-color="#6F767A"/><stop offset="1" stop-color="#555B5F"/></linearGradient>
<linearGradient id="{I('steeld')}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3A4044"/><stop offset="1" stop-color="#25292C"/></linearGradient>
<radialGradient id="{I('face')}" cx=".5" cy=".85" r=".95"><stop offset="0" stop-color="#FFF4D2"/><stop offset=".6" stop-color="{IV}"/><stop offset="1" stop-color="#DFCD9E"/></radialGradient>
<linearGradient id="{I('faced')}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#5D543F"/><stop offset="1" stop-color="#4A4332"/></linearGradient>
<linearGradient id="{I('glass')}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#000" stop-opacity=".36"/><stop offset=".12" stop-color="#000" stop-opacity=".05"/><stop offset=".6" stop-color="#fff" stop-opacity="0"/></linearGradient>
<linearGradient id="{I('cowl')}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2C2823"/><stop offset="1" stop-color="#0F0D0B"/></linearGradient>
<linearGradient id="{I('cap')}" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#7A8185"/><stop offset=".2" stop-color="#E2E5E6"/><stop offset=".48" stop-color="#A2A8AB"/><stop offset=".52" stop-color="#3A3F42"/><stop offset=".56" stop-color="#B7BCBE"/><stop offset=".85" stop-color="#E2E5E6"/><stop offset="1" stop-color="#6B7175"/></linearGradient>
<linearGradient id="{I('btn')}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FBF2D8"/><stop offset="1" stop-color="#E5D3A0"/></linearGradient>
<linearGradient id="{I('btns')}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#565D61"/><stop offset="1" stop-color="#33383B"/></linearGradient>
<radialGradient id="{I('knob')}" cx=".38" cy=".3" r=".85"><stop offset="0" stop-color="#5A5F62"/><stop offset=".55" stop-color="#23262A"/><stop offset="1" stop-color="#0D0E10"/></radialGradient>
<pattern id="{I('hatch')}" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="7" height="7" fill="{PAPER}"/><rect width="3" height="7" fill="#B9B3A0"/></pattern>
<pattern id="{I('hamb')}" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="8" height="8" fill="{AMB}"/><rect width="3.2" height="8" fill="#D08B14"/></pattern>
<pattern id="{I('hsteel')}" width="9" height="9" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="9" height="9" fill="#3A4044"/><rect width="2.5" height="9" fill="#2A2E31"/></pattern>
</defs>"""


def style():
    return f"""<style>@import url('{FONTS}');
.c08-m{{font-family:'Michroma','Eurostile','Arial',sans-serif;letter-spacing:.01em}}
.c08-c{{font-family:'Saira Condensed','Arial Narrow',Arial,sans-serif;font-variant-numeric:tabular-nums lining-nums}}
.c08-b{{font-family:'Saira Semi Condensed','Segoe UI',Arial,sans-serif;font-variant-numeric:tabular-nums lining-nums}}
</style>"""


def wood(x, y, w, h, rx=0):
    return rect(x, y, w, h, WAL2, rx, f'filter="{U("woodf")}"')


def steel(x, y, w, h, rx=0, dark=False):
    return rect(x, y, w, h, U("steeld") if dark else U("steel"), rx, f'filter="{U("steelf")}"')


def screw(x, y, r=4.0, rot=30):
    return (circ(x, y, r, "#A8AEB1", f'stroke="#2A2E31" stroke-width=".8"') +
            line(x - r * .7, y, x + r * .7, y, "#23272A", 1.1, f'transform="rotate({rot} {x:.1f} {y:.1f})"'))


def panel(x, y, w, h, rx=4, fill=STL1):
    return rect(x, y, w, h, fill, rx, f'stroke="#000" stroke-opacity=".6" stroke-width="1"')


# ---------- Maalerens matematikk ----------
def ang(v, k=8.0, M=64.0, A=52.0):
    m = min(1.0, math.log(1 + abs(v) / k) / math.log(1 + M / k))
    return (1 if v >= 0 else -1) * A * m


def net_deg(lager, restordre):
    return ang(restordre - lager)


def teacher_deg(krpw, zero=125.0):
    return ang(krpw - zero, 12.0, 100.0)


def pt(px, py, R, deg):
    a = math.radians(deg)
    return px + R * math.sin(a), py - R * math.cos(a)


def arc(px, py, R, a0, a1):
    x0, y0 = pt(px, py, R, a0)
    x1, y1 = pt(px, py, R, a1)
    large = 1 if abs(a1 - a0) > 180 else 0
    sweep = 1 if a1 > a0 else 0
    return f"M{x0:.2f},{y0:.2f} A{R:.2f},{R:.2f} 0 {large} {sweep} {x1:.2f},{y1:.2f}"


def swing(a0, a1, px, py, dur=1.6, loop=0.0, begin="0s"):
    """Nal med treghet og overshoot. loop>0 gir repetisjon med hvile; sluttposisjon er alltid a1."""
    os_ = (a1 - a0) * 0.24
    total = loop if loop else dur
    f = dur / total
    kt = [0, .42 * f, .68 * f, .86 * f, f] + ([1] if loop else [])
    va = [a0, a1 + os_, a1 - os_ * .36, a1 + os_ * .1, a1] + ([a1] if loop else [])
    vals = ";".join(f"{v:.2f} {px:.2f} {py:.2f}" for v in va)
    ks = ";".join(["0.25 0.1 0.2 1"] * (len(kt) - 1))
    rep = 'repeatCount="indefinite"' if loop else 'fill="freeze"'
    return (f'<animateTransform attributeName="transform" type="rotate" values="{vals}" '
            f'keyTimes="{";".join(f"{k:.4f}" for k in kt)}" calcMode="spline" keySplines="{ks}" dur="{total}s" begin="{begin}" {rep}/>')


NET_MAJOR = [5, 10, 20, 40, 60]
NET_MINOR = [1, 2, 3, 15, 30, 50]


def needle_g(px, py, R, deg, anim="", width=1.8, color=INK, shadow=True, opacity=1):
    blade = [(px - width, py), (px - width * .3, py - R), (px + width * .3, py - R), (px + width, py)]
    sh = ""
    if shadow:
        sh = poly([(a + 3, b + 2) for a, b in blade], "#000", 'opacity=".2"')
    return (f'<g transform="rotate({deg:.2f} {px:.2f} {py:.2f})" opacity="{opacity}">{anim}{sh}{poly(blade, color)}</g>')


def vu(x, y, w, h, deg, cowl="", left="LAGER", right="RESTORDRE", lit=True, red=True, anim="", ghosts=(),
       bezel=7, screws=True, numsize=None, cowlh=None, major=None, minor=None, kfunc=None, labels=None):
    """Tegner en VU-flis. deg er nalvinkel. kfunc mapper skalaverdi til vinkel."""
    kfunc = kfunc or ang
    major = NET_MAJOR if major is None else major
    minor = NET_MINOR if minor is None else minor
    numsize = numsize or max(9.0, w * 0.036)
    cowlh = cowlh or h * 0.29
    px = x + w / 2
    py = y + h - cowlh * .3
    R = min(.47 * w, py - y - numsize - 13)
    cid = uid("clip")
    o = []
    if bezel:
        o.append(steel(x - bezel, y - bezel, w + 2 * bezel, h + 2 * bezel, 5))
        if screws:
            for sx, sy in ((x - bezel / 2, y - bezel / 2), (x + w + bezel / 2, y - bezel / 2),
                           (x - bezel / 2, y + h + bezel / 2), (x + w + bezel / 2, y + h + bezel / 2)):
                o.append(screw(sx, sy, min(3.2, bezel * .42)))
    o.append(f'<clipPath id="{cid}"><rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="3"/></clipPath>')
    o.append(f'<g clip-path="url(#{cid})">')
    o.append(rect(x, y, w, h, U("face") if lit else U("faced")))
    ink = INK if lit else "#A99E80"
    rcol = RED if lit else "#8A3A2C"
    sw = max(1.1, w * .004)
    o.append(f'<path d="{arc(px, py, R, -52, 0)}" fill="none" stroke="{ink}" stroke-width="{sw:.2f}"/>')
    if red:
        band = max(3.0, w * .021)
        o.append(f'<path d="{arc(px, py, R - band / 2 + sw / 2, 0, 52)}" fill="none" stroke="{rcol}" stroke-width="{band:.2f}"/>')
    else:
        o.append(f'<path d="{arc(px, py, R, 0, 52)}" fill="none" stroke="{ink}" stroke-width="{sw:.2f}"/>')
    tl = max(5.0, w * .024)
    for side in (-1, 1):
        for v in minor:
            d = side * abs(kfunc(v))
            x0, y0 = pt(px, py, R, d)
            x1, y1 = pt(px, py, R + tl * .6, d)
            o.append(line(x0, y0, x1, y1, ink, sw * .8))
        for v in major:
            d = side * abs(kfunc(v))
            x0, y0 = pt(px, py, R, d)
            x1, y1 = pt(px, py, R + tl, d)
            o.append(line(x0, y0, x1, y1, ink, sw * 1.3))
            lx, ly = pt(px, py, R + tl + numsize * .62, d)
            o.append(t(lx, ly + numsize * .36, v, numsize, "m", ink, "middle", 400,
                       f'transform="rotate({d * .55:.1f} {lx:.1f} {ly:.1f})"'))
    x0, y0 = pt(px, py, R - w * .02, 0)
    x1, y1 = pt(px, py, R + tl * 1.25, 0)
    o.append(line(x0, y0, x1, y1, ink, sw * 2.2))
    o.append(t(px, py - R - tl * 1.25 - 2.5, "0", numsize * 1.15, "m", ink, "middle"))
    wy = py - R * .40
    lab = max(13, numsize)
    if left:
        o.append(t(x + w * .045, wy, left, lab, "m", ink))
    if right:
        o.append(t(x + w * .955, wy, right, lab, "m", ink, "end"))
    for gd in ghosts:
        o.append(needle_g(px, py, R + 2, gd, "", max(1.0, w * .004), INK, False, .28))
    o.append(needle_g(px, py, R + 2, deg, anim, max(1.1, w * .0052), INK if lit else "#171410"))
    # deksel
    cy = y + h - cowlh
    o.append(f'<path d="M{x:.1f},{y + h:.1f} L{x:.1f},{cy + cowlh * .16:.1f} Q{px:.1f},{cy - cowlh * .16:.1f} '
             f'{x + w:.1f},{cy + cowlh * .16:.1f} L{x + w:.1f},{y + h:.1f} Z" fill="{U("cowl")}"/>')
    o.append(rect(x, y, w, h, U("glass")))
    o.append(poly([(x + w * .58, y), (x + w * .78, y), (x + w * .42, y + h), (x + w * .22, y + h)], "#fff", 'opacity=".05"'))
    o.append("</g>")
    if cowl:
        o.append(cowl(px, cy + cowlh * .1, w, cowlh, x))
    return "".join(o)


def cowl_net(lager, restordre, big_size=44):
    def _c(px, cy, w, cowlh, x):
        o = []
        by = cy + cowlh * .66
        if restordre > 0:
            o.append(t(x + 18, by - big_size * .44, "Lager", 13, "c", IVD, w=500))
            o.append(t(x + 18, by + big_size * .08, lager, big_size * .5, "c", IV, w=700))
            o.append(t(px, by + big_size * .08, restordre, big_size, "c", IV, "middle", 800))
            o.append(t(x + w - 18, by - big_size * .44, "Restordre", 13, "c", IVD, "end", 500))
            o.append(t(x + w - 18, by + big_size * .08, "kasser", 13, "c", IVD, "end", 400))
        else:
            o.append(t(x + 18, by - big_size * .44, "Restordre", 13, "c", IVD, w=500))
            o.append(t(x + 18, by + big_size * .08, restordre, big_size * .5, "c", IV, w=700))
            o.append(t(px, by + big_size * .08, lager, big_size, "c", IV, "middle", 800))
            o.append(t(x + w - 18, by - big_size * .44, "Lager", 13, "c", IVD, "end", 500))
            o.append(t(x + w - 18, by + big_size * .08, "kasser", 13, "c", IVD, "end", 400))
        return "".join(o)
    return _c


# ---------- Tape ----------
def arrivals(seat, week):
    """Hva som kommer i ukene etter week: ordrene fra de tre siste ukene, etter 4 ukers ledetid."""
    out = []
    for back in (3, 2, 1):
        w = week - back
        out.append((w + 4, WK[w - 1]["seats"][seat]["ordre"] if w >= 1 else 4))
    assert sum(v for _, v in out) == WK[week - 1]["seats"][seat]["paa_vei_foer_ordre"], (seat, week)
    return out


def tape(x, y, w, h, frames, head=True, numsize=22):
    """frames: (uke, antall, type) type=fast|ventende|bestilt"""
    o = [rect(x, y, w, h, STL0, 3)]
    hw = 34 if head else 0
    fx = x + hw + 3
    fw = (w - hw - 6) / max(1, len(frames))
    for i, fr in enumerate(frames):
        wk, val, kind = fr
        lx = fx + i * fw
        fill = PAPER if kind == "fast" else (U("hatch") if kind == "ventende" else "#F7F1DF")
        o.append(rect(lx + .75, y + 3, fw - 1.5, h - 6, fill, 1.5))
        if kind == "ventende":
            o.append(rect(lx + 2.5, y + 5, fw - 5, 24, PAPER, 1))
            o.append(rect(lx + 2, y + 4.2, fw - 4, h - 8.4, "none", 1, f'stroke="{INK}" stroke-width="1.4" stroke-dasharray="5 3"'))
        elif kind == "bestilt":
            o.append(rect(lx + 2, y + 4.2, fw - 4, h - 8.4, "none", 1, f'stroke="{INK}" stroke-width="1.6"'))
        o.append(t(lx + 7, y + 22, f"Uke {wk}", 13, "c", INK, w=600))
        o.append(t(lx + fw - 7, y + 24, val, numsize, "c", INK, "end", 800))
        # stansede hull: ett hull per kasse, 12 per rad
        per = 12
        pitch = (fw - 12) / per
        hr = min(2.3, pitch * .36)
        rows = max(1, math.ceil(val / per))
        for j in range(val):
            cx = lx + 6 + pitch * (j % per) + pitch / 2
            cy = y + h - 9 - (rows - 1 - j // per) * (hr * 2 + 2.2)
            if j // per < 3:
                o.append(circ(cx, cy, hr, INK))
    if head:
        o.append(steel(x, y, hw, h, 3, True))
        ay = y + h / 2
        o.append(poly([(x + 22, ay - 9), (x + 22, ay + 9), (x + 9, ay)], IV))
        o.append(line(x + hw, y + 1, x + hw, y + h - 1, "#000", 1.5))
    return "".join(o)


# ---------- Kontroller ----------
def lamp(cx, cy, r, kind):
    if kind == "ok":
        return (circ(cx, cy, r, GRN) + f'<path d="M{cx - r * .5:.1f},{cy:.1f} l{r * .36:.1f},{r * .4:.1f} l{r * .66:.1f},{-r * .8:.1f}" '
                f'fill="none" stroke="{INK}" stroke-width="{max(1.6, r * .26):.1f}" stroke-linecap="round" stroke-linejoin="round"/>')
    if kind == "wait":
        return (circ(cx, cy, r - 1, STL0, f'stroke="{AMB}" stroke-width="2.6"') +
                f'<path d="M{cx:.1f},{cy - r * .55:.1f} V{cy:.1f} H{cx + r * .42:.1f}" fill="none" stroke="{AMB}" stroke-width="1.8" stroke-linecap="round"><animate attributeName="opacity" values="1;.35;1" dur="2.4s" repeatCount="indefinite"/></path>')
    if kind == "you":
        return circ(cx, cy, r - 1, STL0, f'stroke="{IV}" stroke-width="2.6"') + circ(cx, cy, r * .36, IV)
    if kind == "ki":
        s = r * 1.5
        return (poly([(cx, cy - s), (cx + s, cy), (cx, cy + s), (cx - s, cy)], KIC) +
                t(cx, cy + r * .46, "KI", r * 1.3, "c", INK, "middle", 800))
    if kind == "pause":
        return (circ(cx, cy, r - 1, STL0, f'stroke="{IV}" stroke-width="2"') + rect(cx - r * .42, cy - r * .45, r * .28, r * .9, IV) +
                rect(cx + r * .14, cy - r * .45, r * .28, r * .9, IV))
    if kind == "run":
        return circ(cx, cy, r * .8, GRN)
    if kind == "off":
        return circ(cx, cy, r * .72, "#2F3336", 'stroke="#55595C" stroke-width="1"')
    if kind == "lock":
        return (rect(cx - r * .7, cy - r * .1, r * 1.4, r * 1.0, IVD, 1.5) +
                f'<path d="M{cx - r * .42:.1f},{cy - r * .1:.1f} v{-r * .35:.1f} a{r * .42:.1f},{r * .42:.1f} 0 0 1 {r * .84:.1f},0 v{r * .35:.1f}" fill="none" stroke="{IVD}" stroke-width="{max(1.5, r * .2):.1f}"/>')
    return ""


LAMPS_11 = [("Ida", "har bestilt", "ok"), ("Mikkel", "har bestilt", "ok"), ("Jonas", "venter, 3 min", "wait"), ("Sara", "venter: deg", "you")]


def lamps_row(x, y, w, items, h=44):
    o = [panel(x, y, w, h, 3, STL0)]
    cw = w / len(items)
    for i, (name, state, kind) in enumerate(items):
        lx = x + i * cw
        o.append(lamp(lx + 14, y + h / 2, 8, kind))
        o.append(t(lx + 28, y + h / 2 - 3, name, 14, "c", IV, w=700))
        o.append(t(lx + 28, y + h / 2 + 13, state, 13, "c", IVD, w=500))
        if i:
            o.append(line(lx, y + 6, lx, y + h - 6, STL2, 1))
    return "".join(o)


def readout(x, y, w, h, label_lines, val, valsize=25):
    o = [rect(x, y, w, h, STL0, 3, f'stroke="{STL2}" stroke-width="1"')]
    yy = y + 15
    for ln in label_lines:
        o.append(t(x + 7, yy, ln, 13, "c", IVD, w=500))
        yy += 13.5
    o.append(t(x + w - 7, y + h - 8, val, valsize, "c", IV, "end", 700))
    return "".join(o)


def btn(x, y, w, h, label, kind="p", size=19, f="c"):
    if kind == "p":
        return (rect(x, y, w, h, U("btn"), 5, f'filter="{U("softs")}" stroke="#7B6A3F" stroke-width="1"') +
                t(x + w / 2, y + h / 2 + size * .35, label, size, f, INK, "middle", 700))
    if kind == "k":
        return (rect(x, y, w, h, KIC, 5, f'filter="{U("softs")}"') +
                t(x + w / 2, y + h / 2 + size * .35, label, size, f, INK, "middle", 700))
    return (rect(x, y, w, h, U("btns"), 5, f'filter="{U("softs")}" stroke="#000" stroke-width=".8"') +
            t(x + w / 2, y + h / 2 + size * .35, label, size, f, IV, "middle", 600))


def fader_h(x, y, w, val, maxv=40, band=16, ghost=None, h=70, locked=False):
    """Horisontal fader. y = oppe, h = hoyde. Samme skala for bandet 'paa vei' og hetta."""
    tx0 = x + 16
    tx1 = x + w - 16
    tr = tx1 - tx0
    ty = y + 33
    sx = lambda v: tx0 + tr * min(v, maxv) / maxv
    o = [rect(tx0 - 6, ty - 4, tr + 12, 8, "#000", 4, 'stroke="#55595C" stroke-width="1"')]
    if band is not None:
        o.append(rect(tx0, ty - 15, sx(band) - tx0, 9, PAPER, 1))
        for j in range(band):
            o.append(circ(sx(j + .5), ty - 10.5, 2.0, INK))
        o.append(t(tx0 + 1, ty - 19, f"{band} på vei", 14, "c", IV, w=700))
    for v in range(0, maxv + 1, 5):
        tx = sx(v)
        major = v % 10 == 0
        o.append(line(tx, ty + 7, tx, ty + (14 if major else 11), IVD, 1.2 if major else .8))
        if major:
            o.append(t(tx, ty + 33, v, 13, "m", IVD, "middle"))
    if val is not None:
        cx = sx(val)
        cap = 15
        o.append(rect(cx - cap - 1, ty - 24, 2 * cap + 2, 44, "#000", 3, 'opacity=".45" transform="translate(1,3)"'))
        o.append(rect(cx - cap, ty - 24, 2 * cap, 44, U("cap"), 3, 'stroke="#111" stroke-width=".8"'))
        o.append(rect(cx - cap, ty - 1.5, 2 * cap, 3, INK))
        if locked:
            o.append(lamp(cx, ty - 12, 6, "lock"))
    return "".join(o)


# ---------- Telefon ----------
def phone(x, y, s, inner, label=None):
    cid = uid("ph")
    w, h = 390, 844
    return (f'<g transform="translate({x:.1f},{y:.1f}) scale({s})">'
            f'<rect x="-11" y="-11" width="{w + 22}" height="{h + 22}" rx="34" fill="#111315" stroke="#6F767A" stroke-width="2" filter="{U("soft")}"/>'
            f'<clipPath id="{cid}"><rect x="0" y="0" width="{w}" height="{h}" rx="24"/></clipPath>'
            f'<g clip-path="url(#{cid})">{inner}</g></g>')


def game_head(week_txt, role_line, kost_txt, kost_label="Totalkostnad"):
    o = [wood(0, 0, 390, 54)]
    o.append(t(14, 39, week_txt, 34, "c", IV, w=800))
    o.append(t(128 if len(week_txt) < 7 else 150, 25, role_line[0], 16, "c", IV, w=700))
    o.append(t(128 if len(week_txt) < 7 else 150, 43, role_line[1], 14, "c", IVD, w=500))
    if kost_txt:
        o.append(t(378, 22, kost_label, 13, "c", IVD, "end", 500))
        o.append(t(378, 44, kost_txt, 22, "c", IV, "end", 700))
    return "".join(o)


def history(x, y, w, h, orders, first_week=1):
    o = [t(x, y + 13, "Ordrehistorikk", 14, "c", IV, w=600)]
    guided = [i for i, _ in enumerate(orders) if first_week + i <= 4]
    n = max(10, len(orders))
    cw = w / n
    if guided:
        o.append(t(x + w, y + 13, "Uke 1 til 4: Veiledede uker", 13, "c", IVD, "end", 500))
        o.append(rect(x, y + h, cw * len(guided) - 3, 2, IVD))
    for i, val in enumerate(orders):
        cx = x + i * cw + cw / 2
        bh = val / 24 * 15
        o.append(rect(cx - 8, y + 33 - bh, 16, max(1.5, bh), IV))
        o.append(t(cx, y + 47, val, 15, "c", IV, "middle", 700))
        o.append(t(cx, y + 60, first_week + i, 13, "c", IVD, "middle", 400))
    return "".join(o)


def order_panel_typing(week=11, val=24, band=16):
    o = []
    o.append(t(12, 603, "Din ordre", 18, "c", IV, w=700))
    o.append(t(12, 622, f"Uke {week}, hele kasser", 14, "c", IVD, w=500))
    ix = 178
    o.append(btn(ix - 54, 584, 48, 50, "", "s"))
    o.append(rect(ix - 42, 607, 24, 4, IV))
    o.append(rect(ix, 584, 120, 50, U("face"), 3, f'stroke="{IVD}" stroke-width="1.5"'))
    o.append(t(ix + 60, 623, val if val is not None else "", 40, "c", INK, "middle", 800))
    if val is None:
        o.append(line(ix + 60, 596, ix + 60, 624, INK, 2))
    o.append(btn(ix + 126, 584, 48, 50, "", "s"))
    o.append(rect(ix + 138, 607, 24, 4, IV))
    o.append(rect(ix + 148, 597, 4, 24, IV))
    o.append(fader_h(10, 640, 370, val, 40, band))
    label = f"Send ordre: {val} kasser" if val is not None else "Sett ordren først"
    if val is not None:
        o.append(btn(12, 720, 366, 62, label, "p", 24))
    else:
        o.append(rect(12, 720, 366, 62, STL1, 5, f'stroke="{STL2}" stroke-width="1.5" stroke-dasharray="6 4"'))
        o.append(t(195, 758, label, 22, "c", IVD, "middle", 600))
    o.append(t(12, 804, "Ordren kan ikke endres etter sending.", 14, "b", IVD))
    o.append(t(378, 804, "Demodata", 13, "c", IVD, "end"))
    return "".join(o)


def game_screen(week=11, seat="Grossist", spill=17, panel_svg=None, order=24, lamps_items=None, ghosts=(), anim_from=None,
                loop=0.0, tape_extra=None, head_role=None, deg_override=None, pending="ventende", tape_label_extra=True):
    d = WK[week - 1]["seats"][seat]
    deg = net_deg(d["lager"], d["restordre"]) if deg_override is None else deg_override
    o = [wood(0, 0, 390, 844), rect(0, 54, 390, 790, STL1, 0, f'filter="{U("steelf")}"')]
    o.append(game_head(f"Uke {week}", head_role or (seat, f"Spill {spill}, {NAMES[seat]}"), kr(d["kost_sum"]) + " kr"))
    mx, my, mw, mh = 12, 64, 366, 228
    px, py = mx + mw / 2, my + mh - mh * .29 * .3
    anim = ""
    if anim_from is not None:
        anim = swing(anim_from, deg, px, py, 1.6, loop)
    o.append(vu(mx, my, mw, mh, deg, cowl_net(d["lager"], d["restordre"]), anim=anim, ghosts=ghosts))
    # tape
    fr = [(a, b, "fast") for a, b in arrivals(seat, week)]
    total = d["paa_vei_foer_ordre"]
    ty = 303
    o.append(t(12, ty + 14, f"På vei {total}", 18, "c", IV, w=800))
    if order is not None and pending:
        fr.append((week + 4, order, pending))
        if tape_label_extra:
            lbl = f"med ordren din: {total + order}" if pending == "ventende" else f"nå {total + order} på vei"
            o.append(t(378, ty + 14, lbl, 15, "c", IV, "end", 600))
    else:
        fr.append((week + 4, 0, "tom"))
    o.append(tape_frames(10, ty + 20, 370, 64, fr))
    # avlesninger
    ry = 390
    rw = 90.5
    items = [(["Innkommende", "ordre"], d["innkommende_ordre"]), (["Levering", "denne uka"], d["levering"]),
             (["Sendt", "denne uka"], d["sendt"]), (["Neste", "levering"], d["neste_levering"])]
    for i, (lab, val) in enumerate(items):
        o.append(readout(10 + i * (rw + 3.5), ry, rw, 62, lab, val))
    # historikk
    orders = [WK[i]["seats"][seat]["ordre"] for i in range(max(0, week - 11), week - 1)]
    o.append(history(12, 456, 366, 62, orders, max(1, week - 10)))
    # lys
    o.append(lamps_row(10, 523, 370, lamps_items or LAMPS_11))
    o.append(panel_svg if panel_svg is not None else order_panel_typing(week, order, total))
    return "".join(o)


def tape_frames(x, y, w, h, fr):
    """Fire faste rammer der siste kan vaere tom: tapen er ennaa ikke stanset."""
    o = [tape(x, y, w, h, [(f[0], f[1], f[2]) if f[2] != "tom" else (f[0], 0, "fast") for f in fr])]
    for f in fr:
        if f[2] == "tom":
            idx = fr.index(f)
            hw = 34
            fw = (w - hw - 6) / len(fr)
            lx = x + hw + 3 + idx * fw
            o.append(rect(lx + .75, y + 3, fw - 1.5, h - 6, STL1, 1.5))
            o.append(t(lx + fw / 2, y + 28, f"Uke {f[0]}", 13, "c", IVD, "middle", 600))
            o.append(t(lx + fw / 2, y + 45, "ikke satt", 13, "c", IVD, "middle", 400))
    return "".join(o)


# ---------- Side-rammeverk ----------
def page(side, name, W_, H_, title, desc, body_fn):
    global SIDE, SEQ
    SIDE, SEQ = side, 0
    body = body_fn()
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W_} {H_}" font-family="\'Saira Semi Condensed\',\'Segoe UI\',Arial,sans-serif">'
           f'<title>{escape(title)}</title><desc>{escape(desc)}</desc>{style()}{defs()}{body}</svg>')
    (HERE / name).write_text(svg, encoding="utf-8")


def demo(x, y, a="start", fill=IVD, size=14):
    return t(x, y, "Demodata", size, "c", fill, a, 500)


def plate(x, y, w, h, label, size=14, f="m"):
    """Gravert stalskilt med skruer."""
    return (steel(x, y, w, h, 3, True) + screw(x + 9, y + h / 2, 3) + screw(x + w - 9, y + h / 2, 3, 70) +
            t(x + 22, y + h / 2 + size * .36, label, size, f, IV))


# ---------- Kanalstripe ----------
def g_kpw(g):
    return g["kjedekost"] / g["uke"]


def strip(x, y, w, h, g, selected=False):
    st = g["status"]
    near = g.get("ventet_timer", 0) >= 20
    o = []
    live = st != "ferdig"
    o.append(rect(x + 1, y, w - 2, h, "#2E3336" if live else "#1B1E20", 2, f'stroke="{"#5A6165" if live else "#303437"}" stroke-width="1"'))
    # etikett
    o.append(rect(x + 3, y + 3, w - 6, 22, PAPER if live else "#8F8C80", 1.5))
    o.append(t(x + w / 2, y + 20, g["spill"], 17, "c", INK, "middle", 800))
    # malerfjes med korrekt skala
    mx, my, mw, mh = x + 3, y + 28, w - 6, 40
    cid = uid("s")
    px, py = mx + mw / 2, my + mh + 3
    R = min(mw * .55, mh - 7)
    deg = teacher_deg(g_kpw(g))
    o.append(f'<clipPath id="{cid}"><rect x="{mx:.1f}" y="{my:.1f}" width="{mw:.1f}" height="{mh:.1f}" rx="1.5"/></clipPath><g clip-path="url(#{cid})">')
    o.append(rect(mx, my, mw, mh, U("face") if live else U("faced")))
    ink = INK if live else "#A99E80"
    amax = 52
    Rr = R
    o.append(f'<path d="{arc(px, py, Rr, -amax, 0)}" fill="none" stroke="{ink}" stroke-width="1"/>')
    o.append(f'<path d="{arc(px, py, Rr, 0, amax)}" fill="none" stroke="{RED if live else "#8A3A2C"}" stroke-width="1"/>')
    if deg > 0:
        x0, y0 = pt(px, py, Rr, 0)
        x1, y1 = pt(px, py, Rr, deg)
        x2, y2 = pt(px, py, Rr - 8, deg)
        x3, y3 = pt(px, py, Rr - 8, 0)
        o.append(f'<path d="M{x0:.2f},{y0:.2f} A{Rr:.2f},{Rr:.2f} 0 0 1 {x1:.2f},{y1:.2f} L{x2:.2f},{y2:.2f} A{Rr - 8:.2f},{Rr - 8:.2f} 0 0 0 {x3:.2f},{y3:.2f} Z" fill="{RED if live else "#8A3A2C"}"/>')
    for v in (20, 50, 100):
        for sd in (-1, 1):
            d = sd * abs(ang(v, 12.0, 100.0))
            if abs(d) <= 52:
                x0, y0 = pt(px, py, Rr, d)
                x1, y1 = pt(px, py, Rr + 2.6, d)
                o.append(line(x0, y0, x1, y1, ink, .8))
    x0, y0 = pt(px, py, Rr - 1, 0)
    x1, y1 = pt(px, py, Rr + 4, 0)
    o.append(line(x0, y0, x1, y1, ink, 1.5))
    o.append(needle_g(px, py, Rr + 1, deg, "", 1.05, INK if live else "#14110D", False))
    o.append("</g>")
    # tall
    o.append(t(x + w / 2, y + 85, f"Uke {g['uke']}" if st != "ferdig" else "Ferdig", 14, "c", IV if live else "#B5AC93", "middle", 600))
    o.append(t(x + w / 2, y + 102, kr0(g["kjedekost"]), 15, "c", IV if live else "#B5AC93", "middle", 700 if live else 500))
    # status
    sy = y + 110
    if st == "venter":
        fill = U("hamb") if near else AMB
        o.append(rect(x + 3, sy, w - 6, 96 if near else 74, fill, 2))
        if near:
            o.append(rect(x + 6, sy + 3, w - 12, 54, AMB, 1))
            o.append(t(x + w / 2, sy + 17, g["navn"], 15, "c", INK, "middle", 800))
            o.append(t(x + w / 2, sy + 32, SHORT[g["venter_paa"]], 14, "c", INK, "middle", 600))
            o.append(t(x + w / 2, sy + 53, f'{g["ventet_timer"]} t', 21, "c", INK, "middle", 800))
            o.append(rect(x + 6, sy + 59, w - 12, 34, INK, 1))
            o.append(t(x + w / 2, sy + 73, "KI om", 14, "c", AMB, "middle", 700))
            o.append(t(x + w / 2, sy + 88, "1 t", 14, "c", AMB, "middle", 700))
        else:
            o.append(t(x + w / 2, sy + 17, g["navn"], 15, "c", INK, "middle", 800))
            o.append(t(x + w / 2, sy + 34, SHORT[g["venter_paa"]], 14, "c", INK, "middle", 600))
            o.append(t(x + w / 2, sy + 60, f'{g["ventet_timer"]} t', 18, "c", INK, "middle", 800))
    elif st == "pauset":
        o.append(lamp(x + w / 2, sy + 15, 11, "pause"))
        o.append(t(x + w / 2, sy + 42, "Pause", 14, "c", IV, "middle", 700))
        o.append(t(x + w / 2, sy + 58, "19:00", 14, "c", IVD, "middle", 500))
    elif st == "pågår":
        o.append(lamp(x + w / 2, sy + 15, 9, "run"))
        o.append(t(x + w / 2, sy + 42, "Pågår", 14, "c", IV, "middle", 500))
    else:
        o.append(lamp(x + w / 2, sy + 15, 8, "off"))
    # KI
    k = g["ki_seter"]
    for i in range(k):
        cx = x + w / 2 + (i - (k - 1) / 2) * 20
        o.append(lamp(cx, y + h - 16, 8.5, "ki"))
    if selected:
        o.append(rect(x - .5, y - 3, w + 1, h + 6, "none", 3, f'stroke="{IV}" stroke-width="2.5"'))
    return "".join(o)


# =========================================================
# 05 SPILL
# =========================================================
def p05():
    o = [wood(0, 0, 1600, 1000)]
    # telefon
    o.append(phone(54, 62, 1.0, game_screen(anim_from=net_deg(0, 9))))
    o.append(t(54, 40, "Telefon, 390 px. Alt pluss ordren på én skjerm.", 17, "c", IV, w=600))
    # laptop
    lx, ly, lw, lh = 516, 66, 1040, 740
    o.append(t(lx, 40, "Samme kanal på laptop: måleren til venstre, fader i full høyde til høyre.", 17, "c", IV, w=600))
    o.append(rect(lx - 14, ly - 14, lw + 28, lh + 28, "#0E0F10", 14, f'filter="{U("soft")}" stroke="#6F767A" stroke-width="2"'))
    cid = uid("lap")
    o.append(f'<clipPath id="{cid}"><rect x="{lx}" y="{ly}" width="{lw}" height="{lh}" rx="4"/></clipPath><g clip-path="url(#{cid})">')
    o.append(rect(lx, ly, lw, lh, STL1, 0, f'filter="{U("steelf")}"'))
    o.append(wood(lx, ly, lw, 58))
    d = WK[10]["seats"]["Grossist"]
    o.append(t(lx + 20, ly + 42, "Uke 11", 38, "c", IV, w=800))
    o.append(t(lx + 150, ly + 26, "Grossist", 18, "c", IV, w=700))
    o.append(t(lx + 150, ly + 46, "Spill 17, Sara", 15, "c", IVD, w=500))
    o.append(t(lx + lw - 20, ly + 22, "Totalkostnad", 14, "c", IVD, "end", 500))
    o.append(t(lx + lw - 20, ly + 47, "68,00 kr", 25, "c", IV, "end", 700))
    # maler
    mx, my, mw, mh = lx + 22, ly + 76, 660, 330
    deg = net_deg(0, 13)
    py = my + mh - mh * .29 * .3
    o.append(vu(mx, my, mw, mh, deg, cowl_net(0, 13, 62), anim=swing(net_deg(0, 9), deg, mx + mw / 2, py), numsize=19))
    # tape
    ty = my + mh + 14
    o.append(t(mx - 6, ty + 16, "På vei 16", 21, "c", IV, w=800))
    o.append(t(mx + mw + 6, ty + 16, "med ordren din: 40", 17, "c", IV, "end", 600))
    fr = [(a, b, "fast") for a, b in arrivals("Grossist", 11)] + [(15, 24, "ventende")]
    o.append(tape(mx - 7, ty + 24, mw + 14, 74, fr, numsize=26))
    # avlesninger
    ry = ty + 110
    items = [(["Innkommende", "ordre"], 8), (["Levering", "denne uka"], 4), (["Sendt", "denne uka"], 4), (["Neste", "levering"], 4)]
    rw = (mw + 14 - 18) / 4
    for i, (lab, val) in enumerate(items):
        o.append(readout(mx - 7 + i * (rw + 6), ry, rw, 62, lab, val, 30))
    # hoyre: fader
    fx = mx + mw + 30
    fw = lx + lw - fx - 22
    o.append(panel(fx, my - 7, fw, 516, 4, STL0))
    o.append(t(fx + 18, my + 22, "Din ordre", 21, "c", IV, w=700))
    o.append(rect(fx + 18, my + 34, fw - 36, 66, U("face"), 3))
    o.append(t(fx + fw / 2, my + 86, "24", 56, "c", INK, "middle", 800))
    # vertikal fader
    vx = fx + 96
    v0, v1 = my + 482, my + 138
    sy = lambda v: v0 + (v1 - v0) * v / 40
    o.append(rect(vx - 5, v1 - 6, 10, v0 - v1 + 12, "#000", 5, 'stroke="#55595C" stroke-width="1"'))
    for v in range(0, 41, 5):
        major = v % 10 == 0
        o.append(line(vx + 13, sy(v), vx + (28 if major else 21), sy(v), IVD, 1.2 if major else .8))
        if major:
            o.append(t(vx + 34, sy(v) + 6, v, 15, "m", IVD))
    o.append(rect(vx - 30, sy(16), 12, sy(0) - sy(16), PAPER, 1))
    for j in range(16):
        o.append(circ(vx - 24, sy(j + .5), 2.6, INK))
    o.append(t(vx - 42, sy(8) + 6, "16 på vei", 16, "c", IV, "middle", 700, f'transform="rotate(-90 {vx - 42:.1f} {sy(8) + 1:.1f})"'))
    o.append(rect(vx - 25, sy(24) - 15, 50, 30, U("cap"), 3, 'stroke="#111" stroke-width=".8"'))
    o.append(rect(vx - 25, sy(24) - 1.5, 50, 3, INK))
    o.append(t(vx + 92, sy(24) + 6, "24", 22, "c", IV, "start", 800))
    # historikk + knapp under
    hy = ry + 76
    o.append(history(mx - 6, hy, mw + 12, 62, [WK[i]["seats"]["Grossist"]["ordre"] for i in range(10)], 1))
    o.append(btn(fx, my + 520, fw, 56, "Send ordre: 24 kasser", "p", 23))
    o.append(t(fx, my + 596, "Ordren kan ikke endres etter sending.", 15, "b", IVD))
    # lys i laptop
    ly2 = my + 606
    cw = fw / 2
    for i, (nm, st_, kind) in enumerate(LAMPS_11):
        lxx = fx + (i % 2) * cw
        lyy = ly2 + (i // 2) * 28 + 6
        o.append(lamp(lxx + 10, lyy, 8, kind))
        o.append(t(lxx + 24, lyy + 5, f"{nm}: {st_}", 15, "c", IV, w=500))
    o.append("</g>")
    # hengsel og mapping
    o.append(rect(lx - 34, ly + lh + 14, lw + 68, 16, "#3C4144", 6))
    o.append(rect(lx + lw / 2 - 70, ly + lh + 14, 140, 7, "#1A1C1E", 3))
    cap = ("Skalaen er ikke pynt: nålen står alltid på samme vinkel for samme tall. Vinkel = 52° · ln(1 + |n|/8) / ln 9, der n er restordre minus lager. "
           "Null er balanse, høyre er restordre, venstre er lager. Buen forbi null er det eneste røde på skjermen.")
    s, _ = para(lx - 14, ly + lh + 64, cap, 1060, 16.5, "b", IV, 1.36)
    o.append(s)
    o.append(demo(lx + lw + 14, 40, "end", IV, 15))
    return "".join(o)


# =========================================================
# 06 SPILLDYNAMIKK
# =========================================================
def panel_c():
    o = []
    o.append(rect(10, 576, 370, 74, STL0, 3, f'stroke="{STL2}" stroke-width="1"'))
    o.append(lamp(38, 613, 14, "lock"))
    o.append(t(62, 606, "Ordre 24 sendt", 26, "c", IV, w=800))
    o.append(t(62, 630, "Låst. Kan ikke endres.", 15, "c", IVD, w=500))
    o.append(t(12, 675, "Vi venter på Jonas", 21, "c", IV, w=700))
    rows = [("Ida", "Detaljist", "har bestilt", "ok"), ("Mikkel", "Distributør", "har bestilt", "ok"),
            ("Jonas", "Fabrikk", "venter, 3 min", "wait"), ("Sara", "Grossist, deg", "har bestilt", "ok")]
    for i, (n, r, s, k) in enumerate(rows):
        yy = 690 + i * 37
        o.append(rect(10, yy, 370, 33, STL0, 3))
        o.append(lamp(30, yy + 16.5, 9.5, k))
        o.append(t(50, yy + 22, n, 18, "c", IV, w=700))
        o.append(t(110, yy + 22, r, 16, "c", IVD, w=500))
        o.append(t(370, yy + 22, s, 16, "c", IV, "end", 600))
    return "".join(o)


def panel_d():
    o = []
    o.append(t(195, 612, "Uka går videre", 30, "c", IV, "middle", 800))
    s, _ = para(22, 640, "Alle nålene svinger samtidig, på hver sin skjerm. Du ser bare din egen.", 346, 16, "b", IVD)
    o.append(s)
    # tidsakse til skala
    x0, x1, y = 26, 364, 714
    o.append(rect(x0, y, x1 - x0, 6, "#000", 3))
    o.append(f'<rect x="{x0}" y="{y}" width="{x1 - x0}" height="6" rx="3" fill="{IV}"><animate attributeName="width" values="0;{x1 - x0};{x1 - x0}" keyTimes="0;.2667;1" dur="6s" repeatCount="indefinite"/></rect>')
    o.append(t(x0, y + 26, "0 s", 14, "c", IVD))
    o.append(t(x0 + (x1 - x0) * .8, y + 26, "1,6 s", 14, "c", IV, "middle", 700))
    o.append(line(x0 + (x1 - x0) * .8, y - 3, x0 + (x1 - x0) * .8, y + 10, IV, 2))
    o.append(t(x1, y + 26, "2 s", 14, "c", IVD, "end"))
    o.append(btn(12, 756, 366, 56, "Hopp over", "s", 22))
    return "".join(o)


def panel_e():
    o = []
    o.append(rect(10, 576, 370, 120, STL0, 3, f'stroke="{KIC}" stroke-width="2"'))
    o.append(lamp(36, 606, 13, "ki"))
    o.append(t(62, 603, "KI-spiller har setet ditt", 22, "c", IV, w=800))
    o.append(t(62, 622, "Overtatt etter 24 t uten ordre", 15, "c", IVD, w=500))
    o.append(t(22, 650, "Uke 12: KI-spiller bestilte 6.", 16, "c", IV, w=600))
    o.append(t(22, 672, "Ukene står som KI-uker i loggen.", 15, "c", IVD, w=500))
    o.append(btn(12, 704, 366, 58, "Ta tilbake setet", "k", 24))
    o.append(rect(10, 770, 370, 60, STL0, 3))
    o.append(lamp(30, 800, 10, "pause"))
    s, _ = para(50, 794, "Pause: si når dere fortsetter. Da overtar ingen KI.", 310, 15, "c", IV, 1.15)
    o.append(s)
    return "".join(o)


def screen_f():
    o = [wood(0, 0, 390, 844), rect(0, 54, 390, 790, STL1, 0, f'filter="{U("steelf")}"')]
    o.append(game_head("Slutt", ("Spill 17", "Sara, Grossist"), ""))
    # sluttkostnad
    o.append(rect(10, 66, 370, 150, STL0, 4, f'stroke="{STL2}"'))
    o.append(t(195, 100, "Kjeden totalt", 22, "c", IVD, "middle", 600))
    o.append(t(195, 170, "2 266,00 kr", 62, "c", IV, "middle", 800))
    o.append(t(195, 198, "Totalkostnad for alle fire seter", 15, "c", IVD, "middle", 500))
    # dempede kanaler, per Rolle
    o.append(t(14, 244, "Per Rolle", 19, "c", IV, w=700))
    maxv = 800
    yy = 256
    for r in ROLES:
        v = FX["total_cost_per_role"][r]
        o.append(rect(10, yy, 370, 74, STL0, 3))
        o.append(t(22, yy + 28, r, 19, "c", IV, w=700))
        who = NAMES[r] + (", deg" if r == "Grossist" else "")
        o.append(t(22, yy + 49, who, 15, "c", IVD, w=500))
        o.append(t(368, yy + 38, kr(v) + " kr", 24, "c", IV, "end", 700))
        o.append(rect(22, yy + 58, 346, 6, "#000", 3))
        o.append(rect(22, yy + 58, 346 * v / maxv, 6, IV, 3))
        yy += 80
    o.append(t(14, yy + 18, "Stolpene har samme skala, 0 til 800 kr.", 14, "c", IVD))
    o.append(t(14, yy + 44, "Dere ser nå hele kjeden for første gang.", 16, "b", IV))
    o.append(btn(12, 660, 366, 66, "Gå til Debrief", "p", 26))
    o.append(t(14, 752, "Nålene står stille nå. I Debriefen spilles", 15, "b", IVD))
    o.append(t(14, 772, "de av igjen, side om side.", 15, "b", IVD))
    o.append(t(378, 812, "Demodata", 13, "c", IVD, "end"))
    return "".join(o)


def screen_a():
    s = order_panel_typing(11, None, 16)
    return game_screen(order=None, panel_svg=s, ghosts=(net_deg(0, 9),), anim_from=net_deg(0, 9), loop=6.0)


def highlight_a():
    """Merker levering inn og ordre inn over rammen A."""
    o = []
    o.append(rect(10.5, 390.5, 90.5, 62, "none", 3, f'stroke="{AMB}" stroke-width="3"'))
    o.append(rect(104.5, 390.5, 90.5, 62, "none", 3, f'stroke="{AMB}" stroke-width="3"'))
    return "".join(o)


def p06():
    o = [wood(0, 0, 2100, 1200)]
    o.append(t(40, 52, "Én uke på broen: ett tall, så svinger nålen", 40, "c", IV, w=800))
    o.append(demo(2060, 52, "end", IV, 17))
    s = .79
    pw = 390 * s
    gap = (2100 - 80 - 6 * pw) / 5
    y0 = 84
    xs = [40 + i * (pw + gap) for i in range(6)]
    # A
    o.append(phone(xs[0], y0, s, screen_a() + highlight_a()))
    # B
    o.append(phone(xs[1], y0, s, game_screen()))
    # C
    lc = [("Ida", "har bestilt", "ok"), ("Mikkel", "har bestilt", "ok"), ("Jonas", "venter, 3 min", "wait"), ("Sara", "har bestilt", "ok")]
    o.append(phone(xs[2], y0, s, game_screen(panel_svg=panel_c(), pending="bestilt", lamps_items=lc)))
    # D
    d0, d1 = net_deg(0, 13), net_deg(0, 20)
    o.append(phone(xs[3], y0, s, game_screen(week=12, panel_svg=panel_d(), order=None, pending=None, anim_from=d0, loop=6.0,
                                             ghosts=(d0, d1 + (d1 - d0) * .24),
                                             lamps_items=[("Ida", "bestiller", "wait"), ("Mikkel", "bestiller", "wait"), ("Jonas", "bestiller", "wait"), ("Sara", "deg", "you")])))
    # E
    le = [("Ida", "har bestilt", "ok"), ("Mikkel", "har bestilt", "ok"), ("Jonas", "KI-spiller", "ki"), ("Sara", "har bestilt", "ok")]
    o.append(phone(xs[4], y0, s, game_screen(week=13, seat="Fabrikk", panel_svg=panel_e(), order=None, pending=None, lamps_items=le,
                                             head_role=("Fabrikk", "Spill 17, Jonas"))))
    # F
    o.append(phone(xs[5], y0, s, screen_f()))
    # pilbane mellom rammene
    for i in range(5):
        ax = xs[i] + pw + 10
        ay = y0 + 334
        o.append(poly([(ax + 2, ay - 16), (ax + gap - 24, ay), (ax + 2, ay + 16)], IV, 'opacity=".9"'))
    # notater
    notes = [
        ("A. Uka åpner", "Levering 4 og ordre 8 kommer inn. Nålen drar seg fra 9 til 13, og du ser hvorfor: 4 inn, 8 ut. Tapen rykker fram én rute."),
        ("B. Beslutningen", "Du drar faderen til 24. Rett under nålen står 16 på vei, og den samme mengden står som hvitt bånd over faderen. Ett tall. Sekunder."),
        ("C. Bekreftet", "Hetta låses. Ordren blir en stanset rute på tapen. Fire lys på rekke viser hvem det venter på, med navn, Rolle og tid."),
        ("D. Uka går videre", "Nålen svinger fra 13 til 20 med treghet og overshoot, på 1,6 sekunder. Du kan hoppe over. Lyden er aldri nødvendig."),
        ("E. Jonas er borte", "Etter 24 t uten ordre tar KI-spiller setet. Merket med rute og tekst hos alle. Jonas får «Ta tilbake setet». Pause stopper dette på forhånd."),
        ("F. Spillet slutter", "Lampene slukker. Først kjedens totalkostnad, så per Rolle. Ingen plassering. Knappen fører videre til Debrief."),
    ]
    ny = y0 + 844 * s + 46
    for i, (h, b) in enumerate(notes):
        o.append(t(xs[i], ny, h, 24, "c", IV, w=800))
        ss, _ = para(xs[i], ny + 26, b, pw + 12, 16.5, "b", IV, 1.3)
        o.append(ss)
    # setninger og overshoot-kurve
    by = 950
    o.append(rect(0, by, 2100, 250, STL0))
    o.append(steel(0, by, 2100, 7))
    txt = ("Du leser spillet slik en lydtekniker leser en måler: i ett blikk, med kroppen, før du har lest et eneste tall. "
           "Tyngden i nålen gjør at du kjenner hver uke komme, og den samme flisen tåler 36 uker fordi den aldri ber om mer enn ett blikk og ett tall. "
           "Det spillet gjemmer for deg er ikke det som er på vei, men tiden det tar: båndet står rett under nålen, og likevel drar du faderen forbi det. "
           "Det er den følelsen Debriefen senere legger fire nåler ved siden av.")
    ss, _ = para(40, by + 58, txt, 1300, 25, "b", IV, 1.36)
    o.append(ss)
    # kurve
    cx, cy, cw, ch = 1450, by + 44, 600, 160
    o.append(t(cx, by + 34, "Nålens vei i Uke 12, fra 13 til 20 restordre", 19, "c", IV, w=700))
    o.append(rect(cx, cy, cw, ch, "#1F2326", 3))
    a0, a1 = d0, d1
    amin, amax = a0 - 2, a1 + (a1 - a0) * .34
    sx = lambda tt: cx + 34 + (cw - 48) * tt / 2.0
    sy = lambda a: cy + ch - 26 - (ch - 40) * (a - amin) / (amax - amin)
    os_ = (a1 - a0) * .24
    pts = [(0, a0), (.42 * 1.6, a1 + os_), (.68 * 1.6, a1 - os_ * .36), (.86 * 1.6, a1 + os_ * .1), (1.6, a1), (2.0, a1)]
    # glatt kurve
    dd = f"M{sx(pts[0][0]):.1f},{sy(pts[0][1]):.1f}"
    for i in range(1, len(pts)):
        x_0, y_0 = sx(pts[i - 1][0]), sy(pts[i - 1][1])
        x_1, y_1 = sx(pts[i][0]), sy(pts[i][1])
        dd += f" C{x_0 + (x_1 - x_0) * .45:.1f},{y_0:.1f} {x_1 - (x_1 - x_0) * .45:.1f},{y_1:.1f} {x_1:.1f},{y_1:.1f}"
    o.append(line(sx(0), sy(a1), sx(2), sy(a1), IVD, 1, 'stroke-dasharray="4 4"'))
    o.append(line(sx(0), sy(a0), sx(2), sy(a0), IVD, 1, 'stroke-dasharray="4 4"'))
    o.append(f'<path d="{dd}" fill="none" stroke="{IV}" stroke-width="3"/>')
    o.append(t(cx + 8, sy(a1) - 5, "20", 15, "c", IV, w=700))
    o.append(t(cx + 8, sy(a0) + 5, "13", 15, "c", IV, w=700))
    for tt, lab in ((0, "0 s"), (1.0, "1 s"), (1.6, "1,6 s"), (2.0, "2 s")):
        o.append(line(sx(tt), cy + ch - 26, sx(tt), cy + ch - 20, IVD, 1))
        o.append(t(sx(tt), cy + ch - 6, lab, 14, "c", IVD, "middle"))
    return "".join(o)


# =========================================================
# 08 LAERER-OVERSIKT
# =========================================================
def filter_chip(x, y, label, on=False, w=None):
    w = w or tw(label, 16, "c") + 26
    o = [rect(x, y, w, 32, IV if on else STL1, 3, f'stroke="{IV if on else STL2}" stroke-width="1"')]
    o.append(t(x + w / 2, y + 22, label, 16, "c", INK if on else IV, "middle", 700 if on else 500))
    return "".join(o), w


def p08():
    o = [wood(0, 0, 1600, 1000)]
    sx, sy, sw, sh = 80, 26, 1440, 948
    o.append(rect(sx - 8, sy - 8, sw + 16, sh + 16, "#0D0E0F", 8, f'filter="{U("soft")}" stroke="#5B6165" stroke-width="1.5"'))
    o.append(rect(sx, sy, sw, sh, STL1, 0, f'filter="{U("steelf")}"'))
    # hode
    o.append(wood(sx, sy, sw, 86))
    o.append(t(sx + 20, sy + 40, "Oversikt", 34, "c", IV, w=800))
    o.append(t(sx + 20, sy + 66, "IBE160, class-of-1994. Faglærer Bård", 16, "c", IVD, w=500))
    # tellere med form
    cx = sx + 300
    for lab, val, kind in (("ferdig", 41, "off"), ("pågår, herav 2 pauset", 15, "run"), ("venter", 4, "wait")):
        o.append(lamp(cx + 9, sy + 33, 9, kind))
        o.append(t(cx + 25, sy + 42, val, 28, "c", IV, w=800))
        tx = cx + 25 + tw(str(val), 28, "c") + 10
        o.append(t(tx, sy + 41, lab, 17, "c", IVD, w=500))
        cx = tx + tw(lab, 17, "c") + 26
    # KI-sum
    ki_games = sum(1 for g in GAMES if g["ki_seter"])
    ki_seats = sum(g["ki_seter"] for g in GAMES)
    o.append(lamp(cx + 11, sy + 33, 8.5, "ki"))
    o.append(t(cx + 27, sy + 41, f"{ki_seats} KI-seter i {ki_games} spill", 17, "c", IVD, w=500))
    o.append(demo(sx + sw - 20, sy + 26, "end", IV, 15))
    # filter
    fx = sx + 300
    fy = sy + 50
    o.append(t(fx, fy + 22, "Vis", 16, "c", IVD, w=500))
    fx += 32
    for lab, on in (("Alle 60", True), ("Venter 4", False), ("Pågår 15", False), ("Pause 2", False), (f"KI-seter {ki_games}", False), ("Forbi null", False), ("Ferdig 41", False)):
        s, w = filter_chip(fx, fy, lab, on)
        o.append(s)
        fx += w + 6
    o.append(btn(sx + sw - 190, sy + 44, 170, 36, "Send Melding", "p", 18))
    # banker
    bx = sx + 12
    bw = sw - 24
    w = bw / 30
    h = 210
    selected = 2
    for row in range(2):
        by = sy + 96 + row * (h + 12)
        o.append(rect(bx - 4, by - 4, bw + 8, h + 8, "#0F1112", 3))
        for i in range(30):
            g = GAMES[row * 30 + i]
            o.append(strip(bx + i * w, by, w, h, g, g["spill"] == selected))
    # nederste felt
    ny = sy + 96 + 2 * (h + 12) + 4
    nh = sy + sh - ny - 10
    # aapnet kanal
    ox, ow = sx + 12, 640
    o.append(panel(ox, ny, ow, nh, 4, STL0))
    g2 = GAMES[1]
    o.append(rect(ox + 12, ny + 12, 72, 42, PAPER, 2))
    o.append(t(ox + 48, ny + 44, "2", 34, "c", INK, "middle", 800))
    o.append(t(ox + 96, ny + 34, "Spill 2 venter på Noah, Grossist", 26, "c", IV, w=800))
    o.append(t(ox + 96, ny + 54, f"Uke {g2['uke']}. Kjeden har kostet {kr0(g2['kjedekost'])} kr", 16, "c", IVD, w=500))
    # stor kanal med ventetid som maaler
    vx, vy, vw, vh = ox + 18, ny + 72, 214, 130
    kpw = g_kpw(g2)
    tmaj = [20, 50, 100]
    tmin = [10, 35, 75]
    py = vy + vh - vh * .22 * .3
    def _cw(px, cy, w_, ch, x_):
        return t(px, cy + ch * .78, f"{kpw:.0f} kr/uke".replace(".", ","), 22, "c", IV, "middle", 800)
    o.append(vu(vx, vy, vw, vh, teacher_deg(kpw), _cw, left="", right="", major=tmaj, minor=tmin,
                kfunc=lambda v: ang(v, 12.0, 100.0), numsize=10.5, cowlh=vh * .24, bezel=5))
    # ventetid til overtakelse, til skala
    tx = ox + 256
    ty = ny + 88
    tw_ = ow - 256 - 20
    o.append(t(tx, ty - 4, "Inaktivitetsgrense 24 t", 16, "c", IVD, w=500))
    o.append(rect(tx, ty + 4, tw_, 26, "#000", 2, f'stroke="{STL2}"'))
    o.append(rect(tx, ty + 4, tw_ * 23 / 24, 26, U("hamb"), 2))
    o.append(line(tx + tw_, ty, tx + tw_, ty + 34, IV, 2.4))
    o.append(t(tx + 8, ty + 23, "23 t", 19, "c", INK, w=800))
    o.append(t(tx + tw_, ty + 52, "KI overtar om 1 t", 19, "c", AMB, "end", 800))
    # seter
    seats = [("Detaljist", "har bestilt", "ok"), ("Grossist, Noah", "venter, 23 t", "wait"), ("Distributør", "har bestilt", "ok"), ("Fabrikk", "har bestilt", "ok")]
    ly = ty + 62
    for i, (r, s_, k) in enumerate(seats):
        lx = tx + (i % 2) * (tw_ / 2)
        lyy = ly + (i // 2) * 26
        o.append(lamp(lx + 9, lyy + 7, 8, k))
        o.append(t(lx + 24, lyy + 12, f"{r}: {s_}", 15, "c", IV, w=500))
    # det som skjer videre
    hy_ = ny + 236
    o.append(t(ox + 18, hy_, "Det som skjer videre", 19, "c", IV, w=700))
    for i, txt in enumerate(("Noah fikk e-post etter 2 t, og en ny 4 t før overtakelse.",
                             "Om 1 t tar KI-spiller setet, merket for hele gruppa, og uka går videre.",
                             "Noah kan ta tilbake setet. Ukene med KI står som KI-uker i Spillinnsikt.")):
        o.append(rect(ox + 20, hy_ + 13 + i * 26, 6, 6, IVD))
        o.append(t(ox + 36, hy_ + 21 + i * 26, txt, 16.5, "c", IV, w=500))
    # handlinger
    by = ny + nh - 52
    o.append(btn(ox + 18, by, 190, 40, "Send Melding til Noah", "p", 17))
    o.append(btn(ox + 218, by, 186, 40, "Sett inn KI-spiller nå", "s", 17))
    o.append(btn(ox + 414, by, 208, 40, "Åpne Spillinnsikt", "s", 17))
    # trakt
    fx, fw = ox + ow + 12, 410
    o.append(panel(fx, ny, fw, nh, 4, STL0))
    o.append(t(fx + 16, ny + 30, "Trakten", 22, "c", IV, w=800))
    o.append(t(fx + fw - 16, ny + 30, "studenter", 15, "c", IVD, "end", 500))
    funnel = [("Registrert", 240), ("Klassespill ferdig", 164), ("Debrief ferdig", 121), ("Quiz bestått", 97), ("Replay ferdig", 58), ("Test levert", 12), ("KI-vurdering klar", 0)]
    fy = ny + 42
    rowh = (nh - 54) / 7
    for i, (lab, val) in enumerate(funnel):
        yy = fy + i * rowh
        o.append(t(fx + 16, yy + rowh * .68, lab, 16, "c", IV, w=500))
        o.append(rect(fx + 140, yy + 4, 210, rowh - 8, "#000", 1))
        o.append(rect(fx + 140, yy + 4, 210 * val / 240, rowh - 8, IV, 1))
        o.append(t(fx + fw - 16, yy + rowh * .72, val, 19, "c", IV, "end", 700))
    # tegnforklaring
    lx, lw = fx + fw + 12, sx + sw - 12 - (fx + fw + 12)
    o.append(panel(lx, ny, lw, nh, 4, STL0))
    o.append(t(lx + 14, ny + 30, "Slik leser du en stripe", 22, "c", IV, w=800))
    mx = lx + 14
    my = ny + 44
    mw = lw - 28
    o.append(vu(mx + 4, my + 4, mw - 8, 108, teacher_deg(150), None, left="", right="", major=tmaj, minor=tmin,
                kfunc=lambda v: ang(v, 12.0, 100.0), numsize=10.5, cowlh=14, bezel=4, screws=False))
    s, yy = para(lx + 14, my + 134, "Nål: kjedekost per uke. Null = 125 kr/uke, tallene er avstand fra null. Forbi null fylles buen rød.", lw - 28, 15, "b", IV, 1.28)
    o.append(s)
    rows = [("wait", "Ravfarget plate: venter, med navn og timer"), ("pause", "To streker: Pause, med klokkeslett"), ("ki", "Rute: KI-spiller, én per sete"), ("off", "Mørk flate: ferdig")]
    yy += 2
    for k, txt in rows:
        o.append(lamp(lx + 24, yy + 3, 8, k))
        o.append(t(lx + 42, yy + 8, txt, 15, "c", IV, w=500))
        yy += 21
    return "".join(o)


# =========================================================
# 07 DEBRIEF
# =========================================================
def d_head(title, sub):
    o = [wood(0, 0, 390, 54)]
    o.append(t(14, 36, title, 26, "c", IV, w=800))
    o.append(t(378, 36, sub, 16, "c", IVD, "end", 500))
    return "".join(o)


def d_base():
    return wood(0, 0, 390, 844) + rect(0, 54, 390, 790, STL1, 0, f'filter="{U("steelf")}"')


def ki_tag(x, y, w=250):
    o = [lamp(x + 11, y + 10, 8, "ki"), t(x + 28, y + 15, "KI-generert, kan ta feil", 15, "c", IV, w=600)]
    return "".join(o)


def screen_d1():
    o = [d_base(), d_head("Debrief", "Spill 17, Gruppedebrief")]
    # skodde over maaler
    o.append(steel(12, 66, 366, 200, 4, True))
    o.append(rect(12, 66, 366, 200, U("hsteel"), 4, 'opacity=".9"'))
    o.append(rect(30, 106, 330, 122, STL0, 4, f'stroke="{STL3}"'))
    o.append(lamp(195, 134, 16, "lock"))
    o.append(t(195, 180, "Kundens måler er låst", 26, "c", IV, "middle", 800))
    o.append(t(195, 206, "Den åpner når Forklaringen din er lagret.", 16, "c", IVD, "middle", 500))
    for sx_, sy_ in ((22, 76), (368, 76), (22, 256), (368, 256)):
        o.append(screw(sx_, sy_, 4.5))
    o.append(t(14, 300, "Skriv Forklaring", 24, "c", IV, w=800))
    s, yy = para(14, 326, "Hvorfor ble lagrene og ordrene i kjeden som de ble? Skriv med egne ord. Det blir ikke vurdert.", 362, 16, "b", IV)
    o.append(s)
    ly = 708
    tah = ly - 10 - (yy - 4)
    o.append(rect(12, yy - 4, 366, tah, U("face"), 3))
    answer = "Jeg tror kundene plutselig ville ha mye mer. Da restordrene vokste bestilte jeg 24 for å komme ajour. Så kom alt på en gang."
    s, _ = para(26, yy + 26, answer, 338, 17, "b", INK, 1.36)
    o.append(s)
    o.append(line(26, yy + 134, 26, yy + 156, INK, 2))
    o.append(t(366, yy - 4 + tah - 12, "124 tegn", 14, "c", INK2, "end"))
    o.append(lamps_row(10, ly, 370, [("Ida", "har lagret", "ok"), ("Mikkel", "har lagret", "ok"), ("Jonas", "skriver", "wait"), ("Sara", "deg", "you")]))
    o.append(btn(12, 766, 366, 60, "Lagre Forklaring", "p", 24))
    return "".join(o)


def demand_tape(x, y, w, h, yscale=32):
    """Etterspørsel uke for uke, til samme skala som ordrene."""
    o = [rect(x, y, w, h, "#F7F1DF", 2)]
    bw = (w - 8) / 36
    base = y + h - 16
    pxu = (h - 28) / yscale
    for wk in WK:
        i = wk["week"] - 1
        v = wk["demand"]
        o.append(rect(x + 4 + i * bw + .5, base - v * pxu, bw - 1, v * pxu, INK))
    o.append(line(x + 4, base, x + w - 4, base, INK, 1.2))
    for wk_ in (1, 5, 12, 24, 36):
        lx = x + 4 + (wk_ - .5) * bw
        o.append(t(lx, base + 13, wk_, 13, "c", INK, "middle"))
    return "".join(o)


def screen_d2():
    o = [d_base(), d_head("Debrief", "Etterspørselen")]
    deg = ang(4)
    mx, my, mw, mh = 12, 64, 366, 214
    py = my + mh - 62 * .3
    def _c(px, cy, w, ch, x):
        return t(px, cy + ch * .72, "Kunden: +4", 34, "c", IV, "middle", 800)
    o.append(vu(mx, my, mw, mh, deg, _c, left="", right="", red=False, cowlh=62, anim=swing(0, deg, mx + mw / 2, py, 1.8), ghosts=(0,)))
    o.append(t(14, 340, "Fra 4 til 8.", 54, "c", IV, w=800))
    s, yy = para(14, 370, "Kundene kjøpte 4 kasser i uka. I Uke 5 kjøpte de 8. Deretter 8 hver eneste uke, helt til slutt.", 362, 19, "b", IV, 1.3)
    o.append(s)
    o.append(t(14, yy + 12, "Kundeetterspørsel, Uke 1 til 36", 15, "c", IVD, w=500))
    o.append(demand_tape(12, yy + 20, 366, 118))
    yy2 = yy + 160
    s, yy3 = para(14, yy2, "Den ene endringen er alt som kom fra kundene. Resten kom fra kjeden.", 362, 19, "b", IV, 1.3, 600)
    o.append(s)
    o.append(rect(12, yy3 + 2, 366, 66, STL0, 3))
    o.append(t(24, yy3 + 26, "Du skrev:", 15, "c", IVD, w=500))
    o.append(t(24, yy3 + 50, "«kundene plutselig ville ha mye mer»", 18, "c", IV, w=500))
    o.append(btn(12, 770, 366, 58, "Se hva kjeden gjorde", "p", 23))
    return "".join(o)


def lanes(x, y, w, laneh, gap=4, labels=True, ymax=32, lw_label=86, ampw=60, bg="#F7F1DF", fs=15, ax=True):
    """Stripekart: fem spor med samme y-skala og samme x-akse."""
    o = []
    seriess = [("Kunde", [wk["demand"] for wk in WK], None)]
    for r in ROLES:
        seriess.append((r, [wk["seats"][r]["ordre"] for wk in WK], FX["amplification"][r]))
    ww = w - lw_label - ampw
    xx = x + lw_label
    pxu = (laneh - 3) / ymax
    bw = ww / 36
    for i, (lab, ser, amp) in enumerate(seriess):
        yy = y + i * (laneh + gap)
        o.append(rect(xx, yy, ww, laneh, bg, 1))
        for v in (8, 16, 24):
            o.append(line(xx, yy + laneh - v * pxu, xx + ww, yy + laneh - v * pxu, "#CFC8B1", .6))
        for j, v in enumerate(ser):
            if v:
                o.append(rect(xx + j * bw + .3, yy + laneh - v * pxu, max(.8, bw - .6), v * pxu, INK))
        o.append(t(x, yy + laneh / 2 + fs * .36, lab, fs, "c", IV, w=700))
        if amp:
            o.append(t(x + w, yy + laneh / 2 + (fs + 7) * .36, f"{amp:.1f}×".replace(".", ","), fs + 7, "c", IV, "end", 800))
        else:
            o.append(t(x + w, yy + laneh / 2 + fs * .36, "4 til 8", fs, "c", IVD, "end", 600))
    if ax:
        yy = y + 5 * (laneh + gap) + 11
        for wk_ in (1, 5, 11, 18, 24, 36):
            o.append(t(xx + (wk_ - .5) * bw, yy, wk_, 13, "c", IVD, "middle"))
    return "".join(o)


def screen_d3():
    o = [d_base(), d_head("Debrief", "Ordrer per Rolle")]
    s, yy = para(14, 90, "Samme kunde. Større utslag for hvert ledd.", 362, 25, "c", IV, 1.14, 800)
    o.append(s)
    s, yy = para(14, yy + 2, "Hvert spor viser ordrene uke for uke, til samme skala.", 362, 16, "b", IVD)
    o.append(s)
    o.append(lanes(12, yy - 6, 366, 54, 5, fs=15))
    yy = yy - 6 + 5 * 59 + 34
    o.append(t(14, yy, "Forsterkning fra Detaljist til Fabrikk", 15, "c", IVD, w=500))
    o.append(t(14, yy + 42, "1,8×  til  7,6×", 40, "c", IV, w=800))
    s, yy = para(14, yy + 70, "Hvert ledd ser bare ordrene fra leddet foran og det som står i eget bånd. Uka etter ligger alle de gamle ordrene fortsatt på vei.", 362, 16.5, "b", IV, 1.32)
    o.append(s)
    s, yy = para(14, yy + 6, "Øvelsen heter Beer Game. Mønsteret kalles bullwhip-effekten.", 362, 16.5, "b", IVD, 1.32)
    o.append(s)
    o.append(btn(12, 776, 178, 54, "Vis som tabell", "s", 19))
    o.append(btn(200, 776, 178, 54, "Ditt øyeblikk", "p", 21))
    return "".join(o)


def screen_d4():
    o = [d_base(), d_head("Ditt øyeblikk", "Uke 11")]
    deg = net_deg(0, 13)
    o.append(vu(12, 64, 366, 168, deg, cowl_net(0, 13, 36), cowlh=50, numsize=13, bezel=6, major=[10, 20, 40, 60]))
    fr = [(a, b, "fast") for a, b in arrivals("Grossist", 11)] + [(15, 24, "bestilt")]
    o.append(tape(10, 244, 370, 62, fr))
    yy = 330
    o.append(t(14, yy, "Du så", 20, "c", IV, w=800))
    s, yy = para(70, yy, "13 i restordre, 0 på lager, 8 i innkommende ordre. 16 på vei.", 306, 16.5, "b", IV, 1.28)
    o.append(s)
    yy += 8
    o.append(t(14, yy, "Du bestilte", 20, "c", IV, w=800))
    o.append(t(110, yy + 1, "24", 28, "c", IV, w=800))
    yy += 30
    s_ = WK[35]["seats"]["Grossist"]["kost_sum"] - WK[10]["seats"]["Grossist"]["kost_sum"]
    o.append(t(14, yy, "Det kostet senere", 20, "c", IV, w=800))
    s, yy = para(14, yy + 22, f"{kr(s_)} kr av setets 553,50 kr kom etter denne uka. I Uke 29 lå det 30 kasser på lageret ditt.", 362, 16.5, "b", IV, 1.28)
    o.append(s)
    yy += 8
    o.append(t(14, yy, "De andre så, samme uke", 20, "c", IV, w=800))
    rows = [("Ida", "Detaljist", "4 i restordre, 8 inn"), ("Mikkel", "Distributør", "14 på lager, 4 inn"), ("Jonas", "Fabrikk", "9 på lager, 5 inn")]
    yy += 8
    for n, r, v in rows:
        o.append(rect(12, yy, 366, 28, STL0, 2))
        o.append(t(22, yy + 20, n, 16, "c", IV, w=700))
        o.append(t(74, yy + 20, r, 15, "c", IVD, w=500))
        o.append(t(368, yy + 20, v, 16, "c", IV, "end", 500))
        yy += 31
    s, yy = para(14, yy + 18, "24-tallet nådde Mikkel i Uke 13: fra 12 på lager til 7 i restordre. Mikkel så en ordre, ikke grunnen.", 362, 16, "b", IV, 1.28)
    o.append(s)
    o.append(ki_tag(12, yy - 6))
    o.append(btn(12, 784, 366, 48, "Til Debrief-quiz", "p", 21))
    return "".join(o)


def screen_d5():
    o = [d_base(), d_head("Debrief-quiz", "Spørsmål 2")]
    s, yy = para(14, 90, "Kunden gikk fra 4 til 8. Hvorfor ble utslaget størst hos Fabrikk?", 362, 23, "c", IV, 1.2, 800)
    o.append(s)
    opts = [("Fabrikk reagerte dårligere enn de andre", "feil"),
            ("Hvert ledd ser bare ordrene fra leddet foran, og forsinkelsen legger nye ordrer oppå gamle", "riktig"),
            ("Kundene kjøpte mer mot slutten", "nøytral")]
    yy += 2
    for lab, kind in opts:
        lines = wrap(lab, 300, 17, "b")
        h = 22 * len(lines) + 24
        fill = IV if kind == "riktig" else STL0
        col = INK if kind == "riktig" else IV
        o.append(rect(12, yy, 366, h, fill, 3, f'stroke="{IV if kind != "nøytral" else STL2}" stroke-width="{2 if kind == "feil" else 1}"'))
        if kind == "feil":
            o.append(line(30, yy + h / 2 - 8, 46, yy + h / 2 + 8, IV, 3) + line(46, yy + h / 2 - 8, 30, yy + h / 2 + 8, IV, 3))
        elif kind == "riktig":
            o.append(f'<path d="M28,{yy + h / 2:.1f} l7,8 l13,-16" fill="none" stroke="{INK}" stroke-width="3.2" stroke-linecap="round"/>')
        else:
            o.append(circ(38, yy + h / 2, 7, "none", f'stroke="{IVD}" stroke-width="2"'))
        for k, ln in enumerate(lines):
            o.append(t(62, yy + 23 + k * 22, ln, 17, "b", col))
        yy += h + 8
    o.append(t(14, yy + 22, "Du valgte det første. Det er feil.", 20, "c", IV, w=800))
    expl = ("Dette handler om struktur, ikke om hvem som satt i setet. Fabrikk ligger lengst fra kunden, med flest ledd mellom seg og den ene endringen. "
            "Se sporene: hvert ledd sender videre et større utslag enn det selv fikk.")
    s, yy = para(14, yy + 48, expl, 362, 16.5, "b", IV, 1.32)
    o.append(s)
    o.append(ki_tag(12, yy - 4))
    o.append(t(14, yy + 42, "Quizen teller ikke. Du kan prøve igjen.", 16, "b", IVD))
    o.append(btn(12, 772, 366, 56, "Prøv på nytt", "p", 23))
    return "".join(o)


def seq_text(x, y, vals, size, f, fill, a, w, start, step, dur, static):
    """Tall som bytter uke for uke under avspilling. static vises i hvile."""
    o = []
    a0 = start / dur
    a1 = (start + step * len(vals)) / dur
    o.append(f'<text x="{x:.1f}" y="{y:.1f}" class="c08-{f}" font-size="{size}" fill="{fill}" text-anchor="{a}" font-weight="{w}">'
             f'<animate attributeName="opacity" values="1;0;1" keyTimes="0;{a0:.4f};{a1:.4f}" calcMode="discrete" dur="{dur}s" repeatCount="indefinite"/>{escape(str(static))}</text>')
    for i, v in enumerate(vals):
        k0 = (start + step * i) / dur
        k1 = (start + step * (i + 1)) / dur
        o.append(f'<text x="{x:.1f}" y="{y:.1f}" class="c08-{f}" font-size="{size}" fill="{fill}" text-anchor="{a}" font-weight="{w}" opacity="0">'
                 f'<animate attributeName="opacity" values="0;1;0" keyTimes="0;{k0:.4f};{k1:.4f}" calcMode="discrete" dur="{dur}s" repeatCount="indefinite"/>{escape(str(v))}</text>')
    return "".join(o)


def play_anim(degs, static, px, py, start, step, dur):
    vals = [static, static] + degs + [static, static]
    tms = [0, start] + [start + step * (i + .5) for i in range(len(degs))] + [start + step * len(degs) + .4, dur]
    kt = ";".join(f"{a / dur:.4f}" for a in tms)
    vs = ";".join(f"{v:.2f} {px:.2f} {py:.2f}" for v in vals)
    return f'<animateTransform attributeName="transform" type="rotate" values="{vs}" keyTimes="{kt}" dur="{dur}s" repeatCount="indefinite"/>'


def shared_screen(x, y, w, h):
    o = [wood(x, y, w, h, 6)]
    o.append(t(x + 28, y + 48, "Hele broen åpnes", 40, "c", IV, w=800))
    o.append(t(x + 30, y + 76, "Delt skjerm i Gruppedebrief. Bare felles kart, aldri den enkeltes øyeblikk.", 17, "c", IV, w=500))
    start, step, dur = 5.0, .5, 26.0
    # transport
    tx = x + w - 520
    o.append(steel(tx, y + 18, 492, 66, 4, True))
    o.append(t(tx + 16, y + 45, "Uke", 16, "c", IVD, w=500))
    o.append(seq_text(tx + 16, y + 75, [str(i + 1) for i in range(36)], 30, "c", IV, "start", 800, start, step, dur, "18"))
    o.append(btn(tx + 74, y + 28, 150, 46, "", "p"))
    o.append(poly([(tx + 92, y + 40), (tx + 92, y + 62), (tx + 110, y + 51)], INK))
    o.append(t(tx + 120, y + 58, "Spill av", 20, "c", INK, w=700))
    o.append(btn(tx + 234, y + 28, 110, 46, "Pause", "s", 18))
    o.append(btn(tx + 354, y + 28, 124, 46, "Vis tabell", "s", 18))
    # fem maalere
    cols = 5
    gap = 22
    mw = (w - 56 - gap * (cols - 1)) / cols
    mh = 188
    my = y + 100
    wk18 = WK[17]["seats"]
    for i in range(cols):
        mx = x + 28 + i * (mw + gap)
        if i == 0:
            deg = ang(4)
            py = my + mh - 40 * .3
            degs = [ang(wk["demand"] - 4) for wk in WK]
            cap = "Kunde"
            sub = "etterspørsel, endring fra 4"
            def _c(px, cy, w_, ch, x_):
                return t(px, cy + ch * .66, "+4", 28, "c", IV, "middle", 800)
            o.append(vu(mx, my, mw, mh, deg, _c, left="", right="", red=False, cowlh=40, numsize=13,
                        anim=play_anim(degs, deg, mx + mw / 2, py, start, step, dur)))
            tape_vals = [wk["demand"] for wk in WK]
        else:
            r = ROLES[i - 1]
            s_ = wk18[r]
            deg = net_deg(s_["lager"], s_["restordre"])
            py = my + mh - 40 * .3
            degs = [net_deg(wk["seats"][r]["lager"], wk["seats"][r]["restordre"]) for wk in WK]
            cap = r
            sub = f"forsterkning {FX['amplification'][r]:.1f}×".replace(".", ",")
            o.append(vu(mx, my, mw, mh, deg, None, left="", right="", cowlh=40, numsize=13,
                        anim=play_anim(degs, deg, mx + mw / 2, py, start, step, dur)))
            vals = []
            for wk in WK:
                q = wk["seats"][r]
                vals.append(f'{q["restordre"]} restordre' if q["restordre"] else f'{q["lager"]} på lager')
            o.append(seq_text(mx + mw / 2, my + mh - 8, vals, 22, "c", IV, "middle", 800, start, step, dur, f'{s_["restordre"]} restordre'))
            tape_vals = [wk["seats"][r]["ordre"] for wk in WK]
        # bånd under: ordre per uke, samme skala
        ty = my + mh + 12
        o.append(t(mx, ty + 16, cap, 21, "c", IV, w=800))
        o.append(t(mx + mw, ty + 16, sub, 16, "c", IV, "end", 500))
        by = ty + 24
        bh = 70
        o.append(rect(mx - 7, by, mw + 14, bh, "#F7F1DF", 2))
        bw = (mw + 6) / 36
        pxu = (bh - 6) / 32
        for j, v in enumerate(tape_vals):
            if v:
                o.append(rect(mx - 3 + j * bw + .3, by + bh - 2 - v * pxu, max(.8, bw - .6), v * pxu, INK))
        # lesehode, uke 18 i hvile
        hx = mx - 3 + 17.5 * bw
        o.append(f'<line x1="{hx:.1f}" y1="{by:.1f}" x2="{hx:.1f}" y2="{by + bh:.1f}" stroke="{STL2}" stroke-width="2">'
                 f'<animate attributeName="x1" values="{hx:.1f};{hx:.1f};{mx - 3:.1f};{mx - 3 + 36 * bw:.1f};{hx:.1f};{hx:.1f}" keyTimes="0;{start / dur:.4f};{(start + .01) / dur:.4f};{(start + 18) / dur:.4f};{(start + 18.01) / dur:.4f};1" dur="{dur}s" repeatCount="indefinite"/>'
                 f'<animate attributeName="x2" values="{hx:.1f};{hx:.1f};{mx - 3:.1f};{mx - 3 + 36 * bw:.1f};{hx:.1f};{hx:.1f}" keyTimes="0;{start / dur:.4f};{(start + .01) / dur:.4f};{(start + 18) / dur:.4f};{(start + 18.01) / dur:.4f};1" dur="{dur}s" repeatCount="indefinite"/></line>')
    return "".join(o)


def p07():
    o = [rect(0, 0, 2100, 1200, STL1, 0, f'filter="{U("steelf")}"')]
    o.append(t(40, 46, "Debrief: først dine ord, så kundens måler, så hele broen", 36, "c", IV, w=800))
    o.append(demo(2060, 46, "end", IV, 17))
    s = .72
    pw = 390 * s
    gap = (2100 - 80 - 5 * pw) / 4
    y0 = 106
    caps = [("1. Skriv Forklaring", "Avsløringen er låst"), ("2. Etterspørselen avsløres", "Klimaks"), ("3. Ordrer per Rolle", "1,8× til 7,6×"),
            ("4. Ditt øyeblikk", "Uke 11, på egen skjerm"), ("5. Quiz", "Feil svar forklares")]
    screens = [screen_d1(), screen_d2(), screen_d3(), screen_d4(), screen_d5()]
    for i, sc in enumerate(screens):
        x = 40 + i * (pw + gap)
        o.append(t(x - 6, y0 - 26, caps[i][0], 24, "c", IV, w=800))
        o.append(t(x + pw + 6, y0 - 26, caps[i][1], 17, "c", IVD, "end", 500))
        o.append(phone(x, y0, s, sc))
        if i < 4:
            ax = x + pw + gap / 2 - 14
            ay = y0 + 300
            o.append(poly([(ax, ay - 18), (ax + 28, ay), (ax, ay + 18)], IV))
    o.append(shared_screen(40, 736, 2020, 440))
    return "".join(o)


# =========================================================
# 01 LANDING
# =========================================================
def ministrip(x, y, w, h, g):
    st = g["status"]
    live = st != "ferdig"
    o = [rect(x + .5, y, w - 1, h, "#2E3336" if live else "#1B1E20", 1)]
    mh = w * .8
    cid = uid("m")
    px, py = x + w / 2, y + 2 + mh + 2
    R = mh - 3
    deg = teacher_deg(g_kpw(g))
    o.append(f'<clipPath id="{cid}"><rect x="{x + 1.5:.1f}" y="{y + 2:.1f}" width="{w - 3:.1f}" height="{mh:.1f}"/></clipPath><g clip-path="url(#{cid})">')
    o.append(rect(x + 1.5, y + 2, w - 3, mh, U("face") if live else U("faced")))
    if deg > 0:
        o.append(f'<path d="{arc(px, py, R - 2, 0, deg)}" fill="none" stroke="{RED if live else "#8A3A2C"}" stroke-width="4"/>')
    o.append(needle_g(px, py, R, deg, "", .8, INK, False))
    o.append("</g>")
    cy = y + 2 + mh + 12
    if st == "venter":
        o.append(rect(x + 2, y + 2 + mh + 3, w - 4, h - mh - 7, U("hamb") if g.get("ventet_timer", 0) >= 20 else AMB, 1))
    elif st == "pauset":
        o.append(rect(x + w / 2 - 4, cy - 5, 3, 10, IV) + rect(x + w / 2 + 1, cy - 5, 3, 10, IV))
    elif st == "pågår":
        o.append(circ(x + w / 2, cy, 4, GRN))
    if g["ki_seter"] and st != "venter":
        s = 4.5
        o.append(poly([(px, y + h - 12 - s), (px + s, y + h - 12), (px, y + h - 12 + s), (px - s, y + h - 12)], KIC))
    return "".join(o)


def p01():
    o = [wood(0, 0, 1440, 1200)]
    # nav
    o.append(steel(0, 0, 1440, 64, 0, True))
    o.append(t(40, 41, "METERBROEN", 22, "m", IV))
    o.append(t(1140, 40, "Logg inn", 18, "c", IV, "end", 600))
    o.append(btn(1170, 13, 230, 40, "Be om lærertilgang", "p", 19))
    # hero tekst
    o.append(t(80, 164, "Hold 60 spill på sporet", 74, "c", IV, w=800))
    o.append(t(80, 238, "uten å bli dommer.", 74, "c", IV, w=800))
    s, yy = para(82, 292, "Fire studenter styrer hvert sitt ledd i en forsyningskjede, med ett tall per uke. Alt annet regner systemet. Du følger hele klassen på én skjerm, fra Invitasjon til PDF-rapport.", 540, 21, "b", IV, 1.42)
    o.append(s)
    o.append(btn(82, yy + 18, 290, 64, "Be om lærertilgang", "p", 25))
    o.append(t(398, yy + 58, "Logg inn", 22, "c", IV, w=600))
    o.append(line(398, yy + 64, 398 + 66, yy + 64, IV, 1.5))
    o.append(t(82, yy + 118, "Tilgang gis av oss. Studenter kommer inn med Invitasjon.", 16, "b", IVD))
    # hero maler
    mx, my, mw, mh = 720, 110, 620, 310
    deg = net_deg(0, 13)
    py = my + mh - mh * .29 * .3
    o.append(vu(mx, my, mw, mh, deg, cowl_net(0, 13, 60), anim=swing(net_deg(0, 9), deg, mx + mw / 2, py), numsize=18))
    fr = [(a, b, "fast") for a, b in arrivals("Grossist", 11)] + [(15, 24, "ventende")]
    o.append(t(mx - 7, my + mh + 36, "På vei 16", 22, "c", IV, w=800))
    o.append(t(mx + mw + 7, my + mh + 36, "med ordren: 40", 18, "c", IV, "end", 600))
    o.append(tape(mx - 7, my + mh + 44, mw + 14, 74, fr, numsize=26))
    o.append(t(mx - 7, my + mh + 146, "Det studenten ser: sin egen nål, sitt eget bånd, ett tall å sette.", 18, "c", IV, w=500))
    # broen
    by = 618
    o.append(steel(0, by, 1440, 216, 0, True))
    o.append(t(40, by + 40, "Det du ser: 60 Klassespill i én rekke.", 30, "c", IV, w=800))
    o.append(t(1400, by + 34, "Demodata", 15, "c", IV, "end", 500))
    bx, bw = 40, 1360
    w = bw / 60
    sy = by + 58
    o.append(rect(bx - 4, sy - 4, bw + 8, 74, "#0F1112", 2))
    for i, g in enumerate(GAMES):
        o.append(ministrip(bx + i * w, sy, w, 66, g))
    o.append(line(bx + 1 * w + w / 2, sy + 66, bx + 1 * w + w / 2, sy + 90, IV, 1.5))
    o.append(t(bx + 1 * w - 8, sy + 110, "Spill 2 venter på Noah i 23 t. KI-spiller tar setet om 1 t, så gruppa kommer videre.", 18, "c", IV, w=500))
    o.append(t(1400, sy + 110, "Mørk flate: ferdig. Lys flate: pågår. Ravfarget: venter. Rute: KI-spiller.", 17, "c", IVD, "end", 500))
    # neste seksjon
    ny = 866
    o.append(t(80, ny + 44, "Ett fravær stopper ikke gruppa.", 50, "c", IV, w=800))
    s, yy2 = para(82, ny + 88, "Når et sete står tomt for lenge tar en merket KI-spiller over, og studenten kan ta setet tilbake. Grupper kan pause og avtale når de fortsetter. Ingen spill blir stående uferdig.", 520, 19, "b", IV, 1.4)
    o.append(s)
    # fire lys
    lx, ly = 720, ny + 18
    o.append(panel(lx - 7, ly, 634, 180, 4, STL0))
    items = [("Detaljist", "Ida", "har bestilt", "ok"), ("Grossist", "Sara", "har bestilt", "ok"), ("Distributør", "Mikkel", "har bestilt", "ok"), ("Fabrikk", "KI-spiller", "tok setet etter 24 t", "ki")]
    cw = 634 / 4
    for i, (r, n, st_, k) in enumerate(items):
        cx = lx - 7 + i * cw + cw / 2
        o.append(lamp(cx, ly + 46, 19, k))
        o.append(t(cx, ly + 96, r, 21, "c", IV, "middle", 800))
        o.append(t(cx, ly + 120, n, 18, "c", IV, "middle", 500))
        o.append(t(cx, ly + 146, st_, 16, "c", IVD, "middle", 500))
    # veien, tape
    ty = ny + 222
    o.append(t(80, ty + 8, "Hele øvelsen ligger på samme bånd", 28, "c", IV, w=800))
    o.append(t(1360, ty + 8, "På norsk. Spilles på mobil. For klasser på rundt 250 studenter.", 18, "c", IVD, "end", 500))
    stations = ["Canvas-eksport", "Invitasjon", "Klassespill", "Debrief", "Quiz", "Replay", "Individuell test", "PDF-rapport"]
    tx, tw_ = 80, 1280
    fw = tw_ / len(stations)
    o.append(rect(tx - 6, ty + 22, tw_ + 12, 78, STL0, 3))
    for i, st_ in enumerate(stations):
        fx = tx + i * fw
        o.append(rect(fx + 1, ty + 28, fw - 2, 66, PAPER, 1))
        o.append(t(fx + fw / 2, ty + 62, st_, 21, "c", INK, "middle", 700))
        for j in range(12):
            o.append(circ(fx + 12 + j * (fw - 24) / 11, ty + 82, 2, INK))
    return "".join(o)


# =========================================================
# 02 KLASSE
# =========================================================
def field(x, y, w, label, val, h=46, editable=True):
    o = [t(x, y, label, 16, "c", IVD, w=500)]
    o.append(rect(x, y + 7, w, h, U("face"), 2, f'stroke="{STL3}" stroke-width="1"'))
    o.append(t(x + 12, y + 7 + h / 2 + 7, val, 21, "c", INK, w=600))
    return "".join(o)


def p02():
    o = [rect(0, 0, 1440, 1000, STL1, 0, f'filter="{U("steelf")}"')]
    o.append(wood(0, 0, 1440, 76))
    o.append(t(36, 50, "Ny Klasse", 38, "c", IV, w=800))
    o.append(t(1404, 44, "Faglærer Bård. Demodata", 16, "c", IV, "end", 500))
    # venstre kol
    lx, lw = 36, 400
    o.append(panel(lx, 94, lw, 200))
    o.append(field(lx + 16, 124, lw - 32, "Navn på Klassen", "class-of-1994"))
    o.append(field(lx + 16, 206, lw - 32, "Emnekode", "IBE160"))
    # fil
    o.append(panel(lx, 306, lw, 112))
    o.append(rect(lx + 16, 320, 42, 54, PAPER, 2))
    o.append(poly([(lx + 46, 320), (lx + 58, 332), (lx + 46, 332)], "#B9B3A0"))
    o.append(t(lx + 70, 340, "ibe160-canvas-eksport.xlsx", 20, "c", IV, w=700))
    o.append(t(lx + 70, 364, "250 rader lest. 4 ugyldige adresser.", 17, "c", IVD, w=500))
    o.append(btn(lx + 16, 380, 150, 30, "Bytt fil", "s", 15))
    # status / send
    o.append(panel(lx, 430, lw, 546))
    o.append(t(lx + 16, 462, "Invitasjoner", 26, "c", IV, w=800))
    o.append(t(lx + 16, 486, "Gyldig i 14 dager", 16, "c", IVD, w=500))
    bars = [("Sendt", 246, 250, "bar"), ("Akseptert", 238, 250, "ok"), ("Venter svar", 5, 250, "wait"), ("Utløpt", 3, 250, "exp")]
    yy = 508
    for lab, v, m, k in bars:
        o.append(t(lx + 16, yy + 21, lab, 18, "c", IV, w=600))
        o.append(rect(lx + 108, yy + 4, 230, 24, "#000", 1))
        if k == "exp":
            o.append(rect(lx + 108, yy + 4, max(3, 230 * v / m), 24, U("hsteel"), 1, f'stroke="{IV}" stroke-width="1"'))
        else:
            o.append(rect(lx + 108, yy + 4, max(3, 230 * v / m), 24, IV if k in ("bar", "ok") else AMB, 1))
        o.append(t(lx + lw - 14, yy + 24, v, 23, "c", IV, "end", 800))
        yy += 40
    o.append(line(lx + 16, yy + 6, lx + lw - 16, yy + 6, STL2, 1))
    yy += 40
    o.append(t(lx + 16, yy, "Registrering, 250 på lista", 19, "c", IV, w=700))
    yy += 26
    for lab, v in (("Registrert via Invitasjon", 238), ("Manuelt registrert", 2), ("Uregistrert", 10)):
        o.append(t(lx + 16, yy, lab, 17, "c", IV, w=500))
        o.append(t(lx + lw - 14, yy, v, 20, "c", IV, "end", 700))
        yy += 25
    yy += 8
    o.append(btn(lx + 16, yy, lw - 32, 58, "Send Invitasjoner på nytt til 3 utløpte", "p", 20))
    yy += 72
    o.append(btn(lx + 16, yy, lw - 32, 44, "Legg til student manuelt", "s", 18))
    # hoyre kol: patch
    rx, rw = 454, 950
    o.append(panel(rx, 94, rw, 370))
    o.append(t(rx + 18, 128, "Hvilken kolonne er e-post?", 26, "c", IV, w=800))
    o.append(t(rx + rw - 18, 128, "Vi foreslo den som ligner mest på adresser", 16, "c", IVD, "end", 500))
    cols = [("Navn", 170), ("Studentnr", 100), ("E-post", 270), ("Seksjon", 110), ("Sist aktiv", 110)]
    cx = rx + 18
    ty = 146
    selx = None
    rows = [("Berg, Emma", "204411", "emma.berg@stud.example.no", "Gruppe A", "3. nov"),
            ("Dahl, Noah", "204412", "noah.dahl@stud.example.no", "Gruppe A", "5. nov"),
            ("Eide, Sara", "204413", "sara.eide@stud.example.no", "Gruppe B", "4. nov"),
            ("Foss, Ida", "204414", "ida.foss@stud.example.no", "Gruppe B", "5. nov")]
    tablew = sum(c[1] for c in cols)
    for i, (nm, cw) in enumerate(cols):
        sel = nm == "E-post"
        # jack
        jx = cx + cw / 2
        if sel:
            selx = jx
        o.append(rect(cx, ty, cw - 4, 36, IV if sel else STL0, 2, f'stroke="{STL2}"'))
        o.append(t(cx + 10, ty + 25, nm, 18, "c", INK if sel else IV, w=700))
        for r, row in enumerate(rows):
            ry = ty + 40 + r * 30
            o.append(rect(cx, ry, cw - 4, 28, "#F7F1DF" if sel else "#1F2326", 1))
            o.append(t(cx + 10, ry + 20, row[i], 17, "c", INK if sel else IVD, w=500))
        # jack-hull
        o.append(circ(jx, ty + 186, 9, "#000", f'stroke="{IV if sel else STL3}" stroke-width="2.5"'))
        cx += cw
    # patchkabel til Invitasjon
    jack_x = rx + rw - 96
    o.append(f'<path d="M{selx:.1f},{ty + 186:.1f} C{selx + 60:.1f},{ty + 280:.1f} {jack_x - 120:.1f},{ty + 280:.1f} {jack_x:.1f},{ty + 186:.1f}" fill="none" stroke="{IV}" stroke-width="5" stroke-linecap="round"/>')
    o.append(circ(selx, ty + 186, 6, IV))
    o.append(circ(jack_x, ty + 186, 12, IV, f'stroke="{STL3}" stroke-width="2"'))
    o.append(t(jack_x, ty + 158, "Invitasjon", 18, "c", IV, "middle", 700))
    o.append(t(jack_x, ty + 136, "246 adresser", 17, "c", IVD, "middle", 500))
    s_, yy_ = para(rx + 18, ty + 224, "Kabelen viser valget: kolonnen E-post går til Invitasjon. Dra den til en annen kolonne for å bytte.", 380, 17, "c", IVD, 1.25, 500)
    o.append(s_)
    o.append(t(rx + 18, yy_ + 4, "Filen ble lest med kolonnenavn i rad 1.", 16, "c", IVD))
    # ugyldige
    uy = 476
    o.append(panel(rx, uy, rw, 300))
    o.append(t(rx + 18, uy + 34, "4 ugyldige adresser", 26, "c", IV, w=800))
    o.append(t(rx + rw - 18, uy + 34, "De andre 246 er sendt", 16, "c", IVD, "end", 500))
    inv = [(37, "Haugen, Mathias", "mathias.haugen@stud", "Mangler domene", "ok"), (88, "Lie, Aurora", "aurora.lie@@stud.example.no", "To @-tegn", "ok"),
           (141, "Moe, Filip", "filip moe@stud.example.no", "Mellomrom i adressen", "open"), (203, "Vik, Selma", "(tomt felt)", "Tom celle", "open")]
    yy = uy + 50
    for row, nm, addr, why, k in inv:
        o.append(rect(rx + 14, yy, rw - 28, 52, "#1F2326", 2))
        o.append(rect(rx + 22, yy + 9, 70, 34, AMB if k == "open" else PAPER, 1))
        o.append(t(rx + 57, yy + 33, f"Rad {row}", 18, "c", INK, "middle", 800))
        o.append(t(rx + 106, yy + 23, nm, 18, "c", IV, w=700))
        o.append(t(rx + 106, yy + 43, why, 16, "c", IVD, w=500))
        o.append(rect(rx + 290, yy + 9, 340, 34, U("face"), 2))
        o.append(t(rx + 300, yy + 33, addr, 18, "c", INK, w=500))
        if k == "ok":
            o.append(lamp(rx + 658, yy + 26, 10, "ok"))
            o.append(t(rx + 676, yy + 32, "Manuelt registrert", 17, "c", IV, w=600))
        else:
            o.append(btn(rx + 650, yy + 9, 130, 34, "Rett adresse", "s", 16))
            o.append(btn(rx + 790, yy + 9, 136, 34, "Registrer manuelt", "s", 16))
        yy += 58
    # send
    sy = 788
    o.append(panel(rx, sy, rw, 188))
    o.append(t(rx + 18, sy + 34, "Status for hele lista", 24, "c", IV, w=800))
    # linjal med 250 rader delt i segmenter til skala
    bx, bw = rx + 18, rw - 36
    segs = [("Sendt og akseptert", 238, IV), ("Manuelt", 2, PAPER), ("Venter", 5, AMB), ("Utløpt", 3, "#6D7478"), ("Ugyldig", 2, "#000")]
    cx = bx
    o.append(rect(bx, sy + 48, bw, 34, "#000", 1))
    for lab, v, col in segs:
        wd = bw * v / 250
        o.append(rect(cx, sy + 48, max(2, wd - 1), 34, col, 0))
        cx += wd
    o.append(t(bx, sy + 106, "238 akseptert", 18, "c", IV, w=700))
    o.append(t(bx + bw, sy + 106, "2 manuelt, 5 venter, 3 utløpt, 2 ugyldige gjenstår", 18, "c", IV, "end", 500))
    o.append(t(bx, sy + 134, "Stripen har 250 rader til skala, én pr. student på lista.", 16, "c", IVD))
    o.append(btn(bx + bw - 300, sy + 124, 300, 52, "Send påminnelse til 5 som venter", "p", 18))
    return "".join(o)


# =========================================================
# 03 KLASSEOKT
# =========================================================
def knob(cx, cy, r, frac):
    deg = -135 + 270 * frac
    o = []
    for i in range(11):
        d = -135 + 27 * i
        x0, y0 = pt(cx, cy, r + 4, d)
        x1, y1 = pt(cx, cy, r + 9, d)
        o.append(line(x0, y0, x1, y1, IVD, 1.2))
    o.append(circ(cx, cy + 2, r, "#000", 'opacity=".5"'))
    o.append(circ(cx, cy, r, U("knob"), 'stroke="#000" stroke-width="1"'))
    x0, y0 = pt(cx, cy, r * .3, deg)
    x1, y1 = pt(cx, cy, r * .92, deg)
    o.append(line(x0, y0, x1, y1, IV, 3, 'stroke-linecap="round"'))
    return "".join(o)


def p03():
    o = [rect(0, 0, 1440, 1100, STL1, 0, f'filter="{U("steelf")}"')]
    o.append(wood(0, 0, 1440, 78))
    o.append(t(36, 50, "Klasseøkt: IBE160, class-of-1994", 36, "c", IV, w=800))
    o.append(t(760, 50, "240 studenter. Alt er forhåndsutfylt.", 19, "c", IVD, w=500))
    o.append(btn(1118, 14, 290, 50, "Lagre uten endring", "p", 23))
    # kanaler
    sx, sw = 24, 946
    o.append(panel(sx, 92, sw, 446, 4, "#1B1F21"))
    o.append(t(sx + 16, 124, "Spillinnstillinger", 26, "c", IV, w=800))
    o.append(rect(sx + 216, 100, 134, 32, IV, 2))
    o.append(t(sx + 283, 123, "Klassisk", 20, "c", INK, "middle", 800))
    o.append(t(sx + 362, 123, "Standard. Gjelder alle 60 spill.", 17, "c", IVD, w=500))
    ch = [("Startlager", "12", "kasser", 12 / 24), ("I hvert ledd", "4", "enheter", 4 / 12), ("Ordre-", "2", "uker", 2 / 6), ("Frakt-", "2", "uker", 2 / 6), ("Produksjons-", "2", "uker", 2 / 6),
          ("Etterspørsel", "4 til 8", "i uke 5", .33), ("Lagerkost", "0,50", "kr/kasse", .25), ("Restordrekost", "1,00", "kr/kasse", .5), ("Antall uker", "36", "skjult for student", .72), ("Veiledede", "1–4", "uker", .11)]
    sub2 = {"Ordre-": "forsinkelse", "Frakt-": "forsinkelse", "Produksjons-": "forsinkelse", "Veiledede": "uker"}
    cw = (sw - 24) / len(ch)
    cy0 = 142
    for i, (lab, val, unit, fr) in enumerate(ch):
        cx = sx + 12 + i * cw
        o.append(rect(cx + 2, cy0, cw - 4, 248, "#2E3336", 2, 'stroke="#000"'))
        o.append(rect(cx + 6, cy0 + 4, cw - 12, 44, PAPER, 1))
        o.append(t(cx + cw / 2, cy0 + 22, lab, 15, "c", INK, "middle", 700))
        o.append(t(cx + cw / 2, cy0 + 40, sub2.get(lab, ""), 15, "c", INK, "middle", 700))
        o.append(knob(cx + cw / 2, cy0 + 96, 24, fr))
        o.append(rect(cx + 7, cy0 + 144, cw - 14, 54, U("face"), 2))
        o.append(t(cx + cw / 2, cy0 + 182, val, 30 if len(val) < 5 else 24, "c", INK, "middle", 800))
        for j, ln in enumerate(wrap(unit, cw - 10, 15, "c")):
            o.append(t(cx + cw / 2, cy0 + 216 + j * 16, ln, 15, "c", IVD, "middle", 500))
    s, _ = para(sx + 16, cy0 + 272, "Kildene er uenige om forsinkelsene i øvelsen. Dette er produktets standard: 2 uker i hvert ledd. Du kan endre, og endringen gjelder alle Klassespill. Et testspill viser hva innstillingene gjør.", sw - 40, 18, "b", IV, 1.36)
    o.append(s)
    o.append(btn(sx + 16, cy0 + 336, 190, 44, "Kjør testspill", "s", 18))
    o.append(btn(sx + 216, cy0 + 336, 240, 44, "Tilbake til Klassisk", "s", 18))
    # hoyre: moder
    rx, rw = 984, 432
    o.append(panel(rx, 92, rw, 446, 4, "#1B1F21"))
    def seg(y, label, opts, on):
        oo = [t(rx + 16, y, label, 19, "c", IV, w=700)]
        w_ = (rw - 32) / len(opts)
        for i, op in enumerate(opts):
            sel = i == on
            oo.append(rect(rx + 16 + i * w_, y + 8, w_ - 3, 44, IV if sel else STL1, 2, f'stroke="{IV if sel else STL2}"'))
            oo.append(t(rx + 16 + i * w_ + w_ / 2, y + 37, op, 18, "c", INK if sel else IV, "middle", 700 if sel else 500))
        return "".join(oo)
    o.append(seg(124, "KI-modus", ["LLM-spillere", "Regelbaserte"], 0))
    o.append(seg(206, "Debrief-modus", ["Gruppedebrief", "Personlig debrief"], 0))
    # obligatorisk bryter
    o.append(t(rx + 16, 292, "Obligatorisk", 19, "c", IV, w=700))
    o.append(rect(rx + 16, 302, 58, 38, "#000", 3, f'stroke="{STL3}"'))
    o.append(rect(rx + 44, 305, 27, 32, U("cap"), 2))
    o.append(t(rx + 86, 327, "På. Alle steg må fullføres.", 18, "c", IV, w=500))
    o.append(t(rx + 16, 376, "Inaktivitetsgrense", 19, "c", IV, w=700))
    o.append(rect(rx + 16, 386, 90, 44, U("face"), 2))
    o.append(t(rx + 61, 417, "24 t", 28, "c", INK, "middle", 800))
    s, _ = para(rx + 120, 404, "KI overtar et sete når andre har ventet så lenge.", rw - 136, 17, "c", IVD, 1.2, 500)
    o.append(s)
    o.append(t(rx + 16, 470, "KI-spillere fyller alltid tomme seter og er merket.", 18, "c", IV, w=500))
    o.append(lamp(rx + 30, 500, 10, "ki"))
    o.append(t(rx + 50, 506, "Slik ser merket ut for studentene.", 17, "c", IVD, w=500))
    # datoer paa tape, til skala
    dy = 552
    o.append(panel(24, dy, 1392, 200, 4, "#1B1F21"))
    o.append(t(40, dy + 32, "Datoer og Labtimer", 26, "c", IV, w=800))
    o.append(t(1400, dy + 32, "Båndet er til skala, én rute per dag", 16, "c", IVD, "end", 500))
    # dager fra 24. nov til 18. des: 25 dager
    bx, bw = 40, 1360
    days = 25
    dw = bw / days
    ty = dy + 46
    o.append(rect(bx, ty, bw, 66, PAPER, 2))
    weekday = ["ti", "on", "to", "fr", "lø", "sø", "ma"]
    for i in range(days):
        x = bx + i * dw
        o.append(line(x, ty, x, ty + 66, "#B9B3A0", 1))
        n = 24 + i if i <= 6 else i - 6
        o.append(t(x + dw / 2, ty + 20, weekday[i % 7], 15, "c", INK, "middle", 500))
        o.append(t(x + dw / 2, ty + 42, n, 18, "c", INK, "middle", 700))
    labs = [2, 6, 9, 13]  # 26. nov, 30. nov, 3. des, 7. des
    for l in labs:
        x = bx + l * dw
        for k in range(3):
            o.append(circ(x + dw / 2 - 10 + k * 10, ty + 55, 3.4, INK))
    marks = [(0, "Start", "ti. 24. nov"), (14, "Spillfrist", "ti. 8. des"), (17, "Debrief-frist", "fr. 11. des"), (24, "Testfrist", "fr. 18. des")]
    for i_, a, b in marks:
        x = bx + i_ * dw + dw / 2
        o.append(poly([(x - 8, ty + 74), (x + 8, ty + 74), (x, ty + 64)], IV))
        anc = "end" if i_ == 24 else ("start" if i_ == 0 else "middle")
        xx = x + (12 if i_ == 24 else (-12 if i_ == 0 else 0))
        o.append(t(xx, ty + 94, a, 19, "c", IV, anc, 800))
        o.append(t(xx, ty + 114, b, 17, "c", IVD, anc, 500))
    o.append(t(bx + 2 * dw + 40, ty + 94, "Tre hull = Labtime, Datalab A2", 17, "c", IV, w=700))
    o.append(t(bx + 2 * dw + 40, ty + 114, "to. 26. nov 14:15, ma. 30. nov 10:15, to. 3. des 14:15, ma. 7. des 10:15", 16, "c", IVD, w=500))
    # fordeling
    fy = 766
    o.append(panel(24, fy, 1392, 320, 4, "#1B1F21"))
    o.append(t(40, fy + 34, "Fordeling: 240 studenter i 60 spill à 4", 26, "c", IV, w=800))
    o.append(t(40, fy + 58, "Tilfeldig. Hver stripe er ett Klassespill med fire seter. Trykk en stripe for å se navn.", 17, "c", IVD, w=500))
    o.append(btn(1020, fy + 14, 180, 46, "Kjør på nytt", "s", 19))
    o.append(btn(1210, fy + 14, 192, 46, "Bekreft fordeling", "p", 20))
    w = 1360 / 30
    for row in range(2):
        for i in range(30):
            n = row * 30 + i + 1
            x = 40 + i * w
            y = fy + 76 + row * 88
            sel = n == 17
            o.append(rect(x + 1.5, y, w - 3, 80, "#2E3336", 2, f'stroke="{IV if sel else "#000"}" stroke-width="{2.5 if sel else 1}"'))
            o.append(rect(x + 4, y + 3, w - 8, 22, PAPER, 1))
            o.append(t(x + w / 2, y + 20, n, 16, "c", INK, "middle", 800))
            for j in range(4):
                cx = x + w / 2 + (-9 if j % 2 == 0 else 9)
                cy = y + 40 + (j // 2) * 22
                o.append(circ(cx, cy, 7, IV))
    ry = fy + 76 + 2 * 88 + 2
    o.append(t(40, ry + 22, "Spill 17:", 19, "c", IV, w=800))
    o.append(t(112, ry + 22, "Ida, Detaljist.  Sara, Grossist.  Mikkel, Distributør.  Jonas, Fabrikk.", 19, "c", IV, w=500))
    o.append(t(1402, ry + 22, "Demodata", 15, "c", IVD, "end"))
    return "".join(o)


# =========================================================
# 04 STUDENT-HJEM
# =========================================================
def screen_register():
    o = [wood(0, 0, 390, 844)]
    o.append(t(195, 44, "METERBROEN", 19, "m", IV, "middle"))
    o.append(rect(0, 64, 390, 780, STL1, 0, f'filter="{U("steelf")}"'))
    o.append(t(16, 108, "Bård har invitert deg", 32, "c", IV, w=800))
    s, yy = para(16, 136, "Klasse class-of-1994, IBE160. Invitasjonen gjelder i 14 dager.", 356, 17, "b", IV)
    o.append(s)
    yy += 14
    o.append(field(16, yy, 358, "E-post, fra klasselista", "sara.eide@stud.example.no", 48))
    yy += 80
    o.append(field(16, yy, 358, "Navn", "Sara Eide", 48))
    yy += 80
    o.append(field(16, yy, 358, "Velg passord", "••••••••••", 48))
    yy += 74
    o.append(btn(16, yy, 358, 60, "Opprett konto", "p", 24))
    yy += 108
    o.append(t(16, yy, "Dette skal du gjøre", 22, "c", IV, w=800))
    yy += 8
    # liten maaler
    o.append(vu(22, yy + 8, 150, 110, net_deg(12, 0), None, left="", right="", cowlh=14, numsize=13, bezel=5, screws=False, major=[10, 40]))
    s, y2 = para(190, yy + 22, "Du får ett sete i en kjede med fire. Hver uke setter du ett tall. Systemet regner resten.", 186, 16, "b", IV, 1.28)
    o.append(s)
    yy += 142
    s, _ = para(16, yy, "Klassespillet åpner ti. 24. nov. Du får Rolle og gruppe før det.", 356, 17, "b", IVD)
    o.append(s)
    o.append(t(374, 824, "Demodata", 13, "c", IVD, "end"))
    return "".join(o)


def screen_home():
    d = WK[10]["seats"]["Grossist"]
    o = [wood(0, 0, 390, 844), rect(0, 54, 390, 790, STL1, 0, f'filter="{U("steelf")}"')]
    o.append(t(16, 38, "Hei, Sara", 28, "c", IV, w=800))
    o.append(t(374, 34, "IBE160", 17, "c", IVD, "end", 500))
    # venter
    o.append(rect(12, 64, 366, 112, AMB, 4))
    o.append(lamp(38, 94, 15, "wait"))
    o.append(t(62, 94, "Spillet venter på deg", 27, "c", INK, w=800))
    o.append(t(62, 112, "Uke 11. Ida og Mikkel har bestilt.", 15.5, "c", INK, w=600))
    o.append(rect(24, 124, 342, 44, INK, 3))
    o.append(t(195, 153, "Sett ordren din", 22, "c", IV, "middle", 700))
    # spill og rolle
    o.append(panel(12, 184, 366, 176, 4, STL0))
    o.append(t(26, 214, "Spill 17", 25, "c", IV, w=800))
    o.append(t(26, 238, "Du er Grossist", 18, "c", IV, w=500))
    o.append(vu(214, 196, 150, 106, net_deg(0, 13), None, left="", right="", cowlh=14, numsize=13, bezel=5, screws=False, major=[10, 40]))
    o.append(t(214, 322, "13 restordre", 17, "c", IV, w=700))
    o.append(t(214, 342, "68,00 kr", 16, "c", IVD, w=500))
    seats = [("Ida", "Detaljist", "ok"), ("Mikkel", "Distributør", "ok"), ("Jonas", "Fabrikk", "wait")]
    yy = 262
    for n, r, k in seats:
        o.append(lamp(34, yy, 8, k))
        o.append(t(50, yy + 5, n, 16, "c", IV, w=700))
        o.append(t(98, yy + 5, r, 15, "c", IVD, w=500))
        yy += 29
    # steg
    o.append(t(14, 388, "Seks steg", 21, "c", IV, w=800))
    steps = [("Klassespill", "pågår", "Spillfrist ti. 8. des", "run"), ("Debrief", "etter spillet", "Frist fr. 11. des", "lock"), ("Quiz", "etter Debrief", "", "lock"),
             ("Replay", "etter Quiz", "", "lock"), ("Individuell test", "etter Replay", "Frist fr. 18. des", "lock"), ("Rapport", "PDF til slutt", "", "lock")]
    yy = 398
    for i, (n, s_, dl, k) in enumerate(steps):
        on = i == 0
        o.append(rect(12, yy, 366, 31, "#3A4044" if on else STL0, 2))
        o.append(lamp(30, yy + 15.5, 8 if on else 7, k))
        o.append(t(46, yy + 21, n, 17, "c", IV, w=700 if on else 500))
        o.append(t(146, yy + 21, s_, 15, "c", IVD, w=500))
        o.append(t(370, yy + 21, dl, 15, "c", IV if on else IVD, "end", 600 if on else 400))
        yy += 34
    # frist + lab
    yy += 6
    o.append(t(14, yy + 16, "Neste frist", 18, "c", IVD, w=500))
    o.append(t(376, yy + 16, "Spillfrist ti. 8. des", 22, "c", IV, "end", 800))
    yy += 34
    o.append(t(14, yy + 14, "Labtimer, Datalab A2", 19, "c", IV, w=800))
    yy += 22
    labs = [("to. 26. nov", "14:15"), ("ma. 30. nov", "10:15"), ("to. 3. des", "14:15"), ("ma. 7. des", "10:15")]
    fw = 366 / 4
    o.append(rect(12, yy, 366, 62, STL0, 3))
    for i, (a, b) in enumerate(labs):
        x = 14 + i * fw
        o.append(rect(x + 1, yy + 3, fw - 4, 56, PAPER, 1))
        o.append(t(x + fw / 2 - 1, yy + 24, a, 14.5, "c", INK, "middle", 700))
        o.append(t(x + fw / 2 - 1, yy + 46, b, 17, "c", INK, "middle", 600))
    yy += 80
    o.append(t(14, yy, "Du ser ikke hvor lenge spillet varer. Det er meningen.", 15.5, "b", IVD))
    o.append(t(376, 834, "Demodata", 13, "c", IVD, "end"))
    return "".join(o)


def p04():
    o = [wood(0, 0, 1000, 900)]
    o.append(t(46, 24, "Første møte: registrering fra Invitasjon", 18, "c", IV, w=600))
    o.append(t(564, 24, "Hjem under spill", 18, "c", IV, w=600))
    o.append(phone(46, 44, 1.0, screen_register()))
    o.append(phone(564, 44, 1.0, screen_home()))
    return "".join(o)


# =========================================================
# 09 ALLE SIDER
# =========================================================
def mini_lines(x, y, w, n=3, col=IVD, gap=11):
    return "".join(rect(x, y + i * gap, w * (1 - .16 * (i % 3)), 4, col, 1, 'opacity=".55"') for i in range(n))


def mini_phone(x, y, h, inner_fn):
    w = h * .5
    return (rect(x, y, w, h, "#0E1011", 5, f'stroke="{STL3}" stroke-width="1"') + inner_fn(x + 3, y + 3, w - 6, h - 6))


def sk_form(x, y, w, h, rows=3, cta=True):
    o = []
    for i in range(rows):
        o.append(rect(x, y + i * 22, w, 16, IV, 1))
    if cta:
        o.append(rect(x, y + rows * 22 + 4, w, 20, IV2, 2, f'stroke="{IV}"'))
    return "".join(o)


def sk_meter(x, y, w, h, deg):
    return vu(x, y, w, h, deg, None, left="", right="", cowlh=8, bezel=0, screws=False, numsize=8, major=[10, 40], minor=[])


def sk_strips(x, y, w, h, n=20, games=None):
    o = []
    cw = w / n
    for i in range(n):
        g = (games or GAMES)[i % 60]
        o.append(ministrip(x + i * cw, y, cw, h, g))
    return "".join(o)


def sk_tape(x, y, w, h, vals):
    o = [rect(x, y, w, h, STL0, 1)]
    fw = (w - 4) / len(vals)
    for i, v in enumerate(vals):
        o.append(rect(x + 2 + i * fw + .5, y + 2, fw - 1, h - 4, PAPER, 1))
        for j in range(min(v, 12)):
            o.append(circ(x + 2 + i * fw + 3 + (j % 6) * (fw - 6) / 6, y + 6 + (j // 6) * 5, 1.2, INK))
    return "".join(o)


def sk_table(x, y, w, h, cols=4, rows=5):
    o = [rect(x, y, w, h, "#1F2326", 1)]
    rh = h / rows
    for r in range(rows):
        for c in range(cols):
            cw = w / cols
            o.append(rect(x + 4 + c * cw, y + r * rh + rh * .3, cw * .7, rh * .36, IV if r == 0 else IVD, 1, f'opacity="{1 if r == 0 else .55}"'))
    return "".join(o)


def sk_lanes(x, y, w, h):
    o = []
    laneh = h / 4 - 2
    for i, r in enumerate(ROLES):
        yy = y + i * (laneh + 2)
        o.append(rect(x, yy, w, laneh, "#F7F1DF", 1))
        bw = w / 36
        for j, wk in enumerate(WK):
            v = wk["seats"][r]["ordre"]
            o.append(rect(x + j * bw, yy + laneh - v / 32 * laneh, max(.6, bw - .4), v / 32 * laneh, INK))
    return "".join(o)


def sk_bars(x, y, w, h, vals, maxv):
    bw = w / len(vals)
    o = [rect(x, y, w, h, "#1F2326", 1)]
    for i, v in enumerate(vals):
        bh = (h - 4) * v / maxv
        o.append(rect(x + i * bw + 2, y + h - 2 - bh, bw - 4, bh, IV))
    return "".join(o)


def tiles():
    def nm(lager, rest):
        return net_deg(lager, rest)
    S = {}
    S["Invitasjon og registrering"] = ("Lenke fra e-post, navn og passord. E-post er låst.", lambda x, y, w, h: sk_form(x, y, w * .6, h))
    S["Logg inn"] = ("E-post og passord. Tilbake dit du var.", lambda x, y, w, h: sk_form(x + w * .2, y + 14, w * .6, h, 2))
    S["Regler før første ordre"] = ("Nålen, båndet og faderen forklart på ett skjermbilde. Uke 1 til 4 er Veiledede uker.", lambda x, y, w, h: sk_meter(x, y, w * .5, h, nm(12, 0)) + sk_tape(x + w * .54, y, w * .46, 34, [4, 4, 4]) + mini_lines(x + w * .54, y + 44, w * .46))
    S["Startoppgave"] = ("Prøv faderen uten at det teller. Du setter ett tall og ser nålen svinge.", lambda x, y, w, h: sk_meter(x, y, w, h * .62, nm(8, 0)) + rect(x + 6, y + h * .78, w - 12, 4, "#000") + rect(x + w * .3, y + h * .68, 14, 26, U("cap"), 1))
    S["Replay"] = ("Samme kanal, tre KI-spillere merket med rute. Du spiller alene.", lambda x, y, w, h: sk_meter(x, y, w * .62, h, nm(0, 20)) + "".join(lamp(x + w * .72 + i * 20, y + 24, 8, "ki") for i in range(3)) + mini_lines(x + w * .66, y + 50, w * .34))
    S["Replay-gjennomgang"] = ("Kort KI-tekst om kjøringen din, sammenlignet med Klassespillet. Merket.", lambda x, y, w, h: sk_lanes(x, y, w * .58, h) + lamp(x + w * .7, y + 16, 8, "ki") + mini_lines(x + w * .64, y + 36, w * .36))
    S["Individuell test"] = ("Flervalg, tegn et lagerforløp eller fyll tabell, og langsvar. Fortsett senere.", lambda x, y, w, h: (
        "".join(circ(x + 8, y + 10 + i * 18, 5, "none", f'stroke="{IV}" stroke-width="1.5"') + rect(x + 20, y + 8 + i * 18, w * .2, 4, IVD) for i in range(3)) +
        rect(x + w * .36, y, w * .32, h, "#F7F1DF", 1) + f'<path d="M{x + w * .38:.1f},{y + h * .3:.1f} q{w * .08:.1f},{h * .6:.1f} {w * .14:.1f},{h * .3:.1f} t{w * .13:.1f},{-h * .2:.1f}" fill="none" stroke="{INK}" stroke-width="2"/>' +
        rect(x + w * .72, y, w * .28, h, U("face"), 1) + mini_lines(x + w * .75, y + 10, w * .22, 5, INK)))
    S["KI-vurdering"] = ("Teller ikke, er ingen karakter. Står øverst, med rute. Peker på egne svar.", lambda x, y, w, h: lamp(x + 14, y + 14, 9, "ki") + rect(x + 34, y + 8, w * .7, 14, KIC, 1) + mini_lines(x, y + 36, w, 5))
    S["Studentrapport (PDF)"] = ("Egen nål gjennom spillet, Forklaring, øyeblikk og KI-merking. Last ned.", lambda x, y, w, h: rect(x + w * .3, y, w * .4, h, PAPER, 1) + sk_lanes(x + w * .33, y + 6, w * .34, h * .4) + mini_lines(x + w * .33, y + h * .55, w * .34, 4, INK))
    S["Alle spill side om side"] = ("Etter Debrief: hele klassens broer, uten navn. Ingen rangering.", lambda x, y, w, h: sk_strips(x, y, w, h * .7, 24))
    F = {}
    F["Lærerhjem med klasser"] = ("Hver Klasse som en egen bro med neste frist og antall som venter.", lambda x, y, w, h: "".join(sk_strips(x, y + i * (h / 2), w * .7, h / 2 - 5, 18, GAMES[i * 10:]) + mini_lines(x + w * .74, y + i * (h / 2) + 6, w * .26, 2) for i in range(2)))
    F["Klasserapport"] = ("Fullføring per student, trakt, eksport til Canvas. PDF.", lambda x, y, w, h: sk_table(x, y, w * .55, h) + sk_bars(x + w * .6, y, w * .4, h, [240, 164, 121, 97, 58, 12], 240))
    F["Spillinnsikt (uke for uke)"] = ("Fire nåler og tape for ett spill, KI-uker merket, loggen under.", lambda x, y, w, h: "".join(sk_meter(x + i * (w / 4), y, w / 4 - 4, h * .5, nm(0, [16, 38, 43, 54][i])) for i in range(4)) + sk_lanes(x, y + h * .56, w, h * .44))
    F["Studentside"] = ("Én student: steg, ordrer, Forklaring, Melding, justeringer.", lambda x, y, w, h: sk_meter(x, y, w * .36, h * .7, nm(0, 13)) + "".join(lamp(x + w * .46, y + 10 + i * 19, 6, "ok" if i == 0 else "lock") + rect(x + w * .52, y + 8 + i * 19, w * .4, 4, IVD) for i in range(6)))
    F["Spill alle side om side for plenum"] = ("Hele broen på lerretet, uten navn. Kost per spill kan slås av.", lambda x, y, w, h: sk_strips(x, y, w, h * .46, 30, GAMES) + sk_strips(x, y + h * .52, w, h * .46, 30, GAMES[30:]))
    F["Tverrklasse-statistikk"] = ("Samme mål over Klasser og år, til samme skala.", lambda x, y, w, h: "".join(sk_bars(x + i * (w / 3), y, w / 3 - 6, h, [1.8, 4.1, 6.0, 7.6], 8) for i in range(3)))
    F["Meldinger"] = ("Til én, til alle som venter, eller hele Klassen. Ingen chat mellom studenter.", lambda x, y, w, h: sk_table(x, y, w * .4, h, 1, 5) + rect(x + w * .44, y, w * .56, h - 26, U("face"), 1) + mini_lines(x + w * .47, y + 10, w * .48, 4, INK) + rect(x + w * .72, y + h - 20, w * .28, 20, IV2, 2))
    F["Lærers testspill"] = ("Spill selv med egne innstillinger, tre KI-spillere. Teller ikke.", lambda x, y, w, h: sk_meter(x, y, w * .56, h, nm(4, 0)) + "".join(lamp(x + w * .66 + i * 20, y + 20, 8, "ki") for i in range(3)) + rect(x + w * .62, y + 50, w * .36, 20, IV2, 2))
    A = {}
    A["Admin-område"] = ("Klasser, spillstatus og revisjonslogg på tvers.", lambda x, y, w, h: sk_table(x, y, w, h, 5, 5))
    A["Brukere og roller"] = ("Gi lærertilgang, assistenter, kontostatus. Alt logges.", lambda x, y, w, h: sk_table(x, y, w * .7, h, 3, 5) + rect(x + w * .74, y, w * .26, 24, IV2, 2))
    A["KI-kostnad"] = ("Forbruk per Klasse og modell mot taket, med tak-måler.", lambda x, y, w, h: sk_meter(x, y, w * .38, h, ang(-10)) + sk_bars(x + w * .42, y, w * .58, h, [3, 5, 8, 13, 9, 6, 11, 4], 13))
    return S, F, A


def p09():
    o = [wood(0, 0, 2000, 1400)]
    o.append(t(40, 52, "Alle andre sider på samme bro", 40, "c", IV, w=800))
    o.append(t(1960, 48, "Lav detalj. Skissene bruker nål, tape og stripe. Demodata.", 18, "c", IV, "end", 500))
    S, F, A = tiles()
    def row(y, items, h):
        n = len(items)
        x0 = 170
        gap = 14
        w = (2000 - x0 - 30 - gap * (n - 1)) / n
        oo = []
        for i, (title, (line_, fn)) in enumerate(items):
            x = x0 + i * (w + gap)
            oo.append(panel(x, y, w, h, 4, STL1))
            oo.append(rect(x, y, w, h, "none", 4, f'stroke="{STL2}"'))
            ty = y + 30
            lines_t = wrap(title, w - 28, 22, "c")
            for j, ln in enumerate(lines_t[:2]):
                oo.append(t(x + 14, ty + j * 24, ln, 22, "c", IV, w=800))
            ty += (len(lines_t[:2]) - 1) * 24
            s_, yy = para(x + 14, ty + 22, line_, w - 28, 15.5, "b", IVD, 1.28)
            oo.append(s_)
            sk_y = y + 112
            oo.append(fn(x + 14, sk_y, w - 28, h - 112 - 14))
        return "".join(oo)
    S_i, F_i, A_i = list(S.items()), list(F.items()), list(A.items())
    y = 74
    rh = 248
    gaps = 10
    def role_plate(y_, h_, label):
        return (steel(30, y_, 126, h_, 3, True) + screw(44, y_ + 14, 3.5) + screw(142, y_ + 14, 3.5, 70) + screw(44, y_ + h_ - 14, 3.5) + screw(142, y_ + h_ - 14, 3.5, 70) +
                t(93, y_ + h_ / 2 + 8, label, 13.5, "m", IV, "middle"))
    o.append(role_plate(y, rh * 2 + gaps, "STUDENT"))
    o.append(row(y, S_i[:5], rh))
    o.append(row(y + rh + gaps, S_i[5:], rh))
    y2 = y + 2 * (rh + gaps) + 6
    o.append(role_plate(y2, rh * 2 + gaps, "FAGLÆRER"))
    o.append(row(y2, F_i[:4], rh))
    o.append(row(y2 + rh + gaps, F_i[4:], rh))
    y3 = y2 + 2 * (rh + gaps) + 6
    o.append(role_plate(y3, 1400 - y3 - 12, "ADMIN"))
    o.append(row(y3, A_i, 1400 - y3 - 12))
    return "".join(o)


if __name__ == "__main__":
    page("landing", "01-landing.svg", 1440, 1200, "Meterbroen: landingsside for faglærere",
         "Offentlig landingsside. Stor VU-måler med bånd som viser hva en student ser, og en rekke med 60 kanalstriper som viser hva faglæreren ser.", p01)
    page("klasse", "02-laerer-klasse.svg", 1440, 1000, "Meterbroen: faglærer lager Klasse",
         "Navn og emnekode, Canvas-fil, e-postkolonne valgt med patchkabel, ugyldige rader per rad, Invitasjoner med status til skala.", p02)
    page("spill", "03-laerer-spill.svg", 1440, 1100, "Meterbroen: faglærer setter opp Klasseøkt",
         "Forhåndsutfylte standarder som kanalrekke med knapper, KI-modus, Debrief-modus, Obligatorisk, datoer på bånd til skala og fordelingsforhåndsvisning.", p03)
    page("hjem", "04-student-hjem.svg", 1000, 900, "Meterbroen: studenten på mobil",
         "To telefoner: registrering fra Invitasjon, og hjem under spill med Spill 17, seter, seks steg, frist og Labtimer.", p04)
    page("spillskjerm", "05-spill.svg", 1600, 1000, "Meterbroen: spillskjermen i Uke 11",
         "Sara, Grossist. VU-måler med nålen i det røde på 13 restordre, bånd med 16 på vei, fader på 24, og samme skjerm på laptop.", p05)
    page("dynamikk", "06-spilldynamikk.svg", 2100, 1200, "Meterbroen: spilldynamikk i seks ruter",
         "Uka åpner, beslutningen, bekreftet, uka går videre med nålesving, KI-spiller tar setet, og spillet slutter med kjedens totalkostnad.", p06)
    page("debrief", "07-debrief.svg", 2100, 1200, "Meterbroen: Gruppedebrief i fem steg og delt skjerm",
         "Forklaring før avsløring, kundens måler fra 4 til 8, ordrer per Rolle, ditt øyeblikk i Uke 11, quiz, og delt skjerm der hele broen spilles av.", p07)
    page("oversikt", "08-laerer-oversikt.svg", 1600, 1000, "Meterbroen: Oversikt over 60 Klassespill",
         "Lang bro med 60 identiske kanalstriper i to rekker. Hver nål er til skala. Venter, Pause, KI-seter og nær overtakelse har egen form. Åpen kanal og trakt under.", p08)
    page("alle", "09-alle-sider.svg", 2000, 1400, "Meterbroen: kontaktark over alle andre sider",
         "Skisser av alle øvrige sider gruppert per rolle: Student, Faglærer og Admin.", p09)
    print("OK")
