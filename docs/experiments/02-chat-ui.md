# 02 — Chat UI on the gateway

**Date:** 2026-11-02 · **Answers:** — (demo surface for Q2–Q6) · **Versions:** LiteLLM v1.106.6 (Responses API), Next.js 16, CopilotKit 1.79.1 (runtime v2, AG-UI 1.0.2), MSAL browser 5, model gpt-6-luna

## Goal

A chat where a signed-in user works with the notes tools through the gateway, with each MCP tool call visible (arguments, result, or why it failed or was refused), so that the governance experiments show their effect where a user sees it.

## Setup

- `services/ui`: Next.js app adapted from the agentgateway sample. The server runs one AG-UI agent that calls LiteLLM's Responses API with the team's virtual key and LiteLLM's own MCP tool (`{"type": "mcp", "server_label": "litellm", "server_url": "litellm_proxy", "require_approval": "never"}`): LiteLLM decides which MCP servers the key may use and runs the tools; the app only shows what LiteLLM reports.
- `infra/ui`: one app registration (single-page app + API scope `Chat.Use`, v2 tokens), an identity allowed to read **only** the team key's secret in Key Vault (not the vault), and a public container app; only listed users (the deployer) get in.
- Sign-in: MSAL in the browser (tokens in memory only); the server validates issuer, audience, `azp`, `scp`, tenant and user.

## Steps

1. `azd provision ui --preview`, then `azd provision ui`.
2. `azd deploy ui` (remote build); the postdeploy hook switched the app to port 3000.
3. Checks without a browser: `/api/health`, `/api/config`, a chat request without a token.
4. In a browser (the user): sign in, "Add a note: hello from experiment 02", "List the last 3 notes".

## Result

| Check | Result |
|---|---|
| Health and public settings | `{"status":"ok"}`; tenant, client id, scope and origin |
| Chat request without a token | 401 |
| Sign-in, add a note, list notes, through the gateway | works; each MCP call shown as a card |
| Unit and contract tests | 44 passing (stream mapping with the event sequences seen live, auth rules, settings) |

What LiteLLM's Responses API returned (observed live with the team key; details in `services/ui/README.md`):

- Each tool call appears **twice**: first as the model's `function_call` item, then as LiteLLM's `mcp_call` item once it ran the tool, with its `output`. The UI shows only the `mcp_call`.
- A failed tool comes back as an `mcp_call` with `status: completed` and `error: null`: the failure is only in `output`, which starts with `Error executing tool` (LiteLLM also uses `Tool call blocked:` and `Tool call failed:`). The UI treats these prefixes as errors.
- Refusals before the model runs: an unknown key → 401 `token_not_found_in_db` (the message includes a masked key and its hash, removed by the UI); a model the team may not use → 403 `team_model_access_denied`.
- The model sometimes **repeated a tool call** (three `add_note` for one request) and once said the list tool "isn't available" although LiteLLM had run `list_notes`: LiteLLM's follow-up round may not give the model the tool results properly. To watch in 04 and 06 (a refusal could be misreported the same way); the user's own test showed no repetition.
- The checks added a few test notes to the shared notes table.

Display: the assistant's reply restates successful results, so the cards fold them (click to expand); errors stay open.

## Conclusion

The chat shows, for a signed-in user, every tool call the gateway runs and its outcome; refusals and tool errors are visible in the conversation. This is the surface for the governance experiments. Next: 03, connect the gateway in the Microsoft 365 admin center (needs a Global Administrator).
