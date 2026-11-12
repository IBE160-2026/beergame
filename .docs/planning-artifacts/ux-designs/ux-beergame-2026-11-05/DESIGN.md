---
title: "DESIGN: beergame"
status: final
created: 2026-11-05
updated: 2026-11-10
sources:
  - ../../prds/prd-beergame-2026-10-29/prd.md
  - ../../prds/prd-beergame-2026-10-29/addendum.md
  - ../../../../PRODUCT.md
  - .memlog.md
  - decisions.md
  - .working/valgt-konsept/concept.md
  - .working/valgt-konsept/vlib.py
  - .working/valgt-konsept/screens_core.py
  - .working/valgt-konsept/screens_dyn.py
  - .working/valgt-konsept/screens_debrief_teacher.py
  - .working/valgt-konsept/screens_rest.py
  - mockups/
  - .working/concepts-r3/_shared/BRIEF.md
name: ØL-spillet
description: Norwegian supply chain exercise for whole courses. White paper, one navy ink, blue for stock and red for backlog, and one grammar everywhere — the chain band over a graph over a table, week by week on a shared axis.
colors:
  paper: '#FFFFFF'
  ink: '#0F2A47'
  ink-secondary: '#44586F'
  ink-muted: '#5E6F82'
  hairline: '#E1E6EC'
  axis: '#C3CDD8'
  future-tint: '#F2F5F8'
  lager: '#2B6CA3'
  lager-fill: '#CDDFEE'
  restordre: '#B5423A'
  restordre-fill: '#F0D5D2'
  projection: '#6B7785'
  bar-base: '#B4C4D4'
  order-history: '#5F7A95'
  net-neg-1: '#E1A098'
  net-neg-2: '#CF776D'
  net-neg-3: '#B5423A'
  net-neg-4: '#8C2C25'
  net-pos-1: '#93B8DB'
  net-pos-2: '#6A9AC8'
  net-pos-3: '#2B6CA3'
  net-pos-4: '#1B4A75'
  net-zero: '#F2F5F8'
  flow-1: '#A7B6C6'
  flow-2: '#8396AC'
  flow-3: '#56708B'
  flow-4: '#0F2A47'
typography:
  display:
    fontFamily: Source Sans 3
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
  title-page:
    fontFamily: Source Sans 3
    fontSize: 34px
    fontWeight: '700'
    lineHeight: '1.2'
  title-phone:
    fontFamily: Source Sans 3
    fontSize: 30px
    fontWeight: '700'
    lineHeight: '1.2'
  headline:
    fontFamily: Source Sans 3
    fontSize: 22px
    fontWeight: '600'
    lineHeight: '1.3'
  step-title:
    fontFamily: Source Sans 3
    fontSize: 20px
    fontWeight: '600'
    lineHeight: '1.3'
  body-lead:
    fontFamily: Source Sans 3
    fontSize: 19px
    fontWeight: '400'
    lineHeight: 27px
  body:
    fontFamily: Source Sans 3
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 21px
  body-phone:
    fontFamily: Source Sans 3
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.38'
  label:
    fontFamily: Source Sans 3
    fontSize: 15px
    fontWeight: '600'
    lineHeight: '1.3'
  caption:
    fontFamily: Source Sans 3
    fontSize: 13px
    fontWeight: '400'
    lineHeight: '1.38'
  table-cell:
    fontFamily: Source Sans 3
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 20px
  table-cell-laptop:
    fontFamily: Source Sans 3
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 26px
  table-now:
    fontFamily: Source Sans 3
    fontSize: 13px
    fontWeight: '700'
    lineHeight: 20px
  matrix-cell-min:
    fontFamily: Source Sans 3
    fontSize: 9px
    fontWeight: '400'
  button:
    fontFamily: Source Sans 3
    fontSize: 16px
    fontWeight: '600'
  figure-order:
    fontFamily: Source Sans 3
    fontSize: 32px
    fontWeight: '700'
  figure-total:
    fontFamily: Source Sans 3
    fontSize: 18px
    fontWeight: '600'
  figure-hero:
    fontFamily: Source Sans 3
    fontSize: 40px
    fontWeight: '700'
  figure-amplification:
    fontFamily: Source Sans 3
    fontSize: 20px
    fontWeight: '700'
rounded:
  none: 0px
  xs: 2px
  sm: 6px
  full: 9999px
spacing:
  gutter-phone: 20px
  gutter-phone-chart: 16px
  margin-laptop: 80px
  row-phone: 20px
  row-laptop: 26px
  row-label-phone: 76px
  row-label-laptop: 130px
  field-gap: 8px
  control-height-phone: 50px
  order-input-height: 54px
  tap-target-min: 44px
  chain-pipe-unit-phone: 1.4px
  chain-stock-unit-phone: 0.82px
  week-col-min: 1.6em
  reflow-min: 320px
  design-min: 360px
