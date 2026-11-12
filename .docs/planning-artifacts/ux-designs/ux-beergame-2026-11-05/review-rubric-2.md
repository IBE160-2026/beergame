# Spine Pair Review, round 2 — beergame (ØL-spillet)

- **DESIGN.md:** 706 lines, `status: final`
- **EXPERIENCE.md:** 745 lines, `status: final`
- **Run at:** 2026-11-10
- **Baseline:** `validation-report.md` (round 1: C1, C2, H1–H15, M1–M25, L1–L21). M1–M25 and L1–L21 are deferred to issue #26 and are not re-reported unless they got worse.
- **Line numbers** below refer to the files as they stand now (DESIGN = `DESIGN.md`, EXP = `EXPERIENCE.md`).

## Overall verdict

The fix pass did its job. All 17 round-1 critical and high findings are closed, and every fix lives in a named place in the spines rather than in a promise. The week table now has a real narrow-width and 200 % text contract. The drawing item has a value table and keyboard sliders. The Ordrefelt has its full error, submit, timeout and offline story. The focus ring and the interaction states are tokenised. The Terms table maps the PRD nouns to UI strings. Posisjon is shown consistently as a line and a row in both the Klassespill and the Replay, and no text anywhere still describes it as hidden. All 41 component names are identical across both files, in the same seven groups and the same order. Every `{token}` reference resolves (62 distinct paths, plus one illustrative `{colors.…}`), and every stated contrast ratio recomputes.

The remaining risk sits in three places:

- **Faglærer intervention.** In-scope Faglærer actions inside FRs the spine cites still have no control: manual Takeover (FR-37), starting games (FR-22), the «in the room» shorter limit (FR-36) and the completion corrections (FR-17). The new «Pause spillet» has a button but no behaviour.
- **The Mockup deviations table** says it lists every deviation. It no longer does: the accessibility fixes in this pass contradict `05`, `06`, `07` and `08` in ways the table does not mention. Two of them would ship failing text contrast if someone measured from the sheet.
- **A few ambiguities the fix pass introduced:**
  - Sett inn KI-spiller is limited to "during a Pause", but ordering ends the Pause.
  - Spillkort is on the must-reflow list, but it holds a 12-column table.
  - The Interaktiv oppgave cells take negative numbers, but they reuse a keypad pattern that has no minus key.

Architecture can start now. Story development can start for every Student surface and for Faglærer setup. Faglærer live intervention, Lærers testspill and the plausibility question need one more short pass.

New findings in this round: 1 high, 9 medium, 14 low. One of the low findings re-reports a deferred finding that got worse (M11).

## Closure check (round 1 critical + high)

