"""01 landing, 02 Klasse, 03 Klasseøkt, 04 student hjem, 09 kontaktark."""
from datetime import date

from e06lib import *
from screens_debrief_teacher import demand_band

# Standardene i Klasseøkt («Klassisk»). Kontrolleres mot starten av spill 17.
SETT = {"startlager": 12, "per_ledd": 4, "ordre": 2, "frakt": 2, "produksjon": 2}
assert all(SEATS[r].lager[0] == SETT["startlager"] for r in ROLES)
assert all(SEATS[r].paavei(1) == SETT["per_ledd"] * (SETT["ordre"] + SETT["frakt"] - 1) for r in ROLES)


def field(d, x, y, w, label, value, h=42, size=15, muted=False):
    d.t(x, y, label, 14, 600, INK)
    d.rect(x, y + 8, w, h, PAPER, HAIR2, 1, 5)
    d.t(x + 12, y + 8 + h / 2 + size * 0.34, value, size, 400, INK3 if muted else INK)
    return y + 8 + h


def strip(d, x, y, sp, cw=4.3, lane=4, roles=("Fabrikk", "Distributør", "Grossist", "Detaljist")):
    for i, r in enumerate(roles):
        for k, v in enumerate(sp["netto_lager"][r]):
            f, _ = net_fill(v, (1, 13, 25, 49))
            d.rect(x + k * cw, y + i * (lane + 0.5), cw - 0.4, lane, f or "#EEF1F4")


def status_word(sp):
    return {"venter": "Venter", "pauset": "Pause", "pågår": "Pågår", "ferdig": "Ferdig"}[sp["status"]]


# ---------- 01 ----------
def build_01():
    d = Doc("01-landing", 1440, 1200, "Uka som kolonne, landingsside for faglærere",
            "Første skjermbilde bæres av ett setes kjede, graf og tabell på felles kolonner. Neste seksjon viser lærerens oversikt.")
    d.t(80, 58, "Uka som kolonne", 22, 700, INK)
    d.t(1360, 56, "For faglærere", 16, 400, INK2, "end")
    d.line(80, 78, 1360, 78, HAIR, 1)
    d.para(80, 150, "Hver uke er en kolonne. Kjeden viser hvor varene er.", 720, 50, 58, 700, INK)
    d.para(880, 128, "Kjører hele forsyningskjedeøvelsen for emnet ditt, fra Invitasjon til PDF-rapport. På norsk, på mobil, for klasser på rundt 250 studenter.", 480, 19, 27, fill=INK)
    d.button(880, 234, 210, 50, "Be om lærertilgang", size=17)
    d.button(1104, 234, 110, 50, "Logg inn", primary=False, size=17)

    wk = 18
    wmin = 3
    ax = Axis(260, 1100, wmin, wk + 4)
    ytop = 312
    ch = seat_chain(d, 80, ytop, 560, G, wk, G.order(wk), u=1.3, ls=14, vs=17, yb_off=90)
    d.para(700, ytop + 20, f"Kjeden er kolonnen for Uke {wk}, forstørret: restordre {G.rest[wk - 1]}, {G.paavei(wk)} på vei, og {G.overdue(wk)} av dem har ingen dato hos leverandøren.", 520, 17, 24, fill=INK)
    d.para(700, ytop + 100, "Under står de samme ukene som graf og som tall. Studenten kan trykke på en tidligere kolonne og se kjeden slik den var.", 520, 17, 24, fill=INK2)
    ycol = ch["bottom"] + 36
    zoom(d, 80, 640, ch["bottom"] + 8, ax, wk, ycol)
    rows = seat_rows(G, wk, G.order(wk))
    ynet, hn = ycol + 10, 132
    yflow, hf = ynet + hn + 14, 40
    yweek = yflow + hf + 20
    ymat = yweek + 7
    rh = 21
    ybot = ymat + len(rows) * rh
    d.rect(ax.xr(wk), ycol, ax.xr(wk + 4) - ax.xr(wk), ybot - ycol, TINT)
    Y = grid(d, ax, ynet, hn, -40, 30, (-40, -20, 0, 20), 13)
    net_area(d, ax, ynet, hn, G.net, wmin, wk)
    d.circle(ax.xc(wk), Y(G.net(wk)), 4, RED, PAPER, 2)
    flow_bars(d, ax, yflow, hf, G, wmin, wk, 32, x1=ax.xr(wk + 4))
    bwa = ax.slot - 6
    for week, q in G.arrivals(wk, G.order(wk)):
        d.rect(ax.xc(week) - bwa / 2, yflow + hf - q * hf / 32, bwa, q * hf / 32, PAPER, INK if week == wk + 4 else BLUE, 1.2)
    d.t(80, ynet + 14, "Lager over null", 14, 600, INK)
    d.t(80, ynet + hn - 4, "Restordre under", 14, 600, INK)
    d.t(80, yflow + hf - 4, "Levering og ordre inn", 14, 600, INK)
    week_row(d, ax, yweek, list(range(wmin, wk + 5)), wk)
    matrix(d, ax, ymat, rows, wmin, wk + 4, rh=rh, size=13, lx=80, lsize=14)
    diag(d, ax, wk, ymat + 4 * rh + 3, wk + 4, ymat + 2 * rh - 2)
    d.line(ax.xr(wk), ycol - 4, ax.xr(wk), ybot, INK, 1.4)
    d.t(ax.xr(wk) + 5, ycol + 4, "Nå", 13, 700, INK)
    col_box(d, ax, wk, ycol, ybot)
    d.t(80, ybot + 26, f"Ett sete, Grossist, Uke {wk}. Studenten ser bare sine egne tall, og tidsaksen viser aldri når spillet slutter. Demodata.", 15, 400, INK2)

    # Neste seksjon
    y2 = ybot + 92
    d.line(80, y2 - 40, 1360, y2 - 40, HAIR, 1)
    d.t(80, y2, "Alle spillene på én skjerm", 32, 700, INK)
    spill = KL["spill"]
    rank = {"venter": 0, "pauset": 1, "pågår": 2, "ferdig": 3}
    rws = sorted(spill, key=lambda s: (rank[s["status"]], -(s.get("ventet_timer") or 0), -s["uke"]))[:5]
    yy = y2 + 36
    cols = [(80, "Spill"), (136, "Status"), (216, "Grossist, netto lager per uke"), (560, "Uke"), (606, "Venter på")]
    for cx, h in cols:
        d.t(cx, yy, h, 14, 600, INK2)
    d.line(80, yy + 7, 820, yy + 7, HAIR2, 1)
    yy += 28
    for sp in rws:
        d.t(80, yy, sp["spill"], 15, 600, INK)
        d.t(136, yy, status_word(sp), 15, 400, INK)
        strip(d, 216, yy - 13, sp, cw=9, lane=15, roles=("Grossist",))
        d.t(560, yy, sp["uke"], 15, 400, INK)
        if sp["status"] == "venter":
            d.t(606, yy, f"{sp['navn']}, {sp['ventet_timer']} t", 15, 400, INK)
        elif sp["status"] == "pauset":
            d.t(606, yy, f"Fortsetter {sp['fortsetter']}", 15, 400, INK2)
        yy += 25
    fx = 900
    facts = ["KI-spillere fyller tomme seter, alltid merket.", "Ett fravær stopper ikke gruppa, og ingen spill blir stående uferdig.",
             "Studentlisten kommer fra Canvas-eksport.", "Du ser hvem hvert spill venter på, og hvor lenge."]
    fy = y2 + 36
    for f in facts:
        fy = d.para(fx, fy, f, 460, 18, 25) + 10
    d.save()


