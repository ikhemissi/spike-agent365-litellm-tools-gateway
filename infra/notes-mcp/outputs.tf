# Outputs become azd environment values (prefixed NOTES_MCP_). The URL is internal: only apps of the Container Apps
# environment resolve it.

output "NOTES_MCP_APP_NAME" { value = azurerm_container_app.notes.name }
output "NOTES_MCP_URL" { value = "https://${azurerm_container_app.notes.ingress[0].fqdn}/mcp" }
output "NOTES_MCP_STORAGE_NAME" { value = azurerm_storage_account.notes.name }
