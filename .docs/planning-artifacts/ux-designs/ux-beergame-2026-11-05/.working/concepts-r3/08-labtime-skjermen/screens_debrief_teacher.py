"""07 Debrief og 08 Oversikt for Faglærer. Samme rutenett som Labtime-skjermen, nå for hele kjeden og hele klassen."""
import statistics as st

from e08grid import *
from screens_core import NAME, fmt_cost

ORDER_UP = ["Detaljist", "Grossist", "Distributør", "Fabrikk"]


def sec_title(d, x, y, n, title, width):
    """Stegnummeret bærer rekkefølgen i Debriefen."""
    d.line(x, y - 26, x + width, y - 26, INK, 1.2)
    if n:
        d.t(x, y, str(n), 22, 700, INK)
    return d.para(x + (24 if n else 0), y, title, width - 24, 22, 27, 600, INK)


def demand_band(d, ax, y0, h, scale):
    u = h / scale
    base = y0 + h
    dd = f"M{ax.xl(1):.1f} {base:.1f}"
    for w in range(1, 37):
        v = DEM[w - 1]
        dd += f" L{ax.xl(w):.1f} {base - v * u:.1f} L{ax.xr(w):.1f} {base - v * u:.1f}"
    dd += f" L{ax.xr(36):.1f} {base:.1f} Z"
    d.path(dd, BLUEF)
    d.line(ax.xl(1), base, ax.xr(36), base, HAIR2, 1)


def scrubber(d, x, y, w, wk, label=True):
    """Ukeskrubber: spoler kjeden. Tegnet som en tynn akse med håndtak."""
    ax = Axis(x, w, 1, 36)
    d.line(ax.xc(1), y, ax.xc(36), y, HAIR2, 2)
    d.line(ax.xc(1), y, ax.xc(wk), y, INK, 2)
    d.circle(ax.xc(wk), y, 7, PAPER, INK, 2)
    if label:
        d.t(ax.xc(1), y + 22, "Uke 1", 12, 400, INK3)
        d.t(ax.xc(36), y + 22, "Uke 36", 12, 400, INK3, "end")
        d.t(ax.xc(wk), y - 12, f"Uke {wk}", 13, 700, INK, "middle")
    return ax


