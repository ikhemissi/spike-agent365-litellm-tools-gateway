"""Experiment 04: a snapshot of what the gateway enforces for MCP, to compare before and after an action in Agent 365.

For each MCP server: the tools LiteLLM exposes or hides and its approval status; for each team: the servers and tools
it may use. Saved to docs/experiments/assets/04-snapshot-<label>.json (no keys) and printed.
    uv run python src/04_snapshot.py before-block
"""

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from gateway_admin import Gateway, azd_values, read_secret

SERVER_FIELDS = [
    "server_name",
    "server_id",
    "allowed_tools",
    "disallowed_tools",
    "mcp_info",
    "approval_status",
    "allow_all_keys",
    "updated_at",
    "updated_by",
]
PERMISSION_FIELDS = ["mcp_servers", "mcp_access_groups", "mcp_tool_permissions", "blocked_tools"]
ASSETS = Path(__file__).resolve().parent.parent / "docs" / "experiments" / "assets"


def team_permissions(admin: Gateway, team_id: str) -> dict:
    """The team's MCP permissions; /team/list does not include them, /team/info does."""
    info = admin.call("GET", f"/team/info?team_id={team_id}")
    permission = (info.get("team_info") or {}).get("object_permission") or {}
    return {field: permission.get(field) for field in PERMISSION_FIELDS}


def snapshot(admin: Gateway) -> dict:
    # The list omits some fields (mcp_info, updated_by): read each server in full.
    listed = admin.call("GET", "/v1/mcp/server")
    servers = [admin.call("GET", f"/v1/mcp/server/{server['server_id']}") for server in listed]
    teams = admin.call("GET", "/team/list")
    return {
        "taken_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "servers": [{field: server.get(field) for field in SERVER_FIELDS} for server in servers],
        "teams": [
            {"team_alias": team.get("team_alias"), "object_permission": team_permissions(admin, team["team_id"])}
            for team in teams
        ],
    }


def main() -> None:
    label = sys.argv[1] if len(sys.argv) > 1 else "now"
    values = {**azd_values(), **os.environ}
    admin_key = read_secret(values["PLATFORM_KEY_VAULT_NAME"], values["LITELLM_MASTER_KEY_SECRET_NAME"])
    if not admin_key:
        raise SystemExit(
            "The gateway's admin key is missing from Key Vault: provision the litellm-gateway layer first."
        )
    state = snapshot(Gateway(values["LITELLM_URL"], admin_key))
    ASSETS.mkdir(parents=True, exist_ok=True)
    path = ASSETS / f"04-snapshot-{label}.json"
    path.write_text(json.dumps(state, indent=2) + "\n")
    print(json.dumps(state, indent=2))
    print(f"Saved to {path.relative_to(ASSETS.parent.parent.parent)}")


if __name__ == "__main__":
    main()
