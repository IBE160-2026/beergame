"""Kjeden er ryggraden i konsept 02 Fire ledd.
Her ligger kjedevisningen (ett ledd og fire ledd), ukeskrubberen, matrisen og kostnaden per node.
Alle tall kommer fra ../_shared/fixture.json, og bygget stopper hvis kjede, matrise, graf og kostnad ikke stemmer med loggen."""
from e02lib import *

CHAIN = ["Fabrikk", "Distributør", "Grossist", "Detaljist"]   # varene går fra venstre mot høyre
LK, RK = 0.5, 1.0                                           # lagerkost, restordrekost per enhet per uke

# ---------- Matrisens trinn (validert med dataviz validate_palette.js --ordinal, se concept.md) ----------
DIV_B = ["#97BADA", "#6E9FCB", "#2B6CA3", "#1D4E7A"]   # lager 1–9, 10–19, 20–39, 40+
DIV_R = ["#E2A199", "#D47A70", "#B5423A", "#8E2F28"]   # restordre 1–9, 10–19, 20–39, 40+
SEQ = ["#F2F5F8", "#A6B8CA", "#7F95AC", "#44586F", "#0F2A47"]  # ordre 0–4, 5–9, 10–15, 16–23, 24+


def _lum(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contrast(a, b):
    la, lb = sorted([_lum(a), _lum(b)])
    return (lb + 0.05) / (la + 0.05)


def ink_on(fill):
    """Tekstfarge med best kontrast. Bygget stopper under 4,5:1."""
    best = max((INK, PAPER), key=lambda c: contrast(fill, c))
    assert contrast(fill, best) >= 4.5, (fill, contrast(fill, best))
    return best


def div_step(v):
    a = abs(v)
    if a == 0:
        return TINT
    i = 0 if a < 10 else 1 if a < 20 else 2 if a < 40 else 3
    return (DIV_B if v > 0 else DIV_R)[i]


def seq_step(v):
    i = 0 if v <= 4 else 1 if v <= 9 else 2 if v <= 15 else 3 if v <= 23 else 4
    return SEQ[i]


for _c in DIV_B + DIV_R + SEQ + [TINT]:
    ink_on(_c)


# ---------- Tilstand per ledd ----------
def state(S, w):
    """Ett ledds tilstand i Uke w, slik kjeden tegner den. Kostnaden er akkumulert til og med w."""
    cl = sum(S.lager[:w]) * LK
    cr = sum(S.rest[:w]) * RK
    assert abs(cl + cr - S.kostsum(w)) < 1e-6, (S.role, w)
    pipe = [(w + 1, S.order(w - 3)), (w + 2, S.order(w - 2)), (w + 3, S.order(w - 1))]
    over = S.overdue(w)
    assert over >= 0 and over + sum(q for _, q in pipe) == S.paavei(w)
    return dict(role=S.role, lager=S.lager[w - 1], rest=S.rest[w - 1], net=S.net(w), pipe=pipe, over=over,
                pv=S.paavei(w), order=S.order(w), inn=S.inn(w), lev=S.levering(w), sendt=S.sendt(w), cl=cl, cr=cr, cost=cl + cr)


def week_cost(S, w):
    return S.lager[w - 1] * LK + S.rest[w - 1] * RK


def class_week_cost(vals):
    return sum(v * LK if v > 0 else -v * RK for v in vals)


# ---------- Felles tegnehjelp ----------
def chevron(d, x, y, left=True, s=5, col=INK):
    k = -1 if left else 1
    d.path(f"M{x - k * s * 0.5:.1f} {y - s:.1f} L{x + k * s * 0.5:.1f} {y:.1f} L{x - k * s * 0.5:.1f} {y + s:.1f}", stroke=col, sw=1.6)


def arrow_r(d, x, y, col=INK, s=4):
    d.path(f"M{x - s:.1f} {y - s:.1f} L{x:.1f} {y:.1f} L{x - s:.1f} {y + s:.1f}", stroke=col, sw=1.3)


def arrow_l(d, x, y, col=INK, s=4):
    d.path(f"M{x + s:.1f} {y - s:.1f} L{x:.1f} {y:.1f} L{x + s:.1f} {y + s:.1f}", stroke=col, sw=1.3)


def stock_box(d, cx, yb, nw, lager, rest, u, lw=1.2):
    """Beholdningen som boks på sann skala: lager over grunnlinja, restordre under."""
    if lager > 0:
        d.rect(cx - nw / 2, yb - lager * u, nw, lager * u, BLUEF, BLUE, lw)
    if rest > 0:
        d.rect(cx - nw / 2, yb, nw, rest * u, REDF, RED, lw)
    if lager == 0 and rest == 0:
        d.line(cx - nw / 2, yb, cx + nw / 2, yb, INK, 2)


def cost_bar(d, x, y, wmax, cl, cr, cmax, h=7):
    """Kostnaden som to deler på felles skala: lager i blått, restordre i rødt."""
    a = wmax * cl / cmax
    b = wmax * cr / cmax
    if a > 0:
        d.rect(x, y, max(a - 1, 0.8), h, BLUE)
    if b > 0:
        d.rect(x + a, y, b, h, RED)


# ---------- Ett ledd: telefonen ----------
OVER_CAP = 44   # enheter: høyere bokser for forsinket vare får bruddmerke


def chain_seat(d, x, y, w, st, typed=None, u=1.7, up=None, down=None, cost=True, posisjon=False, slotnums=True,
               small=13, upstream="Distributør", downstream="Detaljist", show_cost_split=True, title=True,
               sw=27, nw=56, ext_w=60, mark=None, typed_bold=True, empty_slot=False):
    """Setets eget ledd. Fra venstre: leverandøren (bare navnet), det som er på vei i ukeplasser,
    setets beholdning, det som sendes, og kunden nedstrøms (bare navnet). Ordre går mot venstre øverst.
    Høyden følger tallene, men skalaen u er den samme i alle uker."""
    nslots = 4 if (typed is not None or empty_slot) else 3
    has_over = st["over"] > 0
    qs = [q for _, q in st["pipe"]] + ([typed] if typed is not None else [])
    over_h = min(st["over"], OVER_CAP) * u
    if up is None:
        up = max(max(qs) * u, st["lager"] * u, over_h, 30) + small + 8
    if down is None:
        down = max(st["rest"] * u + small + 8, 24)
    pipe_w = nslots * sw + (sw + 4 if has_over else 0)
    x_up = x
    x_pipe = x + ext_w + 6
    x_node = x_pipe + pipe_w + 10
    cx = x_node + nw / 2
    x_out = x_node + nw
    x_dn = x + w - ext_w
    yo = y + (14 if title else 0)    # ordrelinja
    yb = yo + 10 + up                 # grunnlinja
    # Ordre: tynn linje øverst, informasjon går mot venstre
    d.line(x_up + ext_w, yo, x_dn, yo, INK, 1)
    arrow_l(d, x_up + ext_w, yo)
    arrow_l(d, x_out + 2, yo)
    d.t(x + w, yo - 6, f"Ordre inn {st['inn']}", small, 600, INK, "end")
    if typed is not None:
        d.t(x_pipe, yo - 6, f"Din ordre {typed}", small, 700, INK)
    # Leverandør og kunde: bare navnet, ikke tallene
    for xx, lab in ((x_up, upstream), (x_dn + 6, downstream)):
        bw = ext_w - 6
        d.rect(xx, yb - 30, bw, 30, PAPER, HAIR2, 1, extra='stroke-dasharray="3 3"')
        fs = 11 if text_w(lab, 12) > bw - 6 else 12
        d.t(xx + bw / 2, yb - 11, lab, fs, 400, INK2, "middle")
    # Grunnlinja: varene går mot høyre
    d.line(x_up + ext_w - 6, yb, x_dn + 6, yb, INK, 1)
    arrow_r(d, x_node - 1, yb)
    arrow_r(d, x_dn + 5, yb)
    # Røret: ukeplasser, nærmeste ankomst nærmest noden
    slots = list(st["pipe"])
    if typed is not None:
        slots.append((st["pipe"][-1][0] + 1, typed))
    slots = list(reversed(slots))   # lengst unna til venstre
    xs = x_pipe + (sw + 4 if has_over else 0) + (sw if (typed is None and empty_slot) else 0)
    if has_over:
        hh = over_h
        d.rect(x_pipe + 2, yb - hh, sw - 6, hh, PAPER, GREY, 1.2, extra='stroke-dasharray="3 2"')
        if st["over"] > OVER_CAP:
            yy = yb - hh + 10
            d.rect(x_pipe, yy - 2, sw - 2, 5, PAPER)
            d.line(x_pipe, yy - 3, x_pipe + sw - 2, yy - 6, GREY, 1)
            d.line(x_pipe, yy + 3, x_pipe + sw - 2, yy, GREY, 1)
        if slotnums:
            d.t(x_pipe + sw / 2 - 1, yb - hh - 4, st["over"], small, 400, INK2, "middle")
    for i, (wk, q) in enumerate(slots):
        sx = xs + i * sw
        is_typed = (typed is not None and i == 0 and typed_bold) or wk == mark
        hh = q * u
        if q > 0:
            d.rect(sx + 2, yb - hh, sw - 6, hh, PAPER, INK if is_typed else BLUE, 1.6 if is_typed else 1.1)
        if slotnums:
            d.t(sx + sw / 2 - 1, yb - hh - 4, q, small, 700 if is_typed else 400, INK, "middle")
        d.t(sx + sw / 2 - 1, yb + 15, wk, 11.5, 400, INK3, "middle")
    if typed is None and empty_slot:
        d.rect(xs - sw + 2, yb - 14, sw - 6, 14, "none", INK, 1.1, extra='stroke-dasharray="3 2"')
        d.t(xs - sw + sw / 2 - 1, yb + 15, st["pipe"][-1][0] + 1, 11.5, 400, INK3, "middle")
    if has_over:
        d.t(x_pipe + sw / 2 - 1, yb + 15, "uten", 11, 400, INK3, "middle")
        d.t(x_pipe + sw / 2 - 1, yb + 27, "dato", 11, 400, INK3, "middle")
    # Beholdningen
    stock_box(d, cx, yb, nw, st["lager"], st["rest"], u)
    if st["net"] >= 0:
        d.t(cx, yb - st["lager"] * u - 5, f"Lager {st['lager']}", small, 700, INK, "middle")
    else:
        d.t(cx, yb + st["rest"] * u + small + 2, f"Restordre {st['rest']}", small, 700, INK, "middle")
    # Sendt
    d.t((x_out + x_dn + 6) / 2, yb - 6, f"Sendt {st['sendt']}", small, 400, INK, "middle")
    yend = yb + down
    # Posisjon (bare der den er låst opp)
    if posisjon:
        p = st["net"] + st["pv"]
        tx = x_pipe
        yy = yend + 6
        d.line(tx, yy, x_node + nw, yy, INK, 1)
        d.line(tx, yy - 5, tx, yy, INK, 1)
        d.line(x_node + nw, yy - 5, x_node + nw, yy, INK, 1)
        s = f"Posisjon {sg(st['lager'])} − {st['rest']} + {st['pv']} = {sg(p)}"
        if typed is not None:
            s += f". Med {typed}: {sg(p + typed)}"
        d.t(tx, yy + small + 5, s, small, 700, INK)
        yend = yy + small + 10
    ycost = yend + 12
    if cost:
        d.t(x, ycost + 4, "Totalkostnad", small, 400, INK2)
        d.t(x + w, ycost + 4, f"{nf(st['cost'])} kr", 15, 700, INK, "end")
        if show_cost_split:
            cost_bar(d, x, ycost + 11, w, st["cl"], st["cr"], st["cost"], 5)
            d.t(x, ycost + 32, f"Lager {nf(st['cl'])}", 12.5, 400, INK2)
            d.t(x + w, ycost + 32, f"Restordre {nf(st['cr'])}", 12.5, 400, INK2, "end")
            ycost += 34
        else:
            ycost += 8
    else:
        ycost -= 12
    return {"yb": yb, "bottom": ycost + 6, "cx": cx, "x_pipe": x_pipe, "x_node": x_node, "nw": nw}


# ---------- Fire ledd ----------
def fit_chain(all_states, u, ls=13):
    """Høyden over og under grunnlinja for en hel serie uker, så skrubberen aldri endrer skalaen."""
    upv, dnv = 0, 0
    for sts in all_states:
        for st in sts.values():
            upv = max(upv, max(st["net"], 0), st.get("over", 0) or 0, max([q for _, q in st.get("pipe") or []] or [0]))
            dnv = max(dnv, max(-st["net"], 0))
    return upv * u + ls + 12, dnv * u + ls + 10


def chain4(d, x, y, w, states, u=1.0, up=90, down=70, customer=None, me="Grossist", cost=True, cmax=None,
           names=True, ls=13, sendt=False, production=True, order_label="Ordre", cost_label=True, node_w=None,
           fit=None, frame_me=True, pv_label=True, orders=True, sub_names=True):
    """Hele kjeden: Fabrikk til venstre, kundene til høyre. Varene går mot høyre langs grunnlinja, ordrene mot venstre øverst.
    Hver node: beholdning på sann skala, det som er på vei inn i den, og kostnaden til og med uka."""
    if fit is not None:
        up, down = fit_chain(fit, u, ls)
    cw = 96 if customer is not None else 12
    seg = (w - cw) / 4
    nw = node_w or min(64, seg * 0.3)
    pw = seg - nw - 14
    yo = y + ((38 if sub_names else 34) if names else 8)      # ordrelinja
    yb = yo + 10 + up                  # grunnlinja
    geo = {}
    xend = x + 4 * seg
    ycost = yb + down
    if me in CHAIN and frame_me:
        i = CHAIN.index(me)
        d.rect(x + i * seg + 1, y - 6, seg - 3, (ycost + (50 if cost else 4)) - y + 6, TINT, None, 1, 6)
    d.line(x + 4, yo, xend + (cw - 30 if customer is not None else 0), yo, INK, 1)
    d.line(x, yb, xend + (cw - 26 if customer is not None else 0), yb, INK, 1)
    for i, r in enumerate(CHAIN):
        st = states[r]
        x0 = x + i * seg
        xp = x0 + 6
        xn = x0 + pw + 14
        cx = xn + nw / 2
        geo[r] = {"cx": cx, "xn": xn, "x0": x0}
        if names:
            d.t(cx, y + 12, r, ls + 1, 700, INK, "middle")
            if sub_names:
                nm = NAVN.get(r, "") + (", du" if r == me and me == "Grossist" and frame_me else "")
                d.t(cx, y + 29, nm, ls, 400, INK2, "middle")
        # røret inn i noden, én plass per uke, forsinket vare uten dato lengst til venstre
        if st.get("pipe") is not None:
            slots = list(reversed(st["pipe"]))
            has_over = st["over"] > 0
            sw = (pw - 4) / 4
            xs = xp + sw
            if has_over:
                hh = st["over"] * u
                d.rect(xp + 1, yb - hh, sw - 4, hh, PAPER, GREY, 1.1, extra='stroke-dasharray="3 2"')
            for k, (wk, q) in enumerate(slots):
                if q > 0:
                    d.rect(xs + k * sw + 1, yb - q * u, sw - 4, q * u, PAPER, BLUE, 1.1)
            if pv_label:
                tall = max([st["over"]] + [q for _, q in slots]) * u
                d.t(xp + pw / 2, yb - tall - 6, f"På vei {st['pv']}", ls, 400, INK2, "middle")
            if i == 0 and production:
                d.t(xp + pw / 2, yb + ls + 4, "i produksjon", ls - 1, 400, INK3, "middle")
        arrow_r(d, xn - 1, yb)
        if orders and st.get("order") is not None:
            arrow_l(d, xp + 2, yo)
            d.t(xp + pw / 2, yo - 6, f"{order_label} {st['order']}", ls, 700 if r == me else 400, INK, "middle")
        stock_box(d, cx, yb, nw, max(st["net"], 0), max(-st["net"], 0), u)
        if st["net"] > 0:
            d.t(cx, yb - st["net"] * u - 5, f"Lager {sg(st['net'])}", ls, 600, INK, "middle")
        elif st["net"] < 0:
            d.t(cx, yb + (-st["net"]) * u + ls + 3, f"Restordre {sg(-st['net'])}", ls, 600, INK, "middle")
        else:
            d.t(cx, yb - 6, "Lager 0", ls, 600, INK, "middle")
        if sendt and st.get("sendt") is not None:
            d.t(xn + nw + 4, yb - 5, f"Sendt {st['sendt']}", ls - 1, 400, INK2)
    if customer is not None:
        xc = xend + 10
        bw = cw - 30
        d.rect(xc, yb - 34, bw, 34, PAPER, HAIR2, 1, 4)
        d.t(xc + bw / 2, yb - 13, "Kundene", ls, 600, INK, "middle")
        arrow_r(d, xc - 1, yb)
        if customer != "":
            d.t(xc + bw / 2, yo - 6, f"Kjøper {customer}", ls, 700, INK, "middle")
        arrow_l(d, xend + 2, yo)
    if cost:
        cmax = cmax or max(states[r]["cost"] for r in CHAIN)
        for i, r in enumerate(CHAIN):
            st = states[r]
            x0 = x + i * seg + 8
            bw = seg - 24
            d.t(x0, ycost + 6, f"{nf(st['cost'])} kr", ls + 2, 700, INK)
            cost_bar(d, x0, ycost + 14, bw, st["cl"], st["cr"], cmax, 7)
            if cost_label:
                d.t(x0, ycost + 38, f"lager {nf(st['cl'])}", ls - 1, 400, INK2)
                d.t(x0 + bw, ycost + 38, f"restordre {nf(st['cr'])}", ls - 1, 400, INK2, "end")
    return {"yb": yb, "yo": yo, "geo": geo, "seg": seg, "nw": nw, "bottom": ycost + (46 if cost else 0)}


# ---------- Ukeskrubberen ----------
def scrubber(d, ax, y, sel, wmin=1, wmax=36, step=5, ls=13, label=True, track=True):
    """Spoler tiden. Håndtaket står på samme tidsakse som matrisen under."""
    if track:
        d.line(ax.xl(wmin), y, ax.xr(wmax), y, HAIR2, 3)
        d.line(ax.xl(wmin), y, ax.xc(sel), y, INK, 3)
    for k in range(wmin, wmax + 1):
        if k == sel:
            continue
        if k == wmin or k == wmax or (k % step == 0 and wmax - k >= 3 and k - wmin >= 2):
            d.t(ax.xc(k), y + ls + 9, k, ls - 1, 400, INK3, "middle")
    hw = max(text_w(f"Uke {sel}", ls) + 16, 30)
    d.rect(ax.xc(sel) - hw / 2, y - 11, hw, 22, INK, rx=11)
    d.t(ax.xc(sel), y + ls * 0.34, f"Uke {sel}", ls, 700, PAPER, "middle")
    return y + ls + 12


def scrub_controls(d, x, y, ls=13):
    """Forrige, spol, neste: tegnet som former, ikke tegn."""
    d.rect(x, y - 14, 28, 28, PAPER, HAIR2, 1, 14)
    chevron(d, x + 14, y, True)
    d.rect(x + 34, y - 14, 28, 28, PAPER, HAIR2, 1, 14)
    chevron(d, x + 48, y, False)
    return x + 62


# ---------- Matrisen ----------
def matrix(d, ax, y, rows, ch=20, sel=None, ls=12, wmin=1, wmax=36, label_x=None, numbers=True, sub_ls=None, band=None,
           gap=1.5, right=None):
    """Uker som kolonner, én rad per Rolle eller størrelse. rows: dicts med label, sub, vals(w)->tall eller None, kind.
    kind: 'div' (netto lager), 'seq' (ordre), 'plain' (tall uten farge), 'cost' (kroner per uke)."""
    lx = label_x if label_x is not None else ax.x0 - 8
    yy = y
    for row in rows:
        h = row.get("h", ch)
        if row.get("label"):
            d.t(lx, yy + h / 2 + ls * 0.34 - (5 if row.get("sub") else 0), row["label"], ls + 1, row.get("lw", 600), INK, "end")
        if row.get("sub"):
            d.t(lx, yy + h / 2 + ls * 0.34 + 9, row["sub"], (sub_ls or ls - 1), 400, INK2, "end")
        for k in range(wmin, wmax + 1):
            v = row["vals"](k)
            if v is None:
                continue
            kind = row.get("kind", "plain")
            cx0 = ax.xl(k) + gap / 2
            cw = ax.slot - gap
            if kind == "div":
                f = div_step(v)
            elif kind == "seq":
                f = seq_step(v)
            else:
                f = PAPER
            if f != PAPER:
                d.rect(cx0, yy, cw, h - gap, f)
            if numbers:
                if kind == "cost":
                    s = nf(v, 0) if v else "0"
                else:
                    s = sg(v)
                col = ink_on(f) if f != PAPER else INK
                if kind == "cost" and v == 0:
                    col = INK3
                d.t(ax.xc(k), yy + (h - gap) / 2 + ls * 0.34, s, ls if text_w(s, ls) < cw - 2 else ls - 1.5, 400, col, "middle")
        if right:
            right(row, yy, h)
        yy += h
    if sel is not None:
        d.rect(ax.xl(sel), y - 3, ax.slot, yy - y + 3, "none", INK, 1.6)
    return yy


def week_ticks(d, ax, y, weeks, sel=None, ls=12):
    for k in weeks:
        b = k == sel
        d.t(ax.xc(k), y, k, ls, 700 if b else 400, INK if b else INK3, "middle")


def legend_div(d, x, y, ls=12, lab_l="Restordre", lab_r="Lager"):
    """Trinnene for netto lager, med tall i trinnene, så fargen aldri står alene."""
    d.t(x, y + 11, lab_l, ls, 400, INK2)
    xx = x + text_w(lab_l, ls) + 8
    steps = list(zip(reversed(DIV_R), ("40+", "20", "10", "1"))) + [(TINT, "0")] + list(zip(DIV_B, ("1", "10", "20", "40+")))
    for f, s in steps:
        d.rect(xx, y, 26, 16, f)
        d.t(xx + 13, y + 12, s, 10.5, 400, ink_on(f), "middle")
        xx += 27
    d.t(xx + 6, y + 11, lab_r, ls, 400, INK2)
    return xx + 6 + text_w(lab_r, ls)


def legend_seq(d, x, y, ls=12, lab="Ordre"):
    d.t(x, y + 11, lab, ls, 400, INK2)
    xx = x + text_w(lab, ls) + 8
    for f, s in zip(SEQ, ("0–4", "5", "10", "16", "24+")):
        d.rect(xx, y, 30, 16, f)
        d.t(xx + 15, y + 12, s, 10.5, 400, ink_on(f), "middle")
        xx += 31
    return xx
