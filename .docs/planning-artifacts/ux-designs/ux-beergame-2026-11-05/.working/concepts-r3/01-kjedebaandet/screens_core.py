"""Kjerneflatene: 05 spill, 06 spilldynamikk, 10 pedagogikk."""
from e01lib import *

G = Seat()
BARE = Seat("Grossist", FX["bare_sara_teller_paa_vei"])
ALLE = Seat("Grossist", FX["alle_teller_paa_vei"])
K = FX["spill17"]
NAME = "Kjedebåndet"
PHONE_K = 2.5          # enheter til piksler i telefonens bånd, lik i alle telefonruter
ROWS_PHONE = ["net", "inn", "lev", "ordre", "pv", "kost", "sum"]


def flow_title(d, x, y, g, wk, ls=13):
    """Tittellinja i inn og ut-panelet bærer ukas tall. Lavest først, slik stolpen er stablet."""
    lev, inn = g.levering(wk), g.inn(wk)
    first = ("Levering", lev, BASE)
    second = ("Ordre inn", inn, RED if inn > lev else BASE)
    if lev > inn:
        first, second = ("Ordre inn", inn, BASE), ("Levering", lev, BLUE)
    xx = x
    for lab, val, col in (first, second):
        d.rect(xx, y - 10, 10, 10, col)
        s = f"{lab} {val}"
        d.t(xx + 14, y, s, ls, 600, INK)
        xx += 14 + text_w(s, ls) + 16


def chart_block(d, g, wk, typed, mode, x, y, w, left=30, hn=104, proj=False, ls=13, wmin=None, label="above", gx=None,
                rh=20):
    """Graf eller Tall på samme tidsakse. Returnerer bunn-y."""
    wmin = wmin if wmin is not None else wk - 7
    if mode == "graf":
        m = meteo(d, g, x, y, w, wk, typed, wmin=wmin, left=left, hn=hn, hf=40, gap=12, t_flow="", t_ord="", cost=True,
                  hc=34, cmax=40, t_cost="Kostnad per uke", proj=proj, ls=ls)
        flow_title(d, x, m["yflow"] - 7, g, wk, ls)
        d.t(x, m["yord"] - 7, "Din ordre", ls, 600, INK)
        return m["axisbot"], m
    ax = Axis(x + left, w - left, wmin, wk + 4)
    yy = matrix(d, g, ax, y, wk, typed, ROWS_PHONE, rh=rh, ls=ls, label=label, gx=gx if gx is not None else x + 4)
    wks = [k for k in range(wmin, wk + 5) if (k - wk) % 2 == 0]
    xaxis(d, ax, yy + 8, wks, wk, ls)
    return yy + 12, {"ax": ax}


def order_row(d, y, wk, typed, state="input"):
    d.line(20, y, 370, y, HAIR, 1)
    d.t(20, y + 26, f"Din ordre for Uke {wk}", 15, 600, INK)
    d.t(370, y + 26, f"kommer om lag Uke {wk + 4}", 13, 400, INK2, "end")
    yb = y + 38
    d.rect(20, yb, 178, 52, PAPER, INK if typed is not None else HAIR2, 1.4, 6)
    d.line(62, yb, 62, yb + 52, HAIR2, 1)
    d.line(156, yb, 156, yb + 52, HAIR2, 1)
    d.line(32, yb + 26, 50, yb + 26, INK, 2)
    d.line(168, yb + 26, 186, yb + 26, INK, 2)
    d.line(177, yb + 17, 177, yb + 35, INK, 2)
    if typed is None:
        d.t(109, yb + 33, "Antall", 16, 400, INK3, "middle")
        d.rect(208, yb, 162, 52, PAPER, HAIR2, 1, 6)
        d.t(289, yb + 31, "Bekreft ordre", 15, 600, INK3, "middle")
    else:
        d.t(109, yb + 37, typed, 30, 700, INK, "middle")
        d.button(208, yb, 162, 52, f"Bekreft ordre på {typed}", size=15)
    d.t(20, yb + 74, "Kan ikke endres etter at du har bekreftet.", 13, 400, INK2)
    return yb + 74


