---
title: "Product Brief: beergame"
status: draft
created: 2026-09-04
updated: 2026-09-07
audience: investors and stakeholders
---

# Product Brief: beergame

> **Working name.** "beergame" is the repo name, not a product name. Naming is an open item — see Open Questions.

## Executive Summary

The MIT Beer Distribution Game has taught supply chain dynamics for sixty years, and it is quietly disappearing from classrooms. Not because the lesson stopped mattering — the bullwhip effect is more relevant after five years of supply shocks than it ever was — but because the delivery is broken. In June 2026 an educator writing in *Times Higher Education* declared that the game "may have had its last orders": slow to run, surprisingly fragile, mechanically distracting, and, most damning of all, students finish a session unable to explain how their own decisions produced the outcome they just lived through.

We are rebuilding it as a browser-based product that works on a laptop, an iPad or a phone — and that removes the constraint underneath every one of those complaints: the requirement that four people sit down together at the same hour. AI agents fill any empty role, which turns a once-per-semester group event into something a single student can replay as many times as it takes for the pattern to click. Recent research is unusually kind to this approach: LLM agents reproduce the same myopic ordering behaviour humans display, so AI opponents *preserve* the bullwhip effect instead of optimising it away. The pedagogy survives contact with automation. That is not obvious, and it is the technical bet worth making.

Lecturers set up classes and run live multiplayer sessions the way they always have. Students replay solo between sessions, with an AI debrief that explains what happened and why. Cheap per student, licensed at institutional rates to schools. The first classroom is the founder's own: he teaches the course this ships into.

## The Problem

The game is failing in practice, and the failures are documented rather than assumed. From the *Times Higher Education* account of running it:

- **The mechanics eat the lesson.** "The effort required to run the game can end up distracting from the bigger picture." Students spend the hour moving tokens and doing arithmetic instead of watching a supply chain oscillate.
- **Students cannot explain their own outcome.** "Few could clearly explain how their decisions had led them there." This is the expensive one. The game runs, the bullwhip appears, and the insight does not land.
- **It is slow and it breaks.** "Slow to run and proves surprisingly fragile" — a small bookkeeping error in orders or inventory distorts the result, and the distortion is invisible until the debrief makes no sense.
- **It is predictable.** Fixed demand patterns let students anticipate outcomes rather than react to them.

Underneath all four sits a constraint nobody names: **you get one attempt.** Four people, one demand curve, one slot in the timetable. Nobody replays it. Nobody gets to ask "what if I had not panic-ordered in week six?" — because asking costs another four humans and another hour.

The status quo is that lecturers either run a fragile manual session, adopt a free browser version that automates the arithmetic but keeps the one-shot format, or drop the exercise. The *Times Higher Education* author chose to build a replacement himself. That is the cost of the status quo: the people who care most about the exercise are abandoning it.

## Why Now

Three things converged in the last eighteen months:

1. **The decline is now on the record**, not just felt. A supply chain educator published his reasons for abandoning the game and building a replacement. `[ASSUMPTION] One published account is a signal, not a trend. Before this line goes in a pitch deck it needs corroboration — a second published source, or a handful of lecturer interviews.`
2. **LLM agents became good enough, cheap enough, and — crucially — behaviourally right.** Published work through 2025-2026 shows LLM agents in the beer game are myopic in recognisably human ways and generate bullwhip themselves. A classical optimising bot would have destroyed the exercise; an LLM one does not.
3. **The incumbent field is static.** Multiple free browser versions exist and are well maintained, but they solve the arithmetic problem and stop there. None of them attack the one-attempt constraint. `[ASSUMPTION] Verified at the level of public marketing and product pages, not feature-by-feature testing — see Open Questions.`

## The Solution

A web application, responsive across desktop, tablet and phone, with accounts and persistent history.

**For lecturers.** Create a class, invite or roster students, launch a live session, watch it unfold, and run a debrief built from real data rather than recollection. Any unfilled role is taken by an AI agent, so a session starts on time with the students who actually showed up.

**For students.** Play solo against AI agents whenever they like, as often as they like. The demand pattern varies between runs, so the answer cannot be memorised. After each run, an AI debrief walks through the decisions: here is where you over-ordered, here is what it cost four weeks later, here is what the other roles saw when you did it.

**The core move is repetition.** One session teaches that the bullwhip effect exists. Ten sessions teach why your own instincts cause it. The product exists to make the tenth session possible.

## What Makes This Different

Honest version, because the alternative gets found out in due diligence:

- **The moat is not the simulation.** Beer game mechanics are sixty years old and public. Anyone can build them.
- **The moat is not the AI either, in the long run.** Any competitor can call the same model providers.
- **The defensible position is being first to treat the game as repeatable practice rather than a one-off event**, and building the debrief, progression and class-management layer that only makes sense once repetition is the point. That is a product-design lead and an execution lead, not a technical one.
- **The near-term unfair advantage is distribution and dogfooding**: a founder who teaches the course, ships into his own classroom, and iterates on real students in a real semester before selling to anyone else.

