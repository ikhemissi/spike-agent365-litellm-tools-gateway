# 07 — The identity Agent 365 uses on the gateway

**Date:** 2026-11-02 · **Answers:** Q5 · **Versions:** Microsoft 365 admin center (Agents → Settings → Gateways, preview), LiteLLM v1.106.6

## Goal

Find out which rights the key Agent 365 holds needs, what happens when that key is rotated or revoked, and how a block interacts with the gateway's own tool restrictions.

## Setup

- `src/07_agent365_keys.py`: a read-only LiteLLM user `agent365-viewer` (`proxy_admin_viewer`) with its key; a second key for user `agent365` (`proxy_admin`) for rotation; blocking and unblocking a key. Keys only in Key Vault; the user copied them into the admin center.
- Gateway access log (live console log) and `src/04_snapshot.py`.

## Steps and result

| Time (UTC) | Step | Observed |
|---|---|---|
| ≈17:55 | Reconnect the gateway with the **read-only** key (to change the key: disconnect and reconnect) | discovery works: both servers and the notes server's 3 tools listed |
| 17:57:37, 17:57:41 | Block `notes_readonly` with the read-only key | Agent 365 sends `PUT /v1/mcp/server`; LiteLLM answers **403** "user not allowed to access this route, role= proxy_admin_viewer"; the portal reports the change as not applied; LiteLLM's state unchanged |
| ≈18:01 | Reconnect with a **new** admin key; block the **old** key (18:01:33) | Block (≈18:01) and Unblock (18:02:09) of `notes_readonly` succeed with the new key: rotation without downtime once the new key is connected |
| 18:02:09 | Effect of that unblock | `notes_readonly`, restricted by the gateway admin to `list_notes`, now allows **`add_note`, `list_notes`, `count_notes`** (enforced): the unblock wrote every tool the server has into `allowed_tools`, the write tool included |
| 18:03:06 | Block the key Agent 365 holds (**revocation**) | its next read gets **401**; the Tools registry shows "LiteLLM gateway tools couldn't be loaded. Other available tools are still shown." and no longer lists the LiteLLM servers; blocks already written stay enforced in LiteLLM |
| 18:05:08 | Unblock the new key | connection restored (the old key stays blocked) |

## Conclusion

**Q5 (identity):** Agent 365 acts on the gateway with whatever LiteLLM key an admin gives it at connection time, and its writes show as that key's user (`updated_by`). Reading (discovery) works with a read-only key, and **blocking needs a `proxy_admin` key**, which in LiteLLM is full admin over every key, team, budget and server: there is no narrower role for "manage MCP server tools", so the key Agent 365 holds is the most sensitive credential of the gateway. The key is changed by disconnecting and reconnecting, it can be rotated without downtime (connect the new key, then revoke the old one), and after it is revoked the admin center shows a banner and no longer lists the gateway's tools, while the blocks already written stay in force. A user's identity does not take part in these management calls; it reaches Agent 365 only through the guardrail ([06](06-guardrail-and-audit.md)).

**After an unblock:** an unblock writes every current tool into the server's `allowed_tools` (here, `add_note` was allowed again on the read-only server). Re-check `allowed_tools` after an unblock if the gateway admin had restricted it.