# ---------- 02 ----------
def build_02():
    d = Doc("02-laerer-klasse", 1440, 1000, "Uka som kolonne, lag Klasse",
            "Faglærer lager Klasse, laster opp Canvas-eksport, velger e-postkolonne, ser ugyldige rader og sender Invitasjoner.")
    r = KL["roster"]
    d.t(80, 62, "Lag Klasse", 34, 700, INK)
    d.t(80, 90, "Klasselisten kommer fra Canvas-eksporten din. Ingenting sendes før du trykker send.", 16, 400, INK2)
    lx, lw = 80, 420
    y = field(d, lx, 150, lw, "Navn", "class-of-1994", 50)
    y = field(d, lx, y + 40, lw, "Emnekode", "IBE160", 50)
    y += 40
    d.t(lx, y, "Canvas-eksport", 14, 600, INK)
    d.rect(lx, y + 8, lw, 62, TINT, HAIR2, 1, 5)
    d.t(lx + 12, y + 34, "ibe160-canvas-eksport.xlsx", 15, 600, INK)
    d.t(lx + 12, y + 55, f"{r['paa_lista']} rader lest", 14, 400, INK2)
    d.link(lx + lw - 12, y + 44, "Bytt fil", 14, "end")
    y += 110
    y = field(d, lx, y, lw, "E-postkolonne", "Kolonne C, E-post", 50)
    d.t(lx, y + 24, "Valgt fordi alle rader unntatt fire ser ut som adresser.", 14, 400, INK2)
    y += 76
    ok = r["paa_lista"] - r["ugyldige_rader"]
    d.button(lx, y, lw, 54, f"Send {ok} Invitasjoner", size=17)
    d.t(lx, y + 80, "Invitasjonen er gyldig i 14 dager. Ugyldige rader", 14, 400, INK2)
    d.t(lx, y + 99, "får ingen e-post før de er rettet.", 14, 400, INK2)

    tx, tw = 560, 800
    d.t(tx, 150, f"Ugyldige rader: {r['ugyldige_rader']} av {r['paa_lista']}", 22, 600, INK)
    heads = [(0, "Rad"), (70, "Navn"), (280, "E-post i fila"), (560, "Hva er galt")]
    yy = 186
    for off, h in heads:
        d.t(tx + off, yy, h, 14, 600, INK2)
    d.line(tx, yy + 8, tx + tw, yy + 8, HAIR2, 1)
    bad = [(37, "Emma Solberg", "emma.solberg@stud", "Domene mangler"),
           (88, "Jakob Lien", "jakob.lien(at)stud.example.no", "Mangler @"),
           (141, "Thea Moe", "thea.moe@@stud.example.no", "To @"),
           (203, "Lars Vik", "", "Tom celle")]
    assert len(bad) == r["ugyldige_rader"]
    yy += 34
    for rad, navn, ep, feil in bad:
        d.t(tx, yy, rad, 15, 600, INK)
        d.t(tx + 70, yy, navn, 15, 400, INK)
        d.rect(tx + 280, yy - 19, 262, 30, PAPER, RED, 1, 4)
        d.t(tx + 290, yy + 1, ep or "Skriv adresse", 14, 400, INK if ep else INK3)
        d.t(tx + 560, yy, feil, 15, 400, RED)
        d.link(tx + tw, yy, "Registrer manuelt", 14, "end")
        d.line(tx, yy + 20, tx + tw, yy + 20, HAIR, 1)
        yy += 54
    yy += 22
    d.t(tx, yy, "Forhåndsvisning av fila", 22, 600, INK)
    yy += 32
    hd = [(0, "Rad"), (70, "A Navn"), (280, "B Student-ID"), (430, "C E-post")]
    d.rect(tx + 420, yy - 20, tw - 420, 38 * 5 + 28, TINT)
    for off, h in hd:
        d.t(tx + off, yy, h, 14, 600, INK if off == 430 else INK2)
    d.line(tx, yy + 8, tx + tw, yy + 8, HAIR2, 1)
    prev = [(1, "Sara Lund", "240117", "sara.lund@stud.example.no"), (2, "Ida Berg", "240118", "ida.berg@stud.example.no"),
            (3, "Mikkel Dahl", "240119", "mikkel.dahl@stud.example.no"), (4, "Jonas Hagen", "240120", "jonas.hagen@stud.example.no"),
            (5, "Noah Eide", "240121", "noah.eide@stud.example.no")]
    yy += 34
    for rad, n, sid, e in prev:
        d.t(tx, yy, rad, 15, 400, INK2)
        d.t(tx + 70, yy, n, 15)
        d.t(tx + 280, yy, sid, 15)
        d.t(tx + 430, yy, e, 15)
        yy += 38
    yy += 34
    d.t(tx, yy, "Status etter utsending", 22, 600, INK)
    yy += 20
    segs = [("Registrert", r["registrert"], BLUE), ("Manuelt", r["manuelt_registrert"], INK), ("Uregistrert", r["uregistrert"], HAIR2)]
    xx = tx
    tot = r["paa_lista"]
    for lab, v, col in segs:
        ww = tw * v / tot
        d.rect(xx, yy, ww - 2, 34, col)
        xx += ww
    yy += 60
    xx = tx
    for lab, v, col in segs:
        d.rect(xx, yy - 11, 10, 10, col)
        s = f"{lab} {v}"
        d.t(xx + 15, yy, s, 15, 600, INK)
        xx += 15 + text_w(s, 15) + 28
    d.link(tx + tw, yy, f"Send påminnelse til {r['uregistrert']}", 14, "end")
    d.demodata(1360, 980, a="end")
    d.save()


