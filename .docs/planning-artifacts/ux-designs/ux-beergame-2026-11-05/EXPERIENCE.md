---
title: "EXPERIENCE: beergame"
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
---

# ØL-spillet: Experience Spine

## Foundation

ØL-spillet is a responsive web app in Norwegian bokmål (FR-72). It is portrait-first on the phone for Students (FR-73) and laptop-first for Faglærer surfaces. No third-party UI system is named, and `DESIGN.md` owns every visual. This spine owns behaviour. It references tokens as `{colors.…}`, `{typography.…}` and `{spacing.…}`.

- **Mockups** live in `mockups/` (10 sheets) and are linked per section. These spines win on conflict; every known deviation is listed in `DESIGN.md` → Mockup deviations.
- **Example numbers** come from the synthetic «spill 17» fixture and are examples only:
  - Sara (Grossist) in Uke 11: Totalkostnad 68,00 = 43,00 + 25,00.
  - Chain total 2 266,00 = 901,00 + 1 365,00.
  - Simulert 1 507,00 and 1 341,00.
  - Forsterkning 1,8× / 4,1× / 6,0× / 7,6×.
- **Names.** The product is «ØL-spillet» everywhere a name appears: landing, app header, Invitasjon e-mail, login and the PDF Studentrapport. This is a founder override of FR-84, recorded in the memlog on 2026-11-09. "beergame" is only the repository name.
- **Language.** UI strings are quoted verbatim in Norwegian. People are referred to by name or as "they".
- **Spine-specific sections.** Responsive & Platform (layout per device) follows Information Architecture. After Accessibility Floor come Hidden information and help level (what each round shows and hides), Cost picture (which costs appear where, and never), Chain direction convention (the left-to-right order of the chain), Debrief sequence (the five steps and Delt skjerm), AI disclosure (where and how AI is named) and Demo/synthetic data labelling (Demodata and Simulert). Open Questions closes the spine.

**Terms.** PRD glossary nouns (§3) map to UI strings as below. Spine prose uses the UI string, except Seat, Role, Class game, Takeover, Reclaim and Start date, which keep the PRD term, as do other PRD terms where a sentence paraphrases an FR. Terms with no drawn string are [ASSUMPTION] until copy review.

| PRD term | UI string | Note |
|---|---|---|
| Admin, Admin area | Admin, «Admin-område» | |
| Lecturer, Assistant lecturer | Faglærer, Assistent | |
| Student, User | Student, bruker | |
| Institution | Institusjon [ASSUMPTION] | Admin only |
| Invitation | Invitasjon | |
| Class, Roster | Klasse, klasseliste | «E-post, fra klasselisten» (`04`) |
| Class session | Klasseøkt | |
| Game settings | Spillinnstillinger | Preset «Klassisk» |
| Information visibility | Synlige naboer [ASSUMPTION] | FR-83 |
| Demand pattern | Etterspørsel [ASSUMPTION] | Faglærer setup only |
| Game, Class game, Replay | Spill, Klassespill, Replay | |
| Role: Retailer, Wholesaler, Distributor, Factory | Rolle: Detaljist, Grossist, Distributør, Fabrikk | PRODUCT.md |
| Seat | Sete (plural Setene) | |
| Week, Order | Uke, Ordre | |
| inventory, backlog | Lager, Restordre | |
| incoming order, incoming delivery, units shipped | Ordre inn, Levering, Sendt | |
| Supply line | På vei | |
| — | Netto lager | Lager − Restordre. Negative means backlog |
| — | Posisjon | Lager − Restordre + På vei, that is Netto lager + På vei. Shown in Klassespill and Replay |
| Guided Weeks | Veiledede uker (one: Veiledet uke) | |
| Starting task | Startoppgave | |
| Total cost | Totalkostnad (Seat), Kjedens totalkostnad (chain) | |
| — | Kjedekost | Chain Total cost of one Class game, Faglærer views only |
| — | Kost per uke | Cost charged in one Uke |
| Order amplification | Forsterkning | «1,8×» |
| Detected patterns | Mønstre [ASSUMPTION] | Klasserapport, Debrief |
| AI player, LLM player, Rule-based player | KI-spiller, LLM-spiller, regelbasert KI-spiller [ASSUMPTION] | Students only ever see «KI-spiller» |
| AI mode, Effort level | KI-modus, Innsatsnivå [ASSUMPTION] | |
| Play guard | (no name in UI) | Setestatus copy only |
| Inactivity limit | Ventetid før KI tar over [ASSUMPTION] | |
| Pause, Takeover, Reclaim | Pause, «KI-spiller bestiller for …», «Ta tilbake setet» | |
| Lab hour | Labtime | |
| Start date, Play deadline, Debrief deadline, Test deadline | Startdato, Spillfrist, Debrieffrist [ASSUMPTION], Testfrist | |
| Explanation | Forklaring | |
| Group debrief, Personal debrief, Debrief quiz | Gruppedebrief, Personlig debrief, Debrief-quiz | |
| Individual test, Interactive item | Individuell test, Interaktiv oppgave [ASSUMPTION] | |
| Core items, Adapted items, Item weight | Faste oppgaver, Tilpassede oppgaver, Vekt [ASSUMPTION] | |
| Scoring guide, Control test | Sensorveiledning, Kontrolltest | |
| AI assessment, Indicative letter | KI-vurdering, Veiledende bokstav [ASSUMPTION] | |
| Student report | Studentrapport | PDF |
| Completion status, Completion export | Fullføring, fullføringsliste [ASSUMPTION] | |
| — | Oppfølgingsspill [ASSUMPTION] | FR-17 make-up: a solo Klassespill against three KI-spillere |
| — | Tilrettelegging [ASSUMPTION] | FR-17 per-Student adjustment of the Inactivity limit and the share |
| — | I rommet [ASSUMPTION] | FR-36: a Klassespill marked as played in the room during a Labtime, with a shorter limit |
| Obligatory class session | Obligatorisk | |
| Lecturer overview, Game insight | Oversikt, Spillinnsikt | |
| Class report, Cross-class statistics | Klasserapport, Tverrklasse-statistikk | |
| Message | Melding | |
| — | Kjedebånd, Graf over tabell, Varselbånd | Component names (see Component Patterns) |

**Rejected directions (memlog):** metaphor worlds and illustrated concepts (round 1, "childish"). The other rejected directions are listed under Interaction Primitives → Banned.

**Lifted:** the yr.no meteogram, with the graph over a table on one time axis.

## Information Architecture

| Surface | Role | Reached from | Purpose | Mockup |
|---|---|---|---|---|
| Landing | Public / Faglærer | URL | Persuade a Faglærer. «Be om lærertilgang», «Logg inn» | `01-landing.png` |
| Du er invitert (registration) | Student, Faglærer | Invitasjon e-mail | Create an account. E-mail is prefilled and not editable (FR-4) | `04-student-hjem.png` left |
| Logg inn | All | Landing, invitation | E-post og passord. Ingen åpen registrering | `09-alle-sider.png` |
| Glemt passord, Nytt passord | All | Logg inn «Glemt passord?», reset e-mail | FR-4: reset by e-mail without the Admin | Spine-only |
| Mine data | Student | Hjem → profile | FR-75: every category of stored data, each viewable, with the Studentrapport as the main download | Spine-only |
| Hjem (Student) | Student | Login | Spill, Rolle, Setene, Stegene, Neste frist, Labtime | `04-student-hjem.png` right |
| Regler før første ordre | Student | First open of the Class game | FR-84 briefing: one real Uke explained | `09-alle-sider.png` |
| Startoppgave | Student | After the rules | FR-85 stocks-and-flows task on one column, including «Regn posisjonen for én Uke». Students learn the sum behind the Posisjon row before play; the Debrief shows whether their orders used it (P3) | `09-alle-sider.png` |
| Velg spill og sete | Student | Hjem, before the Start date, when the Klasseøkt uses Student choice | FR-21: pick a Klassespill and a free Sete | Spine-only |
| Spill (Klassespill) | Student | Hjem «Gå til Uke n» | The weekly decision | `05-spill.png`, `06-spilldynamikk.png` |
| Alle rader og kostnad | Student, phone | Order-input link or tap on Totalkostnad | All rows and «Kostnad så langt» | `05-spill.png` middle |
| Spillet er ferdig | Student | Last Uke | Chain total first, then «Gå til Debrief» (FR-28) | `06-spilldynamikk.png` F |
| Debrief (5 steps + Delt skjerm) | Student group | Game end, Hjem | FR-41–FR-46 | `07-debrief.png` |
| Replay, Replay-gjennomgang | Student | Stegene, after the quiz | FR-48–FR-50 | `09-alle-sider.png` |
| Individuell test, KI-vurdering, Studentrapport (PDF) | Student | Stegene | FR-51–FR-58 | `09-alle-sider.png` |
| Alle spill side om side | Student | After own Debrief and the Play deadline | FR-86 | `09-alle-sider.png` |
| Lærerhjem | Faglærer | Login | Klassene dine, what is waiting, next deadline | `09-alle-sider.png` |
| Lag Klasse | Faglærer | Lærerhjem «Ny Klasse» | FR-6–FR-9 | `02-laerer-klasse.png` |
| Faglærere og assistenter | Faglærer | Klasse | FR-10: add a Faglærer as co-owner, invite an Assistent by e-mail for this Klasse only | Spine-only |
| Klasseøkt | Faglærer | Klasse | FR-11–FR-20, FR-83, FR-87. Also holds the spine-only blocks below | `03-laerer-spill.png` |
| Klasseøkt → «Innsatsnivå» | Faglærer | Klasseøkt, shown only when «LLM-spillere» is chosen | FR-78: choose an Effort level from the offered ones | Spine-only |
| Klasseøkt → «Spørsmål og vekter» | Faglærer | Klasseøkt | FR-52: review the question set, take questions out, change Vekt; sum must be 100 % | Spine-only |
| Klasseøkt → «Sensorveiledning» | Faglærer | Klasseøkt | FR-81: edit the Scoring guide for this Klasseøkt; shows whether it is checked | Spine-only |
| Klasseøkt → «KI-vurdering» | Faglærer | Klasseøkt | FR-61: switch the AI assessment off | Spine-only |
| Klasseøkt → «Eksport» | Faglærer, Assistent (reports only) | Klasseøkt | FR-59 ZIP of all Studentrapporter, FR-60 Completion export (CSV or Excel), FR-88 Game data export (CSV) | Spine-only |
| Oversikt | Faglærer, Assistent | Klasseøkt | FR-39, FR-40 | `08-laerer-oversikt.png` |
| Spillinnsikt, Studentside, Klasserapport, Tverrklasse-statistikk, Alle spill i plenum, Meldinger, Lærers testspill | Faglærer | Oversikt and Klasse | FR-62–FR-65, FR-86, FR-40, FR-87 | `09-alle-sider.png` |
| Spillinnsikt → «Spillstyring» | Faglærer; Assistent only the per-Seat «Sett inn KI-spiller for …» | Spillinnsikt; the Varselbånd's «Pause spillet» opens its pause form in place | FR-22 start, FR-36 «I rommet», FR-37 manual Takeover, the Faglærer pause with the agreed time (FR-89 extension, issue #25) | Spine-only |
| Oversikt → «Start spill», «Sett inn KI-spillere» | Faglærer | Oversikt header Lenker | FR-22 start all at once, FR-37 fill every Seat the games wait for in one action. Each is its own page, like Meldingsskjema | Spine-only |
| Studentside → «Tilrettelegging», «Fullføring» | Faglærer | Studentside | FR-17: per-Student Tilrettelegging, Completion correction with a reason, Oppfølgingsspill | Spine-only |
| Admin-område, Brukere og roller, KI-kostnad | Admin | Login | FR-1–FR-3, FR-69 | `09-alle-sider.png` |
| Admin-område → «Kontrolltest» | Admin | Admin-område | FR-82: set up a Control test, mark test students, compare human and AI scores side by side | Spine-only |

