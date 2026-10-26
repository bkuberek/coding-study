export class StressMutex {
  #held = false;
  readonly #waiting: (() => void)[] = [];

  async lock(): Promise<void> {
    if (!this.#held) {
      this.#held = true;
      return;
    }
    await new Promise<void>((resolve) => this.#waiting.push(resolve));
  }

  unlock(): void {
    const next = this.#waiting.shift();
    if (next === undefined) {
      this.#held = false;
    } else {
      next();
    }
  }
}
