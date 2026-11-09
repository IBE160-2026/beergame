"""Kjerneflatene: 05 spill, 06 spilldynamikk, 10 pedagogikk."""
from e07parts import *

G = Seat()
BARE = Seat("Grossist", FX["bare_sara_teller_paa_vei"])
ALLE = Seat("Grossist", FX["alle_teller_paa_vei"])
K = FX["spill17"]
SEATS = {r: Seat(r) for r in ROLES}
DEM = K["serier"]["demand"]

# Bygget stopper hvis noe ikke stemmer med loggen
for _r, _s in SEATS.items():
    check_seat(_s, _r)
    assert abs(_s.akk(36) - K["kost_per_rolle"][_r]) < 1e-6, _r
assert abs(sum(SEATS[r].akk(36) for r in ROLES) - K["kjedekost"]) < 1e-6
for _src, _S in (("bare_sara_teller_paa_vei", BARE), ("alle_teller_paa_vei", ALLE)):
    assert abs(_S.akk(36) - FX[_src]["kost_per_rolle"]["Grossist"]) < 1e-6, _src
assert G.kostsum(11) == 68.0 and G.posisjon(11) == 3 and G.inn(11) == 8 and G.levering(11) == 4 and G.sendt(11) == 4
assert [G.order(k) for k in range(1, 11)] == [4, 4, 4, 4, 4, 4, 4, 4, 4, 8]

LAYER_TABS = ["Graf", "Tall", "Kostnad"]
PH_LEFT = 72  # felles venstremarg på telefonen, så ukene står på samme sted i alle tre lag


def ph_axis(wk, x=20, w=350):
    return Axis(x + PH_LEFT, w - PH_LEFT, wk - 6, wk + 4)


def flow_title(d, x, y, g, wk, size=13):
    lev, inn = g.levering(wk), g.inn(wk)
    first = ("Levering", lev, BASE)
    second = ("Ordre inn", inn, RED if inn > lev else BASE)
    if lev > inn:
        first, second = ("Ordre inn", inn, BASE), ("Levering", lev, BLUE)
    xx = x
    for lab, val, col in (first, second):
        d.rect(xx, y - 10, 10, 10, col)
        s = f"{lab} {val}"
        d.t(xx + 14, y, s, size, 600, INK)
        xx += 14 + text_w(s, size) + 14


# ---------- Lagene på telefonen ----------
def layer_graf(d, g, wk, typed, y, x=20, w=350, hn=94, proj=False):
    m = meteo(d, g, x, y, w, wk, typed, wmin=wk - 6, left=PH_LEFT, hn=hn, hf=34, gap=10, t_flow="", t_ord="", proj=proj, overduenote=False,
              t_net="Lager over null, restordre under")
    flow_title(d, x, m["yflow"] - 7, g, wk)
    d.t(x, m["yord"] - 7, "Din ordre", 13, 600, INK)
    return m


def tall_rows(g, wk, typed):
    def lev(k):
        if k <= wk:
            return g.levering(k)
        arr = dict(g.arrivals(wk, typed))
        q = arr.get(k)
        if q is None:
            return None
        return (q, "typed" if k == wk + 4 and typed is not None else "known")

    def ordre(k):
        if k < wk:
            return g.order(k)
        if k == wk and typed is not None:
            return (typed, "typed")
        return None

    return [
        ("Ordre inn", lambda k: g.inn(k) if k <= wk else None, "flow"),
        ("Levering", lev, "flow"),
        ("Sendt", lambda k: g.sendt(k) if k <= wk else None, "flow"),
        ("Lager", lambda k: g.net(k) if k <= wk else None, "net"),
        ("På vei", lambda k: g.paavei(k) if k <= wk else None, "flow"),
        ("Din ordre", ordre, "flow"),
    ]


def now_frame(d, ax, wk, y0, y1, label=True):
    d.rect(ax.xr(wk), y0, ax.xr(wk + 4) - ax.xr(wk), y1 - y0, TINT)
    d.line(ax.xr(wk), y0 - 6, ax.xr(wk), y1 + 2, INK, 1.4)
    if label:
        d.t(ax.xr(wk) + 5, y0 + 7, "Nå", 13, 700, INK)


