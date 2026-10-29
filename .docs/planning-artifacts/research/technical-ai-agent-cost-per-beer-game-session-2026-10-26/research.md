---
title: 'technical research: AI agent cost per beer game session (LLM vs RL vs rule-based)'
type: 'technical'
topic: 'AI agent cost per beer game session (LLM vs RL vs rule-based)'
decision: 'Are AI agents in solo replay economically viable vs student price, and which agent architecture should the architecture assume'
source: 'native run (web fan-out)'
status: complete
preset: 'deep'
validation: 'normal'
created: '2026-10-26'
updated: '2026-10-29'
claims_verified: 5
claims_unverified: 12
---

# technical research: AI agent cost per beer game session (LLM vs RL vs rule-based)

**Decision this research serves:** Are AI agents in solo replay economically viable vs student price, and which agent architecture should the architecture assume

## Executive summary

**Answer.** Cost does not block LLM agents for turn play. At small-model list prices a 36-turn session with three AI roles comes to roughly 2–9 US cents on plain JSON-order output, about 3 cents for Claude Haiku 5.5 [1][2][9][10]. That figure is **our arithmetic on assumed token counts**; no paper or vendor publishes tokens or dollars per beer-game session (§1). The real cost risks are different: reasoning-length output (4–5x or more), run-to-run instability of LLM agents, and the absence of any vendor guarantee of reproducible output. The architecture should therefore treat the agent as a replaceable policy behind one interface, and record every agent decision, rather than commit to one agent type.

**Three findings that drive this**
1. *Cost is dominated by output tokens, not by the number of replays.* Small tiers cost cents per session on plain JSON output. Mid tiers (Sonnet 5.5) cost about 35–60 cents, and an agent that emits ~2,000 output tokens per call (reasoning billed as output) costs ~4–5x more (§1). Haiku 5.5 defaults to adaptive thinking at medium effort, so this must be actively controlled [6].
2. *No vendor documentation reviewed guarantees deterministic LLM output* [7][19][20]; independent analysis attributes nondeterminism to server-side batching [21]. On current Claude models the sampling controls are not settable at all: Anthropic's Messages guide says temperature, top_p and top_k are unsupported on Claude 4.7 and later and return a 400 error when set to a non-default value (any value from API version 2026-10-21) [8]; no seed parameter was found (absence in parameter lists only). Exact replay of an LLM agent's behaviour is therefore only achievable by recording its decisions, or by using non-LLM agents with an explicit RNG seed (§3).
3. *RL agents are cost-minimisers, not human-like*, and are expensive to train; the only beer-game RL paper read in this run (others exist but were not read) trains one agent against non-RL co-players [18]. A published human-like heuristic exists (Sterman 1989), but its fitted parameters were **not retrieved** from any reliable source (§2).

**Biggest caveat.** The per-session costs are modelled, not measured. A short prototype that logs real token counts, and a measured invalid-order rate for the chosen model, would replace the main assumption in one afternoon.

**Provider note: OpenRouter (added 2026-10-26, §4).** OpenRouter bills model tokens at the provider's list price and charges a 5.5% fee when credits are bought (8% on the Business plan) [27], so the modelled Haiku 5.5 cost rises from about 3.0 to about 3.1 cents per session. It does not change the conclusion that cost is not the blocker, but it adds four things the architecture must handle: unsupported parameters are silently dropped unless `require_parameters` is set [36][29]; requests are load-balanced across providers and can fall back to other providers or models unless pinned [29][37]; default routing allows providers to retain and train on data, so student data needs `data_collection: deny` and/or ZDR [29][35]; and EU in-region routing requires the Business plan [27][39].

**Cheaper models and a weekly switcher (added 2026-10-29, §5).** On OpenRouter's live ZDR endpoint list, DeepSeek V4.1 Flash costs an estimated $0.0157 to $0.0178 per session (about 40–47% below Haiku 5.5's $0.0297) and, unlike Haiku 5.5, supports `seed` and `temperature`; gpt-oss-20b and mistral-nemo are 80–85% cheaper still, but no source shows how well any of them plays the game. Price for the same model varies 10x between providers, so the switcher must choose an endpoint (model + provider + quantisation), gate it on measured quality, and rank by **cost per valid task**, not list price. A reference implementation of the screen and decision logic is in `model-switcher/model_switcher.py`; it pays off only above roughly 260 sessions per week, and the learning study needs a frozen model.

## 1. Cost of LLM agents

**Published figures: none.** No source states tokens per decision, calls, dollars or latency for a beer-game session. The main beer-game LLM paper (4 agents, 25 weeks, 30 runs per configuration, eight models from GPT-4o mini to Llama 4 Maverick) reports none of them; its "cost" is supply-chain game cost, not API cost [13]. InvAgent (12 periods) reports no token or cost data in its text [15], and the abstract of an SCM-LLM paper has none either (its full text was not read) [16]. *Confidence: high for InvAgent; medium for 2605.17036, whose full text was only partly read; low for the SCM-LLM paper.*

