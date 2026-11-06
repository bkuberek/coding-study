// Imports a batch of SKUs: writes each one to the store, then writes an audit entry.

import { AuditLog } from "./auditLog.ts";
import { ShelfStore } from "./shelfStore.ts";

const ALREADY_RUNNING = -1;

export class BatchImporter {
  readonly #shelf = new ShelfStore();
  readonly #audit = new AuditLog();
  readonly #failed: string[] = [];
  #state = "idle";

  /** Resolves with how many SKUs were saved, once the whole batch is done, or -1 at once when a
   * batch is already running. */
  async importAll(skus: string[]): Promise<number> {
    if (this.#state === "running") {
      return ALREADY_RUNNING;
    }
    this.#state = "running";
    let saved = 0;
    for (const sku of skus) {
      try {
        await this.#shelf.save(sku);
        saved += 1;
      } catch {
        this.#failed.push(sku);
      }
    }
    await this.#audit.record(`imported ${saved} of ${skus.length}`);
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

  failedSkus(): string[] {
    return [...this.#failed];
  }
}
