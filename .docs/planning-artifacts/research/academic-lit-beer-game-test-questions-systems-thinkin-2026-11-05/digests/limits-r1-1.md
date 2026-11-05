# Digest limits-r1-1: limits and open debates, MCQ + long answers, LLM scoring, personalised items, supervision, cut scores

Researcher run 2026-11-05. Budget: 17 tool calls, 8 pages fetched in full (marked READ), the rest known only from search-engine summaries (marked SNIPPET: lower confidence, abstract-level, not verified against full text).
Fields per claim: claim | source | publisher | pub_date | accessed 2026-11-05 | confidence | class. Peer-reviewed vs preprint labelled in "publisher".

## A. Multiple-choice: guessing, what MCQ can show, mitigations

A1. Two-tier items (answer + reason) are described as reducing measurement error from guessing, and as separating lack-of-knowledge errors from misconception errors and guessed-correct from understood-correct answers. Evidence base is small, locally published studies (chemistry, pre-service teachers); effect size of the guessing reduction not quantified in what was retrieved.
- Source: https://eepro.naaee.org/research/eeresearch/new-diagnostic-test-measures-misconceptions ; https://openaccess.mku.edu.tr/items/adea3f6d-b247-4a6b-8231-2955662bd2c7/full (and other small-journal hits) | NAAEE / Mus Alparslan Univ. repository, various | various, undated in snippet | accessed 2026-11-05 | confidence low (SNIPPET, small studies) | class: recommendation / descriptive

A2. Two-tier tests can still OVERESTIMATE misconceptions (a pre-service-teacher study found one-tier and even two-tier tests overestimate misconception percentages), because every wrong answer pair is counted as a misconception; the fix proposed in the literature is a third tier with confidence rating (three-tier) or a Certainty of Response Index (CRI).
- Source: same search results as A1 (Tuysuz-type papers; scribd/local journals) | various | undated | accessed 2026-11-05 | confidence low (SNIPPET) | class: empirical-result (small study) / recommendation

A3. A Rasch-based study of a water-cycle test found integrating confidence into mastery "did little to change item functioning", while three-tier use gave higher reliability and lower student ability estimates than two-tier use. A 2024 study criticises yes/no confidence as too coarse (does not capture "somewhat confident"). Whether a third tier actually reduces guessing effects on established inventories is not shown.
- Source: https://journal.unnes.ac.id/journals/jise/article/download/13578/2523 ; https://revistia.com/index.php/ejser/article/view/3405/3241 | Unnes J. Innovative Science Education; European J. Social & Educational Research | 2024-2025 | accessed 2026-11-05 | confidence low-medium (SNIPPET) | class: empirical-result

A4. Concept-inventory note (Waters & Amarie 2019, citing Yasuda et al. and Stewart et al.): the Force Concept Inventory has questions more prone to guessing; linear models have been proposed to adjust scores for guessing. Secondhand via snippet.
- Source: https://par.nsf.gov/servlets/purl/10180349 (hit in the three-tier search; exact attribution via snippet) | NSF PAR | 2019 | accessed 2026-11-05 | confidence low (SNIPPET, secondhand) | class: empirical-result

A5. MCQ vs constructed response: when randomly assigned, constructed-response (CR) science items were MORE difficult than MC counterparts (Herrmann-Abell et al.), attributed partly to writing demand and the reasoning element of the CR rubric; authors conclude CR is needed when constructing an explanation is itself the target. Shepard (2008, quoted by Sangwin & Jones): identical items in both formats measure the same thing, so differences reflect item construction, not format alone. No large higher-education causal-reasoning study or meta-analysis surfaced.
- Source: https://doi.org/10.1007/s10649-016-9725-4 (Sangwin & Jones, Educational Studies in Mathematics) ; https://core.ac.uk/works/2890982 | Springer / CORE | 2016-ish | accessed 2026-11-05 | confidence low-medium (SNIPPET) | class: empirical-result / theoretical

A6. Practitioner guidance only (no empirical test): MC can probe cause-and-effect reasoning if distractors reflect common misconceptions.
- Source: https://academics.lmu.edu/assessment/resources/assessmentresources/examsforassessment/testingfordepthofunderstanding/ | Loyola Marymount Univ. assessment page | undated | accessed 2026-11-05 | confidence low (grey/practitioner) | class: recommendation

