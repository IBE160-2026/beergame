---
title: "Accessibility review: DESIGN.md + EXPERIENCE.md (ØL-spillet)"
reviewer: adversarial accessibility review (agent)
date: 2026-11-09
standard: WCAG 2.1 AA + PRODUCT.md commitments (charts have text/table alternatives, role/status never by colour alone, every Student flow from 360 px)
scope: DESIGN.md, EXPERIENCE.md, mockups/05, 06, 07, 08, .working/valgt-konsept/vlib.py
---

# Accessibility review: ØL-spillet UX spines

## Verdict

**Not ready for a WCAG 2.1 AA claim. Revise before the architecture and story work.**

The palette is good. Every text token passes on `paper` and `future-tint`, the matrix step text passes, and the `ink-muted` idle-border fix holds at token level. The core game screen avoids colour-only meaning well, because it uses signed numbers, position against zero and direct labels.

The gaps are behavioural, and some are structural:
- The core week table cannot hold 12 columns at the 13 px floor at 320 px or at 200 % text. The spine does not say what happens instead.
- There is no focus style.
- One Individuell test item is pointer-only.
- The matrix wall's «Vegg» view carries sign by hue alone, and the red and blue are luminance-matched.
- Several lecturer and cost charts have no text or table alternative.
- Error handling for the irreversible order input is still an [ASSUMPTION].

**Counts:** 2 critical · 8 high · 11 medium · 8 low.

All contrast ratios below were computed from the DESIGN.md frontmatter hex values with the WCAG 2.x relative-luminance formula (the same formula as `vlib.contrast`).

---

## Critical

### C1. Week table: 12 columns cannot meet the 13 px floor at 320 px or at 200 % text
- **Where:** DESIGN → Layout & Spacing (phone: 12 columns, nå − 7 to nå + 4, `row-label-phone` 76 px, `gutter-phone-chart` 16 px). DESIGN → Typography floors (13 px). EXPERIENCE → Accessibility Floor ("360 px with 200 % text zoom … [ASSUMPTION: the table may scroll inside itself]"). `vlib.gtable` shrinks cell text in a loop: `while text_w(...) > ax.slot - 3 and fs > 9: fs -= 0.5`.
- **WCAG:** 1.4.4 Resize Text, 1.4.10 Reflow. Also the spine's own 13 px floor.
- **Failure scenario:**
  - At 360 px, 360 − 2×16 − 76 = 252 px across 12 columns gives 21 px per column. «−13» at 13 px tabular is about 19–20 px, so it barely fits.
  - At 200 % text (26 px), «−13» needs about 39 px, so only about 6 columns fit.
  - At WCAG's reflow width of 320 px, columns are 17.7 px, so «−13» does not fit even at 100 %.
  - The mockup library solves this by shrinking cell text toward 9 px. A developer who copies it gets text that does not grow with zoom and drops below the 13 px floor.
  - If the table instead "scrolls inside itself", the graph above loses its shared x-axis with the table (the core P1 grammar), unless both scroll together. Nothing specifies that.
- **Fix:**
  - Specify the zoom and narrow-width behaviour explicitly. Recommended: the graph and table form one horizontally scrollable unit sharing one scroll position. It scrolls to keep «Nå» in view on load, the row-label column is sticky, and the unit has a visible scroll affordance. This is permitted under the 1.4.10 exception for content that needs two-dimensional layout.
  - Alternatively, reduce the window to nå − 3 … nå + 4 when columns would fall under about 2.2 em.
  - Ban auto-shrinking text below the floor.
  - Require the table to be an HTML `<table>` in relative units (`<th scope="col">` per Uke, `<th scope="row">` per row), not SVG `<text>` in a viewBox. SVG text does not reflow and does not respond to text-only zoom.
  - Add a build check at 320 px and at 200 % text, as vlib already does for the chain band.

### C2. Individuell test: the drawing item has no keyboard or non-drawing alternative
- **Where:** EXPERIENCE → UJ-6 step 4 («Sara draws the bakery stock in an Interactive item»). The Accessibility Floor only asserts that "Interactive items … are fully keyboard-operable (FR-80)" and gives no mechanism.
- **WCAG:** 2.1.1 Keyboard (A), 2.5.1 Pointer Gestures (A, because freehand drawing is a path-based gesture), 1.1.1.
- **Failure scenario:** a keyboard-only or screen-reader Student reaches a required, deadline-bound test step and cannot draw a curve. There is no specified way to enter the same answer, so the Student cannot complete the test.
- **Fix:**
  - Specify that every drawing item is backed by an equivalent value table: one numeric input per Uke, which the drawing writes into and which redraws the curve.
  - Specify keyboard point editing: arrow keys move a point by one unit, Tab moves to the next Uke.
  - Specify that a screen-reader user answers through the table alone.
  - State that scoring reads the table values, so both input modes are equal.

