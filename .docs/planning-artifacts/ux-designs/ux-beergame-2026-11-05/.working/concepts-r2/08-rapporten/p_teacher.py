"""08-laerer-oversikt, 02-laerer-klasse og 03-laerer-spill."""
from datetime import date

from rlib import *

STAT = {"venter": "Venter", "pauset": "Pauset", "pågår": "Pågår", "ferdig": "Ferdig"}


def sidebar_top(d, W, active, right=None):
    d.t(40, 44, "Rapport", 24, "s", INK, 500)
    d.t(150, 43, "class-of-1994, IBE160", 14, "f", INK2)
    x = W - 40
    if right:
        d.t(x, 43, right, 14, "f", INK2, 400, "end")
    d.line(40, 62, W - 40, 62, GRID, 1)


def micro(d, x, y, w, h, g, ymax):
    """Mikrograf: Detaljist og Fabrikk på samme skala og samme 36 uker. Sann skala, ingen pynt."""
    uke = g["uke"]
    X = lambda k: x + (k - 1) / 35 * w
    Y = lambda val: y + h - min(val, ymax) / ymax * h
    d.line(x, y + h, x + w, y + h, GRID, 0.75)
    for role, stroke, sw in (("Detaljist", SAGE, 1), ("Fabrikk", OCHRE, 1.25)):
        s = g["ordre"][role]
        pts = "L".join(f"{X(k + 1):.1f} {Y(val):.1f}" for k, val in enumerate(s[:uke]))
        d.path("M" + pts, stroke=stroke, sw=sw)


