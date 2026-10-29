# Digest beergame-learning-r3-e (round 3, retrieval-focused)

Accessed: 2026-10-26. Budget used: 15 tool calls (4 searches... see list), 8 distinct sources touched.

## Questions
1. Martin, Gonzalez & Lebiere (2004): n, design, repetitions, demand identical across trials?, what improved, statistics.
2. Fu & Gonzalez (2006): same.
3. Diehl & Sterman (1995): findings, one paragraph, from abstract page.
4. Paich & Sterman (1993): confirm abstract wording on repetition improving performance without insight.

## Searches / fetches run
- WS: Martin Gonzalez Lebiere 2004 ACT-R beer game -> found title + CMU PDF URL + kilthub URL
- WS: Fu Gonzalez 2006 instance-based beer game -> found actual title "Learning in Dynamic Decision Making: Information Utilization and Future Planning"
- WS: Paich Sterman 1993 abstract -> INFORMS, IDEAS, MIT DSpace WP 3441-92
- WF kilthub.cmu.edu (Martin) -> HTTP 403
- WF web.archive.org (Fu PDF) -> blocked by tool ("unable to fetch from web.archive.org"); archive route unavailable in this environment
- WF pubsonline.informs.org/doi/fpi/10.1287/mnsc.39.12.1439 -> HTTP 403
- WF cmu.edu/.../FuandGonzalezCogSci2006.pdf -> 404 (3rd failure overall incl. the lead's two)
- WF ideas.repec.org Paich-Sterman -> OK (abstract paraphrase + one verbatim phrase; fetch tool caps quotes at 125 chars)
- WF cmu.edu/.../MartinGonzalezLebiere2004.pdf -> 404
- WS: Fu & Gonzalez title + participants/trials -> abstract text only (snippet)
- WS: Diehl Sterman 1995 abstract -> no abstract page surfaced; bibliographic + secondary citing only
- WF dspace.mit.edu/handle/1721.1/13151 -> Diehl 1992 PhD thesis record, no abstract
- WS: Martin Gonzalez Lebiere design/demand -> nothing new
- WF arxiv.org/pdf/2205.06483 -> unreadable compressed PDF, nothing
- WS: Diehl Sterman abstract (2nd phrasing) -> nothing new

## Findings

F1. Paich & Sterman (1993): repeated trials improved average performance but did not produce insight; feedback-complexity penalty not reduced by experience.
- Claim (abstract, as relayed by search summary of INFORMS page, and confirmed on IDEAS/RePEc by fetch): subjects performed the task repeatedly "encouraging learning"; results poor relative to potential and worsened with feedback complexity; "negative effects of feedback complexity on performance were not moderated by experience, even though average performance improved"; changes in estimated cue weights over trials "explain why subjects improve on average but fail to gain insight into the dynamics of the system"; "experience does not appear to mitigate the misperceptions of feedback".
- Verbatim seen via direct fetch (IDEAS): "Though conditions for learning are excellent, experience does not appear to mitigate the misperceptions of feedback".
- Remaining sentences ("improve on average but fail to gain insight") come from WebSearch result summary of the INFORMS page; the IDEAS fetch paraphrase is consistent ("improved on average but never gained real insight"). Not seen verbatim by me on a page fetch -> medium-high.
- Citation: Paich, M. & Sterman, J.D. (1993). Management Science 39(12), 1439-1458. doi 10.1287/mnsc.39.12.1439.
- URLs: https://ideas.repec.org/a/inm/ormnsc/v39y1993i12p1439-1458.html ; https://pubsonline.informs.org/doi/fpi/10.1287/mnsc.39.12.1439 (403 on fetch) ; MIT WP version https://dspace.mit.edu/bitstream/handle/1721.1/2419/swp-3441-26847843.pdf (not opened)
- Venue: Management Science | 1993 | peer-reviewed
- Design: simulated new-product market task, feedback strength varied across conditions, repeated trials; n and number of trials NOT retrieved (abstract only). Effect size: none retrieved.
- Accessed 2026-10-26 | confidence: medium-high for the gist (abstract seen on IDEAS, relayed on INFORMS); low for n/trials (not seen) | class: peer-reviewed, abstract-level.
- Relevance caveat: task is a new-product market simulation, NOT the beer game; and the abstract claim concerns average improvement without insight, which directly supports "repetition != understanding".

F2. Fu & Gonzalez (2006): repeated practice in the beer game significantly improved performance; improvement attributed to better information use and future planning.
- Correct title (the lead's working title was wrong): "Learning in Dynamic Decision Making: Information Utilization and Future Planning". Cognitive Science Society conference (CogSci 2006), Carnegie Mellon.
- Abstract (via WebSearch result text, snippet-only, not page-fetched): "In two experiments, the researchers examined learning behavior in the beer game. Performance improved significantly across repeated practice." Exp 1: "concurrent verbal reports indicated that performance improved through better utilization of critical information. Subjects also learned to engage in better future planning by anticipating changes in the system." Exp 2: "participants were given only the information critical for their decisions, and initial performance was significantly better, indicating faster learning." Conclusion: "poor utilization of critical information and insufficient future planning are the major factors for learning in dynamic decision making." (Quoted as relayed by the search tool, which may paraphrase.)
- URL: https://www.cmu.edu/dietrich/sds/ddmlab/papers/FuandGonzalezCogSci2006.pdf (fetch returned 404 on 2026-10-26; appears in search results though, so cache/URL may be stale)
- Venue: CogSci 2006 proceedings | 2006 | peer-reviewed conference paper
- Design: two experiments, beer game, repeated trials, verbal protocols in Exp 1, critical-info-only display in Exp 2. n, number of trials, demand sequence identical or not, effect sizes: NOT RETRIEVED.
- Accessed 2026-10-26 | confidence: low (snippet-only) | class: peer-reviewed conference, abstract-level.
- Note: improvement is attributed by the authors to information utilization and planning (a learning-of-strategy account), which is not evidence about whether demand was fixed; the fixed-demand confound remains unaddressed.

F3. Martin, Gonzalez & Lebiere (2004): evidence of learning in the beer game plus an ACT-R instance-based model that fits aggregate performance across trials and local performance within trials.
- Title confirmed: "Learning to Make Decisions in Dynamic Environments: ACT-R Plays the Beer Game". CMU repository lists posting date 2004-07-01 (per search result); venue not confirmed by me (likely a CMU Dept of Psychology technical report / conference paper; do NOT cite as journal).
- Abstract content (search-tool summary, snippet-only): starts from Sterman (1989) misperceptions of feedback; "presents evidence that people learn in the beer game"; describes a "preliminary" instance-based DDM model in ACT-R which "mimics the general patterns of human behavior observed for aggregate performance across trials and local performance within trials".
- URLs: https://www.cmu.edu/dietrich/sds/ddmlab/papers/MartinGonzalezLebiere2004.pdf (404 on fetch) ; https://kilthub.cmu.edu/articles/journal_contribution/Learning_to_Make_Decisions_in_Dynamic_Environments_ACT-R_Plays_the_Beer_Game/6571235 (403 on fetch)
- Design/n/trials/demand sequence/effect sizes: NOT RETRIEVED. The phrase "aggregate performance across trials" implies multiple trials per participant (inference, low confidence).
- Accessed 2026-10-26 | confidence: low (snippet-only) | class: tech report/conference paper (venue unverified), abstract-level.

F4. Diehl & Sterman (1995): bibliographic confirmation only; abstract NOT retrieved.
- Citation: Diehl, E. & Sterman, J.D. (1995). "Effects of Feedback Complexity on Dynamic Decision Making". Organizational Behavior and Human Decision Processes 62(2), 198-215. peer-reviewed.
- Secondhand (secondary sources citing it, as relayed by search summary; snippet-only): cited for the claims that people ignore delays and are insensitive to feedback structure; that performance initially improves but levels off at substantially non-optimal levels; that even outcome feedback does not lead many to learn. Earlier version: Diehl, E.-W. (1992), PhD thesis, MIT Sloan, "Effects of feedback structure on dynamic decision making" (advisor J. D. Sterman), https://dspace.mit.edu/handle/1721.1/13151 (record seen, no abstract; full thesis PDF 16 MB linked from page, not opened).
- Design/n/effect sizes: NOT RETRIEVED.
- Accessed 2026-10-26 | confidence: low | class: secondary-citation only. Do not attribute any specific finding to Diehl & Sterman from this digest without opening the paper.

## Answers to the lead's questions
- n participants: not retrieved for any paper.
- Number of repetitions: not retrieved for any (Fu & Gonzalez "repeated practice", Martin et al. "across trials", Paich & Sterman "repeatedly" - counts unknown).
- Demand sequence identical across trials? NOT DETERMINED for Martin et al. and Fu & Gonzalez. Neither abstract says. The confound therefore remains open; this digest provides no evidence either way.
- What improved: Fu & Gonzalez: performance (cost), attributed to information use and planning; Paich & Sterman: average performance improved but no insight, complexity penalty persists; Martin et al.: aggregate performance across trials (learning evidence), model fit.
- Transfer to different demand: not addressed in any abstract seen.

## Looked for but not found
- Full texts / methods sections of Martin et al. (2004) and Fu & Gonzalez (2006): CMU PDF URLs 404 (third attempt overall); kilthub 403; web.archive.org blocked by the fetch tool in this environment (not tried via other means). Untried within budget: Semantic Scholar, CiteSeerX, ResearchGate, escholarship.org (CogSci proceedings; Fu & Gonzalez 2006 may be at escholarship.org/uc/ under cognitivesciencesociety), core.ac.uk, Google Scholar versions, Gonzalez's later reviews (Gonzalez, Lerch & Lebiere 2003, Cognitive Science; Gonzalez & Dutt 2011 Psych Review).
- Diehl & Sterman 1995 abstract (ScienceDirect, doi likely 10.1006/obhd.1995.1075 - unverified guess, do not cite DOI).
- Sample sizes, trial counts, demand patterns, effect sizes for all four papers.
