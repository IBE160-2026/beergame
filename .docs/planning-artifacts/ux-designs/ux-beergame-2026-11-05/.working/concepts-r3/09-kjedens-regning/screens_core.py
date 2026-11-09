"""Kjerneflatene: 05 spill, 06 spilldynamikk, 10 pedagogikk."""
from e09cost import *

G = S17["Grossist"]
BARE = CHAIN["bare"]["Grossist"]
ALLE = REF["Grossist"]
K = FX["spill17"]
A = FX["alle_teller_paa_vei"]


def phone_game(d, wk, typed, state="typed", hn=86):
    """Telefonen i Klassespillet: kjedebånd øverst, meteogram med kostnadsfelt, ordrefelt."""
    phone_head(d, wk, G.kostsum(wk))
    yb = chain_band(d, G, 20, 100, 350, wk, typed, u=1.3, top=36, bottom=34, ls=13)
    d.line(20, yb + 8, 370, yb + 8, HAIR, 1)
    m = stack_chart(d, G, 16, yb + 18, 358, wk, typed, panels=(("net", hn), ("flow", 34), ("ord", 28), ("cost", 30)),
                    left=30, gap=12, ls=13)
    return m


def order_input(d, y, wk, typed):
    d.t(20, y + 20, f"Din ordre for Uke {wk}", 15, 600, INK)
    d.t(370, y + 20, "Din regning", 14, 600, BLUE, "end", 'text-decoration="underline"')
    yb = y + 32
    d.rect(20, yb, 350, 52, PAPER, INK if typed is not None else HAIR2, 1.4, 6)
    d.line(78, yb, 78, yb + 52, HAIR2, 1)
    d.line(312, yb, 312, yb + 52, HAIR2, 1)
    d.line(40, yb + 26, 58, yb + 26, INK, 2)
    d.line(332, yb + 26, 350, yb + 26, INK, 2)
    d.line(341, yb + 17, 341, yb + 35, INK, 2)
    if typed is None:
        d.t(195, yb + 33, "Antall enheter", 17, 400, INK3, "middle")
    else:
        d.t(195, yb + 38, typed, 32, 700, INK, "middle")
    return yb + 52


def waiting_rows(d, y, rows, x=20, width=350, lh=30):
    """rows: (rolle, navn, status, ferdig?)"""
    for rolle, navn, status, done in rows:
        if done:
            d.circle(x + 6, y - 5, 5, INK)
        else:
            d.circle(x + 6, y - 5, 5, PAPER, INK, 1.5)
        d.t(x + 20, y, rolle, 14, 600, INK)
        d.t(x + 100, y, navn, 14, 400, INK)
        d.t(x + width, y, status, 14, 400, INK2, "end")
        y += lh
    return y


def seat_sara_klar():
    return [("Detaljist", "Ida", "har bestilt", True), ("Distributør", "Mikkel", "har bestilt", True),
            ("Fabrikk", "Jonas", "venter, 3 min", False), ("Grossist", "Sara", "har bestilt", True)]


def own_bill_matrix(d, x, y, w, g, wfrom, wto, ls=13, rowh=24, label_w=92):
    """Setets egen regning som tabell: uker som kolonner, samme tall som i grafen."""
    ax = Axis(x + label_w, w - label_w, wfrom, wto)
    for k in range(wfrom, wto + 1):
        d.t(ax.xc(k), y, k, ls, 700 if k == wto else 400, INK if k == wto else INK3, "middle")
    yy = y + 8
    rows = [("Lager", lambda k: str(g.lager[k - 1]), None), ("Restordre", lambda k: str(g.rest[k - 1]), None),
            ("Kostnad", None, "cell"), ("Sum så langt", lambda k: kr(g.kostsum(k)), None)]
    for lab, fn, kind in rows:
        d.t(x, yy + rowh / 2 + ls * 0.34, lab, ls, 600 if kind or lab == "Sum så langt" else 400, INK)
        for k in range(wfrom, wto + 1):
            if kind == "cell":
                c = g.ck(k)
                fill, txt, wt = cell_style(g.kind(k), c)
                if fill:
                    d.rect(ax.xl(k) + 1, yy + 1, ax.slot - 2, rowh - 2, fill)
                d.t(ax.xc(k), yy + rowh / 2 + ls * 0.34, kr(c), ls, wt, txt if fill else INK3, "middle")
            else:
                v = fn(k)
                d.t(ax.xc(k), yy + rowh / 2 + ls * 0.34, v, ls, 600 if lab == "Sum så langt" and k == wto else 400,
                    INK if v != "0" else INK3, "middle")
        d.line(x, yy + rowh, x + w, yy + rowh, HAIR, 1)
        yy += rowh
    return yy, ax


