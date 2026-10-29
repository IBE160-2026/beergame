---
title: 'competitive research: Beer Distribution Game products and AI-driven bots/engines'
type: 'competitive'
topic: 'Beer game competitors incl. AI bots/engines'
decision: 'Does any incumbent already offer bot-filled roles or repeatable solo practice with an AI debrief; informs PRD differentiation and positioning A vs B'
source: 'native run (web fan-out, 3 rounds, 16 digests)'
status: complete
preset: 'deep'
validation: 'normal'
created: '2026-10-26'
updated: '2026-10-26'
claims_ledger: 'numeric-ref load-bearing claims: verified 9, unverified 5, disputed 1, overturned 1 (superseded working lines in .memlog.md ignored)'
---

# Competitive research: Beer Distribution Game products and AI-driven bots/engines

**Decision this research serves:** Does any incumbent already offer bot-filled roles or repeatable solo practice with an AI debrief? The answer informs PRD differentiation and the positioning choice (A: friction-free beer game vs B: repetition + explanation).

## Executive summary

**The brief's central novelty claim does not survive. Bot-filled roles and solo replay already exist, and for free.** The claim "no product treats this as repeatable practice" is false as worded. A narrower claim survives.

1. **Bot-filled roles are table stakes, and the "AI" is simple rules.** At least seven products fill empty seats with computer players: En Dash, transentis, Zensimu, Forio's Root Beer Game, Responsive eBeer, Skill Dynamics and the open-source siemsene/beergame. Where the logic is visible it is a one-line ordering rule. En Dash's client code orders "last incoming order + 0.5 × (12 − inventory + backlog), ±15% noise" [2]. Zensimu describes a "basic net stock calculation" [10]. None documents difficulty tiers or personas.
2. **Solo replay exists too.** **beergame.endash.us** (launched on Show HN 2026-08-25, JS built 2026-09-17) offers free solo play against three AI roles, a four-role sandbox, a replay route and a 10-question debrief [1][2][4]. It has no traction signal (1 HN point) and reads as a consulting lead magnet. Zensimu (free single-player plan) [11], transentis (free solo) [6] and isee ($15 single-user) [31] also offer solo play.
3. **What nobody documents is the open ground:**
   - LLM-driven or behaviourally distinct opponents with a human seat.
   - Documented randomised per-run demand. Fixed or seeded demand is verified for En Dash, Near Beer and Cohen, and unstated at most others. Skill Dynamics markets "fluctuating" demand and the Couscous Game claims variable demand [39] (low confidence).
   - Any LLM-generated, decision-level debrief explaining causal chains.
   - Cohort-level analytics beyond charts, such as per-student decision-level diagnosis (Zensimu and transentis do document dashboards and exports).

   A skeptic pass found one counterexample to the strongest wording: an abandoned Hugging Face prototype with a human Distributor against GPT-4o-mini agents [32]. The defensible restatement is in the Contrary evidence section.
