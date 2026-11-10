// What a handler answers, the error it throws to refuse a request, and the JSON body it reads.

import type { IncomingMessage } from "node:http";

export type Answer = { status: number; body?: unknown; bytes?: Buffer };

export class HttpError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, detail?: string) {
    super(detail ?? code);
    this.name = "HttpError";
    this.status = status;
    this.code = code;
  }
}

export function notFound(): HttpError {
  return new HttpError(404, "not_found");
}

export async function readJson(request: IncomingMessage): Promise<Record<string, unknown>> {
  const chunks: Buffer[] = [];
  for await (const chunk of request) {
    chunks.push(chunk as Buffer);
  }
  let parsed: unknown;
  try {
    parsed = JSON.parse(Buffer.concat(chunks).toString("utf8"));
  } catch (error) {
    throw new HttpError(400, "invalid_request", `the body is not JSON: ${(error as Error).message}`);
  }
  if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
    throw new HttpError(400, "invalid_request", "the body is not a JSON object");
  }
  return parsed as Record<string, unknown>;
}