# ---------- 05 ----------
def build_05():
    d = Doc("05-spill", 1600, 1000, "Kjedens regning, hovedskjerm i Uke 11",
            "Saras telefon i Uke 11 med 24 tastet inn: kjedebånd med eget ledd, meteogram med kostnadsfelt og ordrefelt. Ved siden av: Din regning som tabell, laptop, og hjelpegraden i Klassespill og Replay.")
    d.t(40, 46, "Uke 11. Sara ser sitt eget ledd, sin egen graf og sin del av regningen.", 26, 600, INK)

    phone(d, 40, 84, 1.0)
    m = phone_game(d, 11, 24)
    yb = order_input(d, m["axisbot"] + 10, 11, 24)
    d.t(20, yb + 22, "Kommer fram om lag Uke 15. Kan ikke endres etter bekreftelse.", 13, 400, INK2)
    d.button(20, yb + 36, 350, 50, "Bekreft ordre på 24")
    d.t(20, yb + 108, "Venter på: Jonas (3 min) og deg.", 13, 400, INK2)
    d.demodata(370, yb + 108, a="end")
    d.end()
    d.t(235, 952, "Telefon, Klassespill: ledd, graf og egen kostnad på én akse.", 14, 400, INK2, "middle")

    # Åpnet panel: Din regning
    px = 460
    phone(d, px, 84, 1.0)
    d.t(20, 62, "Din regning, Uke 1 til 11", 22, 700, INK)
    d.t(370, 62, "Lukk", 15, 600, BLUE, "end", 'text-decoration="underline"')
    d.para(20, 92, "Hver Uke koster det som står i leddet ditt når Uka er regnet: lager × 0,50 og restordre × 1,00.", 350, 14, 19, fill=INK2)
    yy, ax = own_bill_matrix(d, 20, 150, 350, G, 1, 11, rowh=26, label_w=88)
    yy += 26
    L, R = G.lsum(1, 11), G.rsum(1, 11)
    d.t(20, yy, "Lagerkost", 15, 400, INK)
    d.t(370, yy, f"{nf(L)} kr", 15, 400, INK, "end")
    yy += 26
    d.t(20, yy, "Restordrekost", 15, 400, INK)
    d.t(370, yy, f"{nf(R)} kr", 15, 700, INK, "end")
    d.line(20, yy + 9, 370, yy + 9, INK, 1)
    yy += 30
    d.t(20, yy, "Din del av regningen", 15, 600, INK)
    d.t(370, yy, f"{nf(L + R)} kr", 15, 700, INK, "end")
    assert L + R == G.kostsum(11)
    yy += 22
    d.para(20, yy, f"Restordre {G.rest[8]}, {G.rest[9]} og {G.rest[10]} i tre Uker kostet {nf(R)} kr. Like mange enheter på lager hadde kostet halvparten.", 350, 13, 18, fill=INK2)
    yy += 66
    d.t(20, yy, "Regnestykket", 17, 600, INK)
    yy += 26
    d.t(20, yy, "Lager − Restordre + På vei", 14, 400, INK2)
    yy += 24
    d.t(20, yy, "Posisjon", 15, 400, INK)
    d.t(370, yy, f"{G.lager[10]} − {G.rest[10]} + {G.paavei(11)} = {G.posisjon(11)}", 15, 600, INK, "end")
    yy += 26
    d.t(20, yy, "Med ordren på 24", 15, 400, INK)
    d.t(370, yy, f"{G.posisjon(11)} + 24 = {G.posisjon(11) + 24}", 15, 600, INK, "end")
    yy += 34
    d.para(20, yy, "Kjedens regning og de andre leddene vises først når spillet er ferdig.", 350, 13, 18, fill=INK2)
    d.demodata(20, 830)
    d.end()
    d.t(655, 952, "Ett trykk unna: din regning som tall, og regnestykket uten fasit.", 14, 400, INK2, "middle")

    # Laptop
    lx, ly, lw, lh = 880, 84, 680, 470
    d.rect(lx, ly, lw, lh, PAPER, HAIR2, 1.4, 10)
    d.t(lx + 24, ly + 40, "Uke 11", 26, 700, INK)
    d.t(lx + 104, ly + 40, "Grossist, Spill 17", 14, 400, INK2)
    d.t(lx + lw - 24, ly + 40, f"Din del av regningen {nf(G.kostsum(11))} kr", 15, 600, INK, "end")
    yb2 = chain_band(d, G, lx + 24, ly + 58, 420, 11, 24, u=1.0, top=30, bottom=32, ls=13)
    m2 = stack_chart(d, G, lx + 16, yb2 + 8, 428, 11, 24, panels=(("net", 92), ("flow", 34), ("ord", 26), ("cost", 28)),
                     left=30, gap=10, ls=13)
    cx = lx + 476
    y = ly + 80
    for lab, val in [("Lager", G.lager[10]), ("Restordre", G.rest[10]), ("Ordre inn", G.inn(11)), ("Levering", G.levering(11)),
                     ("Sendt", G.sendt(11)), ("På vei", f"{G.paavei(11)} + 24"), ("Uka koster", f"{nf(G.ck(11))} kr")]:
        d.t(cx, y, lab, 14, 400, INK)
        d.t(lx + lw - 24, y, val, 14, 600, INK, "end")
        d.line(cx, y + 7, lx + lw - 24, y + 7, HAIR, 1)
        y += 27
    y += 18
    d.t(cx, y, "Din ordre for Uke 11", 14, 600, INK)
    d.rect(cx, y + 10, lx + lw - 24 - cx, 48, PAPER, INK, 1.4, 6)
    d.t((cx + lx + lw - 24) / 2, y + 45, 24, 30, 700, INK, "middle")
    d.button(cx, y + 70, lx + lw - 24 - cx, 44, "Bekreft ordre på 24", size=15)
    d.t(cx, y + 136, "Venter på: Jonas (3 min) og deg.", 13, 400, INK2)
    d.demodata(lx + lw - 24, ly + lh - 14, a="end")

    # Hjelpegrad
    hy = 600
    d.t(lx, hy, "Hjelpegrad: samme ledd i Uke 11, på to nivåer", 20, 600, INK)
    pw = 320
    d.t(lx, hy + 30, "Klassespill: varene på vei, uten sum", 14, 600, INK)
    e1 = chain_band(d, G, lx, hy + 42, pw, 11, 24, u=1.0, top=30, bottom=32, ls=13, cost=True)
    bx = lx + pw + 40
    d.t(bx, hy + 30, "Replay, etter Debriefen: Posisjon tegnes", 14, 600, INK)
    e2 = chain_band(d, G, bx, hy + 42, pw, 11, 24, u=1.0, top=30, bottom=32, ls=13, pos=True, cost=True)
    yn = max(e1, e2) + 24
    d.para(lx, yn, "I Klassespillet ser Sara hver ordre i røret og hva uka koster, men må legge sammen selv. Det er denne summen folk flest lar være å regne, og regningen i Debriefen viser hva det kostet kjeden.", pw, 14, 19, fill=INK2)
    d.para(bx, yn, f"I Replay står summen under båndet: {G.lager[10]} − {G.rest[10]} + {G.paavei(11) + 24} = {G.posisjon(11) + 24}. Den sier hva som er i leddet og på vei, ikke hva du bør bestille.", pw, 14, 19, fill=INK2)
    d.save()


