// Stops calling a vendor that keeps failing. It counts attempts, not calls, because each attempt is
// load on a vendor that is already struggling.

export class CircuitBreaker {
  readonly #threshold: number;
  readonly #cooldownMs: number;
  #failures = 0;
  #openUntil: number | null = null;
  #probing = false;

  constructor(threshold: number, cooldownMs: number) {
    this.#threshold = threshold;
    this.#cooldownMs = cooldownMs;
  }

  /** May an attempt start now? Once the cooldown is over, one attempt at a time may: the probe. */
  admit(): boolean {
    if (this.#openUntil === null) {
      return true;
    }
    if (Date.now() < this.#openUntil || this.#probing) {
      return false;
    }
    this.#probing = true;
    return true;
  }

  record(failed: boolean): void {
    if (this.#probing) {
      this.#probing = false;
      if (failed) {
        this.#open();
      } else {
        this.#openUntil = null;
        this.#failures = 0;
      }
      return;
    }
    if (this.#openUntil !== null) {
      return;
    }
    this.#failures = failed ? this.#failures + 1 : 0;
    if (this.#failures >= this.#threshold) {
      this.#open();
    }
  }

  isOpen(): boolean {
    return this.#openUntil !== null;
  }

  #open(): void {
    this.#openUntil = Date.now() + this.#cooldownMs;
    this.#failures = 0;
  }
}
