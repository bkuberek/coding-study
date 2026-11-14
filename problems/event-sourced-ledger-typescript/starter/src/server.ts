// The club's wallet ledger: every change to a member's wallet is an event in the store, and
// balances are read from a projection of those events.

import { createServer } from "node:http";
import type { IncomingMessage, ServerResponse } from "node:http";

import { pool } from "./db.ts";

type Answer = { status: number; body: unknown };

const port = Number(process.env.PORT);
const notImplemented: Answer = { status: 501, body: { error: "not_implemented" } };

async function events(account: string): Promise<Answer> {
  const found = await pool.query<{ version: number; type: string; data: unknown }>(
    "SELECT version, type, data FROM events WHERE stream_id = $1 ORDER BY version",
    [account],
  );
  if (found.rows.length === 0) {
    return { status: 404, body: { error: "unknown_account" } };
  }
  return { status: 200, body: found.rows };
}

// Level 1 starts here.
function balance(_account: string, _query: URLSearchParams): Answer {
  return notImplemented;
}

function deposit(_account: string, _body: unknown): Answer {
  return notImplemented;
}

function withdraw(_account: string, _body: unknown): Answer {
  return notImplemented;
}

function transfer(_body: unknown): Answer {
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

async function route(request: IncomingMessage, url: URL): Promise<Answer> {
  const method = request.method ?? "GET";
  const path = url.pathname;
  const accountPath = /^\/accounts\/([^/]+)(\/[a-z]+)?$/.exec(path);
  const account = accountPath === null ? undefined : decodeURIComponent(accountPath[1]);
  const action = accountPath?.[2];
  if (path === "/health") {
    return { status: 200, body: { status: "ok" } };
  }
  if (method === "GET" && account !== undefined && action === undefined) {
    return balance(account, url.searchParams);
  }
  if (method === "GET" && account !== undefined && action === "/events") {
    return events(account);
  }
  if (method === "POST" && account !== undefined && action === "/deposits") {
    return deposit(account, await jsonBody(request));
  }
  if (method === "POST" && account !== undefined && action === "/withdrawals") {
    return withdraw(account, await jsonBody(request));
  }
  if (method === "POST" && path === "/transfers") {
    return transfer(await jsonBody(request));
  }
  return { status: 404, body: { error: "not_found" } };
}

function send(response: ServerResponse, answer: Answer): void {
  response.writeHead(answer.status, { "Content-Type": "application/json" });
  response.end(JSON.stringify(answer.body));
}

const server = createServer((request, response) => {
  const url = new URL(request.url ?? "/", "http://app");
  route(request, url).then(
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
