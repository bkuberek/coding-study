// What a scan's answer does to a stored file: clean releases it, infected deletes its bytes, and
// anything else leaves it where it is, pending and never served.

import { scan } from "./scanner.ts";
import type { FileStore, ScanStatus, StoredFile } from "./store.ts";

export class Quarantine {
  readonly #store: FileStore;
  /** One scan per file at a time: a second request for the same file waits for the first. */
  readonly #scanning = new Map<string, Promise<ScanStatus>>();

  constructor(store: FileStore) {
    this.#store = store;
  }

  /** A new upload's scan. An infected upload is refused, so nothing of it is kept. */
  async admit(file: StoredFile, bytes: Buffer): Promise<ScanStatus> {
    const verdict = await scan(bytes, file.sha256);
    if (verdict === "clean") {
      await this.#store.release(file);
    } else if (verdict === "infected") {
      await this.#store.forget(file);
    }
    return verdict;
  }

  /** Scans a pending file again; a file already settled keeps its status and asks no one. */
  rescan(file: StoredFile): Promise<ScanStatus> {
    if (file.status !== "pending") {
      return Promise.resolve(file.status);
    }
    const running = this.#scanning.get(file.id);
    if (running !== undefined) {
      return running;
    }
    const settling = this.#settle(file).finally(() => this.#scanning.delete(file.id));
    this.#scanning.set(file.id, settling);
    return settling;
  }

  async #settle(file: StoredFile): Promise<ScanStatus> {
    const verdict = await scan(await this.#store.quarantined(file), file.sha256);
    if (verdict === "clean") {
      await this.#store.release(file);
    } else if (verdict === "infected") {
      await this.#store.condemn(file);
    }
    return file.status;
  }
}
