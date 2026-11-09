"""Kjerneflatene: 05 spill, 06 spilldynamikk, 10 pedagogikk."""
from e06lib import *


def phone_body(d, S, wk, typed, sel=None, top=100, ncols=12, nh=92, rh=21, chain=True, typed_in_chain=None):
    """Telefonens tre lag på én kolonneakse: kjeden (kolonnen forstørret), meteogrammet og matrisen.
    sel er uka studenten har trykket på. Høyre kant er alltid nå + 4."""
    sel = sel or wk
    wmin = wk + 4 - ncols + 1
    ax = Axis(82, 292, wmin, wk + 4)
    tc = typed if sel == wk else S.order(sel)
    ch = seat_chain(d, 16, top, 358, S, sel, tc if typed_in_chain is None else typed_in_chain)
    ycol = ch["bottom"] + 30
    zoom(d, 16, 374, ch["bottom"] + 6, ax, sel, ycol)
    # flaten til høyre for nå
    rows = seat_rows(S, wk, typed)
    ynet = ycol + 10
    yweek = ynet + nh + 19
    ymat = yweek + 8
    ybot = ymat + len(rows) * rh
    d.rect(ax.xr(wk), ycol, ax.xr(wk + 4) - ax.xr(wk), ybot - ycol, TINT)
    # meteogrammet: netto lager
    Y = grid(d, ax, ynet, nh, -40, 30, (-20, 0, 20), 13, lx=76)
    net_area(d, ax, ynet, nh, S.net, wmin, wk, lw=1.8)
    d.circle(ax.xc(wk), Y(S.net(wk)), 3.5, BLUE if S.net(wk) >= 0 else RED, PAPER, 1.5)
    if sel != wk:
        d.circle(ax.xc(sel), Y(S.net(sel)), 4, PAPER, INK, 1.6)
    d.t(16, ynet + 12, "Lager", 13, 600, INK)
    d.t(16, ynet + nh - 4, "Restordre", 13, 600, INK)
    # tidsakse = kolonnetopp
    week_row(d, ax, yweek, list(range(wmin, wk + 5)), wk, sel)
    yend = matrix(d, ax, ymat, rows, wmin, wk + 4, rh=rh, lx=16, lsize=13)
    if typed is not None:
        diag(d, ax, wk, ymat + 4 * rh + 3, wk + 4, ymat + 2 * rh - 2)
    # nå-streken
    d.line(ax.xr(wk), ycol - 4, ax.xr(wk), ybot, INK, 1.4)
    d.t(ax.xr(wk) + 4, ycol + 2, "Nå", 13, 700, INK)
    col_box(d, ax, sel, ycol, ybot)
    return {"ax": ax, "ybot": ybot, "ymat": ymat, "chain": ch, "ycol": ycol}


def order_input(d, y, wk, typed, link="Kolonnen som regnestykke"):
    d.t(20, y + 22, f"Din ordre for Uke {wk}", 15, 600, INK)
    if link:
        d.link(370, y + 22, link, 14, "end")
    yb = y + 34
    d.rect(20, yb, 350, 54, PAPER, INK if typed is not None else HAIR2, 1.4, 6)
    d.line(76, yb, 76, yb + 54, HAIR2, 1)
    d.line(314, yb, 314, yb + 54, HAIR2, 1)
    d.line(39, yb + 27, 57, yb + 27, INK, 2)
    d.line(333, yb + 27, 351, yb + 27, INK, 2)
    d.line(342, yb + 18, 342, yb + 36, INK, 2)
    if typed is None:
        d.t(195, yb + 33, "Antall enheter", 17, 400, INK3, "middle")
    else:
        d.big(195, yb + 39, typed, 32, 700, INK, "middle")
    return yb + 54


def seat_sara_klar():
    return [("Detaljist", "Ida", "har bestilt", True), ("Distributør", "Mikkel", "har bestilt", True),
            ("Fabrikk", "Jonas", "venter, 3 min", False), ("Grossist", "Sara", "har bestilt", True)]


