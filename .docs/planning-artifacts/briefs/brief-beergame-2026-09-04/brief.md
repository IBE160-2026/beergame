---
title: "Product Brief: beergame"
status: final
created: 2026-09-04
updated: 2026-10-29
audience: investors and stakeholders
who: BIPA
---

# Product Brief: beergame

> **Working name.** "beergame" is the repo name, not a product name. Naming is an open item — see Open Questions.

## Executive Summary

The MIT Beer Distribution Game has taught supply chain dynamics for sixty years, and it is quietly disappearing from classrooms. Not because the lesson stopped mattering — the bullwhip effect is more relevant after five years of supply shocks than it ever was — but because the delivery is broken. In June 2026 an educator writing in *Times Higher Education* declared that the game "may have had its last orders": slow to run, surprisingly fragile, mechanically distracting, and, most damning of all, students finish a session unable to explain how their own decisions produced the outcome they just lived through.

We are rebuilding it as a browser-based product that works on a laptop, an iPad or a phone — and that removes the constraint underneath every one of those complaints: the requirement that four people sit down together at the same hour. AI opponents fill any empty role, which turns a once-per-semester group event into something a single student can replay as many times as it takes for the pattern to click. The opponents are LLM agents by default, with simple rule-based bots available as a lecturer setting where cheap, comparable results matter more than realism.

Our bet, stated as a bet: **the product is the explanation, not the opponents.** After every run, an AI debrief walks through the student's own decisions and why they produced the outcome. Whether repetition plus that debrief actually teaches students more than one good session is untested. It is the first thing this venture has to prove, and the first classroom is the founder's own: he teaches the course this ships into.

Lecturers set up classes and run live multiplayer sessions the way they always have. Students replay solo between sessions. Cheap per student, licensed at institutional rates to schools.

## The Problem

The game is failing in practice, and the failures are documented rather than assumed. From the *Times Higher Education* account of running it:

- **The mechanics eat the lesson.** "The effort required to run the game can end up distracting from the bigger picture." Students spend the hour moving tokens and doing arithmetic instead of watching a supply chain oscillate.
- **Students cannot explain their own outcome.** "Few could clearly explain how their decisions had led them there." This is the expensive one. The game runs, the bullwhip appears, and the insight does not land.
- **It is slow and it breaks.** "Slow to run and proves surprisingly fragile" — a small bookkeeping error in orders or inventory distorts the result, and the distortion is invisible until the debrief makes no sense.
- **It is predictable.** Fixed demand patterns let students anticipate outcomes rather than react to them.

Underneath all four sits a constraint: **in the classic format you get one attempt.** Four people, one demand curve, one slot in the timetable. Asking "what if I had not panic-ordered in week six?" costs another four humans and another hour.

The status quo is that lecturers either run a fragile manual session, adopt a free browser version, or drop the exercise. The *Times Higher Education* author chose to build a replacement himself. That is the cost of the status quo: the people who care most about the exercise are abandoning it.

## Why Now

1. **The decline is now on the record**, not just felt. A supply chain educator published his reasons for abandoning the game and building a replacement. `[ASSUMPTION] One published account is a signal, not a trend. It needs corroboration — a second published source, or a handful of lecturer interviews.`
2. **LLM opponents are now cheap enough to be viable, but not yet proven as teaching opponents.** Modelled cost is a few cents per game on small models; no published figure exists, so this is our arithmetic. Published research shows LLM agents are myopic in human-like ways but unstable from run to run: default configurations varied by 26–52% between runs and guardrails brought that to about 12–13%. Whether LLM agents play like humans was not measured.
3. **The free field has moved, and the novelty is narrower than we first thought.** Bot-filled roles and solo replay already exist: En Dash (free, solo against AI roles, replay, scripted debrief), transentis, Zensimu and Forio's Root Beer Game all fill empty seats, mostly with one-line ordering rules. What no maintained product is documented as offering, as of 2026-10-26, is LLM-driven opponents alongside a human seat, or an LLM-generated debrief at decision level. `[ASSUMPTION] Verified from public pages and client code, not by hands-on play. Multiplayer bots at En Dash and the bots at Skill Dynamics are unseen.`

## The Solution

A web application, responsive across desktop, tablet and phone, with accounts and persistent history.

**For lecturers.** Create a class, invite or roster students, launch a live session, watch it unfold, and run a debrief built from real data rather than recollection. Any unfilled role is taken by an AI opponent, so a session starts on time with the students who actually showed up. Lecturers choose the opponent type per class (LLM or rule-based) and the demand pattern (fixed series, step or random). A shared per-class seed makes live sessions comparable.

**For students.** Play solo against AI opponents whenever they like, as often as they like. Demand varies between runs, so the answer cannot be memorised. After each run, an AI debrief walks through the decisions: here is where you over-ordered, here is what it cost four weeks later, here is what the other roles saw when you did it. Numbers in the debrief are computed in code from the decision log; the LLM only narrates them.

**The core move is repetition plus explanation.** One session shows that the bullwhip effect exists. The hypothesis is that repeated play with a decision-level debrief teaches why your own instincts cause it. No study separates repetition from debrief, so we treat this as a hypothesis to measure, not a fact.

## What Makes This Different

Honest version, because the alternative gets found out in due diligence:

- **The moat is not the simulation.** Beer game mechanics are sixty years old and public.
- **The moat is not bot-filled seats.** Competitors, mostly free, already do that.
- **The moat is not the AI model.** Any competitor can call the same providers.
- **The position we can defend is the explanation layer**: documented opponent personas, per-run demand variation, a decision-level debrief, and lecturer analytics built on a logged decision history. Repetition is partly delivered by others already; explanation is what remains open. If the debrief is not clearly better than a scripted one, positioning B loses its edge.
- **The near-term unfair advantage is distribution and dogfooding**: a founder who teaches the course and ships into his own classroom before selling to anyone else.

