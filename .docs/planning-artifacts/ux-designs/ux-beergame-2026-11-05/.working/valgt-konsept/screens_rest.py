"""01 landing, 02 Klasse, 03 Klasseøkt, 04 student hjem, 09 kontaktark."""
from datetime import date

from vlib import *
from screens_core import NAME, phone, waiting_rows
from screens_debrief_teacher import UP, demand_band

STATUS = {"venter": "Venter", "pauset": "Pause", "pågår": "Pågår", "ferdig": "Ferdig"}


def field(d, x, y, w, label, value, h=42, size=15, muted=False):
    d.t(x, y, label, 14, 600, INK)
    d.rect(x, y + 8, w, h, PAPER, HAIR2, 1, 5)
    d.t(x + 12, y + 8 + h / 2 + size * 0.34, value, size, 400, INK3 if muted else INK)
    return y + 8 + h


def cells(d, x, y, vals, cw, ch, nums=False, size=11):
    """Netto lager som celler på rad. Med tall når det er plass."""
    for k, v in enumerate(vals):
        f, c = net_cell(v)
        d.rect(x + k * cw + 0.3, y, cw - 0.6, ch, f)
        if nums:
            d.t(x + k * cw + cw / 2, y + ch / 2 + size * 0.36, sg(v), size, 400, c, "middle")


def wall(d, x, y, sp, cw, lane, roles=UP, gap=0.6):
    for i, r in enumerate(roles):
        cells(d, x, y + i * (lane + gap), sp["netto_lager"][r], cw, lane)


