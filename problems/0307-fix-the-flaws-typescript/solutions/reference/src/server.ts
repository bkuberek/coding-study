// The team notes service: its routes, the session check, the request log and error answers.

import { createServer } from "node:http";
import type { IncomingMessage, ServerResponse } from "node:http";

import { download } from "./attachments.ts";
import { HttpError, notFound, readJson } from "./http.ts";
import type { Answer } from "./http.ts";
import { createNote, deleteNote, readNote, searchNotes } from "./notes.ts";
import {
  listUsers,
  login,
  register,
  seedAdmin,
  sessionUser,
  shown,
  updateProfile,
} from "./users.ts";

const port = Number(process.env.PORT);
const adminPassword = process.env.ADMIN_PASSWORD;

async function route(
  request: IncomingMessage,
  path: string,
  query: URLSearchParams,
): Promise<Answer> {
  const method = request.method ?? "GET";
  if (method === "GET" && path === "/health") {
    return { status: 200, body: { status: "ok" } };
  }
  if (method === "POST" && path === "/users") {
    return register(await readJson(request));
  }
  if (method === "POST" && path === "/login") {
    return login(await readJson(request));
  }
  const user = sessionUser(request.headers.authorization);
  if (method === "GET" && path === "/me") {
    return { status: 200, body: shown(user) };
  }
  if (method === "PATCH" && path === "/me") {
    return updateProfile(user, await readJson(request));
  }
  if (method === "GET" && path === "/admin/users") {
    return listUsers(user);
  }
  if (method === "POST" && path === "/notes") {
    return createNote(user, await readJson(request));
  }
  if (method === "GET" && path === "/notes") {
    return searchNotes(user, query.get("q") ?? "");
  }
  const noteId = /^\/notes\/(\d+)$/.exec(path)?.[1];
  if (method === "GET" && noteId !== undefined) {
    return readNote(user, Number(noteId));
  }
  if (method === "DELETE" && noteId !== undefined) {
    return deleteNote(user, Number(noteId));
  }
  const attachment = /^\/attachments\/(.+)$/.exec(path)?.[1];
  if (method === "GET" && attachment !== undefined) {
    return download(attachment);
  }
  throw notFound();
}

// An error answers its code and nothing else. What went wrong inside stays in the log, where the
// team can read it and a client cannot.
function failure(error: unknown): Answer {
  if (error instanceof HttpError) {
    return { status: error.status, body: { error: error.code } };
  }
  console.error(error);
  return { status: 500, body: { error: "internal_error" } };
}

function send(response: ServerResponse, answer: Answer): void {
  response.statusCode = answer.status;
  if (answer.bytes !== undefined) {
    response.setHeader("Content-Type", "application/octet-stream");
    response.end(answer.bytes);
  } else if (answer.body === undefined) {
    response.end();
  } else {
    response.setHeader("Content-Type", "application/json");
    response.end(JSON.stringify(answer.body));
  }
}

if (!adminPassword) {
  throw new Error("ADMIN_PASSWORD is not set");
}
seedAdmin(adminPassword);

// The request log names what was asked and how it was answered. It holds no header: one of them
// carries the session token.
const server = createServer((request, response) => {
  const target = request.url ?? "/";
  const queryAt = target.indexOf("?");
  const path = queryAt === -1 ? target : target.slice(0, queryAt);
  const query = new URLSearchParams(queryAt === -1 ? "" : target.slice(queryAt + 1));
  route(request, path, query)
    .catch(failure)
    .then((answer) => {
      console.log(`${request.method} ${path} ${answer.status}`);
      send(response, answer);
    });
});

server.listen(port, "0.0.0.0", () => {
  console.log(`listening on ${port}`);
});
