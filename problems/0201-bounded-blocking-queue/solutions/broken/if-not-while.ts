export class BoundedBlockingQueue {
  readonly #capacity: number;
  readonly #items: number[] = [];
  #waiting: (() => void)[] = [];

  constructor(capacity: number) {
    this.#capacity = capacity;
  }

  async put(value: number): Promise<void> {
    if (this.#items.length >= this.#capacity) {
      await this.#changed();
    }
    this.#items.push(value);
    this.#wakeAll();
  }

  async take(): Promise<number> {
    if (this.#items.length === 0) {
      await this.#changed();
    }
    const value = this.#items.shift() as number;
    this.#wakeAll();
    return value;
  }

  size(): number {
    return this.#items.length;
  }

  #changed(): Promise<void> {
    return new Promise((resolve) => this.#waiting.push(resolve));
  }

  #wakeAll(): void {
    const waiting = this.#waiting;
    this.#waiting = [];
    for (const resolve of waiting) {
      resolve();
    }
  }
}
