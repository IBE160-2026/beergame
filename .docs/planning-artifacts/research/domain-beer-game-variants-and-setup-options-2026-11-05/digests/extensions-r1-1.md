# Digest extensions-r1-1: Beer Game extensions and teaching variants (Dimension 3)

Accessed for all rows: 2026-11-05. Run limits: about 12 sources read, about 20 tool calls. Many journal pages returned only abstract-level text (publisher full texts were blocked or unreadable PDFs), so effect sizes are mostly directional, not numeric. Where a claim came only from a search-engine summary of a source and not from a page I fetched, I say so. "Fetched" = I opened the page; "search-only" = seen in a search result summary.

Out of scope, one line: communication or chat between players exists as an extension in the literature (Zensimu even exposes it as a per-round setting) and is deferred by the founder.

## A. Information visibility (dimension 1)

| # | Claim | Source URL | Publisher | Pub. date | Confidence | Class |
|---|---|---|---|---|---|---|
| A1 | Croson & Donohue (2006): two experiments with random demand and information lags show the bullwhip persists even after removing the operational causes batching and price fluctuations. Sharing inventory information reduces the bullwhip somewhat by helping upstream members anticipate downstream fluctuations, but does not remove the tendency to underweight the supply line. Upstream members gain most. Authors' own summary: gains are partial, not elimination. (Fetched abstract-level page.) | https://econpapers.repec.org/RePEc:inm:ormnsc:v:52:y:2006:i:3:p:323-336 | Management Science (via EconPapers/RePEc) | 2006 | high (direction), low (magnitude: no numbers retrieved) | effect-size |
| A2 | Croson & Donohue, "Upstream versus downstream information and its impact on the bullwhip effect", System Dynamics Review 21(3), 249-260: in a controlled Beer Distribution Game, giving players downstream inventory information significantly lowers order oscillation; giving upstream (supplier-side) inventory information did NOT. Upstream tiers benefit most from downstream information. This is the direct answer to "see the supplier's inventory": experiment found no significant benefit. (Search-only: two separate search summaries agree; I could not open the paper. The dataset aggregator page and zendy page returned nothing.) | search results listing https://data.zhenzhi.com/details/1/863396533 (aggregator, not opened); journal citation SDR 21, 249-260 | System Dynamics Review (Wiley) | 2005 | medium | effect-size |
| A3 | Gonçalves & Moshtari (2021) re-analysed pooled data from the two Croson & Donohue experiments (2003, 2006). With supply-chain-level information (POS and inventory data), subjects react less to changes in their own inventory and attend more to their supply line (the mechanism by which information helps). Effects are stronger for upstream subjects. (Fetched.) | https://ideas.repec.org/a/bla/sysdyn/v37y2021i2-3p126-154.html | System Dynamics Review (via IDEAS/RePEc) | April 2021 | high | effect-size |
| A4 | Steckel, Gupta & Banerji (2004): beer-game experiment varying cycle (order/delivery) length, shared POS information, and demand pattern. Shorter cycle times help. Shared POS information does not always help: its value depends on demand pattern; with continually changing (S-shaped) end demand, POS data can distract upstream players from the nearest downstream orders and the supply line. So POS sharing can fail or be neutral. (Fetched abstract.) | https://econpapers.repec.org/RePEc:inm:ormnsc:v:50:y:2004:i:4:p:458-464 | Management Science (via EconPapers/RePEc) | 2004 | high (direction) | effect-size |
| A5 | Croson, Donohue, Katok & Sterman, "Supply Chain Management: A Teaching Experiment" (2005, Springer, Experimental Business Research): classroom exercise shows inventory managers are boundedly rational; information-sharing (inventory sharing between firms, POS sharing) is named as a remedy that helps decisions. The page does not report numbers. (Fetched.) | https://ideas.repec.org/h/spr/sprchp/978-0-387-24244-6_13.html | Springer (via IDEAS/RePEc) | 2005 | medium | other |
| A6 | LLM-agent simulation (not human data): four-stage chain, 20 periods, uniform 0-8 demand; information sharing (IS) cut order variance in all four homogeneous configurations, e.g. DeepSeek-Original mean variance 39.43 to 20.15 (p<0.001), GPT-Original 58.45 to 40.39 (p=0.044). Total cost: DeepSeek-Original 751.27 to 585.34; GPT-Original 641.55 to 585.88; best total cost with IS plus the strongest agents. Treat as bots-behave-like-humans evidence only, not as human effect size. (Fetched arXiv html.) | https://arxiv.org/html/2604.17220 | arXiv (Jiang et al., Harbin Inst. of Technology / HK PolyU) | v2 revised 2 June 2026 (preprint, not peer-reviewed) | medium | effect-size |
| A7 | Craft Beer Game (Grassel et al., TU Delft 2021): variant with craft-brewery parameters sharing downstream orders and inventories; reported that full transparency halves missed beer sales and cuts spoilage by about 70% on average. Search-only (the TU Delft record would not load); single source and a perishability variant, so not generalisable. | https://repository.tudelft.nl/record/uuid:ca94f877-6c80-4bfd-a1a0-f9c90ef26f7c (search summary only) | TU Delft repository | 2021 | low | effect-size |
| A8 | Software evidence for how existing products expose visibility: Forio/Darden lets the instructor set whether teammates can share inventory on hand, incoming shipments and demand, and whether sharing has a cost. Zensimu's default template is "round with visibility / round without visibility" (the docs do not say what visibility reveals). (Both fetched.) | https://forio.com/catalog/darden-beer-game-supply-chain-simulation ; https://docs.zensimu.com/article/21-prepare-beer-game-session | Forio (vendor); Zensimu (vendor) | undated | medium (vendor description) | rule-definition |

