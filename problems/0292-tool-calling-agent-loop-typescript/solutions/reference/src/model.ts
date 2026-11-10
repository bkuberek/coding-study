// The chat model's API, as vendors/model/API.md describes it: one request for each step of a
// conversation, with the whole conversation so far and the tools on offer. A reply this code cannot
// read is the model failing, never a reason to guess.

const MODEL_URL = process.env.MODEL_URL;
const MODEL_API_KEY = process.env.MODEL_API_KEY;
const MODEL_NAME = process.env.MODEL_NAME;

/** A call the model asks for. `arguments` is JSON text the model wrote, which nothing has checked. */
export type ToolCall = {
  id: string;
  type: "function";
  function: { name: string; arguments: string };
};

export type AssistantMessage = { role: "assistant"; content: string | null; tool_calls?: ToolCall[] };

export type Message =
  | { role: "system" | "user"; content: string }
  | AssistantMessage
  | { role: "tool"; tool_call_id: string; content: unknown };

export type ToolSpec = {
  type: "function";
  function: { name: string; description: string; parameters: object };
};

export type Usage = { prompt_tokens: number; completion_tokens: number };

export type ModelReply = { message: AssistantMessage; usage: Usage };

/** The model did not answer, or answered something that is not a reply. */
export class ModelUnavailable extends Error {}

type Fields = Record<string, unknown>;

function isFields(value: unknown): value is Fields {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isTokenCount(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value) && value >= 0;
}

function isToolCall(value: unknown): value is ToolCall {
  if (!isFields(value) || typeof value.id !== "string" || !isFields(value.function)) {
    return false;
  }
  return typeof value.function.name === "string" && typeof value.function.arguments === "string";
}

function isAssistantMessage(value: unknown): value is AssistantMessage {
  if (!isFields(value) || value.role !== "assistant") {
    return false;
  }
  const { content, tool_calls: calls } = value;
  const readable = content === null || content === undefined || typeof content === "string";
  return readable && (calls === undefined || (Array.isArray(calls) && calls.every(isToolCall)));
}

function isUsage(value: unknown): value is Usage {
  return isFields(value) && isTokenCount(value.prompt_tokens) && isTokenCount(value.completion_tokens);
}

/** The reply in a body, or ModelUnavailable when the body is not one. */
function replyFrom(body: unknown): ModelReply {
  const choice = isFields(body) && Array.isArray(body.choices) ? body.choices[0] : undefined;
  const message = isFields(choice) ? choice.message : undefined;
  if (!isFields(body) || !isAssistantMessage(message) || !isUsage(body.usage)) {
    throw new ModelUnavailable("the model's reply is not one its API documents");
  }
  return { message, usage: body.usage };
}

/** Sends the conversation so far and the tools on offer, and returns the model's next message. */
export async function chat(messages: Message[], tools: ToolSpec[]): Promise<ModelReply> {
  let response: Response;
  let body: unknown;
  try {
    response = await fetch(`${MODEL_URL}/v1/chat/completions`, {
      method: "POST",
      headers: { Authorization: `Bearer ${MODEL_API_KEY}`, "Content-Type": "application/json" },
      body: JSON.stringify({ model: MODEL_NAME, messages, tools }),
    });
    body = await response.json();
  } catch (error) {
    throw new ModelUnavailable("the model did not answer with JSON", { cause: error });
  }
  if (!response.ok) {
    throw new ModelUnavailable(`the model answered ${response.status}`);
  }
  return replyFrom(body);
}
