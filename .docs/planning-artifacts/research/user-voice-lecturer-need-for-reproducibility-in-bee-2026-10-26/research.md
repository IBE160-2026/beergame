---
title: 'user-voice research: Lecturer need for reproducibility in the beer game'
type: 'user-voice'
topic: 'Lecturer need for reproducibility in the beer game'
decision: 'Must the PRD require same demand curve and comparable results across a cohort, and how deterministic must agents be'
source: 'native run (web fan-out)'
status: complete
preset: 'deep'
validation: 'normal'
created: '2026-10-26'
updated: '2026-10-26'
claims_verified: 3
claims_unverified: 3
---

# user-voice research: Lecturer need for reproducibility in the beer game

**Decision this research serves:** Must the PRD require same demand curve and comparable results across a cohort, and how deterministic must agents be

## Executive summary

**Answer.** The public evidence does **not** show that lecturers need identical demand or comparable raw results across teams for fair grading. It does show that identical demand is the *default* of the classic game, and that the one fresh educator voice we found argues for *more* variation, not less. The PRD should therefore not make cohort-wide bit-exact reproducibility a hard requirement on public evidence alone. It should make two cheaper things explicit: instructor-selectable demand (fixed series, step, or random) and a shared seed so a class can face the same scenario when the lecturer wants that.

**Three findings that drive this**
1. *Identical demand is a by-product of the artefact; no source states it as a fairness rule.* Official guidance recommends a fixed 4-to-8 step from a pre-made hidden deck as most effective for first-time players [1][2]; every board in a 400-student course carries the same pre-set demand cards, and the paper gives no rationale for that [5]. No source says identical demand is required for fair grading.
2. *Grading, where described, does not rest on raw simulation score.* In one course the game session counts 2% of the grade, awarded for attendance, and its authors advise against prizes for the winning team in a very large group [5]; one syllabus grades two team reports and does not mention scoring the simulation itself [6]. Cross-team comparison serves the debrief and a competitive frame [1][5]; no source read ties it to grades.
3. *The classic design assumes naive players, which sits uneasily with the replay thesis.* The protocol's only prerequisite is that participants have not played before, or agree not to reveal the "trick" [1]; a 2026 educator says fixed demand lets students anticipate outcomes "after just a round or two" [4]. Our reading (design reasoning, not sourced): replay needs demand that varies per run, a class-level comparison needs a shared scenario, and a seeded scenario can serve both. Counterweight: an abstract of a 2011 online-game study reports learning from repeated play with demand pattern "not" a significant factor [14] (abstract only).

**Biggest caveat.** Public data on this question is thin: the one post within 18 months that addresses fixed versus variable demand is a single educator who also promotes their own tool [4]; no Reddit or LinkedIn voices surfaced, and Hacker News, Medium and r/professors were not searched (the search tool is not social-optimised). Absence of evidence here means "not found publicly", not "lecturers do not care". Lecturer interviews are the right next step.

## 1. Who they are and what they are trying to do (jobs-to-be-done)

Lecturers run the game to make the bullwhip effect visible and then use a debrief to explain it. The official protocol is built around the debrief: "different people in the same structure produce qualitatively similar results" and cross-team differences are individual ordering choices [1]. Debrief recurs across most sources read [1][2][4][5][7][12]. Practical concerns are logistics and integrity: tracking errors distort results [4], students may "dip into the reserves" [2], and the game can be spoiled by web search (Calgary avoids calling it "The Beer Game" beforehand) [5]. A MERLOT reviewer of the MIT Sloan online game notes that assessing learning outcomes is hard and that debriefing "is crucial" [12]. Fairness-by-same-start appears in a Harvard large-scale business simulation ("all teams have the same baseline"), but that is a different game [13]. *Confidence: medium (few, partly old sources; 1998 and 2010 are outside the 18-month window).*

## 2. Complaints, workarounds and what the evidence says about demand

