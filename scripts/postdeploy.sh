#!/usr/bin/env bash
# azd postdeploy hook (project level): after the first deployment of a container app, the app still listens on the
# placeholder image's port, so its layer is provisioned once more to switch to the app's port and add its health
# probe. Apps already on their port, and apps not provisioned yet, are skipped.
set -euo pipefail
: "${AZURE_RESOURCE_GROUP:?}"

# Each deployed container app: the azd value with its name, and the layer that owns it.
APPS=("NOTES_MCP_APP_NAME:notes-mcp" "UI_APP_NAME:ui")

for entry in "${APPS[@]}"; do
  variable="${entry%%:*}"
  layer="${entry#*:}"
  app="${!variable:-}"
  [[ -n "$app" ]] || continue
  port="$(az containerapp show -n "$app" -g "$AZURE_RESOURCE_GROUP" --query properties.configuration.ingress.targetPort -o tsv)"
  image="$(az containerapp show -n "$app" -g "$AZURE_RESOURCE_GROUP" --query 'properties.template.containers[0].image' -o tsv)"
  if [[ "$port" == "80" && "$image" != mcr.microsoft.com/k8se/quickstart* ]]; then
    echo "First deployment of $app: provisioning the $layer layer again for its port and probe"
    azd provision "$layer" -e "$AZURE_ENV_NAME" --no-prompt
  fi
done
