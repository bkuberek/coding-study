// Values kept in memory under random ids, for what a cookie points at: a session, or a login in
// progress. The id is the only thing that goes to the browser.

import { randomBytes } from "node:crypto";

export class MemoryStore<T> {
  readonly #entries = new Map<string, T>();

  /** Keeps `value` under a new id that nobody can guess, and returns the id. */
  put(value: T): string {
    const id = randomBytes(32).toString("base64url");
    this.#entries.set(id, value);
    return id;
  }

  get(id: string | undefined): T | undefined {
    return id === undefined ? undefined : this.#entries.get(id);
  }

  set(id: string, value: T): void {
    this.#entries.set(id, value);
  }

  /** The value under `id`, which is forgotten: it can be taken once. */
  take(id: string | undefined): T | undefined {
    const value = this.get(id);
    if (id !== undefined) {
      this.#entries.delete(id);
    }
    return value;
  }

  delete(id: string | undefined): void {
    if (id !== undefined) {
      this.#entries.delete(id);
    }
  }
}
