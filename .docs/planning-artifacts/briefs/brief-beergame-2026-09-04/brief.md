---
title: "Product Brief: beergame"
status: final
created: 2026-09-04
updated: 2026-11-05
audience: investors and stakeholders
who: BIPA
---
# Product Brief: beergame

> **Working name.** "beergame" is the repo name, not a product name. Naming is an open item — see Open Questions.

## Executive Summary

The MIT Beer Distribution Game has taught supply chain dynamics for sixty years, and it is quietly disappearing from classrooms. Not because the lesson stopped mattering — the bullwhip effect is more relevant after five years of supply shocks than it ever was — but because the delivery is broken. In June 2026 an educator writing in *Times Higher Education* declared that the game "may have had its last orders": slow to run, surprisingly fragile, mechanically distracting, and, most damning of all, students finish a session unable to explain how their own decisions produced the outcome they just lived through.

We are rebuilding it as a Norwegian-language web product, mobile-first and equally at home on a classroom laptop, that runs the whole exercise for a course of hundreds and removes the constraint underneath every one of those complaints: the requirement that four people sit down together at the same hour. AI players take any empty seat and step in for a student who holds the others up, so a group can play on its own schedule within a deadline and no game is left unfinished. The AI players are LLM agents by default, with simple rule-based bots available as a lecturer setting.

Our bet, stated as a bet: **the product is working AI players plus the explanation.** Bot-filled seats are common; LLM players that behave well enough to teach with are not, and making them work is the first thing we build. After the class game, an AI debrief walks through the group's decisions and why they produced the outcome. Each student then plays a harder second round alone and takes an individual test. Whether this teaches students more than one good session is untested. It is the first thing this venture has to prove, and the first classroom is the founder's own: the founder teaches the course this ships into.

Lecturers invite a class, set the game up and watch every game on one screen. The first version sets no formal grades: the AI gives feedback that does not count, and each student gets a PDF report for approval or use in other systems. Licensed at institutional rates to schools.

## The Problem

The game is failing in practice, and the failures are documented rather than assumed. From the *Times Higher Education* account of running it:

- **The mechanics eat the lesson.** "The effort required to run the game can end up distracting from the bigger picture." Students spend the hour moving tokens and doing arithmetic instead of watching a supply chain oscillate.
- **Students cannot explain their own outcome.** "Few could clearly explain how their decisions had led them there." This is the expensive one. The game runs, the bullwhip appears, and the insight does not land.
- **It is slow and it breaks.** "Slow to run and proves surprisingly fragile" — a small bookkeeping error in orders or inventory distorts the result, and the distortion is invisible until the debrief makes no sense.
- **It is predictable.** Fixed demand patterns let students anticipate outcomes rather than react to them.

Underneath all four sits a constraint: **in the classic format you get one attempt.** Four people, one demand curve, one slot in the timetable. Asking "what if I had not panic-ordered in week six?" costs another four humans and another hour.

The status quo is that lecturers either run a fragile manual session, adopt a free browser version, or drop the exercise. The *Times Higher Education* author chose to build a replacement. That is the cost of the status quo: the people who care most about the exercise are abandoning it.

## Why Now

1. **The decline is now on the record**, not just felt. A supply chain educator published the reasons for abandoning the game and building a replacement. `[ASSUMPTION] One published account is a signal, not a trend. It needs corroboration — a second published source, or a handful of lecturer interviews.`
2. **LLM players are now cheap enough to be viable, but not yet proven for teaching.** Modelled cost is a few cents per game on small models; no published figure exists, so this is our arithmetic. Published research shows LLM agents are myopic in human-like ways but unstable from run to run: default configurations varied by 26–52% between runs and guardrails brought that to about 12–13%. Whether LLM agents play like humans was not measured.
3. **The free field has moved, and the novelty is narrower than we first thought.** Bot-filled roles and solo replay already exist: En Dash (free, solo against AI roles, replay, scripted debrief), transentis, Zensimu and Forio's Root Beer Game all fill empty seats, mostly with one-line ordering rules. What no maintained product is documented as offering, as of 2026-10-26, is LLM-driven players alongside a human seat, or an LLM-generated debrief at decision level. `[ASSUMPTION] Verified from public pages and client code, not by hands-on play. Multiplayer bots at En Dash and the bots at Skill Dynamics are unseen.`

## The Solution

A web application with accounts by invitation, Norwegian throughout, built for the phone and equally usable on a classroom laptop.

**For lecturers.** Register a class, upload the student list from Canvas and send invitations weeks ahead. The system splits students at random into groups of up to four with random roles, and fills any empty seat with an AI player. Lecturers can leave the classic settings as they are or change every game parameter for the whole class, including delays, demand, capacity and what each role may see of its neighbours. They schedule lab hours, watch all games and whom each one is waiting for on one screen, and message students. Lecturers choose the AI player type per class (LLM or rule-based), and can make the exercise obligatory for the course. Obligation is met by completing the steps, never by an AI judgement. Afterwards they get full insight into each game, a class report and statistics across classes.

