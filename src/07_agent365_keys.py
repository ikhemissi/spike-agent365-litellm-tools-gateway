"""Experiment 07: the identity Agent 365 uses on the gateway: a least-privileged key, revocation and rotation.

    uv run python src/07_agent365_keys.py viewer         # user agent365-viewer (proxy_admin_viewer) + its key
    uv run python src/07_agent365_keys.py block <secret> # block the key kept in that Key Vault secret
    uv run python src/07_agent365_keys.py unblock <secret>
    uv run python src/07_agent365_keys.py rotate         # a new key for user agent365 (agent365-gateway-key-next)

Keys are kept in Key Vault and never printed; copy them into the admin center yourself. Prints UTC times.
"""

import os
import sys
from datetime import UTC, datetime

from gateway_admin import Gateway, azd_values, read_secret, store_secret

VIEWER_USER = "agent365-viewer"
VIEWER_SECRET = "agent365-viewer-key"
ADMIN_USER = "agent365"
NEXT_SECRET = "agent365-gateway-key-next"


def now() -> str:
    return f"{datetime.now(UTC):%H:%M:%S} UTC"


def ensure_user(admin: Gateway, user_id: str, role: str) -> None:
    users = admin.call("GET", "/user/list")
    existing = users.get("users", []) if isinstance(users, dict) else users
    if any(user.get("user_id") == user_id for user in existing):
        return
    admin.call("POST", "/user/new", {"user_id": user_id, "user_role": role, "auto_create_key": False})
    print(f"{now()} LiteLLM user '{user_id}' created ({role})")


def issue_key(admin: Gateway, vault: str, user_id: str, secret: str) -> None:
    if read_secret(vault, secret):
        print(f"{now()} key already in Key Vault ({secret})")
        return
    generated = admin.call("POST", "/key/generate", {"user_id": user_id, "key_alias": secret})
    store_secret(vault, secret, generated["key"])
    print(f"{now()} key for '{user_id}' generated and stored in Key Vault ({secret})")


def set_blocked(admin: Gateway, vault: str, secret: str, blocked: bool) -> None:
    key = read_secret(vault, secret)
    if not key:
        raise SystemExit(f"No key in Key Vault under {secret}")
    admin.call("POST", "/key/block" if blocked else "/key/unblock", {"key": key})
    print(f"{now()} key in {secret} {'blocked' if blocked else 'unblocked'}")


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in {"viewer", "block", "unblock", "rotate"}:
        raise SystemExit(__doc__)
    values = {**azd_values(), **os.environ}
    vault = values["PLATFORM_KEY_VAULT_NAME"]
    admin = Gateway(values["LITELLM_URL"], read_secret(vault, values["LITELLM_MASTER_KEY_SECRET_NAME"]))
    command = sys.argv[1]
    if command == "viewer":
        ensure_user(admin, VIEWER_USER, "proxy_admin_viewer")
        issue_key(admin, vault, VIEWER_USER, VIEWER_SECRET)
    elif command == "rotate":
        issue_key(admin, vault, ADMIN_USER, NEXT_SECRET)
    else:
        if len(sys.argv) < 3:
            raise SystemExit("Give the Key Vault secret holding the key, e.g. agent365-gateway-key")
        set_blocked(admin, vault, sys.argv[2], blocked=command == "block")
    print(f"Copy a key: az keyvault secret show --vault-name {vault} -n <secret> --query value -o tsv")


if __name__ == "__main__":
    main()
