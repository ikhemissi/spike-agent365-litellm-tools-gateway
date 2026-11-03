"""Experiment 03: registers a second MCP server in the gateway, to time how Agent 365 discovers a new server and to
see whether it shows LiteLLM's own tool restriction. "notes_readonly" points at the same notes server, but LiteLLM
exposes only its read tool (allowed_tools). Idempotent; prints the time of registration (UTC).
    uv run python src/03_add_readonly_server.py
"""

import os
from datetime import UTC, datetime

from gateway_admin import Gateway, azd_values, read_secret

# LiteLLM refuses "-" in server names.
SERVER_NAME = "notes_readonly"


def main() -> None:
    values = {**azd_values(), **os.environ}
    admin_key = read_secret(values["PLATFORM_KEY_VAULT_NAME"], values["LITELLM_MASTER_KEY_SECRET_NAME"])
    if not admin_key:
        raise SystemExit(
            "The gateway's admin key is missing from Key Vault: provision the litellm-gateway layer first."
        )
    admin = Gateway(values["LITELLM_URL"], admin_key)
    if any(server.get("server_name") == SERVER_NAME for server in admin.call("GET", "/v1/mcp/server")):
        print(f"MCP server '{SERVER_NAME}' already registered")
        return
    created = admin.call(
        "POST",
        "/v1/mcp/server",
        {
            "server_name": SERVER_NAME,
            "alias": SERVER_NAME,
            "description": "Team notes, read only: LiteLLM exposes list_notes only.",
            "url": values["NOTES_MCP_URL"],
            "transport": "http",
            "auth_type": "none",
            "allowed_tools": ["list_notes"],
        },
    )
    print(f"MCP server '{SERVER_NAME}' registered ({created['server_id']}) at {datetime.now(UTC):%H:%M:%S} UTC")


if __name__ == "__main__":
    main()