**For students.** Play the class game with the group, in a lab hour or on the bus, with all four roles ordering in the same week and a clear view of whom the game waits for. A group can pause and agree when to continue. A student who holds the others up is replaced by an AI player and can take the seat back; if nobody plays, nothing happens until the deadline. Then comes the sequence that carries the lesson: a debrief with the group, where each student first explains what happened in their own words and then sees the data (here is where you over-ordered, here is what it cost four weeks later, here is what the other roles saw when you did it); a short quiz that must be answered correctly; a harder second round alone against AI players; and an individual test with interactive tasks and long answers, some built from the student's own games. Numbers in the debrief are computed in code from the decision log; the LLM only narrates them.

**What counts.** Nothing the AI says counts. The AI gives each student a score and written feedback on the test, with an A–F indication the lecturer or the student can turn on. Each student and lecturer can download a PDF report of the games, the debrief and the test. Formal grading with examiners is planned for version 2, not the first version.

**The core move is repetition plus explanation.** One session shows that the bullwhip effect exists. The hypothesis is that playing again after a decision-level debrief teaches why your own instincts cause it. No study separates repetition from debrief, so we treat this as a hypothesis to measure, not a fact. The first version takes one step of it: one second round for every student. Open-ended replay is left out for now, and the first course asks students whether they wanted more before we build it.

## What Makes This Different

Honest version, because the alternative gets found out in due diligence:

- **The moat is not the simulation.** Beer game mechanics are sixty years old and public.
- **The moat is not bot-filled seats.** Competitors, mostly free, already do that.
- **The moat is not repetition.** Free competitors offer open-ended solo play today, and our first version offers one second round.
- **The moat is not access to the AI model, it is making LLM players work.** Any competitor can call the same providers, but no maintained product is documented as shipping LLM-driven players to learners. The published attempts are research demos with no human seat (GenAI Beer Game) or an abandoned prototype (a Hugging Face Space). Raw LLMs are the problem: unstable between runs, and they tend to optimise better than humans. A smart AI player is acceptable, since the game is a team game with no winners, but a near-perfect one would remove the bullwhip. We make them fit for teaching with a fixed response format and retries, a play guard that compares each weekly order with a sensible and a near-optimal reference and switches the seat to a rule-based player outside the accepted band, fixed prompt versions, full decision logging and a rule-based fallback. `[ASSUMPTION] Not yet demonstrated. A prototype must calibrate the play guard and log run-to-run variation, retries and cost; the first course asks whether students find the AI players plausible.`
- **The position we can defend is working LLM players plus the explanation layer**: documented AI player behaviour, a decision-level debrief, and lecturer analytics built on a logged decision history. If the debrief is not clearly better than a scripted one, positioning B loses its edge.
- **The near-term unfair advantage is distribution and dogfooding**: a founder who teaches the course and ships into their own classroom before selling to anyone else.

**The honest risk:** several competent competitors are free, and the closest one, En Dash, is actively built.

## Who This Serves

**The lecturer (primary buyer-influencer).** Teaches supply chain, operations or logistics, often to hundreds of students. Wants the exercise to land without spending weeks as a referee. Success looks like every game finishing and students able to explain the mechanism back.

**The student (primary user).** Needs to actually understand bullwhip, not just witness it once. Success looks like being able to explain the causal chain behind their own orders, having worked through it on the bus, on an iPad, at 23:00 before the deadline.

**The institution (payer).** A department or business school buying for a cohort. Success looks like a defensible line item: measurable engagement, curriculum fit, no IT burden.

## Business Model

Licensed to institutions. The first version has no payment in the product and no individual sign-up; licences are handled by contract, and students come in through a lecturer's invitation.

The earlier two-tier idea remains open for later:

- **Students: cheap.** Low enough to be an impulse decision against free alternatives. `[ASSUMPTION] Price point not yet set.`
- **Institutions: premium.** Class management, cohort analytics and support. `[ASSUMPTION] Price point and packaging not yet set.`

Market anchors: free is the floor (transentis, En Dash); Responsive eBeer lists $10–20 per student; Forio sells at $168 per person, the ceiling.

The strategic logic: students are the most price-resistant segment and the competition is free, so revenue concentrates on institutions. Norwegian procurement rules apply to contracts from NOK 500,000, which is a reason to keep early licences below that level.

## Success Criteria

`[ASSUMPTION] Targets below are placeholders — the shape is proposed, the numbers need your judgement. The PRD holds the full list.`

**Learning (the claim the product rests on)**

- Students order better in the second round: at least 60% amplify demand less than in the class game, measured against a rule-based reference. The brief's earlier kill bar, median solo replays above 3, cannot be measured in the first version, which has one second round. The first course asks instead whether students wanted another round.
- Students can explain the causal chain behind their outcome. On a random sample, we compare each student's explanation in the debrief with the same question in the test, scored by the founder with a second scorer on a share. A short task on stocks and flows before the game is repeated in the test. We do not run a split-cohort test in semester one, so this shows the level students reach, not what caused it.
- LLM players work for teaching. The play guard watches them while a class runs, so no end-of-pilot rule makes rule-based players the default; lecturers can choose rule-based players for any class. Run-to-run variation and student plausibility are reported.
- These are conditions for launch to other schools, with targets fixed before the first order. If explanations hold up but the second round adds little, the fallback is a debrief-first product with simple bots, not a stronger bot engine. If neither shows, we do not launch and re-examine the thesis.

