// The settings the server accepts, and the part the browser is given.
import assert from "node:assert/strict";
import { test } from "node:test";
import { gatewayScope, getConfig, publicConfig } from "../lib/server/config";
import { environment, id } from "./helpers";

test("reads the settings, with defaults for the scope and the development origin", () => {
  const config = getConfig(environment);
  assert.equal(config.LITELLM_URL, "https://litellm.example.com");
  assert.equal(config.UI_SCOPE, "Chat.Use");
  assert.equal(config.UI_ORIGIN, "http://localhost:3000");
  assert.deepEqual(config.ALLOWED_USER_OBJECT_IDS, [id(5), id(6)]);
});

test("the browser gets the sign-in settings only, never the gateway or its key", () => {
  assert.deepEqual(publicConfig(getConfig({ ...environment, UI_ORIGIN: "https://chat.example.com" })), {
    tenantId: id(1), clientId: id(2), scope: `api://${id(2)}/Chat.Use`, origin: "https://chat.example.com",
  });
});

test("without GATEWAY_SCOPE the guardrail settings are off", () => {
  assert.equal(gatewayScope(getConfig(environment)), undefined);
});

test("with GATEWAY_SCOPE the browser gets the scope, and the server the gateway's app id and scope name", () => {
  const config = getConfig({ ...environment, GATEWAY_SCOPE: `api://${id(3)}/Tools.Use` });
  assert.equal(publicConfig(config).gatewayScope, `api://${id(3)}/Tools.Use`);
  assert.deepEqual(gatewayScope(config), { audience: id(3), scopeName: "Tools.Use" });
});

test("accepts HTTPS origins and loopback HTTP origins for development", () => {
  for (const origin of ["https://chat.example.com", "http://localhost:3000", "http://127.0.0.1:3000"]) {
    assert.equal(getConfig({ ...environment, UI_ORIGIN: origin }).UI_ORIGIN, origin);
  }
});

for (const [label, overrides] of [
  ["an HTTP gateway", { LITELLM_URL: "http://litellm.example.com" }],
  ["a gateway URL with credentials", { LITELLM_URL: "https://user:pass@litellm.example.com" }],
  ["a missing key", { LITELLM_API_KEY: undefined }],
  ["a missing model", { LITELLM_MODEL: undefined }],
  ["a tenant that is not a GUID", { UI_TENANT_ID: "contoso.onmicrosoft.com" }],
  ["an HTTP origin that is not loopback", { UI_ORIGIN: "http://chat.example.com" }],
  ["an origin with a path", { UI_ORIGIN: "https://chat.example.com/app" }],
  ["an empty allowed-user list", { ALLOWED_USER_OBJECT_IDS: " , " }],
  ["an allowed user that is not a GUID", { ALLOWED_USER_OBJECT_IDS: `${id(5)},someone@example.com` }],
  ["a gateway scope whose app id is not a GUID", { GATEWAY_SCOPE: "api://litellm-gateway/Tools.Use" }],
  ["a gateway scope that is not an api:// scope", { GATEWAY_SCOPE: `https://${id(3)}/Tools.Use` }],
  ["a gateway scope without a scope name", { GATEWAY_SCOPE: `api://${id(3)}` }],
] as const) {
  test(`refuses ${label}`, () => {
    assert.throws(() => getConfig({ ...environment, ...overrides }));
  });
}

test("errors name the setting, never its value", () => {
  assert.throws(() => getConfig({ ...environment, LITELLM_API_KEY: "sk-secret value" }), (error: Error) =>
    error.message.includes("LITELLM_API_KEY") && !error.message.includes("sk-secret"));
});
