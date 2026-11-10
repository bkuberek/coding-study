// The assistant's API: a staff member asks a question, and gets the assistant's answer.

import { createServer } from "node:http";
import type { IncomingMessage, ServerResponse } from "node:http";

import { runAgent } from "./agent.ts";
import type { Question } from "./agent.ts";
import { ModelUnavailable } from "./model.ts";
import { isRole } from "./roles.ts";

type Answer = { status: number; body: unknown };
type Route = { method: string; handle: (request: IncomingMessage) => Promise<Answer> };

const port = Number(process.env.PORT);
const LONGEST_QUESTION = 2000;

/** The body as JSON, or undefined when it is not JSON. */
async function readJson(request: IncomingMessage): Promise<unknown> {
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

/** The question a request asks, or null when it is not one. */
function questionFrom(body: unknown): Question | null {
  if (typeof body !== "object" || body === null) {
    return null;
  }
  const { role, question } = body as Record<string, unknown>;
  if (!isRole(role) || typeof question !== "string") {
    return null;
  }
  if (question.trim() === "" || question.length > LONGEST_QUESTION) {
    return null;
  }
  return { role, question };
}

async function assist(request: IncomingMessage): Promise<Answer> {
  const question = questionFrom(await readJson(request));
  if (question === null) {
    return { status: 400, body: { error: "invalid request" } };
  }
  try {
    return { status: 200, body: await runAgent(question) };
  } catch (error) {
    if (error instanceof ModelUnavailable) {
      console.error(error.message);
      return { status: 502, body: { error: "model unavailable" } };
    }
    throw error;
  }
}

/** The method a path answers and what answers it; null for a path this API does not have. */
function routeFor(pathname: string): Route | null {
  if (pathname === "/health") {
    return { method: "GET", handle: async () => ({ status: 200, body: { status: "ok" } }) };
  }
  if (pathname === "/assist") {
    return { method: "POST", handle: assist };
  }
  return null;
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