4. **LLM opponents are not a free win.** In Long et al., the best configuration cuts cost up to 80% against Georgia Tech student teams. Default configurations show run-to-run variation (CV) of 26–52% (the paper's text says 26–45%), and guardrails or post-training bring it to about 12–13% [34]. Human-likeness was not measured there. Other work reports myopic behaviour and the right direction of bias but different response distributions [36][37]. Evidence on whether LLM agents "preserve" bullwhip is mixed. The SSRN paper the brief relies on was not found in Crossref, DataCite, OpenAlex or web search; SSRN itself blocked access [38].
5. **Pricing has a free floor and a paid ceiling.** The free floor is transentis, En Dash, Cohen and beergame.org. The paid ceiling is Forio at $168 per person [18][19]. eBeer sits at $10–20 per student and has not moved since 2021 [23]. Zensimu is the commercial mid-market, with 2024 prices of €17.5 per participant and no public prices now [14][11].

**Biggest caveat:** evidence for the replay thesis itself is thin and mostly abstract-level. No retrieved study separates repetition from debrief [41][42][43][44][45], and there is almost no independent lecturer or student voice (one THE article [39]). A–B positioning should be decided with that in mind.

## 1. Offer and feature teardown

| Product | Bot-filled roles | Solo / replay | Demand | Debrief | Classes / LMS |
|---|---|---|---|---|---|
| **En Dash** (free) | Yes, rule-based in browser for solo [2]; server-side logic for multiplayer unknown [3] | Solo vs 3 AI, 4-role sandbox, replay route (UI not stepped through) [2][3] | Fixed 4→8 at week 5; host-editable steps; no random generator [2][3] | 10 scripted questions plus data readout [4] | Free host account; no LMS found [3] |
| **transentis** (free) | "AI players", logic undocumented [6] | Solo always as Retailer; Multigame up to 64 players [6] | Not stated | Dashboard, CSV/JSON/PDF export [7] | Free account; no LMS found |
| **Zensimu / beergameapp.com** | "Computer" fills roles, net-stock rule, timer auto-play [10] | Free single-player plan [11] | Options not specified on any page read | Auto report: charts, PDF/Excel, slides; no AI mentioned [52] | SSO on Enterprise only [11] |
| **Forio MIT Beer Game** | Not mentioned [18] | Not mentioned [18] | Not stated | Facilitation guide; materials behind request [18] | Console behind demo [18] |
| **Forio Root Beer (Harvard)** | "Optional computer-controlled player" [19] | Single-player mode [19] | Scenarios "customizable" [19] | 1 h facilitated; slides locked [19] | Behind demo |
| **Responsive eBeer** | "Server can play the student's position" [22] | Not stated | Not stated | Browser debrief of completed games [22] | Team creation and monitoring [22] |
| **Skill Dynamics** | Solo Distributor vs "AI bots", logic undisclosed [5] | Lead-form gated [5] | "Fluctuating" (marketing) [5] | None stated | n/a |
| **Cohen / CUNY** (CC0) | None; one shared device [29] | No | 20 seeded presets [29] | Four prompts, CSV/PNG [29] | none |
| **siemsene/beergame** (4 stars) | "Beer-GPT" robo-players, simple rule, not an LLM [30] | No | Not stated | Dashboard, leaderboard [30] | Host dashboard |

Also found:
- **MA-system** is a consultant-led service. Its only self-serve evidence is a JS app that would not render, so its "ghost players" are unconfirmed. They were reported from its /Rules page in round 1 and not seen on two other MA-system pages; /Rules was not re-fetched [26].
- **Kearney's iOS app** shows v2.0.3, last updated 2020-10-02, on a third-party listing only, so I read it as probably abandoned. The Apple listing exists but the current version is unconfirmed [25].
- **Fathomd's** asynchronous game is human-only and dates from 2021 [27].
- **Eureka/IESE** is real-time multiplayer with no bots found and quote-only pricing [28].
- **isee systems** sells a $15 single-user game against an automated retailer [31].
- **beergame.org** is free, and its only dated item is a 2019 welcome post [47].
- **The Couscous Game** has no discoverable repo, licence or bot and solo features [39].

Confidence: high on En Dash solo-bot behaviour (read from code) and on Forio page wording; medium on Zensimu wording and on everything resting on vendor marketing pages; low on MA-system and Skill Dynamics bot logic.

## 2. Pricing and packaging

- **Forio:** $168 per person for both the MIT and Root Beer games [18][19], confirmed on live pages. The Forio pricing page's site-wide starting price said "from $165/seat" (not beer-game-specific) in snapshots from 2026-01-19 to 2026-06-13 and says $168 now, with the minimum changing from 100+ to 15+ seats [20]. Competitor-sourced figures ($16/$48 on Zensimu's Harvard/Forio comparison page [49], $150 from an undated blog snippet [50]) conflict with the list price and are unverified; Zensimu's guide itself gives $160–165 [12]. Confidence: high for $168, low for direction (+$3 over four months).
- **Responsive eBeer:** $20 list, $12 student, $10 academic per student, identical across snapshots from 2021 to March 2026, on a page last updated 2024-04-22 [23]. Confidence: high.
- **Zensimu:** €17.5 per participant and €700 for a conference plan, plus €2,040 for the annual plan, in April 2024 [14]. By June 2026 the plans are Free, Conference and Enterprise with a 50% university discount. Prices were not captured in the JS-rendered June snapshot and the live page shows none [15][11]. Its own comparison guide gives $5–40 per player with internal contradictions [12]. There is no firm current list price. Confidence: low.
- **Forio Near Beer:** a single-player funnel page, reported free from indirect and possibly stale sources (fixed, known demand of 10 then 15 cases a week), that upsells to the paid MIT game [24].
- **Free:** transentis [7], En Dash ("free to play and free to host") [3], Cohen [29], beergame.org [47]. **Low-cost:** isee $15 single-user [31]. **Quote-only:** Eureka [28], Fathomd [27].
- **Pattern:** the free tools are lead generators for consulting or training (transentis → Metapad [7], En Dash [3], Skill Dynamics [5]). A student price competes with that free floor.

