"""07 Debrief og 08 lærerens oversikt."""
from statistics import median

from e04lib import *
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
        while text_w(s, fs) > ax.slot - 2 and fs > 8:
            fs -= 0.5
        d.t(ax.xc(k), base, s, fs, 700 if k == bold_at else 400, col, "middle")


# ---------- 07 ----------
def build_07():
    d = Doc("07-debrief", 2100, 1200, f"{NAME}, Gruppedebrief i fem steg",
            "Forklaring, avsløring av etterspørselen, alle fire Rollers ordre som graf over tabell, ditt øyeblikk i Uke 11 "
            "med hele kjeden, kjedens regning per Rolle og kostnadsart, og quiz. Delt skjerm.")
    d.t(40, 44, "Debrief, Spill 17: fra «hadde jeg rett?» til «hvorfor skjedde det?»", 28, 600, INK)

    # Steg 1
    x, w, y = 40, 320, 104
    sec_title(d, x, y, 1, "Skriv Forklaringen først", w)
    d.t(x, y + 32, "Ditt netto lager, hele spillet", 14, 600, INK)
    ax = Axis(x + 30, w - 30, 1, 36)
    Y = grid(d, ax, y + 42, 90, -40, 30, (-40, 0, 20), 13)
    net_area(d, ax, y + 42, 90, G.net, 1, 36)
    for k in range(1, 37):
        f, _ = net_cell(G.net(k))
        d.rect(ax.xl(k) + 0.4, y + 140, ax.slot - 0.8, 12, f)
    d.t(x, y + 150, "Uke", 12, 400, INK3)
    xaxis(d, ax, y + 170, [1, 12, 24, 36], size=12)
    d.t(x, y + 204, "Hvorfor svingte lageret ditt?", 15, 600, INK)
    d.rect(x, y + 214, w, 104, PAPER, HAIR2, 1, 6)
    d.para(x + 12, y + 238, "Restordren vokste, så jeg bestilte mye for å ta den igjen. Det som var på vei, regnet jeg lite med.", w - 24, 15, 20)
    d.button(x, y + 330, w, 44, "Send Forklaring", size=15)
    d.circle(x + 7, y + 399, 5, PAPER, INK, 1.5)
    d.para(x + 20, y + 404, "Avsløringen er låst til alle fire har sendt. Ida og Mikkel har sendt, Jonas skriver.", w - 20, 14, 19, fill=INK2)

    # Steg 2: klimaks
    x2, w2 = 400, 680
    sec_title(d, x2, y, 2, "Kundene bestilte 4, så 8. Etter det endret de seg aldri.", w2)
    ax2 = Axis(x2 + 92, w2 - 92, 1, 36)
    y0, h, scale = y + 26, 250, 26
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
    d.t(ax2.xc(29.5), y0 + h - 8 * u - 10, "Kundene: 8", 16, 700, BLUE, "middle", 'stroke="#FFFFFF" stroke-width="4" paint-order="stroke"')
    d.t(ax2.xc(2.5), y0 + h - 4 * u - 8, "4", 18, 700, BLUE, "middle")
    d.t(ax2.xc(19) + 6, y0 + h - 13 * u, "Ordre inn: det eneste du så", 15, 600, INK2)
    ty = y0 + h + 4
    rh = 18
    table_row(d, ax2, x2, ty, rh, "Uke", lambda k: k if k % 5 == 0 or k == 1 else None, 12, lab_w=600, lab_col=INK2)
    table_row(d, ax2, x2, ty + rh, rh, "Kundene", lambda k: DEM[k - 1], 12)
    table_row(d, ax2, x2, ty + 2 * rh, rh, "Ordre inn", G.inn, 12)
    table_row(d, ax2, x2, ty + 3 * rh, rh, "Din ordre", G.order, 12, cell=seq_cell, bold_at=11)
    for i in range(1, 4):
        d.line(x2, ty + i * rh, ax2.x1, ty + i * rh, HAIR, 1)
    d.line(x2, ty + 4 * rh, ax2.x1, ty + 4 * rh, HAIR, 1)
    d.para(x2, ty + 4 * rh + 26, "Øvelsen heter Beer Game. Kundene endret seg én gang, i Uke 5. Det du så, var Idas ordrer. Nesten alle grupper svinger slik, også i år. Struktur gir atferd, derfor spør vi hvorfor og ikke hvem.", w2, 15, 20, fill=INK)
    d.t(x2, ty + 4 * rh + 92, "P4, P6", 13, 400, INK3)

    # Steg 3
    x3, w3 = 1120, 940
    sec_title(d, x3, y, 3, "Oppstrøms vokser svingningene, og de kommer senere", w3)
    ax3 = Axis(x3 + 100, w3 - 100 - 64, 1, 36)
    g0, gh, gs = y + 24, 190, 32
    Yo = yscale(g0, gh, 0, gs)
    for v in (0, 10, 20, 30):
        d.line(ax3.x0, Yo(v), ax3.x1, Yo(v), HAIR2 if v == 0 else HAIR, 1)
        d.t(ax3.x0 - 5, Yo(v) + 4, v, 13, 400, INK3, "end")
    demand_band(d, ax3, g0, gh, gs)
    for r in ["Detaljist", "Distributør", "Fabrikk", "Grossist"]:
        S = SEATS[r]
        d.path(pts_path([(ax3.xc(k), Yo(S.order(k))) for k in range(1, 37)]), stroke=ROLE_LINE[r], sw=2.4 if r == "Grossist" else 1.5)
    labpos = {"Fabrikk": (15, 31, "start"), "Distributør": (15.5, 19.6, "middle"), "Grossist": (10.6, 24, "end"), "Detaljist": (7, 12.5, "end")}
    for r, (wk, v, a) in labpos.items():
        dx = 8 if a == "start" else (-8 if a == "end" else 0)
        d.t(ax3.xc(wk) + dx, Yo(v) - 4, f"{r}{' (du)' if r == 'Grossist' else ''} {fx1(K['forsterkning'][r])}", 14, 600, INK, a,
            'stroke="#FFFFFF" stroke-width="4" paint-order="stroke"')
    d.t(ax3.xc(2.8), Yo(1.2), "Kundene", 14, 600, BLUE, "middle")
    ty3 = g0 + gh + 4
    rh3 = 21
    table_row(d, ax3, x3, ty3, rh3, "Uke", lambda k: k if k % 2 == 1 or k == 36 else None, 12, lab_w=600, lab_col=INK2)
    onset = {}
    for i, r in enumerate(UP):
        S = SEATS[r]
        ry = ty3 + (i + 1) * rh3
        d.line(x3, ry, ax3.x1 + 64, ry, HAIR, 1)
        table_row(d, ax3, x3, ry, rh3, r + (" (du)" if r == "Grossist" else ""), S.order, 12, cell=seq_cell,
                  lab_w=700 if r == "Grossist" else 400)
        d.t(ax3.x1 + 64, ry + rh3 / 2 + 5, fx1(K["forsterkning"][r]), 14, 700, INK, "end")
        first = next(k for k in range(1, 37) if S.order(k) >= 10)
        onset[r] = first
        d.rect(ax3.xl(first) + 0.3, ry + 0.6, ax3.slot - 0.6, rh3 - 1.2, "none", RED, 2, 1)
    ry = ty3 + 5 * rh3
    d.line(x3, ry, ax3.x1 + 64, ry, HAIR, 1)
    table_row(d, ax3, x3, ry, rh3, "Kundene", lambda k: DEM[k - 1], 12)
    d.line(x3, ry + rh3, ax3.x1 + 64, ry + rh3, HAIR, 1)
    d.t(ax3.x1 + 64, ty3 + rh3 / 2 + 5, "Forst.", 12, 600, INK2, "end")
    d.para(x3, ry + rh3 + 24, f"Rød ramme: første Uke med ordre på 10 eller mer, Uke {onset['Detaljist']}, {onset['Grossist']}, {onset['Distributør']} og {onset['Fabrikk']}. Mørkere celle er større ordre, samme trinn i alle rader. Forsterkning er spennet i ordre delt på spennet hos kundene. P5.", w3, 14, 19, fill=INK2)

    # Rad 2
    yb = 640
    x4, w4 = 40, 900
    sec_title(d, x4, yb, 4, "Ditt øyeblikk: Uke 11. Du bestilte 24 med 16 på vei.", w4)
    d.t(x4, yb + 32, "Hele kjeden i Uke 11", 15, 600, INK)
    yk = chain_full(d, SEATS, x4, yb + 42, 470, 11, ls=13, un=0.55, upipe=0.9)
    d.t(x4, yk + 22, "Dette så du", 15, 600, INK)
    gtable(d, G, x4, yk + 32, 470, 11, 24, wmin=4, wmax=15, lw=78, hn=60, hc=20, rh=18, ls=12, gapf=4,
           rows=("inn", "lev", "net", "pv", "ord", "kost"), titles=False, netlabel=False, cost_tick=False)

    tx, tw = x4 + 510, 390
    d.t(tx, yb + 32, "Dette regnet du", 15, 600, INK)
    ny = d.para(tx, yb + 54, f"Posisjon {G.lager[10]} − {G.rest[10]} + {G.paavei(11)} = {G.posisjon(11)}. Med 24 ble den {G.posisjon(11) + 24}.", tw, 15, 20)
    d.t(tx, ny + 12, "Dette kostet det senere", 15, 600, INK)
    late = G.kostsum(36) - G.kostsum(24)
    assert all(G.rest[k - 1] == 0 for k in range(25, 37))
    ny = d.para(tx, ny + 34, f"{G.levering(15)} av de 24 kom i Uke 15. På vei toppet på {max(G.pv)} i Uke {G.pv.index(max(G.pv)) + 1}, og i Uke {G.lager.index(max(G.lager)) + 1} sto du med lager {max(G.lager)}. Lager i Uke 25 til 36 kostet {nf(late)} kr.", tw, 15, 20)
    d.t(tx, ny + 12, "Dette så de andre i Uke 11", 15, 600, INK)
    ny = d.para(tx, ny + 34, "Kjeden over viser alle fire i samme Uke. Mikkel så ordren din først i Uke 13, og visste ikke hvorfor den var så stor.", tw, 14, 19, fill=INK2)
    ny = d.para(tx, ny + 8, "KI-generert, kan ta feil: «Du reagerte på restordren du så, ikke på posisjonen. Det som var på vei, kom likevel.»", tw, 14, 19, fill=INK2)
    # sammenligning
    B = FX["bare_sara_teller_paa_vei"]
    yy = ny + 30
    d.t(tx, yy, "Samme kjede, Sara teller alt på vei", 15, 600, INK)
    d.t(tx, yy + 20, "Simulert. Viser sammenhengen, ikke en fasit.", 14, 400, INK2)
    rows = [("", "Spill 17", "Simulert"),
            ("Din ordre, Uke 11", "24", str(BARE.order(11))),
            ("Grossist, lagerkost", nf(G.sum_lk()), nf(BARE.sum_lk())),
            ("Grossist, restordrekost", nf(G.sum_rk()), nf(BARE.sum_rk())),
            ("Kjeden, kr", nf(K["kjedekost"]), nf(B["kjedekost"])),
            ("Forsterkning, Grossist", fx1(K["forsterkning"]["Grossist"]), fx1(B["forsterkning"]["Grossist"]))]
    yy += 44
    for i, row in enumerate(rows):
        bold = 600 if i == 0 else 400
        d.t(tx, yy, row[0], 14, bold, INK)
        d.t(tx + 290, yy, row[1], 14, bold, INK, "end")
        d.t(tx + tw, yy, row[2], 14, bold, INK, "end")
        d.line(tx, yy + 7, tx + tw, yy + 7, HAIR, 1)
        yy += 21
    d.t(tx, yy + 6, "P3, P7, P8", 13, 400, INK3)

    # Kjedens regning
    xc, wc = 980, 620
    sec_title(d, xc, yb, 0, "Kjedens regning: 2 266,00 kr", wc)
    d.t(xc, yb + 32, "Målet var lavest kostnad for hele kjeden, ikke for ett ledd.", 15, 400, INK2)
    lwc, sw = 132, 82
    axb = Axis(xc + lwc, wc - lwc - sw, 1, len(BLOCKS))
    gy0, ghh = yb + 50, 140

    def blk(S, a, b, part=None):
        f = {"lk": S.lagerkost, "rk": S.restkost}.get(part, S.ukekost)
        return sum(f(k) for k in range(a, b + 1))

    tot_l = [sum(blk(SEATS[r], a, b, "lk") for r in ROLES) for a, b in BLOCKS]
    tot_r = [sum(blk(SEATS[r], a, b, "rk") for r in ROLES) for a, b in BLOCKS]
    sim = [sum(blk(ALLE_SEATS[r], a, b) for r in ROLES) for a, b in BLOCKS]
    assert abs(sum(tot_l) + sum(tot_r) - K["kjedekost"]) < 1e-9
    assert abs(sum(sim) - FX["alle_teller_paa_vei"]["kjedekost"]) < 1e-9
    cmax = 700
    Yc = yscale(gy0, ghh, 0, cmax)
    for v in (0, 200, 400, 600):
        d.line(axb.x0, Yc(v), axb.x1, Yc(v), HAIR2 if v == 0 else HAIR, 1)
        d.t(axb.x0 - 6, Yc(v) + 4, f"{v} kr" if v else "0", 13, 400, INK3, "end")
    bwb = axb.slot - 14
    for i in range(len(BLOCKS)):
        xb = axb.xc(i + 1) - bwb / 2
        hl = (gy0 + ghh) - Yc(tot_l[i])
        hr = (gy0 + ghh) - Yc(tot_r[i])
        d.rect(xb, gy0 + ghh - hl, bwb, hl, BLUE)
        if hr > 0:
            d.rect(xb, gy0 + ghh - hl - hr - (2 if hl > 0 else 0), bwb, hr, RED)
        ys = Yc(sim[i])
        d.line(xb - 4, ys, xb + bwb + 4, ys, INK, 1.4, "4 3")
    d.t(axb.xc(3), Yc(tot_l[2] + tot_r[2]) - 8, "Restordre", 13, 600, INK, "middle")
    d.t(axb.xc(8) - bwb / 2 - 6, Yc(tot_l[7]) - 6, "Lager", 13, 600, INK, "end")
    d.t(axb.xc(9) + bwb / 2 + 6, Yc(sim[8]) + 4, "Simulert", 13, 400, INK2)
    # tabellen
    rt = gy0 + ghh + 6
    rr = 21
    d.t(xc, rt + 15, "Uke", 12, 600, INK2)
    for i, (a, b) in enumerate(BLOCKS):
        d.t(axb.xc(i + 1), rt + 15, f"{a}–{b}", 12, 400, INK3, "middle")
    d.t(xc + wc, rt + 15, "Sum", 12, 600, INK2, "end")
    trows = [(r, [blk(SEATS[r], a, b) for a, b in BLOCKS], 400) for r in ROLES]
    trows.append(("Kjeden", [tot_l[i] + tot_r[i] for i in range(9)], 700))
    trows.append(("herav restordre", tot_r, 400))
    trows.append(("Simulert, kjeden", sim, 400))
    for j, (lab, vals, wt) in enumerate(trows):
        ry = rt + (j + 1) * rr
        d.line(xc, ry, xc + wc, ry, HAIR2 if lab == "Kjeden" else HAIR, 1)
        col = INK2 if lab.startswith("Simulert") or lab.startswith("herav") else INK
        d.t(xc, ry + 15, lab + (" (du)" if lab == "Grossist" else ""), 13, wt, col)
        for i, v in enumerate(vals):
            d.t(axb.xc(i + 1), ry + 15, nf(v, 1) if v % 1 else nf(v, 0), 13, wt, col, "middle")
        tot = sum(vals)
        d.t(xc + wc, ry + 15, nf(tot), 13, 700 if wt == 700 else 600, col, "end")
    d.line(xc, rt + (len(trows) + 1) * rr, xc + wc, rt + (len(trows) + 1) * rr, HAIR, 1)
    ny = rt + (len(trows) + 1) * rr + 24
    share = sum(tot_r) / K["kjedekost"]
    d.para(xc, ny, f"Restordre er {nf(sum(tot_r))} av {nf(K['kjedekost'])} kr ({round(share * 100)} %), selv om hver enhet koster dobbelt så mye på lager: 1,00 mot 0,50. Stiplet strek er simulert referanse, der alle fire teller det som er på vei ({nf(FX['alle_teller_paa_vei']['kjedekost'])} kr). Simulert, ikke fasit.", wc, 14, 19, fill=INK2)
    d.t(xc, ny + 66, "P8, P6", 13, 400, INK3)

    # Steg 5
    x5, w5 = 1640, 420
    sec_title(d, x5, yb, 5, "Debrief-quiz", w5)
    ny = d.para(x5, yb + 34, f"Uke 11: lager {G.lager[10]}, restordre {G.rest[10]}, {G.paavei(11)} på vei. Hva er posisjonen før du bestiller?", w5, 16, 22, 600)
    yy = ny + 4
    for lab, st in ((sg(-13), "wrong"), (str(G.posisjon(11)), "right"), ("16", None), ("29", None)):
        col = RED if st == "wrong" else (INK if st == "right" else HAIR2)
        d.rect(x5, yy, w5, 38, PAPER, col, 1.4 if st else 1, 6)
        d.t(x5 + 14, yy + 25, lab, 16, 600, INK)
        if st == "wrong":
            d.t(x5 + w5 - 14, yy + 25, "Ditt svar, ikke riktig", 14, 600, RED, "end")
        if st == "right":
            d.t(x5 + w5 - 14, yy + 25, "Riktig", 14, 600, INK, "end")
        yy += 45
    ny = d.para(x5, yy + 8, "−13 er bare raden Netto lager. Raden På vei mangler: 0 − 13 + 16 = 3. Begge står i kolonne 11 i din egen tabell.", w5, 15, 20)
    d.t(x5, ny + 4, "P3", 13, 400, INK3)

    # Delt skjerm
    ys = ny + 40
    d.t(x5, ys, "Delt skjerm", 17, 600, INK)
    axs = Axis(x5 + 84, w5 - 84, 1, 36)
    kparts = lambda k: (sum(SEATS[r].lagerkost(k) for r in ROLES), sum(SEATS[r].restkost(k) for r in ROLES))
    cmx = max(sum(kparts(k)) for k in range(1, 37))
    d.t(x5, ys + 30, "Kjedekost", 12, 600, INK)
    d.t(x5, ys + 45, "per uke", 12, 400, INK2)
    cost_bars(d, axs, ys + 12, 58, kparts, 1, 36, cmx * 1.05, gap=1.6)
    d.t(axs.x1, ys + 10, f"Høyest {nf(cmx, 0)} kr", 12, 400, INK2, "end")
    yr = ys + 82
    d.t(x5, yr - 2, "Netto lager", 12, 600, INK)
    yr += 6
    for r in UP:
        d.t(x5, yr + 10, r, 12, 600 if r == "Grossist" else 400, INK)
        for k in range(1, 37):
            f, _ = net_cell(SEATS[r].net(k))
            d.rect(axs.xl(k) + 0.3, yr, axs.slot - 0.6, 13, f)
        yr += 15
    d.para(x5, yr + 16, "På storskjermen står tallet i hver celle. Gruppa ser alle fire ledd, hver student ser sitt eget steg på telefonen.", w5, 13, 17, fill=INK2)
    d.demodata(2060, 1188, "Demodata. Simulerte tall er merket Simulert.", 13, "end")
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
            while text_w(s_, f_) > ax.slot - 1.5 and f_ > 8:
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
    d.button(rx, yb_, rw / 2 - 6, 40, "Vis i plenum", primary=False, size=14)
    d.button(rx + rw / 2 + 6, yb_, rw / 2 - 6, 40, "Vis som tabell", primary=False, size=14)
    d.demodata(fx0 + fw - 24, fy0 + fh - 8, a="end")
    d.save()


if __name__ == "__main__":
    build_07()
    build_08()
