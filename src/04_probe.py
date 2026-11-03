"""Experiment 04: probes what the team's key can do through the gateway, every few seconds, to time when an action
in Agent 365 takes effect for each kind of client:

- mcp_tools: the tools the gateway's MCP endpoint lists (what a coding agent sees);
- mcp_call: list_notes called over MCP;
- rest_call: list_notes called over LiteLLM's REST API (what an API client or the chat UI's gateway path uses).

Prints a line whenever a result changes, and writes every probe to docs/experiments/assets/04-probe-<label>.csv.
Read-only (list_notes). Stop with Ctrl+C, or after --minutes.
    uv run python src/04_probe.py block-server --interval 10 --minutes 30
"""

import argparse
import csv
import json
import os
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from gateway_admin import azd_values, read_secret

ASSETS = Path(__file__).resolve().parent.parent / "docs" / "experiments" / "assets"
SERVER = "notes"


def post(url: str, key: str, body: dict) -> tuple[int, str]:
    request = urllib.request.Request(
        url,
        method="POST",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()
    except OSError as error:
        return 0, str(error)


def mcp_result(text: str) -> dict:
    """The JSON-RPC message of an MCP answer, sent as server-sent events or as plain JSON."""
    lines = [line[5:].strip() for line in text.splitlines() if line.startswith("data:")]
    return json.loads(lines[-1] if lines else text)


def summary(status: int, text: str, ok: str) -> str:
    """A short, comparable outcome: the expected value, or the HTTP status and the start of the error."""
    if status != 200:
        return f"HTTP {status}: {text[:120]}"
    return ok


def probe_mcp_tools(gateway: str, key: str) -> str:
    status, text = post(f"{gateway}/mcp/", key, {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
    if status != 200:
        return summary(status, text, "")
    tools = mcp_result(text).get("result", {}).get("tools", [])
    return " ".join(sorted(tool["name"] for tool in tools)) or "(no tools)"


def probe_mcp_call(gateway: str, key: str) -> str:
    call = {"name": f"{SERVER}-list_notes", "arguments": {"limit": 1}}
    status, text = post(f"{gateway}/mcp/", key, {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": call})
    if status != 200:
        return summary(status, text, "")
    message = mcp_result(text)
    if "error" in message:
        return f"error: {json.dumps(message['error'])[:120]}"
    result = message.get("result", {})
    return "error: " + json.dumps(result.get("content"))[:120] if result.get("isError") else "ok"


def probe_rest_call(gateway: str, key: str, server_id: str) -> str:
    body = {"server_id": server_id, "name": "list_notes", "arguments": {"limit": 1}}
    status, text = post(f"{gateway}/mcp-rest/tools/call", key, body)
    if status != 200:
        return summary(status, text, "")
    return "error: " + text[:120] if '"isError": true' in text or '"isError":true' in text else "ok"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("label")
    parser.add_argument("--interval", type=int, default=10)
    parser.add_argument("--minutes", type=int, default=30)
    parser.add_argument("--server-id", required=True, help="Id of the notes server in LiteLLM (see 04_snapshot.py)")
    arguments = parser.parse_args()

    values = {**azd_values(), **os.environ}
    key = read_secret(values["PLATFORM_KEY_VAULT_NAME"], "litellm-key-spike")
    if not key:
        raise SystemExit("The team key is missing from Key Vault: run src/01_configure_gateway.py first.")
    gateway = values["LITELLM_URL"].rstrip("/")
    ASSETS.mkdir(parents=True, exist_ok=True)
    path = ASSETS / f"04-probe-{arguments.label}.csv"
    columns = ["time", "mcp_tools", "mcp_call", "rest_call"]
    previous: dict[str, str] = {}
    deadline = time.monotonic() + arguments.minutes * 60
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        while time.monotonic() < deadline:
            row = {
                "time": datetime.now(UTC).strftime("%H:%M:%S"),
                "mcp_tools": probe_mcp_tools(gateway, key),
                "mcp_call": probe_mcp_call(gateway, key),
                "rest_call": probe_rest_call(gateway, key, arguments.server_id),
            }
            writer.writerow(row)
            file.flush()
            changed = [column for column in columns[1:] if row[column] != previous.get(column)]
            if changed:
                print(row["time"], " | ".join(f"{column}: {row[column]}" for column in changed), flush=True)
            previous = row
            time.sleep(arguments.interval)
    print(f"Saved to {path}")


if __name__ == "__main__":
    main()
