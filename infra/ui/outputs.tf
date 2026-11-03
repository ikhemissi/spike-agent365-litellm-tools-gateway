# Outputs become azd environment values (prefixed UI_). No secrets.

output "UI_URL" { value = "https://${azurerm_container_app.ui.ingress[0].fqdn}" }
output "UI_APP_NAME" { value = azurerm_container_app.ui.name }
output "UI_CLIENT_ID" { value = azuread_application.ui.client_id }
