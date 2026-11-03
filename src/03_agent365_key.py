"""Experiment 03: the LiteLLM key Agent 365 holds for the gateway.

Creates a LiteLLM user "agent365" with the proxy-admin role and one key for it, kept in Key Vault
(agent365-gateway-key): Agent 365 discovers the gateway's MCP servers and writes team permissions with it. A key of
its own can be revoked without touching the gateway's master key, and its calls carry its name in LiteLLM's logs.
Idempotent. Never prints a key: copy it from Key Vault into the admin center yourself.
    uv run python src/03_agent365_key.py
"""

import os

from gateway_admin import Gateway, azd_values, read_secret, store_secret

USER_ID = "agent365"
KEY_SECRET = "agent365-gateway-key"


def ensure_user(admin: Gateway) -> None:
    users = admin.call("GET", "/user/list")
    existing = users.get("users", []) if isinstance(users, dict) else users
    if any(user.get("user_id") == USER_ID for user in existing):
        print(f"LiteLLM user '{USER_ID}' found")
        return
    admin.call(
        "POST",
        "/user/new",
        {"user_id": USER_ID, "user_alias": "Agent 365", "user_role": "proxy_admin", "auto_create_key": False},
    )
    print(f"LiteLLM user '{USER_ID}' created (proxy_admin)")


def ensure_key(admin: Gateway, vault: str) -> None:
    if read_secret(vault, KEY_SECRET):
        print(f"Key found in Key Vault ({KEY_SECRET})")
        return
    generated = admin.call("POST", "/key/generate", {"user_id": USER_ID, "key_alias": "agent365-gateway"})
    store_secret(vault, KEY_SECRET, generated["key"])
    print(f"Key generated and stored in Key Vault ({KEY_SECRET})")


def main() -> None:
    values = {**azd_values(), **os.environ}
    vault = values["PLATFORM_KEY_VAULT_NAME"]
    admin_key = read_secret(vault, values["LITELLM_MASTER_KEY_SECRET_NAME"])
    if not admin_key:
        raise SystemExit(
            "The gateway's admin key is missing from Key Vault: provision the litellm-gateway layer first."
        )
    admin = Gateway(values["LITELLM_URL"], admin_key)
    ensure_user(admin)
    ensure_key(admin, vault)
    print(f"\nGateway URL for the admin center: {values['LITELLM_URL']}")
    print(f"Key: az keyvault secret show --vault-name {vault} -n {KEY_SECRET} --query value -o tsv")


if __name__ == "__main__":
    main()
