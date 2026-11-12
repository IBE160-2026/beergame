---
title: "Accessibility review, round 2: DESIGN.md + EXPERIENCE.md (ØL-spillet)"
reviewer: adversarial accessibility review (agent), second round
date: 2026-11-10
standard: WCAG 2.1 AA + PRODUCT.md / NFR-6 commitments (charts have text or table alternatives, role and status never by colour alone, every Student flow from 360 px)
scope: DESIGN.md and EXPERIENCE.md (both status final, updated 2026-11-09), checked against review-accessibility.md and validation-report.md (round 1), PRODUCT.md, PRD FR-17 / FR-36 / FR-89
deferred: medium and low round-1 findings live in GitHub issue #26 and are not re-reported unless worse
---

# Accessibility review, round 2: ØL-spillet UX spines

## Verdict

**The round-1 blockers are fixed. The pair is fit for architecture work. It is not yet ready for an unqualified WCAG 2.1 AA claim: fix the three new high findings before story work.**

All round-1 critical and high findings with an accessibility angle are closed except one, which is partly closed:

- The week-table reflow rule is now concrete and testable.
- The drawing item has a value table and keyboard sliders.
- The focus ring is specified on every background.
- Text on tints has a full allowed/forbidden table.
- The matrix wall carries sign in a glyph.
- The Oversikt can be paused.
- The Ukeskrubber is a real slider.

All the ratios the spine states recompute correctly. The new Posisjon line is told apart from Netto lager by four non-colour cues.

The new problems come mostly from the states and rules the fixes added:

- **Unannounced states.** The new submit-failed, timed-out and offline states of the only irreversible action are not announced.
- **Timing.** The new Pause rule lets a peer shorten a Student's 24 h window to minutes. FR-17's per-Student timing accommodation has no surface.
- **Reflow scope.** The 320 px commitment covers Student surfaces only, although NFR-6 also covers Faglærer screens.

The shared disabled state and the summary Do's table also contradict other rules (N-M1, N-M4).

**Closure:** 14 closed · 1 partly closed (H11) · 0 open · 0 regressed.
**New findings:** 0 critical · 3 high · 4 medium · 10 low.

Contrast ratios below are computed from the DESIGN.md frontmatter hex values with the WCAG 2.x relative-luminance formula (the same formula as `vlib.contrast`).

---

## Contrast recomputation (new and changed pairs)

### Focus ring (`focus-ring`: 2 px `ink` ring, 2 px `paper` gap)

| Ring sits on | `ink` ring vs background | Notes |
|---|---|---|
| `paper` | 14.56 | ✔ |
| `future-tint` | 13.30 | ✔ |
| `hairline` (pressed) | 11.60 | ✔ |
| `lager-fill` | 10.67 | ✔ |
| `restordre-fill` (Varselbånd, near-Takeover row) | 10.51 | ✔ |
| `ink` fill (primary, active segment) | 1.00 | The `paper` gap carries it: `paper` vs `ink` 14.56 ✔ |
| `ink-secondary` (pressed primary) | 1.99 | The `paper` gap carries it: `paper` vs `ink-secondary` 7.31 ✔ |

### Focus ring inset (`focus-ring-inset`: 2 px `ink` frame plus 1 px `paper` inner line)