**Spine-only** surfaces have no mockup. They are built from the patterns in this spine (Tekstfelt, Valgknapper, Bryter, Knapper, Lenke, Tilkoblingslinje) and `DESIGN.md` → Components, and add no features beyond the cited FR.

**Navigation:**
- Student: Hjem is the hub. Stegene is the linear path, Klassespill → Debrief → Quiz → Replay → Individuell test → Rapport, and each step opens when the previous one is done (FR-17, FR-42, FR-48, FR-51). [ASSUMPTION: no global nav bar on phone. Back returns to Hjem.]
- Faglærer: Lærerhjem → Klasse → Klasseøkt / Oversikt.

## Responsive & Platform

| Surface | Form | Layout behaviour |
|---|---|---|
| Student, phone (Klassespill, Replay) | Portrait. Design target 360 px (mockups at 390), reflow floor 320 CSS px | Kjedebånd, then Graf over tabell (Uke nå − 7 to nå + 4), then Ordrefelt. Rows: Uke, Ordre inn, Levering, Netto lager, Posisjon, Din ordre, Kost, kr. «Alle rader og kostnad» is one tap away, which meets FR-23 at 360 px and 100 % text with no horizontal scroll (accepted stance 2). Below that width or at larger text, Graf over tabell scrolls inside its own region (`DESIGN.md` → Layout & Spacing); nothing else scrolls sideways. |
| Student, laptop in Labtime | Landscape | Two columns as in `DESIGN.md` → Layout & Spacing → Devices, with «Kostnad så langt» always visible. Rows: Uke, Ordre inn, Levering, Sendt, Netto lager, På vei, Posisjon, Din ordre, Kost, kr. [ASSUMPTION: the laptop layout applies from 1024 px wide. Tablets get the phone layout in portrait and the laptop layout in landscape.] |
| Student, other flows | Phone and laptop | Registration, Startoppgave, Debrief, Quiz, Replay and Individuell test work from 360 px (FR-73) and reflow at 320 px. For long answers, the phone advises a larger screen. |
| Faglærer laptop | 1440 design canvas, laptop layout from 1024 px [ASSUMPTION, as for Students]; reflow floor 320 CSS px (NFR-6) | Oversikt: graph over the matrix wall, with a right rail. Usable on a tablet (FR-73). The laptop stays the design target; 320 CSS px (1280 px at 400 % zoom) is a floor that must work, not a layout to tune. Below 1024 px the page is one column: headline counts, Varselbånd (text first, its actions wrapped under it at full width), the wall controls, the median graph and Matrisevegg (or its table) in one scroll region, then the right rail stacked under the wall. Every Faglærer and Admin form is one column. Only the two-dimensional list in `DESIGN.md` → Layout & Spacing scrolls sideways, each inside its own region. |
| Plenary projector | Shared screen | «Delt skjerm» in the Group debrief (FR-74) shows only the shared charts. Each Student follows their own step on their phone. «Vis i plenum» (FR-86) shows 60 games as a matrix «uten navn og uten rangering». |
| Landing | Laptop first | [ASSUMPTION: on phone the columns stack: headline, lead, buttons, Seat chart, then «Kostnad så langt».] |

## Voice and Tone

Microcopy only. Posture lives in `DESIGN.md` → Brand & Style.

| Do | Don't |
|---|---|
| «Bekreft ordre på 24». The button repeats the number | «Send», «OK», «Spill!» |
| «Kommer fram om lag Uke 15. Kan ikke endres etter at du har bekreftet.» | «Er du sikker?» |
| «Venter på: Jonas (3 min) og deg.» Role or name plus duration | «Venter på andre spillere …» |
| «Denne uka: 13 restordre × 1,00 = 13,00 kr». Show the sum, not a verdict | «Du burde bestille mer», «Bra jobba» |
| «Kundene bestilte 4, så 8. Etter det endret de seg aldri.» | Blame or praise («Jonas ødela», «Godt spilt!») |
| «Struktur gir atferd, derfor spør vi hvorfor og ikke hvem.» | «Hadde du rett?» framing |
| «KI-generert, kan ta feil: «…»» | Unlabelled AI text |
| «Simulert viser sammenhengen, ikke en fasit.» | «Optimal», «fasit», «beste ordre» |
| «enheter», «Antall enheter» | «øl», «kasser øl», «Beer Game» or «bullwhip» before the Debrief (the product name «ØL-spillet» is the only exception) |
| Second person, direct and concrete. Short declarative sentences. Norwegian number format («2 266,00 kr») | Exclamation marks, emoji, cheerful filler, «11 av 36» |
| Faglærer copy states consequences: «Ingen får beskjed før du bekrefter.», «Du kan lagre uten å endre noe.» | Hedged or marketing copy, learning claims (§6.2) |

## Component Patterns

Behaviour only. Visual specs live in `DESIGN.md` → Components, under the same names and in the same groups. A component with long rules has a one-line row and its own subsection under its group's table. Copy for the Pause and Takeover states lives in State Patterns → Student game, and for the Faglærer's actions in State Patterns → Faglærer live.

### Interaction states

| Component | Behavioural rules |
|---|---|
| Fokusring | Shown on keyboard focus (`:focus-visible`) on every interactive element, including table rows and wall rows that open something. Never removed. Tab order follows reading order. |

### Game screen

| Component | Behavioural rules |
|---|---|
| Topplinje | Top of the phone game screen: Uke, Rolle and Spill, and Totalkostnad. The Totalkostnad pair is one button named «Totalkostnad 68,00 kr, vis alle rader og kostnad»; it opens Alle rader og kostnad. Never shows the number of Uker (FR-14). |
| Kjedebånd | Shows only the Seat's own link during play (FR-23). Upstream neighbour on the left, downstream on the right (see Chain direction). It updates as the order is typed: «På vei 16 + 24», with the new box last on the pipe. Not interactive. [ASSUMPTION: Fabrikk's band shows «Produksjon» at the left end and Detaljist's shows «Kundene» at the right (addendum §B). Only Detaljist sees the customer number, one Uke at a time (FR-14).] |
| Graf over tabell | One column per Uke up to nå + 4; typing writes two cells; Posisjon shows as a row and a line. See below. |
| Ordrefelt | The weekly order, a whole number from 0 to {maks}. See below. |
| Alle rader og kostnad | A full screen on phone, titled «Alle rader, Uke 11», with «Lukk». It holds all rows on the same axis, including Posisjon and «Sum, kr», the column sums «Netto lager i kolonne 11  −9 + 4 − 8 = −13» and «Posisjon i kolonne 11  −13 + 16 = 3», and «Kostnad så langt». It returns to the order with the typed value kept. |
| Kostnad så langt | Shows the Seat's own cost only during play. Laptop: pinned beside the order input. Phone: one tap away. It recalculates when a Uke is charged, not while typing. On laptop, «Vis som tabell» under «Totalkostnad over tid» opens its table in place; on phone the «Sum, kr» row in Alle rader is that table. |
| Uke-overgang | After the last of the four orders in a Uke: «Uke 11 er ferdig regnet», then the deltas («Restordre 13 blir 20»), «Denne uka: 20 restordre × 1,00 = 20,00 kr» and the link «Kostnad så langt». The now-line moves one column. The new Uke shows within 2 s (FR-26, NFR-1). «Hopp over» skips the animation, which never blocks input. |

#### Graf over tabell

| Rule | Behaviour |
|---|---|
| Columns | One column per Uke. The right edge is nå + 4, never the end. |
| Typing | Typing an order writes the value into two cells at once: Din ordre at nå, and Levering at nå + 4, joined by a line. |
| Known arrivals | Known arrivals right of nå are labelled as ordered, not guaranteed (stance 3). |
| Posisjon | Shows as a row and as a line in both the Klassespill and the Replay (founder decision 2026-11-09). Posisjon at nå is the value before this Uke's order («Posisjon 3» in Uke 11); the typed order shows in the Kjedebånd («På vei 16 + 24») and enters Posisjon when the Uke advances. |
| Projection | Only the Replay adds the projection (see Hidden information). |
| Scrolling | Graph and table scroll sideways together in one region when columns run out (`DESIGN.md` → Layout & Spacing): the region has `role="region"`, the name «Graf og tabell» and `tabindex="0"` so arrow keys scroll it. On load and after each Uke advance, the region scrolls back so that the nå column and «Nå» are in view, with as many of nå + 1 … nå + 4 to its right as fit. When all 12 columns fit, nå + 4 is the right edge. |
| Table semantics | Table cells are not focusable; the table has `<th scope="col">` per Uke and `<th scope="row">` per row. |
| Totalkostnad | Tapping the Totalkostnad figure opens «Alle rader og kostnad» on phone. |

#### Ordrefelt

| Rule | Behaviour |
|---|---|
| Range | Whole numbers from 0 to {maks}, the Game settings maximum (FR-24). 0 is a valid order. |
| Field | `type="text" inputmode="numeric" pattern="[0-9]*"`, never `type="number"`, so a mouse wheel cannot change it. The help line «Hele tall fra 0 til {maks}.» is always shown and tied to the field with `aria-describedby`. |
| Empty | «Antall enheter», «Sist Uke bestilte du 8.», and «Bekreft ordre» disabled (`aria-disabled`, still focusable). Pressing it shows «Skriv et helt tall fra 0 til {maks}.» |
| Invalid | Letters, decimals, a minus, spaces: «Skriv et helt tall fra 0 til {maks}.» |
| Out of range | «{n} er mer enn {maks}. Skriv et helt tall fra 0 til {maks}.» |
| Error timing | The error appears as soon as the text is not valid, sets `aria-invalid="true"`, and is announced (`role="alert"`) when the Student leaves the field or presses the button, not on every keystroke. The button stays disabled until the value is valid. |
| Valid | The button is primary, «Bekreft ordre på 24». |
| Enter | Enter in the field moves focus to the button and never submits; only the button confirms. |
| − / + | Named «Én færre» / «Én flere», step by 1, and the new value is announced politely. − is unavailable at 0 and when empty; + on an empty field gives 1 and is unavailable at {maks}. Unavailable means `aria-disabled="true"`, never the native `disabled`: the segment keeps focus, shows the disabled look, and a press does nothing (Accessibility Floor → Focus and order). |
| Veiledede uker | The field is read-only with the fixed order, placed automatically (FR-24). |
| Submitting, failure, offline | See State Patterns → Student game. |

### Controls

| Component | Behavioural rules |
|---|---|
| Knapper | There is one primary button per screen. «Bekreft ordre på 24» confirms and locks the order with one tap. There is no undo and no second dialog, because the consequence is already written above the button. Secondary buttons («Logg inn», «Kjør fordeling på nytt», «Ta tilbake setet», «Vis i plenum», «Sett inn KI-spiller for Jonas») never commit irreversible state. A button that cannot act yet is disabled, never shown as secondary (the empty «Bekreft ordre»). Visual states: `DESIGN.md` → Components → Interaction states. |
| Lenke | Links navigate or open a panel and never commit anything: «Alle rader og kostnad», «Kostnad så langt», «Hopp over», «Bytt fil», «Registrer manuelt», «Send påminnelse til 10», «Legg til Labtime», «Melding». |
| Tekstfelt | Labelled above. Lag Klasse shows an invalid row inline with its reason («Domene mangler», «Mangler @», «To @», «Tom celle») and «Registrer manuelt». The Forklaring field must be saved before the Debrief moves on (FR-41). |
| Valgknapper | Klasseøkt choices take effect when «Lagre Klasseøkt» is pressed. They lock at the Start date (FR-18). Help text under each states the scope: «Gjelder alle KI-spillere i Klassespill og Replay.» |
| Bryter | In the Klasseøkt, a Bryter follows the Valgknapper rules. |

### Seats and status

