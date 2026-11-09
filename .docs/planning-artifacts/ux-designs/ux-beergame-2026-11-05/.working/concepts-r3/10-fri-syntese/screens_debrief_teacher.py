"""07 debrief og 08 lærerens oversikt."""
from statistics import median

from e10syn import *
from screens_core import G, BARE, ALLE, K, NAME

SEATS = {r: Seat(r) for r in ROLES}
SEATS_A = {r: Seat(r, FX["alle_teller_paa_vei"]) for r in ROLES}
SEATS_B = {r: Seat(r, FX["bare_sara_teller_paa_vei"]) for r in ROLES}
DEM = FX["spill17"]["serier"]["demand"]
KL = FX["klasse"]
CHAIN_WEEK = 18


def sec_title(d, x, y, n, title, width, size=22):
    """Stegnummeret bærer rekkefølgen i Debriefen."""
    d.line(x, y - 26, x + width, y - 26, INK, 1.2)
    d.t(x, y, str(n), size, 700, INK)
    return d.para(x + 24, y, title, width - 24, size, size + 5, 600, INK)


def demand_band(d, ax, y0, h, scale, w0=1, w1=36):
    u = h / scale
    base = y0 + h
    dd = f"M{ax.xl(w0):.1f} {base:.1f}"
    for w in range(w0, w1 + 1):
        v = DEM[w - 1]
        dd += f" L{ax.xl(w):.1f} {base - v * u:.1f} L{ax.xr(w):.1f} {base - v * u:.1f}"
    dd += f" L{ax.xr(w1):.1f} {base:.1f} Z"
    d.path(dd, BLUEF)
    d.line(ax.xl(w0), base, ax.xr(w1), base, HAIR2, 1)


def chain_cum(k, src):
    return sum(src[r].kostsum(k) for r in ROLES)