def phone_game(d, g, wk, typed, mode="graf", posisjon=False, proj=False, hn=104, bottom=True, hl=None):
    """Hele telefonskjermen i spillet, i telefonens egne koordinater. Returnerer y der bunnfeltet starter."""
    game_header(d, wk, g.kostsum(wk))
    b = band(d, g, 20, 102, 350, wk, typed, k=PHONE_K, posisjon=posisjon, hl=hl, segmin=74)
    yt = b["bottom"] + 12
    seg_toggle(d, 20, yt, ["Graf", "Tall"], 0 if mode == "graf" else 1, w=140, h=30, size=14)
    d.t(370, yt + 20, "Bare dine tall", 13, 400, INK2, "end")
    yend, m = chart_block(d, g, wk, typed, mode, 16, yt + 46, 358, hn=hn, proj=proj)
    return yend + 8, m


def waiting_rows(d, y, rows, x=20, width=350, lh=30):
    """rows: (rolle, navn, status, ferdig?)"""
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


def cost_split_bars(d, x, y, w, src, ls=14, rowh=44, you="Grossist", maxv=None):
    """Kostnad per Rolle, delt i lagerkost (blå) og restordrekost (rød). Tallene står ved stolpene."""
    seats = {r: Seat(r, src) for r in ROLES}
    mx = maxv or max(s.kostsum(s.n) for s in seats.values())
    for r in ROLES:
        S = seats[r]
        cl, cr = S.cum_lager(S.n), S.cum_rest(S.n)
        lab = r + (" (deg)" if r == you else "")
        d.t(x, y, lab, ls, 600 if r == you else 400, INK)
        d.t(x + w, y, f"{nf(cl + cr)} kr", ls, 600, INK, "end")
        bw = w * cl / mx
        d.rect(x, y + 8, bw, 8, BLUE)
        d.rect(x + bw + (2 if cr else 0), y + 8, max(w * cr / mx - 2, 0), 8, RED)
        y += rowh
    return y


