# bots-r2-g: how incumbents' bot/AI players work (accessed 2026-10-26)

## Skill Dynamics
- Single-player Beer Game, player is Distributor; other three roles "played by AI bots"; four tiers (retailer, wholesaler, distributor, manufacturer) | https://skilldynamics.com/supply-chain-beer-game/ (same text at ?p=1921) | Skill Dynamics | undated (footer (c)2026; testimonial image uploaded Oct 2025) | accessed 2026-10-26 | confidence high (page text), marketing register | feature
- Session lasts "an hour at most", simulates up to a year of supply chain | https://skilldynamics.com/?p=1921 | Skill Dynamics | undated | accessed 2026-10-26 | med | feature
- Bot logic NOT disclosed: page does not say rule-based/ML/LLM; no difficulty options, replay, demand pattern (only "fluctuating customer demand"), or debrief/analytics mentioned | https://skilldynamics.com/supply-chain-beer-game/ | Skill Dynamics | undated | accessed 2026-10-26 | med (absence on page) | feature
- Access: described as "free online" but gated by a form (first/last name, business email, company, number of learners, area of interest) = lead-generation funnel for corporate training | https://skilldynamics.com/supply-chain-beer-game/ | Skill Dynamics | undated | accessed 2026-10-26 | high | pricing
- Company: "Corporate training for companies", academies in supply chain, procurement, trade compliance; site built by Persona Studio; Merck testimonial; founders not named | https://skilldynamics.com/?p=1921 | Skill Dynamics | undated | accessed 2026-10-26 | med | positioning
- Last update unknown (no date on page; only (c)2026 footer) | same | | undated | accessed 2026-10-26 | low | trajectory

## MA-system Consulting (Lund, Sweden)
- Beer Game is a consultant-facilitated product: half-day session, game itself 1-2 h; booking via contact form; also playable online via link (beergame.masystem.se) | https://www.masystem.se/Ma-system-consulting/Spela-Beer-Game | MA-system | undated | accessed 2026-10-26 | med | positioning
- Facilitators give improvement suggestions for the customer's operation; no formal debrief format described. Customer cases: Fagerhult, ScanSpac | https://www.masystem.se (and Spela-Beer-Game page) | MA-system | undated | accessed 2026-10-26 | med | feature
- No pricing on site; contact only (info@masystem.se, +46 46-32 90 00). The reported "free for universities / $20 per player" was NOT verified | https://www.masystem.se/Ma-system-consulting/Spela-Beer-Game | MA-system | undated | accessed 2026-10-26 | med (absence) | pricing
- No mention of ghost/virtual players, solo vs multi, or last-update date on fetched pages; beergame.masystem.se returned only the title "MA-system Beer Game" (likely JS app, content not extractable) | https://beergame.masystem.se | MA-system | undated | accessed 2026-10-26 | low | feature

## transentis
- Playable game beergame.transentis.com: modes Single Player, Multiplayer, Multigame; "free - no account required" for creating a game; "All Rights Reserved" footer, no licence for the game stated | https://beergame.transentis.com | transentis | undated | accessed 2026-10-26 | high | pricing
- Single player always = Retailer role (rules page) | https://beergame.transentis.com/docs/rules | transentis | undated | accessed 2026-10-26 | high | feature
- Game admin can "assign roles to AI players"; FAQ: "you can assign artificial players (AI players), so you can play with 1-4 players" and "Play the multiplayer version against 3 artificial players" | https://beergame.transentis.com/docs/faq | transentis | undated | accessed 2026-10-26 | high | feature
- Difficulty: FAQ answers "single player is too easy" by suggesting multiplayer vs 3 AI players or "Multigame with just 1 player and choose an advanced preset" - difficulty is via presets, not documented bot tiers | https://beergame.transentis.com/docs/faq | transentis | undated | accessed 2026-10-26 | med | feature
- The docs do NOT say how the in-game AI players decide (policy vs trained agent). The link between the web game's AI players and the Q-learning agents is NOT established by any fetched source | https://beergame.transentis.com/docs/rules and /docs/faq | transentis | undated | accessed 2026-10-26 | med (absence) | feature
- "Playing Against Trained Agents" (beergame_ql.html) is a marimo notebook that trains Q-learning agents 10 episodes, loads stored Q-tables (q_tables_50000.json), runs the `smart_agents` scenario and plots results; it does NOT describe a human-playable interface or difficulty levels. Stated purpose: "Play the Beer Distribution Game against agents trained by reinforcement learning, using a stored Q-table" | https://bptk.transentis.com/model_library/beergame/beergame_ql.html | transentis (BPTK) | undated | accessed 2026-10-26 | med (only first 100k of ~980k chars read) | oss
- Training page: tabular Q-learning (class BeergameQlOB), four per-role Q-tables (brewery, distributor, wholesaler, retailer), reward = supply-chain reward, fixed consumer demand, compared against an "Order Balance" policy; results at 10, 37,500 and 50,000 episodes | https://bptk.transentis.com/model_library/beergame/training_ai_beergame.html | transentis (BPTK) | undated | accessed 2026-10-26 | med | oss
- GitHub: transentis/beergame last pushed 2023-03-01, no licence listed, description "train autonomous agents ... reinforcement learning"; contents moved to transentis/bptk_py_tutorial | https://api.github.com/repos/transentis/beergame | GitHub API | 2023-03-01 | accessed 2026-10-26 | high | oss
- transentis/bptk_py_tutorial last pushed 2026-08-28; commit "remove contents" (2026-08-28) is the latest touching model_library/beergame, and the directory listing via API returned empty -> beergame notebooks appear removed from the tutorial repo on GitHub (the website still serves them). Tutorial repo licence: null | https://api.github.com/repos/transentis/bptk_py_tutorial | GitHub API | 2026-08-28 | accessed 2026-10-26 | med | trajectory
- transentis/bptk_py (engine) pushed 2026-10-26, MIT licence; other repos mostly MIT. The web game's own source repo was not found among the org's public repos | https://api.github.com/orgs/transentis/repos | GitHub API | 2026-10-26 | accessed 2026-10-26 | high | oss
- Earlier 404/dead: beergame.transentis.com/docs/guides (404 via search result), www.beergame.transentis.com (no DNS), bptk.transentis.com:8080 (connection refused) | various | | | accessed 2026-10-26 | high | trajectory

