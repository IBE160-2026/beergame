---
title: "PRD addendum: beergame"
status: draft
created: 2026-11-02
updated: 2026-11-05
---

# PRD addendum: beergame

Material that informs the PRD but belongs to architecture, UX or later decisions. The PRD (`prd.md`) is authoritative; this file holds the reasoning and the numbers behind it.

## A. AI players: numbers and mechanics (for architecture)

Source: technical research 2026-10-26 (`research/technical-ai-agent-cost-per-beer-game-session-2026-10-26/research.md`), extracted in `extract-research-tech-learning.md`.

- **Load model (unverified):** 3 AI Seats × 36 Weeks = 108 calls per Class game; about 2,000 input tokens (1,200 cacheable) and 150 output tokens per call without reasoning. A Replay has the same load. A Takeover can make all four Seats AI (144 calls).
- **Modelled cost per Game, uncached/cached:** Haiku 5.5 about USD 0.030/0.018; gpt-5-mini 0.086/0.057; Sonnet 5.5 0.59/0.35; DeepSeek V4.1 Flash about 0.016 (but see §R: DeepSeek's own API is excluded). OpenRouter fee ×1.055–1.08.
- **Tail risk:** reasoning tokens multiply cost about 4.4× (Haiku about USD 0.13 per Game). Reasoning off by default; `max_tokens` must leave room or calls return empty.
- **Latency:** no reliable time-to-first-token figure. AI Seats order in parallel. Placeholder gate p95 ≤ 8 s (PRD NFR-2).
- **Quality evidence:** run-to-run variation of total cost 26–52% at default settings, about 12–13% with an order cap of 2× customer demand (one model only); some models broke ordering rules in more than 25% of decisions; majority voting did not reduce variation; LLMs tend to beat human cost by 50–80%, which may dampen the bullwhip. Human-likeness and student-perceived credibility are unmeasured (issue #11).
- **Reproducibility:** no provider guarantees determinism; current Claude models reject temperature/seed; OpenRouter silently ignores unsupported parameters and may fall back to another provider. Hence: Rule-based players for comparable Class sessions, log everything, pin model per Class session (PRD FR-67, FR-68).
- **Model switcher:** reference code in `research/.../model-switcher/model_switcher.py`; all thresholds are placeholders (invalid-order Wilson 95% upper bound ≤ 2%, behaviour inside a fidelity band, p95 ≤ 8 s, switch only if ≥ 15% cheaper, 7-day cooldown, 5% canary). Weekly automatic switching pays off only above about 260 Games per week (issue #9).
- **Rule-based player:** Sterman (1989) anchoring-and-adjustment heuristic. The fitted parameters have not been retrieved from the primary source (issue #8); values from calculator sites must not be used.

## B. Game mechanics reference (for UX and architecture)

- **Week sequence:** receive incoming delivery into inventory → amount to ship = incoming order + backlog → ship the smaller of inventory and amount to ship, the rest becomes backlog → place Order → pipelines advance. Inventory and backlog are never both positive.
- **Classic values seen across sources:** inventory 12; 4 units per pipeline slot; demand 4 stepping to 8 in Week 5; holding 0.50, backorder 1.00; shipping delay 2; production delay 2; order delay 1 or 2 depending on board version; about 36 Weeks played with players told a longer horizon (one protocol says 50) to avoid end-game effects. Other course material uses inventory 15 and pipelines of 5. The PRD's defaults need the founder's confirmation (Open Question 5).
- **Layout learning from earlier planning (2025):** a portrait facility board with goods flowing down and orders flowing up, one editable number per Week, corners for incoming order, incoming delivery, outgoing order and outgoing delivery, inventory in the centre. Red/green status alone failed colour-blind users. Label pipeline slots as "arrives next week" rather than "Week 1/Week 2".
- **Inactivity ladder from earlier planning:** warning → one cautious AI Order → permanent AI; the PRD adapts this to deadline-bound asynchronous play (FR-36: automatic Takeover after 24 hours).
- **Classic debrief sequence:** feelings ("did you feel in control?", "did you blame your neighbours?") → evidence (demand reveal, orders and inventory per role) → structure ("structure creates behaviour", delays, supply line, demand information lost when it travels only as orders). The PRD's Debrief follows this (FR-44, FR-45). A later information-sharing round is a natural second session (v2 candidate).
- **Known student misperceptions to target:** ignoring the supply line; attributing the oscillation to customer demand or neighbours; not seeing the effect of one's own Orders.

## C. Learning measurement detail (issue #6)

- Research recommends three arms: one session plus human debrief / Replay only / Replay plus AI Debrief, with pre/post stock-and-flow items (Sweeney & Sterman bathtub tasks), a scored explanation, and transfer to an unseen Demand pattern. No published study crosses repetition with debrief or tests transfer.
- The pilot uses the light-touch design in PRD §9.1. A later Class session can randomise Debrief detail within the class. Freeze the model during any study (FR-68).
- Performance (Total cost) and understanding dissociate (Paich & Sterman 1993; Atkins 2002), which is why game cost does not count in the AI assessment and SM-C1 exists.

## T. Individual test design (coaching topic 3, for UX, architecture and writing the question set)

Source: `.docs/planning-artifacts/research/academic-lit-beer-game-test-questions-systems-thinkin-2026-11-05/research.md`. Much of the evidence is thin; confidence is flagged per claim there.

- **Why quantities and consistency.** In Booth Sweeney & Sterman (2000), Students who had played the beer game scored higher on a stock-flow task (46% vs 33%), but only on parts that reward remembering that it oscillates. They did no better on conservation of material or on consistency between graphs. The direction is confirmed by later papers; the exact numbers come from the conference version.
- **Model for Interactive items.** The Manufacturing Case: orders step from 10,000 to 11,000 a week, 4-week production delay, desired inventory 50,000. Production must overshoot orders, and the overshoot equals the lost inventory (4,000 units). Also: given inflow and outflow, draw the stock. Scoring criteria in the study: equilibrium start, lag, overshoot, area conservation, inventory first falling, then recovering, and consistency.
- **Multiple choice.** Evidence for two-tier items (answer plus reason) is small; a reason tier is optional. No evidence on negative marking.
- **Long answers.** No published rubric for free-text mechanism answers was found, so the Scoring guide is new work. Start from 5–8 coded criteria in the style of the study.
- **AI scoring.** Holistic agreement with humans is moderate (QWK about 0.6 for open-weight models); scoring many traits separately is much worse (0.32–0.41); bias direction differs between studies. This is why FR-54 gives one overall score per answer. A constant offset can be detected on a small sample (often 10 or fewer).
- **Adapted items.** No study of items built from a student's own game was found; they are a design bet. A Student's estimated supply-line weight could be computed from the Decision log but is not scored in v1, since nothing validates it as a measure.
- **Scoring guide.** Claude drafts the default during implementation and the founder approves it; a Lecturer can edit it for a Class session.

## R. Regulatory detail (for architecture, DPO dialogue and sales)

Source: `research-regulatory.md` in this folder (2026-10-29; not legal advice).

- **EU AI Act Annex III 3(b):** AI that evaluates learning outcomes in tests counting toward a grade is high-risk; the Commission's draft guidelines (May 2026) say human involvement does not change classification and the Art. 6(3) exemption does not apply to profiling. Obligations for Annex III apply from 2 December 2027 (Regulation (EU) 2026/1744). Norway: not yet incorporated in the EEA Agreement; Norwegian bill expected spring 2027. Provider duties if formal grading with an AI proposal is built in v2: risk management, data governance, technical documentation, logging, human oversight, accuracy, quality management, conformity assessment, registration, post-market monitoring.
- **Art. 50:** AI interacting with people must be disclosed at first interaction; the "obvious" exception does not cover games that mix humans and AI. Machine-readable marking of generated text.
- **GDPR:** Institution = controller, beergame = processor, LLM providers and routers = sub-processors needing prior authorisation. Norwegian institutions use NTNU's sector template or the state template for data processing agreements. DPIA is mandatory for evaluating learning in higher education (Datatilsynet list). EU–US Data Privacy Framework valid but under challenge; keep providers swappable and have an exit plan. China has no adequacy decision.
- **Universal design:** the Norwegian regulation covers digital learning tools; public universities must meet EN 301 549 (= WCAG 2.1 AA).
- **Procurement:** regulation applies from NOK 500,000 excluding VAT (from 1 July 2026); national announcement from NOK 1.3 m; EEA rules from NOK 1.63 m for state bodies. Standard contract: SSA-lille sky.
- **Integration expectations:** Feide (OIDC) and Canvas LTI 1.3 are the main ways in for Norwegian higher education; out of v1 by founder decision (PRD §8.2).

## V. Formal grading: design kept for v2

Moved out of v1 by the founder on 2026-11-05 ("alt som har med formell sensur skal ikke med i første versjon"). This is the flow the founder narrated on 2026-11-02, kept so v2 does not start from nothing:

- The Lecturer registers Examiners in advance: an external examiner and the course lecturer. Examiner is its own role, with access to that Class session's tests only.
- After the Test deadline the AI gives an advisory assessment per Student (rettledende sensur). It is never final.
- Each Examiner enters a proposed grade independently, without seeing the other's. Equal proposals become the joint grade. Different proposals stay open for both, and the system follows up until they agree.
- The system tracks the statutory grading deadline (normally three weeks) and sends reminders.
- The Lecturer sets the grading scale (A–F or Pass/Fail) and thresholds; questions carry weights.
- Students get an email when the joint grade is ready and read it in the app.

Open for v2: appeals and re-grading by new examiners; anonymous grading by candidate number; whether Students with different Adapted items can be graded fairly under the Universities Act (§ 11-6); grade export; a guard against automation bias on the review screen.

Regulation: AI proposing grades on a test that counts is likely high-risk under Annex III 3(b), and human review does not change that (§R). Building the v2 design with an AI proposal means meeting those obligations, or letting Examiners grade without it.

## X. Rejected or deferred alternatives

- **Rule-based players by default** (research recommendation): rejected by the founder on 2026-10-29; LLM players are the differentiator. Kept as a per-Class session option and as the fallback if SM-3 fails.
- **Formal grading in v1:** moved to v2 by the founder on 2026-11-05; see §V. v1 has a non-counting AI assessment and PDF Student reports instead.
- **AI as final grader:** rejected for every version.
- **Voluntary extra Replays in v1:** removed by the founder on 2026-11-05. The brief's kill bar (median solo Replays above 3) cannot be measured in v1; PRD SM-1 and SM-10 replace it for now.
- **Explanation as a separate step before the Debrief:** rejected by the founder on 2026-11-05; the Student explains during the Debrief. The research advises explaining before seeing the analysis, so the PRD places the step before the demand reveal.
- **Supervised Individual test, at least in the pilot** (research recommendation R5): rejected by the founder on 2026-11-05; the test is unsupervised, with Interactive items that are harder to solve with outside AI tools. The research does not show that they are, so the PRD tests it before the pilot (open question 7).
- **One sitting with a 60-minute limit as the default:** replaced by the founder on 2026-11-05; Students can come back as often as they want until the Test deadline, and one sitting with a time limit remains a Lecturer setting.
- **Join by code without accounts** (competitor norm): rejected because Grades, Replays and Cross-class statistics need persistent identities.
- **Feide and Canvas in v1:** deferred by the founder.
- **Player chat:** deferred to v2; in v1 the classic no-talking rule holds.
- **From earlier planning (2025), deliberately not carried over:** free tier, student subscriptions, Stripe billing, white-label, certificates, public game rooms, pause/reset of all games, detailed export packs.