A7. Negative marking / formula scoring: NOT found in this run.

## B. Long answers: human scoring reliability, rubric design

B1. Weak evidence retrieved. Jonsson & Svingby (2007, Educ. Res. Rev.) was cited by later work for the claim that rubrics help raters score more consistently; the original effect sizes were NOT retrieved. A 2023 meta-analysis (Yun) reports human inter-rater agreement about .78 for essay scoring (fragmentary snippet).
- Source: https://link.springer.com/10.1007/s10648-023-09823-4 ; https://files.eric.ed.gov/fulltext/EJ1407232.pdf | Springer (Educ. Psych. Review); ERIC | 2023 | accessed 2026-11-05 | confidence low (SNIPPET) | class: agreement-statistic ("about .78", unverified)

B2. A 2026 biosciences study concluded assessor experience, more than rubric type or guidance, primarily determines grading reliability. Analytic vs holistic comparisons are mixed (one Turkish study: low inter-rater reliability when holistic and analytic raters scored the same essays; one Korean study: highest reliability with multiple-trait scoring).
- Source: https://eprints.whiterose.ac.uk/id/eprint/240546 ; https://dergipark.org.tr/en/download/article-file/183038 ; https://db.koreascholar.com/Article/Detail/272854 | Univ. of Sheffield/Leeds eprints (White Rose); DergiPark; KoreaScholar | 2026 / undated | accessed 2026-11-05 | confidence low (SNIPPET) | class: empirical-result

B3. Benchmark for human-human agreement on short constructed responses: about 0.89 QWK on ASAP short-answer data (secondhand, from an arXiv search summary of arXiv 2408.09540).
- Source: https://www.arxiv.org/pdf/2408.09540 | arXiv (preprint) | 2024 | accessed 2026-11-05 | confidence low (SNIPPET) | class: agreement-statistic

B4. Rubric design for explanation/argument questions specifically (e.g. causal-chain rubrics, SOLO): NOT found in this run.

## C. LLM scoring of free text

C1. READ. Korthals et al., AIED 2025: GPT-4o vs human graders on 6,345 answers (58 graduate students, intro programming course, weekly assignments): "GPT-4o and human graders agreed perfectly in 80% of 6345 evaluated student answers." Human-LLM grade correlation r = .570-.866 per assignment. Humans awarded HIGHER grades; humans overlooked some student mistakes; GPT-4o graded ambiguous cases more strictly and misgraded some. Students: 77% found LLM feedback helpful; 30% said preliminary LLM grades lower than their actual grades made them anxious or upset. Authors: avoid certain tasks and improve rubrics to reconcile most errors. Within-one agreement not reported. Programming domain, not conceptual explanation.
- Source: https://dare.uva.nl/id/9169a478-7822-4d61-b4ee-49aad1a18a1d | AIED 2025, Springer CCIS pp. 36-43 (peer-reviewed conference; UvA repository) | 2025 | accessed 2026-11-05 | confidence medium-high | class: agreement-statistic / empirical-result

C2. READ. Kucia, Chakraborty & Wroblewska, zero-shot open-weight LLMs (Llama-3.1 8B/70B/405B, GPT-OSS 20B/120B), three essay datasets: best holistic QWK about 0.6 (ASAP 2.0: Llama 3.1 70B 0.533 keywords / 0.601 guidelines; 405B 0.496 / 0.592). Analytic multi-trait QWK much lower: ELLIPSE best 0.321, DREsS best 0.414. GPT-OSS 120B only 0.117 / 0.299 on ASAP 2.0. Bias mostly NEGATIVE (under-scoring), all p<0.001 (e.g. Llama 70B Keywords: ASAP -0.39, ELLIPSE -0.66; GPT-OSS 120B -1.57 on ELLIPSE). Model score SD lower than human SD (score compression). Length sensitivity (Pearson r with length, human vs LLM): ASAP 2.0 0.71 vs 0.47; DREsS 0.37 vs 0.39; ELLIPSE 0.18 vs 0.33. Detecting a systematic offset needs small human-labelled sets: "often N<=10" (median N_min 5-10; 90th percentile about 175 in some datasets). Proposes bias-correction-first. Open-weight models, English L2/ESL-type essays, not GPT-5-class; the longer "Guidelines" rubric did not consistently help analytic scoring (helped holistic only).
- Source: https://arxiv.org/html/2604.00259 | arXiv preprint (Warsaw Univ. of Technology; Wolverhampton) | 2026-03-31 | accessed 2026-11-05 | confidence medium | class: agreement-statistic / empirical-result

