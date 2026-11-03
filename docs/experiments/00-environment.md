# 00 — Environment

**Date:** 2026-11-01 · **Versions:** azd 1.37.2, Terraform 1.15.8 (azurerm ~> 4.81, azapi ~> 2.13), LiteLLM `litellm-database` v1.106.6 (pinned by digest), OpenTelemetry collector contrib 0.162.0, PostgreSQL 18, model gpt-6-luna 2026-09-22 (DataZoneStandard, 50k tokens/min)

## Goal

Record the environment every experiment runs in, so that results can be compared and retested; check the points the layers could not verify before a real deployment.

## Setup

| Item | Value |
|---|---|
| Region | francecentral |
| Tenant | a test tenant whose policies require the opt-out tags (set through `RESOURCE_TAGS` in the azd environment) |
| Identities | the deployer (a user: Entra administrator of PostgreSQL, Key Vault secrets officer, Foundry user); the gateway's user-assigned managed identity (Foundry user, Key Vault secrets user, metrics publisher, owner of its database); a shared image-pull identity |
| Products and versions | see above |

Layers (`infra/<layer>/`, one Terraform root and state key each), provisioned in order, each previewed first:

| Layer | Resources | Apply time |
|---|---|---|
| azure-platform | 10 (resource group, Log Analytics, Application Insights, registry + pull identity, Key Vault, Container Apps environment, diagnostic setting) | 4 min 28 s |
| foundry-model | 7 (account, project, model, App Insights connection, roles) | 2 min 10 s |
| postgres | 4 (server, two firewall rules, Entra administrator) | 8 min 23 s |
| litellm-gateway | 8 (identity, roles, admin key in Key Vault, database, container app) | 3 min 40 s |

## Steps

1. `azd env new` with the region, `azd env set RESOURCE_TAGS …`.
2. `azd hooks run preprovision`: the project hook creates the Terraform state store; the foundry-model layer hook checks the model quota (50 available).
3. For each layer: `azd provision <layer> --preview`, read the plan (only additions), then `azd provision <layer>`.
4. Checks below.

## Result

| Check | Result |
|---|---|
| Layer hooks run from their layer folder (`run: bash ./hooks/…` in `azure.yaml`) | yes: the quota preflight and the gateway's postprovision hook ran |
| The Entra administrator can create the gateway identity's role and grant it the `public` schema | yes: role `id-litellm-…` exists; LiteLLM created its 98 tables, owned by that role |
| LiteLLM signs in to PostgreSQL with an Entra token (`AZURE_POSTGRESQL_AUTH`) | yes: `/health/readiness` → `{"status": "healthy", "db": "connected"}` |
| A model call through the gateway, keyless to Foundry | yes: `POST /v1/chat/completions` with the admin key → "gateway ok" |
| The database token is refreshed (more than an hour after start; revision started 17:49 UTC) | yes: at 20:35 UTC `/health/readiness` → `db: connected`, and database-backed admin calls (MCP server, team, key) succeeded |
| The postprovision hook's output appears in `azd provision <layer>` output | no: the hook ran but its lines were not in the captured output |

## Conclusion

The four layers deploy as designed, passwordless end to end (Foundry and PostgreSQL with the managed identity, the admin key only in Key Vault). The gateway stays connected to its database across token refreshes. Next: experiment 01 (the notes MCP server, team and key).
