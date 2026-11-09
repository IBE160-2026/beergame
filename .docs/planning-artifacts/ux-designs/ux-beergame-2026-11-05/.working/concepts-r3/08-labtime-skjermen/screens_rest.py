"""01 landing, 02 Klasse, 03 Klasseøkt, 04 student hjem, 09 kontaktark."""
from datetime import date

from e08grid import *
from screens_core import NAME, waiting_rows, labtime
from screens_debrief_teacher import demand_band, wall_row, med_net, med_ord, FERDIG, SPILL, ORDER_UP, status_txt

RE = Seat("Grossist", FX["replay_sara"])


def field(d, x, y, w, label, value, h=42, size=15, muted=False):
    d.t(x, y, label, 14, 600, INK)
    d.rect(x, y + 8, w, h, PAPER, HAIR2, 1, 5)
    d.t(x + 12, y + 8 + h / 2 + size * 0.34, value, size, 400, INK3 if muted else INK)
    return y + 8 + h


# ---------- 01 ----------
def build_01():
    d = Doc("01-landing", 1440, 1200, f"{NAME}, landingsside for faglærere",
            "Første skjermbilde bæres av rutenettet for ett sete: kjede, graf, tall og kostnad på én skjerm. Neste seksjon viser lærerens oversikt.")
    d.t(80, 58, NAME, 24, 700, INK)
    d.t(1360, 56, "For faglærere", 16, 400, INK2, "end")
    d.line(80, 78, 1360, 78, HAIR, 1)
    d.para(80, 148, "Kjeden, grafen og tallene på én skjerm. Studenten bestemmer, systemet regner.", 780, 46, 54, 700, INK)
    d.para(920, 128, f"{NAME} kjører hele forsyningskjedeøvelsen for emnet ditt, fra Invitasjon til PDF-rapport. På norsk, på mobil og på laptop i Labtime, for klasser på rundt 250 studenter.", 440, 18, 26, fill=INK)
    d.button(920, 236, 210, 50, "Be om lærertilgang", size=17)
    d.button(1144, 236, 110, 50, "Logg inn", primary=False, size=17)
    L = labtime(d, 80, 306, 1280, 600, G, 18, G.order(18), wait=False, chain_u=1.3)
    d.t(80, 306 + L["H"] + 24, "Ett sete, Grossist, Uke 18. Studenten ser bare sine egne tall, og tidsaksen viser aldri når spillet slutter. Demodata.", 15, 400, INK2)

    y2 = 306 + L["H"] + 92
    d.line(80, y2 - 32, 1360, y2 - 32, HAIR, 1)
    d.t(80, y2, "Alle spillene på én skjerm", 26, 700, INK)
    rank = {"venter": 0, "pauset": 1, "pågår": 2, "ferdig": 3}
    rows = sorted(SPILL, key=lambda s: (rank[s["status"]], -(s.get("ventet_timer") or 0), -s["uke"]))[:3]
    yy = y2 + 26
    for sp in rows:
        d.t(80, yy, f"Spill {sp['spill']}", 14, 600, INK)
        d.t(150, yy, status_txt(sp), 14, 400, INK)
        wall_row(d, 220, yy - 11, sp, "Grossist", 9, 12)
        d.t(560, yy, f"Uke {sp['uke']}", 14, 400, INK)
        if sp["status"] == "venter":
            d.t(630, yy, f"venter på {sp['navn']}, {sp['ventet_timer']} t", 14, 400, INK)
        yy += 20
    facts = ["KI-spillere fyller tomme seter, alltid merket.", "Ett fravær stopper ikke gruppa, og ingen spill blir stående uferdig.",
             ]
    fy = y2 - 6
    for f in facts:
        fy = d.para(920, fy, f, 440, 16, 21) + 4
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
    rows = [("Startlager", "12"), ("I hvert ledd ved start", "4 enheter"), ("Etterspørsel", "4, så 8 fra Uke 5"), ("Ordreforsinkelse", "2 uker"), ("Fraktforsinkelse", "2 uker"),
            ("Produksjonsforsinkelse", "2 uker"), ("Lagerkost", "0,50 per enhet per uke"), ("Restordrekost", "1,00 per enhet per uke"),
            ("Antall uker", "36"), ("Veiledede uker", "1–4"), ("Inaktivitetsgrense", "24 t, så KI overtar")]
    for lab, v in rows:
        d.t(lx, y, lab, 15, 400, INK)
        d.t(lx + lw, y, v, 15, 600, INK, "end")
        d.line(lx, y + 10, lx + lw, y + 10, HAIR, 1)
        y += 34
    y += 6
    y = d.para(lx, y, "Kildene er uenige om forsinkelsene. Dette er produktets standard, og du kan endre den.", lw, 14, 19, fill=INK2)
    y += 22
    # Kjeden slik innstillingene står: startlager og det som er på vei ved start
    d.t(lx, y, "Kjeden ved start", 15, 600, INK)
    d.t(lx + lw, y, "Endres når du endrer tallene over", 14, 400, INK2, "end")
    start = 12
    pipe = 4
    u = 2.6
    yb = y + 30 + 12 * u + 20
    kund = 64
    seg = (lw - kund) / 4
    d.line(lx, yb, lx + lw, yb, HAIR2, 1)
    d.t(lx, yb - 4, "Kundene", 13, 600, INK)
    d.t(lx, yb + 18, "4, så 8", 13, 400, INK2)
    for i, r in enumerate(ORDER_UP):
        x0 = lx + kund + i * seg
        d.rect(x0, yb - start * u, 22, start * u, BLUEF, BLUE, 1.2)
        d.t(x0 + 11, yb - start * u - 5, start, 13, 600, INK, "middle")
        d.t(x0, yb + 18, r, 13, 600, INK)
        for j in range(2):
            xx = x0 + 32 + j * 22
            d.rect(xx, yb - pipe * u, 18, pipe * u, PAPER, BLUE, 1)
        d.t(x0 + 32, yb - pipe * u - 5, "4 + 4", 12, 400, INK, "start")
        d.t(x0, yb + 36, "produksjon 2 + 2 uker" if r == "Fabrikk" else "ordre 2 + frakt 2 uker", 12, 400, INK2)
    y = yb + 52
    d.para(lx, y, "Blå boks: startlager 12. Åpne bokser: 4 enheter på vei i hver av de to ukene. Samme tegning som studentene ser i kjeden sin.", lw, 13, 17, fill=INK2)
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
    # venter på deg
    d.rect(20, 100, 350, 214, TINT, None, 1, 6)
    d.t(32, 124, "Spillet venter på deg", 16, 600, INK)
    d.t(358, 124, "Uke 11", 15, 600, INK, "end")
    chain_seat(d, 30, 136, 330, G, 11, None, u=0.8, ls=13, compact=True)
    d.button(32, 252, 326, 48, "Gå til Uke 11", size=16)
    y = 344
    d.t(20, y, "Setene", 15, 600, INK)
    rows = [("Detaljist", "Ida", "har bestilt", True), ("Grossist", "Sara", "venter (deg)", False),
            ("Distributør", "Mikkel", "har bestilt", True), ("Fabrikk", "Jonas", "venter, 3 min", False)]
    y = waiting_rows(d, y + 26, rows, lh=27)
    # seks steg
    y += 14
    d.t(20, y, "Stegene", 15, 600, INK)
    y += 26
    steps = ["Klassespill", "Debrief", "Quiz", "Replay", "Individuell test", "Rapport"]
    yl = y - 5
    d.line(26, yl, 26, yl + 5 * 26, HAIR2, 1.5)
    for i, st in enumerate(steps):
        yy = y + i * 26
        if i == 0:
            d.circle(26, yy - 5, 6, INK)
        else:
            d.circle(26, yy - 5, 5, PAPER, HAIR2, 1.5)
        d.t(42, yy, st, 14, 600 if i == 0 else 400, INK if i == 0 else INK2)
        if i == 0:
            d.t(370, yy, "pågår", 14, 400, INK, "end")
    y += 6 * 26 + 6
    d.line(20, y - 14, 370, y - 14, HAIR, 1)
    d.t(20, y + 6, "Neste frist", 14, 400, INK2)
    d.t(370, y + 6, "Spillfrist ti. 8. des", 14, 600, INK, "end")
    d.t(20, y + 30, "Labtime", 14, 400, INK2)
    d.t(370, y + 30, "to. 26. nov 14:15, Datalab A2", 14, 600, INK, "end")
    d.demodata(20, y + 56)
    d.end()
    d.save()


