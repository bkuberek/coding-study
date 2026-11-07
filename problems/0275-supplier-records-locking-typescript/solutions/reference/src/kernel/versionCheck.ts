// The checks every versioned write shares.

import { ApiError } from "./errors.ts";
import type { FieldProblem } from "./errors.ts";

/** A write that does not say what it read is refused, so it cannot overwrite anything by accident. */
export function requireVersionKey(input: Record<string, unknown>, key: string): void {
  if (!(key in input)) {
    throw new ApiError(428, "version_required", `${key} is required`);
  }
}

export function versionProblems(input: Record<string, unknown>, key: string): FieldProblem[] {
  const value = input[key];
  return typeof value === "number" && Number.isInteger(value) && value >= 1
    ? []
    : [{ field: key, message: "must be a whole number from 1" }];
}

export function requestIdProblems(input: Record<string, unknown>): FieldProblem[] {
  const value = input.requestId;
  return value === undefined || (typeof value === "string" && value !== "")
    ? []
    : [{ field: "requestId", message: "must be a non-empty string" }];
}

export function staleWrite(label: string, current: { version: number }): ApiError {
  return new ApiError(409, "stale_write", `${label} is at version ${current.version}`, {
    current,
    currentVersion: current.version,
  });
}
