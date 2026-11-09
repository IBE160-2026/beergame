"""07 debrief og 08 lærerens oversikt."""
from e09cost import *
from screens_core import G, BARE, ALLE, K, A

SEATS = S17
DEM = FX["spill17"]["serier"]["demand"]
KL = FX["klasse"]
SPINE = ["Fabrikk", "Distributør", "Grossist", "Detaljist"]


def sec_title(d, x, y, n, title, width, size=22):
    """Stegnummeret bærer rekkefølgen i Debriefen."""
    d.line(x, y - 26, x + width, y - 26, INK, 1.2)
    d.t(x, y, str(n), size, 700, INK)
    return d.para(x + 24, y, title, width - 24, size, size + 5, 600, INK)


def demand_band(d, ax, y0, h, scale, wto=36):
    u = h / scale
    base = y0 + h
    dd = f"M{ax.xl(1):.1f} {base:.1f}"
    for w in range(1, wto + 1):
        v = DEM[w - 1]
        dd += f" L{ax.xl(w):.1f} {base - v * u:.1f} L{ax.xr(w):.1f} {base - v * u:.1f}"
    dd += f" L{ax.xr(wto):.1f} {base:.1f} Z"
    d.path(dd, BLUEF)
    d.line(ax.xl(1), base, ax.xr(wto), base, HAIR2, 1)


def role_bill_bar(d, x, y, s, sc, h=12):
    d.rect(x, y, s.lsum() * sc, h, BLUEF, BLUE, 1)
    d.rect(x + s.lsum() * sc, y, s.rsum() * sc, h, REDF, RED, 1)


