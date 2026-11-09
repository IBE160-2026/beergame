"""Lærerflatene: samme blekk, streng grid. 02 Klasse, 03 Klasseøkt, 08 Oversikt (redaksjonsveggen)."""
from c06_ink import *  # noqa: F403

GAMES = FX["class_games"]


def topbar(W, here):
    o = [f'<rect x="0" y="0" width="{W}" height="64" fill="{YEL}"/>', iline(0, 64, W, 64, 3)]
    o.append(T(32, 44, "Uke for uke", 26, "d"))
    x = 300
    for lab in ["Klasser", "Klasseøkter", "Oversikt", "Meldinger"]:
        o.append(T(x, 41, lab, 20, "hb" if lab == here else "h"))
        if lab == here:
            o.append(iline(x, 48, x + tw(lab, 20, "hb"), 48, 2.6))
        x += tw(lab, 20) + 42
    o.append(T(W - 32, 41, "Bård, Faglærer", 19, "h", INK, "end"))
    return "".join(o)


def rute(x, y, w, h, title, flat=WHITE):
    o = [ibox(x, y, w, h, flat, None, 3, mis=(0, 0))]
    o.append(T(x + 18, y + 34, title, 22, "d"))
    return "".join(o)


def table(x, y, cols, rows, rowh=34, head=True, size=17):
    """Ærlig tabell i blekk. cols = [(tittel, bredde, justering)]. rows = lister med str eller (str, ikon)."""
    w = sum(c[1] for c in cols)
    o = []
    cy = y
    if head:
        o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{rowh}" fill="{dots("dk")}"/>')
        o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{rowh}" fill="{WHITE}" opacity=".55"/>')
        cx = x
        for t, cw, al in cols:
            tx = cx + 8 if al == "start" else cx + cw - 8
            o.append(T(tx, y + rowh - 10, t, size, "hb", INK, al))
            cx += cw
        o.append(iline(x, y + rowh, x + w, y + rowh, 2.4, j=.4))
        cy += rowh
    for r in rows:
        cx = x
        for (t, cw, al), cell in zip(cols, r):
            tx = cx + 8 if al == "start" else cx + cw - 8
            if isinstance(cell, tuple):
                kind = cell[1]
                if kind in ("ok", "wait", "exp", "x"):
                    o.append(status_cell(cx + 4, cy + rowh - 11, cell[0], kind))
                elif kind == "b":
                    o.append(T(tx, cy + rowh - 11, cell[0], size, "hb", INK, al))
                elif kind == "m":
                    o.append(T(tx, cy + rowh - 11, cell[0], size, "hb", MAG, al))
            else:
                o.append(T(tx, cy + rowh - 11, cell, size, "h", INK, al))
            cx += cw
        o.append(iline(x, cy + rowh, x + w, cy + rowh, 1.2, j=.5))
        cy += rowh
    return "".join(o)


def field(x, y, w, label, value, h=42, fill=WHITE, soft=False):
    return (T(x, y, label, 17, "hb") + plain(x, y + 7, w, h, fill, 2.2) +
            T(x + 12, y + 7 + h / 2 + 7, value, 20, "h", SOFT if soft else INK))


