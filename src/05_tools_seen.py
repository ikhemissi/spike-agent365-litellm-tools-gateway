"""Experiment 05: the notes server's tools as each side sees them, to detect drift: what Agent 365 reads (LiteLLM's
admin view, including disabled tools) and what the team's key is offered, with each tool's description.
    uv run python src/05_tools_seen.py
"""

import os
from datetime import UTC, datetime

from gateway_admin import Gateway, azd_values, read_secret

SERVER_ID = "7948a6d3-0cda-4adf-8f96-ee05ff3a9a0b"


def tools(gateway: Gateway, include_disabled: bool) -> list[dict]:
    query = f"/mcp-rest/tools/list?server_id={SERVER_ID}" + ("&include_disabled_tools=true" if include_disabled else "")
    listed = gateway.call("GET", query)
    return listed.get("tools", []) if isinstance(listed, dict) else listed


def show(title: str, found: list[dict]) -> None:
    print(f"{title}:")
    for tool in sorted(found, key=lambda tool: tool["name"]):
        print(f"  - {tool['name']}: {tool.get('description', '')}")


def main() -> None:
    values = {**azd_values(), **os.environ}
    vault = values["PLATFORM_KEY_VAULT_NAME"]
    admin = Gateway(values["LITELLM_URL"], read_secret(vault, values["LITELLM_MASTER_KEY_SECRET_NAME"]))
    team = Gateway(values["LITELLM_URL"], read_secret(vault, "litellm-key-spike"))
    print(f"{datetime.now(UTC):%H:%M:%S} UTC")
    show("Admin view, including disabled tools (what Agent 365 reads)", tools(admin, include_disabled=True))
    show("Offered to the team's key", tools(team, include_disabled=False))


if __name__ == "__main__":
    main()