# ---------- 01 ----------
def build_01():
    """Landingssiden røper ikke etterspørselen: setet vises i Uke 4, før noe har endret seg,
    og lærerens oversikt viser status og framdrift, ikke lagerkurver."""
    d = Doc("01-landing", 1440, 1200, f"{NAME}, landingsside for faglærere",
            "Første skjermbilde bæres av ett setes kjedebånd, graf over tabell og Kostnad så langt i en Veiledet uke. "
            "Neste seksjon viser lærerens oversikt med status, framdrift og hvem hvert spill venter på.")
    d.t(80, 58, NAME, 22, 700, INK)
    d.t(1360, 56, "For faglærere", 16, 400, INK2, "end")
    d.line(80, 78, 1360, 78, HAIR, 1)
    d.para(80, 146, "Hver uke har en strek og et tall. Studentene ser begge.", 760, 48, 56, 700, INK)
    d.para(900, 124, "Kjører hele forsyningskjedeøvelsen for emnet ditt, fra Invitasjon til PDF-rapport. På norsk, på mobil, for klasser på rundt 250 studenter.", 460, 19, 27, fill=INK)
    d.button(900, 230, 210, 50, "Be om lærertilgang", size=17)
    d.button(1124, 230, 110, 50, "Logg inn", primary=False, size=17)

    wk = 4
    y = 320
    d.t(80, y, f"Ett sete, Grossist, Uke {wk}. Veiledet uke.", 17, 600, INK)
    d.t(1360, y, "Studenten ser bare sine egne tall. Tidsaksen slutter fire uker etter nå. Demodata.", 15, 400, INK2, "end")
    gw = 860
    yb = chain_seat(d, G, 80, y + 18, gw, wk, G.order(wk), ls=15, upipe=2.6)
    gtable(d, G, 80, yb + 18, gw, wk, G.order(wk), wmin=1, wmax=wk + 4, lw=130, ls=15, rh=26, hn=116, hc=40,
           rows=("inn", "lev", "net", "pv", "ord", "kost"), labels={"kost": "Kost per uke"}, cmax=20,
           t_net="Lager over null, restordre under. Samme kolonne: strek over, tall under.")
    cx = 1000
    cost_panel(d, cx, y + 60, 360, G, wk, h=96, size=15, tsize=17, lh=34)
    d.para(cx, y + 420, "Kostnaden står ved ordrefeltet hele spillet: to kostnadsarter, summen, og regnestykket for uka.", 360, 15, 21, fill=INK2)
    d.para(cx, y + 490, "Ordren tegnes to ganger: der den bestilles, og fire kolonner senere der den kommer.", 360, 15, 21, fill=INK2)

    y2 = 940
    d.line(80, y2 - 48, 1360, y2 - 48, HAIR, 1)
    d.t(80, y2, "Alle spillene på én skjerm", 30, 700, INK)
    spill = KL["spill"]
    rank = {"venter": 0, "pauset": 1, "pågår": 2, "ferdig": 3}
    rows = sorted(spill, key=lambda s: (rank[s["status"]], -(s.get("ventet_timer") or 0), -s["uke"]))[:6]
    yy = y2 + 34
    for cx_, h, a in [(80, "Spill", "start"), (136, "Status", "start"), (216, "Uker spilt", "start"), (676, "Uke", "end"),
                      (706, "KI", "start"), (744, "Venter på", "start")]:
        d.t(cx_, yy, h, 14, 600, INK2, a)
    d.line(80, yy + 7, 840, yy + 7, HAIR2, 1)
    yy += 28
    cw = 12
    for sp in rows:
        d.t(80, yy, sp["spill"], 15, 600, INK)
        d.t(136, yy, STATUS[sp["status"]], 15, 400, INK)
        for k in range(sp["uke"]):
            d.rect(216 + k * cw + 0.5, yy - 13, cw - 1, 15, BASE)
        d.t(676, yy, sp["uke"], 15, 400, INK, "end")
        d.t(706, yy, sp["ki_seter"] or "", 15, 400, INK)
        if sp["status"] == "venter":
            d.t(744, yy, f"{sp['navn']}, {sp['ventet_timer']} t", 15, 600 if sp["ventet_timer"] >= 20 else 400, INK)
        elif sp["status"] == "pauset":
            d.t(744, yy, "Pause", 15, 400, INK2)
        yy += 27
    d.t(80, yy + 8, "Lagerkurvene for hele klassen ser du først når du er logget inn.", 14, 400, INK2)
    fy = y2 + 34
    for f in ("KI-spillere fyller tomme seter, alltid merket.", "Ett fravær stopper ikke gruppa, og ingen spill blir stående uferdig.",
              "Studentlisten kommer fra Canvas-eksport.", "Du ser hvem hvert spill venter på, og hvor lenge."):
        fy = d.para(900, fy, f, 460, 17, 23) + 10
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
def build_03():
    d = Doc("03-laerer-spill", 1440, 1100, f"{NAME}, Klasseøkt",
            "Forhåndsutfylte Spillinnstillinger, KI-modus, Debrief-modus, Obligatorisk, datoer, Labtimer og fordeling av 60 spill.")
    d.t(80, 62, "Klasseøkt for class-of-1994", 34, 700, INK)
    d.t(80, 90, "Alt er fylt ut med standardene.", 16, 400, INK2)
    
    # Venstre
    lx, lw = 80, 560
    y = 140
    d.t(lx, y, "Spillinnstillinger: Klassisk", 22, 600, INK)
    y += 34
    rows = [("Startlager", "12"), ("I hvert ledd ved start", "4 enheter"), ("Ordreforsinkelse", "2 uker"), ("Fraktforsinkelse", "2 uker"),
            ("Produksjonsforsinkelse", "2 uker"), ("Lagerkost", "0,50 per enhet per uke"), ("Restordrekost", "1,00 per enhet per uke"),
            ("Antall uker", "36"), ("Etterspørsel", "4, så 8 fra Uke 5"), ("Veiledede uker", "1–4"), ("Inaktivitetsgrense", "24 t, så KI overtar")]
    for lab, v in rows:
        d.t(lx, y, lab, 15, 400, INK)
        d.t(lx + lw, y, v, 15, 600, INK, "end")
        d.line(lx, y + 10, lx + lw, y + 10, HAIR, 1)
        y += 31
    y += 6
    y = d.para(lx, y, "Kildene er uenige om forsinkelsene. Dette er produktets standard, og du kan endre den.", lw, 14, 19, fill=INK2)
    y += 22
    # Kjeden ved start, slik innstillingene står
    d.t(lx, y, "Kjeden ved start", 15, 600, INK)
    d.t(lx + lw, y, "Varer mot høyre, ordre mot venstre", 14, 400, INK2, "end")
    yk = y + 26
    order = ["Fabrikk", "Distributør", "Grossist", "Detaljist"]
    nw, u = 48, 2.6
    xs = [lx + 100 + i * 110 for i in range(4)]
    yg = yk + 46
    for i, r in enumerate(order):
        xn = xs[i]
        d.rect(xn - nw / 2, yk + 6, nw, 52, PAPER, HAIR2, 1)
        d.rect(xn - nw / 2 + 4, yg - 12 * u, nw - 8, 12 * u, BLUE)
        d.t(xn, yk + 76, r, 13, 600, INK, "middle")
        d.t(xn, yk + 93, "Lager 12", 13, 400, INK2, "middle")
        x0 = xn - nw / 2 - 60
        x1_ = xn - nw / 2 - 2
        arrow(d, x0, yg - 4, x1_, ORD, 2, 6)
        for j in range(2):
            bx = x0 + 8 + j * 22
            d.rect(bx, yg - 10, 4 * u + 6, 12, PAPER, BLUE, 1)
        if i > 0:
            d.t((x0 + x1_) / 2 - 4, yg - 16, "2 uker", 12, 400, INK2, "middle")
            for j in range(2):
                d.circle(x0 + 14 + j * 22, yk + 108, 3, INK)
            d.line(x0 + 4, yk + 108, x1_, yk + 108, INK, 1)
        else:
            d.t((x0 + x1_) / 2 - 4, yg - 16, "2 uker", 12, 400, INK2, "middle")
    arrow(d, xs[3] + nw / 2 + 2, yg - 4, lx + lw - 72, ORD, 2, 6)
    d.t(lx + lw - 64, yg - 8, "Kundene", 13, 600, INK)
    d.t(lx + lw - 64, yg + 9, "4, så 8", 13, 600, BLUE)
    d.t(lx + lw - 64, yg + 25, "fra Uke 5", 13, 400, INK2)
    d.para(lx, yk + 132, "Hver boks på røret er 4 enheter. Frakt mellom leddene og produksjon inn til Fabrikk tar 2 uker. Prikkene er ordre på vei, også 2 uker. Studentene ser ikke kundene under spillet.", lw, 14, 19, fill=INK2)
    # Høyre: datoer på én tidsakse
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
    for i, (dt, lab, ds) in enumerate(marks):
        x = xd(dt)
        d.line(x, ya - 14, x, ya + 8, INK, 1.6)
        anch = "end" if dt == end else ("start" if dt == start else "middle")
        ty = ya - 44
        if lab == "Debrief-frist":
            anch = "start"
            x = x - 8
        if lab == "Spillfrist":
            anch = "end"
            x = x + 10
        d.t(x, ty, lab, 15, 600, INK, anch)
        d.t(x, ty + 18, ds, 14, 400, INK2, anch)
    labs = [(date(2026, 11, 26), "to. 26. nov", "14:15"), (date(2026, 11, 30), "ma. 30. nov", "10:15"), (date(2026, 12, 3), "to. 3. des", "14:15"), (date(2026, 12, 7), "ma. 7. des", "10:15")]
    for dt, ds, kl in labs:
        x = xd(dt)
        d.rect(x - 4, ya + 8, 8, 8, BLUE)
        d.t(x, ya + 34, ds, 14, 400, INK, "middle")
        d.t(x, ya + 52, kl, 14, 400, INK2, "middle")
    d.t(rx, ya + 80, "Blå firkant: Labtime, Datalab A2.", 14, 400, INK2)
    d.t(rx + rw, ya + 80, "Legg til Labtime", 14, 600, BLUE, "end", 'text-decoration="underline"')

    # Fordeling
    y = ya + 146
    d.t(rx, y, "Fordeling: 60 Klassespill à 4", 22, 600, INK)
    d.para(rx, y + 26, f"{KL['traktA']['registrert']} studenter fordeles tilfeldig. Hver søyle er ett spill, hver rad en Rolle. Tomme seter får KI-spiller.", rw, 15, 20, fill=INK2)
    yg = y + 80
    roles = ["Detaljist", "Grossist", "Distributør", "Fabrikk"]
    cell = (rw - 84) / 60
    for j, r in enumerate(roles):
        d.t(rx, yg + j * 34 + 21, r, 14, 400, INK)
        for i in range(60):
            d.rect(rx + 84 + i * cell, yg + j * 34, cell - 2, 30, BASE)
    # Spill 17 uthevet som eksempel
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
    # Valg over hele bredden
    yb = 880
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
    d.button(1140, 1000, 220, 52, "Lagre Klasseøkt", size=17)
    d.t(1124, 1032, "Du kan lagre uten å endre noe.", 15, 400, INK2, "end")
    d.demodata(80, 1032)
    d.save()