# ---------- 07 ----------
def build_07():
    d = Doc("07-debrief", 2100, 1200, f"{NAME}, Gruppedebrief i fem steg",
            "Forklaring, avsløring av etterspørselen, hele kjeden med fire ledd og Rolle × Uke, ditt øyeblikk i Uke 11 med kjedens kostnad, quiz, og delt skjerm med samme rutenett som i Labtime.")
    d.t(40, 44, "Debrief, Spill 17: fra «hadde jeg rett?» til «hvorfor skjedde det?»", 28, 600, INK)

    # Steg 1
    x, w = 40, 300
    y = 104
    sec_title(d, x, y, 1, "Skriv Forklaringen først", w)
    d.t(x, y + 32, "Ditt netto lager, hele spillet", 14, 600, INK)
    ax = Axis(x + 30, w - 30, 1, 36)
    grid(d, ax, y + 42, 96, -40, 30, (-40, 0, 20), 13)
    net_area(d, ax, y + 42, 96, G.net, 1, 36)
    xaxis(d, ax, y + 156, [1, 12, 24, 36])
    d.t(x, y + 192, "Hvorfor svingte lageret ditt?", 15, 600, INK)
    d.rect(x, y + 202, w, 112, PAPER, HAIR2, 1, 6)
    d.para(x + 12, y + 226, "Restordren vokste, så jeg bestilte mye for å ta den igjen. Det som var på vei, regnet jeg lite med.", w - 24, 15, 20)
    d.button(x, y + 324, w, 44, "Send Forklaring", size=15)
    d.circle(x + 7, y + 391, 5, PAPER, INK, 1.5)
    d.para(x + 20, y + 396, "Avsløringen er låst til alle fire har sendt. Ida og Mikkel har sendt, Jonas skriver.", w - 20, 14, 19, fill=INK2)

    # Steg 2: klimaks
    x2, w2 = 380, 600
    sec_title(d, x2, y, 2, "Kundene bestilte 4, så 8. Etter det endret de seg aldri.", w2)
    ax2 = Axis(x2 + 28, w2 - 28, 1, 36)
    y0 = y + 30
    h = 330
    scale = 26
    u = h / scale
    for v in (0, 8, 16, 24):
        yy = y0 + h - v * u
        d.line(ax2.x0, yy, ax2.x1, yy, HAIR, 1)
        d.t(ax2.x0 - 5, yy + 4, v, 13, 400, INK3, "end")
    demand_band(d, ax2, y0, h, scale)
    bw = 5
    for k in range(1, 37):
        d.rect(ax2.xc(k) - bw / 2, y0 + h - G.order(k) * u, bw, G.order(k) * u, INK)
    d.path("M" + " L".join(f"{ax2.xc(k):.1f} {y0 + h - G.inn(k) * u:.1f}" for k in range(1, 37)), stroke=GREY, sw=1.6)
    d.t(ax2.xc(11) + 8, y0 + h - 24 * u + 12, "Din ordre, 24 i Uke 11", 15, 600, INK)
    d.t(ax2.xc(29.5), y0 + h - 8 * u - 10, "Kundenes etterspørsel: 8", 16, 700, BLUE, "middle", 'stroke="#FFFFFF" stroke-width="4" paint-order="stroke"')
    d.t(ax2.xc(2.5), y0 + h - 4 * u - 8, "4", 18, 700, BLUE, "middle")
    d.t(ax2.xc(19) + 6, y0 + h - 13 * u, "Ordre inn: det eneste du så", 15, 600, INK2)
    xaxis(d, ax2, y0 + h + 18, [1, 5, 10, 15, 20, 25, 30, 36], None)
    d.para(x2, y0 + h + 44, "Øvelsen heter Beer Game. Nesten alle grupper svinger slik, også i år. Det du så, var Idas ordrer, ikke kundene. Struktur gir atferd, derfor spør vi hvorfor og ikke hvem.", w2, 15, 20, fill=INK)
    d.t(x2, y0 + h + 96, "P4, P6", 13, 400, INK3)

    # Steg 3: hele kjeden, graf over tall
    x3, w3 = 1020, 1040
    sec_title(d, x3, y, 3, "Hele kjeden: svingningene vokser oppstrøms og kommer senere", w3)
    wk = 15
    d.t(x3, y + 30, "Kjeden i Uke 15. Dra i skrubberen for å spole.", 14, 400, INK2)
    scrubber(d, x3 + 560, y + 26, 470, wk)
    yb = chain_full(d, x3, y + 46, w3, wk, SEATS, u=0.95, ls=13, cost=True, demand=DEM[wk - 1], hi=58)
    ya = yb + 76
    ax3 = Axis(x3 + 120, w3 - 120 - 70, 1, 36)
    rh = 42
    fs = 32
    onset = {}
    for i, r in enumerate(reversed(ORDER_UP)):
        S = SEATS[r]
        yy = ya + i * rh
        ou = rh / fs
        order_bars(d, ax3, yy, rh - 4, S.order, 1, 36, fs, fill=INK if r == "Grossist" else ORD)
        d.t(x3, yy + rh - 18, r, 14, 600, INK)
        d.t(x3, yy + rh - 4, NAVN[r] + (", du" if r == "Grossist" else ""), 13, 400, INK2)
        d.t(ax3.x1 + 70, yy + rh - 6, fx1(K["forsterkning"][r]), 20, 700, INK, "end", 'style="font-variant-numeric:lining-nums proportional-nums"')
        first = next(k for k in range(1, 37) if S.order(k) >= 10)
        onset[r] = (ax3.xc(first), yy + rh - 4 - S.order(first) * (rh - 4) / fs, first)
    pts = [onset[r] for r in reversed(ORDER_UP)]
    d.path("M" + " L".join(f"{a:.1f} {b - 3:.1f}" for a, b, _ in pts), stroke=RED, sw=1.2)
    for a, b, k in pts:
        d.circle(a, b - 3, 3.5, RED, PAPER, 1.5)
        d.t(a - 7, b - 5, f"Uke {k}", 12, 600, RED, "end")
    d.line(ax3.xr(wk), ya - 4, ax3.xr(wk), ya + 4 * rh + 4 * 15 + 4, INK, 1, dash="2 3")
    # Rolle × Uke: ordre som tall, samme kolonner
    ym = ya + 4 * rh + 6
    rows = [(r, (lambda S: (lambda w: S.order(w)))(SEATS[r]), "flow") for r in reversed(ORDER_UP)]
    matrix(d, ax3, ym, rows, 1, 36, now=None, rh=15, size=10, lx=x3 + 112, lsize=12)
    xaxis(d, ax3, ym + 4 * 15 + 15, [1, 5, 10, 15, 20, 25, 30, 36], None, 12)
    d.t(x3, ym + 4 * 15 + 36, "Ordre per Rolle og Uke, som stolpe og som tall. Rødt punkt: første Uke med ordre på 10 eller mer. Til høyre: Forsterkning. P4, P5.", 13, 400, INK2)

    # Rad 2
    yb2 = 712
    x4, w4 = 40, 1040
    sec_title(d, x4, yb2, 4, "Ditt øyeblikk: Uke 11. Du bestilte 24 med 16 på vei. Og hva det kostet kjeden.", w4)
    mm = meteo(d, G, x4, yb2 + 20, 320, 11, 24, left=30, hn=136, hf=50, gap=14, t_flow="", t_ord="Din ordre", t_net="Dette så du", futnote=None)
    d.t(x4, mm["yflow"] - 7, f"Levering {G.levering(11)}, ordre inn {G.inn(11)}", 13, 600, INK)
    tx, tw = x4 + 350, 300
    d.t(tx, yb2 + 34, "Dette regnet du", 15, 600, INK)
    ny = d.para(tx, yb2 + 56, f"Posisjon {G.lager[10]} − {G.rest[10]} + {G.paavei(11)} = {G.posisjon(11)}. Med 24 ble den {G.posisjon(11) + 24}.", tw, 14, 19)
    d.t(tx, ny + 12, "Dette kostet det senere", 15, 600, INK)
    late = G.kostsum(36) - G.kostsum(24)
    assert all(G.rest[k - 1] == 0 for k in range(25, 37))
    ny = d.para(tx, ny + 32, f"{G.levering(15)} av de 24 kom i Uke 15. På vei toppet på {max(G.pv)} i Uke {G.pv.index(max(G.pv)) + 1}, og i Uke {G.lager.index(max(G.lager)) + 1} sto du med lager {max(G.lager)}. Lager i Uke 25 til 36 kostet {kr(late)}.", tw, 14, 19)
    d.t(tx, ny + 12, "Dette så de andre i Uke 11", 15, 600, INK)
    yy = ny + 34
    for r in ("Detaljist", "Distributør", "Fabrikk"):
        S = SEATS[r]
        d.t(tx, yy, f"{NAVN[r]}, {r}", 13, 400, INK)
        stt = f"lager {S.lager[10]}" if S.net(11) >= 0 else f"restordre {S.rest[10]}"
        d.t(tx + tw, yy, f"{stt}, ordre inn {S.inn(11)}", 13, 400, INK2, "end")
        d.line(tx, yy + 7, tx + tw, yy + 7, HAIR, 1)
        yy += 23
    d.para(tx, yy + 10, "KI-generert, kan ta feil: «Du reagerte på restordren du så, ikke på posisjonen. Mikkel fikk 24 fra deg uten å vite hvorfor.»", tw, 13, 18, fill=INK2)

    # Kjedens regning
    rx, rw = x4 + 690, 350
    d.t(rx, yb2 + 34, f"Kjedens regning: {kr(K['kjedekost'])}", 17, 700, INK)
    d.t(rx, yb2 + 54, "Per Rolle og kostnadsart, hele spillet", 13, 400, INK2)
    cols = [rx + 170, rx + 260, rx + rw]
    yy = yb2 + 80
    for c, hd in zip(cols, ("Lager", "Restordre", "Sum")):
        d.t(c, yy, hd, 13, 600, INK2, "end")
    d.line(rx, yy + 6, rx + rw, yy + 6, HAIR2, 1)
    yy += 26
    mx = max(K["kost_per_rolle"].values())
    tl = tr = 0
    for r in ORDER_UP:
        S = SEATS[r]
        cl, cr = S.cum_lager(36), S.cum_rest(36)
        tl += cl
        tr += cr
        d.t(rx, yy, r + (" (deg)" if r == "Grossist" else ""), 14, 600 if r == "Grossist" else 400, INK)
        for c, v in zip(cols, (cl, cr, cl + cr)):
            d.t(c, yy, nf(v), 14, 600 if c == cols[2] else 400, INK, "end")
        d.rect(rx, yy + 6, rw * cl / mx, 5, BLUE)
        d.rect(rx + rw * cl / mx, yy + 6, rw * cr / mx, 5, RED)
        yy += 34
    d.line(rx, yy - 20, rx + rw, yy - 20, HAIR2, 1)
    d.t(rx, yy, "Kjeden", 14, 700, INK)
    for c, v in zip(cols, (tl, tr, tl + tr)):
        d.t(c, yy, nf(v), 14, 700, INK, "end")
    assert abs(tl + tr - K["kjedekost"]) < 1e-9
    yy += 30
    B, A = FX["bare_sara_teller_paa_vei"], FX["alle_teller_paa_vei"]
    d.t(rx, yy, "Simulert, samme kunder", 14, 600, INK)
    yy += 22
    for lab, v in (("Bare Sara teller på vei", B["kjedekost"]), ("Alle fire teller på vei", A["kjedekost"])):
        d.t(rx, yy, lab, 14, 400, INK)
        d.t(cols[2], yy, nf(v), 14, 400, INK, "end")
        d.line(rx, yy + 7, rx + rw, yy + 7, HAIR, 1)
        yy += 24
    d.para(rx, yy + 6, f"Restordre er {nf(tr / (tl + tr) * 100, 0)} % av kjedens regning, fordi den koster dobbelt. Simulert viser sammenhengen, ikke en fasit. P3, P7, P8.", rw, 13, 17, fill=INK2)

    # Steg 5
    x5, w5 = 1120, 380
    sec_title(d, x5, yb2, 5, "Debrief-quiz", w5)
    ny = d.para(x5, yb2 + 34, f"Uke 11: lager {G.lager[10]}, restordre {G.rest[10]}, {G.paavei(11)} på vei. Hva er posisjonen før du bestiller?", w5, 16, 22, 600)
    opts = [(sg(-13), "wrong"), (str(G.posisjon(11)), "right"), ("16", None), ("29", None)]
    yy = ny + 6
    for lab, stt in opts:
        col = RED if stt == "wrong" else (INK if stt == "right" else HAIR2)
        d.rect(x5, yy, w5, 40, PAPER, col, 1.4 if stt else 1, 6)
        d.t(x5 + 14, yy + 26, lab, 16, 600, INK)
        if stt == "wrong":
            d.t(x5 + w5 - 14, yy + 26, "Ditt svar, ikke riktig", 14, 600, RED, "end")
        if stt == "right":
            d.t(x5 + w5 - 14, yy + 26, "Riktig", 14, 600, INK, "end")
        yy += 48
    ny = d.para(x5, yy + 10, "−13 er lager minus restordre. Da mangler det du allerede har bestilt: 0 − 13 + 16 = 3. Det står i kjeden i Uke 11 som 4, 4 og 8 i kø.", w5, 14, 19)
    d.t(x5, ny + 10, "P3", 13, 400, INK3)

    # Delt skjerm: samme rutenett som Labtime, hele kjeden
    xs, ws = 1540, 520
    sec_title(d, xs, yb2, None, "Delt skjerm: rutenettet for hele kjeden", ws)
    fy = yb2 + 14
    fh = 404
    d.rect(xs, fy, ws, fh, PAPER, HAIR2, 1.4, 8)
    ix = xs + 14
    iw = ws - 28
    d.t(ix, fy + 24, "Spill 17", 15, 700, INK)
    scrubber(d, ix + 150, fy + 20, iw - 150, 15, label=False)
    d.t(ix + 150 + (iw - 150) * 14.5 / 36, fy + 40, "Uke 15", 12, 700, INK, "middle")
    yb3 = chain_full(d, ix, fy + 48, iw, 15, SEATS, u=0.6, ls=11, cost=False, hi=58, names=False)
    ygr = yb3 + 76
    lw = iw * 0.64
    axs = Axis(ix + 74, lw - 74, 1, 36)
    rh2 = 34
    for i, r in enumerate(reversed(ORDER_UP)):
        S = SEATS[r]
        yr = ygr + i * (rh2 + 4)
        Ys = yscale(yr, rh2, -70, 60)
        d.line(axs.x0, Ys(0), axs.x1, Ys(0), HAIR2, 1)
        net_area(d, axs, yr, rh2, S.net, 1, 36, -70, 60, lw=1.3)
        d.t(ix, Ys(0) + 4, r, 12, 600, INK)
    d.line(axs.xr(15), ygr - 4, axs.xr(15), ygr + 4 * (rh2 + 4), INK, 1, dash="2 3")
    xaxis(d, axs, ygr + 4 * (rh2 + 4) + 12, [1, 12, 24, 36], None, 11)
    # kostnad per Rolle, akkumulert til Uke 15 og hele spillet
    cx0 = ix + lw + 14
    cw0 = iw - lw - 14
    d.t(cx0, ygr - 6, "Kostnad, kr", 12, 600, INK)
    mxc = max(K["kost_per_rolle"].values())
    for i, r in enumerate(reversed(ORDER_UP)):
        S = SEATS[r]
        yr = ygr + i * (rh2 + 4) + 14
        yr -= 4
        d.rect(cx0, yr, cw0 * S.cum_lager(36) / mxc, 8, BLUE)
        d.rect(cx0 + cw0 * S.cum_lager(36) / mxc, yr, cw0 * S.cum_rest(36) / mxc, 8, RED)
        d.t(cx0, yr + 22, nf(S.kostsum(36)), 12, 400, INK)
    d.t(cx0, ygr + 4 * (rh2 + 4) + 30, f"Kjeden {nf(K['kjedekost'])}", 12, 700, INK)
    d.para(xs, fy + fh + 20, "Gruppa ser samme fem ruter som Sara hadde i Labtime, nå med fire ledd. Hver student følger sitt eget steg på telefonen.", ws, 14, 19, fill=INK2)
    d.demodata(2060, 1190, "Demodata. Simulerte tall er merket Simulert.", 13, "end")
    d.save()


