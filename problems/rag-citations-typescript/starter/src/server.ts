// The team's help assistant: it keeps the internal documents, finds the passages a question needs,
// and answers from them with citations.

import { createServer } from "node:http";
import type { IncomingMessage, ServerResponse } from "node:http";

type Answer = { status: number; body: unknown };

const port = Number(process.env.PORT);
const notImplemented: Answer = { status: 501, body: { error: "not_implemented" } };

// Level 1 starts here.
function putDocument(_id: string, _body: unknown): Answer {
  return notImplemented;
}

function documentChunks(_id: string): Answer {
  return notImplemented;
}

// Level 2 starts here.
function search(_body: unknown): Answer {
  return notImplemented;
}

// Level 3 starts here.
function ask(_body: unknown): Answer {
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
  const documentPath = /^\/documents\/([^/]+)$/.exec(path);
  const chunksPath = /^\/documents\/([^/]+)\/chunks$/.exec(path);
  if (path === "/health") {
    return { status: 200, body: { status: "ok" } };
  }
  if (method === "PUT" && documentPath !== null) {
    return putDocument(decodeURIComponent(documentPath[1]), await jsonBody(request));
  }
  if (method === "GET" && chunksPath !== null) {
    return documentChunks(decodeURIComponent(chunksPath[1]));
  }
  if (method === "POST" && path === "/search") {
    return search(await jsonBody(request));
  }
  if (method === "POST" && path === "/ask") {
    return ask(await jsonBody(request));
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