| Component | Behavioural rules |
|---|---|
| Setestatus | Lists all four Seats with Role, name or «KI-spiller», and «har bestilt» / «venter, 3 min» / «venter (deg)» (FR-25). It appears on the game screen after the Student confirms an order, and on Hjem. It updates live. It hosts Pausevalg below the list and Sett inn KI-spiller on an absent Seat's row. |
| Pausevalg | A Student sets a Pause without a time (FR-89); only the Faglærer sets an agreed time (Spillstyring). See below. |
| Sett inn KI-spiller | Puts a KI-spiller into an absent Seat once that Seat's insert time has passed, whether or not a Pause is running (FR-89, FR-37). See below. |
| Spillkort | Hjem's card while the Klassespill runs. «Spillet venter på deg» with «Gå til Uke 11» when the game waits for this Student (FR-25); other states in State Patterns → Student game. The mini graph is `aria-hidden`; the card's text plus «Netto lager −13 i Uke 11.» is its alternative. |
| Stegene | Shows the six steps and marks the current one («pågår»). Later steps are listed but not active until unlocked. |

#### Pausevalg

| Rule | Behaviour |
|---|---|
| Trigger | «Ta pause» under Setestatus on Spill and Hjem. |
| Eligible | Any Student in a started, unfinished Klassespill that is not already paused. Not in the Replay, where no one waits. |
| Form, in place | No date or time field: a Student cannot set or shorten an agreed time (founder decision 2026-11-10). [ASSUMPTION: a Student can still pause under FR-89, always without a time.] Consequence lines: «Mens spillet har pause, tar ingen KI-spiller over setene. Spillfristen flyttes ikke.» and «Bare faglæreren kan avtale et tidspunkt. Uten det har hver av dere sin vanlige ventetid før en KI-spiller kan settes inn.» Primary «Ta pause uten avtalt tid», and the link «Avbryt». |
| Agreed time | Only the Faglærer sets one, on any paused game or by pausing it (Faglærer → Spillstyring). It then shows in every Seat's pause line. Without it, each absent Seat's own Inactivity limit governs Sett inn KI-spiller, so a peer can never shrink another Student's window. A time proposed with the FR-22 scheduling aid never governs Sett inn KI-spiller. [ASSUMPTION] |
| After | All four Seats see the pause line on Spill and Hjem; the Oversikt shows the game as paused, since when and by whom. Copy: State Patterns → Student game → Paused. |
| End | Any Student ends the pause by ordering (FR-89), including a pause the Faglærer set [ASSUMPTION]. A right to Sett inn KI-spiller that has already arisen survives the end. Automatic Takeover then resumes on the FR-36 clock, which kept running during the Pause; a Seat whose limit has already run is taken over at once. [ASSUMPTION] Copy: State Patterns → Student game → Pause ended. |
| Status | Spine-only. |

#### Sett inn KI-spiller

| Rule | Behaviour |
|---|---|
| Shown (the one eligibility rule) | To every other Student in the game, on the absent Seat's Setestatus row (Spill and Hjem), while all three hold: (1) a Student holds the Seat and has not ordered this Uke; (2) the Seat's insert time has passed; (3) no Takeover of the Seat is done or queued. A running Pause is not a condition: the right survives the end of a Pause and lasts until the Seat orders, any Takeover happens, or the Uke advances. Outside a Pause, automatic Takeover (FR-36) fires at the same moment the right arises, so in practice the button shows during a Pause or after a Faglærer's agreed time. |
| Insert time | If the Faglærer set an agreed time for a Pause in this Uke: that time. Otherwise: the Seat's own Inactivity limit, counted on the FR-36 clock (from the first other order this Uke); with no other order this Uke there is no insert time (FR-36). A Seat with Tilrettelegging never gets an insert time earlier than its own extended limit on that clock, agreed time or not. No Student can set or shorten an insert time. [ASSUMPTION: the FR-36 clock replaces the earlier "clock starts at the Pause"] |
| Before that | While a Pause runs or an agreed time is set, the row states the insert time, never why it is later for one Seat. Copy: State Patterns → Student game → Before the insert time. |
| Control | Consequence «KI-spilleren bestiller for Jonas fra denne Uka. Jonas kan ta setet tilbake fra neste Uke.» above the secondary button «Sett inn KI-spiller for Jonas». One press, no dialog: the step can be undone by a Reclaim. |
| After | Everyone sees the KI-spiller in the Seat, and the absent Student gets «Ta tilbake setet» and the requirement warning (FR-17). The Oversikt marks the Takeover with who triggered it, and it is audit-logged (FR-3). Copy, including a double press: State Patterns → Student game. |
| Status | Spine-only. |

### Game end and Debrief

| Component | Behavioural rules |
|---|---|
| Kjedens regning | Appears only after the game ends (FR-28). Rows go per Role, not per name, from Detaljist to Fabrikk, and the viewer's own row is marked «(deg)». The Debrief adds the «Simulert» rows. |
| Kjedens kostnad over tid | Shown on Spillet er ferdig and in the Debrief, only after the game ends (FR-28). Chain level, never per name. «Vis som tabell» opens Uke / Lager / Restordre / Sum for the chain in place. |
| Etterspørselsbånd | Debrief step 2 only, after the Forklaring is saved. Not interactive. The table Uke / Kundene / Ordre inn / Din ordre under it is its alternative. |
| Ordrestolper | Debrief step 3 and Spillinnsikt. They share columns with the Rolle × Uke numbers below. Not interactive beyond the Ukeskrubber. |
| Ukeskrubber | Spools the full chain to the chosen Uke by drag, step buttons or keys. See below. |
| Quizvalg | Single choice. On submit the wrong choice shows «Ditt svar, ikke riktig» and the right one «Riktig», followed by the explanation. Retry is unlimited until the Testfrist (FR-46). |
| Interaktiv oppgave | Individuell test (FR-80): a drawn answer backed by a value table. See below. |
| Flagg | KI-vurdering (FR-55). One press on «Marker som feil» flags that piece of feedback: «Markert. Faglærer ser det.», with «Angre». A toggle with `aria-pressed`. The flag reaches the Faglærer's Studentside. |

#### Ukeskrubber

| Rule | Behaviour |
|---|---|
| Spooling | Dragging, the step buttons or the keys spool the full chain to the chosen Uke («Kjeden i Uke 15. Dra i skrubberen for å spole.»). A dashed line marks the Uke across the bars. |
| Semantics | `role="slider"`, name «Velg uke», `aria-valuemin="1"`, `aria-valuemax` = the last Uke, `aria-valuetext="Uke 15"`. |
| Keys | Left/Down −1, Right/Up +1, PageDown/PageUp ±4, Home/End to the first and last Uke. |
| Step buttons | «Én uke tilbake» and «Én uke fram» at the ends, for anyone who cannot drag. |
| Result | After 300 ms without change, a polite live region reads the chain as text, Fabrikk first: «Uke 15. Fabrikk: restordre 3, ordre 22. Distributør: restordre 34, ordre 12. …». |
| Delt skjerm | The shared screen's scrubber is operated on that device; each phone keeps its own scrubber, not synced. [ASSUMPTION] |

#### Interaktiv oppgave

| Rule | Behaviour |
|---|---|
| Value table | Every drawing item is backed by a value table, one numeric cell per Uke. Drawing writes into the table and typing redraws the curve: they are one answer. |
| Pointer | Drag a point up or down, or tap a column to place its point. |
| Keyboard | Each point is a `role="slider"` named «Uke 3», `aria-valuetext` «Uke 3: 14 enheter»; Up/Down ±1 unit, PageUp/PageDown ±10 [ASSUMPTION], Tab moves to the next Uke's point and, after the last, into the table. |
| Screen reader | The table alone answers the item; the graph is a view of it. |
| Scoring | Scoring reads the table values only, so both input modes score the same. |
| Cells | Cells take whole numbers, with a leading minus where the quantity can be negative, and use the Ordrefelt error pattern («Skriv et helt tall.»). Every change autosaves. |
| Fyll inn kolonnen | «Fyll inn kolonnen» is the value table without a graph. |

### Faglærer

| Component | Behavioural rules |
|---|---|
| Matrisevegg | Rows grouped by status, with filters, «Melding» links and stable focus. See below. |
| Oppdater automatisk | A Bryter above the Matrisevegg, on by default (WCAG 2.2.2). See below. |
| Visningsbryter | «Vegg» / «Vis som tabell». It is always visible above the wall. The table lists all 60 games with a number in every cell at 13 px, is sortable and is read by screen readers. In «Vis i plenum» the same toggle offers the table, with games in game-number order, no names and no sorting by cost (FR-86). |
| Veggfiltre | Rolle, Celler and Status above the wall. Each filter is a toggle with `aria-pressed` and applies at once; the counts update with it. |
| Varselbånd | Shows the game closest to Takeover: «Spill 2 venter på Noah (Grossist) i 23 t. KI overtar om 1 t.» with «Send Melding» and «Pause spillet» (FR-39), and «Sett inn KI-spiller for Noah», the manual Takeover (FR-37), with its consequence line from Spillstyring. «Pause spillet» opens the Faglærer pause form of Spillstyring in place under the band; while it is open, «Send Melding» shows as secondary, so the screen keeps one primary. A paused game leaves the band at once, because no automatic Takeover runs while paused (FR-36); the band moves on to the next game. The Faglærer pause is a founder decision (2026-11-09) that extends FR-89, and only the Faglærer sets an agreed time (2026-11-10); PRD update in issue #25. An Assistent sees «Send Melding» and «Sett inn KI-spiller for Noah» only. Other waiting games are listed under «Venter ellers». |
| Meldingsskjema | Opens from «Melding» or «Send Melding» as its own page, with the recipient preset: one Student, one Klassespill or the whole Klasseøkt (FR-40), or every Student who has not met the obligatory requirement (FR-17, from the Lenke under the Trakt). Browser Back returns to where it was opened. One-way, no replies. «Send Melding» stays disabled while the text is empty, then sends in the product and by e-mail. Result: «Meldingen er sendt til 4 studenter.» |
| Filopplasting | Lag Klasse (FR-7). Takes .xlsx or .csv; the link «Lim inn adresser i stedet» opens a multi-line Tekstfelt. After reading, «E-postkolonne» is preselected with its reason; choosing another column re-reads the rows at once. «Bytt fil» returns to the empty state. Errors: see State Patterns → Faglærer setup → Lag Klasse. |
| Kostnadsfordeling | Read-only Faglærer chart. |
| Trakt | Read-only Faglærer chart. |
| Datolinje | Read-only Faglærer chart. |
| Fordelingsforhåndsvisning | Read-only Faglærer chart. Selecting a column shows that game's four names («Spill 17  Ida, Detaljist. Sara, Grossist. …»). «Kjør fordeling på nytt» redraws it. «Bekreft fordeling» commits it (FR-20). Beside the button: «Ingen får beskjed før du bekrefter.» |
| Spillstyring | The Faglærer's actions on Class games: start (FR-22), pause with an agreed time (FR-89 extension), «I rommet» with a shorter limit (FR-36) and manual Takeover (FR-37), for one game on Spillinnsikt and for all games from the Oversikt. See below. |
| Tilrettelegging | Studentside block: the per-Student Tilrettelegging of the Inactivity limit and the share (FR-17). Only ever extends. See below. |
| Fullføringsretting | Studentside block: the Completion status per step, its correction with a reason, and the Oppfølgingsspill (FR-17). See below. |

#### Matrisevegg

| Rule | Behaviour |
|---|---|
| Grouping | Rows group by status: Venter, Pause, Pågår, then «Ferdig, lavest kjedekost øverst». |
| Filters | Filters for Rolle, Celler (Netto lager / Ordre / Kost per uke) and Status (with counts) apply at once. |
| Row actions | A row's «Melding» link opens a Message to that game. [ASSUMPTION: clicking a row opens Spillinnsikt.] |
| Cells and legend | Cell text and the always-shown legend: `DESIGN.md` → Components → Matrisevegg. |
| Updates | Updates follow Oppdater automatisk. Keyboard focus stays on the same game, by game ID, across every re-render. |

#### Oppdater automatisk

