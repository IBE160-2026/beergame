"""07 debrief og 08 lærerens oversikt for 05 Klassebildet."""
from e05lib import *
from screens_core import G, BARE, ALLE, K

SEATS = {r: Seat(r) for r in ROLES}
DEM = FX["spill17"]["serier"]["demand"]
STATUS_TXT = {"ferdig": "Ferdig", "pågår": "Pågår", "pauset": "Pause", "venter": "Venter"}


def sec_title(d, x, y, n, title, width):
    """Stegnummeret bærer rekkefølgen i Debriefen."""
    d.line(x, y - 26, x + width, y - 26, INK, 1.2)
    d.t(x, y, str(n), 22, 700, INK)
    return d.para(x + 24, y, title, width - 24, 22, 27, 600, INK)


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


def scrubber(d, x, y, w, wk, n=36, label=None):
    """Ukeskrubber: spoler kjeden gjennom spillet."""
    d.line(x, y, x + w, y, HAIR2, 3)
    xx = x + (wk - 1) / (n - 1) * w
    d.line(x, y, xx, y, INK, 3)
    d.circle(xx, y, 7, PAPER, INK, 2)
    d.t(x, y + 22, "Uke 1", 12, 400, INK3)
    d.t(x + w, y + 22, f"Uke {n}", 12, 400, INK3, "end")
    d.t(xx, y - 12, label or f"Uke {wk}", 13, 700, INK, "middle")


