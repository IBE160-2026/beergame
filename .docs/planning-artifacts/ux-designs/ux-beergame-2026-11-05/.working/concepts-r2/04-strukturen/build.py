"""Konsept 04 Strukturen. Genererer 10 SVG-er fra ../_shared/fixture.json.

Kjør: uv run python build.py [navn ...]
Alle tall i grafer leses fra fixturen. Felles byggeklosser: beholdning, strøm med ventil,
informasjonspil, forsinkelsesmerke og hjelpelinje. Verdier festes alltid til en node.
"""
import json
import math
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
F = json.loads((HERE.parent / "_shared" / "fixture.json").read_text(encoding="utf-8"))
ROLES = ["Detaljist", "Grossist", "Distributør", "Fabrikk"]
PEOPLE = {"Detaljist": "Ida", "Grossist": "Sara", "Distributør": "Mikkel", "Fabrikk": "Jonas"}
S17 = F["spill17"]["serier"]
SIM1 = F["bare_sara_teller_paa_vei"]["serier"]
SIM2 = F["alle_teller_paa_vei"]["serier"]
REPLAY = F["replay_sara"]["serier"]

# Palett
CANVAS = "#D8D9D5"   # betong, lerret
SCREEN = "#E8E8E4"   # betong, lys: grunn på skjerm
PAPER = "#F4F4F1"    # innsiden av en beholdning
INK = "#15181B"      # nær-svart linje og tekst
MUTED = "#484C50"    # sekundær tekst
HAIR = "#A9ABA7"     # hjelpelinje
GRID = "#CDCEC9"     # rutenett
BLUE = "#2F5F85"     # strøm
RED = "#B3241A"      # aktivt signal: nå og tilbakekobling
STOCK = "#2B2E32"    # fyll i beholdning

FONT = "'Red Hat Text','Segoe UI','Helvetica Neue',Arial,sans-serif"
MONO = "'Red Hat Mono','Cascadia Mono',Consolas,monospace"
SIDE = "x"
_uid = [0]


def uid():
    _uid[0] += 1
    return f"d04-{SIDE}-u{_uid[0]}"


# ---------- tall ----------
def nb(v, d=2):
    s = f"{v:,.{d}f}".replace(",", " ").replace(".", ",")
    return s


def kr(v):
    return nb(v, 2) + " kr"


def xf(v):
    return f"{v:.1f}".replace(".", ",") + "×"


def wk(u, role="Grossist", run=None):
    """Verdier for en Rolle ved Uke u (1-basert). På vei er før ukas ordre."""
    run = run or S17
    r = run[role]
    i = u - 1
    prev = r["restordre"][i - 1] if i > 0 else 0
    sendt = prev + r["innkommende_ordre"][i] - r["restordre"][i]
    return dict(u=u, lager=r["lager"][i], rest=r["restordre"][i], inn=r["innkommende_ordre"][i],
                lev=r["levering"][i], pv=r["paa_vei"][i], ordre=r["ordre"][i], sendt=sendt,
                kost=r["kost_sum"][i], kostuke=r["kost_sum"][i] - (r["kost_sum"][i - 1] if i > 0 else 0),
                pos=r["lager"][i] - r["restordre"][i] + r["paa_vei"][i])


def net(run, role, u=None):
    r = run[role]
    n = [a - b for a, b in zip(r["lager"], r["restordre"])]
    return n[:u] if u else n


# Materialbalansen er selve poenget, så build.py nekter å tegne hvis den ikke stemmer.
_w11 = wk(11)
assert (_w11["lager"], _w11["rest"], _w11["inn"], _w11["lev"], _w11["sendt"], _w11["pv"], _w11["kost"]) == (0, 13, 8, 4, 4, 16, 68)
assert _w11["pos"] == 3 and _w11["pos"] + 24 == 27 and _w11["ordre"] == 24
for _t in range(1, 36):
    _n = net(S17, "Grossist")
    assert _n[_t] - _n[_t - 1] == S17["Grossist"]["levering"][_t] - S17["Grossist"]["innkommende_ordre"][_t]


# ---------- tegneprimitiver ----------
def t(x, y, s, size=14, fill=INK, w=400, a="start", mono=False, extra=""):
    cls = "d04-m" if mono else "d04-t"
    return (f'<text class="{cls}" x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{w}" '
            f'fill="{fill}" text-anchor="{a}"{(" " + extra) if extra else ""}>{escape(str(s))}</text>')


def rich(x, y, parts, a="start"):
    """parts: liste av (tekst, size, fill, vekt, mono)."""
    out = [f'<text class="d04-t" x="{x:.1f}" y="{y:.1f}" text-anchor="{a}">']
    for s, size, fill, w, mono in parts:
        cls = ' class="d04-m"' if mono else ""
        out.append(f'<tspan{cls} font-size="{size}" font-weight="{w}" fill="{fill}">{escape(str(s))}</tspan>')
    out.append("</text>")
    return "".join(out)


def nv(x, y, name, val, a="start", size=13, vsize=15, vfill=INK, nfill=MUTED):
    """Navn + målt verdi på én linje. Verdien i mono."""
    return rich(x, y, [(name + " ", size, nfill, 400, False), (val, vsize, vfill, 600, True)], a)


def wrap(s, width, size, f=0.525):
    words, lines, cur = str(s).split(), [], ""
    for wd in words:
        test = (cur + " " + wd).strip()
        if len(test) * size * f > width and cur:
            lines.append(cur)
            cur = wd
        else:
            cur = test
    if cur:
        lines.append(cur)
    return lines


def para(x, y, s, width, size=14, lh=None, fill=INK, w=400, a="start"):
    lh = lh or size * 1.42
    return "".join(t(x, y + i * lh, ln, size, fill, w, a) for i, ln in enumerate(wrap(s, width, size, 0.525 + (0.015 if w >= 600 else 0))))


def para_h(s, width, size=14, lh=None, w=400):
    lh = lh or size * 1.42
    return len(wrap(s, width, size, 0.525 + (0.015 if w >= 600 else 0))) * lh


def ln(x1, y1, x2, y2, c=INK, w=1.0, extra=""):
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{c}" stroke-width="{w}"{(" " + extra) if extra else ""}/>'


def rect(x, y, w, h, fill="none", stroke="none", sw=1.0, rx=0, extra=""):
    h = max(h, 0)
    rxs = f' rx="{rx}"' if rx else ""
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="{sw}"{rxs}{(" " + extra) if extra else ""}/>')


def path(d, fill="none", stroke=INK, sw=1.0, extra=""):
    return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{(" " + extra) if extra else ""}/>'


def circ(x, y, r, fill="none", stroke=INK, sw=1.0):
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'


def group(body, tx=0, ty=0, s=1.0):
    return f'<g transform="translate({tx:.1f} {ty:.1f}) scale({s})">{body}</g>'


def leader(x1, y1, x2, y2, dot=True):
    """Tynn hjelpelinje fra node til verdi. Prikken sitter på noden."""
    return ln(x1, y1, x2, y2, HAIR, 1) + (circ(x1, y1, 1.8, INK, "none", 0) if dot else "")


def head(x, y, ang, size=6, fill=INK):
    a1, a2 = ang + math.radians(152), ang - math.radians(152)
    return (f'<path d="M{x:.1f},{y:.1f} L{x + size * math.cos(a1):.1f},{y + size * math.sin(a1):.1f} '
            f'L{x + size * math.cos(a2):.1f},{y + size * math.sin(a2):.1f} Z" fill="{fill}" stroke="none"/>')


def info(x1, y1, x2, y2, bend=0, c=INK, w=1.1, size=6):
    """Tynn buet informasjonspil."""
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy) or 1
    cx, cy = mx - dy / L * bend, my + dx / L * bend
    ang = math.atan2(y2 - cy, x2 - cx)
    return path(f"M{x1:.1f},{y1:.1f} Q{cx:.1f},{cy:.1f} {x2:.1f},{y2:.1f}", "none", c, w) + head(x2, y2, ang, size, c)


def cloud(x, y, c=INK, k=1.0):
    """Kilde eller sluk: det som ligger utenfor det du styrer."""
    d = (f"M{x - 7 * k:.1f},{y + 3 * k:.1f} a{3.2 * k:.1f},{3.2 * k:.1f} 0 0 1 {1.2 * k:.1f},{-6 * k:.1f} "
         f"a{3.6 * k:.1f},{3.6 * k:.1f} 0 0 1 {6.6 * k:.1f},{-1.4 * k:.1f} a{3.2 * k:.1f},{3.2 * k:.1f} 0 0 1 {5 * k:.1f},{3 * k:.1f} "
         f"a{2.8 * k:.1f},{2.8 * k:.1f} 0 0 1 {-0.8 * k:.1f},{4.4 * k:.1f} Z")
    return path(d, SCREEN, c, 1)


def pipe_h(x1, x2, y, val, unit, arrow=True, c=BLUE, edge=INK):
    """Dobbel pil. Tykkelsen er ukas strøm på samme skala som beholdningen."""
    th = max(3.0, val * unit)
    d = 1 if x2 > x1 else -1
    xe = x2 - d * 7 if arrow else x2
    o = rect(min(x1, xe), y - th / 2, abs(xe - x1), th, c if val > 0 else SCREEN)
    o += ln(x1, y - th / 2, xe, y - th / 2, edge, 1.1) + ln(x1, y + th / 2, xe, y + th / 2, edge, 1.1)
    if arrow:
        hw = th / 2 + 3.5
        o += path(f"M{xe:.1f},{y - hw:.1f} L{x2:.1f},{y:.1f} L{xe:.1f},{y + hw:.1f} Z", c if val > 0 else SCREEN, edge, 1.1)
    return o


def pipe_v(x, y1, y2, val, unit, arrow=True, c=BLUE, edge=INK):
    th = max(3.0, val * unit)
    d = 1 if y2 > y1 else -1
    ye = y2 - d * 7 if arrow else y2
    o = rect(x - th / 2, min(y1, ye), th, abs(ye - y1), c if val > 0 else SCREEN)
    o += ln(x - th / 2, y1, x - th / 2, ye, edge, 1.1) + ln(x + th / 2, y1, x + th / 2, ye, edge, 1.1)
    if arrow:
        hw = th / 2 + 3.5
        o += path(f"M{x - hw:.1f},{ye:.1f} L{x:.1f},{y2:.1f} L{x + hw:.1f},{ye:.1f} Z", c if val > 0 else SCREEN, edge, 1.1)
    return o


def valve(x, y, th=6, vertical=False, c=INK, fill=None):
    h = max(8.0, th / 2 + 3.5)
    w = 6.5
    fill = fill or SCREEN
    if vertical:
        return path(f"M{x - h:.1f},{y - w} L{x + h:.1f},{y + w} L{x - h:.1f},{y + w} L{x + h:.1f},{y - w} Z", fill, c, 1.2)
    return path(f"M{x - w},{y - h:.1f} L{x + w},{y + h:.1f} L{x + w},{y - h:.1f} L{x - w},{y + h:.1f} Z", fill, c, 1.2)


def delay(x, y, h=9, c=INK):
    return ln(x - 4, y + h, x - 1, y - h, c, 1.3) + ln(x + 1, y + h, x + 4, y - h, c, 1.3)


def box_up(x, base, w, val, unit, frame, extra=0, hatch=None, ticks=True, fill=STOCK):
    h = max(frame, (val + extra) * unit)
    o = rect(x, base - h, w, h, PAPER)
    o += rect(x, base - val * unit, w, val * unit, fill)
    if extra:
        o += rect(x, base - (val + extra) * unit, w, extra * unit, f"url(#d04-{SIDE}-{hatch or 'hr'})")
        o += ln(x, base - val * unit, x + w, base - val * unit, RED if (hatch or "hr") == "hr" else INK, 1)
    o += rect(x, base - h, w, h, "none", INK, 1.4)
    if ticks:
        for v in range(10, int((val + extra)) + 1, 10):
            o += ln(x - 3, base - v * unit, x, base - v * unit, INK, 0.9)
    return o


def box_down(x, base, w, val, unit, frame, ticks=True):
    h = max(frame, val * unit)
    o = rect(x, base, w, h, PAPER) + rect(x, base, w, val * unit, STOCK) + rect(x, base, w, h, "none", INK, 1.4)
    if ticks:
        for v in range(10, int(val) + 1, 10):
            o += ln(x - 3, base + v * unit, x, base + v * unit, INK, 0.9)
    return o


def diagram(x0, base, W, u, unit=1.5, role="Grossist", run=None, order="done", typed=None, fs=13, vs=15,
            labels=True, loop=False, delaytxt=True, posval=None, rail=None):
    """Setets stock-and-flow-tegning ved Uke u.

    order: 'typed' tastet men ikke bekreftet (rødt, skravert), 'done' bekreftet, 'open' ikke tastet.
    Returnerer (svg, geo). Skala: 1 enhet = unit px i boks og i rørtykkelse.
    """
    d = wk(u, role, run)
    o_val = typed if typed is not None else d["ordre"]
    if order == "open":
        o_val = 0
    v0, b1, bw, v1, b2, v2, end = x0 + .068 * W, x0 + .164 * W, .203 * W, x0 + .463 * W, x0 + .559 * W, x0 + .864 * W, x0 + W
    hmin = 30 * unit
    yc, yr = base - hmin / 2, base + hmin / 2
    cb = b2 + bw / 2
    src = base + 40 * unit + 34 * (unit / 1.5)
    rb = base + 3 + max(hmin - 3, d["rest"] * unit)
    vy = (rb + src) / 2
    out = []
    out.append(ln(x0, base, end, base, HAIR, 1))
    # Strømmer
    out.append(cloud(x0 + 5, yc))
    th = max(3.0, o_val * unit)
    pcol = BLUE
    if order == "typed":
        out.append(rect(x0 + 13, yc - th / 2, b1 - x0 - 20, th, f"url(#d04-{SIDE}-hr)"))
        out.append(ln(x0 + 13, yc - th / 2, b1 - 7, yc - th / 2, RED, 1.1) + ln(x0 + 13, yc + th / 2, b1 - 7, yc + th / 2, RED, 1.1))
        hw = th / 2 + 3.5
        out.append(path(f"M{b1 - 7:.1f},{yc - hw:.1f} L{b1:.1f},{yc:.1f} L{b1 - 7:.1f},{yc + hw:.1f} Z", SCREEN, RED, 1.1))
        out.append(valve(v0, yc, th, c=RED))
    else:
        out.append(pipe_h(x0 + 13, b1, yc, o_val, unit))
        out.append(valve(v0, yc, th))
    out.append(pipe_h(b1 + bw, b2, yc, d["lev"], unit))
    out.append(valve(v1, yc, d["lev"] * unit))
    out.append(delay(v1 + (b2 - v1) * .42, yc, max(8, d["lev"] * unit / 2 + 5)))
    out.append(pipe_h(b2 + bw, end - 11, yc, d["sendt"], unit))
    out.append(valve(v2, yc, d["sendt"] * unit))
    out.append(cloud(end - 3, yc))
    out.append(pipe_h(b2 + bw, end - 11, yr, d["sendt"], unit))
    out.append(valve(v2, yr, d["sendt"] * unit))
    out.append(cloud(end - 3, yr))
    out.append(info(v2, yc + max(8, d["sendt"] * unit / 2 + 3.5) + 1, v2, yr - max(8, d["sendt"] * unit / 2 + 3.5) - 1, 0, INK, 1, 5))
    out.append(cloud(cb, src + 8))
    out.append(pipe_v(cb, src, rb, d["inn"], unit))
    out.append(valve(cb, vy, d["inn"] * unit, vertical=True))
    # Beholdninger
    ext = o_val if order != "open" else 0
    if order == "typed":
        out.append(box_up(b1, base, bw, d["pv"], unit, hmin, ext, "hr"))
    elif order == "done":
        out.append(box_up(b1, base, bw, d["pv"] + ext, unit, hmin))
    else:
        out.append(box_up(b1, base, bw, d["pv"], unit, hmin))
    out.append(box_up(b2, base - 3, bw, d["lager"], unit, hmin - 3))
    out.append(box_down(b2, base + 3, bw, d["rest"], unit, hmin - 3))
    tot = d["pv"] + ext
    b1top = base - max(hmin, tot * unit)
    b2top = base - 3 - max(hmin - 3, d["lager"] * unit)
    geo = dict(v0=v0, yc=yc, yr=yr, b1=b1, bw=bw, v1=v1, b2=b2, v2=v2, cb=cb, vy=vy, end=end, src=src, th=th, b1top=b1top,
               b2top=b2top, base=base, rb=rb, hmin=hmin)
    if labels:
        ofill = RED if order == "typed" else INK
        rl = rail if rail is not None else min(b1top - vs - 22, base - hmin - vs - 40)
        rv = rl + vs + 2
        geo["rail"] = rl
        yl = rv + 5

        def two(x, name, val, a="start", vfill=INK):
            return t(x, rl, name, fs, MUTED, 400, a) + t(x, rv, val, vs, vfill, 600, a, True)

        out.append(two(x0, "Ordre", "?" if order == "open" else o_val, "start", ofill))
        out.append(leader(v0, yc - max(8, th / 2 + 3.5), v0, yl, False))
        val = f'{d["pv"]}+{o_val}={tot}' if order == "typed" else str(tot)
        out.append(two(b1, "På vei", val))
        out.append(leader(b1 + bw * .5, b1top, b1 + bw * .5, yl))
        out.append(two(v1, "Levering", d["lev"], "middle"))
        out.append(leader(v1, yc - max(8, d["lev"] * unit / 2 + 3.5), v1, yl, False))
        out.append(two(cb, "Lager", d["lager"], "middle"))
        out.append(leader(cb, b2top, cb, yl))
        out.append(two(v2, "Sendt", d["sendt"], "middle"))
        out.append(leader(v2, yc - max(8, d["sendt"] * unit / 2 + 3.5), v2, yl, False))
        ry = base + 3 + hmin * .62
        out.append(nv(b2 - 12, ry + 5, "Restordre", d["rest"], "end", fs, vs))
        out.append(leader(b2, ry, b2 - 10, ry, True))
        out.append(nv(cb - 16, vy + 5, "Innkommende ordre", d["inn"], "end", fs, vs))
        if delaytxt:
            dx = v1 + (b2 - v1) * .42
            out.append(t(b1 + bw * .1, base + fs + 3, "om lag 4 uker", fs, MUTED, 400, "start"))
            out.append(leader(dx, yc + max(8, d["lev"] * unit / 2 + 5), dx, base + 4, False))
    if loop:
        out.append(loop_overlay(geo, d, o_val, order, fs, vs, posval))
    return "".join(out), geo


