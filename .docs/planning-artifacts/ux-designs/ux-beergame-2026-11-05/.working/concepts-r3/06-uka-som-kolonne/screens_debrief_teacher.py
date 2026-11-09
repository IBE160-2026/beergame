"""07 debrief og 08 lærerens oversikt."""
from e06lib import *


def sec_title(d, x, y, n, title, width):
    d.line(x, y - 26, x + width, y - 26, INK, 1.2)
    d.t(x, y, str(n), 22, 700, INK)
    return d.para(x + 24, y, title, width - 24, 22, 27, 600, INK)


def demand_band(d, ax, y0, h, scale, wfrom=1, wto=36):
    u = h / scale
    base = y0 + h
    dd = f"M{ax.xl(wfrom):.1f} {base:.1f}"
    for w in range(wfrom, wto + 1):
        v = DEM[w - 1]
        dd += f" L{ax.xl(w):.1f} {base - v * u:.1f} L{ax.xr(w):.1f} {base - v * u:.1f}"
    dd += f" L{ax.xr(wto):.1f} {base:.1f} Z"
    d.path(dd, BLUEF)
    d.line(ax.xl(wfrom), base, ax.xr(wto), base, HAIR2, 1)


def chain_rows(seats, wfrom, wto, label_sel="Grossist", kind="net"):
    rows = []
    for r in ROLES:
        S = seats[r]
        lab = f"{r}" + (", du" if r == label_sel else "")
        rows.append((lab, kind, (S.net if kind == "net" else S.order)))
    return rows