**List prices (USD per million tokens).** Claude Haiku 5.5: $0.10 input, $0.50 output (prompts up to 100k tokens), cache hit $0.01, 5-minute cache write $0.125 [1][2]. Claude Sonnet 5.5: $2 in, $10 out [1]. Gemini 2.5 Flash-Lite $0.10 / $0.40; Gemini 3.1 Flash-Lite $0.25 / $1.50 [9]. OpenAI gpt-5-nano $0.05 / $0.40; gpt-5-mini $0.25 / $2.00 [10]. DeepSeek and Together publish comparable low prices [11][12]. Batch is 50% off but asynchronous, so unusable for per-turn play; it fits only offline generation such as debriefs [1][5]. Anthropic and OpenAI pages carry no date; only Google's page states one (2026-10-26) [9]. Gemini 3.6/3.8 Flash prices double on 2027-01-01 [9], an example of price movement the business case should tolerate. *Confidence: medium (primary sources, undated).*

**Modelled cost per session.** Assumptions are ours and unverified: 3 AI roles × 36 turns = 108 calls; 2,000 input tokens per call (1,200 cacheable prefix); 150 output tokens (JSON order plus one line, no hidden reasoning); real-time calls, no batch.

| Model | No cache | With cache (optimistic) |
|---|---|---|
| gpt-5-nano [10] | $0.017 | $0.012 |
| Gemini 2.5 Flash-Lite [9] | $0.028 | $0.016 |
| Claude Haiku 5.5 [1] | $0.030 | $0.018 |
| gpt-5-mini [10] | $0.086 | $0.057 |
| Claude Sonnet 5.5 [1] | $0.59 | $0.35 |

Token counts are vendor-neutral assumptions; Claude's newer tokenizer may produce up to ~30% more tokens for the same text (Anthropic glossary [7]), and the cache-write premium is ignored. The cached column assumes the same role's prefix is hit again inside the 5-minute default lifetime [2]; a human who pauses longer forces a rewrite (1-hour TTL costs 2x base input). Prompts under 512 tokens (Haiku 5.5) cannot be cached [2]. If each call emits ~2,000 output tokens, Haiku 5.5 is about $0.13 and Sonnet 5.5 about $2.60 per session. The output-token term dominates once reasoning is on. A debrief is one call per run, not per turn: with an assumed 20k input and 1.5k output tokens it is about $0.003 on Haiku 5.5 or $0.055 on Sonnet 5.5 (our arithmetic, same prices). *Confidence: medium on prices, low-to-medium on totals until tokens are measured.*

**Cost control that the docs support.** Haiku 5.5 uses adaptive thinking only and defaults to medium effort; at lower effort it may skip thinking [6]. Structured outputs guarantee schema-valid JSON, except on refusal or `max_tokens` truncation, and the raw API rejects numeric min/max constraints, so "order ≥ 0" must be validated in application code [3]. Rate limits are not a constraint at classroom scale (Start tier, Haiku 5.5: 1,000 requests/min, 2M input tokens/min) [4]; Gemini lists a free tier for its Flash-Lite models with limits not retrieved [9].