# ---- 02 Klasse ------------------------------------------------------------------------------------
def klasse():
    p = Page("02-laerer-klasse.svg", "klasse", 1440, 1000, "Faglærer lager Klasse",
             "Navn og emnekode, Canvas-fil, e-postkolonne, ugyldige rader listet per rad, Invitasjoner og status sendt, akseptert, utløpt.")
    p.add(topbar(1440, "Klasser"))
    p.add(T(32, 116, "Ny Klasse: class-of-1994", 34, "d"))
    p.add(T(1408, 110, "Demodata", 17, "hb", INK, "end"))
    lx, lw = 32, 612
    rx, rw = 664, 744
    # navn
    p.add(rute(lx, 136, lw, 128, "Navn og emnekode"))
    p.add(field(lx + 18, 196, 360, "Navn på Klassen", "class-of-1994"))
    p.add(field(lx + 396, 196, 198, "Emnekode", "IBE160"))
    # opplasting
    p.add(rute(lx, 278, lw, 150, "Last opp Canvas-fil"))
    p.add(plain(lx + 18, 326, lw - 36, 84, "#FFF6C2", 2, dash="7 5"))
    p.add(ic_page(lx + 48, 368, 1.9))
    p.add(T(lx + 78, 358, "ibe160-canvas-eksport.csv", 21, "hb"))
    p.add(T(lx + 78, 386, "250 rader. Excel og CSV går fint.", 18))
    p.add(button(lx + lw - 160, 346, 130, 44, "Bytt fil", "sec", 18))
    # e-postkolonne
    p.add(rute(lx, 442, lw, 262, "Velg e-postkolonne"))
    p.add(T(lx + 18, 498, "Vi tror det er kolonne 3. Trykk på en annen hvis det er feil.", 18))
    cols = [("Student", 150), ("ID", 76), ("E-post", 240), ("Seksjon", 110)]
    x0 = lx + 18
    x = x0
    y0 = 512
    for i, (c, w) in enumerate(cols):
        if c == "E-post":
            p.add(ibox(x, y0, w, 174, CYA, None, 2.6, mis=(0, 0)))
            p.add(circ(x + 18, y0 + 20, 8, WHITE, INK, 2.2) + f'<circle cx="{x+18}" cy="{y0+20}" r="3.8" fill="{INK}"/>')
            p.add(T(x + 34, y0 + 27, c, 18, "hb"))
        else:
            p.add(circ(x + 14, y0 + 20, 8, WHITE, INK, 2))
            p.add(T(x + 28, y0 + 27, c, 18, "hb"))
        x += w
    p.add(iline(x0, y0 + 38, x0 + 576, y0 + 38, 2.2))
    prev = [("Nilsen, Sara", "11 017", "sara.nilsen@stud.example.no", "IBE160-1"),
            ("Aas, Ida", "11 042", "ida.aas@stud.example.no", "IBE160-1"),
            ("Berg, Mikkel", "11 063", "mikkel.berg@stud.example.no", "IBE160-2"),
            ("Moe, Jonas", "11 071", "jonas.moe@stud.example.no", "IBE160-2")]
    for j, row in enumerate(prev):
        yy = y0 + 62 + j * 32
        x = x0
        for (c, w), v in zip(cols, row):
            p.add(T(x + 8, yy, v, 16.5))
            x += w
        p.add(iline(x0, yy + 9, x0 + 576, yy + 9, 1, j=.4))
    # Bård-rute med forklaring
    p.add(ibox(lx, 718, lw, 250, PAPER, "dc", 3, mis=(0, 0)))
    p.add(fig(lx + 70, 958, "Kunde", 1.65, "rolig"))
    p.add(bubble(lx + 134, 736, lw - 154, 134, (lx + 100, 800), "l", WHITE, 2.6))
    p.add(T(lx + 156, 768, "Du trenger ikke rette alt nå.", 20, "hb"))
    p.add(Pg(lx + 156, 794, "De 246 gyldige kan få Invitasjon med en gang. De fire andre retter du når du har svaret, eller registrerer dem manuelt.", lw - 196, 18))
    p.add(iline(lx + 12, 959, lx + lw - 12, 959, 2.2))

    # høyre: ugyldige rader
    p.add(rute(rx, 136, rw, 302, "Ugyldige rader: 4 av 250"))
    p.add(T(rx + rw - 18, 164, "Listet per rad", 18, "h", INK, "end"))
    rows = [(("37", "b"), "Berg, Emil", "emil.berg@stud", ("Mangler domene", "m"), "Rett"),
            (("88", "b"), "Larsen, Noah", "noah larsen@stud.example.no", ("Mellomrom i adressen", "m"), "Rett"),
            (("141", "b"), "Dahl, Maja", "(tom celle)", ("Ingen adresse", "m"), "Rett"),
            (("203", "b"), "Moe, Hanna", "hanna..moe@stud.example.no", ("To punktum på rad", "m"), "Rett")]
    p.add(table(rx + 18, 186, [("Rad", 56, "start"), ("Student", 130, "start"), ("Verdien i fila", 256, "start"), ("Problem", 180, "start"), ("", 86, "start")], rows, 40))
    for i in range(4):
        y = 186 + 40 * (i + 1) + 5
        p.add(plain(rx + rw - 100, y, 70, 30, WHITE, 2))
        p.add(T(rx + rw - 65, y + 22, "Rett", 17, "hb", INK, "middle"))
    p.add(button(rx + 18, 394, 300, 34, "Registrer manuelt i stedet", "sec", 17))
    # send
    p.add(ibox(rx, 452, rw, 150, YEL, None, 3))
    p.add(T(rx + 18, 486, "Send Invitasjoner", 22, "d"))
    p.add(T(rx + 18, 516, "246 gyldige adresser. Hver Invitasjon er gyldig i 14 dager.", 19))
    p.add(T(rx + 18, 540, "Ingen åpen registrering: bare de på lista kommer inn.", 19))
    p.add(button(rx + 18, 552, 340, 40, "Send 246 Invitasjoner", "prim", 18))
    p.add(button(rx + 370, 552, 240, 40, "Se e-posten først", "sec", 18))
    # status
    p.add(rute(rx, 616, rw, 352, "Status for Invitasjoner"))
    stats = [("Sendt", "246", "wait"), ("Akseptert", "238", "ok"), ("Venter", "5", "wait"), ("Utløpt", "3", "exp")]
    sx = rx + 18
    for lab, val, kind in stats:
        p.add(plain(sx, 664, 122, 72, WHITE, 2))
        p.add({"ok": ic_check, "wait": ic_hour, "exp": ic_clock}[kind](sx + 16, 682, .9))
        p.add(T(sx + 30, 688, lab, 18, "hb"))
        p.add(T(sx + 10, 726, val, 28, "d"))
        sx += 130
    p.add(T(sx + 4, 680, "Klasselista", 18, "hb"))
    for i, t in enumerate(["238 registrert", "2 manuelt registrert", "10 uregistrert"]):
        p.add(T(sx + 4, 702 + i * 20, t, 17))
    rows = [("Aas, Ida", "ida.aas@stud.example.no", ("Akseptert", "ok"), "3. nov"),
            ("Berg, Emil", "rettet fra rad 37", ("Manuelt registrert", "ok"), "4. nov"),
            ("Eide, Tuva", "tuva.eide@stud.example.no", ("Venter, 9 dager igjen", "wait"), "sendt 2. nov"),
            ("Foss, Adam", "adam.foss@stud.example.no", ("Utløpt", "exp"), "sendt 20. okt")]
    p.add(table(rx + 18, 748, [("Student", 130, "start"), ("Adresse", 236, "start"), ("Status", 220, "start"), ("Dato", 122, "start")], rows, 33))
    p.add(button(rx + 18, 918, 330, 38, "Send på nytt til de 8 som mangler", "sec", 17))
    p.save()