components:
  focus-ring:
    color: '{colors.ink}'
    width: 2px
    offset: 2px
    gap-color: '{colors.paper}'
  focus-ring-inset:
    color: '{colors.ink}'
    width: 2px
    inner-line-color: '{colors.paper}'
    inner-line-width: 1px
  button-primary:
    background: '{colors.ink}'
    foreground: '{colors.paper}'
    radius: '{rounded.sm}'
    height: '{spacing.control-height-phone}'
    type: '{typography.button}'
    hover-decoration: underline
    pressed-background: '{colors.ink-secondary}'
    disabled-background: '{colors.future-tint}'
    disabled-border-color: '{colors.axis}'
    disabled-foreground: '{colors.ink-muted}'
  button-secondary:
    background: '{colors.paper}'
    foreground: '{colors.ink}'
    border: '1px {colors.ink-muted}'
    radius: '{rounded.sm}'
    hover-border-color: '{colors.ink}'
    pressed-background: '{colors.hairline}'
    disabled-background: '{colors.future-tint}'
    disabled-border-color: '{colors.axis}'
    disabled-foreground: '{colors.ink-muted}'
  text-field:
    background: '{colors.paper}'
    border: '1px {colors.ink-muted}'
    border-error: '1px {colors.restordre}'
    radius: '{rounded.sm}'
    label: '{typography.label}'
    hover-border-color: '{colors.ink}'
    disabled-background: '{colors.future-tint}'
    disabled-foreground: '{colors.ink-muted}'
  link:
    foreground: '{colors.lager}'
    type: '{typography.label}'
    decoration: underline
    hover-decoration-thickness: 2px
    pressed-foreground: '{colors.ink}'
    on-tint-foreground: '{colors.ink}'
  order-input:
    border-empty: '1px {colors.ink-muted}'
    border-typed: '1.4px {colors.ink}'
    border-error-width: 1.4px
    border-error-color: '{colors.restordre}'
    hover-border-color: '{colors.ink}'
    radius: '{rounded.sm}'
    height: '{spacing.order-input-height}'
    value: '{typography.figure-order}'
    placeholder: '{colors.ink-muted}'
    help: '{typography.caption}'
    help-foreground: '{colors.ink-secondary}'
    error-foreground: '{colors.restordre}'
    disabled-background: '{colors.future-tint}'
    disabled-foreground: '{colors.ink-muted}'
  chain-band:
    node-border: '1px {colors.axis}'
    stock: '{colors.lager}'
    backlog: '{colors.restordre}'
    pipe-box-border: '1px {colors.lager}'
    pipe-box-typed-border: '1.5px {colors.ink}'
    flow-arrow: '1.1px {colors.ink}'
    end-label: '{colors.ink-muted}'
  net-graph:
    line-above: '2px {colors.lager}'
    fill-above: '{colors.lager-fill}'
    line-below: '2px {colors.restordre}'
    fill-below: '{colors.restordre-fill}'
    gridline: '{colors.hairline}'
    zero-line: '{colors.axis}'
    posisjon-line-color: '{colors.ink-secondary}'
    posisjon-line-width: 1.5px
    posisjon-marker: square 4px
    posisjon-label: '{typography.caption}'
    projection: '2px dashed {colors.projection}'
  cost-field:
    holding-bar: '{colors.lager}'
    backlog-bar: '{colors.restordre}'
    baseline: '{colors.axis}'
  week-table:
    row-height: '{spacing.row-phone}'
    label-width: '{spacing.row-label-phone}'
    rule: '{colors.hairline}'
    cell: '{typography.table-cell}'
    now-column: '{typography.table-now}'
    own-order-now-fill: '{colors.ink}'
    own-order-now-text: '{colors.paper}'
    known-arrival-border: '1px {colors.ink}'
    posisjon-cell: '{colors.ink}'
    column-min-width: '{spacing.week-col-min}'
    sticky-label-background: '{colors.paper}'
    scrollbar: '{colors.ink-muted}'
  now-line:
    stroke: '1.4px {colors.ink}'
    future: '{colors.future-tint}'
  cost-panel:
    title: '{typography.label}'
    holding-bar: '{colors.lager}'
    backlog-bar: '{colors.restordre}'
    rule: '{colors.axis}'
    total: '{typography.label}'
  week-summary:
    rule: '{colors.hairline}'
    text: '{typography.body-phone}'
  chain-bill:
    holding-bar: '{colors.lager}'
    backlog-bar: '{colors.restordre}'
    total-rule: '{colors.axis}'
    you-row: '{typography.label}'
  order-bars:
    bar: '{colors.order-history}'
    bar-you: '{colors.ink}'
    first-large-order: '{colors.restordre}'
  scrubber:
    track: '{colors.ink-muted}'
    track-filled: '{colors.ink}'
    handle: '{colors.ink}'
    step-button-border: '1px {colors.ink-muted}'
  matrix-wall:
    net-below: '{colors.net-neg-1}'
    net-above: '{colors.net-pos-1}'
    net-zero: '{colors.net-zero}'
    flows: '{colors.flow-1}'
    min-text: '{typography.matrix-cell-min}'
    sign-glyph-on-light: '{colors.ink}'
    sign-glyph-on-dark: '{colors.paper}'
    legend: '{typography.caption}'
    plenum-caption: '{typography.body}'
  view-toggle:
    active-background: '{colors.ink}'
    active-foreground: '{colors.paper}'
    border: '1px {colors.ink-muted}'
    radius: '{rounded.sm}'
    hover-border-color: '{colors.ink}'
    pressed-background: '{colors.hairline}'
    disabled-background: '{colors.future-tint}'
    disabled-foreground: '{colors.ink-muted}'
  segmented-choice:
    active-background: '{colors.ink}'
    active-foreground: '{colors.paper}'
    border: '1px {colors.ink-muted}'
    radius: '{rounded.sm}'
    hover-border-color: '{colors.ink}'
    pressed-background: '{colors.hairline}'
    disabled-background: '{colors.future-tint}'
    disabled-foreground: '{colors.ink-muted}'
  switch:
    on: '{colors.ink}'
    radius: '{rounded.full}'
    hover-border-color: '{colors.ink}'
    pressed-background: '{colors.ink-secondary}'
    disabled-background: '{colors.future-tint}'
    disabled-foreground: '{colors.ink-muted}'
  seat-status-list:
    done-dot: '{colors.ink}'
    waiting-dot: '1.5px {colors.ink}'
    status-text: '{colors.ink-secondary}'
  step-list:
    current-dot: '{colors.ink}'
    later-dot: '{colors.axis}'
  attention-band:
    background: '{colors.restordre-fill}'
    foreground: '{colors.ink}'
    link-foreground: '{colors.ink}'
  ai-label:
    foreground: '{colors.ink-secondary}'
  demo-label:
    foreground: '{colors.ink-muted}'
    type: '{typography.caption}'
  quiz-option:
    border: '1px {colors.ink-muted}'
    border-correct: '1.4px {colors.ink}'
    border-wrong: '1.4px {colors.restordre}'
    radius: '{rounded.sm}'
    hover-border-color: '{colors.ink}'
    pressed-background: '{colors.hairline}'
    disabled-background: '{colors.future-tint}'
    disabled-foreground: '{colors.ink-muted}'
  cost-distribution:
    tick: '{colors.ink-secondary}'
    median: '{colors.ink}'
    last-year: 'dashed {colors.ink-secondary}'
  funnel:
    bar: '{colors.order-history}'
  date-line:
    axis: '{colors.ink}'
    lab-hour: '{colors.lager}'
  allocation-preview:
    cell: '{colors.bar-base}'
    selected: '1px {colors.ink}'
  game-card:
    border: '1px {colors.axis}'
    radius: '{rounded.sm}'
    title: '{typography.label}'
    total: '{typography.body}'
  phone-header:
    title: '{typography.title-phone}'
    subtitle: '{typography.body-phone}'
    subtitle-foreground: '{colors.ink-secondary}'
    total: '{typography.figure-total}'
    total-label: '{typography.caption}'
  file-upload:
    border: '1px {colors.ink-muted}'
    radius: '{rounded.sm}'
    file-name: '{typography.label}'
    summary: '{typography.body}'
  wall-filters:
    label: '{typography.caption}'
    active-weight: '600'
    active-decoration: underline
    count-foreground: '{colors.ink-secondary}'
  message-composer:
    recipient: '{typography.label}'
    field-border: '1px {colors.ink-muted}'
    sent-count: '{typography.caption}'
  interactive-item:
    point: '{colors.ink}'
    point-size: 8px
    line: '2px {colors.ink}'
    cell-border: '1px {colors.ink-muted}'
    cell-error-color: '{colors.restordre}'
    unanswered: '{colors.ink-muted}'
  pause-control:
    trigger-border: '1px {colors.ink-muted}'
    status: '{typography.body-phone}'
    status-foreground: '{colors.ink}'
  ai-insert:
    border: '1px {colors.ink-muted}'
    consequence: '{typography.caption}'
    consequence-foreground: '{colors.ink-secondary}'
  flag-control:
    foreground: '{colors.ink}'
    type: '{typography.caption}'
    flagged-weight: '600'
  demand-band:
    fill: '{colors.lager-fill}'
    label: '{colors.ink}'
    label-weight: '600'
  chain-cost-chart:
    holding-area: '{colors.lager-fill}'
    backlog-area: '{colors.restordre-fill}'
    holding-line: '{colors.lager}'
    backlog-line: '{colors.restordre}'
    baseline: '{colors.axis}'
  connection-notice:
    rule: '1px {colors.ink-muted}'
    foreground: '{colors.ink}'
    type: '{typography.body}'
    timestamp: '{colors.ink-secondary}'
  skeleton:
    rule: '{colors.hairline}'
    axis: '{colors.axis}'
    label: '{colors.ink-muted}'