| ID | Round-1 finding | Verdict | Evidence / what is missing |
|---|---|---|---|
| C1 | Week table cannot hold 13 px at 320 px or 200 % text | **closed** | Tokens `reflow-min`, `design-min`, `week-col-min` (DESIGN L159–161) and `week-table.column-min-width/sticky-label-background/scrollbar` (L259–261). The «Graf over tabell at narrow widths and large text» rules (DESIGN L544–550) cover one scroll region, sticky labels, a column minimum, column counts, a visible scrollbar, an HTML `<table>`, and product tests at 320 and 360 px, each at 100 % and 200 % text. «Text never shrinks to fit» (L523) bans the `vlib.gtable` shrink. EXP L193–194 adds the scroll-to-nå rule, `role="region"` and `th scope`; EXP L541 holds the reflow floor. Residue: N-T3 (the column count). |
| C2 | Drawing item has no keyboard or non-drawing path | **closed** | DESIGN `interactive-item` (L385–391, L662). EXP «Interaktiv oppgave» subsection (L278–288) gives a value table backing every drawing, slider points, «the table alone answers», and scoring from the table. Also EXP L540 («No task needs a drag or a drawn path»), EXP L517 and UJ-6 step 4 (L695). Residue: N-C4 (minus sign on the numeric keypad). |
| H1 | In-scope FRs with no IA row, flow or state | **closed** | Every listed FR now has a row. FR-4: EXP L100, L358–360. FR-10: L115, L441. FR-21: L105, L372–374. FR-52: L118, L446. FR-59/60/88: L121, L449–450, UJ-8 step 5. FR-61: L120, L430, L448. FR-75: L101, L363. FR-78: L117, L445. FR-81: L119, L447. FR-82: L125, L472. The same class of gap remains for FRs that round 1 did not list (N-F1, N-F2). |
| H2 | No control for setting a Pause or putting in a KI-spiller | **closed** | DESIGN `pause-control`, `ai-insert` (L392–399, L644–645). EXP Pausevalg (L233–242) and Sett inn KI-spiller (L244–252) give trigger, eligibility, copy and who sees what. The states are at EXP L389–394, and UJ-4 step 9 and the failure path reference them (L667–669). Residue: N-F3 (the eligibility rule conflicts with ordering ending the Pause). |
| H3 | No focus ring; no hover, pressed or disabled states | **closed** | Tokens `focus-ring`, `focus-ring-inset` (DESIGN L163–172). Hover, pressed and disabled keys on every interactive component (L173–347). The Interaction states table and the Fokusring contrast on every background (L576–595). Also EXP Fokusring (L170) and Accessibility Floor (L530). Residue: N-T1, N-T2. |
| H4 | About ten used components have no row | **closed** | All ten now have a DESIGN row and an EXP row under the same name: Spillkort, Topplinje, Filopplasting, Veggfiltre, Meldingsskjema, Interaktiv oppgave, Pausevalg, Sett inn KI-spiller, Flagg, Etterspørselsbånd, Kjedens kostnad over tid. Residue: N-C3 (charts that still have no row). |
| H5 | Ordrefelt empty, invalid, Enter and failed submit unspecified | **closed** | DESIGN `order-input` error, help and disabled keys (L210–224) and the Ordrefelt states (L619–624). EXP Ordrefelt subsection (L197–211): range with 0 valid, `type="text" inputmode="numeric"`, help line with `aria-describedby`, inert button, error timing with `role="alert"`, Enter moves focus, − / + named. Also EXP Submitting / Submit failed / Timed out / Offline (L383–387) and the Individuell test review before submit (L424). |
| H6 | No global offline pattern; no stale indicator on the Oversikt | **closed** | DESIGN `connection-notice` (L414–418, L684). EXP Tilkoblingslinje (L329), the All surfaces rows Offline / Reconnected / Page error (L343–345) and Oversikt «Connection lost or stale» (L457). |
| H7 | Whole surfaces have no State Patterns rows | **closed** | Logg inn: L356–360. Startoppgave: L375–378. Replay and Replay-gjennomgang: L410–414. Individuell test: L421–427. Alle spill side om side: L415. Spillinnsikt, Studentside, Klasserapport, Tverrklasse-statistikk: L460–463. Admin: L469–472. Global rows: L342–349. Residue: N-S1, N-S2. |
| H8 | «Posisjon» drawn in the Class-game band in `10` | **closed** (by founder decision) | Posisjon is now shown in both rounds (memlog 2026-11-09). The Mockup deviations row (DESIGN L440) supersedes the old `05` / `09` / `10` captions and settles the `10` labels. Residue: N-V2 (the band itself is still silent on a Posisjon label). |
| H9 | No PRD-to-UI glossary | **closed** | Terms table in EXP Foundation (L38–87) covers PRD term → UI string → note, including Netto lager, Posisjon, Kjedekost and Kost per uke. Residue: N-I3. |
| H10 | Matrisevegg sign by hue alone; no legend | **closed** | DESIGN Matrisevegg cells print a number or a «−» glyph, with an always-visible signed legend and a «Vis i plenum» caption (L667–670, tokens L288–297). The false Colors claim is corrected (L478). EXP Accessibility Floor (L522). |
| H11 | Charts without a text or table alternative | **closed** | EXP chart alternatives table (L497–519) covers every chart round 1 named. «Sum, kr» is restored (DESIGN L625, EXP L180). The `cost-distribution` text summary is at L512, and the Spillkort mini graph is `aria-hidden` (L230, L516). Residue: N-C3 (three charts still unlisted). |
| H12 | Signal or muted text on fill tints fails 4.5:1 | **closed** | DESIGN «Text on tints» table (L480–490); all ratios recompute. Links on tints use `ink` via `link.on-tint-foreground` (L209, L492). `demand-band.label` is `ink` (L404–407, L655). Varselbånd text rule (L674). |
| H13 | Reflow specified at 360 px, not 320 px | **closed** | `reflow-min` 320 / `design-min` 360 (DESIGN L160–161, L529). The two-column reflow vs two-dimensional exception table (L531–533). The Kjedebånd scale is derived from the width, with tests at 320 and 360 (L607–609). Also EXP L137, L139, L541. Residue: N-C2 (Spillkort is misclassified) and N-I1 (Faglærer surfaces). |
| H14 | Live Oversikt re-sorts under the screen reader | **closed** | DESIGN Oppdater automatisk (L671). EXP Oppdater automatisk subsection (L316–323): on by default, frozen re-sort while focus is inside, focus kept by game ID, throttled polite announcements. Matrisevegg «Updates» row (L314). Residue: N-S3. |
| H15 | Ukeskrubber keyboard is only an assumption | **closed** | EXP Ukeskrubber subsection (L267–276): `role="slider"` with values, keys, step buttons, and a 300 ms polite chain readout. The Delt skjerm rule is an [ASSUMPTION]. DESIGN track in `ink-muted` with step buttons at `tap-target-min` (L283–287, L657). |

