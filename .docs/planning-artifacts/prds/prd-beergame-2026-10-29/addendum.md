---
title: "PRD addendum: beergame"
status: final
created: 2026-11-02
updated: 2026-11-05
---

# PRD addendum: beergame

Material that informs the PRD but belongs to architecture, UX or later decisions. The PRD (`prd.md`) is authoritative; this file holds the reasoning and the numbers behind it.

## A. AI players: numbers and mechanics (for architecture)

Source: technical research 2026-10-26 (`research/technical-ai-agent-cost-per-beer-game-session-2026-10-26/research.md`).

- **Load model (unverified):** 3 AI Seats × 36 Weeks = 108 calls per Replay, or a one-Student Class game; a full Class game has no AI Seats. About 2,000 input tokens (1,200 cacheable) and 150 output tokens per call without reasoning. A Takeover can make all four Seats AI (144 calls). Guided Weeks reduce this in a Class game; a default Replay has 30 to 40 Weeks and no Guided Weeks (up to 120 calls). Debrief, Debrief quiz explanations, Adapted items and AI assessment are modelled only as one Debrief call.
- **Modelled cost per Game, uncached/cached:** Haiku 5.5 about USD 0.030/0.018; gpt-5-mini 0.086/0.057; Sonnet 5.5 0.59/0.35; DeepSeek V4.1 Flash about 0.016 on third-party endpoints, excluding reasoning, retries, caching and fees, with region and quality unknown (PRD §6.1 excludes DeepSeek's own API; open-weight models only through EU hosts). OpenRouter fee ×1.055–1.08. Figures are from 2026-10-26 to 2026-10-29, and the re-check is overdue.
- **Tail risk:** reasoning tokens multiply cost about 4.4× (Haiku about USD 0.13 per Game). The research recommends reasoning none or low; the default Effort level is set after the prototype. `max_tokens` must leave room or calls return empty.
- **Cost with retries and Effort (our arithmetic, Haiku 5.5 EU price with 8% fee, USD per Game):** 150 output tokens: 0.035 with 3 AI Seats, 0.047 with 4. 2,000 output tokens: 0.154 with 3, 0.205 with 4. With 25% invalid per attempt, multiply by 1.33; all 5 retries, by 6. Break-even at USD 0.10 with 4 AI Seats is about 770 output tokens per call.
- **Latency:** no reliable time-to-first-token figure. AI Seats order in parallel. Placeholder gate p95 ≤ 8 s (PRD NFR-2).
- **Quality evidence:**
  - Run-to-run variation of total cost is 26–52% at default settings, 12% on one model with a spend cap at 2× total customer demand and a budget rule, and 13% after post-training.
  - Some models broke ordering rules in more than 25% of decisions, and majority voting did not reduce variation.
  - Reasoning models reached 50–80% below student teams (a weak benchmark), and older models out of the box cost about twice as much, so LLMs may dampen the bullwhip or amplify it erratically. A new preprint also lists LLM agents amplifying orders.
  - Bot results must not be cited as human effects. Human-likeness and student-perceived credibility are unmeasured (issue #11).
- **Reproducibility:** no provider guarantees determinism; current Claude models reject temperature and no seed was found; OpenRouter silently ignores unsupported parameters and may fall back to another provider. Hence: Rule-based players for comparable Class sessions, log everything, pin model per Class session (PRD FR-67, FR-68).
- **Model switcher:** reference code in `research/.../model-switcher/model_switcher.py`; all thresholds are placeholders (invalid-order Wilson 95% upper bound ≤ 2%, behaviour inside a fidelity band, p95 ≤ 8 s, switch only if ≥ 15% cheaper, 7-day cooldown, 5% canary). Weekly automatic switching pays off only above about 260 Games per week (issue #9).
- **Rule-based player:** Sterman (1989) anchoring-and-adjustment heuristic. The fitted parameters have not been retrieved from the primary source (issue #8); values from calculator sites must not be used.
- **Prompt design (founder, 2026-11-05):** the prompt sent on an AI player's turn holds the game rules implicitly, as a supply chain manager's job, and the Seat's own data plus what arrives from downstream and upstream.
  - The model is not told it plays a game, that there are four Seats, or that Weeks advance after all Seats have ordered. The Beer Game is a team game with no winners; the model is asked for the best Order given the information.
  - The prompt is calibrated by testing before launch.
  - The Effort level (thinking level) is a Lecturer setting (PRD FR-78). Reasoning raises cost about 4.4× (above) and latency, so the 8 s limit and cost envelope need testing per Effort level.
- **Order format:** every request asks for JSON with a schema; non-matching answers are retried at most 5 times, then the Rule-based Order is used (PRD FR-32). Worst case is 6 calls for one Order, which matters for both cost and the latency limit.
- **Play guard design (PRD FR-79):** per Week and Seat the system computes (i) the Rule-based Order and (ii) a near-optimal Order, which may use information the LLM never sees (full chain state and demand), and records the LLM Order relative to both. Seat-level statistics over a window of Weeks (95% confidence interval was the founder's example) decide the switch. Caveats for the architect:
  - A Seat has only 36 Weeks and the Weeks are autocorrelated, so a confidence interval on a mean is weak. Consider a rolling window and a minimum number of Weeks before the guard can switch.
  - The Rule-based reference itself needs primary-source parameters (issue #8).
  - How the near-optimal reference is computed and the distance measure are to be set in the prototype (issues #9, #11).
  - Fallback Orders equal the lower reference, so they are left out of the statistics.
  - A higher Effort level may push Seats toward the 5% limit, so test it against the guard.
  - Add human Class game data as a check after the pilot.

## B. Game mechanics reference (for UX and architecture)

- **Week sequence (normative in PRD FR-26):** on opening, receive incoming delivery into inventory → amount to ship = incoming order + backlog → ship the smaller of inventory and amount to ship (and capacity), the rest becomes backlog → show the result → all Seats place Orders → charge costs on end-of-Week balances → slots advance. Inventory and backlog are never both positive, except on a capped Seat.
- **Default slot layout (2/2/2, 4 per slot).** An Order placed in Week t reaches the upstream Seat in Week t+2; a shipment sent in Week t arrives in Week t+2.

  | Seat | Incoming order from | Order slots | Incoming goods from | Goods slots |
  |---|---|---|---|---|
  | Retailer | Customer, no delay | 2 | Wholesaler | 2 shipping |
  | Wholesaler | Retailer | 2 | Distributor | 2 shipping |
  | Distributor | Wholesaler | 2 | Factory | 2 shipping |
  | Factory | Distributor | 2 | Own production | 2 production |

  Units at the start: 48 in inventory, 24 in shipping slots, 8 in production slots, 80 in all; order slots hold orders, not units. Check: units on hand and in transit = 80 + units entered production − units delivered to customers. Reference trace: constant demand 4 and all Orders 4 keep inventory at 12 with no backlog, and cost 6.00 per Seat per Week.
- **Warnings for Lecturer-set values (PRD FR-12).** Link minimum Weeks to delays: if each Seat reacts at once to a Week 5 step, the first Factory-made units reach the Retailer around Week 21 at 2/2/2 and Week 29 at 3/3/3 (our arithmetic).
  - The only capacity value found is 6, an illustration; at 6 with demand 8, backlog grows by 2 a Week.
  - Discrete uniform demand is a design choice, not from a source. A fresh seed gives total demand a standard deviation of about 8.5 units over 36 Weeks, so Replay comparisons are not like for like.
- **Classic values seen across sources:** inventory 12; 4 units per pipeline slot; demand 4 stepping to 8 in Week 5; holding 0.50, backorder 1.00; shipping delay 2 is the verified one; sources disagree on order delay (1 or 2) and production delay (2, 3 or 4); about 36 Weeks played, and the only documented practice, in two sources, tells players 50 Weeks to avoid end-game effects. The PRD tells them no number (FR-14).
  - Other course material uses inventory 15 and pipelines of 5.
  - The founder confirmed the PRD's defaults on 2026-11-05, with an order delay of 2 Weeks and 36 Weeks (there is no advanced preset: the Lecturer decides).
- **Layout learning from earlier planning (2025):** a portrait facility board with goods flowing down and orders flowing up, one editable number per Week, corners for incoming order, incoming delivery, outgoing order and outgoing delivery, inventory in the centre.
  - Superseded in the chosen UX (2026-11-09): the chain runs horizontally on every surface, upstream on the left, goods flowing right toward the Retailer and the customer, and orders flowing left (`../../ux-designs/ux-beergame-2026-11-05/EXPERIENCE.md`).
  - Red/green status alone failed colour-blind users. Label slots as "arrives next week" rather than "Week 1/Week 2", on the order leg too.
  - Other UX inputs: the Factory shows production slots and no upstream; the Retailer shows customer demand and no outgoing pipeline; Wholesaler and Distributor are identical; animation can be skipped, with a table view available; orders as bars with weekly and cumulative toggles; backlog drawn as negative inventory; cumulative cost charts; no large statistics panel.
  - Debrief prompts and test items are written fresh, not copied from these sources.
  - §3 terms are internal: UX settles the Norwegian terms with lecturers, using "debrief" and "etterspørselsmønster" and avoiding "reproducible".
- **Information visibility and capacity (research, 2026-11-05; see `.docs/planning-artifacts/research/domain-beer-game-variants-and-setup-options-2026-11-05/research.md`):**
  - In the one experiment that tested upstream information, only downstream information significantly lowered order variance (80.66 baseline, 55.10 upstream-only, not significant; 30.10 downstream-only). "Upstream" and "downstream" there meant all Seats in that direction, and seeing only one neighbour has not been tested in either direction.
  - Point-of-sale data can distract when demand keeps changing, and no total-cost effect was found. Inventory sharing reduces the bullwhip only partly.
  - Capacity (a weekly maximum shipment per Seat) has one platform precedent and no human evidence.
  - Delay values are disputed in the literature: shipping 2 Weeks verified, order delay 1 or 2, production 2 to 4. The Lecturer therefore sets them (FR-12).
- **Inactivity ladder from earlier planning:** warning → one cautious AI Order → permanent AI. The PRD replaces it with Pause, Takeover only when another Student is waiting, and playout at the Play deadline (FR-36, FR-38, FR-89).
- **Classic debrief sequence:** feelings ("did you feel in control?", "did you blame your neighbours?") → evidence (demand reveal, Orders and inventory per Role) → structure ("structure creates behaviour", delays, Supply line, demand information lost when it travels only as orders). The PRD's Debrief follows this (FR-44, FR-45). A later information-sharing round is a natural follow-up (v2 candidate).
- **Known student misperceptions to target:** ignoring the Supply line; attributing the oscillation to customer demand or neighbours; not seeing the effect of one's own Orders.

## C. Learning measurement detail (issue #6)

- Research recommends three arms: one Class game plus human Debrief / Replay only / Replay plus AI Debrief, with pre/post stock-and-flow items (Sweeney & Sterman bathtub tasks), a scored explanation, and transfer to an unseen Demand pattern. No study found crosses repetition with debrief or tests transfer, partly a retrieval limit.
- The pilot uses the light-touch design in PRD §9.1. A later Class session can randomise Debrief detail within the class. Freeze the model during any study (FR-68). The game helped on information and no-collaboration causes, not on delays or structure, and some gains faded by six weeks, so weight the Debrief and test toward delays and structure. Open reading: Martin 2004 and Fu & Gonzalez 2006 (issue #5); the board-over-screen lead (low confidence).
- The evidence suggests performance (Total cost) and understanding dissociate (Paich & Sterman 1993; Atkins 2002), though no cited study measures both on the same participants, which is why game cost does not count in the AI assessment and SM-C1 exists.

## T. Individual test design (for UX, architecture and writing the question set)

Source: `.docs/planning-artifacts/research/academic-lit-beer-game-test-questions-systems-thinkin-2026-11-05/research.md`. Much of the evidence is thin; confidence is flagged per claim there.

- **Why quantities and consistency.** In Booth Sweeney & Sterman (2000), students who had played the Beer Game scored higher on a stock-flow task (46% vs 33%), but only on parts that reward remembering that it oscillates. They did no better on conservation of material or on consistency between graphs. The direction is confirmed by later papers; the exact numbers come from the conference version.
- **Model for Interactive items.** The Manufacturing Case: orders step from 10,000 to 11,000 a week, 4-week production delay, desired inventory 50,000. Production must overshoot orders, and the overshoot equals the lost inventory (4,000 units). Also: given inflow and outflow, draw the stock. Scoring criteria in the study: equilibrium start, lag, overshoot, area conservation, inventory first falling, then recovering, and consistency.
- **Multiple choice.** Evidence for two-tier items (answer plus reason) is small; a reason tier is optional. No evidence on negative marking.
- **Long answers.** No published rubric for free-text mechanism answers was found, so the Scoring guide is new work. Start from 5–8 coded criteria in the style of the study.
- **AI scoring.** Holistic agreement with humans is moderate (QWK about 0.6 for open-weight models); scoring many traits separately is much worse (0.32–0.41); bias direction differs between studies. This is why FR-54 gives one overall score per answer. A constant offset can be detected on a small sample (often 10 or fewer).
- **Adapted items.** No study of items built from a student's own game was found; they are a design bet. A Student's estimated supply-line weight could be computed from the Decision log but is not scored in v1, since nothing validates it as a measure.
- **Originality and freshness.** The model above is a published task, so items use their own stories and numbers. Refresh the findings on unsupervised exams and LLM grading with the trial in open question 6; the re-check dates have passed.
- **Scoring guide.** Claude drafts the default during implementation and the founder approves it; a Lecturer can edit it for a Class session.

## R. Regulatory detail (for architecture, DPO dialogue and sales)

Source: `research-regulatory.md` in this folder (2026-10-29; not legal advice).

- **EU AI Act Annex III 3(b):** AI that evaluates learning outcomes in tests counting toward a grade is high-risk; the Commission's draft guidelines (May 2026) say human involvement does not change classification and the Art. 6(3) exemption does not apply to profiling.
  - Obligations for Annex III apply from 2 December 2027 (Regulation (EU) 2026/1744). Norway: not yet incorporated in the EEA Agreement; Norwegian bill expected spring 2027.
  - Provider duties if formal grading with an AI proposal is built in v2: risk management, data governance, technical documentation, logging, human oversight, accuracy, quality management, conformity assessment, registration, post-market monitoring.
- **Art. 50:** AI interacting with people must be disclosed at first interaction; the "obvious" exception does not cover games that mix humans and AI. Machine-readable marking of generated text.
- **GDPR:** Institution = controller, beergame = processor, LLM providers and routers = sub-processors needing prior authorisation.
  - Norwegian institutions use NTNU's sector template or the state template for data processing agreements. DPIA is mandatory for evaluating learning in higher education (Datatilsynet list).
  - EU–US Data Privacy Framework valid but under challenge; keep providers swappable and have an exit plan. Anthropic's and OpenRouter's listing is unconfirmed; without it, standard contractual clauses and a transfer impact assessment apply. China has no adequacy decision.
  - Set OpenRouter data collection to deny with zero retention, and confirm whether EU routing needs Business or Enterprise.
  - Buyers will benchmark against Sikt KI: data stays in the EU, no training on user data, reusable agreements.
- **Universal design:** the Norwegian regulation covers digital learning tools; public universities must meet EN 301 549 (= WCAG 2.1 AA). Aim for 2.2 where cheap.
- **Procurement:** regulation applies from NOK 500,000 excluding VAT (from 1 July 2026); national announcement from NOK 1.3 m; EEA rules from NOK 1.63 m for state bodies. Standard contract: SSA-lille sky.
- **Integration expectations:** Feide (OIDC) and Canvas LTI 1.3 are the main ways in for Norwegian higher education; out of v1 by founder decision (PRD §8.2).

## V. Formal grading: design kept for v2

Moved out of v1 by the founder on 2026-11-05 ("alt som har med formell sensur skal ikke med i første versjon"). This is the flow the founder narrated on 2026-11-02, kept so v2 does not start from nothing:

- The Lecturer registers Examiners in advance: an external examiner and the course lecturer. Examiner is its own account role, with access to that Class session's tests only.
- After the Test deadline the AI gives an advisory assessment per Student (rettledende sensur). It is never final.
- Each Examiner enters a proposed grade independently, without seeing the other's. Equal proposals become the joint grade. Different proposals stay open for both, and the system follows up until they agree.
- The system tracks the statutory grading deadline (normally three weeks) and sends reminders.
- The Lecturer sets the grading scale (A–F or Pass/Fail) and thresholds; questions carry weights.
- Students get an email when the joint grade is ready and read it in the app.

Open for v2: appeals and re-grading by new examiners; anonymous grading by candidate number; whether Students with different Adapted items can be graded fairly under the Universities Act (§ 11-6); grade export; a guard against automation bias on the review screen.

Regulation: AI proposing grades on a test that counts is likely high-risk under Annex III 3(b), and human review does not change that (§R). Building the v2 design with an AI proposal means meeting those obligations, or letting Examiners grade without it.

## X. Rejected or deferred alternatives

- **Rule-based players by default** (research recommendation): rejected by the founder on 2026-10-29; LLM players are the differentiator. Kept as an option per Class session and as the fallback inside the Play guard (FR-79).
- **End-of-pilot rule "Rule-based becomes the default if SM-3 is not met":** replaced by the founder on 2026-11-05 with the Play guard, which monitors LLM play while a Class session runs and switches a Seat when its Orders leave the accepted band.
- **LLM players tuned to imitate Students (draft SM-C3):** dropped by the founder on 2026-11-05; a smart AI player is acceptable, and the Play guard's upper limit stops only near-optimal play.
- **Formal grading in v1:** moved to v2 by the founder on 2026-11-05; see §V. v1 has a non-counting AI assessment and PDF Student reports instead.
- **AI as final grader:** rejected for every version.
- **Voluntary extra Replays in v1:** removed by the founder on 2026-11-05. The brief's kill bar (median solo Replays above 3) cannot be measured in v1; PRD SM-1 and SM-10 replace it for now.
- **Explanation as a separate step before the Debrief:** rejected by the founder on 2026-11-05; the Student explains during the Debrief. The research advises explaining before seeing the analysis, so the PRD places the step before the demand reveal.
- **Supervised Individual test, at least in the pilot** (research recommendation R5): rejected by the founder on 2026-11-05; the test is unsupervised, with Interactive items that are harder to solve with outside AI tools. The research does not show that they are, so the PRD tests it before the pilot (open question 6).
- **One sitting with a 60-minute limit as the default:** replaced by the founder on 2026-11-05; Students can come back as often as they want until the Test deadline, and one sitting with a time limit remains a Lecturer setting.
- **Join by code without accounts** (competitor norm): rejected because Student reports, Replays and Cross-class statistics need persistent identities.
- **Documented personas** (brief): dropped; LLM players use one supply-chain-manager prompt, and FR-33 documents the AI player types.
- **Optional steps:** the flow is fixed in v1; a Lecturer cannot leave out the Replay or the test.
- **Student tier as an adoption channel** (brief): out of v1. The cost per Replay also decides whether SM-10 can lead to voluntary Replays in v2.
- **Lecturer advancing a Week by hand:** not adopted; manual Takeover and the shorter Lab-hour limit cover live pacing.
- **Telling players a false horizon** (the only documented practice): rejected by the founder on 2026-11-05; Students and AI players are told to act as if the business continues.
- **Feide and Canvas in v1:** deferred by the founder.
- **Automatic Takeover after 24 hours in every case:** replaced by the founder on 2026-11-05 with Pause (FR-89), because it would take over a group that had simply agreed to continue another day.
- **Order bound of 2× recent incoming orders:** dropped on 2026-11-05, as untested and able to freeze a Seat; the maximum Order in FR-12 is the sanity check.
- **Customer demand visible to every Seat:** dropped on 2026-11-05, since it makes the Debrief's mechanism false.
- **Randomising the Replay's AI mode inside the pilot** (review suggestion): not taken up; it is a split-group design the first semester has no room for, and a later Class session can do it.
- **Player chat:** deferred to v2; in v1 the classic no-talking rule holds.
- **From earlier planning (2025), deliberately not carried over:** free tier, student subscriptions, Stripe billing, white-label, certificates, public game rooms, pause/reset of all games.
