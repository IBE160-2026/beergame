# Validation Report — beergame (ØL-spillet)

- **DESIGN.md:** `DESIGN.md`
- **EXPERIENCE.md:** `EXPERIENCE.md`
- **Run at:** 2026-11-09

## Overall verdict

The pair is a strong contract for the core Student loop: Spill, Graf over tabell, Kjedebånd, Kostnad så langt and the Debrief. Every token reference resolves, every colour has a hex value, and the hidden-information, chain-direction and AI-disclosure rules are written down. Outside that loop the contract gets thin. About a dozen in-scope FRs have no IA surface, and several flows and surfaces have no states. There are no global loading, offline, error or permission patterns, and the irreversible order confirm has no failure path. One mockup conflict touching the issue #22 decision is not acknowledged, and nothing maps the English PRD glossary to the Norwegian UI terms. Architecture can start from the game loop now. Story development for setup, test, report and admin surfaces needs one more pass.

The accessibility review sharpens that picture rather than reversing it. The colours mostly pass: every text token clears 4.5:1 on paper and future-tint, the matrix step text passes, and the game screen never carries meaning by colour alone. The gaps are behavioural. There is no focus style, the order input's errors and Enter key are assumptions, the live Oversikt re-sorts under a screen reader, the Ukeskrubber has no slider semantics, and several charts have no table alternative. Two findings are critical: the 12-column week table cannot hold its 13 px floor at 320 px or at 200 % text, and the Individuell test's drawing item has no keyboard path, so a keyboard-only Student cannot finish a deadline-bound test. The reviewer's verdict is that the pair is not ready for a WCAG 2.1 AA claim.

After merging duplicates across the two reviewers: 2 critical, 15 high, 25 medium and 21 low findings. Three findings were reported by both reviewers and are counted once: the missing focus style (H3), the Ordrefelt error and submit-failure states (H5), and non-text contrast on `axis` (M2).

## Status etter retting (2026-11-09)

