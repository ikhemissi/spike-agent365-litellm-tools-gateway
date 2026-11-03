# Findings — Governing LiteLLM MCP servers with Agent 365

**Date:** 2026-11-02 · **Versions tested:** Microsoft 365 admin center, Agents → Settings → Gateways and Agents → Tools (preview, November 2026); LiteLLM v1.106.6; MCP Python SDK 2.3.0; Azure Container Apps

## Summary

Connecting a LiteLLM gateway to Agent 365 takes a URL and a LiteLLM key; Agent 365 then reads the gateway's MCP servers and tools within about a minute, and again whenever an admin browses the Tools page. Its **Block** takes effect quickly: Agent 365 writes an empty, enforced tool allowlist on the server in LiteLLM with the key it holds, and every client going through the gateway is refused within about 2 seconds; unblocking restores access within 10 seconds. Control is **per server, for every team**, and per tool once the server is under Agent 365's enforced allowlist (after one block and unblock); team permissions stay managed in LiteLLM. A changed tool description reaches clients at once and Agent 365 shows the new text; a tool added later is refused until allowed on a server under an enforced allowlist. LiteLLM's Agent 365 guardrail adds a Defender evaluation of every tool call as the signed-in user, recorded in Defender, at 0.4–1.4 s per call, and requires every caller to present a user token. The key Agent 365 holds is a LiteLLM `proxy_admin` key, so it belongs in a vault with rotation; and keeping the MCP servers reachable only through the gateway makes every call go through its allowlist.

## Answers

### Q1 — Discovery

Agent 365 discovered the gateway's server and its tools 48 s after the connection and a newly registered server 63 s after its registration, by calling LiteLLM's admin API (`/v1/mcp/server`, `/mcp-rest/tools/list` with disabled tools) with its key; the Tools page reads the gateway live while an admin browses it. It shows the server, its publisher and source ("LiteLLM"), and its tools, including LiteLLM's own server-level restriction; LiteLLM teams stay managed in the gateway (Agent 365 read only the model, server and tool endpoints). ([03](experiments/03-connect-agent365.md))

### Q2 — Enforcement

Block is enforced by LiteLLM: Agent 365 sets the server's `allowed_tools` to `[]` with `tool_allowlist_enforced: true`, and the MCP endpoint, LiteLLM's REST tool calls and the chat UI were all refused within about 2 s of the write ("Tool … is not allowed for server notes"); unblocking writes back the current tools and access returned within 10 s. It applies to every path through the gateway; keep the MCP servers reachable only through the gateway so that every call goes through it, as the spike's server does (internal ingress only). ([04](experiments/04-block-and-allow.md), [01](experiments/01-notes-mcp-server.md))

### Q3 — Granularity

Per server, and per tool once the server is under an enforced allowlist: a block and unblock leave an enforced allowlist of the current tools, after which enabling and disabling single tools takes effect for every client in 6–8 s. On a server LiteLLM treats as "all tools allowed" (an empty, unenforced list), saving a per-tool toggle sent no write to the gateway, so block and unblock such a server once first. Every control applies to the whole server for every key and team; per-team permissions stay managed in LiteLLM. ([03](experiments/03-connect-agent365.md), [04](experiments/04-block-and-allow.md), [05](experiments/05-tool-drift.md))

### Q4 — Drift

A changed tool description reaches every client at once, and Agent 365 shows the new text. A newly added tool follows the server's allowlist: on a server Agent 365 has blocked and unblocked (enforced allowlist), it is refused (403) until an admin enables it; on any other server it is available at once. ([05](experiments/05-tool-drift.md))

### Q6 — Runtime controls and audit

LiteLLM's Agent 365 guardrail sends every MCP tool call to Agent 365 for a Defender evaluation **as the signed-in user** (On-Behalf-Of with the gateway app's client secret): each call gets a verdict in LiteLLM's traces and an `ExecuteToolByGateway` record in Defender (`CloudAppEvents`) naming the user, the tool and the server, at a cost of 0.4–1.4 s per call. Calls without a user's Entra token are refused, so every client must send one next to its LiteLLM key. Verdicts were Allow for the inputs tested; a blocking policy was not configured in this spike. The records' `PlatformAgentId` is the LiteLLM key's alias, and they match the gateway's traces by time, user and tool. ([06](experiments/06-guardrail-and-audit.md))

### Q5 — Identity

Agent 365 manages the gateway with the LiteLLM key an admin gives it when connecting; its writes show as that key's user. A read-only key (`proxy_admin_viewer`) is enough for discovery, and blocking needs `proxy_admin`, which is full admin over the gateway: the key Agent 365 holds is the gateway's most sensitive credential and belongs in a vault with rotation. Rotation works without downtime (reconnect with a new key, then revoke the old one; to change the key, disconnect and reconnect); after the key is revoked, the admin center shows a banner and no longer lists the gateway's tools, while blocks already written stay in force. A user's identity reaches Agent 365 through the guardrail; it is not passed on to the MCP servers. ([07](experiments/07-agent365-identity.md), [06](experiments/06-guardrail-and-audit.md))

## What we would do differently

- Read the gateway's own logs and state from the start: they give the exact calls and times of each change.
- Put every server under Agent 365's tool control (block and unblock once) before relying on per-tool toggles, and re-check the allowlist after each server release.
- Re-check `allowed_tools` after an unblock if the gateway admin had restricted it: an unblock writes every current tool into it (07).
- Not tested: a Defender policy that blocks gateway tool calls, Entra agent identities for gateway callers, and per-team permissions alongside Agent 365's controls.
