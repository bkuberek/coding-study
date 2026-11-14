// The shop's payment webhooks: the provider says what happened to each order's payment, and the shop
// keeps every order's state right, however late, often or out of order the news arrives.

import { createServer } from "node:http";
import type { IncomingMessage, ServerResponse } from "node:http";

import { nowSeconds } from "./clock.ts";
import { OrderBook } from "./orders.ts";
import { ProviderClient } from "./provider.ts";
import { WebhookReceiver } from "./webhooks/receiver.ts";
import type { Answer } from "./webhooks/receiver.ts";

type Route = { method: string; handle: (request: IncomingMessage) => Promise<Answer> };

const port = Number(process.env.PORT);
const orders = new OrderBook();
const receiver = new WebhookReceiver(
  { secret: String(process.env.WEBHOOK_SECRET), now: nowSeconds },
  orders,
  new ProviderClient(String(process.env.PAYMENT_PROVIDER_URL)),
);
const ORDER_PATH = /^\/orders\/([^/]+)$/;

/** The body's bytes, exactly as they arrived. */
async function readBody(request: IncomingMessage): Promise<Buffer> {
  const chunks: Buffer[] = [];
  for await (const chunk of request) {
    chunks.push(chunk as Buffer);
  }
  return Buffer.concat(chunks);
}

function header(request: IncomingMessage, name: string): string | undefined {
  const value = request.headers[name];
  return typeof value === "string" ? value : undefined;
}

async function receive(request: IncomingMessage): Promise<Answer> {
  return receiver.receive({
    timestamp: header(request, "provider-timestamp"),
    signature: header(request, "provider-signature"),
    body: await readBody(request),
  });
}

async function viewOf(order: string): Promise<Answer> {
  const view = orders.view(order);
  return view === undefined
    ? { status: 404, body: { error: "unknown order" } }
    : { status: 200, body: view };
}

/** The method a path answers and what answers it; null for a path this API does not have. */
function routeFor(pathname: string): Route | null {
  if (pathname === "/health") {
    return { method: "GET", handle: async () => ({ status: 200, body: { status: "ok" } }) };
  }
  if (pathname === "/webhooks/payments") {
    return { method: "POST", handle: receive };
  }
  const order = ORDER_PATH.exec(pathname)?.[1];
  return order === undefined ? null : { method: "GET", handle: () => viewOf(order) };
}

async function route(request: IncomingMessage): Promise<Answer> {
  const found = routeFor(new URL(request.url ?? "/", "http://app").pathname);
  if (found === null) {
    return { status: 404, body: { error: "not found" } };
  }
  if (request.method !== found.method) {
    return { status: 405, body: { error: "method not allowed" } };
  }
  return found.handle(request);
}

function send(response: ServerResponse, answer: Answer): void {
  response.statusCode = answer.status;
  response.setHeader("Content-Type", "application/json");
  response.end(JSON.stringify(answer.body));
}

const server = createServer((request, response) => {
  route(request).then(
    (answer) => send(response, answer),
    (error: unknown) => {
      console.error(error);
      send(response, { status: 500, body: { error: "internal error" } });
    },
  );
});

server.listen(port, "0.0.0.0", () => {
  console.log(`listening on ${port}`);
});
