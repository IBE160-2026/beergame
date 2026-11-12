# Spine Pair Review — beergame (ØL-spillet)

## Overall verdict
The pair is a strong contract for the core Student loop: Spill, Graf over tabell, Kjedebånd, Kostnad så langt and the Debrief. Every `{token}` reference resolves, every colour has a hex value, and the hidden-information, chain-direction and AI-disclosure rules are written down. Outside that loop the contract gets thin. About a dozen in-scope FRs have no IA surface, and several flows and surfaces have no states. There are no global loading, offline, error or permission patterns, and the irreversible order confirm has no failure path. One mockup conflict touching the issue #22 decision is not acknowledged, and nothing maps the English PRD glossary to the Norwegian UI terms. Architecture can start from the game loop now. Story development for setup, test, report and admin surfaces needs one more pass.

## 1. Flow coverage — adequate
I extracted UJ-1 to UJ-9 from PRD §2.3 and checked each Key Flow (EXPERIENCE.md L296–412) for a named protagonist, numbered steps, a climax beat and a failure or edge path. I also cross-checked FR-1 to FR-89 against the FRs that EXPERIENCE.md cites, directly or as a range. All nine UJ headings match the PRD verbatim. Each flow has a protagonist (Kari, Bård, Sara), numbered steps and a bold **Climax**. Failure or edge paths are present for UJ-1, 2, 3, 4, 5, 6, 7 and 8.

### Findings
- **high** Several in-scope MVP FRs (PRD §8.1) have no IA row, no flow and no state, so stories for them have no UX contract:
  - FR-4 password reset
  - FR-10 co-lecturers and Assistant lecturer invitations
  - FR-21 Student choice of game and Seat
  - FR-52 Lecturer excludes questions and changes Item weights
  - FR-59/FR-60 ZIP and Completion export (named in UJ-8 step 5, but no surface)
  - FR-61 AI assessment switched off
  - FR-75 Student data access
  - FR-78 Effort level
  - FR-81 Scoring guide editing
  - FR-82 Control test
  - FR-88 Game data export

  (EXPERIENCE.md IA L45–67; the IA ranges «FR-11–FR-20» and «FR-51–FR-58» imply some of these without placing them). *Fix:* add IA rows, or one-line entries in an existing row, naming the surface and owner. Alternatively, list them explicitly under Open Questions as "spine-only, no layout yet", the way the memlog does for Admin.
- **high** UJ-4 step 9 and its Failure path rest on two Student actions with no defined control, conditions or copy: setting a Pause with an agreed time (FR-89), and «putting in a KI-spiller» for an absent Seat once the agreed time or Inactivity limit has passed (FR-37/FR-89). Only the resulting rows are specified (State Patterns L147–149). Open Question 5 lists the Pause as undrawn, but the insert-AI action is listed nowhere. *Fix:* add a Component Patterns row for each action, covering trigger, eligibility, confirmation copy and who sees what. Then reference them from UJ-4.
- **medium** UJ-6 departs from the PRD journey. The PRD has two Interactive items (draw the bakery inventory, and work out the extra units) and three long answers. The spine has one Interactive item plus «Fyll inn kolonnen» and one «Langsvar» step (EXPERIENCE.md L371–377). *Fix:* align with PRD UJ-6 or FR-52, or record the reduction in the memlog.
- **low** UJ-9 has no edge or failure path, for example the first Class session with no earlier year for Tverrklasse-statistikk. UJ-3 has an edge but no failure, for example a Klasseøkt saved with out-of-range or warned settings (EXPERIENCE.md L323–334, L405–412). *Fix:* add one line each.

## 2. Token completeness — adequate
I extracted all frontmatter tokens: 27 colors, 19 typography roles, 4 rounded, 13 spacing and 29 component objects. I resolved every `{path.to.token}` in both spines: 45 distinct references in DESIGN.md and 6 in EXPERIENCE.md all resolve, and no colour lacks a hex value. Light-only is recorded (DESIGN.md L336; memlog). I recomputed the stated contrast ratios and all are accurate: ink 14.6, ink-secondary 7.3, ink-muted 5.2 and 4.7 on future-tint, lager 5.6, restordre 5.5, order-history 4.46. Matrix cell text is ≥ 4.5 in every step, with the lowest being ink on `net-neg-2` at 4.51.