# ---------- 03 ----------
def start_chain(d, x, y, w):
    """Kjeden ved start, slik innstillingene står: startlager og det som er i hvert ledd, på sann skala."""
    u = 2.6
    nw = 44
    lane = (w - 4 * nw) / 4
    yb = y + 78
    d.line(x + 8, yb, x + w, yb, ORD, 2)
    d.arrow_l(x, yb, ORD, 8)
    for i, r in enumerate(ROLES):
        nx = x + i * (nw + lane)
        d.rect(nx, yb - SETT["startlager"] * u, nw, SETT["startlager"] * u, BLUEF, BLUE, 1.2)
        d.line(nx, yb - 1, nx + nw, yb - 1, INK, 2)
        d.t(nx, y + 14, r, 13, 700, INK)
        d.t(nx + nw / 2, yb - SETT["startlager"] * u - 6, SETT["startlager"], 13, 600, INK, "middle")
        lx0 = nx + nw + 8
        n_sl = SETT["ordre"] + (SETT["produksjon"] if r == "Fabrikk" else SETT["frakt"])
        sw_ = (lane - 16 - (n_sl - 1) * 3) / n_sl
        for j in range(n_sl):
            xx = lx0 + j * (sw_ + 3)
            first_two = j < SETT["ordre"]
            d.rect(xx, yb - SETT["per_ledd"] * u - 1, sw_, SETT["per_ledd"] * u, PAPER, INK if first_two else BLUE, 1, extra=('stroke-dasharray="3 2"' if first_two else ""))
        d.t(lx0, yb + 18, "2 uker ordre", 12, 400, INK2)
        d.t(lx0, yb + 33, "+ 2 uker " + ("produksjon" if r == "Fabrikk" else "frakt"), 12, 400, INK2)
    return yb + 56