def page_08():
    W, H = 1600, 1000
    d = Doc("oversikt", W, H, "Rapport: redaksjonsmøtet",
            "Lærerens oversikt: tre setninger om hva som krever deg nå, trakten og tabell over 60 Klassespill med mikrografer fra ekte serier.", bg=PAPER)
    spill = KL["spill"]
    order = {"venter": 0, "pauset": 1, "pågår": 2, "ferdig": 3}
    rows = sorted(spill, key=lambda g: (order[g["status"]], -(g.get("ventet_timer") or 0), -g["uke"], g["spill"]))
    n = {k: sum(1 for g in spill if g["status"] == k) for k in order}
    assert n["ferdig"] == 41 and n["venter"] == 4 and n["pauset"] == 2 and n["pågår"] == 13
    ymax = max(max(g["ordre"]["Fabrikk"]) for g in spill)
    sidebar_top(d, W, "Oversikt", "Faglærer Bård")

    # Redaksjonsmøtet
    tr = KL["traktA"]
    venter = [g for g in spill if g["status"] == "venter"]
    venter.sort(key=lambda g: -g["ventet_timer"])
    v0 = venter[0]
    assert v0["spill"] == 2
    mangler = tr["klassespill_ferdig"] - tr["debrief_ferdig"]
    d.t(40, 104, "Dette krever deg nå", 30, "s", INK, 500)
    y = 146
    lines = [
        f"**Spill {v0['spill']}** har ventet på {v0['navn']} ({v0['venter_paa']}) i {v0['ventet_timer']} t. KI overtar om {24 - v0['ventet_timer']} t.",
        f"Tre andre spill venter: " + ", ".join(f"spill {g['spill']} på {g['navn']} ({g['ventet_timer']} t)" for g in venter[1:]) + ".",
        f"{mangler} studenter har spilt ferdig, men ikke tatt Debriefen.",
    ]
    for line in lines:
        d.t(40, y, line, 20, "s", INK)
        y += 32

    # Trakten
    fx0, fw = 960, 600
    d.t(fx0, 88, "Trakten: studenter per steg", 15, "f", INK, 600)
    steps = [("Registrert", tr["registrert"]), ("Klassespill ferdig", tr["klassespill_ferdig"]), ("Debrief ferdig", tr["debrief_ferdig"]),
             ("Quiz bestått", tr["quiz_bestått"]), ("Replay ferdig", tr["replay_ferdig"]), ("Test levert", tr["test_levert"]), ("KI-vurdering klar", tr["ki_vurdering_klar"])]
    yy = 108
    for lab, val in steps:
        d.t(fx0, yy + 2, lab, 13, "f", INK2)
        bw = (fw - 170) * val / tr["registrert"]
        if val:
            d.rect(fx0 + 130, yy - 8, bw, 11, fill=SAGE, rx=1)
        d.t(fx0 + 130 + bw + 6, yy + 2, str(val), 13, "f", INK, 500)
        yy += 16.5

    # Regel fra første setning til raden, og fra tredje setning til trakten
    d.path("M36 141H28V305H34", stroke=INK2, sw=0.75)
    d.ring(28, 141, 2.5)
    y3 = 146 + 2 * 32 - 6
    x3 = 40 + tw(lines[2], 20, "s") + 22
    bar_y = 108 + 2 * 16.5 - 3
    bar_x = fx0 + 130 + (fw - 170) * tr["debrief_ferdig"] / tr["registrert"]
    d.path(f"M{x3:.1f} {y3:.1f}H{fx0 - 12}V{bar_y:.1f}H{fx0 - 3}", stroke=INK2, sw=0.75)
    # Filter
    fy = 244
    xx = 40
    for lab, cnt, on in [("Alle", 60, True), ("Venter", n["venter"], False), ("Pauset", n["pauset"], False), ("Pågår", n["pågår"], False), ("Ferdig", n["ferdig"], False)]:
        label = f"{lab} {cnt}"
        wi = tw(label, 14, "f") + 22
        d.rect(xx, fy - 18, wi, 28, fill=WASH if on else "none", stroke=None if on else GRID, rx=3)
        d.t(xx + 11, fy + 1, label, 14, "f", INK, 500 if on else 400)
        xx += wi + 6
    label = f"Med KI-seter {sum(1 for g in spill if g['ki_seter'])}"
    wi = tw(label, 14, "f") + 22
    d.rect(xx + 16, fy - 18, wi, 28, fill="none", stroke=GRID, rx=3)
    d.t(xx + 27, fy + 1, label, 14, "f", INK)
    d.key(650, fy + 1, [("line", OCHRE, "Fabrikkens ordre"), ("line", SAGE, "Detaljistens ordre")], 13, 12)
    d.t(1000, fy + 1, f"Samme skala, 0 til {ymax}, 36 uker", 13, "f", INK2)
    d.button(W - 40 - 170, fy - 20, 170, 32, "Send Melding til valgte", False, 13)
    d.button(W - 40 - 170 - 118, fy - 20, 108, 32, "Pause valgte", False, 13)

    # Tabell: 3 spalter x 20
    cols = 3
    cw, gap = 494, 19
    ry0, rh = 288, 34
    for ci in range(cols):
        cx = 40 + ci * (cw + gap)
        hy = ry0 - 8
        d.t(cx, hy, "Spill", 13, "f", INK2)
        d.t(cx + 42, hy, "Status", 13, "f", INK2)
        d.t(cx + 184, hy, "Ordre", 13, "f", INK2)
        d.t(cx + 350, hy, "Uke", 13, "f", INK2, 400, "end")
        d.t(cx + cw, hy, "Kost, kr", 13, "f", INK2, 400, "end")
        d.line(cx, ry0 - 1, cx + cw, ry0 - 1, INK2, 0.75)
    for i, g in enumerate(rows):
        ci, ri = divmod(i, 20)
        cx = 40 + ci * (cw + gap)
        ry = ry0 + ri * rh
        urgent = g["status"] == "venter" and g["ventet_timer"] >= 23
        if urgent:
            d.rect(cx - 6, ry + 1, cw + 12, rh - 2, fill=OCHRE_W, rx=2)
        wgt = 600 if urgent else 500
        d.t(cx, ry + 22, str(g["spill"]), 14, "f", INK, wgt)
        if g["status"] == "venter":
            t = f"{g['navn']}, {g['ventet_timer']} t"
        elif g["status"] == "pauset":
            t = "Pauset til 19:00"
        elif g["status"] == "pågår":
            t = "Pågår"
        else:
            t = "Ferdig"
        d.t(cx + 42, ry + 22, t, 13, "f", INK if g["status"] in ("venter", "pauset") else INK2, 600 if urgent else (500 if g["status"] == "venter" else 400))
        if g["ki_seter"]:
            d.t(cx + 150, ry + 22, f"KI {g['ki_seter']}", 13, "f", INK, 500)
        micro(d, cx + 184, ry + 5, 136, rh - 9, g, ymax)
        d.t(cx + 350, ry + 22, str(g["uke"]), 13, "f", INK2, 400, "end")
        d.t(cx + cw, ry + 22, nb(g["kjedekost"], 0), 13, "f", INK, 400, "end")
        if not urgent:
            d.line(cx, ry + rh, cx + cw, ry + rh, GRID, 0.5)
    # Regel-kommentar til spill 2: festet til raden
    d.t(40 + 360, ry0 + 21, "Send Melding", 13, "f", INK, 600)
    d.line(40 + 360, ry0 + 25, 40 + 360 + tw("Send Melding", 13, "f") - 6, ry0 + 25, INK, 1)

    d.t(40, H - 14, "Demodata. Rekkefølge: de som venter lengst, først. Kostnad er kjedens totalkostnad så langt.", 13, "f", INK3)
    d.t(W - 40, H - 14, "Alle spill i plenum", 13, "f", INK, 500, "end")
    return d


