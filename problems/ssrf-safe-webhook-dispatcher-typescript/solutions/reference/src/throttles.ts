// What keeps the dispatcher from becoming a weapon against someone else's server: a rate per host,
// and one request in flight per host.

/** At most `limit` deliveries to one host in any `windowMs`, from a log of when each started. */
export class HostRateLimiter {
  readonly #limit: number;
  readonly #windowMs: number;
  readonly #starts = new Map<string, number[]>();

  constructor(limit: number, windowMs: number) {
    this.#limit = limit;
    this.#windowMs = windowMs;
  }

  /** Counts a delivery to `host` and answers true, or answers false and counts nothing. */
  tryTake(host: string, now: number = Date.now()): boolean {
    const recent = (this.#starts.get(host) ?? []).filter((start) => now - start < this.#windowMs);
    const allowed = recent.length < this.#limit;
    if (allowed) {
      recent.push(now);
    }
    this.#starts.set(host, recent);
    return allowed;
  }
}

/** Runs the tasks of one host one at a time, in the order they came, and different hosts at once. */
export class HostQueue {
  readonly #tails = new Map<string, Promise<void>>();

  run<T>(host: string, task: () => Promise<T>): Promise<T> {
    const previous = this.#tails.get(host) ?? Promise.resolve();
    const result = previous.then(task);
    const tail = result.then(
      () => undefined,
      () => undefined,
    );
    this.#tails.set(host, tail);
    void tail.then(() => {
      if (this.#tails.get(host) === tail) {
        this.#tails.delete(host);
      }
    });
    return result;
  }
}
