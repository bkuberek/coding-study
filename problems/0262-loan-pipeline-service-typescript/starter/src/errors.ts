// Errors the API answers on purpose.

import type { ApiResponse } from "./http/router.ts";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }

  toResponse(): ApiResponse {
    return { status: this.status, body: { error: { code: this.code, message: this.message } } };
  }
}

export function notFound(message: string): ApiError {
  return new ApiError(404, "not_found", message);
}
