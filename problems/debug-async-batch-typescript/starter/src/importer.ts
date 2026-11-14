// Imports a batch of SKUs: writes each one to the store, then writes an audit entry.

import { AuditLog } from "./auditLog.ts";
import { ShelfStore } from "./shelfStore.ts";

export class BatchImporter {
  readonly #shelf = new ShelfStore();
  readonly #audit = new AuditLog();
  #state = "idle";

  /** Resolves with how many SKUs were saved, once the whole batch is done. */
  async importAll(skus: string[]): Promise<number> {
    this.#state = "running";
    let saved = 0;
    skus.forEach(async (sku) => {
      await this.#shelf.save(sku);
      saved += 1;
    });
    this.#audit.record(`imported ${saved} of ${skus.length}`);
    this.#state = "finished";
    return saved;
  }

  state(): string {
    return this.#state;
  }

  savedSkus(): string[] {
    return this.#shelf.skus();
  }

  auditLog(): string[] {
    return this.#audit.entries();
  }
}