# ---------- 07 ----------
def build_07():
    d = Doc("07-debrief", 2100, 1200, "Uka som kolonne, Gruppedebrief i fem steg",
            "Forklaring, avsløring av etterspørselen, hele kjeden kolonne for kolonne, ditt øyeblikk i Uke 11 med kjedens kostnad, quiz og delt skjerm.")
    d.t(40, 44, "Debrief, Spill 17: fra «hadde jeg rett?» til «hvorfor skjedde det?»", 28, 600, INK)
    y = 112

    # Steg 1
    x, w = 40, 320
    sec_title(d, x, y, 1, "Skriv Forklaringen først", w)
    d.t(x, y + 32, "Din rad i tabellen: lager, hele spillet", 14, 600, INK)
    ax = Axis(x + 30, w - 30, 1, 36)
    grid(d, ax, y + 42, 96, -40, 30, (-40, 0, 20), 13)
    net_area(d, ax, y + 42, 96, G.net, 1, 36)
    week_row(d, ax, y + 156, [1, 12, 24, 36])
    d.t(x, y + 192, "Hvorfor svingte lageret ditt?", 15, 600, INK)
    d.rect(x, y + 202, w, 112, PAPER, HAIR2, 1, 6)
    d.para(x + 12, y + 226, "Restordren vokste, så jeg bestilte mye for å ta den igjen. Det som var på vei, regnet jeg lite med.", w - 24, 15, 20)
    d.button(x, y + 324, w, 44, "Send Forklaring", size=15)
    d.circle(x + 7, y + 391, 5, PAPER, INK, 1.5)
    d.para(x + 20, y + 396, "Avsløringen er låst til alle fire har sendt. Ida og Mikkel har sendt, Jonas skriver.", w - 20, 14, 19, fill=INK2)

    # Steg 2: klimaks
    x2, w2 = 400, 600
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
    for k in range(1, 37):
        d.rect(ax2.xc(k) - 2.5, y0 + h - G.order(k) * u, 5, G.order(k) * u, INK)
    d.path("M" + " L".join(f"{ax2.xc(k):.1f} {y0 + h - G.inn(k) * u:.1f}" for k in range(1, 37)), stroke=GREY, sw=1.6)
    d.t(ax2.xc(11) + 8, y0 + h - 24 * u + 12, "Din ordre, 24 i Uke 11", 15, 600, INK)
    d.t(ax2.xc(29.5), y0 + h - 8 * u - 10, "Kundene: 8", 16, 700, BLUE, "middle", 'stroke="#FFFFFF" stroke-width="4" paint-order="stroke"')
    d.t(ax2.xc(2.5), y0 + h - 4 * u - 8, "4", 18, 700, BLUE, "middle")
    d.t(ax2.xc(19) + 6, y0 + h - 13 * u, "Ordre inn: det eneste du så", 15, 600, INK2)
    week_row(d, ax2, y0 + h + 18, [1, 5, 10, 15, 20, 25, 30, 36])
    d.para(x2, y0 + h + 44, "Øvelsen heter Beer Game. Nesten alle grupper svinger slik, også i år. Det du så, var Idas ordrer, ikke kundene. Struktur gir atferd, derfor spør vi hvorfor og ikke hvem.", w2, 15, 20, fill=INK)
    d.t(x2, y0 + h + 96, "P4, P6", 13, 400, INK3)

    # Steg 3: hele kjeden, kolonne for kolonne
    x3, w3 = 1040, 1020
    sec_title(d, x3, y, 3, "Hele kjeden, kolonne for kolonne. Svingningene vokser oppstrøms.", w3)
    sel = 18
    ax3 = Axis(x3 + 130, w3 - 130 - 70, 1, 36)
    ch = chain4(d, x3, y + 14, w3, SEATS, sel, kunde=DEM[sel - 1], u=0.7, sel_role="Grossist")
    yc = ch["bottom"] + 20
    zoom(d, x3, x3 + w3, ch["bottom"] + 4, ax3, sel, yc)
    # ordre per Rolle som stolper, samme kolonner
    rh = 33
    fs = 32
    yy = yc + 6
    onset = {}
    for r in ROLES[::-1]:
        S = SEATS[r]
        order_bars(d, ax3, yy, rh, S.order, 1, 36, fs, fill=INK if r == "Grossist" else ORD)
        d.t(x3, yy + rh - 4, r, 14, 600, INK)
        d.big(ax3.x1 + 70, yy + rh - 4, fx1(K["forsterkning"][r]), 20, 700, INK, "end")
        first = next(k for k in range(1, 37) if S.order(k) >= 10)
        onset[r] = (ax3.xc(first), yy + rh - S.order(first) * rh / fs, first)
        yy += rh + 6
    pts = [onset[r] for r in ROLES[::-1]]
    d.path("M" + " L".join(f"{a:.1f} {b - 3:.1f}" for a, b, _ in pts), stroke=RED, sw=1.2)
    for a, b, k in pts:
        d.circle(a, b - 3, 3.5, RED, PAPER, 1.5)
        d.t(a - 7, b - 5, f"Uke {k}", 12, 600, RED, "end")
    week_row(d, ax3, yy + 10, list(range(1, 37)), None, sel, size=12)
    ymat = yy + 16
    rows = [("Kundene", "flow", lambda k: DEM[k - 1])] + [(r, "flow", SEATS[r].order) for r in ROLES]
    ybot = matrix(d, ax3, ymat, rows, 1, 36, rh=18, size=12, lx=x3, lsize=13)
    col_box(d, ax3, sel, yc, ybot)
    d.t(x3, ybot + 22, "Ordre per Rolle, samme skala i alle rader. Rødt punkt: første Uke med ordre på 10 eller mer. Tallet til høyre er Forsterkning. P5.", 13, 400, INK2)

    # Rad 2
    yb = 680
    # Steg 4
    x4, w4 = 40, 1180
    sec_title(d, x4, yb, 4, "Ditt øyeblikk: Uke 11. Du bestilte 24 med 16 på vei.", w4)
    aw = 620
    ch4 = chain4(d, x4, yb + 16, aw, SEATS, 11, u=1.0, show_cost=True, sel_role="Grossist")
    ax4 = Axis(x4 + 130, aw - 130, 1, 15)
    yc4 = ch4["bottom"] + 20
    zoom(d, x4, x4 + aw, ch4["bottom"] + 2, ax4, 11, yc4)
    week_row(d, ax4, yc4 + 16, list(range(1, 16)), None, 11, size=12)
    rows = [(r + (", du" if r == "Grossist" else ""), "net", SEATS[r].net) for r in ROLES]
    rows.append(("Kjeden, kr", "kr", lambda k: chain_week_cost(k)))
    rows.append(("Kjeden, sum", "sum", lambda k: sum(chain_week_cost(j) for j in range(1, k + 1))))
    yend = matrix(d, ax4, yc4 + 22, rows, 1, 15, rh=20, size=12, lx=x4, lsize=13)
    col_box(d, ax4, 11, yc4, yend)
    # kjedens kostnad, Rolle × kostnadsart
    yk = yend + 30
    d.t(x4, yk, "Kjedens kostnad, hele spillet", 15, 600, INK)
    d.t(x4 + aw, yk, f"{nf(K['kjedekost'])} kr", 15, 700, INK, "end")
    cx = [x4 + 210, x4 + 300, x4 + 380]
    d.t(cx[0], yk + 22, "Restordre", 13, 600, INK2, "end")
    d.t(cx[1], yk + 22, "Lager", 13, 600, INK2, "end")
    d.t(cx[2], yk + 22, "Sum", 13, 600, INK2, "end")
    yy = yk + 42
    mx = max(K["kost_per_rolle"].values())
    for r in ROLES:
        S = SEATS[r]
        d.t(x4, yy, r, 13, 600 if r == "Grossist" else 400, INK)
        d.t(cx[0], yy, nf(S.sum_r()), 13, 400, INK, "end")
        d.t(cx[1], yy, nf(S.sum_l()), 13, 400, INK, "end")
        d.t(cx[2], yy, nf(K["kost_per_rolle"][r]), 13, 600, INK, "end")
        bwmax = aw - (cx[2] - x4) - 20
        wr = bwmax * S.sum_r() / mx
        wl = bwmax * S.sum_l() / mx
        d.rect(cx[2] + 20, yy - 10, wr - 1, 11, RED)
        d.rect(cx[2] + 20 + wr + 1, yy - 10, wl - 1, 11, BLUE)
        yy += 21
    # tekst
    tx, tw = x4 + aw + 40, 250
    d.t(tx, yb + 32, "Dette regnet du", 15, 600, INK)
    ny = d.para(tx, yb + 54, f"Lager {G.lager[10]}, restordre {G.rest[10]}, på vei {G.paavei(11)}. Posisjonen var {G.posisjon(11)}, og med 24 ble den {G.posisjon(11) + 24}.", tw, 14, 19)
    d.t(tx, ny + 12, "Dette kostet det senere", 15, 600, INK)
    late = G.kostsum(36) - G.kostsum(24)
    ny = d.para(tx, ny + 34, f"{G.levering(15)} av de 24 kom i Uke 15. På vei toppet på {max(G.pv)} i Uke {G.pv.index(max(G.pv)) + 1}. I Uke {G.lager.index(max(G.lager)) + 1} sto du med lager {max(G.lager)}. Lager i Uke 25 til 36 kostet {nf(late)} kr.", tw, 14, 19)
    d.t(tx, ny + 12, "Dette så de andre", 15, 600, INK)
    ny = d.para(tx, ny + 34, "Kolonnen over: Ida hadde restordre, Mikkel og Jonas hadde lager. Ingen av dere kunne se de andres tall.", tw, 14, 19)
    d.para(tx, ny + 12, "KI-generert, kan ta feil: «Du reagerte på restordren du så, ikke på posisjonen. Mikkel fikk 24 fra deg uten å vite hvorfor.»", tw, 13, 18, fill=INK2)
    # simulert
    rx, rw = tx + tw + 30, w4 - aw - 40 - tw - 30
    d.t(rx, yb + 32, "Samme kjede, Sara teller alt på vei", 15, 600, INK)
    d.para(rx, yb + 52, "Simulert. Viser sammenhengen, ikke en fasit.", rw, 13, 18, fill=INK2)
    B = FX["bare_sara_teller_paa_vei"]
    rows = [("", "Spill 17", "Simulert"),
            ("Din ordre, Uke 11", "24", str(BARE.order(11))),
            ("Grossist, kr", nf(K["kost_per_rolle"]["Grossist"]), nf(B["kost_per_rolle"]["Grossist"])),
            ("Kjeden, kr", nf(K["kjedekost"]), nf(B["kjedekost"])),
            ("Forsterkning, Grossist", fx1(K["forsterkning"]["Grossist"]), fx1(B["forsterkning"]["Grossist"]))]
    yy = yb + 92
    for i, row in enumerate(rows):
        bold = 600 if i == 0 else 400
        d.t(rx, yy, row[0], 13, bold, INK)
        d.t(rx + rw - 72, yy, row[1], 13, bold, INK, "end")
        d.t(rx + rw, yy, row[2], 13, bold, INK, "end")
        d.line(rx, yy + 7, rx + rw, yy + 7, HAIR, 1)
        yy += 24
    axs = Axis(rx + 26, rw - 26, 1, 36)
    ys = yy + 14
    Ys = grid(d, axs, ys, 110, -40, 30, (-40, 0, 20), 12)
    net_area(d, axs, ys, 110, G.net, 1, 36, lw=1.6)
    d.path("M" + " L".join(f"{axs.xc(k):.1f} {Ys(BARE.net(k)):.1f}" for k in range(1, 37)), stroke=INK, sw=1.4)
    d.t(axs.xc(36), Ys(BARE.net(33)) - 8, "Simulert", 13, 600, INK, "end")
    d.t(axs.xc(12), Ys(-34), "Spill 17", 13, 600, RED, "end")
    week_row(d, axs, ys + 128, [1, 12, 24, 36], size=12)
    d.t(rx, ys + 152, "P3, P7, P8", 13, 400, INK3)

    # Steg 5
    x5, w5 = 1260, 360
    sec_title(d, x5, yb, 5, "Debrief-quiz", w5)
    ny = d.para(x5, yb + 34, f"Uke 11: lager {G.lager[10]}, restordre {G.rest[10]}, {G.paavei(11)} på vei. Hva er posisjonen før du bestiller?", w5, 16, 22, 600)
    opts = [(sg(-13), "wrong"), (str(G.posisjon(11)), "right"), ("16", None), ("29", None)]
    yy = ny + 6
    for lab, st in opts:
        col = RED if st == "wrong" else (INK if st == "right" else HAIR2)
        d.rect(x5, yy, w5, 42, PAPER, col, 1.4 if st else 1, 6)
        d.t(x5 + 14, yy + 27, lab, 16, 600, INK)
        if st == "wrong":
            d.t(x5 + w5 - 14, yy + 27, "Ditt svar, ikke riktig", 14, 600, RED, "end")
        if st == "right":
            d.t(x5 + w5 - 14, yy + 27, "Riktig", 14, 600, INK, "end")
        yy += 50
    ny = d.para(x5, yy + 10, "−13 er lager minus restordre. Da mangler det du allerede har bestilt: 0 − 13 + 16 = 3.", w5, 15, 20)
    d.para(x5, ny + 8, "Regnestykket står i kolonnen for Uke 11: rad Lager og rad På vei, rett under hverandre.", w5, 14, 19, fill=INK2)
    d.t(x5, ny + 66, "P3", 13, 400, INK3)

    # Delt skjerm
    xs, ws = 1660, 400
    sec_title(d, xs, yb, " ", "Delt skjerm", ws)
    fy = yb + 18
    d.rect(xs, fy, ws, 380, PAPER, HAIR2, 1.4, 8)
    axs = Axis(xs + 92, ws - 106, 1, 36)
    # kjeden i én kolonne, uten tall: bare boksene på sann skala
    selw = 18
    ytop = fy + 20
    nb = (ws - 40) / 4
    ybase = ytop + 34
    for i, r in enumerate(ROLES):
        c = SEATS[r].col(selw)
        bx = xs + 20 + i * nb
        d.t(bx, ytop + 2, r, 12, 600, INK)
        if c["rest"]:
            d.rect(bx, ybase, 34, c["rest"] * 0.55, REDF, RED, 1)
        if c["lager"]:
            d.rect(bx, ybase - c["lager"] * 0.55, 34, c["lager"] * 0.55, BLUEF, BLUE, 1)
        d.line(bx, ybase, bx + 34, ybase, INK, 1.6)
        d.t(bx + 40, ybase + 14, sg(c["net"]), 12, 600, INK)
    d.line(xs + 12, ybase, xs + ws - 12, ybase, ORD, 1)
    ym = ybase + 54
    zoom(d, xs + 12, xs + ws - 12, ybase + 34, axs, selw, ym - 4)
    for i, r in enumerate(ROLES):
        yr = ym + i * 22
        d.t(xs + 12, yr + 15, r, 12, 600, INK)
        for k in range(1, 37):
            f, _ = net_fill(SEATS[r].net(k))
            if f:
                d.rect(axs.xl(k) + 0.5, yr + 1, axs.slot - 1, 20, f)
    yr = ym + 4 * 22 + 6
    d.t(xs + 12, yr + 13, "Kjeden, kr", 12, 600, INK)
    mxw = max(chain_week_cost(k) for k in range(1, 37))
    for k in range(1, 37):
        cr = sum(SEATS[r].kost_r(k) for r in ROLES)
        cl = sum(SEATS[r].kost_l(k) for r in ROLES)
        hb = 34 / mxw
        d.rect(axs.xl(k) + 0.5, yr + 34 - cr * hb, axs.slot - 1, cr * hb, RED)
        d.rect(axs.xl(k) + 0.5, yr + 34 - cr * hb - cl * hb, axs.slot - 1, cl * hb, BLUE)
    col_box(d, axs, selw, ym - 4, yr + 36, 1.2)
    week_row(d, axs, yr + 52, [1, 12, 18, 24, 36], None, selw, size=12)
    d.para(xs + 14, yr + 82, "Gruppa trykker på en kolonne, og kjeden over viser den uka. Tallene står i cellene når skjermen er stor nok.", ws - 28, 13, 18, fill=INK2)
    d.demodata(2060, 1188, "Demodata. Simulerte tall er merket Simulert.", 13, "end")
    d.save()


