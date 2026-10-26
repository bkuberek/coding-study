export class ConcurrencyLimiter {
  #permits: number;
  readonly #waiters: (() => void)[] = [];

  constructor(limit: number) {
    this.#permits = limit;
  }

  async acquire(): Promise<void> {
    if (this.#permits > 0) {
      this.#permits--;
      return;
    }
    await new Promise<void>((resolve) => this.#waiters.push(resolve));
  }

  tryAcquire(): boolean {
    if (this.#permits === 0) {
      return false;
    }
    this.#permits--;
    return true;
  }

  release(): void {
    const next = this.#waiters.shift();
    if (next === undefined) {
      this.#permits++;
      return;
    }
    next();
  }

  available(): number {
    return this.#permits;
  }
}