def loop_overlay(g, d, o_val, order, fs, vs, posval=None):
    """Posisjon som hjelpevariabel. Tilbakekoblingen lukkes tilbake til Ordre. Bare etter Debrief."""
    px, py = g["v1"] + 16, g["b1top"] - 22
    py = min(py, g["b2top"] - 22)
    pos = d["pos"] if posval is None else posval
    o = info(g["b1"] + g["bw"] * .8, g["b1top"], px - 10, py + 6, 5, INK, 1)
    o += info(g["cb"] - 12, g["b2top"], px + 9, py + 6, -5, INK, 1)
    o += circ(px, py, 10, PAPER, INK, 1.2)
    o += nv(px + 14, py - 8, "Posisjon", pos, "start", fs, vs)
    o += info(px - 10, py - 3, g["v0"] + 3, g["yc"] - g["th"] / 2 - 9, 20, RED, 1.5, 7)
    o += t(g["v0"] + 30, py - 2, "B", fs + 2, RED, 700)
    return o


def timechart(x, y, W, u, s=3.5, fs=13, run=None, role="Grossist", fmax=None, nmax=None, nmin=None, gap=22, vs=None,
              tick=True, nowlab=True, label=True, xlabels=True):
    """Felles tidsakse. Øverst: inn og ut per uke, flaten mellom er endringen i Lager − Restordre.
    Under: Lager over null, Restordre under null. Høyre kant er nå. Samme px per enhet i begge."""
    run = run or S17
    r = run[role]
    lev, inn = r["levering"][:u], r["innkommende_ordre"][:u]
    n = net(run, role, u)
    vs = vs or fs
    fm = fmax if fmax is not None else max(max(lev), max(inn))
    nx = nmax if nmax is not None else max(max(n), 0)
    nn = nmin if nmin is not None else min(min(n), 0)
    fb = y + fm * s
    z = fb + gap + nx * s
    cw = W / u
    out = []
    # rutenett og skala
    for v in range(0, int(fm) + 1, 10):
        yy = fb - v * s
        out.append(ln(x, yy, x + W, yy, GRID if v else HAIR, 1))
        if tick:
            out.append(t(x - 5, yy + 4, v, fs - 1 if fs > 13 else fs, MUTED, 400, "end", True))
    for v in range(-40, 41, 20):
        if nn <= v <= nx:
            yy = z - v * s
            out.append(ln(x, yy, x + W, yy, GRID if v else HAIR, 1))
            if tick:
                out.append(t(x - 5, yy + 4, abs(v), fs - 1 if fs > 13 else fs, MUTED, 400, "end", True))
    # flaten mellom inn og ut
    for i in range(u):
        a, b = lev[i], inn[i]
        if a == b:
            continue
        x1 = x + i * cw
        top, bot = fb - max(a, b) * s, fb - min(a, b) * s
        out.append(rect(x1, top, cw, bot - top, BLUE if a > b else INK, "none", 0, 0, 'opacity="%s"' % (".30" if a > b else ".20")))

    def step(vals):
        d = f"M{x:.1f},{fb - vals[0] * s:.1f}"
        for i, v in enumerate(vals):
            d += f" H{x + i * cw:.1f} V{fb - v * s:.1f}"
        d += f" H{x + W:.1f}"
        return d

    out.append(path(step(inn), "none", INK, 1.8))
    out.append(path(step(lev), "none", BLUE, 2.2))
    # netto som søyler
    g = min(2.0, cw * .16)
    for i, v in enumerate(n):
        x1 = x + i * cw + g / 2
        if v > 0:
            out.append(rect(x1, z - v * s, cw - g, v * s, STOCK))
        elif v < 0:
            out.append(rect(x1, z, cw - g, -v * s, STOCK))
    # nå
    ybot = z - nn * s
    out.append(ln(x + W, y - 4, x + W, ybot + 4, RED, 1.4))
    if label:
        tp = fb - max(inn[max(0, u - 7):] + lev[max(0, u - 7):]) * s - 6
        w_inn = (len("Innkommende ordre") + 1) * fs * .53 + len(str(inn[-1])) * vs * .6 + 4
        out.append(nv(x + W - 5, tp, "Innkommende ordre", inn[-1], "end", fs, vs))
        out.append(ln(x + W - 5 - w_inn - 16, tp - fs * .32, x + W - 5 - w_inn - 3, tp - fs * .32, INK, 1.8))
        w_lev = (len("Levering") + 1) * fs * .53 + len(str(lev[-1])) * vs * .6 + 4
        out.append(nv(x + W - 5, fb + fs + 2, "Levering", lev[-1], "end", fs, vs))
        out.append(ln(x + W - 5 - w_lev - 16, fb + fs + 2 - fs * .32, x + W - 5 - w_lev - 3, fb + fs + 2 - fs * .32, BLUE, 2.4))
        negs = [i for i, v in enumerate(n) if v < 0]
        if n[-1] > 0:
            out.append(nv(x + W - 5, z - max(n[max(0, u - 3):]) * s - 5, "Lager", n[-1], "end", fs, vs))
        elif max(n) > 0:
            out.append(t(x + 3, z - max(n) * s - 5, "Lager", fs, MUTED))
        if negs:
            nx0 = x + negs[0] * cw - 5
            if n[-1] < 0:
                out.append(nv(nx0, z + fs + 4, "Restordre", -n[-1], "end", fs, vs))
            else:
                out.append(t(nx0, z + fs + 4, "Restordre", fs, MUTED, 400, "end"))
    # x-akse
    ya = ybot + fs + 7
    if xlabels:
        for w in [1] + list(range(5, u, 5)):
            if (u - w) * cw < fs * 6.2 or w > u:
                continue
            out.append(ln(x + (w - .5) * cw, ybot, x + (w - .5) * cw, ybot + 4, HAIR, 1))
            out.append(t(x + (w - .5) * cw, ya, w if w > 1 else "Uke 1", fs - (1 if fs > 13 else 0), MUTED, 400, "start" if w == 1 else "middle", False))
        if nowlab:
            out.append(rich(x + W, ya, [("Uke " + str(u) + ", nå", fs, RED, 600, False)], "end"))
    return "".join(out), dict(fb=fb, z=z, ybot=ybot, cw=cw, ya=ya, bottom=ya + 4)


def phone(x, y, s, body, label=None):
    o = rect(0, 0, 390, 844, SCREEN, INK, 1.4, 34) + body
    g = group(o, x, y, s)
    if label:
        g += t(x, y - 12, label, 14, MUTED, 500)
    return g


def button(x, y, w, h, s, primary=True, size=16):
    if primary:
        return rect(x, y, w, h, INK, "none", 0, 3) + t(x + w / 2, y + h / 2 + size * .36, s, size, SCREEN, 600, "middle")
    return rect(x, y, w, h, "none", INK, 1.2, 3) + t(x + w / 2, y + h / 2 + size * .36, s, size, INK, 500, "middle")


def demo(x, y, s="Demodata", a="start", size=13):
    return t(x, y, s, size, MUTED, 400, a)


def begin(side):
    global SIDE
    SIDE = side


def write(name, w, h, title, desc, body, bg=CANVAS):
    style = ("@import url('https://fonts.googleapis.com/css2?family=Red+Hat+Text:wght@400;500;600;700&amp;family=Red+Hat+Mono:wght@400;500;600&amp;display=swap');"
             f".d04-t{{font-family:{FONT};font-feature-settings:'tnum' 1,'kern' 1}}"
             f".d04-m{{font-family:{MONO}}}")
    defs = (f'<pattern id="d04-{SIDE}-hr" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
            f'<rect width="5" height="5" fill="{PAPER}"/><line x1="0" y1="0" x2="0" y2="5" stroke="{RED}" stroke-width="1.5"/></pattern>'
            f'<pattern id="d04-{SIDE}-hk" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
            f'<rect width="5" height="5" fill="{PAPER}"/><line x1="0" y1="0" x2="0" y2="5" stroke="{INK}" stroke-width="1.2"/></pattern>')
    body = re.sub(r'<text [^>]*></text>', '', body)
    body = body.replace('<path d="" fill="none" stroke="#15181B" stroke-width="1.0"/>', '')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" font-family="{FONT}">'
           f'<title>{escape(title)}</title><desc>{escape(desc)}</desc><defs><style>{style}</style>{defs}</defs>'
           f'{rect(0, 0, w, h, bg)}{body}</svg>')
    (HERE / name).write_text(svg, encoding="utf-8")
    print("skrev", name)


# ---------- felles skjermdeler ----------
def play_header(u, role="Grossist", cost=None, spill="Spill 17"):
    c = cost if cost is not None else wk(u, role)["kost"]
    o = t(20, 48, f"Uke {u}", 26, INK, 600)
    o += t(112, 41, role, 14, INK, 500) + t(112, 58, spill, 13, MUTED)
    o += t(370, 34, "Totalkostnad", 13, MUTED, 400, "end") + t(370, 56, kr(c), 18, INK, 600, "end", True)
    return o


def main_phone_body(u=11, typed=24, s=3.6):
    d = wk(u)
    o = play_header(u)
    dg, g = diagram(18, 212, 354, u, 1.5, order="typed", typed=typed, rail=98)
    o += dg
    tc, m = timechart(54, 344, 306, u, s, gap=26)
    o += tc
    # Inndata festet til Ordre-ventilen med rød informasjonspil
    fy = m["bottom"] + 26
    o += path(f"M30,{fy:.1f} L30,{g['yc'] + 66:.1f} Q30,{g['yc'] + 46:.1f} {g['v0'] - 3:.1f},{g['yc'] + g['th'] / 2 + 14:.1f}", "none", RED, 1.3)
    o += head(g["v0"] - 2, g["yc"] + g["th"] / 2 + 11, math.radians(-60), 7, RED)
    o += rect(20, fy, 120, 62, PAPER, RED, 1.5, 2) + t(80, fy + 44, typed, 40, INK, 600, "middle", True)
    o += t(154, fy + 20, "Ordre denne uka", 13, MUTED)
    o += rich(154, fy + 44, [(f'{d["pv"]} + {typed} = {d["pv"] + typed}', 16, INK, 600, True), (" på vei", 13, MUTED, 400, False)])
    o += button(20, fy + 76, 350, 52, f"Bekreft ordre på {typed}")
    o += t(20, fy + 150, "Ordren kan ikke endres etter bekreftelse.", 13, MUTED)
    o += t(20, fy + 172, "Ida og Mikkel har bestilt. Jonas venter (3 min).", 13, INK)
    o += t(20, 824, "Demodata", 13, MUTED)
    o += t(370, 824, "Regnestykke og historikk", 13, INK, 600, "end", extra='text-decoration="underline"')
    return o


def detail_body(u=11, typed=24):
    d = wk(u)
    o = t(20, 48, "Detaljer", 24, INK, 600) + t(370, 46, "Lukk", 14, INK, 600, "end", extra='text-decoration="underline"')
    o += t(20, 68, f"Uke {u}, Grossist", 13, MUTED)
    # Posisjon som hjelpevariabel, festet til de tre beholdningene
    y = 108
    o += t(20, y, "Posisjon", 16, INK, 600)
    unit = 1.5
    base = y + 88
    xs = [(20, "Lager", d["lager"], "+"), (112, "Restordre", d["rest"], "−"), (204, "På vei", d["pv"], "+")]
    px, py = 340, base - 44
    for i, (x_, nm, v, sign) in enumerate(xs):
        o += box_up(x_, base, 56, v, unit, 26, ticks=False)
        o += nv(x_, base + 18, nm, v, "start", 13, 14)
        o += info(x_ + 28, base - 28, px - 13, py + 1 + i, -(26 - 8 * i), INK, 1)
        o += t(x_ + 16, base - 33, sign, 15, INK, 600, "middle")
    o += circ(px, py, 12, PAPER, INK, 1.2)
    o += t(px, py + 5, d["pos"], 14, INK, 600, "middle", True)
    o += rich(20, base + 50, [(f'{d["lager"]} − {d["rest"]} + {d["pv"]} = ', 15, INK, 500, True), (str(d["pos"]), 15, INK, 700, True)])
    o += rich(20, base + 74, [(f'{d["pos"]} + ', 15, INK, 500, True), (str(typed), 15, RED, 700, True), (f' = {d["pos"] + typed}', 15, INK, 700, True)])
    o += t(370, base + 62, "Regnestykket, ikke et råd.", 13, MUTED, 400, "end")
    # På vei som transportbånd: ordre i uke w kommer i uke w+4
    y = base + 126
    o += ln(20, y - 24, 370, y - 24, GRID)
    o += t(20, y, "Det som er på vei", 16, INK, 600)
    arr = [(w + 4, S17["Grossist"]["ordre"][w - 1]) for w in (u - 3, u - 2, u - 1)]
    assert sum(a for _, a in arr) == d["pv"]
    k = 350 / (d["pv"] + typed)
    cx = 20
    by = y + 58
    for w, a in arr:
        wd = a * k
        o += rect(cx, by - 24, wd, 24, STOCK, SCREEN, 1)
        o += t(cx + wd / 2, by - 30, a, 14, INK, 600, "middle", True)
        o += t(cx + wd / 2, by + 18, w, 13, MUTED, 400, "middle")
        cx += wd
    wd = typed * k
    o += rect(cx, by - 24, wd, 24, f"url(#d04-{SIDE}-hr)", RED, 1)
    o += t(cx + wd / 2, by - 30, typed, 14, RED, 600, "middle", True)
    o += t(cx + wd / 2, by + 18, f"Uke {u + 4}", 13, MUTED, 400, "middle")
    o += t(20, by + 42, f"Neste levering: {arr[0][1]}, kjent ankomst Uke {arr[0][0]}.", 13, INK)
    o += t(20, by + 60, "Ikke garantert. Leverandøren kan mangle varer.", 13, MUTED)
    # Ordrehistorikk
    y = by + 110
    o += ln(20, y - 24, 370, y - 24, GRID)
    o += t(20, y, "Dine ordre", 16, INK, 600)
    hist = S17["Grossist"]["ordre"][:u - 1]
    bb = y + 92
    cw = 350 / u
    sc = 64 / typed
    for i, v in enumerate(hist):
        o += rect(20 + i * cw + 1.5, bb - v * sc, cw - 3, v * sc, STOCK)
    o += rect(20 + (u - 1) * cw + 1.5, bb - typed * sc, cw - 3, typed * sc, f"url(#d04-{SIDE}-hr)", RED, 1)
    o += ln(20, bb, 370, bb, HAIR)
    o += t(20 + cw * .5, bb - hist[0] * sc - 5, hist[0], 13, INK, 500, "middle", True)
    o += t(20 + (u - 1.5) * cw, bb - hist[-1] * sc - 5, hist[-1], 13, INK, 500, "middle", True)
    o += t(20 + (u - 1) * cw - 3, bb - typed * sc + 11, typed, 14, RED, 600, "end", True)
    o += t(20, bb + 17, "Uke 1", 13, MUTED) + t(370, bb + 17, f"Uke {u}, nå", 13, RED, 600, "end")
    # Kostnad er også en beholdning
    y = bb + 62
    o += ln(20, y - 24, 370, y - 24, GRID)
    o += t(20, y, "Totalkostnad er også en beholdning", 16, INK, 600)
    fy = y + 36
    o += cloud(28, fy)
    o += pipe_h(36, 246, fy, d["kostuke"], .8)
    o += valve(120, fy, d["kostuke"] * .8)
    o += rect(246, fy - 20, 124, 40, PAPER, INK, 1.4)
    o += t(308, fy + 6, kr(d["kost"]), 15, INK, 600, "middle", True)
    o += rich(20, fy + 44, [("Denne uka ", 13, MUTED, 400, False), (f'{d["rest"]} × 1,00 + {d["lager"]} × 0,50 = {nb(d["kostuke"])}', 14, INK, 500, True)])
    o += t(20, 824, "Demodata", 13, MUTED)
    return o