# ---- 03 Klasseøkt -----------------------------------------------------------------------------------
def segmented(x, y, w, h, opts, active):
    o = []
    cw = w / len(opts)
    for i, op in enumerate(opts):
        on = i == active
        o.append(plain(x + i * cw, y, cw, h, YEL if on else WHITE, 2.4 if on else 1.8))
        if on:
            o.append(ic_check(x + i * cw + 18, y + h / 2, .9))
        o.append(T(x + i * cw + (32 if on else 14), y + h / 2 + 7, op, 19, "hb" if on else "h"))
    return "".join(o)


def oppsett():
    p = Page("03-laerer-spill.svg", "okt", 1440, 1100, "Faglærer setter opp Klasseøkt",
             "Forhåndsutfylte standarder, KI-modus, Debrief-modus, Obligatorisk, datoer, Labtimer, fordeling 60 spill à 4. Kan lagres uten endring.")
    p.add(topbar(1440, "Klasseøkter"))
    p.add(T(32, 116, "Klasseøkt for class-of-1994", 34, "d"))
    p.add(T(1408, 110, "Demodata", 17, "hb", INK, "end"))
    lx, lw = 32, 680
    rx, rw = 732, 676
    # standarder + kjede
    p.add(rute(lx, 136, lw, 582, "Spillinnstillinger"))
    p.add(ibox(lx + lw - 170, 148, 152, 38, YEL, None, 2.6))
    p.add(ic_check(lx + lw - 150, 167, .9) + T(lx + lw - 136, 174, "Klassisk", 20, "hb"))
    # kjeden med forsinkelser
    cy = 318
    xs = [lx + 76, lx + 248, lx + 420, lx + 592]
    for i, r in enumerate(ROLES):
        p.add(fig(xs[i], cy, r, 1.0 if r != "Distributør" else .86))
        p.add(T(xs[i], cy + 22, r, 16.5, "hb", INK, "middle"))
    p.add(iline(lx + 18, cy + 1, lx + lw - 18, cy + 1, 2))
    for i in range(3):
        mx = (xs[i] + xs[i + 1]) / 2
        p.add(T(mx, cy - 72, "ordre 2 uker", 16, "h", INK, "middle"))
        p.add(arrow(mx - 42, cy - 62, mx + 42, cy - 62, 2, INK, bend=-3, head=7))
        p.add(arrow(mx + 42, cy - 36, mx - 42, cy - 36, 2, INK, bend=-3, head=7))
        p.add(T(mx, cy - 14, "frakt 2 uker", 16, "h", INK, "middle"))
    rows1 = [("Startlager", "12"), ("Enheter i hvert ledd", "4"), ("Ordreforsinkelse", "2 uker"), ("Fraktforsinkelse", "2 uker"), ("Produksjonsforsinkelse", "2 uker"), ("Etterspørsel", "4, så 8 i uke 5")]
    rows2 = [("Lagerkost", "0,50 kr"), ("Restordrekost", "1,00 kr"), ("Antall uker", "36"), ("Veiledede uker", "1–4"), ("Inaktivitetsgrense", "24 t"), ("KI i tomme seter", "Alltid")]
    ty = 356
    p.add(table(lx + 18, ty, [("Innstilling", 210, "start"), ("Verdi", 110, "start")], [[a, (b, "b")] for a, b in rows1], 34))
    p.add(table(lx + 346, ty, [("Innstilling", 190, "start"), ("Verdi", 126, "start")], [[a, (b, "b")] for a, b in rows2], 34))
    p.add(plain(lx + 18, 606, lw - 36, 96, "#FFF6C2", 2))
    p.add(T(lx + 32, 634, "Kildene er uenige om forsinkelsene.", 20, "hb"))
    p.add(T(lx + 32, 660, "Dette er produktets standard. Du kan endre alt, og endringen", 18))
    p.add(T(lx + 32, 682, "gjelder alle Klassespill. Et testspill viser hva den gjør.", 18))
    # modus
    p.add(rute(lx, 732, lw, 256, "Modus"))
    p.add(T(lx + 18, 788, "KI-modus", 18, "hb"))
    p.add(segmented(lx + 18, 796, lw - 36, 46, ["LLM-spillere", "Regelbaserte spillere"], 0))
    p.add(T(lx + 18, 868, "Debrief-modus", 18, "hb"))
    p.add(segmented(lx + 18, 876, lw - 36, 46, ["Gruppedebrief", "Personlig debrief"], 0))
    p.add(rr(lx + 18, 942, 56, 30, 15, YEL, INK, 2.4) + circ(lx + 58, 957, 10, INK, INK, 1))
    p.add(ic_check(lx + 34, 957, .7))
    p.add(T(lx + 88, 964, "Obligatorisk", 21, "hb"))
    p.add(T(lx + 196, 964, "for alle på Klasselista", 18))
    # datoer
    p.add(rute(rx, 136, rw, 214, "Datoer"))
    p.add(table(rx + 18, 186, [("", 250, "start"), ("", 200, "start"), ("", 190, "start")],
                [["Start", ("ti. 24. nov 2026", "b"), "Første Uke åpner"],
                 ["Spillfrist", ("ti. 8. des", "b"), "KI spiller ferdig"],
                 ["Debrief-frist", ("fr. 11. des", "b"), "For sent blir registrert"],
                 ["Testfrist", ("fr. 18. des", "b"), "Individuell test"]], 37, head=False, size=18))
    # labtimer
    p.add(rute(rx, 364, rw, 212, "Labtimer"))
    p.add(T(rx + rw - 18, 396, "Datalab A2", 19, "hb", INK, "end"))
    p.add(table(rx + 18, 408, [("", 170, "start"), ("", 120, "start"), ("", 350, "start")],
                [["to. 26. nov", ("14:15", "b"), "Datalab A2"], ["ma. 30. nov", ("10:15", "b"), "Datalab A2"],
                 ["to. 3. des", ("14:15", "b"), "Datalab A2"], ["ma. 7. des", ("10:15", "b"), "Datalab A2"]], 37, head=False, size=18))
    # fordeling
    p.add(rute(rx, 590, rw, 398, "Fordeling: 60 spill à 4"))
    p.add(T(rx + 18, 648, "240 studenter fordelt tilfeldig. Hvert spill har én av hver Rolle.", 19))
    gx, gy = rx + 18, 662
    cw, ch = 53, 53
    for i in range(60):
        r, c = divmod(i, 12)
        x, y = gx + c * cw, gy + r * ch
        hi = i == 16
        p.add(plain(x, y, cw - 4, ch - 4, YEL if hi else WHITE, 2.2 if hi else 1.2, j=.4, over=.5))
        p.add(T(x + 4, y + 15, i + 1, 13, "hb" if hi else "h"))
        for k, role in enumerate(ROLES):
            p.add(mark(x + 7 + k * 11.5, y + 34, role, 4, 1.1))
    y = gy + 5 * ch + 8
    p.add(T(gx, y + 14, "Spill 17: Ida, Sara, Mikkel og Jonas.", 18))
    p.add(button(rx + rw - 348, y - 2, 130, 42, "Kjør på nytt", "sec", 18))
    p.add(button(rx + rw - 208, y - 2, 190, 42, "Bekreft fordeling", "yel", 14))
    # lagre
    p.add(ibox(32, 1004, 1376, 76, MAG, None, 3.2))
    p.add(T(56, 1050, "Alt er utfylt. Du kan lagre uten å endre noe.", 25, "hb", WHITE))
    p.add(ibox(1120, 1016, 270, 52, WHITE, None, 3, mis=(0, 0)))
    p.add(T(1255, 1050, "Lagre Klasseøkt", 18, "d", INK, "middle"))
    p.save()


