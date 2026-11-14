// Every account by id, merged-away ones included.

import { Account } from "./models.ts";

/** The bank's accounts. A merged-away account keeps its id, its history and its place here. */
export class Accounts {
  readonly #byId = new Map<string, Account>();

  /** Opens an account; false when the id is taken, even by a merged-away account. */
  create(timestamp: number, accountId: string): boolean {
    if (this.#byId.has(accountId)) return false;
    this.#byId.set(accountId, new Account(accountId, timestamp));
    return true;
  }

  /** The account with this id, open or merged away. */
  find(accountId: string): Account | undefined {
    return this.#byId.get(accountId);
  }

  findOpen(accountId: string): Account | undefined {
    const account = this.#byId.get(accountId);
    return account?.isOpen ? account : undefined;
  }

  /** The open account that holds `accountId` now, following its merges. */
  holderOf(accountId: string): Account | undefined {
    return this.#byId.get(accountId)?.holder;
  }

  open(): Account[] {
    return this.#byId
      .values()
      .filter((account) => account.isOpen)
      .toArray();
  }

  /** Folds `otherId` into `accountId`; false, changing nothing, unless both are open and differ. */
  merge(timestamp: number, accountId: string, otherId: string): boolean {
    const kept = this.findOpen(accountId);
    const absorbed = this.findOpen(otherId);
    if (kept === undefined || absorbed === undefined || kept === absorbed) return false;
    kept.absorb(absorbed, timestamp);
    return true;
  }
}