| Rule | Behaviour |
|---|---|
| Default | A Bryter above the Matrisevegg, on by default (WCAG 2.2.2). |
| Off | The wall, the table, the rail and the headline counts stop changing; a line «3 endringer siden 14:02» with the secondary button «Oppdater» shows what is waiting. |
| On, while keyboard focus is inside the wall or the table | Rows do not move or re-sort; values update in place, and re-sorting waits until focus leaves. No update ever moves focus. |
| Announced (polite) | Only a new or changed Varselbånd and the headline counts, at most once a minute. |

#### Spillstyring

| Rule | Behaviour |
|---|---|
| Where | One game: a block on Spillinnsikt under the four Seats, with the per-Seat action on each Seat row. All games: two Lenker in the Oversikt header, «Start spill som ikke har startet (12)» and «Sett inn KI-spiller i alle seter som blir ventet på (9)», each opening its own page with the count, the consequence and one primary button; Back returns to the Oversikt. A Lenke with a count of 0 is not shown. |
| Who | Faglærer. An Assistent gets only the per-Seat «Sett inn KI-spiller for …» (FR-37); the other actions are not shown (State Patterns → Permission denied). [ASSUMPTION: the Assistent cannot pause, start or mark «I rommet»] |
| Start (FR-22) | From the Start date, on a game that has not started: primary «Start spillet» with «Spillet starter for alle fire. Reglene for ventetid gjelder fra nå.» above it. The all-games page lists the games and has the primary «Start 12 spill». Starting cannot be undone, so it is always the screen's primary button with its consequence above it. |
| Pause (FR-89 extension) | On a started, unfinished game that is not paused: secondary «Pause spillet» (here and in the Varselbånd). It opens in place: «Når fortsetter spillet?» with date and time from now to the Spillfrist, or the choice «Uten avtalt tid»; the lines «Mens spillet har pause, tar ingen KI-spiller over setene. Spillfristen flyttes ikke.» and «Etter avtalt tid kan studentene sette inn en KI-spiller for den som ikke har bestilt.»; primary «Ta pause til to. 19:00» (or «Ta pause uten avtalt tid»), and «Avbryt». A time outside the range shows «Velg et tidspunkt mellom nå og Spillfristen, {dato}.» in the Ordrefelt error pattern. On a paused game: secondary «Endre avtalt tid» (the same form, prefilled; it also sets a time on a pause a Student made) and secondary «Avslutt pausen» [ASSUMPTION]. |
| I rommet (FR-36) | Only while a Labtime of this Klasseøkt is on, on a started, unfinished game: secondary «Marker som i rommet». It opens in place: «Ventetid i rommet» in whole minutes [ASSUMPTION: default 10, from 2 to 120], the line «Studentene i spillet ser den kortere ventetiden. Den gjelder til Labtimen slutter kl. 16:00.», primary «Marker som i rommet, 10 min», and «Avbryt». Marked: the block reads «I rommet til 16:00. KI tar over etter 10 min uten ordre.» with secondary «Ikke i rommet lenger», and the game's wall row label carries «I rommet». The mark ends with the Labtime. Outside a Labtime the button is shown unavailable (`aria-disabled`) with «Kan bare brukes i en Labtime.» |
| Manual Takeover (FR-37) | Per Seat, on every Student-held Seat of a started, unfinished game: secondary «Sett inn KI-spiller for Jonas» with «KI-spilleren bestiller for Jonas fra denne Uka. Jonas kan ta setet tilbake fra neste Uke.» above it, or «KI-spilleren bestiller for Jonas fra neste Uke.» if Jonas has ordered this Uke. A Seat with Tilrettelegging adds «Jonas har tilrettelegging med mer tid.» to the Faglærer only. One press, no dialog: a Reclaim undoes it. |
| Fill waited-for Seats (FR-37) | "Absent" means a Seat the game waits for: its Student has not ordered this Uke while another Seat has. [ASSUMPTION: the product cannot know who is in the room] Per game: secondary «Sett inn KI-spiller i alle seter som blir ventet på (2)». All games: the Oversikt page lists the Seats per game and has the primary «Sett inn 9 KI-spillere». Seats with Tilrettelegging are left out and listed under «Ikke med (tilrettelegging): Jonas»; the per-Seat action still reaches them. Seats that order before the press are skipped, and the result gives the real count. [ASSUMPTION] |
| After | Students see the result as in State Patterns → Student game (Paused, I rommet, Own Seat taken over). The Oversikt marks each Takeover with who triggered it. Every Spillstyring action is audit-logged with actor, time and change (FR-3 covers Takeover by a person; [ASSUMPTION] for start, pause and «I rommet»). Copy: State Patterns → Faglærer live. |
| Focus, one form | Only one in-place form is open at a time, so the screen keeps one primary button. Focus: Accessibility Floor → Focus and order (in-place forms, removed controls, results). |
| Status | Spine-only. |

#### Tilrettelegging

| Rule | Behaviour |
|---|---|
| Where, who | A block on the Studentside, Faglærer only. [ASSUMPTION: Assistenter do not see it] |
| Idle | «Ingen tilrettelegging.» or the summary «Mer tid: 2 ×. Andel uker: 60 %.», with secondary «Endre tilrettelegging». |
| Form, in place | «Mer tid før KI tar over» as Valgknapper «Som klassen», «1,5 ×», «2 ×», «3 ×» [ASSUMPTION: these factors]. «Andel uker som kreves» as a whole percentage from 0 to the class share, help line «Klassen: 80 %.», error «Skriv et helt tall fra 0 til 80.». The line «Gjelder bare Jonas, fra nå. Ingen andre studenter ser det. Endringen logges.» Primary «Lagre tilrettelegging», and «Avbryt». There is no field for the reason, so no health data is stored. [ASSUMPTION] |
| What it extends | The factor multiplies every limit that governs the Seat: the Klasseøkt's Inactivity limit, the «I rommet» limit (the only timed sitting in v1 [ASSUMPTION]), and the floor under a Faglærer's agreed pause time (Sett inn KI-spiller → Insert time). It also applies to automatic Takeover and to the Varselbånd's «KI overtar om …». It can never shorten anything. |
| Timing | Changeable at any time, also after the Start date; a running clock is recomputed at once. [ASSUMPTION] |
| Student's own view | Hjem shows, under Stegene and only to that Student: «Du har mer tid før en KI-spiller tar setet ditt (2 × vanlig ventetid).» and, if the share is adjusted, «For deg er kravet 60 % av ukene.» In «I rommet» the Student's own line shows their own minutes. Mine data lists it. The other Students only ever see a later insert time. |
| Status | Spine-only. FR-17 names the adjustment; the factors, the floor rule and the screen are this spine's (issue #25). |

#### Fullføringsretting

| Rule | Behaviour |
|---|---|
| Rows | One row per step (Klassespill, Debrief, Debrief-quiz, Replay, Individuell test) with its status in text, «gjort» or «ikke gjort». The Klassespill row adds the share: «Bestilte i 70 % av ukene. Kravet er 80 %.» and, where it applies, «20 % av ukene ble spilt i utspillingen ved Spillfristen.» so the Faglærer can see who fell short because of the playout or the group's pace (FR-17). The requirement line shows only when the Klasseøkt is Obligatorisk. |
| Correct | Secondary «Rett Klassespill» (and so on per step) opens in place: Valgknapper «Gjort» / «Ikke gjort», the Tekstfelt «Begrunnelse» (required; empty gives «Skriv en begrunnelse.»), the line «Rettingen logges med navnet ditt, tidspunktet og begrunnelsen.», primary «Lagre retting», and «Avbryt». After: «Gjort, rettet av Bård 12. des.» with the reason under it. Audit-logged (FR-3). The Student sees the new status in Stegene, marked «rettet av faglærer», not the reason. [ASSUMPTION] |
| Oppfølgingsspill | Until the Testfrist: secondary «Gi oppfølgingsspill» in the Klassespill row. It opens in place: «Jonas får et eget Klassespill mot tre KI-spillere, åpent til Testfristen fr. 18. des. Jonas får beskjed på Hjem og på e-post.», primary «Gi oppfølgingsspill», and «Avbryt». After: «Oppfølgingsspill gitt 12. des. Åpent til fr. 18. des.» The Student's Hjem shows it as a Spillkort titled «Oppfølgingsspill»; it reuses Spill and ends in a Personal debrief. [ASSUMPTION] |
| One panel | Only one in-place form is open at a time on the Studentside, so the screen keeps one primary button. Opening another closes the first and keeps nothing. [ASSUMPTION] |
| Message those not met | On the Oversikt, under the Trakt, when the Klasseøkt is Obligatorisk: the Lenke «Send Melding til 12 som ikke har oppfylt kravet» opens the Meldingsskjema with those Students preset (FR-17, FR-40). |
| Status | Spine-only. |

### System

| Component | Behavioural rules |
|---|---|
| Tilkoblingslinje | Appears at the top of the content when the device is offline, when live data is stale, or when a page fails. It says what still works and what to do. A polite status region; it never covers controls. When resolved it reads «Tilkoblet igjen.» for 5 s, then disappears. |
| Skjelett | Shown while a page loads, in the real layout and columns. Numbers appear all at once when ready. «Laster …» appears only after 1 s; after 10 s the page shows the page-error state. [ASSUMPTION: 10 s] |
| KI-merke | Present wherever a Seat or AI text appears (see AI disclosure). Never removable. |
| Demodata-merke | Present on every surface that shows synthetic data (see Demo/synthetic data labelling). |

## State Patterns

Rows marked spine-only have no mockup. Copy in «» is the UI string; where a row says [ASSUMPTION] the copy is a draft.

### All surfaces

| Surface | State | Treatment |
|---|---|---|
| All | Loading | Skjelett in the real layout. No spinners. «Laster …» only after 1 s. The budget is 3 s on 4G (NFR-1). |
| All | Offline | Tilkoblingslinje: «Frakoblet. Det du har skrevet, er tatt vare på på denne enheten.» Live values carry «Sist oppdatert 21:14». Nothing is sent on its own when the connection returns. |
| All | Reconnected | «Tilkoblet igjen.» for 5 s, then the page refreshes its data in place without moving focus (NFR-5). |
| All | Page error | Tilkoblingslinje: «Siden kunne ikke lastes.» with «Prøv igjen». Anything typed stays in its field. |
| All | Action error | Inline beside the action that failed: «Det ble ikke lagret. Prøv igjen.» with the button still enabled and the input kept. Never a silent failure. Announced with `role="alert"`; focus stays on the action's button (Accessibility Floor → Order and action results). |
| All | Permission denied (FR-5) | «Du har ikke tilgang til denne siden.» and a link to the user's own home («Til Hjem» or «Til Lærerhjem»). The page never says whether the page or item exists. Actions a role lacks (an Assistent creating or deleting a Klasse or Klasseøkt) are not shown at all. |
| All | Session expired | «Du er logget ut. Logg inn igjen for å fortsette.» Logging in returns to the same page with a typed order or answer kept. |
| All | Not found | «Fant ikke siden.» with a link home. |

### Account and access

| Surface | State | Treatment |
|---|---|---|
| Landing | Static | Seat chart in a Veiledet uke with «Demodata». It shows only one Seat. It shows no stock curves for the class («Lagerkurvene for hele klassen ser du først når du er logget inn.»), no rising Ordre inn, no amplification, no customers, quotes, prices or learning claims (§6.2), and no week counts (see Hidden information). «Be om lærertilgang» leads to a request. [ASSUMPTION: a short form reviewed by the Admin; not drawn] |
| Logg inn | Wrong e-mail or password | «Feil e-post eller passord.» The page does not say which one, or whether an account exists. |
| Logg inn | Deactivated user (FR-3) | «Kontoen er deaktivert. Ta kontakt med faglæreren din.» |
| Glemt passord | Sent | «Hvis adressen har en konto, har vi sendt en lenke. Lenken virker i én time.» [ASSUMPTION: one hour] Spine-only. |
| Nytt passord | Link expired or used | «Lenken er utløpt eller brukt.» with «Send ny lenke». Spine-only. |
| Nytt passord | Done | «Passordet er endret.» then Logg inn with the e-mail prefilled. Spine-only. |
| Du er invitert | Valid | «Invitasjonen er gyldig i 14 dager. Du får Rolle og spill når Faglærer har bekreftet fordelingen.» |
| Du er invitert | Expired or used link | A message plus a way to ask for a new Invitasjon (FR-1). [ASSUMPTION: copy to be written] |
| Mine data | Open (FR-75) | One row per category (konto og profil, ordrer, Forklaring, refleksjonssvar, Debrief-quiz, testsvar, KI-vurdering, veiledende bokstav, tilrettelegging if any), each with «Vis». «Last ned Studentrapport» at the top. Spine-only. |

