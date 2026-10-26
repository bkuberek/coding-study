interface WaitingPutter {
  readonly value: number;
  readonly resolve: () => void;
}

export class BoundedBlockingQueue {
  readonly #capacity: number;
  readonly #items: number[] = [];
  readonly #takers: ((value: number) => void)[] = [];
  readonly #putters: WaitingPutter[] = [];

  constructor(capacity: number) {
    this.#capacity = capacity;
  }

  async put(value: number): Promise<void> {
    const taker = this.#takers.shift();
    if (taker !== undefined) {
      taker(value);
      return;
    }
    if (this.#items.length < this.#capacity) {
      this.#items.push(value);
      return;
    }
    await new Promise<void>((resolve) => this.#putters.push({ value, resolve }));
  }

  async take(): Promise<number> {
    if (this.#items.length > 0) {
      const value = this.#items.shift() as number;
      const putter = this.#putters.shift();
      if (putter !== undefined) {
        this.#items.push(putter.value);
        putter.resolve();
      }
      return value;
    }
    return new Promise<number>((resolve) => this.#takers.push(resolve));
  }

  size(): number {
    return this.#items.length;
  }
}