def phone_game(d, x, y, S, wk, typed, s=1.0, sel=None, state="input"):
    phone(d, x, y, s)
    game_header(d, wk, S.kostsum(wk))
    m = phone_body(d, S, wk, typed, sel=sel)
    yy = m["ybot"] + 14
    if state == "input":
        yb = order_input(d, yy, wk, typed)
        if typed is not None:
            d.button(20, yb + 10, 350, 50, f"Bekreft ordre på {typed}")
            d.t(20, yb + 82, f"Kommer fram om lag Uke {wk + 4}. Kan ikke endres etter", 13, 400, INK2)
            d.t(20, yb + 99, "at du har bekreftet. Venter på: Jonas (3 min) og deg.", 13, 400, INK2)
        else:
            d.button(20, yb + 10, 350, 50, "Bekreft ordre", primary=False)
            d.t(20, yb + 82, f"Trykk på en kolonne for å se den uka i kjeden over.", 13, 400, INK2)
    return m


# ---------- 05 ----------
def build_05():
    d = Doc("05-spill", 1600, 1000, "Uka som kolonne, hovedskjerm i Uke 11",
            "Saras telefon i Uke 11 med 24 tastet inn: kjeden er kolonnen for Uke 11 forstørret, meteogrammet og tabellen deler kolonnene. Ved siden av: samme skjerm etter trykk på Uke 8, laptop, og forskjellen mellom Klassespill og Replay.")
    d.t(40, 46, "Uke 11. Kjeden øverst er kolonnen for Uke 11, forstørret.", 26, 600, INK)

    # Telefon 1
    phone_game(d, 40, 84, G, 11, 24)
    d.demodata(20, 828)
    d.end()
    d.t(235, 960, "Telefon, Klassespill: kjede, graf og tall deler kolonnene.", 14, 400, INK2, "middle")

    # Telefon 2: trykk på Uke 8
    px = 460
    phone(d, px, 84, 1.0)
    d.t(20, 66, "Uke 8", 30, 700, INK)
    d.t(20, 88, "Du ser tilbake. Ordren for Uke 11 står.", 14, 400, INK2)
    d.link(370, 70, "Tilbake til Uke 11", 14, "end")
    m = phone_body(d, G, 11, 24, sel=8)
    c8, c7 = G.col(8), G.col(7)
    y = m["ybot"] + 36
    d.t(20, y, "Kolonnen for Uke 8 som regnestykke", 15, 600, INK)
    y += 28
    rows = [("Lager etter Uke 7", sg(c7["net"])), ("+ Levering", f"+ {c8['lev']}"), ("− Ordre inn", f"− {c8['inn']}")]
    for lab, v in rows:
        d.t(20, y, lab, 15, 400, INK)
        d.t(370, y, v, 15, 600, INK, "end")
        y += 24
    d.line(20, y - 16, 370, y - 16, INK, 1)
    d.t(20, y + 2, "Lager etter Uke 8", 15, 600, INK)
    d.t(370, y + 2, sg(c8["net"]), 15, 700, INK, "end")
    y += 30
    d.t(20, y, f"Kostnad Uke 8: {c8['lager']} på lager × 0,50 = {nf(c8['kost'])} kr", 13, 400, INK2)
    d.demodata(20, 828)
    d.end()
    d.t(655, 960, "Trykk på en tidligere kolonne: kjeden viser den uka.", 14, 400, INK2, "middle")

    # Laptop
    lx, ly, lw, lh = 880, 84, 680, 470
    d.rect(lx, ly, lw, lh, PAPER, HAIR2, 1.4, 10)
    d.t(lx + 24, ly + 40, "Uke 11", 26, 700, INK)
    d.t(lx + 104, ly + 40, "Grossist, Spill 17", 14, 400, INK2)
    d.t(lx + lw - 24, ly + 40, f"Totalkostnad {nf(G.kostsum(11))} kr", 14, 600, INK, "end")
    # venstre: kjede + meteogram + matrise, uke 1 til 15
    ax = Axis(lx + 96, 400, 1, 15)
    ch = seat_chain(d, lx + 24, ly + 56, 400, G, 11, 24, u=1.3, yb_off=78)
    ycol = ch["bottom"] + 22
    zoom(d, lx + 24, lx + 424, ch["bottom"] + 4, ax, 11, ycol)
    rows = seat_rows(G, 11, 24)
    nh = 70
    ynet = ycol + 8
    yweek = ynet + nh + 17
    ymat = yweek + 6
    rh = 19
    ybot = ymat + len(rows) * rh
    d.rect(ax.xr(11), ycol, ax.xr(15) - ax.xr(11), ybot - ycol, TINT)
    Y = grid(d, ax, ynet, nh, -40, 30, (-20, 0, 20), 12)
    net_area(d, ax, ynet, nh, G.net, 1, 11, lw=1.6)
    d.t(lx + 24, ynet + 11, "Lager", 12, 600, INK)
    d.t(lx + 24, ynet + nh - 3, "Restordre", 12, 600, INK)
    week_row(d, ax, yweek, list(range(1, 16)), 11, size=12)
    matrix(d, ax, ymat, rows, 1, 15, rh=rh, size=12, lx=lx + 24, lsize=12)
    diag(d, ax, 11, ymat + 4 * rh + 3, 15, ymat + 2 * rh - 2)
    d.line(ax.xr(11), ycol - 4, ax.xr(11), ybot, INK, 1.4)
    col_box(d, ax, 11, ycol, ybot)
    # høyre: ordre
    cx = lx + 520
    cw = lx + lw - 24 - cx
    y = ly + 80
    d.t(cx, y, "Din ordre for Uke 11", 14, 600, INK)
    d.rect(cx, y + 10, cw, 50, PAPER, INK, 1.4, 6)
    d.big(cx + cw / 2, y + 46, 24, 30, 700, INK, "middle")
    d.button(cx, y + 72, cw, 44, "Bekreft ordre på 24", size=15)
    y = d.para(cx, y + 142, "Kommer fram om lag Uke 15. Kan ikke endres etter at du har bekreftet.", cw, 13, 18, fill=INK2)
    y = d.para(cx, y + 8, "Venter på: Jonas (3 min) og deg.", cw, 13, 18, fill=INK2)
    y = d.para(cx, y + 16, "Trykk på en kolonne for å se uka i kjeden. Hold over en celle for regnestykket.", cw, 13, 18, fill=INK2)
    d.demodata(lx + lw - 24, ly + lh - 14, a="end")

    # Hjelpegrad
    hy = 612
    d.t(lx, hy, "Hjelpegrad: samme kolonner på to nivåer", 20, 600, INK)
    d.para(lx, hy + 24, "Klassespillet viser bare det loggen inneholder. Raden Posisjon kommer først i Replay, etter Debriefen.", lw, 14, 19, fill=INK2)
    pw = 330
    for i, (title, pos) in enumerate((("Klassespill", False), ("Replay, etter Debriefen", True))):
        bx = lx + i * (pw + 20)
        d.t(bx, hy + 74, title, 14, 600, INK)
        axh = Axis(bx + 76, pw - 76, 8, 15)
        rr = seat_rows(G, 11, 24, pos=pos, cost=False, sumrow=False)
        if pos:
            # Med ordren: posisjonen etter beslutningen står i nå-kolonnen
            base = rr[-1][2]
            rr[-1] = ("Posisjon", "plain", lambda w, base=base: (f"{G.posisjon(11)}→{G.posisjon(11) + 24}" if w == 11 else base(w)))
        y0 = hy + 92
        week_row(d, axh, y0 + 12, list(range(8, 16)), 11, size=12)
        ybh = y0 + 18 + len(rr) * 19
        d.rect(axh.xr(11), y0 + 18, axh.xr(15) - axh.xr(11), ybh - y0 - 18, TINT)
        matrix(d, axh, y0 + 18, rr, 8, 15, rh=19, size=12, lx=bx, lsize=12)
        d.line(axh.xr(11), y0 + 14, axh.xr(11), ybh, INK, 1.2)
        if pos:
            d.rect(axh.x0 - 76, ybh - 19, pw, 19, "none", INK, 1, 2)
    d.para(lx, hy + 266, f"I Klassespillet står {G.paavei(11)} på vei rett under restordren {G.rest[10]}. Summen må Sara gjøre selv.", pw, 13, 18, fill=INK2)
    d.para(lx + pw + 20, hy + 266, f"I Replay står summen som egen rad: {G.lager[10]} − {G.rest[10]} + {G.paavei(11)} = {G.posisjon(11)}, og {G.posisjon(11) + 24} med ordren. Ingen fasit.", pw, 13, 18, fill=INK2)
    d.save()
