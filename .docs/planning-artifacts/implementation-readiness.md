# Implementation readiness: ØL-spillet v1

**Date:** 2026-11-12
**Verdict on 2026-11-12:** CONCERNS. The founder chose to fix the findings before the sprint tracking file is generated.
**Status on 2026-11-14:** all 29 findings below are fixed in `epics.md` and the UX spines. See the next section.
**Status on 2026-11-17:** the mechanical checks were rerun on the committed plan with the same result as on 2026-11-14, and the founder asked for the tracking file. `implementation-artifacts/sprint-status.yaml` is generated: 15 epics, 199 stories, all in `backlog`. Issues #31, #32 and #21 are still open.
**Checked:** `epics/epics-beergame-2026-11-12/epics.md` (15 epics, 199 stories) against `prd.md`, `ARCHITECTURE-SPINE.md`, `EXPERIENCE.md`, `DESIGN.md` and `open-assumptions.md`.

Nothing below touches Epic 1 or Epic 2, which have no screens. The first story affected is 3.1.

## Status after the fixes (2026-11-14)

- **Decisions:** the founder took the six UX decisions (findings 1, 2, 6, 8, 11 and 17). They are in `EXPERIENCE.md`, `DESIGN.md` and the UX memlog, and listed in `epics/epics-beergame-2026-11-12/open-assumptions.md`.
- **Stories:** 51 edits in 36 stories of `epics.md` close findings 1 to 29. No story was added, removed or renumbered.
- **Checks rerun:** 199 stories and 1 252 criteria, 3 to 8 per story. Every FR, NFR, AD rule and UX-DR is still in a `Covers:` line. Of 468 distinct quoted Norwegian strings, 450 match the UX spines exactly, and the rest are example values or headings. The three new mentions of a later story are hand-offs. The dry run of `sprint_plan.py` parses 15 epics and 199 stories.
- **Architecture:** AD-2 now lists the commands the stories add (issue #32). Event topics per command and the other additions are still only in `open-assumptions.md`.
- **Not done:** the fixes were not read by a second reader. Mockups `03`, `04`, `05`, `06` and `08` are not redrawn; the spines say they win.
- **Left for the founder (issue #31):** confirm the draft copy and the choices made while fixing, and decide the late-registrant case in Story 5.13 (FR-20). None of it blocks Epic 1 or Epic 2.
- **Left open (issue #21):** the date plan against the course date.

## What holds

- All 89 FRs, 10 NFRs, 26 architecture rules (AD) and 78 UX requirements (UX-DR) are claimed in a `Covers:` line, and no story claims an id the sources lack.
- All 28 mentions of a later story are hand-offs ("Story X adds this"), not dependencies. Epics build only on earlier epics.
- Of 452 distinct quoted Norwegian strings in the stories, 435 match `EXPERIENCE.md` or `DESIGN.md` exactly. The other 17 are example values, new copy, or a difference in case.
- Open research inputs (issues #8, #16, #17, #20) are configuration slots with marked placeholders in the stories.
- `sprint_plan.py generate --dry-run` parses all 15 epics and 199 stories. Its two warnings are the document title and the heading «Epic List», which are not epics.

## How the UX check was done

Three readers each took 26 UX-DRs. For each one they read the inventory line, the stories that claim it, and the matching part of the UX spines. 48 of 78 are carried cleanly. The findings marked **confirmed** were checked again in the text; the rest are as the readers reported them.

**Not checked:** the mockup PNGs were not opened. UX-DR75 (responsive rules) and UX-DR76 (accessibility floor) were sampled, not walked row by row. Stories 3.7, 10.9, 11.7, 11.8, 12.7, 13.9 and 15.5 were read only on the lines that cite a UX-DR. The front matter of `DESIGN.md` (token values) was not compared with any story. For the meaning of each FR, this check relies on the validation of 2026-11-12 and only checked ids.

## Findings

### Conflicts: the developer would build the wrong thing or must decide

| # | Stories | UX-DR | What is wrong | Source |
| --- | --- | --- | --- | --- |
| 1 | 7.2, 7.3, 7.7, 7.11 | 8, 41, 42 | 7.2 makes each Matrisevegg row focusable, 7.7 opens a row with Enter, and 7.11 puts a «Melding» link on every row. 7.3 says the SVG wall is `aria-hidden`. Focusable content inside `aria-hidden` fails the axe check the stories require. The spine has both rules. **Confirmed.** | EXPERIENCE.md → Accessibility Floor → Charts; Matrisevegg |
| 2 | 6.14, 6.17, 8.6, 8.7 | 25, 26 | 8.6 puts «Ta pause» under the Setestatus and the pause line above it, for all four Students. 6.14 shows the Setestatus on the play screen only after the Student has confirmed an Order. A Student who has not ordered has no place for either, and that Student ends the pause by ordering. The notice slot 6.14 leaves above the Ordrefelt is filled by no Epic 8 story. The spine has the same hole. **Confirmed.** | EXPERIENCE.md → State Patterns → Spill → Paused |
| 3 | 3.12 | 75 | The audit log table "scrolls inside its own region at 320 px". DESIGN.md lists Admin lists and forms among the surfaces that must reflow. **Confirmed.** | DESIGN.md → Layout & Spacing, widths table |
| 4 | 4.5, 6.1 | 62 | Both quote «Du får Rolle og spill når Faglærer har bekreftet fordelingen.». The founder decided on 2026-11-12 that a Student sees the game from the Start date, so the line is untrue between confirmation and the Start date. Issue #31 names only EXPERIENCE.md for this change. **Confirmed.** | open-assumptions.md, row 1; EXPERIENCE.md line 410 |

### Gaps: a rule or a part is missing

| # | Stories | UX-DR | What is missing | Source |
| --- | --- | --- | --- | --- |
| 5 | none (7.6 nearest) | 72 | «Snitt per ferdig spill, per Rolle», split into lager and restordre, is built by no story. **Confirmed absent.** | EXPERIENCE.md → Cost picture, Faglærer row |
| 6 | 6.12, 6.14 | 60 | «Du får beskjed når Uke 12 åpner.» is in no story, and no notice is sent when a Week opens (8.13 only reminds after a wait, in the digest). The developer must decide what the line promises. **Confirmed absent.** | EXPERIENCE.md → State Patterns → Spill → Confirmed |
| 7 | 3.1 (also 6.6, 6.16, 7.2) | 1, 3 | 3.1 is written for «Logg inn». No criterion puts the whole token set in the theme (matrix steps, `flow-*`, type roles such as `figure-hero`), checks it against DESIGN.md, stops literal colours later, or says how the hand-made SVG charts read tokens. Tabular figures appear only in 3.13. | DESIGN.md front matter; Typography |
| 8 | 5.1, 5.9 | 48, 50 | 5.1 calls «Lagre Klasseøkt» the screen's one primary button; 5.9 calls «Bekreft fordeling» the primary button on the same screen. The spine allows one. Raised as M5 in the UX validation report. | EXPERIENCE.md → Controls → Knapper |
| 9 | 7.8 | 33 | 7.8 leaves a place for Forsterkning in Spillinnsikt, shown "when the caller supplies it". No story supplies it there. The spine has it in both the Debrief and Spillinnsikt. | DESIGN.md → Ordrestolper |
| 10 | 6.17 | 28 | The waiting-for-others Spillkort has no title; the only title given is «Spillet venter på deg». Not on the copy-to-write list. | EXPERIENCE.md → State Patterns → Hjem |
| 11 | 6.7 | 16 | The Kost per uke axis has a fixed maximum marked «40 kr». Neither UX-DR16 nor 6.7 has it, and nothing says what happens when a Week costs more. **Confirmed absent.** | DESIGN.md line 615 |
| 12 | 6.6 | 17 | Known arrivals are "marked as ordered, not guaranteed", but no label text or mark is given. Not on the copy-to-write list. | EXPERIENCE.md → Graf over tabell |
| 13 | 6.9, 6.11 | 14 | 6.9 has «Ordre inn 8» and a screen-reader text ending «På vei 16». 6.11 adds the typed box but not the label «Din ordre 24» or the updated text «… På vei 16 pluss 24». | DESIGN.md → Kjedebånd; EXPERIENCE.md → Screen readers |
| 14 | 6.2, 6.3 | 70 | The spine says «Demodata» covers onboarding examples. Neither the briefing's worked Uke nor the Startoppgave is labelled. | EXPERIENCE.md → Demo data labelling |
| 15 | 3.1 | 74 | The only product-wide copy check in CI is for «Beer Game» and «bullwhip». Exclamation marks, «øl», «optimal», «fasit» and praise are checked per story only. Mail templates and the print route are outside `nb.ts`. | EXPERIENCE.md → Voice and Tone |
| 16 | 6.6, 6.11 | 78 | "No surface shows a recommended order" has no test, although two reference Orders are stored per Seat (1.8, 2.9). The envelope test in 6.6 does not list them. | EXPERIENCE.md → Interaction Primitives → Banned |
| 17 | 11.12, 8.9 | 53, 65 | The spine calls «I rommet» "the only timed sitting in v1". The stories add a timed test sitting and apply the Tilrettelegging factor to it. The spine has no state or copy for the running clock. open-assumptions.md lists the choice but not the conflict. **Confirmed in the spine.** | EXPERIENCE.md → Tilrettelegging |

### Minor

| # | Stories | UX-DR | What is missing |
| --- | --- | --- | --- |
| 18 | 6.1, 9.2, 13.7 | 29 | Lock lines exist only for Replay and Individuell test. Debrief, Quiz and Rapport have none, and nothing says how a finished step reads. |
| 19 | 8.12, 8.7, 8.11 | 52 | The per-game «Sett inn KI-spiller i alle seter som blir ventet på» has no consequence text. 8.7 and 8.11 omit the focus-on-open rule for in-place forms. |
| 20 | 7.1, 8.6 | 41 | 7.1 orders the wall groups Venter, Pågår, Ferdig. 8.6 adds «Pause» without a position. The spine says Venter, Pause, Pågår, Ferdig. |
| 21 | 7.9 | 46 | A second «Send Melding» in the Oversikt header, for the whole Class session, is in neither the spine nor open-assumptions.md. |
| 22 | 9.15, 9.5 | 31, 34 | 9.15 does not place the follow-up field. 9.5 omits the line «Kjeden i Uke 15. Dra i skrubberen for å spole.». |
| 23 | none | 6 | `rounded.xs` on the column highlight frame is in no story, and the spine names no component that has the frame. |
| 24 | 6.9, 7.8, 9.5 | 15 | 6.9 promises the four-Role Kjedebånd for staff views. No staff view draws it. |
| 25 | 6.15 | 22, 23 | The Lenke «Kostnad så langt» in the Uke-overgang has no target, and nothing says when the summary goes away. |
| 26 | 13.8 | 68 | The spine says the report has a graph over the table. The story gives the Student's own Seat a table only. |
| 27 | 13.3, 13.4 | 54 | Focus after save is not stated, and 13.4 has no focus rule for its form. |
| 28 | 5.8 | 69 | «22 KI-spillere i 17 spill, alle merket.» is in no story. **Confirmed absent.** |
| 29 | 3.13, 6.8 | 61 | The Landing's phone stack ends with «Kostnad så langt» in the spine. No story puts it there. |

Finding 12 in story 6.12: the story writes «Venter på …» where 6.14 and the spine write «Venter på: …».

## Open from before

- **Issue #31:** about 90 choices in `open-assumptions.md` are unconfirmed. One needs a decision: a late registrant with no free Seat gets a new Class game in Story 5.13, where FR-20 says a make-up.
- **Issue #32:** the architecture spine lacks the commands, hooks and tables the stories add. The first is `games.commands.advance` in Story 2.1.
- **Issue #21:** there is no date plan for 199 stories against the course date.

## How to fix

- Findings 1, 2, 6, 8, 11 and 17 need a UX decision first, then a change to `EXPERIENCE.md` or `DESIGN.md` and to the stories named: `bmad-ux` to update the spines, then `bmad-correct-course` or a direct edit of `epics.md`.
- The rest are edits to the stories named, with new copy added to the copy-to-write list in `open-assumptions.md`.
- Then run `bmad-sprint-planning` again. If a fix adds or renames a story, the tracking file is generated from the new list.
