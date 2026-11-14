// The shop's public price API: partners ask it for prices, and it asks the slow pricing engine.

import { createServer } from "node:http";
import type { IncomingMessage, ServerResponse } from "node:http";

import { fetchPrice } from "./pricing.ts";
import { store } from "./store.ts";

// `body` is JSON text, sent as it is.
type Answer = { status: number; body: string; headers?: Record<string, string> };

const port = Number(process.env.PORT);

function refusal(status: number, error: string): Answer {
  return { status, body: JSON.stringify({ error }) };
}

// Level 1 starts here: every request asks the engine, which takes its time.
async function price(sku: string): Promise<Answer> {
  let answer;
  try {
    answer = await fetchPrice(sku);
  } catch {
    return refusal(502, "pricing_unavailable");
  }
  if (answer.status === 200) {
    return { status: 200, body: answer.body };
  }
  if (answer.status === 404) {
    return refusal(404, "unknown_sku");
  }
  return refusal(502, "pricing_unavailable");
}

// Level 3 starts here.
function setPrice(_sku: string, _body: unknown): Answer {
  return refusal(501, "not_implemented");
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
  if (method === "GET" && pricePath !== null) {
    return price(decodeURIComponent(pricePath[1]));
  }
  if (method === "PUT" && pricePath !== null) {
    return setPrice(decodeURIComponent(pricePath[1]), await jsonBody(request));
  }
  return refusal(404, "not_found");
}

function send(response: ServerResponse, answer: Answer): void {
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