**Product**

- A lecturer who has used the product once can create a class session in under 10 minutes, unaided.
- Every class game finishes by its deadline, even when students disappear.
- The AI feedback holds up in a control test against human scoring before real students rely on it.

**Business**

- First paying institution outside the founder's own. This is the real validation milestone.
- AI cost stays at or below USD 0.10 per class game and USD 0.50 per student per class session. This is modelled, not measured.

## Scope

**In, for the first version**

- Accounts by invitation; admin, lecturer, assistant lecturer and student roles
- Classes from an uploaded student list, random groups and random roles
- Class games played on the group's own schedule within deadlines, with lab hours
- AI players in any empty seat and when a student holds the others up, a pause for the group, LLM by default with a rule-based option per class, and a play guard
- Classic default settings, all game parameters settable by the lecturer, including capacity and information visibility
- Group or personal debrief with the student's own explanation, computed in code and narrated by an LLM, then a quiz that must be answered correctly
- One harder second round alone against AI players, with a short AI walkthrough
- Individual test with non-counting AI feedback and an optional A–F indication
- PDF report per student; completion list; optional obligatory setting
- Lecturer overview, messages, class report and statistics across classes
- Logging of every decision with seed, model, provider and prompt version
- Norwegian only; mobile-first web, equally usable on a laptop

**Explicitly out of the first version**

- Formal grading: examiners, grades, grading deadlines, appeals (planned for version 2)
- Open-ended or voluntary extra replays
- Communication between players, and replay in the same group (planned for version 2)
- Native apps
- LMS integration (Canvas, Blackboard, Moodle) and Feide login
- Multi-tier or networked supply chain variants beyond the classic four roles
- Payment in the product, procurement and invoicing workflows
- Trained reinforcement-learning players
- Languages other than Norwegian

## Risks and Open Questions

Stated plainly, because investors find these anyway.

1. **The competition is free and competent, and closer than we thought.** Several maintained browser versions already offer bot-filled roles, solo play and a scripted debrief at no cost. Our edge is working LLM players and the quality of the explanation, neither of which has been tested against a buyer.
2. **The core thesis may be wrong, and the first version tests only part of it.** Nothing published separates the effect of repetition from the effect of a good debrief, and one study found repetition raised performance without insight. A good one-shot debrief may be enough. With one second round, the first version cannot show whether more repetition teaches more.
3. **The educator who wrote the obituary built a replacement** with automated mechanics, variable demand and better feedback, and no AI at all. That is live proof that the simpler product may satisfy the need.
4. **Unit economics are modelled, not measured.** A game costs cents on small models, but reasoning-length outputs, up to five retries per order, a higher effort setting and price changes can move it by an order of magnitude. A prototype that logs tokens and invalid orders will settle this.
5. **Reproducibility is a design constraint.** No LLM vendor guarantees deterministic output, and some current models reject temperature and seed settings. Lecturers who need comparable cohort results must choose rule-based players. Whether lecturers actually need identical results is unknown; interviews are needed.
6. **The AI can be wrong, and no human checks the feedback.** LLMs can explain a log incorrectly or invent causes. Mitigation: compute every number in code, let the model only narrate, have the student explain before seeing the data, say plainly that the feedback counts for nothing, and check it in a control test.
7. **AI regulation may catch up with the feedback.** AI that proposes grades is likely high-risk under the EU AI Act from December 2027, even with human review, which is one reason formal grading waits. Non-counting feedback stays outside only while no one grades from it, and an A–F indication makes that harder. Students also may not work through a test that does not count; the obligatory setting addresses that, and an unsupervised test can be answered with outside AI tools.
8. **Institutional sales are slow.** Budget cycles, procurement and possibly tender. First cash is far off while inference cost starts on day one. Institutional buyers will ask for a data-processing agreement and an impact assessment, and Norwegian institutions will expect Feide and Canvas integration, which the first version leaves out.

**Open questions for the founder**

- **Positioning.** Decided: B, repetition plus explanation, carried as an untested hypothesis. The first version tests the explanation and one repetition. See the fallback under Success Criteria.
- Product name.
- Price points, and whether students ever pay directly.
- Hands-on checks of En Dash multiplayer bots, Skill Dynamics and Zensimu solo.
- Market sizing: how many courses actually run this exercise, and where.

## Vision

Start by saving one exercise. The beer game is the wedge because it is famous, taught worldwide, and visibly failing — a specific, provable problem with a named buyer.

But the pattern generalises. Business education is full of multi-player simulations that teach something real and are dying of the same disease: they need N people in a room, so they run once, so nobody learns them properly. Negotiation exercises. Market-entry games. Prisoner's-dilemma variants. Every one of them becomes individually replayable the moment credible AI counterparts exist.

In three years, the ambition is to be the platform where experiential business simulations stop being annual events and become practice — something a student does repeatedly until the intuition is theirs. The beer game is how we prove it works.
