// Calls LiteLLM's Responses API with the team key (and the user's gateway token when the Agent 365 guardrail is on)
// and LiteLLM's own MCP tool, and yields the streamed events.
// LiteLLM runs the MCP tools itself ("server_url": "litellm_proxy"); this app only shows what it reports.
import { z } from "zod";
import type { ChatConfig } from "./config";
import { ChatError, redactGatewayText } from "./errors";

export const instructions = "You help a team manage notes with the notes tools: add a note when asked, "
  + "list notes when asked, and say plainly when a tool fails or is refused. Keep answers short.";

// Lets the gateway expose every MCP server the team's key may use, and run their tools without asking.
export const litellmMcpTool = { type: "mcp", server_label: "litellm", server_url: "litellm_proxy", require_approval: "never" };

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

const itemSchema = z.object({
  id: z.string(),
  type: z.string(),
  name: z.string().optional(),
  status: z.string().optional(),
  arguments: z.string().optional(),
  output: z.string().nullish(),
  error: z.unknown().optional(),
}).passthrough();

const eventSchema = z.object({
  type: z.string(),
  delta: z.unknown().optional(),
  item_id: z.string().optional(),
  item: itemSchema.optional(),
  message: z.string().optional(),
  error: z.object({ message: z.string().optional(), code: z.string().nullish() }).passthrough().nullish(),
  response: z.object({
    status: z.string().optional(),
    error: z.object({ message: z.string().optional() }).passthrough().nullish(),
  }).passthrough().optional(),
}).passthrough();

export type ResponsesItem = z.infer<typeof itemSchema>;
export type ResponsesEvent = z.infer<typeof eventSchema>;

const maxEventSize = 1_048_576;

// Server-sent events: yields the data of each event; LiteLLM sends one JSON object per event and a final [DONE].
export async function* sseData(body: ReadableStream<Uint8Array>): AsyncGenerator<string> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let data: string[] = [];
  try {
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      let end;
      while ((end = buffer.indexOf("\n")) >= 0) {
        const line = buffer.slice(0, end).replace(/\r$/, "");
        buffer = buffer.slice(end + 1);
        if (!line && data.length) {
          yield data.join("\n");
          data = [];
        } else if (line.startsWith("data:")) {
          data.push(line.slice(5).replace(/^ /, ""));
        }
      }
      if (buffer.length + data.join("").length > maxEventSize) {
        throw new ChatError("gateway", "invalid_stream", "The gateway sent an oversized stream event.");
      }
      if (done) break;
    }
    if (data.length) yield data.join("\n");
  } finally {
    await reader.cancel();
    reader.releaseLock();
  }
}

async function refusal(response: Response): Promise<ChatError> {
  let detail = "";
  try {
    const body = await response.json();
    detail = [body?.error?.type, body?.error?.message].filter((part) => typeof part === "string").join(": ");
  } catch {
    // Not every refusal has a JSON body; the status alone still explains it.
  }
  const reason = detail ? ` ${redactGatewayText(detail)}` : "";
  return new ChatError("gateway", "gateway_refused", `The gateway refused the request (HTTP ${response.status}).${reason}`);
}

// Without a gateway token the team key is the bearer token, as before. With one, the Agent 365 guardrail reads the
// user's token from Authorization, so LiteLLM takes the team key from its own header instead.
function gatewayHeaders(config: ChatConfig, gatewayToken?: string): Record<string, string> {
  if (!gatewayToken) {
    return { Authorization: `Bearer ${config.LITELLM_API_KEY}`, "Content-Type": "application/json" };
  }
  return {
    "x-litellm-api-key": config.LITELLM_API_KEY,
    Authorization: `Bearer ${gatewayToken}`,
    "Content-Type": "application/json",
  };
}

export async function* streamResponses({
  config, messages, signal, gatewayToken, fetchImpl = fetch,
}: {
  config: ChatConfig; messages: ChatMessage[]; signal: AbortSignal; gatewayToken?: string; fetchImpl?: typeof fetch;
}): AsyncGenerator<ResponsesEvent> {
  const response = await fetchImpl(`${config.LITELLM_URL}/v1/responses`, {
    method: "POST", redirect: "error",
    headers: gatewayHeaders(config, gatewayToken),
    body: JSON.stringify({
      model: config.LITELLM_MODEL, stream: true, instructions, input: messages, tools: [litellmMcpTool],
    }),
    signal: AbortSignal.any([signal, AbortSignal.timeout(180_000)]),
  });
  if (!response.ok) throw await refusal(response);
  if (!response.body || !response.headers.get("content-type")?.includes("text/event-stream")) {
    await response.body?.cancel();
    throw new ChatError("gateway", "invalid_response", "The gateway did not return a Responses event stream.");
  }
  for await (const data of sseData(response.body)) {
    if (data === "[DONE]") return;
    let event;
    try {
      event = eventSchema.parse(JSON.parse(data));
    } catch {
      throw new ChatError("gateway", "invalid_stream", "The gateway sent an invalid Responses event.");
    }
    yield event;
  }
}