def page_02():
    W, H = 1440, 1000
    d = Doc("klasse", W, H, "Rapport: lag Klasse",
            "Faglærer lager Klasse, laster opp Canvas-eksport, velger e-postkolonne, ser ugyldige rader og sender Invitasjoner.", bg=PAPER)
    sidebar_top(d, W, "Klasse", "Faglærer Bård")
    ro = KL["roster"]
    d.t(40, 112, "Lag Klasse", 34, "s", INK, 500)
    d.para(40, 146, 1100, "Studentlisten kommer fra Canvas-eksporten. Du kan rette radene her eller sende Invitasjoner til de gyldige nå.", 18, "s", INK2, 26)

    # Venstre: skjema
    x0 = 40
    y = 200
    for lab, val, wi in [("Navn på Klassen", "class-of-1994", 300), ("Emnekode", "IBE160", 150)]:
        xx = x0 if lab.startswith("Navn") else x0 + 320
        d.t(xx, y, lab, 14, "f", INK, 500)
        d.rect(xx, y + 10, wi, 44, fill=WASH, rx=3)
        d.t(xx + 12, y + 38, val, 16, "f", INK)
    y = 290
    d.t(x0, y, "Canvas-eksport", 14, "f", INK, 500)
    d.rect(x0, y + 10, 470, 56, fill="none", stroke=INK2, rx=3)
    d.t(x0 + 14, y + 34, "ibe160-studenter-2026.xlsx", 15, "f", INK, 500)
    d.t(x0 + 14, y + 54, f"{ro['paa_lista']} rader, lastet opp", 13, "f", INK2)
    d.t(x0 + 456, y + 44, "Bytt fil", 14, "f", INK, 500, "end")
    y = 384
    d.t(x0, y, "Hvilken kolonne er e-post?", 14, "f", INK, 500)
    yy = y + 22
    for lab, ex, on in [("Name", "Sara Lunde", False), ("SIS Login ID", "saralu", False), ("Email", "sara.lunde@student.example.no", True), ("Section", "IBE160-1", False)]:
        d.circle(x0 + 8, yy, 7, fill=PAPER, stroke=INK if on else INK2, sw=1.25)
        if on:
            d.circle(x0 + 8, yy, 3.5, fill=INK)
        d.t(x0 + 26, yy + 5, lab, 14, "f", INK, 500 if on else 400)
        d.t(x0 + 150, yy + 5, ex, 14, "f", INK2)
        yy += 30
    y = yy + 22
    d.t(x0, y, "Invitasjon", 14, "f", INK, 500)
    d.para(x0, y + 22, 470, "Gyldig i 14 dager. Studentene registrerer seg med lenken, og du ser status her.", 15, "s", INK, 22)
    d.button(x0, y + 68, 300, 54, f"Send {ro['paa_lista'] - ro['ugyldige_rader']} Invitasjoner", True, 16)
    d.button(x0 + 312, y + 68, 158, 54, "Lagre utkast", False, 15)
    y2 = d.para(x0, y + 152, 470, f"De {ro['ugyldige_rader']} ugyldige radene får ingen Invitasjon før du retter dem.", 15, "s", INK2, 22)
    d.t(x0, y2 + 26, "Dette får studentene", 14, "f", INK, 500)
    d.rect(x0, y2 + 38, 470, 112, fill=WASH, rx=3)
    d.para(x0 + 14, y2 + 66, 415, "Du er invitert til en øvelse i forsyningskjeder i IBE160. Dere spiller i grupper på fire, på mobil eller PC, på tiden dere selv velger. Lenken er gyldig i 14 dager.", 15, "s", INK, 22)

    # Høyre: radstripe og ugyldige
    x1 = 580
    w1 = 820
    d.t(x1, 214, f"{ro['ugyldige_rader']} av {ro['paa_lista']} rader må rettes", 26, "s", INK, 500)
    bad = [37, 88, 141, 203]
    sy = 262
    X = lambda r: x1 + (r - 1) / (ro["paa_lista"] - 1) * w1
    for r in range(1, ro["paa_lista"] + 1):
        d.line(X(r), sy, X(r), sy + 26, OCHRE if r in bad else SAGE, 1.6 if r in bad else 0.7)
    d.t(x1, sy + 44, "Rad 1", 13, "f", INK3)
    d.t(x1 + w1, sy + 44, f"Rad {ro['paa_lista']}", 13, "f", INK3, 400, "end")
    rows = [(37, "Emma Solheim", "emma.solheim@student", "Mangler domene"), (88, "Jakob Berg", "jakob,berg@student.example.no", "Komma i adressen"),
            (141, "Nora Lie", "", "Tom celle"), (203, "Elias Moe", "elias.moe@@student.example.no", "To @")]
    ry = sy + 98
    dy = 74
    for i, (r, name, mail, why) in enumerate(rows):
        yy = ry + i * dy
        d.t(x1, yy + 12, f"Rad {r}", 15, "f", INK, 600)
        d.t(x1 + 70, yy + 12, name, 15, "f", INK)
        d.rect(x1 + 220, yy - 10, 360, 34, fill=WASH, rx=3)
        d.t(x1 + 232, yy + 12, mail if mail else "Skriv inn adresse", 14, "f", INK if mail else INK2)
        d.t(x1 + 596, yy + 12, why, 14, "f", INK)
        d.t(x1 + w1, yy + 12, "Fjern", 14, "f", INK, 500, "end")
    # Tynne regler fra stripe ned til rad: tall på stripen
    for i, r in enumerate(bad):
        xr = X(r)
        d.t(xr, sy - 6, str(r), 13, "f", INK, 600, "middle")
    # Status
    sy2 = ry + 4 * dy + 34
    d.line(x1, sy2 - 16, x1 + w1, sy2 - 16, GRID, 1)
    d.t(x1, sy2 + 18, "Status etter Invitasjon", 24, "s", INK, 500)
    tot = ro["paa_lista"]
    parts = [("Registrert", ro["registrert"], SAGE), ("Manuelt registrert", ro["manuelt_registrert"], FOREST), ("Uregistrert", ro["uregistrert"], OCHRE)]
    bx = x1
    by = sy2 + 40
    for lab, val, col in parts:
        bw = w1 * val / tot
        d.rect(bx, by, max(bw - 2, 2), 14, fill=col)
        bx += bw
    d.t(x1, by + 40, f"**{ro['registrert']}** registrert", 16, "f", INK)
    d.t(x1 + 180, by + 40, f"**{ro['manuelt_registrert']}** manuelt registrert", 16, "f", INK)
    d.t(x1 + 420, by + 40, f"**{ro['uregistrert']}** uregistrert", 16, "f", INK)
    d.t(x1 + w1, by + 40, "Send påminnelse til 10", 15, "f", INK, 500, "end")
    d.line(x1 + w1 - tw("Send påminnelse til 10", 15, "f"), by + 44, x1 + w1, by + 44, INK, 1)
    d.t(x1, by + 72, "Tallene viser Klassen etter at Invitasjonene er sendt. Demodata.", 13, "f", INK3)
    return d