def build_07():
    d = Doc("07-debrief", 2100, 1200, f"{NAME}, Gruppedebrief i fem steg",
            "Forklaring, avsløring av etterspørselen, hele kjeden med fire ledd og ordrene som tall, ditt øyeblikk i Uke 11, "
            "kjedens regning mot simulert referanse, quiz, og delt skjerm.")
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
    x2, w2 = 380, 560
    sec_title(d, x2, y, 2, "Kundene kjøpte 4, så 8. Etter det endret de seg aldri.", w2)
    ax2 = Axis(x2 + 28, w2 - 28, 1, 36)
    y0 = y + 50
    h = 300
    scale = 26
    u = h / scale
    for v in (0, 8, 16, 24):
        yy = y0 + h - v * u
        d.line(ax2.x0, yy, ax2.x1, yy, HAIR, 1)
        d.t(ax2.x0 - 5, yy + 4, v, 13, 400, INK3, "end")
    demand_band(d, ax2, y0, h, scale)
    bw = 4.5
    for k in range(1, 37):
        d.rect(ax2.xc(k) - bw / 2, y0 + h - G.order(k) * u, bw, G.order(k) * u, INK)
    d.path("M" + " L".join(f"{ax2.xc(k):.1f} {y0 + h - G.inn(k) * u:.1f}" for k in range(1, 37)), stroke=GREY, sw=1.6)
    d.t(ax2.xc(11) + 8, y0 + h - 24 * u + 12, "Din ordre, 24 i Uke 11", 15, 600, INK)
    d.t(ax2.xc(29.5), y0 + h - 8 * u - 10, "Kundene: 8", 16, 700, BLUE, "middle", 'stroke="#FFFFFF" stroke-width="4" paint-order="stroke"')
    d.t(ax2.xc(2.5), y0 + h - 4 * u - 8, "4", 18, 700, BLUE, "middle")
    d.t(ax2.xc(19) + 6, y0 + h - 13.5 * u, "Ordre inn: det eneste du så", 15, 600, INK2)
    xaxis(d, ax2, y0 + h + 18, [1, 5, 10, 15, 20, 25, 30, 36], None)
    d.para(x2, y0 + h + 44, "Øvelsen heter Beer Game. Nesten alle grupper svinger slik, også i år. Det du så, var Idas ordrer, ikke kundene. Struktur gir atferd, derfor spør vi hvorfor og ikke hvem.", w2, 15, 20, fill=INK)
    d.t(x2, y0 + h + 92, "P4, P6", 13, 400, INK3)

    # Steg 3: hele kjeden og ordrene som tall
    x3, w3 = 980, 1080
    sec_title(d, x3, y, 3, f"Hele kjeden i Uke {CHAIN_WEEK}: alle fire har restordre, og alt er på vei", w3)
    cf = chain_full(d, SEATS, x3, y + 22, w3, CHAIN_WEEK, u=1.15, ls=13, maxup=31, maxdn=54, demand=DEM, you="Grossist",
                    node_w=36, kunde_w=96, end_label="Produksjon")
    # matrise: ordre, Rolle × uke
    my = cf["bottom"] + 22
    lw = 112
    cw = (w3 - lw - 58) / 36
    rh = 24
    mx0 = x3 + lw
    d.t(x3, my + 4, "Ordre per uke", 14, 600, INK)
    for k in range(1, 37):
        sel = k == CHAIN_WEEK
        if sel or k in (1, 5, 10, 15, 20, 25, 30, 36):
            d.t(mx0 + (k - 0.5) * cw, my + 4, k, 12, 700 if sel else 400, INK if sel else INK3, "middle")
    yy = my + 12
    rows = [("Kundene", None)] + [(r, SEATS[r]) for r in ROLES_UP]
    onset = {}
    for lab, S in rows:
        d.t(x3, yy + 17, lab + (", du" if lab == "Grossist" else ""), 13, 600 if lab == "Grossist" else 400, INK)
        for k in range(1, 37):
            v = DEM[k - 1] if S is None else S.order(k)
            first = S is not None and v >= 10 and all(S.order(j) < 10 for j in range(1, k))
            if first:
                onset[lab] = k
            mcell(d, mx0 + (k - 1) * cw, yy, cw, rh, v, "flow", 11, bold=first, outline=first)
        if S is not None:
            d.t(x3 + w3, yy + 17, fx1(K["forsterkning"][lab]), 15, 700, INK, "end")
        yy += rh
    # valgt uke
    d.rect(mx0 + (CHAIN_WEEK - 1) * cw - 1, my + 12 - 2, cw + 2, rh * 5 + 4, "none", INK, 1.2, extra='stroke-dasharray="2 2"')
    d.t(x3 + w3, my - 12, "Forsterkning", 12, 400, INK3, "end")
    d.para(x3, yy + 22, f"Kjeden over er kolonnen for Uke {CHAIN_WEEK}; dra i ukene for å spole. Innrammet: første ordre på 10 eller mer, Uke {onset['Detaljist']}, {onset['Grossist']}, {onset['Distributør']} og {onset['Fabrikk']}. Svingningene vokser oppstrøms og kommer senere. P5, P6.", w3, 14, 19, fill=INK2)

    # Rad 2
    yb = 668
    # Steg 4
    x4, w4 = 40, 720
    sec_title(d, x4, yb, 4, "Ditt øyeblikk: Uke 11. Du bestilte 24 med 16 på vei.", w4)
    m = syn(d, G, x4, yb + 16, 340, 11, 24, wmin=4, left=30, u=1.0, ls=13, hord=30, hnet=96, hcost=24, gap=10, x_left=x4,
            netlabel=False, head_left="Dette så du")
    tx = x4 + 372
    tw = w4 - 372
    d.t(tx, yb + 30, "Dette regnet du", 15, 600, INK)
    ny = d.para(tx, yb + 52, f"Posisjon {G.lager[10]} − {G.rest[10]} + {G.paavei(11)} = {G.posisjon(11)}. Med 24 ble den {G.posisjon(11) + 24}.", tw, 14, 19)
    d.t(tx, ny + 12, "Dette kostet det senere", 15, 600, INK)
    late = G.cum(36, "lager") - G.cum(24, "lager")
    ny = d.para(tx, ny + 32, f"{G.levering(15)} av de 24 kom i Uke 15. På vei toppet på {max(G.pv)} i Uke {G.pv.index(max(G.pv)) + 1}, og i Uke {G.lager.index(max(G.lager)) + 1} sto du med lager {max(G.lager)}. Lager i Uke 25 til 36 kostet {nf(late)} kr.", tw, 14, 19)
    d.t(tx, ny + 12, "Dette så de andre i Uke 11", 15, 600, INK)
    yy = ny + 32
    for r in ("Detaljist", "Distributør", "Fabrikk"):
        S = SEATS[r]
        d.t(tx, yy, f"{NAVN[r]}, {r}", 13, 400, INK)
        st = f"lager {S.lager[10]}" if S.net(11) >= 0 else f"restordre {S.rest[10]}"
        d.t(tx + tw, yy, f"{st}, ordre inn {S.inn(11)}", 13, 400, INK2, "end")
        d.line(tx, yy + 7, tx + tw, yy + 7, HAIR, 1)
        yy += 23
    yy += 10
    d.t(tx, yy, "Samme kjede, bare du teller alt på vei", 14, 600, INK)
    d.t(tx, yy + 18, "Simulert. Viser sammenhengen, ikke en fasit.", 13, 400, INK2)
    B = FX["bare_sara_teller_paa_vei"]
    rr = [("", "Spill 17", "Simulert"), ("Din ordre, Uke 11", "24", str(BARE.order(11))),
          ("Grossist, kr", nf(K["kost_per_rolle"]["Grossist"]), nf(B["kost_per_rolle"]["Grossist"])),
          ("Kjeden, kr", nf(K["kjedekost"]), nf(B["kjedekost"]))]
    yy += 42
    for i, row in enumerate(rr):
        bold = 600 if i == 0 else 400
        d.t(tx, yy, row[0], 13, bold, INK)
        d.t(tx + tw - 90, yy, row[1], 13, bold, INK, "end")
        d.t(tx + tw, yy, row[2], 13, bold, INK, "end")
        d.line(tx, yy + 7, tx + tw, yy + 7, HAIR, 1)
        yy += 22
    d.para(tx, yy + 14, "KI-generert, kan ta feil: «Du reagerte på restordren du så, ikke på køen over den. Mikkel fikk 24 fra deg uten å vite hvorfor.»", tw, 13, 17, fill=INK2)
    d.t(x4, m["axisbot"] + 24, "P2, P3, P7", 13, 400, INK3)

    # Kjedens regning
    xr, wr = 800, 560
    sec_title(d, xr, yb, " ", f"Kjedens regning: {nf(K['kjedekost'])} kr", wr)
    d.para(xr, yb + 26, "Målet var lavest kostnad for hele kjeden. Rødt er restordre, blått er lager, summert over fire Roller.", wr, 14, 19, fill=INK2)
    axc = Axis(xr + 42, 300, 1, 36)
    gy = yb + 70
    gh = 170
    refs = [([(k, chain_cum(k, SEATS_B)) for k in range(1, 37)], "Bare Sara"), ([(k, chain_cum(k, SEATS_A)) for k in range(1, 37)], "Alle fire")]
    lsum = lambda k: sum(SEATS[r].lagerkost(k) for r in ROLES)
    rsum = lambda k: sum(SEATS[r].restkost(k) for r in ROLES)
    Yc, a, b = cum_cost_area(d, axc, gy, gh, lsum, rsum, 1, 36, 2400, refs=refs)
    assert abs(a + b - K["kjedekost"]) < 1e-9
    for v in (0, 1000, 2000):
        d.line(axc.x0, Yc(v), axc.x1, Yc(v), HAIR, 1)
        d.t(axc.x0 - 6, Yc(v) + 4, nf(v, 0), 13, 400, INK3, "end")
    lx = axc.x1 + 8
    d.t(lx, Yc(a + b) + 4, f"Spill 17: {nf(a + b)}", 13, 700, INK)
    d.t(lx, Yc(FX["bare_sara_teller_paa_vei"]["kjedekost"]) + 4, f"Simulert, bare Sara: {nf(FX['bare_sara_teller_paa_vei']['kjedekost'])}", 13, 400, INK2)
    d.t(lx, Yc(FX["alle_teller_paa_vei"]["kjedekost"]) + 14, f"Simulert, alle fire: {nf(FX['alle_teller_paa_vei']['kjedekost'])}", 13, 400, INK2)
    d.rect(lx, Yc(500) - 10, 10, 10, REDF, RED, 1)
    d.t(lx + 16, Yc(500), f"Restordre {nf(b)}", 13, 600, INK)
    d.rect(lx, Yc(500) + 8, 10, 10, BLUEF, BLUE, 1)
    d.t(lx + 16, Yc(500) + 18, f"Lager {nf(a)}", 13, 600, INK)
    xaxis(d, axc, gy + gh + 17, [1, 12, 24, 36])
    # tabell per Rolle
    ty = gy + gh + 54
    cols = [(xr + 196, "Restordre"), (xr + 296, "Lager"), (xr + 396, "Sum"), (xr + wr, "Simulert, alle fire")]
    for cxx, h in cols:
        d.t(cxx, ty, h, 13, 600, INK2, "end")
    d.line(xr, ty + 7, xr + wr, ty + 7, HAIR2, 1)
    ty += 26
    for r in ROLES_UP + ["Kjeden"]:
        if r == "Kjeden":
            lv, rv, sv = a, b, FX["alle_teller_paa_vei"]["kjedekost"]
        else:
            S = SEATS[r]
            lv, rv, sv = S.cum(36, "lager"), S.cum(36, "rest"), FX["alle_teller_paa_vei"]["kost_per_rolle"][r]
        bold = 600 if r in ("Kjeden", "Grossist") else 400
        lab = f"{r}, {NAVN[r]}" if r != "Kjeden" else "Kjeden"
        d.t(xr, ty, lab, 14, bold, INK)
        bwid = 52 * rv / (rv + lv) if (rv + lv) else 0
        for (cxx, _), v in zip(cols, (rv, lv, lv + rv, sv)):
            d.t(cxx, ty, nf(v), 14, bold, INK if cxx != cols[3][0] else INK2, "end")
        d.line(xr, ty + 8, xr + wr, ty + 8, HAIR if r != "Fabrikk" else HAIR2, 1)
        ty += 25
    d.para(xr, ty + 10, f"Restordre er {round(100 * b / (a + b))} % av kjedens kostnad, fordi den koster dobbelt per enhet og varte lenge. Simulert er ingen fasit. P8.", wr, 13, 17, fill=INK2)

    # Steg 5
    x5, w5 = 1400, 300
    sec_title(d, x5, yb, 5, "Debrief-quiz", w5)
    ny = d.para(x5, yb + 32, f"Uke 11: lager {G.lager[10]}, restordre {G.rest[10]}, {G.paavei(11)} på vei. Hva er posisjonen før du bestiller?", w5, 15, 20, 600)
    opts = [(sg(-13), "wrong"), (str(G.posisjon(11)), "right"), ("16", None), ("29", None)]
    yy = ny + 6
    for lab, st in opts:
        col = RED if st == "wrong" else (INK if st == "right" else HAIR2)
        d.rect(x5, yy, w5, 40, PAPER, col, 1.4 if st else 1, 6)
        d.t(x5 + 14, yy + 26, lab, 16, 600, INK)
        if st == "wrong":
            d.t(x5 + w5 - 12, yy + 26, "Ditt svar, ikke riktig", 13, 600, RED, "end")
        if st == "right":
            d.t(x5 + w5 - 12, yy + 26, "Riktig", 13, 600, INK, "end")
        yy += 48
    ny = d.para(x5, yy + 10, "−13 er lager minus restordre. Da mangler køen over lageret: 0 − 13 + 16 = 3.", w5, 14, 19)
    d.para(x5, ny + 6, "Køen står i båndet over Uke 12 til 14 i din egen graf: 4, 4 og 8.", w5, 13, 17, fill=INK2)
    d.t(x5, ny + 60, "P3", 13, 400, INK3)

    # Delt skjerm
    xs, ws = 1740, 320
    sec_title(d, xs, yb, " ", "Delt skjerm: fire lagre", ws)
    fy = yb + 16
    d.rect(xs, fy, ws, 380, PAPER, HAIR2, 1.4, 8)
    axs = Axis(xs + 84, ws - 96, 1, 36)
    yr = fy + 14
    rh2 = 70
    for r in ["Fabrikk", "Distributør", "Grossist", "Detaljist"]:
        S = SEATS[r]
        Ys = yscale(yr, rh2, -70, 60)
        d.line(axs.x0, Ys(0), axs.x1, Ys(0), HAIR2, 1)
        net_area(d, axs, yr, rh2, S.net, 1, 36, -70, 60, lw=1.6)
        d.t(xs + 12, Ys(0) - 2, r, 13, 600, INK)
        d.t(xs + 12, Ys(0) + 14, f"{nf(S.kostsum(36), 0)} kr", 13, 400, INK2)
        yr += rh2 + 6
    demand_band(d, axs, yr, 20, 8)
    d.t(xs + 12, yr + 16, "Kundene", 13, 600, INK)
    xaxis(d, axs, yr + 38, [1, 12, 24, 36])
    d.para(xs, fy + 404, "Netto lager, samme skala i alle fire, med kostnaden ved navnet. Gruppa ser dette sammen; hver student har sitt eget steg på telefonen.", ws, 13, 17, fill=INK2)
    d.demodata(2060, 1188, "Demodata. Simulerte tall er merket Simulert.", 13, "end")
    d.save()


