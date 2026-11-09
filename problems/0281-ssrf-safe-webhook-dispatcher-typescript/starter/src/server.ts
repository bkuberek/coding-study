// The webhook dispatcher: customers register the URLs they want events sent to, and the rest of
// the service asks it to deliver events there.

import { createServer } from "node:http";
import type { IncomingMessage, ServerResponse } from "node:http";

type Endpoint = {
  id: string;
  url: string;
  secret: string;
  status: "active" | "disabled";
  consecutive_failures: number;
};

type Answer = { status: number; body: unknown };

const port = Number(process.env.PORT);
const endpoints = new Map<string, Endpoint>();

function view(endpoint: Endpoint): Omit<Endpoint, "secret"> {
  const { secret: _secret, ...shown } = endpoint;
  return shown;
}

// Level 1 starts here: nothing checks the URL yet.
function register(body: { id: string; url: string; secret: string }): Answer {
  const endpoint: Endpoint = {
    id: body.id,
    url: body.url,
    secret: body.secret,
    status: "active",
    consecutive_failures: 0,
  };
  endpoints.set(endpoint.id, endpoint);
  return { status: 201, body: view(endpoint) };
}

function show(id: string): Answer {
  const endpoint = endpoints.get(id);
  if (endpoint === undefined) {
    return { status: 404, body: { error: "unknown_endpoint" } };
  }
  return { status: 200, body: view(endpoint) };
}

function deliver(_body: unknown): Answer {
  return { status: 501, body: { error: "not implemented" } };
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
  const endpointPath = /^\/endpoints\/([^/]+)$/.exec(path);
  if (path === "/health") {
    return { status: 200, body: { status: "ok" } };
  }
  if (method === "POST" && path === "/endpoints") {
    const body = await jsonBody(request);
    if (typeof body !== "object" || body === null) {
      return { status: 400, body: { error: "invalid_request" } };
    }
    return register(body as { id: string; url: string; secret: string });
  }
  if (method === "GET" && endpointPath !== null) {
    return show(decodeURIComponent(endpointPath[1]));
  }
  if (method === "POST" && path === "/deliveries") {
    return deliver(await jsonBody(request));
  }
  return { status: 404, body: { error: "not_found" } };
}

function send(response: ServerResponse, answer: Answer): void {
  response.statusCode = answer.status;
  response.setHeader("Content-Type", "application/json");
  response.end(JSON.stringify(answer.body));
}

const server = createServer((request, response) => {
  const path = new URL(request.url ?? "/", "http://app").pathname;
  route(request, path)
    .catch((error: unknown) => {
      console.error(error);
      return { status: 500, body: { error: "internal_error" } };
    })
    .then((answer) => send(response, answer));
});

server.listen(port, "0.0.0.0", () => {
  console.log(`listening on ${port}`);
});