def layer_tall(d, g, wk, typed, y, x=20, w=350, rh=25):
    ax = ph_axis(wk, x, w)
    d.t(x, y + 13, "Dine tall per uke", 13, 600, INK)
    y0 = y + 22
    rows = tall_rows(g, wk, typed)
    now_frame(d, ax, wk, y0, y0 + len(rows) * rh, label=False)
    d.t(ax.xr(wk) + 5, y + 13, "Nå", 13, 700, INK)
    yb = matrix(d, ax, y0, rows, range(wk - 6, wk + 5), rh=rh, lx=x)
    xaxis(d, ax, yb + 17, [k for k in range(wk - 6, wk + 5) if (k - wk) % 2 == 0], wk)
    yy = d.para(x, yb + 42, "Minus er restordre. Blå kant: bestilt, ikke garantert. Mørk kant: ordren du taster nå.", w, 13, 17, fill=INK2)
    return yy


def layer_kost(d, g, wk, y, x=20, w=350, hb=60, hc=64, cscale=None):
    ax = ph_axis(wk, x, w)
    tot = g.akk(wk)
    lk, rk = g.akk(wk, "lager"), g.akk(wk, "rest")
    d.t(x, y + 13, "Din kostnad", 13, 600, INK)
    d.t(x + w, y + 13, f"{nf(tot)} kr hittil", 13, 700, INK, "end")
    # denne uka
    y1 = y + 34
    d.t(x, y1, "Per uke", 13, 600, INK)
    now_frame(d, ax, wk, y1 + 8, y1 + 8 + hb, label=False)
    Yb = grid(d, ax, y1 + 8, hb, 0, 40, (0, 20, 40), 13, x1=ax.xr(wk + 4))
    cost_week_bars(d, ax, y1 + 8, hb, g, wk - 6, wk, 40, x1=ax.xr(wk + 4))
    uk = g.ukekost(wk)
    d.t(ax.xr(wk) + 5, Yb(uk) + 4, f"{nf(uk)} kr", 13, 700, INK)
    # samlet
    y2 = y1 + hb + 36
    d.t(x, y2, "Samlet", 13, 600, INK)
    cs = cscale or (100 * (int(tot // 100) + 1))
    now_frame(d, ax, wk, y2 + 8, y2 + 8 + hc, label=False)
    Yc = grid(d, ax, y2 + 8, hc, 0, cs, (0, cs // 2, cs), 13, x1=ax.xr(wk + 4))
    cost_cum_area(d, ax, y2 + 8, hc, g, wk - 6, wk, cs, x1=ax.xr(wk + 4))
    d.t(ax.xr(wk) + 5, Yc(tot) + 4, f"{nf(tot)}", 13, 700, INK)
    xaxis(d, ax, y2 + 8 + hc + 17, [k for k in range(wk - 6, wk + 5) if (k - wk) % 2 == 0], wk)
    yy = y2 + 8 + hc + 40
    d.rect(x, yy - 10, 10, 10, RED)
    d.t(x + 14, yy, f"Restordre {nf(rk)} kr", 13, 600, INK)
    d.rect(x + 176, yy - 10, 10, 10, BLUE)
    d.t(x + 190, yy, f"Lager {nf(lk)} kr", 13, 600, INK)
    yy += 20
    st = f"Denne uka: {g.rest[wk - 1]} restordre × 1,00 = {nf(g.rk(wk))} kr" if g.rest[wk - 1] else f"Denne uka: {g.lager[wk - 1]} på lager × 0,50 = {nf(g.lk(wk))} kr"
    d.t(x, yy, st, 13, 400, INK2)
    return yy


def game_header(d, wk, kost, role="Grossist", spill="Spill 17", x=20):
    d.t(x, 62, f"Uke {wk}", 30, 700, INK)
    d.t(x, 84, f"{role}, {spill}", 14, 400, INK2)
    d.t(370, 58, "Totalkostnad", 13, 400, INK2, "end")
    d.t(370, 80, f"{nf(kost)} kr", 18, 600, INK, "end")


def order_input(d, y, wk, typed):
    d.t(20, y + 18, f"Din ordre for Uke {wk}", 15, 600, INK)
    yb = y + 28
    d.rect(20, yb, 350, 54, PAPER, INK if typed is not None else HAIR2, 1.4, 6)
    d.line(78, yb, 78, yb + 54, HAIR2, 1)
    d.line(312, yb, 312, yb + 54, HAIR2, 1)
    d.line(40, yb + 27, 58, yb + 27, INK, 2)
    d.line(332, yb + 27, 350, yb + 27, INK, 2)
    d.line(341, yb + 18, 341, yb + 36, INK, 2)
    if typed is None:
        d.t(195, yb + 34, "Antall enheter", 17, 400, INK3, "middle")
    else:
        d.t(195, yb + 39, typed, 32, 700, INK, "middle")
    return yb + 54


def waiting_rows(d, y, rows, x=20, width=350, lh=28):
    for rolle, navn, status, done in rows:
        if done:
            d.circle(x + 6, y - 5, 5, INK)
        else:
            d.circle(x + 6, y - 5, 5, PAPER, INK, 1.5)
        d.t(x + 20, y, rolle, 14, 600, INK)
        d.t(x + 104, y, navn, 14, 400, INK)
        d.t(x + width, y, status, 14, 400, INK2, "end")
        y += lh
    return y


def seat_sara_klar():
    return [("Detaljist", "Ida", "har bestilt", True), ("Distributør", "Mikkel", "har bestilt", True),
            ("Fabrikk", "Jonas", "venter, 3 min", False), ("Grossist", "Sara", "har bestilt", True)]


def play_phone(d, g, wk, typed, layer="Graf", bottom="typing", band_typed="same", locked_note=True):
    """Telefonen i Klassespillet. Kjedebånd og ordrefelt står fast; Graf, Tall og Kostnad er lag."""
    game_header(d, wk, g.kostsum(wk))
    bt = typed if band_typed == "same" else band_typed
    yb = seat_band(d, g, wk, 20, 98, 350, bt, u=0.95, fixed=(30, 40))
    ty = yb + 8
    tabs(d, 20, ty, 350, LAYER_TABS, layer)
    cy = ty + 46
    if layer == "Graf":
        layer_graf(d, g, wk, bt, cy)
    elif layer == "Tall":
        layer_tall(d, g, wk, bt, cy)
    else:
        layer_kost(d, g, wk, cy)
    oy = 606
    d.line(20, oy - 6, 370, oy - 6, HAIR, 1)
    if bottom == "typing":
        yb = order_input(d, oy, wk, typed)
        d.button(20, yb + 12, 350, 50, f"Bekreft ordre på {typed}" if typed is not None else "Bekreft ordre", primary=typed is not None)
        d.t(20, yb + 86, "Kan ikke endres etter bekreftelse.", 13, 400, INK2)
        d.t(20, yb + 105, "Venter på: Jonas (3 min) og deg.", 13, 400, INK2)
        d.demodata(370, yb + 105, a="end")
    return oy


# ---------- 05 ----------
def build_05():
    d = Doc("05-spill", 1600, 1000, "Lag for lag, hovedskjerm i Uke 11",
            "Saras telefon i Uke 11 med 24 tastet inn. Kjedebåndet og ordrefeltet står fast, og Graf, Tall og Kostnad er lag hen blar mellom. Ved siden av: de to andre lagene, laptopen og forskjellen mellom Klassespill og Replay.")
    d.t(40, 46, "Uke 11. Kjedebåndet og ordrefeltet står fast. Graf, tall og kostnad er lag du blar mellom.", 26, 600, INK)

    phone(d, 40, 84, 1.0)
    play_phone(d, G, 11, 24, "Graf")
    d.end()
    d.t(235, 952, "Telefon, Klassespill: laget Graf er valgt.", 14, 400, INK2, "middle")

    # De to andre lagene, i full skala
    for i, (lay, cap) in enumerate((("Tall", "Laget Tall: samme uker som tabell, samme kolonner."),
                                    ("Kostnad", "Laget Kostnad: per uke og samlet, delt i to arter."))):
        fx, fy = 460, (84, 470)[i]
        ch = (320, 400)[i]
        d.rect(fx, fy, 390, ch, PAPER, HAIR2, 1.4, 18)
        d.g(f"translate({fx},{fy - 262})")
        tabs(d, 20, 282, 350, LAYER_TABS, lay)
        if lay == "Tall":
            layer_tall(d, G, 11, 24, 328)
        else:
            layer_kost(d, G, 11, 328)
        d.end()
        d.t(fx + 195, fy + ch + 22, cap, 14, 400, INK2, "middle")

    # Laptop: to lag samtidig, Graf over Tall på én tidsakse
    lx, ly, lw, lh = 890, 84, 670, 612
    d.rect(lx, ly, lw, lh, PAPER, HAIR2, 1.4, 10)
    d.t(lx + 24, ly + 40, "Uke 11", 26, 700, INK)
    d.t(lx + 106, ly + 40, "Grossist, Spill 17", 14, 400, INK2)
    d.t(lx + lw - 24, ly + 40, f"Totalkostnad {nf(G.kostsum(11))} kr", 15, 600, INK, "end")
    col = 430
    ybb = seat_band(d, G, 11, lx + 24, ly + 56, col - 10, 24, u=1.2)
    tabs(d, lx + 24, ybb + 8, col - 10, ["Graf og tall", "Kostnad"], "Graf og tall", h=30, size=13)
    gy = ybb + 50
    m = meteo(d, G, lx + 24, gy, col, 11, 24, wmin=5, left=PH_LEFT, hn=70, hf=28, gap=6, t_flow="", t_ord="", t_net="Lager over null, restordre under", axislabel=False)
    flow_title(d, lx + 24, m["yflow"] - 7, G, 11)
    d.t(lx + 24, m["yord"] - 7, "Din ordre", 13, 600, INK)
    ax = m["ax"]
    rows = tall_rows(G, 11, 24)
    ym = m["ybot"] + 6
    d.rect(ax.xr(11), ym, ax.xr(15) - ax.xr(11), len(rows) * 20, TINT)
    yb = matrix(d, ax, ym, rows, range(5, 16), rh=20, lx=lx + 24)
    d.line(ax.xr(11), ym, ax.xr(11), yb, INK, 1.4)
    xaxis(d, ax, yb + 16, range(5, 16), 11)
    rx = lx + 24 + col + 22
    rw = lx + lw - 24 - rx
    y = ly + 84
    d.t(rx, y, "Din kostnad", 14, 600, INK)
    y += 24
    for lab, v, c in (("Restordre", G.akk(11, "rest"), RED), ("Lager", G.akk(11, "lager"), BLUE)):
        d.rect(rx, y - 10, 10, 10, c)
        d.t(rx + 14, y, lab, 14, 400, INK)
        d.t(rx + rw, y, f"{nf(v)} kr", 14, 600, INK, "end")
        y += 22
    d.line(rx, y - 14, rx + rw, y - 14, HAIR2, 1)
    d.t(rx, y + 2, "Totalkostnad", 14, 600, INK)
    d.t(rx + rw, y + 2, f"{nf(G.akk(11))} kr", 14, 700, INK, "end")
    y += 50
    d.t(rx, y, "Din ordre for Uke 11", 14, 600, INK)
    d.rect(rx, y + 10, rw, 48, PAPER, INK, 1.4, 6)
    d.t(rx + rw / 2, y + 45, 24, 30, 700, INK, "middle")
    d.button(rx, y + 70, rw, 44, "Bekreft ordre på 24", size=14)
    d.para(rx, y + 140, "Kan ikke endres etter bekreftelse. Venter på: Jonas (3 min) og deg.", rw, 13, 17, fill=INK2)
    d.para(rx, y + 210, "På laptop er det plass til to lag samtidig. Grafen og tabellen deler kolonner, så hver uke har strek og tall.", rw, 13, 17, fill=INK2)
    d.demodata(lx + lw - 24, ly + lh - 14, a="end")

    # Hjelpegrad: samme kjedebånd på to trinn
    hy = 736
    d.t(lx, hy, "Hjelpegrad: samme Uke, to trinn i lagtrappa", 20, 600, INK)
    pw = 320
    d.t(lx, hy + 28, "Klassespill: du legger sammen selv", 14, 600, INK)
    seat_band(d, G, 11, lx, hy + 42, pw, 24, u=1.0)
    bx = lx + pw + 30
    d.t(bx, hy + 28, "Replay: laget Posisjon er åpnet", 14, 600, INK)
    yb2 = seat_band(d, G, 11, bx, hy + 42, pw, 24, u=1.0, posisjon=True)
    d.para(lx, yb2 - 4, "Tallene er de samme. Forskjellen er om summen står ferdig regnet.", pw, 13, 17, fill=INK2)
    d.save()


# ---------- 06 ----------
def build_06():
    d = Doc("06-spilldynamikk", 2100, 1200, "Lag for lag, en Uke i spillet",
            "Seks telefonruter: Uka åpner, beslutningen, bekreftet, Uka går videre, Jonas er borte, spillet slutter. Under: hva spilleren lærer, og hvordan Veiledede uker åpner ett lag om gangen.")
    s = 0.8
    pw = 390 * s
    gapx = (2100 - 80 - 6 * pw) / 5
    y0 = 196
    d.t(40, 50, "En Uke i Lag for lag: båndet flytter seg, laget du valgte blir stående.", 28, 600, INK)
    notes = [
        ("A  Uka åpner", "Levering og ordre inn er nye. Plassen fire uker fram i båndet står tom og stiplet."),
        ("B  Beslutningen: 24", "Sara taster 24, og tallet står straks bakerst i På vei: 16 + 24. Ingen fasit ved siden av."),
        ("C  Bekreftet", "Ordren er låst. Uka venter på Jonas, med Rolle, navn og hvor lenge. Laget Kostnad er valgt."),
        ("D  Uka går videre", "Båndet rykker én plass mot høyre, og 4 kommer inn. Under 2 sekunder, kan hoppes over."),
        ("E  Jonas er borte", "Pause, så bestiller en KI-spiller for Fabrikk, alltid merket. Jonas kan ta setet tilbake."),
        ("F  Spillet slutter", "Kjedens totalkostnad først, så per Rolle og per art. Nye lag åpnes i Debriefen."),
    ]
    for i, (h, n) in enumerate(notes):
        x = 40 + i * (pw + gapx)
        d.t(x, 96, h, 20, 600, INK)
        d.para(x, 122, n, pw, 15, 20, fill=INK2)

    def px(i):
        return 40 + i * (pw + gapx)

    # A
    phone(d, px(0), y0, s)
    play_phone(d, G, 11, None, "Graf", bottom="none")
    yb = order_input(d, 606, 11, None)
    d.t(20, yb + 26, f"Sist uke bestilte du {G.order(10)}.", 13, 400, INK2)
    d.button(20, yb + 40, 350, 50, "Bekreft ordre", primary=False)
    d.demodata(20, 820)
    d.end()

    # B
    phone(d, px(1), y0, s)
    play_phone(d, G, 11, 24, "Tall")
    d.end()

    # C
    phone(d, px(2), y0, s)
    play_phone(d, G, 11, None, "Kostnad", bottom="none", band_typed=24)
    y = 606
    d.t(20, y + 22, "Ordren på 24 er sendt. Venter på Jonas.", 15, 600, INK)
    waiting_rows(d, y + 56, seat_sara_klar())
    d.t(20, y + 186, "Du får beskjed når Uke 12 åpner.", 13, 400, INK2)
    d.demodata(20, 820)
    d.end()

    # D
    w = 12
    phone(d, px(3), y0, s)
    play_phone(d, G, w, None, "Kostnad", bottom="none")
    y = 606
    d.t(20, y + 22, "Uke 11 er ferdig regnet", 15, 600, INK)
    link(d, 370, y + 22, "Hopp over", 14, a="end")
    yy = y + 54
    for lab, v in (("Levering", G.levering(w)), ("Ordre inn", G.inn(w)), ("Sendt", G.sendt(w)),
                   ("Restordre", f"{G.rest[w - 2]} blir {G.rest[w - 1]}"), ("Kostnad denne uka", f"{nf(G.ukekost(w))} kr")):
        d.t(20, yy, lab, 14, 400, INK)
        d.t(370, yy, v, 14, 600, INK, "end")
        d.line(20, yy + 8, 370, yy + 8, HAIR, 1)
        yy += 26
    d.demodata(20, 820)
    d.end()

    # E
    w = 14
    phone(d, px(4), y0, s)
    play_phone(d, G, w, None, "Graf", bottom="none", band_typed=G.order(w))
    y = 606
    d.t(20, y + 22, "Pause: Jonas har ikke bestilt på 24 t.", 15, 600, INK)
    rows = [("Detaljist", "Ida", "har bestilt", True), ("Distributør", "Mikkel", "har bestilt", True),
            ("Fabrikk", "KI-spiller", "bestiller nå", False), ("Grossist", "Sara", "har bestilt", True)]
    yy = waiting_rows(d, y + 52, rows, lh=24)
    d.rect(20, yy - 6, 350, 72, TINT, None, 1, 6)
    d.t(32, yy + 16, "Jonas ser:", 13, 400, INK2)
    d.t(32, yy + 36, "KI-spiller bestiller for deg.", 14, 600, INK)
    d.button(236, yy + 8, 124, 44, "Ta tilbake setet", primary=False, size=13)
    d.end()

    # F
    phone(d, px(5), y0, s)
    d.t(20, 62, "Spillet er ferdig", 30, 700, INK)
    d.t(20, 84, "Grossist, Spill 17", 14, 400, INK2)
    d.t(20, 128, "Kjedens totalkostnad", 15, 400, INK2)
    d.t(20, 168, f"{nf(K['kjedekost'])} kr", 40, 700, INK, extra='style="font-variant-numeric:lining-nums proportional-nums"')
    rest_all = sum(SEATS[r].akk(36, "rest") for r in ROLES)
    lag_all = sum(SEATS[r].akk(36, "lager") for r in ROLES)
    assert abs(rest_all + lag_all - K["kjedekost"]) < 1e-6
    d.t(20, 194, f"Restordre {nf(rest_all)} kr · Lager {nf(lag_all)} kr", 14, 400, INK)
    y = 236
    mx = max(K["kost_per_rolle"].values())
    sc = 350 / mx
    for r in ROLES:
        S = SEATS[r]
        v = S.akk(36)
        d.t(20, y, r + (" (deg)" if r == "Grossist" else ""), 14, 600 if r == "Grossist" else 400, INK)
        d.t(370, y, f"{nf(v)} kr", 14, 600, INK, "end")
        rr, ll = S.akk(36, "rest"), S.akk(36, "lager")
        d.rect(20, y + 7, rr * sc - 1, 9, RED)
        d.rect(20 + rr * sc + 1, y + 7, ll * sc - 1, 9, BLUE)
        y += 44
    d.t(20, y + 4, "Rødt er restordrekostnad, blått lagerkostnad.", 13, 400, INK2)
    y += 40
    d.t(20, y, "Åpnes i Debriefen", 15, 600, INK)
    tabs(d, 20, y + 12, 350, ["Hele kjeden", "Posisjon", "Simulert"], None, h=32, size=13)
    d.para(20, y + 70, "Kjeden med fire ledd, regnestykket for posisjon, og samme kjede regnet med en rolig regel.", 350, 13, 17, fill=INK2)
    d.button(20, 740, 350, 52, "Gå til Debrief")
    d.demodata(20, 820)
    d.end()

    # Under
    yt = y0 + 844 * s + 54
    d.t(40, yt, "Hva spilleren lærer av kjeden, grafen og kostnaden uke for uke", 24, 600, INK)
    tekst = [
        "Kjedebåndet er det samme hver Uke. Ordren du taster, legger seg bakerst i På vei og rykker én plass per Uke. Du ser at det som kommer nå, er det du bestilte for fire uker siden.",
        "Båndet viser bare tall du kan se fra din plass. Summen av det som er på vei står der, men posisjonen må du regne selv. Den regningen er det Debriefen tar opp.",
        "Laget Kostnad viser at restordre koster dobbelt så mye per enhet som lager, og at summen vokser hver Uke med restordre. Kjedens kostnad ser du først når spillet er ferdig.",
        "Laget du velger, blir stående til du bytter. Den som vil ha tall, får tall. Den som vil ha strek, får strek. Kolonnene står på samme sted i alle tre.",
    ]
    colw = (2100 - 80 - 3 * 40) / 4
    for i, tx in enumerate(tekst):
        d.para(40 + i * (colw + 40), yt + 36, tx, colw, 16, 22, fill=INK)
    # Veiledede uker: ett lag om gangen
    ys = yt + 166
    d.t(40, ys, "Veiledede uker 1–4: ett nytt lag per Uke, med én setning første gang det vises.", 17, 600, INK)
    steps = [(1, [], "Uke 1: bare kjedebåndet og ordrefeltet. «Det du bestiller, kommer om lag 4 uker senere.»"),
             (2, ["Graf"], "Uke 2: + Graf. «Blått er lager, rødt er restordre. Streken er nå.»"),
             (3, ["Graf", "Tall"], "Uke 3: + Tall. «Samme uker som tabell.»"),
             (4, ["Graf", "Tall", "Kostnad"], "Uke 4: + Kostnad. «Restordre 1,00 og lager 0,50 per enhet per uke.»")]
    cw = (2100 - 80 - 3 * 40) / 4
    for i, (wk, labs, txt) in enumerate(steps):
        xx = 40 + i * (cw + 40)
        if labs:
            tabs(d, xx, ys + 16, 300 * len(labs) / 3, labs, labs[-1], h=30, size=13)
        else:
            d.rect(xx, ys + 16, 300, 30, PAPER, HAIR2, 1, 5, 'stroke-dasharray="3 3"')
            d.t(xx + 150, ys + 36, "Ingen lag ennå", 13, 400, INK3, "middle")
        d.para(xx, ys + 70, txt, cw, 14, 19, fill=INK2)
    d.save()


# ---------- 10 ----------
def build_10():
    d = Doc("10-pedagogikk", 2000, 1400, "Lag for lag, grafgrammatikken over tid",
            "Saras kjedebånd, meteogram, tall og kostnad i Uke 5, 11, 18 og 29, merket med prinsipp. Under: lagtrappa for Hjelpegrad og sammenligningen med simulert referanse etter Debriefen.")
    d.t(40, 52, "Fire lag i fire Uker av Saras spill", 34, 700, INK)
    d.para(40, 84, "Hver rad er én Uke. Kjedebåndet viser hvor varene er, meteogrammet når de kom, tallene hva som skjedde, og kostnaden hva det kostet. Tidsaksen er felles i alle rader, så nå-streken vandrer mot høyre.", 1500, 16, 22, fill=INK2)
    cx = {"band": 40, "met": 440, "mat": 1150, "cost": 1440, "note": 1680}
    hy = 148
    for k, t in (("band", "Kjedebånd: ditt ledd"), ("met", "Meteogram, hele spillet så langt"), ("mat", "Tall, fem siste uker"), ("cost", "Kostnad, samlet"), ("note", "Prinsipp og innsikt for neste ordre")):
        d.t(cx[k], hy, t, 15, 600, INK)
    d.line(40, hy + 10, 1960, hy + 10, HAIR2, 1)
    rows = [
        (5, G.order(5), "P1 P2", [
            ("P2 Forsinkelse", "Alt er 4. Det du bestilte i Uke 1, kommer nå. Bevegelsen som kommer i Uke 7, er ikke synlig fra din plass."),
            ("P4 Ordrer er ikke etterspørsel", "Ordre inn er det Ida bestilte, ikke kundene."),
        ]),
        (11, 24, "P1 P3", [
            ("P3 Det som er på vei", f"I båndet: {G.paavei(11)} på vei. Posisjon {G.lager[10]} − {G.rest[10]} + {G.paavei(11)} = {G.posisjon(11)}. Med 24 blir den {G.posisjon(11) + 24}."),
            ("P1 Opphopning", f"Rød celle i Lager: {sg(G.net(10))} + {G.levering(11)} − {G.inn(11)} = {sg(G.net(11))}. Tallraden og grafen er samme regnestykke."),
            ("Til neste ordre", f"Det ble {sg(G.net(15))} i Uke 15, ikke {sg(G.projection(11, 24)[-1][1])}: {G.levering(15)} av 24 kom."),
        ]),
        (18, G.order(18), "P3 P7", [
            ("P3 og P2 igjen", f"{G.paavei(18)} på vei, og {G.overdue(18)} av dem uten dato. Båndet viser dem som forsinket."),
            ("P7 Overreaksjon forsterker", "En ny ordre kommer ikke raskere enn de gamle. Den legger seg bakerst i båndet."),
            ("P8 Restordre koster dobbelt", f"Uke 18 kostet {nf(G.ukekost(18))} kr: {G.rest[17]} i restordre × 1,00."),
        ]),
        (29, G.order(29), "P1 P8", [
            ("P1 Samme regning, motsatt fortegn", "Det som var på vei, kom nesten samtidig. Lageret er summen av gamle ordrer."),
            ("P8 Begge arter teller", f"Lager {G.lager[28]} × 0,50 = {nf(G.lk(29))} kr per uke. Restordre {max(G.rest)} kostet {nf(max(G.rest) * 1.0)} kr per uke."),
        ]),
    ]
    y = hy + 22
    rh = 214
    for now, typed, pr, notes in rows:
        # A: kjedebånd
        d.t(cx["band"], y + 20, f"Uke {now}", 24, 700, INK)
        seat_band(d, G, now, cx["band"], y + 30, 360, typed, u=0.9, ls=13, vs=15)
        # B: meteogram
        m = meteo(d, G, cx["met"], y, 690, now, typed, wmin=1, wmax=36, hn=96, hf=32, gap=6, titles=False, left=34, xstep=5,
                  proj=False, actual=True, nowlabel="Nå", overduenote=False, connector=True, ordlabel=False, netlabel=False)
        d.t(cx["met"] + 690, y + 14, pr, 13, 600, INK2, "end")
        # C: tall
        ax = Axis(cx["mat"] + 80, 190, now - 4, now)
        rws = [("Ordre inn", lambda k: G.inn(k), "flow"), ("Levering", lambda k: G.levering(k), "flow"),
               ("Lager", lambda k: G.net(k), "net"), ("På vei", lambda k: G.paavei(k), "flow"),
               ("Din ordre", lambda k: G.order(k) if k < now else (typed, "typed"), "flow")]
        yb = matrix(d, ax, y + 14, rws, range(now - 4, now + 1), rh=26, lx=cx["mat"])
        xaxis(d, ax, yb + 17, range(now - 4, now + 1), now)
        # D: kostnad samlet, hele spillet på samme skala
        axc = Axis(cx["cost"] + 34, 200, 1, 36)
        Yc = grid(d, axc, y + 14, 140, 0, 600, (0, 300, 600), 13)
        cost_cum_area(d, axc, y + 14, 140, G, 1, now, 600)
        tot = G.akk(now)
        d.circle(axc.xc(now), Yc(tot), 3.5, INK, PAPER, 1.5)
        right = now > 20
        d.t(axc.xc(now) + (-8 if right else 6), Yc(tot) - 8, f"{nf(tot)} kr", 13, 700, INK, "end" if right else "start")
        xaxis(d, axc, y + 14 + 140 + 16, [1, 12, 24, 36], None)
        d.t(cx["cost"], y + 194, f"Restordre {nf(G.akk(now, 'rest'))} kr · Lager {nf(G.akk(now, 'lager'))} kr", 13, 400, INK2)
        # E: notater
        ny = y + 14
        for head, body in notes:
            d.t(cx["note"], ny, head, 14, 600, INK)
            ny = d.para(cx["note"], ny + 18, body, 280, 13, 17, fill=INK2) + 6
        d.line(40, y + rh - 6, 1960, y + rh - 6, HAIR, 1)
        y += rh

    # Nederst venstre: lagtrappa
    yl = y + 20
    d.t(40, yl, "Hjelpegrad som lagtrappe", 22, 600, INK)
    d.para(40, yl + 24, "Fylt celle er åpent lag, mørkest der laget åpnes. Lagene som legger sammen for deg, åpnes først etter Debriefen.", 860, 14, 19, fill=INK2)
    layer_ladder(d, 40, yl + 50, 860, rh=25, ls=14, desc=False, label_w=230)

    # Nederst høyre: etter Debriefen
    rx = 960
    d.t(rx, yl, "Etter Debriefen: samme graf og samme kostnad, med simulert referanse", 22, 600, INK)
    d.t(rx, yl + 24, "Samme kjede og samme kunder, regnet med en rolig regel. Viser sammenhengen, ikke en fasit. Simulert.", 14, 400, INK2)
    gy = yl + 52
    gh = 128
    ax = Axis(rx + 34, 470, 1, 36)
    Y = grid(d, ax, gy, gh, -40, 30, (-40, -20, 0, 20))
    net_area(d, ax, gy, gh, G.net, 1, 36)
    d.path("M" + " L".join(f"{ax.xc(k):.1f} {Y(BARE.net(k)):.1f}" for k in range(1, 37)), stroke=INK, sw=1.6)
    d.t(ax.xc(15), Y(-37), "Spill 17", 13, 600, RED, "end")
    d.t(ax.xc(31), Y(-30), "Simulert: bare Sara", 13, 600, INK, "start")
    d.t(ax.xc(31), Y(-30) + 16, "teller på vei", 13, 600, INK, "start")
    xaxis(d, ax, gy + gh + 16, [1, 12, 24, 36])
    cx2 = rx + 540
    axc = Axis(cx2 + 34, 280, 1, 36)
    Yc = grid(d, axc, gy, gh, 0, 600, (0, 300, 600))
    cost_cum_area(d, axc, gy, gh, G, 1, 36, 600, refs=((BARE, "6 4"), (ALLE, "2 3")))
    d.t(axc.x1 + 6, Yc(G.akk(36)) + 4, f"{nf(G.akk(36))}", 13, 700, INK)
    d.t(axc.x1 + 6, Yc(BARE.akk(36)) + 4, f"{nf(BARE.akk(36))}", 13, 600, GREY)
    d.t(axc.x1 + 6, Yc(ALLE.akk(36)) + 16, f"{nf(ALLE.akk(36))}", 13, 600, GREY)
    xaxis(d, axc, gy + gh + 16, [1, 12, 24, 36])
    d.t(cx2, gy - 16, "Grossist, samlet kostnad i kr", 13, 600, INK)
    B, A = FX["bare_sara_teller_paa_vei"], FX["alle_teller_paa_vei"]
    ty = gy + gh + 44
    d.para(rx, ty, f"Heltrukken: Spill 17. Stiplet: simulert, bare Sara teller på vei ({nf(B['kost_per_rolle']['Grossist'])} kr). Prikket: simulert, alle fire teller på vei ({nf(A['kost_per_rolle']['Grossist'])} kr). Kjeden: {nf(K['kjedekost'])} mot {nf(B['kjedekost'])} og {nf(A['kjedekost'])} kr. Forsterkning, Fabrikk: {fx1(K['forsterkning']['Fabrikk'])} mot {fx1(B['forsterkning']['Fabrikk'])} og {fx1(A['forsterkning']['Fabrikk'])}.", 990, 14, 19, fill=INK)
    d.para(rx, ty + 42, "P7: Å telle det som er på vei er ikke nok alene. I simuleringen ga en regel som jaget siste ordre for hardt, Fabrikk høyere forsterkning (12×) enn spill 17. P5 og P6: formen består, for strukturen er den samme.", 990, 14, 19, fill=INK2)
    d.demodata(1960, 1390, "Demodata. Simulerte referanser er merket Simulert.", 13, "end")
    d.save()


if __name__ == "__main__":
    build_05()
    build_06()
    build_10()