# ---------- 04 ----------
def build_04():
    d = Doc("04-student-hjem", 1000, 900, f"{NAME}, student på mobil", "To telefoner: registrering via Invitasjon, og hjem under spill.")
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
    d.rect(16, 100, 358, 250, PAPER, HAIR2, 1, 6)
    d.t(28, 124, "Spillet venter på deg", 16, 600, INK)
    d.t(362, 124, "Uke 11", 15, 600, INK, "end")
    gtable(d, G, 28, 138, 334, 11, None, wmin=4, wmax=15, lw=72, hn=62, rh=20, rows=("net", "ord"), cost_field=False,
           titles=False, netlabel=False, ticks=(-20, 0, 20))
    d.t(28, 302, f"Totalkostnad {nf(G.kostsum(11))} kr", 14, 400, INK2)
    d.button(200, 284, 162, 44, "Gå til Uke 11", size=15)
    y = 382
    d.t(20, y, "Setene", 15, 600, INK)
    rows = [("Detaljist", "Ida", "har bestilt", True), ("Grossist", "Sara", "venter (deg)", False),
            ("Distributør", "Mikkel", "har bestilt", True), ("Fabrikk", "Jonas", "venter, 3 min", False)]
    y = waiting_rows(d, y + 26, rows, lh=26)
    y += 10
    d.t(20, y, "Stegene", 15, 600, INK)
    y += 26
    steps = ["Klassespill", "Debrief", "Quiz", "Replay", "Individuell test", "Rapport"]
    d.line(26, y - 5, 26, y - 5 + 5 * 24, HAIR2, 1.5)
    for i, st in enumerate(steps):
        yy = y + i * 24
        if i == 0:
            d.circle(26, yy - 5, 6, INK)
        else:
            d.circle(26, yy - 5, 5, PAPER, HAIR2, 1.5)
        d.t(42, yy, st, 14, 600 if i == 0 else 400, INK if i == 0 else INK2)
        if i == 0:
            d.t(370, yy, "pågår", 14, 400, INK, "end")
    y += 6 * 24 + 4
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


