"""01 landing, 02 Klasse, 03 Klasseøkt, 04 student hjem, 09 kontaktark."""
from datetime import date

from e09cost import *
from screens_core import G, BARE, ALLE, K, A, waiting_rows, chain_band, stack_chart
from screens_debrief_teacher import SEATS, DEM, KL, demand_band, chain_cell, SPINE, role_bill_bar

RE = Seat("Grossist", FX["replay_sara"])
RE.ck(1)


def heat(v, cap=45):
    """Divergerende for netto lager: blå over null, rød under, grå midtpunkt."""
    a = min(abs(v) / cap, 1.0) ** 0.75
    n = (238, 241, 244)
    pole = (43, 108, 163) if v > 0 else (181, 66, 58)
    if abs(v) <= 1:
        a = 0
    c = tuple(int(n[i] + (pole[i] - n[i]) * a) for i in range(3))
    return "#%02X%02X%02X" % c


def strip(d, x, y, sp, cw=4.3, lane=4, roles=("Fabrikk", "Distributør", "Grossist", "Detaljist")):
    for i, r in enumerate(roles):
        for k, v in enumerate(sp["netto_lager"][r]):
            d.rect(x + k * cw, y + i * (lane + 0.5), cw + 0.2, lane, heat(v))


def cost_strip(d, x, y, sp, cw=4.3, h=8):
    """Kjedens kostnad per uke for ett spill, samme trinn som Oversikten."""
    for k, (lg, rs) in enumerate(class_week_costs(sp)):
        f_ = chain_cell(lg, rs)
        if f_:
            d.rect(x + k * cw + 0.3, y, cw - 0.6, h, f_)


def field(d, x, y, w, label, value, h=42, size=15, muted=False):
    d.t(x, y, label, 14, 600, INK)
    d.rect(x, y + 8, w, h, PAPER, HAIR2, 1, 5)
    d.t(x + 12, y + 8 + h / 2 + size * 0.34, value, size, 400, INK3 if muted else INK)
    return y + 8 + h


