# Product

<!-- impeccable:product-schema 1 -->

> Inferred from `.docs/planning-artifacts/prds/prd-beergame-2026-10-29/prd.md` on 2026-11-05. The founder asked not to be interviewed at this stage ("Ikke spør meg nå"), so every fact here comes from the PRD, and items marked [INFERRED] have not been confirmed.

## Platform

web

## Users

- **Lecturer** teaching supply chain, logistics or operations in Norwegian higher education, with courses of about 250 students. Runs the exercise midway through a course and must not spend weeks as a referee.
- **Assistant lecturer** helps monitor games, staff Lab hours and message students.
- **Student** plays on a phone, tablet or laptop, mostly on the group's own schedule, often over several evenings.
- **Admin** is the platform operator (the founder in the pilot).
- **Institution** pays and is not a user in v1.

## Product Purpose

Runs the whole four-Role supply chain exercise for a course: Invitations, groups, Class game, Debrief, Debrief quiz, Replay against AI players, Individual test with non-counting AI assessment, and a PDF Student report. AI players step into every empty Seat. Success: every game finishes, every student gets documentation, and students can explain how their own Orders produced what they lived through.

## Positioning

The product is working AI players plus the explanation: a Debrief that explains each student's own decisions from the Decision log, and a second round. Bot-filled Seats alone are not the difference; competitors offer them free.

## Operating Context

- Students play on their own phones, typically in the evening, or in a computer lab during a Lab hour with the Lecturer in the room.
- One decision per Week: one whole number. All Seats order in the same Week; the Week advances when every Seat has ordered. A game can stretch across days, with Pause and Takeover.
- The Lecturer watches 60 Class games at once, on a laptop, and may show all games in a plenary.
- Student lists come from Canvas exports (Excel/CSV). There is no LMS integration in v1.

## Capabilities and Constraints

- Norwegian bokmål only in v1. Screen and product text use: Detaljist, Grossist, Distributør, Fabrikk; Uke; Ordre; Lager; Restordre; Klassespill; KI-spiller.
- Portrait-first playing screen; all Seat data and the Order input visible on a 360 px wide screen without horizontal scroll.
- Hidden information: students never see the number of Weeks or the customer demand series while playing (only the Detaljist sees demand, one Week at a time). Other Seats' numbers are hidden unless Information visibility is switched on.
- Product text never uses the name "Beer Game" before the Debrief, and the product's own name respects this.
- No chat or communication between players in v1. No Student-facing ranking and no prizes.
- AI players, Takeover and AI-generated text are always disclosed. The AI assessment is formative, counts toward nothing and is never a grade.
- No public sign-up: accounts come by Invitation.
- Product name is an open decision. "beergame" is only the repository name.

## Brand Commitments

None yet. No name, logo or visual identity exists.

## Evidence on Hand

No customers, testimonials, prices or measured learning results exist. Product and sales text make no learning or bullwhip claim until measured. Demonstration data must be labelled synthetic.

## Product Principles

- The student only decides; the system does the arithmetic.
- Causes are explained through structure, not people: no blame, no padding praise.
- One missing student never holds the others back, and no game stays unfinished.
- Every number the AI shows comes from computed facts.
- The Lecturer sees everything on one screen and does not referee. [INFERRED from UJ-7]

## Accessibility & Inclusion

WCAG 2.1 AA for Student and Lecturer screens. Charts have text or table alternatives. Role and status are never shown by colour alone. Every Student flow works from 360 px wide.