def build_07():
    d = Doc("07-debrief", 2100, 1200, "Klassebildet, Gruppedebrief i fem steg",
            "Forklaring, avsløring av etterspørselen, hele kjeden med matrise Rolle × uke, ditt øyeblikk i Uke 11 med kjedens kostnad, og quiz. Delt skjerm med fire meteogrammer.")
    d.t(40, 44, "Debrief, Spill 17: fra «hadde jeg rett?» til «hvorfor skjedde det?»", 28, 600, INK)

    # Steg 1
    x, w = 40, 330
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
    x2, w2 = 410, 600
    sec_title(d, x2, y, 2, "Kundene bestilte 4, så 8. Etter det endret de seg aldri.", w2)
    ax2 = Axis(x2 + 28, w2 - 28, 1, 36)
    y0 = y + 52
    h = 330
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
    d.t(ax2.xc(29.5), y0 + h - 8 * u - 10, "Kundeetterspørsel: 8", 16, 700, BLUE, "middle", halo())
    d.t(ax2.xc(2.5), y0 + h - 4 * u - 8, "4", 18, 700, BLUE, "middle")
    d.t(ax2.xc(19) + 6, y0 + h - 13 * u, "Ordre inn: det eneste du så", 15, 600, INK2, extra=halo())
    xaxis(d, ax2, y0 + h + 18, [1, 5, 10, 15, 20, 25, 30, 36], None)
    d.para(x2, y0 + h + 44, "Øvelsen heter Beer Game. Nesten alle grupper svinger slik, også i år. Det du så, var Idas ordrer, ikke kundene. Struktur gir atferd, derfor spør vi hvorfor og ikke hvem.", w2, 15, 20, fill=INK)
    d.t(x2, y0 + h + 96, "P4, P6", 13, 400, INK3)

    # Steg 3: hele kjeden + matrise Rolle × uke
    x3, w3 = 1050, 1010
    sec_title(d, x3, y, 3, "Hele kjeden: svingningene vokser oppstrøms og kommer senere", w3)
    wk = 18
    nodes = {r: SEATS[r].net(wk) for r in ROLES}
    flows = {r: SEATS[r].order(wk) for r in ROLES}
    pv = {r: SEATS[r].paavei(wk) for r in ROLES}
    cost = {r: f"{nf(SEATS[r].kostsum(wk))} kr" for r in ROLES}
    c = chain_full(d, x3, y + 18, 640, nodes, f"{DEM[wk - 1]}", u=0.75, cap=65, ls=13, flows=flows, pv=pv, cost=cost)
    tx = x3 + 670
    d.t(tx, y + 40, f"Uke {wk}, alle fire ledd", 15, 600, INK)
    d.para(tx, y + 62, "Ordrene går mot venstre, varene mot høyre. Under hver boks: kostnad hittil. De åpne stolpene er det som er på vei inn.", 330, 14, 19, fill=INK2)
    scrubber(d, tx + 10, y + 168, 310, wk)
    d.t(tx, y + 214, "Spol, så vokser og krymper boksene.", 13, 400, INK3)
    # matrise
    ym = c["bottom"] + 66
    axm = Axis(x3 + 104, w3 - 104 - 64, 1, 36)
    d.t(x3, ym - 12, "Ordre per Uke. Ramme: første Uke med ordre på 10 eller mer.", 14, 600, INK)
    rows = [(r, SEATS[r].order, "flow") for r in CHAIN_ORDER] + [("Kundene", lambda k: DEM[k - 1], "flow")]
    ch = 22
    ye = matrix(d, axm, ym, rows, 1, 36, ch=ch, ls=11, label_x=x3, label_size=14)
    for i, r in enumerate(CHAIN_ORDER):
        f = first_onset(SEATS[r].ordre)
        d.rect(axm.xl(f) + 0.5, ym + i * ch + 0.5, axm.slot - 1, ch - 1, "none", RED, 2)
        d.t(axm.x1 + 64, ym + i * ch + ch / 2 + 6, fx1(K["forsterkning"][r]), 17, 700, INK, "end", 'style="font-variant-numeric:lining-nums proportional-nums"')
    d.t(axm.x1 + 64, ym - 8, "Forsterkning", 12, 400, INK2, "end")
    xaxis(d, axm, ye + 16, [1, 5, 10, 15, 20, 25, 30, 36], None, 12)
    ons = " → ".join(f"Uke {first_onset(SEATS[r].ordre)}" for r in reversed(CHAIN_ORDER))
    FP = KL["ferdige"]["forsterkning_per_rolle"]
    d.t(x3, ye + 42, f"Bølgen når 10 i {ons}. Klassen, median av 41 ferdige spill: " + " · ".join(fx1(FP[r]["median"]) for r in reversed(CHAIN_ORDER)) + ". P5, P6.", 14, 400, INK2)

    # Rad 2
    yb = 704
    x4, w4 = 40, 1100
    sec_title(d, x4, yb, 4, "Ditt øyeblikk: Uke 11. Du bestilte 24 med 16 på vei.", w4)
    mm = meteo(d, G, x4, yb + 18, 330, 11, 24, left=30, hn=150, hf=56, gap=16, t_flow="", t_ord="Din ordre", t_net="Dette så du", futnote=None)
    d.t(x4, mm["yflow"] - 7, f"Levering {G.levering(11)}, ordre inn {G.inn(11)}", 13, 600, INK)

    tx = x4 + 360
    tw = 310
    d.t(tx, yb + 32, "Dette regnet du", 15, 600, INK)
    ny = d.para(tx, yb + 54, f"Posisjon {G.lager[10]} − {G.rest[10]} + {G.paavei(11)} = {G.posisjon(11)}. Med 24 ble den {G.posisjon(11) + 24}.", tw, 15, 20)
    d.t(tx, ny + 12, "Dette kostet det senere", 15, 600, INK)
    late = G.kostsum(36) - G.kostsum(24)
    assert all(G.rest[k - 1] == 0 for k in range(25, 37))
    ny = d.para(tx, ny + 34, f"{G.levering(15)} av de 24 kom i Uke 15. På vei toppet på {max(G.pv)} i Uke {G.pv.index(max(G.pv)) + 1}, og i Uke {G.lager.index(max(G.lager)) + 1} sto du med lager {max(G.lager)}. Lager i Uke 25 til 36 kostet {nf(late)} kr.", tw, 15, 20)
    d.t(tx, ny + 12, "Dette så de andre i Uke 11", 15, 600, INK)
    yy = ny + 34
    for r in ("Detaljist", "Distributør", "Fabrikk"):
        S = SEATS[r]
        d.t(tx, yy, f"{NAVN[r]}, {r}", 14, 400, INK)
        st = f"lager {S.lager[10]}" if S.net(11) >= 0 else f"restordre {S.rest[10]}"
        d.t(tx + tw, yy, f"{st}, ordre inn {S.inn(11)}", 14, 400, INK2, "end")
        d.line(tx, yy + 7, tx + tw, yy + 7, HAIR, 1)
        yy += 24
    yy += 8
    d.para(tx, yy, "KI-generert, kan ta feil: «Du reagerte på restordren du så, ikke på posisjonen. Mikkel fikk 24 fra deg uten å vite hvorfor.»", tw, 14, 19, fill=INK2)

    # Kjedens kostnad
    rx = x4 + 700
    rw = 400
    d.t(rx, yb + 32, f"Kjedens kostnad: {nf(K['kjedekost'])} kr", 17, 700, INK)
    d.t(rx, yb + 54, "Målet var lavest kostnad for hele kjeden.", 14, 400, INK2)
    A = FX["alle_teller_paa_vei"]
    B = FX["bare_sara_teller_paa_vei"]
    sc = 720.0
    bx0 = rx + 104
    bw_ = rw - 104 - 76
    yy = yb + 86
    for r in ROLES:
        a, b = series_split(K, r)
        d.t(rx, yy + 11, r + (" (du)" if r == "Grossist" else ""), 14, 600 if r == "Grossist" else 400, INK)
        split_bar(d, bx0, yy, bw_, 16, a, b, sc)
        ref = A["kost_per_rolle"][r]
        xr = bx0 + ref / sc * bw_
        d.line(xr, yy - 4, xr, yy + 20, INK, 1.6)
        d.t(rx + rw, yy + 12, nf(K["kost_per_rolle"][r]), 14, 600, INK, "end")
        yy += 34
    tl = sum(series_split(K, r)[0] for r in ROLES)
    tr = sum(series_split(K, r)[1] for r in ROLES)
    d.t(rx, yy + 6, f"Rødt restordre {nf(tr)} kr, blått lager {nf(tl)} kr.", 13, 400, INK2)
    d.t(rx, yy + 24, "Svart strek: simulert, alle fire teller det som er på vei.", 13, 400, INK2)
    yy += 52
    rows = [("", "Spill 17", "Bare Sara", "Alle fire"),
            ("Kjeden, kr", nf(K["kjedekost"]), nf(B["kjedekost"]), nf(A["kjedekost"])),
            ("Grossist, kr", nf(K["kost_per_rolle"]["Grossist"]), nf(B["kost_per_rolle"]["Grossist"]), nf(A["kost_per_rolle"]["Grossist"])),
            ("Forsterkning, Fabrikk", fx1(K["forsterkning"]["Fabrikk"]), fx1(B["forsterkning"]["Fabrikk"]), fx1(A["forsterkning"]["Fabrikk"]))]
    cols = [rx + 220, rx + 310, rx + rw]
    for i, row in enumerate(rows):
        bold = 600 if i == 0 else 400
        d.t(rx, yy, row[0], 13, bold, INK)
        for cx, v in zip(cols, row[1:]):
            d.t(cx, yy, v, 13, bold, INK, "end")
        d.line(rx, yy + 6, rx + rw, yy + 6, HAIR, 1)
        yy += 22
    d.t(rx, yy + 8, "Simulert. Viser sammenhengen, ikke en fasit. P3, P7, P8.", 13, 400, INK3)

    # Steg 5
    x5, w5 = 1180, 400
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
    d.t(x5, ny + 8, "Det samme regnestykket står under kjedebåndet i Replay.", 14, 400, INK2)
    d.t(x5, ny + 34, "P3", 13, 400, INK3)

    # Delt skjerm
    xs, ws = 1620, 440
    sec_title(d, xs, yb, " ", "Delt skjerm: fire meteogrammer", ws)
    fy = yb + 18
    d.rect(xs, fy, ws, 372, PAPER, HAIR2, 1.4, 8)
    axs = Axis(xs + 92, ws - 106, 1, 36)
    yr = fy + 14
    rh2 = 66
    for r in CHAIN_ORDER:
        S = SEATS[r]
        Ys = yscale(yr, rh2, -70, 60)
        d.line(axs.x0, Ys(0), axs.x1, Ys(0), HAIR2, 1)
        net_area(d, axs, yr, rh2, S.net, 1, 36, -70, 60, lw=1.6)
        d.t(xs + 12, Ys(0) - 2, r, 14, 600, INK)
        d.t(xs + 12, Ys(0) + 15, NAVN[r], 13, 400, INK2)
        yr += rh2 + 6
    demand_band(d, axs, yr, 20, 8)
    d.t(xs + 12, yr + 16, "Kundene", 14, 600, INK)
    xaxis(d, axs, yr + 38, [1, 12, 24, 36])
    d.para(xs, fy + 396, "Netto lager, samme skala i alle fire. Gruppa ser dette sammen, mens hver student ser sitt eget steg på telefonen.", ws, 14, 19, fill=INK2)
    d.demodata(2060, 1188, "Demodata. Simulerte tall er merket Simulert. Klassetall: 41 ferdige spill.", 13, "end")
    d.save()