---

## High

### H1. No focus-visible style is defined anywhere
- **Where:** the DESIGN.md frontmatter has no focus token. DESIGN → Components and Elevation ("no shadows") say nothing about focus. EXPERIENCE → Accessibility Floor defines focus order only.
- **WCAG:** 2.4.7 Focus Visible. 1.4.11 for the indicator itself.
- **Failure scenario:**
  - The "no shadows, no chrome" posture invites `outline: none`.
  - Default browser rings are unreliable in several places: on `ink`-filled primary buttons and active toggle segments, on the `restordre-fill` Varselbånd, inside matrix cells (where the dark steps `net-neg-4` / `net-pos-4` / `flow-4` are near `ink`), and on the `ink` «24» Din ordre cell.
  - Keyboard users in the computer lab lose their place, typically between «Bekreft ordre på 24» and the − / + segments.
- **Fix:**
  - Add `focus-ring: 2px solid {colors.ink}, offset 2px` with a `paper` gap, which gives 14.6:1 against `paper`, 10.5:1 against `restordre-fill` and 13.3:1 against `future-tint`.
  - Where the focused element is itself `ink`-filled, the offset gap separates the ring from the fill.
  - Use `:focus-visible`. Never remove the outline without replacing it.
  - For table cells and wall rows, use an inset 2 px `ink` frame (as with `rounded.xs` for the column highlight).
  - Add the ring to every component under DESIGN → Components.

### H2. Matrix wall «Vegg» shows the sign of Netto lager by hue alone, with luminance-matched steps and no legend
- **Where:** DESIGN → Colors, "Matrix steps" ("The cell always prints its signed number … so colour never carries the value alone"). DESIGN → Components, Matrisevegg. `08-laerer-oversikt.png` shows **no numbers in the wall cells**. EXPERIENCE → Responsive («Vis i plenum» shows 60 games as a matrix).
- **WCAG:** 1.4.1 Use of Color, 1.1.1. Also the PRODUCT commitment "status never by colour alone".
- **Failure scenario:**
  - Red and blue steps are matched in luminance: `net-neg-1`/`net-pos-1` 1.05:1, `net-neg-3`/`net-pos-3` 1.01:1, `net-neg-4`/`net-pos-4` 1.10:1.
  - On a washed-out projector, in greyscale, or for a lecturer or student with reduced colour vision, backlog and stock cells of the same magnitude look identical.
  - The spine's claim that every cell prints its number is false for the wall as drawn.
  - The table toggle rescues a lecturer at the laptop (a conforming alternate version). Nothing rescues the **plenum audience**, because «Vis i plenum» has no table and its numbers cannot be read from the back of the room.
  - There is no legend for the bins (1–9 / 10–19 / 20–34 / 35+), so magnitude cannot be decoded at all.
- **Fix:**
  - Correct the DESIGN claim. Say instead that the wall cells print no number below a set cell size, and that the table is the alternative.
  - Add a non-hue cue for sign in «Vegg», for example a 1 px `paper` diagonal hatch or an inner bottom bar on below-zero cells, or a darker-at-same-step red ramp so that sign also differs in lightness.
  - Add a compact legend with signed bin labels («−35 … −1 · 0 · 1 … 35+»).
  - For «Vis i plenum», add a printed caption that names the pattern in words («Rødt: restordre under null. Blått: lager over null.») and offer the plenum view with hatching on by default.

### H3. Several charts have no text or table alternative
- **Where and failure:**
  - **«Totalkostnad over tid»** (DESIGN → cost-panel; EXPERIENCE → Cost picture). EXPERIENCE says "Where the panel is shown, the row «Sum, hele kr» is removed", so the cumulative series has no tabular equivalent at all.
  - **«Kjedens kostnad over tid»** (Spillet er ferdig, `06` F): no table, and only Kjedens regning totals are given.
  - **`cost-distribution` («Klassens kostnad»)**: 41 ticks, a box, the median and «Fjoråret». No list of values, and no alternative is specified.
  - **«Snitt per ferdig spill, per Rolle»** (`08` right rail): each row prints only the total (213, 462 …). The lager/restordre split per Role is carried by the blue/red bar lengths alone, with a colour-chip legend «lager 949 / restordre 1 063 kr».
  - **Delt skjerm «Kostnad, kr» per Role** (`07`): the split bar is printed with only the total.
  - **`date-line` and `allocation-preview`**: read-only charts, but the lecturer **acts** through them («Legg til Labtime», selecting a game column). See M9.
  - **Hjem mini graph** and the **Debrief step 1 colour strip** under «Ditt netto lager» (`07`): colour cells with no numbers.
  - The spine claims "every chart has a table alternative" and "Read-only lecturer charts" and leaves these out.
