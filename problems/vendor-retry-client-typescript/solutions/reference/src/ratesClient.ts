// The client for the rates vendor. The rest of the company calls this, and it calls the vendor.

import { canonicalJson } from "./json.ts";
import { CircuitBreaker } from "./retry/breaker.ts";
import { RetryingCaller } from "./retry/retryingCaller.ts";
import { ScriptedJitter } from "./timing/jitter.ts";
import { ScriptedVendor } from "./vendor/scriptedVendor.ts";

export class RatesClient {
  readonly #vendor = new ScriptedVendor();
  readonly #jitter = new ScriptedJitter();
  readonly #caller = new RetryingCaller(this.#vendor, this.#jitter);

  scriptVendor(steps: string[]): void {
    this.#vendor.script(steps);
  }

  /** Answers JSON text with sorted keys: how many attempts it took, how it ended, and the status of
   * the last attempt. */
  async call(method: string, path: string, idempotencyKey: string): Promise<string> {
    return canonicalJson(await this.#caller.call({ method, path, idempotencyKey }));
  }

  attempts(): string[] {
    return this.#vendor.attemptLog();
  }

  scriptJitter(fractions: number[]): void {
    this.#jitter.script(fractions);
  }

  setDeadline(budgetMs: number): void {
    this.#caller.setDeadline(budgetMs);
  }

  setBreaker(failures: number, cooldownMs: number): void {
    this.#caller.setBreaker(new CircuitBreaker(failures, cooldownMs));
  }
}