---

# ØL-spillet: Design Spine

Visual reference for the chosen concept «Graf over tabell» (02 Meteogrammet's palette and type, 04's chain band and graph-over-table, 08's Debrief and cost panel). Mockups: `mockups/01-landing.png` to `10-pedagogikk.png`. How things behave lives in `EXPERIENCE.md`.

**These spines win on conflict with the mockups and the concept files.** Every known deviation is listed here.

**Mockup deviations.**

| Mockup | What it shows | Spine rule |
|---|---|---|
| `01-landing.png`, header | The working name «Graf over tabell» | The product name is «ØL-spillet» (memlog override, 2026-11-09) |
| `01-landing.png` | «Uker spilt» bars | No week counts outside the game; Faglærer progress is the share of games finished and their status (`EXPERIENCE.md` → Hidden information) |
| All sheets | Idle borders of interactive controls in `axis` (1.6:1) | `ink-muted` (Components → Interaction states) |
| Cost-over-time charts | 12 px axis labels «Uke 1» | [ASSUMPTION: the 12 px axis labels «Uke 1» drawn in the mockups' cost-over-time charts move to 13 px on phone; the 13 px floor wins.] |
| `06-spilldynamikk.png` E | A 38 px «Ta tilbake setet» | [ASSUMPTION: the 38 px «Ta tilbake setet» in `06` E grows to `{spacing.tap-target-min}`.] (`EXPERIENCE.md` → Accessibility Floor) |
| `05-spill.png` («Hjelpegrad: samme kolonne, to nivåer»), `10-pedagogikk.png` («Hjelpegrad»: «Summen må Sara regne selv», «Replay: raden Posisjon … åpnes») and the Replay caption in `09-alle-sider.png` | The old state from before the Posisjon decision, with Posisjon in the Replay only | Posisjon is shown in both rounds, and only the projection is Replay-only (`EXPERIENCE.md` → Hidden information). This also settles the «Posisjon 24 / 3 / 42 / 37» labels beside the Klassespill Kjedebånd in `10-pedagogikk.png`: with Posisjon shown, they no longer conflict with the spine. |

## Brand & Style

ØL-spillet looks like a meteogram (the yr.no kind): the graph on top, the table directly under it, one column per Uke, and a single now-line through both. The design sits on that one grammar. The chain band goes over the graph, a cost field goes under it, and the table puts a number under every mark. A student can always check the line against the number in the same column. That check is the teaching point (P1): stock is a running sum, worked out down the column.

The posture is **elegant and data-centric**. Charts and domain principles carry the design. Metaphors, illustrated worlds and decoration were rejected after round 1 as childish (memlog). The surface is white paper, one navy ink, and two signal colours with fixed jobs: blue for stock, red for backlog. There are no icons, no illustrations, no shadows, no game chrome and no celebration. Faglærer surfaces exist to be scanned in seconds. In the Class game and the Debrief, the graph over the table is the main content. The landing page makes its case with one honest chart of a single Seat.

## Colors

Fixed Meteogrammet palette (BRIEF.md). No new colours were added in round 3. `vlib.py` checks contrast at build time.

| Token | Hex | Job | Contrast on `paper` | Never |
|---|---|---|---|---|
| `paper` | #FFFFFF | The only background, phone through projector | — | Tinted or dark section backgrounds |
| `ink` | #0F2A47 | Text, order marks, primary buttons, the now-line, the Seat's own row and order bar | 14.6:1 | Decoration |
| `ink-secondary` | #44586F | Secondary text, status words («har bestilt»), the AI label | 7.3:1 | Numbers a decision depends on |
| `ink-muted` | #5E6F82 | Axis ticks, «Demodata», chain end labels, placeholders | 5.2:1; 4.7:1 on `future-tint` | Body copy |
| `hairline` | #E1E6EC | Gridlines and table rules | — | Component boundaries |
| `axis` | #C3CDD8 | Zero line, axes, the cost total rule, decorative node borders | — | Text, borders of interactive controls (use `ink-muted`) |
| `future-tint` | #F2F5F8 | Area to the right of the now-line (known arrivals, nå + 4) | — | The past |
| `lager` / `lager-fill` | #2B6CA3 / #CDDFEE | Stock above zero, holding cost (0,50), links | 5.6:1 (`lager`) | Backlog or "good" |
| `restordre` / `restordre-fill` | #B5423A / #F0D5D2 | Backlog below zero, backlog cost (1,00), errors, wrong quiz answer, the near-Takeover band | 5.5:1 (`restordre`) | "Bad player". Red means backlog, never blame |
| `projection` | #6B7785 | Dashed projection line, in Replay only | — | The Class game |
| `bar-base` | #B4C4D4 | Neutral bars (allocation preview) | — | Data with a sign |
| `order-history` | #5F7A95 | Order bars for other Roles, funnel bars | 4.46:1 | Text |

**Fixed cost colours everywhere:** backlog cost in the red family, holding cost in the blue family. Total cost is their sum. The chain's cost is the sum over the four Roles.

**Matrix steps** (04's steps, run through the dataviz validator: monotonic lightness, lightest step ≥ 2:1 against white). They are used in Netto lager cells, the Debrief Rolle × Uke table and the Faglærer matrix wall.

| Scale | Bin | Step 1 | Step 2 | Step 3 | Step 4 |
|---|---|---|---|---|---|
| Netto lager below zero (`net-neg-*`) | \|v\| 1–9 / 10–19 / 20–34 / 35+ | #E1A098 | #CF776D | #B5423A | #8C2C25 |
| Netto lager above zero (`net-pos-*`) | same bins | #93B8DB | #6A9AC8 | #2B6CA3 | #1B4A75 |
| Zero (`net-zero`) | 0 | #F2F5F8 | | | |
| Flows / orders (`flow-*`) | <5 no fill; 5–9 / 10–19 / 20–29 / 30+ | #A7B6C6 | #8396AC | #56708B | #0F2A47 |

Cell numbers are `ink` on steps 1–2 and `paper` on steps 3–4, all ≥ 4.5:1. In Graf over tabell and the Debrief Rolle × Uke table, every Netto lager cell prints its signed number with a true minus (−13). The Matrisevegg prints a number or a sign glyph by its own rule (Components → Matrisevegg). Red and blue steps are matched in lightness (1.01–1.10:1), so only hue tells them apart; the printed number or glyph carries the sign.

**Text on tints.** Text on a filled or tinted background uses only the tokens below. Every pair is ≥ 4.5:1 (WCAG 2.x formula, as `vlib.contrast`). Where a row names several backgrounds, the ratios follow that order (e.g. `lager-fill` / `restordre-fill`).

| Background | Allowed text | Ratio | Fails, never use |
|---|---|---|---|
| `paper` | `ink`, `ink-secondary`, `ink-muted`, `lager`, `restordre` | 14.6 / 7.3 / 5.2 / 5.6 / 5.5 | `order-history` (4.46), `projection` as text |
| `future-tint` | same as `paper` | 13.3 / 6.7 / 4.7 / 5.1 / 5.0 | — |
| `lager-fill`, `restordre-fill` | `ink`, `ink-secondary` | 10.7 / 10.5; 5.4 / 5.3 | `ink-muted` 3.8 / 3.7, `lager` 4.1 / 4.0, `restordre` 4.0 / 4.0, `order-history` 3.3 / 3.2 |
| `net-*-1`, `flow-1` | `ink` | 6.7–7.0 | `ink-secondary` 3.4–3.5 and every lighter token |
| `net-*-2`, `flow-2` | `ink` | 4.51 (`net-neg-2`) / 4.90 (`net-pos-2`) / 4.80 (`flow-2`) | everything else |
| `net-*-3/4`, `flow-3/4` | `paper` | 5.1–14.6 | `ink` (1.0–2.8) |
| `hairline` (pressed fill only) | `ink` | 11.6 | `ink-muted` 4.1 |

Links on a tinted row or band (Varselbånd, the near-Takeover wall row, the Debrief demand band) are `ink` with an underline (`{components.link.on-tint-foreground}`), never `lager`.

Focus ring contrast on every background: Components → Interaction states → Fokusring.

Light theme only. Dark mode is out of scope for v1 (founder decision 2026-11-09). The projector also uses `paper`.

## Typography

**Source Sans 3**, weights 400, 600 and 700, falling back to Source Sans Pro, Segoe UI, Arial, sans-serif. Loaded from Google Fonts.

- **Tabular figures** (`font-variant-numeric: lining-nums tabular-nums`) in every cell, axis, table, cost panel and matrix, so the columns line up.
- **Proportional figures** only in the largest single numbers: `{typography.figure-hero}` for «2 266,00 kr» and `{typography.figure-amplification}` for «7,6×».
- Norwegian number format: space as the thousands separator, comma as the decimal mark, kroner to two decimals («68,00 kr»). Narrow table cells may drop the decimals («13», «6,5»).

| Role | Token | Where |
|---|---|---|
| Landing headline | `display` 48/56 700 | «Hver uke har en strek og et tall. Studentene ser begge.» |
| Laptop page title | `title-page` 34 700 | «Lag Klasse», «Klasseøkt for class-of-1994» |
| Phone screen title | `title-phone` 30 700 | «Uke 11», «Spill 17», «Spillet er ferdig» |
| Section heading | `headline` 22 600 | «Ugyldige rader: 4 av 250», «Datoer», «Kjedens regning» |
| Debrief step title | `step-title` 20 600 | «1  Skriv Forklaringen først» |
| Lead | `body-lead` 19/27 | Landing lead paragraph |
| Body | `body` 15/21, `body-phone` 14 | Laptop help text; seat rows on the phone |
| Labels | `label` 15 600 | Field labels, «Din ordre for Uke 11», «Kostnad så langt» |
| Help and caption | `caption` 13 | Helper lines under the order input, «Demodata», chart notes |
| Table | `table-cell` 13 / `table-cell-laptop` 15; current Uke in `table-now` 700 | Week tables |
| Order value | `figure-order` 32 700 | The number typed into the order input |
| Running total | `figure-total` 18 600 | «68,00 kr» in the phone header |

**Floors:** 13 px on phone screens. 9 px on the Faglærer matrix wall (`matrix-cell-min`), which always has a 13 px table view. Nothing smaller anywhere except the contact-sheet mockup (for the 12 px chart labels in the mockups, see Mockup deviations). No all caps, no eyebrows, no letter-spacing tricks.

**Text never shrinks to fit.** Sizes are set in `rem`/`em` and grow with browser zoom and text-only zoom; cell text never drops below its floor. When a table runs out of width, the visible columns get fewer (Layout & Spacing → Graf over tabell at narrow widths). The mockup library's loop that shrinks table text toward 9 px (`vlib.gtable`) is a drawing shortcut, not a product rule.

## Layout & Spacing

**One grammar, top to bottom:** chain band → graph (Netto lager field with the Posisjon line, then Kost per uke field) → table with one column per Uke → the now-line through all of them. Graph and table share one x-axis. Every mark has its number directly beneath it. Graph fields sit `{spacing.field-gap}` apart. Use whitespace, not boxes, to group things.

**Widths.** `{spacing.design-min}` (360 px) is the design target: the phone layout is drawn and tuned there. `{spacing.reflow-min}` (320 CSS px, WCAG 1.4.10, the same as 1280 px at 400 % zoom) is the reflow floor: every Student, Faglærer and Admin surface works there without page-level horizontal scroll (NFR-6). Faglærer and Admin surfaces keep the laptop as their design target; 320 px is a floor they must pass, not a layout to tune. Components fall into two groups:

| Surfaces | Must reflow to 320 px (no horizontal scroll) | Two-dimensional exception (scrolls inside its own bounded region) |
|---|---|---|
| Student | Kjedebånd, Ordrefelt, Knapper, Kostnad så langt, Uke-overgang, Setestatus, Stegene, Spillkort, Topplinje, Quizvalg, Tekstfelt, Pausevalg, Sett inn KI-spiller, Tilkoblingslinje, every form | Graf over tabell (graph + week table as one unit), Matrisevegg, Ordrestolper with the Rolle × Uke numbers, the Debrief Rolle × Uke table, the value table of an Interaktiv oppgave |
| Faglærer and Admin | Lærerhjem, every form (Lag Klasse with Filopplasting and the invalid rows, Klasseøkt with Valgknapper and Bryter, Spørsmål og vekter, Sensorveiledning, Eksport), Varselbånd, Oppdater automatisk, Visningsbryter, Veggfiltre, the right rail («Venter ellers», Kostnadsfordeling with its text summary, Trakt with its counts), Meldingsskjema, Spillstyring, Tilrettelegging, Fullføringsretting, Studentside, Admin lists and forms | Matrisevegg with the class median graph over it and its «Vis som tabell» table (one region, game column and Uke header sticky), Datolinje, Fordelingsforhåndsvisning, the Spillinnsikt Rolle × Uke table and Ordrestolper, Klasserapport and Tverrklasse-statistikk tables, the Kontrolltest comparison table |

At 320 px on Faglærer surfaces: the page margin `{spacing.margin-laptop}` gives way to `{spacing.gutter-phone}`; the Varselbånd's text comes first and its actions wrap under it at full width; the right rail stacks under the wall; the headline counts and Veggfiltre wrap. Charts on the right rail scale to the width and keep their printed numbers. Product tests render the Oversikt, Klasseøkt, Lag Klasse, Meldingsskjema and one Admin list at 1280 px with 400 % zoom and with 200 % text, and fail on page-level horizontal scroll or an action out of view.

**Devices.** The row keys match `EXPERIENCE.md` → Responsive & Platform.

| Device | Design canvas | Gutters | Rows and label column | Arrangement | Mockup |
|---|---|---|---|---|---|
| Student, phone (Klassespill, Replay) | 360 px design target, portrait. Mockups are drawn at 390×844 | Text `{spacing.gutter-phone}` (20 px). Chain band and table `{spacing.gutter-phone-chart}` (16 px) | Rows `{spacing.row-phone}`, label column `{spacing.row-label-phone}` | The week window runs from nå − 7 to nå + 4, which is 12 columns at 360 px and 100 % text. The right edge is always nå + 4, never the end of the game. The order input and the confirm button fill the width at `{spacing.order-input-height}` and `{spacing.control-height-phone}`. | `05-spill.png`, `06-spilldynamikk.png` |
| Student, laptop in Labtime | — | — | — | Left: chain band, graph and table from Uke 1 to nå + 4. Right column: the order input, with «Kostnad så langt» pinned directly under it. | — |
| Faglærer laptop | 1440 px canvas; laptop layout from 1024 px [ASSUMPTION, as for Students]; reflow floor `{spacing.reflow-min}` | Page margin `{spacing.margin-laptop}` | Rows `{spacing.row-laptop}`, label column `{spacing.row-label-laptop}`, where the graph-over-table grammar appears | The Oversikt puts the class median graph over the matrix wall, with the view toggle above the wall. A right rail holds «Venter ellers», «Klassens kostnad» and «Trakt». | `08-laerer-oversikt.png` |
| Plenary projector | The laptop layout | — | — | The Debrief «Delt skjerm» and «Vis i plenum» reuse the laptop layout on the same white paper. | `07-debrief.png`, right |

**Graf over tabell at narrow widths and large text.** The graph and the week table are one horizontally scrollable region with one scroll position, so every mark stays over its number.

- The row-label column (and the graph's y-axis labels above it) is sticky on `paper` at the left edge. It starts at `{spacing.row-label-phone}` and may widen to at most 40 % of the region as text grows; labels wrap to two lines rather than clip. [ASSUMPTION: 40 %]
- A column is never narrower than `{spacing.week-col-min}` (1.6 em, 20.8 px at 13 px text) or the widest number in the window plus 0.25 em, whichever is larger. [ASSUMPTION: 1.6 em, chosen so 12 columns fit at 360 px and 100 % text, as drawn]
- The number of visible columns follows from that: 12 at 360 px, 10 at 320 px, 4 at 360 px with 200 % text. Columns that do not fit are reached by scrolling; the content never extends past nå + 4. Where the region scrolls on load and on each Uke advance: `EXPERIENCE.md` → Component Patterns → Graf over tabell.
- The scroll affordance is a visible (not overlay) scrollbar in `{components.week-table.scrollbar}` under the table, plus the caption «Sveip for tidligere uker» while earlier columns are hidden. [ASSUMPTION: copy] No fades or gradients.
- The table is an HTML `<table>` in relative units, never SVG text. Product tests render it at 320 px and 360 px, each at 100 % and 200 % text, and fail if any cell text is below 13 px or clipped.

The chain band's scale rule is under Components → Kjedebånd.

## Elevation & Depth

None. There are no shadows, no raised cards and no layering. Depth comes only from two things:

- `future-tint` to the right of the now-line, which separates the known past from known arrivals.
- 1 px rules (`hairline` inside tables, `axis` for zero lines and totals).

The phone panel «Alle rader og kostnad» is a full screen of its own, not a floating sheet.

## Shapes

- `{rounded.sm}` (6 px) on buttons, inputs, the order input, cards, quiz options and toggles.
- `{rounded.xs}` (2 px) on the column highlight frame.
- `{rounded.full}` on status dots and the switch.
- Square corners (`{rounded.none}`) on chart marks, table cells, matrix cells and cost bars. Data stays crisp.

The rounded phone outline in the mockups is presentation chrome, not a token.

## Components

Every component below has behaviour in `EXPERIENCE.md` → Component Patterns, under the same name and in the same groups.

### Interaction states

These apply to every interactive component. Hover is pointer-only and never the only cue.

| State | Filled: `button-primary`, active segment of `view-toggle` / `segmented-choice`, `switch` on | Outlined: `button-secondary`, `text-field`, `order-input`, `quiz-option`, inactive segment, `switch` off, `file-upload`, step buttons | `link` |
|---|---|---|---|
| Idle | `ink` fill, `paper` label (14.6:1) | `paper`, 1 px `ink-muted` border (5.2:1), `ink` label | `lager` 600, underlined; `ink` on tints |
| Hover | label underlined | border `ink` | underline 2 px |
| Focus-visible | `{components.focus-ring.color}` ring, 2 px, 2 px `paper` gap (see Fokusring below) | same | same |
| Pressed | `ink-secondary` fill, `paper` label (7.3:1) | `hairline` fill, `ink` label (11.6:1) | `ink` |
| Disabled | `future-tint` fill, 1 px `axis` border, `ink-muted` label (4.7:1) | same | not used: a link that cannot act is plain text |
| Error | — | 1.4 px `restordre` border plus reason text | — |

Focus uses `:focus-visible`. The outline is never removed without this replacement. Disabled controls that explain themselves (the empty «Bekreft ordre») stay focusable with `aria-disabled`. So does every control that becomes unavailable while it has focus (− and + at their limits, «Bekreft ordre» while submitting): it shows the Disabled look but keeps focus, never the native `disabled` (`EXPERIENCE.md` → Accessibility Floor → Focus and order).

Idle borders of interactive controls (`text-field`, `order-input`, `quiz-option`, `button-secondary`, `view-toggle`, `segmented-choice`) use `ink-muted`, which meets the WCAG 2.1 non-text 3:1 floor. The mockups draw them in `axis` (1.6:1); the spine wins (see Mockup deviations).

- **Fokusring (`focus-ring`, `focus-ring-inset`).** The outer ring goes on controls; the inset frame goes on table rows, wall rows and matrix cells that take focus.
  - `focus-ring`: a 2 px `ink` ring with a 2 px `paper` gap between it and the control. The ring is 14.6:1 on `paper`, 13.3:1 on `future-tint`, 11.6:1 on `hairline`, 10.7:1 on `lager-fill` and 10.5:1 on `restordre-fill`. On `ink` fills (primary button, active segment, the Din ordre cell) the `paper` gap separates ring from fill (14.6:1).
  - `focus-ring-inset`, inside tables and the wall: a 2 px `ink` frame with a 1 px `paper` line inside it. The `ink` frame gives the contrast on light cells (≥ 4.51:1) and the `paper` line gives it on dark cells (≥ 5.14:1), so the ring reads on every matrix step.

### Game screen

- **Topplinje (`phone-header`).** The top of the phone game screen (`05-spill.png`, left): «Uke 11» in `title-phone`, «Grossist, Spill 17» under it in `body-phone` `ink-secondary`, and at the right «Totalkostnad» in `caption` over «68,00 kr» in `figure-total`. The Totalkostnad pair is one button with a hit area of at least `{spacing.tap-target-min}`. It has no border; on hover its label is underlined, and it takes the standard focus ring.
- **Kjedebånd (`chain-band`).** The Seat's own link as a horizontal flow: upstream neighbour at the left end, downstream at the right (`ink-muted` end labels).
  - The node is a paper box with an `axis` border. Its stock shows as a blue bar above the baseline, or its backlog as a red bar below. The label is «Lager 12» or «Restordre 13» in `label`.
  - Arrows are `ink`, 1.1 px. The order line runs left along the top («Din ordre 24», «Ordre inn 8»). The goods line runs right below it («Levering 4», «Sendt 4»).
  - På vei shows as boxes on the pipe at true scale («På vei 16 + 24»). The just-typed order box has a 1.5 px `ink` border. Overdue goods are a dashed box with two slashes.
  - The full four-Role chain (Debrief, Faglærer) adds «Produksjon» at the left and «Kundene» at the right. The Seat's own node gets a 1.4 px `ink` border.
  - **Scale** (issue #24, `10-pedagogikk.png`, Uke 18):
    - Known arrivals (the next four Uker) are always drawn at true scale, `{spacing.chain-pipe-unit-phone}` per unit on phone. Stock and backlog use `{spacing.chain-stock-unit-phone}` per unit.
    - These two values are the maxima at 390 px. The real pixels per unit are derived from the available band width, so the worst Uke of the game (for example «På vei 56 + 13» plus an overdue box, `06` E) fits at 320 px. Labels wrap under the band rather than overlap. [ASSUMPTION: scale down uniformly, with the same factor for pipe and stock]
    - Units overdue with no known date get a fixed-width box with a marked break, and their number is written above it («39»).
    - Product tests check that the band fits at 320 px and 360 px in every Uke of a Classic game.
- **Graf over tabell (`net-graph`, `cost-field`, `week-table`, `now-line`).** Netto lager is one 2 px line. It is blue with `lager-fill` above zero and red with `restordre-fill` below. Axes have a true zero and direct labels («Restordre 13» at the now-dot). Ticks −40/−20/0/20 as drawn; the y-range widens to hold both Netto lager and Posisjon. [ASSUMPTION: ticks in steps of 20, range from the data]
  - **Posisjon line** (Klassespill and Replay): Posisjon = Lager − Restordre + På vei, drawn as a 1.5 px `ink-secondary` line (`{components.net-graph.posisjon-line-color}`, 7.3:1 on `paper`, 6.7:1 on `future-tint`, ≥ 5.3:1 on the fills) with a 4 px square marker at every Uke and no area fill. It is told apart from Netto lager by four cues besides colour: no fill, thinner stroke, square markers, and the direct label «Posisjon 3» at its now-point in `caption`. It is solid, which separates it from the dashed projection. It stops at nå, like Netto lager.
  - Kost per uke is stacked bars: holding cost (blue) at the bottom, backlog cost (red) on top, 1.5 px apart. A key reads «restordre 1,00 / lager 0,50». The axis has a fixed maximum, marked by its one tick, «40 kr», as drawn.
  - Table rows are separated by `hairline`. Netto lager cells are filled with the matrix steps. The Posisjon row has plain `ink` numbers with no fill, so the two sums never look alike. The current Uke number is bold.
  - The Din ordre cell for nå is an `ink` block with a `paper` number. Before the Student types an order, it is an empty dashed cell.
  - Known arrivals in Levering sit in outlined boxes to the right of nå. A thin line joins the order to its arrival cell four columns later.
  - The now-line is 1.4 px `ink`, labelled «Nå».
  - The projection is drawn in Replay only, as a dashed `projection` line ending in a hollow dot.
  - Narrow widths, sticky labels and scrolling: see Layout & Spacing.
- **Ordrefelt (`order-input`).** A full-width box with − and + segments at the ends and the value centred in `figure-order`. Above it: the label «Din ordre for Uke 11», with the link «Alle rader og kostnad» right-aligned. Under it, always: the help line «Hele tall fra 0 til {maks}.» in `caption` `ink-secondary`.
  - Empty: `ink-muted` border and the placeholder «Antall enheter» in `ink-muted`.
  - Typed and valid: 1.4 px `ink` border.
  - Invalid or out of range: 1.4 px `restordre` border (5.5:1) and the reason in `restordre` under the help line («Skriv et helt tall fra 0 til {maks}.»). Colour is never the only cue: the reason text is always there.
  - Read-only (Veiledet uke, submitting): `future-tint` fill, value in `ink-muted` (4.7:1).
  - The − and + segments follow the outlined-control states above; the one that cannot act (− at 0, + at {maks}) takes the Disabled look with `aria-disabled` and keeps focus.
- **Alle rader og kostnad.** A full phone screen on `paper`, with no overlay. The title «Alle rader, Uke 11» is set at 24 px, weight 700 (as drawn), with «Lukk» as a `link` at the top right. It holds `week-table` with all rows (Uke, Ordre inn, Levering, Sendt, Lager, Restordre, Netto lager, På vei, Posisjon, Din ordre, Kost per uke, Sum, kr) under a `net-graph` and `cost-field`. «Sum, kr» is the running Totalkostnad per Uke, the table behind «Totalkostnad over tid». Below that: the lines «Netto lager i kolonne 11  −9 + 4 − 8 = −13» and «Posisjon i kolonne 11  −13 + 16 = 3», then `cost-panel`.
- **Kostnad så langt (`cost-panel`).** The title is in `label`.
  - «Lagerkostnad» and «Restordrekostnad» rows each carry a thin proportional bar under the label (blue, red), with the amount right-aligned in weight 600.
  - An `axis` rule, then «Totalkostnad» in weight 700.
  - «Totalkostnad over tid» is a stacked area from Uke 1 to nå: holding cost below, backlog cost above, true zero. On laptop a `link` «Vis som tabell» under it opens the Uke / Lager / Restordre / Sum, kr table in place.
  - Last comes the week's sum line in `caption`: «Denne uka: 13 restordre × 1,00 = 13,00 kr».
- **Uke-overgang (`week-summary`).** A short list of label and number rows («Levering 4 … Restordre 13 blir 20»), then the week's sum and a link.

### Controls

- **Knapper (`button-primary`, `button-secondary`).** Primary: `ink` fill, `paper` text, weight 600. One per screen. Secondary: paper with an `ink-muted` border. Labels say what happens («Bekreft ordre på 24»). Disabled buttons use the shared disabled state above, never the secondary style.
- **Lenke (`link`).** Links are `lager`, weight 600, underlined.
- **Tekstfelt (`text-field`).** Label above in `label`. The invalid state has a `restordre` border and the reason in `restordre` beside it («Domene mangler»).
- **Valgknapper (`segmented-choice`).** Choice controls have one segment per option. The active one is filled `ink` with `paper` text; the inactive ones have an `ink-muted` border.
- **Bryter (`switch`).** The switch is on in `ink`, with a text label beside it («Ja, står i emneplanen»).

### Seats and status

- **Setestatus (`seat-status-list`).** Rows of dot, Role (weight 600), name and status text (`ink-secondary`, right-aligned). A filled dot means «har bestilt», a hollow dot means waiting. The text always repeats the state.
- **Pausevalg (`pause-control`).** A `button-secondary` «Ta pause» under Setestatus. Choosing it opens, in place, the two consequence lines in `caption` and a `button-primary` «Ta pause uten avtalt tid». It has no date or time field: only the Faglærer sets an agreed time (Faglærer → Spillstyring). While paused, the status line sits above Setestatus in `body-phone` `ink` (copy: `EXPERIENCE.md` → State Patterns → Student game). Spine-only, undrawn.
- **Sett inn KI-spiller (`ai-insert`).** A `button-secondary` «Sett inn KI-spiller for Jonas» on the absent Seat's Setestatus row, full width under the row on phone, with its consequence in `caption` `ink-secondary` directly above it. Spine-only, undrawn.
- **Spillkort (`game-card`).** The Hjem card in `04-student-hjem.png`: a `paper` card with a 1 px `axis` border (decorative; the content is labelled) and `{rounded.sm}`. Title «Spillet venter på deg» in `label` with «Uke 11» right-aligned. Inside: a mini `net-graph` over a `week-table` with three rows (Uke, Netto lager, Din ordre) in the same 12-column window, then «Totalkostnad 68,00 kr» in `body` and one `button-primary` «Gå til Uke 11». It reuses the Graf over tabell tokens at mini scale; no new marks.
- **Stegene (`step-list`).** A vertical line of dots: Klassespill, Debrief, Quiz, Replay, Individuell test, Rapport. The current step is filled, with its status on the right («pågår»).

### Game end and Debrief

- **Kjedens regning (`chain-bill`).** A table with columns Lager / Restordre / Sum and one row per Role from Detaljist to Fabrikk. Each row has a split bar (blue | red) under it. The Seat's own row is in weight 600 with «(deg)». The «Kjeden» row, in weight 700, sits under an `axis` rule.
  - The Debrief adds a «Simulert, samme kunder» block with two rows.
  - The hero total uses `figure-hero`.
- **Kjedens kostnad over tid (`chain-cost-chart`).** On «Spillet er ferdig» (`06-spilldynamikk.png` F): the chain's cumulative cost from Uke 1 to the last Uke as a stacked area, holding cost (`lager-fill`, `lager` edge) below and backlog cost (`restordre-fill`, `restordre` edge) above, on an `axis` baseline with a true zero. The final values are labelled directly at the right end. A `link` «Vis som tabell» sits under it.
- **Etterspørselsbånd (`demand-band`).** Debrief step 2 (`07-debrief.png`): a horizontal `lager-fill` band behind the customers' demand series. The label («Kundenes etterspørsel: 8») and the numbers on the band are `ink`, weight 600 (10.7:1). The band is the blue cue; the text is not.
- **Ordrestolper (`order-bars`).** One row per Role, Fabrikk at the top. Bars are `order-history`, and the viewer's own Role is `ink`. In each row, a red dot with «Uke n» marks the first order of 10 or more; a thin red diagonal joins the dots. Forsterkning is at the right in `figure-amplification`. The Rolle × Uke numbers sit underneath in the same columns, in `flow-*` steps.
- **Ukeskrubber (`scrubber`).** A thin track from «Uke 1» to the last Uke («Uke 36» in a Classic game). The unfilled part is `ink-muted` (5.2:1), the part up to the handle is `ink`, and the `ink` handle carries its «Uke 15» label above. Two outlined step buttons, − and +, sit at the ends of the track at `{spacing.tap-target-min}`.
- **Quizvalg (`quiz-option`).** Full-width rows.
  - Wrong: 1.4 px `restordre` border, with «Ditt svar, ikke riktig» in `restordre` at the right.
  - Correct: 1.4 px `ink` border with «Riktig».
  - The explanation follows as `body` text.
- **Interaktiv oppgave (`interactive-item`).** One graph over one value table, the same grammar as the game. Drawing items: an 8 px `ink` point per Uke joined by a 2 px `ink` line, over a value table with one outlined numeric cell per Uke. Unanswered Uker show an empty cell and no point, with «Ikke besvart» in `ink-muted` beside the row label. Invalid cells use the error state. «Fyll inn kolonnen» uses the value table alone (`09-alle-sider.png`, «Individuell test»).
- **Flagg (`flag-control`).** In the KI-vurdering, under each piece of feedback: a text button «Marker som feil» in `caption` `ink`, underlined. Flagged: «Markert. Faglærer ser det.» in weight 600, with the text button «Angre». No icon.

### Faglærer

- **Matrisevegg (`matrix-wall`).** One row per Class game and one column per Uke, with Netto lager in the matrix steps. Group headers read «Venter 4», «Pause 2», «Pågår 13» and «Ferdig, lavest kjedekost øverst 41». The near-Takeover row is tinted `restordre-fill`, with `ink` text and an `ink` underlined «Melding». The bottom rows hold «Median, Fabrikk» and «Kjedekost/uke, snitt». Text is never under 9 px.
  - **Cells.** A cell prints its signed number («−13», «8», «0») in `{typography.matrix-cell-min}` or larger when the number fits with 1 px to spare. Otherwise a below-zero cell prints only a true minus «−», centred, and other cells stay blank. Glyph and number follow the cell-text rule: `ink` on steps 1–2, `paper` on steps 3–4. Sign is therefore never carried by hue alone.
  - **Legend**, always visible above the wall in `caption`: swatches in step order with signed bins, «−35 og lavere · −34 til −20 · −19 til −10 · −9 til −1 · 0 · 1 til 9 · 10 til 19 · 20 til 34 · 35 og over», and the line «− i en celle: restordre (under null).» When the Celler filter shows Ordre or Kost per uke, the legend switches to the `flow-*` bins.
  - **«Vis i plenum»** renders larger cells with fewer columns, so numbers fit more often, and adds a caption in `body` under the wall: «Rødt: restordre, under null. Blått: lager, over null. Tallet i cellen er netto lager.» [ASSUMPTION: plenum cell size at least 2 × the laptop cell]
- **Oppdater automatisk (`switch`).** A Bryter at the top right of the Matrisevegg with the label «Oppdater automatisk» and the state word beside it. When off, the line «3 endringer siden 14:02» in `body` `ink` and a `button-secondary` «Oppdater» sit under it. «Oppdatert 14:02:15» in `caption` `ink-secondary` stays visible in both states.
- **Visningsbryter (`view-toggle`).** Toggle controls have two segments, styled as Valgknapper: the active one filled `ink` with `paper` text, the inactive one with an `ink-muted` border.
- **Veggfiltre (`wall-filters`).** Three filter groups above the Matrisevegg (Rolle, Celler, Status) as rows of text buttons in `caption`. The active filter is weight 600 and underlined; counts follow in `ink-secondary` («Pause 2»). No pills, no fills.
- **Varselbånd (`attention-band`).** A full-width `restordre-fill` band with `ink` text and the actions at the right («Send Melding» primary, «Pause spillet» and «Sett inn KI-spiller for Noah» secondary, the latter with its consequence in `caption` `ink` under the band text). Below 1024 px the actions wrap under the text at full width. «Pause spillet» opens the Spillstyring pause form in place under the band. Time stamps and reasons inside the band are `ink` or `ink-secondary`, never `ink-muted` or `restordre` (see Colors → Text on tints).
- **Meldingsskjema (`message-composer`).** As drawn in `09-alle-sider.png` («Melding til Noah, Spill 2»): the recipient as the `label` title, a multi-line `text-field`, a `button-primary` «Send Melding», and «Sendt tidligere: 3» in `caption`.
- **Filopplasting (`file-upload`).** In «Lag Klasse» (`02-laerer-klasse.png`): an outlined box with «Velg fil» before a file is chosen. After reading: the file name in `label` («ibe160-canvas-eksport.xlsx»), the summary «250 rader lest» in `body`, and the `link` «Bytt fil». The «E-postkolonne» selector under it is a native select styled as `text-field`, followed by its reason in `body` («Valgt fordi alle rader unntatt fire ser ut som adresser.»).
- **Kostnadsfordeling (`cost-distribution`).** One tick per finished game, a box for the middle half, the median labelled («Median 1 954») and last year as a dashed mark («Fjoråret 2 740»).
- **Trakt (`funnel`).** Horizontal bars in `order-history` with counts.
- **Datolinje (`date-line`).** A timeline with deadline ticks, and Labtimer as `lager` squares («Blå firkant: Labtime, Datalab A2.»).
- **Fordelingsforhåndsvisning (`allocation-preview`).** 60 columns × 4 Role rows in `bar-base`, with the selected game framed in `ink`.
- **Spillstyring (`button-primary`, `button-secondary`, `pause-control`, `ai-insert`).** On Spillinnsikt: a block under the four Seats, titled «Spillstyring» in `label`, with one action per line. Each action is a `button-secondary` with its consequence in `caption` `ink-secondary` directly above it, as `ai-insert`; «Start spillet» before the start is the block's one `button-primary`. Status lines («I rommet til 16:00. …», the pause line) are `body` `ink`, never a coloured fill. The pause form reuses `pause-control` with a `text-field` for date and time, the choice «Uten avtalt tid» and a `button-primary` «Ta pause til to. 19:00». Per-Seat «Sett inn KI-spiller for …» sits on each Seat row as `ai-insert`. On the Oversikt, the all-games actions are two `link`s in the header; their pages use the Meldingsskjema layout (title in `label`, list in `body`, one `button-primary`). Below 1024 px every action is full width. Spine-only, undrawn.
- **Tilrettelegging (`segmented-choice`, `text-field`, `button-secondary`).** A Studentside block titled «Tilrettelegging» in `label`, with its summary in `body` `ink` and a `button-secondary` «Endre tilrettelegging». The form in place has `segmented-choice` for «Mer tid før KI tar over», a `text-field` with its help line in `caption` `ink-secondary`, and a `button-primary` «Lagre tilrettelegging». No badge or icon marks the Student anywhere else. Spine-only, undrawn.
- **Fullføringsretting (`segmented-choice`, `text-field`, `button-secondary`).** A Studentside block titled «Fullføring» in `label`: one row per step with the step in `label` and the status in text («gjort», «ikke gjort») in `body` `ink`; the Klassespill share line in `body` `ink-secondary`; a correction mark («rettet av Bård 12. des.») in `caption` `ink-secondary` with the reason under it. Each row ends in a `button-secondary` («Rett Klassespill», «Gi oppfølgingsspill»). The form in place has `segmented-choice` «Gjort» / «Ikke gjort», a multi-line `text-field` «Begrunnelse» and one `button-primary`. Spine-only, undrawn.

### System

- **Tilkoblingslinje (`connection-notice`).** One line of `ink` `body` text on `paper` between two 1 px `ink-muted` rules, at the top of the content, full width («Frakoblet. …»). An optional `link` sits at its right («Prøv igjen»). Time stamps («Sist oppdatert 21:14») are `ink-secondary`. No colour fill, no icon. Used for offline, stale data and page errors.
- **Skjelett (`skeleton`).** Loading shows the layout that is coming: `hairline` table rules, `axis` axes and `ink-muted` row labels in the real columns, with no numbers and no marks. No spinners, no shimmer animation.
- **KI-merke (`ai-label`).** The text «KI-spiller» in a Seat row, and the prefix «KI-generert, kan ta feil:» before AI text. Plain text with no badge or icon.
- **Demodata-merke (`demo-label`).** «Demodata» in `caption` `ink-muted`, bottom left of a card or bottom right of a page.

## Do's and Don'ts

| Do | Don't |
|---|---|
| Put the graph over the table on one shared Uke axis, with a number under every mark | Show a chart without its numbers, or numbers on a different axis |
| Use blue for stock and holding cost, red for backlog and backlog cost, on every surface | Use red/green, or colour as the only carrier of status, Role or value |
| Draw the chain with upstream on the left: goods flow right, orders flow left | Mirror the chain on any surface, including the Debrief and the projector |
| Stop the time axis at nå + 4 during play | Draw an end, a week count or progress («11 av 36») |
| Use direct labels, a true zero, faint gridlines and a clear «Nå» | Use legend boxes where a direct label fits (the Matrisevegg is the one exception), truncated axes or 3D |
| Tell series apart by stroke, fill, marker and label, as with Netto lager and Posisjon | Separate two lines by colour alone |
| Show the `focus-ring` on every focusable control, with its `paper` gap | `outline: none` without the ring, or a ring that disappears on `ink` fills |
| Keep text on tints to `ink` or `ink-secondary`, and on dark steps to `paper` | `lager`, `restordre` or `ink-muted` text on any fill |
| Let tables scroll inside their own region, with sticky labels, when columns run out | Shrink table text to make columns fit |
| Use tabular figures in all columns and proportional only in the hero numbers | Mix figure styles inside a table |
| Keep white paper, hairlines and whitespace | Shadows, gradients, tinted panels, side-stripe borders, hard offsets |
| Keep text 13 px or larger on phone and 9 px or larger on the matrix wall, with a table view | Smaller text anywhere else |
| Write plain text labels for AI, Demodata and Simulert | Icons, emoji, badges, illustrations, mascots, metaphor worlds |
| Use one primary button per screen, labelled with its effect | «Spill»-style buttons, reward animation, exclamation marks |