- **WCAG:** 1.1.1 Non-text Content, 1.4.1, 1.3.1. Also the PRODUCT commitment "Charts have text or table alternatives".
- **Fix:**
  - Add a table to the Accessibility Floor that names the alternative for **each** chart component: `net-graph`, `cost-field`, `cost-panel` area, `chain-bill`, `order-bars`, `scrubber`, `matrix-wall`, `cost-distribution`, `funnel`, `date-line`, `allocation-preview`, the Hjem mini graph and the step 1 strip.
  - Concretely:
    - Put a Lager / Restordre column next to each Role total in «Snitt per Rolle» and the Delt skjerm.
    - Restore cumulative cost as a «Sum, kr» row in «Alle rader» (screen-reader exposed even if visually hidden on laptop).
    - Give `cost-distribution` a «Vis som tabell» link (game, kjedekost, sorted) plus a text summary («Median 1 954, midterste halvdel 1 500–2 600, fjoråret 2 740»).
    - Mark the Hjem mini graph `aria-hidden` with a text summary («Netto lager −13, Uke 11»).

### H4. Order input: error identification, instructions and the irreversible submit are unspecified
- **Where:** EXPERIENCE → Component Patterns, Ordrefelt ("Invalid input is rejected inline before submit [ASSUMPTION: copy to be written]"). Interaction Primitives ("typing plus Enter confirms [ASSUMPTION]", "numeric `inputmode` [ASSUMPTION]"). DESIGN → `order-input` has no `border-error`, unlike `text-field`.
- **WCAG:** 3.3.1 Error Identification, 3.3.2 Labels or Instructions, 3.3.3 Error Suggestion, 4.1.3 Status Messages.
- **Failure scenario:**
  - A Student types «2 4», «-3», «24,5» or a value above the Game settings maximum. The maximum is never shown («0 to the Game settings maximum»), so the Student cannot know the allowed range before an error.
  - It is undefined what the error looks like and whether it is announced.
  - What the empty secondary «Bekreft ordre» does when pressed is undefined.
  - On laptop, Enter in the field submits an order that cannot be undone, with no review step.
  - If a developer uses `type="number"`, a mouse wheel over the focused field silently changes the value before Enter.
- **Fix:**
  - Write the copy now. Help text under the field: «Hele tall fra 0 til 60.» (with the real maximum). Error, in `restordre` with the reason: «Skriv et helt tall fra 0 til 60.»
  - Add `order-input.border-error: 1.4px {colors.restordre}` (5.5:1).
  - Wire `aria-invalid`, `aria-describedby` → help + error, and announce the error via `role="alert"` on submit.
  - Make the empty «Bekreft ordre» show the same error instead of submitting.
  - Use `type="text" inputmode="numeric" pattern="[0-9]*"`.
  - Make Enter move focus to «Bekreft ordre på 24» rather than submit directly, or require Enter on the button.
  - Give the − / + segments accessible names («Én færre», «Én flere») and announce the new value.
  - Separately, the Individuell test's single submission is a 3.3.4 case (test responses). Require a review step listing unanswered items before «Lever», and state that autosave plus auto-submit at the Testfrist is the "reversible" path.

### H5. Signal-coloured or muted text on the fill tints fails 4.5:1, and the spine has no rule against it
- **Where:** DESIGN → Colors gives fills and text tokens but no rule for text **on** `lager-fill` / `restordre-fill`. `07-debrief.png` step 2 «Kundenes etterspørsel: 8» and «4» are `lager` text on the `lager-fill` demand band. `08-laerer-oversikt.png` has the near-Takeover wall row tinted `restordre-fill` with the «Melding» link (`link` = `lager`) and row text.
- **WCAG:** 1.4.3 Contrast (Minimum).
- **Measured:**

  | Text | on `lager-fill` #CDDFEE | on `restordre-fill` #F0D5D2 |
  |---|---|---|
  | `ink` | 10.67 ✔ | 10.51 ✔ |
  | `ink-secondary` | 5.36 ✔ | 5.28 ✔ |
  | `ink-muted` | **3.78 ✘** | **3.72 ✘** |
  | `lager` (links, demand label) | **4.07 ✘** | **4.01 ✘** |
  | `restordre` (error text) | **4.04 ✘** | **3.98 ✘** |
  | `order-history` | 3.27 ✘ | 3.22 ✘ |

