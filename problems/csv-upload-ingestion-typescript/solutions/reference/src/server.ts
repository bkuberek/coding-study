// The ingestion service: it loads the delivery files suppliers upload, and answers what it has
// loaded. The HTTP routes only read; the work happens in the consumer.

import { createServer } from "node:http";
import type { ServerResponse } from "node:http";

import { consume } from "./consumer.ts";
import { pool } from "./db.ts";
import { type Answer, importsOf } from "./imports.ts";

const port = Number(process.env.PORT);

async function product(sku: string): Promise<Answer> {
  const found = await pool.query<{ sku: string; description: string; quantity: string }>(
    "SELECT sku, description, quantity FROM products WHERE sku = $1",
    [sku],
  );
  const row = found.rows[0];
  if (row === undefined) {
    return { status: 404, body: { error: "unknown_sku" } };
  }
  // `pg` reads a bigint as text, since it may not fit a JavaScript number.
  return {
    status: 200,
    body: { sku: row.sku, description: row.description, quantity: Number(row.quantity) },
  };
}

async function route(method: string, url: URL): Promise<Answer> {
  const productPath = /^\/products\/([^/]+)$/.exec(url.pathname);
  if (url.pathname === "/health") {
    return { status: 200, body: { status: "ok" } };
  }
  if (method === "GET" && productPath !== null) {
    return product(decodeURIComponent(productPath[1]));
  }
  if (method === "GET" && url.pathname === "/imports") {
    return importsOf(url.searchParams.get("key"));
  }
  return { status: 404, body: { error: "not_found" } };
}

function send(response: ServerResponse, answer: Answer): void {
  response.writeHead(answer.status, { "Content-Type": "application/json" });
  response.end(JSON.stringify(answer.body));
}

const server = createServer((request, response) => {
  const url = new URL(request.url ?? "/", "http://app");
  route(request.method ?? "GET", url).then(
    (answer) => send(response, answer),
    (error: unknown) => {
      console.error(error);
      send(response, { status: 500, body: { error: "internal" } });
    },
  );
});

server.listen(port, "0.0.0.0", () => {
  console.log(`listening on ${port}`);
  void consume();
});