### Student game

| Surface | State | Treatment |
|---|---|---|
| Hjem | Before allocation | No game card. The line «Du får Rolle og spill når Faglærer har bekreftet fordelingen.» Stegene greyed out. |
| Hjem | Spillet venter på deg | The card «Spillet venter på deg», Uke 11, mini graph over table, «Totalkostnad 68,00 kr», «Gå til Uke 11» (FR-25) |
| Hjem | Waiting for others | [ASSUMPTION: the same card with Setestatus and no primary action] |
| Velg spill og sete | Open (FR-21) | A list of Klassespill, each with its four Seats as «Grossist, ledig» or the name. Pressing a free Seat shows «Ta setet Grossist i Spill 17» as the primary button. One Seat per Klasseøkt; choosing another releases the first. Spine-only. |
| Velg spill og sete | Seat taken meanwhile | «Setet ble tatt av en annen. Velg et annet.» with the list refreshed. Spine-only. |
| Velg spill og sete | Start date passed without a choice | «Du fikk et sete ved trekning: Grossist i Spill 17.» Spine-only. |
| Startoppgave | Wrong answer | «Ikke riktig. Svaret er 3: 0 − 13 + 16.» The sum is shown in the same column. The Student goes on; nothing counts (FR-85). |
| Startoppgave | Right answer | «Riktig.» with the same sum. |
| Startoppgave | Final question | «Har du spilt et spill som ligner dette før?» with «Ja», «Nei», «Vet ikke» and «Hopp over». It never names the game (FR-84). |
| Startoppgave | Done | «Ferdig. Gå til Uke 1.» |
| Spill | Veiledet uke (1–4) | The order is fixed at 4 and placed automatically. The Uke advances when all Students have opened it (FR-24). The landing shows this state: «Ett sete, Grossist, Uke 4. Veiledet uke.» |
| Spill | Uka åpner | A new column with Levering and Ordre inn already filled, and Netto lager and Posisjon for nå. The Din ordre cell is empty and dashed (`06` A). |
| Spill | Typed | The value shows in two cells, the band shows «På vei 16 + 24», the button reads «Bekreft ordre på 24» (`06` B) |
| Spill | Typed, invalid or out of range | Error border and «Skriv et helt tall fra 0 til {maks}.»; «Bekreft ordre» disabled. See Ordrefelt. |
| Spill | Submitting | The button reads «Sender ordre på 24 …» and is unavailable: it keeps focus with `aria-disabled="true"` and `aria-busy="true"`, never the native `disabled`, and further presses are ignored. The field is read-only. Announcements and focus for this and the next four rows: Accessibility Floor → Order and action results. |
| Spill | Confirmed | «Ordren på 24 er sendt. Venter på Jonas.», Setestatus, «Du får beskjed når Uke 12 åpner.» (`06` C, FR-27) |
| Spill | Submit failed | «Ordren ble ikke sendt. Ingenting er bestilt ennå.» The field keeps 24 and stays editable; the primary button reads «Prøv å sende 24 igjen». A retry can never create a second order. [ASSUMPTION: the server ignores a repeat of the same request] |
| Spill | Timed out | No answer after 10 s [ASSUMPTION]: «Vi vet ikke om ordren kom fram. Sjekker …». The app asks the server: if the order is there, it shows Confirmed; if not, Submit failed. The order is never locked silently. |
| Spill | Offline with a typed order | Tilkoblingslinje plus «Ordren på 24 er ikke sendt.» The value stays in the field. When the connection returns: «Tilkoblet igjen. Ordren er ikke sendt ennå.» and the normal «Bekreft ordre på 24». It is never sent without a press. |
| Spill | Uke advanced | Uke-overgang (`06` D) |
| Spill | Paused | All four Seats see the pause line above Setestatus, on Spill and Hjem, announced politely (FR-89): «Pause, satt av Sara.» when a Student paused; «Pause, satt av faglæreren.» or «Pause til to. 19:00, satt av faglæreren.» when the Faglærer paused or set the time. Only the Faglærer's pause line carries a time. Nothing in it hints at how many Uker remain (FR-14). The Oversikt shows the game as paused, since when and by whom. See Pausevalg and Spillstyring. |
| Spill | Pause ended | Any Student ends the pause by ordering (FR-89); the line becomes «Pausen er over. Sara har bestilt.» |
| Spill | Before the insert time (paused, or an agreed time set) | With an agreed time, the absent Seat's row reads «Avtalt tid to. 19:00. Etter det kan dere sette inn en KI-spiller.» Without one, once the FR-36 clock runs: «Etter on. 10:00 kan dere sette inn en KI-spiller.», the Seat's own insert time. |
| Spill | Insert time passed | The other Students see Sett inn KI-spiller on the absent Seat's row, paused or not, until that Seat orders, a Takeover happens or the Uke advances (Sett inn KI-spiller → Shown). |
| Spill | I rommet (FR-36) | All four see «I rommet til kl. 16:00. En KI-spiller tar setet etter 10 min uten ordre.» above Setestatus, announced politely when it starts and when it ends. Each Student's line shows that Student's own minutes (Tilrettelegging). |
| Hjem | Tilrettelegging (FR-17) | Only the Student concerned sees «Du har mer tid før en KI-spiller tar setet ditt (2 × vanlig ventetid).» under Stegene, and «For deg er kravet 60 % av ukene.» if the share is adjusted. |
| Spill | AI put into an absent Seat | Everyone sees the row «Fabrikk  KI-spiller  bestiller for Jonas» (`06` E, FR-37). |
| Spill | AI put in by two at once | If two Students press at once, the second sees «Sara har allerede satt inn en KI-spiller.» |
| Spill | Own Seat taken over | «KI-spiller har bestilt for deg.» with «Ta tilbake setet». Reclaim takes effect when the next Uke opens (FR-37). The warning about the obligatory requirement must not reveal the number of Uker (FR-17). |
| Spill | Ended by playout | «Spillet er ferdig» with a note that it ended at the Spillfrist (FR-38). In the playout, KI-spillere play every unfinished Klassespill to its last Uke at the Spillfrist. [ASSUMPTION: copy to be written] |
| Spill | Reload or new device | Resumes at the current Uke with nothing lost (FR-26, NFR-5) |
| Spill | Waiting for an AI player | Setestatus shows the KI-spiller row as «venter». The wait is bounded by NFR-2. [ASSUMPTION: no spinner copy beyond that] |

### After the game

| Surface | State | Treatment |
|---|---|---|
| Spillet er ferdig | End | «Kjedens totalkostnad», then «2 266,00 kr», then «Fire Roller, to kostnadsarter, hele spillet.», then Kjedens regning, «Kjedens kostnad over tid», «Hvorfor ble den slik? Det finner dere ut i Debriefen, med alle fire Rollene.», «Gå til Debrief» |
| Debrief | Forklaring not sent | The reveal is locked: «Avsløringen er låst til alle fire har sendt. Ida og Mikkel har sendt, Jonas skriver.» A late joiner writes the Forklaring first (FR-43). |
| Debrief | Group has not met within 48 h, or the Student has dropped out of the group | Continue as a Personal debrief from the same step (FR-43) |
| Debrief | LLM rejected or provider down | The same content from code, without AI text (FR-44) |
| Debrief | Student with < 10 own orders | Shows the game as played mostly by AI players and takes moments from the Replay (FR-44) |
| Quiz | Wrong / right | See Quizvalg. The explanation names the column: «Det står i kolonne 11 i din egen tabell.» |
| Replay | Locked | In Stegene: «Replay, åpnes når du har bestått Debrief-quizen.» (FR-48) |
| Replay | In progress | Hjem and Stegene: «Fortsett Replay, Uke 9.» Same screen as the Spill, with the projection. Waiting is only for KI-spillere (NFR-2). |
| Replay | Finished | «Replay er ferdig», Totalkostnad, then «Gå til gjennomgangen». |
| Replay-gjennomgang | Pending | «Gjennomgangen lages.» in a Skjelett of the chart. [ASSUMPTION: under one minute] |
| Replay-gjennomgang | LLM rejected or provider down | The same chart and numbers from code, without AI text (FR-50 under FR-44 rules). |
| Alle spill side om side | Locked (FR-86) | In Stegene: «Åpnes når Debriefen din er ferdig og Spillfristen er passert.» |

### Test and assessment

| Surface | State | Treatment |
|---|---|---|
| Individuell test | Locked | In Stegene: «Individuell test, åpnes når du har fullført Replay.» (FR-51) |
| Individuell test | Open | First the own-work statement (FR-51), then the items. «Lagret 21:14» after each autosave (polite). |
| Individuell test | Autosave failed | «Ikke lagret. Svarene ligger på denne enheten, og vi prøver igjen.» The Student can keep working. |
| Individuell test | Review before submit | «Lever testen» opens a review: «3 oppgaver er ikke besvart: 4, 7 og 9.», each a link to its item, and «Du kan ikke endre svarene etter at du har levert.» over the primary «Lever testen». |
| Individuell test | Submitted | «Levert to. 18. des kl. 21:40. Du kan ikke endre svarene.» |
| Individuell test | Auto-submitted at the Testfrist | «Testfristen er passert. Svarene dine ble levert automatisk.» (FR-51) |
| Individuell test | Testfrist passed, never opened | «Testfristen er passert. Testen er ikke levert.» The step stays «ikke gjort». |
| KI-vurdering | Not ready | «KI-vurderingen kommer innen ett døgn etter testfristen.» (FR-54) |
| KI-vurdering | Ready / feedback dropped | The Student gets an e-mail and can open the KI-vurdering. «Teller ikke. Ingen karakter.» A note appears where feedback was left out (FR-54) |
| KI-vurdering | Switched off (FR-61) | «Faglærer har slått av KI-vurdering for denne Klasseøkten. Studentrapporten finnes som vanlig.» |

### Faglærer setup

