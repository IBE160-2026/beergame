"""06 spilldynamikk og 10 pedagogikk."""
from vlib import *
from screens_core import NAME, phone, game_header, phone_top, phone_main, order_input, waiting_rows, seat_sara_klar


# ---------- 06 ----------
def build_06():
    d = Doc("06-spilldynamikk", 2100, 1200, f"{NAME}, en Uke i spillet",
            "Seks telefonruter: Uka åpner, beslutningen, bekreftet, Uka går videre, Jonas er borte, spillet slutter. "
            "Hver rute har kjedebånd, graf og tabell på samme ukeakse.")
    s = 0.8
    pw = 390 * s
    gapx = (2100 - 80 - 6 * pw) / 5
    y0 = 176
    d.t(40, 50, "En Uke i Graf over tabell: kolonnen fylles, nå-streken flytter seg, og tallene blir historie.", 28, 600, INK)
    notes = [
        ("A  Uka åpner", "Ny kolonne: levering og ordre inn står allerede der. Cellen under Din ordre er tom og stiplet."),
        ("B  Beslutningen: 24", "Sara taster 24 med 16 på vei. Tallet står i to celler: nå under Din ordre, og i Uke 15 under Levering."),
        ("C  Bekreftet", "Ordren er låst. Skjermen sier hvem Uka venter på, med Rolle, navn og hvor lenge."),
        ("D  Uka går videre", "Nå-streken flytter én kolonne. Under 2 sekunder, og kan hoppes over. Kostnad så langt er ett trykk unna."),
        ("E  Jonas er borte", "Pause, så bestiller KI-spiller for Fabrikk, alltid merket. Jonas kan ta setet tilbake."),
        ("F  Spillet slutter", "Kjedens totalkostnad først, så per Rolle og per kostnadsart. Videre til Debrief."),
    ]

    def px(i):
        return 40 + i * (pw + gapx)

    for i, (h, n) in enumerate(notes):
        d.t(px(i), 94, h, 20, 600, INK)
        d.para(px(i), 120, n, pw, 15, 20, fill=INK2)

    # A
    phone(d, px(0), y0, s)
    phone_main(d, 11, None, "open")
    d.demodata(20, 826)
    d.end()
    # B
    phone(d, px(1), y0, s)
    phone_main(d, 11, 24, "typed")
    d.demodata(20, 826)
    d.end()
    # C
    phone(d, px(2), y0, s)
    m = phone_top(d, G, 11, 24)
    y = m["ybot"] + 30
    d.t(20, y, "Ordren på 24 er sendt. Venter på Jonas.", 15, 600, INK)
    waiting_rows(d, y + 34, seat_sara_klar())
    d.t(20, y + 166, "Du får beskjed når Uke 12 åpner.", 13, 400, INK2)
    d.demodata(20, 826)
    d.end()
    # D
    w = 12
    phone(d, px(3), y0, s)
    m = phone_top(d, G, w, None)
    ax = m["ax"]
    d.line(ax.xr(11), m["ynet"] - 4, ax.xr(11), m["ybot"], INK3, 1, dash="2 3")
    y = m["ybot"] + 30
    d.t(20, y, "Uke 11 er ferdig regnet", 15, 600, INK)
    d.t(370, y, "Hopp over", 14, 600, BLUE, "end", 'text-decoration="underline"')
    yy = y + 30
    for lab, v in (("Levering", G.levering(w)), ("Ordre inn", G.inn(w)), ("Sendt", G.sendt(w)),
                   ("Restordre", f"{G.rest[w - 2]} blir {G.rest[w - 1]}")):
        d.t(20, yy, lab, 14, 400, INK)
        d.t(370, yy, v, 14, 600, INK, "end")
        d.line(20, yy + 7, 370, yy + 7, HAIR, 1)
        yy += 25
    d.t(20, yy + 4, week_sum(G, w), 14, 600, INK)
    d.t(20, yy + 30, "Kostnad så langt", 14, 600, BLUE, "start", 'text-decoration="underline"')
    d.demodata(20, 826)
    d.end()
    # E
    w = 14
    phone(d, px(4), y0, s)
    m = phone_top(d, G, w, G.order(w))
    y = m["ybot"] + 28
    d.t(20, y, "Pause: Jonas har ikke bestilt på 24 t.", 15, 600, INK)
    rows = [("Detaljist", "Ida", "har bestilt", True), ("Distributør", "Mikkel", "har bestilt", True),
            ("Fabrikk", "KI-spiller", "bestiller for Jonas", False), ("Grossist", "Sara", "har bestilt", True)]
    yy = waiting_rows(d, y + 30, rows, lh=25)
    d.rect(20, yy - 6, 350, 74, TINT, None, 1, 6)
    d.t(32, yy + 16, "Jonas ser dette når hen er tilbake:", 13, 400, INK2)
    d.t(32, yy + 38, "KI-spiller har bestilt for deg.", 14, 600, INK)
    d.button(244, yy + 18, 116, 38, "Ta tilbake setet", primary=False, size=13)
    d.demodata(20, 826)
    d.end()
    # F
    phone(d, px(5), y0, s)
    d.t(20, 62, "Spillet er ferdig", 30, 700, INK)
    d.t(20, 84, "Grossist, Spill 17", 14, 400, INK2)
    d.t(20, 128, "Kjedens totalkostnad", 15, 400, INK2)
    d.t(20, 170, f"{nf(K['kjedekost'])} kr", 40, 700, INK, extra='style="font-variant-numeric:lining-nums proportional-nums"')
    d.t(20, 194, "Fire Roller, to kostnadsarter, hele spillet.", 13, 400, INK2)
    y, tl, tr = chain_bill_table(d, 20, 230, 350, K, size=14, lh=30, sim=False)
    y += 34
    d.t(20, y, "Kjedens kostnad over tid", 14, 600, INK)
    ch = ChainSum(SEATS)
    axf = Axis(56, 314, 1, 36)
    top = nice_top(ch.sum_lk(36) + ch.sum_rk(36))
    Yf = cum_cost_area(d, axf, y + 14, 92, ch, 1, 36, top)
    for v in (0, top // 2, top):
        d.t(axf.x0 - 5, Yf(v) + 4, nf(v, 0), 13, 400, INK3, "end")
        if v:
            d.line(axf.xc(1), Yf(v), axf.xc(36), Yf(v), HAIR, 1)
    d.t(axf.xc(1), y + 124, "Uke 1", 13, 400, INK3)
    d.t(axf.xc(36), y + 124, "Uke 36", 13, 400, INK3, "end")
    d.t(axf.xc(22), Yf(ch.sum_lk(22) + ch.sum_rk(22) * 0.35), "restordre", 13, 600, RED, "middle")
    d.t(axf.xc(33), Yf(ch.sum_lk(33) * 0.45), "lager", 13, 600, BLUE, "middle")
    d.t(20, y + 152, "Hvorfor ble den slik? Det finner dere ut", 14, 400, INK2)
    d.t(20, y + 171, "i Debriefen, med alle fire Rollene.", 14, 400, INK2)
    d.button(20, 740, 350, 52, "Gå til Debrief")
    d.demodata(20, 826)
    d.end()

    # Under
    yt = y0 + 844 * s + 50
    d.t(40, yt, "Hva spilleren lærer av å se kjeden, grafen og kostnaden uke for uke", 24, 600, INK)
    tekst = [
        "Hver uke er én kolonne, med samme skala hver gang. Streken viser formen, cellen under viser tallet. Det ene kan alltid kontrolleres med det andre.",
        "Kolonnen regnes nedover: netto lager forrige uke, pluss levering, minus ordre inn. Det er materialbalansen som regnestykke, ikke bare som mønster (P1).",
        "Ordren står to ganger i tabellen: i Din ordre nå, og i Levering fire kolonner senere. Det som kommer nå, ble bestemt før (P2). Kjedebåndet viser det som er på vei som bokser på røret (P3).",
        "Kost per uke er både stolpe og tall. Rød stolpe er restordre til 1,00, blå er lager til 0,50. Sara ser bare sin egen regning til spillet er ferdig (P8).",
    ]
    colw = (2100 - 80 - 3 * 40) / 4
    for i, tx in enumerate(tekst):
        d.para(40 + i * (colw + 40), yt + 34, tx, colw, 16, 22, fill=INK)
    ys = yt + 158
    d.t(40, ys, f"Raden Levering sett fra fem Uker: 24 rykker mot nå-streken, og i Uke 15 kom det {G.levering(15)}.", 17, 600, INK)
    pw2 = (2100 - 80 - 4 * 30) / 5
    for i, wk in enumerate(range(11, 16)):
        xx = 40 + i * (pw2 + 30)
        ax = Axis(xx + 64, pw2 - 64, wk - 3, wk + 4)
        y1 = ys + 16
        rh = 22
        d.rect(ax.xr(wk), y1, ax.xr(wk + 4) - ax.xr(wk), rh * 2, TINT)
        d.t(xx, y1 + 15, "Uke", 13, 600, INK2)
        d.t(xx, y1 + rh + 15, "Levering", 13, 400, INK)
        for k in range(wk - 3, wk + 5):
            d.t(ax.xc(k), y1 + 15, k, 13, 700 if k == wk else 400, INK if k == wk else INK3, "middle")
            if k <= wk:
                v = G.levering(k)
                d.t(ax.xc(k), y1 + rh + 15, v, 13, 700 if k == 15 else 400, INK, "middle")
        typed = 24 if wk == 11 else G.order(wk)
        for week, q in G.arrivals(wk, typed):
            is24 = week == 15
            d.rect(ax.xl(week) + 1.5, y1 + rh + 2, ax.slot - 3, rh - 4, PAPER, INK if is24 else BLUE, 1.5 if is24 else 1, 2)
            d.t(ax.xc(week), y1 + rh + 15, q, 13, 700 if is24 else 400, INK, "middle")
        if wk == 15:
            d.rect(ax.xl(15) + 1.5, y1 + rh + 2, ax.slot - 3, rh - 4, "none", INK, 1.2, 2, 'stroke-dasharray="3 2"')
        d.line(ax.xr(wk), y1 - 4, ax.xr(wk), y1 + 2 * rh + 2, INK, 1.2)
        d.line(xx, y1 + rh, ax.xr(wk + 4), y1 + rh, HAIR, 1)
        cap = {11: "Uke 11: 24 bestilt", 12: "Uke 12: tre kolonner unna", 13: "Uke 13: to kolonner unna",
               14: "Uke 14: neste kolonne", 15: f"Uke 15: {G.levering(15)} kom, {G.overdue(15)} forsinket"}[wk]
        d.t(xx, y1 + 2 * rh + 22, cap, 14, 400, INK2)
    d.save()


# ---------- 10 ----------
def build_10():
    d = Doc("10-pedagogikk", 2000, 1400, f"{NAME}, grafgrammatikken over tid",
            "Saras kjedebånd, graf og tabell i Uke 5, 11, 18 og 29 på én felles ukeakse, med prinsippene P1 til P8 merket, "
            "og sammenligningen med simulert referanse slik den vises etter Debriefen.")
    d.t(40, 52, "Samme graf over tabell i fire Uker av Saras spill", 34, 700, INK)
    d.para(40, 84, "Radene deler ukeakse, så nå-streken vandrer mot høyre. Det som sto som kjente ankomster til høyre for streken, står som historie i raden under. Hver strek har et tall rett under seg.", 1440, 16, 22, fill=INK2)

    keyx = 1530
    rows = [
        (5, G.order(5), [
            ("P2 Forsinkelse", "Alt er 4, og kolonnene er like. Det som kommer i Uke 7, er ikke synlig fra Saras plass ennå."),
            ("P4 Ordrer er ikke etterspørsel", "Raden Ordre inn er det Ida bestilte, ikke det kundene gjorde. Sara har ingen annen kilde."),
            ("Til neste ordre", "En rolig rad betyr bare at ingenting har nådd deg ennå."),
        ]),
        (11, 24, [
            ("P1 Lager er en opphopning", f"Kolonne 11 regnes nedover: {sg(G.net(10))} + {G.levering(11)} levert − {G.inn(11)} inn = {sg(G.net(11))}. Rammen viser de tre cellene."),
            ("P3 Det som er på vei", f"Kjedebåndet har {G.paavei(11)} på røret. Lager {G.lager[10]} − restordre {G.rest[10]} + {G.paavei(11)} = {G.posisjon(11)}. Med 24 blir det {G.posisjon(11) + 24}."),
            ("Til neste ordre", f"I Levering-raden står 24 i Uke 15. Raden under viser at det kom {G.levering(15)}: bestilt er ikke levert."),
        ]),
        (18, G.order(18), [
            ("P3 og P2 igjen. Skalaregel", f"{G.paavei(18)} på vei, og {G.overdue(18)} av dem er over fire uker gamle. Kjente ankomster står på sann skala; de {G.overdue(18)} uten dato får fast bredde og merket brudd, så båndet passer på telefonen."),
            ("P7 Overreaksjon forsterker", "En ny ordre kommer ikke raskere enn de gamle. Den legger seg bakerst, og leverandøren får et større tall å svare på."),
            ("P8 Restordre koster dobbelt", f"Kost per uke er {nf(G.ukekost(18))} kr. Sum hittil {nf(G.kostsum(18))} kr, nesten alt restordre."),
        ]),
        (29, G.order(29), [
            ("P8 Samme mengde, halv pris", f"Lager {G.lager[28]} × 0,50 = {nf(G.lagerkost(29))} kr. Restordre {max(G.rest)} kostet {nf(max(G.rest) * 1.0)} kr per uke. Begge teller."),
            ("P1 Samme regning, motsatt fortegn", "Leveringene i Uke 23 til 26 er gamle ordrer som kom nesten samtidig. Tabellen viser hvilke."),
            ("Til neste ordre", "Kost per uke synker bare når lageret tæres. Hvor mye du vil ha igjen, må du bestemme selv."),
        ]),
    ]
    y = 132
    gx, gw = 570, 920
    rh_row = 228
    for now, typed, notes in rows:
        d.t(40, y + 24, f"Uke {now}", 26, 700, INK)
        lab = f"Lager {G.lager[now - 1]}" if G.net(now) >= 0 else f"Restordre {G.rest[now - 1]}"
        d.t(40, y + 48, lab, 15, 600, INK)
        d.t(40, y + 68, f"På vei {G.paavei(now)}", 15, 400, INK2)
        d.t(40, y + 88, f"Posisjon {sg(G.posisjon(now))}", 15, 400, INK2)
        chain_seat(d, G, 190, y + 6, 350, now, typed, ls=12)
        cost_panel_wide(d, 40, y + 122, 500, G, now, top=600)
        m = gtable(d, G, gx, y, gw, now, typed, wmin=1, wmax=36, lw=96, ls=12, rh=15, hn=62, hc=22, gapf=4,
                   rows=("inn", "lev", "net", "pv", "ord", "kost"), labels={"kost": "Kost per uke"},
                   titles=False, netlabel=False, cost_tick=False, hlcol=11 if now == 11 else None)
        d.t(gx, m["ynet"] + 12, "Netto lager", 12, 600, INK)
        d.t(gx, m["ycost"] + 12, "Kost per uke", 12, 600, INK)
        ny = y + 14
        for head, body in notes:
            d.t(keyx, ny, head, 15, 600, INK)
            ny = d.para(keyx, ny + 19, body, 430, 14, 18, fill=INK2) + 6
        d.line(40, y + rh_row - 8, 1960, y + rh_row - 8, HAIR, 1)
        y += rh_row

    # Etter Debriefen
    y += 6
    ny = d.para(40, y + 22, "Etter Debriefen: samme graf over tabell, med simulert referanse", 480, 24, 30, 600, INK)
    d.para(40, ny + 2, "Samme kjede, samme kunder. Simulert: Sara teller alt som er på vei. Viser sammenhengen, ikke en fasit.", 480, 15, 20, fill=INK2)
    ax = Axis(gx + 96, gw - 96, 1, 36)
    gy, gh = y + 30, 112
    Y = grid(d, ax, gy, gh, -40, 30, (-40, -20, 0, 20), 12)
    net_area(d, ax, gy, gh, G.net, 1, 36)
    d.path(pts_path([(ax.xc(w), Y(BARE.net(w))) for w in range(1, 37)]), stroke=INK, sw=1.6)
    d.path(pts_path([(ax.xc(w), Y(ALLE.net(w))) for w in range(1, 37)]), stroke=GREY, sw=1.4, dash="5 3")
    d.t(ax.xc(17), Y(-38) + 4, "Spill 17", 13, 600, RED, "end")
    d.t(ax.xc(31), Y(BARE.net(31)) - 8, "Simulert, bare Sara", 13, 600, INK, "middle")
    d.t(ax.xc(24), Y(ALLE.net(24)) + 18, "Simulert, alle fire", 13, 600, GREY, "middle")
    d.t(gx, gy + 12, "Netto lager", 12, 600, INK)
    ty = gy + gh + 6
    trh = 17
    trows = [("Uke", None), ("Spill 17", G), ("Simulert", BARE)]
    for i, (lab, S) in enumerate(trows):
        ry = ty + i * trh
        base = ry + trh / 2 + 12 * 0.36
        d.t(gx, base, lab if S is None else f"Netto, {lab}", 12, 600 if S is None else 400, INK2 if S is None else INK)
        if S is not None:
            d.line(gx, ry, ax.x1, ry, HAIR, 1)
        for k in range(1, 37):
            if S is None:
                if k % 2 == 1 or k == 36:
                    d.t(ax.xc(k), base, k, 12, 400, INK3, "middle")
                continue
            f, c = net_cell(S.net(k))
            d.rect(ax.xl(k) + 0.75, ry + 1.5, ax.slot - 1.5, trh - 3, f)
            d.t(ax.xc(k), base, sg(S.net(k)), 12, 400, c, "middle")
    for i, (lab, S) in enumerate((("Sum kr, Spill 17", G), ("Sum kr, Simulert", BARE))):
        ry = ty + (3 + i) * trh
        base = ry + trh / 2 + 12 * 0.36
        d.line(gx, ry, ax.x1, ry, HAIR, 1)
        d.t(gx, base, lab, 12, 400, INK)
        for k in range(1, 37):
            if k % 3 == 0:
                d.t(ax.xc(k), base, sg(int(S.kostsum(k) + 0.5)), 12, 600 if k == 36 else 400, INK, "middle")
    d.line(gx, ty + 5 * trh, ax.x1, ty + 5 * trh, HAIR, 1)
    d.t(gx, ty + 5 * trh + 18, "Summen vises hver tredje uke for å holde cellene lesbare. Uke 36 er sluttsummen.", 12, 400, INK2)

    # Sammenligning og hjelpegrad
    B, A = FX["bare_sara_teller_paa_vei"], FX["alle_teller_paa_vei"]
    tx = 40
    yy = y + 136
    cols = [tx + 300, tx + 400, tx + 500]
    for c, h in zip(cols, ("Spill 17", "Bare Sara", "Alle fire")):
        d.t(c, yy, h, 13, 600, INK, "end")
    d.line(tx, yy + 7, cols[2], yy + 7, HAIR2, 1)
    yy += 24
    gl = [Seat("Grossist", s_) for s_ in (K, B, A)]
    rr = [("Kjeden, kr", [nf(s_["kjedekost"]) for s_ in (K, B, A)]),
          ("Grossist, lagerkost", [nf(s_.sum_lk()) for s_ in gl]),
          ("Grossist, restordrekost", [nf(s_.sum_rk()) for s_ in gl]),
          ("Forsterkning, Grossist", [fx1(s_["forsterkning"]["Grossist"]) for s_ in (K, B, A)]),
          ("Forsterkning, Fabrikk", [fx1(s_["forsterkning"]["Fabrikk"]) for s_ in (K, B, A)])]
    for lab, vals in rr:
        d.t(tx, yy, lab, 13, 400, INK)
        for c, v in zip(cols, vals):
            d.t(c, yy, v, 13, 400, INK, "end")
        d.line(tx, yy + 7, cols[2], yy + 7, HAIR, 1)
        yy += 21
    d.t(tx, yy + 8, "Simulert. P3, P5, P6, P8.", 12, 400, INK3)

    d.t(keyx, y + 22, "Hjelpegrad", 20, 600, INK)
    ny = d.para(keyx, y + 48, "Klassespill: kjedebånd, graf og tabell med Netto lager og På vei i hver sin rad. Summen må Sara regne selv.", 430, 15, 20, fill=INK)
    ny = d.para(keyx, ny + 6, "Replay: raden Posisjon og den stiplede linja åpnes. Studenten har da kjent på hva summen betyr, og bruker den.", 430, 15, 20, fill=INK)
    ny = d.para(keyx, ny + 10, "P7: Å telle det som er på vei er ikke nok alene. I simuleringen ga en regel som jaget siste ordre for hardt, Fabrikk høyere forsterkning (12×) enn spill 17.", 430, 14, 18, fill=INK2)
    d.demodata(1960, 1390, "Demodata. Simulerte referanser er merket Simulert.", 13, "end")
    d.save()


if __name__ == "__main__":
    build_06()
    build_10()
