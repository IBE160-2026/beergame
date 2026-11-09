"""01 landing, 02 Klasse, 03 Klasseøkt, 04 student hjem, 09 kontaktark med plenum, for 05 Klassebildet."""
from datetime import date

from e05lib import *
from screens_core import G, BARE, ALLE, K, waiting_rows
from screens_debrief_teacher import SEATS, DEM, demand_band, sorted_games, STATUS_TXT

RE = Seat("Grossist", FX["replay_sara"])


def field(d, x, y, w, label, value, h=42, size=15, muted=False):
    d.t(x, y, label, 14, 600, INK)
    d.rect(x, y + 8, w, h, PAPER, HAIR2, 1, 5)
    d.t(x + 12, y + 8 + h / 2 + size * 0.34, value, size, 400, INK3 if muted else INK)
    return y + 8 + h


def wall(d, x, y, cw, rh, games, role, gap=0.6, upto=None):
    """Matriseveggen: én rad per spill, én kolonne per Uke, netto lager for én Rolle."""
    for i, s in enumerate(games):
        vals = s["netto_lager"][role][: upto or None]
        for k, v in enumerate(vals):
            f, _ = net_cell(v)
            d.rect(x + k * cw + gap / 2, y + i * rh + gap / 2, cw - gap, rh - gap, f)
        if s["status"] != "ferdig":
            xx = x + len(vals) * cw + 0.5
            d.line(xx, y + i * rh, xx, y + (i + 1) * rh, INK, 1.2)
    return y + len(games) * rh