C3. READ. Deng et al. (Purdue), Qwen 2.5 72B on SciEntsBank (short science answers), no fine-tuning: "Accuracy dropped from 76% to 57%, while Kappa dropped from 0.51 to 0.34" going from 2-way to 5-way labels. Model "generally more lenient than human graders/reference labels"; most common error: labelling "Partially Correct" as "Correct". Synonym substitution caused the largest degradation; typos/OCR also hurt. Deferral to humans on low confidence: 5-way accuracy rose 59.3% to 64.1% while coverage fell 92.8% to 54%. No rubric ablation; QWK and within-one not reported; verbosity not studied. Direction of bias (lenient) CONFLICTS with C1/C2 (strict), so bias direction is dataset/model/prompt dependent.
- Source: https://arxiv.org/html/2601.08843 | arXiv preprint (Purdue) | 2025-12-21 | accessed 2026-11-05 | confidence medium | class: agreement-statistic / empirical-result

C4. READ. Hardy (Stanford) meta-analysis of 890 results on LLM short-answer scoring: decoder (GPT-style) models score lower than encoder models (Bayes posterior mean about -0.39 in text, Table 2 lists -0.37, on the Fisher-z scale); meaning-dependent items harder (about -0.21). Pooled QWK not reported in the part read; rubric/prompt/few-shot NOT modelled as moderators; no acceptability threshold stated. One illustrative case of name-swapped identical work (White vs Black) scoring 1 vs 0 out of 2 (single example, not systematic). Final third of page unread.
- Source: https://arxiv.org/html/2603.04820 | arXiv preprint v2 (Stanford) | 2026-03-26 | accessed 2026-11-05 | confidence medium (preprint, single author) | class: empirical-result (meta-analysis)

C5. SNIPPET. Jiang & Bosch (GPT-4, ASAP-SAS): mean QWK 0.677 across items, depends on how rubric and scored examples are supplied. Shermis (ChatGPT-4o, 25,683 responses, 10 prompts) benchmarked with QWK; rubric and source material in prompt. Aggregate reading: reported GPT QWK for short-answer scoring about 0.6 to 0.9 depending on dataset and prompt design.
- Source: https://pnigel.com/papers/jiang-inpress-63CP3WFU.pdf (mirror host seen as meilu.jpshuntong.com proxy); https://www.themoonlight.io/review/using-chatgpt-to-score-essays-and-short-form-constructed-responses | author page / third-party review | 2024-2025 | accessed 2026-11-05 | confidence low (SNIPPET, secondhand) | class: agreement-statistic

C6. SNIPPET. A 2026 three-course preprint reports AI-human ICCs exceeding human-human ICCs on all five rubric dimensions, but recommends calibrated human-AI co-grading, not replacement. A 2026 sustainability-education study reports only moderate total-score agreement, declining at higher cognitive levels. A study reports ChatGPT marks lower than humans by a mean bias of -1.34 on a 10-point scale.
- Source: https://www.preprints.org/manuscript/202605.1284 ; https://gcris.yasar.edu.tr/entities/publication/1eeab52d-b73f-42b4-baa8-f2c94edfc8c1 | Preprints.org (preprint); Yasar Univ. | 2026 | accessed 2026-11-05 | confidence low (SNIPPET) | class: agreement-statistic

C7. Verbosity/position/format bias: general LLM-as-judge literature acknowledges it, but no GPT-class essay-scoring study measuring it directly was retrieved except the length-correlation figures in C2. Blog-level only: a verdict flip rate above 10% under length-matching is called "meaningful confound" (single blog, NOT a validated threshold).
- Source: https://tianpan.co/blog/2026-04-27-llm-judge-bias-audit-length-position-format | personal blog | 2026-04-27 | accessed 2026-11-05 | confidence low (blog) | class: recommendation

