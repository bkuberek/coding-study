// The optional If-Match header: "I read version N; change this only if it is still N".

import { validationFailed, versionConflict } from "./problems.ts";
import type { ApiRequest } from "./routing.ts";

const DIGITS = /^\d+$/;

/** Throws a 400 for a malformed header and a 409 for a stale one; an absent header passes. */
export function checkIfMatch(
  request: ApiRequest,
  order: { readonly id: string; readonly version: number },
): void {
  const expected = request.headers.get("if-match");
  if (expected === undefined) {
    return;
  }
  if (!DIGITS.test(expected)) {
    throw validationFailed([{ field: "If-Match", message: "must be a whole number" }]);
  }
  if (Number(expected) !== order.version) {
    throw versionConflict(order.id, order.version);
  }
}