### Findings
- **high** Focus and interaction states have no visual spec. EXPERIENCE.md defines focus order, focus moves and full keyboard operability for the Ukeskrubber, quiz, Forklaring and Interactive items (L203–212; FR-80; WCAG 2.4.7). DESIGN.md defines no focus ring (colour, width, offset) and no hover, pressed or disabled appearance for `button-*`, `order-input`, `quiz-option`, `view-toggle`, `segmented-choice`, `switch` or `link` (DESIGN.md L159–291, L401–452). *Fix:* add a `focus-ring` component token, for example 2 px `{colors.ink}` with a 2 px offset on `paper` (≥ 3:1). Add `disabled` and `pressed` keys to the interactive component objects.
- **medium** Contrast is stated only against `paper`. Pairs the design depends on are unstated:
  - `ink` text on `restordre-fill` in the Varselbånd: 10.5:1
  - the `button-secondary` `ink-muted` border on `restordre-fill` in the same band: 3.7:1
  - `lager` on `future-tint`: 5.1:1
  - non-text graphics below 3:1 whose role is undecided: the true zero line in `axis` (1.6:1), the Ukeskrubber track in `axis` (1.6:1) and allocation-preview bars in `bar-base` (1.8:1)

  (DESIGN.md L308–321, L433, L450). *Fix:* add these rows to the Colors table. Decide whether the zero line and scrubber track are informative under WCAG 1.4.11. If they are, move them to `ink-muted`.
- **medium** Some values are off-token or unresolvable:
  - The «Alle rader, Uke 11» title is "24/700 (as drawn)" and has no typography token. `title-phone` is 30 and `headline` is 22 (DESIGN.md L422).
  - Stroke widths of 1.1, 1.4, 1.5 and 2 px are hard-coded across components with no stroke scale.
  - Composite values such as `'1px {colors.ink-muted}'` and `'2px dashed {colors.projection}'` will not flatten in a strict DESIGN.md resolver (L169–291).

  *Fix:* map the title to an existing role or add `title-screen`. Add `stroke.hairline/regular/strong` tokens. Split border values into separate `*-width` and `*-color` keys.
- **low** The `matrix-wall` component maps `net-below`, `net-above` and `flows` to step 1 only (`net-neg-1`, `net-pos-1`, `flow-1`, L241–246), while the prose defines 4-step binned scales (L327–332). A token consumer gets one colour. *Fix:* reference the full scales or add a `scale:` key naming the bins.
- **low** Some tokens are defined but not wired:
  - `week-table` maps only phone tokens. `row-laptop`, `row-label-laptop` and `table-cell-laptop` appear only in prose (L208–216, L375).
  - `figure-total`, `title-page`, `title-phone`, `headline` and `step-title` belong to no component.
  - `matrix-cell-min`, `button` and `figure-*` lack `lineHeight`.
  - `lineHeight` mixes px and unitless values.

  *Fix:* add laptop variants and a phone-header component. Normalise `lineHeight`.

## 3. Component coverage — thin
I extracted every component named anywhere in either spine and matched DESIGN.md Components (L401–452) against EXPERIENCE.md Component Patterns (L106–129). All 22 named components appear on both sides, and most carry real rules.

### Findings
- **high** Several components are used in flows, states or mockups but have no row in either spine:
  - the Hjem game card «Spillet venter på deg» with its mini graph-over-table (State Patterns L140)
  - the phone header with Uke, Rolle/Spill and a tappable Totalkostnad in `figure-total` (L109, L359)
  - file upload with «Bytt fil» and the «E-postkolonne» selector (UJ-2)
  - the Matrisevegg filters for Rolle, Celler and Status (L121)
  - the Meldinger composer (drawn in `09-alle-sider.png`)
  - Interactive items and the «Fyll inn kolonnen» table input (FR-80, UJ-6)
  - the Student Pause control and the insert-KI-spiller action
  - the KI-vurdering flag control (UJ-8 step 2)
  - the Debrief step 2 demand band
  - the «Kjedens kostnad over tid» chart (L153, L240)

  *Fix:* add a row on both sides for each, or state which existing component each one reuses, for example "Hjem card = `net-graph` + `week-table`, 4 columns".
