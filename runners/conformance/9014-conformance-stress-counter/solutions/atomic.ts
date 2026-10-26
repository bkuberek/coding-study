export class StressCounter {
  #count = 0;

  async increment(): Promise<number> {
    this.#count += 1;
    return this.#count;
  }
}
