# Digest: Start settings and parameter values (Dimension 2), run r1-1

Accessed for all sources: 2026-11-05. "Read" = page fetched and read this run. "Snippet" = only seen in a search-engine summary, not read; capped at medium/low confidence.
Publication dates are given where the page states one; "not stated" otherwise.

## Findings

### (a) Starting inventory, pipeline, steady state

1. Classic board game: 12 cases in each inventory, 4 chips in each shipping box and production-delay box, order slips marked "4" in every order box; game starts in equilibrium. Source: https://systemdynamics.org/wp-content/uploads/2020/12/BEER-GAME-INSTRUCTIONS.pdf. Publisher: System Dynamics Society (adapted from Sterman). Date: May 2017 revision. Read. Confidence: high. Class: parameter-value.
2. Sterman's own article: "Each inventory contains 12 cases", "initial throughput is four cases per week", "The game is initialized in equilibrium". Pipeline numbers are not given there. Source: https://web.mit.edu/jsterman/www/SDG/beergame.html. Publisher: MIT (Sterman, OR/MS Today article). Date: October 1992 per the page text. Read. Confidence: high. Class: parameter-value.
3. A 2021 MIT Sloan paper (Paine) states the "typical starting layout ... used in numerous previous studies" (cites Croson & Donohue 2006, Narayanan & Moritz 2015, Sterman 1989) is 12 units on hand per player, 4 units in transit at each shipping stage, 4 orders in the order chain. Four training rounds precede the step: demand fixed at 4 and everyone orders 4. Source: https://arxiv.org/pdf/2202.12786. Publisher: arXiv (J. Paine, MIT Sloan). Date: 18 Dec 2021 (arXiv listing 2022). Read (via pdftotext). Confidence: high for the quoted layout; the secondary claim that those three studies use it is the author's, unchecked. Class: parameter-value.
4. The 15-unit variant exists: beergame.org (a web game) gives example initial values of inventory 15, orders 5, units in each shipping field 5, and demand 5 then 9. Source: https://beergame.org/the-game/structure-rules/. Publisher: beergame.org. Date: not stated. Read. Confidence: high that this web game uses 15/5/5; "e.g." wording means these are examples, not fixed defaults. Class: parameter-value.
5. beergame.org software lets the instructor "define initial stock levels, deliveries, backorders, incoming orders and shipping delay amounts", so initial state is configurable, not fixed. Source: https://beergame.org/software/features/. Publisher: beergame.org. Date: not stated. Read. Confidence: high. Class: other.
6. Zensimu lets the instructor adjust "role names and starting stock, lead times" per round; default values not published on the page read. Source: https://docs.zensimu.com/article/21-prepare-beer-game-session. Publisher: Zensimu (commercial vendor). Date: not stated. Read. Confidence: high for configurability, no values. Class: other.

### (b) Delays