def build_03():
    d = Doc("03-laerer-spill", 1440, 1100, "Uka som kolonne, Klasseøkt",
            "Forhåndsutfylte Spillinnstillinger med kjeden ved start, KI-modus, Debrief-modus, Obligatorisk, datoer, Labtimer og fordeling av 60 spill.")
    d.t(80, 62, "Klasseøkt for class-of-1994", 34, 700, INK)
    d.t(80, 90, "Alt er fylt ut med standardene. Du kan lagre uten å endre noe.", 16, 400, INK2)
    lx, lw = 80, 560
    y = 140
    d.t(lx, y, "Spillinnstillinger: Klassisk", 22, 600, INK)
    y += 34
    rows = [("Startlager", f"{SETT['startlager']}"), ("I hvert ledd ved start", f"{SETT['per_ledd']} enheter"),
            ("Ordreforsinkelse", f"{SETT['ordre']} uker"), ("Fraktforsinkelse", f"{SETT['frakt']} uker"),
            ("Produksjonsforsinkelse", f"{SETT['produksjon']} uker"), ("Lagerkost", "0,50 per enhet per uke"), ("Restordrekost", "1,00 per enhet per uke"),
            ("Antall uker", "36"), ("Veiledede uker", "1–4"), ("Inaktivitetsgrense", "24 t, så KI overtar")]
    for lab, v in rows:
        d.t(lx, y, lab, 15, 400, INK)
        d.t(lx + lw, y, v, 15, 600, INK, "end")
        d.line(lx, y + 10, lx + lw, y + 10, HAIR, 1)
        y += 32
    y = d.para(lx, y + 4, "Kildene er uenige om forsinkelsene. Dette er produktets standard, og du kan endre den.", lw, 14, 19, fill=INK2)
    y += 24
    d.t(lx, y, "Kjeden ved start, slik innstillingene står", 15, 600, INK)
    d.t(lx + lw, y, "Varene går mot venstre", 13, 400, INK2, "end")
    y = start_chain(d, lx, y + 10, lw)
    d.t(lx, y + 4, "Blå boks: startlager. Stiplet: ordre på vei. Hel: varer på vei.", 13, 400, INK2)
    y += 36
    d.t(lx, y, "Etterspørsel: 4, så 8 fra Uke 5", 15, 600, INK)
    d.t(lx + lw, y, "Studentene ser den ikke under spillet", 13, 400, INK2, "end")
    ax = Axis(lx + 20, lw - 20, 1, 36)
    yp = y + 10
    h = 44
    for v in (0, 8):
        yy = yp + h - v * h / 10
        d.line(ax.x0, yy, ax.x1, yy, HAIR, 1)
        d.t(ax.x0 - 6, yy + 4, v, 13, 400, INK3, "end")
    demand_band(d, ax, yp, h, 10)
    week_row(d, ax, yp + h + 16, [1, 5, 12, 24, 36])

    rx, rw = 720, 640
    y = 140
    d.t(rx, y, "Datoer", 22, 600, INK)
    start, end = date(2026, 11, 24), date(2026, 12, 18)
    span = (end - start).days

    def xd(dt):
        return rx + 8 + (dt - start).days / span * (rw - 16)

    ya = y + 116
    d.line(rx, ya, rx + rw, ya, INK, 1.2)
    marks = [(start, "Start", "ti. 24. nov"), (date(2026, 12, 8), "Spillfrist", "ti. 8. des"), (date(2026, 12, 11), "Debrief-frist", "fr. 11. des"), (end, "Testfrist", "fr. 18. des")]
    for dt, lab, ds in marks:
        x = xd(dt)
        d.line(x, ya - 14, x, ya + 8, INK, 1.6)
        anch = "end" if dt == end else ("start" if dt == start else "middle")
        if lab == "Debrief-frist":
            anch, x = "start", x - 8
        if lab == "Spillfrist":
            anch, x = "end", x + 10
        d.t(x, ya - 44, lab, 15, 600, INK, anch)
        d.t(x, ya - 26, ds, 14, 400, INK2, anch)
    labs = [(date(2026, 11, 26), "to. 26. nov", "14:15"), (date(2026, 11, 30), "ma. 30. nov", "10:15"), (date(2026, 12, 3), "to. 3. des", "14:15"), (date(2026, 12, 7), "ma. 7. des", "10:15")]
    for dt, ds, kl in labs:
        x = xd(dt)
        d.rect(x - 4, ya + 8, 8, 8, BLUE)
        d.t(x, ya + 34, ds, 14, 400, INK, "middle")
        d.t(x, ya + 52, kl, 14, 400, INK2, "middle")
    d.t(rx, ya + 80, "Blå firkant: Labtime, Datalab A2.", 14, 400, INK2)
    d.link(rx + rw, ya + 80, "Legg til Labtime", 14, "end")

    y = ya + 146
    d.t(rx, y, "Fordeling: 60 Klassespill à 4", 22, 600, INK)
    d.para(rx, y + 26, f"{KL['traktA']['registrert']} studenter fordeles tilfeldig. Hver søyle er ett spill, hver rad en Rolle. Tomme seter får KI-spiller.", rw, 15, 20, fill=INK2)
    yg = y + 80
    cell = (rw - 84) / 60
    for j, r in enumerate(ROLES):
        d.t(rx, yg + j * 34 + 21, r, 14, 400, INK)
        for i in range(60):
            d.rect(rx + 84 + i * cell, yg + j * 34, cell - 2, 30, BASE)
    d.rect(rx + 84 + 16 * cell - 1, yg - 3, cell, 4 * 34 + 2, "none", INK, 1.4)
    d.t(rx + 84, yg + 158, "1", 13, 400, INK3)
    d.t(rx + 84 + 16.5 * cell, yg + 158, "17", 13, 700, INK, "middle")
    d.t(rx + rw, yg + 158, "60", 13, 400, INK3, "end")
    yy = yg + 188
    d.t(rx, yy, "Spill 17", 15, 600, INK)
    d.t(rx + 84, yy, "Ida, Detaljist. Sara, Grossist. Mikkel, Distributør. Jonas, Fabrikk.", 15, 400, INK)
    yy += 34
    d.button(rx, yy, 180, 46, "Kjør fordeling på nytt", primary=False, size=15)
    d.button(rx + 192, yy, 180, 46, "Bekreft fordeling", size=15)
    d.t(rx + 388, yy + 28, "Ingen får beskjed før du bekrefter.", 14, 400, INK2)

    yb = 900
    d.line(80, yb - 34, 1360, yb - 34, HAIR2, 1)
    blocks = [(80, "KI-modus", ("LLM-spillere", "Regelbaserte spillere"), "Gjelder alle KI-spillere i Klassespill og Replay."),
              (560, "Debrief-modus", ("Gruppedebrief", "Personlig debrief"), "De fire i spillet går gjennom det sammen.")]
    for bx, title, opts, desc in blocks:
        d.t(bx, yb, title, 16, 600, INK)
        xx = bx
        for i, o in enumerate(opts):
            wd = text_w(o, 15) + 28
            d.rect(xx, yb + 14, wd, 36, INK if i == 0 else PAPER, None if i == 0 else HAIR2, 1, 5)
            d.t(xx + wd / 2, yb + 37, o, 15, 600, PAPER if i == 0 else INK, "middle")
            xx += wd + 8
        d.t(bx, yb + 74, desc, 14, 400, INK2)
    d.t(1020, yb, "Obligatorisk", 16, 600, INK)
    d.rect(1020, yb + 18, 52, 28, INK, rx=14)
    d.circle(1058, yb + 32, 10, PAPER)
    d.t(1084, yb + 37, "Ja, står i emneplanen", 15, 400, INK)
    d.t(1020, yb + 74, "Studentene ser at øvelsen er obligatorisk.", 14, 400, INK2)
    d.button(1140, 1010, 220, 52, "Lagre Klasseøkt", size=17)
    d.t(1124, 1042, "Du kan lagre uten å endre noe.", 15, 400, INK2, "end")
    d.demodata(80, 1042)
    d.save()