- **Failure scenario:** the climax reveal label in Debrief step 2 fails at about 14 px bold, which is not "large". The «Melding» link in the most urgent wall row fails at 9 px. Any `ink-muted` time stamp or `restordre` reason placed in the Varselbånd fails.
- **Fix:**
  - Add a rule to DESIGN → Colors: "On `lager-fill`, `restordre-fill` and `net-*-1/2`, text is `ink` or `ink-secondary` only. Links on a tinted row or band use `ink` with an underline."
  - Change the demand label to `ink` 600 with the band itself as the blue cue.

### H6. Reflow: the Student floor is 360 px, but WCAG 1.4.10 tests at 320 CSS px, and the chain-band check runs at 390
- **Where:** EXPERIENCE → Responsive & Platform and Accessibility Floor (360 px). DESIGN → Layout ("The build checks that the band fits the phone in all 36 Uker"). `vlib.py` `PHONE_CHAIN = (16, 358, 1.4)` is the 390 mockup width.
- **WCAG:** 1.4.10 Reflow (320 CSS px, which equals 1280 px at 400 %).
- **Failure scenario:** a Student with 400 % browser zoom on a laptop, or a 320 px-class phone, gets the chain band, the order input with − / + segments and the cost panel at 320 px. The pipe at the fixed `chain-pipe-unit-phone` 1.4 px/unit has never been checked at 360, let alone 320. Week 15 «På vei 56 + 13» plus an overdue box is the known worst case (`06` E).
- **Fix:**
  - State the reflow target as 320 CSS px for every non-tabular Student component, keeping 360 as the design floor.
  - Make the chain-band scale rule derive the units per pixel from the available width, and run the build check at 320 and 360, not only at 390.
  - List which components rely on the 1.4.10 two-dimensional exception (week table, matrix, order-bars) and which must reflow (everything else).

### H7. Live Oversikt auto-updates and re-sorts without a pause, so screen-reader and keyboard users lose their place
- **Where:** EXPERIENCE → State Patterns, Oversikt Live ("Updates within 5 s without reload"). Component Patterns, Matrisevegg (groups by status, «Ferdig, lavest kjedekost øverst») and Visningsbryter (the table "is sortable and is read by screen readers"). UJ-7 step 5 («the Trakt moves»).
- **WCAG:** 2.2.2 Pause, Stop, Hide (auto-updating content), 2.4.3 Focus Order, 4.1.3.
- **Failure scenario:**
  - A lecturer using NVDA reads row 23 of «Vis som tabell». A game finishes, the row jumps from «Pågår» to «Ferdig» and re-sorts by kjedekost, and the virtual cursor now sits on a different game.
  - Keyboard focus on a «Melding» link can be destroyed by the re-render.
  - It is also undefined which changes are announced. Announcing every 5 s update would be unusable, and announcing none hides the new Varselbånd.
- **Fix:**
  - Add a «Frys visningen» / «Oppdater automatisk» switch, default on, plus a polite counter while frozen («3 endringer siden 14:02, Oppdater»).
  - Freeze automatically while focus is inside the table.
  - Keep focus on the same game ID across re-renders.
  - Announce politely only Varselbånd changes and the headline counts, and throttle to at most one announcement per minute.

### H8. Ukeskrubber: keyboard support is only an assumption, with no slider semantics and no announced result
- **Where:** EXPERIENCE → Component Patterns, Ukeskrubber ("[ASSUMPTION: arrow keys step one Uke; Home and End …]"). Accessibility Floor ("fully keyboard-operable (FR-80)"). DESIGN → scrubber track `axis`.
- **WCAG:** 2.1.1, 4.1.2 Name, Role, Value, 4.1.3, 1.4.11.
- **Failure scenario:**
  - A screen-reader Student in the group Debrief step 3 hears an unnamed control.
  - Moving it changes the full chain and the dashed marker across the bars, but nothing is announced, so the step's teaching point ("1,8× grows to 7,6×") is visual-only.
  - The unfilled track is `axis`, 1.61:1 against paper, so its extent is below 3:1.
