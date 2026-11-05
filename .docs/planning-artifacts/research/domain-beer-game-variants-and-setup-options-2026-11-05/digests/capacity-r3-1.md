# Capacity dimension, digest capacity-r3-1

Run date and access date: 2026-11-05. Decision served: how a web-based Beer Game should let a lecturer enable capacity limits as a class setting.
Format per finding: claim | source URL | publisher | publication date | accessed | confidence | fetched or snippet-only.

## Q1. Variants/platforms with capacity limits and how they are defined

1. Zensimu Beer Game has a "Capacity (maximum shipment)" parameter. It caps the number of units a role can ship to its client in a given week, even when the player has enough stock (changelog example: capacity 6 limits shipments despite sufficient stock). Because of the cap a player can hold stock and backorders at the same time. It can be set on one or several roles, and scheduled events can change it mid-game. The changelog gives no default value and says nothing about excess orders beyond the implied backorder.
   - https://feedback.zensimu.com/changelog/beer-game-capacity-maximum-shipment | Zensimu | 2024-06-03 | accessed 2026-11-05 | high | fetched
   - Note: changelog says the "Electric Vehicle Supply Chain" template includes the parameter (fetched).

2. Zensimu Advanced Beer Game Model: capacity constraint is a per-SKU product-data field per role ("stock, stock/backorder costs, sale price, capacity constraint"); MOQ and batch size are separate "capability" fields. A "capacity constraint (maximum shipment quantity)" can be a scheduled disruption event, and parameter changes can be absolute or relative to the current value. The article does not say what happens to orders exceeding capacity. It says that when overall demand exceeds stock+receipts, the player must allocate limited quantities before the game can advance to the next week. It does not list allocation rules (proportional, FCFS and so on).
   - https://docs.zensimu.com/article/47-introduction-to-the-advanced-beer-game-model | Zensimu | last updated 2026-04-01 | accessed 2026-11-05 | high (for what it states) | fetched

3. Zensimu scenario page: "Adjust batch size, MOQs and capacity to simulate process constraints"; events can "increase/decrease lead times, costs, capacity". No definition or values. Capacity types (production vs shipping) not distinguished.
   - https://zensimu.com/beer-game/scenario | Zensimu | undated | accessed 2026-11-05 | medium | fetched

4. The standard game has no capacity limit. Course materials describe production, shipping and warehouse capacity as infinite (from search snippet). beergame.org Structure & Rules mentions no capacity or rationing, only a 2-round delay and carried-forward backlog (EUR 0.50 stock, EUR 1.00 backlog per item per week). The Wikipedia article on the beer distribution game describes four variants (board, table, adapted table, software), none with capacity limits.
   - https://beergame.org/the-game/structure-rules/ | beergame.org | undated | 2026-11-05 | high | fetched
   - https://en.wikipedia.org/wiki/Beer_distribution_game | Wikipedia | undated | 2026-11-05 | medium | fetched
   - Infinite-capacity statement: search snippet only (eclass.aueb.gr "Session Beer Game.pdf", behind login, unreadable) | low | snippet-only

5. Academic: Spiegler and Naim, "The impact of freight transport capacity limitations on supply chain dynamics", Int. J. Logistics Research and Applications 17(1):64-88, DOI 10.1080/13675567.2013.838012. A system dynamics replication of the Beer Game under different transport-capacity scenarios found that capacity limits raise inventory and backlog costs and that backlog and inventory can coexist (not possible in the uncapacitated game). It reports a "positive impact on the backlash effect" (mechanism not given in the abstract). Vertical collaboration in transport provision can overcome the trade-off. Full PDF returned 403, so the cap values and excess-order rule are unknown.
   - https://bura.brunel.ac.uk/handle/2438/11422 | Brunel University / Taylor & Francis | 2014 | 2026-11-05 | high | fetched (abstract level only)

6. Lee, Padmanabhan, Whang (1997), Management Science 43(4):546-558, "Information Distortion in a Supply Chain: The Bullwhip Effect". Section 3.2 "The Rationing Game" is framed as demand potentially exceeding supply "due to limitation in production capacity or uncertainty of production yield". When total orders exceed output, the manufacturer "allocates to retailers in proportion to their orders". Theorem 2: the retailer's optimal order in the rationing game exceeds the plain newsvendor order, which implies bullwhip. The game is "triggered only at an upswing of demand" and amplifies bullwhip beyond demand-signal processing alone. The paper also says the beer game bullwhip may be driven by rational decision making, contrasting Sterman's (1989) "misperceptions of feedback".
   - https://courses.ie.bilkent.edu.tr/ie102/wp-content/uploads/sites/12/2019/02/Lee-Padmanabhan-Whang-1997-MS.pdf (PDF text extracted locally) | INFORMS / Management Science (copy hosted by Bilkent course site) | 1997-04 | 2026-11-05 | high | fetched

## Q2. Typical capacity parameter values

7. The only concrete value found is Zensimu's own changelog illustration of a capacity of 6 limiting shipments. This is an example, not a recommended default. Customer demand in the standard game is 4 per week (per the Sterman/Dogan source below), so 6 is 1.5x steady demand. This is an inference from two sources, flagged as such.
   - https://feedback.zensimu.com/changelog/beer-game-capacity-maximum-shipment | Zensimu | 2024-06-03 | 2026-11-05 | medium | fetched
   - https://mitmgmtfaculty.mit.edu/jsterman/imnothoarding/ | MIT Sloan | 2015 | 2026-11-05 | high for the constant 4/week demand in that experiment (snippet: "constant customer orders of 4 cases per week", from a 2005 SD Society abstract) | snippet-only for the 4/week figure