7. Board game text says shipping delay (production delay at the factory) and "mailing delay" for orders exist, but the 2017 instructions give no numbers; the numbers are implied by the chip layout (two shipping boxes per link). Source: SDS instructions (see 1). Read. Confidence: high that no number is stated; the two-box inference is mine. Class: parameter-value.
8. Typical value: 2-week order delay and 2-week shipping delay between retailer, wholesaler, distributor; factory production takes 3 weeks per one O'Reilly operations text; a University at Albany archive item on a computerised version says 2 periods shipping, 2 periods order receiving, 3 periods for factory production, total order-to-receipt delay 4 periods in the board game. Source: https://oreilly.com/library/view/operations-management-for/9781118369975/13_supplement-a.html and https://archives.albany.edu/downloads/bg257z252 (blocked by bot check when fetched). Publishers: O'Reilly/Wiley text; University at Albany. Dates not stated. Snippet only. Confidence: medium (agrees with Paine's "delivery day of 2 time periods each" in item 3, which is read). Class: parameter-value.
9. Paine states the reference case "a balanced information and delivery day of 2 time periods each". Source: https://arxiv.org/pdf/2202.12786. Read. Confidence: high for this paper's model. Class: parameter-value.
10. beergame.org: "Each delivery (and production order) requires two rounds"; shipping delay can vary 1 to 3 rounds in the software. Sources: https://beergame.org/the-game/structure-rules/ (read) and https://beergame.org/software/features/ (read). Confidence: high. Class: parameter-value.
11. One student handout (via search snippet) describes order delay of one week per node; delay differs by version. Source: https://battles.dev.laser.red/beer-game-student-instructions.html. Publisher: unclear mirror site. Snippet only. Confidence: low. Class: parameter-value.
12. Temple University MIS 3537 (2016 course): Round 2 options include cutting shipping delay from 2 to 1 week and information (order) delay from 2 to 1 week, so the baseline there is 2 and 2. Source: https://community.mis.temple.edu/mis3537beaver2016/ (search snippet; the PDF link returned 404). Publisher: Temple University course site. Date: 2016. Snippet only. Confidence: medium. Class: repeat-round-design.

### (c) Demand patterns

13. Classic: 4 per week through week 4, 8 from week 5 and constant. Stated by the SDS instructions ("four cases per week until week five, and then eight per week from week five on", most effective for first-time players); Sterman's article places the rise in week 5; Paine confirms 4 to 8 after four training rounds. Sources: SDS PDF (read), MIT page (read), arXiv 2202.12786 (read). Confidence: high. Class: parameter-value.
14. beergame.org example: 5 for 5 rounds then 9. Source: https://beergame.org/the-game/structure-rules/. Read. Confidence: high. Class: parameter-value.
15. Demand is hidden from non-retailers; card deck is not revealed in advance; the debrief asks non-retailers what they think customers did, to show that internal structure produced oscillation. Source: SDS PDF. Read. Confidence: high. Class: parameter-value.
16. Software demand options: beergame.org offers "one predefined change/jump" or "a complete series of demand numbers"; Zensimu offers demand "manual or automated" (patterns not named). Sources: https://beergame.org/software/features/ (read), https://zensimu.com/beer-game/scenario/ (read). Confidence: high. Class: parameter-value.
17. Research uses other demand shapes: Cattaneo et al. 2010 compared step, noisy step, cyclic and noisy cyclic demand; a simulation calculator lists step, sinusoidal, AR(1) or constant. Sources: search-result summaries only (original paper not opened; calculator at https://metricgate.com/docs/beer-game-bullwhip-simulation/, dated May 2026). Snippet only. Confidence: low. Class: parameter-value.
18. Bullwhip persists when demand is constant and publicly announced (Croson, Donohue, Katok, Sterman, "Order Stability in Supply Chains"). Source: https://core.ac.uk/download/78053400.pdf (403 on fetch; claim from search summary). Snippet only. Confidence: medium. Class: difficulty-effect.
19. Croson & Donohue 2006 used stochastic end-customer demand; distribution not found. A separate hit giving U[0,10] (Kunze & Guendüez 2006, https://proceedings.systemdynamics.org/2006/proceed/papers/KUNZE354.pdf) is from a search summary only and may not be a beer game; the file I fetched showed no readable text. Confidence: low. Class: parameter-value.

### (d) Costs

20. Holding $0.50 and backlog $1.00 per case per week, charged at every stage; team cost is the sum across stages and weeks. Cost = total inventory x 0.50 + total backlog x 1. Sources: SDS PDF (read), MIT page (read), arXiv 2202.12786 (read, same values and "prior studies referenced above"). Confidence: high. Class: parameter-value.
21. Benchmarks from Sterman's article: average team about $2000, optimal about $200, below $1000 rare, above $10,000 not uncommon. Source: MIT page. Read. Confidence: high (1992 article, anecdotal ranges). Class: other.
22. Web version beergame.org: EUR 0.50 holding, EUR 1.00 backlog; both customisable. Sources as in 4 and 5. Confidence: high. Class: parameter-value.
23. Zensimu allows stock cost, backorder cost, and optional revenue/sale price. Source: https://zensimu.com/beer-game/scenario/. Read. Confidence: high. Class: other.
24. The SDS instructions tell facilitators to stop at week 8 or 9 when the retailer first has a backlog and explain that backlog is cumulative and costs twice as much as inventory. Source: SDS PDF. Read. Confidence: high. Class: other.

### (e) Game length and horizon

25. Players are told 50 weeks; play is halted at about 35-36 weeks ("telling the players it will be fifty weeks prevents horizon effects, where they run their inventories down"). Instructions: play as if it continues to 50 "to avoid unusual end-of-game moves". Sources: SDS PDF (read), MIT page (read). Confidence: high. Class: parameter-value.
26. beergame.org: "usually 40 to 50 rounds in total". Source: https://beergame.org/the-game/structure-rules/. Read. Confidence: high. Class: parameter-value.
27. Zensimu default template: 2 rounds (with and without information visibility) of 20 weeks; "Short Beer Game": 2 rounds of 12 weeks; 1 minute default decision timer; session 1h30-2h. Source: https://docs.zensimu.com/article/21-prepare-beer-game-session. Read. Confidence: high. Class: parameter-value.
28. Paine uses horizon T = 52 periods for learned parameters (a simulation, not human play). Source: arXiv 2202.12786. Read. Confidence: medium. Class: parameter-value.
29. Facilitated board game can run in about 1.5 hours plus at least 40 minutes debrief. Source: SDS PDF. Read. Confidence: high. Class: other.

### (f) Group size and roles

30. Four roles (retailer, wholesaler, distributor, factory); 1 or 2 players per role, 4 to 100 people per game, 4 to hundreds per Sterman. Sources: SDS PDF (4 to 100, read), MIT page (4 to hundreds, read). Confidence: high. Class: parameter-value.
31. beergame.org: each stage played by one or "better two or three" players, typically 8 to 12 per chain; software supports 3 to 5 stages and many parallel chains. Sources: structure-rules (read), features (read). Confidence: high. Class: parameter-value.
32. Zensimu: 2 to 8 roles per chain, default 4; one participant per role remotely, 2-3 per computer in person; unfilled roles played by the computer; 16 participants -> 4 teams. Source: docs.zensimu.com (read). Confidence: high. Class: parameter-value.
33. The SDS game uses a $1 ante, winner-take-all by lowest team cost, and forbids communication (out of scope but part of the standard protocol). Source: SDS PDF. Read. Confidence: high. Class: other.

### (g) Difficulty levels, difficulty effects, repeat rounds

34. No source read this run names "easy/advanced/harder" levels. The nearest: the SDS instructions say the step pattern is "most effective for first-time players", implying other patterns for experienced players, but they do not define any. Source: SDS PDF. Read. Confidence: medium (inference from one phrase). Class: difficulty-effect.
35. Stochastic lead times raise order variance and cost and strengthen bullwhip, though the effect shrinks with experience: Ancarani, Di Mauro, D'Urso, "A human experiment on inventory decisions under supply uncertainty", Int. J. Production Economics 142(1), 2013; 104 MBA students plus 24 purchasing managers. Source: https://econpapers.repec.org/RePEc:eee:proeco:v:142:y:2013:i:1:p:61-73 and https://www.iris.unict.it/handle/20.500.11769/76901. Publisher: Elsevier / University of Catania repository. Snippet only (full text blocked). Confidence: medium; the treatment structure is described inconsistently in two listings (two vs three treatments). Class: difficulty-effect.
36. Bullwhip and under-weighting of supply line persist even with constant, known demand, so demand noise is not required for the beer game to be hard. Source: item 18. Confidence: medium. Class: difficulty-effect.
37. Round 2 design at Temple (2016): demand pattern "may change" between rounds; each team made one change for Round 2, for example point-of-sale data visible to all roles, shipping delay 2 -> 1, order delay 2 -> 1. The stated aim is to show how manipulating aspects of the game changes supply-chain performance, not to prevent memorisation. Source: https://community.mis.temple.edu/mis3537beaver2016/?p=199 (search snippet; linked PDF 404). Publisher: Temple University. Date 2016. Snippet only. Confidence: medium. Class: repeat-round-design.
38. Sparling (2002) two-round format: round 2 played after students receive historical demand data and plan a strategy. Source: https://proceedings.systemdynamics.org/2005/proceed/abstracts/364.htm and related snippet; not opened. Snippet only. Confidence: low (attribution of year/author from snippet). Class: repeat-round-design.
39. Zensimu: debrief compares each round with previous rounds; default template is round 1 without and round 2 with information visibility; instructor can schedule mid-game events (change lead times, costs, capacity) and use "adaptive scenarios". Sources: docs.zensimu.com and https://zensimu.com/beer-game/scenario/ (both read). Confidence: high. Class: repeat-round-design.
40. SDS prerequisite: none of the participants have played before, "or else agree not to reveal the 'trick' of the game". Source: SDS PDF. Read. Confidence: high. This is the only direct statement about repeat-play contamination found. Class: repeat-round-design.

## Compact table: parameter -> values seen -> sources

| Parameter | Values seen | Sources (item no.) |
|---|---|---|
| Initial inventory per role | 12 (classic: SDS, Sterman, Paine); 15 (beergame.org example); configurable in beergame.org and Zensimu | 1, 2, 3, 4, 5, 6 |
| Initial pipeline per slot | 4 (SDS, Paine); 5 (beergame.org example); starts in steady state | 1, 3, 4 |
| Initial orders in order boxes | 4 (SDS, Paine); 5 (beergame.org example) | 1, 3, 4 |
| Order (information) delay | 2 weeks typical (O'Reilly, Albany, Paine, Temple); 1 week in one handout; Round-2 variant 1 | 8, 9, 11, 12 |
| Shipping delay | 2 weeks typical; software range 1-3 | 8, 9, 10, 12 |
| Factory production delay | 3 weeks in O'Reilly/Albany; 2 in beergame.org; SDS text gives none | 7, 8, 10 |
| Demand pattern | 4 then 8 from week 5 (classic); 5 then 9 after 5 rounds (beergame.org); instructor series or one jump (software); stochastic in Croson & Donohue (distribution not found); step/noisy/cyclic in Cattaneo et al. | 13-19 |
| Demand known to players | No: retailer only, deck hidden; one study announces constant demand publicly | 15, 18 |
| Holding cost | $0.50 per case per week | 20, 22 |
| Backlog cost | $1.00 per case per week (twice holding) | 20, 22 |
| Costs charged on | All four stages; team cost = sum | 20 |
| Game length | Told 50, halted about 36 (SDS, Sterman); 40-50 (beergame.org); 52 (Paine, simulation); 2x20 or 2x12 (Zensimu) | 25-28 |
| Horizon disclosed | Yes, as 50 (a false horizon, to avoid end effects) | 25 |
| Players per team | 4 roles x 1-2 people; 8-12 per chain (beergame.org); 2-8 roles (Zensimu) | 30-32 |
| Difficulty levels | None named in sources read | 34 |
| Harder setups (evidence) | Stochastic lead times worsen bullwhip (Ancarani et al.); constant known demand does not remove it | 35, 36 |
| Round-2 variations | Reduce delays, share POS data, add history data, change demand (Temple, Sparling, Zensimu) | 37-39 |

## Leads worth chasing

- Sterman (1989), Management Science 35(3), 321-339: the primary source for 36/50 weeks, four-role structure, and whether any treatment varied demand; not retrieved this run.
- Sterman, Business Dynamics (2000), chapter 17 (Beer Game): delays and the factory production delay as modelled; not retrieved.
- Wu & Katok (2006), J. Operations Management: training and communication protocols across rounds, which includes how later rounds were made different; demand distribution and lead times unretrieved (PDF redirected to a login). Open access copy at https://personal.utdallas.edu/~ekatok/learn_post.pdf did not load.
- Croson & Donohue (2006), "Behavioral causes of the bullwhip effect and the observed value of inventory information", Management Science: stochastic demand distribution and number of periods.
- Order Stability in Supply Chains (Croson, Donohue, Katok, Sterman), core.ac.uk/download/78053400.pdf: constant announced demand, short vs long delay treatments; 403 on fetch, try another mirror.
- Ancarani et al. (2013) full text: stochastic lead-time distribution and treatment structure.
- Cattaneo et al. 2010: step vs noisy step vs cyclic demand comparison.
- Narayanan & Moritz (2015): reported as using the 12/4 layout.
- Zensimu "complete instructor guide" (https://zensimu.com/resources/complete-instructor-guide/) and its template list for default values and any difficulty wording; also its changelog on scheduled disruptions.
- Temple MIS 3537 Root Beer Game assignment pages (2016, 2017) for exact round-2 rules; the PDF link was dead, the blog pages were not opened.
- Albany archive items (blocked by bot check) for the computerised-version delays.

## Looked for and could not find

- A source giving the factory production delay in the 2017 SDS board instructions (no number is stated).
- Any named "difficulty level" or "advanced preset" in a university course, paper or platform read this run.
- Distribution parameters (range, mean, spread) for random demand in Croson & Donohue or Wu & Katok.
- Seasonal, shock or ramp demand in a named human-subject course or study (only a calculator listing sinusoidal/AR(1) and the Cattaneo summary, both unread).
- Any source explicitly saying a second round uses different demand or starting conditions to prevent memorisation; only Temple's "one change per team" and Sparling's history-data round, plus the SDS first-time-players rule.
- Quantified effect of longer delays on cost or bullwhip from a source read in full.
- How courses handle end-of-game effects beyond the false 50-week horizon and stopping at 36 (Zensimu's 12- and 20-week games do not say whether the horizon is disclosed).
