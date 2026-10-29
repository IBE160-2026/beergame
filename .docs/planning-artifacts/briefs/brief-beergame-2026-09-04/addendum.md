---
title: "Addendum: beergame product brief"
status: final
created: 2026-09-07
updated: 2026-10-29
---

# Addendum

Supporting depth for `brief.md`. This material is for the PRD, the architecture work and the pitch Q&A — it earned a place, but it does not belong in a two-page brief.

## Sources behind the problem statement

All claims in "The Problem" and "Why Now" trace to these. Nothing in the brief is invented.

### The decline

- **[Less beer, more couscous: gamifying supply chain education](https://www.timeshighereducation.com/campus/less-beer-more-couscous-gamifying-supply-chain-education)** — *Times Higher Education* Campus, June 2026. The single most useful source for this brief. A supply chain educator explains why he stopped running the beer game and built a browser-based replacement.

  Direct quotes used:
  - *"The effort required to run the game can end up distracting from the bigger picture."*
  - *"Few could clearly explain how their decisions had led them there."*
  - *"Slow to run and proves surprisingly fragile"* — small errors in tracking orders or inventory distort results.
  - *"Fixed demand patterns make it easier for students to anticipate outcomes."*

  What he built instead: orders, inventories, costs and delays handled in the background; system-generated demand fluctuation rather than fixed patterns; clearer feedback. He reports students shifted from asking *"if their answers were correct"* to *"questioning why certain outcomes occurred."*

  **Read this one carefully before the pitch.** It is simultaneously the strongest evidence for the venture and the strongest argument against needing AI at all. An investor who finds it will use it both ways.

### LLM agents in the beer game

The behavioural-fidelity argument rests on these. This is an active research area, not a novel idea — treat it as validation of feasibility, not as proprietary insight.

- **Unverified, do not cite:** SSRN 5266281 (Jin, Jiang, Tian, "Effects of LLM Agent Capability and Capability Gradients on the Bullwhip Effect"). It was not found in Crossref, DataCite, OpenAlex or web search, and SSRN blocked access (research 2026-10-26, [38]). The figures earlier quoted from it (58%, 24%, 44%, 18%, 37%, 63%) are unconfirmed and were removed from the brief. The idea that weaker models are more human opponents is therefore also unsupported.
- **Long et al., Harvard/MIT/Georgia Tech GenAI Beer Game** (competitive research [34]): best configuration cuts cost up to 80% against student teams. Default LLM configurations vary 26–52% run to run (the paper's text says 26–45%); guardrails or post-training bring it to about 12–13%. Human-likeness was not measured.
- **Mixed evidence on behaviour** ([36][37]): LLMs reproduce the direction of human biases and act myopically, but with different response distributions. Treat "LLM opponents preserve the bullwhip effect" as unproven.
- **[AIM-Bench: Evaluating Decision-making Biases of Agentic LLM as Inventory Manager](https://arxiv.org/pdf/2508.11416)** — LLM agents exhibit documented human decision biases in inventory roles.
- **[Reliability and Effectiveness of Autonomous AI Agents in Supply Chain Management](https://arxiv.org/html/2605.17036)** — notes a second amplification layer: not only do order levels amplify upstream, the *dispersion and tail risk* of the decisions themselves amplify across otherwise identical runs. Relevant risk for reproducibility if a lecturer needs comparable results across a cohort.
- **[A Deep Q-Network for the Beer Game](https://www.researchgate.net/publication/349540140_A_Deep_Q-Network_for_the_Beer_Game)** and **[The beer game bullwhip effect mitigation: a deep RL approach](https://www.tandfonline.com/doi/full/10.1080/00207543.2025.2479831)** — the RL alternative. Cheaper to run per game than LLM inference and fully deterministic, but produces optimising rather than human-like play. Worth considering as a cost-control option for agents whose behavioural realism matters less.

## Competitive landscape

Surveyed at the level of public product pages and client code, **not** hands-on feature testing. Full teardown, 52 sources and confidence levels: `.docs/planning-artifacts/research/competitive-beer-game-competitors-2026-10-26/research.md`.

**Added by the 2026-10-26 research (not in the table below):**

| Product | Notes | Price |
|---|---|---|
| **En Dash** (beergame.endash.us) | Free, solo against 3 AI roles, 4-role sandbox, replay route, 10 scripted debrief questions. Solo bots are one-line ordering rules in client code; multiplayer bot logic unseen. Fixed demand. Show HN 2026-08-25, 1 point; reads as a consulting lead magnet but is actively built | Free |
| **Zensimu / beergameapp.com** | Computer fills roles with a net-stock rule, timer auto-play, free single-player plan, automated report, SSO on Enterprise. Small profitable Danish firm | 2024: €17.5 per participant; no current public price |
| **Forio Root Beer (Harvard)** | Optional computer-controlled player, single-player mode | $168 per person |
| **Skill Dynamics** | Solo against "AI bots", logic unseen behind a lead form | — |
| **siemsene/beergame** (open source) | "Beer-GPT" robo-players, a simple rule, not an LLM; reports about 200 players a day | Free |

transentis also offers "AI players" (logic undocumented), free solo play and CSV/JSON/PDF export, and its company is pivoting to the Metapad AI platform.

**Correction.** The earlier line "no product treats this as repeatable practice" is false as worded. Defensible restatement as of 2026-10-26: no maintained, learner-facing beer game is documented as using LLM-driven opponents with a human seat or an LLM-generated decision-level debrief. One abandoned Hugging Face prototype (human Distributor against GPT-4o-mini agents) and research systems without a human seat exist.

| Product | Notes | Price |
|---|---|---|
| [MIT Sloan Beer Game Online](https://mitsloan.mit.edu/teaching-resources-library/mit-sloan-beer-game-online) | The canonical authority. Used with thousands of people in universities and companies | Free/institutional |
| [transentis Beergame](https://beergame.transentis.com/) | Strongest practical competitor. QR or lobby-code entry, no download, no accounts, setup in minutes | Free |
| MA-System | Simplified design, works in modern browsers, suited to distributed single-player or no-budget university use | Free |
| [beergameapp.com](https://beergameapp.com/) | Scale play — a single session handles up to 600 participants | — |
| [Kearney Beer Distribution Game](https://www.kearney.com/web/beer-distribution-game) | iOS App Store, multiplayer, range of scenarios. Consultancy brand play | Free |
| [responsive.net eBeer](https://responsive.net/ebeer.html) | Long-established, systems-dynamics framing | — |
| [Zensimu](https://zensimu.com/beer-game/) | Commercial. Also publishes a [comparison guide](https://zensimu.com/resources/best-beer-game-simulations-comparison-guide/) ranking competitors — a live signal that this market is contested enough to be worth SEO |
| [Forio Near Beer](https://forio.com/resources/bullwhip-supply-chain-near-beer-simulation) | Claims 1M+ learners since 2006 | Commercial |
| [Harvard Business Publishing Root Beer Game](https://help.hbsp.harvard.edu/hc/en-us/articles/6157823105555-How-do-I-use-the-Supply-Chain-Management-Simulation-Root-Beer-Game-in-a-Virtual-Classroom) | The credible paid incumbent. Institutional channel already established | Paid |

**What this table means for the pitch.** Two facts matter more than the rest: Zensimu maintains SEO content about competitors (contested market), and Harvard Business Publishing already sells into exactly the institutional channel the business model targets (an incumbent with a relationship, not a greenfield). "No good product exists" is not a defensible claim in this room. "No product treats this as repeatable practice" might be — and needs verifying against each row above.

## The positioning fork

**Decided 2026-10-29: B**, carried as an untested hypothesis. A forge session (`.docs/forge/beergame-positioning-b/`) pressure-tested it. The core premise, that repetition and debrief are both needed and reinforce each other, stayed unproven: no study separates them, and the founder has no time to test it in semester one. No kill threshold was set beyond the brief's median-replays bar. The research verdict is that B holds only if the debrief and progression layer is the product; the fallback is a debrief-first product with simple bots. The original fork follows for reference.

**A — "The beer game, finally without friction."**
Solve the documented complaints: automated mechanics, variable demand, real debrief. AI bots are a convenience feature that fills empty seats.
*For:* need is documented and verifiable; smaller build; easier to explain.
*Against:* it is precisely what the *Times Higher Education* author already built for himself, and transentis is free. Hard to defend, hard to charge for.

**B — "From one session to a hundred."**
Repetition is the wedge. AI agents exist to make solo replay possible; the AI debrief attacks the "few could explain how their decisions led them there" gap directly.
*For:* attacks the most expensive documented complaint, which nobody else has solved; supports a real progression/analytics product; genuinely novel framing.
*Against:* larger build; per-session inference cost; the premise that repetition is what is missing is a hypothesis, not something an educator has published about.

**Why B was chosen for the draft.** The founder named AI bots as the most important new idea in the concept, and B is the framing where that idea carries strategic weight rather than being a feature transentis could ship in a quarter. This is a reversible drafting decision — flag it and the brief is rewritten toward A in one pass.

## Business model reasoning

The founder specified "cheap for students, expensive for schools." The reasoning below is inferred and needs confirmation.

- Students are the most price-resistant segment in education, and every serious competitor is free. A student tier priced as revenue would fail; priced as an adoption channel it can work.
- Institutions pay for what students never need: class management, cohort analytics, roster handling, support, and someone accountable when it breaks mid-lecture.
- Bottom-up adoption de-risks the top-down sale — a department that already has students using it is not evaluating a cold vendor.
- **The tension to resolve:** institutional revenue implies procurement cycles measured in quarters, while AI inference costs are incurred per replay from day one. Runway must cover the gap between the two.

## Founder position

- Teaches the course the product ships into. First classroom is his own, which supplies a design partner, a test bed and the learning-outcome evidence in section "Success Criteria" of the brief.
- This is stated as a real venture, not coursework.
- **Pitch implication:** practitioner-founders selling into their own profession are a recognised strong pattern. It should be foregrounded in the pitch, not buried — it is the most credible asset in the deck right now, more so than any feature.

## Deliberately deferred

Raised or implied in discovery, parked rather than dropped:

- Product name.
- Market sizing — how many courses worldwide actually run this exercise.
- Hands-on verification of En Dash multiplayer bots, Skill Dynamics and Zensimu solo. (Bot-filled roles at incumbents are now confirmed from public sources.)
- Whether reproducibility across a cohort is a hard requirement for lecturers. No public evidence either way (user-voice research); 5–8 lecturer interviews are needed.
- RL agents: out of the first version. Training cost is high and RL plays as a cost-minimiser, not like a human.

## Decisions and design notes from the 2026-10-29 update

- **Opponent default.** The founder chose LLM opponents as the default, with rule-based bots selectable per class. Research recommended the reverse (rules by default, LLM for debrief and optional personas). The choice is kept; the consequences below must be handled in the PRD and architecture.
- **Cost (modelled, not measured).** Assumes 3 AI roles × 36 turns = 108 calls, 2,000 input and 150 output tokens per call. Per session: Haiku 5.5 about $0.03, gpt-5-mini $0.09, Sonnet 5.5 $0.59; DeepSeek V4.1 Flash about $0.016. Reasoning-length outputs raise Haiku to about $0.13 and Sonnet to about $2.60. Debrief is one call, about $0.003 on Haiku. OpenRouter adds 5.5% to 8%. Suggested guardrail: at or below $0.10 per session, to be verified by a prototype (issue #8). Replays that reuse recorded decisions cost nothing.
- **Reproducibility.** No LLM vendor guarantees determinism. Some Claude models reject temperature and seed settings. Log every decision with seed, model, provider and prompt version. Pin an exact model slug. Freeze the model during any measurement study.
- **Validation.** Validate every LLM order in code; a schema-valid order is not necessarily a legal game move.
- **Debrief design.** Compute all numbers from the decision log and let the LLM narrate. Have the student attempt an explanation first. Hallucination in LLM explanations is a documented risk.
- **Learning evidence.** Thin: Jeong and Hong 2011 (abstract only), Fu and Gonzalez 2006 and Martin 2004 (snippets). Paich and Sterman 1993 found repetition did not bring insight. PRD measurement design: arms of single session, replay only, replay plus AI debrief; pre/post stock-flow test; scored explanations; transfer to an unseen demand pattern.
- **Privacy.** Set data collection to deny and zero data retention on OpenRouter, and prepare a data-processing agreement before the first institutional sale.
- **Pricing anchors.** Free floor (transentis, En Dash); $10–20 per student (eBeer); $168 per person (Forio). A student tier competes with free.
