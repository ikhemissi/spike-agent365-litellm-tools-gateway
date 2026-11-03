# Outputs become azd environment values (prefixed GUARDRAIL_). No secrets: the client secret stays in Key Vault.

output "GUARDRAIL_CLIENT_ID" { value = azuread_application.gateway.client_id }
output "GUARDRAIL_SCOPE" { value = "${azuread_application_identifier_uri.gateway.identifier_uri}/${local.scope}" }
output "GUARDRAIL_SECRET_NAME" { value = azurerm_key_vault_secret.gateway_client_secret.name }