## Q3. Effects of capacity and rationing on bullwhip, cost, behaviour

8. Capacity limits (transport) raise inventory and backlog costs in the beer game simulation (finding 5). This is simulation evidence, not human subjects.
9. Rationing and shortage gaming is one of four bullwhip causes in Lee et al. (finding 6). The Stanford GSB summary gives the same four factors (demand forecast updating, order batching, price fluctuation, rationing and shortage gaming). The HP LaserJet example (resellers cancelled orders when constraints lifted) came from a secondary source, Fibre2Fashion, which I did not read, so treat it as low confidence.
   - https://www.gsb.stanford.edu/insights/whang-lee-eliminating-bullwhip-effect-supply-chains | Stanford GSB | 1995-03-01 | 2026-11-05 | medium | snippet-only
10. Sterman and Dogan (2015), "I'm not hoarding, I'm just stocking up before the hoarders get here", J. Operations Management 39-40:6-22, DOI 10.1016/j.jom.2015.07.002. This is a human-subject beer game with no horizontal competition, randomness or capacity constraint, and constant known demand. About 20% of participants still show significant hoarding and phantom ordering when deliveries falter, which triggers a demand bubble and lowers their payoff. A search summary mentions 22% ordering more than 25x known demand, but this figure was not confirmed on the fetched page; treat it as unverified. Implication for the product: human phantom ordering occurs even without capacity limits, so capacity plus rationing would likely worsen it. That implication is mine, not stated in the sources.
    - https://mitmgmtfaculty.mit.edu/jsterman/imnothoarding/ | MIT Sloan (Sterman) | 2015 | 2026-11-05 | high | fetched
11. Whether capacity makes the game harder or is used in advanced courses: no direct source found. Zensimu places capacity in an "Advanced Model" (finding 2), which suggests advanced use. This is an inference from product structure only. Low confidence.

## Q4. Allocation rules when supply is short

12. Rules named in the literature:
    - Proportional to orders: the rule assumed in Lee et al. (1997), which makes inflating orders pay off.
    - Based on past sales or usage: Lee et al. recommend allocating "in proportion to the retailer's market share in the previous period" to remove the payoff from gaming. General Motors, Texas Instruments and HP are cited as using historic-sales allocation. The paper's summary table also lists "Proportional rationing scheme" and "Allocate based on past sales".
    - Uniform (equal split, capped at the order): Cachon and Lariviere, "An equilibrium analysis of linear, proportional and uniform allocation of scarce capacity", IIE Transactions 1999, pp. 835-849. Under proportional or linear allocation a retailer gets less than ordered whenever capacity binds, so retailers over-order and equilibria may not exist. Under uniform allocation a unique Nash equilibrium exists in which retailers order exactly their desired amounts. Theory, not a game experiment. The abstract does not give formulas.
    - Sources: Lee et al. PDF (above) high, fetched. Cachon and Lariviere: https://www.kellogg.northwestern.edu/faculty/research/detail/1999/an-equilibrium-analysis-of-linear-proportional-and-uniform-allocation | Kellogg School of Management, Northwestern | 1999 | 2026-11-05 | high | fetched (abstract page)
13. First come first served is not evidenced in any source read. Zensimu says only that the player allocates manually when demand exceeds stock; it names no automatic rule.
14. Lee et al. also propose supply-side contracts that restrict buyer flexibility, e.g. forecasts sent 18 weeks ahead with limited revisions (up to 30%), and information sharing to limit gaming. Fetched, high.

## Looked for and could not find

- A documented excess-order rule (backlog, lost or rationed) for capacity in Zensimu. The changelog and the advanced-model article are silent. Backorder is implied by "stock and backorders at the same time".
- Capacity values used in the Spiegler and Naim study (PDF 403; abstract only).
- Any open-source implementation with a shipping or production cap. A GitHub search via the search engine found only caprion/beer-game (no capacity evidence in the snippet; not inspected). Other GitHub and Hugging Face repos were not inspected.
- Capacity features in Forio, Harvard, Darden, transentis and MobLab beer games. No dedicated search was made and no evidence retrieved (budget). Not evidence of absence.
- Sterman, Business Dynamics, chapter on capacity: not retrieved.
- Human-subject experiments directly crossing capacity limits with allocation rules in the beer game (the search engine reported none). The nearest human-subject evidence is Sterman and Dogan (no capacity) and Cachon-Lariviere style theory.
- Any teaching source stating capacity as a multiple of the 4/week demand (6 or 8) beyond the Zensimu example of 6.
- Evidence on difficulty or advanced-course use of capacity limits.
- University of South Carolina dissertation on allocation policies in a supply chain simulation game: only the abstract surfaced through search (https://scholarcommons.sc.edu/etd/4223), not fetched. It is low confidence and snippet-only.
- Other search hits not read: Hussain, Khan and Sabir (2016, IJLRA) on capacity and the backlog bullwhip in a two-tier chain (snippet-only); Springer 2010 paper on a reverse bullwhip under supply disruptions in the beer game (https://link.springer.com/article/10.1007/s10696-009-9054-3, snippet-only). Both are low confidence leads.