def laptop_body(u=11, typed=24):
    d = wk(u)
    o = t(40, 58, f"Uke {u}", 32, INK, 600) + t(150, 48, "Grossist", 17, INK, 500) + t(150, 68, "Spill 17", 16, MUTED)
    o += t(920, 40, "Totalkostnad", 16, MUTED, 400, "end") + t(920, 66, kr(d["kost"]), 22, INK, 600, "end", True)
    dg, g = diagram(36, 246, 884, u, 1.8, order="typed", typed=typed, fs=16, vs=18, rail=106)
    o += dg
    tc, m = timechart(370, 386, 550, u, 2.9, 16, gap=30)
    o += tc
    fy = 410
    o += path(f"M60,{fy} L60,{g['yc'] + 90:.1f} Q60,{g['yc'] + 60:.1f} {g['v0'] - 2:.1f},{g['yc'] + g['th'] / 2 + 12:.1f}", "none", RED, 1.5)
    o += head(g["v0"] - 1, g["yc"] + g["th"] / 2 + 10, math.radians(-75), 8, RED)
    o += rect(40, fy, 130, 66, PAPER, RED, 1.6, 2) + t(105, fy + 48, typed, 42, INK, 600, "middle", True)
    o += button(40, fy + 80, 270, 48, f"Bekreft ordre på {typed}", True, 18)
    o += t(186, fy + 26, "Ordre denne uka", 16, MUTED)
    o += t(186, fy + 52, f'{d["pv"]} + {typed} = {d["pv"] + typed}', 18, INK, 600, "start", True)
    o += t(40, fy + 152, "Kan ikke endres etter bekreftelse.", 16, MUTED)
    o += t(40, fy + 174, "Jonas venter (3 min).", 16, INK)
    return o


def notation_row(x, y, kind, name, txt):
    o = ""
    gx = x
    if kind == "stock":
        o += rect(gx, y - 16, 44, 22, PAPER, INK, 1.4) + rect(gx, y - 6, 44, 12, STOCK)
    elif kind == "flow":
        o += pipe_h(gx - 2, gx + 46, y - 5, 6, 1) + valve(gx + 20, y - 5, 6)
    elif kind == "info":
        o += info(gx, y + 2, gx + 44, y - 8, 8, INK, 1.1)
    elif kind == "delay":
        o += ln(gx, y - 5, gx + 44, y - 5, INK, 1.1) + delay(gx + 22, y - 5, 8)
    elif kind == "cloud":
        o += cloud(gx + 22, y - 5, INK, 1.4)
    o += rich(x + 62, y, [(name + ". ", 15, INK, 600, False), (txt, 15, MUTED, 400, False)])
    return o


# ---------- 05 hovedskjerm ----------
def page05():
    begin("05")
    o = ""
    o += phone(36, 66, 1, main_phone_body(), "Telefon, Uke 11, 24 er tastet")
    o += phone(446, 66, 1, detail_body(), "Ett trykk: det åpnede panelet")
    lx, ly, s = 866, 66, .72
    scr = rect(0, 0, 960, 600, SCREEN) + laptop_body()
    o += group(rect(-10, -10, 980, 620, "none", INK, 1.4, 12) + scr, lx + 7, ly, s)
    o += ln(lx - 16, ly + 446, lx + 716, ly + 446, INK, 1.4)
    o += t(lx, ly - 12, "Laptop i Labtime: samme tegning, samme tall", 14, MUTED, 500)
    y = ly + 492
    o += t(lx, y, "Tallene sitter på tegningen.", 30, INK, 600)
    o += para(lx, y + 34, "Taster Sara 24, går tallet rett inn i På vei, og boksen vokser fra 16 til 40 på samme skala som Lager. Tykkelsen på røret er ukas strøm. Under ser hen inn og ut, og flaten mellom dem er det som skjedde med lageret.", 690, 16, 23, MUTED)
    y2 = y + 134
    o += t(lx, y2, "Slik leses tegningen, uten at noen har forklart den", 15, INK, 600)
    rows = [("stock", "Beholdning", "noe som hoper seg opp. Fylt til skala."),
            ("flow", "Strøm", "det som går inn eller ut per uke, med ventil."),
            ("delay", "Forsinkelse", "her går det om lag 4 uker."),
            ("info", "Informasjon", "tynn pil: dette påvirker noe, uten å flytte varer."),
            ("cloud", "Sky", "utenfor det du styrer.")]
    for i, (k, n, tx) in enumerate(rows):
        o += notation_row(lx, y2 + 32 + i * 30, k, n, tx)
    write("05-spill.svg", 1600, 1000, "Struktur: spillskjermen i Uke 11",
          "Saras skjerm som levende stock-and-flow-tegning med felles tidsakse, åpnet detaljpanel og laptop. Demodata.", o)


# ---------- 10 pedagogikk ----------
def order_chart(x, y, W, u, s, run=None, role="Grossist", fm=32, arc=None, fs=13, ticks=True):
    """Ordre som søyler, Levering som trapp. Buen viser forsinkelsen: samme ordre fire uker senere."""
    run = run or S17
    r = run[role]
    ord_, lev = r["ordre"][:u], r["levering"][:u]
    cw = W / u
    base = y + fm * s
    o = ""
    for v in range(0, fm + 1, 10):
        o += ln(x, base - v * s, x + W, base - v * s, GRID if v else HAIR)
        if ticks:
            o += t(x - 5, base - v * s + 4, v, fs, MUTED, 400, "end", True)
    g = min(2, cw * .16)
    for i, v in enumerate(ord_):
        o += rect(x + i * cw + g / 2, base - v * s, cw - g, v * s, HAIR)
    d = f"M{x:.1f},{base - lev[0] * s:.1f}"
    for i, v in enumerate(lev):
        d += f" H{x + i * cw:.1f} V{base - v * s:.1f}"
    d += f" H{x + W:.1f}"
    o += path(d, "none", BLUE, 2.2)
    if arc and arc + 4 <= u:
        xa, xb = x + (arc - .5) * cw, x + (arc + 3.5) * cw
        ya, yb = base - ord_[arc - 1] * s - 3, base - lev[arc + 3] * s - 3
        o += info(xa, ya, xb, yb, -12, RED, 1.3, 6)
        o += t(xa - 4, ya - 2, f"{ord_[arc - 1]} bestilt, {lev[arc + 3]} levert", fs, INK, 500, "end")
    o += ln(x + W, y - 2, x + W, base + 3, RED, 1.4)
    return o, base


def mini_chain(x, y, kost, forst, w=62, gap=34, k=.07, fs=13):
    """Fire beholdninger: høyde er kostnad. Forsterkning henger i hjelpelinjer."""
    o = ""
    px = x
    for i, role in enumerate(ROLES):
        v = kost[role]
        h = v * k
        o += rect(px, y - h, w, h, STOCK)
        o += rect(px, y - 50, w, 50, "none", INK, 1.1)
        o += t(px, y + 16, role, fs, MUTED)
        o += t(px, y + 34, nb(v), fs + 1, INK, 500, "start", True)
        o += t(px, y + 52, xf(forst[role]), fs + 1, INK, 500, "start", True)
        if i < 3:
            o += ln(px + w, y - 25, px + w + gap - 5, y - 25, INK, 1.1) + head(px + w + gap, y - 25, 0, 6)
        px += w + gap
    return o


def page10():
    begin("10")
    o = t(40, 62, "Samme tegning, fire uker", 40, INK, 600)
    o += para(40, 96, "Strukturen endrer seg aldri. Det er bare tallene som gjør det. Her er Saras egne skjermer ved Uke 5, 11, 18 og 29, tegnet på samme skala, slik at svingningen viser seg uten at noen sier det.", 1100, 18, 26, MUTED)
    o += demo(1960, 62, "Demodata fra spill 17. Sara, Grossist.", "end", 14)
    weeks = [5, 11, 18, 29]
    lab = 40
    colx = [352 + i * 410 for i in range(4)]
    colw = 372
    ystart = 150
    rows = [
        (ystart + 16, "Strukturen", "P2 P3 P6", "Beholdning og strøm på samme skala. Boksen til venstre er det du allerede har bestilt.",
         "Innsikt: se på størrelsen på På vei før du taster. Det er bestillinger du ikke kan ta tilbake."),
        (ystart + 334, "Inn og ut", "P1", "Flaten mellom linjene er det lageret endrer seg med, uke for uke.",
         "Innsikt: er ut større enn inn, synker lageret, uansett hva du bestilte sist."),
        (ystart + 490, "Lager og Restordre", "P1 P8", "Hver søyle er summen av flatene før den. Restordre koster 1,00 og lager 0,50 per enhet per uke.",
         "Innsikt: nivået endrer seg bare gjennom strømmene. Det svarer ikke rett på en ordre."),
        (ystart + 668, "Ordre og Levering", "P2", "Søylene er dine ordre, linja er det som kom. Mellom dem går om lag 4 uker.",
         "Innsikt: det du får nå kom av det du gjorde for fire uker siden."),
    ]
    for ry, nm, ps, txt, ins in rows:
        o += t(lab, ry, nm, 19, INK, 600)
        o += t(lab + 280, ry, ps, 13, RED, 600, "end")
        h = para_h(txt, 285, 14, 19)
        o += para(lab, ry + 23, txt, 285, 14, 19, MUTED)
        o += para(lab, ry + 28 + h, ins, 285, 14, 19, INK, 500)
    o += ln(lab, ystart + 306, 1960, ystart + 306, GRID)
    o += ln(lab, ystart + 644, 1960, ystart + 644, GRID)
    head_caps = {5: "Alt balanserer ennå.", 11: "Lageret er tomt. Sara taster 24.", 18: "Mest på vei, Restordre nær toppen.", 29: "Varene kom. Nå er det Lager."}
    S = 2.0
    for cx, u in zip(colx, weeks):
        o += t(cx, ystart + 18, f"Uke {u}", 22, INK, 600)
        o += t(cx + 92, ystart + 18, head_caps[u], 14, MUTED)
        dg, g = diagram(cx, ystart + 232, colw, u, 1.2, order="done", fs=13, vs=15, delaytxt=False, rail=ystart + 44)
        o += dg
        tc, m = timechart(cx + 30, ystart + 334, colw - 30, u, S, 13, fmax=32, nmax=30, nmin=-40, gap=36)
        o += tc
        oc, b = order_chart(cx + 30, ystart + 670, colw - 30, u, 2.0, arc=11 if u >= 15 else None)
        o += oc
    # etter debrief
    ys = 968
    o += ln(lab, ys - 24, 1960, ys - 24, INK, 1)
    o += t(lab, ys + 8, "Etter Debriefen: samme tegning mot en simulert referanse", 24, INK, 600)
    o += para(lab, ys + 36, "Å regne med det som er på vei demper svingningen. Det er ikke nok alene: i simuleringen ga en regel som jaget siste ordre for hardt, Fabrikk 12×. Rolig tilpasning og å telle det som er på vei må til sammen. Referansen viser sammenhengen, den er ikke en fasit.", 1120, 15, 21, MUTED)
    o += t(1148, ys + 8, "P3 P5 P7 P8", 13, RED, 600, "end")
    runs = [("Spill 17, slik det ble spilt", S17, F["spill17"], "spilt"),
            ("Simulert: bare Grossist teller på vei", SIM1, F["bare_sara_teller_paa_vei"], "sim"),
            ("Simulert: alle fire teller på vei, rolig", SIM2, F["alle_teller_paa_vei"], "sim")]
    w3 = 365
    for i, (nm, run, meta, kind) in enumerate(runs):
        x = lab + 30 + i * (w3 + 20)
        y = ys + 100
        o += t(x - 30, y - 8, nm, 15, INK, 600)
        s2 = 1.05
        # Ordre fra Grossist på samme skala i alle tre
        ord_ = run["Grossist"]["ordre"]
        cw = (w3 - 40) / 36
        fb = y + 24 * s2 + 2
        d = f"M{x:.1f},{fb - ord_[0] * s2:.1f}"
        for k_, v in enumerate(ord_):
            d += f" H{x + k_ * cw:.1f} V{fb - v * s2:.1f}"
        o += ln(x, fb, x + 36 * cw, fb, HAIR)
        o += path(d + f" H{x + 36 * cw:.1f}", "none", BLUE, 1.9)
        o += t(x + 36 * cw, fb - max(ord_) * s2 - 2 if False else y + 8, f"Ordre, topp {max(ord_)}", 13, MUTED, 400, "end")
        n = net(run, "Grossist")
        z = fb + 18 + 30 * s2
        for k_, v in enumerate(n):
            o += rect(x + k_ * cw + .3, z - v * s2 if v > 0 else z, cw - .6, abs(v) * s2, STOCK)
        o += ln(x, z, x + 36 * cw, z, HAIR)
        o += t(x + 36 * cw, z + 40 * s2 + 12, f"Mest Restordre {-min(n)}, mest Lager {max(n)}", 13, MUTED, 400, "end")
        cy = z + 40 * s2 + 70
        o += mini_chain(x - 30, cy, meta["kost_per_rolle"], meta["forsterkning"], w=58, gap=30, k=.07)
        o += nv(x - 30, cy + 76, "Kjeden", kr(meta["kjedekost"]), "start", 14, 15)
        if kind == "sim":
            o += t(x + 335, cy + 76, "Simulert", 13, MUTED, 500, "end")
        else:
            o += t(x + 335, cy + 76, "Kostnad og Forsterkning per Rolle", 13, MUTED, 400, "end")
    # Hjelpegrad
    hx = 1230
    o += t(hx, ys + 8, "Hjelpegrad: tegningen er åpen, sløyfen er lukket", 24, INK, 600)
    o += para(hx, ys + 36, "I Klassespillet ser Sara alle beholdningene, men ingen legger dem sammen for hen. Etter Debriefen får hen Posisjon og sløyfen tilbake til Ordre, i Replay.", 720, 15, 21, MUTED)
    u = 11
    dg1, _ = diagram(hx, ys + 240, 350, u, 1.2, order="typed", typed=24, fs=13, vs=14, delaytxt=False, rail=ys + 122)
    o += dg1
    o += t(hx, ys + 98, "Klassespill", 15, INK, 600)
    o += t(hx, ys + 358, "Ingen Posisjon i tegningen. Regnestykket ligger bak ett trykk.", 13, MUTED)
    rw = 20
    dg2, _ = diagram(hx + 370, ys + 240, 350, rw, 1.2, order="done", run=REPLAY, fs=13, vs=14, delaytxt=False, loop=True, rail=ys + 122)
    o += dg2
    o += t(hx + 370, ys + 98, f"Replay, Uke {rw}", 15, INK, 600)
    o += t(hx + 370, ys + 358, "Posisjon er en node. Sløyfen B er tegnet i rødt.", 13, MUTED)
    o += t(hx + 370, ys + 378, "Ingen anbefalt ordre her heller.", 13, MUTED)
    write("10-pedagogikk.svg", 2000, 1400, "Struktur: grafgrammatikk og pedagogikk",
          "Saras skjerm ved Uke 5, 11, 18 og 29 med prinsippene merket, sammenligning med simulert referanse og forskjellen mellom Klassespill og Replay. Demodata.", o)


