---
title: "Addendum: beergame product brief"
status: draft
created: 2026-09-07
updated: 2026-09-07
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

- **[Effects of LLM Agent Capability and Capability Gradients on the Bullwhip Effect in the Supply Chain](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5266281)** (Jin, Jiang, Tian — SSRN). GPT-4 lowers bullwhip 58% and total supply chain cost 24% relative to GPT-3.5; DeepSeek-R1 achieves 44% and 18%. Information sharing and vendor-managed inventory mitigate bullwhip by 37% and 63% respectively. Useful because it shows agent *capability* is a tunable difficulty dial — a weaker model is a more human opponent.
- **[AIM-Bench: Evaluating Decision-making Biases of Agentic LLM as Inventory Manager](https://arxiv.org/pdf/2508.11416)** — LLM agents exhibit documented human decision biases in inventory roles.
- **[Reliability and Effectiveness of Autonomous AI Agents in Supply Chain Management](https://arxiv.org/html/2605.17036)** — notes a second amplification layer: not only do order levels amplify upstream, the *dispersion and tail risk* of the decisions themselves amplify across otherwise identical runs. Relevant risk for reproducibility if a lecturer needs comparable results across a cohort.
- **[A Deep Q-Network for the Beer Game](https://www.researchgate.net/publication/349540140_A_Deep_Q-Network_for_the_Beer_Game)** and **[The beer game bullwhip effect mitigation: a deep RL approach](https://www.tandfonline.com/doi/full/10.1080/00207543.2025.2479831)** — the RL alternative. Cheaper to run per game than LLM inference and fully deterministic, but produces optimising rather than human-like play. Worth considering as a cost-control option for agents whose behavioural realism matters less.

## Competitive landscape

Surveyed at the level of public product pages, **not** hands-on feature testing. Verification is an open item; `bmad-deep-recon` (competitive) is the right tool for it.

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

Raised in discovery, not yet decided by the founder. `brief.md` is written toward **B**.

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
- Feature-by-feature competitor verification, particularly whether any incumbent already offers bot-filled roles.
- Whether reproducibility across a cohort (same demand curve, comparable results) is a hard requirement for lecturers. If yes, it constrains agent design — see the dispersion finding in the research above.
- RL agents versus LLM agents as a cost-control strategy.