Answer to the one-step-visibility question: the only direct experimental contrast I found (A2) says downstream inventory visibility helps and upstream (supplier) inventory visibility does not significantly reduce oscillation. No source I retrieved tested "see only your immediate neighbour" vs "see everyone" as a separate treatment. Information helps through a specific mechanism (more weight on the supply line, less reaction to own inventory, A3), gains are partial (A1) and POS data can backfire under shifting demand (A4). For software this is a per-role, per-field visibility matrix (own/downstream/upstream/all, inventory/backlog/orders/customer demand), cheap to implement.

## B. Lead time and delays (dimension 2)

| # | Claim | Source URL | Publisher | Date | Conf. | Class |
|---|---|---|---|---|---|---|
| B1 | Steckel et al. (2004) found speeding up cycle time is beneficial (see A4, fetched). | https://econpapers.repec.org/RePEc:inm:ormnsc:v:50:y:2004:i:4:p:458-464 | Management Science | 2004 | high | effect-size |
| B2 | Standard game delays: shipping delay and order-processing delay at each stage; starting state is equilibrium (12 cases inventory, throughput 4/week). Ancillary rules: no capacity limits, breakdowns, random events or financial constraints. (Fetched.) | https://web.mit.edu/jsterman/www/SDG/beergame.html | MIT Sloan (Sterman) | undated (references 1992 and 1994) | high | rule-definition |
| B3 | Stochastic lead times raise cost and bullwhip vs the standard game (study with 104 MBA students and 24 purchasing managers, 2011; effects shrink with experience but persist); a related 2013 paper (Ancarani, Di Mauro, D'Urso) found higher order variance under stochastic lead times. Search-only summary, not opened. | search result summary (no single URL fetched) | journals not identified | 2011, 2013 | low | effect-size |
| B4 | Croson & Donohue list reducing ordering and shipping delays as a remedy alongside information sharing (suggested, not a separate tested treatment in what I read). Search-only. | https://pubsonline.informs.org/doi/pdf/10.1287/inte.32.5.105.35 (search result, not opened) | INFORMS Interfaces | 2002 | low-medium | other |

Software note: fixed lead times are a simple integer parameter per link. Stochastic lead times need a random-draw rule and reproducible seeds.

## C. VMI and centralised ordering (dimension 3)

- C1: I found no human-subject experiment testing VMI or centralised ordering in the Beer Game within budget. A search returned only Croson & Donohue (information sharing as a remedy) and a pointer to Croson et al. (2014) on computer-managed vs human-managed positions, not opened. Confidence: low. Class: other.
- C2: Software view: centralised ordering is a role-structure change (one player or the computer sets orders for all echelons; or the supplier replenishes the customer, so the middle players do not order). This is a mode switch, not a single numeric parameter; it changes the number of decisions per team.
- Teaching rationale (unverified belief from prior knowledge, not evidenced this run): demonstrating that the structure, not the people, drives the bullwhip.

## D. Capacity limits, batching, minimum order sizes (dimension 4)

| # | Claim | Source | Publisher | Date | Conf. | Class |
|---|---|---|---|---|---|---|
| D1 | Standard game has no capacity limits (B2). | https://web.mit.edu/jsterman/www/SDG/beergame.html | MIT Sloan | undated | high | rule-definition |
| D2 | Lee, Padmanabhan & Whang name order batching and price variations as two of four rational causes of the bullwhip (with demand signal processing and rationing/shortage gaming); summary seen in search results only. | https://econpapers.repec.org/RePEc:inm:ormnsc:v:43:y:1997:i:4:p:546-558 | Management Science | 1997 | high (cause list) | other |
| D3 | Croson & Donohue's first experiment removes batching and price fluctuation and still finds the bullwhip (A1): so batching is not needed to produce the effect; adding it is a rule extension. | as A1 | Management Science | 2006 | high | effect-size |
| D4 | Transport-capacity-limited beer-game variant (system dynamics study, search-only): capacity limits raise inventory/backlog costs. Not opened, low confidence. | search results (efos.unios.hr conference PDF) | Business Logistics in Modern Management | year not verified | low | effect-size |
| D5 | Zensimu says batch sizes can be a teaching focus of settings; the doc does not show a batch setting explicitly. | https://docs.zensimu.com/article/21-prepare-beer-game-session | Zensimu (vendor) | undated | low | usage-frequency |

Software note: minimum order or batch size = integer parameter with rounding rule; capacity = per-echelon shipment cap plus a rule for what happens to the excess (backlog). Rationing then needs an allocation rule, which is more than a toggle.

## E. Pricing, promotions, rationing and shortage gaming (dimension 5)

| # | Claim | Source | Publisher | Date | Conf. | Class |
|---|---|---|---|---|---|---|
| E1 | Standard design: each player orders from and ships to one other party and capacity is unlimited, which removes the rationing/gaming incentive; bullwhip still appears (so gaming is not required). Search-only summary. | search results (Cardiff ORCA IJLRA PDF listed) | Cardiff University ORCA | year not verified | low-medium | rule-definition |
| E2 | Phantom ordering exists even in the plain game: Dogan & Sterman, "When Less Leads to More: Phantom Ordering in the Beer Game?" used constant known demand of 4/week and still saw phantom-ordering loops; a follow-up reports 22% of participants ordering more than 25 times the known constant demand. Search-only. | https://link.springer.com/article/10.1007/s10696-009-9054-3 (redirected, not opened) and search results | Springer (journal Flexible Services and Manufacturing, per URL, not verified) | 2009 | medium for existence, low for the 22% | effect-size |
| E3 | Lee et al. recommend allocating by past usage rather than current orders to fight shortage gaming; price swings cause forward-buying (search summary of the Sloan Management Review companion). | https://courses.ischool.berkeley.edu/i290-4/s03/readings/bullwhip.htm | UC Berkeley course reading (reproducing Sloan Mgmt Review) | 1997 | medium | other |

No experiment found where a price promotion or explicit rationing was added to the classic game for human subjects; this is the least evidenced extension. Software: promotion = scripted demand/price events (needs a scenario editor), rationing = allocation rule: both are more complex than a toggle.

## F. Stochastic vs deterministic demand and shocks (dimension 6)

| # | Claim | Source | Publisher | Date | Conf. | Class |
|---|---|---|---|---|---|---|
| F1 | Classic demand: 4 cases/week stepping to 8 in week 5, then constant; game announced as 50 weeks but halted at 36. Typical results: average team cost about $2,000, often above $10,000, rarely below $1,000; optimum about $200 (roughly ten times optimal); about 20-week oscillation; factory peak order more than double the retail peak. Within a class, team costs commonly differ by 5-10x (search summary). (Fetched.) | https://web.mit.edu/jsterman/www/SDG/beergame.html | MIT Sloan (Sterman) | undated | high | rule-definition / effect-size |
| F2 | Constant, announced demand (4/week) was used by Dogan & Sterman and still produced oscillation and amplification, showing demand shocks are not necessary. Croson & Donohue (2006) and Edali & Yasarcan used stochastic end-customer demand (the latter stationary with the distribution announced to subjects). Search-only. | see E2 and A1 | various | 2006, 2009, 2015 | medium | rule-definition |
| F3 | Steckel et al.: demand pattern changes whether POS information helps (A4). | as A4 | Management Science | 2004 | high | effect-size |
| F4 | LLM study used uniform 0-8 demand (A6). | https://arxiv.org/html/2604.17220 | arXiv | 2026 | medium | rule-definition |

Software: demand pattern selection (step / constant / random distribution with seed / custom scripted series) is a simple dropdown plus parameters. Seeding matters so two rounds can be compared.

## G. Incentives and cost structures (dimension 7)

| # | Claim | Source | Publisher | Date | Conf. | Class |
|---|---|---|---|---|---|---|
| G1 | Standard game cost: holding 0.50 per case per week, backlog 1.00 per case per week; the objective is lowest total team cost; the winning team takes a $1 per player pot; no individual incentive (Sterman). (Fetched.) | https://web.mit.edu/jsterman/www/SDG/beergame.html | MIT Sloan | undated | high | rule-definition |
| G2 | Banbury et al. (via search summary): team-focused groups outperform individual-focused groups, but only when they were given information on current demand level. Not opened. | https://proceedings.systemdynamics.org/2013/proceed/papers/P1409.pdf (search result) | System Dynamics Society conference | 2013 (year of proceedings, not verified for paper) | low | effect-size |
| G3 | Edali & Yasarcan compare per-echelon cost with team total; when other echelons behave suboptimally, parameters that are optimal for one echelon may not stay optimal. LLM study agrees: upgrading one upstream agent lowers its own cost but raises team cost under isolation (self-interest effect). | A6 and search results | arXiv; Sys. Dyn. Society | 2015; 2026 | medium | effect-size |
| G4 | A thesis (Qorbani, Radboud) reports risk-averse subjects raise the bullwhip and a loss-of-reward framing matters; abstract only, single master's thesis. | https://theses.ubn.ru.nl/items/ebacd2b1-93e0-40f7-9088-a6bd225ca955/full | Radboud University | year not verified | low | effect-size |

Software: show team and per-role cost side by side (cheap); changing cost coefficients (holding/backlog ratio) is a simple numeric parameter; individual-incentive scoring is a scoring-display choice. No evidence retrieved on the effect of changing the holding:backlog ratio.

## H. AI / computer players (dimension 8, short)

- H1: Rule-based bots follow Sterman's anchoring-and-adjustment ordering heuristic (stock-management heuristic proposed in Sterman 1989 as a model of subjects' decisions; Edali & Yasarcan used it for computer-simulated participants). Search-only summary, so medium confidence. Source: search results; https://proceedings.systemdynamics.org/2015/proceed/papers/P1053.pdf (could not read PDF).
- H2: Reinforcement learning: Oroojlooyjadid, Nazari, Snyder & Takáč, "A Deep Q-Network for the Beer Game" (arXiv 1708.05924, 2017; Manufacturing & Service Operations Management 24(1), 285-304, 2022). DQN agent with reward shaping plays the cooperative game against co-players that may be irrational; it performs well alongside base-stock players; one version says the agent was integrated into a new online beer game played over 17,000 times by over 4,000 people. Search-only. Confidence: medium-high on existence, medium on claims. Source: https://arxiv.org/pdf/1708.05924.pdf (listed, not opened); https://econpapers.repec.org/RePEc:inm:ormsom:v:24:y:2022:i:1:p:285-304 .
- H3: LLM agents: Jiang et al. (arXiv 2604.17220v2, June 2026, fetched) found LLM agents, even stronger reasoning models, still amplify orders (variance up roughly 74-82% across the chain) and underweight the supply line, like humans; information sharing reduced variance (A6). AIM-Bench (arXiv 2508.11416) evaluates LLM inventory managers for biases including demand chasing and bullwhip (search-only). Confidence: medium; preprints.
- H4: Zensimu: roles with no connected player, or players who miss the decision timer (default 1 minute), are played automatically by the computer; bot type not specified. Source: https://docs.zensimu.com/article/21-prepare-beer-game-session (fetched). Confidence: medium.
- Software note: simplest useful bot is a base-stock or anchor-and-adjust rule with parameters; filling empty seats is the main use.

