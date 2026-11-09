"""01 landing, 02 Klasse, 03 Klasseøkt, 04 student hjem, 09 kontaktark."""
from datetime import date

from e07parts import *
from screens_core import G, BARE, ALLE, K, SEATS, DEM, waiting_rows, layer_graf, LAYER_TABS
from screens_debrief_teacher import KL, strip, demand_band, wall_row, MED_NET, FERDIG

RE = Seat("Grossist", FX["replay_sara"])


def field(d, x, y, w, label, value, h=42, size=15, muted=False):
    d.t(x, y, label, 14, 600, INK)
    d.rect(x, y + 8, w, h, PAPER, HAIR2, 1, 5)
    d.t(x + 12, y + 8 + h / 2 + size * 0.34, value, size, 400, INK3 if muted else INK)
    return y + 8 + h


# ---------- 01 ----------
def build_01():
    d = Doc("01-landing", 1440, 1200, "Lag for lag, landingsside for faglærere",
            "Første skjermbilde bæres av ett setes kjedebånd og meteogram på en rolig telefon. Neste seksjon viser lærerens oversikt med matriseveggen.")
    d.t(80, 58, "Lag for lag", 24, 700, INK)
    d.t(1360, 56, "For faglærere", 16, 400, INK2, "end")
    d.line(80, 78, 1360, 78, HAIR, 1)
    y = d.para(80, 156, "Én beslutning i uka. Virkningen kommer fire uker senere.", 640, 50, 58, 700, INK)
    y = d.para(80, y + 18, "Lag for lag kjører hele forsyningskjedeøvelsen for emnet ditt, fra Invitasjon til PDF-rapport. På norsk, på mobil, for klasser på rundt 250 studenter.", 600, 19, 27, fill=INK)
    d.button(80, y + 22, 220, 52, "Be om lærertilgang", size=17)
    d.button(314, y + 22, 120, 52, "Logg inn", primary=False, size=17)
    yy = y + 130
    d.t(80, yy, "Studenten ser én ting om gangen", 20, 600, INK)
    yy = d.para(80, yy + 28, "Kjedebåndet og ordrefeltet står alltid på skjermen. Grafen, tallene og kostnaden er lag studenten blar mellom. Noen lag åpnes først etter Debriefen, og du ser hvilke i Klasseøkt.", 600, 17, 25, fill=INK2)
    tabs(d, 80, yy + 18, 360, LAYER_TABS + ["Posisjon"], "Graf", locked=("Posisjon",), h=32, size=14)
    d.t(80, yy + 78, "Stiplet: åpnes etter Debriefen.", 14, 400, INK2)

    # Telefonen til høyre, i full skala
    px, py = 900, 110
    phone(d, px, py, 1.0)
    d.t(20, 62, "Uke 18", 30, 700, INK)
    d.t(20, 84, "Grossist", 14, 400, INK2)
    d.t(370, 58, "Totalkostnad", 13, 400, INK2, "end")
    d.t(370, 80, f"{nf(G.kostsum(18))} kr", 18, 600, INK, "end")
    yb = seat_band(d, G, 18, 20, 98, 350, G.order(18), u=0.95, fixed=(30, 40))
    tabs(d, 20, yb + 8, 350, LAYER_TABS, "Graf")
    layer_graf(d, G, 18, G.order(18), yb + 54)
    d.line(20, 600, 370, 600, HAIR, 1)
    d.t(20, 624, "Din ordre for Uke 18", 15, 600, INK)
    d.rect(20, 634, 350, 54, PAPER, INK, 1.4, 6)
    d.t(195, 673, G.order(18), 32, 700, INK, "middle")
    d.button(20, 700, 350, 50, f"Bekreft ordre på {G.order(18)}")
    d.t(20, 780, "Ett sete, egne tall. Tidsaksen viser aldri slutten.", 13, 400, INK2)
    d.demodata(370, 800, a="end")
    d.end()

    # Neste seksjon
    y2 = 1000
    d.line(80, 960, 1360, 960, HAIR, 1)
    d.t(80, y2, "Alle spillene på én skjerm", 32, 700, INK)
    d.para(80, y2 + 34, "Hver rad er ett spill, hver celle én uke. Du ser hvem hvert spill venter på, og hvor lenge.", 560, 17, 24, fill=INK2)
    spill = KL["spill"]
    rank = {"venter": 0, "pauset": 1, "pågår": 2, "ferdig": 3}
    rows = sorted(spill, key=lambda s: (rank[s["status"]], -(s.get("ventet_timer") or 0), -s["uke"]))[:8]
    wx, cw, ch = 760, 11, 12
    yy = y2 - 6
    d.t(700, yy, "Spill", 13, 600, INK2, "end")
    d.t(wx, yy, "Grossist, netto lager per uke", 13, 600, INK2)
    d.t(wx + 36 * cw + 16, yy, "Venter på", 13, 600, INK2)
    yy += 14
    for sp in rows:
        d.t(700, yy + 10, sp["spill"], 13, 600, INK, "end")
        wall_row(d, wx, yy, sp, "Grossist", cw, ch)
        if sp["status"] == "venter":
            d.t(wx + 36 * cw + 16, yy + 10, f"{sp['navn']}, {sp['ventet_timer']} t", 13, 400, INK)
        elif sp["status"] == "pauset":
            d.t(wx + 36 * cw + 16, yy + 10, "Pause", 13, 400, INK2)
        yy += ch + 4
    facts = ["KI-spillere fyller tomme seter, alltid merket. Ett fravær stopper ikke gruppa, og ingen spill blir stående uferdig.",
             "Studentlisten kommer fra Canvas-eksport."]
    fy = y2 + 96
    for f in facts:
        fy = d.para(80, fy, f, 560, 16, 22) + 8
    d.save()


