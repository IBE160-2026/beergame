"""AI-held and scripted Seats: the one order source (AD-5). Other modules import `service.py`;
`llm.py` builds the LLM player's request (Story 2.4) and is imported only where an LLM call is
prepared, since it loads pydantic-ai through the gateway."""
