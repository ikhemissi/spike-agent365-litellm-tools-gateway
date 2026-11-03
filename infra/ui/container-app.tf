# The UI's container app. Until azd deploys the service it runs a placeholder image on port 80; the project's
# postdeploy hook provisions this layer again to switch to the app's port and add its health probe.

locals {
  placeholder_image = "mcr.microsoft.com/k8se/quickstart:latest"
  image_deployed    = var.image != ""
  port              = 3000

  ui_env = {
    LITELLM_URL             = var.litellm_url
    LITELLM_MODEL           = var.model
    UI_TENANT_ID            = data.azurerm_client_config.current.tenant_id
    UI_CLIENT_ID            = azuread_application.ui.client_id
    UI_SCOPE                = local.scope
    UI_ORIGIN               = local.origin
    ALLOWED_USER_OBJECT_IDS = data.azurerm_client_config.current.object_id
  }
  # The user's token for the gateway goes with every chat request when the guardrail layer exists (experiment 06).
  gateway_env = var.gateway_scope == "" ? {} : { GATEWAY_SCOPE = var.gateway_scope }
}

resource "azurerm_container_app" "ui" {
  name                         = local.app_name
  resource_group_name          = var.resource_group_name
  container_app_environment_id = var.container_app_environment_id
  revision_mode                = "Single"
  workload_profile_name        = "Consumption"
  # azd finds the app of the ui service through this tag.
  tags = merge(local.tags, { "azd-service-name" = "ui" })

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.ui.id, var.acr_pull_identity_id]
  }

  registry {
    server   = var.registry_server
    identity = var.acr_pull_identity_id
  }

  # The team's LiteLLM key, resolved from Key Vault by the app's identity: the gateway authenticates callers with
  # its own keys (LiteLLM OSS has no usable Entra authentication for callers).
  secret {
    name                = "litellm-api-key"
    key_vault_secret_id = "${var.key_vault_uri}secrets/${var.team_key_secret_name}"
    identity            = azurerm_user_assigned_identity.ui.id
  }

  ingress {
    external_enabled = true
    target_port      = local.image_deployed ? local.port : 80
    transport        = "auto"
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = 1
    max_replicas = 1

    container {
      name   = "ui"
      image  = local.image_deployed ? var.image : local.placeholder_image
      cpu    = 0.5
      memory = "1Gi"

      dynamic "env" {
        for_each = merge(local.ui_env, local.gateway_env)
        content {
          name  = env.key
          value = env.value
        }
      }

      env {
        name        = "LITELLM_API_KEY"
        secret_name = "litellm-api-key"
      }

      dynamic "readiness_probe" {
        for_each = local.image_deployed ? [1] : []
        content {
          transport        = "HTTP"
          port             = local.port
          path             = "/api/health"
          interval_seconds = 10
        }
      }
    }
  }

  lifecycle {
    # azd deploy changes the image between two provisions; the next provision passes the same image back.
    ignore_changes = [template[0].container[0].image]
  }

  depends_on = [azurerm_role_assignment.ui_team_key]
}
