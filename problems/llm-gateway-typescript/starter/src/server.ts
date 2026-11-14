// The company's LLM gateway: one endpoint for every team, in front of the providers.

import { createServer } from "node:http";
import type { IncomingMessage, ServerResponse } from "node:http";

import { askPrimary, ProviderError } from "./primary.ts";

const port = Number(process.env.PORT);
const DEFAULT_MAX_TOKENS = 256;

function answer(response: ServerResponse, status: number, body: unknown): void {
  response.statusCode = status;
  response.setHeader("Content-Type", "application/json");
  response.end(JSON.stringify(body));
}

async function readBody(request: IncomingMessage): Promise<string> {
  const chunks: Buffer[] = [];
  for await (const chunk of request) {
    chunks.push(chunk as Buffer);
  }
  return Buffer.concat(chunks).toString("utf8");
}

async function chat(request: IncomingMessage, response: ServerResponse): Promise<void> {
  let body: { messages?: unknown; max_tokens?: number; stream?: boolean };
  try {
    body = JSON.parse(await readBody(request));
  } catch {
    answer(response, 400, { error: "the body must be a JSON object" });
    return;
  }
  if (body.stream === true) {
    answer(response, 501, { error: "streaming is not built yet" });
    return;
  }
  try {
    const { content, usage } = await askPrimary(body.messages, body.max_tokens ?? DEFAULT_MAX_TOKENS);
    answer(response, 200, { provider: "primary", content, usage });
  } catch (error) {
    if (!(error instanceof ProviderError)) {
      throw error;
    }
    answer(response, 502, { error: "no provider answered" });
  }
}

const server = createServer((request, response) => {
  const url = new URL(request.url ?? "/", "http://gateway");
  if (url.pathname === "/health") {
    answer(response, 200, { status: "ok" });
  } else if (url.pathname === "/v1/chat" && request.method === "POST") {
    chat(request, response).catch((error: unknown) => {
      console.error(error);
      answer(response, 500, { error: "internal error" });
    });
  } else {
    answer(response, 404, { error: "not found" });
  }
});

server.listen(port, "0.0.0.0", () => {
  console.log(`listening on ${port}`);
});
