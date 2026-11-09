"""Kjerneflatene: 05 spill, 06 spilldynamikk, 10 pedagogikk."""
from vlib import *

NAME = "Graf over tabell"


def phone(d, x, y, s=1.0):
    """Åpner en telefonflate i 390×844-skala. Husk d.end()."""
    d.rect(x, y, 390 * s, 844 * s, PAPER, HAIR2, 1.4, 36 * s)
    d.g(f"translate({x},{y}) scale({s})")


def game_header(d, wk, kost, role="Grossist", spill="Spill 17", x=20):
    d.t(x, 62, f"Uke {wk}", 30, 700, INK)
    d.t(x, 84, f"{role}, {spill}", 14, 400, INK2)
    d.t(370, 58, "Totalkostnad", 13, 400, INK2, "end")
    d.t(370, 80, f"{nf(kost)} kr", 18, 600, INK, "end")


def phone_top(d, g, wk, typed, rows=("inn", "lev", "net", "ord", "kost"), hn=92, proj=False):
    """Kjedebånd, graf og tabell for setet. Felles for alle telefonrutene."""
    game_header(d, wk, g.kostsum(wk))
    yb = chain_seat(d, g, 16, 100, 358, wk, typed)
    m = gtable(d, g, 16, yb + 14, 358, wk, typed, wmin=wk - 7, wmax=wk + 4, lw=76, hn=hn, hc=30, rh=20,
               rows=rows, ticks=(-40, -20, 0, 20), proj=proj)
    return m


def order_input(d, y, wk, typed, link="Alle rader og kostnad"):
    d.t(20, y + 22, f"Din ordre for Uke {wk}", 15, 600, INK)
    if link:
        d.t(370, y + 22, link, 14, 600, BLUE, "end", 'text-decoration="underline"')
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
        d.t(195, yb + 39, typed, 32, 700, INK, "middle")
    return yb + 54


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


def phone_main(d, wk=11, typed=24, state="typed"):
    """Hovedskjermen på telefon. state: open, typed, confirmed."""
    g = G
    m = phone_top(d, g, wk, typed if state != "open" else None)
    y = m["ybot"] + 8
    if state in ("open", "typed"):
        yb = order_input(d, y, wk, typed if state == "typed" else None)
        if state == "typed":
            d.t(20, yb + 22, f"Kommer fram om lag Uke {wk + 4}. Kan ikke endres etter", 13, 400, INK2)
            d.t(20, yb + 39, "at du har bekreftet.", 13, 400, INK2)
            d.button(20, yb + 52, 350, 50, f"Bekreft ordre på {typed}")
        else:
            d.t(20, yb + 22, f"Sist Uke bestilte du {g.order(wk - 1)}.", 13, 400, INK2)
            d.button(20, yb + 52, 350, 50, "Bekreft ordre", primary=False)
        d.t(20, yb + 128, "Venter på: Jonas (3 min) og deg.", 13, 400, INK2)
    return m


