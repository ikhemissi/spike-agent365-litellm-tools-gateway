# Experiment 06: what LiteLLM's Agent 365 guardrail needs in Entra. Before each MCP tool call the guardrail exchanges
# the caller's Entra token (audienced to this app registration) for an Agent 365 token (On-Behalf-Of, with this app's
# client secret), so that Microsoft Defender evaluates and records the call as that user.

data "azurerm_client_config" "current" {}

locals {
  scope = "Tools.Use"
  # Microsoft's Agent 365 resource application and its delegated scope (LiteLLM v1.106.6, agent_365 guardrail).
  agent365_app_id  = "ea9ffc3e-8a23-4a7d-836d-234d7c7565c1"
  agent365_scope   = "ThreatProtection.Evaluate.All"
  azure_cli_app_id = "04b07795-8ddb-461a-bbee-02f9e1bf7b46"
  # Clients that may ask for a gateway token without a consent prompt: the Azure CLI (tests) and the chat UI.
  preauthorized_clients = compact([local.azure_cli_app_id, var.ui_client_id])
}

# Fails the plan if the tenant has no Agent 365 service principal: the guardrail cannot work there.
data "azuread_service_principal" "agent365" {
  client_id = local.agent365_app_id
}

resource "random_uuid" "tools_scope" {}

resource "azuread_application" "gateway" {
  display_name     = "LiteLLM gateway (${var.environment_name})"
  sign_in_audience = "AzureADMyOrg"
  owners           = [data.azurerm_client_config.current.object_id]

  api {
    requested_access_token_version = 2

    oauth2_permission_scope {
      id                         = random_uuid.tools_scope.result
      value                      = local.scope
      type                       = "User"
      enabled                    = true
      admin_consent_display_name = "Use MCP tools through the gateway"
      admin_consent_description  = "Allows the application to call MCP tools through the gateway on behalf of the signed-in user."
      user_consent_display_name  = "Use MCP tools through the gateway"
      user_consent_description   = "Allows the application to call MCP tools through the gateway on your behalf."
    }
  }

  required_resource_access {
    resource_app_id = local.agent365_app_id
    resource_access {
      id   = data.azuread_service_principal.agent365.oauth2_permission_scope_ids[local.agent365_scope]
      type = "Scope"
    }
  }

  lifecycle {
    # The identifier URI and pre-authorized clients are managed by their own resources below.
    ignore_changes = [identifier_uris, api[0].known_client_applications]
  }
}

# api://<appId>: accepted by the tenant's default app management policy (custom URIs may be rejected).
resource "azuread_application_identifier_uri" "gateway" {
  application_id = azuread_application.gateway.id
  identifier_uri = "api://${azuread_application.gateway.client_id}"
}

resource "azuread_service_principal" "gateway" {
  client_id = azuread_application.gateway.client_id
  owners    = [data.azurerm_client_config.current.object_id]
}

resource "azuread_application_pre_authorized" "clients" {
  for_each             = toset(local.preauthorized_clients)
  application_id       = azuread_application.gateway.id
  authorized_client_id = each.value
  permission_ids       = [random_uuid.tools_scope.result]
}

# Tenant-wide admin consent for the On-Behalf-Of exchange (needs a Global or Privileged Role Administrator).
resource "azuread_service_principal_delegated_permission_grant" "agent365" {
  service_principal_object_id          = azuread_service_principal.gateway.object_id
  resource_service_principal_object_id = data.azuread_service_principal.agent365.object_id
  claim_values                         = [local.agent365_scope]
}

# Documented exception to passwordless: LiteLLM's On-Behalf-Of exchange needs a client secret. Kept in Key Vault and
# in LiteLLM's database (set by src/06_configure_guardrail.py); also in the Terraform state (Entra-protected).
resource "azuread_application_password" "gateway" {
  application_id = azuread_application.gateway.id
  display_name   = "LiteLLM Agent 365 guardrail"
}

resource "azurerm_key_vault_secret" "gateway_client_secret" {
  name         = "agent365-guardrail-client-secret"
  value        = azuread_application_password.gateway.value
  key_vault_id = var.key_vault_id
}
