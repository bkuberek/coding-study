// The shop's reservation service: checkouts reserve stock while the customer pays, and give it
// back when they finish or walk away.

import { createServer } from "node:http";
import type { IncomingMessage, ServerResponse } from "node:http";

import { pool } from "./db.ts";

type Answer = { status: number; body: unknown };

const port = Number(process.env.PORT);
const notImplemented: Answer = { status: 501, body: { error: "not_implemented" } };

async function product(sku: string): Promise<Answer> {
  const found = await pool.query<{ sku: string; name: string; stock: number }>(
    "SELECT sku, name, stock FROM products WHERE sku = $1",
    [sku],
  );
  const row = found.rows[0];
  if (row === undefined) {
    return { status: 404, body: { error: "unknown_sku" } };
  }
  return { status: 200, body: { sku: row.sku, name: row.name, available: row.stock } };
}

// Level 1 starts here.
function reserve(_body: unknown): Answer {
  return notImplemented;
}

function reservation(_order: string): Answer {
  return notImplemented;
}

function release(_order: string): Answer {
  return notImplemented;
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
  const productPath = /^\/products\/([^/]+)$/.exec(path);
  const reservationPath = /^\/reservations\/([^/]+)$/.exec(path);
  if (path === "/health") {
    return { status: 200, body: { status: "ok" } };
  }
  if (method === "GET" && productPath !== null) {
    return product(decodeURIComponent(productPath[1]));
  }
  if (method === "POST" && path === "/reservations") {
    return reserve(await jsonBody(request));
  }
  if (method === "GET" && reservationPath !== null) {
    return reservation(decodeURIComponent(reservationPath[1]));
  }
  if (method === "DELETE" && reservationPath !== null) {
    return release(decodeURIComponent(reservationPath[1]));
  }
  return { status: 404, body: { error: "not_found" } };
}

function send(response: ServerResponse, answer: Answer): void {
  response.writeHead(answer.status, { "Content-Type": "application/json" });
  response.end(JSON.stringify(answer.body));
}

const server = createServer((request, response) => {
  const path = new URL(request.url ?? "/", "http://app").pathname;
  route(request, path).then(
    (answer) => send(response, answer),
    (error: unknown) => {
      console.error(error);
      send(response, { status: 500, body: { error: "internal" } });
    },
  );
});

server.listen(port, "0.0.0.0", () => {
  console.log(`listening on ${port}`);
});
