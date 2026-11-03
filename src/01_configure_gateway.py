"""Experiment 01: configures the LiteLLM gateway for the spike, then checks it with the team's key.

- registers the notes MCP server at its internal URL (reachable only inside the Container Apps environment: no key);
- creates one team ("spike") allowed to use that server and the model;
- creates one virtual key for the team, kept in Key Vault (litellm-key-spike) for the UI;
- lists the tools and calls both with the team's key.

Idempotent. Reads the azd environment; uses your Azure CLI sign-in (Key Vault secrets officer).
Never prints a key.
    uv run python src/01_configure_gateway.py
"""

import json
import os

from gateway_admin import Gateway, azd_values, read_secret, store_secret

SERVER_NAME = "notes"
TEAM_ALIAS = "spike"
TEAM_KEY_SECRET = "litellm-key-spike"


def ensure_server(admin: Gateway, mcp_url: str) -> str:
    """Creates or updates the notes MCP server; returns its id."""
    settings = {
        "server_name": SERVER_NAME,
        "alias": SERVER_NAME,
        "description": "Team notes: a read tool (list_notes) and a write tool (add_note).",
        "url": mcp_url,
        "transport": "http",
        # Internal ingress is the access control: only apps of the environment can reach the server.
        "auth_type": "none",
    }
    existing = [server for server in admin.call("GET", "/v1/mcp/server") if server.get("server_name") == SERVER_NAME]
    if existing:
        server_id = existing[0]["server_id"]
        admin.call("PUT", "/v1/mcp/server", {"server_id": server_id, **settings})
        print(f"MCP server '{SERVER_NAME}' updated ({server_id})")
        return server_id
    created = admin.call("POST", "/v1/mcp/server", settings)
    print(f"MCP server '{SERVER_NAME}' created ({created['server_id']})")
    return created["server_id"]


def ensure_team(admin: Gateway, server_id: str, model: str) -> str:
    """Creates or updates the team allowed to use the notes server and the model; returns its id."""
    permissions = {"models": [model], "object_permission": {"mcp_servers": [server_id]}}
    teams = admin.call("GET", "/team/list")
    existing = [team for team in teams if team.get("team_alias") == TEAM_ALIAS]
    if existing:
        team_id = existing[0]["team_id"]
        admin.call("POST", "/team/update", {"team_id": team_id, **permissions})
        print(f"Team '{TEAM_ALIAS}' updated ({team_id})")
        return team_id
    created = admin.call("POST", "/team/new", {"team_alias": TEAM_ALIAS, **permissions})
    print(f"Team '{TEAM_ALIAS}' created ({created['team_id']})")
    return created["team_id"]


def ensure_team_key(admin: Gateway, vault: str, team_id: str) -> str:
    """The team's virtual key, from Key Vault, or generated and stored there."""
    key = read_secret(vault, TEAM_KEY_SECRET)
    if key:
        print(f"Team key found in Key Vault ({TEAM_KEY_SECRET})")
        return key
    generated = admin.call("POST", "/key/generate", {"team_id": team_id, "key_alias": f"{TEAM_ALIAS}-ui"})
    store_secret(vault, TEAM_KEY_SECRET, generated["key"])
    print(f"Team key generated and stored in Key Vault ({TEAM_KEY_SECRET})")
    return generated["key"]


def check_tools(team: Gateway, server_id: str) -> None:
    """Lists the tools the team sees, then adds a note and lists notes through the gateway."""
    listed = team.call("GET", f"/mcp-rest/tools/list?server_id={server_id}")
    tools = listed.get("tools", []) if isinstance(listed, dict) else listed
    names = [tool["name"] for tool in tools]
    print(f"Tools visible to the team: {names}")
    add = next(name for name in names if name.endswith("add_note"))
    list_ = next(name for name in names if name.endswith("list_notes"))
    added = team.call(
        "POST",
        "/mcp-rest/tools/call",
        {"server_id": server_id, "name": add, "arguments": {"text": "Experiment 01 check"}},
    )
    print(f"{add}: {json.dumps(added)[:300]}")
    found = team.call(
        "POST", "/mcp-rest/tools/call", {"server_id": server_id, "name": list_, "arguments": {"limit": 3}}
    )
    print(f"{list_}: {json.dumps(found)[:300]}")


def main() -> None:
    values = {**azd_values(), **os.environ}
    vault = values["PLATFORM_KEY_VAULT_NAME"]
    admin_key = read_secret(vault, values["LITELLM_MASTER_KEY_SECRET_NAME"])
    if not admin_key:
        raise SystemExit(
            "The gateway's admin key is missing from Key Vault: provision the litellm-gateway layer first."
        )

    admin = Gateway(values["LITELLM_URL"], admin_key)
    server_id = ensure_server(admin, values["NOTES_MCP_URL"])
    team_id = ensure_team(admin, server_id, values["FOUNDRY_MODEL_DEPLOYMENT_NAME"])
    team_key = ensure_team_key(admin, vault, team_id)
    check_tools(Gateway(values["LITELLM_URL"], team_key), server_id)


if __name__ == "__main__":
    main()
