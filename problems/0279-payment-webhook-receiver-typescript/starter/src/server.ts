// The shop's payment webhooks: the provider says what happened to each order's payment, and the shop
// keeps every order's state.

import { createServer } from "node:http";
import type { IncomingMessage, ServerResponse } from "node:http";

import type { PaymentEvent } from "./events.ts";
import { OrderBook } from "./orders.ts";

type Answer = { status: number; body: unknown };
type Route = { method: string; handle: (request: IncomingMessage) => Promise<Answer> };

const port = Number(process.env.PORT);
const orders = new OrderBook();
const ORDER_PATH = /^\/orders\/([^/]+)$/;

/** The body's bytes, exactly as they arrived. */
async function readBody(request: IncomingMessage): Promise<Buffer> {
  const chunks: Buffer[] = [];
  for await (const chunk of request) {
    chunks.push(chunk as Buffer);
  }
  return Buffer.concat(chunks);
}

async function receive(request: IncomingMessage): Promise<Answer> {
  const body = await readBody(request);
  let event: PaymentEvent;
  try {
    event = JSON.parse(body.toString("utf8")) as PaymentEvent;
  } catch {
    return { status: 400, body: { error: "invalid event" } };
  }
  orders.apply(event);
  return { status: 200, body: { outcome: "applied" } };
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
