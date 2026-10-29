# openrouter-switcher-r5-b (technical, Deepen: cheaper models and weekly switcher)

Accessed: 2026-10-29 (live data; values change). Done by the lead. Sources: OpenRouter public APIs `GET https://openrouter.ai/api/v1/models` (438 paid text models in the pricing scan) and `GET https://openrouter.ai/api/v1/endpoints/zdr` (1,086 endpoints with a Zero Data Retention policy), downloaded without an API key and parsed locally with `model_switcher.py screen` (same folder: `../model-switcher/`). Snapshot saved as `../model-switcher/screen-2026-10-29.json`.
Assumed tokens per session (OUR assumption, same as main report): 216,000 input, 16,200 output (3 roles x 36 turns). Estimated cost = endpoint list price x assumed tokens; it ignores reasoning-token overhead, retries, caching and the OpenRouter credit fee.

## Findings (claim | source | confidence | class)

1. Claude Haiku 5.5 has 6 ZDR endpoints (Google Vertex, Amazon Bedrock; EU variants at $0.11/$0.55), cheapest estimate $0.0297 per session; every one of them lacks `seed` and `temperature` in `supported_parameters` (structured outputs only on the Google endpoints). In the all-models listing Haiku 5.5 also shows seed=false and temperature=false. | /endpoints/zdr, /models | high for the snapshot | docs-guarantee
2. Gate funnel at 2026-10-29: 1,086 ZDR endpoints; 291 endpoints pass (text output, paid, endpoint status 0, supports `seed`, `temperature` and `structured_outputs`, uptime last 24 h >= 99%, context >= 32,768). Rejected: 476 missing a required parameter, 137 not text models, 65 uptime below gate, 51 status not OK, 10 context below gate, 3 free/zero price. | screen output | high for the snapshot | other
3. DeepSeek V4.1 Flash (`deepseek/deepseek-v4.1-flash`): listing price $0.045 in / $0.50 out per million tokens, cache read $0.006; supports seed, temperature, structured outputs, reasoning, 1,048,576 context. 36 ZDR endpoints; cheapest Morph fp8 $0.0157 per session (-47% vs Haiku 5.5), Wafer mxfp4 $0.0178 (-40%), Decart fp4 $0.0224; most expensive endpoint $0.1685 (BaseTen) = 10.7x the cheapest; one DeepInfra endpoint had 52% and one BaseTen endpoint 33% uptime over 24 h. DeepSeek's own first-party API does not appear among provider names in the ZDR list. Older `deepseek/deepseek-v4-flash`: cheapest ZDR endpoints Relace fp4 $0.0181, DeepInfra fp8 $0.0224. | /models, /endpoints/zdr | high for the snapshot | pricing
4. Cheapest eligible endpoints per model (estimated $/session, change vs Haiku 5.5 $0.0297): mistral-nemo @ DekaLLM fp8 $0.0044 (-85%); gpt-oss-20b @ AkashML fp4 $0.0059 (-80%); gpt-oss-120b @ Near AI fp4 $0.0089 (-70%); gemma-3-4b-it @ Parasail $0.0095 (-68%); glm-5.3-flash @ OpenInference fp4 $0.0114 (-62%); mistral-small-24b-2501 @ DeepInfra fp8 $0.0121 (-59%); deepseek-v4.1-flash @ Morph fp8 $0.0157 (-47%); llama-3.3-70b @ DeepInfra fp8 $0.0268 (-10%); qwen3-30b-a3b-instruct-2507 @ DekaLLM $0.0243 (-18%). | screen output | high for the snapshot | pricing
5. Reasoning-capable models (gpt-oss, glm-5.3-flash, deepseek-v4.x) bill reasoning tokens as output on OpenRouter (see main report [38]); the estimates above assume reasoning off, so the real cost per task of these can be several times higher until measured. | main report [38] | medium | pricing
6. Quantisation varies by endpoint (fp4, mxfp4, fp8, bf16, int4); OpenRouter docs note quantised models "may exhibit degraded performance for certain prompts" (main report [29]). | main report [29] | medium | other
7. No source in this run gives beer-game decision quality (invalid-order rate, bullwhip fidelity) for any of these cheaper models. The only related evidence is the arXiv 2605.17036 preprint: small or weaker models vary strongly between runs (Qwen-3 4B CV 26%, Llama 4 Maverick 17B CV 52%) and Phi-4 and DeepSeek-R1-0528 violated ordering rules in >25% of cases (main report [13]). | main report [13] | medium | failure-report

## Arithmetic (ours, assumptions marked)
- Saving per session vs Haiku 5.5: DeepSeek V4.1 Flash (Morph) $0.0140; gpt-oss-20b (AkashML) $0.0238.
- Weekly shadow-evaluation cost, assumed 6 candidates x 30 golden games (3,240 decisions each) at an assumed average of $0.02 per game: about $3.60 per week.
- Break-even volume of the weekly evaluation: $3.60 / $0.0140 = about 260 sessions per week against Haiku; for switching between two cheap candidates with a $0.0098 difference, about 370 sessions per week.

## Looked for but not found
- Any measurement of beer-game decision quality for gpt-oss, DeepSeek V4.x, Mistral, Gemma or GLM models.
- Latency and throughput per endpoint: `latency_last_30m` and `throughput_last_30m` were null in every ZDR record read.
- Data-centre region per endpoint (relevant for EU residency); only the EU in-region routing page mentions Vertex/Bedrock EU variants.
- How the `status` field values (0, -2, -5) are defined; the screen treats 0 as healthy (our assumption).
