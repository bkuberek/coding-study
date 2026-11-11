/**
 * What an attempt's view knows of its attempt ending, so it says so once, however many reads of
 * the attempt find it over.
 */

export class AttemptEnding {
  #ended = false;

  get ended(): boolean {
    return this.#ended;
  }

  /** The attempt is over: `show` runs the first time only. */
  end(show: () => void): void {
    if (this.#ended) return;
    this.#ended = true;
    show();
  }
}