# ---------- 05 ----------
def build_05():
    d = Doc("05-spill", 1600, 1000, f"{NAME}, hovedskjerm i Uke 11",
            "Saras telefon i Uke 11 med 24 tastet inn: kjedebåndet øverst, meteogrammet med fire felt under, og bryteren Graf / Tall. "
            "Ved siden av: samme skjerm med Tall valgt, laptop med graf og tall på samme akse, og hjelpegraden i Klassespill mot Replay.")
    d.t(40, 46, "Uke 11. Båndet viser hvor varene er nå. Grafen og tallene under viser hvordan det ble slik.", 26, 600, INK)

    # Telefon, Graf
    phone(d, 40, 84, 1.0)
    y, _ = phone_game(d, G, 11, 24, "graf")
    yb = order_row(d, y + 4, 11, 24)
    d.t(20, yb + 26, "Venter på: Jonas (3 min) og deg.", 13, 400, INK2)
    d.demodata(370, yb + 26, a="end")
    d.end()
    d.t(235, 956, "Telefon, Klassespill: båndet, grafen med fire felt, ordren.", 14, 400, INK2, "middle")

    # Telefon, Tall
    px = 460
    phone(d, px, 84, 1.0)
    y, _ = phone_game(d, G, 11, 24, "tall")
    yb = order_row(d, y + 4, 11, 24)
    d.t(20, yb + 26, "Venter på: Jonas (3 min) og deg.", 13, 400, INK2)
    d.demodata(370, yb + 26, a="end")
    d.end()
    d.t(655, 956, "Ett trykk på Tall: de samme ukene som tall, kolonne for kolonne.", 14, 400, INK2, "middle")

    # Laptop
    lx, ly, lw, lh = 880, 92, 680, 714
    d.t(lx, ly - 12, "Laptop i Labtime: graf og tall står samtidig, på samme kolonner.", 14, 400, INK2)
    d.rect(lx, ly, lw, lh, PAPER, HAIR2, 1.4, 10)
    d.t(lx + 24, ly + 40, "Uke 11", 26, 700, INK)
    d.t(lx + 106, ly + 40, "Grossist, Spill 17", 14, 400, INK2)
    d.t(lx + lw - 24, ly + 40, f"Totalkostnad {nf(G.kostsum(11))} kr", 15, 600, INK, "end")
    b = band(d, G, lx + 24, ly + 56, lw - 48, 11, 24, k=4.0)
    yc = b["bottom"] + 18
    d.line(lx + 24, yc - 8, lx + lw - 24, yc - 8, HAIR, 1)
    gw = 430
    left = 78
    m = meteo(d, G, lx + 24, yc, gw, 11, 24, wmin=4, left=left, hn=110, hf=40, gap=12, t_flow="", t_ord="", cost=True,
              hc=34, cmax=40, t_cost="Kostnad per uke", axislabel=False)
    flow_title(d, lx + 24, m["yflow"] - 7, G, 11)
    d.t(lx + 24, m["yord"] - 7, "Din ordre", 13, 600, INK)
    ax = m["ax"]
    ym = m["ybot"] + 12
    yy = matrix(d, G, ax, ym, 11, 24, ["net", "inn", "lev", "ordre", "pv", "kost", "sum"], rh=19, label="gutter",
                gx=lx + 24, sep=3)
    xaxis(d, ax, yy + 12, list(range(4, 16)), 11)
    d.t(lx + 24, yy + 12, "Uke", 13, 600, INK2)
    # høyre kolonne
    cx = lx + 24 + gw + 28
    cw = lx + lw - 24 - cx
    yy2 = yc + 4
    d.t(cx, yy2, "Din ordre for Uke 11", 14, 600, INK)
    d.rect(cx, yy2 + 12, cw, 52, PAPER, INK, 1.4, 6)
    d.t(cx + cw / 2, yy2 + 50, 24, 30, 700, INK, "middle")
    d.button(cx, yy2 + 76, cw, 46, "Bekreft ordre på 24", size=15)
    d.para(cx, yy2 + 146, "Kommer om lag Uke 15. Kan ikke endres etter at du har bekreftet.", cw, 13, 18, fill=INK2)
    yk = yy2 + 210
    d.t(cx, yk, "Kostnad så langt", 14, 600, INK)
    rows = [("Lager", G.cum_lager(11), BLUE), ("Restordre", G.cum_rest(11), RED)]
    yk += 24
    for lab, v, col in rows:
        d.rect(cx, yk - 10, 10, 10, col)
        d.t(cx + 16, yk, lab, 14, 400, INK)
        d.t(cx + cw, yk, f"{nf(v)} kr", 14, 600, INK, "end")
        yk += 24
    d.line(cx, yk - 16, cx + cw, yk - 16, HAIR2, 1)
    d.t(cx + 16, yk + 2, "Totalkostnad", 14, 600, INK)
    d.t(cx + cw, yk + 2, f"{nf(G.kostsum(11))} kr", 14, 700, INK, "end")
    d.para(cx, yk + 34, "Restordre koster 1,00 per enhet per uke, lager 0,50.", cw, 13, 18, fill=INK2)
    d.t(cx, ly + lh - 44, "Venter på: Jonas (3 min) og deg.", 13, 400, INK2)
    d.demodata(lx + lw - 24, ly + lh - 18, a="end")

    # Hjelpegrad
    hy = 826
    d.t(lx, hy, "Hjelpegrad: delene i Klassespillet, summen i Replay", 20, 600, INK)
    pw_ = 330
    d.t(lx, hy + 28, "Klassespill", 14, 600, INK)
    band(d, G, lx, hy + 62, pw_, 11, 24, k=2.2, names=False, sub=False, orders=False)
    d.para(lx, hy + 143, "Lager, restordre og hver leveranse på vei står på samme skala. Summen må Sara regne selv.",
           pw_, 14, 19, fill=INK2)
    bx = lx + pw_ + 20
    d.t(bx, hy + 28, "Replay, etter Debriefen", 14, 600, INK)
    band(d, G, bx, hy + 38, pw_, 11, 24, k=2.2, names=False, sub=False, orders=False, posisjon=True)
    d.para(bx, hy + 143, "Klammen legger delene sammen til Posisjon, og grafen får projeksjonen. Ingen fasit.",
           pw_, 14, 19, fill=INK2)
    d.save()