# ---------- 08 ----------
def status_txt(sp):
    return {"ferdig": "Ferdig", "pågår": "Pågår", "pauset": "Pause", "venter": "Venter"}[sp["status"]]


def class_cost(sp):
    return sum(v * HOLD if v > 0 else -v * BACK for r in ROLES for v in sp["netto_lager"][r])


def wk_cost(sp, w):
    return sum((lambda v: v * HOLD if v > 0 else -v * BACK)(sp["netto_lager"][r][w - 1]) for r in ROLES)


SPILL = KL["spill"]
for _sp in SPILL:
    assert abs(class_cost(_sp) - _sp["kjedekost"]) <= 0.5, _sp["spill"]
    for _r in ROLES:
        assert len(_sp["netto_lager"][_r]) == _sp["uke"], _sp["spill"]
FERDIG = [s for s in SPILL if s["status"] == "ferdig"]
assert len(FERDIG) == KL["ferdige"]["antall"]
assert st.median(s["kjedekost"] for s in FERDIG) == KL["ferdige"]["kjedekost"]["median"]


def med_net(role, w):
    return st.median(s["netto_lager"][role][w - 1] for s in FERDIG)


def med_ord(role, w):
    return st.median(s["ordre"][role][w - 1] for s in FERDIG)


def wall_row(d, x, y, sp, role, cw, h):
    vals = sp["netto_lager"][role]
    for k, v in enumerate(vals):
        d.rect(x + k * cw, y, cw - 0.6, h, wall_net(v))