## I. Round-two design (dimension 9)

- I1: Zensimu default template: two rounds of 20 weeks (short option 2 x 12), settings editable per round, the default pair being a round without and a round with visibility; instructors can run a second round implementing the group's own proposals after the debrief. Debrief centres on an orders-versus-end-demand chart showing the bullwhip. Source: https://docs.zensimu.com/article/21-prepare-beer-game-session ; search result for https://zensimu.com/resources/debriefing-instructor-guide/ . Vendor. Confidence: medium. Class: usage-frequency / rule-definition.
- I2: Academic precedent: a 2002 modified-game paper (found via search, not opened) has students play one traditional round, then a second round comparing full cooperation (information sharing) with total independence. Low confidence.
- I3: Forio/Darden: instructor decides whether teammates can share inventory, shipment and demand information, and whether sharing costs something; 30 simulated weeks. https://forio.com/catalog/darden-beer-game-supply-chain-simulation . Vendor. Medium.
- Software design implication: store a round as a settings snapshot (visibility matrix, lead times, demand series with seed, costs, bots), keep the same roles and structure, change one factor, and compare rounds on cost and order-variance ratio.

## J. Ranking by use (teaching vs research)

Evidence on frequency is thin: no survey of instructor usage found. The ranking below combines what existing products expose (vendors Zensimu, Forio) with how often the experimental literature varies each factor. Treat as medium-low confidence.

