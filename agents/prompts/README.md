# prompts

Prompt Registry — a central place for every Agent's system prompt / persona,
instead of scattering them across the codebase. See `system_prompts.py` —
each persona is a string constant, registered in `PROMPT_REGISTRY` so
`services/orchestration-api` can pick one based on context.