# ---------- Plenum ----------
def plenum_live(d, x, y, s):
    """Plenum under Labtime, tegnet i 1280×720 og skalert. Bare status, ingen spilldata."""
    d.rect(x, y, 1280 * s, 720 * s, PAPER, HAIR2, 1.2, 6)
    d.g(f"translate({x:.1f},{y:.1f}) scale({s:.4f})")
    cnt = {k: sum(1 for sp in SPILL if sp["status"] == k) for k in ("venter", "pauset", "pågår", "ferdig")}
    d.t(48, 74, "Labtime, class-of-1994", 40, 700, INK)
    d.t(48, 120, f"{cnt['pågår']} spill i gang · {cnt['venter']} venter på en ordre · {cnt['pauset']} i Pause · {cnt['ferdig']} ferdige", 26, 400, INK2)
    cols = 10
    cwid = (1280 - 96) / cols
    for i, sp in enumerate(sorted(SPILL, key=lambda q: q["spill"])):
        cx = 48 + (i % cols) * cwid
        cy = 160 + (i // cols) * 88
        stt = sp["status"]
        d.rect(cx, cy, cwid - 10, 78, PAPER if stt != "ferdig" else TINT, INK if stt == "venter" else HAIR2, 2.4 if stt == "venter" else 1.2, 6)
        d.t(cx + 12, cy + 32, sp["spill"], 24, 700, INK)
        lab = {"venter": "Venter", "pauset": "Pause", "pågår": "Uke " + str(sp["uke"]), "ferdig": "Ferdig"}[stt]
        d.t(cx + 12, cy + 62, lab, 20, 600 if stt == "venter" else 400, INK if stt != "ferdig" else INK2)
    d.end()


def plenum_after(d, x, y, s):
    """Plenum etter Spillfrist: klassens kjede, netto lager per Rolle, veggen og kostnaden. 1280×720, skalert."""
    d.rect(x, y, 1280 * s, 720 * s, PAPER, HAIR2, 1.2, 6)
    d.g(f"translate({x:.1f},{y:.1f}) scale({s:.4f})")
    d.t(40, 56, f"class-of-1994: {len(FERDIG)} ferdige spill", 34, 700, INK)
    d.t(1240, 56, "Demodata", 18, 400, INK3, "end")
    wk = 15
    lx, lw = 40, 700
    d.t(lx, 104, f"Klassens kjede i Uke {wk}, median", 22, 600, INK)
    kund = 110
    seg = (lw - kund) / 4
    u = 2.4
    yb = 140 + 30 * u + 10
    d.line(lx, yb, lx + lw, yb, HAIR2, 1.5)
    d.t(lx, yb - 6, "Kundene", 20, 600, INK)
    for i, r in enumerate(ORDER_UP):
        x0 = lx + kund + i * seg
        mv = med_net(r, wk)
        node_box(d, x0 + 16, yb, mv, u, 32, 2)
        d.t(x0 + 40, yb - 6, r, 20, 600, INK)
        d.t(x0 + 40, yb + 26, ("Lager " if mv >= 0 else "Restordre ") + sg(abs(mv)), 20, 400, INK)
    yg = yb + 84
    d.t(lx, yg, "Netto lager per Uke, median", 22, 600, INK)
    ax = Axis(lx + 140, lw - 140, 1, 36)
    rhh = 62
    for i, r in enumerate(reversed(ORDER_UP)):
        yr = yg + 16 + i * (rhh + 8)
        Ys = yscale(yr, rhh, -30, 20)
        d.line(ax.x0, Ys(0), ax.x1, Ys(0), HAIR2, 1.5)
        net_area(d, ax, yr, rhh, (lambda rr: (lambda w: med_net(rr, w)))(r), 1, 36, -30, 20, lw=2.4)
        d.t(lx, Ys(0) + 7, r, 20, 400, INK)
    d.line(ax.xr(wk), yg + 12, ax.xr(wk), yg + 16 + 4 * (rhh + 8), INK, 1.5, dash="3 4")
    xaxis(d, ax, yg + 16 + 4 * (rhh + 8) + 22, [1, 12, 24, 36], None, 20)
    rx = 790
    rw = 450
    d.t(rx, 104, "Fabrikk, netto lager, alle ferdige spill", 22, 600, INK)
    cw = rw / 36
    rr = 6.4
    for i, sp in enumerate(sorted(FERDIG, key=lambda q: q["spill"])):
        wall_row(d, rx, 120 + i * rr, sp, "Fabrikk", cw, rr - 0.6)
    yw = 120 + len(FERDIG) * rr
    d.t(rx, yw + 24, "Uke 1", 18, 400, INK3)
    d.t(rx + rw, yw + 24, "Uke 36", 18, 400, INK3, "end")
    d.t(rx, yw + 50, "Rødt: restordre. Blått: lager. Sortert etter spillnummer.", 18, 400, INK2)
    F = KL["ferdige"]["kjedekost"]
    FJ = KL["fjoraaret"]
    yc = yw + 100
    d.t(rx, yc, "Kjedekostnad per spill, kr", 22, 600, INK)
    X_ = lambda v: rx + v / 4000 * rw
    yd = yc + 52
    d.rect(X_(F["q1"]), yd - 18, X_(F["q3"]) - X_(F["q1"]), 36, TINT)
    for sp in FERDIG:
        d.circle(X_(sp["kjedekost"]), yd + ((sp["spill"] * 7) % 15 - 7) * 1.4, 5, ORD)
    d.line(X_(F["median"]), yd - 24, X_(F["median"]), yd + 24, INK, 3)
    d.line(X_(FJ["median_kjedekost"]), yd - 24, X_(FJ["median_kjedekost"]), yd + 24, INK, 1.5, dash="4 4")
    d.t(X_(F["median"]) - 6, yd - 30, f"I år {nf(F['median'], 0)}", 18, 600, INK, "end")
    d.t(X_(FJ["median_kjedekost"]) + 6, yd - 30, f"Fjoråret {nf(FJ['median_kjedekost'], 0)}", 18, 400, INK2)
    for v in (0, 2000, 4000):
        d.t(X_(v), yd + 50, nf(v, 0), 18, 400, INK3, "middle")
    d.end()


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
    d = Doc("09-alle-sider", 2000, 1400, f"{NAME}, alle andre sider", "Kontaktark over øvrige sider for Student, Faglærer og Admin.")
    d.t(40, 56, "Alle andre sider", 34, 700, INK)
    d.t(40, 84, "Rutenettet går igjen der tiden er poenget. Ellers er sidene rolige lister og skjema.", 16, 400, INK2)

    gx = 150
    gap = 20
    cw = 346.0          # flisens lokale bredde
    th = 212            # flisens lokale høyde
    sc = 0.7
    rh = th * sc + 60
    y0 = 112
    state = {"open": False}

    def cell(col, row, title, line):
        if state["open"]:
            d.end()
        x = gx + col * (cw * sc + gap)
        y = y0 + row * rh
        d.t(x, y + th * sc + 20, title, 15, 600, INK)
        d.para(x, y + th * sc + 38, line, cw * sc, 12, 15, fill=INK2)
        d.g(f"translate({x:.1f},{y:.1f}) scale({sc})")
        frame(d, 0, 0, cw, th)
        state["open"] = True
        return 0, 0

    # Grupper
    d.t(40, y0 + 22, "Student", 20, 600, INK)
    d.t(40, y0 + 2 * rh + 22, "Faglærer", 20, 600, INK)
    d.line(40, y0 + 2 * rh - 12, gx + 5 * (cw * sc + gap) - gap, y0 + 2 * rh - 12, HAIR2, 1)

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
    x, y = cell(2, 0, "Regler før første ordre", "Grafen forklart på en ekte Uke: tre felt, nå-streken, fire uker fram.")
    meteo(d, G, x + 10, y + 6, cw - 20, 5, 4, wmin=1, wmax=9, hn=74, hf=30, gap=4, ls=11, left=20, titles=False, xstep=4, netlabel=False, arrnums=False, ordlabel=False, nowlabel="Nå")
    # 4 Startoppgave
    x, y = cell(3, 0, "Startoppgave", "Regn posisjonen for én Uke. Viser hvordan tallene henger sammen.")
    d.t(x + 14, y + 30, f"Lager {G.lager[10]}, restordre {G.rest[10]}, på vei {G.paavei(11)}", 13, 400, INK)
    d.t(x + 14, y + 62, "Posisjon =", 15, 600)
    d.rect(x + 92, y + 44, 60, 28, PAPER, INK, 1.2, 3)
    d.t(x + 122, y + 64, G.posisjon(11), 16, 700, INK, "middle")
    mini_net(d, x + 14, y + 86, cw - 28, 96, G, 11)
    # 5 Replay
    x, y = cell(4, 0, "Replay", "Samme skjerm, nå med projeksjonen åpen. Tre KI-spillere. Tilfeldig etterspørsel.")
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
    x, y = cell(3, 1, "Studentrapport (PDF)", "Din graf, dine beslutninger og din Forklaring, klar til å lagre.")
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
    for i, r in enumerate(ORDER_UP[::-1]):
        wall_row(d, x + 14, y + 96 + i * 9, KL["spill"][0], r, (cw - 28) / 36, 8)
    d.t(x + 14, y + 158, "Ny Klasse", 14, 600, BLUE, "start", 'text-decoration="underline"')
    # Klasserapport
    x, y = cell(1, 2, "Klasserapport", "Fordeling av Forsterkning per Rolle, kjedekost og Detected patterns.")
    F = KL["ferdige"]["forsterkning_per_rolle"]
    yy = y + 26
    scq = (cw - 118) / 13
    for r in ROLES:
        q = F[r]
        bx = x + 90
        d.t(x + 12, yy + 4, r, 12, 400, INK)
        d.line(bx + q["min"] * scq, yy, bx + q["max"] * scq, yy, HAIR2, 1.2)
        d.rect(bx + q["q1"] * scq, yy - 7, (q["q3"] - q["q1"]) * scq, 14, BASE)
        d.line(bx + q["median"] * scq, yy - 8, bx + q["median"] * scq, yy + 8, INK, 2)
        yy += 28
    yy += 2
    M = KL["moenstre"]
    for k, v in list(M.items())[:2]:
        d.t(x + 12, yy, f"{k}: {v}", 11, 400, INK2)
        yy += 16
    # Spillinnsikt
    x, y = cell(2, 2, "Spillinnsikt (uke for uke)", "Ett spill i rutenettet. Læreren blar Uke for Uke.")
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
    # rad 4
    x, y = cell(4, 2, "Tverrklasse-statistikk", "Klassen mot fjoråret. To tall, samme mål. Demodata.")
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
    x, y = cell(0, 3, "Meldinger", "Fra Faglærer til spill eller Klasse. Ingen chat mellom spillere.")
    d.t(x + 14, y + 28, "Melding til Noah, Spill 2", 14, 700)
    d.rect(x + 14, y + 40, cw - 28, 74, PAPER, HAIR2, 1, 3)
    d.para(x + 22, y + 60, "Gruppa venter på ordren din. KI overtar setet om 1 t.", cw - 44, 13, 17)
    d.rect(x + 14, y + 124, 100, 28, INK, rx=3)
    d.t(x + 64, y + 143, "Send", 13, 600, PAPER, "middle")
    d.t(x + 14, y + 176, "Sendt tidligere: 3", 13, 400, INK2)
    # Lærers testspill
    x, y = cell(1, 3, "Lærers testspill", "Spill mot tre KI-spillere før klassen starter.")
    meteo(d, RE, x + 10, y + 6, cw - 20, 9, RE.order(9), wmin=1, hn=86, hf=26, gap=4, ls=11, left=20, titles=False, xstep=4, netlabel=False, arrnums=False, ordlabel=False, nowlabel="Nå", overduenote=False)
    x, y = cell(2, 3, "Admin: Admin-område", "Klasser og drift på ett sted.")
    for i, l in enumerate(("Klasser", "Brukere", "KI-kostnad", "Drift")):
        yy = y + 40 + i * 40
        d.t(x + 14, yy, l, 16, 400, INK)
        d.line(x + 14, yy + 12, x + cw - 14, yy + 12, HAIR, 1)
    x, y = cell(3, 3, "Admin: Brukere og roller", "Kontoer kommer bare via Invitasjon.")
    for i, (n, r) in enumerate((("Bård", "Faglærer"), ("Assistent", "Assistent"), ("Admin", "Admin"))):
        yy = y + 40 + i * 40
        d.t(x + 14, yy, n, 16, 400, INK)
        d.t(x + cw - 14, yy, r, 16, 400, INK2, "end")
        d.line(x + 14, yy + 12, x + cw - 14, yy + 12, HAIR, 1)
    x, y = cell(4, 3, "Admin: KI-kostnad", "Per Klasse og måned, med grense.")
    for i, l in enumerate(("Per Klasse", "Per måned", "Grense")):
        yy = y + 40 + i * 40
        d.t(x + 14, yy, l, 16, 400, INK)
        d.rect(x + cw - 74, yy - 10, 60, 8, HAIR)
        d.line(x + 14, yy + 12, x + cw - 14, yy + 12, HAIR, 1)
    d.end()

    # Plenum, to tilstander
    px = 1470
    d.t(px, y0 + 22, "Alle spill i plenum", 20, 600, INK)
    d.para(px, y0 + 48, "Faglærers projektor i Labtime. Samme rutenett som studentene kjenner. Hva lerretet viser, avhenger av om noen fortsatt spiller.", 490, 14, 19, fill=INK2)
    d.t(px, y0 + 128, "Under Labtime: bare status", 15, 600, INK)
    plenum_live(d, px, y0 + 140, 490 / 1280)
    d.para(px, y0 + 140 + 720 * 490 / 1280 + 22, "Ingen tall fra spillene, ingen navn. Studentene ser hvor mange som venter, ikke hvem eller hvorfor.", 490, 13, 17, fill=INK2)
    yA = 972
    d.line(40, yA - 18, 1960, yA - 18, HAIR2, 1)
    d.t(40, yA + 8, "Plenum etter Spillfrist: hele klassen i samme rutenett", 20, 600, INK)
    scA = 0.55
    plenum_after(d, 40, yA + 22, scA)
    tx = 40 + 1280 * scA + 40
    ty = yA + 50
    for head, body_ in [
        ("Hva lerretet viser", "Klassens kjede i én Uke (median av ferdige spill), netto lager per Rolle over tid, veggen med alle ferdige spill, og kjedekostnaden mot fjoråret."),
        ("Hvorfor først etter Spillfrist", "Under spillet ville tallene fra andre spill vise hvordan svingningene utvikler seg. Det skal studentene oppleve selv før Debriefen."),
        ("Uten rangering", "Veggen er sortert etter spillnummer, ikke etter kostnad. Ingen navn. Mønsteret går igjen i nesten alle rader, og det er poenget: struktur gir atferd."),
        ("Aggregater", "Median netto lager og ordre per Rolle og Uke, og kostnad per Uke regnet fra netto lager (lager × 0,50, restordre × 1,00), over 41 ferdige spill."),
    ]:
        d.t(tx, ty, head, 16, 600, INK)
        ty = d.para(tx, ty + 22, body_, 1960 - tx, 14, 19, fill=INK2) + 16
    d.demodata(1960, 1392, a="end")
    d.save()
