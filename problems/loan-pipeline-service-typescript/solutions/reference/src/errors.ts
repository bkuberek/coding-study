// Errors the API answers on purpose. Anything else is a bug or an outage, which `LoanApi` turns
// into a 500 that says nothing about the cause.

import type { ApiResponse } from "./http/router.ts";
import type { Stage } from "./types.ts";

export interface FieldError {
  readonly field: string;
  readonly message: string;
}

export class ApiError extends Error {
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

  toResponse(): ApiResponse {
    const error = { code: this.code, message: this.message, ...this.details };
    return { status: this.status, body: { error } };
  }
}

export function notFound(message: string): ApiError {
  return new ApiError(404, "not_found", message);
}

export function invalidJson(): ApiError {
  return new ApiError(400, "invalid_json", "Request body must be a JSON object");
}

export function validationFailed(fields: readonly FieldError[]): ApiError {
  return new ApiError(400, "validation_failed", "Request validation failed", { fields });
}

export function invalidQuery(fields: readonly FieldError[]): ApiError {
  return new ApiError(400, "invalid_query", "Request query is invalid", { fields });
}

export function illegalTransition(from: Stage, to: Stage): ApiError {
  return new ApiError(422, "illegal_transition", `Cannot move a loan from ${from} to ${to}`);
}

export function loanClosed(loanId: string): ApiError {
  return new ApiError(422, "loan_closed", `Loan ${loanId} is closed`);
}

export function conditionsOpen(loanId: string, openConditionIds: readonly string[]): ApiError {
  const message = `Loan ${loanId} has open conditions`;
  return new ApiError(409, "conditions_open", message, { openConditionIds });
}
