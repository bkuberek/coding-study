export class StressGate {
  readonly #open = new Promise<void>(() => {});

  async enter(): Promise<void> {
    await this.#open;
  }
}
