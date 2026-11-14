// What a route answers: a status and a JSON body, with refusals as `{"error": "<code>"}`.

export type Answer = { status: number; body: unknown };

export function ok(body: unknown, status = 200): Answer {
  return { status, body };
}

export function refused(status: number, error: string): Answer {
  return { status, body: { error } };
}

export const invalidRequest = refused(400, "invalid_request");