| Cell | `ink` frame vs cell | `paper` line vs cell | Carried by |
|---|---|---|---|
| `net-zero` / blank | 13.30 / 14.56 | 1.09 / 1.00 | `ink` ✔ |
| `net-neg-1` / `net-pos-1` / `flow-1` | 6.71 / 7.02 / 7.04 | 2.17 / 2.08 / 2.07 | `ink` ✔ |
| `net-neg-2` / `net-pos-2` / `flow-2` | **4.51** / 4.90 / 4.80 | 3.22 / 2.97 / 3.03 | `ink` ✔ (4.51 is the #26 L16 margin) |
| `net-neg-3` / `net-pos-3` / `flow-3` | 2.64 / 2.62 / 2.83 | 5.52 / 5.56 / **5.14** | `paper` ✔ |
| `net-neg-4` / `net-pos-4` / `flow-4` | 1.73 / 1.58 / **1.00** | 8.39 / 9.20 / 14.56 | `paper` ✔ |
| `restordre-fill` row | 10.51 | 1.39 | `ink` ✔ |
| `bar-base` (allocation preview) | 8.17 | 1.80 | `ink` ✔ |

The `ink` frame and the `paper` line are always 14.56:1 against each other, so the pair reads on every step. The spine's "≥ 4.51" and "≥ 5.14" claims are exact. On `flow-4` the frame merges with the fill and only the 1 px `paper` line shows. That passes 2.1 AA, which has no thickness rule.

### Text on tints (the darker allowed text tokens)

| Background | `ink` | `ink-secondary` | `ink-muted` | `lager` | `restordre` | `order-history` |
|---|---|---|---|---|---|---|
| `lager-fill` | 10.67 ✔ | 5.36 ✔ | 3.78 ✘ | 4.07 ✘ | 4.04 ✘ | 3.27 ✘ |
| `restordre-fill` | 10.51 ✔ | 5.28 ✔ | 3.72 ✘ | 4.01 ✘ | 3.98 ✘ | 3.22 ✘ |
| `future-tint` | 13.30 ✔ | 6.68 ✔ | 4.71 ✔ | 5.08 ✔ | 5.04 ✔ | 4.08 ✘ |
| `hairline` | 11.60 ✔ | 5.83 ✔ | 4.11 ✘ | 4.43 ✘ | 4.40 ✘ | 3.56 ✘ |
| `net-*-1`, `flow-1` | 6.71–7.04 ✔ | 3.37–3.53 ✘ | | | | |
| `net-*-2`, `flow-2` | 4.51 / 4.90 / 4.80 ✔ | 2.27–2.46 ✘ | | | | |
| `net-*-3/4`, `flow-3/4` | `paper` 5.14–14.56 ✔; `ink` 1.00–2.83 ✘ | | | | | |

Every figure in DESIGN → Colors → Text on tints matches.

### Posisjon line (1.5 px `ink-secondary`)

| Against | Ratio | Notes |
|---|---|---|
| `paper` | 7.31 ✔ | |
| `future-tint` | 6.68 ✔ | |
| `lager-fill` / `restordre-fill` | 5.36 / 5.28 ✔ | The spine says "≥ 5.3"; 5.28 rounds to it. Cosmetic only |
| Netto lager `lager` line | 1.32 | Luminance is nearly equal, so colour does not separate them in greyscale. The non-colour cues carry it (see Verified OK) |
| Netto lager `restordre` line | 1.33 | Same as above |
| `projection` (Replay) | 1.60 | Separated by dash and by the hollow end dot |

### Disabled and pressed states

| Pair | Ratio | Notes |
|---|---|---|
| Disabled label `ink-muted` on `future-tint` | 4.71 | Passes text contrast even though it is exempt |
| Disabled border `axis` on `paper` / `future-tint` | 1.61 / 1.47 | Exempt as an inactive component, but see N-L5 |
| Disabled fill `future-tint` on `paper` | 1.09 | |
| Pressed primary: `paper` on `ink-secondary` | 7.31 ✔ | |
| Pressed outlined: `ink` on `hairline` | 11.60 ✔ | |

Is a disabled control perceivable as disabled?

- **Filled controls:** yes, strongly. The `ink` fill turns into a near-white tint.
- **Outlined controls:** yes. The label drops from `ink` to `ink-muted` (2.82:1 between them), the border fades and the fill tints.
- **Problem:** a disabled *active* segment looks the same as a disabled inactive one (N-M1).

### Other rechecked pairs

| Pair | Ratio |
|---|---|
| Scrubber unfilled track `ink-muted` on `paper` | 5.16 ✔ |
| Scrubber filled `ink` vs unfilled `ink-muted` | 2.82 (position is marked by the `ink` handle and its «Uke 15» label, so OK) |
| Idle `ink-muted` borders on `restordre-fill` (secondary button in Varselbånd) | 3.72 ✔ |
| `ink-muted` borders on `lager-fill` | 3.78 ✔ |
| `ink-muted` borders on `hairline` | 4.11 ✔ |

---

## Task A: closure table

IDs are validation-report IDs; the round-1 accessibility ID is in brackets.

| ID | Finding | Verdict | Where it is fixed | Is the fix sufficient for WCAG? |
|---|---|---|---|---|
| **C1** (a11y C1) | Week table cannot hold 13 px at 320 px / 200 % | **Closed** | DESIGN → Layout & Spacing (Widths table, "Graf over tabell at narrow widths"); Typography "Text never shrinks to fit"; EXPERIENCE → Graf over tabell → Scrolling and Table semantics; Accessibility Floor → Reflow | Yes. Graph and table share one scroll region under the 1.4.10 two-dimensional exception, with sticky labels, a visible scrollbar, an HTML `<table>` in relative units, `role="region"` with a name and `tabindex="0"`, and product tests at 320/360 × 100/200 %. Residual nits: N-L2 (the "12 columns at 360" arithmetic), N-L3 («Sveip» caption), N-L7 (unbreakable labels against the 40 % cap). |
| **C2** (a11y C2) | Drawing item has no keyboard path | **Closed** | EXPERIENCE → Interaktiv oppgave (value table, sliders, screen reader, scoring); Accessibility Floor → Keyboard; DESIGN → Interaktiv oppgave | Yes. 2.1.1 and 2.5.1 are met: the table alone answers the item, scoring reads the table, and no task needs a drawn path. Nit: N-L11. |
| **H2** | No control for Pause / Sett inn KI-spiller | **Closed** (structure) | EXPERIENCE → Pausevalg, Sett inn KI-spiller; DESIGN → Pausevalg, Sett inn KI-spiller | The controls exist. The timing rule they introduce raises a new 2.2.1 problem (N-H2). |
| **H3** (a11y H1) | No focus ring, no pressed or disabled states | **Closed** | DESIGN frontmatter `focus-ring`, `focus-ring-inset`, `*.pressed-*`, `*.disabled-*`; Components → Interaction states → Fokusring; EXPERIENCE → Interaction states, Accessibility Floor → Focus and order | Yes for 2.4.7 and 1.4.11. Every claimed ratio recomputes (table above), including the `ink` fills, the red band and the dark matrix steps. Side effects: N-M1 (a locked selection becomes invisible), N-M2 (focus lost when a control disables itself), N-L1 (focus named on cells that are not focusable). |
| **H4** | About ten components had no row | **Closed** | Both spines now have Topplinje, Spillkort, Filopplasting, Veggfiltre, Meldingsskjema, Interaktiv oppgave, Pausevalg, Sett inn KI-spiller, Flagg, Etterspørselsbånd, Kjedens kostnad over tid | Yes. The a11y-relevant semantics are present: Flagg `aria-pressed`, Veggfiltre `aria-pressed`, Topplinje button name. |
| **H5** (a11y H4) | Ordrefelt errors, Enter, failed submit | **Closed** | EXPERIENCE → Ordrefelt subsection; State Patterns → Spill (Submitting, Submit failed, Timed out, Offline); DESIGN → Ordrefelt, `order-input.border-error-*`; Individuell test → Review before submit | Yes for 3.3.1, 3.3.2 and 3.3.3: an always-visible help line, `aria-describedby`, `aria-invalid`, `role="alert"`, error text in `restordre` 5.52 on `paper`, `type="text" inputmode="numeric"`, Enter moves focus to the button, named − / +, and a 3.3.4 review for the test. The new failure states have no announcement or focus rule (N-H1). |
| **H6** | No offline / stale pattern | **Closed** | EXPERIENCE → Tilkoblingslinje; State Patterns → All (Offline, Reconnected, Page error); Oversikt → Connection lost or stale; DESIGN → Tilkoblingslinje | Yes. It is a polite status region that never covers controls, with text and no colour fill. |
| **H7** | Surfaces without states | **Closed** | EXPERIENCE → State Patterns (Account and access, Test and assessment, After the game, Faglærer live, Admin) | Yes. A11y-relevant: test auto-submit and review are specified. |
| **H8** | «Posisjon» drawn in the Class-game Kjedebånd | **Closed** (superseded) | DESIGN → Mockup deviations, last row; EXPERIENCE → Hidden information (Posisjon row) | Superseded by the 2026-11-09 founder decision: Posisjon is now shown on purpose. Its colour-independence is verified below. |
| **H10** (a11y H2) | Matrix wall sign by hue alone, no legend | **Closed** | DESIGN → Colors (matrix steps note); Components → Matrisevegg (Cells, Legend, «Vis i plenum»); EXPERIENCE → Accessibility Floor (Matrisevegg row, "Never colour alone") | Yes for 1.4.1. A below-zero cell always carries a number or «−» (`ink` ≥ 4.51 / `paper` ≥ 5.14), a signed legend is always visible, the plenum view has a caption in words, and the 13 px table is a conforming alternative. Magnitude bins use monotonic lightness plus the legend, which is acceptable with the table available. Nit: N-L6 (text-only zoom turns numbers into glyphs). |
| **H11** (a11y H3) | Charts without alternatives | **Partly closed** | EXPERIENCE → Accessibility Floor, chart table (19 rows); DESIGN → Kostnad så langt, Kjedens kostnad over tid «Vis som tabell» | Every chart round 1 named now has an alternative. The spine also says every chart's alternative is "listed here", but at least six charts in the spines are not listed (N-M3). |
| **H12** (a11y H5) | Text on tints fails | **Closed** | DESIGN → Colors → Text on tints table and the link-on-tint rule; `link.on-tint-foreground`; Etterspørselsbånd (`ink` 600, 10.67); Varselbånd (no `ink-muted` or `restordre` text); Matrisevegg near-Takeover row | Yes for 1.4.3. Every pair recomputes. The summary Do's table contradicts it (N-M4). |
| **H13** (a11y H6) | Reflow at 360 px, not 320 | **Closed** for Student surfaces | DESIGN → Layout & Spacing (`reflow-min` 320, two-group table, Kjedebånd scale derived from width, tests at 320 and 360); EXPERIENCE → Responsive & Platform, Accessibility Floor → Reflow | Yes for Students. Faglærer surfaces are outside the commitment although NFR-6 covers them (N-H3). The two-group list is not exhaustive (N-L7). |
| **H14** (a11y H7) | Live Oversikt re-sorts under the reader | **Closed** | EXPERIENCE → Oppdater automatisk subsection; Matrisevegg → Updates; DESIGN → Oppdater automatisk | Yes for 2.2.2 (a pause mechanism, on by default), 2.4.3 (focus is kept by game ID and never moved) and 4.1.3 (only the Varselbånd and the counts, at most once a minute). The automatic re-sort hold keys on *focus*. A screen-reader virtual cursor in browse mode is not focus, so the manual switch is the real remedy; it exists. |
| **H15** (a11y H8) | Ukeskrubber not a slider | **Closed** | EXPERIENCE → Ukeskrubber subsection; DESIGN → Ukeskrubber (`ink-muted` track 5.16, step buttons at `tap-target-min`) | Yes for 2.1.1, 4.1.2, 4.1.3 and 1.4.11. |

Not counted, because they have no a11y angle: H1 (missing FR surfaces) and H9 (glossary).

---

## Task B: NEW findings

### Critical

None.

### High

#### N-H1. The new failure states of the irreversible order are silent to screen readers, and focus is undefined during submit

- **Where:**
  - EXPERIENCE → State Patterns → Student game: Submitting, Submit failed, Timed out, Offline with a typed order.
  - All surfaces: Action error, Session expired.
  - Accessibility Floor → Live announcements (the list does not include any of these).
  - Focus and order says only "After confirming, focus moves to the waiting message".
- **WCAG:** 4.1.3 Status Messages, 3.3.1 Error Identification, 2.4.3 Focus Order.
- **Failure scenario:**
  1. A screen-reader Student presses «Bekreft ordre på 24».
  2. The button becomes «Sender ordre på 24 …» and "is disabled". If that is the native `disabled` attribute, focus falls to `<body>`.
  3. The request fails, and «Ordren ble ikke sendt. Ingenting er bestilt ennå.» appears, but no rule says it is announced or where focus goes. The relabel to «Prøv å sende 24 igjen» is not reliably announced on a button that lost focus.
  4. The Student hears nothing, assumes the order went, and leaves.
  5. The group waits, and after the Inactivity limit the Seat is taken over. That Uke counts as not ordered toward the obligatory requirement (FR-17).
  6. «Vi vet ikke om ordren kom fram. Sjekker …», «Ordren på 24 er ikke sendt.» and the inline «Det ble ikke lagret. Prøv igjen.» have the same gap.
  7. So do «Setet ble tatt av en annen. Velg et annet.» and «Sara har allerede satt inn en KI-spiller.».
- **Fix:**
  - Add to Live announcements:
    - Submit failed: `role="alert"`.
    - Timed out: polite, then alert on failure.
    - Offline with a typed order: polite.
    - Action error: `role="alert"` on the inline message.
    - Seat taken and double insert: polite.
  - Specify that during Submitting the button keeps focus with `aria-disabled="true"` (and optionally `aria-busy`), never the native `disabled`.
  - On failure, focus stays on the retry button. On success, focus moves to the waiting message as now.
- **Status:** new. It extends the deferred status-message gap, already in #26 (M16), to states that did not exist in round 1.

#### N-H2. Timing: a peer can shorten a Student's window to minutes, the Inactivity limit can go below 20 h, and FR-17's timing accommodation has no surface

- **Where:**
  - EXPERIENCE → Pausevalg ("date and time (from now to the Spillfrist)").
  - Sett inn KI-spiller → Shown ("either the agreed time has passed or …").
  - Terms («Ventetid før KI tar over»).
  - No surface implements PRD FR-17 «A Lecturer can record a per-Student adjustment of the Inactivity limit, the share and any timed sitting, for Students with a right to it.»
  - PRD FR-36: the Lecturer sets the Inactivity limit per Class session; SM-C5 expects it to be lowered.
- **WCAG:** 2.2.1 Timing Adjustable. Round 1 passed timing only through the 20-hour exception, which these rules remove.
- **Failure scenario:**
  1. Sara sets «Ta pause til» a time 15 minutes from now.
  2. Jonas, a Student with extra-time rights who has not ordered, is offline.
  3. At the agreed time, Sara presses «Sett inn KI-spiller for Jonas». Jonas's normal 24 h window shrank to 15 minutes without his agreement or any warning. He gets the requirement warning only after the fact (the Student warning is #26 L18).
  4. Separately, a Faglærer who lowers the Inactivity limit to 6 h ends the 20-hour exception for every Student.
  5. The accommodation the PRD provides for Students "with a right to it" has no screen, so it will not be built.
- **Fix:**
  - Rule: the KI-spiller can be inserted only after the later of the agreed time and the Seat's own Inactivity limit (including any per-Student adjustment).
  - Rule: the agreed time cannot be earlier than the Inactivity limit from the moment the Pause is set, unless every Seat has seen it.
  - Add a Studentside block «Tilrettelegging» (spine-only): per-Student Inactivity limit, share and timed sitting, with the audit note.
  - In the Klasseøkt, either give the Inactivity-limit setting a floor of 20 h, or require the "KI-spiller tar setet ditt om N t" warning with a one-press «Gi meg mer tid» extension.
- **Status:** new. The missing Student warning before Takeover is already in #26 (L18) and is not re-counted.

#### N-H3. Faglærer surfaces have no reflow or zoom commitment, although NFR-6 covers them

- **Where:**
  - DESIGN → Layout & Spacing → Widths ("every Student surface works there").
  - EXPERIENCE → Responsive & Platform: «Faglærer laptop | 1440 design canvas … Usable on a tablet».
  - Accessibility Floor → Reflow ("every Student flow").
  - PRODUCT.md / NFR-6: «Student and Lecturer screens meet WCAG 2.1 AA».
- **WCAG:** 1.4.10 Reflow (320 CSS px, that is 1280 px at 400 %). 1.4.4 for the non-matrix text.
- **Failure scenario:** a low-vision Faglærer zooms the laptop to 400 % to read «Lag Klasse», «Klasseøkt», the Varselbånd and the right rail («Venter ellers», «Klassens kostnad», «Trakt»), or the Meldingsskjema. The spine sets a 1440 px canvas and a tablet minimum only. A build that follows it can scroll in two dimensions on every Faglærer form, and the Varselbånd's actions «Send Melding» and «Pause spillet» can end up off-screen to the right. Only the Matrisevegg has a defined fallback (its table).
- **Fix:** extend `{spacing.reflow-min}` to every Faglærer and Admin surface. Add a Faglærer column to the two-group table:
  - Must reflow: forms, Varselbånd, right rail, Meldingsskjema, Eksport, Admin lists.
  - Two-dimensional exception: Matrisevegg, Fordelingsforhåndsvisning, the Debrief and Spillinnsikt Rolle × Uke tables.
  - State that at 320 px the right rail stacks under the wall and the Varselbånd actions wrap under its text.

### Medium

#### N-M1. The shared disabled state erases the chosen option on locked settings

- **Where:** DESIGN → Interaction states, Disabled row. The filled column (active segment of `view-toggle` / `segmented-choice`, `switch` on) is "`future-tint` fill, 1 px `axis` border, `ink-muted` label", the same as the outlined column. EXPERIENCE → Valgknapper ("They lock at the Start date"), Bryter (follows Valgknapper), State Patterns → Klasseøkt «After Start date: Game settings are read-only», Innsatsnivå «Locked at the Start date».
- **WCAG:** 1.3.1 Info and Relationships (visual state lost), 4.1.2 (the visual state does not match `aria-checked`), and the PRODUCT "status never by colour alone" spirit.
- **Failure scenario:** after the Start date a Faglærer opens the Klasseøkt to check whether «Gruppedebrief» or «LLM-spillere» was chosen. Every segment renders the same tint, border and label, and the switch "on" looks like "off". The chosen value is only available to assistive technology. Sighted users, including Assistenter checking settings, cannot see it.
- **Fix:** add a «Låst» (read-only) state distinct from Disabled:
  - Active segment: keeps the `ink` 1.4 px border and `ink` label on `future-tint`, plus a text mark («valgt»).
  - Inactive segments: `ink-muted` label.
  - Switch: shows its state word.
  - A line under the group: «Låst fra startdatoen.»

#### N-M2. Controls that disable themselves while focused drop keyboard focus

- **Where:**
  - EXPERIENCE → Ordrefelt (− / +: "− is disabled at 0 … + … disabled at {maks}").
  - State Patterns → Spill → Submitting ("is disabled").
  - Sett inn KI-spiller (the button disappears when pressed).
  - Pausevalg (the form opens "in place"; «Avbryt» closes it).
  - DESIGN → Interaction states gives `aria-disabled` only to "disabled controls that explain themselves (the empty «Bekreft ordre»)".
- **WCAG:** 2.4.3 Focus Order, 2.4.7 Focus Visible (focus lands on `<body>` and the ring vanishes), 2.1.1.
- **Failure scenario:**
  1. A keyboard Student presses «Én færre» down to 0. The segment becomes natively disabled and focus is lost.
  2. The next Tab starts from the top of the page: header, Graf og tabell region, then back to the field.
  3. The same happens when «Sett inn KI-spiller for Jonas» is replaced by the KI-spiller row, and when «Ta pause» swaps into the in-place form.
- **Fix:**
  - Rule: a control that becomes unavailable while focused uses `aria-disabled` and keeps focus.
  - A control that is removed moves focus to its replacement: the Setestatus row text with `tabindex="-1"`, or the first field of the opened form, and back to «Ta pause» on «Avbryt».
- **Status:** partly already in #26 (M18) for the in-place panel focus. The − / + and Submitting cases are new.

#### N-M3. At least six charts have no alternative, although the spine says every alternative is "listed here"

- **Where:** EXPERIENCE → Accessibility Floor → Charts ("every chart has a text or table alternative, listed here"). Charts present in the spines but missing from the list:
  1. The Replay-gjennomgang chart ("Klassespill and Replay on one axis", UJ-5 step 8; its pending state is "a Skjelett of the chart"). This is a Student-facing, required step (Stegene).
  2. The Delt skjerm «Netto lager per Rolle» chart (Debrief sequence, Delt skjerm row). Only «Kostnad, kr» per Role is listed.
  3. The class median graph over the matrix wall on the Oversikt (DESIGN → Layout & Spacing → Devices, Faglærer row).
  4. «Kjedekost per uke, snitt per spill» (Cost picture, Faglærer row).
  5. «Alle spill side om side» for Students (FR-86) and the landing's «Alle spillene på én skjerm». The Matrisevegg row covers «Vis i plenum», not these.
  6. Debrief step 4 «Dette kostet det senere» and «Dette så de andre i Uke 11», if they are charts. The spine does not say.
- **WCAG:** 1.1.1 Non-text Content. NFR-6 / PRODUCT «Charts have text or table alternatives».
- **Failure scenario:** a screen-reader Student reaches the Replay-gjennomgang, the required step after the Replay. The comparison is a chart with no listed table, so they get only the AI text (or nothing, when the LLM is down: «The same chart and numbers from code»).
- **Fix:**
  - Add the six rows:
    - Replay-gjennomgang: «Vis som tabell» (Uke, Klassespill netto lager, Replay netto lager, kost).
    - Delt skjerm Netto lager per Rolle: the Debrief Rolle × Uke table.
    - Oversikt median graph: the «Median, Fabrikk» and «Kjedekost/uke, snitt» wall rows in the table view.
    - Alle spill side om side / landing matrix: the same table offer as the Matrisevegg.
  - Add a catch-all sentence: "A chart not in this table is a spec error."

#### N-M4. The Do's and Don'ts tint rule contradicts the Text on tints table

- **Where:** DESIGN → Do's and Don'ts: «Keep text on tints to `ink` or `ink-secondary`, and on dark steps to `paper`» / «`lager`, `restordre` or `ink-muted` text on any fill». This conflicts with DESIGN → Colors → Text on tints (and the Disabled state).
- **WCAG:** 1.4.3 Contrast (Minimum).
- **Failure scenario:**
  - The summary allows `ink-secondary` on every tint. On `net-*-1` / `flow-1` it is 3.37–3.53 and on `net-*-2` / `flow-2` it is 2.27–2.46, both failing. A developer who uses the quick-reference table for a secondary label in a matrix or Netto lager cell ships failing text.
  - In the other direction, the Don't forbids `ink-muted` "on any fill", while the Disabled state, the read-only Ordrefelt and the Text on tints table all put `ink-muted` on `future-tint` (4.71, allowed). The two tables cannot both be followed.
- **Fix:** reword the Do as «Keep text on tints to the pairs in Colors → Text on tints: `ink` or `ink-secondary` on `lager-fill` / `restordre-fill`, `ink` only on steps 1–2, `paper` on steps 3–4». Reword the Don't as «`lager`, `restordre` or `ink-muted` text on `lager-fill`, `restordre-fill`, `hairline` or a matrix step».

### Low

- **N-L1. Focus is specified on cells the behaviour spine makes unfocusable.** DESIGN → Fokusring puts the outer ring on "the Din ordre cell" and the inset frame on "matrix cells that take focus". EXPERIENCE → Graf over tabell says "Table cells are not focusable", and the Matrisevegg focuses rows (game ID), not cells. Criterion: 2.4.7 (the inconsistency will confuse implementers). *Fix:* remove "the Din ordre cell" and "matrix cells" from the Fokusring bullet, or state which wall cells are focusable and why.
- **N-L2. "12 columns at 360 px" does not follow from the column rule, and the Responsive row repeats the claim.** DESIGN → Graf over tabell at narrow widths sets the column at max(1.6 em, widest number + 0.25 em). «−13» in Source Sans 3 tabular figures is about 1.5 em, so columns are about 1.75 em (22.8 px). At 360 px that gives (360 − 32 − 76) / 22.8 ≈ 11 columns, and about 9 at 320 px, not 12 and 10. EXPERIENCE → Responsive says FR-23 is met at 360 px "with no horizontal scroll". PRODUCT promises «all Seat data … visible on a 360 px wide screen without horizontal scroll». No WCAG failure, because the region scrolls and keeps nå in view, but the product-commitment claim is wrong as written. *Fix:* restate as "12 columns when every number is two characters or fewer; otherwise the earliest past Uke scrolls out", or lower `week-col-min` to fit 1.75 em.
- **N-L3. «Sveip for tidligere uker» names a touch gesture only** (DESIGN → Graf over tabell at narrow widths). At 320 px from 400 % laptop zoom, or with a keyboard, there is nothing to swipe. Criteria: 3.3.2, and 1.3.3 in spirit. *Fix:* «Rull sidelengs for tidligere uker», or give the region's accessible description the arrow-key hint.
- **N-L4. Posisjon and Netto lager labels have no collision rule, and the lines have equal luminance.** Both direct labels («Restordre 13», «Posisjon 3») sit at the nå x-position. When På vei is small, the two values are close and the labels overlap. `ink-secondary` vs `lager` / `restordre` is 1.32 / 1.33, so where the lines coincide only the 4 px squares separate them. Criterion: 1.4.1 support, legibility. *Fix:* nudge the labels vertically apart with a leader, and draw Posisjon on top of Netto lager.
- **N-L5. The focusable, pressable disabled «Bekreft ordre» has a 1.61:1 boundary.** The inactive-component exemption in 1.4.11 is shaky for a control that is focusable and shows an error when pressed. Its `ink-muted` label (4.71) still identifies it. *Fix:* for the "disabled but explains itself" case, use the `ink-muted` border (5.16), and keep `axis` for truly inert controls.
- **N-L6. Text-only zoom turns matrix-wall numbers into glyphs.** A cell prints its number only "when the number fits". With 200 % text and cells sized in px, numbers become «−» or blank, which is a content loss under 1.4.4. The 13 px table view rescues it as an alternate version. *Fix:* size wall cells in `em`. Already in #26 (M25).
- **N-L7. Gaps in the reflow two-group list and the label-column cap.** Student components missing from both columns: Kjedens regning, Kjedens kostnad over tid, Etterspørselsbånd with its table, the Debrief step 1 strip, Ukeskrubber, Delt skjerm. Separately, at 320 px with 200 % text the 40 % label cap is about 115 px, and single-word labels such as «Restordre» (about 112 px at 26 px) or the Alle rader row «Restordre» cannot "wrap to two lines" without hyphenation. Criteria: 1.4.10, 1.4.4. *Fix:* complete the list, and require `hyphens: auto` under `lang="nb"` for row labels (`lang` itself is #26 L14). Related to #26 (M20).
- **N-L8. The Graf over tabell graph is not marked `aria-hidden`.** Accessibility Floor: "A chart whose alternative is a visible table on the same columns needs nothing more". An SVG left exposed leaks tick labels, «Nå», «Posisjon 3» and «Restordre 13» to screen readers as orphan text before the table. Criterion: 1.3.1. *Fix:* "every chart is `aria-hidden`; the visible table or the named alternative is the accessible version".
- **N-L9. The near-Takeover wall row is marked by tint alone inside the wall, and what gets tinted is ambiguous.** The Varselbånd names the game in text, so 1.4.1 is met overall. Inside the wall, though, the urgent row differs from its neighbours only by `restordre-fill`. The spine also does not say whether the tint replaces the row's matrix-step cells (data loss) or only the label area. *Fix:* tint only the label cells, and add a short text marker («KI om 1 t») in the row.
- **N-L10. The Pausevalg date and time field has no validation.** EXPERIENCE → Pausevalg allows "from now to the Spillfrist" but gives no error for a past time or one after the Spillfrist, and no label for the time part. Criteria: 3.3.1, 3.3.3. *Fix:* «Velg et tidspunkt mellom nå og Spillfristen, {dato}.» using the Ordrefelt error pattern.
- **N-L11. Interaktiv oppgave point sliders are underspecified.** Unanswered Uker show "no point", so there is no slider to Tab to, and the keyboard path is the table. Say so. `aria-valuemin` / `aria-valuemax` are not given. 8 px points with 36 Uker at 320 px cannot meet "Tap targets at least 44 px … for every control" (2.5.5 is AAA in 2.1, but it is the product's own rule). *Fix:* "an unanswered Uke's slider starts empty (`aria-valuetext` «Uke 3: ikke besvart») and Up sets 0", give min and max, and exempt chart points from the 44 px rule with column-tap and the table as the alternative.

---

## Verified OK

- **Posisjon is not distinguished by colour alone.** There are four cues besides hue: no area fill, 1.5 px against 2 px stroke, 4 px square markers at every Uke, and the direct label «Posisjon n». It is solid against the dashed projection. In the table it is a plain-number row against filled Netto lager cells. Contrast is 7.31 on `paper`, 6.68 on `future-tint` and 5.28–5.36 on the fills, so it passes 1.4.11. The Accessibility Floor names its alternative (the Posisjon row) and "Never colour alone" lists it.
- **Every contrast figure stated in DESIGN recomputes:** Colors table, Text on tints, the matrix steps, the focus ring and inset ring, pressed (7.31 / 11.60) and disabled labels (4.71).
- **Disabled controls are perceivable as disabled** (fill, border and label all change), and the explaining disabled button stays focusable with `aria-disabled`.
- **Ordrefelt:** the label is always visible, the help line is tied with `aria-describedby`, the error is in text and not colour alone, Enter never submits, and «Bekreft ordre på 24» carries the value (2.5.3 Label in Name).
- **Graf over tabell keyboard path:** one `tabindex="0"` region, table cells not focusable (which removes the hundreds of tab stops in #26 M18), `<th scope>` headers, and the scrollbar visible rather than overlay.
- **Timing passes elsewhere.** The Uke-overgang animation is 2 s or less, skippable, never blocks input and is off under reduced motion. Takeover (24 h default), the 48 h group Debrief and the Testfrist fall under the 20-hour exception. The 10 s submit timeout and the 10 s skeleton timeout are system timeouts, not user time limits. Session expiry now keeps the typed order, which partly covers #26 L18.
- **Motion:** no shimmer, no spinners, no celebration, the Skjelett is static and wall values update in place. No flashing content (2.3.1).
- **Status messages that are covered:** − / + value, test autosave «Lagret», Tilkoblingslinje, Pause set and ended, the Oversikt throttle and the Ukeskrubber result.
- **Target size:** strengthened from "primary controls" to "every control" on phone (part of #26 M22). The Topplinje button, the scrubber step buttons and «Ta tilbake setet» are at `tap-target-min`.
- **Never colour alone:** Setestatus (dot shape plus text), quiz (text), invalid rows (reason), AI (word), Veggfiltre (weight plus underline plus `aria-pressed`), Kjedebånd (labels plus bar direction), first large order (dot plus «Uke n»), wall sign (number or «−» plus legend).
- **Meldingsskjema is its own page and Back works,** which removes the modal-trap risk from #26 M18 for that surface.
- **No dangling pointers found.** Every "→ section" cross-reference between the spines resolves. No round-1 fix was lost in the editorial merge: the focus-after-confirm, Alle rader return-focus, reduced-motion, "Tilkoblingslinje never covers controls" and Enter-moves-focus rules are all still present.
