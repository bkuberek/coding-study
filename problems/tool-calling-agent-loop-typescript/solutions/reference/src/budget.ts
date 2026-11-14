// What one question may spend: a number of requests to the model, and tokens, counted from the
// usage each reply reports.

import type { Usage } from "./model.ts";

export type Exhausted = "step_limit" | "token_budget";

export class Budget {
  readonly #maxSteps: number;
  readonly #maxTokens: number;
  #steps = 0;
  #tokens = 0;

  constructor(maxSteps: number, maxTokens: number) {
    this.#maxSteps = maxSteps;
    this.#maxTokens = maxTokens;
  }

  /** The requests sent to the model so far. */
  get steps(): number {
    return this.#steps;
  }

  /** Counts one reply of the model. */
  spend(usage: Usage): void {
    this.#steps += 1;
    this.#tokens += usage.prompt_tokens + usage.completion_tokens;
  }

  /** Why no further request may be sent, or null while one may. */
  exhausted(): Exhausted | null {
    if (this.#steps >= this.#maxSteps) {
      return "step_limit";
    }
    return this.#tokens >= this.#maxTokens ? "token_budget" : null;
  }
}