| Surface | State | Treatment |
|---|---|---|
| Lærerhjem | Empty (new Faglærer) | No Klasser yet, so «Ny Klasse» is the only action (UJ-1) |
| Lag Klasse | File read | «250 rader lest», «Bytt fil», «Valgt fordi alle rader unntatt fire ser ut som adresser.» |
| Lag Klasse | Unreadable file | «Filen kunne ikke leses. Bruk .xlsx eller .csv, eller lim inn adressene.» |
| Lag Klasse | Invalid rows | «Ugyldige rader: 4 av 250», reason per row. «Send 246 Invitasjoner». «Ugyldige rader får ingen e-post før de er rettet.» |
| Lag Klasse | After sending | «Status etter utsending»: Registrert 238, Manuelt 2, Uregistrert 10, «Send påminnelse til 10» |
| Faglærere og assistenter | List (FR-10) | Faglærere (co-owners) and Assistenter for this Klasse, each with status. «Inviter Assistent» takes an e-mail; «Legg til Faglærer» takes an existing user's e-mail. «Assistenten får tilgang bare til denne Klassen.» Spine-only. |
| Klasseøkt | Defaults | «Alt er fylt ut med standardene.», «Kildene er uenige om forsinkelsene. Dette er produktets standard, og du kan endre den.» |
| Klasseøkt | Out of range or warning | Rejected with the allowed range shown. Warnings do not block (FR-12). [ASSUMPTION: shown inline under the setting] |
| Klasseøkt | After Start date | Game settings are read-only (FR-12) |
| Klasseøkt | «Ventetid før KI tar over» (FR-36) | Whole hours, default 24, never under 20. [ASSUMPTION: floor 20 h, so the WCAG 2.2.1 20-hour exception holds for every Student; the PRD sets no minimum, and SM-C5's lowering stays within it.] Help line «Minst 20 timer. Kortere ventetid kan bare gjelde spill som er i rommet i en Labtime.» Under 20: «Skriv et helt antall timer, 20 eller mer.» in the Ordrefelt error pattern. Locked at the Start date (FR-18). Shorter limits exist only through «I rommet», where the Students sit in a scheduled Labtime and see the limit on screen, and through a Faglærer's agreed pause time; in both, a Student with Tilrettelegging keeps the extended limit (Tilrettelegging → What it extends). [ASSUMPTION: an accessibility review confirms this for «I rommet»] |
| Innsatsnivå | Choosing (FR-78) | Valgknapper with only the offered levels, each with its effect on speed and cost in one line. Hidden when regelbaserte KI-spillere are chosen. Locked at the Start date. Spine-only. |
| Spørsmål og vekter | Editing (FR-52) | A list of questions with Vekt in % and «Ta ut». The sum shows live; «Sum 95 %. Vektene må bli 100 %.» blocks saving. Removing a quantity item warns without blocking: «Du tar ut en oppgave som måler mengder.» Locked at the Start date. Spine-only. |
| Sensorveiledning | Editing (FR-81) | One Tekstfelt per question, marked «Standard» or «Endret». An edited guide shows «Ikke kontrollert med en Kontrolltest.» to the Faglærer and in the feedback. Locked at the Testfrist. Spine-only. |
| KI-vurdering (setting) | Off (FR-61) | Bryter «KI-vurdering» with the help text «Flervalg og interaktive oppgaver rettes fortsatt automatisk. Studentrapporten finnes som vanlig.» Locked at the Testfrist. Spine-only. |
| Eksport | Ready to download | Three actions: «Last ned alle Studentrapporter (ZIP)», «Last ned fullføringsliste (CSV eller Excel)», «Last ned spilldata (CSV)». Notes: «ZIP-filen har aldri med KI-vurderingen.» «Ingen av filene har KI-vurderinger.» Spine-only. |
| Eksport | ZIP being made | «ZIP-filen lages. Du får beskjed når den er klar, innen 10 minutter.» (FR-59). Failure: «ZIP-filen kunne ikke lages.» with «Prøv igjen». Spine-only. |

### Faglærer live

| Surface | State | Treatment |
|---|---|---|
| Oversikt | Live | Updates within 5 s without reload (FR-39). Headline counts read «41 ferdig · 15 pågår (herav 2 pauset) · 4 venter». «Oppdatert 14:02:15» in `{typography.caption}`. |
| Oversikt | Connection lost or stale | No update for 15 s [ASSUMPTION]: Tilkoblingslinje «Ikke oppdatert siden 14:02. Prøver igjen.» with «Last inn på nytt». The wall keeps the last values; nothing is greyed out. |
| Oversikt | Updates paused | Oppdater automatisk is off: «3 endringer siden 14:02» with «Oppdater». |
| Oversikt | Before the Start date | [ASSUMPTION: the wall is empty and lists the allocation, with no cost rail] |
| Spillinnsikt | Not started | «Spillet har ikke startet.» with the four Seats. From the Start date, Spillstyring offers the primary «Start spillet». |
| Spillinnsikt | Running | Spillstyring: «Pause spillet», «Marker som i rommet» (or unavailable with «Kan bare brukes i en Labtime.»), «Sett inn KI-spiller i alle seter som blir ventet på (2)», and «Sett inn KI-spiller for …» on each Student-held Seat. Spine-only. |
| Spillinnsikt | Paused | «Pause siden ma. 14:10, satt av Sara.» or «… satt av deg.», with the agreed time if any, then «Endre avtalt tid» and «Avslutt pausen». [ASSUMPTION: copy] Spine-only. |
| Spillinnsikt | I rommet | «I rommet til 16:00. KI tar over etter 10 min uten ordre.» with «Ikke i rommet lenger». Spine-only. |
| Spillinnsikt | Finished | No Spillstyring actions. |
| Spillinnsikt | Action done | The result replaces the form: «Spillet er startet.», «Pause til to. 19:00 er satt.», «I rommet til 16:00.», «KI-spiller satt inn for Jonas.», «2 KI-spillere satt inn.» [ASSUMPTION: copy] Spine-only. |
| Oversikt | «Start spill» page (FR-22) | A list of the games not started, the line «Spillene starter for alle i dem. Reglene for ventetid gjelder fra nå.», primary «Start 12 spill». Result on the Oversikt: «12 spill er startet.» Not offered before the Start date. Spine-only. |
| Oversikt | «Sett inn KI-spillere» page (FR-37) | The Seats per game with name and wait («Spill 2: Noah, 23 t»), «Ikke med (tilrettelegging): Jonas», the line «Studentene kan ta setene tilbake fra neste Uke.», primary «Sett inn 9 KI-spillere». Result: «9 KI-spillere er satt inn.» Spine-only. |
| Studentside | Steps not done | Each step not done reads «ikke gjort» in text, not only a hollow dot. |
| Studentside | Tilrettelegging | None: «Ingen tilrettelegging.» Saved: «Lagret. Gjelder fra nå.» and the summary. See Tilrettelegging. Spine-only. |
| Studentside | Fullføring | Met, not met with the share line, corrected («Gjort, rettet av Bård 12. des.»), Oppfølgingsspill given. See Fullføringsretting. Spine-only. |
| Klasserapport | Empty or partial | «Ingen spill er ferdige ennå.» Partial: «Oppdateres etter hvert som studentene blir ferdige. 41 av 60 spill er med.» (FR-64) |
| Tverrklasse-statistikk | No earlier Klasseøkt | «Du har ingen tidligere Klasseøkter å sammenligne med.» |

### Admin

| Surface | State | Treatment |
|---|---|---|
| Admin-område | Revoke blocked (FR-2) | «Bård eier 2 Klasser. Legg til en annen Faglærer eller arkiver Klassene først.» |
| Admin-område | Search empty, deactivate | «Ingen treff.» The deactivate button states the consequence: «Deaktiver Bård. Bård kan ikke logge inn, og dataene blir værende.» |
| Admin-område | KI-kostnad limit reached (FR-69) | «Grensen er nådd for class-of-1994. LLM-spillerne er byttet til regelbaserte.» |
| Kontrolltest | Setup and results (FR-82) | Test students are listed with «Teststudent». Results show human and AI scores side by side: exact agreement, within one step, offset, scale compression, agreement by answer length. «Teller aldri med i en Klasseøkt.» Spine-only. |

## Interaction Primitives

- **One decision per Uke:** one whole number, entered in the order input and confirmed with one tap. Everything else is reading.
- On phone, a numeric keypad (`inputmode="numeric"`), − and +. On laptop, the Student types the number, and Enter moves focus to «Bekreft ordre på 24»; only the button confirms. Enter never submits an order from the field.
- **One tap to depth:** «Alle rader og kostnad», the Totalkostnad figure, «Kostnad så langt» and «Hopp over».
- Drag, step buttons or keys on the Ukeskrubber (Debrief only).
- Drag or keys on an Interaktiv oppgave, always with the value table beside it.
- Toggle «Vegg / Vis som tabell», filters, and the «Melding» links (Faglærer).
- Week-advance animation is skippable and never over 2 s.
- **Banned:**
  - a recommended order or «fasit» (rejected, memlog)
  - chat between players (FR-40) (rejected, memlog)
  - any Student-facing ranking or prize (rejected, memlog)
  - progress toward the end of the game
  - confirmation dialogs after the button already states the consequence
  - celebration animation
  - pull-to-refresh as the only way to update (views are live)

## Accessibility Floor

Behavioural. Contrast and type floors live in `DESIGN.md`.

- **Standard:** WCAG 2.1 AA on Student and Faglærer screens (NFR-6).
- **Charts:** every chart has a text or table alternative, listed here. A chart whose alternative is a visible table on the same columns needs nothing more; every other chart is `aria-hidden` and points to its alternative.

| Chart | Alternative |
|---|---|
| Graf over tabell: Netto lager, Posisjon line, Kost per uke (`net-graph`, `cost-field`) | The week table on the same columns, a number under every mark |
| Kjedebånd | Reads as text (see Screen readers) |
| Totalkostnad over tid (`cost-panel`) | Phone: the «Sum, kr» row in Alle rader. Laptop: «Vis som tabell» under the chart (Uke, Lager, Restordre, Sum, kr) |
| Kjedens kostnad over tid | «Vis som tabell» (Uke, Lager, Restordre, Sum for the chain) |
| Kjedens regning split bars | The Lager / Restordre / Sum numbers in the same row |
| Ordrestolper | The Rolle × Uke numbers in the same columns, plus Forsterkning as text |
| Ukeskrubber chain view | The live-region text of the chain at the chosen Uke |
| Debrief step 1 strip «Ditt netto lager, hele spillet» | «Vis som tabell» (Uke, Netto lager) |
| Etterspørselsbånd | The table Uke / Kundene / Ordre inn / Din ordre under it |
| Delt skjerm «Kostnad, kr» per Role, and «Snitt per ferdig spill, per Rolle» | Lager and Restordre numbers printed beside each Role total, not only the total |
| Matrisevegg | «Vis som tabell» (13 px, a number in every cell). In «Vis i plenum»: the caption in words, the legend, and the same table offer |
| Kostnadsfordeling («Klassens kostnad») | A text summary under it («Median 1 954. Midterste halvdel 1 500–2 600. Fjoråret 2 740.») and «Vis som tabell» (Spill, kjedekost, sorted) |
| Trakt | Its counts are printed; the bars are `aria-hidden` and the counts form a list |
| Datolinje | The labelled date fields and the list of Labtimer it is drawn from |
| Fordelingsforhåndsvisning | «Vis som liste»: every Klassespill with its four names |
| Spillkort mini graph | `aria-hidden`, with the card text «Netto lager −13 i Uke 11.» |
| Interaktiv oppgave | The value table |
| Spillinnsikt, Klasserapport, Tverrklasse-statistikk charts | «Vis som tabell» under each |
| PDF Studentrapport | Tagged, with a table under every chart (NFR-6) |

- **Never colour alone:**
  - Netto lager cells print signed numbers; Matrisevegg cells print the number or a «−».
  - Netto lager and Posisjon lines differ in fill, stroke, marker and label.
  - Seat state is dot shape plus text.
  - Wrong quiz answers and invalid input carry text.
  - Invalid rows carry a reason.
  - AI is the word «KI-spiller».
- **Live announcements** (`aria-live` polite unless marked): «Venter på: …», the Uke advance («Uke 11 er ferdig regnet»), Takeover, the reveal unlocking, Pause set and ended, «I rommet» starting and ending, «Tilkoblet igjen.», the Ukeskrubber result, the Oversikt rules under Oppdater automatisk, Ordrefelt errors (`role="alert"`, on leaving the field or pressing the button), and the order and action results below.
- **Order and action results** (WCAG 4.1.3, 3.3.1, 2.4.3). A message that receives focus is read on focus and is not also a live region, so it is read once.

| State | Announcement | Focus |
|---|---|---|
| Submitting | Polite: «Sender ordre på 24 …» | Stays on the button: `aria-disabled="true"`, `aria-busy="true"`, never the native `disabled` |
| Confirmed | Read on focus | Moves to the waiting message «Ordren på 24 er sendt. Venter på Jonas.» (`tabindex="-1"`) |
| Submit failed | Assertive, `role="alert"`: «Ordren ble ikke sendt. Ingenting er bestilt ennå.» | Stays on the button, now active again as «Prøv å sende 24 igjen» |
| Timed out | Polite: «Vi vet ikke om ordren kom fram. Sjekker …»; then as Confirmed or as Submit failed | Stays on the button until the answer |
| Offline with a typed order | Polite: «Ordren på 24 er ikke sendt.»; on return, polite: «Tilkoblet igjen. Ordren er ikke sendt ennå.» | Does not move |
| Action error (all surfaces) | Assertive, `role="alert"` on the inline «Det ble ikke lagret. Prøv igjen.» | Stays on the action's button, which stays active |
| Session expired | Read on focus | The Logg inn page opens with focus on «Du er logget ut. Logg inn igjen for å fortsette.» |
| Seat taken (Velg spill og sete) | Read on focus | Moves to «Setet ble tatt av en annen. Velg et annet.» (`tabindex="-1"`) above the refreshed list |
| KI-spiller put in by two at once | Read on focus | The pressed button is gone; focus moves to «Sara har allerede satt inn en KI-spiller.» on that Setestatus row (`tabindex="-1"`) |
| Sett inn KI-spiller done (Student or Faglærer) | Read on focus | The button is replaced by the KI-spiller row; focus moves to that row's text (`tabindex="-1"`) |
| Spillstyring, Tilrettelegging, Fullføringsretting saved | Read on focus | Moves to the result line that replaces the form |

- **Focus and order:**
  - Focus is always visible: `{components.focus-ring.color}` ring with a `paper` gap (`DESIGN.md` → Components → Interaction states). Never `outline: none` without it.
  - Focus order follows reading order: header, chain band, graph/table, order input, confirm.
  - After confirming, focus moves to the waiting message.
  - A control that becomes unavailable while it has focus never gets the native `disabled`: it takes `aria-disabled="true"`, keeps focus and ignores presses. This covers «Bekreft ordre» while submitting, and − at 0 and + at {maks}.
  - An in-place form (Pausevalg, Spillstyring, Tilrettelegging, Fullføringsretting) moves focus to its first field, or to its primary button when it has no field; «Avbryt» returns focus to the control that opened it.
  - The Alle rader screen returns focus to the link that opened it.
  - Live updates (Oversikt, Setestatus, Matrisevegg) never move focus.
- **Screen readers:**
  - The chain band reads as text: «Ordre inn 8, Levering 4, Sendt 4, Restordre 13, På vei 16 pluss 24».
  - Each table column reads with the Uke as its header.
- Reduced motion: no week-advance animation, and the result shows at once.
- Tap targets at least `{spacing.tap-target-min}` on phone for every control (the 38 px «Ta tilbake setet» in `06` E: see `DESIGN.md` → Mockup deviations).
- **Keyboard (FR-80):** the Ukeskrubber (slider keys and step buttons), quiz, Forklaring and every Interaktiv oppgave (point sliders plus the value table) are fully keyboard-operable. No task needs a drag or a drawn path.
- **Reflow:** every Student flow works at 320 CSS px (WCAG 1.4.10) and at 360 px with 200 % text, without page-level horizontal scroll. 360 px is the design target. Only the components on the two-dimensional list in `DESIGN.md` → Layout & Spacing scroll sideways, each inside its own region; Graf over tabell keeps graph and table on one scroll position with sticky labels, and its text never shrinks below 13 px.
- **Reflow, Faglærer and Admin (NFR-6):** every Faglærer and Admin surface works at 320 CSS px (1280 px at 400 % zoom) and with 200 % text (WCAG 1.4.4), without page-level horizontal scroll; the laptop stays the design target (Responsive & Platform). At that width the Varselbånd's actions wrap under its text and stay in view, the right rail stacks under the wall, and forms are one column. The Matrisevegg, its median graph and its table view share one scroll region (`role="region"`, name «Alle spill», `tabindex="0"`) with the game column and the Uke header sticky; the table keeps its 13 px text and is the reading path at that width. Datolinje, Fordelingsforhåndsvisning and the Rolle × Uke and report tables scroll in their own regions, and their listed alternatives (Charts above) reflow.

## Hidden information and help level

| What | Klassespill | After the game (Debrief, Replay) |
|---|---|---|
| Number of Uker / end | Never shown. The axis stops at nå + 4. The current Uke number is shown (FR-14) | The Debrief scrubber shows «Uke 1 … Uke 36». In the Replay the number of Uker stays hidden (FR-49) |
| Customer demand | Detaljist only, one Uke at a time | Revealed in Debrief step 2, after the Forklaring |
| Other Seats' numbers | Hidden, unless Information visibility is on (FR-83) [ASSUMPTION: neighbour numbers appear in the chain band at the neighbour end, labelled with Role and Uke; not drawn] | Full chain in the Debrief |
| Netto lager, På vei | Separate rows (På vei on laptop and in Alle rader; on phone På vei is in the Kjedebånd) | Same |
| Posisjon (row and line) | Shown: Posisjon = Lager − Restordre + På vei, as a row in the table and a line in the graph (founder decision 2026-11-09, supersedes stance 1 of issue #22) | Same in the Replay. Shown in the Debrief («Posisjon 0 − 13 + 16 = 3. Med 24 ble den 27.») |
| Known arrivals | Levering boxes at nå+1 to nå+4 on `{colors.future-tint}`, marked as ordered, not guaranteed (stance 3). In Uke 15 only 17 of the 24 arrived | Same |
| Projection | Not shown | Replay only: «Den stiplede linja viser netto lager om fire uker: 3 + 24 − 4 × 8 = −5 hvis ordre inn holder seg. Ikke garantert.» [ASSUMPTION: the projection still unlocks only in the Replay] |
| Cost | Own Totalkostnad, Kost per uke, «Kostnad så langt» with the week's sum (stance 2: one tap away on phone) | Kjedens regning, Simulert |
| Recommended order | Never | Never. Simulert is «sammenhengen, ikke en fasit» |

**Week counts outside the game.** The landing shows no week counts. Faglærer progress is shown as the share of games finished and their status, never as «Uker spilt» or any number that hints at game length (FR-14).

The mockups predate the Posisjon decision; see `DESIGN.md` → Mockup deviations.

## Cost picture

- **Rates.** Restordre costs 1,00 and Lager 0,50 per unit per Uke, charged on end-of-Uke balances (FR-26). Displayed as «restordre 1,00 / lager 0,50» in the Kost per uke key.

| Phase | Shown | Never |
|---|---|---|
| During play (own Seat only) | Totalkostnad in the header. The Kost per uke field and «Kost, kr» row in Graf over tabell. «Kostnad så langt»: Lagerkostnad 43,00 + Restordrekostnad 25,00 = Totalkostnad 68,00, then Totalkostnad over tid, then «Denne uka: 13 restordre × 1,00 = 13,00 kr», pinned beside the order on laptop and one tap away on phone. The running total per Uke is the «Sum, kr» row in Alle rader, and «Vis som tabell» under «Totalkostnad over tid» on laptop. | What to order: the panel shows what it cost, never what to order |
| Game end (group) | The chain total first («2 266,00 kr»), then Kjedens regning per Role and cost type, then «Kjedens kostnad over tid» | — |
| Debrief | Kjedens regning with «Kjeden 901,00 / 1 365,00 / 2 266,00». «Simulert, samme kunder: Bare Sara teller på vei 1 507,00 / Alle fire teller på vei 1 341,00». «Restordre er 60 % av kjedens regning, fordi den koster dobbelt.» The share of chain cost from AI-held Seats (FR-44). [ASSUMPTION: as a line under Kjedens regning; not drawn] | — |
| Faglærer (aggregate) | kjedekost per game in the wall; «Klassens kostnad» distribution with the median and «Fjoråret»; «Snitt per ferdig spill, per Rolle» split into lager and restordre; «Kjedekost per uke, snitt per spill». Sorting by cost is for Faglærer only. | Sorting by cost on any Student-facing surface or in plenum |

## Chain direction convention

There is one convention on every surface: Kjedebånd, Klasseøkt «Kjeden ved start» («Varer mot høyre, ordre mot venstre»), the Debrief, «Delt skjerm», Spillinnsikt and the contact-sheet mockup.

- Upstream is on the left: Produksjon → Fabrikk → Distributør → Grossist → Detaljist → Kundene.
- Goods flow right, toward Detaljist and the customer. Orders flow left.
- Rows that list Roles up the chain (Ordrestolper, Delt skjerm) put **Fabrikk at the top**.
- Tables per Role (Kjedens regning, Snitt per Rolle) run **Detaljist to Fabrikk**, the order in which amplification grows.

## Debrief sequence

Group debrief by default (FR-16, FR-43). Each Student is on their own phone, with an optional shared screen. Headings are verbatim (`07-debrief.png`).

| Step | Heading | Behaviour | Principle |
|---|---|---|---|
| 1 | «Skriv Forklaringen først» | «Ditt netto lager, hele spillet» chart. Prompt «Hvorfor svingte lageret ditt?», then «Send Forklaring». The reveal is locked until the Student's own Forklaring is saved. In a group, the step moves on when all have sent (FR-41, FR-43). Students cannot see each other's Forklaringer. | before-measure |
| 2 | «Kundene bestilte 4, så 8. Etter det endret de seg aldri.» | **The reveal.** Demand band, «Ordre inn: det eneste du så», «Din ordre, 24 i Uke 11», table Uke / Kundene / Ordre inn / Din ordre. Names the exercise: «Øvelsen heter Beer Game.» | P4, P6 |
| 3 | «Hele kjeden: svingningene vokser oppstrøms og kommer senere» | Full chain with the Ukeskrubber. Ordrestolper for four Roles with the first order ≥ 10 marked (Uke 6, 11, 13, 15) and Forsterkning 1,8× → 7,6×. Rolle × Uke numbers in the same columns. | P4, P5 |
| 4 | «Ditt øyeblikk: Uke 11. Du bestilte 24 med 16 på vei. Og hva det kostet kjeden.» | «Dette så du» (graph over table), «Dette regnet du», «Dette kostet det senere», «Dette så de andre i Uke 11», the AI line labelled «KI-generert, kan ta feil», then Kjedens regning with Simulert. Only on the Student's own device (FR-43). [ASSUMPTION: the other moments required by FR-44, at least three, are paged within this step; only one is drawn.] | P3, P7, P8 |
| 5 | «Debrief-quiz» | Fixed questions, wrong answers explained, retry until all are correct (FR-46) | P3 |
| — | «Delt skjerm: hele kjeden» | Shared charts only: chain, Netto lager per Role, «Kostnad, kr» per Role, «Kjeden 2 266,00». No Forklaringer and no personal moments (FR-43, FR-74). | P5 |

Reflection questions and bounded follow-up (FR-45) are not drawn. [ASSUMPTION: they sit between steps 3 and 4, under the same AI labelling.]

## AI disclosure

| Where | Rule | Copy |
|---|---|---|
| Setestatus, Klasseøkt allocation, Oversikt | Every AI-held Seat is named «KI-spiller» from the first view (FR-34) | «Tomme seter får KI-spiller.», «22 KI-spillere i 17 spill, alle merket.» |
| Takeover | Announced to the Seat, the group and the Oversikt (FR-36) | «KI-spiller  bestiller for Jonas», «KI-spiller har bestilt for deg.» |
| Play guard switch (FR-79) | The Seat shows that it now uses a rule-based player. [ASSUMPTION: the same Setestatus row, copy to be written] | — |
| AI text (Debrief, quiz explanations, Replay walkthrough, Adapted items) | Prefix, plus machine-readable marking, including in PDFs (FR-34) | «KI-generert, kan ta feil: «…»» |
| KI-vurdering | Every view says that it does not count and is not a grade (FR-55) | «Teller ikke. Ingen karakter.» |
| KI-modus setup | Scope stated | «Gjelder alle KI-spillere i Klassespill og Replay.» |

## Demo/synthetic data labelling

- Any surface showing synthetic numbers carries «Demodata» (`{colors.ink-muted}`, `{typography.caption}`). This covers the landing (twice: Seat chart and «Alle spillene på én skjerm») and onboarding examples. [ASSUMPTION: real Class session data carries no label; Lærers testspill (FR-87) is labelled as a test game, not as Demodata.]
- Simulated references are always labelled «Simulert» («Simulert, samme kunder») and are never called «optimal» or «fasit».
- Replay comparisons say «Ikke like for like.» (FR-50).
- What the landing may show: State Patterns → Account and access → Landing.
- Mockup note: the Debrief page header in the mockups carries «Demodata. Simulerte tall er merket Simulert.» because the mockups show synthetic data. The product shows «Demodata» only on synthetic data (first rule above).

## Key Flows

### UJ-1. Kari, the admin, makes Bård a lecturer.

Not drawn beyond the contact-sheet mockup («Admin-område», «Brukere og roller»).

1. Kari opens the Admin-område, «Brukere og roller».
2. Kari enters Bård's e-mail, picks the Faglærer role and sends the Invitasjon (FR-1).
3. Bård opens the e-mail, which is headed «ØL-spillet», and lands on «Du er invitert» with the e-mail prefilled.
4. Bård sets a password and profile and presses «Opprett konto og gå videre».
5. **Climax:** Bård lands on an empty Lærerhjem with «Ny Klasse» as the only action. The role took effect with no approval step.

Edge: Bård already has an Assistent account. Kari grants the role to it, and Bård sees Lærerhjem at the next page load with the same login (FR-2).

### UJ-2. Bård invites 250 students three weeks ahead.

`02-laerer-klasse.png`

1. In «Lag Klasse», Bård types «class-of-1994» and «IBE160».
2. Bård uploads «ibe160-canvas-eksport.xlsx» and sees «250 rader lest».
3. «E-postkolonne» is preselected: «Kolonne C, E-post. Valgt fordi alle rader unntatt fire ser ut som adresser.»
4. «Ugyldige rader: 4 av 250» lists rows 37, 88, 141 and 203 with reasons.
5. Bård presses «Send 246 Invitasjoner».
6. **Climax:** two weeks later, «Status etter utsending» reads Registrert 238 · Manuelt 2 · Uregistrert 10. Bård registers two by «Registrer manuelt» and presses «Send påminnelse til 10».

Failure: a row is still invalid, so it gets no e-mail until fixed or registered manually.

### UJ-3. Bård sets up the games in the last week.

`03-laerer-spill.png`

1. Bård opens «Klasseøkt for class-of-1994»: «Alt er fylt ut med standardene.», «Spillinnstillinger: Klassisk».
2. Bård reads «Kjeden ved start», where the boxes on the pipe show the delays and Lager 12.
3. Bård keeps «LLM-spillere» and «Gruppedebrief» and switches «Obligatorisk» to «Ja, står i emneplanen».
4. Bård sets the dates on the Datolinje (Start ti. 24. nov to Testfrist fr. 18. des) and adds four Labtimer with «Legg til Labtime».
5. In «Fordeling: 60 Klassespill à 4», Bård checks Spill 17 and presses «Kjør fordeling på nytt» once.
6. **Climax:** Bård presses «Bekreft fordeling»; beside the button: «Ingen får beskjed før du bekrefter.» Bård then presses «Lagre Klasseøkt», and the whole setup needed no changes to the defaults.

Edge: 241 Students gives one game with one Student and three KI-spillere (FR-20).

### UJ-4. Sara's group plays, mostly on its own schedule.

`04-student-hjem.png`, `05-spill.png`, `06-spilldynamikk.png`

1. On the Start date, Sara's Hjem reads «Spill 17 · Du er Grossist». Setene lists Ida, Sara, Mikkel and Jonas.
2. Sara reads «Regler før første ordre» (lowest cost for the whole chain, no talking about Orders) and does the Startoppgave.
3. Uke 1–4 are Veiledede uker, and the order of 4 is placed automatically.
4. In Uke 11, the new column shows Ordre inn 8 and Levering 4. The band reads «Restordre 13» and «På vei 16». The Posisjon row and the Posisjon line read 3.
5. Sara taps «Alle rader og kostnad», sees «Posisjon i kolonne 11  −13 + 16 = 3», «Restordrekostnad 25,00 kr» and the week's sum, then taps «Lukk».
6. Sara types 24. It appears under Din ordre and under Levering in Uke 15, and the band shows «På vei 16 + 24». On a laptop, Enter would move focus to the button.
7. Sara presses «Bekreft ordre på 24» and sees «Ordren på 24 er sendt. Venter på Jonas.»
8. **Climax:** Jonas orders, and the now-line moves one column. «Uke 11 er ferdig regnet: Restordre 13 blir 20. Denne uka: 20 restordre × 1,00 = 20,00 kr.» The Posisjon line takes in the 24. The next order builds on a sum, not on an answer key.
9. After 15 Uker Sara presses «Ta pause» and «Ta pause uten avtalt tid» (Pausevalg). All four see «Pause, satt av Sara.» The group wants to go on in Thursday's Labtime, so Bård sets the agreed time from Spillinnsikt with «Endre avtalt tid» (Spillstyring), and all four see «Pause til to. 19:00, satt av faglæreren.» Sara sees the Uke number, never how many remain.

Failure: on Thursday at 19:00 Jonas has not ordered. Sara orders, which ends the Pause; the agreed time has passed, so the right to insert a KI-spiller stays. Sara's Setestatus now shows «KI-spilleren bestiller for Jonas fra denne Uka. Jonas kan ta setet tilbake fra neste Uke.» over «Sett inn KI-spiller for Jonas». Sara presses it, and the row reads «Fabrikk  KI-spiller  bestiller for Jonas». Jonas later sees «KI-spiller har bestilt for deg.» and «Ta tilbake setet».

Failure: Sara's confirm fails on a weak connection. Sara sees «Ordren ble ikke sendt. Ingenting er bestilt ennå.», the 24 still in the field, and presses «Prøv å sende 24 igjen».

### UJ-5. Sara's group debriefs together, then Sara plays alone.

`06-spilldynamikk.png` F, `07-debrief.png`, `10-pedagogikk.png`

1. «Spillet er ferdig» shows «2 266,00 kr» first, then Kjedens regning per Role. Sara presses «Gå til Debrief».
2. Sara writes the Forklaring and presses «Send Forklaring». The reveal waits for the others.
3. **Climax:** step 2 reveals «Kundene bestilte 4, så 8. Etter det endret de seg aldri.» Sara's 24 in Uke 11 towers over flat demand.
4. Step 3: the group scrubs the chain on the shared screen and sees 1,8× grow to 7,6×.
5. Step 4: Sara sees «Posisjon 0 − 13 + 16 = 3. Med 24 ble den 27.» and Kjedens regning next to «Simulert».
6. Debrief-quiz: Sara answers −13, gets «Ditt svar, ikke riktig» and the column explanation, and answers 3 on retry.
7. Over the weekend Sara starts the Replay: same screen with the same Posisjon row and line, plus the dashed projection, three KI-spillere and random demand.
8. Replay-gjennomgang: Klassespill and Replay on one axis, «Ikke like for like.»

Failure: the group never meets within 48 h, so Sara takes a Personal debrief (FR-43).

### UJ-6. Sara takes the individual test.

`09-alle-sider.png` («Individuell test»)

1. Sara opens the Individuell test from Stegene and confirms the work is their own (FR-51).
2. Sara answers «Flervalg».
3. Sara answers «Fyll inn kolonnen». It is the same column arithmetic as the game, with a table alternative.
4. Sara draws the bakery stock in an Interaktiv oppgave. Each point Sara drags fills the value table under it; a classmate on keyboard alone answers the same item by typing a value per Uke in that table.
5. Sara writes «Langsvar». The phone advises a larger screen, and answers save automatically («Lagret 21:14»).
6. Sara closes the test and returns on later evenings.
7. Sara presses «Lever testen» and reads the review: every item is answered.
8. **Climax:** Sara submits once before the Testfrist and sees «Levert to. 18. des kl. 21:40. Du kan ikke endre svarene.»

Failure: the Testfrist passes first, so saved answers are submitted automatically (FR-51).

### UJ-7. Bård keeps 60 games on track.

`08-laerer-oversikt.png`

1. Bård opens the Oversikt: «41 ferdig · 15 pågår (herav 2 pauset) · 4 venter».
2. **Climax:** the Varselbånd reads «Spill 2 venter på Noah (Grossist) i 23 t. KI overtar om 1 t.» Bård presses «Send Melding» and the band is the only thing Bård has to act on.
3. Bård scans «Venter ellers» and the pauses («Pause i Uke 29, fortsetter i kveld 19:00»).
4. Bård switches «Vis som tabell» to read exact cells.
5. At the Spillfrist, the playout finishes the unfinished games, and the Trakt moves.

Failure: none needed. Takeover runs automatically after 24 h (FR-36).

### UJ-8. Sara reads the AI assessment; Sara and Bård download the reports.

`09-alle-sider.png` («KI-vurdering», «Studentrapport (PDF)»)

1. Sara gets the e-mail and opens the KI-vurdering: «KI-generert, kan ta feil. Teller ikke. Ingen karakter.»
2. Each piece of feedback quotes Sara's answer. Sara flags one with one click (FR-55).
3. Sara turns the Veiledende bokstav on for their own view (FR-56).
4. **Climax:** Sara downloads the Studentrapport, headed «ØL-spillet», with graph over table, decisions, cost and Forklaring. The AI section is left out unless Sara adds it.
5. In Klasseøkt → «Eksport», Bård presses «Last ned alle Studentrapporter (ZIP)», sees «ZIP-filen lages. Du får beskjed når den er klar, innen 10 minutter.», and downloads the fullføringsliste (FR-59, FR-60).

Edge: a Student without a test still gets a report, with the step marked as not done.

### UJ-9. Bård compares and reruns.

`09-alle-sider.png` («Klasserapport», «Alle spill i plenum», «Tverrklasse-statistikk»)

1. Bård opens the Klasserapport: kjedekost and Forsterkning per Role, cost per type, Mønstre.
2. Bård shows «Alle spill i plenum»: 60 games as a matrix, «Mønsteret går igjen, uten navn og uten rangering.»
3. Tverrklasse-statistikk compares «class-of-1993» with «class-of-1994», «Samme mål, samme regnestykke.»
4. **Climax:** Bård creates next year's Klasseøkt from this one (FR-66), prefilled and ready to save unchanged.

## Open Questions

1. **360 px density** of the chain band, two graph fields (now with the Posisjon line), seven rows and the order input is untested with real Students (issue #24).
2. **Cost visibility and P7:** does a prominent «Kostnad så langt» tempt overreaction? Untested (issue #24).
3. **Last year's data** has only a median in the fixture, so «Fjoråret» is a single mark, not a distribution (issue #24).
4. **Matrix wall table view** is drawn only as the toggle, not as its own sheet (issue #24).
5. **Undrawn (spine-only) surfaces:** Information visibility (FR-83), the scheduling aid (FR-22), Pausevalg and Sett inn KI-spiller (FR-89), the Faglærer pause, Spillstyring (FR-22, FR-36, FR-37), Tilrettelegging and Fullføringsretting (FR-17), Play guard disclosure, AI-share of chain cost (FR-44), follow-up questions (FR-45), the drawing Interaktiv oppgave, playout copy, Admin screens, and every IA row marked spine-only.
6. **Laptop breakpoint** and tablet behaviour are not set by any source.
7. **PRD update needed (issue #25):** FR-84, the neutral-naming risk mitigation and PRD open question 1 after the «ØL-spillet» override; FR-89 gains a Faglærer pause, and only the Faglærer sets an agreed pause time (Students pause without one; founder decision 2026-11-10); FR-17's per-Student adjustment gains this spine's Tilrettelegging factors and the rule that it also extends «I rommet» and agreed times; FR-36 gains a 20 h floor on the Klasseøkt Inactivity limit [ASSUMPTION]; the addendum §B "goods flowing down" layout is now horizontal.
8. **Posisjon in the Klassespill (issue #22 risk, test in the pilot):** with Posisjon shown as a row and a line, an order-up-to rule becomes easy to follow, which may flatten the oscillation and weaken the Debrief reveal (step 4, «Dette regnet du»; P3). The pilot should check Forsterkning per Rolle and what the Forklaringer show before this is kept for later courses.