# ---- 08 Redaksjonsveggen ------------------------------------------------------------------------------
def cover(x, y, w, h, gm):
    st = gm["status"]
    n = gm["spill"]
    near = st == "venter" and gm.get("ventet_timer", 0) >= 22
    o = []
    if near:
        o.append(ibox(x, y, w, h, MAG, None, 4, mis=(0, 0)))
        c = WHITE
    elif st == "venter":
        o.append(ibox(x, y, w, h, YEL, None, 3, mis=(0, 0)))
        c = INK
    elif st == "pauset":
        o.append(ibox(x, y, w, h, WHITE, "dc", 2.4, mis=(0, 0)))
        o.append(f'<rect x="{x+4}" y="{y+4}" width="{w-8}" height="{h-8}" fill="{WHITE}" opacity=".8"/>')
        c = INK
    elif st == "pågår":
        o.append(ibox(x, y, w, h, WHITE, None, 2.4, mis=(0, 0)))
        c = INK
    else:
        o.append(ibox(x, y, w, h, "#F1EBD8", None, 1.2, over=.8, mis=(0, 0), j=.5))
        c = SOFT
    o.append(T(x + 7, y + 25, n, 21, "d", INK if c == SOFT else c))
    tx = x + w - 7
    if st == "ferdig":
        o.append(ic_check(tx - 8, y + 16, .8, SOFT))
        o.append(T(x + 7, y + 48, "Ferdig", 15, "h", SOFT))
        o.append(T(x + 7, y + 67, nok(gm["kjedekost"], 0), 14, "h", SOFT))
    elif st == "pågår":
        o.append(path(f"M{tx-14} {y+10}L{tx-3} {y+17}L{tx-14} {y+24}Z", CYA, INK, 1.6))
        o.append(T(x + 7, y + 49, f"Uke {gm['uke']}", 18, "hb"))
        o.append(T(x + 7, y + 67, "Pågår", 14.5))
        if h >= 110 or not gm.get("ki_seter"):
            o.append(T(x + 7, y + 85, nok(gm["kjedekost"], 0), 14))
    elif st == "pauset":
        o.append(ic_pause(tx - 8, y + 16, 1))
        o.append(T(x + 7, y + 44, f"Uke {gm['uke']}", 15.5, "hb"))
        o.append(T(x + 7, y + 60, "Pause til", 14.5))
        o.append(T(x + 7, y + 75, "i kveld 19:00", 14.5))
    else:
        o.append(ic_hour(tx - 8, y + 16, 1, c) if not near else ic_clock(tx - 8, y + 16, 1.05, WHITE))
        o.append(T(x + 7, y + 44, f"{gm['navn']}, {gm['ventet_timer']} t", 16.5, "hb", c))
        o.append(T(x + 7, y + 60, gm["venter_paa"], 14.5, "h", c))
        if near and h < 110:
            o.append(plain(x + 6, y + 64, w - 12, 27, WHITE, 1.8))
            o.append(T(x + w / 2, y + 84, "KI om 1 t", 17, "hb", INK, "middle"))
        else:
            o.append(T(x + 7, y + 75, f"Uke {gm['uke']}", 14.5, "h", c))
        if near and h >= 110:
            o.append(plain(x + 6, y + h - 34, w - 12, 27, WHITE, 1.8))
            o.append(T(x + w / 2, y + h - 14, "KI om 1 t", 17, "hb", INK, "middle"))
    if gm.get("ki_seter"):
        o.append(g(f"translate({x+26:.1f} {y+h-8:.1f}) scale(.82)", ki_tag(0, 0, 1)))
        o.append(T(x + 42, y + h - 7, f"{gm['ki_seter']}" if st != "ferdig" else f"{gm['ki_seter']}", 15, "hb", INK if c == SOFT else c))
    return "".join(o)


