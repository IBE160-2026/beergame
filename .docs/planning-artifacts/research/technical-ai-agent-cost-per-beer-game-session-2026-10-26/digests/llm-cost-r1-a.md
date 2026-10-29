# Digest llm-cost-r1-a (technical research, dimension 1: cost of LLM agents)

Accessed: 2026-10-26 (all). Questions owned: Q1 published tokens/$ per beer-game session; Q2 current list prices + transparent per-session calc; Q3 latency/reliability reports.
Searches run: 2 WebSearch ("LLM agents beer game arXiv"; "LLM agent invalid actions structured output reliability turn-based game"). Fetches: 12 (Anthropic pricing, Gemini pricing, OpenAI docs pricing [openai.com/api/pricing returned 403], DeepSeek pricing x2, Together pricing, arXiv 2605.17036 abs/pdf/html x2, arXiv 2604.17220 abs, INFORMS post, arXiv 2604.07429 abs). 14 tool calls total on the web. Sources actually read: 9 distinct.
Note: WebFetch answers via a small model over page text; numbers below are as relayed by that extraction, not read by eye in the raw page, except Anthropic table rows which I read in the saved raw page text.

## A. Published beer-game LLM studies (Q1)

1. No dollar cost, no token count per decision, no latency, no parse-error rate is reported in the full text of "Reliability and Effectiveness of Autonomous AI Agents in Supply Chain Management" (inference cost "not stated"; tokens/decision "not stated"; max tokens/temperature "not stated"; failed-parse handling "not stated") | https://arxiv.org/html/2605.17036 | arXiv (Long, Simchi-Levi, Zhu, Su, Calmon, Calmon) | v1 2026-05-16, v4 2026-09-21 | 2026-10-26 | medium (read via extraction; only first ~100k + a later slice of ~191k chars read, middle slice partly unread) | other (absence finding)
2. Setup: 4 agents (retailer, wholesaler, distributor, factory); 25-week evaluation games; 30 runs per configuration; models GPT-5 mini, GPT-4o mini, GPT-4.1 mini, Llama 4 Maverick 17B, Llama 3.3 70B, Qwen-3 4B, Phi-4, DeepSeek-R1-0528; human benchmark >100 students, 12 Georgia Tech cohorts | same URL | arXiv | v4 2026-09-21 | 2026-10-26 | medium | performance-number
3. Output contract in the paper's prompt (App. B.2): "Start your response with a JSON object on its own line" of form {"order_quantity": <number_of_cases>}; "This will be parsed by a program, so the format must be valid and exact." | same URL | arXiv | 2026-09-21 | 2026-10-26 | medium | other
4. Run-to-run instability: Table 1 (25 weeks, 30 runs) total cost mean/SD/CV/max: GPT-5 mini 3927/1772/45%/8644; Llama 4 Maverick 17B 4026/2103/52%/8912; Qwen-3 4B 1585/406/26%/2847. Extraction flags text-vs-table inconsistency (text says CV 26-45%, table 52%). Abstract: "agent bullwhip", "run-to-run instability can produce large tail costs"; GenAI agents reduce supply-chain costs "by up to 80% relative to human teams" in best configuration | https://arxiv.org/abs/2605.17036 and html | arXiv | 2026-09-21 | 2026-10-26 | medium | performance-number / failure-report
5. Rule violations: Phi-4 and DeepSeek-R1-0528 "violated basic ordering rules in more than 25% of cases" | https://arxiv.org/html/2605.17036 | arXiv | 2026-09-21 | 2026-10-26 | medium | failure-report
6. Guardrails: budget constraint ("orders were not allowed to exceed available funds") and an expenditure cap at twice total customer demand reduced cost (default Qwen-3 4B: -22% mean cost, CV 26%->12%, max cost -45%; mean cost reductions 25% GPT-5 mini, 39% GPT-4o mini, 41% Llama 4 Maverick 17B, 3% Qwen-3 4B). GRPO post-training of Qwen-3 4B: mean 952, CV 13%, max 1353 | same | arXiv | 2026-09-21 | 2026-10-26 | medium | performance-number
7. Latency (single anecdotal runs by a forum user, live MIT-style beer game sim, info sharing on): gpt-4o-mini ~15 s, gpt-4.1-mini ~20 s, gpt-5-mini ~5 min per run (run length/rounds/agent count not stated). Improvement gpt-4o-mini -> gpt-4.1-mini noted larger than 4.1-mini -> gpt-5-mini. No cost or tokens given | https://connect.informs.org/discussion/can-genai-agents-manage-a-supply-chain-lessons-from-the-classical-beer-game | INFORMS Open Forum (post by D. Simchi-Levi 2025-08-29; reply by W. Hearnes 2025-08-30) | 2025-08-30 | 2026-10-26 | low (forum anecdote, >1 month old and model set old) | performance-number
8. "Dynamics of Cognitive Heterogeneity" (DeepSeek and GPT agents, multi-round): abstract only; agents, rounds, tokens, cost, failure rates all not stated | https://arxiv.org/abs/2604.17220 | arXiv | v1 2026-04-19, v2 2026-06-02 | 2026-10-26 | medium | other (absence)
9. Search-result snippets only (NOT read, not evidence): arXiv 2505.18597 "LLMs for Supply Chain Management", arXiv 2407.11384 InvAgent, AAMAS 2026 papers UYIA3362 and SZPU6292, bptk.transentis.com beergame AI training. SupplyNet and AIM-Bench did not surface in searches.