# ---------- 04 ----------
def build_04():
    d = Doc("04-student-hjem", 1000, 900, "Uka som kolonne, student på mobil", "To telefoner: registrering via Invitasjon, og hjem under spill med siste kolonne som kjede.")
    s = 0.97
    d.t(70, 34, "Registrering", 18, 600, INK)
    d.t(560, 34, "Hjem under spill", 18, 600, INK)
    phone(d, 70, 48, s)
    d.t(20, 72, "Du er invitert", 30, 700, INK)
    d.para(20, 102, "Faglærer Bård har lagt deg til i class-of-1994, IBE160.", 340, 15, 20, fill=INK2)
    y = field(d, 20, 190, 350, "Navn", "Sara Lund", 54)
    y = field(d, 20, y + 34, 350, "E-post, fra klasselisten", "sara.lund@stud.example.no", 54)
    y = field(d, 20, y + 34, 350, "Velg passord", "Minst 10 tegn", 54, muted=True)
    d.button(20, y + 40, 350, 56, "Opprett konto og gå videre")
    d.para(20, y + 130, "Invitasjonen er gyldig i 14 dager. Du får Rolle og spill når Faglærer har bekreftet fordelingen.", 350, 14, 19, fill=INK2)
    d.t(20, y + 210, "Har du konto?", 14, 400, INK2)
    d.link(112, y + 210, "Logg inn", 14)
    d.end()

    phone(d, 560, 48, s)
    d.t(20, 62, "Spill 17", 28, 700, INK)
    d.t(20, 84, "Du er Grossist", 15, 400, INK2)
    d.rect(20, 100, 350, 244, TINT, None, 1, 6)
    d.t(32, 124, "Spillet venter på deg", 16, 600, INK)
    d.t(358, 124, "Uke 11", 15, 600, INK, "end")
    d.t(32, 144, "Kolonnen for Uke 11, slik den står nå:", 13, 400, INK2)
    seat_chain(d, 32, 150, 326, G, 11, None, u=1.2, yb_off=78)
    d.button(32, 282, 326, 48, "Gå til Uke 11", size=16)
    y = 372
    d.t(20, y, "Setene", 15, 600, INK)
    rows = [("Detaljist", "Ida", "har bestilt", True), ("Grossist", "Sara", "venter (deg)", False),
            ("Distributør", "Mikkel", "har bestilt", True), ("Fabrikk", "Jonas", "venter, 3 min", False)]
    y = waiting_rows(d, y + 26, rows, lh=26)
    y += 12
    d.t(20, y, "Stegene", 15, 600, INK)
    y += 26
    steps = ["Klassespill", "Debrief", "Quiz", "Replay", "Individuell test", "Rapport"]
    d.line(26, y - 5, 26, y - 5 + 5 * 25, HAIR2, 1.5)
    for i, st in enumerate(steps):
        yy = y + i * 25
        if i == 0:
            d.circle(26, yy - 5, 6, INK)
        else:
            d.circle(26, yy - 5, 5, PAPER, HAIR2, 1.5)
        d.t(42, yy, st, 14, 600 if i == 0 else 400, INK if i == 0 else INK2)
        if i == 0:
            d.t(370, yy, "pågår", 14, 400, INK, "end")
    y += 6 * 25 + 4
    d.line(20, y - 14, 370, y - 14, HAIR, 1)
    d.t(20, y + 6, "Neste frist", 14, 400, INK2)
    d.t(370, y + 6, "Spillfrist ti. 8. des", 14, 600, INK, "end")
    d.t(20, y + 30, "Labtime", 14, 400, INK2)
    d.t(370, y + 30, "to. 26. nov 14:15, Datalab A2", 14, 600, INK, "end")
    d.demodata(20, y + 56)
    d.end()
    d.save()


# ---------- 09 ----------
def frame(d, x, y, w, h):
    d.rect(x, y, w, h, PAPER, HAIR2, 1, 5)


def mini_net(d, x, y, w, h, S, upto=None, lo=-40, hi=30, lw=1.4):
    ax = Axis(x, w, 1, S.n)
    Y = yscale(y, h, lo, hi)
    d.line(x, Y(0), x + w, Y(0), HAIR2, 1)
    net_area(d, ax, y, h, S.net, 1, upto or S.n, lo, hi, lw=lw)


def lines(d, x, y, w, n, step=11, col=HAIR):
    for i in range(n):
        d.rect(x, y + i * step, w * (1 - 0.14 * (i % 3)), 5, col, rx=1)


def mini_matrix(d, x, y, w, S, now, typed, wfrom, pos=False, rh=16, size=10, lab=52):
    ax = Axis(x + lab, w - lab, wfrom, now + 4)
    rows = seat_rows(S, now, typed, pos=pos, sumrow=False, cost=False)
    yb = y + 10 + len(rows) * rh
    d.rect(ax.xr(now), y + 10, ax.xr(now + 4) - ax.xr(now), yb - y - 10, TINT)
    week_row(d, ax, y + 7, list(range(wfrom, now + 5)), now, size=9)
    matrix(d, ax, y + 10, rows, wfrom, now + 4, rh=rh, size=size, lx=x, lsize=10, gap=0.5)
    d.line(ax.xr(now), y, ax.xr(now), yb, INK, 1.2)
    return ax, yb


