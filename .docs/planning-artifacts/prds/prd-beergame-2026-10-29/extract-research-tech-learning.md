# Extract: technical-cost and learning research for the beergame PRD

Extracted 2026-10-29. Paths are relative to `.docs/planning-artifacts/research/`.
- **T** = `technical-ai-agent-cost-per-beer-game-session-2026-10-26/research.md`. **MS** / **SCR** = its `model-switcher/model_switcher.py` / `screen-2026-10-29.json`.
- **L** = `academic-lit-repeated-play-and-debrief-learning-effec-2026-10-26/research.md`.
- **Td:** / **Ld:** = digests in those folders. **X:** = a cross-reference outside the two reports, used only to settle a number.
- Conflict: T (Rec 1, §3e) recommends rule-based opponents with the LLM used for text. The founder chose LLM opponents as the default, with rule-based opponents per class (Issue #10).

## 1. Game parameters and the Sterman heuristic
- **Neither T nor L states the classic parameters.** T's cost model assumes 3 AI roles × 36 turns; 20–50 turns scales cost by ×0.56–1.39 [Td:llm-cost-r1-a §C].
- Classic configuration as implemented by En Dash (X: competitive `teardown-r3-m.md`, high): 4 roles; inventory 12; pipeline 4 per slot; demand 4, stepping to 8 at week 5; holding 0.5, backlog 1.0; order delay 1, shipping delay 2; 36 weeks; demand fixed.
- System Dynamics Society protocol (X: user-voice `teaching-notes-r1-b.md` #1–2, 2017, high): demand is 4/week, then 8 from week 5. Players are told **50 weeks** "to prevent horizon effects". The game stops around week 35 and demand is not revealed in advance.
- Long et al. ran 25-week games, 30 runs per configuration [Td:llm-cost-r1-a #2]. Constant demand of 4/week still produced oscillation [L§1].
- **Sterman (1989) anchoring-and-adjustment rule:** a smoothed forecast (θ), a stock-adjustment fraction (α_S), a supply-line weight (β) and desired inventory (S*) [T§2].
- **The fitted values were NOT retrieved.** The figures α_S ≈ 0.3 and β ≈ 0 come from a calculator site and "should not be used" [T§2]. The values are in the online supplement §B of Oroojlooyjadid et al. [Td:nonllm-arch-r2-d #4]. How well the heuristic matches human bullwhip is "not evidenced". Issue #8.

## 2. LLM opponent economics
- **No source publishes tokens, cost or latency per session** [T§1].
- Assumed load (unverified): 108 calls per session; 2,000 input tokens per call (1,200 cacheable) and 150 output tokens with no reasoning [T§1].
- **Cost per session, uncached / cached** [T§1; re-verified in Td:verification-technical A0]:
  - gpt-5-nano $0.017 / $0.012
  - Flash-Lite 2.5 $0.028 / $0.016
  - **Haiku 5.5 $0.030 / $0.018**
  - gpt-5-mini $0.086 / $0.057
  - Sonnet 5.5 $0.59 / $0.35
- The OpenRouter fee multiplies cost by ×1.055 (Business ×1.08). EU-routed Haiku costs about $0.035 [T§4].
- **Cheaper endpoints (snapshot 2026-10-29)**, which exclude reasoning, retries and caching [T§5.1; SCR]:
  - **DeepSeek V4.1 Flash** on Morph fp8 costs **$0.0157 (−47%)**.
  - gpt-oss-120b $0.0089, mistral-nemo $0.0044.
  - The same model's price varies 10.7× across 36 endpoints, and some endpoints ran at 33–52% uptime.
- **Reasoning tail risk:** at about 2,000 output tokens per call, Haiku costs about $0.13 and Sonnet about $2.60 (4.4×) [T§1].
  - Haiku defaults to thinking at medium effort.
  - Reasoning tokens are billed as output and count against `max_tokens`; if it is too small the call returns "length" with empty content [T§4].
- **Debrief:** one call per run, about $0.003 (Haiku) to $0.055 (Sonnet) [T§1].
- **Caching:** the Haiku minimum is 512 tokens, but OpenRouter lists 1,024–4,096 (conflict). The TTL is 5 minutes, so a player pausing longer forces a cache rewrite [T§1, §4].
- **No reliable time-to-first-token figure exists.**
  - "Haiku 5.5 (Max)" shows 234 t/s but a 348 s time-to-first-token, which is unusable; the tier median is 1.73 s [Td:llm-cost-r2-c #18].
  - Anecdote: gpt-4o-mini about 15 s per run, gpt-5-mini about 5 min (low confidence) [T§1].
  - The three AI roles order simultaneously, so calls run in parallel [T§1].
- **Recommendation: budget ≤ $0.10 per session and verify it with a prototype** [T Rec 2]. Issue #8.

## 3. LLM opponent quality
The source is arXiv 2605.17036 (preprint; 8 models; human benchmark of more than 100 Georgia Tech students).
- **Invalid orders:** "Phi-4 and DeepSeek-R1-0528 violated basic ordering rules in more than 25% of cases" (no per-model table) [T§1]. **No rate exists for current small or cheap models** [T§5.1].
- **Default run-to-run CV of total cost:** GPT-5 mini 45%, Llama 4 Maverick 52%, Qwen-3 4B 26%. The paper's text says 26–45%; its table shows 52% [T§1].
- **With guardrails:**
  - A spend cap at 2× customer demand cut Qwen's **CV from 26% to 12%** and max cost 45%.
  - A budget rule cut mean cost 3–41% across models.
  - Post-training gave **CV 13%** [Td:llm-cost-r1-a #6].
  - These figures come from **one model**.
- **Voting:** majority voting (10/100 votes) "did NOT meaningfully cut variability" (X: competitive `llm-r2-i.md`).
- **LLM opponents outperform humans:** costs up to 80% below student teams (50–80% for reasoning models). The "agent bullwhip" grows upstream, even with fixed demand (X: `verify-r3-o`).
- **Prompt and information changes moved cost 33–69% on weaker models and hurt advanced ones**, so the prompt version matters (X: `llm-r2-i`).
- **Human-likeness was not measured.** LLMs reproduce bias directions, not human distributions (2510.03310) [L§4; X]. T: whether realism "is needed" was not established.
- **Student-perceived credibility: no evidence** (Issues #9, #11).

## 4. Reproducibility
- **No vendor guarantees determinism** [T§3]:
  - **Anthropic:** `temperature`, `top_p` and `top_k` are unsupported on Claude 4.7+. Non-default values return HTTP 400, and from API version 2026-10-21 any value does (verified). No `seed` was found.
  - **Haiku 5.5's ZDR endpoints** offer neither seed nor temperature, so it fails the gate [T§5.1].
  - **DeepSeek V4.1 Flash** supports both.
  - **OpenAI:** seed is "best effort".
  - **OpenRouter:** unsupported parameters are silently ignored. Requests may fall back to another provider, quantisation or model [T§4].
  - **Cause:** server batching. Deterministic inference costs 26 s → 42–55 s [Td:nonllm-arch-r2-d #11].
- **What the research recommends:**
  - Promise no bit-exact LLM results. Identical cohort results need seeded rule agents or record-replay [T Rec 3].
  - Log endpoint, model slug, provider, quantisation, seed, prompt version and `usage.cost` per decision.
  - Pin an exact slug (aliases lag on price) [T Rec 7].
  - Pin each session to one endpoint; mark outage fallbacks as "mixed". Offer a freeze mode. Replays never call a model [T§5.2].

## 5. Guardrails and architecture
Tags: **[PRD]** = observable behaviour, **[ARCH]** = how it is built.
- **[PRD]** Every AI order is validated against the game rules before it takes effect; an invalid order is replaced by a default order [T Rec 5, high].
  - **[ARCH]** Valid JSON is not guaranteed on refusal or truncation, and schemas cannot carry numeric bounds, so "order ≥ 0" is checked in code [Td:llm-cost-r2-c #8].
- **[PRD]** LLM opponents run with order bounds: a budget rule and a spend cap at 2× customer demand [Td:llm-cost-r1-a #6].
- **[PRD]** Lecturers choose LLM or rule-based opponents per class and can freeze the model; the study model is frozen [T Rec 12].
- **[PRD]** Spend guards: a per-session cap, a daily budget alert and a key limit. Privacy: `deny` plus ZDR, a DPA, and the Business plan if EU routing is needed [T§5.2, Rec 8].
- **[ARCH]** Opponents use one policy interface with a decision log. Reasoning is none and the seed comes from the game seed. RL comes later [T Rec 1, 6].
- **[ARCH] Timeouts are unspecified.** The nearest figure is the p95 ≤ 8 s gate [MS].
- **[ARCH] Model switcher; all thresholds are placeholders** [T§5.2; MS]:
  - *Screen:* ZDR + seed + temperature + structured output + 99% uptime.
  - *Evaluation:* 30 golden games × 108 decisions.
  - *Metric:* cost per valid task.
  - *Gates:* invalid Wilson-95% upper bound ≤ 2%, behaviour inside the fidelity band, p95 ≤ 8 s.
  - *Switch:* at least 15% cheaper, 7-day cooldown.
  - *Canary:* 5% of sessions; roll back at an upper bound above 4% or errors above 5%.
  - *Payoff:* above about 260 sessions/week.
  - *My arithmetic:* passing needs an observed invalid rate of about 1.5% or less.

## 6. Learning evidence
- **The core claim is "an untested hypothesis"** [L Exec].
- **Repetition raises cost performance, not demonstrated understanding.**
  - Jeong & Hong 2011: abstract only.
  - Fu & Gonzalez 2006 and Martin 2004: snippets only, from one lab.
  - Whether demand stayed fixed across repeats is unknown [L§2].
- **Counter-evidence:**
  - Paich & Sterman (1993): average performance improved, but "experience does not appear to mitigate the misperceptions of feedback."
  - Atkins (2002): performance and learning dissociate [L§2].
- **Meta-analyses:** Sitzmann found declarative +11% and retention +9%. Wouters found d = 0.29, larger with multiple sessions. Neither crosses repetition with debrief [L§2].
- **Debrief:**
  - Cheng (2014): simulation plus debrief beats nothing, but the debrief is not isolated.
  - Lacruz (n = 112, self-report): d = 0.45.
  - Cognitive feedback beat outcome feedback [L§3].
  - Human-vs-human debrief RCTs found no difference [Ld:verification-lit B7].
- **AI evidence:**
  - Scoping review (7 studies): evidence "limited, exploratory, and largely single-institutional" [L§4].
  - Chatbot-vs-lecturer debrief RCT (n = 45): no difference [Ld:verification-lit B7].
  - An AI tutor RCT found 0.63–1.3 SD, but tested a tutor, not a debrief.
  - Unrestricted GPT-4 lowered later grades about 17%; a correction exists and was not read.
  - **No evidence exists on how accurately an LLM explains game logs** [L§4].
- **No transfer study exists.** Board players beat players of a screen version (low confidence) [L§2].
- **Instruments:**
  - Sweeney & Sterman (2000) bathtub inventory (square-wave and sawtooth flows; poor scores replicated) [Ld:beergame-learning-r2-c F6].
  - Cronin et al. (2009) stock-flow tasks.
  - The scored explanation and transfer tasks are proposals [L Rec 2].
- **Recommended design** [L Rec 2; Issue #6]:
  - Three arms: (A) one session plus human debrief, (B) replay only, (C) replay plus AI debrief.
  - Measure pre/post stock-flow understanding, explanation and transfer to unseen demand.
  - Vary demand per replay and freeze the model.
- **What one course can do (my inference):** randomise B vs C within the course, use an earlier cohort as A, or run a crossover. The result is pilot evidence, not proof.

## 7. What a good debrief contains
- **Explain cause and structure, not just numbers** [L Rec 3; inference].
- **Compute numbers in code and let the LLM only narrate.** The student writes their own explanation first [L Rec 4]. Keep humans in the loop [L§4].
- **Target the known misperceptions:** ignoring the supply line, blaming outside events, and missing the effects of one's own orders [Ld:debrief-ai-r1-b #10]. Improvement comes from better use of information and planning [Ld:beergame-learning-r3-e F2].
- **Classic facilitator moves** (X: `teaching-notes-r1-b` #3, #10):
  - Ask non-retailers "what do you think the customers were doing?"
  - Reveal the step.
  - Make the point that "same structure, qualitatively similar results."
- **Video adds nothing; short and long debriefs do similarly** [Ld:debrief-ai-r3-f 5a].
- **Afterwards, students should be able to explain** (inference) how their orders, delays and the supply line produced amplification.

## 8. Post-debrief test as learning instrument
- **Measure understanding separately from game cost,** because the two dissociate [L§2].
- **Items:**
  - pre/post bathtub items;
  - a scored causal explanation of the student's own outcome (no rubric is published);
  - an unseen-demand transfer task [L Rec 2].
- **Conditions:** no AI access during the test. Store the pre-debrief explanation. Use the same items in every arm.
- **The research is silent on A–F vs pass/fail.** If arms differ and the test is graded, fairness is at risk (inference).

## 9. Success-metric candidates and counter-metrics
| Metric | Threshold | Basis |
|---|---|---|
| Cost per session | ≤ $0.10 incl. fee | T Rec 2, modelled |
| Invalid AI orders | Wilson-95% UB ≤ 2% | MS placeholder |
| Run-to-run CV | about 12–13% with bounds (26–52% default) | 2605.17036, one model |
| p95 latency / uptime | ≤ 8 s / ≥ 99% | MS placeholder |
| Bullwhip and cost spread | inside a calibrated band | T Rec 13, no published band |
| Model switches during a study | 0 | T§5.2 |
| Learning gain by arm | none published | reference effects: d = 0.29–0.45 |
| Opponent credibility | none | Issue #11 |

**Counter-metrics:** cost falls without an understanding gain; later unaided decline (over-reliance); debrief statements that contradict the decision log; reasoning-token and retry cost; "too-good" opponents that produce no bullwhip; gains on identical demand that do not transfer.

## 10. Open questions
- **#8:** real tokens, reasoning overhead, time-to-first-token and invalid rate of small models; Sterman's fitted parameters; Anthropic `seed`; rules of existing bots.
- **#9 / #10:** cheap-model quality, the fidelity band, the MS thresholds, and how OpenRouter handles `seed` for Claude.
- **#11:** human-likeness and credibility are measured nowhere; the 12–13% CV comes from one model.
- **#6:** no study crosses debrief with repetition or tests transfer. **#5:** library copies of the key papers. **#7:** lecturer needs.
- **No issue yet:** the Bastani correction, LLM accuracy on game logs, the board-vs-screen effect, OpenRouter SLA, DPA and EU residency, and weekly price drift.
- **Staleness:** re-check pricing and API behaviour by 2026-11-01 and run the switcher screen weekly [T Staleness map].
