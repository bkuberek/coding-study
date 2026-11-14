// The upload service: users upload attachments and avatars, and get them back.

import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { createServer } from "node:http";
import type { IncomingMessage, ServerResponse } from "node:http";
import { join } from "node:path";

type Answer = { status: number; body?: unknown; bytes?: Buffer };

const port = Number(process.env.PORT);
const folder = join(process.env.CSTUDY_DATA_DIR ?? "/data", "files");

function sha256(bytes: Buffer): string {
  return createHash("sha256").update(bytes).digest("hex");
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

// Level 1 starts here. This keeps each file under the name it came with, reads the whole body
// before anything looks at its size, and knows nothing of users. The statement says why none of
// that is safe.
async function upload(request: IncomingMessage): Promise<Answer> {
  const body = (await jsonBody(request)) as { name?: unknown; data?: unknown } | undefined;
  if (typeof body?.name !== "string" || typeof body.data !== "string") {
    return { status: 400, body: { error: "invalid_request" } };
  }
  const bytes = Buffer.from(body.data, "base64");
  await mkdir(folder, { recursive: true });
  await writeFile(join(folder, body.name), bytes);
  return {
    status: 201,
    body: { id: body.name, name: body.name, size: bytes.length, sha256: sha256(bytes) },
  };
}

async function metadata(id: string): Promise<Answer> {
  const bytes = await readFile(join(folder, id));
  return { status: 200, body: { id, name: id, size: bytes.length, sha256: sha256(bytes) } };
}

async function content(id: string): Promise<Answer> {
  return { status: 200, bytes: await readFile(join(folder, id)) };
}

async function route(request: IncomingMessage, path: string): Promise<Answer> {
  const method = request.method ?? "GET";
  const filePath = /^\/files\/([^/]+)(\/content)?$/.exec(path);
  if (path === "/health") {
    return { status: 200, body: { status: "ok" } };
  }
  if (method === "POST" && path === "/files") {
    return upload(request);
  }
  if (method === "GET" && filePath !== null) {
    const id = decodeURIComponent(filePath[1]);
    return filePath[2] === undefined ? metadata(id) : content(id);
  }
  if (path === "/usage" || filePath !== null) {
    return { status: 501, body: { error: "not implemented" } };
  }
  return { status: 404, body: { error: "not_found" } };
}

function send(response: ServerResponse, answer: Answer): void {
  response.statusCode = answer.status;
  if (answer.bytes !== undefined) {
    response.setHeader("Content-Type", "application/octet-stream");
    response.end(answer.bytes);
    return;
  }
  response.setHeader("Content-Type", "application/json");
  response.end(JSON.stringify(answer.body));
}

// A client has 2 s to send its whole request, and then gets 408: no connection waits forever on
// one that stopped sending. It bounds the time a request takes, not the bytes it holds.
const limits = { headersTimeout: 2000, requestTimeout: 2000, connectionsCheckingInterval: 250 };

const server = createServer(limits, (request, response) => {
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
