# Governing LiteLLM MCP servers with Agent 365

**Question:** When a LiteLLM gateway is connected to the Agent 365 tools gateway, what is governed: which calls a block stops and how fast, at what granularity, how new or changed MCP servers are noticed, with which identity, which controls we have in Agent 365, and with which audit records?

**Time box:** 2 days (extended for 05–07) · **Status:** done — see [the findings](docs/FINDINGS.md)

| Document | Content |
|---|---|
| [Questions](docs/QUESTIONS.md) | What the spike must answer, and the status of each question |
| [Experiments](docs/experiments/README.md) | One file per experiment, numbered |
| [Findings](docs/FINDINGS.md) | The answers, with links to the evidence |
| [Retest plan](docs/RETEST-PLAN.md) | What to run again when a product changes |
| [Demo runbook](docs/DEMO-RUNBOOK.md) | How to show the results |

## Environment

The infrastructure is a set of azd layers (`infra/<layer>/`, one Terraform root each): `azure-platform`, `foundry-model`, `postgres` and `litellm-gateway`. Each layer's README-level notes are at the top of its `main.tf`.

```bash
az login && azd auth login
azd env new spike-agent365-litellm-tools-gateway --location francecentral
azd env set RESOURCE_TAGS "key=value,key=value"   # tags your tenant's policies require, if any
azd hooks run preprovision                        # remote state backend (run hooks before a preview)
azd provision --preview                           # read the plan of every layer before applying
azd provision
```

The gateway: `azd env get-value LITELLM_URL`; its admin UI is at `/ui` (user `admin`), the admin key is in Key Vault:

```bash
az keyvault secret show --vault-name "$(azd env get-value PLATFORM_KEY_VAULT_NAME)" -n litellm-master-key --query value -o tsv
```

Tear it down when the spike ends: `azd down --purge`. The spike's environment was torn down on 2026-11-02; the [demo runbook](docs/DEMO-RUNBOOK.md) and the [retest plan](docs/RETEST-PLAN.md) start from a new one.

The spike adds its own layer and service: the notes MCP server on Container Apps (`infra/notes-mcp`, `services/notes-mcp`), deployed with `azd deploy notes-mcp`, then registered in the gateway with `uv run python src/01_configure_gateway.py`. The server has internal ingress only: the gateway reaches it inside the Container Apps environment, nothing outside can, so no key is involved.

## Run the experiments' code

```bash
uv sync
uv run python src/<script>.py
```