C8. Published thresholds for "good enough" for formative use: NONE retrieved. Only the human benchmark (about 0.89 QWK on ASAP short answers, B3) as an upper reference. Common practice values (e.g. QWK >= 0.70) were NOT sourced in this run and must not be asserted.

## D. Personalised / individually generated test items

D1. READ. Chen, Hartline & Zoeter, "Fair Grading Algorithms for Randomized Exams": when each student gets a random subset of a question bank, simple averaging is fair ex-ante but not ex-post if difficulties differ. Real data (35 students, 22 questions): question difficulties span about -3.09 to 2.10 on the Rasch logit scale (student abilities -1.49 to 1.15). Simulation with 10 of 22 questions per student: the most unlucky student under simple averaging deviates about 13% from full-bank benchmark vs about 1.6% for a Rasch-based estimator; "this deviation could change a student's letter grade". Rasch estimator beats averaging when students get at least seven questions; reduces bias by about 99%, raises variance about 10%. Needs overlap of items between students (not applicable to fully unique items).
- Source: https://ar5iv.labs.arxiv.org/html/2304.06254 | arXiv preprint (Stanford, Northwestern, Booking.com) | about April 2023 (page gives no date) | accessed 2026-11-05 | confidence medium | class: empirical-result (simulation + small real data)

D2. SNIPPET. Individualised MC exams are argued to reduce cheating and push students toward concepts over memorised answers ("Cheat-resistant multiple-choice examinations using personalization"). A chemistry/physics/physiology study found quantitative problems are easiest to vary without changing mean performance; other question types harder. A Stanford "unique exams" framework generates per-student versions from a skeleton with numeric/lexical perturbation. Peking University paper: variants must capture similar knowledge requirements; asynchronous exams more exposed to collaboration.
- Source: https://ar5iv.labs.arxiv.org/html/2009.01713 ; https://par.nsf.gov/servlets/purl/10299904 ; https://www.nsta.org/journal-college-science-teaching/journal-college-science-teaching-marchapril-2023/issues-question | arXiv / NSF PAR / NSTA journal | 2020-2023 | accessed 2026-11-05 | confidence low-medium (SNIPPET) | class: empirical-result / recommendation

D3. Items tied to each student's own work (open-ended, personalised by student artefact, e.g. their own simulation run): comparability of difficulty across such items, and effects on motivation: NOT found. Existing literature found concerns numerically varied items from a skeleton, not work-anchored prompts. Absence of evidence is a finding.

## E. Supervised vs unsupervised; AI use; duration and attempts

E1. SNIPPET. 3-level meta-analysis, 49 studies, over 100,000 test-takers, 109 effect sizes: unproctored ability tests scored about 0.20 SD higher than proctored; smaller effect for measures hard to look up. These are ability/personnel tests, pre-generative-AI, not course exams.
- Source: https://econtent.hogrefe.com/doi/10.1027/1015-5759/a000494 | Hogrefe (Eur. J. Psychological Assessment, peer-reviewed; exact article metadata per snippet) | pre-2023 | accessed 2026-11-05 | confidence medium (SNIPPET) | class: empirical-result (meta-analysis)

E2. SNIPPET. Course-level older findings are mixed: Hollister & Berenson (2009) found, controlling for GPA, no significant mean difference between proctored and unproctored groups, but greater variation in unproctored; Iowa State analysis found no clear evidence of cheating but cautioned single university and pre-ChatGPT.
- Source: https://digitalcommons.montclair.edu/infomgmt-busanalytics-facpubs/10 ; https://www.news.iastate.edu/news/2023/08/09/exams-cheat | Montclair State Univ.; Iowa State news release | 2009 / 2023 | accessed 2026-11-05 | confidence low-medium | class: empirical-result

