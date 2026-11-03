# The spike's chat UI (services/ui): a public container app where signed-in users chat with the model through the
# LiteLLM gateway, with the team's virtual key, and see each MCP tool call. Users sign in with Entra (MSAL in the
# browser); the app validates their tokens for its own API scope and lets in only the listed users (the deployer).

data "azurerm_client_config" "current" {}

locals {
  token = substr(sha1("${var.subscription_id}-${var.environment_name}"), 0, 8)

  extra_tag_pairs = [for pair in split(",", var.tags) : split("=", pair) if trimspace(pair) != ""]
  extra_tags = {
    for pair in local.extra_tag_pairs : trimspace(pair[0]) => trimspace(join("=", slice(pair, 1, length(pair))))
  }
  tags = merge(local.extra_tags, { "azd-env-name" = var.environment_name })

  app_name = "ca-ui-${local.token}"
  # Known before the app exists, so that the sign-in redirect and the app's own settings need no second pass.
  origin = "https://${local.app_name}.${var.container_apps_default_domain}"
  scope  = "Chat.Use"
}

resource "random_uuid" "chat_scope" {}

# One app registration: the single-page application users sign in to, and the API scope its server checks.
resource "azuread_application" "ui" {
  display_name     = "Notes chat (${var.environment_name})"
  sign_in_audience = "AzureADMyOrg"
  owners           = [data.azurerm_client_config.current.object_id]

  api {
    requested_access_token_version = 2

    oauth2_permission_scope {
      id                         = random_uuid.chat_scope.result
      value                      = local.scope
      type                       = "User"
      enabled                    = true
      admin_consent_display_name = "Use the notes chat"
      admin_consent_description  = "Allows the notes chat to call its server on behalf of the signed-in user."
      user_consent_display_name  = "Use the notes chat"
      user_consent_description   = "Allows the notes chat to call its server on your behalf."
    }
  }

  lifecycle {
    # The identifier URI and the redirect URIs are managed by their own resources below.
    ignore_changes = [identifier_uris, single_page_application]
  }
}

# api://<appId>: accepted by the tenant's default app management policy (custom URIs may be rejected).
resource "azuread_application_identifier_uri" "ui" {
  application_id = azuread_application.ui.id
  identifier_uri = "api://${azuread_application.ui.client_id}"
}

resource "azuread_application_redirect_uris" "ui" {
  application_id = azuread_application.ui.id
  type           = "SPA"
  redirect_uris  = ["${local.origin}/auth/callback", "http://localhost:3000/auth/callback"]
}

resource "azuread_service_principal" "ui" {
  client_id = azuread_application.ui.client_id
  owners    = [data.azurerm_client_config.current.object_id]
}

resource "azurerm_user_assigned_identity" "ui" {
  name                = "id-ui-${local.token}"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = local.tags
}

# Read access to the team's key only, not to the vault (which also holds the gateway's admin key).
resource "azurerm_role_assignment" "ui_team_key" {
  scope                = "${var.key_vault_id}/secrets/${var.team_key_secret_name}"
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.ui.principal_id
  principal_type       = "ServicePrincipal"
}