- **Fix:**
  - Promote the assumption to a rule: `role="slider"`, `aria-valuemin=1`, `aria-valuemax=36`, `aria-valuetext="Uke 15"`, arrows ±1, PageUp/PageDown ±4, Home/End.
  - On change, debounce about 300 ms, then update a polite live region with the chain as text («Uke 15. Fabrikk restordre 3, Distributør restordre 34, Grossist restordre 19, Detaljist restordre 20. Ordre: 22, 12, 12, 8.»).
  - Draw the unfilled track in `ink-muted` (5.16:1).
  - Add − / + step buttons as a non-drag alternative.
  - On «Delt skjerm», state who controls the scrubber.

---

## Medium

### M1. Non-text contrast: `axis` (1.61:1) still carries meaning or state in several places
- **Where and WCAG 1.4.11:**
  - `scrubber.track` (see H8).
  - `step-list.later-dot`: the locked or later step is indicated by an `axis` dot, and «Stegene greyed out» on Hjem has no text.
  - `net-graph.zero-line` and `cost-field.baseline`: the zero line is the reference that separates stock from backlog.
  - The unknown-arrival dashed Levering cell at nå + 4 (`vlib` draws `HAIR2` dashed) and the overdue broken box (`axis` dashed on `future-tint`, 1.47:1).
  - `switch` has no off-state token at all. An off track in `axis` would fail.
- **Also:** `vlib.Doc.button()` still draws secondary buttons with `HAIR2`, so regenerated mockups will keep showing 1.6:1 borders and contradict the spine's fix.
- **Fix:**
  - Change scrubber track, zero line and baselines to `ink-muted`.
  - Give later steps the text «låst» or «åpnes etter Debrief», with the dot as a hollow `ink-muted` ring.
  - Add `switch.off: track 1px {colors.ink-muted}, knob {colors.ink-muted}` and a state word beside it.
  - Draw the unknown and overdue box outlines in `ink-muted`.
  - Update `vlib.button()` to `INK3`.
  - The chain-band `node-border` in `axis` is fine, because it is decorative and labelled.

### M2. Status messages: coverage is partial
- **Where:** EXPERIENCE → Accessibility Floor ("Live announcements … «Venter på: …», the Uke advance, Takeover, and the reveal unlocking").
- **WCAG:** 4.1.3.
- **Missing:**
  - order-input errors (H4)
  - «Ordren på 24 er sendt» (the focus move covers it only if the target has `tabindex="-1"` and a name)
  - Pause starting or ending («Pause: Jonas har ikke bestilt på 24 t.»)
  - «KI-spiller har bestilt for deg.» and the reclaim confirmation
  - «Uke 12 åpner» while the page is open
  - Lag Klasse «250 rader lest» / «Ugyldige rader: 4 av 250»
  - «Send 246 Invitasjoner» result, «Lagre Klasseøkt» result, «Bekreft fordeling» result
  - quiz «Ditt svar, ikke riktig» / «Riktig»
  - Individuell test autosave «Lagret» and auto-submit at the Testfrist
  - wall filter result counts
- **Also:** focus after the week advances is undefined. Focus sits on the waiting message, which disappears.
- **Fix:**
  - Add a full table to the Accessibility Floor: event → region (`status` polite / `alert`) → copy → focus target.
  - After the advance, move focus to the «Uke 12» heading. Do not move it into the order input, which would open the keyboard on phones.

### M3. The Debrief auto-advances a step when others submit, and step focus is undefined
- **Where:** EXPERIENCE → Debrief sequence, step 1 ("In a group, the step moves on when all have sent").
- **WCAG:** 2.4.3 Focus Order, 3.2.x (unexpected context change), 4.1.3.
- **Failure scenario:** a screen-reader Student is reviewing the Forklaring. Jonas sends, step 2 replaces the content and the reading position is lost.
- **Fix:**
  - Unlocking announces «Avsløringen er åpen» politely and enables a «Gå til steg 2» button. It never swaps content under the user.
  - On step change, move focus to the step's `h2`.
  - Put the step headings in a navigable list with `aria-current="step"`.

