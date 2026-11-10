// The tracker's API: many organizations share it and its database, and each must see only its
// own projects and tasks.

import { createServer } from "node:http";
import type { IncomingMessage, ServerResponse } from "node:http";

import { type Answer, ok, refused } from "./answers.ts";
import { authenticate, type Caller } from "./auth.ts";
import { pool } from "./db.ts";
import { searchTasks } from "./search.ts";

const port = Number(process.env.PORT);
const notImplemented = refused(501, "not_implemented");

// Every organization's projects, whoever asks: scoping this list to the caller's organization is
// where level 1 starts.
async function projects(_caller: Caller): Promise<Answer> {
  const found = await pool.query("SELECT id, name FROM projects");
  return ok(found.rows);
}

function createProject(_caller: Caller, _body: unknown): Answer {
  return notImplemented;
}

function project(_caller: Caller, _id: string): Answer {
  return notImplemented;
}

function deleteProject(_caller: Caller, _id: string): Answer {
  return notImplemented;
}

function tasks(_caller: Caller, _projectId: string): Answer {
  return notImplemented;
}

function createTask(_caller: Caller, _projectId: string, _body: unknown): Answer {
  return notImplemented;
}

function task(_caller: Caller, _id: string): Answer {
  return notImplemented;
}

function changeTask(_caller: Caller, _id: string, _body: unknown): Answer {
  return notImplemented;
}

function deleteTask(_caller: Caller, _id: string): Answer {
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
  const named = (pattern: RegExp) => {
    const found = pattern.exec(path);
    return found === null ? undefined : decodeURIComponent(found[1]);
  };
  if (path === "/health") {
    return ok({ status: "ok" });
  }
  const caller = await authenticate(request.headers.authorization);
  if (caller === undefined) {
    return refused(401, "unauthorized");
  }
  const projectId = named(/^\/projects\/([^/]+)$/);
  const tasksOf = named(/^\/projects\/([^/]+)\/tasks$/);
  const taskId = named(/^\/tasks\/([^/]+)$/);
  if (method === "GET" && path === "/projects") {
    return projects(caller);
  }
  if (method === "POST" && path === "/projects") {
    return createProject(caller, await jsonBody(request));
  }
  if (method === "GET" && projectId !== undefined) {
    return project(caller, projectId);
  }
  if (method === "DELETE" && projectId !== undefined) {
    return deleteProject(caller, projectId);
  }
  if (method === "GET" && tasksOf !== undefined) {
    return tasks(caller, tasksOf);
  }
  if (method === "POST" && tasksOf !== undefined) {
    return createTask(caller, tasksOf, await jsonBody(request));
  }
  if (method === "GET" && taskId !== undefined) {
    return task(caller, taskId);
  }
  if (method === "PATCH" && taskId !== undefined) {
    return changeTask(caller, taskId, await jsonBody(request));
  }
  if (method === "DELETE" && taskId !== undefined) {
    return deleteTask(caller, taskId);
  }
  if (method === "GET" && path === "/search/tasks") {
    return searchTasks(pool, url.searchParams);
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

server.listen(port, "0.0.0.0", () => {
  console.log(`listening on ${port}`);
});
