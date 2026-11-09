"""07 Debrief og 08 lærerens oversikt."""
from statistics import median

from vlib import *
from screens_core import NAME, waiting_rows

ALLE_SEATS = {r: Seat(r, FX["alle_teller_paa_vei"]) for r in ROLES}
UP = ["Fabrikk", "Distributør", "Grossist", "Detaljist"]
ROLE_LINE = {"Detaljist": "#8396AC", "Grossist": INK, "Distributør": "#56708B", "Fabrikk": "#33506E"}
BLOCKS = [(a, a + 3) for a in range(1, 37, 4)]


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


def table_row(d, ax, x, ry, rh, label, vals, size=12, cell=None, lab_w=600, lab_col=INK, every=1, bold_at=None):
    """En tabellrad på grafens akse. vals(k) -> tall eller None. cell(v) -> (fyll, tekstfarge)."""
    base = ry + rh / 2 + size * 0.36
    d.t(x, base, label, size, lab_w, lab_col)
    for k in range(ax.wmin, ax.wmax + 1):
        v = vals(k)
        if v is None or (k - ax.wmin) % every:
            continue
        fill, col = cell(v) if cell else (None, INK)
        if fill:
            d.rect(ax.xl(k) + 0.6, ry + 1.2, ax.slot - 1.2, rh - 2.4, fill)
        s = sg(v) if isinstance(v, int) else str(v)
        fs = size
        while text_w(s, fs) > ax.slot - 2 and fs > 9:
            fs -= 0.5
        d.t(ax.xc(k), base, s, fs, 700 if k == bold_at else 400, col, "middle")