**Fixed demand is the classic default.** Official guidance: four cases per week until week five, then eight, as the pattern "most effective for first-time players"; the deck is prepared in advance and "should not be revealed in advance" [1]. The 1998 description is the same [2], so the two are not fully independent (shared Sterman lineage). Each board set in Calgary's large-class kit carries the same demand cards (four 4s, forty-six 8s, one stop card), so demand is identical across boards by construction; the paper lists them as kit contents and says nothing about fairness (silence, not a stated logistics rationale) [5]. *Confidence: medium-high that fixed 4-to-8 decks are the standard in published manual-game guidance; current digital-class practice was not measured.*

**Fixed demand has a known weakness.** An operations-research professor wrote in June 2026 that fixed patterns "make it easier for students to anticipate outcomes after just a round or two", so they built variable demand into their own open-source browser game [4]. The 1998 computerised game by Kaminsky and Simchi-Levi already lets the instructor choose deterministic or random demand and a step change at any time, calling the classic doubling unrealistic [3]. *Confidence: low-medium (one fresh voice, one old paper; not two independent contemporary communities).*

**No fairness complaint was found in either direction.** We found no lecturer saying identical demand is required for fairness, none saying random demand makes teams incomparable, and none about comparing sections across terms, across roughly 40 queries and 20 pages read. "Fairness" appears in the sources only for comparing cost settings across variants [3] and (in snippets) for role or position effects, not demand identity across teams. *Confidence: low-medium that this is a true gap in public sources; low that it reflects lecturer needs.*

**Cheating and prizes.** Calgary reports that in such a large group (about 100 simultaneous games) prizes for the winning team create "an incentive to ignore the game rules"; its authors note that other practitioners do award prizes, and the SDS protocol itself declares a cost-based winner [1][5]. The game session counts 2% of the course grade, for attendance [5]. This weakens, but does not remove, the case that lecturers want ranked, comparable scores. *Confidence: medium for what the source says; one source, large-class context, 2010.*

**Does demand identity affect learning?** An abstract of a 2011 online beer-game study states that learning came from repeated play and communication level "whereas the demand pattern was not" a significant factor (abstract quoted by a search result; full text paywalled) [14]. *Confidence: low; verify before relying.*

## 3. What products offer, and their language

Two products read first-hand treat demand as an instructor setting; for Forio and transentis only a competitor's description exists (and it contradicts itself, saying Forio offers a demand pattern setting but also a "fixed structure" [9]). Zensimu lets the instructor edit final consumer demand per round, save custom session templates and scenarios, and compare teams and rounds [7][8]; beergame.org lets the instructor set one predefined jump or type in a complete demand series, save settings, and download data [11]. The public Forio/Harvard page does not mention demand settings; its facilitation guide is locked [15]. Zensimu's comparison guide says Forio/MIT and transentis let the instructor set weeks, demand pattern and lead times [9] (a competitor describing rivals). Zensimu fills empty roles with a computer player and exposes ordering-behaviour settings (variability, stock target) [10] (vendor text, fetch summary).

**Market signal.** No product reads as advertising identical demand across teams, seeded demand or reproducibility. The closest wording is Zensimu's "consistency across your organization", which refers to shared templates, not demand identity [8]. Vendors differentiate on customisation, monitoring and debrief. Only four to five vendor pages were read, so this is not exhaustive.

**Educator language.** Used: "debrief", "round/period/week", "consumer demand", "demand pattern", "demand series", "anticipate outcomes", "compare teams". Not found as an educator term in the pages read: "replay", "reproducible", "same demand for all teams" ("memorization" appears once in Zensimu copy, meaning retention of lessons; "seeded" appears only in an unverified search summary [16]). Product copy aimed at lecturers should say "debrief" and "demand pattern", not "reproducibility" [1][4][8][11].

## Cross-dimension insights

