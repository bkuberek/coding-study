// The failures the API answers on purpose. Anything else is a bug, and answers a plain 500.

export interface FieldProblem {
  field: string;
  message: string;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown>;

  constructor(status: number, code: string, message: string, details: Record<string, unknown> = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }

  body(): unknown {
    return { error: { code: this.code, message: this.message, ...this.details } };
  }
}

export function notFound(what: string): ApiError {
  return new ApiError(404, "not_found", `No ${what}`);
}

export function invalidJson(): ApiError {
  return new ApiError(400, "invalid_json", "Request body must be a JSON object");
}

export function validationFailed(fields: FieldProblem[]): ApiError {
  return new ApiError(400, "validation_failed", "Request validation failed", { fields });
}
