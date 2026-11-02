/** Counts per key, which tasks share from level 2: a count is read and written with no await
 * between, so no other task runs in between. */
export class Tally {
  readonly #counts = new Map<string, number>();

  async add(key: string, amount: number): Promise<number> {
    const count = (this.#counts.get(key) ?? 0) + amount;
    this.#counts.set(key, count);
    await Promise.resolve();
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