def chip(x, y, label, on=False, flat=WHITE, icon=None):
    w = tw(label, 18, "hb") + 28 + (20 if icon else 0)
    o = plain(x, y, w, 36, YEL if on else flat, 2.6 if on else 1.8)
    tx = x + 12
    if icon:
        o += icon(x + 18, y + 18)
        tx += 18
    o += T(tx, y + 25, label, 18, "hb" if on else "h")
    return o, w


def oversikt():
    p = Page("08-laerer-oversikt.svg", "over", 1600, 1000, "Oversikt: redaksjonsveggen",
             "60 små forsider med status, hvem spillet venter på og hvor lenge, Pause og KI-seter. Nær overtakelse er uthevet. Trakt, Filtrering og Melding på samme skjerm.")
    p.add(topbar(1600, "Oversikt"))
    games = GAMES
    counts = {k: sum(1 for g_ in games if g_["status"] == k) for k in ("ferdig", "pågår", "pauset", "venter")}
    ki_games = sum(1 for g_ in games if g_.get("ki_seter"))
    p.add(T(32, 108, "Oversikt: class-of-1994", 28, "d"))
    p.add(T(494, 106, f"{counts['ferdig']} ferdig, {counts['pågår'] + counts['pauset']} pågår (herav {counts['pauset']} pauset), {counts['venter']} venter", 22, "hb"))
    p.add(T(1216, 104, "Demodata", 17, "hb", INK, "end"))
    # filter
    x = 32
    chips = [("Alle 60", True, None), (f"Venter {counts['venter']}", False, lambda a, b: ic_hour(a, b, .85)),
             (f"Pågår {counts['pågår']}", False, lambda a, b: path(f"M{a-6} {b-7}L{a+6} {b}L{a-6} {b+7}Z", CYA, INK, 1.6)),
             (f"Pauset {counts['pauset']}", False, lambda a, b: ic_pause(a, b, .85)),
             (f"Ferdig {counts['ferdig']}", False, lambda a, b: ic_check(a, b, .85)),
             (f"Med KI-sete {ki_games}", False, None)]
    p.add(T(x, 146, "Filtrering", 18, "hb"))
    x += 78
    for lab, on, ic in chips:
        s, w = chip(x, 122, lab, on, icon=ic)
        p.add(s)
        x += w + 8
    # veggen
    cols, rows = 10, 6
    wx, wy = 32, 170
    cw, ch = 118, 134
    # varselet: Spill 2 er nær overtakelse
    for i, gm in enumerate(games):
        r, c = divmod(i, cols)
        p.add(cover(wx + c * cw, wy + r * ch, cw - 6, ch - 7, gm))
    # høyre spalte
    rx, rw = 1228, 344
    n2 = next(g_ for g_ in games if g_["spill"] == 2)
    p.add(ibox(rx, 82, rw, 170, MAG, None, 4, mis=(2.5, 2.5)))
    p.add(ic_clock(rx + 24, 110, 1.3, WHITE))
    p.add(T(rx + 44, 118, f"Spill 2: KI overtar om 1 t", 22, "hb", WHITE))
    p.add(T(rx + 16, 148, f"{n2['navn']} ({n2['venter_paa']}) har latt gruppa", 19, "h", WHITE))
    p.add(T(rx + 16, 171, f"vente i {n2['ventet_timer']} t. Grensen er 24 t.", 19, "h", WHITE))
    p.add(button(rx + 14, 186, rw - 28, 52, "Send Melding til Noah", "sec", 21))
    # venter nå
    wait = sorted([g_ for g_ in games if g_["status"] == "venter"], key=lambda g_: -g_["ventet_timer"])
    p.add(T(rx, 286, "Venter lengst", 19, "d"))
    rows_ = [[(str(g_["spill"]), "b"), g_["navn"], g_["venter_paa"], (f"{g_['ventet_timer']} t", "b")] for g_ in wait]
    p.add(table(rx, 294, [("Spill", 56, "start"), ("Hvem", 80, "start"), ("Rolle", 130, "start"), ("Ventet", 78, "end")], rows_, 30))
    # trakt
    f = FX["funnel"]
    p.add(T(rx, 480, "Trakten, 240 studenter", 19, "d"))
    steps = [("Registrert", f["registrert"]), ("Klassespill ferdig", f["klassespill_ferdig"]), ("Debrief ferdig", f["debrief_ferdig"]),
             ("Quiz bestått", f["quiz_bestått"]), ("Replay ferdig", f["replay_ferdig"]), ("Test levert", f["test_levert"]), ("KI-vurdering klar", f["ki_vurdering_klar"])]
    y = 492
    for lab, v in steps:
        bw = (rw - 44) * v / 240
        p.add(T(rx, y + 16, lab, 17))
        p.add(T(rx + rw, y + 16, v, 18, "hb", INK, "end"))
        if v:
            p.add(f'<rect x="{rx}" y="{y+21}" width="{bw:.1f}" height="11" fill="{CYA}"/>')
            p.add(f'<rect x="{rx}" y="{y+21}" width="{bw:.1f}" height="11" fill="none" stroke="{INK}" stroke-width="1.8"/>')
        else:
            p.add(f'<path d="M{rx} {y+27}h{rw-44}" stroke="{INK}" stroke-width="1.4" stroke-dasharray="3 5"/>')
        y += 40
    # handlinger
    p.add(button(rx, 782, rw, 48, "Send Melding til alle som venter", "yel", 14))
    p.add(button(rx, 838, rw, 44, "Fyll fraværende seter med KI", "sec", 19))
    # lesenøkkel
    p.add(T(rx, 912, "Slik leser du forsidene", 18, "hb"))
    x = rx
    for lab, flat in [("Venter", YEL), ("Nær KI", MAG), ("Ferdig", "#F1EBD8")]:
        p.add(plain(x, 922, 18, 18, flat, 1.6))
        p.add(T(x + 24, 937, lab, 16))
        x += 104
    p.add(ki_tag(rx + 22, 972, .85))
    p.add(T(rx + 42, 973, "= antall KI-seter", 16.5))
    p.save()