# ---------- 08 ----------
def status_txt(sp):
    return {"ferdig": "Ferdig", "pågår": "Pågår", "pauset": "Pause", "venter": "Venter"}[sp["status"]]


def build_08():
    d = Doc("08-laerer-oversikt", 1600, 1000, "Uka som kolonne, Oversikt for Faglærer",
            "60 Klassespill som rader og uker som kolonner, med klassens kjede for én valgt uke øverst, hvem hvert spill venter på, trakten og klassens kostnadsbilde.")
    spill = KL["spill"]
    X = 32
    d.t(X, 40, "Oversikt", 26, 700, INK)
    d.t(X + 116, 40, "class-of-1994, IBE160", 15, 400, INK2)
    counts = {k: sum(1 for s in spill if s["status"] == k) for k in ("venter", "pauset", "pågår", "ferdig")}
    ki = sum(1 for s in spill if s["ki_seter"] > 0)
    d.t(1040, 40, f"{counts['ferdig']} ferdig · {counts['pågår'] + counts['pauset']} pågår ({counts['pauset']} pauset) · {counts['venter']} venter", 15, 600, INK, "end")

    # Veggen: aksen
    ax = Axis(X + 40, 36 * 13.2, 1, 36)
    selw = 14
    role = "Fabrikk"
    # filter
    yf = 76
    xx = X
    d.t(xx, yf + 4, "Rolle", 13, 400, INK2)
    xx += 38
    for r in ROLES:
        sel = r == role
        d.t(xx, yf + 4, r, 13, 600 if sel else 400, INK)
        if sel:
            d.line(xx, yf + 9, xx + text_w(r, 13), yf + 9, INK, 1.6)
        xx += text_w(r, 13) + 14
    xx += 16
    d.t(xx, yf + 4, "Celle", 13, 400, INK2)
    xx += 36
    for lab, sel in (("Netto lager", True), ("Ordre", False), ("Kostnad", False)):
        d.t(xx, yf + 4, lab, 13, 600 if sel else 400, INK)
        if sel:
            d.line(xx, yf + 9, xx + text_w(lab, 13), yf + 9, INK, 1.6)
        xx += text_w(lab, 13) + 14
    xx += 16
    d.t(xx, yf + 4, "Status", 13, 400, INK2)
    xx += 44
    for lab, c in (("Alle", 60), ("Venter", counts["venter"]), ("Pause", counts["pauset"]), ("Pågår", counts["pågår"]), ("Ferdig", counts["ferdig"]), ("KI", ki)):
        s_ = f"{lab} {c}"
        d.t(xx, yf + 4, s_, 13, 600 if lab == "Alle" else 400, INK)
        if lab == "Alle":
            d.line(xx, yf + 9, xx + text_w(s_, 13), yf + 9, INK, 1.6)
        xx += text_w(s_, 13) + 12
    d.line(X, yf + 22, 1040, yf + 22, HAIR, 1)
    # klassens kjede for valgt uke: median netto lager per Rolle i spillene som har nådd uka
    yk = 112
    n = AGG["n"][selw - 1]
    d.t(X, yk + 14, f"Klassens kjede i Uke {selw}", 15, 600, INK)
    d.t(X, yk + 32, f"Median over {n} spill.", 13, 400, INK2)
    d.t(X, yk + 48, "Trykk på en kolonne.", 13, 400, INK2)
    cw_ = 140
    ub = 0.9
    ybase = yk + 40
    cx0 = X + 200
    d.line(cx0 - 10, ybase, cx0 + 4 * cw_ - 30, ybase, ORD, 1.6)
    d.arrow_l(cx0 - 18, ybase, ORD, 7)
    for i, r in enumerate(ROLES):
        v = AGG["median_net"][r][selw - 1]
        bx = cx0 + i * cw_
        if v > 0:
            d.rect(bx, ybase - v * ub, 40, v * ub, BLUEF, BLUE, 1)
        elif v < 0:
            d.rect(bx, ybase, 40, -v * ub, REDF, RED, 1)
        d.line(bx, ybase, bx + 40, ybase, INK, 2 if r == role else 1.4)
        d.t(bx, yk + 14, r, 13, 700 if r == role else 600, INK)
        d.t(bx + 46, ybase + 15, sg(v) if v == int(v) else nf(v, 1), 13, 600, INK)
    d.t(cx0 + 4 * cw_ - 10, yk + 14, "Kjeden, median i uka", 13, 600, INK)
    d.big(cx0 + 4 * cw_ - 10, yk + 40, f"{nf(AGG['median_cost'][selw - 1], 0)} kr", 22, 700)
    d.t(cx0 + 4 * cw_ - 10, yk + 58, "Minus er restordre", 13, 400, INK2)

    # kolonnehoder
    yh = yk + 96
    d.t(X, yh, "Spill", 12, 600, INK2)
    week_row(d, ax, yh, [1, 5, 10, 14, 20, 25, 30, 36], None, selw, size=11)
    c0 = ax.x1 + 10
    heads = [(c0 + 22, "Uke", "end"), (c0 + 80, "Kjede, kr", "end"), (c0 + 100, "KI", "end"), (c0 + 114, "Venter på / Forsterkning", "start")]
    for xh, h, a in heads:
        d.t(xh, yh, h, 12, 600, INK2, a)
    d.line(X, yh + 5, 1040, yh + 5, HAIR2, 1)
    zoom(d, cx0 - 18, cx0 + 3 * cw_ + 40, ybase + 30, ax, selw, yh + 8)

    rank = {"venter": 0, "pauset": 1, "pågår": 2, "ferdig": 3}
    ordered = sorted(spill, key=lambda s: (rank[s["status"]], -(s.get("ventet_timer") or 0), -s["uke"] if s["status"] != "ferdig" else s["kjedekost"]))
    near = max((s for s in spill if s["status"] == "venter"), key=lambda s: s["ventet_timer"])
    rowh = 9.6
    y = yh + 10
    prev = None
    ytop_wall = y
    group_names = {"venter": "Venter", "pauset": "Pause", "pågår": "Pågår", "ferdig": "Ferdig, billigst kjede øverst"}
    for sp in ordered:
        if sp["status"] != prev:
            y += 3
            d.t(X, y + 10, f"{group_names[sp['status']]} {counts[sp['status']]}", 11, 700, INK)
            y += 13
            prev = sp["status"]
        isnear = sp is near
        if isnear:
            d.rect(X - 4, y - 0.5, 1040 - X + 8, rowh + 1, REDF, None, 1, 2)
        d.t(X + 30, y + rowh - 1.5, sp["spill"], 10, 700 if isnear else 400, INK, "end")
        vals = sp["netto_lager"][role]
        for k, v in enumerate(vals, start=1):
            f, _ = net_fill(v, (1, 13, 25, 49))
            d.rect(ax.xl(k) + 0.4, y + 0.4, ax.slot - 0.8, rowh - 0.8, f or "#EEF1F4")
        if sp["status"] != "ferdig":
            d.line(ax.xr(sp["uke"]) + 0.5, y - 0.5, ax.xr(sp["uke"]) + 0.5, y + rowh + 0.5, INK, 1.4)
        d.t(c0 + 22, y + rowh - 1.5, sp["uke"], 10, 400, INK, "end")
        d.t(c0 + 80, y + rowh - 1.5, nf(sp["kjedekost"], 0), 10, 400, INK, "end")
        if sp["ki_seter"]:
            d.t(c0 + 100, y + rowh - 1.5, sp["ki_seter"], 10, 400, INK, "end")
        if sp["status"] == "venter":
            d.t(c0 + 114, y + rowh - 1.5, f"{sp['navn']}, {sp['venter_paa']}, {sp['ventet_timer']} t" + (". KI om 1 t" if isnear else ""), 10, 700 if isnear else 400, INK)
        elif sp["status"] == "pauset":
            d.t(c0 + 114, y + rowh - 1.5, f"Pause, fortsetter {sp['fortsetter']}", 10, 400, INK2)
        elif sp["status"] == "ferdig":
            d.t(c0 + 114, y + rowh - 1.5, f"Fabrikk {fx1(sp['forsterkning']['Fabrikk'])}", 10, 400, INK2)
        y += rowh
    ybot_wall = y
    col_box(d, ax, selw, ytop_wall - 2, ybot_wall + 2, 1.2)

    # aggregerte rader, samme kolonner
    y += 12
    d.line(X, y - 4, 1040, y - 4, HAIR2, 1)
    d.t(X, y + 12, "Median", 11, 700, INK)
    for k in range(1, 37):
        v = AGG["median_net"][role][k - 1]
        f, tc = net_fill(v, (1, 13, 25, 49))
        d.rect(ax.xl(k) + 0.4, y, ax.slot - 0.8, 16, f or "#EEF1F4")
    d.t(c0, y + 12, f"Median netto lager, {role}", 11, 400, INK2)
    y += 22
    # klassens kostnad per uke, delt i restordre og lager
    cr_ = []
    cl_ = []
    for k in range(1, 37):
        ins = [sp for sp in spill if sp["uke"] >= k]
        cr_.append(sum(-v * RESTKOST for sp in ins for r in ROLES for v in [sp["netto_lager"][r][k - 1]] if v < 0))
        cl_.append(sum(v * LAGERKOST for sp in ins for r in ROLES for v in [sp["netto_lager"][r][k - 1]] if v > 0))
        assert abs(cr_[-1] + cl_[-1] - AGG["sum_cost"][k - 1]) < 1e-6
    mxc = max(a + b for a, b in zip(cr_, cl_))
    hb = 40
    d.t(X, y + 14, "Klassen,", 11, 700, INK)
    d.t(X, y + 27, "kr per uke", 11, 700, INK)
    for k in range(1, 37):
        a, b = cr_[k - 1] / mxc * hb, cl_[k - 1] / mxc * hb
        d.rect(ax.xl(k) + 0.8, y + hb - a, ax.slot - 1.6, a, RED)
        d.rect(ax.xl(k) + 0.8, y + hb - a - b - 0.6, ax.slot - 1.6, b, BLUE)
    d.line(ax.x0, y + hb, ax.x1, y + hb, HAIR2, 1)
    d.t(c0, y + 12, f"Høyest Uke {max(range(36), key=lambda i: cr_[i] + cl_[i]) + 1}: {nf(mxc, 0)} kr", 11, 400, INK2)
    d.t(c0, y + 26, "Rødt restordre, blått lager", 11, 400, INK2)
    d.t(c0, y + 40, f"Akkumulert så langt: {nf(AGG['cum'][-1], 0)} kr", 11, 600, INK)
    week_row(d, ax, y + hb + 14, [1, 5, 10, 14, 20, 25, 30, 36], None, selw, size=11)

    # Høyre panel
    rx, rw = 1090, 478
    d.line(rx - 24, 24, rx - 24, 976, HAIR, 1)
    d.t(rx, 40, "Spillfrist ti. 8. des", 14, 400, INK2)
    d.t(rx, 76, "Nær overtakelse", 16, 600, INK)
    d.rect(rx, 88, rw, 108, REDF, None, 1, 6)
    d.t(rx + 16, 116, f"Spill {near['spill']} venter på {near['navn']} ({near['venter_paa']})", 16, 700, INK)
    d.t(rx + 16, 138, f"i {near['ventet_timer']} t. KI-spiller overtar om {24 - near['ventet_timer']} t.", 15, 400, INK)
    d.button(rx + 16, 150, 170, 34, f"Send Melding til {near['navn']}", size=13)
    d.button(rx + 196, 150, 120, 34, "Pause spillet", primary=False, size=13)
    y = 228
    d.t(rx, y, "Venter ellers", 15, 600, INK)
    y += 24
    others = sorted([s for s in spill if s["status"] == "venter" and s is not near], key=lambda s: -s["ventet_timer"])
    for s in others:
        d.t(rx, y, f"Spill {s['spill']}", 13, 600, INK)
        d.t(rx + 64, y, f"{s['navn']}, {s['venter_paa']}, {s['ventet_timer']} t", 13, 400, INK)
        d.link(rx + rw, y, "Send Melding", 13, "end")
        y += 21
    for s in [s for s in spill if s["status"] == "pauset"]:
        d.t(rx, y, f"Spill {s['spill']}", 13, 600, INK)
        d.t(rx + 64, y, f"Pause i Uke {s['uke']}, fortsetter {s['fortsetter']}", 13, 400, INK2)
        y += 21
    # Trakt
    y += 18
    d.t(rx, y, "Trakten", 15, 600, INK)
    tr = KL["traktA"]
    steps = [("Registrert", tr["registrert"]), ("Klassespill ferdig", tr["klassespill_ferdig"]), ("Debrief ferdig", tr["debrief_ferdig"]),
             ("Quiz bestått", tr["quiz_bestått"]), ("Replay ferdig", tr["replay_ferdig"]), ("Test levert", tr["test_levert"]), ("KI-vurdering klar", tr["ki_vurdering_klar"])]
    y += 20
    for lab, v in steps:
        d.t(rx, y, lab, 13, 400, INK)
        d.t(rx + 160, y, v, 13, 600, INK, "end")
        if v:
            d.rect(rx + 172, y - 10, (rw - 172) * v / steps[0][1], 11, ORD)
        y += 19
    # Klassens kostnadsbilde
    y += 18
    d.t(rx, y, "Kjedekost per ferdig spill", 15, 600, INK)
    F = KL["ferdige"]["kjedekost"]
    FJ = KL["fjoraaret"]
    y += 16
    lo, hi = 0, 3600
    sx = lambda v: rx + 10 + (v - lo) / (hi - lo) * (rw - 20)
    fer = sorted([s["kjedekost"] for s in spill if s["status"] == "ferdig"])
    assert len(fer) == KL["ferdige"]["antall"] and median(fer) == F["median"]
    # prikkstripe, stablet i små søyler per 100 kr
    bins = {}
    for v in fer:
        b = int(v // 150)
        bins[b] = bins.get(b, 0) + 1
        d.circle(sx(b * 150 + 75), y + 62 - bins[b] * 8, 3.2, ORD)
    d.line(sx(lo), y + 66, sx(hi), y + 66, HAIR2, 1)
    for v in (0, 1000, 2000, 3000):
        d.t(sx(v), y + 82, nf(v, 0), 12, 400, INK3, "middle")
    d.line(sx(F["median"]), y + 6, sx(F["median"]), y + 66, INK, 1.6)
    d.t(sx(F["median"]) + 4, y + 8, f"Median {nf(F['median'], 0)}", 12, 700, INK)
    d.line(sx(FJ["median_kjedekost"]), y + 18, sx(FJ["median_kjedekost"]), y + 66, INK, 1, dash="3 3")
    d.t(sx(FJ["median_kjedekost"]) + 4, y + 22, f"Fjoråret {nf(FJ['median_kjedekost'], 0)}", 12, 400, INK2)
    s17 = [s for s in spill if s["spill"] == 17][0]
    y += 104
    d.para(rx, y, f"Ett punkt er ett ferdig spill, samlet per 150 kr. Hele kjeden: summen av fire Roller og to kostnadsarter. Fjoråret: {FJ['klasse']}, {FJ['spill']} spill.", rw, 13, 17, fill=INK2)
    y += 56
    d.t(rx, y, "Mønstre i klassen", 15, 600, INK)
    y += 22
    for k_, v_ in KL["moenstre"].items():
        d.t(rx, y, k_, 13, 400, INK)
        d.t(rx + rw, y, f"{v_}", 13, 600, INK, "end")
        d.line(rx, y + 6, rx + rw, y + 6, HAIR, 1)
        y += 21
    d.para(rx, y + 6, "Antall ganger mønsteret er funnet i ordrene, alle spill sammen. Brukes i Klasserapporten, uten navn.", rw, 13, 17, fill=INK2)
    d.t(rx, 896, "Cellene: netto lager per uke. Trinn ved 13, 25 og 49 enheter. Grå: null.", 12, 400, INK2)
    d.button(rx, 916, 150, 40, "Vis som tabell", primary=False, size=14)
    d.button(rx + 162, 916, 150, 40, "Vis i plenum", primary=False, size=14)
    d.demodata(rx + rw, 948, a="end")
    d.save()


if __name__ == "__main__":
    build_07()
    build_08()