def page_03():
    W, H = 1440, 1100
    d = Doc("oppsett", W, H, "Rapport: sett opp Klasseøkt",
            "Forhåndsutfylte standarder, KI-modus, Debrief-modus, Obligatorisk, datoer, Labtimer og fordeling i 60 spill à 4.", bg=PAPER)
    sidebar_top(d, W, "Klasseøkt", "Faglærer Bård")
    d.t(40, 112, "Klasseøkt", 34, "s", INK, 500)
    d.para(40, 146, 780, "Alt er fylt ut med standardene, «Klassisk». Du kan lagre uten å endre noe.", 18, "s", INK2, 26)
    d.button(W - 40 - 250, 92, 250, 50, "Lagre Klasseøkten", True, 16)

    # Spillinnstillinger
    x0 = 40
    y = 200
    d.t(x0, y, "Spillinnstillinger", 24, "s", INK, 500)
    rows = [("Startlager", "12"), ("I hvert ledd ved start", "4 enheter"), ("Ordreforsinkelse", "2 uker"), ("Fraktforsinkelse", "2 uker"),
            ("Produksjonsforsinkelse", "2 uker"), ("Lagerkost", "0,50 per enhet per uke"), ("Restordrekost", "1,00 per enhet per uke"),
            ("Lengde", "36 uker"), ("Veiledede uker", "Uke 1 til 4"), ("Inaktivitetsgrense", "24 t, så KI overtar")]
    y += 34
    for lab, val in rows:
        d.t(x0, y, lab, 15, "f", INK2)
        d.t(x0 + 230, y, val, 15, "f", INK, 500)
        d.line(x0, y + 11, x0 + 480, y + 11, GRID, 0.75)
        y += 36
    d.para(x0, y + 6, 480, "Kildene er uenige om forsinkelsene. Dette er produktets standard, og du kan endre dem.", 15, "s", INK, 22)
    y += 84
    # Etterspørsel: liten graf
    d.t(x0, y, "Etterspørsel, bare for deg", 19, "s", INK, 500)
    c = Chart(d, x0 + 26, y + 14, 320, 130, 1, 36, 0, 10)
    c.grid([0, 4, 8])
    c.step(S17["demand"], 1, 36, INK, 2)
    c.weeks([1, 36])
    xd, yd = c.P(5, 8)
    d.note(xd, yd, c.X(36) + 14, yd - 9, "**4** til **8** i Uke 5, deretter stabil.", 120, 14, route="hv")
    d.t(x0, y + 190, "Studentene ser den ikke før Debriefen.", 13, "f", INK2)

    # Midten: valg
    x1 = 580
    y = 200
    d.t(x1, y, "Valg", 24, "s", INK, 500)
    y += 34
    groups = [("KI-modus", [("LLM-spillere", True), ("Regelspillere", False)]), ("Debrief-modus", [("Gruppedebrief", True), ("Personlig debrief", False)])]
    for lab, opts in groups:
        d.t(x1, y, lab, 15, "f", INK2)
        xx = x1 + 120
        for o, on in opts:
            wi = tw(o, 14, "f") + 24
            d.rect(xx, y - 20, wi, 30, fill=WASH if on else "none", stroke=None if on else GRID, rx=3)
            d.t(xx + 12, y, o, 14, "f", INK, 500 if on else 400)
            xx += wi + 6
        y += 44
    d.t(x1, y, "Obligatorisk", 15, "f", INK2)
    d.rect(x1 + 120, y - 15, 18, 18, fill=INK, rx=2)
    d.path(f"M{x1 + 124} {y - 6}L{x1 + 128} {y - 2}L{x1 + 134} {y - 10}", stroke=WHITE, sw=1.6)
    d.t(x1 + 148, y, "Klasseøkten er obligatorisk for hele Klassen", 14, "f", INK)
    y += 54

    # Datoer som tidslinje med sann kalender
    d.t(x1, y, "Datoer og Labtimer", 24, "s", INK, 500)
    tl_x, tl_w = x1 + 4, 790
    d0, d1 = date(2026, 11, 24), date(2026, 12, 18)
    X = lambda dd: tl_x + (dd - d0).days / (d1 - d0).days * tl_w
    ty = y + 118
    d.line(tl_x, ty, tl_x + tl_w, ty, INK2, 1)
    # Kalenderuker
    for off in range(0, 25):
        dd = date.fromordinal(d0.toordinal() + off)
        d.line(X(dd), ty, X(dd), ty + (6 if dd.weekday() == 0 else 3), INK3, 0.75)
    marks = [(date(2026, 11, 24), "Start", "ti. 24. nov", "r"), (date(2026, 12, 8), "Spillfrist", "ti. 8. des", "r"),
             (date(2026, 12, 11), "Debrief-frist", "fr. 11. des", "r"), (date(2026, 12, 18), "Testfrist", "fr. 18. des", "l")]
    for dd, lab, dt, side in marks:
        xx = X(dd)
        offset = 58 if lab != "Debrief-frist" else 58
        top = ty - offset
        d.line(xx, top, xx, ty, INK2, 0.75)
        d.ring(xx, ty)
        tx = xx + 7 if side == "r" else xx - 7
        anc = "start" if side == "r" else "end"
        d.t(tx, top + 12, lab, 14, "f", INK, 600, anc)
        d.t(tx, top + 30, dt, 14, "f", INK2, 400, anc)
    labs = [(date(2026, 11, 26), "to. 26. nov", "14:15"), (date(2026, 11, 30), "ma. 30. nov", "10:15"), (date(2026, 12, 3), "to. 3. des", "14:15"), (date(2026, 12, 7), "ma. 7. des", "10:15")]
    for dd, dt, tm in labs:
        xx = X(dd)
        d.rect(xx - 3, ty - 3, 6, 6, fill=FOREST)
        d.line(xx, ty + 3, xx, ty + 22, INK2, 0.75)
        d.t(xx, ty + 38, dt, 13, "f", INK, 500, "middle")
        d.t(xx, ty + 55, tm, 13, "f", INK2, 400, "middle")
    d.key(tl_x, ty + 84, [("ring", INK, "Start og frister")], 13, 16)
    xk = tl_x + 130
    d.rect(xk, ty + 73, 8, 8, fill=FOREST)
    d.t(xk + 14, ty + 84, "Labtime, Datalab A2", 13, "f", INK2)
    y = ty + 140

    # Fordeling
    d.t(x1, y, "Fordeling", 24, "s", INK, 500)
    y = d.para(x1, y + 30, 790, "240 studenter fordeles tilfeldig i 60 spill à 4, med Rollene trukket innad i hvert spill.", 16, "s", INK, 23)
    sq, gp = 8, 1.5
    gw = 39
    gy = y + 2
    rowh = 40
    for i in range(60):
        cx = x1 + (i % 20) * (gw + 2)
        cy = gy + (i // 20) * rowh
        for k in range(4):
            d.rect(cx + k * (sq + gp), cy, sq, 30, fill=OCHRE if (i == 16 and k == 1) else SAGE)
    xr = x1 + 16 * (gw + 2) + 1 * (sq + gp) + sq / 2
    yr = gy + 30
    y = gy + 3 * rowh + 6
    d.line(xr, yr, xr, y + 18, INK2, 0.75)
    d.ring(xr, yr)
    d.t(xr - 7, y + 14, "Spill 17: Sara trakk Grossist. Hver stolpe er ett sete.", 14, "s", INK, 400, "end", halo=PAPER)
    y += 42
    d.button(x1, y, 170, 44, "Fordel på nytt", False, 14)
    d.button(x1 + 182, y, 220, 44, "Bekreft fordelingen", True, 14)
    d.t(x1 + 420, y + 27, "Etter bekreftelse sendes Melding til alle.", 14, "f", INK2)
    return d
