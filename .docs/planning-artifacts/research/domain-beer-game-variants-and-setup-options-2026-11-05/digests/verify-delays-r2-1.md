# Verify: Beer Game delays in weeks (order info / shipping / factory production)

Accessed 2026-11-05 for all rows. Run was capped at about 12 calls and went over because several primary sources were blocked (see "Blocked or unreadable"). The Sterman 1989 full text and the Business Dynamics chapter were NOT retrieved, so no claim below is anchored in Sterman's own text.

## Findings

| # | Claim (exact wording where quoted) | Source URL | Publisher / date | Confidence | Status |
|---|---|---|---|---|---|
| 1 | MIT/SD Society protocol names the three delays but gives NO week counts: "Beer is received after a shipping delay. (In the case of the factory, beer is received after a production delay.) Orders are received after a mailing delay (orders placed to incoming orders)." Init: "four chips in each shipping box and production delay". | https://systemdynamics.org/wp-content/uploads/2020/12/BEER-GAME-INSTRUCTIONS.pdf | System Dynamics Society, hosting upload 2020-12 (MIT SD Group "Instructions for Running the Production-Distribution Game", original date not shown) | high (text) / n.a. for weeks | fetched (PDF, text extracted with pdftotext) |
| 2 | Same MIT instructions, as mirrored by SUNY New Paltz: same wording, no week counts. | https://www2.newpaltz.edu/~liush/OM/beer%20game.htm | SUNY New Paltz course page, date not shown | high | fetched |
| 3 | Kaminsky & Simchi-Levi 1998: "Order processing and filling delays are incorporated into the game to represent order processing, transportation, and manufacturing lead times." Short lead time option "allows play with a one week delivery delay between stages, rather than the two weeks originally employed." Centralized option: "three sets of orders are eliminated, product moves through this supply chain three weeks faster than in the original game." (Implies order delay is not zero and that the original shipping delay is 2 weeks; three order stages x 1 week = 3 weeks is consistent with a 1-week order delay but the paper does not say so explicitly.) | https://kaminsky.ieor.berkeley.edu/Reprints/PK_DSL_98b.pdf | Kaminsky and Simchi-Levi, Northwestern/Berkeley reprint, 1998 | high for quoted text; medium for the inference | fetched (pdftotext) |
| 4 | Wikipedia: "a two-week communication gap of orders toward the upstream"; "a two-week supply chain delay of product towards the downstream"; "the manufacturer places an order which, in turn, becomes product in four weeks". | https://en.wikipedia.org/wiki/Beer_distribution_game | Wikipedia, no stable date | medium (tertiary; WebFetch summarised the page, quotes are from the tool's answer) | fetched |
| 5 | beergame.org: "Each delivery (and production order) requires two rounds until they are finally delivered to the next stage." No separate order delay stated. | https://beergame.org/the-game/structure-rules/ | beergame.org, date not shown | medium (a modern web version, not the original board) | fetched |
| 6 | Bosch Pagans, Strozzi, Zaldivar (Liuc Papers 179): per rules attributed to Jarmain 1963, "the time delay from passing of orders and shipments from one stage to the next is fixed to one week"; "the production time is taken to be three weeks". Model equations cite Thomsen et al. 1992. This is a simplified simulation model, not the physical board. | https://biblio.liuc.it/liucpap/pdf/179.pdf | Liuc Papers n. 179, Oct 2005 | high that the paper says this; low that it describes Sterman's board | fetched (pdftotext) |
| 7 | MIT SD / Paine arXiv 2202.12786: starting layout "12 units of inventory on hand for each player, and 4 units of inventory in transit at each stage in the shipping system, and 4 orders moving through the order chain" (cites Croson and Donohue 2006, Narayanan and Moritz 2015, Sterman 1989a). No week counts given in the text read. | https://arxiv.org/pdf/2202.12786 | arXiv, 2022 | high for quote; no delay value | fetched (pdftotext) |
| 8 | Albany archive paper (computerized beer game; author/title not identified because the page fetch returned only a login/navigation shell): "between each level of the supply chain there are two periods of shipping delays and two periods of order receiving delays"; factory "delay between placement of production orders and receipt of products is three periods"; "in the board game, this delay is four periods". | https://archives.albany.edu/downloads/0p096q973?locale=de | University at Albany Special Collections, date unknown | low-medium (identity unknown) | snippet-only (WebSearch summaries, repeated in 4 searches; direct fetch failed) |
| 9 | CMU DDMLab (Martin, Gonzalez, Lebiere 2004): order-passing delay one week; "additional two week transportation delay" after the supplier fills the order. | https://www.cmu.edu/dietrich/sds/ddmlab/papers/MartinGonzalezLebiere2004.pdf | CMU, 2004 | low-medium | snippet-only (direct fetch 404) |
| 10 | MobLab quickstart manual: "Orders take one week to travel upstream between each node in the supply chain. Deliveries flow ... at the speed of the Shipping Delay. In our default parameters this Shipping Delay is two weeks." | https://s3-us-west-2.amazonaws.com/moblab-manuals/quickstart/beer_game.html | MobLab, date unknown | medium | snippet-only |
| 11 | Course handout (host not identified): version with "shipping delay (or production delay): 3 weeks" and "no mailing delay"; also a team option "Shipping Delay reduced to 1 week from 2". | not identified in search output (candidates: https://eclass.aueb.gr/modules/document/file.php/MISC446/Session%20Beer%20Game.pdf, which returned only a login page) | unknown | low | snippet-only |
| 12 | Sterman 1989 (Management Science 35(3):321-339) and MIT SWP-1933 working-paper full text: located (https://dspace.mit.edu/bitstream/handle/1721.1/2184/SWP-1933-18213539.pdf) but fetch returned HTTP 429 (twice), and curl returned an HTML stub. Not read. | https://dspace.mit.edu/bitstream/handle/1721.1/2184/SWP-1933-18213539.pdf | MIT DSpace, 1988/1989 | n.a. | not retrieved |

## Table: delay -> values seen -> sources

| Delay | Values seen | Sources |
|---|---|---|
| (a) Order-information delay | 1 week | #6 (Liuc, Jarmain-style rules), #9 (CMU, snippet), #10 (MobLab default, snippet); implied by #3 (not explicit) |
| | 2 weeks | #4 (Wikipedia), #8 (Albany, snippet) |
| | none ("no mailing delay") | #11 (a variant, snippet) |
| | name only, no number | #1, #2 (MIT instructions: "mailing delay") |
| (b) Shipping delay | 2 weeks | #3 ("two weeks originally employed"), #4, #5, #8, #9, #10 |
| | 1 week | #6 (simplified model), #3 and #11 (short-lead-time option) |
| | 3 weeks | #11 (variant, snippet) |
| (c) Factory production delay | 3 weeks | #6 (Liuc), #8 (Albany: computerized version) |
| | 4 weeks | #4 (Wikipedia), #8 (Albany: "board game") |
| | 2 weeks | #5 (beergame.org, "production order" same as delivery) |
| | name only | #1, #2 |

## Verdicts

- (a) Order-information delay: **disputed**. 1 week (Liuc/Jarmain, CMU, MobLab) versus 2 weeks (Wikipedia, Albany). No retrieved primary source (Sterman 1989, MIT instructions) states a number. The MIT instructions mention a "mailing delay" without a duration.
- (b) Shipping delay: **verified at 2 weeks for the standard/original configuration** as used by Kaminsky & Simchi-Levi 1998 (fetched primary) and corroborated independently by Wikipedia, beergame.org, MobLab and CMU; other values (1 week, 3 weeks) are documented variants or simplified models. Not verified against Sterman 1989 text itself.
- (c) Factory production delay: **disputed**. 3 weeks (Liuc; Albany computerized) versus 4 weeks (Wikipedia; Albany's "board game") versus 2 weeks (beergame.org). Likely reading: "1 week order delay + 3 weeks production = 4 weeks order-to-inventory" explains 3 vs 4, but no fetched source says this explicitly; treat as hypothesis.
- "2 + 2" vs "1 + 2" total supply-line delay: **unverified for the original board and Sterman 1989**. Evidence is split between "2 + 2" (Wikipedia, Albany snippet) and "1 + 2" (CMU, MobLab, Liuc/Jarmain). Resolve by reading Sterman 1989 (SWP-1933 / Management Science) or Business Dynamics ch. 17 directly.

## Blocked or unreadable (for follow-up)

- MIT DSpace SWP-1933 (Sterman 1989): HTTP 429 with Retry-After 900 s; retry after about 15 minutes.
- Sterman "Teaching Takes Off" (https://web.mit.edu/jsterman/www/SDG/beergame.html): only seen in search snippets, no week counts.
- Albany papers, AUEB eClass, MDPI Systems 8(4):37 and core.ac.uk PDFs: login page or HTTP 403.
- Not reached: Business Dynamics ch. 17, Chen and Samroengraja, Croson and Donohue methods sections, Lee/Padmanabhan/Whang, Simchi-Levi textbook.
