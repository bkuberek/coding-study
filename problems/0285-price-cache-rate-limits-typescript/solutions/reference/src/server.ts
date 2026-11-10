// The shop's public price API: partners ask it for prices, and it asks the slow pricing engine only
// when the store has no good price, once per price however many ask at the same moment.

import { createServer } from "node:http";
import type { IncomingMessage, ServerResponse } from "node:http";

import { waitBeforeNext } from "./limiter.ts";
import { forget, lookUp } from "./prices.ts";
import { putPrice } from "./pricing.ts";
import { store } from "./store.ts";

// `body` is JSON text, sent as it is; a 204 has none.
type Answer = { status: number; body?: string; headers?: Record<string, string> };

const port = Number(process.env.PORT);
const API_KEY = /^[A-Za-z0-9_-]{1,64}$/;
const MAX_AMOUNT_CENTS = 10_000_000;

function refusal(status: number, error: string): Answer {
  return { status, body: JSON.stringify({ error }) };
}

async function price(sku: string): Promise<Answer> {
  const found = await lookUp(sku);
  switch (found.kind) {
    case "price":
      return { status: 200, body: found.body, headers: { "X-Cache": found.cache } };
    case "unknown":
      return refusal(404, "unknown_sku");
    case "unavailable":
      return refusal(502, "pricing_unavailable");
  }
}

async function setPrice(sku: string, body: unknown): Promise<Answer> {
  const amount = amountOf(body);
  if (amount === null) {
    return refusal(400, "invalid_request");
  }
  if (!(await putPrice(sku, amount))) {
    return refusal(502, "pricing_unavailable");
  }
  await forget(sku);
  return { status: 204 };
}

function amountOf(body: unknown): number | null {
  if (typeof body !== "object" || body === null || Array.isArray(body)) {
    return null;
  }
  const amount = (body as Record<string, unknown>).amount_cents;
  const valid =
    typeof amount === "number" &&
    Number.isInteger(amount) &&
    amount >= 1 &&
    amount <= MAX_AMOUNT_CENTS;
  return valid ? amount : null;
}

// The API key and the client's limit come before anything else a request asks for.
async function limited(request: IncomingMessage, handle: () => Promise<Answer>): Promise<Answer> {
  const client = request.headers["x-api-key"];
  if (typeof client !== "string" || !API_KEY.test(client)) {
    return refusal(401, "missing_api_key");
  }
  const waitMs = await waitBeforeNext(client);
  if (waitMs > 0) {
    const retryAfter = String(Math.ceil(waitMs / 1000));
    return { ...refusal(429, "rate_limited"), headers: { "Retry-After": retryAfter } };
  }
  return handle();
}

async function jsonBody(request: IncomingMessage): Promise<unknown> {
  const chunks: Buffer[] = [];
  for await (const chunk of request) {
    chunks.push(chunk as Buffer);
  }
  try {
    return JSON.parse(Buffer.concat(chunks).toString("utf8"));
  } catch {
    return undefined;
  }
}

async function route(request: IncomingMessage, path: string): Promise<Answer> {
  const method = request.method ?? "GET";
  const pricePath = /^\/prices\/([^/]+)$/.exec(path);
  if (path === "/health") {
    await store.ping();
    return { status: 200, body: JSON.stringify({ status: "ok" }) };
  }
  if (pricePath === null) {
    return refusal(404, "not_found");
  }
  const sku = decodeURIComponent(pricePath[1]);
  if (method === "GET") {
    return limited(request, () => price(sku));
  }
  if (method === "PUT") {
    return limited(request, async () => setPrice(sku, await jsonBody(request)));
  }
  return refusal(404, "not_found");
}

function send(response: ServerResponse, answer: Answer): void {
  if (answer.body === undefined) {
    response.writeHead(answer.status, answer.headers);
    response.end();
    return;
  }
  response.writeHead(answer.status, { "Content-Type": "application/json", ...answer.headers });
  response.end(answer.body);
}

const server = createServer((request, response) => {
  const path = new URL(request.url ?? "/", "http://app").pathname;
  route(request, path).then(
    (answer) => send(response, answer),
    (error: unknown) => {
      console.error(error);
      send(response, refusal(500, "internal"));
    },
  );
});

server.listen(port, "0.0.0.0", () => {
  console.log(`listening on ${port}`);
});
