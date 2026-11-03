# Retest plan

What to run again when a product, an SDK or a policy changes, so that the findings stay true.

| Experiment | Retest when | How | Last run |
|---|---|---|---|
| [00](experiments/00-environment.md) | LiteLLM image, azd or Terraform providers change | `azd provision --preview` per layer; readiness after more than an hour (database token refresh) | 2026-11-02 |
| [03](experiments/03-connect-agent365.md) | The admin center's Gateways or Tools pages change (preview) | reconnect; time discovery in the gateway log; register a new server (`src/03_add_readonly_server.py`) | 2026-11-02 |
| [04](experiments/04-block-and-allow.md) | Agent 365 controls or LiteLLM's MCP permissions change | `src/04_probe.py` and `src/04_snapshot.py` around Block, Unblock and a tool toggle on a server that was never blocked | 2026-11-02 |
| [05](experiments/05-tool-drift.md) | Agent 365's tool management changes (preview) | change a description and add a tool; `src/05_tools_seen.py`; note how the portal shows each change | 2026-11-02 |
| [06](experiments/06-guardrail-and-audit.md) | LiteLLM's agent_365 guardrail, Defender real-time protection or the ExecuteToolByGateway schema change; a Defender policy for gateway tool calls is to be tested | `src/06_guarded_calls.py` with and without the guardrail; Advanced Hunting query; compare the recorded fields with 06 | 2026-11-02 |
| [07](experiments/07-agent365-identity.md) | LiteLLM adds finer admin roles; the admin center's gateway connection settings change | `src/07_agent365_keys.py` (viewer, rotate, block/unblock); check what an unblock writes into `allowed_tools` | 2026-11-02 |
