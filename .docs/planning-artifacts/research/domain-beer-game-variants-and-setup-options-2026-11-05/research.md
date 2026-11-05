---
title: 'domain research: Beer Game variants, start settings and common extensions'
type: 'domain'
topic: 'Beer Game variants, start settings and common extensions'
decision: 'Which start settings (presets) and common extensions a lecturer can choose when setting up a class (FR-12, FR-13, FR-49), and which defaults suit a basic and an advanced course'
source: 'native run'
status: complete
claims_verified: 4
claims_unverified: 2
claims_disputed: 1
preset: 'standard'
validation: 'normal'
created: '2026-11-05'
updated: '2026-11-05'
---

# domain research: Beer Game variants, start settings and common extensions

**Decision this research serves:** Which start settings (presets) and common extensions a lecturer can choose when setting up a class (FR-12, FR-13, FR-49), and which defaults suit a basic and an advanced course.

Scope set by the founder on 2026-11-05: communication between players is v2 and out of scope; letting a player see inventory one step upstream is in scope.

## Executive summary

**What the evidence says to do.** Ship one well-evidenced "Classic" preset and make the other options per-class settings, not separate game modes. Offer a small set of toggles that all have precedent in teaching tools: demand pattern, delays, visibility of other roles' data, and AI fill-in. Treat "advanced" as a named bundle of those settings, because no source defines an advanced level.

**Three findings that drive this.**
1. The classic MIT/Sterman setup is well documented and matches the PRD defaults: 12 cases per role, 4 per pipeline slot, demand 4 stepping to 8 in week 5, costs 0.50 and 1.00, players told 50 weeks and play stopped at about 36 [1][2][3]. Confidence: high.
2. Delays are not settled. Shipping delay is 2 weeks (verified). Order delay is 1 week in some sources and 2 in others, and the factory production delay is 2, 3 or 4 weeks [4][5][19][20][26]. The product should expose them as settings with a stated default, not claim one "true" value.
3. Visibility is the most common teaching extension, but evidence for "see the supplier's inventory" is weak. In the one experiment that tested upstream visibility, only downstream (customer-side) information significantly lowered order oscillation; upstream information did not [13]. Nobody has tested seeing only the one neighbouring echelon.

**Biggest caveat.** Many primary papers were blocked, so several claims rest on abstracts or search snippets and are flagged. Sterman 1989 and Business Dynamics ch. 17 were not retrieved.

## 1. Variants of the game

- The classic game is the MIT Sloan System Dynamics Group board game: four roles (retailer, wholesaler, distributor, factory), one or two players per role, 4 to 100 people, no communication between positions, only the retailer sees customer demand [1][2]. Lineage: Forrester's industrial dynamics models in 1958 and 1961 [1]. Confidence: high.
- Documented variants: the Kaminsky and Simchi-Levi computerised game offers global information, centralised ordering, short lead time (1 week instead of the 2 weeks "originally employed") and stochastic demand with an instructor-set step [4]; platform variants with 2 to 8 roles [8] or 3 to 5 stages [6]; a root beer version exists for younger audiences [11][7].
- Software and physical formats differ in parameters, not in the core idea: 15 stock, 5 per slot and demand 5 then 9 on beergame.org [5], versus 12, 4, 4 to 8 on the MIT board [1].

## 2. Common start settings

| Parameter | Values seen | Sources | Confidence |
|---|---|---|---|
| Starting stock per role | 12 (classic); 15 (beergame.org example); configurable | [1][2][3][5][6] | high |
| Pipeline per slot / orders in transit | 4 / 4 (classic, steady state); 5 / 5 (beergame.org) | [1][3][5] | high |
| Shipping delay | 2 weeks standard; 1 as "short lead time" variant; software range 1 to 3 | [4][5][6][26] | high (verified) |
| Order delay | 1 week (Jarmain-style rules, CMU, MobLab) or 2 weeks (Wikipedia, Albany, Temple); MIT text gives no number | [19][20][21][26] | low, disputed |
| Factory production delay | 3 (Liuc, Albany computerised), 4 (Wikipedia, Albany board), 2 (beergame.org) | [5][19][20][26] | low, disputed |
| Demand | 4 then 8 from week 5 (classic, "most effective for first-time players"); 5 then 9 (beergame.org); instructor series or one jump; random in research | [1][3][5][6][14] | high for classic |
| Costs | 0.50 holding, 1.00 backlog per case per week, all four stages; configurable | [1][2][3][6] | high |
| Length | Told 50, stopped at about 36 to avoid end-of-horizon moves; 35 default at HBP; 40 to 50 at beergame.org; 2 x 20 or 2 x 12 at Zensimu | [1][2][5][7][8] | high |
| Team | 4 roles, 1 to 2 players each; 2 to 8 roles in Zensimu | [1][8] | high |

