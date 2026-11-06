// Failures the API answers on purpose. Anything else reaches the client as a bare 500.

import type { Answer } from "./routing.ts";

export interface FieldProblem {
  readonly field: string;
  readonly message: string;
}

export class HttpProblem extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Readonly<Record<string, unknown>>;

  constructor(
    status: number,
    code: string,
    message: string,
    details: Readonly<Record<string, unknown>> = {},
  ) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }

  toAnswer(): Answer {
    const error = { code: this.code, message: this.message, ...this.details };
    return { status: this.status, body: { error } };
  }
}

export function notFound(message: string): HttpProblem {
  return new HttpProblem(404, "not_found", message);
}

export function invalidBody(): HttpProblem {
  return new HttpProblem(400, "invalid_body", "Request body must be a JSON object");
}

export function validationFailed(fields: readonly FieldProblem[]): HttpProblem {
  return new HttpProblem(400, "validation_failed", "Request validation failed", { fields });
}