Teaching, most to least common:
1. Information visibility / sharing (inventory, orders, POS) as round 2 (Zensimu default, Forio setting, Croson et al. teaching experiment).
2. Lead times / delays (Zensimu per-round setting; Steckel).
3. Demand pattern (Zensimu "final consumer demand", Sterman classic step).
4. Batch sizes and stock costs named as teaching focuses (Zensimu), apparently less commonly set.
5. Computer fill-in players (Zensimu automatic play).
6. VMI / centralised ordering, capacity limits, pricing/promotion/rationing: not found as options in the vendor pages I read; mostly discussed in the bullwhip theory (Lee et al.).

Research, most to least studied (in what I retrieved): information sharing (Croson & Donohue, Steckel, Gonçalves & Moshtari); demand pattern; lead-time type (stochastic); phantom ordering and hoarding; incentives and individual traits; bots (rule-based, DQN, LLM, growing quickly 2017-2026).

Simple parameter toggle vs structural change: toggles = visibility matrix, lead times, demand series, cost coefficients, min order/batch, starting stock, number of weeks, bot fill-in. Structural = centralised ordering/VMI, capacity with rationing, promotions, stochastic lead times with seeds, multi-echelon network changes.

## Leads worth chasing

- Croson & Donohue (2005) SDR 21(3) 249-260 full text, and their 2006 Management Science paper full text: exact treatments and numbers (order-variance ratios) for inventory-sharing vs POS-sharing, and the upstream-vs-downstream result.
- Steckel, Gupta & Banerji (2004) full text: size of the cycle-time and POS effects.
- Croson, Donohue, Katok & Sterman (2014), "Order stability in supply chains: coordination risk and the role of coordination stock" (Management Science): computer-managed vs human partners and a candidate for centralised ordering evidence.
- Perera, Fahimnia & Tokar (2020) systematic review of behavioural inventory experiments (named in a search result, not opened): would give usage frequency in research.
- Wu & Katok (2006) on communication: out of scope, one line only.
- Kunze & Sterman (SD Conference 2006, KUNZE354.pdf) on information availability; Zhou (2021) University of Greenwich on behavioural causes and human vs computer partners.
- Dogan & Sterman, "When less leads to more: phantom ordering", for the hoarding rate (22% claim).
- Oroojlooyjadid et al. full paper: how the DQN performs against human-like heuristics, and the "17,000 plays" online game.
- Chen, Drezner, Ryan & Simchi-Levi (bullwhip and information, Management Science 2000): analytical, not looked at.
- Instructor-facing university materials (MIT Sloan Beer Game teaching notes, Darden, Kellogg) for round-two designs not owned by vendors.

## Looked for and could not find

- A human-subject experiment that tests vendor-managed inventory or centralised ordering in the Beer Game.
- A controlled human experiment varying only the fixed lead time with numeric results.
- Any experiment adding price promotions or explicit rationing to the classic game.
- Quantitative effect sizes (order-variance ratio, % cost change) for POS vs inventory information in human experiments; only the LLM study (A6) gave numbers.
- Evidence of how frequently instructors use each extension; no survey of usage.
- An experiment on holding:backlog cost ratio or team vs individual payment in the original game (only weak conference or thesis hints, G2 and G4).
- Full text of Croson & Donohue 2005; publisher sites (Springer, INFORMS, Wiley, Tampere, TU Delft) were blocked, redirected or unreadable in this run.