# ---------- 06 ----------
def build_06():
    d = Doc("06-spilldynamikk", 2100, 1200, "Kjedens regning, en Uke i spillet",
            "Seks telefonruter: Uka åpner, beslutningen, bekreftet, Uka går videre, Jonas er borte, spillet slutter med kjedens regning.")
    s = 0.8
    pw = 390 * s
    gapx = (2100 - 80 - 6 * pw) / 5
    y0 = 188
    d.t(40, 50, "En Uke i Kjedens regning: varene rykker fram i røret, og hver Uke legger en linje til regningen.", 28, 600, INK)
    notes = [
        ("A  Uka åpner", "Ny levering inn, ny ordre inn, og ukas kostnad er lagt til. Plassen ytterst i røret står tom."),
        ("B  Beslutningen: 24", "Sara taster, og 24 legger seg ytterst i røret, bak 4, 4 og 8. 16 var allerede på vei. Ingen fasit."),
        ("C  Bekreftet", "Ordren er låst. Skjermen viser hvem Uka venter på, med Rolle, navn og hvor lenge."),
        ("D  Uka går videre", "Røret rykker én plass, og en ny Uke legges til regningen. Under 2 sekunder, og kan hoppes over."),
        ("E  Jonas er borte", "Pause, så bestiller KI-spiller for Fabrikk, alltid merket. Jonas kan ta setet tilbake."),
        ("F  Spillet slutter", "Kjedens regning først, så per Rolle og per kostnadsart. Hvorfor ble den slik? Det er Debriefen."),
    ]
    for i, (h, n) in enumerate(notes):
        x = 40 + i * (pw + gapx)
        d.t(x, 94, h, 20, 600, INK)
        d.para(x, 120, n, pw, 15, 20, fill=INK2)

    def px(i):
        return 40 + i * (pw + gapx)

    # A
    phone(d, px(0), y0, s)
    m = phone_game(d, 11, None)
    yb = order_input(d, m["axisbot"] + 10, 11, None)
    d.t(20, yb + 22, f"Sist Uke bestilte du {G.order(10)}.", 13, 400, INK2)
    d.button(20, yb + 36, 350, 50, "Bekreft ordre", primary=False)
    d.demodata(20, 830)
    d.end()

    # B
    phone(d, px(1), y0, s)
    m = phone_game(d, 11, 24)
    yb = order_input(d, m["axisbot"] + 10, 11, 24)
    d.t(20, yb + 22, "Kommer fram om lag Uke 15. Kan ikke endres.", 13, 400, INK2)
    d.button(20, yb + 36, 350, 50, "Bekreft ordre på 24")
    d.demodata(20, 830)
    d.end()

    # C
    phone(d, px(2), y0, s)
    m = phone_game(d, 11, 24)
    y = m["axisbot"] + 10
    d.t(20, y + 22, "Ordren på 24 er sendt. Venter på Jonas.", 15, 600, INK)
    waiting_rows(d, y + 56, seat_sara_klar())
    d.t(20, y + 186, "Du får beskjed når Uke 12 åpner.", 13, 400, INK2)
    d.demodata(20, 830)
    d.end()

    # D
    w = 12
    phone(d, px(3), y0, s)
    m = phone_game(d, w, None)
    ax = m["ax"]
    d.line(ax.xr(11), m["ys"]["net"][0] - 2, ax.xr(11), m["ybot"], INK3, 1, dash="2 3")
    y = m["axisbot"] + 10
    d.t(20, y + 22, "Uke 11 er ferdig regnet", 15, 600, INK)
    d.t(370, y + 22, "Hopp over", 14, 600, BLUE, "end", 'text-decoration="underline"')
    rr = [("Inn", G.levering(w)), ("Ordre inn", G.inn(w)), ("Ut", G.sendt(w)),
          ("Restordre", f"{G.rest[w - 2]} blir {G.rest[w - 1]}"), ("Uke 12 koster", f"{nf(G.ck(w))} kr")]
    yy = y + 50
    for lab, v in rr:
        d.t(20, yy, lab, 14, 400, INK)
        d.t(370, yy, v, 14, 600, INK, "end")
        yy += 22
    d.demodata(20, 830)
    d.end()

    # E
    w = 14
    phone(d, px(4), y0, s)
    m = phone_game(d, w, G.order(w), hn=80)
    y = m["axisbot"] + 6
    d.t(20, y + 20, "Pause: Jonas har ikke bestilt på 24 t.", 15, 600, INK)
    rows = [("Detaljist", "Ida", "har bestilt", True), ("Distributør", "Mikkel", "har bestilt", True),
            ("Fabrikk", "KI-spiller for Jonas", "bestiller", False), ("Grossist", "Sara", "har bestilt", True)]
    yy = waiting_rows(d, y + 46, rows, lh=24)
    d.rect(20, yy - 10, 350, 62, TINT, None, 1, 6)
    d.t(32, yy + 10, "Slik ser Jonas det:", 13, 400, INK2)
    d.t(32, yy + 32, "KI-spiller bestiller for deg.", 14, 600, INK)
    d.button(238, yy - 1, 122, 42, "Ta tilbake setet", primary=False, size=13)
    d.end()

    # F: spillet slutter, kjedens regning
    phone(d, px(5), y0, s)
    d.t(20, 62, "Spillet er ferdig", 30, 700, INK)
    d.t(20, 84, "Grossist, Spill 17", 14, 400, INK2)
    d.t(20, 128, "Kjedens regning", 15, 400, INK2)
    d.t(20, 168, f"{nf(K['kjedekost'])} kr", 40, 700, INK, extra='style="font-variant-numeric:lining-nums proportional-nums"')
    L, R = chain_sums(S17)
    d.t(20, 196, f"Lager {nf(L)} kr · restordre {nf(R)} kr", 14, 400, INK2)
    y = 236
    mx = max(K["kost_per_rolle"].values())
    sc = 350 / mx
    for r in ROLES:
        s_ = S17[r]
        v = K["kost_per_rolle"][r]
        me = r == "Grossist"
        d.t(20, y, r + (" (deg)" if me else ""), 14, 600 if me else 400, INK)
        d.t(370, y, f"{nf(v)} kr", 14, 600, INK, "end")
        d.rect(20, y + 8, s_.lsum() * sc, 10, BLUEF, BLUE, 1)
        d.rect(20 + s_.lsum() * sc, y + 8, s_.rsum() * sc, 10, REDF, RED, 1)
        y += 48
    d.t(20, y - 6, "Blått: lagerkost. Rødt: restordrekost.", 13, 400, INK2)
    y += 24
    d.t(20, y, "Kjedens kostnad per uke", 14, 600, INK)
    ax = Axis(20, 350, 1, G.n)
    hh = 90
    cap = max(chain_week(S17, k) for k in range(1, 37))
    u = hh / cap
    for k in range(1, 37):
        lg = sum(S17[r].lk(k) for r in ROLES)
        rs = sum(S17[r].rk(k) for r in ROLES)
        base = y + 12 + hh
        bw_ = ax.slot - 2
        d.rect(ax.xc(k) - bw_ / 2, base - lg * u, bw_, lg * u, BLUE)
        d.rect(ax.xc(k) - bw_ / 2, base - (lg + rs) * u, bw_, rs * u, RED)
    d.line(20, y + 12 + hh, 370, y + 12 + hh, HAIR2, 1)
    xaxis(d, ax, y + 12 + hh + 18, [1, 12, 24, 36])
    d.t(370, y + 4, f"høyest {nf(cap)} kr", 13, 400, INK2, "end")
    d.button(20, 750, 350, 54, "Gå til Debrief")
    d.demodata(20, 830)
    d.end()

    # Under: hva lærer spilleren
    yt = y0 + 844 * s + 54
    d.t(40, yt, "Hva spilleren lærer av å se leddet, grafen og regningen Uke for Uke", 24, 600, INK)
    tekst = [
        "Kjedebåndet viser varene som bokser på samme skala som lageret. Det som er på vei, ligger der hele tiden, og rykker én plass for hver Uke.",
        "Hver ordre står to ganger: som mørk stolpe der den ble lagt, og som åpen boks ytterst i røret og fire Uker fram i grafen. Det du får nå, bestemte du for fire Uker siden.",
        "Kostnadsfeltet legger en stolpe til hver Uke. Rød stolpe er restordre, og den er dobbelt så dyr per enhet som lager. Summen øverst er regnestykket, ikke en karakter.",
        "Under spillet ser Sara bare sin egen del av regningen. Når spillet er ferdig, kommer kjedens regning, og spørsmålet blir hvorfor den ble slik.",
    ]
    colw = (2100 - 80 - 3 * 40) / 4
    for i, tx in enumerate(tekst):
        d.para(40 + i * (colw + 40), yt + 36, tx, colw, 16, 22, fill=INK)
    ys = yt + 124
    d.t(40, ys, f"Ordren på 24 sett fra fem Uker: boksen rykker mot leddet, og i Uke 15 kommer {G.levering(15)}.", 17, 600, INK)
    pw2 = (2100 - 80 - 4 * 30) / 5
    for i, wk in enumerate(range(11, 16)):
        xx = 40 + i * (pw2 + 30)
        typed = 24 if wk == 11 else G.order(wk)
        chain_band(d, G, xx, ys + 10, pw2 - 20, wk, typed, u=0.9, top=26, bottom=36, ls=13, over_note=False, mark=15,
                   cost_txt=f"Uke {wk} koster {nf(G.ck(wk))} kr. Sum {nf(G.kostsum(wk))} kr.")
    d.save()


