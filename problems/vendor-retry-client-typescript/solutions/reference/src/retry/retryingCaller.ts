// The retry loop. It decides nothing about any one result: `policy.ts` does. It owns the order of
// the checks, and the time.

import { sleep } from "../timing/sleep.ts";
import type { JitterSource } from "../timing/jitter.ts";
import { ConnectionReset } from "../vendor/scriptedVendor.ts";
import type { ScriptedVendor, VendorRequest } from "../vendor/scriptedVendor.ts";
import type { CircuitBreaker } from "./breaker.ts";
import {
  ATTEMPT_TIMEOUT_MS,
  MAX_ATTEMPTS,
  backoffDelay,
  isVendorFailure,
  retryAfterDelay,
  verdictOf,
} from "./policy.ts";
import type { AttemptResult } from "./policy.ts";

export interface CallResult {
  attempts: number;
  outcome: string;
  status: number | null;
}

const TIMED_OUT: AttemptResult = { kind: "timeout", status: null, retryAfter: null };
const RESET: AttemptResult = { kind: "reset", status: null, retryAfter: null };

export class RetryingCaller {
  readonly #vendor: ScriptedVendor;
  readonly #jitter: JitterSource;
  #budgetMs: number | null = null;
  #breaker: CircuitBreaker | null = null;
  /** Until when the vendor asked the whole client to stay away. */
  #holdUntil = 0;

  constructor(vendor: ScriptedVendor, jitter: JitterSource) {
    this.#vendor = vendor;
    this.#jitter = jitter;
  }

  setDeadline(budgetMs: number): void {
    this.#budgetMs = budgetMs;
  }

  setBreaker(breaker: CircuitBreaker): void {
    this.#breaker = breaker;
  }

  async call(request: VendorRequest): Promise<CallResult> {
    const deadlineAt = this.#budgetMs === null ? Infinity : Date.now() + this.#budgetMs;
    let attempts = 0;
    let status: number | null = null;

    for (;;) {
      const held = this.#holdUntil - Date.now();
      if (held > 0) {
        if (Date.now() + held >= deadlineAt) {
          return { attempts, outcome: "deadline_exceeded", status };
        }
        await sleep(held);
        continue;
      }
      if (this.#breaker !== null && !this.#breaker.admit()) {
        return { attempts, outcome: "circuit_open", status };
      }

      attempts += 1;
      const result = await this.#attempt(request, deadlineAt);
      status = result.status;
      this.#breaker?.record(isVendorFailure(result));

      const verdict = verdictOf(result, request);
      if (verdict !== "retry") {
        return { attempts, outcome: verdict, status };
      }
      if (this.#breaker?.isOpen()) {
        return { attempts, outcome: "circuit_open", status };
      }
      if (attempts === MAX_ATTEMPTS) {
        return { attempts, outcome: "exhausted", status };
      }

      const askedFor = retryAfterDelay(result);
      if (askedFor !== null) {
        this.#holdUntil = Math.max(this.#holdUntil, Date.now() + askedFor);
        continue;
      }
      const delay = backoffDelay(attempts, this.#jitter.next());
      if (Date.now() + delay >= deadlineAt) {
        return { attempts, outcome: "deadline_exceeded", status };
      }
      await sleep(delay);
    }
  }

  /** One attempt, which ends by the timeout or the deadline if the vendor has not answered. */
  async #attempt(request: VendorRequest, deadlineAt: number): Promise<AttemptResult> {
    let timer: ReturnType<typeof setTimeout> | undefined;
    const timeout = new Promise<AttemptResult>((resolve) => {
      const limit = Math.min(ATTEMPT_TIMEOUT_MS, deadlineAt - Date.now());
      timer = setTimeout(() => resolve(TIMED_OUT), limit);
    });
    try {
      return await Promise.race([this.#answer(request), timeout]);
    } finally {
      clearTimeout(timer);
    }
  }

  async #answer(request: VendorRequest): Promise<AttemptResult> {
    try {
      const { status, retryAfter } = await this.#vendor.send(request);
      return { kind: "answer", status, retryAfter };
    } catch (error) {
      if (error instanceof ConnectionReset) {
        return RESET;
      }
      throw error;
    }
  }
}
