export class StressCounter {
  #count = 0;

  async increment(): Promise<number> {
    const count = this.#count;
    await Promise.resolve();
    this.#count = count + 1;
    return count + 1;
  }
}