## 3. Positioning and messaging

- **Forio / MIT / Harvard:** the credible academic brand and the established channel. MIT's page (dated 2022-01-05) simply sends non-academic users to Forio [21]. The Harvard game is sold as one product [19].
- **Zensimu:** positions on instructor tooling, scale (claims "4 to 600" on beergameapp.com, "1000+" elsewhere, unverified) and an automated debrief, and ranks itself first in its own comparison guide [12][13]. The guide says no provider makes bot or AI claims (paraphrase; competitor sales content), which Zensimu's own "Computer" role and Forio's computer-controlled player make misleading [10][12][19].
- **transentis:** the homepage says "hundreds of players", while its FAQ gives a default Multigame cap of 64 (more on request) [6][7]. That is a mild claim-versus-docs gap.
- **En Dash:** "Choose a role, AI handles the rest" [51]. Solo bots are client-side rules [2]; multiplayer bot logic is unseen.
- **Takeaway:** nobody claims behaviourally realistic or LLM opponents. "AI" in this market means a computer fills a seat.

## 4. Trajectory

- **transentis:** free beer game, but the company is pivoting to the Metapad AI digital-twin platform, with three German webinars scheduled 12, 18 and 26 November 2026 [7]. The RL-notebook repo was last pushed 2023-03-01 [9]; the web game's source repo was not found. My reading is a lead magnet, not a priority product (interpretation). Confidence: medium for the pivot, low for the reading.
- **Zensimu ApS:** Copenhagen, registered 2024-02-20, one employee, net result about DKK 449k for FY2025 [16][17]. The product has been on sale since about 2021–22, so the 2024 entity is probably a successor. No funding, jobs or AI announcements found. Small and profitable.
- **Forio:** the site-wide starting price rose $3 between two data points (low confidence) [20]. No beer-game AI release found. Its AI coaching work relates to a different product.
- **En Dash:** actively built (assets dated 2026-09-17) but with essentially no external traction [1][2].
- **Stale:** MA-system (last dated news is 2017-09-28 per round 1, though a search summary mentioned a 2024 release), Fathomd (2021), Kearney (2020), beergame.org (2019) [26][27][25][47].
- **Pricing history:** earliest pricing snapshots are eBeer 2021-07, Zensimu 2022-06 and Forio 2026-01. Wayback was reachable only via the CDX API. Confidence: medium.

## 5. Customers' voice

