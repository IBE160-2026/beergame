# arch-verify-r3-e digest (round 3, retrieval/verification)

Accessed: 2026-10-26 for all items. Budget used: 18 tool calls (cap hit; several spent on 301 redirects and one blocked host).

## Header

Questions:
1. Sterman (1989) ordering rule + fitted parameters, exact as printed.
2. Computer-player behaviour in existing beer game products.
3. Exact wording from official pages: (a) Anthropic Haiku-class pricing + prompt caching; (b) Anthropic temperature/seed support; (c) OpenAI seed/reproducible outputs.
4. Small neural policy inference latency in browser (ONNX Runtime Web / TF.js).

Searches/fetches run (in order):
- WebFetch docs.anthropic.com pricing, caching, OpenAI platform URL: all 301 redirects (followed below)
- WebSearch "Sterman 1989 beer game anchoring adjustment ordering rule estimated parameters theta alpha_S beta"
- WebFetch platform.claude.com/docs/en/docs/about-claude/pricing (resolved to /docs/en/about-claude/pricing), prompt-caching page, developers.openai.com/api/docs/advanced-usage/reproducible-outputs (404), web.archive.org DSpace PDF (blocked: "unable to fetch from web.archive.org")
- WebFetch platform.claude.com/docs/en/api/messages (first 100k of 1.29M chars read; no temperature/seed text in that portion)
- WebSearch OpenAI seed/determinism (allowed domains openai)
- WebFetch developers.openai.com/api/docs/guides/advanced-usage; platform.claude.com extended-thinking; proceedings.systemdynamics.org/2015/proceed/papers/P1053.pdf (PDF returned as compressed binary; fetch tool could not extract text)
- WebSearch beer game bot/README; WebSearch ONNX Runtime Web small MLP latency

## Findings

Format: claim | source URL | publisher | pub_date | accessed | confidence | class

### Task 3a: Anthropic pricing and caching (official docs)

1. Pricing table row, verbatim: "Claude Haiku 5.5 (for prompts up to 100,000 tokens) | $0.10 / MTok (base input) | $0.125 / MTok (5m cache writes) | $0.20 / MTok (1h cache writes) | $0.01 / MTok (cache hits and refreshes) | $0.50 / MTok (output)". | https://platform.claude.com/docs/en/about-claude/pricing | Anthropic | undated (page shows no date; points to claude.com/pricing for "most current") | 2026-10-26 | high | pricing
2. Same table, verbatim: "Claude Haiku 5.5 (for prompts over 100,000 tokens) | $0.50 / MTok | $0.625 / MTok | $1 / MTok | $0.05 / MTok | $2.50 / MTok". Note: Haiku 5.5 has a long-context surcharge tier; page line says 4.6+ models except Haiku 5.5 include full 1M context at standard pricing. | same URL | Anthropic | undated | 2026-10-26 | high | pricing
3. Same table: "Claude Haiku 4.5 | $1 / MTok | $1.25 / MTok | $2 / MTok | $0.10 / MTok | $5 / MTok". | same URL | Anthropic | undated | 2026-10-26 | high | pricing
4. Batch rows (second table in file; column headers not captured by my grep, so assignment to batch input/output is inferred): "Claude Haiku 5.5 (for prompts up to 100,000 tokens) | $0.05 / MTok | $0.25 / MTok"; over 100k: "$0.25 / MTok | $1.25 / MTok". Consistent with 50% batch discount vs. rows 1-2. | same URL | Anthropic | undated | 2026-10-26 | medium (headers not re-read) | pricing
5. Token-count note, table rows: "Claude Haiku 5.5 | 286 tokens | 406 tokens" (column headings not captured; likely a tokenizer comparison table). Not interpreted. | same URL | Anthropic | undated | 2026-10-26 | low | other
6. Prompt caching minimum, verbatim list item: "512 tokens for Claude Fable 5.1, [Claude Mythos 5.1], Claude Opus 5.5, Claude Opus 5, Claude Sonnet 5.5, Claude Fable 5, [Claude Mythos 5], and Claude Haiku 5.5". Haiku 4.5: "4,096 tokens"; Haiku 3.5: "2,048 tokens". "Shorter prompts cannot be cached, even if marked with cache_control." | https://platform.claude.com/docs/en/build-with-claude/prompt-caching (URL as reported by the fetch tool's page metadata; the fetch tool summarizes with a small model, so quotes are from its output, not raw page text) | Anthropic | undated | 2026-10-26 | medium-high | docs-guarantee
7. Multipliers, verbatim: "Cache write tokens with a 5-minute TTL are 1.25 times the base input tokens price." "Cache write tokens with a 1-hour TTL are 2 times the base input tokens price." "Cache read tokens are 0.1 times the base input tokens price (see the table footnote for per-model exceptions)." Footnote exceptions: Fable 5.1/Mythos 5.1 0.025x; Opus 5.5 and Sonnet 5.5 0.05x; "All other models use the standard 0.1x multiplier." Haiku 5.5 row cache hit $0.01 vs base $0.10 = 0.1x, consistent. | same prompt-caching URL | Anthropic | undated | 2026-10-26 | medium-high | pricing
8. Cache lifetime, verbatim: "By default, the cache has a 5-minute lifetime. The cache is refreshed for no additional cost each time the cached content is used." Also: "The lifetime is measured from the start of the request that writes or reads the cache entry, not from the end of its response." | same | Anthropic | undated | 2026-10-26 | medium-high | docs-guarantee
9. Fetch of prompt-caching page covered only first 100,000 of 162,264 characters; remainder unread. | same | - | - | 2026-10-26 | - | other

