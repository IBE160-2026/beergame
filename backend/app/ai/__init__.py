"""The AI gateway: the only LLM boundary (AD-6).

`app.ai.gateway.run` is the one way to make an LLM call. Other modules also use
`app.ai.config` (model configs) and `app.ai.budget` (budgets) and never touch this package's
tables. Only this package imports pydantic-ai or a provider SDK; `app.ai` imports nothing from
`app.modules`. This file imports nothing, so reading a config does not load pydantic-ai.
"""
