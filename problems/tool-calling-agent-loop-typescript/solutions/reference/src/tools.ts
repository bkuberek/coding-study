// The tools the assistant can use, each a call to one of the shop's systems, whose APIs are in
// vendors/. A tool's parameters are a JSON Schema, sent to the model as it is, and these schemas use
// only the keywords `JsonSchema` names. Running a tool never throws: whatever goes wrong becomes a
// result the model can read.

import type { ToolSpec } from "./model.ts";

export type JsonSchema =
  | {
      type: "object";
      properties: Record<string, JsonSchema>;
      required: string[];
      additionalProperties: false;
    }
  | { type: "string"; minLength?: number; maxLength?: number; pattern?: string; enum?: string[] }
  | { type: "integer"; minimum?: number; maximum?: number };

type Request = { url: string; init?: RequestInit };

export type Tool = {
  name: string;
  description: string;
  parameters: JsonSchema;
  /** The request to the system behind the tool, for arguments its schema accepts. */
  request: (args: Record<string, unknown>) => Request;
};

/** What running a tool gave: its JSON answer, or why there is none. */
export type ToolResult =
  | { ok: true; data: unknown }
  | { ok: false; error: "tool_error" | "tool_timeout"; status?: number };

const KB_URL = process.env.KB_URL;
const ORDERS_URL = process.env.ORDERS_URL;
const HELPDESK_URL = process.env.HELPDESK_URL;
const ORDER_ID = "^A-[0-9]{4}$";

function post(url: string, body: unknown): Request {
  return {
    url,
    init: {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
  };
}

/** Every tool there is, in the order they are offered to the model. */
export const TOOLS: Tool[] = [
  {
    name: "search_kb",
    description: "Search the help center's articles. Answers up to three matches.",
    parameters: {
      type: "object",
      properties: { query: { type: "string", minLength: 1, maxLength: 200 } },
      required: ["query"],
      additionalProperties: false,
    },
    request: (args) => ({
      url: `${KB_URL}/v1/articles/search?q=${encodeURIComponent(String(args.query))}`,
    }),
  },
  {
    name: "lookup_order",
    description: "Look up an order by its id.",
    parameters: {
      type: "object",
      properties: { order_id: { type: "string", pattern: ORDER_ID } },
      required: ["order_id"],
      additionalProperties: false,
    },
    request: (args) => ({ url: `${ORDERS_URL}/v1/orders/${encodeURIComponent(String(args.order_id))}` }),
  },
  {
    name: "create_ticket",
    description: "Open a ticket for the support team.",
    parameters: {
      type: "object",
      properties: {
        subject: { type: "string", minLength: 1, maxLength: 120 },
        body: { type: "string", minLength: 1, maxLength: 2000 },
        priority: { type: "string", enum: ["low", "normal", "high"] },
      },
      required: ["subject", "body", "priority"],
      additionalProperties: false,
    },
    request: (args) => post(`${HELPDESK_URL}/v1/tickets`, args),
  },
  {
    name: "issue_refund",
    description: "Refund part or all of an order to the customer.",
    parameters: {
      type: "object",
      properties: {
        order_id: { type: "string", pattern: ORDER_ID },
        amount_cents: { type: "integer", minimum: 1, maximum: 50000 },
        reason: { type: "string", minLength: 1, maxLength: 300 },
      },
      required: ["order_id", "amount_cents", "reason"],
      additionalProperties: false,
    },
    request: (args) => post(`${ORDERS_URL}/v1/refunds`, args),
  },
];

export function toolNamed(name: string): Tool | undefined {
  return TOOLS.find((tool) => tool.name === name);
}

/** A tool as the model's API describes it. */
export function specOf(tool: Tool): ToolSpec {
  return {
    type: "function",
    function: { name: tool.name, description: tool.description, parameters: tool.parameters },
  };
}

function isTimeout(error: unknown): boolean {
  return error instanceof DOMException && error.name === "TimeoutError";
}

/** Runs a tool within `timeoutMs`, its answer and its body read included. */
export async function runTool(
  tool: Tool,
  args: Record<string, unknown>,
  timeoutMs: number,
): Promise<ToolResult> {
  const { url, init } = tool.request(args);
  try {
    const response = await fetch(url, { ...init, signal: AbortSignal.timeout(timeoutMs) });
    const text = await response.text();
    if (!response.ok) {
      return { ok: false, error: "tool_error", status: response.status };
    }
    return { ok: true, data: JSON.parse(text) };
  } catch (error) {
    return isTimeout(error) ? { ok: false, error: "tool_timeout" } : { ok: false, error: "tool_error" };
  }
}