def build_09():
    d = Doc("09-alle-sider", 2000, 1400, "Uka som kolonne, alle andre sider", "Kontaktark over øvrige sider for Student, Faglærer og Admin.")
    d.t(40, 56, "Alle andre sider", 34, 700, INK)
    d.t(40, 84, "Kolonnene går igjen der tiden er poenget: én uke er én kolonne, og kjeden er den forstørret. Ellers er sidene rolige lister og skjema.", 16, 400, INK2)
    gx = 150
    cols = 5
    gap = 20
    cw = (2000 - gx - 40 - (cols - 1) * gap) / cols
    th = 212
    rh = th + 92
    y0 = 112

    def cell(col, row, title, line, wx=None, xo=None):
        x = xo if xo is not None else gx + col * (cw + gap)
        ww = wx or cw
        y = y0 + row * rh
        frame(d, x, y, ww, th)
        d.t(x, y + th + 22, title, 16, 600, INK)
        d.para(x, y + th + 42, line, ww, 13, 17, fill=INK2)
        return x, y

    d.t(40, y0 + 22, "Student", 20, 600, INK)
    d.t(40, y0 + 2 * rh + 22, "Faglærer", 20, 600, INK)
    d.line(40, y0 + 2 * rh - 18, 1960, y0 + 2 * rh - 18, HAIR2, 1)

    x, y = cell(0, 0, "Invitasjon og registrering", "Lenke fra e-post, navn og passord. Gyldig i 14 dager.")
    d.t(x + 14, y + 28, "Du er invitert", 15, 700)
    for i in range(3):
        d.rect(x + 14, y + 42 + i * 34, cw - 28, 26, PAPER, HAIR2, 1, 3)
    d.rect(x + 14, y + 148, cw - 28, 30, INK, rx=3)
    x, y = cell(1, 0, "Logg inn", "E-post og passord. Ingen åpen registrering.")
    d.t(x + 14, y + 28, "Logg inn", 15, 700)
    for i in range(2):
        d.rect(x + 14, y + 42 + i * 34, cw - 28, 26, PAPER, HAIR2, 1, 3)
    d.rect(x + 14, y + 114, cw - 28, 30, INK, rx=3)
    x, y = cell(2, 0, "Regler før første ordre", "Kjeden forklart på en ekte Uke: lager, levering, sendt og fire bokser på vei. Så kolonnen under.")
    seat_chain(d, x + 12, y + 6, cw - 24, G, 5, G.order(5), u=1.6, ls=11, vs=12, yb_off=70)
    mini_matrix(d, x + 12, y + 128, cw - 24, G, 5, G.order(5), 2, rh=14, size=9)
    x, y = cell(3, 0, "Startoppgave", "Fyll inn én kolonne. Lager etter forrige Uke, pluss levering, minus ordre inn.")
    c8, c9 = G.col(8), G.col(9)
    rr = [("Lager etter Uke 8", sg(c8["net"])), ("+ Levering, Uke 9", f"+ {c9['lev']}"), ("− Ordre inn, Uke 9", f"− {c9['inn']}")]
    yy = y + 32
    for lab, v in rr:
        d.t(x + 14, yy, lab, 14, 400, INK)
        d.t(x + cw - 14, yy, v, 14, 600, INK, "end")
        yy += 24
    d.line(x + 14, yy - 16, x + cw - 14, yy - 16, INK, 1)
    d.t(x + 14, yy + 8, "Lager etter Uke 9", 14, 600, INK)
    d.rect(x + cw - 74, yy - 12, 60, 28, PAPER, INK, 1.2, 3)
    d.t(x + cw - 44, yy + 8, sg(c9["net"]), 15, 700, INK, "middle")
    d.t(x + 14, yy + 48, "Minus betyr restordre.", 13, 400, INK2)
    x, y = cell(4, 0, "Replay", "Samme kolonner, nå med raden Posisjon. Tre KI-spillere. Tilfeldig etterspørsel.")
    d.t(x + 12, y + 20, "Replay, Uke 14", 12, 600, INK)
    mini_matrix(d, x + 12, y + 30, cw - 24, RE, 14, RE.order(14), 6, pos=True, rh=19, size=10)
    x, y = cell(0, 1, "Replay-gjennomgang", "Klassespillet og Replay på samme akse. Ikke like for like.")
    ax = Axis(x + 14, cw - 28, 1, 36)
    Y = yscale(y + 30, 140, -40, 30)
    d.line(ax.x0, Y(0), ax.x1, Y(0), HAIR2, 1)
    d.path("M" + " L".join(f"{ax.xc(k):.1f} {Y(G.net(k)):.1f}" for k in range(1, 37)), stroke=GREY, sw=1.4)
    net_area(d, ax, y + 30, 140, RE.net, 1, RE.n, lw=1.8)
    d.t(x + 14, y + 22, "Klassespill (grå), Replay (farget)", 13, 400, INK2)
    x, y = cell(1, 1, "Individuell test", "Flervalg, fyll inn en kolonne, tegn lageret, og langsvar.")
    wd = (cw - 40) / 3
    d.t(x + 10, y + 22, "Flervalg", 12, 600)
    for i in range(4):
        d.circle(x + 16, y + 40 + i * 22, 4, PAPER, INK, 1)
        d.rect(x + 26, y + 37 + i * 22, wd - 34, 5, HAIR)
    xm = x + 10 + wd + 10
    d.t(xm, y + 22, "Tegn lageret", 12, 600)
    axm = Axis(xm, wd, 1, 15)
    Ym = yscale(y + 34, 120, -40, 30)
    d.line(xm, Ym(0), xm + wd, Ym(0), HAIR2, 1)
    net_area(d, axm, y + 34, 120, G.net, 1, 9, lw=1.4)
    d.path("M" + " L".join(f"{axm.xc(k):.1f} {Ym(G.net(k)):.1f}" for k in range(9, 16)), stroke=INK, sw=1.4, dash="1 3")
    xl = xm + wd + 10
    d.t(xl, y + 22, "Langsvar", 12, 600)
    d.rect(xl, y + 32, wd, 130, PAPER, HAIR2, 1, 3)
    lines(d, xl + 8, y + 44, wd - 16, 6)
    x, y = cell(2, 1, "KI-vurdering", "Tilbakemelding på testen. Teller ikke og er aldri en karakter, og det står der.")
    d.t(x + 14, y + 28, "KI-generert, kan ta feil", 14, 600, INK)
    d.t(x + 14, y + 48, "Teller ikke. Ingen karakter.", 13, 400, INK2)
    lines(d, x + 14, y + 66, cw - 28, 8, 13)
    x, y = cell(3, 1, "Studentrapport (PDF)", "Din kjede i Uke 11, dine kolonner og din Forklaring, klar til å lagre.")
    pw = 124
    px = x + cw / 2 - pw / 2
    d.rect(px, y + 12, pw, th - 24, PAPER, HAIR2, 1)
    d.t(px + 8, y + 30, "Sara, Grossist", 11, 600)
    mini_net(d, px + 8, y + 38, pw - 16, 56, G)
    lines(d, px + 8, y + 104, pw - 16, 5, 11)
    d.t(x + cw - 12, y + th - 14, "PDF", 13, 600, INK2, "end")
    x, y = cell(4, 1, "Alle spill side om side", "Etter Debriefen: alle Grossister i klassen, samme skala. Ingen rangering.")
    fer = [s for s in KL["spill"] if s["status"] == "ferdig"][:24]
    gw = (cw - 28) / 6
    gh = (th - 24) / 4
    for i, sp in enumerate(fer):
        xx = x + 14 + (i % 6) * gw
        yy = y + 12 + (i // 6) * gh
        axg = Axis(xx, gw - 6, 1, 36)
        vals = sp["netto_lager"]["Grossist"]
        net_area(d, axg, yy, gh - 6, lambda k, vals=vals: vals[k - 1], 1, 36, -70, 70, lw=1)

    x, y = cell(0, 2, "Lærerhjem", "Klassene dine, hva som venter, og neste frist.")
    d.t(x + 14, y + 28, "Klassene dine", 15, 700)
    d.t(x + 14, y + 56, "class-of-1994, IBE160", 14, 600)
    d.t(x + 14, y + 74, "Spillfrist ti. 8. des. 4 spill venter.", 13, 400, INK2)
    d.line(x + 14, y + 86, x + cw - 14, y + 86, HAIR, 1)
    strip(d, x + 14, y + 96, KL["spill"][0], cw=(cw - 28) / 36, lane=8)
    d.link(x + 14, y + 158, "Ny Klasse", 14)
    x, y = cell(1, 2, "Klasserapport", "Fordeling av Forsterkning per Rolle, kjedekost og mønstre i ordrene.")
    F = KL["ferdige"]["forsterkning_per_rolle"]
    yy = y + 26
    sc = (cw - 118) / 13
    for r in ROLES:
        q = F[r]
        bx = x + 90
        d.t(x + 12, yy + 4, r, 12, 400, INK)
        d.line(bx + q["min"] * sc, yy, bx + q["max"] * sc, yy, HAIR2, 1.2)
        d.rect(bx + q["q1"] * sc, yy - 7, (q["q3"] - q["q1"]) * sc, 14, BASE)
        d.line(bx + q["median"] * sc, yy - 8, bx + q["median"] * sc, yy + 8, INK, 2)
        yy += 28
    yy += 2
    for k, v in list(KL["moenstre"].items())[:2]:
        d.t(x + 12, yy, f"{k}: {v}", 11, 400, INK2)
        yy += 16
    x, y = cell(2, 2, "Spillinnsikt (uke for uke)", "Ett spill, fire Roller som rader. Læreren trykker på en kolonne, og kjeden over viser den uka.")
    axs = Axis(x + 76, cw - 90, 1, 36)
    for i, r in enumerate(ROLES):
        c = SEATS[r].col(11)
        bx = x + 14 + i * (cw - 28) / 4
        d.t(bx, y + 20, r, 11, 600, INK)
        if c["rest"]:
            d.rect(bx, y + 44, 26, c["rest"] * 0.9, REDF, RED, 1)
        if c["lager"]:
            d.rect(bx, y + 44 - c["lager"] * 0.9, 26, c["lager"] * 0.9, BLUEF, BLUE, 1)
        d.line(bx, y + 44, bx + 26, y + 44, INK, 1.4)
    for i, r in enumerate(ROLES):
        yr = y + 84 + i * 26
        d.t(x + 12, yr + 15, r, 11, 400, INK)
        for k in range(1, 37):
            f, _ = net_fill(SEATS[r].net(k))
            if f:
                d.rect(axs.xl(k) + 0.3, yr, axs.slot - 0.6, 22, f)
    col_box(d, axs, 11, y + 80, y + 84 + 4 * 26, 1.2)
    zoom(d, x + 14, x + cw - 14, y + 66, axs, 11, y + 80)
    x, y = cell(3, 2, "Studentside", "Én students steg, Forklaring, testsvar og rapport. Hele løpet på én side.")
    d.t(x + 14, y + 28, "Sara, Grossist, Spill 17", 14, 700)
    labels = ["Klassespill", "Debrief", "Quiz", "Replay", "Test", "Rapport"]
    sw_ = (cw - 28) / 6
    d.line(x + 14 + sw_ / 2, y + 48, x + 14 + 5.5 * sw_, y + 48, HAIR2, 1.2)
    for i, l in enumerate(labels):
        d.circle(x + 14 + (i + 0.5) * sw_, y + 48, 5, INK if i == 0 else PAPER, INK if i == 0 else HAIR2, 1.2)
        d.t(x + 14 + (i + 0.5) * sw_, y + 70, l, 11, 400, INK2, "middle")
    mini_net(d, x + 14, y + 84, cw - 28, 96, G, 11)
    x, y = cell(4, 2, "Alle spill i plenum", "60 rader med uker som kolonner. Mønsteret går igjen, uten navn og uten rangering.")
    sp = KL["spill"]
    gw = (cw - 20) / 6
    gh = (th - 16) / 10
    for i, s_ in enumerate(sp):
        strip(d, x + 10 + (i % 6) * gw, y + 8 + (i // 6) * gh, s_, cw=(gw - 5) / 36, lane=3.6)

    x, y = cell(0, 3, "Tverrklasse-statistikk", "Klassen mot fjoråret. To tall, samme mål. Demodata.")
    FJ = KL["fjoraaret"]
    ko = KL["ferdige"]["kjedekost"]["median"]
    fa = KL["ferdige"]["forsterkning_per_rolle"]["Fabrikk"]["median"]
    d.t(x + 14, y + 26, "Median kjedekost, kr", 13, 600)
    mx = max(ko, FJ["median_kjedekost"])
    for i, (lab, v) in enumerate(((FJ["klasse"], FJ["median_kjedekost"]), ("class-of-1994", ko))):
        yy = y + 38 + i * 26
        d.t(x + 14, yy + 12, lab, 12, 400, INK)
        d.rect(x + 110, yy, (cw - 180) * v / mx, 16, BASE if i == 0 else ORD)
        d.t(x + cw - 14, yy + 12, nf(v, 0), 13, 600, INK, "end")
    d.t(x + 14, y + 116, "Median Forsterkning, Fabrikk", 13, 600)
    for i, (lab, v) in enumerate(((FJ["klasse"], FJ["median_forsterkning_fabrikk"]), ("class-of-1994", fa))):
        yy = y + 128 + i * 26
        d.t(x + 14, yy + 12, lab, 12, 400, INK)
        d.rect(x + 110, yy, (cw - 180) * v / 7.5, 16, BASE if i == 0 else ORD)
        d.t(x + cw - 14, yy + 12, fx1(v), 13, 600, INK, "end")
    x, y = cell(1, 3, "Meldinger", "Fra Faglærer til ett spill, en gruppe eller hele Klassen. Ingen chat mellom spillere.")
    d.t(x + 14, y + 28, "Melding til Noah, Spill 2", 14, 700)
    d.rect(x + 14, y + 40, cw - 28, 74, PAPER, HAIR2, 1, 3)
    d.para(x + 22, y + 60, "Gruppa venter på ordren din. KI overtar setet om 1 t.", cw - 44, 13, 17)
    d.rect(x + 14, y + 124, 100, 28, INK, rx=3)
    d.t(x + 64, y + 143, "Send", 13, 600, PAPER, "middle")
    d.t(x + 14, y + 176, "Sendt tidligere: 3", 13, 400, INK2)
    x, y = cell(2, 3, "Lærers testspill", "Spill selv mot tre KI-spillere før klassen starter. Telles ikke med.")
    seat_chain(d, x + 12, y + 6, cw - 24, RE, 9, RE.order(9), u=1.6, ls=11, vs=12, yb_off=70)
    mini_matrix(d, x + 12, y + 128, cw - 24, RE, 9, RE.order(9), 3, rh=14, size=9)
    xa = gx + 3 * (cw + gap)
    wa = (2 * cw + gap - 2 * 14) / 3
    d.line(xa - gap / 2, y0 + 3 * rh - 2, xa - gap / 2, y0 + 3 * rh + th + 64, HAIR2, 1)
    d.t(xa, y0 + 3 * rh - 8, "Admin", 20, 600, INK)
    x, y = cell(0, 3, "Admin-område", "Klasser og drift på ett sted.", wa, xa)
    for i, l in enumerate(("Klasser", "Brukere", "KI-kostnad", "Drift")):
        yy = y + 34 + i * 34
        d.t(x + 12, yy, l, 14, 400, INK)
        d.line(x + 12, yy + 10, x + wa - 12, yy + 10, HAIR, 1)
    x, y = cell(0, 3, "Brukere og roller", "Kontoer kommer bare via Invitasjon.", wa, xa + wa + 14)
    for i, (n, r) in enumerate((("Bård", "Faglærer"), ("Assistent", "Assistent"), ("Admin", "Admin"))):
        yy = y + 34 + i * 34
        d.t(x + 12, yy, n, 14, 400, INK)
        d.t(x + wa - 12, yy, r, 14, 400, INK2, "end")
        d.line(x + 12, yy + 10, x + wa - 12, yy + 10, HAIR, 1)
    x, y = cell(0, 3, "KI-kostnad", "Per Klasse og måned. Ingen tall vist her.", wa, xa + 2 * (wa + 14))
    for i, l in enumerate(("Per Klasse", "Per måned", "Grense")):
        yy = y + 34 + i * 34
        d.t(x + 12, yy, l, 14, 400, INK)
        d.rect(x + wa - 62, yy - 10, 50, 7, HAIR)
        d.line(x + 12, yy + 10, x + wa - 12, yy + 10, HAIR, 1)
    d.demodata(1960, 1392, a="end")
    d.save()


if __name__ == "__main__":
    build_01()
    build_02()
    build_03()
    build_04()
    build_09()