Independent voice is almost absent.
- **The one strong source is a THE Campus article** (Abrache, Al Akhawayn University, 2026-06-07). It says the game is "slow to run", "surprisingly fragile" and predictable under fixed demand, and that few students could explain how their decisions led to the outcome. He built an open-source "Couscous Game" with variable demand; a capstone student later built a multiplayer version [39]. It does not mention AI, absentees or remote play.
- **Absentees.** The only quantitative figure is "up to 25%" of students with conflicts, from a single University of Calgary poster abstract with no survey results [40]. Four vendors built workarounds (Zensimu computer fill, eBeer server play, Fathomd async, HBP "inactivate absent students"), which suggests, but does not establish, the need (low-medium confidence).
- **Fill quality.** One Zensimu reviewer (5/5, October 2022, corporate trainer) said that when there are not enough players "computer did not play very well". This is a snippet from a rating site [48], so confidence is low.
- **Not found:** student voice, app-store reviews, Reddit (blocked), evidence of students replaying on their own, and any willingness-to-pay statements beyond vendor price lists.

## 6. AI bots, engines and LLM agents

- **Commercial and free products:** no source documents LLM-driven opponents with a human seat [5][1][6][10]. Where the logic is visible it is rules; for Skill Dynamics, transentis and En Dash multiplayer it is undisclosed, so "non-LLM" there is inference (medium confidence). Zensimu's computer is explicitly a net-stock formula [10]. En Dash's solo bots are explicitly rules [2]. transentis's "AI players" are undocumented, and no source establishes a link to its Q-learning notebooks [6][8]. Skill Dynamics's logic is undisclosed because it sits behind a lead form [5].
- **Open source:** among the repos found, star counts are low (28 or fewer), though siemsene/beergame reports about 200 players a day [30]. The most-starred web repo (MironV/beerdistribution) has 28 stars and was last pushed in 2021. DeepBeerInventory-RL has 91 stars but is legacy research code with no UI. LLM-agent repos have 0–1 stars. The one Gym-style environment found is orlov-ai/beer-game-env (17 stars, 2019). PyPI and npm returned 404 for the names tried.
- **Hugging Face prototype** (Lilli98/Beergamesimulation, MIT licence, created 2025-09-09): human Distributor, GPT-4o-mini opponents, and an LLM-generated order suggestion for the human. It was in `BUILD_ERROR` when queried and is an experiment harness [32].
- **Research systems:**
  - The Harvard/MIT/Georgia Tech GenAI Beer Game puts LLMs in all four roles, with no human seat and no code link [33].
  - SupplyNet (arXiv 2606.24694) lets a user pick a role against gpt-4o agents. It is a graph-based supply-chain simulation, not the classic game. The user study had 14 participants, perceived understanding only, no code found, and a session cost estimate of $0.25–2.00 [35].
- **Human-likeness is mixed.**
  - Long et al.: costs run up to 80% below student teams in the best configuration, but default configurations are erratic (CV 26–52%, "agent bullwhip"), and majority voting did not reduce it. Guardrails or post-training cut CV to about 12–13%. Human-likeness was not measured [34].
  - Zhang et al.: across behavioural operations experiments, LLMs reproduce the direction of human biases but not the response distributions; a beer-game component is unverified [36].
  - Jiang et al.: agents act myopically [37].
- **No LLM debrief or coach** in any beer-game product. En Dash's "insight" is hard-coded text [4]; no AI is mentioned for Zensimu's report [52].

## Cross-dimension insights

1. **The wedge cannot be "AI bots".** Bots are common, free and simple. The undocumented ground is bot *quality and variety* (documented personas and difficulty), per-run demand variation, and a decision-level explanation of why the outcome happened. A similar gap is named by the THE author [39] and, in abstract-level paraphrase, by the System Dynamics Review authors, who say the debrief needs work [45].
2. **Reproducibility conflicts with LLM opponents.** Cohort-comparable results need deterministic, seeded opponents. default-configuration LLM agents show 26–52% run-to-run variation, reduced to about 12–13% with guardrails or post-training [34]. A rule-based or RL default with LLM used for debrief or optional personas is more consistent with a lecturer product.
3. **Competitors are funded by something else.** The free tools are consulting lead magnets and so are unlikely to out-invest a focused product (interpretation). Market size is unknown; eBeer's flat $10–20 list and Zensimu's small profitable firm are weak signals (low confidence).
4. **Unit economics look workable.** SupplyNet estimates $0.25–2.00 per gpt-4o session for a different, graph-based game [35]. At the top of that range a $10–20 price buys 5–10 sessions, at the bottom 40 or more; debrief cost is excluded (low confidence).