Kritiske og høye funn ble rettet i spinene etter at rapporten ble skrevet. Middels og lave funn er utsatt til [GitHub issue #26](https://github.com/IBE160-2026/beergame/issues/26). Hvert funn under har en **Status:**-linje.

| Status | Antall | Funn |
|---|---|---|
| Rettet | 16 | C1, C2, H1–H7, H9–H15 |
| Løst ved beslutning (memlog 2026-11-09) | 1 | H8 |
| Delvis rettet, resten i #26 | 2 | M2, M5 |
| Utsatt til #26 | 44 | M1, M3, M4, M6–M25, L1–L21 |
| Ikke bekreftet | 0 | — |

- Hver «Rettet» er stikkprøvekontrollert mot gjeldende DESIGN.md og EXPERIENCE.md, og statuslinjen peker på seksjonen der rettingen står. Dette er ikke en full ny gjennomgang.
- Linjereferansene i funnene (L123 osv.) peker til utkastet før retting. Etter rettingene og en redaksjonell gjennomgang (struktur og språk) er begge spinene `status: final`, DESIGN.md er på om lag 706 linjer og EXPERIENCE.md på om lag 745.
- Runde 2 av valideringen ligger i `validation-report-2.html` / `validation-report-2.md`.

## Category verdicts

- Flow coverage — adequate: UJ-1 to UJ-9 all present with protagonist, steps and climax; a dozen MVP FRs and two UJ-4 actions have no surface.
- Token completeness — adequate: every reference resolves and every ratio recomputes; no focus, pressed or disabled tokens.
- Component coverage — thin: about ten used components have no row; the Ordrefelt's empty, invalid and failed states are open.
- State coverage — thin: Spill and Debrief are well covered; whole surfaces and all global loading, offline, error and permission patterns are missing.
- Visual reference coverage — adequate: all mockups referenced and conflicts named, except «Posisjon» in `10-pedagogikk.png`.
- Bloat & overspecification — adequate: mostly lean; the cost picture is specified four times and fixture values read as rules.
- Inheritance discipline — thin: sources and UJ headings resolve; no PRD-to-UI glossary, and P1–P8 / stance codes live only in working files.
- Shape fit — strong: canonical order, all defaults present, every invented section load-bearing.
- Accessibility (reviewer) — not ready for a WCAG 2.1 AA claim: colours mostly pass, the gaps are behavioural; 2 critical, 8 high, 11 medium, 8 low as filed.

## Findings by severity

IDs below are this report's own numbering. Where an accessibility finding is cited, its original ID is given as «a11y H4» and so on.

### Critical (2)

**C1 · [Accessibility (reviewer)]** — Week table: 12 columns cannot meet the 13 px floor at 320 px or at 200 % text (a11y C1) (§ DESIGN Layout & Spacing, Typography floors; EXPERIENCE Accessibility Floor; vlib.gtable)

**Status:** Rettet — se DESIGN.md → Layout & Spacing («Graf over tabell at narrow widths and large text») og EXPERIENCE.md → Component Patterns → Graf over tabell (tabellsemantikk)

At 360 px the table gets 21 px per column and «−13» at 13 px barely fits. At 200 % text only about 6 of the 12 columns fit. At WCAG's 320 px reflow width the columns are 17.7 px, so «−13» does not fit even at 100 %. The mockup library "solves" this by shrinking cell text toward 9 px, and a developer who copies it ships text that ignores zoom and breaks the spine's own floor. "The table may scroll inside itself" is an [ASSUMPTION], and if only the table scrolls, the graph loses its shared x-axis, which is the core P1 grammar. Nothing specifies that both scroll together. WCAG 1.4.4, 1.4.10.

Fix: Make the graph and table one horizontally scrollable unit with one scroll position, «Nå» in view on load, a sticky row-label column and a visible scroll affordance (the 1.4.10 two-dimensional exception). Alternatively, narrow the window to nå − 3 … nå + 4 when columns fall under about 2.2 em. Ban auto-shrinking below the floor. Build the table as an HTML `<table>` in relative units with `<th scope="col">` per Uke and `<th scope="row">` per row, not SVG text. Add a build check at 320 px and at 200 % text.

**C2 · [Accessibility (reviewer)]** — Individuell test: the drawing item has no keyboard or non-drawing alternative (a11y C2) (§ EXPERIENCE UJ-6 step 4; Accessibility Floor)

**Status:** Rettet — se EXPERIENCE.md → Component Patterns → Interaktiv oppgave (verditabell, tastatur) og DESIGN.md → Components → Game end and Debrief (Interaktiv oppgave)

A keyboard-only or screen-reader Student reaches a required, deadline-bound test step and cannot draw the bakery stock. The spine only asserts that Interactive items are "fully keyboard-operable (FR-80)" and gives no mechanism, so that Student cannot complete the test. WCAG 2.1.1, 2.5.1 (freehand drawing is a path-based gesture), 1.1.1. Related: the rubric finds no component row for Interactive items (H4) and notes the item is undrawn (L7).

Fix: Back every drawing item with an equivalent value table, one numeric input per Uke, which the drawing writes into and which redraws the curve. Arrow keys move a point by one unit and Tab moves to the next Uke. A screen-reader user answers through the table alone. Scoring reads the table values, so both input modes are equal.

### High (15)

**H1 · [Flow coverage]** — In-scope MVP FRs have no IA row, no flow and no state (§ EXPERIENCE IA L45–67; PRD §8.1)

**Status:** Rettet — se EXPERIENCE.md → Information Architecture (spine-only-rader for FR-4, FR-10, FR-21, FR-52, FR-59/60, FR-61, FR-75, FR-78, FR-81, FR-82, FR-88) og State Patterns

FR-4 password reset; FR-10 co-lecturer and Assistant lecturer invitations; FR-21 Student choice of game and Seat; FR-52 excluding questions and changing Item weights; FR-59/FR-60 ZIP and Completion export (named in UJ-8 step 5, no surface); FR-61 AI assessment off; FR-75 Student data access; FR-78 Effort level; FR-81 Scoring guide editing; FR-82 Control test; FR-88 Game data export. The IA ranges «FR-11–FR-20» and «FR-51–FR-58» imply some of these without placing them. Stories for them have no UX contract.

Fix: Add IA rows, or one-line entries in an existing row, naming the surface and owner. Alternatively list them under Open Questions as "spine-only, no layout yet", as the memlog does for Admin.

**H2 · [Flow coverage]** — UJ-4 rests on two Student actions with no defined control: setting a Pause and putting in a KI-spiller (§ EXPERIENCE UJ-4 step 9; State Patterns L147–149; Open Question 5)

**Status:** Rettet — se EXPERIENCE.md → Component Patterns → Seats and status (Pausevalg, Sett inn KI-spiller) og DESIGN.md → Components → Seats and status

Setting a Pause with an agreed time (FR-89) and putting in a KI-spiller for an absent Seat after the agreed time or Inactivity limit (FR-37/FR-89) have no control, conditions or copy. Only the resulting rows are specified. Open Question 5 lists the Pause as undrawn; the insert-AI action is listed nowhere.

Fix: Add a Component Patterns row for each action covering trigger, eligibility, confirmation copy and who sees what, and reference them from UJ-4.

**H3 · [Token completeness + Accessibility (reviewer)]** — No focus ring, and no hover, pressed or disabled states (§ DESIGN frontmatter, Components L159–291, L401–452; EXPERIENCE Accessibility Floor L203–212)

**Status:** Rettet — se DESIGN.md → Components → Interaction states (Fokusring, pressed, disabled)

EXPERIENCE defines focus order, focus moves and full keyboard operability (FR-80, WCAG 2.4.7). DESIGN defines no focus ring and no hover, pressed or disabled appearance for `button-*`, `order-input`, `quiz-option`, `view-toggle`, `segmented-choice`, `switch` or `link`. The accessibility reviewer adds the failure: the "no shadows, no chrome" posture invites `outline: none`, and default browser rings are unreliable on `ink`-filled buttons and toggle segments, on the `restordre-fill` Varselbånd, inside dark matrix steps and on the `ink` «24» Din ordre cell. Keyboard users in the lab lose their place between «Bekreft ordre på 24» and the − / + segments. WCAG 2.4.7, 1.4.11.

Fix: Add a `focus-ring` token: 2 px solid `{colors.ink}`, 2 px offset with a `paper` gap (14.6:1 on `paper`, 10.5:1 on `restordre-fill`, 13.3:1 on `future-tint`). Use `:focus-visible` and never remove the outline without a replacement. For table cells and wall rows, use an inset 2 px `ink` frame. Add the ring, plus `disabled` and `pressed` keys, to every interactive component.

Sources: rubric §2 Token completeness (high) · accessibility H1 (high)

**H4 · [Component coverage]** — About ten components used in flows, states or mockups have no row in either spine (§ EXPERIENCE State Patterns L140, L109, L121, L153, L240, L359; UJ-2, UJ-6, UJ-8; 09-alle-sider.png)

**Status:** Rettet — se DESIGN.md → Components (Topplinje, Spillkort, Filopplasting, Veggfiltre, Meldingsskjema, Interaktiv oppgave, Flagg, Etterspørselsbånd, Kjedens kostnad over tid) og EXPERIENCE.md → Component Patterns

The Hjem game card «Spillet venter på deg» with its mini graph-over-table; the phone header with Uke, Rolle/Spill and a tappable Totalkostnad; file upload with «Bytt fil» and the «E-postkolonne» selector; the Matrisevegg filters for Rolle, Celler and Status; the Meldinger composer; Interactive items and the «Fyll inn kolonnen» table input; the Student Pause control and insert-KI-spiller action; the KI-vurdering flag control; the Debrief step 2 demand band; and the «Kjedens kostnad over tid» chart.

Fix: Add a row on both sides for each, or state which existing component each reuses, for example "Hjem card = `net-graph` + `week-table`, 4 columns".

**H5 · [Component coverage + State coverage + Accessibility (reviewer)]** — Ordrefelt: empty, invalid, Enter and failed submit are unspecified for the only irreversible Student action (§ EXPERIENCE Component Patterns L110–111, Interaction Primitives L172, State Patterns; DESIGN order-input)

**Status:** Rettet — se EXPERIENCE.md → Component Patterns → Ordrefelt og State Patterns → Student game (Submit failed, Timed out, Offline)

The empty Ordrefelt shows a secondary «Bekreft ordre», while Knapper says secondary buttons never commit irreversible state, and nothing says whether it is disabled or confirms 0. Inline rejection copy, numeric `inputmode` and "typing plus Enter confirms" on laptop are all [ASSUMPTION], so one keystroke can send an order that cannot be undone. The allowed maximum is never shown, `order-input` has no error border (unlike `text-field`), and nothing says whether an error is announced. If «Bekreft ordre på 24» fails or times out, the spine does not say whether the order is locked, retried or still editable. The accessibility reviewer adds that `type="number"` lets a mouse wheel silently change the focused value before Enter. WCAG 3.3.1, 3.3.2, 3.3.3, 4.1.3.

Fix: Keep «Bekreft ordre» inert (showing the error) until a valid whole number is entered, and state whether 0 is a valid explicit entry. Write the copy now: help text «Hele tall fra 0 til {maks}.» and error «Skriv et helt tall fra 0 til {maks}.» in `restordre`. Add `order-input.border-error` in `restordre` (5.5:1). Wire `aria-invalid`, `aria-describedby` and `role="alert"`. Use `type="text" inputmode="numeric" pattern="[0-9]*"`. Enter moves focus to the button and never submits. Name the − / + segments «Én færre» / «Én flere» and announce the value. Add Spill «Submit failed» and «Offline» rows: order kept locally, explicit retry, never a silent lock. For the Individuell test's single submission, add a review step listing unanswered items before «Lever» (3.3.4).

Sources: rubric §3 Component coverage (high, empty-state button; medium, Enter confirms) · rubric §4 State coverage (high, submit failure) · accessibility H4 (high)

**H6 · [State coverage]** — No global offline or connection-lost pattern, and the live Oversikt has no stale indicator (§ EXPERIENCE State Patterns L151, L165)

**Status:** Rettet — se EXPERIENCE.md → State Patterns → All surfaces (Offline) og Faglærer live (Connection lost or stale)

«Reload or new device» covers resume only. The Oversikt promises live updates within 5 s but has no stale or disconnected state, so a lecturer cannot tell a quiet class from a dead connection. The order-specific half of this rubric finding is merged into H5.

Fix: Add a global «Offline» row and an Oversikt «Connection lost» row with a visible stale indicator.

**H7 · [State coverage]** — Whole surfaces have no State Patterns rows (§ EXPERIENCE State Patterns L131–167 against IA L47–67)

**Status:** Rettet — se EXPERIENCE.md → State Patterns (Account and access, Student game, After the game, Test and assessment, Faglærer live, Admin)

Logg inn (wrong password, deactivated user FR-3, password reset FR-4); Startoppgave (wrong answer, feedback, the optional final question FR-85); Replay and Replay-gjennomgang (locked, in progress, finished, LLM down); Individuell test (locked, autosave failed, submitted, auto-submitted at Testfrist, which appear only inside UJ-6); Alle spill side om side (locked until own Debrief and Play deadline, FR-86); Spillinnsikt, Studentside, Klasserapport, Tverrklasse-statistikk (empty, including "no earlier year"); Admin.

Fix: Add at least locked, empty and error rows per surface.

**H8 · [Visual reference coverage]** — Unacknowledged mockup conflict: «Posisjon» drawn in the Class-game Kjedebånd (§ 10-pedagogikk.png; DESIGN L377; EXPERIENCE L109, L224; UJ-5)

**Status:** Løst ved beslutning (memlog 2026-11-09): Posisjon vises som graflinje og tabellrad både i Klassespill og Replay, så konflikten med «Posisjon n» i 10-pedagogikk.png faller bort (DESIGN.md → Components → Game screen → Graf over tabell).

The sheet draws «Posisjon 24», «Posisjon 3», «Posisjon 42» and «Posisjon 37» in the Class-game Kjedebånd at Uke 5, 11, 18 and 29, and DESIGN cites it for the chain-band scale rule. The spine's ban reads "no Posisjon row", which leaves the band label open. A consumer building the band from the cited sheet would show the sum that issue #22 and stance 1 hide.

Fix: Add to Kjedebånd in both spines: "Never shows Posisjon in the Klassespill; the «Posisjon n» labels in `10-pedagogikk.png` are superseded (Replay only)."

**H9 · [Inheritance discipline]** — No glossary maps PRD terms to UI strings (§ PRD §3; PRODUCT.md; EXPERIENCE Foundation)

**Status:** Rettet — se EXPERIENCE.md → Foundation → Terms

The PRD glossary is English and PRODUCT.md fixes only eight Norwegian terms. The spines mix Norwegian UI terms (Faglærer, Klasseøkt, Labtime, Forklaring, På vei, Spillinnsikt, Forsterkning, Spillfrist, Testfrist), English glossary terms (Seat, Class game, Takeover, Interactive item, Detected patterns, Indicative letter) and hybrids («Guided Uke»). They also introduce terms no source defines: Netto lager, Posisjon, Kjedekost, Kjedebånd. Architecture and story authors work from PRD nouns.

Fix: Add a Terms table in EXPERIENCE Foundation with the columns PRD term → UI string → definition or note, including the new terms.

**H10 · [Accessibility (reviewer)]** — Matrisevegg «Vegg» shows the sign of Netto lager by hue alone, with luminance-matched steps and no legend (a11y H2) (§ DESIGN Colors (Matrix steps), Components Matrisevegg; 08-laerer-oversikt.png; «Vis i plenum»)

**Status:** Rettet — se DESIGN.md → Components → Faglærer → Matrisevegg (fortegn «−», alltid synlig tegnforklaring, «Vis i plenum»-tekst) og Colors

Red and blue steps are matched in luminance (1.01–1.10:1). The wall as drawn prints no numbers, so DESIGN's claim that "the cell always prints its signed number" is false. On a washed-out projector, in greyscale, or for anyone with reduced colour vision, backlog and stock cells of the same size look identical. The table toggle rescues the lecturer at the laptop; nothing rescues the plenum audience. There is no legend for the bins, so magnitude cannot be decoded at all. WCAG 1.4.1, 1.1.1, and the PRODUCT commitment "status never by colour alone".

Fix: Correct the DESIGN claim. Add a non-hue cue for sign, such as a 1 px `paper` hatch or inner bottom bar on below-zero cells, or a red ramp that also differs in lightness. Add a signed bin legend («−35 … −1 · 0 · 1 … 35+»). Give «Vis i plenum» a caption in words («Rødt: restordre under null. Blått: lager over null.») and hatching on by default.

**H11 · [Accessibility (reviewer)]** — Several charts have no text or table alternative, despite the spine's claim that every chart has one (a11y H3) (§ DESIGN cost-panel, cost-distribution; EXPERIENCE Cost picture; mockups 06 F, 07, 08)

**Status:** Rettet — se EXPERIENCE.md → Accessibility Floor (tabell over alternativer per graf)

«Totalkostnad over tid» (where it is shown, «Sum, hele kr» is removed, so the cumulative series has no table at all); «Kjedens kostnad over tid»; `cost-distribution` (41 ticks, box, median, «Fjoråret», no values); «Snitt per ferdig spill, per Rolle» and the Delt skjerm cost bars, where the lager/restordre split is carried by bar length and colour alone; `date-line` and `allocation-preview`, which the lecturer acts through; the Hjem mini graph and the Debrief step 1 colour strip. WCAG 1.1.1, 1.4.1, 1.3.1.

Fix: Add an Accessibility Floor table naming the alternative for each chart component. Put Lager / Restordre columns beside each Role total. Restore cumulative cost as a «Sum, kr» row in «Alle rader». Give `cost-distribution` a «Vis som tabell» link and a text summary («Median 1 954, midterste halvdel 1 500–2 600, fjoråret 2 740»). Mark the Hjem mini graph `aria-hidden` with a text summary.

**H12 · [Accessibility (reviewer)]** — Signal-coloured or muted text on the fill tints fails 4.5:1, and nothing forbids it (a11y H5) (§ DESIGN Colors; 07-debrief.png step 2; 08-laerer-oversikt.png)

**Status:** Rettet — se DESIGN.md → Colors → «Text on tints» og Components → Etterspørselsbånd

On `lager-fill` / `restordre-fill`: `ink-muted` 3.78 / 3.72, `lager` 4.07 / 4.01, `restordre` 4.04 / 3.98, `order-history` 3.27 / 3.22. The climax label in Debrief step 2 («Kundenes etterspørsel: 8», `lager` on `lager-fill`, about 14 px bold) fails. So does the «Melding» link in the most urgent wall row, at 9 px. Any `ink-muted` time stamp or `restordre` reason in the Varselbånd would fail too. WCAG 1.4.3.

Fix: Add a rule to DESIGN Colors: on `lager-fill`, `restordre-fill` and `net-*-1/2`, text is `ink` or `ink-secondary` only, and links on a tinted row or band use `ink` with an underline. Set the demand label in `ink` 600 and let the band be the blue cue.

**H13 · [Accessibility (reviewer)]** — Reflow is specified at 360 px, but WCAG 1.4.10 tests at 320 CSS px and the chain-band check runs at 390 (a11y H6) (§ EXPERIENCE Responsive & Platform, Accessibility Floor; DESIGN Layout; vlib.py PHONE_CHAIN)

**Status:** Rettet — se DESIGN.md → Layout & Spacing (Widths, reflow-min 320 px) og EXPERIENCE.md → Accessibility Floor (Reflow)

A Student at 400 % browser zoom on a laptop, or on a 320 px-class phone, gets the chain band, the order input and the cost panel at 320 px. The pipe at a fixed 1.4 px per unit has never been checked at 360, let alone 320. Uke 15 «På vei 56 + 13» plus an overdue box (06 E) is the known worst case. WCAG 1.4.10.

Fix: Set 320 CSS px as the reflow target for every non-tabular Student component and keep 360 as the design floor. Derive chain-band units per pixel from the available width and run the build check at 320 and 360. List which components rely on the two-dimensional exception (week table, matrix, order-bars) and which must reflow.

**H14 · [Accessibility (reviewer)]** — The live Oversikt auto-updates and re-sorts with no pause, so screen-reader and keyboard users lose their place (a11y H7) (§ EXPERIENCE State Patterns (Oversikt Live), Matrisevegg, Visningsbryter; UJ-7 step 5)

**Status:** Rettet — se EXPERIENCE.md → Component Patterns → Faglærer (Matrisevegg, Oppdater automatisk)

A lecturer using NVDA reads row 23 of «Vis som tabell». A game finishes, jumps from «Pågår» to «Ferdig» and re-sorts by kjedekost, and the virtual cursor now sits on a different game. Keyboard focus on a «Melding» link can be destroyed by the re-render. Which changes are announced is undefined: announcing every 5 s update is unusable, and announcing none hides the new Varselbånd. WCAG 2.2.2, 2.4.3, 4.1.3.

Fix: Add an «Oppdater automatisk» switch, on by default, with a polite counter while frozen («3 endringer siden 14:02, Oppdater»). Freeze automatically while focus is inside the table. Keep focus on the same game ID across re-renders. Announce only Varselbånd changes and headline counts, politely, at most once a minute.

**H15 · [Accessibility (reviewer)]** — Ukeskrubber: keyboard support is only an assumption, with no slider semantics and no announced result (a11y H8) (§ EXPERIENCE Component Patterns (Ukeskrubber), Accessibility Floor; DESIGN scrubber track)

**Status:** Rettet — se EXPERIENCE.md → Component Patterns → Ukeskrubber og DESIGN.md → Components → Ukeskrubber

A screen-reader Student in group Debrief step 3 hears an unnamed control. Moving it changes the whole chain and the dashed marker, but nothing is announced, so the step's teaching point ("1,8× grows to 7,6×") is visual-only. The unfilled track is `axis`, 1.61:1 against paper. WCAG 2.1.1, 4.1.2, 4.1.3, 1.4.11.

Fix: Promote the assumption to a rule: `role="slider"`, `aria-valuemin=1`, `aria-valuemax=36`, `aria-valuetext="Uke 15"`, arrows ±1, PageUp/PageDown ±4, Home/End. After a 300 ms debounce, update a polite live region with the chain as text. Draw the unfilled track in `ink-muted` (5.16:1). Add − / + step buttons as a non-drag alternative, and say who controls the scrubber on «Delt skjerm».

### Medium (25)

**M1 · [Flow coverage]** — UJ-6 departs from the PRD journey (§ EXPERIENCE L371–377; PRD UJ-6, FR-52)

**Status:** Utsatt til #26

The PRD has two Interactive items (draw the bakery inventory, work out the extra units) and three long answers. The spine has one Interactive item, «Fyll inn kolonnen» and one «Langsvar».

Fix: Align with PRD UJ-6 / FR-52, or record the reduction in the memlog.

**M2 · [Token completeness + Accessibility (reviewer)]** — Contrast is stated only against paper, and `axis` (1.6:1) still carries meaning (§ DESIGN L308–321, L433, L450; scrubber, step-list, net-graph, cost-field, switch; vlib.Doc.button())

**Status:** Delvis rettet, resten i #26: Ukeskrubber-sporet og av-tilstanden til bryteren er flyttet til ink-muted; øvrige bruk av axis gjenstår.

Pairs the design depends on are unstated: `ink` on `restordre-fill` 10.5, the `button-secondary` border on `restordre-fill` 3.7, `lager` on `future-tint` 5.1. Non-text marks below 3:1 have an undecided role: the true zero line and the Ukeskrubber track in `axis` (1.6:1) and allocation-preview bars in `bar-base` (1.8:1). The accessibility reviewer adds the `step-list` later-dot (with «Stegene greyed out» on Hjem carrying no text), the dashed unknown-arrival and overdue boxes (1.47:1 on tint), a `switch` with no off-state token, and `vlib.Doc.button()` still drawing secondary borders at 1.6:1, so regenerated mockups will contradict the spine. WCAG 1.4.11.

Fix: Add the missing pairs to the Colors table. Move the scrubber track, zero line, baselines and dashed box outlines to `ink-muted`. Give later steps the text «låst» or «åpnes etter Debrief» with a hollow `ink-muted` ring. Add `switch.off` in `ink-muted` plus a state word. Update `vlib.button()` to `INK3`.

Sources: rubric §2 Token completeness (medium) · accessibility M1 (medium)

**M3 · [Token completeness]** — Some values are off-token or unresolvable (§ DESIGN L169–291, L422)

**Status:** Utsatt til #26

The «Alle rader, Uke 11» title is "24/700 (as drawn)" with no typography token (`title-phone` is 30, `headline` 22). Stroke widths of 1.1, 1.4, 1.5 and 2 px are hard-coded with no stroke scale. Composite values such as `'1px {colors.ink-muted}'` will not flatten in a strict resolver.

Fix: Map the title to an existing role or add `title-screen`. Add `stroke.hairline/regular/strong`. Split border values into `*-width` and `*-color` keys.

**M4 · [Component coverage]** — Lecturer chart names differ between the spines, breaking the "same name" rule (§ DESIGN L403, L446; EXPERIENCE L129)

**Status:** Utsatt til #26

DESIGN says `cost-distribution`, `funnel`, `date-line`, `allocation-preview`; EXPERIENCE says Kostnadsfordeling, Trakt, Datolinje, Fordelingsforhåndsvisning.

Fix: Use the Norwegian names in DESIGN.md with the token keys in parentheses, as the other components do.

**M5 · [Component coverage]** — Klasseøkt has two committing actions against "one primary button per screen" (§ DESIGN L467; EXPERIENCE L111, L129, L332 (UJ-3 step 6))

**Status:** Delvis rettet, resten i #26: Enter-oppførselen i Ordrefelt er definert (via H5); to forpliktende knapper i Klasseøkt gjenstår.

«Bekreft fordeling» and «Lagre Klasseøkt» both commit. The Enter-to-confirm half of this rubric finding is merged into H5.

Fix: Say which button is primary, or make Fordeling its own screen.

**M6 · [Component coverage]** — Uke-overgang has behaviour rules but no motion spec (§ EXPERIENCE L115, L176, L210; DESIGN Components)

**Status:** Utsatt til #26

≤ 2 s, skippable, never blocks input and reduced motion are set. What moves, the duration and the easing are not, and there are no motion tokens.

Fix: Add a motion note under Components → Uke-overgang: now-line slide, column fill, ≤ 600 ms, linear or ease-out.

**M7 · [State coverage]** — No loading pattern, and no pending state for LLM-generated content (§ EXPERIENCE State Patterns; NFR-1)

**Status:** Utsatt til #26

NFR-1 sets a 3 s budget on 4G, but there is no cold-load pattern. The Debrief step 4 AI line, KI-vurdering "not ready yet" and the Replay walkthrough have no pending state.

Fix: Add one global loading rule (table skeleton in the same columns, no spinners over 1 s) and one AI-pending rule.

**M8 · [State coverage]** — No permission-denied pattern (§ EXPERIENCE State Patterns; FR-5)

**Status:** Utsatt til #26

A Student opening a Faglærer URL, an Assistant lecturer reaching a create or delete action, and an expired session are all undefined.

Fix: Add a global row.

**M9 · [State coverage]** — Spill and Hjem have specific state gaps (§ EXPERIENCE L123; FR-12, FR-22; issue #25)

**Status:** Utsatt til #26

«Class game not started», where the first Student presses start; the Student-facing view of a Faglærer-initiated pause; a capacity-limited Seat holding stock and backlog at once; Hjem when the game is paused, finished with the Debrief open, or the test is open.

Fix: Add rows and mark undrawn ones [ASSUMPTION].

**M10 · [Visual reference coverage]** — All 10 `.svg` mockups are orphans (§ mockups/; DESIGN preamble)

**Status:** Utsatt til #26

Neither spine says whether the SVGs are the vector source with the same content as the PNGs, or which format to measure from.

Fix: Add one line to DESIGN.md's preamble: "Each PNG has an SVG twin with identical content; measure from the SVG."

**M11 · [Bloat & overspecification]** — The cost picture is specified in four places (§ DESIGN cost-panel L423–427; EXPERIENCE L114, L118, L225, L230–251)

**Status:** Utsatt til #26

DESIGN `cost-panel`, the Component Patterns rows «Kostnad så langt» and «Kjedens regning», the Hidden information «Cost» row and the Cost picture section. Kjedens regning appears in three. These copies will drift.

Fix: Keep the visual spec in DESIGN.md and the behaviour once in Component Patterns. Cut Cost picture to the cross-surface rules: rates binding, who sees what, Faglærer-only sorting.

**M12 · [Bloat & overspecification]** — Fixture values read as product rules (§ EXPERIENCE L142, L232, L244; DESIGN L380, L411)

**Status:** Utsatt til #26

«Restordre costs 1,00 and Lager 0,50», "the order is fixed at 4" in Veiledet uke, «Restordre er 60 % av kjedens regning …» and "fits the phone in all 36 Uker". FR-12 makes costs, Guided Weeks, demand and the number of Weeks configurable, so a consumer may hard-code them.

Fix: Mark them as Classic defaults bound to Game settings, and template the copy («Restordre er {andel} % …»).

**M13 · [Inheritance discipline]** — «Assistant» in the Oversikt IA row matches neither the glossary nor the UI (§ EXPERIENCE L65; 09-alle-sider.png)

**Status:** Utsatt til #26

The glossary term is "Assistant lecturer" and the drawn UI string is «Assistent».

Fix: Use the mapped pair.

**M14 · [Inheritance discipline]** — Component names drift into English aliases (§ DESIGN L365–381; EXPERIENCE L171–175, L192–208, L219)

**Status:** Utsatt til #26

«chain band», «order input», «matrix wall», «Debrief scrubber» and «the wall» appear in DESIGN Layout, Interaction Primitives, Accessibility Floor and Hidden information.

Fix: Use the Component Patterns name everywhere.

**M15 · [Inheritance discipline]** — P1–P8 and stance 1–3 are load-bearing but undefined in the spines (§ EXPERIENCE L54, L77, L109, L223–225, L266–273; DESIGN L300)

**Status:** Utsatt til #26

P1–P8 drive the Debrief Principle column and Open Question 2; stance 1/2/3 drive hidden-information rules. Both are defined only in BRIEF.md (a working file) and the memlog. DESIGN defines P1 alone.

Fix: Inline an 8-row principle table and a 3-row stance table, or link to them by heading.

**M16 · [Accessibility (reviewer)]** — Status-message coverage is partial, and focus after the week advance is undefined (a11y M2) (§ EXPERIENCE Accessibility Floor)

**Status:** Utsatt til #26

Missing: order-input errors; «Ordren på 24 er sendt»; Pause start and end; «KI-spiller har bestilt for deg.» and the reclaim confirmation; «Uke 12 åpner» while the page is open; Lag Klasse read results; the results of «Send 246 Invitasjoner», «Lagre Klasseøkt» and «Bekreft fordeling»; quiz feedback; test autosave and auto-submit; wall filter counts. After the advance, focus sits on a waiting message that disappears. WCAG 4.1.3.

Fix: Add a table to the Accessibility Floor: event → region (`status` polite / `alert`) → copy → focus target. After the advance, move focus to the «Uke 12» heading, not into the order input (that would open the phone keyboard).

**M17 · [Accessibility (reviewer)]** — The Debrief auto-advances when others submit and swaps content under the reader (a11y M3) (§ EXPERIENCE Debrief sequence, step 1)

**Status:** Utsatt til #26

A screen-reader Student is reviewing the Forklaring. Jonas sends, step 2 replaces the content, and the reading position is gone. WCAG 2.4.3, 3.2.x, 4.1.3.

Fix: Unlocking announces «Avsløringen er åpen» politely and enables «Gå til steg 2»; it never swaps content under the user. On step change, focus the step's `h2`. Put step headings in a navigable list with `aria-current="step"`.

**M18 · [Accessibility (reviewer)]** — Focus order, bypass and dialog behaviour are undefined beyond the phone game screen (a11y M4) (§ EXPERIENCE Accessibility Floor)

**Status:** Utsatt til #26

On the laptop Labtime layout the left table (Uke 1 to nå + 4, 9 rows) precedes the order input; focusable cells mean hundreds of Tab stops with no skip link. Wall order and Debrief step order are unspecified. What «Melding» and «Send Melding» open is undefined, a possible trap with no Esc or return-focus rule. «Alle rader og kostnad» has no initial-focus rule. WCAG 2.4.3, 2.4.1, 2.1.2.

Fix: Table cells are not focusable. Add a skip link «Gå til ordren». Specify wall and Debrief order. Any opened panel is a route (Back works) or a modal with focus trap, Esc and return focus. «Alle rader» opens with focus on its `h1`.

**M19 · [Accessibility (reviewer)]** — Red and blue are luminance-identical, so print, greyscale and projection lose the cost split (a11y M5) (§ DESIGN Colors (lager vs restordre 1.01:1, fills 1.02:1); NFR-6 PDF Studentrapport)

**Status:** Utsatt til #26

Mitigated on the game screen, where the Netto lager sign disambiguates. Not mitigated in `cost-field`, `chain-bill` split bars, the key chips, «Totalkostnad over tid», the Delt skjerm bars, or the PDF Studentrapport that Students will print in black and white. WCAG 1.4.1.

Fix: Give restordre a structural cue wherever the two are adjacent without numbers: fixed stack order with a 1.5 px gap and a first-occurrence label, or a fine hatch. Require the PDF to print numbers beside every split bar, and spell legend chips in stack order.

**M20 · [Accessibility (reviewer)]** — Fixed pixel row heights and widths will clip text under text spacing and zoom (a11y M6) (§ DESIGN row-phone 20, row-laptop 26, row-label-phone 76, control-height-phone 50, order-input-height 54)

**Status:** Utsatt til #26

With text-spacing overrides, «Netto lager», «Restordrekostnad» and «Ordre inn» overflow the 76 px label column, and 26 px text clips in a 20 px row. WCAG 1.4.12, 1.4.4.

Fix: State these as minimums (`min-height`, `min-width`); rows grow with content and the label column may widen or wrap. Test with the text-spacing bookmarklet at 360 px.

**M21 · [Accessibility (reviewer)]** — Selected state and control semantics are missing (a11y M7) (§ DESIGN quiz-option, view-toggle, segmented-choice, switch; 08 filters; EXPERIENCE Quizvalg)

**Status:** Utsatt til #26

`quiz-option` has idle, correct and wrong but no selected-before-submit state, so a Student cannot see or hear which answer is chosen. Toggle and filter state is not exposed to assistive technology. WCAG 4.1.2, 1.4.11, 1.4.1. Pairs with H3's missing pressed/disabled keys.

Fix: Add `quiz-option.border-selected` in `ink` plus a filled radio dot, as native radios in a `fieldset` / `legend`. Toggles and segmented choices are a radio group or `aria-pressed`; the switch is `role="switch"` with `aria-checked` and a state word; filters expose `aria-pressed`.

**M22 · [Accessibility (reviewer)]** — Target size is committed only for "primary controls" (a11y M8) (§ DESIGN tap-target-min; EXPERIENCE Accessibility Floor)

**Status:** Utsatt til #26

The − / + segments have no width. «Lukk», «Hopp over», «Alle rader og kostnad» and «Kostnad så langt» are 13–15 px text links; the tappable Totalkostnad has no size; «Ta tilbake setet» at 38 px is an assumption. On the wall, «Melding» links are 9 px text in about 10 px rows. WCAG 2.5.5 (AAA in 2.1; 2.5.8 is AA in 2.2) and the product's own commitment.

Fix: 44 × 44 px minimum hit area for every Student touch target, links included. − / + at least 54 × 54 px. On the wall, move «Melding» and row-open actions to the table view, or give them at least 24 × 24 px with spacing.

**M23 · [Accessibility (reviewer)]** — Fordelingsforhåndsvisning and Datolinje are interactive but specified as read-only charts (a11y M9) (§ EXPERIENCE Component Patterns; UJ-3 step 4)

**Status:** Utsatt til #26

A keyboard-only lecturer cannot select game 17 among 60 unlabelled columns, or check dates drawn only on the timeline. WCAG 2.1.1, 1.1.1, 4.1.2.

Fix: Columns are buttons with names («Spill 17»), arrow-key roving and the four names in a live region, plus a list of all games as the alternative. The Datolinje mirrors labelled date inputs and a list of Labtimer; its legend uses shape, not colour («Firkant: Labtime»).

**M24 · [Accessibility (reviewer)]** — Screen-reader pronunciation of Norwegian number formatting is untested (a11y M10) (§ DESIGN Typography (U+2212, space thousands separator, «×»))

**Status:** Utsatt til #26

Some voices skip U+2212, so «−13» is read as «13» and backlog becomes stock. «2 266,00» can be read as «2» and «266,00». «7,6×» can be read as «7,6 multiplikasjonstegn».

Fix: Use U+202F between thousands groups. Test NVDA, JAWS, VoiceOver and TalkBack with nb voices. Add visually hidden text where needed («minus 13», «7,6 ganger»), and put this in the acceptance criteria for the table alternative.

**M25 · [Accessibility (reviewer)]** — 9 px matrix text is illegible when projected and may not zoom (a11y M11) (§ DESIGN matrix-cell-min; «Vis i plenum»)

**Status:** Utsatt til #26

At 1440 px projected to about 3 m, 9 px is about 2 mm per character, so the plenum audience gets colour only (see H10). If the wall is canvas or fixed-px SVG, browser zoom does not enlarge it (1.4.4).

Fix: The wall scales with browser zoom. «Vis i plenum» renders larger cells with fewer columns, or carries H10's legend, hatching and caption.

### Low (21)

**L1 · [Flow coverage]** — UJ-9 has no edge or failure path, and UJ-3 has no failure path (§ EXPERIENCE L323–334, L405–412)

**Status:** Utsatt til #26

For example, the first Class session with no earlier year for Tverrklasse-statistikk, or a Klasseøkt saved with out-of-range or warned settings.

Fix: Add one line each.

**L2 · [Token completeness]** — `matrix-wall` maps the binned scales to step 1 only (§ DESIGN L241–246 vs L327–332)

**Status:** Utsatt til #26

`net-below`, `net-above` and `flows` point to `net-neg-1`, `net-pos-1`, `flow-1`, while the prose defines 4-step scales. A token consumer gets one colour.

Fix: Reference the full scales or add a `scale:` key naming the bins.

**L3 · [Token completeness]** — Some tokens are defined but not wired (§ DESIGN L208–216, L375)

**Status:** Utsatt til #26

`week-table` maps only phone tokens; `figure-total`, `title-page`, `title-phone`, `headline` and `step-title` belong to no component; `matrix-cell-min`, `button` and `figure-*` lack `lineHeight`; `lineHeight` mixes px and unitless values.

Fix: Add laptop variants and a phone-header component, and normalise `lineHeight`.

**L4 · [Component coverage]** — Some visual rows are too thin to build from (§ DESIGN L428, L448; EXPERIENCE L139)

**Status:** Utsatt til #26

`week-summary` is "a short list … and a link"; `funnel` is "horizontal bars … with counts"; «Stegene greyed out» uses a term DESIGN never defines.

Fix: Give anatomy and a token per state.

**L5 · [State coverage]** — Smaller missing states on Lag Klasse and Landing (§ EXPERIENCE L135; NFR-10)

**Status:** Utsatt til #26

Lag Klasse: unreadable or wrong-format file, bounced Invitations. Landing: «Be om lærertilgang» form error and success (the form itself is an assumption).

Fix: Add the rows.

**L6 · [Visual reference coverage]** — Mockup references are not specific (§ DESIGN preamble; EXPERIENCE IA, Key Flows, L300)

**Status:** Utsatt til #26

References are code spans, not links, and IA and Key Flows use bare filenames. DESIGN Components has no per-component references. Nothing says what `10-pedagogikk.png` illustrates. `09-alle-sider.png` is cited for 12 IA rows without naming the panel. UJ-1 cites "the contact-sheet mockup" with no filename.

Fix: Use relative Markdown links and name the panel each time.

**L7 · [Visual reference coverage]** — The drawing Interactive item is undrawn but missing from Open Question 5 (§ 09-alle-sider.png; EXPERIENCE UJ-6 step 4, L420)

**Status:** Utsatt til #26

«Individuell test» draws only Flervalg, Fyll inn kolonnen and Langsvar. See C2 for the accessibility consequence of leaving this item unspecified.

Fix: Add it to the undrawn list.

**L8 · [Bloat & overspecification]** — The Typography table restates frontmatter sizes (§ DESIGN L346–359)

**Status:** Utsatt til #26

«48/56 700», «34 700» … duplicate the frontmatter, a drift risk.

Fix: Keep the Role, Token and Where columns and drop the numbers.

**L9 · [Bloat & overspecification]** — Decision rationale and decorative lines sit inside behaviour tables and flows (§ EXPERIENCE L54, L123, L347, L358)

**Status:** Utsatt til #26

The Startoppgave IA row and the Varselbånd row carry founder decisions; «Sara's 24 in Uke 11 towers over flat demand» and «The next order builds on a sum, not on an answer key» are decorative.

Fix: Move rationale to the memlog and keep the flows literal.

**L10 · [Bloat & overspecification]** — Mockup-script checks read as product requirements (§ DESIGN L306, L380)

**Status:** Utsatt til #26

«`vlib.py` checks contrast at build time» and «The build checks that the band fits the phone in all 36 Uker» describe mockup scripts; it is unclear whether the product build must enforce them. H13 covers the 320 px gap in the same check.

Fix: Restate them as product test requirements or drop them.

**L11 · [Inheritance discipline]** — Row labels drift between the spines (§ EXPERIENCE L77–78, L238; DESIGN L422)

**Status:** Utsatt til #26

Phone and laptop rows say «Kost, kr» (matching 05); DESIGN «Alle rader», 10 and 01 say «Kost per uke». «Sum, hele kr» is mentioned as removed but never listed.

Fix: Pick one label per row and list the canonical row set once.

**L12 · [Shape fit]** — Inspiration and anti-patterns are folded into Foundation (§ EXPERIENCE L37–43)

**Status:** Utsatt til #26

«Rejected directions» and «Lifted» apply (the memlog records rejected directions and the yr.no reference) but have no section of their own.

Fix: Promote them to a short "Inspiration & Anti-patterns" section.

**L13 · [Shape fit]** — EXPERIENCE.md frontmatter has no `name`, and both spines are `status: draft` (§ EXPERIENCE frontmatter)

**Status:** Utsatt til #26

The paired examples carry `name`.

Fix: Add `name: ØL-spillet` and set the status at finalisation.

**L14 · [Accessibility (reviewer)]** — Page and phrase language are not declared (a11y L1) (§ EXPERIENCE Accessibility Floor; PDF report)

**Status:** Utsatt til #26

`lang="nb"` is not stated for HTML or the PDF (`/Lang (nb-NO)`), and English phrases such as «Øvelsen heter Beer Game.» and «bullwhip» need `lang="en"`. WCAG 3.1.1, 3.1.2.

Fix: Add both to the Accessibility Floor.

**L15 · [Accessibility (reviewer)]** — 12 px text survives in the mockup library (a11y L2) (§ vlib.scrubber(), cost_panel, cost_panel_wide, chain-band overdue number)

**Status:** Utsatt til #26

The DESIGN assumption covers only the cost-over-time charts on phone.

Fix: Extend the floor statement to all of these and assert ≥ 13 px in `Doc.save()` for Student sheets.

**L16 · [Accessibility (reviewer)]** — `ink` on `net-neg-2` is 4.51:1, one hundredth above the threshold (a11y L3) (§ DESIGN Colors (Matrix steps))

**Status:** Utsatt til #26

At sizes down to 9 px, any opacity, colour-profile or anti-aliasing drift fails. The rubric's mechanical notes flag the same margin.

Fix: Nudge `net-neg-2` lighter (≥ 4.7:1 with `ink`) and re-run the ordinal validator.

**L17 · [Accessibility (reviewer)]** — Reduced motion covers only the week-advance animation (a11y L4) (§ EXPERIENCE Accessibility Floor)

**Status:** Utsatt til #26

It also needs to cover the now-line moving, the box inserting into the pipe while typing, scrubber spooling, the Trakt moving and live wall changes.

Fix: "Under `prefers-reduced-motion: reduce`, every transition is instant."

**L18 · [Accessibility (reviewer)]** — Timing passes by exception, with two gaps (a11y L5) (§ EXPERIENCE State Patterns; Takeover rules)

**Status:** Utsatt til #26

The Student is never warned before their own Seat is taken over (only the lecturer sees «KI overtar om 1 t»), and login session expiry is unspecified. WCAG 2.2.1.

Fix: Show «KI-spiller tar setet ditt om N t hvis du ikke bestiller» on Hjem and in the reminder e-mail. Specify a session over 20 h, or warn with an extend option and keep the typed order.

**L19 · [Accessibility (reviewer)]** — Page titles and heading outlines are not specified (a11y L6) (§ EXPERIENCE (all surfaces))

**Status:** Utsatt til #26

WCAG 2.4.2, 1.3.1, 2.4.6.

Fix: Add a title pattern such as «Uke 11 · Spill 17 · ØL-spillet» and a heading outline per surface.

**L20 · [Accessibility (reviewer)]** — Colour semantics collide in Debrief step 2 (a11y L7) (§ 07-debrief.png step 2)

**Status:** Utsatt til #26

The demand band uses `lager-fill` and the customer «8» is `lager`, which makes customer demand look like stock.

Fix: Use `bar-base` or `future-tint` for the band and `ink` for the customer figure.

**L21 · [Accessibility (reviewer)]** — Tappable figures and future hover content need rules (a11y L8) (§ EXPERIENCE Component Patterns)

**Status:** Utsatt til #26

The Totalkostnad figure opens «Alle rader», so it must be a real link or button with a name (4.1.2). Any tooltips later added to wall cells must meet 1.4.13.

Fix: Add both lines to Component Patterns.

## Reviewer files

- `review-rubric.md`
- `review-accessibility.md`
