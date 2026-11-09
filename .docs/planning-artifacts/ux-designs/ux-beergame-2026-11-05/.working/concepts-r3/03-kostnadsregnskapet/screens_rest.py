"""01 landing, 02 Klasse, 03 Klasseøkt, 04 student hjem, 09 kontaktark."""
from datetime import date

from e03kost import *
from screens_core import G, BARE, ALLE, K, PN, waiting_rows, ledger
from screens_debrief_teacher import SEATS, DEM, KL, demand_band, game_week_cost

RE = Seat("Grossist", FX["replay_sara"])
NAME = "Kostnadsregnskapet"


def field(d, x, y, w, label, value, h=42, size=15, muted=False):
    d.t(x, y, label, 14, 600, INK)
    d.rect(x, y + 8, w, h, PAPER, HAIR2, 1, 5)
    d.t(x + 12, y + 8 + h / 2 + size * 0.34, value, size, 400, INK3 if muted else INK)
    return y + 8 + h


def wall_row(d, x, y, sp, cw, h, upto=None):
    """Én rad i matriseveggen: kjedekostnad per uke i marine trinn."""
    wc = game_week_cost(sp)
    for k, v in enumerate(wc[: upto or len(wc)]):
        fill, _ = chain_fill(v)
        d.rect(x + k * cw, y, cw - 0.8, h, fill)


# ---------- 01 ----------
def build_01():
    d = Doc("01-landing", 1440, 1200, f"{NAME}, landingsside for faglærere",
            "Første skjermbilde bæres av ett setes regnskap: kjedebåndet og meteogrammet med kostnad per uke og V-en på siden. Neste seksjon viser lærerens oversikt.")
    d.t(80, 58, NAME, 24, 700, INK)
    d.t(1360, 56, "For faglærere", 16, 400, INK2, "end")
    d.line(80, 78, 1360, 78, HAIR, 1)
    d.para(80, 150, "Én beslutning i uka. Regningen kommer fire uker senere.", 760, 50, 58, 700, INK)
    d.para(900, 128, f"{NAME} kjører hele forsyningskjedeøvelsen for emnet ditt, fra Invitasjon til PDF-rapport. På norsk, på mobil, for klasser på rundt 250 studenter.", 460, 19, 27, fill=INK)
    d.button(900, 234, 210, 50, "Be om lærertilgang", size=17)
    d.button(1124, 234, 110, 50, "Logg inn", primary=False, size=17)

    wk = 18
    yt = 324
    d.t(80, yt, f"Uke {wk} kostet {nf(G.wc(wk))} kr", 22, 700, INK)
    d.t(80, yt + 26, f"Totalkostnad så langt {nf(G.kostsum(wk))} kr: lager {nf(G.cum_lk(wk))}, restordre {nf(G.cum_rk(wk))}.", 16, 400, INK2)
    chain_seat(d, 820, yt - 22, 540, G, wk, G.order(wk), ls=15, show_cost=False)
    m = meteo3(d, G, 80, yt + 96, 1280, wk, G.order(wk), wmin=1, hk=80, hn=200, ho=70, gap=22, ls=15, left=44, sidev=120, kmax=40,
               t_cost="Kostnad per uke, kr", t_net="Lager over null, restordre under. Til høyre: hva det koster per uke",
               t_ord="Egen ordre, og når den er ventet", xstep=2, trail=True)
    d.t(80, m["axisbot"] + 22, "Ett sete, Grossist, Uke 18. Studenten ser bare sine egne tall, og tidsaksen viser aldri når spillet slutter. Demodata.", 15, 400, INK2)

    y2 = m["axisbot"] + 86
    d.line(80, y2 - 40, 1360, y2 - 40, HAIR, 1)
    d.t(80, y2, "Alle spillene på én skjerm", 32, 700, INK)
    spill = KL["spill"]
    rank = {"venter": 0, "pauset": 1, "pågår": 2, "ferdig": 3}
    rows = sorted(spill, key=lambda s: (rank[s["status"]], -(s.get("ventet_timer") or 0), -s["uke"]))[:6]
    yy = y2 + 36
    cols = [(80, "Spill"), (136, "Status"), (216, "Kjedekostnad per uke"), (580, "Uke"), (630, "Venter på")]
    for cx, h in cols:
        d.t(cx, yy, h, 14, 600, INK2)
    d.line(80, yy + 7, 820, yy + 7, HAIR2, 1)
    yy += 28
    for sp in rows:
        d.t(80, yy, sp["spill"], 15, 600, INK)
        d.t(136, yy, {"venter": "Venter", "pauset": "Pause", "pågår": "Pågår", "ferdig": "Ferdig"}[sp["status"]], 15, 400, INK)
        wall_row(d, 216, yy - 14, sp, 9.6, 16)
        d.t(580, yy, sp["uke"], 15, 400, INK)
        if sp["status"] == "venter":
            d.t(630, yy, f"{sp['navn']}, {sp['ventet_timer']} t", 15, 400, INK)
        elif sp["status"] == "pauset":
            d.t(630, yy, f"Fortsetter {sp['fortsetter']}", 15, 400, INK2)
        yy += 27
    fx = 900
    facts = [
        "KI-spillere fyller tomme seter, alltid merket.",
        "Ett fravær stopper ikke gruppa, og ingen spill blir stående uferdig.",
        "Studentlisten kommer fra Canvas-eksport.",
        "Du ser hvem hvert spill venter på, hvor lenge, og hva hvert spill har kostet.",
    ]
    fy = y2 + 36
    for f in facts:
        fy = d.para(fx, fy, f, 460, 18, 25) + 12
    d.save()


