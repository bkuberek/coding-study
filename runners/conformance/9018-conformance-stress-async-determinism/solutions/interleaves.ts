export class StressLog {
  readonly #values: number[] = [];

  async append(value: number): Promise<number> {
    await new Promise((resolve) => setImmediate(resolve));
    this.#values.push(value);
    return this.#values.length;
  }
}