## Contrary evidence

A fresh-context skeptic searched for counterexamples to "no product lets a human learner play or replay against LLM opponents, or offers an LLM debrief". It found one: the Hugging Face prototype [32]. It also found near-misses: the GenAI Beer Game has no human seat [33], and beergame.happily.ai is a human-only companion app [46]. Residual risks:
- En Dash's multiplayer bots run server-side and were not inspected.
- Skill Dynamics's bots are unseen behind a lead form.
- GPT Store, Gem and artifact libraries are poorly indexed.
- Queries in Norwegian, Swedish, Danish and French, and app-store searches, were not run.

**Defensible restatement:** as of 2026-10-26 no maintained, learner-facing beer game product is documented as using LLM-driven opponents with a human seat or an LLM-generated debrief. Only research prototypes and LLM-only simulations were found.

## Recommendations

Confidence is stated for each.

1. **Brief: rewrite the competitive claims** (Why Now #3, Risk #1, "What Makes This Different"). Add En Dash, name Zensimu, and replace "none attack the one-attempt constraint" with the narrower claim above. *Basis: high confidence; code read directly.*
2. **PRD differentiation: target the undocumented ground.** Bot personas with documented behaviour, seeded per-run demand variation, a decision-level debrief, and lecturer analytics. *Basis: medium; absence of evidence in pages read, not hands-on play.*
3. **Positioning A vs B: B holds only if the debrief and progression layer is the product.** A ("beer game without friction") is crowded and free [1][6]. B's "repetition" is partly delivered already; its remaining distinctness is explanation. *Basis: medium; a founder decision, testable in the founder's own course.*
4. **Brief: fix the LLM claims.** Replace "LLM agents preserve bullwhip" with the mixed evidence [34][36][37]. Verify or drop the SSRN citation [38]. Consider rule-based or RL defaults for reproducibility. *Basis: medium; the evidence is mixed and the SSRN paper is unverified.*
5. **Pricing:** use $10–20 per student (eBeer, Zensimu 2024) as the institutional anchor and $168 as the premium ceiling. A student tier competes with free. *Basis: medium; Zensimu's current prices are unknown.*
6. **Next research:** hands-on play of En Dash multiplayer, Zensimu's free solo and Skill Dynamics (via its form); lecturer interviews; find the Couscous Game repo. *Basis: gaps listed below.*

## Open questions

| Question | What would answer it |
|---|---|
| Do En Dash's server-side bots use rules or an LLM? | Play a mixed human/AI session. |
| What do Skill Dynamics's bots do? | Submit the lead form (outward-facing; needs user's go-ahead). |
| Does the SSRN 5266281 paper exist? | SSRN access in a browser, or ask the founder where the brief's citation came from. |
| Does repetition itself improve learning? | Full texts of Jeong & Hong 2011 and Martin et al. 2004, or a pilot in the founder's course. |
| How often are classes short of players? | Lecturer interviews; only the Calgary "up to 25%" poster exists. |
| What are Zensimu's current prices? | JS-rendered pricing page or a quote request. |
| Does MA-system really offer ghost players? | Re-fetch its /Rules page. |
| Does the Couscous Game have a repo or licence? | Contact the author; search the Springer paper. |
| Market size and number of courses running the game | Not found in any credible source. |

## Source appendix

