// The report service's job queue: producers enqueue jobs, and workers claim them, run them, and
// say how it went.

import { createServer } from "node:http";
import type { IncomingMessage, ServerResponse } from "node:http";

import { type Answer, refused } from "./answers.ts";
import { deadLetters, enqueue, job } from "./jobs.ts";
import { claim, complete, fail } from "./workers.ts";

const port = Number(process.env.PORT);

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
  const deadQueue = named(/^\/queues\/([^/]+)\/dead-letters$/);
  const jobId = named(/^\/jobs\/([^/]+)$/);
  const completedId = named(/^\/jobs\/([^/]+)\/complete$/);
  const failedId = named(/^\/jobs\/([^/]+)\/fail$/);
  if (path === "/health") {
    return { status: 200, body: { status: "ok" } };
  }
  if (method === "POST" && enqueueQueue !== undefined) {
    return enqueue(enqueueQueue, await jsonBody(request));
  }
  if (method === "GET" && jobId !== undefined) {
    return job(jobId);
  }
  if (method === "GET" && deadQueue !== undefined) {
    return deadLetters(deadQueue);
  }
  if (method === "POST" && claimQueue !== undefined) {
    return claim(claimQueue, await jsonBody(request));
  }
  if (method === "POST" && completedId !== undefined) {
    return complete(completedId, await jsonBody(request));
  }
  if (method === "POST" && failedId !== undefined) {
    return fail(failedId, await jsonBody(request));
  }
  return refused(404, "not_found");
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
      send(response, refused(500, "internal"));
    },
  );
});

server.listen(port, "0.0.0.0", () => {
  console.log(`listening on ${port}`);
});
