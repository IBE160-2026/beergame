# Digest: teaching notes / educator literature (round 1, angle b)

Run date / accessed: 2026-10-26. Agent: repro-voice-r1 (teaching-notes angle).
Questions owned: Q1 prescribed demand pattern + why + anticipation; Q2 grading/comparing teams, fairness across teams/sections; Q3 randomisation, seeds, deliberate replay; Q4 product instructor features (same-for-all demand, presets, comparison).
Searches run (6): "beer game instructor guide demand step 4 to 8"; "beer game teaching notes grading teams cost"; "beer game facilitator customer demand setting same for all teams"; "beer game random demand students memorize pattern replay"; "beer game assignment syllabus team grade total cost" (plus the fetches below).
Sources actually read in full text (7): Zensimu guide, Zensimu docs article, Forio store page, SD Society instructions PDF, Jackson & Taylor 1998 (ABSEL), Kaminsky & Simchi-Levi 1998, UW Foster OPMGT 560 WIN21 syllabus.
Not read (search-result snippets only, treat as leads): MIT CTL Rice debrief PDF (404 on fetch), Calgary/DSI "large classes" paper, Wisconsin Cao poster, Temple MIS3537 slides, INFORMS ITE 10.1287/ited.2017.0174 (403), iSixSigma guide, Inderscience online beer game study.
Note: WebFetch summarised via small model; PDFs were extracted locally with pdftotext and quotes below are from that raw text unless marked "(fetch summary)".

## Findings

Format: claim | URL | publisher | pub_date | accessed | confidence | class

### Q1 Prescribed demand pattern

1. Official MIT-derived protocol prescribes a FIXED step: "The pattern of customer demand that is most effective for first-time players is a pattern of four cases per week until week five, and then eight per week from week five on." Deck is prepared in advance (50 weeks of cards) and "should not be revealed in advance." | https://systemdynamics.org/wp-content/uploads/2020/12/BEER-GAME-INSTRUCTIONS.pdf | System Dynamics Society (adapted from J. Sterman / MIT SDG instructions) | 2017-05 (revised; original Sterman text older) | 2026-10-26 | high (primary, seminal guidance) | guidance

2. Rationale given for telling players 50 weeks: "telling the players it will be fifty weeks prevents horizon effects, where they run their inventories down because they feel the end of the game is coming." Game is typically stopped around week 35. (Rationale is about end-game behaviour, not about demand memorisation.) | same URL | System Dynamics Society | 2017-05 | 2026-10-26 | high | guidance

3. Protocol assumes players are naive: "The only prerequisite ... is that none of the participants have played the game before, or else agree not to reveal the 'trick' of the game." The pedagogical point depends on non-retailers not knowing the demand pattern (debrief: "All of you who were not retailers ... what do you think the customers were doing?"; "Most people usually believe that customer demand was fluctuating because they believe that the system fluctuations must have been externally driven."). Implication: a known/repeated pattern destroys the debrief moment; this is the closest the guides come to discussing anticipation. Inference marked as ours. | same URL | System Dynamics Society | 2017-05 | 2026-10-26 | high for quotes, medium for the implication | guidance / jtbd

4. Academic description of the classic game: "Consumer demand is a constant four cases of beer per week ... In period five consumer demand at the retail level is doubled to eight cases and maintained at this level for the remainder of the game." Also "The quantity of consumer demand is determined by the administrator." | https://absel-ojs-ttu.tdl.org/absel/article/view/1049/1018 | Developments in Business Simulation and Experiential Learning vol 25 (ABSEL conference proceedings; not a journal, peer-review level unclear), Jackson & Taylor | 1998 | 2026-10-26 | high for description; OLD, seminal | guidance

5. Same paper: "every team is playing in the same time period and not jumping ahead" (about pacing and synchronisation, not demand sameness). Also says the "winner" is lowest total cost and the first four stable periods are critical for a smooth session. | same URL | ABSEL / Jackson & Taylor | 1998 | 2026-10-26 | high | guidance

