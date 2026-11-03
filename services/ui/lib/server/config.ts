// Reads and checks the server settings from the environment; publicConfig is the part the browser may see.
import { z } from "zod";

const loopbackHosts = ["localhost", "127.0.0.1"];
const uuid = "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}";
const gatewayScopePattern = new RegExp(`^api://(${uuid})/([a-zA-Z][a-zA-Z0-9._]*)$`);

const schema = z.object({
  LITELLM_URL: z.string().url(),
  LITELLM_API_KEY: z.string().regex(/^\S+$/),
  LITELLM_MODEL: z.string().regex(/^[\w.:/-]+$/),
  UI_TENANT_ID: z.string().uuid(),
  UI_CLIENT_ID: z.string().uuid(),
  UI_SCOPE: z.string().regex(/^[a-zA-Z][a-zA-Z0-9._]*$/).default("Chat.Use"),
  UI_ORIGIN: z.string().url().default("http://localhost:3000"),
  ALLOWED_USER_OBJECT_IDS: z.string()
    .transform((value) => value.split(",").map((item) => item.trim()).filter(Boolean))
    .pipe(z.array(z.string().uuid()).min(1)),
  // Set when LiteLLM runs the Agent 365 guardrail, which needs the user's own token for the gateway:
  // api://<gateway app id>/<scope name>.
  GATEWAY_SCOPE: z.string().regex(gatewayScopePattern).optional(),
});

export type ChatConfig = z.infer<typeof schema>;

export function getConfig(env: Record<string, string | undefined> = process.env): ChatConfig {
  const parsed = schema.safeParse(env);
  if (!parsed.success) {
    // Names only: a value could be the key.
    throw new Error(`Chat configuration is missing or invalid: ${parsed.error.issues.map((issue) => issue.path.join(".")).join(", ")}`);
  }
  const config = parsed.data;
  const gateway = new URL(config.LITELLM_URL);
  if (gateway.protocol !== "https:" || gateway.username || gateway.password || gateway.search || gateway.hash) {
    throw new Error("LITELLM_URL must be an HTTPS URL without credentials, query or fragment.");
  }
  const origin = new URL(config.UI_ORIGIN);
  const isLoopbackHttp = origin.protocol === "http:" && loopbackHosts.includes(origin.hostname);
  if (origin.origin !== config.UI_ORIGIN || (origin.protocol !== "https:" && !isLoopbackHttp)) {
    throw new Error("UI_ORIGIN must be an HTTPS origin, or http://localhost or http://127.0.0.1 for development.");
  }
  return { ...config, LITELLM_URL: config.LITELLM_URL.replace(/\/+$/, "") };
}

export interface GatewayScope {
  audience: string;
  scopeName: string;
}

// The gateway's app id is the token audience; the scope name must be in the token's scp.
export function gatewayScope(config: ChatConfig): GatewayScope | undefined {
  const match = config.GATEWAY_SCOPE ? gatewayScopePattern.exec(config.GATEWAY_SCOPE) : null;
  return match ? { audience: match[1], scopeName: match[2] } : undefined;
}

export function publicConfig(config: ChatConfig) {
  return {
    tenantId: config.UI_TENANT_ID,
    clientId: config.UI_CLIENT_ID,
    scope: `api://${config.UI_CLIENT_ID}/${config.UI_SCOPE}`,
    origin: config.UI_ORIGIN,
    ...(config.GATEWAY_SCOPE ? { gatewayScope: config.GATEWAY_SCOPE } : {}),
  };
}