### Task 3b: Anthropic temperature / seed

10. NOT CONFIRMED. The Messages API reference page (https://platform.claude.com/docs/en/api/messages) fetched summary says the top-level parameter list "goes from system to thinking with no temperature entry" and no `seed` parameter; but only 100k of 1,289,756 characters were read and the summarizer said the page was truncated in the tools section, so this is absence in a partial read, not proof. | Anthropic | undated | 2026-10-26 | low | docs-guarantee
11. Extended thinking page (https://platform.claude.com/docs/en/build-with-claude/extended-thinking) returned in full; it contains NO sentence about temperature, top_p or top_k. It states: "Claude 4.7 and later models do not support [extended thinking: thinking.type enabled with budget_tokens] and reject requests that use it, returning a 400 error" and that Claude Opus 5.5, Sonnet 5, Sonnet 5.5, Fable 5.1, Haiku 5.5 use adaptive thinking ("type: 'enabled' returns a 400 error"). "Claude Opus 5.5 and Claude Haiku 5.5 default to 'medium'" effort. | Anthropic | undated | 2026-10-26 | high | docs-guarantee
12. Relevance: for Haiku 5.5, thinking is adaptive-only and effort defaults to medium (need to set thinking off/low effort for cost control; adaptive "might skip thinking entirely on easy inputs" at lower effort, verbatim: "at lower effort settings it might skip thinking entirely on easy inputs"). | same | Anthropic | undated | 2026-10-26 | high | docs-guarantee

### Task 3c: OpenAI reproducible outputs

13. The URL developers.openai.com/api/docs/advanced-usage/reproducible-outputs returned HTTP 404. The working page is https://developers.openai.com/api/docs/guides/advanced-usage (section "Reproducible outputs"). Verbatim sentences (as returned by fetch tool): "Chat Completions are non-deterministic by default (which means model outputs may differ from request to request)." "Set the seed parameter to any integer of your choice" "Sometimes, determinism may be impacted due to necessary changes OpenAI makes to model configurations on our end." "If this value is different, you may see different outputs due to changes we've made on our systems." (the last refers to system_fingerprint). Summary from tool: setting seed with identical other parameters gives "mostly deterministic" outputs. | OpenAI | page shows no date | 2026-10-26 | medium (tool paraphrases around quotes; "mostly deterministic" is the tool's wording, not a verified quote) | docs-guarantee
14. OpenAI API reference wording (search-result summary only, not fetched): determinism "is not guaranteed" and system_fingerprint should be checked for backend changes. Cookbook (https://cookbook.openai.com/examples/reproducible_outputs_with_the_seed_parameter) says feature in beta, originally for gpt-4-1106-preview and gpt-3.5-turbo-1106, "small chance" of differences with matching seed and fingerprint. | OpenAI | cookbook ~Nov 2023 (date from memory/not shown; unverified) | 2026-10-26 | low-medium | docs-guarantee

### Task 1: Sterman (1989) rule and parameters

15. Not obtained from a primary or reprinting source. The 2015 SD Society paper P1053 PDF (https://proceedings.systemdynamics.org/2015/proceed/papers/P1053.pdf, "Results of a Beer Game Experiment: Should a Manager...") was downloaded by the fetch tool as compressed binary; text not extracted. Saved at C:\Users\pape\.claude\projects\D--IBE160-2026-beergame\5f0913f8-ee17-4555-877c-18c977319a9c\tool-results\webfetch-1793043591035-4k30l0.pdf (untrusted, not opened further). Could be extracted locally with pdftotext/python if someone wants. | SD Society | 2015 | 2026-10-26 | n/a | parameter
16. Secondary, search-result summary only (not fetched): a Bogazici University conference paper (https://ie.bogazici.edu.tr/sites/ie.boun.edu.tr/files/publication/HakanYasarcan/SIMID/conference%20papers/8.The%20Effect%20of%20Semi-Rational%20Supply%20Chain%20Members%20on%20the%20Decision%20Parameters%20Used%20in%20Managing%20the%20Stock%20of%20an%20Echelon.pdf) maps parameters to: stock adjustment time (1/alpha_S), weight of supply line (beta), desired inventory (S*), smoothing factor (theta), and states "According to Sterman (1989), the optimum value of this parameter is one unit of time (i.e, a week)" [stock adjustment time]. Symbols garbled in extraction. Confirms the rule is anchoring-and-adjustment with parameters theta, alpha_S, beta, S*. | Bogazici University (conference/SIMID paper) | undated | 2026-10-26 | low-medium (secondary, via search snippet) | parameter
17. Low-quality claim from search summary: a calculator site says Sterman (1989) reported alpha_S around 0.3 and beta (alpha_SL) near zero. The search tool itself flagged it as "low-authority" and unverified. Also, the equation form and fitted values were not found in any fetched page. Treat as hypothesis only. | secondary calculator site (metricgate.com/docs/beer-game-bullwhip-simulation/ listed in results; not fetched) | 2026-05-27 (date shown in result title) | 2026-10-26 | low | parameter
18. Dogan and Sterman (later work, per search summary) first estimate Sterman (1989) rule then test relaxed alternatives; candidate follow-up source, not retrieved. | n/a | n/a | 2026-10-26 | low | other

### Task 2: Computer-player behaviour in existing products

19. No product documentation for computer-player ordering rules was found (MIT Sloan Beer Game Online, Zensimu, beergame.org, En Dash not reached; no search for them within budget). | - | - | - | - | - | other
20. Open-source/research examples from search results (not fetched, snippets only): (a) Hugging Face Space "Beergamesimulation" README: Streamlit app, human plays distributor, factory/wholesaler/retailer are GPT-4o-mini agents, 36-week horizon, 2-week shipping delay, 1-week information delay (https://huggingface.co/spaces/Lilli98/Beergamesimulation/blob/main/README.md; community-hosted, not peer-reviewed, undated). (b) transentis BPTK "Training Artificial Intelligence To Play The Beer Distribution Game" (https://bptk.transentis.com/model_library/beergame/training_ai_beergame.html; vendor documentation, undated): title indicates RL training of agents; content not read. (c) Oroojlooyjadid et al., "A Deep Q-Network for the Beer Game" (arXiv 1708.05924; published in Manufacturing & Service Operations Management, INFORMS, doi 10.1287/msom.2020.0939; peer-reviewed): per search summary, DQN near-optimal when teammates use base-stock; base-stock described as optimal under some conditions; independent DQN agents can learn to order zero if only retailer pays stockout cost (supplement). Snippet-level, not verified. | various | various | 2026-10-26 | low-medium | pattern

### Task 4: Browser inference latency

21. No source with a measured latency for a small MLP in ONNX Runtime Web or TF.js was found. Closest, all indirect: Microsoft ONNX Runtime Web post (https://opensource.microsoft.com/blog/2021/09/02/onnx-runtime-web-running-your-machine-learning-model-in-browser/, Microsoft, 2021-09-02, vision models only: MobileNet, SqueezeNet, Emotion, YOLO; speedup chart, no ms for MLP); official tutorial (https://onnxruntime.ai/docs/tutorials/web/) says all ONNX operators are supported by WASM but only a subset by WebGL/WebGPU/WebNN. Medium posts report 8-12 ms for all-MiniLM-L6-v2 on an M2 (sentence-embedding transformer, ~22M params, not an MLP; unverified blog). | Microsoft; Medium blogs | 2021 / undated | 2026-10-26 | low | other

## Looked for but not found

- Sterman (1989) equation and fitted parameter values as printed (theta, alpha_S, beta, S*): not retrieved. MIT DSpace via web.archive.org is blocked by the fetch tool; DSpace direct, Semantic Scholar, INFORMS abstract, textbook excerpts not attempted (budget exhausted after redirects and one failed archive attempt). The 2015 SD Society PDF is on disk but unextracted. Suggest local text extraction of that PDF, or fetching the Bogazici paper directly.
- Any statement on `temperature` or `seed` for current Anthropic models: the Messages API page is 1.29M characters and only the first 100k were read; need a targeted page (e.g. platform.claude.com/docs/en/api/messages parameters via offset, or the "models overview"/migration guide). Anthropic having no `seed` parameter is unconfirmed (absence in partial read only).
- Computer-player difficulty/ordering behaviour on MIT Sloan Beer Game Online, transentis beergame, Zensimu, beergame.org, En Dash: not reached.
- Browser inference latency for small MLP: no source with numbers.
- Any date on Anthropic or OpenAI doc pages: none displayed in fetched content. Dating must rely on access date 2026-10-26 plus the model names visible (Haiku 5.5 etc.).
