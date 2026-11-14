// What was answered for each idempotency key. The answer is frozen when it is remembered: a replay
// repeats what the first request was told, not what the order looks like now.

import type { Answer } from "../shared/routing.ts";
import { canonicalJson } from "../shared/json.ts";
import { idempotencyConflict } from "../shared/problems.ts";

interface Remembered {
  readonly fingerprint: string;
  readonly answer: Answer;
}

export class ReplayCache {
  readonly #byKey = new Map<string, Remembered>();

  /** The remembered answer for this key and request, undefined for a new key, and a 422 when the
   * key was used for a request with another meaning. */
  replay(key: string, input: unknown): Answer | undefined {
    const remembered = this.#byKey.get(key);
    if (remembered === undefined) {
      return undefined;
    }
    if (remembered.fingerprint !== canonicalJson(input)) {
      throw idempotencyConflict(key);
    }
    return remembered.answer;
  }

  remember(key: string, input: unknown, answer: Answer): void {
    const frozen = { status: answer.status, body: structuredClone(answer.body) };
    this.#byKey.set(key, { fingerprint: canonicalJson(input), answer: frozen });
  }
}