- **high** The empty Ordrefelt shows a *secondary* «Bekreft ordre» (EXPERIENCE.md L110). Knapper says secondary buttons "never commit irreversible state" (L111). Nothing says whether the empty-state button is disabled or would confirm 0, and confirming is irreversible with no undo. *Fix:* state "disabled until a valid whole number is entered", specify the disabled visual in DESIGN.md, and state whether 0 is a valid explicit entry.
- **medium** DESIGN.md says every component has behaviour "under the same name" (L403). Its «Lecturer charts (`cost-distribution`, `funnel`, `date-line`, `allocation-preview`)» (L446) appear in EXPERIENCE.md as «Kostnadsfordeling, Trakt, Datolinje, Fordelingsforhåndsvisning» (L129). *Fix:* use the Norwegian names in DESIGN.md with the token keys in parentheses, as the other components do.
- **medium** Two places conflict with the primary-button rules:
  - UJ-3 step 6 has two committing actions on Klasseøkt, «Bekreft fordeling» and «Lagre Klasseøkt», against "one primary button per screen" (DESIGN.md L467; EXPERIENCE.md L111, L129, L332).
  - "On laptop, typing plus Enter confirms [ASSUMPTION]" (L172) would make an irreversible order confirmable by a keystroke, outside the one-tap button contract.

  *Fix:* say which button is primary, or that Fordeling is its own screen. Commit the Enter behaviour, for example "Enter moves focus to the button; it does not submit".
- **medium** Uke-overgang has behavioural rules (≤ 2 s, skippable, never blocks input, reduced motion; L115, L176, L210). DESIGN.md has no motion spec for what moves, duration or easing, and no motion tokens. *Fix:* add a short motion note under Components → Uke-overgang: now-line slide, column fill, duration ≤ 600 ms, linear or ease-out.
- **low** Some visual rows are too thin to build from:
  - `week-summary`: "a short list … and a link" (L428)
  - `funnel`: "horizontal bars … with counts" (L448)
  - "Stegene greyed out" (EXPERIENCE.md L139) uses a term DESIGN.md never defines. DESIGN only gives the `axis` later-dot.

  *Fix:* give anatomy and token per state.

## 4. State coverage — thin
I walked all 20 IA rows (EXPERIENCE.md L47–67) against State Patterns (L131–167), checking for empty, cold-load, focus, error, offline and permission-denied states as applicable. Spill, Debrief, Lag Klasse and Klasseøkt are well covered. Spill alone has 12 states, and each maps to a `06` panel.

### Findings
- **high** The order confirm has no failure state. If «Bekreft ordre på 24» fails or times out, the spine doesn't say whether the order is locked, retried or still editable. This is the product's only irreversible Student action. There is also no global offline or connection-lost pattern: «Reload or new device» (L151) covers resume only. The Oversikt promises live updates within 5 s (L165) but has no stale or disconnected indicator. *Fix:* add Spill «Submit failed» and «Offline» rows (order kept locally, explicit retry, never a silent lock) and an Oversikt «Connection lost» row.
- **high** Whole surfaces have no State Patterns rows:
  - **Logg inn:** wrong password, deactivated user (FR-3), password reset (FR-4)
  - **Startoppgave:** wrong answer, feedback, the optional final question (FR-85)
  - **Replay and Replay-gjennomgang:** locked, in progress, finished, LLM down for the walkthrough
  - **Individuell test:** locked, autosave failed, submitted, auto-submitted at Testfrist. These appear only inside UJ-6.
  - **Alle spill side om side:** locked until own Debrief and Play deadline (FR-86)
  - **Spillinnsikt, Studentside, Klasserapport, Tverrklasse-statistikk:** empty, including "no earlier year"
  - **Admin**

  *Fix:* add at least locked, empty and error rows per surface.
