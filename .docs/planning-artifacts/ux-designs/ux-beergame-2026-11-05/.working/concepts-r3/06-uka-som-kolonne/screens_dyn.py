"""06 spilldynamikk og 10 pedagogikk."""
from e06lib import *
from screens_core import phone_body, phone_game, seat_sara_klar


# ---------- 06 ----------
def build_06():
    d = Doc("06-spilldynamikk", 2100, 1200, "Uka som kolonne, en Uke i spillet",
            "Seks telefonruter: Uka åpner, beslutningen, bekreftet, Uka går videre og en ny kolonne kommer til, Jonas er borte, spillet slutter med kjedens kostnad.")
    s = 0.8
    pw = 390 * s
    gapx = (2100 - 80 - 6 * pw) / 5
    y0 = 196
    d.t(40, 50, "En Uke i spillet: en ny kolonne fylles ut, og kjeden over viser alltid den siste.", 28, 600, INK)
    notes = [
        ("A  Uka åpner", "Kolonnen for Uke 11 har fått levering og ordre inn. Restordren er regnet. Cellen for din ordre står tom."),
        ("B  Beslutningen: 24", "Sara taster 24. Tallet står i kolonnen nå og i Levering fire kolonner fram, og i kjeden som siste boks. 16 var på vei."),
        ("C  Bekreftet", "Ordren er låst. Skjermen sier hvem Uka venter på, med Rolle, navn og hvor lenge."),
        ("D  Uka går videre", "Nå-streken flytter seg én kolonne, og kjeden viser Uke 12. Under 2 sekunder, og kan hoppes over."),
        ("E  Jonas er borte", "Pause, så bestiller en KI-spiller for Fabrikk, alltid merket. Jonas kan ta setet tilbake."),
        ("F  Spillet slutter", "Først kjedens totalkostnad, så per Rolle og per kostnadsart. Videre til Debrief."),
    ]
    for i, (h, n) in enumerate(notes):
        x = 40 + i * (pw + gapx)
        d.t(x, 94, h, 20, 600, INK)
        d.para(x, 120, n, pw, 15, 20, fill=INK2)

    def px(i):
        return 40 + i * (pw + gapx)

    # A
    phone_game(d, px(0), y0, G, 11, None, s)
    d.demodata(20, 828)
    d.end()
    # B
    phone_game(d, px(1), y0, G, 11, 24, s)
    d.demodata(20, 828)
    d.end()
    # C
    phone(d, px(2), y0, s)
    game_header(d, 11, G.kostsum(11))
    m = phone_body(d, G, 11, 24)
    y = m["ybot"] + 14
    d.t(20, y + 24, "Ordren på 24 er sendt. Venter på Jonas.", 15, 600, INK)
    waiting_rows(d, y + 56, seat_sara_klar(), lh=27)
    d.t(20, y + 176, "Du får beskjed når Uke 12 åpner.", 13, 400, INK2)
    d.demodata(20, 828)
    d.end()
    # D
    w = 12
    phone(d, px(3), y0, s)
    game_header(d, w, G.kostsum(w))
    m = phone_body(d, G, w, None)
    ax = m["ax"]
    d.line(ax.xr(11), m["ycol"], ax.xr(11), m["ybot"], INK3, 1, dash="2 3")
    y = m["ybot"] + 14
    d.t(20, y + 24, "Uke 11 er ferdig regnet", 15, 600, INK)
    d.link(370, y + 24, "Hopp over", 14, "end")
    c, cp = G.col(w), G.col(w - 1)
    rr = [("Levering", c["lev"]), ("Ordre inn", c["inn"]), ("Restordre", f"{cp['rest']} blir {c['rest']}"),
          ("Kostnad denne Uka", f"{nf(c['kost'])} kr")]
    yy = y + 52
    for lab, v in rr:
        d.t(20, yy, lab, 14, 400, INK)
        d.t(370, yy, v, 14, 600, INK, "end")
        yy += 23
    d.demodata(20, 828)
    d.end()
    # E
    w = 14
    phone(d, px(4), y0, s)
    game_header(d, w, G.kostsum(w))
    m = phone_body(d, G, w, G.order(w))
    y = m["ybot"] + 12
    d.t(20, y + 22, "Pause: Jonas har ikke bestilt på 24 t.", 15, 600, INK)
    rows = [("Detaljist", "Ida", "har bestilt", True), ("Distributør", "Mikkel", "har bestilt", True),
            ("Fabrikk", "KI-spiller", "bestiller for Jonas", False), ("Grossist", "Sara", "har bestilt", True)]
    yy = waiting_rows(d, y + 48, rows, lh=24, size=13)
    d.rect(20, yy - 8, 350, 50, TINT, None, 1, 6)
    d.t(32, yy + 12, "Jonas ser: KI-spiller", 13, 400, INK2)
    d.t(32, yy + 30, "bestiller for deg.", 13, 400, INK2)
    d.button(232, yy - 1, 128, 36, "Ta tilbake setet", primary=False, size=13)
    d.demodata(20, 828)
    d.end()
    # F
    phone(d, px(5), y0, s)
    d.t(20, 66, "Spillet er ferdig", 30, 700, INK)
    d.t(20, 88, "Grossist, Spill 17", 14, 400, INK2)
    d.t(20, 132, "Kjedens totalkostnad", 15, 400, INK2)
    d.big(20, 172, f"{nf(K['kjedekost'])} kr", 40)
    tl = sum(SEATS[r].sum_l() for r in ROLES)
    tr = sum(SEATS[r].sum_r() for r in ROLES)
    assert abs(tl + tr - K["kjedekost"]) < 1e-9
    d.t(20, 198, f"Restordrekostnad {nf(tr)} kr", 14, 400, INK)
    d.t(20, 218, f"Lagerkostnad {nf(tl)} kr", 14, 400, INK)
    y = 262
    mx = max(K["kost_per_rolle"].values())
    for r in ROLES:
        S = SEATS[r]
        v = K["kost_per_rolle"][r]
        d.t(20, y, r + (" (deg)" if r == "Grossist" else ""), 14, 600 if r == "Grossist" else 400, INK)
        d.t(370, y, f"{nf(v)} kr", 14, 600, INK, "end")
        wl = 350 * S.sum_l() / mx
        wr = 350 * S.sum_r() / mx
        d.rect(20, y + 8, wr - 1, 9, RED)
        d.rect(20 + wr + 1, y + 8, wl - 1, 9, BLUE)
        d.t(20, y + 34, f"restordre {nf(S.sum_r())} · lager {nf(S.sum_l())}", 13, 400, INK2)
        y += 62
    d.t(20, y + 4, "Rødt: restordre, 1,00 per enhet per uke.", 13, 400, INK2)
    d.t(20, y + 22, "Blått: lager, 0,50 per enhet per uke.", 13, 400, INK2)
    d.para(20, y + 60, "Målet var lavest kostnad for hele kjeden. Hvorfor ble den slik? Det finner dere ut sammen i Debriefen, med alle fire ledd.", 350, 14, 19, fill=INK)
    d.button(20, 740, 350, 54, "Gå til Debrief")
    d.demodata(20, 828)
    d.end()

    # Under: hva lærer spilleren
    yt = y0 + 844 * s + 50
    d.t(40, yt, "Hva spilleren lærer av å se kjeden, grafen og kostnaden kolonne for kolonne", 24, 600, INK)
    tekst = [
        "Hver Uke legger én kolonne til tabellen, og kjeden øverst viser alltid den siste. Det som står i kjeden, står også som tall i kolonnen, så bildet kan alltid kontrolleres.",
        "Lager etter forrige Uke + levering − ordre inn er lager nå. Regnestykket står loddrett i kolonnen, og grafen over viser det samme som en linje.",
        "Ordren står to steder: i kolonnen den ble lagt, og i Levering fire kolonner fram. Uke for Uke rykker nå-streken mot den. Det som kommer nå, ble bestemt før.",
        "Kostnad og sum er de to nederste radene. Restordre gir rød celle og koster dobbelt så mye per enhet som lager, så kostnaden kan leses Uke for Uke.",
    ]
    colw = (2100 - 80 - 3 * 40) / 4
    for i, tx in enumerate(tekst):
        d.para(40 + i * (colw + 40), yt + 34, tx, colw, 15, 21, fill=INK)
    ys = yt + 150
    d.t(40, ys, "Ordren på 24 sett fra fem Uker: nå-streken rykker mot kolonnen for Uke 15, og der kommer 17.", 17, 600, INK)
    pw2 = (2100 - 80 - 4 * 30) / 5
    for i, wk in enumerate(range(11, 16)):
        xx = 40 + i * (pw2 + 30)
        ax = Axis(xx + 70, pw2 - 70, 9, 15)
        y1 = ys + 30
        typed = 24 if wk == 11 else G.order(wk)

        def lev(w, wk=wk, typed=typed):
            if w <= wk:
                return (G.levering(w), "typed") if w == 15 else G.levering(w)
            q = dict(G.arrivals(wk, typed)).get(w)
            if q is None:
                return None
            return (q, "typed" if w == 15 else "open")

        rr = [("Levering", "flow", lev), ("På vei", "plain", lambda w, wk=wk: G.paavei(w) if w <= wk else None)]
        week_row(d, ax, y1 - 6, list(range(9, 16)), wk, size=12)
        d.rect(ax.xr(wk), y1, max(ax.x1 - ax.xr(wk), 0), 2 * 20, TINT)
        matrix(d, ax, y1, rr, 9, 15, rh=20, size=12, lx=xx, lsize=12)
        d.line(ax.xr(wk), y1 - 2, ax.xr(wk), y1 + 40, INK, 1.2)
        cap = {11: "Uke 11: 24 i kolonne 15", 12: "Uke 12: tre kolonner igjen", 13: "Uke 13: to igjen", 14: "Uke 14: neste Uke",
               15: f"Uke 15: {G.levering(15)} kom, {G.overdue(15)} forsinket"}[wk]
        d.t(xx, y1 + 62, cap, 14, 400, INK2)
    d.save()


