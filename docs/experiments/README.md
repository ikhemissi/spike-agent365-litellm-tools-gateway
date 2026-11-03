# Experiments

Numbered in the order they run; never renumbered. Copy [TEMPLATE.md](TEMPLATE.md) to `NN-<slug>.md`.

| # | Experiment | Questions | Result |
|---|---|---|---|
| 00 | [Environment](00-environment.md): the layers provisioned; PostgreSQL grant as the Entra administrator, layer hook paths, gateway still healthy after more than an hour (database token refresh) | — | done |
| 01 | [Notes MCP server](01-notes-mcp-server.md): one MCP server (a read and a write tool) on Container Apps, internal only, registered in LiteLLM with one team and one virtual key by script | — | done |
| 02 | [Chat UI](02-chat-ui.md): CopilotKit chat with Entra sign-in calling LiteLLM's Responses API with the team key and its MCP tool; each tool call shown | — | done |
| 03 | [Connect to Agent 365](03-connect-agent365.md): discovery of servers and tools at connection (48 s) and of a new server (63 s); per-server Block and per-tool toggles shown | Q1 | done |
| 04 | [Block and allow](04-block-and-allow.md): Block writes an empty enforced tool allowlist on the server with Agent 365's key; every client refused within ~2 s, restored within 10 s; a per-tool toggle on a server without an enforced allowlist sends no write | Q2, Q3 | done |
| 05 | [Tool drift](05-tool-drift.md): a changed description reaches clients at once and shows in the admin center; a new tool is refused under Agent 365's enforced allowlist until enabled; per-tool toggles work once the server is under it | Q4, Q3 | done |
| 06 | [Guardrail and audit](06-guardrail-and-audit.md): every tool call evaluated as the user (On-Behalf-Of), +0.4–1.4 s; key-only callers refused; verdicts Allow for the inputs tested; ExecuteToolByGateway records name the user, tool and server | Q6, Q5 | done |
| 07 | [Agent 365's identity](07-agent365-identity.md): a read-only key is enough for discovery; blocking needs a proxy_admin key (403 with the read-only one); rotation without downtime; after revocation the admin center shows a banner and no longer lists the gateway's tools; an unblock writes every current tool into `allowed_tools` | Q5 | done |
