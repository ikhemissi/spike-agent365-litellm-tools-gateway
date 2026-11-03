# 06 — Agent 365 guardrail and audit

**Date:** 2026-11-02 · **Answers:** Q6, part of Q5 · **Versions:** LiteLLM v1.106.6 (`agent_365` guardrail, `pre_mcp_call`), Microsoft Agent 365 tool-evaluation endpoint, Microsoft Defender XDR Advanced Hunting

## Goal

Turn on LiteLLM's Agent 365 guardrail and see what it adds: which calls it evaluates or refuses, how much latency, which verdicts Defender returns, and which records land where.

## Setup

- How the guardrail authenticates (read in LiteLLM's source at v1.106.6): before each MCP tool call it exchanges **the caller's Entra token** (audienced to the gateway's app registration) for an Agent 365 token with scope `ThreatProtection.Evaluate.All` (**On-Behalf-Of**, with the gateway app's client secret), and posts the pending call to `https://agent365.svc.cloud.microsoft/agents/tool-evaluation/evaluate`. A caller with only a LiteLLM key has no Entra token: the guardrail refuses its tool calls.
- `infra/guardrail`: the gateway's app registration (scope `Tools.Use`, delegated `ThreatProtection.Evaluate.All` on Microsoft's Agent 365 app with tenant-wide admin consent, the Azure CLI and the chat UI pre-authorized), its client secret in Key Vault (**documented exception**: LiteLLM's On-Behalf-Of exchange needs one). The tenant already had the Agent 365 service principal.
- `src/06_configure_guardrail.py`: guardrail `agent365` on every call, `fail_closed`.
- Callers send two credentials: the LiteLLM key in `x-litellm-api-key`, the user's Entra token in `Authorization` (LiteLLM keeps the bearer for the guardrail since BerriAI/litellm#45746, included in v1.106.6).
- `src/06_guarded_calls.py`: calls with the user's token (from the Azure CLI) and the team key, over REST and MCP: benign reads, writes with test content, and calls with the team key only. The chat UI then sends each user's gateway token too (`GATEWAY_SCOPE`).

## Result

| Case | Without the guardrail | With it |
|---|---|---|
| Benign call with the user's token | 140–230 ms | 0.6–1.9 s; verdict **Allow**, `defender_status: Evaluated` (Agent 365's evaluation 0.4–1.4 s) |
| Team key only (no user token) | allowed | **refused**: REST 401, MCP `isError` "the caller did not present an Entra bearer token"; verdict `Rejected` |
| Writes with test content in `add_note` | — | **Evaluated → Allow**; the note was stored (no blocking policy configured in this spike) |
| Responses API (the chat's path) with the user's token | — | tools run through the guardrail; without the token, the model reports the block |
| Chat UI with the user's gateway token | — | works; no extra consent prompt |

Where the evidence is:

- **LiteLLM's OpenTelemetry spans** (Application Insights, `guardrail` dependency): verdict, `defender_status`, a correlation id and Agent 365's latency for every evaluated call; the reason for every refusal. Not in LiteLLM's spend logs, and only refusals in its console log.
- **Defender Advanced Hunting**, `CloudAppEvents`, `ActionType == "ExecuteToolByGateway"`, `Workload: Agent365`: one record per evaluated call (7 of 7 checked), with the **user** (UPN, display name), `ToolName`, `ToolServerName`, a `ConversationId` and `TraceId`. Also: `PlatformAgentId` = the **alias of the LiteLLM key** (`spike-ui`); `ServerAddress` an internal address of the Container Apps environment. Records are matched to the gateway's trace by time, user and tool.
- Before these calls, the tenant had no tool-execution records in 30 days.

## Conclusion

- **Q6:** the guardrail makes every MCP tool call through the gateway an evaluated, user-attributed event in Defender, at a cost of about 0.4–1.4 s per call, and refuses tool calls that do not carry a user's Entra token. Verdicts were Allow for the inputs tested; a blocking policy was not configured in this spike. Not tested in this time box: a Defender policy or rule that blocks gateway tool calls. The records name the user, the tool and the server, and match the gateway's own traces by time, user and tool.
- **Q5 (part):** a user's identity reaches Agent 365 through the gateway (On-Behalf-Of); LiteLLM does not pass it on to the MCP server itself. The records' `PlatformAgentId` is the LiteLLM key's alias. With the guardrail on, the gateway receives user tokens: every caller sends a user's Entra token next to its LiteLLM key.