### M4. Focus order, bypass and dialog behaviour are undefined beyond the phone game screen
- **Where:** EXPERIENCE → Accessibility Floor (focus order for header → chain band → graph/table → order input → confirm only).
- **WCAG:** 2.4.3, 2.4.1 Bypass Blocks, 2.1.2 No Keyboard Trap.
- **Gaps:**
  - On the laptop Labtime layout, the left table (Uke 1 to nå + 4, 9 rows) comes before the right-hand order input. If cells are focusable, that is hundreds of Tab stops. There is no skip link.
  - The wall order is unspecified: filters → Visning toggle → wall/table → right rail → «Vis i plenum».
  - The Debrief step order is unspecified.
  - What «Melding» and «Send Melding» open (page, panel or modal) is undefined, which is a possible trap and has no Esc or return-focus rule.
  - The phone «Alle rader og kostnad» full screen has no initial-focus rule.
- **Fix:**
  - Table cells are not focusable; the table is read with screen-reader table navigation.
  - Add a skip link «Gå til ordren» on the game screen.
  - Specify wall and Debrief order.
  - Any panel that is opened is either a route (browser Back works) or a modal with a focus trap, Esc and return focus.
  - «Alle rader» opens with focus on its `h1`.

### M5. Red and blue are luminance-identical, so print, greyscale and projection lose the cost and stock split
- **Where:** DESIGN → Colors: `lager` vs `restordre` 1.01:1, `lager-fill` vs `restordre-fill` 1.02:1. Affected: `cost-field` single-type bars, `chain-bill` split bars, the Kost per uke key chips («■ restordre 1,00 ■ lager 0,50»), «Totalkostnad over tid», the Delt skjerm cost bars, and the PDF Studentrapport (NFR-6), which Students will print in black and white.
- **WCAG:** 1.4.1. Also the PRODUCT commitment.
- **Context:** on the game screen this is mitigated, because lager and restordre never coexist in a week and the Netto lager sign in the same column disambiguates the bar. Elsewhere it is not mitigated.
- **Fix:**
  - Give restordre a structural cue wherever the two are adjacent without numbers: always stack restordre on top with a 1.5 px gap and a label on first occurrence, or use a fine hatch on restordre fills.
  - Require the PDF to print a lager / restordre number beside every split bar.
  - Spell out the legend chips in text order matching stack order.

### M6. Fixed pixel row heights and widths will clip text under text-spacing overrides and zoom
- **Where:** DESIGN frontmatter `row-phone` 20 px, `row-laptop` 26 px, `row-label-phone` 76 px, `control-height-phone` 50 px, `order-input-height` 54 px, table line-height 20 px.
- **WCAG:** 1.4.12 Text Spacing, 1.4.4.
- **Failure scenario:**
  - With a line height of 1.5, letter spacing 0.12 em and word spacing 0.16 em, «Netto lager», «Restordrekostnad» and «Ordre inn» overflow the 76 px label column.
  - 26 px text in a 20 px row clips.
- **Fix:** state that these are minimums (`min-height`, `min-width`), that rows grow with content, and that the label column may widen or wrap. Test with the text-spacing bookmarklet at 360 px.

### M7. Control semantics and the selected state are missing
- **Where:** DESIGN → `quiz-option` (idle / correct / wrong only, with no selected-before-submit state), `view-toggle`, `segmented-choice`, `switch`, filters in `08`. EXPERIENCE → Quizvalg "Single choice".
- **WCAG:** 4.1.2, 1.4.11, 1.4.1.
- **Failure scenario:** a Student cannot see or hear which quiz answer is chosen before submitting, because there is no visual state. Toggle and filter state is not exposed to assistive technology.
- **Fix:**
  - Add `quiz-option.border-selected: 1.4px {colors.ink}` plus a filled radio dot, implemented as native radios in a `fieldset` / `legend`.
  - The view toggle and segmented choices are a radio group or `aria-pressed`.
  - The switch is `role="switch"` with `aria-checked` and the visible state word.
  - Filters expose `aria-pressed` or `aria-current`; their bold + underline visual is already fine.

### M8. Target size is committed only for "primary controls"
- **Where:** DESIGN `tap-target-min` 44 px. EXPERIENCE → Accessibility Floor ("for primary controls"; «Ta tilbake setet» at 38 px is an assumption).
- **Criterion:** WCAG 2.5.5 (AAA in 2.1; 2.5.8 is AA in 2.2) and the product's own commitment.
- **Failure scenario:**
  - The − / + segments have no specified width.
  - «Lukk», «Hopp over», «Alle rader og kostnad» and «Kostnad så langt» are 13–15 px text links.
  - The tappable Totalkostnad figure has no stated size.
  - On the wall, «Melding» links are 9 px text in about 10 px rows, and clicking a row opens Spillinnsikt.
