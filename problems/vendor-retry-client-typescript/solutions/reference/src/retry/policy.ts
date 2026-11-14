// What the client does about each result of an attempt. All of it is pure, and all of it fits on
// one page, which is the point: this page is what a review of retry behavior reads.

import type { VendorRequest } from "../vendor/scriptedVendor.ts";

export const MAX_ATTEMPTS = 6;
export const ATTEMPT_TIMEOUT_MS = 1000;
const BASE_DELAY_MS = 100;
const MAX_DELAY_MS = 1000;
const WHOLE_SECONDS = /^\d+$/;

/** What one attempt came to. `status` is null when no answer arrived. */
export interface AttemptResult {
  kind: "answer" | "reset" | "timeout";
  status: number | null;
  retryAfter: string | null;
}

export type Verdict = "ok" | "rejected" | "retry" | "unknown";

function isServerFailure(status: number | null): boolean {
  return status === 500 || status === 502 || status === 503 || status === 504;
}

/** A request that is safe to send twice: it has no effect, or the vendor can spot the repeat. */
function isRepeatable(request: VendorRequest): boolean {
  return request.method === "GET" || request.idempotencyKey !== "";
}

export function verdictOf(result: AttemptResult, request: VendorRequest): Verdict {
  if (result.kind === "reset" || result.status === 429) {
    return "retry";
  }
  if (result.kind === "timeout" || isServerFailure(result.status)) {
    return isRepeatable(request) ? "retry" : "unknown";
  }
  const status = result.status ?? 0;
  return status >= 200 && status < 300 ? "ok" : "rejected";
}

/** True when the attempt says something is wrong with the vendor. */
export function isVendorFailure(result: AttemptResult): boolean {
  return result.kind !== "answer" || isServerFailure(result.status);
}

/** The ceiling grows with the attempts that failed, and the fraction is taken after the cap. */
export function backoffDelay(failedAttempts: number, fraction: number): number {
  const ceiling = Math.min(BASE_DELAY_MS * 2 ** (failedAttempts - 1), MAX_DELAY_MS);
  return Math.floor(fraction * ceiling);
}

/** How long the vendor asked us to wait, in milliseconds, or null when it asked for nothing we can
 * read. The header counts seconds. */
export function retryAfterDelay(result: AttemptResult): number | null {
  if (result.status !== 429 && result.status !== 503) {
    return null;
  }
  if (result.retryAfter === null || !WHOLE_SECONDS.test(result.retryAfter)) {
    return null;
  }
  return Number(result.retryAfter) * 1000;
}