# ---------- 01 ----------
def build_01():
    d = Doc("01-landing", 1440, 1200, "Kjedens regning, landingsside for faglærere",
            "Første skjermbilde bæres av ett setes ledd, graf og regning. Neste seksjon viser kostnaden for alle spillene på lærerens skjerm.")
    d.t(80, 58, "Kjedens regning", 24, 700, INK)
    d.t(1360, 56, "For faglærere", 16, 400, INK2, "end")
    d.line(80, 78, 1360, 78, HAIR, 1)
    d.para(80, 152, "Én beslutning i uka. Regningen kommer senere.", 760, 52, 60, 700, INK)
    d.para(900, 128, "Kjedens regning kjører hele forsyningskjedeøvelsen for emnet ditt, fra Invitasjon til PDF-rapport. På norsk, på mobil, for klasser på rundt 250 studenter.", 460, 19, 27, fill=INK)
    d.button(900, 234, 210, 50, "Be om lærertilgang", size=17)
    d.button(1124, 234, 110, 50, "Logg inn", primary=False, size=17)

    wk = 18
    d.t(80, 326, "Ett ledd i Uke 18", 17, 600, INK)
    e = chain_band(d, G, 80, 336, 520, wk, G.order(wk), u=1.5, top=40, bottom=64, ls=15, node_w=104)
    tx = 680
    d.para(tx, 350, f"Grossisten har {G.paavei(wk)} enheter på vei og {G.rest[wk - 1]} i restordre. Boksene står på samme skala, så det som er bestilt, synes like tydelig som det som mangler.", 640, 18, 26, fill=INK)
    d.para(tx, 440, f"Hver Uke legger en linje til regningen: denne Uka {nf(G.ck(wk))} kr, så langt {nf(G.kostsum(wk))} kr. Restordre koster 1,00 per enhet, lager 0,50.", 640, 18, 26, fill=INK2)
    m = stack_chart(d, G, 80, e + 30, 1280, wk, G.order(wk), panels=(("net", 170), ("flow", 56), ("ord", 40), ("cost", 44)),
                    wmin=1, left=44, gap=14, ls=15, cmax=45)
    d.t(80, m["axisbot"] + 22, "Studenten ser bare sitt eget ledd og sin egen regning, og tidsaksen viser aldri når spillet slutter. Demodata.", 15, 400, INK2)

    y2 = m["axisbot"] + 84
    d.line(80, y2 - 40, 1360, y2 - 40, HAIR, 1)
    d.t(80, y2, "Alle spillene og hva de har kostet, på én skjerm", 32, 700, INK)
    spill = KL["spill"]
    rank = {"venter": 0, "pauset": 1, "pågår": 2, "ferdig": 3}
    rows = sorted(spill, key=lambda s: (rank[s["status"]], -(s.get("ventet_timer") or 0), -s["uke"]))[:4]
    yy = y2 + 34
    for cx, h in [(80, "Spill"), (136, "Status"), (216, "Kostnad per uke, hele kjeden"), (540, "Uke"), (600, "Venter på")]:
        d.t(cx, yy, h, 14, 600, INK2)
    d.line(80, yy + 7, 800, yy + 7, HAIR2, 1)
    yy += 28
    for sp in rows:
        d.t(80, yy, sp["spill"], 15, 600, INK)
        d.t(136, yy, {"venter": "Venter", "pauset": "Pause", "pågår": "Pågår", "ferdig": "Ferdig"}[sp["status"]], 15, 400, INK)
        cost_strip(d, 216, yy - 13, sp, cw=8.6, h=15)
        d.t(540, yy, sp["uke"], 15, 400, INK)
        if sp["status"] == "venter":
            d.t(600, yy, f"{sp['navn']}, {sp['ventet_timer']} t", 15, 400, INK)
        yy += 26
    fy = y2 + 34
    for f in ["KI-spillere fyller tomme seter, alltid merket.", "Ett fravær stopper ikke gruppa, og ingen spill blir stående uferdig.",
              "Studentlisten kommer fra Canvas-eksport."]:
        fy = d.para(880, fy, f, 480, 18, 25) + 10
    d.save()