# ---------- 08 ----------
def status_txt(sp):
    return {"ferdig": "Ferdig", "pågår": "Pågår", "pauset": "Pause", "venter": "Venter"}[sp["status"]]


def class_medians():
    """Median netto lager per Rolle og uke, over spillene som har kommet så langt."""
    out = {}
    for r in ROLES:
        row = []
        for k in range(1, 37):
            vals = [sp["netto_lager"][r][k - 1] for sp in KL["spill"] if sp["uke"] >= k]
            row.append((int(round(median(vals))), len(vals)))
        out[r] = row
    return out


def class_week_cost():
    """Klassens kostnad per uke, summert over alle spill og Roller: (lager, restordre)."""
    res = []
    for k in range(1, 37):
        lk = rk = 0.0
        for sp in KL["spill"]:
            if sp["uke"] >= k:
                for r in ROLES:
                    v = sp["netto_lager"][r][k - 1]
                    if v > 0:
                        lk += v * LAGERKOST
                    else:
                        rk += -v * RESTKOST
        res.append((lk, rk))
    return res


def strip(d, x, y, sp, cw=4.3, lane=4, roles=("Fabrikk", "Distributør", "Grossist", "Detaljist")):
    for i, r in enumerate(roles):
        for k, v in enumerate(sp["netto_lager"][r]):
            fill, _ = net_fill(v)
            d.rect(x + k * cw, y + i * (lane + 0.5), cw + 0.2, lane, fill or "#EEF1F4")


