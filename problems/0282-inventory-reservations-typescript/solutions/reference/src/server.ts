// The shop's reservation service: checkouts reserve stock while the customer pays, and give it
// back when they finish or walk away.

import { createServer } from "node:http";
import type { IncomingMessage, ServerResponse } from "node:http";

import { type Answer, refused } from "./answers.ts";
import { product, receive, warehousesOf } from "./inventory.ts";
import { release, reservation, reserve } from "./reservations.ts";

const port = Number(process.env.PORT);

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
  const named = (pattern: RegExp) => {
    const found = pattern.exec(path);
    return found === null ? undefined : decodeURIComponent(found[1]);
  };
  const productSku = named(/^\/products\/([^/]+)$/);
  const stockSku = named(/^\/products\/([^/]+)\/warehouses$/);
  const order = named(/^\/reservations\/([^/]+)$/);
  const warehouse = named(/^\/warehouses\/([^/]+)\/receipts$/);
  if (path === "/health") {
    return { status: 200, body: { status: "ok" } };
  }
  if (method === "GET" && productSku !== undefined) {
    return product(productSku);
  }
  if (method === "GET" && stockSku !== undefined) {
    return warehousesOf(stockSku);
  }
  if (method === "POST" && path === "/reservations") {
    return reserve(await jsonBody(request));
  }
  if (method === "GET" && order !== undefined) {
    return reservation(order);
  }
  if (method === "DELETE" && order !== undefined) {
    return release(order);
  }
  if (method === "POST" && warehouse !== undefined) {
    return receive(warehouse, await jsonBody(request));
  }
  return refused(404, "not_found");
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
      send(response, refused(500, "internal"));
    },
  );
});

server.listen(port, "0.0.0.0", () => {
  console.log(`listening on ${port}`);
});