# ---------- 01 ----------
def build_01():
    d = Doc("01-landing", 1440, 1200, "Klassebildet, landingsside for faglærere",
            "Første skjermbilde bæres av lærerens oversikt: 60 spill som matrisevegg. Neste seksjon viser ett setes kjedebånd og graf.")
    d.t(80, 58, "Klassebildet", 24, 700, INK)
    d.t(1360, 56, "For faglærere", 16, 400, INK2, "end")
    d.line(80, 78, 1360, 78, HAIR, 1)
    d.para(80, 150, "Alle spillene i klassen på én skjerm.", 700, 52, 60, 700, INK)
    d.para(860, 128, "Klassebildet kjører hele forsyningskjedeøvelsen for emnet ditt, fra Invitasjon til PDF-rapport. På norsk, på mobil, for klasser på rundt 250 studenter.", 500, 19, 27, fill=INK)
    d.button(860, 234, 210, 50, "Be om lærertilgang", size=17)
    d.button(1084, 234, 110, 50, "Logg inn", primary=False, size=17)

    # Matriseveggen
    games = sorted_games()
    role = "Grossist"
    y0 = 330
    cw = 22
    rh = 6.4
    x0 = 160
    d.t(80, y0 - 18, "Netto lager for Grossist i 60 spill, uke for uke", 17, 600, INK)
    d.t(x0 + 36 * cw, y0 - 18, "Venter på", 14, 600, INK2, "start", f'dx="18"')
    yy = y0
    groups = [("venter", "Venter"), ("pauset", "Pause"), ("pågår", "Pågår"), ("ferdig", "Ferdig")]
    for key, lab in groups:
        gs = [s for s in games if s["status"] == key]
        d.t(80, yy + 11, f"{lab} {len(gs)}", 13, 600, INK)
        yy2 = wall(d, x0, yy, cw, rh, gs, role)
        if key == "venter":
            for i, s in enumerate(gs):
                d.t(x0 + 36 * cw + 18, yy + i * rh * 3 + 12, f"Spill {s['spill']}: {s['navn']}, {s['venter_paa']}, {s['ventet_timer']} t", 14, 400, INK)
        yy = yy2 + 8
    d.t(x0 + 36 * cw + 18, y0 + 92, "Strek: nå, i spill som pågår.", 14, 400, INK2)
    lx = net_legend(d, x0 + 36 * cw + 18, y0 + 120, sw=20, ls=12)
    d.t(x0 + 36 * cw + 18, y0 + 168, "Rødt er restordre, blått er lager.", 14, 400, INK2)
    d.t(80, yy + 16, "Lærerens Oversikt. Hver rad er et ekte spill, og du ser hvem det venter på. Demodata.", 15, 400, INK2)

    # Neste seksjon
    y2 = yy + 90
    d.line(80, y2 - 40, 1360, y2 - 40, HAIR, 1)
    d.t(80, y2, "Studenten ser sitt eget ledd, og bestemmer ett tall i uka", 30, 700, INK)
    c = chain_seat(d, 80, y2 + 30, 460, G, 11, 24, u=1.1, cap=40, slot=50, ls=14)
    axl = Axis(680, 680, 1, 15)
    gy, gh = y2 + 50, 150
    d.t(640, y2 + 36, "Lager over null, restordre under", 15, 600, INK)
    d.rect(axl.xr(11), gy - 4, axl.xr(15) - axl.xr(11), gh + 4, TINT)
    Yl = grid(d, axl, gy, gh, -40, 30, (-40, -20, 0, 20), 14)
    net_area(d, axl, gy, gh, G.net, 1, 11)
    d.circle(axl.xc(11), Yl(G.net(11)), 4.5, RED, PAPER, 2)
    d.line(axl.xr(11), gy - 14, axl.xr(11), gh + gy, INK, 1.4)
    d.t(axl.xr(11) + 6, gy - 2, "Nå", 14, 700, INK)
    d.t(axl.xr(11) + 8, Yl(G.net(11)) + 5, f"Restordre {G.rest[10]}", 14, 600, INK)
    xaxis(d, axl, gy + gh + 20, [1, 3, 5, 7, 9, 11, 13, 15], 11, 14)
    d.t(80, y2 + 262, "Ett sete, Grossist, Uke 11. Røret holder det som er bestilt, boksen er lageret. Tidsaksen viser aldri når spillet slutter. Demodata.", 15, 400, INK2)
    fy = y2 + 306
    facts = [
        "KI-spillere fyller tomme seter, alltid merket.",
        "Ett fravær stopper ikke gruppa, og ingen spill blir stående uferdig.",
        "Studentlisten kommer fra Canvas-eksport.",
        "Fra Invitasjon til PDF-rapport, på mobil og på norsk.",
    ]
    colw = (1280 - 3 * 32) / 4
    for i, f in enumerate(facts):
        d.para(80 + i * (colw + 32), fy, f, colw, 17, 24)
    d.save()