**The honest risk:** several competent competitors are free, and the closest one, En Dash, is actively built.

## Who This Serves

**The lecturer (primary buyer-influencer).** Teaches supply chain, operations or logistics. Wants the exercise to land without spending the hour as a referee. Success looks like a debrief where students explain the mechanism back to them.

**The student (primary user).** Needs to actually understand bullwhip, not just witness it once. Success looks like being able to replay until the causal chain is obvious — on the bus, on an iPad, at 23:00 before an exam.

**The institution (payer).** A department or business school buying for a cohort. Success looks like a defensible line item: measurable engagement, curriculum fit, no IT burden.

## Business Model

Two-tier, deliberately asymmetric:

- **Students: cheap.** Low enough to be an impulse decision against free alternatives. `[ASSUMPTION] Price point not yet set.`
- **Institutions: premium.** Class management, cohort analytics, roster integration and support. `[ASSUMPTION] Price point and packaging not yet set.`

Market anchors: free is the floor (transentis, En Dash); Responsive eBeer lists $10–20 per student; Forio sells at $168 per person, the ceiling.

The strategic logic: students are the most price-resistant segment and the competition is free, so the student tier is an adoption channel more than a revenue line. Revenue concentrates on institutions. `[ASSUMPTION] This reading is inferred from "cheap student, expensive school" and should be confirmed.`

## Success Criteria

`[ASSUMPTION] Targets below are placeholders — the shape is proposed, the numbers need your judgement.`

**Learning (the claim the product rests on)**
- Median solo replays per student per course > 3. If students play once and stop, the core thesis is wrong. This is the threshold the first course will measure.
- Students can explain the causal chain behind their outcome. In the founder's first course we log replays per student and collect a simple written explanation task. We do not run a split-cohort test in semester one. A proper design (single session vs replay vs replay plus AI debrief, with a pre/post test and transfer to an unseen demand pattern) belongs in the PRD.
- If replays stay low or explanations do not improve, the fallback is a debrief-first product with simple bots, not a stronger bot engine.

**Product**
- A lecturer can go from signup to a running class session in under 10 minutes, unaided.
- Sessions start on time with fewer than four humans present.

**Business**
- First paying institution outside the founder's own. This is the real validation milestone.
- Cost per AI-driven game session stays below the student price point. Replays that reuse recorded decisions call no model.

## Scope

**In, for the first version**
- Accounts and authentication
- Lecturer-created classes and live multiplayer sessions
- AI opponents filling any unoccupied role, LLM by default with a rule-based option per class
- Full single-player mode against AI opponents
- Variable demand between runs, with a lecturer-selectable pattern and per-class seed
- Post-game debrief with per-role decision history, computed in code and narrated by an LLM
- Logging of every decision with seed, model and prompt version
- Responsive web: desktop, tablet, phone

**Explicitly out of the first version**
- Native apps
- LMS integration (Canvas, Blackboard, Moodle)
- Multi-tier or networked supply chain variants beyond the classic four roles
- Instructor-authored custom scenarios
- Institutional SSO, procurement and invoicing workflows
- Trained reinforcement-learning opponents
- Anything multi-language

## Risks and Open Questions

Stated plainly, because investors find these anyway.

1. **The competition is free and competent, and closer than we thought.** Several maintained browser versions already offer bot-filled roles, solo play and a scripted debrief at no cost. Our edge is the quality of the explanation, which has not been tested against a buyer.
2. **The core thesis may be wrong.** Nothing published separates the effect of repetition from the effect of a good debrief, and one study found repetition raised performance without insight. A good one-shot debrief may be enough, in which case the replay infrastructure is over-engineering.
3. **The educator who wrote the obituary built his own replacement** with automated mechanics, variable demand and better feedback, and no AI at all. That is live proof that the simpler product may satisfy the need.
4. **Unit economics are modelled, not measured.** A game costs cents on small models, but reasoning-length outputs, retries and price changes can move it by an order of magnitude. A prototype that logs tokens and invalid orders will settle this.
5. **Reproducibility is a design constraint.** No LLM vendor guarantees deterministic output, and some current models reject temperature and seed settings. Lecturers who need comparable cohort results must choose rule-based opponents. Whether lecturers actually need identical results is unknown; interviews are needed.
6. **The AI debrief can be wrong.** LLMs can explain a log incorrectly or invent causes. Mitigation: compute every number in code, let the model only narrate, and have the student attempt their own explanation first.
7. **Institutional sales are slow.** Budget cycles, procurement and possibly tender. First cash is far off while inference cost starts on day one. Institutional buyers will also ask for a data-processing agreement.

**Open questions for the founder**
- **Positioning.** Decided: B, repetition plus explanation, carried as an untested hypothesis. See the fallback under Success Criteria.
- Product name.
- Price points, both tiers.
- Hands-on checks of En Dash multiplayer bots, Skill Dynamics and Zensimu solo.
- Market sizing: how many courses actually run this exercise, and where.

## Vision

Start by saving one exercise. The beer game is the wedge because it is famous, taught worldwide, and visibly failing — a specific, provable problem with a named buyer.

But the pattern generalises. Business education is full of multi-player simulations that teach something real and are dying of the same disease: they need N people in a room, so they run once, so nobody learns them properly. Negotiation exercises. Market-entry games. Prisoner's-dilemma variants. Every one of them becomes individually replayable the moment credible AI counterparts exist.

In three years, the ambition is to be the platform where experiential business simulations stop being annual events and become practice — something a student does repeatedly until the intuition is theirs. The beer game is how we prove it works.
