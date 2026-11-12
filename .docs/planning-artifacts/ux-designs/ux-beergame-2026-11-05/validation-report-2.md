# Validation Report, round 2 — beergame (ØL-spillet)

- **DESIGN.md:** `DESIGN.md`
- **EXPERIENCE.md:** `EXPERIENCE.md`
- **Run at:** 2026-11-10
- **Round 1:** `validation-report.md`

## Overall verdict

The fix pass did its job. All 17 round-1 critical and high findings are closed, and each fix lives in a named place in the spines rather than in a promise: the week table has a real 320 px and 200 % text contract, the drawing item has a value table and keyboard sliders, the Ordrefelt has its full error, submit, timeout and offline story, focus and interaction states are tokenised, and the Terms table maps PRD nouns to UI strings. All 41 component names match across both files, every token reference resolves and every stated contrast ratio recomputes. **Architecture can start now**, and so can story work for every Student surface and for Faglærer setup. Three areas need one more short pass before their stories: **Faglærer live intervention** (manual Takeover, starting games, the «in the room» limit and completion corrections have no control, and «Pause spillet» has a button but no behaviour), **Lærers testspill** (no states, no statement of what it reuses), and **the plausibility question** (FR-70 has no surface). Separately, the Mockup deviations table no longer lists every deviation, and the fix pass introduced a few ambiguities of its own.

The accessibility review confirms that picture and sharpens it in one direction. **The colours are verified:** every ratio the spine states recomputes, the focus ring reads on every background including the `ink` fills and the dark matrix steps, text on tints has a full allowed/forbidden table, and the new Posisjon line is told apart from Netto lager by four cues besides colour. **There are no critical findings**, and 14 of the 15 round-1 items with an accessibility angle are closed; H11 (chart alternatives) is only partly closed. But there are **3 new high findings**, and all three come from the states and rules the fixes added: the submit-failed, timed-out and offline states of the irreversible order are not announced and focus during submit is undefined; the Pause rule lets a peer shrink a Student's 24 h window to minutes; and the 320 px commitment covers Student surfaces only, although NFR-6 also covers Faglærer screens. Two of those three overlap rubric findings and are merged here at high. The reviewer's verdict: fit for architecture, not yet ready for an unqualified WCAG 2.1 AA claim, so fix the highs before story work.