# ---------- 02 ----------
def build_02():
    d = Doc("02-laerer-klasse", 1440, 1000, "Klassebildet, lag Klasse",
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
    d = Doc("03-laerer-spill", 1440, 1100, "Klassebildet, Klasseøkt",
            "Forhåndsutfylte Spillinnstillinger med kjeden tegnet slik innstillingene står, KI-modus, Debrief-modus, Obligatorisk, datoer, Labtimer og fordeling av 60 spill.")
    d.t(80, 62, "Klasseøkt for class-of-1994", 34, 700, INK)
    d.t(80, 90, "Alt er fylt ut med standardene. Du kan lagre uten å endre noe.", 16, 400, INK2)

    lx, lw = 80, 560
    y = 140
    d.t(lx, y, "Spillinnstillinger: Klassisk", 22, 600, INK)
    y += 34
    rows = [("Startlager", "12"), ("I hvert ledd ved start", "4 enheter"), ("Ordreforsinkelse", "2 uker"), ("Fraktforsinkelse", "2 uker"),
            ("Produksjonsforsinkelse", "2 uker"), ("Lagerkost", "0,50 per enhet per uke"), ("Restordrekost", "1,00 per enhet per uke"),
            ("Antall uker", "36"), ("Veiledede uker", "1–4"), ("Inaktivitetsgrense", "24 t, så KI overtar")]
    for lab, v in rows:
        d.t(lx, y, lab, 15, 400, INK)
        d.t(lx + lw, y, v, 15, 600, INK, "end")
        d.line(lx, y + 10, lx + lw, y + 10, HAIR, 1)
        y += 32
    y += 4
    y = d.para(lx, y, "Kildene er uenige om forsinkelsene. Dette er produktets standard, og du kan endre den.", lw, 14, 19, fill=INK2)
    y += 26
    d.t(lx, y, "Kjeden slik innstillingene står, Uke 1", 17, 600, INK)
    S = FX["spill17"]["serier"]
    nodes = {r: S[r]["lager"][0] - S[r]["restordre"][0] for r in ROLES}
    pv = {r: S[r]["paa_vei"][0] for r in ROLES}
    flows = {r: S[r]["ordre"][0] for r in ROLES}
    assert all(v == 12 for v in nodes.values())
    c = chain_full(d, lx, y + 8, lw, nodes, f"{DEM[0]}", u=2.4, cap=14, ls=13, flows=flows, pv=pv, you=None,
                   stocklabels={r: f"Lager {nodes[r]}" for r in ROLES})
    yy = c["base"] + 64
    d.para(lx, yy, f"Boksene er startlageret, 12 i hvert ledd. De åpne stolpene er det som er på vei inn i Uke 1 ifølge loggen, {pv['Grossist']} per ledd. Tallene på linja er ordrene. Ordreforsinkelse og fraktforsinkelse gir om lag 4 uker fra ordre til levering. Kundene kjøper 4, så 8 fra Uke 5, og studentene ser det ikke under spillet.", lw, 14, 19, fill=INK2)

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
    d.button(1140, 1012, 220, 52, "Lagre Klasseøkt", size=17)
    d.t(1124, 1044, "Du kan lagre uten å endre noe.", 15, 400, INK2, "end")
    d.demodata(80, 1044)
    d.save()


# ---------- 04 ----------
def build_04():
    d = Doc("04-student-hjem", 1000, 900, "Klassebildet, student på mobil", "To telefoner: registrering via Invitasjon, og hjem under spill med kjedebånd.")
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
    d.rect(20, 100, 350, 230, TINT, None, 1, 6)
    d.t(32, 124, "Spillet venter på deg", 16, 600, INK)
    d.t(358, 124, "Uke 11", 15, 600, INK, "end")
    chain_seat(d, 32, 134, 326, G, 11, None, u=0.9, cap=30, slot=32, ls=12)
    d.button(32, 270, 326, 46, "Gå til Uke 11", size=16)
    y = 360
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
    y += 6 * 25 + 6
    d.line(20, y - 14, 370, y - 14, HAIR, 1)
    d.t(20, y + 6, "Neste frist", 14, 400, INK2)
    d.t(370, y + 6, "Spillfrist ti. 8. des", 14, 600, INK, "end")
    d.t(20, y + 30, "Labtime", 14, 400, INK2)
    d.t(370, y + 30, "to. 26. nov 14:15, Datalab A2", 14, 600, INK, "end")
    d.demodata(20, y + 56)
    d.end()
    d.save()


# ---------- 09 ----------
def plenum(d, x, y, s):
    """Plenumsvisningen i 1280×720, skalert med s. Ingen navn, ingen spillnummer, ingen rangering."""
    W, H = 1280, 720
    d.rect(x, y, W * s, H * s, PAPER, HAIR2, 1.4, 6)
    d.g(f"translate({x},{y}) scale({s})")
    d.t(48, 70, "41 spill, samme bølge", 44, 700, INK)
    d.t(48, 104, "Netto lager per Rolle i klassen: median og midtre halvdel. Ingen navn og ingen spillnummer.", 20, 400, INK2)
    ax = Axis(220, 700, 1, 36)
    yr = 136
    rh = 112
    lo, hi = -70, 70
    for r in CHAIN_ORDER:
        Y = yscale(yr, rh, lo, hi)
        q = [class_quart_net(r, w) for w in range(1, 37)]
        d.line(ax.x0, Y(0), ax.x1, Y(0), HAIR2, 1)
        band = "M" + " L".join(f"{ax.xc(w):.1f} {Y(q[w - 1][2]):.1f}" for w in range(1, 37)) + " L" + " L".join(
            f"{ax.xc(w):.1f} {Y(q[w - 1][0]):.1f}" for w in range(36, 0, -1)) + " Z"
        d.path(band, BASE, extra='fill-opacity="0.6"')
        med = lambda w, q=q: q[w - 1][1]
        net_area(d, ax, yr, rh, med, 1, 36, lo, hi, lw=3, fills=False)
        first = next(w for w in range(1, 37) if med(w) < 0)
        d.circle(ax.xc(first), Y(med(first)), 6, RED, PAPER, 2)
        d.t(ax.xc(first) - 10, Y(med(first)) + 6, f"Uke {first}", 18, 700, RED, "end", halo())
        d.t(48, Y(0) + 2, r, 24, 700, INK)
        lowest = min(q[w - 1][1] for w in range(1, 37))
        d.t(48, Y(0) + 28, f"Median ned til {sg(lowest)}", 17, 400, INK2)
        yr += rh + 8
    Yd = yr + 6
    u = 26 / 8
    dd = f"M{ax.xl(1):.1f} {Yd + 26:.1f}"
    for w in range(1, 37):
        dd += f" L{ax.xl(w):.1f} {Yd + 26 - DEM[w - 1] * u:.1f} L{ax.xr(w):.1f} {Yd + 26 - DEM[w - 1] * u:.1f}"
    d.path(dd + f" L{ax.xr(36):.1f} {Yd + 26:.1f} Z", BLUEF)
    d.t(48, Yd + 22, "Kundene", 22, 600, INK)
    d.t(ax.xc(31), Yd + 18, "4, så 8", 18, 700, BLUE, "middle")
    for k in (1, 12, 24, 36):
        d.t(ax.xc(k), Yd + 52, k, 17, 400, INK3, "middle")
    # Høyre
    rx = 950
    d.t(rx, 160, "Forsterkning, median", 22, 700, INK)
    FP = KL["ferdige"]["forsterkning_per_rolle"]
    yy = 196
    for r in CHAIN_ORDER:
        v = FP[r]["median"]
        d.t(rx, yy + 20, r, 18, 400, INK)
        d.rect(rx + 110, yy + 6, 130 * v / 7, 18, ORD)
        d.t(rx + 244, yy + 22, fx1(v), 22, 700, INK, "start", 'style="font-variant-numeric:lining-nums proportional-nums" dx="4"')
        yy += 40
    yy += 30
    tl = sum(game_cost_split(s_)[0] for s_ in FERDIGE)
    tr = sum(game_cost_split(s_)[1] for s_ in FERDIGE)
    d.t(rx, yy, "Klassen betalte", 22, 700, INK)
    split_bar(d, rx, yy + 16, 250, 22, tl, tr, tl + tr)
    d.t(rx, yy + 64, f"Restordre {nf(tr / (tl + tr) * 100, 0)} %", 18, 600, INK)
    d.t(rx + 250, yy + 64, f"Lager {nf(tl / (tl + tr) * 100, 0)} %", 18, 600, INK, "end")
    d.para(rx, yy + 100, "Restordre koster dobbelt. Kjeden betaler for det som mangler.", 260, 17, 23, fill=INK2)
    d.para(rx, yy + 170, "Rødt punkt: første Uke medianen går under null. Den kommer senere jo lenger opp i kjeden.", 260, 17, 23, fill=INK2)
    d.t(48, 706, "Vises etter Debrief-frist. Demodata.", 15, 400, INK3)
    d.end()


def build_09():
    d = Doc("09-alle-sider", 2000, 1400, "Klassebildet, plenum og alle andre sider",
            "Plenumsvisningen for Faglærer i stort format, og kontaktark over øvrige sider for Faglærer, Student og Admin.")
    d.t(40, 50, "Plenum og alle andre sider", 34, 700, INK)
    d.t(40, 78, "Klassebildet leder: plenum og lærerflater bruker samme matrise, samme kjede og samme kostnadsfarger som studentens skjerm.", 16, 400, INK2)
    d.t(40, 120, "Faglærer", 20, 600, INK)
    s = 0.86
    py = 132
    plenum(d, 40, py, s)
    d.t(40, py + 720 * s + 26, "Alle spill i plenum", 16, 600, INK)
    d.t(40, py + 720 * s + 46, "På lerretet i Labtime eller forelesning: klassens kjede, uten navn og uten rangering. Samme farger som telefonen, store nok for bakerste rad.", 13, 400, INK2)

    def frame(x, y, w, h):
        d.rect(x, y, w, h, PAPER, HAIR2, 1, 5)

    def cell(x, y, w, h, title, line):
        frame(x, y, w, h)
        d.t(x, y + h + 20, title, 15, 600, INK)
        d.para(x, y + h + 38, line, w, 12, 16, fill=INK2)

    # Faglærer-ruter til høyre for plenum
    fx0 = 40 + 1280 * s + 32
    fw = 1960 - fx0
    cw = (fw - 20) / 2
    th = 104
    rh = 168
    fl = [
        ("Lærerhjem", "Klassene dine, hva som venter, og neste frist."),
        ("Klasserapport", "Fordeling av Forsterkning per Rolle, kjedekost og Detected patterns."),
        ("Spillinnsikt (uke for uke)", "Ett spill, hele kjeden og matrisen Rolle × uke. Læreren spoler."),
        ("Studentside", "Én students steg, Forklaring, testsvar og rapport."),
        ("Tverrklasse-statistikk", "Klassen mot fjoråret. Bare medianer er lagret for fjoråret."),
        ("Meldinger", "Fra Faglærer til ett spill eller hele Klassen. Ingen chat mellom spillere."),
        ("Lærers testspill", "Spill selv mot tre KI-spillere før klassen starter. Telles ikke med."),
    ]
    pos = {}
    for i, (t, l) in enumerate(fl):
        x = fx0 + (i % 2) * (cw + 20)
        y = py + (i // 2) * rh
        cell(x, y, cw, th, t, l)
        pos[t] = (x, y)
    # tegninger
    x, y = pos["Lærerhjem"]
    d.t(x + 12, y + 22, "class-of-1994, IBE160", 13, 700)
    d.t(x + 12, y + 40, "Spillfrist ti. 8. des. 4 spill venter.", 12, 400, INK2)
    wall(d, x + 12, y + 50, (cw - 24) / 36, 3.2, sorted_games()[:14], "Fabrikk", gap=0.3)
    x, y = pos["Klasserapport"]
    F = KL["ferdige"]["forsterkning_per_rolle"]
    sc = (cw - 110) / 13
    yy = y + 20
    for r in ROLES:
        q = F[r]
        bx = x + 84
        d.t(x + 10, yy + 4, r, 11, 400, INK)
        d.line(bx + q["min"] * sc, yy, bx + q["max"] * sc, yy, HAIR2, 1.2)
        d.rect(bx + q["q1"] * sc, yy - 6, (q["q3"] - q["q1"]) * sc, 12, BASE)
        d.line(bx + q["median"] * sc, yy - 7, bx + q["median"] * sc, yy + 7, INK, 2)
        yy += 22
    x, y = pos["Spillinnsikt (uke for uke)"]
    axm = Axis(x + 74, cw - 86, 1, 36)
    matrix(d, axm, y + 10, [(r, SEATS[r].order, "flow") for r in CHAIN_ORDER], 1, 36, ch=16, ls=7, label_x=x + 10, label_size=11, numbers=False, hi_week=18)
    d.t(x + 10, y + 92, "Ordre, Fabrikk øverst. Ramme: Uke 18.", 11, 400, INK2)
    x, y = pos["Studentside"]
    d.t(x + 12, y + 22, "Sara, Grossist, Spill 17", 13, 700)
    labels = ["Klassespill", "Debrief", "Quiz", "Replay", "Test", "Rapport"]
    sw = (cw - 24) / 6
    d.line(x + 12 + sw / 2, y + 42, x + 12 + 5.5 * sw, y + 42, HAIR2, 1.2)
    for i, l in enumerate(labels):
        d.circle(x + 12 + (i + 0.5) * sw, y + 42, 5, INK if i == 0 else PAPER, INK if i == 0 else HAIR2, 1.2)
        d.t(x + 12 + (i + 0.5) * sw, y + 62, l, 11, 400, INK2, "middle")
    axs = Axis(x + 12, cw - 24, 1, 36)
    Ys = yscale(y + 70, 30, -40, 30)
    d.line(axs.x0, Ys(0), axs.x1, Ys(0), HAIR2, 1)
    net_area(d, axs, y + 70, 30, G.net, 1, 11, lw=1.2)
    x, y = pos["Tverrklasse-statistikk"]
    FJ = KL["fjoraaret"]
    ko = KL["ferdige"]["kjedekost"]["median"]
    d.t(x + 12, y + 22, "Median kjedekost, kr", 12, 600)
    mx = max(ko, FJ["median_kjedekost"])
    for i, (lab, v) in enumerate(((FJ["klasse"], FJ["median_kjedekost"]), ("class-of-1994", ko))):
        yy = y + 32 + i * 22
        d.t(x + 12, yy + 11, lab, 11, 400, INK)
        d.rect(x + 104, yy, (cw - 170) * v / mx, 14, BASE if i == 0 else ORD)
        d.t(x + cw - 12, yy + 11, nf(v, 0), 12, 600, INK, "end")
    d.t(x + 12, y + 92, f"Fabrikk, median Forsterkning: {fx1(FJ['median_forsterkning_fabrikk'])} mot {fx1(KL['ferdige']['forsterkning_per_rolle']['Fabrikk']['median'])}", 11, 400, INK2)
    x, y = pos["Meldinger"]
    d.t(x + 12, y + 22, "Melding til Noah, Spill 2", 13, 700)
    d.rect(x + 12, y + 32, cw - 24, 40, PAPER, HAIR2, 1, 3)
    d.t(x + 20, y + 56, "Gruppa venter på ordren din. KI overtar om 1 t.", 12, 400, INK)
    d.rect(x + 12, y + 78, 70, 20, INK, rx=3)
    d.t(x + 47, y + 92, "Send", 12, 600, PAPER, "middle")
    x, y = pos["Lærers testspill"]
    meteo(d, RE, x + 8, y + 4, cw - 16, 9, RE.order(9), wmin=1, hn=44, hf=14, gap=3, ls=10, left=18, titles=False, xstep=4,
          netlabel=False, arrnums=False, ordlabel=False, nowlabel="Nå", overduenote=False, axislabel=False, connector=False)

    # Student og Admin
    y0 = 860
    d.line(40, y0 - 36, 1960, y0 - 36, HAIR2, 1)
    d.t(40, y0 - 12, "Student", 20, 600, INK)
    cols = 7
    gap = 16
    cw = (1920 - (cols - 1) * gap) / cols
    th = 176
    rh = 280
    st = [
        ("Invitasjon og registrering", "Lenke fra e-post, navn og passord. Gyldig i 14 dager."),
        ("Logg inn", "E-post og passord. Ingen åpen registrering."),
        ("Regler før første ordre", "Kjedebåndet og grafen forklart på en ekte Uke: røret, boksen, nå-streken."),
        ("Startoppgave", "Regn posisjonen for én Uke. Viser hvordan tallene henger sammen."),
        ("Replay", "Samme skjerm med Posisjon under båndet og projeksjonen åpen. Tre KI-spillere."),
        ("Replay-gjennomgang", "Klassespillet og Replay på samme akse. Ikke like for like."),
        ("Individuell test", "Flervalg, tegneoppgave i egen graf og tabell, og langsvar."),
        ("KI-vurdering", "Tilbakemelding på testen. Teller ikke og er aldri en karakter."),
        ("Studentrapport (PDF)", "Din graf, din matrise, dine beslutninger og din Forklaring."),
        ("Alle spill side om side", "Etter Debriefen: alle Grossister i klassen, samme skala. Ingen rangering."),
    ]
    P = {}
    for i, (t, l) in enumerate(st):
        x = 40 + (i % cols) * (cw + gap)
        y = y0 + (i // cols) * rh
        cell(x, y, cw, th, t, l)
        P[t] = (x, y)
    x, y = P["Invitasjon og registrering"]
    d.t(x + 12, y + 26, "Du er invitert", 14, 700)
    for i in range(3):
        d.rect(x + 12, y + 40 + i * 32, cw - 24, 24, PAPER, HAIR2, 1, 3)
    d.rect(x + 12, y + 140, cw - 24, 26, INK, rx=3)
    x, y = P["Logg inn"]
    d.t(x + 12, y + 26, "Logg inn", 14, 700)
    for i in range(2):
        d.rect(x + 12, y + 40 + i * 32, cw - 24, 24, PAPER, HAIR2, 1, 3)
    d.rect(x + 12, y + 108, cw - 24, 26, INK, rx=3)
    x, y = P["Regler før første ordre"]
    chain_seat(d, x + 8, y + 6, cw - 16, G, 5, 4, u=0.8, cap=24, slot=26, ls=10)
    meteo(d, G, x + 8, y + 104, cw - 16, 5, 4, wmin=1, wmax=9, hn=30, hf=12, gap=3, ls=10, left=18, titles=False, xstep=4,
          netlabel=False, arrnums=False, ordlabel=False, nowlabel="", overduenote=False, axislabel=False)
    x, y = P["Startoppgave"]
    d.t(x + 12, y + 26, f"Lager {G.lager[10]}, restordre {G.rest[10]}, på vei {G.paavei(11)}", 12, 400, INK)
    d.t(x + 12, y + 58, "Posisjon =", 14, 600)
    d.rect(x + 88, y + 40, 52, 26, PAPER, INK, 1.2, 3)
    d.t(x + 114, y + 59, G.posisjon(11), 15, 700, INK, "middle")
    chain_seat(d, x + 8, y + 76, cw - 16, G, 11, None, u=0.7, cap=20, slot=26, ls=10)
    x, y = P["Replay"]
    chain_seat(d, x + 8, y + 6, cw - 16, RE, 14, RE.order(14), u=0.8, cap=24, slot=26, ls=10, show_pos=True)
    x, y = P["Replay-gjennomgang"]
    ax = Axis(x + 12, cw - 24, 1, 36)
    Y = yscale(y + 30, 130, -40, 30)
    d.line(ax.x0, Y(0), ax.x1, Y(0), HAIR2, 1)
    d.path("M" + " L".join(f"{ax.xc(k):.1f} {Y(G.net(k)):.1f}" for k in range(1, 37)), stroke=GREY, sw=1.4)
    net_area(d, ax, y + 30, 130, RE.net, 1, RE.n, lw=1.8)
    d.t(x + 12, y + 22, "Klassespill grå, Replay farget", 12, 400, INK2)
    x, y = P["Individuell test"]
    wd = (cw - 36) / 2
    d.t(x + 12, y + 22, "Fyll inn tabellen", 11, 600)
    axt = Axis(x + 12, cw - 24, 9, 14)
    matrix(d, axt, y + 30, [("", G.net, "net"), ("", lambda k: G.order(k) if k < 12 else None, "flow")], 9, 13, ch=22, ls=11)
    for k in (12, 13):
        d.rect(axt.xl(k) + 1, y + 53, axt.slot - 2, 20, PAPER, INK, 1, extra='stroke-dasharray="3 2"')
    d.t(x + 12, y + 96, "Langsvar", 11, 600)
    d.rect(x + 12, y + 104, cw - 24, 60, PAPER, HAIR2, 1, 3)
    x, y = P["KI-vurdering"]
    d.t(x + 12, y + 26, "KI-generert, kan ta feil", 13, 600, INK)
    d.t(x + 12, y + 44, "Teller ikke. Ingen karakter.", 12, 400, INK2)
    for i in range(7):
        d.rect(x + 12, y + 60 + i * 14, (cw - 24) * (1 - 0.14 * (i % 3)), 5, HAIR, rx=1)
    x, y = P["Studentrapport (PDF)"]
    pw = 120
    px = x + cw / 2 - pw / 2
    d.rect(px, y + 10, pw, th - 20, PAPER, HAIR2, 1)
    d.t(px + 8, y + 26, "Sara, Grossist", 10, 600)
    axp = Axis(px + 8, pw - 16, 1, 36)
    Yp = yscale(y + 32, 44, -40, 30)
    d.line(axp.x0, Yp(0), axp.x1, Yp(0), HAIR2, 1)
    net_area(d, axp, y + 32, 44, G.net, 1, 36, lw=1)
    matrix(d, axp, y + 82, [("", G.net, "net"), ("", G.order, "flow")], 1, 36, ch=6, numbers=False, gap=0.3)
    for i in range(4):
        d.rect(px + 8, y + 104 + i * 11, (pw - 16) * (1 - 0.14 * (i % 3)), 4, HAIR, rx=1)
    x, y = P["Alle spill side om side"]
    fer = [s_ for s_ in KL["spill"] if s_["status"] == "ferdig"][:24]
    gw = (cw - 24) / 4
    gh = (th - 20) / 6
    for i, sp in enumerate(fer):
        xx = x + 12 + (i % 4) * gw
        yy = y + 10 + (i // 4) * gh
        axx = Axis(xx, gw - 6, 1, 36)
        vals = sp["netto_lager"]["Grossist"]
        net_area(d, axx, yy, gh - 4, lambda k, v=vals: v[k - 1], 1, 36, -70, 70, lw=0.8)

    # Admin
    xa = 40 + 3 * (cw + gap) + cw + gap / 2
    ya = y0 + rh
    d.line(xa, ya - 8, xa, ya + th + 50, HAIR2, 1)
    d.t(xa + gap / 2, ya - 14, "Admin", 20, 600, INK)
    ad = [("Admin-område", "Klasser og drift på ett sted.", ("Klasser", "Brukere", "KI-kostnad", "Drift")),
          ("Brukere og roller", "Kontoer kommer bare via Invitasjon.", ("Bård, Faglærer", "Assistent", "Admin")),
          ("KI-kostnad", "Per Klasse og måned.", ("Per Klasse", "Per måned", "Grense"))]
    for i, (t, l, items) in enumerate(ad):
        x = 40 + (4 + i) * (cw + gap)
        cell(x, ya, cw, th, t, l)
        for j, it in enumerate(items):
            yy = ya + 30 + j * 32
            d.t(x + 12, yy, it, 13, 400, INK)
            d.line(x + 12, yy + 10, x + cw - 12, yy + 10, HAIR, 1)
    d.demodata(1960, 1392, a="end")
    d.save()


if __name__ == "__main__":
    build_01()
    build_02()
    build_03()
    build_04()
    build_09()
