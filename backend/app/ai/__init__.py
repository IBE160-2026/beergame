"""The AI gateway: the only LLM boundary (AD-6).

Other modules use `app.ai.config` (model configs) and `app.ai.budget` (budgets) and never touch
this package's tables. `app.ai` imports nothing from `app.modules`.
"""