- The classic game gets comparability for free from a physical deck; a digital product must choose it deliberately. The evidence supports making it a *lecturer-controlled option* (shared scenario/seed per class), not a platform-wide invariant.
- The replay thesis depends on demand that changes between a student's runs, while the debrief tradition depends on a shared structure within a class. These are compatible only if seeds are explicit: per-class seed for live sessions, fresh seed per solo run.
- Agent determinism matters only as far as comparability matters. Since comparability for grading is not evidenced as a need, bit-exact LLM-agent reproducibility is not required by this research; seeded demand plus recorded agent decisions would probably cover the comparisons we can imagine (no lecturer need was documented; see the technical cost research on determinism).

## Contrary evidence

No red-team pass ran. Points that cut against the conclusion: absence of social-platform voices may hide lecturers who do want comparable results; Zensimu's emphasis on shared templates and team comparison suggests some demand for consistency [8]; the 1998 comparison-of-variants fairness point shows researchers do care about like-for-like runs [3].

## Recommendations

1. **PRD: do not require cohort-wide identical results; require instructor-selectable demand (fixed series, step, random) and a lecturer-visible seed that can be shared across a class.** Binds to: PRD functional requirements. Basis: no evidence of a fairness requirement; instructor-set demand exists (a single jump or typed series [11]; per-round edit [7]; deterministic, random or step in a 1998 research tool [3]); a shared class seed has no source. Low-medium confidence.
2. **PRD: per-run fresh seed for solo replay by default.** Binds to: PRD, and the replay thesis in the brief. Basis: the anticipation complaint [4] (one fresh voice, who also promotes a competing tool) and the naive-player assumption [1], against a 2011 abstract saying demand pattern did not matter for learning [14]; low-medium confidence.
3. **Architecture: record agent decisions and seeds so any run can be reproduced on request**, rather than requiring deterministic agents. Binds to: architecture spine. Basis: this research's gap plus the determinism findings in the technical research.
4. **Run 5–8 short lecturer interviews before locking the requirement.** Suggested questions: How do you grade the game? Do you compare teams or sections, and does the demand need to be identical? Have students remembered the pattern? What would make you re-run the same scenario? Binds to: PRD, brief "problem" section. Basis: public evidence is too thin to decide.
5. **Use lecturers' words in product copy:** "debrief", "demand pattern", "consumer demand". Binds to: UX copy.

## Open questions

- Whether lecturers who run several sections or terms want cross-section comparability (no source addressed this); needs interviews.
- Whether students share or memorise demand sequences between cohorts (no evidence either way).
- Instructor controls behind the locked Forio/Harvard guide and the transentis facilitator page (404).
- Full text of the 2011 online beer-game study (abstract only); INFORMS Transactions on Education reports and the MIT CTL debrief deck could not be retrieved.
- A 2026 open-source clone described as "seeded" could not be fetched (403) and its seed claim is unverified [16].
- Reddit and LinkedIn site searches returned no community pages; Hacker News, Medium and r/professors were not searched. Two unopened snippet leads: an AUEB session PDF saying the order deck "can be stacked or randomized by the moderator", and ABSEL article 410 "Human and Agent Playing the Beer Game".

## Source appendix

