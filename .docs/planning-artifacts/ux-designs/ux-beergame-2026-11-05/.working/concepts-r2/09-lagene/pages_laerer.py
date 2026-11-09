"""Lærerflatene: Oversikt, Klasse og Klasseøkt."""
from lib import *

SPILL = FX["klasse"]["spill"]
TOPP = max(max(g["ordre"]["Fabrikk"]) for g in SPILL)


def statuslinje(g):
    st = g["status"]
    ki = g.get("ki_seter", 0)
    kitekst = f", {ki} KI-seter" if ki > 1 else (", 1 KI-sete" if ki == 1 else "")
    if st == "venter":
        tail = ". KI overtar om 1 t" if g["ventet_timer"] >= 23 else ""
        return f"{g['navn']}, {g['venter_paa']}, {g['ventet_timer']} t{tail}"
    if st == "pauset":
        return f"Pause, Uke {g['uke']}, {g['fortsetter']}{kitekst}"
    if st == "pågår":
        return f"Uke {g['uke']}{kitekst}"
    return f"Ferdig{kitekst}"


def teacher_row(g, x, y, w, lh, line_w=120, size=14):
    """Én rad: spillnummer, én linje, ett tall, én kort tekst."""
    urgent = g["status"] == "venter" and g.get("ventet_timer", 0) >= 23
    waits = g["status"] in ("venter", "pauset")
    col = VER if urgent else INK
    out = []
    base = y + lh * 0.62
    out.append(T(x + 22, base, str(g["spill"]), size, 700, col, "end"))
    lx = x + 36
    sc = Sc(lx, y + 5, line_w, lh - 12, 36, 0, TOPP)
    vals = g["ordre"]["Fabrikk"]
    pts = [(sc.X(t), sc.Y(vals[t - 1])) for t in range(1, len(vals) + 1)]
    out.append(path(pts, col if urgent else (INK if g["status"] != "ferdig" else G1), 1))
    if g["status"] != "ferdig":
        ex, ey = pts[-1]
        out.append(f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="2" fill="{col}"/>')
    tx = lx + line_w + 54
    out.append(T(tx, base, num(g["kjedekost"]), size, 400, col if urgent else INK, "end"))
    out.append(T(tx + 14, base, statuslinje(g), size, 700 if waits else 400, col if urgent else (INK if waits else G1)))
    return out


def page_08():
    d = Doc("08-laerer-oversikt", 1600, 1000, "Lag: Oversikt",
            "Faglærerens oversikt over 60 Klassespill: én rolig liste med ett tall og én kort linje per spill, nær overtakelse uthevet, og ett åpnet spill.")
    d.add(T(58, 72, "Oversikt", 40, 300))
    d.add(T(60, 100, "class-of-1994, IBE160. 60 Klassespill.", 15, 400, G1))

    tell = lambda *st: sum(1 for g in SPILL if g["status"] in st)
    filtre = [(f"Alle {len(SPILL)}", True), (f"Venter {tell('venter')}", False),
              (f"Pågår {tell('pågår', 'pauset')}, herav {tell('pauset')} i Pause", False),
              (f"Ferdig {tell('ferdig')}", False)]
    x = 60
    for f, on in filtre:
        d.add(T(x, 140, f, 15, 700 if on else 400, INK if on else G1, u=on))
        x += est(f, 15, 700 if on else 400) + 28

    # Trakten som samme linjespråk: ett trappetrinn per steg, sann null
    tr = FX["klasse"]["traktA"]
    navn = ["registrert", "klassespill ferdig", "debrief ferdig", "quiz bestått", "replay ferdig", "test levert", "KI-vurdering klar"]
    verdier = list(tr.values())
    tx, tw = 780, 760
    stepw = tw / len(verdier)
    th = 58
    ty = 34
    pts = []
    for i, v in enumerate(verdier):
        yv = ty + th - v / verdier[0] * th
        pts += [(tx + i * stepw, yv), (tx + (i + 1) * stepw, yv)]
        d.add(T(tx + i * stepw, ty + th + 22, num(v), 16, 700))
        for j, ord_ in enumerate(wrap(navn[i], stepw - 8, 12)):
            d.add(T(tx + i * stepw, ty + th + 38 + j * 14, ord_, 12, 400, G1))
    d.add(L(tx, ty + th, tx + tw, ty + th, G3, 1))
    d.add(path(pts, INK, 1.5, join="miter"))

    # Liste: viktigst først, siden kostnad høyest først blant ferdige
    orden = {"venter": 0, "pauset": 1, "pågår": 2, "ferdig": 3}
    rows = sorted(SPILL, key=lambda g: (orden[g["status"]], -g.get("ventet_timer", 0), -g["uke"], -g["kjedekost"]))
    cols = [60, 572, 1084]
    cw = 472
    y0 = 214
    lh = 34
    for cx in cols:
        d.add(T(cx + 36, y0 - 12, "Fabrikkens ordre", 12, 400, G1))
        d.add(T(cx + 210, y0 - 12, "Kost", 12, 400, G1, "end"))
        d.add(T(cx + 224, y0 - 12, "Hva skjer", 12, 400, G1))

    # Første kolonne: spill 2 åpnet, ett trykk unna
    n_open = 7
    y = y0
    apen = rows[0]
    d.add(teacher_row(apen, cols[0], y, cw, lh))
    y += lh + 2
    mini_h = 96
    sc = Sc(cols[0] + 36, y, 300, mini_h, 36, 0, TOPP)
    d.add(L(sc.x0, sc.Y(0), sc.x0 + 300, sc.Y(0), G3, 1))
    style = {"Detaljist": (G2, 1, None), "Grossist": (VER, 2, None), "Distributør": (G1, 1, None), "Fabrikk": (INK, 1.25, None)}
    uke = apen["uke"]
    ends = []
    for rolle in ROLLER:
        c, sw, da = style[rolle]
        vals = apen["ordre"][rolle]
        d.add(path([(sc.X(t), sc.Y(vals[t - 1])) for t in range(1, len(vals) + 1)], c, sw, da))
        ends.append((vals[-1], rolle, num(vals[-1]), VER if rolle == "Grossist" else G1))
    d.add(endlabels(sc, ends, 12, gap=15, x=sc.X(uke) + 8))
    y += mini_h + 22
    d.add(T(sc.X(uke) + 100, sc.y0 + 56, f"Uke {uke}", 13, 400, G1))
    d.add(T(sc.X(uke) + 100, sc.y0 + 72, "Alle Rollers ordre", 13, 400, G1))
    d.add(T(cols[0] + 36, y, f"Send Melding til {apen['navn']}", 14, 700, INK, u=True))
    d.add(T(cols[0] + 200, y, "Åpne Spillinsikt", 14, 400, INK, u=True))
    y += 22
    rest = rows[1:]
    per_col = int((1000 - y0 - 34) / lh)
    first_n = int((y0 + per_col * lh - y) / lh)
    i = 0
    for k in range(first_n):
        d.add(teacher_row(rest[i], cols[0], y + k * lh, cw, lh))
        i += 1
    for cx in cols[1:]:
        for k in range(per_col):
            if i < len(rest):
                d.add(teacher_row(rest[i], cx, y0 + k * lh, cw, lh))
                i += 1
    assert i == len(rest), (i, len(rest))
    d.add(T(60, 980, "Linjene har felles skala og felles tidsakse, så et kort spill er et spill som ikke er ferdig. Demodata.", 13, 400, G1))
    d.add(T(1540, 980, "Send Melding til alle", 14, 700, INK, "end", u=True))
    d.save()


def field(x, y, label, val, w, hint=None):
    out = [T(x, y, label, 14, 400, G1), T(x, y + 28, val, 19, 400), L(x, y + 40, x + w, y + 40, G3, 1)]
    if hint:
        out.append(T(x + w, y + 28, hint, 14, 400, INK, "end", u=True))
    return out


def page_02():
    d = Doc("02-laerer-klasse", 1440, 1000, "Lag: Lag Klasse",
            "Faglærer lager Klasse: navn, emnekode, Canvas-fil, e-postkolonne, ugyldige rader, send Invitasjoner og status.")
    ro = FX["klasse"]["roster"]
    d.add(T(78, 92, "Lag Klasse", 40, 300))
    x = 80
    y = 160
    d.add(field(x, y, "Navn", "class-of-1994", 380))
    d.add(field(x, y + 84, "Emnekode", "IBE160", 380))
    d.add(field(x, y + 168, "Studentliste", "class-of-1994.xlsx", 380, "Bytt fil"))
    d.add(T(x, y + 230, f"Canvas-eksport, {num(ro['paa_lista'])} rader.", 14, 400, G1))
    d.add(field(x, y + 268, "E-postkolonne", "SIS Login ID", 380, "Velg annen"))
    d.add(T(x, y + 330, f"{num(ro['paa_lista'] - ro['ugyldige_rader'])} av {num(ro['paa_lista'])} adresser er gyldige.", 14, 400, G1))

    # Hovedinnhold: bare radene som må rettes
    rx = 600
    gyldig = ro["paa_lista"] - ro["ugyldige_rader"]
    d.add(T(rx - 2, 186, f"{num(ro['ugyldige_rader'])} rader må rettes", 34, 300))
    d.add(T(rx, 218, f"De andre {num(gyldig)} er i orden.", 16, 400, G1))
    ugyldige = [(37, "Nora Lien", "nora.lien@student"), (88, "Emil Berg", "emil.berg.student.example.no"),
                (141, "Thea Moe", "thea moe@student.example.no"), (203, "Jakob Dahl", "jakob.dahl@@student.example.no")]
    grunn = ["Mangler domene", "Mangler @", "Mellomrom i adressen", "To @"]
    yy = 266
    d.add(T(rx, yy, "Rad", 13, 400, G1), T(rx + 60, yy, "Navn", 13, 400, G1), T(rx + 190, yy, "Adresse i fila", 13, 400, G1), T(rx + 500, yy, "Feil", 13, 400, G1))
    yy += 32
    for (rad, n, a), g in zip(ugyldige, grunn):
        d.add(T(rx, yy, str(rad), 16, 700), T(rx + 60, yy, n, 16), T(rx + 190, yy, a, 16), T(rx + 500, yy, g, 15, 400, VER))
        d.add(T(rx + 700, yy, "Rett", 15, 400, INK, "end", u=True))
        yy += 40
    d.add(btn(rx, yy + 16, 330, 58, f"Send {num(gyldig)} Invitasjoner"))
    d.add(T(rx + 354, yy + 42, "Gyldig i 14 dager. Rettede rader kan sendes senere.", 14, 400, G1))

    # Status: én linje i sann lengde
    sy = 640
    d.add(T(rx - 2, sy, "Status etter utsending", 26, 300))
    total = ro["paa_lista"]
    lw = 760
    lx = rx
    ly = sy + 46
    deler = [("registrert", ro["registrert"], INK), ("manuelt registrert", ro["manuelt_registrert"], G1), ("uregistrert", ro["uregistrert"], G3)]
    cur = lx
    for navn, v, c in deler:
        w = v / total * lw
        d.add(L(cur, ly, cur + w - 2, ly, c, 4))
        cur += w
    d.add(R(lx, ly + 36, [(num(ro["registrert"]), 700, INK), (" registrert", 400, G1)], 16))
    d.add(R(lx + 170, ly + 36, [(num(ro["manuelt_registrert"]), 700, INK), (" manuelt registrert", 400, G1)], 16))
    d.add(R(lx + 400, ly + 36, [(num(ro["uregistrert"]), 700, INK), (" uregistrert", 400, G1)], 16))
    d.add(T(lx + 760, ly + 36, "Send påminnelse", 15, 400, INK, "end", u=True))
    d.add(T(80, 952, "Demodata", 13, 400, G1))
    d.save()


def page_03():
    d = Doc("03-laerer-spill", 1440, 1100, "Lag: Klasseøkt",
            "Klasseøkt med forhåndsutfylte standarder, valg av lag i grafen, KI-modus, Debrief-modus, datoer, Labtimer og fordeling.")
    d.add(T(78, 92, "Klasseøkt", 40, 300))
    d.add(T(80, 124, "Klassisk. Alt er forhåndsutfylt, og du kan lagre uten å endre noe.", 17, 400, G1))
    d.add(T(1360, 92, "Lagre uten endring", 16, 700, INK, "end", u=True))

    def liste(x, y, w, rows, lh=30, size=15):
        out = []
        for a, b in rows:
            out.append(T(x, y, a, size, 400, G1))
            out.append(T(x + w, y, b, size, 400, INK, "end"))
            y += lh
        return out, y

    # Venstre: Spillinnstillinger
    x1, w1 = 80, 320
    d.add(T(x1, 190, "Spillinnstillinger", 22, 300))
    rows = [("Startlager", "12"), ("I hvert ledd", "4 enheter"), ("Ordreforsinkelse", "2 uker"), ("Fraktforsinkelse", "2 uker"),
            ("Produksjonsforsinkelse", "2 uker"), ("Etterspørsel", "4, så 8 i uke 5"), ("Lagerkost", "0,50"),
            ("Restordrekost", "1,00"), ("Lengde", "36 uker"), ("Veiledede uker", "1 til 4"), ("Inaktivitetsgrense", "24 t")]
    s, y = liste(x1, 226, w1, rows)
    d.add(s)
    s, y = P(x1, y + 10, "Kildene er uenige om forsinkelser. Dette er produktets standard.", w1, 14, 20, fill=G1)
    d.add(s)
    d.add(T(x1, y + 12, "Endre innstillinger", 15, 400, INK, u=True))

    # Midt: lagene, konseptets eget valg
    x2, w2 = 480, 440
    d.add(T(x2, 190, "Lag i grafen", 22, 300))
    s, _ = P(x2, 222, "Studentene får et nytt lag når det gir mening. Du bestemmer når.", w2, 15, 21, fill=G1)
    d.add(s)
    sc = Sc(x2 + 28, 262, w2 - 28 - 110, 210, 11, -22, 44)
    d.add(axes(sc, [1, 5, 10], [-20, 0, 20, 40], size=12, nowlabel="nå"))
    d.add(plot(d, sc, ("areal", "vei", "inn", "lev", "lager")))
    d.add(endlabels(sc, std_labels(sc, 11), 12))
    lag = [("Lager", "Fra Uke 1", True), ("Ordre inn", "Fra Uke 5", True), ("Levering", "Fra Uke 8", True), ("På vei", "Fra Uke 10", True),
           ("Posisjon", "Etter Debrief", False), ("Simulert referanse", "Etter Debrief", False)]
    y = 524
    for navn, naar, _ in lag:
        d.add(T(x2, y, navn, 16, 700 if _ else 400, INK if _ else G1))
        d.add(T(x2 + w2 - 60, y, naar, 15, 400, INK, "end"))
        d.add(T(x2 + w2, y, "Endre", 14, 400, INK, "end", u=True))
        y += 30

    # Høyre
    x3, w3 = 1000, 360
    d.add(T(x3, 190, "Spillere og Debrief", 22, 300))
    s, y = liste(x3, 226, w3, [("KI-modus", "LLM-spillere"), ("Debrief-modus", "Gruppedebrief"), ("Merket", "Obligatorisk")])
    d.add(s)
    d.add(T(x3, y + 26, "Datoer", 22, 300))
    s, y = liste(x3, y + 62, w3, [("Start", "ti. 24. nov 2026"), ("Spillfrist", "ti. 8. des"), ("Debrief-frist", "fr. 11. des"), ("Testfrist", "fr. 18. des")])
    d.add(s)
    d.add(T(x3, y + 26, "Labtimer", 22, 300))
    s, y = liste(x3, y + 62, w3, [("to. 26. nov", "14:15"), ("ma. 30. nov", "10:15"), ("to. 3. des", "14:15"), ("ma. 7. des", "10:15")])
    d.add(s)
    d.add(T(x3, y, "Datalab A2", 15, 400, G1))

    # Fordeling
    fy = 800
    d.add(T(x1, fy, "Fordeling", 22, 300))
    s, _ = P(x1, fy + 32, "240 studenter fordeles tilfeldig i 60 spill à 4. Ett punkt er én student.", 420, 15, 21, fill=G1)
    d.add(s)
    gx, gy = 80, fy + 76
    cw, rh = 21.3, 13
    n_spill = len(SPILL)
    for i in range(n_spill):
        hl = SPILL[i]["spill"] == 17
        for j in range(4):
            d.add(f'<circle cx="{gx + i * cw + 6:.1f}" cy="{gy + j * rh + 6:.1f}" r="{2.6 if hl else 2.2}" fill="{VER if hl else G1}"/>')
    hx = gx + 16 * cw + 6
    d.add(L(hx, gy + 4 * rh + 2, hx, gy + 4 * rh + 12, VER, 1))
    d.add(T(hx, gy + 4 * rh + 30, "Spill 17: Ida, Sara, Mikkel, Jonas", 15, 700, INK, "middle"))
    d.add(T(x1, 1026, "Kjør fordelingen på nytt", 16, 400, INK, u=True))
    d.add(btn(x1 + 240, 996, 280, 50, "Bekreft fordeling og lagre", 16))
    d.add(T(1360, 1040, "Demodata", 13, 400, G1, "end"))
    d.save()
