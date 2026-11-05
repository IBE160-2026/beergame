---
title: 'academic-lit research: Test questions for assessing understanding of the beer game and supply-chain dynamics'
type: 'academic-lit'
topic: 'Test questions for assessing understanding of the beer game and supply-chain dynamics'
decision: 'Which question types and themes the first Individual test bank (FR-52, FR-53) should contain, to show whether a student understands the mechanism behind demand amplification (SM-2, SM-7)'
source: 'native run'
status: complete
preset: 'standard'
validation: 'normal'
created: '2026-11-05'
updated: '2026-11-05'
claims_verified: 3
claims_disputed: 1
claims_unverified: 5
---

# academic-lit research: Test questions for assessing understanding of the beer game and supply-chain dynamics

**Decision this research serves:** Which question types and themes the first Individual test bank (FR-52, FR-53) should contain, to show whether a student understands the mechanism behind demand amplification (SM-2, SM-7)

## Executive summary

**What to do.** Build the first test bank around *accounting logic*, not pattern recall: a few graph-sketch or number items with a new cover story (stock after a demand step, production vs inventory, "how many units are missing?"), a short set of multiple-choice items for causes and definitions, and long answers that must explain the mechanism from structure (delay, supply line, own ordering rule). Treat the Adapted items (own-game) as a design bet with no precedent, and keep their total weight fixed.

**The three findings that drive this.**
1. Students who had played the beer game scored higher on a stock-flow task, but only on parts that reward remembering "it oscillates"; they did no better on conservation of material or on graph consistency [1]. A test that asks "does it oscillate?" will flatter the game and show nothing about understanding.
2. Even well-educated adults fail simple stock-flow tasks: in the original study 89% broke conservation of material and the average on the delay task was 41% [1][3]. Simple direction items ("does the stock rise?") are weak discriminators; quantity and consistency items discriminate better.
3. For a 250-student course, an LLM can score long answers only within limits measured in other settings: holistic agreement is moderate, multi-trait scoring is much worse, and bias direction varies [8][9][10]. SM-7's threshold has no published benchmark and must be calibrated on your own sample.

**Biggest caveat.** No validated beer-game test, no published rubric for free-text mechanism answers, and no study of items built from a student's own game were found. Much of the evidence is conference papers, preprints, abstracts or search summaries; confidence is flagged per claim. Two load-bearing claims were only partly confirmed (see Open questions).

## 1. The canon: measuring stock-flow and delay understanding

- The reference instrument is the "Bathtub Dynamics" systems thinking inventory: short text scenarios, the respondent sketches a graph, scored against 5–8 coded criteria; about 10 minutes; described by its authors as initial, not a validated scale [1]. The journal version is *System Dynamics Review* 16(4), 249–286 (2000) [1].
- Task types usable as items: (a) given inflow and outflow graphs, sketch the stock; (b) sawtooth inflow; (c) the Manufacturing Case: orders step from 10,000 to 11,000 a week, 4-week production delay, desired inventory 50,000. Production must overshoot orders, and the overshoot area equals the lost inventory (4,000 units) [1].
- Results (conference version, MIT Sloan students, n about 143–225 per task): about 80% correct on the easiest direction item, 48% on the sawtooth task, 41% on the Manufacturing Case; 89% broke conservation of material; 10% gave inventory consistent with production and orders. Education, age and similar variables did not predict score [1]. Confidence: high for the conference version, medium for the journal numbers.
- The explanation offered is the "correlation heuristic" (assume the stock looks like its flow): highly educated adults often cannot infer simple stock-flow behaviour, and the failure is not due to graph reading or motivation [3]. Abstract only. Confidence: high for the claim, low for task details.
- The classic beer-game mechanism is anchoring-and-adjustment ordering with weak weight on the supply line [2]. A later paper reports the average supply-line weight as 0.34 and a stock adjustment time of 3.85 weeks from Sterman's participants; the primary text was not retrievable, so only "clearly below 1" is safe [2][19]. Confidence: medium for direction, low for numbers (status: disputed against the digest's "about 0.3").
- No validity or reliability record for these tasks was found. The only psychometrically validated inventory found is for a neighbouring construct (earth system thinking), seen via abstracts. Confidence: low.

## 2. In practice: what beer-game tests ask, and what separates understanding from recall

