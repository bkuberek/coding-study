// A source of random fractions that a test can script. A production build would pass one over
// `Math.random`; this interface is what makes retry timing testable at all.

export interface JitterSource {
  /** A fraction from 0 to 1. */
  next(): number;
}

export class ScriptedJitter implements JitterSource {
  readonly #fractions: number[] = [];

  script(fractions: number[]): void {
    this.#fractions.push(...fractions);
  }

  /** The next scripted fraction, or 1 when the script has run out. */
  next(): number {
    return this.#fractions.shift() ?? 1;
  }
}
