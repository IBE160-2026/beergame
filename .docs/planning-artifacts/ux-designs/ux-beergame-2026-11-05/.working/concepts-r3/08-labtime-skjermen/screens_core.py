"""Kjerneflatene: 05 spill, 06 spilldynamikk, 10 pedagogikk. Rutenettet: Kjede, Graf, Tall, Kostnad, Ordre."""
from e08grid import *

NAME = "Labtime-skjermen"


def flow_title(d, x, y, g, wk, ls=13):
    lev, inn = g.levering(wk), g.inn(wk)
    first = ("Levering", lev, BASE)
    second = ("Ordre inn", inn, RED if inn > lev else BASE)
    if lev > inn:
        first, second = ("Ordre inn", inn, BASE), ("Levering", lev, BLUE)
    xx = x
    for lab, val, col in (first, second):
        d.rect(xx, y - ls + 3, 10, 10, col)
        s = f"{lab} {val}"
        d.t(xx + 14, y, s, ls, 600, INK)
        xx += 14 + text_w(s, ls) + 14


def fmt_cost(v):
    return str(int(v)) if v == int(v) else nf(v, 1)


def seat_rows(g, wk, typed, pos=False, cost=True, short=False):
    """Setets tabell. Kolonnene er de samme ukene som i grafen over. Til høyre for nå: bare kjente ankomster."""
    arr = dict(g.arrivals(wk, typed))

    def lev(w):
        if w <= wk:
            return g.levering(w)
        q = arr.get(w)
        if q is None:
            return None
        return (q, "typed" if w == wk + 4 else "open")

    def ordre(w):
        if w < wk:
            return g.order(w)
        if w == wk and typed is not None:
            return (typed, "typed")
        return None

    past = lambda f: (lambda w: f(w) if w <= wk else None)
    rows = [("Ordre inn", past(g.inn), "flow"),
            ("Levering", lev, "flow"),
            ("Sendt", past(g.sendt), "flow"),
            ("Netto lager", past(g.net), "net"),
            ("På vei", past(g.paavei), "flow"),
            ("Din ordre", ordre, "flow")]
    if short:
        rows = [rows[0], rows[1], rows[3], rows[4], rows[5]]
    if pos:
        rows.append(("Posisjon", past(g.posisjon), "net"))
    if cost:
        rows.append(("Kostnad, kr", lambda w: ((fmt_cost(g.ukekost(w)), "plain") if w <= wk else None), "cost"))
    return rows


def cost_matrix_fill(d, ax, y, rh, g, wfrom, wk, row_index):
    """Farger kostnadsraden etter art: rød familie for restordre, blå for lager. Tallet står i cella."""
    yy = y + row_index * rh
    for w in range(wfrom, wk + 1):
        lk, rk = g.lagerkost(w), g.restkost(w)
        fill = cell_cost(rk, "rest") if rk else cell_cost(lk, "lager")
        if fill != PAPER:
            d.rect(ax.xl(w) + 0.5, yy + 0.5, ax.slot - 1, rh - 1, fill)


def draw_seat_matrix(d, ax, y, g, wk, typed, rh=17, size=12, pos=False, lx=None, short=False, wfrom=None):
    wfrom = wfrom or ax.wmin
    rows = seat_rows(g, wk, typed, pos=pos, short=short)
    ci = len(rows) - 1
    cost_matrix_fill(d, ax, y, rh, g, wfrom, wk, ci)
    # kostnadsraden tegnes med gjennomsiktig grunn så fargen over synes
    rows2 = rows[:-1]
    yend = matrix(d, ax, y, rows2, wfrom, wk + 4, now=wk, rh=rh, size=size, lx=lx)
    lab, fn, _ = rows[-1]
    d.t(lx if lx is not None else ax.x0 - 8, yend + rh * 0.5 + size * 0.34, lab, size, 400, INK, "end")
    for w in range(wfrom, wk + 1):
        v = fn(w)[0]
        d.t(ax.xc(w) - 0.5, yend + rh * 0.5 + size * 0.34, v, size, 700 if w == wk else 400, INK, "middle")
    d.rect(ax.xl(wk), y, ax.slot, rh * len(rows), "none", INK, 1.2)
    return yend + rh


def order_cell(d, x, y, w, wk, typed, state="input", size=14):
    d.t(x, y, f"Din ordre for Uke {wk}", size, 600, INK)
    d.rect(x, y + 10, w, 48, PAPER, INK if typed is not None else HAIR2, 1.4, 6)
    if typed is None:
        d.t(x + w / 2, y + 41, "Antall enheter", 16, 400, INK3, "middle")
    else:
        d.t(x + w / 2, y + 45, typed, 30, 700, INK, "middle")
    if state == "input":
        d.button(x, y + 70, w, 42, f"Bekreft ordre på {typed}" if typed is not None else "Bekreft ordre", primary=typed is not None, size=15)
        yy = d.para(x, y + 132, "Kommer fram om lag Uke " + str(wk + 4) + ". Kan ikke endres etter at du har bekreftet.", w, 13, 17, fill=INK2)
    else:
        yy = y + 80
    return yy