# ---------- 10 ----------
def build_10():
    d = Doc("10-pedagogikk", 2000, 1400, "Kjedens regning, grafgrammatikken over tid",
            "Saras ledd, meteogram og regning i Uke 5, 11, 18 og 29 på én felles tidsakse, og kjedens regning mot simulert referanse etter Debriefen.")
    d.t(40, 56, "Samme ledd, samme graf og samme regning i fire Uker av Saras spill", 34, 700, INK)
    d.para(40, 90, "Til venstre står leddet slik Sara så det. I midten deler radene tidsakse og skala, så nå-streken vandrer mot høyre. Nederst i hver rad er regningen, uke for uke, i kroner.", 1400, 17, 23, fill=INK2)

    keyx = 1500
    rows = [
        (5, G.order(5), [
            ("P2 Forsinkelse", "Røret er fullt av 4-ere. Det som skjer hos kundene i Uke 5, er ikke synlig fra Saras ledd ennå."),
            ("P4 Ordrer er ikke etterspørsel", "Ordre inn er det Ida bestilte. Sara har ingen annen kilde."),
            ("Til neste ordre", f"Regningen er rolig: {nf(G.ck(5))} kr per Uke for lager {G.lager[4]}. Det betyr bare at ingenting har nådd leddet ennå."),
        ]),
        (11, 24, [
            ("P3 Det som er på vei", f"Røret har {G.paavei(11)} enheter, og leddet mangler {G.rest[10]}. Posisjon {G.lager[10]} − {G.rest[10]} + {G.paavei(11)} = {G.posisjon(11)}. Med 24 blir den {G.posisjon(11) + 24}."),
            ("P1 Lager er en opphopning", f"Inn {G.levering(11)}, ordre inn {G.inn(11)}: leddet faller {G.net(10) - G.net(11)} denne Uka. Rød del av stolpen er nøyaktig det."),
            ("P8 Restordre koster dobbelt", f"Uke 11 koster {nf(G.ck(11))} kr for {G.rest[10]} i restordre. {G.rest[10]} på lager hadde kostet {nf(G.rest[10] * 0.5)} kr."),
        ]),
        (18, G.order(18), [
            ("P3 og P2 igjen", f"{G.paavei(18)} på vei, og {G.overdue(18)} av dem er hos Distributør uten dato. Røret er fullt, men leddet er tomt."),
            ("P7 Overreaksjon forsterker", "En ny ordre kommer ikke raskere enn de gamle. Den legger seg bakerst i røret, og Distributør får et større tall å svare på."),
            ("Til neste ordre", f"Uka koster {nf(G.ck(18))} kr. Spør hva {G.paavei(18)} på vei koster når de kommer, ikke bare hva restordren koster nå."),
        ]),
        (29, G.order(29), [
            ("P8 Begge sider koster", f"Lager {G.lager[28]} × 0,50 = {nf(G.ck(29))} kr per Uke. Restordren er borte, men varene som skulle dekke den, kom samtidig og ble liggende."),
            ("P1 Samme regning, motsatt fortegn", "Blå stolper i Uke 25 til 27 er gamle ordrer som kom nesten samtidig. Toppen er summen av dem."),
            ("Til neste ordre", f"Regningen så langt: {nf(G.kostsum(29))} kr, {nf(G.rsum(1, 29))} av dem restordre. Hvor mye du vil ha på lager, må du bestemme selv."),
        ]),
    ]
    y = 140
    cx0, cw_ = 470, 990
    rh = 232
    for now, typed, notes in rows:
        d.t(40, y + 26, f"Uke {now}", 26, 700, INK)
        chain_band(d, G, 40, y + 40, 370, now, typed, u=0.85, top=36, bottom=46, ls=13, over_note=True)
        m = stack_chart(d, G, cx0, y + 8, cw_, now, typed, panels=(("net", 72), ("flow", 26), ("ord", 22), ("cost", 22)),
                        wmin=1, wmax=36, left=34, gap=7, ls=12, titles=False, xstep=4, ticks=(-40, 0, 20), cost_cells=True,
                        net_label=False, ord_label=False, arrnums=False)
        ax = m["ax"]
        for name, lab in (("flow", "Inn og ut"), ("ord", "Ordre"), ("cost", "Kr")):
            y0_, h_ = m["ys"][name]
            d.t(cx0 + 28, y0_ + h_ / 2 + 4, lab, 12, 400, INK2, "end")
        d.t(m["fx0"] + 6, m["ys"]["cost"][0] + 16, f"Sum {nf(G.kostsum(now))} kr", 13, 700, INK)
        ny = y + 16
        for head, body in notes:
            d.t(keyx, ny, head, 15, 600, INK)
            ny = d.para(keyx, ny + 19, body, 460, 14, 18, fill=INK2) + 4
        d.line(40, y + rh - 8, 1960, y + rh - 8, HAIR, 1)
        y += rh

    # Etter Debriefen: kjedens regning mot simulert referanse
    y += 6
    d.t(40, y + 22, "Etter Debriefen: kjedens regning mot simulert referanse", 24, 600, INK)
    d.t(40, y + 46, "Samme kunder, samme struktur. I referansen teller alle fire det som er på vei og tilpasser rolig. Simulert, ingen fasit.", 15, 400, INK2)
    gy = y + 76
    gh = 196
    ax = Axis(110, 620, 1, 36)
    Y, pts, rpts = cum_area(d, ax, gy, gh, S17, ROLES, 2400, ref=REF, ticks=(0, 1000, 2000), ls=13)
    L, R = chain_sums(S17)
    rl, rr_ = chain_sums(REF)
    d.t(ax.xc(36) + 10, Y(L + R) + 5, f"Spill 17: {nf(L + R)} kr", 14, 700, INK)
    d.t(ax.xc(36) + 10, Y(rl + rr_) + 5, f"Simulert: {nf(rl + rr_)} kr", 14, 600, INK2)
    w30 = pts[29]
    ref30 = cum_lines(REF, ROLES)[29][2]
    d.t(ax.xc(29), Y((ref30 + w30[2]) / 2) + 5, f"Restordrekost {nf(R)}", 14, 600, INK, "middle")
    w33 = pts[32]
    d.t(ax.xc(31), Y(w33[1] / 2) + 5, f"Lagerkost {nf(L)}", 14, 600, INK, "middle")
    xaxis(d, ax, gy + gh + 18, [1, 5, 10, 15, 20, 25, 30, 36], None)
    d.t(110, gy + gh + 42, "Akkumulert kostnad for kjeden. Stiplet: simulert referanse. P5, P6, P8.", 13, 400, INK2)
    lx = 940
    d.t(lx, gy - 34, "Regningen, linje for linje", 15, 600, INK)
    ledger(d, lx, gy - 6, 520, S17, ROLES, ref=REF, ls=13, rowh=22, col1=lx + 196, col2=lx + 272)
    d.t(lx, gy + 246, "Stolpe: Spill 17. Grå strek under: Simulert.", 13, 400, INK2)

    d.t(keyx, y + 22, "Hjelpegrad", 20, 600, INK)
    ny = d.para(keyx, y + 48, "Klassespill: eget ledd med røret, egen graf og egen regning. Posisjon ligger ett trykk unna som regnestykke.", 460, 15, 20, fill=INK)
    ny = d.para(keyx, ny + 6, "Etter Debriefen: kjedens regning, og i Replay tegnes Posisjon som sum under båndet.", 460, 15, 20, fill=INK)
    ny = d.para(keyx, ny + 12, "P7: Å telle det som er på vei er ikke nok alene. I simuleringen ga en regel som jaget siste ordre for hardt, Fabrikk høyere forsterkning (12×) enn spill 17.", 460, 14, 18, fill=INK2)
    d.para(keyx, ny + 8, "P5: Distributør og Fabrikk betalte mest, uten å se en eneste kunde. Svingningene vokser oppover, og regningen vokser med dem.", 460, 14, 18, fill=INK2)
    d.demodata(1960, 1388, "Demodata. Simulerte referanser er merket Simulert.", 13, "end")
    d.save()


if __name__ == "__main__":
    build_05()
    build_06()
    build_10()
