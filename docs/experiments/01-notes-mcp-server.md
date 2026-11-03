# 01 — Notes MCP server

**Date:** 2026-11-01 · **Answers:** — (setup for Q1–Q6) · **Versions:** MCP Python SDK 2.3.0 (`MCPServer`, stateless streamable HTTP), Python 3.12, LiteLLM v1.106.6, Container Apps (Consumption), azurerm ~> 4.81

## Goal

Give the gateway one MCP server to govern, with a read tool and a write tool, reachable only through the gateway; register it in LiteLLM with one team and one virtual key, by a script that can be run again.

## Setup

- `infra/notes-mcp`: the spike's own layer: a storage account (shared keys disabled) for the notes table, the server's managed identity (Storage Table Data Contributor), and the container app with **internal ingress only** in the platform's Container Apps environment, pulling from the platform's registry with its pull identity.
- `services/notes-mcp`: the server (`server.py`), tools `add_note(text)` and `list_notes(limit)`, logic in `notes.py`; 19 tests, including MCP protocol tests over HTTP (initialize, `tools/list`, `tools/call`).
- `src/01_configure_gateway.py`: registers the server (internal URL, no auth), creates team `spike` (the model and the notes server), generates its virtual key into Key Vault (`litellm-key-spike`), then lists and calls the tools with that key.

## Steps

1. `azd provision notes-mcp --preview`, then `azd provision notes-mcp`.
2. `azd deploy notes-mcp` (remote build in the registry); the project's postdeploy hook provisions the layer again to switch from the placeholder's port to 8080.
3. `uv run python src/01_configure_gateway.py`, twice (idempotence).
4. Call the internal URL from outside the environment.

## Result

| Check | Result |
|---|---|
| Tools seen by the team through the gateway (`GET /mcp-rest/tools/list`) | `add_note`, `list_notes` |
| Write then read through the gateway (`POST /mcp-rest/tools/call`) | the note added is listed back, with its id and time |
| Second run of the script | server and team updated in place, key reused from Key Vault |
| The server's internal URL from the internet | 404 from the environment's ingress (the request never reaches the server) |
| Keys or passwords involved | none: the gateway reaches the server inside the environment, the server reaches its table with its managed identity |

What changed on the way:

- **Azure Functions (Flex Consumption) was dropped.** With a user-assigned identity, `azurerm_function_app_flex_consumption` writes its own `AzureWebJobsStorage` connection string (with an empty key), which takes precedence over the identity-based settings: the host failed with 403 on storage (open provider issues hashicorp/terraform-provider-azurerm#29149, #33211). Also, LiteLLM has no managed-identity authentication to MCP servers, so Functions would have needed its system key in LiteLLM. Container Apps with internal ingress avoids both.
- **Replacing a role assignment under a new Terraform address raced:** the new assignment (same role and scope) was created while the old one was being destroyed, and Azure answered 409 `RoleAssignmentExists`; a second apply finished. A `moved` block avoids it.
- **MCP Python SDK 2.x:** `FastMCP` is now `mcp.server.MCPServer`; an app's session manager runs once, so tests create one app per test (`create_app()`); DNS-rebinding protection is disabled explicitly (internal-only server).
- **Hook output:** azd ran the project's postdeploy hook (the port switched to 8080) without showing its lines in the captured output, as for the layer hooks in 00.

## Conclusion

The gateway now fronts one internal MCP server with a read and a write tool, for one team with one key: the setup the next experiments govern from Agent 365. Nothing but the gateway can reach the server, so blocks applied at the gateway cannot be bypassed by calling the server directly (to confirm in 04). Next: 02, the CopilotKit UI using the team's key.