def mini_gt(d, g, x, y, w, now, typed=None, rows=("lev", "net", "ord"), wmin=None, proj=False, hn=56, cost=False, labels=None):
    return gtable(d, g, x, y, w, now, typed, wmin=wmin or max(1, now - 7), wmax=now + 4, lw=58, ls=10, rh=12, hn=hn, hc=16,
                  rows=rows, titles=False, netlabel=False, cost_field=cost, cost_tick=False, proj=proj, gapf=4,
                  nowlabel="Nå", labels=labels)


def build_09():
    d = Doc("09-alle-sider", 2000, 1400, f"{NAME}, alle andre sider", "Kontaktark over øvrige sider for Student, Faglærer og Admin.")
    d.t(40, 56, "Alle andre sider", 34, 700, INK)
    d.t(40, 84, "Der tiden er poenget, står grafen over tabellen med felles ukekolonner. Ellers er sidene rolige lister og skjema.", 16, 400, INK2)
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
    x, y = cell(2, 0, "Regler før første ordre", "Én ekte Uke forklart: kolonnen, nå-streken, og at ordren kommer fire kolonner senere.")
    mini_gt(d, G, x + 10, y + 12, cw - 20, 5, 4, rows=("inn", "lev", "net", "ord"), wmin=1, hn=70)
    x, y = cell(3, 0, "Startoppgave", "Regn posisjonen for én Uke fra cellene i kolonnen. Viser hvordan radene henger sammen.")
    d.t(x + 14, y + 28, "Kolonne 11", 13, 600, INK)
    rows_ = [("Lager", G.lager[10]), ("Restordre", G.rest[10]), ("På vei", G.paavei(11))]
    for i, (lab, v) in enumerate(rows_):
        yy = y + 52 + i * 26
        d.t(x + 14, yy, lab, 13, 400, INK)
        d.rect(x + 120, yy - 15, 44, 21, PAPER, HAIR2, 1, 3)
        d.t(x + 142, yy, v, 13, 600, INK, "middle")
    d.t(x + 14, y + 150, "Posisjon =", 15, 600)
    d.rect(x + 104, y + 132, 60, 28, PAPER, INK, 1.2, 3)
    d.t(x + 134, y + 152, G.posisjon(11), 16, 700, INK, "middle")
    d.t(x + 180, y + 152, "Lager − Restordre + På vei", 12, 400, INK2)
    x, y = cell(4, 0, "Replay", "Samme skjerm, nå med raden Posisjon og projeksjonen. Tre KI-spillere. Tilfeldig etterspørsel.")
    mini_gt(d, RE, x + 10, y + 12, cw - 20, 14, RE.order(14), rows=("lev", "net", "pv", "pos", "ord"), proj=True, hn=70)
    x, y = cell(0, 1, "Replay-gjennomgang", "Klassespillet og Replay på samme ukeakse, med kostnaden som rad under. Ikke like for like.")
    ax = Axis(x + 70, cw - 84, 1, 36)
    Y = yscale(y + 16, 104, -40, 30)
    d.line(ax.x0, Y(0), ax.x1, Y(0), HAIR2, 1)
    d.path(pts_path([(ax.xc(k), Y(G.net(k))) for k in range(1, 37)]), stroke=GREY, sw=1.4)
    net_area(d, ax, y + 16, 104, RE.net, 1, RE.n, lw=1.8)
    d.t(x + 12, y + 30, "Netto lager", 11, 600)
    d.t(x + 12, y + 44, "grå: Klassespill", 10, 400, INK2)
    for i, (lab, S) in enumerate((("Kr, Klassespill", G), ("Kr, Replay", RE))):
        yy = y + 138 + i * 18
        d.t(x + 12, yy, lab, 10, 400, INK)
        for k in range(4, S.n + 1, 8):
            d.t(ax.xc(k), yy, sg(int(S.kostsum(k) + 0.5)), 10, 400, INK, "middle")
    d.t(x + 12, y + 186, f"Sum: {nf(G.kostsum(36))} mot {nf(RE.kostsum(RE.n))} kr", 11, 600, INK)
    x, y = cell(1, 1, "Individuell test", "Flervalg, en tabelloppgave der studenten fyller inn kolonnen, og langsvar.")
    wd = (cw - 40) / 3
    d.t(x + 10, y + 22, "Flervalg", 12, 600)
    for i in range(4):
        d.circle(x + 16, y + 40 + i * 22, 4, PAPER, INK, 1)
        d.rect(x + 26, y + 37 + i * 22, wd - 34, 5, HAIR)
    xm = x + 10 + wd + 10
    d.t(xm, y + 22, "Fyll inn kolonnen", 12, 600)
    for i, (lab, v) in enumerate((("Netto", sg(G.net(10))), ("Lev.", G.levering(11)), ("Inn", G.inn(11)), ("Netto", None))):
        yy = y + 46 + i * 26
        d.t(xm, yy, lab, 11, 400, INK)
        d.rect(xm + 44, yy - 14, wd - 48, 20, PAPER, INK if v is None else HAIR2, 1.2 if v is None else 1, 3)
        d.t(xm + 44 + (wd - 48) / 2, yy, v if v is not None else "?", 12, 600, INK, "middle")
    xl = xm + wd + 10
    d.t(xl, y + 22, "Langsvar", 12, 600)
    d.rect(xl, y + 32, wd, 130, PAPER, HAIR2, 1, 3)
    lines(d, xl + 8, y + 44, wd - 16, 6)
    x, y = cell(2, 1, "KI-vurdering", "Tilbakemelding på testen. Teller ikke og er aldri en karakter, og det står der.")
    d.t(x + 14, y + 28, "KI-generert, kan ta feil", 14, 600, INK)
    d.t(x + 14, y + 48, "Teller ikke. Ingen karakter.", 13, 400, INK2)
    lines(d, x + 14, y + 66, cw - 28, 8, 13)
    x, y = cell(3, 1, "Studentrapport (PDF)", "Din graf over tabell, dine beslutninger, din kostnad og din Forklaring.")
    pw = 150
    px = x + cw / 2 - pw / 2
    d.rect(px, y + 10, pw, th - 20, PAPER, HAIR2, 1)
    d.t(px + 8, y + 26, "Sara, Grossist", 11, 600)
    axp = Axis(px + 8, pw - 16, 1, 36)
    Yp = yscale(y + 34, 44, -40, 30)
    d.line(axp.x0, Yp(0), axp.x1, Yp(0), HAIR2, 1)
    net_area(d, axp, y + 34, 44, G.net, 1, 36, lw=1.2)
    cells(d, px + 8, y + 82, G.net_, (pw - 16) / 36, 8)
    lines(d, px + 8, y + 104, pw - 16, 6, 11)
    d.t(x + cw - 12, y + th - 14, "PDF", 13, 600, INK2, "end")
    x, y = cell(4, 1, "Alle spill side om side", "Etter Debriefen: alle Grossister i klassen, samme skala. Ingen rangering.")
    fer = [s for s in KL["spill"] if s["status"] == "ferdig"][:16]
    for i, sp in enumerate(fer):
        yy = y + 12 + i * 12
        cells(d, x + 14, yy, sp["netto_lager"]["Grossist"], (cw - 28) / 36, 10)

    x, y = cell(0, 2, "Lærerhjem", "Klassene dine, hva som venter, og neste frist.")
    d.t(x + 14, y + 28, "Klassene dine", 15, 700)
    d.t(x + 14, y + 56, "class-of-1994, IBE160", 14, 600)
    d.t(x + 14, y + 74, "Spillfrist ti. 8. des. 4 spill venter.", 13, 400, INK2)
    d.line(x + 14, y + 86, x + cw - 14, y + 86, HAIR, 1)
    wall(d, x + 14, y + 96, KL["spill"][0], (cw - 28) / 36, 9)
    d.t(x + 14, y + 158, "Ny Klasse", 14, 600, BLUE, "start", 'text-decoration="underline"')
    x, y = cell(1, 2, "Klasserapport", "Kjedekost og Forsterkning per Rolle, kostnad per kostnadsart, og Detected patterns.")
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
    x, y = cell(2, 2, "Spillinnsikt (uke for uke)", "Ett spill: hele kjeden i valgt Uke over matrisen Rolle × uke. Læreren blar Uke for Uke.")
    chain_full(d, SEATS, x + 4, y + 4, cw - 8, 11, ls=9, un=0.3, upipe=0.5, cost=False, names=False, demand=True, order_row=False)
    ax = Axis(x + 64, cw - 76, 1, 36)
    yy = y + 128
    for r in UP:
        d.t(x + 12, yy + 9, r, 10, 400, INK)
        cells(d, ax.x0, yy, SEATS[r].net_, ax.slot, 11)
        yy += 13
    d.line(ax.xr(11), y + 122, ax.xr(11), yy + 2, INK, 1.4)
    x, y = cell(3, 2, "Studentside", "Én students steg, Forklaring, testsvar og rapport.")
    d.t(x + 14, y + 28, "Sara, Grossist, Spill 17", 14, 700)
    labels = ["Klassespill", "Debrief", "Quiz", "Replay", "Test", "Rapport"]
    sw = (cw - 28) / 6
    d.line(x + 14 + sw / 2, y + 48, x + 14 + 5.5 * sw, y + 48, HAIR2, 1.2)
    for i, l in enumerate(labels):
        d.circle(x + 14 + (i + 0.5) * sw, y + 48, 5, INK if i < 2 else PAPER, INK if i < 2 else HAIR2, 1.2)
        d.t(x + 14 + (i + 0.5) * sw, y + 70, l, 11, 400, INK2, "middle")
    mini_gt(d, G, x + 10, y + 86, cw - 20, 11, 24, rows=("net", "ord"), hn=50)
    x, y = cell(4, 2, "Alle spill i plenum", "60 spill som matrise på lerretet. Mønsteret går igjen, uten navn og uten rangering.")
    sp_ = KL["spill"]
    gw = (cw - 20) / 6
    gh = (th - 16) / 10
    for i, s in enumerate(sp_):
        wall(d, x + 10 + (i % 6) * gw, y + 8 + (i // 6) * gh, s, (gw - 5) / 36, 3.6, gap=0.4)

    x, y = cell(0, 3, "Tverrklasse-statistikk", "Klassen mot fjoråret. Samme mål, samme regnestykke. Demodata.")
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
    mini_gt(d, RE, x + 10, y + 12, cw - 20, 9, RE.order(9), rows=("inn", "lev", "net", "ord"), wmin=1, hn=70)
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