| # | Finding it supports | Publisher | Date | Accessed | Confidence |
|---|---|---|---|---|---|
| 1 | En Dash Show HN, 1 point; free; lead magnet | [Hacker News (Algolia)](https://hn.algolia.com/api/v1/items/49434038) | 2026-08-25 | 2026-10-26 | high |
| 2 | En Dash bot rules, solo, sandbox, fixed demand | [En Dash client JS](https://beergame.endash.us/assets/game-store-Y9g3exkA.js) | 2026-09-17 | 2026-10-26 | high |
| 3 | En Dash multiplayer, host controls, free, no LMS | [En Dash](https://beergame.endash.us/for-instructors) | undated | 2026-10-26 | high |
| 4 | En Dash scripted debrief | [En Dash client JS](https://beergame.endash.us/assets/debrief-DjkZM_KC.js) | 2026-09-17 | 2026-10-26 | high |
| 5 | Skill Dynamics solo with "AI bots", lead-form gated | [Skill Dynamics](https://skilldynamics.com/supply-chain-beer-game/) | undated (2026 footer) | 2026-10-26 | medium |
| 6 | transentis AI players, solo, Multigame cap | [transentis FAQ](https://beergame.transentis.com/docs/faq) | undated | 2026-10-26 | high |
| 7 | transentis free, dashboard/exports, Metapad pivot | [transentis](https://beergame.transentis.com/) | 2026 | 2026-10-26 | high |
| 8 | transentis Q-learning notebook not tied to web game | [transentis BPTK](https://bptk.transentis.com/model_library/beergame/beergame_ql.html) | undated | 2026-10-26 | medium |
| 9 | transentis beergame repo last pushed 2023-03-01 | [GitHub API](https://api.github.com/repos/transentis/beergame) | 2023-03-01 | 2026-10-26 | high |
| 10 | Zensimu computer fill, net-stock rule, timer auto-play, report | [Zensimu](https://zensimu.com/resources/large-sessions-guide) | undated | 2026-10-26 | medium |
| 11 | Zensimu plans, free solo, SSO, no public prices | [Zensimu](https://zensimu.com/pricing) | undated | 2026-10-26 | medium |
| 12 | Zensimu comparison guide: conflicting prices, "no provider has bots" | [Zensimu](https://zensimu.com/resources/best-beer-game-simulations-comparison-guide/) | undated | 2026-10-26 | low |
| 13 | beergameapp.com is a Zensimu property | [beergameapp.com](https://beergameapp.com) | undated | 2026-10-26 | medium |
| 14 | Zensimu 2024 prices | [Wayback](https://web.archive.org/web/20240424210259id_/https://zensimu.com/pricing/) | 2024-04-24 | 2026-10-26 | medium |
| 15 | Zensimu plans restructured, no prices captured | [Wayback](https://web.archive.org/web/20260611185327id_/https://zensimu.com/pricing/) | 2026-06-11 | 2026-10-26 | medium |
| 16 | Zensimu ApS registry: 1 employee, profitable | [Proff.dk](https://www.proff.dk/firma/zensimu-aps/kc3b8benhavn-v/dataprogramvare-og-udvikling/0QLE2PI009O) | accounts 2025-12 | 2026-10-26 | high |
| 17 | Zensimu ApS (independent CVR mirror) | [Firma API](https://firmaapi.dk/virksomhed/zensimu-aps-44668033) | 2026 | 2026-10-26 | high |
| 18 | Forio MIT Beer Game $168 | [Forio](https://forio.com/catalog/mit-beer-game-supply-chain-simulation) | 2026 | 2026-10-26 | high |
| 19 | Forio Root Beer: $168, computer player, solo | [Forio](https://forio.com/catalog/harvard-root-beer-game-supply-chain-simulation) | 2026 | 2026-10-26 | high |
| 20 | Forio site-wide starting price $165 → $168 | [Forio pricing](https://forio.com/pricing) | 2026-06 to 2026-10 | 2026-10-26 | high |
| 21 | MIT Sloan page links to Forio, no price | [MIT Sloan](https://mitsloan.mit.edu/teaching-resources-library/mit-sloan-beer-game-online) | 2022-01-05 | 2026-10-26 | high |
| 22 | eBeer server plays missing position, team mgmt | [Responsive](https://www.responsive.net/ebeer.html) | 2024-04-22 | 2026-10-26 | high |
| 23 | eBeer $20/$12/$10, flat 2021–2026 | [Responsive](https://responsive.net/pricingGames.html) | 2024-04-22 | 2026-10-26 | high |
| 24 | Forio Near Beer free funnel, fixed demand | [Forio](https://forio.com/resources/bullwhip-supply-chain-near-beer-simulation) | 2025-12-14 | 2026-10-26 | medium |
| 25 | Kearney app v2.0.3, last update 2020-10-02 | [iPhoneAddict](https://iphoneaddict.fr/apps/economie-entreprise/kearney-beer-distribution-game.html) | 2020-10-02 | 2026-10-26 | medium |
| 26 | MA-system consultant-led; ghost players disputed | [MA-system](https://www.masystem.se/MA-system-Consulting/Play-The-Beer-Game/Rules) | undated | 2026-10-26 | low |
| 27 | Fathomd async, human-only | [Fathomd](https://www.fathomd.com/bdg) | 2021 | 2026-10-26 | high |
| 28 | Eureka/IESE multiplayer, quote-only | [Eureka Simulations](https://www.eurekasimulations.com/en/beergame/login.php) | undated | 2026-10-26 | medium |
| 29 | Cohen simulator CC0, no bots, 1 star | [GitHub API](https://api.github.com/repos/jncohen/supply-chain-simulation) | pushed 2026-10-16 | 2026-10-26 | high |
| 30 | siemsene/beergame rule-based robo-players | [GitHub README](https://raw.githubusercontent.com/siemsene/beergame/main/README.md) | 2026-05-01 | 2026-10-26 | medium |
| 31 | isee systems $15 single-user | [isee systems](https://ssl.iseesystems.com/store/simulations/beer-game.aspx) | undated | 2026-10-26 | medium |
| 32 | HF Space, human + GPT-4o-mini, build error | [Hugging Face](https://huggingface.co/spaces/Lilli98/Beergamesimulation) | 2025-09-09 | 2026-10-26 | high |
| 33 | GenAI Beer Game: all LLM, no human seat | [Info Theory Lab](https://infotheorylab.github.io/beer-game/) | 2025-08-29 | 2026-10-26 | high |
| 34 | LLM agents: 80% best-config cost cut; default CV 26–52%, tuned about 12–13% | [arXiv 2605.17036](https://arxiv.org/abs/2605.17036) | 2026-09-21 (v4) | 2026-10-26 | high |
| 35 | SupplyNet: human + gpt-4o, n=14, $0.25–2.00 estimate | [arXiv 2606.24694](https://arxiv.org/abs/2606.24694) | 2026-06-23 | 2026-10-26 | medium |
| 36 | LLMs reproduce bias direction, not distributions | [arXiv 2510.03310](https://arxiv.org/abs/2510.03310) | 2025 | 2026-10-26 | medium |
| 37 | LLM agents myopic in multi-stage chains | [arXiv 2604.17220](https://arxiv.org/abs/2604.17220) | 2026-04-19 | 2026-10-26 | medium |
| 38 | SSRN paper cited by the brief: could not be found | [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5266281) | unknown | 2026-10-26 | low (unverified) |
| 39 | THE Campus article; Couscous Game, no repo | [Times Higher Education](https://www.timeshighereducation.com/campus/less-beer-more-couscous-gamifying-supply-chain-education) | 2026-06-07 | 2026-10-26 | high |
| 40 | "Up to 25%" absentees, one poster abstract | [Univ. of Calgary](https://prism.ucalgary.ca/handle/1880/110564) | 2019-04-30 | 2026-10-26 | medium |
| 41 | Sterman 1989: misperception of feedback | [Crossref](https://api.crossref.org/works/10.1287/mnsc.35.3.321) | 1989 | 2026-10-26 | high |
| 42 | Croson & Donohue 2006: info sharing helps only somewhat | [Crossref](https://api.crossref.org/works/10.1287/mnsc.1050.0436) | 2006 | 2026-10-26 | medium |
| 43 | Jeong & Hong 2011: learning across repeated plays (secondary summary) | [Inderscience](https://www.inderscienceonline.com/doi/abs/10.1504/IJIOME.2011.042668) | 2011 | 2026-10-26 | low |
| 44 | Panić 2020: two cohorts, n=42, information sharing | [Univ. of Belgrade repository](https://rfos.fon.bg.ac.rs/handle/123456789/2136) | 2020 | 2026-10-26 | low |
| 45 | Beer Game history: debrief needs work (abstract-level) | [System Dynamics Review](https://onlinelibrary.wiley.com/doi/pdfdirect/10.1002/sdr.1767) | 2024 | 2026-10-26 | medium |
| 46 | beergame.happily.ai human-only companion | [Happily](https://beergame.happily.ai) | undated | 2026-10-26 | medium |
| 47 | beergame.org free, last post 2019 | [beergame.org](https://beergame.org) | 2019-03-02 | 2026-10-26 | high |
| 48 | Zensimu reviewer: computer plays poorly (search snippet; page returned 403) | [GetApp](https://www.getapp.de/software/2061710/zensimu) | 2022-10-07 | 2026-10-26 | low |
| 49 | Zensimu's Harvard/Forio comparison page: $16/$48 claim (competitor content) | [Zensimu](https://zensimu.com/comparison/zensimu-vs-harvard-forio-beer-game-feature-price-comparison) | undated | 2026-10-26 | low |
| 50 | MBA Crystal Ball: about $150 per seat for Root Beer Game (search snippet) | [MBA Crystal Ball](https://www.mbacrystalball.com/management-games/) | undated | 2026-10-26 | low |
| 51 | En Dash home page: "Choose a role, AI handles the rest" | [En Dash](https://beergame.endash.us/) | undated | 2026-10-26 | high |
| 52 | Zensimu beer game page: auto debrief report, charts, PDF/Excel, slides; no AI mentioned | [Zensimu](https://zensimu.com/beer-game) | undated | 2026-10-26 | medium |

## Staleness map

Windows: pricing and features 3 months, trajectory 6, sentiment 12, papers 12. Computed with `recon_kit.py staleness`.

**Already past their window (treat as history until re-checked):**

| Claim | Last dated | Why it matters |
|---|---|---|
| eBeer $20/$12/$10 [23] | 2024-04-22 (unchanged in a 2026-03 snapshot) | Price anchor for institutions |
| Zensimu plan structure, no public prices [11][15] | 2026-06-11 | Current Zensimu prices unknown |
| Skill Dynamics "AI bots" [5] | 2025-10 (last dated asset) | Closest unseen competitor |
| Zensimu company facts [16] | FY2025 accounts | Funding or hiring could change the picture |
| Kearney app [25] | 2020-10-02 | Probably abandoned |
| Calgary "up to 25%" absentees [40] | 2019-04-30 | Only quantitative need figure |
| Zensimu reviewer on computer quality [48] | 2022-10-07 | Only fill-quality voice |

**Re-check dates for current claims:**

| Claim | Re-check by |
|---|---|
| En Dash features [2][3][4] | 2026-12-17 (earliest) |
| Forio price $168 [18][19]; Zensimu Computer and free solo [10][11]; Forio computer player [19] | 2027-01-26 |
| En Dash traction [1] | 2027-02-25 |
| transentis Metapad pivot [7] | 2027-04-26 |
| THE Campus article [39]; SupplyNet cost [35] | 2027-06 |
| LLM-agent findings [34] | 2027-09-21 |

The earliest upcoming re-check is **2026-12-17** (En Dash), which is the competitor most likely to change. A Refresh run starts from this table.
