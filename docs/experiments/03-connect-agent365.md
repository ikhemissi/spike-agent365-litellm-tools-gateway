# 03 — Connect the gateway to Agent 365 (discovery)

**Date:** 2026-11-02 · **Answers:** Q1, part of Q3 and Q5 · **Versions:** Microsoft 365 admin center (Agents → Settings → Gateways, preview), LiteLLM v1.106.6

## Goal

Connect the LiteLLM gateway to Agent 365's tools gateway and observe what Agent 365 discovers, how fast, and with which calls; then register a new server and time its discovery.

## Setup

- The gateway with one MCP server `notes` (two tools), team `spike`, and a dedicated LiteLLM user `agent365` with the `proxy_admin` role and its own key in Key Vault (`agent365-gateway-key`, created by `src/03_agent365_key.py`), so that Agent 365's access can be revoked without touching the master key and its calls are attributable.
- Evidence: the gateway's access log in Log Analytics (`ContainerAppConsoleLogs`), with the requests and their times; ingestion took 5–10 minutes.

## Steps

1. Admin center, as Global Administrator: Agents → Settings → Gateways → LiteLLM gateway → Connect a gateway (name, the gateway URL, the agent365 key), tenant consent (14:13 local, 13:13 UTC).
2. Agents → Tools: wait for the server; open it.
3. `src/03_add_readonly_server.py`: register `notes_readonly` (same server, LiteLLM exposes only `list_notes` through `allowed_tools`) at 13:22:44 UTC; wait for it in the Tools page.

## Result

| Time (UTC) | Observed |
|---|---|
| 13:13:13 | Agent 365 calls `GET /models` with the agent365 key (when connecting) |
| 13:14:01 | `GET /v1/mcp/server`, then `GET /mcp-rest/tools/list?server_id=…&include_disabled_tools=true` for the server (twice): discovery 48 s after connecting |
| ≈13:15–13:16 | `notes` visible in the Tools page |
| 13:15–13:17 | the same calls again while the admin browses, and `GET /v1/mcp/server/<id>` when the server is opened: the portal reads the gateway live |
| 13:22:44 | `notes_readonly` registered |
| 13:23:47 | servers listed and both servers' tools read (63 s after registration); `notes_readonly` visible at ≈13:24 |

What the Tools page shows:

- The source is **"LiteLLM"** (filter and publisher).
- Each server lists its tools with an **Enabled** toggle per tool, and the server has a **Block** button.
- For `notes_readonly`, `add_note` is shown **disabled** and `list_notes` **enabled**: Agent 365 reflects LiteLLM's own server-level tool restriction (`allowed_tools`, read with `include_disabled_tools=true`).
- The view is organised by server and tool; Agent 365 called only `/models`, `/v1/mcp/server` and `/mcp-rest/tools/list` (not LiteLLM's team endpoints).
- LiteLLM refuses `-` in MCP server names (`notes_readonly`, not `notes-readonly`).

## Conclusion

Q1 (discovery): Agent 365 discovers a connected LiteLLM gateway's servers and tools within about a minute (48 s at connection, 63 s for a new server), by reading LiteLLM's admin API with the key it was given, and again whenever an admin browses the Tools page. It shows per-server and per-tool controls; the per-tool state matches LiteLLM's server-level `allowed_tools`, which suggests that the toggles act on the server for every caller, not per team. Experiment 04 checks what Block and the toggles change in LiteLLM, and when each client is affected.