## Other vendors with computer players
- Lokad online Beer Game: no sign-up; a commenter notes the computer plays the other 3 roles if you lack friends (snippet only, not fetched) | https://news.lokad.com/posts/106 | Lokad | undated | accessed 2026-10-26 | low | feature
- Zensimu: if the timer expires, the computer plays automatically for players who have not ordered (facilitator tool, snippet only) | https://docs.zensimu.com/article/21-prepare-beer-game-session | Zensimu | undated | accessed 2026-10-26 | low | feature
- Academic precedents: Kaminsky & Simchi-Levi computerized beer game (1998) already provided simulated "participants" so users could pick a role and play alone | https://kaminsky.ieor.berkeley.edu/Reprints/PK_DSL_98b.pdf | Berkeley IEOR | 1998 | accessed 2026-10-26 | low (snippet) | feature
- Research on AI agents playing the beer game exists (arXiv 2605.17036, 2026 preprint; happily.ai write-up claims AI agents cost ~2.6x matched human teams, secondary, unverified) | https://arxiv.org/pdf/2605.17036 | arXiv | 2026 | accessed 2026-10-26 | low (snippet) | sentiment

## Takeaway for the decision
- "AI bots to fill empty roles" is already present in at least Skill Dynamics (marketing claim, free-with-form), transentis (AI players documented in FAQ, up to 3), and probably Lokad. None of the three discloses bot logic, none documents LLM-based players, none documents difficulty tiers for bots or solo replay analytics. Commoditized as a feature (filler bots); not commoditized as a differentiated, explained, replayable AI-opponent experience. Evidence is thin (marketing pages, undated).

## Leads worth chasing
- Actually play beergame.transentis.com in a browser (single player, AI players, "advanced preset") to observe bot behaviour; JS app not readable via fetch.
- Play Skill Dynamics via the form to observe bot behaviour, replay, debrief.
- beergame.masystem.se is a JS app; needs browser testing for ghost players and pricing; ask MA-system by email for price.
- Read beergame_ql.html beyond the first 100k chars (offset 100000) and transentis blog "training-artificial-intelligence-to-play-the-beer-game" to see if the web game uses the trained Q-tables.
- Lokad beer game page (lokad.com / news.lokad.com/posts/106) and Zensimu docs fetched directly.
- Check whether the removal of beergame notebooks from bptk_py_tutorial is a deprecation signal (see commit 37f4221 "remove contents").

## Looked for but not found
- Any description of Skill Dynamics bot algorithm, difficulty, replay, demand pattern, debrief, page modified date: nothing.
- MA-system pricing ("free for universities / $20 per player"), ghost players, solo/multi modes, last update: nothing on fetched pages.
- transentis docs page stating what drives the web game's AI players; beergame.transentis.com/docs/guides (404); any licence for the web game: nothing.
- Source repo for the beergame.transentis.com web app on GitHub: not found among transentis org repos.
- Any LLM-based playable bot in an incumbent product: nothing found.