# ---------- 07 ----------
def build_07():
    """Debriefen fra Labtime-skjermen (08), portert til graf over tabell og til kjedens retning
    (oppstrøms til venstre, varene mot høyre)."""
    d = Doc("07-debrief", 2100, 1200, f"{NAME}, Gruppedebrief i fem steg",
            "Forklaring først, avsløring av etterspørselen, hele kjeden med skrubber og ordrestolper over Rolle × Uke, "
            "ditt øyeblikk i Uke 11 med Kjedens regning, quiz, og delt skjerm for hele kjeden.")
    d.t(40, 44, "Debrief, Spill 17: fra «hadde jeg rett?» til «hvorfor skjedde det?»", 28, 600, INK)

    # Steg 1: Forklaringen først
    x, w, y = 40, 300, 104
    sec_title(d, x, y, 1, "Skriv Forklaringen først", w)
    d.t(x, y + 32, "Ditt netto lager, hele spillet", 14, 600, INK)
    ax = Axis(x + 30, w - 30, 1, 36)
    grid(d, ax, y + 42, 96, -40, 30, (-40, 0, 20), 13)
    net_area(d, ax, y + 42, 96, G.net, 1, 36)
    for k in range(1, 37):
        f, _ = net_cell(G.net(k))
        d.rect(ax.xl(k) + 0.4, y + 146, ax.slot - 0.8, 12, f)
    d.t(x, y + 156, "Uke", 12, 400, INK3)
    xaxis(d, ax, y + 176, [1, 12, 24, 36], size=12)
    d.t(x, y + 210, "Hvorfor svingte lageret ditt?", 15, 600, INK)
    d.rect(x, y + 220, w, 112, PAPER, HAIR2, 1, 6)
    d.para(x + 12, y + 244, "Restordren vokste, så jeg bestilte mye for å ta den igjen. Det som var på vei, regnet jeg lite med.", w - 24, 15, 20)
    d.button(x, y + 344, w, 44, "Send Forklaring", size=15)
    d.circle(x + 7, y + 411, 5, PAPER, INK, 1.5)
    d.para(x + 20, y + 416, "Avsløringen er låst til alle fire har sendt. Ida og Mikkel har sendt, Jonas skriver.", w - 20, 14, 19, fill=INK2)

    # Steg 2: klimaks, graf over tabell
    x2, w2 = 380, 600
    sec_title(d, x2, y, 2, "Kundene bestilte 4, så 8. Etter det endret de seg aldri.", w2)
    ax2 = Axis(x2 + 76, w2 - 76, 1, 36)
    y0, h, scale = y + 30, 270, 26
    u = h / scale
    for v in (0, 8, 16, 24):
        yy = y0 + h - v * u
        d.line(ax2.x0, yy, ax2.x1, yy, HAIR, 1)
        d.t(ax2.x0 - 5, yy + 4, v, 13, 400, INK3, "end")
    demand_band(d, ax2, y0, h, scale)
    bw = 5
    for k in range(1, 37):
        d.rect(ax2.xc(k) - bw / 2, y0 + h - G.order(k) * u, bw, G.order(k) * u, INK)
    d.path(pts_path([(ax2.xc(k), y0 + h - G.inn(k) * u) for k in range(1, 37)]), stroke=GREY, sw=1.6)
    d.t(ax2.xc(11) + 8, y0 + h - 24 * u + 12, "Din ordre, 24 i Uke 11", 15, 600, INK)
    d.t(ax2.xc(29.5), y0 + h - 8 * u - 10, "Kundenes etterspørsel: 8", 16, 700, BLUE, "middle", 'stroke="#FFFFFF" stroke-width="4" paint-order="stroke"')
    d.t(ax2.xc(2.5), y0 + h - 4 * u - 8, "4", 18, 700, BLUE, "middle")
    d.t(ax2.xc(19) + 6, y0 + h - 13 * u, "Ordre inn: det eneste du så", 15, 600, INK2)
    ty = y0 + h + 4
    rh = 19
    table_row(d, ax2, x2, ty, rh, "Uke", lambda k: k if k % 5 == 0 or k == 1 else None, 12, lab_w=600, lab_col=INK2)
    table_row(d, ax2, x2, ty + rh, rh, "Kundene", lambda k: DEM[k - 1], 11)
    table_row(d, ax2, x2, ty + 2 * rh, rh, "Ordre inn", G.inn, 11)
    table_row(d, ax2, x2, ty + 3 * rh, rh, "Din ordre", G.order, 11, cell=seq_cell, bold_at=11)
    for i in range(1, 5):
        d.line(x2, ty + i * rh, ax2.x1, ty + i * rh, HAIR, 1)
    ny = d.para(x2, ty + 4 * rh + 28, "Øvelsen heter Beer Game. Nesten alle grupper svinger slik, også i år. Det du så, var Idas ordrer, ikke kundene. Struktur gir atferd, derfor spør vi hvorfor og ikke hvem.", w2, 15, 20, fill=INK)
    d.t(x2, ny + 6, "P4, P6", 13, 400, INK3)

    # Steg 3: hele kjeden med skrubber, ordrestolper over Rolle × Uke
    x3, w3 = 1020, 1040
    sec_title(d, x3, y, 3, "Hele kjeden: svingningene vokser oppstrøms og kommer senere", w3)
    wk = 15
    d.t(x3, y + 30, "Kjeden i Uke 15. Dra i skrubberen for å spole.", 14, 400, INK2)
    scrubber(d, x3 + 560, y + 26, 470, wk)
    yk = chain_full(d, SEATS, x3, y + 56, w3, wk, ls=13, un=0.5, upipe=0.5)
    ya = yk + 20
    ax3 = Axis(x3 + 120, w3 - 120 - 70, 1, 36)
    rhb, fs = 40, 32
    onset = {}
    for i, r in enumerate(UP):
        S = SEATS[r]
        yy = ya + i * rhb
        order_bars(d, ax3, yy, rhb - 4, S.order, 1, 36, fs, fill=INK if r == "Grossist" else ORD)
        d.t(x3, yy + rhb - 18, r, 14, 600, INK)
        d.t(x3, yy + rhb - 3, NAVN[r] + (", du" if r == "Grossist" else ""), 13, 400, INK2)
        d.t(ax3.x1 + 70, yy + rhb - 6, fx1(K["forsterkning"][r]), 20, 700, INK, "end", 'style="font-variant-numeric:lining-nums proportional-nums"')
        first = next(k for k in range(1, 37) if S.order(k) >= 10)
        onset[r] = (ax3.xc(first), yy + rhb - 4 - S.order(first) * (rhb - 4) / fs, first)
    pts = [onset[r] for r in UP]
    d.path(pts_path([(a, b - 3) for a, b, _ in pts]), stroke=RED, sw=1.2)
    for a, b, k in pts:
        d.circle(a, b - 3, 3.5, RED, PAPER, 1.5)
        d.t(a - 7, b - 2, f"Uke {k}", 12, 600, RED, "end", 'stroke="#FFFFFF" stroke-width="3" paint-order="stroke"')
    ym = ya + 4 * rhb + 6
    rhm = 16
    for i, r in enumerate(UP):
        ry = ym + i * rhm
        d.line(x3 + 40, ry, ax3.x1, ry, HAIR, 1)
        table_row(d, ax3, x3 + 40, ry, rhm, r, SEATS[r].order, 11, cell=seq_cell, lab_w=600 if r == "Grossist" else 400)
    d.line(x3 + 40, ym + 4 * rhm, ax3.x1, ym + 4 * rhm, HAIR, 1)
    d.line(ax3.xr(wk), ya - 4, ax3.xr(wk), ym + 4 * rhm, INK, 1, dash="2 3")
    xaxis(d, ax3, ym + 4 * rhm + 15, [1, 5, 10, 15, 20, 25, 30, 36], None, 12)
    d.t(x3, ym + 4 * rhm + 38, "Ordre per Rolle og Uke, som stolpe og som tall i samme kolonne. Rødt punkt: første Uke med ordre på 10 eller mer. Til høyre: Forsterkning. P4, P5.", 13, 400, INK2)

    # Rad 2. Steg 4: ditt øyeblikk og Kjedens regning
    yb2 = 700
    x4, w4 = 40, 1040
    sec_title(d, x4, yb2, 4, "Ditt øyeblikk: Uke 11. Du bestilte 24 med 16 på vei. Og hva det kostet kjeden.", w4)
    d.t(x4, yb2 + 34, "Dette så du", 15, 600, INK)
    gtable(d, G, x4, yb2 + 44, 320, 11, 24, wmin=5, wmax=15, lw=70, hn=64, hc=22, rh=19, ls=12, gapf=6,
           rows=("inn", "lev", "net", "pv", "ord", "kost"), titles=False, netlabel=True, cost_tick=False)
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

    rx, rw = x4 + 690, 350
    d.t(rx, yb2 + 34, f"Kjedens regning: {kr(K['kjedekost'])}", 17, 700, INK)
    d.t(rx, yb2 + 54, "Per Rolle og kostnadsart, hele spillet", 13, 400, INK2)
    yy, tl, tr = chain_bill_table(d, rx, yb2 + 82, rw, K, size=14, lh=33, sim=True, cols=[rx + 170, rx + 260, rx + rw])
    d.para(rx, yy + 14, f"Restordre er {nf(tr / (tl + tr) * 100, 0)} % av kjedens regning, fordi den koster dobbelt. Simulert viser sammenhengen, ikke en fasit. P3, P7, P8.", rw, 13, 17, fill=INK2)

    # Steg 5: quiz
    x5, w5 = 1120, 380
    sec_title(d, x5, yb2, 5, "Debrief-quiz", w5)
    ny = d.para(x5, yb2 + 34, f"Uke 11: lager {G.lager[10]}, restordre {G.rest[10]}, {G.paavei(11)} på vei. Hva er posisjonen før du bestiller?", w5, 16, 22, 600)
    yy = ny + 6
    for lab, stt in ((sg(-13), "wrong"), (str(G.posisjon(11)), "right"), ("16", None), ("29", None)):
        col = RED if stt == "wrong" else (INK if stt == "right" else HAIR2)
        d.rect(x5, yy, w5, 40, PAPER, col, 1.4 if stt else 1, 6)
        d.t(x5 + 14, yy + 26, lab, 16, 600, INK)
        if stt == "wrong":
            d.t(x5 + w5 - 14, yy + 26, "Ditt svar, ikke riktig", 14, 600, RED, "end")
        if stt == "right":
            d.t(x5 + w5 - 14, yy + 26, "Riktig", 14, 600, INK, "end")
        yy += 48
    ny = d.para(x5, yy + 10, "−13 er lager minus restordre. Da mangler det du allerede har bestilt: 0 − 13 + 16 = 3. Det står i kolonne 11 i din egen tabell, og som 4, 4 og 8 på røret i kjeden.", w5, 14, 19)
    d.t(x5, ny + 10, "P3", 13, 400, INK3)

    # Delt skjerm: hele kjeden
    xs, ws = 1540, 520
    sec_title(d, xs, yb2, None, "Delt skjerm: hele kjeden", ws)
    fy, fh = yb2 + 14, 366
    d.rect(xs, fy, ws, fh, PAPER, HAIR2, 1.4, 8)
    ix, iw = xs + 14, ws - 28
    d.t(ix, fy + 26, "Spill 17", 15, 700, INK)
    scrubber(d, ix + 120, fy + 21, iw - 120, 15, label=False)
    sax = Axis(ix + 120, iw - 120, 1, 36)
    d.t(sax.xc(15), fy + 44, "Uke 15", 12, 700, INK, "middle")
    yb3 = chain_full(d, SEATS, ix, fy + 54, iw, 15, ls=11, un=0.3, upipe=0.35, cost=False, names=False, order_row=False)
    ygr = yb3 + 8
    lw_ = iw * 0.64
    axs = Axis(ix + 74, lw_ - 74, 1, 36)
    rh2 = 34
    for i, r in enumerate(UP):
        S = SEATS[r]
        yr = ygr + i * (rh2 + 4)
        Ys = yscale(yr, rh2, -70, 60)
        d.line(axs.x0, Ys(0), axs.x1, Ys(0), HAIR2, 1)
        net_area(d, axs, yr, rh2, S.net, 1, 36, -70, 60, lw=1.3)
        d.t(ix, Ys(0) + 4, r, 12, 600, INK)
    d.line(axs.xr(15), ygr - 4, axs.xr(15), ygr + 4 * (rh2 + 4), INK, 1, dash="2 3")
    xaxis(d, axs, ygr + 4 * (rh2 + 4) + 12, [1, 12, 24, 36], None, 11)
    d.t(ix, ygr - 6, "Netto lager", 12, 600, INK)
    cx0, cw0 = ix + lw_ + 14, iw - lw_ - 14
    d.t(cx0, ygr - 6, "Kostnad, kr", 12, 600, INK)
    per, tl, tr = chain_bill(K)
    mxc = max(a + b for a, b in per.values())
    for i, r in enumerate(UP):
        cl, cr = per[r]
        yr = ygr + i * (rh2 + 4) + 8
        d.rect(cx0, yr, cw0 * cl / mxc, 8, BLUE)
        d.rect(cx0 + cw0 * cl / mxc + 1, yr, max(cw0 * cr / mxc - 1, 0), 8, RED)
        d.t(cx0, yr + 22, nf(cl + cr), 12, 400, INK)
    d.t(cx0, ygr + 4 * (rh2 + 4) + 12, f"Kjeden {nf(tl + tr)}", 12, 700, INK)
    d.para(xs, fy + fh + 20, "Gruppa ser hele kjeden på storskjermen, i samme retning som på telefonen: varene går mot høyre, ordrene mot venstre. Hver student følger sitt eget steg på telefonen.", ws, 14, 19, fill=INK2)
    d.demodata(2060, 44, "Demodata. Simulerte tall er merket Simulert.", 13, "end")
    d.save()


