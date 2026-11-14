// What a route answers: a status and a JSON body, with refusals as `{"error": "<code>"}`, or no
// body at all for a 204.

export type Answer = { status: number; body?: unknown };

export function ok(body: unknown, status = 200): Answer {
  return { status, body };
}

export function refused(status: number, error: string): Answer {
  return { status, body: { error } };
}

export const invalidRequest = refused(400, "invalid_request");
export const unknownJob = refused(404, "unknown_job");
export const noContent: Answer = { status: 204 };
