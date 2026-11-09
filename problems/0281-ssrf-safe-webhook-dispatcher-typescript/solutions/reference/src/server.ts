// The webhook dispatcher: customers register the URLs they want events sent to, and the rest of
// the service asks it to deliver events there.

import { createServer } from "node:http";
import type { IncomingMessage, ServerResponse } from "node:http";

import { resolveDestination } from "./destinations.ts";
import { Dispatcher } from "./dispatcher.ts";
import { Endpoint, EndpointRegistry } from "./endpoints.ts";
import { webhookUrl } from "./urls.ts";

type Answer = { status: number; body: unknown };
type Registration = { id: string; url: string; secret: string };
type DeliveryRequest = { endpoints: string[]; event: Record<string, unknown> };

const ENDPOINT_ID = /^[A-Za-z0-9_-]{1,64}$/;
const ENDPOINT_PATH = /^\/endpoints\/([^/]+)$/;
const MIN_SECRET_LENGTH = 16;
const MAX_ENDPOINTS_PER_DELIVERY = 10;

const port = Number(process.env.PORT);
const registry = new EndpointRegistry();
const dispatcher = new Dispatcher();

function refusal(status: number, error: string): Answer {
  return { status, body: { error } };
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isRegistration(body: unknown): body is Registration {
  if (!isObject(body)) {
    return false;
  }
  const { id, url, secret } = body;
  return (
    typeof id === "string" &&
    ENDPOINT_ID.test(id) &&
    typeof url === "string" &&
    typeof secret === "string" &&
    secret.length >= MIN_SECRET_LENGTH
  );
}

function isDeliveryRequest(body: unknown): body is DeliveryRequest {
  if (!isObject(body)) {
    return false;
  }
  const { endpoints, event } = body;
  return (
    Array.isArray(endpoints) &&
    endpoints.length >= 1 &&
    endpoints.length <= MAX_ENDPOINTS_PER_DELIVERY &&
    endpoints.every((id) => typeof id === "string") &&
    new Set(endpoints).size === endpoints.length &&
    isObject(event)
  );
}

/** The URL is checked as written, then where it leads, before anything is stored. */
async function register(body: unknown): Promise<Answer> {
  if (!isRegistration(body)) {
    return refusal(400, "invalid_request");
  }
  if (registry.has(body.id)) {
    return refusal(409, "endpoint_exists");
  }
  const url = webhookUrl(body.url);
  if (url === null) {
    return refusal(400, "invalid_url");
  }
  const destination = await resolveDestination(url);
  if ("refusal" in destination) {
    return refusal(400, destination.refusal);
  }
  const endpoint = new Endpoint(body.id, body.url, body.secret);
  if (!registry.add(endpoint)) {
    return refusal(409, "endpoint_exists");
  }
  return { status: 201, body: endpoint.view() };
}

function show(id: string): Answer {
  const endpoint = registry.get(id);
  return endpoint === undefined
    ? refusal(404, "unknown_endpoint")
    : { status: 200, body: endpoint.view() };
}

async function deliverEvent(body: unknown): Promise<Answer> {
  if (!isDeliveryRequest(body)) {
    return refusal(400, "invalid_request");
  }
  const endpoints = body.endpoints.map((id) => registry.get(id));
  if (endpoints.includes(undefined)) {
    return refusal(404, "unknown_endpoint");
  }
  const results = await dispatcher.dispatch(endpoints as Endpoint[], body.event);
  return { status: 200, body: { results } };
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
  if (path === "/health") {
    return { status: 200, body: { status: "ok" } };
  }
  if (method === "POST" && path === "/endpoints") {
    return register(await jsonBody(request));
  }
  if (method === "POST" && path === "/deliveries") {
    return deliverEvent(await jsonBody(request));
  }
  const endpointPath = ENDPOINT_PATH.exec(path);
  if (method === "GET" && endpointPath !== null) {
    return show(decodeURIComponent(endpointPath[1]));
  }
  return refusal(404, "not_found");
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
      return refusal(500, "internal_error");
    })
    .then((answer) => send(response, answer));
});

server.listen(port, "0.0.0.0", () => {
  console.log(`listening on ${port}`);
});