# ---------- 02 ----------
def build_02():
    d = Doc("02-laerer-klasse", 1440, 1000, "Lag for lag, lag Klasse",
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


# ---------- 03 og 04 ----------
def settings_chain(d, x, y, w, u=2.6):
    """Kjeden slik innstillingene står: startlager 12 i hvert ledd, 4 enheter i hver forsinkelsesplass."""
    roles = ["Fabrikk", "Distributør", "Grossist", "Detaljist"]
    step = (w - 60) / 4
    xs = [x + 70 + i * step for i in range(4)]
    base = y + 40 + 12 * u
    nw = 34
    for i, r in enumerate(roles):
        cx = xs[i]
        d.t(cx, y + 14, r, 14, 600, INK, "middle")
        d.rect(cx - nw / 2, base - 12 * u, nw, 12 * u, BLUEF, BLUE, 1.1)
        d.line(cx - nw / 2 - 3, base, cx + nw / 2 + 3, base, INK, 1.2)
        d.t(cx, base - 12 * u - 6, "12", 13, 600, INK, "middle")
        # to plasser foran hvert ledd: 2 uker frakt (produksjon for Fabrikk)
        left = (xs[i - 1] + nw / 2 + 4) if i else x
        for j in range(2):
            sx = left + 6 + j * 24
            d.rect(sx, base - 4 * u, 18, 4 * u, PAPER, BLUE, 1)
            d.t(sx + 9, base - 4 * u - 4, "4", 13, 400, INK, "middle")
        d.line(left + 54, base - 6, cx - nw / 2 - 6, base - 6, INK, 1)
        arrow_head(d, cx - nw / 2 - 2, base - 6, "right", 5)
        d.t(left + 27, base + 16, "produksjon" if i == 0 else "frakt", 12, 400, INK2, "middle")
    kx = x + w - 10
    d.line(xs[-1] + nw / 2 + 6, base - 6, kx - 40, base - 6, INK, 1)
    arrow_head(d, kx - 36, base - 6, "right", 5)
    d.t(kx - 10, y + 14, "Kunde", 14, 600, INK, "middle")
    yo = base + 40
    for i in range(4):
        right = xs[i + 1] - nw / 2 if i < 3 else kx - 36
        d.line(right - 4, yo, xs[i] + nw / 2 + 10, yo, INK2, 1)
        arrow_head(d, xs[i] + nw / 2 + 4, yo, "left", 5, INK2)
        d.t((right + xs[i]) / 2 + 8, yo + 16, "ordre, 2 uker", 12, 400, INK, "middle")
    return yo + 24


def build_03():
    d = Doc("03-laerer-spill", 1440, 1100, "Lag for lag, Klasseøkt",
            "Forhåndsutfylte Spillinnstillinger med kjeden tegnet slik den står ved start, KI-modus, Debrief-modus, Obligatorisk, datoer, Labtimer, fordeling av 60 spill og lagtrappa for studentene.")
    d.t(80, 62, "Klasseøkt for class-of-1994", 34, 700, INK)
    d.t(80, 90, "Alt er fylt ut med standardene. Du kan lagre uten å endre noe.", 16, 400, INK2)

    lx, lw = 80, 560
    y = 140
    d.t(lx, y, "Spillinnstillinger: Klassisk", 22, 600, INK)
    y += 32
    rows = [("Startlager", "12"), ("I hvert ledd ved start", "4 enheter"), ("Ordreforsinkelse", "2 uker"), ("Fraktforsinkelse", "2 uker"),
            ("Produksjonsforsinkelse", "2 uker"), ("Lagerkost", "0,50 per enhet per uke"), ("Restordrekost", "1,00 per enhet per uke"),
            ("Antall uker", "36"), ("Veiledede uker", "1–4"), ("Inaktivitetsgrense", "24 t, så KI overtar")]
    for lab, v in rows:
        d.t(lx, y, lab, 15, 400, INK)
        d.t(lx + lw, y, v, 15, 600, INK, "end")
        d.line(lx, y + 10, lx + lw, y + 10, HAIR, 1)
        y += 31
    y += 4
    y = d.para(lx, y, "Kildene er uenige om forsinkelsene. Dette er produktets standard, og du kan endre den.", lw, 14, 19, fill=INK2)
    y += 24
    d.t(lx, y, "Slik står kjeden ved start", 15, 600, INK)
    y = settings_chain(d, lx, y + 12, lw)
    d.t(lx, y + 18, "Om lag 4 uker fra ordre til levering: 2 uker ordre og 2 uker frakt.", 14, 400, INK2)
    y += 44
    d.t(lx, y, "Etterspørsel: 4, så 8 fra Uke 5", 15, 600, INK)
    d.t(lx + lw, y, "Studentene ser den ikke under spillet", 14, 400, INK2, "end")
    ax = Axis(lx + 20, lw - 20, 1, 36)
    yp = y + 12
    h = 80
    for v in (0, 4, 8):
        yy = yp + h - v * h / 10
        d.line(ax.x0, yy, ax.x1, yy, HAIR, 1)
        d.t(ax.x0 - 6, yy + 4, v, 13, 400, INK3, "end")
    demand_band(d, ax, yp, h, 10)
    xaxis(d, ax, yp + h + 17, [1, 5, 12, 24, 36])

    # Høyre: datoer
    rx, rw = 720, 640
    y = 140
    d.t(rx, y, "Datoer", 22, 600, INK)
    start, end = date(2026, 11, 24), date(2026, 12, 18)
    span = (end - start).days

    def xd(dt):
        return rx + 8 + (dt - start).days / span * (rw - 16)

    ya = y + 100
    d.line(rx, ya, rx + rw, ya, INK, 1.2)
    marks = [(start, "Start", "ti. 24. nov", "start", 0), (date(2026, 12, 8), "Spillfrist", "ti. 8. des", "end", 10),
             (date(2026, 12, 11), "Debrief-frist", "fr. 11. des", "start", -8), (end, "Testfrist", "fr. 18. des", "end", 0)]
    for dt, lab, ds, anch, off in marks:
        x = xd(dt)
        d.line(x, ya - 14, x, ya + 8, INK, 1.6)
        d.t(x + off, ya - 44, lab, 15, 600, INK, anch)
        d.t(x + off, ya - 26, ds, 14, 400, INK2, anch)
    for dt, ds, kl in [(date(2026, 11, 26), "to. 26. nov", "14:15"), (date(2026, 11, 30), "ma. 30. nov", "10:15"),
                       (date(2026, 12, 3), "to. 3. des", "14:15"), (date(2026, 12, 7), "ma. 7. des", "10:15")]:
        x = xd(dt)
        d.rect(x - 4, ya + 8, 8, 8, BLUE)
        d.t(x, ya + 34, ds, 14, 400, INK, "middle")
        d.t(x, ya + 52, kl, 14, 400, INK2, "middle")
    d.t(rx, ya + 80, "Blå firkant: Labtime, Datalab A2.", 14, 400, INK2)
    link(d, rx + rw, ya + 80, "Legg til Labtime", 14, a="end")

    # Fordeling
    y = ya + 128
    d.t(rx, y, "Fordeling: 60 Klassespill à 4", 22, 600, INK)
    d.t(rx, y + 24, f"{KL['traktA']['registrert']} studenter fordeles tilfeldig. Hver søyle er ett spill. Tomme seter får KI-spiller.", 14, 400, INK2)
    yg = y + 42
    cell = (rw - 84) / 60
    for j, r in enumerate(ROLES):
        d.t(rx, yg + j * 24 + 16, r, 13, 400, INK)
        for i in range(60):
            d.rect(rx + 84 + i * cell, yg + j * 24, cell - 2, 20, BASE)
    d.rect(rx + 84 + 16 * cell - 1, yg - 3, cell, 4 * 24 + 2, "none", INK, 1.4)
    d.t(rx + 84, yg + 112, "1", 13, 400, INK3)
    d.t(rx + 84 + 16.5 * cell, yg + 112, "17", 13, 700, INK, "middle")
    d.t(rx + rw, yg + 112, "60", 13, 400, INK3, "end")
    d.t(rx, yg + 136, "Spill 17: Ida, Detaljist. Sara, Grossist. Mikkel, Distributør. Jonas, Fabrikk.", 14, 400, INK)
    yy = yg + 152
    d.button(rx, yy, 180, 40, "Kjør fordeling på nytt", primary=False, size=14)
    d.button(rx + 192, yy, 170, 40, "Bekreft fordeling", size=14)
    d.t(rx + 378, yy + 25, "Ingen får beskjed før du bekrefter.", 14, 400, INK2)

    # Lagtrappa
    y = yy + 84
    d.t(rx, y, "Hjelpegrad for studentene: Standard", 22, 600, INK)
    d.t(rx, y + 24, "Hvilke lag telefonen viser på hvert trinn. Fylt celle er åpent.", 14, 400, INK2)
    layer_ladder(d, rx, y + 44, rw, rh=23, ls=13, desc=False, label_w=190)

    # Valg over hele bredden
    yb = 1000
    d.line(80, yb - 32, 1360, yb - 32, HAIR2, 1)
    blocks = [(80, "KI-modus", ("LLM-spillere", "Regelbaserte"), "Gjelder alle KI-spillere."),
              (420, "Debrief-modus", ("Gruppedebrief", "Personlig"), "De fire går gjennom det sammen.")]
    for bx, title, opts, desc in blocks:
        d.t(bx, yb, title, 16, 600, INK)
        xx = bx
        for i, o in enumerate(opts):
            wd = text_w(o, 14) + 26
            d.rect(xx, yb + 12, wd, 34, INK if i == 0 else PAPER, None if i == 0 else HAIR2, 1, 5)
            d.t(xx + wd / 2, yb + 34, o, 14, 600, PAPER if i == 0 else INK, "middle")
            xx += wd + 8
        d.t(bx, yb + 70, desc, 14, 400, INK2)
    d.t(760, yb, "Obligatorisk", 16, 600, INK)
    d.rect(760, yb + 16, 52, 28, INK, rx=14)
    d.circle(798, yb + 30, 10, PAPER)
    d.t(824, yb + 35, "Ja, står i emneplanen", 15, 400, INK)
    d.t(760, yb + 70, "Studentene ser at øvelsen er obligatorisk.", 14, 400, INK2)
    d.button(1140, yb + 10, 220, 50, "Lagre Klasseøkt", size=17)
    d.demodata(1360, yb + 84, a="end")
    d.save()


def build_04():
    d = Doc("04-student-hjem", 1000, 900, "Lag for lag, student på mobil", "To telefoner: registrering via Invitasjon, og hjem under spill med stegene og hvilke lag som åpnes når.")
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
    link(d, 112, y + 210, "Logg inn", 14)
    d.end()

    phone(d, 560, 48, s)
    d.t(20, 62, "Spill 17", 28, 700, INK)
    d.t(20, 84, "Du er Grossist", 15, 400, INK2)
    d.rect(20, 100, 350, 244, TINT, None, 1, 6)
    d.t(32, 124, "Spillet venter på deg", 16, 600, INK)
    d.t(358, 124, "Uke 11", 15, 600, INK, "end")
    seat_band(d, G, 11, 32, 136, 326, None, u=0.7, ls=13, vs=14, compact=True)
    d.button(32, 286, 326, 44, "Gå til Uke 11", size=16)
    y = 372
    d.t(20, y, "Setene", 15, 600, INK)
    rows = [("Detaljist", "Ida", "har bestilt", True), ("Grossist", "Sara", "venter (deg)", False),
            ("Distributør", "Mikkel", "har bestilt", True), ("Fabrikk", "Jonas", "venter, 3 min", False)]
    y = waiting_rows(d, y + 26, rows, lh=24)
    y += 6
    d.t(20, y, "Stegene, og hva som åpnes", 15, 600, INK)
    y += 26
    steps = [("Klassespill", "Lag: Graf, Tall, Kostnad", True), ("Debrief", "Åpner Posisjon, Hele kjeden, Simulert", False),
             ("Quiz", None, False), ("Replay", "Åpner Projeksjon", False), ("Individuell test", None, False), ("Rapport", None, False)]
    yl = y - 5
    ys = []
    yy = y
    for st, note, cur in steps:
        ys.append(yy)
        yy += 38 if note else 24
    d.line(26, yl, 26, ys[-1] - 5, HAIR2, 1.5)
    for (st, note, cur), yy in zip(steps, ys):
        if cur:
            d.circle(26, yy - 5, 6, INK)
        else:
            d.circle(26, yy - 5, 5, PAPER, HAIR2, 1.5)
        d.t(42, yy, st, 14, 600 if cur else 400, INK if cur else INK2)
        if cur:
            d.t(370, yy, "pågår", 14, 400, INK, "end")
        if note:
            d.t(42, yy + 17, note, 13, 400, INK2)
    y = ys[-1] + 26
    d.line(20, y - 12, 370, y - 12, HAIR, 1)
    d.t(20, y + 8, "Neste frist", 14, 400, INK2)
    d.t(370, y + 8, "Spillfrist ti. 8. des", 14, 600, INK, "end")
    d.t(20, y + 30, "Labtime", 14, 400, INK2)
    d.t(370, y + 30, "to. 26. nov 14:15, Datalab A2", 14, 600, INK, "end")
    d.demodata(20, y + 54)
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


def build_09():
    d = Doc("09-alle-sider", 2000, 1400, "Lag for lag, alle andre sider", "Kontaktark over øvrige sider for Student, Faglærer og Admin.")
    d.t(40, 56, "Alle andre sider", 34, 700, INK)
    d.t(40, 84, "Kjedebåndet og lagene går igjen der tiden er poenget. Ellers er sidene rolige lister og skjema.", 16, 400, INK2)

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

    # Grupper
    d.t(40, y0 + 22, "Student", 20, 600, INK)
    d.t(40, y0 + 2 * rh + 22, "Faglærer", 20, 600, INK)
    d.line(40, y0 + 2 * rh - 18, 1960, y0 + 2 * rh - 18, HAIR2, 1)

    # 1 Invitasjon
    x, y = cell(0, 0, "Invitasjon og registrering", "Lenke fra e-post, navn og passord. Gyldig i 14 dager.")
    d.t(x + 14, y + 28, "Du er invitert", 15, 700)
    for i in range(3):
        d.rect(x + 14, y + 42 + i * 34, cw - 28, 26, PAPER, HAIR2, 1, 3)
    d.rect(x + 14, y + 148, cw - 28, 30, INK, rx=3)
    # 2 Logg inn
    x, y = cell(1, 0, "Logg inn", "E-post og passord. Ingen åpen registrering.")
    d.t(x + 14, y + 28, "Logg inn", 15, 700)
    for i in range(2):
        d.rect(x + 14, y + 42 + i * 34, cw - 28, 26, PAPER, HAIR2, 1, 3)
    d.rect(x + 14, y + 114, cw - 28, 30, INK, rx=3)
    # 3 Regler
    x, y = cell(2, 0, "Regler før første ordre", "Kjedebåndet forklart på en ekte Uke. Lagene kommer ett om gangen i Veiledede uker.")
    seat_band(d, G, 5, x + 12, y + 10, cw - 24, 4, u=1.4, ls=11, vs=12)
    tabs(d, x + 12, y + th - 36, cw - 24, ["Uke 1", "Uke 2", "Uke 3", "Uke 4"], "Uke 1", h=24, size=11)
    # 4 Startoppgave
    x, y = cell(3, 0, "Startoppgave", "Regn posisjonen for én Uke. Viser hvordan tallene henger sammen.")
    d.t(x + 14, y + 30, f"Lager {G.lager[10]}, restordre {G.rest[10]}, på vei {G.paavei(11)}", 13, 400, INK)
    d.t(x + 14, y + 62, "Posisjon =", 15, 600)
    d.rect(x + 92, y + 44, 60, 28, PAPER, INK, 1.2, 3)
    d.t(x + 122, y + 64, G.posisjon(11), 16, 700, INK, "middle")
    mini_net(d, x + 14, y + 86, cw - 28, 96, G, 11)
    # 5 Replay
    x, y = cell(4, 0, "Replay", "Alle lag åpne, også Posisjon og projeksjonen. Tre KI-spillere. Tilfeldig etterspørsel.")
    meteo(d, RE, x + 10, y + 6, cw - 20, 14, RE.order(14), wmin=3, hn=86, hf=26, gap=4, ls=11, left=20, titles=False, xstep=4, netlabel=False, arrnums=False, ordlabel=False, proj=True, nowlabel="Nå", overduenote=False)
    # 6 Replay-gjennomgang
    x, y = cell(0, 1, "Replay-gjennomgang", "Klassespillet og Replay på samme akse. Ikke like for like.")
    ax = Axis(x + 14, cw - 28, 1, 36)
    Y = yscale(y + 30, 140, -40, 30)
    d.line(ax.x0, Y(0), ax.x1, Y(0), HAIR2, 1)
    d.path("M" + " L".join(f"{ax.xc(k):.1f} {Y(G.net(k)):.1f}" for k in range(1, 37)), stroke=GREY, sw=1.4)
    net_area(d, ax, y + 30, 140, RE.net, 1, RE.n, lw=1.8)
    d.t(x + 14, y + 22, "Klassespill (grå), Replay (farget)", 13, 400, INK2)
    # 7 Individuell test
    x, y = cell(1, 1, "Individuell test", "Flervalg, tegneoppgave i egen graf, og langsvar. Samme tre felt som i spillet.")
    wd = (cw - 40) / 3
    d.t(x + 10, y + 22, "Flervalg", 12, 600)
    for i in range(4):
        d.circle(x + 16, y + 40 + i * 22, 4, PAPER, INK if i != 1 else INK, 1)
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
    # 8 KI-vurdering
    x, y = cell(2, 1, "KI-vurdering", "Tilbakemelding på testen. Teller ikke og er aldri en karakter, og det står der.")
    d.t(x + 14, y + 28, "KI-generert, kan ta feil", 14, 600, INK)
    d.t(x + 14, y + 48, "Teller ikke. Ingen karakter.", 13, 400, INK2)
    lines(d, x + 14, y + 66, cw - 28, 8, 13)
    # 9 Studentrapport
    x, y = cell(3, 1, "Studentrapport (PDF)", "Din graf, dine tall, din kostnad og din Forklaring, klar til å lagre.")
    pw = 124
    px = x + cw / 2 - pw / 2
    d.rect(px, y + 12, pw, th - 24, PAPER, HAIR2, 1)
    d.t(px + 8, y + 30, "Sara, Grossist", 11, 600)
    mini_net(d, px + 8, y + 38, pw - 16, 56, G)
    lines(d, px + 8, y + 104, pw - 16, 5, 11)
    d.t(x + cw - 12, y + th - 14, "PDF", 13, 600, INK2, "end")
    # 10 Alle spill side om side
    x, y = cell(4, 1, "Alle spill side om side", "Etter Debriefen: alle Grossister i klassen, samme skala. Ingen rangering.")
    fer = [s for s in KL["spill"] if s["status"] == "ferdig"][:24]
    gw = (cw - 28) / 6
    gh = (th - 24) / 4
    for i, sp in enumerate(fer):
        xx = x + 14 + (i % 6) * gw
        yy = y + 12 + (i // 6) * gh
        ax = Axis(xx, gw - 6, 1, 36)
        vals = sp["netto_lager"]["Grossist"]
        net_area(d, ax, yy, gh - 6, lambda k: vals[k - 1], 1, 36, -70, 70, lw=1)

    # Faglærer
    x, y = cell(0, 2, "Lærerhjem", "Klassene dine, hva som venter, og neste frist.")
    d.t(x + 14, y + 28, "Klassene dine", 15, 700)
    d.t(x + 14, y + 56, "class-of-1994, IBE160", 14, 600)
    d.t(x + 14, y + 74, "Spillfrist ti. 8. des. 4 spill venter.", 13, 400, INK2)
    d.line(x + 14, y + 86, x + cw - 14, y + 86, HAIR, 1)
    strip(d, x + 14, y + 96, KL["spill"][0], cw=(cw - 28) / 36, lane=8)
    d.t(x + 14, y + 158, "Ny Klasse", 14, 600, BLUE, "start", 'text-decoration="underline"')
    # Klasserapport
    x, y = cell(1, 2, "Klasserapport", "Fordeling av Forsterkning per Rolle, kjedekost og Detected patterns.")
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
    M = KL["moenstre"]
    for k, v in list(M.items())[:2]:
        d.t(x + 12, yy, f"{k}: {v}", 11, 400, INK2)
        yy += 16
    # Spillinnsikt
    x, y = cell(2, 2, "Spillinnsikt (uke for uke)", "Ett spill: hele kjeden og fire meteogrammer. Læreren blar Uke for Uke.")
    yy = y + 10
    ax = Axis(x + 72, cw - 86, 1, 36)
    for r in ["Fabrikk", "Distributør", "Grossist", "Detaljist"]:
        d.t(x + 12, yy + 24, r, 12, 400, INK)
        mini_h = 40
        Y = yscale(yy, mini_h, -70, 60)
        d.line(ax.x0, Y(0), ax.x1, Y(0), HAIR2, 1)
        net_area(d, ax, yy, mini_h, SEATS[r].net, 1, 36, -70, 60, lw=1.2)
        yy += 44
    d.line(ax.xc(11), y + 6, ax.xc(11), y + th - 8, INK, 1.2)
    # Studentside
    x, y = cell(3, 2, "Studentside", "Én students steg, Forklaring, testsvar og rapport. Hele løpet på én side.")
    d.t(x + 14, y + 28, "Sara, Grossist, Spill 17", 14, 700)
    labels = ["Klassespill", "Debrief", "Quiz", "Replay", "Test", "Rapport"]
    sw = (cw - 28) / 6
    d.line(x + 14 + sw / 2, y + 48, x + 14 + 5.5 * sw, y + 48, HAIR2, 1.2)
    for i, l in enumerate(labels):
        d.circle(x + 14 + (i + 0.5) * sw, y + 48, 5, INK if i == 0 else PAPER, INK if i == 0 else HAIR2, 1.2)
        d.t(x + 14 + (i + 0.5) * sw, y + 70, l, 11, 400, INK2, "middle")
    mini_net(d, x + 14, y + 84, cw - 28, 96, G, 11)
    # Plenum
    x, y = cell(4, 2, "Alle spill i plenum", "60 striper på lerretet. Mønsteret går igjen, uten navn og uten rangering.")
    sp = KL["spill"]
    gw = (cw - 20) / 6
    gh = (th - 16) / 10
    for i, s in enumerate(sp):
        strip(d, x + 10 + (i % 6) * gw, y + 8 + (i // 6) * gh, s, cw=(gw - 5) / 36, lane=3.6)

    # rad 4
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
    # Meldinger
    x, y = cell(1, 3, "Meldinger", "Fra Faglærer til ett spill, en gruppe eller hele Klassen. Ingen chat mellom spillere.")
    d.t(x + 14, y + 28, "Melding til Noah, Spill 2", 14, 700)
    d.rect(x + 14, y + 40, cw - 28, 74, PAPER, HAIR2, 1, 3)
    d.para(x + 22, y + 60, "Gruppa venter på ordren din. KI overtar setet om 1 t.", cw - 44, 13, 17)
    d.rect(x + 14, y + 124, 100, 28, INK, rx=3)
    d.t(x + 64, y + 143, "Send", 13, 600, PAPER, "middle")
    d.t(x + 14, y + 176, "Sendt tidligere: 3", 13, 400, INK2)
    # Lærers testspill
    x, y = cell(2, 3, "Lærers testspill", "Spill selv mot tre KI-spillere før klassen starter. Telles ikke med.")
    meteo(d, RE, x + 10, y + 6, cw - 20, 9, RE.order(9), wmin=1, hn=86, hf=26, gap=4, ls=11, left=20, titles=False, xstep=4, netlabel=False, arrnums=False, ordlabel=False, nowlabel="Nå", overduenote=False)
    # Admin: tre smalere felt
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