- **medium** There is no cold-load or loading pattern anywhere, though NFR-1 sets a 3 s budget on 4G. There is no pending state for LLM-generated content: the Debrief step 4 AI line, KI-vurdering "not ready yet", and the Replay walkthrough. *Fix:* add one global loading rule (table skeleton in the same columns, no spinners over 1 s) and one AI-pending rule.
- **medium** There is no permission-denied pattern (FR-5) for a Student opening a Faglærer URL, an Assistant lecturer reaching a create or delete action, or an expired session. *Fix:* add a global row.
- **medium** Spill and Hjem have specific gaps:
  - «Class game not started», where the first Student presses start (FR-22)
  - the Student-facing view of a Faglærer-initiated pause (founder decision, issue #25; L123)
  - a capacity-limited Seat holding stock and backlog at once (FR-12)
  - Hjem when the game is paused, when it is finished with the Debrief open, and when the test is open

  *Fix:* add rows; mark undrawn ones with [ASSUMPTION].
- **low** Smaller missing states:
  - Lag Klasse: unreadable or wrong-format file, and bounced Invitations (NFR-10)
  - Landing: «Be om lærertilgang» form error and success. The form itself is an assumption (L135).

## 5. Visual reference coverage — adequate
`mockups/` holds 01–10 as `.png` and `.svg` (20 files), and `imports/` is empty. All 10 PNGs are referenced in at least one spine: in DESIGN.md L296 and L367–377, and in EXPERIENCE.md IA L49–67, State Patterns (`06` A–F), the Debrief sequence and Key Flows. "Spines win on conflict" is stated in DESIGN.md L296 and EXPERIENCE.md L28. Known conflicts are named: the header name, «Uker spilt», `axis` borders, 12 px labels and the 38 px button. I checked the mockup text via the SVGs. The `06` panels A–F exist as cited.

### Findings
- **high** One conflict is not acknowledged. `10-pedagogikk.png` draws «Posisjon 24», «Posisjon 3», «Posisjon 42» and «Posisjon 37» in the **Class-game** Kjedebånd at Uke 5, 11, 18 and 29. DESIGN.md L377 cites this sheet for the chain-band scale rule, and UJ-5 cites it too. The spine bans Posisjon in the Klassespill but words the ban as "no Posisjon **row**" (EXPERIENCE.md L109, L224), which leaves the band label open. A consumer building the band from the cited sheet would show the sum that issue #22 and stance 1 hide. *Fix:* add to Kjedebånd (both spines): "Never shows Posisjon in the Klassespill; the «Posisjon n» labels in `10-pedagogikk.png` are superseded (Replay only)."
- **medium** All 10 `.svg` files are orphans. Neither spine mentions them or says whether they are the vector source with the same content as the PNGs, or which format to measure from. *Fix:* add one line in DESIGN.md's preamble, for example "Each PNG has an SVG twin with identical content; measure from the SVG."
- **low** Several references are not specific:
  - Mockup references are code spans, not links, and IA and Key Flows use bare filenames without `mockups/`.
  - DESIGN.md Components has no per-component mockup references, and its preamble cites a range, «01 to 10».
  - Nothing says what `10-pedagogikk.png` illustrates: P1–P8 across Uke 5, 11, 18 and 29, plus the post-Debrief Simulert comparison.
  - `09-alle-sider.png` is cited for 12 IA rows without naming the panel (Key Flows do name panels).
  - UJ-1 cites "the contact-sheet mockup" with no filename (L300).

  *Fix:* use relative Markdown links and name the panel each time.
- **low** `09-alle-sider.png` «Individuell test» draws only Flervalg, Fyll inn kolonnen and Langsvar. The drawing Interactive item in UJ-6 step 4 is undrawn, but Open Question 5's undrawn list (L420) omits it. *Fix:* add it to the list.

## 6. Bloat and overspecification — adequate
Both spines are mostly lean. DESIGN.md's editorial voice is confined to Brand & Style, and the EXPERIENCE.md tables carry most of the behaviour.

### Findings
- **medium** The cost picture is specified in four places: DESIGN.md `cost-panel` (L423–427), the Component Patterns rows «Kostnad så langt» and «Kjedens regning» (L114, L118), the Hidden information «Cost» row (L225) and the Cost picture section (L230–251). Kjedens regning appears in three. These copies will drift. *Fix:* keep the visual spec in DESIGN.md and the behaviour once in Component Patterns. Cut Cost picture down to the cross-surface rules: rates binding, who sees what, and Faglærer-only sorting.
- **medium** Fixture values read as product rules:
  - «Restordre costs 1,00 and Lager 0,50» and the key text «restordre 1,00 / lager 0,50» (L232; DESIGN.md L411)
  - "the order is fixed at 4" in Veiledet uke (L142)
  - «Restordre er 60 % av kjedens regning, fordi den koster dobbelt» (L244)
  - "fits the phone in all 36 Uker" (DESIGN.md L380)

  FR-12 makes costs, Guided Weeks, demand and the number of Weeks configurable, so a consumer may hard-code these. *Fix:* mark them as Classic defaults bound to Game settings, and flag templated copy, for example «Restordre er {andel} % …».
- **low** The DESIGN.md Typography table restates the frontmatter sizes («48/56 700», «34 700» …, L346–359), which is a drift risk. *Fix:* keep the Role, Token and Where columns and drop the numbers.
- **low** Decision rationale sits inside behaviour tables: the Startoppgave IA row (L54) and the Varselbånd row's founder decision and issue note (L123). Some Key Flow lines are decorative: «Sara's 24 in Uke 11 towers over flat demand» (L358) and «The next order builds on a sum, not on an answer key» (L347). *Fix:* move the rationale to the memlog and keep the flows literal.
- **low** «`vlib.py` checks contrast at build time» (DESIGN.md L306) and «The build checks that the band fits the phone in all 36 Uker» (L380) describe mockup scripts. It is unclear whether the product build must enforce them. *Fix:* restate them as product test requirements or drop them.

## 7. Inheritance discipline — thin
All 13 frontmatter `sources` resolve in both spines. The UJ headings match the PRD verbatim. All 6 EXPERIENCE.md token references resolve to DESIGN.md tokens by name. The «ØL-spillet» override (issue #25) is handled consistently:
- DESIGN.md has `name: ØL-spillet`.
- The landing-header conflict is acknowledged (L296).
- EXPERIENCE Foundation lists every place the name appears (L34).
- Voice keeps «Beer Game» and «bullwhip» out until Debrief step 2, which introduces «Øvelsen heter Beer Game.»
- Open Question 7 tracks the PRD update.

### Findings
- **high** No glossary maps PRD terms to UI terms. The PRD §3 glossary is English, and PRODUCT.md fixes only eight Norwegian terms. The spines mix three kinds of term:
  - Norwegian UI terms: Faglærer, Klasseøkt, Labtime, Forklaring, På vei, Spillinnsikt, Forsterkning, Spillfrist and Testfrist
  - English glossary terms: Seat, Class game, Takeover, Interactive item, Detected patterns, Indicative letter
  - hybrids: «Guided Uke» (L293)

  They also introduce domain terms that no source defines: Netto lager, Posisjon (formula only in `.working/concepts-r3/_shared/BRIEF.md` L67), Kjedekost and Kjedebånd. Architecture and story authors work from PRD nouns and need a one-to-one map to UI strings. *Fix:* add a Terms table in EXPERIENCE Foundation with the columns PRD term → UI string → definition or note, including the new terms.
- **medium** «Assistant» in the Oversikt IA row (L65) is neither the glossary term "Assistant lecturer" nor the UI string «Assistent» drawn in `09-alle-sider.png`. *Fix:* use the mapped pair.
- **medium** Component names drift into English aliases: «chain band», «order input», «matrix wall», «Debrief scrubber» and «the wall» appear in DESIGN.md Layout (L365–381), EXPERIENCE Interaction Primitives (L171–175), Accessibility Floor (L192–208) and Hidden information (L219). *Fix:* use the Component Patterns name everywhere.
- **medium** Load-bearing labels are undefined in the spines. «P1–P8» drives the Debrief sequence's Principle column (L266–273), IA L54 and Open Question 2, and «stance 1/2/3» drives L77, L109 and L223–225. They are defined only in BRIEF.md (Norwegian, a working file) and the memlog. DESIGN.md defines P1 alone (L300). *Fix:* inline an 8-row principle table and a 3-row stance table, or link to them by heading.
- **low** Row labels drift. The phone and laptop rows say «Kost, kr» (L77–78, matching `05`), while DESIGN.md «Alle rader» and `10` and `01` say «Kost per uke» (L422). «Sum, hele kr» is mentioned as removed (L238) but never listed. *Fix:* pick one label per row and list the canonical row set once.

## 8. Shape fit — strong
DESIGN.md sections run in canonical order: Brand & Style → Colors → Typography → Layout & Spacing → Elevation & Depth → Shapes → Components → Do's and Don'ts, with none omitted. EXPERIENCE.md has all eight required defaults, plus Responsive & Platform, which applies because the product is multi-surface. Every invented section is load-bearing for a PRD constraint:
- Hidden information and help level (FR-14, FR-23, FR-83, issue #22)
- Cost picture
- Chain direction convention (it supersedes addendum §B)
- Debrief sequence
- AI disclosure (FR-34, FR-55)
- Demo/synthetic data labelling (§6.2)
- Open Questions

### Findings
- **low** Inspiration and anti-patterns apply, since the memlog records rejected directions and the yr.no reference. They are folded into Foundation as «Rejected directions» and «Lifted» (L37–43) instead of their own section. *Fix:* promote them to a short "Inspiration & Anti-patterns" section so extractors find them.
- **low** The EXPERIENCE.md frontmatter has no `name` key, which the paired examples carry. Both spines are `status: draft`. *Fix:* add `name: ØL-spillet` and set the status at finalisation.

## Mechanical notes
- **Sources:** 13 of 13 entries resolve from WS: the PRD, the addendum, PRODUCT.md, the memlog, decisions.md, 6 `.working/valgt-konsept/` files, `mockups/` and BRIEF.md. Both spines carry identical source lists. Python build scripts listed as design sources are unusual, but they resolve.
- **Frontmatter:**
  - DESIGN.md has `name`, `description`, `colors` (27, all hex), `typography` (19), `rounded` (4), `spacing` (13) and `components` (29).
  - The titles say «beergame», which is consistent with the "repository name" rule (EXPERIENCE L34).
  - EXPERIENCE.md lacks `name`.
- **Token references:** all resolve. 45 distinct `{…}` references across both files; 0 unresolved. The `{colors.…}` placeholders at EXPERIENCE L26 are illustrative. Composite strings such as `'1px {colors.ink-muted}'` are not spec-clean values.
- **Name inconsistencies:**
  - Lecturer charts vs Kostnadsfordeling, Trakt, Datolinje and Fordelingsforhåndsvisning. This also makes DESIGN L403's "same name" claim false.
  - «Assistant» vs «Assistent» vs "Assistant lecturer".
  - «Kost, kr» vs «Kost per uke».
  - English component aliases in the prose.
  - «Guided Uke» hybrid.
- **Cross-refs:** issues #22, #24 and #25 exist and are open. The P1–P8 and stance 1–3 codes resolve only through working files and the memlog. `06` A–F panel letters were verified in `06-spilldynamikk.svg`.
- **Unacknowledged mockup conflict:** «Posisjon» in the Class-game band in `10-pedagogikk` (see §5).
- **Assumptions:** 1 `[ASSUMPTION]` in DESIGN.md and 23 in EXPERIENCE.md. The load-bearing ones still uncommitted are:
  - the laptop breakpoint at 1024 px (L78)
  - no phone nav bar (L70)
  - Enter confirms on laptop (L172)
  - other FR-44 moments paged inside Debrief step 4 (L271)
  - FR-45 placement (L275)
  - matrix row click opens Spillinnsikt (L121)
- **Contrast arithmetic:** every stated ratio was recomputed and matches. The closest pass is `ink` on `net-neg-2` at 4.51:1, so any palette tweak breaks it.
- **Mermaid:** none in either file.