- Beer-game players outperformed others on the Manufacturing Case (46% vs 33%) and drew oscillation more often, but the authors attribute this to recall: no gain on conservation of material or consistency, and no effect on the bathtub tasks [1]. Secondary sources confirm the direction, not the exact numbers. Confidence: high for direction, medium for numbers.
- Only one real exam was found: a 2024 take-home with an ~800-word bullwhip essay, "compare with your experience playing the Beer Game", and "what have you learnt". No answer key, no items from the student's own run [5]. Confidence: medium (single course).
- A controlled study with a delayed exam found the game helped on the "information" and "no collaboration" causes of volatility but not on delays or supply-chain structure; the game was weaker on definitions, and some gains faded by the exam six weeks later [4]. Slides only. Confidence: medium.
- Instructor debrief prompts ("Did you feel controlled by forces in the system?", "Why are there order delays?", "What is unrealistic about this game?") are structural and ungraded. They are seeds for explain-from-structure items, not validated test items [6]. Confidence: medium.
- Learning gain: a Thai one-group study (N = 65) reports 56.2 → 78.5 on a pre/post test; no control group and items not recoverable [7]. Confidence: medium-low.
- Not found: verbatim pre/post items, any rubric for free-text mechanism answers, any item built from a student's own order log, any study that uses a student's estimated supply-line weight as a graded outcome.

## 3. Limits and open debates

**Multiple choice.** Two-tier items (answer plus reason) are said to separate understood from guessed answers, but the evidence is small studies, and they can overestimate misconceptions. A third tier with confidence is the proposed fix; its benefit is not shown [17]. In a randomised comparison, constructed-response science items were harder than multiple-choice ones, partly because of the writing and reasoning demand [16]. Confidence: low. Negative marking: no evidence found.

**Long answers and human scoring.** Evidence on rubric design for causal or systems explanations was not found. Human agreement on essays is reported as about .78 (fragment), and assessor experience mattered more than rubric type in one 2026 study. Confidence: low.

**LLM scoring (formative use).**
- GPT-4o agreed perfectly with human graders on about 80% of 6,345 programming answers; humans graded higher; 30% of students found preliminary LLM grades upsetting [8]. The domain is programming, not conceptual explanation. Confirmed only on the authors' page; the venue is a short Springer proceedings paper. Confidence: high for the figure, medium for transfer.
- Open-weight 70B-class models, zero-shot on essays: holistic QWK about 0.6, multi-trait 0.32–0.41, mostly under-scoring, score compression, and agreement depends on essay length [9]. Qwen 72B on short science answers: kappa fell from 0.51 to 0.34 going from 2-way to 5-way labels, and it was lenient [10]. A meta-analysis finds GPT-style decoder models score below encoder models on short-answer scoring, and meaning-dependent items are harder [11]. Bias direction therefore differs between studies [8][9][10]. All are preprints except [8]; open-weight models, not frontier models. Confidence: medium.
- No published threshold for "good enough" for formative use was found. A bias offset on a new dataset can be detected with a small human-scored sample (often 10 or fewer) [9]. Confidence: medium.

**Personalised items.** When students get different items, plain averaging can misstate a student's score: in a simulation the most unlucky student deviated about 13% from the full-bank score, enough to change a letter grade, while a Rasch-based estimator cut this to 1.6%. That estimator needs overlap in items between students [12]. Nothing was found on comparability or motivation for items built from a student's own work. Confidence: medium for [12] (preprint, small real data), none for own-work items.

**Supervised vs unsupervised.** Unsupervised online exams gave higher grades and shorter completion times than in-person ones across more than 600 students [14]. In a take-home exam study, 94% of unedited ChatGPT-4 answers went undetected and scored on average half a grade boundary higher than real students; short answers were 200 words each [13] (verified against the PLOS ONE paper). An older meta-analysis of ability tests finds unproctored scores about 0.20 SD higher [15] (snippet only). These findings concern exams that count, mostly with older models. Nothing was found on time limits or number of attempts.

**Cut scores.** No evidence on mapping rubric totals to indicative letters; standard-setting research for constructed-response items is described as limited. Confidence: low.

## Cross-dimension insights

- The game's strongest effect is on recognising the pattern, and that is exactly what a naive "does it oscillate?" item rewards. The test must ask for something recall cannot give: a number, an area, a consistency check, or an explanation tied to a specific week [1][4].
- Adapted items and LLM scoring pull in opposite directions. Items unique to each student cannot be scored by an answer key and cannot be calibrated against other students' answers [12], so their quality rests on the LLM's reading of the Decision log, which the SM-7 sample must test directly.
- The supervision question matters mostly for the evidence, not for fairness. Because the test does not count, the risk in an unsupervised sitting is that long answers come from outside AI tools [13][14], which would inflate SM-2 and SM-7.

