// The client for the rates vendor. The rest of the company calls this, and it calls the vendor.

import { canonicalJson } from "./json.ts";
import { ScriptedVendor } from "./vendor/scriptedVendor.ts";

export class RatesClient {
  readonly #vendor = new ScriptedVendor();

  scriptVendor(steps: string[]): void {
    this.#vendor.script(steps);
  }

  /** Answers JSON text with sorted keys: how many attempts it took, how it ended, and the status of
   * the last attempt. */
  async call(method: string, path: string, idempotencyKey: string): Promise<string> {
    const answer = await this.#vendor.send({ method, path, idempotencyKey });
    const outcome = answer.status >= 200 && answer.status < 300 ? "ok" : "exhausted";
    return canonicalJson({ attempts: 1, outcome, status: answer.status });
  }

  attempts(): string[] {
    return this.#vendor.attemptLog();
  }
}