E3. READ. Klein & Malik, six exam sessions (three online unsupervised, three in-person), more than 600 students: unsupervised online had higher average grades and shorter completion times (authors interpret this as AI-assisted cheating, not a direct measure of AI use); in-person lower, "more realistic"; exam format and question design explained a large share of grade variance (eta-squared = 0.667); rewording questions in more complex language narrowed the gap. No proctored-online condition; no exact means or p-values on the page read; no limitations section.
- Source: https://www.synapsesocial.com/papers/69be37726e48c4981c677153 (aggregator of Acta Universitatis Sapientiae, Informatica) | Acta Univ. Sapientiae Informatica (open access journal) | 2026-03-19 | accessed 2026-11-05 | confidence medium | class: empirical-result

E4. SNIPPET (news coverage of PLOS ONE paper; primary not read). University of Reading, Scarfe et al. 2024: 33 fake student submissions written by ChatGPT-4 unedited into the real take-home exam system; 94% undetected; AI submissions received higher grades than real students in 83.4% of cases. Format: four answers from six questions, 200-word limit each (short answers). Authors recommend moving away from unsupervised take-home exams; markers were not told of the study. Note age: 2024, GPT-4 era.
- Source: https://www.techtimes.com/articles/306101/20240627/chatgpt-exam-answers-go-undetected-beating-human-students-uk-university.htm (secondary) ; primary PLOS ONE 2024, not opened | TechTimes (secondary) | 2024-06-27 | accessed 2026-11-05 | confidence low-medium (secondary coverage of peer-reviewed study) | class: empirical-result

E5. Typical or justified duration, number of attempts: NOT found. No source retrieved on time limits or attempts for written conceptual tests.

## F. Cut scores / grade bands from rubric totals

F1. SNIPPET. Angoff-type standard setting is well studied for selected-response tests; research for constructed-response items is "much more limited"; Plake and colleagues' adaptation to a high-school writing assessment was "less than successful". Näsström & Nyström (2008) compared Angoff vs borderline-group on Swedish national maths test with constructed-response items and concluded both are reasonable and trustworthy approaches but confirm some of the potential problems.
- Source: https://openpublishing.library.umass.edu/pare/article/1500/galley/1451/view (Practical Assessment, Research & Evaluation, peer-reviewed) | UMass PARE | date not captured | accessed 2026-11-05 | confidence low-medium (SNIPPET) | class: descriptive / empirical-result

F2. A calculator page states ICC(2,k) above 0.80 indicates good inter-judge reliability in Angoff panels; this is a tool description, not a peer-reviewed threshold.
- Source: https://metricgate.com/calculator/angoff-standard-setting | vendor page | undated | accessed 2026-11-05 | confidence low | class: recommendation
- Direct evidence on mapping rubric totals to indicative letter grades: not found.

## Leads worth chasing
- Primary PLOS ONE paper (Scarfe et al. 2024) and any 2025-2026 replication with newer models in unsupervised written exams.
- Hogrefe meta-analysis (Eur. J. Psych. Assessment) to confirm authors, year and effect size for E1.
- Jonsson & Svingby 2007 (Educ. Res. Rev.) and Yun 2023 for B1 numbers.
- Hardy 2026 (arXiv 2603.04820) appendix and the remaining third of the page for the pooled QWK and study count.
- Sangwin & Jones / Herrmann-Abell for A5; Waters & Amarie 2019 plus FCI guessing literature (Stewart et al.) for A4.
- "Rubric-conditioned" and "analytic rubric" LLM scoring with frontier models (GPT-5-class, Claude-class); C2 and C3 used open-weight 70B-class models.
- Stanford "unique exams" (arXiv 2009.01713) full text for D2.
- Plake et al., Näsström & Nyström 2008 for rubric-based standard setting (body-of-work, borderline-group).

## Looked for and could not find
- Negative-marking evidence for conceptual tests.
- Empirical comparison of confidence-rated MCQ vs unrated MCQ on guessing in a university course.
- Rubric designs validated for causal/systems explanation answers; inter-rater kappa for such answers with trained markers.
- Published "good enough" thresholds for LLM-human agreement in formative use.
- Direct measurement of verbosity, position or format bias of GPT-class models on student essays/short answers (only length correlations in C2).
- Evidence on score comparability across individually generated, student-work-anchored items; evidence on motivation effects of personalised items.
- Evidence on test duration or number of attempts for written conceptual tests.
- Evidence on mapping rubric totals to letter grades.
