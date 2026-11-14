// The team's help assistant: it keeps the internal documents, finds the passages a question needs,
// and answers from them with citations.

import { createServer } from "node:http";
import type { IncomingMessage, ServerResponse } from "node:http";

import { ask, DEFAULT_K, DEFAULT_MIN_SCORE, listChunks, putDocument, search } from "./assistant.ts";
import { ProviderError } from "./models.ts";
import { documentWords, isDocumentId, question, searchRequest } from "./requests.ts";

type Answer = { status: number; body: unknown };

const port = Number(process.env.PORT);
const invalid: Answer = { status: 400, body: { error: "invalid_request" } };

async function putDocumentRoute(id: string, body: unknown): Promise<Answer> {
  const words = documentWords(body);
  if (!isDocumentId(id) || words === null) {
    return invalid;
  }
  const chunks = await putDocument(id, words);
  if (chunks === null) {
    return { status: 413, body: { error: "document_too_large" } };
  }
  return { status: 200, body: { document_id: id, chunks } };
}

async function documentChunks(id: string): Promise<Answer> {
  const chunks = await listChunks(id);
  if (chunks === null) {
    return { status: 404, body: { error: "unknown_document" } };
  }
  return { status: 200, body: { document_id: id, chunks } };
}

async function searchRoute(body: unknown): Promise<Answer> {
  const request = searchRequest(body, { k: DEFAULT_K, minScore: DEFAULT_MIN_SCORE });
  if (request === null) {
    return invalid;
  }
  return { status: 200, body: { results: await search(request.query, request.k, request.minScore) } };
}

async function askRoute(body: unknown): Promise<Answer> {
  const asked = question(body);
  if (asked === null) {
    return invalid;
  }
  return { status: 200, body: await ask(asked) };
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
  const documentPath = /^\/documents\/([^/]+)$/.exec(path);
  const chunksPath = /^\/documents\/([^/]+)\/chunks$/.exec(path);
  if (path === "/health") {
    return { status: 200, body: { status: "ok" } };
  }
  if (method === "PUT" && documentPath !== null) {
    return putDocumentRoute(decodeURIComponent(documentPath[1]), await jsonBody(request));
  }
  if (method === "GET" && chunksPath !== null) {
    return documentChunks(decodeURIComponent(chunksPath[1]));
  }
  if (method === "POST" && path === "/search") {
    return searchRoute(await jsonBody(request));
  }
  if (method === "POST" && path === "/ask") {
    return askRoute(await jsonBody(request));
  }
  return { status: 404, body: { error: "not_found" } };
}

async function answered(request: IncomingMessage, path: string): Promise<Answer> {
  try {
    return await route(request, path);
  } catch (error) {
    if (error instanceof ProviderError) {
      console.error(`${error.code}: ${error.message}`);
      return { status: 502, body: { error: error.code } };
    }
    throw error;
  }
}

function send(response: ServerResponse, answer: Answer): void {
  response.writeHead(answer.status, { "Content-Type": "application/json" });
  response.end(JSON.stringify(answer.body));
}

const server = createServer((request, response) => {
  const path = new URL(request.url ?? "/", "http://app").pathname;
  answered(request, path).then(
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