# ---------- 10 ----------
def build_10():
    d = Doc("10-pedagogikk", 2000, 1400, "Uka som kolonne, grafgrammatikken over tid",
            "Fire kolonner fra Saras spill, Uke 5, 11, 18 og 29, forstørret til kjedevisning over et felles meteogram og en felles tabell. Med prinsippene merket, og simulert referanse slik den vises etter Debriefen.")
    d.t(40, 52, "Fire kolonner fra Saras spill, forstørret", 34, 700, INK)
    d.para(40, 84, "Kjeden øverst er alltid én kolonne i tabellen under. Graf og tall deler kolonnene, så det som er tegnet, kan regnes. Arket viser hele spillet i ettertid. Under spillet slutter aksen alltid ved nå + 4.", 1900, 16, 22, fill=INK2)
    weeks = [5, 11, 18, 29]
    ax = Axis(190, 1770, 1, 36)
    notes = {
        5: [("P2 Forsinkelse", "Alt er 4. Bevegelsen som kommer i Uke 7, er ikke synlig herfra ennå."),
            ("P4 Ordrer er ikke etterspørsel", "Ordre inn er det Ida bestilte. Sara har ingen annen kilde."),
            ("Til neste ordre", f"Rolig betyr bare at ingenting har nådd deg. Lageret koster {nf(G.wcost(5))} kr hver Uke.")],
        11: [("P3 Det som er på vei", f"Fire bokser på vei, {G.paavei(11)} + 24. Restordren {G.rest[10]} står rett ved siden av. Summen gjør du selv."),
             ("P1 Kolonnen er regnestykket", f"{sg(G.net(10))} + {G.levering(11)} − {G.inn(11)} = {sg(G.net(11))}. Rød celle er restordre."),
             ("Til neste ordre", f"24 står i kolonne 15. Der kom {G.levering(15)}. Bestilt er ikke levert.")],
        18: [("P2 og P3 igjen", f"{G.paavei(18)} på vei, og {G.overdue(18)} av dem har ingen dato. Restordren er {G.rest[17]}."),
             ("P7 Overreaksjon forsterker", "En ny ordre legger seg bakerst i køen. Leverandøren får et større tall å svare på."),
             ("Til neste ordre", f"Uka koster {nf(G.wcost(18))} kr, summen er {nf(G.kostsum(18))} kr. Spør hva {G.paavei(18)} på vei gjør når de kommer.")],
        29: [("P8 Restordre koster dobbelt", f"Lager {G.lager[28]} × 0,50 = {nf(G.wcost(29))} kr per Uke. Restordre {max(G.rest)} kostet {nf(max(G.rest) * RESTKOST)} kr per Uke."),
             ("P1 Samme regning, motsatt fortegn", f"Kolonnene 24 til 26 fikk {G.levering(24)}, {G.levering(25)} og {G.levering(26)} inn: gamle ordrer, nesten samtidig."),
             ("Til neste ordre", "Blå celler koster også. Hvor mye du vil ha igjen, må du bestemme selv.")],
    }
    bw = 430
    bx = [40, 530, 1020, 1510]
    ytop = 138
    zy = 476
    for i, wk in enumerate(weeks):
        x = bx[i]
        c = G.col(wk)
        d.t(x, ytop, f"Uke {wk}", 26, 700, INK)
        st = f"Lager {c['lager']}" if c["net"] >= 0 else f"Restordre {c['rest']}"
        d.t(x + bw, ytop, f"{st} · På vei {c['pv']} · Sum {nf(c['sum'])} kr", 14, 600, INK2, "end")
        ch = seat_chain(d, x, ytop + 8, bw, G, wk, G.order(wk), u=1.15, yb_off=80)
        ny = max(ch["bottom"] + 20, ytop + 182)
        for head, body in notes[wk]:
            d.t(x, ny, head, 15, 600, INK)
            ny = d.para(x, ny + 19, body, bw, 14, 18, fill=INK2) + 6
        zoom(d, x, x + bw, zy - 6, ax, wk, zy + 24)

    # Meteogram over hele spillet
    yc = zy + 24
    ynet, hn = yc + 8, 120
    yflow, hf = ynet + hn + 14, 42
    yord, ho = yflow + hf + 12, 42
    ycost, hc = yord + ho + 12, 42
    grid(d, ax, ynet, hn, -40, 30, (-40, -20, 0, 20), 13)
    net_area(d, ax, ynet, hn, G.net, 1, 36)
    flow_bars(d, ax, yflow, hf, G, 1, 36, 32)
    order_bars(d, ax, yord, ho, G.order, 1, 36, 25)
    uc = hc / 40
    bwid = ax.slot - 3
    for w in range(1, 37):
        cr, cl = G.kost_r(w), G.kost_l(w)
        base = ycost + hc
        if cr:
            d.rect(ax.xc(w) - bwid / 2, base - cr * uc, bwid, cr * uc, RED)
        if cl:
            d.rect(ax.xc(w) - bwid / 2, base - cl * uc, bwid, cl * uc, BLUE)
    d.line(ax.x0, ycost + hc, ax.x1, ycost + hc, HAIR2, 1)
    lab = [(ynet + 14, "Netto lager", True), (ynet + 32, "over null: lager", False), (ynet + 48, "under: restordre", False),
           (yflow + hf - 4, "Inn og ut, P1", True), (yord + ho - 4, "Din ordre, P2", True), (ycost + hc - 4, "Kostnad, P8", True)]
    for yy, s_, strong in lab:
        d.t(40, yy, s_, 13, 600 if strong else 400, INK if strong else INK2)
    yweek = ycost + hc + 20
    week_row(d, ax, yweek, list(range(1, 37)), None, size=13)
    ymat = yweek + 8
    rows = seat_rows(G, 36, None, future=False)
    rows[4] = ("Din ordre", "flow", G.order)
    ybot = matrix(d, ax, ymat, rows, 1, 36, rh=22, size=13, lx=40, lsize=13)
    for wk in weeks:
        col_box(d, ax, wk, yc, ybot)
        d.t(ax.xc(wk), yc - 6, f"Uke {wk}", 13, 700, INK, "middle")
    d.path(f"M{ax.xr(11) - 2:.1f} {yord + ho - 24 * ho / 25:.1f} L{ax.xc(15):.1f} {yflow + hf + 1:.1f}", stroke=INK, sw=1)
    d.t(40, ybot + 22, "Graf og tabell bruker samme kolonner. Kostnad = lager × 0,50 + restordre × 1,00, og Sum er de samme tallene lagt sammen. Kontrollert mot loggen for alle 36 uker.", 13, 400, INK2)

    # Etter Debriefen
    y = ybot + 66
    d.line(40, y - 28, 1960, y - 28, HAIR2, 1)
    d.t(40, y, "Etter Debriefen: samme kolonner, med simulert referanse", 22, 600, INK)
    d.t(40, y + 22, "Samme kjede, samme kunder. Grossist regner med alt på vei fra Uke 5. Simulert. Viser sammenhengen, ikke en fasit.", 14, 400, INK2)
    ax2 = Axis(190, 1110, 1, 36)
    y2 = y + 40
    week_row(d, ax2, y2 + 12, list(range(1, 37)), None, size=11)
    rr = [("Lager, spill 17", "net", G.net), ("Lager, simulert", "net", BARE.net),
          ("Sum kr, spill 17", "kr", G.kostsum), ("Sum kr, simulert", "kr", BARE.kostsum)]
    yb2 = matrix(d, ax2, y2 + 18, rr, 1, 36, rh=21, size=11, lx=40, lsize=13)
    yg = yb2 + 14
    hg = 110
    Yk = yscale(yg, hg, 0, 560)
    for v in (0, 200, 400):
        d.line(ax2.x0, Yk(v), ax2.x1, Yk(v), HAIR2 if v == 0 else HAIR, 1)
        d.t(ax2.x0 - 5, Yk(v) + 4, v, 12, 400, INK3, "end")
    for S_, col, sw, dash in ((G, INK, 2, None), (BARE, GREY, 2, None), (ALLE, GREY, 1.4, "5 4")):
        d.path("M" + " L".join(f"{ax2.xc(w):.1f} {Yk(S_.kostsum(w)):.1f}" for w in range(1, 37)), stroke=col, sw=sw, dash=dash)
    ly = [Yk(G.kostsum(36)) + 4, Yk(BARE.kostsum(36)) + 4, Yk(ALLE.kostsum(36)) + 4]
    for i in (1, 2):
        ly[i] = max(ly[i], ly[i - 1] + 16)
    d.t(ax2.xc(36) + 12, ly[0], f"Spill 17 {nf(G.kostsum(36))}", 13, 600, INK)
    d.t(ax2.xc(36) + 12, ly[1], f"Simulert, bare Sara {nf(BARE.kostsum(36))}", 13, 600, INK2)
    d.t(ax2.xc(36) + 12, ly[2], f"Simulert, alle fire {nf(ALLE.kostsum(36))}", 13, 400, INK2)
    d.t(40, yg + 30, "Grossist, sum kr", 13, 600, INK)
    d.t(40, yg + 47, "Stiplet: alle fire", 13, 400, INK2)
    d.t(40, yg + 63, "teller, simulert", 13, 400, INK2)

    tx = 1500
    B, A = FX["bare_sara_teller_paa_vei"], FX["alle_teller_paa_vei"]
    cols = [tx + 250, tx + 345, tx + 460]
    yy = y + 4
    d.t(cols[0], yy, "Spill 17", 14, 600, INK, "end")
    d.t(cols[1], yy, "Bare Sara", 14, 600, INK, "end")
    d.t(cols[2], yy, "Alle fire", 14, 600, INK, "end")
    d.line(tx, yy + 8, cols[2], yy + 8, HAIR2, 1)
    rr = [("Kjeden, kr", nf(K["kjedekost"]), nf(B["kjedekost"]), nf(A["kjedekost"])),
          ("Grossist, kr", nf(K["kost_per_rolle"]["Grossist"]), nf(B["kost_per_rolle"]["Grossist"]), nf(A["kost_per_rolle"]["Grossist"])),
          ("Forsterkning, Grossist", fx1(K["forsterkning"]["Grossist"]), fx1(B["forsterkning"]["Grossist"]), fx1(A["forsterkning"]["Grossist"])),
          ("Forsterkning, Fabrikk", fx1(K["forsterkning"]["Fabrikk"]), fx1(B["forsterkning"]["Fabrikk"]), fx1(A["forsterkning"]["Fabrikk"]))]
    yy += 30
    for row in rr:
        d.t(tx, yy, row[0], 14, 400, INK)
        for c_, v in zip(cols, row[1:]):
            d.t(c_, yy, v, 14, 400, INK, "end")
        d.line(tx, yy + 8, cols[2], yy + 8, HAIR, 1)
        yy += 26
    yy += 12
    d.t(tx, yy, "Hjelpegrad", 17, 600, INK)
    yy = d.para(tx, yy + 22, "Klassespill: kjeden og kolonnene med loggens egne tall. Ingen Posisjon-rad, ingen projeksjon.", 460, 14, 18, fill=INK)
    yy = d.para(tx, yy + 4, "Replay: raden Posisjon og projeksjonen åpnes, etter Debriefen.", 460, 14, 18, fill=INK)
    d.para(tx, yy + 6, "P5, P6, P7: forsterkningen faller også for de andre Rollene når ett ledd teller det som er på vei. Men å telle er ikke nok alene: en regel som jaget siste ordre for hardt, ga Fabrikk 12× i simuleringen.", 460, 13, 17, fill=INK2)
    d.demodata(1960, 1390, "Demodata. Simulerte referanser er merket Simulert.", 13, "end")
    d.save()


if __name__ == "__main__":
    build_06()
    build_10()