# ---------- 02 ----------
def build_02():
    d = Doc("02-laerer-klasse", 1440, 1000, "Kjedens regning, lag Klasse",
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


def chain_start(d, x, y, w, u=3.0):
    """Kjeden slik Spillinnstillingene står: fire ledd med startlager på sann skala, og det som ligger i rørene."""
    node_w, kund_w = 112, 86
    link_w = (w - 4 * node_w - kund_w) / 4
    base = y + 74
    xx = x
    order = ["Fabrikk", "Distributør", "Grossist", "Detaljist"]
    for i, r in enumerate(order):
        # røret inn til leddet
        sw = 34
        gx = xx + (link_w - 2 * sw - 8) / 2
        for j in range(2):
            d.rect(gx + j * (sw + 8), base - 4 * u, sw, 4 * u, PAPER, BLUE, 1.2)
            d.t(gx + j * (sw + 8) + sw / 2, base - 4 * u - 5, "4", 14, 400, INK, "middle")
        d.t(xx + link_w / 2, base + 20, "produksjon 2 uker" if i == 0 else "frakt 2 uker", 14, 400, INK2, "middle")
        if i > 0:
            # ordre går mot strømmen: tynn marine linje over røret
            oy = y + 14
            d.line(xx + 6, oy, xx + link_w - 6, oy, INK, 1)
            d.path(f"M{xx + 12:.1f} {oy - 4:.1f} L{xx + 6:.1f} {oy:.1f} L{xx + 12:.1f} {oy + 4:.1f}", stroke=INK, sw=1)
            d.t(xx + link_w / 2, oy - 6, "ordre 2 uker", 14, 400, INK2, "middle")
        d.line(xx, base, xx + link_w, base, HAIR2, 1)
        xx += link_w
        d.rect(xx, base - 62, node_w, 62 + 30, "none", HAIR2, 1, 4)
        d.rect(xx + 14, base - 12 * u, node_w - 28, 12 * u, BLUEF, BLUE, 1)
        d.t(xx + node_w / 2, base - 12 * u - 6, "Lager 12", 14, 600, INK, "middle")
        d.t(xx + node_w / 2, base + 22, r, 15, 600, INK, "middle")
        d.t(xx + node_w / 2, base + 48, f"{nf(12 * LAGERKOST)} kr per uke", 14, 400, INK2, "middle")
        xx += node_w
    d.line(xx, base, xx + 30, base, HAIR2, 1)
    d.t(xx + 36, base + 5, "Kundene", 15, 600, INK)
    return base + 60


# ---------- 03 ----------
def build_03():
    d = Doc("03-laerer-spill", 1440, 1100, "Kjedens regning, Klasseøkt",
            "Forhåndsutfylte Spillinnstillinger, KI-modus, Debrief-modus, Obligatorisk, datoer, Labtimer og fordeling av 60 spill.")
    d.t(80, 62, "Klasseøkt for class-of-1994", 34, 700, INK)
    d.t(80, 90, "Alt er fylt ut med standardene.", 16, 400, INK2)
    d.t(80, 136, "Kjeden ved start", 20, 600, INK)
    d.t(1360, 136, f"Før noen har bestilt, koster hver Uke 4 × {nf(12 * LAGERKOST)} = {nf(4 * 12 * LAGERKOST)} kr for kjeden.", 15, 400, INK2, "end")
    chain_start(d, 80, 150, 1280)
    d.line(80, 300, 1360, 300, HAIR, 1)

    # Venstre
    lx, lw = 80, 560
    y = 340
    d.t(lx, y, "Spillinnstillinger: Klassisk", 22, 600, INK)
    y += 34
    rows = [("Startlager", "12"), ("I hvert ledd ved start", "4 enheter"), ("Ordreforsinkelse", "2 uker"), ("Fraktforsinkelse", "2 uker"),
            ("Produksjonsforsinkelse", "2 uker"), ("Lagerkost", "0,50 per enhet per uke"), ("Restordrekost", "1,00 per enhet per uke"),
            ("Antall uker", "36"), ("Veiledede uker", "1–4"), ("Inaktivitetsgrense", "24 t, så KI overtar")]
    for lab, v in rows:
        d.t(lx, y, lab, 15, 400, INK)
        d.t(lx + lw, y, v, 15, 600, INK, "end")
        d.line(lx, y + 10, lx + lw, y + 10, HAIR, 1)
        y += 30
    y += 6
    y = d.para(lx, y, "Kildene er uenige om forsinkelsene. Dette er produktets standard, og du kan endre den.", lw, 14, 19, fill=INK2)
    y += 22
    # etterspørselsgraf
    d.t(lx, y, "Etterspørsel: 4, så 8 fra Uke 5", 15, 600, INK)
    d.t(lx + lw, y, "Studentene ser den ikke under spillet", 14, 400, INK2, "end")
    ax = Axis(lx + 20, lw - 20, 1, 36)
    yp = y + 14
    h = 100
    for v in (0, 4, 8):
        yy = yp + h - v * h / 10
        d.line(ax.x0, yy, ax.x1, yy, HAIR, 1)
        d.t(ax.x0 - 6, yy + 4, v, 13, 400, INK3, "end")
    demand_band(d, ax, yp, h, 10)
    xaxis(d, ax, yp + h + 18, [1, 5, 12, 24, 36])
    # Høyre: datoer på én tidsakse
    rx, rw = 720, 640
    y = 340
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
    y = ya + 124
    d.t(rx, y, "Fordeling: 60 Klassespill à 4", 22, 600, INK)
    d.para(rx, y + 26, f"{KL['traktA']['registrert']} studenter fordeles tilfeldig. Hver søyle er ett spill, hver rad en Rolle. Tomme seter får KI-spiller.", rw, 15, 20, fill=INK2)
    yg = y + 66
    roles = ["Detaljist", "Grossist", "Distributør", "Fabrikk"]
    cell = (rw - 84) / 60
    for j, r in enumerate(roles):
        d.t(rx, yg + j * 24 + 16, r, 14, 400, INK)
        for i in range(60):
            d.rect(rx + 84 + i * cell, yg + j * 24, cell - 2, 21, BASE)
    # Spill 17 uthevet som eksempel
    d.rect(rx + 84 + 16 * cell - 1, yg - 3, cell, 4 * 24 + 2, "none", INK, 1.4)
    d.t(rx + 84, yg + 116, "1", 13, 400, INK3)
    d.t(rx + 84 + 16.5 * cell, yg + 116, "17", 13, 700, INK, "middle")
    d.t(rx + rw, yg + 116, "60", 13, 400, INK3, "end")
    yy = yg + 144
    d.t(rx, yy, "Spill 17", 15, 600, INK)
    d.t(rx + 84, yy, "Ida, Detaljist. Sara, Grossist. Mikkel, Distributør. Jonas, Fabrikk.", 15, 400, INK)
    yy += 18
    d.button(rx, yy, 180, 42, "Kjør fordeling på nytt", primary=False, size=15)
    d.button(rx + 192, yy, 180, 42, "Bekreft fordeling", size=15)
    d.t(rx + 388, yy + 28, "Ingen får beskjed før du bekrefter.", 14, 400, INK2)
    # Valg over hele bredden
    yb = 950
    d.line(80, yb - 30, 1360, yb - 30, HAIR2, 1)
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
    d.button(1140, 1042, 220, 46, "Lagre Klasseøkt", size=17)
    d.t(1124, 1071, "Du kan lagre uten å endre noe.", 15, 400, INK2, "end")
    d.demodata(80, 1070)
    d.save()


# ---------- 04 ----------
def build_04():
    d = Doc("04-student-hjem", 1000, 900, "Kjedens regning, student på mobil", "To telefoner: registrering via Invitasjon, og hjem under spill.")
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
    d.t(358, 124, f"Uke 11 · {nf(G.kostsum(11))} kr", 15, 600, INK, "end")
    ax = Axis(52, 306, 1, 11)
    Y = grid(d, ax, 134, 104, -40, 30, (-20, 0, 20), 13)
    net_area(d, ax, 134, 104, G.net, 1, 11, lw=1.6)
    d.circle(ax.xc(11), Y(G.net(11)), 3.5, RED, PAPER, 1.5)
    d.t(358, Y(G.net(11)) + 20, f"Restordre {G.rest[10]}", 13, 600, INK, "end")
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
    d = Doc("09-alle-sider", 2000, 1400, "Kjedens regning, alle andre sider", "Kontaktark over øvrige sider for Student, Faglærer og Admin.")
    d.t(40, 56, "Alle andre sider", 34, 700, INK)
    d.t(40, 84, "Leddet, meteogrammet og regningen går igjen der tiden og kostnaden er poenget. Ellers er sidene rolige lister og skjema.", 16, 400, INK2)

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
    x, y = cell(2, 0, "Regler før første ordre", "Leddet og grafen forklart på en ekte Uke: røret, nå-streken, og hva en Uke koster.")
    meteo(d, G, x + 10, y + 6, cw - 20, 5, 4, wmin=1, wmax=9, hn=74, hf=30, gap=4, ls=11, left=20, titles=False, xstep=4, netlabel=False, arrnums=False, ordlabel=False, nowlabel="Nå")
    # 4 Startoppgave
    x, y = cell(3, 0, "Startoppgave", "Regn posisjonen for én Uke. Viser hvordan tallene henger sammen.")
    d.t(x + 14, y + 30, f"Lager {G.lager[10]}, restordre {G.rest[10]}, på vei {G.paavei(11)}", 13, 400, INK)
    d.t(x + 14, y + 62, "Posisjon =", 15, 600)
    d.rect(x + 92, y + 44, 60, 28, PAPER, INK, 1.2, 3)
    d.t(x + 122, y + 64, G.posisjon(11), 16, 700, INK, "middle")
    mini_net(d, x + 14, y + 86, cw - 28, 96, G, 11)
    # 5 Replay
    x, y = cell(4, 0, "Replay", "Samme skjerm, nå med Posisjon tegnet under båndet. Tre KI-spillere. Tilfeldig etterspørsel.")
    meteo(d, RE, x + 10, y + 6, cw - 20, 14, RE.order(14), wmin=3, hn=86, hf=26, gap=4, ls=11, left=20, titles=False, xstep=4, netlabel=False, arrnums=False, ordlabel=False, proj=True, nowlabel="Nå", overduenote=False)
    # 6 Replay-gjennomgang
    x, y = cell(0, 1, "Replay-gjennomgang", f"Klassespillet og Replay på samme akse. Din regning {nf(G.kostsum(36))} mot {nf(RE.kostsum(RE.n))} kr. Ikke like for like.")
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
    x, y = cell(3, 1, "Studentrapport (PDF)", "Din graf, din del av kjedens regning, dine beslutninger og din Forklaring.")
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
    cost_strip(d, x + 14, y + 100, KL["spill"][0], cw=(cw - 28) / 36, h=22)
    d.t(x + 14, y + 158, "Ny Klasse", 14, 600, BLUE, "start", 'text-decoration="underline"')
    # Klasserapport
    x, y = cell(1, 2, "Klasserapport", "Klassens regning per Rolle og kostnadsart, Forsterkning per Rolle og Detected patterns.")
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
    x, y = cell(2, 2, "Spillinnsikt (uke for uke)", "Ett spill: Rolle × uke i kroner, med kjedens sum over. Læreren blar Uke for Uke.")
    ax = Axis(x + 72, cw - 86, 1, 36)
    Yc, _, _ = cum_area(d, ax, y + 10, 60, S17, ROLES, 2400)
    yy = y + 84
    for r in SPINE:
        d.t(x + 12, yy + 22, r, 12, 400, INK)
        for k in range(1, 37):
            f_, _, _ = cell_style(S17[r].kind(k), S17[r].ck(k))
            if f_:
                d.rect(ax.xl(k) + 0.3, yy + 8, ax.slot - 0.6, 24, f_)
        yy += 28
    d.line(ax.xc(11), y + 6, ax.xc(11), y + th - 8, INK, 1.2)
    # Studentside
    x, y = cell(3, 2, "Studentside", "Én students steg, Forklaring, test og rapport.")
    d.t(x + 14, y + 28, "Sara, Grossist, Spill 17", 14, 700)
    labels = ["Klassespill", "Debrief", "Quiz", "Replay", "Test", "Rapport"]
    sw = (cw - 28) / 6
    d.line(x + 14 + sw / 2, y + 48, x + 14 + 5.5 * sw, y + 48, HAIR2, 1.2)
    for i, l in enumerate(labels):
        d.circle(x + 14 + (i + 0.5) * sw, y + 48, 5, INK if i == 0 else PAPER, INK if i == 0 else HAIR2, 1.2)
        d.t(x + 14 + (i + 0.5) * sw, y + 70, l, 11, 400, INK2, "middle")
    mini_net(d, x + 14, y + 84, cw - 28, 96, G, 11)
    # Plenum
    x, y = cell(4, 2, "Alle spill i plenum", "60 kostnadsstriper på lerretet. Mønsteret går igjen, uten navn og uten rangering.")
    sp = KL["spill"]
    gw = (cw - 20) / 6
    gh = (th - 16) / 10
    for i, s in enumerate(sp):
        cost_strip(d, x + 10 + (i % 6) * gw, y + 10 + (i // 6) * gh, s, cw=(gw - 5) / 36, h=gh - 6)

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