- **Fix:**
  - Make 44 × 44 px the minimum hit area for **every** Student touch target, including links, padded invisibly.
  - Make the − / + segments at least 54 × 54 px.
  - On the wall, put «Melding» and row-open actions in the table view, or a hit area of at least 24 × 24 px (the 2.5.8 floor) with spacing.

### M9. Allocation preview and date-line are interactive but specified as read-only charts
- **Where:** EXPERIENCE → Component Patterns ("Read-only lecturer charts. In Fordelingsforhåndsvisning, selecting a column shows that game's four names"). UJ-3 step 4 («Legg til Labtime»).
- **WCAG:** 2.1.1, 1.1.1, 4.1.2.
- **Failure scenario:** a keyboard-only lecturer cannot select game 17 among 60 unlabelled columns, or check dates that are only drawn on the timeline.
- **Fix:**
  - Columns are buttons with names («Spill 17»), arrow-key roving, and the four names in a live region.
  - Provide a list or table of all games with their four names as the alternative.
  - The Datolinje mirrors labelled date inputs and a list of Labtimer. The legend «Blå firkant: Labtime» becomes «Firkant: Labtime» (shape, not colour, per 1.3.3) with the list as the alternative.

### M10. Screen-reader pronunciation of Norwegian number formatting is untested
- **Where:** DESIGN → Typography: true minus U+2212, space as the thousands separator, «×», «1,8×».
- **WCAG:** 1.3.1 and 2.4.6 in spirit, and the usability of the table alternative.
- **Failure scenario:**
  - Some voices skip U+2212, so «−13» is read as «13» and backlog becomes stock.
  - «2 266,00» can be read as «2» and «266,00».
  - «7,6×» can be read as «7,6 multiplikasjonstegn».
- **Fix:**
  - Use a narrow no-break space (U+202F) between thousands groups.
  - Test NVDA, JAWS, VoiceOver and TalkBack with nb voices.
  - Where needed, add `aria-label` / visually hidden text («minus 13», «7,6 ganger»).
  - Add this to the acceptance criteria for the table alternative.

### M11. 9 px matrix text: projector legibility and zoom behaviour
- **Where:** DESIGN `matrix-cell-min` 9 px. «Vis i plenum».
- **Failure scenario:**
  - At 1440 px projected to about 3 m, 9 px is about 2 mm per character. The plenum audience gets colour only (see H2).
  - If the wall is rendered as canvas or fixed-px SVG, browser zoom does not enlarge the text (1.4.4).
- **Fix:**
  - The wall scales with browser zoom.
  - «Vis i plenum» renders at a larger cell size with fewer columns, or with the H2 legend, hatching and caption.
  - The lecturer table view stays at 13 px or larger, which is already specified.

---

## Low

- **L1. Language (3.1.1, 3.1.2).** `lang="nb"` is not stated for HTML or the PDF (`/Lang (nb-NO)`). English phrases need `lang="en"`: «Øvelsen heter Beer Game.» (Debrief step 2) and «bullwhip» if used. *Fix:* add both to the Accessibility Floor.
- **L2. 12 px text survives in the mockup library.** `vlib.scrubber()` («Uke 1»/«Uke 36» at 12 px), `cost_panel` axes and labels (12 px), `cost_panel_wide` (12 px), and the chain-band overdue number (`max(ls − 1, 11)` = 12 px). The DESIGN assumption covers only the cost-over-time charts on phone. *Fix:* extend the floor statement to all of these and assert ≥ 13 in `Doc.save()` for Student sheets.
- **L3. `ink` on `net-neg-2` is 4.51:1.** That is 0.01 above the threshold, at sizes down to 9 px. Any opacity, colour-profile or anti-aliasing drift fails. *Fix:* nudge `net-neg-2` lighter (target ≥ 4.7:1 with `ink`) and re-run the ordinal validator.
- **L4. Reduced motion covers only the week-advance animation.** It also needs to cover the now-line moving, the box inserting into the pipe while typing, scrubber spooling, the Trakt moving and live wall changes. *Fix:* "Under `prefers-reduced-motion: reduce`, every transition is instant." (2.3.3 is AAA, but it is cheap, and 2.2.2 applies to anything over 5 s.)
- **L5. Timing (2.2.1) passes by exception.** The 24 h Takeover, the 48 h group Debrief and the Testfrist are covered by the 20-hour and deadline exceptions. Two gaps remain:
  - the Student is never warned before their own Seat is taken over, since only the lecturer sees «KI overtar om 1 t»
  - login session expiry is unspecified

  *Fix:* show «KI-spiller tar setet ditt om N t hvis du ikke bestiller» on Hjem and in the reminder e-mail, without revealing week counts. Specify a session length over 20 h, or warn with an extend option and keep the typed order.
