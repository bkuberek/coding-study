/**
 * What an attempt's view knows of its attempt ending, so it neither says so twice nor reads an
 * attempt it knows is over: reading one is answered with a 409, which the browser logs as an
 * error.
 */

export class AttemptEnding {
  #ended = false;
  #finishing = false;
  #held = false;

  get ended(): boolean {
    return this.#ended;
  }

  /**
   * Whether a read of the attempt should wait: it is over, or this tab is finishing it. A read
   * held back while this tab finishes is remembered, for `failed` to report.
   */
  holds(): boolean {
    if (this.#finishing && !this.#ended) this.#held = true;
    return this.#ended || this.#finishing;
  }

  /** This tab is about to finish the attempt: the changes it causes need no read. */
  finishing(): void {
    this.#finishing = true;
  }

  /** Finishing failed, so the attempt stands; true when a read was held back meanwhile. */
  failed(): boolean {
    const held = this.#held;
    this.#finishing = false;
    this.#held = false;
    return held;
  }

  /** The attempt is over: `show` runs the first time only. */
  end(show: () => void): void {
    this.#finishing = false;
    this.#held = false;
    if (this.#ended) return;
    this.#ended = true;
    show();
  }
}

/** What the Done dialog tells the view of finishing the attempt. */
export interface Finishing {
  /** The Done request is about to go out. */
  begin(): void;
  /** It was refused, or failed. */
  failed(): void;
  /** The attempt is finished. */
  finished(): void;
}
