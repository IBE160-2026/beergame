"""Seks figurer som viser alternativene i de seks UX-valgene fra klarhetssjekken 2026-11-12
(.docs/planning-artifacts/implementation-readiness.md, funn 1, 2, 6, 8, 11 og 17).

Kjør fra denne mappa: uv run --no-project python build.py
Etterpå: uv run --no-project python ../concepts-r3/_shared/render.py .

Bruker byggeklossene i ../valgt-konsept/vlib.py, så farger og skrift er de samme som i mockupene.
Ny tekst i figurene er utkast. Ordlyden bestemmes etter valget."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "valgt-konsept"))

import vlib  # noqa: E402
from vlib import (BASE, BLUE, HAIR, HAIR2, INK, INK2, INK3, PAPER, RED, TINT, Doc, net_cell,  # noqa: E402
                  text_w)

vlib.HERE = HERE

M = 40
FOOT = "Ny tekst i figurene er utkast. Ordlyden bestemmes etter valget."


def cols(W, n=3, gap=35):
    cw = (W - 2 * M - gap * (n - 1)) / n
    return [M + i * (cw + gap) for i in range(n)], cw


def head(d, title, today):
    d.t(M, 50, title, 26, 700)
    d.t(M, 82, "I dag", 15, 600)
    return d.para(M + 52, 82, today, d.W - 2 * M - 52, 15, 21, 400, INK2) + 14


def col_head(d, x, y, cw, letter, title, desc):
    d.t(x, y, letter, 20, 700)
    d.t(x + 26, y, title, 20, 600)
    return d.para(x, y + 26, desc, cw, 14, 20, 400, INK2) + 8


def col_heads(d, xs, y, cw, opts):
    return max(col_head(d, x, y, cw, o[0], o[1], o[2]) for x, o in zip(xs, opts))


def follows(d, x, y, cw, text):
    d.line(x, y - 18, x + cw, y - 18, HAIR, 1)
    d.t(x, y, "Følger av valget", 13, 600)
    return d.para(x, y + 19, text, cw, 13, 18, 400, INK2)


def foot(d):
    d.t(M, d.H - 22, FOOT, 13, 400, INK3)


def link(d, x, y, s, size=13, a="start"):
    d.t(x, y, s, size, 600, BLUE, a, 'text-decoration="underline"')


def dashed(d, x, y, w, h):
    d.rect(x, y, w, h, "none", INK, 1.2, 4, 'stroke-dasharray="5 4"')


def stop(d, x, y, n):
    d.circle(x, y, 9, INK)
    d.t(x, y + 4.2, str(n), 12, 700, PAPER, "middle")


def seat_rows(d, x, y, w, rows, rh=22):
    for filled, role, name, status in rows:
        if filled:
            d.circle(x + 5, y - 4, 4, INK)
        else:
            d.circle(x + 5, y - 4, 3.2, PAPER, INK, 1.6)
        d.t(x + 18, y, role, 13, 600)
        d.t(x + 96, y, name, 13, 400, INK2)
        d.t(x + w, y, status, 12, 400, INK2, "end")
        y += rh
    return y


# ---------------------------------------------------------------- 1 Matrisevegg

WALL = [(2, 19, "Noah, Grossist, 23 t"), (30, 24, "Ida, Detaljist, 18 t"), (10, 24, "Oskar, Grossist, 16 t"),
        (28, 22, "Mikkel, Distributør, 14 t"), (46, 24, ""), (24, 24, "")]
NCOL = 24


def wall_val(r, wk):
    trough = 12 + (r * 3) % 5
    depth = 16 + (r * 7) % 22
    if wk <= 5:
        return 12
    if wk <= trough:
        return round(12 - (12 + depth) * (wk - 5) / (trough - 5))
    return min(34, -depth + (wk - trough) * 7)


def wall(d, x, y, cw, mode):
    """mode: 'rows' (A), 'hidden' (B), 'cells' (C). Returnerer y under veggen."""
    # Visningsbryter
    d.t(x, y + 17, "Visning", 13, 400, INK3)
    bx = x + 58
    d.rect(bx, y, 190, 28, PAPER, HAIR2, 1, 5)
    d.rect(bx + 1, y + 1, 72, 26, INK, None, 0, 4)
    d.t(bx + 37, y + 18.5, "Vegg", 13, 600, PAPER, "middle")
    d.t(bx + 131, y + 18.5, "Vis som tabell", 13, 600, INK, "middle")
    if mode == "hidden":
        d.rect(bx + 74, y - 3, 119, 34, "none", INK, 2, 6)
        stop(d, bx + 206, y + 14, 1)
    y += 48
    lab, cwid, rh = 36, 9.8, 17
    gx = x + lab
    d.t(x, y, "Spill", 12, 600)
    for wk in (1, 5, 10, 15, 20):
        d.t(gx + (wk - 0.5) * cwid, y, str(wk), 11, 400, INK3, "middle")
    y += 8
    top = y
    if mode == "hidden":
        d.add('<g opacity="0.38">')
    for r, (spill, now, who) in enumerate(WALL):
        ry = y + r * rh
        if r == 0:
            d.rect(x - 4, ry, cw + 8, rh - 2, "#F6E4E2")
        d.t(x, ry + 12, str(spill), 12, 400)
        for wk in range(1, min(now, NCOL) + 1):
            fill, _ = net_cell(wall_val(r, wk))
            d.rect(gx + (wk - 1) * cwid, ry + 1, cwid - 1, rh - 4, fill)
        tx = gx + NCOL * cwid + 10
        if who:
            d.t(tx, ry + 12, who, 12, 400)
            link(d, x + cw, ry + 12, "Melding", 12, "end")
    if mode == "hidden":
        d.end()
    bottom = y + len(WALL) * rh
    if mode == "rows":
        d.rect(x - 6, top - 2, cw + 12, rh + 2, "none", INK, 2, 3)
        stop(d, x - 20, top + 8, 1)
    elif mode == "hidden":
        d.rect(gx - 2, top - 2, NCOL * cwid + 4, len(WALL) * rh + 2, "none", INK3, 1, 0, 'stroke-dasharray="5 4"')
        d.rect(gx + NCOL * cwid / 2 - 112, top + len(WALL) * rh / 2 - 14, 224, 26, PAPER)
        d.t(gx + NCOL * cwid / 2, top + len(WALL) * rh / 2 + 4, "Bilde. Ingen fokus, ingen lenker.", 14, 600, INK,
            "middle")
    else:
        cx, cy = gx + 13 * cwid, top
        d.rect(cx - 2, cy - 1, cwid + 3, rh, "none", INK, 2, 2)
        for dx, dy, ch in ((-16, 12, "←"), (cwid + 8, 12, "→"), (cwid / 2 - 4, 34, "↓")):
            d.t(cx + dx, cy + dy, ch, 13, 700)
    return bottom + 18


def reader(d, x, y, cw, said, keys):
    lines = vlib.wrap(said, cw - 28, 14)
    h = 36 + 20 * len(lines)
    d.rect(x, y, cw, h, TINT, None, 0, 4)
    d.t(x + 14, y + 21, "Skjermleser leser", 12, 600, INK2)
    yy = y + 42
    for ln in lines:
        d.t(x + 14, yy, ln, 14, 400)
        yy += 20
    yy = y + h + 24
    d.t(x, yy, "Tastatur", 13, 600)
    return d.para(x + 66, yy, keys, cw - 66, 13, 18, 400, INK2)


def fig1():
    d = Doc("v1-matrisevegg", 1620, 640, "Valg 1: Matriseveggen for tastatur og skjermleser",
            "Tre alternativer for hva som kan nås og leses i Matriseveggen.")
    y = head(d, "Valg 1  Matriseveggen: hva får den som bruker tastatur eller skjermleser?",
             "EXPERIENCE.md sier at veggen er skjult for skjermleser, med «Vis som tabell» som alternativ. "
             "Samtidig skal hver rad kunne få fokus, åpne Spillinnsikt og ha lenka «Melding». Begge deler kan ikke gjelde.")
    xs, cw = cols(d.W)
    opts = [
        ("A", "Radene leses, cellene skjules",
         "Hver rad er ett stopp og leses som én linje. Bare de fargede cellene er skjult.", "rows",
         "Spill 2. Venter på Noah, Grossist, 23 timer. Uke 19. Kjedekost 1 058 kr. Lenke: Melding.",
         "Tab går rad for rad og til «Melding». Enter åpner Spillinnsikt. Tallene leses i «Vis som tabell».",
         "Story 7.3 endres: bare cellene skjules. Story 7.2, 7.7 og 7.11 står som de er."),
        ("B", "Hele veggen er et bilde",
         "Veggen har ingen stopp. Alt som kan gjøres med et spill, gjøres fra tabellen.", "hidden",
         "Alle spill, bilde. Tallene og handlingene står i Vis som tabell.",
         "Ingen stopp i veggen. «Melding» og Spillinnsikt nås fra tabellen, også for den som ser veggen og bruker "
         "tastatur.",
         "Story 7.2, 7.7 og 7.11 endres: fokus, Enter og «Melding» flyttes til tabellen. Klikk i veggen finnes bare "
         "for mus."),
        ("C", "Hele veggen kan leses",
         "Veggen er en tabell for skjermleseren. Hver celle kan nås og leses der den står.", "cells",
         "Spill 2, Uke 14: Netto lager −13.",
         "Piltastene går celle for celle: opptil 60 rader × 36 Uker = 2 160 celler. Lenkene står i hver rad.",
         "Story 7.3 endres: veggen skjules ikke. Veggen og «Vis som tabell» blir to lesbare utgaver av de samme "
         "tallene."),
    ]
    yb = 0
    y0 = col_heads(d, xs, y, cw, opts)
    for x, (let, title, desc, mode, said, keys, fol) in zip(xs, opts):
        yy = wall(d, x + 24, y0 + 8, cw - 28, mode)
        yy = reader(d, x, yy, cw, said, keys)
        yb = max(yb, yy)
    for x, o in zip(xs, opts):
        follows(d, x, yb + 30, cw, o[6])
    foot(d)
    d.save()


# ---------------------------------------------------------------- 2 Pause

SEATS_NOT_ORDERED = [(True, "Detaljist", "Ida", "har bestilt"), (False, "Grossist", "Sara", "venter (deg)"),
                     (True, "Distributør", "Mikkel", "har bestilt"), (False, "Fabrikk", "Jonas", "venter, 3 min")]


def phone_top(d, x, y, w, h, caption):
    d.t(x + w / 2, y - 12, caption, 13, 600, INK, "middle")
    d.rect(x, y, w, h, PAPER, HAIR2, 1.2, 26)
    p = 16
    d.t(x + p, y + 40, "Uke 15", 22, 700)
    d.t(x + p, y + 58, "Grossist, Spill 17", 12, 400, INK3)
    d.t(x + w - p, y + 30, "Totalkostnad", 11, 400, INK3, "end")
    d.t(x + w - p, y + 48, "142,00 kr", 14, 600, INK, "end")
    d.rect(x + p, y + 72, w - 2 * p, 96, TINT, None, 0, 4)
    d.t(x + w / 2, y + 116, "Kjedebånd og Graf over tabell", 12, 400, INK3, "middle")
    d.t(x + w / 2, y + 133, "som i dag", 12, 400, INK3, "middle")
    return x + p, y + 190, w - 2 * p


def order_field(d, x, y, w, extra_link=None):
    d.t(x, y, "Din ordre for Uke 15", 13, 600)
    if extra_link:
        link(d, x + w, y, extra_link, 13, "end")
    d.rect(x, y + 10, w, 38, PAPER, HAIR2, 1, 5)
    d.line(x + 36, y + 10, x + 36, y + 48, HAIR2)
    d.line(x + w - 36, y + 10, x + w - 36, y + 48, HAIR2)
    d.t(x + 18, y + 35, "−", 18, 400, INK, "middle")
    d.t(x + w - 18, y + 35, "+", 18, 400, INK, "middle")
    d.t(x + w / 2, y + 34, "Antall enheter", 13, 400, INK3, "middle")
    d.rect(x, y + 60, w, 36, PAPER, HAIR2, 1, 5)
    d.t(x + w / 2, y + 83, "Bekreft ordre", 14, 600, INK3, "middle")
    return y + 120


def fig2():
    d = Doc("v2-pause", 1800, 860, "Valg 2: Pause før Studenten har bestilt",
            "Tre alternativer for hvor pauselinja og «Ta pause» står før Studenten har bestilt.")
    y = head(d, "Valg 2  Pause: hvor står pauselinja og «Ta pause» før Studenten har bestilt?",
             "Pauselinja står over Setestatus og «Ta pause» under. På spillskjermen vises Setestatus først når Studenten "
             "har bekreftet en ordre. Sara, som ikke har bestilt denne Uka, har derfor ikke noe sted for dem. "
             "Etter at hun har bestilt, er alle tre alternativene like og som i dag. Stiplet ramme viser det som plasseres.")
    xs, cw = cols(d.W)
    pw, ph, gap = 256, 470, 30
    opts = [
        ("A", "Setestatus vises hele Uka",
         "Setestatus står på spillskjermen både før og etter ordren. Pauselinja og «Ta pause» står ved den, som i dag.",
         "Story 6.14 endres: Setestatus vises alltid. Skjermen blir lengre før ordren, og på telefon kan pauselinja "
         "havne under det som vises uten å rulle."),
        ("B", "Over Ordrefeltet",
         "Før ordren står pauselinja i en egen plass over Ordrefeltet, og «Ta pause» er en Lenke der.",
         "Plassen Story 6.14 setter av over Ordrefeltet blir brukt. Story 8.6 og 8.7 får to plasseringer: én før og "
         "én etter ordren."),
        ("C", "Bare linja. Pause fra Hjem",
         "Før ordren vises bare pauselinja over Ordrefeltet. «Ta pause» står på Hjem, og her først etter ordren.",
         "Som B for pauselinja. Den som står midt i en ordre må til Hjem eller bestille først for å ta pause."),
    ]
    yb = 0
    y0 = col_heads(d, xs, y, cw, opts)
    for i, (x, (let, title, desc, fol)) in enumerate(zip(xs, opts)):
        yy = y0 + 30
        x1, x2 = x + 4, x + 4 + pw + gap
        # Før pause
        cx, cy, w = phone_top(d, x1, yy, pw, ph, "Ingen pause. Sara har ikke bestilt.")
        if let == "A":
            cy = order_field(d, cx, cy, w)
            e = seat_rows(d, cx, cy, w, SEATS_NOT_ORDERED)
            link(d, cx, e + 6, "Ta pause")
            dashed(d, cx - 8, cy - 18, w + 16, e - cy + 34)
        elif let == "B":
            link(d, cx, cy, "Ta pause")
            dashed(d, cx - 8, cy - 16, text_w("Ta pause", 13) + 22, 24)
            cy = order_field(d, cx, cy + 30, w)
            d.t(cx, cy, "Venter på: Jonas (3 min) og deg.", 12, 400, INK3)
        else:
            cy = order_field(d, cx, cy, w)
            d.t(cx, cy, "Venter på: Jonas (3 min) og deg.", 12, 400, INK3)
            d.para(cx, cy + 40, "«Ta pause» finnes ikke her. Den står på Hjem.", w, 12, 17, 400, INK3)
        # Under pause
        cx, cy, w = phone_top(d, x2, yy, pw, ph, "Pause satt av Ida. Sara har ikke bestilt.")
        if let == "A":
            cy = order_field(d, cx, cy, w)
            d.t(cx, cy, "Pause, satt av Ida.", 13, 600)
            e = seat_rows(d, cx, cy + 26, w, SEATS_NOT_ORDERED)
            dashed(d, cx - 8, cy - 18, w + 16, e - cy + 8)
        else:
            d.t(cx, cy, "Pause, satt av Ida.", 13, 600)
            dashed(d, cx - 8, cy - 16, w + 16, 24)
            cy = order_field(d, cx, cy + 30, w)
            d.t(cx, cy, "Venter på: Jonas (3 min) og deg.", 12, 400, INK3)
        yb = max(yb, yy + ph)
    for x, o in zip(xs, opts):
        follows(d, x, yb + 46, cw, o[3])
    foot(d)
    d.save()


# ---------------------------------------------------------------- 3 Beskjed når Uka åpner

SEATS_ORDERED = [(True, "Detaljist", "Ida", "har bestilt"), (True, "Grossist", "Sara", "har bestilt"),
                 (True, "Distributør", "Mikkel", "har bestilt"), (False, "Fabrikk", "Jonas", "venter, 3 min")]


def mail_strip(d, x, y, cw, weeks, label, note):
    d.t(x, y, "Beskjeder til Sara i ett spill på 36 Uker", 13, 600)
    x0, w = x + 4, cw - 8
    yy = y + 34
    d.line(x0, yy, x0 + w, yy, HAIR2, 1)
    for wk in (1, 12, 24, 36):
        xx = x0 + (wk - 1) / 35 * w
        d.line(xx, yy, xx, yy + 5, HAIR2, 1)
        d.t(xx, yy + 19, f"Uke {wk}", 12, 400, INK3, "start" if wk == 1 else ("end" if wk == 36 else "middle"))
    for wk in weeks:
        xx = x0 + (wk - 1) / 35 * w
        d.rect(xx - 3.5, yy - 16, 7, 12, INK)
    d.t(x, yy + 46, label, 14, 600)
    return d.para(x, yy + 66, note, cw, 13, 18, 400, INK2)


def fig3():
    d = Doc("v3-ukebeskjed", 1620, 700, "Valg 3: Linja om beskjed når neste Uke åpner",
            "Tre alternativer for hva skjermen lover etter at ordren er sendt.")
    y = head(d, "Valg 3  Etter ordren: hva lover linja «Du får beskjed når Uke 12 åpner.»?",
             "Linja står på skjermen etter at ordren er sendt. Ingen slik beskjed finnes. FR-27 sender bare e-post når "
             "spillet har ventet på Studenten en stund, samlet i én e-post per dag og aldri om natten.")
    xs, cw = cols(d.W)
    waits = [9, 17, 28]
    opts = [
        ("A", "Linja fjernes", "Skjermen sier at ordren er sendt og hvem spillet venter på. Ikke noe mer.",
         None, waits, "3 e-poster",
         "Bare når spillet har ventet på Sara, som i dag (FR-27).",
         "Én linje tas ut av EXPERIENCE.md. Ingen story endres."),
        ("B", "Linja sier det som faktisk skjer",
         "Linja byttes med en som er sann: skjermen går videre av seg selv, og e-post kommer bare når spillet venter.",
         ["Skjermen går videre når alle har bestilt.", "Du får e-post hvis spillet venter på deg."], waits,
         "3 e-poster", "Bare når spillet har ventet på Sara, som i dag (FR-27).",
         "Ny tekst i EXPERIENCE.md og i Story 6.12 eller 6.14. Ingen ny funksjon."),
        ("C", "Beskjed for hver Uke",
         "Løftet beholdes, og systemet sender en beskjed hver gang en ny Uke åpner.",
         ["Du får beskjed når Uke 12 åpner."], list(range(2, 37)), "35 beskjeder",
         "Én per Uke. I en Labtime kommer alle i løpet av én økt. Bryter regelen om én e-post per dag.",
         "Nytt krav: FR-27 i PRD og AD-9 i arkitekturen endres, og beskjeden trenger en ny story."),
    ]
    yb = 0
    y0 = col_heads(d, xs, y, cw, opts)
    for x, (let, title, desc, lines, weeks, label, note, fol) in zip(xs, opts):
        yy = y0 + 6
        h = 222
        d.rect(x, yy, cw, h, PAPER, HAIR2, 1.2, 12)
        px, pw = x + 20, cw - 40
        d.t(px, yy + 34, "Ordren på 24 er sendt. Venter på Jonas.", 15, 600)
        e = seat_rows(d, px, yy + 66, pw, SEATS_ORDERED)
        if lines:
            for k, ln in enumerate(lines):
                d.t(px, e + 12 + 19 * k, ln, 13, 400, INK2)
            dashed(d, px - 8, e - 6, pw + 16, 19 * len(lines) + 10)
        else:
            dashed(d, px - 8, e - 6, pw + 16, 29)
            d.t(px, e + 12, "(ingen linje her)", 13, 400, INK3)
        yb = max(yb, mail_strip(d, x, yy + h + 40, cw, weeks, label, note))
    for x, o in zip(xs, opts):
        follows(d, x, yb + 30, cw, o[7])
    foot(d)
    d.save()


# ---------------------------------------------------------------- 4 Primærknapp på Klasseøkt

def small_button(d, x, y, label, primary, size=12):
    w = text_w(label, size) + 26
    d.rect(x, y, w, 28, INK if primary else PAPER, None if primary else HAIR2, 1, 5)
    d.t(x + w / 2, y + 18.5, label, size, 600, PAPER if primary else INK, "middle")
    return w


def grey_lines(d, x, y, w, n, gap=15):
    for i in range(n):
        d.rect(x, y + i * gap, w * (0.5 + 0.1 * ((i * 3) % 4)), 6, HAIR)
        d.rect(x + w - 40, y + i * gap, 40, 6, HAIR)


def alloc_strip(d, x, y, w):
    cw = w / 60
    for r in range(4):
        for c in range(60):
            d.rect(x + c * cw, y + r * 11, cw - 1.2, 9, BASE)
    d.rect(x + 16 * cw - 1.5, y - 2, cw + 1.8, 46, "none", INK, 1.2)


def thumb(d, x, y, w, h, title, kind, save_primary=True, show_save=True, note=None):
    """kind: 'link' | 'open' | 'confirmed' | 'page'."""
    d.rect(x, y, w, h, PAPER, HAIR2, 1.2, 8)
    d.t(x + 18, y + 30, title, 16, 700)
    if kind == "page":
        link(d, x + w - 18, y + 30, "Tilbake til Klasseøkt", 12, "end")
        rx, rw = x + 18, w - 36
        d.t(rx, y + 60, "240 studenter fordeles tilfeldig. Tomme seter får KI-spiller.", 12, 400, INK2)
        alloc_strip(d, rx, y + 76, rw)
        bw = small_button(d, rx, y + 136, "Kjør fordeling på nytt", False)
        bw2 = small_button(d, rx + bw + 10, y + 136, "Bekreft fordeling", True)
        d.t(rx + bw + bw2 + 22, y + 154, "Ingen får beskjed før du bekrefter.", 12, 400, INK2)
        return
    lw = 150
    d.t(x + 18, y + 58, "Spillinnstillinger", 12, 600)
    grey_lines(d, x + 18, y + 70, lw, 7)
    rx = x + 18 + lw + 28
    rw = w - 36 - lw - 28
    d.t(rx, y + 58, "Fordeling: 60 Klassespill à 4", 12, 600)
    if kind == "link":
        d.t(rx, y + 80, "Ikke bekreftet.", 12, 400, INK2)
        link(d, rx, y + 102, "Se og bekreft fordelingen", 12)
    elif kind == "open":
        alloc_strip(d, rx, y + 70, rw)
        bw = small_button(d, rx, y + 124, "Kjør på nytt", False)
        small_button(d, rx + bw + 8, y + 124, "Bekreft fordeling", True)
    elif kind == "confirmed":
        d.t(rx, y + 80, "Fordelingen er bekreftet.", 12, 400, INK2)
        link(d, rx, y + 102, "Vis fordelingen", 12)
    if show_save:
        lab = "Lagre Klasseøkt"
        bw = text_w(lab, 12) + 26
        small_button(d, x + w - 18 - bw, y + h - 44, lab, save_primary)
    if note:
        d.t(x + 18, y + h - 26, note, 12, 400, INK3)


def count(d, x, y, n):
    d.t(x, y, f"Primærknapper på skjermen: {n}", 13, 600, INK if n == 1 else RED)


def fig4():
    d = Doc("v4-primaerknapp", 1620, 950, "Valg 4: Primærknappen på Klasseøkt",
            "Tre alternativer for hvordan «Bekreft fordeling» og «Lagre Klasseøkt» deler skjermen.")
    y = head(d, "Valg 4  Klasseøkt: hvilken knapp er primærknappen?",
             "Regelen er én primærknapp per skjerm, og en sekundærknapp kan aldri gjøre noe som ikke kan angres. "
             "På Klasseøkt er både «Lagre Klasseøkt» og «Bekreft fordeling» tegnet og beskrevet som primærknapp. "
             "«Bekreft fordeling» varsler studentene.")
    xs, cw = cols(d.W)
    th = 222
    opts = [
        ("A", "Fordelingen får sin egen side",
         "Klasseøkt lenker til en side for fordelingen. Hver side har sin ene primærknapp.",
         "Ny side i informasjonsarkitekturen. Story 5.8 til 5.10 bygges der, og reisen i EXPERIENCE.md får ett "
         "sidebytte før «Bekreft fordeling»."),
        ("B", "Panel på stedet",
         "Forhåndsvisningen åpnes på Klasseøkt. Mens den er åpen er «Bekreft fordeling» primærknappen, og "
         "«Lagre Klasseøkt» vises som sekundær.",
         "Samme regel som Varselbånd og Spillstyring bruker. Story 5.1 og 5.9 får regelen for hvilken knapp som er "
         "primær når."),
        ("C", "To primærknapper på denne skjermen",
         "Klasseøkt blir et navngitt unntak. Begge knappene er primære, hver med følgen skrevet ved siden av.",
         "Regelen om én primærknapp får et unntak i EXPERIENCE.md. Mockup 03 og Story 5.1 og 5.9 står som de er."),
    ]
    yb = 0
    y0 = col_heads(d, xs, y, cw, opts)
    for x, (let, title, desc, fol) in zip(xs, opts):
        yy = y0 + 6
        if let == "A":
            d.t(x, yy + 12, "Klasseøkt", 13, 600, INK2)
            thumb(d, x, yy + 22, cw, th, "Klasseøkt for class-of-1994", "link")
            count(d, x, yy + th + 46, 1)
            y2 = yy + th + 78
            d.t(x, y2 + 12, "Siden «Fordeling»", 13, 600, INK2)
            thumb(d, x, y2 + 22, cw, th, "Fordeling: 60 Klassespill à 4", "page")
            count(d, x, y2 + th + 46, 1)
            yb = max(yb, y2 + th + 46)
        elif let == "B":
            d.t(x, yy + 12, "Forhåndsvisningen er åpen", 13, 600, INK2)
            thumb(d, x, yy + 22, cw, th, "Klasseøkt for class-of-1994", "open", save_primary=False)
            count(d, x, yy + th + 46, 1)
            y2 = yy + th + 78
            d.t(x, y2 + 12, "Etter «Bekreft fordeling»", 13, 600, INK2)
            thumb(d, x, y2 + 22, cw, th, "Klasseøkt for class-of-1994", "confirmed")
            count(d, x, y2 + th + 46, 1)
        else:
            d.t(x, yy + 12, "Som mockup 03 i dag", 13, 600, INK2)
            thumb(d, x, yy + 22, cw, th, "Klasseøkt for class-of-1994", "open")
            count(d, x, yy + th + 46, 2)
    for x, o in zip(xs, opts):
        follows(d, x, yb + 50, cw, o[3])
    foot(d)
    d.save()


# ---------------------------------------------------------------- 5 Kostnadsaksen

COST = {7: (3, 0), 8: (1, 2), 9: (0, 9), 10: (0, 13), 11: (0, 20), 12: (0, 34), 13: (0, 41), 14: (0, 52),
        15: (0, 62), 16: (0, 58), 17: (0, 44), 18: (0, 30)}
WEEKS = list(range(7, 19))


def cost_chart(d, x, y, cw, now, top, clip=False, note=None):
    lab, h = 74, 92
    x0 = x + lab
    colw = (cw - lab) / len(WEEKS)
    base = y + h
    d.t(x, y - 12, f"Uke {now}", 14, 700)
    hi = max(sum(COST[w]) for w in WEEKS if w <= now)
    d.t(x + 56, y - 12, f"Høyeste Uke så langt: {hi} kr", 13, 400, INK2)
    # flaten til høyre for nå
    nx = x0 + (now - WEEKS[0] + 1) * colw
    d.rect(nx, y - 4, x0 + len(WEEKS) * colw - nx, h + 52, TINT)
    d.line(x0 - 6, y, x0 + len(WEEKS) * colw, y, HAIR, 1)
    d.t(x0 - 10, y + 4, f"{top} kr", 12, 400, INK3, "end")
    d.t(x, base - 2, "Kost per uke", 12, 600)
    for i, wk in enumerate(WEEKS):
        if wk > now:
            continue
        lager, rest = COST[wk]
        bx, bw = x0 + i * colw + 4, colw - 8
        tot = lager + rest
        shown = min(tot, top) if clip else tot
        u = h / top
        if lager:
            d.rect(bx, base - lager * u, bw, lager * u, BLUE)
        rs = shown - lager
        if rs > 0:
            d.rect(bx, base - shown * u, bw, rs * u - (1.5 if lager else 0), RED)
        if clip and tot > top:
            d.path(f"M{bx - 2:.1f},{y + 9:.1f} L{bx + bw + 2:.1f},{y + 3:.1f}", "none", PAPER, 3)
            d.t(bx + bw / 2, y - 6, str(tot), 12, 700, RED, "middle")
    d.line(x0 - 6, base, x0 + len(WEEKS) * colw, base, HAIR2, 1)
    d.line(nx, y - 4, nx, base + 48, INK, 1.2)
    # tabellrader
    for row, (name, fn) in enumerate((("Uke", lambda w: str(w)), ("Kost, kr", lambda w: str(sum(COST[w]))))):
        ry = base + 20 + row * 20
        d.t(x, ry, name, 12, 400, INK2)
        for i, wk in enumerate(WEEKS):
            if row == 1 and wk > now:
                continue
            bold = wk == now
            d.t(x0 + (i + 0.5) * colw, ry, fn(wk), 12, 700 if bold else 400, INK if (bold or row) else INK3, "middle")
    if note:
        d.t(x0 + 4, y + 16, note, 12, 600, INK2)
    return base + 52


def fig5():
    d = Doc("v5-kostakse", 1620, 800, "Valg 5: Aksen for Kost per uke når en Uke koster mer enn 40 kr",
            "Tre alternativer for hva aksen gjør over 40 kr.")
    y = head(d, "Valg 5  Kost per uke: hva gjør aksen når en Uke koster mer enn 40 kr?",
             "DESIGN.md gir aksen et fast maksimum, merket med ett aksemerke, «40 kr». En restordre over 40 enheter "
             "koster mer enn det, og verken DESIGN.md eller Story 6.7 sier hva som skjer da. Tabellen under grafen "
             "viser alltid det riktige tallet.")
    xs, cw = cols(d.W)
    opts = [
        ("A", "Fast 40 kr, stolpen kappes",
         "Aksen står. En stolpe over 40 kr kappes øverst med et bruddmerke, og tallet står over.",
         dict(top=40, clip=True), dict(top=40, clip=True),
         "Høyden på en stolpe betyr det samme i alle Uker og alle spill. Over 40 kr bærer tallet forskjellen, "
         "ikke høyden."),
        ("B", "Aksen dobles når det trengs",
         "Aksen går fra 40 til 80 kr første gang en Uke går over, og videre til 160 kr.",
         dict(top=40), dict(top=80, note="Aksen byttet til 80 kr i Uke 13"),
         "Hele stolpen vises alltid. Høydene skifter betydning når aksen bytter: de samme Ukene ser lavere ut enn "
         "de gjorde."),
        ("C", "Høyere fast maksimum",
         "Aksen får ett høyere tak fra første Uke, her 120 kr, og bytter aldri.",
         dict(top=120), dict(top=120),
         "Ingen kapping og ingen bytte i vanlige spill. Vanlige Uker blir lave stolper, og et dårlig spill kan "
         "fortsatt gå over taket."),
    ]
    yb = 0
    y0 = col_heads(d, xs, y, cw, opts)
    for x, (let, title, desc, k12, k15, fol) in zip(xs, opts):
        yy = y0 + 34
        yy = cost_chart(d, x, yy, cw, 12, **k12) + 48
        yy = cost_chart(d, x, yy, cw, 15, **k15)
        yb = max(yb, yy)
    for x, o in zip(xs, opts):
        follows(d, x, yb + 44, cw, o[5])
    d.t(M, d.H - 44, "Gjelder DESIGN.md → Graf over tabell og Story 6.7. Røde stolper er restordrekost, blå er lagerkost.",
        13, 400, INK3)
    foot(d)
    d.save()


# ---------------------------------------------------------------- 6 Tidsbegrenset test

def test_card(d, x, y, cw, h, right=None, sub=None, body=None, boxed=False):
    d.rect(x, y, cw, h, PAPER, HAIR2, 1.2, 10)
    d.t(x + 20, y + 34, "Individuell test", 17, 700)
    d.t(x + 20, y + 54, "Spørsmål 4 av 12 · Lagret 21:14", 12, 400, INK3)
    if right:
        w = text_w(right, 15) + 24
        d.rect(x + cw - 20 - w, y + 16, w, 32, PAPER, INK if boxed else HAIR2, 1.2, 5)
        d.t(x + cw - 20 - w / 2, y + 37, right, 15, 600, INK, "middle")
    yy = y + 82
    if sub:
        d.t(x + 20, yy, sub, 14, 600)
        yy += 24
    d.rect(x + 20, yy, cw - 40, 8, HAIR)
    d.rect(x + 20, yy + 16, (cw - 40) * 0.7, 8, HAIR)
    if body:
        d.para(x + 20, y + h - 22, body, cw - 40, 12, 17, 400, INK3)


def states(d, x, y, cw, rows):
    for when, what in rows:
        d.t(x, y, when, 13, 600)
        y = d.para(x + 96, y, what, cw - 96, 13, 18, 400, INK2) + 6
    return y


def fig6():
    d = Doc("v6-tidsbegrenset-test", 1620, 690, "Valg 6: Tidsbegrenset test i én økt",
            "Tre alternativer for hvordan en test med tidsgrense vises, eller om den venter til etter v1.")
    y = head(d, "Valg 6  Individuell test i én økt med tidsgrense: hvordan vises tiden?",
             "FR-51 lar Faglærer kreve én økt med tidsgrense, og Story 11.12 bygger det. EXPERIENCE.md sier at "
             "«I rommet» er den eneste tidsbegrensede økta i v1, og har verken tilstander eller tekst for en test "
             "der klokka går. Tilrettelegging nevner bare ventetid før KI tar over.")
    xs, cw = cols(d.W)
    opts = [
        ("A", "Synlig tid igjen",
         "Tiden som er igjen står øverst på testen hele tiden.",
         dict(right="Tid igjen 38 min", boxed=True),
         [("Underveis", "«Tid igjen 38 min» øverst, oppdatert uten at fokus flyttes."),
          ("5 min igjen", "Leses opp én gang: «5 minutter igjen. Svarene dine er lagret.»"),
          ("Tiden er ute", "«Tiden er ute. Testen er levert.»"),
          ("Tilrettelegging", "Faktoren gjelder tidsgrensen: 60 min blir 90 min ved 1,5.")],
         "EXPERIENCE.md får tilstander og tekst for klokka, og Tilrettelegging nevner testen. Story 11.12 og 8.9 "
         "står som de er."),
        ("B", "Sluttid i tekst, ingen nedtelling",
         "Testen sier når den lukkes. Ingenting teller ned på skjermen.",
         dict(sub="Testen lukkes kl. 21:40."),
         [("Underveis", "Linja «Testen lukkes kl. 21:40.» står stille under tittelen."),
          ("5 min igjen", "Leses opp én gang: «Testen lukkes om 5 minutter. Svarene dine er lagret.»"),
          ("Tiden er ute", "«Tiden er ute. Testen er levert.»"),
          ("Tilrettelegging", "Faktoren flytter sluttiden: kl. 21:40 blir kl. 22:10 ved 1,5.")],
         "Som A i EXPERIENCE.md, men uten et tall som teller ned. Studenten regner selv ut hvor lang tid som er igjen."),
        ("C", "Venter til etter v1",
         "Testen har ingen tidsgrense i v1. Studenten kan lukke den og komme tilbake fram til Testfrist.",
         dict(body="Du kan lukke testen og komme tilbake fram til Testfrist fr. 18. des."),
         [("Underveis", "Som i dag: «Lagret 21:14», ingen tid."),
          ("Testfrist", "Det som er lagret leveres automatisk (FR-51)."),
          ("Klasseøkt", "Valget «Én økt med tidsgrense» tilbys ikke."),
          ("Tilrettelegging", "Uendret.")],
         "EXPERIENCE.md står som den er. Story 11.12 tas ut av v1 eller legges bak et flagg, og FR-51 i PRD får "
         "samme merknad."),
    ]
    yb = 0
    y0 = col_heads(d, xs, y, cw, opts)
    for x, (let, title, desc, card, rows, fol) in zip(xs, opts):
        yy = y0 + 6
        test_card(d, x, yy, cw, 170, **card)
        yb = max(yb, states(d, x, yy + 206, cw, rows))
    for x, o in zip(xs, opts):
        follows(d, x, yb + 30, cw, o[5])
    foot(d)
    d.save()


for fn in (fig1, fig2, fig3, fig4, fig5, fig6):
    fn()
    print("bygget", fn.__name__)