6. Computerised variant allows either: "demand in the computerized game can be either deterministic or random, and may have a step change in mean demand at any time chosen by the instructor." So the computerised academic version already treats deterministic vs random as an instructor choice. | https://kaminsky.ieor.berkeley.edu/Reprints/PK_DSL_98b.pdf | Kaminsky & Simchi-Levi, in Supply Chain and Technology Management (POMS, Miami); hosted at UC Berkeley | 1998 | 2026-10-26 | high (primary); OLD | feature / guidance

7. Same paper uses fairness language for CONDITIONS comparison: raising retailer backorder cost to $4.00 "enables a fair comparison between centralized and decentralized policies". Shows authors care about like-for-like comparison across runs when comparing variants. | same URL | Kaminsky & Simchi-Levi | 1998 | 2026-10-26 | high | guidance

8. Zensimu guide: students "adjust ordering behavior"; default start "each role starts the game with a stock of 12 units and incoming orders of 4 units for the next 2 weeks"; instructor announces a promotion to trigger demand increase ("announce that a big promotion has started leading to a demand increase"). Also "more variability and a more erratic demand typically generate even more perturbations in the upstream chain." The page has a "Setup end consumer demand" screen but text does not state fixed vs random default or same-for-all. (fetch summary) | https://zensimu.com/resources/complete-instructor-guide/ | Zensimu (vendor) | undated | 2026-10-26 | medium (vendor, marketing register, undated) | guidance / feature

### Q2 Grading / comparing teams, fairness

9. Standard protocol compares teams on cost: "Calculate team costs to determine the winner, and compute the average team cost" (done during the break), and players "ante up $1.00 ... winner takes all." Comparison is used for the debrief and the competitive frame, not for grades. | https://systemdynamics.org/wp-content/uploads/2020/12/BEER-GAME-INSTRUCTIONS.pdf | System Dynamics Society | 2017-05 | 2026-10-26 | high | guidance

10. Official debrief frames cross-team DIFFERENCES as the point: "different people in the same structure produce qualitatively similar results ... Differences in individual ordering patterns (free will) result in the quantitative differences in game results. But the qualitative patterns are the same." This presupposes teams face the same structure (and, by the fixed deck, same demand). Same-demand is implicit, not stated as a fairness rule. | same URL | System Dynamics Society | 2017-05 | 2026-10-26 | high for quote, medium for the implication | guidance / jtbd

11. Syllabus example: UW Foster OPMGT 560 (Winter 2021) uses a web-based "Supply Chain Simulation Game" that "builds upon the Beer Game"; two simulation reports "submitted for teams and graded on a ten-point scale"; the two reports are 20% of the grade; peer ratings adjust individuals. Grading is on the REPORT (analysis), not on raw simulation score; syllabus says nothing about identical scenarios or fairness. | https://foster.uw.edu/wp-content/uploads/2021/08/OPMGT-560-WIN21.pdf | University of Washington Foster School of Business (course syllabus) | 2021-08 (older than 18 months; flag) | 2026-10-26 | high for what it says; one syllabus only, no prevalence | guidance / language

12. Zensimu docs: debrief pages let players "compare their result with the one of the other teams"; instructor results page shows data and graphs such as the bullwhip effect; follow-up page shows each team's progress by round. No ranking/score or grading mentioned. (fetch summary) | https://docs.zensimu.com/article/21-organize-beer-game-session | Zensimu (vendor help page, "last updated January 31, 2026") | 2026-01-31 | 2026-10-26 | medium (vendor) | feature

### Q3 Randomisation, seeds, replay

13. No seed or "reproducibility" language found in any read source. Closest: the manual game's physical deck of cards is itself a fixed sequence that is identical for each team by construction (card deck "in order" weeks 1-50), i.e. determinism comes from the artefact, not from a stated principle. Inference, ours. | SDS PDF above | System Dynamics Society | 2017-05 | 2026-10-26 | low (absence + inference) | language

14. Deliberate second round exists in vendor sample plan, but it varies INFORMATION not demand: "Play a second round, with another setup: allow communication between players ('Transparent mode')." Default template: 2 rounds, with/without visibility, 20 weeks, ~1h30-2h; short template 2x12 weeks. (fetch summaries) | https://zensimu.com/resources/complete-instructor-guide/ and https://docs.zensimu.com/article/21-organize-beer-game-session | Zensimu (vendor) | undated / 2026-01-31 | 2026-10-26 | medium (vendor) | feature / guidance