**Reliability.** In the 25-week beer-game study the authors report that, in their trials, Phi-4 and DeepSeek-R1-0528 violated basic ordering rules in more than 25% of cases (Sec. 3.1; no per-model table retrieved); total cost varied strongly between identical runs (coefficient of variation 26–52% across three tabulated models; the paper's text states 26–45% while its table shows 52% for Llama 4 Maverick); simple code-side guardrails (budget cap, expenditure cap at twice customer demand) cut mean cost and tail cost (preprint) [13]. No invalid-order rate was found for current small models. A forum anecdote puts gpt-4o-mini at ~15 s per game run versus ~5 minutes for gpt-5-mini [14]; *low confidence*. The Artificial Analysis "Haiku 5.5 (Max)" row shows 234 tokens/s but a 348 s time-to-first-token that is incompatible with a non-reasoning call (it is the max-effort variant); treat it as unusable [17]. Three AI roles decide simultaneously in the standard game, so they can be called in parallel and a turn costs about one call of wall-clock (our inference).

## 2. Cost and realism of non-LLM agents

**RL.** The beer-game RL agent read in this run, a Deep Q-Network (Oroojlooyjadid et al.), appeared as an arXiv preprint and was published in Manufacturing & Service Operations Management 24(1), 2022 (figures below were read from the arXiv v4 text and not re-checked against the journal version) [18]. Other RL and agent-based beer-game papers exist but were not read. It plays one role at a time against non-RL co-players (base-stock, Sterman-formula, random); multi-RL training is left to future work. It is a cost-minimiser, not a model of human behaviour: with Sterman-formula co-players it beats an optimised base-stock policy by 23% on average (Sec. 4.2), and the paper claims near-optimality only against base-stock co-players. Training is heavy: hyper-parameter tuning took 28,390,987 seconds in total across 140 instances (hardware unstated; ~329 CPU/GPU-days summed), with transfer learning ~17.6x faster. After training the authors say it "executes nearly instantaneously" and the network is a small MLP, so browser or tiny-server inference is plausible; **no measured latency or browser benchmark was found** [18]. No behavioural-cloning or human-like RL agent for the beer game was found. *Confidence: high on the paper's figures, low on browser feasibility.*

**Rule-based (Sterman 1989).** Sterman's anchoring-and-adjustment rule (smoothed demand forecast, stock-adjustment fraction, supply-line weight, desired inventory) is the standard model of human ordering and is already used as the human-like co-player in the RL paper [18][24]. The fitted values were **not obtained from a primary or reliable secondary source**: the MIT DSpace working paper returned HTTP 429, the SD Society PDF was unreadable, and the only numbers seen (stock-adjustment ~0.3, supply-line weight near zero) come from a calculator website and should not be used [23]. Marginal cost of such agents is effectively zero and they are reproducible by construction when seeded (design reasoning, §3). How closely the heuristic reproduces human bullwhip, and the computer-player behaviour of existing products, were not evidenced in this run.

## 3. Architecture patterns for cost and reproducibility

**No vendor guarantees determinism.** Anthropic's glossary: "Even with temperature set to 0, the results will not be fully deterministic" [7]. OpenAI's cookbook: seeded requests are a "best effort" to be deterministic and "Determinism is not guaranteed" (archived, undated page) [20]; its current guide says determinism may be impacted by changes OpenAI makes to model configurations [19]. Thinking Machines Lab attributes inference nondeterminism mainly to varying server batch size and shows a deterministic setup is possible at a speed cost (company blog, not peer-reviewed) [21]. A preprint finds output varies even under "deterministic" settings (accuracy varying up to 15% across runs on tasks) [22]. Anthropic's Messages guide states that `temperature`, `top_p` and `top_k` "are not supported on Claude 4.7 and later models ... Setting them to a non-default value returns a 400 error, and starting with `2026-10-21` any value does" [8]. Parameter lists of the Messages API reference show no `seed` (three reads, two of them partial), but no explicit statement about seed was found. *Status: temperature removal verified from the official guide; seed support unconfirmed; the non-guarantee of determinism is well supported, and on current Claude models temperature 0 is not even available.*

**Pattern that follows (our reasoning, not sourced).** (a) Put each agent behind a policy interface so rule-based, RL and LLM agents are interchangeable per role and difficulty. (b) Persist every agent decision per turn: this gives exact replay, a debrief data source and cost telemetry at once. (c) Use seeded heuristic agents wherever bit-exact reproducibility matters. (d) Validate every LLM output against game rules in code and fall back to a default order. (e) Use LLMs where text is the product (debrief, per-run), not for every move, unless behavioural realism of LLM turn play is itself the value. Related patterns on invalid actions (validate then default or retry) are reported qualitatively in abstracts and an answer-engine summary; the underlying papers were not read [25].

## 4. OpenRouter as the AI provider (deepening, 2026-10-26)

Scope: whether routing all model calls through OpenRouter changes the cost, reproducibility, reliability or privacy conclusions above. Sources are OpenRouter's own documentation, read through page summaries; only the privacy policy shows a date (last updated 2026-08-31) [34]. Single-publisher, primary sources, so confidence is medium; no independent third-party report was found.

**Cost.** "Inference is billed at each provider's list price on every plan"; the platform fee applies only when credits are bought: Standard 5.5%, Business 8%, Enterprise by contract, and an errored fallback attempt is not charged for model tokens [27]. Bring-your-own-key use is free of OpenRouter fees up to $25,000 of list-price inference per month on Standard and Business, then 5% [27]. Our modelled Haiku 5.5 session of $0.030 becomes about $0.031 (Standard) and Sonnet 5.5 $0.59 about $0.63 (our arithmetic). The Haiku 5.5 model page shows EU in-region prices of $0.11 input and $0.55 output per million tokens via Google Vertex and Amazon Bedrock, available only on Business or Enterprise via `eu.openrouter.ai` [39]; our arithmetic puts a session at about $0.035 including the 8% fee. A search summary of OpenRouter pages gives the standard Haiku 5.5 price as $0.10 / $0.50 with cache read $0.01, matching Anthropic's list price [39][1] (search summary only), and shows a "Claude Haiku Latest" alias page still priced at $1 / $5, so a pinned model slug should be used instead of an alias [39]. Free models are capped at 20 requests per minute and 50 per day (1,000 per day after buying at least $10 of credits), which rules them out for classroom use [27][31]. Per-response `usage.cost` and native-tokenizer token counts are returned, which supplies the cost telemetry recommended for the prototype [36].

**Reasoning and thinking.** Reasoning is controlled with `reasoning.effort` (including "none") or Anthropic's `thinking: {type: "disabled"}`; reasoning tokens are billed as output even when excluded and count against `max_tokens`, so too small a `max_tokens` can end with `finish_reason: "length"` and empty content [38]. This confirms the report's cost warning and makes "reasoning off for turn play" an explicit request setting.

**Reproducibility.** OpenRouter exposes `seed` and `temperature`, saying seeded requests "sample deterministically" while "Determinism is not guaranteed for some models", and that at temperature 0 "the model always gives the same response for a given input" [28]. That second sentence is stronger than what the underlying vendors say [7][20] and should not be relied on. Three OpenRouter behaviours make exact replay harder still: parameters a model does not support are "ignored" rather than rejected [36] (whether OpenRouter drops or forwards `temperature` for Claude 4.7+ models, which Anthropic rejects [8], was not found); requests are load-balanced across providers by default and fall back to other providers on errors, with quantised variants possible [29]; and a `models` fallback array or the Auto Router can change which model answers, reported only in the response `model` field [37][40]. The routing page contains no discussion of reproducibility across providers [29]. The conclusion stands and sharpens: record each decision together with the answering model and provider, and pin routing (`provider.only` or `order` with `allow_fallbacks: false`) when comparable behaviour matters.

**Structured output and caching.** `response_format` with a JSON schema works per endpoint, strict enforcement depends on the provider, and `require_parameters: true` routes only to endpoints that support the request; a Response Healing plugin exists for non-streaming calls [32]. Anthropic prompt caching requires `cache_control`, with 1.25x/2x write and 0.1x read prices, and OpenRouter keeps cached requests on the same provider for about 10 minutes of inactivity [30]. OpenRouter lists a 1,024 to 4,096 token minimum for Anthropic models, which conflicts with Anthropic's own 512 tokens for Haiku 5.5 [30][2]; test with real prompts. Schema validity still does not enforce game rules [3], so order validation stays in application code.

**Reliability and limits.** Paid models have "no platform-level request cap", but provider limits apply and a 429 may come from either side; low or negative credit balances cause errors and prepaid accounts below an unspecified balance get an in-flight spending budget, so auto top-up should be on [31]. Failover to other providers happens on 5xx responses [36]. Latency overhead, uptime figures and SLA terms were not found in the documentation read; contractual SLAs are listed only for Enterprise [27][36].

**Privacy.** OpenRouter states it does not store prompts or responses unless the account opts in, and that request metadata (token counts, latency) is kept [33]. The privacy policy does not use the terms controller or processor, says OpenRouter does not control how model providers handle inputs, says providers may retain and use inputs for their own purposes, allows transfers outside the EEA and UK under standard contractual clauses, and mentions a Data Processing Agreement for some users [34]. Routing defaults to `data_collection: "allow"`, which permits providers that store data and may train on it; `data_collection: "deny"` and ZDR (`zdr: true`, or account-wide toggles) restrict routing, remove first-party Anthropic, OpenAI and AI Studio endpoints while leaving Bedrock, Azure and Vertex, and can reduce the endpoints available [29][35]. Because the product holds student accounts and play history, an institutional buyer will ask for this; the safe defaults are `deny` plus ZDR and a DPA, to be confirmed with OpenRouter.

**Does it change any conclusion?** No. Cost is slightly higher (fee), the reproducibility and privacy findings get stricter, and the recommendations below add routing settings. *Confidence: medium on all of the above; documentation-only evidence.*

## 5. Cheaper models and a weekly model switcher (deepening, 2026-10-29)

Scope: the team will use models cheaper than Haiku (DeepSeek and similar) and wants logic that switches model, for example weekly, to the one with the lowest cost per task. Evidence: OpenRouter's public model and Zero-Data-Retention endpoint lists, pulled on 2026-10-29 and screened with the reference program in `model-switcher/model_switcher.py` (output in `model-switcher/screen-2026-10-29.json`, digest `digests/openrouter-switcher-r5-b.md`) [41][42]. Costs are list price times our assumed 216,000 input and 16,200 output tokens per session; they exclude reasoning overhead, retries, caching and the credit fee. The data is a live snapshot and changes daily.

### 5.1 What the snapshot shows

- **Haiku 5.5 fails the reproducibility gate.** None of its six ZDR endpoints (Google Vertex, Amazon Bedrock) lists `seed` or `temperature` as supported; the estimate is $0.0297 per session [41][42]. This matches Anthropic's removal of sampling parameters [8].
- **Many endpoints pass a gate of ZDR, `seed`, `temperature`, `structured_outputs`, uptime ≥ 99% and context ≥ 32k.** Of 1,086 ZDR endpoints, 291 pass; most rejections are a missing required parameter (476) or not being a text model (137) [42].
- **DeepSeek V4.1 Flash** supports seed, temperature, structured outputs and reasoning; its cheapest ZDR endpoints are Morph fp8 at $0.0157 per session (−47% against Haiku 5.5) and Wafer mxfp4 at $0.0178 (−40%). DeepSeek's own first-party API does not appear in the ZDR list [42].
- **The endpoint matters more than the model.** The same DeepSeek V4.1 Flash costs from $0.0157 to $0.1685 per session across 36 ZDR endpoints (10.7x), and some endpoints had 33% to 52% uptime over 24 hours [42]. The unit the switcher must choose is therefore *model + provider + quantisation*, not the model name.
- **Cheaper again, with unknown quality:** mistral-nemo $0.0044, gpt-oss-20b $0.0059, gpt-oss-120b $0.0089, glm-5.3-flash $0.0114 (−85% to −62%). Reasoning-capable models bill reasoning tokens as output [38], so their real cost per task can be several times the estimate until measured.
- **No source gives beer-game decision quality for any of these models.** The closest evidence is the preprint in which weaker models broke ordering rules in more than 25% of cases and varied strongly between runs [13]. Cheapest per token is therefore not cheapest per task: invalid decisions, retries and reasoning tokens must be counted.

*Confidence: high that the snapshot is accurate on its date; low on whether any cheap model plays well enough; the design below is our reasoning.*

### 5.2 Switcher logic (reference implementation: `model-switcher/model_switcher.py`)

The unit of work is a *task* = one agent decision (an order), with debriefs handled in a separate pool because they need a stronger model. The switcher keeps one **champion** endpoint per pool and re-decides weekly in four stages.

1. **Screen (free, automatic).** Pull `/models` and `/endpoints/zdr`. Keep endpoints that are paid, text-output, status OK, ZDR, support `seed`, `temperature` and `structured_outputs`, with uptime and context above the gates. Rank by estimated cost and take the cheapest K (for example 6) per pool, plus the incumbent. Implemented as `model_switcher.py screen`.
2. **Shadow evaluation (cheap, automatic).** Play seeded golden games (for example 30 games × 108 decisions = 3,240 decisions per candidate) against the real game engine, with the same prompts, reasoning off, pinned provider and `require_parameters`. Record per candidate: attempted and valid decisions, total `usage.cost` including retries and reasoning tokens [36], p95 latency, uptime and a fidelity verdict (bullwhip amplification and total-cost spread inside a band calibrated against the Sterman-heuristic baseline and human data; band to be set by the team).
3. **Decide (pure function).** Metric: **cost per valid task = Σ usage.cost ÷ valid decisions**. An endpoint is eligible only if all gates pass: enough tasks measured, 95% upper bound of the invalid rate ≤ 2% (Wilson), fidelity inside the band, p95 latency ≤ 8 s, uptime ≥ 99%. Choose the cheapest eligible endpoint; switch only if it is at least 15% cheaper than the re-measured incumbent and the 7-day cooldown has passed; if the incumbent fails a gate, switch to the best eligible endpoint at once; if nothing passes, keep the incumbent and raise an alert. Implemented and tested as `model_switcher.py decide` and `selftest` (nine decision cases and four rollback cases pass). All thresholds are placeholders to calibrate.
4. **Canary and rollback.** Send about 5% of new sessions to the new champion for 24 to 48 hours; roll back automatically if the live invalid-rate upper bound exceeds twice the gate or the error rate exceeds 5%.

**Rules around the loop**
- **A session is pinned to one endpoint for its whole length.** The switcher never changes model mid-game; runtime fallbacks via the `models` array are for outages only, are logged, and mark the session as mixed [37].
- **Freeze mode.** A lecturer, a class or the learning study can freeze the model for a period; the switcher then only alerts if the frozen endpoint fails its gates. The founder's first-course study (measurement plan, Issue #6) must run on a frozen model, because changing the opponent's behaviour changes the learning outcome being measured.
- **Replays do not call a model.** Because every decision is recorded, replaying a run is unaffected by switching; only new games use the new champion.
- **Request settings per call:** pinned `provider.only` or `order` with `allow_fallbacks: false`, `require_parameters: true`, `data_collection: "deny"`, `zdr: true`, reasoning none, `max_tokens` above the visible output size, `seed` set from the game seed [29][35][36][38]. The cheapest-provider shortcut `:floor` or `sort: price` is the zero-effort alternative but can change provider and quantisation silently, so it fails the reproducibility rule.
- **Extra triggers beyond the weekly job:** the champion's price rises by more than 20%, its 24-hour uptime falls below the gate, or it disappears from `/models`.
- **Spend guards:** a per-session cost cap, a daily budget alert and an OpenRouter key limit [31].
- **Logging:** endpoint, model slug, provider, quantisation, seed, prompt version and `usage.cost` with every decision.

### 5.3 When is it worth automating?

With our assumptions the weekly shadow evaluation costs about $3.60 (6 candidates × 30 games × an assumed $0.02 per game). Moving from Haiku 5.5 to DeepSeek V4.1 Flash on Morph saves about $0.014 per session, so the evaluation pays for itself above roughly 260 sessions per week; switching between two cheap candidates that differ by $0.0098 per session needs about 370 sessions per week. Below that, a manually chosen and quality-checked model with the same guards is cheaper to run than the automation; the one-off decision to leave Haiku does not need a weekly job. The 15% hysteresis and cooldown exist because every switch changes how the AI opponents behave.

### 5.4 Limits of this section

No cheap model has been tested on the game, so the quality gate is a design, not a result. Estimated costs ignore reasoning tokens, retries and caching. Endpoint latency fields were empty, so only uptime is gated. Endpoint regions were not available, so EU residency is not guaranteed by ZDR alone (see §4). The `status` field is treated as healthy at 0, which is our assumption. No verifier subagent has reviewed this section.

## Cross-dimension insights

- The model switcher and the learning study pull against each other: a cost-optimal opponent that changes weekly is a confound for the measurement plan, so freeze mode is a requirement, not a nicety.
- Using OpenRouter widens the decision log: the answering model and provider are now variable and must be stored with every agent decision, alongside the seed and the prompt version.
- Cost and reproducibility pull in the same direction: recording decisions makes replay free and reproducible, and a heuristic or RL policy is both the cheapest and the only reproducible-by-construction option. LLM turn play is the most expensive, least reproducible and most realistic-in-style option; the research did not establish whether that realism is needed (see the learning-evidence and competitive research for that question).
- Because price per session is small compared with plausible student prices, the economic question moves from cost per session to cost *tail risk* (reasoning output, retries, failures) and price volatility, which guardrails and a model-agnostic interface address.

## Contrary evidence

No red-team pass ran (`red_team = off`). Counter-points inside the evidence: the published 80% game-cost advantage of LLM agents over student teams (preprint, best configuration) sits beside >25% rule violations for some models and 26–52% run-to-run variation [13]; "cheap" holds only for the small, non-reasoning configuration.

## Recommendations

1. **Architecture spine: model the agent layer as a policy interface with a decision log.** Binds to: architecture. Basis: vendor docs plus reasoning; medium confidence.
2. **Plan on a small-tier LLM with thinking off or low for turn play, and budget ≤ $0.10 per session; verify by prototype.** Binds to: architecture constraint, PRD cost guardrail. Basis: modelled costs resting on assumed tokens; low-to-medium confidence.
3. **Do not promise bit-exact reproducibility from LLM agents.** If the PRD requires identical results across a cohort, require seeded heuristic agents or record-replay. Binds to: PRD non-functional requirements. Basis: vendor docs (high on the non-guarantee).
4. **Generate debriefs per run, one call, optionally via batch when latency is not needed.** Binds to: PRD debrief feature. Basis: price arithmetic; medium.
5. **Add input validation of every agent order in application code** (schema validity is not game validity). Binds to: architecture. Basis: Anthropic docs [3] and failure report [13]; high.
6. **Treat RL as optional later work, not an MVP dependency.** Training cost is high, no multi-agent or human-like result exists, and no browser latency evidence was found. Basis: [18]; medium.
7. **OpenRouter configuration for turn play:** pin an exact model slug (no `-latest` alias), set `require_parameters: true`, `allow_fallbacks: false` and a pinned provider order when comparable behaviour matters, set reasoning to none, keep `max_tokens` above the visible output size, and store `model`, provider and `usage.cost` with every decision. Binds to: architecture spine. Basis: OpenRouter docs [29][36][37][38][39]; medium confidence.
8. **Privacy defaults for student data:** `data_collection: "deny"` and ZDR on all production requests; plan for the Business plan (8% fee) if EU in-region routing is required; request a Data Processing Agreement before the first institutional sale. Binds to: PRD non-functional requirements (privacy), institutional sales material. Basis: [29][34][35][27]; medium confidence, contract terms unverified.
9. **Budget the fee:** model cost per session as provider list price × 1.055 (Standard) or × 1.08 (Business). Binds to: PRD cost guardrail. Basis: [27]; medium.
10. **Replace Haiku 5.5 as the turn-play default with a cheaper endpoint that supports `seed`, `temperature` and structured outputs** (start the comparison with DeepSeek V4.1 Flash, gpt-oss-120b and one very small model as a floor), chosen by measured cost per valid task on golden games, not by list price. Binds to: architecture spine (agent policy interface). Basis: [41][42]; cost evidence high for the snapshot, quality evidence none (low confidence that any cheap model is good enough).
11. **Build the switcher as the four stages in §5.2 (screen, shadow evaluation, decide, canary/rollback), with sessions pinned to one endpoint, a freeze mode and a decision log.** Start with the screen and manual approval; automate the weekly decision once volume exceeds roughly 260 sessions per week. Binds to: architecture, PRD cost guardrail. Basis: reasoning from [41][42][36][37] plus the break-even arithmetic in §5.3; medium-low confidence (thresholds are placeholders).
12. **Freeze the model for the founder's learning study** and record it in the study protocol. Binds to: PRD measurement plan (Issue #6). Basis: reasoning; medium confidence.
13. **Calibrate the fidelity band before the first switch:** play the Sterman-heuristic baseline and a human reference on the golden games and set the allowed range for bullwhip amplification and total-cost spread. Binds to: architecture (evaluation harness), PRD agent requirements. Basis: no published band exists [13]; low confidence in any number chosen now.

## Open questions

- Real tokens per call, retries and thinking overhead: needs a prototype with logging.
- Invalid-order and rule-violation rate of current small models (Haiku 5.5, Flash-Lite, nano) in a beer game.
- Sterman (1989) fitted parameters from the primary paper (MIT DSpace working paper, Management Science 35(3):321–339 [24]); how closely the heuristic matches human bullwhip.
- Computer-player rules and difficulty levels in existing products.
- Latency of non-reasoning small-model calls (time-to-first-token) from a reliable benchmark.
- Current Anthropic temperature/seed behaviour: read the Messages guide directly.
- Browser inference latency for a small MLP.
- OpenRouter: latency overhead, uptime and SLA terms; which plan includes a Data Processing Agreement; whether OpenRouter drops or forwards `temperature`/`seed` for Claude 4.7+ models (test with `require_parameters` on and off); whether `seed` is honoured for the chosen model; the in-flight spending budget threshold for prepaid accounts; Haiku 5.5 non-EU prices read directly from the model page; independent third-party reports of OpenRouter reliability.
- Switcher: decision quality (invalid-order rate, bullwhip fidelity, spread) of DeepSeek V4.x, gpt-oss, Mistral, Gemma and GLM models on the game; real tokens including reasoning overhead per call; per-endpoint latency (fields were empty); endpoint regions for EU residency; behaviour of the `status` field; whether the cheapest endpoints keep their price and uptime for a week (the snapshot is one day).
- Whether the earlier competitive-research claim of $0.25–2.00 per session for a published study (SupplyNet) can be sourced; it did not surface here.

## Source appendix

| # | Claim / finding supported | Publisher | Pub date | Accessed | Confidence |
|---|---|---|---|---|---|
| 1 | Claude pricing: Haiku 5.5, Sonnet 5.5, batch | [Anthropic](https://platform.claude.com/docs/en/about-claude/pricing) | undated | 2026-10-26 | medium |
| 2 | Prompt caching: 512-token minimum, multipliers, 5-min TTL | [Anthropic](https://platform.claude.com/docs/en/build-with-claude/prompt-caching) | undated | 2026-10-26 | medium |
| 3 | Structured outputs guarantees and exceptions | [Anthropic](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) | undated | 2026-10-26 | medium |
| 4 | Rate limits (Start tier, Haiku 5.5) | [Anthropic](https://platform.claude.com/docs/en/api/rate-limits) | undated | 2026-10-26 | medium |
| 5 | Batch API 50% discount, asynchronous | [Anthropic](https://platform.claude.com/docs/en/build-with-claude/batch-processing) | undated | 2026-10-26 | medium |
| 6 | Adaptive thinking, medium effort default for Haiku 5.5 | [Anthropic](https://platform.claude.com/docs/en/build-with-claude/extended-thinking) | undated | 2026-10-26 | medium |
| 7 | Temperature 0 not fully deterministic | [Anthropic](https://platform.claude.com/docs/en/about-claude/glossary) | undated | 2026-10-26 | medium |
| 8 | Temperature/top_p/top_k unsupported on Claude 4.7+ (400 error); no seed parameter seen in parameter lists | [Anthropic](https://platform.claude.com/docs/en/build-with-claude/working-with-messages) | undated | 2026-10-26 | high (temperature), low (seed) |
| 9 | Gemini prices, batch, free tier, price rise 2027-01-01 | [Google](https://ai.google.dev/gemini-api/docs/pricing) | 2026-10-26 | 2026-10-26 | high |
| 10 | OpenAI small-model prices | [OpenAI](https://developers.openai.com/api/docs/pricing) | undated | 2026-10-26 | medium |
| 11 | DeepSeek prices | [DeepSeek](https://api-docs.deepseek.com/quick_start/pricing/) | undated | 2026-10-26 | medium |
| 12 | Together AI serverless prices | [Together AI](https://www.together.ai/pricing) | undated | 2026-10-26 | medium |
| 13 | LLM agents in beer game: setup, variance, >25% rule violations, guardrails (preprint) | [arXiv 2605.17036](https://arxiv.org/abs/2605.17036) | 2026-05-16 (v4 2026-09-21) | 2026-10-26 | medium |
| 14 | Latency anecdote, gpt-4o-mini vs gpt-5-mini | [INFORMS Open Forum](https://connect.informs.org/discussion/can-genai-agents-manage-a-supply-chain-lessons-from-the-classical-beer-game) | 2025-08-30 | 2026-10-26 | low |
| 15 | InvAgent: no token/cost data | [arXiv 2407.11384](https://arxiv.org/pdf/2407.11384) | not verified | 2026-10-26 | medium |
| 16 | SCM-LLM paper: abstract has no cost data | [arXiv 2505.18597](https://arxiv.org/abs/2505.18597) | 2025-05-24 | 2026-10-26 | medium |
| 17 | Haiku 5.5 speed 234 t/s; TTFT anomalous | [Artificial Analysis](https://artificialanalysis.ai/models/claude-haiku-5-5) | 2026-10 | 2026-10-26 | low |
| 18 | DQN for beer game: training cost, 23% vs base-stock, cost-minimiser not human-like (journal version: MSOM 24(1), 2022) | [arXiv 1708.05924](https://arxiv.org/abs/1708.05924v4) | 2020-10-14 (v4) | 2026-10-26 | high (figures from arXiv v4) |
| 19 | OpenAI reproducible outputs: not guaranteed | [OpenAI](https://developers.openai.com/api/docs/guides/advanced-usage) | undated | 2026-10-26 | medium |
| 20 | OpenAI cookbook: seed best effort (archived) | [OpenAI cookbook](https://developers.openai.com/cookbook/examples/reproducible_outputs_with_the_seed_parameter) | undated | 2026-10-26 | medium |
| 21 | Nondeterminism caused by batch-size variation | [Thinking Machines Lab](https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/) | 2025-09-10 | 2026-10-26 | high |
| 22 | LLM output variation under deterministic settings (preprint) | [arXiv 2408.04667](https://arxiv.org/abs/2408.04667) | 2025-04-02 (v5) | 2026-10-26 | high (abstract) |
| 23 | Unverified Sterman parameter values (do not use) | [MetricGate](https://metricgate.com/docs/beer-game-bullwhip-simulation/) | 2026-05-27 | 2026-10-26 | low |
| 24 | Sterman (1989) bibliographic record | [IDEAS/RePEc](https://ideas.repec.org/a/inm/ormnsc/v35y1989i3p321-339.html) | 1989 | 2026-10-26 | medium |
| 25 | Qualitative invalid-action patterns in LLM game agents (abstracts only) | [arXiv 2512.11421, 2605.29512](https://arxiv.org/abs/2512.11421) | 2025-12 to 2026-05 | 2026-10-26 | low |
| 27 | OpenRouter billing: list-price pass-through, 5.5%/8% credit fee, BYOK, free-tier caps, plans, EU routing on Business | [OpenRouter](https://openrouter.ai/pricing) | undated | 2026-10-26 | medium |
| 28 | OpenRouter parameters incl. seed and temperature wording | [OpenRouter](https://openrouter.ai/docs/api-reference/parameters) | undated | 2026-10-26 | medium |
| 29 | Provider routing: load balancing, fallbacks, require_parameters, data_collection, zdr | [OpenRouter](https://openrouter.ai/docs/features/provider-routing) | undated | 2026-10-26 | medium |
| 30 | Prompt caching on OpenRouter, stickiness | [OpenRouter](https://openrouter.ai/docs/features/prompt-caching) | undated | 2026-10-26 | medium |
| 31 | Rate limits, free models, credit-dependent limits, 429 handling | [OpenRouter](https://openrouter.ai/docs/api-reference/limits) | undated | 2026-10-26 | medium |
| 32 | Structured outputs, per-endpoint support, response healing | [OpenRouter](https://openrouter.ai/docs/features/structured-outputs) | undated | 2026-10-26 | medium |
| 33 | Prompt/response storage defaults, opt-in, metadata | [OpenRouter](https://openrouter.ai/docs/guides/privacy/data-collection) | undated | 2026-10-26 | medium |
| 34 | Privacy policy: providers, transfers outside EEA, DPA mention | [OpenRouter, Inc.](https://openrouter.ai/privacy) | 2026-08-31 | 2026-10-26 | medium-high |
| 35 | Zero Data Retention routing and its effect on endpoints | [OpenRouter](https://openrouter.ai/docs/guides/features/zdr) | undated | 2026-10-26 | medium |
| 36 | API overview: unsupported parameters ignored, usage and cost fields, 5xx failover | [OpenRouter](https://openrouter.ai/docs/api-reference/overview) | undated | 2026-10-26 | medium |
| 37 | Model fallbacks array: triggers, billing, `model` field | [OpenRouter](https://openrouter.ai/docs/guides/routing/model-fallbacks) | undated | 2026-10-26 | medium |
| 38 | Reasoning controls and billing | [OpenRouter](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens) | undated | 2026-10-26 | medium |
| 39 | Claude Haiku 5.5 on OpenRouter: EU prices (page); standard prices and alias lag (search summary) | [OpenRouter](https://openrouter.ai/anthropic/claude-haiku-5.5) | undated | 2026-10-26 | medium (EU), low-medium (rest) |
| 40 | Auto Router can change the answering model between turns | [OpenRouter](https://openrouter.ai/docs/features/model-routing) | undated | 2026-10-26 | medium |
| 41 | Model catalogue: prices, supported parameters (Haiku 5.5 seed/temperature false; DeepSeek V4.1 Flash true) | [OpenRouter models API](https://openrouter.ai/api/v1/models) | live, 2026-10-29 | 2026-10-29 | high (snapshot) |
| 42 | ZDR endpoint list: per-endpoint prices, quantisation, uptime, supported parameters | [OpenRouter ZDR endpoints API](https://openrouter.ai/api/v1/endpoints/zdr) | live, 2026-10-29 | 2026-10-29 | high (snapshot) |

## Staleness map

Computed with `recon_kit.py staleness` on 2026-10-26 (windows: pricing and version 1 month, AI-adjacent performance numbers 3 months, patterns 24 months).

| Claim | Class | Re-check by |
|---|---|---|
| Haiku 5.5 list price [1] and modelled cost per session | pricing | 2026-11-01 |
| Haiku 5.5 512-token cache minimum [2]; temperature/top_p/top_k unsupported [8] | version | 2026-11-01 |
| OpenRouter fees, plans, limits, routing and privacy terms [27]–[40] | pricing | 2026-11-26 (privacy policy dated 2026-08-31) |
| Endpoint prices, uptime and supported parameters used for the switcher snapshot [41][42] | pricing | 2026-11-05 (re-run `model_switcher.py screen` weekly; prices and uptime change daily) |
| LLM-agent rule violations and variance [13] | performance-number | 2026-12-01 |
| DQN results [18] | pattern | stale since 2022-10 (seminal-style result; recheck for newer RL work) |

**Earliest re-check: 2026-11-01** (all pricing and API-behaviour claims; prices have moved before, e.g. the Gemini 2027-01-01 doubling).
