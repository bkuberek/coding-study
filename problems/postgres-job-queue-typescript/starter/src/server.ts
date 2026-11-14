// The report service's job queue: producers enqueue jobs, and workers claim them, run them, and
// say how it went. This first version only takes jobs in.

import { createServer } from "node:http";
import type { IncomingMessage, ServerResponse } from "node:http";

import { now, timestamp } from "./clock.ts";
import { pool } from "./db.ts";

type Answer = { status: number; body?: unknown };
type Fields = Record<string, unknown>;
type JobRow = { id: string; queue: string; tenant: string; payload: unknown; enqueued_at: Date };

const port = Number(process.env.PORT);
const NAME = /^[A-Za-z0-9_-]{1,64}$/;
const QUEUE = /^[a-z0-9-]{1,32}$/;
const JOB_COLUMNS = "id, queue, tenant, payload, enqueued_at";
const notImplemented: Answer = { status: 501, body: { error: "not_implemented" } };
const invalidRequest: Answer = { status: 400, body: { error: "invalid_request" } };

function isObject(value: unknown): value is Fields {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isName(value: unknown): value is string {
  return typeof value === "string" && NAME.test(value);
}

// All the first version knows of a job: it waits, never claimed, from the moment it was enqueued.
function shown(row: JobRow): Fields {
  return {
    id: row.id,
    queue: row.queue,
    tenant: row.tenant,
    payload: row.payload,
    status: "queued",
    attempts: 0,
    run_after: timestamp(row.enqueued_at),
  };
}

async function enqueue(queue: string, body: unknown): Promise<Answer> {
  if (!QUEUE.test(queue) || !isObject(body)) {
    return invalidRequest;
  }
  if (!isName(body.id) || !isName(body.tenant) || !isObject(body.payload)) {
    return invalidRequest;
  }
  const added = await pool.query<JobRow>(
    `INSERT INTO jobs (id, queue, tenant, payload, enqueued_at) VALUES ($1, $2, $3, $4, $5)
     ON CONFLICT (id) DO NOTHING
     RETURNING ${JOB_COLUMNS}`,
    [body.id, queue, body.tenant, body.payload, now()],
  );
  const row = added.rows[0];
  if (row === undefined) {
    return { status: 409, body: { error: "job_exists" } };
  }
  return { status: 201, body: shown(row) };
}

async function job(id: string): Promise<Answer> {
  const found = await pool.query<JobRow>(`SELECT ${JOB_COLUMNS} FROM jobs WHERE id = $1`, [id]);
  const row = found.rows[0];
  if (row === undefined) {
    return { status: 404, body: { error: "unknown_job" } };
  }
  return { status: 200, body: shown(row) };
}

// Level 1 starts here.
function claim(_queue: string, _body: unknown): Answer {
  return notImplemented;
}

function complete(_id: string, _body: unknown): Answer {
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
  const named = (pattern: RegExp) => {
    const found = pattern.exec(path);
    return found === null ? undefined : decodeURIComponent(found[1]);
  };
  const enqueueQueue = named(/^\/queues\/([^/]+)\/jobs$/);
  const claimQueue = named(/^\/queues\/([^/]+)\/claim$/);
  const jobId = named(/^\/jobs\/([^/]+)$/);
  const completedId = named(/^\/jobs\/([^/]+)\/complete$/);
  if (path === "/health") {
    return { status: 200, body: { status: "ok" } };
  }
  if (method === "POST" && enqueueQueue !== undefined) {
    return enqueue(enqueueQueue, await jsonBody(request));
  }
  if (method === "GET" && jobId !== undefined) {
    return job(jobId);
  }
  if (method === "POST" && claimQueue !== undefined) {
    return claim(claimQueue, await jsonBody(request));
  }
  if (method === "POST" && completedId !== undefined) {
    return complete(completedId, await jsonBody(request));
  }
  return { status: 404, body: { error: "not_found" } };
}

// A 204 has no body; every other answer is JSON.
function send(response: ServerResponse, answer: Answer): void {
  if (answer.body === undefined) {
    response.writeHead(answer.status);
    response.end();
    return;
  }
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
