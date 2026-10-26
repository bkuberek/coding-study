export class ConcurrencyLimiter {
  #permits: number;
  #waiters: (() => void)[] = [];

  constructor(limit: number) {
    this.#permits = limit;
  }

  async acquire(): Promise<void> {
    if (this.#permits === 0) {
      await new Promise<void>((resolve) => this.#waiters.push(resolve));
    }
    this.#permits--;
  }

  tryAcquire(): boolean {
    if (this.#permits === 0) {
      return false;
    }
    this.#permits--;
    return true;
  }

  release(): void {
    this.#permits++;
    const waiters = this.#waiters;
    this.#waiters = [];
    for (const resolve of waiters) {
      resolve();
    }
  }

  available(): number {
    return this.#permits;
  }
}
