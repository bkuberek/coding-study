// Small helpers for the gateway's own HTTP answers.

import type { IncomingMessage, ServerResponse } from "node:http";

export function answer(response: ServerResponse, status: number, body: unknown): void {
  response.statusCode = status;
  response.setHeader("Content-Type", "application/json");
  response.end(JSON.stringify(body));
}

export async function readBody(request: IncomingMessage): Promise<string> {
  const chunks: Buffer[] = [];
  for await (const chunk of request) {
    chunks.push(chunk as Buffer);
  }
  return Buffer.concat(chunks).toString("utf8");
}

/** A header's value, or undefined when it is missing or empty. */
export function header(request: IncomingMessage, name: string): string | undefined {
  const value = request.headers[name.toLowerCase()];
  const text = Array.isArray(value) ? value[0] : value;
  return text === "" ? undefined : text;
}