**No source names difficulty levels.** The nearest hint is that the 4-to-8 step suits first-time players [1]. The evidence for what makes the game harder is thin: stochastic lead times raise bullwhip and cost (search summary only, medium-low) [22], and bullwhip persists even with constant, known demand [25] (snippet only). The transentis platform mentions an "advanced preset" without defining it [10]. An "advanced course" preset therefore has to be designed, not copied.

**Repeat rounds.** The only precedents change one factor per round: Temple 2016 had each team change one thing for round 2, such as sharing point-of-sale data or cutting a delay [21]; Zensimu's default pairs a round without and a round with visibility [8]. No source says a changed round prevents memorisation; the SDS instructions only say participants must not have played before [1].

## 3. Common extensions

Ranking for teaching (medium-low confidence; no usage survey exists): visibility of information, then lead times, then demand pattern, then batch size and costs, then computer fill-in players. VMI, centralised ordering, promotions and rationing appear in theory [23] but not as vendor options [8][9][12]. Capacity limits exist as a vendor option in one platform only [27].

| Extension | Teaching use | Evidence of effect | Software effort |
|---|---|---|---|
| Visibility (own, downstream, upstream, all; inventory, backlog, orders, customer demand) | Common: HBP, Forio/Darden, beergame.org, Zensimu [6][7][8][12] | Mixed, see below | Toggle matrix per role and field |
| Shorter or different delays | Common [8][21] | Shorter cycle times help [17] | Integer parameters |
| Demand pattern (step, series, random with seed) | Common [6][7][9] | Pattern changes whether POS data helps [17] | Dropdown plus seed |
| Capacity limit (weekly maximum shipment per role) | Rare, one vendor [9][27] | Raises inventory and backlog costs in simulation [28]; no human experiment found | One integer per role, excess stays as backlog |
| Batch size, minimum order | Rare, vendor only [9] | None found | Parameters |
| Centralised ordering / VMI | Kaminsky and Simchi-Levi only [4] | No human experiment found | Structural change |
| Stochastic lead times | Research [22] | Raises bullwhip (snippet) | Needs seed and rule |
| Computer fill-in players | Common [8][10][7] | Rule-based, DQN and LLM bots exist [18][24] | Already planned |