def seat_rows(x, y, w, rows, rowh=56):
    """Setene som kjede. Fylt = har bestilt, tom = venter, skravert = KI-spiller. Alltid med ord."""
    o = ""
    for i, (role, who, stat, state) in enumerate(rows):
        yy = y + i * rowh
        o += rect(x, yy, 34, 26, PAPER)
        if state == "done":
            o += rect(x, yy, 34, 26, STOCK)
        if state == "ki":
            o += rect(x, yy, 34, 26, f"url(#d04-{SIDE}-hk)")
        o += rect(x, yy, 34, 26, "none", RED if state == "you" else INK, 1.3)
        if i < len(rows) - 1:
            o += ln(x + 17, yy + 26, x + 17, yy + rowh - 5, INK, 1.1) + head(x + 17, yy + rowh, math.pi / 2, 6)
        o += t(x + 48, yy + 11, role, 14, INK, 600) + t(x + 48, yy + 28, who, 13, MUTED)
        o += t(x + w, yy + 18, stat, 13, INK, 500, "end")
    return o


def keypad(y):
    o = ""
    keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "", "0", ""]
    cw, ch = 350 / 3, 78
    for i, k in enumerate(keys):
        cx, cy = 20 + (i % 3) * cw, y + (i // 3) * ch
        if k:
            o += rect(cx + 3, cy + 3, cw - 6, ch - 6, PAPER, HAIR, 1, 3)
            o += t(cx + cw / 2, cy + ch / 2 + 9, k, 26, INK, 500, "middle")
        elif i == 11:
            o += path(f"M{cx + cw / 2 + 16:.1f},{cy + ch / 2 - 10:.1f} H{cx + cw / 2 - 8:.1f} L{cx + cw / 2 - 20:.1f},{cy + ch / 2:.1f} L{cx + cw / 2 - 8:.1f},{cy + ch / 2 + 10:.1f} H{cx + cw / 2 + 16:.1f} Z", "none", INK, 1.3)
    return o


def body_open(u=11):
    o = play_header(u)
    dg, g = diagram(18, 212, 354, u, 1.5, order="open", rail=98)
    o += dg
    tc, m = timechart(54, 344, 306, u, 3.6, gap=26)
    o += tc
    fy = m["bottom"] + 34
    o += rect(20, fy, 120, 62, PAPER, INK, 1.4, 2) + ln(80, fy + 14, 80, fy + 48, INK, 1.6)
    o += t(154, fy + 20, "Ordre denne uka", 13, MUTED) + t(154, fy + 42, "Tast ett heltall.", 14, INK)
    o += button(20, fy + 76, 350, 52, "Bekreft ordre", False)
    o += t(20, fy + 152, "Ida og Mikkel har bestilt. Jonas venter (3 min).", 13, INK)
    o += t(20, 824, "Demodata", 13, MUTED)
    return o


def body_type(u=11, typed=24):
    d = wk(u)
    o = play_header(u)
    dg, g = diagram(18, 212, 354, u, 1.5, order="typed", typed=typed, rail=98)
    o += dg
    fy = 338
    o += rect(20, fy, 120, 62, PAPER, RED, 1.5, 2) + t(80, fy + 44, typed, 40, INK, 600, "middle", True)
    o += t(154, fy + 20, "Ordre denne uka", 13, MUTED)
    o += rich(154, fy + 44, [(f'{d["pv"]} + {typed} = {d["pv"] + typed}', 16, INK, 600, True), (" på vei", 13, MUTED, 400, False)])
    o += path(f"M30,{fy} L30,{g['yc'] + 66:.1f} Q30,{g['yc'] + 46:.1f} {g['v0'] - 3:.1f},{g['yc'] + g['th'] / 2 + 14:.1f}", "none", RED, 1.3)
    o += head(g["v0"] - 2, g["yc"] + g["th"] / 2 + 11, math.radians(-60), 7, RED)
    o += button(20, fy + 76, 350, 52, f"Bekreft ordre på {typed}")
    o += keypad(476)
    return o


def body_confirmed(u=11, typed=24):
    o = play_header(u)
    dg, g = diagram(18, 212, 354, u, 1.5, order="done", rail=98)
    o += dg
    o += t(20, 356, f"Ordre {typed} er bekreftet.", 22, INK, 600)
    o += t(20, 382, "Uka går videre når alle har bestilt.", 14, MUTED)
    o += seat_rows(20, 416, 350, [("Detaljist", "Ida", "har bestilt", "done"), ("Grossist", "Sara, deg", "har bestilt", "done"),
                                  ("Distributør", "Mikkel", "har bestilt", "done"), ("Fabrikk", "Jonas", "venter, 3 min", "wait")], 62)
    o += para(20, 690, "Du trenger ikke vente her. Du får beskjed når Uke 12 åpner.", 340, 14, 20, MUTED)
    o += t(20, 824, "Demodata", 13, MUTED)
    return o


def body_next(u=12):
    d0, d = wk(u - 1), wk(u)
    o = play_header(u)
    dg, g = diagram(18, 212, 354, u, 1.5, order="open", rail=98)
    o += dg
    y = 340
    o += rich(20, y, [("På vei ", 13, MUTED, 400, False), (f'{d0["pv"] + d0["ordre"]} − {d["lev"]} = {d["pv"]}', 15, INK, 600, True)])
    o += rich(20, y + 22, [("Restordre ", 13, MUTED, 400, False), (f'{d0["rest"]} + {d["inn"]} − {d["sendt"]} = {d["rest"]}', 15, INK, 600, True)])
    assert d0["pv"] + d0["ordre"] - d["lev"] == d["pv"] and d0["rest"] + d["inn"] - d["sendt"] == d["rest"]
    tc, m = timechart(54, 392, 306, u, 3.3, gap=26)
    o += tc
    o += button(20, 730, 350, 48, "Hopp over", False)
    o += t(20, 824, "Demodata", 13, MUTED)
    return o


def body_jonas(u=14):
    d = wk(u, "Fabrikk")
    o = play_header(u, "Fabrikk", d["kost"])
    o += t(20, 112, "En KI-spiller har setet ditt.", 22, INK, 600)
    o += para(20, 138, "Spillet sto på Pause mens gruppa ventet på deg. Etter 24 t overtok en KI-spiller, så de andre kunne spille videre.", 345, 14, 20, MUTED)
    r = S17["Fabrikk"]["ordre"][:u]
    x, base, W, s = 20, 288, 350, 4.4
    cw = W / u
    for i, v in enumerate(r):
        ki = i >= u - 3
        o += rect(x + i * cw + 1.5, base - v * s, cw - 3, v * s, f"url(#d04-{SIDE}-hk)" if ki else STOCK, INK if ki else "none", 1 if ki else 0)
    o += ln(x, base, x + W, base, HAIR)
    o += t(x, base + 18, "Dine ordre, Uke 1", 13, MUTED)
    o += t(x + W, base + 18, f"Uke {u}, nå", 13, RED, 600, "end")
    o += t(x + W, base - max(r[u - 3:]) * s - 6, "KI-spiller, Uke 12 til 14", 13, INK, 500, "end")
    o += seat_rows(20, 340, 350, [("Detaljist", "Ida", "har bestilt", "done"), ("Grossist", "Sara", "har bestilt", "done"),
                                  ("Distributør", "Mikkel", "har bestilt", "done"), ("Fabrikk", "Du", "KI-spiller, merket", "ki")], 58)
    o += button(20, 600, 350, 52, "Ta tilbake setet")
    o += para(20, 678, f"Du fortsetter fra Uke {u + 1}. Ordrene KI-spilleren la inn står, og de er merket i loggen.", 345, 14, 20, MUTED)
    o += t(20, 824, "Demodata", 13, MUTED)
    return o


def body_end():
    o = t(20, 56, "Spillet er over.", 26, INK, 600)
    o += t(20, 96, "Kjedens totalkostnad", 14, MUTED)
    o += t(20, 132, kr(F["spill17"]["kjedekost"]), 32, INK, 600, "start", True)
    k = .19
    x, base, w = 40, 620, 110
    tot = F["spill17"]["kjedekost"]
    o += rect(x, base - tot * k, w, tot * k, PAPER, INK, 1.4)
    yy = base
    ys = []
    for role in ROLES:
        v = F["spill17"]["kost_per_rolle"][role]
        h = v * k
        o += rect(x, yy - h, w, h, f"url(#d04-{SIDE}-hk)" if role == "Grossist" else STOCK, SCREEN, 1.5)
        ys.append((role, v, yy - h / 2))
        yy -= h
    o += rect(x, base - tot * k, w, tot * k, "none", INK, 1.4)
    for role, v, cy in ys:
        o += leader(x + w, cy, 186, cy)
        nm = role + (", deg" if role == "Grossist" else "")
        o += t(192, cy - 2, nm, 14, INK, 500) + t(192, cy + 17, nb(v), 16, INK, 600, "start", True)
    o += para(20, 660, "Hvorfor det ble slik, ser dere i Debriefen.", 340, 15, 21, INK)
    o += button(20, 700, 350, 52, "Videre til Debrief")
    o += t(20, 824, "Demodata", 13, MUTED)
    return o


def page06():
    begin("06")
    o = t(36, 60, "Én Uke, seks øyeblikk", 34, INK, 600)
    o += t(2064, 60, "Demodata fra spill 17", 14, MUTED, 400, "end")
    s = .78
    pw = 390 * s
    gap = (2028 - 6 * pw) / 5
    y = 92
    frames = [
        (body_open(), "Uka åpner.", "Strømmene går først: Levering inn, Innkommende ordre inn, Sendt ut. Boksene står klare før du taster."),
        (body_type(), "Beslutningen: 24 med 16 på vei.", "Boksen vokser mens hen taster, fra 16 til 40. Tallet går rett inn i tegningen. Ingen anbefaling."),
        (body_confirmed(), "Bekreftet, venter på de andre.", "Ordren er låst. Hen ser hvem det venter på, med Rolle, navn og hvor lenge."),
        (body_next(), "Uka går videre.", "Regnestykket vises i maks 2 sek, og kan hoppes over. 40 − 4 blir 36. Flaten i uka som kom, ligger nå i tidsaksen."),
        (body_jonas(), "Jonas er borte: Pause og KI-spiller.", "Ett fravær stopper ikke gruppa. Setet er merket, ordrene er merket, og Jonas kan ta det tilbake."),
        (body_end(), "Spillet slutter.", "Kjedens totalkostnad først, så per Rolle. Hele kjeden er én beholdning. Ingen rangering."),
    ]
    for i, (b, h, n) in enumerate(frames):
        x = 36 + i * (pw + gap)
        o += phone(x, y, s, b)
        o += t(x, y + 844 * s + 26, h, 16, INK, 600)
        o += para(x, y + 844 * s + 48, n, pw + 8, 14, 19, MUTED)
    yy = 880
    o += ln(36, yy, 2064, yy, GRID)
    o += t(36, yy + 40, "Det spilleren lærer uke for uke", 22, INK, 600)
    o += para(36, yy + 72, "Tegningen er den samme hver uke, så øyet merker hva som vokser. Sara ser at På vei blir større for hver ordre, lenge før noe kommer fram. Hen ser at Restordre ikke svarer på det hen bestilte i dag, bare på det som kom inn og gikk ut. Etter noen uker slutter hen å lete etter feilen hos de andre og begynner å lese strukturen.", 560, 16, 24, MUTED)
    ux = 660
    for i, u in enumerate([9, 10, 11, 12, 13, 14]):
        x = ux + i * 236
        dg, g = diagram(x, yy + 136, 216, u, .78, labels=False, order="done")
        o += t(x, yy + 30, f"Uke {u}", 15, INK, 600)
        d = wk(u)
        o += t(x, yy + 50, f'På vei {d["pv"] + d["ordre"]}', 13, MUTED)
        o += t(x + 216, yy + 50, f'Restordre {d["rest"]}', 13, MUTED, 400, "end")
        o += dg
        tc, _m = timechart(x, yy + 200, 216, u, 1.45, 13, fmax=12, nmax=12, nmin=-30, gap=8, tick=False, label=False, xlabels=False)
        o += tc
    write("06-spilldynamikk.svg", 2100, 1200, "Struktur: spilldynamikk i én Uke",
          "Seks telefonruter fra Uka åpner til spillet slutter, med notater og hva spilleren lærer. Demodata.", o)


# ---------- 07 Debrief ----------
def band(x, cy, W, vals, s, cw=None, fill=BLUE):
    cw = cw or W / len(vals)
    top, bot = "", ""
    d = f"M{x:.1f},{cy - vals[0] * s / 2:.1f}"
    for i, v in enumerate(vals):
        d += f" H{x + i * cw:.1f} V{cy - v * s / 2:.1f}"
    d += f" H{x + len(vals) * cw:.1f} V{cy + vals[-1] * s / 2:.1f}"
    for i in range(len(vals) - 1, -1, -1):
        d += f" V{cy + vals[i] * s / 2:.1f} H{x + i * cw:.1f}"
    return ln(x, cy, x + len(vals) * cw, cy, fill, .8) + path(d + " Z", fill, "none", 0)


def deb_header(step, title):
    o = t(20, 44, f"Debrief, steg {step} av 5", 13, MUTED)
    for i, ln_ in enumerate(wrap(title, 350, 23, .54)):
        o += t(20, 76 + i * 29, ln_, 23, INK, 600)
    return o


def deb1():
    o = deb_header(1, "Hvorfor svingte kjeden, tror du?")
    o += para(20, 142, "Skriv Forklaringen din før du ser noe mer. Tre setninger er nok. Den kan du ikke endre etterpå.", 345, 14, 20, MUTED)
    o += rect(20, 206, 350, 186, PAPER, INK, 1.3, 2)
    o += para(34, 234, "Jeg tror kundene kjøpte mer og mer utover i spillet, og at det varierte mye fra uke til uke. Da jeg gikk tom, bestilte jeg mye for å ta det igjen.", 322, 15, 22)
    o += ln(34, 356, 34, 374, INK, 1.4)
    # Låst boks: etterspørselen er en beholdning du ikke har sett
    y = 450
    o += t(20, y - 12, "Kundeetterspørsel, Uke 1 til 36", 14, INK, 600)
    o += rect(20, y, 350, 120, f"url(#d04-{SIDE}-hk)", INK, 1.3, 0, 'opacity=".32"')
    o += rect(20, y, 350, 120, "none", INK, 1.3)
    # hengelås som enkel tegning
    o += rect(182, y + 54, 26, 20, SCREEN, INK, 1.4) + path(f"M187,{y + 54} v-7 a8,8 0 0 1 16,0 v7", "none", INK, 1.4)
    o += t(195, y + 96, "Låst til Forklaringen er levert", 14, INK, 500, "middle")
    o += button(20, 620, 350, 52, "Lever Forklaring og åpne")
    o += t(20, 696, "Ida har levert. Mikkel har levert. Jonas skriver.", 13, MUTED)
    return o


def deb2():
    dem = S17["demand"]
    o = deb_header(2, "Kundene hoppet én gang. Så var det stille.")
    o += para(20, 142, "Dette er alt kundene gjorde: 4 per uke, 8 fra Uke 5, og slik var det i alle 36 uker. Det du tok imot var noe helt annet.", 345, 14, 20, MUTED)
    x, W, s = 46, 324, 26
    base = 560
    fm = 12
    cw = W / 36
    for v in (0, 4, 8, 12):
        o += ln(x, base - v * s, x + W, base - v * s, GRID if v else HAIR)
        o += t(x - 6, base - v * s + 4, v, 13, MUTED, 400, "end", True)
    inn = S17["Grossist"]["innkommende_ordre"]
    d = f"M{x:.1f},{base - inn[0] * s:.1f}"
    for i, v in enumerate(inn):
        d += f" H{x + i * cw:.1f} V{base - v * s:.1f}"
    o += path(d + f" H{x + W:.1f}", "none", BLUE, 1.6)
    d = f"M{x:.1f},{base - dem[0] * s:.1f}"
    for i, v in enumerate(dem):
        d += f" H{x + i * cw:.1f} V{base - v * s:.1f}"
    o += path(d + f" H{x + W:.1f}", "none", RED, 3.6)
    o += t(x + 3, base - 4 * s - 10, "4", 18, RED, 600, "start", True)
    o += t(x + 4 * cw - 4, base - 6 * s, "Uke 5", 13, RED, 600, "end")
    o += rich(x + W, base - 8 * s - 10, [("Kundene ", 14, INK, 600, False), ("8", 18, RED, 700, True)], "end")
    o += ln(x + 8 * cw, base - 13 * s + 6, x + 8 * cw + 16, base - 13 * s + 6, BLUE, 2)
    o += t(x + 8 * cw + 22, base - 13 * s + 11, "Det du fikk: Innkommende ordre", 13, INK)
    o += t(x, base + 20, "Uke 1", 13, MUTED) + t(x + W, base + 20, "Uke 36", 13, MUTED, 400, "end")
    o += para(20, 620, "Øvelsen dere har spilt heter ølspillet. Den er laget for å vise nettopp dette.", 345, 15, 21, INK, 500)
    o += button(20, 700, 350, 52, "Se alle fire Rollene")
    o += t(20, 780, "Alle tall fra loggen.", 13, MUTED)
    return o


def deb3():
    o = deb_header(3, "Samme kunde. Svingningen vokser oppover og kommer senere.")
    x, W = 20, 350
    cw = W / 36
    s = 1.55
    y0 = 166
    rowh = 112
    wk5 = x + 4.5 * cw
    o += ln(wk5, y0 - 4, wk5, y0 + 4 * rowh - 8, HAIR)
    for i, role in enumerate(ROLES):
        cy = y0 + i * rowh + 62
        vals = S17[role]["ordre"]
        o += t(x, y0 + i * rowh + 11, role, 14, INK, 600)
        o += t(x + 350, y0 + i * rowh + 13, xf(F["spill17"]["forsterkning"][role]), 18, INK, 600, "end", True)
        o += band(x, cy, W, vals, s)
        pk = vals.index(max(vals))
        o += t(x + (pk + .5) * cw, cy - max(vals) * s / 2 - 5, f"{max(vals)} i Uke {pk + 1}", 13, INK, 500, "middle")
    o += t(wk5 + 4, y0 + 4 * rowh - 8, "Uke 5", 13, MUTED)
    o += t(x + W, y0 + 4 * rowh - 8, "Uke 36", 13, MUTED, 400, "end")
    o += para(20, 648, "Tykkelsen er ordren per uke, på samme skala i alle fire. Tallet til høyre er Forsterkning: hvor mye mer ordrene svinger enn kundene.", 345, 14, 20, MUTED)
    o += button(20, 730, 350, 52, "Se ditt øyeblikk")
    return o


def deb4():
    d = wk(11)
    o = deb_header(4, "Ditt øyeblikk: Uke 11")
    o += t(20, 106, f'Dette så du. Du bestilte {d["ordre"]}.', 15, INK, 500)
    dg, g = diagram(18, 212, 354, 11, 1.1, order="done", fs=13, vs=15, rail=128, delaytxt=False)
    o += dg
    # kurven etterpå
    y = 300
    x, W = 34, 336
    cw = W / 36
    s = 1.45
    z = y + 30 * s + 8
    nS, nR = net(S17, "Grossist"), net(SIM1, "Grossist")
    for i, v in enumerate(nS):
        o += rect(x + i * cw + .4, z - v * s if v > 0 else z, cw - .8, abs(v) * s, STOCK)
    o += ln(x, z, x + W, z, HAIR)
    dp = f"M{x:.1f},{z - nR[0] * s:.1f}"
    for i, v in enumerate(nR):
        dp += f" H{x + i * cw:.1f} V{z - v * s:.1f}"
    o += path(dp + f" H{x + W:.1f}", "none", SCREEN, 3.4) + path(dp + f" H{x + W:.1f}", "none", BLUE, 1.8)
    xn = x + 10.5 * cw
    o += ln(xn, y, xn, z + 40 * s, RED, 1.3)
    o += t(xn + 4, y + 6, "Uke 11", 13, RED, 600)
    mi = nS.index(min(nS))
    o += t(x + (mi + .5) * cw, z - min(nS) * s + 15, f"Restordre {-min(nS)}, Uke {mi + 1}", 13, INK, 500, "middle")
    ma = nS.index(max(nS))
    o += t(x + W, z - max(nS) * s - 5, f"Lager {max(nS)}, Uke {ma + 1}", 13, INK, 500, "end")
    yn = z + 40 * s + 38
    o += ln(20, yn - 5, 36, yn - 5, BLUE, 2) + t(42, yn, "Simulert: Grossist teller på vei", 13, INK)
    o += rich(20, yn + 24, [("Din kostnad ", 13, MUTED, 400, False), (nb(F["spill17"]["kost_per_rolle"]["Grossist"]), 15, INK, 600, True), ("   Simulert ", 13, MUTED, 400, False), (nb(F["bare_sara_teller_paa_vei"]["kost_per_rolle"]["Grossist"]), 15, INK, 600, True)])
    o += t(20, yn + 44, "Viser sammenhengen, ikke en fasit.", 13, MUTED)
    # hva de andre så
    yo = yn + 80
    o += ln(20, yo - 22, 370, yo - 22, GRID)
    o += t(20, yo, "Hva de andre så", 15, INK, 600)
    ida, mik, jon = wk(11, "Detaljist"), wk(13, "Distributør"), wk(15, "Fabrikk")
    assert mik["inn"] == d["ordre"]
    yy = yo + 22
    for tx in (f'Ida: Innkommende ordre {ida["inn"]}, Restordre {ida["rest"]}.',
               f'Mikkel så din {d["ordre"]} i Uke 13, uten å vite hvorfor, og bestilte {mik["ordre"]}.',
               f'Jonas startet produksjon av {jon["ordre"]} i Uke 15.'):
        o += para(20, yy, tx, 345, 13, 18)
        yy += para_h(tx, 345, 13, 18) + 4
    o += t(20, 824, "Teksten er KI-generert, kan ta feil. Tallene er fra loggen.", 13, MUTED)
    return o


def deb5():
    d0, d = wk(12), wk(13)
    assert d0["rest"] + d["inn"] - d["sendt"] == d["rest"]
    o = deb_header(5, "Debrief-quiz")
    o += para(20, 104, f'I Uke 13 var Lager {d["lager"]} og Restordre {d0["rest"]} fra før. Innkommende ordre var {d["inn"]} og Levering {d["lev"]}. Hva ble Restordre?', 345, 15, 21, INK, 500)
    # liten tegning
    y = 208
    o += cloud(28, y)
    o += pipe_h(36, 150, y, d["inn"], 1.6)
    o += valve(92, y, d["inn"] * 1.6)
    o += t(92, y - 22, f'+{d["inn"]}', 14, INK, 600, "middle", True)
    o += rect(150, y - 30, 90, 60, PAPER, INK, 1.4) + t(195, y + 6, f'{d0["rest"]} + ...', 14, INK, 600, "middle", True)
    o += pipe_h(240, 352, y, d["sendt"], 1.6)
    o += valve(296, y, d["sendt"] * 1.6)
    o += t(296, y - 22, f'−{d["sendt"]}', 14, INK, 600, "middle", True)
    o += cloud(362, y)
    opts = [(d0["rest"] - d["inn"] + d["sendt"], ""), (d["rest"], "right"), (d0["rest"] + d["inn"], "wrong"), (d0["rest"] + d["inn"] + d["sendt"], "")]
    yy = 262
    for v, st in opts:
        stroke = INK if st == "right" else (RED if st == "wrong" else HAIR)
        o += rect(20, yy, 350, 44, PAPER if st else "none", stroke, 1.5 if st else 1, 2)
        o += t(36, yy + 28, v, 17, INK, 600, "start", True)
        if st == "wrong":
            o += t(356, yy + 27, "Ditt svar, feil", 13, RED, 600, "end")
        if st == "right":
            o += t(356, yy + 27, "Riktig svar", 13, INK, 600, "end")
        yy += 52
    o += para(20, yy + 16, f'Du la {d["inn"]} til {d0["rest"]} og fikk {d0["rest"] + d["inn"]}. Men {d["lev"]} kom inn og gikk rett ut igjen til det som var i kø. Restordre endres med inn minus ut, altså {d0["rest"]} + {d["inn"]} − {d["sendt"]} = {d["rest"]}.', 345, 15, 22)
    o += para(20, yy + 124, "Det er samme regnestykke som i Lager. Du møter det igjen i Individuell test.", 345, 14, 20, MUTED)
    o += button(20, 730, 350, 48, "Neste spørsmål")
    return o


def causal_loop(cx, cy, r, fs=15):
    pos = {"lr": (cx, cy - r), "o": (cx + r * 1.15, cy), "pv": (cx, cy + r), "l": (cx - r * 1.15, cy)}
    o = t(pos["lr"][0], pos["lr"][1] - 4, "Lager og Restordre", fs, INK, 600, "middle")
    o += t(pos["o"][0] + 10, pos["o"][1] + 5, "Ordre", fs, INK, 600)
    o += t(pos["pv"][0], pos["pv"][1] + 17, "På vei", fs, INK, 600, "middle")
    o += t(pos["l"][0] - 10, pos["l"][1] + 5, "Levering", fs, INK, 600, "end")
    o += info(cx + 40, cy - r + 6, cx + r * 1.15 + 6, cy - 14, -22, RED, 1.5, 8)
    o += info(cx + r * 1.15 + 6, cy + 14, cx + 22, cy + r - 6, -22, RED, 1.5, 8)
    o += info(cx - 22, cy + r - 6, cx - r * 1.15 - 6, cy + 14, -22, RED, 1.5, 8)
    o += info(cx - r * 1.15 - 6, cy - 14, cx - 40, cy - r + 6, -22, RED, 1.5, 8)
    o += t(cx + r * .9, cy - r * .62, "−", fs + 4, RED, 700, "middle")
    o += t(cx + r * .9, cy + r * .78, "+", fs + 2, RED, 700, "middle")
    o += t(cx - r * .9, cy + r * .78, "+", fs + 2, RED, 700, "middle")
    o += t(cx - r * .9, cy - r * .62, "+", fs + 2, RED, 700, "middle")
    o += delay(cx - r * .6, cy + r * .68, 8, RED)
    o += t(cx, cy + 4, "B", 30, RED, 700, "middle")
    o += t(cx, cy + 24, "balanserer", 13, MUTED, 400, "middle")
    return o


def page07():
    begin("07")
    o = t(36, 56, "Debrief: forklar først, se så strukturen", 34, INK, 600)
    o += t(2064, 56, "Demodata fra spill 17. Grossist Sara, Gruppedebrief.", 14, MUTED, 400, "end")
    s = .78
    pw = 390 * s
    gap = (2028 - 5 * pw) / 4
    y = 82
    bodies = [(deb1(), "Forklaringen låser opp avsløringen."),
              (deb2(), "Klimaks: rett strek mot alt hen tok imot."),
              (deb3(), "Linjene tykner oppover i kjeden, og senere."),
              (deb4(), "Hva du så, hva du gjorde, hva det kostet."),
              (deb5(), "Feil svar forklares med tegningen.")]
    for i, (b, n) in enumerate(bodies):
        x = 36 + i * (pw + gap)
        o += phone(x, y, s, b)
        o += t(x, y + 844 * s + 22, n, 15, INK, 500)
        if i < 4:
            yy = y + 844 * s / 2
            o += pipe_h(x + pw + 14, x + pw + gap - 14, yy, 3, 1)
            o += valve(x + pw + gap / 2, yy, 3)
    # Delt skjerm
    sy = 808
    sw = 1330
    o += rect(36, sy, sw, 372, SCREEN, INK, 1.4, 8)
    o += t(60, sy + 38, "Slik er strukturen. Det er den som svinger, ikke dere.", 26, INK, 600)
    o += t(sw + 12, sy + 38, "Delt skjerm", 14, MUTED, 400, "end")
    bx, bw = 214, 1024
    cw = bw / 36
    ky = sy + 58
    rh = 54
    s_ = 1.35
    rows = [("Kunde", S17["demand"], None)] + [(r, S17[r]["ordre"], F["spill17"]["forsterkning"][r]) for r in ROLES]
    for v in (5,):
        xx = bx + (v - .5) * cw
        o += ln(xx, ky - 2, xx, ky + 5 * rh, HAIR)
        o += t(xx + 4, ky + 5 * rh + 15, "Uke 5", 13, MUTED)
    o += t(bx, ky + 5 * rh + 15, "Uke 1", 13, MUTED) + t(bx + bw, ky + 5 * rh + 15, "Uke 36", 13, MUTED, 400, "end")
    for i, (nm, vals, f_) in enumerate(rows):
        cy = ky + i * rh + rh / 2
        if i == 0:
            o += cloud(88, cy, INK, 1.4)
            o += t(112, cy + 5, nm, 15, INK, 600)
        else:
            o += rect(68, cy - 14, 34, 28, PAPER, INK, 1.4)
            o += t(112, cy + 5, nm, 15, INK, 600)
            # ordre oppover i kjeden, varer nedover, med forsinkelse
            y1, y2 = cy - 14, cy - rh + (14 if i > 1 else 10)
            o += info(79, y2 + 1, 79, y1 - 1, 0, INK, 1, 5)
            o += ln(92, y1 - 1, 92, y2 + 1, INK, 1) + head(92, y2, -math.pi / 2, 5)
            o += delay(92, (y1 + y2) / 2, 5)
        o += band(bx, cy, bw, vals, s_, fill=BLUE)
        pk = vals.index(max(vals))
        if f_:
            o += t(bx + bw + 14, cy + 6, xf(f_), 18, INK, 600, "start", True)
            o += t(bx + (pk + .5) * cw, cy - max(vals) * s_ / 2 - 3, f"{max(vals)}, Uke {pk + 1}", 13, INK, 500, "middle")
        else:
            o += t(bx + bw + 14, cy + 5, "4, så 8", 14, INK, 500, "start", True)
    # årsaksdiagram
    lx = 1410
    o += t(lx, sy + 28, "Fagets begreper", 22, INK, 600)
    o += causal_loop(lx + 150, sy + 196, 86)
    terms = [("Beholdning", "hoper seg opp. Lager, Restordre, På vei."),
             ("Strøm", "per uke, inn eller ut. Ordre, Levering, Sendt."),
             ("Forsinkelse", "om lag 4 uker fra ordre til levering."),
             ("Balanserende sløyfe", "prøver å rette opp. Med forsinkelse slår den over."),
             ("Forsterkning", "ordrene svinger mer enn kundene, 1,8× til 7,6×.")]
    ty = sy + 62
    for n_, d_ in terms:
        o += t(lx + 330, ty, n_, 15, INK, 600)
        o += para(lx + 330, ty + 20, d_, 322, 14, 19, MUTED)
        ty += 20 + para_h(d_, 322, 14, 19) + 14
    write("07-debrief.svg", 2100, 1200, "Struktur: Debriefen i fem steg og delt skjerm",
          "Forklaring før avsløring, kundeetterspørselen, fire Rollers ordre, Saras øyeblikk i Uke 11 med simulert referanse, quiz og delt skjerm med strukturdiagram og balanserende sløyfe. Demodata.", o)


# ---------- 08 lærerflate ----------
def micro_chain(x, cy, g, W=128, bw=22, h=15):
    """Mikrotegning: fire små beholdninger, netto lager til skala, ordre som rørtykkelse."""
    gap = (W - 4 * bw) / 3
    o = ""
    k = (h / 2) / 60
    for i, role in enumerate(ROLES):
        bx = x + i * (bw + gap)
        n = g["netto_lager"][role][-1]
        if i < 3:
            th = max(1.0, min(6.0, g["ordre"][ROLES[i + 1]][-1] * .22))
            o += rect(bx + bw, cy - th / 2, gap, th, BLUE)
        o += rect(bx, cy - h / 2, bw, h, PAPER)
        vh = min(abs(n) * k, h / 2)
        if n > 0:
            o += rect(bx, cy - vh, bw, vh, STOCK)
        elif n < 0:
            o += rect(bx, cy, bw, vh, STOCK)
        o += rect(bx, cy - h / 2, bw, h, "none", INK, 1)
        o += ln(bx, cy, bx + bw, cy, HAIR, .8)
    return o


def trace(x, y, W, h, g, fm=40):
    cw = W / 36
    o = ln(x, y + h, x + W, y + h, GRID)

    def pl(vals):
        return " ".join(f"{x + i * cw:.1f},{y + h - min(v, fm) / fm * h:.1f}" for i, v in enumerate(vals))

    o += f'<polyline points="{pl(g["ordre"]["Detaljist"])}" fill="none" stroke="{INK}" stroke-width=".9"/>'
    o += f'<polyline points="{pl(g["ordre"]["Fabrikk"])}" fill="none" stroke="{BLUE}" stroke-width="1.3"/>'
    if g["status"] != "ferdig":
        xn = x + (g["uke"] - 1) * cw
        o += ln(xn, y, xn, y + h, RED, 1)
    return o


def status_mark(x, cy, st):
    o = rect(x, cy - 6, 12, 12, PAPER, INK, 1)
    if st == "ferdig":
        o += rect(x, cy - 6, 12, 12, STOCK)
    elif st == "pågår":
        o += rect(x, cy, 12, 6, STOCK)
    elif st == "pauset":
        o = rect(x + 2, cy - 6, 3, 12, STOCK) + rect(x + 7, cy - 6, 3, 12, STOCK)
    return o


def page08():
    begin("08")
    K = F["klasse"]
    sp = K["spill"]
    o = rect(0, 0, 1600, 1000, SCREEN)
    o += t(24, 40, "Oversikt", 26, INK, 600) + t(140, 40, "class-of-1994, IBE160", 15, MUTED)
    cnt = {s: sum(1 for g in sp if g["status"] == s) for s in ("ferdig", "pågår", "pauset", "venter")}
    assert cnt == {"ferdig": 41, "pågår": 13, "pauset": 2, "venter": 4}
    o += t(1576, 38, "Demodata", 13, MUTED, 400, "end")
    # Svingningene i klassen
    y0, h0 = 86, 86
    px0, pw = 24, 192
    fm = 40
    for i, role in enumerate(ROLES):
        x = px0 + i * (pw + 16)
        o += t(x, y0 - 18, role, 14, INK, 600)
        o += t(x + pw, y0 - 18, "median " + xf(K["ferdige"]["forsterkning_per_rolle"][role]["median"]), 13, INK, 500, "end", True)
        o += ln(x, y0 + h0, x + pw, y0 + h0, HAIR)
        cw = pw / 36
        for g in sp:
            vals = g["ordre"][role]
            pts = " ".join(f"{x + j * cw:.1f},{y0 + h0 - min(v, fm) / fm * h0:.1f}" for j, v in enumerate(vals))
            o += f'<polyline points="{pts}" fill="none" stroke="{INK}" stroke-width=".6" opacity=".2"/>'
        med = []
        for w in range(36):
            vs_ = sorted(g["ordre"][role][w] for g in sp if len(g["ordre"][role]) > w)
            med.append(vs_[len(vs_) // 2])
        pts = " ".join(f"{x + j * cw:.1f},{y0 + h0 - v / fm * h0:.1f}" for j, v in enumerate(med))
        o += f'<polyline points="{pts}" fill="none" stroke="{BLUE}" stroke-width="2"/>'
        o += t(x, y0 + h0 + 15, "Uke 1", 13, MUTED) + t(x + pw, y0 + h0 + 15, "36", 13, MUTED, 400, "end")
    o += t(24, y0 + h0 + 36, "Ordre per Rolle i alle 60 spill, på samme skala. Blå linje er medianen.", 13, MUTED)
    # Trakten som kjede av beholdninger
    tx = 880
    tr = K["traktA"]
    steps = [("Registrert", tr["registrert"]), ("Klassespill ferdig", tr["klassespill_ferdig"]), ("Debrief ferdig", tr["debrief_ferdig"]),
             ("Quiz bestått", tr["quiz_bestått"]), ("Replay ferdig", tr["replay_ferdig"]), ("Test levert", tr["test_levert"]), ("KI-vurdering klar", tr["ki_vurdering_klar"])]
    bw, gp, base = 50, 50, 150
    k = 84 / 240
    for i, (nm, v) in enumerate(steps):
        x = tx + i * (bw + gp)
        o += rect(x, base - 84, bw, 84, PAPER) + rect(x, base - v * k, bw, v * k, STOCK) + rect(x, base - 84, bw, 84, "none", INK, 1.2)
        o += t(x + bw / 2, base - 90, v, 15, INK, 600, "middle", True)
        lns = wrap(nm, 88, 13)
        for j, l_ in enumerate(lns):
            o += t(x + bw / 2, base + 17 + j * 15, l_, 13, MUTED, 400, "middle")
        if i < 6:
            o += pipe_h(x + bw, x + bw + gp, base - 42, steps[i + 1][1], .035)
    # Filter
    fy = 214
    o += ln(24, fy - 2, 1576, fy - 2, HAIR)
    filt = [("Alle", 60, True), ("Trenger tilsyn", cnt["venter"] + cnt["pauset"], False), ("Venter", cnt["venter"], False), ("Pågår", cnt["pågår"] + cnt["pauset"], False), ("Pauset", cnt["pauset"], False), ("Ferdig", cnt["ferdig"], False)]
    fx = 24
    for nm, v, act in filt:
        w_ = (len(nm) + len(str(v)) + 2) * 7.6
        o += rich(fx, fy + 24, [(nm + " ", 14, INK, 600 if act else 400, False), (str(v), 14, INK, 600, True)])
        if act:
            o += ln(fx, fy + 31, fx + w_, fy + 31, INK, 1.6)
        fx += w_ + 26
    o += t(fx + 16, fy + 24, "Det som haster, står først. Melding går til utvalget.", 13, MUTED)
    o += button(1412, fy + 4, 164, 32, "Send Melding", True, 14)
    # Liste, to spalter a 30 rader
    order = {"venter": 0, "pauset": 1, "pågår": 2, "ferdig": 3}
    rows = sorted(sp, key=lambda g: (order[g["status"]], -g.get("ventet_timer", 0), -g["uke"] if g["status"] != "ferdig" else g["spill"]))
    ry0, rh = 288, 23.6
    colw = 766
    for c in range(2):
        cx = 24 + c * (colw + 20)
        hy = ry0 - 12
        o += t(cx, hy, "Spill", 13, MUTED) + t(cx + 42, hy, "Status", 13, MUTED) + t(cx + 124, hy, "Uke", 13, MUTED)
        o += t(cx + 160, hy, "Kjeden nå", 13, MUTED) + t(cx + 298, hy, "Ordre: Detaljist, Fabrikk", 13, MUTED)
        o += t(cx + 508, hy, "Kost", 13, MUTED, 400, "end") + t(cx + 520, hy, "Venter på, KI", 13, MUTED)
        o += ln(cx, hy + 6, cx + colw, hy + 6, HAIR)
        for r in range(30):
            g = rows[c * 30 + r]
            y = ry0 + r * rh
            cy = y + rh / 2 - 2
            near = g.get("ventet_timer", 0) >= 20
            if near:
                o += rect(cx - 4, y - 2, colw + 8, rh, PAPER, RED, 1.2)
            o += t(cx + 26, cy + 5, g["spill"], 13, INK, 600, "end", True)
            o += status_mark(cx + 42, cy, g["status"])
            o += t(cx + 60, cy + 5, g["status"].capitalize(), 13, INK)
            o += t(cx + 146, cy + 5, g["uke"], 13, INK, 400, "end", True)
            o += micro_chain(cx + 160, cy, g)
            o += trace(cx + 298, cy - 9, 164, 18, g)
            o += t(cx + 508, cy + 5, nb(g["kjedekost"], 0), 13, INK, 400, "end", True)
            note = ""
            if g["status"] == "venter":
                note = f'{g["navn"]}, {g["venter_paa"]}, {g["ventet_timer"]} t'
                if near:
                    note += ", KI overtar om 1 t"
            elif g["status"] == "pauset":
                note = "Fortsetter " + g["fortsetter"]
            elif g["ki_seter"]:
                note = f'KI-spiller i {g["ki_seter"]} sete' + ("r" if g["ki_seter"] > 1 else "")
            o += t(cx + 520, cy + 5, note, 13, RED if near else (INK if g["status"] in ("venter", "pauset") else MUTED), 600 if near else 400)
    write("08-laerer-oversikt.svg", 1600, 1000, "Struktur: Oversikt for faglærer",
          "Svingningene i klassen, trakten som beholdninger og 60 Klassespill med mikrotegning av kjeden, status og hvem det venter på. Demodata.", o, SCREEN)


# ---------- 01 landing ----------
def page01():
    begin("01")
    o = rect(0, 0, 1440, 1200, SCREEN)
    o += t(72, 52, "Struktur", 20, INK, 700)
    o += t(1368, 50, "Logg inn", 15, INK, 500, "end", extra='text-decoration="underline"')
    u = 18
    # Tegningen bærer siden
    o += t(72, 150, "Forsyningskjeden,", 58, INK, 600) + t(72, 214, "tegnet slik", 58, INK, 600) + t(72, 278, "faget tegner den.", 58, INK, 600)
    o += para(72, 326, "En øvelse for hele klassen. Fire seter i hver gruppe, én beslutning per Uke, og tallene sitter på tegningen. Struktur kjører alt fra invitasjon til PDF-rapport.", 500, 18, 27, MUTED)
    o += button(72, 436, 210, 52, "Be om lærertilgang", True, 16)
    o += button(296, 436, 110, 52, "Logg inn", False, 16)
    dg, g = diagram(640, 400, 728, u, 2.2, order="done", fs=15, vs=18, rail=86)
    o += dg
    tc, m = timechart(108, 590, 1260, u, 3.4, 15, gap=40, vs=17)
    o += tc
    o += t(72, 570, "", 13)
    o += t(1368, 1008 - 0, "", 13)
    ys = m["bottom"] + 24
    o += t(72, ys, "Ett setes egne tall, Uke 18. Demodata.", 14, MUTED)
    o += para(1368 - 520, ys, "Flaten mellom Levering og Innkommende ordre er det Lager og Restordre endrer seg med.", 520, 14, 20, MUTED) if False else ""
    # Neste seksjon: forløpet som kjede, faktum på hjelpelinjer
    ny = ys + 66
    o += ln(72, ny - 34, 1368, ny - 34, INK, 1)
    o += t(72, ny + 4, "Fra Canvas-liste til PDF-rapport", 34, INK, 600)
    steps = [("Invitasjon", "Studentlisten kommer fra Canvas-eksport."), ("Klassespill", "Klasser på rundt 250 studenter, på mobil og på norsk."),
             ("KI-spillere", "Fyller tomme seter. Ett fravær stopper ikke gruppa."), ("Oversikt", "Alle spillene på én skjerm."),
             ("Debrief", "Ingen spill blir stående uferdig, så hver gruppe når hit."), ("PDF-rapport", "Kjører hele øvelsen, helt fram til rapporten.")]
    pitch = 1296 / 6
    by = ny + 62
    for i, (n_, f_) in enumerate(steps):
        x = 72 + i * pitch
        o += rect(x, by, 92, 36, PAPER, INK, 1.4)
        o += t(x, by - 8, n_, 15, INK, 600)
        if i < 5:
            o += pipe_h(x + 92, x + pitch, by + 18, 4, 1.2)
            o += valve(x + 92 + (pitch - 92) / 2, by + 18, 5)
        o += leader(x + 14, by + 36, x + 14, by + 56)
        o += para(x, by + 74, f_, pitch - 26, 15, 21, MUTED)
    write("01-landing.svg", 1440, 1200, "Struktur: landingsside for faglærere",
          "Første skjermbilde med ett setes stock-and-flow-tegning og tidsakse, og starten av neste seksjon. Demodata.", o, SCREEN)


# ---------- 02 Lag Klasse ----------
def field(x, y, w, label, val, mono=False, h=40):
    o = t(x, y, label, 14, MUTED)
    o += rect(x, y + 8, w, h, PAPER, INK, 1.1, 2) + t(x + 12, y + 8 + h / 2 + 5, val, 15, INK, 500, "start", mono)
    return o


def page02():
    begin("02")
    R = F["klasse"]["roster"]
    o = rect(0, 0, 1440, 1000, SCREEN)
    o += t(48, 56, "Lag Klasse", 34, INK, 600) + t(1392, 52, "Demodata", 13, MUTED, 400, "end")
    # Skjema
    x = 48
    o += field(x, 100, 360, "Navn på Klasse", "class-of-1994")
    o += field(x, 172, 360, "Emnekode", "IBE160")
    o += t(x, 244, "Canvas-fil", 14, MUTED)
    o += rect(x, 252, 360, 72, PAPER, INK, 1.1, 2)
    o += t(x + 14, 282, "ibe160-canvas-eksport.xlsx", 15, INK, 500)
    o += t(x + 14, 306, f'{R["paa_lista"]} rader lest. Bytt fil', 13, MUTED)
    o += field(x, 346, 360, "E-postkolonne", "E-post (kolonne D)")
    o += t(x, 418, "Slik ser kolonnen ut", 14, MUTED)
    for i, s_ in enumerate(["emma.berg@stud.example.no", "noah.lund@stud.example.no", "sara.moe@stud.example.no"]):
        o += t(x + 12, 442 + i * 22, s_, 14, INK)
        o += ln(x, 448 + i * 22, x + 360, 448 + i * 22, GRID)
    # Struktur: rader strømmer gjennom Klassen
    ox = 470
    o += t(ox, 104, "Radene gjennom Klassen", 20, INK, 600)
    valid = R["paa_lista"] - R["ugyldige_rader"]
    base, k = 310, 150 / 250
    bx = [ox, ox + 320, ox + 640]
    vals = [("På lista", R["paa_lista"]), ("Klare til Invitasjon", valid)]
    o += cloud(ox - 6, 0) if False else ""
    for i, (n_, v) in enumerate(vals):
        o += rect(bx[i], base - v * k, 130, v * k, STOCK) + rect(bx[i], base - 150, 130, 150, "none", INK, 1.3)
        o += t(bx[i], base - 178, n_, 14, MUTED) + t(bx[i], base - 158, v, 17, INK, 600, "start", True)
        o += leader(bx[i] + 65, base - 150, bx[i] + 65, base - 172) if False else ""
    o += pipe_h(bx[0] + 130, bx[1], base - 75, valid, .06)
    o += valve(bx[0] + 225, base - 75, 14)
    o += t(bx[0] + 225, base - 104, "E-post er gyldig", 13, MUTED, 400, "middle")
    # Ugyldig gren
    o += pipe_v(bx[0] + 225, base - 62, base + 8, R["ugyldige_rader"], 1)
    o += rich(bx[0] + 238, base, [("Ugyldige ", 14, MUTED, 400, False), (str(R["ugyldige_rader"]), 16, RED, 600, True)])
    # Invitert
    o += pipe_h(bx[1] + 130, bx[2], base - 75, valid, .06)
    o += valve(bx[1] + 225, base - 75, 14)
    o += t(bx[1] + 225, base - 104, "Send Invitasjoner", 13, MUTED, 400, "middle")
    p = R["paa_lista"]
    segs = [("Registrert", R["registrert"], STOCK), ("Manuelt registrert", R["manuelt_registrert"], BLUE), ("Uregistrert", R["uregistrert"], PAPER)]
    assert sum(s[1] for s in segs) == p
    yy = base
    o += t(bx[2], base - 178, "Status etter utsending", 14, MUTED)
    o += t(bx[2], base - 158, p, 17, INK, 600, "start", True)
    for n_, v, c in segs:
        h = v * k
        o += rect(bx[2], yy - h, 130, h, c, "none", 0)
        yy -= h
    o += rect(bx[2], base - 150, 130, 150, "none", INK, 1.3)
    lab_y = {"Registrert": base - 70, "Manuelt registrert": base - 136, "Uregistrert": base - 158 + 2}
    o += leader(bx[2] + 130, base - 70, bx[2] + 148, base - 70)
    o += t(bx[2] + 152, base - 65, f'Registrert {R["registrert"]}', 14, INK)
    yt = base - R["registrert"] * k
    o += leader(bx[2] + 130, yt - 1, bx[2] + 148, base - 120)
    o += t(bx[2] + 152, base - 115, f'Manuelt {R["manuelt_registrert"]}', 14, INK)
    o += leader(bx[2] + 130, base - 147, bx[2] + 148, base - 148)
    o += t(bx[2] + 152, base - 143, f'Uregistrert {R["uregistrert"]}', 14, INK)
    # Ugyldige rader
    ty = 370
    o += t(ox, ty, "Fire rader må rettes", 20, INK, 600)
    o += t(1392, ty, "Resten sendes uansett. Ingen blir stående.", 13, MUTED, 400, "end")
    cols = [ox, ox + 70, ox + 260, ox + 600]
    hy = ty + 30
    for c_, h_ in zip(cols, ["Rad", "Navn", "E-post i fila", "Feil"]):
        o += t(c_, hy, h_, 13, MUTED)
    o += ln(ox, hy + 7, 1392, hy + 7, HAIR)
    bad = [(37, "Amalie Dahl", "amalie.dahl@stud", "Mangler domene"), (88, "Tobias Olsen", "t.olsen@@stud.example.no", "To krøllalfa"),
           (141, "Karl Berg", "karl berg@stud.example.no", "Mellomrom i adressen"), (203, "Ingrid Vik", "", "Tom celle")]
    for i, (r_, n_, e_, f_) in enumerate(bad):
        y = hy + 34 + i * 44
        o += t(cols[0], y, r_, 15, INK, 600, "start", True) + t(cols[1], y, n_, 15, INK)
        o += rect(cols[2] - 8, y - 22, 320, 34, PAPER, RED, 1.1, 2) + t(cols[2], y, e_, 14, INK)
        o += t(cols[3], y, f_, 14, INK)
        o += t(1392, y, "Rett i fila og last opp på nytt", 13, MUTED, 400, "end") if False else ""
        o += ln(ox, y + 16, 1392, y + 16, GRID)
    # Handling
    y = 660
    o += button(ox, y, 300, 52, f"Send {valid} Invitasjoner", True, 16)
    o += t(ox + 318, y + 22, "Invitasjonen er gyldig i 14 dager.", 14, INK)
    o += t(ox + 318, y + 42, "Studenten registrerer seg selv fra lenken.", 13, MUTED)
    # Etterpå
    y = 760
    o += ln(ox, y, 1392, y, HAIR)
    o += t(ox, y + 36, "Etter utsending: de som mangler", 20, INK, 600)
    o += t(ox, y + 64, f'{R["uregistrert"]} av {R["paa_lista"]} er ikke registrert ennå.', 15, MUTED)
    o += button(ox, y + 84, 240, 44, f'Send påminnelse til {R["uregistrert"]}', False, 15)
    o += button(ox + 256, y + 84, 200, 44, "Registrer manuelt", False, 15)
    write("02-laerer-klasse.svg", 1440, 1000, "Struktur: Lag Klasse",
          "Navn og emnekode, Canvas-fil, e-postkolonne, ugyldige rader per rad, send Invitasjoner og status. Demodata.", o, SCREEN)


# ---------- 03 Klasseøkt ----------
def page03():
    begin("03")
    o = rect(0, 0, 1440, 1100, SCREEN)
    o += t(48, 56, "Klasseøkt", 34, INK, 600)
    o += t(1392, 44, "class-of-1994, IBE160", 15, MUTED, 400, "end") + t(1392, 66, "Demodata", 13, MUTED, 400, "end")
    o += t(48, 90, "Standarden heter Klassisk. Alle verdier sitter på kjeden der de virker. Du kan lagre uten å endre noe.", 16, MUTED)

    def param(x, y, name, val):
        return t(x, y, name, 14, MUTED) + t(x, y + 20, val, 17, INK, 600, "start", True) + ln(x, y + 26, x + max(len(str(val)) * 11, 30), y + 26, INK, 1)

    # Lang kjede: varer går mot høyre, ordre mot venstre
    pitch = 300
    bx0 = 150
    base = 320
    bw, unit = 120, 3.0
    rail = 124
    o += cloud(66, base - 18)
    o += pipe_h(76, bx0, base - 18, 4, 1.5)
    o += valve(112, base - 18, 6)
    o += delay(134, base - 18, 8)
    o += leader(112, base - 30, 112, rail + 32, False)
    o += param(48, rail, "Produksjonsforsinkelse", "2 uker")
    names = ["Fabrikk", "Distributør", "Grossist", "Detaljist"]
    for i, n_ in enumerate(names):
        x = bx0 + i * pitch
        o += box_up(x, base, bw, 12, unit, 12 * unit, ticks=False)
        o += t(x + bw / 2, base - 13, n_, 15, SCREEN, 600, "middle")
        end = x + bw + (pitch - bw) if i < 3 else x + bw + 110
        o += pipe_h(x + bw, end, base - 18, 4, 1.5)
        vx = x + bw + (pitch - bw) * .36 if i < 3 else x + bw + 44
        o += valve(vx, base - 18, 6)
        if i < 3:
            dx = x + bw + (pitch - bw) * .62
            o += delay(dx, base - 18, 8)
            o += leader(dx, base - 30, dx, rail + 32, False)
            o += param(dx - 30, rail, "Fraktforsinkelse", "2 uker")
            # ordre mot venstre, tynn informasjonspil
            o += info(x + bw + (pitch - bw) * .94, base + 44, x + bw + 4, base + 44, -8, INK, 1.1)
            o += delay(x + bw + (pitch - bw) * .5, base + 49, 6)
    # Rader over og under
    o += param(490, rail, "I hvert ledd", "4 enheter")
    o += leader(bx0 + pitch + bw + (pitch - bw) * .36, base - 28, 530, rail + 32, False)
    o += leader(bx0 + 74, base - 36, bx0 + 74, rail + 32)
    o += param(bx0 + 64, rail, "Startlager", "12")
    o += leader(bx0 + pitch + bw + (pitch - bw) * .5, base + 58, bx0 + pitch + bw + (pitch - bw) * .5, base + 78, False)
    o += t(bx0 + pitch + bw + (pitch - bw) * .5 - 30, base + 96, "Ordreforsinkelse", 14, MUTED) + t(bx0 + pitch + bw + (pitch - bw) * .5 - 30, base + 116, "2 uker", 17, INK, 600, "start", True)
    cx = bx0 + 3 * pitch + bw + 120
    o += cloud(cx, base - 18, INK, 1.4)
    o += leader(cx, base - 30, cx, rail + 32, False)
    dem = S17["demand"]
    o += param(cx - 90, rail, "Etterspørsel fra kunde", f"{dem[0]}, så {dem[4]} i Uke 5")
    o += t(48, base + 96, "Lagerkost", 14, MUTED) + t(48, base + 116, "0,50", 17, INK, 600, "start", True)
    o += leader(165, base, 80, base + 80)
    o += t(150, base + 96, "Restordrekost", 14, MUTED) + t(150, base + 116, "1,00", 17, INK, 600, "start", True)
    o += leader(195, base, 190, base + 80)
    o += t(320, base + 96, "Lengde", 14, MUTED) + t(320, base + 116, "36 uker", 17, INK, 600, "start", True)
    o += t(800, base + 96, "Veiledede uker", 14, MUTED) + t(800, base + 116, "1–4", 17, INK, 600, "start", True)
    o += para(960, base + 96, "Kildene er uenige om forsinkelser. Dette er produktets standard, ikke den eneste riktige.", 430, 14, 20, MUTED)
    # Tre spalter
    y = 480
    o += ln(48, y - 16, 1392, y - 16, HAIR)
    x1, x2, x3 = 48, 470, 880
    o += t(x1, y + 16, "Slik går den", 20, INK, 600)

    def choice(x, y, label, opts, sel):
        o_ = t(x, y, label, 14, MUTED)
        xx = x
        for op in opts:
            on = op == sel
            wd = len(op) * 8 + 26
            o_ += rect(xx, y + 8, wd, 34, INK if on else "none", INK, 1.1, 2)
            o_ += t(xx + wd / 2, y + 30, op, 14, SCREEN if on else INK, 500, "middle")
            xx += wd + 8
        return o_

    o += choice(x1, y + 54, "KI-modus", ["LLM-spillere", "Regelspillere"], "LLM-spillere")
    o += choice(x1, y + 128, "Debrief-modus", ["Gruppedebrief", "Individuell"], "Gruppedebrief")
    o += t(x1, y + 202, "Obligatorisk", 14, MUTED)
    o += rect(x1, y + 212, 22, 22, INK, INK, 1, 2) + path(f"M{x1 + 5},{y + 223} l4,5 l8,-10", "none", SCREEN, 2)
    o += t(x1 + 32, y + 228, "Merket Obligatorisk for alle i Klassen", 14, INK)
    o += field(x1, y + 266, 180, "Inaktivitetsgrense", "24 t", True)
    o += t(x1, y + 340, "Etter dette tar en KI-spiller setet.", 13, MUTED)
    # Datoer
    o += t(x2, y + 16, "Datoer", 20, INK, 600)
    dates = [("Start", "ti. 24. nov 2026"), ("Spillfrist", "ti. 8. des"), ("Debrief-frist", "fr. 11. des"), ("Testfrist", "fr. 18. des")]
    yy = y + 54
    for n_, v in dates:
        o += t(x2, yy, n_, 14, MUTED) + t(x2 + 150, yy, v, 15, INK, 500)
        o += ln(x2, yy + 10, x2 + 350, yy + 10, GRID)
        yy += 36
    o += t(x2, yy + 22, "Labtimer, Datalab A2", 16, INK, 600)
    yy += 52
    for v in ["to. 26. nov 14:15", "ma. 30. nov 10:15", "to. 3. des 14:15", "ma. 7. des 10:15"]:
        o += t(x2, yy, v, 15, INK)
        o += ln(x2, yy + 10, x2 + 350, yy + 10, GRID)
        yy += 32
    o += t(x2, yy + 8, "Legg til Labtime", 14, INK, 500, extra='text-decoration="underline"')
    # Fordeling
    o += t(x3, y + 16, "Fordeling", 20, INK, 600)
    o += t(x3, y + 46, "240 studenter fordelt tilfeldig på 60 spill à 4.", 15, MUTED)
    gx, gy = x3, y + 68
    cw, ch = 51, 42
    for i in range(60):
        cx_ = gx + (i % 10) * cw
        cy_ = gy + (i // 10) * ch
        for j in range(4):
            o += rect(cx_ + j * 10.5, cy_ + 8, 8.5, 18, STOCK if True else PAPER)
        o += ln(cx_, cy_ + 32, cx_ + 42, cy_ + 32, GRID)
    o += button(x3, gy + 262, 160, 44, "Kjør på nytt", False, 15)
    o += button(x3 + 172, gy + 262, 200, 44, "Bekreft fordeling", True, 15)
    o += ln(48, 926, 1392, 926, HAIR)
    o += button(48, 952, 280, 52, "Lagre Klasseøkt", True, 16)
    o += t(344, 976, "Kan lagres uten endring.", 14, INK)
    o += t(344, 996, "Du kan endre datoer og Labtimer fram til start.", 13, MUTED)
    write("03-laerer-spill.svg", 1440, 1100, "Struktur: Klasseøkt",
          "Spillinnstillinger festet til kjeden, KI-modus, Debrief-modus, Obligatorisk, datoer, Labtimer og fordelingsforhåndsvisning. Demodata.", o, SCREEN)


# ---------- 04 student hjem ----------
def body_register():
    o = t(20, 60, "Du er invitert", 28, INK, 600)
    o += para(20, 92, "IBE160, class-of-1994. Faglærer Bård har lagt deg til fra klasselisten. Invitasjonen er gyldig i 14 dager.", 345, 15, 21, MUTED)
    o += field(20, 176, 350, "E-post", "sara.moe@stud.example.no")
    o += field(20, 248, 350, "Navn", "Sara Moe")
    o += field(20, 320, 350, "Velg passord", "············")
    o += button(20, 396, 350, 52, "Opprett konto")
    o += para(20, 478, "Etterpå får du et Sete i en gruppe på fire. Tomme seter fylles av KI-spillere, og de er alltid merket.", 345, 14, 20, MUTED)
    y = 560
    o += t(20, y, "Dette er tegningen du skal bruke", 15, INK, 600)
    dg, g = diagram(18, y + 88, 354, 1, 1.1, order="done", labels=False)
    o += dg
    o += para(20, y + 184, "Bokser hoper seg opp. Rør går inn eller ut per Uke. Du bestemmer ett tall per Uke, resten regner systemet.", 345, 14, 20, MUTED)
    return o


def body_home():
    d = wk(11)
    o = t(20, 56, "Hei, Sara", 26, INK, 600) + t(370, 54, "Demodata", 13, MUTED, 400, "end")
    o += t(20, 80, "Spill 17, Grossist", 15, MUTED)
    # Setene
    y = 104
    bw, gp = 58, 40
    o += path("", "none")
    people = [("Detaljist", "Ida"), ("Grossist", "Sara"), ("Distributør", "Mikkel"), ("Fabrikk", "Jonas")]
    xs = [20 + i * (bw + gp) for i in range(4)]
    for i, (r, p) in enumerate(people):
        me = r == "Grossist"
        o += rect(xs[i], y + 18, bw, 26, PAPER if me else STOCK, RED if me else INK, 1.5 if me else 1.2)
        if i < 3:
            o += ln(xs[i] + bw, y + 31, xs[i] + bw + gp - 5, y + 31, INK, 1.1) + head(xs[i] + bw + gp, y + 31, 0, 6)
        o += t(xs[i], y + 11, p, 14, INK, 600 if me else 500)
        o += t(xs[i], y + 60, r, 13, MUTED)
    # Spillet venter på deg
    y = 192
    o += ln(20, y - 8, 370, y - 8, GRID)
    o += t(20, y + 22, "Spillet venter på deg", 22, INK, 600)
    o += t(20, y + 46, "Uke 11. Jonas venter også (3 min).", 14, MUTED)
    o += button(20, y + 60, 350, 52, "Gå til Uke 11")
    # Seks steg som kjede
    y = 330
    steps = [("Klassespill", "Pågår, Uke 11", "ti. 8. des", "now"), ("Debrief", "Etter Klassespillet", "fr. 11. des", ""), ("Quiz", "Etter Debriefen", "", ""),
             ("Replay", "Mot tre KI-spillere", "", ""), ("Individuell test", "Flervalg, tegning, langsvar", "fr. 18. des", ""), ("Rapport", "PDF når alt er levert", "", "")]
    rh = 50
    for i, (n_, s_, fr, st) in enumerate(steps):
        yy = y + i * rh
        o += rect(20, yy, 26, 26, PAPER, RED if st else INK, 1.5 if st else 1.2)
        if st:
            o += rect(20, yy + 13, 26, 13, STOCK)
        if i < 5:
            o += ln(33, yy + 26, 33, yy + rh - 5, INK, 1.1) + head(33, yy + rh, math.pi / 2, 6)
        o += t(60, yy + 12, n_, 15, INK, 600 if st else 500) + t(60, yy + 29, s_, 13, MUTED)
        if fr:
            o += t(370, yy + 12, "Frist", 13, MUTED, 400, "end") + t(370, yy + 29, fr, 13, INK, 500, "end")
    y = 648
    o += ln(20, y, 370, y, GRID)
    o += rich(20, y + 28, [("Neste frist ", 13, MUTED, 400, False), ("Spillfrist ti. 8. des", 15, INK, 600, False)])
    o += rich(20, y + 58, [("Labtime ", 13, MUTED, 400, False), ("to. 26. nov 14:15, Datalab A2", 15, INK, 500, False)])
    o += t(20, y + 82, "Se alle Labtimer", 14, INK, 500, extra='text-decoration="underline"')
    return o


def page04():
    begin("04")
    o = phone(24, 42, 1, body_register(), "Invitasjon og registrering")
    o += phone(434, 42, 1, body_home(), "Hjem under spill")
    x = 842
    o += t(x, 92, "Samme språk", 20, INK, 600)
    o += para(x, 120, "Setene og de seks stegene er tegnet som kjeder. Fylt betyr gjort eller har bestilt. Hen møter notasjonen allerede før første Uke.", 142, 14, 20, MUTED)
    write("04-student-hjem.svg", 1000, 900, "Struktur: Sara på mobil",
          "Registrering fra Invitasjon og hjem under spill med seter, seks steg, neste frist og Labtimer. Demodata.", o)


# ---------- 09 kontaktark ----------
def page09():
    begin("09")
    o = t(40, 60, "Alle andre sider", 38, INK, 600)
    o += t(1960, 56, "Lavere detaljnivå. Samme notasjon overalt. Demodata.", 15, MUTED, 400, "end")

    def lines(x, y, w, n, gap=20, c=HAIR, sw=6):
        return "".join(rect(x, y + i * gap, w * (1 - (i % 3) * .12), sw, c) for i in range(n))

    def ph(title):
        return t(20, 54, title, 26, INK, 600)

    # Studentrutene i 390-skala
    def st_invite():
        return ph("Du er invitert") + lines(20, 90, 340, 2) + "".join(rect(20, 160 + i * 74, 350, 44, PAPER, INK, 1.2, 2) for i in range(3)) + rect(20, 400, 350, 52, INK)

    def st_login():
        return ph("Logg inn") + "".join(rect(20, 120 + i * 74, 350, 44, PAPER, INK, 1.2, 2) for i in range(2)) + rect(20, 270, 350, 52, INK) + lines(20, 350, 200, 1)

    def st_rules():
        dg, _ = diagram(18, 280, 354, 1, 1.5, order="done", fs=18, vs=20, rail=120)
        return ph("Regler før første ordre") + dg + lines(20, 450, 340, 6, 28, HAIR, 8) + rect(20, 700, 350, 52, INK)

    def st_start():
        dg, _ = diagram(18, 220, 354, 5, 1.5, order="typed", typed=4, labels=False)
        return ph("Startoppgave") + lines(20, 80, 340, 2) + dg + "".join(rect(20, 360 + i * 60, 350, 46, PAPER, INK, 1.2, 2) for i in range(4)) + rect(20, 620, 350, 52, INK)

    def st_replay():
        dg, _ = diagram(18, 230, 354, 20, 1.5, order="done", run=REPLAY, labels=False, loop=True, vs=20, fs=18)
        tc, _m = timechart(54, 370, 306, 20, 3.0, run=REPLAY, label=False, gap=20, xlabels=False, tick=False)
        return ph("Replay, Uke 20") + dg + tc + rect(20, 700, 120, 60, PAPER, INK, 1.4, 2) + rect(154, 700, 216, 60, INK)

    def st_replay_review():
        tc, _m = timechart(54, 120, 306, 33, 3.0, run=REPLAY, label=False, gap=20, xlabels=False, tick=False)
        return ph("Replay-gjennomgang") + tc + lines(20, 470, 340, 7, 28, HAIR, 8) + t(20, 720, "Ikke like for like", 22, INK, 600)

    def st_test():
        o_ = ph("Individuell test")
        o_ += t(20, 96, "Flervalg", 20, INK, 600) + "".join(rect(20, 110 + i * 44, 350, 34, PAPER, INK, 1, 2) for i in range(3))
        o_ += t(20, 278, "Tegn: Lager uke for uke", 20, INK, 600)
        vals = S17["Grossist"]["lager"][4:11]
        for i, v in enumerate(vals):
            o_ += rect(30 + i * 48, 400 - v * 7, 40, v * 7, STOCK if i < 4 else "none", INK, 1)
        o_ += ln(20, 400, 370, 400, INK, 1) + rect(20, 420, 350, 40, "none", HAIR, 1)
        o_ += "".join(ln(20 + i * 50, 420, 20 + i * 50, 460, HAIR) for i in range(1, 7))
        o_ += t(20, 510, "Langsvar", 20, INK, 600) + rect(20, 524, 350, 190, PAPER, INK, 1, 2) + lines(34, 540, 310, 6, 26, HAIR, 6)
        return o_

    def st_ki():
        return ph("KI-vurdering") + t(20, 92, "KI-generert, kan ta feil.", 18, RED, 600) + t(20, 118, "Teller ikke. Er ikke en karakter.", 18, INK, 500) + lines(20, 160, 340, 12, 30, HAIR, 8) + rect(20, 560, 350, 120, "none", INK, 1.2)

    def st_report():
        tc, _m = timechart(70, 190, 250, 36, 2.2, label=False, gap=16, xlabels=False, tick=False)
        return rect(40, 40, 310, 620, PAPER, INK, 1.2) + t(60, 90, "Studentrapport", 24, INK, 600) + lines(60, 110, 260, 2, 18, HAIR, 5) + tc + lines(60, 490, 270, 6, 22, HAIR, 6) + rect(20, 700, 350, 52, INK)

    def st_allgames():
        o_ = ph("Alle spill side om side")
        sp = F["klasse"]["spill"]
        for i, g in enumerate(sp[:24]):
            x_, y_ = 20 + (i % 4) * 90, 90 + (i // 4) * 104
            vals = g["ordre"]["Fabrikk"]
            cy = y_ + 40
            o_ += t(x_, y_ + 6, g["spill"], 16, INK, 600, "start", True)
            o_ += band(x_, cy, 78, vals, 1.2, 78 / 36)
        return o_

    # Lærerflater i 960x600
    def lt(title):
        return t(32, 66, title, 42, INK, 600) + ln(32, 90, 928, 90, HAIR, 2)

    sp = F["klasse"]["spill"]

    def rows_(x, y, n, rh=44):
        o_ = ""
        for i in range(n):
            g = sp[i]
            o_ += micro_chain(x, y + i * rh, g, 200, 36, 30)
            o_ += trace(x + 230, y + i * rh - 16, 300, 32, g)
            o_ += ln(x, y + i * rh + 20, x + 860, y + i * rh + 20, GRID, 2)
        return o_

    def tc_home():
        return lt("Lærerhjem") + rows_(32, 150, 3, 70) + "".join(rect(32 + i * 300, 370, 280, 200, "none", INK, 2) for i in range(3))

    def tc_report():
        K = F["klasse"]["ferdige"]["forsterkning_per_rolle"]
        o_ = lt("Klasserapport")
        for i, r in enumerate(ROLES):
            q = K[r]
            y_ = 150 + i * 100
            sc = 58
            o_ += t(32, y_ + 16, r, 26, INK, 600)
            o_ += ln(250 + q["min"] * sc, y_ + 8, 250 + q["max"] * sc, y_ + 8, INK, 2)
            o_ += rect(250 + q["q1"] * sc, y_ - 12, (q["q3"] - q["q1"]) * sc, 40, STOCK)
            o_ += rect(250 + q["median"] * sc - 2, y_ - 12, 4, 40, SCREEN)
        return o_

    def tc_insight():
        tc, _m = timechart(90, 110, 840, 36, 3.8, label=False, gap=24, xlabels=False, tick=False)
        return lt("Spillinnsikt, uke for uke") + tc + ""

    def tc_student():
        dg, _ = diagram(32, 300, 560, 11, 2.2, order="done", labels=False)
        return lt("Studentside: Sara") + dg + lines(640, 130, 280, 8, 40, HAIR, 12)

    def tc_plenum():
        o_ = lt("Alle spill i plenum")
        for i, g in enumerate(sp[:60]):
            x_, y_ = 32 + (i % 10) * 90, 110 + (i // 10) * 78
            o_ += band(x_, y_ + 32, 80, g["ordre"]["Fabrikk"], 1.3, 80 / 36)
        return o_

    def tc_cross():
        FJ = F["klasse"]["fjoraaret"]
        K = F["klasse"]["ferdige"]["kjedekost"]
        o_ = lt("Tverrklasse-statistikk")
        sc = 830 / 3600
        for i, (n_, m_) in enumerate([("class-of-1994", K["median"]), (FJ["klasse"], FJ["median_kjedekost"])]):
            y_ = 150 + i * 150
            o_ += t(32, y_, n_, 26, INK, 600) + rect(32, y_ + 16, m_ * sc, 60, STOCK)
            o_ += t(32 + m_ * sc + 12, y_ + 58, nb(m_, 0), 30, INK, 600, "start", True)
        return o_

    def tc_msg():
        return lt("Meldinger") + "".join(ln(32, 150 + i * 56, 560, 150 + i * 56, GRID, 2) + rect(32, 120 + i * 56, 380, 14, HAIR) for i in range(7)) + rect(600, 120, 328, 300, PAPER, INK, 2) + rect(600, 440, 328, 60, INK)

    def tc_testgame():
        dg, _ = diagram(32, 280, 620, 11, 2.3, order="typed", typed=24, labels=False)
        return lt("Lærers testspill") + dg + t(690, 150, "Bare du og tre", 26, INK, 500) + t(690, 186, "KI-spillere", 26, INK, 500)

    def tc_admin():
        return lt("Admin-område") + "".join(rect(32, 130 + i * 90, 896, 70, "none", INK, 2) + rect(52, 155 + i * 90, 300, 18, HAIR) for i in range(5))

    def tc_users():
        return lt("Brukere og roller") + "".join(rect(32, 124 + i * 50, 260, 16, HAIR) + rect(350, 124 + i * 50, 200, 16, GRID) + ln(32, 150 + i * 50, 928, 150 + i * 50, GRID, 2) for i in range(9))

    def tc_cost():
        sp_ = F["klasse"]["spill"]
        vals = [sum(g["ki_seter"] for g in sp_[i:i + 5]) for i in range(0, 60, 5)]
        o_ = lt("KI-kostnad")
        for i, v in enumerate(vals):
            o_ += rect(60 + i * 70, 540 - v * 40, 56, v * 40, STOCK)
        return o_ + ln(32, 540, 928, 540, INK, 2)

    groups = [
        ("Student", 40, [
            ("Invitasjon og registrering", "Lenke fra e-post, ingen åpen påmelding.", st_invite), ("Logg inn", "E-post og passord.", st_login),
            ("Regler før første ordre", "Tegningen forklart på ett skjermbilde.", st_rules), ("Startoppgave", "Les av tegningen før første Uke.", st_start),
            ("Replay", "Sløyfen og Posisjon er nå på tegningen.", st_replay), ("Replay-gjennomgang", "Tilfeldig etterspørsel, ikke like for like.", st_replay_review),
            ("Individuell test", "Flervalg, tegne- og tabelloppgave, langsvar.", st_test), ("KI-vurdering", "Teller ikke, er aldri en karakter.", st_ki),
            ("Studentrapport (PDF)", "Dine grafer og beslutninger fra loggen.", st_report), ("Alle spill side om side", "Etter Debrief. Ingen rangering.", st_allgames)]),
    ]
    y = 100
    o += t(40, y, "Student", 22, INK, 600)
    y += 16
    pitch = 192
    sc = 174 / 390
    for i, (n_, d_, f_) in enumerate(groups[0][2]):
        x = 40 + i * pitch
        o += phone(x, y, sc, f_())
        o += t(x, y + 844 * sc + 22, n_, 14, INK, 600) if len(n_) * 7.6 < pitch else "".join(t(x, y + 844 * sc + 22 + j * 17, l_, 14, INK, 600) for j, l_ in enumerate(wrap(n_, pitch - 14, 14, .54)))
        hh = 17 if len(n_) * 7.6 >= pitch else 0
        o += para(x, y + 844 * sc + 42 + hh, d_, pitch - 16, 13, 17, MUTED)
    y = 604
    o += ln(40, y - 22, 1960, y - 22, HAIR)
    o += t(40, y + 6, "Faglærer", 22, INK, 600)
    y += 24
    teach = [("Lærerhjem", "Klasser og hva som haster nå.", tc_home), ("Klasserapport", "Forsterkning per Rolle, kvartiler, trakt.", tc_report),
             ("Spillinnsikt (uke for uke)", "Ett spill, alle Roller, samme tidsakse.", tc_insight), ("Studentside", "Én students seter, Forklaring og test.", tc_student),
             ("Alle spill i plenum", "60 bånd på én skjerm.", tc_plenum), ("Tverrklasse-statistikk", "Mot fjorårets klasse.", tc_cross),
             ("Meldinger", "Til spill, Rolle eller hele Klassen.", tc_msg), ("Lærers testspill", "Prøv Spillinnstillingene selv.", tc_testgame)]
    tw = 300
    pitch2 = 322
    th = 600 * tw / 960

    def thumb(x, y, n_, d_, f_):
        return (group(rect(0, 0, 960, 600, SCREEN, INK, 3, 10) + f_(), x, y, tw / 960) +
                t(x, y + th + 22, n_, 15, INK, 600) + para(x, y + th + 42, d_, tw - 10, 13, 17, MUTED))

    for i, (n_, d_, f_) in enumerate(teach[:6]):
        o += thumb(40 + i * pitch2, y, n_, d_, f_)
    y2 = y + th + 96
    for i, (n_, d_, f_) in enumerate(teach[6:]):
        o += thumb(40 + i * pitch2, y2, n_, d_, f_)
    ax = 40 + 2 * pitch2 + 20
    o += ln(ax - 16, y2 - 34, ax - 16, y2 + th + 70, HAIR)
    o += t(ax, y2 - 14, "Admin", 22, INK, 600)
    admin = [("Admin-område", "Klasser, kvoter, drift.", tc_admin), ("Brukere og roller", "Faglærer, assistent, student, admin.", tc_users), ("KI-kostnad", "Her vist med antall KI-seter i demodata.", tc_cost)]
    for i, (n_, d_, f_) in enumerate(admin):
        o += thumb(ax + i * pitch2, y2, n_, d_, f_)
    ny = y2 + th + 118
    o += ln(40, ny - 40, 1960, ny - 40, HAIR)
    o += t(40, ny, "Notasjonen følger studenten videre", 24, INK, 600)
    o += para(40, ny + 32, "I Individuell test tegner studenten selv beholdning og strøm. Det samme språket går igjen i Startoppgaven, Replay og Studentrapporten, slik at testen måler forståelse av tegningen og ikke hukommelse for et mønster.", 860, 15, 22, MUTED)
    rows_n = [("stock", "Beholdning", "hoper seg opp."), ("flow", "Strøm", "per uke, med ventil."), ("delay", "Forsinkelse", "om lag 4 uker."), ("info", "Informasjon", "tynn pil.")]
    for i, (k_, n_, tx_) in enumerate(rows_n):
        o += notation_row(1000 + (i % 2) * 460, ny + 8 + (i // 2) * 40, k_, n_, tx_)
    write("09-alle-sider.svg", 2000, 1400, "Struktur: kontaktark over alle andre sider",
          "Oversikt over øvrige sider for student, faglærer og admin. Demodata.", o)


# === SIDER SLUTT ===

PAGES = {"01": page01, "02": page02, "03": page03, "04": page04, "05": page05, "06": page06, "07": page07, "08": page08, "09": page09, "10": page10}

if __name__ == "__main__":
    wanted = sys.argv[1:] or list(PAGES)
    for k_ in wanted:
        PAGES[k_]()