def cost_cell(d, x, y, w, g, wk, h=96, size=13, title=True, axis_top=None):
    """Kostnadsruta: akkumulert totalkostnad delt i lager og restordre, og denne ukas regnestykke."""
    if title:
        d.t(x, y, "Kostnad så langt", 14, 600, INK)
        y += 8
    cl, cr = g.cum_lager(wk), g.cum_rest(wk)
    tot = cl + cr
    rows = [("Lagerkostnad", cl, BLUE), ("Restordrekostnad", cr, RED)]
    yy = y + 16
    for lab, v, col in rows:
        d.t(x, yy, lab, size, 400, INK)
        d.t(x + w, yy, kr(v), size, 600, INK, "end")
        d.rect(x, yy + 5, max(w * v / max(tot, 1), 1), 4, col)
        yy += 30
    d.t(x, yy, "Totalkostnad", size, 600, INK)
    d.t(x + w, yy, kr(tot), size, 700, INK, "end")
    d.line(x, yy - 15, x + w, yy - 15, HAIR2, 1)
    yy += 12
    ax = Axis(x + 30, w - 30, 1, wk)
    top = axis_top or (100 if tot <= 100 else (200 if tot <= 200 else 600))
    Y = cum_cost_area(d, ax, yy, h, g, 1, wk, top)
    for v in (0, top // 2, top):
        d.t(ax.x0 - 5, Y(v) + 4, v, 12, 400, INK3, "end")
        if v:
            d.line(ax.x0, Y(v), ax.x1, Y(v), HAIR, 1)
    d.t(ax.x0, yy + h + 16, "Uke 1", 12, 400, INK3)
    d.t(ax.x1, yy + h + 16, f"Uke {wk}", 12, 700, INK, "end")
    yy += h + 36
    lk, rk = g.lagerkost(wk), g.restkost(wk)
    if rk:
        s = f"Denne Uka: {g.rest[wk - 1]} restordre × 1,00 = {kr(rk)}"
    else:
        s = f"Denne Uka: {g.lager[wk - 1]} på lager × 0,50 = {kr(lk)}"
    return d.para(x, yy, s, w, 13, 17, fill=INK2)


def labtime(d, x, y, W, H, g, wk, typed, replay=False, state="input", spill="Spill 17", wait=True, chain_u=1.9):
    """Hovedflaten: ett rutenett der Kjede, Graf, Tall, Kostnad og Ordre står samtidig."""
    i_frame = len(d.b)
    d.b.append("")
    p = 22
    X, R = x + p, x + W - p
    d.t(X, y + 38, f"Uke {wk}", 26, 700, INK)
    d.t(X + text_w(f"Uke {wk}", 26) + 14, y + 38, f"Grossist, {spill}" + (", Replay" if replay else ""), 14, 400, INK2)
    d.t(R, y + 38, f"Totalkostnad {kr(g.kostsum(wk))}", 16, 600, INK, "end")
    d.line(X, y + 54, R, y + 54, HAIR, 1)
    # K: kjeden, hele bredden
    yk = y + 70
    yend = chain_seat(d, X, yk, R - X, g, wk, typed, u=chain_u, ls=13, pos=replay)
    Lw = (R - X) * 0.67
    xr = X + Lw + 30
    Rw = R - xr
    ym = yend + 26
    d.line(X, ym - 14, R, ym - 14, HAIR, 1)
    # M: meteogrammet
    m = meteo(d, g, X, ym, Lw, wk, typed, left=84, hn=112, hf=40, gap=12, ls=12, t_flow="", t_ord="", proj=replay,
              t_net="Netto lager: lager over null, restordre under", xstep=1, overduenote=False)
    flow_title(d, X, m["yflow"] - 6, g, wk, 12)
    d.t(X, m["yord"] - 6, "Din ordre", 12, 600, INK)
    # T: tallene, samme kolonner som grafen
    yt = m["axisbot"] + 8
    yend2 = draw_seat_matrix(d, m["ax"], yt, g, wk, typed, rh=16, size=12, pos=replay, lx=X + 76)
    # O og C i høyre kolonne
    yo = ym + 6
    yy = order_cell(d, xr, yo, Rw, wk, typed, state)
    if wait:
        d.t(xr, yy + 4, "Venter på: Jonas (3 min) og deg.", 13, 400, INK2)
    d.t(xr, yy + 26, "Regnestykket", 13, 600, BLUE, "start", 'text-decoration="underline"')
    yc = yy + 62
    d.line(xr, yc - 22, R, yc - 22, HAIR, 1)
    yc_end = cost_cell(d, xr, yc, Rw, g, wk, h=70)
    bottom = max(yend2 + 22, yc_end + 6, y + H - 22)
    d.line(xr - 15, ym - 4, xr - 15, bottom - 18, HAIR, 1)
    d.demodata(X, bottom)
    Hr = bottom + 16 - y
    i = len(d.b)
    d.rect(x, y, W, Hr, PAPER, HAIR2, 1.4, 10)
    d.b[i_frame] = d.b.pop(i)
    return {"m": m, "yt": yt, "yend": yend2, "xr": xr, "H": Hr}


# ---------- Telefonen: samme rutenett, redusert ----------
def tabs(d, y, active, labels=("Graf", "Tall", "Kostnad"), x=20, w=350, h=34):
    sw = w / len(labels)
    d.rect(x, y, w, h, PAPER, HAIR2, 1, 6)
    for i, lab in enumerate(labels):
        if lab == active:
            d.rect(x + i * sw + 2, y + 2, sw - 4, h - 4, INK, rx=5)
        d.t(x + i * sw + sw / 2, y + h / 2 + 5, lab, 14, 600, PAPER if lab == active else INK, "middle")


def order_input(d, y, wk, typed):
    d.t(20, y + 22, f"Din ordre for Uke {wk}", 15, 600, INK)
    yb = y + 34
    d.rect(20, yb, 350, 56, PAPER, INK if typed is not None else HAIR2, 1.4, 6)
    d.line(78, yb, 78, yb + 56, HAIR2, 1)
    d.line(312, yb, 312, yb + 56, HAIR2, 1)
    d.line(40, yb + 28, 58, yb + 28, INK, 2)
    d.line(332, yb + 28, 350, yb + 28, INK, 2)
    d.line(341, yb + 19, 341, yb + 37, INK, 2)
    if typed is None:
        d.t(195, yb + 36, "Antall enheter", 18, 400, INK3, "middle")
    else:
        d.t(195, yb + 40, typed, 32, 700, INK, "middle")
    return yb + 56


def phone_tab_content(d, g, wk, typed, tab, y0, replay=False):
    if tab == "Graf":
        m = meteo(d, g, 16, y0, 358, wk, typed, left=30, hn=96, hf=38, gap=12, ls=13, t_flow="", t_ord="", proj=replay,
                  t_net="Lager over null, restordre under", omax=25, fmax=32)
        flow_title(d, 16, m["yflow"] - 7, g, wk)
        d.t(16, m["yord"] - 7, "Din ordre", 13, 600, INK)
        return m["axisbot"]
    if tab == "Tall":
        ax = Axis(100, 274, wk - 5, wk + 4)
        d.t(16, y0 + 12, "Uke", 13, 400, INK2)
        for w in range(wk - 5, wk + 5):
            d.t(ax.xc(w), y0 + 12, w, 13, 700 if w == wk else 400, INK if w == wk else INK3, "middle")
        d.rect(ax.xr(wk), y0 - 2, ax.xr(wk + 4) - ax.xr(wk), 250, TINT)
        yend = draw_seat_matrix(d, ax, y0 + 22, g, wk, typed, rh=27, size=13, lx=92, short=False, wfrom=wk - 5, pos=replay)
        d.para(16, yend + 22, "Til høyre for nå står bare det som er bestilt. Bestilt er ikke garantert.", 350, 13, 17, fill=INK2)
        return yend + 40
    if tab == "Kostnad":
        return cost_cell(d, 20, y0 + 6, 350, g, wk, h=120, size=14)


def phone_game(d, x, y, s, g, wk, typed, tab="Graf", state="input", replay=False, footer=None):
    phone(d, x, y, s)
    game_header(d, wk, g.kostsum(wk))
    chain_seat(d, 16, 104, 358, g, wk, typed, u=1.0, ls=13, compact=True)
    tabs(d, 238, tab)
    phone_tab_content(d, g, wk, typed, tab, 296, replay)
    if state == "input":
        yb = order_input(d, 584, wk, typed)
        d.button(20, yb + 12, 350, 52, f"Bekreft ordre på {typed}" if typed is not None else "Bekreft ordre", primary=typed is not None)
        d.t(20, yb + 92, footer or "Venter på: Jonas (3 min) og deg.", 13, 400, INK2)
        d.demodata(370, yb + 92, a="end")
    d.end()


# ---------- 05 ----------
def hjelpegrad_pair(d, x, y, w, g=None, wk=11, typed=24):
    """Samme Uke på to nivåer: Klassespill (Posisjon-raden og linja låst) og Replay (åpnet)."""
    g = g or G
    d.t(x, y, "Hjelpegrad: samme Uke 11 i Klassespill og i Replay", 18, 600, INK)
    cw = (w - 30) / 2
    for j, replay in enumerate((False, True)):
        xx = x + j * (cw + 30)
        d.t(xx, y + 28, "Klassespill: tallene, ingen sum" if not replay else "Replay, etter Debriefen: summen åpnes", 14, 600, INK)
        ax = Axis(xx + 68, cw - 68, wk - 3, wk + 4)
        y0 = y + 42
        hh = 80
        d.rect(ax.xr(wk), y0, ax.xr(wk + 4) - ax.xr(wk), hh, TINT)
        Y = grid(d, ax, y0, hh, -40, 30, (-20, 0, 20), 12)
        net_area(d, ax, y0, hh, g.net, wk - 3, wk)
        d.circle(ax.xc(wk), Y(g.net(wk)), 3.5, RED, PAPER, 1.5)
        d.line(ax.xr(wk), y0 - 4, ax.xr(wk), y0 + hh, INK, 1.2)
        if replay:
            p24 = g.projection(wk, typed)
            d.path("M" + " L".join(f"{ax.xc(a):.1f} {Y(v):.1f}" for a, v in p24), stroke=GREY, sw=2, dash="6 4")
            d.circle(ax.xc(wk + 4), Y(p24[-1][1]), 3.5, PAPER, GREY, 2)
            d.t(ax.xr(wk) + 4, Y(-32), f"Med 24: {sg(p24[-1][1])}", 12, 600, INK)
        yt = y0 + hh + 8
        rows = [("Netto lager", lambda w: g.net(w) if w <= wk else None, "net"),
                ("På vei", lambda w: g.paavei(w) if w <= wk else None, "flow")]
        if replay:
            rows.append(("Posisjon", lambda w: g.posisjon(w) if w <= wk else None, "net"))
        else:
            rows.append(("Posisjon", "Låst til etter Debriefen", "lock"))
        matrix(d, ax, yt, rows, wk - 3, wk, now=wk, rh=17, size=12, lx=ax.x0 - 6)
        xaxis(d, ax, yt + 3 * 17 + 15, list(range(wk - 3, wk + 5)), wk, 12)
        txt = ("Lager, restordre og på vei står i hver sin rad. Summen må Sara regne selv, slik svingningene i Debriefen får noe å forklare."
               if not replay else f"Posisjon {g.lager[wk - 1]} − {g.rest[wk - 1]} + {g.paavei(wk)} = {g.posisjon(wk)} står i raden, og {g.posisjon(wk) + typed} etter ordren. Linja: hvis ordre inn holder seg. Ikke garantert.")
        d.para(xx, yt + 3 * 17 + 40, txt, cw, 13, 17, fill=INK2)


def build_05():
    d = Doc("05-spill", 1600, 1000, f"{NAME}, hovedskjerm i Uke 11",
            "Saras laptop i Labtime med rutenettet Kjede, Graf, Tall, Kostnad og Ordre samtidig, og den samme skjermen redusert på telefon med fanene Graf og Tall. Under: rutenettet på tre flater, og Hjelpegrad.")
    d.t(40, 46, "Uke 11 i Labtime: kjede, graf, tall og kostnad på én skjerm, og ordren på 24 står i alle fire.", 24, 600, INK)
    L = labtime(d, 40, 70, 960, 600, G, 11, 24)
    d.t(40, 70 + L["H"] + 22, "Laptop i Labtime. Grafen og tabellen deler kolonner, så hver Uke har både strek og tall.", 14, 400, INK2)

    s = 0.66
    phone_game(d, 1030, 70, s, G, 11, 24, "Graf")
    phone_game(d, 1030 + 390 * s + 12, 70, s, G, 11, 24, "Tall")
    d.t(1030, 70 + 844 * s + 22, "Telefon: kjede og ordre står fast. Graf, Tall og Kostnad", 14, 400, INK2)
    d.t(1030, 70 + 844 * s + 40, "er de tre andre rutene, én om gangen. Til høyre: Tall.", 14, 400, INK2)

    # Rutenettet på tre flater
    y0 = 70 + L["H"] + 52

    def gridmap(x, y, w, h, cells, title):
        d.t(x, y, title, 14, 600, INK)
        yy = y + 10
        for (cx, cy, cw, ch, lab) in cells:
            d.rect(x + cx * w, yy + cy * h, cw * w - 4, ch * h - 4, PAPER, INK, 1, 3)
            d.t(x + cx * w + 7, yy + cy * h + 16, lab, 12, 400, INK)

    d.t(40, y0, "Ett rutenett på tre flater", 18, 600, INK)
    gridmap(40, y0 + 26, 230, 106, [(0, 0, 1, 0.24, "Kjede"), (0, 0.24, 0.67, 0.42, "Graf"), (0.67, 0.24, 0.33, 0.42, "Ordre"),
                                    (0, 0.66, 0.67, 0.34, "Tall"), (0.67, 0.66, 0.33, 0.34, "Kostnad")], "Laptop i Labtime")
    gridmap(300, y0 + 26, 230, 106, [(0, 0, 1, 0.24, "Kjede, fire ledd"), (0, 0.24, 0.67, 0.42, "Graf, fire Roller"), (0.67, 0.24, 0.33, 0.76, "Kostnad"),
                                     (0, 0.66, 0.67, 0.34, "Tall: Rolle × Uke")], "Debrief og plenum")
    gridmap(560, y0 + 26, 110, 106, [(0, 0, 1, 0.24, "Kjede"), (0, 0.24, 1, 0.46, "Én av tre"), (0, 0.7, 1, 0.3, "Ordre")], "Telefon")
    d.para(700, y0 + 36, "Rutene står på samme plass på alle flater. Den som har lært laptopen i Labtime, kjenner igjen telefonen hjemme og Debriefen.", 300, 13, 17, fill=INK2)

    hjelpegrad_pair(d, 1030, 694, 530)
    d.save()


# ---------- 06 ----------
def waiting_rows(d, y, rows, x=20, width=350, lh=30):
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


def build_06():
    d = Doc("06-spilldynamikk", 2100, 1200, f"{NAME}, en Uke i spillet",
            "Seks telefonruter: Uka åpner, beslutningen, bekreftet, Uka går videre, Jonas er borte, spillet slutter. Under: ordren på 24 som flytter seg gjennom kjeden.")
    s = 0.8
    pw = 390 * s
    gapx = (2100 - 80 - 6 * pw) / 5
    y0 = 170
    d.t(40, 50, "En Uke på telefonen: kjeden og ordren står fast, og rutene under bytter innhold.", 28, 600, INK)
    notes = [
        ("A  Uka åpner", "Ny levering og ny ordre inn. I kjeden er plassen for Uke 15 tom og stiplet."),
        ("B  Beslutningen: 24", "24 legger seg bakerst i kjeden, etter 4, 4 og 8. Tallet står også i tabellen. Ingen fasit."),
        ("C  Bekreftet", "Ordren er låst. Skjermen sier hvem Uka venter på, med Rolle, navn og hvor lenge."),
        ("D  Uka går videre", "Boksene i kjeden rykker ett steg mot lageret. Under 2 sekunder, og kan hoppes over."),
        ("E  Jonas er borte", "Pause, så bestiller KI-spiller for Fabrikk, alltid merket. Jonas kan ta setet tilbake."),
        ("F  Spillet slutter", "Nå åpnes hele kjeden: kjedens kostnad først, så per Rolle og per kostnadsart."),
    ]
    for i, (h, n) in enumerate(notes):
        x = 40 + i * (pw + gapx)
        d.t(x, 94, h, 20, 600, INK)
        d.para(x, 118, n, pw, 15, 20, fill=INK2)

    def px(i):
        return 40 + i * (pw + gapx)

    phone_game(d, px(0), y0, s, G, 11, None, "Graf", footer="Sist Uke bestilte du 8.")
    phone_game(d, px(1), y0, s, G, 11, 24, "Tall")

    # C
    phone(d, px(2), y0, s)
    game_header(d, 11, G.kostsum(11))
    chain_seat(d, 16, 104, 358, G, 11, 24, u=1.0, ls=13, compact=True)
    tabs(d, 238, "Graf")
    phone_tab_content(d, G, 11, 24, "Graf", 296)
    y = 584
    d.line(20, y, 370, y, HAIR, 1)
    d.t(20, y + 28, "Ordren på 24 er sendt. Venter på Jonas.", 15, 600, INK)
    waiting_rows(d, y + 60, seat_sara_klar(), lh=28)
    d.t(20, y + 190, "Du får beskjed når Uke 12 åpner.", 13, 400, INK2)
    d.end()

    # D
    w = 12
    phone(d, px(3), y0, s)
    game_header(d, w, G.kostsum(w))
    chain_seat(d, 16, 104, 358, G, w, None, u=1.0, ls=13, compact=True)
    tabs(d, 238, "Graf")
    m = phone_tab_content(d, G, w, None, "Graf", 296)
    y = 584
    d.line(20, y, 370, y, HAIR, 1)
    d.t(20, y + 28, "Uke 11 er ferdig regnet", 15, 600, INK)
    d.t(370, y + 28, "Hopp over", 14, 600, BLUE, "end", 'text-decoration="underline"')
    yy = y + 58
    for lab, v in [("Levering", G.levering(w)), ("Ordre inn", G.inn(w)), ("Sendt", G.sendt(w)),
                   ("Restordre", f"{G.rest[w - 2]} blir {G.rest[w - 1]}"), ("Kostnad denne Uka", kr(G.ukekost(w)))]:
        d.t(20, yy, lab, 14, 400, INK)
        d.t(370, yy, v, 14, 600, INK, "end")
        yy += 24
    d.end()

    # E
    w = 14
    phone(d, px(4), y0, s)
    game_header(d, w, G.kostsum(w))
    chain_seat(d, 16, 104, 358, G, w, G.order(w), u=1.0, ls=13, compact=True)
    tabs(d, 238, "Graf")
    phone_tab_content(d, G, w, G.order(w), "Graf", 296)
    y = 584
    d.line(20, y, 370, y, HAIR, 1)
    d.t(20, y + 26, "Pause: Jonas har ikke bestilt på 24 t.", 15, 600, INK)
    rows = [("Detaljist", "Ida", "har bestilt", True), ("Distributør", "Mikkel", "har bestilt", True),
            ("Fabrikk", "KI-spiller", "bestiller for Jonas", False), ("Grossist", "Sara", "har bestilt", True)]
    yy = waiting_rows(d, y + 54, rows, lh=25)
    d.rect(20, yy - 6, 350, 70, TINT, None, 1, 6)
    d.t(32, yy + 16, "Slik ser Jonas det:", 13, 400, INK2)
    d.t(32, yy + 36, "KI-spiller bestiller for deg.", 14, 600, INK)
    d.button(236, yy + 6, 124, 40, "Ta tilbake setet", primary=False, size=13)
    d.end()

    # F
    phone(d, px(5), y0, s)
    d.t(20, 66, "Spillet er ferdig", 30, 700, INK)
    d.t(20, 88, "Grossist, Spill 17", 14, 400, INK2)
    d.t(20, 128, "Kjedens kostnad", 15, 400, INK2)
    d.t(20, 166, kr(K["kjedekost"]), 38, 700, INK, extra='style="font-variant-numeric:lining-nums proportional-nums"')
    # fire ledd, kostnad per Rolle og art
    y = 200
    d.t(20, y, "Rolle", 13, 600, INK2)
    d.t(230, y, "Lager", 13, 600, INK2, "end")
    d.t(300, y, "Restordre", 13, 600, INK2, "end")
    d.t(370, y, "Sum", 13, 600, INK2, "end")
    d.line(20, y + 7, 370, y + 7, HAIR2, 1)
    y += 30
    mx = max(K["kost_per_rolle"].values())
    for r in ROLES:
        S = SEATS[r]
        cl, cr = S.cum_lager(36), S.cum_rest(36)
        d.t(20, y, r + (" (deg)" if r == "Grossist" else ""), 14, 600 if r == "Grossist" else 400, INK)
        d.t(230, y, nf(cl), 14, 400, INK, "end")
        d.t(300, y, nf(cr), 14, 400, INK, "end")
        d.t(370, y, nf(cl + cr), 14, 600, INK, "end")
        bw = 350 * (cl + cr) / mx
        d.rect(20, y + 7, 350 * cl / mx, 6, BLUE)
        d.rect(20 + 350 * cl / mx, y + 7, 350 * cr / mx, 6, RED)
        y += 40
    tl = sum(SEATS[r].cum_lager(36) for r in ROLES)
    tr = sum(SEATS[r].cum_rest(36) for r in ROLES)
    d.t(20, y, "Kjeden", 14, 700, INK)
    d.t(230, y, nf(tl), 14, 600, INK, "end")
    d.t(300, y, nf(tr), 14, 600, INK, "end")
    d.t(370, y, nf(tl + tr), 14, 700, INK, "end")
    d.line(20, y - 18, 370, y - 18, HAIR2, 1)
    y += 30
    d.para(20, y, "Blått er lagerkostnad, rødt er restordrekostnad. Restordre koster dobbelt per enhet.", 350, 13, 17, fill=INK2)
    y += 50
    y += 26
    d.t(20, y, "Kjedens kostnad per Uke", 14, 600, INK)
    ax = Axis(52, 318, 1, 36)
    wl = [sum(SEATS[r].lagerkost(w) for r in ROLES) for w in range(1, 37)]
    wr = [sum(SEATS[r].restkost(w) for r in ROLES) for w in range(1, 37)]
    top = 180
    assert max(a + b for a, b in zip(wl, wr)) <= top
    hh = 120
    Y = yscale(y + 14, hh, 0, top)
    for v in (0, 90, 180):
        d.line(ax.x0, Y(v), ax.x1, Y(v), HAIR2 if v == 0 else HAIR, 1)
        d.t(ax.x0 - 5, Y(v) + 4, v, 12, 400, INK3, "end")
    bw = ax.slot - 2
    for w in range(1, 37):
        a, b = wl[w - 1], wr[w - 1]
        d.rect(ax.xc(w) - bw / 2, Y(a), bw, Y(0) - Y(a), BLUE)
        d.rect(ax.xc(w) - bw / 2, Y(a + b), bw, Y(a) - Y(a + b), RED)
    xaxis(d, ax, y + 14 + hh + 16, [1, 12, 24, 36], None, 12)
    d.para(20, y + 14 + hh + 42, "Hele kjeden med fire ledd ser dere sammen i Debriefen.", 350, 14, 19, fill=INK)
    d.button(20, 740, 350, 54, "Gå til Debrief")
    d.demodata(20, 826)
    d.end()

    # Under: hva spilleren lærer
    yt = y0 + 844 * s + 50
    d.t(40, yt, "Hva spilleren lærer av å se kjeden, grafen og kostnaden Uke for Uke", 24, 600, INK)
    tekst = [
        "Kjeden står fast øverst og viser hvor varene er nå: lageret som boks på sann skala, og det som er på vei som åpne bokser i kø. En ordre er en boks som må gå hele køen.",
        "Grafen under har samme fargespråk. Rød del av stolpen er det lageret faller den Uka, og i Tall-fanen står det samme tallet i cella. Regnestykket stemmer, ikke bare mønsteret.",
        "Kostnaden står løpende øverst og som egen fane: restordre koster 1,00 og lager 0,50 per enhet per Uke. Sara ser bare sin egen del mens spillet pågår.",
        "Når spillet er ferdig, åpnes de tre andre leddene. Først da ser gruppa at kjeden betalte mye mer enn summen av det hver enkelt kunne se.",
    ]
    colw = (2100 - 80 - 3 * 40) / 4
    for i, tx in enumerate(tekst):
        d.para(40 + i * (colw + 40), yt + 34, tx, colw, 16, 22, fill=INK)
    ys = yt + 166
    d.t(40, ys, f"Ordren på 24 i kjeden, sett fra fem Uker: boksen rykker mot lageret, og i Uke 15 kommer {G.levering(15)}.", 17, 600, INK)
    pw2 = (2100 - 80 - 4 * 24) / 5
    for i, wk in enumerate(range(11, 16)):
        xx = 40 + i * (pw2 + 24)
        typed = 24 if wk == 11 else G.order(wk)
        chain_seat(d, xx, ys + 12, pw2, G, wk, typed, u=0.85, ls=12, compact=True)
    d.save()


# ---------- 10 ----------
def build_10():
    d = Doc("10-pedagogikk", 2000, 1400, f"{NAME}, grafgrammatikken over tid",
            "Saras rutenett i Uke 5, 11, 18 og 29: kjede, meteogram, tabell og kostnad på én felles tidsakse, med prinsippene merket, og sammenligning med simulert referanse etter Debriefen.")
    d.t(40, 54, "Fire Uker av Saras spill, i samme rutenett", 34, 700, INK)
    d.para(40, 86, "Hver rad er Labtime-skjermen i én Uke. Grafen og tabellen deler tidsakse, så nå-streken vandrer mot høyre, og det som sto som bestilt i en rad, står som historie i raden under.", 1400, 16, 22, fill=INK2)
    keyx = 1540
    rows = [
        (5, G.order(5), [
            ("P2 Forsinkelse", "Alt er 4. Ingenting av det som kommer i Uke 7, er synlig fra Saras plass ennå."),
            ("P4 Ordrer er ikke etterspørsel", "Ordre inn er Idas ordre, ikke kundenes. Kjeden viser bare naboene."),
            ("Til neste ordre", "En rolig rad betyr bare at ingenting har nådd deg ennå."),
        ]),
        (11, 24, [
            ("P3 Det som er på vei", f"Kjeden viser 4, 4 og 8 i kø, og 24 bakerst. Posisjon {G.lager[10]} − {G.rest[10]} + {G.paavei(11)} = {G.posisjon(11)}, med 24 blir den {G.posisjon(11) + 24}."),
            ("P1 Lager er en opphopning", f"I tabellen: netto lager {sg(G.net(10))} + levering {G.levering(11)} − ordre inn {G.inn(11)} = {sg(G.net(11))}. Den røde stolpedelen er de samme {G.inn(11) - G.levering(11)}."),
            ("Til neste ordre", f"I Uke 15 kom {G.levering(15)} av 24. Bestilt er ikke levert."),
        ]),
        (18, G.order(18), [
            ("P2 og P3 igjen", f"{G.paavei(18)} på vei, og {G.overdue(18)} av dem uten dato hos leverandøren. Køen er lang, men lageret er tomt."),
            ("P7 Overreaksjon forsterker", "En ny ordre kommer ikke raskere enn de gamle. Den legger seg bakerst i køen."),
            ("P8 Restordre koster dobbelt", f"Restordre {G.rest[17]} koster {kr(G.restkost(18))} denne Uka. Kostnadsraden er rød hele veien."),
        ]),
        (29, G.order(29), [
            ("P8 Lager koster også", f"Lager {G.lager[28]} × 0,50 = {kr(G.lagerkost(29))} denne Uka. Toppen var lager {max(G.lager)}."),
            ("P1 Samme regning, motsatt fortegn", "Det som var på vei, kom nesten samtidig. Toppen er summen av gamle ordrer."),
            ("Til neste ordre", "Køen i kjeden er kort nå. Hvor mye du vil ha igjen, bestemmer du selv."),
        ]),
    ]
    y = 128
    rh = 240
    for now, typed, notes in rows:
        # venstre: uke, kjede, kostnad
        d.t(40, y + 22, f"Uke {now}", 24, 700, INK)
        lab = f"Lager {G.lager[now - 1]}" if G.net(now) >= 0 else f"Restordre {G.rest[now - 1]}"
        d.t(150, y + 22, f"{lab} · Totalkostnad {kr(G.kostsum(now))}", 14, 400, INK2)
        chain_seat(d, 40, y + 36, 470, G, now, typed, u=1.0, ls=12, compact=True)
        d.t(40, y + 190, "Kjeden P2 P3", 12, 400, INK3)
        # midten: graf og tall på felles akse 1 til 36
        gx, gw = 560, 950
        m = meteo(d, G, gx, y + 4, gw, now, typed, wmin=1, wmax=36, hn=70, hf=26, gap=6, titles=False, left=100, xstep=5,
                  proj=False, actual=False, nowlabel="Nå", overduenote=False, connector=True, ordlabel=False, netlabel=False,
                  arrnums=False, ls=12, ticks=(-40, 0, 20))
        ax = m["ax"]
        d.t(gx, m["ynet"] + 40, "Netto lager", 12, 400, INK2)
        d.t(gx, m["yflow"] + 20, "Inn og ut", 12, 400, INK2)
        d.t(gx, m["yord"] + 16, "Ordre", 12, 400, INK2)
        # tabell under grafen
        yt = m["axisbot"] + 2
        rows_m = [("Netto lager", lambda w: G.net(w) if w <= now else None, "net"),
                  ("På vei", lambda w: G.paavei(w) if w <= now else None, "flow"),
                  ("Kostnad, kr", lambda w: (fmt_cost(G.ukekost(w)), "plain") if w <= now else None, "plain")]
        cost_matrix_fill(d, ax, yt, 15, G, 1, now, 2)
        matrix(d, ax, yt, rows_m, 1, now, now=now, rh=15, size=10, lx=gx + 94, lsize=11)
        d.rect(ax.xr(now), yt, ax.xr(min(now + 4, 36)) - ax.xr(now), 45, TINT)
        d.t(gx + gw + 4, yt + 40, "", 11)
        # notater
        ny = y + 16
        for head, body in notes:
            d.t(keyx, ny, head, 15, 600, INK)
            ny = d.para(keyx, ny + 18, body, 420, 13, 17, fill=INK2) + 6
        d.line(40, y + rh - 10, 1960, y + rh - 10, HAIR, 1)
        y += rh

    # Etter Debriefen: hele kjeden og kostnaden mot simulert referanse
    d.t(40, y + 20, "Etter Debriefen: hele kjeden og kjedens kostnad, mot simulert referanse", 22, 600, INK)
    d.t(40, y + 42, "Samme kunder, samme struktur. Simulert: alle fire teller det som er på vei, med en rolig regel. Viser sammenhengen, ikke en fasit.", 14, 400, INK2)
    yy = y + 62
    d.t(40, yy + 12, "Spill 17, Uke 15", 14, 600, INK)
    chain_full(d, 40, yy + 18, 600, 15, SEATS, u=0.7, ls=12, cost=True, hi=56, names=False)
    d.t(700, yy + 12, "Simulert, Uke 15", 14, 600, INK)
    chain_full(d, 700, yy + 18, 600, 15, SEATS_ALLE, u=0.7, ls=12, cost=True, hi=56, names=False)
    # akkumulert kjedekost
    cx, cw_ = 1360, 600
    d.t(cx, yy + 12, "Kjedens kostnad, akkumulert", 14, 600, INK)
    ax = Axis(cx + 44, cw_ - 190, 1, 36)
    hh = 150
    Yc = yscale(yy + 24, hh, 0, 2400)
    for v in (0, 800, 1600, 2400):
        d.line(ax.x0, Yc(v), ax.x1, Yc(v), HAIR2 if v == 0 else HAIR, 1)
        d.t(ax.x0 - 5, Yc(v) + 4, nf(v, 0), 12, 400, INK3, "end")
    c17 = [sum(SEATS[r].kostsum(w) for r in ROLES) for w in range(1, 37)]
    cal = [sum(SEATS_ALLE[r].kostsum(w) for r in ROLES) for w in range(1, 37)]
    assert abs(c17[-1] - K["kjedekost"]) < 1e-9 and abs(cal[-1] - FX["alle_teller_paa_vei"]["kjedekost"]) < 1e-9
    d.path("M" + " L".join(f"{ax.xc(w):.1f} {Yc(c17[w - 1]):.1f}" for w in range(1, 37)), stroke=INK, sw=2)
    d.path("M" + " L".join(f"{ax.xc(w):.1f} {Yc(cal[w - 1]):.1f}" for w in range(1, 37)), stroke=GREY, sw=2, dash="6 4")
    d.t(ax.x1 + 6, Yc(c17[-1]) + 4, f"Spill 17: {kr(c17[-1])}", 13, 600, INK)
    d.t(ax.x1 + 6, Yc(cal[-1]) + 4, f"Simulert: {kr(cal[-1])}", 13, 600, INK2)
    xaxis(d, ax, yy + 24 + hh + 16, [1, 12, 24, 36], None, 12)
    d.para(cx, yy + 24 + hh + 40, "P8 og P6: målet er lavest kostnad for hele kjeden. Gapet åpner seg når restordren bygger seg opp oppstrøms.", cw_, 13, 17, fill=INK2)
    d.demodata(1960, 1390, "Demodata. Simulerte referanser er merket Simulert.", 13, "end")
    d.save()


if __name__ == "__main__":
    build_05()
    build_06()
    build_10()
