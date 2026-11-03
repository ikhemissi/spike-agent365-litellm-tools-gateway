# Notes chat UI

A small Next.js chat ([CopilotKit](https://docs.copilotkit.ai) on [AG-UI](https://docs.ag-ui.com)) for the spike's
demos: a signed-in user asks for notes, and the assistant uses the **notes MCP server through the LiteLLM gateway**.
Every tool call is shown in the chat with its arguments and its result, or with the error or refusal that stopped it —
blocked calls are what the demos show.

```text
browser (MSAL sign-in) ──Bearer token──▶ /api/copilotkit (checks token, origin, size)
    ──team key (+ the user's gateway token with GATEWAY_SCOPE)──▶ LiteLLM POST /v1/responses with tool {type: mcp, server_url: litellm_proxy}
    ──▶ LiteLLM lists and runs the team's MCP tools itself ──▶ streamed events ──▶ AG-UI events ──▶ chat
```

The app never calls an MCP server: LiteLLM decides which tools exist for the team's key and runs them; the app shows
what LiteLLM reports. The team key stays on the server.

| Path | Role |
|---|---|
| `app/page.tsx`, `app/providers.tsx` | Sign-in (MSAL, popup) and the chat |
| `app/tool-call.tsx` | How a tool call is shown |
| `app/auth/callback/page.tsx` | Returns the sign-in popup's result to the page |
| `app/api/copilotkit/[[...slug]]/route.ts` | The CopilotKit runtime endpoint |
| `app/api/config/route.ts`, `app/api/health/route.ts` | Public sign-in settings; the container probe |
| `lib/server/handler.ts` | Origin check, sign-in, 128 KiB body limit, request ids, runs the agent |
| `lib/server/auth.ts` | Entra token validation: the sign-in token, and the gateway token when `GATEWAY_SCOPE` is set |
| `lib/server/agent.ts` | The `notes` agent: conversation in, AG-UI events out, errors as chat messages |
| `lib/server/litellm.ts` | The Responses API call and its event stream |
| `lib/server/responses-to-ag-ui.ts` | LiteLLM events → AG-UI events |
| `lib/tool-result.ts` | A tool result as the chat shows it (`ok` or `error`) |

## Settings

| Variable | Required | Meaning |
|---|---|---|
| `LITELLM_URL` | yes | The gateway, HTTPS (`azd env get-value LITELLM_URL`) |
| `LITELLM_API_KEY` | yes | The team's LiteLLM virtual key (Key Vault secret `litellm-key-spike`); server only |
| `LITELLM_MODEL` | yes | The model alias, e.g. `gpt-6-luna` (`azd env get-value FOUNDRY_MODEL_DEPLOYMENT_NAME`) |
| `UI_TENANT_ID` | yes | Entra tenant (GUID) |
| `UI_CLIENT_ID` | yes | The app registration used both as the SPA and as the API (GUID) |
| `UI_SCOPE` | no, `Chat.Use` | The delegated scope the API exposes; the browser asks for `api://{UI_CLIENT_ID}/{UI_SCOPE}` |
| `UI_ORIGIN` | no, `http://localhost:3000` | The page's origin: HTTPS, or `http://localhost` / `http://127.0.0.1` for development |
| `ALLOWED_USER_OBJECT_IDS` | yes | Comma-separated user object ids (GUIDs) allowed to chat |
| `GATEWAY_SCOPE` | no | Only when LiteLLM runs the Agent 365 guardrail: the gateway app registration's delegated scope, `api://{gateway app id}/{scope}` (see [Agent 365 guardrail](#agent-365-guardrail)) |

`/api/config` returns only `{tenantId, clientId, scope, origin}`, plus `gatewayScope` when `GATEWAY_SCOPE` is set.

**Sign-in rules** (`/api/copilotkit`): a `Bearer` token signed RS256 by the tenant (`https://login.microsoftonline.com/{tenant}/v2.0`),
audience `UI_CLIENT_ID`, with `exp`, `iat`, `oid`, `tid`, `azp` and `scp`; `tid` is the tenant, `azp` is `UI_CLIENT_ID`,
the token is delegated (no `idtyp: app`), `scp` contains `UI_SCOPE`, and `oid` is in `ALLOWED_USER_OBJECT_IDS`.
Otherwise 401 (no or invalid token) or 403 (wrong caller, scope or user). The app registration needs the SPA redirect
URI `{UI_ORIGIN}/auth/callback` and the exposed scope.

## Agent 365 guardrail

When LiteLLM runs Microsoft's Agent 365 guardrail on MCP tool calls, it needs to know **which user** is calling, not
only which team. A call to LiteLLM then carries two credentials:

| Header to LiteLLM | Credential | Proves |
|---|---|---|
| `x-litellm-api-key` | The team's LiteLLM key (`LITELLM_API_KEY`), from the server | Which team: models and MCP servers it may use |
| `Authorization: Bearer …` | The signed-in user's own Entra token for the gateway's app registration | Which user: the guardrail checks it on every tool call |

With only the team key in `Authorization`, LiteLLM refuses the tool calls ("the caller did not present an Entra
bearer token"). Set `GATEWAY_SCOPE` to turn this on; without it the app sends exactly what it sent before (the team
key in `Authorization`, no gateway token).

With `GATEWAY_SCOPE` set:

1. The browser, signed in as before, also gets a token for `GATEWAY_SCOPE` silently from MSAL (same account), and
   sends it on each chat request in `x-gateway-token`, next to the sign-in token in `Authorization`. The gateway's app
   registration pre-authorizes the chat's app on that scope, so no consent prompt is expected; if Entra still wants
   an interaction, **Renew sign-in** asks for it in the same popup flow.
2. `/api/copilotkit` checks the sign-in token as before, then requires `x-gateway-token`: signed RS256 by the tenant
   (same v2 issuer), audience the gateway app id from `GATEWAY_SCOPE`, `azp` this chat's app, delegated (no
   `idtyp: app`), `scp` containing the scope name, and the same `oid` and `tid` as the sign-in token. Otherwise 401
   (missing, invalid or expired) or 403 (wrong caller, scope or another user).
3. The agent calls LiteLLM with the team key in `x-litellm-api-key` and the gateway token in `Authorization`.

The gateway token is never logged, is not passed to the CopilotKit runtime, and is removed from gateway messages
shown in the chat.

## Run locally

Node 22 or later.

```bash
cd services/ui
npm ci
cp .env.example .env.local    # git-ignored: fill in the values, never commit the key
npm run dev                   # http://localhost:3000
```

To fill `LITELLM_API_KEY` without printing it, from the repository root:

```bash
echo "LITELLM_API_KEY=$(az keyvault secret show --vault-name "$(azd env get-value PLATFORM_KEY_VAULT_NAME)" \
  -n litellm-key-spike --query value -o tsv)" >> services/ui/.env.local
```

Checks: `npm run typecheck && npm run lint && npm test && npm run build`. The tests use the event sequences observed
live (`tests/helpers.ts`) and need no network.

The container (`Dockerfile`) runs the standalone server as the non-root `node` user on port 3000;
`GET /api/health` answers `{"status":"ok"}` without sign-in. Next.js and CopilotKit telemetry are disabled.

## What LiteLLM v1.106.6 streams

Request (checked live with the team key):

```json
POST {LITELLM_URL}/v1/responses
Authorization: Bearer <team key>
{ "model": "gpt-6-luna", "stream": true, "instructions": "...", "input": [{"role": "user", "content": "..."}],
  "tools": [{"type": "mcp", "server_label": "litellm", "server_url": "litellm_proxy", "require_approval": "never"}] }
```

The answer is `text/event-stream`: one JSON event per `data:` line, ending with `data: [DONE]`. Observed, for
"add a note, then list notes":

| Event | Meaning | In the chat |
|---|---|---|
| `response.created`, `response.in_progress` | Started | — |
| `response.output_item.added` (item `function_call`, name `notes-add_note`), `response.function_call_arguments.delta` / `.done`, `response.output_item.done` | The model asks for a tool | — (shown once, from the `mcp_call` below) |
| `response.mcp_list_tools.in_progress` / `.completed`, `response.output_item.done` (item `mcp_list_tools`, `server_label: litellm`, tool names prefixed with the server: `notes-add_note`, `notes-list_notes`) | LiteLLM lists the team's MCP tools (first round only) | — |
| `response.output_item.added` (item `mcp_call`: `id: mcp_…`, `name`, `arguments`, `status: in_progress`) | LiteLLM runs the tool | `TOOL_CALL_START` (name), `TOOL_CALL_ARGS`, `TOOL_CALL_END` |
| `response.mcp_call.in_progress`, `response.mcp_call_arguments.delta` / `.done`, `response.mcp_call.completed` | Progress of that call (LiteLLM sends these, and the `added` item above, together after the call ran) | — |
| `response.output_item.done` (item `mcp_call`, `status: completed`, `output`, `error` absent or `null`) | The tool's result | `TOOL_CALL_RESULT` |
| `response.output_item.added` / `.done` (item `reasoning`, encrypted) | Model reasoning | — |
| `response.output_item.added` (item `message`, `phase: commentary` or `final_answer`), `response.content_part.added`, `response.output_text.delta`, `response.output_text.done`, `response.content_part.done`, `response.output_item.done` | Assistant text; a response can hold several messages | `TEXT_MESSAGE_START`, `_CONTENT`, `_END` |
| `response.completed` (`response.status: completed`) | Finished | `RUN_FINISHED` |

**Failures:**

- **A tool that fails is still `status: completed`, with `error: null`.** The error is only in `output`: the notes
  server's own error gives `"Error executing tool list_notes"` (checked live with `limit: 500`); in LiteLLM's source
  (`litellm/responses/mcp/litellm_proxy_mcp_handler.py` at v1.106.6) a guardrail block gives `"Tool call blocked: …"`,
  a gateway `HTTPException` gives `"Tool call failed: …"`, and other exceptions `"Error executing tool: …"`. The app
  treats these prefixes (or a non-empty `error`, or `status: failed`) as an error result.
- **A refusal before the stream** is a JSON error with the HTTP status (checked live): an unknown key gives 401
  `token_not_found_in_db` (its message echoes a masked key and the key's hash: the app removes both), a model the
  team may not use gives 403 `team_model_access_denied`.
- **A failure during the stream** is an `error` event (`error: {type: "mcp_gateway_error", code, message}` in the
  source), or `response.failed` / `response.incomplete`; a stream that ends without `response.completed` is also a failure.

**Seen live:** the model often repeated a call (`add_note` three times for one request) and then answered that the
list tool "isn't available", although LiteLLM had run `list_notes` and returned notes. LiteLLM's follow-up round does
not seem to give the model the tool results the way it expects; worth an experiment before reading too much into the
model's text. The chat shows each call LiteLLM actually ran, so the repetition is visible.

## How tool calls appear

Each `mcp_call` LiteLLM ran is one card in the chat (`app/tool-call.tsx`, registered for every tool name with
CopilotKit's `renderToolCalls`): the tool name as the gateway names it (`notes-add_note`), the arguments, then the
result (green) or the error (red, marked `failed`). A tool error does not end the run: the model usually explains it.

A refusal or failure of the whole request (401/403 from the gateway, a stream error, a bad request) appears as an
assistant message starting with ⚠️, with the gateway's reason and a request id, and ends the run with `RUN_ERROR`. The
server logs only the request id, stage and code. Tool calls and their results stay in the chat; only the user's and
assistant's text is sent back to the gateway on the next turn.
