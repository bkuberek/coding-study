// The tools the assistant can use, each a call to one of the shop's systems, whose APIs are in
// vendors/. A tool's parameters are a JSON Schema, sent to the model as it is, and these schemas use
// only the keywords `JsonSchema` names.

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

export type Tool = {
  name: string;
  description: string;
  parameters: JsonSchema;
  /** Calls the system behind the tool with the arguments, and returns its JSON answer. */
  run: (args: Record<string, unknown>) => Promise<unknown>;
};

const KB_URL = process.env.KB_URL;
const ORDERS_URL = process.env.ORDERS_URL;
const HELPDESK_URL = process.env.HELPDESK_URL;
const ORDER_ID = "^A-[0-9]{4}$";

async function call(url: string, init?: RequestInit): Promise<unknown> {
  const response = await fetch(url, init);
  if (!response.ok) {
    throw new Error(`${url} answered ${response.status}`);
  }
  return response.json();
}

function post(url: string, body: unknown): Promise<unknown> {
  return call(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
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
    run: (args) => call(`${KB_URL}/v1/articles/search?q=${encodeURIComponent(String(args.query))}`),
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
    run: (args) => call(`${ORDERS_URL}/v1/orders/${encodeURIComponent(String(args.order_id))}`),
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
    run: (args) => post(`${HELPDESK_URL}/v1/tickets`, args),
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
    run: (args) => post(`${ORDERS_URL}/v1/refunds`, args),
  },
];

/** A tool as the model's API describes it. */
export function specOf(tool: Tool): ToolSpec {
  return {
    type: "function",
    function: { name: tool.name, description: tool.description, parameters: tool.parameters },
  };
}