- **L6. Page titles and headings (2.4.2, 1.3.1, 2.4.6) are not specified.** *Fix:* add a pattern such as «Uke 11 · Spill 17 · ØL-spillet» and a heading outline per surface: `h1` the screen title, `h2` the chain band, graph, table, order and cost panel.
- **L7. Colour semantics collide.** The Debrief step 2 demand band uses `lager-fill` and the customer number «8» in the full chain is `lager`, which makes customer demand look like stock. *Fix:* use `bar-base` or `future-tint` for the demand band and `ink` for the customer figure.
- **L8. Tappable figures and hover content.** The Totalkostnad figure opens «Alle rader», so it must be a real link or button with a name («Totalkostnad 68,00 kr, vis alle rader og kostnad»), per 4.1.2. If tooltips are later added to wall cells, they must meet 1.4.13 (dismissible, hoverable, persistent). *Fix:* add both lines to Component Patterns.

---

## Verified OK

- **Text tokens on `paper`:** `ink` 14.56, `ink-secondary` 7.31, `ink-muted` 5.16, `lager` 5.56, `restordre` 5.52.
- **Text tokens on `future-tint`:** 13.30 / 6.68 / 4.71 / 5.08 / 5.04. All pass 4.5:1 and match the `vlib` assertion.
- **Matrix step cell text:**
  - `ink` on `net-neg-1` 6.71, `net-neg-2` 4.51 (see L3), `net-pos-1` 7.02, `net-pos-2` 4.90, `flow-1` 7.04, `flow-2` 4.80.
  - `paper` on `net-neg-3` 5.52, `net-neg-4` 8.39, `net-pos-3` 5.56, `net-pos-4` 9.20, `flow-3` 5.14, `flow-4` 14.56.
  - `ink` on `net-zero` 13.30.
- **Varselbånd:** `ink` on `restordre-fill` 10.51. Primary button `paper` on `ink` 14.56. The secondary button's `ink-muted` border on `restordre-fill` is 3.72, which passes 3:1.
- **Idle-border fix holds at token level.** `text-field`, `order-input`, `quiz-option`, `button-secondary`, `view-toggle` and `segmented-choice` all use `ink-muted` (5.16:1). The exceptions are listed in M1: scrubber track, step dots, switch off-state, dashed boxes and `vlib.button()`.
- **Meaningful non-text marks pass 3:1:**
  - now-line `ink` 14.56
  - known-arrival boxes `lager` 5.56
  - typed order box `ink`
  - projection 4.56 on paper and 4.17 on tint
  - `order-history` bars 4.46
  - own order bar `ink` vs `order-history` 3.26, also labelled «Sara, du»
  - error and wrong-answer borders `restordre` 5.52
- **Game screen (net-graph) avoids colour-only sign.** Sign is carried by position against the zero line and the colour switch, the direct label «Restordre 13», and signed table cells with a true minus.
- **Never colour alone, verified for:** Setestatus (filled / hollow dot plus text), quiz («Ditt svar, ikke riktig» / «Riktig»), invalid rows (reason text), AI («KI-spiller», «KI-generert, kan ta feil»), wall filter selection (bold plus underline), chain band («Lager 12» / «Restordre 13» plus bar direction), and the first large order (red dot plus «Uke n»).
- **Graf over tabell** puts a number under every mark on the same Uke column, so the table is a genuine alternative for `net-graph`, `cost-field` totals, Netto lager and orders. Order-bars sit over the Rolle × Uke numbers.
- **Chain band** reads as text. «Vis som tabell» is always visible on the wall, and its table uses 13 px text and is sortable.
- **Focus rules that exist are sound.** Focus goes to the waiting message after confirming, and «Alle rader» returns focus to its opener.
- **No confirmation dialogs.** The consequence is stated above the button, and the button label carries the value («Bekreft ordre på 24»), so 2.5.3 Label in Name holds.
- **Timing passes 2.2.1 by exception.** The week-advance animation is 2 s or less, skippable, never blocks input and is off under reduced motion. The 24 h, 48 h and deadline limits fall under the 20-hour and deadline exceptions.
- **No flashing content (2.3.1).**