**Tally:** 17 closed, 0 partly closed, 0 open, 0 regressed.

**Deferred items closed in passing (worth trimming from #26):**
- Fully closed: M4 (Norwegian chart names in DESIGN), M7 (Skjelett and AI pending), M8 (permission denied, session expired), M13 (Assistent), L7 (drawing item in OQ5), L10 (build checks restated as product tests), L20 (demand label `ink`), L21 (Totalkostnad is a named button).
- Partly closed:
  - M16: the announcement list grew, but focus after the advance is still undefined.
  - M18: Meldingsskjema is its own page and Back works.
  - M21: filters and Flagg use `aria-pressed`, but `quiz-option` still has no selected state.
  - L13: status is final, but EXPERIENCE still has no `name`.
  - L18: session expiry is specified, but there is no warning before your own Takeover.

## 1. Flow coverage — adequate

UJ-1 to UJ-9 match the PRD headings verbatim (EXP L617–734). Each flow has a named protagonist (Kari, Bård, Sara), numbered steps and a bold **Climax**. Failure or edge paths are present for UJ-1, 2, 4, 5, 6 and 8. UJ-3 has an edge but no failure path, and UJ-9 has neither; both are L1 in #26. UJ-7 says "Failure: none needed". I cross-checked FR-1 to FR-89 against every FR the spines cite, directly or by range. These are not cited: FR-29–33, FR-35, FR-47, FR-67, FR-68, FR-70, FR-71, FR-76, FR-77. Of these, FR-70, FR-71 and FR-76 have a user-facing surface.

### Findings
- **high** (N-F1) In-scope Faglærer actions inside FRs the spine cites have no control, state or flow, so their stories have no UX contract:
  - **FR-37:** a Faglærer or Assistent triggers Takeover of any Seat at any time, and fills all absent Seats in one game, or in all games, in one action (the PRD's example is the start of a Labtime). The Varselbånd announces «KI overtar om 1 t» but offers only «Send Melding» and «Pause spillet» (EXP L298, DESIGN L674).
  - **FR-22:** the Faglærer starts any Class game or all at once. The Student's «presses start» is already M9 in #26. The scheduling aid is listed as spine-only in OQ5 (L742) but has no specification at all.
  - **FR-36:** marking a game «in the room» during a Labtime with a shorter Inactivity limit.
  - **FR-17:** correcting a Student's Completion status with a reason, a make-up solo game, per-Student adjustments of the limit and share, and «message those who have not met the requirement» in one action.

  *Fix:* add rows to Oversikt / Spillinnsikt / Studentside, for example a Faglærer variant of Sett inn KI-spiller («Sett inn KI-spiller i alle ledige seter»). Alternatively, list each one in OQ5 as "spine-only, no layout yet" with the surface that owns it.
- **medium** (N-F2) Three in-scope FRs with a UI have no surface:
  - FR-70, the optional five-point «how believable were the KI-spillere» question after the Replay and after any Class game with AI players. It is Student-facing.
  - FR-76, Admin deletion on request.
  - FR-71, the Admin's pseudonymised export.

  None is in the IA (L95–125), State Patterns or OQ5. *Fix:* add an IA row and one state row each, or list them as spine-only in OQ5.
- **medium** (N-F3) The Sett inn KI-spiller eligibility conflicts with how a Pause ends:
  - The row says it acts "during a Pause" (EXP L229).
  - Any Student ends the Pause by ordering (L241, L390; FR-89).
  - Setestatus, which hosts the button, appears on Spill only after the Student has confirmed an order (L227).

  So in UJ-4's failure path (L669), Sara's own order has ended the Pause before she can see «Sett inn KI-spiller for Jonas». The «Shown» rule (L248) does not require a running Pause, so the two rows disagree. Nothing says whether the right survives the end of the Pause, or how it interacts with the automatic Takeover clock. This was introduced by the H2 fix. *Fix:* drop "during a Pause". State that once the agreed time (or the Inactivity limit) has passed, the right lasts until the absent Seat orders or automatic Takeover happens, whether or not the Pause has ended.
- **low** (N-F4) Three journey steps name actions that have no control or state:
  - UJ-8 step 3, turning on the Veiledende bokstav (FR-56) (EXP L721).
  - UJ-8 step 4, "the AI section is left out unless Sara adds it" (L722).
  - UJ-9 step 4, creating next year's Klasseøkt from this one (FR-66) (L734). No IA row says where «Ny Klasseøkt fra denne» lives.

  *Fix:* one Component Patterns or State Patterns line each (a Bryter in KI-vurdering, a Bryter in the report download, a Lenke on Klasseøkt).

## 2. Token completeness — adequate

The frontmatter has 27 colours (all hex), 19 typography roles, 4 radii, 16 spacing tokens and 44 component objects. There are 232 `{…}` references in DESIGN (55 distinct) and 9 in EXP (8 distinct, one illustrative `{colors.…}`), and none is unresolved. `{maks}` and `{n}` are copy placeholders, not token paths.

I recomputed every stated contrast ratio and all of them match:
- the Colors table and the Text on tints table
- the focus ring on `paper`, `future-tint`, `hairline` and both fills
- the inset ring at ≥ 4.51 / ≥ 5.14
- the Posisjon line at 7.3 / 6.7 / ≥ 5.3

Contrast is now stated for every pair the design depends on. The open non-text cases (`axis` zero line, `step-list` later-dot, `bar-base`) are M2 in #26, and composite values are M3.

### Findings
- **low** (N-T1) The error border width disagrees with itself:
  - `text-field.border-error` is `1px {colors.restordre}` (DESIGN L197).
  - The Interaction states table gives every outlined control a «1.4 px `restordre` border plus reason text» (L587).
  - `order-input` uses 1.4 px (L213).

  *Fix:* set `text-field.border-error` to 1.4 px, or except text fields in the table.
- **low** (N-T2) Text buttons have no state column. The Interaction states table covers Filled, Outlined and `link` (L580–587). Flagg «Marker som feil» / «Angre» (L663), the Veggfiltre text buttons (L673) and the borderless Totalkostnad button (L599) are text buttons whose hover, pressed and disabled looks are left to inference. *Fix:* add "text buttons follow `link`, in `ink`" or a fourth column.
- **low** (N-T3) «12 at 360 px» (DESIGN L548) contradicts the column rule one line above it (L547). A column is the larger of 1.6 em and the widest number plus 0.25 em. In tabular Source Sans 3, «−13» is about 1.75 em, so any window holding a two-digit negative Netto lager, or a three-digit Posisjon, gives 11 or fewer columns at 360 px. Nothing breaks, because the region scrolls. But «12 columns at 360 px and 100 % text» is also the basis of the FR-23 claim (EXP L137) and of the Spillkort window (N-C2). *Fix:* say "up to 12", and state the expected count with «−13» in the window.

## 3. Component coverage — adequate

DESIGN Components and EXP Component Patterns both list 41 components under identical Norwegian names. They use the same seven groups (Interaction states, Game screen, Controls, Seats and status, Game end and Debrief, Faglærer, System) in the same order. Every DESIGN row carries its token key in parentheses, so M4 is closed. Each long-rule component has its own EXP subsection: Graf over tabell, Ordrefelt, Pausevalg, Sett inn KI-spiller, Ukeskrubber, Interaktiv oppgave, Matrisevegg and Oppdater automatisk.

### Findings
- **medium** (N-C1) «Pause spillet» (the Faglærer pause, issue #25) is a button with no behaviour. The Varselbånd row (EXP L298) and DESIGN L674 place it, and OQ5 lists it as undrawn. Nothing states:
  - whether it opens the Pausevalg form (with or without an agreed time)
  - whether a Student's order ends it, as with FR-89
  - whether it stops the «KI overtar om 1 t» countdown in the band
  - whether it is audit-logged

  The Student-facing copy for it is M9 in #26; the Faglærer-side behaviour is not. *Fix:* add a row under Faglærer, or a «Faglærer» column in the Pausevalg subsection.
- **medium** (N-C2) Spillkort is on the "must reflow to 320 px, no horizontal scroll" list (DESIGN L533). It holds "a mini `net-graph` over a `week-table` … in the same 12-column window" (L646). At the 13 px floor and 1.6 em columns, 12 columns need about 250 px plus the 76 px label column. That does not fit inside a bordered card at 320 px, and fits at 360 px only with zero padding (see also N-T3). The table is real text; only the graph is `aria-hidden` (EXP L230). *Fix:* give the card its own window (for example nå − 3 … nå + 4) or move Spillkort to the two-dimensional list.
- **medium** (N-C4) The Interaktiv oppgave cells take "whole numbers, with a leading minus where the quantity can be negative, and use the Ordrefelt error pattern" (EXP L287). The Ordrefelt pattern is `inputmode="numeric" pattern="[0-9]*"` (L202). Phone numeric keypads, iOS in particular, have no minus key, and the pattern rejects «−». A phone Student cannot type a negative stock in a deadline-bound test item. This was introduced by the C2 fix. *Fix:* for signed cells use `inputmode="text"` (or `decimal` plus a ± segment) and the pattern `-?[0-9]+`, accept both U+2212 and U+002D, and say so in the Interaktiv oppgave subsection.
- **low** (N-C3) Some charts have no component row and are missing from the alternatives table, although that table says it lists every chart (EXP L497):
  - the Debrief step 1 strip «Ditt netto lager, hele spillet» (it has an alternative at L508, but no component row)
  - Delt skjerm «Netto lager per Role» and its chain view (L592)
  - «Snitt per ferdig spill, per Rolle» (L510, L570)
  - the Oversikt class median graph (DESIGN L541)
  - Klasseøkt «Kjeden ved start» (UJ-3 step 2)
  - the Replay-gjennomgang «Klassespill and Replay on one axis» chart (L684)

  *Fix:* state the reuse in one line each (for example "Kjeden ved start = Kjedebånd, four Roles"), and add the Replay-gjennomgang and Delt skjerm Netto lager charts to the alternatives table.
- **low** (N-C5) «Sist Uke bestilte du 8.» has no defined position. It is part of the Ordrefelt Empty state (EXP L203) but has no place in DESIGN Ordrefelt (L619–624). `06` A draws it as a caption under the field, which is exactly where the spine now puts the always-shown help line «Hele tall fra 0 til {maks}.». *Fix:* state the order of the two lines, or drop one.
- **low** (N-C6) Pausevalg's placement collides with two rules:
  - Its trigger sits under Setestatus (EXP L237), and Setestatus shows on Spill only after confirming (L227). A Student who has not ordered can pause only from Hjem.
  - On Hjem, the open form's primary «Ta pause til to. 19:00» sits beside Spillkort's primary «Gå til Uke 11», against "one primary button per screen" (L217).

  This extends M5 in #26. *Fix:* say where «Ta pause» sits before ordering, and demote one of the two buttons while the form is open.

## 4. State coverage — adequate

I walked all 31 IA rows (EXP L97–125) against State Patterns (L334–472).
- Global rows now exist for Loading, Offline, Reconnected, Page error, Action error, Permission denied, Session expired and Not found (L342–349).
- Focus rules are in the Accessibility Floor (L529–534).
- Spill alone has 21 states, including the full submit / failure / timeout / offline set and the Pause and Takeover rows.
- Every spine-only surface added by the H1 fix has at least one state.

The Hjem gaps (paused, Debrief open, test open) and «Class game not started» are M9 in #26.

### Findings
- **medium** (N-S1) Two Faglærer surfaces have no states at all:
  - **Lærers testspill (FR-87)** appears only inside a bundled IA row (L123). There is no state, no flow, and no statement of which screen it reuses: presumably the Student Spill with three KI-spillere and chosen Spillinnstillinger, with a «Testspill» label rather than Demodata (L609). Nothing says how it starts or ends, or that it never reaches reports.
  - **Alle spill i plenum** (FR-86, Faglærer side) has no state for before the Spillfrist or with games unfinished.

  *Fix:* give Lærers testspill its own IA row with "reuses Spill; label «Testspill»; never in reports" and Not started / In progress / Finished rows. Add a «Spillfristen er ikke passert» row for plenum.
- **low** (N-S2) Smaller missing states:
  - The Studentrapport download before the Testfrist. It is available only after the deadline, yet Mine data puts «Last ned Studentrapport» at the top (L363).
  - «Legg til Faglærer» with an e-mail that has no account (L441).
  - Mine data when a category is empty.

  *Fix:* one row each.
- **low** (N-S3) Oppdater automatisk «Off» says "the wall, the table, the rail and the headline counts stop changing" (L321). It does not say whether the Varselbånd, the near-Takeover warning the Faglærer is there to act on (UJ-7 climax), also freezes. The «Announced» row (L323) implies it keeps updating. *Fix:* state that the Varselbånd always stays live and is announced even when updates are off.

## 5. Visual reference coverage — adequate

`mockups/` holds 01–10 as `.png` and `.svg`; `imports/` is empty. All ten PNGs are cited in at least one spine, with panels named where it matters (`06` A–F, `05` left/middle, `04` left/right, `07` right, named `09` panels). The SVGs are still unmentioned (M10 in #26). The spines-win rule is stated once (DESIGN L429). EXP L28 points to it, and EXP L559 is a reminder rather than a second rule. The Posisjon supersession row (DESIGN L440) is correct, and I verified it against the SVG text of `05`, `09` and `10`.

### Findings
- **medium** (N-V1) The Mockup deviations table says «Every known deviation is listed here» (DESIGN L429), but the accessibility fixes from this pass contradict the mockups in ways it does not list. I checked each against the SVG source:
  - `07` step 2: «Kundenes etterspørsel: 8» is drawn in `lager` (#2B6CA3). The spine says `ink` 600 (L655). `lager` on `lager-fill` is 4.07:1, so it fails.
  - `08`: the «Melding» links in the near-Takeover row are drawn in `lager` at 10 px. The spine says `ink` underlined (L492, L667). `lager` on `restordre-fill` is 4.01:1.
  - `08`: the wall has no signed legend, no «−» glyphs, no «Oppdater automatisk» switch and no plenum caption (L667–671).
  - `05` / `06`: the Ordrefelt has no help line «Hele tall fra 0 til {maks}.». In `06` A the empty «Bekreft ordre» is drawn as an enabled secondary button (`paper`, `axis` border), where the spine requires the disabled state (L635; EXP L203).
  - `07`: the Ukeskrubber has no − / + step buttons, and its track is drawn in `axis`.
  - No sheet has the week-table scrollbar or «Sveip for tidligere uker» (L549).
  - The Demodata header note lives in EXP L613 instead of the table.

  A consumer measuring from `07` or `08` ships two contrast failures. *Fix:* add the rows, or one blanket row: "Round-1 accessibility fixes (focus ring, Ordrefelt help and disabled state, Matrisevegg legend, glyphs and switch, text on tints, Ukeskrubber step buttons, scroll affordance) are undrawn; the spine wins". Move the Demodata note into the table.
- **low** (N-V2) The deviation row says the «Posisjon 24 / 3 / 42 / 37» labels beside the Klassespill Kjedebånd in `10` "no longer conflict" (L440). In `10` they sit in a left annotation column with Lager / Restordre and På vei. But the Kjedebånd anatomy (DESIGN L600–609), its behaviour row (EXP L177) and its screen-reader text (L536) have no Posisjon label. A builder could read the row as licence to add one. *Fix:* add "the Kjedebånd carries no Posisjon label; Posisjon lives in the graph and the table".
- **low** (N-V3) The Debrief content in `07` was written when Posisjon had to be computed. The quiz item «Uke 11: lager 0, restordre 13, 16 på vei. Hva er posisjonen før du bestiller?» (UJ-5 step 6, L682) and step 4's «Dette regnet du» (L590) now ask about a number the Student's own table printed every Uke. This does not contradict the spine, but OQ8 (L745) tracks only the oscillation risk. *Fix:* add to OQ8 that this quiz item and «Dette regnet du» need a re-check if Posisjon stays visible.

## 6. Bloat and overspecification — adequate

Both files roughly doubled in size. Most of the growth is load-bearing for downstream consumers:
- the Terms table (L38–87)
- the per-section State Patterns
- the chart alternatives table
- the Text on tints table
- the eight subsections

The paired examples are 93–157 lines, but they describe far smaller products, so size alone is not a finding. Brand voice stays inside Brand & Style.

### Findings
- **low** (N-B1) The cost picture duplication got worse; this is already M11 in #26. The cost-table alternative («Sum, kr» on phone, «Vis som tabell» on laptop) is now stated in six places: DESIGN L625 and L629, EXP L180, L181, L503 and L567. Posisjon's definition is stated in six: EXP L60, L191, L551 and DESIGN L527, L611, L625. Today they agree, but they will drift. *Fix:* as M11, plus keep each formula in the Terms table and point to it.
- **low** (N-B2) DESIGN now carries behaviour and copy that EXPERIENCE also owns:
  - Pausevalg «Choosing it opens, in place, a date and time field …» (DESIGN L644)
  - Oppdater automatisk's Off line and «Oppdater» (L671)
  - the Ordrefelt error copy (L622)
  - the Meldingsskjema button rules (L675)

  *Fix:* keep anatomy and tokens in DESIGN, and point to EXP for copy and triggers.

## 7. Inheritance discipline — adequate

All 13 frontmatter `sources` resolve, and both files have identical lists. All nine UJ headings are verbatim. The Terms table maps the PRD §3 nouns. Component names are identical across both files. All 62 distinct token paths resolve. The founder overrides are handled consistently:
- «ØL-spillet» (EXP L34, Voice L158, OQ7)
- the Faglærer pause (L298, OQ7)
- Posisjon in both rounds (L191, L551, DESIGN L440, L611)
- light theme only (DESIGN L496)

No text anywhere still describes Posisjon as hidden. The only Replay-only element left is the projection, which is consistent across DESIGN L463 and L617, EXP L192 and L553, and UJ-5 step 7.

### Findings
- **medium** (N-I1) NFR-6 puts WCAG 2.1 AA on Student and Faglærer screens (EXP L496), but the reflow commitment covers only Student surfaces. DESIGN L529 says "every Student surface works there", and EXP L541 says "every Student flow". WCAG 1.4.10 also applies to Lag Klasse, Klasseøkt with its Datolinje, Spørsmål og vekter, the Oversikt right rail, Meldingsskjema and Admin at 1280 px × 400 %. *Fix:* extend the 320 px floor to every form and non-tabular Faglærer and Admin component, and add the Matrisevegg and Datolinje to the two-dimensional exception list.
- **medium** (N-I2) Both spines are `status: final`, but neither points to issue #26, where 46 known medium and low findings are open against them. These include two primary buttons on Klasseøkt (M5), fixture values that read as rules (M12), undefined P1–P8 and stance codes (M15) and the Debrief auto-advance (M17). A story author building from the spine alone cannot see them. *Fix:* add one Open Question: «Known open validation findings: issue #26 (see `validation-report.md`)».
- **low** (N-I3) The Terms table's own rules are not followed:
  - It says spine prose keeps «Class game», but prose uses «Klassespill» throughout (19 lines, for example EXP L238 and the L545 column header; «Class game» appears 4 times).
  - «Setene» is given as the plural of Sete (L54). It is the definite plural; the copy itself uses «seter» (L600).
  - «KI-kostnad» (IA L124, FR-69) is missing from the table.

  *Fix:* change the rule to "prose uses the UI string except Seat, Takeover and Reclaim", correct the plural, and add KI-kostnad.

## 8. Shape fit — strong

DESIGN runs in canonical order: Brand & Style (L442), Colors (L448), Typography (L498), Layout & Spacing (L525), Elevation & Depth (L554), Shapes (L563), Components (L572) and Do's and Don'ts (L689). The Mockup deviations table sits in the preamble, which suits a cross-cutting rule.

EXPERIENCE has all eight required sections: Foundation, Information Architecture, Voice and Tone, Component Patterns, State Patterns, Interaction Primitives, Accessibility Floor and Key Flows. It adds Responsive & Platform, which the multi-surface product needs. Every invented section is load-bearing:
- Hidden information and help level (FR-14, FR-23, FR-83, issue #22)
- Cost picture
- Chain direction convention (it supersedes addendum §B)
- Debrief sequence
- AI disclosure (FR-34, FR-55)
- Demo/synthetic data labelling (§6.2)
- Open Questions

Splitting Component Patterns and State Patterns into the DESIGN groups and per-section tables makes extraction cleaner than in round 1.

### Findings
- None new. Inspiration & Anti-patterns is still folded into Foundation (L89–91), which is L12 in #26. EXPERIENCE frontmatter still lacks `name` (L13 in #26, partly closed).

## Mechanical notes

- **Sources:** 13 of 13 resolve from WS, in identical lists in both files.
- **Frontmatter:**
  - DESIGN has `name: ØL-spillet` and `description`, with 27 colours, 19 typography roles, 4 radii, 16 spacing tokens and 44 component objects.
  - EXPERIENCE has no `name`.
  - Both files are `status: final`, updated 2026-11-09.
- **Token references:**
  - DESIGN has 232 references, 55 distinct. EXPERIENCE has 9, 8 distinct. None is unresolved.
  - `net-neg-3/4`, `net-pos-3/4` and `flow-3/4` are never referenced by path; they are reachable only through the prose hex table (L2 in #26).
  - `{maks}` and `{n}` are copy placeholders in the same brace syntax. A strict resolver should skip dot-less braces.
- **Contrast:** recomputed with the WCAG 2.x formula, all stated values match.
  - Closest passes: `ink` on `net-neg-2` at 4.51 (L16 in #26) and `order-history` on `paper` at 4.46, which is correctly listed as never text.
  - `lager` vs `restordre` is 1.01:1 and their fills 1.02:1, as stated.
- **Component names:** 41 of 41 are identical, in the same 7 groups and the same order in both files. No orphans on either side.
- **Cross-references:** every "see …" / "→" pointer in both files resolves to an existing section, row or bullet. That includes Layout & Spacing → Devices, Components → Interaction states → Fokusring, State Patterns → Student game → Paused / Pause ended / Paused before the agreed time, State Patterns → Account and access → Landing, and State Patterns → Faglærer setup → Lag Klasse. «(see Chain direction)» (EXP L177) abbreviates «Chain direction convention».
- **Posisjon:** consistent in all 21 mentions across both files. The formula, 0 − 13 + 16 = 3, «Med 24 ble den 27» and the projection 3 + 24 − 4 × 8 = −5 all check arithmetically. No text still describes it as hidden.
- **FRs never cited:** FR-29–33, 35, 47, 67, 68, 70, 71, 76, 77. Of these, FR-70, FR-71 and FR-76 have UI (N-F2); the rest are engine, log or retention.
- **Assumptions:** 8 `[ASSUMPTION]` in DESIGN and 42 in EXPERIENCE. 28 rows are marked spine-only.
- **Issues:** #22, #24, #25 and #26 are open. The spines cite #22, #24 and #25 but not #26 (N-I2).
- **Mockup checks:** I verified against SVG text and fills. `07` demand label is `#2B6CA3`. `08` «Melding» is `#2B6CA3` at 10 px. `06` A empty «Bekreft ordre» is drawn with a `paper` fill and a `#C3CDD8` border. `10` Posisjon labels sit in the left annotation column (x = 40). None of «Hele tall», «Oppdater automatisk», «Sveip», «35 og over» or «Rødt:» appears in any SVG.