After merging duplicates across the two reviewers: **0 critical, 4 high, 11 medium and 23 low** findings. Four findings were reported by both reviewers and are counted once, at the higher severity: the Pause / Sett inn KI-spiller eligibility (R2-H2), the Student-only 320 px rule (R2-H3), charts with no listed alternative (R2-M5) and the «12 columns at 360 px» arithmetic (R2-L4). Two low findings re-report items already in [#26](https://github.com/IBE160-2026/beergame/issues/26) that the reviewers chose to flag again (M11, M25).

## Status etter retting (2026-11-10)
R2-H1 til R2-H4 er rettet i dokumentene, se statuslinjene under hvert funn. Middels og lave funn er utsatt til issue #26. HTML-versjonen viser rapporten slik den var før rettingen.

## Closure of round-1 critical and high

The rubric walker checked all 17; the accessibility reviewer checked the 15 with an accessibility angle. They agree on every item except H11.

| ID | Rubric | Accessibility | Note |
|---|---|---|---|
| C1 | closed | closed | Week table: one scroll region, sticky labels, column minimum, HTML `<table>`, tests at 320/360 × 100/200 %. Residue: column-count arithmetic (R2-L4), «Sveip» (R2-L15), label cap (R2-L19). |
| C2 | closed | closed | Drawing item has a value table and keyboard sliders; the table alone answers. Residue: no minus key on phone keypads (R2-M4), slider details (R2-L23). |
| H1 | closed | — (no a11y angle) | Every listed FR now has a row. The same class of gap remains for FRs round 1 did not list (R2-H1, R2-M1). |
| H2 | closed | closed (structure) | Pausevalg and Sett inn KI-spiller exist. The eligibility and timing rule they introduce is new finding R2-H2. |
| H3 | closed | closed | Focus ring and inset ring recompute on every background. Side effects: R2-L2, R2-L3, R2-M9, R2-M10, R2-L14. |
| H4 | closed | closed | All ten components have a row on both sides under the same name. Residue: charts still without a row (R2-M5). |
| H5 | closed | closed | Ordrefelt help line, error, Enter and failure states specified. The new failure states are not announced (R2-H4); help-line order (R2-L5). |
| H6 | closed | closed | Tilkoblingslinje, global Offline / Reconnected / Page error, Oversikt «Connection lost or stale». |
| H7 | closed | closed | Every named surface has states. Residue: Lærers testspill and plenum (R2-M6), smaller rows (R2-L7). |
| H8 | closed (founder decision) | closed (superseded) | Posisjon shown in both rounds (memlog 2026-11-09). Residue: Kjedebånd label (R2-L9). |
| H9 | closed | — (no a11y angle) | Terms table maps PRD terms to UI strings. Residue: its own rules not followed (R2-L13). |
| H10 | closed | closed | Matrisevegg sign carried by number or «−» glyph plus signed legend. Nit: text-only zoom (R2-L18, already in #26 M25). |
| H11 | closed | **partly closed** | **Reviewers differ.** Rubric: every chart round 1 named now has an alternative. A11y: the table claims to list every chart, but at least six are missing, including the Student-facing Replay-gjennomgang chart (R2-M5). |
| H12 | closed | closed | Text on tints table; every ratio recomputes. The summary Do's table contradicts it (R2-M11). |
| H13 | closed | closed | **Student surfaces only.** Faglærer and Admin surfaces sit outside the 320 px commitment (R2-H3); Spillkort misclassified (R2-M3); two-group list incomplete (R2-L19). |
| H14 | closed | closed | Oppdater automatisk: on by default, re-sort frozen while focus is inside, focus kept by game ID. Residue: does the Varselbånd freeze too (R2-L8). |
| H15 | closed | closed | Ukeskrubber is a `role="slider"` with step buttons and a polite readout. |

**Tally.** Rubric: 17 closed, 0 partly closed, 0 open, 0 regressed. Accessibility: 14 closed, 1 partly closed (H11), 0 open, 0 regressed; H1 and H9 not assessed.

## Category verdicts

- Flow coverage — adequate: UJ-1 to UJ-9 verbatim with protagonist, steps and climax; Faglærer intervention inside cited FRs has no control (R2-H1), and FR-70/71/76 have no surface.
- Token completeness — adequate: every reference resolves and every ratio recomputes, including the focus rings; only small internal inconsistencies remain.
- Component coverage — adequate: 41 of 41 names identical in both files; «Pause spillet», Spillkort reflow and signed Interaktiv oppgave cells are open.
- State coverage — adequate: global rows exist and Spill has 21 states; Lærers testspill and the Faglærer side of plenum have none.
- Visual reference coverage — adequate: all mockups cited with panels; the Mockup deviations table misses the accessibility fixes, two of which would ship failing contrast.
- Bloat & overspecification — adequate: growth is mostly load-bearing; the cost picture and Posisjon are stated six times each.
- Inheritance discipline — adequate: sources, UJ headings and founder overrides consistent; reflow stops at Student surfaces and the spines do not point to #26.
- Shape fit — strong: canonical order, all eight sections, every invented section load-bearing; no new findings.
- Accessibility (reviewer) — fit for architecture, not yet an unqualified WCAG 2.1 AA claim: colours verified, 0 critical, 3 high, 4 medium, 10 low as filed.

## New findings by severity

IDs are this report's own numbering. Each reviewer's original ID is given in brackets: «rubric N-F1», «a11y N-H2» and so on. Line numbers (L123) refer to the spines as they stand on 2026-11-10.

### Critical (0)

None. Neither reviewer filed a critical finding.

### High (4)

**R2-H1 [rubric N-F1]** — In-scope Faglærer intervention actions have no control, state or flow (§ EXP Varselbånd L298; DESIGN L674; OQ5 L742)
**Status:** Rettet 2026-11-10 — se EXPERIENCE.md → Spillstyring, Tilrettelegging, Fullføringsretting; DESIGN.md → Components (Faglærer).

These actions sit inside FRs the spine cites, so their stories have no UX contract:
- **FR-37:** a Faglærer or Assistent triggers Takeover of any Seat at any time, and fills all absent Seats in one game or all games in one action (the PRD's example is the start of a Labtime). The Varselbånd announces «KI overtar om 1 t» but offers only «Send Melding» and «Pause spillet».
- **FR-22:** the Faglærer starts any Class game or all at once. The scheduling aid is listed as spine-only in OQ5 but has no specification. (The Student's «presses start» is already M9 in #26.)
- **FR-36:** marking a game «in the room» during a Labtime with a shorter Inactivity limit.
- **FR-17:** correcting a Student's Completion status with a reason, a make-up solo game, per-Student adjustments of the limit and share, and «message those who have not met the requirement» in one action. The per-Student timing adjustment also carries the accessibility angle in R2-H2.

Fix: Add rows to Oversikt / Spillinnsikt / Studentside, for example a Faglærer variant of Sett inn KI-spiller («Sett inn KI-spiller i alle ledige seter»). Alternatively, list each one in OQ5 as "spine-only, no layout yet" with the surface that owns it.

**R2-H2 [a11y N-H2 · rubric N-F3]** — Sett inn KI-spiller and Pause: the eligibility rule conflicts with how a Pause ends, and lets a peer shrink a Student's 24 h window to minutes (§ EXP Pausevalg L233–242, Sett inn KI-spiller L229, L244–252, L390; UJ-4 L669; Terms; PRD FR-17, FR-36, FR-89) — Student warning part already in #26 (L18)
**Status:** Rettet 2026-11-10 — se EXPERIENCE.md → Pausevalg, Sett inn KI-spiller, UJ-4 (beslutning 2026-11-10: bare Faglærer setter pausetid; Faglærer kan gi enkeltstudenter mer tid).

*Eligibility (rubric, medium).* The Sett inn KI-spiller row acts "during a Pause" (L229), but any Student ends the Pause by ordering (L241, L390; FR-89), and Setestatus, which hosts the button, appears on Spill only after the Student has confirmed an order (L227). So in UJ-4's failure path, Sara's own order has ended the Pause before she can see «Sett inn KI-spiller for Jonas». The «Shown» rule (L248) does not require a running Pause, so the two rows disagree, and nothing says whether the right survives the Pause or how it interacts with the automatic Takeover clock. Introduced by the H2 fix.

*Timing (accessibility, high; WCAG 2.2.1).* Round 1 passed timing only through the 20-hour exception, which these rules remove. Sara sets «Ta pause til» 15 minutes from now; Jonas, who has extra-time rights and has not ordered, is offline; at the agreed time Sara inserts a KI-spiller and Jonas's 24 h window has shrunk to 15 minutes without his agreement or warning. Separately, a Faglærer who lowers the Inactivity limit to 6 h (FR-36; SM-C5 expects it to be lowered) ends the 20-hour exception for every Student. FR-17's per-Student adjustment of the Inactivity limit, share and timed sitting has no screen, so it will not be built.

Fix:
- Drop "during a Pause". The KI-spiller can be inserted only after the *later* of the agreed time and the Seat's own Inactivity limit (including any per-Student adjustment); once that has passed, the right lasts until the absent Seat orders or automatic Takeover happens, whether or not the Pause has ended.
- The agreed time cannot be earlier than the Inactivity limit from the moment the Pause is set, unless every Seat has seen it.
- Add a Studentside block «Tilrettelegging» (spine-only): per-Student Inactivity limit, share and timed sitting, with the audit note.
- In the Klasseøkt, give the Inactivity-limit setting a floor of 20 h, or require a «KI-spiller tar setet ditt om N t» warning with a one-press «Gi meg mer tid» extension.

**R2-H3 [a11y N-H3 · rubric N-I1]** — The 320 px reflow commitment covers only Student surfaces, although NFR-6 covers Faglærer screens too (§ DESIGN Layout & Spacing → Widths L529; EXP Responsive & Platform, Accessibility Floor → Reflow L496, L541; PRODUCT.md NFR-6)
**Status:** Rettet 2026-11-10 — se DESIGN.md → Layout & Spacing; EXPERIENCE.md → Responsive & Platform.

DESIGN says "every Student surface works there", and EXP says "every Student flow". Responsive gives the Faglærer laptop only a 1440 design canvas and "usable on a tablet". WCAG 1.4.10 (320 CSS px, that is 1280 px at 400 %) and 1.4.4 also apply to Lag Klasse, Klasseøkt with its Datolinje, Spørsmål og vekter, the Oversikt right rail, Meldingsskjema and Admin. *Failure scenario (accessibility):* a low-vision Faglærer zooms the laptop to 400 % to read the Varselbånd and the right rail («Venter ellers», «Klassens kostnad», «Trakt»). A build that follows the spine can scroll in two dimensions on every Faglærer form, and the Varselbånd's «Send Melding» and «Pause spillet» can end up off-screen to the right. Only the Matrisevegg has a defined fallback.

Fix: Extend `{spacing.reflow-min}` to every Faglærer and Admin surface, and add a Faglærer column to the two-group table:
- Must reflow: forms, Varselbånd, right rail, Meldingsskjema, Eksport, Admin lists.
- Two-dimensional exception: Matrisevegg, Datolinje, Fordelingsforhåndsvisning, the Debrief and Spillinnsikt Rolle × Uke tables.
- At 320 px the right rail stacks under the wall and the Varselbånd actions wrap under its text.

**R2-H4 [a11y N-H1]** — The new failure states of the irreversible order are silent to screen readers, and focus is undefined during submit (§ EXP State Patterns → Student game: Submitting, Submit failed, Timed out, Offline; All surfaces: Action error, Session expired; Accessibility Floor → Live announcements, Focus and order) — extends #26 (M16)
**Status:** Rettet 2026-11-10 — se EXPERIENCE.md → Accessibility Floor (kunngjøringer og fokus ved innsending).

WCAG 4.1.3, 3.3.1, 2.4.3. A screen-reader Student presses «Bekreft ordre på 24». The button becomes «Sender ordre på 24 …» and "is disabled"; if that is the native `disabled` attribute, focus falls to `<body>`. The request fails and «Ordren ble ikke sendt. Ingenting er bestilt ennå.» appears, but no rule says it is announced or where focus goes, and the relabel to «Prøv å sende 24 igjen» is not reliably announced on a button that lost focus. The Student hears nothing, assumes the order went, and leaves. The group waits; after the Inactivity limit the Seat is taken over, and that Uke counts as not ordered toward the obligatory requirement (FR-17). «Vi vet ikke om ordren kom fram. Sjekker …», «Ordren på 24 er ikke sendt.», «Det ble ikke lagret. Prøv igjen.», «Setet ble tatt av en annen. Velg et annet.» and «Sara har allerede satt inn en KI-spiller.» have the same gap.

Fix:
- Add to Live announcements: Submit failed `role="alert"`; Timed out polite, then alert on failure; Offline with a typed order polite; Action error `role="alert"` on the inline message; Seat taken and double insert polite.
- During Submitting the button keeps focus with `aria-disabled="true"` (optionally `aria-busy`), never the native `disabled`.
- On failure, focus stays on the retry button. On success, focus moves to the waiting message as now.

### Medium (11)

**R2-M1 [rubric N-F2]** — Three in-scope FRs with a UI have no surface: FR-70, FR-71, FR-76 (§ EXP IA L95–125; State Patterns; OQ5)

FR-70 is the optional five-point «how believable were the KI-spillere» question after the Replay and after any Class game with AI players; it is Student-facing. FR-76 is Admin deletion on request, and FR-71 the Admin's pseudonymised export. None is in the IA, State Patterns or OQ5.

Fix: Add an IA row and one state row each, or list them as spine-only in OQ5.

**R2-M2 [rubric N-C1]** — «Pause spillet» (the Faglærer pause, issue #25) is a button with no behaviour (§ EXP Varselbånd L298; DESIGN L674; OQ5)

The Varselbånd row places it, and OQ5 lists it as undrawn. Nothing states whether it opens the Pausevalg form (with or without an agreed time), whether a Student's order ends it as with FR-89, whether it stops the «KI overtar om 1 t» countdown in the band, or whether it is audit-logged. The Student-facing copy is M9 in #26; the Faglærer-side behaviour is not.

Fix: Add a row under Faglærer, or a «Faglærer» column in the Pausevalg subsection.

**R2-M3 [rubric N-C2]** — Spillkort is on the must-reflow list but holds a 12-column table (§ DESIGN L533, L646; EXP L230)

Spillkort is on the "must reflow to 320 px, no horizontal scroll" list, yet holds "a mini `net-graph` over a `week-table` … in the same 12-column window". At the 13 px floor and 1.6 em columns, 12 columns need about 250 px plus the 76 px label column. That does not fit in a bordered card at 320 px and fits at 360 px only with zero padding (see R2-L4). The table is real text; only the graph is `aria-hidden`.

Fix: Give the card its own window (for example nå − 3 … nå + 4), or move Spillkort to the two-dimensional list.

**R2-M4 [rubric N-C4]** — Interaktiv oppgave cells take negative numbers, but the reused keypad pattern has no minus key (§ EXP L202, L287)

The cells take "whole numbers, with a leading minus where the quantity can be negative, and use the Ordrefelt error pattern". The Ordrefelt pattern is `inputmode="numeric" pattern="[0-9]*"`. Phone numeric keypads, iOS in particular, have no minus key, and the pattern rejects «−». A phone Student cannot type a negative stock in a deadline-bound test item. Introduced by the C2 fix.

Fix: For signed cells use `inputmode="text"` (or `decimal` plus a ± segment) and the pattern `-?[0-9]+`; accept both U+2212 and U+002D; say so in the Interaktiv oppgave subsection.

**R2-M5 [a11y N-M3 · rubric N-C3]** — At least six charts have no component row or listed alternative, although the table says it lists every chart (§ EXP Accessibility Floor → Charts L497–519; L508, L510, L570, L592, L684; DESIGN L541; UJ-3 step 2)

The chart alternatives table says every chart's alternative is "listed here". Missing:
- The Replay-gjennomgang chart «Klassespill and Replay on one axis» (UJ-5 step 8). Student-facing and a required step; its pending state is "a Skjelett of the chart".
- Delt skjerm «Netto lager per Rolle» and its chain view (only «Kostnad, kr» per Role is listed).
- The Oversikt class median graph over the matrix wall.
- «Kjedekost per uke, snitt per spill» / «Snitt per ferdig spill, per Rolle».
- «Alle spill side om side» for Students (FR-86) and the landing's «Alle spillene på én skjerm».
- Debrief step 4 «Dette kostet det senere» and «Dette så de andre i Uke 11», if they are charts; the spine does not say.

The rubric also notes component rows missing for the Debrief step 1 strip «Ditt netto lager, hele spillet» and Klasseøkt «Kjeden ved start». *Accessibility failure (WCAG 1.1.1, NFR-6):* a screen-reader Student reaches the Replay-gjennomgang, the required step after the Replay, and gets only the AI text, or nothing when the LLM is down. This is why the accessibility reviewer rates H11 only partly closed. Merged at the reviewer's medium (rubric filed it low).

Fix:
- State the reuse in one line each, for example "Kjeden ved start = Kjedebånd, four Roles".
- Add rows: Replay-gjennomgang «Vis som tabell» (Uke, Klassespill netto lager, Replay netto lager, kost); Delt skjerm Netto lager → the Debrief Rolle × Uke table; Oversikt median → the «Median, Fabrikk» and «Kjedekost/uke, snitt» wall rows in the table view; Alle spill side om side / landing → the same table offer as the Matrisevegg.
- Add a catch-all: "A chart not in this table is a spec error."

**R2-M6 [rubric N-S1]** — Lærers testspill and the Faglærer side of Alle spill i plenum have no states (§ EXP IA L123; L609; FR-86, FR-87)

Lærers testspill (FR-87) appears only inside a bundled IA row. There is no state, no flow and no statement of which screen it reuses: presumably the Student Spill with three KI-spillere and chosen Spillinnstillinger, labelled «Testspill» rather than Demodata. Nothing says how it starts or ends, or that it never reaches reports. Alle spill i plenum (FR-86, Faglærer side) has no state for before the Spillfrist or with games unfinished.

Fix: Give Lærers testspill its own IA row with "reuses Spill; label «Testspill»; never in reports" and Not started / In progress / Finished rows. Add a «Spillfristen er ikke passert» row for plenum.

**R2-M7 [rubric N-V1]** — The Mockup deviations table claims to list every deviation, but misses the accessibility fixes; two would ship failing contrast (§ DESIGN L429; `05`, `06`, `07`, `08` SVG source)

Checked against the SVG source:
- `07` step 2: «Kundenes etterspørsel: 8» is drawn in `lager` (#2B6CA3); the spine says `ink` 600. `lager` on `lager-fill` is 4.07:1, a fail.
- `08`: the «Melding» links in the near-Takeover row are `lager` at 10 px; the spine says `ink` underlined. `lager` on `restordre-fill` is 4.01:1, a fail.
- `08`: the wall has no signed legend, no «−» glyphs, no «Oppdater automatisk» switch and no plenum caption.
- `05` / `06`: no Ordrefelt help line; in `06` A the empty «Bekreft ordre» is drawn enabled, where the spine requires the disabled state.
- `07`: the Ukeskrubber has no − / + step buttons, and its track is in `axis`.
- No sheet has the week-table scrollbar or «Sveip for tidligere uker».
- The Demodata header note lives in EXP L613 instead of the table.

Fix: Add the rows, or one blanket row: "Round-1 accessibility fixes (focus ring, Ordrefelt help and disabled state, Matrisevegg legend, glyphs and switch, text on tints, Ukeskrubber step buttons, scroll affordance) are undrawn; the spine wins". Move the Demodata note into the table.

**R2-M8 [rubric N-I2]** — Both spines are final, but neither points to the 46 open findings in issue #26 (§ DESIGN, EXP Open Questions)

Open items include two primary buttons on Klasseøkt (M5), fixture values that read as rules (M12), undefined P1–P8 and stance codes (M15) and the Debrief auto-advance (M17). A story author building from the spine alone cannot see them.

Fix: Add one Open Question: «Known open validation findings: issue #26 (see `validation-report.md`)».

**R2-M9 [a11y N-M1]** — The shared disabled state erases the chosen option on locked settings (§ DESIGN Interaction states, Disabled row; EXP Valgknapper, Bryter, Klasseøkt «After Start date», Innsatsnivå)

WCAG 1.3.1, 4.1.2. The filled column of the Disabled row (active segment, `switch` on) is "`future-tint` fill, 1 px `axis` border, `ink-muted` label", the same as the outlined column. After the Start date a Faglærer opens the Klasseøkt to check whether «Gruppedebrief» or «LLM-spillere» was chosen. Every segment renders identically and the switch "on" looks like "off". The chosen value exists only for assistive technology; sighted users, including Assistenter checking settings, cannot see it.

Fix: Add a «Låst» (read-only) state distinct from Disabled: the active segment keeps the `ink` 1.4 px border and `ink` label on `future-tint` plus a text mark («valgt»); inactive segments use an `ink-muted` label; the switch shows its state word; a line under the group reads «Låst fra startdatoen.»

**R2-M10 [a11y N-M2]** — Controls that disable or remove themselves while focused drop keyboard focus (§ EXP Ordrefelt − / +; Spill → Submitting; Sett inn KI-spiller; Pausevalg; DESIGN Interaction states) — partly already in #26 (M18)

WCAG 2.4.3, 2.4.7, 2.1.1. A keyboard Student presses «Én færre» down to 0; the segment becomes natively disabled and focus is lost, so the next Tab starts from the top of the page. The same happens when «Sett inn KI-spiller for Jonas» is replaced by the KI-spiller row, and when «Ta pause» swaps into the in-place form. DESIGN gives `aria-disabled` only to "disabled controls that explain themselves". The in-place panel focus is M18 in #26; the − / + and Submitting cases are new.

Fix: A control that becomes unavailable while focused uses `aria-disabled` and keeps focus. A control that is removed moves focus to its replacement: the Setestatus row text with `tabindex="-1"`, or the first field of the opened form, and back to «Ta pause» on «Avbryt».

**R2-M11 [a11y N-M4]** — The Do's and Don'ts tint rule contradicts the Text on tints table (§ DESIGN Do's and Don'ts; Colors → Text on tints; Disabled state)

WCAG 1.4.3. The Do «Keep text on tints to `ink` or `ink-secondary`» allows `ink-secondary` on every tint, but on `net-*-1` / `flow-1` it is 3.37–3.53 and on `net-*-2` / `flow-2` 2.27–2.46, both failing. A developer who uses the quick-reference table for a secondary label in a matrix or Netto lager cell ships failing text. In the other direction, the Don't forbids `ink-muted` "on any fill", while the Disabled state, the read-only Ordrefelt and the Text on tints table all put `ink-muted` on `future-tint` (4.71, allowed). The two tables cannot both be followed.

Fix: Do: «Keep text on tints to the pairs in Colors → Text on tints: `ink` or `ink-secondary` on `lager-fill` / `restordre-fill`, `ink` only on steps 1–2, `paper` on steps 3–4». Don't: «`lager`, `restordre` or `ink-muted` text on `lager-fill`, `restordre-fill`, `hairline` or a matrix step».

### Low (23)

**R2-L1 [rubric N-F4]** — Three journey steps name actions that have no control or state (§ EXP UJ-8 L721–722; UJ-9 L734)

UJ-8 step 3 turns on the Veiledende bokstav (FR-56); UJ-8 step 4 says "the AI section is left out unless Sara adds it"; UJ-9 step 4 creates next year's Klasseøkt from this one (FR-66). No IA row says where «Ny Klasseøkt fra denne» lives.

Fix: One Component Patterns or State Patterns line each: a Bryter in KI-vurdering, a Bryter in the report download, a Lenke on Klasseøkt.

**R2-L2 [rubric N-T1]** — The error border width disagrees with itself (§ DESIGN L197, L213, L587)

`text-field.border-error` is `1px {colors.restordre}`, while the Interaction states table gives every outlined control a «1.4 px `restordre` border plus reason text», and `order-input` uses 1.4 px.

Fix: Set `text-field.border-error` to 1.4 px, or except text fields in the table.

**R2-L3 [rubric N-T2]** — Text buttons have no state column (§ DESIGN L580–587, L599, L663, L673)

The Interaction states table covers Filled, Outlined and `link`. Flagg «Marker som feil» / «Angre», the Veggfiltre text buttons and the borderless Totalkostnad button are text buttons whose hover, pressed and disabled looks are left to inference.

Fix: Add "text buttons follow `link`, in `ink`", or a fourth column.

**R2-L4 [rubric N-T3 · a11y N-L2]** — «12 columns at 360 px» does not follow from the column rule (§ DESIGN L547–548; EXP L137 Responsive, FR-23)

A column is the larger of 1.6 em and the widest number plus 0.25 em. In tabular Source Sans 3, «−13» makes a column about 1.75 em (22.8 px), so (360 − 32 − 76) / 22.8 ≈ 11 columns at 360 px and about 9 at 320 px, not 12 and 10. A three-digit Posisjon has the same effect. Nothing breaks, because the region scrolls and keeps nå in view, so there is no WCAG failure. But «12 columns at 360 px and 100 % text» is the basis of the FR-23 claim, of PRODUCT's «all Seat data … visible on a 360 px wide screen without horizontal scroll», and of the Spillkort window (R2-M3), so the product commitment is wrong as written.

Fix: Say "up to 12": "12 columns when every number is two characters or fewer; otherwise the earliest past Uke scrolls out", and state the expected count with «−13» in the window. Alternatively, lower `week-col-min` to fit 1.75 em.

**R2-L5 [rubric N-C5]** — «Sist Uke bestilte du 8.» has no defined position (§ EXP L203; DESIGN Ordrefelt L619–624; `06` A)

It is part of the Ordrefelt Empty state but has no place in DESIGN Ordrefelt. `06` A draws it as a caption under the field, exactly where the spine now puts the always-shown help line «Hele tall fra 0 til {maks}.».

Fix: State the order of the two lines, or drop one.

**R2-L6 [rubric N-C6]** — Pausevalg's placement collides with two rules (§ EXP L217, L227, L237) — extends #26 (M5)

The trigger sits under Setestatus, which shows on Spill only after confirming, so a Student who has not ordered can pause only from Hjem. On Hjem, the open form's primary «Ta pause til to. 19:00» sits beside Spillkort's primary «Gå til Uke 11», against "one primary button per screen".

Fix: Say where «Ta pause» sits before ordering, and demote one of the two buttons while the form is open.

**R2-L7 [rubric N-S2]** — Smaller missing states (§ EXP L363, L441)

The Studentrapport download before the Testfrist (available only after the deadline, yet Mine data puts «Last ned Studentrapport» at the top); «Legg til Faglærer» with an e-mail that has no account; Mine data when a category is empty.

Fix: One row each.

**R2-L8 [rubric N-S3]** — Oppdater automatisk «Off» does not say whether the Varselbånd freezes (§ EXP L321, L323; UJ-7 climax)

«Off» says "the wall, the table, the rail and the headline counts stop changing". The Varselbånd is the near-Takeover warning the Faglærer is there to act on. The «Announced» row implies it keeps updating, but the Off rule does not say.

Fix: State that the Varselbånd always stays live and is announced even when updates are off.

**R2-L9 [rubric N-V2]** — The Kjedebånd itself is silent on a Posisjon label (§ DESIGN L440, L600–609; EXP L177, L536; `10`)

The deviation row says the «Posisjon 24 / 3 / 42 / 37» labels in `10` "no longer conflict". In `10` they sit in a left annotation column, but the Kjedebånd anatomy, behaviour row and screen-reader text have no Posisjon label. A builder could read the row as licence to add one.

Fix: Add "the Kjedebånd carries no Posisjon label; Posisjon lives in the graph and the table".

**R2-L10 [rubric N-V3]** — Debrief content in `07` still asks the Student to compute a Posisjon the table now prints (§ EXP UJ-5 step 6 L682; L590; OQ8 L745)

The quiz item «Uke 11: lager 0, restordre 13, 16 på vei. Hva er posisjonen før du bestiller?» and step 4's «Dette regnet du» ask about a number the Student's own table printed every Uke. Not a contradiction, but OQ8 tracks only the oscillation risk.

Fix: Add to OQ8 that this quiz item and «Dette regnet du» need a re-check if Posisjon stays visible.

**R2-L11 [rubric N-B1]** — The cost-picture and Posisjon duplication got worse (§ DESIGN L527, L611, L625, L629; EXP L60, L180, L181, L191, L503, L551, L567) — already in #26 (M11)

The cost-table alternative («Sum, kr» on phone, «Vis som tabell» on laptop) is stated in six places, and Posisjon's definition in six. They agree today but will drift. Re-reported because it got worse.

Fix: As M11, plus keep each formula in the Terms table and point to it.

**R2-L12 [rubric N-B2]** — DESIGN now carries behaviour and copy that EXPERIENCE also owns (§ DESIGN L622, L644, L671, L675)

Pausevalg «Choosing it opens, in place, a date and time field …»; Oppdater automatisk's Off line and «Oppdater»; the Ordrefelt error copy; the Meldingsskjema button rules.

Fix: Keep anatomy and tokens in DESIGN, and point to EXP for copy and triggers.

**R2-L13 [rubric N-I3]** — The Terms table's own rules are not followed (§ EXP L54, L124, L238, L545, L600)

It says spine prose keeps «Class game», but prose uses «Klassespill» throughout (19 lines; «Class game» appears 4 times). «Setene» is given as the plural of Sete but is the definite plural; the copy uses «seter». «KI-kostnad» (IA L124, FR-69) is missing.

Fix: Change the rule to "prose uses the UI string except Seat, Takeover and Reclaim", correct the plural, and add KI-kostnad.

**R2-L14 [a11y N-L1]** — Focus is specified on cells the behaviour spine makes unfocusable (§ DESIGN Fokusring; EXP Graf over tabell, Matrisevegg)

WCAG 2.4.7. DESIGN puts the outer ring on "the Din ordre cell" and the inset frame on "matrix cells that take focus". EXP says "Table cells are not focusable", and the Matrisevegg focuses rows by game ID, not cells. Implementers will be confused.

Fix: Remove "the Din ordre cell" and "matrix cells" from the Fokusring bullet, or state which wall cells are focusable and why.

**R2-L15 [a11y N-L3]** — «Sveip for tidligere uker» names a touch gesture only (§ DESIGN Graf over tabell at narrow widths)

WCAG 3.3.2, 1.3.3 in spirit. At 320 px from 400 % laptop zoom, or with a keyboard, there is nothing to swipe.

Fix: «Rull sidelengs for tidligere uker», or put the arrow-key hint in the region's accessible description.

**R2-L16 [a11y N-L4]** — Posisjon and Netto lager labels have no collision rule, and the lines have equal luminance (§ DESIGN Graf over tabell)

Both direct labels («Restordre 13», «Posisjon 3») sit at the nå x-position; when På vei is small they overlap. `ink-secondary` vs `lager` / `restordre` is 1.32 / 1.33, so where the lines coincide only the 4 px squares separate them.

Fix: Nudge the labels vertically apart with a leader, and draw Posisjon on top of Netto lager.

**R2-L17 [a11y N-L5]** — The focusable, pressable disabled «Bekreft ordre» has a 1.61:1 boundary (§ DESIGN Interaction states, Disabled)

The 1.4.11 inactive-component exemption is shaky for a control that is focusable and shows an error when pressed. Its `ink-muted` label (4.71) still identifies it.

Fix: For the "disabled but explains itself" case use the `ink-muted` border (5.16), and keep `axis` for truly inert controls.

**R2-L18 [a11y N-L6]** — Text-only zoom turns matrix-wall numbers into glyphs (§ DESIGN Matrisevegg) — already in #26 (M25)

WCAG 1.4.4. A cell prints its number only "when the number fits". With 200 % text and cells sized in px, numbers become «−» or blank. The 13 px table view rescues it as an alternate version.

Fix: Size wall cells in `em`.

**R2-L19 [a11y N-L7]** — Gaps in the reflow two-group list and the label-column cap (§ DESIGN Layout & Spacing, two-group table, 40 % label cap) — related to #26 (M20)

WCAG 1.4.10, 1.4.4. Student components missing from both columns: Kjedens regning, Kjedens kostnad over tid, Etterspørselsbånd with its table, the Debrief step 1 strip, Ukeskrubber, Delt skjerm. At 320 px with 200 % text the 40 % label cap is about 115 px, and single-word labels such as «Restordre» (about 112 px at 26 px) cannot "wrap to two lines" without hyphenation.

Fix: Complete the list, and require `hyphens: auto` under `lang="nb"` for row labels (`lang` itself is #26 L14).

**R2-L20 [a11y N-L8]** — The Graf over tabell graph is not marked `aria-hidden` (§ EXP Accessibility Floor → Charts)

WCAG 1.3.1. "A chart whose alternative is a visible table on the same columns needs nothing more". An exposed SVG leaks tick labels, «Nå», «Posisjon 3» and «Restordre 13» to screen readers as orphan text before the table.

Fix: "Every chart is `aria-hidden`; the visible table or the named alternative is the accessible version".

**R2-L21 [a11y N-L9]** — The near-Takeover wall row is marked by tint alone inside the wall, and what gets tinted is ambiguous (§ DESIGN Matrisevegg; EXP Varselbånd)

The Varselbånd names the game in text, so 1.4.1 is met overall. Inside the wall, though, the urgent row differs only by `restordre-fill`, and the spine does not say whether the tint replaces the row's matrix-step cells (data loss) or only the label area.

Fix: Tint only the label cells, and add a short text marker («KI om 1 t») in the row.

**R2-L22 [a11y N-L10]** — The Pausevalg date and time field has no validation (§ EXP Pausevalg)

WCAG 3.3.1, 3.3.3. It allows "from now to the Spillfrist" but gives no error for a past time or one after the Spillfrist, and no label for the time part.

Fix: «Velg et tidspunkt mellom nå og Spillfristen, {dato}.» using the Ordrefelt error pattern.

**R2-L23 [a11y N-L11]** — Interaktiv oppgave point sliders are underspecified (§ EXP Interaktiv oppgave)

Unanswered Uker show "no point", so there is no slider to Tab to and the keyboard path is the table, which the spine should say. `aria-valuemin` / `aria-valuemax` are not given. 8 px points with 36 Uker at 320 px cannot meet the product's own "tap targets at least 44 px … for every control".

Fix: "An unanswered Uke's slider starts empty (`aria-valuetext` «Uke 3: ikke besvart») and Up sets 0"; give min and max; exempt chart points from the 44 px rule, with column tap and the table as the alternative.

## Deferred findings in #26 that are now closed

The rubric walker found these deferred round-1 findings closed in passing by the fix pass. They can be trimmed from [issue #26](https://github.com/IBE160-2026/beergame/issues/26).

| ID | Status | What changed / what remains |
|---|---|---|
| M4 | closed | Norwegian chart names in DESIGN, token keys in parentheses. |
| M7 | closed | Skjelett loading and AI-pending states. |
| M8 | closed | Permission denied and Session expired rows. |
| M13 | closed | «Assistent» naming. |
| L7 | closed | Drawing item listed in OQ5. |
| L10 | closed | Build checks restated as product tests. |
| L20 | closed | Demand label in `ink`. |
| L21 | closed | Totalkostnad is a named button. |
| M16 | partly closed | The announcement list grew; focus after the Uke advance is still undefined. R2-H4 extends it. |
| M18 | partly closed | Meldingsskjema is its own page and Back works; in-place panel focus remains (see R2-M10). |
| M21 | partly closed | Filters and Flagg use `aria-pressed`; `quiz-option` still has no selected state. |
| L13 | partly closed | Status is final; EXPERIENCE frontmatter still has no `name`. |
| L18 | partly closed | Session expiry is specified; no warning before your own Takeover (see R2-H2). |

## Reviewer files

- `review-rubric-2.md` — rubric walker, round 2 (filed 1 high, 9 medium, 14 low)
- `review-accessibility-2.md` — adversarial accessibility reviewer, round 2 (filed 0 critical, 3 high, 4 medium, 10 low, plus N-L6 re-reporting #26 M25)
- `validation-report.md` / `validation-report.html` — round 1, annotated with status per finding
