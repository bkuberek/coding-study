// The chat model's API, as vendors/model/API.md describes it: one request for each step of a
// conversation, with the whole conversation so far and the tools on offer.

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

/** Sends the conversation so far and the tools on offer, and returns the model's next message. */
export async function chat(messages: Message[], tools: ToolSpec[]): Promise<ModelReply> {
  const response = await fetch(`${MODEL_URL}/v1/chat/completions`, {
    method: "POST",
    headers: { Authorization: `Bearer ${MODEL_API_KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify({ model: MODEL_NAME, messages, tools }),
  });
  if (!response.ok) {
    throw new Error(`the model answered ${response.status}`);
  }
  const reply = (await response.json()) as {
    choices: { message: AssistantMessage }[];
    usage: Usage;
  };
  return { message: reply.choices[0].message, usage: reply.usage };
}
