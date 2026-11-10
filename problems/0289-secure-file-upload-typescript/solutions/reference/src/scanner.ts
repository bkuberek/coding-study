// The malware-scanning vendor. Only its own "clean" makes a file clean: a scan that cannot finish
// answers "pending", and a pending file stays in quarantine.

import { setTimeout as sleep } from "node:timers/promises";

import { SCANNER_API_KEY, SCANNER_URL } from "./config.ts";
import { FIRST_RETRY_WAIT_MS, SCAN_ATTEMPTS, SCAN_TIMEOUT_MS } from "./limits.ts";
import type { ScanStatus } from "./store.ts";

type Attempt =
  | { kind: "verdict"; verdict: "clean" | "infected" }
  | { kind: "retry"; waitMs: number | null }
  | { kind: "give_up" };

const WHOLE_SECONDS = /^\d+$/;

export async function scan(bytes: Buffer, sha256: string): Promise<ScanStatus> {
  for (let attempt = 1; ; attempt += 1) {
    const outcome = await ask(bytes, sha256);
    if (outcome.kind === "verdict") {
      return outcome.verdict;
    }
    if (outcome.kind === "give_up" || attempt === SCAN_ATTEMPTS) {
      return "pending";
    }
    await sleep(outcome.waitMs ?? FIRST_RETRY_WAIT_MS * 2 ** (attempt - 1));
  }
}

async function ask(bytes: Buffer, sha256: string): Promise<Attempt> {
  try {
    const response = await fetch(`${SCANNER_URL}/v1/scan`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${SCANNER_API_KEY}`,
        "Content-Type": "application/octet-stream",
        "X-Content-Sha256": sha256,
      },
      body: bytes,
      // It covers the body too, so a vendor that answers a byte at a time cannot outlast it.
      signal: AbortSignal.timeout(SCAN_TIMEOUT_MS),
    });
    const text = await response.text();
    if (response.status === 429) {
      return { kind: "retry", waitMs: retryAfterMs(response.headers.get("retry-after")) };
    }
    if (response.status >= 500) {
      return { kind: "retry", waitMs: null };
    }
    return response.status === 200 ? verdictIn(text) : { kind: "give_up" };
  } catch {
    // No answer in time, or no connection: the vendor may answer the next time.
    return { kind: "retry", waitMs: null };
  }
}

/** An answer that names no verdict is no verdict, and never a clean one. */
function verdictIn(text: string): Attempt {
  try {
    const verdict = (JSON.parse(text) as { verdict?: unknown }).verdict;
    if (verdict === "clean" || verdict === "infected") {
      return { kind: "verdict", verdict };
    }
  } catch {
    // Broken JSON, or JSON that is not an object: no verdict either way.
  }
  return { kind: "give_up" };
}

function retryAfterMs(value: string | null): number | null {
  return value !== null && WHOLE_SECONDS.test(value) ? Number(value) * 1000 : null;
}
