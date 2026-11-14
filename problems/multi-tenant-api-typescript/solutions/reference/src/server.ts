// The tracker's API: many organizations share it and its database, and each sees only its own
// projects, tasks, members and comments. Every request is authenticated first, then served in one
// transaction for the caller's organization.

import { createServer } from "node:http";
import type { IncomingMessage, ServerResponse } from "node:http";

import { type Answer, notFound, ok, refused, unauthorized } from "./answers.ts";
import { authenticate, type Caller } from "./auth.ts";
import { addComment, listComments } from "./comments.ts";
import { asTenant, type Connection } from "./db.ts";
import { changeMe, changeRole, listMembers } from "./members.ts";
import { createProject, deleteProject, listProjects, project } from "./projects.ts";
import { searchComments, searchTasks } from "./search.ts";
import { changeTask, createTask, deleteTask, listTasks, task } from "./tasks.ts";

type Request = { caller: Caller; id: string; body: unknown; query: URLSearchParams };
type Route = {
  method: string;
  path: RegExp;
  handle: (db: Connection, request: Request) => Promise<Answer>;
};

const port = Number(process.env.PORT);
const METHODS_WITH_BODIES = new Set(["POST", "PATCH"]);

const ROUTES: Route[] = [
  { method: "GET", path: /^\/projects$/, handle: (db, r) => listProjects(db, r.caller) },
  { method: "POST", path: /^\/projects$/, handle: (db, r) => createProject(db, r.caller, r.body) },
  { method: "GET", path: /^\/projects\/([^/]+)$/, handle: (db, r) => project(db, r.caller, r.id) },
  {
    method: "DELETE",
    path: /^\/projects\/([^/]+)$/,
    handle: (db, r) => deleteProject(db, r.caller, r.id),
  },
  {
    method: "GET",
    path: /^\/projects\/([^/]+)\/tasks$/,
    handle: (db, r) => listTasks(db, r.caller, r.id),
  },
  {
    method: "POST",
    path: /^\/projects\/([^/]+)\/tasks$/,
    handle: (db, r) => createTask(db, r.caller, r.id, r.body),
  },
  { method: "GET", path: /^\/tasks\/([^/]+)$/, handle: (db, r) => task(db, r.caller, r.id) },
  {
    method: "PATCH",
    path: /^\/tasks\/([^/]+)$/,
    handle: (db, r) => changeTask(db, r.caller, r.id, r.body),
  },
  { method: "DELETE", path: /^\/tasks\/([^/]+)$/, handle: (db, r) => deleteTask(db, r.caller, r.id) },
  {
    method: "GET",
    path: /^\/tasks\/([^/]+)\/comments$/,
    handle: (db, r) => listComments(db, r.caller, r.id),
  },
  {
    method: "POST",
    path: /^\/tasks\/([^/]+)\/comments$/,
    handle: (db, r) => addComment(db, r.caller, r.id, r.body),
  },
  { method: "GET", path: /^\/members$/, handle: (db, r) => listMembers(db, r.caller) },
  { method: "PATCH", path: /^\/me$/, handle: (db, r) => changeMe(db, r.caller, r.body) },
  {
    method: "PATCH",
    path: /^\/members\/([^/]+)$/,
    handle: (db, r) => changeRole(db, r.caller, r.id, r.body),
  },
  { method: "GET", path: /^\/search\/tasks$/, handle: (db, r) => searchTasks(db, r.query) },
  { method: "GET", path: /^\/search\/comments$/, handle: (db, r) => searchComments(db, r.query) },
];

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

function decoded(segment: string | undefined): string | undefined {
  try {
    return decodeURIComponent(segment ?? "");
  } catch {
    return undefined;
  }
}

async function route(request: IncomingMessage, url: URL): Promise<Answer> {
  if (url.pathname === "/health") {
    return ok({ status: "ok" });
  }
  const caller = await authenticate(request.headers.authorization);
  if (caller === undefined) {
    return unauthorized;
  }
  const method = request.method ?? "GET";
  for (const { path, handle } of ROUTES.filter((candidate) => candidate.method === method)) {
    const found = path.exec(url.pathname);
    const id = found === null ? undefined : decoded(found[1]);
    if (id !== undefined) {
      const body = METHODS_WITH_BODIES.has(method) ? await jsonBody(request) : undefined;
      const given: Request = { caller, id, body, query: url.searchParams };
      return asTenant(caller.tenant, (db) => handle(db, given));
    }
  }
  return notFound;
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

server.listen(port, "0.0.0.0", () => {
  console.log(`listening on ${port}`);
});
