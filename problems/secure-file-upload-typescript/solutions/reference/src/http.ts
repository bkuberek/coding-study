// Reading a request's body within a limit, and writing an answer.

import type { IncomingMessage, ServerResponse } from "node:http";

export type Answer = {
  status: number;
  /** Sent as JSON, unless `bytes` is given. */
  body?: unknown;
  bytes?: Buffer;
  headers?: Record<string, string>;
};

export function refusal(status: number, error: string): Answer {
  return { status, body: { error } };
}

/**
 * The body, or null as soon as it is known to pass `limit`: from the length it declares, before
 * reading a byte of it, or from the count of what has arrived, without waiting for the rest. A
 * body sent in chunks declares no length, and a client can stop sending without ending it.
 */
export async function readBody(request: IncomingMessage, limit: number): Promise<Buffer | null> {
  if (Number(request.headers["content-length"]) > limit) {
    return null;
  }
  const chunks: Buffer[] = [];
  let size = 0;
  for await (const chunk of request) {
    size += (chunk as Buffer).length;
    if (size > limit) {
      // Leaving the loop destroys the request, so nothing more of it is read.
      return null;
    }
    chunks.push(chunk as Buffer);
  }
  return Buffer.concat(chunks);
}

/** The parsed JSON object a body holds, or null for anything else. */
export function jsonObject(body: Buffer): Record<string, unknown> | null {
  try {
    const parsed: unknown = JSON.parse(body.toString("utf8"));
    return typeof parsed === "object" && parsed !== null && !Array.isArray(parsed)
      ? (parsed as Record<string, unknown>)
      : null;
  } catch {
    return null;
  }
}

export function send(response: ServerResponse, answer: Answer): void {
  response.statusCode = answer.status;
  for (const [name, value] of Object.entries(answer.headers ?? {})) {
    response.setHeader(name, value);
  }
  if (answer.bytes !== undefined) {
    response.setHeader("Content-Length", answer.bytes.length);
    response.end(answer.bytes);
  } else if (answer.body === undefined) {
    response.end();
  } else {
    response.setHeader("Content-Type", "application/json");
    response.end(JSON.stringify(answer.body));
  }
}
