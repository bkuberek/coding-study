// The club's wallet ledger: every change to a member's wallet is an event in the store, and
// balances are read from a projection of those events.

import { createServer } from "node:http";
import type { IncomingMessage, ServerResponse } from "node:http";

import { type Answer, ok, refused } from "./answers.ts";
import { deposit, transfer, withdraw } from "./commands.ts";
import { rebuild } from "./projection.ts";
import { balance, events } from "./queries.ts";

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

async function rebuilt(): Promise<Answer> {
  await rebuild();
  return ok({ status: "rebuilt" });
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
  if (method === "POST" && path === "/admin/rebuild") {
    return rebuilt();
  }
  return refused(404, "not_found");
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
      send(response, refused(500, "internal"));
    },
  );
});

await rebuild();
server.listen(port, "0.0.0.0", () => {
  console.log(`listening on ${port}`);
});