**Visibility, the founder's question.**
- Croson and Donohue (2005): treatments were baseline, upstream-only (own inventory plus all upstream members' inventories), and downstream-only. Mean order variance was 80.66 baseline, 55.10 upstream-only (not significant, p=0.234) and 30.10 downstream-only (p=0.044). "Upstream" there means all upstream echelons, not just the supplier one step up [13]. Confidence: high (full text read).
- Croson and Donohue (2006) showed all four players all four inventory positions: bullwhip reduced "somewhat", and 42 of 44 subjects still underweighted the supply line [14]. Gains are partial. Confidence: high.
- Sharing point-of-sale data helps upstream players when demand is stable (abstract only) [15] but "does not always help" and can distract when demand keeps changing [17] (abstract only). Gonçalves and Moshtari (2021) found information makes subjects react less to their own inventory and watch the supply line more [16].
- No total-cost result for these treatments was found. An LLM-agent preprint reports sharing cutting order variance (for example 39.43 to 20.15 for one model), but this is bot data, not human data [18].
- **Implication.** "See the supplier's inventory one step upstream" is cheap to build and fits the teaching practice of a round with visibility, but the best-supported variant is downstream and customer-demand information, and one-step-upstream has not been tested.

**Capacity, added at the founder's request.**
- Zensimu is the only platform read with a documented capacity setting: "maximum shipment", a weekly cap per role on units shipped even when stock is available, so stock and backlog can coexist; it can be set on one or several roles and changed by scheduled events [27]. The only value found is 6, used as an illustration (1.5 times the classic demand of 4). No default is documented [27]. Confidence: medium (vendor).
- The classic game and beergame.org have no capacity limit [1][2][5]. Forio, Harvard, transentis, MobLab and open-source games were not checked for it, so this is not evidence of absence.
- A system dynamics study of transport-capacity limits in the Beer Game reports higher inventory and backlog costs; the cap values were not retrievable [28] (abstract only). Confidence: low.
- Rationing: when a supplier cannot fill all orders, proportional-to-orders allocation drives over-ordering, and allocation by past sales is the remedy firms use [23]. Cachon and Lariviere (1999) show in theory that uniform allocation removes order inflation while proportional or linear allocation induces it [29] (abstract only). Even without capacity limits about 20% of human players hoard or phantom-order when deliveries falter [30], which suggests capacity would worsen it (inference, not evidence).
- No source says capacity makes the game harder, gives a convention for the cap, or reports a human experiment crossing capacity with allocation rules.
- **Design implication (inference).** In the linear four-role chain each role has exactly one customer, so no allocation rule among customers arises: a cap simply limits shipments and the rest stays as backlog. Allocation rules only matter in networks with several customers per supplier, which are out of scope.

## Cross-dimension insights

- Teaching tools make visibility a round-two switch (Zensimu's default pair, Temple's one-change rule) [8][21]. That fits the PRD's Replay: the Replay scenario can change one named setting, which also makes the comparison with the Class game interpretable.
- Because delays and demand are the settings most often changed, and the delays are disputed in the literature, the default values matter less than showing the lecturer exactly what each preset contains.

## Recommendations

1. **Presets (FR-11, FR-12).** Provide "Classic" (PRD defaults, order delay 2 as the founder chose) and "Advanced course" as named bundles; each setting stays editable. Basis: high for Classic; the Advanced bundle is a design choice with no source, so say so in the PRD. Feeds FR-11, FR-12, Open Question 5.
2. **Delays as settings.** Expose order, shipping and production delay separately with defaults 2, 2, 2 and allowed ranges 1 to 3. Basis: order and production delay are disputed in sources (low confidence), shipping verified. Feeds FR-12.
3. **Demand patterns.** Keep step (default), fixed series and random with seed (FR-13); add nothing else in v1. Basis: high.
4. **Visibility toggle.** Add a per-class setting for what each role can see of other roles: nothing (default), one step upstream, one step downstream, customer demand to all. Evidence supports downstream and customer-demand sharing better than upstream (medium); one-step-upstream is untested, so treat it as a lecturer's choice, not a claim about learning. Feeds a new FR near FR-12 and the AI player prompts.
5. **Replay scenarios (FR-49).** Define a scenario as "Classic plus one changed setting" from the same toggles (longer delay, random demand, visibility on, starting with backlog). Basis: precedent for one-change rounds (medium-low). Starting with backlog or low stock has no source and must be designed.
6. **Capacity (added by the founder).** Offer an optional weekly maximum shipment per role, off by default, with excess staying as backlog; the lecturer can set it for one role or all and use it in the Replay scenario. No allocation rule is needed in a linear chain. Basis: one vendor precedent [27], low-quality effect evidence [28]; the default off and any cap value are design choices. Feeds FR-12.
7. **Defer.** Batch size and minimum order, centralised ordering, promotions, rationing and stochastic lead times: little teaching evidence and structural work. Basis: medium-low.
8. **Hidden horizon.** Keep the told-50, stop-at-36 pattern as the Classic default; it is the only documented practice [1][2].

## Open questions

- Order delay (1 or 2 weeks) and factory production delay (2, 3 or 4): read Sterman 1989 (MIT working paper SWP-1933, Management Science 35(3)) or Business Dynamics ch. 17. A retry of the MIT DSpace copy was blocked by HTTP 429.
- Distribution and parameters of random demand in Croson and Donohue and Wu and Katok.
- Whether seeing only the supplier's inventory one step upstream changes behaviour: untested; could be a pilot question.
- Instructor usage frequencies for each extension: no survey found.
- The Forio facilitator guide (behind login) would settle MIT/Forio defaults.

## Source appendix

| n | Claim or finding it supports | Publisher | Pub. date | Accessed | Confidence |
|---|---|---|---|---|---|
| [1] | Classic setup, costs, demand, 50/36 weeks, no communication, delay boxes without week counts | [System Dynamics Society, Beer Game instructions](https://systemdynamics.org/wp-content/uploads/2020/12/BEER-GAME-INSTRUCTIONS.pdf) | 2017-05 (orig. 1992) | 2026-11-05 | high |
| [2] | Sterman's account: 12 cases, equilibrium, 50/36, benchmark costs | [MIT, Sterman, Teaching Takes Off](https://web.mit.edu/jsterman/www/SDG/beergame.html) | 1992 | 2026-11-05 | high |
| [3] | Typical layout 12/4/4, four training rounds, step 4 to 8 | [arXiv 2202.12786, Paine, MIT Sloan](https://arxiv.org/pdf/2202.12786) | 2021-12 | 2026-11-05 | high |
| [4] | Computerised variants: global information, centralised, short lead time, stochastic demand; 2-week original delivery | [Kaminsky and Simchi-Levi](https://kaminsky.ieor.berkeley.edu/Reprints/PK_DSL_98b.pdf) | 1998 | 2026-11-05 | high |
| [5] | 15/5/5, demand 5 then 9, 40 to 50 rounds, production order needs two rounds | [beergame.org, structure and rules](https://beergame.org/the-game/structure-rules/) | undated | 2026-11-05 | medium |
| [6] | Configurable parameters, 3 to 5 stages, visibility options, delay 1 to 3 | [beergame.org, software features](https://beergame.org/software/features/) | undated | 2026-11-05 | medium |
| [7] | HBP Root Beer Game V2 presets, POS visibility, about 35 weeks, single-player mode | [Harvard Business Publishing product sheet](https://s3.amazonaws.com/he-product-images/docs/M11406-RootBeerGameV2.pdf) | undated | 2026-11-05 | high |
| [8] | Zensimu templates, rounds with and without visibility, 2 to 8 roles, bots, timer | [Zensimu docs](https://docs.zensimu.com/article/21-organize-beer-game-session) | undated | 2026-11-05 | medium |
| [9] | Zensimu scenario builder: batch, capacity, events | [Zensimu scenario](https://zensimu.com/beer-game/scenario/) | undated | 2026-11-05 | medium |
| [10] | transentis: AI players, multigame, "advanced preset" | [transentis FAQ](https://beergame.transentis.com/docs/faq) | undated | 2026-11-05 | medium |
| [11] | MIT/Forio class setup and admin options | [Forio, MIT simulation info](https://sites.google.com/forio.com/mit-simulation-info/beer-game) | undated | 2026-11-05 | high |
| [12] | Forio/Darden: instructor sets what teammates can share | [Forio Darden catalog](https://forio.com/catalog/darden-beer-game-supply-chain-simulation) | undated | 2026-11-05 | medium |
| [13] | Upstream versus downstream information: order variance 80.66, 55.10, 30.10 | [Wiley, System Dynamics Review 21(3), Croson and Donohue](https://onlinelibrary.wiley.com/doi/abs/10.1002/sdr.320) | 2005 | 2026-11-05 | high (full text via Wharton copy) |
| [14] | Inventory sharing reduces bullwhip somewhat; supply line still underweighted | [Management Science 52(3), Croson and Donohue](https://econpapers.repec.org/RePEc:inm:ormnsc:v:52:y:2006:i:3:p:323-336) | 2006 | 2026-11-05 | high |
| [15] | POS sharing reduces upstream order oscillation in stable demand | [Production and Operations Management, Croson and Donohue](https://repository.upenn.edu/oid_papers/172) | 2003 | 2026-11-05 | medium (abstract only) |
| [16] | Information shifts attention to supply line | [Wiley via IDEAS, Gonçalves and Moshtari](https://ideas.repec.org/a/bla/sysdyn/v37y2021i2-3p126-154.html) | 2021-04 | 2026-11-05 | high |
| [17] | Shorter cycle helps; POS sharing not always | [Management Science 50(4), Steckel, Gupta and Banerji](https://econpapers.repec.org/RePEc:inm:ormnsc:v:50:y:2004:i:4:p:458-464) | 2004 | 2026-11-05 | medium (abstract only) |
| [18] | LLM agents amplify orders; information sharing reduces variance (bot data) | [arXiv 2604.17220, Jiang et al.](https://arxiv.org/html/2604.17220) | 2026-06 | 2026-11-05 | medium (preprint) |
| [19] | Wikipedia: 2-week order delay, 4-week production, physical formats | [Wikipedia, Beer distribution game](https://en.wikipedia.org/wiki/Beer_distribution_game) | undated | 2026-11-05 | low |
| [20] | 2 order, 2 shipping, 3 production (computerised) | [O'Reilly operations text](https://oreilly.com/library/view/operations-management-for/9781118369975/13_supplement-a.html) | undated | 2026-11-05 | low (snippet) |
| [21] | Round 2: one change per team (POS, delay 2 to 1) | [Temple University MIS 3537](https://community.mis.temple.edu/mis3537beaver2016/) | 2016 | 2026-11-05 | medium (snippet) |
| [22] | Stochastic lead times raise bullwhip | [Int. J. Production Economics 142(1), Ancarani et al.](https://econpapers.repec.org/RePEc:eee:proeco:v:142:y:2013:i:1:p:61-73) | 2013 | 2026-11-05 | medium-low (snippet) |
| [23] | Four causes of bullwhip; constant known demand does not remove it | [Management Science 43(4), Lee, Padmanabhan and Whang](https://econpapers.repec.org/RePEc:inm:ormnsc:v:43:y:1997:i:4:p:546-558) | 1997 | 2026-11-05 | high (cause list) |
| [24] | DQN agent for the Beer Game | [MSOM 24(1), Oroojlooyjadid et al.](https://econpapers.repec.org/RePEc:inm:ormsom:v:24:y:2022:i:1:p:285-304) | 2022 | 2026-11-05 | medium |
| [25] | Bullwhip persists with constant, announced demand | [Croson, Donohue, Katok and Sterman, Order Stability in Supply Chains](https://core.ac.uk/download/78053400.pdf) | 2014 | 2026-11-05 | medium (snippet; fetch returned 403) |
| [26] | Delay values 1 vs 2 weeks; shipping 2 verified; production 2, 3 or 4 | Liuc, CMU DDMLab, MobLab, Albany (see digests/verify-delays-r2-1.md) | various | 2026-11-05 | low to medium |
| [27] | Zensimu maximum shipment capacity setting, example value 6 | [Zensimu changelog, capacity maximum shipment](https://feedback.zensimu.com/changelog/beer-game-capacity-maximum-shipment) and [advanced model docs](https://docs.zensimu.com/article/47-introduction-to-the-advanced-beer-game-model) | 2024-06 (docs updated 2026-04) | 2026-11-05 | medium |
| [28] | Transport-capacity limits raise inventory and backlog costs in a Beer Game simulation | Int. J. Logistics Research and Applications 17(1), Spiegler and Naim, [Brunel repository](https://bura.brunel.ac.uk/handle/2438/11422) | 2014 | 2026-11-05 | low (abstract only) |
| [29] | Uniform allocation removes order inflation; proportional or linear induces it (theory) | [Kellogg, Cachon and Lariviere](https://www.kellogg.northwestern.edu/faculty/research/detail/1999/an-equilibrium-analysis-of-linear-proportional-and-uniform-allocation) | 1999 | 2026-11-05 | medium (abstract) |
| [30] | About 20% of human players hoard or phantom-order when deliveries falter, with no capacity limit | [MIT, Sterman and Dogan, I'm not hoarding](https://mitmgmtfaculty.mit.edu/jsterman/imnothoarding/) | 2015 | 2026-11-05 | medium |

## Staleness map

Claims that age fastest are platform capabilities (vendor pages, undated, re-check within 18 months) and the 2026 LLM-agent preprint (re-check within 6 months). The classic parameter values and the 1998 to 2006 experiments do not age. Earliest re-check: about 2027-05, for the preprint [18].
