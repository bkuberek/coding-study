// The campus portal: its users sign in with the campus identity provider, and the app keeps a
// session of its own for each of them, behind a cookie.

import { createServer } from "node:http";
import type { IncomingMessage, ServerResponse } from "node:http";

import { PORT } from "./config.ts";
import { readCookies } from "./cookies.ts";
import { MemoryStore } from "./store.ts";

/** Who is signed in, from the claims of their ID token. */
export type User = { sub: string; username: string; email: string };
type Session = { user: User };

/** What a route answers: a status, and a JSON body, a redirect or cookies to set. */
type Answer = { status: number; body?: unknown; location?: string; cookies?: string[] };
type Route = { method: string; handle: (request: IncomingMessage, url: URL) => Promise<Answer> };

const SESSION_COOKIE = "session";
const NOT_SIGNED_IN: Answer = { status: 401, body: { error: "not signed in" } };
const sessions = new MemoryStore<Session>();

function sessionOf(request: IncomingMessage): Session | undefined {
  return sessions.get(readCookies(request.headers.cookie).get(SESSION_COOKIE));
}

function notImplemented(level: number): Route["handle"] {
  return async () => ({ status: 501, body: { error: `not implemented yet: level ${level}` } });
}

async function home(request: IncomingMessage): Promise<Answer> {
  return { status: 200, body: { app: "campus portal", signed_in: sessionOf(request) !== undefined } };
}

async function me(request: IncomingMessage): Promise<Answer> {
  const session = sessionOf(request);
  return session === undefined ? NOT_SIGNED_IN : { status: 200, body: session.user };
}

const ROUTES: Record<string, Route> = {
  "/health": { method: "GET", handle: async () => ({ status: 200, body: { status: "ok" } }) },
  "/": { method: "GET", handle: home },
  "/login": { method: "GET", handle: notImplemented(1) },
  "/callback": { method: "GET", handle: notImplemented(1) },
  "/me": { method: "GET", handle: me },
  "/refresh": { method: "POST", handle: notImplemented(3) },
  "/logout": { method: "POST", handle: notImplemented(3) },
};

async function route(request: IncomingMessage): Promise<Answer> {
  const url = new URL(request.url ?? "/", "http://app");
  const found = Object.hasOwn(ROUTES, url.pathname) ? ROUTES[url.pathname] : undefined;
  if (found === undefined) {
    return { status: 404, body: { error: "not found" } };
  }
  if (request.method !== found.method) {
    return { status: 405, body: { error: "method not allowed" } };
  }
  return found.handle(request, url);
}

function send(response: ServerResponse, answer: Answer): void {
  response.statusCode = answer.status;
  if (answer.location !== undefined) {
    response.setHeader("Location", answer.location);
  }
  if (answer.cookies !== undefined) {
    response.setHeader("Set-Cookie", answer.cookies);
  }
  if (answer.body === undefined) {
    response.end();
    return;
  }
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

server.listen(PORT, "0.0.0.0", () => {
  console.log(`listening on ${PORT}`);
});
