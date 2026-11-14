// The product store. It takes writes one at a time, and each write takes 100 ms. It rejects a row
// whose SKU starts with "bad-", after the same 100 ms.

const SAVE_MS = 100;

export class ShelfStore {
  readonly #skus: string[] = [];

  async save(sku: string): Promise<void> {
    await new Promise((resolve) => setTimeout(resolve, SAVE_MS));
    if (sku.startsWith("bad-")) {
      throw new Error(`The store rejected ${sku}`);
    }
    this.#skus.push(sku);
  }

  skus(): string[] {
    return [...this.#skus];
  }
}
