# Questions

The main question: when a LiteLLM gateway is connected to the Agent 365 tools gateway, what is governed, how fast, at what granularity, with which identity and which records? Split into:

| # | Question | Experiments | Status |
|---|---|---|---|
| Q1 | **Discovery:** what does Agent 365 show from a connected LiteLLM gateway (servers, tools, teams), and how fast does a newly registered server appear? | 03 | answered |
| Q2 | **Enforcement:** what does an allow or block in the Microsoft 365 admin center change in LiteLLM (per-team MCP permissions), which clients does it stop (the UI, a direct API call, a coding agent), and how long does it take? | 04 | answered |
| Q3 | **Granularity:** is control per server, per tool or per team? Can LiteLLM's own per-key or per-team tool permissions complement it, and does Agent 365 see them? | 03, 04, 05 | answered |
| Q4 | **Drift:** when an approved MCP server changes its tool definitions, is the change noticed, flagged or re-approved anywhere? | 05 | answered |
| Q5 | **Identity:** what rights does the key Agent 365 holds for the gateway have, where is it stored and how is it rotated? Can a user's identity reach the MCP servers through LiteLLM? | 06, 07 | answered |
| Q6 | **Runtime controls and audit:** what does LiteLLM's Agent 365 guardrail block (Defender threat detection on tool calls), how much latency does it add, and which records land where (LiteLLM logs, `CloudAppEvents` `ExecuteToolByGateway`, Agent 365) for an allowed call, a blocked call and an admin change? | 06 | answered |

Status: `open`, `answered`, `partly answered`, `unanswered` (with what blocked it).

## References

- Microsoft Learn, "Manage Tools Gateway in Microsoft 365 admin center" (preview).
- LiteLLM, the Agent 365 MCP tool-call guardrail (BerriAI/litellm#38241) and its design issue (BerriAI/litellm#37343).
