import { isOpen, type Balances } from "./accounts.ts";

const REFUSED = -1;

/** The balances of open accounts; refuses what names an unknown account or would overdraw. */
export class Ledger {
  readonly #balances: Balances = new Map();

  open(accountId: string): boolean {
    if (isOpen(this.#balances, accountId)) {
      return false;
    }
    this.#balances.set(accountId, 0);
    return true;
  }

  add(accountId: string, amount: number): number {
    const balance = this.#balances.get(accountId);
    if (balance === undefined) {
      return REFUSED;
    }
    this.#balances.set(accountId, balance + amount);
    return balance + amount;
  }

  move(sourceId: string, targetId: string, amount: number): number {
    const source = this.#balances.get(sourceId);
    const target = this.#balances.get(targetId);
    if (source === undefined || target === undefined || sourceId === targetId || source < amount) {
      return REFUSED;
    }
    this.#balances.set(sourceId, source - amount);
    this.#balances.set(targetId, target + amount);
    return source - amount;
  }
}
