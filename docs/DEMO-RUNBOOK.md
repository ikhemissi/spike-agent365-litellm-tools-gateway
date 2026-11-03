# Demo runbook

A step-by-step script to show the results, written so that someone else can run it. About 15 minutes.

## Before the demo

- [ ] Environment up: `curl -s "$(azd env get-value LITELLM_URL)/health/readiness"` → `"db":"connected"`, and `curl -s "$(azd env get-value UI_URL)/api/health"` → `ok`.
- [ ] The gateway connected in the Microsoft 365 admin center (Agents → Settings → Gateways → LiteLLM gateway) with the key in Key Vault `agent365-gateway-key-next`; Agents → Tools → LiteLLM lists `notes` and `notes_readonly`.
- [ ] `notes` available with all its tools enabled; the Agent 365 guardrail on (`uv run python src/06_configure_guardrail.py`).
- [ ] Tabs open, signed in as a Global Administrator (PIM role active): the chat UI (`azd env get-value UI_URL`), Agents → Tools → LiteLLM → notes, Defender Advanced Hunting.
- [ ] A terminal with `uv run python src/04_probe.py demo --interval 5 --minutes 20 --server-id <notes server id>` running (the id: `uv run python src/04_snapshot.py demo`).

## Steps

| # | Do | Show | Say |
|---|---|---|---|
| 1 | In the chat: "Add a note: demo", then "List the last 2 notes" | the answer, then the folded tool lines | The chat reaches an internal MCP server only through the LiteLLM gateway, with the team's key and the user's token. |
| 2 | Agents → Tools → LiteLLM | the servers and tools discovered from LiteLLM | Agent 365 reads the gateway with a LiteLLM admin key; new servers appear within about a minute. |
| 3 | Block `notes` | the probe switching to refused within seconds; the chat answering that the tool is unavailable | Block writes an enforced, empty tool allowlist in LiteLLM: every client through the gateway is refused within about 2 s. |
| 4 | Unblock, then disable `add_note` only | the probe: `add_note` gone, `list_notes` still ok | Per-tool control applies once a server has been blocked and unblocked; it acts for every team. |
| 5 | Advanced Hunting: `CloudAppEvents \| where ActionType == "ExecuteToolByGateway" \| take 20` | records with the user, tool and server | The guardrail evaluates every tool call as the signed-in user and records the user, the tool and the server. |
| 6 | Back to the slides | the findings summary | What was observed, what to check (`allowed_tools` after an unblock, tool descriptions after a server release), and keeping the `proxy_admin` key in a vault with rotation. |

Restore after the demo: re-enable `add_note`, check the probe shows both tools.

## If something fails

- Tools page shows "LiteLLM gateway tools couldn't be loaded": the key Agent 365 holds is blocked or wrong; check `uv run python src/07_agent365_keys.py` and reconnect.
- Per-tool toggles apply once the server is under an enforced allowlist (block, then unblock the server once).
- The chat's tool calls are refused with "no Entra bearer token": sign in again (the gateway token expired) or check `GATEWAY_SCOPE`.
- Fallback: the probe CSVs and snapshots in `docs/experiments/assets/`, and the tables in the experiment pages.