**The honest risk:** several competent competitors are free. See Risks.

## Who This Serves

**The lecturer (primary buyer-influencer).** Teaches supply chain, operations or logistics. Wants the exercise to land without spending the hour as a referee. Success looks like a debrief where students explain the mechanism back to them.

**The student (primary user).** Needs to actually understand bullwhip, not just witness it once. Success looks like being able to replay until the causal chain is obvious — on the bus, on an iPad, at 23:00 before an exam.

**The institution (payer).** A department or business school buying for a cohort. Success looks like a defensible line item: measurable engagement, curriculum fit, no IT burden.

## Business Model

Two-tier, deliberately asymmetric:

- **Students: cheap.** Low enough to be an impulse decision against free alternatives. `[ASSUMPTION] Price point not yet set.`
- **Institutions: premium.** Class management, cohort analytics, roster integration and support are what a department pays for, and what a student never needs. `[ASSUMPTION] Price point and packaging not yet set.`

The strategic logic: students are the most price-resistant segment there is and the competition is free, so the student tier is an adoption channel more than a revenue line. Revenue concentrates on institutions, and student adoption is what makes the institutional sale easy. `[ASSUMPTION] This reading of the model is inferred from "cheap student, expensive school" and should be confirmed.`

## Success Criteria

`[ASSUMPTION] Targets below are placeholders — the shape is proposed, the numbers need your judgement.`

**Learning (the claim the product rests on)**
- Students who replay solo can explain the causal chain behind their outcome measurably better than one-session students. This is testable in the founder's own course in the first semester, and it is the single most valuable evidence this venture can produce early.
- Median solo replays per student per course > 3. If students play once and stop, the core thesis is wrong.

**Product**
- A lecturer can go from signup to a running class session in under 10 minutes, unaided.
- Sessions start on time with fewer than four humans present.

**Business**
- First paying institution outside the founder's own. This is the real validation milestone.
- Cost per AI-driven game session stays below the student price point.

## Scope

**In, for the first version**
- Accounts and authentication
- Lecturer-created classes and live multiplayer sessions
- AI agents filling any unoccupied role
- Full single-player mode against AI agents
- Variable demand patterns between runs
- Post-game debrief with per-role decision history
- Responsive web: desktop, tablet, phone

**Explicitly out of the first version**
- Native apps
- LMS integration (Canvas, Blackboard, Moodle)
- Multi-tier or networked supply chain variants beyond the classic four roles
- Instructor-authored custom scenarios
- Institutional SSO, procurement and invoicing workflows
- Anything multi-language

## Risks and Open Questions

Stated plainly, because investors find these anyway.

1. **The competition is free and competent.** Several maintained browser versions exist at zero cost. Our answer is that they solve arithmetic, not repetition — but that answer has not been tested against a buyer yet.
2. **The core thesis may be wrong.** The documented complaint is that the game is fragile and opaque, *not* that people cannot find four players. If a better one-shot experience is enough, the AI investment is over-engineering and a cheaper competitor wins.
3. **The educator who wrote the obituary built his own replacement** — with automated mechanics, variable demand and better feedback, and no AI at all. That is a live proof that the simpler product may satisfy the need.
4. **Unit economics of AI agents are unproven.** Every solo replay costs model inference. The strategy depends on replays being frequent *and* cheap, which pull against each other.
5. **Institutional sales are slow.** Budget cycles, procurement and possibly tender. A model built on institutional revenue has a long first-cash timeline.
6. **Positioning is not yet settled** — see below.

**Open questions for the founder**
- **Positioning.** `[ASSUMPTION] This brief is written toward "repetition and explanation are the wedge; AI agents are what make repetition possible." The alternative framing — "the beer game, finally without friction," with bots as a convenience feature — is safer but far more crowded. This choice shapes the PRD, the architecture and the pitch. It needs an explicit decision.`
- Product name.
- Price points, both tiers.
- Feature-by-feature competitive verification.
- Market sizing: how many courses actually run this exercise, and where.

## Vision

Start by saving one exercise. The beer game is the wedge because it is famous, taught worldwide, and visibly failing — a specific, provable problem with a named buyer.

But the pattern generalises. Business education is full of multi-player simulations that teach something real and are dying of the same disease: they need N people in a room, so they run once, so nobody learns them properly. Negotiation exercises. Market-entry games. Prisoner's-dilemma variants. Every one of them becomes individually replayable the moment credible AI counterparts exist.

In three years, the ambition is to be the platform where experiential business simulations stop being annual events and become practice — something a student does repeatedly until the intuition is theirs. The beer game is how we prove it works.
