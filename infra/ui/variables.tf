# azd passes every value of main.tfvars.json as a string, empty when the azd environment does not set it.

variable "environment_name" {
  description = "azd environment name (AZURE_ENV_NAME)."
  type        = string
}

variable "subscription_id" {
  description = "Target subscription (AZURE_SUBSCRIPTION_ID)."
  type        = string
}

variable "location" {
  description = "Region (AZURE_LOCATION)."
  type        = string
  default     = "francecentral"
}

variable "tags" {
  description = "Extra tags, as comma-separated key=value pairs (RESOURCE_TAGS). Empty: none."
  type        = string
  default     = ""
}

variable "resource_group_name" {
  description = "Resource group of the platform layer (AZURE_RESOURCE_GROUP)."
  type        = string

  validation {
    condition     = var.resource_group_name != ""
    error_message = "AZURE_RESOURCE_GROUP is empty: provision the azure-platform layer first."
  }
}

variable "container_app_environment_id" {
  description = "Container Apps environment of the platform layer (AZURE_CONTAINER_APPS_ENVIRONMENT_ID)."
  type        = string
}

variable "container_apps_default_domain" {
  description = "Its default domain (PLATFORM_CONTAINER_APPS_DEFAULT_DOMAIN), for the app's URL before the app exists."
  type        = string
}

variable "registry_server" {
  description = "Container registry of the platform layer (AZURE_CONTAINER_REGISTRY_ENDPOINT), where azd builds the image."
  type        = string
}

variable "acr_pull_identity_id" {
  description = "The platform's image-pull identity (PLATFORM_ACR_PULL_IDENTITY_ID)."
  type        = string
}

variable "key_vault_id" {
  description = "The platform's Key Vault (PLATFORM_KEY_VAULT_ID), holding the team's LiteLLM key."
  type        = string
}

variable "key_vault_uri" {
  description = "Its URI (PLATFORM_KEY_VAULT_URI)."
  type        = string
}

variable "team_key_secret_name" {
  description = "Key Vault secret with the LiteLLM virtual key the UI uses, created by src/01_configure_gateway.py."
  type        = string
  default     = "litellm-key-spike"
}

variable "litellm_url" {
  description = "The gateway (LITELLM_URL)."
  type        = string

  validation {
    condition     = startswith(var.litellm_url, "https://")
    error_message = "LITELLM_URL is empty or not HTTPS: provision the litellm-gateway layer first."
  }
}

variable "model" {
  description = "The model the UI asks the gateway for (FOUNDRY_MODEL_DEPLOYMENT_NAME)."
  type        = string
}

variable "image" {
  description = "Image deployed by azd (SERVICE_UI_IMAGE_NAME); empty before the first deployment."
  type        = string
  default     = ""
}

variable "gateway_scope" {
  description = "The gateway app's scope for the Agent 365 guardrail (GUARDRAIL_SCOPE, from the guardrail layer, which itself needs this layer's client id: provision ui again after guardrail). Empty: the UI sends no user token to the gateway."
  type        = string
  default     = ""
}