# ---------- 06 ----------
def build_06():
    d = Doc("06-spilldynamikk", 2100, 1200, f"{NAME}, en Uke i spillet",
            "Seks telefonruter: Uka åpner, beslutningen, bekreftet, Uka går videre, Jonas er borte, spillet slutter. "
            "Under: hva båndet, grafen og kostnaden lærer bort, og ordren på 24 som rykker gjennom båndet.")
    s = 0.8
    pw = 390 * s
    gapx = (2100 - 80 - 6 * pw) / 5
    y0 = 196
    d.t(40, 50, "En Uke i Kjedebåndet: ordren legger seg i båndet, rykker mot lageret og kommer fram om lag fire Uker senere.", 26, 600, INK)
    notes = [
        ("A  Uka åpner", "Levering og ordre inn er nye. Båndet viser 16 på vei i tre leveranser, og kostnadsfeltet har fått en ny stolpe."),
        ("B  Beslutningen: 24", "Sara taster 24. Tallet legger seg bakerst i båndet og fire Uker fram i grafen. Ingen fasit ved siden av."),
        ("C  Bekreftet", "Ordren er låst. Skjermen sier hvem Uka venter på, med Rolle, navn og hvor lenge."),
        ("D  Uka går videre", "Alt i båndet rykker ett steg mot høyre. Under 2 sekunder, og kan hoppes over."),
        ("E  Jonas er borte", "Pause, så bestiller KI-spiller for Fabrikk, alltid merket. Jonas kan ta setet tilbake."),
        ("F  Spillet slutter", "Kjedens totalkostnad først, så per Rolle og per kostnadsart. Spørsmålet går videre til Debrief."),
    ]
    for i, (h, n) in enumerate(notes):
        x = 40 + i * (pw + gapx)
        d.t(x, 98, h, 20, 600, INK)
        d.para(x, 124, n, pw, 15, 20, fill=INK2)

    def px(i):
        return 40 + i * (pw + gapx)

    # A
    phone(d, px(0), y0, s)
    y, _ = phone_game(d, G, 11, None)
    yb = order_row(d, y + 4, 11, None)
    d.t(20, yb + 26, f"Sist Uke bestilte du {G.order(10)}.", 13, 400, INK2)
    d.end()

    # B
    phone(d, px(1), y0, s)
    y, _ = phone_game(d, G, 11, 24)
    yb = order_row(d, y + 4, 11, 24)
    d.t(20, yb + 26, "Venter på: Jonas (3 min) og deg.", 13, 400, INK2)
    d.end()

    # C
    phone(d, px(2), y0, s)
    y, _ = phone_game(d, G, 11, 24)
    d.line(20, y + 4, 370, y + 4, HAIR, 1)
    d.t(20, y + 30, "Ordren på 24 er sendt. Venter på Jonas.", 15, 600, INK)
    waiting_rows(d, y + 60, seat_sara_klar(), lh=26)
    d.end()

    # D
    w = 12
    phone(d, px(3), y0, s)
    y, m = phone_game(d, G, w, None)
    ax = m["ax"]
    d.line(ax.xr(11), m["ynet"] - 2, ax.xr(11), m["ybot"], INK3, 1, dash="2 3")
    d.line(20, y + 4, 370, y + 4, HAIR, 1)
    d.t(20, y + 30, "Uke 11 er ferdig regnet", 15, 600, INK)
    d.t(370, y + 30, "Hopp over", 14, 600, BLUE, "end", 'text-decoration="underline"')
    rr = [("Restordre", f"{G.rest[w - 2]} blir {G.rest[w - 1]}"),
          ("Kostnad Uke 12", f"{nf(G.ukekost(w))} kr")]
    yy = y + 58
    for lab, v in rr:
        d.t(20, yy, lab, 14, 400, INK)
        d.t(370, yy, v, 14, 600, INK, "end")
        yy += 24
    d.end()

    # E
    w = 12
    phone(d, px(4), y0, s)
    y, _ = phone_game(d, G, w, G.order(w))
    d.line(20, y + 4, 370, y + 4, HAIR, 1)
    d.t(20, y + 28, "Pause: Jonas har ikke bestilt på 24 t.", 15, 600, INK)
    rows = [("Detaljist", "Ida", "har bestilt", True), ("Distributør", "Mikkel", "har bestilt", True),
            ("Fabrikk", "KI-spiller", "bestiller for Jonas", False)]
    yy = waiting_rows(d, y + 54, rows, lh=24)
    d.t(20, yy + 2, "Jonas kan ta setet tilbake når som helst.", 13, 400, INK2)
    d.end()

    # F
    phone(d, px(5), y0, s)
    d.t(20, 66, "Spillet er ferdig", 30, 700, INK)
    d.t(20, 88, "Grossist, Spill 17", 14, 400, INK2)
    d.t(20, 134, "Kjedens totalkostnad", 15, 400, INK2)
    d.t(20, 176, f"{nf(K['kjedekost'])} kr", 40, 700, INK, extra='style="font-variant-numeric:lining-nums proportional-nums"')
    seats = {r: Seat(r) for r in ROLES}
    cl = sum(S.cum_lager(36) for S in seats.values())
    cr = sum(S.cum_rest(36) for S in seats.values())
    assert abs(cl + cr - K["kjedekost"]) < 1e-9
    yk = 210
    tot = cl + cr
    d.rect(20, yk, 350 * cl / tot - 1, 12, BLUE)
    d.rect(20 + 350 * cl / tot + 1, yk, 350 * cr / tot - 1, 12, RED)
    d.t(20, yk + 34, f"Lager {nf(cl)} kr", 14, 600, INK)
    d.t(370, yk + 34, f"Restordre {nf(cr)} kr", 14, 600, INK, "end")
    d.line(20, yk + 54, 370, yk + 54, HAIR, 1)
    d.t(20, yk + 82, "Per Rolle", 15, 600, INK)
    cost_split_bars(d, 20, yk + 110, 350, K, ls=14, rowh=44)
    yq = yk + 110 + 4 * 44 + 10
    d.para(20, yq, "Blått er lagerkostnad, rødt er restordrekostnad. Hvorfor ble det slik? Det finner dere ut i Debriefen.",
           350, 14, 19, fill=INK2)
    d.button(20, 750, 350, 54, "Gå til Debrief")
    d.end()

    # Under: hva lærer spilleren
    yt = y0 + 844 * s + 54
    d.t(40, yt, "Hva spilleren lærer av å se båndet, grafen og kostnaden Uke for Uke", 24, 600, INK)
    tekst = [
        "Båndet er setets egen kjede: det som er på vei, står som bokser på samme skala som lager og restordre. Det som er bestilt, er like synlig som det som står på lager.",
        "Grafen under gir historien. Hver ordre står to ganger: nederst der den ble lagt, og fire Uker fram der den kommer. Bryteren Tall viser de samme ukene som tall.",
        "Kostnadsfeltet viser hva hver Uke koster: blå stolper for lager, røde for restordre. En restordre på 13 gir en stolpe dobbelt så høy som et lager på 13.",
        "I Klassespillet må Sara legge delene sammen selv. Etter Debriefen vet hen hvorfor det er verdt det, og i Replay legger båndet sammen til Posisjon.",
    ]
    colw = (2100 - 80 - 3 * 40) / 4
    for i, tx in enumerate(tekst):
        d.para(40 + i * (colw + 40), yt + 36, tx, colw, 16, 22, fill=INK)
    ys = yt + 140
    d.t(40, ys, "Ordren på 24 sett fra fem Uker: den rykker mot lageret, og i Uke 15 kommer bare 17. Resten venter hos leverandøren.", 17, 600, INK)
    pw2 = (2100 - 80 - 4 * 30) / 5
    for i, wk in enumerate(range(11, 16)):
        xx = 40 + i * (pw2 + 30)
        typed = 24 if wk == 11 else G.order(wk)
        band(d, G, xx, ys + 16, pw2, wk, typed, k=1.6, names=False, sub=False, orders=False, hl=15, segmin=64)
        cap = {11: "Uke 11: 24 bestilt", 12: "Uke 12: kommer om tre Uker", 13: "Uke 13: kommer om to Uker", 14: "Uke 14: kommer neste Uke",
               15: f"Uke 15: {G.levering(15)} kom, {G.overdue(15)} forsinket"}[wk]
        d.t(xx, ys + 104, cap, 14, 600 if wk in (11, 15) else 400, INK if wk in (11, 15) else INK2)
    d.demodata(2060, 1188, a="end")
    d.save()