## B. Current list prices (Q2), USD per 1M tokens

Anthropic page (https://platform.claude.com/docs/en/about-claude/pricing; Anthropic; page carries no visible date in extraction; accessed 2026-10-26; confidence high on rows read raw; recency of page unknown -> flag, but it references Aug-Sep 2026 events so it is current to at least Sep 2026):
10. Claude Haiku 5.5 (prompts <=100k tokens): input 0.10, 5m cache write 0.125, 1h cache write 0.20, cache hit 0.01, output 0.50; batch input 0.05, output 0.25 (50% batch discount). Over 100k tokens: 0.50 in / 2.50 out | high | pricing
11. Claude Sonnet 5.5: input 2, 5m write 2.50, 1h write 4, cache hit 0.10 (0.05x base per footnote), output 10; batch 1 in / 5 out | high | pricing
12. Claude Sonnet 5: 2 in / 10 out; footnote: intro price became standard, the scheduled rise to 3/15 on 2026-09-01 "will not occur" (so earlier reports of a Sonnet 5 price rise are superseded) | high | pricing
13. Claude Haiku 4.5: 1 in / 5 out, cache hit 0.10 (still listed). Opus 5.5: 4 in / 20 out. Fable 5.1: 10 in / 50 out | high | pricing

Google (https://ai.google.dev/gemini-api/docs/pricing; Google; page states "Last updated: 2026-10-26 UTC"; accessed 2026-10-26; high), standard paid tier input / output / cached input:
14. Gemini 2.5 Flash-Lite 0.10 / 0.40 / 0.01; Gemini 3.1 Flash-Lite 0.25 / 1.50 / 0.025; Gemini 3.5 Flash-Lite 0.30 / 2.50 / 0.03; Gemini 2.5 Flash 0.30 / 2.50 / 0.03; Gemini 3 Flash Preview 0.50 / 3.00 / 0.05; Gemini 3.6 Flash and 3.8 Flash 0.75 / 3.75 / 0.075. Output includes thinking tokens. Batch = 50% (e.g. 3.1 Flash-Lite 0.125 / 0.75). Cache storage billed separately. Gemini 3.6 Flash and 3.8 Flash prices DOUBLE on 2027-01-01 | high | pricing

OpenAI (https://developers.openai.com/api/docs/pricing; OpenAI; page shows no as-of date -> flag; accessed 2026-10-26; medium; the older openai.com/api/pricing URL gave HTTP 403), short-context <=272k, input / cached / output:
15. gpt-5-nano 0.05 / 0.005 / 0.40; gpt-6-luna 0.10 / 0.01 / 0.50; gpt-5.4-nano 0.20 / 0.02 / 1.25; gpt-5.6-luna 0.20 / 0.02 / 1.20; gpt-5-mini 0.25 / 0.025 / 2.00; gpt-5.4-mini 0.75 / 0.075 / 4.50. Batch = half of standard. "Priority processing" renamed Fast mode 2026-07-30 | medium | pricing

DeepSeek (https://api-docs.deepseek.com/quick_start/pricing/ ; DeepSeek; no date; accessed 2026-10-26; medium-high):
16. deepseek-flash: cache hit 0.006 (peak) / 0.003 (off-peak), cache miss 0.30 / 0.15, output 1.20 / 0.60. deepseek-v4-pro: hit 0.044/0.022, miss 1.32/0.66, output 3.96/1.98. Peak = 01:00-04:00 and 06:00-10:00 UTC Mon-Fri (excl. Chinese public holidays); off-peak half price | medium-high | pricing

Together AI serverless (https://www.together.ai/pricing ; Together AI; no date; accessed 2026-10-26; medium; WebFetch could not confirm a batch discount):
17. Llama 3 8B Instruct Lite 0.14/0.14; Qwen3.8 Flash 0.15/0.47; Qwen3.5 9B 0.17/0.25; Qwen3 235B A22B 2507 FP8 0.20/0.60; gpt-oss-120B 0.15/0.60; DeepSeek V4.1 Flash 0.30/1.20 (cached 0.006). No Llama 3.3 / Llama 4 chat in table as extracted | medium | pricing

## C. Per-session cost calc (Q2), my arithmetic, ASSUMPTIONS ARE MINE (unverified, no published token counts exist per item 1)

Assumptions: 3 AI roles x 36 turns = 108 LLM calls per session (range 20-50 turns -> x0.56 to x1.39). Per call: 2,000 input tokens (of which 1,200 is a static, cacheable prefix: rules + role + system prompt; remainder is state + recent history) and 150 output tokens (JSON order plus a one-line rationale, NO hidden reasoning). Session totals: 216,000 input tokens; 16,200 output tokens. Interactive (real-time) use, so batch discount not applied (batch = 50% off everything below). "With caching" = 129,600 input tokens at cache-hit price, 86,400 at base price; cache WRITE premium (Anthropic 1.25x on 5m) and Gemini storage fees ignored (small); caching also assumes the same role's prefix is re-hit within the TTL (Anthropic 5m default; a human who thinks >5 min between turns forces rewrites; 1h write exists at 2x base) -> optimistic.

| Model | No cache $/session | With cache $/session |
|---|---|---|
| gpt-5-nano | 0.0173 | 0.0115 |
| Gemini 2.5 Flash-Lite | 0.0281 | 0.0164 |
| Claude Haiku 5.5 | 0.0297 | 0.0180 |
| Qwen3.5 9B (Together) | 0.0408 | n/a (no cached price listed) |
| gpt-oss-120B (Together) | 0.0421 | n/a |
| deepseek-flash off-peak | 0.0421 | ~0.025 (derived, off-peak hit 0.003) |
| Gemini 3.1 Flash-Lite | 0.0783 | 0.0491 |
| deepseek-flash peak | 0.0842 | 0.0461 |
| gpt-5-mini | 0.0864 | 0.0572 |
| Gemini 3.6 Flash (doubles 2027-01-01) | 0.2228 | 0.1353 |
| Claude Sonnet 5.5 | 0.594 | 0.348 |

Sensitivity (Haiku 5.5 / Sonnet 5.5): if models emit ~2,000 output tokens per call (reasoning/thinking billed as output; Gemini page states output includes thinking) -> 216,000 output tokens: Haiku 5.5 ~0.13, Sonnet 5.5 ~2.59 per session uncached. Output tokens dominate once reasoning is on. Hand-check: Haiku no cache = 216,000*0.10/1e6 + 16,200*0.50/1e6 = 0.0216+0.0081 = 0.0297.
Reading: at plain-JSON-order output, small/mini-tier models cost roughly 1-9 US cents per 36-turn session (Haiku 5.5 about 3 cents), a mid-tier (Sonnet 5.5) about 35-60 cents; reasoning-mode output can multiply that 4-5x. Class: pricing/derived. Confidence medium (prices high, token assumptions unverified).

## D. Reliability / latency reports (Q3)

18. Format vs. rule violations are distinct failure modes in LLM game agents (format/structure errors vs rule violations vs turn limit), and handling patterns reported: invalid output -> default action, or skip turn + corrective feedback + retry; validate structured action against environment rules before committing | answer-engine summary of arXiv 2512.11421, 2605.29512 and others (underlying papers NOT read) | arXiv | 2025-12 to 2026-05 | 2026-10-26 | low | failure-report
19. GameWorld (arXiv 2604.07429, submitted 2026-04-08): abstract fetched, does not define Invalid Action Rate or report rates; search summary's claim that weaker models forget the action space under long contexts is UNVERIFIED | https://arxiv.org/abs/2604.07429 | arXiv | 2026-04-08 | 2026-10-26 | low | failure-report
20. Beer-game-specific evidence of rule violations is item 5 (>25% for Phi-4, DeepSeek-R1-0528); items 4 and 6 show variance and that simple code-side guardrails (budget cap, expenditure cap) cut tail cost. Paper does not say how parse failures were handled | see A | medium | failure-report

## Leads worth chasing
- Full text of arXiv 2605.17036: unread middle slice of the HTML (chars ~100k-191k boundary) and appendices may contain call counts or tokens; also the project's code/repo if linked. Its authors' live sim (Simchi-Levi, MIT) may expose latency/cost.
- arXiv 2505.18597 (LLMs for SCM, risk-averse/risk-seeking beer game) and AAMAS 2026 UYIA3362 / SZPU6292: not read; may report calls and model costs.
- arXiv 2407.11384 InvAgent (multi-agent inventory): may give per-run token/cost.
- Primary papers behind item 18: arXiv 2512.11421, 2605.29512 (MindGames), 2607.25308 (CAST) for measured invalid-action rates.
- Official structured-output docs (Anthropic, OpenAI, Gemini constrained decoding / JSON schema) to quantify how far schema-constrained output removes format errors; not fetched.
- Anthropic prompt-caching doc for minimum cacheable prefix length per model (Haiku-tier minimums can exceed 1,200 tokens; if so my caching column is invalid for a short prefix) - not verified.
- Latency benchmarks (time-to-first-token, tokens/s) from provider docs or Artificial Analysis for Haiku 5.5 / Flash-Lite / gpt-5-nano - not fetched; only anecdote in item 7.
- Rate limits / free tiers (Gemini free tier, student cost ceiling) not checked.

## Looked for but not found
- Any published token count per decision or total dollar cost per beer-game session (none in 2605.17036 or in the INFORMS thread).
- SupplyNet and AIM-Bench: no search result surfaced them.
- OpenAI pricing as-of date; DeepSeek, Together, OpenAI pages undated (flag: cannot confirm they are <1 month old).
- A Together/other-provider batch discount percentage; Llama 4 / Llama 3.3 prices on Together (not in extracted table).
- Measured parse-error / invalid-order rate for current small models (Haiku 5.5, Flash-Lite, nano) in a beer game.
- Whether the "Phi-4 / R1 break rules >25%" finding (item 5) holds for current small models: not checked.