def build_07():
    d = Doc("07-debrief", 2100, 1200, "Kjedens regning, Gruppedebrief i fem steg",
            "Forklaring, avsløring av etterspørselen, hele kjeden med fire ledd og hva hvert ledd betalte, ditt øyeblikk i Uke 11, kjedens regning som Rolle × uke i kroner mot simulert referanse, quiz og delt skjerm.")
    d.t(40, 44, "Debrief, Spill 17: kjeden betalte 2 266,00 kr. Hvorfor ble regningen slik?", 28, 600, INK)

    # ---------- Steg 1 ----------
    x, w = 40, 330
    y = 104
    sec_title(d, x, y, 1, "Skriv Forklaringen først", w)
    d.t(x, y + 30, "Ditt netto lager, hele spillet", 14, 600, INK)
    ax = Axis(x + 30, w - 30, 1, 36)
    Y = grid(d, ax, y + 40, 60, -40, 30, (-40, 0, 20), 13)
    net_area(d, ax, y + 40, 60, G.net, 1, 36)
    xaxis(d, ax, y + 116, [1, 12, 24, 36])
    d.t(x, y + 140, f"Din del av regningen: {nf(G.kostsum(36))} kr", 14, 600, INK)
    d.t(x, y + 158, f"lager {nf(G.lsum())} · restordre {nf(G.rsum())}", 14, 400, INK2)
    d.t(x, y + 184, "Hvorfor ble regningen din slik?", 15, 600, INK)
    d.rect(x, y + 192, w, 64, PAPER, HAIR2, 1, 6)
    d.para(x + 12, y + 213, "Restordren vokste, så jeg bestilte mye for å ta den igjen. Det som var på vei, regnet jeg lite med.", w - 24, 14, 19)
    d.button(x, y + 264, w, 38, "Send Forklaring", size=15)
    d.circle(x + 7, y + 321, 5, PAPER, INK, 1.5)
    d.para(x + 20, y + 326, "Avsløringen er låst til alle fire har sendt. Ida og Mikkel har sendt, Jonas skriver.", w - 20, 13, 17, fill=INK2)

    # ---------- Steg 2: klimaks ----------
    x2, w2 = 410, 560
    sec_title(d, x2, y, 2, "Kundene bestilte 4, så 8. Etter det endret de seg aldri.", w2)
    ax2 = Axis(x2 + 28, w2 - 28, 1, 36)
    y0 = y + 22
    h = 252
    scale = 26
    u = h / scale
    for v in (0, 8, 16, 24):
        yy = y0 + h - v * u
        d.line(ax2.x0, yy, ax2.x1, yy, HAIR, 1)
        d.t(ax2.x0 - 5, yy + 4, v, 13, 400, INK3, "end")
    demand_band(d, ax2, y0, h, scale)
    for k in range(1, 37):
        d.rect(ax2.xc(k) - 2, y0 + h - G.order(k) * u, 4, G.order(k) * u, INK)
    d.path("M" + " L".join(f"{ax2.xc(k):.1f} {y0 + h - G.inn(k) * u:.1f}" for k in range(1, 37)), stroke=GREY, sw=1.6)
    d.t(ax2.xc(11) + 8, y0 + h - 24 * u + 12, "Din ordre, 24 i Uke 11", 14, 600, INK)
    d.t(ax2.xc(29.5), y0 + h - 8 * u - 10, "Kundeetterspørsel: 8", 15, 700, BLUE, "middle", 'stroke="#FFFFFF" stroke-width="4" paint-order="stroke"')
    d.t(ax2.xc(2.5), y0 + h - 4 * u - 8, "4", 17, 700, BLUE, "middle")
    d.t(ax2.xc(19) + 6, y0 + h - 13.5 * u, "Ordre inn: det eneste du så", 14, 600, INK2)
    xaxis(d, ax2, y0 + h + 18, [1, 5, 10, 15, 20, 25, 30, 36], None)
    d.para(x2, y0 + h + 42, "Øvelsen heter Beer Game. Nesten alle grupper svinger slik, også i år. Det du så, var Idas ordrer, ikke kundene. Struktur gir atferd, derfor spør vi hvorfor og ikke hvem. P4, P6.", w2, 14, 19, fill=INK)

    # ---------- Steg 3: hele kjeden ----------
    x3, w3 = 1010, 1050
    sec_title(d, x3, y, 3, "Hele kjeden: svingningene vokser oppover, og regningen med dem", w3)
    ax3 = Axis(x3 + 128, 600, 1, 36)
    rx = ax3.x1 + 24
    d.t(rx, y + 26, "Hva leddet betalte, kr", 13, 600, INK2)
    d.t(x3 + w3, y + 26, "Forsterkning", 13, 600, INK2, "end")
    y3 = y + 34
    rh = 58
    fs = 32
    sc = 230 / max(K["kost_per_rolle"].values())
    onset = {}
    for i, r in enumerate(SPINE):
        yy = y3 + i * (rh + 10)
        S = SEATS[r]
        ou = rh / fs
        d.line(ax3.x0, yy, ax3.x1, yy, HAIR, 1)
        order_bars(d, ax3, yy, rh, S.order, 1, 36, fs, fill=INK if r == "Grossist" else ORD)
        # leddet som node i kjeden
        d.rect(x3, yy + 6, 110, rh - 8, PAPER, INK if r == "Grossist" else HAIR2, 1.2, 4)
        d.t(x3 + 10, yy + 26, r, 15, 600, INK)
        d.t(x3 + 10, yy + 44, "Sara, du" if r == "Grossist" else NAVN[r], 13, 400, INK2)
        if i < 3:
            d.line(x3 + 55, yy + rh - 2, x3 + 55, yy + rh + 8, INK2, 1.2)
            d.path(f"M{x3 + 51:.1f} {yy + rh + 4:.1f} L{x3 + 55:.1f} {yy + rh + 9:.1f} L{x3 + 59:.1f} {yy + rh + 4:.1f}", stroke=INK2, sw=1.2)
        role_bill_bar(d, rx, yy + 22, S, sc)
        d.t(rx, yy + 16, f"{nf(K['kost_per_rolle'][r])}", 15, 700, INK)
        d.t(x3 + w3, yy + 36, fx1(K["forsterkning"][r]), 20, 700, INK, "end", 'style="font-variant-numeric:lining-nums proportional-nums"')
        first = next(k for k in range(1, 37) if S.order(k) >= 10)
        onset[r] = (ax3.xc(first), yy + rh - S.order(first) * ou, first)
    pts = [onset[r] for r in SPINE]
    d.path("M" + " L".join(f"{a:.1f} {b - 3:.1f}" for a, b, _ in pts), stroke=RED, sw=1.2)
    for a, b, k in pts:
        d.circle(a, b - 3, 4, RED, PAPER, 1.5)
        d.t(a - 8, b - 6, f"Uke {k}", 13, 600, RED, "end")
    yd = y3 + 4 * (rh + 10)
    d.line(x3 + 55, yd - 10, x3 + 55, yd - 2, INK2, 1.2)
    demand_band(d, ax3, yd, 8 * rh / fs + 1, 8)
    d.t(x3 + 10, yd + 14, "Kundene", 15, 600, INK)
    d.t(ax3.xc(30), yd + 11, "4, så 8", 13, 600, BLUE, "middle")
    xaxis(d, ax3, yd + 8 * rh / fs + 18, [1, 5, 10, 15, 20, 25, 30, 36])
    d.t(rx, yd + 14, "Blått: lagerkost. Rødt: restordrekost.", 13, 400, INK2)
    d.t(x3 + 128, yd + 8 * rh / fs + 40, "Varene går nedover, ordrene oppover. Rødt punkt: første Uke med ordre på 10 eller mer. Samme skala i alle rader. P5.", 13, 400, INK2)

    # ---------- Steg 4: ditt øyeblikk og kjedens regning ----------
    yb = 504
    sec_title(d, 40, yb, 4, "Ditt øyeblikk i Uke 11, og hva det kostet kjeden", 2020)
    x4, w4 = 40, 400
    d.t(x4, yb + 30, "Dette så du", 14, 600, INK)
    e = chain_band(d, G, x4, yb + 38, w4, 11, 24, u=1.1, top=32, bottom=30, ls=13, cost=True)
    tw = w4
    d.t(x4, e + 26, "Dette regnet du", 14, 600, INK)
    ny = d.para(x4, e + 46, f"Posisjon {G.lager[10]} − {G.rest[10]} + {G.paavei(11)} = {G.posisjon(11)}. Med 24 ble den {G.posisjon(11) + 24}.", tw, 14, 19)
    d.t(x4, ny + 10, "Dette kostet det senere", 14, 600, INK)
    late = G.lsum(25, 36)
    ny = d.para(x4, ny + 30, f"{G.levering(15)} av de 24 kom i Uke 15. Restordren nådde {max(G.rest)} i Uke {G.rest.index(max(G.rest)) + 1}, så kom alt samtidig: lager i Uke 25 til 36 kostet deg {nf(late)} kr.", tw, 14, 19)
    d.t(x4, ny + 10, "Dette så de andre i Uke 11", 14, 600, INK)
    yy = ny + 30
    for r in ("Detaljist", "Distributør", "Fabrikk"):
        S = SEATS[r]
        d.t(x4, yy, f"{NAVN[r]}, {r}", 13, 400, INK)
        st = f"lager {S.lager[10]}" if S.net(11) >= 0 else f"restordre {S.rest[10]}"
        d.t(x4 + tw, yy, f"{st}, ordre inn {S.inn(11)}", 13, 400, INK2, "end")
        yy += 20
    d.para(x4, yy + 6, "KI-generert, kan ta feil: «Du så restordren, ikke posisjonen.»", tw, 13, 17, fill=INK2)

    # Kjedens regning: akkumulert over matrisen, felles tidsakse
    bx = 490
    L, R = chain_sums(S17)
    rl, rr = chain_sums(REF)
    d.t(bx, yb + 30, f"Kjedens regning: {nf(L + R)} kr", 20, 700, INK)
    d.t(bx + 282, yb + 30, f"lager {nf(L)} · restordre {nf(R)}. Stiplet: simulert referanse, {nf(rl + rr)} kr.", 14, 400, INK2)
    axm = Axis(bx + 104, 36 * 32, 1, 36)
    cy = yb + 48
    ch = 112
    Yc, pts, rpts = cum_area(d, axm, cy, ch, S17, ROLES, 2400, ref=REF, ticks=(0, 1000, 2000), ls=13)
    d.t(axm.x1 + 8, Yc(L + R) + 5, f"{nf(L + R)}", 14, 700, INK)
    d.t(axm.x1 + 8, Yc(rl + rr) + 5, f"{nf(rl + rr)} Simulert", 14, 600, INK2)
    d.line(axm.xc(11), cy - 4, axm.xc(11), cy + ch, INK, 1, dash="2 3")
    d.t(axm.xc(11) - 4, Yc(pts[10][2]) - 10, f"Uke 11: {nf(pts[10][2])}", 13, 600, INK, "end")
    xaxis(d, axm, cy + ch + 17, list(range(1, 37)), 11, 12)
    my = cy + ch + 30
    end = cost_matrix(d, bx, my + 8, axm, S17, SPINE, rowh=30, ls=13, tot_x=axm.x1 + 14, tot_w=290, highlight=11,
                      bold_role="Grossist", cell_ls=12)
    d.t(bx, end + 20, "Hver celle er ukas kostnad for leddet i kroner: blå er lager × 0,50, rød og halvfet er restordre × 1,00. Tom celle: 0. Raden Kjeden er summen. P1, P5, P8.", 13, 400, INK2)

    # ---------- Rad 3 ----------
    y5 = 930
    d.line(40, y5 - 26, 640, y5 - 26, INK, 1.2)
    d.t(40, y5, "Regningen, linje for linje, mot simulert referanse", 18, 600, INK)
    ledger(d, 40, y5 + 26, 600, S17, ROLES, ref=REF, ls=13, rowh=19, col1=40 + 200, col2=40 + 280)
    d.t(40, y5 + 240, "Stolpe: Spill 17. Grå strek: Simulert, alle teller det som er på vei. Ingen fasit.", 13, 400, INK2)

    x5, w5 = 690, 640
    sec_title(d, x5, y5, 5, "Debrief-quiz", w5, 18)
    d.para(x5, y5 + 28, "Hvilket ledd betalte mest av kjedens regning?", w5, 16, 21, 600)
    opts = [("Grossist", "wrong"), ("Distributør", "right"), ("Detaljist", None), ("Fabrikk", None)]
    ow = (w5 - 12) / 2
    for i, (lab, st) in enumerate(opts):
        ox = x5 + (i % 2) * (ow + 12)
        oy = y5 + 44 + (i // 2) * 48
        col = RED if st == "wrong" else (INK if st == "right" else HAIR2)
        d.rect(ox, oy, ow, 40, PAPER, col, 1.4 if st else 1, 6)
        d.t(ox + 14, oy + 26, lab, 16, 600, INK)
        if st == "wrong":
            d.t(ox + ow - 14, oy + 26, "Ditt svar, ikke riktig", 14, 600, RED, "end")
        if st == "right":
            d.t(ox + ow - 14, oy + 26, "Riktig", 14, 600, INK, "end")
    kp = K["kost_per_rolle"]
    ny = d.para(x5, y5 + 160, f"Grossist betalte {nf(kp['Grossist'])} kr. Distributør betalte {nf(kp['Distributør'])} og Fabrikk {nf(kp['Fabrikk'])}, uten å se en eneste kunde. Svingningene vokser oppover i kjeden, og regningen følger med. Det er struktur, ikke skyld.", w5, 14, 19)
    d.t(x5, ny + 6, "P5, P6, P8", 13, 400, INK3)

    xs, ws = 1380, 680
    sec_title(d, xs, y5, " ", "Delt skjerm: kjeden og regningen samtidig", ws, 18)
    fy = y5 + 14
    d.rect(xs, fy, ws, 222, PAPER, HAIR2, 1.4, 8)
    axs = Axis(xs + 110, 360, 1, 36)
    yr = fy + 14
    rh2 = 40
    scs = 110 / max(kp.values())
    for r in SPINE:
        S = SEATS[r]
        Ys = yscale(yr, rh2, -70, 60)
        d.line(axs.x0, Ys(0), axs.x1, Ys(0), HAIR2, 1)
        net_area(d, axs, yr, rh2, S.net, 1, 36, -70, 60, lw=1.4)
        d.t(xs + 14, Ys(0) + 4, r, 14, 600, INK)
        role_bill_bar(d, axs.x1 + 20, Ys(0) - 6, S, scs, 10)
        d.t(xs + ws - 14, Ys(0) + 4, nf(kp[r]), 14, 600, INK, "end")
        yr += rh2 + 6
    d.t(xs + 14, yr + 12, "Kundene", 14, 600, INK)
    demand_band(d, axs, yr, 16, 8)
    d.t(xs + ws - 14, yr + 12, f"{nf(L + R)} kr", 14, 700, INK, "end")
    d.t(xs, fy + 242, "Netto lager på samme skala, og hva hvert ledd betalte. Gruppa ser dette sammen.", 13, 400, INK2)
    d.demodata(40, 1192, "Demodata. Simulerte tall er merket Simulert.", 13, "start")
    d.save()


# ---------- 08 ----------
def chain_cell(lg, rs):
    """Celle i klassens kostnadsvegg: hue etter største kostnadsart, trinn etter kjedens kroner den uka."""
    tot = lg + rs
    if tot <= 0:
        return None
    kind = "rest" if rs >= lg else "lager"
    return cell_style(kind, tot, (40, 100))[0]


def status_txt(sp):
    return {"ferdig": "Ferdig", "pågår": "Pågår", "pauset": "Pause", "venter": "Venter"}[sp["status"]]


def build_08():
    d = Doc("08-laerer-oversikt", 1600, 1000, "Kjedens regning, Oversikt for Faglærer",
            "60 Klassespill på én skjerm: kjedens kostnad per uke som matrisevegg, kjedekost per spill delt i lager og restordre, status, hvem spillene venter på, KI-seter, klassens regning og trakten.")
    fx0, fy0, fw, fh = 40, 20, 1520, 960
    d.rect(fx0, fy0, fw, fh, PAPER, HAIR2, 1.2, 8)
    X = fx0 + 24
    spill = KL["spill"]
    counts = {k: sum(1 for s in spill if s["status"] == k) for k in ("venter", "pauset", "pågår", "ferdig")}
    d.t(X, fy0 + 38, "Oversikt", 24, 700, INK)
    d.t(X + 104, fy0 + 38, "class-of-1994, IBE160", 15, 400, INK2)
    d.t(X + 290, fy0 + 38, f"{counts['ferdig']} ferdig · {counts['pågår'] + counts['pauset']} pågår (herav {counts['pauset']} pauset) · {counts['venter']} venter", 15, 600, INK)
    d.t(fx0 + fw - 24, fy0 + 38, "Spillfrist ti. 8. des", 15, 400, INK2, "end")

    # Filter
    yf = fy0 + 74
    ki = sum(1 for s in spill if s["ki_seter"] > 0)
    labs = [("Alle", len(spill)), ("Venter", counts["venter"]), ("Pause", counts["pauset"]), ("Pågår", counts["pågår"]), ("Ferdig", counts["ferdig"]), ("Med KI-spiller", ki)]
    xx = X
    for i, (lab, c) in enumerate(labs):
        s = f"{lab} {c}"
        wd = text_w(s, 14) + 22
        d.rect(xx, yf - 14, wd, 26, INK if i == 0 else PAPER, None if i == 0 else HAIR2, 1, 4)
        d.t(xx + wd / 2, yf + 4, s, 14, 600, PAPER if i == 0 else INK, "middle")
        xx += wd + 8

    # Matrisevegg
    cx0 = X + 34
    cell = 13.2
    ax = Axis(cx0, 36 * cell, 1, 36)
    yt = yf + 40
    d.t(X, yt, "Kjedens kostnad per uke, alle 60 spill", 16, 600, INK)
    # legende
    lx = X + 300
    d.t(lx, yt, "Mest restordre", 13, 400, INK2)
    for i, c in enumerate(reversed(RK)):
        d.rect(lx + 96 + i * 18, yt - 11, 16, 12, c)
    for i, c in enumerate(LK):
        d.rect(lx + 154 + i * 18 + 4, yt - 11, 16, 12, c)
    d.t(lx + 218, yt, "Mest lager", 13, 400, INK2)
    d.t(lx + 300, yt, "Trinn: under 40, 40–100, over 100 kr", 13, 400, INK2)
    # kolonneoppsummering: median ukeskostnad, ferdige spill
    ferd = [s for s in spill if s["status"] == "ferdig"]
    wc = {s["spill"]: class_week_costs(s) for s in spill}
    med_l = [median([wc[s["spill"]][k][0] for s in ferd]) for k in range(36)]
    med_r = [median([wc[s["spill"]][k][1] for s in ferd]) for k in range(36)]
    sy = yt + 14
    sh = 40
    mx = max(a + b for a, b in zip(med_l, med_r))
    for k in range(36):
        tot = med_l[k] + med_r[k]
        hh = tot / mx * sh
        rr_ = med_r[k] / mx * sh
        d.rect(ax.xl(k + 1) + 1, sy + sh - hh, cell - 2, hh - rr_, BLUE)
        d.rect(ax.xl(k + 1) + 1, sy + sh - rr_, cell - 2, rr_, RED)
    d.line(ax.x0, sy + sh, ax.x1, sy + sh, HAIR2, 1)
    d.para(ax.x1 + 12, sy + 12, "Median per uke i de 41 ferdige spillene: rødt restordre, blått lager over.", 260, 13, 17, fill=INK2)
    # ukeakse
    wy = sy + sh + 16
    for k in (1, 6, 12, 18, 24, 30, 36):
        d.t(ax.xc(k), wy, k, 12, 400, INK3, "middle")
    # kolonneoverskrifter til høyre
    c_uke, c_ki, c_kost = ax.x1 + 30, ax.x1 + 56, ax.x1 + 116
    bar_x, bar_w = ax.x1 + 126, 190
    c_txt = bar_x + bar_w + 10
    d.t(X, wy, "Spill", 12, 600, INK2)
    d.t(c_uke, wy, "Uke", 12, 600, INK2, "end")
    d.t(c_ki, wy, "KI", 12, 600, INK2, "end")
    d.t(c_kost, wy, "Kjede, kr", 12, 600, INK2, "end")
    d.t(bar_x, wy, "Lager | restordre", 12, 600, INK2)
    d.t(c_txt, wy, "Venter på", 12, 600, INK2)
    ksc = bar_w / 3600
    near = sorted([s for s in spill if s["status"] == "venter"], key=lambda s: -s["ventet_timer"])
    top = near[0]
    groups = [("Venter", near), ("Pause", [s for s in spill if s["status"] == "pauset"]),
              ("Pågår", sorted([s for s in spill if s["status"] == "pågår"], key=lambda s: -s["uke"])),
              ("Ferdig, lavest kjedekost øverst", sorted(ferd, key=lambda s: s["kjedekost"]))]
    rowh = 10.6
    yy = wy + 8
    medx = bar_x + KL["ferdige"]["kjedekost"]["median"] * ksc
    fjx = bar_x + KL["fjoraaret"]["median_kjedekost"] * ksc
    simx = bar_x + A["kjedekost"] * ksc
    ytop_rows = yy
    for gname, rows in groups:
        yy += 15
        d.t(X, yy - 2, f"{gname} {len(rows)}", 12, 700, INK)
        for sp in rows:
            costs = wc[sp["spill"]]
            isnear = sp["spill"] == top["spill"]
            if isnear:
                d.rect(X - 4, yy, c_txt + 150 - X, rowh, REDF, None, 1, 2)
            d.t(X + 26, yy + 8.6, sp["spill"], 10.5, 700 if isnear else 400, INK, "end")
            for k, (lg, rs) in enumerate(costs):
                f_ = chain_cell(lg, rs)
                if f_:
                    d.rect(ax.xl(k + 1) + 0.6, yy + 0.6, cell - 1.2, rowh - 1.2, f_)
            if sp["status"] != "ferdig":
                d.line(ax.xr(sp["uke"]) + 1, yy, ax.xr(sp["uke"]) + 1, yy + rowh, INK, 1.4)
            d.t(c_uke, yy + 8.6, sp["uke"], 10.5, 400, INK, "end")
            d.t(c_ki, yy + 8.6, sp["ki_seter"] or "", 10.5, 400, INK, "end")
            d.t(c_kost, yy + 8.6, nf(sp["kjedekost"], 0), 10.5, 600 if sp["status"] == "ferdig" else 400, INK, "end")
            lg_t = sum(a for a, _ in costs)
            rs_t = sum(b for _, b in costs)
            if sp["status"] == "ferdig":
                d.rect(bar_x, yy + 2, lg_t * ksc, rowh - 4, BLUE)
                d.rect(bar_x + lg_t * ksc, yy + 2, rs_t * ksc, rowh - 4, RED)
            else:
                d.rect(bar_x, yy + 2, (lg_t + rs_t) * ksc, rowh - 4, "none", INK2, 0.8)
            if sp["status"] == "venter":
                d.t(c_txt, yy + 8.6, f"{sp['navn']}, {sp['venter_paa']}, {sp['ventet_timer']} t", 10.5, 700 if isnear else 400, INK)
            elif sp["status"] == "pauset":
                d.t(c_txt, yy + 8.6, f"Fortsetter {sp['fortsetter']}", 10.5, 400, INK2)
            yy += rowh
    # referanselinjer i stolpekolonnen
    for xv, lab, dash in ((medx, "Median", None), (fjx, "Fjoråret", "3 3"), (simx, "Simulert", "1 3")):
        d.line(xv, ytop_rows + 8, xv, yy, INK, 1, dash=dash)
    d.t(bar_x, yy + 16, f"Strek: median {nf(KL['ferdige']['kjedekost']['median'], 0)}. Stiplet: fjoråret {nf(KL['fjoraaret']['median_kjedekost'], 0)}. Prikket: Simulert {nf(A['kjedekost'], 0)}. Åpen stolpe: foreløpig.", 12, 400, INK2)
    d.t(X, yy + 16, "Svart strek i raden: der spillet er nå.", 12, 400, INK2)

    # ---------- Høyre kolonne ----------
    rx = 1100
    rw = fx0 + fw - 24 - rx
    y = fy0 + 74
    d.t(rx, y + 4, "Nær overtakelse", 16, 600, INK)
    d.rect(rx, y + 16, rw, 92, REDF, None, 1, 6)
    d.t(rx + 14, y + 42, f"Spill {top['spill']} venter på {top['navn']} ({top['venter_paa']})", 16, 700, INK)
    d.t(rx + 14, y + 64, f"{top['ventet_timer']} t. KI overtar om {24 - top['ventet_timer']} t.", 15, 400, INK)
    d.button(rx + 14, y + 74, 150, 28, f"Send Melding til {top['navn']}", size=13)
    d.button(rx + 174, y + 74, 110, 28, "Pause spillet", primary=False, size=13)
    yy2 = y + 136
    for s in near[1:]:
        d.t(rx, yy2, f"Spill {s['spill']}", 14, 600, INK)
        d.t(rx + 70, yy2, f"{s['navn']}, {s['venter_paa']}, {s['ventet_timer']} t", 14, 400, INK)
        d.t(rx + rw, yy2, "Send Melding", 13, 600, BLUE, "end", 'text-decoration="underline"')
        yy2 += 22

    # Klassens regning
    y = yy2 + 22
    d.line(rx, y - 18, rx + rw, y - 18, HAIR, 1)
    d.t(rx, y, "Klassens regning, 41 ferdige spill", 16, 600, INK)
    tot_l = sum(role_split(s, r)[0] for s in ferd for r in ROLES)
    tot_r = sum(role_split(s, r)[1] for s in ferd for r in ROLES)
    assert abs(tot_l + tot_r - sum(s["kjedekost"] for s in ferd)) <= 0.5 * len(ferd)  # kjedekost er avrundet per spill
    d.t(rx, y + 22, f"Sum {nf(tot_l + tot_r, 0)} kr: lager {nf(tot_l, 0)}, restordre {nf(tot_r, 0)} ({round(100 * tot_r / (tot_l + tot_r))} %).", 13, 400, INK2)
    # fordeling: prikkplott
    py = y + 42
    pw_ = rw
    xs_ = lambda v: rx + v / 3600 * pw_
    d.line(rx, py + 64, rx + pw_, py + 64, HAIR2, 1)
    q = KL["ferdige"]["kjedekost"]
    d.rect(xs_(q["q1"]), py + 4, xs_(q["q3"]) - xs_(q["q1"]), 60, TINT)
    bins_ = {}
    for s in sorted(ferd, key=lambda s: s["kjedekost"]):
        b = int(s["kjedekost"] // 150)
        n = bins_.get(b, 0)
        bins_[b] = n + 1
        d.circle(xs_(b * 150 + 75), py + 58 - n * 9, 3.6, INK)
    d.line(xs_(q["median"]), py, xs_(q["median"]), py + 64, INK, 1.4)
    d.t(xs_(q["median"]) + 4, py + 6, f"Median {nf(q['median'], 0)}", 12, 600, INK)
    d.line(xs_(KL["fjoraaret"]["median_kjedekost"]), py, xs_(KL["fjoraaret"]["median_kjedekost"]), py + 64, INK, 1, dash="3 3")
    d.t(xs_(KL["fjoraaret"]["median_kjedekost"]) + 4, py + 6, f"Fjoråret {nf(KL['fjoraaret']['median_kjedekost'], 0)}", 12, 400, INK2)
    d.line(xs_(A["kjedekost"]), py, xs_(A["kjedekost"]), py + 64, INK, 1, dash="1 3")
    d.t(xs_(A["kjedekost"]) - 4, py + 6, f"Simulert {nf(A['kjedekost'], 0)}", 12, 400, INK2, "end")
    for v in (0, 1000, 2000, 3000):
        d.t(xs_(v), py + 80, nf(v, 0), 12, 400, INK3, "middle")
    d.t(rx, py + 100, f"Kjedekost per spill. Grått felt: midtre halvdel, {nf(q['q1'], 0)} til {nf(q['q3'], 0)} kr.", 12, 400, INK2)
    # per Rolle: median av lager og restordre
    y = py + 128
    d.t(rx, y, "Median per Rolle, kr", 13, 600, INK)
    d.t(rx + rw, y, "lager + restordre", 13, 400, INK2, "end")
    rsc = (rw - 170) / 1000
    for i, r in enumerate(SPINE):
        yy3 = y + 20 + i * 22
        ml = median([role_split(s, r)[0] for s in ferd])
        mr = median([role_split(s, r)[1] for s in ferd])
        d.t(rx, yy3 + 10, r, 13, 400, INK)
        d.rect(rx + 90, yy3, ml * rsc, 12, BLUE)
        d.rect(rx + 90 + ml * rsc, yy3, mr * rsc, 12, RED)
        d.t(rx + rw, yy3 + 10, f"{nf(ml, 0)} + {nf(mr, 0)}", 13, 400, INK, "end")
    # Trakt
    y = y + 20 + 4 * 22 + 30
    d.line(rx, y - 18, rx + rw, y - 18, HAIR, 1)
    d.t(rx, y, "Trakten", 16, 600, INK)
    tr = KL["traktA"]
    steps = [("Registrert", tr["registrert"]), ("Klassespill ferdig", tr["klassespill_ferdig"]), ("Debrief ferdig", tr["debrief_ferdig"]),
             ("Quiz bestått", tr["quiz_bestått"]), ("Replay ferdig", tr["replay_ferdig"]), ("Test levert", tr["test_levert"]), ("KI-vurdering klar", tr["ki_vurdering_klar"])]
    for i, (lab, v) in enumerate(steps):
        yy4 = y + 14 + i * 19
        d.t(rx, yy4 + 10, lab, 13, 400, INK)
        d.t(rx + 150, yy4 + 10, v, 13, 600, INK, "end")
        d.rect(rx + 160, yy4 + 1, (rw - 160) * v / steps[0][1], 11, ORD if v else HAIR)
    yb_ = y + 14 + 7 * 19 + 24
    d.button(rx, yb_, 140, 36, "Vis som tabell", primary=False, size=14)
    d.button(rx + 150, yb_, 140, 36, "Vis i plenum", primary=False, size=14)
    d.demodata(fx0 + fw - 24, fy0 + fh - 10, a="end")
    d.save()


if __name__ == "__main__":
    build_07()
    build_08()