def build_08():
    d = Doc("08-laerer-oversikt", 1600, 1000, f"{NAME}, Oversikt for Faglærer",
            "60 Klassespill på én 1440-skjerm: hva som venter nå, filtre, klassens median per Rolle og uke som tall, "
            "matriseveggen 60 spill × uker, kjedekostnad per spill mot fjoråret, klassens kostnad per uke og trakten.")
    spill = KL["spill"]
    X = 40
    d.t(X, 48, "Oversikt", 28, 700, INK)
    counts = {k: sum(1 for s in spill if s["status"] == k) for k in ("venter", "pauset", "pågår", "ferdig")}
    d.t(X + 128, 48, f"class-of-1994, IBE160 · 60 Klassespill: {counts['ferdig']} ferdig, {counts['pågår'] + counts['pauset']} pågår ({counts['pauset']} pauset), {counts['venter']} venter", 15, 400, INK2)
    d.t(1560, 48, "Spillfrist ti. 8. des", 15, 400, INK2, "end")

    near = sorted([s for s in spill if s["status"] == "venter"], key=lambda s: -s["ventet_timer"])
    top = near[0]
    d.rect(X, 66, 1520, 36, REDF, None, 1, 4)
    d.t(X + 12, 90, f"Spill {top['spill']} venter på {top['navn']} ({top['venter_paa']}) i {top['ventet_timer']} t. KI overtar om {24 - top['ventet_timer']} t.", 16, 600, INK)
    d.button(1300, 71, 120, 26, "Send Melding", size=13)
    d.button(1428, 71, 120, 26, "Pause spillet", primary=False, size=13)
    others = ", ".join(f"spill {s['spill']} på {s['navn']} {s['ventet_timer']} t" for s in near[1:])
    pa = [s for s in spill if s["status"] == "pauset"]
    d.t(X, 126, f"Venter også: {others}. Pause: spill {', '.join(str(s['spill']) for s in pa)}, fortsetter {pa[0]['fortsetter']}.", 14, 400, INK)

    # filtre
    yf = 160
    ki = sum(1 for s in spill if s["ki_seter"] > 0)
    labs = [("Alle", len(spill)), ("Venter", counts["venter"]), ("Pause", counts["pauset"]), ("Pågår", counts["pågår"]),
            ("Ferdig", counts["ferdig"]), ("Med KI-spiller", ki)]
    xx = X
    for i, (lab, c) in enumerate(labs):
        s = f"{lab} {c}"
        wd = text_w(s, 14) + 22
        d.rect(xx, yf - 17, wd, 26, INK if i == 0 else PAPER, None if i == 0 else HAIR2, 1, 4)
        d.t(xx + wd / 2, yf + 1, s, 14, 600, PAPER if i == 0 else INK, "middle")
        xx += wd + 8
    xx += 24
    d.t(xx, yf + 1, "Rolle", 14, 400, INK2)
    xx += 44
    for r in ROLES:
        sel = r == "Fabrikk"
        d.t(xx, yf + 1, r, 14, 700 if sel else 400, INK)
        if sel:
            d.line(xx, yf + 6, xx + text_w(r, 14), yf + 6, INK, 2)
        xx += text_w(r, 14) + 16

    # Venstre: median-matrise og vegg, felles kolonner
    cx0 = X + 96
    cw = 17.5
    colx = lambda k: cx0 + (k - 1) * cw
    ym = 222
    d.t(X, ym - 20, "Klassens kjede: median netto lager per Rolle og uke, over spillene som har kommet så langt", 14, 600, INK)
    for k in range(1, 37):
        if k in (1, 5, 10, 15, 20, 25, 30, 36):
            d.t(colx(k) + cw / 2, ym, k, 11, 400, INK3, "middle")
    MED = class_medians()
    yy = ym + 8
    for r in ["Fabrikk", "Distributør", "Grossist", "Detaljist"]:
        d.t(X, yy + 12, r, 12, 600 if r == "Fabrikk" else 400, INK)
        for k in range(1, 37):
            v, n = MED[r][k - 1]
            mcell(d, colx(k), yy, cw, 17, v, "net", 10, gap=0.6)
        yy += 17
    nlast = MED["Fabrikk"][35][1]
    d.t(colx(36) + cw + 8, ym + 8 + 12, "Spill med", 11, 400, INK3)
    d.t(colx(36) + cw + 8, ym + 8 + 26, "i uka:", 11, 400, INK3)
    d.t(colx(36) + cw + 8, ym + 8 + 46, f"Uke 1: 60", 11, 400, INK2)
    d.t(colx(36) + cw + 8, ym + 8 + 60, f"Uke 36: {nlast}", 11, 400, INK2)

    # Veggen
    yw = yy + 30
    hx = colx(36) + cw
    heads = [(X, "Spill", "start"), (X + 34, "Status", "start"), (cx0, "Fabrikk, netto lager per uke", "start"),
             (hx + 40, "Uke", "end"), (hx + 102, "Kjede, kr", "end"), (hx + 126, "KI", "end"), (hx + 140, "Venter på / neste", "start")]
    for x_, h, a in heads:
        d.t(x_, yw, h, 12, 600, INK2, a)
    d.line(X, yw + 5, 1080, yw + 5, HAIR2, 1)
    rank = {"venter": 0, "pauset": 1, "pågår": 2, "ferdig": 3}
    ordered = sorted(spill, key=lambda s: (rank[s["status"]], -(s.get("ventet_timer") or 0),
                                           -s["uke"] if s["status"] != "ferdig" else s["kjedekost"]))
    rowh = 10.3
    y = yw + 9
    cur = None
    grp = {"venter": "Venter", "pauset": "Pause", "pågår": "Pågår", "ferdig": "Ferdig, lavest kjedekost øverst"}
    for sp in ordered:
        if sp["status"] != cur:
            if cur is not None:
                y += 4
                d.line(X, y - 2, 1080, y - 2, HAIR2, 1)
            cur = sp["status"]
        isnear = sp["spill"] == top["spill"]
        if isnear:
            d.rect(X - 4, y - 0.5, 1044, rowh + 1, REDF, None, 1, 2)
        if sp["spill"] == 17:
            d.rect(X - 4, y - 0.5, 1044, rowh + 1, TINT, None, 1, 2)
        d.t(X, y + 9, sp["spill"], 11, 700 if isnear else 400, INK)
        d.t(X + 34, y + 9, status_txt(sp), 11, 700 if sp["status"] in ("venter", "pauset") else 400, INK if sp["status"] != "ferdig" else INK2)
        for k, v in enumerate(sp["netto_lager"]["Fabrikk"]):
            fill, _ = net_fill(v)
            d.rect(colx(k + 1) + 0.4, y + 0.4, cw - 0.8, rowh - 0.8, fill or "#EEF1F4")
        if sp["status"] != "ferdig":
            d.line(colx(sp["uke"]) + cw, y - 0.5, colx(sp["uke"]) + cw, y + rowh + 0.5, INK, 1.4)
        d.t(hx + 40, y + 9, sp["uke"], 11, 400, INK, "end")
        d.t(hx + 102, y + 9, nf(sp["kjedekost"], 0), 11, 400, INK, "end")
        d.t(hx + 126, y + 9, sp["ki_seter"] or "", 11, 400, INK, "end")
        if sp["status"] == "venter":
            d.t(hx + 140, y + 9, f"{sp['navn']}, {sp['venter_paa']}, {sp['ventet_timer']} t", 11, 700 if isnear else 400, INK)
            d.t(1080, y + 9, "Melding", 11, 600, BLUE, "end", 'text-decoration="underline"')
        elif sp["status"] == "pauset":
            d.t(hx + 140, y + 9, f"Fortsetter {sp['fortsetter']}", 11, 400, INK2)
        elif sp["spill"] == 17:
            d.t(hx + 140, y + 9, "Sara, Grossist (eksemplet)", 11, 400, INK2)
        y += rowh
    d.t(X, y + 16, "Spillene står sortert: venter, pause, pågår, ferdig (lavest kjedekost øverst). Svart strek: der spillet står nå. Vis som tabell gir alle tallene.", 12, 400, INK2)

    # Høyre kolonne
    rx = 1130
    rw = 430
    d.line(rx - 24, 146, rx - 24, 990, HAIR, 1)
    d.t(rx, 206, "Kjedekostnad per spill", 16, 600, INK)
    d.t(rx, 226, "Fylt: ferdig. Ring: pågår, foreløpig kostnad. Bare Faglærer ser dette.", 12, 400, INK2)
    sx0, sx1 = rx + 4, rx + rw - 10
    smax = 4000
    sxx = lambda v: sx0 + v / smax * (sx1 - sx0)
    base = 362
    F = KL["ferdige"]["kjedekost"]
    FJ = KL["fjoraaret"]
    d.rect(sxx(F["q1"]), 246, sxx(F["q3"]) - sxx(F["q1"]), base - 246 + 4, TINT)
    d.line(sxx(F["median"]), 240, sxx(F["median"]), base + 4, INK, 1.4)
    d.t(sxx(F["median"]) - 4, 252, f"Median {nf(F['median'], 0)}", 12, 600, INK, "end")
    d.line(sxx(FJ["median_kjedekost"]), 240, sxx(FJ["median_kjedekost"]), base + 4, INK2, 1, dash="3 3")
    d.t(sxx(FJ["median_kjedekost"]) + 4, 252, f"Fjoråret {nf(FJ['median_kjedekost'], 0)}", 12, 400, INK2)
    bins = {}
    for sp in sorted(spill, key=lambda s: s["kjedekost"]):
        bkey = int(sp["kjedekost"] // 100)
        n = bins.get(bkey, 0)
        bins[bkey] = n + 1
        cxp = sxx(bkey * 100 + 50)
        cyp = base - 4 - n * 9
        if sp["status"] == "ferdig":
            d.circle(cxp, cyp, 3.6, INK)
        else:
            d.circle(cxp, cyp, 3.2, PAPER, INK, 1.2)
    d.line(sx0, base + 4, sx1, base + 4, HAIR2, 1)
    for v in (0, 1000, 2000, 3000, 4000):
        d.t(sxx(v), base + 20, nf(v, 0), 12, 400, INK3, "middle")
    d.t(rx, base + 42, f"Midtre halvdel av ferdige spill: {nf(F['q1'], 0)} til {nf(F['q3'], 0)} kr. Fjoråret: {FJ['klasse']}, {FJ['spill']} spill.", 12, 400, INK2)
    d.t(rx, base + 58, f"Simulert referanse, alle teller på vei: {nf(FX['alle_teller_paa_vei']['kjedekost'], 0)} kr. Ikke et mål for studentene.", 12, 400, INK2)

    # Klassens kostnad per uke
    cy = 470
    WC = class_week_cost()
    tot_l = sum(a for a, _ in WC)
    tot_r = sum(b for _, b in WC)
    assert abs(tot_l + tot_r - sum(s["kjedekost"] for s in spill)) < 0.5 * len(spill)
    d.t(rx, cy, "Klassens kostnad per uke, alle spill", 16, 600, INK)
    d.t(rx, cy + 20, f"Så langt {nf(tot_l + tot_r, 0)} kr: restordre {nf(tot_r, 0)}, lager {nf(tot_l, 0)}.", 12, 400, INK2)
    axk = Axis(rx + 36, rw - 40, 1, 36)
    ky = cy + 34
    kh = 120
    kmax = max(a + b for a, b in WC)
    kscale = int(-(-kmax // 1000) * 1000)
    Yk = yscale(ky, kh, 0, kscale)
    for v in (0, kscale // 2, kscale):
        d.line(axk.x0, Yk(v), axk.x1, Yk(v), HAIR, 1)
        d.t(axk.x0 - 5, Yk(v) + 4, nf(v, 0), 11, 400, INK3, "end")
    bwk = axk.slot - 2
    for k, (a_, b_) in enumerate(WC, start=1):
        xk = axk.xc(k) - bwk / 2
        d.rect(xk, Yk(a_), bwk, Yk(0) - Yk(a_), BLUE)
        d.rect(xk, Yk(a_ + b_), bwk, Yk(a_) - Yk(a_ + b_), RED)
    xaxis(d, axk, ky + kh + 15, [1, 12, 24, 36], None, 11)
    pk = max(range(36), key=lambda i: WC[i][1]) + 1
    d.t(axk.xc(pk), Yk(WC[pk - 1][0] + WC[pk - 1][1]) - 5, f"Uke {pk}", 11, 600, INK, "middle")
    d.t(rx, ky + kh + 34, "Rødt: restordre × 1,00. Blått: lager × 0,50. Færre spill står i de siste ukene.", 12, 400, INK2)

    # Trakt
    ty = 700
    d.t(rx, ty, "Trakten", 16, 600, INK)
    tr = KL["traktA"]
    steps = [("Registrert", tr["registrert"]), ("Klassespill ferdig", tr["klassespill_ferdig"]), ("Debrief ferdig", tr["debrief_ferdig"]),
             ("Quiz bestått", tr["quiz_bestått"]), ("Replay ferdig", tr["replay_ferdig"]), ("Test levert", tr["test_levert"]),
             ("KI-vurdering klar", tr["ki_vurdering_klar"])]
    yy = ty + 24
    for lab, v in steps:
        d.t(rx, yy, lab, 13, 400, INK)
        d.t(rx + 160, yy, v, 13, 600, INK, "end")
        d.rect(rx + 172, yy - 10, (rw - 180) * v / steps[0][1], 11, ORD if v else HAIR)
        yy += 22
    M = KL["moenstre"]
    yy += 8
    d.t(rx, yy, "Mønstre i ordrene, ferdige spill", 13, 600, INK)
    yy += 18
    for k, v in M.items():
        d.t(rx, yy, k, 12, 400, INK2)
        d.t(rx + rw, yy, v, 12, 600, INK, "end")
        yy += 16
    d.button(rx, 950, 150, 34, "Vis i plenum", primary=False, size=14)
    d.button(rx + 162, 950, 150, 34, "Vis som tabell", primary=False, size=14)
    d.demodata(1560, 990, a="end")
    d.save()


if __name__ == "__main__":
    build_07()
    build_08()