# ---------- 08 ----------
def week_stats(role, key="netto_lager"):
    """Median og kvartiler per uke over spill som har spilt uka."""
    out = []
    for w in range(1, 37):
        vals = sorted(sp[key][role][w - 1] for sp in KL["spill"] if len(sp[key][role]) >= w)
        n = len(vals)
        q1, q3 = vals[int(0.25 * (n - 1))], vals[int(0.75 * (n - 1))]
        out.append((n, median(vals), q1, q3))
    return out


def week_cost_mean(w):
    """Kjedekost i Uke w, snitt per spill som har spilt uka: (lager, restordre)."""
    sp = [s for s in KL["spill"] if len(s["netto_lager"]["Fabrikk"]) >= w]
    lk = sum(max(s["netto_lager"][r][w - 1], 0) * 0.5 for s in sp for r in ROLES) / len(sp)
    rk = sum(max(-s["netto_lager"][r][w - 1], 0) * 1.0 for s in sp for r in ROLES) / len(sp)
    return lk, rk


def build_08():
    d = Doc("08-laerer-oversikt", 1600, 1000, f"{NAME}, Oversikt for Faglærer",
            "60 Klassespill på én skjerm. Over: klassens median netto lager for valgt Rolle. Under: én rad per spill, én kolonne per uke, "
            "med status, kjedekost og hvem spillet venter på. Til høyre: klassens kostnadsbilde og trakten.")
    fx0, fy0, fw, fh = 24, 16, 1552, 968
    d.rect(fx0, fy0, fw, fh, PAPER, HAIR2, 1.2, 8)
    X = fx0 + 24
    spill = KL["spill"]
    cnt = {k: sum(1 for s in spill if s["status"] == k) for k in ("venter", "pauset", "pågår", "ferdig")}
    d.t(X, fy0 + 38, "Oversikt", 24, 700, INK)
    d.t(X + 104, fy0 + 38, "class-of-1994, IBE160", 15, 400, INK2)
    d.t(X + 1040, fy0 + 38, f"{cnt['ferdig']} ferdig · {cnt['pågår'] + cnt['pauset']} pågår (herav {cnt['pauset']} pauset) · {cnt['venter']} venter", 15, 600, INK, "end")
    d.t(fx0 + fw - 24, fy0 + 38, "Spillfrist ti. 8. des", 15, 400, INK2, "end")

    near = sorted([s for s in spill if s["status"] == "venter"], key=lambda s: -s["ventet_timer"])
    top = near[0]
    ya = fy0 + 58
    d.rect(X, ya, 1040, 34, REDF, None, 1, 4)
    d.t(X + 12, ya + 23, f"Spill {top['spill']} venter på {top['navn']} ({top['venter_paa']}) i {top['ventet_timer']} t. KI overtar om {24 - top['ventet_timer']} t.", 15, 600, INK)
    d.button(X + 800, ya + 5, 112, 24, "Send Melding", size=13)
    d.button(X + 920, ya + 5, 112, 24, "Pause spillet", primary=False, size=13)

    # Filter
    yf = ya + 58
    role = "Fabrikk"
    xx = X
    d.t(xx, yf, "Rolle", 13, 400, INK2)
    xx += 38
    for r in ROLES:
        sel = r == role
        d.t(xx, yf, r, 14, 700 if sel else 400, INK)
        if sel:
            d.line(xx, yf + 5, xx + text_w(r, 14), yf + 5, INK, 2)
        xx += text_w(r, 14) + 16
    xx += 14
    d.t(xx, yf, "Celler", 13, 400, INK2)
    xx += 44
    for i, lab in enumerate(("Netto lager", "Ordre", "Kost per uke")):
        d.t(xx, yf, lab, 14, 700 if i == 0 else 400, INK)
        if i == 0:
            d.line(xx, yf + 5, xx + text_w(lab, 14), yf + 5, INK, 2)
        xx += text_w(lab, 14) + 16
    xx += 14
    d.t(xx, yf, "Status", 13, 400, INK2)
    xx += 44
    ki = sum(1 for s in spill if s["ki_seter"] > 0)
    for i, (lab, c) in enumerate((("Alle", 60), ("Venter", cnt["venter"]), ("Pause", cnt["pauset"]), ("Pågår", cnt["pågår"]),
                                  ("Ferdig", cnt["ferdig"]), ("Med KI-spiller", ki))):
        s_ = f"{lab} {c}"
        d.t(xx, yf, s_, 14, 700 if i == 0 else 400, INK)
        if i == 0:
            d.line(xx, yf + 5, xx + text_w(s_, 14), yf + 5, INK, 2)
        xx += text_w(s_, 14) + 14

    # Kolonner
    cS, cU, cK, cC = X, X + 36, X + 60, X + 128
    mx0 = X + 142
    ax = Axis(mx0, 36 * 15.5, 1, 36)
    tx = ax.x1 + 12
    # Graf over veggen: klassens median netto lager for valgt Rolle
    gy, gh = yf + 22, 68
    st = week_stats(role)
    Y = yscale(gy, gh, -60, 40)
    for v in (-40, 0, 20):
        d.line(ax.x0, Y(v), ax.x1, Y(v), HAIR2 if v == 0 else HAIR, 1)
        d.t(ax.x0 - 5, Y(v) + 4, sg(v), 12, 400, INK3, "end")
    band = [(ax.xc(w), Y(st[w - 1][3])) for w in range(1, 37)] + [(ax.xc(w), Y(st[w - 1][2])) for w in range(36, 0, -1)]
    d.path(pts_path(band) + " Z", GREY, extra='fill-opacity="0.16"')
    med = lambda w: st[w - 1][1]
    net_area(d, ax, gy, gh, med, 1, 36, -60, 40, lw=2, fills=False)
    d.t(X, gy + 12, f"{role}, median", 13, 600, INK)
    d.t(X, gy + 28, "Bånd: midterste", 12, 400, INK2)
    d.t(X, gy + 42, "halvdel av spillene", 12, 400, INK2)
    lowest = min(range(1, 37), key=med)
    # Visning: veggen eller tabellen, alltid synlig over veggen
    vx, vy = tx, gy + 4
    d.t(vx, vy + 17, "Visning", 13, 400, INK2)
    sx0 = vx + 56
    d.rect(sx0, vy, 250, 28, PAPER, HAIR2, 1, 5)
    d.rect(sx0 + 1, vy + 1, 92, 26, INK, None, 1, 4)
    d.t(sx0 + 47, vy + 19, "Vegg", 14, 600, PAPER, "middle")
    d.t(sx0 + 171, vy + 19, "Vis som tabell", 14, 600, INK, "middle")
    d.para(vx, vy + 48, "Tabellen viser alle 60 spill med tall i hver celle, 13 px, og kan sorteres og leses med skjermleser.", fx0 + 1090 - vx, 12, 16, fill=INK2)
    d.t(ax.xc(lowest) + 8, Y(med(lowest)) + 14, f"Median {sg(int(med(lowest)))} i Uke {lowest}", 12, 600, INK)

    # Overskrift for tabellen
    yh = gy + gh + 20
    for xh, h, a in ((cS, "Spill", "start"), (cU + 24, "Uke", "end"), (cK + 24, "KI", "end"), (cC, "Kjede", "end")):
        d.t(xh, yh, h, 12, 600, INK2, a)
    for w in range(1, 37):
        if w % 5 == 0 or w == 1:
            d.t(ax.xc(w), yh, w, 12, 400, INK3, "middle")
    d.t(tx, yh, "Venter på · Forsterkning, Fabrikk", 12, 600, INK2)
    d.line(X, yh + 5, fx0 + 1090, yh + 5, HAIR2, 1)

    rank = {"venter": 0, "pauset": 1, "pågår": 2, "ferdig": 3}
    groups = [("venter", "Venter", sorted([s for s in spill if s["status"] == "venter"], key=lambda s: -s["ventet_timer"])),
              ("pauset", "Pause", [s for s in spill if s["status"] == "pauset"]),
              ("pågår", "Pågår", sorted([s for s in spill if s["status"] == "pågår"], key=lambda s: -s["uke"])),
              ("ferdig", "Ferdig, lavest kjedekost øverst", sorted([s for s in spill if s["status"] == "ferdig"], key=lambda s: s["kjedekost"]))]
    y = yh + 9
    rh = 10.2
    fs = 9.5
    for key, title, rows in groups:
        y += 12.5
        d.t(X, y - 1, f"{title} {len(rows)}", 12, 700, INK)
        y += 2
        for sp in rows:
            isnear = sp["spill"] == top["spill"]
            if isnear:
                d.rect(X - 6, y - 0.5, 1090 - 24 + 6, rh + 1, REDF, None, 1, 2)
            b = y + rh - 2
            d.t(cS, b, sp["spill"], fs, 700 if isnear else 400, INK)
            d.t(cU + 24, b, sp["uke"], fs, 400, INK, "end")
            d.t(cK + 24, b, sp["ki_seter"] or "", fs, 400, INK, "end")
            d.t(cC, b, nf(sp["kjedekost"], 0), fs, 400, INK, "end")
            vals = sp["netto_lager"][role]
            for k, v in enumerate(vals):
                f, _ = net_cell(v)
                d.rect(ax.xl(k + 1) + 0.3, y + 0.4, ax.slot - 0.6, rh - 0.8, f)
            if sp["status"] == "venter":
                d.t(tx, b, f"{sp['navn']}, {sp['venter_paa']}, {sp['ventet_timer']} t", fs + 0.5, 700 if isnear else 400, INK)
                d.t(fx0 + 1090, b, "Melding", fs + 0.5, 600, BLUE, "end", 'text-decoration="underline"')
            elif sp["status"] == "pauset":
                d.t(tx, b, f"Pause, fortsetter {sp['fortsetter']}", fs + 0.5, 400, INK2)
            elif sp["status"] == "ferdig":
                d.t(tx, b, fx1(sp["forsterkning"]["Fabrikk"]), fs + 0.5, 400, INK2)
            y += rh
    # Bunnrader: tallene til grafen
    y += 6
    d.line(X, y, fx0 + 1090, y, HAIR2, 1)
    for lab, fn in ((f"Median, {role}", lambda w: sg(int(round(st[w - 1][1])))),
                    ("Kjedekost/uke, snitt", lambda w: str(int(round(sum(week_cost_mean(w))))))):
        b = y + 13
        d.t(X, b, lab, 11, 600, INK)
        for w in range(1, 37):
            s_ = fn(w)
            f_ = 10
            while text_w(s_, f_) > ax.slot - 1.5 and f_ > 9:
                f_ -= 0.5
            d.t(ax.xc(w), b, s_, f_, 400, INK, "middle")
        y += 16
    d.t(tx, y - 4, "Tallene under grafen. Vis som tabell for alle celler.", 11, 400, INK2)

    # Høyre panel
    rx = fx0 + 1120
    rw = fx0 + fw - 24 - rx
    yy = ya + 64
    d.t(rx, yy, "Venter ellers", 16, 600, INK)
    yy += 24
    for s_ in near[1:]:
        d.t(rx, yy, f"Spill {s_['spill']}", 14, 600, INK)
        d.t(rx + 70, yy, f"{s_['navn']}, {s_['venter_paa']}, {s_['ventet_timer']} t", 14, 400, INK)
        d.t(rx + rw, yy, "Send Melding", 13, 600, BLUE, "end", 'text-decoration="underline"')
        yy += 22
    for s_ in [s for s in spill if s["status"] == "pauset"]:
        d.t(rx, yy, f"Spill {s_['spill']}", 14, 600, INK)
        d.t(rx + 70, yy, f"Pause i Uke {s_['uke']}, fortsetter {s_['fortsetter']}", 14, 400, INK2)
        yy += 22
    kisum = sum(s["ki_seter"] for s in spill)
    d.t(rx, yy + 4, f"{kisum} KI-spillere i {ki} spill, alle merket.", 13, 400, INK2)

    # Klassens kostnad
    yy += 40
    d.line(rx, yy - 22, rx + rw, yy - 22, HAIR, 1)
    d.t(rx, yy, "Klassens kostnad", 16, 600, INK)
    F = KL["ferdige"]["kjedekost"]
    FJ = KL["fjoraaret"]
    fer = [s for s in spill if s["status"] == "ferdig"]
    assert len(fer) == KL["ferdige"]["antall"]
    d.t(rx, yy + 20, f"Kjedekost i {len(fer)} ferdige spill. Hvert merke er ett spill.", 13, 400, INK2)
    sx = Axis(rx, rw, 0, 39)
    kx = lambda v: rx + 8 + (v / 4000) * (rw - 16)
    yd = yy + 66
    d.rect(kx(F["q1"]), yd - 14, kx(F["q3"]) - kx(F["q1"]), 28, TINT, HAIR2, 1)
    for s_ in fer:
        d.line(kx(s_["kjedekost"]), yd - 9, kx(s_["kjedekost"]), yd + 9, ORD, 1.4)
    d.line(kx(F["median"]), yd - 16, kx(F["median"]), yd + 16, INK, 2.4)
    d.line(kx(FJ["median_kjedekost"]), yd - 22, kx(FJ["median_kjedekost"]), yd + 16, INK, 1.2, "3 3")
    d.t(kx(F["median"]) - 4, yd - 22, f"Median {nf(F['median'], 0)}", 13, 600, INK, "end")
    d.t(kx(FJ["median_kjedekost"]) + 4, yd - 26, f"Fjoråret {nf(FJ['median_kjedekost'], 0)}", 13, 400, INK2)
    for v in (0, 1000, 2000, 3000, 4000):
        d.t(kx(v), yd + 34, nf(v, 0), 12, 400, INK3, "middle")
    d.t(rx, yd + 54, "Kroner. Boksen er midterste halvdel.", 12, 400, INK2)
    # per Rolle og kostnadsart
    yr = yd + 80
    d.t(rx, yr, "Snitt per ferdig spill, per Rolle", 14, 600, INK)
    yr += 8
    per = {}
    for r in ROLES:
        lk = sum(max(v, 0) * 0.5 for s in fer for v in s["netto_lager"][r]) / len(fer)
        rk = sum(max(-v, 0) * 1.0 for s in fer for v in s["netto_lager"][r]) / len(fer)
        per[r] = (lk, rk)
    for s_ in fer:
        for r in ROLES:
            c = sum(v * 0.5 if v > 0 else -v for v in s_["netto_lager"][r])
            assert abs(c - s_["kost_per_rolle"][r]) < 0.51
    mxr = max(a + b for a, b in per.values())
    bx0, bwmax = rx + 92, rw - 92 - 64
    for r in ROLES:
        lk, rk = per[r]
        yr += 24
        d.t(rx, yr, r, 13, 400, INK)
        wl, wr_ = bwmax * lk / mxr, bwmax * rk / mxr
        d.rect(bx0, yr - 11, wl, 13, BLUE)
        d.rect(bx0 + wl + 2, yr - 11, wr_, 13, RED)
        d.t(rx + rw, yr, nf(lk + rk, 0), 13, 600, INK, "end")
    yr += 22
    tl = sum(a for a, b in per.values())
    tr = sum(b for a, b in per.values())
    xx = chip(d, rx, yr, BLUE, f"lager {nf(tl, 0)}", 13, 400, INK2)
    chip(d, xx, yr, RED, f"restordre {nf(tr, 0)} kr", 13, 400, INK2)

    # Kjedekost per uke for klassen: graf, tallene står i bunnraden under veggen
    yw = yr + 46
    d.line(rx, yw - 22, rx + rw, yw - 22, HAIR, 1)
    d.t(rx, yw, "Kjedekost per uke, snitt per spill", 14, 600, INK)
    axw = Axis(rx + 34, rw - 34, 1, 36)
    wc = [week_cost_mean(w) for w in range(1, 37)]
    cmw = max(a + b for a, b in wc)
    top_ = 10 * (int(cmw / 10) + 1)
    cost_bars(d, axw, yw + 12, 70, lambda w: wc[w - 1], 1, 36, top_, gap=1.6)
    d.line(axw.x0, yw + 12, axw.x1, yw + 12, HAIR, 1)
    d.t(axw.x0 - 4, yw + 16, f"{top_}", 12, 400, INK3, "end")
    d.t(axw.x0 - 4, yw + 86, "0", 12, 400, INK3, "end")
    xaxis(d, axw, yw + 98, [1, 12, 24, 36], size=12)
    peak = max(range(1, 37), key=lambda w: sum(wc[w - 1]))
    d.t(axw.xc(2), yw + 32, f"Høyest i Uke {peak}: {nf(sum(wc[peak - 1]), 0)} kr", 12, 600, INK)

    # Trakt
    yt = yw + 140
    d.line(rx, yt - 24, rx + rw, yt - 24, HAIR, 1)
    d.t(rx, yt, "Trakt", 16, 600, INK)
    tr_ = KL["traktA"]
    steps = [("Registrert", tr_["registrert"]), ("Klassespill ferdig", tr_["klassespill_ferdig"]), ("Debrief ferdig", tr_["debrief_ferdig"]),
             ("Quiz bestått", tr_["quiz_bestått"]), ("Replay ferdig", tr_["replay_ferdig"]), ("Test levert", tr_["test_levert"]),
             ("KI-vurdering klar", tr_["ki_vurdering_klar"])]
    yt += 8
    for lab, v in steps:
        yt += 18
        d.t(rx, yt, lab, 13, 400, INK)
        d.t(rx + 156, yt, v, 13, 600, INK, "end")
        if v:
            d.rect(rx + 166, yt - 10, (rw - 166) * v / steps[0][1], 11, ORD)
        else:
            d.line(rx + 166, yt - 10, rx + 166, yt + 1, ORD, 1.5)
    yb_ = fy0 + fh - 62
    d.button(rx, yb_, rw, 40, "Vis i plenum", primary=False, size=14)
    d.demodata(fx0 + fw - 24, fy0 + fh - 8, a="end")
    d.save()


if __name__ == "__main__":
    build_07()
    build_08()