# ---------- 10 ----------
def build_10():
    d = Doc("10-pedagogikk", 2000, 1400, f"{NAME}, grafgrammatikken over tid",
            "Saras kjedebånd, meteogram med kostnadsfelt og matrise i Uke 5, 11, 18 og 29 på én felles tidsakse, "
            "og sammenligningen av kostnaden med simulerte referanser slik den vises etter Debriefen.")
    d.t(40, 56, "Båndet, grafen og tallene i fire Uker av Saras spill", 36, 700, INK)
    d.para(40, 90, "Til venstre står kjeden slik den så ut fra Saras plass. Til høyre står de samme tallene over tid, først som graf og nederst som tabell. Alt deler én tidsakse, så hver Uke har både strek og tall.", 1460, 17, 23, fill=INK2)

    keyx = 1586
    keyw = 374
    d.t(keyx, 56, "Slik leses arket", 17, 600, INK)
    d.rect(keyx, 68, 22, 14, PAPER, BLUE, 1.2)
    d.t(keyx + 32, 80, "På vei, en boks per leveranse. Lager blått, restordre rødt.", 14, 400, INK2)
    d.path(f"M{keyx} 98 L{keyx + 22} 98", stroke=GREY, sw=2, dash="6 4")
    d.t(keyx + 32, 103, "Projeksjon. Bare i Replay, aldri i Klassespillet.", 14, 400, INK2)
    d.line(keyx, 120, keyx + 22, 120, INK, 1)
    d.t(keyx + 32, 125, "Det som faktisk skjedde. Bare på dette arket.", 14, 400, INK2)

    rows = [
        (5, G.order(5), [
            ("P2 Forsinkelse", "Alt er 4. Båndet har tre like leveranser på vei, og bevegelsen som kommer i Uke 7, er ikke synlig ennå."),
            ("P4 Ordrer er ikke etterspørsel", "Ordre inn er det Ida bestilte. Sara har ingen annen kilde."),
            ("Til neste ordre", "En rolig Uke betyr bare at ingenting har nådd deg ennå."),
        ]),
        (11, 24, [
            ("P3 Det som er på vei", f"Båndet viser 13 i restordre og {G.paavei(11)} på vei på samme skala. Posisjon {G.lager[10]} − {G.rest[10]} + {G.paavei(11)} = {G.posisjon(11)}."),
            ("P1 Lager er en opphopning", f"Rød del av stolpen er det netto lager faller: {G.inn(11)} inn minus {G.levering(11)} levert gir {sg(G.net(11) - G.net(10))}."),
            ("Til neste ordre", f"Det ble {sg(G.net(15))}, ikke {sg(G.projection(11, 24)[-1][1])}: {G.levering(15)} av 24 kom i Uke 15."),
        ]),
        (18, G.order(18), [
            ("P3 og P2 igjen", f"{G.paavei(18)} på vei, og {G.overdue(18)} av dem er stiplet: bestilt for over fire Uker siden, uten dato."),
            ("P7 Overreaksjon forsterker", "En ny ordre legger seg bakerst i båndet. Den kommer ikke raskere, og leverandøren får et større tall å svare på."),
            ("P8 Restordre koster dobbelt", f"Restordre {G.rest[17]} koster {nf(G.restkost(18))} kr denne Uka. Kostnadsstolpene er på sitt høyeste."),
        ]),
        (29, G.order(29), [
            ("P8 Begge koster", f"Lager {G.lager[28]} × 0,50 = {nf(G.lagerkost(29))} kr per Uke. Halvparten av restordren, men det varer."),
            ("P1 Samme regning, motsatt fortegn", "Det store båndet fra Uke 18 har kommet fram. Toppen i lageret er summen av gamle ordrer."),
            ("Til neste ordre", "Båndet er nesten tomt. Hvor mye du vil ha på vei, må du bestemme selv."),
        ]),
    ]
    y = 140
    x0, wplot = 460, 1090
    rh = 182
    bandw = 400
    left = 70
    for now, typed, notes in rows:
        d.t(40, y + 24, f"Uke {now}", 26, 700, INK)
        band(d, G, 40, y + 34, bandw, now, typed, k=1.9, names=False, segmin=60)
        m = meteo(d, G, x0, y + 4, wplot, now, typed, wmin=1, wmax=36, hn=64, hf=24, gap=6, titles=False, left=left,
                  xstep=4, proj=True, actual=True, nowlabel="Nå", overduenote=False, connector=True, ordlabel=False,
                  netlabel=False, cost=True, hc=26, cmax=40, costsum=False, costnum=False, axislabel=False, arrnums=False)
        ax = m["ax"]
        Y = m["Y"]
        for lab, yy_ in (("Inn og ut", m["yflow"] + 22), ("Ordre", m["yord"] + m["ho"] - 2), ("Kostnad", m["ycost"] + 24)):
            d.t(ax.x0 - 6, yy_, lab, 13, 400, INK2, "end")
        d.t(ax.xr(now) + 6, m["ycost"] + 24, f"Sum {nf(G.kostsum(now))} kr", 13, 600, INK)
        p = G.projection(now, typed)[-1][1]
        act = G.net(now + 4)
        ex = ax.xr(now + 4) + 8
        if now == 18:
            over = G.overdue(now)
            d.t(ex, Y(p + over) + 5, f"Planlagt {sg(p)} til {sg(p + over)}", 13, 600, INK2)
            d.t(ex, Y(act) + 4, f"Det ble {sg(act)}", 13, 600, INK)
        elif abs(Y(p) - Y(act)) < 16:
            d.t(ex, Y(p) - 2, f"Planlagt {sg(p)}", 13, 600, INK2)
            d.t(ex, Y(p) + 14, f"Det ble {sg(act)}", 13, 600, INK)
        else:
            d.t(ex, Y(p) + 5, f"Planlagt {sg(p)}", 13, 600, INK2)
            d.t(ex, Y(act) + 5, f"Det ble {sg(act)}", 13, 600, INK)
        ny = y + 10
        for head, body in notes:
            d.t(keyx, ny, head, 15, 600, INK)
            ny = d.para(keyx, ny + 18, body, keyw, 14, 18, fill=INK2) + 3
        d.line(40, y + rh - 6, 1960, y + rh - 6, HAIR, 1)
        y += rh

    # Matrisen på samme akse
    ym = y + 14
    d.t(40, ym + 4, "Hele loggen som tall", 22, 600, INK)
    d.para(40, ym + 30, "Samme kolonner som grafen over. De fire Ukene over er markert. Debriefen viser hele tabellen, Klassespillet bare fram til nå.", 300, 14, 19, fill=INK2)
    ax = Axis(x0 + left, wplot - left, 1, 36)
    xaxis(d, ax, ym + 2, [k for k in range(1, 37)], None, 12)
    for wk_ in (5, 11, 18, 29):
        d.rect(ax.xl(wk_) + 0.5, ym + 8, ax.slot - 1, 7 * 22 + 4, "none", INK, 1.2)
        d.t(ax.xc(wk_), ym + 2, wk_, 12, 700, INK, "middle")
    yy = matrix(d, G, ax, ym + 10, 36, G.order(36), ["net", "inn", "lev", "ordre", "pv", "kost", "sum"], rh=19, ls=12,
                label="gutter", gx=x0 - 90, future=False, sep=3, wmin=1)

    # Etter Debriefen: kostnaden mot simulert referanse
    yr = yy + 30
    d.line(40, yr - 16, 1960, yr - 16, HAIR2, 1)
    ny_ = d.para(40, yr + 10, "Etter Debriefen: kostnaden mot simulert referanse", 380, 22, 27, 600, INK)
    d.para(40, ny_ + 4, "Samme kjede, samme kunder. Simulert. Tallene viser en sammenheng, ingen fasit.", 380, 14, 19, fill=INK2)
    B, A = FX["bare_sara_teller_paa_vei"], FX["alle_teller_paa_vei"]
    tx = 40
    cols = [tx + 196, tx + 290, tx + 380]
    ty = ny_ + 64
    for c, h in zip(cols, ("Spill 17", "Bare Sara", "Alle fire")):
        d.t(c, ty, h, 13, 600, INK, "end")
    d.line(tx, ty + 7, cols[2], ty + 7, HAIR2, 1)
    rr = [("Grossist, lager", nf(G.cum_lager(36)), nf(BARE.cum_lager(36)), nf(ALLE.cum_lager(36))),
          ("Grossist, restordre", nf(G.cum_rest(36)), nf(BARE.cum_rest(36)), nf(ALLE.cum_rest(36))),
          ("Grossist, kr", nf(K["kost_per_rolle"]["Grossist"]), nf(B["kost_per_rolle"]["Grossist"]), nf(A["kost_per_rolle"]["Grossist"])),
          ("Kjeden, kr", nf(K["kjedekost"], 0), nf(B["kjedekost"], 0), nf(A["kjedekost"], 0)),
          ("Forsterkning, Fabrikk", fx1(K["forsterkning"]["Fabrikk"]), fx1(B["forsterkning"]["Fabrikk"]), fx1(A["forsterkning"]["Fabrikk"]))]
    ty += 26
    for row in rr:
        d.t(tx, ty, row[0], 13, 400, INK)
        for c, v in zip(cols, row[1:]):
            d.t(c, ty, v, 13, 400, INK, "end")
        d.line(tx, ty + 7, cols[2], ty + 7, HAIR, 1)
        ty += 23
    # akkumulert kostnad, samme tidsakse
    gy = yr + 8
    gh = 1380 - gy - 26
    Yc = yscale(gy, gh, 0, 600)
    for v in (0, 200, 400, 600):
        d.line(ax.x0, Yc(v), ax.x1, Yc(v), HAIR2 if v == 0 else HAIR, 1)
        d.t(ax.x0 - 5, Yc(v) + 4, nf(v, 0), 12, 400, INK3, "end")
    lo = [(ax.xc(k), Yc(G.cum_lager(k))) for k in range(1, 37)]
    hi = [(ax.xc(k), Yc(G.kostsum(k))) for k in range(1, 37)]
    base = Yc(0)
    d.path("M" + " L".join(f"{a:.1f} {b:.1f}" for a, b in lo) + f" L{lo[-1][0]:.1f} {base:.1f} L{lo[0][0]:.1f} {base:.1f} Z", BLUEF)
    d.path("M" + " L".join(f"{a:.1f} {b:.1f}" for a, b in hi) + " L" + " L".join(f"{a:.1f} {b:.1f}" for a, b in reversed(lo)) + " Z", REDF)
    d.path("M" + " L".join(f"{a:.1f} {b:.1f}" for a, b in hi), stroke=INK, sw=2)
    for S, col in ((BARE, INK2), (ALLE, GREY)):
        d.path("M" + " L".join(f"{ax.xc(k):.1f} {Yc(S.kostsum(k)):.1f}" for k in range(1, 37)), stroke=col, sw=1.4, dash="5 3")
    d.t(ax.xc(34), Yc(G.kostsum(34)) - 10, f"Spill 17: {nf(G.kostsum(36))} kr", 13, 700, INK, "end")
    d.t(ax.xc(36), Yc(BARE.kostsum(36)) + 20, f"Bare Sara teller på vei, simulert: {nf(BARE.kostsum(36))} kr", 13, 600, INK, "end", 'stroke="#F0D5D2" stroke-width="4" paint-order="stroke"')
    d.t(ax.xc(36), Yc(ALLE.kostsum(36)) + 20, f"Alle fire teller på vei, simulert: {nf(ALLE.kostsum(36))} kr", 13, 600, INK, "end", 'stroke="#F0D5D2" stroke-width="4" paint-order="stroke"')
    d.t(ax.xc(20), Yc(G.cum_lager(20)) + (base - Yc(G.cum_lager(20))) / 2 + 4, "lager", 13, 600, BLUE, "middle")
    d.t(ax.xc(24), Yc((G.cum_lager(24) + G.kostsum(24)) / 2) + 4, "restordre", 13, 600, RED, "middle")
    d.t(ax.x0 + 6, gy + 14, "Grossist, akkumulert kostnad, kr", 13, 600, INK)
    xaxis(d, ax, gy + gh + 16, [1, 5, 10, 15, 20, 25, 30, 36], None, 12)

    # Hjelpegrad og P7
    ny = yr + 4
    d.t(keyx, ny, "Hjelpegrad", 20, 600, INK)
    ny = d.para(keyx, ny + 26, "Klassespill: båndet viser delene, grafen viser kjente ankomster. Ingen sum og ingen linje.", keyw, 14, 19, fill=INK)
    ny = d.para(keyx, ny + 4, "Replay: båndet legger sammen til Posisjon, og projeksjonen åpnes. Studenten har da kjent på hva summen betyr.", keyw, 14, 19, fill=INK)
    ny = d.para(keyx, ny + 8, "P7: Å telle det som er på vei er ikke nok alene. I simuleringen ga en regel som jaget siste ordre for hardt, Fabrikk høyere forsterkning (12×) enn spill 17.", keyw, 13, 17, fill=INK2)
    d.para(keyx, ny + 6, "P8 og kjedemålet: restordre koster dobbelt, og målet er lavest kostnad for hele kjeden, ikke for ett ledd.", keyw, 13, 17, fill=INK2)
    d.demodata(1960, 1392, "Demodata. Simulerte referanser er merket Simulert.", 13, "end")
    d.save()


if __name__ == "__main__":
    build_05()
    build_06()
    build_10()
