// Reading a request body.

import { invalidJson } from "./errors.ts";

/** The body as a JSON object. Throws a 400 for broken JSON and for JSON of any other shape. */
export function readJsonObject(body: string): Record<string, unknown> {
  let parsed: unknown;
  try {
    parsed = JSON.parse(body);
  } catch {
    throw invalidJson();
  }
  if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw invalidJson();
  }
  return parsed as Record<string, unknown>;
}