15. Memorisation statement is vendor marketing only: "better memorization for learners" (about retention of lessons, not demand sequence). | https://zensimu.com/resources/complete-instructor-guide/ | Zensimu | undated | 2026-10-26 | low | language

### Q4 Product instructor features

16. Forio/HBP MIT Beer Game store page lists a "Facilitation Guide along with 1:1 facilitator training", session "Intro 15 minutes, Gameplay 1-1.5 hours, Debrief 30-60 minutes", and the rule "No one can see end-customer demand except the retailer." Public page says NOTHING about demand settings, same-for-all, or comparison dashboards; guide is locked. (fetch summary; page copyright 2001-2026, screenshots Dec 2025) | https://forio.com/store/mit-beer-game-supply-chain-simulation | Forio Corporation (vendor, marketing) | undated | 2026-10-26 | medium; gap, not evidence of absence | feature

17. Zensimu lets instructors edit "final consumer demand" per round in session Settings, create own session templates ("Our platform allows you to create your own session templates"), and "Create a Scenario" (e.g. pharma setting). Public text does not say whether demand is constant/step/random or identical across teams. (fetch summary) | https://docs.zensimu.com/article/21-organize-beer-game-session | Zensimu | 2026-01-31 | 2026-10-26 | medium (vendor) | feature

18. Instructor-chosen computer players: Zensimu "the computer will play where a participant is missing" with settings for ordering behaviour (variability, stock target) -> relevant to AI-agent determinism: the vendor exposes the agent policy as a configurable parameter. (fetch summary) | https://zensimu.com/resources/complete-instructor-guide/ | Zensimu | undated | 2026-10-26 | medium | feature

## Prevalence check
"Teaching notes prescribe fixed 4->8 step with a pre-prepared deck": two independent publishers read in full: System Dynamics Society (2017) and Jackson & Taylor/ABSEL (1998; describes the same step). Note Jackson & Taylor cite Sterman 1984 packet, so partly shared lineage, not fully independent. Treat as medium-high. "Educators grade by team cost": NOT supported; the one syllabus read grades reports. "Educators require same demand for fairness": NOT supported by any read source (only implicit).

## Leads worth chasing
- INFORMS Transactions on Education 10.1287/ited.2017.0174 (appeared in search for the 4-to-8 query; 403 on fetch). Try via author preprint or Google Scholar cache.
- MIT CTL "Rice - Beer Game Debrief" PDF (search snippet: "Was the experience the same or different for each team?"); URL 404 on fetch, search for the current CTL link.
- Calgary/DSI 2010 "Running the Beer Distribution Game for large classes" (prism.ucalgary.ca/handle/1880/51105): large-class logistics may cover multiple sections and comparability.
- Columbia "stationary beer game" PDF and Kaminsky stationary-demand literature: random i.i.d. demand variant where "all the players a priori know the demand distribution"; could show educators' reasons to randomise.
- Inderscience "Learning from online beer distribution simulation game" (search snippet: demand pattern not a significant factor, communication level was): empirical evidence demand pattern may matter little for learning outcomes.
- Forio facilitation guide (locked) and Forio/HBP help pages; ask a lecturer with access. Also transentis walk-through blog and Darden "instructor's guide and user's manual".
- Temple MIS3537 and Wisconsin Cao poster (student cost comparison and graphing) for assignment practices.
- MIT OCW 2.008 S25 Lec 15 and 15.772J slides for in-class practice.

## Looked for but not found
- Any instructor guide stating explicitly that all teams MUST get identical demand "for fairness".
- Any mention of seeds, reproducible random sequences, or deliberately re-running the same scenario to measure learning.
- Any teaching note discussing students memorising/anticipating the 4->8 step on a second play (only the "naive participants" prerequisite).
- Any syllabus that grades teams by rank or raw cost; the one syllabus found grades written reports.
- Guidance on comparability across multiple sections/semesters.
- Public detail on Forio instructor controls (demand settings, comparison dashboards): behind a locked guide.
- Recent (<=18 months) educator commentary: sources read are 1998, 2017 and 2021 plus undated or 2026 vendor pages; sentiment freshness is therefore weak. Public data is thin on this question.