# ---------- 08 ----------
def sorted_games():
    rank = {"venter": 0, "pauset": 1, "pågår": 2, "ferdig": 3}
    return sorted(SPILL, key=lambda s: (rank[s["status"]], -(s.get("ventet_timer") or 0),
                                        -s["uke"] if s["status"] in ("pågår", "pauset") else s["kjedekost"]))


def class_cost_strip(d, ax, y, h, games, label=True, ls=13):
    vals = [class_week_cost(w, games) for w in range(1, 37)]
    mx = max(a + b for a, b in vals)
    scale = 5000
    assert mx <= scale
    cost_bars(d, ax, y, h, lambda k: vals[k - 1], 1, 36, scale)
    pk = max(range(1, 37), key=lambda k: sum(vals[k - 1]))
    if label:
        d.t(ax.xc(pk), y + h - sum(vals[pk - 1]) * h / scale - 5, f"{nf(sum(vals[pk - 1]), 0)} kr i Uke {pk}", ls - 1, 600, INK, "middle", halo())
    return vals


def build_08():
    d = Doc("08-laerer-oversikt", 1600, 1000, "Klassebildet, Oversikt for Faglærer",
            "60 Klassespill på én skjerm som matrisevegg: netto lager for Fabrikk per Uke, klassens median og kostnad per uke på samme akse, kjedekostnad per spill mot fjorårets median, klassens kjede med fire ledd, kostnad per Rolle og trakten.")
    fx0, fy0, fw, fh = 16, 14, 1568, 972
    d.rect(fx0, fy0, fw, fh, PAPER, HAIR2, 1.2, 8)
    X = 40
    XR = fx0 + fw - 24
    counts = {k: sum(1 for s in SPILL if s["status"] == k) for k in ("venter", "pauset", "pågår", "ferdig")}
    d.t(X, 50, "Oversikt", 24, 700, INK)
    d.t(X + 104, 50, f"class-of-1994, IBE160. {len(SPILL)} Klassespill: {counts['ferdig']} ferdig, {counts['pågår'] + counts['pauset']} pågår (herav {counts['pauset']} pauset), {counts['venter']} venter", 15, 400, INK2)
    d.button(XR - 130, 30, 130, 30, "Vis i plenum", primary=False, size=14)
    d.button(XR - 270, 30, 130, 30, "Send Melding", size=14)
    d.t(XR - 284, 50, "Spillfrist ti. 8. des", 14, 400, INK2, "end")

    # Hva skjer nå
    near = sorted([s for s in SPILL if s["status"] == "venter"], key=lambda s: -s["ventet_timer"])
    top = near[0]
    y = 74
    d.rect(X, y, 1060, 30, REDF, None, 1, 4)
    d.t(X + 12, y + 20, f"Spill {top['spill']} venter på {top['navn']} ({top['venter_paa']}) i {top['ventet_timer']} t. KI overtar om {24 - top['ventet_timer']} t.", 15, 700, INK)
    d.button(X + 1060 - 236, y + 3, 120, 24, f"Melding til {top['navn']}", size=13)
    d.button(X + 1060 - 110, y + 3, 104, 24, "Pause spillet", primary=False, size=13)
    others = ", ".join(f"spill {s['spill']} {s['navn']} {s['ventet_timer']} t" for s in near[1:])
    pa = [s for s in SPILL if s["status"] == "pauset"]
    d.t(X + 12, y + 50, f"Venter også: {others}. Pause: " + ", ".join(f"spill {s['spill']}" for s in pa) + f", fortsetter {pa[0]['fortsetter']}.", 14, 400, INK)

    # Kontroller
    yc = 152
    def seg(x, label, opts, sel):
        d.t(x, yc + 5, label, 13, 400, INK2)
        xx = x + text_w(label, 13) + 8
        for o in opts:
            wd = text_w(o, 13) + 16
            on = o == sel
            d.rect(xx, yc - 12, wd, 24, INK if on else PAPER, None if on else HAIR2, 1, 4)
            d.t(xx + wd / 2, yc + 5, o, 13, 600, PAPER if on else INK, "middle")
            xx += wd + 4
        return xx + 14
    xx = seg(X, "Rolle", ["Fabrikk", "Distributør", "Grossist", "Detaljist"], "Fabrikk")
    xx = seg(xx, "Vis", ["Netto lager", "Ordre"], "Netto lager")
    ki = sum(1 for s in SPILL if s["ki_seter"] > 0)
    xx = seg(xx, "Status", [f"Alle {len(SPILL)}", f"Venter {counts['venter']}", f"Pause {counts['pauset']}", f"Pågår {counts['pågår']}", f"Ferdig {counts['ferdig']}", f"Med KI {ki}"], f"Alle {len(SPILL)}")
    d.t(XR, yc + 5, "Vis som tabell", 13, 600, BLUE, "end", 'text-decoration="underline"')
    d.line(X, yc + 22, XR, yc + 22, HAIR, 1)

    # Matriseveggen
    mx0 = 118
    ax = Axis(mx0, 36 * 16, 1, 36)
    xu = ax.x1 + 26
    xb0, xbw = ax.x1 + 36, 150
    xkr = xb0 + xbw + 48
    xki = xkr + 22
    xv = xki + 10
    # klassens kostnad per uke (41 ferdige), samme akse
    yk = 196
    d.t(X, yk + 4, "Klassens kostnad", 13, 600, INK)
    d.t(X, yk + 20, "per uke, 41 ferdige", 12, 400, INK2)
    vals = class_cost_strip(d, ax, yk - 4, 42, FERDIGE)
    tot_l = sum(a for a, b in vals)
    tot_r = sum(b for a, b in vals)
    yax = yk + 52
    xaxis(d, ax, yax, [1, 5, 10, 15, 20, 25, 30, 36], None, 12)
    # median-raden
    ymed = yax + 6
    d.t(X, ymed + 12, "Median", 12, 700, INK)
    d.t(X, ymed + 26, "41 ferdige", 11, 400, INK2)
    matrix(d, ax, ymed, [("", lambda k: class_median_net("Fabrikk", k), "net")], 1, 36, ch=20, ls=10, gap=1)
    d.rect(ax.x0, ymed, ax.w, 20, "none", INK, 1)
    # kolonnetitler
    hy = ymed + 44
    d.t(X, hy, "Spill", 12, 600, INK2)
    d.t(66, hy, "Status", 12, 600, INK2)
    d.t(mx0, hy, "Netto lager, Fabrikk, Uke 1 til nå", 12, 600, INK2)
    d.t(xu, hy, "Uke", 12, 600, INK2, "end")
    d.t(xb0, hy, "Kjedekostnad, kr", 12, 600, INK2)
    d.t(xki, hy, "KI", 12, 600, INK2, "end")
    d.t(xv, hy, "Venter på", 12, 600, INK2)
    games = sorted_games()
    groups = [("venter", "Venter"), ("pauset", "Pause"), ("pågår", "Pågår"), ("ferdig", "Ferdig, billigst øverst")]
    y = hy + 8
    SC = 3600.0
    med_now = KL["ferdige"]["kjedekost"]["median"]
    fj = KL["fjoraaret"]["median_kjedekost"]
    ybar_top = y
    for key, title in groups:
        gs = [s for s in games if s["status"] == key]
        rh = 7.0 if key == "ferdig" else 14
        y += 14
        d.t(X, y - 2, f"{title} {len(gs)}", 12, 700, INK)
        d.line(X, y + 1, xv + 120, y + 1, HAIR, 1)
        y += 3
        for s in gs:
            isnear = s["spill"] == top["spill"]
            if isnear:
                d.rect(X - 6, y - 1, xv + 128 - X, rh + 2, REDF, None, 1, 2)
            vals_ = s["netto_lager"]["Fabrikk"]
            for k, v in enumerate(vals_, 1):
                f, tc = net_cell(v)
                d.rect(ax.xl(k) + 0.5, y + 0.5, ax.slot - 1, rh - 1, f)
            if s["status"] != "ferdig":
                d.line(ax.xr(s["uke"]) + 1, y, ax.xr(s["uke"]) + 1, y + rh, INK, 1.4)
            lk, rk = game_cost_split(s)
            split_bar(d, xb0, y + (2 if rh > 10 else 1), xbw, rh - (4 if rh > 10 else 2), lk, rk, SC)
            if rh > 10:
                ty = y + rh - 3
                d.t(X, ty, s["spill"], 13, 600, INK)
                d.t(66, ty, STATUS_TXT[s["status"]], 13, 600 if key in ("venter", "pauset") else 400, INK)
                d.t(xu, ty, s["uke"], 13, 400, INK, "end")
                d.t(xkr, ty, nf(s["kjedekost"], 0), 13, 400, INK, "end")
                d.t(xki, ty, s["ki_seter"] or "", 13, 400, INK, "end")
                if key == "venter":
                    d.t(xv, ty, f"{s['navn']}, {s['venter_paa']}, {s['ventet_timer']} t", 13, 700 if isnear else 400, INK)
                elif key == "pauset":
                    d.t(xv, ty, f"Fortsetter {s['fortsetter']}", 13, 400, INK2)
            else:
                ty = y + rh - 0.8
                d.t(X + 24, ty, s["spill"], 8, 400, INK2, "end")
                if s["ki_seter"]:
                    d.t(xki, ty, s["ki_seter"], 8, 400, INK2, "end")
            y += rh
        y += 4
    ybar_bot = y - 4
    # referanselinjer i kostnadskolonnen
    for v, lab, dash, col in ((med_now, f"Median i år {nf(med_now, 0)}", None, INK), (fj, f"Fjoråret {nf(fj, 0)}", "3 3", INK2)):
        xx = xb0 + v / SC * xbw
        d.line(xx, ybar_top + 12, xx, ybar_bot, col, 1.2, dash=dash)
    d.t(xb0 + med_now / SC * xbw - 3, ybar_bot + 14, f"Median {nf(med_now, 0)}", 12, 600, INK, "end")
    d.t(xb0 + fj / SC * xbw + 3, ybar_bot + 14, f"Fjoråret {nf(fj, 0)}", 12, 400, INK2)
    # forklaring
    yl = ybar_bot + 14
    d.t(X, yl, "Restordre", 12, 400, INK2)
    lx_ = net_legend(d, X + 60, yl - 10, sw=18, labels=False)
    d.t(lx_ + 4, yl, "Lager. Strek: nå i spill som pågår.", 12, 400, INK2)
    d.t(xb0 - 40, yl, "Rødt: restordrekost. Blått: lagerkost.", 12, 400, INK2, "end")

    # Høyre: klassebildet
    RX = 1118
    RW = XR - RX
    d.line(RX - 18, 196, RX - 18, 970, HAIR, 1)
    # a) Klassens kjede
    y = 196
    d.t(RX, y, "Klassens kjede, median av 41 ferdige spill", 15, 700, INK)
    wk = 18
    nodes = {r: class_median_net(r, wk) for r in ROLES}
    flows = {r: class_median_order(r, wk) for r in ROLES}
    medcost = {r: median([s["kost_per_rolle"][r] for s in FERDIGE]) for r in ROLES}
    cost = {r: f"{nf(medcost[r], 0)} kr" for r in ROLES}
    c = chain_full(d, RX, y + 10, RW, nodes, "8", u=0.5, cap=50, ls=12, flows=flows, cost=cost, you=None,
                   stocklabels={r: sg(nodes[r]) for r in ROLES})
    scrubber(d, RX + 60, c["bottom"] + 52, RW - 120, wk)
    d.t(RX, c["bottom"] + 88, "Tall på linja: median ordre i Uka. Under boksen: median kostnad for Rollen, hele spillet.", 12, 400, INK2)
    # b) Kjedekostnad per spill
    y = c["bottom"] + 120
    d.t(RX, y, "Kjedekostnad per spill", 15, 700, INK)
    d.t(RX, y + 18, "Prikk: ferdig. Ring: pågår, foreløpig. Bare Faglærer ser dette.", 12, 400, INK2)
    axd0, axdw = RX + 4, RW - 8
    yb = y + 108
    xs = lambda v: axd0 + v / SC * axdw
    q1, q3 = KL["ferdige"]["kjedekost"]["q1"], KL["ferdige"]["kjedekost"]["q3"]
    d.rect(xs(q1), yb - 64, xs(q3) - xs(q1), 66, TINT)
    bins = {}
    for s in sorted(SPILL, key=lambda s: (s["status"] != "ferdig", s["kjedekost"])):
        bkey = int(s["kjedekost"] // 120)
        n = bins.get(bkey, 0)
        bins[bkey] = n + 1
        cx = axd0 + (bkey + 0.5) * 120 / SC * axdw
        cy = yb - 5 - n * 9
        if s["status"] == "ferdig":
            d.circle(cx, cy, 3.6, INK)
        else:
            d.circle(cx, cy, 3.2, PAPER, INK, 1.2)
    d.line(axd0, yb + 2, axd0 + axdw, yb + 2, HAIR2, 1)
    d.line(xs(med_now), yb - 70, xs(med_now), yb + 2, INK, 1.4)
    d.line(xs(fj), yb - 70, xs(fj), yb + 2, INK2, 1.2, dash="3 3")
    d.t(xs(med_now) - 4, yb - 72, f"Median {nf(med_now, 0)}", 12, 700, INK, "end")
    d.t(xs(fj) + 4, yb - 72, f"Fjoråret {nf(fj, 0)}", 12, 400, INK2)
    for v in (0, 1000, 2000, 3000):
        d.t(xs(v), yb + 16, nf(v, 0), 11, 400, INK3, "middle")
    d.t(RX, yb + 36, f"Midtre halvdel {nf(q1, 0)} til {nf(q3, 0)} kr. Fjoråret har bare medianen lagret ({KL['fjoraaret']['spill']} spill).", 12, 400, INK2)
    # c) Hva klassen betalte for
    y = yb + 60
    tot_all = sum(game_cost_split(s)[0] + game_cost_split(s)[1] for s in SPILL)
    d.t(RX, y, "Hva de 41 ferdige spillene betalte for", 15, 700, INK)
    split_r = {}
    for r in ROLES:
        a = sum(game_cost_split(s, [r])[0] for s in FERDIGE)
        b = sum(game_cost_split(s, [r])[1] for s in FERDIGE)
        split_r[r] = (a, b)
    assert abs(sum(a + b for a, b in split_r.values()) - (tot_l + tot_r)) < 1e-6
    mxr = max(a + b for a, b in split_r.values())
    yy = y + 22
    for r in ROLES:
        a, b = split_r[r]
        d.t(RX, yy + 10, r, 13, 400, INK)
        split_bar(d, RX + 86, yy, (RW - 86 - 70) * (a + b) / mxr, 12, a, b, a + b)
        d.t(XR, yy + 10, f"{nf(a + b, 0)} kr", 13, 400, INK, "end")
        yy += 18
    pr = tot_r / (tot_l + tot_r) * 100
    d.t(RX, yy + 10, f"Restordre {nf(tot_r, 0)} kr ({nf(pr, 0)} %), lager {nf(tot_l, 0)} kr. Hele klassen hittil: {nf(tot_all, 0)} kr.", 12, 400, INK2)
    # d) Trakt
    y = yy + 40
    d.t(RX, y, "Trakten", 15, 700, INK)
    tr = KL["traktA"]
    steps = [("Registrert", tr["registrert"]), ("Klassespill ferdig", tr["klassespill_ferdig"]), ("Debrief ferdig", tr["debrief_ferdig"]),
             ("Quiz bestått", tr["quiz_bestått"]), ("Replay ferdig", tr["replay_ferdig"]), ("Test levert", tr["test_levert"]), ("KI-vurdering klar", tr["ki_vurdering_klar"])]
    yy = y + 18
    for lab, v in steps:
        d.t(RX, yy + 9, lab, 12, 400, INK)
        d.rect(RX + 120, yy, (RW - 120 - 40) * v / steps[0][1], 10, ORD if v else HAIR)
        d.t(XR, yy + 9, v, 12, 600, INK, "end")
        yy += 14
    y = yy + 18
    d.t(RX, y, "Mønstre i ordrene, alle spill", 15, 700, INK)
    yy = y + 20
    for k, v in KL["moenstre"].items():
        d.t(RX, yy, k, 12, 400, INK)
        d.t(XR, yy, v, 12, 600, INK, "end")
        yy += 15
    d.demodata(XR - 300, 978, a="end")
    d.save()


if __name__ == "__main__":
    build_07()
    build_08()