# ---------- 05 ----------
def build_05():
    d = Doc("05-spill", 1600, 1000, f"{NAME}, hovedskjerm i Uke 11",
            "Saras telefon i Uke 11 med 24 tastet inn: kjedebånd øverst, graf over tabell på samme ukeakse, ordrefelt. "
            "Ved siden av: alle rader og Kostnad så langt åpnet, laptop i Labtime med kostnadspanelet ved ordrefeltet, "
            "og forskjellen mellom Klassespill og Replay.")
    d.t(40, 46, "Uke 11. Hver uke er en kolonne: streken over, tallet under, og 24 står både der det bestilles og der det kommer.", 24, 600, INK)

    # Telefon
    phone(d, 40, 80, 1.0)
    phone_main(d, 11, 24, "typed")
    d.demodata(370, 826, a="end")
    d.end()
    d.para(235, 948, "Telefon, Klassespill: ledd, graf og tabell deler kolonner. Trykk på Totalkostnad eller lenken for neste flate.", 360, 14, 19, fill=INK2, a="middle")

    # Åpnet: alle rader og kostnad
    px = 460
    phone(d, px, 80, 1.0)
    d.t(20, 62, "Alle rader, Uke 11", 24, 700, INK)
    d.t(370, 58, "Lukk", 15, 600, BLUE, "end", 'text-decoration="underline"')
    d.t(20, 84, "Grossist, Spill 17", 14, 400, INK2)
    m = gtable(d, G, 16, 104, 358, 11, 24, wmin=4, wmax=15, lw=96, hn=58, hc=22, rh=21, gapf=6,
               rows=("inn", "lev", "sendt", "lager", "rest", "net", "pv", "ord", "kost"),
               labels={"kost": "Kost per uke"}, cost_title=False, t_net="Netto lager")
    y = m["ybot"] + 26
    d.t(20, y, "Netto lager i kolonne 11", 14, 400, INK)
    d.t(370, y, f"{sg(G.net(10))} + {G.levering(11)} − {G.inn(11)} = {sg(G.net(11))}", 14, 600, INK, "end")
    d.line(20, y + 20, 370, y + 20, HAIR, 1)
    cost_panel(d, 20, y + 50, 350, G, 11, h=70, size=14, lh=30)
    d.demodata(20, 826)
    d.end()
    d.para(655, 948, "Ett trykk unna: alle radene, og Kostnad så langt med regnestykket for uka.", 360, 14, 19, fill=INK2, a="middle")

    # Laptop
    lx, ly, lw, lh = 880, 80, 680, 576
    d.rect(lx, ly, lw, lh, PAPER, HAIR2, 1.4, 10)
    d.t(lx + 24, ly + 40, "Uke 11", 26, 700, INK)
    d.t(lx + 106, ly + 40, "Grossist, Spill 17", 14, 400, INK2)
    d.t(lx + lw - 24, ly + 40, f"Totalkostnad {nf(G.kostsum(11))} kr", 15, 600, INK, "end")
    cw = 412
    yb = chain_seat(d, G, lx + 20, ly + 58, cw, 11, 24)
    gtable(d, G, lx + 20, yb + 14, cw, 11, 24, wmin=1, wmax=15, lw=86, hn=84, hc=26, rh=20, gapf=6,
           rows=("inn", "lev", "sendt", "net", "pv", "ord", "kost"), cost_title=False,
           t_net="Netto lager og kost per uke")
    cx = lx + cw + 38
    rw = lx + lw - 24 - cx
    y = ly + 80
    d.t(cx, y, "Din ordre for Uke 11", 14, 600, INK)
    d.rect(cx, y + 10, rw, 50, PAPER, INK, 1.4, 6)
    d.t(cx + rw / 2, y + 46, 24, 30, 700, INK, "middle")
    d.button(cx, y + 70, rw, 44, "Bekreft ordre på 24", size=15)
    yy = d.para(cx, y + 136, "Kommer fram om lag Uke 15. Kan ikke endres etter at du har bekreftet.", rw, 13, 17, fill=INK2)
    d.t(cx, yy + 2, "Venter på: Jonas (3 min) og deg.", 13, 400, INK2)
    d.line(cx, yy + 22, cx + rw, yy + 22, HAIR2, 1)
    cost_panel(d, cx, yy + 50, rw, G, 11, h=76, size=13, lh=28)
    d.demodata(lx + 24, ly + lh - 14)
    d.t(lx + lw / 2, ly + lh + 22, "Laptop i Labtime: samme kolonner, og Kostnad så langt står alltid ved ordrefeltet.", 14, 400, INK2, "middle")

    # Hjelpegrad
    hy = ly + lh + 66
    d.t(lx, hy, "Hjelpegrad: samme kolonne, to nivåer", 20, 600, INK)
    pw = 330
    for i, (title, rows, proj) in enumerate((
            ("Klassespill: delene, ikke summen", ("lev", "net", "pv", "ord"), False),
            ("Replay, etter Debriefen: Posisjon og linje", ("lev", "net", "pv", "pos", "ord"), True))):
        bx = lx + i * (pw + 20)
        d.t(bx, hy + 26, title, 14, 600, INK)
        gtable(d, G, bx, hy + 38, pw, 11, 24, wmin=6, wmax=15, lw=66, hn=56, rh=18, cost_field=False,
               rows=rows, proj=proj, titles=False, netlabel=False, labels={"ord": "Ordre"}, ord_label="Ordre")
    yn = hy + 38 + 56 + 4 + 6 * 18 + 22
    d.para(lx, yn, "Netto lager og På vei står i hver sin rad, men summen må Sara regne selv.", pw, 13, 17, fill=INK2)
    d.para(lx + pw + 20, yn, f"Posisjon-raden og den stiplede linja åpnes: {G.posisjon(11)} + 24 − 4 × {G.inn(11)} = {sg(G.projection(11, 24)[-1][1])} hvis ordre inn holder seg. Ikke garantert.", pw, 13, 17, fill=INK2)
    d.save()