| # | Claim / finding supported | Publisher | Pub date | Accessed | Confidence |
|---|---|---|---|---|---|
| 1 | Official protocol: fixed 4→8 step, hidden deck, naive players, debrief framing | [System Dynamics Society](https://systemdynamics.org/wp-content/uploads/2020/12/BEER-GAME-INSTRUCTIONS.pdf) | 2017-05 | 2026-10-26 | high |
| 2 | Classic game description; cheating; debrief prerequisites | [ABSEL proceedings, Jackson & Taylor](https://absel-ojs-ttu.tdl.org/absel/article/view/1049) | 1998 | 2026-10-26 | medium (old) |
| 3 | Computerised game with instructor-chosen deterministic or random demand; fair comparison of variants | [Kaminsky & Simchi-Levi (hosted at UC Berkeley IEOR)](https://kaminsky.ieor.berkeley.edu/Reprints/PK_DSL_98b.pdf) | c. 1998 | 2026-10-26 | medium (old) |
| 4 | Fixed demand lets students anticipate outcomes; manual tracking errors | [Times Higher Education Campus](https://timeshighereducation.com/campus/less-beer-more-couscous-gamifying-supply-chain-education) | 2026-06-07 | 2026-10-26 | medium (one voice) |
| 5 | Calgary large class: one deck, attendance-only grade, no prizes, spoiler risk, delayed debrief | [Decision Sciences Institute proceedings](https://ucalgary.scholaris.ca/bitstreams/a2ba791f-01dc-4ab9-b30b-5150fc59379b/download) | 2010-11 | 2026-10-26 | medium (old) |
| 6 | Syllabus grades two team reports (a Beer-Game-derived web simulation); scoring of the simulation itself not mentioned | [University of Washington Foster](https://foster.uw.edu/wp-content/uploads/2021/08/OPMGT-560-WIN21.pdf) | 2021-08 | 2026-10-26 | high (one syllabus) |
| 7 | Zensimu instructor settings, templates, team comparison | [Zensimu help center](https://docs.zensimu.com/article/21-organize-beer-game-session) | 2026-01-31 | 2026-10-26 | medium (vendor) |
| 8 | Zensimu: "consistency across your organization"; comparison features | [Zensimu comparison page](https://zensimu.com/comparison/zensimu-vs-transentis-beer-game) | undated | 2026-10-26 | medium (marketing) |
| 9 | Zensimu description of rivals' demand settings | [Zensimu comparison guide](https://zensimu.com/resources/best-beer-game-simulations-comparison-guide/) | 2026 | 2026-10-26 | medium (competitor) |
| 10 | Zensimu instructor guide: computer player settings, second round varies information | [Zensimu](https://zensimu.com/resources/complete-instructor-guide/) | undated | 2026-10-26 | medium (vendor, fetch summary) |
| 11 | beergame.org: predefined jump or typed demand series, saved settings | [beergame.org](https://beergame.org/software/features/) | undated | 2026-10-26 | medium (vendor) |
| 12 | MERLOT review of MIT Sloan Beer Game Online | [MERLOT](https://www.merlot.org/merlot/viewCompositeReview.htm?id=1383295) | 2025-01-09 | 2026-10-26 | medium (one reviewer) |
| 13 | HBS large-scale simulation: same baseline for all teams (different game) | [Harvard Business School Working Knowledge](https://www.library.hbs.edu/working-knowledge/in-this-classroon-beer-can-improve-your-grade) | 2016-03-09 | 2026-10-26 | low (old, different game) |
| 14 | Online beer game study: repeated play and communication mattered, demand pattern did not | [Inderscience](https://www.inderscience.com/offers.php?id=42668) | 2011 | 2026-10-26 | low (abstract via snippet) |
| 15 | Forio/Harvard page lacks demand-setting detail; guide locked | [Forio](https://forio.com/store/mit-beer-game-supply-chain-simulation) | undated | 2026-10-26 | medium |
| 16 | Open-source "seeded" clone, unverified lead (fetch returned 403; search summary only, not retrieved) | [CUNY academic blog](https://jncohen.commons.gc.cuny.edu/?p=13045) | 2026 | not retrieved | low |

## Staleness map

Computed with `recon_kit.py staleness` on 2026-10-26 (windows: sentiment 18 months, vendor features 6 months, seminal guidance effectively none).

| Claim | Class | Re-check by |
|---|---|---|
| Fixed demand is predictable, single educator voice [4] | sentiment | 2027-12-01 |
| Zensimu and beergame.org instructor demand settings [7][11] | feature | stale since 2026-07-01: re-check vendor pages |
| SDS protocol fixed 4-to-8 [1] | seminal | none |
| Calgary large-class practice [5] | sentiment | stale since 2012-05 (kept as a historical reference only) |

**Earliest re-check: now, for vendor features (2026-07-01 window passed).** The core finding is an absence of evidence, so any new public lecturer voice should trigger a refresh.