def build_08():
    d = Doc("08-laerer-oversikt", 1600, 1000, f"{NAME}, Oversikt for Faglærer",
            "60 Klassespill på én 1440-skjerm: hva skjer nå, matriseveggen 60 spill × Uker med netto lager, status og hvem hvert spill venter på, og klassens kjede og kostnad aggregert over 41 ferdige spill.")
    fx0, fy0, fw, fh = 80, 24, 1440, 952
    d.rect(fx0, fy0, fw, fh, PAPER, HAIR2, 1.2, 8)
    X = fx0 + 24
    R = fx0 + fw - 24
    d.t(X, fy0 + 38, "Oversikt", 26, 700, INK)
    d.t(X + 112, fy0 + 38, "class-of-1994, IBE160", 15, 400, INK2)
    d.t(X + 300, fy0 + 38, "Spillfrist ti. 8. des. Labtime nå: ma. 30. nov 10:15, Datalab A2.", 15, 400, INK2)
    d.button(R - 300, fy0 + 14, 140, 36, "Vis i plenum", primary=False, size=14)
    d.button(R - 150, fy0 + 14, 150, 36, "Melding til Klassen", primary=False, size=14)

    counts = {k: sum(1 for s in SPILL if s["status"] == k) for k in ("venter", "pauset", "pågår", "ferdig")}
    near = sorted([s for s in SPILL if s["status"] == "venter"], key=lambda s: -s["ventet_timer"])
    top = near[0]
    # Hva skjer nå
    yn = fy0 + 82
    d.t(X, yn, "Hva skjer nå", 16, 600, INK)
    d.t(X + 120, yn, f"{counts['ferdig']} ferdig · {counts['pågår'] + counts['pauset']} pågår, herav {counts['pauset']} i Pause · {counts['venter']} venter", 15, 400, INK)
    y = yn + 28
    d.rect(X, y - 18, 820, 32, REDF, None, 1, 4)
    d.t(X + 10, y + 3, f"Nær overtakelse: Spill {top['spill']} venter på {top['navn']} ({top['venter_paa']}) i {top['ventet_timer']} t. KI overtar om {24 - top['ventet_timer']} t.", 15, 600, INK)
    d.button(X + 610, y - 14, 112, 24, "Send Melding", size=13)
    d.button(X + 730, y - 14, 82, 24, "Pause", primary=False, size=13)
    y += 30
    d.t(X + 10, y, "Venter også: " + ", ".join(f"Spill {s['spill']}, {s['navn']} ({s['venter_paa']}), {s['ventet_timer']} t" for s in near[1:]), 14, 400, INK)
    y += 22
    pa = [s for s in SPILL if s["status"] == "pauset"]
    kisum = sum(s["ki_seter"] for s in SPILL)
    ki = sum(1 for s in SPILL if s["ki_seter"] > 0)
    d.t(X + 10, y, "Pause: " + ", ".join(f"Spill {s['spill']}" for s in pa) + f", fortsetter {pa[0]['fortsetter']}. {kisum} KI-spillere i {ki} spill.", 14, 400, INK)

    # Trakten
    tx = X + 870
    d.t(tx, yn, "Trakten", 16, 600, INK)
    tr = KL["traktA"]
    steps = [("Registrert", tr["registrert"]), ("Klassespill", tr["klassespill_ferdig"]), ("Debrief", tr["debrief_ferdig"]),
             ("Quiz", tr["quiz_bestått"]), ("Replay", tr["replay_ferdig"]), ("Test", tr["test_levert"]), ("KI-vurdering", tr["ki_vurdering_klar"])]
    colw = (R - tx) / 7
    for i, (lab, v) in enumerate(steps):
        xx = tx + i * colw
        hh = 42 * v / steps[0][1]
        base = yn + 58
        d.rect(xx, base - hh, colw - 8, max(hh, 1), ORD if v else HAIR)
        d.t(xx, base + 18, v, 14, 600, INK)
        d.t(xx, base + 34, lab, 12, 400, INK2)

    # Filterrad
    yf = fy0 + 214
    d.line(X, yf - 22, R, yf - 22, HAIR, 1)
    labs = [("Alle", len(SPILL)), ("Venter", counts["venter"]), ("Pause", counts["pauset"]), ("Pågår", counts["pågår"]), ("Ferdig", counts["ferdig"]), ("Med KI-spiller", ki)]
    xx = X
    for i, (lab, c) in enumerate(labs):
        s = f"{lab} {c}"
        wd = text_w(s, 13) + 18
        d.rect(xx, yf - 12, wd, 24, INK if i == 0 else PAPER, None if i == 0 else HAIR2, 1, 4)
        d.t(xx + wd / 2, yf + 4, s, 13, 600, PAPER if i == 0 else INK, "middle")
        xx += wd + 6
    xx += 18
    d.t(xx, yf + 4, "Rolle i veggen", 13, 400, INK2)
    xx += text_w("Rolle i veggen", 13) + 8
    for r in ORDER_UP:
        d.t(xx, yf + 4, r, 13, 700 if r == "Fabrikk" else 400, INK, extra='text-decoration="underline"' if r == "Fabrikk" else "")
        xx += text_w(r, 13) + 12
    d.t(R - 470, yf + 4, "Vis som tabell", 13, 600, BLUE, "start", 'text-decoration="underline"')

    # Matriseveggen
    wx = X + 160
    cw = 9.6
    wall_w = 36 * cw
    hx = {"spill": X, "status": X + 34, "uke": wx + wall_w + 26, "venter": wx + wall_w + 36, "ki": wx + wall_w + 236, "kost": wx + wall_w + 300}
    yh = yf + 34
    for k, hd, a in (("spill", "Spill", "start"), ("status", "Status", "start"), ("uke", "Uke", "end"), ("venter", "Venter på / neste", "start"),
                     ("ki", "KI", "end"), ("kost", "Kjede, kr", "end")):
        d.t(hx[k], yh, hd, 12, 600, INK2, a)
    d.t(wx, yh, "Netto lager, Fabrikk, Uke 1 til nå", 12, 600, INK2)
    d.line(X, yh + 5, hx["kost"], yh + 5, HAIR2, 1)
    rank = {"venter": 0, "pauset": 1, "pågår": 2, "ferdig": 3}
    ordered = sorted(SPILL, key=lambda s: (rank[s["status"]], -(s.get("ventet_timer") or 0), -s["uke"] if s["status"] == "pågår" else s["kjedekost"]))
    rh = 9.6
    y = yh + 12
    cur = None
    names = {"venter": "Venter", "pauset": "Pause", "pågår": "Pågår", "ferdig": "Ferdig, lavest kjedekost øverst"}
    for sp in ordered:
        if sp["status"] != cur:
            cur = sp["status"]
            y += 3
            d.t(X, y + 9, f"{names[cur]} {counts[cur]}", 12, 700, INK)
            y += 12
        isnear = sp["spill"] == top["spill"]
        if isnear:
            d.rect(X - 4, y - 1, hx["kost"] - X + 8, rh + 1, REDF, None, 1, 2)
        fs = 9.5
        d.t(hx["spill"], y + 8, sp["spill"], fs, 600, INK)
        d.t(hx["status"], y + 8, status_txt(sp), fs, 400, INK)
        wall_row(d, wx, y, sp, "Fabrikk", cw, rh - 1)
        if sp["status"] != "ferdig":
            d.line(wx + sp["uke"] * cw + 1, y - 1, wx + sp["uke"] * cw + 1, y + rh, INK, 1.4)
        d.t(hx["uke"], y + 8, sp["uke"], fs, 400, INK, "end")
        if sp["status"] == "venter":
            d.t(hx["venter"], y + 8, f"{sp['navn']}, {sp['venter_paa']}, {sp['ventet_timer']} t", fs, 600 if isnear else 400, INK)
        elif sp["status"] == "pauset":
            d.t(hx["venter"], y + 8, f"Fortsetter {sp['fortsetter']}", fs, 400, INK2)
        elif sp["status"] == "ferdig":
            d.t(hx["venter"], y + 8, f"Fabrikk {fx1(sp['forsterkning']['Fabrikk'])}", fs, 400, INK2)
        d.t(hx["ki"], y + 8, sp["ki_seter"] or "", fs, 400, INK, "end")
        d.t(hx["kost"], y + 8, nf(sp["kjedekost"], 0), fs, 400, INK, "end")
        y += rh
    # fargeforklaring under veggen
    ly = y + 22
    d.t(X, ly, "Restordre", 12, 400, INK2)
    xx = X + 62
    for v in (-50, -30, -15, -5, 0, 5, 15, 30, 50):
        d.rect(xx, ly - 10, 22, 12, wall_net(v))
        xx += 24
    d.t(xx + 4, ly, "Lager. Trinn: 1–2, 3–10, 11–25, 26–45, over 45. Mørk strek: nå i spill som pågår. Tall i tabellvisningen.", 12, 400, INK2)

    # Høyre: klassen aggregert, samme rutenett
    rx = hx["kost"] + 40
    rw = R - rx
    d.line(rx - 20, yf + 20, rx - 20, fy0 + fh - 20, HAIR, 1)
    d.t(rx, yh, f"Klassens kjede, Uke 15, median av {len(FERDIG)} ferdige spill", 13, 600, INK)
    wk = 15
    kund_w = 60
    seg = (rw - kund_w) / 4
    u = 1.2
    yb = yh + 18 + 14 + 30 * u + 8
    d.line(rx, yb, R, yb, HAIR2, 1)
    d.t(rx, yb - 4, "Kundene", 12, 600, INK)
    d.t(rx, yh + 22, "Ordre", 12, 400, INK2)
    for i, r in enumerate(ORDER_UP):
        x0 = rx + kund_w + i * seg
        mv = med_net(r, wk)
        node_box(d, x0 + 10, yb, mv, u, 20)
        d.t(x0 + 26, yb - 4, r, 12, 600, INK)
        d.t(x0 + 26, yb + 16, ("Lager " if mv >= 0 else "Restordre ") + sg(abs(mv)), 12, 400, INK)
        d.t(x0, yh + 22, sg(med_ord(r, wk)), 12, 600, INK)
        arrow(d, x0 + 18, yh + 18, x0 + seg - 8, INK3, 0.8, 5)
    # median netto lager per Rolle over tid
    yg = yb + 60
    d.t(rx, yg, "Netto lager per Uke, median av ferdige spill", 13, 600, INK)
    axc = Axis(rx + 76, rw - 76, 1, 36)
    rhh = 34
    for i, r in enumerate(reversed(ORDER_UP)):
        yr = yg + 10 + i * (rhh + 4)
        Ys = yscale(yr, rhh, -30, 20)
        d.line(axc.x0, Ys(0), axc.x1, Ys(0), HAIR2, 1)
        net_area(d, axc, yr, rhh, (lambda rr: (lambda w: med_net(rr, w)))(r), 1, 36, -30, 20, lw=1.3)
        d.t(rx, Ys(0) + 4, r, 12, 400, INK)
        lo = min(med_net(r, w) for w in range(1, 37))
        d.t(axc.x1, yr + rhh + 2, f"laveste {sg(lo)}", 11, 400, INK2, "end")
    d.line(axc.xr(wk), yg + 8, axc.xr(wk), yg + 10 + 4 * (rhh + 4), INK, 1, dash="2 3")
    xaxis(d, axc, yg + 10 + 4 * (rhh + 4) + 12, [1, 12, 24, 36], None, 11)

    # Kostnadsbildet: kjedekost per ferdig spill mot fjoråret
    yc = yg + 10 + 4 * (rhh + 4) + 48
    F = KL["ferdige"]["kjedekost"]
    FJ = KL["fjoraaret"]
    d.t(rx, yc, f"Kjedekostnad per ferdig spill, kr", 13, 600, INK)
    axk_x0, axk_w = rx + 10, rw - 20
    lo_, hi_ = 0, 4000
    X_ = lambda v: axk_x0 + (v - lo_) / (hi_ - lo_) * axk_w
    yd = yc + 34
    d.rect(X_(F["q1"]), yd - 12, X_(F["q3"]) - X_(F["q1"]), 24, TINT)
    for s in FERDIG:
        d.circle(X_(s["kjedekost"]), yd + ((s["spill"] * 7) % 15 - 7) * 0.9, 3, ORD)
    d.line(X_(F["median"]), yd - 16, X_(F["median"]), yd + 16, INK, 2)
    d.line(X_(FJ["median_kjedekost"]), yd - 16, X_(FJ["median_kjedekost"]), yd + 16, INK, 1, dash="3 3")
    d.t(X_(F["median"]) - 4, yd - 20, f"I år, median {nf(F['median'], 0)}", 12, 600, INK, "end")
    d.t(X_(FJ["median_kjedekost"]) + 4, yd - 20, f"Fjoråret {nf(FJ['median_kjedekost'], 0)}", 12, 400, INK2)
    for v in (0, 1000, 2000, 3000, 4000):
        d.t(X_(v), yd + 32, nf(v, 0), 11, 400, INK3, "middle")
    d.t(rx, yd + 52, f"Grått felt: midterste halvdel ({nf(F['q1'], 0)} til {nf(F['q3'], 0)}). Fjoråret: {FJ['spill']} spill i {FJ['klasse']}.", 12, 400, INK2)
    # klassens kostnad per Uke, delt i art
    yk = yd + 80
    d.t(rx, yk, "Klassens kostnad per Uke, alle ferdige spill, kr", 13, 600, INK)
    wl = [sum(sum(max(s["netto_lager"][r][w - 1], 0) * HOLD for r in ROLES) for s in FERDIG) for w in range(1, 37)]
    wr = [sum(sum(max(-s["netto_lager"][r][w - 1], 0) * BACK for r in ROLES) for s in FERDIG) for w in range(1, 37)]
    assert abs(sum(wl) + sum(wr) - sum(class_cost(s) for s in FERDIG)) < 1e-6
    topk = 5000
    assert max(a + b for a, b in zip(wl, wr)) <= topk
    hk = 70
    Yk = yscale(yk + 10, hk, 0, topk)
    for v in (0, 2500, 5000):
        d.line(axc.x0, Yk(v), axc.x1, Yk(v), HAIR2 if v == 0 else HAIR, 1)
        d.t(axc.x0 - 5, Yk(v) + 4, nf(v, 0), 11, 400, INK3, "end")
    bw = axc.slot - 2
    for w in range(1, 37):
        a, b = wl[w - 1], wr[w - 1]
        d.rect(axc.xc(w) - bw / 2, Yk(a), bw, Yk(0) - Yk(a), BLUE)
        d.rect(axc.xc(w) - bw / 2, Yk(a + b), bw, Yk(a) - Yk(a + b), RED)
    xaxis(d, axc, yk + 10 + hk + 13, [1, 12, 24, 36], None, 11)
    tot = sum(wl) + sum(wr)
    d.t(rx, yk + hk + 44, f"Lager {nf(sum(wl), 0)} kr, restordre {nf(sum(wr), 0)} kr, til sammen {nf(tot, 0)} kr.", 12, 400, INK2)
    d.demodata(R, fy0 + fh - 10, a="end")
    d.save()


if __name__ == "__main__":
    build_07()
    build_08()
