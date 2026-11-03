# 04 — Block and allow from Agent 365

**Date:** 2026-11-02 · **Answers:** Q2, Q3 (part) · **Versions:** Microsoft 365 admin center (Agents → Tools, preview), LiteLLM v1.106.6

## Goal

Find out what Agent 365's controls on a LiteLLM server change in the gateway, which clients they stop, and how fast.

## Setup

- The notes server registered in LiteLLM; team `spike` allowed to use it; Agent 365 connected with its own LiteLLM key (`agent365`, proxy admin) — see [03](03-connect-agent365.md).
- `src/04_probe.py`: every 10 s with the team's key, (1) MCP `tools/list` on the gateway (what a coding agent sees), (2) `list_notes` over MCP, (3) `list_notes` over LiteLLM's REST API. Changes printed; every probe in [04-probe-controls.csv](assets/04-probe-controls.csv).
- `src/04_snapshot.py`: LiteLLM's MCP state (servers in full, team permissions) before and after: [baseline](assets/04-snapshot-baseline.json), [after block](assets/04-snapshot-after-block.json), [after unblock](assets/04-snapshot-after-unblock.json).
- The gateway's access log (live console log, then Log Analytics) for the calls Agent 365 made.
- The chat UI ([02](02-chat-ui.md)) as the user-facing client.

## Steps

- **A.** Disable one tool (`add_note`) with its toggle on the server's page, Save (14:32–14:35 local, four attempts).
- **B.** Block the server (14:44 local).
- **C.** Unblock it (14:48 local).

## Result

**A — per-tool toggle:** the toggles did not apply yet. During each attempt Agent 365 **read** the gateway (`GET /v1/mcp/server/<id>`, `GET /mcp-rest/tools/list…&include_disabled_tools=true`); no write reached LiteLLM, and the probe saw no change. The server had no enforced allowlist yet; [05](05-tool-drift.md) shows the toggles applying once it has one.

**B — block:**

| Time (UTC) | Observed |
|---|---|
| 13:44:08 | probe: both tools listed, both calls ok |
| 13:44:16.6 | `PUT /v1/mcp/server` (202) by `agent365`: the server's `allowed_tools` set to `[]` with `mcp_info.tool_allowlist_enforced: true` |
| 13:44:18 | probe: MCP lists no tools; MCP call → "Tool list_notes is not allowed for server notes. Contact proxy admin to allow this tool."; REST → 403 with the same message |
| after | chat UI: the assistant answers it cannot access the notes tool; portal: server "Blocked", both tool toggles shown disabled |

**C — unblock:**

| Time (UTC) | Observed |
|---|---|
| 13:48:27 | probe: still refused |
| 13:48:29.3 | write by `agent365`: `allowed_tools` set to `["add_note", "list_notes"]`, `tool_allowlist_enforced` still `true` |
| 13:48:38 | probe: both tools listed, both calls ok; chat UI lists notes; portal: "Available", both toggles enabled |

Team permissions never changed: the controls act on the **server**, for every key and team.

## Conclusion

- **Q2 (enforcement):** Block is enforced by the gateway itself, through LiteLLM's own tool allowlist written with the key Agent 365 holds; it applied to every client path through the gateway (MCP, REST, the chat UI's Responses API path) within about 2 s of the write (block) and within one probe interval of it (unblock, under 10 s). Every call goes through it because the server is reachable only inside the environment ([01](01-notes-mcp-server.md)); keep MCP servers reachable only through the gateway for the same effect. The block is visible to users as a refusal message from the gateway.
- **Q3 (granularity):** per server in this experiment: on this server (no enforced allowlist yet) saving a per-tool toggle sent no write to the gateway, and the toggles apply once the server is under an enforced allowlist (05); Block acts on the whole server for every team. Agent 365 reflects LiteLLM's own server-level tool restriction (03); per-team permissions stay managed in LiteLLM.
- **To test in 05:** after an unblock the server keeps an **enforced allowlist of the tools that existed at that moment**, so a tool the server adds later would be refused until someone allows it.