## Contrary evidence

Not run (red team off). The nearest counter-evidence: the Thai pre/post study reports a large gain from a beer-game course [7]. It does not contradict the recommendations below.

## Recommendations

| # | Recommendation | Feeds | Confidence basis |
|---|---|---|---|
| R1 | Include 2–3 graph-sketch or numeric items with a **new cover story**, scored on conservation (area) and on consistency between production and inventory, not on oscillation. Ask one output per item; extra required outputs lowered performance in [1]. | FR-52, SM-2 | One primary source [1]; format unvalidated. Medium. |
| R2 | Use multiple choice for definitions and the causes of amplification, with distractors built from common misconceptions, including an unrelated-cause distractor. Optionally add a reason tier. Do not rely on MC to show understanding of the mechanism. | FR-52 | Thin and indirect [4][16][17]. Low. |
| R3 | Long answers ask the student to explain from structure (delay, supply line, own ordering rule), not from other players' behaviour. Build the SM-2 rubric from 5–8 coded criteria in the style of [1]; no ready rubric exists. | FR-52, SM-2, open question 7 | Format [1], prompts [6]; rubric design not evidenced. Low-medium. |
| R4 | Keep Adapted items at a fixed total weight and treat them as a bet. Generate them from templates with the student's own numbers (same question type for everyone) so difficulty varies less. Do not grade a student's estimated supply-line weight in v1. | FR-53 | Template idea is inference from [12]; no precedent for own-game items. Low. |
| R5 | For the pilot, take the test **supervised** (for example in a lab hour), at least for a sample large enough to measure SM-2. Allow unsupervised sittings later if long answers look machine-written. Fix the time limit by piloting; no evidence on 60 minutes or one attempt. | FR-51, open question 7, SM-2 | Evidence from counting exams and older models [13][14]. Medium for the risk, none for the duration. |
| R6 | Calibrate SM-7 on the founder-scored sample: score each long answer holistically, not on many traits; estimate a bias offset; report agreement as exact and within-one-step; set the threshold (the draft's 80% within one step) after seeing the first sample. | SM-7, FR-54 | Open-weight and different-domain evidence [8][9][10]; no published threshold. Low-medium. |
| R7 | Keep the indicative letter bands as a lecturer setting with a simple default; no evidence supports particular cut points. | FR-56 | None. |

## Open questions

1. Exact figures in the journal version of [1] (46% vs 33% and the null conservation result): confirm from the SDR text or MIT working paper WP 4132-00; both fetches failed.
2. Sterman's 1989 parameter estimates (adjustment fraction and supply-line weight): confirm from the Management Science paper or MIT working paper SWP-1933.
3. Which rubric structure scores a free-text "why did the bullwhip happen?" answer reliably? Not found in the literature; needs a pilot with two scorers.
4. How well do frontier LLMs score conceptual long answers against a rubric (QWK, within-one)? Existing evidence is open-weight models and programming answers.
5. How comparable is difficulty across own-game Adapted items? No evidence.
6. What time limit and how many attempts? No evidence found.
7. Not retrieved: Plate's Systems Thinking Concept Inventory, Croson & Donohue, Wu & Katok, Kapmeier et al. 2015, Ossimitz/Kainz. A Deepen run could read them.

## Source appendix

| # | Finding it supports | Publisher | Pub date | Accessed | Confidence |
|---|---|---|---|---|---|
| [1] | Bathtub/Manufacturing tasks, results, beer-game recall effect | [System Dynamics Society conference proceedings](https://proceedings.systemdynamics.org/2000/PDFs/sweeney4.pdf) (preliminary version); journal: Wiley, SDR 16(4); [MIT working paper](https://dspace.mit.edu/handle/1721.1/2777) | 2000 | 2026-11-05 | high direction / medium numbers |
| [2] | Anchor-and-adjust ordering, supply-line neglect | [INFORMS Management Science 35(3)](https://econpapers.repec.org/RePEc:inm:ormnsc:v:35:y:1989:i:3:p:321-339) (listing only) | 1989 | 2026-11-05 | medium direction / low numbers |
| [3] | Correlation heuristic, adults fail stock-flow | [Elsevier OBHDP 108(1), via Sterman's page](https://www.mit.edu/~jsterman/Why_Adults_Accumulation.html) (abstract) | 2009 | 2026-11-05 | high claim / low detail |
| [4] | Game vs lectures, causes of volatility, fading | [Univ. Warwick / Economics Network slides](https://www.economicsnetwork.ac.uk/dee2011/presentations/mcmahon_games.pdf) | 2011-09 | 2026-11-05 | medium |
| [5] | Real take-home exam with Beer Game reflection | [CYCU Temple program exam](https://www.mgt.ncu.edu.tw/~ckfarn/PDF/2023S%20Temple%20Integrated%20BSys%20mid%20term.pdf) | 2024-04 | 2026-11-05 | medium |
| [6] | Debrief prompts | [beergame.org](https://beergame.org/teaching/debriefing) | undated | 2026-11-05 | medium |
| [7] | Thai pre/post gain | [J. MCU Social Development 11(2)](https://so06.tci-thaijo.org/index.php/JMSD/article/download/294330/196487/1392734) | 2026-06 | 2026-11-05 | medium-low |
| [8] | GPT-4o vs human grading, 80% perfect agreement | [Springer CCIS 2591 (Korthals et al.), via author page](https://lukekorthals.github.io/publications/grading-university-students-with-llms.html) | 2025 | 2026-11-05 | high figure |
| [9] | Open-weight LLM essay scoring QWK | [arXiv preprint 2604.00259](https://arxiv.org/html/2604.00259) | 2026-03 | 2026-11-05 | medium |
| [10] | Short-answer scoring kappa, leniency | [arXiv preprint 2601.08843](https://arxiv.org/html/2601.08843) | 2025-12 | 2026-11-05 | medium |
| [11] | Meta-analysis decoder vs encoder | [arXiv preprint 2603.04820](https://arxiv.org/html/2603.04820) | 2026-03 | 2026-11-05 | medium |
| [12] | Random item subsets and fairness | [arXiv preprint 2304.06254](https://ar5iv.labs.arxiv.org/html/2304.06254) | 2023-04 | 2026-11-05 | medium |
| [13] | 94% undetected AI submissions | [PLOS ONE 19(6) e0305354](https://pmc.ncbi.nlm.nih.gov/articles/PMC11206930) | 2024-06 | 2026-11-05 | high |
| [14] | Unsupervised vs in-person exams | [Acta Univ. Sapientiae Informatica, via aggregator](https://www.synapsesocial.com/papers/69be37726e48c4981c677153) | 2026-03 | 2026-11-05 | medium |
| [15] | Unproctored vs proctored ability tests | [Hogrefe EJPA](https://econtent.hogrefe.com/doi/10.1027/1015-5759/a000494) (snippet) | before 2023 | 2026-11-05 | medium (snippet) |
| [16] | MC vs constructed-response difficulty | [Springer ESM (Sangwin & Jones)](https://doi.org/10.1007/s10649-016-9725-4) (snippet) | about 2016 | 2026-11-05 | low-medium |
| [17] | Two-tier and three-tier diagnostic items | [NAAEE and small journals](https://eepro.naaee.org/research/eeresearch/new-diagnostic-test-measures-misconceptions) (snippets) | various | 2026-11-05 | low |
| [19] | Supply-line weight 0.34 (secondary) | [Albany archive, SD conference paper](https://archives.albany.edu/description/catalog/ua435aspace_dd9414c6ff6768850d7309c95004802c) | n/a | 2026-11-05 | low |

## Staleness map

LLM scoring and AI-misuse claims age fastest (12-month window); the seminal beer-game result has no bar.

| Claim | Class | Published | Re-check |
|---|---|---|---|
| Open-weight LLM essay scoring [9] | llm-scoring | 2026-03 | 2027-03-31 |
| GPT-4o 80% agreement [8] | llm-scoring | 2025-06 | **2026-06-01 (already past)** |
| Qwen 72B kappa [10] | llm-scoring | 2025-12 | 2026-12-21 |
| 94% undetected [13] | ai-misuse | 2024-06 | **2025-06-26 (already past; GPT-4 era)** |
| Unsupervised exam gap [14] | ai-misuse | 2026-03 | 2027-03-19 |
| Random-subset fairness [12] | assessment-method | 2023-04 | 2028-04-01 |
| Beer-game recall effect [1] | seminal | 2000 | none |

Earliest re-check date: 2025-06-26, already due. A Refresh should start with [13] and [8].
