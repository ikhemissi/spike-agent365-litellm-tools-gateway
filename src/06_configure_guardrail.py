"""Experiment 06: turns LiteLLM's Agent 365 guardrail on for every MCP tool call (or off with --remove).

The guardrail sends each pending tool call to Agent 365, where Microsoft Defender evaluates it as the calling user
(On-Behalf-Of with the gateway app's client secret, from Key Vault into LiteLLM's database); fail_closed blocks tool
calls when Agent 365 cannot be reached. Idempotent. Never prints a secret.
    uv run python src/06_configure_guardrail.py [--remove]
"""

import os
import sys

from gateway_admin import Gateway, azd_values, read_secret

GUARDRAIL_NAME = "agent365"


def existing_guardrail_id(admin: Gateway) -> str | None:
    listed = admin.call("GET", "/guardrails/list")
    for guardrail in listed.get("guardrails", []):
        if guardrail.get("guardrail_name") == GUARDRAIL_NAME:
            return guardrail.get("guardrail_id")
    return None


def main() -> None:
    values = {**azd_values(), **os.environ}
    vault = values["PLATFORM_KEY_VAULT_NAME"]
    admin = Gateway(values["LITELLM_URL"], read_secret(vault, values["LITELLM_MASTER_KEY_SECRET_NAME"]))
    guardrail_id = existing_guardrail_id(admin)

    if "--remove" in sys.argv:
        if guardrail_id:
            admin.call("DELETE", f"/guardrails/{guardrail_id}")
            print(f"Guardrail '{GUARDRAIL_NAME}' removed")
        else:
            print(f"Guardrail '{GUARDRAIL_NAME}' was not configured")
        return
    if guardrail_id:
        print(f"Guardrail '{GUARDRAIL_NAME}' already configured ({guardrail_id})")
        return

    client_secret = read_secret(vault, values["GUARDRAIL_SECRET_NAME"])
    if not client_secret:
        raise SystemExit("The gateway app's client secret is missing from Key Vault: provision the guardrail layer.")
    created = admin.call(
        "POST",
        "/guardrails",
        {
            "guardrail": {
                "guardrail_name": GUARDRAIL_NAME,
                "litellm_params": {
                    "guardrail": "agent_365",
                    "mode": "pre_mcp_call",
                    "default_on": True,
                    "tenant_id": values["AZURE_TENANT_ID"],
                    "client_id": values["GUARDRAIL_CLIENT_ID"],
                    "client_secret": client_secret,
                    "unreachable_fallback": "fail_closed",
                },
                "guardrail_info": {"description": "Agent 365 / Defender evaluation of every MCP tool call."},
            }
        },
    )
    print(f"Guardrail '{GUARDRAIL_NAME}' configured ({created.get('guardrail_id')})")


if __name__ == "__main__":
    main()