# ---------- 02 ----------
def build_02():
    d = Doc("02-laerer-klasse", 1440, 1000, f"{NAME}, lag Klasse",
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
    d.t(lx + lw - 12, y + 44, "Bytt fil", 14, 600, BLUE, "end", 'text-decoration="underline"')
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
        d.t(tx + tw, yy, "Registrer manuelt", 14, 600, BLUE, "end", 'text-decoration="underline"')
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
    d.t(tx + tw, yy, f"Send påminnelse til {r['uregistrert']}", 14, 600, BLUE, "end", 'text-decoration="underline"')
    d.demodata(1360, 980, a="end")
    d.save()


# ---------- 03 ----------
def chain_setup(d, x, y, w, start=12, pipe=4, ls=14):
    """Kjeden slik innstillingene står ved start: startlager som boks på sann skala, 4 enheter i hvert ledd underveis."""
    names = ["Fabrikk", "Distributør", "Grossist", "Detaljist"]
    block = (w - 80) / 4
    base = y + 50
    nw = 58
    for i, r in enumerate(names):
        p0 = x + i * block
        pw_ = block - nw - 14
        nx = p0 + pw_ + 8
        seg = pw_ / 2
        for j in range(2):
            d.rect(p0 + j * seg + 1, base - 12, seg - 3, 12, PAPER, BLUE, 1.1)
            d.t(p0 + j * seg + seg / 2, base - 17, pipe, ls - 1, 400, INK, "middle")
        d.line(p0 + pw_, base - 6, nx - 2, base - 6, INK, 1.2)
        d.t(p0 + pw_ / 2, base + ls + 4, "Produksjon" if i == 0 else "Frakt", ls - 1, 400, INK2, "middle")
        d.t(p0 + pw_ / 2, base + 2 * ls + 6, "2 uker", ls - 1, 400, INK2, "middle")
        d.t(nx, base - 40, r, ls, 600, INK)
        d.rect(nx, base - 30, nw, 30, PAPER, HAIR2, 1)
        d.rect(nx + 1, base - start * 1.5, nw - 2, start * 1.5, BLUEF)
        d.line(nx + 1, base - start * 1.5, nx + nw - 1, base - start * 1.5, BLUE, 1.6)
        d.line(nx, base, nx + nw, base, INK, 1.1)
        d.t(nx + nw / 2, base + ls + 4, f"Lager {start}", ls - 1, 400, INK2, "middle")
    kx = x + 4 * block
    d.line(kx - 4, base - 6, kx + 20, base - 6, INK, 1.2)
    d.t(kx + 26, base - 1, "Kundene", ls, 600, INK)
    return base + 2 * ls + 10


def build_03():
    d = Doc("03-laerer-spill", 1440, 1100, f"{NAME}, Klasseøkt",
            "Forhåndsutfylte Spillinnstillinger med kjeden tegnet slik den står ved start, kostnadsreglene, KI-modus, Debrief-modus, Obligatorisk, datoer, Labtimer og fordeling av 60 spill.")
    d.t(80, 62, "Klasseøkt for class-of-1994", 34, 700, INK)
    d.t(80, 90, "Alt er fylt ut med standardene. Du kan lagre uten å endre noe.", 16, 400, INK2)

    lx, lw = 80, 560
    y = 140
    d.t(lx, y, "Spillinnstillinger: Klassisk", 22, 600, INK)
    y += 32
    rows = [("Startlager", "12"), ("I hvert ledd ved start", "4 enheter"), ("Ordreforsinkelse", "2 uker"), ("Fraktforsinkelse", "2 uker"),
            ("Produksjonsforsinkelse", "2 uker"), ("Antall uker", "36"), ("Veiledede uker", "1–4"), ("Inaktivitetsgrense", "24 t, så KI overtar")]
    for lab, v in rows:
        d.t(lx, y, lab, 15, 400, INK)
        d.t(lx + lw, y, v, 15, 600, INK, "end")
        d.line(lx, y + 10, lx + lw, y + 10, HAIR, 1)
        y += 31
    y = d.para(lx, y + 2, "Kildene er uenige om forsinkelsene. Dette er produktets standard, og du kan endre den.", lw, 14, 19, fill=INK2)
    y += 24
    d.t(lx, y, "Kostnadsreglene", 17, 600, INK)
    y += 26
    for lab, v, col in (("Lagerkost", "0,50 per enhet per uke", BLUE), ("Restordrekost", "1,00 per enhet per uke", RED)):
        d.rect(lx, y - 10, 10, 10, col)
        d.t(lx + 16, y, lab, 15, 400, INK)
        d.t(lx + lw - 140, y, v, 15, 600, INK, "end")
        d.line(lx, y + 10, lx + lw - 140, y + 10, HAIR, 1)
        y += 31
    Yv = yscale(y - 64, 70, -20, 20)
    side_v(d, lx + lw - 110, 100, Yv, -20, 20, None, 20, 13, head=True)
    y += 14
    d.t(lx, y + 4, "Studentene ser regnskapet sitt hver uke. Kjedens sum ser de etter spillet.", 14, 400, INK2)
    y += 44
    d.t(lx, y, "Etterspørsel: 4, så 8 fra Uke 5", 15, 600, INK)
    d.t(lx + lw, y, "Studentene ser den ikke under spillet", 14, 400, INK2, "end")
    ax = Axis(lx + 20, lw - 20, 1, 36)
    yp, h = y + 12, 80
    for v in (0, 4, 8):
        yy = yp + h - v * h / 10
        d.line(ax.x0, yy, ax.x1, yy, HAIR, 1)
        d.t(ax.x0 - 6, yy + 4, v, 13, 400, INK3, "end")
    demand_band(d, ax, yp, h, 10)
    xaxis(d, ax, yp + h + 18, [1, 5, 12, 24, 36])

    # Høyre: kjeden, datoer, fordeling
    rx, rw = 720, 640
    y = 140
    d.t(rx, y, "Kjeden ved start, slik innstillingene står", 22, 600, INK)
    chain_setup(d, rx, y + 20, rw)
    y += 150
    d.t(rx, y, "Datoer", 22, 600, INK)
    start, end = date(2026, 11, 24), date(2026, 12, 18)
    span = (end - start).days

    def xd(dt):
        return rx + 8 + (dt - start).days / span * (rw - 16)

    ya = y + 86
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
        d.t(x, ya - 40, lab, 15, 600, INK, anch)
        d.t(x, ya - 22, ds, 14, 400, INK2, anch)
    for dt, ds, kl in [(date(2026, 11, 26), "to. 26. nov", "14:15"), (date(2026, 11, 30), "ma. 30. nov", "10:15"), (date(2026, 12, 3), "to. 3. des", "14:15"), (date(2026, 12, 7), "ma. 7. des", "10:15")]:
        x = xd(dt)
        d.rect(x - 4, ya + 8, 8, 8, BLUE)
        d.t(x, ya + 34, ds, 14, 400, INK, "middle")
        d.t(x, ya + 52, kl, 14, 400, INK2, "middle")
    d.t(rx, ya + 80, "Blå firkant: Labtime, Datalab A2.", 14, 400, INK2)
    d.t(rx + rw, ya + 80, "Legg til Labtime", 14, 600, BLUE, "end", 'text-decoration="underline"')

    y = ya + 130
    d.t(rx, y, "Fordeling: 60 Klassespill à 4", 22, 600, INK)
    d.para(rx, y + 26, f"{KL['traktA']['registrert']} studenter fordeles tilfeldig. Hver søyle er ett spill, hver rad en Rolle. Tomme seter får KI-spiller.", rw, 15, 20, fill=INK2)
    yg = y + 72
    roles = ["Detaljist", "Grossist", "Distributør", "Fabrikk"]
    cell = (rw - 84) / 60
    for j, r in enumerate(roles):
        d.t(rx, yg + j * 30 + 19, r, 14, 400, INK)
        for i in range(60):
            d.rect(rx + 84 + i * cell, yg + j * 30, cell - 2, 26, BASE)
    d.rect(rx + 84 + 16 * cell - 1, yg - 3, cell, 4 * 30 + 2, "none", INK, 1.4)
    d.t(rx + 84, yg + 140, "1", 13, 400, INK3)
    d.t(rx + 84 + 16.5 * cell, yg + 140, "17", 13, 700, INK, "middle")
    d.t(rx + rw, yg + 140, "60", 13, 400, INK3, "end")
    yy = yg + 168
    d.t(rx, yy, "Spill 17", 15, 600, INK)
    d.t(rx + 84, yy, "Ida, Detaljist. Sara, Grossist. Mikkel, Distributør. Jonas, Fabrikk.", 15, 400, INK)
    yy += 26
    d.button(rx, yy, 180, 44, "Kjør fordeling på nytt", primary=False, size=15)
    d.button(rx + 192, yy, 180, 44, "Bekreft fordeling", size=15)
    d.t(rx + 388, yy + 27, "Ingen får beskjed før du bekrefter.", 14, 400, INK2)

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
    d.button(1140, 1020, 220, 52, "Lagre Klasseøkt", size=17)
    d.t(1124, 1052, "Du kan lagre uten å endre noe.", 15, 400, INK2, "end")
    d.demodata(80, 1052)
    d.save()


# ---------- 04 ----------
def build_04():
    d = Doc("04-student-hjem", 1000, 900, f"{NAME}, student på mobil", "To telefoner: registrering via Invitasjon, og hjem under spill med regnskapet så langt.")
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
    d.t(112, y + 210, "Logg inn", 14, 600, BLUE, "start", 'text-decoration="underline"')
    d.end()

    phone(d, 560, 48, s)
    d.t(20, 62, "Spill 17", 28, 700, INK)
    d.t(20, 84, "Du er Grossist", 15, 400, INK2)
    d.rect(20, 100, 350, 232, TINT, None, 1, 6)
    d.t(32, 124, "Spillet venter på deg", 16, 600, INK)
    d.t(358, 124, "Uke 11", 15, 600, INK, "end")
    d.t(32, 148, "Totalkostnad så langt", 13, 400, INK2)
    d.t(32, 176, f"{nf(G.kostsum(11))} kr", 24, 700, INK, extra=PN)
    cost_split_bar(d, 180, 166, 178, G.cum_lk(11), G.cum_rk(11), h=8, labels=False)
    d.t(180, 192, f"Lager {nf(G.cum_lk(11))}", 13, 400, INK2)
    d.t(358, 192, f"Restordre {nf(G.cum_rk(11))}", 13, 400, INK2, "end")
    ax = Axis(52, 306, 1, 11)
    yk, hk = 206, 50
    for v in (0, 10):
        d.line(ax.x0, yk + hk - v * hk / 15, ax.x1, yk + hk - v * hk / 15, HAIR2 if v == 0 else HAIR, 1)
        d.t(ax.x0 - 5, yk + hk - v * hk / 15 + 4, v, 13, 400, INK3, "end")
    cost_bars(d, ax, yk, hk, G, 1, 11, 15)
    d.t(ax.xc(11), yk + hk - 13 * hk / 15 - 5, "13,00", 13, 600, INK, "middle")
    d.button(32, 272, 326, 48, "Gå til Uke 11", size=16)
    y = 362
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


def lines(d, x, y, w, n, step=11, col=HAIR):
    for i in range(n):
        d.rect(x, y + i * step, w * (1 - 0.14 * (i % 3)), 5, col, rx=1)


def build_09():
    d = Doc("09-alle-sider", 2000, 1400, f"{NAME}, alle andre sider", "Kontaktark over øvrige sider for Student, Faglærer og Admin.")
    d.t(40, 56, "Alle andre sider", 34, 700, INK)
    d.t(40, 84, "Regnskapet går igjen der kostnaden er poenget. Ellers er sidene rolige lister og skjema.", 16, 400, INK2)
    gx, cols, gap = 150, 5, 20
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
    x, y = cell(2, 0, "Regler før første ordre", "Regnskapet forklart på en ekte Uke: lager × 0,50, restordre × 1,00, og V-en på siden.")
    d.t(x + 12, y + 24, "Uke 5 kostet 6,00 kr", 13, 700)
    d.t(x + 12, y + 42, "12 på lager × 0,50 = 6,00 kr", 12, 400, INK2)
    meteo3(d, G, x + 8, y + 52, cw - 16, 5, 4, wmin=1, wmax=9, hk=0, hn=84, ho=34, gap=6, ls=11, left=22, sidev=40, titles=False, xstep=4,
           netlabel=False, arrnums=False, ordlabel=False, vlabel=True)
    x, y = cell(3, 0, "Startoppgave", "Regn ut hva én Uke koster, og posisjonen. Viser hvordan tallene henger sammen.")
    d.t(x + 14, y + 28, f"Lager {G.lager[10]}, restordre {G.rest[10]}, på vei {G.paavei(11)}", 13, 400, INK)
    d.t(x + 14, y + 60, "Uka koster", 14, 600)
    d.rect(x + 100, y + 42, 74, 28, PAPER, INK, 1.2, 3)
    d.t(x + 137, y + 62, nf(G.wc(11)), 15, 700, INK, "middle")
    d.t(x + 14, y + 96, "Posisjon", 14, 600)
    d.rect(x + 100, y + 78, 74, 28, PAPER, INK, 1.2, 3)
    d.t(x + 137, y + 98, G.posisjon(11), 15, 700, INK, "middle")
    axs = Axis(x + 14, cw - 28, 1, 11)
    cost_bars(d, axs, y + 128, 64, G, 1, 11, 15)
    x, y = cell(4, 0, "Replay", "Samme skjerm, nå med kostnaden for de neste fire ukene regnet ut. Tre KI-spillere. Tilfeldig etterspørsel.")
    meteo3(d, RE, x + 8, y + 6, cw - 16, 14, RE.order(14), wmin=3, hk=44, hn=80, ho=26, gap=5, ls=11, left=22, sidev=0, titles=False,
           xstep=4, netlabel=False, arrnums=False, ordlabel=False, proj=True, cost_label=False, overduenote=False, kmax=25, kticks=(0, 20))

    x, y = cell(0, 1, "Replay-gjennomgang", "Totalkostnad i Klassespillet og i Replay på samme akse. Ikke like for like.")
    ax = Axis(x + 14, cw - 28, 1, 36)
    Y = yscale(y + 30, 160, 0, 600)
    d.line(ax.x0, Y(0), ax.x1, Y(0), HAIR2, 1)
    d.path("M" + " L".join(f"{ax.xc(k):.1f} {Y(G.kostsum(k)):.1f}" for k in range(1, 37)), stroke=GREY, sw=1.4)
    d.path("M" + " L".join(f"{ax.xc(k):.1f} {Y(RE.kostsum(k)):.1f}" for k in range(1, RE.n + 1)), stroke=INK, sw=2)
    d.t(ax.xc(36), Y(G.kostsum(36)) - 6, f"Klassespill {nf(G.kostsum(36), 0)}", 12, 600, GREY, "end")
    d.t(ax.xc(RE.n), Y(RE.kostsum(RE.n)) - 8, f"Replay {nf(RE.kostsum(RE.n), 0)}", 12, 600, INK, "end")
    x, y = cell(1, 1, "Individuell test", "Flervalg, en tabelloppgave der studenten fyller inn ukas kostnad, og langsvar.")
    wd = (cw - 40) / 3
    d.t(x + 10, y + 22, "Flervalg", 12, 600)
    for i in range(4):
        d.circle(x + 16, y + 40 + i * 22, 4, PAPER, INK, 1)
        d.rect(x + 26, y + 37 + i * 22, wd - 34, 5, HAIR)
    xm = x + 10 + wd + 10
    d.t(xm, y + 22, "Fyll inn", 12, 600)
    for i, k in enumerate(range(9, 15)):
        yy = y + 36 + i * 22
        d.t(xm, yy + 12, k, 11, 400, INK3)
        d.rect(xm + 22, yy, wd - 24, 18, PAPER, HAIR2 if k > 11 else INK, 1, 2)
        if k <= 11:
            d.t(xm + wd - 6, yy + 13, nf(G.wc(k)), 11, 400, INK, "end")
    xl = xm + wd + 10
    d.t(xl, y + 22, "Langsvar", 12, 600)
    d.rect(xl, y + 32, wd, 130, PAPER, HAIR2, 1, 3)
    lines(d, xl + 8, y + 44, wd - 16, 6)
    x, y = cell(2, 1, "KI-vurdering", "Tilbakemelding på testen. Teller ikke og er aldri en karakter, og det står der.")
    d.t(x + 14, y + 28, "KI-generert, kan ta feil", 14, 600, INK)
    d.t(x + 14, y + 48, "Teller ikke. Ingen karakter.", 13, 400, INK2)
    lines(d, x + 14, y + 66, cw - 28, 8, 13)
    x, y = cell(3, 1, "Studentrapport (PDF)", "Ditt regnskap, dine beslutninger og din Forklaring, klar til å lagre.")
    pw = 124
    px = x + cw / 2 - pw / 2
    d.rect(px, y + 12, pw, th - 24, PAPER, HAIR2, 1)
    d.t(px + 8, y + 30, "Sara, Grossist", 11, 600)
    d.t(px + 8, y + 46, f"{nf(G.kostsum(36))} kr", 12, 700)
    cost_split_bar(d, px + 8, y + 52, pw - 16, G.cum_lk(36), G.cum_rk(36), h=5, labels=False)
    axp = Axis(px + 8, pw - 16, 1, 36)
    cost_bars(d, axp, y + 64, 36, G, 1, 36, 40)
    lines(d, px + 8, y + 112, pw - 16, 5, 11)
    d.t(x + cw - 12, y + th - 14, "PDF", 13, 600, INK2, "end")
    x, y = cell(4, 1, "Alle spill side om side", "Etter Debriefen: alle Grossister i klassen, kostnad per uke på samme skala. Ingen rangering.")
    fer = [s for s in KL["spill"] if s["status"] == "ferdig"][:24]
    gw = (cw - 28) / 6
    gh = (th - 24) / 4
    for i, sp in enumerate(sorted(fer, key=lambda s: s["spill"])):
        xx = x + 14 + (i % 6) * gw
        yy = y + 12 + (i // 6) * gh
        vals = sp["netto_lager"]["Grossist"]
        bw = (gw - 8) / 36
        for k, v in enumerate(vals):
            c = wcost(v)
            hh = min(c, 40) / 40 * (gh - 10)
            d.rect(xx + k * bw, yy + gh - 8 - hh, max(bw - 0.3, 0.5), hh, BLUE if v > 0 else RED)
        d.line(xx, yy + gh - 8, xx + gw - 8, yy + gh - 8, HAIR2, 0.8)

    x, y = cell(0, 2, "Lærerhjem", "Klassene dine, hva som venter, og neste frist.")
    d.t(x + 14, y + 28, "Klassene dine", 15, 700)
    d.t(x + 14, y + 56, "class-of-1994, IBE160", 14, 600)
    d.t(x + 14, y + 74, "Spillfrist ti. 8. des. 4 spill venter.", 13, 400, INK2)
    d.line(x + 14, y + 86, x + cw - 14, y + 86, HAIR, 1)
    for i, sp in enumerate(KL["spill"][:6]):
        wall_row(d, x + 14, y + 96 + i * 9, sp, (cw - 28) / 36, 7.5)
    d.t(x + 14, y + 172, "Ny Klasse", 14, 600, BLUE, "start", 'text-decoration="underline"')
    x, y = cell(1, 2, "Klasserapport", "Kjedekostnad og Forsterkning per Rolle for klassen, og mønstre i ordrene. PDF.")
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
    q = KL["ferdige"]["kjedekost"]
    d.t(x + 12, yy + 10, f"Kjedekost, median {nf(q['median'], 0)} kr", 12, 600, INK)
    d.t(x + 12, yy + 28, f"Midtre halvdel {nf(q['q1'], 0)} til {nf(q['q3'], 0)} kr", 12, 400, INK2)
    x, y = cell(2, 2, "Spillinnsikt (uke for uke)", "Ett spill: kjeden med fire ledd og Rolle × uke i kroner. Faglærer blar uke for uke.")
    chain_full(d, x + 8, y + 6, cw - 16, SEATS, wk=11, ls=10, cost=False, kunde=False, node_w=30, names=False, show_vals=False, px=0.6)
    axi = Axis(x + 66, cw - 80, 1, 36)
    yy = y + 92
    for r in ["Fabrikk", "Distributør", "Grossist", "Detaljist"]:
        S = SEATS[r]
        d.t(x + 12, yy + 14, r, 11, 400, INK)
        for k in range(1, 37):
            fill, _ = cost_fill("rk" if S.rest[k - 1] else "lk", S.wc(k))
            d.rect(axi.xl(k), yy + 3, axi.slot - 0.6, 15, fill if fill != PAPER else TINT)
        yy += 20
    d.line(axi.xr(11), y + 88, axi.xr(11), yy + 2, INK, 1.4)
    d.t(axi.xr(11) + 4, yy + 16, "Uke 11", 11, 600, INK)
    x, y = cell(3, 2, "Studentside", "Én students steg, regnskap, Forklaring, testsvar og rapport på én side.")
    d.t(x + 14, y + 28, "Sara, Grossist, Spill 17", 14, 700)
    labels = ["Klassespill", "Debrief", "Quiz", "Replay", "Test", "Rapport"]
    sw = (cw - 28) / 6
    d.line(x + 14 + sw / 2, y + 48, x + 14 + 5.5 * sw, y + 48, HAIR2, 1.2)
    for i, l in enumerate(labels):
        d.circle(x + 14 + (i + 0.5) * sw, y + 48, 5, INK if i == 0 else PAPER, INK if i == 0 else HAIR2, 1.2)
        d.t(x + 14 + (i + 0.5) * sw, y + 70, l, 11, 400, INK2, "middle")
    d.t(x + 14, y + 98, f"Totalkostnad så langt {nf(G.kostsum(11))} kr", 13, 600, INK)
    axs = Axis(x + 14, cw - 28, 1, 11)
    cost_bars(d, axs, y + 110, 80, G, 1, 11, 15)
    x, y = cell(4, 2, "Alle spill i plenum", "Matriseveggen på lerretet: kjedekostnad per uke for 60 spill, uten navn og uten rangering.")
    sp = sorted(KL["spill"], key=lambda s: s["spill"])
    for i, s in enumerate(sp):
        wall_row(d, x + 10, y + 8 + i * 3.25, s, (cw - 20) / 36, 2.8)

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
    x, y = cell(2, 3, "Lærers testspill", "Spill selv mot tre KI-spillere før klassen starter, med samme regnskap. Telles ikke med.")
    meteo3(d, RE, x + 8, y + 6, cw - 16, 9, RE.order(9), wmin=1, hk=44, hn=80, ho=26, gap=5, ls=11, left=22, sidev=36, titles=False,
           xstep=4, netlabel=False, arrnums=False, ordlabel=False, cost_label=False, overduenote=False, kmax=25, kticks=(0, 20), vlabel=False)
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
    for f in (build_01, build_02, build_03, build_04, build_09):
        f()
