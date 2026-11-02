/** Counts per key; `add` awaits between reading a count and writing it. */
export class Tally {
  readonly #counts = new Map<string, number>();

  async add(key: string, amount: number): Promise<number> {
    const count = (this.#counts.get(key) ?? 0) + amount;
    await Promise.resolve();
    this.#counts.set(key, count);
    return count;
  }

  count(key: string): number {
    return this.#counts.get(key) ?? 0;
  }

  take(key: string, amount: number): boolean {
    const count = this.#counts.get(key) ?? 0;
    if (count < amount) {
      return false;
    }
    this.#counts.set(key, count - amount);
    return true;
  }
}
