// Requests to the running service, for the tests.

import assert from "node:assert/strict";
import { randomBytes } from "node:crypto";

const app = `http://127.0.0.1:${process.env.PORT}`;
const password = "notes-pass-1234";
/** Tells this run's users from those of an earlier run, since `cstudy dev` keeps its data. */
const run = randomBytes(4).toString("hex");

export function call(
  method: string,
  path: string,
  token?: string,
  body?: unknown,
): Promise<Response> {
  const headers: Record<string, string> = {};
  if (token !== undefined) {
    headers.Authorization = `Bearer ${token}`;
  }
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  const sent = typeof body === "string" || body === undefined ? body : JSON.stringify(body);
  return fetch(`${app}${path}`, { method, headers, body: sent });
}

export function userName(name: string): string {
  return `${name}-${run}`;
}

/** Signs a new user up and in, and answers their session token. */
export async function signedUp(name: string): Promise<string> {
  const username = userName(name);
  assert.equal((await call("POST", "/users", undefined, { username, password })).status, 201);
  const response = await call("POST", "/login", undefined, { username, password });
  assert.equal(response.status, 200);
  return ((await response.json()) as { token: string }).token;
}

/** Writes a note and answers its id. */
export async function written(token: string, title: string, body = ""): Promise<string> {
  const response = await call("POST", "/notes", token, { title, body });
  assert.equal(response.status, 201);
  return ((await response.json()) as { id: string }).id;
}
